from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase17_gva_feature_lineage.csv",
    "partial_stats_phase17_gva_hash_registry.csv",
    "partial_stats_phase17_gva_fallback_equivalence.csv",
    "partial_stats_phase17_gva_origin_materialization_audit.csv",
    "partial_stats_phase17_gva_strict_source_registry.csv",
    "partial_stats_phase17_gva_conservative_source_registry.csv",
    "partial_stats_phase17_gva_sensitivity_source_registry.csv",
    "partial_stats_phase17_gva_release_ledger.csv",
    "partial_stats_phase17_gva_energy_contract_mapping.csv",
    "partial_stats_phase17_gva_energy_exposure.csv",
    "partial_stats_phase17_gva_energy_quality.csv",
    "partial_stats_phase17_gva_energy_sector_results.csv",
    "partial_stats_phase17_gva_monthly_employment_registry.csv",
    "partial_stats_phase17_gva_labor_coverage.csv",
    "partial_stats_phase17_gva_labor_quality.csv",
    "partial_stats_phase17_gva_output_release_evidence.csv",
    "partial_stats_phase17_gva_demand_release_evidence.csv",
    "partial_stats_phase17_gva_indicator_coverage.csv",
    "partial_stats_phase17_gva_indicator_variance.csv",
    "partial_stats_phase17_gva_indicator_sign_stability.csv",
    "partial_stats_phase17_gva_indicator_placebo.csv",
    "partial_stats_phase17_gva_indicator_incremental_value.csv",
    "partial_stats_phase17_gva_indicator_certification.csv",
    "partial_stats_phase17_gva_b0_results.csv",
    "partial_stats_phase17_gva_strict_energy_results.csv",
    "partial_stats_phase17_gva_energy_share_results.csv",
    "partial_stats_phase17_gva_output_sensitivity_results.csv",
    "partial_stats_phase17_gva_demand_sensitivity_results.csv",
    "partial_stats_phase17_gva_selective_router_results.csv",
    "partial_stats_phase17_gva_information_utilization.csv",
    "partial_stats_phase17_gva_revision_utility.csv",
    "partial_stats_phase17_gva_harmful_revision.csv",
    "partial_stats_phase17_gva_worst_group_results.csv",
    "partial_stats_phase17_gva_quarterly_policy_results.csv",
    "partial_stats_phase17_gva_monthly_experimental_results.csv",
    "partial_stats_phase17_gva_denton_results.csv",
    "partial_stats_phase17_gva_temporal_consistency.csv",
    "partial_stats_phase17_gva_monthly_activation_gate.csv",
    "partial_stats_phase17_gva_annual_estimates_2025.csv",
    "partial_stats_phase17_gva_quarterly_estimates_2025.csv",
    "partial_stats_phase17_gva_annual_nowcast_2026.csv",
    "partial_stats_phase17_gva_quarterly_nowcast_2026.csv",
    "partial_stats_phase17_gva_current_indicator_contributions.csv",
    "partial_stats_phase17_gva_experiment_manifest.csv",
    "partial_stats_phase17_gva_execution_manifest.csv",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase17_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA", "target must remain GVA")
    require(final["target_unchanged"] is True, "target changed")
    require(final["status"] in {"feature_store_integrity_failed", "strict_energy_sector_policy_selected", "strict_energy_rejected", "sensitivity_output_signal_detected", "baseline_retained_after_block_certification"}, "unexpected final status")
    require(final["canonical_asof_store"] == "partial_stats_phase17_gva_asof_feature_store.parquet", "canonical store must be parquet")
    require((PROCESSED_DIR / final["canonical_asof_store"]).exists(), "canonical parquet missing")
    require(final["fallback_equivalence"] == "pass", "fallback equivalence failed")
    require(final["origin_materialization_pass"] is True, "origin materialization failed")
    require(final["hash_integrity"] == "pass", "hash integrity failed")
    require(final["feature_lineage_completion_rate"] == 1.0, "lineage incomplete")
    require(final["strict_source_count"] >= 1, "strict source missing")
    require(final["sensitivity_mixed_into_strict"] is False, "sensitivity mixed into strict")
    require(final["monthly_primary_status"] == "monthly_primary_blocked", "monthly primary should be blocked")
    require(final["official_statistics_claim"] is False and final["production_use"] is False, "official or production claim not allowed")

    for name in REQUIRED_CSVS:
        df = frame(name)
        require(len(df) > 0, f"empty artifact: {name}")

    eq = frame("partial_stats_phase17_gva_fallback_equivalence.csv").iloc[0]
    require(eq["canonical_content_hash"] == eq["fallback_content_hash"], "canonical/fallback hashes differ")
    require(eq["fallback_equivalence_status"] == "pass", "fallback equivalence status failed")

    lineage = frame("partial_stats_phase17_gva_feature_lineage.csv")
    require(lineage["lineage_complete"].eq("Y").all(), "feature lineage incomplete")

    hash_reg = frame("partial_stats_phase17_gva_hash_registry.csv")
    for col in ["eligible_source_set_hash", "eligible_observation_hash", "raw_feature_value_hash", "transformed_feature_value_hash", "model_input_hash"]:
        require(hash_reg[col].astype(str).str.len().gt(0).all(), f"hash column missing: {col}")

    cert = frame("partial_stats_phase17_gva_indicator_certification.csv")
    require(set(cert["block"]) == {"output", "labor", "energy", "demand", "business"}, "missing certification blocks")
    require(cert[cert["block"].eq("energy")]["release_gate"].iloc[0] == "pass", "energy strict release gate should pass")
    require(cert[cert["block"].isin(["output", "demand"])]["release_gate"].eq("sensitivity_only").all(), "output/demand must remain sensitivity")

    energy = frame("partial_stats_phase17_gva_energy_contract_mapping.csv")
    primary = energy[energy["contract_class"].eq("산업용")].iloc[0]
    require(primary["primary_energy_signal"] == "Y", "industrial electricity should be primary energy signal")
    require(primary["allowed_industries"] == "B00,C00,D00", "energy sector gate mismatch")

    for name in [
        "partial_stats_phase17_gva_b0_results.csv",
        "partial_stats_phase17_gva_strict_energy_results.csv",
        "partial_stats_phase17_gva_energy_share_results.csv",
        "partial_stats_phase17_gva_output_sensitivity_results.csv",
        "partial_stats_phase17_gva_demand_sensitivity_results.csv",
        "partial_stats_phase17_gva_selective_router_results.csv",
    ]:
        result = frame(name)
        require(len(result) == 16, f"model result should have 16 rows: {name}")
        require(pd.to_numeric(result["wmape"], errors="coerce").notna().all(), f"wmape missing: {name}")

    monthly = frame("partial_stats_phase17_gva_monthly_activation_gate.csv")
    require(monthly[monthly["gate"].eq("monthly_primary")]["status"].iloc[0] == "blocked", "monthly primary gate should block")
    require(monthly[monthly["gate"].eq("monthly_sector_experimental")]["status"].iloc[0] == "generated", "monthly experimental should be generated")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase17_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 44)), "report sections must be 1..43")
    for phrase in ["Feature Store Integrity", "Strict Energy Adjustment", "Monthly Experimental Track", final["status"]]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(
        json.dumps(
            {
                "status": final["status"],
                "selected_policy": final["selected_policy"],
                "fallback_equivalence": final["fallback_equivalence"],
                "monthly_primary_status": final["monthly_primary_status"],
                "report": "reports/partial_statistics_estimation_phase17_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
