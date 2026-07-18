from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT
from run_partial_statistics_phase10 import P7_POLICY_HASH


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    gate = frame("partial_stats_phase10_gate_registry.csv")
    require({"source_authenticity", "cell_integrity", "historical_availability", "future_observed_availability", "model_promotion"}.issubset(set(gate["gate_scope"])), "gate scopes incomplete")
    hist = gate[gate["gate_scope"].eq("historical_availability")].iloc[0]
    require(hist["current_status"] == "blocked_release_evidence", "historical availability gate should remain blocked")
    require("future forecast generation not blocked" in hist["blocking_effect"], "historical gate should not block future forecast")

    cube = frame("partial_stats_phase10_official_stable_cube.csv")
    require(len(cube) == 41808, "official stable cube row count changed")
    require((cube["data_integrity_status"] == "primary_official_source_cube").all(), "official cube not active for data integrity")
    require((cube["source_hash"].astype(str) != "").all(), "source hash missing in official cube")
    audit = frame("partial_stats_phase10_official_cube_audit.csv")
    conflict = audit[audit["audit_id"].eq("raw_R4_conflict_count")].iloc[0]
    require(int(conflict["value"]) == 0 and conflict["status"] == "pass", "raw/R4 conflict gate failed")
    suppression = audit[audit["audit_id"].eq("suppression_count")].iloc[0]
    require(int(suppression["value"]) > 0 and suppression["status"] == "pass_preserved", "suppression not preserved")

    incumbent = json.loads((PROCESSED_DIR / "partial_stats_phase10_incumbent_registry.json").read_text(encoding="utf-8"))
    require(incumbent["incumbent_policy_hash"] == P7_POLICY_HASH, "P7 hash changed")
    require(incumbent["immutable"] is True, "incumbent should be immutable")
    shadow = json.loads((PROCESSED_DIR / "partial_stats_phase10_shadow_challenger_registry.json").read_text(encoding="utf-8"))
    require(shadow["shadow_frozen"] is True, "C3 shadow should be frozen")
    identity = frame("partial_stats_phase10_policy_identity_audit.csv")
    c3 = identity[identity["audit_id"].eq("C3_prediction_distinct")].iloc[0]
    require(float(c3["exact_match_rate"]) < 1.0, "C3 must be non-identical to incumbent")

    candidate = frame("partial_stats_phase10_holdout_candidate_registry.csv").iloc[0]
    require(candidate["candidate_target_period"] == "2025", "candidate target period should be 2025")
    contamination = frame("partial_stats_phase10_holdout_contamination_audit.csv")
    require((contamination["local_presence"] == "N").all(), "candidate target should not exist locally")

    forecast = frame("partial_stats_phase10_forecast_archive.csv")
    require(not forecast.empty, "forecast archive empty")
    require(set(forecast["policy_role"]) == {"incumbent", "shadow_challenger"}, "forecast should contain incumbent and shadow")
    require((forecast["target_period"] == "2025").all(), "forecast target period mismatch")
    manifest = json.loads((PROCESSED_DIR / "partial_stats_phase10_forecast_archive_manifest.json").read_text(encoding="utf-8"))
    require(manifest["target_values_accessed"] is False, "target values must not be accessed")
    require(manifest["forecast_rows"] == len(forecast), "forecast row manifest mismatch")

    watcher = json.loads((PROCESSED_DIR / "partial_stats_phase10_release_watcher_status.json").read_text(encoding="utf-8"))
    require(watcher["target_values_requested"] is False, "watcher must not request target values")
    require(watcher["api_key_persisted"] is False, "watcher must not persist API key")
    first = frame("partial_stats_phase10_release_first_seen.csv").iloc[0]
    require(first["availability_status"] == "not_detected", "future vintage should not be detected yet")

    decision = json.loads((PROCESSED_DIR / "partial_stats_phase10_holdout_decision.json").read_text(encoding="utf-8"))
    require(decision["final_status"] == "forecast_frozen_waiting_release", "final holdout decision status mismatch")
    require(decision["one_shot_consumed"] is False, "one-shot should not be consumed before actual")

    final = json.loads((PROCESSED_DIR / "partial_stats_phase10_final_status.json").read_text(encoding="utf-8"))
    require(final["status"] == "forecast_frozen_waiting_release", "final status mismatch")
    require(final["one_shot_consumed"] is False, "final status should not consume holdout")
    require(final["production_use"] is False and final["confirmatory_use"] is False, "production/confirmatory use must remain false")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase10.md").read_text(encoding="utf-8")
    for section in range(1, 29):
        require(f"## {section}." in report, f"report section {section} missing")

    print(
        json.dumps(
            {
                "official_cube_rows": len(cube),
                "forecast_rows": len(forecast),
                "candidate_target_period": candidate["candidate_target_period"],
                "forecast_archive_hash": manifest["forecast_archive_hash"],
                "final_status": final["status"],
                "report": "reports/partial_statistics_estimation_phase10.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
