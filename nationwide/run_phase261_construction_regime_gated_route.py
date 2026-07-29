#!/usr/bin/env python3
"""Phase261: regime-gated construction multi-source rolling diagnostic.

This experiment reuses Phase244 materialized candidate detail only.  It does
not collect new raw data and does not adopt a national construction route.  The
goal is to test whether pre-declared source/regime gates can make the limited
BuildingHUB/CALS/Seoul redevelopment signals safer than the baseline in
out-of-year rolling holdout.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "processed" / "phase244_construction_multi_source_activity_route"
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase261_construction_regime_gated_route.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

DETAIL = IN / "phase244_candidate_detail.csv"

REGIME_PRIORITY = [
    "multi_source_positive",
    "seoul_redevelopment_positive",
    "buildinghub_positive",
    "cals_positive",
]

SCENARIO_ALLOWLIST = {
    "multi_source_positive": ("조합 ",),
    "seoul_redevelopment_positive": ("서울 정비사업",),
    "buildinghub_positive": ("BuildingHUB",),
    "cals_positive": ("CALS",),
}

MIN_TRAIN_ROWS = 5
MIN_TRAIN_CITIES = 3


def md_table(df: pd.DataFrame, limit: int | None = None, digits: int = 3) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if str(c).lower() in {"year", "holdout_year"}:
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else str(int(v)))
        elif pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{float(v):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def metric(df: pd.DataFrame, pred_col: str, label: str = "") -> dict[str, Any]:
    actual = pd.to_numeric(df["actual_eok"], errors="coerce")
    pred = pd.to_numeric(df[pred_col], errors="coerce")
    abs_err = (pred - actual).abs()
    ape = np.where(actual.abs().gt(0), abs_err / actual.abs() * 100, np.nan)
    large = actual.abs().ge(1000)
    denom = actual.abs().sum()
    return {
        "scenario": label,
        "rows": int(len(df)),
        "actual_sum_eok": float(actual.sum()),
        "predicted_sum_eok": float(pred.sum()),
        "abs_error_sum_eok": float(abs_err.sum()),
        "wape_pct": float(abs_err.sum() / denom * 100) if denom else np.nan,
        "over10_cells": int((ape > 10).sum()),
        "over20_cells": int((ape > 20).sum()),
        "large_actual_over10_cells": int(((ape > 10) & large).sum()),
        "max_ape_pct": float(np.nanmax(ape)) if len(ape) else np.nan,
    }


def load_detail() -> pd.DataFrame:
    d = pd.read_csv(DETAIL)
    for c in [
        "actual_eok",
        "baseline_parent_predicted_eok",
        "candidate_predicted_eok",
        "cals_amount_eok",
        "redevelopment_units",
        "buildinghub_area",
    ]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    d["year"] = pd.to_numeric(d["year"], errors="coerce").astype(int)
    d["cell_key"] = d["province_full"].astype(str) + "|" + d["city"].astype(str) + "|" + d["year"].astype(str)
    d["signal_positive_count"] = (
        d[["cals_amount_eok", "redevelopment_units", "buildinghub_area"]].gt(0).sum(axis=1)
    )
    d["multi_source_positive"] = d["signal_positive_count"].ge(2)
    d["seoul_redevelopment_positive"] = d["province_full"].eq("서울특별시") & d["redevelopment_units"].gt(0)
    d["buildinghub_positive"] = d["buildinghub_area"].gt(0)
    d["cals_positive"] = d["cals_amount_eok"].gt(0)
    return d


def baseline_frame(detail: pd.DataFrame) -> pd.DataFrame:
    base = detail[detail["scenario"].eq("baseline_parent_control")].copy()
    base["selected_scenario"] = "baseline_parent_control"
    base["selected_regime"] = "baseline"
    base["selected_predicted_eok"] = base["baseline_parent_predicted_eok"]
    base["selection_reason"] = "baseline"
    return base


def scenario_allowed(regime: str, scenario: str) -> bool:
    return any(str(scenario).startswith(prefix) for prefix in SCENARIO_ALLOWLIST[regime])


def nonworse(cand: dict[str, Any], base: dict[str, Any]) -> bool:
    return (
        cand["wape_pct"] <= base["wape_pct"]
        and cand["over10_cells"] <= base["over10_cells"]
        and cand["over20_cells"] <= base["over20_cells"]
        and cand["large_actual_over10_cells"] <= base["large_actual_over10_cells"]
        and cand["max_ape_pct"] <= base["max_ape_pct"]
    )


def train_selection(detail: pd.DataFrame, holdout_year: int) -> pd.DataFrame:
    train_years = [y for y in sorted(detail["year"].unique()) if y < holdout_year]
    rows: list[dict[str, Any]] = []
    for regime in REGIME_PRIORITY:
        train_base = detail[
            detail["scenario"].eq("baseline_parent_control")
            & detail["year"].isin(train_years)
            & detail[regime]
        ].copy()
        if train_base.empty:
            rows.append(
                {
                    "holdout_year": holdout_year,
                    "train_years": ",".join(map(str, train_years)),
                    "regime": regime,
                    "selected_scenario": "baseline_parent_control",
                    "selection_reason": "no_train_regime_cells",
                    "train_rows": 0,
                    "train_wape_pct": np.nan,
                    "baseline_train_wape_pct": np.nan,
                }
            )
            continue
        base_metric = metric(train_base, "baseline_parent_predicted_eok", "baseline_parent_control")
        train_cities = train_base[["province_full", "city"]].drop_duplicates().shape[0]
        if len(train_base) < MIN_TRAIN_ROWS or train_cities < MIN_TRAIN_CITIES:
            rows.append(
                {
                    "holdout_year": holdout_year,
                    "train_years": ",".join(map(str, train_years)),
                    "regime": regime,
                    "selected_scenario": "baseline_parent_control",
                    "selection_reason": "fallback_sparse_train_regime",
                    "train_rows": int(base_metric["rows"]),
                    "train_cities": int(train_cities),
                    "train_wape_pct": float(base_metric["wape_pct"]),
                    "baseline_train_wape_pct": float(base_metric["wape_pct"]),
                    "train_over10_cells": int(base_metric["over10_cells"]),
                    "baseline_train_over10_cells": int(base_metric["over10_cells"]),
                    "train_max_ape_pct": float(base_metric["max_ape_pct"]),
                    "baseline_train_max_ape_pct": float(base_metric["max_ape_pct"]),
                }
            )
            continue
        candidates = []
        for scenario, g in detail[detail["year"].isin(train_years) & detail[regime]].groupby("scenario"):
            if scenario == "baseline_parent_control" or not scenario_allowed(regime, scenario):
                continue
            # Require the same training cells as the regime baseline.
            if len(g) != len(train_base):
                continue
            cand_metric = metric(g, "candidate_predicted_eok", str(scenario))
            if nonworse(cand_metric, base_metric):
                candidates.append({**cand_metric, "scenario": str(scenario)})
        if candidates:
            chosen = pd.DataFrame(candidates).sort_values(["wape_pct", "over10_cells", "max_ape_pct"]).iloc[0].to_dict()
            rows.append(
                {
                    "holdout_year": holdout_year,
                    "train_years": ",".join(map(str, train_years)),
                    "regime": regime,
                    "selected_scenario": chosen["scenario"],
                    "selection_reason": "train_regime_guardrail_pass",
                    "train_rows": int(chosen["rows"]),
                    "train_cities": int(train_cities),
                    "train_wape_pct": float(chosen["wape_pct"]),
                    "baseline_train_wape_pct": float(base_metric["wape_pct"]),
                    "train_over10_cells": int(chosen["over10_cells"]),
                    "baseline_train_over10_cells": int(base_metric["over10_cells"]),
                    "train_max_ape_pct": float(chosen["max_ape_pct"]),
                    "baseline_train_max_ape_pct": float(base_metric["max_ape_pct"]),
                }
            )
        else:
            rows.append(
                {
                    "holdout_year": holdout_year,
                    "train_years": ",".join(map(str, train_years)),
                    "regime": regime,
                    "selected_scenario": "baseline_parent_control",
                    "selection_reason": "fallback_no_regime_safe_candidate",
                    "train_rows": int(base_metric["rows"]),
                    "train_cities": int(train_cities),
                    "train_wape_pct": float(base_metric["wape_pct"]),
                    "baseline_train_wape_pct": float(base_metric["wape_pct"]),
                    "train_over10_cells": int(base_metric["over10_cells"]),
                    "baseline_train_over10_cells": int(base_metric["over10_cells"]),
                    "train_max_ape_pct": float(base_metric["max_ape_pct"]),
                    "baseline_train_max_ape_pct": float(base_metric["max_ape_pct"]),
                }
            )
    return pd.DataFrame(rows)


def apply_policy(detail: pd.DataFrame, selections: pd.DataFrame) -> pd.DataFrame:
    base = baseline_frame(detail)
    parts = []
    for year, g in base.groupby("year"):
        if int(year) == 2021:
            x = g.copy()
            x["selection_reason"] = "warmup_baseline"
            parts.append(x)
            continue
        year_sel = selections[selections["holdout_year"].eq(int(year))].copy()
        x = g.copy()
        for idx, row in x.iterrows():
            applied = False
            for regime in REGIME_PRIORITY:
                if not bool(row[regime]):
                    continue
                sel = year_sel[year_sel["regime"].eq(regime)]
                if sel.empty:
                    continue
                scenario = str(sel.iloc[0]["selected_scenario"])
                if scenario == "baseline_parent_control":
                    continue
                cand = detail[
                    detail["scenario"].eq(scenario)
                    & detail["province_full"].eq(row["province_full"])
                    & detail["city"].eq(row["city"])
                    & detail["year"].eq(int(year))
                ]
                if cand.empty:
                    continue
                x.loc[idx, "selected_scenario"] = scenario
                x.loc[idx, "selected_regime"] = regime
                x.loc[idx, "selected_predicted_eok"] = float(cand.iloc[0]["candidate_predicted_eok"])
                x.loc[idx, "selection_reason"] = str(sel.iloc[0]["selection_reason"])
                applied = True
                break
            if not applied:
                x.loc[idx, "selection_reason"] = "no_applicable_safe_regime"
        parts.append(x)
    selected = pd.concat(parts, ignore_index=True)
    selected["selected_abs_error_eok"] = (selected["selected_predicted_eok"] - selected["actual_eok"]).abs()
    selected["selected_ape_pct"] = np.where(
        selected["actual_eok"].abs().gt(0),
        selected["selected_abs_error_eok"] / selected["actual_eok"].abs() * 100,
        np.nan,
    )
    return selected


def holdout_summary(selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, g in selected.groupby("year"):
        base = metric(g, "baseline_parent_predicted_eok", "baseline")
        sel = metric(g, "selected_predicted_eok", "regime_gated")
        rows.append(
            {
                "year": int(year),
                "rows": int(len(g)),
                "active_cells": int(g["selected_scenario"].ne("baseline_parent_control").sum()),
                "baseline_wape_pct": base["wape_pct"],
                "selected_wape_pct": sel["wape_pct"],
                "wape_delta_pp": sel["wape_pct"] - base["wape_pct"],
                "baseline_over10_cells": base["over10_cells"],
                "selected_over10_cells": sel["over10_cells"],
                "baseline_over20_cells": base["over20_cells"],
                "selected_over20_cells": sel["over20_cells"],
                "baseline_large_actual_over10_cells": base["large_actual_over10_cells"],
                "selected_large_actual_over10_cells": sel["large_actual_over10_cells"],
                "baseline_max_ape_pct": base["max_ape_pct"],
                "selected_max_ape_pct": sel["max_ape_pct"],
            }
        )
    return pd.DataFrame(rows)


def overall_summary(selected: pd.DataFrame) -> pd.DataFrame:
    base = metric(selected, "baseline_parent_predicted_eok", "baseline_parent_control")
    sel = metric(selected, "selected_predicted_eok", "regime_gated")
    out = pd.DataFrame([base, sel])
    out["active_cells"] = [0, int(selected["selected_scenario"].ne("baseline_parent_control").sum())]
    return out


def regime_coverage(base: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for regime in REGIME_PRIORITY:
        x = base[base[regime]].copy()
        rows.append(
            {
                "regime": regime,
                "rows": len(x),
                "cities": x[["province_full", "city"]].drop_duplicates().shape[0],
                "years": x["year"].nunique(),
                "actual_sum_eok": x["actual_eok"].sum(),
                "baseline_wape_pct": metric(x, "baseline_parent_predicted_eok", "baseline")["wape_pct"] if not x.empty else np.nan,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    detail = load_detail()
    base = baseline_frame(detail)
    selections = pd.concat([train_selection(detail, y) for y in [2022, 2023]], ignore_index=True)
    selected = apply_policy(detail, selections)
    overall = overall_summary(selected)
    by_year = holdout_summary(selected)
    coverage = regime_coverage(base)
    active = selected[selected["selected_scenario"].ne("baseline_parent_control")].copy()

    selections.to_csv(OUT / "phase261_construction_regime_gate_selection.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase261_construction_regime_gate_selected_detail.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT / "phase261_construction_regime_gate_overall_summary.csv", index=False, encoding="utf-8-sig")
    by_year.to_csv(OUT / "phase261_construction_regime_gate_holdout_summary.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(OUT / "phase261_construction_regime_gate_coverage.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase261 건설업 지역유형 gate 다중자료 rolling 진단

생성시각: {CREATED_AT}

## 1. 목적

PPS 공사계약·공사공고 전량 수집이 `HTTP 429`로 막힌 상태에서, 이미 로컬에 수집된 CALS·서울 정비사업·BuildingHUB 신호만으로 건설업 시군구 배분을 안정적으로 개선할 수 있는지 점검한다. 이 실험은 route 채택이 아니라 retrospective rolling diagnostic이다.

## 2. 누수방지 설계

| 항목 | 설정 |
| --- | --- |
| 입력 | Phase244 candidate detail 재사용. 새 raw 수집 없음 |
| 검증 범위 | 2021~2023 건설업 시군구×연간 GVA actual 공표 셀 |
| parent total | Phase244의 시도 건설업 actual 총량 control 유지. strict nowcast 성능 아님 |
| 선택 규칙 | 2022는 2021 성과만, 2023은 2021~2022 성과만으로 지역유형×후보 선택 |
| 지역유형 | 다중신호, 서울 정비사업 양수, BuildingHUB 양수, CALS 양수 |
| guardrail | 훈련연도 WAPE·10%·20%·대형 actual 10%·max APE 모두 baseline 비악화 |
| 최소 표본 | 지역유형별 훈련 5셀 이상, 3개 시군구 이상 |
| fallback | 지역유형 gate 미통과 또는 신호 미적용 셀은 baseline 유지 |

## 3. 지역유형 coverage

{md_table(coverage, digits=3)}

## 4. 지역유형별 rolling 선택

{md_table(selections, digits=3)}

## 5. 연도별 holdout 결과

{md_table(by_year, digits=3)}

## 6. 전체 성능

{md_table(overall, digits=3)}

## 7. 적용 셀 예시

{md_table(active[["province_full", "city", "year", "selected_regime", "selected_scenario", "actual_eok", "baseline_parent_predicted_eok", "selected_predicted_eok", "selected_ape_pct"]], limit=20, digits=3)}

## 8. 판정

1. PPS 없이 사용 가능한 대체자료 신호는 coverage가 좁다. CALS 양수는 31개 도시, 서울 정비사업은 9개 구, BuildingHUB는 5개 도시 수준이다.
2. 지역유형 gate는 같은 목표연도 actual을 보고 후보를 고르지 않지만, 입력 parent total이 사후 시도 actual control이므로 strict 속보 route가 아니다.
3. rolling 결과가 baseline guardrail을 통과하지 못하거나 적용 셀이 매우 제한적이면 건설업 전국 route로 채택하지 않는다.
4. 건설업 10% 목표 달성에는 PPS 계약/공고 완전월·민간건축 장기 금액형 자료·전국 정비사업 이력이 계속 필요하다.

## 9. 산출물

- `nationwide/outputs/phase261_construction_regime_gate_selection.csv`
- `nationwide/outputs/phase261_construction_regime_gate_selected_detail.csv`
- `nationwide/outputs/phase261_construction_regime_gate_overall_summary.csv`
- `nationwide/outputs/phase261_construction_regime_gate_holdout_summary.csv`
- `nationwide/outputs/phase261_construction_regime_gate_coverage.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(overall.to_string(index=False))
    print(by_year.to_string(index=False))


if __name__ == "__main__":
    main()
