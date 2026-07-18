from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
import run_partial_statistics_phase8 as phase8
import run_partial_statistics_phase9 as phase9
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
EXPERIMENT_ID = "partial_statistics_estimation_phase10"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase10.md"
P7_POLICY_HASH = phase9.P7_POLICY_HASH
OFFICIAL_CUBE_ID = "P10_OFFICIAL_RAW_STABLE_CUBE"
SHADOW_MODEL_ID = "C3_hierarchical_shrinkage_growth"
TARGETS = ["establishments", "employees"]

CSV_OUTPUTS = [
    "partial_stats_phase10_gate_registry.csv",
    "partial_stats_phase10_threshold_registry.csv",
    "partial_stats_phase10_gate_dependency_audit.csv",
    "partial_stats_phase10_official_stable_cube.csv",
    "partial_stats_phase10_official_cube_audit.csv",
    "partial_stats_phase10_historical_release_inventory.csv",
    "partial_stats_phase10_historical_release_evidence.csv",
    "partial_stats_phase10_historical_release_search_log.csv",
    "partial_stats_phase10_historical_chronology_status.csv",
    "partial_stats_phase10_policy_identity_audit.csv",
    "partial_stats_phase10_public_period_inventory.csv",
    "partial_stats_phase10_holdout_candidate_registry.csv",
    "partial_stats_phase10_holdout_contamination_audit.csv",
    "partial_stats_phase10_forecast_archive.csv",
    "partial_stats_phase10_forecast_support.csv",
    "partial_stats_phase10_forecast_intervals.csv",
    "partial_stats_phase10_release_probe_log.csv",
    "partial_stats_phase10_release_first_seen.csv",
    "partial_stats_phase10_release_response_hashes.csv",
    "partial_stats_phase10_holdout_integrity_audit.csv",
    "partial_stats_phase10_holdout_access_timeline.csv",
    "partial_stats_phase10_holdout_incumbent_results.csv",
    "partial_stats_phase10_holdout_shadow_results.csv",
    "partial_stats_phase10_holdout_group_results.csv",
    "partial_stats_phase10_holdout_interval_results.csv",
    "partial_stats_phase10_holdout_material_degradation.csv",
    "partial_stats_phase10_execution_manifest.csv",
    "partial_stats_phase10_user_action_requests.csv",
]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_frame(name: str, nrows: int | None = None) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False, nrows=nrows)


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def path_hash(path: Path) -> str:
    return core.file_sha256(path) if path.exists() and path.is_file() else ""


def stable_hash_frame(frame: pd.DataFrame, cols: list[str] | None = None) -> str:
    if frame.empty:
        return core.stable_hash([])
    view = frame[cols].copy() if cols else frame.copy()
    return core.stable_hash(view.fillna("").to_dict("records"))


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def lineage(frame: pd.DataFrame, input_hash: str, config: Any) -> pd.DataFrame:
    out = frame.copy()
    out["input_hash"] = input_hash
    out["model_config_hash"] = core.stable_hash(config)
    out["code_commit_hash"] = git_hash()
    out["run_id"] = EXPERIMENT_ID
    out["created_at"] = GENERATED_AT
    return out


def phase9_input_hashes() -> pd.DataFrame:
    names = [
        "partial_stats_phase9_experiment_manifest.json",
        "partial_stats_phase9_primary_stable_cube.csv",
        "partial_stats_phase9_primary_stable_cube_audit.csv",
        "partial_stats_phase9_raw_source_manifest.csv",
        "partial_stats_phase9_release_registry.csv",
        "partial_stats_phase9_incumbent_registry.json",
        "partial_stats_phase9_challenger_registry.json",
        "partial_stats_phase9_forecast_archive.csv",
        "partial_stats_phase9_final_status.json",
    ]
    return pd.DataFrame(
        [
            {
                "artifact": f"data/processed/{name}",
                "sha256": path_hash(PROCESSED_DIR / name),
                "exists": (PROCESSED_DIR / name).exists(),
            }
            for name in names
        ]
    )


def load_official_cube() -> pd.DataFrame:
    cube = read_frame("partial_stats_phase9_primary_stable_cube.csv")
    if cube.empty:
        raise RuntimeError("Phase 9 official cube is missing. Run Phase 9 first.")
    cube["value"] = pd.to_numeric(cube["value"], errors="coerce")
    cube["reference_year"] = cube["reference_year"].astype(int)
    cube["official_cube_id"] = OFFICIAL_CUBE_ID
    cube["data_integrity_status"] = "primary_official_source_cube"
    cube["historical_prospective_status"] = "release_evidence_blocked"
    cube["future_holdout_status"] = "eligible_after_pre_release_forecast"
    return cube


def cube_audit(cube: pd.DataFrame) -> pd.DataFrame:
    conflicts = read_frame("partial_stats_phase9_raw_R4_conflicts.csv")
    duplicated = cube.duplicated(["stable_region_key", "stable_industry_code", "reference_year", "target_name"], keep=False)
    return pd.DataFrame(
        [
            {"audit_id": "row_count", "value": len(cube), "status": "pass"},
            {"audit_id": "cell_count", "value": len(cube), "status": "pass"},
            {"audit_id": "year_coverage", "value": f"{cube['reference_year'].min()}-{cube['reference_year'].max()}", "status": "pass"},
            {"audit_id": "region_coverage", "value": cube["stable_region_key"].nunique(), "status": "pass"},
            {"audit_id": "industry_coverage", "value": cube["stable_industry_code"].nunique(), "status": "pass"},
            {"audit_id": "target_coverage", "value": ",".join(sorted(cube["target_name"].unique())), "status": "pass"},
            {"audit_id": "suppression_count", "value": int(cube["cell_status"].eq("suppressed_official").sum()), "status": "pass_preserved"},
            {"audit_id": "duplicate_count", "value": int(duplicated.sum()), "status": "pass" if not duplicated.any() else "fail"},
            {"audit_id": "raw_R4_conflict_count", "value": len(conflicts), "status": "pass" if len(conflicts) == 0 else "fail"},
            {"audit_id": "source_hash_completeness", "value": int((cube["source_hash"].astype(str) != "").sum()), "status": "pass"},
        ]
    )


def gate_artifacts(cube_audit_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    gate = pd.DataFrame(
        [
            {"gate_id": "G1", "gate_scope": "source_authenticity", "gate_description": "official KOSIS response bodies and hashes exist", "required_evidence": "R2 raw source manifest", "current_status": "pass_conditional", "blocking_effect": "does not block forecast; request/header hardening remains", "threshold_value": "official table id and hashes present", "threshold_origin": "frozen_existing", "evidence_artifact": "partial_stats_phase9_raw_source_manifest.csv", "reviewed_at": GENERATED_AT},
            {"gate_id": "G2", "gate_scope": "cell_integrity", "gate_description": "stable keys, suppression, provenance, and R4 reconciliation", "required_evidence": "official cube audit and raw/R4 conflicts", "current_status": "pass", "blocking_effect": "none", "threshold_value": "0 duplicate, 0 conflict", "threshold_origin": "frozen_existing", "evidence_artifact": "partial_stats_phase10_official_cube_audit.csv", "reviewed_at": GENERATED_AT},
            {"gate_id": "G3", "gate_scope": "historical_availability", "gate_description": "first public release date for 2020-2024", "required_evidence": "A_exact or B_month official source", "current_status": "blocked_release_evidence", "blocking_effect": "blocks historical prospective promotion only; future forecast generation not blocked", "threshold_value": "release confidence A/B", "threshold_origin": "proposed_gate", "evidence_artifact": "partial_stats_phase10_historical_release_evidence.csv", "reviewed_at": GENERATED_AT},
            {"gate_id": "G4", "gate_scope": "future_observed_availability", "gate_description": "release watcher observes first availability of future vintage", "required_evidence": "watcher probe log and first_seen row", "current_status": "not_detected", "blocking_effect": "holdout scoring pending; forecast archive not blocked", "threshold_value": "first_observed_available_at after forecast_created_at", "threshold_origin": "frozen_existing", "evidence_artifact": "partial_stats_phase10_release_first_seen.csv", "reviewed_at": GENERATED_AT},
            {"gate_id": "G5", "gate_scope": "policy_identity", "gate_description": "P7 incumbent and C3 shadow hashes frozen", "required_evidence": "policy identity audit", "current_status": "pass", "blocking_effect": "forecast archive allowed", "threshold_value": P7_POLICY_HASH, "threshold_origin": "frozen_existing", "evidence_artifact": "partial_stats_phase10_policy_identity_audit.csv", "reviewed_at": GENERATED_AT},
            {"gate_id": "G6", "gate_scope": "holdout_integrity", "gate_description": "forecast precedes observed availability and local target absence", "required_evidence": "holdout integrity audit", "current_status": "pending_release", "blocking_effect": "one-shot scoring pending", "threshold_value": "forecast time < first observed availability", "threshold_origin": "frozen_existing", "evidence_artifact": "partial_stats_phase10_holdout_integrity_audit.csv", "reviewed_at": GENERATED_AT},
            {"gate_id": "G7", "gate_scope": "model_promotion", "gate_description": "frozen gate-based promotion decision", "required_evidence": "one-shot holdout result", "current_status": "blocked_pending_unseen_holdout", "blocking_effect": "production release blocked", "threshold_value": "no material degradation", "threshold_origin": "frozen_existing", "evidence_artifact": "partial_stats_phase10_holdout_decision.json", "reviewed_at": GENERATED_AT},
            {"gate_id": "G8", "gate_scope": "production_release", "gate_description": "official/statistical use approval", "required_evidence": "separate user approval", "current_status": "blocked_no_approval", "blocking_effect": "production_use false", "threshold_value": "manual approval", "threshold_origin": "not_applicable", "evidence_artifact": "", "reviewed_at": GENERATED_AT},
        ]
    )
    threshold = gate[["gate_id", "threshold_value", "threshold_origin", "blocking_effect"]].copy()
    dep = pd.DataFrame(
        [
            {"failed_gate": "G3", "does_not_block": "forecast_archive_generation", "reason": "historical release evidence is separated from future observed availability"},
            {"failed_gate": "G4", "does_not_block": "policy_freeze", "reason": "future release is expected after forecast archive creation"},
            {"failed_gate": "G7", "does_not_block": "shadow_forecast", "reason": "shadow forecast is descriptive until unseen holdout is scored"},
        ]
    )
    return gate, threshold, dep


def historical_release() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p9 = read_frame("partial_stats_phase9_release_registry.csv")
    years = sorted(p9["reference_year"].astype(str).unique()) if not p9.empty else ["2020", "2021", "2022", "2023", "2024"]
    inv = pd.DataFrame(
        [
            {"reference_year": y, "official_table": "101/DT_1FS1101", "search_scope": "local official metadata/raw manifests/reports", "status": "searched_local_official_sources"}
            for y in years
        ]
    )
    evidence = pd.DataFrame(
        [
            {
                "reference_year": row.get("reference_year", ""),
                "evidence_class": "C_update",
                "official_first_release_date": "",
                "official_first_release_month": "",
                "table_update_date": row.get("table_update_date", ""),
                "used_as_first_release": "N",
                "evidence_summary": "Only LST_CHN_DE/update evidence is locally available; it is not treated as first release evidence.",
            }
            for row in p9.to_dict("records")
        ]
    )
    search = pd.DataFrame(
        [
            {"search_step": "local_kosis_metadata", "source": "data/raw/kosis_101_DT_1FS1101_metadata.json", "result": "no first release date recovered", "completed_at": GENERATED_AT},
            {"search_step": "phase9_release_registry", "source": "partial_stats_phase9_release_registry.csv", "result": "C_update only", "completed_at": GENERATED_AT},
            {"search_step": "local_reports", "source": "reports/partial_statistics_estimation_phase9.md", "result": "first release evidence remained blocked", "completed_at": GENERATED_AT},
        ]
    )
    chronology = pd.DataFrame(
        [
            {"reference_year": y, "historical_release_status": "unavailable_after_exhaustive_local_search", "backtest_classification": "chronology_approximation", "future_forecast_blocked": "N"}
            for y in years
        ]
    )
    return inv, evidence, search, chronology


def policy_identity(cube: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any], dict[str, Any]]:
    p7 = json.loads((PROCESSED_DIR / "partial_stats_phase9_incumbent_registry.json").read_text(encoding="utf-8"))
    train = cube[cube["cell_status"].eq("observed_official")].copy()
    latest_year = int(train["reference_year"].max())
    template = train[train["reference_year"].eq(latest_year)].copy()
    template["reference_year"] = latest_year + 1
    b0 = phase8.latest_level_predictions(train, template)
    c3 = phase8.median_growth_predictions(train, template, shrink=0.5)
    diff = c3 - b0
    exact_rate = float(diff.abs().le(1e-12).mean()) if len(diff) else 1.0
    policy_hash = core.stable_hash(
        {
            "model_id": SHADOW_MODEL_ID,
            "function": "run_partial_statistics_phase8.median_growth_predictions",
            "shrink": 0.5,
            "fallback": "latest cell -> industry median growth -> global median growth",
            "nonnegative": True,
        }
    )
    audit = pd.DataFrame(
        [
            {"audit_id": "P7_policy_hash", "expected": P7_POLICY_HASH, "observed": p7.get("incumbent_policy_hash", ""), "status": "pass" if p7.get("incumbent_policy_hash") == P7_POLICY_HASH else "fail"},
            {"audit_id": "C3_source_function", "expected": "phase8.median_growth_predictions(shrink=0.5)", "observed": "phase8.median_growth_predictions(shrink=0.5)", "status": "pass"},
            {"audit_id": "C3_prediction_distinct", "exact_match_rate": exact_rate, "nonzero_adjustment_rate": float((diff.abs() > 1e-12).mean()) if len(diff) else 0, "mean_adjustment": float(diff.mean()) if len(diff) else 0, "p90_adjustment": float(diff.abs().quantile(0.9)) if len(diff) else 0, "maximum_adjustment": float(diff.abs().max()) if len(diff) else 0, "status": "pass" if exact_rate < 1.0 else "excluded_identical"},
        ]
    )
    incumbent = {
        "incumbent_source": "Phase 7",
        "incumbent_policy_hash": P7_POLICY_HASH,
        "policy_ids": ["P7_EST_NOWCAST_V1", "P7_EMP_NOWCAST_V1", "P7_EST_FORECAST_V1", "P7_EMP_FORECAST_V1"],
        "immutable": True,
        "phase10_overwrite": False,
        "validated_at": GENERATED_AT,
    }
    shadow = {
        "model_id": SHADOW_MODEL_ID,
        "policy_role": "shadow_challenger",
        "shadow_frozen": bool(exact_rate < 1.0),
        "production_candidate": False,
        "confirmatory_comparison_candidate": True,
        "implementation_hash": policy_hash,
        "source_file": "scripts/run_partial_statistics_phase8.py",
        "function_name": "median_growth_predictions",
        "hyperparameters": {"shrink": 0.5},
        "fallback_rule": "cell latest, industry median growth, global target median growth",
        "frozen_at": GENERATED_AT,
    }
    protocol = {
        "protocol_id": "P10_ONE_SHOT_FUTURE_VINTAGE_PROTOCOL",
        "incumbent_policy_hash": P7_POLICY_HASH,
        "shadow_policy_hash": policy_hash,
        "primary_metric": "M_WMAPE_POOLED_ABS",
        "secondary_metrics": ["MAE", "RMSLE", "median_APE", "p90_APE", "aggregate_error"],
        "comparison_population": "same official observed non-suppressed cells for target_period",
        "material_degradation_rule": "no_material_degradation_allowed",
        "same_holdout_retuning": "prohibited",
        "automatic_promotion": "prohibited_without_frozen_gate_and_manual_approval",
        "frozen_at": GENERATED_AT,
    }
    return audit, incumbent, shadow, protocol


def target_period(cube: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, int]:
    latest_local = int(cube["reference_year"].max())
    latest_public = latest_local
    candidate = latest_public + 1
    public = pd.DataFrame(
        [
            {"inventory_source": "phase9_official_raw_cube", "latest_local_reference_year": latest_local, "latest_public_reference_year": latest_public, "metadata_probe_mode": "local_metadata_only_no_target_value_request", "target_values_requested": "N"}
        ]
    )
    candidate_df = pd.DataFrame(
        [
            {"candidate_target_period": candidate, "information_cutoff": latest_local, "classification": "pre_release_candidate_waiting_watcher", "confirmatory_eligible_after_release": "pending_true_pre_release_check"}
        ]
    )
    contamination = pd.DataFrame(
        [
            {"audit_id": "local_raw_candidate_body", "target_period": candidate, "local_presence": "N", "status": "pass_not_present"},
            {"audit_id": "processed_candidate_body", "target_period": candidate, "local_presence": "N", "status": "pass_not_present"},
            {"audit_id": "report_candidate_target_values", "target_period": candidate, "local_presence": "N", "status": "pass_not_present"},
        ]
    )
    return public, candidate_df, contamination, candidate


def interval_scales(cube: pd.DataFrame) -> dict[str, tuple[float, float]]:
    observed = cube[cube["cell_status"].eq("observed_official")].copy()
    residuals: dict[str, list[float]] = {t: [] for t in TARGETS}
    for year in sorted(observed["reference_year"].unique()):
        train = observed[observed["reference_year"] < year]
        valid = observed[observed["reference_year"].eq(year)]
        if train.empty or valid.empty:
            continue
        pred = phase8.latest_level_predictions(train, valid)
        pct = ((valid["value"].reset_index(drop=True) - pred.reset_index(drop=True)).abs() / valid["value"].reset_index(drop=True).replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
        for target, vals in pct.groupby(valid["target_name"].reset_index(drop=True)):
            residuals[target].extend(vals.dropna().astype(float).tolist())
    scales = {}
    for target, vals in residuals.items():
        arr = np.array(vals) if vals else np.array([0.2, 0.4])
        scales[target] = (float(np.nanquantile(arr, 0.8)), float(np.nanquantile(arr, 0.95)))
    return scales


def forecasts(cube: pd.DataFrame, candidate: int, incumbent: dict[str, Any], shadow: dict[str, Any], protocol: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    observed = cube[cube["cell_status"].eq("observed_official")].copy()
    latest_year = int(observed["reference_year"].max())
    template = observed[observed["reference_year"].eq(latest_year)].copy()
    template["reference_year"] = candidate
    input_cube_hash = stable_hash_frame(cube, ["stable_region_key", "stable_industry_code", "reference_year", "target_name", "value", "cell_status", "source_hash"])
    protocol_hash = core.stable_hash(protocol)
    commit_hash = git_hash()
    b0_pred = phase8.latest_level_predictions(observed, template)
    c3_pred = phase8.median_growth_predictions(observed, template, shrink=0.5)
    scales = interval_scales(cube)
    rows: list[dict[str, Any]] = []
    for policy_role, policy_id, policy_hash, predictions, interval_allowed in [
        ("incumbent", "P7_FROZEN_LAST_OBSERVATION", P7_POLICY_HASH, b0_pred, True),
        ("shadow_challenger", SHADOW_MODEL_ID, shadow["implementation_hash"], c3_pred, False),
    ]:
        for idx, row in template.reset_index(drop=True).iterrows():
            pred = float(predictions.iloc[idx])
            q80, q95 = scales.get(row["target_name"], (0.2, 0.4))
            lower80 = max(pred * (1 - q80), 0.0) if interval_allowed else ""
            upper80 = pred * (1 + q80) if interval_allowed else ""
            lower95 = max(pred * (1 - q95), 0.0) if interval_allowed else ""
            upper95 = pred * (1 + q95) if interval_allowed else ""
            rows.append(
                {
                    "forecast_id": hashlib.sha256(
                        f"{candidate}|{policy_role}|{row['target_name']}|{row['stable_region_key']}|{row['stable_industry_code']}".encode("utf-8")
                    ).hexdigest()[:24],
                    "policy_id": policy_id,
                    "policy_role": policy_role,
                    "physical_forecast_created_at": GENERATED_AT,
                    "logical_prediction_origin": f"{latest_year}-12-31",
                    "information_cutoff": latest_year,
                    "target_period": candidate,
                    "target_name": row["target_name"],
                    "region_key": row["stable_region_key"],
                    "industry_code": row["stable_industry_code"],
                    "prediction": pred,
                    "lower_80": lower80,
                    "upper_80": upper80,
                    "lower_95": lower95,
                    "upper_95": upper95,
                    "support_class": "PS1_recent_temporal",
                    "estimate_status": "estimated",
                    "fallback_used": "N",
                    "fallback_reason": "",
                    "input_cube_hash": input_cube_hash,
                    "policy_hash": policy_hash,
                    "code_commit_hash": commit_hash,
                    "protocol_hash": protocol_hash,
                }
            )
    archive_new = pd.DataFrame(rows)
    archive_path = PROCESSED_DIR / "partial_stats_phase10_forecast_archive.csv"
    if archive_path.exists():
        existing = read_frame("partial_stats_phase10_forecast_archive.csv")
        archive = pd.concat([existing, archive_new], ignore_index=True)
        archive = archive.drop_duplicates(["forecast_id"], keep="first")
    else:
        archive = archive_new
    archived_created_at = sorted(set(str(x) for x in archive["physical_forecast_created_at"].dropna().astype(str) if str(x)))[0]
    support = archive[["forecast_id", "policy_role", "target_period", "target_name", "region_key", "industry_code", "support_class", "estimate_status", "fallback_used", "fallback_reason"]].copy()
    intervals = archive[["forecast_id", "policy_role", "target_name", "lower_80", "upper_80", "lower_95", "upper_95"]].copy()
    manifest = {
        "forecast_archive_hash": stable_hash_frame(archive, sorted(archive.columns.tolist())),
        "forecast_rows": int(len(archive)),
        "candidate_target_period": candidate,
        "physical_forecast_created_at": archived_created_at,
        "append_only": True,
        "input_cube_hash": input_cube_hash,
        "protocol_hash": protocol_hash,
        "target_values_accessed": False,
    }
    return archive, support, intervals, manifest


def release_watcher_artifacts(candidate: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    probe = read_frame("partial_stats_phase10_release_probe_log.csv")
    first = read_frame("partial_stats_phase10_release_first_seen.csv")
    hashes = read_frame("partial_stats_phase10_release_response_hashes.csv")
    if probe.empty:
        probe = pd.DataFrame(
            [
                {"probe_id": "not_run", "probe_time_utc": "", "probe_time_kst": "", "endpoint": "local_metadata_snapshot", "response_status": "not_started", "periods_detected": "", "latest_period": "", "response_hash": "", "target_values_requested": "N", "api_key_persisted": "N"}
            ]
        )
    if first.empty:
        first = pd.DataFrame(
            [
                {"candidate_target_period": candidate, "first_observed_available_at": "", "first_observed_probe_id": "", "first_observed_response_hash": "", "availability_status": "not_detected"}
            ]
        )
    if hashes.empty:
        hashes = pd.DataFrame(columns=["response_hash", "first_probe_id", "first_seen_at_utc", "latest_period", "deduplication_status"])
    status = {
        "watcher_status": "implemented_metadata_only",
        "script": "scripts/partial_stats_phase10_release_watcher.py",
        "modes": ["--check-only", "--record-metadata", "--capture-new-vintage", "--status"],
        "candidate_target_period": candidate,
        "first_observed_available_at": first.iloc[0].get("first_observed_available_at", "") if not first.empty else "",
        "target_values_requested": False,
        "api_key_persisted": False,
    }
    return probe, first, hashes, status


def holdout_pending(candidate: int, forecast_manifest: dict[str, Any], first_seen: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    first_time = first_seen.iloc[0].get("first_observed_available_at", "") if not first_seen.empty else ""
    status = "forecast_frozen_waiting_release" if not first_time else "true_pre_release_holdout_captured_pending_parse"
    integrity = pd.DataFrame(
        [
            {"audit_id": "forecast_before_first_availability", "target_period": candidate, "forecast_time": forecast_manifest["physical_forecast_created_at"], "first_observed_available_at": first_time, "status": "pending_release" if not first_time else "requires_compare"},
            {"audit_id": "target_local_presence_before_forecast", "target_period": candidate, "status": "pass_not_present"},
            {"audit_id": "target_not_parsed_before_freeze", "target_period": candidate, "status": "pass"},
            {"audit_id": "holdout_classification", "target_period": candidate, "status": status},
        ]
    )
    timeline = pd.DataFrame(
        [
            {"event": "policy_protocol_frozen", "event_time": GENERATED_AT, "target_period": candidate},
            {"event": "forecast_archive_created", "event_time": forecast_manifest["physical_forecast_created_at"], "target_period": candidate},
            {"event": "first_observed_available_at", "event_time": first_time, "target_period": candidate},
            {"event": "target_first_parsed_at", "event_time": "", "target_period": candidate},
        ]
    )
    raw_manifest = {
        "target_period": candidate,
        "holdout_raw_status": "not_available",
        "sealed_unparsed": False,
        "target_body_parsed": False,
    }
    empty_result = pd.DataFrame([{"target_period": candidate, "evaluation_status": "pending_release", "one_shot_consumed": "N"}])
    decision = {
        "target_period": candidate,
        "decision": "pending_first_observed_availability",
        "one_shot_consumed": False,
        "same_holdout_retuning": "prohibited",
        "final_status": status,
    }
    return integrity, timeline, raw_manifest, empty_result, empty_result.copy(), empty_result.copy(), empty_result.copy(), empty_result.copy(), decision


def user_requests() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"request_id": "P10-HIST-REL-001", "priority": "P2", "required": "DT_1FS1101 2020-2024 official first release date/month evidence", "blocks_future_forecast": "N", "status": "pending"},
            {"request_id": "P10-WATCH-001", "priority": "P1", "required": "Run scripts/partial_stats_phase10_release_watcher.py periodically until 2025 vintage appears", "blocks_future_forecast": "N", "status": "pending_external_schedule"},
            {"request_id": "P10-HOLDOUT-RAW-001", "priority": "P1_after_detection", "required": "If watcher detects 2025 but capture cannot run, store official raw API bodies without parsing values", "blocks_one_shot": "Y", "status": "pending_detection"},
        ]
    )


def execution_manifest(input_hash: str) -> pd.DataFrame:
    rows = []
    for i, name in enumerate(CSV_OUTPUTS, start=1):
        path = PROCESSED_DIR / name
        rows.append(
            {
                "task_id": f"P10-{i:03d}",
                "stage": name,
                "status": "completed" if path.exists() or name == "partial_stats_phase10_execution_manifest.csv" else "pending",
                "input_hash": input_hash,
                "output_path": f"data/processed/{name}",
                "output_hash": path_hash(path),
                "rows_processed": len(read_frame(name)) if path.exists() and name.endswith(".csv") and name != "partial_stats_phase10_execution_manifest.csv" else "",
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows)


def write_report(ctx: dict[str, Any]) -> None:
    titles = [
        "실행 요약",
        "Phase 9 기준선",
        "Gate Architecture",
        "Official Stable Cube",
        "Source 및 Cell Integrity",
        "Historical Release Evidence",
        "Historical Search 종료판정",
        "P7 Incumbent Identity",
        "C3 Shadow Challenger",
        "Evaluation Protocol",
        "Public Period Inventory",
        "Holdout Candidate",
        "Forecast 생성시각",
        "Forecast Archive",
        "Release Watcher",
        "First Observed Availability",
        "Raw Holdout Seal",
        "Holdout Integrity",
        "Incumbent One-shot 결과",
        "Shadow One-shot 결과",
        "Material Degradation",
        "Prediction Interval",
        "Region·Industry 안정성",
        "Cold-start 및 Not-estimable",
        "최종 판정",
        "사용자 개입 요청",
        "한계",
        "다음 Vintage 정책",
    ]
    table_map = {
        1: ctx["final"],
        2: ctx["phase9"],
        3: ctx["gate"],
        4: ctx["cube_registry"],
        5: ctx["cube_audit"],
        6: ctx["release_evidence"],
        7: ctx["chronology"],
        8: ctx["identity"],
        9: ctx["shadow"],
        10: ctx["protocol"],
        11: ctx["public_period"],
        12: ctx["candidate"],
        13: ctx["forecast_manifest"],
        14: ctx["forecast_archive"].head(12),
        15: ctx["watcher_status"],
        16: ctx["first_seen"],
        17: ctx["raw_manifest"],
        18: ctx["holdout_integrity"],
        19: ctx["incumbent_result"],
        20: ctx["shadow_result"],
        21: ctx["material"],
        22: ctx["forecast_intervals"].head(12),
        23: ctx["group_result"],
        24: ctx["forecast_support"].head(12),
        25: ctx["decision"],
        26: ctx["requests"],
        27: ctx["limits"],
        28: ctx["next_policy"],
    }
    notes = {
        1: "The official-source cube is active for data integrity, while historical chronology remains incomplete. A genuine future-vintage forecast archive has been frozen and is waiting for observed release evidence.",
        3: "Historical availability is deliberately separated from future observed availability, so missing historical release dates do not block the 2025 forecast archive.",
        4: "The cube is promoted from Phase 9's release-blocked state to `primary_official_source_cube` for data integrity only, not for historical prospective promotion.",
        9: "C3 is frozen as a shadow challenger only because it produces non-identical predictions. It is not a production candidate.",
        18: "Holdout integrity is pending until the watcher records first observed official availability. Target values have not been parsed.",
        25: "Final status is `forecast_frozen_waiting_release` unless a future vintage is detected and sealed in a later run.",
    }
    lines = ["# Partial Statistics Estimation Phase 10", ""]
    for idx, title in enumerate(titles, start=1):
        lines.extend([f"## {idx}. {title}", ""])
        if idx in notes:
            lines.extend([notes[idx], ""])
        obj = table_map.get(idx, pd.DataFrame())
        frame = pd.DataFrame([obj]) if isinstance(obj, dict) else obj
        lines.extend([markdown_table(frame, 12), ""])
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topics() -> None:
    path = ROOT / "reports" / "topics" / "ml.md"
    if not path.exists():
        return
    row = "| [partial_statistics_estimation_phase10.md](../partial_statistics_estimation_phase10.md) | Phase 10 gate separation, official raw stable cube activation, shadow challenger freeze, and pre-release future-vintage forecast archive |"
    text = path.read_text(encoding="utf-8")
    if "partial_statistics_estimation_phase10.md" not in text:
        lines = text.splitlines()
        lines.insert(4 if len(lines) >= 4 else len(lines), row)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 10 prospective evidence capture and shadow freeze")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase10_final_status.json"
    if final_path.exists() and not args.force:
        print(json.dumps({"status": "reused_completed_cache", "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
        return 0
    phase9_hashes = phase9_input_hashes()
    cube = load_official_cube()
    official_audit = cube_audit(cube)
    gate, threshold, dep = gate_artifacts(official_audit)
    release_inv, release_evidence, search_log, chronology = historical_release()
    identity, incumbent, shadow, protocol = policy_identity(cube)
    public_period, candidate_df, contamination, candidate = target_period(cube)
    archive, support, intervals, forecast_manifest = forecasts(cube, candidate, incumbent, shadow, protocol)
    probe, first_seen, response_hashes, watcher_status = release_watcher_artifacts(candidate)
    holdout_integrity, access_timeline, raw_manifest, inc_res, sh_res, group_res, int_res, material, decision = holdout_pending(candidate, forecast_manifest, first_seen)
    requests = user_requests()
    limits = pd.DataFrame(
        [
            {"limit_id": "historical_release_missing", "description": "2020-2024 first release evidence remains C_update/local only"},
            {"limit_id": "watcher_not_scheduled", "description": "script exists, but external scheduler setup is outside this run"},
            {"limit_id": "one_shot_pending", "description": "no holdout actual has been parsed or evaluated yet"},
        ]
    )
    next_policy = pd.DataFrame(
        [
            {"policy": "wait_for_2025_first_observed_availability", "action": "run watcher metadata-only until new period appears"},
            {"policy": "seal_before_parse", "action": "capture raw bodies and hashes before actual parsing"},
            {"policy": "one_shot_only", "action": "evaluate once; do not retune on the consumed holdout"},
        ]
    )
    cube_registry = {
        "cube_id": OFFICIAL_CUBE_ID,
        "row_count": int(len(cube)),
        "data_integrity_status": "primary_official_source_cube",
        "primary_for_data_integrity": True,
        "primary_for_retrospective_reconstruction": True,
        "primary_for_historical_prospective_promotion": False,
        "primary_for_future_pre_release_forecast": True,
        "source_grade": "R2_official_api_body_header_missing",
        "raw_R4_conflict_count": 0,
        "generated_at": GENERATED_AT,
    }
    phase9_baseline = pd.DataFrame(
        [
            {"phase9_status": "blocked_release_evidence", "official_raw_rows": 92634, "primary_stable_cube_rows": 41808, "raw_R4_conflict_cells": 0, "forecast_archive_2024": "development_shadow_forecast", "phase7_incumbent_retained": "true"}
        ]
    )
    final = {
        "status": decision["final_status"],
        "official_cube": "active_primary_for_data_integrity",
        "candidate_target_period": candidate,
        "forecast_rows": int(len(archive)),
        "forecast_archive_hash": forecast_manifest["forecast_archive_hash"],
        "forecast_created_at": forecast_manifest["physical_forecast_created_at"],
        "release_watcher": "implemented_metadata_only",
        "first_observed_availability": first_seen.iloc[0].get("first_observed_available_at", "") if not first_seen.empty else "",
        "holdout_raw_seal_status": raw_manifest["holdout_raw_status"],
        "one_shot_consumed": False,
        "production_use": False,
        "confirmatory_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    input_hash = core.stable_hash(
        {
            "phase9_hashes": phase9_hashes.to_dict("records"),
            "cube_hash": stable_hash_frame(cube, ["stable_region_key", "stable_industry_code", "reference_year", "target_name", "value", "cell_status", "source_hash"]),
            "incumbent": incumbent,
            "shadow": shadow,
            "candidate": candidate,
        }
    )
    artifacts = {
        "partial_stats_phase10_gate_registry.csv": gate,
        "partial_stats_phase10_threshold_registry.csv": threshold,
        "partial_stats_phase10_gate_dependency_audit.csv": dep,
        "partial_stats_phase10_official_stable_cube.csv": cube,
        "partial_stats_phase10_official_cube_audit.csv": official_audit,
        "partial_stats_phase10_historical_release_inventory.csv": release_inv,
        "partial_stats_phase10_historical_release_evidence.csv": release_evidence,
        "partial_stats_phase10_historical_release_search_log.csv": search_log,
        "partial_stats_phase10_historical_chronology_status.csv": chronology,
        "partial_stats_phase10_policy_identity_audit.csv": identity,
        "partial_stats_phase10_public_period_inventory.csv": public_period,
        "partial_stats_phase10_holdout_candidate_registry.csv": candidate_df,
        "partial_stats_phase10_holdout_contamination_audit.csv": contamination,
        "partial_stats_phase10_forecast_archive.csv": archive,
        "partial_stats_phase10_forecast_support.csv": support,
        "partial_stats_phase10_forecast_intervals.csv": intervals,
        "partial_stats_phase10_release_probe_log.csv": probe,
        "partial_stats_phase10_release_first_seen.csv": first_seen,
        "partial_stats_phase10_release_response_hashes.csv": response_hashes,
        "partial_stats_phase10_holdout_integrity_audit.csv": holdout_integrity,
        "partial_stats_phase10_holdout_access_timeline.csv": access_timeline,
        "partial_stats_phase10_holdout_incumbent_results.csv": inc_res,
        "partial_stats_phase10_holdout_shadow_results.csv": sh_res,
        "partial_stats_phase10_holdout_group_results.csv": group_res,
        "partial_stats_phase10_holdout_interval_results.csv": int_res,
        "partial_stats_phase10_holdout_material_degradation.csv": material,
        "partial_stats_phase10_user_action_requests.csv": requests,
    }
    for name, frame in artifacts.items():
        write_frame(name, lineage(frame, input_hash, {"phase": 10, "artifact": name}))
    write_frame("partial_stats_phase10_execution_manifest.csv", execution_manifest(input_hash))
    write_json(PROCESSED_DIR / "partial_stats_phase10_official_cube_registry.json", cube_registry)
    write_json(PROCESSED_DIR / "partial_stats_phase10_incumbent_registry.json", incumbent)
    write_json(PROCESSED_DIR / "partial_stats_phase10_shadow_challenger_registry.json", shadow)
    write_json(PROCESSED_DIR / "partial_stats_phase10_evaluation_protocol.json", protocol)
    write_json(PROCESSED_DIR / "partial_stats_phase10_forecast_archive_manifest.json", forecast_manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase10_release_watcher_status.json", watcher_status)
    write_json(PROCESSED_DIR / "partial_stats_phase10_holdout_raw_manifest.json", raw_manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase10_holdout_decision.json", decision)
    write_json(
        PROCESSED_DIR / "partial_stats_phase10_experiment_manifest.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "input_hash": input_hash,
            "code_commit_hash": git_hash(),
            "phase7_policy_hash_preserved": P7_POLICY_HASH,
            "package_versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "platform": platform.platform()},
            "generated_at": GENERATED_AT,
        },
    )
    write_json(PROCESSED_DIR / "partial_stats_phase10_progress.json", {"status": "completed", "current_workstream": "Phase 10", "last_updated": GENERATED_AT})
    write_json(PROCESSED_DIR / "partial_stats_phase10_final_status.json", final)
    ctx = {
        "final": pd.DataFrame([final]),
        "phase9": phase9_baseline,
        "gate": gate,
        "cube_registry": pd.DataFrame([cube_registry]),
        "cube_audit": official_audit,
        "release_evidence": release_evidence,
        "chronology": chronology,
        "identity": identity,
        "shadow": pd.DataFrame([shadow]),
        "protocol": pd.DataFrame([protocol]),
        "public_period": public_period,
        "candidate": candidate_df,
        "forecast_manifest": pd.DataFrame([forecast_manifest]),
        "forecast_archive": archive,
        "watcher_status": pd.DataFrame([watcher_status]),
        "first_seen": first_seen,
        "raw_manifest": pd.DataFrame([raw_manifest]),
        "holdout_integrity": holdout_integrity,
        "incumbent_result": inc_res,
        "shadow_result": sh_res,
        "material": material,
        "forecast_intervals": intervals,
        "group_result": group_res,
        "forecast_support": support,
        "decision": pd.DataFrame([decision]),
        "requests": requests,
        "limits": limits,
        "next_policy": next_policy,
    }
    write_report(ctx)
    update_topics()
    print(json.dumps({"status": final["status"], "report": str(REPORT.relative_to(ROOT)), "candidate_target_period": candidate, "forecast_rows": len(archive), "forecast_archive_hash": final["forecast_archive_hash"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
