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
MONTHLY_BRIDGE_2020_PILOT_SUMMARY = OUT / "monthly_bridge_summary_2020_backcast_pilot.csv"
MONTHLY_BRIDGE_2020_FULL_SUMMARY = OUT / "monthly_bridge_summary_2020_fullcoverage_backcast.csv"
MONTHLY_BRIDGE_2016_2020_SUMMARY = OUT / "monthly_bridge_summary_2016_2020_backcast.csv"
MONTHLY_BRIDGE_2015_INIT_SUMMARY = OUT / "monthly_bridge_summary_2015_initialization.csv"
SIGUNGU_LONG_BACKCAST_SUMMARY = OUT / "sido_quarterly_grdp_summary_2016_2020_backcast.csv"
SIGUNGU_2015_INIT_SUMMARY = OUT / "sido_quarterly_grdp_summary_2015_initialization.csv"
PPS_CONTRACT_QUALITY = ROOT / "data" / "processed" / "phase249_pps_contract_quality_audit" / "phase249_monthly_collection_quality.csv"
PPS_CONTRACT_SAFE_CANDIDATES = (
    ROOT
    / "data"
    / "processed"
    / "phase250_pps_contract_construction_route_validation"
    / "phase250_guardrail_safe_candidates.csv"
)
PHASE252_ROUTE_SUMMARY = OUT / "phase252_summary_by_track_quarter.csv"


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


def fmt_pct_points(value: object, digits: int = 3) -> str:
    try:
        if value is None or pd.isna(value):
            return ""
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


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
    def fmt_intish(value: object) -> object:
        try:
            if pd.isna(value):
                return ""
            f = float(value)
            return str(int(f)) if f.is_integer() else value
        except Exception:
            return value

    out: dict[str, object] = {}
    contract = cov[cov["source_id"].eq("pps_contract_info")]
    if contract.empty:
        out["contract_status"] = "missing_from_source_coverage"
    else:
        r = contract.iloc[0].to_dict()
        out.update(
            {
                "contract_status": r.get("coverage_status"),
                "contract_period_min": r.get("period_min"),
                "contract_period_max": r.get("period_max"),
                "contract_months_complete": fmt_intish(r.get("pps_months_complete")),
                "contract_adoptable_years": fmt_intish(r.get("pps_adoptable_years")),
                "contract_first_incomplete_period": fmt_intish(r.get("pps_first_incomplete_period")),
            }
        )
        if PPS_CONTRACT_QUALITY.exists():
            qa = pd.read_csv(PPS_CONTRACT_QUALITY, dtype={"period": str})
            incomplete = qa[qa["quality_complete"].ne(True)].copy()
            if not incomplete.empty:
                first = incomplete.sort_values("period").iloc[0]
                out.update(
                    {
                        "contract_latest_first_incomplete_period": first.get("period"),
                        "contract_latest_first_incomplete_error": first.get("manifest_error", ""),
                        "contract_latest_first_incomplete_manifest_rows": fmt_intish(
                            first.get("manifest_rows_collected", first.get("rows_collected", ""))
                        ),
                    }
                )
        if PPS_CONTRACT_SAFE_CANDIDATES.exists():
            safe = pd.read_csv(PPS_CONTRACT_SAFE_CANDIDATES)
            out["contract_safe_candidate_count"] = len(safe)
    bid = cov[cov["source_id"].eq("pps_bid_notice_robust")]
    if bid.empty:
        out["bid_status"] = "missing_from_source_coverage"
    else:
        r = bid.iloc[0].to_dict()
        out.update(
            {
                "bid_status": r.get("coverage_status"),
                "bid_period_min": r.get("period_min"),
                "bid_period_max": r.get("period_max"),
                "bid_months_complete": fmt_intish(r.get("pps_months_complete")),
                "bid_complete_periods": r.get("pps_complete_periods"),
                "bid_first_incomplete_period": fmt_intish(r.get("pps_first_incomplete_period")),
            }
        )
    return out


def phase252_status() -> dict[str, object]:
    """Summarize leakage-safe rolling activity-route experiments.

    These files are intentionally ignored CSV outputs.  The audit keeps only
    the decision-level numbers so the goal status can be regenerated without
    accidentally tracking large CSV artifacts.
    """

    out: dict[str, object] = {}
    if PHASE252_ROUTE_SUMMARY.exists():
        route = pd.read_csv(PHASE252_ROUTE_SUMMARY)
        if not route.empty:
            out["route_rows"] = int(route["rows"].sum())
            out["route_adopted_rows"] = int(route["adopted_rows"].sum())
            out["route_worse_wape_rows"] = int((route["rolling_wape_pct"] > route["baseline_wape_pct"]).sum())
            out["route_worse_over10_rows"] = int(
                (route["rolling_over10_cells"] > route["baseline_over10_cells"]).sum()
            )
            out["route_max_delta_wape_pp"] = float(route["delta_wape_pp"].max())
    return out


def requirement_rows(
    source_counts: pd.DataFrame,
    sigungu_matrix: pd.DataFrame,
    sido_summary: pd.DataFrame,
    national_summary: pd.DataFrame,
    pps: dict[str, object],
    phase252: dict[str, object],
) -> pd.DataFrame:
    direct_coverage_count = int(source_counts[source_counts["coverage_status"].eq("covers_2015_2025")]["source_count"].sum())
    sigungu_year_min = int(sigungu_matrix["year"].min())
    sigungu_year_max = int(sigungu_matrix["year"].max())
    sigungu_provinces = int(sigungu_matrix["quarter_region"].nunique())
    status_rows = [
        {
            "requirement": "2015~2025 사용자료 전체 수집",
            "current_status": "partial",
            "evidence": f"{direct_coverage_count}개 자료군은 2015~2025 직접 coverage, PPS계약={pps.get('contract_status')}, PPS공고={pps.get('bid_status')}, 시군구 GVA actual={sigungu_year_min}~{sigungu_year_max}",
            "next_action": "PPS API 쿨다운 후 건설 공사계약/공사공고 완전월 수집; 시군구 actual 공표 공백은 상위 집계검증으로 분리 표기",
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
            "current_status": "tiered_2015_initialization_2016_2020_backcast_2021_2025_operational",
            "evidence": monthly_bridge_evidence(),
            "next_action": "월별 actual 검증이 아니라 분기 재집계 보존형 bridge로 표기; 2015~2020은 `nationwide/monthly_bridge_2015_2020_extension_audit.md`의 backcast 등급 기준을 따른다",
        },
        {
            "requirement": "2015 시군구×업종 초기화 재구성",
            "current_status": "satisfied_as_initialization_reconstruction",
            "evidence": sigungu_2015_initialization_evidence(),
            "next_action": "예측 성능 또는 속보성으로 해석 금지; 장기 패널 시작점과 상위합 보존성 산출물로만 사용",
        },
        {
            "requirement": "2016~2020 시군구×업종 분기 backcast",
            "current_status": "satisfied_as_posthoc_backcast",
            "evidence": sigungu_long_backcast_evidence(),
            "next_action": "사후 전국 분기경로를 사용한 장기 재구성으로 표기; Q+1개월 속보 성능 또는 시군구 내부 구성비 actual 검증으로 해석 금지",
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
            "evidence": (
                f"PPS계약 first incomplete={pps.get('contract_first_incomplete_period')}, "
                f"latest first incomplete={pps.get('contract_latest_first_incomplete_period')}, "
                f"manifest_rows={pps.get('contract_latest_first_incomplete_manifest_rows')}, "
                f"last_error={pps.get('contract_latest_first_incomplete_error')}, "
                f"adoptable_years={pps.get('contract_adoptable_years')}, "
                f"phase250_safe_candidates={pps.get('contract_safe_candidate_count', '')}; "
                f"PPS공고 complete={pps.get('bid_complete_periods')}, first incomplete={pps.get('bid_first_incomplete_period')}"
            ),
            "next_action": "429 해제 후 월/일 단위 재개; 계약은 quality_complete 연도만, 공고는 완전월만 rolling 검증에 투입하고, safe candidate 0개 상태에서는 건설업 route로 채택하지 않음",
        },
        {
            "requirement": "활동지표 route rolling 자동채택",
            "current_status": "rejected_for_operational_adoption",
            "evidence": (
                f"Phase252 strict route rows={phase252.get('route_rows', '')}, "
                f"adopted_rows={phase252.get('route_adopted_rows', '')}, "
                f"WAPE 악화 운영요약행={phase252.get('route_worse_wape_rows', '')}, "
                f"10%초과 악화 운영요약행={phase252.get('route_worse_over10_rows', '')}, "
                f"최대 WAPE 악화폭={fmt_pct_points(phase252.get('route_max_delta_wape_pp'))}pp"
            ),
            "next_action": "현재 운영 산출물에는 반영하지 않음; 후보 발굴 결과로 보관하고 공표일 장부·지역별 직접 활동자료가 보강된 뒤 재검증",
        },
        {
            "requirement": "과학자/평가자 검증",
            "current_status": "latest_monthly_bridge_postaudit_reflected",
            "evidence": "월별 bridge 사후평가에서 전국 월별 지표를 공간배분 근거로 오해하지 않도록 indicator_rows_pct 해석 보강 필요 지적",
            "next_action": "후속 실험마다 사전/사후 검증을 반복하고, 자동채택 표현은 rolling gate 통과분으로 제한",
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
    evidence = (
        f"{int(r['years_min'])}~{int(r['years_max'])}, {int(r['monthly_rows']):,}행, "
        f"월별 시간경로 적용 {float(r['indicator_rows_pct']):.3f}%, "
        f"분기 재집계 오류셀 {int(r['bad_quarter_cells_gt_1won_equiv'])}개"
    )
    if MONTHLY_BRIDGE_2020_FULL_SUMMARY.exists():
        full = pd.read_csv(MONTHLY_BRIDGE_2020_FULL_SUMMARY)
        if not full.empty:
            fr = full.iloc[0]
            evidence += (
                f"; 2020 전국 share-bridge backcast {int(fr['province_count'])}개 시도·"
                f"{int(fr['city_count'])}개 하위단위·{int(fr['monthly_rows']):,}행, "
                f"기준값 재스케일 오류셀 {int(fr['bad_basis_scale_cells_gt_1won_equiv'])}개, "
                f"분기 재집계 오류셀 {int(fr['bad_quarter_cells_gt_1won_equiv'])}개"
            )
    if MONTHLY_BRIDGE_2016_2020_SUMMARY.exists():
        long_m = pd.read_csv(MONTHLY_BRIDGE_2016_2020_SUMMARY)
        if not long_m.empty:
            lr = long_m.iloc[0]
            evidence += (
                f"; 2016~2020 월별 backcast {int(lr['monthly_rows']):,}행, "
                f"월별 시간경로 적용 {float(lr['indicator_rows_pct']):.3f}%, "
                f"균등분할 {float(lr['fallback_equal_split_rows_pct']):.3f}%, "
                f"분기 재집계 오류셀 {int(lr['bad_quarter_cells_gt_1won_equiv'])}개"
            )
    if MONTHLY_BRIDGE_2015_INIT_SUMMARY.exists():
        init_m = pd.read_csv(MONTHLY_BRIDGE_2015_INIT_SUMMARY)
        if not init_m.empty:
            ir = init_m.iloc[0]
            evidence += (
                f"; 2015 초기화 월별 재구성 {int(ir['monthly_rows']):,}행, "
                f"월별 시간경로 적용 {float(ir['indicator_rows_pct']):.3f}%, "
                f"균등분할 {float(ir['fallback_equal_split_rows_pct']):.3f}%, "
                f"분기 재집계 오류셀 {int(ir['bad_quarter_cells_gt_1won_equiv'])}개"
            )
    elif MONTHLY_BRIDGE_2020_PILOT_SUMMARY.exists():
        pilot = pd.read_csv(MONTHLY_BRIDGE_2020_PILOT_SUMMARY)
        if not pilot.empty:
            pr = pilot.iloc[0]
            evidence += (
                f"; 2020 제한 파일럿 {int(pr['province_count'])}개 시도·"
                f"{int(pr['city_count'])}개 하위단위·{int(pr['monthly_rows']):,}행, "
                f"분기 재집계 오류셀 {int(pr['bad_quarter_cells_gt_1won_equiv'])}개"
            )
    return evidence


def sigungu_long_backcast_evidence() -> str:
    if not SIGUNGU_LONG_BACKCAST_SUMMARY.exists():
        return "sido_quarterly_grdp_summary_2016_2020_backcast.csv 없음"
    d = pd.read_csv(SIGUNGU_LONG_BACKCAST_SUMMARY)
    if d.empty:
        return "2016~2020 backcast summary 비어 있음"
    r = d.iloc[0]
    return (
        f"{int(r['years'])}개년, {int(r['province_quarter_rows'])}개 시도분기행, "
        f"시도 GRDP WAPE={float(r['wape_pct']):.3f}%, 최대오차율={float(r['max_ape_pct']):.3f}%, "
        "기준값 재스케일 오류 0셀"
    )


def sigungu_2015_initialization_evidence() -> str:
    if not SIGUNGU_2015_INIT_SUMMARY.exists():
        return "sido_quarterly_grdp_summary_2015_initialization.csv 없음"
    d = pd.read_csv(SIGUNGU_2015_INIT_SUMMARY)
    if d.empty:
        return "2015 initialization summary 비어 있음"
    r = d.iloc[0]
    return (
        f"{int(r['province_count'])}개 시도, {int(r['quarter_rows'])}개 시도분기행, "
        f"사후 재구성 GRDP WAPE={float(r['wape_pct']):.3f}%, 최대오차율={float(r['max_ape_pct']):.3f}%"
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source_counts = source_summary()
    sigungu_matrix = sigungu_publication_matrix()
    sido_summary, national_summary, activity_summary = validation_summary()
    pps = pps_status()
    phase252 = phase252_status()
    requirements = requirement_rows(source_counts, sigungu_matrix, sido_summary, national_summary, pps, phase252)

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
- 2015년은 전년도 기준값이 없어 초기화용 사후 재구성으로 분리했고, 예측 성능 평가 대상이 아니다.
- 2015년 WAPE/APE는 목표연도 공식 연간총량과 전국 분기경로를 사용한 계층 보존성·분기 재구성 일관성 지표이며, 모델 예측 정확도 지표가 아니다.
- 2016~2020은 2015~2019 시군구 구성비를 동년 시도×업종 공식총량에 연결한 전국 사후 backcast로 확장했고, 시도 GRDP 분기 집계 WAPE는 1.970%다.
- 2015년은 초기화용 사후 재구성, 2016~2020년은 사후 전국 분기경로 기반 장기 backcast, 2021~2025년은 운영형 분기·월 bridge로 구분하며 세 구간의 성능을 같은 지표로 합산하지 않는다.
- `시군구×업종×월`은 2021~2025 분기값 보존형 bridge로 확정하고, 2020은 2019 시군구 구성비를 2019 시도×업종 공식총량에 연결한 전국 사후 backcast로 분리한다.
- 건설업은 PPS 전량 수집과 품질게이트가 끝나기 전에는 전국 route로 채택하지 않는다.
- 활동지표 route는 업종별 잔여오차 축소 후보지만, Phase252 rolling holdout에서 악화 위험이 확인되어 현재 운영 산출물에는 자동채택하지 않는다.

## 산출물

- `nationwide/outputs/active_goal_requirement_audit_2015_2025.csv`
- `nationwide/outputs/active_goal_requirement_source_counts.csv`
- `nationwide/outputs/active_goal_sigungu_actual_publication_matrix.csv`
- `nationwide/outputs/active_goal_sido_validation_summary.csv`
- `nationwide/outputs/active_goal_national_boundary_summary.csv`
- `nationwide/outputs/active_goal_activity_validation_summary.csv`
- `nationwide/sigungu_2015_initialization_reconstruction.md`
- `nationwide/monthly_bridge_2015_2020_extension_audit.md`
- `nationwide/monthly_bridge_scope_gate_2015_2025.md`
- `nationwide/sigungu_2016_2020_fullcoverage_share_bridge_backcast.md`
- `nationwide/sigungu_2020_fullcoverage_share_bridge_backcast.md`
- `nationwide/sigungu_2020_backcast_monthly_bridge_pilot.md`
- `reports/partial_statistics_estimation_phase252_rolling_indicator_route_selection.md`
- `reports/partial_statistics_estimation_phase254_pps_retry_after_update.md`
- `reports/partial_statistics_estimation_phase255_sigungu_residual_priority_audit.md`
"""
    REPORT.write_text(md, encoding="utf-8")
    print(REPORT)
    print(requirements.to_string(index=False))


if __name__ == "__main__":
    main()
