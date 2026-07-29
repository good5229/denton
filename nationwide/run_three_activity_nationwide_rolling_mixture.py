#!/usr/bin/env python3
"""Nationwide rolling mixture experiment for three routed activities.

This extends the older five-hard-region route experiment to all 17
metropolitan regions, but limits the number of special activities to three:

* 건설업
* 운수 및 창고업
* 숙박 및 음식점업

Selection is rolling and pre-validation based: for target year y, candidate
route/weight pairs are selected only from years < y. Target-year actuals are
used only for evaluation after the selection is fixed.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "nationwide"
OUT = HERE / "outputs"
REPORT = HERE / "three_activity_nationwide_rolling_mixture.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

TARGET_ACTIVITIES = ["건설업", "운수 및 창고업", "숙박 및 음식점업"]
WEIGHTS = [0.0, 0.25, 0.50, 0.75, 1.0]
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


def load_hard_module():
    path = HERE / "run_hard_region_indicator_route_experiment.py"
    spec = importlib.util.spec_from_file_location("hard_route", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.HARD_REGIONS = ALL_REGIONS
    return mod


def wape(err: pd.Series, actual: pd.Series) -> float:
    denom = actual.abs().sum()
    if denom == 0:
        return float("nan")
    return float(err.abs().sum() / denom * 100)


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


def build_candidate_detail() -> pd.DataFrame:
    mod = load_hard_module()
    base = pd.read_csv(OUT / "operating_point_sido_activity_validation.csv")
    base["available_quarters"] = base["available_quarters_x"].fillna(base["available_quarters"]).astype(int)
    base = base[
        base["quarter_region"].isin(ALL_REGIONS)
        & base["activity"].isin(TARGET_ACTIVITIES)
        & base["track"].eq("recursive_no_target_actual")
    ].copy()
    panel = mod.make_indicator_panel()
    panel = panel[panel["quarter_region"].isin(ALL_REGIONS) & panel["activity"].isin(TARGET_ACTIVITIES)].copy()
    cand = mod.route_predictions(panel)
    cand = cand[cand["activity"].isin(TARGET_ACTIVITIES)].copy()
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
        on=["quarter_region", "activity", "year", "available_quarters", "official_annual_eok"],
        how="inner",
    )
    merged["baseline_abs_error_eok"] = merged["annualized_error_eok"].abs()
    merged["candidate_abs_error_eok"] = merged["candidate_annualized_error_eok"].abs()
    return merged


def rolling_select(cand: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["track", "quarter_region", "activity", "available_quarters"]
    for key, g in cand.groupby(keys):
        track, region, activity, k = key
        g = g.sort_values(["year", "route_id"]).copy()
        years = sorted(g["year"].unique())
        for year in years:
            current = g[g["year"].eq(year)].copy()
            if current.empty:
                continue
            base_row = current.iloc[0]
            selected_route = "baseline"
            selected_weight = 0.0
            selected_basis = "no_prior_safe_candidate"
            prior = g[g["year"].lt(year)].copy()
            if not prior.empty:
                trial_rows = []
                for route_id, rg in prior.groupby("route_id"):
                    for weight in WEIGHTS:
                        pred = rg["annualized_predicted_eok"] + weight * (
                            rg["candidate_annualized_eok"] - rg["annualized_predicted_eok"]
                        )
                        err = (pred - rg["official_annual_eok"]).abs()
                        recent = rg[rg["year"].ge(year - 2)].copy()
                        if recent.empty:
                            recent_worse = 0
                        else:
                            recent_pred = recent["annualized_predicted_eok"] + weight * (
                                recent["candidate_annualized_eok"] - recent["annualized_predicted_eok"]
                            )
                            recent_err = (recent_pred - recent["official_annual_eok"]).abs()
                            recent_worse = int((recent_err > recent["baseline_abs_error_eok"] + 1e-9).sum())
                        trial_rows.append(
                            {
                                "route_id": route_id,
                                "weight": weight,
                                "prior_rows": len(rg),
                                "prior_baseline_abs_error_eok": float(rg["baseline_abs_error_eok"].sum()),
                                "prior_candidate_abs_error_eok": float(err.sum()),
                                "prior_improvement_eok": float(rg["baseline_abs_error_eok"].sum() - err.sum()),
                                "recent_worse_rows": recent_worse,
                            }
                        )
                score = pd.DataFrame(trial_rows)
                safe = score[(score["weight"] > 0) & (score["prior_improvement_eok"] > 0) & (score["recent_worse_rows"] == 0)].copy()
                if not safe.empty:
                    safe = safe.sort_values(["prior_improvement_eok", "prior_rows", "weight"], ascending=[False, False, True])
                    selected_route = str(safe.iloc[0]["route_id"])
                    selected_weight = float(safe.iloc[0]["weight"])
                    selected_basis = (
                        f"prior_improvement_{float(safe.iloc[0]['prior_improvement_eok']):.3f}_eok"
                        f"_recent_worse_{int(safe.iloc[0]['recent_worse_rows'])}"
                    )
            selected_current = current[current["route_id"].eq(selected_route)]
            if selected_route == "baseline" or selected_current.empty:
                candidate_pred = float(base_row["annualized_predicted_eok"])
            else:
                cr = selected_current.iloc[0]
                candidate_pred = float(cr["annualized_predicted_eok"]) + selected_weight * (
                    float(cr["candidate_annualized_eok"]) - float(cr["annualized_predicted_eok"])
                )
            actual = float(base_row["official_annual_eok"])
            selected_error = candidate_pred - actual
            rows.append(
                {
                    "track": track,
                    "quarter_region": region,
                    "activity": activity,
                    "available_quarters": int(k),
                    "year": int(year),
                    "selected_route_id": selected_route,
                    "selected_weight": selected_weight,
                    "selected_basis": selected_basis,
                    "baseline_predicted_eok": float(base_row["annualized_predicted_eok"]),
                    "selected_predicted_eok": candidate_pred,
                    "official_annual_eok": actual,
                    "baseline_abs_error_eok": float(base_row["baseline_abs_error_eok"]),
                    "selected_abs_error_eok": abs(selected_error),
                    "baseline_ape_pct": float(base_row["annualized_ape_pct"]),
                    "selected_ape_pct": abs(selected_error) / abs(actual) * 100 if actual else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def summarize(sel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    activity = (
        sel.groupby(["activity", "available_quarters"], as_index=False)
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
    activity["baseline_wape_pct"] = activity["baseline_abs_error_sum_eok"] / activity["official_sum_eok"] * 100
    activity["selected_wape_pct"] = activity["selected_abs_error_sum_eok"] / activity["official_sum_eok"] * 100
    activity["delta_wape_pp"] = activity["selected_wape_pct"] - activity["baseline_wape_pct"]

    operating = (
        sel.groupby("available_quarters", as_index=False)
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
        )
    )
    operating["baseline_wape_pct"] = operating["baseline_abs_error_sum_eok"] / operating["official_sum_eok"] * 100
    operating["selected_wape_pct"] = operating["selected_abs_error_sum_eok"] / operating["official_sum_eok"] * 100
    operating["delta_wape_pp"] = operating["selected_wape_pct"] - operating["baseline_wape_pct"]

    route = (
        sel[sel["selected_route_id"].ne("baseline")]
        .groupby(["activity", "available_quarters", "selected_route_id", "selected_weight"], as_index=False)
        .size()
        .rename(columns={"size": "adopted_rows"})
        .sort_values(["activity", "available_quarters", "adopted_rows"], ascending=[True, True, False])
    )
    policy = activity.copy()
    policy["recommended_action"] = "baseline 유지"
    accept = (
        policy["selected_wape_pct"].lt(policy["baseline_wape_pct"])
        & policy["selected_wape_pct"].le(10)
        & policy["selected_over10_cells"].le(policy["baseline_over10_cells"])
        & policy["selected_over20_cells"].le(policy["baseline_over20_cells"])
        & policy["selected_max_ape_pct"].le(policy["baseline_max_ape_pct"])
    )
    policy.loc[accept, "recommended_action"] = "rolling mixture 채택"
    policy["reason"] = "평균WAPE/10%초과/20%초과/최대오차율 중 하나 이상 악화 또는 WAPE 10% 초과"
    policy.loc[accept, "reason"] = "모든 guardrail 통과"
    return activity, operating, route, policy


def main() -> int:
    cand = build_candidate_detail()
    sel = rolling_select(cand)
    activity, operating, route, policy = summarize(sel)
    cand.to_csv(OUT / "three_activity_nationwide_candidate_detail.csv", index=False, encoding="utf-8-sig")
    sel.to_csv(OUT / "three_activity_nationwide_rolling_mixture_detail.csv", index=False, encoding="utf-8-sig")
    activity.to_csv(OUT / "three_activity_nationwide_rolling_mixture_activity_summary.csv", index=False, encoding="utf-8-sig")
    operating.to_csv(OUT / "three_activity_nationwide_rolling_mixture_operating_summary.csv", index=False, encoding="utf-8-sig")
    route.to_csv(OUT / "three_activity_nationwide_rolling_mixture_route_summary.csv", index=False, encoding="utf-8-sig")
    policy.to_csv(OUT / "three_activity_nationwide_recommended_policy.csv", index=False, encoding="utf-8-sig")

    report = f"""# 전국 3개 업종 rolling mixture 라우팅 실험

생성시각: {CREATED_AT}

## 목적

과학자 검토 의견에 따라 모든 업종을 특화하지 않고 `건설업`, `운수 및 창고업`, `숙박 및 음식점업` 3개 업종만 대상으로 활동지표 route를 시험했다.

## 누수 방지 규칙

| 항목 | 적용 |
| --- | --- |
| 목표연도 actual | route 선택에는 사용하지 않음. 선택 후 평가에만 사용 |
| 후보 가중치 | 0%, 25%, 50%, 75%, 100% |
| 선택 기준 | target year 이전 연도의 누적 절대오차 개선 |
| 최근 악화 방지 | 최근 2년 prior 중 후보가 기준선보다 악화된 행이 있으면 미채택 |
| 대상 업종 수 | 3개로 고정 |

## 운영시점별 결과

{md_table(operating.rename(columns={
    "available_quarters": "사용분기수",
    "rows": "검증셀",
    "adopted_rows": "채택셀",
    "baseline_wape_pct": "기준WAPE_pct",
    "selected_wape_pct": "선택WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_cells": "기준10pct초과",
    "selected_over10_cells": "선택10pct초과",
    "baseline_over20_cells": "기준20pct초과",
    "selected_over20_cells": "선택20pct초과",
}), 3)}

## 업종별 결과

{md_table(activity.rename(columns={
    "activity": "업종",
    "available_quarters": "사용분기수",
    "rows": "검증셀",
    "adopted_rows": "채택셀",
    "baseline_wape_pct": "기준WAPE_pct",
    "selected_wape_pct": "선택WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_cells": "기준10pct초과",
    "selected_over10_cells": "선택10pct초과",
    "baseline_over20_cells": "기준20pct초과",
    "selected_over20_cells": "선택20pct초과",
    "baseline_max_ape_pct": "기준최대오차율_pct",
    "selected_max_ape_pct": "선택최대오차율_pct",
}), 3)}

## 채택 route 요약

{md_table(route.rename(columns={
    "activity": "업종",
    "available_quarters": "사용분기수",
    "selected_route_id": "채택route",
    "selected_weight": "가중치",
    "adopted_rows": "채택셀수",
}), 3)}

## 운영시점별 권고

아래 권고는 평균 WAPE만 보지 않고, 10% 초과 셀·20% 초과 셀·최대오차율이 모두 악화되지 않는 경우만 채택으로 본다.

{md_table(policy[[
    "activity", "available_quarters", "baseline_wape_pct", "selected_wape_pct",
    "baseline_over10_cells", "selected_over10_cells",
    "baseline_over20_cells", "selected_over20_cells",
    "baseline_max_ape_pct", "selected_max_ape_pct",
    "recommended_action", "reason"
]].rename(columns={
    "activity": "업종",
    "available_quarters": "사용분기수",
    "baseline_wape_pct": "기준WAPE_pct",
    "selected_wape_pct": "선택WAPE_pct",
    "baseline_over10_cells": "기준10pct초과",
    "selected_over10_cells": "선택10pct초과",
    "baseline_over20_cells": "기준20pct초과",
    "selected_over20_cells": "선택20pct초과",
    "baseline_max_ape_pct": "기준최대오차율_pct",
    "selected_max_ape_pct": "선택최대오차율_pct",
    "recommended_action": "권고",
    "reason": "사유",
}), 3)}

## 판단

- 이 실험은 target-year actual을 route 선택에 쓰지 않았으므로 no-worse 사후선택보다 보수적이다.
- 최근 prior 악화가 있으면 미채택하는 규칙 때문에 채택셀 수가 적다. 이는 성능 과장을 막는 대신 개선폭을 제한한다.
- 결과가 기준선보다 악화되는 운영시점이나 업종은 자동 채택 대상에서 제외해야 한다.
- 따라서 `숙박 및 음식점업` Q1~Q2, 최대오차율이 악화되는 일부 `건설업` 운영시점은 평균 WAPE만 좋아도 공개 성능으로 채택하지 않는다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(operating.to_string(index=False))
    print(activity.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
