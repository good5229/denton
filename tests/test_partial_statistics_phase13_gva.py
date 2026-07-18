from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase13_final_status_separates_origin_and_model_origin_counts() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase13_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["status"] == "strict_vintage_blocked_sensitivity_completed"
    assert final["target"] == "GVA"
    assert final["target_years"] == [2022, 2023]
    assert final["origin_count"] == 8
    assert final["independent_origin_count"] == 8
    assert final["independent_model_origin_count"] == 48
    assert final["collapsed_origin_count"] == 0
    assert final["actual_used_for_selection"] is False
    assert final["production_use"] is False
    assert final["official_statistics_claim"] is False


def test_phase13_feature_hashes_and_observations_advance_by_origin() -> None:
    growth = read_csv("partial_stats_phase13_gva_origin_information_growth.csv")
    assert set(growth["target_year"].astype(int)) == {2022, 2023}
    for _, group in growth.groupby(growth["target_year"].astype(int)):
        assert group["feature_content_hash"].nunique() == 4
        assert pd.to_numeric(group["eligible_observation_count"], errors="coerce").is_monotonic_increasing
        assert group["latest_available_observation_period"].nunique() >= 3
        assert group["feature_hash_changed"].eq("True").all()


def test_phase13_model_paths_are_independently_executed() -> None:
    identity = read_csv("partial_stats_phase13_gva_origin_identity_audit.csv")
    expected = {
        "B0_parent_share",
        "M1_direct_growth",
        "M2_employee_productivity",
        "M3_establishment_productivity",
        "M4_proxy_residual",
        "M5_fixed_ensemble",
    }
    assert expected == set(identity["model_id"])
    for keys, group in identity[identity["model_id"].isin(["M1_direct_growth", "M4_proxy_residual", "M5_fixed_ensemble"])].groupby(["target_year", "model_id"]):
        assert group["prediction_hash"].nunique() >= 3, keys

    for name in [
        "partial_stats_phase13_gva_direct_growth_results.csv",
        "partial_stats_phase13_gva_employee_productivity_results.csv",
        "partial_stats_phase13_gva_establishment_productivity_results.csv",
        "partial_stats_phase13_gva_proxy_residual_results.csv",
    ]:
        result = read_csv(name)
        assert len(result) == 8
        assert set(result["evaluation_status"]) == {"outer_evaluation_sensitivity"}


def test_phase13_monthly_primary_is_blocked_not_overclaimed() -> None:
    monthly = read_csv("partial_stats_phase13_gva_monthly_source_registry.csv")
    assert monthly["primary_monthly_eligible"].eq("N").all()
    placeholder = read_csv("partial_stats_phase13_gva_monthly_placeholder_registry.csv")
    assert placeholder.iloc[0]["allowed"] == "Y_display_only"
    temporal = read_csv("partial_stats_phase13_gva_temporal_disaggregation.csv")
    assert "blocked" in set(temporal["status"])
    assert "placeholder_only" in set(temporal["status"])


def test_phase13_report_records_limits_and_no_official_claim() -> None:
    report = (ROOT / "reports" / "partial_statistics_estimation_phase13_gva.md").read_text(encoding="utf-8")
    assert "Phase 12 restored GVA as the primary target" in report
    assert "monthly output remains placeholder-only" in report
    assert "strict official vintage performance" in report
    assert "production/official statistics use" in report
