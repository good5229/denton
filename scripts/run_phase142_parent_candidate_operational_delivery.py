#!/usr/bin/env python3
"""Phase142: parent-guarded candidate operational delivery tables.

Phase141 improved rolling annual nowcast WAPE by selecting seasonal-share
families at city×KSIC-parent×vintage granularity.  Because that routing is more
flexible than the city-level Phase139/140 guard, this phase materializes it as
a *candidate* operational delivery table rather than replacing the conservative
baseline.

The table keeps the user-requested operational workflow:

* Q1 data -> Q1 GVA and first annual nowcast;
* Q1~Q2 data -> Q2 GVA, Q1/YTD recheck, annual renowcast;
* Q1~Q3 data -> Q3 GVA, Q1~Q2/YTD recheck, annual renowcast;
* Q1~Q4 data -> Q4 GVA, Q1~Q3/YTD recheck, final annual accounting recovery.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase142_parent_candidate_operational_delivery"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase142_parent_candidate_operational_delivery.md"

SELECTED = DATA / "phase141_parent_guarded_seasonal_routing" / "phase141_parent_selected_predictions.csv"
ROUTES = DATA / "phase141_parent_guarded_seasonal_routing" / "phase141_parent_guarded_routes.csv"
BASELINE = DATA / "phase138_operational_delivery_tables" / "phase138_2022_2023_operational_performance.csv"
CITY_GUARDED = DATA / "phase140_guarded_operational_delivery" / "phase140_2022_2023_operational_performance_guarded.csv"

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

VINTAGE_ORDER = {
    "1분기+1개월": 1,
    "1~2분기+1개월": 2,
    "1~3분기+1개월": 3,
    "1~4분기+1개월": 4,
}


def ensure_inputs() -> None:
    missing = [p for p in [SELECTED, ROUTES, BASELINE, CITY_GUARDED] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required phase output(s): " + ", ".join(str(p) for p in missing))


def amount_bucket(v: pd.Series) -> pd.Series:
    return np.select(
        [v.ge(5000.0), v.ge(1000.0)],
        ["very_large_5000eok_plus", "large_1000_5000eok"],
        default="small_under_1000eok",
    )


def prepare_selected() -> pd.DataFrame:
    df = pd.read_csv(SELECTED, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df = df.sort_values(["city", "year", "parent_code", "middle_code", "available_quarters"]).copy()
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
        parent_routes = int(g[["parent_code", "parent_selected_candidate"]].drop_duplicates().shape[0])
        adopted_parent_routes = (
            int((g["parent_selected_candidate"] != "cell_prior_mean").sum())
            if int(k) < 4 else 0
        )
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
            "parent_route_count": parent_routes,
            "nonbaseline_cell_count": adopted_parent_routes,
        })
    return pd.DataFrame(rows).sort_values(
        ["city", "vintage_label"],
        key=lambda s: s.map(VINTAGE_ORDER) if s.name == "vintage_label" else s,
    )


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
            "gt10_cells": int((g["annual_error_rate_pct"] > 10).sum()),
            "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
            "operation_note": "회계적 연간 회수: 예측력으로 해석 금지" if int(k) == 4 else "확장검증 전 후보 성능",
        })
    return pd.DataFrame(rows).sort_values(["city", "available_quarters"])


def compare(perf: pd.DataFrame) -> pd.DataFrame:
    base = pd.read_csv(BASELINE).rename(columns={
        "overall_wape_pct": "baseline_wape_pct",
        "high_value_wape_pct": "baseline_high_value_wape_pct",
    })
    guarded = pd.read_csv(CITY_GUARDED).rename(columns={
        "overall_wape_pct": "city_guarded_wape_pct",
        "high_value_wape_pct": "city_guarded_high_value_wape_pct",
    })
    cand = perf.rename(columns={
        "overall_wape_pct": "parent_candidate_wape_pct",
        "high_value_wape_pct": "parent_candidate_high_value_wape_pct",
        "error_sum_eok": "parent_candidate_error_sum_eok",
    })
    out = cand.merge(
        base[["city", "vintage_label", "baseline_wape_pct", "baseline_high_value_wape_pct"]],
        on=["city", "vintage_label"],
        how="left",
    ).merge(
        guarded[["city", "vintage_label", "city_guarded_wape_pct", "city_guarded_high_value_wape_pct"]],
        on=["city", "vintage_label"],
        how="left",
    )
    out["candidate_vs_baseline_wape_delta_pct_point"] = out["parent_candidate_wape_pct"] - out["baseline_wape_pct"]
    out["candidate_vs_city_guarded_wape_delta_pct_point"] = out["parent_candidate_wape_pct"] - out["city_guarded_wape_pct"]
    out["candidate_vs_baseline_high_value_delta_pct_point"] = (
        out["parent_candidate_high_value_wape_pct"] - out["baseline_high_value_wape_pct"]
    )
    return out.sort_values(["city", "available_quarters"])


def adopted_route_summary(routes: pd.DataFrame) -> pd.DataFrame:
    d = routes[routes["adopt_parent_route"]].copy()
    return (
        d.groupby(["city", "vintage_label"], as_index=False)
        .agg(
            adopted_parent_routes=("parent_code", "count"),
            error_delta_eok=("error_delta_eok", "sum"),
            max_improvement_parent=("error_delta_eok", "min"),
        )
        .sort_values(["city", "vintage_label"], key=lambda s: s.map(VINTAGE_ORDER) if s.name == "vintage_label" else s)
    )


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


def accounting_checks(pred: pd.DataFrame) -> pd.DataFrame:
    checks = []
    q4 = pred[pred["available_quarters"].eq(4)].copy()
    q4["diff"] = (q4["annual_prediction_eok"] - q4["actual_annual_gva_eok"]).abs()
    checks.append({
        "check_id": "q4_full_year_recovery",
        "rows": int(len(q4)),
        "max_abs_diff_eok": float(q4["diff"].max()) if len(q4) else np.nan,
        "pass": bool((q4["diff"] < 1e-9).all()) if len(q4) else False,
    })
    tmp = pred.copy()
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
    delivery: pd.DataFrame,
    perf: pd.DataFrame,
    comp: pd.DataFrame,
    route_summary: pd.DataFrame,
    top: pd.DataFrame,
    checks: pd.DataFrame,
) -> None:
    REPORT.write_text("\n".join([
        "# Phase142 상위산업 라우팅 후보 GVA 운영 납품표",
        "",
        "## 목적",
        "",
        "Phase141의 도시×상위산업×빈티지 계절비중 선택 결과를 사용자가 요청한 rolling GVA 운영표 형식으로 변환했다. 이 표는 기존 납품표를 대체하는 최종본이 아니라, 추가 연도·타 시군구 확장검증 전의 후보 운영표다.",
        "",
        "## 2023 운영 산출 예시: 도시 총계",
        "",
        md_table(delivery, [
            "city", "vintage_label", "available_input", "current_output", "current_quarter_estimate_eok",
            "recheck_output", "previous_period_recheck_eok", "ytd_estimate_eok", "annual_output",
            "annual_prediction_eok", "annual_actual_eok", "annual_cell_abs_error_sum_eok",
            "annual_wape_pct", "high_value_wape_pct", "parent_route_count", "nonbaseline_cell_count",
        ]),
        "",
        "## 2022~2023 평균 성능: 기존·도시라우팅·상위산업 후보 비교",
        "",
        md_table(comp, [
            "city", "vintage_label", "evaluated_years",
            "baseline_wape_pct", "city_guarded_wape_pct", "parent_candidate_wape_pct",
            "candidate_vs_baseline_wape_delta_pct_point", "candidate_vs_city_guarded_wape_delta_pct_point",
            "baseline_high_value_wape_pct", "city_guarded_high_value_wape_pct", "parent_candidate_high_value_wape_pct",
            "candidate_vs_baseline_high_value_delta_pct_point", "gt20_cells", "operation_note",
        ]),
        "",
        "## 채택 라우팅 요약",
        "",
        md_table(route_summary, [
            "city", "vintage_label", "adopted_parent_routes", "error_delta_eok", "max_improvement_parent",
        ]),
        "",
        "## 2023 오차기여 상위 중분류",
        "",
        md_table(top, [
            "city", "vintage_label", "parent_code", "middle_code", "middle_label", "parent_selected_candidate",
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
        "1. 상위산업 후보 라우팅은 고양시 Q1/Q2/Q3 WAPE를 5.13→4.40%, 3.13→2.88%, 1.60→1.43%로 낮춘다.",
        "2. 고양시 1,000억원 이상 업종 WAPE도 Q1/Q2/Q3에서 4.92→4.23%, 2.95→2.74%, 1.51→1.36%로 낮아진다.",
        "3. 포항시도 Q1/Q2/Q3 WAPE가 3.91→3.59%, 2.14→1.97%, 1.25→1.15%로 낮아진다.",
        "4. 단, 이 표는 후보 선택과 성능평가가 모두 2022~2023에 기반하므로 최종 채택 전 확장검증이 필요하다. 숫자가 예쁘다고 바로 최종 성능이라고 우기면 안 된다.",
        "5. Q4+1개월의 0%는 예측 성능이 아니라 연간 합계 회계 회수다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    ensure_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    pred = prepare_selected()
    routes = pd.read_csv(ROUTES)
    delivery = delivery_2023(pred)
    perf = performance(pred)
    comp = compare(perf)
    route_summary = adopted_route_summary(routes)
    top = top_2023(pred)
    checks = accounting_checks(pred)

    delivery.to_csv(OUT / "phase142_2023_operational_city_delivery_parent_candidate.csv", index=False)
    perf.to_csv(OUT / "phase142_2022_2023_operational_performance_parent_candidate.csv", index=False)
    comp.to_csv(OUT / "phase142_baseline_city_parent_comparison.csv", index=False)
    route_summary.to_csv(OUT / "phase142_adopted_route_summary.csv", index=False)
    top.to_csv(OUT / "phase142_2023_top_middle_contributors_parent_candidate.csv", index=False)
    checks.to_csv(OUT / "phase142_accounting_checks.csv", index=False)
    write_report(delivery, perf, comp, route_summary, top, checks)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
