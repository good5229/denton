from __future__ import annotations

from collections import defaultdict
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


TARGET_YEARS = {2023, 2024, 2025}


def parent_key(row: dict[str, str]) -> tuple[str, str, int, int]:
    return (
        row.get("parent_area_code", ""),
        row.get("sector_code", ""),
        int(row.get("year", 0)),
        int(row.get("quarter", 0)),
    )


def load_parent_history() -> dict[tuple[str, str, int, int], float]:
    totals: dict[tuple[str, str, int, int], float] = defaultdict(float)
    for row in read_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv"):
        value = parse_number(row.get("estimated_gva"))
        if value is None:
            continue
        totals[parent_key(row)] += value
    return totals


def load_last_shares(parent_history: dict[tuple[str, str, int, int], float]) -> dict[tuple[str, str, str, int], dict[str, Any]]:
    shares: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for row in read_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv"):
        year = int(row.get("year", 0))
        quarter = int(row.get("quarter", 0))
        parent_total = parent_history.get(parent_key(row))
        value = parse_number(row.get("estimated_gva"))
        if not parent_total or value is None:
            continue
        key = (row.get("sigungu_code", ""), row.get("sector_code", ""), row.get("parent_area_code", ""), quarter)
        current = shares.get(key)
        if current and int(current["base_year"]) >= year:
            continue
        shares[key] = {
            "source_region": row.get("source_region", ""),
            "parent_area_code": row.get("parent_area_code", ""),
            "sigungu_code": row.get("sigungu_code", ""),
            "sigungu_name": row.get("sigungu_name", ""),
            "sector_code": row.get("sector_code", ""),
            "sector_name": row.get("sector_name", ""),
            "quarter": quarter,
            "share": value / parent_total,
            "base_year": year,
            "base_sigungu_gva": value,
            "base_parent_gva": parent_total,
        }
    return shares


def load_parent_forecasts() -> dict[tuple[str, str, int, int], dict[str, Any]]:
    out: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for row in read_csv(PROCESSED_DIR / "rolling_quarterly_gva_predictions.csv"):
        year = int(row.get("target_year", 0))
        quarter = int(row.get("quarter", 0))
        if year not in TARGET_YEARS:
            continue
        value = parse_number(row.get("predicted_gva"))
        if value is None:
            continue
        key = (row.get("area_code", ""), row.get("sector_code", ""), year, quarter)
        out[key] = {
            "parent_area_code": row.get("area_code", ""),
            "sector_code": row.get("sector_code", ""),
            "year": year,
            "quarter": quarter,
            "period": row.get("period", ""),
            "parent_predicted_gva": value,
            "parent_method": row.get("method", ""),
            "train_start_year": row.get("train_start_year", ""),
            "train_end_year": row.get("train_end_year", ""),
        }
    return out


def forecast() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    parent_history = load_parent_history()
    shares = load_last_shares(parent_history)
    parent_forecasts = load_parent_forecasts()
    quarterly: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for share in shares.values():
        for year in sorted(TARGET_YEARS):
            forecast_parent = parent_forecasts.get((share["parent_area_code"], share["sector_code"], year, share["quarter"]))
            if not forecast_parent:
                skipped.append(
                    {
                        "sigungu_code": share["sigungu_code"],
                        "sigungu_name": share["sigungu_name"],
                        "sector_code": share["sector_code"],
                        "year": year,
                        "quarter": share["quarter"],
                        "reason": "missing parent rolling quarterly forecast",
                    }
                )
                continue
            value = float(forecast_parent["parent_predicted_gva"]) * float(share["share"])
            quarterly.append(
                {
                    "source_region": share["source_region"],
                    "parent_area_code": share["parent_area_code"],
                    "sigungu_code": share["sigungu_code"],
                    "sigungu_name": share["sigungu_name"],
                    "sector_code": share["sector_code"],
                    "sector_name": share["sector_name"],
                    "year": year,
                    "quarter": share["quarter"],
                    "period": forecast_parent["period"],
                    "predicted_gva": round(value, 6),
                    "actual_quarterly_gva": "",
                    "parent_predicted_gva": round(float(forecast_parent["parent_predicted_gva"]), 6),
                    "last_observed_share": round(float(share["share"]), 12),
                    "share_base_year": share["base_year"],
                    "share_base_sigungu_gva": round(float(share["base_sigungu_gva"]), 6),
                    "share_base_parent_gva": round(float(share["base_parent_gva"]), 6),
                    "method": "last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast",
                    "parent_method": forecast_parent["parent_method"],
                    "benchmark_status": "out_of_sample_forecast",
                }
            )

    annual_groups: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in quarterly:
        key = (row["sigungu_code"], row["sector_code"], int(row["year"]))
        item = annual_groups.setdefault(
            key,
            {
                "source_region": row["source_region"],
                "parent_area_code": row["parent_area_code"],
                "sigungu_code": row["sigungu_code"],
                "sigungu_name": row["sigungu_name"],
                "sector_code": row["sector_code"],
                "sector_name": row["sector_name"],
                "year": row["year"],
                "predicted_annual_gva": 0.0,
                "actual_annual_gva": "",
                "method": "sum of quarterly out-of-sample forecasts",
                "benchmark_status": "out_of_sample_forecast",
            },
        )
        item["predicted_annual_gva"] += float(row["predicted_gva"])
    annual = []
    for row in annual_groups.values():
        row["predicted_annual_gva"] = round(float(row["predicted_annual_gva"]), 6)
        annual.append(row)
    return quarterly, annual, skipped


def main() -> int:
    quarterly, annual, skipped = forecast()
    write_csv(PROCESSED_DIR / "sigungu_quarterly_gva_forecasts.csv", quarterly)
    write_csv(PROCESSED_DIR / "sigungu_annual_gva_forecasts.csv", annual)
    write_csv(PROCESSED_DIR / "sigungu_gva_forecast_skipped.csv", skipped)
    write_csv(
        PROCESSED_DIR / "sigungu_gva_forecast_summary.csv",
        [
            {
                "quarterly_rows": len(quarterly),
                "annual_rows": len(annual),
                "skipped_rows": len(skipped),
                "target_years": ",".join(str(year) for year in sorted(TARGET_YEARS)),
            }
        ],
    )
    print(f"sigungu forecast quarterly rows: {len(quarterly)}")
    print(f"sigungu forecast annual rows: {len(annual)}")
    print(f"skipped: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
