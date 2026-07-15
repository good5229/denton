from __future__ import annotations

from collections import defaultdict
from typing import Any

from allocate_detailed_industry import parent_area_from_admin
from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


def load_manufacturing_actual_proxy_shares() -> dict[tuple[str, str, str, str, int, str], float]:
    values: dict[tuple[str, str, str, str, int, str], float] = {}
    totals: dict[tuple[str, str, str, int, str], float] = defaultdict(float)
    for row in read_csv(PROCESSED_DIR / "expanded_manufacturing_sigungu_ksic.csv"):
        if row.get("metric") != "value_added":
            continue
        value = parse_number(row.get("value"))
        year = parse_number(row.get("prd_de"))
        level = row.get("ksic_level", "")
        if value is None or value < 0 or year is None or not level:
            continue
        parent_area = parent_area_from_admin(row.get("c1_id", ""))
        if not parent_area:
            continue
        key = (parent_area, row.get("c1_id", ""), row.get("c1_nm", ""), level, int(year), row.get("c2_id", ""))
        group_key = (parent_area, row.get("c1_id", ""), row.get("c1_nm", ""), int(year), level)
        values[key] = value
        totals[group_key] += value
    shares: dict[tuple[str, str, str, str, int, str], float] = {}
    for key, value in values.items():
        parent_area, sigungu_code, sigungu_name, level, year, _ = key
        total = totals.get((parent_area, sigungu_code, sigungu_name, year, level), 0.0)
        if total > 0:
            shares[key] = value / total
    return shares


def manufacturing_proxy_share_backtest() -> list[dict[str, Any]]:
    actual_shares = load_manufacturing_actual_proxy_shares()
    rows = read_csv(PROCESSED_DIR / "detailed_industry_annual_estimates.csv")
    group_totals: dict[tuple[str, str, str, str, int], float] = defaultdict(float)
    for row in rows:
        value = parse_number(row.get("estimated_annual_gva"))
        year = parse_number(row.get("year"))
        if value is None or year is None:
            continue
        key = (row.get("parent_area_code", ""), row.get("sigungu_code", ""), row.get("sigungu_name", ""), row.get("detail_level", ""), int(year))
        group_totals[key] += value

    out: list[dict[str, Any]] = []
    for row in rows:
        estimate = parse_number(row.get("estimated_annual_gva"))
        year = parse_number(row.get("year"))
        if estimate is None or year is None:
            continue
        group_key = (row.get("parent_area_code", ""), row.get("sigungu_code", ""), row.get("sigungu_name", ""), row.get("detail_level", ""), int(year))
        estimated_total = group_totals.get(group_key, 0.0)
        if estimated_total <= 0:
            continue
        predicted_share = estimate / estimated_total
        actual_key = (
            row.get("parent_area_code", ""),
            row.get("sigungu_code", ""),
            row.get("sigungu_name", ""),
            row.get("detail_level", ""),
            int(year),
            row.get("detail_code", ""),
        )
        actual_share = actual_shares.get(actual_key)
        if actual_share is None:
            continue
        error = predicted_share - actual_share
        out.append(
            {
                "parent_area_code": row.get("parent_area_code", ""),
                "sigungu_code": row.get("sigungu_code", ""),
                "sigungu_name": row.get("sigungu_name", ""),
                "detail_level": row.get("detail_level", ""),
                "detail_code": row.get("detail_code", ""),
                "detail_name": row.get("detail_name", ""),
                "year": int(year),
                "predicted_allocation_share": round(predicted_share, 12),
                "actual_value_added_share": round(actual_share, 12),
                "share_error": round(error, 12),
                "absolute_share_error": round(abs(error), 12),
                "proxy_year_used": row.get("proxy_year", ""),
                "target_year_proxy_available_afterward": "True",
                "parent_status": row.get("parent_status", ""),
                "method": "lagged proxy allocation share compared with same-year value-added proxy share",
            }
        )
    return out


def summarize_share_errors(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row.get(key, "")) for key in keys)].append(row)
    out: list[dict[str, Any]] = []
    for key, items in sorted(groups.items()):
        mae = sum(float(row["absolute_share_error"]) for row in items) / len(items)
        out.append(
            {
                **{field: value for field, value in zip(keys, key)},
                "comparison_count": len(items),
                "mean_absolute_share_error": round(mae, 12),
            }
        )
    return out


def load_constraint_summary(filename: str, family: str) -> list[dict[str, Any]]:
    rows = read_csv(PROCESSED_DIR / filename)
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(family, row.get("detail_level", ""), row.get("parent_status", "") or "benchmark_constrained_estimate")].append(row)
    out: list[dict[str, Any]] = []
    for (family_name, level, status), items in sorted(groups.items()):
        max_abs = max((parse_number(row.get("absolute_constraint_error")) or 0.0 for row in items), default=0.0)
        out.append(
            {
                "family": family_name,
                "detail_level": level,
                "parent_status": status,
                "diagnostic_rows": len(items),
                "max_absolute_constraint_error": round(max_abs, 9),
                "constraint_ok": max_abs < 0.001,
            }
        )
    return out


def main() -> int:
    proxy_rows = manufacturing_proxy_share_backtest()
    constraint_rows = load_constraint_summary("detailed_industry_constraint_diagnostics.csv", "manufacturing") + load_constraint_summary(
        "service_detail_constraint_diagnostics.csv", "service"
    )
    write_csv(PROCESSED_DIR / "detail_manufacturing_proxy_share_backtest.csv", proxy_rows)
    write_csv(PROCESSED_DIR / "detail_manufacturing_proxy_share_by_level.csv", summarize_share_errors(proxy_rows, ["detail_level"]))
    write_csv(PROCESSED_DIR / "detail_manufacturing_proxy_share_by_year.csv", summarize_share_errors(proxy_rows, ["year"]))
    write_csv(PROCESSED_DIR / "detail_parent_constraint_summary.csv", constraint_rows)
    print(f"manufacturing proxy share comparisons: {len(proxy_rows)}")
    print(f"constraint summary rows: {len(constraint_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
