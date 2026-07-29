#!/usr/bin/env python3
"""Phase253 all-available-activity rolling route selection.

Purpose
-------
Previous ``no-worse`` diagnostics are useful as an upper-bound signal, but
they are not an operational policy because they can inspect target-year
actuals.  This experiment builds a route-selection policy that can be audited:

* for target year y, use only years < y to choose a route;
* apply the frozen route/weight to y;
* evaluate against y actuals only after the decision is fixed.

The candidate sources are the public activity indicators already harvested in
the nationwide pipeline:

* regional manufacturing production index;
* regional service production indexes by service block;
* regional construction orders raw and BOK-style distributed order stock.

The output is still a latest-vintage backtest, not a complete historical
release-vintage nowcast.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "nationwide"
OUT = HERE / "outputs"
REPORT = HERE / "phase253_all_activity_rolling_route_selection.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

ALL_REGIONS = [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기도",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]
WEIGHTS = [0.0, 0.25, 0.50, 0.75, 1.0]
GRDP_REPLACE_ACTIVITIES = ["광업, 제조업", "건설업", "서비스업"]


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def load_indicator_module():
    path = HERE / "run_hard_region_indicator_route_experiment.py"
    spec = importlib.util.spec_from_file_location("hard_route", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Reuse the source builders, but expand their hard-region scope to all
    # 17 metropolitan regions.
    mod.HARD_REGIONS = ALL_REGIONS
    return mod


def route_predictions_no_target_actual(panel: pd.DataFrame) -> pd.DataFrame:
    """Build candidate predictions without joining target-year official actuals."""
    mod = load_indicator_module()
    annual = mod.annual_official()
    rows = []
    for (region, activity, route_id, year), g in panel[panel["year"].between(2021, 2025)].groupby(
        ["quarter_region", "activity", "route_id", "year"]
    ):
        prev = panel[
            panel["quarter_region"].eq(region)
            & panel["activity"].eq(activity)
            & panel["route_id"].eq(route_id)
            & panel["year"].eq(year - 1)
        ]
        if prev.empty:
            continue
        basis = annual[
            annual["quarter_region"].eq(region)
            & annual["activity"].eq(activity)
            & annual["year"].eq(year - 1)
        ]
        if basis.empty:
            continue
        prev_annual_indicator = float(prev["indicator_value"].sum())
        if prev_annual_indicator == 0:
            continue
        prev_by_q = prev.set_index("quarter")["indicator_value"].to_dict()
        g = g.sort_values("quarter")
        for k in [1, 2, 3, 4]:
            cur_cum = float(g[g["quarter"].le(k)]["indicator_value"].sum())
            prev_cum = float(sum(v for q, v in prev_by_q.items() if q <= k))
            if prev_cum == 0:
                continue
            basis_eok = float(basis["official_annual_eok"].iloc[0])
            rows.append(
                {
                    "quarter_region": region,
                    "activity": activity,
                    "route_id": route_id,
                    "year": int(year),
                    "available_quarters": int(k),
                    "candidate_cumulative_eok": basis_eok * cur_cum / prev_annual_indicator,
                    "candidate_annualized_eok": basis_eok * cur_cum / prev_cum,
                    "candidate_basis_annual_year": int(year - 1),
                    "candidate_uses_target_year_actual": "N",
                }
            )
    return pd.DataFrame(rows)


def build_candidate_detail() -> pd.DataFrame:
    mod = load_indicator_module()
    base = pd.read_csv(OUT / "operating_point_sido_activity_validation.csv")
    base["available_quarters"] = base["available_quarters_x"].fillna(base["available_quarters"]).astype(int)
    base = base[
        base["quarter_region"].isin(ALL_REGIONS)
        & base["track"].isin(["recursive_no_target_actual", "prior_year_province_anchor"])
    ].copy()
    panel = mod.make_indicator_panel()
    panel = panel[panel["quarter_region"].isin(ALL_REGIONS)].copy()
    cand = route_predictions_no_target_actual(panel)
    merged = cand.merge(
        base[
            [
                "track",
                "quarter_region",
                "activity",
                "year",
                "available_quarters",
                "annualized_predicted_eok",
                "official_annual_eok",
                "annualized_error_eok",
                "annualized_ape_pct",
            ]
        ],
        on=["quarter_region", "activity", "year", "available_quarters"],
        how="inner",
    )
    merged["candidate_annualized_error_eok"] = merged["candidate_annualized_eok"] - merged["official_annual_eok"]
    merged["baseline_abs_error_eok"] = merged["annualized_error_eok"].abs()
    merged["candidate_abs_error_eok"] = merged["candidate_annualized_error_eok"].abs()
    merged["candidate_ape_pct"] = merged["candidate_abs_error_eok"] / merged["official_annual_eok"].abs() * 100
    return merged


def score_prior(prior: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for route_id, rg in prior.groupby("route_id"):
        baseline_abs = rg["baseline_abs_error_eok"]
        actual = rg["official_annual_eok"].abs()
        baseline_ape = rg["annualized_ape_pct"]
        baseline_wape = baseline_abs.sum() / actual.sum() * 100 if actual.sum() else float("nan")
        for weight in WEIGHTS:
            pred = rg["annualized_predicted_eok"] + weight * (
                rg["candidate_annualized_eok"] - rg["annualized_predicted_eok"]
            )
            err = (pred - rg["official_annual_eok"]).abs()
            ape = err / actual * 100
            selected_wape = err.sum() / actual.sum() * 100 if actual.sum() else float("nan")
            rows.append(
                {
                    "route_id": route_id,
                    "weight": weight,
                    "prior_rows": int(len(rg)),
                    "prior_year_min": int(rg["year"].min()),
                    "prior_year_max": int(rg["year"].max()),
                    "prior_baseline_wape_pct": float(baseline_wape),
                    "prior_selected_wape_pct": float(selected_wape),
                    "prior_delta_wape_pp": float(selected_wape - baseline_wape),
                    "prior_baseline_abs_error_eok": float(baseline_abs.sum()),
                    "prior_selected_abs_error_eok": float(err.sum()),
                    "prior_error_reduction_eok": float(baseline_abs.sum() - err.sum()),
                    "prior_baseline_over10_cells": int((baseline_ape > 10).sum()),
                    "prior_selected_over10_cells": int((ape > 10).sum()),
                    "prior_baseline_over20_cells": int((baseline_ape > 20).sum()),
                    "prior_selected_over20_cells": int((ape > 20).sum()),
                    "prior_baseline_max_ape_pct": float(baseline_ape.max()),
                    "prior_selected_max_ape_pct": float(ape.max()),
                }
            )
    return pd.DataFrame(rows)


def choose_route(score: pd.DataFrame) -> tuple[str, float, str]:
    if score.empty:
        return "baseline", 0.0, "no_prior_rows"
    safe = score[
        score["weight"].gt(0)
        & score["prior_selected_wape_pct"].lt(score["prior_baseline_wape_pct"])
        & score["prior_selected_over10_cells"].le(score["prior_baseline_over10_cells"])
        & score["prior_selected_over20_cells"].le(score["prior_baseline_over20_cells"])
        & score["prior_selected_max_ape_pct"].le(score["prior_baseline_max_ape_pct"] + 1e-12)
    ].copy()
    if safe.empty:
        return "baseline", 0.0, "no_prior_guardrail_pass"
    safe = safe.sort_values(
        ["prior_error_reduction_eok", "prior_delta_wape_pp", "prior_rows", "weight"],
        ascending=[False, True, False, True],
    )
    r = safe.iloc[0]
    return (
        str(r["route_id"]),
        float(r["weight"]),
        "prior_wape_improved_over10_over20_max_nonworse",
    )


def rolling_select(cand: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, float | int | str]] = []
    decisions: list[dict[str, float | int | str]] = []
    keys = ["track", "quarter_region", "activity", "available_quarters"]
    for key, g in cand.groupby(keys):
        track, region, activity, k = key
        g = g.sort_values(["year", "route_id"]).copy()
        for year in sorted(g["year"].unique()):
            current = g[g["year"].eq(year)].copy()
            if current.empty:
                continue
            base = current.iloc[0]
            prior = g[g["year"].lt(year)].copy()
            score = score_prior(prior) if not prior.empty else pd.DataFrame()
            route_id, weight, basis = choose_route(score)
            prior_rows = int(score["prior_rows"].max()) if not score.empty else 0
            prior_best_error_reduction = float(score["prior_error_reduction_eok"].max()) if not score.empty else 0.0
            selected_pred = float(base["annualized_predicted_eok"])
            if route_id != "baseline":
                sr = current[current["route_id"].eq(route_id)]
                if not sr.empty:
                    cr = sr.iloc[0]
                    selected_pred = float(cr["annualized_predicted_eok"]) + weight * (
                        float(cr["candidate_annualized_eok"]) - float(cr["annualized_predicted_eok"])
                    )
                else:
                    route_id = "baseline"
                    weight = 0.0
                    basis = "selected_route_not_available_in_target_year"
            decisions.append(
                {
                    "track": track,
                    "quarter_region": region,
                    "activity": activity,
                    "available_quarters": int(k),
                    "target_year": int(year),
                    "selected_route_id": route_id,
                    "selected_weight": weight,
                    "decision_basis": basis,
                    "prior_rows": prior_rows,
                    "prior_best_error_reduction_eok": prior_best_error_reduction,
                }
            )
            actual = float(base["official_annual_eok"])
            baseline_err = float(base["annualized_predicted_eok"]) - actual
            selected_err = selected_pred - actual
            rows.append(
                {
                    "track": track,
                    "quarter_region": region,
                    "activity": activity,
                    "year": int(year),
                    "available_quarters": int(k),
                    "selected_route_id": route_id,
                    "selected_weight": weight,
                    "decision_basis": basis,
                    "baseline_predicted_eok": float(base["annualized_predicted_eok"]),
                    "selected_predicted_eok": selected_pred,
                    "official_annual_eok": actual,
                    "baseline_error_eok": baseline_err,
                    "selected_error_eok": selected_err,
                    "baseline_abs_error_eok": abs(baseline_err),
                    "selected_abs_error_eok": abs(selected_err),
                    "baseline_ape_pct": abs(baseline_err) / abs(actual) * 100 if actual else float("nan"),
                    "selected_ape_pct": abs(selected_err) / abs(actual) * 100 if actual else float("nan"),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(decisions)


def summarize(sel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    def agg_frame(keys: list[str]) -> pd.DataFrame:
        s = (
            sel.groupby(keys, as_index=False)
            .agg(
                rows=("year", "count"),
                adopted_rows=("selected_route_id", lambda x: int((x != "baseline").sum())),
                official_sum_eok=("official_annual_eok", lambda x: x.abs().sum()),
                baseline_abs_error_sum_eok=("baseline_abs_error_eok", "sum"),
                selected_abs_error_sum_eok=("selected_abs_error_eok", "sum"),
                baseline_over10_cells=("baseline_ape_pct", lambda x: int((x > 10).sum())),
                selected_over10_cells=("selected_ape_pct", lambda x: int((x > 10).sum())),
                baseline_over20_cells=("baseline_ape_pct", lambda x: int((x > 20).sum())),
                selected_over20_cells=("selected_ape_pct", lambda x: int((x > 20).sum())),
                baseline_max_ape_pct=("baseline_ape_pct", "max"),
                selected_max_ape_pct=("selected_ape_pct", "max"),
            )
        )
        s["baseline_wape_pct"] = s["baseline_abs_error_sum_eok"] / s["official_sum_eok"] * 100
        s["selected_wape_pct"] = s["selected_abs_error_sum_eok"] / s["official_sum_eok"] * 100
        s["delta_wape_pp"] = s["selected_wape_pct"] - s["baseline_wape_pct"]
        return s

    operating = agg_frame(["track", "available_quarters"])
    activity = agg_frame(["track", "activity", "available_quarters"])
    region = agg_frame(["track", "quarter_region", "available_quarters"])
    route = (
        sel[sel["selected_route_id"].ne("baseline")]
        .groupby(["track", "activity", "available_quarters", "selected_route_id", "selected_weight"], as_index=False)
        .size()
        .rename(columns={"size": "adopted_rows"})
        .sort_values(["track", "activity", "available_quarters", "adopted_rows"], ascending=[True, True, True, False])
    )
    return operating, activity, region, route


def recompute_grdp(sel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    op_total = pd.read_csv(OUT / "operating_point_sido_grdp_validation.csv")
    repl = sel[sel["activity"].isin(GRDP_REPLACE_ACTIVITIES)].copy()
    adj = (
        repl.groupby(["track", "quarter_region", "year", "available_quarters"], as_index=False)
        .agg(
            baseline_replaced_pred=("baseline_predicted_eok", "sum"),
            selected_replaced_pred=("selected_predicted_eok", "sum"),
            adopted_replaced_rows=("selected_route_id", lambda x: int((x != "baseline").sum())),
        )
    )
    grdp = op_total.merge(adj, on=["track", "quarter_region", "year", "available_quarters"], how="left")
    for c in ["baseline_replaced_pred", "selected_replaced_pred", "adopted_replaced_rows"]:
        grdp[c] = grdp[c].fillna(0.0)
    grdp["rolling_route_annualized_predicted_grdp_eok"] = (
        grdp["annualized_predicted_grdp_eok"] + grdp["selected_replaced_pred"] - grdp["baseline_replaced_pred"]
    )
    grdp["rolling_route_error_eok"] = (
        grdp["rolling_route_annualized_predicted_grdp_eok"] - grdp["official_annual_grdp_eok"]
    )
    grdp["rolling_route_ape_pct"] = grdp["rolling_route_error_eok"].abs() / grdp["official_annual_grdp_eok"].abs() * 100
    summary = (
        grdp.groupby(["track", "available_quarters", "operating_label"], as_index=False)
        .agg(
            rows=("year", "count"),
            adopted_replaced_rows=("adopted_replaced_rows", "sum"),
            official_sum_eok=("official_annual_grdp_eok", lambda x: x.abs().sum()),
            baseline_abs_error_sum_eok=("annualized_error_eok", lambda x: x.abs().sum()),
            selected_abs_error_sum_eok=("rolling_route_error_eok", lambda x: x.abs().sum()),
            baseline_over10_cells=("annualized_ape_pct", lambda x: int((x > 10).sum())),
            selected_over10_cells=("rolling_route_ape_pct", lambda x: int((x > 10).sum())),
            baseline_over20_cells=("annualized_ape_pct", lambda x: int((x > 20).sum())),
            selected_over20_cells=("rolling_route_ape_pct", lambda x: int((x > 20).sum())),
            baseline_max_ape_pct=("annualized_ape_pct", "max"),
            selected_max_ape_pct=("rolling_route_ape_pct", "max"),
        )
    )
    summary["baseline_wape_pct"] = summary["baseline_abs_error_sum_eok"] / summary["official_sum_eok"] * 100
    summary["selected_wape_pct"] = summary["selected_abs_error_sum_eok"] / summary["official_sum_eok"] * 100
    summary["delta_wape_pp"] = summary["selected_wape_pct"] - summary["baseline_wape_pct"]
    return grdp, summary


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cand = build_candidate_detail()
    sel, decisions = rolling_select(cand)
    operating, activity, region, route = summarize(sel)
    grdp, grdp_summary = recompute_grdp(sel)

    cand.to_csv(OUT / "phase253_all_activity_candidate_detail.csv", index=False, encoding="utf-8-sig")
    sel.to_csv(OUT / "phase253_all_activity_rolling_selection_detail.csv", index=False, encoding="utf-8-sig")
    decisions.to_csv(OUT / "phase253_all_activity_rolling_decisions.csv", index=False, encoding="utf-8-sig")
    operating.to_csv(OUT / "phase253_all_activity_operating_summary.csv", index=False, encoding="utf-8-sig")
    activity.to_csv(OUT / "phase253_all_activity_activity_summary.csv", index=False, encoding="utf-8-sig")
    region.to_csv(OUT / "phase253_all_activity_region_summary.csv", index=False, encoding="utf-8-sig")
    route.to_csv(OUT / "phase253_all_activity_route_summary.csv", index=False, encoding="utf-8-sig")
    grdp.to_csv(OUT / "phase253_all_activity_grdp_detail.csv", index=False, encoding="utf-8-sig")
    grdp_summary.to_csv(OUT / "phase253_all_activity_grdp_summary.csv", index=False, encoding="utf-8-sig")

    headline = grdp_summary[grdp_summary["track"].eq("recursive_no_target_actual")].copy()
    op_head = operating[operating["track"].eq("recursive_no_target_actual")].copy()
    act_best = (
        activity[activity["track"].eq("recursive_no_target_actual")]
        .sort_values(["delta_wape_pp", "selected_wape_pct"], ascending=[True, True])
        .head(20)
    )
    act_worst = (
        activity[activity["track"].eq("recursive_no_target_actual")]
        .sort_values(["delta_wape_pp", "selected_wape_pct"], ascending=[False, False])
        .head(20)
    )
    leakage = pd.DataFrame(
        [
            {
                "audit_item": "target_year_actual_in_selection",
                "result": "not_used",
                "evidence": "target year row is evaluated only after route_id/weight are selected from years < target_year",
            },
            {
                "audit_item": "first_year_route",
                "result": "baseline_only",
                "evidence": "the first candidate year in each route group has no prior validation year and is forced to baseline",
            },
            {
                "audit_item": "candidate_scope",
                "result": "public_activity_indicators_only",
                "evidence": "candidate prediction table contains only indicator-based predictions; target-year official values are joined later for evaluation",
            },
            {
                "audit_item": "strict_nowcast_claim",
                "result": "not_claimed",
                "evidence": "latest-vintage public indicators are used; historical publication-vintage ledger remains incomplete",
            },
        ]
    )

    report = f"""# Phase253 전 업종 후보 rolling route 선택 검증

생성시각: {CREATED_AT}

## 목적

`no-worse` 방식은 목표연도 실제값을 확인한 뒤 좋아지는 셀만 채택할 수 있어 운영 성능으로 주장하기 어렵다. Phase253는 목표연도 `y`에 대해 **`y` 이전 연도 성과만으로 활동자료 사용 여부를 결정**한 뒤, 그 결정값을 `y`에 적용해 검증한다.

## 채택 규칙

| 항목 | 내용 |
| --- | --- |
| 대상 | 17개 시도 × 공개 활동지표가 있는 업종 × 2021~2025 × 운영시점 |
| 후보 활동자료 | 제조업 생산지수, 서비스업생산지수, 건설수주 원지표, 건설수주 BOK식 분산지표 |
| 후보 가중치 | 기준방식 0%, 활동자료 25%, 50%, 75%, 100% 혼합 |
| 사전 선택 | 목표연도 이전 연도만 사용 |
| 통과 조건 | prior WAPE 개선, 10% 초과 셀 비증가, 20% 초과 셀 비증가, 최대오차율 비악화 |
| 미통과 | 기준 계층배분 유지 |
| 해석 | 최신 빈티지 사후 백테스트. Q+1개월 strict 빈티지 성능은 별도 공표일 장부 필요 |

## 누수 방지 점검

{md_table(leakage, 3)}

## 업종 연간환산 기준 운영시점 결과

{md_table(op_head[[
    "available_quarters", "rows", "adopted_rows", "baseline_wape_pct", "selected_wape_pct",
    "delta_wape_pp", "baseline_over10_cells", "selected_over10_cells",
    "baseline_over20_cells", "selected_over20_cells", "baseline_max_ape_pct", "selected_max_ape_pct"
]].rename(columns={
    "available_quarters": "사용분기수",
    "rows": "검증셀",
    "adopted_rows": "채택셀",
    "baseline_wape_pct": "기준WAPE_pct",
    "selected_wape_pct": "rolling선택WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_cells": "기준10pct초과",
    "selected_over10_cells": "선택10pct초과",
    "baseline_over20_cells": "기준20pct초과",
    "selected_over20_cells": "선택20pct초과",
    "baseline_max_ape_pct": "기준최대오차율_pct",
    "selected_max_ape_pct": "선택최대오차율_pct",
}), 3)}

## GRDP 총량 재집계 결과

GRDP 재집계는 중복을 피하기 위해 `광업, 제조업`, `건설업`, `서비스업` 3개 대분류 대체분만 반영한다. 서비스 세부업종 결과는 업종 진단에는 포함하지만 GRDP 총량에는 별도 중복 합산하지 않는다.

{md_table(headline[[
    "available_quarters", "operating_label", "rows", "adopted_replaced_rows",
    "baseline_wape_pct", "selected_wape_pct", "delta_wape_pp",
    "baseline_over10_cells", "selected_over10_cells",
    "baseline_over20_cells", "selected_over20_cells",
    "baseline_max_ape_pct", "selected_max_ape_pct"
]].rename(columns={
    "available_quarters": "사용분기수",
    "operating_label": "운영시점",
    "rows": "시도연도셀",
    "adopted_replaced_rows": "대체채택행",
    "baseline_wape_pct": "기준GRDP_WAPE_pct",
    "selected_wape_pct": "선택GRDP_WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_cells": "기준10pct초과",
    "selected_over10_cells": "선택10pct초과",
    "baseline_over20_cells": "기준20pct초과",
    "selected_over20_cells": "선택20pct초과",
    "baseline_max_ape_pct": "기준최대오차율_pct",
    "selected_max_ape_pct": "선택최대오차율_pct",
}), 3)}

## rolling 선택으로 개선된 대표 업종

{md_table(act_best[[
    "activity", "available_quarters", "rows", "adopted_rows", "baseline_wape_pct", "selected_wape_pct",
    "delta_wape_pp", "baseline_over10_cells", "selected_over10_cells", "selected_max_ape_pct"
]].rename(columns={
    "activity": "업종",
    "available_quarters": "사용분기수",
    "rows": "검증셀",
    "adopted_rows": "채택셀",
    "baseline_wape_pct": "기준WAPE_pct",
    "selected_wape_pct": "선택WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_cells": "기준10pct초과",
    "selected_over10_cells": "선택10pct초과",
    "selected_max_ape_pct": "선택최대오차율_pct",
}), 3)}

## rolling 선택 후에도 악화된 대표 업종

{md_table(act_worst[[
    "activity", "available_quarters", "rows", "adopted_rows", "baseline_wape_pct", "selected_wape_pct",
    "delta_wape_pp", "baseline_over10_cells", "selected_over10_cells", "selected_max_ape_pct"
]].rename(columns={
    "activity": "업종",
    "available_quarters": "사용분기수",
    "rows": "검증셀",
    "adopted_rows": "채택셀",
    "baseline_wape_pct": "기준WAPE_pct",
    "selected_wape_pct": "선택WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_cells": "기준10pct초과",
    "selected_over10_cells": "선택10pct초과",
    "selected_max_ape_pct": "선택최대오차율_pct",
}), 3)}

## 판단

- 목표연도 actual을 route 선택에 사용하지 않아 기존 no-worse 진단보다 누수 위험은 낮다.
- 그러나 전국 전체에 일괄 채택할 운영 근거로는 아직 부족하다. 일부 업종·운영시점은 prior guardrail을 통과해도 holdout에서 악화된다.
- 공개 산출물에서는 `기준 계층배분`과 `rolling 사전선택`을 함께 제시하고, 개선된 항목만 대표성과로 과장하지 않는다.
- 다음 개선축은 route 자체보다 **공표일 장부를 붙인 빈티지별 속보 검증**과 **시군구 공간배분용 직접 활동자료 보강**이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(op_head.to_string(index=False))
    print(headline.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
