from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase15_gva_methodology_registry.csv",
    "partial_stats_phase15_gva_indicator_definition_registry.csv",
    "partial_stats_phase15_gva_literature_mapping.csv",
    "partial_stats_phase15_gva_source_inventory.csv",
    "partial_stats_phase15_gva_release_ledger.csv",
    "partial_stats_phase15_gva_vintage_registry.csv",
    "partial_stats_phase15_gva_source_quality.csv",
    "partial_stats_phase15_gva_output_factor.csv",
    "partial_stats_phase15_gva_labor_factor.csv",
    "partial_stats_phase15_gva_energy_factor.csv",
    "partial_stats_phase15_gva_demand_factor.csv",
    "partial_stats_phase15_gva_business_factor.csv",
    "partial_stats_phase15_gva_narrative_factor.csv",
    "partial_stats_phase15_gva_exposure_index.csv",
    "partial_stats_phase15_gva_riaf.csv",
    "partial_stats_phase15_gva_indicator_quality.csv",
    "partial_stats_phase15_gva_indicator_disagreement.csv",
    "partial_stats_phase15_gva_b0_results.csv",
    "partial_stats_phase15_gva_riaf_bridge_results.csv",
    "partial_stats_phase15_gva_riaf_midas_results.csv",
    "partial_stats_phase15_gva_factor_residual_results.csv",
    "partial_stats_phase15_gva_exposure_allocation_results.csv",
    "partial_stats_phase15_gva_ensemble_results.csv",
    "partial_stats_phase15_gva_indicator_ablation.csv",
    "partial_stats_phase15_gva_information_utilization.csv",
    "partial_stats_phase15_gva_revision_utility.csv",
    "partial_stats_phase15_gva_harmful_revision.csv",
    "partial_stats_phase15_gva_worst_group_results.csv",
    "partial_stats_phase15_gva_temporal_indicator_registry.csv",
    "partial_stats_phase15_gva_denton_results.csv",
    "partial_stats_phase15_gva_chow_lin_results.csv",
    "partial_stats_phase15_gva_temporal_consistency.csv",
    "partial_stats_phase15_gva_annual_estimates_2025.csv",
    "partial_stats_phase15_gva_quarterly_estimates_2025.csv",
    "partial_stats_phase15_gva_annual_nowcast_2026.csv",
    "partial_stats_phase15_gva_quarterly_nowcast_2026.csv",
    "partial_stats_phase15_gva_current_indicator_contributions.csv",
    "partial_stats_phase15_gva_experiment_manifest.csv",
]


EXPECTED_STATUS = {
    "literature_indicator_policy_selected",
    "sector_limited_indicator_selected",
    "diagnostic_indicators_only",
    "baseline_retained_after_indicator_test",
    "monthly_primary_activated",
    "monthly_primary_blocked",
    "annual_quarterly_current_estimates_generated",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def variable_artifact_exists(block: str) -> bool:
    parquet = PROCESSED_DIR / f"partial_stats_phase15_gva_{block}_variables.parquet"
    fallback = PROCESSED_DIR / f"partial_stats_phase15_gva_{block}_variables_fallback.csv"
    return parquet.exists() or fallback.exists()


def main() -> int:
    final_path = PROCESSED_DIR / "partial_stats_phase15_gva_final_status.json"
    require(final_path.exists(), "missing final status")
    final = json.loads(final_path.read_text(encoding="utf-8"))
    require(final["target"] == "GVA", "target must remain GVA")
    require(final["target_unchanged"] is True, "target changed flag should be true")
    require(final["status"] in EXPECTED_STATUS, "unexpected final status")
    require(set(final["secondary_statuses"]).issubset(EXPECTED_STATUS), "unexpected secondary status")
    require(final["actual_used_for_indicator_construction"] is False, "indicator construction used actuals")
    require(final["actual_used_for_weight_selection"] is False, "weight selection used actuals")
    require(final["raw_proxy_direct_to_gva"] is False, "raw proxies must not feed GVA directly")
    require(final["national_indicator_broadcast_to_municipality"] is False, "national indicator broadcast is not allowed")
    require(final["monthly_primary_status"] == "monthly_primary_blocked", "monthly primary should remain blocked")
    require(final["quarterly_consistency_status"] == "pass", "quarterly consistency should pass")
    require(final["official_statistics_claim"] is False and final["production_use"] is False, "official or production claim not allowed")

    for name in REQUIRED_CSVS:
        df = frame(name)
        require(len(df) > 0, f"empty artifact: {name}")
    for block in ["output", "labor", "energy", "demand", "business", "narrative"]:
        require(variable_artifact_exists(block), f"missing variable artifact for {block}")

    quality = frame("partial_stats_phase15_gva_indicator_quality.csv")
    blocked = quality[quality["quality_grade"].isin(["Q4", "Q5"])]
    require(blocked["primary_eligible"].eq("N").all(), "Q4/Q5 indicators must be excluded from primary")

    riaf = frame("partial_stats_phase15_gva_riaf.csv")
    require(riaf["actual_used_for_weight_selection"].eq("N").all(), "RIAF weights should not use outer actual")

    midas = frame("partial_stats_phase15_gva_riaf_midas_results.csv")
    require(midas["evaluation_status"].eq("blocked_insufficient_historical_monthly_indicators").all(), "MIDAS should be blocked")

    ablation = frame("partial_stats_phase15_gva_indicator_ablation.csv")
    require(set(ablation["model_id"].unique()) == {"A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7"}, "missing ablations A0-A7")

    temporal = frame("partial_stats_phase15_gva_temporal_consistency.csv")
    quarter = temporal[temporal["check_id"].eq("2025_quarter_sum_equals_annual")].iloc[0]
    require(quarter["status"] == "pass", "quarter sum check failed")
    require(float(quarter["max_absolute_gap"]) < 1e-4, "quarter sum gap too large")

    annual_2025 = frame("partial_stats_phase15_gva_annual_estimates_2025.csv")
    annual_2026 = frame("partial_stats_phase15_gva_annual_nowcast_2026.csv")
    require(annual_2025["actual_used"].eq("N").all(), "2025 estimates used actual")
    require(annual_2026["actual_used"].eq("N").all(), "2026 estimates used actual")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase15_gva.md").read_text(encoding="utf-8")
    section_numbers = [int(m.group(1)) for m in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(section_numbers == list(range(1, 36)), "report sections must be 1..35")
    for phrase in ["RIAF", "Indicator Quality", "monthly_primary_blocked", "공식통계"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(
        json.dumps(
            {
                "status": final["status"],
                "selected_policy": final["selected_policy"],
                "model_origin_count": final["model_origin_count"],
                "monthly_primary_status": final["monthly_primary_status"],
                "report": "reports/partial_statistics_estimation_phase15_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
