from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


def count_file(filename: str, year_field: str = "year") -> dict[str, Any]:
    path = PROCESSED_DIR / filename
    if not path.exists():
        return {"rows": 0, "min_year": "", "max_year": "", "status": "missing"}
    rows = read_csv(path)
    years: list[int] = []
    for row in rows:
        raw = row.get(year_field) or row.get("target_year") or str(row.get("period", ""))[:4]
        value = parse_number(raw)
        if value is not None:
            years.append(int(value))
    return {
        "rows": len(rows),
        "min_year": min(years) if years else "",
        "max_year": max(years) if years else "",
        "status": "available",
    }


def comparable_counts(filename: str, predicted_field: str, actual_field: str) -> dict[str, Any]:
    path = PROCESSED_DIR / filename
    if not path.exists():
        return {"comparison_count": 0, "mape": "", "wmape": ""}
    rows = read_csv(path)
    errors: list[float] = []
    abs_actual_sum = 0.0
    abs_error_sum = 0.0
    for row in rows:
        predicted = parse_number(row.get(predicted_field))
        actual = parse_number(row.get(actual_field))
        if predicted is None or actual is None or actual == 0:
            continue
        error = predicted - actual
        errors.append(abs(error / actual) * 100.0)
        abs_actual_sum += abs(actual)
        abs_error_sum += abs(error)
    return {
        "comparison_count": len(errors),
        "mape": round(sum(errors) / len(errors), 6) if errors else "",
        "wmape": round(abs_error_sum / abs_actual_sum * 100.0, 6) if abs_actual_sum else "",
    }


def detail_status_counts(filename: str) -> dict[str, int]:
    path = PROCESSED_DIR / filename
    if not path.exists():
        return {}
    counts: Counter[str] = Counter()
    for row in read_csv(path):
        counts[row.get("parent_status", "") or "unknown"] += 1
    return dict(counts)


def build_registry() -> list[dict[str, Any]]:
    specs = [
        {
            "registry_id": "sido_annual_large_sector",
            "level": "sido",
            "grain": "annual",
            "industry_depth": "large",
            "source_file": "rolling_annual_prediction_comparisons.csv",
            "value_field": "predicted_annual_gva",
            "actual_field": "actual_annual_gva",
            "actual_role": "official_actual",
            "validation_type": "direct_forecast_error",
            "confidence_floor": "B",
            "note": "시도·대분류 연간 공식 GRVA를 숨기고 rolling 방식으로 예측한 뒤 실제값과 비교 가능",
        },
        {
            "registry_id": "sido_quarter_large_sector",
            "level": "sido",
            "grain": "quarter",
            "industry_depth": "large",
            "source_file": "rolling_quarterly_gva_predictions.csv",
            "value_field": "predicted_gva",
            "actual_field": "",
            "actual_role": "partial_official_actual",
            "validation_type": "annual_sum_and_national_quarter_crosscheck",
            "confidence_floor": "B",
            "note": "시도별 산업 분기 actual은 제한적이며 전국 분기 GDP와 연간합 정합성 중심 검증",
        },
        {
            "registry_id": "sigungu_annual_large_sector_benchmark",
            "level": "sigungu",
            "grain": "annual",
            "industry_depth": "large",
            "source_file": "sigungu_denton_constraint_diagnostics.csv",
            "value_field": "allocated_annual_sum",
            "actual_field": "benchmark_annual_gva",
            "actual_role": "benchmark",
            "validation_type": "constraint_error",
            "confidence_floor": "B",
            "note": "시군구 연간 GRVA 벤치마크와 분기 배분합의 회계 정합성 검증",
        },
        {
            "registry_id": "sigungu_quarter_large_sector_estimate",
            "level": "sigungu",
            "grain": "quarter",
            "industry_depth": "large",
            "source_file": "sigungu_quarterly_gva_estimates.csv",
            "value_field": "estimated_gva",
            "actual_field": "",
            "actual_role": "unavailable",
            "validation_type": "parent_and_annual_constraint",
            "confidence_floor": "C",
            "note": "공식 시군구 분기 산업 GVA actual 부재. 연간 벤치마크와 상위 시도 분기 경로로 간접 검증",
        },
        {
            "registry_id": "sigungu_quarter_large_sector_forecast",
            "level": "sigungu",
            "grain": "quarter",
            "industry_depth": "large",
            "source_file": "sigungu_quarterly_gva_forecasts.csv",
            "value_field": "predicted_gva",
            "actual_field": "",
            "actual_role": "future_or_unavailable",
            "validation_type": "out_of_sample_parent_path",
            "confidence_floor": "C",
            "note": "최신 시군구 비중을 상위 시도 분기 예측 경로에 적용한 forecast. 실제 발표 전에는 직접 오차 검증 불가",
        },
        {
            "registry_id": "sigungu_quarter_manufacturing_detail",
            "level": "sigungu",
            "grain": "quarter",
            "industry_depth": "middle_small_class",
            "source_file": "detailed_industry_quarterly_estimates.csv",
            "value_field": "estimated_gva",
            "actual_field": "",
            "actual_role": "proxy",
            "validation_type": "parent_constraint_and_proxy_backtest",
            "confidence_floor": "C",
            "note": "제조업 중·소·세분류. 시군구 제조업 총량 제약과 광업제조업조사 proxy로 검증",
        },
        {
            "registry_id": "sigungu_quarter_service_detail",
            "level": "sigungu",
            "grain": "quarter",
            "industry_depth": "middle_small_class",
            "source_file": "service_detail_quarterly_estimates.csv",
            "value_field": "estimated_gva",
            "actual_field": "",
            "actual_role": "proxy",
            "validation_type": "parent_constraint_and_proxy_backtest",
            "confidence_floor": "C",
            "note": "서비스 중·소·세분류. 전국 서비스업생산지수 세부항목을 proxy로 사용",
        },
        {
            "registry_id": "emd_quarter_large_sector",
            "level": "emd",
            "grain": "quarter",
            "industry_depth": "large",
            "source_file": "emd_quarterly_gva_estimates.csv",
            "value_field": "estimated_gva",
            "actual_field": "",
            "actual_role": "proxy",
            "validation_type": "sigungu_parent_constraint_and_local_proxy",
            "confidence_floor": "D",
            "note": "읍면동 공식 GVA 부재. 경제총조사/사업체 proxy로 배분하며 일부 지역 자료 확보 시 외부 검증 가능",
        },
    ]

    registry: list[dict[str, Any]] = []
    for spec in specs:
        info = count_file(spec["source_file"])
        metric = comparable_counts(spec["source_file"], spec["value_field"], spec["actual_field"]) if spec["actual_field"] else {}
        status_counts = detail_status_counts(spec["source_file"])
        registry.append(
            {
                **spec,
                **info,
                "comparison_count": metric.get("comparison_count", ""),
                "mape": metric.get("mape", ""),
                "wmape": metric.get("wmape", ""),
                "benchmark_constrained_rows": status_counts.get("benchmark_constrained_estimate", ""),
                "out_of_sample_rows": status_counts.get("out_of_sample_forecast", ""),
            }
        )
    return registry


def summarize(registry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in registry:
        grouped[(row["level"], row["industry_depth"])].append(row)
    out: list[dict[str, Any]] = []
    for (level, depth), rows in sorted(grouped.items()):
        out.append(
            {
                "level": level,
                "industry_depth": depth,
                "registry_rows": len(rows),
                "source_rows": sum(int(parse_number(row.get("rows")) or 0) for row in rows),
                "direct_comparison_rows": sum(int(parse_number(row.get("comparison_count")) or 0) for row in rows),
                "actual_roles": ", ".join(sorted({row["actual_role"] for row in rows})),
                "validation_types": ", ".join(sorted({row["validation_type"] for row in rows})),
            }
        )
    return out


def main() -> int:
    registry = build_registry()
    write_csv(PROCESSED_DIR / "validation_registry.csv", registry)
    write_csv(PROCESSED_DIR / "validation_registry_summary.csv", summarize(registry))
    print(f"validation registry rows: {len(registry)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
