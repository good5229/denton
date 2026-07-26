#!/usr/bin/env python3
"""Phase145: operational route decision registry.

After Phase143/144 temporal holdout audits, same-window route improvements
should not automatically replace the baseline.  This phase materializes a
decision registry and final operating table:

* Goyang: keep Phase138 baseline for Q1~Q3; Q4 is accounting recovery.
* Pohang: keep Phase138 baseline for Q1~Q2; allow city-temporal route for Q3
  only as a limited candidate because it improves temporal holdout WAPE by
  about 0.02 percentage points; Q4 is accounting recovery.

This file separates "pretty diagnostic candidate" from "operationally selected
route" so downstream poster/report work does not accidentally promote
same-window results.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase145_operational_route_decision_registry"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase145_operational_route_decision_registry.md"

BASE_PRED = DATA / "phase131_rolling_vintage_gva_update" / "phase131_rolling_vintage_predictions.csv"
CITY_TEMP_PRED = DATA / "phase144_city_temporal_route_audit" / "phase144_city_temporal_selected_predictions.csv"
BASE_DELIVERY = DATA / "phase138_operational_delivery_tables" / "phase138_2023_operational_city_delivery.csv"
BASE_PERF = DATA / "phase138_operational_delivery_tables" / "phase138_2022_2023_operational_performance.csv"
CITY_TEMP_COMP = DATA / "phase144_city_temporal_route_audit" / "phase144_baseline_samewindow_temporal_comparison.csv"

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
    missing = [p for p in [BASE_PRED, CITY_TEMP_PRED, BASE_DELIVERY, BASE_PERF, CITY_TEMP_COMP] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required phase output(s): " + ", ".join(str(p) for p in missing))


def amount_bucket(v: pd.Series) -> pd.Series:
    return np.select(
        [v.ge(5000.0), v.ge(1000.0)],
        ["very_large_5000eok_plus", "large_1000_5000eok"],
        default="small_under_1000eok",
    )


def decision_registry() -> pd.DataFrame:
    comp = pd.read_csv(CITY_TEMP_COMP)
    rows: list[dict[str, object]] = []
    for _, r in comp.iterrows():
        k = int(r["available_quarters"])
        city = r["city"]
        label = r["vintage_label"]
        if k == 4:
            selected = "accounting_full_year_recovery"
            status = "회계 회수"
            reason = "1~4분기 합계가 연간 최종값을 회수하므로 예측성능으로 해석하지 않음"
        elif city == "포항시" and k == 3 and float(r["city_temporal_vs_baseline_delta_pct_point"]) < -1e-9:
            selected = "city_temporal_limited_candidate"
            status = "제한 후보 채택"
            reason = "시간분리 검증에서 baseline보다 WAPE가 낮지만 개선폭이 작아 제한 후보로 표기"
        else:
            selected = "phase138_baseline"
            status = "baseline 유지"
            reason = "시간분리 검증에서 candidate가 baseline보다 같거나 악화"
        rows.append({
            "city": city,
            "available_quarters": k,
            "vintage_label": label,
            "selected_operational_route": selected,
            "decision_status": status,
            "baseline_wape_pct": r["baseline_wape_pct"],
            "city_temporal_wape_pct": r["city_temporal_wape_pct"],
            "temporal_delta_pct_point": r["city_temporal_vs_baseline_delta_pct_point"],
            "baseline_high_value_wape_pct": r["baseline_high_value_wape_pct"],
            "city_temporal_high_value_wape_pct": r["city_temporal_high_value_wape_pct"],
            "reason": reason,
        })
    return pd.DataFrame(rows).sort_values(["city", "available_quarters"])


def load_selected_predictions(registry: pd.DataFrame) -> pd.DataFrame:
    base = pd.read_csv(BASE_PRED, dtype={"middle_code": str})
    city_temp = pd.read_csv(CITY_TEMP_PRED, dtype={"middle_code": str})
    for df in [base, city_temp]:
        df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    base["source_ytd_eok"] = base["ytd_estimate_eok"]
    city_temp["source_ytd_eok"] = city_temp["ytd_eok"]
    city_temp = city_temp.rename(columns={
        "city_temporal_selected_candidate": "route_candidate",
    })
    base["route_candidate"] = "cell_prior_mean"

    frames: list[pd.DataFrame] = []
    for _, r in registry.iterrows():
        city = r["city"]
        k = int(r["available_quarters"])
        route = r["selected_operational_route"]
        source = city_temp if route == "city_temporal_limited_candidate" else base
        part = source[source["city"].eq(city) & source["available_quarters"].eq(k)].copy()
        if route == "accounting_full_year_recovery":
            part["route_candidate"] = "observed_full_year_sum"
        part["selected_operational_route"] = route
        part["decision_status"] = r["decision_status"]
        frames.append(part)
    selected = pd.concat(frames, ignore_index=True)
    selected = selected.sort_values(["city", "year", "parent_code", "middle_code", "available_quarters"])
    selected["amount_bucket"] = amount_bucket(selected["actual_annual_gva_eok"])
    selected["current_quarter_estimate_eok"] = selected.groupby(
        ["city", "year", "parent_code", "middle_code"]
    )["source_ytd_eok"].diff().fillna(selected["source_ytd_eok"])
    selected["previous_period_recheck_eok"] = np.where(
        selected["available_quarters"].gt(1),
        selected["source_ytd_eok"] - selected["current_quarter_estimate_eok"],
        np.nan,
    )
    selected["ytd_estimate_eok"] = selected["source_ytd_eok"]
    selected["annual_error_eok"] = (selected["annual_prediction_eok"] - selected["actual_annual_gva_eok"]).abs()
    selected["annual_error_rate_pct"] = np.where(
        selected["actual_annual_gva_eok"].gt(0),
        selected["annual_error_eok"] / selected["actual_annual_gva_eok"] * 100,
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
        route = ", ".join(sorted(set(g["selected_operational_route"].astype(str))))
        rows.append({
            "city": keys[0],
            "available_quarters": int(keys[1]),
            "vintage_label": keys[2],
            "selected_operational_route": route,
            "evaluated_years": "2022-2023",
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "overall_wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_error_sum_eok": high_err,
            "high_value_wape_pct": high_err / high_actual * 100 if high_actual > 0 else np.nan,
            "gt10_cells": int((g["annual_error_rate_pct"] > 10).sum()),
            "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
            "operation_note": "회계적 연간 회수: 예측력으로 해석 금지" if int(keys[1]) == 4 else "시간분리 감사 후 운영 선택 성능",
        })
    return pd.DataFrame(rows).sort_values(["city", "available_quarters"])


def delivery_2023(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for keys, g in selected[selected["year"].eq(2023)].groupby(["city", "available_quarters", "vintage_label"], sort=False):
        city, k, label = keys
        op = VINTAGE_OPERATION[int(k)]
        high = g[g["actual_annual_gva_eok"].ge(1000.0)]
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        rows.append({
            "city": city,
            "target_year": 2023,
            "vintage_label": label,
            "available_input": op["available_input"],
            "current_output": op["current_output"],
            "current_quarter_estimate_eok": float(g["current_quarter_estimate_eok"].sum()),
            "recheck_output": op["recheck_output"],
            "previous_period_recheck_eok": float(g["previous_period_recheck_eok"].fillna(0.0).sum()) if int(k) > 1 else np.nan,
            "ytd_estimate_eok": float(g["ytd_estimate_eok"].sum()),
            "annual_output": op["annual_output"],
            "annual_prediction_eok": float(g["annual_prediction_eok"].sum()),
            "annual_actual_eok": actual,
            "annual_cell_abs_error_sum_eok": err,
            "annual_wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_wape_pct": (
                float(high["annual_error_eok"].sum()) / float(high["actual_annual_gva_eok"].sum()) * 100
                if len(high) and float(high["actual_annual_gva_eok"].sum()) > 0 else np.nan
            ),
            "selected_operational_route": ", ".join(sorted(set(g["selected_operational_route"].astype(str)))),
            "decision_status": ", ".join(sorted(set(g["decision_status"].astype(str)))),
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
        - tmp["ytd_estimate_eok"]
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
    registry: pd.DataFrame,
    perf: pd.DataFrame,
    delivery: pd.DataFrame,
    top: pd.DataFrame,
    checks: pd.DataFrame,
) -> None:
    REPORT.write_text("\n".join([
        "# Phase145 시간분리 감사 후 운영 경로 결정 레지스트리",
        "",
        "## 목적",
        "",
        "Phase140/142의 same-window 개선 후보가 시간분리 검증에서 대부분 탈락했으므로, 실제 운영에 어떤 경로를 써야 하는지 명시한 결정 레지스트리를 만들었다. 이 표는 후보 성능표가 아니라 downstream 보고서·포스터가 따라야 할 운영 선택표다.",
        "",
        "## 운영 경로 결정",
        "",
        md_table(registry, [
            "city", "vintage_label", "selected_operational_route", "decision_status",
            "baseline_wape_pct", "city_temporal_wape_pct", "temporal_delta_pct_point",
            "baseline_high_value_wape_pct", "city_temporal_high_value_wape_pct", "reason",
        ]),
        "",
        "## 2022~2023 운영 선택 성능",
        "",
        md_table(perf, [
            "city", "vintage_label", "selected_operational_route", "evaluated_years",
            "overall_wape_pct", "high_value_wape_pct", "gt20_cells", "operation_note",
        ]),
        "",
        "## 2023 운영 산출 예시",
        "",
        md_table(delivery, [
            "city", "vintage_label", "available_input", "current_output", "current_quarter_estimate_eok",
            "recheck_output", "previous_period_recheck_eok", "ytd_estimate_eok", "annual_output",
            "annual_prediction_eok", "annual_actual_eok", "annual_cell_abs_error_sum_eok",
            "annual_wape_pct", "high_value_wape_pct", "selected_operational_route", "decision_status",
        ]),
        "",
        "## 2023 오차기여 상위 중분류",
        "",
        md_table(top, [
            "city", "vintage_label", "parent_code", "middle_code", "middle_label",
            "actual_annual_gva_eok", "annual_prediction_eok", "annual_error_eok",
            "annual_error_rate_pct", "error_contribution_pct", "selected_operational_route",
        ], n=48),
        "",
        "## 회계 검증",
        "",
        md_table(checks, checks.columns.tolist()),
        "",
        "## 판정",
        "",
        "1. 고양시는 Q1/Q2/Q3 모두 Phase138 baseline을 운영 기준으로 유지한다. Phase140/142 후보는 시간분리에서 악화되어 최종안으로 승격하지 않는다.",
        "2. 포항시는 Q1/Q2는 baseline, Q3만 도시 시간분리 제한 후보를 허용한다. 다만 개선폭이 약 0.02%p라 강한 성능개선으로 주장하지 않는다.",
        "3. Q4+1개월은 모든 도시에서 연간 합계 회계 회수이며 예측성능으로 해석하지 않는다.",
        "4. 다음 개선은 라우팅 자유도 확대가 아니라 독립 추가연도·타 시군구 확장검증 또는 업종별 직접 활동자료 확보가 필요하다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    ensure_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    registry = decision_registry()
    selected = load_selected_predictions(registry)
    perf = performance(selected)
    delivery = delivery_2023(selected)
    top = top_2023(selected)
    checks = accounting_checks(selected)

    registry.to_csv(OUT / "phase145_operational_route_decision_registry.csv", index=False)
    selected.to_csv(OUT / "phase145_selected_operational_predictions.csv", index=False)
    perf.to_csv(OUT / "phase145_selected_operational_performance.csv", index=False)
    delivery.to_csv(OUT / "phase145_2023_selected_operational_delivery.csv", index=False)
    top.to_csv(OUT / "phase145_2023_top_middle_contributors.csv", index=False)
    checks.to_csv(OUT / "phase145_accounting_checks.csv", index=False)
    write_report(registry, perf, delivery, top, checks)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
