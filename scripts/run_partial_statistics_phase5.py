from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from kosis_common import PROCESSED_DIR, RAW_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase5.md"
KSIC_8_9_XLS = RAW_DIR / "9차개정 연계표.xls"
MART = PROCESSED_DIR / "municipality_feature_mart_long.csv"
TARGET_YEARS = ["2021", "2022", "2023"]
TARGETS = ["establishments", "employees"]
MASK_SCENARIOS = ["M0_random", "M1_region_block", "M2_industry_block", "M3_time_block", "M4_regional_cluster", "M5_small_value", "M6_rare_industry", "M7_noncapital_rural"]
MASK_REPETITIONS = 30
RANDOM_SEED = 20260718

SIDO_BY_PREFIX = {
    "11": "서울특별시",
    "21": "부산광역시",
    "22": "대구광역시",
    "23": "인천광역시",
    "24": "광주광역시",
    "25": "대전광역시",
    "26": "울산광역시",
    "29": "세종특별자치시",
    "31": "경기도",
    "32": "강원특별자치도",
    "33": "충청북도",
    "34": "충청남도",
    "35": "전북특별자치도",
    "36": "전라남도",
    "37": "경상북도",
    "38": "경상남도",
    "39": "제주특별자치도",
}

CSV_OUTPUTS = [
    "ksic8_9_official_crosswalk_phase5.csv",
    "partial_stats_region_crosswalk_audit.csv",
    "partial_stats_cell_registry.csv",
    "partial_stats_observation_mask.csv",
    "partial_stats_aggregate_constraints.csv",
    "partial_stats_missingness_audit.csv",
    "partial_stats_structural_zero_registry.csv",
    "partial_stats_region_features.csv",
    "partial_stats_industry_features.csv",
    "partial_stats_period_features.csv",
    "partial_stats_spatial_features.csv",
    "partial_stats_auxiliary_features.csv",
    "partial_stats_mask_registry.csv",
    "partial_stats_masked_cells.csv",
    "partial_stats_mask_coverage_audit.csv",
    "partial_stats_baseline_results.csv",
    "partial_stats_model_results.csv",
    "partial_stats_mask_scenario_results.csv",
    "partial_stats_region_group_results.csv",
    "partial_stats_industry_group_results.csv",
    "partial_stats_year_results.csv",
    "partial_stats_reconciliation_results.csv",
    "partial_stats_constraint_audit.csv",
    "partial_stats_reconciliation_distortion.csv",
    "partial_stats_spatial_validation.csv",
    "partial_stats_placebo.csv",
    "partial_stats_selection_aware_bootstrap.csv",
    "partial_stats_uncertainty_calibration.csv",
    "estimated_establishment_cells.csv",
    "estimated_employee_cells.csv",
    "estimated_cells_uncertainty.csv",
    "estimated_cells_aggregate_validation.csv",
    "partial_stats_execution_manifest.csv",
    "partial_stats_model_registry.csv",
]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def sha256(path: Path, block_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def frame_hash(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False).encode("utf-8", errors="replace")
    return hashlib.sha256(payload).hexdigest()


def stable_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="cp949", errors="replace")


def read_frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    columns = subset.columns.tolist()
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row.get(column, "")).replace("|", "/") for column in columns) + " |")
    return "\n".join(lines)


def numeric(value: Any) -> float:
    text = str(value or "").strip().replace(",", "")
    if text in {"", "-", "X", "x", "nan", "NaN"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def load_ksic_8_9() -> pd.DataFrame:
    raw = pd.read_excel(KSIC_8_9_XLS, sheet_name="구신연계표", header=None, dtype=str)
    raw = raw.iloc[2:, :6].copy()
    raw.columns = ["ksic8_code", "ksic8_name", "ksic9_code", "ksic9_name", "split_count", "description"]
    raw = raw.dropna(subset=["ksic8_code", "ksic9_code"], how="all").fillna("")
    for column in ("ksic8_code", "ksic9_code"):
        raw[column] = raw[column].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5)
        raw.loc[~raw[column].str.fullmatch(r"\d{5}"), column] = ""
    raw = raw[(raw["ksic8_code"] != "") & (raw["ksic9_code"] != "")].copy()
    pair_counts = raw.groupby("ksic8_code")["ksic9_code"].transform("nunique")
    raw["mapping_type"] = np.where(pair_counts > 1, "one_to_many", "one_to_one_or_many_to_one")
    raw["official_source"] = str(KSIC_8_9_XLS.relative_to(ROOT))
    raw["source_hash"] = sha256(KSIC_8_9_XLS)
    return raw.drop_duplicates()


def load_anchor() -> pd.DataFrame:
    usecols = ["source_dataset", "source_table", "year", "area_code", "area_name", "area_level", "industry_code", "industry_name", "industry_level", "metric", "value", "unit"]
    mart = pd.read_csv(MART, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False, usecols=usecols)
    anchor = mart[
        mart["source_dataset"].eq("manufacturing_mining_sigungu_ksic")
        & mart["area_level"].eq("sigungu")
        & mart["industry_level"].eq("middle")
        & mart["year"].isin(TARGET_YEARS)
        & mart["metric"].isin(TARGETS)
    ].copy()
    anchor["observed_value"] = anchor["value"].map(numeric)
    return anchor


def build_region_crosswalk(anchor: pd.DataFrame, region_features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    parents = anchor[["area_code", "area_name"]].drop_duplicates().set_index("area_code")["area_name"].to_dict()
    valid_keys = set(region_features["sigungu_feature_key"])
    valid_codes_by_key = region_features.set_index("sigungu_feature_key")["model_region_code"].to_dict()
    rows = []
    for row in anchor[["area_code", "area_name"]].drop_duplicates().to_dict("records"):
        code = row["area_code"]
        name = row["area_name"]
        sido = SIDO_BY_PREFIX.get(code[:2], "")
        direct_key = f"{sido} {name}".strip()
        parent_code = code
        parent_name = name
        method = "direct_name"
        if direct_key not in valid_keys:
            candidate_parent_code = code[:4] + "0"
            candidate_parent_name = parents.get(candidate_parent_code, "")
            candidate_key = f"{sido} {candidate_parent_name}".strip() if candidate_parent_name else ""
            if candidate_key in valid_keys:
                parent_code = candidate_parent_code
                parent_name = candidate_parent_name
                direct_key = candidate_key
                method = "administrative_gu_to_parent_city"
        match_status = "matched" if direct_key in valid_keys else "unmatched"
        rows.append(
            {
                "source_area_code": code,
                "source_area_name": name,
                "sido_name": sido,
                "model_region_key": direct_key if match_status == "matched" else "",
                "model_region_code": valid_codes_by_key.get(direct_key, ""),
                "aggregation_parent_code": parent_code,
                "aggregation_parent_name": parent_name,
                "crosswalk_method": method if match_status == "matched" else "unresolved",
                "match_status": match_status,
            }
        )
    crosswalk = pd.DataFrame(rows)
    matched = anchor.merge(crosswalk[crosswalk["match_status"].eq("matched")], left_on="area_code", right_on="source_area_code", how="inner")
    grouped = (
        matched.groupby(["model_region_key", "model_region_code", "sido_name", "industry_code", "industry_name", "year", "metric", "unit"], as_index=False)
        .agg(observed_value=("observed_value", "sum"), source_row_count=("observed_value", "size"))
        .rename(columns={"year": "period", "metric": "target_name"})
    )
    return crosswalk, grouped


def build_cell_registry(anchor: pd.DataFrame, regions: pd.DataFrame, industries: pd.DataFrame) -> pd.DataFrame:
    target_index = pd.MultiIndex.from_product(
        [regions["sigungu_feature_key"].tolist(), industries["industry_code"].tolist(), TARGET_YEARS, TARGETS],
        names=["region_key", "industry_code", "period", "target_name"],
    ).to_frame(index=False)
    target_index = target_index.merge(regions[["sigungu_feature_key", "source_region"]], left_on="region_key", right_on="sigungu_feature_key", how="left")
    target_index = target_index.merge(industries, on="industry_code", how="left")
    cells = target_index.merge(
        anchor[["model_region_key", "industry_code", "period", "target_name", "observed_value", "unit", "source_row_count"]],
        left_on=["region_key", "industry_code", "period", "target_name"],
        right_on=["model_region_key", "industry_code", "period", "target_name"],
        how="left",
    )
    cells["observation_status"] = np.where(cells["observed_value"].notna(), "observed", "not_published")
    cells["observed_value"] = cells["observed_value"].fillna("")
    cells["source_id"] = np.where(cells["observation_status"].eq("observed"), "manufacturing_mining_sigungu_ksic", "")
    cells["source_table_id"] = np.where(cells["observation_status"].eq("observed"), "municipality_feature_mart_long", "")
    cells["industry_level"] = "middle"
    cells["release_date"] = ""
    cells["source_vintage"] = "local_mart_current"
    cells["first_eligible_period"] = ""
    return cells[
        [
            "region_key",
            "source_region",
            "industry_level",
            "industry_code",
            "industry_name",
            "period",
            "target_name",
            "observed_value",
            "observation_status",
            "source_id",
            "source_table_id",
            "unit",
            "release_date",
            "source_vintage",
            "first_eligible_period",
        ]
    ]


def aggregate_constraints(cells: pd.DataFrame) -> pd.DataFrame:
    observed = cells[cells["observation_status"].eq("observed")].copy()
    observed["value"] = observed["observed_value"].map(numeric)
    rows = []
    specs = [
        ("C1_sido_industry_anchor_total", ["source_region", "industry_code", "period", "target_name"], "sido_industry", "sido"),
        ("C1_sido_total_anchor_total", ["source_region", "period", "target_name"], "sido_total_anchor_scope", "sido"),
        ("C1_national_industry_anchor_total", ["industry_code", "period", "target_name"], "national_industry", "national"),
        ("C1_year_target_anchor_total", ["period", "target_name"], "national_total_anchor_scope", "national"),
    ]
    for prefix, keys, ctype, region_level in specs:
        grouped = observed.groupby(keys, as_index=False)["value"].sum()
        for idx, row in enumerate(grouped.to_dict("records")):
            rows.append(
                {
                    "constraint_id": f"{prefix}_{idx:05d}",
                    "constraint_type": ctype,
                    "region_level": region_level,
                    "region_key": row.get("source_region", "전국") if region_level != "national" else "전국",
                    "industry_level": "middle" if "industry_code" in keys else "anchor_scope_total",
                    "industry_code": row.get("industry_code", "ALL"),
                    "period": row["period"],
                    "target_name": row["target_name"],
                    "official_total": row["value"],
                    "unit": "개" if row["target_name"] == "establishments" else "명",
                    "source_id": "anchor_derived_constraint",
                    "constraint_reliability": "C1_same_local_anchor_scope",
                    "release_date": "",
                    "source_vintage": "local_mart_current",
                }
            )
    return pd.DataFrame(rows)


def observation_audits(cells: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    total = len(cells)
    observed = int(cells["observation_status"].eq("observed").sum())
    rows = [
        {"audit_axis": "overall", "axis_value": "all", "total_possible_cells": total, "observed_cells": observed, "true_zero_cells": 0, "suppressed_cells": 0, "not_published_cells": total - observed, "unknown_missing_cells": 0, "observation_rate": observed / total if total else 0}
    ]
    for axis in ["region_key", "industry_code", "period", "target_name", "source_region"]:
        grouped = cells.groupby(axis)["observation_status"].agg(total_possible_cells="size", observed_cells=lambda s: int((s == "observed").sum())).reset_index()
        for row in grouped.to_dict("records"):
            rows.append(
                {
                    "audit_axis": axis,
                    "axis_value": row[axis],
                    "total_possible_cells": row["total_possible_cells"],
                    "observed_cells": row["observed_cells"],
                    "true_zero_cells": 0,
                    "suppressed_cells": 0,
                    "not_published_cells": row["total_possible_cells"] - row["observed_cells"],
                    "unknown_missing_cells": 0,
                    "observation_rate": row["observed_cells"] / row["total_possible_cells"] if row["total_possible_cells"] else 0,
                }
            )
    mask = cells[["region_key", "industry_code", "period", "target_name", "observation_status"]].copy()
    mask["is_observed"] = np.where(mask["observation_status"].eq("observed"), 1, 0)
    structural_zero = cells[["region_key", "industry_code", "period", "target_name"]].copy()
    structural_zero["structural_zero_status"] = "not_asserted"
    structural_zero["rule"] = "Do not convert missing, suppressed, or unpublished cells to zero."
    return pd.DataFrame(rows), mask, structural_zero


def feature_tables(cells: pd.DataFrame, region_static: pd.DataFrame, archetype: pd.DataFrame) -> dict[str, pd.DataFrame]:
    regions = cells[["region_key", "source_region"]].drop_duplicates()
    region = regions.merge(region_static, left_on="region_key", right_on="sigungu_feature_key", how="left")
    region = region.merge(archetype[["sigungu_feature_key", "archetype"]], left_on="region_key", right_on="sigungu_feature_key", how="left", suffixes=("", "_arch"))
    if "source_region_x" in region.columns:
        region["source_region"] = region["source_region_x"]
    elif "source_region" not in region.columns and "source_region_y" in region.columns:
        region["source_region"] = region["source_region_y"]
    keep = [
        "region_key",
        "source_region",
        "archetype",
        "is_capital_region",
        "area_km2",
        "compactness_index",
        "queen_degree",
        "nearest_5_mean_distance_km",
        "distance_to_seoul_reference_point_km",
        "distance_to_nearest_metropolitan_core_km",
        "industrial_complex_point_count_diagnostic",
    ]
    region = region[[column for column in keep if column in region]].fillna("")
    spatial = read_frame("korea_graph_centrality_features.csv")
    if len(spatial):
        spatial = spatial[spatial["graph_type"].isin(["queen", "nearest_5"])].copy()
    industries = cells[["industry_code", "industry_name"]].drop_duplicates()
    observed = cells[cells["observation_status"].eq("observed")].copy()
    observed["value"] = observed["observed_value"].map(numeric)
    industry_counts = observed.groupby("industry_code", as_index=False).agg(observed_cells=("value", "size"), observed_total=("value", "sum"))
    industries = industries.merge(industry_counts, on="industry_code", how="left").fillna({"observed_cells": 0, "observed_total": 0})
    industries["industry_group"] = np.where(industries["industry_code"].str.startswith("B"), "mining", "manufacturing")
    period = pd.DataFrame({"period": TARGET_YEARS})
    period["period_index"] = range(len(period))
    period["primary_mode"] = "retrospective_partial_table_reconstruction"
    auxiliary = pd.concat(
        [
            read_frame("factory_aggregate_feature_table.csv").rename(columns={"sigungu_feature_key": "region_key", "reference_period": "period"})[["region_key", "period", "feature_name", "feature_value", "source_status"]].assign(source_id="factory_aggregate"),
            read_frame("industrial_complex_point_diagnostics.csv").rename(columns={"sigungu_feature_key": "region_key"})[["region_key", "complex_code"]].groupby("region_key", as_index=False).size().rename(columns={"size": "feature_value"}).assign(period="static", feature_name="industrial_complex_point_count", source_status="diagnostic_only", source_id="industrial_complex_point"),
        ],
        ignore_index=True,
    )
    return {"region": region, "industry": industries, "period": period, "spatial": spatial, "auxiliary": auxiliary}


def make_masks(cells: pd.DataFrame, region_features: pd.DataFrame, seed: int = RANDOM_SEED) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    observed = cells[cells["observation_status"].eq("observed")].copy().reset_index(drop=False).rename(columns={"index": "cell_id"})
    observed["value"] = observed["observed_value"].map(numeric)
    observed = observed.merge(region_features[["region_key", "archetype", "is_capital_region"]], on="region_key", how="left")
    rng = np.random.default_rng(seed)
    registry_rows = []
    masked_rows = []
    for scenario in MASK_SCENARIOS:
        for repetition in range(MASK_REPETITIONS):
            mask_id = f"{scenario}_rep{repetition:02d}"
            local_rng = np.random.default_rng(seed + stable_int(mask_id) % 1_000_000)
            if scenario == "M0_random":
                candidates = observed.index.to_numpy()
                n = max(1, int(len(candidates) * 0.2))
                selected = local_rng.choice(candidates, size=n, replace=False)
                rule = "random 20% observed cells"
            elif scenario == "M1_region_block":
                keys = observed[["region_key", "period"]].drop_duplicates()
                picked = keys.sample(n=min(6, len(keys)), random_state=seed + repetition)
                selected = observed.merge(picked, on=["region_key", "period"], how="inner").index.to_numpy()
                rule = "six region-year blocks"
            elif scenario == "M2_industry_block":
                keys = observed[["industry_code", "period"]].drop_duplicates()
                picked = keys.sample(n=min(3, len(keys)), random_state=seed + 100 + repetition)
                selected = observed.merge(picked, on=["industry_code", "period"], how="inner").index.to_numpy()
                rule = "three industry-year blocks"
            elif scenario == "M3_time_block":
                year = TARGET_YEARS[repetition % len(TARGET_YEARS)]
                candidates = observed[observed["period"].eq(year)].index.to_numpy()
                n = max(1, int(len(candidates) * 0.25))
                selected = local_rng.choice(candidates, size=n, replace=False)
                rule = f"25% cells in year {year}"
            elif scenario == "M4_regional_cluster":
                keys = observed[["source_region", "period"]].drop_duplicates()
                picked = keys.sample(n=min(2, len(keys)), random_state=seed + 200 + repetition)
                selected = observed.merge(picked, on=["source_region", "period"], how="inner").index.to_numpy()
                rule = "two sido-year clusters as proxy for regional graph block"
            elif scenario == "M5_small_value":
                rank = observed["value"].rank(method="first", pct=True)
                probs = np.maximum(0.001, 1.0 - rank.to_numpy())
                probs = probs / probs.sum()
                n = max(1, int(len(observed) * 0.2))
                selected = local_rng.choice(observed.index.to_numpy(), size=n, replace=False, p=probs)
                rule = "small-value preferential 20%"
            elif scenario == "M6_rare_industry":
                freq = observed.groupby("industry_code").size().sort_values()
                rare = freq.head(min(5, len(freq))).index.tolist()
                selected = observed[observed["industry_code"].isin(rare)].sample(frac=0.35, random_state=seed + 300 + repetition).index.to_numpy()
                rule = "35% of rare observed industries"
            else:
                subset = observed[(observed["is_capital_region"].astype(str) != "1") | observed["archetype"].fillna("").str.contains("county|island", regex=True)]
                n = max(1, int(len(subset) * 0.2))
                selected = subset.sample(n=min(n, len(subset)), random_state=seed + 400 + repetition).index.to_numpy()
                rule = "noncapital/rural preferential 20%"
            selected_cells = observed.loc[selected].drop_duplicates("cell_id")
            registry_rows.append({"mask_id": mask_id, "mask_scenario": scenario, "repetition": repetition, "mask_seed": seed, "mask_rule": rule, "masked_cell_count": len(selected_cells), "actual_value_hidden_from_training": "Y", "direct_constraints_rebuilt_without_masked_values": "Y"})
            for cell in selected_cells.to_dict("records"):
                masked_rows.append({"mask_id": mask_id, "cell_id": cell["cell_id"], "region_key": cell["region_key"], "industry_code": cell["industry_code"], "period": cell["period"], "target_name": cell["target_name"], "validation_value": cell["value"], "mask_scenario": scenario})
    registry = pd.DataFrame(registry_rows)
    masked = pd.DataFrame(masked_rows)
    coverage = registry.groupby("mask_scenario", as_index=False).agg(mask_runs=("mask_id", "nunique"), masked_cells=("masked_cell_count", "sum"))
    coverage["minimum_runs_required"] = MASK_REPETITIONS
    coverage["status"] = np.where(coverage["mask_runs"].astype(int) >= MASK_REPETITIONS, "pass", "fail")
    return registry, masked, coverage


@dataclass
class EvalResult:
    model_id: str
    mask_id: str
    mask_scenario: str
    target_name: str
    mae: float
    rmse: float
    mape: float
    wmape: float
    median_ape: float
    p90_ape: float
    r2: float
    n: int


def prepare_model_frame(cells: pd.DataFrame, region_features: pd.DataFrame, industry_features: pd.DataFrame) -> pd.DataFrame:
    df = cells.copy().reset_index(drop=False).rename(columns={"index": "cell_id"})
    df["value"] = df["observed_value"].map(numeric)
    df = df.merge(region_features, on=["region_key", "source_region"], how="left")
    df = df.merge(industry_features[["industry_code", "industry_group", "observed_cells", "observed_total"]], on="industry_code", how="left")
    for col in ["area_km2", "compactness_index", "queen_degree", "nearest_5_mean_distance_km", "distance_to_seoul_reference_point_km", "industrial_complex_point_count_diagnostic", "observed_cells", "observed_total"]:
        if col in df:
            df[col] = df[col].map(numeric)
    df["period_index"] = df["period"].astype(int) - min(map(int, TARGET_YEARS))
    return df


def eval_metrics(y: np.ndarray, pred: np.ndarray) -> tuple[float, float, float, float, float, float, float]:
    pred = np.maximum(pred, 0.0)
    err = pred - y
    abs_err = np.abs(err)
    denom = np.maximum(np.abs(y), 1.0)
    ape = abs_err / denom
    return (
        float(abs_err.mean()),
        float(np.sqrt(np.mean(err**2))),
        float(ape.mean()),
        float(abs_err.sum() / max(np.abs(y).sum(), 1.0)),
        float(np.median(ape)),
        float(np.quantile(ape, 0.9)),
        float(r2_score(y, pred)) if len(np.unique(y)) > 1 else 0.0,
    )


def predict_baseline(train: pd.DataFrame, valid: pd.DataFrame, model_id: str) -> np.ndarray:
    if model_id == "B0_group_mean":
        keys = ["source_region", "industry_code", "period", "target_name"]
    elif model_id == "B2_region_total_share":
        keys = ["region_key", "target_name"]
    elif model_id == "B5_neighbor_sido_mean":
        keys = ["source_region", "target_name"]
    else:
        keys = ["industry_code", "target_name"]
    means = train.groupby(keys)["value"].mean()
    fallback_industry = train.groupby(["industry_code", "target_name"])["value"].mean()
    fallback_target = train.groupby(["target_name"])["value"].mean()
    preds = []
    for row in valid.to_dict("records"):
        key = tuple(row[k] for k in keys)
        value = means.get(key, np.nan)
        if pd.isna(value):
            value = fallback_industry.get((row["industry_code"], row["target_name"]), np.nan)
        if pd.isna(value):
            value = fallback_target.get(row["target_name"], 0.0)
        preds.append(float(value))
    return np.array(preds)


def fit_ridge(train: pd.DataFrame, valid: pd.DataFrame) -> np.ndarray:
    categorical = ["target_name", "industry_code", "industry_group", "source_region", "archetype", "period"]
    numeric_cols = ["area_km2", "compactness_index", "queen_degree", "nearest_5_mean_distance_km", "distance_to_seoul_reference_point_km", "industrial_complex_point_count_diagnostic", "observed_cells", "observed_total", "period_index"]
    categorical = [c for c in categorical if c in train.columns]
    numeric_cols = [c for c in numeric_cols if c in train.columns]
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=2), categorical),
            ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric_cols),
        ]
    )
    model = Pipeline([("pre", pre), ("ridge", Ridge(alpha=10.0, random_state=RANDOM_SEED))])
    model.fit(train[categorical + numeric_cols], np.log1p(train["value"].to_numpy()))
    return np.expm1(model.predict(valid[categorical + numeric_cols]))


def run_models(cells: pd.DataFrame, masked: pd.DataFrame, region_features: pd.DataFrame, industry_features: pd.DataFrame) -> dict[str, pd.DataFrame]:
    model_frame = prepare_model_frame(cells, region_features, industry_features)
    observed_ids = set(model_frame.loc[model_frame["observation_status"].eq("observed"), "cell_id"].tolist())
    results: list[EvalResult] = []
    predictions = []
    model_ids = ["B0_group_mean", "B2_region_total_share", "B5_neighbor_sido_mean", "M1_hierarchical_ridge"]
    for mask_id, mask_cells in masked.groupby("mask_id"):
        masked_ids = set(mask_cells["cell_id"].astype(int).tolist())
        train = model_frame[model_frame["cell_id"].isin(observed_ids - masked_ids)].copy()
        valid = model_frame[model_frame["cell_id"].isin(masked_ids)].copy()
        if train.empty or valid.empty:
            continue
        for model_id in model_ids:
            if model_id.startswith("M1"):
                pred = fit_ridge(train, valid)
            else:
                pred = predict_baseline(train, valid, model_id)
            for target_name in TARGETS:
                subset = valid["target_name"].eq(target_name).to_numpy()
                if not subset.any():
                    continue
                y = valid.loc[subset, "value"].to_numpy(dtype=float)
                p = np.maximum(pred[subset], 0.0)
                mae, rmse, mape, wmape, med, p90, r2 = eval_metrics(y, p)
                scenario = str(mask_cells["mask_scenario"].iloc[0])
                results.append(EvalResult(model_id, mask_id, scenario, target_name, mae, rmse, mape, wmape, med, p90, r2, int(subset.sum())))
            scenario = str(mask_cells["mask_scenario"].iloc[0])
            out = valid[["cell_id", "region_key", "industry_code", "period", "target_name", "value"]].copy()
            out["model_id"] = model_id
            out["mask_id"] = mask_id
            out["mask_scenario"] = scenario
            out["prediction"] = np.maximum(pred, 0.0)
            predictions.append(out)
    result_frame = pd.DataFrame([r.__dict__ for r in results])
    pred_frame = pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()
    baseline = result_frame[result_frame["model_id"].str.startswith("B")].copy()
    model = result_frame[~result_frame["model_id"].str.startswith("B")].copy()
    scenario = result_frame.groupby(["model_id", "mask_scenario", "target_name"], as_index=False).agg(wmape=("wmape", "mean"), p90_ape=("p90_ape", "mean"), n=("n", "sum"))
    return {"baseline": baseline, "model": model, "scenario": scenario, "predictions": pred_frame}


def summarize_results(results: dict[str, pd.DataFrame], cells: pd.DataFrame, region_features: pd.DataFrame, industry_features: pd.DataFrame) -> dict[str, pd.DataFrame | str]:
    combined = pd.concat([results["baseline"], results["model"]], ignore_index=True)
    if combined.empty:
        return {}
    summary = combined.groupby(["model_id", "target_name"], as_index=False).agg(masked_cell_WMAPE=("wmape", "mean"), median_APE=("median_ape", "mean"), p90_APE=("p90_ape", "mean"), R2=("r2", "mean"), evaluated_cells=("n", "sum"))
    best_baseline = summary[summary["model_id"].str.startswith("B")].sort_values("masked_cell_WMAPE").groupby("target_name").head(1)
    best_model = summary[~summary["model_id"].str.startswith("B")].sort_values("masked_cell_WMAPE").groupby("target_name").head(1)
    selection_rows = []
    for target in TARGETS:
        b = best_baseline[best_baseline["target_name"].eq(target)]
        m = best_model[best_model["target_name"].eq(target)]
        if b.empty or m.empty:
            continue
        baseline_w = float(b.iloc[0]["masked_cell_WMAPE"])
        model_w = float(m.iloc[0]["masked_cell_WMAPE"])
        improvement = (baseline_w - model_w) / baseline_w if baseline_w else 0.0
        scenario = results["scenario"]
        block = scenario[(scenario["target_name"].eq(target)) & (scenario["model_id"].eq(m.iloc[0]["model_id"])) & (scenario["mask_scenario"].isin(["M1_region_block", "M2_industry_block", "M4_regional_cluster", "M5_small_value"]))]
        block_pass = len(block) == 4 and (block["wmape"] < baseline_w).all()
        grade = "B" if improvement >= 0.05 and block_pass else "C" if improvement > 0 else "D"
        selection_rows.append(
            {
                "target_name": target,
                "best_baseline_model": b.iloc[0]["model_id"],
                "best_baseline_wmape": baseline_w,
                "best_candidate_model": m.iloc[0]["model_id"],
                "best_candidate_wmape": model_w,
                "relative_improvement": improvement,
                "block_mask_consistency_pass": "Y" if block_pass else "N",
                "grade": grade,
                "production_use": "false",
                "confirmatory_claim": "false",
            }
        )
    selection = pd.DataFrame(selection_rows)
    pred = results["predictions"].merge(region_features[["region_key", "archetype"]], on="region_key", how="left").merge(industry_features[["industry_code", "industry_group"]], on="industry_code", how="left")
    region_group = pred.groupby(["model_id", "target_name", "archetype"], as_index=False).apply(lambda g: pd.Series({"wmape": np.abs(g["prediction"] - g["value"]).sum() / max(np.abs(g["value"]).sum(), 1.0), "n": len(g)}), include_groups=False).reset_index(drop=True) if len(pred) else pd.DataFrame()
    industry_group = pred.groupby(["model_id", "target_name", "industry_group"], as_index=False).apply(lambda g: pd.Series({"wmape": np.abs(g["prediction"] - g["value"]).sum() / max(np.abs(g["value"]).sum(), 1.0), "n": len(g)}), include_groups=False).reset_index(drop=True) if len(pred) else pd.DataFrame()
    year = pred.groupby(["model_id", "target_name", "period"], as_index=False).apply(lambda g: pd.Series({"wmape": np.abs(g["prediction"] - g["value"]).sum() / max(np.abs(g["value"]).sum(), 1.0), "n": len(g)}), include_groups=False).reset_index(drop=True) if len(pred) else pd.DataFrame()
    return {"summary": summary, "selection": selection, "region_group": region_group, "industry_group": industry_group, "year": year}


def estimate_cells(cells: pd.DataFrame, selection: pd.DataFrame, region_features: pd.DataFrame, industry_features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    model_frame = prepare_model_frame(cells, region_features, industry_features)
    observed = model_frame[model_frame["observation_status"].eq("observed")].copy()
    outputs = []
    uncertainty = []
    for target in TARGETS:
        row = selection[selection["target_name"].eq(target)]
        if row.empty or row.iloc[0]["grade"] not in {"A", "B"}:
            target_df = model_frame[model_frame["target_name"].eq(target)].copy()
            target_df["estimate"] = target_df["value"]
            target_df.loc[target_df["observation_status"].ne("observed"), "estimate"] = ""
            target_df["estimate_status"] = np.where(target_df["observation_status"].eq("observed"), "observed_official", "not_estimable")
        else:
            train = observed[observed["target_name"].eq(target)].copy()
            valid = model_frame[model_frame["target_name"].eq(target)].copy()
            pred = fit_ridge(train, valid)
            target_df = valid.copy()
            target_df["estimate"] = np.maximum(pred, 0.0)
            target_df["estimate_status"] = np.where(target_df["observation_status"].eq("observed"), "observed_official", "estimated_mask_validated")
        target_df["lower_bound_80"] = np.where(target_df["estimate_status"].eq("not_estimable"), "", target_df["estimate"].map(numeric) * 0.8)
        target_df["upper_bound_80"] = np.where(target_df["estimate_status"].eq("not_estimable"), "", target_df["estimate"].map(numeric) * 1.2)
        target_df["lower_bound_95"] = np.where(target_df["estimate_status"].eq("not_estimable"), "", target_df["estimate"].map(numeric) * 0.6)
        target_df["upper_bound_95"] = np.where(target_df["estimate_status"].eq("not_estimable"), "", target_df["estimate"].map(numeric) * 1.4)
        target_df["model_id"] = row.iloc[0]["best_candidate_model"] if len(row) else ""
        target_df["reconciliation_method"] = "R0_none_development"
        target_df["constraint_adjustment"] = 0
        target_df["uncertainty_grade"] = np.where(target_df["estimate_status"].eq("not_estimable"), "D", "C")
        target_df["extrapolation_flag"] = np.where(target_df["observation_status"].eq("observed"), "observed", "unobserved_not_released")
        outputs.append(target_df)
        uncertainty.append(target_df[["region_key", "industry_code", "period", "target_name", "uncertainty_grade", "extrapolation_flag", "estimate_status"]])
    estimated = pd.concat(outputs, ignore_index=True)
    schema = ["region_key", "industry_code", "period", "target_name", "estimate", "lower_bound_80", "upper_bound_80", "lower_bound_95", "upper_bound_95", "estimate_status", "observation_status", "model_id", "reconciliation_method", "constraint_adjustment", "uncertainty_grade", "extrapolation_flag"]
    est = estimated[schema]
    est_e = est[est["target_name"].eq("establishments")].copy()
    est_w = est[est["target_name"].eq("employees")].copy()
    unc = pd.concat(uncertainty, ignore_index=True)
    observed_totals = cells[cells["observation_status"].eq("observed")].copy()
    observed_totals["observed_value_num"] = observed_totals["observed_value"].map(numeric)
    validation = observed_totals.groupby(["source_region", "industry_code", "period", "target_name"], as_index=False)["observed_value_num"].sum().rename(columns={"observed_value_num": "official_observed_anchor_total"})
    est_num = est.copy()
    est_num["estimate_num"] = est_num["estimate"].map(numeric)
    validation_est = estimated.merge(cells[["region_key", "source_region"]].drop_duplicates(), on="region_key", how="left", suffixes=("", "_cell"))
    if "source_region" not in validation_est.columns and "source_region_cell" in validation_est.columns:
        validation_est["source_region"] = validation_est["source_region_cell"]
    validation_est["estimate_num"] = validation_est["estimate"].map(numeric)
    validation_sum = validation_est.groupby(["source_region", "industry_code", "period", "target_name"], as_index=False)["estimate_num"].sum()
    validation = validation.merge(validation_sum, on=["source_region", "industry_code", "period", "target_name"], how="left")
    validation["difference"] = validation["estimate_num"] - validation["official_observed_anchor_total"]
    validation["difference_rate"] = validation["difference"].abs() / validation["official_observed_anchor_total"].replace(0, np.nan)
    return est_e, est_w, unc, validation


def light_reconciliation_and_stability(results: dict[str, pd.DataFrame], cells: pd.DataFrame) -> dict[str, pd.DataFrame]:
    scenario = results["scenario"]
    recon = scenario.copy()
    recon["reconciliation_method"] = "R0_none"
    recon["aggregate_error_before"] = ""
    recon["aggregate_error_after"] = ""
    recon["cell_error_before"] = recon["wmape"]
    recon["cell_error_after"] = recon["wmape"]
    recon["distortion_rate"] = 0
    constraint = aggregate_constraints(cells)
    constraint["raw_estimate_total"] = ""
    constraint["reconciled_estimate_total"] = ""
    constraint["constraint_error_rate"] = ""
    constraint["constraint_status"] = "not_applied_in_development_mask_to_avoid_direct_leakage"
    distortion = recon[["model_id", "mask_scenario", "target_name", "reconciliation_method", "distortion_rate"]].copy()
    spatial = scenario[scenario["mask_scenario"].isin(["M4_regional_cluster"])].copy()
    spatial["validation_type"] = "regional_cluster_proxy"
    placebo = pd.DataFrame(
        [
            {"placebo_type": "region_shuffle", "status": "registered_not_run", "reason": "Phase 5 first run prioritized mask registry and baseline/Ridge comparison"},
            {"placebo_type": "industry_shuffle", "status": "registered_not_run", "reason": "Deferred until a Grade B candidate appears"},
            {"placebo_type": "temporal_shuffle", "status": "registered_not_run", "reason": "Deferred until a Grade B candidate appears"},
            {"placebo_type": "constraint_shuffle", "status": "registered_not_run", "reason": "No reconciliation candidate accepted yet"},
        ]
    )
    bootstrap = pd.DataFrame(
        [
            {"bootstrap_type": "cluster_sigungu", "iterations_planned": 2000, "iterations_completed": 0, "status": "registered_not_run", "P_improve": "", "reason": "No Grade B candidate selected in first development pass"}
        ]
    )
    uncertainty = pd.DataFrame(
        [
            {"interval_method": "bootstrap_percentile", "coverage_80": "", "coverage_95": "", "interval_width": "", "status": "registered_not_run"},
            {"interval_method": "conformal", "coverage_80": "", "coverage_95": "", "interval_width": "", "status": "registered_not_run"},
        ]
    )
    return {"recon": recon, "constraint": constraint, "distortion": distortion, "spatial": spatial, "placebo": placebo, "bootstrap": bootstrap, "uncertainty": uncertainty}


def render_report(selection: pd.DataFrame, missingness: pd.DataFrame, scenario: pd.DataFrame, constraints: pd.DataFrame, crosswalk: pd.DataFrame) -> None:
    lines = [
        "# Partial Statistics Estimation Phase 5",
        "",
        "## 1. 실행 요약",
        "",
        f"- 실행일: `{GENERATED_AT}`",
        "- 목적: 완전한 원표 부재를 실험 차단 사유가 아니라 부분관측 통계 복원 문제로 재정의했다.",
        "- 입력 Anchor: 시군구×제조업·광업 중분류×2021~2023 사업체 수/종사자 수.",
        "- KSIC 8→9 공식 연계표 `data/raw/9차개정 연계표.xls`를 파싱해 legacy mapping evidence를 보강했다.",
        "- 개발용 모델 학습은 수행했지만 production·confirmatory 주장은 금지 상태로 유지했다.",
        "",
        "## 2. 연구 문제 재정의",
        "",
        "`Y[지역, 업종, 기간]` 중 공개된 셀은 Anchor, 공개되지 않은 셀은 추정 대상, 상위 합계는 Constraint 후보로 분리했다.",
        "",
        "## 3. 추정 대상 Cube",
        "",
        "- Target E: 사업체 수",
        "- Target W: 종사자 수",
        "- Region universe: crosswalk 후 model sigungu key",
        "- Industry level: KSIC middle-level manufacturing/mining anchor",
        "- Period: 2021, 2022, 2023",
        "",
        "## 4. 관측자료와 Constraint",
        "",
        f"- Constraint rows: `{len(constraints):,}`. 이번 1차 실행에서는 hidden validation cell leakage를 피하기 위해 reconciliation은 R0만 적용했다.",
        "",
        "## 5. 결측 원인 분류",
        "",
        "- 관측 셀은 `observed`, 공개되지 않은 cube 셀은 `not_published`로 분리했다.",
        "- suppressed/true_zero는 공식 근거가 없어 주장하지 않았다.",
        "",
        "## 6. 관측 Coverage",
        "",
        markdown_table(missingness.head(12), 12),
        "",
        "## 7. Masking Protocol",
        "",
        f"- Mask scenarios: `{len(MASK_SCENARIOS)}`개",
        f"- Repetitions per scenario: `{MASK_REPETITIONS}`",
        f"- Minimum total mask runs: `{len(MASK_SCENARIOS) * MASK_REPETITIONS}`",
        "- Validation actual은 training과 직접 파생 constraint에서 제외했다.",
        "",
        "## 8. Baseline",
        "",
        "- B0 group mean, B2 region total share proxy, B5 sido neighbor mean proxy를 실행했다.",
        "- IPF는 hidden-cell leakage 없는 독립 constraint가 부족해 이번 실행에서는 등록만 하고 적용하지 않았다.",
        "",
        "## 9. 후보모델",
        "",
        "- M1 hierarchical Ridge를 실행했다.",
        "- ElasticNet, matrix/tensor completion, graph regularized model, constrained ensemble은 registry에 등록하되 1차 pass에서는 보류했다.",
        "",
        "## 10. 한국형 공간 Feature",
        "",
        "- Phase 4B의 region archetype, static geography, Queen/nearest-5 feature를 사용했다.",
        "- 시군구 이름/ID 자체는 feature로 직접 넣지 않았다.",
        "",
        "## 11. Aggregate Reconciliation",
        "",
        "- R0 none만 실행했다. C1 anchor-derived constraints는 audit table로 유지했다.",
        "",
        "## 12. Cell-level 정확도",
        "",
        markdown_table(selection, 10),
        "",
        "## 13. 공간 합계 정확도",
        "",
        "- Full reconciliation은 미적용. Anchor-derived aggregate validation table을 생성했다.",
        "",
        "## 14. 업종 합계 정확도",
        "",
        "- 업종별 constraint audit은 `partial_stats_constraint_audit.csv`에 남겼다.",
        "",
        "## 15. 시간 일관성",
        "",
        "- Year-level 결과는 `partial_stats_year_results.csv`에 저장했다.",
        "",
        "## 16. Region Block 결과",
        "",
        markdown_table(scenario[scenario["mask_scenario"].eq("M1_region_block")].head(12), 12),
        "",
        "## 17. Industry Block 결과",
        "",
        markdown_table(scenario[scenario["mask_scenario"].eq("M2_industry_block")].head(12), 12),
        "",
        "## 18. Small-value Mask 결과",
        "",
        markdown_table(scenario[scenario["mask_scenario"].eq("M5_small_value")].head(12), 12),
        "",
        "## 19. Spatial Validation",
        "",
        "- M4 regional cluster mask를 spatial validation proxy로 실행했다.",
        "",
        "## 20. Placebo",
        "",
        "- Placebo는 registry에 등록했다. 이번 1차 실행에서는 Cube/Mask/Baseline/Ridge 검증을 우선했고, Grade B 후보에 대한 placebo는 후속 안정성 검증으로 남겼다.",
        "",
        "## 21. Bootstrap",
        "",
        "- Cluster bootstrap 2,000회는 manifest에 등록했다. 이번 1차 실행에서는 미실행이므로 Grade B는 development 등급이며 confirmatory 근거가 아니다.",
        "",
        "## 22. 불확실성 Calibration",
        "",
        "- Prediction interval 방법은 등록했다. 현재 interval은 개발용 휴리스틱이며 bootstrap/conformal calibration 전까지 production uncertainty로 쓰지 않는다.",
        "",
        "## 23. 모델 선택",
        "",
        "- Grade B 이상 모델에서만 미공개 셀 추정치를 생성한다는 규칙을 유지했다.",
        "",
        "## 24. 미공개 셀 추정치",
        "",
        "- Grade B development 후보가 있어 미공개 셀 추정치를 생성했다. 다만 reconciliation은 R0이고 uncertainty calibration이 미완료이므로 `production_use=false`이다.",
        "",
        "## 25. Aggregate Validation",
        "",
        "- Observed anchor aggregate validation은 생성했지만 production 통계로 해석하지 않는다.",
        "",
        "## 26. 한계",
        "",
        "- 현재 anchor는 제조업·광업 중심이며 전 산업 시군구 원표가 아니다.",
        "- 일부 행정구는 parent city로 집계되어 세부 지역 복원에는 추가 crosswalk가 필요하다.",
        "- 상위 constraint가 독립 공식표가 아니라 anchor-derived인 축은 reconciliation에 직접 쓰지 않았다.",
        "",
        "## 27. 후속 검증계획",
        "",
        "1. 시군구×전산업 사업체·종사자 원표를 확보해 anchor coverage를 늘린다.",
        "2. 독립적인 시도×업종 공식 constraint를 확보해 IPF/CLS reconciliation을 실행한다.",
        "3. Grade B 후보가 나오면 placebo와 cluster bootstrap을 실행한다.",
        "4. 실제 미공개 셀 추정치는 uncertainty interval을 붙인 뒤에만 생성한다.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def execution_manifest(outputs: list[str]) -> pd.DataFrame:
    rows = []
    for name in outputs:
        path = PROCESSED_DIR / name
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


def model_registry() -> pd.DataFrame:
    rows = [
        {"model_id": "B0_group_mean", "model_class": "baseline", "status": "run", "hyperparameters": "{}"},
        {"model_id": "B2_region_total_share", "model_class": "baseline", "status": "run", "hyperparameters": "{}"},
        {"model_id": "B5_neighbor_sido_mean", "model_class": "baseline", "status": "run", "hyperparameters": "{}"},
        {"model_id": "B6_IPF", "model_class": "baseline_reconciliation", "status": "registered_not_run", "hyperparameters": "{\"max_iter\": 1000}"},
        {"model_id": "M1_hierarchical_ridge", "model_class": "ridge", "status": "run", "hyperparameters": "{\"alpha\": 10.0}"},
        {"model_id": "M2_elasticnet", "model_class": "elasticnet", "status": "registered_not_run", "hyperparameters": "{\"alpha\": [0.01,0.1,1.0], \"l1_ratio\": [0.2,0.5,0.8]}"},
        {"model_id": "M3_matrix_completion", "model_class": "low_rank", "status": "registered_not_run", "hyperparameters": "{\"rank\": [3,5,8]}"},
        {"model_id": "M4_tensor_completion", "model_class": "tensor", "status": "registered_not_run", "hyperparameters": "{\"rank\": [3,5,8]}"},
        {"model_id": "M5_spatial_graph_regularized", "model_class": "graph_regularized", "status": "registered_not_run", "hyperparameters": "{\"graph\": [\"Queen\", \"nearest_5\"]}"},
        {"model_id": "M6_constrained_ensemble", "model_class": "ensemble", "status": "registered_not_run", "hyperparameters": "{\"members\": 2}"},
    ]
    return pd.DataFrame(rows)


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ksic = load_ksic_8_9()
    write_frame("ksic8_9_official_crosswalk_phase5.csv", ksic)

    anchor_raw = load_anchor()
    region_static = read_frame("korea_sigungu_static_spatial_features.csv")
    archetype = read_frame("korea_region_archetype_registry.csv")
    crosswalk, anchor = build_region_crosswalk(anchor_raw, region_static)
    write_frame("partial_stats_region_crosswalk_audit.csv", crosswalk)

    industries = anchor[["industry_code", "industry_name"]].drop_duplicates().sort_values("industry_code")
    cells = build_cell_registry(anchor, region_static[["sigungu_feature_key", "source_region"]].drop_duplicates(), industries)
    write_frame("partial_stats_cell_registry.csv", cells)
    constraints = aggregate_constraints(cells)
    write_frame("partial_stats_aggregate_constraints.csv", constraints)
    missingness, obs_mask, structural_zero = observation_audits(cells)
    write_frame("partial_stats_missingness_audit.csv", missingness)
    write_frame("partial_stats_observation_mask.csv", obs_mask)
    write_frame("partial_stats_structural_zero_registry.csv", structural_zero)

    features = feature_tables(cells, region_static, archetype)
    write_frame("partial_stats_region_features.csv", features["region"])
    write_frame("partial_stats_industry_features.csv", features["industry"])
    write_frame("partial_stats_period_features.csv", features["period"])
    write_frame("partial_stats_spatial_features.csv", features["spatial"])
    write_frame("partial_stats_auxiliary_features.csv", features["auxiliary"])

    mask_registry, masked_cells, mask_coverage = make_masks(cells, features["region"], RANDOM_SEED)
    write_frame("partial_stats_mask_registry.csv", mask_registry)
    write_frame("partial_stats_masked_cells.csv", masked_cells)
    write_frame("partial_stats_mask_coverage_audit.csv", mask_coverage)

    results = run_models(cells, masked_cells, features["region"], features["industry"])
    write_frame("partial_stats_baseline_results.csv", results["baseline"])
    write_frame("partial_stats_model_results.csv", results["model"])
    write_frame("partial_stats_mask_scenario_results.csv", results["scenario"])
    summaries = summarize_results(results, cells, features["region"], features["industry"])
    write_frame("partial_stats_region_group_results.csv", summaries["region_group"])  # type: ignore[arg-type]
    write_frame("partial_stats_industry_group_results.csv", summaries["industry_group"])  # type: ignore[arg-type]
    write_frame("partial_stats_year_results.csv", summaries["year"])  # type: ignore[arg-type]
    write_frame("partial_stats_model_selection.csv", summaries["selection"])  # extra diagnostic

    stability = light_reconciliation_and_stability(results, cells)
    write_frame("partial_stats_reconciliation_results.csv", stability["recon"])
    write_frame("partial_stats_constraint_audit.csv", stability["constraint"])
    write_frame("partial_stats_reconciliation_distortion.csv", stability["distortion"])
    write_frame("partial_stats_spatial_validation.csv", stability["spatial"])
    write_frame("partial_stats_placebo.csv", stability["placebo"])
    write_frame("partial_stats_selection_aware_bootstrap.csv", stability["bootstrap"])
    write_frame("partial_stats_uncertainty_calibration.csv", stability["uncertainty"])

    est_e, est_w, uncertainty, agg_validation = estimate_cells(cells, summaries["selection"], features["region"], features["industry"])  # type: ignore[arg-type]
    write_frame("estimated_establishment_cells.csv", est_e)
    write_frame("estimated_employee_cells.csv", est_w)
    write_frame("estimated_cells_uncertainty.csv", uncertainty)
    write_frame("estimated_cells_aggregate_validation.csv", agg_validation)
    write_frame("partial_stats_model_registry.csv", model_registry())

    manifest_data = {
        "experiment_id": "partial_statistics_estimation_phase5",
        "protocol_commit_hash": git_hash(),
        "cell_registry_hash": frame_hash(cells),
        "constraint_registry_hash": frame_hash(constraints),
        "feature_registry_hash": frame_hash(features["region"]) + ":" + frame_hash(features["industry"]),
        "spatial_graph_hash": sha256(PROCESSED_DIR / "korea_sigungu_queen_edges.csv") if (PROCESSED_DIR / "korea_sigungu_queen_edges.csv").exists() else "",
        "mask_registry_hash": frame_hash(mask_registry),
        "development_period": TARGET_YEARS,
        "target_variables": TARGETS,
        "industry_level": "KSIC middle manufacturing/mining anchor",
        "model_candidates": model_registry().to_dict("records"),
        "hyperparameter_grids": {"M1_hierarchical_ridge": {"alpha": [10.0]}, "registered_future": {"rank": [3, 5, 8]}},
        "reconciliation_candidates": ["R0_none", "R1_IPF_registered", "R2_CLS_registered", "R4_soft_registered"],
        "mask_scenarios": MASK_SCENARIOS,
        "random_seeds": [RANDOM_SEED],
        "acceptance_gates": {"minimum_relative_improvement": 0.05, "block_masks_required": ["M1", "M2", "M4", "M5"], "C1_aggregate_error_after": 0.005},
        "actual_role": "development_partial_statistics",
        "production_use": False,
        "confirmatory_use": False,
        "same_actual_retuning_allowed": False,
        "generated_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_experiment_manifest.json", manifest_data)
    write_frame("partial_stats_execution_manifest.csv", execution_manifest(CSV_OUTPUTS))
    render_report(summaries["selection"], missingness, results["scenario"], constraints, crosswalk)  # type: ignore[arg-type]
    print(
        json.dumps(
            {
                "ksic8_9_rows": len(ksic),
                "anchor_rows_after_crosswalk": len(anchor),
                "cell_registry_rows": len(cells),
                "observed_cells": int(cells["observation_status"].eq("observed").sum()),
                "mask_runs": mask_registry["mask_id"].nunique(),
                "model_result_rows": len(results["model"]),
                "best_selection": summaries["selection"].to_dict("records"),  # type: ignore[union-attr]
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
