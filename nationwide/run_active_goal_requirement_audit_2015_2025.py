#!/usr/bin/env python3
"""Requirement audit for the active 2015-2025 nationwide goal.

The active goal is broader than the already finished nationwide GRDP
validation.  This audit deliberately separates:

* evidence-backed completed layers,
* layers that are feasible only for a narrower publication window, and
* layers blocked by API/source availability.

It should be read as a continuation map, not as a completion certificate.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = HERE / "active_goal_requirement_audit_2015_2025.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

SOURCE_COVERAGE = OUT / "source_coverage_audit_2015_2025.csv"
SIGUNGU_ANNUAL = OUT / "annual_sigungu_gva_normalized.csv"
SIDO_GRDP_VALIDATION = OUT / "operating_point_sido_grdp_validation.csv"
NATIONAL_BOUNDARY = OUT / "national_gdp_yearly_summary.csv"
ACTIVITY_VALIDATION = OUT / "sido_activity_quarterly_validation.csv"
LONG_WINDOW_SUMMARY = OUT / "sido_long_window_operating_summary.csv"
MONTHLY_BRIDGE_SUMMARY = OUT / "monthly_bridge_summary.csv"


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if str(c).lower() in {"year", "years", "available_quarters"}:
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else str(int(x)) if float(x).is_integer() else str(x))
        elif pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = [
        "| " + " | ".join(v.columns) + " |",
        "| " + " | ".join(["---"] * len(v.columns)) + " |",
    ]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def source_summary() -> pd.DataFrame:
    df = pd.read_csv(SOURCE_COVERAGE)
    return (
        df.groupby("coverage_status", as_index=False)
        .agg(source_count=("source_id", "count"), rows=("rows", "sum"))
        .sort_values(["coverage_status"])
    )


def sigungu_publication_matrix() -> pd.DataFrame:
    annual = pd.read_csv(SIGUNGU_ANNUAL)
    activity_count = annual["activity_group"].nunique()
    matrix = (
        annual.groupby(["quarter_region", "province_full", "year"], as_index=False)
        .agg(
            sigungu_count=("city", "nunique"),
            activity_count=("activity_group", "nunique"),
            rows=("annual_gva_eok", "size"),
            latest_change_date=("latest_change_date", "max"),
        )
        .sort_values(["quarter_region", "year"])
    )
    # Add expected activity count so the audit can distinguish a missing year
    # from a present-but-partial industry table.
    matrix["expected_activity_count_in_local_source"] = activity_count
    matrix["table_shape_status"] = matrix.apply(
        lambda r: "activity_complete_for_local_schema"
        if int(r["activity_count"]) == int(r["expected_activity_count_in_local_source"])
        else "activity_partial_for_local_schema",
        axis=1,
    )
    return matrix


def validation_summary() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sido = pd.read_csv(SIDO_GRDP_VALIDATION)
    by_track = (
        sido.groupby(["track", "available_quarters", "operating_label"], as_index=False)
        .agg(
            validation_rows=("annualized_ape_pct", "size"),
            annualized_wape_pct=(
                "annualized_error_eok",
                lambda s: 0.0,
            ),
        )
    )
    # Recompute WAPE from errors and actuals; the lambda above is overwritten
    # to avoid relying on a precomputed summary file with unknown freshness.
    by_track = (
        sido.assign(abs_annualized_error_eok=sido["annualized_error_eok"].abs())
        .groupby(["track", "available_quarters", "operating_label"], as_index=False)
        .agg(
            validation_rows=("annualized_ape_pct", "size"),
            abs_error_sum_eok=("abs_annualized_error_eok", "sum"),
            actual_sum_eok=("official_annual_grdp_eok", "sum"),
            max_ape_pct=("annualized_ape_pct", "max"),
        )
    )
    by_track["annualized_wape_pct"] = by_track["abs_error_sum_eok"] / by_track["actual_sum_eok"] * 100
    by_track = by_track[
        [
            "track",
            "available_quarters",
            "operating_label",
            "validation_rows",
            "annualized_wape_pct",
            "max_ape_pct",
        ]
    ].sort_values(["track", "available_quarters"])

    national = pd.read_csv(NATIONAL_BOUNDARY)
    national_wape_col = (
        "national_boundary_wape_pct"
        if "national_boundary_wape_pct" in national.columns
        else "national_wape_pct"
    )
    national_summary = (
        national.groupby("track", as_index=False)
        .agg(
            years=("year", "nunique"),
            national_boundary_wape_mean_pct=(national_wape_col, "mean"),
            national_boundary_wape_max_pct=(national_wape_col, "max"),
        )
        .sort_values("track")
    )

    activity = pd.read_csv(ACTIVITY_VALIDATION)
    activity_summary = (
        activity.assign(abs_error_eok=activity["error_eok"].abs())
        .groupby(["track", "activity"], as_index=False)
        .agg(
            rows=("ape_pct", "size"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            actual_sum_eok=("official_value_eok", lambda s: s.abs().sum()),
            max_ape_pct=("ape_pct", "max"),
            over_10pct_cells=("ape_pct", lambda s: int((s > 10).sum())),
        )
    )
    activity_summary["activity_wape_pct"] = activity_summary["abs_error_sum_eok"] / activity_summary["actual_sum_eok"] * 100
    activity_summary = activity_summary.sort_values(["activity_wape_pct", "max_ape_pct"], ascending=False)
    return by_track, national_summary, activity_summary


def pps_status() -> dict[str, object]:
    cov = pd.read_csv(SOURCE_COVERAGE)
    row = cov[cov["source_id"].eq("pps_contract_info")]
    if row.empty:
        return {"status": "missing_from_source_coverage"}
    r = row.iloc[0].to_dict()
    def fmt_intish(value: object) -> object:
        try:
            if pd.isna(value):
                return ""
            f = float(value)
            return str(int(f)) if f.is_integer() else value
        except Exception:
            return value

    return {
        "coverage_status": r.get("coverage_status"),
        "period_min": r.get("period_min"),
        "period_max": r.get("period_max"),
        "pps_months_complete": fmt_intish(r.get("pps_months_complete")),
        "pps_adoptable_years": fmt_intish(r.get("pps_adoptable_years")),
        "pps_first_incomplete_period": fmt_intish(r.get("pps_first_incomplete_period")),
    }


def requirement_rows(
    source_counts: pd.DataFrame,
    sigungu_matrix: pd.DataFrame,
    sido_summary: pd.DataFrame,
    national_summary: pd.DataFrame,
    pps: dict[str, object],
) -> pd.DataFrame:
    direct_coverage_count = int(source_counts[source_counts["coverage_status"].eq("covers_2015_2025")]["source_count"].sum())
    sigungu_year_min = int(sigungu_matrix["year"].min())
    sigungu_year_max = int(sigungu_matrix["year"].max())
    sigungu_provinces = int(sigungu_matrix["quarter_region"].nunique())
    status_rows = [
        {
            "requirement": "2015~2025 사용자료 전체 수집",
            "current_status": "partial",
            "evidence": f"{direct_coverage_count}개 자료군은 2015~2025 직접 coverage, PPS={pps.get('coverage_status')}, 시군구 GVA actual={sigungu_year_min}~{sigungu_year_max}",
            "next_action": "PPS API 쿨다운 후 건설 공사계약 전량 수집; 시군구 actual 공표 공백은 상위 집계검증으로 분리 표기",
        },
        {
            "requirement": "기준연도 다른 지수 조정",
            "current_status": "satisfied_for_current_local_inputs",
            "evidence": "coverage audit상 주요 생산·서비스 지수는 2020=100 소급계열, index_base_bridge=metadata_ok",
            "next_action": "legacy 2015=100 계열 추가 시 bridge-year 재기준화 후 투입",
        },
        {
            "requirement": "전국 17개 시도 분기/연간환산 검증",
            "current_status": "satisfied",
            "evidence": f"{int(sido_summary['validation_rows'].sum())}개 시도×연도×운영시점 검증행, 전국경계 {int(national_summary['years'].max())}개년",
            "next_action": "해석은 최신 빈티지 사후 백테스트로 제한",
        },
        {
            "requirement": "2015~2025 장기 시도 안정성 검증",
            "current_status": "satisfied_with_initialization_limit",
            "evidence": long_window_evidence(),
            "next_action": "2015년은 전년도 기준값이 없어 초기화 연도로 표기; 성능 검증은 2016~2025로 유지",
        },
        {
            "requirement": "전국 시군구×업종 월별 산출",
            "current_status": "partial_bridge_2021_2025",
            "evidence": monthly_bridge_evidence(),
            "next_action": "월별 actual 검증이 아니라 분기 재집계 보존형 bridge로 표기; 2015~2020 시군구 월별 산출은 별도 기준값 필요",
        },
        {
            "requirement": "전국 시군구×업종 전기간 직접 actual 검증",
            "current_status": "not_satisfied_due_publication_scope",
            "evidence": f"시군구 actual 로컬 공표범위 {sigungu_year_min}~{sigungu_year_max}, 공표 시도 {sigungu_provinces}개",
            "next_action": "공표된 연도는 직접검증, 2024~2025 및 미공표 시도는 시도·전국 상위 actual 집계검증으로 대체",
        },
        {
            "requirement": "건설업 직접 활동자료 route 전국 채택",
            "current_status": "blocked_by_pps_api_quota",
            "evidence": f"PPS first incomplete={pps.get('pps_first_incomplete_period')}, adoptable_years={pps.get('pps_adoptable_years')}",
            "next_action": "429 해제 후 월/일 단위 재개; quality_complete 연도만 rolling 검증에 투입",
        },
        {
            "requirement": "과학자/평가자 검증",
            "current_status": "in_progress",
            "evidence": "현재 evaluator/scientist agent 검토 요청 진행 중",
            "next_action": "회신 반영 후 requirement audit와 상태 문서 갱신",
        },
    ]
    return pd.DataFrame(status_rows)


def long_window_evidence() -> str:
    if not LONG_WINDOW_SUMMARY.exists():
        return "sido_long_window_operating_summary.csv 없음"
    d = pd.read_csv(LONG_WINDOW_SUMMARY)
    best = d[(d["track"].eq("prior_year_province_anchor")) & (d["available_quarters"].eq(1))]
    if best.empty:
        return f"{len(d)}개 장기검증 요약행 존재"
    r = best.iloc[0]
    return (
        f"2016~2025 {int(r['years'])}개년×{int(r['regions'])}개 시도, "
        f"Q1 연간환산 WAPE={float(r['annualized_wape_pct']):.3f}%, "
        f"최대오차율={float(r['annualized_max_ape_pct']):.3f}%"
    )


def monthly_bridge_evidence() -> str:
    if not MONTHLY_BRIDGE_SUMMARY.exists():
        return "monthly_bridge_summary.csv 없음"
    d = pd.read_csv(MONTHLY_BRIDGE_SUMMARY)
    if d.empty:
        return "monthly_bridge_summary.csv 비어 있음"
    r = d.iloc[0]
    return (
        f"{int(r['years_min'])}~{int(r['years_max'])}, {int(r['monthly_rows']):,}행, "
        f"월별지표 적용 {float(r['indicator_rows_pct']):.3f}%, "
        f"분기 재집계 오류셀 {int(r['bad_quarter_cells_gt_1won_equiv'])}개"
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source_counts = source_summary()
    sigungu_matrix = sigungu_publication_matrix()
    sido_summary, national_summary, activity_summary = validation_summary()
    pps = pps_status()
    requirements = requirement_rows(source_counts, sigungu_matrix, sido_summary, national_summary, pps)

    source_counts.to_csv(OUT / "active_goal_requirement_source_counts.csv", index=False, encoding="utf-8-sig")
    sigungu_matrix.to_csv(OUT / "active_goal_sigungu_actual_publication_matrix.csv", index=False, encoding="utf-8-sig")
    sido_summary.to_csv(OUT / "active_goal_sido_validation_summary.csv", index=False, encoding="utf-8-sig")
    national_summary.to_csv(OUT / "active_goal_national_boundary_summary.csv", index=False, encoding="utf-8-sig")
    activity_summary.to_csv(OUT / "active_goal_activity_validation_summary.csv", index=False, encoding="utf-8-sig")
    requirements.to_csv(OUT / "active_goal_requirement_audit_2015_2025.csv", index=False, encoding="utf-8-sig")

    top_activity = activity_summary.head(12)[
        ["track", "activity", "rows", "activity_wape_pct", "max_ape_pct", "over_10pct_cells"]
    ]
    sigungu_years = (
        sigungu_matrix.groupby("year", as_index=False)
        .agg(
            province_count=("quarter_region", "nunique"),
            sigungu_count=("sigungu_count", "sum"),
            rows=("rows", "sum"),
        )
        .sort_values("year")
    )

    md = f"""# 2015~2025 전국 목표 요구사항 감사

생성시각: {CREATED_AT}

## 판정 요약

이 문서는 현재 `/goal`의 완료 증명서가 아니라, 남은 요구사항을 숨기지 않기 위한 진행 감사다. 현재 산출물은 `시도·전국 상위 경계 검증`과 `사용자료 coverage/기준연도 감사`까지는 강한 증거가 있으나, `2015~2025 전기간 시군구×업종 직접 actual 검증`은 공표자료 범위상 아직 완료로 볼 수 없다.

## 요구사항별 현재 상태

{md_table(requirements, digits=3)}

## 사용자료 coverage 요약

{md_table(source_counts, digits=0)}

## 시군구 annual actual 공표 범위

{md_table(sigungu_years, digits=0)}

## 시도 분기/연간환산 검증 요약

{md_table(sido_summary, digits=3)}

## 전국 GDP/GRDP 경계 요약

{md_table(national_summary, digits=3)}

## 업종별 잔여 오차 상위

{md_table(top_activity, digits=3)}

## 운영 결론

- 현 상태는 `전국 17개 시도 총량 모니터링`에는 사용 가능한 후보 체계다.
- `시군구×업종`은 공표연도 직접검증과 상위 집계검증을 병행해야 하며, 2015~2025 전기간 직접검증으로 표현하면 안 된다.
- 건설업은 PPS 전량 수집과 품질게이트가 끝나기 전에는 전국 route로 채택하지 않는다.
- 활동지표 route는 업종별 잔여오차 축소 후보지만, 자동채택이 아니라 rolling out-of-year gate 통과분만 채택한다.

## 산출물

- `nationwide/outputs/active_goal_requirement_audit_2015_2025.csv`
- `nationwide/outputs/active_goal_requirement_source_counts.csv`
- `nationwide/outputs/active_goal_sigungu_actual_publication_matrix.csv`
- `nationwide/outputs/active_goal_sido_validation_summary.csv`
- `nationwide/outputs/active_goal_national_boundary_summary.csv`
- `nationwide/outputs/active_goal_activity_validation_summary.csv`
"""
    REPORT.write_text(md, encoding="utf-8")
    print(REPORT)
    print(requirements.to_string(index=False))


if __name__ == "__main__":
    main()
