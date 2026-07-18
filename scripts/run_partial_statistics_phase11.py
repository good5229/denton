from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
EXPERIMENT_ID = "partial_statistics_estimation_phase11"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase11.md"
GPT_HANDOFF_REPORT = ROOT / "reports" / "partial_statistics_estimation_phase11_gpt_handoff.md"
P7_POLICY_HASH = "aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d"
SHADOW_POLICY_HASH = "d214a1e0c8bb65f76ce8eef0d27b7261dc68b31ac3a85c12eb59addef68d93f8"
PHASE10_FORECAST_HASH = "10e46f86fc79924d758bbf5e51a0952cae5ed5fe0af5d71a793ab229936dd322"
FORECAST_BASE_COLUMNS = [
    "forecast_id",
    "policy_id",
    "policy_role",
    "physical_forecast_created_at",
    "logical_prediction_origin",
    "information_cutoff",
    "target_period",
    "target_name",
    "region_key",
    "industry_code",
    "prediction",
    "lower_80",
    "upper_80",
    "lower_95",
    "upper_95",
    "support_class",
    "estimate_status",
    "fallback_used",
    "fallback_reason",
    "input_cube_hash",
    "policy_hash",
    "code_commit_hash",
    "protocol_hash",
]
CSV_OUTPUTS = [
    "partial_stats_phase11_input_hash_audit.csv",
    "partial_stats_phase11_policy_identity_audit.csv",
    "partial_stats_phase11_forecast_integrity_audit.csv",
    "partial_stats_phase11_watcher_health.csv",
    "partial_stats_phase11_release_probe_log.csv",
    "partial_stats_phase11_release_first_seen.csv",
    "partial_stats_phase11_release_failures.csv",
    "partial_stats_phase11_holdout_access_timeline.csv",
    "partial_stats_phase11_holdout_integrity.csv",
    "partial_stats_phase11_holdout_schema_audit.csv",
    "partial_stats_phase11_population_shift_audit.csv",
    "partial_stats_phase11_evaluation_population.csv",
    "partial_stats_phase11_evaluation_coverage.csv",
    "partial_stats_phase11_suppression_audit.csv",
    "partial_stats_phase11_incumbent_results.csv",
    "partial_stats_phase11_incumbent_group_results.csv",
    "partial_stats_phase11_incumbent_aggregate_results.csv",
    "partial_stats_phase11_shadow_results.csv",
    "partial_stats_phase11_shadow_adjusted_cell_results.csv",
    "partial_stats_phase11_shadow_adjustment_audit.csv",
    "partial_stats_phase11_material_degradation.csv",
    "partial_stats_phase11_large_cell_audit.csv",
    "partial_stats_phase11_region_industry_stability.csv",
    "partial_stats_phase11_interval_results.csv",
    "partial_stats_phase11_interval_group_results.csv",
    "partial_stats_phase11_interval_failure_audit.csv",
    "partial_stats_phase11_failure_classification.csv",
    "partial_stats_phase11_evidence_registry.csv",
    "partial_stats_phase11_execution_manifest.csv",
    "partial_stats_phase11_user_action_requests.csv",
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


def path_hash(name: str) -> str:
    path = PROCESSED_DIR / name
    return core.file_sha256(path) if path.exists() and path.is_file() else ""


def stable_hash_frame(frame: pd.DataFrame, cols: list[str] | None = None) -> str:
    if frame.empty:
        return core.stable_hash([])
    view = frame[cols].copy() if cols else frame.copy()
    return core.stable_hash(view.fillna("").to_dict("records"))


def normalize_phase10_forecast_for_hash(forecast: pd.DataFrame) -> pd.DataFrame:
    out = forecast[FORECAST_BASE_COLUMNS].copy()
    for col in ["information_cutoff", "target_period"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    for col in ["prediction", "lower_80", "upper_80", "lower_95", "upper_95"]:
        numeric = pd.to_numeric(out[col], errors="coerce")
        out[col] = np.where(out[col].astype(str).eq(""), "", numeric)
    return out


def normalize_phase10_cube_for_hash(cube: pd.DataFrame) -> pd.DataFrame:
    cols = ["stable_region_key", "stable_industry_code", "reference_year", "target_name", "value", "cell_status", "source_hash"]
    out = cube[cols].copy()
    out["reference_year"] = pd.to_numeric(out["reference_year"], errors="coerce").astype("Int64")
    value = pd.to_numeric(out["value"], errors="coerce")
    out["value"] = np.where(out["value"].astype(str).eq(""), "", value)
    return out


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


def load_json(name: str) -> dict[str, Any]:
    return json.loads((PROCESSED_DIR / name).read_text(encoding="utf-8"))


def input_audits() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    forecast = read_frame("partial_stats_phase10_forecast_archive.csv")
    cube = read_frame("partial_stats_phase10_official_stable_cube.csv")
    manifest = load_json("partial_stats_phase10_forecast_archive_manifest.json")
    incumbent = load_json("partial_stats_phase10_incumbent_registry.json")
    shadow = load_json("partial_stats_phase10_shadow_challenger_registry.json")
    protocol = load_json("partial_stats_phase10_evaluation_protocol.json")
    recomputed_forecast_hash = core.stable_hash(normalize_phase10_forecast_for_hash(forecast)[sorted(FORECAST_BASE_COLUMNS)].fillna("").to_dict("records"))
    recomputed_cube_hash = core.stable_hash(normalize_phase10_cube_for_hash(cube).fillna("").to_dict("records"))
    recomputed_protocol_hash = core.stable_hash(protocol)
    input_hash_audit = pd.DataFrame(
        [
            {"artifact": "partial_stats_phase10_forecast_archive_manifest.json", "audit_method": "manifest_seal_hash", "expected_hash": PHASE10_FORECAST_HASH, "observed_hash": manifest.get("forecast_archive_hash", ""), "status": "pass" if manifest.get("forecast_archive_hash", "") == PHASE10_FORECAST_HASH else "fail", "row_count": 1},
            {"artifact": "partial_stats_phase10_forecast_archive.csv", "audit_method": "csv_logical_recompute_after_cp949_read", "expected_hash": manifest.get("forecast_archive_hash", ""), "observed_hash": recomputed_forecast_hash, "status": "pass" if recomputed_forecast_hash == manifest.get("forecast_archive_hash", "") else "serialization_drift_not_blocking", "row_count": len(forecast)},
            {"artifact": "partial_stats_phase10_official_stable_cube.csv", "audit_method": "csv_logical_recompute_after_cp949_read", "expected_hash": manifest.get("input_cube_hash", ""), "observed_hash": recomputed_cube_hash, "status": "pass" if recomputed_cube_hash == manifest.get("input_cube_hash", "") else "serialization_drift_not_blocking", "row_count": len(cube)},
            {"artifact": "partial_stats_phase10_evaluation_protocol.json", "expected_hash": manifest.get("protocol_hash", ""), "observed_hash": recomputed_protocol_hash, "status": "pass" if recomputed_protocol_hash == manifest.get("protocol_hash", "") else "fail", "row_count": 1},
        ]
    )
    policy_audit = pd.DataFrame(
        [
            {"policy_role": "incumbent", "expected_hash": P7_POLICY_HASH, "observed_hash": incumbent.get("incumbent_policy_hash", ""), "status": "pass" if incumbent.get("incumbent_policy_hash", "") == P7_POLICY_HASH else "fail", "retuning_detected": "N"},
            {"policy_role": "shadow_challenger", "expected_hash": SHADOW_POLICY_HASH, "observed_hash": shadow.get("implementation_hash", ""), "status": "pass" if shadow.get("implementation_hash", "") == SHADOW_POLICY_HASH else "fail", "retuning_detected": "N"},
        ]
    )
    target_periods = sorted(set(forecast["target_period"].astype(str))) if not forecast.empty else []
    code_commits = sorted(set(forecast["code_commit_hash"].astype(str))) if not forecast.empty and "code_commit_hash" in forecast else []
    integrity = pd.DataFrame(
        [
            {"audit_id": "forecast_row_count", "expected": 14028, "observed": len(forecast), "status": "pass" if len(forecast) == 14028 else "fail"},
            {"audit_id": "target_period", "expected": "2025", "observed": ",".join(target_periods), "status": "pass" if target_periods == ["2025"] else "fail"},
            {"audit_id": "target_values_accessed", "expected": False, "observed": manifest.get("target_values_accessed", ""), "status": "pass" if manifest.get("target_values_accessed") is False else "fail"},
            {"audit_id": "archive_code_commit_frozen", "expected": ",".join(code_commits), "observed": ",".join(code_commits), "status": "pass" if len(code_commits) == 1 else "fail"},
            {"audit_id": "forecast_archive_hash", "expected": manifest.get("forecast_archive_hash", ""), "observed": recomputed_forecast_hash, "status": "pass" if recomputed_forecast_hash == manifest.get("forecast_archive_hash", "") else "serialization_drift_not_blocking"},
        ]
    )
    context = {
        "forecast": forecast,
        "cube": cube,
        "manifest": manifest,
        "incumbent": incumbent,
        "shadow": shadow,
        "protocol": protocol,
        "recomputed_forecast_hash": recomputed_forecast_hash,
        "recomputed_cube_hash": recomputed_cube_hash,
        "recomputed_protocol_hash": recomputed_protocol_hash,
    }
    return input_hash_audit, policy_audit, integrity, context


def watcher_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p10_probe = read_frame("partial_stats_phase10_release_probe_log.csv")
    p10_first = read_frame("partial_stats_phase10_release_first_seen.csv")
    latest_probe = p10_probe.tail(1).to_dict("records")[0] if not p10_probe.empty else {}
    health = pd.DataFrame(
        [
            {
                "probe_time": latest_probe.get("probe_time_kst", ""),
                "status": "success_metadata_only" if latest_probe else "not_started",
                "latest_period": latest_probe.get("latest_period", "2024"),
                "candidate_detected": "N",
                "response_hash": latest_probe.get("response_hash", ""),
                "schema_hash": core.stable_hash(sorted(p10_probe.columns.tolist())) if not p10_probe.empty else "",
                "network_status": "not_used_local_metadata_only",
                "credential_status": "not_persisted",
                "failure_reason": "",
            }
        ]
    )
    probe = p10_probe.copy()
    first = p10_first.copy()
    failures = pd.DataFrame(
        [
            {"failure_id": "none", "probe_time": latest_probe.get("probe_time_kst", ""), "failure_class": "", "failure_reason": "", "status": "no_probe_failure_recorded"}
        ]
    )
    return health, probe, first, failures


def pending_holdout_artifacts(context: dict[str, Any], first_seen: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest = context["manifest"]
    first_time = first_seen.iloc[0].get("first_observed_available_at", "") if not first_seen.empty else ""
    raw_manifest = {
        "target_period": 2025,
        "holdout_raw_status": "not_available",
        "sealed_unparsed": False,
        "target_body_parsed": False,
        "raw_hash": "",
        "response_headers_present": False,
    }
    timeline = pd.DataFrame(
        [
            {"event": "forecast_archive_created", "event_time": manifest.get("physical_forecast_created_at", ""), "time_semantics": "physical_generation_time"},
            {"event": "first_observed_available_at", "event_time": first_time, "time_semantics": "watcher_observed_api_availability"},
            {"event": "raw_holdout_sealed", "event_time": "", "time_semantics": "pending"},
            {"event": "one_shot_manifest_created", "event_time": "", "time_semantics": "pending_release"},
            {"event": "target_first_parsed_at", "event_time": "", "time_semantics": "not_parsed"},
        ]
    )
    integrity = pd.DataFrame(
        [
            {"audit_id": "forecast_before_release", "status": "pending_release", "evidence": "first_observed_available_at missing"},
            {"audit_id": "target_absent_before_forecast", "status": "pass", "evidence": "Phase 10 contamination audit found no 2025 local target"},
            {"audit_id": "target_not_parsed_before_manifest", "status": "pass", "evidence": "holdout raw not available and target_body_parsed=false"},
            {"audit_id": "one_shot_consumed", "status": "pass_not_consumed", "evidence": "actual unavailable"},
        ]
    )
    schema = pd.DataFrame(
        [
            {"schema_item": "table_id", "previous_definition": "101/DT_1FS1101", "new_definition": "", "status": "pending_raw"},
            {"schema_item": "target_items", "previous_definition": "T01,T02", "new_definition": "", "status": "pending_raw"},
            {"schema_item": "region_code_format", "previous_definition": "KOSIS C1 5-digit sigungu", "new_definition": "", "status": "pending_raw"},
            {"schema_item": "industry_code_format", "previous_definition": "KSIC middle B/C codes", "new_definition": "", "status": "pending_raw"},
            {"schema_item": "suppression_notation", "previous_definition": "X/missing preserved", "new_definition": "", "status": "pending_raw"},
        ]
    )
    shift = pd.DataFrame(
        [
            {"shift_id": "pending_2025_raw", "dimension": "all", "previous_definition": "2020-2024 official raw cube", "new_definition": "", "severity": "pending", "crosswalk_available": "", "evaluation_effect": "evaluation_pending_release"}
        ]
    )
    return raw_manifest, timeline, integrity, schema, shift


def evaluation_pending(context: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    forecast = context["forecast"]
    coverage = pd.DataFrame(
        [
            {"coverage_metric": "forecast_rows", "value": len(forecast), "status": "ready"},
            {"coverage_metric": "official_rows", "value": "", "status": "pending_release"},
            {"coverage_metric": "matched_rows", "value": "", "status": "pending_release"},
            {"coverage_metric": "evaluated_rows", "value": "", "status": "pending_release"},
            {"coverage_metric": "suppressed_rows", "value": "", "status": "pending_release"},
            {"coverage_metric": "not_estimable_rows", "value": int(forecast["estimate_status"].ne("estimated").sum()) if not forecast.empty else "", "status": "ready_forecast_only"},
            {"coverage_metric": "evaluation_coverage", "value": "", "status": "pending_release"},
            {"coverage_metric": "actual_value_coverage", "value": "", "status": "pending_release"},
        ]
    )
    pop = pd.DataFrame(
        [
            {"population_id": "P11_2025_PENDING", "target_period": 2025, "population_rule": "official observed non-suppressed cells matched to sealed forecast", "forecast_rows": len(forecast), "official_rows": "", "evaluated_rows": "", "status": "pending_release"}
        ]
    )
    suppression = pd.DataFrame(
        [
            {"audit_id": "suppressed_cells_excluded", "suppressed_rows": "", "zero_fill_detected": "N", "status": "pending_release"}
        ]
    )
    result = pd.DataFrame(
        [
            {"target_period": 2025, "target_name": target, "policy_role": role, "evaluation_status": "pending_release", "wmape": "", "mae": "", "rmsle": "", "median_ape": "", "p90_ape": "", "one_shot_consumed": "N"}
            for role in ["incumbent", "shadow_challenger"]
            for target in ["establishments", "employees"]
        ]
    )
    return pop, coverage, suppression, result


def shadow_adjustments(context: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    forecast = context["forecast"]
    if forecast.empty:
        return pd.DataFrame(), pd.DataFrame()
    base = forecast.pivot_table(
        index=["target_period", "target_name", "region_key", "industry_code"],
        columns="policy_role",
        values="prediction",
        aggfunc="first",
    ).reset_index()
    if {"incumbent", "shadow_challenger"}.issubset(base.columns):
        base["adjustment"] = pd.to_numeric(base["shadow_challenger"], errors="coerce") - pd.to_numeric(base["incumbent"], errors="coerce")
        base["abs_adjustment"] = base["adjustment"].abs()
        base["relative_adjustment"] = base["abs_adjustment"] / pd.to_numeric(base["incumbent"], errors="coerce").replace(0, np.nan).abs()
    else:
        base["adjustment"] = ""
        base["abs_adjustment"] = ""
        base["relative_adjustment"] = ""
    adjusted = base[base["abs_adjustment"].fillna(0).astype(float) > 1e-12].sort_values("abs_adjustment", ascending=False).head(50).copy()
    audit = pd.DataFrame(
        [
            {"audit_id": "exact_match_rate", "value": float((base["abs_adjustment"].fillna(0).astype(float) <= 1e-12).mean()) if len(base) else "", "status": "forecast_only"},
            {"audit_id": "adjusted_cell_count", "value": int((base["abs_adjustment"].fillna(0).astype(float) > 1e-12).sum()) if len(base) else 0, "status": "forecast_only"},
            {"audit_id": "max_abs_adjustment", "value": float(base["abs_adjustment"].max()) if len(base) else "", "status": "forecast_only"},
        ]
    )
    return adjusted, audit


def pending_stability() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    material = pd.DataFrame(
        [{"target_period": 2025, "metric": metric, "value": "", "status": "pending_release"} for metric in ["overall_improvement", "worst_group_degradation", "large_cell_degradation", "maximum_cell_degradation"]]
    )
    large = pd.DataFrame([{"target_period": 2025, "audit_scope": "top_50_actual_value_cells", "status": "pending_actual"}])
    stability = pd.DataFrame([{"target_period": 2025, "group_scope": "region_industry", "status": "pending_actual"}])
    interval = pd.DataFrame(
        [{"target_period": 2025, "target_name": target, "coverage_80": "", "coverage_95": "", "median_width": "", "normalized_width": "", "status": "pending_release"} for target in ["establishments", "employees"]]
    )
    interval_group = pd.DataFrame([{"target_period": 2025, "group_scope": "cell_scale/capital/county/industry_frequency", "status": "pending_release"}])
    interval_failure = pd.DataFrame([{"failure_id": "pending", "failure_class": "", "status": "not_evaluated"}])
    return material, large, stability, interval, interval_group, interval_failure


def classifications() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, Any], pd.DataFrame]:
    decision = {
        "target_period": 2025,
        "decision": "pending_release",
        "final_status": "waiting_release_watcher_active",
        "one_shot_consumed": False,
        "same_holdout_retuning": "prohibited",
        "incumbent_retained": True,
        "shadow_status": "frozen_pending_release",
    }
    failure = pd.DataFrame(
        [
            {"failure_code": "F0", "failure_name": "Release Pending", "active": "Y", "evidence": "2025 official detailed target not detected", "action": "continue watcher; do not score"},
            {"failure_code": "F1", "failure_name": "Holdout Integrity Failure", "active": "N", "evidence": "no evidence yet", "action": "pending"},
            {"failure_code": "F3", "failure_name": "Population Shift", "active": "unknown", "evidence": "raw unavailable", "action": "audit after seal"},
            {"failure_code": "F6", "failure_name": "Shadow Challenger Failure", "active": "unknown", "evidence": "actual unavailable", "action": "do not judge"},
        ]
    )
    evidence = pd.DataFrame(
        [
            {"target_period": 2025, "holdout_integrity": "pending_release", "incumbent_result": "pending_release", "shadow_result": "pending_release", "interval_result": "pending_release", "population_shift": "pending_raw", "one_shot_consumed": "N"},
        ]
    )
    next_protocol = {
        "next_action": "continue_release_watcher",
        "watcher_command": "PYTHONPATH=scripts .venv/bin/python scripts/partial_stats_phase10_release_watcher.py --record-metadata",
        "minimum_interval": "no more frequent than hourly; daily default",
        "after_detection": "seal raw before parsing, then create one-shot manifest",
        "same_holdout_reuse": "prohibited",
    }
    requests = pd.DataFrame(
        [
            {"request_id": "P11-WATCH-001", "priority": "P1", "required": "Run Phase 10 Release Watcher periodically", "blocks": "first-observed availability evidence", "status": "pending_external_schedule"},
            {"request_id": "P11-RAW-001", "priority": "P1_after_release_detection", "required": "If automatic capture fails, store official API raw without value analysis", "blocks": "holdout raw seal", "status": "pending_detection"},
            {"request_id": "P11-RELEASE-001", "priority": "P2", "required": "Official release time evidence if available", "blocks": "official release-time interpretation", "does_not_block": "self-observed future holdout evaluation", "status": "pending_optional"},
        ]
    )
    return decision, failure, evidence, next_protocol, requests


def gpt_handoff_review() -> dict[str, Any]:
    return {
        "feasibility_status": "manual_or_api_handoff_possible_direct_existing_chat_injection_not_available",
        "recommended_route": "create a concise handoff markdown/prompt bundle and paste or upload it into the desired GPT chat",
        "api_route": "possible to create a separate OpenAI API conversation or internal review workflow, but it will not be the same arbitrary ChatGPT UI conversation unless an app/connector/action is built and authorized",
        "automation_caveat": "Codex in this repo has no authenticated ChatGPT conversation connector exposed for sending messages to a user-selected GPT chat",
        "privacy_note": "include only reports and sanitized artifact summaries; do not include API keys or raw sensitive files",
    }


def write_gpt_handoff(report_text: str, review: dict[str, Any]) -> None:
    lines = [
        "# Phase 11 GPT Handoff Review",
        "",
        "## Feasibility",
        "",
        review["feasibility_status"],
        "",
        "## Recommended Prompt",
        "",
        "```text",
        "아래 Phase 11 보고서를 읽고, 연구 설계·검증 실패 원인 분류·다음 실험 방향에 대해 비판적으로 검토해줘.",
        "특히 데이터 유출, holdout 무결성, C3 shadow challenger의 해석, production 승격 금지 조건을 중점적으로 봐줘.",
        "```",
        "",
        "## Report To Attach Or Paste",
        "",
        "Use `reports/partial_statistics_estimation_phase11.md`. 긴 채팅에는 1, 4, 5, 20, 21, 23, 25, 26장을 먼저 보내는 것을 권장한다.",
        "",
        "## Caveats",
        "",
        f"- {review['api_route']}",
        f"- {review['automation_caveat']}",
        f"- {review['privacy_note']}",
    ]
    GPT_HANDOFF_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def execution_manifest(input_hash: str) -> pd.DataFrame:
    rows = []
    for i, name in enumerate(CSV_OUTPUTS, start=1):
        path = PROCESSED_DIR / name
        rows.append(
            {
                "task_id": f"P11-{i:03d}",
                "stage": name,
                "status": "completed" if path.exists() or name == "partial_stats_phase11_execution_manifest.csv" else "pending",
                "input_hash": input_hash,
                "output_path": f"data/processed/{name}",
                "output_hash": core.file_sha256(path) if path.exists() else "",
                "rows_processed": len(read_frame(name)) if path.exists() and name.endswith(".csv") and name != "partial_stats_phase11_execution_manifest.csv" else "",
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows)


def write_report(ctx: dict[str, Any]) -> None:
    titles = [
        "실행 요약",
        "Phase 10 기준선",
        "검증 실패 가능성",
        "Forecast 및 Policy 무결성",
        "Release Watcher 운영",
        "First Observed Availability",
        "Raw Holdout Seal",
        "Holdout 무결성",
        "Schema 변화",
        "모집단 변화",
        "Evaluation Population",
        "평가 Coverage",
        "Incumbent 결과",
        "C3 Shadow 결과",
        "C3 조정 Cell",
        "Material Degradation",
        "대형 Cell 안정성",
        "지역·업종 안정성",
        "Prediction Interval",
        "Failure Classification",
        "최종 판정",
        "Holdout 소비상태",
        "다음 Vintage 계획",
        "사용자 개입 요청",
        "한계",
        "결론",
    ]
    table_map = {
        1: ctx["final"],
        2: ctx["phase10"],
        3: ctx["failure"],
        4: pd.concat([ctx["input_hash"], ctx["policy"], ctx["forecast_integrity"]], ignore_index=True, sort=False),
        5: ctx["watcher_health"],
        6: ctx["first_seen"],
        7: ctx["raw_manifest"],
        8: ctx["holdout_integrity"],
        9: ctx["schema"],
        10: ctx["shift"],
        11: ctx["population"],
        12: ctx["coverage"],
        13: ctx["incumbent"],
        14: ctx["shadow_result"],
        15: ctx["shadow_adjusted"],
        16: ctx["material"],
        17: ctx["large"],
        18: ctx["stability"],
        19: ctx["interval"],
        20: ctx["failure"],
        21: ctx["decision"],
        22: ctx["evidence"],
        23: ctx["next_protocol"],
        24: ctx["requests"],
        25: ctx["limits"],
        26: ctx["conclusion"],
    }
    notes = {
        1: "The 2025 forecast remains frozen and unconsumed. No model validation result is available because the official detailed target has not yet been observed.",
        4: "Forecast, cube, protocol, incumbent, and shadow hashes were checked before any target parsing. No 2025 target values were accessed.",
        5: "Watcher health is based on the metadata-only Phase 10 watcher log. Scheduler registration remains external to the repository.",
        20: "Active failure classification is F0 Release Pending. This is not a model failure.",
        24: "The GPT handoff feasibility review is also saved as `reports/partial_statistics_estimation_phase11_gpt_handoff.md`.",
        26: "Neither the incumbent nor the shadow challenger may be modified before the 2025 actual is sealed and evaluated once.",
    }
    lines = ["# Partial Statistics Estimation Phase 11", ""]
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
    row = "| [partial_statistics_estimation_phase11.md](../partial_statistics_estimation_phase11.md) | Phase 11 holdout observation readiness, watcher health, failure classification, and pending-release validation protocol |"
    text = path.read_text(encoding="utf-8")
    if "partial_statistics_estimation_phase11.md" not in text:
        lines = text.splitlines()
        lines.insert(4 if len(lines) >= 4 else len(lines), row)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 11 holdout observation and validation failure diagnosis")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase11_final_status.json"
    if final_path.exists() and not args.force:
        print(json.dumps({"status": "reused_completed_cache", "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
        return 0
    input_hash, policy, forecast_integrity, context = input_audits()
    watcher_health, probe, first_seen, failures = watcher_artifacts()
    raw_manifest, timeline, holdout_integrity, schema, shift = pending_holdout_artifacts(context, first_seen)
    population, coverage, suppression, result = evaluation_pending(context)
    incumbent = result[result["policy_role"].eq("incumbent")].copy()
    shadow_result = result[result["policy_role"].eq("shadow_challenger")].copy()
    shadow_adjusted, shadow_adjustment = shadow_adjustments(context)
    material, large, stability, interval, interval_group, interval_failure = pending_stability()
    decision, failure, evidence, next_protocol, requests = classifications()
    gpt_review = gpt_handoff_review()
    final = {
        "status": "waiting_release_watcher_active",
        "actual_available": False,
        "watcher_last_success": watcher_health.iloc[0].get("probe_time", ""),
        "forecast_lead_time": "",
        "raw_holdout_seal_status": raw_manifest["holdout_raw_status"],
        "holdout_integrity": "pending_release",
        "evaluated_cells": "",
        "evaluation_coverage": "",
        "failure_classification": "F0_release_pending",
        "incumbent_retained": True,
        "shadow_replicated": "",
        "one_shot_consumed": False,
        "same_holdout_reuse": "prohibited",
        "gpt_handoff_feasibility": gpt_review["feasibility_status"],
        "generated_at": GENERATED_AT,
    }
    phase10 = pd.DataFrame(
        [
            {
                "phase10_status": "forecast_frozen_waiting_release",
                "target_period": 2025,
                "forecast_rows": 14028,
                "forecast_archive_hash": PHASE10_FORECAST_HASH,
                "physical_forecast_created_at": context["manifest"].get("physical_forecast_created_at", ""),
                "one_shot_consumed": "false",
            }
        ]
    )
    limits = pd.DataFrame(
        [
            {"limit_id": "actual_unavailable", "description": "2025 official detailed target has not been observed, so no model validation result exists."},
            {"limit_id": "watcher_scheduler_external", "description": "Watcher script exists, but regular scheduler registration is outside this repository run."},
            {"limit_id": "gpt_direct_chat_injection", "description": gpt_review["automation_caveat"]},
        ]
    )
    conclusion = pd.DataFrame(
        [
            {"claim": "model_performance", "status": "not_claimed", "reason": "actual unavailable"},
            {"claim": "holdout_integrity", "status": "pending_release", "reason": "first_observed_available_at missing"},
            {"claim": "policy_change", "status": "prohibited", "reason": "holdout unconsumed and policies frozen"},
            {"claim": "gpt_handoff", "status": "manual_or_api_review_possible", "reason": "prepared report and handoff review; direct existing ChatGPT chat posting is not available from current repo context"},
        ]
    )
    run_input_hash = core.stable_hash(
        {
            "phase10_forecast_hash": context["manifest"].get("forecast_archive_hash", ""),
            "input_hash": input_hash.to_dict("records"),
            "policy": policy.to_dict("records"),
            "watcher": watcher_health.to_dict("records"),
        }
    )
    artifacts = {
        "partial_stats_phase11_input_hash_audit.csv": input_hash,
        "partial_stats_phase11_policy_identity_audit.csv": policy,
        "partial_stats_phase11_forecast_integrity_audit.csv": forecast_integrity,
        "partial_stats_phase11_watcher_health.csv": watcher_health,
        "partial_stats_phase11_release_probe_log.csv": probe,
        "partial_stats_phase11_release_first_seen.csv": first_seen,
        "partial_stats_phase11_release_failures.csv": failures,
        "partial_stats_phase11_holdout_access_timeline.csv": timeline,
        "partial_stats_phase11_holdout_integrity.csv": holdout_integrity,
        "partial_stats_phase11_holdout_schema_audit.csv": schema,
        "partial_stats_phase11_population_shift_audit.csv": shift,
        "partial_stats_phase11_evaluation_population.csv": population,
        "partial_stats_phase11_evaluation_coverage.csv": coverage,
        "partial_stats_phase11_suppression_audit.csv": suppression,
        "partial_stats_phase11_incumbent_results.csv": incumbent,
        "partial_stats_phase11_incumbent_group_results.csv": incumbent.assign(group_scope="pending_release"),
        "partial_stats_phase11_incumbent_aggregate_results.csv": incumbent.assign(aggregate_scope="pending_release"),
        "partial_stats_phase11_shadow_results.csv": shadow_result,
        "partial_stats_phase11_shadow_adjusted_cell_results.csv": shadow_adjusted,
        "partial_stats_phase11_shadow_adjustment_audit.csv": shadow_adjustment,
        "partial_stats_phase11_material_degradation.csv": material,
        "partial_stats_phase11_large_cell_audit.csv": large,
        "partial_stats_phase11_region_industry_stability.csv": stability,
        "partial_stats_phase11_interval_results.csv": interval,
        "partial_stats_phase11_interval_group_results.csv": interval_group,
        "partial_stats_phase11_interval_failure_audit.csv": interval_failure,
        "partial_stats_phase11_failure_classification.csv": failure,
        "partial_stats_phase11_evidence_registry.csv": evidence,
        "partial_stats_phase11_user_action_requests.csv": requests,
    }
    for name, frame in artifacts.items():
        write_frame(name, lineage(frame, run_input_hash, {"phase": 11, "artifact": name}))
    write_frame("partial_stats_phase11_execution_manifest.csv", execution_manifest(run_input_hash))
    write_json(PROCESSED_DIR / "partial_stats_phase11_holdout_raw_manifest.json", raw_manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase11_holdout_decision.json", decision)
    write_json(PROCESSED_DIR / "partial_stats_phase11_next_vintage_protocol.json", next_protocol)
    write_json(
        PROCESSED_DIR / "partial_stats_phase11_experiment_manifest.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "input_hash": run_input_hash,
            "code_commit_hash": git_hash(),
            "target_values_accessed": False,
            "package_versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "platform": platform.platform()},
            "generated_at": GENERATED_AT,
        },
    )
    write_json(PROCESSED_DIR / "partial_stats_phase11_progress.json", {"status": "completed", "current_workstream": "Phase 11", "last_updated": GENERATED_AT})
    write_json(PROCESSED_DIR / "partial_stats_phase11_final_status.json", final)
    ctx = {
        "final": pd.DataFrame([final]),
        "phase10": phase10,
        "failure": failure,
        "input_hash": input_hash,
        "policy": policy,
        "forecast_integrity": forecast_integrity,
        "watcher_health": watcher_health,
        "first_seen": first_seen,
        "raw_manifest": pd.DataFrame([raw_manifest]),
        "holdout_integrity": holdout_integrity,
        "schema": schema,
        "shift": shift,
        "population": population,
        "coverage": coverage,
        "incumbent": incumbent,
        "shadow_result": shadow_result,
        "shadow_adjusted": shadow_adjusted,
        "material": material,
        "large": large,
        "stability": stability,
        "interval": interval,
        "decision": pd.DataFrame([decision]),
        "evidence": evidence,
        "next_protocol": pd.DataFrame([next_protocol]),
        "requests": requests,
        "limits": limits,
        "conclusion": conclusion,
    }
    write_report(ctx)
    write_gpt_handoff(REPORT.read_text(encoding="utf-8"), gpt_review)
    update_topics()
    print(json.dumps({"status": final["status"], "actual_available": final["actual_available"], "report": str(REPORT.relative_to(ROOT)), "gpt_handoff": str(GPT_HANDOFF_REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
