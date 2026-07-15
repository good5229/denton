from __future__ import annotations

from collections import defaultdict
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


INPUT_FILE = PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv"


def comparable_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(INPUT_FILE):
        predicted = parse_number(row.get("predicted_annual_gva"))
        actual = parse_number(row.get("actual_annual_gva"))
        error = parse_number(row.get("error"))
        ape = parse_number(row.get("absolute_percent_error"))
        if predicted is None or actual is None or actual == 0 or error is None or ape is None:
            continue
        item = dict(row)
        item["_predicted"] = predicted
        item["_actual"] = actual
        item["_error"] = error
        item["_ape"] = ape
        item["_abs_error"] = abs(error)
        rows.append(item)
    return rows


def summarize(rows: list[dict[str, Any]], group_fields: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row.get(field, "")) for field in group_fields)
        grouped[key].append(row)

    out: list[dict[str, Any]] = []
    for key, items in sorted(grouped.items()):
        actual_sum = sum(float(row["_actual"]) for row in items)
        predicted_sum = sum(float(row["_predicted"]) for row in items)
        error_sum = sum(float(row["_error"]) for row in items)
        abs_error_sum = sum(float(row["_abs_error"]) for row in items)
        mape = sum(float(row["_ape"]) for row in items) / len(items)
        signed_mpe = sum(float(row.get("percent_error", 0) or 0) for row in items) / len(items)
        row_out: dict[str, Any] = {field: value for field, value in zip(group_fields, key)}
        row_out.update(
            {
                "comparison_count": len(items),
                "predicted_sum": round(predicted_sum, 6),
                "actual_sum": round(actual_sum, 6),
                "error_sum": round(error_sum, 6),
                "absolute_error_sum": round(abs_error_sum, 6),
                "mape": round(mape, 6),
                "signed_mpe": round(signed_mpe, 6),
                "wmape": round(abs_error_sum / actual_sum * 100.0, 6) if actual_sum else "",
                "aggregate_percent_error": round(error_sum / actual_sum * 100.0, 6) if actual_sum else "",
            }
        )
        out.append(row_out)
    return out


def top_errors(rows: list[dict[str, Any]], limit: int = 100) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: (float(row["_ape"]), float(row["_abs_error"])), reverse=True)
    out: list[dict[str, Any]] = []
    for row in ordered[:limit]:
        out.append(
            {
                "rank": len(out) + 1,
                "area_code": row.get("area_code", ""),
                "area_name": row.get("area_name", ""),
                "sector_code": row.get("sector_code", ""),
                "sector_name": row.get("sector_name", ""),
                "target_year": row.get("target_year", ""),
                "method": row.get("method", ""),
                "predicted_annual_gva": round(float(row["_predicted"]), 6),
                "actual_annual_gva": round(float(row["_actual"]), 6),
                "error": round(float(row["_error"]), 6),
                "absolute_error": round(float(row["_abs_error"]), 6),
                "percent_error": row.get("percent_error", ""),
                "absolute_percent_error": round(float(row["_ape"]), 6),
            }
        )
    return out


def summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actual_sum = sum(float(row["_actual"]) for row in rows)
    abs_error_sum = sum(float(row["_abs_error"]) for row in rows)
    mape = sum(float(row["_ape"]) for row in rows) / len(rows) if rows else 0.0
    return [
        {
            "comparison_count": len(rows),
            "area_count": len({row.get("area_code", "") for row in rows}),
            "sector_count": len({row.get("sector_code", "") for row in rows}),
            "target_year_start": min((row.get("target_year", "") for row in rows), default=""),
            "target_year_end": max((row.get("target_year", "") for row in rows), default=""),
            "mape": round(mape, 6),
            "wmape": round(abs_error_sum / actual_sum * 100.0, 6) if actual_sum else "",
        }
    ]


def main() -> int:
    rows = comparable_rows()
    write_csv(PROCESSED_DIR / "rolling_backtest_summary.csv", summary(rows))
    write_csv(PROCESSED_DIR / "rolling_backtest_by_year.csv", summarize(rows, ["target_year"]))
    write_csv(PROCESSED_DIR / "rolling_backtest_by_region.csv", summarize(rows, ["area_code", "area_name"]))
    write_csv(PROCESSED_DIR / "rolling_backtest_by_sector.csv", summarize(rows, ["sector_code", "sector_name"]))
    write_csv(PROCESSED_DIR / "rolling_backtest_by_method.csv", summarize(rows, ["method"]))
    write_csv(PROCESSED_DIR / "rolling_backtest_error_matrix.csv", summarize(rows, ["area_code", "area_name", "sector_code", "sector_name"]))
    write_csv(PROCESSED_DIR / "rolling_backtest_top_errors.csv", top_errors(rows))
    print(f"comparable rows: {len(rows)}")
    print("wrote rolling backtest diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
