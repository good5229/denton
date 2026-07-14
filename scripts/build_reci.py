from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


REGION_NAMES = {
    "00": "전국",
    "11": "서울특별시",
    "21": "부산광역시",
    "22": "대구광역시",
    "23": "인천광역시",
    "24": "광주광역시",
    "25": "대전광역시",
    "26": "울산광역시",
    "29": "세종특별자치시",
    "31": "경기도",
    "32": "강원특별자치도",
    "33": "충청북도",
    "34": "충청남도",
    "35": "전북특별자치도",
    "36": "전라남도",
    "37": "경상북도",
    "38": "경상남도",
    "39": "제주특별자치도",
}
RECI_SECTORS = {
    "A00",
    "B00",
    "C00",
    "D00",
    "F00",
    "G00",
    "H00",
    "I00",
    "J00",
    "K00",
    "L00",
    "MN0",
    "O00",
    "P00",
    "Q00",
    "ERS",
}


def period_sort(period: str) -> int:
    return int(period[:4]) * 10 + int(period[-1])


def pct_error(predicted: float, actual: float) -> float | str:
    if actual == 0:
        return ""
    return (predicted - actual) / actual * 100.0


def pearson(xs: list[float], ys: list[float]) -> float | str:
    if len(xs) < 3 or len(xs) != len(ys):
        return ""
    mx, my = mean(xs), mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return ""
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def quarterly_reci() -> tuple[list[dict[str, Any]], dict[tuple[str, str], float]]:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    for row in read_csv(PROCESSED_DIR / "all_industries_quarterly_gva_estimates.csv"):
        value = parse_number(row.get("estimated_gva"))
        if value is None:
            continue
        totals[(row.get("area_code", ""), row.get("period", ""))] += value

    base: dict[str, float] = {}
    for area in {key[0] for key in totals}:
        values = [value for (code, period), value in totals.items() if code == area and period.startswith("2020Q")]
        if values:
            base[area] = mean(values)

    rows = []
    for (area, period), value in sorted(totals.items(), key=lambda item: (item[0][0], period_sort(item[0][1]))):
        base_value = base.get(area)
        rows.append(
            {
                "area_code": area,
                "area_name": REGION_NAMES.get(area, area),
                "period": period,
                "year": period[:4],
                "quarter": period[-1],
                "reci_gva": round(value, 6),
                "reci_index_2020q_avg_100": round(value / base_value * 100.0, 6) if base_value else "",
            }
        )
    write_csv(PROCESSED_DIR / "reci_quarterly_index.csv", rows)
    return rows, totals


def actual_annual() -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = defaultdict(float)
    for row in read_csv(PROCESSED_DIR / "annual_grva_real.csv"):
        if row.get("c2_id") not in RECI_SECTORS:
            continue
        value = parse_number(row.get("value"))
        if value is not None:
            out[(row.get("c1_id", ""), row.get("prd_de", ""))] += value
    return out


def annual_validation(totals: dict[tuple[str, str], float]) -> list[dict[str, Any]]:
    annual_pred: dict[tuple[str, str], float] = defaultdict(float)
    for (area, period), value in totals.items():
        annual_pred[(area, period[:4])] += value
    actual = actual_annual()
    rows = []
    for key in sorted(set(annual_pred) & set(actual)):
        area, year = key
        predicted = annual_pred[key]
        observed = actual[key]
        error = predicted - observed
        rows.append(
            {
                "area_code": area,
                "area_name": REGION_NAMES.get(area, area),
                "year": year,
                "reci_annualized_gva": round(predicted, 6),
                "actual_annual_grva": round(observed, 6),
                "error": round(error, 6),
                "absolute_error": round(abs(error), 6),
                "percent_error": round(pct_error(predicted, observed), 12) if observed else "",
            }
        )
    write_csv(PROCESSED_DIR / "reci_annual_validation.csv", rows)
    return rows


def rolling_validation() -> list[dict[str, Any]]:
    predicted: dict[tuple[str, str], float] = defaultdict(float)
    actual: dict[tuple[str, str], float] = defaultdict(float)
    names: dict[str, str] = {}
    for row in read_csv(PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv"):
        p = parse_number(row.get("predicted_annual_gva"))
        a = parse_number(row.get("actual_annual_gva"))
        key = (row.get("area_code", ""), row.get("target_year", ""))
        if p is not None:
            predicted[key] += p
        if a is not None:
            actual[key] += a
        names[row.get("area_code", "")] = row.get("area_name", "")
    rows = []
    for key in sorted(set(predicted) & set(actual)):
        area, year = key
        p = predicted[key]
        a = actual[key]
        error = p - a
        rows.append(
            {
                "area_code": area,
                "area_name": names.get(area) or REGION_NAMES.get(area, area),
                "year": year,
                "predicted_reci_annual_gva": round(p, 6),
                "actual_annual_grva": round(a, 6),
                "error": round(error, 6),
                "absolute_error": round(abs(error), 6),
                "percent_error": round(pct_error(p, a), 12) if a else "",
                "absolute_percent_error": round(abs(pct_error(p, a)), 12) if a else "",
            }
        )
    write_csv(PROCESSED_DIR / "reci_rolling_validation.csv", rows)
    return rows


def growth_correlation(rows: list[dict[str, Any]], predicted_field: str, actual_field: str, year_field: str = "year") -> list[dict[str, Any]]:
    by_area: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if parse_number(row.get(predicted_field)) is not None and parse_number(row.get(actual_field)) is not None:
            by_area[row["area_code"]].append(row)
    out = []
    for area, items in by_area.items():
        items.sort(key=lambda row: int(row[year_field]))
        pred_growth: list[float] = []
        actual_growth: list[float] = []
        for prev, curr in zip(items, items[1:]):
            p0 = parse_number(prev[predicted_field])
            p1 = parse_number(curr[predicted_field])
            a0 = parse_number(prev[actual_field])
            a1 = parse_number(curr[actual_field])
            if not p0 or not a0 or p1 is None or a1 is None:
                continue
            pred_growth.append((p1 / p0 - 1.0) * 100.0)
            actual_growth.append((a1 / a0 - 1.0) * 100.0)
        corr = pearson(pred_growth, actual_growth)
        out.append(
            {
                "area_code": area,
                "area_name": items[0].get("area_name", REGION_NAMES.get(area, area)),
                "growth_pairs": len(pred_growth),
                "growth_pearson_corr": round(corr, 6) if isinstance(corr, float) else "",
            }
        )
    return out


def summary(annual_rows: list[dict[str, Any]], rolling_rows: list[dict[str, Any]]) -> None:
    annual_ape = [abs(float(row["percent_error"])) for row in annual_rows if row.get("percent_error") not in {"", None}]
    rolling_ape = [abs(float(row["absolute_percent_error"])) for row in rolling_rows if row.get("absolute_percent_error") not in {"", None}]
    annual_corr = growth_correlation(annual_rows, "reci_annualized_gva", "actual_annual_grva")
    rolling_corr = growth_correlation(rolling_rows, "predicted_reci_annual_gva", "actual_annual_grva")
    write_csv(PROCESSED_DIR / "reci_growth_correlations.csv", annual_corr + [{**row, "validation_type": "rolling"} for row in rolling_corr])
    write_csv(
        PROCESSED_DIR / "reci_validation_summary.csv",
        [
            {
                "annual_validation_rows": len(annual_rows),
                "annual_validation_mape": round(mean(annual_ape), 9) if annual_ape else "",
                "rolling_validation_rows": len(rolling_rows),
                "rolling_validation_mape": round(mean(rolling_ape), 9) if rolling_ape else "",
            }
        ],
    )


def main() -> int:
    _, totals = quarterly_reci()
    annual_rows = annual_validation(totals)
    rolling_rows = rolling_validation()
    summary(annual_rows, rolling_rows)
    print(f"RECI annual validation rows: {len(annual_rows)}")
    print(f"RECI rolling validation rows: {len(rolling_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
