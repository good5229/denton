from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

try:
    import geopandas as gpd
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Run this verifier with the repository .venv") from exc

from kosis_common import PROCESSED_DIR, ROOT


CSV_OUTPUTS = [
    "phase3_local_source_inventory.csv",
    "phase3_archive_member_inventory.csv",
    "factory_observed_ksic_inventory.csv",
    "factory_ksic_field_audit.csv",
    "factory_multi_ksic_audit.csv",
    "ksic10_official_registry.csv",
    "ksic11_official_registry.csv",
    "ksic10_11_official_crosswalk.csv",
    "ksic_crosswalk_relationship_audit.csv",
    "factory_observed_ksic_mapping.csv",
    "factory_observed_ksic_mapping_audit.csv",
    "factory_ksic_manual_review_queue.csv",
    "korea_sigungu_boundary_inventory.csv",
    "korea_sigungu_geometry_audit.csv",
    "korea_sigungu_geometry_crosswalk.csv",
    "korea_sigungu_centroids.csv",
    "korea_sigungu_queen_edges.csv",
    "korea_sigungu_rook_edges.csv",
    "korea_sigungu_distance_edges.csv",
    "korea_spatial_graph_audit.csv",
    "industrial_complex_geometry_inventory.csv",
    "industrial_complex_geometry_audit.csv",
    "industrial_complex_sigungu_intersections.csv",
    "industrial_complex_sigungu_allocation.csv",
    "industrial_complex_allocation_audit.csv",
    "factory_historical_search_manifest.csv",
    "industrial_complex_api_probe_manifest.csv",
    "industrial_complex_period_inventory.csv",
    "industrial_complex_historical_activity.csv",
    "structural_phase3_source_gates.csv",
    "structural_phase3_execution_manifest.csv",
    "structural_phase3_user_action_requests.csv",
]


def rows(name: str) -> list[dict[str, str]]:
    path = PROCESSED_DIR / name
    with path.open(encoding="cp949", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    for name in CSV_OUTPUTS:
        path = PROCESSED_DIR / name
        require(path.exists(), f"missing output: {name}")
        path.read_text(encoding="cp949")

    registry10 = rows("ksic10_official_registry.csv")
    registry11 = rows("ksic11_official_registry.csv")
    crosswalk = rows("ksic10_11_official_crosswalk.csv")
    relationship = rows("ksic_crosswalk_relationship_audit.csv")
    mapping_audit = rows("factory_observed_ksic_mapping_audit.csv")[0]
    require(len(registry10) == 1196, f"unexpected KSIC10 registry size: {len(registry10)}")
    require(len(registry11) == 1205, f"unexpected KSIC11 registry size: {len(registry11)}")
    require(len(crosswalk) == 1231, f"unexpected crosswalk size: {len(crosswalk)}")
    require(any(row.get("mapping_type") == "one_to_many" and row.get("deterministic_fine_mapping") == "N" for row in crosswalk), "one-to-many relations were not preserved")
    require(all(row.get("one_to_many_collapsed_count", "0") in {"", "0"} for row in relationship), "one-to-many collapse detected")
    require(mapping_audit["row_mapping_gate"] == "fail", "KSIC row gate should remain conservative")
    require(mapping_audit["employee_mapping_gate"] == "fail", "KSIC employee gate should remain conservative")

    gpkg = PROCESSED_DIR / "korea_sigungu_geometry.gpkg"
    require(gpkg.exists(), "missing sigungu GPKG")
    geometry = gpd.read_file(gpkg, layer="model_sigungu_2025q2")
    require(len(geometry) == 228, f"unexpected model geometry count: {len(geometry)}")
    require(int((~geometry.geometry.is_valid).sum()) == 0, "invalid model geometry remains")
    require(int(geometry.geometry.is_empty.sum()) == 0, "empty model geometry remains")
    crosswalk_rows = rows("korea_sigungu_geometry_crosswalk.csv")
    require(len(crosswalk_rows) == 228, f"unexpected geometry crosswalk count: {len(crosswalk_rows)}")
    require(all(row["status"] == "matched" for row in crosswalk_rows), "unmatched model region remains")

    graph_audit = {row["graph_type"]: row for row in rows("korea_spatial_graph_audit.csv")}
    for graph_type in ("queen", "rook", "nearest_3", "nearest_5"):
        require(graph_audit[graph_type]["status"] == "pass", f"{graph_type} graph failed")
        require(graph_audit[graph_type]["asymmetric_edge_count"] == "0", f"{graph_type} asymmetry")
        require(graph_audit[graph_type]["self_edge_count"] == "0", f"{graph_type} self edge")
        require(graph_audit[graph_type]["duplicate_edge_count"] == "0", f"{graph_type} duplicate edge")
    require(graph_audit["nearest_3"]["isolated_node_count"] == "0", "nearest-3 isolate")
    require(graph_audit["nearest_5"]["isolated_node_count"] == "0", "nearest-5 isolate")

    gates = {row["source_group"]: row["status"] for row in rows("structural_phase3_source_gates.csv")}
    require(gates["spatial_graph"] == "pass", "spatial gate did not pass")
    require(gates["ksic"] == "blocked_mapping_quality", "KSIC gate should remain blocked")
    require(gates["industrial_complex_allocation"] == "blocked_geometry_source", "industrial geometry gate should remain source-blocked")

    restart = json.loads((PROCESSED_DIR / "structural_phase3_restart_manifest.json").read_text(encoding="utf-8"))
    require(restart["new_ml_training"] == "prohibited_not_run", "ML training guard changed")
    require(restart["restart_decision"] == "blocked_user_action_required", "unexpected restart decision")
    require((ROOT / restart["report"]).exists(), "integrated report missing")
    print(
        json.dumps(
            {
                "cp949_csv_count": len(CSV_OUTPUTS),
                "ksic10_codes": len(registry10),
                "ksic11_codes": len(registry11),
                "crosswalk_rows": len(crosswalk),
                "spatial_nodes": len(geometry),
                "spatial_gate": gates["spatial_graph"],
                "ksic_gate": gates["ksic"],
                "industrial_gate": gates["industrial_complex_allocation"],
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
