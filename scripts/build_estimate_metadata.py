from __future__ import annotations

from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, read_csv, write_csv


def row_value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key, "")
        if value != "":
            return value
    return ""


def metadata_row(
    *,
    dataset: str,
    row: dict[str, str],
    region_level: str,
    industry_level: str,
    time_level: str,
    benchmark_status: str,
    source_resolution: str,
    confidence_grade: str,
    method_note: str,
    value_type: str,
) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "area_code": row_value(row, "area_code", "parent_area_code", "source_region"),
        "area_name": row_value(row, "area_name", "source_region"),
        "sigungu_code": row_value(row, "sigungu_code"),
        "sigungu_name": row_value(row, "sigungu_name"),
        "emd_code": row_value(row, "emd_code"),
        "emd_name": row_value(row, "emd_name"),
        "sector_code": row_value(row, "sector_code", "parent_sector_code", "detail_code"),
        "sector_name": row_value(row, "sector_name", "parent_sector_name", "detail_name"),
        "detail_code": row_value(row, "detail_code"),
        "detail_name": row_value(row, "detail_name"),
        "year": row_value(row, "year", "target_year"),
        "quarter": row_value(row, "quarter"),
        "period": row_value(row, "period"),
        "region_level": region_level,
        "industry_level": industry_level,
        "time_level": time_level,
        "benchmark_status": benchmark_status,
        "source_resolution": source_resolution,
        "confidence_grade": confidence_grade,
        "value_type": value_type,
        "method_note": method_note,
        "constraint_error": row_value(row, "constraint_error", "absolute_constraint_error"),
    }


def write_metadata(
    source_filename: str,
    output_filename: str,
    *,
    dataset: str,
    region_level: str,
    industry_level: str,
    time_level: str,
    benchmark_status: str,
    source_resolution: str,
    confidence_grade: str,
    method_note: str,
    value_type: str,
) -> int:
    source = PROCESSED_DIR / source_filename
    rows = read_csv(source)
    metadata = [
        metadata_row(
            dataset=dataset,
            row=row,
            region_level=region_level,
            industry_level=industry_level,
            time_level=time_level,
            benchmark_status=benchmark_status,
            source_resolution=source_resolution,
            confidence_grade=confidence_grade,
            method_note=method_note,
            value_type=value_type,
        )
        for row in rows
    ]
    write_csv(PROCESSED_DIR / output_filename, metadata)
    return len(metadata)


def main() -> int:
    specs = [
        {
            "source_filename": "all_industries_quarterly_gva_estimates.csv",
            "output_filename": "all_industries_quarterly_gva_metadata.csv",
            "dataset": "sido_quarterly_gva",
            "region_level": "sido",
            "industry_level": "economic_activity",
            "time_level": "quarter",
            "benchmark_status": "benchmarked",
            "source_resolution": "official annual sido GRVA + quarterly indicators",
            "confidence_grade": "A",
            "value_type": "benchmarked_estimate",
            "method_note": "Proportional Denton allocation constrained to official annual sido GRVA.",
        },
        {
            "source_filename": "rolling_quarterly_gva_predictions.csv",
            "output_filename": "rolling_quarterly_gva_prediction_metadata.csv",
            "dataset": "rolling_sido_quarterly_gva",
            "region_level": "sido",
            "industry_level": "economic_activity",
            "time_level": "quarter",
            "benchmark_status": "extrapolated",
            "source_resolution": "prior official annual sido GRVA + current quarterly indicators",
            "confidence_grade": "B",
            "value_type": "rolling_prediction",
            "method_note": "One-year-ahead extrapolation using only prior annual benchmarks; validate where actual annual GRVA exists.",
        },
        {
            "source_filename": "sigungu_quarterly_gva_estimates.csv",
            "output_filename": "sigungu_quarterly_gva_metadata.csv",
            "dataset": "sigungu_quarterly_gva",
            "region_level": "sigungu",
            "industry_level": "economic_activity",
            "time_level": "quarter",
            "benchmark_status": "benchmarked",
            "source_resolution": "official annual sigungu GRVA + parent sido quarterly profile",
            "confidence_grade": "B",
            "value_type": "benchmarked_estimate",
            "method_note": "Proportional Denton allocation constrained to official annual sigungu GRVA; quarter profile inherits parent sido pattern.",
        },
        {
            "source_filename": "detailed_industry_quarterly_estimates.csv",
            "output_filename": "detailed_industry_quarterly_metadata.csv",
            "dataset": "sigungu_detailed_manufacturing_gva",
            "region_level": "sigungu",
            "industry_level": "ksic_detail",
            "time_level": "quarter",
            "benchmark_status": "proxy_allocated",
            "source_resolution": "sigungu manufacturing quarterly benchmark + KSIC annual proxy",
            "confidence_grade": "C",
            "value_type": "proxy_allocation_estimate",
            "method_note": "Allocate sigungu manufacturing quarterly GVA to KSIC detail using value added, employees, or establishments proxy shares.",
        },
        {
            "source_filename": "emd_quarterly_gva_estimates.csv",
            "output_filename": "emd_quarterly_gva_metadata.csv",
            "dataset": "emd_quarterly_gva",
            "region_level": "emd",
            "industry_level": "economic_activity",
            "time_level": "quarter",
            "benchmark_status": "proxy_allocated",
            "source_resolution": "sigungu quarterly benchmark + 2015 emd economic census proxy",
            "confidence_grade": "D",
            "value_type": "proxy_allocation_estimate",
            "method_note": "Allocate sigungu quarterly GVA to emd using fixed 2015 sales, employees, or establishments proxy shares.",
        },
        {
            "source_filename": "reci_quarterly_index.csv",
            "output_filename": "reci_quarterly_index_metadata.csv",
            "dataset": "reci_quarterly_index",
            "region_level": "sido",
            "industry_level": "all_reci_sectors",
            "time_level": "quarter",
            "benchmark_status": "benchmarked",
            "source_resolution": "sum of benchmarked sido industry quarterly GVA",
            "confidence_grade": "A",
            "value_type": "index",
            "method_note": "Aggregate benchmarked industry quarterly GVA and index to 2020 quarterly average = 100.",
        },
        {
            "source_filename": "reci_rolling_validation.csv",
            "output_filename": "reci_rolling_validation_metadata.csv",
            "dataset": "reci_rolling_validation",
            "region_level": "sido",
            "industry_level": "all_reci_sectors",
            "time_level": "annual",
            "benchmark_status": "validated_prediction",
            "source_resolution": "rolling predictions compared with official annual GRVA",
            "confidence_grade": "B",
            "value_type": "validation",
            "method_note": "Annualized rolling RECI predictions compared against actual annual GRVA where available.",
        },
    ]

    summary = []
    for spec in specs:
        count = write_metadata(**spec)
        summary.append(
            {
                "metadata_file": spec["output_filename"],
                "source_file": spec["source_filename"],
                "rows": count,
                "confidence_grade": spec["confidence_grade"],
                "benchmark_status": spec["benchmark_status"],
                "method_note": spec["method_note"],
            }
        )
    write_csv(PROCESSED_DIR / "estimate_metadata_summary.csv", summary)
    print(f"metadata files: {len(summary)}")
    print(f"metadata rows: {sum(int(row['rows']) for row in summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
