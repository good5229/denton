#!/usr/bin/env python3
"""Phase256: audit source readiness for mining/manufacturing sigungu tails.

Phase255 showed that `광업, 제조업` is the largest absolute-error activity in
the public sigungu annual GVA validation window.  This script does not adopt a
new route.  It checks whether already collected local sources can explain those
tail cells without leakage or overclaiming.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase256_manufacturing_tail_source_readiness.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

TAIL = OUT / "phase255_residual_priority_by_city_activity.csv"
ANNUAL = OUT / "annual_sigungu_activity_error_audit.csv"
MFG_INDEX = ROOT / "data" / "processed" / "phase195_monthly_mining_manufacturing_production_index.csv"
DETAIL_INDEX = ROOT / "data" / "processed" / "phase195_monthly_detail_manufacturing_production_index.csv"
ELEC_FEATURES = ROOT / "data" / "processed" / "municipality_electricity_features_2021_2023.csv"
FACTORY_SNAPSHOT = ROOT / "data" / "raw" / "public_data_portal" / "factory_full_snapshot_15106170_download.csv"


def read_csv_fallback(path: Path, **kwargs) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"failed to read {path}: {last!r}")


def md_table(df: pd.DataFrame, limit: int | None = None, digits: int = 2) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if str(c).lower() == "year":
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else str(int(v)))
        elif pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{float(v):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = [
        "| " + " | ".join(x.columns) + " |",
        "| " + " | ".join(["---"] * len(x.columns)) + " |",
    ]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def province_key(name: object) -> str:
    text = "" if pd.isna(name) else str(name)
    replacements = {
        "강원특별자치도": "강원도",
        "전북특별자치도": "전라북도",
        "세종특별자치시": "세종시",
        "제주특별자치도": "제주도",
    }
    text = replacements.get(text, text)
    return (
        text.replace("특별시", "")
        .replace("광역시", "")
        .replace("특별자치도", "")
        .replace("특별자치시", "")
        .replace("도", "")
        .replace("시", "")
    )


def factory_city_rollup(province: object, city: object) -> str:
    """Align factory-admin units to the sigungu units used by GVA validation.

    Factory snapshots often store ordinary city districts such as `청주시 흥덕구`
    or `포항시 남구`, while the GVA validation table is at `청주시`/`포항시`.
    Metropolitan/autonomous-gu observations such as `서울특별시 강남구` must stay
    at gu level.  Sejong has a blank factory city in the source and is mapped to
    the single-layer `세종시` unit used elsewhere in this project.
    """
    prov = "" if pd.isna(province) else str(province).strip()
    text = "" if pd.isna(city) else str(city).strip()
    if "세종" in prov and not text:
        return "세종시"
    first = text.split()[0] if text else ""
    if first.endswith("시"):
        return first
    return text


def load_tail() -> pd.DataFrame:
    city = pd.read_csv(TAIL)
    mfg = city[city["activity"].eq("광업, 제조업")].copy()
    mfg = mfg.sort_values("abs_error_sum_eok", ascending=False)
    return mfg


def province_index_coverage() -> pd.DataFrame:
    idx = read_csv_fallback(MFG_INDEX)
    idx["prd_de"] = idx["prd_de"].astype(str)
    idx["year"] = idx["prd_de"].str[:4].astype(int)
    idx = idx[idx["c2_nm"].eq("제조업") & idx["item_nm"].astype(str).str.contains("생산지수", na=False)].copy()
    out = (
        idx.groupby("c1_nm", as_index=False)
        .agg(
            mfg_index_months=("prd_de", "nunique"),
            mfg_index_min=("prd_de", "min"),
            mfg_index_max=("prd_de", "max"),
            mfg_index_years=("year", "nunique"),
        )
        .rename(columns={"c1_nm": "province_short"})
    )
    out["province_key"] = out["province_short"].map(province_key)
    return out


def detail_index_summary() -> pd.DataFrame:
    d = read_csv_fallback(DETAIL_INDEX)
    d["prd_de"] = d["prd_de"].astype(str)
    return (
        d.groupby("c1_nm", as_index=False)
        .agg(months=("prd_de", "nunique"), min_period=("prd_de", "min"), max_period=("prd_de", "max"))
        .sort_values(["months", "c1_nm"], ascending=[False, True])
    )


def electricity_coverage() -> pd.DataFrame:
    e = read_csv_fallback(ELEC_FEATURES)
    e["year"] = pd.to_numeric(e["year"], errors="coerce")
    e = e[e["year"].between(2021, 2023)].copy()
    e["province_full"] = e["sido_name_normalized"].astype(str)
    e["city"] = e["sigungu_name_normalized"].astype(str)
    for c in ["electricity_total_kwh", "electricity_industrial_kwh", "electricity_industrial_share"]:
        e[c] = pd.to_numeric(e[c], errors="coerce")
    return (
        e.groupby(["province_full", "city"], as_index=False)
        .agg(
            electricity_months=("observation_period", "nunique"),
            electricity_years=("year", "nunique"),
            industrial_kwh_sum=("electricity_industrial_kwh", "sum"),
            total_kwh_sum=("electricity_total_kwh", "sum"),
            industrial_share_mean=("electricity_industrial_share", "mean"),
            first_publication_date=("source_publication_date", "min"),
            last_publication_date=("source_publication_date", "max"),
            leakage_pass_rows=("leakage_check_passed", lambda s: int((s.astype(str) == "Y").sum())),
        )
    )


def factory_coverage() -> pd.DataFrame:
    f = read_csv_fallback(FACTORY_SNAPSHOT)
    f["province_full"] = f["시도명"].astype(str)
    f["province_key"] = f["province_full"].map(province_key)
    f["city"] = [factory_city_rollup(p, c) for p, c in zip(f["시도명"], f["시군구명"], strict=False)]
    for c in ["종업원합계", "제조시설면적", "용지면적", "건축면적"]:
        f[c] = pd.to_numeric(f.get(c), errors="coerce").fillna(0)
    return (
        f.groupby(["province_key", "city"], as_index=False)
        .agg(
            factory_rows=("회사명", "count"),
            factory_employee_sum=("종업원합계", "sum"),
            factory_mfg_area_sum=("제조시설면적", "sum"),
            factory_land_area_sum=("용지면적", "sum"),
            factory_building_area_sum=("건축면적", "sum"),
            factory_industry_count=("대표업종", "nunique"),
        )
    )


def annual_tail_cells() -> pd.DataFrame:
    a = pd.read_csv(ANNUAL)
    a = a[a["activity"].eq("광업, 제조업")].copy()
    for c in ["predicted_eok", "actual_eok", "abs_error_eok", "ape_pct"]:
        a[c] = pd.to_numeric(a[c], errors="coerce")
    a["large_actual_over10"] = (a["actual_eok"].abs().ge(1000) & a["ape_pct"].gt(10)).astype(int)
    return a


def readiness_label(row: pd.Series) -> str:
    has_index = bool(row.get("mfg_index_months", 0) >= 120)
    has_elec = bool(row.get("electricity_months", 0) >= 36 and row.get("leakage_pass_rows", 0) >= 36)
    has_factory = bool(row.get("factory_rows", 0) > 0)
    if has_index and has_elec and has_factory:
        return "candidate_bundle_ready_for_holdout_design"
    if has_index and (has_elec or has_factory):
        return "partial_bundle_needs_structural_pair"
    if has_index:
        return "time_path_only"
    return "insufficient_local_sources"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tail = load_tail()
    prov_idx = province_index_coverage()
    elec = electricity_coverage()
    factory = factory_coverage()
    annual = annual_tail_cells()
    detail = detail_index_summary()

    # province_short is already the short KOSIS region label, while tail has full
    # province names.  Normalize special-province names before joining so that
    # Sejong/Jeonbuk/Gangwon/Jeju are not silently dropped.
    tail["province_key"] = tail["province_full"].map(province_key)

    joined = (
        tail.merge(prov_idx.drop(columns=["province_short"]), on="province_key", how="left")
        .merge(elec, on=["province_full", "city"], how="left")
        .merge(factory, on=["province_key", "city"], how="left")
    )
    for c in [
        "mfg_index_months",
        "electricity_months",
        "electricity_years",
        "industrial_kwh_sum",
        "total_kwh_sum",
        "industrial_share_mean",
        "leakage_pass_rows",
        "factory_rows",
        "factory_employee_sum",
        "factory_mfg_area_sum",
        "factory_industry_count",
    ]:
        if c in joined:
            joined[c] = pd.to_numeric(joined[c], errors="coerce").fillna(0)
    joined["source_readiness"] = joined.apply(readiness_label, axis=1)
    joined["route_adoption_status"] = "not_adopted_source_readiness_only"
    joined["sigungu_unit"] = joined["province_full"].astype(str) + " " + joined["city"].astype(str)

    cells = annual.merge(
        joined[
            [
                "province_full",
                "city",
                "mfg_index_months",
                "electricity_months",
                "electricity_years",
                "industrial_kwh_sum",
                "industrial_share_mean",
                "leakage_pass_rows",
                "factory_rows",
                "factory_employee_sum",
                "factory_mfg_area_sum",
                "source_readiness",
            ]
        ],
        on=["province_full", "city"],
        how="left",
    )

    readiness_summary = (
        joined.groupby("source_readiness", as_index=False)
        .agg(
            city_activity_groups=("city", "size"),
            city_count=("sigungu_unit", "nunique"),
            actual_sum_eok=("actual_sum_eok", "sum"),
            abs_error_sum_eok=("abs_error_sum_eok", "sum"),
            over10_cells=("over10_cells", "sum"),
            over20_cells=("over20_cells", "sum"),
            large_actual_over10_cells=("large_actual_over10_cells", "sum"),
        )
        .sort_values("abs_error_sum_eok", ascending=False)
    )
    readiness_summary["wape_pct"] = readiness_summary["abs_error_sum_eok"] / readiness_summary["actual_sum_eok"].abs() * 100

    top_joined = joined.sort_values("abs_error_sum_eok", ascending=False).head(30).copy()
    large_cells = cells[cells["large_actual_over10"].eq(1)].sort_values("abs_error_eok", ascending=False).head(50)

    joined.to_csv(OUT / "phase256_manufacturing_tail_source_readiness_by_city.csv", index=False, encoding="utf-8-sig")
    readiness_summary.to_csv(OUT / "phase256_manufacturing_tail_source_readiness_summary.csv", index=False, encoding="utf-8-sig")
    cells.to_csv(OUT / "phase256_manufacturing_tail_source_readiness_cells.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase256_manufacturing_detail_index_coverage.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase256 광업·제조업 tail 자료준비도 감사

생성시각: {CREATED_AT}

## 1. 목적

Phase255에서 `광업, 제조업`은 시군구×업종 공개 actual 구간의 절대오차 1위로 확인됐다. 이번 감사는 새 route를 채택하는 실험이 아니라, 이미 로컬에 있는 제조업 생산지수·전력·공장등록 자료가 이 tail을 설명할 준비가 되어 있는지 점검한다.

## 2. 자료별 역할 판정

| 자료 | 로컬 coverage | 역할 | 운영 채택 여부 |
| --- | --- | --- | --- |
| 시도별 월간 제조업 생산지수 | 2015-01~2025-05, 2020=100 | 제조업 C00 월별 시간경로 | 시간경로 후보로 사용 가능 |
| 전국 세부 제조업 생산지수 | 2020-01~2025-05, 일부 항목 | 중분류 시간경로 후보 | 지역 차원이 없어 시군구 공간배분 단독 근거 금지 |
| 시군구 전력사용량 historical feature | 2021~2023 주요 검증 구간 | 지역 규모·전력집약도 보조 | 전력 단독 route 미채택, 구조자료와 결합 후보 |
| 공장등록 snapshot | 현재 스냅샷, 일반구는 시 단위 roll-up | 시군구 제조업 규모·업종구성 보조 | 등록일/vintage 불완전, 단독 route 미채택 |

## 3. 세부 제조업 생산지수 coverage

{md_table(detail, digits=0)}

## 4. 자료준비도별 tail 규모

{md_table(readiness_summary[["source_readiness", "city_activity_groups", "city_count", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "large_actual_over10_cells"]], digits=2)}

## 5. 광업·제조업 시군구 tail 상위와 자료 연결 상태

{md_table(top_joined[["province_full", "city", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "large_actual_over10_cells", "mfg_index_months", "electricity_months", "industrial_share_mean", "factory_rows", "factory_employee_sum", "factory_mfg_area_sum", "source_readiness"]], digits=2)}

## 6. 대형 actual·10% 초과 제조업 셀

{md_table(large_cells[["province_full", "city", "year", "actual_eok", "predicted_eok", "abs_error_eok", "ape_pct", "electricity_months", "industrial_share_mean", "factory_rows", "factory_employee_sum", "source_readiness"]], limit=20, digits=2)}

## 7. 판정

1. 시도별 월간 제조업 생산지수는 제조업 GVA의 월별 시간경로에는 필수지만, 시군구 내부 구조를 바꾸는 자료가 아니다.
2. 전국 세부 제조업 생산지수는 일부 항목만 있고 지역 차원이 없으므로 중분류 시간경로 후보일 뿐, 대형 제조업 도시의 공간배분 단독 근거가 아니다.
3. 시군구 전력과 공장등록은 광업·제조업 tail 대부분에 연결된다. 단, 공장등록은 일반구를 시 단위로 합친 현재 snapshot이므로 과거연도 속보자료로 직접 쓰면 안 되고, 기존 전력 단독·공장 단독 실험도 운영 gate를 통과하지 못했다.
4. 따라서 현 단계의 제조업 tail 대부분은 `candidate_bundle_ready_for_holdout_design`이며, 이는 route 채택 상태가 아니라 holdout 검증 설계를 시작할 수 있다는 뜻이다.
5. 다음 실험은 top-error 셀에서 바로 성능을 주장하지 말고, 제조업 대형 도시를 discovery/holdout으로 분리한 뒤 `월간 생산지수 × 전력집약도 × 공장규모` 묶음의 out-of-year 또는 holdout-city 검증으로 진행해야 한다.

## 8. 금지 해석

- 월간 제조업 생산지수 반영을 중분류·시군구 구조 개선으로 표현하지 않는다.
- 현재 공장등록 snapshot을 2021~2023 당시의 정확한 공장 stock으로 표현하지 않는다.
- 전력 단독 feature를 운영 route로 채택했다고 표현하지 않는다.
- Phase255의 top-error 도시를 보고 만든 가중치를 같은 도시·같은 연도에서 성과로 보고하지 않는다.

## 9. 다음 수집·검증 우선순위

1. 공장등록의 등록일·폐업/휴업·변경이력 또는 연도별 snapshot 확보.
2. 제조업 중분류별 출하액·부가가치·종사자·급여액의 시군구 또는 산업단지 단위 자료 확보.
3. 대형 제조업 도시(화성·이천·평택·구미·서산 등)는 공장규모와 전력집약도 interaction 후보를 사전 고정한 뒤 holdout 검증.
4. 포항·울산·인천 등 항만/중화학 비중이 큰 도시는 항만 품목 물동량·대형사업장 자료를 별도 후보로 유지.

## 10. 산출물

- `nationwide/outputs/phase256_manufacturing_tail_source_readiness_by_city.csv`
- `nationwide/outputs/phase256_manufacturing_tail_source_readiness_summary.csv`
- `nationwide/outputs/phase256_manufacturing_tail_source_readiness_cells.csv`
- `nationwide/outputs/phase256_manufacturing_detail_index_coverage.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(readiness_summary.to_string(index=False))


if __name__ == "__main__":
    main()
