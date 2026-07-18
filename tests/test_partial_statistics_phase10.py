from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR
from run_partial_statistics_phase10 import P7_POLICY_HASH


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase10_gate_separation_allows_future_forecast() -> None:
    gate = read_csv("partial_stats_phase10_gate_registry.csv")
    historical = gate[gate["gate_scope"].eq("historical_availability")].iloc[0]
    future = gate[gate["gate_scope"].eq("future_observed_availability")].iloc[0]
    assert historical["current_status"] == "blocked_release_evidence"
    assert "future forecast generation not blocked" in historical["blocking_effect"]
    assert future["current_status"] == "not_detected"


def test_phase10_official_cube_active_for_data_integrity() -> None:
    cube = read_csv("partial_stats_phase10_official_stable_cube.csv")
    assert len(cube) == 41808
    assert set(cube["data_integrity_status"]) == {"primary_official_source_cube"}
    assert (cube["source_hash"].astype(str) != "").all()
    audit = read_csv("partial_stats_phase10_official_cube_audit.csv")
    conflict = audit[audit["audit_id"].eq("raw_R4_conflict_count")].iloc[0]
    assert int(conflict["value"]) == 0


def test_phase10_policy_and_shadow_are_frozen() -> None:
    incumbent = json.loads((PROCESSED_DIR / "partial_stats_phase10_incumbent_registry.json").read_text(encoding="utf-8"))
    assert incumbent["incumbent_policy_hash"] == P7_POLICY_HASH
    assert incumbent["immutable"] is True
    shadow = json.loads((PROCESSED_DIR / "partial_stats_phase10_shadow_challenger_registry.json").read_text(encoding="utf-8"))
    assert shadow["model_id"] == "C3_hierarchical_shrinkage_growth"
    assert shadow["shadow_frozen"] is True
    identity = read_csv("partial_stats_phase10_policy_identity_audit.csv")
    c3 = identity[identity["audit_id"].eq("C3_prediction_distinct")].iloc[0]
    assert float(c3["exact_match_rate"]) < 1.0


def test_phase10_forecast_archive_is_sealed_for_2025() -> None:
    forecast = read_csv("partial_stats_phase10_forecast_archive.csv")
    assert not forecast.empty
    assert set(forecast["target_period"]) == {"2025"}
    assert set(forecast["policy_role"]) == {"incumbent", "shadow_challenger"}
    manifest = json.loads((PROCESSED_DIR / "partial_stats_phase10_forecast_archive_manifest.json").read_text(encoding="utf-8"))
    assert manifest["target_values_accessed"] is False
    assert manifest["forecast_rows"] == len(forecast)


def test_phase10_watcher_is_metadata_only() -> None:
    probe = read_csv("partial_stats_phase10_release_probe_log.csv")
    assert (probe["target_values_requested"] == "N").all()
    assert (probe["api_key_persisted"] == "N").all()
    status = json.loads((PROCESSED_DIR / "partial_stats_phase10_release_watcher_status.json").read_text(encoding="utf-8"))
    assert status["target_values_requested"] is False
    assert status["api_key_persisted"] is False


def test_phase10_holdout_waits_for_release_without_consuming_one_shot() -> None:
    decision = json.loads((PROCESSED_DIR / "partial_stats_phase10_holdout_decision.json").read_text(encoding="utf-8"))
    assert decision["final_status"] == "forecast_frozen_waiting_release"
    assert decision["one_shot_consumed"] is False
    final = json.loads((PROCESSED_DIR / "partial_stats_phase10_final_status.json").read_text(encoding="utf-8"))
    assert final["status"] == "forecast_frozen_waiting_release"
    assert final["production_use"] is False
    assert final["confirmatory_use"] is False
