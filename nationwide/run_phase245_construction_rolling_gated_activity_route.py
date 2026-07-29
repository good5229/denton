#!/usr/bin/env python3
"""Phase245 rolling-gated construction activity route.

Builds on Phase244 signals but does not apply a signal everywhere.  For each
city and target year, a candidate can be used only when it improved every prior
year available for the same city without increasing APE.  This mirrors the
guarded adoption logic used in earlier local experiments.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "processed" / "phase244_construction_multi_source_activity_route"
OUT = ROOT / "data" / "processed" / "phase245_construction_rolling_gated_activity_route"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase245_construction_rolling_gated_activity_route.md"


def md_table(df: pd.DataFrame, max_rows: int | None = None, digits: int = 3) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{v:,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def metric(df: pd.DataFrame, pred_col: str) -> dict[str, float | int]:
    actual = df["actual_eok"].astype(float)
    pred = df[pred_col].astype(float)
    abs_err = (pred - actual).abs()
    ape = np.where(actual.gt(0), abs_err / actual * 100, np.nan)
    return {
        "rows": int(len(df)),
        "actual_sum_eok": float(actual.sum()),
        "abs_error_sum_eok": float(abs_err.sum()),
        "wape_pct": float(abs_err.sum() / actual.sum() * 100),
        "over10_cells": int((ape > 10).sum()),
        "over20_cells": int((ape > 20).sum()),
        "max_ape_pct": float(np.nanmax(ape)),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    detail = pd.read_csv(IN / "phase244_candidate_detail.csv")
    baseline = detail[detail["scenario"].eq("baseline_parent_control")].copy()
    baseline["baseline_abs"] = (baseline["baseline_parent_predicted_eok"] - baseline["actual_eok"]).abs()
    baseline["baseline_ape"] = np.where(baseline["actual_eok"].gt(0), baseline["baseline_abs"] / baseline["actual_eok"] * 100, np.nan)

    # Candidate pool: only conservative candidates from Phase244 safe list and
    # low-weight one-signal routes.  Avoid data-mining across all combinations.
    safe = pd.read_csv(IN / "phase244_guardrail_safe_candidates.csv")
    candidate_names = set(safe["scenario"].head(10).tolist())
    candidate_names.update(
        x
        for x in detail["scenario"].unique()
        if any(token in str(x) for token in ["서울 정비사업 착공세대 0.01", "서울 정비사업 착공세대 0.02", "서울 정비사업 착공세대 0.03", "BuildingHUB 건축면적 0.01"])
    )
    pool = detail[detail["scenario"].isin(candidate_names)].copy()
    pool = pool.merge(
        baseline[["province_full", "city", "year", "baseline_parent_predicted_eok", "baseline_abs", "baseline_ape"]],
        on=["province_full", "city", "year"],
        how="left",
        suffixes=("", "_base"),
    )
    pool["candidate_abs"] = (pool["candidate_predicted_eok"] - pool["actual_eok"]).abs()
    pool["candidate_ape"] = np.where(pool["actual_eok"].gt(0), pool["candidate_abs"] / pool["actual_eok"] * 100, np.nan)
    pool["improved"] = (pool["candidate_abs"] < pool["baseline_abs"]) & (pool["candidate_ape"] <= pool["baseline_ape"])

    selected_rows = []
    choices = []
    key_cols = ["province_full", "city"]
    for _, b in baseline.sort_values(key_cols + ["year"]).iterrows():
        y = int(b["year"])
        city_mask = (pool["province_full"].eq(b["province_full"])) & (pool["city"].eq(b["city"]))
        if y <= 2021:
            selected = b.copy()
            selected["selected_scenario"] = "baseline_parent_control"
            selected["selected_predicted_eok"] = b["baseline_parent_predicted_eok"]
            reason = "first_year_baseline"
        else:
            prior_years = list(range(2021, y))
            candidates = []
            for scen, g in pool[city_mask & pool["year"].isin(prior_years)].groupby("scenario"):
                if len(g) < len(prior_years):
                    continue
                if not bool(g["improved"].all()):
                    continue
                target = pool[city_mask & pool["year"].eq(y) & pool["scenario"].eq(scen)]
                if target.empty:
                    continue
                # Choose the candidate with smallest prior absolute error,
                # but keep it conservative by requiring all prior years pass.
                candidates.append((float(g["candidate_abs"].sum()), scen, target.iloc[0]))
            if candidates:
                candidates.sort(key=lambda z: (z[0], z[1]))
                target = candidates[0][2]
                selected = b.copy()
                selected["selected_scenario"] = candidates[0][1]
                selected["selected_predicted_eok"] = target["candidate_predicted_eok"]
                reason = "prior_year_city_pass"
            else:
                selected = b.copy()
                selected["selected_scenario"] = "baseline_parent_control"
                selected["selected_predicted_eok"] = b["baseline_parent_predicted_eok"]
                reason = "no_prior_pass"
        selected["reason"] = reason
        selected_rows.append(selected)
        choices.append(
            {
                "province_full": b["province_full"],
                "city": b["city"],
                "year": y,
                "selected_scenario": selected["selected_scenario"],
                "reason": reason,
                "actual_eok": b["actual_eok"],
                "baseline_predicted_eok": b["baseline_parent_predicted_eok"],
                "selected_predicted_eok": selected["selected_predicted_eok"],
            }
        )

    selected = pd.DataFrame(selected_rows)
    selected["selected_abs_error_eok"] = (selected["selected_predicted_eok"] - selected["actual_eok"]).abs()
    selected["selected_ape_pct"] = np.where(selected["actual_eok"].gt(0), selected["selected_abs_error_eok"] / selected["actual_eok"] * 100, np.nan)

    base_metrics = metric(baseline, "baseline_parent_predicted_eok")
    selected_metrics = metric(selected, "selected_predicted_eok")
    summary = pd.DataFrame([{**base_metrics, "policy": "baseline_parent_control"}, {**selected_metrics, "policy": "rolling_city_gated"}])

    city_base = baseline.assign(abs_err=baseline["baseline_abs"]).groupby(["province_full", "city"], as_index=False).agg(actual=("actual_eok", "sum"), abs_err=("abs_err", "sum"))
    city_sel = selected.groupby(["province_full", "city"], as_index=False).agg(actual=("actual_eok", "sum"), abs_err=("selected_abs_error_eok", "sum"))
    city = city_base.merge(city_sel, on=["province_full", "city"], suffixes=("_base", "_selected"))
    city["base_wape"] = city["abs_err_base"] / city["actual_base"] * 100
    city["selected_wape"] = city["abs_err_selected"] / city["actual_selected"] * 100
    city["wape_change"] = city["selected_wape"] - city["base_wape"]
    city["worsened"] = city["wape_change"] > 1e-9

    choices_df = pd.DataFrame(choices)
    choices_df.to_csv(OUT / "phase245_selected_choices.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase245_selected_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase245_policy_summary.csv", index=False, encoding="utf-8-sig")
    city.to_csv(OUT / "phase245_city_guardrail.csv", index=False, encoding="utf-8-sig")

    active = choices_df[choices_df["selected_scenario"].ne("baseline_parent_control")]
    report = f"""# Phase245 건설업 rolling city-gated 활동자료 route

생성시각: {datetime.now().astimezone().isoformat(timespec='seconds')}

## 결론

Phase244에서 전체 WAPE를 낮추는 후보는 있었지만 일부 시군구 WAPE가 악화됐다. Phase245는 이를 막기 위해 도시별 과거연도 gate를 적용했다.

- 2021년: warm-up으로 기준선 유지
- 2022년: 2021년에 같은 도시에서 개선된 후보만 적용
- 2023년: 2021~2022년 모두 같은 도시에서 개선된 후보만 적용
- 후보가 없으면 기준선 유지

## 1. 정책 성능

{md_table(summary, digits=3)}

## 2. 적용된 후보 수

| 항목 | 값 |
| --- | ---: |
| 전체 셀 | {len(choices_df):,} |
| 활동자료 적용 셀 | {len(active):,} |
| 기준선 유지 셀 | {len(choices_df) - len(active):,} |
| WAPE 악화 도시 수 | {int(city['worsened'].sum()):,} |
| 최대 도시 WAPE 변화 | {float(city['wape_change'].max()):.3f}%p |

## 3. 적용 후보 예시

{md_table(active[["province_full", "city", "year", "selected_scenario", "reason", "actual_eok", "baseline_predicted_eok", "selected_predicted_eok"]], max_rows=20, digits=3)}

## 4. 도시별 변화 상위

{md_table(city.sort_values("wape_change").head(15)[["province_full", "city", "base_wape", "selected_wape", "wape_change"]], digits=3)}

## 5. 판정

rolling gate를 걸면 일부 셀에는 안전하게 활동자료를 붙일 수 있지만, 적용 범위가 매우 작아 전체 WAPE 개선폭은 제한적이다. 건설업 시군구 WAPE 10% 목표에는 여전히 조달청 계약정보 전량, LH 공고, 지역별 민간 대형개발/정비사업 자료의 추가 수집이 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(summary.to_string(index=False))
    print("active_cells", len(active), "worsened_cities", int(city["worsened"].sum()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
