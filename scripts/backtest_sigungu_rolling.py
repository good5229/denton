from __future__ import annotations

from collections import defaultdict
from typing import Any

from denton_sigungu import SECTOR_NAME_MAP, canonical_region, load_province_codes, normalize_name
from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


MIN_BASE_YEAR = 2019


def load_sigungu_actual() -> dict[tuple[str, str, str, str, str, int], float]:
    province_codes = load_province_codes()
    out: dict[tuple[str, str, str, str, str, int], float] = {}
    for row in read_csv(PROCESSED_DIR / "expanded_sigungu_grva_real.csv"):
        source_region = canonical_region(row.get("source_region", ""))
        sigungu_name = canonical_region(row.get("c1_nm", ""))
        if sigungu_name == source_region or row.get("c1_id", "") == province_codes.get(source_region):
            continue
        sector = SECTOR_NAME_MAP.get(normalize_name(row.get("c2_nm", "")))
        value = parse_number(row.get("value"))
        year = parse_number(row.get("prd_de"))
        if not sector or value is None or value <= 0 or year is None:
            continue
        sector_code, sector_name = sector
        out[
            (
                source_region,
                row.get("c1_id", ""),
                row.get("c1_nm", ""),
                sector_code,
                sector_name,
                int(year),
            )
        ] = value
    return out


def load_parent_actual() -> dict[tuple[str, str, int], float]:
    out: dict[tuple[str, str, int], float] = {}
    for row in read_csv(PROCESSED_DIR / "annual_grva_real.csv"):
        value = parse_number(row.get("value"))
        year = parse_number(row.get("prd_de"))
        if value is None or value <= 0 or year is None:
            continue
        out[(canonical_region(row.get("c1_nm", "")), row.get("c2_id", ""), int(year))] = value
    return out


def load_parent_predictions() -> dict[tuple[str, str, int], dict[str, Any]]:
    out: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in read_csv(PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv"):
        year = parse_number(row.get("target_year"))
        value = parse_number(row.get("predicted_annual_gva"))
        if year is None or value is None:
            continue
        out[(row.get("area_name", ""), row.get("sector_code", ""), int(year))] = {
            "value": value,
            "method": row.get("method", ""),
            "train_start_year": row.get("train_start_year", ""),
            "train_end_year": row.get("train_end_year", ""),
        }
    return out


def latest_share(
    *,
    actual: dict[tuple[str, str, str, str, str, int], float],
    parent_actual: dict[tuple[str, str, int], float],
    source_region: str,
    sigungu_code: str,
    sigungu_name: str,
    sector_code: str,
    sector_name: str,
    target_year: int,
) -> dict[str, Any] | None:
    candidates = []
    for year in range(MIN_BASE_YEAR, target_year):
        child = actual.get((source_region, sigungu_code, sigungu_name, sector_code, sector_name, year))
        parent = parent_actual.get((source_region, sector_code, year))
        if child is None or parent is None or parent <= 0:
            continue
        candidates.append(
            {
                "base_year": year,
                "share": child / parent,
                "base_child_actual": child,
                "base_parent_actual": parent,
            }
        )
    return max(candidates, key=lambda row: row["base_year"]) if candidates else None


def backtest() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actual = load_sigungu_actual()
    parent_actual = load_parent_actual()
    parent_predictions = load_parent_predictions()
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for (source_region, sigungu_code, sigungu_name, sector_code, sector_name, target_year), actual_value in sorted(actual.items()):
        if target_year <= MIN_BASE_YEAR:
            continue
        parent_prediction = parent_predictions.get((source_region, sector_code, target_year))
        if not parent_prediction:
            skipped.append(
                {
                    "source_region": source_region,
                    "sigungu_code": sigungu_code,
                    "sigungu_name": sigungu_name,
                    "sector_code": sector_code,
                    "sector_name": sector_name,
                    "target_year": target_year,
                    "reason": "missing parent sido rolling annual prediction",
                }
            )
            continue
        share = latest_share(
            actual=actual,
            parent_actual=parent_actual,
            source_region=source_region,
            sigungu_code=sigungu_code,
            sigungu_name=sigungu_name,
            sector_code=sector_code,
            sector_name=sector_name,
            target_year=target_year,
        )
        if not share:
            skipped.append(
                {
                    "source_region": source_region,
                    "sigungu_code": sigungu_code,
                    "sigungu_name": sigungu_name,
                    "sector_code": sector_code,
                    "sector_name": sector_name,
                    "target_year": target_year,
                    "reason": "missing pre-target sigungu share",
                }
            )
            continue
        predicted = float(parent_prediction["value"]) * float(share["share"])
        error = predicted - actual_value
        rows.append(
            {
                "source_region": source_region,
                "sigungu_code": sigungu_code,
                "sigungu_name": sigungu_name,
                "sector_code": sector_code,
                "sector_name": sector_name,
                "target_year": target_year,
                "predicted_annual_gva": round(predicted, 6),
                "actual_annual_gva": round(actual_value, 6),
                "error": round(error, 6),
                "percent_error": round(error / actual_value * 100.0, 12) if actual_value else "",
                "absolute_percent_error": round(abs(error / actual_value) * 100.0, 12) if actual_value else "",
                "last_observed_share": round(float(share["share"]), 12),
                "share_base_year": share["base_year"],
                "share_base_sigungu_gva": round(float(share["base_child_actual"]), 6),
                "share_base_parent_gva": round(float(share["base_parent_actual"]), 6),
                "parent_predicted_annual_gva": round(float(parent_prediction["value"]), 6),
                "parent_method": parent_prediction["method"],
                "train_start_year": parent_prediction["train_start_year"],
                "train_end_year": parent_prediction["train_end_year"],
                "forecast_as_of": f"{target_year}-01-01",
                "release_filter": "target-year sigungu actual is held out; latest pre-target share only",
                "method": "latest pre-target sigungu-to-sido annual share applied to sido rolling annual prediction",
            }
        )
    return rows, skipped


def summarize(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row.get(key, "")) for key in keys)].append(row)
    out: list[dict[str, Any]] = []
    for key, items in sorted(groups.items()):
        abs_error_sum = sum(abs(float(row["error"])) for row in items)
        actual_sum = sum(abs(float(row["actual_annual_gva"])) for row in items)
        mape = sum(float(row["absolute_percent_error"]) for row in items) / len(items) if items else 0.0
        out.append(
            {
                **{field: value for field, value in zip(keys, key)},
                "comparison_count": len(items),
                "predicted_sum": round(sum(float(row["predicted_annual_gva"]) for row in items), 6),
                "actual_sum": round(sum(float(row["actual_annual_gva"]) for row in items), 6),
                "mape": round(mape, 6),
                "wmape": round(abs_error_sum / actual_sum * 100.0, 6) if actual_sum else "",
            }
        )
    return out


def main() -> int:
    rows, skipped = backtest()
    write_csv(PROCESSED_DIR / "sigungu_annual_rolling_backtest.csv", rows)
    write_csv(PROCESSED_DIR / "sigungu_annual_rolling_backtest_by_year.csv", summarize(rows, ["target_year"]))
    write_csv(PROCESSED_DIR / "sigungu_annual_rolling_backtest_by_sector.csv", summarize(rows, ["sector_code", "sector_name"]))
    write_csv(PROCESSED_DIR / "sigungu_annual_rolling_backtest_by_region.csv", summarize(rows, ["source_region"]))
    write_csv(PROCESSED_DIR / "sigungu_annual_rolling_backtest_skipped.csv", skipped)
    print(f"sigungu rolling backtest rows: {len(rows)}")
    print(f"skipped: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
