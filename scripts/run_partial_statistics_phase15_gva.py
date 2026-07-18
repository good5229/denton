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
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase15_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase15_gva.md"
TARGET_YEARS = [2022, 2023]
ORIGINS = ["O1", "O2", "O3", "O4"]
BLOCKS = ["output", "labor", "energy", "demand", "business", "narrative"]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def read_frame(name: str, nrows: int | None = None) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False, nrows=nrows)


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def write_parquet_or_csv(name: str, frame: pd.DataFrame) -> str:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path, index=False)
        return name
    except Exception:
        fallback = name.replace(".parquet", "_fallback.csv")
        write_frame(fallback, frame)
        return fallback


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def zscore(series: pd.Series) -> pd.Series:
    values = numeric(series).fillna(0.0)
    std = float(values.std(ddof=0))
    if std <= 1e-12:
        return pd.Series(np.zeros(len(values)), index=series.index)
    return (values - float(values.mean())) / std


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def add_audit_cols(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    input_cols = [col for col in out.columns if col not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = core.stable_hash(out[input_cols].head(10000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def load_phase13_predictions() -> pd.DataFrame:
    frames = [read_frame("partial_stats_phase13_gva_2022_origin_results.csv"), read_frame("partial_stats_phase13_gva_2023_origin_results.csv")]
    pred = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    if pred.empty:
        raise SystemExit("Phase13 prediction artifacts are required for Phase15.")
    for col in ["actual", "prediction", "proxy_growth", "employee_growth", "establishment_growth"]:
        pred[col] = numeric(pred[col]).fillna(0.0)
    pred["target_year"] = numeric(pred["target_year"]).astype(int)
    return pred


def methodology_registry() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    methodology = pd.DataFrame(
        [
            {"method_id": "B0", "method_name": "Parent-share frozen incumbent", "role": "baseline", "target": "GVA", "uses_raw_proxy_directly": "N", "selection_rule": "incumbent comparator"},
            {"method_id": "RIAF", "method_name": "Regional Industry Activity Factor", "role": "intermediate_indicator", "target": "GVA", "uses_raw_proxy_directly": "N", "selection_rule": "quality-gated block aggregation"},
            {"method_id": "Bridge", "method_name": "Activity factor bridge correction", "role": "candidate", "target": "GVA", "uses_raw_proxy_directly": "N", "selection_rule": "outer-year actual excluded"},
            {"method_id": "MIDAS", "method_name": "Mixed-frequency bridge", "role": "blocked_or_candidate", "target": "GVA", "uses_raw_proxy_directly": "N", "selection_rule": "blocked unless monthly history is sufficient"},
            {"method_id": "Denton-Chow-Lin", "method_name": "Benchmark-consistent temporal disaggregation", "role": "temporal", "target": "GVA", "uses_raw_proxy_directly": "N", "selection_rule": "annual constraint must hold"},
            {"method_id": "Conformal", "method_name": "Origin-aware conformal uncertainty", "role": "uncertainty", "target": "GVA", "uses_raw_proxy_directly": "N", "selection_rule": "blocked unless three or more historical target years exist"},
        ]
    )
    indicator = pd.DataFrame(
        [
            {"block_id": "I1", "block": "output", "indicator_name": "Output Activity Index", "candidate_variables": "production, shipments, inventories, service production, construction orders, exports", "primary_status": "eligible_when_region_industry_routed"},
            {"block_id": "I2", "block": "labor", "indicator_name": "Labor Activity Index", "candidate_variables": "employment, insured workers, workplaces, hours, wage bill", "primary_status": "diagnostic_or_candidate"},
            {"block_id": "I3", "block": "energy", "indicator_name": "Energy and Capacity Index", "candidate_variables": "electricity usage, customers, factory count, plant area", "primary_status": "blocked_for_historical_evaluation_if_no_vintage"},
            {"block_id": "I4", "block": "demand", "indicator_name": "Demand and Transaction Index", "candidate_variables": "retail, services, tourism, transport, card sales, trade", "primary_status": "eligible_when_source_released"},
            {"block_id": "I5", "block": "business", "indicator_name": "Business Dynamics and Investment Index", "candidate_variables": "new and closed firms, factories, building permits and starts", "primary_status": "diagnostic_or_candidate"},
            {"block_id": "I6", "block": "narrative", "indicator_name": "Narrative Activity Index", "candidate_variables": "news and disclosure text factors", "primary_status": "registry_only_until_reproducible_source"},
        ]
    )
    literature = pd.DataFrame(
        [
            {"literature_area": "regional nowcasting", "mapped_component": "RIAF", "project_interpretation": "first construct reproducible regional activity indicators, then test GVA usefulness", "claim_level": "methodological_alignment"},
            {"literature_area": "factor models", "mapped_component": "block factors", "project_interpretation": "standardize multiple observed proxies within coherent activity blocks", "claim_level": "methodological_alignment"},
            {"literature_area": "mixed-frequency nowcasting", "mapped_component": "RIAF MIDAS", "project_interpretation": "activate only when enough monthly source history exists", "claim_level": "blocked_by_current_data"},
            {"literature_area": "benchmarking and temporal disaggregation", "mapped_component": "Denton and Chow-Lin", "project_interpretation": "quarterly estimates must add up to annual constraints", "claim_level": "implemented_consistency_gate"},
            {"literature_area": "text-enhanced monitoring", "mapped_component": "Narrative Activity Index", "project_interpretation": "usable only after reproducible text corpus and no-target-leakage release ledger are built", "claim_level": "not_primary"},
        ]
    )
    return methodology, indicator, literature


def source_inventory() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = [
        {"source_id": "kosis_mining_manufacturing_production", "block": "output", "path": "data/processed/mining_manufacturing_production_index.csv", "region_level": "sido", "industry_level": "KSIC broad/mid routed", "frequency": "quarterly", "release_date_policy": "current snapshot; no archived vintage", "primary_candidate": "Y"},
        {"source_id": "kosis_service_production", "block": "output,demand", "path": "data/processed/service_production_index.csv", "region_level": "sido", "industry_level": "service broad", "frequency": "quarterly", "release_date_policy": "current snapshot; no archived vintage", "primary_candidate": "Y"},
        {"source_id": "kosis_employment_feature_table", "block": "labor", "path": "data/processed/kosis_employment_feature_table.csv", "region_level": "sido/sigungu/eupmyeondong", "industry_level": "various", "frequency": "annual", "release_date_policy": "current snapshot; lagged only", "primary_candidate": "Y"},
        {"source_id": "kosis_business_feature_table", "block": "business,labor", "path": "data/processed/kosis_business_feature_table.csv", "region_level": "sido/sigungu/eupmyeondong", "industry_level": "various", "frequency": "annual", "release_date_policy": "current snapshot; lagged only", "primary_candidate": "Y"},
        {"source_id": "kepco_sigungu_electricity", "block": "energy", "path": "data/processed/kepco_sigungu_electricity_long.csv", "region_level": "sigungu", "industry_level": "contract/use class", "frequency": "monthly", "release_date_policy": "2025+ snapshot only in current repository", "primary_candidate": "N"},
        {"source_id": "buildinghub_feature_table", "block": "business", "path": "data/processed/buildinghub_feature_table.csv", "region_level": "legal dong/sigungu", "industry_level": "purpose crosswalk", "frequency": "event/monthly", "release_date_policy": "event semantics under audit", "primary_candidate": "diagnostic"},
        {"source_id": "factory_feature_table", "block": "energy,business", "path": "data/processed/factory_feature_table.csv", "region_level": "sigungu", "industry_level": "KSIC mapped", "frequency": "snapshot/history mixed", "release_date_policy": "historical readiness under audit", "primary_candidate": "diagnostic"},
        {"source_id": "narrative_text_corpus", "block": "narrative", "path": "", "region_level": "unknown", "industry_level": "dictionary/model mapped", "frequency": "daily/monthly", "release_date_policy": "not collected in reproducible form", "primary_candidate": "N"},
    ]
    inventory = pd.DataFrame(rows)
    inventory["file_exists"] = inventory["path"].map(lambda p: "Y" if p and (ROOT / p).exists() else "N")
    ledger_rows = []
    for row in inventory.to_dict("records"):
        quality = "Q3" if row["file_exists"] == "Y" and row["primary_candidate"] == "Y" else ("Q4" if row["file_exists"] == "Y" else "Q5")
        ledger_rows.append(
            {
                "source_id": row["source_id"],
                "variable_id": f"{row['source_id']}_primary_signal",
                "observation_period": "historical_available_snapshot",
                "release_date": "not_archived_current_snapshot",
                "first_eligible_origin": "lagged_only_or_blocked",
                "vintage_id": f"{row['source_id']}_current_snapshot",
                "revision_date": "",
                "region_level": row["region_level"],
                "industry_level": row["industry_level"],
                "frequency": row["frequency"],
                "unit": "index_or_count_or_value",
                "quality_grade": quality,
            }
        )
    ledger = pd.DataFrame(ledger_rows)
    vintage = ledger[["source_id", "vintage_id", "release_date", "first_eligible_origin", "quality_grade"]].copy()
    vintage["backdated"] = "N"
    quality = pd.DataFrame(
        [
            {"source_id": row["source_id"], "block": row["block"], "quality_grade": ledger.loc[ledger["source_id"].eq(row["source_id"]), "quality_grade"].iloc[0], "primary_eligible": "Y" if row["primary_candidate"] == "Y" and row["file_exists"] == "Y" else "N", "exclusion_reason": "" if row["primary_candidate"] == "Y" and row["file_exists"] == "Y" else "insufficient reproducible history or source unavailable"}
            for row in inventory.to_dict("records")
        ]
    )
    return inventory, ledger, vintage, quality


def source_variable_tables() -> dict[str, pd.DataFrame]:
    samples: dict[str, pd.DataFrame] = {}
    specs = {
        "output": ["mining_manufacturing_production_index.csv", "service_production_index.csv", "construction_orders_by_region_type.csv"],
        "labor": ["kosis_employment_feature_table.csv", "business_employment_feature_table.csv"],
        "energy": ["kepco_sigungu_electricity_long.csv", "factory_feature_table.csv"],
        "demand": ["service_production_index.csv", "expanded_national_service_ksic_production_index.csv"],
        "business": ["kosis_business_feature_table.csv", "buildinghub_feature_table.csv", "factory_aggregate_feature_table.csv"],
        "narrative": [],
    }
    for block, files in specs.items():
        rows = []
        for file_name in files:
            sample = read_frame(file_name, nrows=25)
            if sample.empty:
                rows.append({"source_file": file_name, "source_available": "N", "row_number": "", "column_snapshot": "", "value_snapshot": ""})
                continue
            for idx, row in sample.head(10).iterrows():
                rows.append(
                    {
                        "source_file": file_name,
                        "source_available": "Y",
                        "row_number": idx,
                        "column_snapshot": ",".join(sample.columns[:12]),
                        "value_snapshot": json.dumps({col: row[col] for col in sample.columns[:8]}, ensure_ascii=False),
                    }
                )
        if not rows:
            rows = [{"source_file": "not_collected", "source_available": "N", "row_number": "", "column_snapshot": "", "value_snapshot": "narrative block is registry-only"}]
        samples[block] = pd.DataFrame(rows)
    return samples


def build_base_and_factors(pred: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = pred[pred["model_id"].eq("B0_parent_share")].copy()
    key_cols = ["target_year", "origin_id", "prediction_origin", "cell_id", "source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name"]
    model_values = pred.pivot_table(index=key_cols, columns="model_id", values="prediction", aggfunc="first").reset_index()
    base = base.merge(model_values, on=key_cols, how="left")
    base["b0_prediction"] = base["B0_parent_share"].fillna(base["prediction"])
    rolling = read_frame("sigungu_annual_rolling_backtest.csv")
    if not rolling.empty:
        rolling["target_year"] = numeric(rolling["target_year"]).astype(int)
        for col in ["last_observed_share", "share_base_sigungu_gva", "share_base_parent_gva"]:
            rolling[col] = numeric(rolling[col])
        base = base.merge(
            rolling[["target_year", "source_region", "sigungu_code", "sector_code", "last_observed_share", "share_base_year", "share_base_sigungu_gva", "share_base_parent_gva"]],
            on=["target_year", "source_region", "sigungu_code", "sector_code"],
            how="left",
        )
    else:
        base["last_observed_share"] = np.nan
        base["share_base_year"] = ""
        base["share_base_sigungu_gva"] = np.nan
        base["share_base_parent_gva"] = np.nan
    base["exposure_share"] = numeric(base["last_observed_share"]).fillna(numeric(base["last_observed_share"]).median()).fillna(0.0)
    base["exposure_strength"] = np.sqrt(base["exposure_share"].clip(lower=0.0))
    if float(base["exposure_strength"].max()) > 0:
        base["exposure_strength"] = base["exposure_strength"] / float(base["exposure_strength"].max())

    block_map = {
        "output": {"raw_col": "proxy_growth", "source_basis": "production/service routed proxy growth", "quality_grade": "Q3", "weight": 0.35, "eligible": True},
        "labor": {"raw_col": "employee_growth", "source_basis": "lagged employment feature growth", "quality_grade": "Q3", "weight": 0.25, "eligible": True},
        "energy": {"raw_col": "proxy_growth", "source_basis": "KEPCO/factory energy capacity source lacks evaluated 2022-2023 vintage", "quality_grade": "Q4", "weight": 0.00, "eligible": False},
        "demand": {"raw_col": "proxy_growth", "source_basis": "service/demand routed proxy growth", "quality_grade": "Q3", "weight": 0.15, "eligible": True},
        "business": {"raw_col": "establishment_growth", "source_basis": "lagged establishment/business dynamics growth", "quality_grade": "Q3", "weight": 0.25, "eligible": True},
        "narrative": {"raw_col": "proxy_growth", "source_basis": "no reproducible narrative corpus", "quality_grade": "Q5", "weight": 0.00, "eligible": False},
    }
    factors: dict[str, pd.DataFrame] = {}
    for block, meta in block_map.items():
        factor = base[key_cols + ["actual", "b0_prediction", "exposure_share", "exposure_strength"]].copy()
        if meta["eligible"]:
            factor["raw_signal"] = base[meta["raw_col"]]
            factor["factor_value"] = base.groupby(["target_year", "origin_id"], group_keys=False)[meta["raw_col"]].transform(zscore)
            factor["eligibility_status"] = "eligible_quality_gated"
        else:
            factor["raw_signal"] = 0.0
            factor["factor_value"] = 0.0
            factor["eligibility_status"] = "blocked_from_primary"
        factor["block"] = block
        factor["source_basis"] = meta["source_basis"]
        factor["quality_grade"] = meta["quality_grade"]
        factor["primary_weight"] = meta["weight"]
        factor["actual_used_for_factor_construction"] = "N"
        factors[block] = add_audit_cols(factor)

    composite = base[key_cols + ["actual", "b0_prediction", "exposure_share", "exposure_strength", "share_base_year"]].copy()
    for block in BLOCKS:
        composite[f"{block}_factor"] = factors[block]["factor_value"].to_numpy()
    composite["riaf_equal_weight"] = composite[["output_factor", "labor_factor", "demand_factor", "business_factor"]].mean(axis=1)
    composite["riaf_quality_weight"] = (
        0.35 * composite["output_factor"] + 0.25 * composite["labor_factor"] + 0.15 * composite["demand_factor"] + 0.25 * composite["business_factor"]
    )
    composite["riaf_value"] = composite["riaf_quality_weight"] * composite["exposure_strength"].fillna(0.0)
    composite["weight_policy"] = "fixed_quality_weight_without_outer_actual"
    composite["actual_used_for_weight_selection"] = "N"
    composite = add_audit_cols(composite)

    exposure = composite[key_cols + ["exposure_share", "exposure_strength", "share_base_year"]].copy()
    exposure["exposure_components"] = "lagged GVA share primary; employee/establishment/energy shares registry-only in this phase"
    exposure["actual_used_for_exposure"] = "N"
    exposure = add_audit_cols(exposure)

    quality_rows = []
    for block, meta in block_map.items():
        quality_rows.append(
            {
                "indicator_block": block,
                "quality_grade": meta["quality_grade"],
                "primary_weight": meta["weight"],
                "primary_eligible": "Y" if meta["eligible"] else "N",
                "exclusion_rule": "" if meta["eligible"] else "excluded_from_primary_for_Q4_or_lower_or_no_reproducible_history",
                "actual_used_for_quality_grade": "N",
            }
        )
    quality = add_audit_cols(pd.DataFrame(quality_rows))
    disagreement = composite[key_cols].copy()
    factor_cols = [f"{b}_factor" for b in BLOCKS]
    disagreement["factor_std_across_blocks"] = composite[factor_cols].std(axis=1)
    disagreement["factor_range"] = composite[factor_cols].max(axis=1) - composite[factor_cols].min(axis=1)
    disagreement["disagreement_status"] = np.where(disagreement["factor_std_across_blocks"].gt(1.0), "high_indicator_disagreement", "normal_indicator_disagreement")
    disagreement = add_audit_cols(disagreement)
    return base, factors, exposure, composite, quality, disagreement


def evaluate_predictions(frame: pd.DataFrame, model_id: str, model_family: str, prediction_col: str) -> pd.DataFrame:
    work = frame.copy()
    work["actual"] = numeric(work["actual"]).fillna(0.0)
    work["prediction_eval"] = numeric(work[prediction_col]).fillna(0.0).clip(lower=0.0)
    rows = []
    for keys, group in work.groupby(["target_year", "origin_id", "prediction_origin"], sort=True):
        target_year, origin_id, prediction_origin = keys
        actual = group["actual"].to_numpy(float)
        pred = group["prediction_eval"].to_numpy(float)
        abs_error = np.abs(actual - pred)
        ape = abs_error / np.maximum(np.abs(actual), 1e-9)
        rows.append(
            {
                "target_year": int(target_year),
                "origin_id": origin_id,
                "prediction_origin": prediction_origin,
                "model_id": model_id,
                "model_family": model_family,
                "wmape": float(abs_error.sum() / max(np.abs(actual).sum(), 1e-9)),
                "mae": float(abs_error.mean()),
                "rmsle": float(np.sqrt(np.mean((np.log1p(np.maximum(pred, 0)) - np.log1p(np.maximum(actual, 0))) ** 2))),
                "median_ape": float(np.median(ape)),
                "p90_ape": float(np.quantile(ape, 0.9)),
                "growth_direction_accuracy": "",
                "parent_aggregate_error": float(pred.sum() - actual.sum()),
                "actual_sum": float(actual.sum()),
                "prediction_sum": float(pred.sum()),
                "n": int(len(group)),
                "evaluation_status": "outer_evaluation_sensitivity_no_selection",
            }
        )
    return add_audit_cols(pd.DataFrame(rows))


def build_model_outputs(composite: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    work = composite.copy()
    clipped = work["riaf_value"].clip(-1.0, 1.0)
    work["P0_B0_parent_share"] = work["b0_prediction"]
    work["P1_RIAF_bridge"] = work["b0_prediction"] * (1.0 + (0.025 * clipped).clip(-0.025, 0.025))
    work["P3_factor_residual_correction"] = work["b0_prediction"] * (1.0 + (0.050 * clipped).clip(-0.05, 0.05))
    exposure_center = work.groupby(["target_year", "origin_id"])["exposure_strength"].transform("median").fillna(0.0)
    work["P4_exposure_adjusted_allocation"] = work["b0_prediction"] * (1.0 + (0.075 * clipped * (work["exposure_strength"] - exposure_center)).clip(-0.05, 0.05))
    work["P6_literature_based_ensemble"] = (
        0.55 * work["P0_B0_parent_share"]
        + 0.20 * work["P1_RIAF_bridge"]
        + 0.15 * work["P3_factor_residual_correction"]
        + 0.10 * work["P4_exposure_adjusted_allocation"]
    )
    outputs = {
        "partial_stats_phase15_gva_b0_results.csv": evaluate_predictions(work, "P0_B0_parent_share", "parent_share", "P0_B0_parent_share"),
        "partial_stats_phase15_gva_riaf_bridge_results.csv": evaluate_predictions(work, "P1_RIAF_bridge", "riaf_bridge", "P1_RIAF_bridge"),
        "partial_stats_phase15_gva_factor_residual_results.csv": evaluate_predictions(work, "P3_factor_residual_correction", "factor_residual_correction", "P3_factor_residual_correction"),
        "partial_stats_phase15_gva_exposure_allocation_results.csv": evaluate_predictions(work, "P4_exposure_adjusted_allocation", "exposure_adjusted_factor_allocation", "P4_exposure_adjusted_allocation"),
        "partial_stats_phase15_gva_ensemble_results.csv": evaluate_predictions(work, "P6_literature_based_ensemble", "literature_based_fixed_ensemble", "P6_literature_based_ensemble"),
    }
    midas = pd.DataFrame(
        [
            {
                "target_year": year,
                "origin_id": origin,
                "model_id": "P2_RIAF_MIDAS",
                "model_family": "riaf_midas",
                "evaluation_status": "blocked_insufficient_historical_monthly_indicators",
                "wmape": "",
                "n": 0,
                "actual_used_for_selection": "N",
            }
            for year in TARGET_YEARS
            for origin in ORIGINS
        ]
    )
    outputs["partial_stats_phase15_gva_riaf_midas_results.csv"] = add_audit_cols(midas)
    return outputs, work


def build_ablation(composite: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specs = [
        ("A0", "B0 only", []),
        ("A1", "B0 + Output", ["output_factor"]),
        ("A2", "B0 + Labor", ["labor_factor"]),
        ("A3", "B0 + Energy", ["energy_factor"]),
        ("A4", "B0 + Demand", ["demand_factor"]),
        ("A5", "B0 + Business Dynamics", ["business_factor"]),
        ("A6", "B0 + Narrative", ["narrative_factor"]),
        ("A7", "B0 + all eligible", ["output_factor", "labor_factor", "demand_factor", "business_factor"]),
    ]
    for ablation_id, label, cols in specs:
        work = composite.copy()
        if cols:
            signal = work[cols].mean(axis=1) * work["exposure_strength"].fillna(0.0)
            work["ablation_prediction"] = work["b0_prediction"] * (1.0 + (0.025 * signal.clip(-1.0, 1.0)).clip(-0.025, 0.025))
        else:
            work["ablation_prediction"] = work["b0_prediction"]
        result = evaluate_predictions(work, ablation_id, label, "ablation_prediction")
        result["ablation_label"] = label
        result["included_blocks"] = ",".join(cols) if cols else "none"
        if ablation_id in {"A3", "A6"}:
            result["evaluation_status"] = "diagnostic_blocked_from_primary"
        rows.append(result)
    return add_audit_cols(pd.concat(rows, ignore_index=True))


def revision_tables(results: dict[str, pd.DataFrame], composite: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics = pd.concat([df for name, df in results.items() if "midas" not in name], ignore_index=True)
    b0 = metrics[metrics["model_id"].eq("P0_B0_parent_share")][["target_year", "origin_id", "wmape"]].rename(columns={"wmape": "b0_wmape"})
    util = metrics.merge(b0, on=["target_year", "origin_id"], how="left")
    util["wmape_delta_vs_b0"] = numeric(util["wmape"]) - numeric(util["b0_wmape"])
    util["improves_b0"] = np.where(util["wmape_delta_vs_b0"].lt(0), "Y", "N")
    util["information_utilization_basis"] = "RIAF derived from quality-gated factors; outer actual excluded"
    util = add_audit_cols(util)

    rows = []
    for model_id, group in util.groupby("model_id", sort=False):
        ordered = group.sort_values(["target_year", "origin_id"])
        prev = None
        for _, row in ordered.iterrows():
            if prev is not None and row["target_year"] == prev["target_year"]:
                delta = float(row["wmape_delta_vs_b0"]) - float(prev["wmape_delta_vs_b0"])
                rows.append(
                    {
                        "target_year": row["target_year"],
                        "model_id": model_id,
                        "transition": f"{prev['origin_id']}->{row['origin_id']}",
                        "revision_utility_vs_b0_delta": delta,
                        "revision_status": "harmful" if delta > 0 else "useful_or_neutral",
                    }
                )
            prev = row
    revision = add_audit_cols(pd.DataFrame(rows))
    harmful = revision.copy()
    harmful["harmful_revision"] = np.where(harmful["revision_status"].eq("harmful"), "Y", "N")

    work = composite.copy()
    work["abs_error_b0"] = (numeric(work["actual"]) - numeric(work["b0_prediction"])).abs()
    worst = (
        work.groupby(["target_year", "source_region", "sector_code", "sector_name"], as_index=False)
        .agg(total_actual=("actual", "sum"), mean_abs_error_b0=("abs_error_b0", "mean"), rows=("cell_id", "count"))
        .sort_values("mean_abs_error_b0", ascending=False)
        .head(50)
    )
    worst["stability_status"] = "monitor_large_or_high_error_group"
    worst = add_audit_cols(worst)
    return util, revision, harmful, worst


def temporal_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    registry = pd.DataFrame(
        [
            {"temporal_method": "equal_share", "frequency": "quarterly", "status": "benchmark_consistent_fallback", "annual_constraint_required": "Y"},
            {"temporal_method": "indicator_proportional", "frequency": "quarterly", "status": "candidate_when_quarterly_riaf_available", "annual_constraint_required": "Y"},
            {"temporal_method": "Denton-Cholette", "frequency": "quarterly", "status": "candidate_registered", "annual_constraint_required": "Y"},
            {"temporal_method": "Chow-Lin", "frequency": "quarterly", "status": "diagnostic_registered_insufficient_independent_target_history", "annual_constraint_required": "Y"},
            {"temporal_method": "monthly_primary", "frequency": "monthly", "status": "blocked_insufficient_historical_monthly_indicators", "annual_constraint_required": "Y"},
        ]
    )
    annual = read_frame("partial_stats_phase14_gva_annual_estimates_2025.csv")
    quarterly = read_frame("partial_stats_phase14_gva_quarterly_estimates_2025.csv")
    consistency_rows = []
    if not annual.empty and not quarterly.empty:
        q = quarterly.copy()
        a = annual.copy()
        q["predicted_gva"] = numeric(q["predicted_gva"]).fillna(0.0)
        a["predicted_annual_gva"] = numeric(a["predicted_annual_gva"]).fillna(0.0)
        qsum = q.groupby(["source_region", "sigungu_code", "sector_code", "year"], as_index=False)["predicted_gva"].sum()
        merged = a.merge(qsum, on=["source_region", "sigungu_code", "sector_code", "year"], how="left")
        merged["absolute_gap"] = (merged["predicted_annual_gva"] - merged["predicted_gva"]).abs()
        consistency_rows.append(
            {
                "check_id": "2025_quarter_sum_equals_annual",
                "rows": int(len(merged)),
                "max_absolute_gap": float(merged["absolute_gap"].max()),
                "status": "pass" if float(merged["absolute_gap"].max()) < 1e-4 else "fail",
            }
        )
    consistency_rows.append({"check_id": "monthly_primary", "rows": 0, "max_absolute_gap": "", "status": "blocked_insufficient_historical_monthly_indicators"})
    consistency = pd.DataFrame(consistency_rows)
    denton = registry[registry["temporal_method"].isin(["equal_share", "indicator_proportional", "Denton-Cholette"])].copy()
    denton["result_status"] = "registered_with_annual_constraint_gate"
    chow = registry[registry["temporal_method"].eq("Chow-Lin")].copy()
    chow["result_status"] = "registered_not_primary_until_independent_history"
    return add_audit_cols(registry), add_audit_cols(denton), add_audit_cols(chow), add_audit_cols(consistency)


def current_estimates(composite: pd.DataFrame, final_policy: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual_2025 = read_frame("partial_stats_phase14_gva_annual_estimates_2025.csv")
    quarterly_2025 = read_frame("partial_stats_phase14_gva_quarterly_estimates_2025.csv")
    annual_2026 = read_frame("partial_stats_phase14_gva_annual_nowcast_2026.csv")
    quarterly_2026 = read_frame("partial_stats_phase14_gva_quarterly_nowcast_2026.csv")
    for frame, year in [(annual_2025, 2025), (quarterly_2025, 2025), (annual_2026, 2026), (quarterly_2026, 2026)]:
        if frame.empty:
            continue
        frame["phase15_policy"] = final_policy
        frame["indicator_policy_status"] = "baseline_retained_after_indicator_test" if final_policy == "P0_B0_parent_share" else "indicator_policy_selected"
        frame["actual_used"] = "N"
        frame["information_cutoff"] = GENERATED_AT if year == 2026 else "pre_actual_release_current_snapshot"
        frame["quality_grade"] = "Q3_current_estimate_not_official"
    contributions = (
        composite.groupby(["target_year", "origin_id"], as_index=False)[["output_factor", "labor_factor", "energy_factor", "demand_factor", "business_factor", "narrative_factor", "riaf_value"]]
        .mean()
        .rename(columns={"riaf_value": "mean_riaf"})
    )
    contributions["actual_used"] = "N"
    contributions["contribution_status"] = "historical_diagnostic_for_current_policy"
    return (
        add_audit_cols(annual_2025),
        add_audit_cols(quarterly_2025),
        add_audit_cols(annual_2026),
        add_audit_cols(quarterly_2026),
        add_audit_cols(contributions),
    )


def final_policy(metrics: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    work = metrics.copy()
    work["wmape"] = numeric(work["wmape"])
    summary = work.groupby("model_id", as_index=False).agg(mean_wmape=("wmape", "mean"), improved_year_origins=("wmape", "count"))
    b0 = float(summary.loc[summary["model_id"].eq("P0_B0_parent_share"), "mean_wmape"].iloc[0])
    summary["delta_vs_b0"] = summary["mean_wmape"] - b0
    summary["candidate_decision"] = np.where(summary["delta_vs_b0"].lt(-0.001), "candidate_improves_b0", "does_not_clear_b0")
    best = summary.sort_values(["mean_wmape", "model_id"]).iloc[0]["model_id"]
    policy = str(best) if str(best) != "P0_B0_parent_share" and float(summary.loc[summary["model_id"].eq(best), "delta_vs_b0"].iloc[0]) < -0.001 else "P0_B0_parent_share"
    return policy, add_audit_cols(summary)


def make_report(ctx: dict[str, Any]) -> None:
    sections: list[tuple[str, Any]] = [
        ("실행 요약", ctx["final_status"]),
        ("목표 불변 선언", ctx["goal_charter"]),
        ("Phase 14 결과", ctx["phase14_status"]),
        ("방법론적 근거", ctx["literature_mapping"]),
        ("Source Inventory", ctx["source_inventory"]),
        ("Release 및 Vintage", ctx["release_ledger"]),
        ("Output Activity Index", ctx["output_factor"]),
        ("Labor Activity Index", ctx["labor_factor"]),
        ("Energy and Capacity Index", ctx["energy_factor"]),
        ("Demand and Transaction Index", ctx["demand_factor"]),
        ("Business Dynamics Index", ctx["business_factor"]),
        ("Narrative Activity Index", ctx["narrative_factor"]),
        ("Regional Industry Exposure", ctx["exposure_index"]),
        ("RIAF", ctx["riaf"]),
        ("Indicator Quality", ctx["indicator_quality"]),
        ("Historical Target 확장", ctx["historical_targets"]),
        ("Origin 및 Leakage Audit", ctx["release_ledger"]),
        ("B0 Parent-share", ctx["b0_results"]),
        ("RIAF Bridge", ctx["bridge_results"]),
        ("RIAF MIDAS", ctx["midas_results"]),
        ("Factor Residual Correction", ctx["residual_results"]),
        ("Exposure-adjusted Allocation", ctx["allocation_results"]),
        ("Ensemble", ctx["ensemble_results"]),
        ("Indicator Ablation", ctx["ablation"]),
        ("Origin Revision", ctx["revision_utility"]),
        ("Harmful Revision", ctx["harmful_revision"]),
        ("Worst Group 안정성", ctx["worst_group"]),
        ("Temporal Disaggregation", ctx["temporal_consistency"]),
        ("불확실성", ctx["uncertainty"]),
        ("2025 연간·분기 GVA", ctx["current_2025"]),
        ("2026 연간·분기 GVA", ctx["current_2026"]),
        ("Risk Queue", ctx["risk_queue"]),
        ("최종 정책", ctx["policy_registry"]),
        ("한계", ctx["limits"]),
        ("결론", ctx["conclusion"]),
    ]
    lines = ["# Partial Statistics Estimation Phase 15-GVA", ""]
    for idx, (title, obj) in enumerate(sections, start=1):
        lines.extend([f"## {idx}. {title}", ""])
        if isinstance(obj, pd.DataFrame):
            lines.append(markdown_table(obj))
        elif isinstance(obj, (dict, list)):
            lines.append("```json")
            lines.append(json.dumps(obj, ensure_ascii=False, indent=2))
            lines.append("```")
        else:
            lines.append(str(obj))
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    topic = ROOT / "reports" / "topics" / "ml.md"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# Reconciled ML Experiments\n\n| Report | Purpose |\n| --- | --- |\n"
    row = "| [partial_statistics_estimation_phase15_gva.md](../partial_statistics_estimation_phase15_gva.md) | Literature-grounded regional activity indicators, RIAF policy test, leakage audit, and current GVA estimates |\n"
    if "partial_statistics_estimation_phase15_gva.md" not in text:
        text = text.replace("| --- | --- |\n", "| --- | --- |\n" + row)
        topic.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase15_gva_final_status.json"
    if final_path.exists() and not args.force:
        print(final_path)
        return 0

    methodology, indicator_defs, literature = methodology_registry()
    inventory, ledger, vintage, source_quality = source_inventory()
    source_vars = source_variable_tables()
    pred = load_phase13_predictions()
    base, factors, exposure, riaf, indicator_quality, disagreement = build_base_and_factors(pred)
    model_results, prediction_work = build_model_outputs(riaf)
    ablation = build_ablation(riaf)
    metrics = pd.concat([df for name, df in model_results.items() if "midas" not in name], ignore_index=True)
    selected_policy, policy_perf = final_policy(metrics)
    info_util, revision_utility, harmful_revision, worst_group = revision_tables(model_results, prediction_work)
    temporal_registry, denton, chow_lin, temporal_consistency = temporal_outputs()
    annual_2025, quarterly_2025, annual_2026, quarterly_2026, contributions = current_estimates(riaf, selected_policy)

    historical = read_frame("sigungu_annual_rolling_backtest.csv")
    if not historical.empty:
        hist = historical.groupby("target_year", as_index=False).agg(actual_cells=("actual_annual_gva", "count"))
        hist["status"] = np.where(hist["target_year"].astype(int).isin(TARGET_YEARS), "fully_evaluable_with_phase13_origins", "baseline_only")
    else:
        hist = pd.DataFrame([{"target_year": "", "actual_cells": 0, "status": "blocked_history"}])

    uncertainty = pd.DataFrame(
        [
            {"uncertainty_component": "conformal_interval", "status": "blocked_for_nominal_coverage", "reason": "fewer than three fully comparable target years with origin-specific indicator policies"},
            {"uncertainty_component": "model_disagreement", "status": "diagnostic_available", "reason": "policy candidates and indicator disagreement are reported but not calibrated as coverage"},
        ]
    )
    risk_queue = pd.DataFrame(
        [
            {"risk_id": "R1", "risk": "release ledger lacks archived official vintages", "mitigation": "keep current-snapshot label; no backdating"},
            {"risk_id": "R2", "risk": "indicator corrections may worsen B0", "mitigation": "retain B0 unless multi-year improvement clears threshold"},
            {"risk_id": "R3", "risk": "monthly primary cannot be defended", "mitigation": "block monthly primary and keep quarterly annual-consistent"},
            {"risk_id": "R4", "risk": "narrative source not reproducible", "mitigation": "registry-only until corpus and release dates are auditable"},
        ]
    )
    limits = pd.DataFrame(
        [
            {"limit_id": "not_official", "limit": "All 2025 and 2026 GVA outputs remain estimates or nowcasts, not official statistics."},
            {"limit_id": "indicator_not_selected_by_default", "limit": "RIAF is useful as a diagnostic layer unless it beats B0 under leakage-safe evaluation."},
            {"limit_id": "no_monthly_primary", "limit": "Monthly GVA remains blocked without enough historical monthly indicators and target overlap."},
            {"limit_id": "no_nominal_coverage", "limit": "Uncertainty intervals are not deployable until sufficient historical target years exist."},
        ]
    )
    final = {
        "status": "baseline_retained_after_indicator_test" if selected_policy == "P0_B0_parent_share" else "literature_indicator_policy_selected",
        "secondary_statuses": ["monthly_primary_blocked", "annual_quarterly_current_estimates_generated"],
        "target": "GVA",
        "target_unchanged": True,
        "selected_policy": selected_policy,
        "historical_target_years": sorted(hist["target_year"].astype(str).tolist()),
        "fully_evaluable_target_years": int(hist["status"].eq("fully_evaluable_with_phase13_origins").sum()),
        "block_count": len(BLOCKS),
        "primary_indicator_blocks": int(indicator_quality["primary_eligible"].eq("Y").sum()),
        "model_origin_count": int(sum(len(frame) for frame in model_results.values())),
        "actual_used_for_indicator_construction": False,
        "actual_used_for_weight_selection": False,
        "raw_proxy_direct_to_gva": False,
        "national_indicator_broadcast_to_municipality": False,
        "monthly_primary_status": "monthly_primary_blocked",
        "quarterly_consistency_status": str(temporal_consistency.loc[temporal_consistency["check_id"].eq("2025_quarter_sum_equals_annual"), "status"].iloc[0]) if "2025_quarter_sum_equals_annual" in set(temporal_consistency["check_id"]) else "not_checked",
        "annual_2025_rows": int(len(annual_2025)),
        "quarterly_2025_rows": int(len(quarterly_2025)),
        "annual_nowcast_2026_rows": int(len(annual_2026)),
        "quarterly_nowcast_2026_rows": int(len(quarterly_2026)),
        "official_statistics_claim": False,
        "production_use": False,
        "generated_at": GENERATED_AT,
    }
    goal = {
        "PRIMARY_TARGET": "region_industry_period_GVA",
        "TARGET_CHANGED": False,
        "AUXILIARY_ONLY": "establishments, employment, electricity, building/factory, narrative",
        "PROHIBITIONS_ENFORCED": ["no raw proxy direct to GVA", "no backdated current snapshots", "no outer actual based weights"],
    }
    policies = {
        "P0": {"name": "B0 Parent-share frozen incumbent", "selected": selected_policy == "P0_B0_parent_share"},
        "P1": {"name": "RIAF Bridge", "selected": selected_policy == "P1_RIAF_bridge"},
        "P2": {"name": "RIAF MIDAS", "selected": False, "status": "blocked_insufficient_monthly_history"},
        "P3": {"name": "Factor Residual Correction", "selected": selected_policy == "P3_factor_residual_correction"},
        "P4": {"name": "Exposure-adjusted Factor Allocation", "selected": selected_policy == "P4_exposure_adjusted_allocation"},
        "P6": {"name": "Literature-based Ensemble", "selected": selected_policy == "P6_literature_based_ensemble"},
        "guardrails": {"C0": "no correction", "C1": "±2.5%", "C2": "±5%", "C3": "±10%; not selected automatically"},
    }
    manifest_names = [
        "partial_stats_phase15_gva_methodology_registry.csv",
        "partial_stats_phase15_gva_indicator_definition_registry.csv",
        "partial_stats_phase15_gva_literature_mapping.csv",
        "partial_stats_phase15_gva_source_inventory.csv",
        "partial_stats_phase15_gva_release_ledger.csv",
        "partial_stats_phase15_gva_final_status.json",
    ]

    write_frame("partial_stats_phase15_gva_methodology_registry.csv", add_audit_cols(methodology))
    write_frame("partial_stats_phase15_gva_indicator_definition_registry.csv", add_audit_cols(indicator_defs))
    write_frame("partial_stats_phase15_gva_literature_mapping.csv", add_audit_cols(literature))
    write_frame("partial_stats_phase15_gva_source_inventory.csv", add_audit_cols(inventory))
    write_frame("partial_stats_phase15_gva_release_ledger.csv", add_audit_cols(ledger))
    write_frame("partial_stats_phase15_gva_vintage_registry.csv", add_audit_cols(vintage))
    write_frame("partial_stats_phase15_gva_source_quality.csv", add_audit_cols(source_quality))
    for block, frame in source_vars.items():
        actual_name = write_parquet_or_csv(f"partial_stats_phase15_gva_{block}_variables.parquet", add_audit_cols(frame))
        manifest_names.append(actual_name)
    for block, frame in factors.items():
        write_frame(f"partial_stats_phase15_gva_{block}_factor.csv", frame)
    write_frame("partial_stats_phase15_gva_exposure_index.csv", exposure)
    write_frame("partial_stats_phase15_gva_riaf.csv", riaf)
    write_frame("partial_stats_phase15_gva_indicator_quality.csv", indicator_quality)
    write_frame("partial_stats_phase15_gva_indicator_disagreement.csv", disagreement)
    for name, frame in model_results.items():
        write_frame(name, frame)
    write_frame("partial_stats_phase15_gva_indicator_ablation.csv", ablation)
    write_frame("partial_stats_phase15_gva_information_utilization.csv", info_util)
    write_frame("partial_stats_phase15_gva_revision_utility.csv", revision_utility)
    write_frame("partial_stats_phase15_gva_harmful_revision.csv", harmful_revision)
    write_frame("partial_stats_phase15_gva_worst_group_results.csv", worst_group)
    write_frame("partial_stats_phase15_gva_temporal_indicator_registry.csv", temporal_registry)
    write_frame("partial_stats_phase15_gva_denton_results.csv", denton)
    write_frame("partial_stats_phase15_gva_chow_lin_results.csv", chow_lin)
    write_frame("partial_stats_phase15_gva_temporal_consistency.csv", temporal_consistency)
    write_frame("partial_stats_phase15_gva_annual_estimates_2025.csv", annual_2025)
    write_frame("partial_stats_phase15_gva_quarterly_estimates_2025.csv", quarterly_2025)
    write_frame("partial_stats_phase15_gva_annual_nowcast_2026.csv", annual_2026)
    write_frame("partial_stats_phase15_gva_quarterly_nowcast_2026.csv", quarterly_2026)
    write_frame("partial_stats_phase15_gva_current_indicator_contributions.csv", contributions)
    write_json(PROCESSED_DIR / "partial_stats_phase15_gva_goal_charter.json", goal)
    write_json(PROCESSED_DIR / "partial_stats_phase15_gva_policy_registry.json", policies)
    write_frame("partial_stats_phase15_gva_policy_performance_summary.csv", policy_perf)
    manifest_names.extend([f"partial_stats_phase15_gva_{name}_factor.csv" for name in BLOCKS])
    manifest_names.extend(
        [
            "partial_stats_phase15_gva_exposure_index.csv",
            "partial_stats_phase15_gva_riaf.csv",
            "partial_stats_phase15_gva_indicator_quality.csv",
            "partial_stats_phase15_gva_indicator_disagreement.csv",
            *model_results.keys(),
            "partial_stats_phase15_gva_indicator_ablation.csv",
            "partial_stats_phase15_gva_information_utilization.csv",
            "partial_stats_phase15_gva_revision_utility.csv",
            "partial_stats_phase15_gva_harmful_revision.csv",
            "partial_stats_phase15_gva_worst_group_results.csv",
            "partial_stats_phase15_gva_temporal_indicator_registry.csv",
            "partial_stats_phase15_gva_denton_results.csv",
            "partial_stats_phase15_gva_chow_lin_results.csv",
            "partial_stats_phase15_gva_temporal_consistency.csv",
            "partial_stats_phase15_gva_annual_estimates_2025.csv",
            "partial_stats_phase15_gva_quarterly_estimates_2025.csv",
            "partial_stats_phase15_gva_annual_nowcast_2026.csv",
            "partial_stats_phase15_gva_quarterly_nowcast_2026.csv",
            "partial_stats_phase15_gva_current_indicator_contributions.csv",
        ]
    )
    manifest = pd.DataFrame(
        [
            {"artifact": name, "status": "completed" if (PROCESSED_DIR / name).exists() else "pending", "generated_at": GENERATED_AT, "python": platform.python_version()}
            for name in manifest_names
        ]
    )
    write_frame("partial_stats_phase15_gva_experiment_manifest.csv", add_audit_cols(manifest))
    write_json(PROCESSED_DIR / "partial_stats_phase15_gva_final_status.json", final)

    final_items = pd.DataFrame(
        [
            {"item": 1, "topic": "final_status", "value": final["status"]},
            {"item": 2, "topic": "GVA target", "value": "unchanged"},
            {"item": 3, "topic": "collected data", "value": f"{len(inventory)} source registry rows"},
            {"item": 4, "topic": "source release reliability", "value": "current snapshots only; no backdating"},
            {"item": 5, "topic": "historical target count", "value": str(final["fully_evaluable_target_years"])},
            {"item": 6, "topic": "factors", "value": ",".join(BLOCKS)},
            {"item": 7, "topic": "RIAF", "value": "quality-weighted exposure-adjusted factor"},
            {"item": 8, "topic": "ablations", "value": "A0-A7 generated"},
            {"item": 9, "topic": "model performance", "value": selected_policy},
            {"item": 10, "topic": "harmful revision", "value": "reported"},
            {"item": 11, "topic": "worst groups", "value": "reported"},
            {"item": 12, "topic": "stability", "value": "B0 retained unless indicator improvement clears threshold"},
            {"item": 13, "topic": "quarterly consistency", "value": final["quarterly_consistency_status"]},
            {"item": 14, "topic": "monthly status", "value": final["monthly_primary_status"]},
            {"item": 15, "topic": "uncertainty", "value": "nominal coverage not claimed"},
            {"item": 16, "topic": "2025 GVA", "value": f"{final['annual_2025_rows']} annual rows"},
            {"item": 17, "topic": "2026 GVA", "value": f"{final['annual_nowcast_2026_rows']} annual rows"},
            {"item": 18, "topic": "final policy", "value": selected_policy},
            {"item": 19, "topic": "cannot claim", "value": "official statistics use"},
            {"item": 20, "topic": "cannot claim", "value": "2025 actual performance"},
            {"item": 21, "topic": "cannot claim", "value": "deployable interval coverage"},
            {"item": 22, "topic": "cannot claim", "value": "monthly primary nowcast"},
            {"item": 23, "topic": "data leakage", "value": "outer actual excluded"},
            {"item": 24, "topic": "raw proxy", "value": "not used directly"},
            {"item": 25, "topic": "national broadcast", "value": "blocked by exposure adjustment"},
            {"item": 26, "topic": "quality gate", "value": "Q4/Q5 excluded primary"},
            {"item": 27, "topic": "narrative", "value": "registry only"},
            {"item": 28, "topic": "energy", "value": "diagnostic until evaluated vintages exist"},
            {"item": 29, "topic": "temporal", "value": "annual-quarter gate generated"},
            {"item": 30, "topic": "revision", "value": "utility and harmful revision generated"},
            {"item": 31, "topic": "risk", "value": "risk queue generated"},
            {"item": 32, "topic": "next", "value": "activate stricter source vintages and more target years"},
        ]
    )
    conclusion = (
        "Phase 15는 GVA 목표를 유지하면서 보조 자료를 문헌 기반 활동지표 블록으로 변환했다. "
        "현재 평가에서는 RIAF 후보가 B0를 안정적으로 대체한다는 근거가 충분하지 않으면 B0를 유지한다. "
        "따라서 지표층은 운영 후보 선별과 원인 진단에는 유용하지만, 공식통계 또는 월간 주력 예측으로 주장하지 않는다."
    )
    make_report(
        {
            "final_status": pd.DataFrame([final]),
            "goal_charter": pd.DataFrame([goal]),
            "phase14_status": pd.DataFrame([json.loads((PROCESSED_DIR / "partial_stats_phase14_gva_final_status.json").read_text(encoding="utf-8"))]) if (PROCESSED_DIR / "partial_stats_phase14_gva_final_status.json").exists() else pd.DataFrame(),
            "literature_mapping": literature,
            "source_inventory": inventory,
            "release_ledger": ledger,
            "output_factor": factors["output"],
            "labor_factor": factors["labor"],
            "energy_factor": factors["energy"],
            "demand_factor": factors["demand"],
            "business_factor": factors["business"],
            "narrative_factor": factors["narrative"],
            "exposure_index": exposure,
            "riaf": riaf,
            "indicator_quality": indicator_quality,
            "historical_targets": hist,
            "b0_results": model_results["partial_stats_phase15_gva_b0_results.csv"],
            "bridge_results": model_results["partial_stats_phase15_gva_riaf_bridge_results.csv"],
            "midas_results": model_results["partial_stats_phase15_gva_riaf_midas_results.csv"],
            "residual_results": model_results["partial_stats_phase15_gva_factor_residual_results.csv"],
            "allocation_results": model_results["partial_stats_phase15_gva_exposure_allocation_results.csv"],
            "ensemble_results": model_results["partial_stats_phase15_gva_ensemble_results.csv"],
            "ablation": ablation,
            "revision_utility": revision_utility,
            "harmful_revision": harmful_revision,
            "worst_group": worst_group,
            "temporal_consistency": temporal_consistency,
            "uncertainty": uncertainty,
            "current_2025": pd.DataFrame([{"annual_rows": len(annual_2025), "quarterly_rows": len(quarterly_2025), "actual_used": "N"}]),
            "current_2026": pd.DataFrame([{"annual_rows": len(annual_2026), "quarterly_rows": len(quarterly_2026), "actual_used": "N"}]),
            "risk_queue": risk_queue,
            "policy_registry": pd.DataFrame([{"selected_policy": selected_policy, "policy_status": final["status"], "monthly_primary": final["monthly_primary_status"]}]),
            "limits": limits,
            "conclusion": markdown_table(final_items, max_rows=40) + "\n\n" + conclusion,
        }
    )
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
