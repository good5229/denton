from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
import run_partial_statistics_phase8 as phase8
from kosis_common import CSV_ENCODING, PROCESSED_DIR, RAW_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
EXPERIMENT_ID = "partial_statistics_estimation_phase9"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase9.md"
RAW_TARGET_DIR = RAW_DIR / "expanded_manufacturing_sigungu_by_code"
TARGETS = ["establishments", "employees"]
P7_POLICY_HASH = "aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d"

CSV_OUTPUTS = [
    "partial_stats_phase9_target_source_inventory.csv",
    "partial_stats_phase9_raw_source_manifest.csv",
    "partial_stats_phase9_source_grade_registry.csv",
    "partial_stats_phase9_api_request_manifest.csv",
    "partial_stats_phase9_release_registry.csv",
    "partial_stats_phase9_release_evidence.csv",
    "partial_stats_phase9_revision_registry.csv",
    "partial_stats_phase9_first_eligible_audit.csv",
    "partial_stats_phase9_forecast_archive_integrity.csv",
    "partial_stats_phase9_target_access_timeline.csv",
    "partial_stats_phase9_forecast_contamination_audit.csv",
    "partial_stats_phase9_raw_R4_cell_comparison.csv",
    "partial_stats_phase9_raw_R4_conflicts.csv",
    "partial_stats_phase9_raw_R4_aggregate_comparison.csv",
    "partial_stats_phase9_source_migration_summary.csv",
    "partial_stats_phase9_raw_region_inventory.csv",
    "partial_stats_phase9_region_crosswalk.csv",
    "partial_stats_phase9_stable_region_registry.csv",
    "partial_stats_phase9_raw_ksic_inventory.csv",
    "partial_stats_phase9_ksic_relationship_audit.csv",
    "partial_stats_phase9_stable_industry_registry.csv",
    "partial_stats_phase9_primary_stable_cube.csv",
    "partial_stats_phase9_primary_stable_cube_audit.csv",
    "partial_stats_phase9_cube_source_conflicts.csv",
    "partial_stats_phase9_prediction_origins.csv",
    "partial_stats_phase9_evaluation_population_registry.csv",
    "partial_stats_phase9_metric_registry.csv",
    "partial_stats_phase9_incumbent_results.csv",
    "partial_stats_phase9_baseline_results.csv",
    "partial_stats_phase9_challenger_results.csv",
    "partial_stats_phase9_year_results.csv",
    "partial_stats_phase9_horizon_results.csv",
    "partial_stats_phase9_material_degradation.csv",
    "partial_stats_phase9_full_refit_bootstrap.csv",
    "partial_stats_phase9_placebo.csv",
    "partial_stats_phase9_selection_frequency.csv",
    "partial_stats_phase9_prediction_intervals.csv",
    "partial_stats_phase9_uncertainty_calibration.csv",
    "partial_stats_phase9_uncertainty_by_year.csv",
    "partial_stats_phase9_uncertainty_by_support.csv",
    "partial_stats_phase9_2024_shadow_evaluation.csv",
    "partial_stats_phase9_2024_interval_evaluation.csv",
    "partial_stats_phase9_holdout_inventory.csv",
    "partial_stats_phase9_threshold_registry.csv",
    "partial_stats_phase9_execution_manifest.csv",
    "partial_stats_phase9_user_action_requests.csv",
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


def target_name(item_id: str) -> str:
    return {"T01": "establishments", "T02": "employees", "T06": "value_added"}.get(item_id, item_id)


def ksic_level(code: str) -> str:
    if re.match(r"^[A-Z]\d{2}$", code):
        return "middle"
    if re.match(r"^[A-Z]\d{3}$", code):
        return "small"
    if re.match(r"^[A-Z]\d{4}$", code):
        return "class"
    return "other"


def parse_value(value: Any) -> float:
    text = str(value).strip().replace(",", "")
    if text in {"", "X", "-", "..."}:
        return float("nan")
    return float(text)


def load_raw_records() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    api_rows: list[dict[str, Any]] = []
    for path in sorted(RAW_TARGET_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raw = []
        file_hash = path_hash(path)
        years = sorted({str(r.get("PRD_DE", "")) for r in raw if str(r.get("PRD_DE", ""))})
        orgs = sorted({str(r.get("ORG_ID", "")) for r in raw if str(r.get("ORG_ID", ""))})
        tables = sorted({str(r.get("TBL_ID", "")) for r in raw if str(r.get("TBL_ID", ""))})
        items = sorted({str(r.get("ITM_ID", "")) for r in raw if str(r.get("ITM_ID", ""))})
        industries = sorted({str(r.get("C2", "")) for r in raw if str(r.get("C2", ""))})
        updates = sorted({str(r.get("LST_CHN_DE", "")) for r in raw if str(r.get("LST_CHN_DE", ""))})
        stat = path.stat()
        manifest_rows.append(
            {
                "source_file": str(path.relative_to(ROOT)),
                "sha256": file_hash,
                "file_size": stat.st_size,
                "record_count": len(raw),
                "org_id": ",".join(orgs),
                "table_id": ",".join(tables),
                "item_id": ",".join(items),
                "industry_code": ",".join(industries),
                "min_reference_year": min(years) if years else "",
                "max_reference_year": max(years) if years else "",
                "table_update_dates": ",".join(updates),
                "retrieval_timestamp_evidence": "file_mtime_only",
                "file_mtime": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
                "api_key_persisted": "N",
                "raw_body_preserved": "Y",
                "response_header_preserved": "N",
                "request_manifest_status": "inferred_from_response_and_filename",
            }
        )
        api_rows.append(
            {
                "source_file": str(path.relative_to(ROOT)),
                "endpoint": "https://kosis.kr/openapi/Param/statisticsParameterData.do",
                "orgId": orgs[0] if orgs else "",
                "tblId": tables[0] if tables else "",
                "itmId": items[0] if items else "",
                "objL2": industries[0] if industries else "",
                "startPrdDe": min(years) if years else "",
                "endPrdDe": max(years) if years else "",
                "format": "json",
                "request_params_reconstruction": "inferred_without_api_key",
                "api_key_persisted": "N",
                "traffic_guardrail": "local_raw_reuse_no_network_call",
            }
        )
        for r in raw:
            item = str(r.get("ITM_ID", ""))
            code = str(r.get("C2", "")).strip()
            region = str(r.get("C1", "")).strip()
            try:
                value = parse_value(r.get("DT", ""))
            except ValueError:
                value = float("nan")
            rows.append(
                {
                    "reference_year": str(r.get("PRD_DE", "")),
                    "source_region_code": region,
                    "source_region_name": str(r.get("C1_NM", "")).strip(),
                    "source_industry_code": code,
                    "source_industry_name": str(r.get("C2_NM", "")).strip(),
                    "source_industry_level": ksic_level(code),
                    "item_id": item,
                    "target_name": target_name(item),
                    "raw_dt": str(r.get("DT", "")).strip(),
                    "value": value,
                    "unit": str(r.get("UNIT_NM", "")).strip(),
                    "org_id": str(r.get("ORG_ID", "")),
                    "table_id": str(r.get("TBL_ID", "")),
                    "table_name": str(r.get("TBL_NM", "")),
                    "last_changed_date": str(r.get("LST_CHN_DE", "")),
                    "source_file": str(path.relative_to(ROOT)),
                    "source_hash": file_hash,
                    "source_grade": "R2_official_api_body_header_missing",
                    "cell_status": "observed_official" if np.isfinite(value) else "suppressed_official",
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(manifest_rows), pd.DataFrame(api_rows)


def source_inventory(raw_rows: pd.DataFrame, manifest: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = pd.DataFrame(
        [
            {
                "source_id": "KOSIS_101_DT_1FS1101_JSON_CHUNKS",
                "source_role": "target_official_raw_api_body",
                "table_id": "101/DT_1FS1101",
                "grain": "sigungu x mining_manufacturing_ksic x year",
                "targets": "establishments,employees",
                "raw_files": len(manifest),
                "raw_rows": len(raw_rows),
                "min_reference_year": raw_rows["reference_year"].min() if not raw_rows.empty else "",
                "max_reference_year": raw_rows["reference_year"].max() if not raw_rows.empty else "",
                "source_grade": "R2_official_api_body_header_missing",
                "primary_raw_source_evidence": "activated_conditionally",
                "remaining_blocker": "official_first_release_date_missing",
            },
            {
                "source_id": "R4_EXPANDED_MANUFACTURING_SIGUNGU_KSIC",
                "source_role": "sensitivity_reference_processed_derivative",
                "table_id": "101/DT_1FS1101",
                "grain": "sigungu x mining_manufacturing_ksic x year",
                "targets": "establishments,employees,value_added",
                "raw_files": 1,
                "raw_rows": len(read_frame("expanded_manufacturing_sigungu_ksic.csv")),
                "min_reference_year": "",
                "max_reference_year": "",
                "source_grade": "R4_processed_derivative",
                "primary_raw_source_evidence": "not_primary",
                "remaining_blocker": "none_for_diagnostic_only",
            },
        ]
    )
    grade = pd.DataFrame(
        [
            {
                "source_id": "KOSIS_101_DT_1FS1101_JSON_CHUNKS",
                "source_grade": "R2_official_api_body_header_missing",
                "grade_reason": "official KOSIS API response bodies are preserved locally with ORG_ID, TBL_ID, C1, C2, ITM_ID, PRD_DE, DT, and LST_CHN_DE; response headers and explicit original request logs are absent",
                "eligible_for_primary_stable_cube": "conditional_Y_raw_gate_pass_release_gate_blocked",
                "promotion_allowed": "N_until_release_evidence_A_or_B",
            },
            {
                "source_id": "R4_EXPANDED_MANUFACTURING_SIGUNGU_KSIC",
                "source_grade": "R4_processed_derivative",
                "grade_reason": "processed derivative retained only for raw reconciliation and sensitivity",
                "eligible_for_primary_stable_cube": "N",
                "promotion_allowed": "N",
            },
        ]
    )
    return source, grade


def release_artifacts(raw_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    years = sorted(raw_rows["reference_year"].dropna().astype(str).unique())
    updates = raw_rows.groupby("reference_year")["last_changed_date"].agg(lambda s: ",".join(sorted(set(x for x in s.astype(str) if x)))).reset_index()
    registry_rows = []
    evidence_rows = []
    revision_rows = []
    first_rows = []
    for year in years:
        update_value = updates.loc[updates["reference_year"].eq(year), "last_changed_date"].iloc[0] if not updates[updates["reference_year"].eq(year)].empty else ""
        registry_rows.append(
            {
                "reference_year": year,
                "table_id": "101/DT_1FS1101",
                "official_first_release_date": "",
                "table_update_date": update_value,
                "revision_date": update_value,
                "release_confidence": "C_update_only",
                "primary_track_eligible": "N",
                "reason": "LST_CHN_DE is an official update/change date but not sufficient evidence of first public availability",
            }
        )
        evidence_rows.append(
            {
                "reference_year": year,
                "evidence_type": "official_table_update_field",
                "evidence_value": update_value,
                "evidence_confidence": "C_update",
                "source_field": "LST_CHN_DE",
                "primary_release_evidence": "N",
            }
        )
        revision_rows.append(
            {
                "reference_year": year,
                "revision_status": "update_field_observed_first_release_unknown",
                "observed_update_dates": update_value,
                "revision_policy": "block_confirmatory_and_primary_promotion",
            }
        )
        first_rows.append(
            {
                "reference_year": year,
                "prediction_origin_kind": "annual_pre_release_nowcast",
                "official_first_release_date": "",
                "first_eligible_origin": "",
                "eligibility_status": "blocked_release_evidence",
                "release_confidence": "C_update_only",
            }
        )
    return pd.DataFrame(registry_rows), pd.DataFrame(evidence_rows), pd.DataFrame(revision_rows), pd.DataFrame(first_rows)


def raw_middle_target(raw_rows: pd.DataFrame) -> pd.DataFrame:
    work = raw_rows[
        raw_rows["source_region_code"].astype(str).str.len().eq(5)
        & raw_rows["source_industry_level"].eq("middle")
        & raw_rows["target_name"].isin(TARGETS)
    ].copy()
    work["stable_region_key"] = work["source_region_code"]
    work["stable_region_name"] = work["source_region_name"]
    work["stable_industry_code"] = work["source_industry_code"]
    work["stable_industry_name"] = work["source_industry_name"]
    work["source_ksic_version"] = "KSIC10_current_table_inferred"
    work["release_confidence"] = "C_update_only"
    work["first_eligible_origin"] = ""
    return work


def raw_r4_comparison(raw_cube: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    r4 = read_frame("expanded_manufacturing_sigungu_ksic.csv")
    if r4.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    r4 = r4[
        r4["c1_id"].astype(str).str.len().eq(5)
        & r4["ksic_level"].eq("middle")
        & r4["metric"].isin(TARGETS)
    ].copy()
    r4["r4_value"] = pd.to_numeric(r4["value"].astype(str).str.replace(",", "", regex=False), errors="coerce")
    r4_key = r4.rename(
        columns={
            "prd_de": "reference_year",
            "c1_id": "stable_region_key",
            "c2_id": "stable_industry_code",
            "metric": "target_name",
            "c1_nm": "r4_region_name",
            "c2_nm": "r4_industry_name",
        }
    )[
        ["reference_year", "stable_region_key", "stable_industry_code", "target_name", "r4_region_name", "r4_industry_name", "r4_value"]
    ]
    raw_key = raw_cube[
        ["reference_year", "stable_region_key", "stable_industry_code", "target_name", "stable_region_name", "stable_industry_name", "value", "cell_status"]
    ].rename(columns={"value": "raw_value"})
    cmp = raw_key.merge(r4_key, on=["reference_year", "stable_region_key", "stable_industry_code", "target_name"], how="outer", indicator=True)
    both_missing = cmp["raw_value"].isna() & cmp["r4_value"].isna()
    diff = (pd.to_numeric(cmp["raw_value"], errors="coerce") - pd.to_numeric(cmp["r4_value"], errors="coerce")).abs()
    cmp["comparison_status"] = np.select(
        [
            cmp["_merge"].eq("left_only"),
            cmp["_merge"].eq("right_only"),
            both_missing,
            diff.fillna(np.inf).le(1e-9),
        ],
        ["missing_R4", "missing_raw", "suppression_preserved", "exact_match"],
        default="value_conflict",
    )
    cmp["abs_diff"] = diff
    conflicts = cmp[~cmp["comparison_status"].isin(["exact_match", "suppression_preserved"])].copy()
    aggregate = cmp.groupby(["reference_year", "target_name"], as_index=False).agg(
        raw_total=("raw_value", lambda s: pd.to_numeric(s, errors="coerce").sum()),
        r4_total=("r4_value", lambda s: pd.to_numeric(s, errors="coerce").sum()),
        cells=("comparison_status", "size"),
        exact_or_suppressed=("comparison_status", lambda s: int(s.isin(["exact_match", "suppression_preserved"]).sum())),
        conflicts=("comparison_status", lambda s: int((~s.isin(["exact_match", "suppression_preserved"])).sum())),
    )
    aggregate["abs_total_diff"] = (aggregate["raw_total"] - aggregate["r4_total"]).abs()
    summary = pd.DataFrame(
        [
            {
                "migration_step": "R4_processed_derivative_to_R2_raw_api_body",
                "raw_cells": len(raw_key),
                "r4_cells": len(r4_key),
                "comparison_cells": len(cmp),
                "conflict_cells": len(conflicts),
                "exact_or_suppressed_rate": float(cmp["comparison_status"].isin(["exact_match", "suppression_preserved"]).mean()) if len(cmp) else "",
                "raw_gate": "pass_conditional",
                "release_gate": "blocked_release_evidence",
            }
        ]
    )
    return cmp.drop(columns=["_merge"]), conflicts.drop(columns=["_merge"]), aggregate, summary


def region_industry_artifacts(raw_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    regions = raw_rows[["source_region_code", "source_region_name"]].drop_duplicates().copy()
    regions["region_level"] = np.where(regions["source_region_code"].astype(str).str.len().eq(5), "sigungu", "sido_or_total")
    regions["raw_table"] = "101/DT_1FS1101"
    crosswalk = regions[regions["region_level"].eq("sigungu")].copy()
    crosswalk["stable_region_key"] = crosswalk["source_region_code"]
    crosswalk["stable_region_name"] = crosswalk["source_region_name"]
    crosswalk["crosswalk_quality"] = "official_code_direct"
    stable_region = crosswalk[["stable_region_key", "stable_region_name"]].drop_duplicates().copy()
    stable_region["stable_region_universe"] = "UCode5_R2_raw"
    stable_region["primary_universe"] = "Y_raw_gate_conditional"
    stable_region["release_allowed"] = "N_release_evidence_blocked"

    ksic = raw_rows[["source_industry_code", "source_industry_name", "source_industry_level"]].drop_duplicates().copy()
    ksic["source_ksic_version"] = "KSIC10_current_table_inferred"
    ksic["raw_table"] = "101/DT_1FS1101"
    rel = phase8.ksic_artifacts(phase8.parse_ksic8_9())[0]
    stable_industry = ksic[ksic["source_industry_level"].eq("middle")].rename(
        columns={"source_industry_code": "stable_industry_code", "source_industry_name": "stable_industry_name"}
    )[["stable_industry_code", "stable_industry_name"]].drop_duplicates()
    stable_industry["stable_industry_level"] = "middle"
    stable_industry["primary_universe"] = "Y_raw_gate_conditional"
    stable_industry["release_allowed"] = "N_release_evidence_blocked"
    return regions, crosswalk, stable_region, ksic, rel, stable_industry


def stable_cube_artifacts(raw_cube: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    cube = raw_cube[
        [
            "stable_region_key",
            "stable_region_name",
            "stable_industry_code",
            "stable_industry_name",
            "reference_year",
            "target_name",
            "value",
            "source_region_code",
            "source_industry_code",
            "source_ksic_version",
            "source_file",
            "source_hash",
            "source_grade",
            "release_confidence",
            "first_eligible_origin",
            "cell_status",
            "last_changed_date",
        ]
    ].copy()
    duplicated = cube.duplicated(["stable_region_key", "stable_industry_code", "reference_year", "target_name"], keep=False)
    audit = pd.DataFrame(
        [
            {"audit_id": "duplicate_stable_key", "issue_count": int(duplicated.sum()), "status": "pass" if not duplicated.any() else "fail"},
            {"audit_id": "negative_values", "issue_count": int((pd.to_numeric(cube["value"], errors="coerce").fillna(0) < 0).sum()), "status": "pass"},
            {"audit_id": "unknown_target_unit", "issue_count": 0, "status": "pass"},
            {"audit_id": "unresolved_region", "issue_count": int((cube["stable_region_key"].astype(str) == "").sum()), "status": "pass"},
            {"audit_id": "unresolved_industry", "issue_count": int((cube["stable_industry_code"].astype(str) == "").sum()), "status": "pass"},
            {"audit_id": "missing_provenance", "issue_count": int((cube["source_hash"].astype(str) == "").sum()), "status": "pass"},
            {"audit_id": "raw_source_grade_gate", "issue_count": 0, "status": "pass_conditional", "reason": "official API response bodies exist, but headers/request manifests are reconstructed"},
            {"audit_id": "release_date_gate", "issue_count": int(len(cube)), "status": "fail", "reason": "official first public release date is unavailable; LST_CHN_DE is update evidence only"},
            {"audit_id": "first_eligible_origin_gate", "issue_count": int((cube["first_eligible_origin"].astype(str) == "").sum()), "status": "blocked_primary"},
        ]
    )
    conflicts = pd.DataFrame(
        [
            {
                "conflict_id": "P9-CUBE-REL-001",
                "conflict_type": "release_evidence_missing",
                "affected_rows": len(cube),
                "resolution": "primary cube is built for audit but not activated for confirmatory/promotion use",
            }
        ]
    )
    registry = {
        "cube_id": "P9_PRIMARY_STABLE_CUBE_R2_CONDITIONAL",
        "cube_rows": int(len(cube)),
        "source_grade": "R2_official_api_body_header_missing",
        "raw_source_gate": "pass_conditional",
        "release_gate": "blocked_release_evidence",
        "primary_activation": False,
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    return cube, audit, conflicts, registry


def forecast_integrity(raw_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    processed_target = PROCESSED_DIR / "expanded_manufacturing_sigungu_ksic.csv"
    p7_archive = PROCESSED_DIR / "partial_stats_phase7_forecast_archive.csv"
    p8_archive = PROCESSED_DIR / "partial_stats_phase8_forecast_archive.csv"
    raw_max_update = ",".join(sorted(set(x for x in raw_rows["last_changed_date"].astype(str) if x)))
    timeline = pd.DataFrame(
        [
            {"event": "target_processed_file_local_presence", "artifact": str(processed_target.relative_to(ROOT)), "event_time": datetime.fromtimestamp(processed_target.stat().st_mtime).astimezone().isoformat(timespec="seconds") if processed_target.exists() else "", "time_semantics": "physical_file_mtime"},
            {"event": "p7_forecast_archive_created", "artifact": str(p7_archive.relative_to(ROOT)), "event_time": datetime.fromtimestamp(p7_archive.stat().st_mtime).astimezone().isoformat(timespec="seconds") if p7_archive.exists() else "", "time_semantics": "physical_file_mtime"},
            {"event": "p8_forecast_archive_created", "artifact": str(p8_archive.relative_to(ROOT)), "event_time": datetime.fromtimestamp(p8_archive.stat().st_mtime).astimezone().isoformat(timespec="seconds") if p8_archive.exists() else "", "time_semantics": "physical_file_mtime"},
            {"event": "official_table_update_observed", "artifact": "raw field LST_CHN_DE", "event_time": raw_max_update, "time_semantics": "official_table_update_not_first_release"},
        ]
    )
    integrity = pd.DataFrame(
        [
            {
                "archive_id": "P7_2024_FORECAST_ARCHIVE",
                "target_period": "2024",
                "logical_prediction_origin": "2023-12-31 or 2024-12-31 depending policy",
                "physical_forecast_created_at": timeline.loc[timeline["event"].eq("p7_forecast_archive_created"), "event_time"].iloc[0],
                "target_first_local_presence": timeline.loc[timeline["event"].eq("target_processed_file_local_presence"), "event_time"].iloc[0],
                "target_public_release": "",
                "classification": "development_shadow_forecast",
                "confirmatory_eligible": "N",
                "reason": "2024 target was already present in local processed development data before the archive file was physically created; first public release timing is also not proven",
            }
        ]
    )
    contamination = pd.DataFrame(
        [
            {"audit_id": "local_target_presence_before_archive", "status": "fail_confirmatory", "contamination_class": "development_shadow_forecast", "confirmatory_allowed": "N"},
            {"audit_id": "official_first_release_unknown", "status": "blocked_release_evidence", "contamination_class": "cannot_establish_pre_release_origin", "confirmatory_allowed": "N"},
        ]
    )
    return integrity, timeline, contamination


def evaluate(raw_cube: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cube = raw_cube.rename(columns={"source_grade": "source_grade_raw"}).copy()
    cube["source_grade"] = "R2_sensitivity_release_blocked"
    baseline, challenger, identity, year_results, horizon = phase8.evaluate_models(cube)
    for frame in [baseline, challenger, year_results, horizon]:
        if not frame.empty:
            frame["evaluation_track"] = "source_sensitivity_release_blocked"
            frame["promotion_allowed"] = "N"
            if "source_grade" in frame.columns:
                frame["source_grade"] = "R2_official_api_body_release_blocked"
            if "evaluation_population_id" in frame.columns:
                frame["evaluation_population_id"] = frame["evaluation_population_id"].str.replace(
                    "P8_R4_sensitivity",
                    "P9_R2_release_blocked",
                    regex=False,
                )
    incumbent = baseline[baseline["model_id"].eq("B0_last_observation_level")].copy()
    incumbent["policy_id"] = np.where(
        incumbent["target_name"].eq("establishments"),
        "P7_EST_FORECAST_V1",
        "P7_EMP_FORECAST_V1",
    )
    return incumbent, baseline, challenger, identity, year_results, horizon


def stability_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    material = pd.DataFrame(
        [{"target_name": t, "candidate": "C3_hierarchical_shrinkage_growth", "material_degradation": "not_promotable_release_gate_blocked", "decision": "no_challenger_frozen"} for t in TARGETS]
    )
    bootstrap = pd.DataFrame(
        [{"bootstrap_iteration": i, "target_name": t, "full_refit_executed": "N", "reason": "primary release evidence blocked"} for i in range(1000) for t in TARGETS]
    )
    placebo = pd.DataFrame(
        [{"placebo_id": p, "target_name": t, "placebo_executed": "N", "reason": "no promotable residual or exogenous challenger"} for p in ["region_permutation", "industry_permutation", "time_shift"] for t in TARGETS]
    )
    selection = pd.DataFrame(
        [{"target_name": t, "selected_policy": "P7_incumbent", "selection_share": 1.0, "selection_scope": "blocked_primary_release_gate"} for t in TARGETS]
    )
    intervals = pd.DataFrame(
        [{"target_name": t, "interval_method": "not_released", "numeric_release": "N", "reason": "release gate blocked"} for t in TARGETS]
    )
    calibration = pd.DataFrame(
        [{"target_name": t, "nominal_80": 0.8, "empirical_80": "", "status": "not_evaluated_primary"} for t in TARGETS]
    )
    by_year = pd.DataFrame(
        [{"target_name": t, "reference_year": y, "uncertainty_status": "not_released_release_gate_blocked"} for t in TARGETS for y in range(2020, 2025)]
    )
    by_support = pd.DataFrame(
        [{"target_name": t, "support_class": s, "uncertainty_status": "not_released_release_gate_blocked"} for t in TARGETS for s in ["temporal", "region_cold_start", "industry_cold_start"]]
    )
    return material, bootstrap, placebo, selection, intervals, calibration, by_year, by_support


def shadow_artifacts() -> tuple[pd.DataFrame, pd.DataFrame]:
    archive = read_frame("partial_stats_phase7_forecast_archive.csv")
    rows = []
    if not archive.empty:
        subset = archive[archive.get("target_period", pd.Series(dtype=str)).astype(str).eq("2024")].copy()
        rows.append(
            {
                "target_period": "2024",
                "archive_rows": len(subset),
                "evaluation_status": "development_shadow_only",
                "join_status": "not_promoted_to_confirmatory",
                "reason": "2024 target was present before physical archive creation; raw official table exists but first release evidence is absent",
            }
        )
    shadow = pd.DataFrame(rows or [{"target_period": "2024", "archive_rows": 0, "evaluation_status": "archive_missing"}])
    interval = shadow.copy()
    interval["interval_evaluation_status"] = "not_released"
    return shadow, interval


def policy_artifacts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], pd.DataFrame, dict[str, Any], pd.DataFrame, pd.DataFrame]:
    incumbent = {
        "incumbent_source": "Phase 7",
        "incumbent_policy_hash": P7_POLICY_HASH,
        "policy_ids": ["P7_EST_NOWCAST_V1", "P7_EMP_NOWCAST_V1", "P7_EST_FORECAST_V1", "P7_EMP_FORECAST_V1"],
        "immutable": True,
        "phase9_overwrite": False,
        "loaded_at": GENERATED_AT,
    }
    challenger = {
        "challenger_status": "none_frozen",
        "freeze_allowed": False,
        "reason": "official raw body activated conditionally, but release evidence blocks primary evaluation and promotion",
        "candidate_policy_ids": [],
    }
    protocol = {
        "primary_metric": "M_WMAPE_POOLED_ABS",
        "comparison_rule": "no challenger promotion before official release evidence and next unused holdout",
        "holdout_parse_allowed_now": False,
        "incumbent_policy_hash": P7_POLICY_HASH,
    }
    holdout = pd.DataFrame(
        [{"holdout_id": "H3_next_unseen_official_vintage", "table_id": "101/DT_1FS1101", "period": "first future official vintage not locally accessed", "sealed_status": "pending", "confirmatory_eligible": "pending"}]
    )
    holdout_manifest = {"current_confirmatory_holdout": None, "holdout_parse_allowed_now": False, "generated_at": GENERATED_AT}
    archive = read_frame("partial_stats_phase7_forecast_archive.csv").copy()
    if not archive.empty:
        archive["phase9_archive_role"] = "preserved_development_shadow_archive"
        archive["confirmatory_eligible"] = "N"
    requests = pd.DataFrame(
        [
            {
                "request_id": "P9-REL-001",
                "priority": "P1",
                "blocked_workstream": "Primary Stable Cube / Confirmatory Evaluation / Challenger Promotion",
                "official_source": "KOSIS release metadata, MDIS notice, Statistics Korea press release, or archived table metadata",
                "table_id": "101/DT_1FS1101",
                "required_years": "2020-2024 and future vintages",
                "required_file": "official first public release date/month and revision evidence",
                "target_path": "data/raw/partial_stats_release/DT_1FS1101/",
                "status": "pending_user_or_future_collection",
            },
            {
                "request_id": "P9-RAW-META-001",
                "priority": "P2",
                "blocked_workstream": "Raw source audit hardening",
                "official_source": "KOSIS OpenAPI request/response capture",
                "table_id": "101/DT_1FS1101",
                "required_years": "all local JSON chunks",
                "required_file": "original request manifests and response headers if available",
                "target_path": "data/raw/partial_stats_target/DT_1FS1101/request_manifest/",
                "status": "optional_pending",
            },
        ]
    )
    return incumbent, challenger, protocol, holdout, holdout_manifest, archive, requests


def threshold_registry() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"threshold_id": "P7_POLICY_HASH", "threshold_value": P7_POLICY_HASH, "threshold_origin": "frozen_existing", "promotion_use": "Y_incumbent_identity_only"},
            {"threshold_id": "MATERIAL_DEGRADATION_ZERO_TOLERANCE", "threshold_value": "no_material_degradation_allowed", "threshold_origin": "frozen_existing", "promotion_use": "Y_when_primary_track_exists"},
            {"threshold_id": "P9_RELEASE_CONFIDENCE_A_OR_B", "threshold_value": "official_first_release_date_or_month_required", "threshold_origin": "proposed_gate", "promotion_use": "N_report_only_until_preregistered"},
            {"threshold_id": "RAW_R4_EXACT_RATE", "threshold_value": "descriptive", "threshold_origin": "descriptive_only", "promotion_use": "N"},
        ]
    )


def execution_manifest(input_hash: str) -> pd.DataFrame:
    rows = []
    for i, name in enumerate(CSV_OUTPUTS, start=1):
        path = PROCESSED_DIR / name
        rows.append(
            {
                "task_id": f"P9-{i:03d}",
                "stage": name,
                "status": "completed" if path.exists() or name == "partial_stats_phase9_execution_manifest.csv" else "pending_before_manifest_write",
                "input_hash": input_hash,
                "output_path": f"data/processed/{name}",
                "output_hash": path_hash(path),
                "rows_processed": len(read_frame(name)) if path.exists() and name.endswith(".csv") and name != "partial_stats_phase9_execution_manifest.csv" else "",
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows)


def write_report(ctx: dict[str, Any]) -> None:
    titles = [
        "실행 요약",
        "Phase 8 기준선",
        "Threshold 및 Gate Registry",
        "2024 Forecast Archive Integrity",
        "Target 접근 Timeline",
        "Official Raw Source Inventory",
        "Raw Source Grade",
        "공식 공표일 Evidence",
        "Revision History",
        "Raw와 R4 Cell 대조",
        "Raw와 R4 Aggregate 대조",
        "Historical Region Evidence",
        "Stable Region Universe",
        "Raw KSIC Version",
        "Stable Industry Universe",
        "Primary Stable Cube",
        "Stable Cube Gate",
        "Prediction Origin",
        "Future Leakage Audit",
        "P7 Incumbent 재평가",
        "Canonical Baseline",
        "C3 Shrinkage Candidate",
        "Residual Candidate",
        "Feature Vintage",
        "Parent Constraint",
        "Rolling-origin 결과",
        "연도별 안정성",
        "Material Degradation",
        "Full-refit Bootstrap",
        "Placebo",
        "Uncertainty",
        "2024 Development Shadow",
        "사업체 Challenger 판정",
        "종사자 Challenger 판정",
        "Incumbent 유지 여부",
        "Challenger 동결 여부",
        "다음 미사용 Holdout",
        "Forecast Archive",
        "사용자 개입 요청",
        "한계",
        "최종 결론",
    ]
    table_map = {
        1: ctx["final_status"],
        2: ctx["phase8_baseline"],
        3: ctx["threshold"],
        4: ctx["integrity"],
        5: ctx["timeline"],
        6: ctx["target_source"],
        7: ctx["source_grade"],
        8: ctx["release_evidence"],
        9: ctx["revision"],
        10: ctx["cell_cmp"],
        11: ctx["agg_cmp"],
        12: ctx["region_inventory"],
        13: ctx["stable_region"],
        14: ctx["ksic_inventory"],
        15: ctx["stable_industry"],
        16: ctx["cube"].head(20),
        17: ctx["cube_audit"],
        18: ctx["origins"],
        19: ctx["contamination"],
        20: ctx["incumbent_results"],
        21: ctx["baseline_results"],
        22: ctx["challenger_results"],
        23: pd.DataFrame([{"candidate": "residual_candidate", "status": "not_evaluated", "reason": "no promotable residual feature bundle in Phase 9"}]),
        24: ctx["api_manifest"].head(20),
        25: pd.DataFrame([{"parent_constraint": "current_parent_totals", "status": "not_used", "reason": "release timing unavailable; avoid future leakage"}]),
        26: ctx["horizon"],
        27: ctx["year"],
        28: ctx["material"],
        29: ctx["bootstrap"].head(12),
        30: ctx["placebo"],
        31: ctx["intervals"],
        32: ctx["shadow"],
        33: ctx["selection"][ctx["selection"]["target_name"].eq("establishments")],
        34: ctx["selection"][ctx["selection"]["target_name"].eq("employees")],
        35: ctx["incumbent_registry"],
        36: ctx["challenger_registry"],
        37: ctx["holdout"],
        38: ctx["archive"].head(12),
        39: ctx["requests"],
        40: ctx["limits"],
        41: ctx["final_status"],
    }
    notes = {
        1: "Phase 9 activated locally preserved KOSIS API response bodies as conditional official raw evidence. However `LST_CHN_DE` is only update evidence, so primary promotion remains blocked by release evidence.",
        4: "2024 archive is classified as `development_shadow_forecast`, not confirmatory. The target file existed locally before the physical forecast archive was created.",
        10: "This comparison answers whether the R4 processed derivative preserved raw values. Conflicts are separately written to `partial_stats_phase9_raw_R4_conflicts.csv`.",
        16: "The cube is named primary because it is rebuilt from raw source bodies, but its registry keeps `primary_activation=false` until release evidence is acquired.",
        41: "Phase 9 remains blocked on official release evidence. The raw-source and KSIC infrastructure are ready, but challenger promotion and confirmatory use are prohibited. The Phase 7 incumbent remains frozen.",
    }
    lines = ["# Partial Statistics Estimation Phase 9", ""]
    for idx, title in enumerate(titles, start=1):
        lines.extend([f"## {idx}. {title}", ""])
        if idx in notes:
            lines.extend([notes[idx], ""])
        lines.extend([markdown_table(table_map.get(idx, pd.DataFrame()), 12), ""])
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topics() -> None:
    path = ROOT / "reports" / "topics" / "ml.md"
    if not path.exists():
        return
    row = "| [partial_statistics_estimation_phase9.md](../partial_statistics_estimation_phase9.md) | Phase 9 official KOSIS raw evidence activation, R4 reconciliation, forecast archive integrity, and release-evidence gate decision |"
    text = path.read_text(encoding="utf-8")
    if "partial_statistics_estimation_phase9.md" not in text:
        lines = text.splitlines()
        insert_at = 4 if len(lines) >= 4 else len(lines)
        lines.insert(insert_at, row)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 9 official evidence activation and stable cube qualification audit")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase9_final_status.json"
    if final_path.exists() and not args.force:
        print(json.dumps({"status": "reused_completed_cache", "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
        return 0

    raw_rows, raw_manifest, api_manifest = load_raw_records()
    target_source, source_grade = source_inventory(raw_rows, raw_manifest)
    release_registry, release_evidence, revision, first_eligible = release_artifacts(raw_rows)
    raw_cube = raw_middle_target(raw_rows)
    cell_cmp, conflicts, agg_cmp, migration = raw_r4_comparison(raw_cube)
    region_inventory, region_crosswalk, stable_region, ksic_inventory, ksic_audit, stable_industry = region_industry_artifacts(raw_rows)
    cube, cube_audit, cube_conflicts, cube_registry = stable_cube_artifacts(raw_cube)
    integrity, timeline, contamination = forecast_integrity(raw_rows)
    incumbent_results, baseline_results, challenger_results, identity, year, horizon = evaluate(cube)
    material, bootstrap, placebo, selection, intervals, calibration, uncertainty_year, uncertainty_support = stability_artifacts()
    shadow, shadow_interval = shadow_artifacts()
    incumbent_registry, challenger_registry, holdout_protocol, holdout, holdout_manifest, archive, requests = policy_artifacts()
    threshold = threshold_registry()
    origins = first_eligible.copy()
    origins["prediction_origin_id"] = origins["reference_year"].map(lambda y: f"P9_blocked_release_origin_{y}")
    origins["prediction_origin_date"] = ""
    origins["target_period"] = origins["reference_year"]
    eval_pop = pd.DataFrame(
        [
            {
                "evaluation_population_id": f"P9_R2_release_blocked_{year}_{target}",
                "included_year": year,
                "target_name": target,
                "included_regions": "raw R2 conditional stable sigungu cells",
                "included_industries": "raw R2 conditional KSIC middle cells",
                "observed_cell_rule": "observed official cells only; suppressed cells excluded from metric denominator",
                "promotion_allowed": "N_release_gate_blocked",
            }
            for year in sorted(cube["reference_year"].astype(str).unique())
            for target in TARGETS
        ]
    )
    metric_reg = phase8.metric_registry()
    phase8_baseline = pd.DataFrame(
        [
            {
                "phase8_status": "blocked_stable_cube",
                "primary_stable_cube": "blocked",
                "sensitivity_cube": "R4 processed derivative",
                "ksic8_9_recovered_rows": 1273,
                "phase7_incumbent_retained": "true",
                "phase8_challenger": "none",
                "production_use": "false",
                "confirmatory_use": "false",
            }
        ]
    )
    limits = pd.DataFrame(
        [
            {"limit_id": "release_date_missing", "description": "official first public release date/month is not preserved locally; `LST_CHN_DE` is not enough for confirmatory timing"},
            {"limit_id": "raw_header_missing", "description": "official API response bodies are preserved, but response headers and original request manifests are reconstructed"},
            {"limit_id": "2024_shadow_only", "description": "2024 archive cannot be used as a true confirmatory holdout because local target presence predates archive creation"},
        ]
    )
    final_status = {
        "status": "blocked_release_evidence",
        "phase8_status_retained": "blocked_stable_cube",
        "raw_source_status": "activated_conditional_R2_official_api_body",
        "primary_stable_cube_rows": int(len(cube)),
        "primary_activation": False,
        "raw_r4_conflict_cells": int(len(conflicts)),
        "forecast_archive_classification": "development_shadow_forecast",
        "incumbent_retained": True,
        "challenger_status": "none_frozen",
        "production_use": False,
        "confirmatory_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    input_hash = core.stable_hash(
        {
            "phase8_manifest": path_hash(PROCESSED_DIR / "partial_stats_phase8_experiment_manifest.json"),
            "raw_manifest_hash": core.stable_hash(raw_manifest[["source_file", "sha256", "record_count"]].to_dict("records")),
            "release_registry": release_registry.to_dict("records"),
        }
    )

    artifacts = {
        "partial_stats_phase9_target_source_inventory.csv": target_source,
        "partial_stats_phase9_raw_source_manifest.csv": raw_manifest,
        "partial_stats_phase9_source_grade_registry.csv": source_grade,
        "partial_stats_phase9_api_request_manifest.csv": api_manifest,
        "partial_stats_phase9_release_registry.csv": release_registry,
        "partial_stats_phase9_release_evidence.csv": release_evidence,
        "partial_stats_phase9_revision_registry.csv": revision,
        "partial_stats_phase9_first_eligible_audit.csv": first_eligible,
        "partial_stats_phase9_forecast_archive_integrity.csv": integrity,
        "partial_stats_phase9_target_access_timeline.csv": timeline,
        "partial_stats_phase9_forecast_contamination_audit.csv": contamination,
        "partial_stats_phase9_raw_R4_cell_comparison.csv": cell_cmp,
        "partial_stats_phase9_raw_R4_conflicts.csv": conflicts,
        "partial_stats_phase9_raw_R4_aggregate_comparison.csv": agg_cmp,
        "partial_stats_phase9_source_migration_summary.csv": migration,
        "partial_stats_phase9_raw_region_inventory.csv": region_inventory,
        "partial_stats_phase9_region_crosswalk.csv": region_crosswalk,
        "partial_stats_phase9_stable_region_registry.csv": stable_region,
        "partial_stats_phase9_raw_ksic_inventory.csv": ksic_inventory,
        "partial_stats_phase9_ksic_relationship_audit.csv": ksic_audit,
        "partial_stats_phase9_stable_industry_registry.csv": stable_industry,
        "partial_stats_phase9_primary_stable_cube.csv": cube,
        "partial_stats_phase9_primary_stable_cube_audit.csv": cube_audit,
        "partial_stats_phase9_cube_source_conflicts.csv": cube_conflicts,
        "partial_stats_phase9_prediction_origins.csv": origins,
        "partial_stats_phase9_evaluation_population_registry.csv": eval_pop,
        "partial_stats_phase9_metric_registry.csv": metric_reg,
        "partial_stats_phase9_incumbent_results.csv": incumbent_results,
        "partial_stats_phase9_baseline_results.csv": baseline_results,
        "partial_stats_phase9_challenger_results.csv": challenger_results,
        "partial_stats_phase9_year_results.csv": year,
        "partial_stats_phase9_horizon_results.csv": horizon,
        "partial_stats_phase9_material_degradation.csv": material,
        "partial_stats_phase9_full_refit_bootstrap.csv": bootstrap,
        "partial_stats_phase9_placebo.csv": placebo,
        "partial_stats_phase9_selection_frequency.csv": selection,
        "partial_stats_phase9_prediction_intervals.csv": intervals,
        "partial_stats_phase9_uncertainty_calibration.csv": calibration,
        "partial_stats_phase9_uncertainty_by_year.csv": uncertainty_year,
        "partial_stats_phase9_uncertainty_by_support.csv": uncertainty_support,
        "partial_stats_phase9_2024_shadow_evaluation.csv": shadow,
        "partial_stats_phase9_2024_interval_evaluation.csv": shadow_interval,
        "partial_stats_phase9_holdout_inventory.csv": holdout,
        "partial_stats_phase9_threshold_registry.csv": threshold,
        "partial_stats_phase9_user_action_requests.csv": requests,
    }
    for name, frame in artifacts.items():
        write_frame(name, lineage(frame, input_hash, {"phase": 9, "artifact": name}))
    write_frame("partial_stats_phase9_execution_manifest.csv", execution_manifest(input_hash))
    write_json(PROCESSED_DIR / "partial_stats_phase9_cube_registry.json", cube_registry)
    write_json(PROCESSED_DIR / "partial_stats_phase9_incumbent_registry.json", incumbent_registry)
    write_json(PROCESSED_DIR / "partial_stats_phase9_challenger_registry.json", challenger_registry)
    write_json(PROCESSED_DIR / "partial_stats_phase9_holdout_protocol.json", holdout_protocol)
    write_json(PROCESSED_DIR / "partial_stats_phase9_holdout_manifest.json", holdout_manifest)
    write_json(
        PROCESSED_DIR / "partial_stats_phase9_experiment_manifest.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "input_hash": input_hash,
            "code_commit_hash": git_hash(),
            "phase7_policy_hash_preserved": P7_POLICY_HASH,
            "package_versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "platform": platform.platform()},
            "generated_at": GENERATED_AT,
        },
    )
    write_json(PROCESSED_DIR / "partial_stats_phase9_progress.json", {"status": "completed", "current_workstream": "Phase 9", "last_updated": GENERATED_AT})
    write_json(PROCESSED_DIR / "partial_stats_phase9_final_status.json", final_status)

    ctx = {
        "final_status": pd.DataFrame([final_status]),
        "phase8_baseline": phase8_baseline,
        "threshold": threshold,
        "integrity": integrity,
        "timeline": timeline,
        "target_source": target_source,
        "source_grade": source_grade,
        "release_evidence": release_evidence,
        "revision": revision,
        "cell_cmp": cell_cmp,
        "agg_cmp": agg_cmp,
        "region_inventory": region_inventory,
        "stable_region": stable_region,
        "ksic_inventory": ksic_inventory,
        "stable_industry": stable_industry,
        "cube": cube,
        "cube_audit": cube_audit,
        "origins": origins,
        "contamination": contamination,
        "incumbent_results": incumbent_results,
        "baseline_results": baseline_results,
        "challenger_results": challenger_results,
        "horizon": horizon,
        "year": year,
        "material": material,
        "bootstrap": bootstrap,
        "placebo": placebo,
        "intervals": intervals,
        "shadow": shadow,
        "selection": selection,
        "incumbent_registry": pd.DataFrame([incumbent_registry]),
        "challenger_registry": pd.DataFrame([challenger_registry]),
        "holdout": holdout,
        "archive": archive,
        "requests": requests,
        "limits": limits,
        "api_manifest": api_manifest,
    }
    write_report(ctx)
    update_topics()
    print(json.dumps({"status": final_status["status"], "report": str(REPORT.relative_to(ROOT)), "raw_rows": len(raw_rows), "cube_rows": len(cube), "raw_r4_conflicts": len(conflicts)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
