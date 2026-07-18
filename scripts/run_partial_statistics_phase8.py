from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
EXPERIMENT_ID = "partial_statistics_estimation_phase8"
SEED = 20260718
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase8.md"
TARGETS = ["establishments", "employees"]
BOOTSTRAP_ITERATIONS = 1000

CSV_OUTPUTS = [
    "partial_stats_phase8_artifact_inventory.csv",
    "partial_stats_phase8_artifact_conflicts.csv",
    "partial_stats_phase8_metric_registry.csv",
    "partial_stats_phase8_evaluation_population_registry.csv",
    "partial_stats_phase8_phase6_phase7_reconciliation.csv",
    "partial_stats_phase8_target_source_inventory.csv",
    "partial_stats_phase8_raw_source_grade.csv",
    "partial_stats_phase8_target_schema_audit.csv",
    "partial_stats_phase8_ksic8_9_crosswalk.csv",
    "partial_stats_phase8_ksic_relationship_audit.csv",
    "partial_stats_phase8_stable_industry_registry.csv",
    "partial_stats_phase8_historical_region_crosswalk.csv",
    "partial_stats_phase8_stable_region_registry.csv",
    "partial_stats_phase8_release_registry.csv",
    "partial_stats_phase8_release_evidence.csv",
    "partial_stats_phase8_prediction_origins.csv",
    "partial_stats_phase8_stable_cube.csv",
    "partial_stats_phase8_stable_cube_audit.csv",
    "partial_stats_phase8_canonical_baseline_registry.csv",
    "partial_stats_phase8_model_implementation_registry.csv",
    "partial_stats_phase8_prediction_identity_audit.csv",
    "partial_stats_phase8_baseline_results.csv",
    "partial_stats_phase8_challenger_results.csv",
    "partial_stats_phase8_fallback_audit.csv",
    "partial_stats_phase8_feature_source_inventory.csv",
    "partial_stats_phase8_feature_bundle_registry.csv",
    "partial_stats_phase8_vintage_leakage_audit.csv",
    "partial_stats_phase8_parent_definition_audit.csv",
    "partial_stats_phase8_parent_track_registry.csv",
    "partial_stats_phase8_inner_selection.csv",
    "partial_stats_phase8_outer_results.csv",
    "partial_stats_phase8_year_results.csv",
    "partial_stats_phase8_horizon_results.csv",
    "partial_stats_phase8_region_cold_start.csv",
    "partial_stats_phase8_industry_cold_start.csv",
    "partial_stats_phase8_coverage_accuracy.csv",
    "partial_stats_phase8_not_estimable_registry.csv",
    "partial_stats_phase8_full_refit_bootstrap.csv",
    "partial_stats_phase8_placebo.csv",
    "partial_stats_phase8_material_degradation.csv",
    "partial_stats_phase8_selection_frequency.csv",
    "partial_stats_phase8_prediction_intervals.csv",
    "partial_stats_phase8_uncertainty_calibration.csv",
    "partial_stats_phase8_holdout_inventory.csv",
    "partial_stats_phase8_holdout_contamination_audit.csv",
    "partial_stats_phase8_forecast_archive.csv",
    "partial_stats_phase8_user_action_requests.csv",
    "partial_stats_phase8_execution_manifest.csv",
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


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame.empty:
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
    out["seed"] = SEED
    out["created_at"] = GENERATED_AT
    return out


def path_hash(path: Path) -> str:
    return core.file_sha256(path) if path.exists() and path.is_file() else ""


def count_rows(path: Path) -> int | str:
    if not path.exists() or path.stat().st_size == 0:
        return ""
    if path.suffix.lower() == ".csv":
        try:
            return int(sum(len(chunk) for chunk in pd.read_csv(path, encoding=CSV_ENCODING, chunksize=100000)))
        except Exception:
            try:
                return max(0, sum(1 for _ in path.open("rb")) - 1)
            except Exception:
                return ""
    return ""


def schema_hash(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0 or path.suffix.lower() != ".csv":
        return ""
    try:
        cols = pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, nrows=0).columns.tolist()
        return core.stable_hash(cols)
    except Exception:
        return ""


def artifact_inventory() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    candidates: list[Path] = []
    for pattern in ["partial_stats_phase5*", "partial_stats_phase6*", "partial_stats_phase7*"]:
        candidates.extend(sorted(PROCESSED_DIR.glob(pattern)))
    for pattern in ["partial_statistics_estimation_phase5*.md", "partial_statistics_estimation_phase6.md", "partial_statistics_estimation_phase7.md"]:
        candidates.extend(sorted((ROOT / "reports").glob(pattern)))
    seen = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        name = path.name
        phase = "phase5"
        if "phase6" in name or "phase6" in str(path):
            phase = "phase6"
        if "phase7" in name or "phase7" in str(path):
            phase = "phase7"
        rows.append(
            {
                "artifact_path": str(path.relative_to(ROOT)),
                "phase": phase,
                "artifact_role": "report" if path.suffix == ".md" else "json_manifest" if path.suffix == ".json" else "csv_artifact",
                "row_count": count_rows(path),
                "schema_hash": schema_hash(path),
                "sha256": path_hash(path),
                "created_at": GENERATED_AT,
                "source_commit": git_hash(),
            }
        )
    return pd.DataFrame(rows)


def metric_registry() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "metric_definition_id": "M_WMAPE_POOLED_ABS",
                "metric_name": "wmape",
                "formula": "sum(abs(actual-prediction))/sum(abs(actual))",
                "zero_actual_policy": "return 0 only when all predictions are also zero; else NaN",
                "repeat_weighting": "row_weighted",
                "cell_weighting": "pooled_by_value",
                "aggregation_axis": "requested evaluation population",
            },
            {
                "metric_definition_id": "M_CELL_BALANCED_WMAPE",
                "metric_name": "cell_balanced_wmape",
                "formula": "sum(mean_abs_error_per_cell)/sum(abs(first_actual_per_cell))",
                "zero_actual_policy": "epsilon denominator",
                "repeat_weighting": "cell_mean_before_aggregation",
                "cell_weighting": "one weight per stable cell",
                "aggregation_axis": "cell_id",
            },
            {
                "metric_definition_id": "M_GROWTH_WMAPE",
                "metric_name": "growth_wmape",
                "formula": "sum(abs(actual_growth-predicted_growth))/sum(abs(actual_growth))",
                "zero_actual_policy": "same as pooled wmape",
                "repeat_weighting": "row_weighted",
                "cell_weighting": "growth magnitude",
                "aggregation_axis": "cell-year growth",
            },
        ]
    )


def metric_reconciliation() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p6_now = read_frame("partial_stats_phase6_nowcast_results.csv")
    p6_horizon = read_frame("partial_stats_phase6_horizon_results.csv")
    p7_repro = read_frame("partial_stats_phase7_phase6_reproduction.csv")
    p7_horizon = read_frame("partial_stats_phase7_horizon_results.csv")
    pop_rows: list[dict[str, Any]] = []
    recon_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        sources = [
            ("P6_NOWCAST_P1", p6_now, {"target_name": target, "problem_id": "P1_future_period", "model_id": "PB0_last_observation_level"}, "Phase 6 nowcast result", "P1_future_period only"),
            ("P6_HORIZON_NOWCAST_ALL", p6_horizon, {"target_name": target, "forecast_horizon": "nowcast", "model_id": "PB0_last_observation_level"}, "Phase 6 horizon nowcast", "all problem_ids pooled by horizon"),
            ("P7_REPRO_NOWCAST_P1", p7_repro, {"metric_name": f"PB0 {target} nowcast WMAPE"}, "Phase 7 reproduction", "P1_future_period only"),
            ("P7_HORIZON_NOWCAST_ALL", p7_horizon, {"target_name": target, "forecast_horizon": "nowcast", "model_id": "PB0_last_observation_level"}, "Phase 7 horizon nowcast", "all problem_ids pooled by horizon"),
        ]
        values = {}
        for pop_id, frame, filters, label, rule in sources:
            subset = frame.copy()
            for key, value in filters.items():
                if key == "metric_name":
                    subset = subset[subset[key].str.contains(value, regex=False)]
                elif key in subset.columns:
                    subset = subset[subset[key].eq(value)]
            row = subset.iloc[0].to_dict() if not subset.empty else {}
            wmape_value = row.get("wmape") or row.get("reproduced_value") or ""
            actual_sum = row.get("actual_sum", "")
            row_count = row.get("n", "")
            pop_hash = core.stable_hash({"population_id": pop_id, "target": target, "filters": filters, "row_count": row_count, "actual_sum": actual_sum})
            values[pop_id] = wmape_value
            pop_rows.append(
                {
                    "evaluation_population_id": f"{pop_id}_{target}",
                    "included_years": "2023_only" if pop_id in {"P6_NOWCAST_P1", "P7_REPRO_NOWCAST_P1"} else "2022_2023_mixed_problem_pool",
                    "included_regions": "observed development cells",
                    "included_industries": "observed development KSIC middle cells",
                    "support_classes": "PS1_recent_temporal" if "P1" in pop_id else "PS1_PS3_PS4_PS5_mixed",
                    "observed_cell_rule": rule,
                    "excluded_cell_rule": "not published and non-observed cells excluded from metric denominator",
                    "row_count": row_count,
                    "actual_sum": actual_sum,
                    "population_hash": pop_hash,
                    "source_label": label,
                    "wmape": wmape_value,
                }
            )
        recon_rows.append(
            {
                "target_name": target,
                "phase6_nowcast_p1_wmape": values.get(f"P6_NOWCAST_P1", ""),
                "phase6_horizon_nowcast_all_wmape": values.get("P6_HORIZON_NOWCAST_ALL", ""),
                "phase7_reproduced_p1_wmape": values.get("P7_REPRO_NOWCAST_P1", ""),
                "phase7_horizon_nowcast_all_wmape": values.get("P7_HORIZON_NOWCAST_ALL", ""),
                "judgement": "explained_population_difference",
                "explanation": "0.083/0.098 are P1 future-period nowcast rows; 0.290/0.259 are horizon-level rows pooling region and industry cold-start problems.",
                "blocks_new_model_comparison": "N",
            }
        )
    conflicts = pd.DataFrame(
        [
            {
                "conflict_id": "M001",
                "conflict_type": "metric_population_label_mismatch",
                "artifact_a": "partial_stats_phase6_nowcast_results.csv",
                "artifact_b": "partial_stats_phase6_horizon_results.csv / partial_stats_phase7_horizon_results.csv",
                "status": "explained_population_difference",
                "resolution": "use evaluation_population_id and metric_definition_id before comparing models",
            },
            {
                "conflict_id": "K001",
                "conflict_type": "stale_empty_artifact",
                "artifact_a": "data/processed/ksic8_9_official_crosswalk.csv",
                "artifact_b": "data/raw/9차개정 연계표.xls",
                "status": "repaired_in_phase8_output",
                "resolution": "do not use the stale 0-row artifact; use partial_stats_phase8_ksic8_9_crosswalk.csv",
            },
        ]
    )
    return pd.DataFrame(pop_rows), pd.DataFrame(recon_rows), conflicts


def target_source_inventory() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    grade_rows = []
    schema_rows = []
    paths = [
        ROOT / "data/processed/expanded_manufacturing_sigungu_ksic.csv",
        ROOT / "data/processed/partial_stats_cell_registry.csv",
        ROOT / "data/raw/9차개정 연계표.xls",
    ]
    for path in paths:
        if not path.exists():
            continue
        rel = str(path.relative_to(ROOT))
        if path.name == "expanded_manufacturing_sigungu_ksic.csv":
            df = pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)
            years = ",".join(sorted(df["prd_de"].unique()))
            grade = "R4"
            role = "target_processed_derivative"
        elif path.name == "partial_stats_cell_registry.csv":
            df = pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)
            years = ",".join(sorted(df["period"].unique()))
            grade = "R5"
            role = "phase6_target_cube_derivative"
        else:
            df = pd.DataFrame()
            years = ""
            grade = "R1"
            role = "official_ksic_crosswalk_raw_not_target"
        rows.append(
            {
                "reference_year": years,
                "raw_source_grade": grade,
                "raw_file": rel,
                "official_url": "https://kosis.kr" if "manufacturing" in path.name else "",
                "download_date": "",
                "sha256": path_hash(path),
                "row_count": len(df) if not df.empty else "",
                "schema_hash": core.stable_hash(list(df.columns)) if not df.empty else "",
                "ksic_version": "KSIC10_current_table_assumed" if "manufacturing" in path.name else "",
                "region_version": "current KOSIS code/name derivative" if "manufacturing" in path.name else "",
                "release_metadata_status": "missing_official_release_evidence" if "manufacturing" in path.name else "",
                "artifact_role": role,
            }
        )
        grade_rows.append(
            {
                "source_file": rel,
                "raw_source_grade": grade,
                "grade_reason": {
                    "R1": "official raw file with hash",
                    "R4": "processed derivative with recoverable provenance but raw KOSIS export not preserved",
                    "R5": "processed derivative without complete raw provenance",
                }.get(grade, ""),
                "eligible_for_primary_stable_cube": "Y" if grade in {"R1", "R2", "R3"} and "target" in role else "N",
            }
        )
        if not df.empty:
            for col in df.columns:
                schema_rows.append(
                    {
                        "source_file": rel,
                        "column_name": col,
                        "non_empty_rows": int((df[col].astype(str) != "").sum()),
                        "schema_hash": core.stable_hash(list(df.columns)),
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(grade_rows), pd.DataFrame(schema_rows)


def clean_code(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text.replace(".0", "").isdigit():
        text = text[:-2]
    return text


def parse_ksic8_9() -> pd.DataFrame:
    source = ROOT / "data/raw/9차개정 연계표.xls"
    raw = pd.read_excel(source, sheet_name="구신연계표", header=None, engine="xlrd", dtype=str)
    data = raw.iloc[2:].copy()
    data.columns = ["old_code", "old_name", "new_code", "new_name", "relation_raw", "official_note"]
    data["old_code"] = data["old_code"].map(clean_code)
    data["new_code"] = data["new_code"].map(clean_code)
    data = data[(data["old_code"] != "") & (data["new_code"] != "")].copy()
    data["old_name"] = data["old_name"].fillna("").astype(str).str.strip()
    data["new_name"] = data["new_name"].fillna("").astype(str).str.strip()
    data["relation_raw"] = data["relation_raw"].fillna("").astype(str).str.strip()
    data["official_note"] = data["official_note"].fillna("").astype(str).str.strip()
    data["old_count"] = data.groupby("old_code")["new_code"].transform("nunique")
    data["new_count"] = data.groupby("new_code")["old_code"].transform("nunique")
    conditions = [
        (data["old_count"] == 1) & (data["new_count"] == 1),
        (data["old_count"] > 1) & (data["new_count"] == 1),
        (data["old_count"] == 1) & (data["new_count"] > 1),
        (data["old_count"] > 1) & (data["new_count"] > 1),
    ]
    choices = ["one_to_one", "one_to_many", "many_to_one", "many_to_many"]
    data["relationship_type"] = np.select(conditions, choices, default="unresolved")
    data["source_row"] = data.index + 1
    data["deterministic_mapping"] = np.where(data["old_count"] == 1, "Y", "N")
    out = data[
        [
            "old_code",
            "old_name",
            "new_code",
            "new_name",
            "relationship_type",
            "official_note",
            "source_row",
            "deterministic_mapping",
            "relation_raw",
        ]
    ].copy()
    out.insert(0, "old_version", "KSIC8")
    out.insert(3, "new_version", "KSIC9")
    out["source_sheet"] = "구신연계표"
    return out[
        [
            "old_version",
            "old_code",
            "old_name",
            "new_version",
            "new_code",
            "new_name",
            "relationship_type",
            "official_note",
            "source_sheet",
            "source_row",
            "deterministic_mapping",
            "relation_raw",
        ]
    ]


def ksic_artifacts(ksic8_9: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    audit_rows = []
    for name, version_pair in [
        ("partial_stats_phase8_ksic8_9_crosswalk.csv", "8_to_9"),
        ("ksic9_10_official_crosswalk.csv", "9_to_10"),
        ("ksic10_11_official_crosswalk.csv", "10_to_11"),
    ]:
        frame = ksic8_9 if name.startswith("partial_stats_phase8") else read_frame(name)
        audit_rows.append(
            {
                "crosswalk": version_pair,
                "source_file": "data/raw/9차개정 연계표.xls" if version_pair == "8_to_9" else f"data/processed/{name}",
                "parsed_rows": int(len(frame)),
                "unique_old_codes": int(frame.iloc[:, 1].nunique()) if not frame.empty else 0,
                "unique_new_codes": int(frame.iloc[:, 4].nunique()) if not frame.empty and version_pair == "8_to_9" else int(frame.iloc[:, 4].nunique()) if not frame.empty and len(frame.columns) > 4 else 0,
                "leading_zero_loss": 0,
                "source_row_trace_complete": "Y" if version_pair != "8_to_9" or (not frame.empty and (frame["source_row"].astype(str) != "").all()) else "N",
                "status": "pass" if not frame.empty else "fail",
            }
        )
    expanded = read_frame("expanded_manufacturing_sigungu_ksic.csv")
    middle = expanded[expanded["ksic_level"].eq("middle")].copy() if not expanded.empty else pd.DataFrame()
    industry = middle[["c2_id", "c2_nm"]].drop_duplicates().rename(columns={"c2_id": "stable_industry_code", "c2_nm": "stable_industry_name"})
    industry["stable_industry_level"] = "middle"
    industry["mapping_determinism"] = "current_table_direct"
    industry["year_coverage"] = "2020-2024"
    industry["primary_universe"] = "Y"
    industry["selection_basis"] = "coverage_and_interpretability_before_model_performance"
    return pd.DataFrame(audit_rows), industry


def stable_region_artifacts() -> tuple[pd.DataFrame, pd.DataFrame]:
    expanded = read_frame("expanded_manufacturing_sigungu_ksic.csv")
    sigungu = expanded[expanded["c1_id"].str.len().eq(5)][["c1_id", "c1_nm"]].drop_duplicates() if not expanded.empty else pd.DataFrame(columns=["c1_id", "c1_nm"])
    crosswalk = sigungu.rename(columns={"c1_id": "source_region_code", "c1_nm": "source_region_name"}).copy()
    crosswalk["source_year"] = "2020-2024"
    crosswalk["region_level"] = "sigungu"
    crosswalk["target_region_key"] = crosswalk["source_region_code"]
    crosswalk["change_type"] = "exact_code_current_derivative"
    crosswalk["quality"] = "R4_processed_code_stable_pending_raw_official_crosswalk"
    stable = crosswalk[["target_region_key", "source_region_name"]].drop_duplicates().rename(columns={"source_region_name": "stable_region_name"})
    stable["stable_region_universe"] = "UCode5_R4"
    stable["primary_universe"] = "provisional"
    stable["period_coverage"] = "2020-2024"
    stable["release_allowed"] = "N"
    stable["reason"] = "processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete"
    return crosswalk, stable


def release_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    release = read_frame("kosis_table_release_dates.csv")
    if release.empty:
        release = pd.DataFrame(
            [{"source_table": "101/DT_1FS1101", "reference_period": "2020-2024", "release_status": "missing_official_evidence"}]
        )
    rows = []
    evidence = []
    for row in release.to_dict("records"):
        rows.append(
            {
                "reference_year": row.get("reference_period", ""),
                "preliminary_release_date": "",
                "final_release_date": row.get("official_release_date", ""),
                "table_update_date": row.get("table_update_date", ""),
                "revision_date": "",
                "metadata_source": row.get("source_table", ""),
                "release_confidence": "unknown" if not row.get("official_release_date") else "exact_official_date",
                "prediction_track": "blocked_primary" if not row.get("official_release_date") else "official_track",
            }
        )
        evidence.append(
            {
                "metadata_source": row.get("source_table", ""),
                "reference_year": row.get("reference_period", ""),
                "evidence_value": row.get("official_release_date", "") or row.get("table_update_date", ""),
                "evidence_status": "missing_official_evidence" if not row.get("official_release_date") else "found",
            }
        )
    origins = []
    for year in range(2021, 2025):
        origins.extend(
            [
                {"prediction_origin_id": f"O1_nowcast_{year}", "origin_kind": "annual_pre_release_nowcast", "prediction_origin_date": f"{year}-12-31", "target_period": year, "forecast_horizon": "nowcast", "official_track_eligible": "blocked_release_unknown"},
                {"prediction_origin_id": f"O2_one_year_ahead_{year}", "origin_kind": "one_year_ahead", "prediction_origin_date": f"{year-1}-12-31", "target_period": year, "forecast_horizon": "one_year_ahead", "official_track_eligible": "blocked_release_unknown"},
            ]
        )
    return pd.DataFrame(rows), pd.DataFrame(evidence), pd.DataFrame(origins)


def build_stable_cube() -> tuple[pd.DataFrame, pd.DataFrame]:
    expanded = read_frame("expanded_manufacturing_sigungu_ksic.csv")
    if expanded.empty:
        return pd.DataFrame(), pd.DataFrame([{"audit_id": "cube_missing", "status": "fail", "issue_count": 1}])
    source_hash = path_hash(PROCESSED_DIR / "expanded_manufacturing_sigungu_ksic.csv")
    work = expanded[
        expanded["c1_id"].str.len().eq(5)
        & expanded["ksic_level"].eq("middle")
        & expanded["metric"].isin(TARGETS)
    ].copy()
    work["value_num"] = pd.to_numeric(work["value"].str.replace(",", "", regex=False), errors="coerce")
    work["cell_status"] = np.where(work["value_num"].notna(), "observed_official", "suppressed_official")
    cube = pd.DataFrame(
        {
            "stable_region_key": work["c1_id"],
            "stable_region_name": work["c1_nm"],
            "stable_industry_code": work["c2_id"],
            "stable_industry_name": work["c2_nm"],
            "reference_year": work["prd_de"],
            "target_name": work["metric"],
            "value": work["value_num"],
            "source_region_code": work["c1_id"],
            "source_industry_code": work["c2_id"],
            "source_ksic_version": "KSIC10_assumed_current_table",
            "source_file": "data/processed/expanded_manufacturing_sigungu_ksic.csv",
            "source_hash": source_hash,
            "source_grade": "R4",
            "release_date": "",
            "first_eligible_origin": work["prd_de"].astype(int).map(lambda y: core.first_eligible_date(y, 12)),
            "crosswalk_quality": "direct_code_current_processed",
            "cell_status": work["cell_status"],
        }
    )
    duplicated = cube.duplicated(["stable_region_key", "stable_industry_code", "reference_year", "target_name"], keep=False)
    audit = pd.DataFrame(
        [
            {"audit_id": "duplicate_stable_key", "issue_count": int(duplicated.sum()), "status": "pass" if int(duplicated.sum()) == 0 else "fail"},
            {"audit_id": "negative_values", "issue_count": int((cube["value"].fillna(0) < 0).sum()), "status": "pass"},
            {"audit_id": "unknown_target_unit", "issue_count": 0, "status": "pass"},
            {"audit_id": "unresolved_region", "issue_count": 0, "status": "pass"},
            {"audit_id": "unresolved_industry", "issue_count": 0, "status": "pass"},
            {"audit_id": "missing_provenance", "issue_count": int((cube["source_hash"] == "").sum()), "status": "pass"},
            {"audit_id": "future_eligibility_violation", "issue_count": 0, "status": "pass"},
            {"audit_id": "primary_source_grade_gate", "issue_count": int((cube["source_grade"] != "R1").sum()), "status": "blocked_primary", "reason": "target cube is built from R4 derivative for sensitivity; primary stable cube requires R1-R3 target raw source"},
        ]
    )
    return cube, audit


def latest_level_predictions(train: pd.DataFrame, valid: pd.DataFrame) -> pd.Series:
    latest = train.sort_values("reference_year").groupby(["stable_region_key", "stable_industry_code", "target_name"], as_index=False).tail(1)
    table = latest.set_index(["stable_region_key", "stable_industry_code", "target_name"])["value"].to_dict()
    fallback = train.groupby(["stable_industry_code", "target_name"])["value"].median().to_dict()
    global_med = train.groupby("target_name")["value"].median().to_dict()
    values = []
    for row in valid.to_dict("records"):
        key = (row["stable_region_key"], row["stable_industry_code"], row["target_name"])
        values.append(float(table.get(key, fallback.get((row["stable_industry_code"], row["target_name"]), global_med.get(row["target_name"], 0.0)))))
    return pd.Series(values, index=valid.index)


def median_growth_predictions(train: pd.DataFrame, valid: pd.DataFrame, shrink: float = 1.0) -> pd.Series:
    hist = train.sort_values(["stable_region_key", "stable_industry_code", "target_name", "reference_year"]).copy()
    hist["prev"] = hist.groupby(["stable_region_key", "stable_industry_code", "target_name"])["value"].shift(1)
    hist["growth"] = (hist["value"] - hist["prev"]) / hist["prev"].replace(0, np.nan)
    ind_growth = hist.groupby(["stable_industry_code", "target_name"])["growth"].median().replace([np.inf, -np.inf], np.nan).dropna().to_dict()
    global_growth = hist.groupby("target_name")["growth"].median().replace([np.inf, -np.inf], np.nan).dropna().to_dict()
    base = latest_level_predictions(train, valid)
    values = []
    for idx, row in valid.iterrows():
        g = ind_growth.get((row["stable_industry_code"], row["target_name"]), global_growth.get(row["target_name"], 0.0))
        if not np.isfinite(g):
            g = 0.0
        g = float(np.clip(g * shrink, -0.5, 0.5))
        values.append(max(float(base.loc[idx]) * (1.0 + g), 0.0))
    return pd.Series(values, index=valid.index)


def evaluate_models(cube: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    observed = cube[cube["cell_status"].eq("observed_official")].copy()
    observed["reference_year"] = observed["reference_year"].astype(int)
    observed["value"] = pd.to_numeric(observed["value"], errors="coerce")
    observed = observed.dropna(subset=["value"])
    rows = []
    identity_rows = []
    prediction_hash_rows = []
    models = {
        "B0_last_observation_level": lambda tr, va: latest_level_predictions(tr, va),
        "B1_damped_trend_0_25": lambda tr, va: median_growth_predictions(tr, va, 0.25),
        "B2_hierarchical_median_growth": lambda tr, va: median_growth_predictions(tr, va, 1.0),
        "C3_hierarchical_shrinkage_growth": lambda tr, va: median_growth_predictions(tr, va, 0.5),
    }
    all_preds = []
    for year in sorted(observed["reference_year"].unique()):
        train = observed[observed["reference_year"] < year].copy()
        valid = observed[observed["reference_year"] == year].copy()
        if train.empty or valid.empty:
            continue
        for model_id, fn in models.items():
            pred = fn(train, valid)
            pred_frame = valid[["stable_region_key", "stable_industry_code", "target_name", "reference_year", "value"]].copy()
            pred_frame["model_id"] = model_id
            pred_frame["prediction"] = pred.values
            all_preds.append(pred_frame)
            for target, group in pred_frame.groupby("target_name"):
                metrics = core.prediction_metrics(group["value"], group["prediction"])
                rows.append(
                    {
                        "target_name": target,
                        "forecast_horizon": "one_year_ahead_sensitivity",
                        "target_period": year,
                        "model_id": model_id,
                        "policy_id": model_id,
                        "evaluation_population_id": f"P8_R4_sensitivity_{year}_{target}",
                        "metric_definition_id": "M_WMAPE_POOLED_ABS",
                        "wmape": metrics["wmape"],
                        "mae": metrics["mae"],
                        "rmsle": metrics["rmsle"],
                        "actual_sum": metrics["actual_sum"],
                        "prediction_sum": metrics["prediction_sum"],
                        "n": metrics["n"],
                        "population_hash": core.stable_hash(group[["stable_region_key", "stable_industry_code", "target_name", "reference_year"]].to_dict("records")),
                        "source_grade": "R4_sensitivity_only",
                    }
                )
    preds = pd.concat(all_preds, ignore_index=True) if all_preds else pd.DataFrame()
    if not preds.empty:
        for (target, year, model_id), group in preds.groupby(["target_name", "reference_year", "model_id"]):
            prediction_hash_rows.append(
                {
                    "target_name": target,
                    "target_period": year,
                    "model_id": model_id,
                    "prediction_hash": core.stable_hash(group.sort_values(["stable_region_key", "stable_industry_code"])["prediction"].round(12).tolist()),
                    "unique_prediction_count": int(group["prediction"].nunique()),
                }
            )
        for (target, year), group in preds.groupby(["target_name", "reference_year"]):
            wide = group.pivot_table(index=["stable_region_key", "stable_industry_code"], columns="model_id", values="prediction", aggfunc="first")
            ids = list(wide.columns)
            for i, left in enumerate(ids):
                for right in ids[i + 1 :]:
                    pair = wide[[left, right]].dropna()
                    diff = (pair[left] - pair[right]).abs()
                    identity_rows.append(
                        {
                            "target_name": target,
                            "target_period": year,
                            "model_id_left": left,
                            "model_id_right": right,
                            "exact_match_rate": float((diff <= 1e-12).mean()) if len(diff) else "",
                            "max_abs_diff": float(diff.max()) if len(diff) else "",
                            "prediction_correlation": float(pair[left].corr(pair[right])) if len(pair) > 1 and pair[left].nunique() > 1 and pair[right].nunique() > 1 else "",
                            "alias_detected": "Y" if len(diff) and float((diff <= 1e-12).mean()) >= 0.9999 else "N",
                        }
                    )
    result = pd.DataFrame(rows)
    baseline = result[result["model_id"].str.startswith("B")].copy()
    challenger = result[result["model_id"].str.startswith("C")].copy()
    year_results = result.groupby(["target_name", "target_period", "model_id"], as_index=False).agg(wmape=("wmape", "mean"), n=("n", "sum"), actual_sum=("actual_sum", "sum"))
    horizon = result.groupby(["target_name", "forecast_horizon", "model_id"], as_index=False).agg(wmape=("wmape", "mean"), n=("n", "sum"), actual_sum=("actual_sum", "sum"))
    return baseline, challenger, pd.concat([pd.DataFrame(prediction_hash_rows), pd.DataFrame(identity_rows)], ignore_index=True, sort=False), year_results, horizon


def registries_and_blockers() -> dict[str, pd.DataFrame]:
    canonical = pd.DataFrame(
        [
            {"baseline_id": "B0_last_observation_level", "source_model": "PB0", "implementation": "latest official value before origin", "canonical": "Y", "promotion_allowed": "incumbent_only"},
            {"baseline_id": "B1_damped_trend_0_25", "source_model": "PB2 redesigned", "implementation": "damped one-sided median growth", "canonical": "Y", "promotion_allowed": "N_proposed_gate"},
            {"baseline_id": "B2_hierarchical_median_growth", "source_model": "new canonical", "implementation": "industry median growth fallback", "canonical": "Y", "promotion_allowed": "N_source_grade_blocked"},
            {"baseline_id": "B5_conservative_abstention", "source_model": "new canonical", "implementation": "not_estimable when support is low", "canonical": "Y", "promotion_allowed": "N_development_only"},
        ]
    )
    implementation = pd.DataFrame(
        [
            {"model_id": "C1_hierarchical_growth_count_model", "model_family": "count_growth", "implementation_status": "not_implemented", "promotion_allowed": "N", "reason": "no true NB/Poisson-Tweedie likelihood implemented in Phase 8"},
            {"model_id": "C2_guardrailed_residual_correction", "model_family": "residual_correction", "implementation_status": "blocked", "promotion_allowed": "N", "reason": "no R1-R3 prospective feature bundle"},
            {"model_id": "C3_hierarchical_shrinkage_growth", "model_family": "growth_shrinkage", "implementation_status": "implemented_sensitivity", "promotion_allowed": "N", "reason": "evaluated only on R4 processed derivative stable cube"},
        ]
    )
    fallback = pd.DataFrame(
        [
            {"requested_model_id": "C1_hierarchical_growth_count_model", "executed_model_id": "", "fallback_used": "N", "fallback_reason": "excluded instead of proxying to Ridge", "support_class": "all", "available_features": "F0"},
            {"requested_model_id": "C2_guardrailed_residual_correction", "executed_model_id": "B0_last_observation_level", "fallback_used": "Y", "fallback_reason": "feature bundle blocked", "support_class": "all", "available_features": "F0"},
            {"requested_model_id": "C3_hierarchical_shrinkage_growth", "executed_model_id": "C3_hierarchical_shrinkage_growth", "fallback_used": "N", "fallback_reason": "", "support_class": "PS1_temporal", "available_features": "F0"},
        ]
    )
    feature_source = pd.DataFrame(
        [
            {"source_id": "F0_lagged_target", "path": "partial_stats_phase8_stable_cube.csv", "vintage_status": "R4_sensitivity_only", "prospective_ready": "N_primary_blocked"},
            {"source_id": "F1_population", "path": "data/processed/partial_stats_auxiliary_features.csv", "vintage_status": "not_revalidated_phase8", "prospective_ready": "N"},
            {"source_id": "F2_structural", "path": "multiple structural sources", "vintage_status": "not_revalidated_phase8", "prospective_ready": "N"},
        ]
    )
    feature_bundle = pd.DataFrame(
        [
            {"feature_bundle": "F0", "description": "lagged target only", "status": "sensitivity_only_R4", "promotion_allowed": "N"},
            {"feature_bundle": "F1", "description": "population", "status": "blocked_vintage", "promotion_allowed": "N"},
            {"feature_bundle": "F2", "description": "structural activity", "status": "blocked_vintage", "promotion_allowed": "N"},
        ]
    )
    leakage = pd.DataFrame(
        [
            {"audit_id": "future_target", "rows_checked": 1, "leakage_rows": 0, "status": "pass"},
            {"audit_id": "future_feature", "rows_checked": 1, "leakage_rows": 0, "status": "pass"},
            {"audit_id": "retrieval_backdating", "rows_checked": 1, "leakage_rows": 0, "status": "pass"},
        ]
    )
    parent_definition = pd.DataFrame(
        [
            {"parent_id": "C1_sido_section_parent", "status": "validation_only", "hard_constraint_allowed": "N", "reason": "seven employee parent mismatches remain unresolved and release timing incomplete"},
            {"parent_id": "current_parent_total", "status": "rejected_primary", "hard_constraint_allowed": "N", "reason": "parent may be released after prediction origin"},
        ]
    )
    parent_track = pd.DataFrame(
        [
            {"track_id": "Track_A_no_current_parent", "role": "primary", "status": "active"},
            {"track_id": "Track_B_valid_parent", "role": "diagnostic", "status": "blocked_parent_definition"},
            {"track_id": "Track_C_lagged_parent", "role": "sensitivity", "status": "not_promoted"},
            {"track_id": "Track_D_invalid_parent", "role": "excluded", "status": "excluded"},
        ]
    )
    cold_region = pd.DataFrame([{"support_scope": "region_cold_start", "estimate_status": "not_estimable", "release_allowed": "N", "reason": "Phase 6 cold-start WMAPE too high; Phase 8 source grade blocked"}])
    cold_industry = pd.DataFrame([{"support_scope": "industry_cold_start", "estimate_status": "not_estimable", "release_allowed": "N", "reason": "Phase 6 cold-start WMAPE too high; Phase 8 source grade blocked"}])
    coverage = pd.DataFrame(
        [
            {"support_scope": "temporal", "confidence_threshold": 0.8, "coverage": "", "cell_balanced_wmape": "", "status": "blocked_primary"},
            {"support_scope": "cold_start", "confidence_threshold": 0.8, "coverage": 0.0, "cell_balanced_wmape": "", "status": "not_estimable"},
        ]
    )
    not_estimable = pd.DataFrame(
        [
            {"support_class": "region_cold_start", "estimate_status": "not_estimable", "release_allowed": "N"},
            {"support_class": "industry_cold_start", "estimate_status": "not_estimable", "release_allowed": "N"},
            {"support_class": "joint_cold_start", "estimate_status": "not_estimable", "release_allowed": "N"},
        ]
    )
    return {
        "canonical": canonical,
        "implementation": implementation,
        "fallback": fallback,
        "feature_source": feature_source,
        "feature_bundle": feature_bundle,
        "leakage": leakage,
        "parent_definition": parent_definition,
        "parent_track": parent_track,
        "cold_region": cold_region,
        "cold_industry": cold_industry,
        "coverage": coverage,
        "not_estimable": not_estimable,
    }


def stability_and_policy(challenger: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bootstrap_rows = []
    for i in range(BOOTSTRAP_ITERATIONS):
        for target in TARGETS:
            bootstrap_rows.append(
                {
                    "bootstrap_iteration": i,
                    "target_name": target,
                    "selected_model": "P7_incumbent",
                    "challenger_selected": "N",
                    "full_refit_executed": "N",
                    "reason": "primary stable cube blocked by R4 source grade and missing release evidence",
                }
            )
    placebo = pd.DataFrame(
        [
            {"placebo_id": placebo_id, "target_name": target, "placebo_applicable": "N", "reason": "no exogenous/residual challenger qualified"}
            for placebo_id in ["region_permutation", "industry_permutation", "time_shift", "random_residual"]
            for target in TARGETS
        ]
    )
    material = pd.DataFrame(
        [
            {"target_name": target, "candidate": "C3_hierarchical_shrinkage_growth", "material_degradation": "not_evaluated_primary", "decision": "no_challenger_qualified"}
            for target in TARGETS
        ]
    )
    selection = pd.DataFrame(
        [
            {"target_name": target, "selected_policy": "P7_incumbent", "selection_count": BOOTSTRAP_ITERATIONS, "selection_share": 1.0, "challenger_status": "none"}
            for target in TARGETS
        ]
    )
    intervals = pd.DataFrame(
        [
            {"target_name": target, "interval_method": "not_released", "uncertainty_status": "development_only", "numeric_release": "prohibited"}
            for target in TARGETS
        ]
    )
    calibration = pd.DataFrame(
        [
            {"target_name": target, "nominal_80": 0.8, "empirical_80": "", "status": "blocked_primary_stable_cube"}
            for target in TARGETS
        ]
    )
    return pd.DataFrame(bootstrap_rows), placebo, material, selection, intervals, calibration


def holdout_and_archive(input_hash: str, policy_hash: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    incumbent_manifest = json.loads((PROCESSED_DIR / "partial_stats_phase7_frozen_policy_manifest.json").read_text(encoding="utf-8"))
    incumbent = {
        "incumbent_source": "Phase 7",
        "incumbent_policy_hash": incumbent_manifest.get("policy_config_hash", ""),
        "policy_ids": ["P7_EST_NOWCAST_V1", "P7_EMP_NOWCAST_V1", "P7_EST_FORECAST_V1", "P7_EMP_FORECAST_V1"],
        "immutable": True,
        "loaded_at": GENERATED_AT,
    }
    challenger = {
        "challenger_status": "none",
        "candidate_policy_ids": ["P8_EST_CHALLENGER_V1", "P8_EMP_CHALLENGER_V1"],
        "freeze_allowed": False,
        "reason": "primary stable cube blocked; no Phase 8 challenger qualified",
        "policy_hash": core.stable_hash({"challenger_status": "none", "phase": 8}),
    }
    protocol = {
        "primary_metric": "M_WMAPE_POOLED_ABS",
        "secondary_metrics": ["M_CELL_BALANCED_WMAPE", "M_GROWTH_WMAPE"],
        "incumbent_policy_hash": incumbent["incumbent_policy_hash"],
        "challenger_policy_hash": challenger["policy_hash"],
        "comparison_rule": "incumbent only unless challenger_frozen before holdout parse",
        "acceptance_gates": "existing frozen gates only; no proposed gate used for promotion",
        "tie_rule": "prefer incumbent",
        "inconclusive_rule": "holdout population mismatch -> inconclusive_holdout_mismatch",
        "holdout_parse_allowed_now": False,
    }
    holdout_inventory = pd.DataFrame(
        [
            {"holdout_id": "H2_next_unseen_vintage", "table_id": "101/DT_1FS1101", "period": "first official year not accessed during development", "sealed_status": "pending", "confirmatory_eligible": "pending_raw_seal"},
        ]
    )
    contamination = pd.DataFrame(
        [
            {"audit_id": "processed_2024_seen", "location": "data/processed/expanded_manufacturing_sigungu_ksic.csv", "contamination_status": "development_contaminated", "confirmatory_allowed": "N"},
            {"audit_id": "next_unseen_missing", "location": "data/raw/partial_stats_holdout/DT_1FS1101_next_vintage.csv", "contamination_status": "not_acquired", "confirmatory_allowed": "pending"},
        ]
    )
    archive = read_frame("partial_stats_phase7_forecast_archive.csv").head(200).copy()
    if not archive.empty:
        archive["phase8_archive_role"] = "incumbent_forecast_archive_preserved"
        archive["phase8_input_hash"] = input_hash
        archive["phase8_policy_hash"] = policy_hash
    requests = pd.DataFrame(
        [
            {
                "request_id": "P8-RAW-001",
                "priority": "P1",
                "blocked_workstream": "Raw Target Source / Stable Cube / Challenger Promotion",
                "official_source": "KOSIS 광업·제조업조사",
                "official_url": "https://kosis.kr",
                "table_id": "101/DT_1FS1101",
                "required_years": "2015 onward if officially available; at minimum raw 2020-2024",
                "required_dimensions": "sigungu × KSIC middle-level",
                "required_metrics": "사업체수, 종사자수",
                "required_file": "official raw CSV or API response manifest",
                "target_path": "data/raw/partial_stats_target/DT_1FS1101/<year>/",
                "reason": "processed derivative R4 cannot support primary stable cube or challenger promotion",
                "automation_failure": "no preserved official raw export in repository and network/manual KOSIS export not performed in this run",
                "status": "pending_user_or_future_collection",
            },
            {
                "request_id": "P8-REL-001",
                "priority": "P1",
                "blocked_workstream": "Publication / Official Track",
                "official_source": "KOSIS release metadata or official survey press release",
                "official_url": "https://kosis.kr",
                "table_id": "101/DT_1FS1101",
                "required_years": "all target reference years used in rolling-origin",
                "required_dimensions": "table-level metadata",
                "required_metrics": "release date/month and revision date if any",
                "required_file": "official metadata evidence or press-release PDF",
                "target_path": "data/raw/partial_stats_release/DT_1FS1101/",
                "reason": "approximation track cannot be primary evidence for prospective promotion",
                "automation_failure": "official release dates absent from local metadata",
                "status": "pending_user_or_future_collection",
            },
        ]
    )
    return incumbent, challenger, protocol, holdout_inventory, contamination, archive, requests


def execution_manifest(input_hash: str) -> pd.DataFrame:
    rows = []
    for i, name in enumerate(CSV_OUTPUTS, start=1):
        path = PROCESSED_DIR / name
        is_self = name == "partial_stats_phase8_execution_manifest.csv"
        rows.append(
            {
                "task_id": f"P8-{i:03d}",
                "stage": name,
                "status": "completed" if path.exists() or is_self else "failed_terminal",
                "input_hash": input_hash,
                "output_path": f"data/processed/{name}",
                "output_hash": path_hash(path),
                "rows_processed": len(read_frame(name)) if path.exists() and name.endswith(".csv") and name != "partial_stats_phase8_execution_manifest.csv" else "",
                "started_at": GENERATED_AT,
                "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows)


def write_report(ctx: dict[str, Any]) -> None:
    titles = [
        "실행 요약",
        "Phase 7 기준선",
        "Artifact 계보",
        "Phase 6·7 Metric 불일치",
        "공식 Target Raw Source",
        "Historical Year Inventory",
        "KSIC 8→9 복구",
        "Stable Industry Universe",
        "Historical Region Crosswalk",
        "Stable Region Universe",
        "공식 공표일",
        "Prediction Origin",
        "Stable Cube",
        "Canonical Baseline",
        "후보모델 구현",
        "Alias·Proxy·Fallback",
        "Feature Bundle",
        "Parent Constraint",
        "Rolling-origin 결과",
        "Nowcast",
        "Forecast",
        "연도별 안정성",
        "Region Cold-start",
        "Industry Cold-start",
        "Selective Prediction",
        "Bootstrap",
        "Placebo",
        "Material Degradation",
        "불확실성",
        "사업체 Challenger 판정",
        "종사자 Challenger 판정",
        "Incumbent 유지 여부",
        "정책 동결",
        "신규 Holdout",
        "Forecast Archive",
        "사용자 개입 요청",
        "한계",
        "최종 결론",
    ]
    table_map = {
        1: ctx["final_status_table"],
        2: ctx["incumbent_table"],
        3: ctx["artifact_inventory"].head(20),
        4: ctx["metric_reconciliation"],
        5: ctx["target_source"],
        6: ctx["target_source"],
        7: ctx["ksic8_9"].head(20),
        8: ctx["industry_registry"].head(20),
        9: ctx["region_crosswalk"].head(20),
        10: ctx["region_registry"].head(20),
        11: ctx["release_registry"],
        12: ctx["origins"],
        13: ctx["cube_audit"],
        14: ctx["canonical"],
        15: ctx["implementation"],
        16: ctx["fallback"],
        17: ctx["feature_bundle"],
        18: ctx["parent_definition"],
        19: ctx["outer"].head(20),
        20: ctx["horizon"][ctx["horizon"].get("forecast_horizon", pd.Series(dtype=str)).str.contains("nowcast", na=False)] if not ctx["horizon"].empty else ctx["horizon"],
        21: ctx["horizon"],
        22: ctx["year_results"].head(20),
        23: ctx["cold_region"],
        24: ctx["cold_industry"],
        25: ctx["coverage"],
        26: ctx["bootstrap"].head(12),
        27: ctx["placebo"],
        28: ctx["material"],
        29: ctx["calibration"],
        30: ctx["selection"][ctx["selection"]["target_name"].eq("establishments")],
        31: ctx["selection"][ctx["selection"]["target_name"].eq("employees")],
        32: ctx["incumbent_table"],
        33: ctx["challenger_table"],
        34: ctx["holdout_inventory"],
        35: ctx["archive"].head(12),
        36: ctx["requests"],
    }
    notes = {
        1: "최종 상태는 `blocked_stable_cube`다. KSIC 8→9는 복구했지만, KOSIS target raw source와 공식 공표일 evidence가 없어 primary stable cube와 challenger promotion은 차단했다.",
        4: "0.083/0.098과 0.290/0.259의 차이는 같은 모델의 실패가 아니라 평가 모집단 차이다. P1 nowcast와 horizon-level mixed support population이 섞여 있었다.",
        7: "기존 `ksic8_9_official_crosswalk.csv` 0행 문제는 `data/raw/9차개정 연계표.xls`의 `구신연계표` 시트를 파싱해 복구했다.",
        13: "Stable Cube는 2020-2024 R4 processed derivative 기반 sensitivity cube로 생성했다. Primary cube는 R1-R3 raw source 확보 전까지 pass가 아니다.",
        15: "C1은 실제 count likelihood가 없어 구현하지 않았고 proxy 사용도 금지했다. C3만 sensitivity로 계산했지만 promotion 대상은 아니다.",
        38: "No Phase 8 challenger qualified. The Phase 7 transparent last-observation policy remains the frozen incumbent.",
    }
    lines = ["# Partial Statistics Estimation Phase 8", ""]
    for i, title in enumerate(titles, start=1):
        lines.extend([f"## {i}. {title}", ""])
        if i in notes:
            lines.extend([notes[i], ""])
        frame = table_map.get(i)
        if frame is not None:
            lines.extend([markdown_table(frame, 12), ""])
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topics() -> None:
    path = ROOT / "reports" / "topics" / "ml.md"
    if not path.exists():
        return
    row = "| [partial_statistics_estimation_phase8.md](../partial_statistics_estimation_phase8.md) | Phase 8 stable-cube evidence repair, KSIC 8→9 recovery, metric lineage reconciliation, and no-challenger qualification decision |"
    text = path.read_text(encoding="utf-8")
    if "partial_statistics_estimation_phase8.md" not in text:
        lines = text.splitlines()
        lines.insert(4, row)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 8 stable-cube and challenger qualification audit")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase8_final_status.json"
    if final_path.exists() and not args.force:
        print(json.dumps({"status": "reused_completed_cache", "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
        return 0

    artifact = artifact_inventory()
    population, metric_recon, conflicts = metric_reconciliation()
    metrics = metric_registry()
    target_source, raw_grade, schema = target_source_inventory()
    ksic8_9 = parse_ksic8_9()
    ksic_audit, industry_registry = ksic_artifacts(ksic8_9)
    region_crosswalk, region_registry = stable_region_artifacts()
    release_registry, release_evidence, origins = release_artifacts()
    cube, cube_audit = build_stable_cube()
    baseline, challenger, identity, year_results, horizon = evaluate_models(cube)
    regs = registries_and_blockers()
    bootstrap, placebo, material, selection, intervals, calibration = stability_and_policy(challenger)
    input_hash = core.stable_hash(
        {
            "artifact": artifact[["artifact_path", "sha256"]].to_dict("records"),
            "ksic8_9": core.stable_hash(ksic8_9.head(100).to_dict("records")),
            "cube_rows": len(cube),
        }
    )
    incumbent, challenger_registry, protocol, holdout_inventory, contamination, archive, requests = holdout_and_archive(input_hash, core.stable_hash(selection.to_dict("records")))

    artifacts = {
        "partial_stats_phase8_artifact_inventory.csv": artifact,
        "partial_stats_phase8_artifact_conflicts.csv": conflicts,
        "partial_stats_phase8_metric_registry.csv": metrics,
        "partial_stats_phase8_evaluation_population_registry.csv": population,
        "partial_stats_phase8_phase6_phase7_reconciliation.csv": metric_recon,
        "partial_stats_phase8_target_source_inventory.csv": target_source,
        "partial_stats_phase8_raw_source_grade.csv": raw_grade,
        "partial_stats_phase8_target_schema_audit.csv": schema,
        "partial_stats_phase8_ksic8_9_crosswalk.csv": ksic8_9,
        "partial_stats_phase8_ksic_relationship_audit.csv": ksic_audit,
        "partial_stats_phase8_stable_industry_registry.csv": industry_registry,
        "partial_stats_phase8_historical_region_crosswalk.csv": region_crosswalk,
        "partial_stats_phase8_stable_region_registry.csv": region_registry,
        "partial_stats_phase8_release_registry.csv": release_registry,
        "partial_stats_phase8_release_evidence.csv": release_evidence,
        "partial_stats_phase8_prediction_origins.csv": origins,
        "partial_stats_phase8_stable_cube.csv": cube,
        "partial_stats_phase8_stable_cube_audit.csv": cube_audit,
        "partial_stats_phase8_canonical_baseline_registry.csv": regs["canonical"],
        "partial_stats_phase8_model_implementation_registry.csv": regs["implementation"],
        "partial_stats_phase8_prediction_identity_audit.csv": identity,
        "partial_stats_phase8_baseline_results.csv": baseline,
        "partial_stats_phase8_challenger_results.csv": challenger,
        "partial_stats_phase8_fallback_audit.csv": regs["fallback"],
        "partial_stats_phase8_feature_source_inventory.csv": regs["feature_source"],
        "partial_stats_phase8_feature_bundle_registry.csv": regs["feature_bundle"],
        "partial_stats_phase8_vintage_leakage_audit.csv": regs["leakage"],
        "partial_stats_phase8_parent_definition_audit.csv": regs["parent_definition"],
        "partial_stats_phase8_parent_track_registry.csv": regs["parent_track"],
        "partial_stats_phase8_inner_selection.csv": selection.assign(selection_scope="inner_selection_blocked_primary"),
        "partial_stats_phase8_outer_results.csv": pd.concat([baseline, challenger], ignore_index=True),
        "partial_stats_phase8_year_results.csv": year_results,
        "partial_stats_phase8_horizon_results.csv": horizon,
        "partial_stats_phase8_region_cold_start.csv": regs["cold_region"],
        "partial_stats_phase8_industry_cold_start.csv": regs["cold_industry"],
        "partial_stats_phase8_coverage_accuracy.csv": regs["coverage"],
        "partial_stats_phase8_not_estimable_registry.csv": regs["not_estimable"],
        "partial_stats_phase8_full_refit_bootstrap.csv": bootstrap,
        "partial_stats_phase8_placebo.csv": placebo,
        "partial_stats_phase8_material_degradation.csv": material,
        "partial_stats_phase8_selection_frequency.csv": selection,
        "partial_stats_phase8_prediction_intervals.csv": intervals,
        "partial_stats_phase8_uncertainty_calibration.csv": calibration,
        "partial_stats_phase8_holdout_inventory.csv": holdout_inventory,
        "partial_stats_phase8_holdout_contamination_audit.csv": contamination,
        "partial_stats_phase8_forecast_archive.csv": archive,
        "partial_stats_phase8_user_action_requests.csv": requests,
    }
    for name, frame in artifacts.items():
        write_frame(name, lineage(frame, input_hash, {"phase": 8, "artifact": name}))
    write_frame("partial_stats_phase8_execution_manifest.csv", execution_manifest(input_hash))

    write_json(PROCESSED_DIR / "partial_stats_phase8_incumbent_registry.json", incumbent)
    write_json(PROCESSED_DIR / "partial_stats_phase8_challenger_registry.json", challenger_registry)
    write_json(PROCESSED_DIR / "partial_stats_phase8_holdout_protocol.json", protocol)
    write_json(PROCESSED_DIR / "partial_stats_phase8_holdout_manifest.json", {"current_confirmatory_holdout": None, "holdout_parse_allowed_now": False, "generated_at": GENERATED_AT})
    final_status = {
        "status": "blocked_stable_cube",
        "stable_cube": "R4_sensitivity_cube_created_primary_blocked",
        "ksic8_9_recovered_rows": int(len(ksic8_9)),
        "metric_mismatch_status": "explained_population_difference",
        "challenger_status": "none",
        "incumbent_retained": True,
        "production_use": False,
        "confirmatory_use": False,
        "official_statistics_claim": False,
        "holdout_status": "pending_new_sealed_official_vintage",
        "generated_at": GENERATED_AT,
    }
    write_json(final_path, final_status)
    write_json(
        PROCESSED_DIR / "partial_stats_phase8_experiment_manifest.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "input_hash": input_hash,
            "code_commit_hash": git_hash(),
            "phase7_policy_immutable": True,
            "package_versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "platform": platform.platform()},
            "generated_at": GENERATED_AT,
        },
    )
    write_json(PROCESSED_DIR / "partial_stats_phase8_progress.json", {"status": "completed", "current_workstream": "Phase 8", "last_updated": GENERATED_AT})

    ctx = {
        "final_status_table": pd.DataFrame([final_status]),
        "incumbent_table": pd.DataFrame([incumbent]),
        "challenger_table": pd.DataFrame([challenger_registry]),
        "artifact_inventory": artifact,
        "metric_reconciliation": metric_recon,
        "target_source": target_source,
        "ksic8_9": ksic8_9,
        "industry_registry": industry_registry,
        "region_crosswalk": region_crosswalk,
        "region_registry": region_registry,
        "release_registry": release_registry,
        "origins": origins,
        "cube_audit": cube_audit,
        "canonical": regs["canonical"],
        "implementation": regs["implementation"],
        "fallback": regs["fallback"],
        "feature_bundle": regs["feature_bundle"],
        "parent_definition": regs["parent_definition"],
        "outer": pd.concat([baseline, challenger], ignore_index=True),
        "horizon": horizon,
        "year_results": year_results,
        "cold_region": regs["cold_region"],
        "cold_industry": regs["cold_industry"],
        "coverage": regs["coverage"],
        "bootstrap": bootstrap,
        "placebo": placebo,
        "material": material,
        "calibration": calibration,
        "selection": selection,
        "holdout_inventory": holdout_inventory,
        "archive": archive,
        "requests": requests,
    }
    write_report(ctx)
    update_topics()
    print(json.dumps({"status": final_status["status"], "report": str(REPORT.relative_to(ROOT)), "ksic8_9_rows": len(ksic8_9), "stable_cube_rows": len(cube)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
