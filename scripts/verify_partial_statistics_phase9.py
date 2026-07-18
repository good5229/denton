from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT
from run_partial_statistics_phase9 import CSV_OUTPUTS, P7_POLICY_HASH


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    frames = {name: frame(name) for name in CSV_OUTPUTS}

    raw_manifest = frames["partial_stats_phase9_raw_source_manifest.csv"]
    require(len(raw_manifest) >= 900, "raw KOSIS JSON chunk manifest is unexpectedly small")
    require((raw_manifest["api_key_persisted"] == "N").all(), "API key must not be persisted")
    require((raw_manifest["table_id"].str.contains("DT_1FS1101")).all(), "raw manifest must be DT_1FS1101")

    source_grade = frames["partial_stats_phase9_source_grade_registry.csv"]
    require(source_grade["source_grade"].str.contains("R2_official_api_body").any(), "R2 official raw body source grade missing")
    require((source_grade["promotion_allowed"] != "Y").all(), "promotion must remain blocked")

    release = frames["partial_stats_phase9_release_registry.csv"]
    require(not release.empty, "release registry empty")
    require((release["release_confidence"] == "C_update_only").all(), "release evidence should be update-only")
    require((release["primary_track_eligible"] == "N").all(), "release gate must block primary track")

    cube = frames["partial_stats_phase9_primary_stable_cube.csv"]
    require(not cube.empty, "Phase 9 raw stable cube empty")
    require(cube["source_grade"].str.contains("R2_official_api_body").all(), "stable cube should be rebuilt from R2 raw API bodies")
    duplicated = cube.duplicated(["stable_region_key", "stable_industry_code", "reference_year", "target_name"], keep=False)
    require(not duplicated.any(), "duplicate stable cube keys detected")

    cube_audit = frames["partial_stats_phase9_primary_stable_cube_audit.csv"]
    release_gate = cube_audit[cube_audit["audit_id"].eq("release_date_gate")]
    require(not release_gate.empty and release_gate.iloc[0]["status"] == "fail", "release date gate must fail")

    cmp = frames["partial_stats_phase9_raw_R4_cell_comparison.csv"]
    conflicts = frames["partial_stats_phase9_raw_R4_conflicts.csv"]
    require(not cmp.empty, "raw/R4 comparison empty")
    exact_rate = cmp["comparison_status"].isin(["exact_match", "suppression_preserved"]).mean()
    require(exact_rate > 0.99, f"raw/R4 exact-or-suppressed rate too low: {exact_rate}")
    require(len(conflicts) < len(cmp) * 0.01, "raw/R4 conflicts are too large for a preserved derivative")

    integrity = frames["partial_stats_phase9_forecast_archive_integrity.csv"]
    require("development_shadow_forecast" in set(integrity["classification"]), "2024 archive should be development shadow")
    require((integrity["confirmatory_eligible"] == "N").all(), "2024 archive must not be confirmatory")

    incumbent = json.loads((PROCESSED_DIR / "partial_stats_phase9_incumbent_registry.json").read_text(encoding="utf-8"))
    require(incumbent["incumbent_policy_hash"] == P7_POLICY_HASH, "P7 policy hash changed")
    require(incumbent["immutable"] is True, "incumbent must remain immutable")

    cube_registry = json.loads((PROCESSED_DIR / "partial_stats_phase9_cube_registry.json").read_text(encoding="utf-8"))
    require(cube_registry["primary_activation"] is False, "primary activation should remain false")
    require(cube_registry["release_gate"] == "blocked_release_evidence", "cube release gate should be blocked")

    final_status = json.loads((PROCESSED_DIR / "partial_stats_phase9_final_status.json").read_text(encoding="utf-8"))
    require(final_status["status"] == "blocked_release_evidence", "final status must be blocked_release_evidence")
    require(final_status["incumbent_retained"] is True, "incumbent should be retained")
    require(final_status["confirmatory_use"] is False, "confirmatory use must remain false")

    requests = frames["partial_stats_phase9_user_action_requests.csv"]
    require("P9-REL-001" in set(requests["request_id"]), "release evidence user request missing")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase9.md").read_text(encoding="utf-8")
    for section in range(1, 42):
        require(f"## {section}." in report, f"report section {section} missing")
    require("Phase 9 remains blocked on official release evidence" in report, "final blocked-release conclusion missing")

    print(
        json.dumps(
            {
                "cp949_csv_count": len(frames),
                "raw_manifest_files": len(raw_manifest),
                "stable_cube_rows": len(cube),
                "raw_r4_exact_or_suppressed_rate": exact_rate,
                "raw_r4_conflicts": len(conflicts),
                "final_status": final_status["status"],
                "report": "reports/partial_statistics_estimation_phase9.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
