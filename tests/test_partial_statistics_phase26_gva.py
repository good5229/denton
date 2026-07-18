from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase26_semantic_dimension_and_comparator_gates() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase26_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["phase25_reproduction_status"] == "pass"
    assert final["national_gdp_region_count"] == 1
    assert final["unknown_semantic_dimension_count"] == 0
    assert final["model_used_comparator_match_rate"] >= 0.95

    dim = read_csv("partial_stats_phase26_gva_source_dimension_registry.csv")
    assert dim["semantic_role"].ne("unknown").all()
    assert "recovered_from_region_to_industry" in set(dim["mapping_status"])

    indicator = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase26_gva_indicator_cube.parquet")
    gdp = indicator[indicator["source_family"].eq("rolling_national_quarterly_gdp_real")]
    assert gdp["region_code"].nunique() == 1
    assert gdp["industry_code"].nunique() >= 1

    coverage = read_csv("partial_stats_phase26_gva_comparator_coverage.csv")
    model_used = coverage[coverage["model_used"].eq("Y")]
    assert len(model_used) == final["semantic_qualified_series_count"]
    assert (model_used["match_rate"].astype(float) >= 0.95).all()
    assert (model_used["region_coverage_rate"].astype(float) >= 0.90).all()


def test_phase26_service_and_energy_not_overpromoted() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase26_gva_final_status.json").read_text(encoding="utf-8"))
    service = read_csv("partial_stats_phase26_gva_service_region_audit.csv").iloc[0]
    assert service["classification"] == "collection_filter_error"
    assert float(service["region_coverage_rate"]) == final["service_production_region_coverage"]
    assert service["qp2_use_status"] == "excluded_until_full_region_collection"

    energy = read_csv("partial_stats_phase26_gva_energy_series_collision_audit.csv").iloc[0]
    assert int(energy["phase26_series_id_null_count"]) == 0
    assert int(final["energy_unresolved_duplicate_count"]) == 0
    assert energy["resolution_status"] == "energy_series_quarantined"


def test_phase26_release_asof_and_qp2_remain_diagnostic() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase26_gva_final_status.json").read_text(encoding="utf-8"))
    release = read_csv("partial_stats_phase26_gva_release_evidence_registry.csv")
    assert (release["release_evidence_grade"].isin(["R1", "R2", "R3"]).sum()) >= 1
    assert release[release["release_evidence_grade"].isin(["R4", "R5"])]["primary_origin_allowed"].eq("N").all()

    origin = read_csv("partial_stats_phase26_gva_origin_information_audit.csv")
    assert origin["eligible_source_set_hash"].nunique() == final["independent_origin_count"]

    qp2 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase26_gva_qp2_manufacturing_results.parquet")
    assert len(qp2) == final["QP2_prediction_row_count"]
    assert final["QP2_nonfallback_row_count"] == 0
    assert final["QP2_fallback_rate"] == 1.0
    assert qp2["official_actual_used"].eq("N").all()
    assert qp2["prediction_changed_from_qp1"].eq("N").all()


def test_phase26_historical_electricity_scored_but_sw0_retained() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase26_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["historical_electricity_month_count"] == 36
    assert final["historical_electricity_common_year_count"] >= 2
    assert final["electricity_publication_date_qualification_rate"] == 0.0

    spatial = read_csv("partial_stats_phase26_gva_annual_spatial_holdout.csv")
    sw0 = spatial[spatial["policy_id"].eq("SW0_last_annual_gva_share")].iloc[0]
    swe = spatial[spatial["policy_id"].eq("SW_ELEC_FORECAST")].iloc[0]
    assert int(swe["common_year_count"]) >= 2
    assert float(swe["share_mae"]) > float(sw0["share_mae"])

    selection = read_csv("partial_stats_phase26_gva_spatial_policy_selection.csv").iloc[0]
    assert selection["selected_spatial_policy"] == "SW0_last_annual_gva_share"


def test_phase26_report_and_topic_index() -> None:
    report = (ROOT / "reports" / "partial_statistics_estimation_phase26_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 33))
    assert "Source Dimension Registry" in report
    assert "Energy Series Collision Audit" in report
    assert "Electricity Forecast Spatial Holdout" in report
    assert "아직 주장" in report

    topic = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase26_gva.md" in topic
