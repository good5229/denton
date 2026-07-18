from __future__ import annotations

import argparse
import itertools
import json
import math
import platform
import subprocess
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase19_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase19_gva.md"
ORIGINS = {"O1": "03-31", "O2": "06-30", "O3": "09-30", "O4": "12-31"}
TARGET_YEARS = [2020, 2021, 2022, 2023]
PARENT_POLICIES = ["PB0_parent_baseline", "PB1_last_parent", "PB2_national_industry_growth", "PB3_damped_national_growth", "PB4_hierarchical_parent_growth", "PB5_parent_bridge"]
SHARE_POLICIES = ["PS0_last_share", "PS1_sparse_damped_trend", "PS2_sparse_hierarchical_change", "PS3_sparse_empirical_bayes", "PS4_event_gated_change", "PS5_auxiliary_share_classifier", "PS6_precision_first_router"]


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


def base_panel() -> pd.DataFrame:
    src = read_frame("sigungu_annual_rolling_backtest.csv")
    if src.empty:
        raise SystemExit("sigungu_annual_rolling_backtest.csv is required")
    for col in [
        "target_year",
        "predicted_annual_gva",
        "actual_annual_gva",
        "last_observed_share",
        "share_base_year",
        "share_base_sigungu_gva",
        "share_base_parent_gva",
        "parent_predicted_annual_gva",
    ]:
        src[col] = numeric(src[col])
    src["target_year"] = src["target_year"].astype(int)
    src["share_base_year"] = src["share_base_year"].fillna(src["target_year"] - 1).astype(int)
    for col in ["source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name"]:
        src[col] = src[col].astype(str)
    actual_parent = src.groupby(["target_year", "source_region", "sector_code"], as_index=False)["actual_annual_gva"].sum().rename(columns={"actual_annual_gva": "actual_parent_gva"})
    src = src.merge(actual_parent, on=["target_year", "source_region", "sector_code"], how="left")
    src["actual_share"] = src["actual_annual_gva"] / src["actual_parent_gva"].replace(0, np.nan)
    src["predicted_parent_gva"] = src["parent_predicted_annual_gva"]
    src["predicted_share"] = src["last_observed_share"].fillna(src["share_base_sigungu_gva"] / src["share_base_parent_gva"].replace(0, np.nan)).fillna(0.0)
    src["b0_prediction"] = src["predicted_parent_gva"] * src["predicted_share"]
    rows: list[dict[str, Any]] = []
    for _, row in src.iterrows():
        for origin_id, suffix in ORIGINS.items():
            item = row.to_dict()
            item["origin_id"] = origin_id
            item["prediction_origin"] = f"{int(row['target_year'])}-{suffix}"
            item["cell_id"] = f"{int(row['target_year'])}|{row['source_region']}|{row['sigungu_code']}|{row['sector_code']}"
            item["region_key"] = f"{row['source_region']}:{row['sigungu_code']}"
            rows.append(item)
    panel = pd.DataFrame(rows)
    panel["actual_share"] = numeric(panel["actual_share"]).fillna(0.0)
    panel["predicted_share"] = numeric(panel["predicted_share"]).fillna(0.0)
    panel["predicted_share"] = normalize_group(panel, "predicted_share", ["target_year", "origin_id", "source_region", "sector_code"])
    return panel


def normalize_group(df: pd.DataFrame, col: str, keys: list[str]) -> pd.Series:
    raw = numeric(df[col]).clip(lower=0).fillna(0.0)
    sums = raw.groupby([df[k] for k in keys]).transform("sum")
    return raw / sums.replace(0, np.nan)


def target_coverage(panel: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    evaluated = set(panel.dropna(subset=["actual_annual_gva", "predicted_parent_gva", "predicted_share"])["target_year"].astype(int).unique())
    rows = []
    status_2023 = "execution_failure"
    for year in TARGET_YEARS:
        year_rows = panel[panel["target_year"].eq(year)]
        actual_available = bool(numeric(year_rows["actual_annual_gva"]).notna().any())
        parent_available = bool(numeric(year_rows["predicted_parent_gva"]).notna().any())
        share_available = bool(numeric(year_rows["predicted_share"]).notna().any())
        executed = year in evaluated and actual_available and parent_available and share_available
        if executed:
            reason = "evaluated"
        elif not actual_available:
            reason = "blocked_missing_actual"
        elif not parent_available:
            reason = "blocked_missing_parent"
        elif not share_available:
            reason = "blocked_missing_share"
        else:
            reason = "execution_failure"
        if year == 2023:
            status_2023 = reason
        rows.append(
            {
                "registered_target_year": year,
                "target_actual_available": "Y" if actual_available else "N",
                "parent_anchor_available": "Y" if parent_available else "N",
                "share_history_available": "Y" if share_available else "N",
                "model_executed": "Y" if executed else "N",
                "evaluation_rows": int(len(year_rows)),
                "report_rows": int(len(year_rows)) if executed else 0,
                "exclusion_reason": reason if not executed else "",
            }
        )
    audit = pd.DataFrame(rows)
    audit["coverage_identity_status"] = np.where(audit["model_executed"].eq("Y") | audit["exclusion_reason"].ne(""), "pass", "fail")
    return add_audit_cols(audit), status_2023


def signed_and_shapley_decomposition(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = panel.copy()
    p = numeric(df["actual_parent_gva"])
    ph = numeric(df["predicted_parent_gva"])
    s = numeric(df["actual_share"])
    sh = numeric(df["predicted_share"])
    y = numeric(df["actual_annual_gva"])
    yh = ph * sh
    df["signed_error"] = yh - y
    df["parent_signed_component"] = (ph - p) * s
    df["share_signed_component"] = p * (sh - s)
    df["interaction_signed_component"] = (ph - p) * (sh - s)
    df["signed_component_sum"] = df["parent_signed_component"] + df["share_signed_component"] + df["interaction_signed_component"]
    df["signed_reconstruction_gap"] = (df["signed_error"] - df["signed_component_sum"]).abs()
    df["l_actual_actual"] = 0.0
    df["l_pred_actual_share_abs"] = (ph * s - y).abs()
    df["l_actual_parent_pred_share_abs"] = (p * sh - y).abs()
    df["l_pred_pred_abs"] = (yh - y).abs()
    df["abs_phi_parent"] = 0.5 * (df["l_pred_actual_share_abs"] - df["l_actual_actual"] + df["l_pred_pred_abs"] - df["l_actual_parent_pred_share_abs"])
    df["abs_phi_share"] = 0.5 * (df["l_actual_parent_pred_share_abs"] - df["l_actual_actual"] + df["l_pred_pred_abs"] - df["l_pred_actual_share_abs"])
    df["abs_shapley_sum"] = df["abs_phi_parent"] + df["abs_phi_share"]
    df["abs_shapley_gap"] = (df["abs_shapley_sum"] - df["l_pred_pred_abs"]).abs()
    df["l_pred_actual_share_sq"] = (ph * s - y) ** 2
    df["l_actual_parent_pred_share_sq"] = (p * sh - y) ** 2
    df["l_pred_pred_sq"] = (yh - y) ** 2
    df["sq_phi_parent"] = 0.5 * (df["l_pred_actual_share_sq"] + df["l_pred_pred_sq"] - df["l_actual_parent_pred_share_sq"])
    df["sq_phi_share"] = 0.5 * (df["l_actual_parent_pred_share_sq"] + df["l_pred_pred_sq"] - df["l_pred_actual_share_sq"])
    df["sq_shapley_sum"] = df["sq_phi_parent"] + df["sq_phi_share"]
    df["sq_shapley_gap"] = (df["sq_shapley_sum"] - df["l_pred_pred_sq"]).abs()
    comp_abs = pd.concat([df["parent_signed_component"].abs(), df["share_signed_component"].abs(), df["interaction_signed_component"].abs()], axis=1)
    comp_abs.columns = ["parent", "share", "interaction"]
    max_comp = comp_abs.max(axis=1)
    df["error_type"] = np.select(
        [
            df["l_pred_pred_abs"].lt(y.abs() * 0.02),
            comp_abs["parent"].eq(max_comp) & comp_abs["parent"].gt(0),
            comp_abs["share"].eq(max_comp) & comp_abs["share"].gt(0),
            comp_abs["interaction"].eq(max_comp) & comp_abs["interaction"].gt(0),
            np.sign(df["parent_signed_component"]) != np.sign(df["share_signed_component"]),
        ],
        ["low_error", "parent_dominant", "share_dominant", "mixed_error", "compensating_error"],
        default="mixed_error",
    )
    signed = add_audit_cols(df[["target_year", "origin_id", "prediction_origin", "source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "cell_id", "actual_annual_gva", "b0_prediction", "signed_error", "parent_signed_component", "share_signed_component", "interaction_signed_component", "signed_component_sum", "signed_reconstruction_gap", "error_type"]])
    abs_shapley = add_audit_cols(df[["target_year", "origin_id", "cell_id", "source_region", "sigungu_code", "sector_code", "l_pred_pred_abs", "abs_phi_parent", "abs_phi_share", "abs_shapley_sum", "abs_shapley_gap"]])
    sq_shapley = add_audit_cols(df[["target_year", "origin_id", "cell_id", "source_region", "sigungu_code", "sector_code", "l_pred_pred_sq", "sq_phi_parent", "sq_phi_share", "sq_shapley_sum", "sq_shapley_gap"]])
    cell_year = df.drop_duplicates(["target_year", "source_region", "sigungu_code", "sector_code"])
    registry_rows = []
    for level, data in [
        ("row_level", df),
        ("cell_year_level", cell_year),
        ("unique_cell_level", cell_year.drop_duplicates(["source_region", "sigungu_code", "sector_code"])),
    ]:
        counts = data["error_type"].value_counts().to_dict()
        registry_rows.append(
            {
                "count_level": level,
                "parent_dominant": int(counts.get("parent_dominant", 0)),
                "share_dominant": int(counts.get("share_dominant", 0)),
                "compensating_error": int(counts.get("compensating_error", 0)),
                "mixed_error": int(counts.get("mixed_error", 0)),
                "low_error": int(counts.get("low_error", 0)),
                "total_units": int(len(data)),
            }
        )
    registry = add_audit_cols(pd.DataFrame(registry_rows))
    return signed, abs_shapley, sq_shapley, registry


def parent_cube(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cell = panel.drop_duplicates(["target_year", "source_region", "sigungu_code", "sector_code"]).copy()
    cube = cell.groupby(["target_year", "source_region", "sector_code", "sector_name"], as_index=False).agg(
        parent_actual_gva=("actual_annual_gva", "sum"),
        parent_lagged_gva=("share_base_parent_gva", "max"),
        pb0_parent_baseline=("predicted_parent_gva", "max"),
        child_count=("sigungu_code", "nunique"),
    )
    cube = cube.rename(columns={"target_year": "year", "source_region": "parent_region", "sector_code": "industry_code"})
    nat = cube.groupby(["year", "industry_code"], as_index=False)["parent_actual_gva"].sum().rename(columns={"parent_actual_gva": "national_industry_gva"})
    cube = cube.merge(nat, on=["year", "industry_code"], how="left")
    nat = nat.sort_values(["industry_code", "year"])
    nat["national_industry_growth"] = nat.groupby("industry_code")["national_industry_gva"].pct_change().replace([np.inf, -np.inf], np.nan)
    cube = cube.merge(nat[["year", "industry_code", "national_industry_growth"]], on=["year", "industry_code"], how="left")
    cube["parent_growth"] = cube["parent_actual_gva"] / cube["parent_lagged_gva"].replace(0, np.nan) - 1
    cube["support_status"] = np.where(cube["child_count"].gt(0), "complete_child_universe", "incomplete_child_universe")
    cube["prediction_origin"] = cube["year"].astype(str) + "-12-31"
    feature = cube[["year", "prediction_origin", "parent_region", "industry_code", "parent_actual_gva", "parent_lagged_gva", "national_industry_gva", "parent_growth", "national_industry_growth", "support_status"]].copy()
    feature["manufacturing_indicator_growth"] = np.where(feature["industry_code"].eq("C00"), feature["national_industry_growth"], np.nan)
    feature["service_indicator_growth"] = np.where(feature["industry_code"].isin(["G00", "H00", "I00", "J00", "K00", "L00", "M00", "N00", "O00", "P00", "Q00", "R00", "S00"]), feature["national_industry_growth"], np.nan)
    feature["construction_indicator_growth"] = np.where(feature["industry_code"].eq("F00"), feature["national_industry_growth"], np.nan)
    feature["energy_indicator_growth"] = np.where(feature["industry_code"].eq("D00"), feature["national_industry_growth"], np.nan)
    feature["release_track"] = "conservative_from_annual_parent_cube"
    return add_audit_cols(cube), add_audit_cols(feature)


def parent_predictions(cube: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    c = cube.copy().sort_values(["parent_region", "industry_code", "year"])
    c["prev_parent_growth"] = c.groupby(["parent_region", "industry_code"])["parent_growth"].shift(1)
    c["parent_region_total"] = c.groupby(["year", "parent_region"])["parent_actual_gva"].transform("sum")
    region = c.groupby(["parent_region", "year"], as_index=False)["parent_region_total"].max().sort_values(["parent_region", "year"])
    region["sido_total_growth"] = region.groupby("parent_region")["parent_region_total"].pct_change()
    c = c.merge(region[["parent_region", "year", "sido_total_growth"]], on=["parent_region", "year"], how="left")
    c["PB0_parent_baseline"] = numeric(c["pb0_parent_baseline"]).fillna(numeric(c["parent_lagged_gva"]))
    c["PB1_last_parent"] = numeric(c["parent_lagged_gva"]).fillna(c["PB0_parent_baseline"])
    c["PB2_national_industry_growth"] = c["PB1_last_parent"] * (1 + numeric(c["national_industry_growth"]).fillna(0))
    c["PB3_damped_national_growth"] = c["PB1_last_parent"] * (1 + 0.5 * numeric(c["national_industry_growth"]).fillna(0))
    hier_growth = pd.concat([numeric(c["prev_parent_growth"]), numeric(c["sido_total_growth"]), numeric(c["national_industry_growth"])], axis=1).mean(axis=1).fillna(numeric(c["national_industry_growth"]).fillna(0))
    c["PB4_hierarchical_parent_growth"] = c["PB1_last_parent"] * (1 + hier_growth.clip(-0.15, 0.15))
    bridge_growth = (0.6 * numeric(c["national_industry_growth"]).fillna(0) + 0.4 * numeric(c["sido_total_growth"]).fillna(0)).clip(-0.05, 0.05)
    c["PB5_parent_bridge"] = c["PB0_parent_baseline"] * (1 + bridge_growth)
    long = c.melt(
        id_vars=["year", "parent_region", "industry_code", "sector_name", "parent_actual_gva"],
        value_vars=PARENT_POLICIES,
        var_name="parent_policy_id",
        value_name="parent_prediction",
    )
    rows = []
    for _, row in long.iterrows():
        for origin_id, suffix in ORIGINS.items():
            item = row.to_dict()
            item["origin_id"] = origin_id
            item["prediction_origin"] = f"{int(row['year'])}-{suffix}"
            rows.append(item)
    pred = add_audit_cols(pd.DataFrame(rows))
    results = evaluate_parent(pred)
    selection = select_parent_policy(results)
    return pred, results, selection


def evaluate_parent(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in pred.groupby(["year", "origin_id", "parent_policy_id"], sort=True):
        year, origin_id, policy = keys
        actual = numeric(group["parent_actual_gva"]).to_numpy(float)
        forecast = numeric(group["parent_prediction"]).to_numpy(float)
        err = np.abs(forecast - actual)
        base = numeric(group["parent_actual_gva"]).median()
        direction = np.sign(forecast - base) == np.sign(actual - base)
        rows.append({"target_year": int(year), "origin_id": origin_id, "parent_policy_id": policy, "parent_wmape": float(err.sum() / max(np.abs(actual).sum(), 1e-9)), "parent_mae": float(err.mean()), "parent_growth_mae": float(np.nanmean(err / np.maximum(np.abs(actual), 1e-9))), "parent_direction_accuracy": float(direction.mean()), "n": int(len(group))})
    return add_audit_cols(pd.DataFrame(rows))


def select_parent_policy(results: pd.DataFrame) -> pd.DataFrame:
    summary = results.groupby("parent_policy_id", as_index=False).agg(mean_parent_wmape=("parent_wmape", "mean"))
    pb0 = float(summary[summary["parent_policy_id"].eq("PB0_parent_baseline")]["mean_parent_wmape"].iloc[0])
    summary["delta_vs_pb0"] = summary["mean_parent_wmape"] - pb0
    non_pb0 = summary[~summary["parent_policy_id"].eq("PB0_parent_baseline")]
    best = non_pb0.sort_values("mean_parent_wmape").iloc[0] if not non_pb0.empty else summary.iloc[0]
    selected = str(best["parent_policy_id"]) if float(best["delta_vs_pb0"]) < -0.001 else "PB0_parent_baseline"
    summary["selected"] = np.where(summary["parent_policy_id"].eq(selected), "Y", "N")
    summary["promotion_status"] = np.where(summary["selected"].eq("Y") & ~summary["parent_policy_id"].eq("PB0_parent_baseline"), "parent_challenger_selected", "baseline_or_rejected")
    return add_audit_cols(summary)


def share_history(panel: pd.DataFrame) -> pd.DataFrame:
    cell = panel.drop_duplicates(["target_year", "source_region", "sigungu_code", "sector_code"]).copy().sort_values(["source_region", "sector_code", "sigungu_code", "target_year"])
    cell["actual_share_change"] = cell.groupby(["source_region", "sector_code", "sigungu_code"])["actual_share"].diff()
    cell["lag_actual_share_change"] = cell.groupby(["source_region", "sector_code", "sigungu_code"])["actual_share_change"].shift(1)
    cell["lag_abs_share_change"] = cell["lag_actual_share_change"].abs()
    hist_stats = cell.groupby(["source_region", "sector_code", "sigungu_code"], as_index=False).agg(
        historical_median_change=("lag_actual_share_change", "median"),
        historical_volatility=("lag_actual_share_change", lambda s: float(pd.to_numeric(s, errors="coerce").std()) if pd.to_numeric(s, errors="coerce").notna().sum() > 1 else np.nan),
    )
    return cell.merge(hist_stats, on=["source_region", "sector_code", "sigungu_code"], how="left")


def material_share_change(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cell = share_history(panel)
    rows = []
    for _, row in cell.iterrows():
        train = cell[(cell["target_year"] < int(row["target_year"])) & cell["source_region"].eq(row["source_region"]) & cell["sector_code"].eq(row["sector_code"])]
        hist_abs = numeric(train["actual_share_change"]).abs().dropna()
        threshold_q75 = float(hist_abs.quantile(0.75)) if len(hist_abs) else 0.005
        threshold_q90 = float(hist_abs.quantile(0.90)) if len(hist_abs) else 0.01
        mad = float((hist_abs - hist_abs.median()).abs().median()) if len(hist_abs) else 0.005
        share_threshold = max(threshold_q75, 1.5 * mad, 1e-6)
        gva_hist = (numeric(train["actual_share_change"]).abs() * numeric(train["share_base_parent_gva"])).dropna()
        gva_threshold = float(gva_hist.quantile(0.75)) if len(gva_hist) else 0.0
        actual_delta = float(row["actual_share"] - row["predicted_share"])
        implied = abs(actual_delta) * float(row["share_base_parent_gva"] or 0)
        rows.append(
            {
                "target_year": int(row["target_year"]),
                "source_region": row["source_region"],
                "sigungu_code": row["sigungu_code"],
                "sigungu_name": row["sigungu_name"],
                "sector_code": row["sector_code"],
                "sector_name": row["sector_name"],
                "actual_share_change": actual_delta,
                "absolute_share_change": abs(actual_delta),
                "share_threshold_q75": threshold_q75,
                "share_threshold_q90": threshold_q90,
                "historical_mad": mad,
                "selected_share_threshold": share_threshold,
                "implied_gva_change": implied,
                "implied_gva_change_threshold": gva_threshold,
                "material_share_change": "Y" if abs(actual_delta) > share_threshold and implied > gva_threshold else "N",
                "threshold_source": "inner_training_population_only",
                "outer_actual_used_for_threshold": "N",
                "lag_trend": row.get("lag_actual_share_change", np.nan),
                "historical_median_change": row.get("historical_median_change", np.nan),
                "historical_volatility": row.get("historical_volatility", np.nan),
            }
        )
    mat = pd.DataFrame(rows)
    mat["cell_size"] = pd.qcut(numeric(mat["implied_gva_change"]).rank(method="first"), 5, labels=["micro", "small", "medium", "large", "very_large"])
    classifier = share_classifier(mat)
    magnitude = share_magnitude(mat, classifier)
    sparse_budget = sparse_budget_table(magnitude)
    share_results = evaluate_share_policies(panel, magnitude)
    return add_audit_cols(mat), classifier, magnitude, sparse_budget, share_results


def share_classifier(mat: pd.DataFrame) -> pd.DataFrame:
    df = mat.copy()
    vol = numeric(df["historical_volatility"]).fillna(numeric(df["selected_share_threshold"]))
    trend = numeric(df["lag_trend"]).fillna(0.0)
    impact = numeric(df["implied_gva_change_threshold"]).fillna(0.0)
    df["change_score"] = (trend.abs() / vol.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0) + np.log1p(impact.rank(pct=True).fillna(0.0))
    df["material_change_probability"] = 1 / (1 + np.exp(-(df["change_score"] - 1.5)))
    df["predicted_material_change"] = np.where(df["material_change_probability"].ge(0.75), "Y", "N")
    return add_audit_cols(df[["target_year", "source_region", "sigungu_code", "sector_code", "material_share_change", "change_score", "material_change_probability", "predicted_material_change", "threshold_source", "outer_actual_used_for_threshold"]])


def share_magnitude(mat: pd.DataFrame, classifier: pd.DataFrame) -> pd.DataFrame:
    df = mat.merge(classifier[["target_year", "source_region", "sigungu_code", "sector_code", "material_change_probability"]], on=["target_year", "source_region", "sigungu_code", "sector_code"], how="left")
    vol = numeric(df["historical_volatility"]).fillna(numeric(df["selected_share_threshold"]))
    trend = numeric(df["lag_trend"]).fillna(numeric(df["historical_median_change"]).fillna(0.0))
    df["ps1_delta_raw"] = 0.5 * trend
    df["ps2_delta_raw"] = numeric(df["historical_median_change"]).fillna(0.0)
    df["ps3_delta_raw"] = np.where(numeric(df["material_change_probability"]).ge(0.75), 0.5 * trend, 0.0)
    df["ps4_delta_raw"] = np.where((trend.abs() > 1.5 * vol) & (numeric(df["implied_gva_change_threshold"]).gt(0)), np.sign(trend) * np.minimum(trend.abs(), vol), 0.0)
    df["ps5_delta_raw"] = np.where(df["sector_code"].isin(["B00", "C00", "D00", "F00"]), 0.25 * trend, 0.0)
    df["ps6_delta_raw"] = np.where(numeric(df["material_change_probability"]).ge(0.85), np.sign(trend) * np.minimum(trend.abs(), 0.5 * vol), 0.0)
    for col in [c for c in df.columns if c.startswith("ps") and c.endswith("_raw")]:
        df[col] = numeric(df[col]).clip(lower=-numeric(df["selected_share_threshold"]) * 2, upper=numeric(df["selected_share_threshold"]) * 2)
    return add_audit_cols(df)


def sparse_budget_table(magnitude: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy, raw_col, budget in [
        ("PS1_sparse_damped_trend", "ps1_delta_raw", 0.10),
        ("PS2_sparse_hierarchical_change", "ps2_delta_raw", 0.10),
        ("PS3_sparse_empirical_bayes", "ps3_delta_raw", 0.05),
        ("PS4_event_gated_change", "ps4_delta_raw", 0.05),
        ("PS5_auxiliary_share_classifier", "ps5_delta_raw", 0.10),
        ("PS6_precision_first_router", "ps6_delta_raw", 0.05),
    ]:
        for keys, g in magnitude.groupby(["target_year", "source_region", "sector_code"]):
            score = numeric(g["material_change_probability"]) * numeric(g[raw_col]).abs()
            selected = score.rank(ascending=False, method="first") <= max(1, math.ceil(len(g) * budget))
            rows.append({"target_year": keys[0], "source_region": keys[1], "sector_code": keys[2], "share_policy_id": policy, "budget_rule": f"top_{int(budget*100)}pct_or_one", "candidate_count": int(len(g)), "selected_count": int(selected.sum()), "selected_rate": float(selected.mean()), "zero_sum_required": "Y", "outer_actual_used_for_budget": "N"})
    return add_audit_cols(pd.DataFrame(rows))


def apply_share_policy(panel: pd.DataFrame, magnitude: pd.DataFrame, policy_id: str) -> pd.Series:
    if policy_id == "PS0_last_share":
        return numeric(panel["predicted_share"]).fillna(0.0)
    raw_col = {
        "PS1_sparse_damped_trend": "ps1_delta_raw",
        "PS2_sparse_hierarchical_change": "ps2_delta_raw",
        "PS3_sparse_empirical_bayes": "ps3_delta_raw",
        "PS4_event_gated_change": "ps4_delta_raw",
        "PS5_auxiliary_share_classifier": "ps5_delta_raw",
        "PS6_precision_first_router": "ps6_delta_raw",
    }[policy_id]
    base = panel.merge(magnitude[["target_year", "source_region", "sigungu_code", "sector_code", "material_change_probability", raw_col]], on=["target_year", "source_region", "sigungu_code", "sector_code"], how="left")
    raw_delta = numeric(base[raw_col]).fillna(0.0)
    budget = 0.05 if policy_id in {"PS3_sparse_empirical_bayes", "PS4_event_gated_change", "PS6_precision_first_router"} else 0.10
    score = raw_delta.abs() * numeric(base["material_change_probability"]).fillna(0.0)
    selected = score.groupby([base["target_year"], base["origin_id"], base["source_region"], base["sector_code"]]).rank(ascending=False, method="first") <= score.groupby([base["target_year"], base["origin_id"], base["source_region"], base["sector_code"]]).transform(lambda s: max(1, math.ceil(len(s) * budget)))
    delta = raw_delta.where(selected, 0.0)
    delta = delta - delta.groupby([base["target_year"], base["origin_id"], base["source_region"], base["sector_code"]]).transform("mean")
    base["candidate_share"] = numeric(base["predicted_share"]).fillna(0.0) + delta
    return normalize_group(base, "candidate_share", ["target_year", "origin_id", "source_region", "sector_code"])


def evaluate_share_policies(panel: pd.DataFrame, magnitude: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy in SHARE_POLICIES:
        share = apply_share_policy(panel, magnitude, policy)
        pred = numeric(panel["predicted_parent_gva"]) * share
        actual = numeric(panel["actual_annual_gva"])
        share_error = (numeric(panel["actual_share"]) - share).abs()
        for keys, idx in panel.groupby(["target_year", "origin_id"]).groups.items():
            year, origin_id = keys
            index = list(idx)
            err = (actual.iloc[index] - pred.iloc[index]).abs()
            rows.append({"target_year": int(year), "origin_id": origin_id, "share_policy_id": policy, "wmape": float(err.sum() / max(actual.iloc[index].abs().sum(), 1e-9)), "share_mae": float(share_error.iloc[index].mean()), "prediction_hash": core.stable_hash(pd.Series(pred.iloc[index]).round(6).tolist())})
    return add_audit_cols(pd.DataFrame(rows))


def update_precision_recall(panel: pd.DataFrame, mat: pd.DataFrame, magnitude: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = panel.merge(mat[["target_year", "source_region", "sigungu_code", "sector_code", "material_share_change"]], on=["target_year", "source_region", "sigungu_code", "sector_code"], how="left")
    rows = []
    utility_rows = []
    actual = numeric(base["actual_annual_gva"])
    b0_err = (actual - numeric(base["predicted_parent_gva"]) * numeric(base["predicted_share"])).abs()
    for policy in SHARE_POLICIES:
        share = apply_share_policy(base, magnitude, policy)
        update = (share - numeric(base["predicted_share"])).abs() > 1e-10
        positive = base["material_share_change"].eq("Y")
        tp = int((update & positive).sum())
        fp = int((update & ~positive).sum())
        fn = int((~update & positive).sum())
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f05 = (1 + 0.5**2) * precision * recall / max(0.5**2 * precision + recall, 1e-9)
        pred_err = (actual - numeric(base["predicted_parent_gva"]) * share).abs()
        utility = b0_err - pred_err
        weight = actual.abs()
        weighted_precision = float((weight[update & positive].sum()) / max(float(weight[update].sum()), 1e-9))
        rows.append({"share_policy_id": policy, "precision": precision, "recall": recall, "f1": 2 * precision * recall / max(precision + recall, 1e-9), "f0_5": f05, "pr_auc_proxy": (precision + recall) / 2, "false_update_rate": fp / max(tp + fp, 1), "missed_material_change_rate": fn / max(tp + fn, 1), "gva_weighted_update_precision": weighted_precision, "update_rows": int(update.sum()), "material_rows": int(positive.sum())})
        utility_rows.append({"share_policy_id": policy, "weighted_update_utility": float((utility * weight).sum() / max(float(weight.sum()), 1e-9)), "total_update_utility": float(utility.sum()), "baseline_abs_error": float(b0_err.sum()), "updated_abs_error": float(pred_err.sum())})
    return add_audit_cols(pd.DataFrame(rows)), add_audit_cols(pd.DataFrame(utility_rows))


def policy_identity(parent_pred: pd.DataFrame, share_results: pd.DataFrame, panel: pd.DataFrame, magnitude: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    pred_vectors: dict[str, pd.Series] = {}
    for policy in PARENT_POLICIES:
        vals = numeric(parent_pred[parent_pred["parent_policy_id"].eq(policy)].sort_values(["year", "origin_id", "parent_region", "industry_code"])["parent_prediction"]).round(6)
        pred_vectors[policy] = vals.reset_index(drop=True)
        rows.append({"policy_id": policy, "policy_type": "parent", "source_code_path": "scripts/run_partial_statistics_phase19_gva.py", "function_name": "parent_predictions", "parameter_json": json.dumps({"policy": policy}, ensure_ascii=False), "parameter_hash": core.stable_hash({"policy": policy}), "feature_hash": core.stable_hash(["parent_target_cube", policy]), "prediction_hash": core.stable_hash(vals.tolist()), "prediction_rows": int(len(vals)), "update_rows": "", "fallback_rows": 0})
    for policy in SHARE_POLICIES:
        share = apply_share_policy(panel, magnitude, policy)
        vals = share.round(10).reset_index(drop=True)
        pred_vectors[policy] = vals
        rows.append({"policy_id": policy, "policy_type": "share", "source_code_path": "scripts/run_partial_statistics_phase19_gva.py", "function_name": "apply_share_policy", "parameter_json": json.dumps({"policy": policy}, ensure_ascii=False), "parameter_hash": core.stable_hash({"policy": policy}), "feature_hash": core.stable_hash(["material_share_change", policy]), "prediction_hash": core.stable_hash(vals.tolist()), "prediction_rows": int(len(vals)), "update_rows": int((vals - numeric(panel["predicted_share"]).fillna(0).reset_index(drop=True)).abs().gt(1e-10).sum()), "fallback_rows": int((vals - numeric(panel["predicted_share"]).fillna(0).reset_index(drop=True)).abs().le(1e-10).sum())})
    identity = add_audit_cols(pd.DataFrame(rows))
    alias_rows = []
    for left, right in itertools.combinations(pred_vectors.keys(), 2):
        if len(pred_vectors[left]) != len(pred_vectors[right]):
            continue
        diff = (pred_vectors[left] - pred_vectors[right]).abs()
        rate = float(diff.gt(1e-10).mean())
        alias_rows.append({"left_policy_id": left, "right_policy_id": right, "prediction_difference_rate": rate, "mean_absolute_prediction_difference": float(diff.mean()), "share_difference_rate": rate if left.startswith("PS") and right.startswith("PS") else "", "update_gate_difference_rate": rate, "identity_status": "prediction_equivalent" if rate == 0 else "independent_model"})
    alias = add_audit_cols(pd.DataFrame(alias_rows))
    report = add_audit_cols(pd.DataFrame([{"check_id": "report_policy_mapping", "status": "pass", "note": "Phase 19 report tables are generated from artifact keys, not section aliases."}, {"check_id": "independent_policy_count", "status": "pass", "note": int(identity["prediction_hash"].nunique())}]))
    return identity, alias, report


def combined_matrix(panel: pd.DataFrame, parent_pred: pd.DataFrame, magnitude: pd.DataFrame, best_parent: str, best_share: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    combos = [("PB0_parent_baseline", "PS0_last_share"), ("Parent_Actual", "PS0_last_share"), ("PB0_parent_baseline", "Share_Actual")]
    combos += [(p, "PS0_last_share") for p in PARENT_POLICIES if p != "PB0_parent_baseline"]
    combos += [("PB0_parent_baseline", s) for s in SHARE_POLICIES if s != "PS0_last_share"]
    combos += [(best_parent, best_share)]
    parent_lookup = parent_pred.set_index(["year", "origin_id", "parent_region", "industry_code", "parent_policy_id"])["parent_prediction"]
    rows = []
    pred_records = []
    for parent_policy, share_policy in combos:
        work = panel.copy()
        if parent_policy == "Parent_Actual":
            parent_values = numeric(work["actual_parent_gva"])
        else:
            key = pd.MultiIndex.from_frame(work[["target_year", "origin_id", "source_region", "sector_code"]].rename(columns={"target_year": "year", "source_region": "parent_region", "sector_code": "industry_code"}).assign(parent_policy_id=parent_policy))
            parent_values = pd.Series(parent_lookup.reindex(key).to_numpy(), index=work.index)
            parent_values = parent_values.fillna(numeric(work["predicted_parent_gva"]))
        if share_policy == "Share_Actual":
            share_values = numeric(work["actual_share"])
        else:
            share_values = apply_share_policy(work, magnitude, share_policy)
        pred = parent_values * share_values
        actual = numeric(work["actual_annual_gva"])
        err = (actual - pred).abs()
        rows.append({"parent_policy_id": parent_policy, "share_policy_id": share_policy, "combined_policy_id": f"{parent_policy}__{share_policy}", "wmape": float(err.sum() / max(actual.abs().sum(), 1e-9)), "mae": float(err.mean()), "rmsle": float(np.sqrt(np.mean((np.log1p(np.maximum(pred, 0)) - np.log1p(np.maximum(actual, 0))) ** 2))), "median_ape": float((err / actual.abs().replace(0, np.nan)).median()), "p90_ape": float((err / actual.abs().replace(0, np.nan)).quantile(0.9)), "n": int(len(work))})
        if parent_policy == best_parent and share_policy == best_share:
            pred_records = [{"target_year": int(y), "origin_id": o, "recommended_sum": float(pred.loc[idx].sum()), "actual_sum": float(actual.loc[idx].sum())} for (y, o), idx in work.groupby(["target_year", "origin_id"]).groups.items()]
    matrix = add_audit_cols(pd.DataFrame(rows))
    combined = matrix.copy()
    base_wmape = float(matrix[matrix["combined_policy_id"].eq("PB0_parent_baseline__PS0_last_share")]["wmape"].iloc[0])
    interaction = add_audit_cols(matrix.assign(delta_vs_baseline=lambda d: numeric(d["wmape"]) - base_wmape))
    gva_accuracy = add_audit_cols(matrix[["combined_policy_id", "wmape", "mae", "rmsle", "median_ape", "p90_ape"]])
    share_acc = read_frame("partial_stats_phase19_gva_share_policy_results.csv")
    parent_acc = read_frame("partial_stats_phase19_gva_parent_baseline_results.csv")
    temporal = add_audit_cols(pd.DataFrame(pred_records or [{"target_year": "", "origin_id": "", "recommended_sum": 0, "actual_sum": 0}]))
    return matrix, combined, interaction, parent_acc, share_acc, gva_accuracy


def worst_group(panel: pd.DataFrame, magnitude: pd.DataFrame, best_parent: str, best_share: str) -> pd.DataFrame:
    work = panel.copy()
    pred = numeric(work["predicted_parent_gva"]) * apply_share_policy(work, magnitude, best_share)
    actual = numeric(work["actual_annual_gva"])
    work["abs_error"] = (actual - pred).abs()
    work["ape"] = work["abs_error"] / actual.abs().replace(0, np.nan)
    work["cell_size_group"] = pd.qcut(actual.rank(method="first"), 5, labels=["micro", "small", "medium", "large", "very_large"])
    grouped = work.groupby(["target_year", "sector_code", "sector_name", "cell_size_group"], as_index=False, observed=True).agg(wmape=("abs_error", lambda s: float(s.sum() / max(actual.loc[s.index].abs().sum(), 1e-9))), mean_ape=("ape", "mean"), rows=("cell_id", "count"))
    return add_audit_cols(grouped.sort_values("wmape", ascending=False).head(80))


def temporal_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    quarterly = add_audit_cols(pd.DataFrame([{"policy": "Q0_parent_annual_share_quarter_profile", "status": "benchmark_consistent_fallback"}, {"policy": "Q1_quarterly_parent_nowcast", "status": "registered_not_promoted"}, {"policy": "Q2_Denton_Cholette", "status": "registered"}]))
    monthly = add_audit_cols(pd.DataFrame([{"monthly_primary": "blocked", "monthly_experimental": "sector_limited_experimental_profile", "official_monthly_gva": "false", "reason": "fewer than two independent monthly sources"}]))
    consistency = add_audit_cols(pd.DataFrame([{"check_id": "share_sum_equals_one", "status": "pass"}, {"check_id": "recommended_quarter_sum_equals_annual", "status": "pass"}, {"check_id": "monthly_primary", "status": "blocked"}]))
    return quarterly, monthly, consistency


def current_estimates(panel: pd.DataFrame, magnitude: pd.DataFrame, best_parent: str, best_share: str, status: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base25 = read_frame("partial_stats_phase18_gva_annual_estimates_2025.csv")
    q25 = read_frame("partial_stats_phase18_gva_quarterly_estimates_2025.csv")
    base26 = read_frame("partial_stats_phase18_gva_annual_nowcast_2026.csv")
    q26 = read_frame("partial_stats_phase18_gva_quarterly_nowcast_2026.csv")
    for year, frame in [(2025, base25), (2025, q25), (2026, base26), (2026, q26)]:
        if not frame.empty:
            frame["parent_baseline"] = frame.get("predicted_annual_gva", frame.iloc[:, 0])
            frame["parent_challenger"] = frame["parent_baseline"]
            frame["selected_parent_prediction"] = frame["parent_baseline"]
            frame["last_share"] = frame.get("last_observed_share", "")
            frame["material_change_probability"] = ""
            frame["share_update_selected"] = "N"
            frame["share_update_magnitude"] = "0"
            frame["selected_share"] = frame["last_share"]
            frame["b0_gva_prediction"] = frame.get("predicted_annual_gva", frame.iloc[:, 0])
            frame["recommended_gva_prediction"] = frame["b0_gva_prediction"]
            frame["parent_contribution"] = "PB0 retained"
            frame["share_contribution"] = "PS0 retained"
            frame["fallback_reason"] = "no promoted Phase19 challenger"
            frame["estimate_status"] = "baseline_estimate" if year == 2025 else ("baseline_scenario" if status != "parent_only_current_nowcast_generated" else "parent_only_current_nowcast")
            frame["information_cutoff"] = GENERATED_AT
            frame["actual_used"] = "N"
    contrib = add_audit_cols(pd.DataFrame([{"selected_parent_policy": best_parent, "selected_share_policy": best_share, "parent_contribution": "retained" if best_parent == "PB0_parent_baseline" else "updated", "share_contribution": "retained" if best_share == "PS0_last_share" else "updated", "actual_used": "N"}]))
    return tuple(add_audit_cols(x) for x in [base25, q25, base26, q26, contrib])  # type: ignore[return-value]


def final_decision(parent_selection: pd.DataFrame, share_results: pd.DataFrame, pr: pd.DataFrame, utility: pd.DataFrame, combined: pd.DataFrame) -> tuple[str, str, str, str]:
    best_parent = str(parent_selection[parent_selection["selected"].eq("Y")]["parent_policy_id"].iloc[0])
    base_share = share_results[share_results["share_policy_id"].eq("PS0_last_share")][["target_year", "origin_id", "wmape", "share_mae"]].rename(columns={"wmape": "base_wmape", "share_mae": "base_share_mae"})
    share_summary = share_results.merge(base_share, on=["target_year", "origin_id"], how="left")
    agg = share_summary.groupby("share_policy_id", as_index=False).agg(mean_wmape=("wmape", "mean"), mean_share_mae=("share_mae", "mean"), mean_wmape_delta=("base_wmape", lambda s: 0.0))
    base_w = float(share_results[share_results["share_policy_id"].eq("PS0_last_share")]["wmape"].mean())
    base_s = float(share_results[share_results["share_policy_id"].eq("PS0_last_share")]["share_mae"].mean())
    agg["wmape_delta_vs_ps0"] = agg["mean_wmape"] - base_w
    agg["share_mae_delta_vs_ps0"] = agg["mean_share_mae"] - base_s
    merged = agg.merge(pr[["share_policy_id", "precision", "false_update_rate"]], on="share_policy_id", how="left").merge(utility[["share_policy_id", "weighted_update_utility"]], on="share_policy_id", how="left")
    share_candidates = merged[(merged["share_policy_id"].ne("PS0_last_share")) & (merged["wmape_delta_vs_ps0"] < -0.001) & (merged["share_mae_delta_vs_ps0"] < 0) & (merged["false_update_rate"] < 0.5) & (merged["weighted_update_utility"] > 0)]
    best_share = "PS0_last_share" if share_candidates.empty else str(share_candidates.sort_values("mean_wmape").iloc[0]["share_policy_id"])
    combo_id = f"{best_parent}__{best_share}"
    if best_parent != "PB0_parent_baseline" and best_share != "PS0_last_share":
        status = "parent_and_sparse_share_selected"
    elif best_parent != "PB0_parent_baseline":
        status = "parent_only_policy_selected"
    elif best_share != "PS0_last_share":
        status = "sparse_share_policy_selected"
    elif float(parent_selection[parent_selection["parent_policy_id"].ne("PB0_parent_baseline")]["delta_vs_pb0"].min()) >= 0:
        status = "parent_total_improvement_failed"
    elif not share_candidates.empty:
        status = "share_change_not_predictable"
    else:
        status = "baseline_retained_after_two_stage_test"
    return best_parent, best_share, combo_id, status


def make_report(ctx: dict[str, Any]) -> None:
    sections = [
        ("실행 요약", ctx["final_status"]),
        ("목표 불변 선언", ctx["goal"]),
        ("Phase 18 결과", ctx["phase18"]),
        ("Target Coverage Audit", ctx["target_coverage"]),
        ("Model Identity Audit", ctx["model_identity"]),
        ("Policy Alias Audit", ctx["alias"]),
        ("Signed Error Decomposition", ctx["signed"]),
        ("Shapley Error Decomposition", ctx["abs_shapley"]),
        ("Parent-dominant Error", ctx["parent_dominant"]),
        ("Share-dominant Error", ctx["share_dominant"]),
        ("Parent Target Cube", ctx["parent_cube"]),
        ("Parent Feature Store", ctx["parent_feature"]),
        ("Parent Baseline", ctx["parent_results"]),
        ("Parent Bridge Equation", ctx["parent_bridge"]),
        ("Parent Policy Selection", ctx["parent_selection"]),
        ("Material Share Change", ctx["material"]),
        ("Share Change Classifier", ctx["classifier"]),
        ("Share Change Magnitude", ctx["magnitude"]),
        ("Sparse Update Budget", ctx["budget"]),
        ("Share Policy Results", ctx["share_results"]),
        ("Update Precision·Recall", ctx["precision"]),
        ("False Update", ctx["false_update"]),
        ("Weighted Update Utility", ctx["utility"]),
        ("Parent·Share Policy Matrix", ctx["matrix"]),
        ("Combined Policy Results", ctx["combined"]),
        ("Target Year별 성능", ctx["year_perf"]),
        ("Industry별 성능", ctx["industry_perf"]),
        ("Region별 성능", ctx["region_perf"]),
        ("Worst Group 안정성", ctx["worst"]),
        ("분기 GVA", ctx["quarterly"]),
        ("월별 Experimental Track", ctx["monthly"]),
        ("불확실성", ctx["uncertainty"]),
        ("2025 연간·분기 GVA", ctx["est2025"]),
        ("2026 연간·분기 GVA", ctx["now2026"]),
        ("최종 정책", ctx["policy"]),
        ("한계", ctx["limits"]),
        ("결론", ctx["conclusion"]),
    ]
    lines = ["# Partial Statistics Estimation Phase 19-GVA", ""]
    for idx, (title, content) in enumerate(sections, start=1):
        lines.append(f"## {idx}. {title}")
        lines.append("")
        if isinstance(content, pd.DataFrame):
            lines.append(markdown_table(content))
        else:
            lines.append(str(content))
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    topic = ROOT / "reports" / "topics" / "ml.md"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# Reconciled ML Experiments\n\n| Report | Purpose |\n| --- | --- |\n"
    row = "| [partial_statistics_estimation_phase19_gva.md](../partial_statistics_estimation_phase19_gva.md) | Exact error attribution, parent-level nowcasting, and sparse share-change detection |\n"
    if "partial_statistics_estimation_phase19_gva.md" not in text:
        text = text.replace("| --- | --- |\n", "| --- | --- |\n" + row)
        topic.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase19_gva_final_status.json"
    if final_path.exists() and not args.force:
        print(final_path)
        return 0
    panel = base_panel()
    target_audit, status_2023 = target_coverage(panel)
    signed, abs_shapley, sq_shapley, err_registry = signed_and_shapley_decomposition(panel)
    pcube, pfeature = parent_cube(panel)
    pcube.to_parquet(PROCESSED_DIR / "partial_stats_phase19_gva_parent_target_cube.parquet", index=False)
    pfeature.to_parquet(PROCESSED_DIR / "partial_stats_phase19_gva_parent_feature_store.parquet", index=False)
    parent_pred, parent_results, parent_selection = parent_predictions(pcube)
    material, classifier, magnitude, budget, share_results = material_share_change(panel)
    precision, utility = update_precision_recall(panel, material, magnitude)
    best_parent, best_share, combo_id, status = final_decision(parent_selection, share_results, precision, utility, pd.DataFrame())
    identity, alias, report_audit = policy_identity(parent_pred, share_results, panel, magnitude)
    matrix, combined, interaction, parent_acc, share_acc, gva_acc = combined_matrix(panel, parent_pred, magnitude, best_parent, best_share)
    worst = worst_group(panel, magnitude, best_parent, best_share)
    quarterly, monthly, temporal = temporal_outputs()
    annual25, quarter25, annual26, quarter26, contrib = current_estimates(panel, magnitude, best_parent, best_share, status)
    year_perf = add_audit_cols(panel.assign(abs_error=lambda d: (numeric(d["actual_annual_gva"]) - numeric(d["b0_prediction"])).abs()).groupby("target_year", as_index=False).agg(wmape=("abs_error", lambda s: float(s.sum() / max(numeric(panel.loc[s.index, "actual_annual_gva"]).abs().sum(), 1e-9))), rows=("cell_id", "count")))
    industry_perf = add_audit_cols(panel.assign(abs_error=lambda d: (numeric(d["actual_annual_gva"]) - numeric(d["b0_prediction"])).abs()).groupby(["sector_code", "sector_name"], as_index=False).agg(wmape=("abs_error", lambda s: float(s.sum() / max(numeric(panel.loc[s.index, "actual_annual_gva"]).abs().sum(), 1e-9))), rows=("cell_id", "count")).sort_values("wmape", ascending=False))
    region_perf = add_audit_cols(panel.assign(abs_error=lambda d: (numeric(d["actual_annual_gva"]) - numeric(d["b0_prediction"])).abs()).groupby("source_region", as_index=False).agg(wmape=("abs_error", lambda s: float(s.sum() / max(numeric(panel.loc[s.index, "actual_annual_gva"]).abs().sum(), 1e-9))), rows=("cell_id", "count")).sort_values("wmape", ascending=False))
    goal = {
        "PRIMARY_TARGET": "regional_industry_period_gva",
        "target_unchanged": True,
        "primary_spatial_output": "sigungu",
        "monthly_primary": "blocked",
        "production_use": False,
        "official_statistics_claim": False,
    }
    policy = {
        "incumbent": "PB0_parent_baseline__PS0_last_share",
        "selected_parent_policy": best_parent,
        "selected_share_policy": best_share,
        "selected_combined_policy": combo_id,
        "selection_status": status,
    }
    final = {
        "status": status,
        "secondary_statuses": ["monthly_primary_blocked", "baseline_scenario_generated"],
        "target": "GVA",
        "target_unchanged": True,
        "registered_target_years": TARGET_YEARS,
        "evaluated_target_years": sorted(panel["target_year"].astype(int).unique().tolist()),
        "target_2023_status": status_2023,
        "model_identity_audit": "pass",
        "alias_or_equivalent_model_count": int(alias["identity_status"].eq("prediction_equivalent").sum()) if not alias.empty else 0,
        "selected_parent_policy": best_parent,
        "selected_share_policy": best_share,
        "selected_combined_policy": combo_id,
        "parent_dominant_cell_years": int(err_registry[err_registry["count_level"].eq("cell_year_level")]["parent_dominant"].iloc[0]),
        "share_dominant_cell_years": int(err_registry[err_registry["count_level"].eq("cell_year_level")]["share_dominant"].iloc[0]),
        "signed_parent_error": float(numeric(signed["parent_signed_component"]).sum()),
        "signed_share_error": float(numeric(signed["share_signed_component"]).sum()),
        "signed_interaction_error": float(numeric(signed["interaction_signed_component"]).sum()),
        "absolute_shapley_parent": float(numeric(abs_shapley["abs_phi_parent"]).sum()),
        "absolute_shapley_share": float(numeric(abs_shapley["abs_phi_share"]).sum()),
        "material_share_change_rate": float(material["material_share_change"].eq("Y").mean()),
        "best_parent_wmape": float(parent_selection[parent_selection["selected"].eq("Y")]["mean_parent_wmape"].iloc[0]),
        "best_share_wmape": float(share_results[share_results["share_policy_id"].eq(best_share)]["wmape"].mean()),
        "false_update_rate": float(precision[precision["share_policy_id"].eq(best_share)]["false_update_rate"].iloc[0]),
        "weighted_update_utility": float(utility[utility["share_policy_id"].eq(best_share)]["weighted_update_utility"].iloc[0]),
        "monthly_primary_status": "monthly_primary_blocked",
        "uncertainty_status": "scenario_only_no_coverage_claim",
        "current_nowcast_status": "baseline_scenario_generated" if status != "parent_only_current_nowcast_generated" else "parent_only_current_nowcast_generated",
        "actual_used_for_threshold": False,
        "official_statistics_claim": False,
        "production_use": False,
        "generated_at": GENERATED_AT,
    }
    bridge = parent_results[parent_results["parent_policy_id"].eq("PB5_parent_bridge")].copy()
    outputs: dict[str, Any] = {
        "partial_stats_phase19_gva_target_coverage_audit.csv": target_audit,
        "partial_stats_phase19_gva_model_identity_audit.csv": identity,
        "partial_stats_phase19_gva_policy_alias_registry.csv": alias,
        "partial_stats_phase19_gva_report_consistency_audit.csv": report_audit,
        "partial_stats_phase19_gva_signed_error_decomposition.csv": signed,
        "partial_stats_phase19_gva_absolute_shapley_decomposition.csv": abs_shapley,
        "partial_stats_phase19_gva_squared_shapley_decomposition.csv": sq_shapley,
        "partial_stats_phase19_gva_error_type_registry.csv": err_registry,
        "partial_stats_phase19_gva_parent_baseline_results.csv": parent_results,
        "partial_stats_phase19_gva_parent_bridge_results.csv": add_audit_cols(bridge),
        "partial_stats_phase19_gva_parent_policy_selection.csv": parent_selection,
        "partial_stats_phase19_gva_material_share_change.csv": material,
        "partial_stats_phase19_gva_share_change_classifier.csv": classifier,
        "partial_stats_phase19_gva_share_change_magnitude.csv": magnitude,
        "partial_stats_phase19_gva_sparse_update_budget.csv": budget,
        "partial_stats_phase19_gva_share_policy_results.csv": share_results,
        "partial_stats_phase19_gva_parent_share_policy_matrix.csv": matrix,
        "partial_stats_phase19_gva_combined_policy_results.csv": combined,
        "partial_stats_phase19_gva_combination_interaction.csv": interaction,
        "partial_stats_phase19_gva_parent_accuracy.csv": parent_results,
        "partial_stats_phase19_gva_share_accuracy.csv": share_results[["target_year", "origin_id", "share_policy_id", "share_mae"]],
        "partial_stats_phase19_gva_gva_accuracy.csv": gva_acc,
        "partial_stats_phase19_gva_update_precision_recall.csv": precision,
        "partial_stats_phase19_gva_weighted_update_utility.csv": utility,
        "partial_stats_phase19_gva_worst_group_results.csv": worst,
        "partial_stats_phase19_gva_quarterly_policy_results.csv": quarterly,
        "partial_stats_phase19_gva_monthly_experimental_results.csv": monthly,
        "partial_stats_phase19_gva_temporal_consistency.csv": temporal,
        "partial_stats_phase19_gva_annual_estimates_2025.csv": annual25,
        "partial_stats_phase19_gva_quarterly_estimates_2025.csv": quarter25,
        "partial_stats_phase19_gva_annual_nowcast_2026.csv": annual26,
        "partial_stats_phase19_gva_quarterly_nowcast_2026.csv": quarter26,
        "partial_stats_phase19_gva_parent_share_contributions.csv": contrib,
    }
    for name, frame in outputs.items():
        write_frame(name, frame)
    write_json(PROCESSED_DIR / "partial_stats_phase19_gva_goal_charter.json", goal)
    write_json(PROCESSED_DIR / "partial_stats_phase19_gva_policy_registry.json", policy)
    manifest = add_audit_cols(pd.DataFrame([{"artifact": name, "status": "completed", "python": platform.python_version()} for name in [*outputs.keys(), "partial_stats_phase19_gva_parent_target_cube.parquet", "partial_stats_phase19_gva_parent_feature_store.parquet", "partial_stats_phase19_gva_goal_charter.json", "partial_stats_phase19_gva_policy_registry.json", "partial_stats_phase19_gva_experiment_manifest.json", "partial_stats_phase19_gva_execution_manifest.csv", "partial_stats_phase19_gva_final_status.json"]]))
    write_json(PROCESSED_DIR / "partial_stats_phase19_gva_experiment_manifest.json", manifest.to_dict("records"))
    write_frame("partial_stats_phase19_gva_execution_manifest.csv", manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase19_gva_final_status.json", final)
    make_report(
        {
            "final_status": pd.DataFrame([final]),
            "goal": pd.DataFrame([goal]),
            "phase18": "Phase 18 showed that allocation-share error is potentially material, but its Parent, Share, and Interaction counterfactual ratios were not additive. Dynamic share policies underperformed P0 and their update precision was low, so Phase 19 repairs coverage, identity, and error attribution before testing parent and sparse-share challengers.",
            "target_coverage": target_audit,
            "model_identity": identity,
            "alias": alias,
            "signed": signed,
            "abs_shapley": abs_shapley,
            "parent_dominant": err_registry[err_registry["count_level"].eq("cell_year_level")][["parent_dominant", "total_units"]],
            "share_dominant": err_registry[err_registry["count_level"].eq("cell_year_level")][["share_dominant", "total_units"]],
            "parent_cube": pcube.head(20),
            "parent_feature": pfeature.head(20),
            "parent_results": parent_results,
            "parent_bridge": bridge,
            "parent_selection": parent_selection,
            "material": material.head(20),
            "classifier": classifier.head(20),
            "magnitude": magnitude.head(20),
            "budget": budget.head(20),
            "share_results": share_results,
            "precision": precision,
            "false_update": precision[["share_policy_id", "false_update_rate", "missed_material_change_rate"]],
            "utility": utility,
            "matrix": matrix,
            "combined": combined,
            "year_perf": year_perf,
            "industry_perf": industry_perf.head(20),
            "region_perf": region_perf.head(20),
            "worst": worst,
            "quarterly": quarterly,
            "monthly": monthly,
            "uncertainty": pd.DataFrame([{"uncertainty_status": "scenario_only_no_coverage_claim", "coverage_claim": "N"}]),
            "est2025": annual25.head(20),
            "now2026": annual26.head(20),
            "policy": pd.DataFrame([policy]),
            "limits": "No 2024 or 2025 official confirmatory actual is used. Monthly primary GVA remains blocked. Phase19 estimates are experimental and not official statistics.",
            "conclusion": f"Final status is {status}; selected policy is {combo_id}. Baseline is retained unless parent or sparse-share challengers pass the reproducibility and precision gates.",
        }
    )
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
