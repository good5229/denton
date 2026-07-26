#!/usr/bin/env python3
"""Phase140: operational delivery tables with guarded seasonal routing.

Phase138 is the baseline operational table.  Phase139 found two conservative
seasonal-share route changes that improve 2022~2023 amount-weighted WAPE
without worsening either evaluated year.  This phase materializes those
selected predictions in the same delivery-table language used for operations.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase140_guarded_operational_delivery"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase140_guarded_operational_delivery.md"

SELECTED = DATA / "phase139_guarded_seasonal_share_routing" / "phase139_selected_predictions.csv"
ROUTES = DATA / "phase139_guarded_seasonal_share_routing" / "phase139_guarded_routes.csv"
BASELINE = DATA / "phase138_operational_delivery_tables" / "phase138_2022_2023_operational_performance.csv"

VINTAGE_OPERATION = {
    1: {
        "available_input": "1분기 자료",
        "current_output": "1분기(1~3월) GVA 추정",
        "recheck_output": "해당 없음",
        "annual_output": "당해년도 GVA 1차 추정",
    },
    2: {
        "available_input": "1~2분기 자료",
        "current_output": "2분기(4~6월) GVA 추정",
        "recheck_output": "1분기(1~3월) GVA 재검증",
        "annual_output": "당해년도 GVA 재추정",
    },
    3: {
        "available_input": "1~3분기 자료",
        "current_output": "3분기(7~9월) GVA 추정",
        "recheck_output": "1~2분기(1~6월) GVA 재검증",
        "annual_output": "당해년도 GVA 재추정",
    },
    4: {
        "available_input": "1~4분기 자료",
        "current_output": "4분기(10~12월) GVA 추정",
        "recheck_output": "1~3분기(1~9월) GVA 재검증",
        "annual_output": "당해년도 GVA 최종 추정",
    },
}


def ensure_inputs() -> None:
    missing = [p for p in [SELECTED, ROUTES, BASELINE] if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Phase140 requires Phase138 and Phase139 generated outputs. Missing: "
            + ", ".join(str(p) for p in missing)
        )


def amount_bucket(v: pd.Series) -> pd.Series:
    return np.select(
        [v.ge(5000.0), v.ge(1000.0)],
        ["very_large_5000eok_plus", "large_1000_5000eok"],
        default="small_under_1000eok",
    )


def prepare_selected() -> pd.DataFrame:
    df = pd.read_csv(SELECTED, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["amount_bucket"] = amount_bucket(df["actual_annual_gva_eok"])
    df["current_quarter_estimate_eok"] = df.groupby(
        ["city", "year", "parent_code", "middle_code"]
    )["ytd_eok"].diff().fillna(df["ytd_eok"])
    df["previous_period_recheck_eok"] = np.where(
        df["available_quarters"].gt(1),
        df["ytd_eok"] - df["current_quarter_estimate_eok"],
        np.nan,
    )
    df["annual_error_eok"] = (df["annual_prediction_eok"] - df["actual_annual_gva_eok"]).abs()
    df["annual_error_rate_pct"] = np.where(
        df["actual_annual_gva_eok"].gt(0),
        df["annual_error_eok"] / df["actual_annual_gva_eok"] * 100,
        np.nan,
    )
    return df


def delivery_2023(pred: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for keys, g in pred[pred["year"].eq(2023)].groupby(["city", "available_quarters", "vintage_label"], sort=False):
        city, k, label = keys
        op = VINTAGE_OPERATION[int(k)]
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        high = g[g["actual_annual_gva_eok"].ge(1000.0)]
        selected_candidates = ", ".join(sorted(set(g["selected_candidate"].dropna().astype(str))))
        rows.append({
            "city": city,
            "target_year": 2023,
            "vintage_label": label,
            "available_input": op["available_input"],
            "current_output": op["current_output"],
            "current_quarter_estimate_eok": float(g["current_quarter_estimate_eok"].sum()),
            "recheck_output": op["recheck_output"],
            "previous_period_recheck_eok": float(g["previous_period_recheck_eok"].fillna(0).sum()) if int(k) > 1 else np.nan,
            "ytd_estimate_eok": float(g["ytd_eok"].sum()),
            "annual_output": op["annual_output"],
            "annual_prediction_eok": float(g["annual_prediction_eok"].sum()),
            "annual_actual_eok": actual,
            "annual_cell_abs_error_sum_eok": err,
            "annual_wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_wape_pct": (
                float(high["annual_error_eok"].sum()) / float(high["actual_annual_gva_eok"].sum()) * 100
                if len(high) and float(high["actual_annual_gva_eok"].sum()) > 0 else np.nan
            ),
            "selected_seasonal_route": selected_candidates,
        })
    return pd.DataFrame(rows).sort_values(["city", "target_year", "vintage_label"], key=lambda s: s.map({
        "1분기+1개월": 1,
        "1~2분기+1개월": 2,
        "1~3분기+1개월": 3,
        "1~4분기+1개월": 4,
    }) if s.name == "vintage_label" else s)


def performance(pred: pd.DataFrame) -> pd.DataFrame:
    d = pred[pred["year"].between(2022, 2023)].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "available_quarters", "vintage_label"], sort=False):
        city, k, label = keys
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        high = g[g["actual_annual_gva_eok"].ge(1000.0)]
        rows.append({
            "city": city,
            "vintage_label": label,
            "available_quarters": int(k),
            "evaluated_years": "2022-2023",
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "overall_wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_error_sum_eok": float(high["annual_error_eok"].sum()),
            "high_value_wape_pct": (
                float(high["annual_error_eok"].sum()) / float(high["actual_annual_gva_eok"].sum()) * 100
                if len(high) and float(high["actual_annual_gva_eok"].sum()) > 0 else np.nan
            ),
            "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
            "operation_note": "회계적 연간 회수: 예측력으로 해석 금지" if int(k) == 4 else "운영 성능 비교 대상",
        })
    return pd.DataFrame(rows).sort_values(["city", "available_quarters"])


def compare_to_baseline(perf: pd.DataFrame) -> pd.DataFrame:
    base = pd.read_csv(BASELINE)
    m = perf.merge(
        base[["city", "vintage_label", "overall_wape_pct", "high_value_wape_pct"]],
        on=["city", "vintage_label"],
        how="left",
        suffixes=("_guarded", "_baseline"),
    )
    m["overall_wape_delta_pct_point"] = m["overall_wape_pct_guarded"] - m["overall_wape_pct_baseline"]
    m["high_value_wape_delta_pct_point"] = m["high_value_wape_pct_guarded"] - m["high_value_wape_pct_baseline"]
    return m


def top_2023(pred: pd.DataFrame) -> pd.DataFrame:
    d = pred[pred["year"].eq(2023) & pred["available_quarters"].isin([1, 2, 3])].copy()
    d["error_contribution_pct"] = d.groupby(["city", "vintage_label"])["annual_error_eok"].transform(
        lambda s: s / s.sum() * 100 if float(s.sum()) > 0 else 0
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


def write_report(
    delivery: pd.DataFrame,
    perf: pd.DataFrame,
    comp: pd.DataFrame,
    routes: pd.DataFrame,
    top: pd.DataFrame,
) -> None:
    REPORT.write_text("\n".join([
        "# Phase140 보수적 라우팅 반영 GVA 운영 납품표",
        "",
        "## 목적",
        "",
        "Phase139에서 통과한 보수적 계절비중 라우팅을 Phase138 운영표 형식에 반영했다. 목표는 잔차를 지우는 보정이 아니라, 예측시점 이전 자료만으로 연간 환산 계절비중을 더 안정적으로 선택하는 것이다.",
        "",
        "## 채택된 라우팅",
        "",
        md_table(routes[routes["adopt_guarded_route"]], [
            "city", "vintage_label", "selected_candidate", "baseline_wape_pct", "selected_wape_pct",
            "wape_delta_pct_point", "baseline_high_value_wape_pct", "selected_high_value_wape_pct",
            "high_value_wape_delta_pct_point", "error_delta_eok",
        ]),
        "",
        "## 2023 운영 산출 예시: 도시 총계",
        "",
        md_table(delivery, [
            "city", "vintage_label", "available_input", "current_output", "current_quarter_estimate_eok",
            "recheck_output", "previous_period_recheck_eok", "ytd_estimate_eok", "annual_output",
            "annual_prediction_eok", "annual_actual_eok", "annual_cell_abs_error_sum_eok",
            "annual_wape_pct", "high_value_wape_pct", "selected_seasonal_route",
        ]),
        "",
        "## 2022~2023 평균 운영 성능: Phase138 대비",
        "",
        md_table(comp, [
            "city", "vintage_label", "evaluated_years", "overall_wape_pct_baseline",
            "overall_wape_pct_guarded", "overall_wape_delta_pct_point",
            "high_value_wape_pct_baseline", "high_value_wape_pct_guarded",
            "high_value_wape_delta_pct_point", "gt20_cells", "operation_note",
        ]),
        "",
        "## 2023 오차기여 상위 중분류",
        "",
        md_table(top, [
            "city", "vintage_label", "middle_code", "middle_label", "selected_candidate",
            "actual_annual_gva_eok", "annual_prediction_eok", "annual_error_eok",
            "annual_error_rate_pct", "error_contribution_pct",
        ], n=48),
        "",
        "## 판정",
        "",
        "1. 고양시 1분기+1개월 연간 nowcast는 WAPE가 5.13%에서 4.94%로 낮아지고, 1,000억원 이상 업종 WAPE도 4.92%에서 4.77%로 낮아진다.",
        "2. 포항시 1~3분기+1개월은 WAPE가 1.25%에서 1.23%로 낮아진다. 개선폭은 작지만 보수적 guardrail을 통과했다.",
        "3. 고양시 1~2분기, 1~3분기 및 포항시 1분기, 1~2분기는 후보가 일부 평균개선을 보였어도 특정 연도 악화가 있어 기존 방식을 유지한다.",
        "4. KOBIS는 사용 가능하지만 고양시 J59에는 채택되지 않았고, KOPIS는 사용할 수 없으므로 본 운영표에는 반영하지 않는다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    ensure_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    pred = prepare_selected()
    routes = pd.read_csv(ROUTES)
    delivery = delivery_2023(pred)
    perf = performance(pred)
    comp = compare_to_baseline(perf)
    top = top_2023(pred)

    delivery.to_csv(OUT / "phase140_2023_operational_city_delivery_guarded.csv", index=False)
    perf.to_csv(OUT / "phase140_2022_2023_operational_performance_guarded.csv", index=False)
    comp.to_csv(OUT / "phase140_phase138_comparison.csv", index=False)
    top.to_csv(OUT / "phase140_2023_top_middle_contributors_guarded.csv", index=False)
    write_report(delivery, perf, comp, routes, top)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
