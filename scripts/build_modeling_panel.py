from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


def num(value: Any) -> float | None:
    return parse_number(value)


def pct_error(predicted: float | None, actual: float | None) -> float | str:
    if predicted is None or actual is None or actual == 0:
        return ""
    return round((predicted - actual) / actual * 100.0, 12)


def abs_pct_error(predicted: float | None, actual: float | None) -> float | str:
    value = pct_error(predicted, actual)
    return round(abs(float(value)), 12) if value != "" else ""


def base_row(
    *,
    source_file: str,
    level: str,
    grain: str,
    industry_depth: str,
    area_code: str,
    area_name: str,
    parent_area_code: str = "",
    sigungu_code: str = "",
    sigungu_name: str = "",
    emd_code: str = "",
    emd_name: str = "",
    sector_code: str = "",
    sector_name: str = "",
    parent_sector_code: str = "",
    parent_sector_name: str = "",
    detail_code: str = "",
    detail_name: str = "",
    detail_level: str = "",
    year: str = "",
    predicted: Any = "",
    actual: Any = "",
    actual_role: str = "",
    value_role: str = "",
    benchmark_status: str = "",
    proxy_metric: str = "",
    proxy_year: str = "",
    method: str = "",
    as_of_policy: str = "",
) -> dict[str, Any]:
    predicted_value = num(predicted)
    actual_value = num(actual)
    return {
        "source_file": source_file,
        "level": level,
        "grain": grain,
        "industry_depth": industry_depth,
        "area_code": area_code,
        "area_name": area_name,
        "parent_area_code": parent_area_code,
        "sigungu_code": sigungu_code,
        "sigungu_name": sigungu_name,
        "emd_code": emd_code,
        "emd_name": emd_name,
        "sector_code": sector_code,
        "sector_name": sector_name,
        "parent_sector_code": parent_sector_code,
        "parent_sector_name": parent_sector_name,
        "detail_code": detail_code,
        "detail_name": detail_name,
        "detail_level": detail_level,
        "year": year,
        "predicted_value": round(predicted_value, 6) if predicted_value is not None else "",
        "actual_value": round(actual_value, 6) if actual_value is not None else "",
        "actual_role": actual_role,
        "value_role": value_role,
        "is_comparable": bool(predicted_value is not None and actual_value is not None and actual_value != 0),
        "percent_error": pct_error(predicted_value, actual_value),
        "absolute_percent_error": abs_pct_error(predicted_value, actual_value),
        "benchmark_status": benchmark_status,
        "proxy_metric": proxy_metric,
        "proxy_year": proxy_year,
        "method": method,
        "as_of_policy": as_of_policy,
    }


def sido_annual_rows() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv"):
        out.append(
            base_row(
                source_file="rolling_annual_prediction_comparisons.csv",
                level="sido",
                grain="annual",
                industry_depth="large",
                area_code=row.get("area_code", ""),
                area_name=row.get("area_name", ""),
                sector_code=row.get("sector_code", ""),
                sector_name=row.get("sector_name", ""),
                year=row.get("target_year", ""),
                predicted=row.get("predicted_annual_gva"),
                actual=row.get("actual_annual_gva"),
                actual_role="official_actual",
                value_role="forecast",
                benchmark_status="rolling_out_of_sample",
                method=row.get("method", ""),
                as_of_policy="target-year Jan 1; only released indicators/proxies are eligible",
            )
        )
    return out


def sigungu_annual_rows() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "sigungu_denton_constraint_diagnostics.csv"):
        out.append(
            base_row(
                source_file="sigungu_denton_constraint_diagnostics.csv",
                level="sigungu",
                grain="annual",
                industry_depth="large",
                area_code=row.get("sigungu_code", ""),
                area_name=row.get("sigungu_name", ""),
                parent_area_code=row.get("parent_area_code", ""),
                sigungu_code=row.get("sigungu_code", ""),
                sigungu_name=row.get("sigungu_name", ""),
                sector_code=row.get("sector_code", ""),
                sector_name=row.get("sector_name", ""),
                year=row.get("year", ""),
                predicted=row.get("estimated_annual_sum"),
                actual=row.get("benchmark_annual_gva"),
                actual_role="benchmark",
                value_role="benchmarked_allocation",
                benchmark_status="benchmark_constrained_estimate",
                method="annual benchmark constrained Denton allocation",
                as_of_policy="benchmark period is known; not an out-of-sample forecast",
            )
        )
    for row in read_csv(PROCESSED_DIR / "sigungu_annual_gva_forecasts.csv"):
        out.append(
            base_row(
                source_file="sigungu_annual_gva_forecasts.csv",
                level="sigungu",
                grain="annual",
                industry_depth="large",
                area_code=row.get("sigungu_code", ""),
                area_name=row.get("sigungu_name", ""),
                parent_area_code=row.get("parent_area_code", ""),
                sigungu_code=row.get("sigungu_code", ""),
                sigungu_name=row.get("sigungu_name", ""),
                sector_code=row.get("sector_code", ""),
                sector_name=row.get("sector_name", ""),
                year=row.get("year", ""),
                predicted=row.get("predicted_annual_gva"),
                actual=row.get("actual_annual_gva"),
                actual_role="future_or_unavailable",
                value_role="forecast",
                benchmark_status=row.get("benchmark_status", ""),
                method=row.get("method", ""),
                as_of_policy="target-year Jan 1; latest available sigungu share only",
            )
        )
    return out


def manufacturing_detail_rows() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "detailed_industry_annual_estimates.csv"):
        out.append(
            base_row(
                source_file="detailed_industry_annual_estimates.csv",
                level="sigungu",
                grain="annual",
                industry_depth=row.get("detail_level", "detail"),
                area_code=row.get("sigungu_code", ""),
                area_name=row.get("sigungu_name", ""),
                parent_area_code=row.get("parent_area_code", ""),
                sigungu_code=row.get("sigungu_code", ""),
                sigungu_name=row.get("sigungu_name", ""),
                sector_code=row.get("detail_code", ""),
                sector_name=row.get("detail_name", ""),
                parent_sector_code=row.get("parent_sector_code", ""),
                parent_sector_name=row.get("parent_sector_name", ""),
                detail_code=row.get("detail_code", ""),
                detail_name=row.get("detail_name", ""),
                detail_level=row.get("detail_level", ""),
                year=row.get("year", ""),
                predicted=row.get("estimated_annual_gva"),
                actual=row.get("actual_proxy_value"),
                actual_role="proxy_actual" if row.get("actual_proxy_value") else "proxy_unavailable",
                value_role="proxy_allocation",
                benchmark_status=row.get("parent_status", ""),
                proxy_metric=row.get("proxy_metric", ""),
                proxy_year=row.get("proxy_year", ""),
                method=row.get("method", "manufacturing detail allocation"),
                as_of_policy=row.get("release_filter", ""),
            )
        )
    return out


def service_detail_rows() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "service_detail_annual_estimates.csv"):
        out.append(
            base_row(
                source_file="service_detail_annual_estimates.csv",
                level="sigungu",
                grain="annual",
                industry_depth=row.get("detail_level", "detail"),
                area_code=row.get("sigungu_code", ""),
                area_name=row.get("sigungu_name", ""),
                parent_area_code=row.get("parent_area_code", ""),
                sigungu_code=row.get("sigungu_code", ""),
                sigungu_name=row.get("sigungu_name", ""),
                sector_code=row.get("detail_code", ""),
                sector_name=row.get("detail_name", ""),
                parent_sector_code=row.get("parent_sector_code", ""),
                parent_sector_name=row.get("parent_sector_name", ""),
                detail_code=row.get("detail_code", ""),
                detail_name=row.get("detail_name", ""),
                detail_level=row.get("detail_level", ""),
                year=row.get("year", ""),
                predicted=row.get("estimated_annual_gva"),
                actual="",
                actual_role="proxy",
                value_role="proxy_allocation",
                benchmark_status=row.get("parent_status", ""),
                proxy_metric=row.get("proxy_metric", ""),
                method=row.get("method", "service detail allocation"),
                as_of_policy="released service detail index only where prediction mode applies",
            )
        )
    return out


def emd_annual_rows() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "emd_annual_gva_estimates.csv"):
        out.append(
            base_row(
                source_file="emd_annual_gva_estimates.csv",
                level="emd",
                grain="annual",
                industry_depth="large",
                area_code=row.get("emd_code", ""),
                area_name=row.get("emd_name", ""),
                parent_area_code=row.get("parent_area_code", ""),
                sigungu_code=row.get("sigungu_code", ""),
                sigungu_name=row.get("sigungu_name", ""),
                emd_code=row.get("emd_code", ""),
                emd_name=row.get("emd_name", ""),
                sector_code=row.get("sector_code", ""),
                sector_name=row.get("sector_name", ""),
                year=row.get("year", ""),
                predicted=row.get("estimated_annual_gva"),
                actual="",
                actual_role="proxy",
                value_role="proxy_allocation",
                benchmark_status="proxy_allocated",
                proxy_metric=row.get("proxy_metric", ""),
                proxy_year=row.get("proxy_year", ""),
                method=row.get("method", ""),
                as_of_policy="fixed available emd proxy; official emd GVA unavailable",
            )
        )
    return out


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["level"], row["grain"], row["industry_depth"])].append(row)
    out: list[dict[str, Any]] = []
    for (level, grain, depth), items in sorted(grouped.items()):
        comparable = [row for row in items if row["is_comparable"]]
        errors = [float(row["absolute_percent_error"]) for row in comparable if row["absolute_percent_error"] != ""]
        roles = Counter(row["actual_role"] for row in items)
        out.append(
            {
                "level": level,
                "grain": grain,
                "industry_depth": depth,
                "rows": len(items),
                "comparable_rows": len(comparable),
                "mape": round(sum(errors) / len(errors), 6) if errors else "",
                "actual_roles": ", ".join(f"{key}:{value}" for key, value in sorted(roles.items())),
            }
        )
    return out


def main() -> int:
    rows = (
        sido_annual_rows()
        + sigungu_annual_rows()
        + manufacturing_detail_rows()
        + service_detail_rows()
        + emd_annual_rows()
    )
    rows.sort(key=lambda row: (row["level"], row["area_code"], row["sector_code"], row["year"]))
    write_csv(PROCESSED_DIR / "modeling_panel_annual.csv", rows)
    write_csv(PROCESSED_DIR / "modeling_panel_summary.csv", summarize(rows))
    print(f"modeling panel annual rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
