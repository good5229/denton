from __future__ import annotations

from collections import defaultdict
from math import exp, log
from statistics import mean
from typing import Any

import numpy as np

from data_availability import annual_forecast_origin, is_available_as_of
from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv
from run_ml_baseline_experiment import GradientBoostedTrees, RegressionTree, ridge_fit


TARGET_SECTORS = {"A00", "B00", "D00"}
STRUCTURAL_LAG_MONTHS = 12
QUARTERLY_LAG_MONTHS = 2
REPORT_PATH = ROOT / "reports" / "sector_specific_model_experiment.md"


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


def load_target_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv"):
        if row.get("sector_code") not in TARGET_SECTORS:
            continue
        predicted = parse_number(row.get("predicted_annual_gva"))
        actual = parse_number(row.get("actual_annual_gva"))
        year = parse_number(row.get("target_year"))
        if predicted is None or actual is None or predicted <= 0 or actual <= 0 or year is None:
            continue
        rows.append(
            {
                "area_code": row.get("area_code", ""),
                "area_name": row.get("area_name", ""),
                "sector_code": row.get("sector_code", ""),
                "sector_name": row.get("sector_name", ""),
                "target_year": int(year),
                "baseline": predicted,
                "actual": actual,
                "method": row.get("method", ""),
            }
        )
    return rows


def load_structural() -> dict[tuple[str, str, int, str], float]:
    out: dict[tuple[str, str, int, str], float] = {}
    for row in read_csv(PROCESSED_DIR / "sector_structural_business_stats.csv"):
        value = parse_number(row.get("value"))
        year = parse_number(row.get("prd_de"))
        if value is None or year is None:
            continue
        out[(row.get("c1_id", ""), row.get("sector_code", ""), int(year), row.get("metric", ""))] = value
    return out


def load_quarterly_indicator(filename: str, area_code: str, sector_code: str) -> dict[str, float]:
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
    for row in read_csv(PROCESSED_DIR / "energy_exogenous_with_ecos_quarterly.csv"):
        value = parse_number(row.get("quarterly_average"))
        if value is None:
            value = parse_number(row.get("quarterly_value"))
        if value is None:
            continue
        out[row.get("indicator", "")][row.get("period", "")] = value
    return out


def feature_context() -> dict[str, Any]:
    return {
        "structural": load_structural(),
        "exogenous": load_exogenous(),
        "production_cache": {},
        "area_codes": sorted({row.get("area_code", "") for row in load_target_rows()}),
    }


def production_filename(sector_code: str) -> str | None:
    if sector_code == "B00":
        return "rolling_mining_production_index.csv"
    if sector_code == "D00":
        return "rolling_electricity_gas_production_index.csv"
    return None


def log1p_or_zero(value: float | None) -> float:
    return log(1.0 + value) if value is not None and value >= 0 else 0.0


def yoy(current: float | None, previous: float | None) -> float:
    if current is None or previous is None or previous == 0:
        return 0.0
    return current / previous - 1.0


def build_features(rows: list[dict[str, Any]], ctx: dict[str, Any]) -> np.ndarray:
    structural: dict[tuple[str, str, int, str], float] = ctx["structural"]
    exogenous: dict[str, dict[str, float]] = ctx["exogenous"]
    area_index = {area: idx for idx, area in enumerate(ctx["area_codes"])}
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
    width = 8 + len(area_index) + len(exog_names) * 2
    x = np.zeros((len(rows), width), dtype=float)
    for i, row in enumerate(rows):
        year = int(row["target_year"])
        area = row["area_code"]
        sector = row["sector_code"]
        x[i, 0] = 1.0
        x[i, 1] = log(float(row["baseline"]))
        x[i, 2] = (year - 2020) / 10.0
        structural_years = {
            key_year
            for (key_area, key_sector, key_year, _), _value in structural.items()
            if key_area == area and key_sector == sector
        }
        feature_year = latest_annual_year(structural_years, year)
        prev_feature_year = feature_year - 1 if feature_year else None
        for offset, metric in enumerate(["establishments", "employees", "sales"]):
            current = structural.get((area, sector, feature_year, metric)) if feature_year else None
            previous = structural.get((area, sector, prev_feature_year, metric)) if prev_feature_year else None
            x[i, 3 + offset] = log1p_or_zero(current)
            if metric == "sales":
                x[i, 6] = yoy(current, previous)
        prod_file = production_filename(sector)
        if prod_file:
            cache_key = (prod_file, area, sector)
            if cache_key not in ctx["production_cache"]:
                ctx["production_cache"][cache_key] = load_quarterly_indicator(prod_file, area, sector)
            prod = ctx["production_cache"][cache_key]
            periods = latest_quarters(set(prod), year, 4)
            if periods:
                x[i, 7] = mean(prod[p] for p in periods)
        area_pos = area_index.get(area)
        if area_pos is not None:
            x[i, 8 + area_pos] = 1.0
        start = 8 + len(area_index)
        if sector == "D00":
            for j, name in enumerate(exog_names):
                series = exogenous.get(name, {})
                periods = latest_quarters(set(series), year, 4)
                if periods:
                    latest = series[periods[-1]]
                    avg = mean(series[p] for p in periods)
                    x[i, start + j * 2] = log1p_or_zero(latest)
                    x[i, start + j * 2 + 1] = yoy(latest, avg)
    return x


def metrics(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    actual_sum = 0.0
    abs_error_sum = 0.0
    ape: list[float] = []
    for row in rows:
        pred = parse_number(row.get(field))
        actual = parse_number(row.get("actual"))
        if pred is None or actual is None or actual == 0:
            continue
        error = pred - actual
        actual_sum += abs(actual)
        abs_error_sum += abs(error)
        ape.append(abs(error / actual) * 100.0)
    return {
        "comparison_count": len(ape),
        "mape": round(sum(ape) / len(ape), 6) if ape else "",
        "wmape": round(abs_error_sum / actual_sum * 100.0, 6) if actual_sum else "",
    }


def fit_predict_model(model_name: str, x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    if model_name == "ridge":
        beta = ridge_fit(x_train, y_train, float(params["alpha"]))
        return x_test @ beta
    if model_name == "tree":
        return RegressionTree(max_depth=int(params["max_depth"]), min_leaf=int(params["min_leaf"])).fit(x_train, y_train).predict(x_test)
    if model_name == "boosted_tree":
        return GradientBoostedTrees(rounds=int(params["rounds"]), learning_rate=float(params["learning_rate"])).fit(x_train, y_train).predict(x_test)
    raise ValueError(model_name)


def param_grid(model_name: str) -> list[dict[str, Any]]:
    if model_name == "ridge":
        return [{"alpha": value} for value in [0.2, 1.0, 5.0, 20.0, 80.0]]
    if model_name == "tree":
        return [{"max_depth": d, "min_leaf": l} for d in [2, 3, 4] for l in [8, 15, 25]]
    if model_name == "boosted_tree":
        return [{"rounds": r, "learning_rate": lr} for r in [10, 25, 50] for lr in [0.04, 0.08, 0.15]]
    return [{}]


def tune_params(model_name: str, train_rows: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, Any]:
    train_years = sorted({int(row["target_year"]) for row in train_rows})
    if len(train_years) < 3:
        return param_grid(model_name)[0]
    val_year = train_years[-1]
    fit_rows = [row for row in train_rows if int(row["target_year"]) < val_year]
    val_rows = [row for row in train_rows if int(row["target_year"]) == val_year]
    if not fit_rows or not val_rows:
        return param_grid(model_name)[0]
    x_fit = build_features(fit_rows, ctx)
    x_val = build_features(val_rows, ctx)
    y_fit = np.array([log(float(row["actual"]) / float(row["baseline"])) for row in fit_rows])
    best_params = param_grid(model_name)[0]
    best_wmape = float("inf")
    for params in param_grid(model_name):
        pred_ratio = fit_predict_model(model_name, x_fit, y_fit, x_val, params)
        scored = []
        for row, ratio in zip(val_rows, pred_ratio):
            scored.append({**row, "prediction": float(row["baseline"]) * exp(float(ratio))})
        score = parse_number(metrics(scored, "prediction").get("wmape"))
        if score is not None and score < best_wmape:
            best_wmape = score
            best_params = params
    return best_params


def run() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows = load_target_rows()
    ctx = feature_context()
    predictions: list[dict[str, Any]] = []
    tuning_rows: list[dict[str, Any]] = []
    for sector in sorted(TARGET_SECTORS):
        sector_rows = [row for row in all_rows if row["sector_code"] == sector]
        for target_year in sorted({row["target_year"] for row in sector_rows}):
            train = [row for row in sector_rows if row["target_year"] < target_year]
            test = [row for row in sector_rows if row["target_year"] == target_year]
            if len(train) < 30 or not test:
                continue
            x_train = build_features(train, ctx)
            x_test = build_features(test, ctx)
            y_train = np.array([log(float(row["actual"]) / float(row["baseline"])) for row in train])
            model_outputs: dict[str, tuple[np.ndarray, dict[str, Any]]] = {}
            for model_name in ["ridge", "tree", "boosted_tree"]:
                params = tune_params(model_name, train, ctx)
                pred_ratio = fit_predict_model(model_name, x_train, y_train, x_test, params)
                model_outputs[model_name] = (pred_ratio, params)
                tuning_rows.append({"sector_code": sector, "target_year": target_year, "model": model_name, **params})
            for idx, row in enumerate(test):
                out = {
                    **row,
                    "baseline_prediction": round(float(row["baseline"]), 6),
                    "forecast_as_of": f"{target_year}-01-01",
                    "leakage_policy": "train rows and feature releases must be strictly before forecast_as_of; structural business features use max year <= target_year-2",
                }
                for model_name, (values, params) in model_outputs.items():
                    pred = float(row["baseline"]) * exp(float(values[idx]))
                    out[f"{model_name}_prediction"] = round(pred, 6)
                    out[f"{model_name}_params"] = ";".join(f"{key}={value}" for key, value in sorted(params.items()))
                predictions.append(out)
    summary: list[dict[str, Any]] = []
    for sector in sorted(TARGET_SECTORS):
        part = [row for row in predictions if row["sector_code"] == sector]
        for field, label in [
            ("baseline_prediction", "baseline"),
            ("ridge_prediction", "ridge_residual"),
            ("tree_prediction", "tree_residual"),
            ("boosted_tree_prediction", "boosted_tree_residual"),
        ]:
            summary.append({"sector_code": sector, "model": label, **metrics(part, field)})
    for field, label in [
        ("baseline_prediction", "baseline"),
        ("ridge_prediction", "ridge_residual"),
        ("tree_prediction", "tree_residual"),
        ("boosted_tree_prediction", "boosted_tree_residual"),
    ]:
        summary.append({"sector_code": "__ALL__", "model": label, **metrics(predictions, field)})
    return predictions, summary + tuning_rows


def write_report(summary: list[dict[str, Any]]) -> None:
    perf = [row for row in summary if "comparison_count" in row]
    lines = [
        "# A/B/D 산업별 전용 모델 실험",
        "",
        "## 원칙",
        "",
        "- target year의 actual은 학습에 사용하지 않는다.",
        "- 구조변수는 target-year 1월 1일 기준 공개 가능하다고 볼 수 있는 최신 연도만 사용한다.",
        "- `sector_structural_business_stats.csv`의 사업체수·종사자수·매출액은 보수적으로 `target_year-2` 이하만 feature로 사용한다.",
        "- 전기가스 외생변수는 공표 지연 2개월을 가정하고, 예측 기준일 이전에 공표 가능한 분기만 사용한다.",
        "",
        "## 성능",
        "",
        "| sector | model | count | MAPE | WMAPE |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in perf:
        lines.append(f"| {row['sector_code']} | {row['model']} | {row['comparison_count']} | {row['mape']} | {row['wmape']} |")
    lines.extend(
        [
            "",
            "## 해석",
            "",
            "이 실험은 산업별 특화 feature와 파라미터 탐색이 baseline을 개선하는지 검정한다. 성능이 개선되지 않는 산업은 기존 Denton/indicator baseline을 유지하고, 개선되는 산업만 제한적으로 residual correction을 채택하는 것이 안전하다.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    predictions, rows = run()
    perf = [row for row in rows if "comparison_count" in row]
    tuning = [row for row in rows if "comparison_count" not in row]
    write_csv(PROCESSED_DIR / "sector_specific_model_predictions.csv", predictions)
    write_csv(PROCESSED_DIR / "sector_specific_model_comparison.csv", perf)
    write_csv(PROCESSED_DIR / "sector_specific_model_tuning.csv", tuning)
    write_report(perf)
    print(f"sector-specific predictions: {len(predictions)}")
    print(f"comparison rows: {len(perf)}")
    print(f"tuning rows: {len(tuning)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
