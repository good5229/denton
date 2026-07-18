from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
EXPERIMENT_ID = "partial_statistics_estimation_phase13_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase13_gva.md"
TARGET_YEARS = [2022, 2023]
ORIGINS = [
    ("O1", "early_origin", 3, 31),
    ("O2", "mid_origin", 6, 30),
    ("O3", "late_origin", 9, 30),
    ("O4", "year_end_origin", 12, 31),
]
MODEL_CONFIGS = {
    "B0_parent_share": {"family": "parent_share", "description": "Parent GVA times latest pre-target child share."},
    "M1_direct_growth": {"family": "direct_growth", "proxy_weight": 0.50, "growth_cap": 0.30},
    "M2_employee_productivity": {"family": "employee_productivity", "employee_weight": 0.20, "growth_cap": 0.25},
    "M3_establishment_productivity": {"family": "establishment_productivity", "business_weight": 0.20, "growth_cap": 0.25},
    "M4_proxy_residual": {"family": "proxy_residual", "proxy_weight": 0.15, "correction_cap": 0.08},
    "M5_fixed_ensemble": {"family": "fixed_ensemble", "weights": {"B0": 0.40, "M1": 0.20, "M2": 0.15, "M3": 0.15, "M4": 0.10}},
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


def add_months(year: int, month: int, add: int) -> tuple[int, int]:
    month0 = month - 1 + add
    return year + month0 // 12, month0 % 12 + 1


def quarter_release_date(prd_de: str, lag_months: int = 2) -> str:
    text = str(prd_de)
    year = int(text[:4])
    quarter = int(text[-2:])
    end_month = quarter * 3
    rel_year, rel_month = add_months(year, end_month, lag_months)
    return f"{rel_year}-{rel_month:02d}-28"


def origin_table() -> pd.DataFrame:
    rows = []
    for target_year in TARGET_YEARS:
        for origin_id, origin_label, month, day in ORIGINS:
            rows.append(
                {
                    "target_year": target_year,
                    "origin_id": origin_id,
                    "origin_label": origin_label,
                    "prediction_origin": f"{target_year}-{month:02d}-{day:02d}",
                    "track": "chronology_incomplete_sensitivity",
                    "minimum_independent_origin_candidate": "Y",
                }
            )
    return pd.DataFrame(rows)


def sector_letter(code: Any) -> str:
    text = str(code or "")
    return text[0] if text else ""


def load_targets() -> pd.DataFrame:
    annual = read_frame("sigungu_annual_rolling_backtest.csv")
    annual = annual[annual["target_year"].astype(str).isin([str(y) for y in TARGET_YEARS])].copy()
    annual["target_year"] = annual["target_year"].astype(int)
    for col in [
        "predicted_annual_gva",
        "actual_annual_gva",
        "share_base_sigungu_gva",
        "share_base_parent_gva",
        "parent_predicted_annual_gva",
    ]:
        annual[col] = numeric(annual[col])
    annual["sector_letter"] = annual["sector_code"].map(sector_letter)
    annual["cell_id"] = (
        annual["target_year"].astype(str)
        + "|"
        + annual["source_region"].astype(str)
        + "|"
        + annual["sigungu_code"].astype(str)
        + "|"
        + annual["sector_code"].astype(str)
    )
    return annual


def production_ledger() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    specs = [
        ("mining_manufacturing_production_index.csv", "mining_manufacturing_production_index"),
        ("service_production_index.csv", "service_production_index"),
    ]
    for filename, source_id in specs:
        df = read_frame(filename)
        if df.empty:
            continue
        df = df[df["prd_se"].eq("Q")].copy()
        df["observation_year"] = df["prd_de"].str[:4].astype(int)
        df = df[df["observation_year"].between(2021, 2023)].copy()
        df["release_date"] = df["prd_de"].map(quarter_release_date)
        for row in df.to_dict("records"):
            rows.append(
                {
                    "source_id": source_id,
                    "source_file": filename,
                    "observation_period": f"{str(row['prd_de'])[:4]}Q{int(str(row['prd_de'])[-2:])}",
                    "observation_year": row["observation_year"],
                    "release_date": row["release_date"],
                    "first_eligible_origin": row["release_date"],
                    "vintage_id": f"{source_id}:assumed_lag_current_snapshot",
                    "revision_date": "",
                    "availability_confidence": "C_assumed_release_lag_current_snapshot",
                    "region_name": row.get("c1_nm", ""),
                    "industry_code": row.get("c2_id", ""),
                    "industry_name": row.get("c2_nm", ""),
                    "metric": row.get("item_nm", ""),
                    "value": row.get("value", ""),
                    "strict_track_eligible": "N",
                }
            )
    return pd.DataFrame(rows)


def annual_feature_ledger() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    specs = [
        ("kosis_business_feature_table.csv", "business_establishment_count"),
        ("kosis_employment_feature_table.csv", "employee_count"),
    ]
    for filename, source_id in specs:
        df = read_frame(filename)
        if df.empty:
            continue
        df = df[df["area_level"].isin(["sido", "sigungu"]) & df["industry_level"].eq("section")].copy()
        for row in df.to_dict("records"):
            first_year = pd.to_numeric(pd.Series([row.get("first_eligible_target_year", "")]), errors="coerce").iloc[0]
            if not np.isfinite(first_year):
                continue
            release = f"{int(first_year)}-01-01"
            rows.append(
                {
                    "source_id": source_id,
                    "source_file": filename,
                    "observation_period": str(row.get("year", "")),
                    "observation_year": row.get("year", ""),
                    "release_date": release,
                    "first_eligible_origin": release,
                    "vintage_id": f"{source_id}:lag_assumption_current_snapshot",
                    "revision_date": row.get("revision_date", ""),
                    "availability_confidence": "C_assumed_annual_lag_current_snapshot",
                    "region_code": row.get("area_code", ""),
                    "region_name": row.get("area_name", ""),
                    "industry_code": row.get("industry_code", ""),
                    "industry_name": row.get("industry_name", ""),
                    "metric": row.get("metric", ""),
                    "value": row.get("value", ""),
                    "strict_track_eligible": "N",
                }
            )
    return pd.DataFrame(rows)


def observation_release_ledger() -> pd.DataFrame:
    return pd.concat([production_ledger(), annual_feature_ledger()], ignore_index=True, sort=False)


def proxy_features_for_origin(ledger: pd.DataFrame, target: pd.DataFrame, origin: dict[str, Any]) -> pd.DataFrame:
    eligible = ledger[ledger["first_eligible_origin"].astype(str).le(str(origin["prediction_origin"]))].copy()
    obs_rows = []
    prod = eligible[eligible["source_id"].isin(["mining_manufacturing_production_index", "service_production_index"])].copy()
    if not prod.empty:
        prod["observation_year"] = pd.to_numeric(prod["observation_year"], errors="coerce")
        prod["value_num"] = numeric(prod["value"])
        prod["sector_letter"] = prod["industry_code"].map(sector_letter)
        prod = prod[prod["observation_year"].eq(int(origin["target_year"]))].copy()
    proxy_lookup = proxy_growth_lookup(prod)
    annual_feat = eligible[eligible["source_id"].isin(["business_establishment_count", "employee_count"])].copy()
    if not annual_feat.empty:
        annual_feat["observation_year"] = pd.to_numeric(annual_feat["observation_year"], errors="coerce")
        annual_feat["value_num"] = numeric(annual_feat["value"])
        annual_feat["sector_letter"] = annual_feat["industry_code"].map(sector_letter)
    annual_lookup = annual_growth_lookup(annual_feat, int(origin["target_year"]))
    for row in target.to_dict("records"):
        region = row["source_region"]
        sector = row["sector_letter"]
        proxy_count, proxy_mean, latest_obs = proxy_lookup.get(
            (region, sector),
            proxy_lookup.get(("전국", sector), (0, 100.0, "")),
        )
        proxy_growth = np.clip(proxy_mean / 100.0 - 1.0, -0.35, 0.35)
        emp_growth = annual_lookup.get(("employee_count", region, sector), annual_lookup.get(("employee_count", region, "0"), 0.0))
        biz_growth = annual_lookup.get(("business_establishment_count", region, sector), annual_lookup.get(("business_establishment_count", region, "0"), 0.0))
        obs_rows.append(
            {
                "target_year": row["target_year"],
                "origin_id": origin["origin_id"],
                "prediction_origin": origin["prediction_origin"],
                "cell_id": row["cell_id"],
                "source_region": region,
                "sigungu_code": row["sigungu_code"],
                "sigungu_name": row["sigungu_name"],
                "sector_code": row["sector_code"],
                "sector_name": row["sector_name"],
                "actual": row["actual_annual_gva"],
                "parent_share_prediction": row["predicted_annual_gva"],
                "prev_gva": row["share_base_sigungu_gva"],
                "parent_prev_gva": row["share_base_parent_gva"],
                "parent_prediction": row["parent_predicted_annual_gva"],
                "parent_growth": safe_growth(row["parent_predicted_annual_gva"], row["share_base_parent_gva"]),
                "proxy_observation_count": proxy_count,
                "latest_proxy_observation_period": latest_obs,
                "proxy_index_mean": proxy_mean,
                "proxy_growth": proxy_growth,
                "employee_growth": emp_growth,
                "establishment_growth": biz_growth,
                "eligible_source_count": int(eligible["source_id"].nunique()),
                "eligible_observation_count": int(len(eligible)),
            }
        )
    return pd.DataFrame(obs_rows)


def proxy_growth_lookup(prod: pd.DataFrame) -> dict[tuple[str, str], tuple[int, float, str]]:
    if prod.empty:
        return {}
    lookup: dict[tuple[str, str], tuple[int, float, str]] = {}
    for key, group in prod.groupby(["region_name", "sector_letter"], sort=False):
        lookup[(str(key[0]), str(key[1]))] = (
            int(len(group)),
            float(group["value_num"].mean()),
            str(group["observation_period"].max()),
        )
    return lookup


def annual_growth_lookup(features: pd.DataFrame, target_year: int) -> dict[tuple[str, str, str], float]:
    if features.empty:
        return {}
    work = features[features["observation_year"].le(target_year - 1)].copy()
    if work.empty:
        return {}
    work = work.sort_values(["source_id", "region_name", "sector_letter", "observation_year"])
    lookup: dict[tuple[str, str, str], float] = {}
    for key, group in work.groupby(["source_id", "region_name", "sector_letter"], sort=False):
        if len(group) < 2:
            continue
        latest = float(group.iloc[-1]["value_num"])
        prev = float(group.iloc[-2]["value_num"])
        lookup[(str(key[0]), str(key[1]), str(key[2]))] = float(np.clip((latest / max(prev, 1.0)) - 1.0, -0.25, 0.25))
    all_industry = work[work["industry_code"].eq("0")].sort_values(["source_id", "region_name", "observation_year"])
    for key, group in all_industry.groupby(["source_id", "region_name"], sort=False):
        if len(group) < 2:
            continue
        latest = float(group.iloc[-1]["value_num"])
        prev = float(group.iloc[-2]["value_num"])
        lookup[(str(key[0]), str(key[1]), "0")] = float(np.clip((latest / max(prev, 1.0)) - 1.0, -0.25, 0.25))
    return lookup


def annual_growth(features: pd.DataFrame, source_id: str, region: str, sector: str, target_year: int) -> float:
    if features.empty:
        return 0.0
    df = features[(features["source_id"].eq(source_id)) & (features["region_name"].eq(region)) & (features["sector_letter"].eq(sector))].copy()
    if df.empty:
        df = features[(features["source_id"].eq(source_id)) & (features["region_name"].eq(region)) & (features["industry_code"].eq("0"))].copy()
    if df.empty:
        return 0.0
    df = df[df["observation_year"].le(target_year - 1)].sort_values("observation_year")
    if len(df) < 2:
        return 0.0
    latest = float(df.iloc[-1]["value_num"])
    prev = float(df.iloc[-2]["value_num"])
    return float(np.clip((latest / max(prev, 1.0)) - 1.0, -0.25, 0.25))


def safe_growth(current: Any, previous: Any) -> float:
    cur = float(current) if pd.notna(current) and str(current) != "" else math.nan
    prev = float(previous) if pd.notna(previous) and str(previous) != "" else math.nan
    if not np.isfinite(cur) or not np.isfinite(prev) or prev <= 0:
        return 0.0
    return float(np.clip(cur / prev - 1.0, -0.50, 0.50))


def build_asof_matrix(target: pd.DataFrame, ledger: pd.DataFrame, origins: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    matrices = []
    registry_rows = []
    eligibility_rows = []
    for origin in origins.to_dict("records"):
        target_rows = target[target["target_year"].eq(int(origin["target_year"]))].copy()
        matrix = proxy_features_for_origin(ledger, target_rows, origin)
        matrices.append(matrix)
        eligible = ledger[ledger["first_eligible_origin"].astype(str).le(str(origin["prediction_origin"]))].copy()
        for srow in eligible.to_dict("records"):
            eligibility_rows.append(
                {
                    "target_year": origin["target_year"],
                    "origin_id": origin["origin_id"],
                    "prediction_origin": origin["prediction_origin"],
                    "source_id": srow["source_id"],
                    "observation_period": srow["observation_period"],
                    "release_date": srow["release_date"],
                    "eligible": "Y",
                    "strict_track_eligible": srow.get("strict_track_eligible", "N"),
                    "availability_confidence": srow.get("availability_confidence", ""),
                }
            )
        content_hash = core.stable_hash(
            matrix[
                [
                    "cell_id",
                    "proxy_observation_count",
                    "latest_proxy_observation_period",
                    "proxy_index_mean",
                    "employee_growth",
                    "establishment_growth",
                ]
            ].round(10).to_dict("records")
        )
        registry_rows.append(
            {
                "target_year": origin["target_year"],
                "origin_id": origin["origin_id"],
                "prediction_origin": origin["prediction_origin"],
                "eligible_source_count": int(eligible["source_id"].nunique()),
                "eligible_observation_count": int(len(eligible)),
                "latest_available_observation_period": eligible["observation_period"].max() if len(eligible) else "",
                "feature_count": 8,
                "nonmissing_feature_count": int(matrix[["proxy_growth", "employee_growth", "establishment_growth"]].notna().sum().sum()),
                "feature_content_hash": content_hash,
                "strict_track_status": "blocked_current_snapshot_release_assumptions",
            }
        )
    return pd.concat(matrices, ignore_index=True), pd.DataFrame(registry_rows), pd.DataFrame(eligibility_rows)


def predict_models(matrix: pd.DataFrame) -> dict[str, pd.DataFrame]:
    work = matrix.copy()
    parent_growth = work["parent_growth"].fillna(0.0).astype(float)
    proxy_growth = work["proxy_growth"].fillna(0.0).astype(float)
    emp_growth = work["employee_growth"].fillna(0.0).astype(float)
    biz_growth = work["establishment_growth"].fillna(0.0).astype(float)
    baseline = work["parent_share_prediction"].astype(float).clip(lower=0)
    prev = work["prev_gva"].astype(float).clip(lower=0)
    preds = {
        "B0_parent_share": baseline,
        "M1_direct_growth": (prev * (1.0 + np.clip(parent_growth + 0.50 * proxy_growth, -0.30, 0.30))).clip(lower=0),
        "M2_employee_productivity": (baseline * (1.0 + np.clip(0.20 * emp_growth, -0.25, 0.25))).clip(lower=0),
        "M3_establishment_productivity": (baseline * (1.0 + np.clip(0.20 * biz_growth, -0.25, 0.25))).clip(lower=0),
        "M4_proxy_residual": (baseline * (1.0 + np.clip(0.15 * proxy_growth, -0.08, 0.08))).clip(lower=0),
    }
    preds["M5_fixed_ensemble"] = (
        0.40 * preds["B0_parent_share"]
        + 0.20 * preds["M1_direct_growth"]
        + 0.15 * preds["M2_employee_productivity"]
        + 0.15 * preds["M3_establishment_productivity"]
        + 0.10 * preds["M4_proxy_residual"]
    ).clip(lower=0)
    out: dict[str, pd.DataFrame] = {}
    base_cols = [
        "target_year",
        "origin_id",
        "prediction_origin",
        "cell_id",
        "source_region",
        "sigungu_code",
        "sigungu_name",
        "sector_code",
        "sector_name",
        "actual",
        "proxy_observation_count",
        "latest_proxy_observation_period",
        "proxy_growth",
        "employee_growth",
        "establishment_growth",
    ]
    for model_id, prediction in preds.items():
        frame = work[base_cols].copy()
        frame["model_id"] = model_id
        frame["model_family"] = MODEL_CONFIGS[model_id]["family"]
        frame["prediction"] = np.asarray(prediction, dtype=float)
        frame["estimate_status"] = "estimated"
        frame["actual_used_for_selection"] = "N"
        frame["implementation_status"] = "independently_executed"
        out[model_id] = frame
    return out


def aggregate_results(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in predictions.groupby(["target_year", "origin_id", "prediction_origin", "model_id", "model_family"], sort=False):
        metrics = core.prediction_metrics(group["actual"], group["prediction"])
        row = dict(zip(["target_year", "origin_id", "prediction_origin", "model_id", "model_family"], keys))
        row.update(metrics)
        row["evaluation_status"] = "outer_evaluation_sensitivity"
        rows.append(row)
    return pd.DataFrame(rows)


def origin_identity(predictions: pd.DataFrame, asof: pd.DataFrame, registry: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for keys, group in predictions.groupby(["target_year", "origin_id", "prediction_origin", "model_id"], sort=False):
        target_year, origin_id, prediction_origin, model_id = keys
        feature_row = registry[(registry["target_year"].astype(int).eq(int(target_year))) & (registry["origin_id"].eq(origin_id))].iloc[0]
        eligible_source_hash = core.stable_hash(
            sorted(
                asof[
                    (asof["target_year"].astype(int).eq(int(target_year)))
                    & (asof["origin_id"].eq(origin_id))
                    & (asof["eligible"].eq("Y"))
                ]["source_id"].unique()
            )
        )
        prediction_hash = core.stable_hash(group[["cell_id", "prediction"]].round(8).to_dict("records"))
        rows.append(
            {
                "target_year": target_year,
                "origin_id": origin_id,
                "prediction_origin": prediction_origin,
                "model_id": model_id,
                "eligible_source_hash": eligible_source_hash,
                "feature_content_hash": feature_row["feature_content_hash"],
                "model_config_hash": core.stable_hash(MODEL_CONFIGS[model_id]),
                "prediction_hash": prediction_hash,
            }
        )
    audit = pd.DataFrame(rows)
    audit["collapse_key"] = audit[["eligible_source_hash", "feature_content_hash", "model_config_hash", "prediction_hash"]].agg("|".join, axis=1)
    audit["collapse_group_id"] = audit.groupby(["target_year", "model_id", "collapse_key"]).ngroup().map(lambda x: f"CG{x:04d}")
    audit["independent_origin"] = ~audit.duplicated(["target_year", "model_id", "collapse_key"])
    audit["origin_status"] = np.where(audit["independent_origin"], "independent_origin", "collapsed_origin")
    collapse = (
        audit.groupby(["target_year", "model_id", "collapse_group_id", "origin_status"], as_index=False)
        .agg(origin_count=("origin_id", "nunique"), origins=("origin_id", lambda s: ",".join(s)))
    )
    growth = (
        registry.sort_values(["target_year", "prediction_origin"])
        .assign(
            eligible_observation_delta=lambda d: d.groupby("target_year")["eligible_observation_count"].diff().fillna(0).astype(int),
            feature_hash_changed=lambda d: d.groupby("target_year")["feature_content_hash"].transform(lambda s: s.ne(s.shift()).fillna(True)),
        )
    )
    return audit.drop(columns=["collapse_key"]), collapse, growth


def revision_results(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sorted_pred = predictions.sort_values(["target_year", "model_id", "cell_id", "prediction_origin"])
    for _, group in sorted_pred.groupby(["target_year", "model_id", "cell_id"], sort=False):
        prev_prediction = None
        prev_origin = None
        actual = float(group.iloc[0]["actual"])
        for row in group.to_dict("records"):
            revision = "" if prev_prediction is None else float(row["prediction"] - prev_prediction)
            direction_match = ""
            if prev_prediction is not None:
                direction_match = str(np.sign(float(row["prediction"] - prev_prediction)) == np.sign(actual - prev_prediction))
            rows.append(
                {
                    "target_year": row["target_year"],
                    "model_id": row["model_id"],
                    "cell_id": row["cell_id"],
                    "origin_id": row["origin_id"],
                    "previous_origin_id": prev_origin or "",
                    "prediction": row["prediction"],
                    "revision_from_previous_origin": revision,
                    "absolute_revision": "" if revision == "" else abs(float(revision)),
                    "relative_revision": "" if revision == "" else abs(float(revision)) / max(abs(prev_prediction), 1.0),
                    "actual_direction_match": direction_match,
                }
            )
            prev_prediction = float(row["prediction"])
            prev_origin = row["origin_id"]
    return pd.DataFrame(rows)


def split_model_outputs(model_predictions: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "partial_stats_phase13_gva_parent_share_results.csv": aggregate_results(model_predictions["B0_parent_share"]),
        "partial_stats_phase13_gva_direct_growth_results.csv": aggregate_results(model_predictions["M1_direct_growth"]),
        "partial_stats_phase13_gva_employee_productivity_results.csv": aggregate_results(model_predictions["M2_employee_productivity"]),
        "partial_stats_phase13_gva_establishment_productivity_results.csv": aggregate_results(model_predictions["M3_establishment_productivity"]),
        "partial_stats_phase13_gva_proxy_residual_results.csv": aggregate_results(model_predictions["M4_proxy_residual"]),
        "partial_stats_phase13_gva_ensemble_results.csv": aggregate_results(model_predictions["M5_fixed_ensemble"]),
    }


def monthly_outputs(ledger: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    registry = pd.DataFrame(
        [
            {"source_id": "kepco_sigungu_electricity_long.csv", "frequency": "monthly", "historical_2022_2023_available": "N", "primary_monthly_eligible": "N", "reason": "local file starts after historical evaluation years"},
            {"source_id": "mining_manufacturing_production_index.csv", "frequency": "quarterly", "historical_2022_2023_available": "Y", "primary_monthly_eligible": "N", "reason": "quarterly source cannot justify monthly primary estimate alone"},
            {"source_id": "service_production_index.csv", "frequency": "quarterly", "historical_2022_2023_available": "Y", "primary_monthly_eligible": "N", "reason": "quarterly source cannot justify monthly primary estimate alone"},
        ]
    )
    activity = (
        ledger[ledger["source_id"].isin(["mining_manufacturing_production_index", "service_production_index"])]
        .groupby(["source_id", "observation_period"], as_index=False)
        .agg(activity_index=("value", lambda s: float(pd.to_numeric(s, errors="coerce").mean())))
    )
    temporal = pd.DataFrame(
        [
            {"method": "primary_monthly_activity_nowcast", "status": "blocked", "reason": "no eligible region-industry monthly indicator for 2022-2023 origins"},
            {"method": "quarterly_equal_split_placeholder", "status": "placeholder_only", "reason": "may be used for display scenario but not as monthly nowcast"},
        ]
    )
    placeholder = pd.DataFrame(
        [
            {"placeholder_id": "P13_MONTHLY_PLACEHOLDER", "allowed": "Y_display_only", "forbidden_claim": "monthly activity-based nowcast", "description": "Quarterly values may be divided by three only as a placeholder scenario."}
        ]
    )
    return registry, activity, temporal, placeholder


def interval_outputs(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    cal_rows = []
    for keys, group in predictions.groupby(["target_year", "origin_id", "model_id"], sort=False):
        target_year, origin_id, model_id = keys
        residual = np.abs(group["actual"].astype(float) - group["prediction"].astype(float))
        q80 = float(np.quantile(residual, 0.80))
        q95 = float(np.quantile(residual, 0.95))
        lower80 = np.maximum(group["prediction"].astype(float) - q80, 0)
        upper80 = group["prediction"].astype(float) + q80
        lower95 = np.maximum(group["prediction"].astype(float) - q95, 0)
        upper95 = group["prediction"].astype(float) + q95
        coverage80 = ((group["actual"].astype(float) >= lower80) & (group["actual"].astype(float) <= upper80)).mean()
        coverage95 = ((group["actual"].astype(float) >= lower95) & (group["actual"].astype(float) <= upper95)).mean()
        cal_rows.append(
            {
                "target_year": target_year,
                "origin_id": origin_id,
                "model_id": model_id,
                "coverage_80": float(coverage80),
                "coverage_95": float(coverage95),
                "mean_width_80": float((upper80 - lower80).mean()),
                "mean_width_95": float((upper95 - lower95).mean()),
                "calibration_status": "posthoc_diagnostic_not_deployable",
            }
        )
        sample = group.head(200).copy()
        sample["lower_80"] = np.maximum(sample["prediction"].astype(float) - q80, 0)
        sample["upper_80"] = sample["prediction"].astype(float) + q80
        sample["lower_95"] = np.maximum(sample["prediction"].astype(float) - q95, 0)
        sample["upper_95"] = sample["prediction"].astype(float) + q95
        rows.append(sample[["target_year", "origin_id", "model_id", "cell_id", "prediction", "actual", "lower_80", "upper_80", "lower_95", "upper_95"]])
    interval = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    calibration = pd.DataFrame(cal_rows)
    group_results = (
        calibration.groupby(["origin_id", "model_id"], as_index=False)
        .agg(coverage_80=("coverage_80", "mean"), coverage_95=("coverage_95", "mean"), mean_width_95=("mean_width_95", "mean"))
    )
    return interval, calibration, group_results


def current_estimates() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = read_frame("partial_stats_phase12_gva_annual_estimates_2025.csv")
    quarterly = read_frame("partial_stats_phase12_gva_quarterly_estimates_2025.csv")
    monthly = read_frame("partial_stats_phase12_gva_monthly_estimates_2025.csv")
    nowcast = read_frame("partial_stats_phase12_gva_annual_nowcast_2026.csv")
    for frame, role in [(annual, "phase13_carry_forward_reconciled_annual"), (quarterly, "phase13_carry_forward_quarterly"), (monthly, "placeholder_only_not_primary"), (nowcast, "phase13_baseline_scenario")]:
        if not frame.empty:
            frame["phase13_role"] = role
            frame["actual_used"] = "N"
    return annual, quarterly, monthly, nowcast


def write_report(ctx: dict[str, pd.DataFrame], final: dict[str, Any]) -> None:
    lines = [
        "# Partial Statistics Estimation Phase 13-GVA",
        "",
        "## 1. 실행 요약",
        "",
        "Phase 13 converts Phase 12's repeated origin labels into an explicit origin-identity audit and a chronology-incomplete sensitivity experiment with genuinely changing as-of feature hashes.",
        "",
        markdown_table(pd.DataFrame([final])),
        "",
        "## 2. Phase 12 판정 반영",
        "",
        "Phase 12 restored GVA as the primary target, but its prediction origins collapsed because the same parent-share prediction was repeated across origin labels. This report treats that as a limitation, not as evidence of true multi-origin performance.",
        "",
        "## 3. Observation Release Ledger",
        "",
        markdown_table(ctx["ledger"]),
        "",
        "## 4. Origin Information Growth",
        "",
        markdown_table(ctx["growth"]),
        "",
        "## 5. Origin Collapse Audit",
        "",
        markdown_table(ctx["identity"]),
        "",
        "## 6. Model Results",
        "",
        markdown_table(ctx["accuracy"]),
        "",
        "## 7. Forecast Revision",
        "",
        markdown_table(ctx["revision"]),
        "",
        "## 8. Monthly Activity Decision",
        "",
        markdown_table(ctx["monthly_registry"]),
        "",
        "## 9. Interval Diagnostics",
        "",
        markdown_table(ctx["interval_calibration"]),
        "",
        "## 10. Current 2025 and 2026 Estimates",
        "",
        "2025 estimates are carried forward from the Phase 12 reconciled quarterly cube. 2026 remains a baseline scenario, not a current-indicator nowcast.",
        "",
        "## 11. 최종 결론",
        "",
        "1. 실제 독립 Origin 수: " + str(final["independent_origin_count"]),
        "2. Collapsed Origin 수: " + str(final["collapsed_origin_count"]),
        "3. Origin별 Source 증가량: see `partial_stats_phase13_gva_origin_information_growth.csv`.",
        "4. Origin별 Feature Hash 차이: " + str(final["feature_hash_unique_count"]) + " unique hashes.",
        "5. Origin별 Prediction Hash 차이: " + str(final["prediction_hash_unique_count"]) + " unique hashes.",
        "6. 2022 Early/Mid/Late 성능: recorded in origin accuracy.",
        "7. 2023 Early/Mid/Late 성능: recorded in origin accuracy.",
        "8. Early-to-late 개선: diagnostic only; actual was not used for model selection.",
        "9. Forecast Revision 안정성: recorded in revision results.",
        "10. Parent-share 성능: baseline retained.",
        "11. Direct GVA 성능: independently executed as direct growth sensitivity model.",
        "12. Employee Productivity 성능: independently executed with lagged employee features.",
        "13. Establishment Productivity 성능: independently executed with lagged establishment features.",
        "14. Proxy Residual 성능: independently executed with bounded proxy correction.",
        "15. 월별 Activity Source: no eligible 2022-2023 region-industry monthly source.",
        "16. 월별 Placeholder 여부: monthly output remains placeholder-only.",
        "17. Origin별 Interval Coverage: posthoc diagnostic only, not deployable calibration.",
        "18. 2025 GVA 수정 결과: carried from Phase 12 reconciled quarterly cube.",
        "19. 2026 Nowcast 수정 결과: baseline scenario only.",
        "20. 아직 주장할 수 없는 내용: strict official vintage performance, production/official statistics use, 2025 actual performance, and activity-based monthly nowcast.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    topic = ROOT / "reports" / "topics" / "ml.md"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# Reconciled ML Experiments\n\n| Report | Purpose |\n| --- | --- |\n"
    row = "| [partial_statistics_estimation_phase13_gva.md](../partial_statistics_estimation_phase13_gva.md) | Phase 13 true-origin audit, sensitivity multi-origin GVA models, monthly blocker, and interval diagnostics |\n"
    if "partial_statistics_estimation_phase13_gva.md" not in text:
        text = text.replace("| --- | --- |\n", "| --- | --- |\n" + row)
        topic.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase13_gva_final_status.json"
    if final_path.exists() and not args.force:
        print(final_path)
        return 0

    targets = load_targets()
    origins = origin_table()
    ledger = observation_release_ledger()
    matrix, registry, eligibility = build_asof_matrix(targets, ledger, origins)
    model_predictions = predict_models(matrix)
    predictions = pd.concat(model_predictions.values(), ignore_index=True)
    identity, collapse, growth = origin_identity(predictions, eligibility, registry)
    revision = revision_results(predictions)
    accuracy = aggregate_results(predictions)
    model_outputs = split_model_outputs(model_predictions)
    monthly_registry, activity, temporal, placeholder = monthly_outputs(ledger)
    intervals, interval_calibration, interval_group = interval_outputs(predictions)
    annual_2025, quarterly_2025, monthly_2025, nowcast_2026 = current_estimates()

    final = {
        "status": "strict_vintage_blocked_sensitivity_completed",
        "target": "GVA",
        "target_years": TARGET_YEARS,
        "origin_count": int(len(origins)),
        "model_count": int(len(MODEL_CONFIGS)),
        "independent_origin_count": int(registry["feature_content_hash"].nunique()),
        "collapsed_origin_count": int(len(registry) - registry["feature_content_hash"].nunique()),
        "independent_model_origin_count": int(identity[identity["independent_origin"]].shape[0]),
        "collapsed_model_origin_count": int(identity[~identity["independent_origin"]].shape[0]),
        "feature_hash_unique_count": int(registry["feature_content_hash"].nunique()),
        "prediction_hash_unique_count": int(identity["prediction_hash"].nunique()),
        "monthly_primary_status": "blocked_no_eligible_monthly_source",
        "strict_vintage_status": "blocked_current_snapshot_release_assumptions",
        "sensitivity_track": "completed",
        "actual_used_for_selection": False,
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    input_hash = core.stable_hash(
        {
            "targets": targets[["target_year", "cell_id", "predicted_annual_gva", "actual_annual_gva"]].to_dict("records"),
            "origins": origins.to_dict("records"),
            "ledger_rows": len(ledger),
            "model_configs": MODEL_CONFIGS,
        }
    )
    lineage = {
        "input_hash": input_hash,
        "code_commit_hash": git_hash(),
        "run_id": EXPERIMENT_ID,
        "created_at": GENERATED_AT,
    }
    artifacts: dict[str, pd.DataFrame] = {
        "partial_stats_phase13_gva_origin_identity_audit.csv": identity,
        "partial_stats_phase13_gva_origin_collapse_registry.csv": collapse,
        "partial_stats_phase13_gva_origin_information_growth.csv": growth,
        "partial_stats_phase13_gva_observation_release_ledger.csv": ledger,
        "partial_stats_phase13_gva_origin_feature_eligibility.csv": eligibility,
        "partial_stats_phase13_gva_vintage_availability.csv": ledger[["source_id", "vintage_id", "availability_confidence", "strict_track_eligible"]].drop_duplicates(),
        "partial_stats_phase13_gva_asof_dataset_registry.csv": registry,
        "partial_stats_phase13_gva_asof_hash_audit.csv": registry[["target_year", "origin_id", "feature_content_hash", "strict_track_status"]],
        "partial_stats_phase13_gva_2022_origin_results.csv": predictions[predictions["target_year"].astype(int).eq(2022)],
        "partial_stats_phase13_gva_2023_origin_results.csv": predictions[predictions["target_year"].astype(int).eq(2023)],
        "partial_stats_phase13_gva_origin_accuracy.csv": accuracy,
        "partial_stats_phase13_gva_revision_results.csv": revision,
        "partial_stats_phase13_gva_monthly_source_registry.csv": monthly_registry,
        "partial_stats_phase13_gva_activity_index.csv": activity,
        "partial_stats_phase13_gva_temporal_disaggregation.csv": temporal,
        "partial_stats_phase13_gva_monthly_placeholder_registry.csv": placeholder,
        "partial_stats_phase13_gva_origin_intervals.csv": intervals,
        "partial_stats_phase13_gva_interval_calibration.csv": interval_calibration,
        "partial_stats_phase13_gva_interval_group_results.csv": interval_group,
        "partial_stats_phase13_gva_annual_estimates_2025.csv": annual_2025,
        "partial_stats_phase13_gva_quarterly_estimates_2025.csv": quarterly_2025,
        "partial_stats_phase13_gva_monthly_estimates_2025.csv": monthly_2025,
        "partial_stats_phase13_gva_nowcast_2026.csv": nowcast_2026,
    }
    artifacts.update(model_outputs)
    for name, frame in artifacts.items():
        out = frame.copy()
        for key, value in lineage.items():
            out[key] = value
        write_frame(name, out)
    try:
        matrix.to_parquet(PROCESSED_DIR / "partial_stats_phase13_gva_asof_feature_matrix.parquet", index=False)
    except Exception:
        write_frame("partial_stats_phase13_gva_asof_feature_matrix_fallback.csv", matrix)
    write_json(PROCESSED_DIR / "partial_stats_phase13_gva_experiment_manifest.json", {"experiment_id": EXPERIMENT_ID, "input_hash": input_hash, "model_configs": MODEL_CONFIGS, "package_versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "platform": platform.platform()}, "generated_at": GENERATED_AT})
    write_json(final_path, final)
    write_report(
        {
            "ledger": ledger,
            "growth": growth,
            "identity": identity,
            "accuracy": accuracy,
            "revision": revision,
            "monthly_registry": monthly_registry,
            "interval_calibration": interval_calibration,
        },
        final,
    )
    print(
        json.dumps(
            {
                "status": final["status"],
                "report": str(REPORT.relative_to(ROOT)),
                "independent_origin_count": final["independent_origin_count"],
                "independent_model_origin_count": final["independent_model_origin_count"],
                "collapsed_origin_count": final["collapsed_origin_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
