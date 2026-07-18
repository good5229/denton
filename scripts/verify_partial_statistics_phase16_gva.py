from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase16_gva_electricity_source_registry.csv",
    "partial_stats_phase16_gva_employment_source_registry.csv",
    "partial_stats_phase16_gva_output_source_registry.csv",
    "partial_stats_phase16_gva_source_download_manifest.csv",
    "partial_stats_phase16_gva_release_ledger.csv",
    "partial_stats_phase16_gva_vintage_registry.csv",
    "partial_stats_phase16_gva_release_confidence.csv",
    "partial_stats_phase16_gva_target_registry.csv",
    "partial_stats_phase16_gva_target_support.csv",
    "partial_stats_phase16_gva_origin_registry.csv",
    "partial_stats_phase16_gva_feature_hash_registry.csv",
    "partial_stats_phase16_gva_leakage_audit.csv",
    "partial_stats_phase16_gva_output_factor.csv",
    "partial_stats_phase16_gva_labor_factor.csv",
    "partial_stats_phase16_gva_energy_factor.csv",
    "partial_stats_phase16_gva_demand_factor.csv",
    "partial_stats_phase16_gva_business_factor.csv",
    "partial_stats_phase16_gva_indicator_coverage.csv",
    "partial_stats_phase16_gva_indicator_sign_stability.csv",
    "partial_stats_phase16_gva_indicator_lead_lag.csv",
    "partial_stats_phase16_gva_indicator_placebo.csv",
    "partial_stats_phase16_gva_indicator_qualification.csv",
    "partial_stats_phase16_gva_b0_results.csv",
    "partial_stats_phase16_gva_output_bridge_results.csv",
    "partial_stats_phase16_gva_labor_bridge_results.csv",
    "partial_stats_phase16_gva_energy_bridge_results.csv",
    "partial_stats_phase16_gva_multiblock_results.csv",
    "partial_stats_phase16_gva_residual_results.csv",
    "partial_stats_phase16_gva_exposure_allocation_results.csv",
    "partial_stats_phase16_gva_ensemble_results.csv",
    "partial_stats_phase16_gva_information_utilization.csv",
    "partial_stats_phase16_gva_revision_utility.csv",
    "partial_stats_phase16_gva_harmful_revision.csv",
    "partial_stats_phase16_gva_risk_queue.csv",
    "partial_stats_phase16_gva_temporal_indicator_registry.csv",
    "partial_stats_phase16_gva_denton_results.csv",
    "partial_stats_phase16_gva_chow_lin_results.csv",
    "partial_stats_phase16_gva_temporal_consistency.csv",
    "partial_stats_phase16_gva_monthly_activation_gate.csv",
    "partial_stats_phase16_gva_annual_estimates_2025.csv",
    "partial_stats_phase16_gva_quarterly_estimates_2025.csv",
    "partial_stats_phase16_gva_annual_nowcast_2026.csv",
    "partial_stats_phase16_gva_quarterly_nowcast_2026.csv",
    "partial_stats_phase16_gva_current_indicator_contributions.csv",
    "partial_stats_phase16_gva_experiment_manifest.csv",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def asof_store_exists(name: str) -> bool:
    return (PROCESSED_DIR / name).exists()


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase16_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA", "target must remain GVA")
    require(final["target_unchanged"] is True, "target changed")
    require(final["status"] in {"strict_indicator_policy_selected", "sector_limited_indicator_selected", "origin_limited_indicator_selected", "baseline_retained_after_strict_indicator_test"}, "unexpected status")
    require(final["fully_evaluable_target_years"] >= 3, "Phase16 should have at least three fully evaluable target years")
    require(final["monthly_primary_status"] == "monthly_primary_blocked", "monthly primary should remain blocked")
    require(final["actual_used_for_indicator_construction"] is False, "indicator construction used actual")
    require(final["actual_used_for_weight_or_lag_selection"] is False, "weight or lag selection used actual")
    require(final["current_snapshot_backdated_to_strict"] is False, "current snapshot was backdated into strict track")
    require(final["official_statistics_claim"] is False and final["production_use"] is False, "official or production claim not allowed")
    require(asof_store_exists(final["asof_feature_store_artifact"]), "as-of feature store artifact missing")

    for name in REQUIRED_CSVS:
        df = frame(name)
        require(len(df) > 0, f"empty artifact: {name}")

    target = frame("partial_stats_phase16_gva_target_registry.csv")
    require(target["fully_evaluable"].eq("Y").sum() >= 3, "target registry does not support three full years")

    ledger = frame("partial_stats_phase16_gva_release_ledger.csv")
    require("A_exact" in set(ledger["release_confidence"]), "exact release confidence source missing")
    kosis = ledger[ledger["release_confidence"].eq("D_current_snapshot")]
    require(kosis["track"].eq("sensitivity").all(), "current snapshots must remain sensitivity track")

    leakage = frame("partial_stats_phase16_gva_leakage_audit.csv")
    must_pass = leakage[leakage["check_id"].isin(["feature_release_before_origin", "target_actual_hidden", "target_derived_feature_absent", "future_month_excluded"])]
    require(must_pass["status"].eq("pass").all(), "leakage audit failed")

    qualification = frame("partial_stats_phase16_gva_indicator_qualification.csv")
    require(set(qualification["block"]) == {"output", "labor", "energy", "demand", "business"}, "missing indicator blocks")
    rejected_or_diagnostic = qualification[qualification["primary_eligible"].eq("N")]
    require(len(rejected_or_diagnostic) >= 1, "expected at least one non-primary block")

    for name in [
        "partial_stats_phase16_gva_b0_results.csv",
        "partial_stats_phase16_gva_output_bridge_results.csv",
        "partial_stats_phase16_gva_labor_bridge_results.csv",
        "partial_stats_phase16_gva_energy_bridge_results.csv",
        "partial_stats_phase16_gva_multiblock_results.csv",
        "partial_stats_phase16_gva_residual_results.csv",
        "partial_stats_phase16_gva_exposure_allocation_results.csv",
        "partial_stats_phase16_gva_ensemble_results.csv",
    ]:
        result = frame(name)
        require(len(result) == 16, f"model result should cover 4 years x 4 origins: {name}")
        require(pd.to_numeric(result["wmape"], errors="coerce").notna().all(), f"wmape missing: {name}")

    temporal = frame("partial_stats_phase16_gva_temporal_consistency.csv")
    require(temporal["status"].eq("pass").any(), "quarterly consistency pass missing")
    monthly = frame("partial_stats_phase16_gva_monthly_activation_gate.csv")
    require(monthly[monthly["gate"].eq("monthly_primary")]["status"].iloc[0] == "blocked", "monthly activation gate should block")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase16_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 44)), "report sections must be 1..43")
    for phrase in ["Historical Target", "Electricity Source", "Monthly Activation Gate", "baseline_retained_after_strict_indicator_test"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(
        json.dumps(
            {
                "status": final["status"],
                "selected_policy": final["selected_policy"],
                "fully_evaluable_target_years": final["fully_evaluable_target_years"],
                "monthly_primary_status": final["monthly_primary_status"],
                "report": "reports/partial_statistics_estimation_phase16_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
