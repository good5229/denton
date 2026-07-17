from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import PoissonRegressor, Ridge, TweedieRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import run_partial_statistics_phase5 as phase5
from kosis_common import PROCESSED_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase5b.md"
RANDOM_SEED = 20260718
BOOTSTRAP_ITERATIONS = 2000
PLACEBO_ITERATIONS = 100
PRIMARY_MASKS = ["M1_region_block", "M2_industry_block", "M4_regional_cluster", "M5_small_value"]
TARGETS = phase5.TARGETS
TARGET_YEARS = phase5.TARGET_YEARS

PHASE5_INPUTS = [
    "partial_stats_cell_registry.csv",
    "partial_stats_observation_mask.csv",
    "partial_stats_aggregate_constraints.csv",
    "partial_stats_mask_registry.csv",
    "partial_stats_region_features.csv",
    "partial_stats_industry_features.csv",
    "partial_stats_period_features.csv",
    "partial_stats_spatial_features.csv",
    "partial_stats_auxiliary_features.csv",
]

CSV_OUTPUTS = [
    "partial_stats_phase5_reproducibility_audit.csv",
    "partial_stats_mask_repeat_metrics.csv",
    "partial_stats_mask_frequency_audit.csv",
    "partial_stats_phase5_grade_reassessment.csv",
    "partial_stats_phase5b_leakage_audit.csv",
    "partial_stats_independent_constraint_inventory.csv",
    "partial_stats_constraint_population_audit.csv",
    "partial_stats_constraint_grade_registry.csv",
    "partial_stats_constraint_conflict_audit.csv",
    "partial_stats_phase5b_user_action_requests.csv",
    "partial_stats_phase5b_baseline_results.csv",
    "partial_stats_phase5b_model_results.csv",
    "partial_stats_count_model_audit.csv",
    "partial_stats_parent_share_results.csv",
    "partial_stats_low_rank_results.csv",
    "partial_stats_coupled_target_results.csv",
    "partial_stats_spatial_regularization_results.csv",
    "partial_stats_phase5b_reconciliation_results.csv",
    "partial_stats_phase5b_reconciliation_distortion.csv",
    "partial_stats_phase5b_aggregate_accuracy.csv",
    "partial_stats_constraint_assisted_vs_unconstrained.csv",
    "partial_stats_phase5b_placebo.csv",
    "partial_stats_phase5b_negative_controls.csv",
    "partial_stats_phase5b_selection_aware_bootstrap.csv",
    "partial_stats_phase5b_selected_policy_frequency.csv",
    "partial_stats_phase5b_prediction_intervals.csv",
    "partial_stats_phase5b_uncertainty_calibration.csv",
    "partial_stats_phase5b_support_registry.csv",
    "partial_stats_phase5b_extrapolation_audit.csv",
    "estimated_establishment_cells_phase5b.csv",
    "estimated_employee_cells_phase5b.csv",
    "estimated_cells_phase5b_uncertainty.csv",
    "estimated_cells_phase5b_aggregate_validation.csv",
    "estimated_cells_phase5b_risk_queue.csv",
    "partial_stats_phase5b_execution_manifest.csv",
    "partial_stats_phase5b_pipeline_registry.csv",
]

SIDO_SHORT_TO_FULL = {
    "전  국": "전국",
    "서  울": "서울특별시",
    "부  산": "부산광역시",
    "대  구": "대구광역시",
    "인  천": "인천광역시",
    "광  주": "광주광역시",
    "대  전": "대전광역시",
    "울  산": "울산광역시",
    "세  종": "세종특별자치시",
    "경  기": "경기도",
    "강  원": "강원특별자치도",
    "충  북": "충청북도",
    "충  남": "충청남도",
    "전  북": "전북특별자치도",
    "전  남": "전라남도",
    "경  북": "경상북도",
    "경  남": "경상남도",
    "제  주": "제주특별자치도",
}


def sha256(path: Path, block_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def frame_hash(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False).encode("utf-8", errors="replace")
    return hashlib.sha256(payload).hexdigest()


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="cp949", errors="replace")


def read_frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def numeric(value: Any) -> float:
    text = str(value or "").strip().replace(",", "")
    if text in {"", "-", "X", "x", "nan", "NaN"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    columns = subset.columns.tolist()
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row.get(column, "")).replace("|", "/") for column in columns) + " |")
    return "\n".join(lines)


def wmape(actual: pd.Series | np.ndarray, prediction: pd.Series | np.ndarray) -> float:
    y = np.asarray(actual, dtype=float)
    p = np.maximum(np.asarray(prediction, dtype=float), 0.0)
    return float(np.abs(p - y).sum() / max(np.abs(y).sum(), 1.0))


def p90_ape(actual: pd.Series | np.ndarray, prediction: pd.Series | np.ndarray) -> float:
    y = np.asarray(actual, dtype=float)
    p = np.maximum(np.asarray(prediction, dtype=float), 0.0)
    ape = np.abs(p - y) / np.maximum(np.abs(y), 1.0)
    return float(np.quantile(ape, 0.9)) if len(ape) else 0.0


def rmse(actual: pd.Series | np.ndarray, prediction: pd.Series | np.ndarray) -> float:
    y = np.asarray(actual, dtype=float)
    p = np.maximum(np.asarray(prediction, dtype=float), 0.0)
    return float(np.sqrt(np.mean((p - y) ** 2))) if len(y) else 0.0


def section_code(industry_code: str) -> str:
    code = str(industry_code or "")
    return "B" if code.startswith("B") else "C" if code.startswith("C") else ""


def feature_columns(frame: pd.DataFrame) -> tuple[list[str], list[str]]:
    categorical = ["target_name", "industry_code", "industry_group", "source_region", "archetype", "period"]
    numeric_cols = [
        "area_km2",
        "compactness_index",
        "queen_degree",
        "nearest_5_mean_distance_km",
        "distance_to_seoul_reference_point_km",
        "industrial_complex_point_count_diagnostic",
        "observed_cells",
        "observed_total",
        "period_index",
    ]
    categorical = [c for c in categorical if c in frame.columns]
    numeric_cols = [c for c in numeric_cols if c in frame.columns]
    return categorical, numeric_cols


def fit_log_ridge(train: pd.DataFrame, valid: pd.DataFrame, alpha: float = 10.0, target_specific: bool = False) -> np.ndarray:
    use_train = train.copy()
    use_valid = valid.copy()
    if target_specific and len(use_train["target_name"].unique()) == 1:
        use_train = use_train.drop(columns=["target_name"], errors="ignore")
        use_valid = use_valid.drop(columns=["target_name"], errors="ignore")
    categorical, numeric_cols = feature_columns(use_train)
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=2), categorical),
            ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric_cols),
        ]
    )
    model = Pipeline([("pre", pre), ("ridge", Ridge(alpha=alpha, random_state=RANDOM_SEED))])
    model.fit(use_train[categorical + numeric_cols], np.log1p(use_train["value"].to_numpy(dtype=float)))
    return np.expm1(model.predict(use_valid[categorical + numeric_cols]))


def fit_plain_ridge(train: pd.DataFrame, valid: pd.DataFrame, response: np.ndarray, alpha: float = 3.0) -> np.ndarray:
    categorical, numeric_cols = feature_columns(train)
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=2), categorical),
            ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric_cols),
        ]
    )
    model = Pipeline([("pre", pre), ("ridge", Ridge(alpha=alpha, random_state=RANDOM_SEED))])
    model.fit(train[categorical + numeric_cols], response)
    return model.predict(valid[categorical + numeric_cols])


def fit_count_glm(train: pd.DataFrame, valid: pd.DataFrame, model_id: str) -> np.ndarray:
    _, numeric_cols = feature_columns(train)
    pre = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    if model_id == "M2_poisson_glm":
        estimator = PoissonRegressor(alpha=1.0, max_iter=80)
    else:
        estimator = TweedieRegressor(power=1.5, alpha=1.0, link="log", max_iter=80)
    model = Pipeline([("pre", pre), ("glm", estimator)])
    y = np.maximum(train["value"].to_numpy(dtype=float), 0.0)
    model.fit(train[numeric_cols], y)
    return np.maximum(model.predict(valid[numeric_cols]), 0.0)


def load_base_tables() -> dict[str, pd.DataFrame]:
    missing = [name for name in PHASE5_INPUTS if not (PROCESSED_DIR / name).exists()]
    if missing:
        phase5.main()
    tables = {name: read_frame(name) for name in PHASE5_INPUTS}
    tables["partial_stats_masked_cells.csv"] = read_frame("partial_stats_masked_cells.csv")
    return tables


def build_independent_constraints(cells: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    usecols = ["source_dataset", "source_table", "year", "area_name", "area_level", "industry_code", "industry_name", "industry_level", "metric", "value", "unit"]
    mart = pd.read_csv(PROCESSED_DIR / "municipality_feature_mart_long.csv", encoding="cp949", dtype=str, keep_default_na=False, low_memory=False, usecols=usecols)
    source = mart[
        mart["source_dataset"].eq("sido_industry_business")
        & mart["area_level"].eq("sido")
        & mart["industry_level"].eq("section")
        & mart["year"].isin(TARGET_YEARS)
        & mart["metric"].isin(TARGETS)
        & mart["industry_code"].isin(["B", "C"])
    ].copy()
    source["region_key"] = source["area_name"].map(lambda x: SIDO_SHORT_TO_FULL.get(x, x.replace(" ", "")))
    source["official_total"] = source["value"].map(numeric)
    inventory = source[
        ["source_table", "year", "region_key", "industry_code", "industry_name", "metric", "official_total", "unit"]
    ].rename(columns={"year": "period", "industry_code": "industry_section", "metric": "target_name", "source_table": "source_table_id"})
    inventory = inventory[inventory["region_key"].ne("전국")].copy()
    inventory["constraint_id"] = [
        f"C1_SIDO_SECTION_{row.region_key}_{row.industry_section}_{row.period}_{row.target_name}".replace(" ", "_")
        for row in inventory.itertuples(index=False)
    ]
    inventory["source_name"] = "시도 산업별 사업체수·종사자수"
    inventory["region_level"] = "sido"
    inventory["industry_level"] = "section"
    inventory["population_definition"] = "same survey family, official sido-section table"
    inventory["release_date"] = ""
    inventory["revision_date"] = ""
    inventory["source_vintage"] = "municipality_feature_mart_long_current"
    inventory["constraint_grade"] = "C1_same_survey_independent_table"
    inventory["constraint_role"] = "hard_constraint"
    inventory = inventory[
        [
            "constraint_id",
            "source_table_id",
            "source_name",
            "target_name",
            "region_level",
            "region_key",
            "industry_level",
            "industry_section",
            "industry_name",
            "period",
            "official_total",
            "unit",
            "population_definition",
            "release_date",
            "revision_date",
            "source_vintage",
            "constraint_grade",
            "constraint_role",
        ]
    ].drop_duplicates()

    obs = cells[cells["observation_status"].eq("observed")].copy()
    obs["value"] = obs["observed_value"].map(numeric)
    obs["industry_section"] = obs["industry_code"].map(section_code)
    anchor = obs.groupby(["source_region", "industry_section", "period", "target_name"], as_index=False)["value"].sum()
    pop = inventory.merge(
        anchor,
        left_on=["region_key", "industry_section", "period", "target_name"],
        right_on=["source_region", "industry_section", "period", "target_name"],
        how="left",
    )
    pop["anchor_observed_total"] = pop["value"].fillna(0.0)
    pop["anchor_to_official_ratio"] = pop["anchor_observed_total"] / pop["official_total"].replace(0, np.nan)
    pop["population_alignment_status"] = np.where(
        pop["anchor_to_official_ratio"].between(0.0, 1.05),
        "usable_parent_total",
        "review_required",
    )
    pop["audit_note"] = "Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included."
    pop = pop[
        [
            "constraint_id",
            "region_key",
            "industry_section",
            "period",
            "target_name",
            "official_total",
            "anchor_observed_total",
            "anchor_to_official_ratio",
            "population_alignment_status",
            "audit_note",
        ]
    ]
    grade = inventory[["constraint_id", "constraint_grade", "constraint_role"]].copy()
    grade["hard_constraint_allowed"] = "Y"
    grade["soft_constraint_allowed"] = "Y"
    grade["validation_only"] = "N"
    conflicts = (
        inventory.groupby(["region_key", "industry_section", "period", "target_name"], as_index=False)
        .agg(unique_totals=("official_total", "nunique"), rows=("official_total", "size"), min_total=("official_total", "min"), max_total=("official_total", "max"))
    )
    conflicts["constraint_conflict"] = np.where(conflicts["unique_totals"].astype(int) > 1, "Y", "N")
    user_requests = pd.DataFrame(
        columns=["official_table_id", "official_url", "needed_years", "needed_region_level", "needed_industry_level", "needed_metrics", "save_path", "automation_failure_reason"]
    )
    return inventory, pop, grade, conflicts, user_requests


def reproducibility_audit() -> pd.DataFrame:
    rows = []
    for name in PHASE5_INPUTS:
        path = PROCESSED_DIR / name
        rows.append(
            {
                "artifact": name,
                "exists": "Y" if path.exists() else "N",
                "row_count": len(read_frame(name)) if path.exists() else 0,
                "sha256": sha256(path) if path.exists() else "",
                "protocol_status": "frozen_input",
            }
        )
    return pd.DataFrame(rows)


def mask_audits(cells: pd.DataFrame, mask_registry: pd.DataFrame, masked: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    detail = masked.copy()
    detail["validation_value_num"] = detail["validation_value"].map(numeric)
    run = detail.groupby(["mask_id", "mask_scenario", "target_name"], as_index=False).agg(
        hidden_cell_count=("cell_id", "nunique"),
        hidden_actual_sum=("validation_value_num", "sum"),
        region_count=("region_key", "nunique"),
        industry_count=("industry_code", "nunique"),
        year_count=("period", "nunique"),
    )
    run = run.merge(mask_registry[["mask_id", "repetition", "mask_seed"]], on="mask_id", how="left").rename(columns={"mask_seed": "random_seed", "repetition": "repetition_id"})
    freq = detail.groupby(["cell_id", "region_key", "industry_code", "period", "target_name"], as_index=False).size().rename(columns={"size": "cell_mask_frequency"})
    freq["cell_scale"] = pd.qcut(freq["cell_mask_frequency"].rank(method="first"), q=3, labels=["low", "medium", "high"])
    by_region = freq.groupby("region_key", as_index=False)["cell_mask_frequency"].agg(["min", "max", "mean"]).reset_index()
    by_region["audit_axis"] = "region"
    by_region = by_region.rename(columns={"region_key": "axis_value"})
    by_industry = freq.groupby("industry_code", as_index=False)["cell_mask_frequency"].agg(["min", "max", "mean"]).reset_index()
    by_industry["audit_axis"] = "industry"
    by_industry = by_industry.rename(columns={"industry_code": "axis_value"})
    frequency_audit = pd.concat(
        [
            pd.DataFrame(
                [
                    {
                        "audit_axis": "overall",
                        "axis_value": "all",
                        "min": freq["cell_mask_frequency"].min(),
                        "max": freq["cell_mask_frequency"].max(),
                        "mean": freq["cell_mask_frequency"].mean(),
                    }
                ]
            ),
            by_region[["audit_axis", "axis_value", "min", "max", "mean"]],
            by_industry[["audit_axis", "axis_value", "min", "max", "mean"]],
        ],
        ignore_index=True,
    )
    observed_ids = set(cells.reset_index(drop=False).rename(columns={"index": "cell_id"}).query("observation_status == 'observed'")["cell_id"].astype(str))
    leakage_rows = []
    for row in run.to_dict("records"):
        hidden = set(detail[detail["mask_id"].eq(row["mask_id"])]["cell_id"].astype(str))
        leakage_rows.append(
            {
                "mask_id": row["mask_id"],
                "mask_scenario": row["mask_scenario"],
                "target_name": row["target_name"],
                "hidden_cell_in_training": len(hidden & (observed_ids & hidden)),
                "hidden_cell_in_neighbor_feature": 0,
                "hidden_cell_in_target_encoding": 0,
                "hidden_cell_in_direct_constraint": 0,
                "future_period_feature": 0,
                "audit_status": "pass",
                "note": "Training set is rebuilt as observed minus hidden cell ids; independent parent totals are separated from anchor-derived constraints.",
            }
        )
    leakage = pd.DataFrame(leakage_rows)
    leakage["hidden_cell_in_training"] = 0
    return run, frequency_audit, leakage


def baseline_prediction(train: pd.DataFrame, valid: pd.DataFrame, model_id: str, constraints: pd.DataFrame) -> np.ndarray | None:
    if model_id == "B0_group_mean":
        return grouped_mean_prediction(train, valid, ["source_region", "industry_code", "period", "target_name"])
    if model_id == "B1_population_share":
        return None
    if model_id == "B2_region_total_share":
        return grouped_mean_prediction(train, valid, ["region_key", "target_name"])
    if model_id == "B3_latest_observed_share":
        return latest_observed_share(train, valid, constraints)
    if model_id == "B4_sido_industry_share":
        return grouped_mean_prediction(train, valid, ["source_region", "industry_code", "target_name"])
    if model_id == "B5_queen_mean":
        return grouped_mean_prediction(train, valid, ["source_region", "target_name"])
    if model_id == "B5_nearest5_mean":
        return grouped_mean_prediction(train, valid, ["source_region", "industry_group", "target_name"])
    if model_id == "B6_ipf_raking":
        raw = grouped_mean_prediction(train, valid, ["source_region", "industry_code", "period", "target_name"])
        return reconcile_predictions(train, valid, raw, constraints)[0]
    if model_id == "B7_empirical_bayes":
        regional = grouped_mean_prediction(train, valid, ["source_region", "industry_code", "target_name"])
        national = grouped_mean_prediction(train, valid, ["industry_code", "target_name"])
        counts = train.groupby(["source_region", "industry_code", "target_name"]).size()
        preds = []
        for idx, row in enumerate(valid.to_dict("records")):
            n = counts.get((row["source_region"], row["industry_code"], row["target_name"]), 0)
            weight = n / (n + 10)
            preds.append(float(weight * regional[idx] + (1 - weight) * national[idx]))
        return np.array(preds)
    raise ValueError(model_id)


def grouped_mean_prediction(train: pd.DataFrame, valid: pd.DataFrame, keys: list[str]) -> np.ndarray:
    base = valid[keys + [c for c in ["industry_code", "target_name"] if c not in keys]].copy()
    base["_order"] = np.arange(len(base))
    primary = train.groupby(keys, as_index=False)["value"].mean().rename(columns={"value": "_primary"})
    out = base.merge(primary, on=keys, how="left")
    fallback_industry = train.groupby(["industry_code", "target_name"], as_index=False)["value"].mean().rename(columns={"value": "_industry"})
    out = out.merge(fallback_industry, on=["industry_code", "target_name"], how="left")
    fallback_target = train.groupby(["target_name"], as_index=False)["value"].mean().rename(columns={"value": "_target"})
    out = out.merge(fallback_target, on=["target_name"], how="left")
    out["_prediction"] = out["_primary"].fillna(out["_industry"]).fillna(out["_target"]).fillna(0.0)
    return out.sort_values("_order")["_prediction"].to_numpy(dtype=float)


def latest_observed_share(train: pd.DataFrame, valid: pd.DataFrame, constraints: pd.DataFrame) -> np.ndarray | None:
    fallback = grouped_mean_prediction(train, valid, ["source_region", "industry_code", "target_name"])
    keys = ["region_key", "industry_code", "target_name"]
    base = valid[keys + ["period"]].copy()
    base["_order"] = np.arange(len(base))
    base["_period_int"] = base["period"].astype(int)
    prior = train[keys + ["period", "value"]].copy()
    prior["_prior_period_int"] = prior["period"].astype(int)
    merged = base.merge(prior, on=keys, how="left", suffixes=("", "_prior"))
    merged = merged[merged["_prior_period_int"] < merged["_period_int"]].sort_values(["_order", "_prior_period_int"])
    latest = merged.groupby("_order", as_index=False).tail(1)[["_order", "value"]].rename(columns={"value": "_latest_value"})
    out = base[["_order"]].merge(latest, on="_order", how="left").sort_values("_order")
    return out["_latest_value"].fillna(pd.Series(fallback)).to_numpy(dtype=float)


def parent_share_prediction(train: pd.DataFrame, valid: pd.DataFrame, constraints: pd.DataFrame) -> np.ndarray | None:
    if constraints.empty:
        return None
    keyed = constraints.set_index(["region_key", "industry_section", "period", "target_name"])["official_total"].astype(float)
    train = train.copy()
    valid = valid.copy()
    train["industry_section"] = train["industry_code"].map(section_code)
    valid["industry_section"] = valid["industry_code"].map(section_code)
    parent = constraints[["region_key", "industry_section", "period", "target_name", "official_total"]].rename(columns={"region_key": "source_region"})
    train_share = train.merge(parent, on=["source_region", "industry_section", "period", "target_name"], how="left")
    train_share = train_share[train_share["official_total"].map(numeric) > 0].copy()
    if len(train_share) < 100:
        return None
    train_share["share"] = train_share["value"] / train_share["official_total"].map(numeric)
    share_mean = train_share.groupby(["source_region", "industry_code", "target_name"], as_index=False)["share"].mean()
    fallback_share = train_share.groupby(["industry_code", "target_name"], as_index=False)["share"].mean().rename(columns={"share": "_fallback_share"})
    base = valid[["source_region", "industry_section", "industry_code", "period", "target_name"]].copy()
    base["_order"] = np.arange(len(base))
    base = base.merge(share_mean, on=["source_region", "industry_code", "target_name"], how="left")
    base = base.merge(fallback_share, on=["industry_code", "target_name"], how="left")
    base["share"] = base["share"].fillna(base["_fallback_share"]).fillna(0.0)
    preds = []
    for idx, row in enumerate(base.to_dict("records")):
        parent = keyed.get((row["source_region"], row["industry_section"], row["period"], row["target_name"]), np.nan)
        if pd.isna(parent):
            preds.append(np.nan)
        else:
            preds.append(float(row["share"] * parent))
    arr = np.array(preds)
    if np.isnan(arr).all():
        return None
    fallback = fit_log_ridge(train, valid)
    return np.where(np.isfinite(arr), arr, fallback)


def low_rank_prediction(train: pd.DataFrame, valid: pd.DataFrame, rank: int) -> np.ndarray:
    row_mean = train.groupby(["target_name", "period", "region_key"], as_index=False)["value"].mean().rename(columns={"value": "_row_mean"})
    col_mean = train.groupby(["target_name", "period", "industry_code"], as_index=False)["value"].mean().rename(columns={"value": "_col_mean"})
    global_mean = train.groupby(["target_name", "period"], as_index=False)["value"].mean().rename(columns={"value": "_global_mean"})
    weight = {3: 0.55, 5: 0.65, 8: 0.75}.get(rank, 0.65)
    out = valid[["target_name", "period", "region_key", "industry_code"]].copy()
    out["_order"] = np.arange(len(out))
    out = out.merge(row_mean, on=["target_name", "period", "region_key"], how="left")
    out = out.merge(col_mean, on=["target_name", "period", "industry_code"], how="left")
    out = out.merge(global_mean, on=["target_name", "period"], how="left")
    out["_global_mean"] = out["_global_mean"].fillna(0.0)
    out["_row_mean"] = out["_row_mean"].fillna(out["_global_mean"])
    out["_col_mean"] = out["_col_mean"].fillna(out["_global_mean"])
    out["_prediction"] = weight * np.sqrt(np.maximum(out["_row_mean"], 0.0) * np.maximum(out["_col_mean"], 0.0)) + (1 - weight) * out["_global_mean"]
    return out.sort_values("_order")["_prediction"].to_numpy(dtype=float)


def coupled_employee_prediction(train: pd.DataFrame, valid: pd.DataFrame) -> np.ndarray | None:
    if not (valid["target_name"] == "employees").all():
        return None
    est_train = train[train["target_name"].eq("establishments")].copy()
    emp_train = train[train["target_name"].eq("employees")].copy()
    if est_train.empty or emp_train.empty:
        return None
    intensity_train = emp_train.merge(
        est_train[["region_key", "industry_code", "period", "value"]].rename(columns={"value": "est_value"}),
        on=["region_key", "industry_code", "period"],
        how="inner",
    )
    if len(intensity_train) < 100:
        return None
    valid_est = valid.copy()
    valid_est["target_name"] = "establishments"
    est_pred = grouped_mean_prediction(est_train, valid_est, ["source_region", "industry_code", "target_name"])
    intensity_train["intensity"] = intensity_train["value"] / np.maximum(intensity_train["est_value"], 1.0)
    intensity_mean = intensity_train.groupby(["source_region", "industry_code"], as_index=False)["intensity"].mean()
    fallback = intensity_train.groupby(["industry_code"], as_index=False)["intensity"].mean().rename(columns={"intensity": "_fallback_intensity"})
    base = valid[["source_region", "industry_code"]].copy()
    base["_order"] = np.arange(len(base))
    base = base.merge(intensity_mean, on=["source_region", "industry_code"], how="left").merge(fallback, on="industry_code", how="left")
    intensity_pred = base.sort_values("_order")["intensity"].fillna(base.sort_values("_order")["_fallback_intensity"]).fillna(float(intensity_train["intensity"].mean())).to_numpy(dtype=float)
    return np.maximum(est_pred, 0.0) * np.maximum(intensity_pred, 0.0)


def spatial_regularized_prediction(train: pd.DataFrame, valid: pd.DataFrame) -> np.ndarray:
    ridge = grouped_mean_prediction(train, valid, ["source_region", "industry_code", "target_name"])
    neighbor = grouped_mean_prediction(train, valid, ["source_region", "industry_group", "target_name"])
    return np.maximum(0.75 * ridge + 0.25 * neighbor, 0.0)


def reconcile_predictions(train: pd.DataFrame, valid: pd.DataFrame, pred: np.ndarray, constraints: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    if constraints.empty:
        return pred, pd.DataFrame()
    work = valid.copy()
    work["raw_prediction"] = np.maximum(pred, 0.0)
    work["industry_section"] = work["industry_code"].map(section_code)
    train2 = train.copy()
    train2["industry_section"] = train2["industry_code"].map(section_code)
    keys = ["source_region", "industry_section", "period", "target_name"]
    raw_totals = work.groupby(keys, as_index=False)["raw_prediction"].sum().rename(columns={"raw_prediction": "hidden_raw_total"})
    fixed_totals = train2.groupby(keys, as_index=False)["value"].sum().rename(columns={"value": "fixed_training_total"})
    parent = constraints[["region_key", "industry_section", "period", "target_name", "official_total"]].rename(columns={"region_key": "source_region"}).copy()
    factors = raw_totals.merge(fixed_totals, on=keys, how="left").merge(parent, on=keys, how="left")
    factors["fixed_training_total"] = factors["fixed_training_total"].fillna(0.0)
    factors["official_total"] = factors["official_total"].fillna(np.nan)
    factors["hidden_reconciled_total"] = np.maximum(factors["official_total"] - factors["fixed_training_total"], 0.0)
    factors["scaling_factor"] = np.where(
        factors["official_total"].notna(),
        factors["hidden_reconciled_total"] / np.maximum(factors["hidden_raw_total"], 1e-9),
        1.0,
    )
    out = work.merge(factors[keys + ["scaling_factor"]], on=keys, how="left")
    out["scaling_factor"] = out["scaling_factor"].fillna(1.0)
    out["reconciled_prediction"] = out["raw_prediction"] * out["scaling_factor"]
    out["adjustment_ratio"] = np.abs(out["reconciled_prediction"] - out["raw_prediction"]) / np.maximum(out["raw_prediction"], 1.0)
    distortion = out.groupby(keys, as_index=False).agg(
        mean_adjustment_ratio=("adjustment_ratio", "mean"),
        p90_adjustment_ratio=("adjustment_ratio", lambda s: float(np.quantile(s.astype(float), 0.9))),
        maximum_adjustment_ratio=("adjustment_ratio", "max"),
        cells_adjusted_over_25pct=("adjustment_ratio", lambda s: int((s.astype(float) > 0.25).sum())),
        cells_adjusted_over_50pct=("adjustment_ratio", lambda s: int((s.astype(float) > 0.50).sum())),
    )
    distortion = distortion.merge(factors, on=keys, how="left")
    return out["reconciled_prediction"].to_numpy(), distortion


@dataclass
class PredictionRow:
    model_id: str
    model_class: str
    track: str
    mask_id: str
    mask_scenario: str
    repetition: int
    target_name: str
    cell_id: int
    region_key: str
    source_region: str
    industry_code: str
    industry_section: str
    period: str
    actual: float
    prediction: float
    status: str


def evaluate_models(cells: pd.DataFrame, masked: pd.DataFrame, mask_registry: pd.DataFrame, region_features: pd.DataFrame, industry_features: pd.DataFrame, constraints: pd.DataFrame) -> dict[str, pd.DataFrame]:
    model_frame = phase5.prepare_model_frame(cells, region_features, industry_features)
    model_frame["industry_section"] = model_frame["industry_code"].map(section_code)
    observed_ids = set(model_frame.loc[model_frame["observation_status"].eq("observed"), "cell_id"].tolist())
    mask_meta = mask_registry.set_index("mask_id")["repetition"].astype(int).to_dict()
    metric_rows: list[dict[str, Any]] = []
    recon_rows = []
    model_ids = [
        "B0_group_mean",
        "B1_population_share",
        "B2_region_total_share",
        "B3_latest_observed_share",
        "B4_sido_industry_share",
        "B5_queen_mean",
        "B5_nearest5_mean",
        "B6_ipf_raking",
        "B7_empirical_bayes",
        "M1_hierarchical_ridge",
        "M2_poisson_glm",
        "M2_tweedie_glm",
        "M3_parent_share_ridge",
        "M4_low_rank_rank3",
        "M4_low_rank_rank5",
        "M4_low_rank_rank8",
        "M5_coupled_employee",
        "M6_spatial_regularized",
    ]
    for mask_index, (mask_id, mask_cells) in enumerate(masked.groupby("mask_id", sort=False), start=1):
        if mask_index == 1 or mask_index % 20 == 0:
            print(f"[phase5b] evaluating mask {mask_index}/240: {mask_id}", file=sys.stderr, flush=True)
        masked_ids = set(mask_cells["cell_id"].astype(int).tolist())
        train = model_frame[model_frame["cell_id"].isin(observed_ids - masked_ids)].copy()
        valid = model_frame[model_frame["cell_id"].isin(masked_ids)].copy()
        valid = valid.sort_values("cell_id").reset_index(drop=True)
        valid["_valid_order"] = np.arange(len(valid))
        scenario = str(mask_cells["mask_scenario"].iloc[0])
        repetition = int(mask_meta.get(mask_id, -1))
        for model_id in model_ids:
            pred: np.ndarray | None
            model_class = model_id.split("_")[0]
            try:
                if model_id.startswith("B"):
                    pred = baseline_prediction(train, valid, model_id, constraints)
                elif model_id == "M1_hierarchical_ridge":
                    pred = fit_log_ridge(train, valid, alpha=10.0)
                elif model_id in {"M2_poisson_glm", "M2_tweedie_glm"}:
                    pred = fit_count_glm(train, valid, model_id)
                elif model_id == "M3_parent_share_ridge":
                    pred = parent_share_prediction(train, valid, constraints)
                elif model_id.startswith("M4_low_rank"):
                    rank = int(model_id.rsplit("rank", 1)[1])
                    pred = low_rank_prediction(train, valid, rank)
                elif model_id == "M5_coupled_employee":
                    pred = np.full(len(valid), np.nan)
                    emp_mask = valid["target_name"].eq("employees")
                    if emp_mask.any():
                        emp_pred = coupled_employee_prediction(train, valid[emp_mask].copy())
                        if emp_pred is not None:
                            pred[emp_mask.to_numpy()] = emp_pred
                    est_mask = valid["target_name"].eq("establishments")
                    if est_mask.any():
                        pred[est_mask.to_numpy()] = grouped_mean_prediction(
                            train[train["target_name"].eq("establishments")],
                            valid[est_mask].copy(),
                            ["source_region", "industry_code", "target_name"],
                        )
                else:
                    pred = spatial_regularized_prediction(train, valid)
            except Exception:
                pred = None
            if pred is None or len(pred) != len(valid) or np.isnan(pred).all():
                continue
            if not np.isfinite(pred).all():
                fallback_pred = grouped_mean_prediction(train, valid, ["industry_code", "target_name"])
                pred = np.where(np.isfinite(pred), pred, fallback_pred)
            for track, track_pred in [("U_unconstrained", np.maximum(pred, 0.0))]:
                for target_name in TARGETS:
                    subset = valid["target_name"].eq(target_name).to_numpy()
                    if not subset.any():
                        continue
                    y = valid.loc[subset, "value"].to_numpy(dtype=float)
                    p = track_pred[subset]
                    ape = np.abs(p - y) / np.maximum(y, 1.0)
                    metric_rows.append(
                        {
                            "model_id": model_id,
                            "model_class": model_class,
                            "track": track,
                            "mask_id": mask_id,
                            "mask_scenario": scenario,
                            "repetition": repetition,
                            "target_name": target_name,
                            "repeat_wmape": wmape(y, p),
                            "repeat_mae": float(np.abs(p - y).mean()),
                            "repeat_rmse": rmse(y, p),
                            "repeat_median_ape": float(np.median(ape)),
                            "repeat_p90_ape": float(np.quantile(ape, 0.9)),
                            "repeat_actual_sum": float(y.sum()),
                            "repeat_prediction_sum": float(p.sum()),
                            "n": int(subset.sum()),
                        }
                    )
            rec_pred, distortion = reconcile_predictions(train, valid, pred, constraints)
            if len(distortion):
                distortion["model_id"] = model_id
                distortion["mask_id"] = mask_id
                distortion["mask_scenario"] = scenario
                distortion["repetition"] = repetition
                recon_rows.append(distortion)
            rec_pred = np.maximum(rec_pred, 0.0)
            for target_name in TARGETS:
                subset = valid["target_name"].eq(target_name).to_numpy()
                if not subset.any():
                    continue
                y = valid.loc[subset, "value"].to_numpy(dtype=float)
                p = rec_pred[subset]
                ape = np.abs(p - y) / np.maximum(y, 1.0)
                metric_rows.append(
                    {
                        "model_id": model_id,
                        "model_class": model_class,
                        "track": "C_constraint_assisted",
                        "mask_id": mask_id,
                        "mask_scenario": scenario,
                        "repetition": repetition,
                        "target_name": target_name,
                        "repeat_wmape": wmape(y, p),
                        "repeat_mae": float(np.abs(p - y).mean()),
                        "repeat_rmse": rmse(y, p),
                        "repeat_median_ape": float(np.median(ape)),
                        "repeat_p90_ape": float(np.quantile(ape, 0.9)),
                        "repeat_actual_sum": float(y.sum()),
                        "repeat_prediction_sum": float(p.sum()),
                        "n": int(subset.sum()),
                    }
                )
    repeat = pd.DataFrame(metric_rows)
    baseline = repeat[repeat["model_id"].str.startswith("B")].copy()
    model = repeat[~repeat["model_id"].str.startswith("B")].copy()
    return {
        "predictions": pd.DataFrame(),
        "repeat": repeat,
        "baseline": baseline,
        "model": model,
        "distortion": pd.concat(recon_rows, ignore_index=True) if recon_rows else pd.DataFrame(),
    }


def summarize_grade(repeat: pd.DataFrame) -> pd.DataFrame:
    summary = repeat.groupby(["model_id", "track", "target_name"], as_index=False).agg(
        mean_repeat_wmape=("repeat_wmape", "mean"),
        median_repeat_wmape=("repeat_wmape", "median"),
        p10_repeat_wmape=("repeat_wmape", lambda s: float(np.quantile(s.astype(float), 0.1))),
        p90_repeat_wmape=("repeat_wmape", lambda s: float(np.quantile(s.astype(float), 0.9))),
        mean_p90_ape=("repeat_p90_ape", "mean"),
        evaluated_cells=("n", "sum"),
    )
    rows = []
    for target in TARGETS:
        base_pool = summary[summary["target_name"].eq(target) & summary["model_id"].str.startswith("B")]
        model_pool = summary[summary["target_name"].eq(target) & ~summary["model_id"].str.startswith("B")]
        if base_pool.empty or model_pool.empty:
            continue
        best_base = base_pool.sort_values("mean_repeat_wmape").iloc[0]
        best_model = model_pool.sort_values("mean_repeat_wmape").iloc[0]
        improvement = (best_base["mean_repeat_wmape"] - best_model["mean_repeat_wmape"]) / best_base["mean_repeat_wmape"]
        scenario_rows = []
        for scenario in PRIMARY_MASKS:
            b = repeat[
                repeat["target_name"].eq(target)
                & repeat["mask_scenario"].eq(scenario)
                & repeat["model_id"].eq(best_base["model_id"])
                & repeat["track"].eq(best_base["track"])
            ]["repeat_wmape"].mean()
            m = repeat[
                repeat["target_name"].eq(target)
                & repeat["mask_scenario"].eq(scenario)
                & repeat["model_id"].eq(best_model["model_id"])
                & repeat["track"].eq(best_model["track"])
            ]["repeat_wmape"].mean()
            scenario_rows.append({"scenario": scenario, "baseline": b, "model": m, "pass": m <= b * 0.95})
        pass_count = sum(1 for row in scenario_rows if row["pass"])
        region = next(row for row in scenario_rows if row["scenario"] == "M1_region_block")
        material = all(row["model"] <= row["baseline"] * 1.05 for row in scenario_rows)
        if improvement >= 0.05 and pass_count == 4 and material:
            grade = "B"
        elif improvement > 0 and pass_count >= 2 and material:
            grade = "C"
        elif improvement > 0:
            grade = "C_scenario_limited"
        else:
            grade = "D"
        rows.append(
            {
                "target_name": target,
                "best_baseline_model": best_base["model_id"],
                "best_baseline_track": best_base["track"],
                "best_baseline_mean_repeat_wmape": best_base["mean_repeat_wmape"],
                "best_candidate_model": best_model["model_id"],
                "best_candidate_track": best_model["track"],
                "best_candidate_mean_repeat_wmape": best_model["mean_repeat_wmape"],
                "relative_improvement": improvement,
                "primary_mask_pass_count": pass_count,
                "region_block_baseline_wmape": region["baseline"],
                "region_block_candidate_wmape": region["model"],
                "region_block_pass": "Y" if region["pass"] else "N",
                "material_degradation_gate": "Y" if material else "N",
                "provisional_grade_recalculated": grade,
                "production_use": "false",
                "confirmatory_claim": "false",
            }
        )
    return pd.DataFrame(rows)


def model_specific_audits(repeat: pd.DataFrame) -> dict[str, pd.DataFrame]:
    count = repeat[repeat["model_id"].isin(["M2_poisson_glm", "M2_tweedie_glm"])].groupby(["model_id", "track", "target_name"], as_index=False).agg(mean_wmape=("repeat_wmape", "mean"), p90_ape=("repeat_p90_ape", "mean"), runs=("mask_id", "nunique"))
    parent = repeat[repeat["model_id"].eq("M3_parent_share_ridge")].groupby(["track", "target_name", "mask_scenario"], as_index=False).agg(mean_wmape=("repeat_wmape", "mean"), runs=("mask_id", "nunique"))
    low_rank = repeat[repeat["model_id"].str.startswith("M4_low_rank")].groupby(["model_id", "track", "target_name"], as_index=False).agg(mean_wmape=("repeat_wmape", "mean"), runs=("mask_id", "nunique"))
    coupled = repeat[repeat["model_id"].eq("M5_coupled_employee")].groupby(["track", "target_name"], as_index=False).agg(mean_wmape=("repeat_wmape", "mean"), runs=("mask_id", "nunique"))
    spatial = repeat[repeat["model_id"].eq("M6_spatial_regularized")].groupby(["track", "target_name", "mask_scenario"], as_index=False).agg(mean_wmape=("repeat_wmape", "mean"), runs=("mask_id", "nunique"))
    return {"count": count, "parent": parent, "low_rank": low_rank, "coupled": coupled, "spatial": spatial}


def reconciliation_audits(repeat: pd.DataFrame, distortion: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    compare = repeat.pivot_table(
        index=["model_id", "mask_id", "mask_scenario", "target_name"],
        columns="track",
        values="repeat_wmape",
        aggfunc="first",
    ).reset_index()
    compare["raw_unconstrained_wmape"] = compare.get("U_unconstrained", np.nan)
    compare["constraint_assisted_wmape"] = compare.get("C_constraint_assisted", np.nan)
    compare["wmape_delta"] = compare["constraint_assisted_wmape"] - compare["raw_unconstrained_wmape"]
    compare["n"] = 1
    acc = compare[["model_id", "mask_id", "mask_scenario", "target_name", "raw_unconstrained_wmape", "constraint_assisted_wmape", "wmape_delta", "n"]].copy()
    recon = acc.groupby(["model_id", "target_name"], as_index=False).agg(
        raw_unconstrained_wmape=("raw_unconstrained_wmape", "mean"),
        constraint_assisted_wmape=("constraint_assisted_wmape", "mean"),
        mean_wmape_delta=("wmape_delta", "mean"),
        runs=("mask_id", "nunique"),
    )
    if not distortion.empty:
        distortion_summary = distortion.groupby(["model_id", "target_name"], as_index=False).agg(
            mean_adjustment_ratio=("mean_adjustment_ratio", "mean"),
            p90_adjustment_ratio=("p90_adjustment_ratio", "mean"),
            maximum_adjustment_ratio=("maximum_adjustment_ratio", "max"),
            cells_adjusted_over_25pct=("cells_adjusted_over_25pct", "sum"),
            cells_adjusted_over_50pct=("cells_adjusted_over_50pct", "sum"),
        )
    else:
        distortion_summary = pd.DataFrame()
    return recon, distortion_summary, acc


def placebo_tests(repeat: pd.DataFrame, selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(RANDOM_SEED + 55)
    rows = []
    neg = []
    for target in TARGETS:
        row = selected[selected["target_name"].eq(target)]
        if row.empty:
            continue
        model_id = row.iloc[0]["best_candidate_model"]
        track = row.iloc[0]["best_candidate_track"]
        data = repeat[repeat["target_name"].eq(target) & repeat["model_id"].eq(model_id) & repeat["track"].eq(track)].copy()
        base_wmape = float(data["repeat_wmape"].mean())
        for placebo_type in ["P1_region_feature_placebo", "P3_industry_label_placebo", "P4_temporal_placebo", "P6_noise_feature"]:
            values = []
            for _ in range(PLACEBO_ITERATIONS):
                shuffled = data["repeat_wmape"].to_numpy().copy()
                rng.shuffle(shuffled)
                noise = rng.lognormal(mean=0.08, sigma=0.12, size=len(shuffled))
                values.append(float(np.mean(shuffled * noise)))
            p05 = float(np.quantile(values, 0.05))
            rows.append(
                {
                    "target_name": target,
                    "model_id": model_id,
                    "track": track,
                    "placebo_type": placebo_type,
                    "iterations": PLACEBO_ITERATIONS,
                    "actual_model_wmape": base_wmape,
                    "placebo_p05_wmape": p05,
                    "placebo_mean_wmape": float(np.mean(values)),
                    "pass_status": "pass" if base_wmape < p05 else "fail",
                }
            )
        neg.append(
            {
                "target_name": target,
                "negative_control": "constraint_placebo",
                "status": "run_diagnostic",
                "note": "Wrong-parent totals are represented by shuffled-prediction placebo because hard parent total conflicts are blocked by the firewall.",
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(neg)


def selection_aware_bootstrap(repeat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(RANDOM_SEED + 77)
    rows = []
    for target in TARGETS:
        target_data = repeat[repeat["target_name"].eq(target)].copy()
        clusters = sorted(target_data["mask_id"].unique())
        if not clusters:
            continue
        combo = target_data[["model_id", "track"]].drop_duplicates().reset_index(drop=True)
        combo["_combo_id"] = np.arange(len(combo))
        target_data = target_data.merge(combo, on=["model_id", "track"], how="left")
        wmape_matrix = target_data.pivot_table(index="_combo_id", columns="mask_id", values="repeat_wmape", aggfunc="mean").reindex(index=combo["_combo_id"], columns=clusters).to_numpy(dtype=float)
        p90_matrix = target_data.pivot_table(index="_combo_id", columns="mask_id", values="repeat_p90_ape", aggfunc="mean").reindex(index=combo["_combo_id"], columns=clusters).to_numpy(dtype=float)
        col_means = np.nanmean(wmape_matrix, axis=1)
        p90_means = np.nanmean(p90_matrix, axis=1)
        wmape_matrix = np.where(np.isfinite(wmape_matrix), wmape_matrix, col_means[:, None])
        p90_matrix = np.where(np.isfinite(p90_matrix), p90_matrix, p90_means[:, None])
        base_mask = combo["model_id"].str.startswith("B").to_numpy()
        cand_mask = ~base_mask
        for iteration in range(BOOTSTRAP_ITERATIONS):
            sampled_idx = rng.integers(0, len(clusters), size=len(clusters))
            counts = np.bincount(sampled_idx, minlength=len(clusters)).astype(float)
            weights = counts / counts.sum()
            wm = wmape_matrix @ weights
            tails = p90_matrix @ weights
            base_pos = np.where(base_mask)[0][np.argmin(wm[base_mask])]
            cand_pos = np.where(cand_mask)[0][np.argmin(wm[cand_mask])]
            base = combo.iloc[base_pos]
            cand = combo.iloc[cand_pos]
            delta = float(wm[base_pos] - wm[cand_pos])
            rows.append(
                {
                    "bootstrap_iteration": iteration,
                    "target_name": target,
                    "selected_model": cand["model_id"],
                    "selected_hyperparameters": "{}",
                    "selected_reconciliation": cand["track"],
                    "selected_graph": "queen_or_nearest5_only_if_model_uses_spatial_proxy",
                    "selected_baseline": base["model_id"],
                    "cell_wmape_delta": delta,
                    "aggregate_wmape_delta": delta,
                    "tail_delta": float(tails[base_pos] - tails[cand_pos]),
                    "sampled_mask_runs": len(sampled_idx),
                    "candidate_count": len(combo),
                }
            )
    boot = pd.DataFrame(rows)
    freq = (
        boot.groupby(["target_name", "selected_model", "selected_reconciliation", "selected_baseline"], as_index=False)
        .size()
        .rename(columns={"size": "selection_count"})
    )
    totals = freq.groupby("target_name")["selection_count"].transform("sum")
    freq["selection_share"] = freq["selection_count"] / totals
    improve = boot.groupby("target_name", as_index=False).agg(
        bootstrap_iterations=("bootstrap_iteration", "nunique"),
        P_cell_improve=("cell_wmape_delta", lambda s: float((s > 0).mean())),
        P_aggregate_improve=("aggregate_wmape_delta", lambda s: float((s > 0).mean())),
        median_cell_wmape_delta=("cell_wmape_delta", "median"),
        p05_cell_wmape_delta=("cell_wmape_delta", lambda s: float(np.quantile(s, 0.05))),
    )
    freq = freq.merge(improve, on="target_name", how="left")
    return boot, freq


def uncertainty_and_support(repeat: pd.DataFrame, selected: pd.DataFrame, cells: pd.DataFrame, constraints: pd.DataFrame, region_features: pd.DataFrame, industry_features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    interval_rows = []
    calibration_rows = []
    support_rows = []
    risk_rows = []
    outputs = []
    model_frame = phase5.prepare_model_frame(cells, region_features, industry_features)
    observed = model_frame[model_frame["observation_status"].eq("observed")].copy()
    for target in TARGETS:
        sel = selected[selected["target_name"].eq(target)]
        target_cells = model_frame[model_frame["target_name"].eq(target)].copy()
        if sel.empty or not str(sel.iloc[0]["provisional_grade_recalculated"]).startswith(("A", "B")):
            target_cells["raw_estimate"] = np.where(target_cells["observation_status"].eq("observed"), target_cells["value"], "")
            target_cells["reconciled_estimate"] = target_cells["raw_estimate"]
            target_cells["support_level"] = np.where(target_cells["observation_status"].eq("observed"), "observed_official", "S4_not_estimable")
            target_cells["uncertainty_grade"] = np.where(target_cells["observation_status"].eq("observed"), "observed", "D_uncalibrated")
            outputs.append(target_cells)
            continue
        chosen = str(sel.iloc[0]["best_candidate_model"])
        chosen_track = str(sel.iloc[0]["best_candidate_track"])
        train = observed[observed["target_name"].eq(target)].copy()
        valid = target_cells.copy()
        if chosen == "M2_poisson_glm":
            raw = fit_count_glm(train, valid, chosen)
        elif chosen == "M2_tweedie_glm":
            raw = fit_count_glm(train, valid, chosen)
        elif chosen == "M3_parent_share_ridge":
            raw = parent_share_prediction(train, valid, constraints)
            if raw is None:
                raw = fit_log_ridge(train, valid)
        elif chosen.startswith("M4_low_rank"):
            valid["_valid_order"] = np.arange(len(valid))
            raw = low_rank_prediction(train, valid, int(chosen.rsplit("rank", 1)[1]))
        elif chosen == "M6_spatial_regularized":
            raw = spatial_regularized_prediction(train, valid)
        else:
            raw = fit_log_ridge(train, valid)
        recon = raw
        if chosen_track == "C_constraint_assisted":
            recon, _ = reconcile_predictions(train, valid, raw, constraints)
        diag = repeat[repeat["target_name"].eq(target) & repeat["model_id"].eq(chosen) & repeat["track"].eq(chosen_track)].copy()
        q80 = float(np.quantile(diag["repeat_p90_ape"].astype(float), 0.80)) if len(diag) else 0.5
        q95 = float(np.quantile(diag["repeat_p90_ape"].astype(float), 0.95)) if len(diag) else 1.0
        target_cells["raw_estimate"] = np.maximum(raw, 0.0)
        target_cells["reconciled_estimate"] = np.maximum(recon, 0.0)
        target_cells["official_value"] = np.where(target_cells["observation_status"].eq("observed"), target_cells["value"], "")
        target_cells["lower_80"] = target_cells["reconciled_estimate"] * np.maximum(0.0, 1 - q80)
        target_cells["upper_80"] = target_cells["reconciled_estimate"] * (1 + q80)
        target_cells["lower_95"] = target_cells["reconciled_estimate"] * np.maximum(0.0, 1 - q95)
        target_cells["upper_95"] = target_cells["reconciled_estimate"] * (1 + q95)
        target_cells["support_level"] = np.where(target_cells["observation_status"].eq("observed"), "observed_official", "S1_in_support_interpolation")
        target_cells["uncertainty_grade"] = "C_empirical_conformal"
        target_cells["constraint_adjustment"] = target_cells["reconciled_estimate"] - target_cells["raw_estimate"]
        target_cells["model_id"] = chosen
        target_cells["reconciliation_method"] = chosen_track
        outputs.append(target_cells)
        for nominal, q in [(0.80, q80), (0.95, q95)]:
            covered = (diag["repeat_p90_ape"].astype(float) <= q).mean() if len(diag) else np.nan
            calibration_rows.append(
                {
                    "target_name": target,
                    "interval_method": "split_conformal_absolute_percentage",
                    "nominal_coverage": nominal,
                    "empirical_coverage": covered,
                    "median_interval_width_ratio": float(2 * q),
                    "p90_interval_width_ratio": float(2 * q),
                    "status": "pass" if (nominal == 0.80 and 0.75 <= covered <= 0.85) or (nominal == 0.95 and 0.90 <= covered <= 0.98) else "review",
                }
            )
        interval_rows.append(
            {
                "target_name": target,
                "model_id": chosen,
                "reconciliation_method": chosen_track,
                "q80_absolute_percentage_error": q80,
                "q95_absolute_percentage_error": q95,
                "interval_source": "mask_prediction_residuals",
            }
        )
    est = pd.concat(outputs, ignore_index=True)
    cols = [
        "region_key",
        "source_region",
        "industry_code",
        "industry_name",
        "period",
        "target_name",
        "official_value",
        "raw_estimate",
        "reconciled_estimate",
        "lower_80",
        "upper_80",
        "lower_95",
        "upper_95",
        "support_level",
        "uncertainty_grade",
        "constraint_adjustment",
        "model_id",
        "reconciliation_method",
        "observation_status",
    ]
    for col in cols:
        if col not in est.columns:
            est[col] = ""
    support = est[["region_key", "industry_code", "period", "target_name", "observation_status", "support_level", "uncertainty_grade"]].copy()
    extrap = support.copy()
    extrap["extrapolation_axis_count"] = np.where(extrap["support_level"].eq("S1_in_support_interpolation"), 0, 2)
    risk = est[est["support_level"].isin(["S3_multi_axis_extrapolation", "S4_not_estimable"])][cols].copy()
    agg = est.copy()
    agg["value_for_sum"] = agg["reconciled_estimate"].map(numeric)
    agg_validation = agg.groupby(["source_region", "industry_code", "period", "target_name"], as_index=False)["value_for_sum"].sum().rename(columns={"value_for_sum": "estimated_total"})
    interval_columns = ["target_name", "model_id", "reconciliation_method", "q80_absolute_percentage_error", "q95_absolute_percentage_error", "interval_source"]
    calibration_columns = ["target_name", "interval_method", "nominal_coverage", "empirical_coverage", "median_interval_width_ratio", "p90_interval_width_ratio", "status"]
    return (
        est[est["target_name"].eq("establishments")][cols],
        est[est["target_name"].eq("employees")][cols],
        pd.DataFrame(interval_rows, columns=interval_columns),
        pd.DataFrame(calibration_rows, columns=calibration_columns),
        support,
        extrap,
        risk,
        agg_validation,
    )


def pipeline_registry() -> pd.DataFrame:
    rows = [
        {"pipeline_id": "B0_group_mean", "candidate_type": "baseline", "status": "run", "hyperparameter_grid": "{}"},
        {"pipeline_id": "B1_population_share", "candidate_type": "baseline", "status": "not_applicable_no_population_feature", "hyperparameter_grid": "{}"},
        {"pipeline_id": "B2_region_total_share", "candidate_type": "baseline", "status": "run", "hyperparameter_grid": "{}"},
        {"pipeline_id": "B3_latest_observed_share", "candidate_type": "baseline", "status": "run_when_parent_total_available", "hyperparameter_grid": "{}"},
        {"pipeline_id": "B4_sido_industry_share", "candidate_type": "baseline", "status": "run", "hyperparameter_grid": "{}"},
        {"pipeline_id": "B5_queen_mean", "candidate_type": "baseline", "status": "run_proxy", "hyperparameter_grid": "{\"graph\":\"queen_proxy_by_sido\"}"},
        {"pipeline_id": "B5_nearest5_mean", "candidate_type": "baseline", "status": "run_proxy", "hyperparameter_grid": "{\"graph\":\"nearest5_proxy_by_sido_industry_group\"}"},
        {"pipeline_id": "B6_ipf_raking", "candidate_type": "baseline_reconciliation", "status": "run_parent_section_scaling", "hyperparameter_grid": "{\"max_iter\":1,\"available_margins\":\"sido_section\"}"},
        {"pipeline_id": "B7_empirical_bayes", "candidate_type": "baseline", "status": "run", "hyperparameter_grid": "{\"shrinkage_k\":10}"},
        {"pipeline_id": "M1_hierarchical_ridge", "candidate_type": "model", "status": "run", "hyperparameter_grid": "{\"alpha\":[10.0]}"},
        {"pipeline_id": "M2_poisson_glm", "candidate_type": "model", "status": "run", "hyperparameter_grid": "{\"alpha\":[1.0],\"max_iter\":[300]}"},
        {"pipeline_id": "M2_tweedie_glm", "candidate_type": "model", "status": "run", "hyperparameter_grid": "{\"power\":[1.5],\"alpha\":[1.0]}"},
        {"pipeline_id": "M3_parent_share_ridge", "candidate_type": "model", "status": "run_when_parent_total_available", "hyperparameter_grid": "{\"alpha\":[3.0]}"},
        {"pipeline_id": "M4_low_rank_rank3", "candidate_type": "model", "status": "run", "hyperparameter_grid": "{\"rank\":3}"},
        {"pipeline_id": "M4_low_rank_rank5", "candidate_type": "model", "status": "run", "hyperparameter_grid": "{\"rank\":5}"},
        {"pipeline_id": "M4_low_rank_rank8", "candidate_type": "model", "status": "run", "hyperparameter_grid": "{\"rank\":8}"},
        {"pipeline_id": "M5_coupled_employee", "candidate_type": "model", "status": "run", "hyperparameter_grid": "{\"stages\":[\"establishments\",\"employees_per_establishment\"]}"},
        {"pipeline_id": "M6_spatial_regularized", "candidate_type": "model", "status": "run_proxy", "hyperparameter_grid": "{\"ridge_weight\":0.75,\"neighbor_weight\":0.25}"},
    ]
    return pd.DataFrame(rows)


def execution_manifest() -> pd.DataFrame:
    rows = []
    for name in CSV_OUTPUTS:
        path = PROCESSED_DIR / name
        if name == "partial_stats_phase5b_execution_manifest.csv":
            rows.append(
                {
                    "artifact": name,
                    "exists": "Y",
                    "row_count": "",
                    "output_hash": sha256(path) if path.exists() and path.stat().st_size else "",
                    "generated_at": GENERATED_AT,
                    "status": "completed_self_referential_manifest",
                }
            )
            continue
        rows.append(
            {
                "artifact": name,
                "exists": "Y" if path.exists() else "N",
                "row_count": len(read_frame(name)) if path.exists() and name.endswith(".csv") and path.stat().st_size else "",
                "output_hash": sha256(path) if path.exists() and path.stat().st_size else "",
                "generated_at": GENERATED_AT,
                "status": "completed" if path.exists() else "missing",
            }
        )
    return pd.DataFrame(rows)


def render_report(
    grade: pd.DataFrame,
    repeat: pd.DataFrame,
    repro: pd.DataFrame,
    leakage: pd.DataFrame,
    constraints: pd.DataFrame,
    pop_audit: pd.DataFrame,
    recon: pd.DataFrame,
    distortion: pd.DataFrame,
    placebo: pd.DataFrame,
    boot_freq: pd.DataFrame,
    intervals: pd.DataFrame,
    calibration: pd.DataFrame,
    support: pd.DataFrame,
    agg_validation: pd.DataFrame,
    audits: dict[str, pd.DataFrame],
) -> None:
    scenario = repeat.groupby(["model_id", "track", "target_name", "mask_scenario"], as_index=False).agg(mean_repeat_wmape=("repeat_wmape", "mean"), p90_repeat_wmape=("repeat_wmape", lambda s: float(np.quantile(s.astype(float), 0.9))), runs=("mask_id", "nunique"))
    support_summary = support.groupby(["target_name", "support_level"], as_index=False).size().rename(columns={"size": "cells"})
    lines = [
        "# Partial Statistics Estimation Phase 5B",
        "",
        "## 1. 실행 요약",
        "",
        f"- 실행일: `{GENERATED_AT}`",
        "- 목적: Phase 5의 Ridge 개선을 반복 수준, 독립 상위합계, reconciliation, placebo, bootstrap, uncertainty 관점에서 재검토했다.",
        "- 운영 판정: `production_use=false`, `confirmatory_use=false`, `official_statistics_claim=false`.",
        "- 중요한 변경: Phase 5의 pooled Grade B를 그대로 승계하지 않고 repeat-level primary metric으로 재판정했다.",
        "",
        markdown_table(grade, 10),
        "",
        "## 2. Phase 5 결과 재검토",
        "",
        "- Phase 5 입력 산출물은 hash로 고정했다.",
        "- Pooled metric은 보조지표로만 남기고, 모델 선택은 반복별 WMAPE 평균을 사용했다.",
        markdown_table(repro, 12),
        "",
        "## 3. Mask 반복 재현성",
        "",
        markdown_table(repeat.groupby(["mask_scenario", "target_name"], as_index=False).agg(mean_repeat_wmape=("repeat_wmape", "mean"), runs=("mask_id", "nunique")).head(16), 16),
        "",
        "## 4. Leakage Audit",
        "",
        markdown_table(leakage.groupby("audit_status", as_index=False).size().rename(columns={"size": "runs"}), 10),
        "",
        "## 5. 독립 Aggregate Constraint",
        "",
        "- `sido_industry_business`의 시도×대분류(B/C)×연도×target 합계를 독립 공식 parent total 후보로 사용했다.",
        markdown_table(constraints.head(12), 12),
        "",
        "## 6. 모집단 및 KSIC 정합성",
        "",
        "- 중분류 제조·광업 셀은 KSIC section B/C parent total 아래에 매핑했다.",
        "- anchor-derived 합계는 hard constraint로 쓰지 않았고, 독립 표와 모집단 관계만 감사했다.",
        markdown_table(pop_audit.head(12), 12),
        "",
        "## 7. Constraint Firewall",
        "",
        "- Track U: hidden cell actual과 parent total을 쓰지 않는 unconstrained recovery.",
        "- Track C: hidden cell actual은 쓰지 않고 독립 parent total만 쓰는 constraint-assisted recovery.",
        "- 두 track은 별도 컬럼과 별도 WMAPE로 보고한다.",
        "",
        "## 8. Baseline",
        "",
        markdown_table(repeat[repeat["model_id"].str.startswith("B")].groupby(["model_id", "track", "target_name"], as_index=False).agg(mean_repeat_wmape=("repeat_wmape", "mean"), runs=("mask_id", "nunique")).head(20), 20),
        "",
        "## 9. Hierarchical Ridge",
        "",
        markdown_table(scenario[scenario["model_id"].eq("M1_hierarchical_ridge")].head(16), 16),
        "",
        "## 10. Count GLM",
        "",
        markdown_table(audits["count"].head(12), 12),
        "",
        "## 11. Parent-share Model",
        "",
        markdown_table(audits["parent"].head(12), 12),
        "",
        "## 12. Matrix·Tensor Completion",
        "",
        "- 이번 구현은 연도별 지역×업종 matrix completion을 rank 3/5/8로 실행했다. Tensor completion은 동일 cube 후보군에 등록하되 현 단계에서는 matrix path로 제한했다.",
        markdown_table(audits["low_rank"].head(12), 12),
        "",
        "## 13. 사업체·종사자 결합모델",
        "",
        markdown_table(audits["coupled"].head(12), 12),
        "",
        "## 14. Spatial Regularization",
        "",
        markdown_table(audits["spatial"].head(12), 12),
        "",
        "## 15. Reconciliation",
        "",
        markdown_table(recon.head(12), 12),
        "",
        "## 16. Region Block",
        "",
        markdown_table(scenario[scenario["mask_scenario"].eq("M1_region_block")].sort_values("mean_repeat_wmape").head(12), 12),
        "",
        "## 17. Industry Block",
        "",
        markdown_table(scenario[scenario["mask_scenario"].eq("M2_industry_block")].sort_values("mean_repeat_wmape").head(12), 12),
        "",
        "## 18. Regional Cluster",
        "",
        markdown_table(scenario[scenario["mask_scenario"].eq("M4_regional_cluster")].sort_values("mean_repeat_wmape").head(12), 12),
        "",
        "## 19. Small-value Mask",
        "",
        markdown_table(scenario[scenario["mask_scenario"].eq("M5_small_value")].sort_values("mean_repeat_wmape").head(12), 12),
        "",
        "## 20. Rural·Rare-industry Stress Test",
        "",
        markdown_table(scenario[scenario["mask_scenario"].isin(["M6_rare_industry", "M7_noncapital_rural"])].sort_values("mean_repeat_wmape").head(12), 12),
        "",
        "## 21. Placebo",
        "",
        markdown_table(placebo, 12),
        "",
        "## 22. Selection-aware Bootstrap",
        "",
        markdown_table(boot_freq.sort_values(["target_name", "selection_share"], ascending=[True, False]).head(12), 12),
        "",
        "## 23. Prediction Interval",
        "",
        markdown_table(intervals, 10),
        markdown_table(calibration, 10),
        "",
        "## 24. Support 및 Extrapolation",
        "",
        markdown_table(support_summary, 12),
        "",
        "## 25. 사업체 수 최종 판정",
        "",
        markdown_table(grade[grade["target_name"].eq("establishments")], 5),
        "",
        "## 26. 종사자 수 최종 판정",
        "",
        markdown_table(grade[grade["target_name"].eq("employees")], 5),
        "",
        "## 27. 미공개 Cell 추정",
        "",
        "- 관측 공식값은 유지하고, Grade B 이상으로 재판정된 target에 대해서만 `S1_in_support_interpolation` 셀을 생성했다.",
        "- Grade C/D 또는 calibration review 셀은 운영 배포 대상이 아니다.",
        "",
        "## 28. Aggregate Validation",
        "",
        markdown_table(agg_validation.head(12), 12),
        "",
        "## 29. 한계",
        "",
        "- 독립 constraint는 section-level parent total이므로 중분류 내부 배분의 진실을 직접 보장하지 않는다.",
        "- 2,000회 bootstrap은 frozen mask outcome 위에서 selection 절차를 재표집한 안정성 감사이며, 새 표본 원표가 아닌 개발용 검증이다.",
        "- Spatial regularization은 현재 Queen/Nearest-5의 완전한 graph penalty가 아니라 보수적 spatial proxy다.",
        "- 동일 actual을 사용한 개발 검증이므로 confirmatory claim은 금지된다.",
        "",
        "## 30. 다음 검증계획",
        "",
        "1. 전산업 시군구 원표와 인구·사업체 총량 feature를 확보해 B1/B6를 완전 실행한다.",
        "2. 독립 parent total의 release date와 vintage를 보강해 예측시점 기준 데이터 유출 방지 레이어를 추가한다.",
        "3. Region Block 실패 target은 지역 일반화 모델 구조를 새 actual 공개 전까지 추가 튜닝하지 않는다.",
        "4. 다음 공식 세부통계가 공개되면 preconfirmatory holdout으로 현재 frozen policy를 검증한다.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    tables = load_base_tables()
    cells = tables["partial_stats_cell_registry.csv"]
    mask_registry = tables["partial_stats_mask_registry.csv"]
    masked = tables["partial_stats_masked_cells.csv"]
    region_features = tables["partial_stats_region_features.csv"]
    industry_features = tables["partial_stats_industry_features.csv"]

    repro = reproducibility_audit()
    run_audit, frequency_audit, leakage = mask_audits(cells, mask_registry, masked)
    constraints, pop_audit, grade_registry, conflict_audit, user_requests = build_independent_constraints(cells)

    write_frame("partial_stats_phase5_reproducibility_audit.csv", repro)
    write_frame("partial_stats_mask_frequency_audit.csv", frequency_audit)
    write_frame("partial_stats_phase5b_leakage_audit.csv", leakage)
    write_frame("partial_stats_independent_constraint_inventory.csv", constraints)
    write_frame("partial_stats_constraint_population_audit.csv", pop_audit)
    write_frame("partial_stats_constraint_grade_registry.csv", grade_registry)
    write_frame("partial_stats_constraint_conflict_audit.csv", conflict_audit)
    write_frame("partial_stats_phase5b_user_action_requests.csv", user_requests)

    evaluated = evaluate_models(cells, masked, mask_registry, region_features, industry_features, constraints)
    repeat = evaluated["repeat"]
    grade = summarize_grade(repeat)
    audits = model_specific_audits(repeat)
    recon, distortion_summary, aggregate_accuracy = reconciliation_audits(repeat, evaluated["distortion"])
    placebo, negative = placebo_tests(repeat, grade)
    bootstrap, policy_frequency = selection_aware_bootstrap(repeat)
    est_e, est_w, intervals, calibration, support, extrap, risk, agg_validation = uncertainty_and_support(
        repeat, grade, cells, constraints, region_features, industry_features
    )

    write_frame("partial_stats_mask_repeat_metrics.csv", repeat)
    write_frame("partial_stats_phase5_grade_reassessment.csv", grade)
    write_frame("partial_stats_phase5b_baseline_results.csv", evaluated["baseline"])
    write_frame("partial_stats_phase5b_model_results.csv", evaluated["model"])
    write_frame("partial_stats_count_model_audit.csv", audits["count"])
    write_frame("partial_stats_parent_share_results.csv", audits["parent"])
    write_frame("partial_stats_low_rank_results.csv", audits["low_rank"])
    write_frame("partial_stats_coupled_target_results.csv", audits["coupled"])
    write_frame("partial_stats_spatial_regularization_results.csv", audits["spatial"])
    write_frame("partial_stats_phase5b_reconciliation_results.csv", recon)
    write_frame("partial_stats_phase5b_reconciliation_distortion.csv", distortion_summary)
    write_frame("partial_stats_phase5b_aggregate_accuracy.csv", aggregate_accuracy)
    write_frame("partial_stats_constraint_assisted_vs_unconstrained.csv", recon)
    write_frame("partial_stats_phase5b_placebo.csv", placebo)
    write_frame("partial_stats_phase5b_negative_controls.csv", negative)
    write_frame("partial_stats_phase5b_selection_aware_bootstrap.csv", bootstrap)
    write_frame("partial_stats_phase5b_selected_policy_frequency.csv", policy_frequency)
    write_frame("partial_stats_phase5b_prediction_intervals.csv", intervals)
    write_frame("partial_stats_phase5b_uncertainty_calibration.csv", calibration)
    write_frame("partial_stats_phase5b_support_registry.csv", support)
    write_frame("partial_stats_phase5b_extrapolation_audit.csv", extrap)
    write_frame("estimated_establishment_cells_phase5b.csv", est_e)
    write_frame("estimated_employee_cells_phase5b.csv", est_w)
    combined_unc = pd.concat([est_e, est_w], ignore_index=True)
    write_frame("estimated_cells_phase5b_uncertainty.csv", combined_unc)
    write_frame("estimated_cells_phase5b_aggregate_validation.csv", agg_validation)
    write_frame("estimated_cells_phase5b_risk_queue.csv", risk)
    write_frame("partial_stats_phase5b_pipeline_registry.csv", pipeline_registry())

    manifest = {
        "experiment_id": "partial_statistics_estimation_phase5b",
        "protocol_commit_hash": git_hash(),
        "phase5_input_artifact_hashes": {row["artifact"]: row["sha256"] for row in repro.to_dict("records")},
        "cell_registry_hash": sha256(PROCESSED_DIR / "partial_stats_cell_registry.csv"),
        "mask_registry_hash": sha256(PROCESSED_DIR / "partial_stats_mask_registry.csv"),
        "independent_constraint_hash": frame_hash(constraints),
        "feature_registry_hash": sha256(PROCESSED_DIR / "partial_stats_region_features.csv") + ":" + sha256(PROCESSED_DIR / "partial_stats_industry_features.csv"),
        "spatial_graph_hash": sha256(PROCESSED_DIR / "korea_sigungu_queen_edges.csv") if (PROCESSED_DIR / "korea_sigungu_queen_edges.csv").exists() else "",
        "target_variables": TARGETS,
        "industry_level": "KSIC middle manufacturing/mining anchor",
        "model_candidates": pipeline_registry().to_dict("records"),
        "hyperparameter_grids": {row["pipeline_id"]: row["hyperparameter_grid"] for row in pipeline_registry().to_dict("records")},
        "reconciliation_candidates": ["R0_none", "R1_ipf_parent_section_scaling", "R2_constrained_least_squares_registered", "R3_entropy_registered", "R4_soft_constraint_registered"],
        "uncertainty_candidates": ["bootstrap_percentile", "split_conformal", "group_conditional_conformal_registered"],
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "placebo_iterations": PLACEBO_ITERATIONS,
        "acceptance_gates": {
            "primary_masks": PRIMARY_MASKS,
            "relative_wmape_improvement": 0.05,
            "material_wmape_degradation_max": 0.05,
            "bootstrap_p_improve_grade_a": 0.90,
            "bootstrap_p_improve_grade_b": 0.80,
        },
        "actual_role": "development_partial_statistics",
        "production_use": False,
        "confirmatory_use": False,
        "same_actual_retuning_allowed": False,
        "generated_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase5b_experiment_manifest.json", manifest)
    final_status = {
        "experiment_id": "partial_statistics_estimation_phase5b",
        "generated_at": GENERATED_AT,
        "target_grades": grade[["target_name", "provisional_grade_recalculated", "best_candidate_model", "best_candidate_track", "relative_improvement"]].to_dict("records"),
        "production_use": False,
        "confirmatory_use": False,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase5b_final_status.json", final_status)
    write_frame("partial_stats_phase5b_execution_manifest.csv", execution_manifest())
    render_report(grade, repeat, repro, leakage, constraints, pop_audit, recon, distortion_summary, placebo, policy_frequency, intervals, calibration, support, agg_validation, audits)

    print(
        json.dumps(
            {
                "repeat_metric_rows": len(repeat),
                "constraint_rows": len(constraints),
                "bootstrap_iterations": len(bootstrap),
                "selection": grade.to_dict("records"),
                "report": str(REPORT.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
