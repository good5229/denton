#!/usr/bin/env python3
"""Summarise Phase153 RTMS rent collection for GVA allocation experiments."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase153_rtms_rent_history"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase153_rtms_rent_source_bridge.md"


def md_table(df: pd.DataFrame, floatfmt: str = ".2f") -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    view = view.where(pd.notna(view), "")
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            if pd.api.types.is_float_dtype(view[col]):
                view[col] = view[col].map(lambda x: format(float(x), floatfmt))
            else:
                view[col] = view[col].map(lambda x: f"{int(x):,}")
    view = view.astype(str)
    view = view.replace({"nan": "", "NaN": "", "None": ""})
    return "\n".join(
        [
            "| " + " | ".join(view.columns) + " |",
            "| " + " | ".join(["---"] * len(view.columns)) + " |",
            *["| " + " | ".join(row) + " |" for row in view.to_numpy()],
        ]
    )


def main() -> None:
    rows = pd.read_csv(OUT / "phase153_rtms_rent_rows.csv", encoding="utf-8-sig", dtype=str)
    calls = pd.read_csv(OUT / "phase153_rtms_rent_call_manifest.csv", encoding="utf-8-sig", dtype=str)
    monthly = pd.read_csv(OUT / "phase153_rtms_rent_gu_monthly.csv", encoding="utf-8-sig", dtype=str)
    probe_path = ROOT / "data" / "processed" / "phase152_rtms_nonres_trade_history" / "phase152_rtms_related_api_probe.csv"
    probe = pd.read_csv(probe_path, encoding="utf-8-sig", dtype=str) if probe_path.exists() else pd.DataFrame()

    for c in ["deposit_10k_krw", "monthly_rent_10k_krw", "area_sqm"]:
        rows[c + "_num"] = pd.to_numeric(rows[c], errors="coerce").fillna(0)

    call_summary = pd.DataFrame(
        [
            {
                "호출수": len(calls),
                "정상호출": int(calls["result_code"].eq("000").sum()),
                "실패호출": int((~calls["result_code"].eq("000")).sum()),
                "수집 Row": len(rows),
                "월별 셀": len(monthly),
            }
        ]
    )
    city_summary = (
        rows.groupby(["asset_type", "city"], as_index=False)
        .agg(
            row_count=("period", "size"),
            months=("period", "nunique"),
            deposit_eok=("deposit_10k_krw_num", lambda s: s.sum() / 10000),
            monthly_rent_eok=("monthly_rent_10k_krw_num", lambda s: s.sum() / 10000),
            area_sqm=("area_sqm_num", "sum"),
        )
        .sort_values(["asset_type", "city"])
    )
    city_summary.columns = ["유형", "지역", "Row", "월수", "보증금합계(억원)", "월세합계(억원)", "면적(㎡)"]

    gu_summary = (
        rows.groupby(["asset_type", "city", "general_gu"], as_index=False)
        .agg(
            row_count=("period", "size"),
            months=("period", "nunique"),
            deposit_eok=("deposit_10k_krw_num", lambda s: s.sum() / 10000),
            monthly_rent_eok=("monthly_rent_10k_krw_num", lambda s: s.sum() / 10000),
            area_sqm=("area_sqm_num", "sum"),
        )
        .sort_values(["asset_type", "city", "general_gu"])
    )
    gu_summary.columns = ["유형", "지역", "구", "Row", "월수", "보증금합계(억원)", "월세합계(억원)", "면적(㎡)"]

    year_summary = (
        rows.groupby(["asset_type", "city", "deal_year"], as_index=False)
        .agg(
            row_count=("period", "size"),
            deposit_eok=("deposit_10k_krw_num", lambda s: s.sum() / 10000),
            monthly_rent_eok=("monthly_rent_10k_krw_num", lambda s: s.sum() / 10000),
            area_sqm=("area_sqm_num", "sum"),
        )
        .sort_values(["asset_type", "city", "deal_year"])
    )
    year_summary.columns = ["유형", "지역", "연도", "Row", "보증금합계(억원)", "월세합계(억원)", "면적(㎡)"]

    status = probe[["public_data_pk", "name", "access_status", "http_status", "result_code", "total_count", "url"]].copy() if not probe.empty else pd.DataFrame()
    if not status.empty:
        status.columns = ["ID", "자료명", "상태", "HTTP", "결과코드", "표본 총건수", "링크"]

    manifest = {
        "phase": "phase153_rtms_rent_source_bridge",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_files": [
            "phase153_rtms_rent_rows.csv",
            "phase153_rtms_rent_call_manifest.csv",
            "phase153_rtms_rent_gu_monthly.csv",
        ],
        "output_files": [str(REPORT.relative_to(ROOT))],
        "strict_asof_limit": "행별 공표일자/확정일자 공개시점이 없어 Q+1개월 속보에는 직접 주장하지 않는다.",
    }
    (OUT / "phase153_rtms_rent_source_bridge_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = f"""# Phase153 전월세 실거래 활동자료 수집 및 GVA 연결 메모

## 목적

Phase152에서 상업업무용 매매 실거래를 확보했지만, `681 부동산 임대 및 공급업`을 설명하려면 매매보다 임대차 흐름이 더 직접적이다. 이번 단계는 승인된 RTMS 전월세 API 중 실제 호출 가능한 자료를 수집해 부동산업 내부 배분의 임대흐름 축을 보강한다.

## 자료 출처와 접근상태

{md_table(status)}

현재 수집 완료 자료는 `국토교통부_아파트 전월세 실거래가 자료`다. 오피스텔 및 단독/다가구 전월세는 사용자 신청 완료 후에도 현재 키에서 403으로 남아 있어, 포털 승인 반영 지연 또는 계정/키 반영 문제로 보인다.

## 수집 결과

{md_table(call_summary)}

## 도시별 수집 규모

{md_table(city_summary)}

## 구별 수집 규모

{md_table(gu_summary)}

## 연도별 흐름

{md_table(year_summary)}

## GVA 모델 연결 판단

1. 이 자료는 `부동산업(KSIC 68)` 총량을 직접 대체하지 않는다.
2. `681 부동산 임대 및 공급업`의 임대차 활동축으로 사용 가능하다. 보증금합계, 월세합계, 계약건수, 전용면적이 기존 재고가치·건축물면적 자료를 보완한다.
3. `682 부동산 관련 서비스업`에도 계약건수 중심으로 제한적으로 사용할 수 있지만, 중개업소 수·상업업무용 매매와 결합해야 한다.
4. 행별 공표일자/확정일자 공개시점이 없으므로, 속보성 실험에서는 계약월 자료를 그대로 쓰지 말고 `계약월+보수적 지연` 또는 공식 공표시차 감사를 둬야 한다.
5. 정밀화 실험에서는 Phase150의 2축 모델에 `아파트 전월세 계약건수·보증금·월세`를 임대흐름 축으로 추가해 681/682 소분류 집계검증 오차 변화를 비교한다.

## 다음 작업

- 오피스텔/단독다가구 전월세 API가 200으로 열리면 같은 수집기를 `--apis offi_rent single_multi_rent`로 재실행한다.
- Phase150 2축 후보에 `아파트 전월세 임대흐름`을 추가해 `681/682` 정밀화 오차가 줄어드는지 검증한다.
- 속보성 후보는 행별 공표일자 부재 때문에 “Q+1개월 확정 사용 가능”으로 주장하지 않고, 보수적 lag track을 별도로 만든다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"rows={len(rows)} calls={len(calls)} ok_calls={int(calls['result_code'].eq('000').sum())}")


if __name__ == "__main__":
    main()
