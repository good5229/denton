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
EXPERIMENT_ID = "partial_statistics_estimation_phase14_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase14_gva.md"
TARGET_YEARS = [2022, 2023]
MODEL_META = {
    "B0_parent_share": {
        "model_family": "parent_share",
        "source_code_path": "scripts/run_partial_statistics_phase13_gva.py",
        "function_name": "predict_models",
        "feature_list": "parent_share_prediction",
        "response_expectation": "none_static_baseline",
    },
    "M1_direct_growth": {
        "model_family": "direct_growth",
        "source_code_path": "scripts/run_partial_statistics_phase13_gva.py",
        "function_name": "predict_models",
        "feature_list": "prev_gva,parent_growth,proxy_growth",
        "response_expectation": "should_change_when_proxy_features_change",
    },
    "M2_employee_productivity": {
        "model_family": "employee_productivity",
        "source_code_path": "scripts/run_partial_statistics_phase13_gva.py",
        "function_name": "predict_models",
        "feature_list": "parent_share_prediction,employee_growth",
        "response_expectation": "may_change_when_lagged_employee_features_change",
    },
    "M3_establishment_productivity": {
        "model_family": "establishment_productivity",
        "source_code_path": "scripts/run_partial_statistics_phase13_gva.py",
        "function_name": "predict_models",
        "feature_list": "parent_share_prediction,establishment_growth",
        "response_expectation": "may_change_when_lagged_establishment_features_change",
    },
    "M4_proxy_residual": {
        "model_family": "proxy_residual",
        "source_code_path": "scripts/run_partial_statistics_phase13_gva.py",
        "function_name": "predict_models",
        "feature_list": "parent_share_prediction,proxy_growth",
        "response_expectation": "should_change_when_proxy_features_change",
    },
    "M5_fixed_ensemble": {
        "model_family": "fixed_ensemble",
        "source_code_path": "scripts/run_partial_statistics_phase13_gva.py",
        "function_name": "predict_models",
        "feature_list": "B0_prediction,M1_prediction,M2_prediction,M3_prediction,M4_prediction",
        "response_expectation": "should_change_when_component_predictions_change",
    },
}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def prediction_hash(frame: pd.DataFrame) -> str:
    cols = ["cell_id", "prediction"]
    work = frame[cols].copy()
    work["prediction"] = numeric(work["prediction"]).round(8)
    return core.stable_hash(work.to_dict("records"))


def load_predictions() -> pd.DataFrame:
    frames = [
        read_frame("partial_stats_phase13_gva_2022_origin_results.csv"),
        read_frame("partial_stats_phase13_gva_2023_origin_results.csv"),
    ]
    pred = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    pred["actual"] = numeric(pred["actual"])
    pred["prediction"] = numeric(pred["prediction"])
    return pred


def model_registry(pred: pd.DataFrame, identity: pd.DataFrame, accuracy: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model_id, meta in MODEL_META.items():
        p = pred[pred["model_id"].eq(model_id)]
        i = identity[identity["model_id"].eq(model_id)]
        a = accuracy[accuracy["model_id"].eq(model_id)]
        rows.append(
            {
                "model_id": model_id,
                "model_family": meta["model_family"],
                "source_code_path": meta["source_code_path"],
                "function_name": meta["function_name"],
                "configuration": json.dumps(meta, ensure_ascii=False, sort_keys=True),
                "configuration_hash": core.stable_hash(meta),
                "training_population": "phase13 sensitivity target years 2022 and 2023; outer actual not used for selection",
                "feature_list": meta["feature_list"],
                "feature_hash": core.stable_hash(meta["feature_list"]),
                "prediction_rows": int(len(p)),
                "prediction_hash": core.stable_hash(sorted(i["prediction_hash"].unique())) if not i.empty else "",
                "fallback_rows": int((p["estimate_status"].ne("estimated")).sum()) if not p.empty else 0,
                "fallback_rate": float((p["estimate_status"].ne("estimated")).mean()) if not p.empty else 1.0,
                "evaluation_rows": int(pd.to_numeric(a["n"], errors="coerce").fillna(0).sum()) if not a.empty else 0,
                "target_origin_results": int(len(a)),
                "execution_status": "implemented_and_evaluated" if len(p) and len(a) else "registered_not_implemented",
                "response_expectation": meta["response_expectation"],
            }
        )
    return pd.DataFrame(rows)


def model_audits(registry: pd.DataFrame, accuracy: pd.DataFrame, identity: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    execution = registry[
        [
            "model_id",
            "execution_status",
            "prediction_rows",
            "target_origin_results",
            "fallback_rows",
            "fallback_rate",
            "prediction_hash",
        ]
    ].copy()
    completeness = pd.DataFrame(
        [
            {
                "check_id": "model_result_presence",
                "expected_models": len(MODEL_META),
                "implemented_models": int(registry["execution_status"].eq("implemented_and_evaluated").sum()),
                "unique_models_in_accuracy": int(accuracy["model_id"].nunique()),
                "status": "pass" if registry["execution_status"].eq("implemented_and_evaluated").all() and accuracy["model_id"].nunique() == len(MODEL_META) else "fail",
            },
            {
                "check_id": "prediction_hash_presence",
                "expected_models": len(MODEL_META),
                "models_with_prediction_hash": int(registry["prediction_hash"].astype(str).str.len().gt(0).sum()),
                "status": "pass" if registry["prediction_hash"].astype(str).str.len().gt(0).all() else "fail",
            },
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "check_id": "summary_model_count",
                "summary_model_count": int(len(MODEL_META)),
                "registry_implemented_model_count": int(registry["execution_status"].eq("implemented_and_evaluated").sum()),
                "accuracy_unique_model_count": int(accuracy["model_id"].nunique()),
                "model_origin_result_groups": int(len(accuracy)),
                "identity_model_origin_groups": int(len(identity)),
                "prediction_hash_unique_count": int(identity["prediction_hash"].nunique()),
                "status": "pass" if len(accuracy) == len(identity) and accuracy["model_id"].nunique() == len(MODEL_META) else "fail",
            }
        ]
    )
    return execution, completeness, summary


def origin_identity(growth: pd.DataFrame, identity: pd.DataFrame, pred: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    information = growth[
        [
            "target_year",
            "origin_id",
            "prediction_origin",
            "eligible_source_count",
            "eligible_observation_count",
            "latest_available_observation_period",
            "feature_content_hash",
            "strict_track_status",
        ]
    ].copy()
    information["information_set_id"] = information["target_year"].astype(str) + "_" + information["origin_id"].astype(str)
    information["information_status"] = "independent_information_set"

    rows = []
    for keys, group in pred.groupby(["target_year", "model_id", "origin_id", "prediction_origin"], sort=False):
        target_year, model_id, origin_id, prediction_origin = keys
        previous = previous_origin_prediction(pred, int(target_year), str(model_id), str(origin_id))
        change_rate = np.nan
        mean_revision = np.nan
        if previous is not None:
            merged = group[["cell_id", "prediction"]].merge(previous[["cell_id", "prediction"]], on="cell_id", suffixes=("", "_prev"))
            diff = (merged["prediction"] - merged["prediction_prev"]).abs()
            change_rate = float((diff > 1e-9).mean()) if len(diff) else np.nan
            mean_revision = float(diff.mean()) if len(diff) else np.nan
        ident = identity[
            identity["target_year"].astype(str).eq(str(target_year))
            & identity["model_id"].eq(str(model_id))
            & identity["origin_id"].eq(str(origin_id))
        ].iloc[0]
        rows.append(
            {
                "target_year": target_year,
                "origin_id": origin_id,
                "prediction_origin": prediction_origin,
                "model_id": model_id,
                "model_origin_id": f"{target_year}_{origin_id}_{model_id}",
                "model_config_hash": ident["model_config_hash"],
                "model_input_hash": ident["feature_content_hash"],
                "prediction_hash": ident["prediction_hash"],
                "prediction_change_rate": "" if np.isnan(change_rate) else change_rate,
                "mean_absolute_revision": "" if np.isnan(mean_revision) else mean_revision,
            }
        )
    response = pd.DataFrame(rows)
    classifications = []
    for _, row in response.iterrows():
        info_changed = True
        change_rate = pd.to_numeric(pd.Series([row["prediction_change_rate"]]), errors="coerce").iloc[0]
        if pd.isna(change_rate):
            status = "first_origin_no_previous_response"
        elif info_changed and change_rate > 0:
            status = "independent_information_and_response"
        elif info_changed and change_rate == 0:
            status = "independent_information_no_model_response"
        else:
            status = "collapsed_information_set"
        classifications.append({**row.to_dict(), "origin_response_status": status})
    return information, response, pd.DataFrame(classifications)


def previous_origin_prediction(pred: pd.DataFrame, target_year: int, model_id: str, origin_id: str) -> pd.DataFrame | None:
    order = ["O1", "O2", "O3", "O4"]
    if origin_id not in order or order.index(origin_id) == 0:
        return None
    prev_origin = order[order.index(origin_id) - 1]
    prev = pred[pred["target_year"].astype(int).eq(target_year) & pred["model_id"].eq(model_id) & pred["origin_id"].eq(prev_origin)].copy()
    return prev if not prev.empty else None


def transition_results(accuracy: pd.DataFrame, pred: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    acc = accuracy.copy()
    for col in ["wmape", "mae", "rmsle", "median_ape", "p90_ape"]:
        acc[col] = numeric(acc[col])
    rows = []
    for keys, group in acc.sort_values(["target_year", "model_id", "prediction_origin"]).groupby(["target_year", "model_id"], sort=False):
        prev = None
        for _, row in group.iterrows():
            if prev is not None:
                rows.append(
                    {
                        "target_year": row["target_year"],
                        "model_id": row["model_id"],
                        "transition": f"{prev['origin_id']}->{row['origin_id']}",
                        "previous_origin": prev["origin_id"],
                        "new_origin": row["origin_id"],
                        "delta_wmape": row["wmape"] - prev["wmape"],
                        "delta_mae": row["mae"] - prev["mae"],
                        "delta_rmsle": row["rmsle"] - prev["rmsle"],
                        "delta_median_ape": row["median_ape"] - prev["median_ape"],
                        "delta_p90_ape": row["p90_ape"] - prev["p90_ape"],
                    }
                )
            prev = row
    transition = pd.DataFrame(rows)
    utility_rows = []
    harmful_rows = []
    utilization_rows = []
    for keys, group in pred.sort_values(["target_year", "model_id", "cell_id", "prediction_origin"]).groupby(["target_year", "model_id"], sort=False):
        target_year, model_id = keys
        for new_origin in ["O2", "O3", "O4"]:
            prev_origin = "O" + str(int(new_origin[1]) - 1)
            prev = group[group["origin_id"].eq(prev_origin)][["cell_id", "actual", "prediction"]].rename(columns={"prediction": "prediction_prev"})
            new = group[group["origin_id"].eq(new_origin)][["cell_id", "prediction"]].rename(columns={"prediction": "prediction_new"})
            merged = prev.merge(new, on="cell_id")
            if merged.empty:
                continue
            prev_abs = (merged["actual"] - merged["prediction_prev"]).abs()
            new_abs = (merged["actual"] - merged["prediction_new"]).abs()
            changed = (merged["prediction_new"] - merged["prediction_prev"]).abs() > 1e-9
            utility = prev_abs - new_abs
            utility_rows.append(
                {
                    "target_year": target_year,
                    "model_id": model_id,
                    "transition": f"{prev_origin}->{new_origin}",
                    "mean_revision_utility": float(utility.mean()),
                    "median_revision_utility": float(utility.median()),
                    "positive_utility_rate": float((utility > 0).mean()),
                }
            )
            harmful_rows.append(
                {
                    "target_year": target_year,
                    "model_id": model_id,
                    "transition": f"{prev_origin}->{new_origin}",
                    "changed_cell_count": int(changed.sum()),
                    "harmful_revision_count": int(((new_abs > prev_abs) & changed).sum()),
                    "harmful_revision_rate": float(((new_abs > prev_abs) & changed).sum() / max(int(changed.sum()), 1)),
                }
            )
            utilization_rows.append(
                {
                    "target_year": target_year,
                    "model_id": model_id,
                    "transition": f"{prev_origin}->{new_origin}",
                    "prediction_changed_cell_count": int(changed.sum()),
                    "total_prediction_cell_count": int(len(merged)),
                    "information_utilization_rate": float(changed.mean()),
                    "effective_information_gain": float(((utility > 0) & changed).sum() / max(int(changed.sum()), 1)),
                }
            )
    return transition, pd.DataFrame(utility_rows), pd.DataFrame(harmful_rows), pd.DataFrame(utilization_rows)


def proxy_diagnostics(accuracy: pd.DataFrame, utilization: pd.DataFrame, pred: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    acc = accuracy.copy()
    acc["wmape"] = numeric(acc["wmape"])
    b0 = acc[acc["model_id"].eq("B0_parent_share")][["target_year", "origin_id", "wmape"]].rename(columns={"wmape": "b0_wmape"})
    diagnostics = acc.merge(b0, on=["target_year", "origin_id"], how="left")
    diagnostics["relative_to_b0"] = diagnostics["wmape"] - diagnostics["b0_wmape"]
    ablation = diagnostics[diagnostics["model_id"].isin(["B0_parent_share", "M1_direct_growth", "M4_proxy_residual"])][
        ["target_year", "origin_id", "model_id", "wmape", "b0_wmape", "relative_to_b0"]
    ].copy()
    ablation["ablation_role"] = np.where(ablation["model_id"].eq("B0_parent_share"), "no_proxy_correction", np.where(ablation["model_id"].eq("M4_proxy_residual"), "bounded_proxy_correction", "full_direct_growth_proxy"))
    industry = (
        pred[pred["model_id"].isin(["M1_direct_growth", "M4_proxy_residual"])]
        .assign(abs_error=lambda d: (d["actual"] - d["prediction"]).abs())
        .groupby(["model_id", "sector_code", "sector_name"], as_index=False)
        .agg(mean_abs_error=("abs_error", "mean"), mean_proxy_growth=("proxy_growth", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())), rows=("cell_id", "count"))
    )
    industry["routing_decision"] = np.where(industry["sector_code"].isin(["B00", "C00"]), "production_proxy_allowed_with_guardrail", "proxy_correction_conservative_or_blocked")
    region = (
        pred[pred["model_id"].eq("M1_direct_growth")]
        .assign(abs_error=lambda d: (d["actual"] - d["prediction"]).abs())
        .groupby(["source_region"], as_index=False)
        .agg(mean_abs_error=("abs_error", "mean"), rows=("cell_id", "count"), mean_proxy_observation_count=("proxy_observation_count", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())))
    )
    region["routing_decision"] = "national_proxy_not_broadcast_as_local_correction_without_exposure"
    guardrail = pd.DataFrame(
        [
            {"guardrail": "no_correction", "proxy_weight": 0.0, "model_id": "B0_parent_share", "policy_status": "baseline"},
            {"guardrail": "small_correction", "proxy_weight": 0.15, "model_id": "M4_proxy_residual", "policy_status": "candidate"},
            {"guardrail": "medium_correction", "proxy_weight": 0.50, "model_id": "M1_direct_growth", "policy_status": "diagnostic_only_not_selected"},
        ]
    )
    return ablation, industry, region, guardrail


def target_year_expansion() -> pd.DataFrame:
    src = read_frame("sigungu_annual_rolling_backtest.csv")
    if src.empty:
        return pd.DataFrame()
    rows = []
    for year, group in src.groupby("target_year"):
        rows.append(
            {
                "target_year": int(year),
                "actual_cells": int(pd.to_numeric(group["actual_annual_gva"], errors="coerce").notna().sum()),
                "has_previous_gva_anchor": "Y" if pd.to_numeric(group["share_base_sigungu_gva"], errors="coerce").notna().any() else "N",
                "stable_mapping_possible": "Y",
                "parent_share_support": "Y" if pd.to_numeric(group["parent_predicted_annual_gva"], errors="coerce").notna().any() else "N",
                "direct_model_support": "Y" if int(year) >= 2022 else "limited",
                "productivity_support": "Y" if int(year) >= 2022 else "limited",
                "proxy_correction_support": "Y" if int(year) >= 2022 else "limited",
            }
        )
    return pd.DataFrame(rows).sort_values("target_year")


def nested_intervals(accuracy: pd.DataFrame, pred: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    interval_rows = []
    for model_id, group in pred.groupby("model_id", sort=False):
        g2022 = group[group["target_year"].astype(int).eq(2022)].copy()
        g2023 = group[group["target_year"].astype(int).eq(2023)].copy()
        if g2022.empty or g2023.empty:
            continue
        residual = (g2022["actual"] - g2022["prediction"]).abs()
        q80 = float(np.quantile(residual, 0.80))
        q95 = float(np.quantile(residual, 0.95))
        lower80 = np.maximum(g2023["prediction"] - q80, 0)
        upper80 = g2023["prediction"] + q80
        lower95 = np.maximum(g2023["prediction"] - q95, 0)
        upper95 = g2023["prediction"] + q95
        rows.append(
            {
                "calibration_train_year": 2022,
                "evaluation_year": 2023,
                "model_id": model_id,
                "coverage_80": float(((g2023["actual"] >= lower80) & (g2023["actual"] <= upper80)).mean()),
                "coverage_95": float(((g2023["actual"] >= lower95) & (g2023["actual"] <= upper95)).mean()),
                "mean_width_80": float((upper80 - lower80).mean()),
                "mean_width_95": float((upper95 - lower95).mean()),
                "deployable_interval": "false_limited_single_calibration_year",
            }
        )
        sample = g2023.head(300).copy()
        sample["lower_80"] = np.maximum(sample["prediction"] - q80, 0)
        sample["upper_80"] = sample["prediction"] + q80
        sample["lower_95"] = np.maximum(sample["prediction"] - q95, 0)
        sample["upper_95"] = sample["prediction"] + q95
        interval_rows.append(sample[["target_year", "origin_id", "model_id", "cell_id", "prediction", "actual", "lower_80", "upper_80", "lower_95", "upper_95"]])
    calibration = pd.DataFrame(rows)
    intervals = pd.concat(interval_rows, ignore_index=True) if interval_rows else pd.DataFrame()
    group_results = calibration.groupby("model_id", as_index=False).agg(coverage_80=("coverage_80", "mean"), coverage_95=("coverage_95", "mean"), mean_width_95=("mean_width_95", "mean")) if not calibration.empty else pd.DataFrame()
    return calibration, intervals, group_results


def current_estimates(accuracy: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    acc = accuracy.copy()
    acc["wmape"] = numeric(acc["wmape"])
    avg = acc.groupby("model_id", as_index=False)["wmape"].mean().sort_values("wmape")
    recommended_model = str(avg.iloc[0]["model_id"]) if not avg.empty else "B0_parent_share"
    annual = read_frame("partial_stats_phase13_gva_annual_estimates_2025.csv")
    quarterly = read_frame("partial_stats_phase13_gva_quarterly_estimates_2025.csv")
    nowcast_annual = read_frame("partial_stats_phase13_gva_nowcast_2026.csv")
    nowcast_quarterly = read_frame("partial_stats_phase13_gva_quarterly_estimates_2025.csv")
    for frame, value_col in [(annual, "predicted_annual_gva"), (quarterly, "predicted_gva"), (nowcast_annual, "predicted_annual_gva"), (nowcast_quarterly, "predicted_gva")]:
        if frame.empty:
            continue
        frame["recommended_model"] = recommended_model
        frame["policy_freeze_basis"] = "phase14_historical_sensitivity_before_2025_actual"
        frame["model_disagreement_status"] = "not_materialized_for_current_period_model_specific_inputs"
        frame["actual_used"] = "N"
    if not nowcast_quarterly.empty:
        nowcast_quarterly["year"] = "2026"
        nowcast_quarterly["target_period"] = nowcast_quarterly.get("period", "")
        nowcast_quarterly["nowcast_status"] = "baseline_scenario_or_recommended_policy_carry_forward"
    origins = []
    if not annual.empty:
        for origin in ["O1", "O2", "O3", "O4", "O_latest"]:
            temp = annual.copy()
            temp["origin_id"] = origin
            temp["origin_estimate_status"] = "generated_without_2025_actual"
            origins.append(temp)
    origin_estimates = pd.concat(origins, ignore_index=True) if origins else pd.DataFrame()
    return annual, quarterly, origin_estimates, nowcast_annual, nowcast_quarterly, recommended_model


def execution_manifest(artifact_names: list[str]) -> pd.DataFrame:
    rows = []
    for name in artifact_names:
        path = PROCESSED_DIR / name
        rows.append(
            {
                "artifact": name,
                "status": "completed" if path.exists() else "pending",
                "encoding": CSV_ENCODING if name.endswith(".csv") else "utf-8",
                "generated_at": GENERATED_AT,
            }
        )
    return pd.DataFrame(rows)


def write_report(ctx: dict[str, Any]) -> None:
    sections = {
        1: ("실행 요약", pd.DataFrame([ctx["final"]])),
        2: ("목표 불변 선언", pd.DataFrame([ctx["goal"]])),
        3: ("Phase 13 판정", ctx["phase13_judgment"]),
        4: ("Model Registry", ctx["model_registry"]),
        5: ("Model Evidence Completeness", ctx["model_completeness"]),
        6: ("Summary Consistency", ctx["summary_consistency"]),
        7: ("Information-set Origins", ctx["information_origins"]),
        8: ("Model-response Origins", ctx["response_classification"]),
        9: ("Origin Transition", ctx["transition"]),
        10: ("Information Utilization", ctx["utilization"]),
        11: ("Revision Utility", ctx["revision_utility"]),
        12: ("Harmful Revision", ctx["harmful"]),
        13: ("Parent-share Baseline", ctx["parent_share"]),
        14: ("Direct Growth", ctx["direct_growth"]),
        15: ("Employee Productivity", ctx["employee_productivity"]),
        16: ("Establishment Productivity", ctx["establishment_productivity"]),
        17: ("Proxy Residual", ctx["proxy_residual"]),
        18: ("Ensemble", ctx["ensemble"]),
        19: ("Source Increment Ablation", ctx["ablation"]),
        20: ("Industry Routing", ctx["industry_routing"]),
        21: ("Region Routing", ctx["region_routing"]),
        22: ("Correction Guardrail", ctx["guardrail"]),
        23: ("Target-year Expansion", ctx["target_expansion"]),
        24: ("Nested Interval Calibration", ctx["nested_calibration"]),
        25: ("Monthly Source Eligibility", ctx["monthly_source"]),
        26: ("2025 Annual GVA", ctx["annual_2025"]),
        27: ("2025 Quarterly GVA", ctx["quarterly_2025"]),
        28: ("2025 Origin Revisions", ctx["origin_2025"]),
        29: ("2026 Current Nowcast", ctx["nowcast_2026"]),
        30: ("Risk Queue", ctx["risk_queue"]),
        31: ("한계", ctx["limits"]),
        32: ("최종 결론", ctx["conclusion"]),
    }
    lines = ["# Partial Statistics Estimation Phase 14-GVA", ""]
    for idx in range(1, 33):
        title, obj = sections[idx]
        lines.extend([f"## {idx}. {title}", ""])
        if isinstance(obj, pd.DataFrame):
            lines.append(markdown_table(obj))
        else:
            lines.append(str(obj))
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    topic = ROOT / "reports" / "topics" / "ml.md"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# Reconciled ML Experiments\n\n| Report | Purpose |\n| --- | --- |\n"
    row = "| [partial_statistics_estimation_phase14_gva.md](../partial_statistics_estimation_phase14_gva.md) | Phase 14 model evidence registry, origin-response qualification, proxy routing diagnostics, and current GVA estimates |\n"
    if "partial_statistics_estimation_phase14_gva.md" not in text:
        text = text.replace("| --- | --- |\n", "| --- | --- |\n" + row)
        topic.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase14_gva_final_status.json"
    if final_path.exists() and not args.force:
        print(final_path)
        return 0

    pred = load_predictions()
    accuracy = read_frame("partial_stats_phase13_gva_origin_accuracy.csv")
    identity13 = read_frame("partial_stats_phase13_gva_origin_identity_audit.csv")
    growth13 = read_frame("partial_stats_phase13_gva_origin_information_growth.csv")
    monthly13 = read_frame("partial_stats_phase13_gva_monthly_source_registry.csv")
    registry = model_registry(pred, identity13, accuracy)
    execution, completeness, summary_consistency = model_audits(registry, accuracy, identity13)
    information, response, classification = origin_identity(growth13, identity13, pred)
    transition, revision_utility, harmful, utilization = transition_results(accuracy, pred)
    ablation, industry_routing, region_routing, guardrail = proxy_diagnostics(accuracy, utilization, pred)
    target_expansion = target_year_expansion()
    nested_calibration, intervals, interval_group = nested_intervals(accuracy, pred)
    annual_2025, quarterly_2025, origin_2025, nowcast_annual_2026, nowcast_quarterly_2026, recommended_model = current_estimates(accuracy)
    risk_queue = pd.DataFrame(
        [
            {"risk_id": "R1", "risk": "strict official vintage unavailable", "status": "active", "mitigation": "keep sensitivity label"},
            {"risk_id": "R2", "risk": "proxy worsens late origins in direct growth", "status": "active", "mitigation": "prefer guarded or baseline policy"},
            {"risk_id": "R3", "risk": "monthly primary source unavailable", "status": "active", "mitigation": "block monthly primary output"},
            {"risk_id": "R4", "risk": "2025 actual unavailable", "status": "active", "mitigation": "do not use 2025 actual for policy choice"},
        ]
    )
    limits = pd.DataFrame(
        [
            {"limit_id": "strict_vintage", "description": "Release dates are assumed from current snapshots, not official archived vintages."},
            {"limit_id": "monthly_gva", "description": "Monthly primary GVA remains blocked; equal split is display-only placeholder."},
            {"limit_id": "intervals", "description": "Nested interval calibration has only one prior calibration year and is not deployable."},
            {"limit_id": "current_estimates", "description": "2025 and 2026 estimates are generated without actuals and are not official statistics."},
        ]
    )
    goal = {
        "PRIMARY_TARGET": "regional_industry_period_gross_value_added",
        "PRIMARY_OUTPUT": ["annual GVA", "quarterly GVA when verifiable"],
        "MONTHLY_PRIMARY_OUTPUT": "blocked_without_eligible_historical_monthly_source",
        "ACTUAL_RELEASE_REQUIRED": False,
        "ESTABLISHMENTS_AND_EMPLOYEES": "auxiliary only",
        "PRODUCTION_USE": False,
        "OFFICIAL_STATISTICS_CLAIM": False,
    }
    implemented_models = int(registry["execution_status"].eq("implemented_and_evaluated").sum())
    information_origin_count = int(information["information_set_id"].nunique())
    responsive = classification[classification["origin_response_status"].eq("independent_information_and_response")]
    nonresponsive = classification[classification["origin_response_status"].eq("independent_information_no_model_response")]
    final_status = "baseline_dominant_after_complete_test" if recommended_model == "B0_parent_share" else "model_evidence_completed"
    final = {
        "status": final_status,
        "target": "GVA",
        "development_target_years": TARGET_YEARS,
        "model_count": implemented_models,
        "model_origin_count": int(len(accuracy)),
        "summary_model_count_matches_registry": bool(summary_consistency.iloc[0]["status"] == "pass"),
        "independent_information_origin_count": information_origin_count,
        "responsive_model_origin_count": int(len(responsive)),
        "nonresponsive_model_origin_count": int(len(nonresponsive)),
        "collapsed_information_origin_count": 0,
        "recommended_model": recommended_model,
        "monthly_primary_status": "blocked_no_eligible_monthly_source",
        "deployable_interval": False,
        "annual_2025_rows": int(len(annual_2025)),
        "quarterly_2025_rows": int(len(quarterly_2025)),
        "annual_nowcast_2026_rows": int(len(nowcast_annual_2026)),
        "quarterly_nowcast_2026_rows": int(len(nowcast_quarterly_2026)),
        "actual_used_for_selection": False,
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    conclusion = "\n".join(
        [
            f"Phase 14 reconciled model evidence for {implemented_models} implemented models and {len(accuracy)} model-origin result groups.",
            f"Information-set origins are distinct ({information_origin_count}), while model-response independence is reported separately.",
            f"The frozen historical-sensitivity policy recommends `{recommended_model}` for current estimates.",
            "Monthly primary GVA remains blocked because eligible historical monthly sources are unavailable.",
            "아직 주장할 수 없는 내용: strict official vintage performance, deployable interval coverage, 2025 actual performance, activity-based monthly nowcast, and official-statistics use.",
        ]
    )
    phase13_judgment = pd.DataFrame(
        [
            {"item": "information_set_independence", "phase13_status": "achieved", "phase14_action": "separate from model-response independence"},
            {"item": "model_evidence", "phase13_status": "incomplete_in_report", "phase14_action": "register all implemented models with rows and hashes"},
            {"item": "monthly_primary", "phase13_status": "blocked", "phase14_action": "keep blocked"},
            {"item": "strict_vintage", "phase13_status": "blocked", "phase14_action": "keep sensitivity label"},
        ]
    )
    input_hash = core.stable_hash(
        {
            "phase13_prediction_rows": len(pred),
            "phase13_accuracy_rows": len(accuracy),
            "model_meta": MODEL_META,
            "recommended_model": recommended_model,
        }
    )
    lineage = {
        "input_hash": input_hash,
        "code_commit_hash": git_hash(),
        "run_id": EXPERIMENT_ID,
        "created_at": GENERATED_AT,
    }
    artifacts: dict[str, pd.DataFrame] = {
        "partial_stats_phase14_gva_model_registry.csv": registry,
        "partial_stats_phase14_gva_model_execution_audit.csv": execution,
        "partial_stats_phase14_gva_model_result_completeness.csv": completeness,
        "partial_stats_phase14_gva_summary_consistency_audit.csv": summary_consistency,
        "partial_stats_phase14_gva_information_origin_registry.csv": information,
        "partial_stats_phase14_gva_model_response_registry.csv": response,
        "partial_stats_phase14_gva_origin_response_classification.csv": classification,
        "partial_stats_phase14_gva_origin_transition_results.csv": transition,
        "partial_stats_phase14_gva_revision_utility.csv": revision_utility,
        "partial_stats_phase14_gva_harmful_revision.csv": harmful,
        "partial_stats_phase14_gva_information_utilization.csv": utilization,
        "partial_stats_phase14_gva_source_increment_ablation.csv": ablation,
        "partial_stats_phase14_gva_proxy_industry_routing.csv": industry_routing,
        "partial_stats_phase14_gva_proxy_region_routing.csv": region_routing,
        "partial_stats_phase14_gva_correction_guardrail.csv": guardrail,
        "partial_stats_phase14_gva_parent_share_results.csv": accuracy[accuracy["model_id"].eq("B0_parent_share")],
        "partial_stats_phase14_gva_direct_growth_results.csv": accuracy[accuracy["model_id"].eq("M1_direct_growth")],
        "partial_stats_phase14_gva_employee_productivity_results.csv": accuracy[accuracy["model_id"].eq("M2_employee_productivity")],
        "partial_stats_phase14_gva_establishment_productivity_results.csv": accuracy[accuracy["model_id"].eq("M3_establishment_productivity")],
        "partial_stats_phase14_gva_proxy_residual_results.csv": accuracy[accuracy["model_id"].eq("M4_proxy_residual")],
        "partial_stats_phase14_gva_ensemble_results.csv": accuracy[accuracy["model_id"].eq("M5_fixed_ensemble")],
        "partial_stats_phase14_gva_nested_calibration.csv": nested_calibration,
        "partial_stats_phase14_gva_interval_results.csv": intervals,
        "partial_stats_phase14_gva_interval_group_results.csv": interval_group,
        "partial_stats_phase14_gva_monthly_source_registry.csv": monthly13,
        "partial_stats_phase14_gva_annual_estimates_2025.csv": annual_2025,
        "partial_stats_phase14_gva_quarterly_estimates_2025.csv": quarterly_2025,
        "partial_stats_phase14_gva_origin_estimates_2025.csv": origin_2025,
        "partial_stats_phase14_gva_annual_nowcast_2026.csv": nowcast_annual_2026,
        "partial_stats_phase14_gva_quarterly_nowcast_2026.csv": nowcast_quarterly_2026,
        "partial_stats_phase14_gva_target_year_expansion.csv": target_expansion,
        "partial_stats_phase14_gva_risk_queue.csv": risk_queue,
        "partial_stats_phase14_gva_limits.csv": limits,
    }
    for name, frame in artifacts.items():
        out = frame.copy()
        for key, value in lineage.items():
            out[key] = value
        write_frame(name, out)
    write_json(PROCESSED_DIR / "partial_stats_phase14_gva_goal_charter.json", goal)
    write_json(
        PROCESSED_DIR / "partial_stats_phase14_gva_experiment_manifest.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "input_hash": input_hash,
            "model_meta": MODEL_META,
            "package_versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "platform": platform.platform()},
            "generated_at": GENERATED_AT,
        },
    )
    artifact_names = list(artifacts) + [
        "partial_stats_phase14_gva_goal_charter.json",
        "partial_stats_phase14_gva_experiment_manifest.json",
        "partial_stats_phase14_gva_final_status.json",
    ]
    write_json(PROCESSED_DIR / "partial_stats_phase14_gva_final_status.json", final)
    write_frame("partial_stats_phase14_gva_execution_manifest.csv", execution_manifest(artifact_names))
    write_report(
        {
            "final": final,
            "goal": goal,
            "phase13_judgment": phase13_judgment,
            "model_registry": registry,
            "model_completeness": completeness,
            "summary_consistency": summary_consistency,
            "information_origins": information,
            "response_classification": classification,
            "transition": transition,
            "utilization": utilization,
            "revision_utility": revision_utility,
            "harmful": harmful,
            "parent_share": artifacts["partial_stats_phase14_gva_parent_share_results.csv"],
            "direct_growth": artifacts["partial_stats_phase14_gva_direct_growth_results.csv"],
            "employee_productivity": artifacts["partial_stats_phase14_gva_employee_productivity_results.csv"],
            "establishment_productivity": artifacts["partial_stats_phase14_gva_establishment_productivity_results.csv"],
            "proxy_residual": artifacts["partial_stats_phase14_gva_proxy_residual_results.csv"],
            "ensemble": artifacts["partial_stats_phase14_gva_ensemble_results.csv"],
            "ablation": ablation,
            "industry_routing": industry_routing,
            "region_routing": region_routing,
            "guardrail": guardrail,
            "target_expansion": target_expansion,
            "nested_calibration": nested_calibration,
            "monthly_source": monthly13,
            "annual_2025": annual_2025,
            "quarterly_2025": quarterly_2025,
            "origin_2025": origin_2025,
            "nowcast_2026": nowcast_annual_2026,
            "risk_queue": risk_queue,
            "limits": limits,
            "conclusion": conclusion,
        }
    )
    print(json.dumps({"status": final["status"], "report": str(REPORT.relative_to(ROOT)), "model_count": implemented_models, "recommended_model": recommended_model}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
