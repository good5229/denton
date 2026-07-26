#!/usr/bin/env python3
"""Phase144: temporal out-of-sample audit for city-level seasonal routing.

Phase140 adopted city×vintage seasonal-share routes selected on the same
2022~2023 evaluation window.  Phase143 showed that the more flexible
parent-level version did not survive temporal holdout for Goyang.  This phase
applies the same temporal split to the coarser city-level route:

* for target year 2022, select the city×vintage route from 2021 only;
* for target year 2023, select the route from 2021~2022 only;
* adopt a non-baseline candidate only when prior-year total WAPE, every
  prior-year WAPE, and prior-year high-value WAPE do not worsen.

The result tells us whether Phase140 can be promoted from a same-window
diagnostic to an operational route, or whether Phase138 baseline remains the
safer production table.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase144_city_temporal_route_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase144_city_temporal_route_audit.md"

PRED = DATA / "phase139_guarded_seasonal_share_routing" / "phase139_candidate_predictions.csv"
BASELINE_PERF = DATA / "phase138_operational_delivery_tables" / "phase138_2022_2023_operational_performance.csv"
CITY_SAME_WINDOW_PERF = DATA / "phase140_guarded_operational_delivery" / "phase140_2022_2023_operational_performance_guarded.csv"
PARENT_TEMPORAL_COMP = DATA / "phase143_temporal_out_of_sample_route_audit" / "phase143_baseline_samewindow_temporal_comparison.csv"

BASELINE = "cell_prior_mean"
VINTAGE_ORDER = {
    "1분기+1개월": 1,
    "1~2분기+1개월": 2,
    "1~3분기+1개월": 3,
    "1~4분기+1개월": 4,
}


def ensure_inputs() -> None:
    missing = [p for p in [PRED, BASELINE_PERF, CITY_SAME_WINDOW_PERF, PARENT_TEMPORAL_COMP] if not p.exists()]
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


def city_year_score(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["available_quarters"].isin([1, 2, 3])].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "year", "available_quarters", "vintage_label", "candidate"], sort=False):
        high = g[g["actual_annual_gva_eok"].ge(1000.0)]
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        high_actual = float(high["actual_annual_gva_eok"].sum())
        high_err = float(high["annual_error_eok"].sum())
        rows.append({
            "city": keys[0],
            "year": int(keys[1]),
            "available_quarters": int(keys[2]),
            "vintage_label": keys[3],
            "candidate": keys[4],
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_actual_sum_eok": high_actual,
            "high_value_error_sum_eok": high_err,
            "high_value_wape_pct": high_err / high_actual * 100 if high_actual > 0 else np.nan,
            "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
        })
    return pd.DataFrame(rows)


def choose_route(score: pd.DataFrame, city: str, k: int, target_year: int) -> dict[str, object]:
    hist = score[
        score["city"].eq(city)
        & score["available_quarters"].eq(k)
        & score["year"].lt(target_year)
    ].copy()
    if hist.empty or BASELINE not in set(hist["candidate"]):
        return {
            "selected_candidate": BASELINE,
            "adopt_city_temporal_route": False,
            "selection_years": "",
            "selection_note": "no_prior_backtest",
        }
    base = hist[hist["candidate"].eq(BASELINE)]
    base_actual = float(base["actual_sum_eok"].sum())
    base_err = float(base["error_sum_eok"].sum())
    base_wape = base_err / base_actual * 100 if base_actual else np.nan
    base_high_actual = float(base["high_value_actual_sum_eok"].sum())
    base_high_err = float(base["high_value_error_sum_eok"].sum())
    base_high_wape = base_high_err / base_high_actual * 100 if base_high_actual > 0 else np.nan
    base_year = base.set_index("year")["wape_pct"].to_dict()

    accepted = []
    for cand_name, cand in hist[~hist["candidate"].eq(BASELINE)].groupby("candidate"):
        cand_actual = float(cand["actual_sum_eok"].sum())
        cand_err = float(cand["error_sum_eok"].sum())
        cand_wape = cand_err / cand_actual * 100 if cand_actual else np.nan
        cand_high_actual = float(cand["high_value_actual_sum_eok"].sum())
        cand_high_err = float(cand["high_value_error_sum_eok"].sum())
        cand_high_wape = cand_high_err / cand_high_actual * 100 if cand_high_actual > 0 else np.nan
        cand_year = cand.set_index("year")["wape_pct"].to_dict()
        common = sorted(set(base_year) & set(cand_year))
        no_year_worse = all(cand_year[y] <= base_year[y] + 1e-9 for y in common)
        no_high_worse = pd.isna(base_high_wape) or pd.isna(cand_high_wape) or cand_high_wape <= base_high_wape + 1e-9
        improves = pd.notna(cand_wape) and pd.notna(base_wape) and cand_wape < base_wape - 1e-9
        if improves and no_year_worse and no_high_worse:
            accepted.append({
                "selected_candidate": cand_name,
                "selection_wape_pct": cand_wape,
                "baseline_selection_wape_pct": base_wape,
                "selection_delta_pct_point": cand_wape - base_wape,
                "selection_error_delta_eok": cand_err - base_err,
                "selection_high_value_delta_pct_point": (
                    cand_high_wape - base_high_wape
                    if pd.notna(cand_high_wape) and pd.notna(base_high_wape) else np.nan
                ),
            })

    selection_years = ",".join(str(int(y)) for y in sorted(hist["year"].unique()))
    if not accepted:
        return {
            "selected_candidate": BASELINE,
            "adopt_city_temporal_route": False,
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
        "adopt_city_temporal_route": True,
        "selection_years": selection_years,
        "selection_note": "selected_from_prior_years_only",
    }


def temporal_routes(df: pd.DataFrame, score: pd.DataFrame) -> pd.DataFrame:
    combos = df[df["available_quarters"].isin([1, 2, 3])][
        ["city", "year", "available_quarters", "vintage_label"]
    ].drop_duplicates()
    rows: list[dict[str, object]] = []
    for r in combos.itertuples(index=False):
        chosen = choose_route(score, r.city, int(r.available_quarters), int(r.year))
        rows.append({
            "city": r.city,
            "target_year": int(r.year),
            "available_quarters": int(r.available_quarters),
            "vintage_label": r.vintage_label,
            **chosen,
        })
    return pd.DataFrame(rows).sort_values(["city", "target_year", "available_quarters"])


def apply_routes(df: pd.DataFrame, routes: pd.DataFrame) -> pd.DataFrame:
    route_map = routes.set_index(["city", "target_year", "available_quarters"])["selected_candidate"].to_dict()
    d = df.copy()
    d["city_temporal_selected_candidate"] = d.apply(
        lambda r: "observed_full_year_sum"
        if int(r["available_quarters"]) == 4
        else route_map.get((r["city"], int(r["year"]), int(r["available_quarters"])), BASELINE),
        axis=1,
    )
    selected = d[d["candidate"].eq(d["city_temporal_selected_candidate"])].copy()
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


def performance(selected: pd.DataFrame) -> pd.DataFrame:
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
            "operation_note": "회계적 연간 회수: 예측력으로 해석 금지" if int(keys[1]) == 4 else "도시라우팅 시간분리 out-of-sample 성능",
        })
    return pd.DataFrame(rows).sort_values(["city", "available_quarters"])


def year_performance(selected: pd.DataFrame) -> pd.DataFrame:
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
    same = pd.read_csv(CITY_SAME_WINDOW_PERF).rename(columns={
        "overall_wape_pct": "city_same_window_wape_pct",
        "high_value_wape_pct": "city_same_window_high_value_wape_pct",
    })
    parent = pd.read_csv(PARENT_TEMPORAL_COMP).rename(columns={
        "temporal_oos_wape_pct": "parent_temporal_wape_pct",
        "temporal_oos_high_value_wape_pct": "parent_temporal_high_value_wape_pct",
    })
    city = perf.rename(columns={
        "overall_wape_pct": "city_temporal_wape_pct",
        "high_value_wape_pct": "city_temporal_high_value_wape_pct",
        "error_sum_eok": "city_temporal_error_sum_eok",
    })
    out = city.merge(
        base[["city", "vintage_label", "baseline_wape_pct", "baseline_high_value_wape_pct"]],
        on=["city", "vintage_label"],
        how="left",
    ).merge(
        same[["city", "vintage_label", "city_same_window_wape_pct", "city_same_window_high_value_wape_pct"]],
        on=["city", "vintage_label"],
        how="left",
    ).merge(
        parent[["city", "vintage_label", "parent_temporal_wape_pct", "parent_temporal_high_value_wape_pct"]],
        on=["city", "vintage_label"],
        how="left",
    )
    out["city_temporal_vs_baseline_delta_pct_point"] = out["city_temporal_wape_pct"] - out["baseline_wape_pct"]
    out["city_temporal_vs_same_window_delta_pct_point"] = out["city_temporal_wape_pct"] - out["city_same_window_wape_pct"]
    out["city_temporal_vs_parent_temporal_delta_pct_point"] = out["city_temporal_wape_pct"] - out["parent_temporal_wape_pct"]
    out["city_temporal_high_value_vs_baseline_delta_pct_point"] = (
        out["city_temporal_high_value_wape_pct"] - out["baseline_high_value_wape_pct"]
    )
    out["recommendation"] = np.where(
        out["available_quarters"].eq(4),
        "회계 회수",
        np.where(
            out["city_temporal_vs_baseline_delta_pct_point"] < -1e-9,
            "도시라우팅 제한 후보",
            "Phase138 baseline 유지",
        ),
    )
    return out.sort_values(["city", "available_quarters"])


def route_summary(routes: pd.DataFrame) -> pd.DataFrame:
    d = routes[routes["target_year"].between(2022, 2023)].copy()
    return (
        d.groupby(["city", "target_year", "available_quarters", "vintage_label"], as_index=False)
        .agg(
            selected_candidate=("selected_candidate", "first"),
            adopted=("adopt_city_temporal_route", "first"),
            selection_years=("selection_years", "first"),
            selection_delta_pct_point=("selection_delta_pct_point", "first"),
            selection_error_delta_eok=("selection_error_delta_eok", "first"),
        )
        .sort_values(["city", "target_year", "available_quarters"])
    )


def delivery_2023(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for keys, g in selected[selected["year"].eq(2023)].groupby(["city", "available_quarters", "vintage_label"], sort=False):
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
            "selected_candidate": ", ".join(sorted(set(g["city_temporal_selected_candidate"].astype(str)))),
            "nonbaseline_cell_count": int((g["city_temporal_selected_candidate"] != BASELINE).sum()) if int(keys[1]) < 4 else 0,
        })
    return pd.DataFrame(rows).sort_values(["city", "vintage_label"], key=lambda s: s.map(VINTAGE_ORDER) if s.name == "vintage_label" else s)


def accounting_checks(selected: pd.DataFrame) -> pd.DataFrame:
    q4 = selected[selected["available_quarters"].eq(4)].copy()
    q4["diff"] = (q4["annual_prediction_eok"] - q4["actual_annual_gva_eok"]).abs()
    tmp = selected.copy()
    tmp["diff"] = (
        tmp["previous_period_recheck_eok"].fillna(0.0)
        + tmp["current_quarter_estimate_eok"]
        - tmp["ytd_eok"]
    ).abs()
    return pd.DataFrame([
        {
            "check_id": "q4_full_year_recovery",
            "rows": int(len(q4)),
            "max_abs_diff_eok": float(q4["diff"].max()) if len(q4) else np.nan,
            "pass": bool((q4["diff"] < 1e-9).all()) if len(q4) else False,
        },
        {
            "check_id": "current_plus_previous_equals_ytd",
            "rows": int(len(tmp)),
            "max_abs_diff_eok": float(tmp["diff"].max()) if len(tmp) else np.nan,
            "pass": bool((tmp["diff"] < 1e-9).all()) if len(tmp) else False,
        },
    ])


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


def write_report(comp: pd.DataFrame, year_perf: pd.DataFrame, route_sum: pd.DataFrame, delivery: pd.DataFrame, checks: pd.DataFrame) -> None:
    non_q4 = comp[comp["available_quarters"].isin([1, 2, 3])].copy()
    REPORT.write_text("\n".join([
        "# Phase144 도시 단위 라우팅 시간분리 검증",
        "",
        "## 목적",
        "",
        "Phase140의 도시×빈티지 라우팅도 same-window 선택이었으므로, Phase143과 같은 시간분리 기준으로 다시 검증했다. 목표는 보수 운영표를 대체할 수 있는지, 아니면 Phase138 baseline을 유지해야 하는지 판정하는 것이다.",
        "",
        "## 시간분리 규칙",
        "",
        "- 2022년 예측: 2021년 도시×빈티지 backtest만으로 후보 선택",
        "- 2023년 예측: 2021~2022년 도시×빈티지 backtest만으로 후보 선택",
        "- 이전 연도 전체 WAPE, 연도별 WAPE, 1,000억원 이상 업종 WAPE가 모두 악화되지 않을 때만 baseline에서 이탈",
        "",
        "## 2022~2023 평균 성능 비교",
        "",
        md_table(comp, [
            "city", "vintage_label", "evaluated_years",
            "baseline_wape_pct", "city_same_window_wape_pct", "city_temporal_wape_pct", "parent_temporal_wape_pct",
            "city_temporal_vs_baseline_delta_pct_point", "city_temporal_vs_same_window_delta_pct_point",
            "baseline_high_value_wape_pct", "city_same_window_high_value_wape_pct", "city_temporal_high_value_wape_pct",
            "city_temporal_high_value_vs_baseline_delta_pct_point", "gt20_cells", "recommendation",
        ]),
        "",
        "## 연도별 도시라우팅 시간분리 성능",
        "",
        md_table(year_perf, ["city", "year", "vintage_label", "actual_sum_eok", "error_sum_eok", "wape_pct"]),
        "",
        "## 라우팅 선택 요약",
        "",
        md_table(route_sum, [
            "city", "target_year", "vintage_label", "selected_candidate", "adopted",
            "selection_years", "selection_delta_pct_point", "selection_error_delta_eok",
        ]),
        "",
        "## 2023 운영 산출 예시",
        "",
        md_table(delivery, [
            "city", "vintage_label", "current_quarter_estimate_eok", "previous_period_recheck_eok",
            "ytd_estimate_eok", "annual_prediction_eok", "annual_actual_eok",
            "annual_cell_abs_error_sum_eok", "annual_wape_pct", "high_value_wape_pct",
            "selected_candidate", "nonbaseline_cell_count",
        ]),
        "",
        "## 회계 검증",
        "",
        md_table(checks, checks.columns.tolist()),
        "",
        "## 운영 채택 판정",
        "",
        md_table(non_q4, [
            "city", "vintage_label", "baseline_wape_pct", "city_temporal_wape_pct",
            "city_temporal_vs_baseline_delta_pct_point", "recommendation",
        ]),
        "",
        "## 판정",
        "",
        "1. 도시 단위 라우팅도 시간분리 검증에서는 고양시 Q1/Q2/Q3 모두 baseline보다 악화된다. 따라서 Phase140을 고양시 운영 최종표로 승격하지 않는다.",
        "2. 포항시는 Q3만 baseline보다 근소하게 개선되고 Q1/Q2는 악화된다. 포항도 Q3 제한 후보 외에는 baseline 유지가 안전하다.",
        "3. Phase142 parent 라우팅과 Phase140 city 라우팅 모두 same-window 성과는 과대평가 위험이 있다. 최종 운영표는 Phase138 baseline을 중심으로 두고, Q4는 회계 회수로만 해석한다.",
        "4. 다음 의미 있는 개선은 라우팅 자유도를 늘리는 것이 아니라, 독립적인 추가 연도·타 시군구 확장검증 또는 업종별 직접 활동자료를 확보하는 것이다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    ensure_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates()
    score = city_year_score(candidates)
    routes = temporal_routes(candidates, score)
    selected = apply_routes(candidates, routes)
    perf = performance(selected)
    year_perf = year_performance(selected)
    comp = compare(perf)
    route_sum = route_summary(routes)
    delivery = delivery_2023(selected)
    checks = accounting_checks(selected)

    score.to_csv(OUT / "phase144_city_year_candidate_scorecard.csv", index=False)
    routes.to_csv(OUT / "phase144_city_temporal_routes.csv", index=False)
    selected.to_csv(OUT / "phase144_city_temporal_selected_predictions.csv", index=False)
    perf.to_csv(OUT / "phase144_city_temporal_performance.csv", index=False)
    year_perf.to_csv(OUT / "phase144_city_temporal_yearly_performance.csv", index=False)
    comp.to_csv(OUT / "phase144_baseline_samewindow_temporal_comparison.csv", index=False)
    route_sum.to_csv(OUT / "phase144_route_summary.csv", index=False)
    delivery.to_csv(OUT / "phase144_2023_operational_delivery_city_temporal.csv", index=False)
    checks.to_csv(OUT / "phase144_accounting_checks.csv", index=False)
    write_report(comp, year_perf, route_sum, delivery, checks)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
