from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def parquet(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_parquet(path)


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase26_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "GVA target changed")
    require(final["phase25_reproduction_status"] == "pass", "Phase25 reproduction failed")
    require(final["holdout_2026q2_event_status"] == "waiting_first_release", "2026Q2 holdout unexpectedly consumed")
    require(final["archive_2026q3_qp2_diagnostic_integrity"] == "pass_existing_archive_preserved", "existing QP2 F0 archive not preserved")
    require(final["production_use"] is False and final["official_statistics_claim"] is False, "forbidden production/statistics claim")

    dim = csv("partial_stats_phase26_gva_source_dimension_registry.csv")
    require(len(dim) > 0, "empty dimension registry")
    require(dim["semantic_role"].ne("unknown").all(), "unknown semantic role remains")
    require(set(dim["semantic_role"]).issubset({"time", "region", "industry", "measure", "unit", "seasonal_adjustment", "price_basis", "indicator_item", "vintage", "other"}), "invalid semantic role")

    indicator = parquet("partial_stats_phase26_gva_indicator_cube.parquet")
    gdp = indicator[indicator["source_family"].eq("rolling_national_quarterly_gdp_real")]
    require(gdp["region_code"].nunique() == 1 and gdp["region_code"].iloc[0] == "00", "national GDP region dimension not recovered")
    require(gdp["industry_code"].nunique() >= 1, "national GDP industry dimension missing")

    service = csv("partial_stats_phase26_gva_service_region_audit.csv").iloc[0]
    require(service["classification"] == "collection_filter_error", "service source must be classified as partial collection")
    require(float(service["region_coverage_rate"]) < 0.9, "service region coverage should remain below QP2 gate")

    energy = csv("partial_stats_phase26_gva_energy_series_collision_audit.csv").iloc[0]
    require(int(energy["phase26_series_id_null_count"]) == 0, "energy series_id null remains")
    require(int(final["energy_unresolved_duplicate_count"]) == 0, "energy unresolved duplicate count should be zero after split/quarantine")
    require(int(energy["quarantined_row_count"]) > 0, "energy collision should be quarantined rather than promoted")

    coverage = csv("partial_stats_phase26_gva_comparator_coverage.csv")
    model_used = coverage[coverage["model_used"].eq("Y")]
    require(len(model_used) >= 1, "no model-used comparator series")
    require((model_used["match_rate"].astype(float) >= 0.95).all(), "model-used match rate below gate")
    require((model_used["region_coverage_rate"].astype(float) >= 0.90).all(), "model-used region coverage below gate")
    require((model_used["many_to_many_join_count"].astype(int) == 0).all(), "many-to-many join in model-used series")
    require((model_used["join_row_inflation_rate"].astype(float) == 0.0).all(), "row inflation in model-used series")

    release = csv("partial_stats_phase26_gva_release_evidence_registry.csv")
    require((release["release_evidence_grade"].isin(["R1", "R2", "R3"]).sum()) >= 1, "no R1-R3 release evidence")
    require(release[release["release_evidence_grade"].isin(["R4", "R5"])]["primary_origin_allowed"].eq("N").all(), "R4/R5 primary origin allowed")

    asof = parquet("partial_stats_phase26_gva_asof_feature_store.parquet")
    require(asof["eligibility_status"].str.contains("future", case=False, na=False).sum() == 0, "future leakage marker found")
    origin = csv("partial_stats_phase26_gva_origin_information_audit.csv")
    require(origin["eligible_source_set_hash"].nunique() == final["independent_origin_count"], "origin hash count mismatch")

    qp2 = parquet("partial_stats_phase26_gva_qp2_manufacturing_results.parquet")
    require(len(qp2) == final["QP2_prediction_row_count"], "QP2 row count mismatch")
    require(qp2["official_actual_used"].eq("N").all(), "QP2 archive used official actual")
    require(qp2["prediction_changed_from_qp1"].eq("N").all(), "QP2 should remain fallback without values")
    require(final["QP2_nonfallback_row_count"] == 0 and final["QP2_fallback_rate"] == 1.0, "QP2 fallback status mismatch")

    e_monthly = parquet("partial_stats_phase26_gva_electricity_monthly_cube.parquet")
    require(e_monthly["reference_month"].nunique() == final["historical_electricity_month_count"], "electricity month count mismatch")
    spatial = csv("partial_stats_phase26_gva_annual_spatial_holdout.csv")
    sw0 = spatial[spatial["policy_id"].eq("SW0_last_annual_gva_share")].iloc[0]
    swe = spatial[spatial["policy_id"].eq("SW_ELEC_FORECAST")].iloc[0]
    require(int(swe["common_year_count"]) >= 2, "electricity forecast common years below minimum")
    require(float(swe["share_mae"]) > float(sw0["share_mae"]), "SW_ELEC unexpectedly beats SW0; update selection gate")
    require(float(final["electricity_publication_date_qualification_rate"]) == 0.0, "electricity official publication-date qualification should remain zero")
    selection = csv("partial_stats_phase26_gva_spatial_policy_selection.csv").iloc[0]
    require(selection["selected_spatial_policy"] == "SW0_last_annual_gva_share", "SW0 should remain selected")

    building = csv("partial_stats_phase26_gva_building_knowledge_time_audit.csv").iloc[0]
    factory = csv("partial_stats_phase26_gva_factory_snapshot_audit.csv").iloc[0]
    require(building["knowledge_time_status"] == "materialized_retrospective_structural_diagnostic", "building source overpromoted")
    require(factory["snapshot_status"] == "factory_snapshot_only", "factory source overpromoted")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase26_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 33)), "report sections must be 1..32")
    for phrase in ["Source Dimension Registry", "Energy Series Collision Audit", "Electricity Forecast Spatial Holdout", "아직 주장"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
