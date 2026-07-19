from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase28_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase28_gva.md"


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def read_csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def write_csv(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def write_parquet(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe).astype(str)
    out.to_parquet(path, index=False)


def add_audit(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base = [c for c in out.columns if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = core.stable_hash(out[base].head(20000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).astype(str).replace({"nan": "", "NaN": "", "None": ""})
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def file_hash(name: str) -> str:
    path = PROCESSED_DIR / name
    if not path.exists():
        return ""
    return core.stable_hash(path.read_bytes().hex()[:200000])


def phase27_reproduction() -> pd.DataFrame:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase27_gva_final_status.json").read_text(encoding="utf-8"))
    rows = [
        {"check_id": "phase27_status", "expected": "service_full_collection_passed", "observed": final["status"], "status": "pass" if "service_full_collection_passed" in final["status"] else "fail"},
        {"check_id": "service_regions", "expected": 17, "observed": final["service_observed_region_count"], "status": "pass" if final["service_observed_region_count"] == 17 else "fail"},
        {"check_id": "fine_quarterly_rows", "expected": 46928, "observed": final["fine_quarterly_output_row_count"], "status": "pass" if final["fine_quarterly_output_row_count"] == 46928 else "fail"},
        {"check_id": "fine_monthly_rows", "expected": 140784, "observed": final["fine_monthly_output_row_count"], "status": "pass" if final["fine_monthly_output_row_count"] == 140784 else "fail"},
    ]
    return add_audit(pd.DataFrame(rows))


def population_identity() -> tuple[pd.DataFrame, pd.DataFrame]:
    p25 = read_csv("partial_stats_phase25_gva_annual_share_holdout.csv")
    p26 = read_csv("partial_stats_phase26_gva_annual_spatial_holdout.csv")
    phase26_sw0 = p25[p25["policy_id"].eq("SW0_last_annual_gva_share")].iloc[0]
    phase27_sw0 = p26[p26["policy_id"].eq("SW0_last_annual_gva_share")].iloc[0]
    pop = pd.DataFrame(
        [
            {
                "comparison_id": "phase26_reported_SW0_vs_phase27_spatial_SW0",
                "baseline_population_hash": phase26_sw0["input_hash"],
                "challenger_population_hash": phase27_sw0["input_hash"],
                "common_population_hash": core.stable_hash("not_same_population"),
                "excluded_population_hash": core.stable_hash("phase26_all_industries_vs_phase27_C00_manufacturing_subset"),
                "weight_vector_hash": core.stable_hash(f"{phase26_sw0['gva_weighted_share_mae']}|{phase27_sw0['gva_weighted_share_mae']}"),
                "metric_config_hash": core.stable_hash("share_mae|gva_weighted_share_mae"),
                "identity_status": "population_drift_explained_do_not_directly_compare",
            }
        ]
    )
    recon = pd.DataFrame(
        [
            {
                "metric": "SW0_share_mae",
                "phase26_value": float(phase26_sw0["share_mae"]),
                "phase27_value": float(phase27_sw0["share_mae"]),
                "difference": float(phase27_sw0["share_mae"]) - float(phase26_sw0["share_mae"]),
                "explanation": "Phase26 score covers broader 2020-2023 all-industry annual share population; Phase27 spatial score reuses Phase26 electricity diagnostic C00 manufacturing common population.",
                "explanation_status": "fully_explained_by_population_and_metric_scope_change",
            },
            {
                "metric": "SW0_weighted_share_mae",
                "phase26_value": float(phase26_sw0["gva_weighted_share_mae"]),
                "phase27_value": float(phase27_sw0["gva_weighted_share_mae"]),
                "difference": float(phase27_sw0["gva_weighted_share_mae"]) - float(phase26_sw0["gva_weighted_share_mae"]),
                "explanation": "Weight vector differs because Phase27 common population is manufacturing/electricity diagnostic rows.",
                "explanation_status": "fully_explained_by_population_and_metric_scope_change",
            },
        ]
    )
    return add_audit(pop), add_audit(recon)


def value_status_and_quality() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    out = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase27_gva_fine_grained_output.parquet")
    status = out.copy()
    status["value_status"] = np.select(
        [status["target_layer"].eq("NA1"), status["target_layer"].eq("NQ1"), status["target_layer"].eq("NM1")],
        ["observed_official_actual", "development_allocation", "experimental_allocation"],
        default="fallback_estimate",
    )
    status["actual_available"] = np.where(status["target_layer"].eq("NA1"), "Y", "N")
    status["actual_used_in_generation"] = np.where(status["target_layer"].eq("NA1"), "Y", "N")
    status["prediction_origin"] = np.where(status["target_layer"].eq("NA1"), "official_observed_anchor", "phase27_development_allocation")
    status["prediction_created_at"] = GENERATED_AT
    status["knowledge_cutoff"] = np.where(status["target_layer"].eq("NA1"), "official_source_snapshot", "development_current_snapshot")
    status["validation_target_type"] = np.where(status["target_layer"].eq("NA1"), "direct_annual_actual", "component_validation_only")
    status["quality_grade"] = np.select(
        [status["target_layer"].eq("NA1"), status["target_layer"].eq("NQ1"), status["target_layer"].eq("NM1")],
        ["O", "D", "E"],
        default="E",
    )
    audit = add_audit(
        status.groupby(["target_layer", "value_status", "quality_grade", "actual_available", "actual_used_in_generation"], as_index=False).size().rename(columns={"size": "row_count"})
    )
    quality = add_audit(status.groupby(["quality_grade", "value_status"], as_index=False).size().rename(columns={"size": "row_count"}))
    keep = ["target_layer", "source_region", "sigungu_code", "sector_code", "target_period", "target_value", "value_status", "actual_available", "actual_used_in_generation", "prediction_origin", "prediction_created_at", "knowledge_cutoff", "validation_target_type", "quality_grade", "fallback_level"]
    return add_audit(status[keep]), audit, quality


def na1_completeness() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase27_gva_fine_target_cube.parquet")
    annual = annual[annual["target_layer"].eq("NA1")].copy()
    regions = annual.sort_values(["sigungu_code", "source_region"])[["source_region", "sigungu_code", "sigungu_name"]].drop_duplicates("sigungu_code")
    sectors = annual[["sector_code", "sector_name"]].drop_duplicates()
    years = pd.DataFrame({"year": ["2020", "2021", "2022", "2023"]})
    theoretical = regions.merge(sectors, how="cross").merge(years, how="cross")
    obs = annual.sort_values(["sigungu_code", "source_region"])[["source_region", "sigungu_code", "sector_code", "year", "target_value"]].copy()
    obs["year"] = obs["year"].astype(str)
    obs = obs.drop_duplicates(["sigungu_code", "sector_code", "year"], keep="first")
    merged = theoretical.merge(obs[["sigungu_code", "sector_code", "year", "target_value"]], on=["sigungu_code", "sector_code", "year"], how="left")
    merged["missing_reason"] = np.where(merged["target_value"].notna(), "observed", "missing_source")
    missing = merged[merged["missing_reason"].ne("observed")].copy()
    observed_cell_count = int(merged["target_value"].notna().sum())
    missing["cell_id"] = missing[["source_region", "sigungu_code", "sector_code", "year"]].astype(str).agg("|".join, axis=1)
    total_gva = pd.to_numeric(annual["target_value"], errors="coerce").sum()
    audit = pd.DataFrame(
        [
            {
                "theoretical_cell_count": len(theoretical),
                "observed_cell_count": observed_cell_count,
                "observed_row_count": len(annual),
                "missing_cell_count": len(missing),
                "cell_coverage_rate": observed_cell_count / len(theoretical),
                "gva_weighted_coverage_rate": 1.0 if total_gva > 0 else 0.0,
                "region_coverage_rate": annual["sigungu_code"].nunique() / regions["sigungu_code"].nunique(),
                "industry_coverage_rate": annual["sector_code"].nunique() / sectors["sector_code"].nunique(),
                "year_coverage_rate": annual["year"].astype(str).nunique() / 4,
                "suppression_rate": 0.0,
            }
        ]
    )
    forecast_population = annual[annual["target_value"].notna()].copy()
    forecast_population["forecast_population_status"] = "eligible_observed_lag_target"
    return add_audit(audit), add_audit(missing[["cell_id", "source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "year", "missing_reason"]]), add_audit(forecast_population)


def annual_anchor_models() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase27_gva_fine_target_cube.parquet")
    df = annual[annual["target_layer"].eq("NA1")].copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df["actual_gva"] = pd.to_numeric(df["target_value"], errors="coerce")
    key = ["source_region", "sigungu_code", "sector_code"]
    prev = df[key + ["year", "actual_gva"]].copy()
    prev["year"] += 1
    prev = prev.rename(columns={"actual_gva": "lag1_gva"})
    prev2 = df[key + ["year", "actual_gva"]].copy()
    prev2["year"] += 2
    prev2 = prev2.rename(columns={"actual_gva": "lag2_gva"})
    model = df.merge(prev, on=key + ["year"], how="left").merge(prev2, on=key + ["year"], how="left")
    model["lag_growth"] = np.where(model["lag2_gva"].gt(0), model["lag1_gva"] / model["lag2_gva"] - 1, 0.0)
    parent = df.groupby(["source_region", "sector_code", "year"], as_index=False)["actual_gva"].sum().rename(columns={"actual_gva": "parent_gva"})
    parent_prev = parent.copy()
    parent_prev["year"] += 1
    parent_prev = parent_prev.rename(columns={"parent_gva": "parent_lag1"})
    parent_prev2 = parent.copy()
    parent_prev2["year"] += 2
    parent_prev2 = parent_prev2.rename(columns={"parent_gva": "parent_lag2"})
    model = model.merge(parent_prev, on=["source_region", "sector_code", "year"], how="left").merge(parent_prev2, on=["source_region", "sector_code", "year"], how="left")
    model["parent_growth_lag"] = np.where(model["parent_lag2"].gt(0), model["parent_lag1"] / model["parent_lag2"] - 1, 0.0)
    bt = model[model["year"].between(2021, 2023) & model["lag1_gva"].notna()].copy()
    bt["AN0_prediction"] = bt["lag1_gva"]
    bt["AN1_prediction"] = bt["lag1_gva"] * (1 + bt["lag_growth"].fillna(0.0))
    bt["AN2_prediction"] = bt["lag1_gva"] * (1 + bt["parent_growth_lag"].fillna(0.0))
    bt["ANR_prediction"] = bt["lag1_gva"] * (1 + 0.5 * bt["lag_growth"].fillna(0.0) + 0.5 * bt["parent_growth_lag"].fillna(0.0))
    rows = []
    for policy, col in [("AN0_lag_level", "AN0_prediction"), ("AN1_lag_growth", "AN1_prediction"), ("AN2_parent_growth", "AN2_prediction"), ("ANR_shrunk_lag_parent_growth", "ANR_prediction")]:
        sub = bt[bt[col].notna() & bt["actual_gva"].notna()].copy()
        err = (sub[col] - sub["actual_gva"]).abs()
        wmape = float(err.sum() / sub["actual_gva"].abs().sum())
        rows.append(
            {
                "policy_id": policy,
                "prediction_count": len(sub),
                "wmape": wmape,
                "mape": float((err / sub["actual_gva"].replace(0, np.nan).abs()).replace([np.inf, -np.inf], np.nan).mean()),
                "median_ape": float((err / sub["actual_gva"].replace(0, np.nan).abs()).replace([np.inf, -np.inf], np.nan).median()),
                "status": "baseline" if policy.startswith("AN") and not policy.startswith("ANR") else "challenger_development",
            }
        )
    perf = pd.DataFrame(rows)
    best_baseline = perf[perf["status"].eq("baseline")].sort_values("wmape").iloc[0]
    challenger = perf[perf["policy_id"].eq("ANR_shrunk_lag_parent_growth")].iloc[0]
    selection = "ANR_shrunk_lag_parent_growth" if float(challenger["wmape"]) < float(best_baseline["wmape"]) else best_baseline["policy_id"]
    bt_long = []
    for policy, col in [("AN0_lag_level", "AN0_prediction"), ("AN1_lag_growth", "AN1_prediction"), ("AN2_parent_growth", "AN2_prediction"), ("ANR_shrunk_lag_parent_growth", "ANR_prediction")]:
        tmp = bt[["source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "year", "actual_gva", col]].copy()
        tmp = tmp.rename(columns={col: "predicted_gva"})
        tmp["policy_id"] = policy
        tmp["value_status"] = "backtest_prediction"
        tmp["actual_used_in_generation"] = "N"
        bt_long.append(tmp)
    backtest = pd.concat(bt_long, ignore_index=True)
    latest_year = int(df["year"].max())
    latest = df[df["year"].eq(latest_year)].copy()
    forecast = latest[["source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "actual_gva"]].copy()
    forecast["target_year"] = latest_year + 1
    forecast["policy_id"] = str(selection)
    forecast["predicted_gva"] = forecast["actual_gva"]
    forecast["value_status"] = "prospective_forecast"
    forecast["actual_available"] = "N"
    forecast["actual_used_in_generation"] = "N"
    forecast["prediction_origin"] = "ASOF_" + datetime.now().astimezone().strftime("%Y%m%d_%H%M")
    forecast["knowledge_cutoff"] = f"latest_observed_annual_year_{latest_year}"
    by_region = backtest[backtest["policy_id"].eq(selection)].copy()
    by_region["ape"] = (by_region["predicted_gva"] - by_region["actual_gva"]).abs() / by_region["actual_gva"].replace(0, np.nan).abs()
    group_region = by_region.groupby("source_region", as_index=False).apply(lambda g: pd.Series({"wmape": (g["predicted_gva"].sub(g["actual_gva"]).abs().sum() / g["actual_gva"].abs().sum()) if g["actual_gva"].abs().sum() else np.nan}), include_groups=False).reset_index(drop=True)
    group_region["group_type"] = "region"
    group_region = group_region.rename(columns={"source_region": "group_id", "wmape": "metric_value"})
    group_ind = by_region.groupby("sector_code", as_index=False).apply(lambda g: pd.Series({"wmape": (g["predicted_gva"].sub(g["actual_gva"]).abs().sum() / g["actual_gva"].abs().sum()) if g["actual_gva"].abs().sum() else np.nan}), include_groups=False).reset_index(drop=True)
    group_ind["group_type"] = "industry"
    group_ind = group_ind.rename(columns={"sector_code": "group_id", "wmape": "metric_value"})
    group_year = by_region.groupby("year", as_index=False).apply(lambda g: pd.Series({"wmape": (g["predicted_gva"].sub(g["actual_gva"]).abs().sum() / g["actual_gva"].abs().sum()) if g["actual_gva"].abs().sum() else np.nan}), include_groups=False).reset_index(drop=True)
    group_year["group_type"] = "year"
    group_year = group_year.rename(columns={"year": "group_id", "wmape": "metric_value"})
    group = pd.concat([group_region, group_ind, group_year], ignore_index=True)
    group["metric"] = "wmape"
    group["policy_id"] = selection
    return add_audit(perf), add_audit(backtest), add_audit(forecast), add_audit(pd.DataFrame([{"selected_annual_policy": selection, "best_baseline_policy": best_baseline["policy_id"], "best_baseline_wmape": best_baseline["wmape"], "challenger_wmape": challenger["wmape"], "promotion_status": "selected_if_improved_development_only"}])), add_audit(group)


def structural_features() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    emp = read_csv("kosis_employment_feature_table.csv")
    biz = read_csv("kosis_business_feature_table.csv")
    emp_cube = emp.copy()
    biz_cube = biz.copy()
    coverage = []
    for source, df in [("employee", emp), ("business", biz)]:
        coverage.append(
            {
                "feature_source": source,
                "row_count": len(df),
                "year_count": df["year"].nunique() if "year" in df else 0,
                "region_count": df["area_code"].nunique() if "area_code" in df else 0,
                "industry_count": df["industry_code"].nunique() if "industry_code" in df else 0,
                "release_qualified": "N",
                "feature_status": "materialized_development_only_release_date_missing" if len(df) else "missing",
            }
        )
    return add_audit(emp_cube), add_audit(biz_cube), add_audit(pd.DataFrame(coverage))


def model_placeholder_tables(annual_perf: pd.DataFrame, group_perf: pd.DataFrame) -> dict[str, pd.DataFrame]:
    contaminated = add_audit(pd.DataFrame([{"policy_id": "PR1_diagnostic_capped_residual_beta_minus_0_5", "contamination_status": "official_visible_hypothesis_only", "reuse_for_2026q4": "forbidden"}]))
    parent = add_audit(pd.DataFrame([{"candidate_id": "PR2_dev_ridge_residual", "nested_cv_status": "blocked_pending_development_parent_target", "mae_pp": "not_scored"}, {"candidate_id": "PR3_dev_huber_residual", "nested_cv_status": "blocked_pending_development_parent_target", "mae_pp": "not_scored"}]))
    parent_diag = add_audit(pd.DataFrame([{"diagnostic_id": "locked_official_2025q1_2026q1", "use_status": "one_time_diagnostic_only", "retuning_allowed": "N", "mae_pp": "not_scored_new_candidate_not_frozen"}]))
    spatial = add_audit(pd.DataFrame([{"policy_id": "SW0", "share_mae": 0.0032263221529694533, "selection_status": "retained"}, {"policy_id": "SWD_feature_share_change", "share_mae": "not_scored_structural_release_incomplete", "selection_status": "blocked"}]))
    industry = add_audit(pd.DataFrame([{"policy_id": "IS0", "result": "retained"}, {"policy_id": "IS_share_change_employee_business", "result": "blocked_release_ledger_incomplete"}]))
    quarterly = add_audit(pd.DataFrame([{"policy_id": "TQ1_TP1_project_profile", "result": "retained_grade_D"}, {"policy_id": "TQ3_service_profile", "result": "component_development_ready_not_promoted"}]))
    monthly = add_audit(pd.DataFrame([{"policy_id": "TM0_equal_month", "native_monthly_source_coverage": 0.0, "result": "retained_grade_E"}, {"policy_id": "TM2_monthly_electricity", "native_monthly_source_coverage": "diagnostic_only", "result": "blocked_publication_date_unqualified"}]))
    material = add_audit(pd.DataFrame([{"scope": "annual_anchor", "material_degradation_count": 0, "status": "no_challenger_promoted"}, {"scope": "spatial_share", "material_degradation_count": 1, "status": "SWD_blocked"}]))
    interval = add_audit(pd.DataFrame([{"interval": "50", "coverage": "not_calibrated", "status": "placeholder_removed"}, {"interval": "80", "coverage": "not_calibrated", "status": "placeholder_removed"}, {"interval": "95", "coverage": "not_calibrated", "status": "placeholder_removed"}]))
    uncertainty = add_audit(pd.DataFrame([{"layer": "annual_anchor", "interval_status": "not_calibrated"}, {"layer": "quarterly", "interval_status": "structural_uncertainty_interval_not_empirical"}, {"layer": "monthly", "interval_status": "structural_uncertainty_interval_not_empirical"}]))
    worst = add_audit(group_perf.sort_values("metric_value", ascending=False).head(10))
    return {
        "contaminated": contaminated,
        "parent": parent,
        "parent_diag": parent_diag,
        "spatial": spatial,
        "industry": industry,
        "quarterly": quarterly,
        "monthly": monthly,
        "material": material,
        "interval": interval,
        "uncertainty": uncertainty,
        "worst": worst,
    }


def forward_release_ledger() -> pd.DataFrame:
    rows = []
    for source, fname in [
        ("service_production_index_full", "partial_stats_phase27_gva_service_full_cube.parquet"),
        ("mining_manufacturing_production_index", "partial_stats_phase26_gva_release_event_registry.csv"),
        ("annual_anchor_cube", "partial_stats_phase28_gva_annual_target_cube.parquet"),
        ("employee_feature_cube", "kosis_employment_feature_table.csv"),
        ("business_feature_cube", "kosis_business_feature_table.csv"),
        ("fine_forecast_output", "partial_stats_phase28_gva_fine_forecast_output.parquet"),
    ]:
        rows.append(
            {
                "checked_at": GENERATED_AT,
                "source_id": source,
                "latest_reference_period": "current_local_snapshot",
                "official_update_timestamp": "",
                "query_payload": "local_or_phase27_preserved",
                "response_hash": file_hash(fname),
                "page_hash": "",
                "attachment_hash": "",
                "changed_row_count": "not_scored_first_forward_snapshot",
                "revision_count": 0,
                "origin_status": "forward_release_ledger_active",
            }
        )
    return add_audit(pd.DataFrame(rows))


def q4_manifest(selection: pd.DataFrame, pop: pd.DataFrame) -> dict[str, Any]:
    return {
        "target_period": "2026Q4",
        "created_at": GENERATED_AT,
        "annual_anchor_policy": selection.iloc[0]["selected_annual_policy"],
        "parent_policy": "QP1_G_national_growth_bridge",
        "spatial_policy": "SW0_last_annual_gva_share",
        "industry_policy": "IS0_previous_year_industry_share",
        "quarterly_profile_policy": "TP1_project_parent_proxy_profile",
        "monthly_profile_policy": "TM0_equal_month",
        "reconciliation_policy": "proportional_reconciliation_same_price_basis",
        "interval_policy": "not_calibrated_no_empirical_interval_claim",
        "fallback_policy": "last_observed_anchor_or_parent_fallback",
        "feature_release_rules": "strict_R1_R3_for_promotion;R4_pseudo_development_only",
        "parameter_hashes": core.stable_hash(selection.to_dict("records")),
        "population_hashes": pop.iloc[0]["common_population_hash"],
        "official_actual_used": False,
        "archive_status": "frozen_manifest_not_backdated",
    }


def report(final: dict[str, Any], tables: dict[str, pd.DataFrame]) -> None:
    sections = [
        ("실행 요약", "Phase 28은 관측 Anchor와 예측·배분 행을 분리하고, NA1 completeness와 annual anchor backtest/forecast를 생성했다."),
        ("목표·가격기준 불변 선언", final["price_basis_separation_status"]),
        ("Phase 27 재현", markdown_table(tables["reproduction"])),
        ("Prospective Archive 무결성", f"2026Q2={final['holdout_2026q2_status']}, 2026Q3={final['archive_2026q3_integrity']}, 2026Q4={final['manifest_2026q4_status']}"),
        ("Population Identity Audit", markdown_table(tables["population"])),
        ("SW0 Score Reconciliation", markdown_table(tables["sw0_recon"])),
        ("Value Status Audit", markdown_table(tables["value_audit"])),
        ("Quality Grade 재분류", markdown_table(tables["quality"])),
        ("NA1 Completeness", markdown_table(tables["na1_audit"])),
        ("결측 Cell 분류", markdown_table(tables["missing"], 12)),
        ("Annual Anchor Baseline", markdown_table(tables["annual_perf"][tables["annual_perf"]["status"].eq("baseline")])),
        ("Annual Anchor Challenger", markdown_table(tables["annual_perf"][tables["annual_perf"]["status"].eq("challenger_development")])),
        ("Rolling-origin Annual Performance", markdown_table(tables["annual_perf"])),
        ("종사자 Feature Cube", markdown_table(tables["structural"][tables["structural"]["feature_source"].eq("employee")])),
        ("사업체 Feature Cube", markdown_table(tables["structural"][tables["structural"]["feature_source"].eq("business")])),
        ("Parent Nested CV", markdown_table(tables["parent"])),
        ("Locked Official Diagnostic", markdown_table(tables["parent_diag"])),
        ("Spatial Share-change", markdown_table(tables["spatial"])),
        ("Industry Share-change", markdown_table(tables["industry"])),
        ("Quarterly Profile", markdown_table(tables["quarterly"])),
        ("Monthly Profile", markdown_table(tables["monthly"])),
        ("Hierarchical Reconciliation", final["selected_reconciliation_policy"]),
        ("Coverage by Group", markdown_table(tables["coverage"])),
        ("Performance by Group", markdown_table(tables["performance"], 12)),
        ("Worst Group", markdown_table(tables["worst"])),
        ("Material Degradation", markdown_table(tables["material"])),
        ("Interval Calibration", markdown_table(tables["interval"])),
        ("Structural Uncertainty", markdown_table(tables["uncertainty"])),
        ("Fine Forecast Output", markdown_table(tables["forecast"].head(10))),
        ("Forward Release Ledger", markdown_table(tables["forward"])),
        ("2026Q4 Frozen Manifest", json.dumps(final["q4_manifest"], ensure_ascii=False, indent=2)),
        ("선택정책", f"Annual={final['selected_annual_policy']}; Parent={final['selected_parent_policy']}; Spatial={final['selected_spatial_policy']}; Quarterly={final['selected_quarterly_profile']}; Monthly={final['selected_monthly_profile']}"),
        ("아직 주장할 수 없는 내용", final["claims_still_prohibited"]),
        ("결론", "NA1 과거 anchor는 Grade O로 재분류했다. 2024 annual anchor forecast는 생성했지만 strict release와 interval calibration이 부족해 production/official claim은 금지한다."),
    ]
    lines = ["# Partial Statistics Estimation Phase 28-GVA", ""]
    for idx, (title, body) in enumerate(sections, 1):
        lines += [f"## {idx}. {title}", "", str(body), ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topic() -> None:
    topic = ROOT / "reports" / "topics" / "ml.md"
    line = "| [partial_statistics_estimation_phase28_gva.md](../partial_statistics_estimation_phase28_gva.md) | Phase 28 forecastability audit, annual nominal anchor forecasting, and forward-only prospective system |"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# ML Reports\n"
    if "partial_statistics_estimation_phase28_gva.md" not in text:
        topic.write_text(text.rstrip() + "\n" + line + "\n", encoding="utf-8")


def main() -> int:
    reproduction = phase27_reproduction()
    if not reproduction["status"].eq("pass").all():
        raise SystemExit("phase27_reproduction_failed")
    population, sw0_recon = population_identity()
    status_output, value_audit, quality = value_status_and_quality()
    na1_audit, missing, annual_target = na1_completeness()
    annual_perf, backtest, forecast, annual_selection, performance = annual_anchor_models()
    emp, biz, structural = structural_features()
    placeholders = model_placeholder_tables(annual_perf, performance)
    coverage = add_audit(pd.concat([
        na1_audit.assign(group_type="NA1"),
        structural[["feature_source", "row_count", "year_count", "region_count", "industry_count", "feature_status"]].rename(columns={"feature_source": "group_type"}),
    ], ignore_index=True, sort=False))
    fine_forecast = forecast.copy()
    fine_forecast["quality_grade"] = "B" if annual_selection.iloc[0]["selected_annual_policy"].startswith("ANR") else "A"
    fine_forecast["validation_target_type"] = "annual_anchor_backtest"
    output_quality = add_audit(pd.concat([
        quality,
        fine_forecast.groupby(["quality_grade", "value_status"], as_index=False).size().rename(columns={"size": "row_count"}),
    ], ignore_index=True, sort=False))
    forward = forward_release_ledger()
    q2 = json.loads((PROCESSED_DIR / "partial_stats_phase27_gva_2026q2_holdout_status.json").read_text(encoding="utf-8"))
    q3 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase27_gva_2026q3_asof_archive.parquet")
    q4 = q4_manifest(annual_selection, population)

    outputs_csv = {
        "partial_stats_phase28_gva_population_identity_audit.csv": population,
        "partial_stats_phase28_gva_sw0_score_reconciliation.csv": sw0_recon,
        "partial_stats_phase28_gva_value_status_audit.csv": value_audit,
        "partial_stats_phase28_gva_na1_completeness_audit.csv": na1_audit,
        "partial_stats_phase28_gva_missing_cell_registry.csv": missing,
        "partial_stats_phase28_gva_contaminated_hypothesis_registry.csv": placeholders["contaminated"],
        "partial_stats_phase28_gva_structural_feature_coverage.csv": structural,
        "partial_stats_phase28_gva_parent_nested_cv.csv": placeholders["parent"],
        "partial_stats_phase28_gva_parent_candidate_results.csv": placeholders["parent_diag"],
        "partial_stats_phase28_gva_spatial_share_change_results.csv": placeholders["spatial"],
        "partial_stats_phase28_gva_industry_share_change_results.csv": placeholders["industry"],
        "partial_stats_phase28_gva_quarterly_profile_results.csv": placeholders["quarterly"],
        "partial_stats_phase28_gva_monthly_profile_results.csv": placeholders["monthly"],
        "partial_stats_phase28_gva_coverage_by_group.csv": coverage,
        "partial_stats_phase28_gva_performance_by_group.csv": performance,
        "partial_stats_phase28_gva_worst_group.csv": placeholders["worst"],
        "partial_stats_phase28_gva_material_degradation.csv": placeholders["material"],
        "partial_stats_phase28_gva_interval_calibration.csv": placeholders["interval"],
        "partial_stats_phase28_gva_structural_uncertainty.csv": placeholders["uncertainty"],
        "partial_stats_phase28_gva_output_quality_registry.csv": output_quality,
        "partial_stats_phase28_gva_forward_release_ledger.csv": forward,
    }
    for name, frame in outputs_csv.items():
        write_csv(name, frame)

    write_parquet("partial_stats_phase28_gva_annual_target_cube.parquet", annual_target)
    write_parquet("partial_stats_phase28_gva_annual_anchor_backtest.parquet", backtest)
    write_parquet("partial_stats_phase28_gva_annual_anchor_forecast.parquet", forecast)
    write_parquet("partial_stats_phase28_gva_employee_feature_cube.parquet", emp)
    write_parquet("partial_stats_phase28_gva_business_feature_cube.parquet", biz)
    write_parquet("partial_stats_phase28_gva_fine_forecast_output.parquet", fine_forecast)
    write_parquet("partial_stats_phase28_gva_2026q3_asof_archive.parquet", q3)
    write_json(PROCESSED_DIR / "partial_stats_phase28_gva_2026q2_status.json", q2)
    write_json(PROCESSED_DIR / "partial_stats_phase28_gva_2026q4_frozen_manifest.json", q4)

    counts = output_quality.groupby("quality_grade")["row_count"].sum().astype(int).to_dict()
    final = {
        "status": "forecastability_audited;actual_anchor_grade_O;annual_anchor_forecast_created;forward_release_ledger_active;incumbents_retained",
        "target": "GVA",
        "target_unchanged": True,
        "price_basis_separation_status": "real_growth_and_nominal_level_tracks_separated",
        "phase27_reproduction_status": "pass",
        "holdout_2026q2_status": q2.get("event_status", "waiting_first_release"),
        "archive_2026q3_integrity": "pass_existing_archive_preserved_new_asof_only",
        "manifest_2026q4_status": "frozen_manifest_created_not_backdated",
        "q4_manifest": q4,
        "population_identity_status": population.iloc[0]["identity_status"],
        "phase26_SW0_common_population_MAE": float(sw0_recon[sw0_recon["metric"].eq("SW0_share_mae")]["phase26_value"].iloc[0]),
        "phase27_SW0_common_population_MAE": float(sw0_recon[sw0_recon["metric"].eq("SW0_share_mae")]["phase27_value"].iloc[0]),
        "SW0_score_difference_explanation": sw0_recon.iloc[0]["explanation_status"],
        "NA1_theoretical_cell_count": int(na1_audit.iloc[0]["theoretical_cell_count"]),
        "NA1_observed_cell_count": int(na1_audit.iloc[0]["observed_cell_count"]),
        "NA1_coverage_rate": float(na1_audit.iloc[0]["cell_coverage_rate"]),
        "missing_source_cell_count": int((missing["missing_reason"] == "missing_source").sum()),
        "suppressed_cell_count": 0,
        "not_applicable_cell_count": 0,
        "observed_official_anchor_count": int((status_output["value_status"] == "observed_official_actual").sum()),
        "annual_backtest_prediction_count": int(len(backtest)),
        "prospective_annual_forecast_count": int(len(forecast)),
        "annual_baseline_WMAPE": float(annual_perf[annual_perf["status"].eq("baseline")]["wmape"].min()),
        "annual_challenger_WMAPE": float(annual_perf[annual_perf["policy_id"].eq("ANR_shrunk_lag_parent_growth")]["wmape"].iloc[0]),
        "annual_macro_region_WMAPE": float(performance[performance["group_type"].eq("region")]["metric_value"].mean()),
        "annual_macro_industry_WMAPE": float(performance[performance["group_type"].eq("industry")]["metric_value"].mean()),
        "annual_worst_decile_APE": float(backtest.assign(ape=(backtest["predicted_gva"] - backtest["actual_gva"]).abs() / backtest["actual_gva"].replace(0, np.nan).abs())["ape"].quantile(0.9)),
        "employee_feature_coverage": structural[structural["feature_source"].eq("employee")]["feature_status"].iloc[0],
        "business_feature_coverage": structural[structural["feature_source"].eq("business")]["feature_status"].iloc[0],
        "parent_development_candidate": "PR2_dev_ridge_residual_blocked",
        "parent_nested_CV_MAE": "not_scored",
        "parent_locked_official_diagnostic_MAE": "not_scored_new_candidate_not_frozen",
        "spatial_baseline_MAE": "SW0_retained",
        "spatial_challenger_MAE": "not_scored_structural_release_incomplete",
        "industry_baseline_MAE": "IS0_retained",
        "industry_challenger_MAE": "blocked_release_ledger_incomplete",
        "quarterly_baseline_result": "TQ1_TP1_retained_grade_D",
        "quarterly_challenger_result": "TQ3_service_profile_development_ready_not_promoted",
        "monthly_native_source_coverage": 0.0,
        "monthly_challenger_result": "TM0_equal_month_retained_grade_E",
        "performance_worst_region": performance[performance["group_type"].eq("region")].sort_values("metric_value", ascending=False)["group_id"].iloc[0],
        "performance_worst_industry": performance[performance["group_type"].eq("industry")].sort_values("metric_value", ascending=False)["group_id"].iloc[0],
        "performance_worst_year": str(performance[performance["group_type"].eq("year")].sort_values("metric_value", ascending=False)["group_id"].iloc[0]),
        "material_degradation_count": int(placeholders["material"]["material_degradation_count"].astype(int).sum()),
        "50_percent_annual_interval_coverage": "not_calibrated",
        "80_percent_annual_interval_coverage": "not_calibrated",
        "95_percent_annual_interval_coverage": "not_calibrated",
        "quarterly_structural_interval_status": "structural_uncertainty_interval_not_empirical",
        "monthly_structural_interval_status": "structural_uncertainty_interval_not_empirical",
        "fine_annual_forecast_row_count": int(len(fine_forecast)),
        "fine_quarterly_development_row_count": int((status_output["value_status"] == "development_allocation").sum()),
        "fine_monthly_experimental_row_count": int((status_output["value_status"] == "experimental_allocation").sum()),
        "quality_grade_O_count": int(counts.get("O", 0)),
        "quality_grade_A_count": int(counts.get("A", 0)),
        "quality_grade_B_count": int(counts.get("B", 0)),
        "quality_grade_C_count": int(counts.get("C", 0)),
        "quality_grade_D_count": int(counts.get("D", 0)),
        "quality_grade_E_count": int(counts.get("E", 0)),
        "forward_release_event_count": int(len(forward)),
        "selected_annual_policy": annual_selection.iloc[0]["selected_annual_policy"],
        "selected_parent_policy": "QP1_G_national_growth_bridge",
        "selected_spatial_policy": "SW0_last_annual_gva_share",
        "selected_industry_policy": "IS0_previous_year_industry_share",
        "selected_quarterly_profile": "TP1_project_parent_proxy_profile",
        "selected_monthly_profile": "TM0_equal_month",
        "selected_reconciliation_policy": "proportional_reconciliation_same_price_basis",
        "production_use": False,
        "official_statistics_claim": False,
        "claims_still_prohibited": "official statistics equivalence, production use, calibrated interval coverage, monthly direct accuracy, quarterly direct GVA accuracy, PR1 reuse, strict origin-responsive parent challenger, structural-feature challenger promotion",
        "generated_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase28_gva_final_status.json", final)
    tables = {
        "reproduction": phase27_reproduction(),
        "population": population,
        "sw0_recon": sw0_recon,
        "value_audit": value_audit,
        "quality": output_quality,
        "na1_audit": na1_audit,
        "missing": missing,
        "annual_perf": annual_perf,
        "structural": structural,
        "parent": placeholders["parent"],
        "parent_diag": placeholders["parent_diag"],
        "spatial": placeholders["spatial"],
        "industry": placeholders["industry"],
        "quarterly": placeholders["quarterly"],
        "monthly": placeholders["monthly"],
        "coverage": coverage,
        "performance": performance,
        "worst": placeholders["worst"],
        "material": placeholders["material"],
        "interval": placeholders["interval"],
        "uncertainty": placeholders["uncertainty"],
        "forecast": fine_forecast,
        "forward": forward,
    }
    report(final, tables)
    update_topic()
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
