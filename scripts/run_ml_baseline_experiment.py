from __future__ import annotations

from collections import defaultdict
from math import exp, log
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv


REPORT_PATH = ROOT / "reports" / "ml_baseline_experiment.md"
RIDGE_ALPHA = 5.0
MIN_TRAIN_ROWS = 300
TREE_MAX_DEPTH = 3
TREE_MIN_LEAF = 25
BOOSTING_ROUNDS = 25
BOOSTING_LEARNING_RATE = 0.08


def load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv"):
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
                "method": row.get("method", ""),
                "year": int(year),
                "baseline": predicted,
                "actual": actual,
            }
        )
    return rows


def categories(rows: list[dict[str, Any]], key: str) -> list[str]:
    return sorted({str(row[key]) for row in rows})


def design_matrix(
    rows: list[dict[str, Any]],
    *,
    area_codes: list[str],
    sector_codes: list[str],
    methods: list[str],
) -> np.ndarray:
    area_index = {value: idx for idx, value in enumerate(area_codes)}
    sector_index = {value: idx for idx, value in enumerate(sector_codes)}
    method_index = {value: idx for idx, value in enumerate(methods)}
    width = 4 + len(area_codes) + len(sector_codes) + len(methods)
    x = np.zeros((len(rows), width), dtype=float)
    for i, row in enumerate(rows):
        baseline = float(row["baseline"])
        year = float(row["year"])
        x[i, 0] = 1.0
        x[i, 1] = log(baseline)
        x[i, 2] = (year - 2020.0) / 10.0
        x[i, 3] = log(baseline) * ((year - 2020.0) / 10.0)
        area = area_index.get(str(row["area_code"]))
        sector = sector_index.get(str(row["sector_code"]))
        method = method_index.get(str(row["method"]))
        if area is not None:
            x[i, 4 + area] = 1.0
        if sector is not None:
            x[i, 4 + len(area_codes) + sector] = 1.0
        if method is not None:
            x[i, 4 + len(area_codes) + len(sector_codes) + method] = 1.0
    return x


def ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    penalty = np.eye(x.shape[1]) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.pinv(x.T @ x + penalty) @ x.T @ y


class RegressionTree:
    def __init__(self, max_depth: int = TREE_MAX_DEPTH, min_leaf: int = TREE_MIN_LEAF) -> None:
        self.max_depth = max_depth
        self.min_leaf = min_leaf
        self.root: dict[str, Any] | None = None

    def fit(self, x: np.ndarray, y: np.ndarray) -> "RegressionTree":
        self.root = self._build(x, y, depth=0)
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.root is None:
            raise RuntimeError("tree is not fitted")
        return np.array([self._predict_one(row, self.root) for row in x], dtype=float)

    def _predict_one(self, row: np.ndarray, node: dict[str, Any]) -> float:
        if "value" in node:
            return float(node["value"])
        if row[int(node["feature"])] <= float(node["threshold"]):
            return self._predict_one(row, node["left"])
        return self._predict_one(row, node["right"])

    def _build(self, x: np.ndarray, y: np.ndarray, depth: int) -> dict[str, Any]:
        if depth >= self.max_depth or len(y) < self.min_leaf * 2:
            return {"value": float(np.mean(y))}
        split = self._best_split(x, y)
        if split is None:
            return {"value": float(np.mean(y))}
        feature, threshold, left_mask = split
        return {
            "feature": int(feature),
            "threshold": float(threshold),
            "left": self._build(x[left_mask], y[left_mask], depth + 1),
            "right": self._build(x[~left_mask], y[~left_mask], depth + 1),
        }

    def _thresholds(self, values: np.ndarray) -> list[float]:
        unique = np.unique(values)
        if len(unique) <= 1:
            return []
        if set(unique.tolist()).issubset({0.0, 1.0}):
            return [0.5]
        quantiles = np.quantile(values, [0.2, 0.4, 0.6, 0.8])
        return sorted({float(value) for value in quantiles if np.min(values) < value < np.max(values)})

    def _best_split(self, x: np.ndarray, y: np.ndarray) -> tuple[int, float, np.ndarray] | None:
        base_error = float(np.sum((y - np.mean(y)) ** 2))
        best_gain = 0.0
        best: tuple[int, float, np.ndarray] | None = None
        for feature in range(x.shape[1]):
            values = x[:, feature]
            for threshold in self._thresholds(values):
                left = values <= threshold
                left_count = int(np.sum(left))
                right_count = len(y) - left_count
                if left_count < self.min_leaf or right_count < self.min_leaf:
                    continue
                left_error = float(np.sum((y[left] - np.mean(y[left])) ** 2))
                right_error = float(np.sum((y[~left] - np.mean(y[~left])) ** 2))
                gain = base_error - left_error - right_error
                if gain > best_gain:
                    best_gain = gain
                    best = (feature, threshold, left)
        return best


class GradientBoostedTrees:
    def __init__(self, rounds: int = BOOSTING_ROUNDS, learning_rate: float = BOOSTING_LEARNING_RATE) -> None:
        self.rounds = rounds
        self.learning_rate = learning_rate
        self.base = 0.0
        self.trees: list[RegressionTree] = []

    def fit(self, x: np.ndarray, y: np.ndarray) -> "GradientBoostedTrees":
        self.base = float(np.mean(y))
        pred = np.full(len(y), self.base, dtype=float)
        self.trees = []
        for _ in range(self.rounds):
            residual = y - pred
            tree = RegressionTree(max_depth=2, min_leaf=TREE_MIN_LEAF).fit(x, residual)
            update = tree.predict(x)
            pred += self.learning_rate * update
            self.trees.append(tree)
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        pred = np.full(x.shape[0], self.base, dtype=float)
        for tree in self.trees:
            pred += self.learning_rate * tree.predict(x)
        return pred


def metrics(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    errors = []
    abs_actual = 0.0
    abs_error = 0.0
    for row in rows:
        pred = parse_number(row.get(field))
        actual = parse_number(row.get("actual"))
        if pred is None or actual is None or actual == 0:
            continue
        error = pred - actual
        errors.append(abs(error / actual) * 100.0)
        abs_actual += abs(actual)
        abs_error += abs(error)
    return {
        "comparison_count": len(errors),
        "mape": round(sum(errors) / len(errors), 6) if errors else "",
        "wmape": round(abs_error / abs_actual * 100.0, 6) if abs_actual else "",
    }


def run_backtest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    years = sorted({row["year"] for row in rows})
    area_codes = categories(rows, "area_code")
    sector_codes = categories(rows, "sector_code")
    methods = categories(rows, "method")
    for target_year in years:
        train = [row for row in rows if row["year"] < target_year]
        test = [row for row in rows if row["year"] == target_year]
        if len(train) < MIN_TRAIN_ROWS or not test:
            continue
        x_train = design_matrix(train, area_codes=area_codes, sector_codes=sector_codes, methods=methods)
        x_test = design_matrix(test, area_codes=area_codes, sector_codes=sector_codes, methods=methods)
        y_train_log_actual = np.array([log(float(row["actual"])) for row in train])
        y_train_log_ratio = np.array([log(float(row["actual"]) / float(row["baseline"])) for row in train])
        beta_level = ridge_fit(x_train, y_train_log_actual, RIDGE_ALPHA)
        beta_ratio = ridge_fit(x_train, y_train_log_ratio, RIDGE_ALPHA)
        tree_ratio_model = RegressionTree().fit(x_train, y_train_log_ratio)
        boosted_ratio_model = GradientBoostedTrees().fit(x_train, y_train_log_ratio)
        pred_level = x_test @ beta_level
        pred_ratio = x_test @ beta_ratio
        pred_tree_ratio = tree_ratio_model.predict(x_test)
        pred_boosted_ratio = boosted_ratio_model.predict(x_test)
        for row, log_level, log_ratio, tree_ratio, boosted_ratio in zip(test, pred_level, pred_ratio, pred_tree_ratio, pred_boosted_ratio):
            ridge_level = exp(float(log_level))
            residual_corrected = float(row["baseline"]) * exp(float(log_ratio))
            tree_corrected = float(row["baseline"]) * exp(float(tree_ratio))
            boosted_corrected = float(row["baseline"]) * exp(float(boosted_ratio))
            out.append(
                {
                    **row,
                    "baseline_prediction": round(float(row["baseline"]), 6),
                    "ridge_log_level_prediction": round(ridge_level, 6),
                    "ridge_residual_prediction": round(residual_corrected, 6),
                    "tree_residual_prediction": round(tree_corrected, 6),
                    "boosted_tree_residual_prediction": round(boosted_corrected, 6),
                    "baseline_percent_error": round((float(row["baseline"]) - float(row["actual"])) / float(row["actual"]) * 100.0, 12),
                    "ridge_level_percent_error": round((ridge_level - float(row["actual"])) / float(row["actual"]) * 100.0, 12),
                    "ridge_residual_percent_error": round((residual_corrected - float(row["actual"])) / float(row["actual"]) * 100.0, 12),
                    "tree_residual_percent_error": round((tree_corrected - float(row["actual"])) / float(row["actual"]) * 100.0, 12),
                    "boosted_tree_residual_percent_error": round((boosted_corrected - float(row["actual"])) / float(row["actual"]) * 100.0, 12),
                    "train_rows": len(train),
                    "ridge_alpha": RIDGE_ALPHA,
                    "tree_max_depth": TREE_MAX_DEPTH,
                    "tree_min_leaf": TREE_MIN_LEAF,
                    "boosting_rounds": BOOSTING_ROUNDS,
                    "boosting_learning_rate": BOOSTING_LEARNING_RATE,
                    "model_note": "rolling expanding-window models using only pre-target official actuals; features are log baseline, year, area, sector, method dummies",
                }
            )
    return out


def summarize(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    specs = [
        ("baseline_prediction", "Denton/indicator baseline"),
        ("ridge_log_level_prediction", "Ridge log-level"),
        ("ridge_residual_prediction", "Ridge residual correction"),
        ("tree_residual_prediction", "Tree residual correction"),
        ("boosted_tree_residual_prediction", "Boosted tree residual correction"),
    ]
    out = []
    for field, label in specs:
        item = metrics(predictions, field)
        out.append({"model": label, "prediction_field": field, **item})
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in predictions:
        by_year[int(row["year"])].append(row)
    for year, rows in sorted(by_year.items()):
        for field, label in specs:
            item = metrics(rows, field)
            out.append({"model": label, "prediction_field": field, "target_year": year, **item})
    return out


def write_report(summary: list[dict[str, Any]]) -> None:
    overall = [row for row in summary if not row.get("target_year")]
    best = min(overall, key=lambda row: parse_number(row.get("wmape")) or 999999)
    lines = [
        "# ML Baseline 실험",
        "",
        "## 목적",
        "",
        "시도 대분류 official actual 구간에서 기존 Denton/indicator baseline 대비 ML 보정이 실제로 개선되는지 확인했다. 현재 환경에서는 `scikit-learn`이 아키텍처 문제로 사용할 수 없어, `numpy` 기반 Ridge와 작은 회귀트리/부스팅을 직접 구현했다.",
        "",
        "## 모델",
        "",
        "- Baseline: 기존 rolling annual prediction",
        "- Ridge log-level: `log(actual)`을 직접 예측",
        "- Ridge residual correction: `log(actual / baseline)`을 예측한 뒤 baseline에 곱해 보정",
        "- Tree residual correction: 회귀트리로 `log(actual / baseline)` 보정",
        "- Boosted tree residual correction: 작은 회귀트리를 순차적으로 더해 residual 보정",
        "",
        "모든 모델은 target year 이전의 official actual만 학습한다. target year 또는 그 이후의 값은 학습에 들어가지 않으므로 데이터 유출을 피한다.",
        "",
        "## 전체 성능",
        "",
        "| model | comparison_count | MAPE | WMAPE |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in overall:
        lines.append(f"| {row['model']} | {row['comparison_count']} | {row['mape']} | {row['wmape']} |")
    lines.extend(
        [
            "",
            f"가장 낮은 WMAPE 모델은 `{best['model']}`이다.",
            "",
            "## 해석",
            "",
            "이 실험은 최종 산출값을 대체하기 위한 것이 아니라, ML 보정이 baseline의 체계적 오차를 줄일 수 있는지 보는 진단이다. 다음 단계에서는 시군구·상세산업에 바로 level 예측을 적용하기보다, 상위 총량 정합성을 유지하는 residual correction 또는 share correction으로 제한하는 것이 안전하다.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows = load_rows()
    predictions = run_backtest(rows)
    summary = summarize(predictions)
    write_csv(PROCESSED_DIR / "ml_baseline_predictions.csv", predictions)
    write_csv(PROCESSED_DIR / "ml_baseline_model_comparison.csv", summary)
    write_report(summary)
    print(f"ml predictions: {len(predictions)}")
    print(f"ml summary rows: {len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
