from __future__ import annotations

from collections import defaultdict
from math import exp, log
from statistics import mean, median
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, parse_number, write_csv
from run_reconciled_model_experiment import (
    EPS,
    MIN_TRAIN_ROWS,
    build_matrix,
    context,
    historical_values,
    load_rows,
    reconcile_group,
    safe_log,
    safe_ratio,
    structural_features,
    target_values,
    xgb,
    xgboost_predict,
)


PARAMS = {
    "objective": "reg:squarederror",
    "n_estimators": 60,
    "max_depth": 2,
    "learning_rate": 0.05,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "reg_lambda": 5.0,
    "min_child_weight": 3.0,
}


def grouped(rows: list[dict[str, Any]], keys: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[tuple(row[key] for key in keys)].append(row)
    return out


def matrix_groups(x: np.ndarray, ctx: dict[str, Any], sector_code: str) -> dict[str, list[int]]:
    area_count = len(ctx["areas"])
    method_count = len(ctx["methods"])
    tail_start = x.shape[1] - area_count - method_count
    indicator_end = tail_start
    structural_start = 13
    structural_end = 28
    groups = {
        "F0_baseline_share": [0, 2, 3, 4],
        "F1_lagged_share": [5],
        "F2_rolling_share": [6, 7, 8, 9],
        "F3_lagged_residual": [10],
        "F4_rolling_residual": [11, 12],
        "F5_structural": list(range(structural_start, min(structural_end, x.shape[1]))),
        "F6_F7_indicator_exogenous": list(range(min(structural_end, indicator_end), indicator_end)),
        "F8_area_static": list(range(indicator_end, indicator_end + area_count)),
        "F9_method_static": list(range(indicator_end + area_count, x.shape[1])),
        "F10_time": [1],
    }
    return {name: sorted({idx for idx in indices if 0 <= idx < x.shape[1]}) for name, indices in groups.items()}


def select_columns(x: np.ndarray, columns: list[int]) -> np.ndarray:
    if not columns:
        return np.ones((x.shape[0], 1), dtype=float)
    columns = sorted({0, *columns})
    return x[:, columns]


def variant_columns(groups: dict[str, list[int]], variant: str) -> list[int]:
    all_cols = sorted({idx for indices in groups.values() for idx in indices})
    if variant == "full":
        return all_cols
    if variant.startswith("drop_"):
        drop = variant.removeprefix("drop_")
        return sorted(set(all_cols) - set(groups.get(drop, [])))
    if variant == "core_F0":
        return groups["F0_baseline_share"]
    if variant == "core_F0_F3":
        return groups["F0_baseline_share"] + groups["F3_lagged_residual"]
    if variant == "core_F0_F5":
        return groups["F0_baseline_share"] + groups["F5_structural"]
    if variant == "core_F0_F3_F5":
        return groups["F0_baseline_share"] + groups["F3_lagged_residual"] + groups["F5_structural"]
    if variant == "core_F0_F3_F5_F6F7":
        return groups["F0_baseline_share"] + groups["F3_lagged_residual"] + groups["F5_structural"] + groups["F6_F7_indicator_exogenous"]
    if variant == "no_lagged_residual":
        return sorted(set(all_cols) - set(groups["F3_lagged_residual"]))
    if variant == "no_residual_features":
        return sorted(set(all_cols) - set(groups["F3_lagged_residual"]) - set(groups["F4_rolling_residual"]))
    if variant == "residual_features_only":
        return groups["F0_baseline_share"] + groups["F3_lagged_residual"] + groups["F4_rolling_residual"]
    if variant == "structural_features_only":
        return groups["F0_baseline_share"] + groups["F5_structural"]
    raise ValueError(variant)


def wmape(rows: list[dict[str, Any]], field: str) -> float:
    denom = sum(abs(float(row.get("actual", row.get("actual_annual_gva", 0.0)))) for row in rows)
    if denom <= 0:
        return 0.0
    return sum(abs(float(row[field]) - float(row.get("actual", row.get("actual_annual_gva", 0.0)))) for row in rows) / denom * 100.0


def mape(rows: list[dict[str, Any]], field: str) -> float:
    values = []
    for row in rows:
        actual = float(row.get("actual", row.get("actual_annual_gva", 0.0)))
        if actual:
            values.append(abs((float(row[field]) - actual) / actual) * 100.0)
    return mean(values) if values else 0.0


def improvement(base: float, current: float) -> float:
    return (base - current) / base * 100.0 if base else 0.0


def run_ablation() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if xgb is None:
        return [], []
    rows = load_rows()
    ctx = context(rows)
    variants = [
        "full",
        "drop_F1_lagged_share",
        "drop_F2_rolling_share",
        "drop_F3_lagged_residual",
        "drop_F4_rolling_residual",
        "drop_F5_structural",
        "drop_F6_F7_indicator_exogenous",
        "drop_F8_area_static",
        "drop_F9_method_static",
        "drop_F10_time",
        "core_F0",
        "core_F0_F3",
        "core_F0_F5",
        "core_F0_F3_F5",
        "core_F0_F3_F5_F6F7",
        "no_lagged_residual",
        "no_residual_features",
        "residual_features_only",
        "structural_features_only",
    ]
    predictions: list[dict[str, Any]] = []
    for sector in sorted({row["sector_code"] for row in rows}):
        sector_rows = [row for row in rows if row["sector_code"] == sector]
        for target_year in sorted({row["target_year"] for row in sector_rows}):
            train_rows = [row for row in sector_rows if row["target_year"] < target_year]
            test_rows = [row for row in sector_rows if row["target_year"] == target_year]
            if len(train_rows) < MIN_TRAIN_ROWS or not test_rows:
                continue
            x_train_full = build_matrix(train_rows, ctx)
            x_test_full = build_matrix(test_rows, ctx)
            groups = matrix_groups(x_train_full, ctx, sector)
            y_train = target_values(train_rows, "log_ratio")
            for variant in variants:
                cols = variant_columns(groups, variant)
                raw = xgboost_predict(select_columns(x_train_full, cols), y_train, select_columns(x_test_full, cols), PARAMS)
                pred = reconcile_group(test_rows, raw, "log_ratio")
                for row, value in zip(test_rows, pred):
                    predictions.append(
                        {
                            "variant": variant,
                            "target_year": row["target_year"],
                            "sector_code": row["sector_code"],
                            "sector_name": row["sector_name"],
                            "area_code": row["area_code"],
                            "area_name": row["area_name"],
                            "actual_annual_gva": round(row["actual"], 6),
                            "baseline_prediction": round(row["baseline"], 6),
                            "prediction": round(value, 6),
                            "feature_count": len(cols),
                            "model_params": ";".join(f"{key}={value}" for key, value in PARAMS.items()),
                        }
                    )
    return predictions, summarize(predictions, "variant")


def sector_group(sector: str) -> str:
    if sector in {"A00", "B00", "C00", "D00", "F00"}:
        return sector
    if sector in {"G00", "H00", "I00"}:
        return "trade_transport_food"
    if sector in {"J00", "K00", "L00", "MN0"}:
        return "market_services"
    return "public_social_services"


def run_structure() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if xgb is None:
        return [], []
    rows = load_rows()
    ctx = context(rows)
    predictions: list[dict[str, Any]] = []
    for target_year in sorted({row["target_year"] for row in rows}):
        test_year_rows = [row for row in rows if row["target_year"] == target_year]
        train_year_rows = [row for row in rows if row["target_year"] < target_year]
        if len(train_year_rows) >= MIN_TRAIN_ROWS:
            global_pred = fit_predict_common(train_year_rows, test_year_rows, ctx)
            predictions.extend(make_structure_rows("global_model", test_year_rows, global_pred))
        for sector in sorted({row["sector_code"] for row in test_year_rows}):
            train = [row for row in rows if row["sector_code"] == sector and row["target_year"] < target_year]
            test = [row for row in test_year_rows if row["sector_code"] == sector]
            if len(train) >= MIN_TRAIN_ROWS:
                predictions.extend(make_structure_rows("sector_model", test, fit_predict(train, test, ctx)))
        for group_name in sorted({sector_group(row["sector_code"]) for row in test_year_rows}):
            train = [row for row in rows if sector_group(row["sector_code"]) == group_name and row["target_year"] < target_year]
            test = [row for row in test_year_rows if sector_group(row["sector_code"]) == group_name]
            if len(train) >= MIN_TRAIN_ROWS:
                predictions.extend(make_structure_rows(f"sector_group_model:{group_name}", test, fit_predict(train, test, ctx)))
    return predictions, summarize(predictions, "model_structure")


def fit_predict(train_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]], ctx: dict[str, Any]) -> list[float]:
    x_train = build_matrix(train_rows, ctx)
    x_test = build_matrix(test_rows, ctx)
    raw = xgboost_predict(x_train, target_values(train_rows, "log_ratio"), x_test, PARAMS)
    return reconcile_group(test_rows, raw, "log_ratio")


def common_matrix(rows: list[dict[str, Any]], ctx: dict[str, Any]) -> np.ndarray:
    area_index = {area: idx for idx, area in enumerate(ctx["areas"])}
    sector_index = {sector: idx for idx, sector in enumerate(sorted({row["sector_code"] for row in ctx_rows(ctx)}))}
    method_index = {method: idx for idx, method in enumerate(ctx["methods"])}
    vectors: list[list[float]] = []
    for row in rows:
        hist_share = historical_values(row, ctx, "share", 3)
        hist_ratio = historical_values(row, ctx, "log_ratio", 3)
        latest_share = hist_share[0] if hist_share else row["baseline_share"]
        share_mean = mean(hist_share) if hist_share else latest_share
        share_std = float(np.std(hist_share)) if len(hist_share) > 1 else 0.0
        latest_ratio = hist_ratio[0] if hist_ratio else 0.0
        ratio_mean = mean(hist_ratio) if hist_ratio else 0.0
        ratio_std = float(np.std(hist_ratio)) if len(hist_ratio) > 1 else 0.0
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
        area_dummy[area_index[row["area_code"]]] = 1.0
        sector_dummy = [0.0] * len(sector_index)
        sector_dummy[sector_index[row["sector_code"]]] = 1.0
        method_dummy = [0.0] * len(method_index)
        method_dummy[method_index[row["method"]]] = 1.0
        vectors.append(base + structural_features(row, ctx) + area_dummy + sector_dummy + method_dummy)
    return np.asarray(vectors, dtype=float)


def ctx_rows(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for area, sector, year in ctx["actual_by_key"]:
        rows.append({"area_code": area, "sector_code": sector, "target_year": year})
    return rows


def fit_predict_common(train_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]], ctx: dict[str, Any]) -> list[float]:
    x_train = common_matrix(train_rows, ctx)
    x_test = common_matrix(test_rows, ctx)
    raw = xgboost_predict(x_train, target_values(train_rows, "log_ratio"), x_test, PARAMS)
    return reconcile_group(test_rows, raw, "log_ratio")


def make_structure_rows(model: str, test_rows: list[dict[str, Any]], predictions: list[float]) -> list[dict[str, Any]]:
    out = []
    for row, value in zip(test_rows, predictions):
        out.append(
            {
                "model_structure": model,
                "target_year": row["target_year"],
                "sector_code": row["sector_code"],
                "sector_name": row["sector_name"],
                "area_code": row["area_code"],
                "area_name": row["area_name"],
                "actual_annual_gva": round(row["actual"], 6),
                "baseline_prediction": round(row["baseline"], 6),
                "prediction": round(value, 6),
            }
        )
    return out


def summarize(predictions: list[dict[str, Any]], group_field: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for (name,), items in sorted(grouped(predictions, [group_field]).items()):
        normalized = [
            {
                **row,
                "actual": parse_number(row["actual_annual_gva"]),
                "baseline": parse_number(row["baseline_prediction"]),
                "prediction": parse_number(row["prediction"]),
            }
            for row in items
        ]
        base = wmape(normalized, "baseline")
        current = wmape(normalized, "prediction")
        sector_year = [improvement(wmape(part, "baseline"), wmape(part, "prediction")) for part in grouped(normalized, ["sector_code", "target_year"]).values()]
        out.append(
            {
                group_field: name,
                "count": len(items),
                "wmape": round(current, 6),
                "mape": round(mape(normalized, "prediction"), 6),
                "improvement_vs_baseline_pct": round(improvement(base, current), 6),
                "degraded_sector_year_count": sum(1 for value in sector_year if value < 0),
                "materially_degraded_sector_year_count": sum(1 for value in sector_year if value < -2),
                "worst_sector_year_improvement": round(min(sector_year), 6) if sector_year else "",
                "median_sector_year_improvement": round(median(sector_year), 6) if sector_year else "",
            }
        )
    return out


def write_table(lines: list[str], rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> None:
    lines.append("| " + " | ".join(label for label, _key in columns) + " |")
    lines.append("| " + " | ".join("---" if label in {"variant", "structure"} else "---:" for label, _key in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")) for _label, key in columns) + " |")


def write_reports(ablation_summary: list[dict[str, Any]], structure_summary: list[dict[str, Any]]) -> None:
    reports = ROOT / "reports"
    lines = [
        "# Reconciled Feature Ablation",
        "",
        "- 대상: XGBoost log-ratio residual, rolling target-year backtest",
        "- 튜닝 비용을 통제하기 위해 고정 파라미터를 사용했다. 따라서 기존 full-grid tuned 결과와 절대값을 직접 동일시하지 않고, feature group 간 상대 비교로 해석한다.",
        "",
        "## Feature Variant 비교",
        "",
    ]
    write_table(lines, ablation_summary, [("variant", "variant"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("improvement %", "improvement_vs_baseline_pct"), ("degraded", "degraded_sector_year_count"), ("material degraded", "materially_degraded_sector_year_count"), ("worst", "worst_sector_year_improvement")])
    lines.extend(["", "## 해석", "", "`drop_*`는 해당 feature group 제거 후 성능이다. `core_*`는 baseline/share와 지정 feature만 사용한 축약 모델이다. residual feature 제거와 structural-only 결과를 함께 보아 XGBoost 개선이 단순 잔차 복사인지 확인한다."])
    (reports / "reconciled_feature_ablation.md").write_text("\n".join(lines), encoding="utf-8")

    lines = [
        "# 산업별 모델 구조 비교",
        "",
        "- 대상: XGBoost log-ratio residual, rolling target-year backtest",
        "- 같은 고정 파라미터로 global, sector, 사전 산업군 모델을 비교했다.",
        "",
        "## 구조별 성능",
        "",
    ]
    write_table(lines, structure_summary, [("structure", "model_structure"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("improvement %", "improvement_vs_baseline_pct"), ("degraded", "degraded_sector_year_count"), ("material degraded", "materially_degraded_sector_year_count"), ("worst", "worst_sector_year_improvement")])
    lines.extend(["", "## 해석", "", "표본 수가 작은 산업에서는 sector model의 분산이 커질 수 있으므로, global 또는 사전 산업군 모델이 downside를 줄이는지 함께 확인해야 한다."])
    (reports / "sector_model_structure.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ablation_predictions, ablation_summary = run_ablation()
    structure_predictions, structure_summary = run_structure()
    write_csv(PROCESSED_DIR / "reconciled_feature_ablation_predictions.csv", ablation_predictions)
    write_csv(PROCESSED_DIR / "reconciled_feature_ablation_summary.csv", ablation_summary)
    write_csv(PROCESSED_DIR / "sector_model_structure_predictions.csv", structure_predictions)
    write_csv(PROCESSED_DIR / "sector_model_structure_summary.csv", structure_summary)
    write_reports(ablation_summary, structure_summary)
    print(f"ablation predictions: {len(ablation_predictions)}")
    print(f"structure predictions: {len(structure_predictions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
