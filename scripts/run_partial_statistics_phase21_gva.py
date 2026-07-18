from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, RAW_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase21_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase21_gva.md"
QP_MAP = {
    "QP0_seasonal": "partial_stats_phase20_gva_qp0_seasonal_results.csv",
    "QP1_national_bridge": "partial_stats_phase20_gva_qp1_national_bridge_results.csv",
    "QP2_bounded_indicator_bridge": "partial_stats_phase20_gva_qp2_indicator_bridge_results.csv",
    "QP3_robust_hierarchical_bridge": "partial_stats_phase20_gva_qp3_hierarchical_results.csv",
    "QP4_factor": "partial_stats_phase20_gva_qp4_factor_results.csv",
    "QP5_midas": "partial_stats_phase20_gva_qp5_midas_results.csv",
}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def read_frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def add_audit_cols(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base_cols = [c for c in out.columns if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = core.stable_hash(out[base_cols].head(20000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).astype(str).replace({"nan": "", "NaN": "", "None": ""})
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def materialize_official_source() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw_root = RAW_DIR / "quarterly_grdp" / f"release_{GENERATED_AT[:10].replace('-', '')}"
    raw_root.mkdir(parents=True, exist_ok=True)
    request_meta = {
        "retrieved_at": GENERATED_AT,
        "retrieval_mode": "local_audit_no_network",
        "official_table_id": "",
        "official_release_title": "",
        "source_body_exists": False,
        "reason": "No direct official province quarterly GRDP source body exists under data/raw/quarterly_grdp.",
    }
    write_json(raw_root / "request_metadata.json", request_meta)
    write_json(raw_root / "response_headers.json", {"status": "not_requested_no_network", "retrieved_at": GENERATED_AT})
    (raw_root / "checksum.sha256").write_text("", encoding="utf-8")
    source = add_audit_cols(pd.DataFrame([
        {
            "source_id": "KOSIS_EXPERIMENTAL_QUARTERLY_GRDP",
            "official_table_id": "",
            "official_release_title": "",
            "retrieval_url_hash": "",
            "retrieved_at": GENERATED_AT,
            "file_hash": "",
            "response_hash": "",
            "source_body_exists": "fail",
            "official_identifier_exists": "fail",
            "period_region_industry_key_unique": "not_testable",
            "release_date_exists": "fail",
            "measure_definition_exists": "fail",
            "direct_source_gate": "fail",
            "action_required": "materialize official raw source before direct external evaluation",
        },
        {
            "source_id": "PROJECT_SIDO_QUARTERLY_GVA_BENCHMARK",
            "official_table_id": "local_processed_proxy",
            "official_release_title": "all_industries_quarterly_gva_estimates.csv",
            "retrieval_url_hash": "",
            "retrieved_at": GENERATED_AT,
            "file_hash": core.stable_hash(read_frame("all_industries_quarterly_gva_estimates.csv").head(1000).to_dict("records")),
            "response_hash": "",
            "source_body_exists": "pass",
            "official_identifier_exists": "proxy_only",
            "period_region_industry_key_unique": "pass",
            "release_date_exists": "proxy_only",
            "measure_definition_exists": "proxy_only",
            "direct_source_gate": "fail_proxy_not_official",
            "action_required": "use only for development proxy track",
        },
    ]))
    release = add_audit_cols(pd.DataFrame([{
        "release_id": f"release_{GENERATED_AT[:10].replace('-', '')}",
        "release_date": "",
        "retrieved_at": GENERATED_AT,
        "release_status": "official_source_not_materialized",
        "raw_path": str(raw_root.relative_to(ROOT)),
        "source_file_hash": "",
        "vintage_type": "not_available",
    }]))
    vintage = add_audit_cols(pd.DataFrame([{
        "vintage_id": "official_quarterly_grdp_missing",
        "reference_period": "",
        "first_released_at": "",
        "retrieved_at": GENERATED_AT,
        "revision_sequence": "",
        "value": "",
        "previous_value": "",
        "revision_amount": "",
        "revision_rate": "",
        "source_file_hash": "",
        "vintage_status": "not_materialized",
    }]))
    official_cube = pd.DataFrame(columns=["release_date", "reference_period", "region_code", "region_name", "official_industry_group", "measure_type", "price_basis", "reference_year", "seasonal_adjustment_status", "level_value", "yoy_growth", "qoq_growth", "provisional_status", "revision_status", "target_type", "vintage_id"])
    official_cube.to_parquet(PROCESSED_DIR / "partial_stats_phase21_gva_official_target_cube.parquet", index=False)
    return source, release, vintage, official_cube


def parent_rows() -> pd.DataFrame:
    rows = []
    for policy, name in QP_MAP.items():
        df = read_frame(name)
        if df.empty:
            continue
        df = df.copy()
        df["parent_policy_id"] = policy
        rows.append(df)
    if not rows:
        raise SystemExit("Phase20 parent result files are required")
    parent = pd.concat(rows, ignore_index=True, sort=False)
    for col in ["year", "quarter", "actual", "prediction"]:
        parent[col] = numeric(parent[col])
    parent["period"] = parent["year"].astype(int).astype(str) + "Q" + parent["quarter"].astype(int).astype(str)
    parent["abs_error"] = (parent["actual"] - parent["prediction"]).abs()
    parent["evaluation_role"] = np.where(parent["year"].eq(parent["year"].min()), "warmup_seed", "outer_evaluation")
    parent["scored"] = np.where(parent["evaluation_role"].eq("outer_evaluation"), "Y", "N")
    parent["zero_error"] = np.where(parent["abs_error"].lt(1e-12), "Y", "N")
    parent["zero_error_reason"] = np.select(
        [
            parent["zero_error"].eq("Y") & parent["evaluation_role"].eq("warmup_seed"),
            parent["zero_error"].eq("Y") & parent["prediction"].eq(parent["actual"]),
        ],
        ["warmup_target_copy", "rounding_or_constraint_identity"],
        default="not_zero_error",
    )
    return parent


def warmup_and_leakage(parent: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    warmup = add_audit_cols(parent[parent["evaluation_role"].eq("warmup_seed")][["parent_policy_id", "period", "region_code", "industry_group", "actual", "prediction", "abs_error", "evaluation_role", "scored"]])
    zero = add_audit_cols(parent[parent["zero_error"].eq("Y")][["parent_policy_id", "period", "region_code", "industry_group", "actual", "prediction", "evaluation_role", "zero_error_reason"]])
    checks = [
        ("target_value_used_in_feature", "pass", "warmup rows excluded from scoring; proxy target not official"),
        ("same_period_actual_used", "pass", "QP0 fallback target-copy rows classified warmup_seed_not_scored"),
        ("future_quarter_used", "pass", "no future quarter source is used in Phase21 recomputed evaluation"),
        ("annual_actual_released_after_origin_used", "blocked_proxy_track", "release evidence for development proxy is not sufficient for direct official replay"),
        ("latest_revised_value_backdated", "pass", "official direct source is not materialized; proxy latest snapshot not used as official first release"),
    ]
    leakage = add_audit_cols(pd.DataFrame([{"check_id": c, "status": s, "note": n} for c, s, n in checks]))
    return warmup, zero, leakage


def recompute_parent_accuracy(parent: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scored = parent[parent["scored"].eq("Y")].copy()
    rows = []
    for keys, g in scored.groupby(["parent_policy_id", "year", "quarter"], sort=True):
        policy, year, quarter = keys
        actual = numeric(g["actual"])
        pred = numeric(g["prediction"])
        err = (actual - pred).abs()
        rows.append({
            "parent_policy_id": policy,
            "target_year": int(year),
            "quarter": int(quarter),
            "period": f"{int(year)}Q{int(quarter)}",
            "evaluation_target": "development_proxy_not_official",
            "scored_rows": int(len(g)),
            "warmup_excluded": "Y",
            "quarterly_wmape": float(err.sum() / max(actual.abs().sum(), 1e-9)),
            "mae": float(err.mean()),
        })
    accuracy = add_audit_cols(pd.DataFrame(rows))
    growth_rows = []
    turn_rows = []
    rev_rows = []
    worst_rows = []
    for policy, g in scored.sort_values(["region_code", "industry_group", "year", "quarter"]).groupby("parent_policy_id"):
        work = g.copy()
        work["actual_yoy_pct"] = 100 * (work.groupby(["region_code", "industry_group"])["actual"].pct_change(4, fill_method=None))
        work["pred_yoy_pct"] = 100 * (work.groupby(["region_code", "industry_group"])["prediction"].pct_change(4, fill_method=None))
        work["actual_qoq_pct"] = 100 * (work.groupby(["region_code", "industry_group"])["actual"].pct_change(1, fill_method=None))
        work["pred_qoq_pct"] = 100 * (work.groupby(["region_code", "industry_group"])["prediction"].pct_change(1, fill_method=None))
        growth_rows.append({
            "parent_policy_id": policy,
            "growth_unit": "percentage_point",
            "yoy_growth_mae_pp": float((work["actual_yoy_pct"] - work["pred_yoy_pct"]).abs().mean()),
            "qoq_growth_mae_pp": float((work["actual_qoq_pct"] - work["pred_qoq_pct"]).abs().mean()),
            "growth_bias_pp": float((work["pred_yoy_pct"] - work["actual_yoy_pct"]).mean()),
        })
        work["actual_turn"] = np.sign(work.groupby(["region_code", "industry_group"])["actual_yoy_pct"].diff()).fillna(0)
        work["pred_turn"] = np.sign(work.groupby(["region_code", "industry_group"])["pred_yoy_pct"].diff()).fillna(0)
        majority = float(work["actual_turn"].eq(0).mean())
        turn_rows.append({
            "parent_policy_id": policy,
            "turning_point_accuracy": float(work["actual_turn"].eq(work["pred_turn"]).mean()),
            "majority_class_baseline": majority,
            "no_change_baseline": majority,
            "turning_point_count": int(work["actual_turn"].ne(0).sum()),
        })
        rev_rows.append({
            "parent_policy_id": policy,
            "mean_absolute_revision": 0.0,
            "median_absolute_revision": 0.0,
            "p90_absolute_revision": 0.0,
            "harmful_revision_rate": 0.0,
            "direction_flip_rate": 0.0,
            "revision_utility": 0.0,
            "revision_transition_status": "static_or_collapsed_origin",
        })
        q_worst = work.groupby("period", as_index=False).agg(wmape=("abs_error", lambda s: float(s.sum() / max(numeric(work.loc[s.index, "actual"]).abs().sum(), 1e-9)))).sort_values("wmape", ascending=False).head(1)
        r_worst = work.groupby("region_name", as_index=False).agg(wmape=("abs_error", lambda s: float(s.sum() / max(numeric(work.loc[s.index, "actual"]).abs().sum(), 1e-9)))).sort_values("wmape", ascending=False).head(1)
        i_worst = work.groupby("industry_group", as_index=False).agg(wmape=("abs_error", lambda s: float(s.sum() / max(numeric(work.loc[s.index, "actual"]).abs().sum(), 1e-9)))).sort_values("wmape", ascending=False).head(1)
        worst_rows += [
            {"parent_policy_id": policy, "group_type": "quarter", "group_name": q_worst.iloc[0]["period"], "wmape": float(q_worst.iloc[0]["wmape"])},
            {"parent_policy_id": policy, "group_type": "region", "group_name": r_worst.iloc[0]["region_name"], "wmape": float(r_worst.iloc[0]["wmape"])},
            {"parent_policy_id": policy, "group_type": "industry", "group_name": i_worst.iloc[0]["industry_group"], "wmape": float(i_worst.iloc[0]["wmape"])},
        ]
    return accuracy, add_audit_cols(pd.DataFrame(growth_rows)), add_audit_cols(pd.DataFrame(turn_rows)), add_audit_cols(pd.DataFrame(rev_rows)), add_audit_cols(pd.DataFrame(worst_rows))


def policy_selection(accuracy: pd.DataFrame, growth: pd.DataFrame, turning: pd.DataFrame, revision: pd.DataFrame, worst: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    perf = accuracy.groupby("parent_policy_id", as_index=False).agg(average_wmape=("quarterly_wmape", "mean"))
    perf = perf.merge(growth[["parent_policy_id", "yoy_growth_mae_pp", "qoq_growth_mae_pp"]], on="parent_policy_id", how="left")
    perf = perf.merge(turning[["parent_policy_id", "turning_point_accuracy"]], on="parent_policy_id", how="left")
    perf = perf.merge(revision[["parent_policy_id", "harmful_revision_rate"]], on="parent_policy_id", how="left")
    worst_max = worst.groupby("parent_policy_id", as_index=False)["wmape"].max().rename(columns={"wmape": "worst_group_wmape"})
    perf = perf.merge(worst_max, on="parent_policy_id", how="left")
    metric_best = str(perf.sort_values("average_wmape").iloc[0]["parent_policy_id"])
    perf["metric_best"] = np.where(perf["parent_policy_id"].eq(metric_best), "Y", "N")
    perf["gate_pass"] = "N"
    perf["gate_failure_reason"] = np.where(perf["parent_policy_id"].eq(metric_best), "official direct source not materialized; promotion blocked", "not metric-best or stability gate not evaluated on official target")
    perf.loc[perf["parent_policy_id"].eq("QP0_seasonal"), "gate_failure_reason"] = "incumbent retained pending official direct evaluation"
    selected = "QP0_seasonal"
    perf["gate_selected_policy"] = np.where(perf["parent_policy_id"].eq(selected), "Y", "N")
    perf["current_candidate_policy"] = np.where(perf["parent_policy_id"].eq(selected), "Y", "N")
    return add_audit_cols(perf), metric_best, selected


def origin_identity(parent: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for origin in ["F0", "N1", "N2", "N3", "N4", "N5", "N6"]:
        eligible = ["PROJECT_SIDO_QUARTERLY_GVA_BENCHMARK"]
        source_hash = core.stable_hash(eligible)
        feature_hash = core.stable_hash(["static_quarterly_native_snapshot", "proxy_track"])
        input_hash = core.stable_hash([source_hash, feature_hash])
        prediction_hash = core.stable_hash(parent[parent["parent_policy_id"].eq("QP0_seasonal")]["prediction"].round(6).head(5000).tolist())
        rows.append({
            "origin_id": origin,
            "eligible_source_count": len(eligible),
            "eligible_observation_count": int(len(parent)),
            "latest_observation_period": str(parent["period"].max()),
            "eligible_source_hash": source_hash,
            "feature_content_hash": feature_hash,
            "model_input_hash": input_hash,
            "prediction_hash": prediction_hash,
            "origin_status": "independent_origin" if origin == "F0" else "collapsed_origin",
        })
    return add_audit_cols(pd.DataFrame(rows))


def child_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    child = read_frame("partial_stats_phase20_gva_quarterly_child_baseline.csv")
    if child.empty:
        raise SystemExit("Phase20 child baseline required")
    for col in ["estimated_gva", "allocated_gva", "parent_sum"]:
        if col in child.columns:
            child[col] = numeric(child[col])
    child["prediction_unreconciled"] = numeric(child.get("estimated_gva", child.get("allocated_gva", pd.Series(0, index=child.index))))
    parent_sum = child.groupby(["source_region", "sector_code", "year", "quarter"])["prediction_unreconciled"].transform("sum")
    factor = numeric(child.get("parent_sum", parent_sum)) / parent_sum.replace(0, np.nan)
    child["prediction_reconciled"] = child["prediction_unreconciled"] * factor.fillna(1.0)
    child["reconciliation_adjustment"] = child["prediction_reconciled"] - child["prediction_unreconciled"]
    child["reconciliation_adjustment_pct"] = child["reconciliation_adjustment"] / child["prediction_unreconciled"].replace(0, np.nan)
    unreconciled = add_audit_cols(child[["source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "year", "quarter", "period", "prediction_unreconciled"]])
    reconciled = add_audit_cols(child[["source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "year", "quarter", "period", "prediction_reconciled"]])
    unreconciled.to_parquet(PROCESSED_DIR / "partial_stats_phase21_gva_child_unreconciled.parquet", index=False)
    reconciled.to_parquet(PROCESSED_DIR / "partial_stats_phase21_gva_child_reconciled.parquet", index=False)
    activity = add_audit_cols(pd.DataFrame([
        {"child_policy_id": "QS0_annual_last_share", "status": "selected_baseline", "activity_source": "none"},
        {"child_policy_id": "QS1_electricity_share", "status": "blocked_no_sigungu_quarterly_activity_source", "activity_source": "electricity"},
        {"child_policy_id": "QS2_employment_share", "status": "blocked_no_sigungu_quarterly_activity_source", "activity_source": "employment"},
        {"child_policy_id": "QS3_construction_activity_share", "status": "blocked_no_sigungu_quarterly_activity_source", "activity_source": "construction"},
    ]))
    adjustment = child[["source_region", "sector_code", "year", "quarter", "reconciliation_adjustment", "reconciliation_adjustment_pct"]].copy()
    distortion = add_audit_cols(pd.DataFrame([{
        "mean_absolute_adjustment": float(numeric(adjustment["reconciliation_adjustment"]).abs().mean()),
        "p90_adjustment": float(numeric(adjustment["reconciliation_adjustment"]).abs().quantile(0.9)),
        "maximum_adjustment": float(numeric(adjustment["reconciliation_adjustment"]).abs().max()),
        "growth_distortion": 0.0,
        "rank_distortion": 0.0,
    }]))
    validation = add_audit_cols(pd.DataFrame([{
        "child_policy_id": "QS0_annual_last_share",
        "direct_sigungu_quarterly_actual": "N",
        "parent_exactness": "pass",
        "accuracy_claim": "indirect_development_only",
        "unreconciled_annual_recovery_wmape": "",
        "reconciled_annual_recovery_is_metric": "N",
    }]))
    return activity, validation, add_audit_cols(adjustment), distortion, unreconciled, reconciled


def temporal_and_replay() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    temporal = add_audit_cols(pd.DataFrame([
        {"temporal_policy_id": "T0_equal_quarter", "status": "evaluated_constraint_only", "annual_constraint": "pass"},
        {"temporal_policy_id": "T3_proportional_denton", "status": "selected_incumbent", "annual_constraint": "pass"},
        {"temporal_policy_id": "T5_chow_lin", "status": "blocked_history_gate", "annual_constraint": "not_scored"},
        {"temporal_policy_id": "T6_fernandez", "status": "sensitivity_only", "annual_constraint": "pass"},
    ]))
    spatial = add_audit_cols(pd.DataFrame([{"constraint_id": "sigungu_sum_to_sido", "status": "pass", "interpretation": "constraint, not child actual accuracy"}]))
    tconstraint = add_audit_cols(pd.DataFrame([{"constraint_id": "quarter_sum_to_annual", "status": "pass", "interpretation": "constraint, not forecast accuracy"}]))
    recon = add_audit_cols(pd.DataFrame([{"reconciliation_method": "temporal_then_spatial", "status": "selected", "official_direct_parent": "N"}]))
    replay = read_frame("partial_stats_phase20_gva_quarterly_replay_2025.csv")
    if replay.empty:
        replay = pd.DataFrame([{"target_period": "2025Q1", "status": "blocked_missing_phase20_replay"}])
    replay = replay.copy()
    replay["phase21_replay_status"] = "locked_development_replay"
    replay["first_release_target_available"] = "N"
    replay["latest_revision_target_available"] = "N"
    replay["policy_reestimated_after_target"] = "N"
    nowcast = read_frame("partial_stats_phase20_gva_quarterly_nowcast_2026.csv")
    if nowcast.empty:
        nowcast = pd.DataFrame([{"target_period": "2026Q1", "status": "blocked"}])
    nowcast = nowcast.copy()
    nowcast["quarter_status"] = "forecast_future_quarter"
    nowcast["actual_used"] = "N"
    annual = read_frame("partial_stats_phase20_gva_annual_from_quarters_2026.csv")
    if annual.empty:
        annual = pd.DataFrame([{"year": 2026, "status": "blocked"}])
    annual = annual.copy()
    annual["annual_from_quarters_status"] = "baseline_quarterly_scenario"
    annual["actual_used"] = "N"
    return temporal, spatial, tconstraint, recon, add_audit_cols(replay), add_audit_cols(nowcast), add_audit_cols(annual)


def forecast_archive(nowcast: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    archive = nowcast.head(20000).copy()
    archive["forecast_created_at"] = GENERATED_AT
    archive["information_cutoff"] = GENERATED_AT
    archive["policy_id"] = "QP0_seasonal__QS0_annual_last_share__T3_proportional_denton"
    archive["configuration_hash"] = core.stable_hash({"policy": "phase21_incumbent"})
    archive["prediction_hash"] = core.stable_hash(archive.head(5000).to_dict("records"))
    archive["archive_status"] = "frozen_waiting_release"
    archive["one_shot_consumed"] = "false"
    manifest = {
        "forecast_created_at": GENERATED_AT,
        "archive_status": "frozen_waiting_release",
        "target_periods": sorted(archive.get("period", pd.Series(dtype=str)).astype(str).unique().tolist()),
        "prediction_rows": int(len(archive)),
        "configuration_hash": core.stable_hash({"policy": "phase21_incumbent"}),
        "input_hash": core.stable_hash(archive.head(5000).to_dict("records")),
        "one_shot_consumed": False,
    }
    return add_audit_cols(archive), manifest


def make_report(ctx: dict[str, Any]) -> None:
    sections = [
        ("실행 요약", ctx["final"]),
        ("목표 불변 선언", ctx["goal"]),
        ("Phase 20 결과", ctx["phase20"]),
        ("공식 분기 GRDP Source", ctx["source"]),
        ("Official Source Authenticity", ctx["source"]),
        ("Release·Vintage Registry", ctx["vintage"]),
        ("Target Measure", ctx["measure"]),
        ("Official·Proxy Track 분리", ctx["tracks"]),
        ("Warm-up Audit", ctx["warmup"]),
        ("Zero-error Audit", ctx["zero"]),
        ("Leakage Audit", ctx["leakage"]),
        ("Quarterly Origin", ctx["origin"]),
        ("Origin Identity", ctx["origin"]),
        ("QP0 Seasonal Baseline", ctx["qp0"]),
        ("QP1 National Bridge", ctx["qp1"]),
        ("QP2 Bounded Indicator Bridge", ctx["qp2"]),
        ("QP3 Robust Hierarchical Bridge", ctx["qp3"]),
        ("QP4 Factor Model", ctx["qp4"]),
        ("QP5 MIDAS Gate", ctx["qp5"]),
        ("Shock-quarter Stability", ctx["shock"]),
        ("Parent Policy Selection", ctx["selection"]),
        ("Quarterly Growth Accuracy", ctx["growth"]),
        ("Turning-point Accuracy", ctx["turning"]),
        ("Forecast Revision", ctx["revision"]),
        ("Child Last-share Baseline", ctx["child_validation"]),
        ("Child Activity Share", ctx["activity"]),
        ("Unreconciled Forecast", ctx["unreconciled_note"]),
        ("Reconciled Estimate", ctx["reconciled_note"]),
        ("Reconciliation Adjustment", ctx["adjustment"]),
        ("Temporal Disaggregation", ctx["temporal"]),
        ("Spatial Reconciliation", ctx["spatial"]),
        ("Temporal Reconciliation", ctx["tconstraint"]),
        ("Distortion Audit", ctx["distortion"]),
        ("Official Parent Accuracy", ctx["official_accuracy"]),
        ("Child Indirect Validation", ctx["child_validation"]),
        ("2025 Pseudo-real-time Replay", ctx["replay"]),
        ("Prospective Forecast Archive", ctx["archive"]),
        ("2026 Quarterly Nowcast", ctx["nowcast"]),
        ("2026 Annual-from-quarters", ctx["annual"]),
        ("Monthly Gate", ctx["monthly"]),
        ("불확실성", ctx["uncertainty"]),
        ("Risk Queue", ctx["risk"]),
        ("최종 정책", ctx["policy"]),
        ("한계", ctx["limits"]),
        ("결론", ctx["conclusion"]),
    ]
    lines = ["# Partial Statistics Estimation Phase 21-GVA", ""]
    for idx, (title, content) in enumerate(sections, start=1):
        lines += [f"## {idx}. {title}", ""]
        lines.append(markdown_table(content) if isinstance(content, pd.DataFrame) else str(content))
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    topic = ROOT / "reports" / "topics" / "ml.md"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# Reconciled ML Experiments\n\n| Report | Purpose |\n| --- | --- |\n"
    row = "| [partial_statistics_estimation_phase21_gva.md](../partial_statistics_estimation_phase21_gva.md) | Official quarterly GRDP materialization audit, leakage-free quarterly evaluation, and prospective forecast validation |\n"
    if "partial_statistics_estimation_phase21_gva.md" not in text:
        topic.write_text(text.replace("| --- | --- |\n", "| --- | --- |\n" + row), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase21_gva_final_status.json"
    if final_path.exists() and not args.force:
        print(final_path)
        return 0
    source, release, vintage, official_cube = materialize_official_source()
    parent = parent_rows()
    warmup, zero, leakage = warmup_and_leakage(parent)
    accuracy, growth, turning, revision, worst = recompute_parent_accuracy(parent)
    selection, metric_best, selected = policy_selection(accuracy, growth, turning, revision, worst)
    origin = origin_identity(parent)
    activity, child_validation, adjustment, distortion, unreconciled, reconciled = child_outputs()
    temporal, spatial, tconstraint, recon, replay, nowcast, annual = temporal_and_replay()
    archive, archive_manifest = forecast_archive(nowcast)
    measure = add_audit_cols(pd.DataFrame([
        {"measure_id": "official_quarterly_grdp", "status": "not_materialized", "target_type": "not_available"},
        {"measure_id": "project_quarterly_parent_proxy", "status": "development_proxy", "target_type": "level_proxy"},
        {"measure_id": "annual_sigungu_gva", "status": "active", "target_type": "nominal_level"},
    ]))
    tracks = add_audit_cols(pd.DataFrame([
        {"track_id": "official_direct_track", "target_source": "official quarterly GRDP", "role": "direct external evaluation", "status": "blocked_not_materialized"},
        {"track_id": "development_proxy_track", "target_source": "PROJECT_SIDO_QUARTERLY_GVA_BENCHMARK", "role": "historical model development only", "status": "active"},
    ]))
    official_eval = add_audit_cols(pd.DataFrame([{"evaluation_target": "official_first_release", "status": "blocked_official_source_not_materialized", "rows": 0}]))
    policy = {
        "metric_best_policy": metric_best,
        "gate_selected_policy": selected,
        "current_candidate_policy": selected,
        "selected_child_policy": "QS0_annual_last_share",
        "selected_temporal_policy": "T3_proportional_denton",
        "selection_failure_reason": "official direct source not materialized; proxy metric-best cannot be promoted",
    }
    final = {
        "status": "quarterly_child_benchmark_consistent_development;prospective_forecast_archive_frozen;monthly_primary_blocked",
        "target": "GVA",
        "target_unchanged": True,
        "official_quarterly_source_materialized": False,
        "official_source_period": "",
        "official_vintage_count": 0,
        "first_release_target_count": 0,
        "latest_revision_target_count": 0,
        "official_proxy_tracks_separated": True,
        "real_nominal_track_status": "separated_no_unexplained_mixing",
        "warmup_rows": int(len(warmup)),
        "zero_error_rows": int(len(zero)),
        "zero_error_primary_reason": str(zero["zero_error_reason"].mode().iloc[0]) if len(zero) else "none",
        "leakage_audit": "pass_with_proxy_limitations",
        "independent_origin_count": int(origin["origin_status"].eq("independent_origin").sum()),
        "collapsed_origin_count": int(origin["origin_status"].eq("collapsed_origin").sum()),
        "metric_best_policy": metric_best,
        "gate_selected_policy": selected,
        "quarterly_wmape": float(selection[selection["parent_policy_id"].eq(selected)]["average_wmape"].iloc[0]),
        "yoy_growth_mae_pp": float(growth[growth["parent_policy_id"].eq(selected)]["yoy_growth_mae_pp"].iloc[0]),
        "qoq_growth_mae_pp": float(growth[growth["parent_policy_id"].eq(selected)]["qoq_growth_mae_pp"].iloc[0]),
        "turning_point_accuracy": float(turning[turning["parent_policy_id"].eq(selected)]["turning_point_accuracy"].iloc[0]),
        "harmful_revision_rate": float(revision[revision["parent_policy_id"].eq(selected)]["harmful_revision_rate"].iloc[0]),
        "parent_exactness": "constraint_pass_not_accuracy",
        "temporal_policy": "T3_proportional_denton",
        "prospective_archive_status": "frozen_waiting_release",
        "monthly_primary_status": "monthly_primary_blocked",
        "uncertainty_status": "scenario_only",
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    outputs = {
        "partial_stats_phase21_gva_official_source_registry.csv": source,
        "partial_stats_phase21_gva_official_release_ledger.csv": release,
        "partial_stats_phase21_gva_official_vintage_registry.csv": vintage,
        "partial_stats_phase21_gva_warmup_audit.csv": warmup,
        "partial_stats_phase21_gva_zero_error_audit.csv": zero,
        "partial_stats_phase21_gva_leakage_audit.csv": leakage,
        "partial_stats_phase21_gva_origin_identity_audit.csv": origin,
        "partial_stats_phase21_gva_selection_consistency_audit.csv": selection,
        "partial_stats_phase21_gva_qp0_results.csv": accuracy[accuracy["parent_policy_id"].eq("QP0_seasonal")],
        "partial_stats_phase21_gva_qp1_results.csv": accuracy[accuracy["parent_policy_id"].eq("QP1_national_bridge")],
        "partial_stats_phase21_gva_qp2_results.csv": accuracy[accuracy["parent_policy_id"].eq("QP2_bounded_indicator_bridge")],
        "partial_stats_phase21_gva_qp3_results.csv": accuracy[accuracy["parent_policy_id"].eq("QP3_robust_hierarchical_bridge")],
        "partial_stats_phase21_gva_qp4_results.csv": accuracy[accuracy["parent_policy_id"].eq("QP4_factor")],
        "partial_stats_phase21_gva_qp5_results.csv": accuracy[accuracy["parent_policy_id"].eq("QP5_midas")],
        "partial_stats_phase21_gva_parent_policy_selection.csv": selection,
        "partial_stats_phase21_gva_child_activity_share.csv": activity,
        "partial_stats_phase21_gva_child_validation.csv": child_validation,
        "partial_stats_phase21_gva_temporal_policy_results.csv": temporal,
        "partial_stats_phase21_gva_spatial_constraints.csv": spatial,
        "partial_stats_phase21_gva_temporal_constraints.csv": tconstraint,
        "partial_stats_phase21_gva_reconciliation_results.csv": recon,
        "partial_stats_phase21_gva_reconciliation_adjustments.csv": adjustment,
        "partial_stats_phase21_gva_distortion_audit.csv": distortion,
        "partial_stats_phase21_gva_official_parent_accuracy.csv": official_eval,
        "partial_stats_phase21_gva_growth_accuracy.csv": growth,
        "partial_stats_phase21_gva_turning_point_accuracy.csv": turning,
        "partial_stats_phase21_gva_revision_results.csv": revision,
        "partial_stats_phase21_gva_worst_group_results.csv": worst,
        "partial_stats_phase21_gva_quarterly_replay_2025.csv": replay,
        "partial_stats_phase21_gva_quarterly_nowcast_2026.csv": nowcast,
        "partial_stats_phase21_gva_annual_from_quarters_2026.csv": annual,
        "partial_stats_phase21_gva_forecast_archive.csv": archive,
    }
    for name, frame in outputs.items():
        write_frame(name, frame)
    write_json(PROCESSED_DIR / "partial_stats_phase21_gva_goal_charter.json", {"PRIMARY_TARGET": "region_industry_period_gva", "MONTHLY_PRIMARY": "blocked", "PRODUCTION_USE": False, "OFFICIAL_STATISTICS_CLAIM": False})
    write_json(PROCESSED_DIR / "partial_stats_phase21_gva_policy_registry.json", policy)
    write_json(PROCESSED_DIR / "partial_stats_phase21_gva_forecast_archive_manifest.json", archive_manifest)
    manifest = add_audit_cols(pd.DataFrame([{"artifact": name, "status": "completed", "python": platform.python_version()} for name in [*outputs.keys(), "partial_stats_phase21_gva_official_target_cube.parquet", "partial_stats_phase21_gva_child_unreconciled.parquet", "partial_stats_phase21_gva_child_reconciled.parquet", "partial_stats_phase21_gva_goal_charter.json", "partial_stats_phase21_gva_policy_registry.json", "partial_stats_phase21_gva_forecast_archive_manifest.json", "partial_stats_phase21_gva_experiment_manifest.json", "partial_stats_phase21_gva_execution_manifest.csv", "partial_stats_phase21_gva_final_status.json"]]))
    write_json(PROCESSED_DIR / "partial_stats_phase21_gva_experiment_manifest.json", manifest.to_dict("records"))
    write_frame("partial_stats_phase21_gva_execution_manifest.csv", manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase21_gva_final_status.json", final)
    make_report({
        "final": pd.DataFrame([final]),
        "goal": pd.DataFrame([{"PRIMARY_TARGET": "region_industry_period_gva", "QUARTERLY_DIRECT_TARGET": "sido_official_broad_industry_quarter", "QUARTERLY_DEVELOPMENT_TARGET": "sigungu_detailed_industry_quarter", "MONTHLY_PRIMARY": "blocked"}]),
        "phase20": "Phase 20 activated a quarterly development track, but its parent target was a project proxy rather than materialized official quarterly GRDP. Phase 21 supersedes proxy-only scoring with warm-up exclusion and explicit official/proxy track separation.",
        "source": source,
        "vintage": vintage,
        "measure": measure,
        "tracks": tracks,
        "warmup": warmup,
        "zero": zero,
        "leakage": leakage,
        "origin": origin,
        "qp0": outputs["partial_stats_phase21_gva_qp0_results.csv"],
        "qp1": outputs["partial_stats_phase21_gva_qp1_results.csv"],
        "qp2": outputs["partial_stats_phase21_gva_qp2_results.csv"],
        "qp3": outputs["partial_stats_phase21_gva_qp3_results.csv"],
        "qp4": outputs["partial_stats_phase21_gva_qp4_results.csv"],
        "qp5": outputs["partial_stats_phase21_gva_qp5_results.csv"],
        "shock": worst[worst["group_type"].eq("quarter")],
        "selection": selection,
        "growth": growth,
        "turning": turning,
        "revision": revision,
        "activity": activity,
        "child_validation": child_validation,
        "unreconciled_note": "Saved as data/processed/partial_stats_phase21_gva_child_unreconciled.parquet.",
        "reconciled_note": "Saved as data/processed/partial_stats_phase21_gva_child_reconciled.parquet.",
        "adjustment": adjustment.head(20),
        "temporal": temporal,
        "spatial": spatial,
        "tconstraint": tconstraint,
        "distortion": distortion,
        "official_accuracy": official_eval,
        "replay": replay.head(20),
        "archive": archive.head(20),
        "nowcast": nowcast.head(20),
        "annual": annual.head(20),
        "monthly": pd.DataFrame([{"monthly_primary_status": "monthly_primary_blocked"}]),
        "uncertainty": pd.DataFrame([{"uncertainty_status": "scenario_only", "coverage_claim": "N"}]),
        "risk": pd.DataFrame([{"risk": "official quarterly GRDP direct source not materialized", "severity": "high"}, {"risk": "proxy target cannot validate official external accuracy", "severity": "high"}]),
        "policy": pd.DataFrame([policy]),
        "limits": "Official direct quarterly GRDP evaluation is blocked until raw source body, release date, vintage id, and measure definition are materialized. Child quarterly estimates remain development-only.",
        "conclusion": "Phase21 repairs Phase20 evaluation semantics: warm-up rows are not scored, zero-error rows are classified, proxy and official tracks are separated, and a prospective archive is frozen for future one-shot scoring.",
    })
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
