from __future__ import annotations

import random
from collections import defaultdict
from statistics import mean, median
from typing import Any

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv


PREDICTIONS = PROCESSED_DIR / "reconciled_model_predictions.csv"
COMPARISON = PROCESSED_DIR / "reconciled_model_comparison.csv"
REPORT = ROOT / "reports" / "reconciled_model_stability_report.md"
MODEL = "xgboost_log_ratio_reconciled"
MODEL_FIELD = f"{MODEL}_prediction"
BOOTSTRAP_ITERATIONS = 1000
RANDOM_SEED = 20260716

CONFIG = {
    "min_average_improvement_pct": 2.0,
    "min_improved_year_ratio": 0.60,
    "min_recent_improved_years": 2,
    "max_single_year_degradation_pct": 10.0,
    "bootstrap_probability_threshold": 0.60,
}


def load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(PREDICTIONS):
        actual = parse_number(row.get("actual_annual_gva"))
        baseline = parse_number(row.get("baseline_prediction"))
        model = parse_number(row.get(MODEL_FIELD))
        if actual is None or baseline is None or model is None or actual <= 0:
            continue
        rows.append(
            {
                **row,
                "target_year": int(str(row["target_year"])),
                "actual": actual,
                "baseline": baseline,
                "model": model,
                "baseline_abs_error": abs(baseline - actual),
                "model_abs_error": abs(model - actual),
            }
        )
    return rows


def wmape(rows: list[dict[str, Any]], field: str) -> float:
    denominator = sum(abs(float(row["actual"])) for row in rows)
    if denominator == 0:
        return 0.0
    numerator = sum(abs(float(row[field]) - float(row["actual"])) for row in rows)
    return numerator / denominator * 100.0


def mape(rows: list[dict[str, Any]], field: str) -> float:
    values = [abs((float(row[field]) - float(row["actual"])) / float(row["actual"])) * 100.0 for row in rows if float(row["actual"]) != 0]
    return mean(values) if values else 0.0


def improvement_pct(baseline_wmape: float, model_wmape: float) -> float:
    if baseline_wmape == 0:
        return 0.0
    return (baseline_wmape - model_wmape) / baseline_wmape * 100.0


def summarize_group(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row[key]) for key in keys)].append(row)
    out: list[dict[str, Any]] = []
    for key, items in sorted(groups.items()):
        base = wmape(items, "baseline")
        model = wmape(items, "model")
        out.append(
            {
                **{field: value for field, value in zip(keys, key)},
                "n_obs": len(items),
                "actual_gva_sum": round(sum(float(row["actual"]) for row in items), 6),
                "baseline_wmape_pct": round(base, 6),
                "model_wmape_pct": round(model, 6),
                "improvement_pct": round(improvement_pct(base, model), 6),
                "baseline_mape_pct": round(mape(items, "baseline"), 6),
                "model_mape_pct": round(mape(items, "model"), 6),
                "baseline_absolute_error": round(sum(float(row["baseline_abs_error"]) for row in items), 6),
                "model_absolute_error": round(sum(float(row["model_abs_error"]) for row in items), 6),
                "absolute_error_reduction": round(
                    sum(float(row["baseline_abs_error"]) - float(row["model_abs_error"]) for row in items), 6
                ),
            }
        )
    return out


def leave_one_year_out(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    years = sorted({row["target_year"] for row in rows})
    for year in years:
        part = [row for row in rows if row["target_year"] != year]
        base = wmape(part, "baseline")
        model = wmape(part, "model")
        out.append(
            {
                "excluded_year": year,
                "n_obs": len(part),
                "baseline_wmape_pct": round(base, 6),
                "model_wmape_pct": round(model, 6),
                "improvement_pct": round(improvement_pct(base, model), 6),
            }
        )
    return out


def sector_year_matrix(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sector = summarize_group(rows, ["sector_code", "sector_name", "target_year"])
    years = sorted({str(row["target_year"]) for row in rows})
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in by_sector:
        key = (row["sector_code"], row["sector_name"])
        grouped.setdefault(key, {"sector_code": row["sector_code"], "sector_name": row["sector_name"]})
        grouped[key][f"improvement_{row['target_year']}"] = row["improvement_pct"]
        grouped[key][f"model_wmape_{row['target_year']}"] = row["model_wmape_pct"]
    out = []
    for key, item in sorted(grouped.items()):
        improved = [parse_number(item.get(f"improvement_{year}")) for year in years]
        improved_values = [value for value in improved if value is not None]
        recent_years = years[-2:]
        recent_improved = sum(1 for year in recent_years if (parse_number(item.get(f"improvement_{year}")) or 0) > 0)
        item["improved_year_count"] = sum(1 for value in improved_values if value > 0)
        item["evaluated_year_count"] = len(improved_values)
        item["improved_year_ratio"] = round(item["improved_year_count"] / len(improved_values), 6) if improved_values else ""
        item["recent_improved_years"] = recent_improved
        item["worst_year_degradation_pct"] = round(min(improved_values), 6) if improved_values else ""
        out.append(item)
    return out


def region_size_bucket(rows: list[dict[str, Any]]) -> dict[str, str]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[row["area_name"]] += float(row["actual"])
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    n = len(ordered)
    buckets: dict[str, str] = {}
    for idx, (region, _value) in enumerate(ordered):
        rank = (idx + 1) / n
        if rank <= 0.10:
            bucket = "top_10pct"
        elif rank <= 0.25:
            bucket = "top_10_25pct"
        elif rank <= 0.50:
            bucket = "middle_25_50pct"
        elif rank <= 0.75:
            bucket = "lower_50_75pct"
        else:
            bucket = "bottom_25pct"
        buckets[region] = bucket
    return buckets


def bootstrap(rows: list[dict[str, Any]], keys: list[str], label: str) -> dict[str, Any]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row[key]) for key in keys)].append(row)
    group_items = list(groups.values())
    rng = random.Random(RANDOM_SEED + len(keys))
    deltas = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        sampled: list[dict[str, Any]] = []
        for _idx in range(len(group_items)):
            sampled.extend(rng.choice(group_items))
        deltas.append(wmape(sampled, "baseline") - wmape(sampled, "model"))
    deltas.sort()
    low_idx = int(0.025 * (len(deltas) - 1))
    high_idx = int(0.975 * (len(deltas) - 1))
    return {
        "bootstrap_unit": label,
        "iterations": BOOTSTRAP_ITERATIONS,
        "mean_delta_wmape_pct": round(mean(deltas), 6),
        "median_delta_wmape_pct": round(median(deltas), 6),
        "ci95_low_delta_wmape_pct": round(deltas[low_idx], 6),
        "ci95_high_delta_wmape_pct": round(deltas[high_idx], 6),
        "probability_model_better": round(sum(1 for value in deltas if value > 0) / len(deltas), 6),
    }


def selection_rules(sector_summary: list[dict[str, Any]], matrix: list[dict[str, Any]], bootstrap_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bootstrap_prob = {row["sector_code"]: parse_number(row.get("probability_model_better")) for row in bootstrap_rows}
    matrix_by_sector = {row["sector_code"]: row for row in matrix}
    out = []
    for row in sector_summary:
        sector = row["sector_code"]
        detail = matrix_by_sector.get(sector, {})
        avg_improvement = float(row["improvement_pct"])
        improved_ratio = parse_number(detail.get("improved_year_ratio")) or 0.0
        recent = int(detail.get("recent_improved_years") or 0)
        worst = parse_number(detail.get("worst_year_degradation_pct")) or 0.0
        prob = bootstrap_prob.get(sector)
        conditions = {
            "avg": avg_improvement >= CONFIG["min_average_improvement_pct"],
            "ratio": improved_ratio >= CONFIG["min_improved_year_ratio"],
            "recent": recent >= CONFIG["min_recent_improved_years"],
            "worst": worst >= -CONFIG["max_single_year_degradation_pct"],
            "bootstrap": prob is not None and prob >= CONFIG["bootstrap_probability_threshold"],
        }
        passed = sum(1 for value in conditions.values() if value)
        if avg_improvement <= 0:
            grade = "D"
            selected = "baseline"
        elif passed == len(conditions):
            grade = "A"
            selected = MODEL
        elif conditions["avg"] and conditions["ratio"] and conditions["worst"]:
            grade = "B"
            selected = f"baseline_and_{MODEL}"
        else:
            grade = "C"
            selected = "baseline"
        reason = "; ".join(f"{key}={'pass' if value else 'fail'}" for key, value in conditions.items())
        out.append(
            {
                "sector_code": sector,
                "sector_name": row.get("sector_name", ""),
                "selected_model": selected,
                "confidence_grade": grade,
                "average_improvement_pct": round(avg_improvement, 6),
                "improved_year_ratio": round(improved_ratio, 6),
                "recent_year_improvement_count": recent,
                "worst_year_degradation_pct": round(worst, 6),
                "bootstrap_probability_better": round(prob, 6) if prob is not None else "",
                "selection_reason": reason,
            }
        )
    return out


def sector_bootstrap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for sector in sorted({row["sector_code"] for row in rows}):
        part = [row for row in rows if row["sector_code"] == sector]
        if not part:
            continue
        result = bootstrap(part, ["target_year"], "target_year_block")
        result["sector_code"] = sector
        result["sector_name"] = part[0]["sector_name"]
        out.append(result)
    return out


def report(
    overall: list[dict[str, Any]],
    yearly: list[dict[str, Any]],
    loo: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    region: list[dict[str, Any]],
    boot: list[dict[str, Any]],
    sector_selection: list[dict[str, Any]],
) -> None:
    all_row = overall[0]
    best_year = max(yearly, key=lambda row: float(row["improvement_pct"]))
    worst_year = min(yearly, key=lambda row: float(row["improvement_pct"]))
    improved_years = sum(1 for row in yearly if float(row["improvement_pct"]) > 0)
    lines = [
        "# Reconciled ML 후속 안정성 검증",
        "",
        "## 요약",
        "",
        f"- 평가 모델: `{MODEL}`",
        f"- 전체 baseline WMAPE: `{all_row['baseline_wmape_pct']}`%",
        f"- 전체 model WMAPE: `{all_row['model_wmape_pct']}`%",
        f"- 전체 개선율: `{all_row['improvement_pct']}`%",
        f"- 개선 연도 수: `{improved_years}/{len(yearly)}`",
        f"- 최대 개선 연도: `{best_year['target_year']}` ({best_year['improvement_pct']}%)",
        f"- 최대 악화 연도: `{worst_year['target_year']}` ({worst_year['improvement_pct']}%)",
        "",
        "## Bootstrap",
        "",
        "| unit | mean delta WMAPE | median | 95% low | 95% high | P(model better) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in boot:
        lines.append(
            f"| {row['bootstrap_unit']} | {row['mean_delta_wmape_pct']} | {row['median_delta_wmape_pct']} | {row['ci95_low_delta_wmape_pct']} | {row['ci95_high_delta_wmape_pct']} | {row['probability_model_better']} |"
        )
    lines.extend(
        [
            "",
            "## Leave-One-Year-Out",
            "",
            "| excluded year | baseline WMAPE | model WMAPE | improvement % |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in loo:
        lines.append(f"| {row['excluded_year']} | {row['baseline_wmape_pct']} | {row['model_wmape_pct']} | {row['improvement_pct']} |")
    lines.extend(
        [
            "",
            "## 산업별 채택 등급",
            "",
            "| sector | selected model | grade | avg improvement | improved year ratio | recent improved years | bootstrap P | reason |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in sector_selection:
        lines.append(
            f"| {row['sector_code']} | {row['selected_model']} | {row['confidence_grade']} | {row['average_improvement_pct']} | {row['improved_year_ratio']} | {row['recent_year_improvement_count']} | {row['bootstrap_probability_better']} | {row['selection_reason']} |"
        )
    lines.extend(
        [
            "",
            "## 해석",
            "",
            "전체 평균 개선만으로 ML을 전면 채택하지 않는다. 산업별 등급은 평균 개선율, 개선 연도 비율, 최근 연도 개선 지속성, 최악 연도 악화폭, bootstrap 안정성을 함께 본다. `A/B`가 아닌 산업은 기본 산출에서 baseline을 유지하고 ML은 참고값으로만 둔다.",
            "",
            "상세 표는 `data/processed/reconciled_model_*` 안정성 CSV에 저장된다.",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


REPORT = ROOT / "reports" / "reconciled_model_stability_report.md"


def main() -> int:
    rows = load_rows()
    overall = summarize_group(rows, [])
    yearly = summarize_group(rows, ["target_year"])
    sector = summarize_group(rows, ["sector_code", "sector_name"])
    region = summarize_group(rows, ["area_code", "area_name"])
    buckets = region_size_bucket(rows)
    for row in rows:
        row["size_bucket"] = buckets[row["area_name"]]
        row["capital_region"] = "capital" if row["area_name"] in {"서울특별시", "인천광역시", "경기도"} else "non_capital"
        row["region_type"] = "metro" if row["area_name"].endswith("광역시") or row["area_name"] in {"서울특별시", "세종특별자치시"} else "province"
    by_size = summarize_group(rows, ["size_bucket"])
    by_capital = summarize_group(rows, ["capital_region"])
    by_region_type = summarize_group(rows, ["region_type"])
    loo = leave_one_year_out(rows)
    matrix = sector_year_matrix(rows)
    boot = [
        bootstrap(rows, ["target_year", "sector_code"], "target_year_sector_parent"),
        bootstrap(rows, ["area_code"], "region"),
        bootstrap(rows, ["target_year"], "target_year_block"),
    ]
    sector_boot = sector_bootstrap(rows)
    selection = selection_rules(sector, matrix, sector_boot)
    write_csv(PROCESSED_DIR / "reconciled_model_stability_by_year.csv", yearly)
    write_csv(PROCESSED_DIR / "reconciled_model_stability_leave_one_year_out.csv", loo)
    write_csv(PROCESSED_DIR / "reconciled_model_stability_sector_year_matrix.csv", matrix)
    write_csv(PROCESSED_DIR / "reconciled_model_stability_by_region.csv", region)
    write_csv(PROCESSED_DIR / "reconciled_model_stability_by_size_bucket.csv", by_size)
    write_csv(PROCESSED_DIR / "reconciled_model_stability_by_capital_region.csv", by_capital)
    write_csv(PROCESSED_DIR / "reconciled_model_stability_by_region_type.csv", by_region_type)
    write_csv(PROCESSED_DIR / "reconciled_model_bootstrap.csv", boot)
    write_csv(PROCESSED_DIR / "reconciled_model_sector_bootstrap.csv", sector_boot)
    write_csv(PROCESSED_DIR / "reconciled_model_selection_rules.csv", selection)
    report(overall, yearly, loo, matrix, region, boot, selection)
    print(f"rows: {len(rows)}")
    print(f"yearly rows: {len(yearly)}")
    print(f"sector rows: {len(sector)}")
    print(f"selection rows: {len(selection)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
