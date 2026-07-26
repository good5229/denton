#!/usr/bin/env python3
"""Phase138: operational delivery tables for rolling GVA estimates.

Phase131 produced the row-level rolling vintage predictions.  Phase137 added
amount-weighted evaluation.  This phase turns those outputs into user-facing
operational delivery tables matching the requested prediction workflow:

1. with Q1 data: estimate Q1 and annual GVA;
2. with Q1~Q2 data: estimate Q2, re-check Q1/YTD, re-nowcast annual GVA;
3. with Q1~Q3 data: estimate Q3, re-check Q1~Q2/YTD, re-nowcast annual GVA;
4. with Q1~Q4 data: estimate Q4, re-check Q1~Q3/YTD, final annual estimate.

The tables keep validation wording explicit: quarterly rows are internal monthly
cube aggregation checks, while annual errors are evaluated against the smallest
available annual benchmark currently materialized.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase138_operational_delivery_tables"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase138_operational_delivery_tables.md"

ROLLING = DATA / "phase131_rolling_vintage_gva_update" / "phase131_rolling_vintage_predictions.csv"
SCORE = DATA / "phase137_amount_weighted_operational_scorecard" / "phase137_rolling_total_scorecard.csv"


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


def amount_bucket(v: pd.Series) -> pd.Series:
    return np.select(
        [v.ge(5000.0), v.ge(1000.0)],
        ["very_large_5000eok_plus", "large_1000_5000eok"],
        default="small_under_1000eok",
    )


def load_predictions() -> pd.DataFrame:
    df = pd.read_csv(ROLLING, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["amount_bucket"] = amount_bucket(df["actual_annual_gva_eok"])
    df["quarter_scope"] = df["available_quarters"].map(lambda k: VINTAGE_OPERATION[int(k)]["current_output"])
    df["recheck_scope"] = df["available_quarters"].map(lambda k: VINTAGE_OPERATION[int(k)]["recheck_output"])
    df["annual_scope"] = df["available_quarters"].map(lambda k: VINTAGE_OPERATION[int(k)]["annual_output"])
    return df


def delivery_summary(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, g in pred[pred["year"].eq(2023)].groupby(["city", "available_quarters", "vintage_id", "vintage_label"], sort=False):
        op = VINTAGE_OPERATION[int(keys[1])]
        actual = float(g["actual_annual_gva_eok"].sum())
        annual_pred = float(g["annual_prediction_eok"].sum())
        annual_err = float(g["annual_error_eok"].sum())
        cur = float(g["current_quarter_estimate_eok"].sum())
        prev = float(g["previous_quarters_recheck_eok"].fillna(0).sum())
        ytd = float(g["ytd_estimate_eok"].sum())
        high = g[g["actual_annual_gva_eok"].ge(1000)]
        rows.append({
            "city": keys[0],
            "target_year": 2023,
            "vintage_label": keys[3],
            "available_input": op["available_input"],
            "current_output": op["current_output"],
            "current_quarter_estimate_eok": cur,
            "recheck_output": op["recheck_output"],
            "previous_period_recheck_eok": prev if int(keys[1]) > 1 else np.nan,
            "ytd_estimate_eok": ytd,
            "annual_output": op["annual_output"],
            "annual_prediction_eok": annual_pred,
            "annual_actual_eok": actual,
            "annual_cell_abs_error_sum_eok": annual_err,
            "annual_wape_pct": annual_err / actual * 100 if actual else np.nan,
            "high_value_wape_pct": float(high["annual_error_eok"].sum()) / float(high["actual_annual_gva_eok"].sum()) * 100 if len(high) else np.nan,
            "quarter_validation": "internal monthly cube aggregation",
            "annual_validation": "after-publication annual benchmark aggregation",
        })
    return pd.DataFrame(rows).sort_values(["city", "vintage_label"], key=lambda s: s.map({
        "1분기+1개월": 1,
        "1~2분기+1개월": 2,
        "1~3분기+1개월": 3,
        "1~4분기+1개월": 4,
    }) if s.name == "vintage_label" else s)


def performance_average() -> pd.DataFrame:
    score = pd.read_csv(SCORE)
    out = score.copy()
    out["operation_note"] = np.where(
        out["available_quarters"].eq(4),
        "회계적 연간 회수: 예측력으로 해석 금지",
        "운영 성능 비교 대상",
    )
    return out[[
        "city",
        "vintage_label",
        "evaluated_years",
        "overall_wape_pct",
        "high_value_wape_pct",
        "small_high_pct_cells",
        "all_gt20_cells",
        "operation_note",
    ]]


def top_examples(pred: pd.DataFrame) -> pd.DataFrame:
    d = pred[pred["year"].eq(2023) & pred["available_quarters"].isin([1, 2, 3])].copy()
    d["error_contribution_pct"] = d.groupby(["city", "vintage_label"])["annual_error_eok"].transform(
        lambda s: s / s.sum() * 100 if s.sum() else 0
    )
    d = d.sort_values(["city", "available_quarters", "annual_error_eok"], ascending=[True, True, False])
    return d.groupby(["city", "available_quarters"], as_index=False).head(8)[[
        "city",
        "vintage_label",
        "parent_code",
        "middle_code",
        "middle_label",
        "amount_bucket",
        "annual_prediction_eok",
        "actual_annual_gva_eok",
        "annual_error_eok",
        "annual_error_rate_pct",
        "error_contribution_pct",
        "seasonal_basis",
        "history_year_count",
    ]]


def validation_matrix(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for k, op in VINTAGE_OPERATION.items():
        sample = pred[pred["available_quarters"].eq(k)]
        rows.append({
            "available_quarters": k,
            "available_input": op["available_input"],
            "current_quarter_output": op["current_output"],
            "recheck_output": op["recheck_output"],
            "annual_output": op["annual_output"],
            "quarter_validation_level": sample["quarter_validation_status"].dropna().iloc[0] if len(sample) else "",
            "annual_validation_level": sample["annual_validation_status"].dropna().iloc[0] if len(sample) else "",
            "interpretation": "분기값은 독립 official actual 검증이 아니라 월별 큐브 집계 일관성 검증; 연간값은 공표 후 연간 벤치마크와 비교",
        })
    return pd.DataFrame(rows)


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

    body = ["| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *body])


def write_report(delivery: pd.DataFrame, perf: pd.DataFrame, examples: pd.DataFrame, validation: pd.DataFrame) -> None:
    q3_perf = perf[perf["vintage_label"].eq("1~3분기+1개월")]
    REPORT.write_text("\n".join([
        "# Phase138 고양·포항 rolling GVA 운영 납품 테이블",
        "",
        "## 목적",
        "",
        "사용자가 정의한 4개 예측 빈티지(Q1, Q1~Q2, Q1~Q3, Q1~Q4)를 그대로 운영 테이블로 정리했다. 2023년은 산출 예시로, 성능은 2022~2023 평균 WAPE로 표시한다.",
        "",
        "## 2023 운영 산출 예시: 도시 총계",
        "",
        md_table(delivery, ["city", "vintage_label", "available_input", "current_output", "current_quarter_estimate_eok", "recheck_output", "previous_period_recheck_eok", "ytd_estimate_eok", "annual_output", "annual_prediction_eok", "annual_actual_eok", "annual_cell_abs_error_sum_eok", "annual_wape_pct", "high_value_wape_pct"]),
        "",
        "## 2022~2023 평균 운영 성능",
        "",
        md_table(perf, ["city", "vintage_label", "evaluated_years", "overall_wape_pct", "high_value_wape_pct", "small_high_pct_cells", "all_gt20_cells", "operation_note"]),
        "",
        "## Q3+1개월 운영판단 핵심",
        "",
        md_table(q3_perf, ["city", "vintage_label", "overall_wape_pct", "high_value_wape_pct", "small_high_pct_cells", "all_gt20_cells"]),
        "",
        "## 2023 빈티지별 오차기여 상위 중분류 예시",
        "",
        md_table(examples, ["city", "vintage_label", "parent_code", "middle_code", "middle_label", "amount_bucket", "annual_prediction_eok", "actual_annual_gva_eok", "annual_error_eok", "annual_error_rate_pct", "error_contribution_pct"], n=48),
        "",
        "## 검증 레벨 매트릭스",
        "",
        md_table(validation, validation.columns.tolist()),
        "",
        "## 판정",
        "",
        "1. 요청한 네 가지 예측 흐름은 모두 테이블화됐다: 현재 분기 추정, 이전 분기/YTD 재검증, 당해년도 재추정/최종추정.",
        "2. 2023 도시 총계 예시는 진단용이고, 성능 주장은 2022~2023 평균 WAPE를 기준으로 한다. `annual cell abs error sum`은 도시 총계 차이가 아니라 중분류별 절대오차 합계다.",
        "3. 분기값은 현재 독립 official quarterly actual이 없어 내부 월별 큐브 집계 검증으로만 둔다. 연간값은 공표 후 연간 벤치마크로 집계검증한다.",
        "4. Q4+1개월의 0%는 예측 성능이 아니라 연간 합계 회계 회수다. 실제 운영 성능은 Q1~Q3 빈티지를 중심으로 봐야 한다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pred = load_predictions()
    delivery = delivery_summary(pred)
    perf = performance_average()
    examples = top_examples(pred)
    validation = validation_matrix(pred)

    delivery.to_csv(OUT / "phase138_2023_operational_city_delivery.csv", index=False)
    perf.to_csv(OUT / "phase138_2022_2023_operational_performance.csv", index=False)
    examples.to_csv(OUT / "phase138_2023_top_middle_examples.csv", index=False)
    validation.to_csv(OUT / "phase138_validation_level_matrix.csv", index=False)
    write_report(delivery, perf, examples, validation)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
