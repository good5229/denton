from __future__ import annotations

from collections import defaultdict
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


METRIC_PRIORITY = ("sales", "employees", "establishments")
INDUSTRY_TO_SECTOR = {
    "A": "A00",
    "B": "B00",
    "C": "C00",
    "D": "D00",
    "E": "ERS",
    "F": "F00",
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


def admin_level(code: str) -> str:
    if code == "00":
        return "national"
    if len(code) == 2:
        return "sido"
    if len(code) == 5:
        return "sigungu"
    if len(code) >= 7:
        return "emd"
    return "unknown"


def load_sigungu_names() -> dict[tuple[str, str], str]:
    names = {}
    for row in read_csv(PROCESSED_DIR / "emd_economic_census_2015.csv"):
        code = row.get("c2_id", "")
        if admin_level(code) == "sigungu":
            names[(code[:2], row.get("c2_nm", ""))] = code
    return names


def load_proxy_rows() -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(PROCESSED_DIR / "emd_economic_census_2015.csv"):
        emd_code = row.get("c2_id", "")
        if admin_level(emd_code) != "emd":
            continue
        sector = INDUSTRY_TO_SECTOR.get(row.get("c1_id", ""))
        if not sector:
            continue
        value = parse_number(row.get("value"))
        if value is None or value < 0:
            continue
        rows.append(
            {
                "parent_area_code": emd_code[:2],
                "sigungu_code_2015": emd_code[:5],
                "emd_code": emd_code,
                "emd_name": row.get("c2_nm", ""),
                "sector_code": sector,
                "industry_code": row.get("c1_id", ""),
                "industry_name": row.get("c1_nm", ""),
                "metric": row.get("metric", ""),
                "proxy_value": value,
            }
        )
    return rows


def build_weights(proxy_rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in proxy_rows:
        grouped[(row["parent_area_code"], row["sigungu_code_2015"], row["sector_code"], row["metric"])].append(row)

    selected: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for key_metric, rows in grouped.items():
        base = key_metric[:-1]
        metric = key_metric[-1]
        total = sum(float(row["proxy_value"]) for row in rows)
        if total <= 0:
            continue
        current = selected.get(base)
        if current and METRIC_PRIORITY.index(current[0]["metric"]) <= METRIC_PRIORITY.index(metric):
            continue
        selected[base] = [{**row, "share": float(row["proxy_value"]) / total} for row in rows]
    return selected


def allocate() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    sigungu_names = load_sigungu_names()
    weights = build_weights(load_proxy_rows())
    quarterly = []
    diagnostics: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    skipped = []

    for row in read_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv"):
        parent_area = row.get("parent_area_code", "")
        sector = row.get("sector_code", "")
        sigungu_name = row.get("sigungu_name", "")
        sigungu_code_2015 = sigungu_names.get((parent_area, sigungu_name))
        if not sigungu_code_2015:
            skipped.append(
                {
                    "parent_area_code": parent_area,
                    "sigungu_code": row.get("sigungu_code", ""),
                    "sigungu_name": sigungu_name,
                    "sector_code": sector,
                    "period": row.get("period", ""),
                    "reason": "missing 2015 economic census sigungu code",
                }
            )
            continue
        weight_rows = weights.get((parent_area, sigungu_code_2015, sector), [])
        if not weight_rows:
            skipped.append(
                {
                    "parent_area_code": parent_area,
                    "sigungu_code": row.get("sigungu_code", ""),
                    "sigungu_name": sigungu_name,
                    "sector_code": sector,
                    "period": row.get("period", ""),
                    "reason": "missing emd proxy weights",
                }
            )
            continue
        parent_value = parse_number(row.get("estimated_gva"))
        if parent_value is None:
            continue
        allocated_sum = 0.0
        for weight in weight_rows:
            estimate = parent_value * float(weight["share"])
            allocated_sum += estimate
            quarterly.append(
                {
                    "source_region": row.get("source_region", ""),
                    "parent_area_code": parent_area,
                    "sigungu_code": sigungu_code_2015,
                    "sigungu_name": sigungu_name,
                    "emd_code": weight["emd_code"],
                    "emd_name": weight["emd_name"],
                    "sector_code": sector,
                    "sector_name": row.get("sector_name", ""),
                    "year": row.get("year", ""),
                    "quarter": row.get("quarter", ""),
                    "period": row.get("period", ""),
                    "estimated_gva": round(estimate, 6),
                    "parent_sigungu_quarterly_gva": round(parent_value, 6),
                    "allocation_share": round(float(weight["share"]), 12),
                    "proxy_metric": weight["metric"],
                    "proxy_year": "2015",
                    "method": "2015 emd economic census proxy share within sigungu sector quarterly GVA",
                }
            )
        diag_key = (sigungu_code_2015, sector, row.get("period", ""), row.get("year", ""))
        diag = diagnostics.setdefault(
            diag_key,
            {
                "parent_area_code": parent_area,
                "sigungu_code": sigungu_code_2015,
                "sigungu_name": sigungu_name,
                "sector_code": sector,
                "sector_name": row.get("sector_name", ""),
                "period": row.get("period", ""),
                "year": row.get("year", ""),
                "allocated_sum": 0.0,
                "parent_sigungu_quarterly_gva": 0.0,
            },
        )
        diag["allocated_sum"] += allocated_sum
        diag["parent_sigungu_quarterly_gva"] += parent_value

    diagnostic_rows = []
    for row in diagnostics.values():
        allocated = float(row["allocated_sum"])
        parent = float(row["parent_sigungu_quarterly_gva"])
        error = allocated - parent
        diagnostic_rows.append(
            {
                **row,
                "allocated_sum": round(allocated, 6),
                "parent_sigungu_quarterly_gva": round(parent, 6),
                "constraint_error": round(error, 9),
                "absolute_constraint_error": round(abs(error), 9),
                "percent_constraint_error": round(error / parent * 100.0, 12) if parent else "",
            }
        )
    annual: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in quarterly:
        key = (row["emd_code"], row["sector_code"], row["year"], row["sigungu_code"], row["parent_area_code"])
        item = annual.setdefault(
            key,
            {
                "source_region": row["source_region"],
                "parent_area_code": row["parent_area_code"],
                "sigungu_code": row["sigungu_code"],
                "sigungu_name": row["sigungu_name"],
                "emd_code": row["emd_code"],
                "emd_name": row["emd_name"],
                "sector_code": row["sector_code"],
                "sector_name": row["sector_name"],
                "year": row["year"],
                "estimated_annual_gva": 0.0,
                "proxy_metric": row["proxy_metric"],
                "proxy_year": row["proxy_year"],
                "method": row["method"],
            },
        )
        item["estimated_annual_gva"] += float(row["estimated_gva"])
    annual_rows = []
    for row in annual.values():
        row["estimated_annual_gva"] = round(float(row["estimated_annual_gva"]), 6)
        annual_rows.append(row)
    return quarterly, annual_rows, diagnostic_rows, skipped


def main() -> int:
    quarterly, annual, diagnostics, skipped = allocate()
    write_csv(PROCESSED_DIR / "emd_quarterly_gva_estimates.csv", quarterly)
    write_csv(PROCESSED_DIR / "emd_annual_gva_estimates.csv", annual)
    write_csv(PROCESSED_DIR / "emd_constraint_diagnostics.csv", diagnostics)
    write_csv(PROCESSED_DIR / "emd_allocation_skipped.csv", skipped)
    print(f"emd quarterly estimates: {len(quarterly)} rows")
    print(f"emd annual estimates: {len(annual)} rows")
    print(f"emd diagnostics: {len(diagnostics)} rows")
    print(f"emd skipped: {len(skipped)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
