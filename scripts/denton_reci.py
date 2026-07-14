from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


SECTOR_SPECS = [
    {
        "sector_code": "C00",
        "sector_name": "제조업",
        "indicator_dataset": "mining_manufacturing_production_index",
        "indicator_industry_codes": {"C"},
    },
    {
        "sector_code": "SER",
        "sector_name": "서비스업",
        "indicator_dataset": "service_production_index",
        "indicator_industry_codes": {"T"},
    },
]


def parse_quarter(period: str) -> tuple[int, int]:
    text = period.strip().replace(" ", "")
    for mark in ("Q", "q"):
        if mark in text:
            year, q = text.split(mark, 1)
            return int(year), int(q)
    if "/4" in text:
        year = int(text[:4])
        q = int(text[4:].split("/")[0].replace(".", "").replace("-", ""))
        return year, q
    if len(text) == 6 and text[4:].isdigit():
        quarter = int(text[4:])
        if 1 <= quarter <= 4:
            return int(text[:4]), quarter
    raise ValueError(f"Cannot parse quarter period: {period}")


def quarter_label(year: int, quarter: int) -> str:
    return f"{year}Q{quarter}"


def proportional_denton(indicator: list[float], annual: list[float]) -> np.ndarray:
    n = len(indicator)
    p = len(annual)
    if n != p * 4:
        raise ValueError("indicator length must equal annual length * 4")
    i = np.asarray(indicator, dtype=float)
    if np.any(i <= 0) or np.any(~np.isfinite(i)):
        raise ValueError("indicator values must be positive finite numbers")

    m = np.diag(1.0 / i)
    d = np.zeros((n - 1, n))
    for row in range(n - 1):
        d[row, row] = -1.0
        d[row, row + 1] = 1.0
    h = 2.0 * (m.T @ d.T @ d @ m)

    j = np.zeros((p, n))
    for year_idx in range(p):
        j[year_idx, year_idx * 4 : year_idx * 4 + 4] = 1.0

    lhs = np.block([[h, j.T], [j, np.zeros((p, p))]])
    rhs = np.concatenate([np.zeros(n), np.asarray(annual, dtype=float)])
    try:
        solution = np.linalg.solve(lhs, rhs)
    except np.linalg.LinAlgError:
        solution = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
    return solution[:n]


def extrapolate_last_bi(indicator: list[float], last_benchmarked: float, last_indicator: float) -> np.ndarray:
    ratio = last_benchmarked / last_indicator
    return np.asarray(indicator, dtype=float) * ratio


def load_annual_grva() -> dict[tuple[str, str], dict[int, float]]:
    rows = read_csv(PROCESSED_DIR / "annual_grva_real.csv")
    wanted = {spec["sector_code"] for spec in SECTOR_SPECS}
    series: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    for row in rows:
        value = parse_number(row.get("value"))
        if value is None:
            continue
        area = row.get("c1_id", "")
        sector = row.get("c2_id", "")
        if sector not in wanted:
            continue
        series[(area, sector)][int(row["prd_de"])] = value
    return series


def load_indicators() -> dict[tuple[str, str], dict[tuple[int, int], float]]:
    rows = read_csv(PROCESSED_DIR / "kosis_collected_all.csv")
    specs = {
        spec["indicator_dataset"]: spec
        for spec in SECTOR_SPECS
    }
    series: dict[tuple[str, str], dict[tuple[int, int], float]] = defaultdict(dict)
    for row in rows:
        spec = specs.get(row.get("dataset"))
        if not spec:
            continue
        industry = row.get("c2_id", "")
        if industry not in spec["indicator_industry_codes"]:
            continue
        value = parse_number(row.get("value"))
        if value is None or value <= 0:
            continue
        year, quarter = parse_quarter(row["prd_de"])
        series[(row.get("c1_id", ""), spec["sector_code"])][(year, quarter)] = value
    return series


def annual_sum(rows: list[dict[str, object]], year: int) -> float:
    return sum(float(row["estimated_gva"]) for row in rows if int(row["year"]) == year)


def main() -> int:
    annual = load_annual_grva()
    indicators = load_indicators()
    train_years = [2019, 2020, 2021, 2022]
    all_years = [2019, 2020, 2021, 2022, 2023]

    estimates: list[dict[str, object]] = []
    validation: list[dict[str, object]] = []

    sector_names = {spec["sector_code"]: spec["sector_name"] for spec in SECTOR_SPECS}

    for key, annual_by_year in sorted(annual.items()):
        area, sector = key
        indicator_by_q = indicators.get(key)
        if not indicator_by_q:
            continue
        if not all(year in annual_by_year for year in all_years):
            continue
        try:
            full_indicator = [
                indicator_by_q[(year, quarter)]
                for year in all_years
                for quarter in range(1, 5)
            ]
            train_indicator = [
                indicator_by_q[(year, quarter)]
                for year in train_years
                for quarter in range(1, 5)
            ]
        except KeyError:
            continue

        full = proportional_denton(
            full_indicator,
            [annual_by_year[year] for year in all_years],
        )
        train = proportional_denton(
            train_indicator,
            [annual_by_year[year] for year in train_years],
        )
        extrapolated_2023 = extrapolate_last_bi(
            [indicator_by_q[(2023, quarter)] for quarter in range(1, 5)],
            float(train[-1]),
            train_indicator[-1],
        )
        estimated_2023 = float(extrapolated_2023.sum())
        actual_2023 = annual_by_year[2023]
        error = estimated_2023 - actual_2023
        pct_error = error / actual_2023 * 100.0 if actual_2023 else math.nan

        validation.append(
            {
                "area_code": area,
                "sector_code": sector,
                "sector_name": sector_names.get(sector, sector),
                "actual_2023": round(actual_2023, 6),
                "estimated_2023_extrapolated": round(estimated_2023, 6),
                "error": round(error, 6),
                "percent_error": round(pct_error, 6),
                "absolute_percent_error": round(abs(pct_error), 6),
            }
        )

        idx = 0
        for year in all_years:
            for quarter in range(1, 5):
                estimates.append(
                    {
                        "area_code": area,
                        "sector_code": sector,
                        "sector_name": sector_names.get(sector, sector),
                        "year": year,
                        "quarter": quarter,
                        "period": quarter_label(year, quarter),
                        "indicator": full_indicator[idx],
                        "estimated_gva": round(float(full[idx]), 6),
                        "benchmark_annual_gva": annual_by_year[year],
                    }
                )
                idx += 1

    write_csv(PROCESSED_DIR / "denton_quarterly_gva_estimates.csv", estimates)
    write_csv(PROCESSED_DIR / "denton_2023_extrapolation_errors.csv", validation)

    if validation:
        mae = sum(abs(float(row["error"])) for row in validation) / len(validation)
        mape = sum(float(row["absolute_percent_error"]) for row in validation) / len(validation)
    else:
        mae = math.nan
        mape = math.nan
    write_csv(
        PROCESSED_DIR / "denton_error_summary.csv",
        [{"n": len(validation), "mae": round(mae, 6), "mape": round(mape, 6)}],
    )
    print(f"quarterly estimates: {len(estimates)} rows")
    print(f"validation rows: {len(validation)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
