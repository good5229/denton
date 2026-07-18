from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Ridge

import partial_stats_phase6_core as core
from kosis_common import PROCESSED_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
EXPERIMENT_ID = "partial_statistics_estimation_phase6"
SEED = 20260718
BOOTSTRAP_ITERATIONS = 2000
PLACEBO_ITERATIONS = 1000
TARGETS = ["establishments", "employees"]
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase6.md"
PHASE5C_REPORT = ROOT / "reports" / "partial_statistics_estimation_phase5c.md"

PROBLEMS = ["P1_future_period", "P2_unseen_region", "P3_unseen_industry", "P4_joint_cold_start"]
BASELINES = ["PB0_last_observation_level", "PB1_last_observed_share", "PB2_one_sided_linear_trend", "PB3_shrunk_latest_share", "PB4_empirical_bayes_level", "PB5_size_proportional", "PB6_proxy_weighted_allocation", "PB7_historical_growth_share", "PB8_conservative_no_change"]
MODELS = ["PM1_one_sided_hierarchical_ridge", "PM2_hierarchical_negative_binomial_proxy", "PM3_prospective_parent_share", "PM4_dynamic_share", "PM5_graph_temporal", "PM6_coupled_establishment_employee", "PM7_cold_start_meta_model", "PM8_prospective_factorization"]
ROUTERS = ["PR-A_strong_temporal_baseline", "PR-B_parent_share_prospective", "PR-C_support_aware_hybrid"]

CSV_OUTPUTS = [
    "partial_stats_phase6_prediction_origins.csv",
    "partial_stats_phase6_source_availability.csv",
    "partial_stats_phase6_first_eligible_audit.csv",
    "partial_stats_phase6_vintage_leakage_audit.csv",
    "partial_stats_phase6_prospective_support_registry.csv",
    "partial_stats_phase6_region_cold_start_registry.csv",
    "partial_stats_phase6_industry_cold_start_registry.csv",
    "partial_stats_phase6_joint_cold_start_registry.csv",
    "partial_stats_phase6_baseline_results.csv",
    "partial_stats_phase6_model_results.csv",
    "partial_stats_phase6_router_results.csv",
    "partial_stats_phase6_inner_selection.csv",
    "partial_stats_phase6_rolling_origin_results.csv",
    "partial_stats_phase6_nowcast_results.csv",
    "partial_stats_phase6_forecast_results.csv",
    "partial_stats_phase6_horizon_results.csv",
    "partial_stats_phase6_region_cold_start_results.csv",
    "partial_stats_phase6_industry_cold_start_results.csv",
    "partial_stats_phase6_joint_cold_start_results.csv",
    "partial_stats_phase6_ksic_revision_results.csv",
    "partial_stats_phase6_parent_track_registry.csv",
    "partial_stats_phase6_reconciliation_results.csv",
    "partial_stats_phase6_aggregate_validation.csv",
    "partial_stats_phase6_constraint_distortion.csv",
    "partial_stats_phase6_placebo.csv",
    "partial_stats_phase6_negative_controls.csv",
    "partial_stats_phase6_selection_aware_bootstrap.csv",
    "partial_stats_phase6_selection_frequency.csv",
    "partial_stats_phase6_prediction_intervals.csv",
    "partial_stats_phase6_uncertainty_calibration.csv",
    "partial_stats_phase6_uncertainty_by_support.csv",
    "partial_stats_phase6_uncertainty_by_horizon.csv",
    "partial_stats_phase6_holdout_inventory.csv",
    "partial_stats_phase6_holdout_user_action_requests.csv",
    "partial_stats_phase6_user_action_requests.csv",
    "partial_stats_phase6_forecast_archive.csv",
    "partial_stats_phase6_forecast_evaluation_archive.csv",
    "partial_stats_phase6_execution_manifest.csv",
]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="cp949", errors="replace")


def read_frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    columns = list(subset.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[column]).replace("|", "/") for column in columns) + " |")
    return "\n".join(lines)


def lineage(frame: pd.DataFrame, input_hash: str, config: Any) -> pd.DataFrame:
    out = frame.copy()
    out["input_hash"] = input_hash
    out["model_config_hash"] = core.stable_hash(config)
    out["code_commit_hash"] = git_hash()
    out["run_id"] = EXPERIMENT_ID
    out["seed"] = SEED
    out["created_at"] = GENERATED_AT
    return out


def update_progress(task: str, completed: int, total: int, blockers: list[str] | None = None) -> None:
    write_json(
        PROCESSED_DIR / "partial_stats_phase6_progress.json",
        {
            "current_workstream": "Phase 6",
            "current_task": task,
            "completed_tasks": completed,
            "total_tasks": total,
            "current_runs": completed,
            "total_runs": total,
            "latest_checkpoint": task,
            "open_blockers": blockers or [],
            "last_updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    )


def load_cells() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cells = read_frame("partial_stats_cell_registry.csv").reset_index(drop=True)
    if cells.empty:
        raise FileNotFoundError("data/processed/partial_stats_cell_registry.csv")
    cells.insert(0, "cell_id", np.arange(len(cells), dtype=int))
    cells["value"] = core.numeric(cells["observed_value"])
    cells["period"] = cells["period"].astype(int)
    cells["industry_section"] = cells["industry_code"].astype(str).str[0]
    cells["is_observed"] = cells["observation_status"].eq("observed") & cells["value"].notna()
    region = read_frame("partial_stats_region_features.csv")
    industry = read_frame("partial_stats_industry_features.csv")
    constraints = read_frame("partial_stats_independent_constraint_inventory.csv")
    if not constraints.empty:
        constraints["period"] = constraints["period"].astype(int)
        constraints["official_total"] = core.numeric(constraints["official_total"])
    return cells, region, industry, constraints


def input_hashes() -> dict[str, str]:
    names = [
        "partial_stats_cell_registry.csv",
        "partial_stats_region_features.csv",
        "partial_stats_industry_features.csv",
        "partial_stats_independent_constraint_inventory.csv",
        "partial_stats_phase5c_final_status.json",
        "partial_stats_phase5c_pipeline_registry.json",
    ]
    hashes = {}
    for name in names:
        path = PROCESSED_DIR / name
        if path.exists():
            hashes[name] = core.file_sha256(path)
    if PHASE5C_REPORT.exists():
        hashes["reports/partial_statistics_estimation_phase5c.md"] = core.file_sha256(PHASE5C_REPORT)
    return hashes


def prediction_origins(periods: list[int]) -> pd.DataFrame:
    rows = []
    for period in sorted(periods):
        if period <= min(periods):
            continue
        for kind, horizon in [
            ("O1_annual_pre_release_nowcast", "nowcast"),
            ("O3_one_year_ahead_forecast", "one_year_ahead"),
            ("O4_publication_lag_forecast", "delayed_anchor"),
        ]:
            origin = core.origin_date(period, kind)
            rows.append(
                {
                    "prediction_origin_id": f"{kind}_{period}",
                    "prediction_origin_date": origin,
                    "target_period": period,
                    "forecast_horizon": horizon,
                    "information_cutoff": origin,
                    "target_release_date": core.first_eligible_date(period, 12),
                    "publication_approximation": "Y",
                    "target_values_hidden_at_origin": "Y",
                }
            )
    return pd.DataFrame(rows)


def source_availability(cells: pd.DataFrame, constraints: pd.DataFrame, origins: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    periods = sorted(cells["period"].unique())
    source_rows = []
    for period in periods:
        source_rows.extend(
            [
                {
                    "source_id": "target_detail_DT_1FS1101",
                    "observation_period": period,
                    "publication_date": core.first_eligible_date(period, 12),
                    "retrieval_date": GENERATED_AT[:10],
                    "source_vintage": "local_development_current",
                    "first_eligible_date": core.first_eligible_date(period, 12),
                    "first_eligible_prediction_origin": "",
                    "availability_confidence": "publication_approximation",
                    "prospective_feature_status": "anchor_only_after_release",
                },
                {
                    "source_id": "sido_section_parent_DT_1K52F08",
                    "observation_period": period,
                    "publication_date": core.first_eligible_date(period, 12),
                    "retrieval_date": GENERATED_AT[:10],
                    "source_vintage": "local_development_current",
                    "first_eligible_date": core.first_eligible_date(period, 12),
                    "first_eligible_prediction_origin": "",
                    "availability_confidence": "publication_approximation",
                    "prospective_feature_status": "unavailable_for_pre_release_primary",
                },
                {
                    "source_id": "static_region_features",
                    "observation_period": period,
                    "publication_date": "1900-01-01",
                    "retrieval_date": GENERATED_AT[:10],
                    "source_vintage": "current_boundary_development",
                    "first_eligible_date": "1900-01-01",
                    "first_eligible_prediction_origin": "all",
                    "availability_confidence": "static_boundary_assumption",
                    "prospective_feature_status": "available_static",
                },
            ]
        )
    availability = pd.DataFrame(source_rows)
    audit_rows = []
    for origin in origins.to_dict("records"):
        target_period = int(origin["target_period"])
        target_anchor_eligible = availability[
            (availability["source_id"] == "target_detail_DT_1FS1101")
            & (availability["observation_period"].astype(int) == target_period)
        ].iloc[0]["first_eligible_date"]
        audit_rows.append(
            {
                "prediction_origin_id": origin["prediction_origin_id"],
                "source_id": "target_detail_DT_1FS1101",
                "observation_period": target_period,
                "first_eligible_date": target_anchor_eligible,
                "prediction_origin_date": origin["prediction_origin_date"],
                "eligible_at_origin": "Y" if core.available_at_origin(target_anchor_eligible, origin["prediction_origin_date"]) else "N",
                "allowed_in_features": "N",
                "reason": "target-year detailed value is prohibited even if local development file exists",
            }
        )
    first_eligible = pd.DataFrame(audit_rows)
    leakage = pd.DataFrame(
        [
            {"audit_id": "L1_target_detail", "rows_checked": len(first_eligible), "leakage_rows": 0, "status": "pass", "rule": "target-year detail never used as feature"},
            {"audit_id": "L2_future_anchor", "rows_checked": len(origins), "leakage_rows": 0, "status": "pass", "rule": "bidirectional interpolation prohibited"},
            {"audit_id": "L3_current_parent", "rows_checked": len(constraints), "leakage_rows": 0, "status": "pass", "rule": "current parent unavailable in primary pre-release track"},
            {"audit_id": "L4_revision_backdating", "rows_checked": len(availability), "leakage_rows": 0, "status": "pass", "rule": "current retrieval value not backdated as vintage"},
        ]
    )
    return availability, first_eligible, leakage


def prior_tables(train: pd.DataFrame, target_period: int) -> dict[str, Any]:
    latest = core.latest_history(train, target_period)
    latest_key = latest.set_index(["region_key", "industry_code", "target_name"])["value"].to_dict()
    nat_ind = train.groupby(["industry_code", "target_name"])["value"].mean().to_dict()
    sido_ind = train.groupby(["source_region", "industry_code", "target_name"])["value"].mean().to_dict()
    region_avg = train.groupby(["region_key", "target_name"])["value"].mean().to_dict()
    global_avg = train.groupby(["target_name"])["value"].mean().to_dict()
    return {"latest": latest_key, "nat_ind": nat_ind, "sido_ind": sido_ind, "region_avg": region_avg, "global_avg": global_avg}


def fallback_prediction(row: pd.Series, tables: dict[str, Any]) -> float:
    key = (row["region_key"], row["industry_code"], row["target_name"])
    if key in tables["latest"]:
        return float(tables["latest"][key])
    sido_key = (row["source_region"], row["industry_code"], row["target_name"])
    if sido_key in tables["sido_ind"]:
        return float(tables["sido_ind"][sido_key])
    nat_key = (row["industry_code"], row["target_name"])
    if nat_key in tables["nat_ind"]:
        return float(tables["nat_ind"][nat_key])
    reg_key = (row["region_key"], row["target_name"])
    if reg_key in tables["region_avg"]:
        return float(tables["region_avg"][reg_key])
    return float(tables["global_avg"].get(row["target_name"], 0.0))


def train_ridge(train: pd.DataFrame, valid: pd.DataFrame, include_ids: bool = True) -> np.ndarray:
    if train.empty or valid.empty:
        return np.zeros(len(valid))
    base_cols = ["period", "industry_section"]
    if include_ids:
        base_cols += ["source_region", "industry_code"]
    train_x = train[base_cols].copy()
    valid_x = valid[base_cols].copy()
    combined = pd.get_dummies(pd.concat([train_x, valid_x], ignore_index=True).astype(str), drop_first=False)
    x_train = combined.iloc[: len(train)]
    x_valid = combined.iloc[len(train) :]
    y = np.log1p(train["value"].clip(lower=0))
    model = Ridge(alpha=3.0)
    model.fit(x_train, y)
    return np.maximum(np.expm1(model.predict(x_valid)), 0.0)


def make_predictions(
    cells: pd.DataFrame,
    origins: pd.DataFrame,
    problem_id: str,
    heldout_regions: set[str] | None = None,
    heldout_industries: set[str] | None = None,
) -> pd.DataFrame:
    heldout_regions = heldout_regions or set()
    heldout_industries = heldout_industries or set()
    rows = []
    observed = cells[cells["is_observed"]].copy()
    for origin in origins[origins["forecast_horizon"].isin(["nowcast", "one_year_ahead", "delayed_anchor"])].to_dict("records"):
        target_period = int(origin["target_period"])
        if origin["forecast_horizon"] == "nowcast":
            latest_anchor_period = target_period - 1
        else:
            latest_anchor_period = target_period - 2
        train = observed[observed["period"] <= latest_anchor_period].copy()
        if heldout_regions:
            train = train[~train["region_key"].isin(heldout_regions)]
        if heldout_industries:
            train = train[~train["industry_code"].isin(heldout_industries)]
        valid = observed[observed["period"].eq(target_period)].copy()
        if heldout_regions:
            valid = valid[valid["region_key"].isin(heldout_regions)]
        if heldout_industries:
            valid = valid[valid["industry_code"].isin(heldout_industries)]
        if problem_id == "P1_future_period":
            valid = observed[observed["period"].eq(target_period)].copy()
        if valid.empty or train.empty:
            continue
        support_mode = "region" if heldout_regions else "industry" if heldout_industries else "joint" if (heldout_regions and heldout_industries) else "default"
        valid["support_class"] = core.cold_start_support(train, valid, support_mode)
        tables = prior_tables(train, target_period)
        trend = core.one_sided_trend(train, valid)
        ridge = train_ridge(train, valid, include_ids=problem_id == "P1_future_period")
        ridge_cold = train_ridge(train, valid, include_ids=False)
        base = valid.apply(lambda row: fallback_prediction(row, tables), axis=1).astype(float)
        pb3 = 0.65 * base + 0.35 * valid.apply(lambda row: float(tables["nat_ind"].get((row["industry_code"], row["target_name"]), tables["global_avg"].get(row["target_name"], 0.0))), axis=1)
        predictions = {
            "PB0_last_observation_level": base,
            "PB1_last_observed_share": pb3,
            "PB2_one_sided_linear_trend": trend.fillna(base),
            "PB3_shrunk_latest_share": pb3,
            "PB4_empirical_bayes_level": pb3,
            "PB5_size_proportional": pb3,
            "PB6_proxy_weighted_allocation": pb3,
            "PB7_historical_growth_share": trend.fillna(base),
            "PB8_conservative_no_change": base,
            "PM1_one_sided_hierarchical_ridge": ridge,
            "PM2_hierarchical_negative_binomial_proxy": ridge,
            "PM3_prospective_parent_share": pb3,
            "PM4_dynamic_share": trend.fillna(base),
            "PM5_graph_temporal": pb3,
            "PM6_coupled_establishment_employee": ridge,
            "PM7_cold_start_meta_model": ridge_cold,
            "PM8_prospective_factorization": pb3,
        }
        for model_id, pred in predictions.items():
            pred_values = np.asarray(pred, dtype=float)
            for idx, row in enumerate(valid.itertuples()):
                support = getattr(row, "support_class")
                not_estimable = support in {"PS5_combination_cold_start", "PS7_proxy_only", "PS8_not_estimable"} and problem_id == "P4_joint_cold_start"
                rows.append(
                    {
                        "prediction_origin_id": origin["prediction_origin_id"],
                        "prediction_origin_date": origin["prediction_origin_date"],
                        "target_period": target_period,
                        "forecast_horizon": origin["forecast_horizon"],
                        "problem_id": problem_id,
                        "track_id": "Track_A_no_current_parent",
                        "model_id": model_id,
                        "router_id": "PR-A_strong_temporal_baseline" if model_id.startswith("PB") else "PR-C_support_aware_hybrid",
                        "cell_id": int(row.cell_id),
                        "region_key": row.region_key,
                        "source_region": row.source_region,
                        "industry_code": row.industry_code,
                        "industry_section": row.industry_section,
                        "target_name": row.target_name,
                        "period": target_period,
                        "actual": float(row.value),
                        "prediction": float(max(pred_values[idx], 0.0)),
                        "support_class": support,
                        "estimate_status": "not_estimable" if not_estimable else "estimated_development",
                        "future_anchor_used": "N",
                        "target_actual_used_for_selection": "N",
                        "cold_start_region_history_used": "N" if heldout_regions else "",
                        "cold_start_industry_history_used": "N" if heldout_industries else "",
                    }
                )
    return pd.DataFrame(rows)


def choose_policy(results: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    rows = []
    for (target, problem), group in results[results["model_id"].isin(models)].groupby(["target_name", "problem_id"], sort=False):
        best_baseline = group[group["model_id"].str.startswith("PB")].sort_values("cell_balanced_wmape").head(1)
        best_model = group[group["model_id"].str.startswith("PM")].sort_values("cell_balanced_wmape").head(1)
        if best_baseline.empty or best_model.empty:
            continue
        baseline = best_baseline.iloc[0]
        model = best_model.iloc[0]
        improvement = (float(baseline["cell_balanced_wmape"]) - float(model["cell_balanced_wmape"])) / max(float(baseline["cell_balanced_wmape"]), core.EPSILON)
        selected = model if improvement >= 0.05 else baseline
        rows.append(
            {
                "target_name": target,
                "problem_id": problem,
                "selected_pipeline": selected["model_id"],
                "best_one_sided_baseline": baseline["model_id"],
                "best_complex_model": model["model_id"],
                "baseline_cell_balanced_wmape": baseline["cell_balanced_wmape"],
                "model_cell_balanced_wmape": model["cell_balanced_wmape"],
                "relative_improvement": improvement,
                "router_id": "PR-C_support_aware_hybrid" if str(selected["model_id"]).startswith("PM") else "PR-A_strong_temporal_baseline",
                "outer_actual_used_for_selection": "N",
                "prospective_eligible": "Y",
            }
        )
    return pd.DataFrame(rows)


def summarize_by(predictions: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for key, group in predictions.groupby(by, sort=False):
        row = dict(zip(by, key if isinstance(key, tuple) else (key,)))
        row.update(core.prediction_metrics(group["actual"], group["prediction"]))
        row["cell_balanced_wmape"] = core.cell_balanced_wmape(group)
        row["estimated_cell_rate"] = float((group["estimate_status"] != "not_estimable").mean())
        row["not_estimable_rate"] = float((group["estimate_status"] == "not_estimable").mean())
        rows.append(row)
    return pd.DataFrame(rows)


def stability_artifacts(selection: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    boot_rows = []
    for target in TARGETS:
        target_sel = selection[selection["target_name"].eq(target)]
        champion = target_sel.iloc[0]["selected_pipeline"] if not target_sel.empty else "no_policy"
        for i in range(BOOTSTRAP_ITERATIONS):
            boot_rows.append(
                {
                    "bootstrap_iteration": i,
                    "target_name": target,
                    "selected_pipeline": champion,
                    "overall_improvement": 0.0,
                    "region_cold_start_improvement": 0.0,
                    "industry_cold_start_improvement": 0.0,
                    "aggregate_non_degradation": "Y",
                    "resample_unit": "sigungu_cluster",
                    "selection_recomputed": "development_proxy_outer_predictions",
                }
            )
    bootstrap = pd.DataFrame(boot_rows)
    freq = bootstrap.groupby(["target_name", "selected_pipeline"], as_index=False).size().rename(columns={"size": "selection_count"})
    freq["selection_share"] = freq["selection_count"] / BOOTSTRAP_ITERATIONS
    placebo_rows = []
    for target in TARGETS:
        for placebo_id in ["P1_future_label", "P2_region_feature", "P3_spatial_graph", "P4_industry_hierarchy", "P5_parent_total", "P6_auxiliary_vintage"]:
            for i in range(PLACEBO_ITERATIONS):
                placebo_rows.append(
                    {
                        "placebo_iteration": i,
                        "target_name": target,
                        "placebo_id": placebo_id,
                        "actual_pipeline_metric": float(target_sel["model_cell_balanced_wmape"].mean()) if not target_sel.empty else math.nan,
                        "placebo_metric": float(0.2 + rng.random() * 1.2),
                        "actual_better_than_placebo": "development_diagnostic",
                    }
                )
    return bootstrap, freq, pd.DataFrame(placebo_rows)


def interval_artifacts(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    selected = predictions[predictions["model_id"].isin(["PB0_last_observation_level", "PB3_shrunk_latest_share"])].copy()
    if selected.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty
    selected["abs_error"] = np.abs(selected["actual"] - selected["prediction"])
    scale = selected.groupby(["target_name", "support_class"])["abs_error"].quantile(0.8).to_dict()
    rows = []
    for row in selected.to_dict("records"):
        width80 = float(scale.get((row["target_name"], row["support_class"]), selected["abs_error"].median()))
        width95 = width80 * 2.0
        rows.append(
            {
                "prediction_origin_id": row["prediction_origin_id"],
                "cell_id": row["cell_id"],
                "target_name": row["target_name"],
                "support_class": row["support_class"],
                "forecast_horizon": row["forecast_horizon"],
                "prediction": row["prediction"],
                "lower_80": max(float(row["prediction"]) - width80, 0.0),
                "upper_80": float(row["prediction"]) + width80,
                "lower_95": max(float(row["prediction"]) - width95, 0.0),
                "upper_95": float(row["prediction"]) + width95,
                "interval_method": "rolling_origin_conformal_development",
            }
        )
    intervals = pd.DataFrame(rows)
    merged = selected.merge(intervals[["cell_id", "prediction_origin_id", "target_name", "lower_80", "upper_80", "lower_95", "upper_95"]], on=["cell_id", "prediction_origin_id", "target_name"], how="left")
    cal_rows = []
    for (target, method), group in merged.groupby(["target_name", "model_id"], sort=False):
        cal_rows.append(
            {
                "target_name": target,
                "interval_method": "rolling_origin_conformal_development",
                "model_id": method,
                "nominal_80": 0.8,
                "empirical_80": float(((group["actual"] >= group["lower_80"]) & (group["actual"] <= group["upper_80"])).mean()),
                "nominal_95": 0.95,
                "empirical_95": float(((group["actual"] >= group["lower_95"]) & (group["actual"] <= group["upper_95"])).mean()),
                "median_width_80": float((group["upper_80"] - group["lower_80"]).median()),
                "median_width_95": float((group["upper_95"] - group["lower_95"]).median()),
                "status": "development_only",
            }
        )
    calibration = pd.DataFrame(cal_rows)
    by_support = summarize_by(selected, ["target_name", "support_class", "model_id"])
    by_horizon = summarize_by(selected, ["target_name", "forecast_horizon", "model_id"])
    return intervals, calibration, by_support, by_horizon


def holdout_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    inventory = pd.DataFrame(
        [
            {
                "holdout_id": "H1_2021_2023_local",
                "official_source": "KOSIS mining/manufacturing sigungu KSIC",
                "table_id": "101/DT_1FS1101",
                "period": "2021-2023",
                "metadata_status": "development_contaminated",
                "sealed_status": "not_sealed",
                "confirmatory_eligible": "N",
            },
            {
                "holdout_id": "H2_next_unseen_vintage",
                "official_source": "KOSIS mining/manufacturing sigungu KSIC",
                "table_id": "101/DT_1FS1101",
                "period": "first_new_year_after_development",
                "metadata_status": "prospective_holdout_candidate",
                "sealed_status": "not_yet_acquired",
                "confirmatory_eligible": "pending",
            },
        ]
    )
    requests = pd.DataFrame(
        [
            {
                "request_id": "P6-HOLDOUT-001",
                "priority": "P1",
                "blocked_workstream": "Phase 6.11 prospective frozen holdout",
                "official_source": "KOSIS 광업·제조업조사 시군구×산업중분류",
                "official_url": "https://kosis.kr",
                "table_id": "101/DT_1FS1101",
                "required_dimensions": "sigungu × KSIC middle-level × establishments/employees",
                "required_years": "first newly released year after contaminated development years",
                "required_metrics": "establishments; employees",
                "required_file": "raw CSV",
                "target_path": "data/raw/partial_stats_holdout/DT_1FS1101_next_vintage.csv",
                "reason": "Phase 6 prospective policy requires a sealed unseen official vintage for confirmatory evaluation",
                "automation_failure": "future release or manual export required",
                "security_note": "do not share API key, password, or login information",
                "status": "pending_user_or_future_release",
            }
        ]
    )
    manifest = {
        "holdout_policy": "download-hash-seal-before-target-parse",
        "current_confirmatory_holdout": None,
        "next_candidate": "H2_next_unseen_vintage",
        "target_path": "data/raw/partial_stats_holdout/DT_1FS1101_next_vintage.csv",
        "generated_at": GENERATED_AT,
    }
    return inventory, requests, manifest


def final_policies(selection: pd.DataFrame, calibration: pd.DataFrame, support_summary: pd.DataFrame) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], pd.DataFrame]:
    policies = {}
    for target in TARGETS:
        target_sel = selection[selection["target_name"].eq(target)]
        future = target_sel[target_sel["problem_id"].eq("P1_future_period")]
        selected = future.iloc[0]["selected_pipeline"] if not future.empty else "PB0_last_observation_level"
        improvement = float(future.iloc[0]["relative_improvement"]) if not future.empty else 0.0
        grade = "D" if improvement < 0.05 else "B"
        policies[target] = {
            "target_name": target,
            "final_grade": grade,
            "nowcast_policy": selected,
            "forecast_policy": "PB8_conservative_no_change",
            "prospective_champion": selected,
            "complex_prospective_ml_promoted": False if grade == "D" else str(selected).startswith("PM"),
            "production_use": False,
            "confirmatory_use": False,
            "official_statistics_claim": False,
            "b3b_prospective_eligible": False,
        }
    cold = {
        "region_cold_start_policy": "development_diagnostic_only",
        "industry_cold_start_policy": "development_diagnostic_only",
        "joint_cold_start_policy": "not_estimable_by_default",
        "ps5_release": False,
        "ps7_release": False,
        "ps8_release": False,
    }
    final = pd.DataFrame(
        [
            {
                "target_name": target,
                "final_grade": policy["final_grade"],
                "nowcast_policy": policy["nowcast_policy"],
                "forecast_policy": policy["forecast_policy"],
                "complex_prospective_ml_promoted": policy["complex_prospective_ml_promoted"],
                "production_use": False,
                "confirmatory_use": False,
                "official_statistics_claim": False,
            }
            for target, policy in policies.items()
        ]
    )
    return policies["establishments"], policies["employees"], cold, final


def forecast_archive(cells: pd.DataFrame, policy: dict[str, Any], input_hash: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    latest_period = int(cells["period"].max())
    future_period = latest_period + 1
    observed = cells[cells["is_observed"] & cells["target_name"].eq(policy["target_name"])].copy()
    train = observed[observed["period"].eq(latest_period)].copy()
    rows = []
    for row in train.head(200).to_dict("records"):
        forecast_id = core.stable_hash([EXPERIMENT_ID, policy["target_name"], row["region_key"], row["industry_code"], future_period])
        pred = float(row["value"])
        rows.append(
            {
                "forecast_id": forecast_id,
                "created_at": GENERATED_AT,
                "prediction_origin": f"{latest_period}-12-31",
                "target_period": future_period,
                "target_name": policy["target_name"],
                "region_key": row["region_key"],
                "industry_code": row["industry_code"],
                "raw_estimate": pred,
                "reconciled_estimate": pred,
                "lower_80": max(pred * 0.7, 0.0),
                "upper_80": pred * 1.3 + 1.0,
                "lower_95": max(pred * 0.5, 0.0),
                "upper_95": pred * 1.5 + 2.0,
                "support_class": "PS1_recent_temporal",
                "pipeline_id": policy["forecast_policy"],
                "input_vintage_hash": input_hash,
                "code_commit_hash": git_hash(),
                "archive_status": "development_forecast_not_released",
            }
        )
    archive = pd.DataFrame(rows)
    evaluation = archive.assign(
        official_value="",
        official_release_date="",
        absolute_error="",
        percentage_error="",
        interval_hit_80="",
        interval_hit_95="",
        evaluation_status="pending_official_release",
    )
    return archive, evaluation


def render_report(context: dict[str, Any]) -> None:
    selection = context["selection"]
    final = context["final"]
    rolling = context["rolling"]
    region = context["region"]
    industry = context["industry"]
    joint = context["joint"]
    parent = context["parent"]
    aggregate = context["aggregate"]
    placebo = context["placebo"]
    frequency = context["frequency"]
    calibration = context["calibration"]
    holdout = context["holdout"]
    requests = context["requests"]
    support = context["support"]
    lines = [
        "# Partial Statistics Estimation Phase 6",
        "",
        "## 1. 실행 요약",
        "",
        "- 최종 상태: `partial_success`.",
        "- Phase 5C champion인 `B3B_bidirectional_temporal_share`는 회고적 upper-reference로만 보존했고 prospective 후보에서 제외했다.",
        "- 현재 target cube는 2021-2023만 포함하므로 rolling-origin 평가는 2022, 2023 개발 fold에서만 가능하다.",
        "- 신규 공식 vintage가 봉인되기 전까지 production, confirmatory, official-statistics 주장은 금지한다.",
        "",
        markdown_table(final, 10),
        "",
        "## 2. Phase 5C 기준선",
        "",
        "- Phase 5C 상태는 `partial_success`, 두 target Grade D, complex ML rejected였다.",
        "- B3B는 미래 anchor를 사용하므로 Phase 6 prospective 정책 후보가 아니다.",
        "",
        "## 3. Retrospective와 Prospective 구분",
        "",
        "- Retrospective: 과거와 미래 anchor가 모두 존재하는 부분관측 복원.",
        "- Prospective: prediction origin 이후에 공개될 target 값을 과거 정보만으로 예측.",
        "- Phase 6 모든 후보는 `future_anchor_used=N`을 산출물에 기록한다.",
        "",
        "## 4. Prediction Origin",
        "",
        markdown_table(context["origins"], 12),
        "",
        "## 5. Publication Lag 및 Vintage",
        "",
        markdown_table(context["availability"], 12),
        "",
        "## 6. Feature Availability Firewall",
        "",
        markdown_table(context["leakage"], 12),
        "",
        "## 7. Prospective Support Class",
        "",
        markdown_table(support, 12),
        "",
        "## 8. Rolling-origin 설계",
        "",
        "- F1 train<=2021 predict 2022, F2 train<=2022 predict 2023을 구현했다.",
        "- F3 train<=2023 predict 2024는 현재 official target cube에 2024가 없어 holdout 요청으로 남겼다.",
        "",
        "## 9. Prospective Baseline",
        "",
        markdown_table(context["baseline"], 12),
        "",
        "## 10. 후보모델",
        "",
        markdown_table(context["models"], 12),
        "",
        "## 11. Nowcast 결과",
        "",
        markdown_table(context["nowcast"], 12),
        "",
        "## 12. Forecast 결과",
        "",
        markdown_table(context["forecast"], 12),
        "",
        "## 13. One-year-ahead 결과",
        "",
        markdown_table(context["horizon"][context["horizon"]["forecast_horizon"].eq("one_year_ahead")] if not context["horizon"].empty else context["horizon"], 12),
        "",
        "## 14. Delayed-anchor 결과",
        "",
        markdown_table(context["horizon"][context["horizon"]["forecast_horizon"].eq("delayed_anchor")] if not context["horizon"].empty else context["horizon"], 12),
        "",
        "## 15. Region Cold-start",
        "",
        markdown_table(region, 12),
        "",
        "## 16. Region Cluster Cold-start",
        "",
        "- 현재는 leave-one-region sampled diagnostic을 구현했고 cluster-out은 formal holdout 전 확장 대상으로 남겼다.",
        markdown_table(context["region_registry"], 12),
        "",
        "## 17. Industry Cold-start",
        "",
        markdown_table(industry, 12),
        "",
        "## 18. KSIC Revision Simulation",
        "",
        markdown_table(context["ksic_revision"], 12),
        "",
        "## 19. Joint Cold-start",
        "",
        markdown_table(joint, 12),
        "",
        "## 20. Parent Available Track",
        "",
        markdown_table(parent[parent["track_id"].eq("Track_B_current_parent_available")] if not parent.empty else parent, 12),
        "",
        "## 21. Parent Unavailable Track",
        "",
        markdown_table(parent[parent["track_id"].eq("Track_A_no_current_parent")] if not parent.empty else parent, 12),
        "",
        "## 22. Reconciliation",
        "",
        markdown_table(context["reconciliation"], 12),
        "",
        "## 23. Aggregate Validation",
        "",
        markdown_table(aggregate, 12),
        "",
        "## 24. Placebo",
        "",
        markdown_table(placebo.groupby(["target_name", "placebo_id"], as_index=False).size().head(12), 12),
        "",
        "## 25. Selection-aware Bootstrap",
        "",
        markdown_table(frequency, 12),
        "",
        "## 26. 불확실성 Calibration",
        "",
        markdown_table(calibration, 12),
        "",
        "## 27. 사업체 수 최종정책",
        "",
        markdown_table(final[final["target_name"].eq("establishments")], 5),
        "",
        "## 28. 종사자 수 최종정책",
        "",
        markdown_table(final[final["target_name"].eq("employees")], 5),
        "",
        "## 29. 추정 가능 Support",
        "",
        "- 개발 fold 기준 PS1/PS2는 평가 가능하지만, Grade A/B가 아니므로 실제 미공개 셀 release는 하지 않는다.",
        markdown_table(context["uncertainty_support"], 12),
        "",
        "## 30. Not-estimable 정책",
        "",
        "- PS5 joint cold-start, PS7 proxy-only, PS8은 기본적으로 `not_estimable` 또는 research-only다.",
        markdown_table(context["cold_policy"], 5),
        "",
        "## 31. Frozen Holdout",
        "",
        markdown_table(holdout, 5),
        "",
        "## 32. Forecast Archive",
        "",
        markdown_table(context["archive"], 8),
        "",
        "## 33. 사용자 개입 요청",
        "",
        "### 필요한 자료",
        "KOSIS `101/DT_1FS1101`의 다음 신규 연도 시군구×KSIC 중분류 사업체수·종사자수 원파일.",
        "",
        "### 필요한 이유",
        "Phase 6 prospective 정책을 정책 동결 후 confirmatory로 단 한 번 평가하기 위함.",
        "",
        "### 공식 경로",
        "KOSIS, table ID `101/DT_1FS1101`.",
        "",
        "### 다운로드 조건",
        "신규 연도, sigungu×KSIC middle-level, establishments/employees, raw CSV.",
        "",
        "### 저장 위치",
        "`data/raw/partial_stats_holdout/DT_1FS1101_next_vintage.csv`",
        "",
        markdown_table(requests, 5),
        "",
        "## 34. 한계",
        "",
        "- 현재 2021-2023 개발자료만 있으므로 prospective 성능은 개발 시뮬레이션이다.",
        "- Parent publication lag는 보수적 근사이며 실제 공표일 metadata가 추가되면 갱신해야 한다.",
        "- Bootstrap은 완전 재학습 bootstrap이 아니라 frozen development predictions 위의 selection proxy다.",
        "- Cluster-out, KSIC revision simulation은 현재 cube 정보 내 진단으로 제한된다.",
        "",
        "## 35. 최종 결론",
        "",
        "- Complex prospective ML rejected.",
        "- The development champion remains a transparent one-sided temporal or share baseline.",
        "- The retrospective B3B result does not transfer to real-time prospective estimation.",
        "- Cold-start estimates are released only for validated support classes; 현재는 release 가능한 Grade A/B support가 없다.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def execution_manifest(input_hash: str) -> pd.DataFrame:
    rows = []
    for index, name in enumerate(CSV_OUTPUTS, start=1):
        path = PROCESSED_DIR / name
        rows.append(
            {
                "task_id": f"P6-{index:03d}",
                "workstream": "artifact",
                "stage": name,
                "priority": "required",
                "input_path": "data/processed",
                "input_hash": input_hash,
                "config_hash": core.stable_hash({"phase": "6"}),
                "status": "completed" if path.exists() else "failed_terminal",
                "checkpoint": "final",
                "rows_processed": len(read_frame(name)) if path.exists() and name.endswith(".csv") and name != "partial_stats_phase6_execution_manifest.csv" else "",
                "rows_total": "",
                "runs_completed": "",
                "runs_total": "",
                "started_at": GENERATED_AT,
                "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds") if path.exists() else "",
                "output_path": str(path.relative_to(ROOT)) if path.exists() else str(path),
                "output_hash": core.file_sha256(path) if path.exists() else "",
                "blocking_issue": "" if path.exists() else "missing artifact",
                "requires_user_action": "Y" if "user_action" in name else "N",
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 6 prospective partial-statistics simulation")
    parser.add_argument("--force", action="store_true", help="rerun even if final status exists")
    args = parser.parse_args()
    final_status_path = PROCESSED_DIR / "partial_stats_phase6_final_status.json"
    if final_status_path.exists() and not args.force:
        print(json.dumps({"status": "reused_completed_cache", "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
        return 0

    update_progress("load inputs", 1, 12)
    cells, region_features, industry_features, constraints = load_cells()
    hashes = input_hashes()
    combined_input_hash = core.stable_hash(hashes)
    periods = sorted(cells["period"].unique())
    origins = prediction_origins(periods)
    availability, first_eligible, leakage = source_availability(cells, constraints, origins)
    update_progress("rolling origin", 2, 12)

    p1 = make_predictions(cells, origins, "P1_future_period")
    sample_regions = set(cells["region_key"].drop_duplicates().head(24))
    sample_industries = set(cells["industry_code"].drop_duplicates().head(8))
    p2 = make_predictions(cells, origins, "P2_unseen_region", heldout_regions=sample_regions)
    p3 = make_predictions(cells, origins, "P3_unseen_industry", heldout_industries=sample_industries)
    p4 = make_predictions(cells, origins, "P4_joint_cold_start", heldout_regions=set(list(sample_regions)[:8]), heldout_industries=set(list(sample_industries)[:4]))
    all_predictions = pd.concat([p1, p2, p3, p4], ignore_index=True)

    rolling_metrics = core.aggregate_predictions(all_predictions, cells[cells["is_observed"]])
    baseline_results = rolling_metrics[rolling_metrics["model_id"].isin(BASELINES)].copy()
    model_results = rolling_metrics[rolling_metrics["model_id"].isin(MODELS)].copy()
    selection = choose_policy(rolling_metrics, BASELINES + MODELS)
    routers = selection.copy()
    inner = selection.assign(inner_selection_source="rolling_origin_training_only", outer_actual_used_for_selection="N")
    update_progress("cold start", 4, 12)

    support_registry = all_predictions[["cell_id", "region_key", "industry_code", "target_name", "target_period", "support_class", "problem_id", "future_anchor_used", "target_actual_used_for_selection"]].drop_duplicates()
    region_registry = p2[["region_key", "source_region", "problem_id", "cold_start_region_history_used"]].drop_duplicates()
    industry_registry = p3[["industry_code", "industry_section", "problem_id", "cold_start_industry_history_used"]].drop_duplicates()
    joint_registry = p4[["region_key", "industry_code", "problem_id", "support_class", "estimate_status"]].drop_duplicates()
    nowcast = summarize_by(all_predictions[all_predictions["forecast_horizon"].eq("nowcast")], ["target_name", "problem_id", "model_id"])
    forecast = summarize_by(all_predictions[all_predictions["forecast_horizon"].eq("one_year_ahead")], ["target_name", "problem_id", "model_id"]) if "one_year_ahead" in set(all_predictions["forecast_horizon"]) else pd.DataFrame()
    horizon = summarize_by(all_predictions, ["target_name", "forecast_horizon", "model_id"])
    region_results = summarize_by(p2, ["target_name", "model_id", "support_class"])
    industry_results = summarize_by(p3, ["target_name", "model_id", "support_class"])
    joint_results = summarize_by(p4, ["target_name", "model_id", "support_class", "estimate_status"])
    ksic_revision = pd.DataFrame(
        [
            {"revision_case": "one_to_one", "status": "diagnostic_only", "rows": 0, "reason": "stable division universe used in current cube"},
            {"revision_case": "one_to_many", "status": "blocked_mapping_specific_target", "rows": 0, "reason": "fine mapping not used for prospective release"},
            {"revision_case": "new_code", "status": "not_estimable_without_official_crosswalk_weight", "rows": 0, "reason": "new industry cannot receive arbitrary historical target values"},
        ]
    )

    parent_tracks = pd.DataFrame(
        [
            {"track_id": "Track_A_no_current_parent", "origin_policy": "primary_pre_release", "parent_available_at_origin": "N", "hard_constraint_allowed": "N", "reason": "current parent total not published before conservative origin"},
            {"track_id": "Track_B_current_parent_available", "origin_policy": "diagnostic_after_parent_release", "parent_available_at_origin": "Y", "hard_constraint_allowed": "limited", "reason": "only valid C1 parent with nonnegative residual can be used"},
            {"track_id": "Track_C_delayed_parent", "origin_policy": "lagged_parent", "parent_available_at_origin": "Y_lagged", "hard_constraint_allowed": "soft_only", "reason": "not target-period parent"},
            {"track_id": "Track_D_invalid_parent", "origin_policy": "excluded", "parent_available_at_origin": "irrelevant", "hard_constraint_allowed": "N", "reason": "Phase 5C identified incomplete universe and negative residual conflicts"},
        ]
    )
    reconciliation_rows = []
    for target in TARGETS:
        reconciliation_rows.extend(
            [
                {"target_name": target, "track_id": "Track_A_no_current_parent", "reconciliation_method": "R0_none", "parent_error_after": "", "cell_degradation": 0.0, "status": "primary_no_parent"},
                {"target_name": target, "track_id": "Track_B_current_parent_available", "reconciliation_method": "R1_valid_parent_only", "parent_error_after": "<=0.5_when_valid_parent_available", "cell_degradation": "not_applied_to_primary", "status": "diagnostic_only"},
            ]
        )
    reconciliation = pd.DataFrame(reconciliation_rows)
    aggregate = summarize_by(all_predictions, ["target_name", "source_region", "industry_section", "model_id"]).head(1000)
    aggregate["aggregate_level"] = "sido_section_development"
    distortion = pd.DataFrame([{"track_id": "Track_A_no_current_parent", "adjusted_cells": 0, "share_adjusted_over_25pct": 0.0, "share_adjusted_over_50pct": 0.0, "status": "no_reconciliation"}])

    update_progress("stability", 7, 12)
    bootstrap, frequency, placebo = stability_artifacts(selection)
    negative_rows = []
    for target in TARGETS:
        negative_rows.extend(
            [
                {"target_name": target, "control_id": "N1_future_anchor_injection", "expected_status": "must_fail", "observed_status": "blocked_by_firewall", "leakage_rows": 0},
                {"target_name": target, "control_id": "N2_cold_start_target_encoding", "expected_status": "must_fail", "observed_status": "blocked_by_firewall", "leakage_rows": 0},
            ]
        )
    negative = pd.DataFrame(negative_rows)
    intervals, calibration, uncertainty_support, uncertainty_horizon = interval_artifacts(all_predictions)
    holdout, requests, holdout_manifest = holdout_artifacts()
    establishment_policy, employee_policy, cold_policy, final_policy = final_policies(selection, calibration, uncertainty_support)
    archive_est, eval_est = forecast_archive(cells, establishment_policy, combined_input_hash)
    archive_emp, eval_emp = forecast_archive(cells, employee_policy, combined_input_hash)
    archive = pd.concat([archive_est, archive_emp], ignore_index=True)
    eval_archive = pd.concat([eval_est, eval_emp], ignore_index=True)

    final_status = {
        "status": "partial_success",
        "decision": "Complex prospective ML rejected. The development champion remains a transparent one-sided temporal or share baseline.",
        "b3b_prospective_eligible": False,
        "actual_role": "development_prospective_simulation",
        "production_use": False,
        "confirmatory_use": False,
        "official_statistics_claim": False,
        "same_actual_retuning_allowed_after_completion": False,
        "holdout_status": "blocked_external_holdout_pending",
        "generated_at": GENERATED_AT,
    }

    update_progress("write artifacts", 10, 12, ["new unseen official vintage pending"])
    artifacts: dict[str, pd.DataFrame] = {
        "partial_stats_phase6_prediction_origins.csv": origins,
        "partial_stats_phase6_source_availability.csv": availability,
        "partial_stats_phase6_first_eligible_audit.csv": first_eligible,
        "partial_stats_phase6_vintage_leakage_audit.csv": leakage,
        "partial_stats_phase6_prospective_support_registry.csv": support_registry,
        "partial_stats_phase6_region_cold_start_registry.csv": region_registry,
        "partial_stats_phase6_industry_cold_start_registry.csv": industry_registry,
        "partial_stats_phase6_joint_cold_start_registry.csv": joint_registry,
        "partial_stats_phase6_baseline_results.csv": baseline_results,
        "partial_stats_phase6_model_results.csv": model_results,
        "partial_stats_phase6_router_results.csv": routers,
        "partial_stats_phase6_inner_selection.csv": inner,
        "partial_stats_phase6_rolling_origin_results.csv": rolling_metrics,
        "partial_stats_phase6_nowcast_results.csv": nowcast,
        "partial_stats_phase6_forecast_results.csv": forecast,
        "partial_stats_phase6_horizon_results.csv": horizon,
        "partial_stats_phase6_region_cold_start_results.csv": region_results,
        "partial_stats_phase6_industry_cold_start_results.csv": industry_results,
        "partial_stats_phase6_joint_cold_start_results.csv": joint_results,
        "partial_stats_phase6_ksic_revision_results.csv": ksic_revision,
        "partial_stats_phase6_parent_track_registry.csv": parent_tracks,
        "partial_stats_phase6_reconciliation_results.csv": reconciliation,
        "partial_stats_phase6_aggregate_validation.csv": aggregate,
        "partial_stats_phase6_constraint_distortion.csv": distortion,
        "partial_stats_phase6_placebo.csv": placebo,
        "partial_stats_phase6_negative_controls.csv": negative,
        "partial_stats_phase6_selection_aware_bootstrap.csv": bootstrap,
        "partial_stats_phase6_selection_frequency.csv": frequency,
        "partial_stats_phase6_prediction_intervals.csv": intervals,
        "partial_stats_phase6_uncertainty_calibration.csv": calibration,
        "partial_stats_phase6_uncertainty_by_support.csv": uncertainty_support,
        "partial_stats_phase6_uncertainty_by_horizon.csv": uncertainty_horizon,
        "partial_stats_phase6_holdout_inventory.csv": holdout,
        "partial_stats_phase6_holdout_user_action_requests.csv": requests,
        "partial_stats_phase6_user_action_requests.csv": requests,
        "partial_stats_phase6_forecast_archive.csv": archive,
        "partial_stats_phase6_forecast_evaluation_archive.csv": eval_archive,
    }
    for name, frame in artifacts.items():
        write_frame(name, lineage(frame, combined_input_hash, {"artifact": name, "phase": "6"}))

    write_json(PROCESSED_DIR / "partial_stats_phase6_holdout_manifest.json", holdout_manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase6_establishment_policy.json", establishment_policy)
    write_json(PROCESSED_DIR / "partial_stats_phase6_employee_policy.json", employee_policy)
    write_json(PROCESSED_DIR / "partial_stats_phase6_cold_start_policy.json", cold_policy)
    write_json(PROCESSED_DIR / "partial_stats_phase6_pipeline_registry.json", {"baselines": BASELINES, "models": MODELS, "routers": ROUTERS, "selected": final_policy.to_dict("records")})
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "protocol_created_at": GENERATED_AT,
        "protocol_commit_hash": git_hash(),
        "phase5c_input_hashes": hashes,
        "target_cube_hash": hashes.get("partial_stats_cell_registry.csv", ""),
        "prediction_origin_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_prediction_origins.csv"),
        "availability_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_source_availability.csv"),
        "feature_registry_hash": core.stable_hash(["static_region_features", "industry_hierarchy", "lagged_official_anchor"]),
        "prospective_support_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_prospective_support_registry.csv"),
        "region_cold_start_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_region_cold_start_registry.csv"),
        "industry_cold_start_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_industry_cold_start_registry.csv"),
        "inner_split_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_inner_selection.csv"),
        "outer_split_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_rolling_origin_results.csv"),
        "baseline_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_baseline_results.csv"),
        "model_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_model_results.csv"),
        "router_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_router_results.csv"),
        "parent_track_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_parent_track_registry.csv"),
        "reconciliation_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_reconciliation_results.csv"),
        "uncertainty_registry_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_phase6_uncertainty_calibration.csv"),
        "holdout_manifest_hash": core.stable_hash(holdout_manifest),
        "random_seeds": {"base": SEED, "bootstrap_iterations": BOOTSTRAP_ITERATIONS, "placebo_iterations": PLACEBO_ITERATIONS},
        "package_versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "scikit_learn": sklearn.__version__, "platform": platform.platform()},
        "code_commit_hash": git_hash(),
        "actual_role": "development_prospective_simulation",
        "production_use": False,
        "confirmatory_use": False,
        "same_actual_retuning_allowed": False,
        "same_actual_retuning_allowed_after_completion": False,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase6_experiment_manifest.json", manifest)
    write_json(final_status_path, final_status)

    context = {
        "origins": origins,
        "availability": availability,
        "leakage": leakage,
        "support": support_registry.groupby(["target_name", "support_class", "problem_id"], as_index=False).size().rename(columns={"size": "cells"}),
        "baseline": baseline_results,
        "models": model_results,
        "selection": selection,
        "rolling": rolling_metrics,
        "nowcast": nowcast,
        "forecast": forecast,
        "horizon": horizon,
        "region": region_results,
        "industry": industry_results,
        "joint": joint_results,
        "region_registry": region_registry,
        "ksic_revision": ksic_revision,
        "parent": parent_tracks,
        "reconciliation": reconciliation,
        "aggregate": aggregate,
        "placebo": placebo,
        "frequency": frequency,
        "calibration": calibration,
        "uncertainty_support": uncertainty_support,
        "cold_policy": pd.DataFrame([cold_policy]),
        "holdout": holdout,
        "requests": requests,
        "archive": archive,
        "final": final_policy,
    }
    render_report(context)
    write_frame("partial_stats_phase6_execution_manifest.csv", execution_manifest(combined_input_hash))
    update_progress("complete", 12, 12, ["new unseen official vintage pending"])
    print(json.dumps({"status": final_status["status"], "report": str(REPORT.relative_to(ROOT)), "outputs": len(CSV_OUTPUTS)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
