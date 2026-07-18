from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


EXPECTED_MODELS = {
    "B0_parent_share",
    "M1_direct_growth",
    "M2_employee_productivity",
    "M3_establishment_productivity",
    "M4_proxy_residual",
    "M5_fixed_ensemble",
}


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase14_summary_counts_match_model_evidence() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase14_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["model_count"] == 6
    assert final["model_origin_count"] == 48
    assert final["summary_model_count_matches_registry"] is True
    assert final["independent_information_origin_count"] == 8
    assert final["collapsed_information_origin_count"] == 0
    assert final["actual_used_for_selection"] is False
    assert final["production_use"] is False
    assert final["official_statistics_claim"] is False

    registry = read_csv("partial_stats_phase14_gva_model_registry.csv")
    assert set(registry["model_id"]) == EXPECTED_MODELS
    assert registry["execution_status"].eq("implemented_and_evaluated").all()
    assert pd.to_numeric(registry["prediction_rows"], errors="coerce").gt(0).all()
    assert registry["prediction_hash"].astype(str).str.len().gt(0).all()


def test_phase14_summary_consistency_and_completeness_pass() -> None:
    completeness = read_csv("partial_stats_phase14_gva_model_result_completeness.csv")
    assert completeness["status"].eq("pass").all()
    consistency = read_csv("partial_stats_phase14_gva_summary_consistency_audit.csv").iloc[0]
    assert consistency["status"] == "pass"
    assert int(consistency["summary_model_count"]) == 6
    assert int(consistency["registry_implemented_model_count"]) == 6
    assert int(consistency["accuracy_unique_model_count"]) == 6
    assert int(consistency["model_origin_result_groups"]) == 48


def test_phase14_information_and_model_response_are_separated() -> None:
    information = read_csv("partial_stats_phase14_gva_information_origin_registry.csv")
    assert information["information_set_id"].nunique() == 8
    response = read_csv("partial_stats_phase14_gva_origin_response_classification.csv")
    assert len(response) == 48
    b0 = response[response["model_id"].eq("B0_parent_share") & response["origin_response_status"].ne("first_origin_no_previous_response")]
    assert b0["origin_response_status"].eq("independent_information_no_model_response").all()
    m1 = response[response["model_id"].eq("M1_direct_growth") & response["origin_response_status"].ne("first_origin_no_previous_response")]
    assert m1["origin_response_status"].eq("independent_information_and_response").all()

    utilization = read_csv("partial_stats_phase14_gva_information_utilization.csv")
    assert pd.to_numeric(utilization[utilization["model_id"].eq("M1_direct_growth")]["information_utilization_rate"], errors="coerce").gt(0).any()


def test_phase14_monthly_interval_and_current_estimate_policies() -> None:
    monthly = read_csv("partial_stats_phase14_gva_monthly_source_registry.csv")
    assert monthly["primary_monthly_eligible"].eq("N").all()
    calibration = read_csv("partial_stats_phase14_gva_nested_calibration.csv")
    assert calibration["deployable_interval"].eq("false_limited_single_calibration_year").all()

    final = json.loads((PROCESSED_DIR / "partial_stats_phase14_gva_final_status.json").read_text(encoding="utf-8"))
    annual = read_csv("partial_stats_phase14_gva_annual_estimates_2025.csv")
    quarterly = read_csv("partial_stats_phase14_gva_quarterly_estimates_2025.csv")
    assert len(annual) > 0 and len(quarterly) > 0
    assert annual["actual_used"].eq("N").all()
    assert quarterly["actual_used"].eq("N").all()
    assert annual["recommended_model"].eq(final["recommended_model"]).all()


def test_phase14_report_has_required_sections_and_limits() -> None:
    report = (ROOT / "reports" / "partial_statistics_estimation_phase14_gva.md").read_text(encoding="utf-8")
    section_numbers = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert section_numbers == list(range(1, 33))
    assert "Model-response Origins" in report
    assert "Monthly Source Eligibility" in report
    assert "아직 주장할 수 없는 내용" in report
