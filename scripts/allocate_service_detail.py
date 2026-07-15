from __future__ import annotations

from collections import defaultdict
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


SERVICE_PARENT = {
    "E": "ERS",
    "G": "G00",
    "H": "H00",
    "I": "I00",
    "J": "J00",
    "K": "K00",
    "L": "L00",
    "M": "MN0",
    "N": "MN0",
    "O": "O00",
    "P": "P00",
    "Q": "Q00",
    "R": "ERS",
    "S": "ERS",
}
SERVICE_SECTORS = set(SERVICE_PARENT.values())


def period_from_prd(prd_de: str) -> str:
    text = str(prd_de)
    if len(text) == 6:
        return f"{text[:4]}Q{text[-1]}"
    return text


def detail_level(code: str) -> str:
    # Codes are letter-prefixed KSIC-like identifiers, e.g. G46, G463, G4631.
    digits = len(code) - 1
    if digits <= 0:
        return "section"
    if digits == 2:
        return "middle"
    if digits == 3:
        return "small"
    return "class"


def load_detail_indicators() -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in read_csv(PROCESSED_DIR / "expanded_national_service_ksic_production_index.csv"):
        code = row.get("c1_id", "")
        if len(code) <= 1:
            continue
        parent = SERVICE_PARENT.get(code[:1])
        if not parent:
            continue
        value = parse_number(row.get("value"))
        if value is None or value <= 0:
            continue
        period = period_from_prd(row.get("prd_de", ""))
        level = detail_level(code)
        grouped[(parent, period, level)].append(
            {
                "detail_code": code,
                "detail_name": row.get("c1_nm", ""),
                "detail_level": level,
                "indicator": value,
            }
        )
    return grouped


def allocate() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    indicators = load_detail_indicators()
    quarterly: list[dict[str, Any]] = []
    diagnostics: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    skipped: list[dict[str, Any]] = []

    for row in read_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv"):
        sector = row.get("sector_code", "")
        if sector not in SERVICE_SECTORS:
            continue
        period = row.get("period", "")
        level_groups = {
            level: indicators.get((sector, period, level), [])
            for level in ("middle", "small", "class")
        }
        if not any(level_groups.values()):
            skipped.append(
                {
                    "sigungu_code": row.get("sigungu_code", ""),
                    "sigungu_name": row.get("sigungu_name", ""),
                    "sector_code": sector,
                    "period": period,
                    "reason": "missing national service detail indicator",
                }
            )
            continue
        parent_value = parse_number(row.get("estimated_gva"))
        if parent_value is None:
            continue
        for level, detail_rows in level_groups.items():
            if not detail_rows:
                continue
            total_indicator = sum(float(item["indicator"]) for item in detail_rows)
            if total_indicator <= 0:
                continue
            allocated = 0.0
            for item in detail_rows:
                share = float(item["indicator"]) / total_indicator
                estimate = parent_value * share
                allocated += estimate
                quarterly.append(
                    {
                        "source_region": row.get("source_region", ""),
                        "parent_area_code": row.get("parent_area_code", ""),
                        "sigungu_code": row.get("sigungu_code", ""),
                        "sigungu_name": row.get("sigungu_name", ""),
                        "parent_sector_code": sector,
                        "parent_sector_name": row.get("sector_name", ""),
                        "detail_code": item["detail_code"],
                        "detail_name": item["detail_name"],
                        "detail_level": item["detail_level"],
                        "year": row.get("year", ""),
                        "quarter": row.get("quarter", ""),
                        "period": period,
                        "estimated_gva": round(estimate, 6),
                        "parent_quarterly_gva": round(parent_value, 6),
                        "allocation_share": round(share, 12),
                        "indicator": round(float(item["indicator"]), 6),
                        "proxy_metric": "national_service_production_index",
                        "method": "national service detail production index share within sigungu parent service quarterly GVA by detail level",
                    }
                )
            diag_key = (row.get("sigungu_code", ""), sector, level, period, row.get("year", ""))
            diagnostics[diag_key] = {
                "sigungu_code": row.get("sigungu_code", ""),
                "sigungu_name": row.get("sigungu_name", ""),
                "sector_code": sector,
                "sector_name": row.get("sector_name", ""),
                "detail_level": level,
                "period": period,
                "year": row.get("year", ""),
                "allocated_sum": round(allocated, 6),
                "parent_quarterly_gva": round(parent_value, 6),
                "constraint_error": round(allocated - parent_value, 9),
                "absolute_constraint_error": round(abs(allocated - parent_value), 9),
                "percent_constraint_error": round((allocated - parent_value) / parent_value * 100.0, 12) if parent_value else "",
            }

    annual: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in quarterly:
        key = (row["sigungu_code"], row["parent_sector_code"], row["detail_code"], row["year"])
        item = annual.setdefault(
            key,
            {
                "source_region": row["source_region"],
                "parent_area_code": row["parent_area_code"],
                "sigungu_code": row["sigungu_code"],
                "sigungu_name": row["sigungu_name"],
                "parent_sector_code": row["parent_sector_code"],
                "parent_sector_name": row["parent_sector_name"],
                "detail_code": row["detail_code"],
                "detail_name": row["detail_name"],
                "detail_level": row["detail_level"],
                "year": row["year"],
                "estimated_annual_gva": 0.0,
                "proxy_metric": row["proxy_metric"],
                "method": row["method"],
            },
        )
        item["estimated_annual_gva"] += float(row["estimated_gva"])
    annual_rows = []
    for row in annual.values():
        row["estimated_annual_gva"] = round(float(row["estimated_annual_gva"]), 6)
        annual_rows.append(row)

    summary = [
        {
            "quarterly_rows": len(quarterly),
            "annual_rows": len(annual_rows),
            "diagnostic_rows": len(diagnostics),
            "skipped_rows": len(skipped),
            "unique_sigungu": len({row["sigungu_code"] for row in quarterly}),
            "unique_parent_sectors": len({row["parent_sector_code"] for row in quarterly}),
            "unique_detail_codes": len({row["detail_code"] for row in quarterly}),
            "max_absolute_constraint_error": max((float(row["absolute_constraint_error"]) for row in diagnostics.values()), default=0.0),
        }
    ]
    return quarterly, annual_rows, list(diagnostics.values()), skipped + summary


def main() -> int:
    quarterly, annual, diagnostics, skipped_and_summary = allocate()
    summary = skipped_and_summary[-1:] if skipped_and_summary else []
    skipped = skipped_and_summary[:-1] if skipped_and_summary else []
    write_csv(PROCESSED_DIR / "service_detail_quarterly_estimates.csv", quarterly)
    write_csv(PROCESSED_DIR / "service_detail_annual_estimates.csv", annual)
    write_csv(PROCESSED_DIR / "service_detail_constraint_diagnostics.csv", diagnostics)
    write_csv(PROCESSED_DIR / "service_detail_allocation_skipped.csv", skipped)
    write_csv(PROCESSED_DIR / "service_detail_summary.csv", summary)
    print(f"service detail quarterly rows: {len(quarterly)}")
    print(f"service detail annual rows: {len(annual)}")
    print(f"service detail diagnostics: {len(diagnostics)}")
    print(f"service detail skipped: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
