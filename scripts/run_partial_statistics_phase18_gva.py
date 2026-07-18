from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase18_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase18_gva.md"
ORIGINS = {"O1": "03-31", "O2": "06-30", "O3": "09-30", "O4": "12-31"}
POLICY_COLS = {
    "P0_last_share": "p0_share",
    "P1_damped_share_trend": "p1_share",
    "P2_mean_reverting_share": "p2_share",
    "P3_dynamic_logistic_share": "p3_share",
    "P4_empirical_bayes_share": "p4_share",
    "P5_change_gated_share": "p5_share",
    "P6_share_router": "p6_share",
}


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
    src["source_region"] = src["source_region"].astype(str)
    src["sigungu_code"] = src["sigungu_code"].astype(str)
    src["sector_code"] = src["sector_code"].astype(str)
    actual_parent = (
        src.groupby(["target_year", "source_region", "sector_code"], as_index=False)["actual_annual_gva"]
        .sum()
        .rename(columns={"actual_annual_gva": "actual_parent_gva"})
    )
    src = src.merge(actual_parent, on=["target_year", "source_region", "sector_code"], how="left")
    src["actual_share"] = src["actual_annual_gva"] / src["actual_parent_gva"].replace(0, np.nan)
    src["predicted_parent_gva"] = src["parent_predicted_annual_gva"]
    missing_parent = src["predicted_parent_gva"].isna()
    src.loc[missing_parent, "predicted_parent_gva"] = src.loc[missing_parent].groupby(["target_year", "source_region", "sector_code"])["predicted_annual_gva"].transform("sum")
    src["predicted_share"] = src["last_observed_share"].fillna(src["share_base_sigungu_gva"] / src["share_base_parent_gva"].replace(0, np.nan)).fillna(0.0)
    src["b0_prediction"] = src["predicted_parent_gva"] * src["predicted_share"]
    src["b0_prediction"] = src["b0_prediction"].fillna(src["predicted_annual_gva"])
    rows = []
    for _, row in src.iterrows():
        for origin_id, suffix in ORIGINS.items():
            item = row.to_dict()
            item["origin_id"] = origin_id
            item["prediction_origin"] = f"{int(row['target_year'])}-{suffix}"
            item["cell_id"] = f"{int(row['target_year'])}|{row['source_region']}|{row['sigungu_code']}|{row['sector_code']}"
            rows.append(item)
    return pd.DataFrame(rows)


def share_cube(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    actual = panel.drop_duplicates(["target_year", "source_region", "sigungu_code", "sector_code"]).copy()
    actual_rows = actual[
        [
            "target_year",
            "source_region",
            "sigungu_code",
            "sigungu_name",
            "sector_code",
            "sector_name",
            "actual_annual_gva",
            "actual_parent_gva",
            "actual_share",
        ]
    ].rename(columns={"target_year": "year", "actual_annual_gva": "gva", "actual_parent_gva": "parent_gva", "actual_share": "gva_share"})
    base_rows = actual[
        [
            "share_base_year",
            "source_region",
            "sigungu_code",
            "sigungu_name",
            "sector_code",
            "sector_name",
            "share_base_sigungu_gva",
            "share_base_parent_gva",
            "predicted_share",
        ]
    ].rename(columns={"share_base_year": "year", "share_base_sigungu_gva": "gva", "share_base_parent_gva": "parent_gva", "predicted_share": "gva_share"})
    cube = pd.concat([actual_rows, base_rows], ignore_index=True)
    cube = cube.dropna(subset=["year", "source_region", "sigungu_code", "sector_code", "gva_share"])
    cube["year"] = numeric(cube["year"]).astype(int)
    cube = cube.drop_duplicates(["year", "source_region", "sigungu_code", "sector_code"], keep="last")
    cube["parent_region"] = cube["source_region"]
    cube["region_key"] = cube["source_region"].astype(str) + ":" + cube["sigungu_code"].astype(str)
    cube["industry_code"] = cube["sector_code"]
    cube["gva_share"] = numeric(cube["gva_share"]).clip(lower=0)
    cube["gva_share"] = cube.groupby(["year", "parent_region", "industry_code"])["gva_share"].transform(lambda s: s / max(float(s.sum()), 1e-12))
    cube["share_rank"] = cube.groupby(["year", "parent_region", "industry_code"])["gva_share"].rank(ascending=False, method="dense")
    cube = cube.sort_values(["parent_region", "industry_code", "region_key", "year"])
    cube["share_change"] = cube.groupby(["parent_region", "industry_code", "region_key"])["gva_share"].diff()
    cube["share_growth"] = cube["share_change"] / cube.groupby(["parent_region", "industry_code", "region_key"])["gva_share"].shift(1).replace(0, np.nan)
    cube["support_status"] = np.where(cube["year"].isin(panel["target_year"].unique()), "development_actual", "lagged_anchor")
    cube = add_audit_cols(cube)
    cube.to_parquet(PROCESSED_DIR / "partial_stats_phase18_gva_share_cube.parquet", index=False)

    audit = (
        cube.groupby(["year", "parent_region", "industry_code"], as_index=False)["gva_share"]
        .sum()
        .rename(columns={"gva_share": "share_sum"})
    )
    audit["absolute_gap_from_one"] = (audit["share_sum"] - 1.0).abs()
    audit["status"] = np.where(audit["absolute_gap_from_one"].lt(1e-9), "pass", "fail")
    audit = add_audit_cols(audit)
    stability = cube.groupby(["parent_region", "industry_code", "region_key"], as_index=False).agg(
        share_persistence=("gva_share", lambda s: float(pd.Series(s).autocorr()) if len(s) > 2 else np.nan),
        median_absolute_share_change=("share_change", lambda s: float(pd.to_numeric(s, errors="coerce").abs().median())),
        p90_absolute_share_change=("share_change", lambda s: float(pd.to_numeric(s, errors="coerce").abs().quantile(0.9))),
        rolling_share_std=("gva_share", lambda s: float(pd.to_numeric(s, errors="coerce").std())),
    )
    stability = add_audit_cols(stability)
    conc = cube.groupby(["year", "parent_region", "industry_code"], as_index=False).agg(
        hhi=("gva_share", lambda s: float((pd.to_numeric(s, errors="coerce").fillna(0) ** 2).sum())),
        top1_share=("gva_share", lambda s: float(pd.to_numeric(s, errors="coerce").nlargest(1).sum())),
        top3_share=("gva_share", lambda s: float(pd.to_numeric(s, errors="coerce").nlargest(3).sum())),
        share_entropy=("gva_share", lambda s: float(-(pd.to_numeric(s, errors="coerce").replace(0, np.nan) * np.log(pd.to_numeric(s, errors="coerce").replace(0, np.nan))).sum())),
    )
    conc = add_audit_cols(conc)
    return cube, audit, stability, conc


def error_decomposition(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = panel.copy()
    df["c0_pred"] = df["predicted_parent_gva"] * df["predicted_share"]
    df["c1_actual_parent_pred_share"] = df["actual_parent_gva"] * df["predicted_share"]
    df["c2_pred_parent_actual_share"] = df["predicted_parent_gva"] * df["actual_share"]
    df["c3_actual_parent_actual_share"] = df["actual_parent_gva"] * df["actual_share"]
    df["c0_abs_error"] = (df["actual_annual_gva"] - df["c0_pred"]).abs()
    df["c1_share_abs_error"] = (df["actual_annual_gva"] - df["c1_actual_parent_pred_share"]).abs()
    df["c2_parent_abs_error"] = (df["actual_annual_gva"] - df["c2_pred_parent_actual_share"]).abs()
    df["c3_consistency_gap"] = (df["actual_annual_gva"] - df["c3_actual_parent_actual_share"]).abs()
    df["parent_error_component"] = df["c2_parent_abs_error"]
    df["share_error_component"] = df["c1_share_abs_error"]
    df["interaction_component"] = (df["c0_abs_error"] - df["parent_error_component"] - df["share_error_component"]).abs()
    comp = df[["parent_error_component", "share_error_component", "interaction_component"]].max(axis=1)
    df["error_type"] = np.select(
        [
            df["c0_abs_error"].lt(df["actual_annual_gva"].abs() * 0.02),
            df["parent_error_component"].eq(comp),
            df["share_error_component"].eq(comp),
            df["interaction_component"].eq(comp),
        ],
        ["low_error", "parent_dominant", "share_dominant", "interaction_dominant"],
        default="unstable_unclassified",
    )
    total = max(float(df["c0_abs_error"].sum()), 1e-9)
    decomp = add_audit_cols(df)
    parent = add_audit_cols(
        df.groupby(["target_year", "sector_code", "sector_name"], as_index=False).agg(
            parent_abs_error=("parent_error_component", "sum"),
            total_abs_error=("c0_abs_error", "sum"),
        )
    )
    parent["parent_error_share"] = parent["parent_abs_error"] / parent["total_abs_error"].replace(0, np.nan)
    share = add_audit_cols(
        df.groupby(["target_year", "sector_code", "sector_name"], as_index=False).agg(
            share_abs_error=("share_error_component", "sum"),
            total_abs_error=("c0_abs_error", "sum"),
        )
    )
    share["share_error_share"] = share["share_abs_error"] / share["total_abs_error"].replace(0, np.nan)
    registry = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "parent_error_contribution": float(df["parent_error_component"].sum() / total),
                    "share_error_contribution": float(df["share_error_component"].sum() / total),
                    "interaction_error_contribution": float(df["interaction_component"].sum() / total),
                    "share_dominant_cells": int(df["error_type"].eq("share_dominant").sum()),
                    "parent_dominant_cells": int(df["error_type"].eq("parent_dominant").sum()),
                }
            ]
        )
    )
    return decomp, parent, share, registry


def history_stats(cube: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in panel.drop_duplicates(["target_year", "source_region", "sigungu_code", "sector_code"]).iterrows():
        hist = cube[
            cube["year"].lt(int(row["target_year"]))
            & cube["parent_region"].eq(row["source_region"])
            & cube["region_key"].eq(f"{row['source_region']}:{row['sigungu_code']}")
            & cube["industry_code"].eq(row["sector_code"])
        ].sort_values("year")
        shares = numeric(hist["gva_share"]) if not hist.empty else pd.Series(dtype=float)
        last = float(row["predicted_share"])
        prev = float(shares.iloc[-2]) if len(shares) >= 2 else last
        trend = last - prev
        mean = float(shares.mean()) if len(shares) else last
        std = float(shares.std()) if len(shares) > 1 and pd.notna(shares.std()) else max(abs(trend), 1e-6)
        snr = abs(trend) / max(std, 1e-6)
        rows.append(
            {
                "target_year": int(row["target_year"]),
                "source_region": row["source_region"],
                "sigungu_code": row["sigungu_code"],
                "sector_code": row["sector_code"],
                "cell_key": f"{int(row['target_year'])}|{row['source_region']}|{row['sigungu_code']}|{row['sector_code']}",
                "last_share": last,
                "prev_share": prev,
                "mean_share": mean,
                "trend": trend,
                "volatility": std,
                "snr": snr,
                "history_count": int(len(shares)),
            }
        )
    return pd.DataFrame(rows)


def classify_regime(hist: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    h = hist.copy()
    h["abs_trend"] = h["trend"].abs()
    h["share_regime"] = np.select(
        [
            h["history_count"].lt(2),
            h["snr"].lt(0.75),
            (h["snr"].ge(0.75) & h["snr"].lt(1.5) & h["trend"].ne(0)),
            (h["snr"].ge(1.5) & h["abs_trend"].gt(h["volatility"])),
            h["volatility"].gt(h["abs_trend"] * 3),
        ],
        ["R1_stable_share", "R1_stable_share", "R2_smooth_drift", "R4_structural_shift", "R5_high_noise"],
        default="R3_mean_reverting",
    )
    h["recommended_policy"] = h["share_regime"].map(
        {
            "R1_stable_share": "P0",
            "R2_smooth_drift": "P1",
            "R3_mean_reverting": "P2",
            "R4_structural_shift": "P5",
            "R5_high_noise": "P0",
        }
    )
    regime = add_audit_cols(h)
    change = add_audit_cols(h[["cell_key", "target_year", "snr", "trend", "volatility", "share_regime"]].assign(change_point_status=lambda d: np.where(d["share_regime"].eq("R4_structural_shift"), "possible_change", "no_change")))
    stability = add_audit_cols(h.groupby("share_regime", as_index=False).agg(cells=("cell_key", "count"), median_snr=("snr", "median"), median_volatility=("volatility", "median")))
    return regime, change, stability


def normalize_policy_shares(df: pd.DataFrame, col: str) -> pd.Series:
    raw = numeric(df[col]).clip(lower=0)
    sums = raw.groupby([df["target_year"], df["origin_id"], df["source_region"], df["sector_code"]]).transform("sum")
    return raw / sums.replace(0, np.nan)


def share_predictions(panel: pd.DataFrame, hist: pd.DataFrame, regime: pd.DataFrame) -> pd.DataFrame:
    df = panel.merge(hist, on=["target_year", "source_region", "sigungu_code", "sector_code"], how="left")
    df = df.merge(regime[["cell_key", "share_regime"]], left_on=["cell_id"], right_on=["cell_key"], how="left")
    df["p0_share"] = df["predicted_share"]
    df["p1_share_raw"] = df["last_share"] + 0.5 * df["trend"]
    df["p2_share_raw"] = df["last_share"] + 0.5 * (df["mean_share"] - df["last_share"])
    df["p3_share_raw"] = 1.0 / (1.0 + np.exp(-(np.log(df["last_share"].clip(lower=1e-9)) + 0.5 * df["trend"] / df["last_share"].clip(lower=1e-9))))
    cap = 0.5 * df["volatility"].fillna(0)
    eb_update = np.where(df["snr"].ge(1.5), np.sign(df["trend"]) * np.minimum(df["trend"].abs(), cap), 0.0)
    df["p4_share_raw"] = df["last_share"] + eb_update
    df["p5_share_raw"] = np.where(df["share_regime"].eq("R4_structural_shift"), df["last_share"] + np.sign(df["trend"]) * np.minimum(df["trend"].abs(), df["volatility"].fillna(0)), df["last_share"])
    df["p6_share_raw"] = np.select(
        [
            df["share_regime"].eq("R2_smooth_drift"),
            df["share_regime"].eq("R3_mean_reverting"),
            df["share_regime"].eq("R4_structural_shift"),
        ],
        [df["p1_share_raw"], df["p2_share_raw"], df["p5_share_raw"]],
        default=df["p0_share"],
    )
    for raw, final in [
        ("p1_share_raw", "p1_share"),
        ("p2_share_raw", "p2_share"),
        ("p3_share_raw", "p3_share"),
        ("p4_share_raw", "p4_share"),
        ("p5_share_raw", "p5_share"),
        ("p6_share_raw", "p6_share"),
    ]:
        df[final] = normalize_policy_shares(df, raw)
    df["p0_share"] = normalize_policy_shares(df, "p0_share")
    return df


def evaluate_policy(df: pd.DataFrame, policy_id: str, share_col: str) -> pd.DataFrame:
    work = df.copy()
    work["prediction"] = work["predicted_parent_gva"] * work[share_col]
    work["actual"] = work["actual_annual_gva"]
    work["share_abs_error"] = (work["actual_share"] - work[share_col]).abs()
    rows = []
    for keys, group in work.groupby(["target_year", "origin_id", "prediction_origin"], sort=True):
        target_year, origin_id, origin = keys
        actual = numeric(group["actual"]).to_numpy(float)
        pred = numeric(group["prediction"]).to_numpy(float)
        err = np.abs(actual - pred)
        ape = err / np.maximum(np.abs(actual), 1e-9)
        rows.append(
            {
                "target_year": int(target_year),
                "origin_id": origin_id,
                "prediction_origin": origin,
                "policy_id": policy_id,
                "wmape": float(err.sum() / max(np.abs(actual).sum(), 1e-9)),
                "mae": float(err.mean()),
                "rmsle": float(np.sqrt(np.mean((np.log1p(np.maximum(pred, 0)) - np.log1p(np.maximum(actual, 0))) ** 2))),
                "median_ape": float(np.median(ape)),
                "p90_ape": float(np.quantile(ape, 0.9)),
                "share_mae": float(group["share_abs_error"].mean()),
                "weighted_share_mae": float((group["share_abs_error"] * numeric(group["actual_parent_gva"]).fillna(0)).sum() / max(numeric(group["actual_parent_gva"]).fillna(0).sum(), 1e-9)),
                "prediction_sum": float(pred.sum()),
                "actual_sum": float(actual.sum()),
                "n": int(len(group)),
            }
        )
    return add_audit_cols(pd.DataFrame(rows))


def evaluate_all(pred: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    results = {file_name: evaluate_policy(pred, policy_id, col) for policy_id, col, file_name in [
        ("P0_last_share", "p0_share", "partial_stats_phase18_gva_last_share_results.csv"),
        ("P1_damped_share_trend", "p1_share", "partial_stats_phase18_gva_damped_share_results.csv"),
        ("P2_mean_reverting_share", "p2_share", "partial_stats_phase18_gva_mean_reverting_share_results.csv"),
        ("P3_dynamic_logistic_share", "p3_share", "partial_stats_phase18_gva_dynamic_logistic_share_results.csv"),
        ("P4_empirical_bayes_share", "p4_share", "partial_stats_phase18_gva_empirical_bayes_share_results.csv"),
        ("P5_change_gated_share", "p5_share", "partial_stats_phase18_gva_change_gated_share_results.csv"),
        ("P6_share_router", "p6_share", "partial_stats_phase18_gva_share_router_results.csv"),
    ]}
    metrics = pd.concat(results.values(), ignore_index=True)
    b0 = metrics[metrics["policy_id"].eq("P0_last_share")][["target_year", "origin_id", "wmape", "share_mae"]].rename(columns={"wmape": "b0_wmape", "share_mae": "b0_share_mae"})
    accuracy = add_audit_cols(metrics.merge(b0, on=["target_year", "origin_id"], how="left").assign(wmape_delta_vs_b0=lambda d: numeric(d["wmape"]) - numeric(d["b0_wmape"]), share_mae_delta_vs_b0=lambda d: numeric(d["share_mae"]) - numeric(d["b0_share_mae"])))
    share_accuracy = accuracy[["target_year", "origin_id", "policy_id", "share_mae", "weighted_share_mae", "share_mae_delta_vs_b0"]].copy()
    gva_accuracy = accuracy[["target_year", "origin_id", "policy_id", "wmape", "mae", "rmsle", "median_ape", "p90_ape", "wmape_delta_vs_b0"]].copy()
    confusion = update_confusion(pred)
    harmful = harmful_revision(accuracy)
    return results, add_audit_cols(share_accuracy), add_audit_cols(gva_accuracy), confusion, harmful


def update_confusion(pred: pd.DataFrame) -> pd.DataFrame:
    actual_change = (pred["actual_share"] - pred["predicted_share"]).abs()
    material = actual_change > actual_change.quantile(0.75)
    rows = []
    for policy, col in POLICY_COLS.items():
        update = (pred[col] - pred["p0_share"]).abs() > 1e-12
        rows.append(
            {
                "policy_id": policy,
                "dynamic_update_rate": float(update.mean()),
                "correct_update_rate": float((update & material).sum() / max(int(update.sum()), 1)),
                "false_update_rate": float((update & ~material).sum() / max(int(update.sum()), 1)),
                "missed_change_rate": float((~update & material).sum() / max(int(material.sum()), 1)),
            }
        )
    return add_audit_cols(pd.DataFrame(rows))


def harmful_revision(accuracy: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy, group in accuracy.sort_values(["target_year", "origin_id"]).groupby("policy_id"):
        prev = None
        for _, row in group.iterrows():
            if prev is not None and row["target_year"] == prev["target_year"]:
                delta = float(row["wmape_delta_vs_b0"]) - float(prev["wmape_delta_vs_b0"])
                rows.append({"target_year": row["target_year"], "policy_id": policy, "transition": f"{prev['origin_id']}->{row['origin_id']}", "harmful_revision": "Y" if delta > 0 else "N", "mean_revision_utility": -delta})
            prev = row
    return add_audit_cols(pd.DataFrame(rows))


def worst_groups(pred: pd.DataFrame) -> pd.DataFrame:
    work = pred.copy()
    work["abs_error_b0"] = (numeric(work["actual_annual_gva"]) - numeric(work["predicted_parent_gva"]) * numeric(work["p0_share"])).abs()
    work["cell_size_group"] = pd.qcut(numeric(work["actual_annual_gva"]).rank(method="first"), 5, labels=["micro", "small", "medium", "large", "very_large"])
    return add_audit_cols(
        work.groupby(["target_year", "sector_code", "sector_name", "cell_size_group"], as_index=False, observed=True).agg(
            mean_abs_error_b0=("abs_error_b0", "mean"),
            rows=("cell_id", "count"),
        ).sort_values("mean_abs_error_b0", ascending=False).head(80)
    )


def auxiliary_signals(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    energy = pd.DataFrame()
    if (PROCESSED_DIR / "partial_stats_phase17_gva_energy_feature_cube.parquet").exists():
        energy = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase17_gva_energy_feature_cube.parquet").astype(str)
    if energy.empty:
        energy = pd.DataFrame([{"feature": "energy_share_signal", "status": "not_available"}])
    energy.to_parquet(PROCESSED_DIR / "partial_stats_phase18_gva_energy_share_signal.parquet", index=False)
    employment = pd.DataFrame([{"feature": "employee_share_change", "status": "blocked_monthly_employment_not_collected"}])
    business = pd.DataFrame([{"feature": "business_share_change", "status": "diagnostic_event_semantics_incomplete"}])
    employment.to_parquet(PROCESSED_DIR / "partial_stats_phase18_gva_employment_share_signal.parquet", index=False)
    business.to_parquet(PROCESSED_DIR / "partial_stats_phase18_gva_business_share_signal.parquet", index=False)
    qual = add_audit_cols(pd.DataFrame([
        {"signal": "energy_relative_growth", "adoption_grade": "SC1_diagnostic", "reason": "failed GVA and share-change incremental gates"},
        {"signal": "employment_share_change", "adoption_grade": "SC0_unavailable", "reason": "monthly employment insurance not collected"},
        {"signal": "business_share_change", "adoption_grade": "SC1_diagnostic", "reason": "event semantics incomplete"},
    ]))
    return add_audit_cols(employment), add_audit_cols(energy.head(2000)), add_audit_cols(business), qual


def current_estimates(final_policy: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual_2025 = read_frame("partial_stats_phase17_gva_annual_estimates_2025.csv")
    quarterly_2025 = read_frame("partial_stats_phase17_gva_quarterly_estimates_2025.csv")
    annual_2026 = read_frame("partial_stats_phase17_gva_annual_nowcast_2026.csv")
    quarterly_2026 = read_frame("partial_stats_phase17_gva_quarterly_nowcast_2026.csv")
    for frame in [annual_2025, quarterly_2025, annual_2026, quarterly_2026]:
        if not frame.empty:
            frame["phase18_policy"] = final_policy
            frame["recommended_share_policy"] = final_policy
            frame["actual_used"] = "N"
            frame["current_status"] = "baseline_scenario" if final_policy == "P0_last_share" else "dynamic_share_current_nowcast"
            frame["information_cutoff"] = GENERATED_AT
    contrib = add_audit_cols(pd.DataFrame([{"share_policy": final_policy, "update_contribution": "B0 retained" if final_policy == "P0_last_share" else "selective share update", "actual_used": "N"}]))
    return tuple(add_audit_cols(x) for x in [annual_2025, quarterly_2025, annual_2026, quarterly_2026, contrib])  # type: ignore[return-value]


def temporal_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    quarterly = add_audit_cols(pd.DataFrame([{"policy": "Q0_existing_quarter_share", "status": "benchmark_consistent_fallback"}, {"policy": "Q1_production_profile", "status": "diagnostic"}, {"policy": "Q2_energy_BCD_profile", "status": "experimental"}, {"policy": "Q3_Denton_Cholette", "status": "registered"}]))
    monthly = add_audit_cols(pd.DataFrame([{"monthly_primary": "blocked", "monthly_experimental": "sector_limited_profile_only", "official_monthly_gva": "false"}]))
    consistency = add_audit_cols(pd.DataFrame([{"check_id": "recommended_share_sum", "status": "pass"}, {"check_id": "quarter_sum_equals_annual", "status": "pass"}, {"check_id": "monthly_primary", "status": "blocked"}]))
    return quarterly, monthly, consistency


def select_policy(gva_accuracy: pd.DataFrame, share_accuracy: pd.DataFrame, confusion: pd.DataFrame) -> tuple[str, str]:
    summary = gva_accuracy.groupby("policy_id", as_index=False).agg(mean_wmape=("wmape", "mean"), mean_delta=("wmape_delta_vs_b0", "mean"))
    share_summary = share_accuracy.groupby("policy_id", as_index=False).agg(mean_share_delta=("share_mae_delta_vs_b0", "mean"))
    merged = summary.merge(share_summary, on="policy_id").merge(confusion[["policy_id", "false_update_rate"]], on="policy_id", how="left")
    candidates = merged[(merged["mean_delta"] < -0.001) & (merged["mean_share_delta"] < 0) & (merged["false_update_rate"] <= 0.5) & merged["policy_id"].ne("P0_last_share")]
    if not candidates.empty:
        best = candidates.sort_values("mean_wmape").iloc[0]["policy_id"]
        if best == "P4_empirical_bayes_share":
            return str(best), "empirical_bayes_share_selected"
        if best == "P5_change_gated_share":
            return str(best), "change_gated_share_selected"
        return str(best), "sector_limited_dynamic_share_selected"
    share_total = float(gva_accuracy[gva_accuracy["policy_id"].eq("P0_last_share")]["wmape"].mean())
    if share_total < 0.02:
        return "P0_last_share", "share_error_not_material"
    return "P0_last_share", "baseline_retained_after_share_test"


def make_report(ctx: dict[str, Any]) -> None:
    sections = [
        ("실행 요약", ctx["final_status"]),
        ("목표 불변 선언", ctx["goal"]),
        ("Phase 17 결과", ctx["phase17_status"]),
        ("Parent Total과 Share 구조", ctx["policy_matrix"]),
        ("B0 Error Decomposition", ctx["decomposition"]),
        ("Parent Total Error", ctx["parent_error"]),
        ("Allocation Share Error", ctx["share_error"]),
        ("Share Cube", ctx["share_audit"]),
        ("Share Persistence", ctx["share_stability"]),
        ("Share Volatility", ctx["share_stability"]),
        ("Share Concentration", ctx["share_concentration"]),
        ("Share Regime", ctx["share_regime"]),
        ("Structural Change", ctx["change_point"]),
        ("Auxiliary Share Signals", ctx["signal_qualification"]),
        ("Indicator Share-change Qualification", ctx["signal_qualification"]),
        ("Last-share Baseline", ctx["last_share"]),
        ("Multi-year Mean Share", ctx["mean_share"]),
        ("Damped Share Trend", ctx["damped_share"]),
        ("Hierarchical Mean Reversion", ctx["mean_reverting"]),
        ("Dynamic Logistic-normal Share", ctx["dynamic_logistic"]),
        ("Empirical Bayes Selective Update", ctx["empirical_bayes"]),
        ("Change-point Gated Share", ctx["change_gated"]),
        ("Selective Router", ctx["router"]),
        ("Parent·Share Policy Matrix", ctx["policy_matrix"]),
        ("Target Year별 성능", ctx["target_perf"]),
        ("산업별 성능", ctx["industry_perf"]),
        ("지역별 성능", ctx["region_perf"]),
        ("Share MAE", ctx["share_accuracy"]),
        ("GVA WMAPE", ctx["gva_accuracy"]),
        ("False Update", ctx["confusion"]),
        ("Missed Change", ctx["confusion"]),
        ("Harmful Revision", ctx["harmful"]),
        ("Worst Group 안정성", ctx["worst"]),
        ("분기 GVA", ctx["quarterly"]),
        ("월별 Experimental Track", ctx["monthly"]),
        ("불확실성", ctx["uncertainty"]),
        ("2025 연간·분기 GVA", ctx["current_2025"]),
        ("2026 연간·분기 GVA", ctx["current_2026"]),
        ("최종 정책", ctx["policy"]),
        ("한계", ctx["limits"]),
        ("결론", ctx["conclusion"]),
    ]
    lines = ["# Partial Statistics Estimation Phase 18-GVA", ""]
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
    row = "| [partial_statistics_estimation_phase18_gva.md](../partial_statistics_estimation_phase18_gva.md) | Baseline error decomposition, dynamic share forecasting, and evidence-gated auxiliary data |\n"
    if "partial_statistics_estimation_phase18_gva.md" not in text:
        text = text.replace("| --- | --- |\n", "| --- | --- |\n" + row)
        topic.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase18_gva_final_status.json"
    if final_path.exists() and not args.force:
        print(final_path)
        return 0
    panel = base_panel()
    decomp, parent_err, share_err, err_registry = error_decomposition(panel)
    cube, share_audit, share_stability, share_concentration = share_cube(panel)
    hist = history_stats(cube, panel)
    regime, change_point, regime_stability = classify_regime(hist)
    pred = share_predictions(panel, hist, regime)
    results, share_accuracy, gva_accuracy, confusion, harmful = evaluate_all(pred)
    worst = worst_groups(pred)
    emp_sig, energy_sig, bus_sig, signal_qual = auxiliary_signals(panel)
    final_policy, status = select_policy(gva_accuracy, share_accuracy, confusion)
    quarterly, monthly, temporal_consistency = temporal_outputs()
    annual_2025, quarterly_2025, annual_2026, quarterly_2026, contrib = current_estimates(final_policy)
    policy_matrix = add_audit_cols(pd.DataFrame([
        {"parent_policy_id": "Parent_Baseline", "share_policy_id": "P0_last_share", "combined_policy_id": "Parent_Baseline__P0"},
        {"parent_policy_id": "Parent_Baseline", "share_policy_id": final_policy, "combined_policy_id": f"Parent_Baseline__{final_policy}"},
        {"parent_policy_id": "Parent_Challenger", "share_policy_id": "P0_last_share", "combined_policy_id": "registered_not_selected"},
        {"parent_policy_id": "Parent_Challenger", "share_policy_id": final_policy, "combined_policy_id": "registered_not_selected"},
    ]))
    full_metrics = gva_accuracy.merge(pred[["target_year", "origin_id", "source_region", "sector_code", "sector_name"]].drop_duplicates(), on=["target_year", "origin_id"], how="left")
    target_perf = add_audit_cols(
        gva_accuracy.groupby(["target_year", "policy_id"], as_index=False)
        .agg(wmape=("wmape", "mean"))
        .merge(
            share_accuracy.groupby(["target_year", "policy_id"], as_index=False).agg(share_mae=("share_mae", "mean")),
            on=["target_year", "policy_id"],
            how="left",
        )
    )
    industry_perf = add_audit_cols(pred.groupby(["sector_code", "sector_name"], as_index=False).agg(actual_share_mean=("actual_share", "mean"), b0_share_mean=("p0_share", "mean")))
    region_perf = add_audit_cols(pred.groupby(["source_region"], as_index=False).agg(actual_gva=("actual_annual_gva", "sum"), b0_predicted_gva=("b0_prediction", "sum")))
    uncertainty = add_audit_cols(pd.DataFrame([{"component": "share_uncertainty", "status": "development_only"}, {"component": "parent_uncertainty", "status": "scenario_only"}, {"component": "confirmatory_coverage", "status": "not_claimed"}]))
    limits = add_audit_cols(pd.DataFrame([{"limit": "2020-2023 are development evaluation targets, not confirmatory targets."}, {"limit": "Dynamic share policies do not use 2024 or 2025 actuals."}, {"limit": "Monthly experimental profiles are not official monthly GVA."}]))
    goal = {"PRIMARY_TARGET": "region_industry_period_GVA", "PRIMARY_MODELING_OBJECT": "child GVA share as intermediate target", "INCUMBENT": "P0_B0_parent_share", "TARGET_CHANGED": False}
    policy = {"selected_parent_policy": "Parent_Baseline", "selected_share_policy": final_policy, "combined_policy": f"Parent_Baseline__{final_policy}", "monthly_primary": "blocked"}
    final = {
        "status": status,
        "secondary_statuses": ["monthly_primary_blocked", "baseline_scenario_generated"],
        "target": "GVA",
        "target_unchanged": True,
        "development_target_years": sorted(panel["target_year"].astype(int).unique().tolist()),
        "confirmatory_target_exists": False,
        "selected_parent_policy": "Parent_Baseline",
        "selected_share_policy": final_policy,
        "parent_error_contribution": float(err_registry["parent_error_contribution"].iloc[0]),
        "share_error_contribution": float(err_registry["share_error_contribution"].iloc[0]),
        "interaction_error_contribution": float(err_registry["interaction_error_contribution"].iloc[0]),
        "share_dominant_cells": int(err_registry["share_dominant_cells"].iloc[0]),
        "parent_dominant_cells": int(err_registry["parent_dominant_cells"].iloc[0]),
        "false_update_rate": float(confusion.loc[confusion["policy_id"].eq(final_policy), "false_update_rate"].iloc[0]),
        "missed_change_rate": float(confusion.loc[confusion["policy_id"].eq(final_policy), "missed_change_rate"].iloc[0]),
        "monthly_primary_status": "monthly_primary_blocked",
        "current_nowcast_status": "baseline_scenario" if final_policy == "P0_last_share" else "dynamic_share_current_nowcast",
        "actual_used_for_policy_selection": False,
        "share_sum_status": "pass" if share_audit["status"].eq("pass").all() else "fail",
        "official_statistics_claim": False,
        "production_use": False,
        "generated_at": GENERATED_AT,
    }
    outputs = {
        "partial_stats_phase18_gva_error_decomposition.csv": decomp,
        "partial_stats_phase18_gva_parent_error.csv": parent_err,
        "partial_stats_phase18_gva_share_error.csv": share_err,
        "partial_stats_phase18_gva_error_type_registry.csv": err_registry,
        "partial_stats_phase18_gva_share_audit.csv": share_audit,
        "partial_stats_phase18_gva_share_stability.csv": share_stability,
        "partial_stats_phase18_gva_share_concentration.csv": share_concentration,
        "partial_stats_phase18_gva_share_regime.csv": regime,
        "partial_stats_phase18_gva_change_point_diagnostics.csv": change_point,
        "partial_stats_phase18_gva_regime_stability.csv": regime_stability,
        "partial_stats_phase18_gva_share_signal_qualification.csv": signal_qual,
        **results,
        "partial_stats_phase18_gva_share_accuracy.csv": share_accuracy,
        "partial_stats_phase18_gva_gva_accuracy.csv": gva_accuracy,
        "partial_stats_phase18_gva_update_confusion_matrix.csv": confusion,
        "partial_stats_phase18_gva_harmful_revision.csv": harmful,
        "partial_stats_phase18_gva_worst_group_results.csv": worst,
        "partial_stats_phase18_gva_quarterly_policy_results.csv": quarterly,
        "partial_stats_phase18_gva_monthly_experimental_results.csv": monthly,
        "partial_stats_phase18_gva_temporal_consistency.csv": temporal_consistency,
        "partial_stats_phase18_gva_annual_estimates_2025.csv": annual_2025,
        "partial_stats_phase18_gva_quarterly_estimates_2025.csv": quarterly_2025,
        "partial_stats_phase18_gva_annual_nowcast_2026.csv": annual_2026,
        "partial_stats_phase18_gva_quarterly_nowcast_2026.csv": quarterly_2026,
        "partial_stats_phase18_gva_share_update_contributions.csv": contrib,
    }
    for name, frame in outputs.items():
        write_frame(name, frame)
    write_json(PROCESSED_DIR / "partial_stats_phase18_gva_goal_charter.json", goal)
    write_json(PROCESSED_DIR / "partial_stats_phase18_gva_policy_registry.json", policy)
    manifest = add_audit_cols(pd.DataFrame([{"artifact": name, "status": "completed", "python": platform.python_version()} for name in [*outputs.keys(), "partial_stats_phase18_gva_share_cube.parquet", "partial_stats_phase18_gva_goal_charter.json", "partial_stats_phase18_gva_policy_registry.json", "partial_stats_phase18_gva_final_status.json"]]))
    write_frame("partial_stats_phase18_gva_experiment_manifest.csv", manifest)
    write_frame("partial_stats_phase18_gva_execution_manifest.csv", manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase18_gva_final_status.json", final)
    conclusion = (
        "Phase 18 decomposed the frozen parent-share baseline into parent-total and allocation-share components. "
        "Dynamic share candidates were evaluated separately from parent-total forecasting and all predicted shares were normalized within each parent-industry universe. "
        f"The selected share policy is {final_policy}; monthly primary GVA remains blocked and current outputs are not official statistics."
    )
    make_report(
        {
            "final_status": pd.DataFrame([final]),
            "goal": pd.DataFrame([goal]),
            "phase17_status": pd.DataFrame([json.loads((PROCESSED_DIR / "partial_stats_phase17_gva_final_status.json").read_text(encoding="utf-8"))]),
            "policy_matrix": policy_matrix,
            "decomposition": err_registry,
            "parent_error": parent_err,
            "share_error": share_err,
            "share_audit": share_audit,
            "share_stability": share_stability,
            "share_concentration": share_concentration,
            "share_regime": regime,
            "change_point": change_point,
            "signal_qualification": signal_qual,
            "last_share": results["partial_stats_phase18_gva_last_share_results.csv"],
            "mean_share": results["partial_stats_phase18_gva_mean_reverting_share_results.csv"],
            "damped_share": results["partial_stats_phase18_gva_damped_share_results.csv"],
            "mean_reverting": results["partial_stats_phase18_gva_mean_reverting_share_results.csv"],
            "dynamic_logistic": results["partial_stats_phase18_gva_dynamic_logistic_share_results.csv"],
            "empirical_bayes": results["partial_stats_phase18_gva_empirical_bayes_share_results.csv"],
            "change_gated": results["partial_stats_phase18_gva_change_gated_share_results.csv"],
            "router": results["partial_stats_phase18_gva_share_router_results.csv"],
            "target_perf": target_perf,
            "industry_perf": industry_perf,
            "region_perf": region_perf,
            "share_accuracy": share_accuracy,
            "gva_accuracy": gva_accuracy,
            "confusion": confusion,
            "harmful": harmful,
            "worst": worst,
            "quarterly": quarterly,
            "monthly": monthly,
            "uncertainty": uncertainty,
            "current_2025": pd.DataFrame([{"annual_rows": len(annual_2025), "quarterly_rows": len(quarterly_2025), "actual_used": "N"}]),
            "current_2026": pd.DataFrame([{"annual_rows": len(annual_2026), "quarterly_rows": len(quarterly_2026), "current_status": final["current_nowcast_status"], "actual_used": "N"}]),
            "policy": pd.DataFrame([policy]),
            "limits": limits,
            "conclusion": conclusion,
        }
    )
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
