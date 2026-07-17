from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from build_structural_phase4 import CSV_OUTPUTS, REPORT
from kosis_common import PROCESSED_DIR


JSON_OUTPUTS = [
    "factory_ksic_multilevel_gate_status.json",
    "factory_phase4_ml_readiness.json",
    "industrial_geometry_selected_source.json",
    "industrial_complex_phase4_ml_readiness.json",
    "business_employment_selected_source.json",
    "business_employment_phase4_ml_readiness.json",
    "korea_spatial_feature_leakage_rules.json",
    "structural_phase4_restart_manifest.json",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing output: {name}")
    path.read_text(encoding="cp949")
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    frames: dict[str, pd.DataFrame] = {}
    for name in CSV_OUTPUTS:
        frames[name] = frame(name)
    for name in JSON_OUTPUTS:
        path = PROCESSED_DIR / name
        require(path.exists(), f"missing output: {name}")
        json.loads(path.read_text(encoding="utf-8"))

    reconciliation = frames["structural_phase3_metric_reconciliation.csv"].set_index("metric")
    require(reconciliation.loc["unresolved_code_name_pairs", "phase4_recomputed_value"] in {"496", "496.0"}, "496 unresolved pairs were not reconciled")
    require(reconciliation.loc["unresolved_top_frequency_codes", "phase4_recomputed_value"] in {"50", "50.0"}, "top-50 diagnostic metric changed")
    require(reconciliation.loc["unresolved_factory_rows", "phase4_recomputed_value"] in {"2156", "2156.0"}, "unresolved factory row count changed")

    registry9 = frames["ksic9_official_registry.csv"]
    crosswalk9 = frames["ksic9_10_official_crosswalk.csv"]
    require(len(registry9) == 1145, f"unexpected KSIC9 registry size: {len(registry9)}")
    require(registry9["code"].str.fullmatch(r"\d{5}").all(), "KSIC9 code width was not preserved")
    require(len(crosswalk9) == 1377, f"unexpected official KSIC9-10 relationship rows: {len(crosswalk9)}")
    require(crosswalk9["official_page_number"].astype(int).between(866, 944).all(), "KSIC PDF page provenance is invalid")
    require((crosswalk9["mapping_type"] == "one_to_many").any(), "official one-to-many relations disappeared")
    require((crosswalk9.loc[crosswalk9["mapping_type"] == "one_to_many", "deterministic_fine_mapping"] == "N").all(), "one-to-many relation was collapsed")

    for name in ("factory_ksic_fine_mapping.csv", "factory_ksic_group_mapping.csv", "factory_ksic_division_mapping.csv"):
        require(len(frames[name]) == 198235, f"factory mapping row count changed in {name}")
    ksic_gate = json.loads((PROCESSED_DIR / "factory_ksic_multilevel_gate_status.json").read_text(encoding="utf-8"))
    require(ksic_gate["K_FINE"]["row_mapping_rate"] > 0.99, "official KSIC9-10 table did not improve fine row coverage")
    require(ksic_gate["K_FINE"]["employee_weighted_mapping_rate"] < 0.99, "fine employee gate should remain blocked")
    require(all(ksic_gate[level]["status"] == "blocked_mapping_quality" for level in ("K_FINE", "K_GROUP", "K_DIVISION")), "KSIC gate was released without official KSIC8-9 evidence")

    geometry = json.loads((PROCESSED_DIR / "industrial_geometry_selected_source.json").read_text(encoding="utf-8"))
    require(geometry["feature_count"] == 1451, "DAM_PDAN feature count changed")
    require(geometry["geometry_level"] == "G3" and geometry["allocation_role"] == "diagnostic_only", "Point geometry was treated as allocatable")
    require(len(frames["industrial_complex_activity_allocated.csv"]) == 0, "industrial activity was allocated from Point geometry")

    industrial_periods = frames["industrial_activity_period_inventory.csv"]
    available = sorted(industrial_periods.loc[industrial_periods["status"] != "missing", "reference_period"].unique())
    require(available == ["2021Q2"], f"unexpected industrial company-stock coverage: {available}")
    industrial_ready = json.loads((PROCESSED_DIR / "industrial_complex_phase4_ml_readiness.json").read_text(encoding="utf-8"))
    require(industrial_ready["company_stock_2021Q1_2023Q4"] == "incomplete", "one-quarter source was marked complete")
    require(industrial_ready["publication_date"] == "incomplete", "unknown historical release date was accepted")

    static = frames["korea_sigungu_static_spatial_features.csv"]
    centrality = frames["korea_graph_centrality_features.csv"]
    isolation = frames["korea_threshold_graph_isolation_audit.csv"]
    require(len(static) == 228, f"unexpected static spatial feature rows: {len(static)}")
    require(len(centrality) == 456, f"unexpected graph centrality rows: {len(centrality)}")
    isolate_counts = isolation.groupby("graph_type").size().to_dict()
    require(isolate_counts == {"distance_threshold_100km": 2, "distance_threshold_50km": 2}, f"threshold isolate audit changed: {isolate_counts}")
    spatial_rules = json.loads((PROCESSED_DIR / "korea_spatial_feature_leakage_rules.json").read_text(encoding="utf-8"))
    require(spatial_rules["candidate_graphs"] == ["queen", "nearest_5"], "graph candidate set was not frozen")
    require("same_period_actual_residual" in spatial_rules["forbidden_features"], "same-period target leakage guard missing")

    leakage = frames["structural_vintage_leakage_audit.csv"]
    require((leakage["future_information_rows"] == "0").all(), "future information entered the feature registry")
    require((leakage["vintage_reuse_violations"] == "0").all(), "vintage reuse violation found")
    restart = json.loads((PROCESSED_DIR / "structural_phase4_restart_manifest.json").read_text(encoding="utf-8"))
    require(restart["new_ml_training"] == "prohibited_not_run", "ML training guard changed")
    require(restart["same_actual_retuning"] == "prohibited_not_run", "same-actual retuning guard changed")
    require(restart["restart_decision"] == "blocked_source_completion", "restart decision should remain source-blocked")

    report = REPORT.read_text(encoding="utf-8")
    for section in range(1, 25):
        require(f"## {section}." in report, f"integrated report section {section} missing")
    require("2021Q2" in report and "2021Q1과 2021Q3~2023Q4는 비어" in report, "industrial period limitation is not explicit in report")
    require("Point를 이용한 시군구 전량배분은 하지 않았다" in report, "Point allocation prohibition missing in report")

    print(
        json.dumps(
            {
                "cp949_csv_count": len(CSV_OUTPUTS),
                "unknown_candidates_classified": len(frames["phase4_unknown_candidate_classification.csv"]),
                "ksic9_registry_codes": len(registry9),
                "ksic9_10_relationships": len(crosswalk9),
                "factory_mapping_rows_per_level": 198235,
                "industrial_company_stock_periods": available,
                "spatial_regions": len(static),
                "threshold_isolates": isolate_counts,
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
