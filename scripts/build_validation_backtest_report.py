from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv


REPORT_PATH = ROOT / "reports" / "validation_backtest_summary.md"


def summarize_panel() -> list[dict[str, Any]]:
    rows = read_csv(PROCESSED_DIR / "modeling_panel_annual.csv")
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["level"], row["industry_depth"], row["actual_role"], row["value_role"])].append(row)
    out: list[dict[str, Any]] = []
    for (level, depth, actual_role, value_role), items in sorted(grouped.items()):
        comparable = [row for row in items if row.get("is_comparable") == "True"]
        abs_errors = [parse_number(row.get("absolute_percent_error")) for row in comparable]
        abs_errors = [value for value in abs_errors if value is not None]
        predicted_sum = sum(parse_number(row.get("predicted_value")) or 0.0 for row in comparable)
        actual_sum = sum(parse_number(row.get("actual_value")) or 0.0 for row in comparable)
        wmape = abs(predicted_sum - actual_sum) / actual_sum * 100.0 if actual_sum else ""
        out.append(
            {
                "level": level,
                "industry_depth": depth,
                "actual_role": actual_role,
                "value_role": value_role,
                "rows": len(items),
                "comparable_rows": len(comparable),
                "mape": round(sum(abs_errors) / len(abs_errors), 6) if abs_errors else "",
                "aggregate_percent_error": round((predicted_sum - actual_sum) / actual_sum * 100.0, 6) if actual_sum else "",
                "wmape_like": round(wmape, 6) if wmape != "" else "",
            }
        )
    return out


def top_official_errors(limit: int = 12) -> list[dict[str, Any]]:
    rows = [
        row
        for row in read_csv(PROCESSED_DIR / "modeling_panel_annual.csv")
        if row.get("actual_role") == "official_actual" and row.get("is_comparable") == "True"
    ]
    rows.sort(key=lambda row: parse_number(row.get("absolute_percent_error")) or -1, reverse=True)
    out: list[dict[str, Any]] = []
    for row in rows[:limit]:
        out.append(
            {
                "level": row["level"],
                "area_name": row["area_name"],
                "sector_name": row["sector_name"],
                "year": row["year"],
                "predicted_value": row["predicted_value"],
                "actual_value": row["actual_value"],
                "absolute_percent_error": row["absolute_percent_error"],
                "method": row["method"],
            }
        )
    return out


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return "_해당 없음_"
    header = "| " + " | ".join(fields) + " |"
    sep = "| " + " | ".join("---" for _ in fields) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join([header, sep, *body])


def write_report(summary: list[dict[str, Any]], top_errors: list[dict[str, Any]]) -> None:
    official = [row for row in summary if row["actual_role"] == "official_actual"]
    benchmark = [row for row in summary if row["actual_role"] == "benchmark"]
    proxy = [row for row in summary if row["actual_role"] in {"proxy", "proxy_actual", "proxy_unavailable"}]
    future = [row for row in summary if row["actual_role"] in {"future_or_unavailable", "unavailable"}]
    text = f"""# 레벨별 정확도 검증 요약

생성일: {date.today().isoformat()}

## 핵심 해석

현재 직접적인 예측 정확도는 `official_actual`과 비교 가능한 시도 연간 대분류에서 가장 강하게 검증된다. 시군구 연간 대분류의 낮은 오차는 예측 성능이 아니라 공식 연간 벤치마크와의 회계 정합성이다. 시군구 중분류·소분류와 읍면동은 아직 공식 actual이 없으므로 proxy 및 상위합 정합성 검증으로 관리해야 한다.

## Official Actual 비교

{md_table(official, ["level", "industry_depth", "value_role", "rows", "comparable_rows", "mape", "aggregate_percent_error", "wmape_like"])}

## Benchmark 정합성

{md_table(benchmark, ["level", "industry_depth", "value_role", "rows", "comparable_rows", "mape", "aggregate_percent_error", "wmape_like"])}

## Proxy 또는 미검증 구간

{md_table(proxy, ["level", "industry_depth", "actual_role", "value_role", "rows", "comparable_rows"])}

## Forecast Actual 미공표 구간

{md_table(future, ["level", "industry_depth", "actual_role", "value_role", "rows", "comparable_rows"])}

## Official Actual 기준 상위 오차

{md_table(top_errors, ["area_name", "sector_name", "year", "predicted_value", "actual_value", "absolute_percent_error"])}

## 다음 검증 과제

1. 시군구 대분류는 연간 actual을 숨기는 rolling backtest를 별도 구성해야 한다.
2. 중분류·소분류는 공식 actual 부재로 인해 제조업 proxy actual, 서비스업 세부지수, 상위합 정합성을 분리 평가해야 한다.
3. 읍면동은 서울 등 일부 지역의 외부 준actual을 확보해 proxy share의 안정성을 검증해야 한다.
4. ML 모델은 official actual 검증 구간을 주평가 대상으로 두고, benchmark/proxy 행은 낮은 가중치 또는 보조 진단으로 사용해야 한다.
"""
    REPORT_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    summary = summarize_panel()
    top_errors = top_official_errors()
    write_csv(PROCESSED_DIR / "validation_backtest_by_role.csv", summary)
    write_csv(PROCESSED_DIR / "validation_backtest_top_official_errors.csv", top_errors)
    write_report(summary, top_errors)
    print(f"validation backtest role rows: {len(summary)}")
    print(f"top official errors: {len(top_errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
