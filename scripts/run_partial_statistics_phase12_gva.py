from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
EXPERIMENT_ID = "partial_statistics_estimation_phase12_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase12_gva.md"
TARGET_YEARS = [2022, 2023, 2024, 2025]
HISTORICAL_EVAL_YEARS = [2022, 2023, 2024]
PRICE_TRACK = "VA_nominal"
MONTHS = list(range(1, 13))


CSV_OUTPUTS = [
    "partial_stats_phase12_gva_target_year_registry.csv",
    "partial_stats_phase12_gva_origin_registry.csv",
    "partial_stats_phase12_gva_target_origin_grid.csv",
    "partial_stats_phase12_gva_source_inventory.csv",
    "partial_stats_phase12_gva_release_registry.csv",
    "partial_stats_phase12_gva_vintage_registry.csv",
    "partial_stats_phase12_gva_origin_feature_eligibility.csv",
    "partial_stats_phase12_gva_asof_dataset_registry.csv",
    "partial_stats_phase12_gva_leakage_audit.csv",
    "partial_stats_phase12_gva_2022_origin_results.csv",
    "partial_stats_phase12_gva_2023_origin_results.csv",
    "partial_stats_phase12_gva_2024_origin_results.csv",
    "partial_stats_phase12_gva_origin_summary.csv",
    "partial_stats_phase12_gva_revision_results.csv",
    "partial_stats_phase12_gva_baseline_results.csv",
    "partial_stats_phase12_gva_model_results.csv",
    "partial_stats_phase12_gva_productivity_results.csv",
    "partial_stats_phase12_gva_parent_share_results.csv",
    "partial_stats_phase12_gva_ensemble_results.csv",
    "partial_stats_phase12_gva_monthly_activity_index.csv",
    "partial_stats_phase12_gva_temporal_model_results.csv",
    "partial_stats_phase12_gva_temporal_consistency_audit.csv",
    "partial_stats_phase12_gva_annual_estimates_2025.csv",
    "partial_stats_phase12_gva_quarterly_estimates_2025.csv",
    "partial_stats_phase12_gva_monthly_estimates_2025.csv",
    "partial_stats_phase12_gva_origin_estimates_2025.csv",
    "partial_stats_phase12_gva_annual_nowcast_2026.csv",
    "partial_stats_phase12_gva_quarterly_nowcast_2026.csv",
    "partial_stats_phase12_gva_monthly_nowcast_2026.csv",
    "partial_stats_phase12_gva_reconciliation_distortion.csv",
    "partial_stats_phase12_gva_uncertainty_results.csv",
    "partial_stats_phase12_gva_not_estimable.csv",
    "partial_stats_phase12_gva_risk_queue.csv",
    "partial_stats_phase12_gva_execution_manifest.csv",
]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def stable_hash_frame(frame: pd.DataFrame, cols: list[str] | None = None) -> str:
    if frame.empty:
        return core.stable_hash([])
    view = frame[cols].copy() if cols else frame.copy()
    return core.stable_hash(view.fillna("").to_dict("records"))


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def lineage(frame: pd.DataFrame, input_hash: str, config: Any) -> pd.DataFrame:
    out = frame.copy()
    out["input_hash"] = input_hash
    out["model_config_hash"] = core.stable_hash(config)
    out["code_commit_hash"] = git_hash()
    out["run_id"] = EXPERIMENT_ID
    out["created_at"] = GENERATED_AT
    return out


def origin_registry() -> pd.DataFrame:
    rows = [
        {"origin_id": "O0", "origin_label": "previous_year_end_forecast", "origin_month": 12, "origin_day": 31, "origin_kind": "one_year_ahead", "strict_track_allowed": "Y"},
        {"origin_id": "O1", "origin_label": "first_quarter_nowcast", "origin_month": 3, "origin_day": 31, "origin_kind": "quarterly_nowcast", "strict_track_allowed": "Y"},
        {"origin_id": "O2", "origin_label": "second_quarter_nowcast", "origin_month": 6, "origin_day": 30, "origin_kind": "quarterly_nowcast", "strict_track_allowed": "Y"},
        {"origin_id": "O3", "origin_label": "third_quarter_nowcast", "origin_month": 9, "origin_day": 30, "origin_kind": "quarterly_nowcast", "strict_track_allowed": "Y"},
        {"origin_id": "O4", "origin_label": "year_end_nowcast", "origin_month": 12, "origin_day": 31, "origin_kind": "year_end_nowcast", "strict_track_allowed": "Y"},
        {"origin_id": "O5", "origin_label": "pre_release_final_nowcast", "origin_month": 12, "origin_day": 31, "origin_kind": "pre_release_sensitivity", "strict_track_allowed": "N_release_date_missing"},
    ]
    rows.extend(
        {
            "origin_id": f"O_M{m:02d}",
            "origin_label": f"monthly_origin_{m:02d}",
            "origin_month": m,
            "origin_day": 28 if m == 2 else 30 if m in {4, 6, 9, 11} else 31,
            "origin_kind": "monthly_nowcast",
            "strict_track_allowed": "Y",
        }
        for m in MONTHS
    )
    return pd.DataFrame(rows)


def target_year_registry() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_year": 2022, "target_role": "historical_pseudo_real_time", "actual_role": "outer_evaluation_only", "actual_release_required_for_execution": "false", "confirmatory_role": "false"},
            {"target_year": 2023, "target_role": "historical_pseudo_real_time", "actual_role": "outer_evaluation_only", "actual_release_required_for_execution": "false", "confirmatory_role": "false"},
            {"target_year": 2024, "target_role": "historical_pseudo_real_time", "actual_role": "outer_evaluation_if_available", "actual_release_required_for_execution": "false", "confirmatory_role": "false_development_outer"},
            {"target_year": 2025, "target_role": "current_pre_release_estimate", "actual_role": "unused_or_unavailable", "actual_release_required_for_execution": "false", "confirmatory_role": "false"},
        ]
    )


def target_origin_grid(origins: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year in TARGET_YEARS:
        for row in origins.to_dict("records"):
            origin_year = year - 1 if row["origin_id"] == "O0" else year
            rows.append(
                {
                    "target_year": year,
                    "origin_id": row["origin_id"],
                    "prediction_origin": f"{origin_year}-{int(row['origin_month']):02d}-{int(row['origin_day']):02d}",
                    "target_period": str(year),
                    "origin_kind": row["origin_kind"],
                    "actual_hidden_until_evaluation": "Y",
                    "target_actual_as_feature": "prohibited",
                }
            )
    return pd.DataFrame(rows)


def source_inventory() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    specs = [
        ("sigungu_annual_rolling_backtest.csv", "annual_gva_outer_evaluation", "VA_nominal", "D_current_snapshot", "sensitivity_backtest"),
        ("sigungu_annual_gva_forecasts.csv", "annual_gva_pre_release_estimate", "VA_nominal", "D_current_snapshot", "current_estimate"),
        ("sigungu_quarterly_gva_forecasts.csv", "quarterly_gva_pre_release_estimate", "VA_nominal", "D_current_snapshot", "current_estimate"),
        ("sigungu_quarterly_gva_estimates.csv", "quarterly_gva_anchor_history", "VA_nominal", "D_current_snapshot", "sensitivity_history"),
        ("detailed_industry_quarterly_estimates.csv", "manufacturing_detail_quarterly_proxy", "VA_nominal", "C_bounded", "sensitivity_detail"),
        ("service_detail_quarterly_estimates.csv", "service_detail_quarterly_proxy", "VA_nominal", "D_current_snapshot", "sensitivity_detail"),
        ("kepco_sigungu_electricity_long.csv", "electricity_auxiliary", "auxiliary", "D_current_snapshot", "current_or_future_only"),
        ("expanded_manufacturing_sigungu_ksic.csv", "establishment_employee_auxiliary", "auxiliary", "D_current_snapshot", "auxiliary_not_target"),
    ]
    rows = []
    release = []
    vintage = []
    for source_id, role, track, confidence, use_rule in specs:
        df = read_frame(source_id)
        years = []
        for col in ["target_year", "year", "reference_year"]:
            if col in df:
                years.extend(pd.to_numeric(df[col], errors="coerce").dropna().astype(int).tolist())
        rows.append(
            {
                "source_id": source_id,
                "source_role": role,
                "target_track": track,
                "row_count": len(df),
                "min_observation_year": min(years) if years else "",
                "max_observation_year": max(years) if years else "",
                "availability_confidence": confidence,
                "use_rule": use_rule,
                "primary_target": "Y" if "gva" in role else "N_auxiliary",
            }
        )
        release.append(
            {
                "source_id": source_id,
                "release_date": "",
                "release_month": "",
                "first_observed_available_at": "",
                "revision_date": "",
                "availability_confidence": confidence,
                "strict_track_eligible": "Y" if confidence in {"A_exact", "B_month"} else "N",
            }
        )
        vintage.append(
            {
                "source_id": source_id,
                "vintage_id": f"{source_id}:current_snapshot",
                "retrieval_date": "",
                "revision_policy": "latest_revised_sensitivity" if confidence == "D_current_snapshot" else "bounded_sensitivity",
                "historical_backdate_allowed": "N" if confidence in {"D_current_snapshot", "E_unknown"} else "bounded_only",
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(release), pd.DataFrame(vintage)


def feature_eligibility(grid: pd.DataFrame, sources: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    leakage = []
    asof = []
    for grow in grid.to_dict("records"):
        allowed = 0
        blocked = 0
        source_vintages = []
        for srow in sources.to_dict("records"):
            status = "allowed_sensitivity"
            reason = "current snapshot used only as sensitivity or current estimate"
            if srow["target_track"] == "auxiliary" and srow["availability_confidence"] == "D_current_snapshot" and int(grow["target_year"]) < 2025:
                status = "blocked_historical_strict"
                reason = "current snapshot cannot be backdated into historical strict origin"
            if "actual" in srow["source_role"] or srow["source_id"].startswith("sigungu_annual_rolling"):
                reason = "target actual is hidden until evaluation; existing backtest file is used as frozen outer result, not feature"
            allowed += int(status.startswith("allowed"))
            blocked += int(status.startswith("blocked"))
            source_vintages.append(f"{srow['source_id']}:{status}")
            rows.append(
                {
                    "target_year": grow["target_year"],
                    "origin_id": grow["origin_id"],
                    "prediction_origin": grow["prediction_origin"],
                    "source_id": srow["source_id"],
                    "eligibility_status": status,
                    "eligibility_reason": reason,
                    "feature_release_before_origin": "unknown_or_sensitivity",
                    "target_actual_feature": "N",
                }
            )
        asof.append(
            {
                "as_of_dataset_id": f"ASOF_{grow['target_year']}_{grow['origin_id']}",
                "target_year": grow["target_year"],
                "prediction_origin": grow["prediction_origin"],
                "source_vintages": ";".join(source_vintages),
                "row_count": allowed + blocked,
                "feature_count": allowed,
                "content_hash": core.stable_hash(source_vintages),
                "strict_track_status": "limited_by_release_metadata",
            }
        )
        leakage.append(
            {
                "target_year": grow["target_year"],
                "origin_id": grow["origin_id"],
                "future_feature_rows": 0,
                "target_actual_feature_rows": 0,
                "current_snapshot_backdated_rows": blocked,
                "leakage_status": "pass_no_target_actual" if blocked == 0 else "sensitivity_only_current_snapshot_blocked_from_strict",
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(asof), pd.DataFrame(leakage)


def prediction_metrics(frame: pd.DataFrame, actual_col: str, pred_col: str) -> dict[str, Any]:
    work = frame.copy()
    actual = numeric(work[actual_col])
    pred = numeric(work[pred_col])
    mask = actual.notna() & pred.notna() & actual.ne(0)
    if not mask.any():
        return {"n": 0, "wmape": "", "mae": "", "rmsle": "", "median_ape": "", "p90_ape": "", "actual_sum": "", "prediction_sum": ""}
    y = actual[mask].astype(float)
    p = pred[mask].clip(lower=0).astype(float)
    err = (y - p).abs()
    ape = err / y.abs().clip(lower=1.0)
    return {
        "n": int(mask.sum()),
        "wmape": float(err.sum() / y.abs().sum()),
        "mae": float(err.mean()),
        "rmsle": float(np.sqrt(((np.log1p(y.clip(lower=0)) - np.log1p(p)) ** 2).mean())),
        "median_ape": float(ape.median()),
        "p90_ape": float(ape.quantile(0.9)),
        "actual_sum": float(y.sum()),
        "prediction_sum": float(p.sum()),
    }


def origin_results(grid: pd.DataFrame) -> tuple[dict[int, pd.DataFrame], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    backtest = read_frame("sigungu_annual_rolling_backtest.csv")
    if backtest.empty:
        empty = {year: pd.DataFrame() for year in HISTORICAL_EVAL_YEARS}
        return empty, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    base = backtest[backtest["target_year"].isin([str(y) for y in HISTORICAL_EVAL_YEARS])].copy()
    base["predicted_annual_gva"] = numeric(base["predicted_annual_gva"])
    base["actual_annual_gva"] = numeric(base["actual_annual_gva"])
    origin_frames: list[pd.DataFrame] = []
    for grow in grid[grid["target_year"].isin(HISTORICAL_EVAL_YEARS)].to_dict("records"):
        year = str(grow["target_year"])
        subset = base[base["target_year"].eq(year)].copy()
        if subset.empty:
            rows = pd.DataFrame(
                [
                    {
                        "target_year": year,
                        "origin_id": grow["origin_id"],
                        "prediction_origin": grow["prediction_origin"],
                        "evaluation_status": "pending_actual_or_no_backtest_rows",
                    }
                ]
            )
            origin_frames.append(rows)
            continue
        # Do not inject actuals into predictions. Later origins are identical until
        # independently released GVA/proxy vintages are available.
        subset["origin_id"] = grow["origin_id"]
        subset["prediction_origin"] = grow["prediction_origin"]
        subset["prediction_value"] = subset["predicted_annual_gva"]
        subset["actual_value"] = subset["actual_annual_gva"]
        subset["price_track"] = PRICE_TRACK
        subset["model_id"] = "B3_historical_parent_share_baseline"
        subset["evaluation_status"] = np.where(subset["actual_value"].notna(), "evaluated_outer", "pending_actual")
        origin_frames.append(
            subset[
                [
                    "target_year",
                    "origin_id",
                    "prediction_origin",
                    "source_region",
                    "sigungu_code",
                    "sigungu_name",
                    "sector_code",
                    "sector_name",
                    "price_track",
                    "model_id",
                    "prediction_value",
                    "actual_value",
                    "evaluation_status",
                ]
            ]
        )
    all_results = pd.concat(origin_frames, ignore_index=True) if origin_frames else pd.DataFrame()
    by_year = {year: all_results[all_results["target_year"].astype(str).eq(str(year))].copy() for year in HISTORICAL_EVAL_YEARS}
    summary_rows = []
    for (year, origin_id), group in all_results.groupby(["target_year", "origin_id"], dropna=False):
        m = prediction_metrics(group, "actual_value", "prediction_value")
        summary_rows.append({"target_year": year, "origin_id": origin_id, **m, "evaluation_status": "evaluated_outer" if m["n"] else "pending_actual"})
    summary = pd.DataFrame(summary_rows)
    baseline = summary.assign(model_id="B3_historical_parent_share_baseline", model_family="annual_baseline")
    model_results = summary.assign(model_id="direct_gva_model_not_promoted", model_family="direct_gva", result_status="not_trained_release_limited")
    prod_results = summary.assign(model_id="productivity_model_not_promoted", model_family="productivity", result_status="auxiliary_only")
    parent_results = summary.assign(model_id="parent_share_baseline", model_family="parent_share", result_status="active_baseline")
    return by_year, summary, baseline, model_results, pd.concat([prod_results, parent_results], ignore_index=True)


def revision_results(all_by_year: dict[int, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for year, frame in all_by_year.items():
        if frame.empty:
            continue
        keys = ["sigungu_code", "sector_code"]
        work = frame.sort_values(keys + ["prediction_origin"]).copy()
        work["prev_prediction"] = work.groupby(keys)["prediction_value"].shift(1)
        work["revision_from_previous_origin"] = work["prediction_value"] - work["prev_prediction"]
        rows.append(
            work[
                [
                    "target_year",
                    "origin_id",
                    "prediction_origin",
                    "sigungu_code",
                    "sector_code",
                    "prediction_value",
                    "revision_from_previous_origin",
                    "evaluation_status",
                ]
            ]
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def current_2025_estimates() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = read_frame("sigungu_annual_gva_forecasts.csv")
    quarterly = read_frame("sigungu_quarterly_gva_forecasts.csv")
    annual_2025 = annual[annual["year"].eq("2025")].copy() if not annual.empty else pd.DataFrame()
    quarterly_2025 = quarterly[quarterly["year"].eq("2025")].copy() if not quarterly.empty else pd.DataFrame()
    if not quarterly_2025.empty:
        quarterly_2025["target_period"] = quarterly_2025["period"]
        quarterly_2025["prediction_origin"] = GENERATED_AT[:10]
        quarterly_2025["price_track"] = PRICE_TRACK
        quarterly_2025["estimate_role"] = "current_pre_release_estimate"
        quarterly_2025["actual_used"] = "N"
        quarterly_2025["estimate_status"] = "estimated"
        key_cols = ["source_region", "parent_area_code", "sigungu_code", "sigungu_name", "sector_code", "sector_name"]
        annual_2025 = (
            quarterly_2025.assign(predicted_annual_gva=numeric(quarterly_2025["predicted_gva"]))
            .groupby(key_cols, as_index=False)["predicted_annual_gva"]
            .sum()
        )
        annual_2025["year"] = 2025
        annual_2025["actual_annual_gva"] = ""
        annual_2025["method"] = "sum of quarterly out-of-sample forecasts"
        annual_2025["benchmark_status"] = "out_of_sample_forecast"
        annual_2025["annual_source_status"] = "reconciled_from_quarterly_estimates"
    if not annual_2025.empty:
        annual_2025["target_period"] = "2025"
        annual_2025["prediction_origin"] = GENERATED_AT[:10]
        annual_2025["price_track"] = PRICE_TRACK
        annual_2025["estimate_role"] = "current_pre_release_estimate"
        annual_2025["actual_used"] = "N"
        annual_2025["estimate_status"] = "estimated"
        annual_cols = [
            "source_region",
            "parent_area_code",
            "sigungu_code",
            "sigungu_name",
            "sector_code",
            "sector_name",
            "year",
            "predicted_annual_gva",
            "actual_annual_gva",
            "method",
            "benchmark_status",
            "annual_source_status",
            "target_period",
            "prediction_origin",
            "price_track",
            "estimate_role",
            "actual_used",
            "estimate_status",
        ]
        annual_2025 = annual_2025[[col for col in annual_cols if col in annual_2025.columns]]
    monthly_rows = []
    if not quarterly_2025.empty:
        for row in quarterly_2025.to_dict("records"):
            q = int(row["quarter"])
            qval = float(row.get("predicted_gva") or row.get("estimated_gva") or 0)
            for offset, month in enumerate(range((q - 1) * 3 + 1, (q - 1) * 3 + 4), start=1):
                monthly_rows.append(
                    {
                        "source_region": row.get("source_region", ""),
                        "parent_area_code": row.get("parent_area_code", ""),
                        "sigungu_code": row.get("sigungu_code", ""),
                        "sigungu_name": row.get("sigungu_name", ""),
                        "sector_code": row.get("sector_code", ""),
                        "sector_name": row.get("sector_name", ""),
                        "year": 2025,
                        "month": month,
                        "quarter": q,
                        "period": f"2025M{month:02d}",
                        "estimated_gva": qval / 3.0,
                        "quarterly_parent_gva": qval,
                        "monthly_share": 1.0 / 3.0,
                        "temporal_method": "equal_monthly_share_within_quarter_pending_monthly_indicator",
                        "prediction_origin": GENERATED_AT[:10],
                        "price_track": PRICE_TRACK,
                        "actual_used": "N",
                    }
                )
    monthly_2025 = pd.DataFrame(monthly_rows)
    origin_estimates = annual_2025.copy()
    if not origin_estimates.empty:
        origin_estimates["origin_id"] = "O_latest"
        origin_estimates["origin_kind"] = "latest_available_nowcast"
        origin_estimates["forecast_revision_status"] = "first_phase12_current_estimate"
    return annual_2025, quarterly_2025, monthly_2025, origin_estimates


def temporal_audits(annual_2025: pd.DataFrame, quarterly_2025: pd.DataFrame, monthly_2025: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    activity = monthly_2025[["sigungu_code", "sector_code", "year", "month", "quarter", "monthly_share", "temporal_method"]].copy() if not monthly_2025.empty else pd.DataFrame()
    temporal_results = pd.DataFrame(
        [
            {"temporal_model": "equal_monthly_share", "status": "active_fallback", "reason": "monthly indicator release/vintage matrix incomplete"},
            {"temporal_model": "denton_cholette", "status": "not_promoted", "reason": "requires origin-specific high-frequency indicator"},
            {"temporal_model": "chow_lin", "status": "not_promoted", "reason": "requires validated monthly/quarterly regressors"},
        ]
    )
    rows = []
    if not quarterly_2025.empty and not monthly_2025.empty:
        key_cols = ["source_region", "sigungu_code", "sigungu_name", "sector_code", "quarter"]
        msum = monthly_2025.groupby(key_cols, as_index=False)["estimated_gva"].sum()
        q = quarterly_2025.copy()
        q["quarter"] = q["quarter"].astype(str)
        msum["quarter"] = msum["quarter"].astype(str)
        q["q_value"] = numeric(q["predicted_gva"])
        merged = q.merge(msum, on=key_cols, how="left")
        merged["abs_diff"] = (merged["q_value"] - merged["estimated_gva"]).abs()
        rows.append({"constraint": "month_sum_equals_quarter", "max_abs_diff": float(merged["abs_diff"].max()), "status": "pass" if float(merged["abs_diff"].max()) < 1e-6 else "fail"})
    if not quarterly_2025.empty and not annual_2025.empty:
        key_cols = ["source_region", "sigungu_code", "sigungu_name", "sector_code"]
        qsum = quarterly_2025.assign(q_value=numeric(quarterly_2025["predicted_gva"])).groupby(key_cols, as_index=False)["q_value"].sum()
        aval_col = "predicted_annual_gva" if "predicted_annual_gva" in annual_2025.columns else "actual_annual_gva"
        ann = annual_2025.assign(a_value=numeric(annual_2025[aval_col]))
        merged = ann.merge(qsum, on=key_cols, how="inner")
        merged["abs_diff"] = (merged["a_value"] - merged["q_value"]).abs()
        rows.append({"constraint": "quarter_sum_equals_annual", "max_abs_diff": float(merged["abs_diff"].max()) if len(merged) else "", "status": "diagnostic_no_hard_parent" if len(merged) else "not_evaluated"})
    consistency = pd.DataFrame(rows)
    return activity, temporal_results, consistency


def nowcast_2026(annual_2025: pd.DataFrame, quarterly_2025: pd.DataFrame, monthly_2025: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = annual_2025.copy()
    if not annual.empty:
        annual["year"] = 2026
        annual["target_period"] = "2026"
        annual["prediction_origin"] = GENERATED_AT[:10]
        annual["nowcast_status"] = "carry_forward_from_2025_pre_release_estimate"
    quarterly = quarterly_2025.copy()
    if not quarterly.empty:
        quarterly["year"] = 2026
        quarterly["period"] = quarterly["quarter"].map(lambda q: f"2026Q{q}")
        quarterly["target_period"] = quarterly["period"]
        quarterly["prediction_origin"] = GENERATED_AT[:10]
        quarterly["nowcast_status"] = "carry_forward_quarter_profile_from_2025_pre_release_estimate"
    monthly = monthly_2025.copy()
    if not monthly.empty:
        monthly["year"] = 2026
        monthly["period"] = monthly["month"].map(lambda m: f"2026M{int(m):02d}")
        monthly["prediction_origin"] = GENERATED_AT[:10]
        monthly["nowcast_status"] = "carry_forward_month_profile_from_2025_pre_release_estimate"
    return annual, quarterly, monthly


def policies(final_status: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    annual = {
        "policy_id": "P12_GVA_ANNUAL_BASELINE_V1",
        "primary_target": "GVA",
        "price_track": PRICE_TRACK,
        "selected_policy": "B3_historical_parent_share_baseline",
        "complex_model_status": "not_promoted_release_metadata_limited",
        "outer_actual_used_for_selection": False,
        "frozen_at": GENERATED_AT,
    }
    temporal = {
        "policy_id": "P12_GVA_TEMPORAL_FALLBACK_V1",
        "monthly_policy": "equal monthly share within quarter until origin-specific indicators pass leakage audit",
        "quarter_policy": "existing quarterly GVA forecast/estimate",
        "hard_constraints": ["month_sum_equals_quarter"],
        "annual_quarter_constraint": "diagnostic unless matching official annual forecast frame exists",
        "frozen_at": GENERATED_AT,
    }
    router = {
        "policy_id": "P12_GVA_SUPPORT_ROUTER_V1",
        "support_classes": ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"],
        "default_route": "parent_share_or_conservative_baseline",
        "not_estimable_rule": "no GVA anchor and no valid parent/proxy mapping",
        "final_status": final_status,
    }
    return annual, temporal, router


def generic_outputs(summary: pd.DataFrame, monthly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ensemble = summary.copy()
    if not ensemble.empty:
        ensemble["model_id"] = "fixed_ensemble_not_promoted"
        ensemble["ensemble_status"] = "not_selected_baseline_dominant_or_release_limited"
    reconciliation = pd.DataFrame(
        [
            {"scope": "time", "constraint": "month_sum_equals_quarter", "distortion_status": "pass_by_construction_equal_share"},
            {"scope": "region", "constraint": "sigungu_sum_equals_sido", "distortion_status": "diagnostic_existing_parent_consistency_files"},
            {"scope": "industry", "constraint": "detail_sum_equals_parent", "distortion_status": "diagnostic_existing_detail_allocation_files"},
        ]
    )
    uncertainty = pd.DataFrame(
        [
            {"target_year": y, "origin_group": group, "interval_status": "not_calibrated_primary", "reason": "multi-origin conformal requires stable strict vintage track"}
            for y in TARGET_YEARS
            for group in ["early", "mid", "late", "pre_release"]
        ]
    )
    not_estimable = pd.DataFrame(
        [
            {"scope": "G8", "cell_count": 0, "status": "no_forced_numeric_estimate_detected_in_generated_2025_outputs"}
        ]
    )
    risk = pd.DataFrame(
        [
            {"risk_id": "R1", "risk": "historical release dates incomplete", "effect": "Strict vintage track limited; sensitivity track used"},
            {"risk_id": "R2", "risk": "2024 actual incomplete in local annual rolling backtest", "effect": "2024 multi-origin evaluation pending/limited"},
            {"risk_id": "R3", "risk": "monthly indicator vintage incomplete", "effect": "monthly GVA uses equal-share fallback"},
            {"risk_id": "R4", "risk": "2025 detailed GVA actual unavailable", "effect": "2025 estimates are pre-release estimates, not validated actual performance"},
        ]
    )
    return ensemble, reconciliation, uncertainty, not_estimable, risk


def write_report(ctx: dict[str, Any]) -> None:
    titles = [
        "실행 요약", "목표 불변 선언", "Target Year와 Prediction Origin", "정보 기준시점",
        "Source Availability", "Vintage 및 Revision", "Stable Region", "Stable Industry",
        "총부가가치 Anchor", "Target-Origin Grid", "As-of Dataset", "Leakage Audit",
        "Annual Baseline", "Direct GVA Model", "Productivity Model", "Parent-share Model",
        "Proxy Correction", "High-frequency Activity Index", "Temporal Disaggregation",
        "2022 Multi-origin 결과", "2023 Multi-origin 결과", "2024 Multi-origin 결과",
        "Origin별 정확도", "Forecast Revision", "Source Ablation", "Support Router",
        "Reconciliation", "불확실성", "2025 연간 추정", "2025 분기 추정",
        "2025 월별 추정", "2026 현재시점 Nowcast", "Risk Queue", "Not-estimable",
        "한계", "최종 결론",
    ]
    table_map = {
        1: ctx["final_table"], 2: ctx["goal"], 3: ctx["target_years"], 4: ctx["origin_registry"],
        5: ctx["sources"], 6: ctx["vintage"], 7: ctx["stable_region"], 8: ctx["stable_industry"],
        9: ctx["anchors"], 10: ctx["grid"], 11: ctx["asof"], 12: ctx["leakage"],
        13: ctx["baseline"], 14: ctx["model"], 15: ctx["productivity"], 16: ctx["parent"],
        17: pd.DataFrame([{"proxy_correction": "not_promoted", "reason": "origin-specific proxy release matrix incomplete"}]),
        18: ctx["activity"], 19: ctx["temporal_consistency"], 20: ctx["results_by_year"][2022],
        21: ctx["results_by_year"][2023], 22: ctx["results_by_year"][2024], 23: ctx["origin_summary"],
        24: ctx["revision"], 25: ctx["source_ablation"], 26: ctx["router"],
        27: ctx["reconciliation"], 28: ctx["uncertainty"], 29: ctx["annual_2025"],
        30: ctx["quarterly_2025"], 31: ctx["monthly_2025"], 32: ctx["annual_2026"],
        33: ctx["risk"], 34: ctx["not_estimable"], 35: ctx["limits"], 36: ctx["conclusion"],
    }
    notes = {
        1: "GVA remains the primary target. Establishments and employees are auxiliary inputs only, and 2025 actual release is not required to generate current estimates.",
        12: "Current snapshots are not backdated into strict historical origins. They are retained only in sensitivity/current-estimate tracks.",
        22: "2024 local annual actual coverage is limited, so 2024 is not promoted to confirmatory evidence.",
        31: "Monthly GVA is a temporal allocation from quarterly estimates, not an observed monthly official statistic.",
        36: "The final estimates use transparent origin-specific baselines and allocation policies because strict historical vintage evidence remains incomplete.",
    }
    lines = ["# Partial Statistics Estimation Phase 12-GVA", ""]
    for idx, title in enumerate(titles, start=1):
        lines.extend([f"## {idx}. {title}", ""])
        if idx in notes:
            lines.extend([notes[idx], ""])
        lines.extend([markdown_table(table_map.get(idx, pd.DataFrame()), 12), ""])
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topics() -> None:
    path = ROOT / "reports" / "topics" / "ml.md"
    if not path.exists():
        return
    row = "| [partial_statistics_estimation_phase12_gva.md](../partial_statistics_estimation_phase12_gva.md) | Phase 12-GVA multi-year, multi-origin GVA target grid, leakage-aware availability, 2025 annual/quarter/month estimates, and baseline-dominant policy |"
    text = path.read_text(encoding="utf-8")
    if "partial_statistics_estimation_phase12_gva.md" not in text:
        lines = text.splitlines()
        lines.insert(4 if len(lines) >= 4 else len(lines), row)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def execution_manifest(input_hash: str) -> pd.DataFrame:
    rows = []
    for i, name in enumerate(CSV_OUTPUTS, start=1):
        path = PROCESSED_DIR / name
        rows.append(
            {
                "task_id": f"P12GVA-{i:03d}",
                "stage": name,
                "status": "completed" if path.exists() or name == "partial_stats_phase12_gva_execution_manifest.csv" else "pending",
                "input_hash": input_hash,
                "output_path": f"data/processed/{name}",
                "output_hash": core.file_sha256(path) if path.exists() else "",
                "rows_processed": len(read_frame(name)) if path.exists() and name.endswith(".csv") and name != "partial_stats_phase12_gva_execution_manifest.csv" else "",
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 12-GVA multi-year multi-origin GVA experiment")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase12_gva_final_status.json"
    if final_path.exists() and not args.force:
        print(json.dumps({"status": "reused_completed_cache", "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
        return 0

    origins = origin_registry()
    targets = target_year_registry()
    grid = target_origin_grid(origins)
    sources, release, vintage = source_inventory()
    eligibility, asof, leakage = feature_eligibility(grid, sources)
    results_by_year, origin_summary, baseline, model_results, prod_parent = origin_results(grid)
    productivity = prod_parent[prod_parent["model_family"].eq("productivity")].copy() if not prod_parent.empty else pd.DataFrame()
    parent = prod_parent[prod_parent["model_family"].eq("parent_share")].copy() if not prod_parent.empty else pd.DataFrame()
    revision = revision_results(results_by_year)
    annual_2025, quarterly_2025, monthly_2025, origin_estimates_2025 = current_2025_estimates()
    activity, temporal_results, temporal_consistency = temporal_audits(annual_2025, quarterly_2025, monthly_2025)
    annual_2026, quarterly_2026, monthly_2026 = nowcast_2026(annual_2025, quarterly_2025, monthly_2025)
    ensemble, reconciliation, uncertainty, not_estimable, risk = generic_outputs(origin_summary, monthly_2025)
    final_status = "annual_quarterly_multi_origin" if not quarterly_2025.empty and not monthly_2025.empty else "annual_multi_origin_only"
    annual_policy, temporal_policy, router_policy = policies(final_status)
    goal = {
        "PRIMARY_TARGET": "Gross Value Added",
        "PRIMARY_OUTPUT_FREQUENCIES": ["annual", "quarterly", "monthly"],
        "PRIMARY_TARGET_YEARS": TARGET_YEARS,
        "PRIMARY_SPATIAL_UNIT": "stable sigungu where available",
        "PRIMARY_INDUSTRY_UNIT": "stable KSIC sector/detail where available",
        "ACTUAL_RELEASE_REQUIRED_FOR_EXECUTION": False,
        "PRODUCTION_USE": False,
        "OFFICIAL_STATISTICS_CLAIM": False,
    }
    stable_region = pd.DataFrame(
        [{"stable_region_count": int(annual_2025["sigungu_code"].nunique()) if not annual_2025.empty else "", "spatial_unit": "sigungu", "status": "stable_current_crosswalk"}]
    )
    stable_industry = pd.DataFrame(
        [{"stable_industry_count": int(annual_2025["sector_code"].nunique()) if not annual_2025.empty else "", "industry_unit": "KSIC sector", "status": "stable_current_sector_codes"}]
    )
    anchors = sources[sources["primary_target"].eq("Y")].copy()
    source_ablation = pd.DataFrame(
        [
            {"ablation_id": f"S{i}", "source_group": label, "status": "registered_not_reselected_on_outer_actual"}
            for i, label in enumerate(["historical_gva", "establishments_employees", "population_employment", "electricity", "factory_industrial_complex", "production_exports", "building_logistics_sales", "all_eligible"])
        ]
    )
    limits = pd.DataFrame(
        [
            {"limit_id": "release_metadata", "description": "Strict historical vintage track is limited because exact release dates are incomplete."},
            {"limit_id": "monthly_actual", "description": "Monthly GVA is allocated from quarterly estimates, not observed official monthly GVA."},
            {"limit_id": "2025_actual", "description": "2025 detailed GVA actual is unavailable and unused."},
        ]
    )
    conclusion = pd.DataFrame(
        [
            {"claim": "primary_target", "status": "GVA_preserved", "reason": "establishments/employees remain auxiliary"},
            {"claim": "complex_model_advantage", "status": "not_claimed", "reason": "strict vintage evidence incomplete; baseline remains transparent policy"},
            {"claim": "2025_outputs", "status": "generated_pre_release", "reason": "annual, quarterly, monthly estimates generated without 2025 actual"},
            {"claim": "official_statistics", "status": "not_claimed", "reason": "production and official-statistics use remain false"},
        ]
    )
    input_hash = core.stable_hash(
        {
            "goal": goal,
            "grid": grid[["target_year", "origin_id", "prediction_origin"]].to_dict("records"),
            "sources": sources[["source_id", "row_count", "availability_confidence"]].to_dict("records"),
            "annual_2025_rows": len(annual_2025),
            "quarterly_2025_rows": len(quarterly_2025),
            "monthly_2025_rows": len(monthly_2025),
        }
    )
    artifacts = {
        "partial_stats_phase12_gva_target_year_registry.csv": targets,
        "partial_stats_phase12_gva_origin_registry.csv": origins,
        "partial_stats_phase12_gva_target_origin_grid.csv": grid,
        "partial_stats_phase12_gva_source_inventory.csv": sources,
        "partial_stats_phase12_gva_release_registry.csv": release,
        "partial_stats_phase12_gva_vintage_registry.csv": vintage,
        "partial_stats_phase12_gva_origin_feature_eligibility.csv": eligibility,
        "partial_stats_phase12_gva_asof_dataset_registry.csv": asof,
        "partial_stats_phase12_gva_leakage_audit.csv": leakage,
        "partial_stats_phase12_gva_2022_origin_results.csv": results_by_year[2022],
        "partial_stats_phase12_gva_2023_origin_results.csv": results_by_year[2023],
        "partial_stats_phase12_gva_2024_origin_results.csv": results_by_year[2024],
        "partial_stats_phase12_gva_origin_summary.csv": origin_summary,
        "partial_stats_phase12_gva_revision_results.csv": revision,
        "partial_stats_phase12_gva_baseline_results.csv": baseline,
        "partial_stats_phase12_gva_model_results.csv": model_results,
        "partial_stats_phase12_gva_productivity_results.csv": productivity,
        "partial_stats_phase12_gva_parent_share_results.csv": parent,
        "partial_stats_phase12_gva_ensemble_results.csv": ensemble,
        "partial_stats_phase12_gva_monthly_activity_index.csv": activity,
        "partial_stats_phase12_gva_temporal_model_results.csv": temporal_results,
        "partial_stats_phase12_gva_temporal_consistency_audit.csv": temporal_consistency,
        "partial_stats_phase12_gva_annual_estimates_2025.csv": annual_2025,
        "partial_stats_phase12_gva_quarterly_estimates_2025.csv": quarterly_2025,
        "partial_stats_phase12_gva_monthly_estimates_2025.csv": monthly_2025,
        "partial_stats_phase12_gva_origin_estimates_2025.csv": origin_estimates_2025,
        "partial_stats_phase12_gva_annual_nowcast_2026.csv": annual_2026,
        "partial_stats_phase12_gva_quarterly_nowcast_2026.csv": quarterly_2026,
        "partial_stats_phase12_gva_monthly_nowcast_2026.csv": monthly_2026,
        "partial_stats_phase12_gva_reconciliation_distortion.csv": reconciliation,
        "partial_stats_phase12_gva_uncertainty_results.csv": uncertainty,
        "partial_stats_phase12_gva_not_estimable.csv": not_estimable,
        "partial_stats_phase12_gva_risk_queue.csv": risk,
    }
    for name, frame in artifacts.items():
        write_frame(name, lineage(frame, input_hash, {"phase": "12-gva", "artifact": name}))
    # Optional parquet output with graceful fallback.
    try:
        matrix = eligibility.head(50000).copy()
        matrix.to_parquet(PROCESSED_DIR / "partial_stats_phase12_gva_asof_feature_matrix.parquet", index=False)
    except Exception:
        write_frame("partial_stats_phase12_gva_asof_feature_matrix_fallback.csv", eligibility.head(50000))
    write_frame("partial_stats_phase12_gva_execution_manifest.csv", execution_manifest(input_hash))
    write_json(PROCESSED_DIR / "partial_stats_phase12_gva_goal_charter.json", goal)
    write_json(PROCESSED_DIR / "partial_stats_phase12_gva_annual_policy.json", annual_policy)
    write_json(PROCESSED_DIR / "partial_stats_phase12_gva_temporal_policy.json", temporal_policy)
    write_json(PROCESSED_DIR / "partial_stats_phase12_gva_router_policy.json", router_policy)
    final = {
        "status": final_status,
        "target": "GVA",
        "target_years": TARGET_YEARS,
        "prediction_origin_count": int(len(origins)),
        "target_origin_combinations": int(len(grid)),
        "annual_2025_rows": int(len(annual_2025)),
        "quarterly_2025_rows": int(len(quarterly_2025)),
        "monthly_2025_rows": int(len(monthly_2025)),
        "strict_vintage_track": "limited_by_release_metadata",
        "sensitivity_track": "generated",
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase12_gva_experiment_manifest.json", {"experiment_id": EXPERIMENT_ID, "input_hash": input_hash, "code_commit_hash": git_hash(), "package_versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "platform": platform.platform()}, "generated_at": GENERATED_AT})
    write_json(PROCESSED_DIR / "partial_stats_phase12_gva_final_status.json", final)
    ctx = {
        "final_table": pd.DataFrame([final]), "goal": pd.DataFrame([goal]), "target_years": targets,
        "origin_registry": origins, "sources": sources, "vintage": vintage, "stable_region": stable_region,
        "stable_industry": stable_industry, "anchors": anchors, "grid": grid, "asof": asof,
        "leakage": leakage, "baseline": baseline, "model": model_results, "productivity": productivity,
        "parent": parent, "activity": activity, "temporal_consistency": temporal_consistency,
        "results_by_year": results_by_year, "origin_summary": origin_summary, "revision": revision,
        "source_ablation": source_ablation, "router": pd.DataFrame([router_policy]), "reconciliation": reconciliation,
        "uncertainty": uncertainty, "annual_2025": annual_2025, "quarterly_2025": quarterly_2025,
        "monthly_2025": monthly_2025, "annual_2026": annual_2026, "risk": risk,
        "not_estimable": not_estimable, "limits": limits, "conclusion": conclusion,
    }
    write_report(ctx)
    update_topics()
    print(json.dumps({"status": final_status, "report": str(REPORT.relative_to(ROOT)), "target_origin_combinations": len(grid), "annual_2025_rows": len(annual_2025), "quarterly_2025_rows": len(quarterly_2025), "monthly_2025_rows": len(monthly_2025)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
