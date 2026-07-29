#!/usr/bin/env python3
"""Validate PPS contract amount signals for construction GVA allocation.

The script consumes monthly CSV files produced by Phase248.  It can run on
partial collections, but adoption requires complete months for the validation
years.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MONTHLY = ROOT / "data" / "processed" / "phase248_pps_contract_monthly"
QA = ROOT / "data" / "processed" / "phase249_pps_contract_quality_audit" / "phase249_monthly_collection_quality.csv"
ERR = ROOT / "nationwide" / "outputs" / "annual_sigungu_activity_error_audit.csv"
OUT = ROOT / "data" / "processed" / "phase250_pps_contract_construction_route_validation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase250_pps_contract_construction_route_validation.md"


def safe_read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return pd.DataFrame()


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


def load_complete_months(start_year: int = 2015, end_year: int = 2025) -> pd.DataFrame:
    qa = safe_read(QA)
    complete_periods: set[str] | None = None
    complete_col = "quality_complete" if "quality_complete" in qa.columns else "complete"
    if not qa.empty and "period" in qa and complete_col in qa:
        qa["period"] = qa["period"].astype(str).str.zfill(6)
        complete_periods = set(qa[qa[complete_col].astype(str).str.lower().isin(["true", "1"])]["period"])
    frames = []
    for p in sorted(MONTHLY.glob("pps_contract_*.csv")):
        period = p.stem.rsplit("_", 1)[-1]
        year = int(period[:4])
        if not (start_year <= year <= end_year):
            continue
        if complete_periods is not None and period not in complete_periods:
            continue
        df = safe_read(p)
        if df.empty or "source_period" not in df.columns:
            continue
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def base_frame() -> pd.DataFrame:
    err = pd.read_csv(ERR)
    x = err[(err["activity"].eq("건설업")) & (err["year"].between(2021, 2023)) & (err["actual_eok"].gt(0))].copy()
    prov = x.groupby(["quarter_region", "year"], as_index=False).agg(sido_actual_eok=("actual_eok", "sum"), sido_predicted_eok=("predicted_eok", "sum"))
    x = x.merge(prov, on=["quarter_region", "year"], how="left")
    x["current_share"] = x["predicted_eok"] / x["sido_predicted_eok"]
    x["baseline_parent_predicted_eok"] = x["sido_actual_eok"] * x["current_share"]
    return x


def metric(df: pd.DataFrame, pred_col: str) -> dict[str, float | int]:
    actual = df["actual_eok"].astype(float)
    pred = df[pred_col].astype(float)
    abs_err = (pred - actual).abs()
    ape = np.where(actual.gt(0), abs_err / actual * 100, np.nan)
    return {
        "rows": int(len(df)),
        "actual_sum_eok": float(actual.sum()),
        "abs_error_sum_eok": float(abs_err.sum()),
        "wape_pct": float(abs_err.sum() / actual.sum() * 100) if actual.sum() else np.nan,
        "over10_cells": int((ape > 10).sum()),
        "over20_cells": int((ape > 20).sum()),
        "max_ape_pct": float(np.nanmax(ape)) if len(ape) else np.nan,
    }


def contract_signal_monthly(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    x = df.copy()
    x = x[x["matched_province_full"].fillna("").ne("") & x["matched_city"].fillna("").ne("")].copy()
    x["amount_eok"] = pd.to_numeric(x.get("contract_amount_eok"), errors="coerce").fillna(0)
    x = x[x["amount_eok"].gt(0)].copy()
    x["contract_date"] = pd.to_datetime(x.get("cntrctDate"), errors="coerce")
    x["start_date"] = pd.to_datetime(x.get("cbgnDate"), errors="coerce")
    x["completion_date"] = pd.to_datetime(x.get("ttalCcmpltDate"), errors="coerce")
    rows = []
    # Contract-date signal.
    c = x[x["contract_date"].notna()].copy()
    c["year"] = c["contract_date"].dt.year
    c["quarter"] = c["contract_date"].dt.to_period("Q").astype(str)
    c["month"] = c["contract_date"].dt.to_period("M").astype(str)
    rows.append(c.assign(signal_type="contract_date", signal_amount_eok=c["amount_eok"]))
    # Start-date signal.
    s = x[x["start_date"].notna()].copy()
    s["year"] = s["start_date"].dt.year
    s["quarter"] = s["start_date"].dt.to_period("Q").astype(str)
    s["month"] = s["start_date"].dt.to_period("M").astype(str)
    rows.append(s.assign(signal_type="start_date", signal_amount_eok=s["amount_eok"]))
    # Annualized duration allocation; monthly expansion is intentionally capped
    # to rows with valid start/completion dates and a sane duration.
    d = x[x["start_date"].notna() & x["completion_date"].notna() & x["completion_date"].ge(x["start_date"])].copy()
    d["duration_months"] = ((d["completion_date"].dt.year - d["start_date"].dt.year) * 12 + (d["completion_date"].dt.month - d["start_date"].dt.month) + 1).clip(lower=1, upper=60)
    expanded = []
    for r in d.itertuples(index=False):
        months = int(r.duration_months)
        amount = float(r.amount_eok) / months
        start = pd.Timestamp(r.start_date).to_period("M")
        for i in range(months):
            m = start + i
            expanded.append(
                {
                    "matched_province_full": r.matched_province_full,
                    "matched_city": r.matched_city,
                    "year": int(m.year),
                    "quarter": str(m.asfreq("Q")),
                    "month": str(m),
                    "signal_type": "duration_allocated",
                    "signal_amount_eok": amount,
                }
            )
    if expanded:
        rows.append(pd.DataFrame(expanded))
    all_rows = pd.concat(rows, ignore_index=True, sort=False)
    all_rows = all_rows[all_rows["year"].between(2015, 2025)].copy()
    return (
        all_rows.groupby(["signal_type", "matched_province_full", "matched_city", "year", "quarter", "month"], as_index=False)
        .agg(signal_amount_eok=("signal_amount_eok", "sum"), signal_rows=("signal_amount_eok", "count"))
    )


def annual_signal(monthly_signal: pd.DataFrame) -> pd.DataFrame:
    if monthly_signal.empty:
        return pd.DataFrame()
    return (
        monthly_signal.groupby(["signal_type", "matched_province_full", "matched_city", "year"], as_index=False)
        .agg(signal_amount_eok=("signal_amount_eok", "sum"), signal_rows=("signal_rows", "sum"))
    )


def metric_by_year(df: pd.DataFrame, pred_col: str, train_years: set[int] | None = None, holdout_years: set[int] | None = None) -> dict[str, float | int | str]:
    x = df.copy()
    if holdout_years is not None:
        x = x[x["year"].isin(holdout_years)].copy()
    out = metric(x, pred_col)
    out["train_years"] = ",".join(map(str, sorted(train_years or [])))
    out["holdout_years"] = ",".join(map(str, sorted(holdout_years or [])))
    return out


def candidate_detail(base: pd.DataFrame, sg: pd.DataFrame, signal_type: str, alpha: float) -> pd.DataFrame:
    x = base.merge(
        sg.rename(columns={"matched_province_full": "province_full", "matched_city": "city"}),
        on=["province_full", "city", "year"],
        how="left",
    )
    x["signal_amount_eok"] = x["signal_amount_eok"].fillna(0.0)
    total = x.groupby(["province_full", "year"])["signal_amount_eok"].transform("sum")
    x["signal_share"] = np.where(total.gt(0), x["signal_amount_eok"] / total, np.nan)
    raw = np.where(x["signal_share"].notna(), x["current_share"] + alpha * (x["signal_share"].fillna(0) - x["current_share"]), x["current_share"])
    raw = pd.Series(raw, index=x.index).clip(lower=0)
    raw_sum = raw.groupby([x["province_full"], x["year"]]).transform("sum")
    x["candidate_share"] = np.where(raw_sum.gt(0), raw / raw_sum, x["current_share"])
    x["candidate_predicted_eok"] = x["sido_actual_eok"] * x["candidate_share"]
    x["candidate_abs_error_eok"] = (x["candidate_predicted_eok"] - x["actual_eok"]).abs()
    x["candidate_ape_pct"] = np.where(x["actual_eok"].gt(0), x["candidate_abs_error_eok"] / x["actual_eok"] * 100, np.nan)
    x["scenario"] = f"{signal_type}_alpha{alpha:.3f}"
    x["signal_type"] = signal_type
    x["alpha"] = alpha
    return x


def evaluate(base: pd.DataFrame, signal: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = [dict(metric_by_year(base, "baseline_parent_predicted_eok"), scenario="baseline_parent_control", signal_type="baseline", alpha=0.0, fold="all")]
    rolling_rows = []
    details = []
    for signal_type, sg in signal.groupby("signal_type"):
        for alpha in [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]:
            d = candidate_detail(base, sg, signal_type, alpha)
            scenario = f"{signal_type}_alpha{alpha:.3f}"
            rows.append(dict(metric_by_year(d, "candidate_predicted_eok"), scenario=scenario, signal_type=signal_type, alpha=alpha, fold="all"))
            for holdout in sorted(d["year"].unique()):
                train = set(int(y) for y in d["year"].unique() if y != holdout)
                hold = {int(holdout)}
                rolling_rows.append(dict(metric_by_year(d, "candidate_predicted_eok", train, hold), scenario=scenario, signal_type=signal_type, alpha=alpha, fold=f"holdout_{holdout}"))
            details.append(d)
    rolling = pd.DataFrame(rolling_rows)
    return (
        pd.DataFrame(rows).sort_values(["wape_pct", "over10_cells"]),
        pd.concat(details, ignore_index=True) if details else pd.DataFrame(),
        rolling.sort_values(["scenario", "fold"]) if not rolling.empty else pd.DataFrame(),
    )


def temporal_estimates(monthly_signal: pd.DataFrame, selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if monthly_signal.empty or selected.empty:
        return pd.DataFrame(), pd.DataFrame()
    scenario = str(selected.iloc[0]["scenario"])
    signal_type = str(selected.iloc[0]["signal_type"])
    alpha = float(selected.iloc[0]["alpha"])
    annual = selected[["province_full", "city", "year", "actual_eok", "sido_actual_eok", "current_share", "candidate_share", "candidate_predicted_eok"]].copy()
    m = monthly_signal[monthly_signal["signal_type"].eq(signal_type)].copy()
    m = m.rename(columns={"matched_province_full": "province_full", "matched_city": "city"})
    m_total = m.groupby(["province_full", "city", "year"])["signal_amount_eok"].transform("sum")
    m["within_city_year_share"] = np.where(m_total.gt(0), m["signal_amount_eok"] / m_total, np.nan)
    out = annual.merge(m, on=["province_full", "city", "year"], how="left")
    # If a city-year has no monthly signal, fall back to equal 12-month split so
    # annual consistency is preserved and the missing signal is explicit.
    missing = out["month"].isna()
    if missing.any():
        fill = []
        fallback_keys = out.loc[missing, ["province_full", "city", "year", "actual_eok", "sido_actual_eok", "current_share", "candidate_share", "candidate_predicted_eok"]].drop_duplicates()
        for r in fallback_keys.itertuples(index=False):
            for mm in range(1, 13):
                period = pd.Period(f"{int(r.year)}-{mm:02d}", freq="M")
                fill.append(
                    {
                        "province_full": r.province_full,
                        "city": r.city,
                        "year": int(r.year),
                        "actual_eok": r.actual_eok,
                        "sido_actual_eok": r.sido_actual_eok,
                        "current_share": r.current_share,
                        "candidate_share": r.candidate_share,
                        "candidate_predicted_eok": r.candidate_predicted_eok,
                        "signal_type": signal_type,
                        "quarter": str(period.asfreq("Q")),
                        "month": str(period),
                        "signal_amount_eok": 0.0,
                        "signal_rows": 0,
                        "within_city_year_share": 1 / 12,
                    }
                )
        out = pd.concat([out[~missing], pd.DataFrame(fill)], ignore_index=True, sort=False)
    out["within_city_year_share"] = out["within_city_year_share"].fillna(1 / 12)
    out["estimated_eok"] = out["candidate_predicted_eok"] * out["within_city_year_share"]
    out["scenario"] = scenario
    out["alpha"] = alpha
    month_cols = ["scenario", "signal_type", "alpha", "province_full", "city", "year", "quarter", "month", "estimated_eok", "signal_amount_eok", "signal_rows"]
    month = out[month_cols].sort_values(["province_full", "city", "month"])
    quarter = (
        month.groupby(["scenario", "signal_type", "alpha", "province_full", "city", "year", "quarter"], as_index=False)
        .agg(estimated_eok=("estimated_eok", "sum"), signal_amount_eok=("signal_amount_eok", "sum"), signal_rows=("signal_rows", "sum"))
    )
    return month, quarter


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    contracts = load_complete_months()
    monthly_signal = contract_signal_monthly(contracts)
    signal = annual_signal(monthly_signal)
    base = base_frame()
    summary, detail, rolling = evaluate(base, signal) if not signal.empty else (
        pd.DataFrame([dict(metric_by_year(base, "baseline_parent_predicted_eok"), scenario="baseline_parent_control", signal_type="baseline", alpha=0.0, fold="all")]),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    current = summary[summary["scenario"].eq("baseline_parent_control")].iloc[0]
    baseline_by_holdout = {}
    for holdout in sorted(base["year"].unique()):
        baseline_by_holdout[int(holdout)] = metric_by_year(base, "baseline_parent_predicted_eok", set(int(y) for y in base["year"].unique() if y != holdout), {int(holdout)})
    if not rolling.empty:
        rolling["baseline_wape_pct"] = rolling["holdout_years"].map(lambda y: baseline_by_holdout.get(int(y), {}).get("wape_pct") if str(y).isdigit() else np.nan)
        rolling["baseline_over10_cells"] = rolling["holdout_years"].map(lambda y: baseline_by_holdout.get(int(y), {}).get("over10_cells") if str(y).isdigit() else np.nan)
        rolling["rolling_improves_wape"] = rolling["wape_pct"].lt(rolling["baseline_wape_pct"])
        roll_gate = (
            rolling.groupby(["scenario", "signal_type", "alpha"], as_index=False)
            .agg(
                holdout_folds=("fold", "count"),
                improved_folds=("rolling_improves_wape", "sum"),
                mean_holdout_wape_pct=("wape_pct", "mean"),
                mean_baseline_wape_pct=("baseline_wape_pct", "mean"),
                max_holdout_wape_pct=("wape_pct", "max"),
            )
        )
        roll_gate["mean_wape_improvement_pctp"] = roll_gate["mean_baseline_wape_pct"] - roll_gate["mean_holdout_wape_pct"]
    else:
        roll_gate = pd.DataFrame()
    safe = summary[
        summary["scenario"].ne("baseline_parent_control")
        & summary["wape_pct"].lt(float(current["wape_pct"]))
        & summary["over10_cells"].le(int(current["over10_cells"]))
        & summary["over20_cells"].le(int(current["over20_cells"]))
        & summary["max_ape_pct"].le(float(current["max_ape_pct"]))
    ].copy()
    if not roll_gate.empty:
        safe = safe.merge(roll_gate, on=["scenario", "signal_type", "alpha"], how="left")
        safe = safe[safe["mean_wape_improvement_pctp"].gt(0) & safe["improved_folds"].ge((safe["holdout_folds"] * 0.5).round())].copy()
    monthly_signal.to_csv(OUT / "phase250_pps_contract_signal_sigungu_month.csv", index=False, encoding="utf-8-sig")
    (
        monthly_signal.groupby(["signal_type", "matched_province_full", "matched_city", "year", "quarter"], as_index=False)
        .agg(signal_amount_eok=("signal_amount_eok", "sum"), signal_rows=("signal_rows", "sum"))
        .to_csv(OUT / "phase250_pps_contract_signal_sigungu_quarter.csv", index=False, encoding="utf-8-sig")
        if not monthly_signal.empty
        else pd.DataFrame().to_csv(OUT / "phase250_pps_contract_signal_sigungu_quarter.csv", index=False, encoding="utf-8-sig")
    )
    signal.to_csv(OUT / "phase250_pps_contract_signal_sigungu_year.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase250_candidate_summary.csv", index=False, encoding="utf-8-sig")
    if not rolling.empty:
        rolling.to_csv(OUT / "phase250_rolling_holdout_detail.csv", index=False, encoding="utf-8-sig")
        roll_gate.to_csv(OUT / "phase250_rolling_holdout_gate.csv", index=False, encoding="utf-8-sig")
    safe.to_csv(OUT / "phase250_guardrail_safe_candidates.csv", index=False, encoding="utf-8-sig")
    if not detail.empty:
        detail.to_csv(OUT / "phase250_candidate_detail.csv", index=False, encoding="utf-8-sig")
    if not safe.empty and not detail.empty:
        selected_detail = detail[detail["scenario"].eq(str(safe.iloc[0]["scenario"]))].copy()
        month_est, quarter_est = temporal_estimates(monthly_signal, selected_detail)
        month_est.to_csv(OUT / "phase250_selected_sigungu_month_estimates.csv", index=False, encoding="utf-8-sig")
        quarter_est.to_csv(OUT / "phase250_selected_sigungu_quarter_estimates.csv", index=False, encoding="utf-8-sig")

    complete_months = contracts["source_period"].astype(str).nunique() if not contracts.empty else 0
    report = f"""# Phase250 조달청 계약정보 기반 건설업 route 검증

생성시각: {datetime.now().astimezone().isoformat(timespec='seconds')}

## 1. 입력 상태

- 사용 월 수: {complete_months}
- 계약행 수: {len(contracts):,}
- 지역매칭 신호행: {len(signal):,}

이 스크립트는 complete 월만 사용한다. 2015~2025 전량 수집 전에는 결과가 부분 검증이라는 점을 유지한다.

## 2. 후보 성능 상위

{md_table(summary[["scenario", "signal_type", "alpha", "rows", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct"]], max_rows=20, digits=3)}

## 3. Guardrail 통과 후보

{md_table(safe[["scenario", "signal_type", "alpha", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct"]], max_rows=20, digits=3) if not safe.empty else "_없음_"}

## 4. Rolling holdout 검증

{md_table(roll_gate[["scenario", "signal_type", "alpha", "holdout_folds", "improved_folds", "mean_baseline_wape_pct", "mean_holdout_wape_pct", "mean_wape_improvement_pctp", "max_holdout_wape_pct"]].sort_values("mean_wape_improvement_pctp", ascending=False), max_rows=20, digits=3) if not roll_gate.empty else "_신호가 부족해 산출하지 못함_"}

## 5. 월·분기 추정 산출물

안전 후보가 있을 때 `phase250_selected_sigungu_month_estimates.csv`, `phase250_selected_sigungu_quarter_estimates.csv`를 생성한다. 연간 검증 가능한 GVA를 먼저 통과한 후보만 월·분기로 배분하며, city-year 신호가 없으면 연간 합 보존을 위해 균등 12개월 fallback을 명시적으로 적용한다.

## 6. 판정

전량 수집 완료 후 `contract_date`, `start_date`, `duration_allocated` 세 기준을 비교해 운영 route를 선택한다. 본모형 채택은 전체 WAPE 개선, over10/over20 셀 비증가, max APE 비악화, rolling holdout 평균 개선을 동시에 요구한다. 현재 산출값은 수집 완료월 기준의 중간 점검값이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(summary.head(10).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
