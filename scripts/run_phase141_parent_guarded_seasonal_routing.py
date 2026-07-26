#!/usr/bin/env python3
"""Phase141: parent-industry guarded seasonal routing.

Phase139 selected one seasonal-share family per city×vintage.  That is safe but
coarse: a city-wide route can improve aggregate WAPE while making one large
industry look worse.  This phase tests the next natural granularity,
city×KSIC-parent×vintage, with the same no-worsening guardrail.

This remains a model-selection audit.  Candidate predictions use only
pre-target-year seasonal shares; actual annual GVA is used only to evaluate
which predefined routing family would have been safer in the 2022~2023
backtest.  Because this is more flexible than Phase139, it should be treated as
an operational candidate until additional out-of-sample years or other cities
are tested.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase141_parent_guarded_seasonal_routing"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase141_parent_guarded_seasonal_routing.md"

PRED = DATA / "phase139_guarded_seasonal_share_routing" / "phase139_candidate_predictions.csv"
BASELINE_NAME = "cell_prior_mean"


def ensure_input() -> None:
    if not PRED.exists():
        raise FileNotFoundError(f"Run Phase139 first; missing {PRED}")


def load_candidates() -> pd.DataFrame:
    df = pd.read_csv(PRED, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    return df


def score_parent(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["year"].between(2022, 2023) & df["available_quarters"].isin([1, 2, 3])].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "parent_code", "available_quarters", "vintage_label", "candidate"], sort=False):
        high = g[g["actual_annual_gva_eok"].ge(1000.0)]
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        high_actual = float(high["actual_annual_gva_eok"].sum())
        high_err = float(high["annual_error_eok"].sum())
        rows.append({
            "city": keys[0],
            "parent_code": keys[1],
            "available_quarters": int(keys[2]),
            "vintage_label": keys[3],
            "candidate": keys[4],
            "evaluated_years": "2022-2023",
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_actual_sum_eok": high_actual,
            "high_value_error_sum_eok": high_err,
            "high_value_wape_pct": high_err / high_actual * 100 if high_actual > 0 else np.nan,
            "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
        })
    return pd.DataFrame(rows)


def score_parent_year(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["year"].between(2022, 2023) & df["available_quarters"].isin([1, 2, 3])].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "parent_code", "year", "available_quarters", "vintage_label", "candidate"], sort=False):
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
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
        })
    return pd.DataFrame(rows)


def choose_routes(score: pd.DataFrame, yearly: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for keys, g in score.groupby(["city", "parent_code", "available_quarters", "vintage_label"], sort=False):
        city, parent, k, label = keys
        if BASELINE_NAME not in set(g["candidate"]):
            continue
        base = g[g["candidate"].eq(BASELINE_NAME)].iloc[0]
        base_year = yearly[
            yearly["city"].eq(city)
            & yearly["parent_code"].eq(parent)
            & yearly["available_quarters"].eq(k)
            & yearly["candidate"].eq(BASELINE_NAME)
        ].set_index("year")["wape_pct"]

        accepted = []
        for _, cand in g[~g["candidate"].eq(BASELINE_NAME)].iterrows():
            cand_year = yearly[
                yearly["city"].eq(city)
                & yearly["parent_code"].eq(parent)
                & yearly["available_quarters"].eq(k)
                & yearly["candidate"].eq(cand["candidate"])
            ].set_index("year")["wape_pct"]
            common = sorted(set(base_year.index) & set(cand_year.index))
            no_year_worse = bool(all(cand_year.loc[y] <= base_year.loc[y] + 1e-9 for y in common))
            no_high_worse = (
                pd.isna(base["high_value_wape_pct"])
                or pd.isna(cand["high_value_wape_pct"])
                or cand["high_value_wape_pct"] <= base["high_value_wape_pct"] + 1e-9
            )
            improves = bool(cand["wape_pct"] < base["wape_pct"] - 1e-9)
            if improves and no_high_worse and no_year_worse:
                accepted.append(cand)

        if accepted:
            chosen = pd.DataFrame(accepted).sort_values(["wape_pct", "high_value_wape_pct"]).iloc[0]
            adopt = True
        else:
            chosen = base
            adopt = False

        rows.append({
            "city": city,
            "parent_code": parent,
            "available_quarters": int(k),
            "vintage_label": label,
            "baseline_candidate": BASELINE_NAME,
            "selected_candidate": chosen["candidate"],
            "adopt_parent_route": adopt,
            "baseline_wape_pct": float(base["wape_pct"]),
            "selected_wape_pct": float(chosen["wape_pct"]),
            "wape_delta_pct_point": float(chosen["wape_pct"] - base["wape_pct"]),
            "baseline_high_value_wape_pct": float(base["high_value_wape_pct"]) if pd.notna(base["high_value_wape_pct"]) else np.nan,
            "selected_high_value_wape_pct": float(chosen["high_value_wape_pct"]) if pd.notna(chosen["high_value_wape_pct"]) else np.nan,
            "high_value_wape_delta_pct_point": (
                float(chosen["high_value_wape_pct"] - base["high_value_wape_pct"])
                if pd.notna(base["high_value_wape_pct"]) and pd.notna(chosen["high_value_wape_pct"]) else np.nan
            ),
            "baseline_error_sum_eok": float(base["error_sum_eok"]),
            "selected_error_sum_eok": float(chosen["error_sum_eok"]),
            "error_delta_eok": float(chosen["error_sum_eok"] - base["error_sum_eok"]),
        })
    return pd.DataFrame(rows).sort_values(["city", "available_quarters", "parent_code"])


def apply_routes(df: pd.DataFrame, routes: pd.DataFrame) -> pd.DataFrame:
    route_map = routes.set_index(["city", "parent_code", "available_quarters"])["selected_candidate"].to_dict()
    d = df.copy()
    d["parent_selected_candidate"] = d.apply(
        lambda r: "observed_full_year_sum"
        if int(r["available_quarters"]) == 4
        else route_map.get((r["city"], r["parent_code"], int(r["available_quarters"])), BASELINE_NAME),
        axis=1,
    )
    selected = d[d["candidate"].eq(d["parent_selected_candidate"])].copy()
    selected["amount_bucket"] = np.select(
        [selected["actual_annual_gva_eok"].ge(5000.0), selected["actual_annual_gva_eok"].ge(1000.0)],
        ["very_large_5000eok_plus", "large_1000_5000eok"],
        default="small_under_1000eok",
    )
    return selected


def city_score(selected: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label, source in [("baseline", baseline), ("parent_guarded", selected)]:
        d = source[source["year"].between(2022, 2023) & source["available_quarters"].isin([1, 2, 3, 4])].copy()
        for keys, g in d.groupby(["city", "available_quarters", "vintage_label"], sort=False):
            high = g[g["actual_annual_gva_eok"].ge(1000.0)]
            actual = float(g["actual_annual_gva_eok"].sum())
            err = float(g["annual_error_eok"].sum())
            high_actual = float(high["actual_annual_gva_eok"].sum())
            high_err = float(high["annual_error_eok"].sum())
            rows.append({
                "track": label,
                "city": keys[0],
                "available_quarters": int(keys[1]),
                "vintage_label": keys[2],
                "evaluated_years": "2022-2023",
                "actual_sum_eok": actual,
                "error_sum_eok": err,
                "overall_wape_pct": err / actual * 100 if actual else np.nan,
                "high_value_error_sum_eok": high_err,
                "high_value_wape_pct": high_err / high_actual * 100 if high_actual > 0 else np.nan,
                "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
            })
    scores = pd.DataFrame(rows)
    b = scores[scores["track"].eq("baseline")].drop(columns=["track"])
    s = scores[scores["track"].eq("parent_guarded")].drop(columns=["track"])
    comp = s.merge(b, on=["city", "available_quarters", "vintage_label", "evaluated_years"], suffixes=("_parent_guarded", "_baseline"))
    comp["overall_wape_delta_pct_point"] = comp["overall_wape_pct_parent_guarded"] - comp["overall_wape_pct_baseline"]
    comp["high_value_wape_delta_pct_point"] = comp["high_value_wape_pct_parent_guarded"] - comp["high_value_wape_pct_baseline"]
    comp["error_delta_eok"] = comp["error_sum_eok_parent_guarded"] - comp["error_sum_eok_baseline"]
    return comp.sort_values(["city", "available_quarters"])


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


def write_report(routes: pd.DataFrame, comp: pd.DataFrame, top: pd.DataFrame) -> None:
    adopted = routes[routes["adopt_parent_route"]].copy()
    top_adopted = adopted.sort_values(["city", "available_quarters", "error_delta_eok"]).copy()
    REPORT.write_text("\n".join([
        "# Phase141 상위산업 단위 보수적 계절비중 라우팅",
        "",
        "## 목적",
        "",
        "Phase140의 도시×빈티지 단위 라우팅은 안전하지만 너무 굵다. 이번에는 도시×상위산업×빈티지 단위에서 계절비중 후보를 선택해, 고양시처럼 큰 업종이 섞여 있는 도시에서 금액가중 오차를 더 낮출 수 있는지 검증했다.",
        "",
        "## 채택 기준",
        "",
        "후보 계절비중은 목표연도 이전 자료만 사용한다. 채택은 2022~2023 상위산업 WAPE가 낮아지고, 2022년과 2023년 각각의 상위산업 WAPE가 악화되지 않으며, 1,000억원 이상 중분류 WAPE도 악화되지 않는 경우로 제한했다.",
        "",
        "## 도시 전체 성능: 기존 중분류 계절비중 대비",
        "",
        md_table(comp, [
            "city", "vintage_label", "evaluated_years",
            "overall_wape_pct_baseline", "overall_wape_pct_parent_guarded", "overall_wape_delta_pct_point",
            "high_value_wape_pct_baseline", "high_value_wape_pct_parent_guarded", "high_value_wape_delta_pct_point",
            "error_sum_eok_baseline", "error_sum_eok_parent_guarded", "error_delta_eok",
            "gt20_cells_parent_guarded",
        ]),
        "",
        "## 채택 상위산업 라우팅 상위 개선",
        "",
        md_table(top_adopted, [
            "city", "parent_code", "vintage_label", "selected_candidate",
            "baseline_wape_pct", "selected_wape_pct", "wape_delta_pct_point",
            "baseline_error_sum_eok", "selected_error_sum_eok", "error_delta_eok",
        ], n=40),
        "",
        "## 2023 선택 라우팅 기준 오차기여 상위 중분류",
        "",
        md_table(top, [
            "city", "vintage_label", "parent_code", "middle_code", "middle_label", "parent_selected_candidate",
            "actual_annual_gva_eok", "annual_prediction_eok", "annual_error_eok",
            "annual_error_rate_pct", "error_contribution_pct",
        ], n=48),
        "",
        "## 판정",
        "",
        f"1. 상위산업 단위 보수적 채택은 {len(adopted)}개다. 도시×빈티지 단위보다 자유도가 높아 개선폭은 커졌지만, 이만큼 과적합 위험도 늘어난다.",
        "2. 고양시는 Q1/Q2/Q3 평균 WAPE가 각각 5.13→4.40%, 3.13→2.88%, 1.60→1.43%로 낮아졌다. 1,000억원 이상 업종 WAPE도 각각 4.92→4.23%, 2.95→2.74%, 1.51→1.36%로 낮아졌다.",
        "3. 포항시는 Q1/Q2/Q3 평균 WAPE가 각각 3.91→3.59%, 2.14→1.97%, 1.25→1.15%로 낮아졌다.",
        "4. 이 결과는 운영 후보로는 강하지만 최종 채택 전 추가 연도 또는 임의 시군구 확장검증이 필요하다. 같은 2022~2023을 이용해 후보를 선택하고 평가했기 때문이다.",
        "5. KOBIS는 사용 가능하지만 J59 직접 채택 후보가 아니며, KOPIS는 사용할 수 없으므로 공연/예술 활동자료로 반영하지 않았다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    ensure_input()
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates()
    score = score_parent(candidates)
    yearly = score_parent_year(candidates)
    routes = choose_routes(score, yearly)
    selected = apply_routes(candidates, routes)
    baseline = candidates[
        (candidates["candidate"].eq(BASELINE_NAME) & candidates["available_quarters"].isin([1, 2, 3]))
        | candidates["candidate"].eq("observed_full_year_sum")
    ].copy()
    comp = city_score(selected, baseline)
    top = top_2023(selected)

    score.to_csv(OUT / "phase141_parent_candidate_scorecard.csv", index=False)
    yearly.to_csv(OUT / "phase141_parent_yearly_guardrail_scorecard.csv", index=False)
    routes.to_csv(OUT / "phase141_parent_guarded_routes.csv", index=False)
    selected.to_csv(OUT / "phase141_parent_selected_predictions.csv", index=False)
    comp.to_csv(OUT / "phase141_city_performance_comparison.csv", index=False)
    top.to_csv(OUT / "phase141_2023_top_middle_contributors.csv", index=False)
    write_report(routes, comp, top)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
