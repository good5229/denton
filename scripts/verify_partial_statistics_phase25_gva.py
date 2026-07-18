from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase25_gva_phase24_reproduction.csv",
    "partial_stats_phase25_gva_series_registry.csv",
    "partial_stats_phase25_gva_duplicate_audit.csv",
    "partial_stats_phase25_gva_join_cardinality_audit.csv",
    "partial_stats_phase25_gva_release_evidence_registry.csv",
    "partial_stats_phase25_gva_release_ledger.csv",
    "partial_stats_phase25_gva_origin_information_audit.csv",
    "partial_stats_phase25_gva_qp2_fallback_audit.csv",
    "partial_stats_phase25_gva_revision_utility.csv",
    "partial_stats_phase25_gva_annual_share_holdout.csv",
    "partial_stats_phase25_gva_spatial_policy_selection.csv",
    "partial_stats_phase25_gva_2026q2_one_shot_evaluation.csv",
    "partial_stats_phase25_gva_prospective_archive_manifest.csv",
]

REQUIRED_PARQUETS = [
    "partial_stats_phase25_gva_indicator_cube.parquet",
    "partial_stats_phase25_gva_regional_surprise_cube.parquet",
    "partial_stats_phase25_gva_asof_feature_store.parquet",
    "partial_stats_phase25_gva_qp2_responsive_results.parquet",
    "partial_stats_phase25_gva_electricity_spatial_features.parquet",
    "partial_stats_phase25_gva_building_permit_features.parquet",
    "partial_stats_phase25_gva_factory_registry_features.parquet",
    "partial_stats_phase25_gva_spatial_weight_cube.parquet",
    "partial_stats_phase25_gva_2026q3_qp0_archive.parquet",
    "partial_stats_phase25_gva_2026q3_qp1_archive.parquet",
    "partial_stats_phase25_gva_2026q3_qp2_shadow_archive.parquet",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase25_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "GVA target changed")
    require(final["phase24_reproduction_status"] == "pass", "Phase24 reproduction failed")
    require(final["archive_2026q2_integrity"] == "pass_existing_archive_preserved", "2026Q2 archive not preserved")
    require(final["one_shot_2026q2_result"] == "waiting_first_release", "unexpected 2026Q2 one-shot state")
    require(final["many_to_many_join_count"] == 0, "many-to-many join detected")
    require(abs(float(final["join_row_inflation_rate"])) < 1e-12, "join row inflation detected")
    require(final["r1_r3_qualified_source_count"] == 0, "R1-R3 source count should remain zero")
    require(final["qp2_r_changed_prediction_row_count"] == 0, "QP2-R should not change without qualified source")
    require(final["revision_row_count"] == 0, "revision rows should be zero")
    require(final["qp2_fallback_rate"] == 1.0, "QP2 fallback rate should be 1")
    require(final["production_use"] is False and final["official_statistics_claim"] is False, "forbidden claim")

    for name in REQUIRED_CSVS:
        require(len(csv(name)) > 0, f"empty artifact: {name}")
    for name in REQUIRED_PARQUETS:
        require((PROCESSED_DIR / name).exists(), f"missing artifact: {name}")

    reproduction = csv("partial_stats_phase25_gva_phase24_reproduction.csv")
    require(reproduction["reproduction_status"].eq("pass").all(), "Phase24 reproduction rows failed")

    indicator = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_indicator_cube.parquet")
    key = [
        "source_family",
        "series_id",
        "region_code",
        "industry_code",
        "measure_type",
        "unit",
        "seasonal_adjustment",
        "price_basis",
        "observation_period",
        "vintage_id",
    ]
    require(not indicator.duplicated(key).any(), "canonical indicator key is not unique after repair")

    dup = csv("partial_stats_phase25_gva_duplicate_audit.csv")
    model_used_unresolved = dup[dup["primary_use"].eq("eligible_after_release_gate")]["unresolved_duplicate_count"].astype(int).sum()
    require(model_used_unresolved == 0, "model-used unresolved duplicates must be zero")

    join = csv("partial_stats_phase25_gva_join_cardinality_audit.csv").iloc[0]
    require(join["join_status"] == "pass", "join cardinality audit failed")
    require(int(join["many_to_many_join_count"]) == 0, "many-to-many join count should be zero")
    require(float(join["join_row_inflation_rate"]) == 0.0, "join row inflation should be zero")

    evidence = csv("partial_stats_phase25_gva_release_evidence_registry.csv")
    require(evidence["release_evidence_grade"].isin(["R4", "R5"]).all(), "unexpected primary-grade source without evidence")
    require(evidence["primary_origin_allowed"].eq("N").all(), "R4/R5 source cannot be primary")

    asof = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_asof_feature_store.parquet")
    require(asof["eligibility_status"].eq("blocked_no_R1_R3_release_timestamp").all(), "as-of gate should be release blocked")

    qp2 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_qp2_responsive_results.parquet")
    require(len(qp2) == final["qp2_r_prediction_row_count"], "QP2 row count mismatch")
    require(qp2["prediction_changed_from_qp1"].eq("N").all(), "QP2 should not change predictions")
    require(qp2["fallback_reason"].astype(str).ne("").all(), "QP2 fallback reason missing")

    q3_qp0 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_2026q3_qp0_archive.parquet")
    q3_qp1 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_2026q3_qp1_archive.parquet")
    q3_qp2 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_2026q3_qp2_shadow_archive.parquet")
    for archive in [q3_qp0, q3_qp1, q3_qp2]:
        require(archive["target_period"].eq("2026Q3").all(), "2026Q3 archive target mismatch")
        require(archive["official_actual_used"].eq("N").all(), "future archive must not use official actual")
    require(q3_qp0["forecast_status"].eq("frozen_forecast_rows").all(), "QP0 archive not frozen")
    require(q3_qp1["forecast_status"].eq("frozen_forecast_rows").all(), "QP1 archive not frozen")
    require(q3_qp2["forecast_status"].eq("diagnostic_fallback_archive_not_prospective_shadow").all(), "QP2 archive status mismatch")

    spatial = csv("partial_stats_phase25_gva_spatial_policy_selection.csv").iloc[0]
    require(spatial["selected_spatial_policy"] == "SW0_last_annual_gva_share", "SW0 should remain selected")
    require("blocked" in spatial["electricity_spatial_source_status"], "electricity holdout should be blocked, not promoted")

    event = json.loads((PROCESSED_DIR / "partial_stats_phase25_gva_2026q2_holdout_event_status.json").read_text(encoding="utf-8"))
    require(event["event_status"] == "waiting_first_release", "unexpected 2026Q2 event status")
    require(event["official_actual_used"] is False, "2026Q2 actual cannot be used")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase25_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 29)), "report sections must be 1..28")
    for phrase in ["Series Grain Audit", "Release Evidence Registry", "2026Q3 Forecast Archive", "아직 주장"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
