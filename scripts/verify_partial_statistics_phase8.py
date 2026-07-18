from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT
from run_partial_statistics_phase8 import BOOTSTRAP_ITERATIONS, CSV_OUTPUTS, TARGETS


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    frames = {name: frame(name) for name in CSV_OUTPUTS}

    ksic = frames["partial_stats_phase8_ksic8_9_crosswalk.csv"]
    require(len(ksic) > 0, "KSIC 8->9 crosswalk is empty")
    require((ksic["old_code"].astype(str).str.len() > 0).all(), "KSIC old code missing")
    require((ksic["new_code"].astype(str).str.len() > 0).all(), "KSIC new code missing")
    require((ksic["source_row"].astype(str).str.len() > 0).all(), "KSIC source row trace missing")
    require({"one_to_one", "one_to_many", "many_to_one", "many_to_many"}.intersection(set(ksic["relationship_type"])), "KSIC relationship types missing")

    relationship = frames["partial_stats_phase8_ksic_relationship_audit.csv"]
    row = relationship[relationship["crosswalk"].eq("8_to_9")].iloc[0]
    require(int(row["parsed_rows"]) == len(ksic), "KSIC audit row count mismatch")
    require(row["status"] == "pass", "KSIC 8->9 audit not pass")

    recon = frames["partial_stats_phase8_phase6_phase7_reconciliation.csv"]
    require((recon["judgement"] == "explained_population_difference").all(), "metric mismatch not explained")
    require((recon["blocks_new_model_comparison"] == "N").all(), "metric mismatch still blocks comparison")

    cube = frames["partial_stats_phase8_stable_cube.csv"]
    require(not cube.empty, "stable cube empty")
    require((cube["source_grade"] == "R4").all(), "stable cube source grade should be explicit R4")
    require((pd.to_numeric(cube["value"], errors="coerce").fillna(0) >= 0).all(), "negative stable cube value")
    duplicated = cube.duplicated(["stable_region_key", "stable_industry_code", "reference_year", "target_name"], keep=False)
    require(not duplicated.any(), "duplicate stable cube keys detected")

    cube_audit = frames["partial_stats_phase8_stable_cube_audit.csv"]
    primary_gate = cube_audit[cube_audit["audit_id"].eq("primary_source_grade_gate")]
    require(not primary_gate.empty and primary_gate.iloc[0]["status"] == "blocked_primary", "primary source grade gate not blocked")

    impl = frames["partial_stats_phase8_model_implementation_registry.csv"]
    c1 = impl[impl["model_id"].eq("C1_hierarchical_growth_count_model")].iloc[0]
    require(c1["implementation_status"] == "not_implemented", "C1 count model must not be proxied")
    c3 = impl[impl["model_id"].eq("C3_hierarchical_shrinkage_growth")].iloc[0]
    require(c3["implementation_status"] == "implemented_sensitivity", "C3 sensitivity implementation missing")

    leakage = frames["partial_stats_phase8_vintage_leakage_audit.csv"]
    require((pd.to_numeric(leakage["leakage_rows"], errors="coerce").fillna(0) == 0).all(), "vintage leakage detected")

    bootstrap = frames["partial_stats_phase8_full_refit_bootstrap.csv"]
    require(len(bootstrap) == BOOTSTRAP_ITERATIONS * len(TARGETS), "bootstrap row count changed")
    require((bootstrap["full_refit_executed"] == "N").all(), "bootstrap should be blocked in primary track")

    final_status = json.loads((PROCESSED_DIR / "partial_stats_phase8_final_status.json").read_text(encoding="utf-8"))
    require(final_status["status"] == "blocked_stable_cube", "final status must be blocked_stable_cube")
    require(final_status["challenger_status"] == "none", "challenger should not be frozen")
    require(final_status["incumbent_retained"] is True, "P7 incumbent not retained")
    require(final_status["confirmatory_use"] is False, "confirmatory use must remain false")

    incumbent = json.loads((PROCESSED_DIR / "partial_stats_phase8_incumbent_registry.json").read_text(encoding="utf-8"))
    challenger = json.loads((PROCESSED_DIR / "partial_stats_phase8_challenger_registry.json").read_text(encoding="utf-8"))
    protocol = json.loads((PROCESSED_DIR / "partial_stats_phase8_holdout_protocol.json").read_text(encoding="utf-8"))
    require(incumbent["immutable"] is True, "incumbent should be immutable")
    require(challenger["challenger_status"] == "none", "challenger registry should be none")
    require(protocol["holdout_parse_allowed_now"] is False, "holdout parse should be blocked")

    requests = frames["partial_stats_phase8_user_action_requests.csv"]
    require({"P8-RAW-001", "P8-REL-001"}.issubset(set(requests["request_id"])), "user action requests incomplete")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase8.md").read_text(encoding="utf-8")
    for section in range(1, 39):
        require(f"## {section}." in report, f"report section {section} missing")
    require("No Phase 8 challenger qualified" in report, "final no-challenger conclusion missing")

    execution = frames["partial_stats_phase8_execution_manifest.csv"]
    require((execution["status"] == "completed").all(), "execution manifest incomplete")

    print(
        json.dumps(
            {
                "cp949_csv_count": len(frames),
                "ksic8_9_rows": len(ksic),
                "stable_cube_rows": len(cube),
                "bootstrap_rows": len(bootstrap),
                "final_status": final_status["status"],
                "report": "reports/partial_statistics_estimation_phase8.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
