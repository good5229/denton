from __future__ import annotations

import json
import re
import sys

import pandas as pd

from build_structural_phase4b import CSV_OUTPUTS, JSON_OUTPUTS, REPORT
from kosis_common import PROCESSED_DIR


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing CSV output: {name}")
    path.read_text(encoding="cp949")
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    frames = {name: frame(name) for name in CSV_OUTPUTS}
    for name in JSON_OUTPUTS:
        path = PROCESSED_DIR / name
        require(path.exists(), f"missing JSON output: {name}")
        json.loads(path.read_text(encoding="utf-8"))

    artifact = frames["phase4b_artifact_audit.csv"]
    require((artifact["audit_status"] == "pass").all(), "Phase 4 baseline artifact audit did not pass")

    business = frames["phase4b_business_source_scorecard.csv"]
    require("full_industry_coverage_missing" in set(business["primary_exclusion_reason"]), "partial sigungu business source was not excluded")
    partial = business[business["source_id"].eq("kosis_national_establishment_census_sigungu_partial")].iloc[0]
    require(partial["industry_top_level_score"] == "4", "manufacturing/mining partial source received full top-level industry score")
    selected_business = json.loads((PROCESSED_DIR / "phase4b_selected_business_source.json").read_text(encoding="utf-8"))
    selected_employment = json.loads((PROCESSED_DIR / "phase4b_selected_employment_source.json").read_text(encoding="utf-8"))
    require(selected_business["selection_status"] == "blocked_user_action", "business source was selected without passing gates")
    require(selected_employment["selection_status"] == "blocked_user_action", "employment source was selected without passing gates")

    coverage = frames["kosis_business_employment_coverage_audit.csv"]
    row = coverage[coverage["source_dataset"].eq("manufacturing_mining_sigungu_ksic")].iloc[0]
    require(row["period_coverage_pass"] == "Y", "partial manufacturing/mining source should have target-year coverage")
    require(row["full_industry_coverage_pass"] == "N", "partial manufacturing/mining source was misclassified as full-industry")

    kosis_raw = frames["kosis_business_employment_raw_long.csv"]
    require(len(kosis_raw) >= 250000, "KOSIS local mart was not carried into Phase 4B raw long audit")
    first = frames["structural_source_first_eligible_audit.csv"]
    require((first["future_information_rows"] == "0").all(), "future-information leakage audit failed")
    require((first["eligibility_status"] == "blocked_publication").all(), "publication-blocked source was marked eligible")

    factory_ready = json.loads((PROCESSED_DIR / "factory_aggregate_ml_readiness.json").read_text(encoding="utf-8"))
    require(factory_ready["status"] == "blocked_publication", "factory aggregate source should remain publication-blocked")
    factory_rows = frames["factory_aggregate_historical_table.csv"]
    require(len(factory_rows) >= 200, "factory aggregate sigungu rows were not parsed")
    factory_recon = frames["factory_aggregate_total_reconciliation.csv"]
    require((factory_recon["status"] == "pass_current_snapshot").any(), "factory current snapshot total reconciliation was not recorded")
    micro = json.loads((PROCESSED_DIR / "factory_micro_source_final_status.json").read_text(encoding="utf-8"))
    require(micro["status"] == "blocked_missing_history", "factory micro source should remain history-blocked")

    ksic_gate = json.loads((PROCESSED_DIR / "factory_ksic_multilevel_gate_phase4b.json").read_text(encoding="utf-8"))
    require(ksic_gate["ksic8_9_official_relationship"] == "missing", "KSIC8->9 missing gate was not preserved")
    require(ksic_gate["gate_relaxation"] == "prohibited_not_done", "KSIC gate was relaxed")
    require(ksic_gate["K_FINE"]["status"] == "blocked_mapping_quality", "KSIC fine gate unexpectedly passed")

    workbook = frames["industrial_workbook_full_sheet_inventory.csv"]
    require(len(workbook) == 7, f"unexpected industrial workbook sheet count: {len(workbook)}")
    require((workbook["scan_status"] == "complete").all(), "industrial workbook full scan did not complete")
    for value in workbook["first_detected_period"].tolist() + workbook["last_detected_period"].tolist():
        if value:
            match = re.fullmatch(r"(\d{4})Q[1-4]", value)
            require(bool(match), f"invalid detected quarter: {value}")
            require(1900 <= int(match.group(1)) <= 2035, f"detected quarter year out of bounds: {value}")
    periods = frames["industrial_workbook_period_classification.csv"]
    target_periods = set(periods.loc[periods["source_component"].eq("phase4_recovered_activity"), "reference_period"])
    require(target_periods == {f"{year}Q{q}" for year in ("2021", "2022", "2023") for q in range(1, 5)}, "target quarter classification incomplete")
    require("partial_data_available" in set(periods["period_status"]), "2021Q2 partial activity was not preserved")

    api_probe = frames["industrial_api_probe_manifest_phase4b.csv"]
    require((api_probe["request_status"] == "not_called_official_parameters_not_frozen").all(), "industrial API was called before operation freeze")
    api_period = frames["industrial_api_period_inventory_phase4b.csv"]
    require(len(api_period) == 60, "industrial API period inventory did not preserve Phase 4 period grid")

    allocation = frames["industrial_complex_allocatable_value_coverage.csv"]
    require(len(allocation) == 1, "industrial allocation coverage summary missing")
    require(allocation.iloc[0]["coverage_gate"] == "prospective_only_not_target_window", "prospective-only allocation was treated as target-window evidence")
    restricted = frames["industrial_complex_restricted_allocation.csv"]
    require(len(restricted) == 0, "restricted allocation should remain empty until target-window coverage passes")

    spatial = frames["korea_region_archetype_registry.csv"]
    require(len(spatial) == 228, "spatial archetype registry must cover 228 model sigungu regions")
    require((spatial["actual_residual_used"] == "N").all(), "spatial archetype used actual residuals")
    spatial_registry = json.loads((PROCESSED_DIR / "korea_spatial_validation_registry.json").read_text(encoding="utf-8"))
    require(spatial_registry["primary_contiguity_graph"] == "Queen", "primary contiguity graph was not frozen")
    require(spatial_registry["primary_distance_graph"] == "nearest_5", "primary distance graph was not frozen")

    requests = frames["structural_phase4b_user_action_requests.csv"]
    require(len(requests) == 4, "unexpected user-action request count")
    require(requests.loc[requests["request_id"].eq("P4B-003"), "official_url"].str.contains("3069832").any(), "official industrial polygon route missing")

    gates = frames["structural_phase4b_source_gates.csv"]
    require("pass_static_context" in set(gates["status"]), "static spatial source should pass as context")
    require(not gates["status"].str.contains("ml_ready").any(), "a source was marked ML-ready prematurely")
    restart = json.loads((PROCESSED_DIR / "structural_phase4b_restart_manifest.json").read_text(encoding="utf-8"))
    require(restart["at_least_one_structural_source_ml_ready"] is False, "ML-ready flag should remain false")
    require(restart["phase5_preregistration"] == "prohibited", "Phase 5 preregistration was improperly enabled")
    require(restart["new_ml_training"] == "prohibited_not_run", "ML training guard changed")
    require(restart["restart_decision"] == "blocked_source_completion", "restart decision changed")

    report = REPORT.read_text(encoding="utf-8")
    for section in range(1, 27):
        require(f"## {section}." in report, f"Phase 4B report section {section} missing")
    require("ML 재개는 아직 차단" in report, "report did not state ML restart block")
    require("대표점 기반 전량배정은 계속 금지" in report, "report did not preserve point-allocation prohibition")

    print(
        json.dumps(
            {
                "cp949_csv_count": len(CSV_OUTPUTS),
                "json_count": len(JSON_OUTPUTS),
                "kosis_raw_long_rows": len(kosis_raw),
                "factory_aggregate_rows": len(factory_rows),
                "industrial_workbook_sheets": len(workbook),
                "spatial_archetype_rows": len(spatial),
                "user_action_requests": len(requests),
                "restart_decision": restart["restart_decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
