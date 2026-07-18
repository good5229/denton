from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR
from run_partial_statistics_phase9 import P7_POLICY_HASH


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase9_uses_preserved_official_raw_bodies_without_api_keys() -> None:
    manifest = read_csv("partial_stats_phase9_raw_source_manifest.csv")
    assert len(manifest) >= 900
    assert set(manifest["api_key_persisted"]) == {"N"}
    assert manifest["table_id"].str.contains("DT_1FS1101").all()
    grade = read_csv("partial_stats_phase9_source_grade_registry.csv")
    assert grade["source_grade"].str.contains("R2_official_api_body").any()


def test_phase9_release_gate_blocks_primary_activation() -> None:
    release = read_csv("partial_stats_phase9_release_registry.csv")
    assert set(release["release_confidence"]) == {"C_update_only"}
    assert set(release["primary_track_eligible"]) == {"N"}
    cube_registry = json.loads((PROCESSED_DIR / "partial_stats_phase9_cube_registry.json").read_text(encoding="utf-8"))
    assert cube_registry["primary_activation"] is False
    assert cube_registry["release_gate"] == "blocked_release_evidence"


def test_phase9_rebuilds_raw_cube_without_duplicate_keys() -> None:
    cube = read_csv("partial_stats_phase9_primary_stable_cube.csv")
    assert not cube.empty
    assert cube["source_grade"].str.contains("R2_official_api_body").all()
    assert not cube.duplicated(["stable_region_key", "stable_industry_code", "reference_year", "target_name"]).any()


def test_phase9_raw_r4_reconciliation_is_nearly_exact() -> None:
    comparison = read_csv("partial_stats_phase9_raw_R4_cell_comparison.csv")
    conflicts = read_csv("partial_stats_phase9_raw_R4_conflicts.csv")
    exact_rate = comparison["comparison_status"].isin(["exact_match", "suppression_preserved"]).mean()
    assert exact_rate > 0.99
    assert len(conflicts) < len(comparison) * 0.01


def test_phase9_2024_archive_is_shadow_not_confirmatory() -> None:
    integrity = read_csv("partial_stats_phase9_forecast_archive_integrity.csv")
    assert "development_shadow_forecast" in set(integrity["classification"])
    assert set(integrity["confirmatory_eligible"]) == {"N"}


def test_phase9_incumbent_hash_is_immutable() -> None:
    incumbent = json.loads((PROCESSED_DIR / "partial_stats_phase9_incumbent_registry.json").read_text(encoding="utf-8"))
    assert incumbent["incumbent_policy_hash"] == P7_POLICY_HASH
    assert incumbent["immutable"] is True
    final_status = json.loads((PROCESSED_DIR / "partial_stats_phase9_final_status.json").read_text(encoding="utf-8"))
    assert final_status["status"] == "blocked_release_evidence"
    assert final_status["confirmatory_use"] is False
