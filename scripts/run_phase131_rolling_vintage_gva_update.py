#!/usr/bin/env python3
"""Phase131: rolling quarterly GVA update protocol for Goyang and Pohang.

This phase turns the poster-oriented 2023 diagnostics into an operational
quarterly update table:

* after Q1 data: estimate Q1 and nowcast annual GVA;
* after Q2 data: estimate Q2, re-check Q1/YTD, and re-nowcast annual GVA;
* after Q3 data: estimate Q3, re-check Q1~Q2/YTD, and re-nowcast annual GVA;
* after Q4 data: estimate Q4, re-check Q1~Q3/YTD, and produce final annual GVA.

The quarterly/monthly city×industry cubes currently available are development
estimates, not independent official quarterly actuals.  Therefore quarter and
YTD rows are labelled as accounting/internal consistency checks.  Annual
nowcast performance is evaluated against the smallest available annual
benchmark constructed from the city monthly cube and, for 2023 middle industry
diagnostics, the Phase130/Phase127 precision registries.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase131_rolling_vintage_gva_update"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase131_rolling_vintage_gva_update.md"

CITY_SPECS = {
    "고양시": {
        "monthly": DATA / "partial_stats_phase41_goyang_emd_group_monthly.parquet",
        "value_col": "estimated_emd_group_monthly_gva",
        "precision_registry": DATA / "phase130_goyang_precision_adoption" / "phase130_goyang_precision_registry.csv",
        "precision_pred_col": "phase130_predicted_gva_eok",
        "precision_err_col": "phase130_error_gva_eok",
        "precision_rate_col": "phase130_error_rate_pct",
    },
    "포항시": {
        "monthly": DATA / "partial_stats_phase42_pohang_emd_group_monthly.parquet",
        "value_col": "estimated_emd_group_monthly_gva",
        "precision_registry": DATA / "phase127_precision_comwel_after_phase114" / "phase127_strict_registry.csv",
        "precision_pred_col": "phase127_strict_predicted_gva_eok",
        "precision_err_col": "phase127_strict_error_gva_eok",
        "precision_rate_col": "phase127_strict_error_rate_pct",
    },
}

VINTAGES = [
    (1, "Q1_plus_1m", "1분기+1개월", "04-30", "Q1 추정; 연간 1차 추정"),
    (2, "Q2_plus_1m", "1~2분기+1개월", "07-31", "Q2 추정; Q1 재검증; 연간 재추정"),
    (3, "Q3_plus_1m", "1~3분기+1개월", "10-31", "Q3 추정; Q1~Q2 재검증; 연간 재추정"),
    (4, "Q4_plus_1m", "1~4분기+1개월", "01-31", "Q4 추정; Q1~Q3 재검증; 연간 최종 추정"),
]

AVAILABLE_DATA_LABEL = {
    1: "1분기",
    2: "1~2분기",
    3: "1~3분기",
    4: "1~4분기",
}


def read_monthly(city: str, spec: dict[str, object]) -> pd.DataFrame:
    df = pd.read_parquet(spec["monthly"])
    value_col = str(spec["value_col"])
    required = ["year", "quarter", "gva_parent_code", "division_code", "division_name", value_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{city} monthly cube missing columns: {missing}")
    out = (
        df.groupby(["year", "quarter", "gva_parent_code", "division_code", "division_name"], as_index=False)[value_col]
        .sum()
        .rename(columns={
            "gva_parent_code": "parent_code",
            "division_code": "middle_code",
            "division_name": "middle_label",
            value_col: "quarter_gva_raw",
        })
    )
    # The monthly cubes are in million KRW-like units; poster/registry tables use eok KRW.
    out["quarter_gva_eok"] = out["quarter_gva_raw"] / 100.0
    out["middle_code"] = out["middle_code"].astype(str).str.zfill(2)
    out["city"] = city
    return out[["city", "year", "quarter", "parent_code", "middle_code", "middle_label", "quarter_gva_eok"]]


def build_seasonal_share(q: pd.DataFrame) -> pd.DataFrame:
    annual = q.groupby(["city", "year", "parent_code", "middle_code"], as_index=False).agg(annual_gva_eok=("quarter_gva_eok", "sum"))
    q = q.merge(annual, on=["city", "year", "parent_code", "middle_code"], how="left")
    q["quarter_share"] = np.where(q["annual_gva_eok"] > 0, q["quarter_gva_eok"] / q["annual_gva_eok"], np.nan)
    rows = []
    for (city, parent, middle), g in q.groupby(["city", "parent_code", "middle_code"], sort=False):
        years = sorted(g["year"].dropna().unique())
        for year in years:
            hist = g[g["year"] < year]
            for k, *_ in VINTAGES:
                hist_k = hist[hist["quarter"].le(k)]
                if hist_k.empty:
                    share = k / 4.0
                    basis = "equal_quarter_no_prior_history"
                    n = 0
                else:
                    share_by_year = hist_k.groupby("year")["quarter_share"].sum()
                    share = float(share_by_year.mean())
                    basis = "prior_year_same_ytd_share"
                    n = int(share_by_year.notna().sum())
                rows.append({
                    "city": city,
                    "year": int(year),
                    "parent_code": parent,
                    "middle_code": middle,
                    "available_quarters": k,
                    "seasonal_ytd_share": share,
                    "seasonal_basis": basis,
                    "history_year_count": n,
                })
    return pd.DataFrame(rows)


def prediction_date(year: int, k: int, suffix: str) -> str:
    if k == 4:
        return f"{year + 1}-{suffix}"
    return f"{year}-{suffix}"


def build_predictions(q: pd.DataFrame, seasonal: pd.DataFrame) -> pd.DataFrame:
    annual = q.groupby(["city", "year", "parent_code", "middle_code", "middle_label"], as_index=False).agg(actual_annual_gva_eok=("quarter_gva_eok", "sum"))
    preds = []
    for _, a in annual.iterrows():
        subset = q[
            q["city"].eq(a.city)
            & q["year"].eq(a.year)
            & q["parent_code"].eq(a.parent_code)
            & q["middle_code"].eq(a.middle_code)
        ]
        by_q = subset.set_index("quarter")["quarter_gva_eok"].to_dict()
        for k, vid, label, suffix, task in VINTAGES:
            ytd = sum(float(by_q.get(qq, 0.0)) for qq in range(1, k + 1))
            cur = float(by_q.get(k, 0.0))
            recheck = sum(float(by_q.get(qq, 0.0)) for qq in range(1, k)) if k > 1 else np.nan
            srow = seasonal[
                seasonal["city"].eq(a.city)
                & seasonal["year"].eq(a.year)
                & seasonal["parent_code"].eq(a.parent_code)
                & seasonal["middle_code"].eq(a.middle_code)
                & seasonal["available_quarters"].eq(k)
            ]
            share = float(srow["seasonal_ytd_share"].iloc[0]) if len(srow) else k / 4.0
            basis = str(srow["seasonal_basis"].iloc[0]) if len(srow) else "equal_quarter_fallback"
            hist_n = int(srow["history_year_count"].iloc[0]) if len(srow) else 0
            annual_pred = ytd / share if share > 0 else np.nan
            if k == 4:
                annual_pred = ytd
                basis = "observed_full_year_sum"
            err = abs(annual_pred - float(a.actual_annual_gva_eok)) if pd.notna(annual_pred) else np.nan
            rate = err / float(a.actual_annual_gva_eok) * 100 if float(a.actual_annual_gva_eok) > 0 and pd.notna(err) else np.nan
            amount_tier = "large" if float(a.actual_annual_gva_eok) >= 1000 else "small_or_medium"
            preds.append({
                "city": a.city,
                "year": int(a.year),
                "vintage_id": vid,
                "vintage_label": label,
                "prediction_date": prediction_date(int(a.year), k, suffix),
                "available_quarters": k,
                "task_summary": task,
                "parent_code": a.parent_code,
                "middle_code": a.middle_code,
                "middle_label": a.middle_label,
                "current_quarter": k,
                "current_quarter_estimate_eok": cur,
                "previous_quarters_recheck_eok": recheck,
                "ytd_estimate_eok": ytd,
                "seasonal_ytd_share": share,
                "annual_prediction_eok": annual_pred,
                "actual_annual_gva_eok": float(a.actual_annual_gva_eok),
                "annual_error_eok": err,
                "annual_error_rate_pct": rate,
                "amount_tier": amount_tier,
                "seasonal_basis": basis,
                "history_year_count": hist_n,
                "quarter_validation_status": "internal_monthly_cube_aggregation_not_independent_actual",
                "annual_validation_status": "evaluated_against_year_total_after_publication",
            })
    return pd.DataFrame(preds)


def precision_2023_detail() -> pd.DataFrame:
    frames = []
    for city, spec in CITY_SPECS.items():
        path = Path(spec["precision_registry"])
        if not path.exists():
            continue
        df = pd.read_csv(path, dtype={"middle_code": str})
        df = df[df["city"].eq(city)].copy()
        df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
        pred_col = str(spec["precision_pred_col"])
        err_col = str(spec["precision_err_col"])
        rate_col = str(spec["precision_rate_col"])
        df["precision_prediction_eok"] = df[pred_col]
        df["precision_error_eok"] = df[err_col]
        df["precision_error_rate_pct"] = df[rate_col]
        frames.append(df[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "precision_prediction_eok", "precision_error_eok", "precision_error_rate_pct"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def summarize(preds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eval_df = preds[preds["year"].ge(2022)].copy()
    rows = []
    for keys, g in eval_df.groupby(["city", "vintage_id", "vintage_label", "available_quarters"], sort=False):
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        large = g[g["amount_tier"].eq("large")]
        large_actual = float(large["actual_annual_gva_eok"].sum()) if len(large) else np.nan
        large_err = float(large["annual_error_eok"].sum()) if len(large) else np.nan
        rows.append({
            "city": keys[0],
            "vintage_id": keys[1],
            "vintage_label": keys[2],
            "available_quarters": keys[3],
            "evaluated_years": "2022-2023",
            "cell_count": int(len(g)),
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "wape_pct": err / actual * 100 if actual else np.nan,
            "large_cell_count": int(len(large)),
            "large_actual_sum_eok": large_actual,
            "large_error_sum_eok": large_err,
            "large_wape_pct": large_err / large_actual * 100 if large_actual else np.nan,
            "gt10_cells": int((g["annual_error_rate_pct"] > 10).sum()),
            "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
        })
    summary = pd.DataFrame(rows)

    diag2023 = preds[preds["year"].eq(2023)].copy()
    diag2023["abs_amount_rank"] = diag2023.groupby(["city", "vintage_id"])["actual_annual_gva_eok"].rank(method="first", ascending=False)
    important = diag2023[diag2023["abs_amount_rank"].le(12)].sort_values(["city", "vintage_id", "annual_error_eok"], ascending=[True, True, False])

    precision = precision_2023_detail()
    precision_rows = []
    if not precision.empty:
        for city, g in precision.groupby("city", sort=False):
            actual = float(g["actual_gva_eok"].sum())
            err = float(g["precision_error_eok"].sum())
            large = g[g["actual_gva_eok"].ge(1000)]
            precision_rows.append({
                "city": city,
                "target_year": 2023,
                "precision_route": "phase130_goyang" if city == "고양시" else "phase127_strict_pohang",
                "actual_sum_eok": actual,
                "error_sum_eok": err,
                "wape_pct": err / actual * 100 if actual else np.nan,
                "large_cell_count": int(len(large)),
                "large_wape_pct": float(large["precision_error_eok"].sum()) / float(large["actual_gva_eok"].sum()) * 100 if len(large) else np.nan,
                "gt10_cells": int((g["precision_error_rate_pct"] > 10).sum()),
                "gt20_cells": int((g["precision_error_rate_pct"] > 20).sum()),
            })
    return summary, important, pd.DataFrame(precision_rows)


def accounting_checks(preds: pd.DataFrame) -> pd.DataFrame:
    checks = []
    # Q4 annual prediction must recover YTD/full year exactly.
    q4 = preds[preds["available_quarters"].eq(4)].copy()
    q4["diff"] = (q4["annual_prediction_eok"] - q4["actual_annual_gva_eok"]).abs()
    checks.append({
        "check_id": "q4_full_year_recovery",
        "rows": int(len(q4)),
        "max_abs_diff_eok": float(q4["diff"].max()) if len(q4) else np.nan,
        "pass": bool((q4["diff"] < 1e-9).all()) if len(q4) else False,
    })
    # Current quarter + previous recheck should equal YTD.
    tmp = preds.copy()
    tmp["prev_filled"] = tmp["previous_quarters_recheck_eok"].fillna(0.0)
    tmp["diff"] = (tmp["prev_filled"] + tmp["current_quarter_estimate_eok"] - tmp["ytd_estimate_eok"]).abs()
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
            return f"{float(v):,.2f}"
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        return str(v).replace("|", "\\|")

    body = ["| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *body])


def write_report(summary: pd.DataFrame, important: pd.DataFrame, precision: pd.DataFrame, checks: pd.DataFrame) -> None:
    top2023 = important[important["vintage_id"].eq("Q1_plus_1m")].copy()
    REPORT.write_text("\n".join([
        "# Phase131 고양·포항 rolling 분기 GVA 갱신 프로토콜",
        "",
        "## 목적",
        "",
        "분기별 자료가 누적될 때마다 `현재 분기 추정`, `이전 분기 재검증`, `당해년도 재추정`을 갱신하는 운영형 산출물을 만들었다. 현재 분기·월 단위 독립 공식 actual은 없으므로 분기 행은 내부 회계 일관성 검증으로 두고, 성능은 연간 집계값과 2023년 중분류 정밀 레지스트리로 평가한다.",
        "",
        "## 분기 빈티지별 요구사항 매핑",
        "",
        md_table(pd.DataFrame([
            {"vintage_label": label, "available_data": AVAILABLE_DATA_LABEL[k], "prediction_date_rule": suffix, "outputs": task}
            for k, _, label, suffix, task in VINTAGES
        ]), ["vintage_label", "available_data", "prediction_date_rule", "outputs"]),
        "",
        "## 2022~2023 평균 연간 nowcast 성능",
        "",
        md_table(summary.sort_values(["city", "available_quarters"]), ["city", "vintage_label", "evaluated_years", "actual_sum_eok", "error_sum_eok", "wape_pct", "large_cell_count", "large_wape_pct", "gt10_cells", "gt20_cells"]),
        "",
        "## 2023 공표 후 정밀화 성능",
        "",
        md_table(precision, precision.columns.tolist()),
        "",
        "## 2023년 금액 큰 중분류 Q1+1개월 진단 예시",
        "",
        md_table(top2023.sort_values(["city", "annual_error_eok"], ascending=[True, False]), ["city", "middle_label", "actual_annual_gva_eok", "annual_prediction_eok", "annual_error_eok", "annual_error_rate_pct", "amount_tier", "seasonal_basis"], n=30),
        "",
        "## 회계 검증",
        "",
        md_table(checks, checks.columns.tolist()),
        "",
        "## 해석",
        "",
        "1. 금액이 큰 업종은 상대오차보다 금액가중 WAPE를 우선 지표로 본다.",
        "2. Q1~Q3 연간 nowcast는 과거 같은 누적분기 비중을 사용한다. Q4의 0% 오차는 예측 성능이 아니라 1~4분기 합계가 연간 최종값을 회계적으로 회수한다는 뜻이다.",
        "3. 현재 월별 큐브는 엄격한 실시간 공표 빈티지 archive가 아니므로, 분기 성능은 독립 actual 검증이 아니라 집계 일관성 검증으로만 주장한다.",
        "4. 다음 단계는 고양·포항 월별 직접 활동자료에 공표일자를 붙여, Q+1개월 시점에 실제로 이용 가능한 자료만으로 parent/middle quarterly vintage를 재산출하는 것이다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    q = pd.concat([read_monthly(city, spec) for city, spec in CITY_SPECS.items()], ignore_index=True)
    seasonal = build_seasonal_share(q)
    preds = build_predictions(q, seasonal)
    summary, important, precision = summarize(preds)
    checks = accounting_checks(preds)

    q.to_csv(OUT / "phase131_middle_quarter_benchmark.csv", index=False)
    seasonal.to_csv(OUT / "phase131_seasonal_ytd_shares.csv", index=False)
    preds.to_csv(OUT / "phase131_rolling_vintage_predictions.csv", index=False)
    summary.to_csv(OUT / "phase131_annual_nowcast_performance_summary.csv", index=False)
    important.to_csv(OUT / "phase131_2023_amount_weighted_diagnostics.csv", index=False)
    precision.to_csv(OUT / "phase131_2023_precision_summary.csv", index=False)
    checks.to_csv(OUT / "phase131_accounting_checks.csv", index=False)
    write_report(summary, important, precision, checks)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
