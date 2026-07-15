from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv


INPUT = PROCESSED_DIR / "reconciled_model_predictions.csv"
REPORT = ROOT / "reports" / "reconciled_model_safety_report.md"
MODEL = "xgboost_log_ratio_reconciled"
MODEL_FIELD = f"{MODEL}_prediction"
GRID = [round(value / 10, 1) for value in range(0, 11)]
MIN_TRAIN_YEARS = 2


def load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(INPUT):
        actual = parse_number(row.get("actual_annual_gva"))
        baseline = parse_number(row.get("baseline_prediction"))
        model = parse_number(row.get(MODEL_FIELD))
        parent_total = parse_number(row.get("parent_baseline_total"))
        if actual is None or baseline is None or model is None or parent_total is None:
            continue
        if actual <= 0 or baseline <= 0 or model <= 0 or parent_total <= 0:
            continue
        rows.append(
            {
                **row,
                "target_year": int(str(row["target_year"])),
                "actual": actual,
                "baseline": baseline,
                "model": model,
                "parent_total": parent_total,
            }
        )
    return rows


def raw_shrink(row: dict[str, Any], alpha: float) -> float:
    # Equivalent to baseline * exp(alpha * log(model / baseline)).
    return float(row["baseline"]) ** (1.0 - alpha) * float(row["model"]) ** alpha


def raw_blend(row: dict[str, Any], weight: float) -> float:
    return (1.0 - weight) * float(row["baseline"]) + weight * float(row["model"])


def reconcile(rows: list[dict[str, Any]], raw_values: list[float]) -> list[float]:
    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        groups[(int(row["target_year"]), row["sector_code"])].append(idx)
    out = [0.0] * len(rows)
    for indices in groups.values():
        parent_total = float(rows[indices[0]]["parent_total"])
        total = sum(max(raw_values[idx], 0.0) for idx in indices)
        if total <= 0:
            total = sum(float(rows[idx]["baseline"]) for idx in indices)
            raw = [float(rows[idx]["baseline"]) for idx in indices]
        else:
            raw = [max(raw_values[idx], 0.0) for idx in indices]
        for idx, value in zip(indices, raw):
            out[idx] = parent_total * value / total if total > 0 else parent_total / len(indices)
    return out


def wmape(rows: list[dict[str, Any]], predictions: list[float]) -> float:
    actual_sum = sum(abs(float(row["actual"])) for row in rows)
    if actual_sum == 0:
        return 0.0
    error_sum = sum(abs(pred - float(row["actual"])) for row, pred in zip(rows, predictions))
    return error_sum / actual_sum * 100.0


def score_candidate(rows: list[dict[str, Any]], mode: str, value: float) -> float:
    if mode == "shrink":
        raw = [raw_shrink(row, value) for row in rows]
    elif mode == "blend":
        raw = [raw_blend(row, value) for row in rows]
    else:
        raise ValueError(mode)
    return wmape(rows, reconcile(rows, raw))


def choose_value(train_rows: list[dict[str, Any]], mode: str) -> tuple[float, float]:
    best_value = 0.0
    best_score = float("inf")
    for value in GRID:
        score = score_candidate(train_rows, mode, value)
        if score < best_score:
            best_value = value
            best_score = score
    return best_value, best_score


def run() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_rows()
    predictions: list[dict[str, Any]] = []
    tuning: list[dict[str, Any]] = []
    for sector in sorted({row["sector_code"] for row in rows}):
        sector_rows = [row for row in rows if row["sector_code"] == sector]
        for target_year in sorted({row["target_year"] for row in sector_rows}):
            test_rows = [row for row in sector_rows if row["target_year"] == target_year]
            train_rows = [row for row in sector_rows if row["target_year"] < target_year]
            train_years = sorted({row["target_year"] for row in train_rows})
            if len(train_years) < MIN_TRAIN_YEARS:
                shrink_value, shrink_score = 0.0, score_candidate(test_rows, "shrink", 0.0)
                blend_value, blend_score = 0.0, score_candidate(test_rows, "blend", 0.0)
                fallback_reason = "insufficient_pre_target_years"
            else:
                shrink_value, shrink_score = choose_value(train_rows, "shrink")
                blend_value, blend_score = choose_value(train_rows, "blend")
                fallback_reason = ""
            shrink_pred = reconcile(test_rows, [raw_shrink(row, shrink_value) for row in test_rows])
            blend_pred = reconcile(test_rows, [raw_blend(row, blend_value) for row in test_rows])
            tuning.append(
                {
                    "sector_code": sector,
                    "sector_name": test_rows[0]["sector_name"] if test_rows else "",
                    "target_year": target_year,
                    "selected_shrink_alpha": shrink_value,
                    "selected_shrink_validation_wmape": round(shrink_score, 6),
                    "selected_blend_weight": blend_value,
                    "selected_blend_validation_wmape": round(blend_score, 6),
                    "train_years": ",".join(str(year) for year in train_years),
                    "fallback_reason": fallback_reason,
                }
            )
            for row, shrink, blend in zip(test_rows, shrink_pred, blend_pred):
                selected = shrink
                selected_mode = "shrink"
                if abs(blend - row["actual"]) < abs(shrink - row["actual"]):
                    # This column is diagnostic only; operational selection remains pre-target below.
                    diagnostic_best = "blend"
                else:
                    diagnostic_best = "shrink"
                if blend_score < shrink_score:
                    selected = blend
                    selected_mode = "blend"
                fallback_applied = selected_mode == "shrink" and shrink_value == 0.0 or selected_mode == "blend" and blend_value == 0.0
                predictions.append(
                    {
                        "area_code": row["area_code"],
                        "area_name": row["area_name"],
                        "sector_code": row["sector_code"],
                        "sector_name": row["sector_name"],
                        "target_year": row["target_year"],
                        "actual_annual_gva": round(float(row["actual"]), 6),
                        "baseline_prediction": round(float(row["baseline"]), 6),
                        "full_ml_prediction": round(float(row["model"]), 6),
                        "shrink_prediction": round(shrink, 6),
                        "blend_prediction": round(blend, 6),
                        "safe_selected_prediction": round(selected, 6),
                        "selected_mode": selected_mode,
                        "selected_shrink_alpha": shrink_value,
                        "selected_blend_weight": blend_value,
                        "diagnostic_best_mode_using_target_actual": diagnostic_best,
                        "fallback_applied": fallback_applied,
                        "fallback_reason": fallback_reason if fallback_applied else "",
                        "leakage_policy": "shrink/blend weights selected only from pre-target years; target actual used for evaluation only",
                    }
                )
    summary = summarize(predictions)
    return predictions, summary, tuning


def metric(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    actual_sum = sum(abs(float(row["actual_annual_gva"])) for row in rows)
    abs_error = sum(abs(float(row[field]) - float(row["actual_annual_gva"])) for row in rows)
    ape = [abs((float(row[field]) - float(row["actual_annual_gva"])) / float(row["actual_annual_gva"])) * 100.0 for row in rows]
    return {
        "comparison_count": len(rows),
        "mape_pct": round(mean(ape), 6) if ape else "",
        "wmape_pct": round(abs_error / actual_sum * 100.0, 6) if actual_sum else "",
    }


def summarize(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = {"__ALL__": predictions}
    for row in predictions:
        groups.setdefault(row["sector_code"], []).append(row)
    fields = [
        ("baseline_prediction", "baseline"),
        ("full_ml_prediction", "full_ml"),
        ("shrink_prediction", "shrink"),
        ("blend_prediction", "blend"),
        ("safe_selected_prediction", "safe_selected"),
    ]
    for sector, rows in sorted(groups.items()):
        baseline_wmape = metric(rows, "baseline_prediction")["wmape_pct"]
        for field, label in fields:
            item = metric(rows, field)
            current = parse_number(item["wmape_pct"])
            base = parse_number(baseline_wmape)
            out.append(
                {
                    "sector_code": sector,
                    "model": label,
                    **item,
                    "baseline_wmape_pct": baseline_wmape,
                    "improvement_pct": round((base - current) / base * 100.0, 6) if base and current is not None else "",
                }
            )
    return out


def report(summary: list[dict[str, Any]], tuning: list[dict[str, Any]]) -> None:
    lines = [
        "# Reconciled ML 안전장치 실험",
        "",
        "## 목적",
        "",
        "Full ML residual이 baseline보다 악화되는 산업·연도를 통제하기 위해, target year 이전 검증 구간만 사용해 residual shrinkage alpha와 linear blend weight를 선택했다.",
        "",
        "## 전체 성능",
        "",
        "| model | count | MAPE | WMAPE | improvement vs baseline % |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in [row for row in summary if row["sector_code"] == "__ALL__"]:
        lines.append(f"| {row['model']} | {row['comparison_count']} | {row['mape_pct']} | {row['wmape_pct']} | {row['improvement_pct']} |")
    lines.extend(
        [
            "",
            "## 산업별 safe_selected",
            "",
            "| sector | baseline WMAPE | safe WMAPE | improvement % |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in summary:
        if row["sector_code"] == "__ALL__" or row["model"] != "safe_selected":
            continue
        lines.append(f"| {row['sector_code']} | {row['baseline_wmape_pct']} | {row['wmape_pct']} | {row['improvement_pct']} |")
    alpha_counts: dict[str, int] = defaultdict(int)
    blend_counts: dict[str, int] = defaultdict(int)
    for row in tuning:
        alpha_counts[str(row["selected_shrink_alpha"])] += 1
        blend_counts[str(row["selected_blend_weight"])] += 1
    lines.extend(
        [
            "",
            "## 선택 강도 분포",
            "",
            f"- shrink alpha: {dict(sorted(alpha_counts.items()))}",
            f"- blend weight: {dict(sorted(blend_counts.items()))}",
            "",
            "## 해석",
            "",
            "`alpha=0` 또는 `weight=0`은 baseline fallback과 같다. 이 실험은 target actual을 사용해 안전장치를 고른 것이 아니라, 각 target year 이전 데이터에서만 강도를 선택했다.",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    predictions, summary, tuning = run()
    write_csv(PROCESSED_DIR / "reconciled_model_safe_predictions.csv", predictions)
    write_csv(PROCESSED_DIR / "reconciled_model_safe_comparison.csv", summary)
    write_csv(PROCESSED_DIR / "reconciled_model_safe_tuning.csv", tuning)
    report(summary, tuning)
    print(f"safe predictions: {len(predictions)}")
    print(f"summary rows: {len(summary)}")
    print(f"tuning rows: {len(tuning)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
