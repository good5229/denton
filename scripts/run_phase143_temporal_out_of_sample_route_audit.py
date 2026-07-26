#!/usr/bin/env python3
"""Phase143: temporal out-of-sample audit for parent seasonal routing.

Phase141/142 showed that city×parent×vintage route selection can lower WAPE,
but it selected and evaluated routes on the same 2022~2023 window.  This phase
uses a stricter temporal split:

* for target year 2022, select a route from 2021 parent-level backtest only;
* for target year 2023, select a route from 2021~2022 parent-level backtests;
* if no prior-year candidate beats the baseline without prior-year worsening,
  keep the baseline middle-industry seasonal share.

Predictions themselves still use only target-year YTD and prior-year seasonal
shares from Phase139 candidates.  The additional audit here is only about which
predefined seasonal-share family is allowed to be selected before the target
year is evaluated.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase143_temporal_out_of_sample_route_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase143_temporal_out_of_sample_route_audit.md"

PRED = DATA / "phase139_guarded_seasonal_share_routing" / "phase139_candidate_predictions.csv"
BASELINE_PERF = DATA / "phase138_operational_delivery_tables" / "phase138_2022_2023_operational_performance.csv"
PARENT_CANDIDATE_PERF = DATA / "phase142_parent_candidate_operational_delivery" / "phase142_2022_2023_operational_performance_parent_candidate.csv"

BASELINE = "cell_prior_mean"
VINTAGE_ORDER = {
    "1분기+1개월": 1,
    "1~2분기+1개월": 2,
    "1~3분기+1개월": 3,
    "1~4분기+1개월": 4,
}


def ensure_inputs() -> None:
    missing = [p for p in [PRED, BASELINE_PERF, PARENT_CANDIDATE_PERF] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required output(s): " + ", ".join(str(p) for p in missing))


def load_candidates() -> pd.DataFrame:
    df = pd.read_csv(PRED, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["amount_bucket"] = np.select(
        [df["actual_annual_gva_eok"].ge(5000.0), df["actual_annual_gva_eok"].ge(1000.0)],
        ["very_large_5000eok_plus", "large_1000_5000eok"],
        default="small_under_1000eok",
    )
    return df


def parent_year_score(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["available_quarters"].isin([1, 2, 3])].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "parent_code", "year", "available_quarters", "vintage_label", "candidate"], sort=False):
        high = g[g["actual_annual_gva_eok"].ge(1000.0)]
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        high_actual = float(high["actual_annual_gva_eok"].sum())
        high_err = float(high["annual_error_eok"].sum())
        rows.append({
            "city": keys[0],
            "parent_code": keys[1],
            "year": int(keys[2]),
            "available_quarters": int(keys[3]),
            "vintage_label": keys[4],
            "candidate": keys[5],
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_actual_sum_eok": high_actual,
            "high_value_error_sum_eok": high_err,
            "high_value_wape_pct": high_err / high_actual * 100 if high_actual > 0 else np.nan,
            "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
        })
    return pd.DataFrame(rows)


def choose_route_for_target(score: pd.DataFrame, city: str, parent: str, k: int, target_year: int) -> dict[str, object]:
    hist = score[
        score["city"].eq(city)
        & score["parent_code"].eq(parent)
        & score["available_quarters"].eq(k)
        & score["year"].lt(target_year)
    ].copy()
    if hist.empty or BASELINE not in set(hist["candidate"]):
        return {
            "selected_candidate": BASELINE,
            "adopt_temporal_route": False,
            "selection_years": "",
            "selection_note": "no_prior_backtest",
        }

    base = hist[hist["candidate"].eq(BASELINE)]
    base_total_actual = float(base["actual_sum_eok"].sum())
    base_total_err = float(base["error_sum_eok"].sum())
    base_wape = base_total_err / base_total_actual * 100 if base_total_actual else np.nan
    base_high_actual = float(base["high_value_actual_sum_eok"].sum())
    base_high_err = float(base["high_value_error_sum_eok"].sum())
    base_high_wape = base_high_err / base_high_actual * 100 if base_high_actual > 0 else np.nan
    base_year_wape = base.set_index("year")["wape_pct"].to_dict()

    accepted = []
    for cand_name, cand in hist[~hist["candidate"].eq(BASELINE)].groupby("candidate"):
        cand_total_actual = float(cand["actual_sum_eok"].sum())
        cand_total_err = float(cand["error_sum_eok"].sum())
        cand_wape = cand_total_err / cand_total_actual * 100 if cand_total_actual else np.nan
        cand_high_actual = float(cand["high_value_actual_sum_eok"].sum())
        cand_high_err = float(cand["high_value_error_sum_eok"].sum())
        cand_high_wape = cand_high_err / cand_high_actual * 100 if cand_high_actual > 0 else np.nan
        cand_year_wape = cand.set_index("year")["wape_pct"].to_dict()
        common = sorted(set(base_year_wape) & set(cand_year_wape))
        no_year_worse = all(cand_year_wape[y] <= base_year_wape[y] + 1e-9 for y in common)
        no_high_worse = pd.isna(base_high_wape) or pd.isna(cand_high_wape) or cand_high_wape <= base_high_wape + 1e-9
        improves = pd.notna(cand_wape) and pd.notna(base_wape) and cand_wape < base_wape - 1e-9
        if improves and no_year_worse and no_high_worse:
            accepted.append({
                "selected_candidate": cand_name,
                "selection_wape_pct": cand_wape,
                "baseline_selection_wape_pct": base_wape,
                "selection_delta_pct_point": cand_wape - base_wape,
                "selection_error_delta_eok": cand_total_err - base_total_err,
                "selection_high_value_delta_pct_point": (
                    cand_high_wape - base_high_wape
                    if pd.notna(cand_high_wape) and pd.notna(base_high_wape) else np.nan
                ),
            })

    selection_years = ",".join(str(int(y)) for y in sorted(hist["year"].unique()))
    if not accepted:
        return {
            "selected_candidate": BASELINE,
            "adopt_temporal_route": False,
            "selection_years": selection_years,
            "selection_note": "baseline_kept_by_temporal_guardrail",
            "selection_wape_pct": base_wape,
            "baseline_selection_wape_pct": base_wape,
            "selection_delta_pct_point": 0.0,
            "selection_error_delta_eok": 0.0,
            "selection_high_value_delta_pct_point": 0.0,
        }
    chosen = pd.DataFrame(accepted).sort_values(["selection_wape_pct", "selection_error_delta_eok"]).iloc[0].to_dict()
    return {
        **chosen,
        "adopt_temporal_route": True,
        "selection_years": selection_years,
        "selection_note": "selected_from_prior_years_only",
    }


def temporal_routes(df: pd.DataFrame, score: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    combos = df[df["available_quarters"].isin([1, 2, 3])][
        ["city", "parent_code", "year", "available_quarters", "vintage_label"]
    ].drop_duplicates()
    for r in combos.itertuples(index=False):
        chosen = choose_route_for_target(score, r.city, r.parent_code, int(r.available_quarters), int(r.year))
        rows.append({
            "city": r.city,
            "parent_code": r.parent_code,
            "target_year": int(r.year),
            "available_quarters": int(r.available_quarters),
            "vintage_label": r.vintage_label,
            **chosen,
        })
    return pd.DataFrame(rows).sort_values(["city", "target_year", "available_quarters", "parent_code"])


def apply_routes(df: pd.DataFrame, routes: pd.DataFrame) -> pd.DataFrame:
    route_map = routes.set_index(["city", "parent_code", "target_year", "available_quarters"])["selected_candidate"].to_dict()
    d = df.copy()
    d["temporal_selected_candidate"] = d.apply(
        lambda r: "observed_full_year_sum"
        if int(r["available_quarters"]) == 4
        else route_map.get((r["city"], r["parent_code"], int(r["year"]), int(r["available_quarters"])), BASELINE),
        axis=1,
    )
    selected = d[d["candidate"].eq(d["temporal_selected_candidate"])].copy()
    selected = selected.sort_values(["city", "year", "parent_code", "middle_code", "available_quarters"])
    selected["current_quarter_estimate_eok"] = selected.groupby(
        ["city", "year", "parent_code", "middle_code"]
    )["ytd_eok"].diff().fillna(selected["ytd_eok"])
    selected["previous_period_recheck_eok"] = np.where(
        selected["available_quarters"].gt(1),
        selected["ytd_eok"] - selected["current_quarter_estimate_eok"],
        np.nan,
    )
    return selected


def city_performance(selected: pd.DataFrame) -> pd.DataFrame:
    d = selected[selected["year"].between(2022, 2023)].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "available_quarters", "vintage_label"], sort=False):
        high = g[g["actual_annual_gva_eok"].ge(1000.0)]
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        high_actual = float(high["actual_annual_gva_eok"].sum())
        high_err = float(high["annual_error_eok"].sum())
        rows.append({
            "city": keys[0],
            "available_quarters": int(keys[1]),
            "vintage_label": keys[2],
            "evaluated_years": "2022-2023",
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "overall_wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_error_sum_eok": high_err,
            "high_value_wape_pct": high_err / high_actual * 100 if high_actual > 0 else np.nan,
            "gt10_cells": int((g["annual_error_rate_pct"] > 10).sum()),
            "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
            "operation_note": "회계적 연간 회수: 예측력으로 해석 금지" if int(keys[1]) == 4 else "시간분리 out-of-sample 성능",
        })
    return pd.DataFrame(rows).sort_values(["city", "available_quarters"])


def city_year_performance(selected: pd.DataFrame) -> pd.DataFrame:
    d = selected[selected["year"].between(2022, 2023)].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "year", "available_quarters", "vintage_label"], sort=False):
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        rows.append({
            "city": keys[0],
            "year": int(keys[1]),
            "available_quarters": int(keys[2]),
            "vintage_label": keys[3],
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "wape_pct": err / actual * 100 if actual else np.nan,
        })
    return pd.DataFrame(rows).sort_values(["city", "year", "available_quarters"])


def compare(perf: pd.DataFrame) -> pd.DataFrame:
    base = pd.read_csv(BASELINE_PERF).rename(columns={
        "overall_wape_pct": "baseline_wape_pct",
        "high_value_wape_pct": "baseline_high_value_wape_pct",
    })
    parent = pd.read_csv(PARENT_CANDIDATE_PERF).rename(columns={
        "overall_wape_pct": "same_window_parent_wape_pct",
        "high_value_wape_pct": "same_window_parent_high_value_wape_pct",
    })
    temporal = perf.rename(columns={
        "overall_wape_pct": "temporal_oos_wape_pct",
        "high_value_wape_pct": "temporal_oos_high_value_wape_pct",
        "error_sum_eok": "temporal_oos_error_sum_eok",
    })
    out = temporal.merge(
        base[["city", "vintage_label", "baseline_wape_pct", "baseline_high_value_wape_pct"]],
        on=["city", "vintage_label"],
        how="left",
    ).merge(
        parent[["city", "vintage_label", "same_window_parent_wape_pct", "same_window_parent_high_value_wape_pct"]],
        on=["city", "vintage_label"],
        how="left",
    )
    out["temporal_vs_baseline_wape_delta_pct_point"] = out["temporal_oos_wape_pct"] - out["baseline_wape_pct"]
    out["temporal_vs_same_window_parent_delta_pct_point"] = out["temporal_oos_wape_pct"] - out["same_window_parent_wape_pct"]
    out["temporal_vs_baseline_high_value_delta_pct_point"] = (
        out["temporal_oos_high_value_wape_pct"] - out["baseline_high_value_wape_pct"]
    )
    return out.sort_values(["city", "available_quarters"])


def route_summary(routes: pd.DataFrame) -> pd.DataFrame:
    d = routes[routes["target_year"].between(2022, 2023)].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "target_year", "available_quarters", "vintage_label"], sort=False):
        adopted = g[g["adopt_temporal_route"].astype(bool)]
        rows.append({
            "city": keys[0],
            "target_year": int(keys[1]),
            "available_quarters": int(keys[2]),
            "vintage_label": keys[3],
            "adopted_parent_routes": int(len(adopted)),
            "candidate_error_delta_eok_on_selection_years": float(adopted["selection_error_delta_eok"].sum()) if len(adopted) else 0.0,
            "selection_years": ";".join(sorted(set(g["selection_years"].fillna("").astype(str)))),
        })
    return pd.DataFrame(rows).sort_values(["city", "target_year", "available_quarters"])


def delivery_2023(selected: pd.DataFrame) -> pd.DataFrame:
    d = selected[selected["year"].eq(2023)].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "available_quarters", "vintage_label"], sort=False):
        high = g[g["actual_annual_gva_eok"].ge(1000.0)]
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        rows.append({
            "city": keys[0],
            "target_year": 2023,
            "vintage_label": keys[2],
            "current_quarter_estimate_eok": float(g["current_quarter_estimate_eok"].sum()),
            "previous_period_recheck_eok": float(g["previous_period_recheck_eok"].fillna(0).sum()) if int(keys[1]) > 1 else np.nan,
            "ytd_estimate_eok": float(g["ytd_eok"].sum()),
            "annual_prediction_eok": float(g["annual_prediction_eok"].sum()),
            "annual_actual_eok": actual,
            "annual_cell_abs_error_sum_eok": err,
            "annual_wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_wape_pct": (
                float(high["annual_error_eok"].sum()) / float(high["actual_annual_gva_eok"].sum()) * 100
                if len(high) and float(high["actual_annual_gva_eok"].sum()) > 0 else np.nan
            ),
            "nonbaseline_cell_count": int((g["temporal_selected_candidate"] != BASELINE).sum()) if int(keys[1]) < 4 else 0,
        })
    return pd.DataFrame(rows).sort_values(["city", "vintage_label"], key=lambda s: s.map(VINTAGE_ORDER) if s.name == "vintage_label" else s)


def top_2023(selected: pd.DataFrame) -> pd.DataFrame:
    d = selected[selected["year"].eq(2023) & selected["available_quarters"].isin([1, 2, 3])].copy()
    d["error_contribution_pct"] = d.groupby(["city", "vintage_label"])["annual_error_eok"].transform(
        lambda s: s / s.sum() * 100 if float(s.sum()) else 0
    )
    return (
        d.sort_values(["city", "available_quarters", "annual_error_eok"], ascending=[True, True, False])
        .groupby(["city", "available_quarters"], as_index=False)
        .head(8)
    )


def accounting_checks(selected: pd.DataFrame) -> pd.DataFrame:
    checks = []
    q4 = selected[selected["available_quarters"].eq(4)].copy()
    q4["diff"] = (q4["annual_prediction_eok"] - q4["actual_annual_gva_eok"]).abs()
    checks.append({
        "check_id": "q4_full_year_recovery",
        "rows": int(len(q4)),
        "max_abs_diff_eok": float(q4["diff"].max()) if len(q4) else np.nan,
        "pass": bool((q4["diff"] < 1e-9).all()) if len(q4) else False,
    })
    tmp = selected.copy()
    tmp["diff"] = (
        tmp["previous_period_recheck_eok"].fillna(0.0)
        + tmp["current_quarter_estimate_eok"]
        - tmp["ytd_eok"]
    ).abs()
    checks.append({
        "check_id": "current_plus_previous_equals_ytd",
        "rows": int(len(tmp)),
        "max_abs_diff_eok": float(tmp["diff"].max()) if len(tmp) else np.nan,
        "pass": bool((tmp["diff"] < 1e-9).all()) if len(tmp) else False,
    })
    return pd.DataFrame(checks)


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    labels = [c.replace("_eok", " 억원").replace("_pct", " %").replace("_", " ") for c in d.columns]

    def fmt(v: object) -> str:
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            if np.isfinite(float(v)) and abs(float(v) - round(float(v))) < 1e-9:
                return f"{int(round(float(v))):,}"
            return f"{float(v):,.2f}"
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        return str(v).replace("|", "\\|")

    return "\n".join([
        "| " + " | ".join(labels) + " |",
        "| " + " | ".join(["---"] * len(labels)) + " |",
        *("| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()),
    ])


def write_report(
    comp: pd.DataFrame,
    year_perf: pd.DataFrame,
    routes: pd.DataFrame,
    route_sum: pd.DataFrame,
    delivery: pd.DataFrame,
    top: pd.DataFrame,
    checks: pd.DataFrame,
) -> None:
    adopted = routes[routes["target_year"].between(2022, 2023) & routes["adopt_temporal_route"].astype(bool)].copy()
    rec = comp[comp["available_quarters"].isin([1, 2, 3])].copy()
    rec["recommendation"] = np.where(
        rec["temporal_vs_baseline_wape_delta_pct_point"] < -1e-9,
        "시간분리 개선: 제한적 후보 유지",
        "baseline/보수표 유지",
    )
    rec["reason"] = np.where(
        rec["temporal_vs_baseline_wape_delta_pct_point"] < -1e-9,
        "목표연도 이전 선택에서도 baseline보다 WAPE 감소",
        "시간분리 적용 시 baseline보다 WAPE가 같거나 악화",
    )
    REPORT.write_text("\n".join([
        "# Phase143 상위산업 라우팅 시간분리 검증",
        "",
        "## 목적",
        "",
        "Phase141/142의 상위산업 후보 라우팅은 같은 2022~2023 창에서 후보를 고르고 평가했다. 이번에는 목표연도 이전 실적만으로 라우팅을 고른 뒤 목표연도에 적용해 과적합 위험을 점검했다.",
        "",
        "## 시간분리 규칙",
        "",
        "- 2022년 예측: 2021년 backtest만으로 라우팅 선택",
        "- 2023년 예측: 2021~2022년 backtest만으로 라우팅 선택",
        "- 이전 연도에서 전체 WAPE, 연도별 WAPE, 1,000억원 이상 업종 WAPE가 모두 악화되지 않을 때만 baseline에서 이탈",
        "",
        "## 2022~2023 평균 성능 비교",
        "",
        md_table(comp, [
            "city", "vintage_label", "evaluated_years",
            "baseline_wape_pct", "same_window_parent_wape_pct", "temporal_oos_wape_pct",
            "temporal_vs_baseline_wape_delta_pct_point", "temporal_vs_same_window_parent_delta_pct_point",
            "baseline_high_value_wape_pct", "same_window_parent_high_value_wape_pct", "temporal_oos_high_value_wape_pct",
            "temporal_vs_baseline_high_value_delta_pct_point", "gt20_cells", "operation_note",
        ]),
        "",
        "## 연도별 out-of-sample 성능",
        "",
        md_table(year_perf, ["city", "year", "vintage_label", "actual_sum_eok", "error_sum_eok", "wape_pct"]),
        "",
        "## 라우팅 선택 요약",
        "",
        md_table(route_sum, [
            "city", "target_year", "vintage_label", "adopted_parent_routes",
            "candidate_error_delta_eok_on_selection_years", "selection_years",
        ]),
        "",
        "## 운영 채택 권고",
        "",
        md_table(rec, [
            "city", "vintage_label", "baseline_wape_pct", "same_window_parent_wape_pct",
            "temporal_oos_wape_pct", "temporal_vs_baseline_wape_delta_pct_point",
            "recommendation", "reason",
        ]),
        "",
        "## 2023 운영 산출 예시",
        "",
        md_table(delivery, [
            "city", "vintage_label", "current_quarter_estimate_eok", "previous_period_recheck_eok",
            "ytd_estimate_eok", "annual_prediction_eok", "annual_actual_eok",
            "annual_cell_abs_error_sum_eok", "annual_wape_pct", "high_value_wape_pct", "nonbaseline_cell_count",
        ]),
        "",
        "## 2023 오차기여 상위 중분류",
        "",
        md_table(top, [
            "city", "vintage_label", "parent_code", "middle_code", "middle_label", "temporal_selected_candidate",
            "actual_annual_gva_eok", "annual_prediction_eok", "annual_error_eok",
            "annual_error_rate_pct", "error_contribution_pct",
        ], n=48),
        "",
        "## 회계 검증",
        "",
        md_table(checks, checks.columns.tolist()),
        "",
        "## 판정",
        "",
        f"1. 시간분리 기준으로 채택된 2022~2023 라우팅은 {len(adopted)}개다. 이는 Phase142의 same-window 후보보다 훨씬 엄격하다.",
        "2. 고양시는 Q1/Q2/Q3 모두 시간분리 WAPE가 baseline보다 높다. 따라서 Phase142 상위산업 후보 라우팅을 고양시 운영 최종안으로 채택하면 안 된다.",
        "3. 포항시는 Q3만 baseline보다 0.01%p 낮고 Q1/Q2는 악화된다. 따라서 포항도 Q3 제한 후보 외에는 Phase138/140의 보수표를 유지해야 한다.",
        "4. 같은 창에서 고른 Phase142와 시간분리 결과의 차이가 과적합 비용이다. 숫자가 예뻐 보여도 목표연도 이전 선택에서 통과하지 못하면 운영 성능으로 주장하지 않는다.",
        "5. 이 감사도 3개 연도만 사용하므로 최종 일반화 증거는 아니다. 다음 확정 단계는 타 시군구 확장검증이다.",
        "6. Q4+1개월 0%는 계속 예측성능이 아니라 회계 회수다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    ensure_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates()
    score = parent_year_score(candidates)
    routes = temporal_routes(candidates, score)
    selected = apply_routes(candidates, routes)
    perf = city_performance(selected)
    year_perf = city_year_performance(selected)
    comp = compare(perf)
    route_sum = route_summary(routes)
    delivery = delivery_2023(selected)
    top = top_2023(selected)
    checks = accounting_checks(selected)

    score.to_csv(OUT / "phase143_parent_year_candidate_scorecard.csv", index=False)
    routes.to_csv(OUT / "phase143_temporal_parent_routes.csv", index=False)
    selected.to_csv(OUT / "phase143_temporal_selected_predictions.csv", index=False)
    perf.to_csv(OUT / "phase143_temporal_oos_performance.csv", index=False)
    year_perf.to_csv(OUT / "phase143_temporal_oos_yearly_performance.csv", index=False)
    comp.to_csv(OUT / "phase143_baseline_samewindow_temporal_comparison.csv", index=False)
    route_sum.to_csv(OUT / "phase143_route_summary.csv", index=False)
    delivery.to_csv(OUT / "phase143_2023_operational_delivery_temporal_oos.csv", index=False)
    top.to_csv(OUT / "phase143_2023_top_contributors_temporal_oos.csv", index=False)
    checks.to_csv(OUT / "phase143_accounting_checks.csv", index=False)
    write_report(comp, year_perf, routes, route_sum, delivery, top, checks)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
