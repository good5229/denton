from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT
from run_partial_statistics_phase11 import PHASE10_FORECAST_HASH, P7_POLICY_HASH, SHADOW_POLICY_HASH


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase11_forecast_and_policy_hashes_pass() -> None:
    hashes = read_csv("partial_stats_phase11_input_hash_audit.csv")
    manifest = hashes[
        hashes["artifact"].eq("partial_stats_phase10_forecast_archive_manifest.json")
        & hashes["audit_method"].eq("manifest_seal_hash")
    ].iloc[0]
    assert manifest["status"] == "pass"
    assert manifest["observed_hash"] == PHASE10_FORECAST_HASH
    recompute = hashes[hashes["artifact"].eq("partial_stats_phase10_forecast_archive.csv")].iloc[0]
    assert recompute["status"] in {"pass", "serialization_drift_not_blocking"}
    policy = read_csv("partial_stats_phase11_policy_identity_audit.csv")
    assert policy[policy["policy_role"].eq("incumbent")].iloc[0]["observed_hash"] == P7_POLICY_HASH
    assert policy[policy["policy_role"].eq("shadow_challenger")].iloc[0]["observed_hash"] == SHADOW_POLICY_HASH


def test_phase11_actual_unavailable_does_not_consume_holdout() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase11_final_status.json").read_text(encoding="utf-8"))
    assert final["status"] == "waiting_release_watcher_active"
    assert final["actual_available"] is False
    assert final["one_shot_consumed"] is False
    decision = json.loads((PROCESSED_DIR / "partial_stats_phase11_holdout_decision.json").read_text(encoding="utf-8"))
    assert decision["same_holdout_retuning"] == "prohibited"


def test_phase11_release_pending_is_not_model_failure() -> None:
    failure = read_csv("partial_stats_phase11_failure_classification.csv")
    f0 = failure[failure["failure_code"].eq("F0")].iloc[0]
    assert f0["active"] == "Y"
    assert "do not score" in f0["action"]
    incumbent = read_csv("partial_stats_phase11_incumbent_results.csv")
    shadow = read_csv("partial_stats_phase11_shadow_results.csv")
    assert set(incumbent["evaluation_status"]) == {"pending_release"}
    assert set(shadow["evaluation_status"]) == {"pending_release"}


def test_phase11_raw_holdout_remains_unparsed() -> None:
    raw = json.loads((PROCESSED_DIR / "partial_stats_phase11_holdout_raw_manifest.json").read_text(encoding="utf-8"))
    assert raw["holdout_raw_status"] == "not_available"
    assert raw["target_body_parsed"] is False
    first = read_csv("partial_stats_phase11_release_first_seen.csv")
    assert first.iloc[0]["availability_status"] == "not_detected"


def test_phase11_coverage_is_pending_release() -> None:
    coverage = read_csv("partial_stats_phase11_evaluation_coverage.csv")
    evaluated = coverage[coverage["coverage_metric"].eq("evaluated_rows")].iloc[0]
    assert evaluated["status"] == "pending_release"
    population = read_csv("partial_stats_phase11_evaluation_population.csv")
    assert population.iloc[0]["status"] == "pending_release"


def test_phase11_gpt_handoff_review_exists() -> None:
    text = (ROOT / "reports" / "partial_statistics_estimation_phase11_gpt_handoff.md").read_text(encoding="utf-8")
    assert "direct_existing_chat_injection_not_available" in text
    assert "reports/partial_statistics_estimation_phase11.md" in text
