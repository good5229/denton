from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.decomposition import TruncatedSVD
from sklearn.linear_model import Ridge


EPSILON = 1e-12


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def nonnegative(values: Iterable[float]) -> np.ndarray:
    return np.maximum(np.asarray(values, dtype=float), 0.0)


def wmape(actual: Iterable[float], prediction: Iterable[float]) -> float:
    y = np.asarray(actual, dtype=float)
    p = nonnegative(prediction)
    denominator = float(np.abs(y).sum())
    if denominator <= EPSILON:
        return 0.0 if np.allclose(y, p) else math.nan
    return float(np.abs(y - p).sum() / denominator)


def mae(actual: Iterable[float], prediction: Iterable[float]) -> float:
    y = np.asarray(actual, dtype=float)
    p = nonnegative(prediction)
    return float(np.abs(y - p).mean()) if len(y) else math.nan


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
    zero = np.isclose(y, 0.0)
    small_cutoff = float(np.quantile(y, 0.25)) if len(y) else 0.0
    small = y <= small_cutoff
    return {
        "wmape": wmape(y, p),
        "mae": mae(y, p),
        "median_absolute_error": float(np.median(errors)) if len(y) else math.nan,
        "rmsle": rmsle(y, p),
        "poisson_deviance": poisson_deviance(y, p),
        "median_ape": float(np.median(ape)) if len(y) else math.nan,
        "p90_ape": float(np.quantile(ape, 0.90)) if len(y) else math.nan,
        "exact_zero_error": float(errors[zero].mean()) if zero.any() else 0.0,
        "small_cell_absolute_error": float(errors[small].mean()) if small.any() else math.nan,
        "actual_sum": float(y.sum()),
        "prediction_sum": float(p.sum()),
        "n": int(len(y)),
    }


def aggregate_prediction_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    required = {"target_name", "model_id", "mask_id", "mask_scenario", "cell_id", "actual", "prediction"}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"prediction rows missing required columns: {sorted(missing)}")
    run_rows: list[dict[str, Any]] = []
    keys = ["target_name", "model_id", "mask_id", "mask_scenario"]
    for key, group in predictions.groupby(keys, sort=False):
        row = dict(zip(keys, key))
        row.update(prediction_metrics(group["actual"], group["prediction"]))
        run_rows.append(row)
    runs = pd.DataFrame(run_rows)
    output: list[dict[str, Any]] = []
    for (target, model), group in predictions.groupby(["target_name", "model_id"], sort=False):
        run_subset = runs[(runs["target_name"] == target) & (runs["model_id"] == model)].copy()
        cell = group.groupby("cell_id", as_index=False).agg(
            actual=("actual", "first"),
            mean_absolute_error=("prediction", lambda s: 0.0),
        )
        absolute = group.assign(abs_error=np.abs(group["actual"] - group["prediction"]))
        cell_error = absolute.groupby("cell_id", as_index=False).agg(actual=("actual", "first"), abs_error=("abs_error", "mean"))
        cell_balanced = float(cell_error["abs_error"].sum() / max(np.abs(cell_error["actual"]).sum(), EPSILON))
        weighted_repeat = float(
            np.nansum(run_subset["wmape"] * run_subset["actual_sum"])
            / max(float(run_subset["actual_sum"].sum()), EPSILON)
        )
        output.append(
            {
                "target_name": target,
                "model_id": model,
                "cell_balanced_wmape": cell_balanced,
                "pooled_wmape": wmape(group["actual"], group["prediction"]),
                "scenario_macro_wmape": float(run_subset["wmape"].mean()),
                "scenario_weighted_wmape": weighted_repeat,
                "median_repeat_wmape": float(run_subset["wmape"].median()),
                "p90_repeat_wmape": float(run_subset["wmape"].quantile(0.90)),
                "mae": mae(group["actual"], group["prediction"]),
                "rmsle": rmsle(group["actual"], group["prediction"]),
                "unique_cells": int(group["cell_id"].nunique()),
                "prediction_rows": int(len(group)),
            }
        )
    return pd.DataFrame(output)


def section_code(industry_code: str) -> str:
    text = str(industry_code)
    return text[:1] if text[:1] in {"B", "C"} else ""


def build_support_registry(cells: pd.DataFrame, observed_ids: set[int], valid_ids: set[int] | None = None) -> pd.DataFrame:
    work = cells.copy()
    work["cell_id"] = work["cell_id"].astype(int)
    hidden = valid_ids or set()
    available = work[work["cell_id"].isin(observed_ids - hidden)].copy()
    temporal = set(zip(available["region_key"], available["industry_code"], available["target_name"]))
    regional_counts = available.groupby(["source_region", "industry_code", "period", "target_name"]).size().to_dict()
    industry_counts = available.groupby(["region_key", "period", "target_name"]).size().to_dict()
    parent_keys = set(zip(work["source_region"], work["industry_section"], work["period"], work["target_name"])) if "valid_parent" not in work else set(
        zip(work.loc[work["valid_parent"], "source_region"], work.loc[work["valid_parent"], "industry_section"], work.loc[work["valid_parent"], "period"], work.loc[work["valid_parent"], "target_name"])
    )
    rows: list[dict[str, Any]] = []
    for row in work.to_dict("records"):
        cell_id = int(row["cell_id"])
        is_observed = cell_id in observed_ids and cell_id not in hidden
        has_temporal = (row["region_key"], row["industry_code"], row["target_name"]) in temporal
        has_regional = regional_counts.get((row["source_region"], row["industry_code"], row["period"], row["target_name"]), 0) >= 2
        has_industry = industry_counts.get((row["region_key"], row["period"], row["target_name"]), 0) >= 2
        has_parent = (row["source_region"], row["industry_section"], row["period"], row["target_name"]) in parent_keys
        if is_observed:
            support = "S0_observed"
        elif has_temporal:
            support = "S1_temporal"
        elif has_regional:
            support = "S2_regional"
        elif has_industry:
            support = "S3_industry"
        elif has_parent:
            support = "S4_parent_only"
        elif has_regional or has_industry:
            support = "S5_sparse_multi_axis"
        else:
            support = "S6_not_estimable"
        rows.append(
            {
                "cell_id": cell_id,
                "support_class": support,
                "has_temporal_support": int(has_temporal),
                "has_regional_support": int(has_regional),
                "has_industry_support": int(has_industry),
                "has_valid_parent": int(has_parent),
                "support_uses_actual_value": "N",
            }
        )
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class ConstraintDecision:
    status: str
    role: str
    residual_total: float
    reason: str


def decide_constraint(
    official_total: float,
    fixed_observed_total: float,
    complete_child_universe: bool,
    duplicate_parent_count: int = 1,
    unit_match: bool = True,
) -> ConstraintDecision:
    residual = float(official_total) - float(fixed_observed_total)
    if duplicate_parent_count != 1:
        return ConstraintDecision("rejected", "validation_only", residual, "duplicate_parent")
    if not unit_match:
        return ConstraintDecision("rejected", "validation_only", residual, "unit_mismatch")
    if not complete_child_universe:
        return ConstraintDecision("rejected", "validation_only", residual, "incomplete_child_universe")
    if residual < -1e-8:
        return ConstraintDecision("rejected", "validation_only", residual, "negative_residual")
    return ConstraintDecision("usable", "hard", max(residual, 0.0), "same_universe_nonnegative_residual")


def reconcile_residual_share(raw: Iterable[float], residual_total: float) -> np.ndarray:
    values = nonnegative(raw)
    if residual_total < -EPSILON:
        raise ValueError("negative residual cannot be reconciled")
    if len(values) == 0:
        return values
    total = float(values.sum())
    if total <= EPSILON:
        return np.full(len(values), max(residual_total, 0.0) / len(values))
    return values * max(residual_total, 0.0) / total


def reconcile_entropy(raw: Iterable[float], residual_total: float) -> np.ndarray:
    prior = np.maximum(nonnegative(raw), EPSILON)
    return reconcile_residual_share(prior, residual_total)


def reconcile_least_squares(raw: Iterable[float], residual_total: float, weights: Iterable[float] | None = None) -> np.ndarray:
    values = nonnegative(raw)
    if residual_total < -EPSILON:
        raise ValueError("negative residual cannot be reconciled")
    if not len(values):
        return values
    if weights is None:
        ordered = np.sort(values)[::-1]
        cumulative = np.cumsum(ordered)
        candidates = ordered - (cumulative - residual_total) / np.arange(1, len(values) + 1) > 0
        rho = int(np.where(candidates)[0][-1]) if candidates.any() else 0
        theta = (cumulative[rho] - residual_total) / (rho + 1)
        return np.maximum(values - theta, 0.0)
    w = np.maximum(np.asarray(weights, dtype=float), EPSILON)
    objective = lambda x: float(np.sum(w * (x - values) ** 2))
    result = minimize(objective, reconcile_residual_share(values, residual_total), method="SLSQP", bounds=[(0.0, None)] * len(values), constraints=[{"type": "eq", "fun": lambda x: float(x.sum() - residual_total)}], options={"maxiter": 300, "ftol": 1e-10})
    if not result.success:
        return reconcile_residual_share(values, residual_total)
    return nonnegative(result.x)


def hamilton_integerize(values: Iterable[float], total: int | None = None) -> np.ndarray:
    x = nonnegative(values)
    target = int(round(float(x.sum()))) if total is None else int(total)
    floors = np.floor(x).astype(int)
    remainder = target - int(floors.sum())
    fractions = x - floors
    if remainder > 0:
        order = np.argsort(-fractions, kind="stable")
        floors[order[:remainder]] += 1
    elif remainder < 0:
        order = np.argsort(fractions, kind="stable")
        for idx in order:
            if remainder == 0:
                break
            removable = min(floors[idx], -remainder)
            floors[idx] -= removable
            remainder += removable
    return floors


def soft_impute_prediction(train: pd.DataFrame, valid: pd.DataFrame, rank: int = 5, iterations: int = 20, shrinkage: float = 0.1) -> np.ndarray:
    keys = ["region_key", "industry_code"]
    train_key = train.assign(matrix_col=train["industry_code"].astype(str) + "@" + train["period"].astype(str))
    valid_key = valid.assign(matrix_col=valid["industry_code"].astype(str) + "@" + valid["period"].astype(str))
    rows = sorted(set(train_key["region_key"]) | set(valid_key["region_key"]))
    cols = sorted(set(train_key["matrix_col"]) | set(valid_key["matrix_col"]))
    row_index = {value: idx for idx, value in enumerate(rows)}
    col_index = {value: idx for idx, value in enumerate(cols)}
    matrix = np.full((len(rows), len(cols)), np.nan)
    for row in train_key.to_dict("records"):
        matrix[row_index[row["region_key"]], col_index[row["matrix_col"]]] = math.log1p(max(float(row["value"]), 0.0))
    observed = np.isfinite(matrix)
    global_mean = float(np.nanmean(matrix)) if observed.any() else 0.0
    filled = np.where(observed, matrix, global_mean)
    for _ in range(iterations):
        centered = filled - filled.mean(axis=0, keepdims=True)
        use_rank = max(1, min(rank, min(centered.shape) - 1))
        svd = TruncatedSVD(n_components=use_rank, random_state=20260718)
        reconstructed = svd.inverse_transform(svd.fit_transform(centered)) + filled.mean(axis=0, keepdims=True)
        reconstructed = (1.0 - shrinkage) * reconstructed + shrinkage * global_mean
        filled = np.where(observed, matrix, reconstructed)
    return np.array([max(math.expm1(filled[row_index[row.region_key], col_index[row.matrix_col]]), 0.0) for row in valid_key.itertuples()], dtype=float)


def metric_toy_cases() -> pd.DataFrame:
    cases = [
        ("perfect_prediction", [0, 1, 10], [0, 1, 10], 0.0),
        ("constant_overprediction", [1, 1], [2, 2], 1.0),
        ("constant_underprediction", [2, 2], [1, 1], 0.5),
        ("all_zero_actual", [0, 0], [0, 0], 0.0),
        ("tiny_denominator", [0.001], [0.002], 1.0),
        ("mixed_zero_nonzero", [0, 10], [2, 8], 0.4),
    ]
    rows = []
    for case_id, actual, pred, expected in cases:
        calculated = wmape(actual, pred)
        rows.append({"test_id": case_id, "expected": expected, "calculated": calculated, "status": "pass" if (math.isnan(expected) and math.isnan(calculated)) or math.isclose(expected, calculated, rel_tol=1e-9, abs_tol=1e-9) else "fail"})
    repeated = pd.DataFrame(
        {
            "target_name": ["x", "x", "x"],
            "model_id": ["m", "m", "m"],
            "mask_id": ["a", "b", "b"],
            "mask_scenario": ["s", "s", "s"],
            "cell_id": [1, 1, 2],
            "actual": [10.0, 10.0, 10.0],
            "prediction": [0.0, 10.0, 10.0],
        }
    )
    calculated = float(aggregate_prediction_metrics(repeated).iloc[0]["cell_balanced_wmape"])
    rows.append({"test_id": "repeated_same_cell", "expected": 0.25, "calculated": calculated, "status": "pass" if math.isclose(calculated, 0.25) else "fail"})
    return pd.DataFrame(rows)
