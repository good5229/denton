from __future__ import annotations

import json
import math
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase19_gva_target_coverage_audit.csv",
    "partial_stats_phase19_gva_model_identity_audit.csv",
    "partial_stats_phase19_gva_policy_alias_registry.csv",
    "partial_stats_phase19_gva_report_consistency_audit.csv",
    "partial_stats_phase19_gva_signed_error_decomposition.csv",
    "partial_stats_phase19_gva_absolute_shapley_decomposition.csv",
    "partial_stats_phase19_gva_squared_shapley_decomposition.csv",
    "partial_stats_phase19_gva_error_type_registry.csv",
    "partial_stats_phase19_gva_parent_baseline_results.csv",
    "partial_stats_phase19_gva_parent_bridge_results.csv",
    "partial_stats_phase19_gva_parent_policy_selection.csv",
    "partial_stats_phase19_gva_material_share_change.csv",
    "partial_stats_phase19_gva_share_change_classifier.csv",
    "partial_stats_phase19_gva_share_change_magnitude.csv",
    "partial_stats_phase19_gva_sparse_update_budget.csv",
    "partial_stats_phase19_gva_share_policy_results.csv",
    "partial_stats_phase19_gva_parent_share_policy_matrix.csv",
    "partial_stats_phase19_gva_combined_policy_results.csv",
    "partial_stats_phase19_gva_combination_interaction.csv",
    "partial_stats_phase19_gva_parent_accuracy.csv",
    "partial_stats_phase19_gva_share_accuracy.csv",
    "partial_stats_phase19_gva_gva_accuracy.csv",
    "partial_stats_phase19_gva_update_precision_recall.csv",
    "partial_stats_phase19_gva_weighted_update_utility.csv",
    "partial_stats_phase19_gva_worst_group_results.csv",
    "partial_stats_phase19_gva_quarterly_policy_results.csv",
    "partial_stats_phase19_gva_monthly_experimental_results.csv",
    "partial_stats_phase19_gva_temporal_consistency.csv",
    "partial_stats_phase19_gva_annual_estimates_2025.csv",
    "partial_stats_phase19_gva_quarterly_estimates_2025.csv",
    "partial_stats_phase19_gva_annual_nowcast_2026.csv",
    "partial_stats_phase19_gva_quarterly_nowcast_2026.csv",
    "partial_stats_phase19_gva_parent_share_contributions.csv",
    "partial_stats_phase19_gva_execution_manifest.csv",
]


ALLOWED_STATUS = {
    "evaluation_integrity_failed",
    "parent_only_policy_selected",
    "sparse_share_policy_selected",
    "parent_and_sparse_share_selected",
    "share_change_not_predictable",
    "parent_total_improvement_failed",
    "baseline_retained_after_two_stage_test",
    "parent_only_current_nowcast_generated",
    "baseline_scenario_generated",
    "monthly_primary_blocked",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def main() -> int:
    final_path = PROCESSED_DIR / "partial_stats_phase19_gva_final_status.json"
    require(final_path.exists(), "missing final status")
    final = json.loads(final_path.read_text(encoding="utf-8"))
    require(final["status"] in ALLOWED_STATUS, "unexpected final status")
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "GVA target changed")
    require(final["registered_target_years"] == [2020, 2021, 2022, 2023], "registered years mismatch")
    require(final["evaluated_target_years"] == [2020, 2021, 2022, 2023], "evaluated years mismatch")
    require(final["target_2023_status"] == "evaluated", "2023 target status must be explicit")
    require(final["model_identity_audit"] == "pass", "model identity audit failed")
    require(final["monthly_primary_status"] == "monthly_primary_blocked", "monthly primary should remain blocked")
    require(final["official_statistics_claim"] is False and final["production_use"] is False, "official or production claim not allowed")
    require(final["actual_used_for_threshold"] is False, "outer actual used for threshold")

    for name in REQUIRED_CSVS:
        df = frame(name)
        require(len(df) > 0, f"empty artifact: {name}")
    require((PROCESSED_DIR / "partial_stats_phase19_gva_parent_target_cube.parquet").exists(), "missing parent target cube")
    require((PROCESSED_DIR / "partial_stats_phase19_gva_parent_feature_store.parquet").exists(), "missing parent feature store")
    require((PROCESSED_DIR / "partial_stats_phase19_gva_experiment_manifest.json").exists(), "missing experiment manifest json")

    coverage = frame("partial_stats_phase19_gva_target_coverage_audit.csv")
    require(coverage["coverage_identity_status"].eq("pass").all(), "target coverage identity failed")
    require(coverage[coverage["registered_target_year"].eq("2023")]["model_executed"].iloc[0] == "Y", "2023 not executed")

    signed = frame("partial_stats_phase19_gva_signed_error_decomposition.csv")
    require(num(signed["signed_reconstruction_gap"]).max() < 1e-5, "signed decomposition gap too large")
    abs_shapley = frame("partial_stats_phase19_gva_absolute_shapley_decomposition.csv")
    require(num(abs_shapley["abs_shapley_gap"]).max() < 1e-5, "absolute Shapley gap too large")
    sq_shapley = frame("partial_stats_phase19_gva_squared_shapley_decomposition.csv")
    require(num(sq_shapley["sq_shapley_gap"]).max() < 1e-2, "squared Shapley gap too large")

    registry = frame("partial_stats_phase19_gva_error_type_registry.csv")
    require(set(registry["count_level"]) == {"row_level", "cell_year_level", "unique_cell_level"}, "missing error registry levels")
    cell_year = registry[registry["count_level"].eq("cell_year_level")].iloc[0]
    counted = sum(int(cell_year[col]) for col in ["parent_dominant", "share_dominant", "compensating_error", "mixed_error", "low_error"])
    require(counted == int(cell_year["total_units"]), "cell-year error types do not sum")

    parent_results = frame("partial_stats_phase19_gva_parent_baseline_results.csv")
    require(set(parent_results["parent_policy_id"]) == {"PB0_parent_baseline", "PB1_last_parent", "PB2_national_industry_growth", "PB3_damped_national_growth", "PB4_hierarchical_parent_growth", "PB5_parent_bridge"}, "missing parent policies")
    require(num(parent_results["parent_wmape"]).between(0, 10).all(), "parent WMAPE out of range")

    material = frame("partial_stats_phase19_gva_material_share_change.csv")
    require(material["outer_actual_used_for_threshold"].eq("N").all(), "outer actual threshold leakage")
    require(material["material_share_change"].isin(["Y", "N"]).all(), "invalid material label")

    budget = frame("partial_stats_phase19_gva_sparse_update_budget.csv")
    require(budget["zero_sum_required"].eq("Y").all(), "zero-sum budget not required")
    require(budget["outer_actual_used_for_budget"].eq("N").all(), "outer actual budget leakage")
    candidate_count = num(budget["candidate_count"]).fillna(0)
    selected_count = num(budget["selected_count"]).fillna(0)
    allowed_count = candidate_count.mul(0.20).apply(lambda x: max(3, math.ceil(x)))
    require((selected_count <= allowed_count).all(), "sparse budget too wide")

    pr = frame("partial_stats_phase19_gva_update_precision_recall.csv")
    require(set(pr["share_policy_id"]) == {"PS0_last_share", "PS1_sparse_damped_trend", "PS2_sparse_hierarchical_change", "PS3_sparse_empirical_bayes", "PS4_event_gated_change", "PS5_auxiliary_share_classifier", "PS6_precision_first_router"}, "missing share policies")
    for col in ["precision", "recall", "false_update_rate", "missed_material_change_rate"]:
        require(num(pr[col]).between(0, 1).all(), f"{col} out of range")

    matrix = frame("partial_stats_phase19_gva_parent_share_policy_matrix.csv")
    require("PB0_parent_baseline__PS0_last_share" in set(matrix["combined_policy_id"]), "missing incumbent combined policy")

    current = frame("partial_stats_phase19_gva_annual_nowcast_2026.csv")
    require(current["actual_used"].eq("N").all(), "2026 actual should not be used")
    require(current["estimate_status"].isin(["baseline_scenario", "parent_only_current_nowcast"]).all(), "bad 2026 status")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase19_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 38)), "report sections must be 1..37")
    for phrase in ["Target Coverage Audit", "Model Identity Audit", "Shapley Error Decomposition", final["status"]]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(
        json.dumps(
            {
                "status": final["status"],
                "selected_parent_policy": final["selected_parent_policy"],
                "selected_share_policy": final["selected_share_policy"],
                "target_2023_status": final["target_2023_status"],
                "report": "reports/partial_statistics_estimation_phase19_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
