from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv
from denton_reci import parse_quarter, proportional_denton, extrapolate_last_bi, quarter_label


YEARS = [2019, 2020, 2021, 2022, 2023]
TRAIN_YEARS = [2019, 2020, 2021, 2022]
QUARTERS = [(year, quarter) for year in YEARS for quarter in range(1, 5)]


SECTOR_NAMES = {
    "A00": "농업, 임업 및 어업",
    "B00": "광업",
    "C00": "제조업",
    "D00": "전기, 가스, 증기 및 공기 조절 공급업",
    "F00": "건설업",
    "G00": "도매 및 소매업",
    "H00": "운수 및 창고업",
    "I00": "숙박 및 음식점업",
    "J00": "정보통신업",
    "K00": "금융 및 보험업",
    "L00": "부동산업",
    "MN0": "사업서비스업",
    "O00": "공공 행정, 국방 및 사회보장 행정",
    "P00": "교육 서비스업",
    "Q00": "보건업 및 사회복지 서비스업",
    "ERS": "문화 및 기타서비스업",
}

PRODUCTION_INDICATOR_MAP = {
    "B00": ("mining_production_index", {"B"}),
    "C00": ("mining_manufacturing_production_index", {"C"}),
    "D00": ("electricity_gas_production_index", {"D"}),
}

SERVICE_INDICATOR_MAP = {
    "G00": {"G"},
    "H00": {"H"},
    "I00": {"I"},
    "J00": {"J"},
    "K00": {"K"},
    "L00": {"L"},
    "MN0": {"M", "N"},
    "P00": {"P"},
    "Q00": {"Q"},
    "ERS": {"E", "R", "S"},
}

NATIONAL_GDP_CODE_MAP = {
    "A00": "13102136275ACC_ITEM.1101",
    "B00": "13102136275ACC_ITEM.1102",
    "C00": "13102136275ACC_ITEM.1103",
    "D00": "13102136275ACC_ITEM.1104",
    "F00": "13102136275ACC_ITEM.1105",
    "G00": "13102136275ACC_ITEM.1106",
    "H00": "13102136275ACC_ITEM.1107",
    "I00": "13102136275ACC_ITEM.1106",
    "J00": "13102136275ACC_ITEM.1114",
    "K00": "13102136275ACC_ITEM.1108",
    "L00": "13102136275ACC_ITEM.1109",
    "MN0": "13102136275ACC_ITEM.1115",
    "O00": "13102136275ACC_ITEM.1110",
    "P00": "13102136275ACC_ITEM.1111",
    "Q00": "13102136275ACC_ITEM.1112",
    "ERS": "13102136275ACC_ITEM.1113",
}

DEFLATOR_CODE_MAP = {
    "A00": "13102134503ACC_ITEM.1101",
    "B00": "13102134503ACC_ITEM.1102",
    "C00": "13102134503ACC_ITEM.1103",
    "D00": "13102134503ACC_ITEM.1104",
    "F00": "13102134503ACC_ITEM.1105",
    "G00": "13102134503ACC_ITEM.1106",
    "H00": "13102134503ACC_ITEM.1107",
    "I00": "13102134503ACC_ITEM.1106",
    "J00": "13102134503ACC_ITEM.1114",
    "K00": "13102134503ACC_ITEM.1108",
    "L00": "13102134503ACC_ITEM.1109",
    "MN0": "13102134503ACC_ITEM.1115",
    "O00": "13102134503ACC_ITEM.1110",
    "P00": "13102134503ACC_ITEM.1111",
    "Q00": "13102134503ACC_ITEM.1112",
    "ERS": "13102134503ACC_ITEM.1113",
}


def load_annual() -> dict[tuple[str, str], dict[int, float]]:
    series: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    for row in read_csv(PROCESSED_DIR / "annual_grva_real.csv"):
        sector = row.get("c2_id", "")
        if sector not in SECTOR_NAMES:
            continue
        value = parse_number(row.get("value"))
        if value is None:
            continue
        series[(row.get("c1_id", ""), sector)][int(row["prd_de"])] = value
    return series


def load_indicator_rows() -> list[dict[str, str]]:
    return read_csv(PROCESSED_DIR / "kosis_collected_all.csv")


def average_indicator(values: list[float]) -> float | None:
    values = [v for v in values if v > 0 and math.isfinite(v)]
    if not values:
        return None
    return sum(values) / len(values)


def production_indicators(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[tuple[int, int], float]]:
    out: dict[tuple[str, str], dict[tuple[int, int], float]] = defaultdict(dict)
    lookup = {(dataset, next(iter(codes))): sector for sector, (dataset, codes) in PRODUCTION_INDICATOR_MAP.items()}
    for row in rows:
        sector = lookup.get((row.get("dataset"), row.get("c2_id")))
        if not sector:
            continue
        value = parse_number(row.get("value"))
        if value is None or value <= 0:
            continue
        out[(row.get("c1_id", ""), sector)][parse_quarter(row["prd_de"])] = value
    return out


def service_indicators(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[tuple[int, int], float]]:
    bucket: dict[tuple[str, str, tuple[int, int]], list[float]] = defaultdict(list)
    code_to_sector: dict[str, str] = {}
    for sector, codes in SERVICE_INDICATOR_MAP.items():
        for code in codes:
            code_to_sector[code] = sector
    for row in rows:
        if row.get("dataset") != "service_production_index":
            continue
        sector = code_to_sector.get(row.get("c2_id", ""))
        if not sector:
            continue
        value = parse_number(row.get("value"))
        if value is None or value <= 0:
            continue
        bucket[(row.get("c1_id", ""), sector, parse_quarter(row["prd_de"]))].append(value)

    out: dict[tuple[str, str], dict[tuple[int, int], float]] = defaultdict(dict)
    for (area, sector, quarter), values in bucket.items():
        avg = average_indicator(values)
        if avg is not None:
            out[(area, sector)][quarter] = avg
    return out


def construction_indicator(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[tuple[int, int], float]]:
    orders: dict[tuple[str, str], dict[tuple[int, int], float]] = defaultdict(dict)
    for row in rows:
        if row.get("dataset") != "construction_orders_by_region_type":
            continue
        area = row.get("c1_id", "")
        kind = row.get("c2_id", "")
        if kind not in {"1", "2"}:
            continue
        value = parse_number(row.get("value"))
        if value is None:
            continue
        orders[(area, kind)][parse_quarter(row["prd_de"])] = value

    all_quarters = [(year, q) for year in range(2013, 2024) for q in range(1, 5)]
    out: dict[tuple[str, str], dict[tuple[int, int], float]] = defaultdict(dict)
    areas = {area for area, _ in orders}
    for area in areas:
        for quarter in QUARTERS:
            idx = all_quarters.index(quarter)
            building_window = all_quarters[max(0, idx - 11) : idx + 1]
            civil_window = all_quarters[max(0, idx - 23) : idx + 1]
            building = sum(orders.get((area, "1"), {}).get(q, 0.0) / 12.0 for q in building_window)
            civil = sum(orders.get((area, "2"), {}).get(q, 0.0) / 24.0 for q in civil_window)
            indicator = building + civil
            if indicator > 0:
                out[(area, "F00")][quarter] = indicator
    return out


def national_gdp_indicators(rows: list[dict[str, str]]) -> dict[str, dict[tuple[int, int], float]]:
    out: dict[str, dict[tuple[int, int], float]] = defaultdict(dict)
    code_to_sectors: dict[str, list[str]] = defaultdict(list)
    for sector, code in NATIONAL_GDP_CODE_MAP.items():
        code_to_sectors[code].append(sector)
    for row in rows:
        if row.get("dataset") != "national_quarterly_gdp_real":
            continue
        sectors = code_to_sectors.get(row.get("c1_id", ""), [])
        if not sectors:
            continue
        value = parse_number(row.get("value"))
        if value is None or value <= 0:
            continue
        for sector in sectors:
            out[sector][parse_quarter(row["prd_de"])] = value * 1000.0
    return out


def national_deflators(rows: list[dict[str, str]]) -> dict[str, dict[tuple[int, int], float]]:
    out: dict[str, dict[tuple[int, int], float]] = defaultdict(dict)
    code_to_sectors: dict[str, list[str]] = defaultdict(list)
    for sector, code in DEFLATOR_CODE_MAP.items():
        code_to_sectors[code].append(sector)
    for row in rows:
        if row.get("dataset") != "national_quarterly_gdp_deflator":
            continue
        sectors = code_to_sectors.get(row.get("c1_id", ""), [])
        value = parse_number(row.get("value"))
        if not sectors or value is None:
            continue
        for sector in sectors:
            out[sector][parse_quarter(row["prd_de"])] = value
    return out


def merge_indicators(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[tuple[int, int], float]], dict[tuple[str, str], str]]:
    merged: dict[tuple[str, str], dict[tuple[int, int], float]] = {}
    methods: dict[tuple[str, str], str] = {}
    for source, method in [
        (production_indicators(rows), "regional production index"),
        (service_indicators(rows), "regional service production index"),
        (construction_indicator(rows), "construction orders distributed 12/24 quarters"),
    ]:
        for key, series in source.items():
            merged[key] = series
            methods[key] = method
    national = national_gdp_indicators(rows)
    annual = load_annual()
    for area, sector in annual:
        key = (area, sector)
        if key in merged:
            continue
        if sector in national:
            merged[key] = dict(national[sector])
            methods[key] = "national quarterly GDP share"
    return merged, methods


def estimate() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    rows = load_indicator_rows()
    annual = load_annual()
    indicators, methods = merge_indicators(rows)
    deflators = national_deflators(rows)

    estimates: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for key, annual_by_year in sorted(annual.items()):
        area, sector = key
        if area in {"01", "02"}:
            continue
        if not all(year in annual_by_year for year in YEARS):
            continue
        indicator_by_q = indicators.get(key)
        if not indicator_by_q:
            skipped.append({"area_code": area, "sector_code": sector, "reason": "missing indicator"})
            continue
        try:
            full_indicator = [indicator_by_q[q] for q in QUARTERS]
            train_indicator = [
                indicator_by_q[(year, quarter)]
                for year in TRAIN_YEARS
                for quarter in range(1, 5)
            ]
        except KeyError as exc:
            national = national_gdp_indicators(rows).get(sector, {})
            for q in QUARTERS:
                indicator_by_q.setdefault(q, national.get(q))
            if any(indicator_by_q.get(q) is None for q in QUARTERS):
                skipped.append({"area_code": area, "sector_code": sector, "reason": f"missing quarter {exc}"})
                continue
            full_indicator = [float(indicator_by_q[q]) for q in QUARTERS]
            train_indicator = [
                float(indicator_by_q[(year, quarter)])
                for year in TRAIN_YEARS
                for quarter in range(1, 5)
            ]
        try:
            full = proportional_denton(full_indicator, [annual_by_year[y] for y in YEARS])
            train = proportional_denton(train_indicator, [annual_by_year[y] for y in TRAIN_YEARS])
        except Exception as exc:
            skipped.append({"area_code": area, "sector_code": sector, "reason": str(exc)})
            continue
        extrapolated = extrapolate_last_bi(
            [indicator_by_q[(2023, q)] for q in range(1, 5)],
            float(train[-1]),
            train_indicator[-1],
        )
        est_2023 = float(extrapolated.sum())
        actual_2023 = annual_by_year[2023]
        pct = (est_2023 - actual_2023) / actual_2023 * 100.0 if actual_2023 else math.nan
        errors.append(
            {
                "area_code": area,
                "sector_code": sector,
                "sector_name": SECTOR_NAMES[sector],
                "method": methods.get(key, ""),
                "actual_2023": round(actual_2023, 6),
                "estimated_2023_extrapolated": round(est_2023, 6),
                "error": round(est_2023 - actual_2023, 6),
                "percent_error": round(pct, 6),
                "absolute_percent_error": round(abs(pct), 6),
            }
        )
        for idx, (year, quarter) in enumerate(QUARTERS):
            estimates.append(
                {
                    "area_code": area,
                    "sector_code": sector,
                    "sector_name": SECTOR_NAMES[sector],
                    "year": year,
                    "quarter": quarter,
                    "period": quarter_label(year, quarter),
                    "method": methods.get(key, ""),
                    "indicator": round(float(full_indicator[idx]), 6),
                    "estimated_gva": round(float(full[idx]), 6),
                    "benchmark_annual_gva": annual_by_year[year],
                    "national_gdp_deflator": deflators.get(sector, {}).get((year, quarter)),
                }
            )
    apply_national_benchmark(estimates, national_gdp_indicators(rows))
    return estimates, errors, skipped


def apply_national_benchmark(
    estimates: list[dict[str, object]],
    national: dict[str, dict[tuple[int, int], float]],
) -> None:
    code_counts = defaultdict(int)
    for code in NATIONAL_GDP_CODE_MAP.values():
        code_counts[code] += 1
    ambiguous = {
        sector
        for sector, code in NATIONAL_GDP_CODE_MAP.items()
        if code_counts[code] > 1
    }

    groups: dict[tuple[str, int, int], list[dict[str, object]]] = defaultdict(list)
    for row in estimates:
        groups[(str(row["sector_code"]), int(row["year"]), int(row["quarter"]))].append(row)

    for (sector, year, quarter), rows in groups.items():
        national_value = national.get(sector, {}).get((year, quarter))
        regional_rows = [row for row in rows if row["area_code"] != "00"]
        total = sum(float(row["estimated_gva"]) for row in regional_rows)
        if sector in ambiguous:
            reason = "not applied: national GDP code combines multiple GRDP sectors"
            factor = ""
        elif national_value is None:
            reason = "not applied: missing national GDP benchmark"
            factor = ""
        elif total <= 0:
            reason = "not applied: non-positive regional sum"
            factor = ""
        else:
            reason = "applied"
            factor = national_value / total

        for row in rows:
            row["national_gdp_benchmark"] = national_value
            row["gdp_benchmark_factor"] = factor
            row["gdp_benchmark_status"] = reason
            if row["area_code"] == "00":
                row["gdp_benchmarked_gva"] = row["estimated_gva"]
            elif isinstance(factor, float):
                row["gdp_benchmarked_gva"] = round(float(row["estimated_gva"]) * factor, 6)
            else:
                row["gdp_benchmarked_gva"] = row["estimated_gva"]


def main() -> int:
    estimates, errors, skipped = estimate()
    write_csv(PROCESSED_DIR / "all_industries_quarterly_gva_estimates.csv", estimates)
    write_csv(PROCESSED_DIR / "all_industries_2023_extrapolation_errors.csv", errors)
    write_csv(PROCESSED_DIR / "all_industries_skipped.csv", skipped)
    if errors:
        mae = sum(abs(float(r["error"])) for r in errors) / len(errors)
        mape = sum(float(r["absolute_percent_error"]) for r in errors) / len(errors)
    else:
        mae = math.nan
        mape = math.nan
    write_csv(PROCESSED_DIR / "all_industries_error_summary.csv", [{"n": len(errors), "mae": round(mae, 6), "mape": round(mape, 6), "skipped": len(skipped)}])
    print(f"all-industry quarterly estimates: {len(estimates)} rows")
    print(f"all-industry validation rows: {len(errors)}")
    print(f"skipped: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
