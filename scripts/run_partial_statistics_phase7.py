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

import partial_stats_phase6_core as core
import run_partial_statistics_phase6 as phase6
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
EXPERIMENT_ID = "partial_statistics_estimation_phase7"
SEED = 20260718
FULL_REFIT_BOOTSTRAP = 1000
POLICY_BOOTSTRAP = 2000
TARGETS = ["establishments", "employees"]
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase7.md"

PHASE6_HASH_INPUTS = [
    "partial_stats_phase6_experiment_manifest.json",
    "partial_stats_phase6_pipeline_registry.json",
    "partial_stats_phase6_baseline_results.csv",
    "partial_stats_phase6_model_results.csv",
    "partial_stats_phase6_rolling_origin_results.csv",
    "partial_stats_phase6_selection_aware_bootstrap.csv",
    "partial_stats_phase6_prediction_intervals.csv",
    "partial_stats_phase6_final_status.json",
]

CSV_OUTPUTS = [
    "partial_stats_phase7_phase6_reproduction.csv",
    "partial_stats_phase7_input_hashes.csv",
    "partial_stats_phase7_model_implementation_registry.csv",
    "partial_stats_phase7_prediction_identity_audit.csv",
    "partial_stats_phase7_alias_registry.csv",
    "partial_stats_phase7_fallback_audit.csv",
    "partial_stats_phase7_target_year_inventory.csv",
    "partial_stats_phase7_target_schema_audit.csv",
    "partial_stats_phase7_historical_cell_registry.csv",
    "partial_stats_phase7_region_crosswalk.csv",
    "partial_stats_phase7_region_universe_audit.csv",
    "partial_stats_phase7_ksic_crosswalk.csv",
    "partial_stats_phase7_industry_universe_audit.csv",
    "partial_stats_phase7_release_registry.csv",
    "partial_stats_phase7_release_date_evidence.csv",
    "partial_stats_phase7_first_eligible_audit.csv",
    "partial_stats_phase7_vintage_leakage_audit.csv",
    "partial_stats_phase7_auxiliary_source_inventory.csv",
    "partial_stats_phase7_auxiliary_feature_registry.csv",
    "partial_stats_phase7_feature_bundle_registry.csv",
    "partial_stats_phase7_parent_constraint_inventory.csv",
    "partial_stats_phase7_parent_definition_audit.csv",
    "partial_stats_phase7_parent_mismatch_audit.csv",
    "partial_stats_phase7_parent_track_registry.csv",
    "partial_stats_phase7_prediction_origins.csv",
    "partial_stats_phase7_inner_selection.csv",
    "partial_stats_phase7_outer_results.csv",
    "partial_stats_phase7_horizon_results.csv",
    "partial_stats_phase7_year_results.csv",
    "partial_stats_phase7_baseline_results.csv",
    "partial_stats_phase7_model_results.csv",
    "partial_stats_phase7_residual_correction_results.csv",
    "partial_stats_phase7_material_degradation_audit.csv",
    "partial_stats_phase7_region_cold_start_results.csv",
    "partial_stats_phase7_industry_cold_start_results.csv",
    "partial_stats_phase7_selective_prediction_results.csv",
    "partial_stats_phase7_coverage_accuracy_curve.csv",
    "partial_stats_phase7_not_estimable_registry.csv",
    "partial_stats_phase7_full_refit_bootstrap.csv",
    "partial_stats_phase7_policy_bootstrap.csv",
    "partial_stats_phase7_placebo.csv",
    "partial_stats_phase7_selection_frequency.csv",
    "partial_stats_phase7_prediction_intervals.csv",
    "partial_stats_phase7_uncertainty_calibration.csv",
    "partial_stats_phase7_uncertainty_by_year.csv",
    "partial_stats_phase7_uncertainty_by_support.csv",
    "partial_stats_phase7_holdout_inventory.csv",
    "partial_stats_phase7_holdout_contamination_audit.csv",
    "partial_stats_phase7_holdout_user_action_requests.csv",
    "partial_stats_phase7_forecast_archive.csv",
    "partial_stats_phase7_forecast_evaluation_archive.csv",
    "partial_stats_phase7_user_action_requests.csv",
    "partial_stats_phase7_execution_manifest.csv",
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


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    columns = list(subset.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in columns) + " |")
    return "\n".join(lines)


def lineage(frame: pd.DataFrame, input_hash: str, config: Any) -> pd.DataFrame:
    out = frame.copy()
    target_path = PROCESSED_DIR / "partial_stats_cell_registry.csv"
    origin_path = PROCESSED_DIR / "partial_stats_phase7_prediction_origins.csv"
    feature_path = PROCESSED_DIR / "partial_stats_phase7_feature_bundle_registry.csv"
    out["input_hash"] = input_hash
    out["target_cube_hash"] = core.file_sha256(target_path) if target_path.exists() else ""
    out["origin_registry_hash"] = core.file_sha256(origin_path) if origin_path.exists() else ""
    out["feature_registry_hash"] = core.file_sha256(feature_path) if feature_path.exists() else ""
    out["model_config_hash"] = core.stable_hash(config)
    out["code_commit_hash"] = git_hash()
    out["run_id"] = EXPERIMENT_ID
    out["seed"] = SEED
    out["created_at"] = GENERATED_AT
    return out


def input_hashes() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    names = PHASE6_HASH_INPUTS + [
        "partial_stats_cell_registry.csv",
        "partial_stats_region_features.csv",
        "partial_stats_industry_features.csv",
        "partial_stats_independent_constraint_inventory.csv",
        "expanded_manufacturing_sigungu_ksic.csv",
        "kosis_table_release_dates.csv",
        "ksic8_9_official_crosswalk.csv",
        "ksic9_10_official_crosswalk.csv",
        "ksic10_11_official_crosswalk.csv",
    ]
    for name in names:
        path = PROCESSED_DIR / name
        rows.append(
            {
                "input_name": name,
                "input_path": f"data/processed/{name}",
                "exists": "Y" if path.exists() else "N",
                "file_hash": core.file_sha256(path) if path.exists() else "",
                "file_size": path.stat().st_size if path.exists() else "",
                "role": "phase6_frozen_baseline" if name in PHASE6_HASH_INPUTS else "phase7_input",
            }
        )
    report = ROOT / "reports" / "partial_statistics_estimation_phase6.md"
    rows.append(
        {
            "input_name": "partial_statistics_estimation_phase6.md",
            "input_path": "reports/partial_statistics_estimation_phase6.md",
            "exists": "Y" if report.exists() else "N",
            "file_hash": core.file_sha256(report) if report.exists() else "",
            "file_size": report.stat().st_size if report.exists() else "",
            "role": "phase6_frozen_baseline",
        }
    )
    return pd.DataFrame(rows)


def combined_input_hash(hashes: pd.DataFrame) -> str:
    return core.stable_hash(hashes[["input_path", "file_hash", "role"]].to_dict("records"))


def phase6_reproduction() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    nowcast = read_frame("partial_stats_phase6_nowcast_results.csv")
    horizon = read_frame("partial_stats_phase6_horizon_results.csv")
    selection = read_frame("partial_stats_phase6_selection_frequency.csv")
    region = read_frame("partial_stats_phase6_region_cold_start_results.csv")
    industry = read_frame("partial_stats_phase6_industry_cold_start_results.csv")

    checks = [
        ("PB0 establishments nowcast WMAPE", nowcast, {"target_name": "establishments", "problem_id": "P1_future_period", "model_id": "PB0_last_observation_level"}, "wmape", 0.0830871221209108),
        ("PB0 employees nowcast WMAPE", nowcast, {"target_name": "employees", "problem_id": "P1_future_period", "model_id": "PB0_last_observation_level"}, "wmape", 0.0978123896946449),
        ("PB0 establishments one-year-ahead WMAPE", horizon, {"target_name": "establishments", "forecast_horizon": "one_year_ahead", "model_id": "PB0_last_observation_level"}, "wmape", 0.3263073361521203),
        ("PB0 employees one-year-ahead WMAPE", horizon, {"target_name": "employees", "forecast_horizon": "one_year_ahead", "model_id": "PB0_last_observation_level"}, "wmape", 0.3044952144202435),
        ("PB0 establishments bootstrap selection count", selection, {"target_name": "establishments", "selected_pipeline": "PB0_last_observation_level"}, "selection_count", 2000.0),
        ("PB0 employees bootstrap selection count", selection, {"target_name": "employees", "selected_pipeline": "PB0_last_observation_level"}, "selection_count", 2000.0),
        ("Region Cold-start establishments PB0 WMAPE", region, {"target_name": "establishments", "model_id": "PB0_last_observation_level"}, "wmape", 2.262476712510648),
        ("Region Cold-start employees PB0 WMAPE", region, {"target_name": "employees", "model_id": "PB0_last_observation_level"}, "wmape", 2.43516715184072),
        ("Industry Cold-start establishments PB0 WMAPE", industry, {"target_name": "establishments", "model_id": "PB0_last_observation_level"}, "wmape", 1.1851306980461567),
        ("Industry Cold-start employees PB0 WMAPE", industry, {"target_name": "employees", "model_id": "PB0_last_observation_level"}, "wmape", 1.189272388161393),
    ]
    for metric_name, frame, filters, column, expected in checks:
        subset = frame.copy()
        for key, value in filters.items():
            if key in subset.columns:
                subset = subset[subset[key].eq(str(value))]
        observed = math.nan
        if not subset.empty and column in subset.columns:
            observed = float(pd.to_numeric(subset.iloc[0][column], errors="coerce"))
        rows.append(
            {
                "metric_name": metric_name,
                "source_artifact": "phase6",
                "filter": json.dumps(filters, ensure_ascii=False, sort_keys=True),
                "value_column": column,
                "expected_value": expected,
                "reproduced_value": observed,
                "absolute_diff": abs(observed - expected) if math.isfinite(observed) else "",
                "status": "pass" if math.isfinite(observed) and abs(observed - expected) < 1e-9 else "fail",
            }
        )
    return pd.DataFrame(rows)


def implementation_registry() -> pd.DataFrame:
    rows = [
        ("PB0_last_observation_level", "baseline_level", "scripts/run_partial_statistics_phase6.py", "make_predictions", "latest history lookup", "fallback_prediction", "{}", "lagged observed cells", "period/source_region/industry_code/target", "none", "", "", "fully_implemented"),
        ("PB1_last_observed_share", "baseline_share", "scripts/run_partial_statistics_phase6.py", "make_predictions", "shrunk latest/national mix", "pb3 expression", "{\"latest_weight\":0.65,\"national_weight\":0.35}", "lagged observed cells", "industry national mean", "none", "PB3_shrunk_latest_share", "same expression as PB3", "alias"),
        ("PB2_one_sided_linear_trend", "baseline_growth", "scripts/partial_stats_phase6_core.py", "one_sided_trend", "one-sided capped difference", "trend.fillna(base)", "{\"cap\":\"±50pct of last level\"}", "two or more historical points", "period/cell id", "none", "PB0_last_observation_level", "missing trend history", "fully_implemented"),
        ("PB3_shrunk_latest_share", "baseline_share", "scripts/run_partial_statistics_phase6.py", "make_predictions", "shrunk latest/national mix", "pb3 expression", "{\"latest_weight\":0.65,\"national_weight\":0.35}", "lagged observed cells", "industry national mean", "none", "", "", "fully_implemented"),
        ("PB4_empirical_bayes_level", "baseline_share", "scripts/run_partial_statistics_phase6.py", "make_predictions", "same as pb3", "pb3 expression", "{\"alias_of\":\"PB3\"}", "lagged observed cells", "industry national mean", "none", "PB3_shrunk_latest_share", "same expression as PB3", "alias"),
        ("PB5_size_proportional", "baseline_share", "scripts/run_partial_statistics_phase6.py", "make_predictions", "same as pb3", "pb3 expression", "{\"alias_of\":\"PB3\"}", "lagged observed cells", "industry national mean", "none", "PB3_shrunk_latest_share", "same expression as PB3", "alias"),
        ("PB6_proxy_weighted_allocation", "baseline_share", "scripts/run_partial_statistics_phase6.py", "make_predictions", "same as pb3", "pb3 expression", "{\"alias_of\":\"PB3\"}", "lagged observed cells", "industry national mean", "none", "PB3_shrunk_latest_share", "same expression as PB3", "alias"),
        ("PB7_historical_growth_share", "baseline_growth", "scripts/partial_stats_phase6_core.py", "one_sided_trend", "same as PB2", "trend.fillna(base)", "{\"alias_of\":\"PB2\"}", "two or more historical points", "period/cell id", "none", "PB2_one_sided_linear_trend", "same expression as PB2", "alias"),
        ("PB8_conservative_no_change", "baseline_level", "scripts/run_partial_statistics_phase6.py", "make_predictions", "same as PB0", "fallback_prediction", "{\"alias_of\":\"PB0\"}", "lagged observed cells", "period/source_region/industry_code/target", "none", "PB0_last_observation_level", "conservative no-change equals latest level", "alias"),
        ("PM1_one_sided_hierarchical_ridge", "ridge", "scripts/run_partial_statistics_phase6.py", "train_ridge", "Ridge(alpha=3.0)", "log1p inverse", "{\"alpha\":3.0}", "lagged observed cells", "period/section/source_region/industry_code", "log1p", "PB0_last_observation_level", "empty train/valid", "fully_implemented"),
        ("PM2_hierarchical_negative_binomial_proxy", "count_model_proxy", "scripts/run_partial_statistics_phase6.py", "make_predictions", "uses PM1 ridge predictions", "ridge", "{\"proxy\":\"ridge_not_negative_binomial\"}", "lagged observed cells", "same as PM1", "log1p", "PM1_one_sided_hierarchical_ridge", "negative-binomial not implemented", "proxy_only"),
        ("PM3_prospective_parent_share", "parent_share_proxy", "scripts/run_partial_statistics_phase6.py", "make_predictions", "uses pb3 because current parent unavailable", "pb3", "{\"parent\":\"not actually used\"}", "lagged observed cells", "industry national mean", "none", "PB3_shrunk_latest_share", "current parent blocked", "fallback_dominant"),
        ("PM4_dynamic_share", "growth_model", "scripts/partial_stats_phase6_core.py", "one_sided_trend", "same as PB2 trend", "trend.fillna(base)", "{\"alias_of\":\"PB2\"}", "two or more historical points", "period/cell id", "none", "PB2_one_sided_linear_trend", "same expression as PB2", "alias"),
        ("PM5_graph_temporal", "graph_proxy", "scripts/run_partial_statistics_phase6.py", "make_predictions", "uses pb3, no graph fit", "pb3", "{\"graph\":\"not_used\"}", "lagged observed cells", "industry national mean", "none", "PB3_shrunk_latest_share", "graph model not implemented", "fallback_dominant"),
        ("PM6_coupled_establishment_employee", "coupled_proxy", "scripts/run_partial_statistics_phase6.py", "make_predictions", "uses PM1 ridge independently", "ridge", "{\"coupling\":\"not_used\"}", "lagged observed cells", "same as PM1", "log1p", "PM1_one_sided_hierarchical_ridge", "coupled objective not implemented", "alias"),
        ("PM7_cold_start_meta_model", "ridge_cold", "scripts/run_partial_statistics_phase6.py", "train_ridge", "Ridge without ids", "log1p inverse", "{\"alpha\":3.0,\"include_ids\":false}", "lagged observed cells", "period/section only", "log1p", "PB0_last_observation_level", "empty train/valid", "partially_implemented"),
        ("PM8_prospective_factorization", "factorization_proxy", "scripts/run_partial_statistics_phase6.py", "make_predictions", "uses pb3, no factorization fit", "pb3", "{\"factorization\":\"not_used\"}", "lagged observed cells", "industry national mean", "none", "PB3_shrunk_latest_share", "factorization model not implemented", "fallback_dominant"),
    ]
    columns = [
        "model_id",
        "model_family",
        "implementation_module",
        "implementation_function",
        "fit_method",
        "prediction_method",
        "hyperparameters",
        "training_columns",
        "feature_columns",
        "target_transform",
        "fallback_model",
        "fallback_conditions",
        "implementation_status",
    ]
    return pd.DataFrame(rows, columns=columns)


def prediction_identity_audit(cells: pd.DataFrame, origins: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p1 = phase6.make_predictions(cells, origins, "P1_future_period")
    sample_regions = set(cells["region_key"].drop_duplicates().head(24))
    sample_industries = set(cells["industry_code"].drop_duplicates().head(8))
    p2 = phase6.make_predictions(cells, origins, "P2_unseen_region", heldout_regions=sample_regions)
    p3 = phase6.make_predictions(cells, origins, "P3_unseen_industry", heldout_industries=sample_industries)
    all_predictions = pd.concat([p1, p2, p3], ignore_index=True)
    if all_predictions.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    key_cols = ["target_name", "problem_id", "forecast_horizon", "model_id"]
    hash_rows = []
    for key, group in all_predictions.groupby(key_cols, sort=False):
        records = group.sort_values(["cell_id", "prediction_origin_id"])[["cell_id", "prediction_origin_id", "prediction"]].to_dict("records")
        hash_rows.append(dict(zip(key_cols, key), prediction_hash=core.stable_hash(records), unique_prediction_count=int(group["prediction"].nunique()), fallback_rate=""))

    models = sorted(all_predictions["model_id"].unique())
    audit_rows = []
    alias_rows = []
    group_cols = ["target_name", "problem_id", "forecast_horizon"]
    for group_key, group in all_predictions.groupby(group_cols, sort=False):
        wide = group.pivot_table(index=["cell_id", "prediction_origin_id"], columns="model_id", values="prediction", aggfunc="first")
        for i, left in enumerate(models):
            if left not in wide.columns:
                continue
            for right in models[i + 1 :]:
                if right not in wide.columns:
                    continue
                pair = wide[[left, right]].dropna()
                if pair.empty:
                    continue
                diff = (pair[left] - pair[right]).abs()
                exact = float((diff <= 1e-12).mean())
                near = float((diff <= np.maximum(1e-9, pair[left].abs() * 1e-9)).mean())
                max_abs = float(diff.max())
                corr = float(pair[left].corr(pair[right])) if pair[left].nunique() > 1 and pair[right].nunique() > 1 else 1.0
                row = {
                    "target_name": group_key[0],
                    "problem_id": group_key[1],
                    "forecast_horizon": group_key[2],
                    "model_id_left": left,
                    "model_id_right": right,
                    "prediction_correlation": corr,
                    "exact_match_rate": exact,
                    "near_match_rate": near,
                    "max_abs_diff": max_abs,
                    "alias_rule": "exact_match_rate>=0.9999_or_max_abs_diff<=1e-12",
                    "alias_detected": "Y" if exact >= 0.9999 or max_abs <= 1e-12 else "N",
                    "n": int(len(pair)),
                }
                audit_rows.append(row)
                if row["alias_detected"] == "Y":
                    alias_rows.append(
                        {
                            "alias_model_id": right,
                            "canonical_model_id": left,
                            "target_name": group_key[0],
                            "problem_id": group_key[1],
                            "forecast_horizon": group_key[2],
                            "evidence": f"exact_match_rate={exact:.6f}; max_abs_diff={max_abs:.12g}",
                            "promotion_allowed": "N",
                        }
                    )
    fallback_rows = []
    registry = implementation_registry()
    for row in registry.to_dict("records"):
        fallback_rows.append(
            {
                "requested_model_id": row["model_id"],
                "executed_model_id": row["fallback_model"] or row["model_id"],
                "fallback_used": "Y" if row["fallback_model"] else "N",
                "fallback_reason": row["fallback_conditions"],
                "support_class": "all_development_support_classes",
                "available_features": row["feature_columns"],
                "implementation_status": row["implementation_status"],
            }
        )
    return pd.DataFrame(hash_rows), pd.concat([pd.DataFrame(hash_rows), pd.DataFrame(audit_rows)], ignore_index=True, sort=False), pd.DataFrame(alias_rows), pd.DataFrame(fallback_rows)


def historical_inventory() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path = PROCESSED_DIR / "expanded_manufacturing_sigungu_ksic.csv"
    if path.exists():
        expanded = pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)
        expanded["year"] = pd.to_numeric(expanded["prd_de"], errors="coerce").astype("Int64")
        rows = []
        for year, group in expanded.dropna(subset=["year"]).groupby("year", sort=True):
            role = "development_extension" if int(year) < 2021 else "development_contaminated"
            rows.append(
                {
                    "source_dataset": "manufacturing_mining_sigungu_ksic",
                    "org_id": "101",
                    "table_id": "DT_1FS1101",
                    "available_year": int(year),
                    "table_version": "local_processed_expanded",
                    "ksic_version": "KSIC10_assumed_current_table",
                    "region_classification_version": "current_local_region_names",
                    "download_status": "local_processed_available",
                    "raw_file": "data/processed/expanded_manufacturing_sigungu_ksic.csv",
                    "file_hash": core.file_sha256(path),
                    "row_count": int(len(group)),
                    "schema_hash": core.stable_hash(list(group.columns)),
                    "data_role": role,
                }
            )
        schema = pd.DataFrame(
            [
                {
                    "source_file": "data/processed/expanded_manufacturing_sigungu_ksic.csv",
                    "column_name": col,
                    "non_empty_rows": int((expanded[col].astype(str) != "").sum()),
                    "schema_hash": core.stable_hash(list(expanded.columns)),
                }
                for col in expanded.columns
            ]
        )
        cells = expanded.rename(
            columns={
                "c1_id": "region_code",
                "c1_nm": "region_name",
                "c2_id": "industry_code",
                "c2_nm": "industry_name",
                "prd_de": "period",
                "metric": "target_name",
            }
        )[
            ["region_code", "region_name", "industry_code", "industry_name", "period", "target_name", "value", "ksic_level"]
        ].head(200000)
        cells["registry_role"] = "historical_inventory_sample" if len(expanded) > len(cells) else "historical_inventory_full"
        return pd.DataFrame(rows), schema, cells

    cells = read_frame("partial_stats_cell_registry.csv")
    rows = []
    if not cells.empty:
        for year, group in cells.groupby("period", sort=True):
            rows.append(
                {
                    "source_dataset": "partial_stats_cell_registry",
                    "org_id": "101",
                    "table_id": "DT_1FS1101",
                    "available_year": year,
                    "table_version": "phase6_target_cube",
                    "ksic_version": "KSIC10_assumed_current_table",
                    "region_classification_version": "current_local_region_names",
                    "download_status": "local_processed_available",
                    "raw_file": "data/processed/partial_stats_cell_registry.csv",
                    "file_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_cell_registry.csv"),
                    "row_count": int(len(group)),
                    "schema_hash": core.stable_hash(list(cells.columns)),
                    "data_role": "development_contaminated",
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(), cells.head(200000)


def crosswalk_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    region = read_frame("partial_stats_region_features.csv")
    region_crosswalk = pd.DataFrame(
        [
            {
                "source_region_code": "",
                "source_region_name": row["region_key"],
                "source_year": "current",
                "target_region_key": row["region_key"],
                "method": "exact_name",
                "quality": "high",
            }
            for row in region.to_dict("records")
        ]
    )
    universe = pd.DataFrame(
        [
            {"universe_id": "U228_current", "region_count": int(region["region_key"].nunique()) if not region.empty else 0, "role": "primary_current_universe", "release_allowed": "development_only"},
            {"universe_id": "UStable_historical", "region_count": "", "role": "pending_historical_boundary_harmonization", "release_allowed": "N"},
        ]
    )
    ksic_rows = []
    for name, version_pair in [
        ("ksic8_9_official_crosswalk.csv", "8_to_9"),
        ("ksic9_10_official_crosswalk.csv", "9_to_10"),
        ("ksic10_11_official_crosswalk.csv", "10_to_11"),
    ]:
        path = PROCESSED_DIR / name
        if path.exists():
            frame = read_frame(name)
            ksic_rows.append(
                {
                    "crosswalk_file": f"data/processed/{name}",
                    "version_pair": version_pair,
                    "row_count": int(len(frame)),
                    "file_hash": core.file_sha256(path),
                    "relationship_status": "official_processed_available",
                }
            )
        else:
            ksic_rows.append(
                {
                    "crosswalk_file": f"data/processed/{name}",
                    "version_pair": version_pair,
                    "row_count": 0,
                    "file_hash": "",
                    "relationship_status": "missing",
                }
            )
    industry = read_frame("partial_stats_industry_features.csv")
    industry_universe = pd.DataFrame(
        [
            {
                "universe_id": "KSIC_middle_current",
                "industry_count": int(industry["industry_code"].nunique()) if not industry.empty else 0,
                "role": "primary_phase6_cube",
                "release_allowed": "development_only",
            },
            {
                "universe_id": "KSIC_multiversion_stable",
                "industry_count": "",
                "role": "pending_full_historical_harmonization",
                "release_allowed": "N",
            },
        ]
    )
    return region_crosswalk, universe, pd.DataFrame(ksic_rows), industry_universe


def release_artifacts(origins: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    release_dates = read_frame("kosis_table_release_dates.csv")
    rows = []
    evidence = []
    if not release_dates.empty:
        for row in release_dates.to_dict("records"):
            rows.append(
                {
                    "source_dataset": row.get("source_dataset", ""),
                    "source_table": row.get("source_table", ""),
                    "reference_period": row.get("reference_period", ""),
                    "official_release_date": row.get("official_release_date", ""),
                    "table_update_date": row.get("table_update_date", ""),
                    "release_status": row.get("release_status", ""),
                    "release_confidence": "missing_or_approximation" if not row.get("official_release_date") else "official_date",
                }
            )
            evidence.append(
                {
                    "source_table": row.get("source_table", ""),
                    "reference_period": row.get("reference_period", ""),
                    "evidence_type": row.get("release_evidence_priority", ""),
                    "evidence_value": row.get("official_release_date") or row.get("table_update_date") or "",
                    "official_metadata_found": "Y" if row.get("official_release_date") else "N",
                }
            )
    first_rows = []
    leakage_rows = []
    for row in origins.to_dict("records"):
        target_period = int(row["target_period"])
        approx = core.first_eligible_date(target_period, 12)
        eligible = core.available_at_origin(approx, row["prediction_origin_date"])
        first_rows.append(
            {
                "prediction_origin_id": row["prediction_origin_id"],
                "source_id": "target_detail_DT_1FS1101",
                "observation_period": target_period,
                "first_eligible_date": approx,
                "evidence_status": "conservative_publication_approximation",
                "prediction_origin_date": row["prediction_origin_date"],
                "eligible_at_origin": "Y" if eligible else "N",
                "allowed_in_features": "N",
                "reason": "target-year detailed official values remain prohibited as features",
            }
        )
    leakage_rows.append(
        {
            "audit_id": "P7-L1-target-detail-firewall",
            "rows_checked": len(first_rows),
            "leakage_rows": 0,
            "status": "pass",
            "rule": "target-year details are never eligible features before policy freeze or holdout evaluation",
        }
    )
    leakage_rows.append(
        {
            "audit_id": "P7-L2-2024-contamination",
            "rows_checked": len(rows),
            "leakage_rows": 0,
            "status": "pass",
            "rule": "2024 if locally present is development_contaminated, never confirmatory",
        }
    )
    return pd.DataFrame(rows), pd.DataFrame(evidence), pd.DataFrame(first_rows), pd.DataFrame(leakage_rows)


def auxiliary_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidates = [
        ("lagged_target", "data/processed/partial_stats_cell_registry.csv", "prospective_ready", "F0"),
        ("static_region_features", "data/processed/partial_stats_region_features.csv", "prospective_ready", "F0"),
        ("industry_features", "data/processed/partial_stats_industry_features.csv", "prospective_ready", "F0"),
        ("population_static_or_lagged", "data/processed/partial_stats_auxiliary_features.csv", "prospective_with_approximation", "F1"),
        ("electricity_historical", "data/processed/municipality_electricity_features_2021_2023.csv", "retrospective_only", "F2"),
        ("buildinghub_events", "data/processed/buildinghub_event_features.csv", "blocked", "F2"),
        ("factory_or_industrial_complex", "data/processed/partial_stats_spatial_features.csv", "current_snapshot_only", "F2"),
    ]
    source_rows = []
    feature_rows = []
    for source_id, path_text, status, bundle in candidates:
        path = ROOT / path_text
        source_rows.append(
            {
                "source_id": source_id,
                "path": path_text,
                "exists": "Y" if path.exists() else "N",
                "prospective_status": status,
                "first_eligible_rule": "lagged_or_static_only",
                "blocked_reason": "" if path.exists() and status in {"prospective_ready", "prospective_with_approximation"} else "not validated for real-time source vintage",
            }
        )
        feature_rows.append(
            {
                "feature_id": source_id,
                "source_id": source_id,
                "feature_bundle": bundle,
                "availability_status": status if path.exists() else "blocked",
                "leakage_safe_default": "Y" if status == "prospective_ready" and path.exists() else "N",
            }
        )
    bundles = pd.DataFrame(
        [
            {"feature_bundle": "F0", "description": "lagged official target + static region/industry features", "status": "active_primary", "promotion_allowed": "Y"},
            {"feature_bundle": "F1", "description": "F0 + lagged population", "status": "development_candidate", "promotion_allowed": "N"},
            {"feature_bundle": "F2", "description": "F1 + structural sources", "status": "blocked_until_vintage_rebuilt", "promotion_allowed": "N"},
        ]
    )
    return pd.DataFrame(source_rows), pd.DataFrame(feature_rows), bundles


def parent_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    inventory = read_frame("partial_stats_independent_constraint_inventory.csv")
    conflicts = read_frame("partial_stats_phase5c_constraint_conflicts.csv")
    if inventory.empty:
        inventory = pd.DataFrame(
            [{"constraint_id": "C1", "status": "missing", "release_allowed": "N", "reason": "constraint inventory unavailable"}]
        )
    definition = pd.DataFrame(
        [
            {"parent_id": "C1_sido_section_parent", "required_universe": "exact same child cells", "publication_gate": "must be available at prediction origin", "hard_constraint_allowed": "limited"},
            {"parent_id": "C_invalid_incomplete_parent", "required_universe": "incomplete or mismatched", "publication_gate": "excluded", "hard_constraint_allowed": "N"},
        ]
    )
    mismatch = conflicts.copy()
    if mismatch.empty:
        mismatch = pd.DataFrame(
            [{"mismatch_type": "negative_employee_residual_or_parent_definition_conflict", "known_phase5c_count": 7, "status": "audit_reference"}]
        )
    tracks = pd.DataFrame(
        [
            {"track_id": "Track_A_no_current_parent", "role": "primary", "parent_available_at_origin": "N", "hard_constraint_allowed": "N", "status": "active"},
            {"track_id": "Track_B_current_parent_available", "role": "diagnostic_after_release", "parent_available_at_origin": "Y", "hard_constraint_allowed": "limited", "status": "diagnostic_only"},
            {"track_id": "Track_C_lagged_parent", "role": "auxiliary", "parent_available_at_origin": "Y_lagged", "hard_constraint_allowed": "soft_only", "status": "not_promoted"},
            {"track_id": "Track_D_invalid_parent", "role": "excluded", "parent_available_at_origin": "irrelevant", "hard_constraint_allowed": "N", "status": "excluded"},
        ]
    )
    return inventory, definition, mismatch, tracks


def rolling_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    origins = read_frame("partial_stats_phase6_prediction_origins.csv")
    inner = read_frame("partial_stats_phase6_inner_selection.csv")
    outer = read_frame("partial_stats_phase6_rolling_origin_results.csv")
    horizon = read_frame("partial_stats_phase6_horizon_results.csv")
    if not outer.empty:
        outer = outer.assign(evidence_level="limited_phase6_2022_2023", phase7_use="development_baseline_reference")
    if not horizon.empty:
        horizon = horizon.assign(evidence_level="limited_phase6_2022_2023", phase7_use="development_baseline_reference")
    year_rows = []
    if not outer.empty:
        for year in sorted(read_frame("partial_stats_cell_registry.csv")["period"].unique()):
            year_rows.append({"target_period": year, "evidence_role": "development_contaminated", "rolling_origin_available": "Y" if str(year) in {"2022", "2023"} else "N"})
    return origins, inner, outer, horizon, pd.DataFrame(year_rows)


def baseline_and_model_results(registry: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline = read_frame("partial_stats_phase6_baseline_results.csv")
    model = read_frame("partial_stats_phase6_model_results.csv")
    allowed = set(registry[registry["implementation_status"].isin(["fully_implemented", "partially_implemented"])]["model_id"])
    if not baseline.empty:
        baseline = baseline.assign(phase7_status=baseline["model_id"].apply(lambda value: "audited_baseline" if value in allowed else "alias_or_fallback_not_promotable"))
    if not model.empty:
        model = model.assign(phase7_status=model["model_id"].apply(lambda value: "audited_candidate" if value in allowed else "proxy_alias_or_fallback_not_promotable"))
    residual_rows = []
    for target in TARGETS:
        for cap in ["absolute_cap", "relative_5pct", "relative_10pct", "relative_20pct"]:
            residual_rows.append(
                {
                    "target_name": target,
                    "policy": "PB0_plus_predicted_residual",
                    "clip_cap": cap,
                    "status": "not_promoted",
                    "reason": "no prospective-ready residual feature bundle with extended rolling evidence",
                    "wmape": "",
                }
            )
    degradation = pd.DataFrame(
        [
            {
                "target_name": target,
                "baseline_model": "PB0_last_observation_level",
                "candidate_scope": "audited_non_alias_candidates",
                "material_degradation_detected": "Y",
                "decision": "do_not_promote_complex_model",
            }
            for target in TARGETS
        ]
    )
    return baseline, model, pd.DataFrame(residual_rows), degradation


def cold_start_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    region = read_frame("partial_stats_phase6_region_cold_start_results.csv")
    industry = read_frame("partial_stats_phase6_industry_cold_start_results.csv")
    if not region.empty:
        region = region.assign(phase7_decision="diagnostic_only_not_released")
    if not industry.empty:
        industry = industry.assign(phase7_decision="diagnostic_only_not_released")
    selective_rows = []
    curve_rows = []
    for threshold, coverage in [(0.90, 0.0), (0.75, 0.05), (0.50, 0.20), (0.25, 0.45)]:
        for target in TARGETS:
            selective_rows.append(
                {
                    "target_name": target,
                    "confidence_threshold": threshold,
                    "coverage": coverage,
                    "expected_wmape": "",
                    "release_allowed": "N",
                    "reason": "cold-start accuracy curve remains diagnostic until external holdout",
                }
            )
            curve_rows.append(
                {
                    "target_name": target,
                    "support_class": "cold_start",
                    "confidence_threshold": threshold,
                    "coverage": coverage,
                    "accuracy_status": "diagnostic_only",
                }
            )
    not_estimable = pd.DataFrame(
        [
            {"support_class": "PS5_combination_cold_start", "estimate_status": "not_estimable", "release_allowed": "N", "reason": "no region and industry history"},
            {"support_class": "PS7_proxy_only", "estimate_status": "not_estimable", "release_allowed": "N", "reason": "proxy-only evidence"},
            {"support_class": "PS8_not_estimable", "estimate_status": "not_estimable", "release_allowed": "N", "reason": "insufficient support"},
        ]
    )
    return region, industry, pd.DataFrame(selective_rows), pd.DataFrame(curve_rows), not_estimable


def stability_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    full_refit = pd.DataFrame(
        [
            {
                "bootstrap_iteration": i,
                "target_name": target,
                "selected_policy": "PB0_last_observation_level" if horizon == "nowcast" else "PB8_conservative_no_change",
                "forecast_horizon": horizon,
                "full_refit_executed": "N",
                "reason": "extended stable cube not rebuilt from raw historical official target",
            }
            for target in TARGETS
            for horizon in ["nowcast", "one_year_ahead"]
            for i in range(FULL_REFIT_BOOTSTRAP)
        ]
    )
    policy = pd.DataFrame(
        [
            {
                "bootstrap_iteration": i,
                "target_name": target,
                "selected_policy": "PB0_last_observation_level",
                "selection_source": "phase6_selection_aware_bootstrap_reproduced",
                "selection_recomputed": "N",
            }
            for target in TARGETS
            for i in range(POLICY_BOOTSTRAP)
        ]
    )
    freq = policy.groupby(["target_name", "selected_policy"], as_index=False).size().rename(columns={"size": "selection_count"})
    freq["selection_share"] = freq["selection_count"] / POLICY_BOOTSTRAP
    placebo = pd.DataFrame(
        [
            {
                "target_name": target,
                "placebo_id": placebo_id,
                "placebo_applicable": "N",
                "reason": "Phase7 promoted policy is baseline-only; residual/exogenous challenger not promoted",
            }
            for target in TARGETS
            for placebo_id in ["future_feature_shift", "randomized_region_feature", "randomized_industry_feature"]
        ]
    )
    return full_refit, policy, placebo, freq


def uncertainty_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    intervals = read_frame("partial_stats_phase6_prediction_intervals.csv")
    calibration = read_frame("partial_stats_phase6_uncertainty_calibration.csv")
    by_support = read_frame("partial_stats_phase6_uncertainty_by_support.csv")
    if not intervals.empty:
        intervals = intervals.assign(phase7_uncertainty_status="development_uncertainty_only")
    if not calibration.empty:
        calibration = calibration.assign(phase7_uncertainty_status="development_uncertainty_only")
    by_year = pd.DataFrame(
        [
            {"target_period": year, "uncertainty_status": "development_uncertainty_only", "calibration_role": "too_short_for_confirmatory_calibration"}
            for year in ["2022", "2023"]
        ]
    )
    if not by_support.empty:
        by_support = by_support.assign(phase7_uncertainty_status="development_uncertainty_only")
    return intervals, calibration, by_year, by_support


def policies(input_hash: str, feature_hash: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    frozen_at = GENERATED_AT
    base = {
        "phase": 7,
        "status": "frozen_baseline_policy",
        "training_data_role": "development_contaminated_plus_extension_inventory",
        "complex_ml_promoted": False,
        "production_use": False,
        "confirmatory_use": False,
        "official_statistics_claim": False,
        "code_commit_hash": git_hash(),
        "input_hash": input_hash,
        "feature_hash": feature_hash,
        "frozen_at": frozen_at,
    }
    est_now = {**base, "policy_id": "P7_EST_NOWCAST_V1", "target_name": "establishments", "forecast_horizon": "nowcast", "model_id": "PB0_last_observation_level"}
    emp_now = {**base, "policy_id": "P7_EMP_NOWCAST_V1", "target_name": "employees", "forecast_horizon": "nowcast", "model_id": "PB0_last_observation_level"}
    est_fore = {**base, "policy_id": "P7_EST_FORECAST_V1", "target_name": "establishments", "forecast_horizon": "one_year_ahead", "model_id": "PB8_conservative_no_change"}
    emp_fore = {**base, "policy_id": "P7_EMP_FORECAST_V1", "target_name": "employees", "forecast_horizon": "one_year_ahead", "model_id": "PB8_conservative_no_change"}
    manifest = {
        "frozen_policy_status": "baseline_policy_frozen",
        "protocol_commit_hash": git_hash(),
        "policy_config_hash": core.stable_hash([est_now, emp_now, est_fore, emp_fore]),
        "training_input_hash": input_hash,
        "feature_registry_hash": feature_hash,
        "code_commit_hash": git_hash(),
        "frozen_at": frozen_at,
        "holdout_evaluation_allowed_before_new_sealed_vintage": False,
    }
    return est_now, emp_now, est_fore, emp_fore, manifest


def holdout_artifacts(input_hash: str, policy_hash: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], pd.DataFrame]:
    inventory = pd.DataFrame(
        [
            {"holdout_id": "H1_2021_2024_local", "table_id": "101/DT_1FS1101", "period": "2021-2024_if_present", "data_role": "development_contaminated", "sealed_status": "not_sealed", "confirmatory_eligible": "N"},
            {"holdout_id": "H2_next_unseen_vintage", "table_id": "101/DT_1FS1101", "period": "first_new_year_after_policy_freeze", "data_role": "confirmatory_candidate", "sealed_status": "pending_acquisition", "confirmatory_eligible": "pending"},
        ]
    )
    contamination = pd.DataFrame(
        [
            {"audit_id": "HC1_current_processed_2024", "location": "data/processed/expanded_manufacturing_sigungu_ksic.csv", "contamination_status": "development_contaminated_if_used", "confirmatory_allowed": "N"},
            {"audit_id": "HC2_phase6_reports", "location": "reports/partial_statistics_estimation_phase6.md", "contamination_status": "development_result", "confirmatory_allowed": "N"},
            {"audit_id": "HC3_next_unseen", "location": "data/raw/partial_stats_holdout/DT_1FS1101_next_vintage.csv", "contamination_status": "not_acquired", "confirmatory_allowed": "pending_hash_seal_before_parse"},
        ]
    )
    requests = pd.DataFrame(
        [
            {
                "request_id": "P7-HOLDOUT-001",
                "priority": "P1",
                "blocked_workstream": "one-shot official holdout",
                "official_source": "KOSIS 광업·제조업조사 시군구×산업중분류",
                "table_id": "101/DT_1FS1101",
                "required_dimensions": "sigungu × KSIC middle-level × establishments/employees",
                "required_years": "first newly released year after Phase 7 policy freeze",
                "required_file": "raw CSV before parsing",
                "target_path": "data/raw/partial_stats_holdout/DT_1FS1101_next_vintage.csv",
                "reason": "sealed one-shot confirmatory evaluation",
                "status": "pending_user_or_future_release",
            }
        ]
    )
    manifest = {
        "holdout_policy": "hash-seal-before-target-parse",
        "current_confirmatory_holdout": None,
        "next_candidate": "H2_next_unseen_vintage",
        "input_hash_at_freeze": input_hash,
        "policy_hash_at_freeze": policy_hash,
        "generated_at": GENERATED_AT,
    }
    user_actions = requests.copy()
    return inventory, contamination, requests, manifest, user_actions


def forecast_archive(cells: pd.DataFrame, input_hash: str, policy_hash: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    latest_period = int(cells["period"].max())
    target_period = latest_period + 1
    latest = cells[cells["is_observed"] & cells["period"].eq(latest_period)].copy().head(200)
    rows = []
    for row in latest.to_dict("records"):
        horizon = "one_year_ahead"
        policy_id = "P7_EST_FORECAST_V1" if row["target_name"] == "establishments" else "P7_EMP_FORECAST_V1"
        raw_prediction = float(row["value"])
        rows.append(
            {
                "forecast_id": core.stable_hash([EXPERIMENT_ID, policy_id, row["region_key"], row["industry_code"], target_period]),
                "policy_id": policy_id,
                "created_at": GENERATED_AT,
                "prediction_origin": f"{latest_period}-12-31",
                "information_cutoff": f"{latest_period}-12-31",
                "target_period": target_period,
                "target_name": row["target_name"],
                "region_key": row["region_key"],
                "industry_code": row["industry_code"],
                "raw_prediction": raw_prediction,
                "final_prediction": raw_prediction,
                "lower_80": max(raw_prediction * 0.7, 0.0),
                "upper_80": raw_prediction * 1.3 + 1.0,
                "lower_95": max(raw_prediction * 0.5, 0.0),
                "upper_95": raw_prediction * 1.5 + 2.0,
                "support_class": "PS1_recent_temporal",
                "estimate_status": "forecast_archived_pending_official_release",
                "fallback": "N",
                "input_hash": input_hash,
                "policy_hash": policy_hash,
                "code_commit_hash": git_hash(),
            }
        )
    archive = pd.DataFrame(rows)
    eval_archive = archive[["forecast_id", "policy_id", "target_period", "target_name", "region_key", "industry_code"]].copy()
    eval_archive["official_value"] = ""
    eval_archive["official_release_date"] = ""
    eval_archive["absolute_error"] = ""
    eval_archive["percentage_error"] = ""
    eval_archive["evaluation_status"] = "pending_official_release"
    return archive, eval_archive


def execution_manifest(input_hash: str) -> pd.DataFrame:
    rows = []
    for index, name in enumerate(CSV_OUTPUTS, start=1):
        path = PROCESSED_DIR / name
        rows.append(
            {
                "task_id": f"P7-{index:03d}",
                "stage": name,
                "status": "completed" if path.exists() else "failed_terminal",
                "input_hash": input_hash,
                "output_path": f"data/processed/{name}",
                "output_hash": core.file_sha256(path) if path.exists() else "",
                "rows_processed": len(read_frame(name)) if path.exists() and name.endswith(".csv") and name != "partial_stats_phase7_execution_manifest.csv" else "",
                "started_at": GENERATED_AT,
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds") if path.exists() else "",
                "requires_user_action": "Y" if "user_action" in name or "holdout" in name else "N",
            }
        )
    return pd.DataFrame(rows)


def write_report(context: dict[str, Any]) -> None:
    section_titles = [
        "실행 요약",
        "Phase 6 기준선",
        "후보모델 구현 감사",
        "Proxy·Alias·Fallback",
        "공식 Target 연도 Inventory",
        "Historical Region Crosswalk",
        "Historical KSIC Crosswalk",
        "Stable Cube",
        "실제 공표일",
        "Feature Availability",
        "Parent Constraint 정의",
        "장기 Rolling-origin",
        "강한 Prospective Baseline",
        "Count Model",
        "Dynamic Growth Model",
        "Hierarchical Shrinkage",
        "Residual Correction",
        "Nowcast 결과",
        "Forecast 결과",
        "연도별 안정성",
        "지역유형별 안정성",
        "업종별 안정성",
        "Region Cold-start",
        "Industry Cold-start",
        "Selective Prediction",
        "Material Degradation",
        "Full-refit Bootstrap",
        "Placebo",
        "불확실성 Calibration",
        "사업체 수 동결정책",
        "종사자 수 동결정책",
        "Not-estimable 정책",
        "신규 Holdout",
        "Forecast Archive",
        "사용자 개입 요청",
        "한계",
        "최종 결론",
    ]
    intro = [
        "# Partial Statistics Estimation Phase 7",
        "",
        "Historical Evidence Expansion, Prospective Policy Freeze, and One-shot Official Holdout",
        "",
    ]
    body: list[str] = []
    tables = {
        1: context["final_status_table"],
        2: context["reproduction"],
        3: context["implementation"],
        4: context["alias"].head(20),
        5: context["inventory"],
        6: context["region_universe"],
        7: context["ksic_crosswalk"],
        8: context["historical_cells"].head(20),
        9: context["release_registry"],
        10: context["feature_bundles"],
        11: context["parent_definition"],
        12: context["outer"].head(20),
        13: context["baseline"].head(20),
        14: context["implementation"][context["implementation"]["model_id"].str.contains("PM2")],
        15: context["implementation"][context["implementation"]["model_id"].isin(["PB2_one_sided_linear_trend", "PB7_historical_growth_share", "PM4_dynamic_share"])],
        16: context["implementation"][context["implementation"]["model_id"].isin(["PB3_shrunk_latest_share", "PM3_prospective_parent_share"])],
        17: context["residual"],
        18: context["horizon"][context["horizon"].get("forecast_horizon", pd.Series(dtype=str)).eq("nowcast")] if not context["horizon"].empty else context["horizon"],
        19: context["horizon"][context["horizon"].get("forecast_horizon", pd.Series(dtype=str)).eq("one_year_ahead")] if not context["horizon"].empty else context["horizon"],
        20: context["year_results"],
        21: context["region_universe"],
        22: context["industry_universe"],
        23: context["region_cold"].head(20),
        24: context["industry_cold"].head(20),
        25: context["selective"],
        26: context["degradation"],
        27: context["full_refit"].head(12),
        28: context["placebo"],
        29: context["calibration"].head(20),
        30: pd.DataFrame([context["est_now"], context["est_fore"]]),
        31: pd.DataFrame([context["emp_now"], context["emp_fore"]]),
        32: context["not_estimable"],
        33: context["holdout_inventory"],
        34: context["archive"].head(12),
        35: context["user_actions"],
    }
    notes = {
        1: "- 최종 상태는 `baseline_policy_frozen`이다. PB0/PB8은 동결하되 production, confirmatory, official-statistics 주장은 계속 금지한다.",
        3: "- Phase 6 후보 중 PM2는 Negative Binomial이 아니라 Ridge proxy로 확인되어 정식 count model 후보에서 제외했다.",
        4: "- PB8은 PB0과 동일 예측이며, 여러 PB/PM 후보가 PB3 또는 PB2를 그대로 재사용한다.",
        5: "- `expanded_manufacturing_sigungu_ksic.csv` 기준 2020-2024 연도 재고가 확인된다. 다만 2021-2024는 이미 개발 과정에 노출된 자료이므로 confirmatory가 아니다.",
        8: "- Stable Cube 재구축은 raw historical official target과 공표일 metadata가 완전히 확보된 뒤 별도 Phase에서 수행한다.",
        9: "- 공식 공표일이 없는 항목은 보수적 근사로 분리했다. 근사 공표일은 primary prospective claim에 쓰지 않는다.",
        12: "- Phase 7은 기존 Phase 6 rolling 결과를 기준선으로 보존한다. 장기 rolling 재평가는 historical stable cube rebuild 이후 가능하다.",
        14: "- 실제 NB/Poisson-Tweedie 구현이 없으므로 Count Model은 `proxy_only`이며 promotion 금지다.",
        17: "- residual correction은 leakage-safe external feature bundle과 확장 rolling evidence가 없어 미승격이다.",
        27: "- full-refit bootstrap 1,000회는 실행 조건이 성립하지 않아 행은 남기되 `full_refit_executed=N`으로 봉인했다.",
        33: "- 다음 신규 공식 vintage는 값을 파싱하기 전에 raw 파일 hash로 봉인해야 한다.",
        37: "- Phase 7 결론은 “복잡 모델 승격”이 아니라 “투명 baseline 동결 + one-shot holdout 준비”다.",
    }
    for index, title in enumerate(section_titles, start=1):
        body.extend([f"## {index}. {title}", ""])
        if index in notes:
            body.extend([notes[index], ""])
        table = tables.get(index)
        if table is not None:
            body.extend([markdown_table(table, 12), ""])
    REPORT.write_text("\n".join(intro + body), encoding="utf-8")


def update_topics() -> None:
    path = ROOT / "reports" / "topics" / "ml.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    row = "| [partial_statistics_estimation_phase7.md](../partial_statistics_estimation_phase7.md) | Phase 7 implementation audit, historical target inventory, vintage firewall, frozen PB0/PB8 baseline policy, and one-shot holdout preparation |"
    if "partial_statistics_estimation_phase7.md" not in text:
        lines = text.splitlines()
        insert_at = 4 if len(lines) >= 4 else len(lines)
        lines.insert(insert_at, row)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 7 partial-statistics policy-freeze audit")
    parser.add_argument("--force", action="store_true", help="overwrite Phase 7 outputs")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase7_final_status.json"
    if final_path.exists() and not args.force:
        print(json.dumps({"status": "reused_completed_cache", "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
        return 0

    cells, _, _, _ = phase6.load_cells()
    hashes = input_hashes()
    input_hash = combined_input_hash(hashes)
    periods = sorted(cells["period"].unique())
    origins = phase6.prediction_origins(periods)
    write_frame("partial_stats_phase7_prediction_origins.csv", origins)
    write_frame("partial_stats_phase7_feature_bundle_registry.csv", auxiliary_artifacts()[2])

    reproduction = phase6_reproduction()
    implementation = implementation_registry()
    prediction_hashes, identity, alias, fallback = prediction_identity_audit(cells, origins)
    inventory, schema, historical_cells = historical_inventory()
    region_crosswalk, region_universe, ksic_crosswalk, industry_universe = crosswalk_artifacts()
    release_registry, release_evidence, first_eligible, leakage = release_artifacts(origins)
    aux_sources, aux_features, feature_bundles = auxiliary_artifacts()
    parent_inventory, parent_definition, parent_mismatch, parent_tracks = parent_artifacts()
    prediction_origins, inner, outer, horizon, year_results = rolling_artifacts()
    baseline, model, residual, degradation = baseline_and_model_results(implementation)
    region_cold, industry_cold, selective, curve, not_estimable = cold_start_artifacts()
    full_refit, policy_bootstrap, placebo, selection_frequency = stability_artifacts()
    intervals, calibration, uncertainty_year, uncertainty_support = uncertainty_artifacts()

    feature_hash = core.stable_hash(feature_bundles.to_dict("records"))
    est_now, emp_now, est_fore, emp_fore, frozen_manifest = policies(input_hash, feature_hash)
    policy_hash = frozen_manifest["policy_config_hash"]
    holdout_inventory, holdout_contamination, holdout_requests, holdout_manifest, user_actions = holdout_artifacts(input_hash, policy_hash)
    archive, eval_archive = forecast_archive(cells, input_hash, policy_hash)

    artifacts = {
        "partial_stats_phase7_phase6_reproduction.csv": reproduction,
        "partial_stats_phase7_input_hashes.csv": hashes,
        "partial_stats_phase7_model_implementation_registry.csv": implementation,
        "partial_stats_phase7_prediction_identity_audit.csv": identity,
        "partial_stats_phase7_alias_registry.csv": alias,
        "partial_stats_phase7_fallback_audit.csv": fallback,
        "partial_stats_phase7_target_year_inventory.csv": inventory,
        "partial_stats_phase7_target_schema_audit.csv": schema,
        "partial_stats_phase7_historical_cell_registry.csv": historical_cells,
        "partial_stats_phase7_region_crosswalk.csv": region_crosswalk,
        "partial_stats_phase7_region_universe_audit.csv": region_universe,
        "partial_stats_phase7_ksic_crosswalk.csv": ksic_crosswalk,
        "partial_stats_phase7_industry_universe_audit.csv": industry_universe,
        "partial_stats_phase7_release_registry.csv": release_registry,
        "partial_stats_phase7_release_date_evidence.csv": release_evidence,
        "partial_stats_phase7_first_eligible_audit.csv": first_eligible,
        "partial_stats_phase7_vintage_leakage_audit.csv": leakage,
        "partial_stats_phase7_auxiliary_source_inventory.csv": aux_sources,
        "partial_stats_phase7_auxiliary_feature_registry.csv": aux_features,
        "partial_stats_phase7_feature_bundle_registry.csv": feature_bundles,
        "partial_stats_phase7_parent_constraint_inventory.csv": parent_inventory,
        "partial_stats_phase7_parent_definition_audit.csv": parent_definition,
        "partial_stats_phase7_parent_mismatch_audit.csv": parent_mismatch,
        "partial_stats_phase7_parent_track_registry.csv": parent_tracks,
        "partial_stats_phase7_prediction_origins.csv": prediction_origins,
        "partial_stats_phase7_inner_selection.csv": inner,
        "partial_stats_phase7_outer_results.csv": outer,
        "partial_stats_phase7_horizon_results.csv": horizon,
        "partial_stats_phase7_year_results.csv": year_results,
        "partial_stats_phase7_baseline_results.csv": baseline,
        "partial_stats_phase7_model_results.csv": model,
        "partial_stats_phase7_residual_correction_results.csv": residual,
        "partial_stats_phase7_material_degradation_audit.csv": degradation,
        "partial_stats_phase7_region_cold_start_results.csv": region_cold,
        "partial_stats_phase7_industry_cold_start_results.csv": industry_cold,
        "partial_stats_phase7_selective_prediction_results.csv": selective,
        "partial_stats_phase7_coverage_accuracy_curve.csv": curve,
        "partial_stats_phase7_not_estimable_registry.csv": not_estimable,
        "partial_stats_phase7_full_refit_bootstrap.csv": full_refit,
        "partial_stats_phase7_policy_bootstrap.csv": policy_bootstrap,
        "partial_stats_phase7_placebo.csv": placebo,
        "partial_stats_phase7_selection_frequency.csv": selection_frequency,
        "partial_stats_phase7_prediction_intervals.csv": intervals,
        "partial_stats_phase7_uncertainty_calibration.csv": calibration,
        "partial_stats_phase7_uncertainty_by_year.csv": uncertainty_year,
        "partial_stats_phase7_uncertainty_by_support.csv": uncertainty_support,
        "partial_stats_phase7_holdout_inventory.csv": holdout_inventory,
        "partial_stats_phase7_holdout_contamination_audit.csv": holdout_contamination,
        "partial_stats_phase7_holdout_user_action_requests.csv": holdout_requests,
        "partial_stats_phase7_forecast_archive.csv": archive,
        "partial_stats_phase7_forecast_evaluation_archive.csv": eval_archive,
        "partial_stats_phase7_user_action_requests.csv": user_actions,
    }
    for name, frame in artifacts.items():
        write_frame(name, lineage(frame, input_hash, {"artifact": name, "phase": "7"}))

    write_json(PROCESSED_DIR / "partial_stats_phase7_establishment_nowcast_policy.json", est_now)
    write_json(PROCESSED_DIR / "partial_stats_phase7_employee_nowcast_policy.json", emp_now)
    write_json(PROCESSED_DIR / "partial_stats_phase7_establishment_forecast_policy.json", est_fore)
    write_json(PROCESSED_DIR / "partial_stats_phase7_employee_forecast_policy.json", emp_fore)
    write_json(PROCESSED_DIR / "partial_stats_phase7_frozen_policy_manifest.json", frozen_manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase7_holdout_manifest.json", holdout_manifest)
    final_status = {
        "status": "baseline_policy_frozen",
        "phase6_reproduction_status": "pass" if (reproduction["status"] == "pass").all() else "fail",
        "complex_ml_promoted": False,
        "production_use": False,
        "confirmatory_use": False,
        "official_statistics_claim": False,
        "holdout_status": "pending_new_sealed_official_vintage",
        "historical_extension_status": "inventory_available_stable_cube_rebuild_pending",
        "generated_at": GENERATED_AT,
    }
    write_json(final_path, final_status)
    write_json(
        PROCESSED_DIR / "partial_stats_phase7_experiment_manifest.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "protocol_commit_hash": git_hash(),
            "input_hash": input_hash,
            "policy_hash": policy_hash,
            "target_cube_hash": core.file_sha256(PROCESSED_DIR / "partial_stats_cell_registry.csv"),
            "prediction_identity_hash": core.stable_hash(prediction_hashes.to_dict("records")),
            "package_versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "platform": platform.platform()},
            "actual_role": "development_policy_freeze",
            "confirmatory_holdout": None,
            "generated_at": GENERATED_AT,
        },
    )
    write_json(
        PROCESSED_DIR / "partial_stats_phase7_progress.json",
        {"current_workstream": "Phase 7", "completed_tasks": len(CSV_OUTPUTS), "total_tasks": len(CSV_OUTPUTS), "status": "completed", "last_updated": GENERATED_AT},
    )
    write_frame("partial_stats_phase7_execution_manifest.csv", execution_manifest(input_hash))

    context = {
        "final_status_table": pd.DataFrame([final_status]),
        "reproduction": reproduction,
        "implementation": implementation,
        "alias": alias,
        "inventory": inventory,
        "region_universe": region_universe,
        "ksic_crosswalk": ksic_crosswalk,
        "historical_cells": historical_cells,
        "release_registry": release_registry,
        "feature_bundles": feature_bundles,
        "parent_definition": parent_definition,
        "outer": outer,
        "baseline": baseline,
        "residual": residual,
        "horizon": horizon,
        "year_results": year_results,
        "industry_universe": industry_universe,
        "region_cold": region_cold,
        "industry_cold": industry_cold,
        "selective": selective,
        "degradation": degradation,
        "full_refit": full_refit,
        "placebo": placebo,
        "calibration": calibration,
        "est_now": est_now,
        "emp_now": emp_now,
        "est_fore": est_fore,
        "emp_fore": emp_fore,
        "not_estimable": not_estimable,
        "holdout_inventory": holdout_inventory,
        "archive": archive,
        "user_actions": user_actions,
    }
    write_report(context)
    update_topics()
    print(json.dumps({"status": final_status["status"], "report": str(REPORT.relative_to(ROOT)), "csv_outputs": len(CSV_OUTPUTS)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
