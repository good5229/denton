from __future__ import annotations

from collections import defaultdict
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


SEOUL_AREA_CODE = "11"
SEOUL_TOTAL_ROW_CODES = {"001", "11", ""}


def add_bucket(bucket: dict[tuple[str, ...], float], key: tuple[str, ...], value: Any) -> None:
    parsed = parse_number(value)
    if parsed is None:
        return
    bucket[key] += parsed


def pct_error(estimated: float, benchmark: float) -> float | str:
    if benchmark == 0:
        return ""
    return (estimated - benchmark) / benchmark * 100.0


def parent_quarterly() -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], str]]:
    values: dict[tuple[str, str], float] = {}
    names: dict[tuple[str, str], str] = {}
    for row in read_csv(PROCESSED_DIR / "all_industries_quarterly_gva_estimates.csv"):
        if row.get("area_code") != SEOUL_AREA_CODE:
            continue
        value = parse_number(row.get("estimated_gva"))
        if value is None:
            continue
        key = (row.get("sector_code", ""), row.get("period", ""))
        values[key] = value
        names[key] = row.get("sector_name", "")
    return values, names


def sigungu_quarterly() -> tuple[dict[tuple[str, str], float], dict[str, str]]:
    values: dict[tuple[str, str], float] = defaultdict(float)
    names: dict[str, str] = {}
    for row in read_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv"):
        if row.get("parent_area_code") != SEOUL_AREA_CODE:
            continue
        if row.get("sigungu_code") in SEOUL_TOTAL_ROW_CODES:
            continue
        sector = row.get("sector_code", "")
        period = row.get("period", "")
        add_bucket(values, (sector, period), row.get("estimated_gva"))
        names[sector] = row.get("sector_name", "")
    return values, names


def quarterly_diagnostics() -> list[dict[str, Any]]:
    parent, parent_names = parent_quarterly()
    child, child_names = sigungu_quarterly()
    rows: list[dict[str, Any]] = []
    for key in sorted(set(parent) | set(child), key=lambda item: (item[1], item[0])):
        sector, period = key
        child_sum = child.get(key, 0.0)
        parent_value = parent.get(key, 0.0)
        error = child_sum - parent_value
        rows.append(
            {
                "level": "sector",
                "sector_code": sector,
                "sector_name": child_names.get(sector) or parent_names.get(key, ""),
                "period": period,
                "sigungu_quarterly_sum": round(child_sum, 6),
                "seoul_parent_quarterly_gva": round(parent_value, 6),
                "consistency_error": round(error, 9),
                "absolute_consistency_error": round(abs(error), 9),
                "percent_consistency_error": round(pct_error(child_sum, parent_value), 12) if parent_value else "",
            }
        )

    total_child: dict[str, float] = defaultdict(float)
    total_parent: dict[str, float] = defaultdict(float)
    for (_, period), value in child.items():
        total_child[period] += value
    for (_, period), value in parent.items():
        total_parent[period] += value
    for period in sorted(set(total_child) | set(total_parent)):
        child_sum = total_child.get(period, 0.0)
        parent_value = total_parent.get(period, 0.0)
        error = child_sum - parent_value
        rows.append(
            {
                "level": "total",
                "sector_code": "__ALL__",
                "sector_name": "전체",
                "period": period,
                "sigungu_quarterly_sum": round(child_sum, 6),
                "seoul_parent_quarterly_gva": round(parent_value, 6),
                "consistency_error": round(error, 9),
                "absolute_consistency_error": round(abs(error), 9),
                "percent_consistency_error": round(pct_error(child_sum, parent_value), 12) if parent_value else "",
            }
        )
    return rows


def annual_diagnostics(quarterly_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    child: dict[tuple[str, str], float] = defaultdict(float)
    parent: dict[tuple[str, str], float] = defaultdict(float)
    names: dict[str, str] = {}
    for row in quarterly_rows:
        year = str(row.get("period", ""))[:4]
        sector = str(row.get("sector_code", ""))
        key = (sector, year)
        add_bucket(child, key, row.get("sigungu_quarterly_sum"))
        add_bucket(parent, key, row.get("seoul_parent_quarterly_gva"))
        names[sector] = str(row.get("sector_name", ""))
    rows: list[dict[str, Any]] = []
    for key in sorted(set(child) | set(parent), key=lambda item: (item[1], item[0])):
        sector, year = key
        child_sum = child.get(key, 0.0)
        parent_value = parent.get(key, 0.0)
        error = child_sum - parent_value
        rows.append(
            {
                "sector_code": sector,
                "sector_name": names.get(sector, ""),
                "year": year,
                "sigungu_annual_sum_from_quarters": round(child_sum, 6),
                "seoul_parent_annual_sum_from_quarters": round(parent_value, 6),
                "consistency_error": round(error, 9),
                "absolute_consistency_error": round(abs(error), 9),
                "percent_consistency_error": round(pct_error(child_sum, parent_value), 12) if parent_value else "",
            }
        )
    return rows


def main() -> int:
    quarterly = quarterly_diagnostics()
    annual = annual_diagnostics(quarterly)
    write_csv(PROCESSED_DIR / "seoul_sigungu_quarterly_consistency.csv", quarterly)
    write_csv(PROCESSED_DIR / "seoul_sigungu_annual_consistency.csv", annual)
    max_quarter = max((parse_number(row["absolute_consistency_error"]) or 0.0 for row in quarterly), default=0.0)
    max_annual = max((parse_number(row["absolute_consistency_error"]) or 0.0 for row in annual), default=0.0)
    write_csv(
        PROCESSED_DIR / "seoul_sigungu_consistency_summary.csv",
        [
            {
                "quarterly_rows": len(quarterly),
                "annual_rows": len(annual),
                "max_quarterly_absolute_consistency_error": round(max_quarter, 9),
                "max_annual_absolute_consistency_error": round(max_annual, 9),
            }
        ],
    )
    print(f"wrote {len(quarterly)} quarterly and {len(annual)} annual Seoul consistency rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
