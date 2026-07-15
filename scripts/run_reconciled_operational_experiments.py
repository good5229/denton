from __future__ import annotations

from collections import defaultdict
from math import exp, log
from statistics import mean, median
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv
from run_ml_baseline_experiment import ridge_fit

try:
    import xgboost as xgb

    XGB_STATUS = "available"
except Exception as exc:  # Optional dependency.
    xgb = None
    XGB_STATUS = f"unavailable: {type(exc).__name__}: {exc}"


EPS = 1e-12
PREDICTIONS = PROCESSED_DIR / "reconciled_model_predictions.csv"
SAFE = PROCESSED_DIR / "reconciled_model_safe_predictions.csv"
ML_FIELD = "xgboost_log_ratio_reconciled_prediction"
YEARS_FOR_HISTORY = 2


def num(value: Any, default: float = 0.0) -> float:
    parsed = parse_number(value)
    return default if parsed is None else float(parsed)


def load_rows() -> list[dict[str, Any]]:
    safe_by_key: dict[tuple[str, str, int], dict[str, str]] = {}
    if SAFE.exists():
        for row in read_csv(SAFE):
            safe_by_key[(row["area_code"], row["sector_code"], int(row["target_year"]))] = row
    rows: list[dict[str, Any]] = []
    for row in read_csv(PREDICTIONS):
        actual = num(row.get("actual_annual_gva"))
        baseline = num(row.get("baseline_prediction"))
        full_ml = num(row.get(ML_FIELD))
        parent_baseline = num(row.get("parent_baseline_total"))
        parent_actual = num(row.get("parent_actual_total"))
        if min(actual, baseline, full_ml, parent_baseline, parent_actual) <= 0:
            continue
        year = int(row["target_year"])
        safe = safe_by_key.get((row["area_code"], row["sector_code"], year), {})
        rows.append(
            {
                "area_code": row["area_code"],
                "area_name": row["area_name"],
                "sector_code": row["sector_code"],
                "sector_name": row["sector_name"],
                "target_year": year,
                "actual": actual,
                "baseline": baseline,
                "full_ml": full_ml,
                "safe_selected": num(safe.get("safe_selected_prediction"), baseline),
                "safe_mode": safe.get("selected_mode", ""),
                "safe_alpha": num(safe.get("selected_shrink_alpha"), 0.0),
                "safe_blend_weight": num(safe.get("selected_blend_weight"), 0.0),
                "parent_baseline": parent_baseline,
                "parent_actual": parent_actual,
            }
        )
    return sorted(rows, key=lambda r: (r["target_year"], r["sector_code"], r["area_code"]))


def grouped(rows: list[dict[str, Any]], keys: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[tuple(row[key] for key in keys)].append(row)
    return out


def wmape(rows: list[dict[str, Any]], field: str) -> float:
    denom = sum(abs(float(r["actual"])) for r in rows)
    if denom <= 0:
        return 0.0
    return sum(abs(float(r[field]) - float(r["actual"])) for r in rows) / denom * 100.0


def mape(rows: list[dict[str, Any]], field: str) -> float:
    values = [abs((float(r[field]) - float(r["actual"])) / float(r["actual"])) * 100.0 for r in rows if float(r["actual"])]
    return mean(values) if values else 0.0


def improvement(base: float, current: float) -> float:
    return (base - current) / base * 100.0 if base else 0.0


def parent_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for (year, sector), items in sorted(grouped(rows, ["target_year", "sector_code"]).items()):
        first = items[0]
        baseline = first["parent_baseline"]
        actual = first["parent_actual"]
        out.append(
            {
                "target_year": year,
                "sector_code": sector,
                "sector_name": first["sector_name"],
                "parent_baseline": baseline,
                "parent_actual": actual,
                "log_ratio": log((actual + EPS) / (baseline + EPS)),
            }
        )
    return out


def standardize_fit(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean_values = x.mean(axis=0)
    std_values = x.std(axis=0)
    std_values[std_values < EPS] = 1.0
    scaled = (x - mean_values) / std_values
    scaled[:, 0] = 1.0
    mean_values[0] = 0.0
    std_values[0] = 1.0
    return scaled, mean_values, std_values


def standardize_apply(x: np.ndarray, mean_values: np.ndarray, std_values: np.ndarray) -> np.ndarray:
    scaled = (x - mean_values) / std_values
    scaled[:, 0] = 1.0
    return scaled


def parent_matrix(rows: list[dict[str, Any]], sectors: list[str]) -> np.ndarray:
    sector_index = {sector: idx for idx, sector in enumerate(sectors)}
    vectors = []
    for row in rows:
        dummy = [0.0] * len(sectors)
        dummy[sector_index[row["sector_code"]]] = 1.0
        vectors.append(
            [
                1.0,
                (row["target_year"] - 2017.0) / 10.0,
                log(row["parent_baseline"] + EPS),
            ]
            + dummy
        )
    return np.asarray(vectors, dtype=float)


def ridge_parent_predict(train: list[dict[str, Any]], test: list[dict[str, Any]], sectors: list[str]) -> list[float]:
    if len(train) < 8:
        return [0.0 for _ in test]
    x_train = parent_matrix(train, sectors)
    y_train = np.asarray([row["log_ratio"] for row in train], dtype=float)
    x_test = parent_matrix(test, sectors)
    scaled_train, mean_values, std_values = standardize_fit(x_train)
    beta = ridge_fit(scaled_train, y_train, 2.0)
    return list(standardize_apply(x_test, mean_values, std_values) @ beta)


def xgboost_parent_predict(train: list[dict[str, Any]], test: list[dict[str, Any]], sectors: list[str]) -> list[float]:
    if xgb is None or len(train) < 20:
        return [0.0 for _ in test]
    train_matrix = xgb.DMatrix(parent_matrix(train, sectors), label=np.asarray([row["log_ratio"] for row in train], dtype=float))
    test_matrix = xgb.DMatrix(parent_matrix(test, sectors))
    booster = xgb.train(
        {
            "objective": "reg:squarederror",
            "max_depth": 2,
            "eta": 0.05,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "lambda": 5.0,
            "min_child_weight": 3.0,
            "seed": 42,
            "nthread": 1,
            "verbosity": 0,
        },
        train_matrix,
        num_boost_round=60,
    )
    return list(np.asarray(booster.predict(test_matrix), dtype=float))


def parent_history_log_ratio(parent_rows: list[dict[str, Any]], sector: str, year: int) -> list[float]:
    return [r["log_ratio"] for r in parent_rows if r["sector_code"] == sector and r["target_year"] < year]


def run_parent_models(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    parents = parent_groups(rows)
    sectors = sorted({r["sector_code"] for r in parents})
    out: list[dict[str, Any]] = []
    for year in sorted({r["target_year"] for r in parents}):
        test = [r for r in parents if r["target_year"] == year]
        train = [r for r in parents if r["target_year"] < year]
        global_hist = [r["log_ratio"] for r in train]
        ridge_pred = ridge_parent_predict(train, test, sectors)
        xgb_pred = xgboost_parent_predict(train, test, sectors)
        for idx, row in enumerate(test):
            sector_hist = parent_history_log_ratio(parents, row["sector_code"], row["target_year"])
            rolling = sector_hist[-YEARS_FOR_HISTORY:]
            global_mean = mean(global_hist) if global_hist else 0.0
            sector_mean = mean(sector_hist) if sector_hist else global_mean
            sector_median = median(sector_hist) if sector_hist else global_mean
            rolling_mean = mean(rolling) if rolling else sector_mean
            shrink_weight = len(sector_hist) / (len(sector_hist) + 3.0)
            shrunken = shrink_weight * sector_mean + (1.0 - shrink_weight) * global_mean
            models = {
                "parent_baseline": 0.0,
                "parent_global_mean_log_ratio": global_mean,
                "parent_sector_mean_log_ratio": sector_mean,
                "parent_sector_median_log_ratio": sector_median,
                "parent_rolling2_log_ratio": rolling_mean,
                "parent_shrunken_sector_log_ratio": shrunken,
                "parent_ridge_log_ratio": ridge_pred[idx],
                "parent_xgboost_log_ratio": xgb_pred[idx],
                "parent_ensemble": 0.5 * ridge_pred[idx] + 0.5 * xgb_pred[idx],
            }
            for model, pred_log_ratio in models.items():
                prediction = row["parent_baseline"] * exp(pred_log_ratio)
                out.append(
                    {
                        "model": model,
                        "target_year": row["target_year"],
                        "sector_code": row["sector_code"],
                        "sector_name": row["sector_name"],
                        "parent_actual": round(row["parent_actual"], 6),
                        "parent_baseline": round(row["parent_baseline"], 6),
                        "parent_prediction": round(prediction, 6),
                        "parent_absolute_error": round(abs(prediction - row["parent_actual"]), 6),
                        "parent_ape": round(abs(prediction - row["parent_actual"]) / row["parent_actual"] * 100.0, 6),
                        "parent_bias": round((prediction - row["parent_actual"]) / row["parent_actual"] * 100.0, 6),
                        "predicted_log_ratio": round(pred_log_ratio, 12),
                        "history_rows_used": len(train),
                        "sector_history_rows_used": len(sector_hist),
                        "leakage_policy": "target year parent actual is excluded from all fitted/bias-correction models",
                    }
                )
    summary = summarize_parent_predictions(out)
    return out, summary


def summarize_parent_predictions(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    baseline_by_group: dict[tuple[int, str], float] = {}
    for row in predictions:
        if row["model"] == "parent_baseline":
            baseline_by_group[(row["target_year"], row["sector_code"])] = float(row["parent_ape"])
    for (model,), items in sorted(grouped(predictions, ["model"]).items()):
        denom = sum(abs(float(r["parent_actual"])) for r in items)
        err = sum(abs(float(r["parent_prediction"]) - float(r["parent_actual"])) for r in items)
        bias = sum(float(r["parent_prediction"]) - float(r["parent_actual"]) for r in items) / denom * 100.0 if denom else 0.0
        by_year = grouped(items, ["target_year"])
        by_sector = grouped(items, ["sector_code"])
        improved_years = 0
        for year_key, year_items in by_year.items():
            base_items = [r for r in predictions if r["model"] == "parent_baseline" and r["target_year"] == year_key[0]]
            if parent_wmape(year_items) < parent_wmape(base_items):
                improved_years += 1
        improved_sectors = 0
        sector_improvements = []
        for sector_key, sector_items in by_sector.items():
            base_items = [r for r in predictions if r["model"] == "parent_baseline" and r["sector_code"] == sector_key[0]]
            base_w = parent_wmape(base_items)
            cur_w = parent_wmape(sector_items)
            sector_improvements.append(improvement(base_w, cur_w))
            if cur_w < base_w:
                improved_sectors += 1
        out.append(
            {
                "model": model,
                "count": len(items),
                "parent_wmape": round(err / denom * 100.0, 6) if denom else "",
                "parent_mape": round(mean([float(r["parent_ape"]) for r in items]), 6) if items else "",
                "parent_bias": round(bias, 6),
                "improved_year_count": improved_years,
                "improved_sector_count": improved_sectors,
                "worst_sector_improvement_pct": round(min(sector_improvements), 6) if sector_improvements else "",
            }
        )
    return out


def parent_wmape(rows: list[dict[str, Any]]) -> float:
    denom = sum(abs(float(r["parent_actual"])) for r in rows)
    if denom <= 0:
        return 0.0
    return sum(abs(float(r["parent_prediction"]) - float(r["parent_actual"])) for r in rows) / denom * 100.0


def parent_predictions_by_key(parent_rows: list[dict[str, Any]], model: str) -> dict[tuple[int, str], float]:
    return {(r["target_year"], r["sector_code"]): float(r["parent_prediction"]) for r in parent_rows if r["model"] == model}


def choose_parent_model(parent_summary: list[dict[str, Any]]) -> str:
    candidates = list(parent_summary)
    if not candidates:
        return "parent_baseline"
    return min(candidates, key=lambda r: float(r["parent_wmape"]))["model"]


def hard_scale(row: dict[str, Any], raw_value: float, target_parent: float) -> float:
    return raw_value * target_parent / row["parent_baseline"] if row["parent_baseline"] else raw_value


def sector_parent_uncertainty(parent_rows: list[dict[str, Any]], sector: str, year: int) -> float:
    hist = [r for r in parent_rows if r["model"] == "parent_baseline" and r["sector_code"] == sector and r["target_year"] < year]
    return parent_wmape(hist) if hist else 1.0


def soft_beta_from_uncertainty(parent_wmape_pct: float) -> float:
    return 1.0 / (1.0 + (parent_wmape_pct / 2.0) ** 2)


def run_soft_reconciliation(
    rows: list[dict[str, Any]],
    parent_rows: list[dict[str, Any]],
    parent_summary: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    best_parent = choose_parent_model(parent_summary)
    best_parent_by_key = parent_predictions_by_key(parent_rows, best_parent)
    parent_baseline_by_key = parent_predictions_by_key(parent_rows, "parent_baseline")
    out: list[dict[str, Any]] = []
    for row in rows:
        key = (row["target_year"], row["sector_code"])
        target_parent = best_parent_by_key.get(key, row["parent_baseline"])
        baseline_parent = parent_baseline_by_key.get(key, row["parent_baseline"])
        beta_uncertainty = soft_beta_from_uncertainty(sector_parent_uncertainty(parent_rows, row["sector_code"], row["target_year"]))
        predictions = {
            "no_reconciliation": row["full_ml"],
            "hard_reconciliation_forecast_parent": hard_scale(row, row["full_ml"], baseline_parent),
            "hard_reconciliation_best_parent": hard_scale(row, row["full_ml"], target_parent),
            "soft_reconciliation_global_025": row["full_ml"] + 0.25 * (hard_scale(row, row["full_ml"], target_parent) - row["full_ml"]),
            "soft_reconciliation_global_050": row["full_ml"] + 0.50 * (hard_scale(row, row["full_ml"], target_parent) - row["full_ml"]),
            "soft_reconciliation_global_075": row["full_ml"] + 0.75 * (hard_scale(row, row["full_ml"], target_parent) - row["full_ml"]),
            "soft_reconciliation_uncertainty": row["full_ml"] + beta_uncertainty * (hard_scale(row, row["full_ml"], target_parent) - row["full_ml"]),
        }
        for method, prediction in predictions.items():
            out.append(
                {
                    "reconciliation_method": method,
                    "parent_model": best_parent if "best_parent" in method or "soft" in method else "parent_baseline",
                    "target_year": row["target_year"],
                    "area_code": row["area_code"],
                    "area_name": row["area_name"],
                    "sector_code": row["sector_code"],
                    "sector_name": row["sector_name"],
                    "actual_annual_gva": round(row["actual"], 6),
                    "baseline_prediction": round(row["baseline"], 6),
                    "full_ml_prediction": round(row["full_ml"], 6),
                    "prediction": round(max(prediction, 0.0), 6),
                    "ml_selected": method != "hard_reconciliation_forecast_parent",
                    "parent_target": round(target_parent, 6),
                    "soft_beta": round(beta_uncertainty if method == "soft_reconciliation_uncertainty" else 1.0, 6),
                }
            )
    return out, summarize_policy_predictions(out, "reconciliation_method", "prediction")


def run_parent_shocks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    shocks = [-0.10, -0.05, -0.03, -0.01, 0.0, 0.01, 0.03, 0.05, 0.10]
    out: list[dict[str, Any]] = []
    for shock in shocks:
        for method, beta in [
            ("hard_reconciliation", 1.0),
            ("soft_reconciliation_global_050", 0.5),
            ("soft_reconciliation_global_025", 0.25),
        ]:
            tmp = []
            for row in rows:
                target_parent = row["parent_baseline"] * (1.0 + shock)
                hard = hard_scale(row, row["full_ml"], target_parent)
                prediction = row["full_ml"] + beta * (hard - row["full_ml"])
                tmp.append({**row, "prediction": prediction})
            out.append(shock_summary(tmp, method, shock))
    return out


def shock_summary(rows: list[dict[str, Any]], method: str, shock: float) -> dict[str, Any]:
    base = wmape(rows, "baseline")
    current = wmape(rows, "prediction")
    sector_improvements = []
    for _sector, items in grouped(rows, ["sector_code"]).items():
        sector_improvements.append(improvement(wmape(items, "baseline"), wmape(items, "prediction")))
    parent_gap = abs(sum(r["prediction"] for r in rows) - sum(r["actual"] for r in rows)) / sum(r["actual"] for r in rows) * 100.0
    return {
        "reconciliation_method": method,
        "parent_shock": shock,
        "child_wmape": round(current, 6),
        "child_mape": round(mape(rows, "prediction"), 6),
        "parent_error": round(parent_gap, 6),
        "worst_sector_improvement": round(min(sector_improvements), 6),
        "degraded_sector_years": degraded_sector_years(rows, "prediction"),
        "mean_parent_gap_after_reconciliation": round(parent_gap, 6),
        "improvement_vs_baseline_pct": round(improvement(base, current), 6),
    }


def raw_shrink_value(row: dict[str, Any], alpha: float) -> float:
    return row["baseline"] * exp(alpha * log((row["full_ml"] + EPS) / (row["baseline"] + EPS)))


def reconcile_to_forecast_parent(items: list[dict[str, Any]], raw_values: list[float]) -> list[float]:
    total = sum(max(v, 0.0) for v in raw_values)
    parent = items[0]["parent_baseline"]
    if total <= 0:
        return [row["baseline"] for row in items]
    return [parent * max(value, 0.0) / total for value in raw_values]


def rolling_gamma_for_sector(rows: list[dict[str, Any]], sector: str, year: int) -> float:
    train = [r for r in rows if r["sector_code"] == sector and r["target_year"] < year]
    if len({r["target_year"] for r in train}) < 2:
        return 999.0
    best_gamma = 0.0
    best_score = float("inf")
    for gamma in [0.0, 1.0, 2.0, 5.0, 10.0]:
        candidates = []
        for (_y, _s), items in grouped(train, ["target_year", "sector_code"]).items():
            raw = []
            for item in items:
                uncertainty = abs(log((item["full_ml"] + EPS) / (item["baseline"] + EPS)))
                alpha = 1.0 / (1.0 + gamma * uncertainty)
                raw.append(raw_shrink_value(item, alpha))
            for item, pred in zip(items, reconcile_to_forecast_parent(items, raw)):
                candidates.append({**item, "prediction": pred})
        score = wmape(candidates, "prediction")
        if score < best_score:
            best_score = score
            best_gamma = gamma
    return best_gamma


def run_adaptive_shrinkage(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    out: list[dict[str, Any]] = []
    for (year, sector), items in grouped(rows, ["target_year", "sector_code"]).items():
        gamma = rolling_gamma_for_sector(rows, sector, year)
        raw_values = []
        meta = []
        for row in items:
            uncertainty = abs(log((row["full_ml"] + EPS) / (row["baseline"] + EPS)))
            alpha = 0.0 if gamma >= 999.0 else 1.0 / (1.0 + gamma * uncertainty)
            raw_values.append(raw_shrink_value(row, alpha))
            meta.append((uncertainty, alpha, gamma))
        reconciled = reconcile_to_forecast_parent(items, raw_values)
        for row, pred, (uncertainty, alpha, gamma_value) in zip(items, reconciled, meta):
            out.append(
                {
                    "target_year": year,
                    "sector_code": sector,
                    "sector_name": row["sector_name"],
                    "area_code": row["area_code"],
                    "area_name": row["area_name"],
                    "actual_annual_gva": round(row["actual"], 6),
                    "baseline_prediction": round(row["baseline"], 6),
                    "full_ml_prediction": round(row["full_ml"], 6),
                    "prediction": round(pred, 6),
                    "ml_selected": alpha > 0.0,
                    "adaptive_alpha": round(alpha, 8),
                    "selected_gamma": gamma_value,
                    "baseline_ml_disagreement": round(uncertainty, 8),
                    "leakage_policy": "gamma selected from same-sector pre-target years only",
                }
            )
    return out, summarize_policy_predictions([dict(r, policy="adaptive_shrinkage") for r in out], "policy", "prediction")


def historical_sector_improvement(rows: list[dict[str, Any]], sector: str, year: int, field: str = "full_ml") -> list[float]:
    values = []
    hist = [r for r in rows if r["sector_code"] == sector and r["target_year"] < year]
    for _year, items in grouped(hist, ["target_year"]).items():
        values.append(improvement(wmape(items, "baseline"), wmape(items, field)))
    return values


def run_regret_gating(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    thresholds = [0.0, 0.1, 0.2, 0.5]
    out: list[dict[str, Any]] = []
    for row in rows:
        history = historical_sector_improvement(rows, row["sector_code"], row["target_year"])
        avg = mean(history) if history else -999.0
        recent = history[-1] if history else -999.0
        worst = min(history) if history else -999.0
        std = float(np.std(history)) if len(history) > 1 else 999.0
        lower = avg - std
        for threshold in thresholds:
            use_ml = avg > threshold
            prediction = row["full_ml"] if use_ml else row["baseline"]
            out.append(make_gate_row(row, f"regret_mean_gt_{threshold}", prediction, use_ml, avg, lower, recent, worst))
        use_ml = lower > 0.0
        out.append(make_gate_row(row, "regret_lower_bound_gt_0", row["full_ml"] if use_ml else row["baseline"], use_ml, avg, lower, recent, worst))
    return out, summarize_policy_predictions(out, "policy", "prediction")


def make_gate_row(row: dict[str, Any], policy: str, prediction: float, use_ml: bool, avg: float, lower: float, recent: float, worst: float) -> dict[str, Any]:
    return {
        "policy": policy,
        "target_year": row["target_year"],
        "sector_code": row["sector_code"],
        "sector_name": row["sector_name"],
        "area_code": row["area_code"],
        "area_name": row["area_name"],
        "actual_annual_gva": round(row["actual"], 6),
        "baseline_prediction": round(row["baseline"], 6),
        "full_ml_prediction": round(row["full_ml"], 6),
        "prediction": round(prediction, 6),
        "ml_selected": use_ml,
        "expected_improvement_mean_pct": round(avg, 6),
        "expected_improvement_lower_bound_pct": round(lower, 6),
        "recent_improvement_pct": round(recent, 6),
        "worst_history_improvement_pct": round(worst, 6),
        "leakage_policy": "gate features are calculated from pre-target sector-year losses only",
    }


def summarize_policy_predictions(rows: list[dict[str, Any]], group_field: str, prediction_field: str) -> list[dict[str, Any]]:
    out = []
    oracle = oracle_wmape(rows)
    for (policy,), items in sorted(grouped(rows, [group_field]).items()):
        normalized = [
            {
                **r,
                "actual": num(r.get("actual_annual_gva"), num(r.get("actual"))),
                "baseline": num(r.get("baseline_prediction"), num(r.get("baseline"))),
                "prediction": num(r.get(prediction_field)),
            }
            for r in items
        ]
        base = wmape(normalized, "baseline")
        current = wmape(normalized, "prediction")
        sector_year_imps = sector_year_improvements(normalized, "prediction")
        ml_rows = [r for r in items if str(r.get("ml_selected", "")).lower() == "true"]
        out.append(
            {
                "policy": policy,
                "count": len(items),
                "wmape": round(current, 6),
                "mape": round(mape(normalized, "prediction"), 6),
                "improvement_vs_baseline_pct": round(improvement(base, current), 6),
                "improved_year_count": improved_year_count(normalized, "prediction"),
                "degraded_sector_year_count": sum(1 for v in sector_year_imps if v < 0.0),
                "materially_degraded_sector_year_count": sum(1 for v in sector_year_imps if v < -2.0),
                "worst_sector_year_improvement": round(min(sector_year_imps), 6) if sector_year_imps else "",
                "p05_sector_year_improvement": round(float(np.percentile(sector_year_imps, 5)), 6) if sector_year_imps else "",
                "median_sector_year_improvement": round(median(sector_year_imps), 6) if sector_year_imps else "",
                "mean_sector_year_improvement": round(mean(sector_year_imps), 6) if sector_year_imps else "",
                "oracle_regret_wmape": round(current - oracle, 6) if oracle else "",
                "candidate_ml_selection_rate": round(len(ml_rows) / len(items), 6) if items else "",
                "effective_ml_application_rate": round(len(ml_rows) / len(items), 6) if items else "",
            }
        )
    return out


def oracle_wmape(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    normalized = []
    for row in rows:
        actual = num(row.get("actual_annual_gva"), num(row.get("actual")))
        baseline = num(row.get("baseline_prediction"), num(row.get("baseline")))
        full_ml = num(row.get("full_ml_prediction"), num(row.get("full_ml")),)
        normalized.append({**row, "actual": actual, "baseline": baseline, "full_ml": full_ml})
    chosen = []
    for (_sector, _year), items in grouped(normalized, ["sector_code", "target_year"]).items():
        base = wmape(items, "baseline")
        ml = wmape(items, "full_ml")
        field = "full_ml" if ml < base else "baseline"
        chosen.extend({**r, "oracle_prediction": r[field]} for r in items)
    return wmape(chosen, "oracle_prediction")


def sector_year_improvements(rows: list[dict[str, Any]], prediction_field: str) -> list[float]:
    values = []
    for _key, items in grouped(rows, ["sector_code", "target_year"]).items():
        values.append(improvement(wmape(items, "baseline"), wmape(items, prediction_field)))
    return values


def improved_year_count(rows: list[dict[str, Any]], prediction_field: str) -> int:
    return sum(1 for _year, items in grouped(rows, ["target_year"]).items() if wmape(items, prediction_field) < wmape(items, "baseline"))


def degraded_sector_years(rows: list[dict[str, Any]], prediction_field: str) -> int:
    return sum(1 for value in sector_year_improvements(rows, prediction_field) if value < 0)


def final_policy_summary(
    rows: list[dict[str, Any]],
    soft_summary: list[dict[str, Any]],
    adaptive_summary: list[dict[str, Any]],
    regret_summary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    base_rows = []
    for row in rows:
        base_rows.append({**row, "policy": "baseline", "prediction": row["baseline"], "ml_selected": False})
        base_rows.append({**row, "policy": "full_ml", "prediction": row["full_ml"], "ml_selected": True})
        base_rows.append({**row, "policy": "current_safe", "prediction": row["safe_selected"], "ml_selected": row["safe_alpha"] > 0 or row["safe_blend_weight"] > 0})
    base_summary = summarize_policy_predictions(base_rows, "policy", "prediction")
    selected_soft = [r for r in soft_summary if r["policy"] in {"hard_reconciliation_best_parent", "soft_reconciliation_uncertainty"}]
    selected_regret = sorted(regret_summary, key=lambda r: float(r["wmape"]))[:2]
    return base_summary + selected_soft + adaptive_summary + selected_regret


def write_markdown_table(lines: list[str], rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> None:
    lines.append("| " + " | ".join(label for label, _key in columns) + " |")
    lines.append("| " + " | ".join("---:" if label not in {"model", "policy", "method", "sector"} else "---" for label, _key in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")) for _label, key in columns) + " |")


def write_reports(
    parent_summary: list[dict[str, Any]],
    soft_summary: list[dict[str, Any]],
    shock_rows: list[dict[str, Any]],
    adaptive_summary: list[dict[str, Any]],
    regret_summary: list[dict[str, Any]],
    final_summary: list[dict[str, Any]],
    best_parent_model: str,
) -> None:
    reports = ROOT / "reports"
    lines = [
        "# 부모 총량 예측 및 오차 분해",
        "",
        f"- XGBoost 상태: `{XGB_STATUS}`",
        f"- 운영 후보 부모 모델: `{best_parent_model}`",
        "- 모든 부모 모델은 target year 이전의 부모 오차만 사용했다.",
        "",
        "## 부모 총량 모델 비교",
        "",
    ]
    write_markdown_table(lines, parent_summary, [("model", "model"), ("WMAPE", "parent_wmape"), ("MAPE", "parent_mape"), ("bias", "parent_bias"), ("improved years", "improved_year_count"), ("improved sectors", "improved_sector_count"), ("worst sector", "worst_sector_improvement_pct")])
    lines.extend(
        [
            "",
            "## 해석",
            "",
            "부모 총량은 하위 지역 share와 독립된 병목이다. 부모 예측을 바꾸면 모든 하위 셀에 같은 방향의 스케일 오차가 전파되므로, 하위 ML의 개선폭은 부모 모델 정확도와 함께 해석해야 한다.",
        ]
    )
    (reports / "parent_total_model_report.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Soft Reconciliation 비교", "", f"- 부모 총량 보정 후보: `{best_parent_model}`", "", "## 방법별 성능", ""]
    write_markdown_table(lines, soft_summary, [("method", "policy"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("improvement %", "improvement_vs_baseline_pct"), ("degraded", "degraded_sector_year_count"), ("material degraded", "materially_degraded_sector_year_count"), ("worst", "worst_sector_year_improvement"), ("oracle regret", "oracle_regret_wmape")])
    lines.extend(["", "## Parent Shock", ""])
    write_markdown_table(lines, shock_rows, [("method", "reconciliation_method"), ("shock", "parent_shock"), ("WMAPE", "child_wmape"), ("MAPE", "child_mape"), ("parent error", "parent_error"), ("worst", "worst_sector_improvement"), ("degraded", "degraded_sector_years")])
    (reports / "soft_reconciliation_report.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Adaptive Residual Shrinkage", "", "## 결과", ""]
    write_markdown_table(lines, adaptive_summary, [("policy", "policy"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("improvement %", "improvement_vs_baseline_pct"), ("degraded", "degraded_sector_year_count"), ("material degraded", "materially_degraded_sector_year_count"), ("worst", "worst_sector_year_improvement")])
    lines.extend(["", "## 해석", "", "행별 baseline-ML 괴리가 클수록 residual 적용 강도를 낮추는 정책이다. gamma는 같은 산업의 target 이전 연도에서만 선택했다."])
    (reports / "adaptive_shrinkage_report.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Expected Regret Gating", "", "## 정책 비교", ""]
    write_markdown_table(lines, regret_summary, [("policy", "policy"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("improvement %", "improvement_vs_baseline_pct"), ("degraded", "degraded_sector_year_count"), ("material degraded", "materially_degraded_sector_year_count"), ("worst", "worst_sector_year_improvement"), ("ML rate", "candidate_ml_selection_rate")])
    lines.extend(["", "## 해석", "", "사전 gating은 target year 이전 산업별 WMAPE 개선 이력으로 다음 연도 ML 적용 여부를 고른다. Oracle과 달리 평가연도 actual/loss는 선택에 쓰지 않는다."])
    (reports / "regret_gating_report.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Reconciled Feature Ablation", "", "이번 실행에서는 전체 feature 재학습 ablation 대신 운영정책 진단을 우선했다. 기존 전체 XGBoost가 단순 residual persistence보다 우수하다는 점은 `reports/reconciled_model_next_experiments.md`에서 확인됐지만, F0-F10 drop-one 재학습은 별도 장시간 실험으로 남긴다.", "", "## 다음 구현 항목", "", "- `run_reconciled_model_experiment.py`의 feature vector에 이름과 group metadata를 붙인다.", "- 동일 tuned parameter grid로 `full`, `drop-one`, `core-only`를 rolling 재학습한다.", "- gain/permutation importance를 target year별로 저장한다."]
    (reports / "reconciled_feature_ablation.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 산업별 모델 구조 비교", "", "현재 실행은 global XGBoost residual 결과를 기반으로 정책 레벨 선택을 비교했다. 산업별 개별 모델은 표본 수가 작아 rolling outer test와 shrinkage 규칙을 붙여 다음 단계에서 실행한다.", "", "## 비교 예정 구조", "", "- global model", "- sector model", "- sector group model", "- global plus sector residual correction", "- global sector shrinkage"]
    (reports / "sector_model_structure.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Reconciled ML 운영정책 통합 결과", "", f"- 부모 총량 후보: `{best_parent_model}`", f"- XGBoost 상태: `{XGB_STATUS}`", "", "## 최종 정책 비교", ""]
    write_markdown_table(lines, final_summary, [("policy", "policy"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("improvement %", "improvement_vs_baseline_pct"), ("improved years", "improved_year_count"), ("degraded", "degraded_sector_year_count"), ("material degraded", "materially_degraded_sector_year_count"), ("worst", "worst_sector_year_improvement"), ("oracle regret", "oracle_regret_wmape"), ("effective ML rate", "effective_ml_application_rate")])
    lines.extend(["", "## 판단", "", "운영 후보는 전체 WMAPE 개선과 downside 제한을 함께 봐야 한다. `current_safe`, `adaptive_shrinkage`, `expected regret gate`, `soft reconciliation` 중 WMAPE와 material degradation이 동시에 낮은 정책을 시군구 pilot 후보로 올리는 것이 합리적이다."])
    (reports / "reconciled_operational_policy_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows = load_rows()
    parent_predictions, parent_summary = run_parent_models(rows)
    best_parent = choose_parent_model(parent_summary)
    soft_predictions, soft_summary = run_soft_reconciliation(rows, parent_predictions, parent_summary)
    shock_rows = run_parent_shocks(rows)
    adaptive_predictions, adaptive_summary = run_adaptive_shrinkage(rows)
    regret_predictions, regret_summary = run_regret_gating(rows)
    final_summary = final_policy_summary(rows, soft_summary, adaptive_summary, regret_summary)

    write_csv(PROCESSED_DIR / "parent_total_predictions.csv", parent_predictions)
    write_csv(PROCESSED_DIR / "parent_total_model_summary.csv", parent_summary)
    write_csv(PROCESSED_DIR / "soft_reconciliation_predictions.csv", soft_predictions)
    write_csv(PROCESSED_DIR / "soft_reconciliation_summary.csv", soft_summary)
    write_csv(PROCESSED_DIR / "soft_reconciliation_parent_shocks.csv", shock_rows)
    write_csv(PROCESSED_DIR / "adaptive_shrinkage_predictions.csv", adaptive_predictions)
    write_csv(PROCESSED_DIR / "adaptive_shrinkage_summary.csv", adaptive_summary)
    write_csv(PROCESSED_DIR / "regret_gating_predictions.csv", regret_predictions)
    write_csv(PROCESSED_DIR / "regret_gating_summary.csv", regret_summary)
    write_csv(PROCESSED_DIR / "reconciled_operational_policy_summary.csv", final_summary)
    write_reports(parent_summary, soft_summary, shock_rows, adaptive_summary, regret_summary, final_summary, best_parent)
    print(f"parent predictions: {len(parent_predictions)}")
    print(f"soft predictions: {len(soft_predictions)}")
    print(f"adaptive predictions: {len(adaptive_predictions)}")
    print(f"regret predictions: {len(regret_predictions)}")
    print(f"best parent model: {best_parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
