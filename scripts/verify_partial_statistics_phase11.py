from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT
from run_partial_statistics_phase11 import PHASE10_FORECAST_HASH, P7_POLICY_HASH, SHADOW_POLICY_HASH


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    input_hash = frame("partial_stats_phase11_input_hash_audit.csv")
    manifest_row = input_hash[
        input_hash["artifact"].eq("partial_stats_phase10_forecast_archive_manifest.json")
        & input_hash["audit_method"].eq("manifest_seal_hash")
    ].iloc[0]
    require(manifest_row["observed_hash"] == PHASE10_FORECAST_HASH, "Phase 10 forecast manifest hash changed")
    recompute_row = input_hash[input_hash["artifact"].eq("partial_stats_phase10_forecast_archive.csv")].iloc[0]
    require(recompute_row["status"] in {"pass", "serialization_drift_not_blocking"}, "forecast archive recompute audit has unexpected status")

    policy = frame("partial_stats_phase11_policy_identity_audit.csv")
    incumbent = policy[policy["policy_role"].eq("incumbent")].iloc[0]
    shadow = policy[policy["policy_role"].eq("shadow_challenger")].iloc[0]
    require(incumbent["observed_hash"] == P7_POLICY_HASH and incumbent["status"] == "pass", "incumbent hash mismatch")
    require(shadow["observed_hash"] == SHADOW_POLICY_HASH and shadow["status"] == "pass", "shadow hash mismatch")

    integrity = frame("partial_stats_phase11_forecast_integrity_audit.csv")
    rows = integrity[integrity["audit_id"].eq("forecast_row_count")].iloc[0]
    require(rows["status"] == "pass" and int(rows["observed"]) == 14028, "forecast row count mismatch")
    accessed = integrity[integrity["audit_id"].eq("target_values_accessed")].iloc[0]
    require(accessed["status"] == "pass", "target values should not be accessed")

    health = frame("partial_stats_phase11_watcher_health.csv").iloc[0]
    require(health["status"] == "success_metadata_only", "watcher health should be metadata-only success")
    first_seen = frame("partial_stats_phase11_release_first_seen.csv").iloc[0]
    require(first_seen["availability_status"] == "not_detected", "2025 should not be detected yet")

    raw_manifest = json.loads((PROCESSED_DIR / "partial_stats_phase11_holdout_raw_manifest.json").read_text(encoding="utf-8"))
    require(raw_manifest["target_body_parsed"] is False, "holdout target body must not be parsed")
    require(raw_manifest["holdout_raw_status"] == "not_available", "raw holdout should remain unavailable")

    coverage = frame("partial_stats_phase11_evaluation_coverage.csv")
    evaluated = coverage[coverage["coverage_metric"].eq("evaluated_rows")].iloc[0]
    require(evaluated["status"] == "pending_release", "evaluation rows should be pending")
    incumbent_results = frame("partial_stats_phase11_incumbent_results.csv")
    shadow_results = frame("partial_stats_phase11_shadow_results.csv")
    require((incumbent_results["evaluation_status"] == "pending_release").all(), "incumbent results should be pending")
    require((shadow_results["evaluation_status"] == "pending_release").all(), "shadow results should be pending")

    failure = frame("partial_stats_phase11_failure_classification.csv")
    f0 = failure[failure["failure_code"].eq("F0")].iloc[0]
    require(f0["active"] == "Y", "F0 release pending should be active")

    decision = json.loads((PROCESSED_DIR / "partial_stats_phase11_holdout_decision.json").read_text(encoding="utf-8"))
    require(decision["final_status"] == "waiting_release_watcher_active", "holdout decision status mismatch")
    require(decision["one_shot_consumed"] is False, "one-shot should not be consumed")

    final = json.loads((PROCESSED_DIR / "partial_stats_phase11_final_status.json").read_text(encoding="utf-8"))
    require(final["status"] == "waiting_release_watcher_active", "final status mismatch")
    require(final["actual_available"] is False, "actual should be unavailable")
    require(final["one_shot_consumed"] is False, "final one-shot should not be consumed")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase11.md").read_text(encoding="utf-8")
    for section in range(1, 27):
        require(f"## {section}." in report, f"report section {section} missing")
    handoff = (ROOT / "reports" / "partial_statistics_estimation_phase11_gpt_handoff.md").read_text(encoding="utf-8")
    require("direct_existing_chat_injection_not_available" in handoff, "GPT handoff feasibility conclusion missing")

    print(
        json.dumps(
            {
                "final_status": final["status"],
                "actual_available": final["actual_available"],
                "forecast_rows": int(rows["observed"]),
                "active_failure": "F0_release_pending",
                "report": "reports/partial_statistics_estimation_phase11.md",
                "gpt_handoff": "reports/partial_statistics_estimation_phase11_gpt_handoff.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
