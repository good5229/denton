from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


EXPECTED_MODELS = {
    "B0_parent_share",
    "M1_direct_growth",
    "M2_employee_productivity",
    "M3_establishment_productivity",
    "M4_proxy_residual",
    "M5_fixed_ensemble",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase14_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA", "target must remain GVA")
    require(final["status"] in {"baseline_dominant_after_complete_test", "model_evidence_completed", "proxy_routing_improved"}, "unexpected final status")
    require(final["model_count"] == 6, "model count mismatch")
    require(final["model_origin_count"] == 48, "model-origin count mismatch")
    require(final["summary_model_count_matches_registry"] is True, "summary consistency failed")
    require(final["independent_information_origin_count"] == 8, "information origin count mismatch")
    require(final["collapsed_information_origin_count"] == 0, "collapsed information origin should be zero")
    require(final["monthly_primary_status"] == "blocked_no_eligible_monthly_source", "monthly primary should be blocked")
    require(final["deployable_interval"] is False, "intervals should not be deployable")
    require(final["actual_used_for_selection"] is False, "outer actual must not be used for selection")
    require(final["production_use"] is False and final["official_statistics_claim"] is False, "no production or official claim allowed")

    registry = frame("partial_stats_phase14_gva_model_registry.csv")
    require(set(registry["model_id"]) == EXPECTED_MODELS, "model registry missing expected models")
    require((registry["execution_status"] == "implemented_and_evaluated").all(), "all registered models should be evaluated")
    require(pd.to_numeric(registry["prediction_rows"], errors="coerce").gt(0).all(), "prediction rows missing")
    require(registry["prediction_hash"].astype(str).str.len().gt(0).all(), "prediction hashes missing")

    completeness = frame("partial_stats_phase14_gva_model_result_completeness.csv")
    require((completeness["status"] == "pass").all(), "model completeness failed")
    consistency = frame("partial_stats_phase14_gva_summary_consistency_audit.csv").iloc[0]
    require(consistency["status"] == "pass", "summary consistency audit failed")
    require(int(consistency["summary_model_count"]) == int(consistency["registry_implemented_model_count"]) == int(consistency["accuracy_unique_model_count"]) == 6, "model count fields do not agree")

    info = frame("partial_stats_phase14_gva_information_origin_registry.csv")
    require(info["information_set_id"].nunique() == 8, "information set ids should be distinct")
    response = frame("partial_stats_phase14_gva_origin_response_classification.csv")
    require(len(response) == 48, "response classification row count mismatch")
    b0 = response[response["model_id"].eq("B0_parent_share") & response["origin_response_status"].ne("first_origin_no_previous_response")]
    require((b0["origin_response_status"] == "independent_information_no_model_response").all(), "B0 should be static after first origin")
    m1 = response[response["model_id"].eq("M1_direct_growth") & response["origin_response_status"].ne("first_origin_no_previous_response")]
    require((m1["origin_response_status"] == "independent_information_and_response").all(), "M1 should respond after first origin")

    utilization = frame("partial_stats_phase14_gva_information_utilization.csv")
    m1_util = utilization[utilization["model_id"].eq("M1_direct_growth")]
    require(pd.to_numeric(m1_util["information_utilization_rate"], errors="coerce").gt(0).any(), "M1 should use incremental information")

    monthly = frame("partial_stats_phase14_gva_monthly_source_registry.csv")
    require((monthly["primary_monthly_eligible"] == "N").all(), "monthly sources should remain ineligible")
    calibration = frame("partial_stats_phase14_gva_nested_calibration.csv")
    require((calibration["deployable_interval"] == "false_limited_single_calibration_year").all(), "intervals should be non-deployable")

    annual = frame("partial_stats_phase14_gva_annual_estimates_2025.csv")
    quarterly = frame("partial_stats_phase14_gva_quarterly_estimates_2025.csv")
    nowcast = frame("partial_stats_phase14_gva_annual_nowcast_2026.csv")
    require(len(annual) > 0 and len(quarterly) > 0 and len(nowcast) > 0, "current estimate outputs are empty")
    require((annual["actual_used"] == "N").all() and (quarterly["actual_used"] == "N").all(), "2025 actual should not be used")
    require((annual["recommended_model"] == final["recommended_model"]).all(), "recommended model not stamped on annual estimates")

    execution = frame("partial_stats_phase14_gva_execution_manifest.csv")
    final_row = execution[execution["artifact"].eq("partial_stats_phase14_gva_final_status.json")].iloc[0]
    require(final_row["status"] == "completed", "final status should be completed in execution manifest")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase14_gva.md").read_text(encoding="utf-8")
    section_numbers = [int(m.group(1)) for m in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(section_numbers == list(range(1, 33)), "report sections must be 1..32")
    for phrase in [
        "Model Registry",
        "Model-response Origins",
        "Monthly Source Eligibility",
        "아직 주장할 수 없는 내용",
    ]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(
        json.dumps(
            {
                "status": final["status"],
                "model_count": final["model_count"],
                "model_origin_count": final["model_origin_count"],
                "recommended_model": final["recommended_model"],
                "monthly_primary_status": final["monthly_primary_status"],
                "report": "reports/partial_statistics_estimation_phase14_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
