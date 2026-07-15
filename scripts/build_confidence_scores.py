from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


def grade_from_metrics(mape: float | None, wmape: float | None, count: int, aggregate_abs_error: float | None) -> tuple[str, int, str]:
    if count < 3 or mape is None or wmape is None:
        return "D", 25, "비교 가능한 actual 관측치가 부족함"
    score = 100
    if mape <= 5:
        score -= 0
    elif mape <= 10:
        score -= 12
    elif mape <= 20:
        score -= 28
    else:
        score -= 45
    if wmape <= 3:
        score -= 0
    elif wmape <= 6:
        score -= 8
    elif wmape <= 12:
        score -= 20
    else:
        score -= 32
    if aggregate_abs_error is not None:
        if aggregate_abs_error <= 2:
            score -= 0
        elif aggregate_abs_error <= 5:
            score -= 5
        elif aggregate_abs_error <= 10:
            score -= 12
        else:
            score -= 22
    if count < 5:
        score -= 10
    score = max(0, min(100, score))
    if score >= 85:
        return "A", score, "낮은 오차와 충분한 backtest 관측치"
    if score >= 70:
        return "B", score, "검증 가능하나 일부 조합에서 오차 관리 필요"
    if score >= 50:
        return "C", score, "탐색적 활용 가능, 지역·산업별 추가 검증 필요"
    return "D", score, "오차가 크거나 검증 근거가 부족해 참고용으로 제한"


def build_sido_scores() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "rolling_backtest_error_matrix.csv"):
        count = int(parse_number(row.get("comparison_count")) or 0)
        mape = parse_number(row.get("mape"))
        wmape = parse_number(row.get("wmape"))
        agg = parse_number(row.get("aggregate_percent_error"))
        grade, score, reason = grade_from_metrics(mape, wmape, count, abs(agg) if agg is not None else None)
        rows.append(
            {
                "level": "sido",
                "grain": "annual",
                "area_code": row.get("area_code", ""),
                "area_name": row.get("area_name", ""),
                "sector_code": row.get("sector_code", ""),
                "sector_name": row.get("sector_name", ""),
                "confidence_grade": grade,
                "confidence_score": score,
                "comparison_count": count,
                "mape": row.get("mape", ""),
                "wmape": row.get("wmape", ""),
                "aggregate_percent_error": row.get("aggregate_percent_error", ""),
                "value_role": "forecast_vs_actual",
                "confidence_reason": reason,
                "as_of_policy": "target-year Jan 1; only released indicators/proxies are eligible",
            }
        )
    return rows


def build_level_scores() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    summary = read_csv(PROCESSED_DIR / "rolling_backtest_summary.csv")
    if summary:
        row = summary[0]
        mape = parse_number(row.get("mape"))
        wmape = parse_number(row.get("wmape"))
        count = int(parse_number(row.get("comparison_count")) or 0)
        grade, score, reason = grade_from_metrics(mape, wmape, count, None)
        out.append(
            {
                "level": "sido",
                "grain": "annual",
                "area_code": "__ALL__",
                "area_name": "전체 시도",
                "sector_code": "__ALL__",
                "sector_name": "전체 산업",
                "confidence_grade": grade,
                "confidence_score": score,
                "comparison_count": count,
                "mape": row.get("mape", ""),
                "wmape": row.get("wmape", ""),
                "aggregate_percent_error": "",
                "value_role": "forecast_vs_actual",
                "confidence_reason": reason,
                "as_of_policy": "target-year Jan 1; only released indicators/proxies are eligible",
            }
        )
    static_rows = [
        ("sido", "quarter", "B", 72, "분기 actual은 전국 GDP만 직접 비교 가능하고 시도별 공식 분기 GVA는 부재", "forecast_path"),
        ("sigungu", "annual", "B", 70, "연간 actual/벤치마크와 예측 구간이 혼재하며 공식 시군구 분기 actual은 부재", "benchmark_or_forecast"),
        ("sigungu", "quarter", "C", 58, "시군구 연간 벤치마크를 부모 시도 분기경로로 배분한 추정", "allocation"),
        ("detail", "annual", "C", 52, "lag-aware KSIC proxy와 ECOS IO prior 기반 세부산업 배분", "proxy_allocation"),
        ("detail", "quarter", "C", 50, "시군구 제조업 분기 총량을 세부산업 proxy로 배분", "proxy_allocation"),
        ("emd", "annual", "D", 35, "읍면동 공식 GVA actual 부재, 경제총조사/사업체 proxy 기반", "proxy_allocation"),
        ("emd", "quarter", "D", 32, "읍면동 공식 분기 GVA actual 부재, 하향 proxy 배분", "proxy_allocation"),
    ]
    for level, grain, grade, score, reason, role in static_rows:
        out.append(
            {
                "level": level,
                "grain": grain,
                "area_code": "__ALL__",
                "area_name": "전체",
                "sector_code": "__ALL__",
                "sector_name": "전체",
                "confidence_grade": grade,
                "confidence_score": score,
                "comparison_count": "",
                "mape": "",
                "wmape": "",
                "aggregate_percent_error": "",
                "value_role": role,
                "confidence_reason": reason,
                "as_of_policy": "released-data-only where prediction mode applies",
            }
        )
    return out


def summarize_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["level"], row["grain"])].append(row)
    for (level, grain), items in sorted(grouped.items()):
        counts = Counter(row["confidence_grade"] for row in items)
        scores = [parse_number(row.get("confidence_score")) for row in items if parse_number(row.get("confidence_score")) is not None]
        out.append(
            {
                "level": level,
                "grain": grain,
                "rows": len(items),
                "grade_a": counts.get("A", 0),
                "grade_b": counts.get("B", 0),
                "grade_c": counts.get("C", 0),
                "grade_d": counts.get("D", 0),
                "avg_confidence_score": round(mean(scores), 6) if scores else "",
            }
        )
    return out


def main() -> int:
    rows = build_level_scores() + build_sido_scores()
    rows.sort(key=lambda row: (row["level"], row["grain"], row["area_code"], row["sector_code"]))
    write_csv(PROCESSED_DIR / "estimate_confidence_scores.csv", rows)
    write_csv(PROCESSED_DIR / "estimate_confidence_summary.csv", summarize_scores(rows))
    print(f"confidence score rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
