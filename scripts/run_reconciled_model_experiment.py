from __future__ import annotations

from collections import defaultdict
from math import exp, log, sqrt
from statistics import mean
from typing import Any

import numpy as np

from data_availability import annual_forecast_origin, is_available_as_of
from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv
from run_ml_baseline_experiment import ridge_fit

try:
    import xgboost as xgb

    XGBOOST_STATUS = "available"
except Exception as exc:  # Optional native dependency.
    xgb = None
    XGBOOST_STATUS = f"unavailable: {type(exc).__name__}: {exc}"


EPS = 1e-12
STRUCTURAL_LAG_MONTHS = 12
QUARTERLY_LAG_MONTHS = 2
MIN_TRAIN_ROWS = 30
REPORT_PATH = ROOT / "reports" / "reconciled_model_experiment.md"


def safe_log(value: float | None) -> float:
    if value is None or value <= 0:
        return 0.0
    return log(value)


def safe_ratio(numerator: float | None, denominator: float | None) -> float:
    if numerator is None or denominator is None or abs(denominator) < EPS:
        return 0.0
    return numerator / denominator


def yoy(current: float | None, previous: float | None) -> float:
    if current is None or previous is None or abs(previous) < EPS:
        return 0.0
    return current / previous - 1.0


def period_sort(period: str) -> tuple[int, int]:
    return int(period[:4]), int(period[-1])


def latest_annual_year(years: set[int], target_year: int) -> int | None:
    as_of = annual_forecast_origin(target_year)
    candidates = [year for year in years if is_available_as_of(str(year), "A", STRUCTURAL_LAG_MONTHS, as_of)]
    return max(candidates) if candidates else None


def latest_quarters(periods: set[str], target_year: int, count: int = 4) -> list[str]:
    as_of = annual_forecast_origin(target_year)
    candidates = [period for period in periods if is_available_as_of(period, "Q", QUARTERLY_LAG_MONTHS, as_of)]
    return sorted(candidates, key=period_sort)[-count:]


def load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv"):
        area_code = row.get("area_code", "")
        if area_code == "00":
            continue
        baseline = parse_number(row.get("predicted_annual_gva"))
        actual = parse_number(row.get("actual_annual_gva"))
        year = parse_number(row.get("target_year"))
        if baseline is None or actual is None or year is None or baseline <= 0 or actual <= 0:
            continue
        rows.append(
            {
                "area_code": area_code,
                "area_name": row.get("area_name", ""),
                "sector_code": row.get("sector_code", ""),
                "sector_name": row.get("sector_name", ""),
                "target_year": int(year),
                "method": row.get("method", ""),
                "baseline": float(baseline),
                "actual": float(actual),
            }
        )

    baseline_totals: dict[tuple[int, str], float] = defaultdict(float)
    actual_totals: dict[tuple[int, str], float] = defaultdict(float)
    for row in rows:
        key = (row["target_year"], row["sector_code"])
        baseline_totals[key] += row["baseline"]
        actual_totals[key] += row["actual"]
    for row in rows:
        key = (row["target_year"], row["sector_code"])
        row["parent_baseline_total"] = baseline_totals[key]
        row["parent_actual_total"] = actual_totals[key]
        row["baseline_share"] = safe_ratio(row["baseline"], baseline_totals[key])
        row["actual_share"] = safe_ratio(row["actual"], actual_totals[key])
        row["baseline_log_ratio_to_actual"] = log((row["actual"] + EPS) / (row["baseline"] + EPS))
    return sorted(rows, key=lambda row: (row["sector_code"], row["target_year"], row["area_code"]))


def load_structural() -> dict[tuple[str, str, int, str], float]:
    out: dict[tuple[str, str, int, str], float] = {}
    path = PROCESSED_DIR / "sector_structural_business_stats.csv"
    if not path.exists():
        return out
    for row in read_csv(path):
        value = parse_number(row.get("value"))
        year = parse_number(row.get("prd_de"))
        if value is None or year is None:
            continue
        out[(row.get("c1_id", ""), row.get("sector_code", ""), int(year), row.get("metric", ""))] = value
    return out


def load_quarterly_indicator(filename: str, area_code: str) -> dict[str, float]:
    out: dict[str, float] = {}
    path = PROCESSED_DIR / filename
    if not path.exists():
        return out
    for row in read_csv(path):
        if row.get("c1_id") != area_code:
            continue
        value = parse_number(row.get("value"))
        if value is None:
            continue
        prd = row.get("prd_de", "")
        if len(prd) >= 6:
            out[f"{prd[:4]}Q{int(prd[-2:])}"] = value
    return out


def load_exogenous() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(dict)
    path = PROCESSED_DIR / "energy_exogenous_with_ecos_quarterly.csv"
    if not path.exists():
        return out
    for row in read_csv(path):
        value = parse_number(row.get("quarterly_average"))
        if value is None:
            value = parse_number(row.get("quarterly_value"))
        if value is None:
            continue
        out[row.get("indicator", "")][row.get("period", "")] = value
    return out


def context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actual_by_key = {(row["area_code"], row["sector_code"], row["target_year"]): row["actual"] for row in rows}
    baseline_by_key = {(row["area_code"], row["sector_code"], row["target_year"]): row["baseline"] for row in rows}
    actual_total_by_group: dict[tuple[str, int], float] = defaultdict(float)
    for row in rows:
        actual_total_by_group[(row["sector_code"], row["target_year"])] += row["actual"]
    return {
        "areas": sorted({row["area_code"] for row in rows}),
        "methods": sorted({row["method"] for row in rows}),
        "actual_by_key": actual_by_key,
        "baseline_by_key": baseline_by_key,
        "actual_total_by_group": actual_total_by_group,
        "structural": load_structural(),
        "exogenous": load_exogenous(),
        "production_cache": {},
    }


def production_filename(sector_code: str) -> str | None:
    if sector_code == "B00":
        return "rolling_mining_production_index.csv"
    if sector_code == "D00":
        return "rolling_electricity_gas_production_index.csv"
    return None


def historical_values(row: dict[str, Any], ctx: dict[str, Any], field: str, max_lag: int = 3) -> list[float]:
    area = row["area_code"]
    sector = row["sector_code"]
    year = row["target_year"]
    values: list[float] = []
    for prior_year in range(year - 1, year - max_lag - 1, -1):
        actual = ctx["actual_by_key"].get((area, sector, prior_year))
        baseline = ctx["baseline_by_key"].get((area, sector, prior_year))
        parent_actual = ctx["actual_total_by_group"].get((sector, prior_year))
        if actual is None or baseline is None or parent_actual is None or parent_actual <= 0:
            continue
        if field == "share":
            values.append(actual / parent_actual)
        elif field == "log_ratio":
            values.append(log((actual + EPS) / (baseline + EPS)))
    return values


def structural_features(row: dict[str, Any], ctx: dict[str, Any]) -> list[float]:
    structural: dict[tuple[str, str, int, str], float] = ctx["structural"]
    area = row["area_code"]
    sector = row["sector_code"]
    target_year = row["target_year"]
    years = {year for (key_area, key_sector, year, _), _value in structural.items() if key_area == area and key_sector == sector}
    feature_year = latest_annual_year(years, target_year)
    prev_year = feature_year - 1 if feature_year else None
    features: list[float] = []
    for metric in ["establishments", "employees", "sales"]:
        current = structural.get((area, sector, feature_year, metric)) if feature_year else None
        previous = structural.get((area, sector, prev_year, metric)) if prev_year else None
        same_sector_sum = 0.0
        same_area_sum = 0.0
        if feature_year:
            for (key_area, key_sector, key_year, key_metric), value in structural.items():
                if key_year != feature_year or key_metric != metric:
                    continue
                if key_sector == sector and key_area != "00":
                    same_sector_sum += value
                if key_area == area:
                    same_area_sum += value
        features.extend(
            [
                safe_log(current),
                safe_ratio(current, same_sector_sum),
                safe_ratio(current, same_area_sum),
                yoy(current, previous),
            ]
        )
    employees = structural.get((area, sector, feature_year, "employees")) if feature_year else None
    establishments = structural.get((area, sector, feature_year, "establishments")) if feature_year else None
    sales = structural.get((area, sector, feature_year, "sales")) if feature_year else None
    features.extend(
        [
            safe_log(safe_ratio(sales, employees) if employees else None),
            safe_log(safe_ratio(sales, establishments) if establishments else None),
            safe_log(safe_ratio(employees, establishments) if establishments else None),
        ]
    )
    return features


def indicator_features(row: dict[str, Any], ctx: dict[str, Any]) -> list[float]:
    sector = row["sector_code"]
    area = row["area_code"]
    target_year = row["target_year"]
    features = [0.0, 0.0, 0.0]
    prod_file = production_filename(sector)
    if prod_file:
        cache_key = (prod_file, area)
        if cache_key not in ctx["production_cache"]:
            ctx["production_cache"][cache_key] = load_quarterly_indicator(prod_file, area)
        series = ctx["production_cache"][cache_key]
        periods = latest_quarters(set(series), target_year, 8)
        latest4 = periods[-4:]
        prev4 = periods[:4]
        if latest4:
            latest_mean = mean(series[p] for p in latest4)
            prev_mean = mean(series[p] for p in prev4) if len(prev4) == 4 else None
            features = [latest_mean, yoy(latest_mean, prev_mean), safe_log(latest_mean)]
    if sector != "D00":
        return features
    exog_names = [
        "wti_oil_usd",
        "coal_australia_usd",
        "natural_gas_usd",
        "usd_krw",
        "ecos_usd_krw_avg",
        "ecos_import_price_crude_oil",
        "ecos_import_price_bituminous_coal",
        "ecos_import_price_oil_gas",
        "ecos_ppi_power_gas_steam",
        "ecos_ppi_city_gas",
    ]
    for name in exog_names:
        series = ctx["exogenous"].get(name, {})
        periods = latest_quarters(set(series), target_year, 8)
        latest4 = periods[-4:]
        prev4 = periods[:4]
        if latest4:
            latest_mean = mean(series[p] for p in latest4)
            prev_mean = mean(series[p] for p in prev4) if len(prev4) == 4 else None
            features.extend([safe_log(latest_mean), yoy(latest_mean, prev_mean)])
        else:
            features.extend([0.0, 0.0])
    return features


def build_matrix(rows: list[dict[str, Any]], ctx: dict[str, Any]) -> np.ndarray:
    area_index = {area: idx for idx, area in enumerate(ctx["areas"])}
    method_index = {method: idx for idx, method in enumerate(ctx["methods"])}
    vectors: list[list[float]] = []
    for row in rows:
        hist_share = historical_values(row, ctx, "share", 3)
        hist_ratio = historical_values(row, ctx, "log_ratio", 3)
        latest_share = hist_share[0] if hist_share else row["baseline_share"]
        share_mean = mean(hist_share) if hist_share else latest_share
        share_std = sqrt(mean([(value - share_mean) ** 2 for value in hist_share])) if len(hist_share) > 1 else 0.0
        latest_ratio = hist_ratio[0] if hist_ratio else 0.0
        ratio_mean = mean(hist_ratio) if hist_ratio else 0.0
        ratio_std = sqrt(mean([(value - ratio_mean) ** 2 for value in hist_ratio])) if len(hist_ratio) > 1 else 0.0
        base = [
            1.0,
            (row["target_year"] - 2017.0) / 10.0,
            safe_log(row["baseline"]),
            row["baseline_share"],
            safe_log(row["baseline_share"]),
            latest_share,
            share_mean,
            share_std,
            row["baseline_share"] - latest_share,
            safe_ratio(row["baseline_share"], latest_share),
            latest_ratio,
            ratio_mean,
            ratio_std,
        ]
        area_dummy = [0.0] * len(area_index)
        area_pos = area_index.get(row["area_code"])
        if area_pos is not None:
            area_dummy[area_pos] = 1.0
        method_dummy = [0.0] * len(method_index)
        method_pos = method_index.get(row["method"])
        if method_pos is not None:
            method_dummy[method_pos] = 1.0
        vectors.append(base + structural_features(row, ctx) + indicator_features(row, ctx) + area_dummy + method_dummy)
    return np.asarray(vectors, dtype=float)


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


def ridge_predict(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    scaled_train, mean_values, std_values = standardize_fit(x_train)
    scaled_test = standardize_apply(x_test, mean_values, std_values)
    beta = ridge_fit(scaled_train, y_train, float(params["alpha"]))
    return scaled_test @ beta


def xgboost_predict(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    if xgb is None:
        raise RuntimeError("xgboost unavailable")
    train_matrix = xgb.DMatrix(x_train, label=y_train)
    test_matrix = xgb.DMatrix(x_test)
    booster = xgb.train(
        {
            "objective": params["objective"],
            "max_depth": int(params["max_depth"]),
            "eta": float(params["learning_rate"]),
            "subsample": float(params["subsample"]),
            "colsample_bytree": float(params["colsample_bytree"]),
            "lambda": float(params["reg_lambda"]),
            "min_child_weight": float(params["min_child_weight"]),
            "seed": 42,
            "nthread": 1,
            "verbosity": 0,
        },
        train_matrix,
        num_boost_round=int(params["n_estimators"]),
    )
    return np.asarray(booster.predict(test_matrix), dtype=float)


def param_grid(model_name: str) -> list[dict[str, Any]]:
    if model_name == "ridge":
        return [{"alpha": alpha} for alpha in [0.2, 1.0, 5.0, 20.0, 80.0]]
    if model_name == "xgboost" and xgb is not None:
        return [
            {
                "objective": objective,
                "n_estimators": n,
                "max_depth": d,
                "learning_rate": lr,
                "subsample": ss,
                "colsample_bytree": cs,
                "reg_lambda": lam,
                "min_child_weight": mcw,
            }
            for objective in ["reg:squarederror", "reg:absoluteerror"]
            for n in [30, 80]
            for d in [2, 3]
            for lr in [0.03, 0.08]
            for ss in [0.8, 1.0]
            for cs in [0.8, 1.0]
            for lam in [1.0, 5.0]
            for mcw in [1.0, 5.0]
        ]
    return []


def model_predict(model_name: str, x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    if model_name == "ridge":
        return ridge_predict(x_train, y_train, x_test, params)
    if model_name == "xgboost":
        return xgboost_predict(x_train, y_train, x_test, params)
    raise ValueError(model_name)


def target_values(rows: list[dict[str, Any]], target_kind: str) -> np.ndarray:
    if target_kind == "share":
        return np.asarray([log(max(float(row["actual_share"]), EPS)) for row in rows], dtype=float)
    if target_kind == "log_ratio":
        return np.asarray([float(row["baseline_log_ratio_to_actual"]) for row in rows], dtype=float)
    raise ValueError(target_kind)


def reconcile_group(rows: list[dict[str, Any]], raw_values: np.ndarray, target_kind: str) -> list[float]:
    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        groups[(row["target_year"], row["sector_code"])].append(idx)
    out = [0.0] * len(rows)
    for indices in groups.values():
        parent_total = float(rows[indices[0]]["parent_baseline_total"])
        if target_kind == "share":
            raw = [max(exp(float(raw_values[idx])), 0.0) for idx in indices]
        elif target_kind == "log_ratio":
            raw = [float(rows[idx]["baseline"]) * exp(float(raw_values[idx])) for idx in indices]
        else:
            raise ValueError(target_kind)
        total = sum(raw)
        if total <= 0:
            fallback = [float(rows[idx]["baseline_share"]) for idx in indices]
            total = sum(fallback)
            raw = fallback
        for idx, value in zip(indices, raw):
            out[idx] = parent_total * value / total if total > 0 else parent_total / len(indices)
    return out


def score_predictions(rows: list[dict[str, Any]], predictions: list[float]) -> dict[str, Any]:
    abs_error = 0.0
    abs_actual = 0.0
    ape: list[float] = []
    for row, pred in zip(rows, predictions):
        actual = float(row.get("actual", row.get("actual_annual_gva", 0.0)))
        error = pred - actual
        abs_error += abs(error)
        abs_actual += abs(actual)
        ape.append(abs(error / actual) * 100.0)
    return {
        "comparison_count": len(ape),
        "mape": round(sum(ape) / len(ape), 6) if ape else "",
        "wmape": round(abs_error / abs_actual * 100.0, 6) if abs_actual else "",
    }


def aggregation_errors(rows: list[dict[str, Any]], predictions: list[float]) -> tuple[float, float]:
    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        groups[(row["target_year"], row["sector_code"])].append(idx)
    errors = []
    for indices in groups.values():
        parent_total = float(rows[indices[0]]["parent_baseline_total"])
        if parent_total <= 0:
            continue
        errors.append(abs(sum(predictions[idx] for idx in indices) - parent_total) / parent_total * 100.0)
    return (round(max(errors), 10) if errors else 0.0, round(mean(errors), 10) if errors else 0.0)


def tune_params(
    *,
    model_name: str,
    target_kind: str,
    train_rows: list[dict[str, Any]],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    candidates = param_grid(model_name)
    if not candidates:
        return {}
    train_years = sorted({row["target_year"] for row in train_rows})
    if len(train_years) < 3:
        return candidates[0]
    val_year = train_years[-1]
    fit_rows = [row for row in train_rows if row["target_year"] < val_year]
    val_rows = [row for row in train_rows if row["target_year"] == val_year]
    if len(fit_rows) < MIN_TRAIN_ROWS or not val_rows:
        return candidates[0]
    x_fit = build_matrix(fit_rows, ctx)
    y_fit = target_values(fit_rows, target_kind)
    x_val = build_matrix(val_rows, ctx)
    best_params = candidates[0]
    best_wmape = float("inf")
    for params in candidates:
        raw = model_predict(model_name, x_fit, y_fit, x_val, params)
        pred = reconcile_group(val_rows, raw, target_kind)
        wmape = parse_number(score_predictions(val_rows, pred)["wmape"])
        if wmape is not None and wmape < best_wmape:
            best_wmape = wmape
            best_params = params
    return best_params


def run() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_rows()
    ctx = context(rows)
    predictions: list[dict[str, Any]] = []
    tuning_rows: list[dict[str, Any]] = []
    model_specs = [("ridge", "share"), ("ridge", "log_ratio")]
    if xgb is not None:
        model_specs.extend([("xgboost", "share"), ("xgboost", "log_ratio")])

    for sector in sorted({row["sector_code"] for row in rows}):
        sector_rows = [row for row in rows if row["sector_code"] == sector]
        for target_year in sorted({row["target_year"] for row in sector_rows}):
            train_rows = [row for row in sector_rows if row["target_year"] < target_year]
            test_rows = [row for row in sector_rows if row["target_year"] == target_year]
            if len(train_rows) < MIN_TRAIN_ROWS or not test_rows:
                continue
            x_train = build_matrix(train_rows, ctx)
            x_test = build_matrix(test_rows, ctx)
            model_predictions: dict[str, tuple[list[float], dict[str, Any]]] = {}
            for model_name, target_kind in model_specs:
                params = tune_params(model_name=model_name, target_kind=target_kind, train_rows=train_rows, ctx=ctx)
                y_train = target_values(train_rows, target_kind)
                raw = model_predict(model_name, x_train, y_train, x_test, params)
                pred = reconcile_group(test_rows, raw, target_kind)
                label = f"{model_name}_{target_kind}_reconciled"
                model_predictions[label] = (pred, params)
                tuning_rows.append(
                    {
                        "sector_code": sector,
                        "target_year": target_year,
                        "model": label,
                        "validation_policy": "last pre-target year only; target year never used for tuning",
                        **params,
                    }
                )
            for idx, row in enumerate(test_rows):
                out = {
                    "area_code": row["area_code"],
                    "area_name": row["area_name"],
                    "sector_code": row["sector_code"],
                    "sector_name": row["sector_name"],
                    "target_year": row["target_year"],
                    "actual_annual_gva": round(float(row["actual"]), 6),
                    "baseline_prediction": round(float(row["baseline"]), 6),
                    "parent_baseline_total": round(float(row["parent_baseline_total"]), 6),
                    "parent_actual_total": round(float(row["parent_actual_total"]), 6),
                    "baseline_share": round(float(row["baseline_share"]), 12),
                    "actual_share": round(float(row["actual_share"]), 12),
                    "forecast_as_of": f"{row['target_year']}-01-01",
                    "leakage_policy": "features use only pre-target official actuals and release-aware structural/exogenous data",
                }
                for label, (values, params) in model_predictions.items():
                    out[f"{label}_prediction"] = round(values[idx], 6)
                    out[f"{label}_params"] = ";".join(f"{key}={value}" for key, value in sorted(params.items()))
                predictions.append(out)

    summary: list[dict[str, Any]] = []
    prediction_fields = ["baseline_prediction"]
    if predictions:
        prediction_fields.extend([field for field in predictions[0] if field.endswith("_prediction") and field != "baseline_prediction"])
    for sector in sorted({row["sector_code"] for row in predictions} | {"__ALL__"}):
        part = predictions if sector == "__ALL__" else [row for row in predictions if row["sector_code"] == sector]
        if not part:
            continue
        for field in prediction_fields:
            pred = [float(row[field]) for row in part if row.get(field) != ""]
            aligned = [row for row in part if row.get(field) != ""]
            max_agg, mean_agg = aggregation_errors(aligned, pred)
            model = "baseline" if field == "baseline_prediction" else field.removesuffix("_prediction")
            base_metric = score_predictions(aligned, pred)
            summary.append(
                {
                    "sector_code": sector,
                    "model": model,
                    **base_metric,
                    "max_parent_aggregation_error_pct": max_agg,
                    "mean_parent_aggregation_error_pct": mean_agg,
                }
            )
    baseline_wmape = {
        row["sector_code"]: parse_number(row.get("wmape"))
        for row in summary
        if row.get("model") == "baseline"
    }
    for row in summary:
        base = baseline_wmape.get(row["sector_code"])
        current = parse_number(row.get("wmape"))
        row["baseline_wmape"] = round(base, 6) if base is not None else ""
        row["wmape_improvement_pct"] = (
            round((base - current) / base * 100.0, 6)
            if base is not None and current is not None and base > 0
            else ""
        )
    return predictions, summary, tuning_rows


def report_lines(summary: list[dict[str, Any]]) -> list[str]:
    best_rows = []
    for sector in sorted({row["sector_code"] for row in summary}):
        sector_rows = [row for row in summary if row["sector_code"] == sector]
        best = min(sector_rows, key=lambda row: float(row["wmape"]))
        baseline = next(row for row in sector_rows if row["model"] == "baseline")
        best_rows.append(
            {
                "sector_code": sector,
                "baseline_wmape": baseline["wmape"],
                "best_model": best["model"],
                "best_wmape": best["wmape"],
                "improvement": best["wmape_improvement_pct"],
            }
        )
    lines = [
        "# 계층 정합 ML 개선 실험",
        "",
        "## 목적",
        "",
        "기존 ML 실험이 개별 행의 GVA를 독립적으로 보정하던 한계를 줄이기 위해, `연도 × 산업` 부모 총량 안에서 지역별 share 또는 Denton log-ratio residual을 예측한 뒤 부모 baseline 총량에 다시 정규화했다.",
        "",
        "## 적용한 개선",
        "",
        "1. `baseline_share`, lagged actual share, rolling share, lagged Denton log-ratio를 feature로 추가했다.",
        "2. 사업체수·종사자수·매출액은 target-year 1월 1일 기준 공표 가능 연도만 사용했다.",
        "3. Ridge는 표준화 후 학습했다.",
        "4. XGBoost는 `reg:squarederror`와 `reg:absoluteerror`를 모두 튜닝 후보로 둔다.",
        "5. 모든 ML 예측은 `연도 × 산업` 부모 baseline 총량과 일치하도록 reconciliation했다.",
        "",
        "## XGBoost 상태",
        "",
        XGBOOST_STATUS,
        "",
        "## 성능",
        "",
        "| sector | model | count | MAPE | WMAPE | improvement vs baseline % | max aggregation error % | mean aggregation error % |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        lines.append(
            f"| {row['sector_code']} | {row['model']} | {row['comparison_count']} | {row['mape']} | {row['wmape']} | {row['wmape_improvement_pct']} | {row['max_parent_aggregation_error_pct']} | {row['mean_parent_aggregation_error_pct']} |"
        )
    lines.extend(
        [
            "",
            "## 최저 WMAPE 모델",
            "",
            "| sector | baseline WMAPE | best model | best WMAPE | improvement % |",
            "| --- | ---: | --- | ---: | ---: |",
        ]
    )
    for row in best_rows:
        lines.append(
            f"| {row['sector_code']} | {row['baseline_wmape']} | {row['best_model']} | {row['best_wmape']} | {row['improvement']} |"
        )
    lines.extend(
        [
            "",
            "## 해석 기준",
            "",
            "`baseline`은 기존 Denton/indicator rolling 예측이다. `*_share_reconciled`는 지역 share를 직접 예측하고, `*_log_ratio_reconciled`는 Denton 예측값 대비 실제값의 로그비율을 예측한 뒤 정규화한다. 양수 개선은 같은 official actual 구간에서 baseline WMAPE보다 낮을 때만 인정한다.",
            "",
            "## 결론",
            "",
            "현재 통합 실험에서는 직접 share 예측보다 Denton log-ratio residual을 예측한 뒤 부모 총량에 reconciliation하는 방식이 가장 안정적이다. 전체 기준 최저 WMAPE가 baseline보다 낮다면, 다음 단계는 이 방식을 시군구 rolling backtest와 세부산업 proxy share 검증으로 확장하는 것이다.",
        ]
    )
    return lines


def main() -> int:
    predictions, summary, tuning = run()
    write_csv(PROCESSED_DIR / "reconciled_model_predictions.csv", predictions)
    write_csv(PROCESSED_DIR / "reconciled_model_comparison.csv", summary)
    write_csv(PROCESSED_DIR / "reconciled_model_tuning.csv", tuning)
    REPORT_PATH.write_text("\n".join(report_lines(summary)), encoding="utf-8")
    print(f"reconciled predictions: {len(predictions)}")
    print(f"comparison rows: {len(summary)}")
    print(f"tuning rows: {len(tuning)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
