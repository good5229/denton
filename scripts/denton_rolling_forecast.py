from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from denton_all_industries import (
    SECTOR_NAMES,
    average_indicator,
    national_gdp_indicators,
    production_indicators,
    service_indicators,
)
from denton_reci import extrapolate_last_bi, parse_quarter, proportional_denton, quarter_label
from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


ROLLING_PREFIX = "rolling_"


def strip_rolling_dataset(row: dict[str, str]) -> dict[str, str]:
    copied = dict(row)
    dataset = copied.get("dataset", "")
    if dataset.startswith(ROLLING_PREFIX):
        copied["dataset"] = dataset[len(ROLLING_PREFIX) :]
    return copied


def load_rolling_rows() -> list[dict[str, str]]:
    return [strip_rolling_dataset(row) for row in read_csv(PROCESSED_DIR / "rolling_kosis_collected_all.csv")]


def load_annual(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[int, float]]:
    annual: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    for row in rows:
        if row.get("dataset") != "annual_grva_real":
            continue
        sector = row.get("c2_id", "")
        if sector not in SECTOR_NAMES:
            continue
        value = parse_number(row.get("value"))
        if value is None or value <= 0:
            continue
        annual[(row.get("c1_id", ""), sector)][int(row["prd_de"])] = value
    return annual


def all_quarters(start_year: int, end_year: int) -> list[tuple[int, int]]:
    return [(year, quarter) for year in range(start_year, end_year + 1) for quarter in range(1, 5)]


def rolling_construction_indicator(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[tuple[int, int], float]]:
    orders: dict[tuple[str, str], dict[tuple[int, int], float]] = defaultdict(dict)
    for row in rows:
        if row.get("dataset") != "construction_orders_by_region_type":
            continue
        kind = row.get("c2_id", "")
        if kind not in {"1", "2"}:
            continue
        value = parse_number(row.get("value"))
        if value is None:
            continue
        orders[(row.get("c1_id", ""), kind)][parse_quarter(row["prd_de"])] = value

    observed = sorted({quarter for series in orders.values() for quarter in series})
    if not observed:
        return {}
    quarter_axis = all_quarters(observed[0][0], observed[-1][0])
    out: dict[tuple[str, str], dict[tuple[int, int], float]] = defaultdict(dict)
    for area in {area for area, _ in orders}:
        for quarter in quarter_axis:
            if quarter not in observed:
                continue
            idx = quarter_axis.index(quarter)
            building_window = quarter_axis[max(0, idx - 11) : idx + 1]
            civil_window = quarter_axis[max(0, idx - 23) : idx + 1]
            building = sum(orders.get((area, "1"), {}).get(q, 0.0) / 12.0 for q in building_window)
            civil = sum(orders.get((area, "2"), {}).get(q, 0.0) / 24.0 for q in civil_window)
            indicator = building + civil
            if indicator > 0:
                out[(area, "F00")][quarter] = indicator
    return out


def merge_indicators(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[tuple[int, int], float]], dict[tuple[str, str], str]]:
    merged: dict[tuple[str, str], dict[tuple[int, int], float]] = {}
    methods: dict[tuple[str, str], str] = {}
    for source, method in [
        (production_indicators(rows), "regional production index"),
        (service_indicators(rows), "regional service production index"),
        (rolling_construction_indicator(rows), "construction orders distributed 12/24 quarters"),
    ]:
        for key, series in source.items():
            merged[key] = series
            methods[key] = method
    national = national_gdp_indicators(rows)
    for sector, series in national.items():
        for area in {area for area, _ in merged} | {area for area, _ in load_annual(rows)}:
            key = (area, sector)
            if key not in merged:
                merged[key] = dict(series)
                methods[key] = "national quarterly GDP share"
    return merged, methods


def available_full_years(indicator: dict[tuple[int, int], float]) -> list[int]:
    years = sorted({year for year, _ in indicator})
    return [year for year in years if all((year, q) in indicator for q in range(1, 5))]


def estimate() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_rolling_rows()
    annual = load_annual(rows)
    indicators, methods = merge_indicators(rows)
    predictions: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for key, annual_by_year in sorted(annual.items()):
        area, sector = key
        indicator = indicators.get(key)
        if not indicator:
            skipped.append({"area_code": area, "sector_code": sector, "target_year": "", "reason": "missing indicator"})
            continue
        indicator_years = available_full_years(indicator)
        for target_year in indicator_years:
            train_years = [year for year in sorted(annual_by_year) if year < target_year]
            if len(train_years) < 2:
                continue
            if train_years != list(range(train_years[0], train_years[-1] + 1)):
                train_years = list(range(max(train_years) - len(train_years) + 1, max(train_years) + 1))
                if not all(year in annual_by_year for year in train_years):
                    continue
            try:
                train_indicator = [
                    indicator[(year, quarter)]
                    for year in train_years
                    for quarter in range(1, 5)
                ]
                target_indicator = [indicator[(target_year, quarter)] for quarter in range(1, 5)]
                fitted_train = proportional_denton(train_indicator, [annual_by_year[year] for year in train_years])
                extrapolated = extrapolate_last_bi(target_indicator, float(fitted_train[-1]), train_indicator[-1])
            except Exception as exc:
                skipped.append({"area_code": area, "sector_code": sector, "target_year": target_year, "reason": str(exc)})
                continue
            target_sum = float(extrapolated.sum())
            actual = annual_by_year.get(target_year)
            for idx, quarter in enumerate(range(1, 5)):
                predictions.append(
                    {
                        "area_code": area,
                        "sector_code": sector,
                        "sector_name": SECTOR_NAMES.get(sector, sector),
                        "target_year": target_year,
                        "quarter": quarter,
                        "period": quarter_label(target_year, quarter),
                        "train_start_year": train_years[0],
                        "train_end_year": train_years[-1],
                        "method": methods.get(key, ""),
                        "indicator": round(float(target_indicator[idx]), 6),
                        "predicted_gva": round(float(extrapolated[idx]), 6),
                        "actual_annual_gva_available": actual is not None,
                    }
                )
            comparison = {
                "area_code": area,
                "sector_code": sector,
                "sector_name": SECTOR_NAMES.get(sector, sector),
                "target_year": target_year,
                "train_start_year": train_years[0],
                "train_end_year": train_years[-1],
                "method": methods.get(key, ""),
                "predicted_annual_gva": round(target_sum, 6),
                "actual_annual_gva": round(actual, 6) if actual is not None else "",
                "error": "",
                "percent_error": "",
                "absolute_percent_error": "",
            }
            if actual:
                error = target_sum - actual
                pct = error / actual * 100.0
                comparison.update(
                    {
                        "error": round(error, 6),
                        "percent_error": round(pct, 6),
                        "absolute_percent_error": round(abs(pct), 6),
                    }
                )
            comparisons.append(comparison)
    return predictions, comparisons, skipped


def main() -> int:
    predictions, comparisons, skipped = estimate()
    write_csv(PROCESSED_DIR / "rolling_quarterly_gva_predictions.csv", predictions)
    write_csv(PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv", comparisons)
    write_csv(PROCESSED_DIR / "rolling_prediction_skipped.csv", skipped)
    comparable = [row for row in comparisons if row.get("absolute_percent_error") != ""]
    mape = (
        sum(float(row["absolute_percent_error"]) for row in comparable) / len(comparable)
        if comparable
        else math.nan
    )
    write_csv(
        PROCESSED_DIR / "rolling_prediction_summary.csv",
        [
            {
                "quarterly_prediction_rows": len(predictions),
                "annual_comparison_rows": len(comparisons),
                "comparable_rows": len(comparable),
                "skipped": len(skipped),
                "mape": round(mape, 6),
            }
        ],
    )
    print(f"rolling quarterly predictions: {len(predictions)} rows")
    print(f"annual comparisons: {len(comparisons)} rows")
    print(f"comparable rows: {len(comparable)}")
    print(f"skipped: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
