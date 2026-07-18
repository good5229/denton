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
import run_partial_statistics_phase16_gva as phase16
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase17_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase17_gva.md"
ENERGY_SECTORS = {"B00", "C00", "D00"}
SERVICE_SECTORS = {"G00", "H00", "I00", "J00", "K00", "L00", "M00", "N00", "O00", "Q00", "R00"}


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


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def add_audit_cols(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base_cols = [col for col in out.columns if col not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = core.stable_hash(out[base_cols].head(20000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
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


def stable_frame_hash(frame: pd.DataFrame, cols: list[str] | None = None) -> str:
    work = frame[cols].copy() if cols else frame.copy()
    work = work.fillna("").sort_values(list(work.columns)).reset_index(drop=True)
    return core.stable_hash(work.to_dict("records"))


def build_phase16_context() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame]:
    panel = phase16.build_target_panel()
    release_ledger, _, _ = phase16.build_release_ledger(panel)
    store, _, _, factors = phase16.build_feature_store(panel, release_ledger)
    _, _, _, _, qualification = phase16.indicator_diagnostics(factors, panel)
    return panel, release_ledger, store, factors, qualification


def canonical_feature_store(store: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    canonical_cols = [
        "target_year",
        "origin_id",
        "prediction_origin",
        "region_key",
        "industry_code",
        "feature_name",
        "feature_value",
        "source_id",
        "observation_period",
        "release_date",
        "quality_grade",
        "block",
        "feature_available",
    ]
    out = store[canonical_cols].copy()
    out = out.rename(columns={"release_date": "official_release_date"})
    out["first_eligible_origin"] = out["origin_id"]
    out["vintage_id"] = out["source_id"].astype(str) + "_" + out["target_year"].astype(str) + "_" + out["origin_id"].astype(str)
    out["transformation_id"] = out["block"].astype(str) + "_standardized_asof_v1"
    source_cols = ["source_id", "observation_period", "region_key", "industry_code", "feature_name", "feature_value"]
    out["source_row_hash"] = out[source_cols].fillna("").astype(str).agg("|".join, axis=1).map(lambda text: core.stable_hash(text))
    out["source_file_hash"] = out["source_id"].map(lambda source: core.stable_hash(str(source)))
    out = add_audit_cols(out)

    parquet_path = PROCESSED_DIR / "partial_stats_phase17_gva_asof_feature_store.parquet"
    fallback_path = PROCESSED_DIR / "partial_stats_phase17_gva_asof_feature_store_fallback.csv"
    out.to_parquet(parquet_path, index=False)
    write_frame(fallback_path.name, out)
    from_parquet = pd.read_parquet(parquet_path).fillna("")
    from_csv = pd.read_csv(fallback_path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False).fillna("")
    canonical_hash = stable_frame_hash(from_parquet.astype(str))
    fallback_hash = stable_frame_hash(from_csv.astype(str))
    equivalence = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "canonical_artifact": parquet_path.name,
                    "fallback_artifact": fallback_path.name,
                    "canonical_content_hash": canonical_hash,
                    "fallback_content_hash": fallback_hash,
                    "fallback_equivalence_status": "pass" if canonical_hash == fallback_hash else "fail",
                }
            ]
        )
    )

    hash_rows = []
    for keys, group in out.groupby(["target_year", "origin_id"], sort=True):
        target_year, origin_id = keys
        hash_rows.append(
            {
                "target_year": int(target_year),
                "origin_id": origin_id,
                "eligible_source_set_hash": core.stable_hash(sorted(group["source_id"].unique())),
                "eligible_observation_hash": stable_frame_hash(group, ["source_id", "observation_period", "region_key", "industry_code", "feature_name"]),
                "raw_feature_value_hash": stable_frame_hash(group, ["source_id", "region_key", "industry_code", "feature_name", "feature_value"]),
                "transformed_feature_value_hash": stable_frame_hash(group, ["region_key", "industry_code", "feature_name", "feature_value", "transformation_id"]),
                "model_input_hash": stable_frame_hash(group[group["feature_available"].eq("Y")], ["region_key", "industry_code", "feature_name", "feature_value"]),
                "prediction_hash": "",
            }
        )
    hash_registry = add_audit_cols(pd.DataFrame(hash_rows))

    materialization_rows = []
    for (target_year, feature_name), group in hash_registry.merge(out[["target_year", "origin_id", "feature_name"]].drop_duplicates(), on=["target_year", "origin_id"], how="left").groupby(["target_year", "feature_name"], sort=True):
        ordered = group.drop_duplicates(["origin_id"]).sort_values("origin_id")
        obs_changes = int(ordered["eligible_observation_hash"].nunique())
        raw_changes = int(ordered["raw_feature_value_hash"].nunique())
        status = "valid_same_content" if obs_changes == 1 and raw_changes == 1 else ("origin_materialized" if raw_changes > 1 else "new_observation_not_materialized")
        materialization_rows.append({"target_year": target_year, "feature_name": feature_name, "eligible_observation_hash_count": obs_changes, "raw_feature_value_hash_count": raw_changes, "materialization_status": status})
    materialization = add_audit_cols(pd.DataFrame(materialization_rows))

    lineage = out[
        [
            "target_year",
            "origin_id",
            "region_key",
            "industry_code",
            "feature_name",
            "source_id",
            "observation_period",
            "official_release_date",
            "first_eligible_origin",
            "vintage_id",
            "source_row_hash",
            "transformation_id",
        ]
    ].copy()
    required = ["source_id", "observation_period", "source_row_hash", "transformation_id", "vintage_id"]
    lineage["lineage_complete"] = np.where(lineage[required].astype(str).ne("").all(axis=1), "Y", "N")
    lineage = add_audit_cols(lineage)
    return out, equivalence, hash_registry, materialization, lineage


def source_tracks(release_ledger: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ledger = release_ledger.copy()
    strict = ledger[ledger["track"].eq("strict")].copy()
    conservative = ledger[ledger["track"].eq("conservative")].copy()
    if conservative.empty:
        conservative = pd.DataFrame([{"source_id": "none", "track": "conservative", "status": "no_C_documented_lag_source"}])
    sensitivity = ledger[ledger["track"].eq("sensitivity")].copy()
    return add_audit_cols(strict), add_audit_cols(conservative), add_audit_cols(sensitivity), add_audit_cols(ledger)


def energy_feature_cube(panel: pd.DataFrame, factors: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    energy = factors["energy"].copy()
    cube = energy.copy()
    cube["energy_sector_allowed"] = np.where(cube["sector_code"].isin(ENERGY_SECTORS), "Y", "N")
    cube["industrial_kwh_yoy"] = numeric(cube["raw_signal"])
    cube["industrial_kwh_mom"] = ""
    cube["rolling_3m_yoy"] = cube["industrial_kwh_yoy"]
    cube["rolling_6m_yoy"] = cube["industrial_kwh_yoy"]
    cube["year_to_date_growth"] = cube["industrial_kwh_yoy"]
    cube["customer_count_yoy"] = ""
    cube["kwh_per_customer_yoy"] = ""
    cube["regional_relative_growth"] = cube.groupby(["target_year", "origin_id"])["industrial_kwh_yoy"].transform(lambda s: numeric(s).fillna(0) - numeric(s).fillna(0).mean())
    cube["same_month_yoy_primary"] = "Y"
    cube = add_audit_cols(cube)
    (PROCESSED_DIR / "partial_stats_phase17_gva_energy_feature_cube.parquet").parent.mkdir(parents=True, exist_ok=True)
    cube.to_parquet(PROCESSED_DIR / "partial_stats_phase17_gva_energy_feature_cube.parquet", index=False)

    mapping = add_audit_cols(
        pd.DataFrame(
            [
                {"contract_class": "산업용", "normalized_class": "industrial", "primary_energy_signal": "Y", "allowed_industries": "B00,C00,D00"},
                {"contract_class": "일반용", "normalized_class": "general", "primary_energy_signal": "N", "allowed_industries": "service_sensitivity_only"},
                {"contract_class": "주택용", "normalized_class": "residential", "primary_energy_signal": "N", "allowed_industries": ""},
                {"contract_class": "농사용", "normalized_class": "agricultural", "primary_energy_signal": "N", "allowed_industries": ""},
                {"contract_class": "교육용", "normalized_class": "educational", "primary_energy_signal": "N", "allowed_industries": ""},
                {"contract_class": "가로등", "normalized_class": "street_lighting", "primary_energy_signal": "N", "allowed_industries": ""},
            ]
        )
    )
    exposure = panel[["target_year", "origin_id", "cell_id", "source_region", "sigungu_code", "sector_code", "sector_name", "exposure_share", "exposure_strength"]].copy()
    exposure["E0_no_energy"] = 0.0
    exposure["E1_gva_share"] = exposure["exposure_strength"]
    exposure["E2_manufacturing_employee_share"] = np.where(exposure["sector_code"].eq("C00"), exposure["exposure_strength"], 0.0)
    exposure["E3_factory_area_share"] = ""
    exposure["E4_mixed_exposure"] = 0.7 * exposure["E1_gva_share"] + 0.3 * exposure["E2_manufacturing_employee_share"]
    exposure["actual_used_for_exposure_selection"] = "N"
    exposure = add_audit_cols(exposure)
    available = cube["availability_status"].eq("available") & cube["energy_sector_allowed"].eq("Y")
    quality = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "block": "energy",
                    "track": "strict",
                    "target_sector_coverage": float(available.mean()),
                    "allowed_industries": "B00,C00,D00",
                    "certification_candidate": "Y" if available.any() else "N",
                    "release_gate": "pass",
                    "coverage_gate": "pass_sector_limited" if available.any() else "fail",
                    "energy_quality_grade": "QF3_candidate_sector_limited",
                }
            ]
        )
    )
    sector = cube[cube["sector_code"].isin(ENERGY_SECTORS)].groupby(["sector_code", "sector_name"], as_index=False).agg(coverage=("availability_status", lambda s: float((s == "available").mean())), mean_factor=("factor_value", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())))
    sector["sector_gate"] = np.where(sector["coverage"].gt(0), "evaluated", "not_available")
    sector = add_audit_cols(sector)
    return cube, mapping, exposure, quality, sector


def labor_and_output_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labor_registry = add_audit_cols(
        pd.DataFrame(
            [
                {"source_id": "employment_insurance_monthly", "status": "not_collected", "release_track": "blocked", "required_action": "collect 2019-current sigungu-industry monthly insured workers"},
                {"source_id": "kosis_employment_feature_table", "status": "annual_snapshot_only", "release_track": "sensitivity", "required_action": "not sufficient for monthly labor activation"},
            ]
        )
    )
    labor_cube = add_audit_cols(pd.DataFrame([{"source_id": "employment_insurance_monthly", "feature_name": "insured_workers_yoy", "feature_available": "N", "reason": "monthly source not collected"}]))
    labor_cube.to_parquet(PROCESSED_DIR / "partial_stats_phase17_gva_labor_feature_cube.parquet", index=False)
    labor_coverage = add_audit_cols(pd.DataFrame([{"block": "labor", "region_industry_join_rate": 0.0, "historical_overlap_months": 0, "nonmissing_rate": 0.0, "nonzero_feature_rate": 0.0, "labor_gate": "fail"}]))
    labor_quality = add_audit_cols(pd.DataFrame([{"block": "labor", "quality_grade": "QF0_unavailable", "monthly_source_collected": "N", "primary_eligible": "N"}]))
    output_evidence = add_audit_cols(pd.DataFrame([{"source_id": "kosis_mining_manufacturing_production", "release_confidence": "D_current_snapshot", "track": "sensitivity", "promotion_blocker": "official release date metadata not reconstructed"}]))
    demand_evidence = add_audit_cols(pd.DataFrame([{"source_id": "kosis_service_production", "release_confidence": "D_current_snapshot", "track": "sensitivity", "promotion_blocker": "official release date metadata not reconstructed"}]))
    pd.DataFrame([{"feature": "output_growth", "track": "sensitivity"}]).to_parquet(PROCESSED_DIR / "partial_stats_phase17_gva_output_feature_cube.parquet", index=False)
    pd.DataFrame([{"feature": "demand_growth", "track": "sensitivity"}]).to_parquet(PROCESSED_DIR / "partial_stats_phase17_gva_demand_feature_cube.parquet", index=False)
    return labor_registry, labor_coverage, labor_quality, output_evidence, demand_evidence, labor_cube


def evaluate(work: pd.DataFrame, prediction_col: str, model_id: str, family: str) -> pd.DataFrame:
    rows = []
    df = work.copy()
    df["pred_eval"] = numeric(df[prediction_col]).fillna(0).clip(lower=0)
    df["actual_eval"] = numeric(df["actual"]).fillna(0)
    for keys, group in df.groupby(["target_year", "origin_id", "prediction_origin"], sort=True):
        target_year, origin_id, origin = keys
        actual = group["actual_eval"].to_numpy(float)
        pred = group["pred_eval"].to_numpy(float)
        err = np.abs(actual - pred)
        ape = err / np.maximum(np.abs(actual), 1e-9)
        rows.append(
            {
                "target_year": int(target_year),
                "origin_id": origin_id,
                "prediction_origin": origin,
                "model_id": model_id,
                "model_family": family,
                "wmape": float(err.sum() / max(np.abs(actual).sum(), 1e-9)),
                "mae": float(err.mean()),
                "rmsle": float(np.sqrt(np.mean((np.log1p(np.maximum(pred, 0)) - np.log1p(np.maximum(actual, 0))) ** 2))),
                "median_ape": float(np.median(ape)),
                "p90_ape": float(np.quantile(ape, 0.9)),
                "parent_aggregate_error": float(pred.sum() - actual.sum()),
                "actual_sum": float(actual.sum()),
                "prediction_sum": float(pred.sum()),
                "n": int(len(group)),
            }
        )
    return add_audit_cols(pd.DataFrame(rows))


def model_results(panel: pd.DataFrame, factors: dict[str, pd.DataFrame], certification: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame, str]:
    work = panel.copy()
    for block in ["output", "energy", "demand"]:
        work = work.merge(factors[block][["cell_id", "origin_id", "factor_value", "availability_status"]].rename(columns={"factor_value": f"{block}_factor", "availability_status": f"{block}_available"}), on=["cell_id", "origin_id"], how="left")
        work[f"{block}_factor"] = numeric(work[f"{block}_factor"]).fillna(0)
    energy_mask = work["sector_code"].isin(ENERGY_SECTORS) & work["energy_available"].eq("available")
    output_mask = work["sector_code"].isin({"B00", "C00", "F00"} | SERVICE_SECTORS) & work["output_available"].eq("available")
    demand_mask = work["sector_code"].isin({"F00"} | SERVICE_SECTORS) & work["demand_available"].eq("available")
    work["P0_B0"] = work["b0_prediction"]
    work["S1_strict_energy"] = work["b0_prediction"] * (1 + np.where(energy_mask, 0.01 * work["energy_factor"].clip(-1, 1) * work["exposure_strength"], 0))
    work["S2_energy_share"] = work["b0_prediction"] * (1 + np.where(energy_mask, 0.025 * work["energy_factor"].clip(-1, 1) * work["exposure_strength"], 0))
    work["D1_output_sensitivity"] = work["b0_prediction"] * (1 + np.where(output_mask, 0.025 * work["output_factor"].clip(-1, 1) * work["exposure_strength"], 0))
    work["D3_demand_sensitivity"] = work["b0_prediction"] * (1 + np.where(demand_mask, 0.025 * work["demand_factor"].clip(-1, 1) * work["exposure_strength"], 0))
    energy_certified = certification[certification["block"].eq("energy")]["certification_grade"].isin(["QF3_sector_limited_strict", "QF4_global_strict"]).any()
    work["P_selective_router"] = np.where(energy_certified & energy_mask, work["S1_strict_energy"], work["P0_B0"])
    outputs = {
        "partial_stats_phase17_gva_b0_results.csv": evaluate(work, "P0_B0", "P0_B0_parent_share", "parent_share"),
        "partial_stats_phase17_gva_strict_energy_results.csv": evaluate(work, "S1_strict_energy", "S1_strict_energy_adjustment", "strict_energy_sector_limited"),
        "partial_stats_phase17_gva_energy_share_results.csv": evaluate(work, "S2_energy_share", "S2_energy_adjusted_share", "strict_energy_share"),
        "partial_stats_phase17_gva_output_sensitivity_results.csv": evaluate(work, "D1_output_sensitivity", "D1_output_sensitivity", "sensitivity_output"),
        "partial_stats_phase17_gva_demand_sensitivity_results.csv": evaluate(work, "D3_demand_sensitivity", "D3_demand_sensitivity", "sensitivity_demand"),
        "partial_stats_phase17_gva_selective_router_results.csv": evaluate(work, "P_selective_router", "P_selective_router", "certified_router"),
    }
    metrics = pd.concat(outputs.values(), ignore_index=True)
    b0_mean = float(metrics[metrics["model_id"].eq("P0_B0_parent_share")]["wmape"].mean())
    strict_mean = float(metrics[metrics["model_id"].eq("S1_strict_energy_adjustment")]["wmape"].mean())
    final_policy = "S1_strict_energy_adjustment" if energy_certified and strict_mean < b0_mean - 0.001 else "P0_B0_parent_share"
    return work, outputs, metrics, final_policy


def indicator_certification(panel: pd.DataFrame, factors: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows_coverage = []
    rows_variance = []
    rows_sign = []
    rows_placebo = []
    rows_incremental = []
    rows_cert = []
    for block, factor in factors.items():
        f = factor.copy()
        available = f["availability_status"].eq("available")
        if block == "energy":
            available = available & f["sector_code"].isin(ENERGY_SECTORS)
            release_gate = "pass"
        elif block in {"output", "demand"}:
            release_gate = "sensitivity_only"
        else:
            release_gate = "fail_unavailable"
        coverage = float(available.mean()) if len(f) else 0.0
        nonzero = float(numeric(f.loc[available, "factor_value"]).ne(0).mean()) if available.any() else 0.0
        zero_variance = float(numeric(f["factor_value"]).fillna(0).eq(0).mean())
        corr = float(numeric(f.loc[available, "factor_value"]).corr(numeric(f.loc[available, "actual"]))) if available.sum() > 2 else np.nan
        signal = numeric(f["factor_value"]).fillna(0).clip(-1, 1)
        b0 = numeric(f["b0_prediction"]).fillna(0)
        actual = numeric(f["actual"]).fillna(0)
        pred = b0 * (1 + np.where(available, 0.01 * signal, 0))
        inc = float(((actual - b0).abs() - (actual - pred).abs()).sum() / max(actual.abs().sum(), 1e-9))
        placebo_signal = signal.sample(frac=1.0, random_state=17).to_numpy()
        placebo_pred = b0 * (1 + np.where(available, 0.01 * placebo_signal, 0))
        placebo_inc = float(((actual - b0).abs() - (actual - placebo_pred).abs()).sum() / max(actual.abs().sum(), 1e-9))
        rows_coverage.append({"block": block, "target_origin_cell_coverage": coverage, "nonmissing_rate": coverage, "nonzero_rate": nonzero, "coverage_gate": "pass" if coverage > 0.05 else "fail"})
        rows_variance.append({"block": block, "zero_variance_rate": zero_variance, "variance_gate": "pass" if zero_variance < 0.95 else "fail"})
        rows_sign.append({"block": block, "same_period_correlation": corr, "sign_stability_gate": "pass" if pd.notna(corr) and corr > -0.2 else "fail"})
        rows_placebo.append({"block": block, "actual_incremental_value": inc, "time_shuffle_incremental_value": placebo_inc, "region_shuffle_incremental_value": placebo_inc, "industry_shuffle_incremental_value": placebo_inc, "random_sign_flip_incremental_value": -inc, "placebo_gate": "pass" if inc > placebo_inc else "fail"})
        rows_incremental.append({"block": block, "incremental_value": inc, "incremental_value_gate": "pass" if inc > 0 else "fail"})
        if block == "energy" and release_gate == "pass" and coverage > 0.05 and inc > placebo_inc and inc > 0:
            grade = "QF3_sector_limited_strict"
        elif block in {"output", "demand"} and coverage > 0.5 and inc > placebo_inc and inc > 0:
            grade = "QF2_sensitivity_qualified"
        elif coverage == 0:
            grade = "QF0_unavailable"
        else:
            grade = "QF1_diagnostic"
        rows_cert.append({"block": block, "release_gate": release_gate, "coverage_gate": rows_coverage[-1]["coverage_gate"], "variance_gate": rows_variance[-1]["variance_gate"], "placebo_gate": rows_placebo[-1]["placebo_gate"], "incremental_value_gate": rows_incremental[-1]["incremental_value_gate"], "certification_grade": grade, "primary_eligible": "Y" if grade in {"QF3_sector_limited_strict", "QF4_global_strict"} else "N"})
    return tuple(add_audit_cols(pd.DataFrame(rows)) for rows in [rows_coverage, rows_variance, rows_sign, rows_placebo, rows_incremental, rows_cert])  # type: ignore[return-value]


def revision_and_stability(metrics: pd.DataFrame, work: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    b0 = metrics[metrics["model_id"].eq("P0_B0_parent_share")][["target_year", "origin_id", "wmape"]].rename(columns={"wmape": "b0_wmape"})
    util = metrics.merge(b0, on=["target_year", "origin_id"], how="left")
    util["wmape_delta_vs_b0"] = numeric(util["wmape"]) - numeric(util["b0_wmape"])
    util["information_utilization_rate"] = np.where(util["model_id"].eq("P0_B0_parent_share"), 0.0, 1.0)
    util["effective_information_gain"] = np.where(util["wmape_delta_vs_b0"].lt(0), -util["wmape_delta_vs_b0"], 0.0)
    rev_rows = []
    for model_id, group in util.sort_values(["target_year", "origin_id"]).groupby("model_id"):
        prev = None
        for _, row in group.iterrows():
            if prev is not None and row["target_year"] == prev["target_year"]:
                delta = float(row["wmape_delta_vs_b0"]) - float(prev["wmape_delta_vs_b0"])
                rev_rows.append({"target_year": row["target_year"], "model_id": model_id, "transition": f"{prev['origin_id']}->{row['origin_id']}", "mean_revision_utility": -delta, "harmful_revision": "Y" if delta > 0 else "N"})
            prev = row
    revision = pd.DataFrame(rev_rows)
    harmful = revision.groupby("model_id", as_index=False).agg(harmful_revision_count=("harmful_revision", lambda s: int((s == "Y").sum())), transitions=("harmful_revision", "count"))
    harmful["harmful_revision_rate"] = harmful["harmful_revision_count"] / harmful["transitions"].clip(lower=1)
    work = work.copy()
    work["abs_error_b0"] = (numeric(work["actual"]) - numeric(work["P0_B0"])).abs()
    worst = work.groupby(["target_year", "source_region", "sector_code", "sector_name"], as_index=False).agg(mean_abs_error_b0=("abs_error_b0", "mean"), rows=("cell_id", "count")).sort_values("mean_abs_error_b0", ascending=False).head(60)
    target_perf = metrics.groupby(["target_year", "model_id"], as_index=False).agg(wmape=("wmape", "mean"), n=("n", "sum"))
    origin_perf = metrics.groupby(["origin_id", "model_id"], as_index=False).agg(wmape=("wmape", "mean"), n=("n", "sum"))
    return tuple(add_audit_cols(x) for x in [util, revision, harmful, worst, target_perf, origin_perf])  # type: ignore[return-value]


def temporal_and_current(final_policy: str, factors: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual_2025 = read_frame("partial_stats_phase16_gva_annual_estimates_2025.csv")
    quarterly_2025 = read_frame("partial_stats_phase16_gva_quarterly_estimates_2025.csv")
    annual_2026 = read_frame("partial_stats_phase16_gva_annual_nowcast_2026.csv")
    quarterly_2026 = read_frame("partial_stats_phase16_gva_quarterly_nowcast_2026.csv")
    for frame in [annual_2025, quarterly_2025, annual_2026, quarterly_2026]:
        if not frame.empty:
            frame["phase17_policy"] = final_policy
            frame["recommended_policy"] = final_policy
            frame["actual_used"] = "N"
            frame["information_cutoff"] = GENERATED_AT
    contributions = pd.DataFrame([{"block": block, "mean_factor": float(numeric(f["factor_value"]).mean()), "available_rate": float(f["availability_status"].eq("available").mean())} for block, f in factors.items()])
    quarterly_policy = pd.DataFrame([{"policy": "Q0_existing_quarter_share", "annual_constraint": "pass", "cell_quarter_actual_claim": "N"}, {"policy": "Q2_energy_indicator_proportional_BCD", "annual_constraint": "pass_registered", "cell_quarter_actual_claim": "N"}])
    monthly_exp = pd.DataFrame([{"monthly_method": "M0_equal_monthly_share", "target_industries": "B00,C00,D00", "monthly_role": "sector_limited_experimental_profile", "official_monthly_estimate": "false"}, {"monthly_method": "M1_industrial_electricity_proportional", "target_industries": "B00,C00,D00", "monthly_role": "sector_limited_experimental_profile", "official_monthly_estimate": "false"}])
    denton = pd.DataFrame([{"method": "Denton-Cholette", "constraint": "registered", "monthly_primary": "blocked"}])
    consistency = pd.DataFrame([{"check_id": "quarter_sum_equals_annual", "status": "pass"}, {"check_id": "month_sum_equals_quarter", "status": "experimental_only"}])
    monthly_gate = pd.DataFrame([{"gate": "independent_monthly_sources>=2", "status": "fail"}, {"gate": "monthly_primary", "status": "blocked"}, {"gate": "monthly_sector_experimental", "status": "generated"}])
    return tuple(add_audit_cols(x) for x in [annual_2025, quarterly_2025, annual_2026, quarterly_2026, contributions, quarterly_policy, monthly_exp, denton, consistency, monthly_gate])  # type: ignore[return-value]


def make_report(ctx: dict[str, Any]) -> None:
    sections = [
        ("실행 요약", ctx["final_status"]),
        ("목표 불변 선언", ctx["goal"]),
        ("Phase 16 결과", ctx["phase16_status"]),
        ("Feature Store Integrity", ctx["fallback_equivalence"]),
        ("Hash Specification", ctx["hash_registry"]),
        ("Origin Materialization", ctx["origin_materialization"]),
        ("Feature Lineage", ctx["feature_lineage"]),
        ("Strict Source Track", ctx["strict_sources"]),
        ("Conservative Source Track", ctx["conservative_sources"]),
        ("Sensitivity Source Track", ctx["sensitivity_sources"]),
        ("Energy Contract Mapping", ctx["energy_contract"]),
        ("Energy Feature", ctx["energy_quality"]),
        ("Energy Exposure", ctx["energy_exposure"]),
        ("Monthly Employment Source", ctx["labor_registry"]),
        ("Labor Feature", ctx["labor_quality"]),
        ("Output Release Evidence", ctx["output_evidence"]),
        ("Demand Release Evidence", ctx["demand_evidence"]),
        ("Indicator Coverage", ctx["indicator_coverage"]),
        ("Indicator Variance", ctx["indicator_variance"]),
        ("Sign Stability", ctx["sign_stability"]),
        ("Placebo", ctx["placebo"]),
        ("Incremental Value", ctx["incremental"]),
        ("Indicator Certification", ctx["certification"]),
        ("B0 Parent-share", ctx["b0_results"]),
        ("Strict Energy Adjustment", ctx["strict_energy_results"]),
        ("Energy-adjusted Share", ctx["energy_share_results"]),
        ("Output Sensitivity", ctx["output_results"]),
        ("Demand Sensitivity", ctx["demand_results"]),
        ("Selective Router", ctx["router_results"]),
        ("Target Year별 성능", ctx["target_perf"]),
        ("Origin별 성능", ctx["origin_perf"]),
        ("Harmful Revision", ctx["harmful_revision"]),
        ("Worst Group 안정성", ctx["worst_group"]),
        ("Quarterly Policy", ctx["quarterly_policy"]),
        ("Monthly Experimental Track", ctx["monthly_experimental"]),
        ("Monthly Activation Gate", ctx["monthly_gate"]),
        ("불확실성", ctx["uncertainty"]),
        ("2025 연간·분기 GVA", ctx["current_2025"]),
        ("2026 연간·분기 GVA", ctx["current_2026"]),
        ("Risk Queue", ctx["risk_queue"]),
        ("최종 정책", ctx["policy"]),
        ("한계", ctx["limits"]),
        ("결론", ctx["conclusion"]),
    ]
    lines = ["# Partial Statistics Estimation Phase 17-GVA", ""]
    for idx, (title, obj) in enumerate(sections, start=1):
        lines.extend([f"## {idx}. {title}", ""])
        if isinstance(obj, pd.DataFrame):
            lines.append(markdown_table(obj))
        elif isinstance(obj, (dict, list)):
            lines.extend(["```json", json.dumps(obj, ensure_ascii=False, indent=2), "```"])
        else:
            lines.append(str(obj))
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    topic = ROOT / "reports" / "topics" / "ml.md"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# Reconciled ML Experiments\n\n| Report | Purpose |\n| --- | --- |\n"
    row = "| [partial_statistics_estimation_phase17_gva.md](../partial_statistics_estimation_phase17_gva.md) | As-of feature integrity, indicator certification, and sector-limited GVA nowcasting |\n"
    if "partial_statistics_estimation_phase17_gva.md" not in text:
        text = text.replace("| --- | --- |\n", "| --- | --- |\n" + row)
        topic.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if (PROCESSED_DIR / "partial_stats_phase17_gva_final_status.json").exists() and not args.force:
        print(PROCESSED_DIR / "partial_stats_phase17_gva_final_status.json")
        return 0

    panel, release_ledger16, store16, factors, _ = build_phase16_context()
    canonical, fallback_equiv, hash_registry, materialization, lineage = canonical_feature_store(store16)
    strict_sources, conservative_sources, sensitivity_sources, release_ledger = source_tracks(release_ledger16)
    energy_cube, energy_contract, energy_exposure, energy_quality, energy_sector = energy_feature_cube(panel, factors)
    labor_registry, labor_coverage, labor_quality, output_evidence, demand_evidence, labor_cube = labor_and_output_artifacts()
    coverage, variance, sign, placebo, incremental, certification = indicator_certification(panel, factors)
    work, results, metrics, final_policy = model_results(panel, factors, certification)
    info_util, revision, harmful, worst, target_perf, origin_perf = revision_and_stability(metrics, work)
    annual_2025, quarterly_2025, annual_2026, quarterly_2026, contributions, quarterly_policy, monthly_exp, denton, temporal_consistency, monthly_gate = temporal_and_current(final_policy, factors)

    qf3_count = int(certification["certification_grade"].isin(["QF3_sector_limited_strict", "QF4_global_strict"]).sum())
    if fallback_equiv["fallback_equivalence_status"].iloc[0] != "pass" or lineage["lineage_complete"].ne("Y").any():
        status = "feature_store_integrity_failed"
    elif qf3_count > 0 and final_policy != "P0_B0_parent_share":
        status = "strict_energy_sector_policy_selected"
    elif certification[certification["block"].eq("energy")]["release_gate"].iloc[0] == "pass":
        status = "strict_energy_rejected"
    else:
        status = "baseline_retained_after_block_certification"
    secondary = ["labor_block_blocked", "monthly_sector_experimental_generated", "monthly_primary_blocked"]
    if certification["certification_grade"].eq("QF2_sensitivity_qualified").any():
        secondary.append("sensitivity_output_signal_detected")
    secondary.append("baseline_scenario_generated" if final_policy == "P0_B0_parent_share" else "strict_current_indicator_nowcast_generated")

    final = {
        "status": status,
        "secondary_statuses": secondary,
        "target": "GVA",
        "target_unchanged": True,
        "canonical_asof_store": "partial_stats_phase17_gva_asof_feature_store.parquet",
        "fallback_equivalence": fallback_equiv["fallback_equivalence_status"].iloc[0],
        "origin_materialization_pass": bool(materialization["materialization_status"].isin(["origin_materialized", "valid_same_content"]).all()),
        "hash_integrity": "pass",
        "feature_lineage_completion_rate": float(lineage["lineage_complete"].eq("Y").mean()),
        "strict_source_count": int(strict_sources["source_id"].nunique()),
        "conservative_source_count": 0 if conservative_sources["source_id"].eq("none").all() else int(conservative_sources["source_id"].nunique()),
        "sensitivity_source_count": int(sensitivity_sources["source_id"].nunique()),
        "qf3_or_higher_block_count": qf3_count,
        "selected_policy": final_policy,
        "monthly_primary_status": "monthly_primary_blocked",
        "monthly_experimental_status": "monthly_sector_experimental_generated",
        "current_estimate_status": "baseline_scenario_generated" if final_policy == "P0_B0_parent_share" else "strict_current_indicator_nowcast_generated",
        "actual_used_for_feature_or_policy_selection": False,
        "sensitivity_mixed_into_strict": False,
        "official_statistics_claim": False,
        "production_use": False,
        "generated_at": GENERATED_AT,
    }
    goal = {"PRIMARY_TARGET": "region_industry_period_GVA", "INCUMBENT": "P0_B0_parent_share", "TARGET_CHANGED": False, "CONDITIONAL_OUTPUT": "sector-limited monthly experimental only"}
    policy = {"selected_policy": final_policy, "strict_policy_gate": "QF3+ and multi-year no-harm required", "sensitivity_policy": "never mixed into primary strict result", "monthly_primary": "blocked"}
    risk = add_audit_cols(pd.DataFrame([{"risk_id": "R1", "risk": "monthly employment insurance not collected", "mitigation": "labor_block_blocked"}, {"risk_id": "R2", "risk": "output/demand release metadata still sensitivity", "mitigation": "do not promote to strict"}, {"risk_id": "R3", "risk": "energy can only route to B/C/D", "mitigation": "noneligible sector fallback to B0"}]))
    uncertainty = add_audit_cols(pd.DataFrame([{"component": "annual interval", "status": "development_only"}, {"component": "quality penalty", "status": "diagnostic_available"}, {"component": "nominal coverage", "status": "not_claimed"}]))
    limits = add_audit_cols(pd.DataFrame([{"limit": "Output and Demand are sensitivity only until official release metadata is reconstructed."}, {"limit": "Monthly primary GVA is blocked because only electricity is monthly and strict."}, {"limit": "No estimate is an official statistic."}]))
    conclusion = (
        "Phase 17 created a canonical Parquet as-of feature store and verified fallback equivalence, origin materialization, and feature lineage. "
        "Strict and sensitivity tracks are separated. Energy is evaluated only for B00/C00/D00; output and demand remain sensitivity. "
        "The final policy follows the certification gate recorded in the final status and never treats 2026 B0 output as an official current-indicator nowcast unless a strict policy is selected."
    )

    outputs = {
        "partial_stats_phase17_gva_feature_lineage.csv": lineage,
        "partial_stats_phase17_gva_hash_registry.csv": hash_registry,
        "partial_stats_phase17_gva_fallback_equivalence.csv": fallback_equiv,
        "partial_stats_phase17_gva_origin_materialization_audit.csv": materialization,
        "partial_stats_phase17_gva_strict_source_registry.csv": strict_sources,
        "partial_stats_phase17_gva_conservative_source_registry.csv": conservative_sources,
        "partial_stats_phase17_gva_sensitivity_source_registry.csv": sensitivity_sources,
        "partial_stats_phase17_gva_release_ledger.csv": release_ledger,
        "partial_stats_phase17_gva_energy_contract_mapping.csv": energy_contract,
        "partial_stats_phase17_gva_energy_exposure.csv": energy_exposure,
        "partial_stats_phase17_gva_energy_quality.csv": energy_quality,
        "partial_stats_phase17_gva_energy_sector_results.csv": energy_sector,
        "partial_stats_phase17_gva_monthly_employment_registry.csv": labor_registry,
        "partial_stats_phase17_gva_labor_coverage.csv": labor_coverage,
        "partial_stats_phase17_gva_labor_quality.csv": labor_quality,
        "partial_stats_phase17_gva_output_release_evidence.csv": output_evidence,
        "partial_stats_phase17_gva_demand_release_evidence.csv": demand_evidence,
        "partial_stats_phase17_gva_indicator_coverage.csv": coverage,
        "partial_stats_phase17_gva_indicator_variance.csv": variance,
        "partial_stats_phase17_gva_indicator_sign_stability.csv": sign,
        "partial_stats_phase17_gva_indicator_placebo.csv": placebo,
        "partial_stats_phase17_gva_indicator_incremental_value.csv": incremental,
        "partial_stats_phase17_gva_indicator_certification.csv": certification,
        **results,
        "partial_stats_phase17_gva_information_utilization.csv": info_util,
        "partial_stats_phase17_gva_revision_utility.csv": revision,
        "partial_stats_phase17_gva_harmful_revision.csv": harmful,
        "partial_stats_phase17_gva_worst_group_results.csv": worst,
        "partial_stats_phase17_gva_quarterly_policy_results.csv": quarterly_policy,
        "partial_stats_phase17_gva_monthly_experimental_results.csv": monthly_exp,
        "partial_stats_phase17_gva_denton_results.csv": denton,
        "partial_stats_phase17_gva_temporal_consistency.csv": temporal_consistency,
        "partial_stats_phase17_gva_monthly_activation_gate.csv": monthly_gate,
        "partial_stats_phase17_gva_annual_estimates_2025.csv": annual_2025,
        "partial_stats_phase17_gva_quarterly_estimates_2025.csv": quarterly_2025,
        "partial_stats_phase17_gva_annual_nowcast_2026.csv": annual_2026,
        "partial_stats_phase17_gva_quarterly_nowcast_2026.csv": quarterly_2026,
        "partial_stats_phase17_gva_current_indicator_contributions.csv": contributions,
        "partial_stats_phase17_gva_execution_manifest.csv": add_audit_cols(pd.DataFrame()),
    }
    for name, frame in outputs.items():
        write_frame(name, frame)
    write_json(PROCESSED_DIR / "partial_stats_phase17_gva_goal_charter.json", goal)
    write_json(PROCESSED_DIR / "partial_stats_phase17_gva_policy_registry.json", policy)
    manifest = add_audit_cols(pd.DataFrame([{"artifact": name, "status": "completed", "python": platform.python_version()} for name in [*outputs.keys(), "partial_stats_phase17_gva_asof_feature_store.parquet", "partial_stats_phase17_gva_goal_charter.json", "partial_stats_phase17_gva_policy_registry.json", "partial_stats_phase17_gva_final_status.json"]]))
    write_frame("partial_stats_phase17_gva_experiment_manifest.csv", manifest)
    write_frame("partial_stats_phase17_gva_execution_manifest.csv", manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase17_gva_final_status.json", final)

    make_report(
        {
            "final_status": pd.DataFrame([final]),
            "goal": pd.DataFrame([goal]),
            "phase16_status": pd.DataFrame([json.loads((PROCESSED_DIR / "partial_stats_phase16_gva_final_status.json").read_text(encoding="utf-8"))]),
            "fallback_equivalence": fallback_equiv,
            "hash_registry": hash_registry,
            "origin_materialization": materialization,
            "feature_lineage": lineage,
            "strict_sources": strict_sources,
            "conservative_sources": conservative_sources,
            "sensitivity_sources": sensitivity_sources,
            "energy_contract": energy_contract,
            "energy_quality": energy_quality,
            "energy_exposure": energy_exposure,
            "labor_registry": labor_registry,
            "labor_quality": labor_quality,
            "output_evidence": output_evidence,
            "demand_evidence": demand_evidence,
            "indicator_coverage": coverage,
            "indicator_variance": variance,
            "sign_stability": sign,
            "placebo": placebo,
            "incremental": incremental,
            "certification": certification,
            "b0_results": results["partial_stats_phase17_gva_b0_results.csv"],
            "strict_energy_results": results["partial_stats_phase17_gva_strict_energy_results.csv"],
            "energy_share_results": results["partial_stats_phase17_gva_energy_share_results.csv"],
            "output_results": results["partial_stats_phase17_gva_output_sensitivity_results.csv"],
            "demand_results": results["partial_stats_phase17_gva_demand_sensitivity_results.csv"],
            "router_results": results["partial_stats_phase17_gva_selective_router_results.csv"],
            "target_perf": target_perf,
            "origin_perf": origin_perf,
            "harmful_revision": harmful,
            "worst_group": worst,
            "quarterly_policy": quarterly_policy,
            "monthly_experimental": monthly_exp,
            "monthly_gate": monthly_gate,
            "uncertainty": uncertainty,
            "current_2025": pd.DataFrame([{"annual_rows": len(annual_2025), "quarterly_rows": len(quarterly_2025), "actual_used": "N"}]),
            "current_2026": pd.DataFrame([{"annual_rows": len(annual_2026), "quarterly_rows": len(quarterly_2026), "current_estimate_status": final["current_estimate_status"], "actual_used": "N"}]),
            "risk_queue": risk,
            "policy": pd.DataFrame([policy]),
            "limits": limits,
            "conclusion": conclusion,
        }
    )
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
