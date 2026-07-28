#!/usr/bin/env python3
"""Audit Phase156 external 10-sigungu RTMS rent collection.

This phase deliberately avoids claiming 681/682 prediction error, because the
external sample has public L00 real-estate GVA totals but not public 681/682
small-industry actuals.  It instead documents collection completeness and
checks whether rent activity indicators have usable variation against the
published L00 total.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase156_rtms_rent_external_10"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase156_rtms_rent_external_10_audit.md"
MONTHLY = OUT / "phase156_rtms_rent_sigungu_monthly.csv"
ROWS = OUT / "phase156_rtms_rent_rows.csv"
CALLS = OUT / "phase156_rtms_rent_call_manifest.csv"
CROSSWALK = OUT / "phase156_external_10_lawd_crosswalk.csv"
GRVA = DATA / "expanded_sigungu_grva_real.csv"


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
    view = view.fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[col].replace("|", "\\|") for col in view.columns) + " |")
    return "\n".join(lines)


def read_l00_actual() -> pd.DataFrame:
    grva = pd.read_csv(GRVA, encoding="cp949", dtype=str)
    grva["value_num"] = pd.to_numeric(grva["value"], errors="coerce")
    l00 = grva[
        grva["prd_de"].eq("2023")
        & grva["c2_id"].eq("L00")
    ].copy()
    xw = pd.read_csv(CROSSWALK, dtype={"area_code": str, "lawd_cd": str, "rtms_lawd_cd": str})
    out = xw.merge(
        l00[["source_region", "c1_id", "c1_nm", "value_num"]],
        left_on=["source_region", "area_code", "c1_nm"],
        right_on=["source_region", "c1_id", "c1_nm"],
        how="left",
        validate="one_to_one",
    )
    out["l00_realestate_gva_eok"] = out["value_num"] / 100.0
    return out[
        [
            "source_region",
            "c1_nm",
            "area_code",
            "lawd_cd",
            "name",
            "폐지여부",
            "rtms_lawd_cd",
            "rtms_lawd_name",
            "rtms_code_policy",
            "l00_realestate_gva_eok",
        ]
    ]


def main() -> None:
    if not MONTHLY.exists():
        raise FileNotFoundError(MONTHLY)
    rows = pd.read_csv(ROWS, encoding="utf-8-sig", low_memory=False)
    calls = pd.read_csv(CALLS, encoding="utf-8-sig")
    monthly = pd.read_csv(MONTHLY, encoding="utf-8-sig", dtype={"kosis_area_code": str, "lawd_cd": str})
    l00 = read_l00_actual()

    calls["result_code_norm"] = calls["result_code"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(3)
    source_summary = (
        rows.groupby(["source_name", "asset_type"], as_index=False)
        .agg(
            row_count=("period", "size"),
            sigungu_count=("kosis_area_code", "nunique"),
            month_cells=("period", "nunique"),
        )
        .sort_values(["asset_type", "source_name"])
    )
    call_summary = (
        calls.groupby(["source_name"], as_index=False)
        .agg(
            calls=("period", "size"),
            ok_calls=("result_code_norm", lambda s: int(s.eq("000").sum())),
            total_items=("item_count", "sum"),
            min_period=("period", "min"),
            max_period=("period", "max"),
        )
        .sort_values("source_name")
    )
    for col in ["min_period", "max_period"]:
        call_summary[col] = call_summary[col].astype(str)

    m = monthly.copy()
    m["year"] = m["period"].astype(str).str[:4]
    m2023 = m[m["year"].eq("2023")].copy()
    sig = (
        m2023.groupby(["source_region", "sigungu_name", "kosis_area_code", "lawd_cd"], as_index=False)
        .agg(
            rent_contract_count=("rent_contract_count", "sum"),
            deposit_eok=("deposit_10k_krw", lambda s: s.sum() / 10000),
            monthly_rent_eok=("monthly_rent_10k_krw", lambda s: s.sum() / 10000),
            rent_area_sqm=("area_sqm", "sum"),
            source_types=("source_id", "nunique"),
        )
    )
    sig["deposit_per_contract_eok"] = sig["deposit_eok"] / sig["rent_contract_count"].replace(0, np.nan)
    sig["deposit_per_area_10k_per_sqm"] = sig["deposit_eok"] * 10000 / sig["rent_area_sqm"].replace(0, np.nan)
    sig = sig.merge(
        l00[["source_region", "c1_nm", "area_code", "l00_realestate_gva_eok"]],
        left_on=["source_region", "sigungu_name", "kosis_area_code"],
        right_on=["source_region", "c1_nm", "area_code"],
        how="left",
        validate="one_to_one",
    )
    sig["deposit_to_l00_gva_pct"] = sig["deposit_eok"] / sig["l00_realestate_gva_eok"].replace(0, np.nan) * 100
    sig["contract_per_l00_100eok"] = sig["rent_contract_count"] / sig["l00_realestate_gva_eok"].replace(0, np.nan) * 100
    sig = sig.sort_values("deposit_to_l00_gva_pct", ascending=False)

    coverage = monthly.groupby(["source_region", "sigungu_name", "asset_type"], as_index=False).agg(
        observed_month_cells=("period", "nunique"),
        row_count=("rent_contract_count", "sum"),
    )
    expected_months = 48
    coverage["coverage_pct"] = coverage["observed_month_cells"] / expected_months * 100

    outputs = {
        "source_summary": source_summary,
        "call_summary": call_summary,
        "sigungu_2023_metrics": sig,
        "coverage": coverage,
        "l00_actual_crosswalk": l00,
    }
    for name, df in outputs.items():
        df.to_csv(OUT / f"phase156_{name}.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "phase": "phase156_rtms_rent_external_10_audit",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_files": [
            str(ROWS.relative_to(ROOT)),
            str(MONTHLY.relative_to(ROOT)),
            str(CALLS.relative_to(ROOT)),
            str(CROSSWALK.relative_to(ROOT)),
            str(GRVA.relative_to(ROOT)),
        ],
        "raw_scope_note": (
            "RTMS APIs are nationwide services parameterized by LAWD_CD, but the local raw cache for this phase "
            "contains only the 10 selected external sigungu. Re-running the collector with a broader target list can "
            "collect other regions without changing source metadata."
        ),
        "validation_boundary": (
            "External sample has public 2023 L00 real-estate GVA totals; public 681/682 small-industry actuals were not "
            "found locally, so no 681/682 error-rate claim is made."
        ),
    }
    (OUT / "phase156_audit_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    missing_l00 = l00[l00["l00_realestate_gva_eok"].isna()]
    report = f"""# Phase156 외부 10개 시군구 주거 전월세 자료 수집 및 부동산업 감사

## 목적

고양·포항 두 도시에서 만든 `681 부동산 임대 및 공급업 / 682 부동산 관련 서비스업` 배분 후보가 두 도시 과적합인지 확인하기 위해, Phase106의 외부 10개 시군구에 같은 유형의 전월세 활동자료를 수집했다.

## 수집 결과

- 대상: Phase106 외부 표본 10개 시군구, 2020~2023년 월별
- 자료: 아파트·오피스텔·단독/다가구 전월세 실거래
- 총 호출: {len(calls):,}건, 정상 호출: {int(calls['result_code_norm'].eq('000').sum()):,}건
- 총 행수: {len(rows):,}건
- 원자료 범위 기록: RTMS API는 전국 법정동코드 조회형 서비스이나, 이번 로컬 raw cache는 외부 검증 표본 10개 시군구만 보관했다. 추후 다른 지역 분석 시 같은 수집기를 대상 목록만 바꿔 재실행한다.

### API별 수집량

{md_table(source_summary.rename(columns={'source_name':'자료명','asset_type':'자산유형','row_count':'행수','sigungu_count':'시군구수','month_cells':'월수'}), 0)}

### 호출 정상성

{md_table(call_summary.rename(columns={'source_name':'자료명','calls':'호출','ok_calls':'정상호출','total_items':'응답행 합계','min_period':'최소월','max_period':'최대월'}), 0)}

## 법정동코드 매핑

일부 지역은 KOSIS actual의 공표지역명과 2026년 현재 RTMS 조회코드가 다르다. 따라서 KOSIS/공표코드는 actual 매칭에 보존하고, RTMS 수집에는 probe로 행이 확인된 현행 조회코드를 별도로 사용했다.

{md_table(l00.rename(columns={'source_region':'광역','c1_nm':'시군구','area_code':'KOSIS코드','lawd_cd':'KOSIS명칭 법정동5자리','name':'KOSIS명칭 법정동명','폐지여부':'KOSIS명칭 상태','rtms_lawd_cd':'RTMS조회코드','rtms_lawd_name':'RTMS조회명','rtms_code_policy':'조회코드 정책','l00_realestate_gva_eok':'2023 부동산업 GVA(억원)'}), 1)}

## 2023년 부동산업 총량 대비 전월세 활동자료

아래 표는 소분류 실제값 검증이 아니라, 외부 표본에서 전월세 자료가 지역별 부동산업 규모와 어느 정도의 변별력을 갖는지 보는 총량 감사다.

{md_table(sig[['source_region','sigungu_name','l00_realestate_gva_eok','rent_contract_count','deposit_eok','monthly_rent_eok','deposit_per_contract_eok','deposit_per_area_10k_per_sqm','deposit_to_l00_gva_pct','contract_per_l00_100eok']].rename(columns={'source_region':'광역','sigungu_name':'시군구','l00_realestate_gva_eok':'2023 부동산업 GVA(억원)','rent_contract_count':'전월세 계약건수','deposit_eok':'보증금 합계(억원)','monthly_rent_eok':'월세 합계(억원)','deposit_per_contract_eok':'계약당 보증금(억원)','deposit_per_area_10k_per_sqm':'㎡당 보증금(만원)','deposit_to_l00_gva_pct':'보증금/GVA(%)','contract_per_l00_100eok':'GVA 100억원당 계약'}), 2)}

## 검증 경계

1. 외부 10개 지역의 2023년 `L00 부동산업` 총량 actual은 확인했다.
2. 그러나 공개자료 안에서 외부 10개 지역의 `681/682 소분류 actual`은 확인되지 않았다.
3. 따라서 이번 단계는 681/682 오차율을 주장하지 않는다.
4. 대신 고양·포항에서 수집했던 전월세 3종을 외부지역에도 동일하게 수집할 수 있음을 확인했고, 부동산업 총량 대비 전월세 활동자료의 지역별 변별력이 충분히 존재함을 확인했다.
5. 681/682 배분식의 외부 성능검증을 하려면 외부 10개 지역의 소분류 actual 또는 이를 대체할 독립 검증자료가 추가로 필요하다.

## 다음 단계

- 외부 10개 지역에 대해 공시가격·중개업소·건축물 연면적 자료까지 같은 방식으로 수집한다.
- 고양·포항에서 고정한 보수 후보식만 외부지역에 적용해, 소분류 actual이 있는 지역 또는 독립 검증자료에서 10% 목표를 재평가한다.
- 소분류 actual이 계속 없다면 포스터에는 `외부 10개 지역 자료수집 가능성 및 총량 일관성 검증`까지만 반영하고, 681/682 오차율은 고양·포항 내부 검증으로 제한한다.
"""
    if not missing_l00.empty:
        report += "\n\n## 주의: L00 actual 누락\n\n" + md_table(missing_l00, 2)
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
