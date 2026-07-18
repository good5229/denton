from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase18_gva_error_decomposition.csv",
    "partial_stats_phase18_gva_parent_error.csv",
    "partial_stats_phase18_gva_share_error.csv",
    "partial_stats_phase18_gva_error_type_registry.csv",
    "partial_stats_phase18_gva_share_audit.csv",
    "partial_stats_phase18_gva_share_stability.csv",
    "partial_stats_phase18_gva_share_concentration.csv",
    "partial_stats_phase18_gva_share_regime.csv",
    "partial_stats_phase18_gva_change_point_diagnostics.csv",
    "partial_stats_phase18_gva_regime_stability.csv",
    "partial_stats_phase18_gva_share_signal_qualification.csv",
    "partial_stats_phase18_gva_last_share_results.csv",
    "partial_stats_phase18_gva_damped_share_results.csv",
    "partial_stats_phase18_gva_mean_reverting_share_results.csv",
    "partial_stats_phase18_gva_dynamic_logistic_share_results.csv",
    "partial_stats_phase18_gva_empirical_bayes_share_results.csv",
    "partial_stats_phase18_gva_change_gated_share_results.csv",
    "partial_stats_phase18_gva_share_router_results.csv",
    "partial_stats_phase18_gva_share_accuracy.csv",
    "partial_stats_phase18_gva_gva_accuracy.csv",
    "partial_stats_phase18_gva_update_confusion_matrix.csv",
    "partial_stats_phase18_gva_harmful_revision.csv",
    "partial_stats_phase18_gva_worst_group_results.csv",
    "partial_stats_phase18_gva_quarterly_policy_results.csv",
    "partial_stats_phase18_gva_monthly_experimental_results.csv",
    "partial_stats_phase18_gva_temporal_consistency.csv",
    "partial_stats_phase18_gva_annual_estimates_2025.csv",
    "partial_stats_phase18_gva_quarterly_estimates_2025.csv",
    "partial_stats_phase18_gva_annual_nowcast_2026.csv",
    "partial_stats_phase18_gva_quarterly_nowcast_2026.csv",
    "partial_stats_phase18_gva_share_update_contributions.csv",
    "partial_stats_phase18_gva_experiment_manifest.csv",
    "partial_stats_phase18_gva_execution_manifest.csv",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase18_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA", "target must remain GVA")
    require(final["target_unchanged"] is True, "target changed")
    require(final["status"] in {"share_error_not_material", "share_change_not_predictable", "dynamic_share_rejected", "sector_limited_dynamic_share_selected", "change_gated_share_selected", "empirical_bayes_share_selected", "baseline_retained_after_share_test", "parent_total_improvement_required"}, "unexpected status")
    require(final["confirmatory_target_exists"] is False, "confirmatory target should be absent")
    require(final["selected_parent_policy"] == "Parent_Baseline", "parent policy should remain separated")
    require(final["selected_share_policy"], "selected share policy missing")
    require(final["actual_used_for_policy_selection"] is False, "actual used for policy selection")
    require(final["share_sum_status"] == "pass", "share sum audit failed")
    require(final["monthly_primary_status"] == "monthly_primary_blocked", "monthly primary should remain blocked")
    require(final["official_statistics_claim"] is False and final["production_use"] is False, "official or production claim not allowed")

    for name in REQUIRED_CSVS:
        df = frame(name)
        require(len(df) > 0, f"empty artifact: {name}")

    share_cube_path = PROCESSED_DIR / "partial_stats_phase18_gva_share_cube.parquet"
    require(share_cube_path.exists(), "missing share cube parquet")
    cube = pd.read_parquet(share_cube_path)
    require((pd.to_numeric(cube["gva_share"], errors="coerce") >= -1e-12).all(), "negative share found")

    share_audit = frame("partial_stats_phase18_gva_share_audit.csv")
    require(share_audit["status"].eq("pass").all(), "share sum audit rows failed")
    require(pd.to_numeric(share_audit["absolute_gap_from_one"], errors="coerce").max() < 1e-8, "share sum gap too large")

    decomp = frame("partial_stats_phase18_gva_error_decomposition.csv")
    max_c3_gap = pd.to_numeric(decomp["c3_consistency_gap"], errors="coerce").max()
    require(max_c3_gap < 1e-4, "actual parent x actual share reconstruction failed")
    type_registry = frame("partial_stats_phase18_gva_error_type_registry.csv").iloc[0]
    require(float(type_registry["share_dominant_cells"]) >= 0 and float(type_registry["parent_dominant_cells"]) >= 0, "error type counts invalid")

    for name in [
        "partial_stats_phase18_gva_last_share_results.csv",
        "partial_stats_phase18_gva_damped_share_results.csv",
        "partial_stats_phase18_gva_mean_reverting_share_results.csv",
        "partial_stats_phase18_gva_dynamic_logistic_share_results.csv",
        "partial_stats_phase18_gva_empirical_bayes_share_results.csv",
        "partial_stats_phase18_gva_change_gated_share_results.csv",
        "partial_stats_phase18_gva_share_router_results.csv",
    ]:
        result = frame(name)
        require(len(result) == 16, f"share result should have 16 rows: {name}")
        require(pd.to_numeric(result["wmape"], errors="coerce").notna().all(), f"wmape missing: {name}")
        require(pd.to_numeric(result["share_mae"], errors="coerce").notna().all(), f"share_mae missing: {name}")

    confusion = frame("partial_stats_phase18_gva_update_confusion_matrix.csv")
    require(set(confusion["policy_id"]) == {"P0_last_share", "P1_damped_share_trend", "P2_mean_reverting_share", "P3_dynamic_logistic_share", "P4_empirical_bayes_share", "P5_change_gated_share", "P6_share_router"}, "missing update policies")
    require(pd.to_numeric(confusion["false_update_rate"], errors="coerce").between(0, 1).all(), "false update rate out of range")
    require(pd.to_numeric(confusion["missed_change_rate"], errors="coerce").between(0, 1).all(), "missed change rate out of range")

    current = frame("partial_stats_phase18_gva_annual_nowcast_2026.csv")
    require(current["actual_used"].eq("N").all(), "2026 actual should not be used")
    require(current["current_status"].eq(final["current_nowcast_status"]).all(), "current status mismatch")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase18_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 42)), "report sections must be 1..41")
    for phrase in ["B0 Error Decomposition", "Share Regime", "Empirical Bayes", final["status"]]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(
        json.dumps(
            {
                "status": final["status"],
                "selected_share_policy": final["selected_share_policy"],
                "share_sum_status": final["share_sum_status"],
                "monthly_primary_status": final["monthly_primary_status"],
                "report": "reports/partial_statistics_estimation_phase18_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
