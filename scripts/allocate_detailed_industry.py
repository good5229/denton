from __future__ import annotations

from collections import defaultdict
from typing import Any

from data_availability import annual_forecast_origin, is_available_as_of
from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


MANUFACTURING_PARENT = "C00"
PROXY_PRIORITY = ("value_added", "employees", "establishments")
ANNUAL_PROXY_PUBLICATION_LAG_MONTHS = 12
FORECAST_ORIGIN_MONTH = 1
FORECAST_ORIGIN_DAY = 1
USE_ECOS_IO_PRIOR = True
KSIC_TO_ECOS_IO_MIDDLE = {
    "C10": "08",
    "C11": "09",
    "C12": "10",
    "C13": "11",
    "C14": "11",
    "C15": "12",
    "C16": "13",
    "C17": "14",
    "C18": "15",
    "C19": "16",
    "C20": "22",
    "C21": "20",
    "C22": "23",
    "C23": "26",
    "C24": "27",
    "C25": "30",
    "C26": "33",
    "C27": "37",
    "C28": "38",
    "C29": "40",
    "C30": "42",
    "C31": "43",
    "C32": "43",
    "C33": "44",
}
ADMIN_PREFIX_TO_PARENT = {
    "11": "11",
    "21": "21",
    "22": "22",
    "23": "23",
    "24": "24",
    "25": "25",
    "26": "26",
    "29": "29",
    "31": "31",
    "32": "32",
    "33": "33",
    "34": "34",
    "35": "35",
    "36": "36",
    "37": "37",
    "38": "38",
    "39": "39",
}


def parent_area_from_admin(code: str) -> str:
    return ADMIN_PREFIX_TO_PARENT.get(str(code)[:2], "")


def load_parent_quarterly() -> dict[tuple[str, str, str], dict[tuple[int, int], dict[str, Any]]]:
    out: dict[tuple[str, str, str], dict[tuple[int, int], dict[str, Any]]] = defaultdict(dict)
    for row in read_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv"):
        if row.get("sector_code") != MANUFACTURING_PARENT:
            continue
        value = parse_number(row.get("estimated_gva"))
        if value is None:
            continue
        key = (row.get("parent_area_code", ""), row.get("sigungu_name", ""), row.get("source_region", ""))
        out[key][(int(row["year"]), int(row["quarter"]))] = {
            "value": value,
            "parent_sigungu_code": row.get("sigungu_code", ""),
            "benchmark_annual_gva": row.get("benchmark_annual_gva", ""),
            "parent_status": "benchmark_constrained_estimate",
            "parent_method": row.get("method", ""),
        }
    forecast_path = PROCESSED_DIR / "sigungu_quarterly_gva_forecasts.csv"
    if not forecast_path.exists():
        return out
    for row in read_csv(forecast_path):
        if row.get("sector_code") != MANUFACTURING_PARENT:
            continue
        value = parse_number(row.get("predicted_gva"))
        if value is None:
            continue
        key = (row.get("parent_area_code", ""), row.get("sigungu_name", ""), row.get("source_region", ""))
        out[key][(int(row["year"]), int(row["quarter"]))] = {
            "value": value,
            "parent_sigungu_code": row.get("sigungu_code", ""),
            "benchmark_annual_gva": "",
            "parent_status": row.get("benchmark_status", "out_of_sample_forecast"),
            "parent_method": row.get("method", ""),
        }
    return out


def load_proxy_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "expanded_manufacturing_sigungu_ksic.csv"):
        if not str(row.get("c2_id", "")).startswith("C"):
            continue
        if row.get("metric") not in PROXY_PRIORITY:
            continue
        if row.get("c1_id") in {"00"}:
            continue
        value = parse_number(row.get("value"))
        if value is None or value < 0:
            continue
        parent_area = parent_area_from_admin(row.get("c1_id", ""))
        if not parent_area:
            continue
        rows.append(
            {
                "parent_area_code": parent_area,
                "sigungu_code": row.get("c1_id", ""),
                "sigungu_name": row.get("c1_nm", ""),
                "detail_code": row.get("c2_id", ""),
                "detail_name": row.get("c2_nm", ""),
                "detail_level": row.get("ksic_level", ""),
                "year": int(row.get("prd_de", "0")),
                "metric": row.get("metric", ""),
                "proxy_value": value,
            }
        )
    return rows


def latest_available_proxy_year(available: set[int], target_year: int) -> int | None:
    as_of = annual_forecast_origin(target_year, FORECAST_ORIGIN_MONTH, FORECAST_ORIGIN_DAY)
    candidates = [
        year
        for year in available
        if is_available_as_of(str(year), "A", ANNUAL_PROXY_PUBLICATION_LAG_MONTHS, as_of)
    ]
    return max(candidates) if candidates else None


def ksic_middle_code(detail_code: str) -> str:
    text = str(detail_code)
    return text[:3] if text.startswith("C") and len(text) >= 3 else text


def load_io_self_factors() -> dict[str, dict[str, Any]]:
    factors: dict[str, dict[str, Any]] = {}
    path = PROCESSED_DIR / "ecos_io_middle_industry_prior.csv"
    if not path.exists() or not USE_ECOS_IO_PRIOR:
        return factors
    for row in read_csv(path):
        if row.get("demand_code") != row.get("input_code"):
            continue
        value = parse_number(row.get("value_added_inducement"))
        if value is None or value <= 0:
            value = parse_number(row.get("production_inducement"))
        if value is None or value <= 0:
            continue
        factors[row["demand_code"]] = {
            "factor": value,
            "io_code": row.get("demand_code"),
            "io_name": row.get("demand_name"),
            "io_year": row.get("year"),
        }
    return factors


def build_weights(proxy_rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str, int], list[dict[str, Any]]]:
    io_factors = load_io_self_factors()
    by_metric: dict[tuple[str, str, str, str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in proxy_rows:
        key = (
            row["parent_area_code"],
            row["sigungu_code"],
            row["sigungu_name"],
            row["detail_level"],
            row["year"],
            row["metric"],
        )
        by_metric[key].append(row)

    selected: dict[tuple[str, str, str, str, int], list[dict[str, Any]]] = {}
    for key_metric, rows in by_metric.items():
        base = key_metric[:-1]
        metric = key_metric[-1]
        total = sum(float(row["proxy_value"]) for row in rows)
        if total <= 0:
            continue
        current = selected.get(base)
        if current:
            current_metric = current[0]["metric"]
            if PROXY_PRIORITY.index(current_metric) <= PROXY_PRIORITY.index(metric):
                continue
        selected[base] = rows
    adjusted: dict[tuple[str, str, str, str, int], list[dict[str, Any]]] = {}
    for base, rows in selected.items():
        prepared = []
        for row in rows:
            io_code = KSIC_TO_ECOS_IO_MIDDLE.get(ksic_middle_code(row["detail_code"]), "")
            io_payload = io_factors.get(io_code, {})
            io_factor = float(io_payload.get("factor", 1.0)) if io_payload else 1.0
            adjusted_proxy = float(row["proxy_value"]) * io_factor
            prepared.append(
                {
                    **row,
                    "io_prior_code": io_payload.get("io_code", io_code),
                    "io_prior_name": io_payload.get("io_name", ""),
                    "io_prior_year": io_payload.get("io_year", ""),
                    "io_value_added_self_factor": io_factor if io_payload else "",
                    "io_adjusted_proxy_value": adjusted_proxy,
                }
            )
        adjusted_total = sum(float(row["io_adjusted_proxy_value"]) for row in prepared)
        if adjusted_total <= 0:
            continue
        adjusted[base] = [
            {**row, "share": float(row["io_adjusted_proxy_value"]) / adjusted_total}
            for row in prepared
        ]
    return adjusted


def allocate() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    parent = load_parent_quarterly()
    weights = build_weights(load_proxy_rows())
    years_by_group: dict[tuple[str, str, str, str], set[int]] = defaultdict(set)
    for parent_area, sigungu_code, sigungu_name, level, year in weights:
        years_by_group[(parent_area, sigungu_code, sigungu_name, level)].add(year)

    quarterly: list[dict[str, Any]] = []
    annual: dict[tuple[str, str, str, str, str, int], dict[str, Any]] = {}
    diagnostics: dict[tuple[str, str, str, int], dict[str, Any]] = {}

    for parent_key, parent_quarters in parent.items():
        parent_area, sigungu_name, source_region = parent_key
        for group_key, available_years in years_by_group.items():
            group_parent, sigungu_code, group_name, level = group_key
            if group_parent != parent_area or group_name != sigungu_name:
                continue
            for (year, quarter), parent_row in parent_quarters.items():
                proxy_year = latest_available_proxy_year(available_years, year)
                if proxy_year is None:
                    continue
                weight_rows = weights.get((parent_area, sigungu_code, group_name, level, proxy_year), [])
                parent_value = float(parent_row["value"])
                estimated_sum = 0.0
                for weight in weight_rows:
                    estimate = parent_value * float(weight["share"])
                    estimated_sum += estimate
                    quarterly.append(
                        {
                            "source_region": source_region,
                            "parent_area_code": parent_area,
                            "sigungu_code": sigungu_code,
                            "sigungu_name": group_name,
                            "parent_sector_code": MANUFACTURING_PARENT,
                            "parent_sector_name": "제조업",
                            "detail_code": weight["detail_code"],
                            "detail_name": weight["detail_name"],
                            "detail_level": level,
                            "year": year,
                            "quarter": quarter,
                            "period": f"{year}Q{quarter}",
                            "estimated_gva": round(estimate, 6),
                            "parent_quarterly_gva": round(parent_value, 6),
                            "parent_status": parent_row.get("parent_status", ""),
                            "parent_method": parent_row.get("parent_method", ""),
                            "allocation_share": round(float(weight["share"]), 12),
                            "proxy_metric": weight["metric"],
                            "proxy_year": proxy_year,
                            "io_prior_code": weight.get("io_prior_code", ""),
                            "io_prior_name": weight.get("io_prior_name", ""),
                            "io_prior_year": weight.get("io_prior_year", ""),
                            "io_value_added_self_factor": weight.get("io_value_added_self_factor", ""),
                            "io_adjusted_proxy_value": round(float(weight.get("io_adjusted_proxy_value", 0.0)), 6),
                            "forecast_as_of": f"{year:04d}-{FORECAST_ORIGIN_MONTH:02d}-{FORECAST_ORIGIN_DAY:02d}",
                            "proxy_publication_lag_months": ANNUAL_PROXY_PUBLICATION_LAG_MONTHS,
                            "release_filter": "proxy year must be released before forecast_as_of",
                            "method": "lag-aware annual KSIC proxy share with ECOS IO prior within sigungu manufacturing quarterly GVA",
                        }
                    )
                    annual_key = (parent_area, sigungu_code, group_name, level, weight["detail_code"], year)
                    item = annual.setdefault(
                        annual_key,
                        {
                            "source_region": source_region,
                            "parent_area_code": parent_area,
                            "sigungu_code": sigungu_code,
                            "sigungu_name": group_name,
                            "parent_sector_code": MANUFACTURING_PARENT,
                            "parent_sector_name": "제조업",
                            "detail_code": weight["detail_code"],
                            "detail_name": weight["detail_name"],
                            "detail_level": level,
                            "year": year,
                            "estimated_annual_gva": 0.0,
                            "actual_proxy_value": weight["proxy_value"] if weight["metric"] == "value_added" and proxy_year == year else "",
                            "proxy_metric": weight["metric"],
                            "proxy_year": proxy_year,
                            "parent_status": parent_row.get("parent_status", ""),
                            "parent_method": parent_row.get("parent_method", ""),
                            "io_prior_code": weight.get("io_prior_code", ""),
                            "io_prior_name": weight.get("io_prior_name", ""),
                            "io_prior_year": weight.get("io_prior_year", ""),
                            "io_value_added_self_factor": weight.get("io_value_added_self_factor", ""),
                            "io_adjusted_proxy_value": round(float(weight.get("io_adjusted_proxy_value", 0.0)), 6),
                            "forecast_as_of": f"{year:04d}-{FORECAST_ORIGIN_MONTH:02d}-{FORECAST_ORIGIN_DAY:02d}",
                            "proxy_publication_lag_months": ANNUAL_PROXY_PUBLICATION_LAG_MONTHS,
                            "release_filter": "proxy year must be released before forecast_as_of",
                        },
                    )
                    item["estimated_annual_gva"] += estimate
                diag_key = (parent_area, sigungu_code, level, year)
                diag = diagnostics.setdefault(
                    diag_key,
                    {
                        "parent_area_code": parent_area,
                        "sigungu_code": sigungu_code,
                        "sigungu_name": group_name,
                        "detail_level": level,
                        "year": year,
                        "allocated_annual_sum": 0.0,
                        "parent_annual_sum": 0.0,
                        "parent_status": parent_row.get("parent_status", ""),
                    },
                )
                diag["allocated_annual_sum"] += estimated_sum
                diag["parent_annual_sum"] += parent_value

    annual_rows = []
    for row in annual.values():
        row["estimated_annual_gva"] = round(float(row["estimated_annual_gva"]), 6)
        actual = parse_number(row.get("actual_proxy_value"))
        if actual is not None and actual != 0:
            error = float(row["estimated_annual_gva"]) - actual
            row["proxy_error"] = round(error, 6)
            row["percent_proxy_error"] = round(error / actual * 100.0, 12)
        else:
            row["proxy_error"] = ""
            row["percent_proxy_error"] = ""
        annual_rows.append(row)

    diagnostic_rows = []
    for row in diagnostics.values():
        allocated = float(row["allocated_annual_sum"])
        parent_sum = float(row["parent_annual_sum"])
        error = allocated - parent_sum
        diagnostic_rows.append(
            {
                **row,
                "allocated_annual_sum": round(allocated, 6),
                "parent_annual_sum": round(parent_sum, 6),
                "constraint_error": round(error, 9),
                "absolute_constraint_error": round(abs(error), 9),
                "percent_constraint_error": round(error / parent_sum * 100.0, 12) if parent_sum else "",
            }
        )
    return quarterly, annual_rows, diagnostic_rows


def main() -> int:
    quarterly, annual, diagnostics = allocate()
    write_csv(PROCESSED_DIR / "detailed_industry_quarterly_estimates.csv", quarterly)
    write_csv(PROCESSED_DIR / "detailed_industry_annual_estimates.csv", annual)
    write_csv(PROCESSED_DIR / "detailed_industry_constraint_diagnostics.csv", diagnostics)
    print(f"detailed industry quarterly estimates: {len(quarterly)} rows")
    print(f"detailed industry annual estimates: {len(annual)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
