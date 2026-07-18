from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase24_gva_model_identity_audit.csv",
    "partial_stats_phase24_gva_policy_equivalence_matrix.csv",
    "partial_stats_phase24_gva_unique_policy_registry.csv",
    "partial_stats_phase24_gva_superseded_artifact_registry.csv",
    "partial_stats_phase24_gva_period_integrity_audit.csv",
    "partial_stats_phase24_gva_quarterly_source_registry.csv",
    "partial_stats_phase24_gva_release_ledger.csv",
    "partial_stats_phase24_gva_qp0_growth_results.csv",
    "partial_stats_phase24_gva_qp1_frozen_results.csv",
    "partial_stats_phase24_gva_qp2_responsive_results.csv",
    "partial_stats_phase24_gva_qp3_shrunk_results.csv",
    "partial_stats_phase24_gva_qp4_contribution_results.csv",
    "partial_stats_phase24_gva_parent_policy_selection.csv",
    "partial_stats_phase24_gva_model_response_audit.csv",
    "partial_stats_phase24_gva_revision_utility.csv",
    "partial_stats_phase24_gva_harmful_revision.csv",
    "partial_stats_phase24_gva_spatial_source_registry.csv",
    "partial_stats_phase24_gva_annual_share_holdout.csv",
    "partial_stats_phase24_gva_spatial_policy_selection.csv",
    "partial_stats_phase24_gva_temporal_profile_holdout.csv",
    "partial_stats_phase24_gva_indicator_fallback_comparison.csv",
    "partial_stats_phase24_gva_temporal_policy_selection.csv",
    "partial_stats_phase24_gva_annual_implicit_deflator.csv",
    "partial_stats_phase24_gva_quarterly_price_proxy.csv",
    "partial_stats_phase24_gva_real_nominal_bridge_validation.csv",
    "partial_stats_phase24_gva_2026q2_archive_integrity.csv",
    "partial_stats_phase24_gva_execution_manifest.csv",
]

REQUIRED_PARQUETS = [
    "partial_stats_phase24_gva_quarterly_indicator_cube.parquet",
    "partial_stats_phase24_gva_regional_surprise_cube.parquet",
    "partial_stats_phase24_gva_asof_feature_store.parquet",
    "partial_stats_phase24_gva_origin_prediction_cube.parquet",
    "partial_stats_phase24_gva_spatial_weight_cube.parquet",
    "partial_stats_phase24_gva_temporal_profile_cube.parquet",
    "partial_stats_phase24_gva_quarterly_output_2026.parquet",
    "partial_stats_phase24_gva_shadow_forecast_archive.parquet",
    "partial_stats_phase24_gva_2026q3_forecast_archive.parquet",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase24_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "GVA target changed")
    require(final["qp1_qp2_qp3_equivalent"] is True, "QP1/QP2/QP3 equivalence should be detected")
    require(final["independent_parent_policy_count"] == 2, "independent policy count must be reduced to 2")
    require(final["qp1_frozen"] is True, "QP1 incumbent must remain frozen")
    require(final["qualified_quarterly_source_count"] == 0, "unqualified proxy-lag sources must not be counted as qualified")
    require(final["spatial_materialized_source_count"] == 1, "pending spatial sources must not be counted as materialized")
    require(final["archive_2026q2_integrity"] == "pass_existing_archive_preserved", "2026Q2 archive must be preserved")
    require(final["production_use"] is False and final["official_statistics_claim"] is False, "forbidden claim")

    for name in REQUIRED_CSVS:
        require(len(csv(name)) > 0, f"empty artifact: {name}")
    for name in REQUIRED_PARQUETS:
        require((PROCESSED_DIR / name).exists(), f"missing artifact: {name}")

    superseded = csv("partial_stats_phase24_gva_superseded_artifact_registry.csv")
    require(superseded["allowed_for_training"].astype(str).str.lower().eq("false").all(), "invalid artifacts cannot be used for training")
    require(superseded["artifact_status"].str.contains("superseded_invalid_period_key", regex=False).any(), "invalid artifact not isolated")

    equivalence = csv("partial_stats_phase24_gva_policy_equivalence_matrix.csv")
    q12 = equivalence[
        equivalence["left_policy_id"].eq("QP1_G_national_growth_bridge")
        & equivalence["right_policy_id"].eq("QP2_G_indicator_growth_bridge")
    ].iloc[0]
    q13 = equivalence[
        equivalence["left_policy_id"].eq("QP1_G_national_growth_bridge")
        & equivalence["right_policy_id"].eq("QP3_G_pooled_robust_growth")
    ].iloc[0]
    require(float(q12["maximum_prediction_difference"]) < 1e-9, "QP1/QP2 predictions should be equivalent")
    require(float(q13["maximum_prediction_difference"]) < 1e-9, "QP1/QP3 predictions should be equivalent")
    require(q12["equivalence_status"] == "alias_registration_error", "QP2 alias not detected")
    require(q13["equivalence_status"] == "alias_registration_error", "QP3 alias not detected")

    unique = csv("partial_stats_phase24_gva_unique_policy_registry.csv")
    retained = unique[unique["unique_registry_status"].eq("retained_unique_policy")]
    removed = unique[unique["unique_registry_status"].eq("removed_alias_prediction_equivalent_to_qp1")]
    require(set(retained["policy_id"]) == {"QP0_G_seasonal_growth", "QP1_G_national_growth_bridge"}, "unique registry retained wrong policies")
    require(set(removed["policy_id"]) == {"QP2_G_indicator_growth_bridge", "QP3_G_pooled_robust_growth"}, "alias registry wrong")

    sources = csv("partial_stats_phase24_gva_quarterly_source_registry.csv")
    require(sources["source_status"].eq("materialized").sum() == final["materialized_quarterly_source_count"], "materialized source count mismatch")
    require(sources["qualified_for_primary_origin_responsive"].eq("Y").sum() == 0, "proxy-lag sources should not qualify")

    response = csv("partial_stats_phase24_gva_model_response_audit.csv")
    expected = response[response["response_expected"].astype(str).str.lower().eq("true")]
    require(len(expected) > 0, "at least one responsive policy must be registered")
    require(expected["origin_response_status"].eq("expected_response_missing").all(), "missing response must be explicit")

    spatial = csv("partial_stats_phase24_gva_spatial_policy_selection.csv").iloc[0]
    require(int(spatial["registered_source_count"]) >= 3, "registered spatial source count too small")
    require(int(spatial["materialized_source_count"]) == 1, "spatial materialized source count mismatch")
    require(spatial["selection_status"] == "spatial_last_share_retained", "spatial baseline should be retained")

    temporal = csv("partial_stats_phase24_gva_temporal_policy_selection.csv").iloc[0]
    require(temporal["selection_status"] == "temporal_profile_baseline_retained", "temporal baseline should be retained")

    archive = csv("partial_stats_phase24_gva_2026q2_archive_integrity.csv").iloc[0]
    require(str(archive["archive_immutable"]).lower() == "true", "2026Q2 archive not immutable")
    require(archive["original_prediction_hash"] == archive["current_prediction_hash"], "2026Q2 archive hash changed")

    q3 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_2026q3_forecast_archive.parquet")
    require(q3["target_period"].eq("2026Q3").all(), "2026Q3 archive target mismatch")
    require(q3["official_actual_used"].eq("N").all(), "future archive must not use official actual")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase24_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 38)), "report sections must be 1..37")
    for phrase in ["Model Identity Audit", "Policy Equivalence", "2026Q2 Prospective Archive", "아직 주장"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
