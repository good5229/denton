from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


EPSILON = 1e-12


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path, block_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def nonnegative(values: Iterable[float]) -> np.ndarray:
    return np.maximum(np.asarray(values, dtype=float), 0.0)


def wmape(actual: Iterable[float], prediction: Iterable[float]) -> float:
    y = np.asarray(actual, dtype=float)
    p = nonnegative(prediction)
    denominator = float(np.abs(y).sum())
    if denominator <= EPSILON:
        return 0.0 if np.allclose(y, p) else math.nan
    return float(np.abs(y - p).sum() / denominator)


def rmsle(actual: Iterable[float], prediction: Iterable[float]) -> float:
    y = nonnegative(actual)
    p = nonnegative(prediction)
    return float(np.sqrt(np.mean((np.log1p(y) - np.log1p(p)) ** 2))) if len(y) else math.nan


def poisson_deviance(actual: Iterable[float], prediction: Iterable[float]) -> float:
    y = nonnegative(actual)
    p = np.maximum(nonnegative(prediction), EPSILON)
    terms = np.where(y > 0, y * np.log(np.maximum(y, EPSILON) / p) - (y - p), p)
    return float(2.0 * terms.mean()) if len(y) else math.nan


def prediction_metrics(actual: Iterable[float], prediction: Iterable[float]) -> dict[str, float]:
    y = np.asarray(actual, dtype=float)
    p = nonnegative(prediction)
    errors = np.abs(y - p)
    ape = errors / np.maximum(np.abs(y), 1.0)
    return {
        "wmape": wmape(y, p),
        "pooled_wmape": wmape(y, p),
        "mae": float(errors.mean()) if len(errors) else math.nan,
        "median_absolute_error": float(np.median(errors)) if len(errors) else math.nan,
        "rmsle": rmsle(y, p),
        "median_ape": float(np.median(ape)) if len(ape) else math.nan,
        "p90_ape": float(np.quantile(ape, 0.90)) if len(ape) else math.nan,
        "poisson_deviance": poisson_deviance(y, p),
        "actual_sum": float(y.sum()),
        "prediction_sum": float(p.sum()),
        "n": int(len(y)),
    }


def cell_balanced_wmape(predictions: pd.DataFrame) -> float:
    if predictions.empty:
        return math.nan
    work = predictions.assign(abs_error=lambda d: np.abs(d["actual"] - d["prediction"]))
    by_cell = work.groupby("cell_id", as_index=False).agg(actual=("actual", "first"), abs_error=("abs_error", "mean"))
    return float(by_cell["abs_error"].sum() / max(float(np.abs(by_cell["actual"]).sum()), EPSILON))


def growth_metrics(predictions: pd.DataFrame, history: pd.DataFrame) -> dict[str, float]:
    if predictions.empty:
        return {"yoy_direction_accuracy": math.nan, "growth_mae": math.nan, "growth_wmape": math.nan, "turning_point_accuracy": math.nan}
    prev = history[["region_key", "industry_code", "target_name", "period", "value"]].copy()
    prev["period"] = prev["period"].astype(int)
    pred = predictions.copy()
    pred["period"] = pred["period"].astype(int)
    pred["prev_period"] = pred["period"] - 1
    merged = pred.merge(
        prev.rename(columns={"period": "prev_period", "value": "prev_value"}),
        on=["region_key", "industry_code", "target_name", "prev_period"],
        how="left",
    )
    merged = merged.dropna(subset=["prev_value"])
    if merged.empty:
        return {"yoy_direction_accuracy": math.nan, "growth_mae": math.nan, "growth_wmape": math.nan, "turning_point_accuracy": math.nan}
    actual_growth = merged["actual"] - merged["prev_value"]
    predicted_growth = merged["prediction"] - merged["prev_value"]
    direction = np.sign(actual_growth) == np.sign(predicted_growth)
    turning = (np.sign(actual_growth) != 0) == (np.sign(predicted_growth) != 0)
    return {
        "yoy_direction_accuracy": float(direction.mean()),
        "growth_mae": float(np.abs(actual_growth - predicted_growth).mean()),
        "growth_wmape": wmape(actual_growth, predicted_growth),
        "turning_point_accuracy": float(turning.mean()),
    }


def aggregate_predictions(predictions: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["target_name", "problem_id", "track_id", "model_id", "router_id"]
    for key, group in predictions.groupby(keys, sort=False):
        row = dict(zip(keys, key))
        row.update(prediction_metrics(group["actual"], group["prediction"]))
        row["cell_balanced_wmape"] = cell_balanced_wmape(group)
        row.update(growth_metrics(group, history))
        row["unique_cells"] = int(group["cell_id"].nunique())
        row["prediction_rows"] = int(len(group))
        row["estimated_cell_rate"] = float((group["estimate_status"] != "not_estimable").mean())
        row["not_estimable_rate"] = float((group["estimate_status"] == "not_estimable").mean())
        row["future_anchor_used"] = "N"
        row["target_actual_used_for_selection"] = "N"
        rows.append(row)
    return pd.DataFrame(rows)


def first_eligible_date(period: int, lag_months: int = 12) -> str:
    release_year = period + (lag_months // 12)
    month = lag_months % 12
    if month == 0:
        return f"{release_year}-12-31"
    return f"{release_year}-{month:02d}-28"


def origin_date(target_period: int, origin_kind: str = "O1_annual_pre_release_nowcast") -> str:
    if origin_kind == "O3_one_year_ahead_forecast":
        return f"{target_period - 1}-12-31"
    if origin_kind == "O4_publication_lag_forecast":
        return f"{target_period}-12-31"
    return f"{target_period}-12-31"


def available_at_origin(first_eligible: str, origin: str) -> bool:
    return str(first_eligible) <= str(origin)


def latest_history(train: pd.DataFrame, target_period: int) -> pd.DataFrame:
    prior = train[train["period"].astype(int) < int(target_period)].copy()
    if prior.empty:
        return prior
    prior["period_int"] = prior["period"].astype(int)
    prior = prior.sort_values(["region_key", "industry_code", "target_name", "period_int"])
    return prior.groupby(["region_key", "industry_code", "target_name"], as_index=False).tail(1)


def one_sided_trend(train: pd.DataFrame, valid: pd.DataFrame) -> pd.Series:
    hist = train.copy()
    hist["period_int"] = hist["period"].astype(int)
    hist = hist.sort_values(["region_key", "industry_code", "target_name", "period_int"])
    keyed = hist.groupby(["region_key", "industry_code", "target_name"])
    last = keyed.tail(1).set_index(["region_key", "industry_code", "target_name"])["value"]
    prev = keyed.nth(-2).set_index(["region_key", "industry_code", "target_name"])["value"] if len(hist) else pd.Series(dtype=float)
    values = []
    for row in valid.itertuples():
        key = (row.region_key, row.industry_code, row.target_name)
        base = float(last.get(key, np.nan))
        older = float(prev.get(key, np.nan)) if key in prev.index else np.nan
        if not np.isfinite(base):
            values.append(np.nan)
        elif np.isfinite(older):
            change = np.clip(base - older, -0.5 * max(base, 1.0), 0.5 * max(base, 1.0))
            values.append(max(base + change, 0.0))
        else:
            values.append(base)
    return pd.Series(values, index=valid.index, dtype=float)


def support_class(train: pd.DataFrame, row: pd.Series, parent_available: bool = False) -> str:
    key = (row["region_key"], row["industry_code"], row["target_name"])
    same_cell = train[
        (train["region_key"] == key[0])
        & (train["industry_code"] == key[1])
        & (train["target_name"] == key[2])
    ]
    if not same_cell.empty:
        gap = int(row["period"]) - int(same_cell["period"].astype(int).max())
        return "PS1_recent_temporal" if gap <= 1 else "PS2_delayed_temporal"
    if train[train["region_key"] == row["region_key"]].empty and not train[train["industry_code"] == row["industry_code"]].empty:
        return "PS3_regional_cold_start"
    if train[train["industry_code"] == row["industry_code"]].empty and not train[train["region_key"] == row["region_key"]].empty:
        return "PS4_industry_cold_start"
    if train[train["region_key"] == row["region_key"]].empty and train[train["industry_code"] == row["industry_code"]].empty:
        return "PS5_combination_cold_start"
    if parent_available:
        return "PS6_parent_only"
    return "PS7_proxy_only"


def cold_start_support(train: pd.DataFrame, valid: pd.DataFrame, mode: str) -> pd.Series:
    labels = []
    for row in valid.to_dict("records"):
        if mode == "region":
            labels.append("PS3_regional_cold_start")
        elif mode == "industry":
            labels.append("PS4_industry_cold_start")
        elif mode == "joint":
            labels.append("PS5_combination_cold_start")
        else:
            labels.append(support_class(train, pd.Series(row)))
    return pd.Series(labels, index=valid.index)


@dataclass(frozen=True)
class ForecastRecord:
    forecast_id: str
    created_at: str
    prediction_origin: str
    target_period: str
    target_name: str
    region_key: str
    industry_code: str
    raw_estimate: float
    reconciled_estimate: float
    lower_80: float
    upper_80: float
    lower_95: float
    upper_95: float
    support_class: str
    pipeline_id: str
    input_vintage_hash: str
    code_commit_hash: str

