from __future__ import annotations

from collections import defaultdict
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


def compact_name(value: str) -> str:
    return (
        str(value or "")
        .replace(" ", "")
        .replace(",", "")
        .replace("·", "")
        .replace("ㆍ", "")
    )


def is_parent_total_row(row: dict[str, str]) -> bool:
    source = compact_name(row.get("source_region", ""))
    sigungu = compact_name(row.get("sigungu_name", ""))
    if not source or not sigungu:
        return False
    if row.get("sigungu_code") == row.get("parent_area_code"):
        return True
    return sigungu in {
        source,
        source.replace("특별", ""),
        source.replace("광역", ""),
        source.replace("특별자치", ""),
    }


def add_number(bucket: dict[tuple[str, ...], float], key: tuple[str, ...], value: Any) -> None:
    parsed = parse_number(value)
    if parsed is not None:
        bucket[key] += parsed


def pct_error(child_sum: float, parent_value: float) -> float | str:
    if parent_value == 0:
        return ""
    return (child_sum - parent_value) / parent_value * 100.0


def load_parent_quarterly() -> tuple[dict[tuple[str, str, str], float], dict[str, str], dict[str, str]]:
    values: dict[tuple[str, str, str], float] = {}
    sector_names: dict[str, str] = {}
    area_names: dict[str, str] = {}
    for row in read_csv(PROCESSED_DIR / "annual_grva_real.csv"):
        if row.get("c1_id") and row.get("c1_nm"):
            area_names[row["c1_id"]] = row["c1_nm"]
    for row in read_csv(PROCESSED_DIR / "all_industries_quarterly_gva_estimates.csv"):
        value = parse_number(row.get("estimated_gva"))
        if value is None:
            continue
        area = row.get("area_code", "")
        if area == "00":
            continue
        sector = row.get("sector_code", "")
        period = row.get("period", "")
        values[(area, sector, period)] = value
        sector_names[sector] = row.get("sector_name", "")
    return values, sector_names, area_names


def load_sigungu_sums() -> tuple[dict[tuple[str, str, str], float], dict[str, str]]:
    values: dict[tuple[str, str, str], float] = defaultdict(float)
    area_names: dict[str, str] = {}
    for row in read_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv"):
        if is_parent_total_row(row):
            continue
        area = row.get("parent_area_code", "")
        sector = row.get("sector_code", "")
        period = row.get("period", "")
        add_number(values, (area, sector, period), row.get("estimated_gva"))
        if area and row.get("source_region"):
            area_names[area] = row["source_region"]
    return values, area_names


def quarterly_diagnostics() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    parent, sector_names, parent_area_names = load_parent_quarterly()
    child, area_names = load_sigungu_sums()
    rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for key in sorted(set(parent) & set(child), key=lambda item: (item[0], item[2], item[1])):
        area, sector, period = key
        child_sum = child.get(key, 0.0)
        parent_value = parent.get(key, 0.0)
        error = child_sum - parent_value
        rows.append(
            {
                "parent_area_code": area,
                "parent_area_name": area_names.get(area) or parent_area_names.get(area, ""),
                "sector_code": sector,
                "sector_name": sector_names.get(sector, ""),
                "period": period,
                "year": period[:4],
                "sigungu_quarterly_sum": round(child_sum, 6),
                "parent_sido_quarterly_gva": round(parent_value, 6),
                "consistency_error": round(error, 9),
                "absolute_consistency_error": round(abs(error), 9),
                "percent_consistency_error": round(pct_error(child_sum, parent_value), 12) if parent_value else "",
            }
        )
    for key in sorted(set(parent) - set(child), key=lambda item: (item[0], item[2], item[1])):
        area, sector, period = key
        missing.append(
            {
                "parent_area_code": area,
                "parent_area_name": parent_area_names.get(area, ""),
                "sector_code": sector,
                "sector_name": sector_names.get(sector, ""),
                "period": period,
                "year": period[:4],
                "parent_sido_quarterly_gva": round(parent.get(key, 0.0), 6),
                "reason": "missing sigungu child estimate for parent-sector-period",
            }
        )
    return rows, missing


def summarize(rows: list[dict[str, Any]], group_fields: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row.get(field, "")) for field in group_fields)
        grouped[key].append(row)
    out: list[dict[str, Any]] = []
    for key, items in sorted(grouped.items()):
        child_sum = sum(float(row["sigungu_quarterly_sum"]) for row in items)
        parent_sum = sum(float(row["parent_sido_quarterly_gva"]) for row in items)
        abs_error_sum = sum(float(row["absolute_consistency_error"]) for row in items)
        error_sum = child_sum - parent_sum
        mape = sum(abs(float(row["percent_consistency_error"] or 0.0)) for row in items) / len(items)
        record: dict[str, Any] = {field: value for field, value in zip(group_fields, key)}
        record.update(
            {
                "comparison_count": len(items),
                "sigungu_sum_total": round(child_sum, 6),
                "parent_sido_total": round(parent_sum, 6),
                "error_sum": round(error_sum, 6),
                "absolute_error_sum": round(abs_error_sum, 6),
                "mape": round(mape, 6),
                "wmape": round(abs_error_sum / parent_sum * 100.0, 6) if parent_sum else "",
                "aggregate_percent_error": round(error_sum / parent_sum * 100.0, 6) if parent_sum else "",
            }
        )
        out.append(record)
    return out


def top_errors(rows: list[dict[str, Any]], limit: int = 100) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: float(row["absolute_consistency_error"]), reverse=True)
    out: list[dict[str, Any]] = []
    for row in ordered[:limit]:
        item = dict(row)
        item["rank"] = len(out) + 1
        out.append(item)
    return out


def main() -> int:
    quarterly, missing = quarterly_diagnostics()
    by_area = summarize(quarterly, ["parent_area_code", "parent_area_name"])
    by_sector = summarize(quarterly, ["sector_code", "sector_name"])
    by_area_sector = summarize(quarterly, ["parent_area_code", "parent_area_name", "sector_code", "sector_name"])
    by_year = summarize(quarterly, ["year"])
    overall = summarize(quarterly, [])
    write_csv(PROCESSED_DIR / "sigungu_parent_quarterly_consistency.csv", quarterly)
    write_csv(PROCESSED_DIR / "sigungu_parent_consistency_by_area.csv", by_area)
    write_csv(PROCESSED_DIR / "sigungu_parent_consistency_by_sector.csv", by_sector)
    write_csv(PROCESSED_DIR / "sigungu_parent_consistency_by_area_sector.csv", by_area_sector)
    write_csv(PROCESSED_DIR / "sigungu_parent_consistency_by_year.csv", by_year)
    write_csv(PROCESSED_DIR / "sigungu_parent_consistency_top_errors.csv", top_errors(quarterly))
    write_csv(PROCESSED_DIR / "sigungu_parent_consistency_missing_child.csv", missing)
    write_csv(PROCESSED_DIR / "sigungu_parent_consistency_summary.csv", overall)
    print(f"quarterly consistency rows: {len(quarterly)}")
    print(f"area-sector rows: {len(by_area_sector)}")
    print(f"missing child rows: {len(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
