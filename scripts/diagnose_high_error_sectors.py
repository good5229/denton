from __future__ import annotations

from collections import defaultdict
from typing import Any

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv


TARGET_SECTORS = {
    "A00": "농업 임업 및 어업",
    "B00": "광업",
    "D00": "전기 가스 증기 및 공기 조절 공급업",
}
REPORT_PATH = ROOT / "reports" / "high_error_sector_diagnostics.md"


def summarize(rows: list[dict[str, str]], keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key, "") for key in keys)].append(row)
    out: list[dict[str, Any]] = []
    for key, items in sorted(groups.items()):
        abs_errors = [parse_number(row.get("absolute_percent_error")) for row in items]
        abs_errors = [value for value in abs_errors if value is not None]
        actual_sum = sum(abs(parse_number(row.get("actual_annual_gva")) or 0.0) for row in items)
        abs_error_sum = sum(abs(parse_number(row.get("error")) or 0.0) for row in items)
        out.append(
            {
                **{field: value for field, value in zip(keys, key)},
                "comparison_count": len(items),
                "mape": round(sum(abs_errors) / len(abs_errors), 6) if abs_errors else "",
                "wmape": round(abs_error_sum / actual_sum * 100.0, 6) if actual_sum else "",
                "actual_sum": round(actual_sum, 6),
            }
        )
    return out


def high_error_rows() -> list[dict[str, str]]:
    rows = [
        row
        for row in read_csv(PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv")
        if row.get("sector_code") in TARGET_SECTORS and parse_number(row.get("actual_annual_gva")) not in {None, 0}
    ]
    rows.sort(key=lambda row: parse_number(row.get("absolute_percent_error")) or -1, reverse=True)
    return rows


def energy_augmented_summary() -> list[dict[str, Any]]:
    path = PROCESSED_DIR / "energy_augmented_backtest.csv"
    if not path.exists():
        return []
    rows = read_csv(path)
    out: list[dict[str, Any]] = []
    for field, label in [
        ("baseline_absolute_percent_error", "baseline"),
        ("adjusted_absolute_percent_error", "energy_exogenous_adjusted"),
    ]:
        values = [parse_number(row.get(field)) for row in rows]
        values = [value for value in values if value is not None]
        out.append(
            {
                "sector_code": "D00",
                "model": label,
                "comparison_count": len(values),
                "mape": round(sum(values) / len(values), 6) if values else "",
            }
        )
    return out


def recommendations() -> list[dict[str, Any]]:
    return [
        {
            "sector_code": "A00",
            "sector_name": TARGET_SECTORS["A00"],
            "issue": "기후·작황·지역 품목 구조 영향이 커서 단순 생산지수/전국 분기 share만으로 지역 변동 설명이 제한됨",
            "recommended_model": "baseline Denton 유지 + 농업 특화 proxy 보강",
            "candidate_features": "농산물 생산량, 재배면적, 축산 사육두수, 기상재해, 지역 농업 총조사 proxy",
            "leakage_rule": "target year에 아직 공표되지 않은 작황·총조사 자료는 사용 금지",
        },
        {
            "sector_code": "B00",
            "sector_name": TARGET_SECTORS["B00"],
            "issue": "규모가 작은 지역이 많아 MAPE가 폭발하고, 광산 개폐·품목별 가격 충격에 민감함",
            "recommended_model": "지역별 최근 share shrinkage + 품목/광산 활동 proxy",
            "candidate_features": "광업 생산지수 세부항목, 광산 생산량, 원자재 가격, 사업체수 변화",
            "leakage_rule": "소표본 지역은 전국/권역 평균으로 shrinkage하고 target 이후 사업체 변화를 학습에 넣지 않음",
        },
        {
            "sector_code": "D00",
            "sector_name": TARGET_SECTORS["D00"],
            "issue": "유가·석탄·환율·발전원 구성과 지역 설비 구조에 민감함",
            "recommended_model": "전기가스 전용 외생변수 residual correction",
            "candidate_features": "유가, 석탄가격, 환율, 전력판매량, 발전량, 발전원별 비중",
            "leakage_rule": "forecast_as_of 이전에 공표된 분기 exogenous만 사용",
        },
    ]


def write_report(by_sector: list[dict[str, Any]], energy: list[dict[str, Any]], recs: list[dict[str, Any]]) -> None:
    lines = [
        "# 고오차 산업 진단",
        "",
        "## 대상",
        "",
        "Official actual 기준 상위 오차에 반복적으로 등장한 농림어업(`A00`), 광업(`B00`), 전기·가스(`D00`)를 별도 진단했다.",
        "",
        "## 시도 연간 official actual 기준 성능",
        "",
        "| sector | count | MAPE | WMAPE |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in by_sector:
        lines.append(f"| {row['sector_code']} {row['sector_name']} | {row['comparison_count']} | {row['mape']} | {row['wmape']} |")
    lines.extend(["", "## 전기·가스 외생변수 보정 실험", "", "| model | count | MAPE |", "| --- | ---: | ---: |"])
    for row in energy:
        lines.append(f"| {row['model']} | {row['comparison_count']} | {row['mape']} |")
    lines.extend(["", "## 권고", "", "| sector | recommended model | leakage rule |", "| --- | --- | --- |"])
    for row in recs:
        lines.append(f"| {row['sector_code']} | {row['recommended_model']} | {row['leakage_rule']} |")
    lines.extend(
        [
            "",
            "## 결론",
            "",
            "전체 산업에 동일한 ML 보정을 적용하기보다, baseline이 안정적인 산업은 Denton/indicator 방식을 유지하고 고오차 산업에는 산업별 전용 feature와 shrinkage를 적용하는 방식이 더 안전하다.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows = high_error_rows()
    by_sector = summarize(rows, ["sector_code", "sector_name"])
    by_area_sector = summarize(rows, ["area_code", "area_name", "sector_code", "sector_name"])
    energy = energy_augmented_summary()
    recs = recommendations()
    write_csv(PROCESSED_DIR / "high_error_sector_summary.csv", by_sector)
    write_csv(PROCESSED_DIR / "high_error_sector_by_area.csv", by_area_sector)
    write_csv(PROCESSED_DIR / "high_error_sector_energy_augmented_summary.csv", energy)
    write_csv(PROCESSED_DIR / "high_error_sector_recommendations.csv", recs)
    write_report(by_sector, energy, recs)
    print(f"high-error rows: {len(rows)}")
    print(f"sector summary rows: {len(by_sector)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
