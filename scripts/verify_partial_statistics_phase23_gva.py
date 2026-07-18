from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase23_gva_official_target_semantic_audit.csv",
    "partial_stats_phase23_gva_official_target_cardinality.csv",
    "partial_stats_phase23_gva_official_target_lineage.csv",
    "partial_stats_phase23_gva_period_key_registry.csv",
    "partial_stats_phase23_gva_period_integrity_audit.csv",
    "partial_stats_phase23_gva_carry_forward_period_audit.csv",
    "partial_stats_phase23_gva_prediction_representation_registry.csv",
    "partial_stats_phase23_gva_official_industry_crosswalk.csv",
    "partial_stats_phase23_gva_alignment_failures.csv",
    "partial_stats_phase23_gva_qp0_growth_results.csv",
    "partial_stats_phase23_gva_qp1_growth_results.csv",
    "partial_stats_phase23_gva_qp2_growth_results.csv",
    "partial_stats_phase23_gva_qp3_growth_results.csv",
    "partial_stats_phase23_gva_qp4_growth_results.csv",
    "partial_stats_phase23_gva_qp5_growth_results.csv",
    "partial_stats_phase23_gva_official_growth_accuracy.csv",
    "partial_stats_phase23_gva_official_direction_accuracy.csv",
    "partial_stats_phase23_gva_official_quarter_comparison.csv",
    "partial_stats_phase23_gva_official_worst_group_results.csv",
    "partial_stats_phase23_gva_official_policy_selection.csv",
    "partial_stats_phase23_gva_origin_registry.csv",
    "partial_stats_phase23_gva_model_response_audit.csv",
    "partial_stats_phase23_gva_revision_utility.csv",
    "partial_stats_phase23_gva_spatial_source_registry.csv",
    "partial_stats_phase23_gva_annual_share_holdout_results.csv",
    "partial_stats_phase23_gva_spatial_policy_selection.csv",
    "partial_stats_phase23_gva_temporal_profile_registry.csv",
    "partial_stats_phase23_gva_profile_coverage.csv",
    "partial_stats_phase23_gva_temporal_profile_validation.csv",
    "partial_stats_phase23_gva_deflator_feasibility.csv",
    "partial_stats_phase23_gva_replay_2025.csv",
    "partial_stats_phase23_gva_execution_manifest.csv",
]

REQUIRED_PARQUETS = [
    "partial_stats_phase23_gva_official_target_deduplicated.parquet",
    "partial_stats_phase23_gva_official_prediction_alignment.parquet",
    "partial_stats_phase23_gva_origin_prediction_cube.parquet",
    "partial_stats_phase23_gva_spatial_weight_cube.parquet",
    "partial_stats_phase23_gva_temporal_profile_cube.parquet",
    "partial_stats_phase23_gva_real_growth_track.parquet",
    "partial_stats_phase23_gva_nominal_level_track.parquet",
    "partial_stats_phase23_gva_quarterly_output_2026.parquet",
    "partial_stats_phase23_gva_prospective_forecast_archive.parquet",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase23_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "GVA target changed")
    require(final["official_target_rows"] == 1740, "official target row count mismatch")
    require(final["primary_target_rows"] == 340, "primary official target row count mismatch")
    require(final["deduplicated_target_rows"] == 1650, "deduplicated target row count mismatch")
    require(final["period_key_error_rows_phase23"] == 0, "Phase23 period keys must be clean")
    require(final["official_statistics_claim"] is False and final["production_use"] is False, "official/production claim not allowed")
    require(final["prospective_holdout_status"] == "frozen_waiting_first_release", "prospective holdout not frozen")

    for name in REQUIRED_CSVS:
        require(len(csv(name)) > 0, f"empty artifact: {name}")
    for name in REQUIRED_PARQUETS:
        require((PROCESSED_DIR / name).exists(), f"missing artifact: {name}")

    semantic = csv("partial_stats_phase23_gva_official_target_semantic_audit.csv")
    require(set(["target_growth", "duplicate_print"]).issubset(set(semantic["row_role"])), "row role classification missing")
    require(semantic["primary_evaluation_flag"].eq("Y").sum() == 340, "primary flag row count mismatch")
    require(semantic["row_role"].eq("duplicate_print").sum() == 90, "duplicate print count mismatch")

    cardinality = csv("partial_stats_phase23_gva_official_target_cardinality.csv")
    require(cardinality["status"].str.contains("pass", regex=False).all(), "cardinality audit failed")

    period = csv("partial_stats_phase23_gva_period_key_registry.csv")
    expected = period["year"].astype(str) + "Q" + period["quarter"].astype(str)
    require(period["period"].eq(period["target_period"]).all(), "period must equal target_period")
    require(period["period"].eq(expected).all(), "period must equal derived year-quarter")

    integrity = csv("partial_stats_phase23_gva_period_integrity_audit.csv")
    phase23 = integrity[integrity["artifact"].eq("phase23_current_outputs")].iloc[0]
    require(int(phase23["period_error_rows"]) == 0 and phase23["status"] == "pass", "Phase23 period identity failed")

    representation = csv("partial_stats_phase23_gva_prediction_representation_registry.csv")
    require(representation["official_alignment_status"].eq("alignable_primary").sum() == final["official_alignable_policy_count"], "alignable policy count mismatch")
    require(representation["official_alignment_status"].str.contains("blocked", regex=False).sum() == final["missing_prediction_blocked_policy_count"], "blocked policy count mismatch")

    alignment = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_official_prediction_alignment.parquet")
    require(alignment["alignment_status"].eq("aligned_primary").all(), "primary alignment should be complete")
    require(alignment["target_period"].isin(["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1"]).all(), "unexpected target period")
    require(alignment["absolute_error_pp"].notna().all(), "growth error missing")

    accuracy = csv("partial_stats_phase23_gva_official_growth_accuracy.csv")
    require(set(["QP0_G_seasonal_growth", "QP1_G_national_growth_bridge"]).issubset(set(accuracy["policy_id"])), "QP0/QP1 official results missing")
    require(num(accuracy["official_mae_pp"]).notna().all(), "official MAE missing")

    output = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_quarterly_output_2026.parquet")
    expected_output = output["year"].astype(str) + "Q" + output["quarter"].astype(str)
    require(output["period"].eq(output["target_period"]).all(), "2026 output period mismatch")
    require(output["period"].eq(expected_output).all(), "2026 output year-quarter mismatch")
    require(output[output["target_period"].eq("2026Q1")]["quarter_status"].str.contains("official_parent_observed", regex=False).all(), "2026Q1 official parent not reflected")

    archive = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_prospective_forecast_archive.parquet")
    require(archive["target_period"].eq("2026Q2").all(), "prospective target period should be 2026Q2")
    require(archive["period"].eq(archive["target_period"]).all(), "archive period mismatch")
    require(archive["archive_status"].eq("frozen_waiting_first_release").all(), "archive not frozen")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase23_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 45)), "report sections must be 1..44")
    for phrase in ["Official Prediction Alignment", "2026Q1 Official Parent", "Prospective Holdout", "아직 주장"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
