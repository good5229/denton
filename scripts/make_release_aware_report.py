from __future__ import annotations

from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv


FIGURE_DIR = ROOT / "reports" / "figures"
REPORT_PATH = ROOT / "reports" / "release_aware_backtest_report.md"


def esc(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt(value: Any, digits: int = 2) -> str:
    number = parse_number(value)
    if number is None:
        return "-"
    return f"{number:,.{digits}f}"


def pct(value: Any, digits: int = 2) -> str:
    number = parse_number(value)
    if number is None:
        return "-"
    return f"{number:,.{digits}f}%"


def svg_text(x: float, y: float, text: str, size: int = 14, weight: int = 600, fill: str = "#263447", anchor: str = "start") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(text)}</text>'


def svg_bar_chart(path: Path, title: str, rows: list[dict[str, Any]], label_key: str, value_keys: list[tuple[str, str, str]]) -> None:
    width, height = 1280, 720
    margin = {"left": 120, "right": 70, "top": 110, "bottom": 110}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    max_value = max(parse_number(row[key]) or 0 for row in rows for key, _, _ in value_keys)
    max_value = max(1.0, max_value * 1.18)
    group_w = plot_w / max(1, len(rows))
    bar_w = min(38, group_w / (len(value_keys) + 1.2))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="1280" height="720" fill="#f7f9fc"/>',
        svg_text(60, 58, title, 28, 800, "#17202a"),
        svg_text(60, 86, "예측 시점에 공표된 자료만 사용한 backtest 기준", 15, 600, "#627084"),
    ]
    for idx in range(6):
        value = max_value * idx / 5
        y = margin["top"] + plot_h - plot_h * value / max_value
        parts.append(f'<line x1="{margin["left"]}" y1="{y:.1f}" x2="{width - margin["right"]}" y2="{y:.1f}" stroke="#dbe3ee" stroke-width="1"/>')
        parts.append(svg_text(106, y + 5, f"{value:.0f}%", 12, 600, "#728094", "end"))
    for i, row in enumerate(rows):
        x0 = margin["left"] + i * group_w + group_w / 2
        for j, (key, legend, color) in enumerate(value_keys):
            value = parse_number(row.get(key)) or 0.0
            h = plot_h * value / max_value
            x = x0 - (len(value_keys) * bar_w) / 2 + j * bar_w
            y = margin["top"] + plot_h - h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 4:.1f}" height="{h:.1f}" rx="4" fill="{color}"/>')
            if h > 24:
                parts.append(svg_text(x + (bar_w - 4) / 2, y - 7, f"{value:.1f}", 11, 700, "#263447", "middle"))
        label = str(row[label_key])
        parts.append(svg_text(x0, margin["top"] + plot_h + 32, label, 13, 700, "#263447", "middle"))
    legend_x = margin["left"]
    for key, legend, color in value_keys:
        parts.append(f'<rect x="{legend_x}" y="640" width="18" height="18" rx="4" fill="{color}"/>')
        parts.append(svg_text(legend_x + 26, 655, legend, 13, 700, "#263447"))
        legend_x += 185
    parts.append(svg_text(width - 70, 682, "단위: %", 12, 600, "#728094", "end"))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def svg_horizontal_bar(path: Path, title: str, rows: list[dict[str, Any]], label_key: str, value_key: str) -> None:
    width, height = 1280, 720
    margin = {"left": 310, "right": 80, "top": 110, "bottom": 80}
    plot_w = width - margin["left"] - margin["right"]
    max_value = max(parse_number(row[value_key]) or 0 for row in rows) * 1.15
    bar_h = 34
    gap = 18
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="1280" height="720" fill="#f7f9fc"/>',
        svg_text(60, 58, title, 28, 800, "#17202a"),
        svg_text(60, 86, "산업별 연간 예측치와 실제 공표값 비교", 15, 600, "#627084"),
    ]
    for i, row in enumerate(rows):
        y = margin["top"] + i * (bar_h + gap)
        value = parse_number(row[value_key]) or 0.0
        w = plot_w * value / max_value if max_value else 0
        parts.append(svg_text(margin["left"] - 18, y + 23, str(row[label_key])[:24], 14, 700, "#263447", "end"))
        parts.append(f'<rect x="{margin["left"]}" y="{y}" width="{plot_w}" height="{bar_h}" rx="6" fill="#edf2f8"/>')
        parts.append(f'<rect x="{margin["left"]}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="6" fill="#c8564a"/>')
        parts.append(svg_text(margin["left"] + w + 12, y + 23, f"{value:.1f}%", 14, 800, "#263447"))
    parts.append(svg_text(width - 80, 682, "MAPE 기준 상위 10개 산업", 12, 600, "#728094", "end"))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def svg_energy_comparison(path: Path, summary: dict[str, Any], feature_counts: list[tuple[str, int]]) -> None:
    width, height = 1280, 720
    baseline_mape = parse_number(summary.get("baseline_mape")) or 0
    adjusted_mape = parse_number(summary.get("adjusted_mape")) or 0
    baseline_wmape = parse_number(summary.get("baseline_wmape")) or 0
    adjusted_wmape = parse_number(summary.get("adjusted_wmape")) or 0
    max_value = max(baseline_mape, adjusted_mape, baseline_wmape, adjusted_wmape) * 1.25
    bars = [
        ("Baseline MAPE", baseline_mape, "#2f72c8"),
        ("Adjusted MAPE", adjusted_mape, "#c8564a"),
        ("Baseline WMAPE", baseline_wmape, "#2f72c8"),
        ("Adjusted WMAPE", adjusted_wmape, "#c8564a"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="1280" height="720" fill="#f7f9fc"/>',
        svg_text(60, 58, "전기·가스 외생변수 보정 결과", 28, 800, "#17202a"),
        svg_text(60, 86, "as-of 기준에서 공개된 최신 4개 분기만 사용", 15, 600, "#627084"),
    ]
    x0, y0, plot_h = 110, 145, 380
    bar_w = 105
    for i, (label, value, color) in enumerate(bars):
        x = x0 + i * 155
        h = plot_h * value / max_value
        y = y0 + plot_h - h
        parts.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" rx="8" fill="{color}"/>')
        parts.append(svg_text(x + bar_w / 2, y - 12, f"{value:.2f}%", 15, 800, "#263447", "middle"))
        for line_idx, line in enumerate(label.split(" ")):
            parts.append(svg_text(x + bar_w / 2, y0 + plot_h + 30 + line_idx * 18, line, 13, 700, "#263447", "middle"))
    parts.append(f'<rect x="780" y="145" width="400" height="290" rx="10" fill="#ffffff" stroke="#d9e0ea"/>')
    parts.append(svg_text(810, 188, "채택 판단", 22, 800, "#17202a"))
    parts.append(svg_text(810, 232, f"MAPE 변화: {fmt(summary.get('mape_delta'), 2)}%p", 20, 800, "#c8564a"))
    parts.append(svg_text(810, 272, f"채택 여부: {summary.get('adopt_augmented_indicator')}", 18, 800, "#263447"))
    parts.append(svg_text(810, 312, f"비교 건수: {summary.get('comparison_count')}", 16, 700, "#627084"))
    parts.append(svg_text(810, 352, "결론: 외생변수 자동 보정은 보류", 16, 800, "#263447"))
    parts.append(svg_text(810, 402, "선택 feature 빈도", 16, 800, "#17202a"))
    for idx, (feature, count) in enumerate(feature_counts[:3]):
        parts.append(svg_text(830, 432 + idx * 24, f"{feature[:34]}: {count}", 13, 700, "#627084"))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    header = "| " + " | ".join(label for _, label in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in selected:
        body.append("| " + " | ".join(esc(row.get(key, "")) for key, _ in columns) + " |")
    return "\n".join([header, sep, *body])


def build_report() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    yearly = read_csv(PROCESSED_DIR / "rolling_backtest_by_year.csv")
    sector = read_csv(PROCESSED_DIR / "rolling_backtest_by_sector.csv")
    energy_rows = read_csv(PROCESSED_DIR / "energy_augmented_backtest.csv")
    energy_summary = read_csv(PROCESSED_DIR / "energy_augmented_summary.csv")[0]
    release_calendar = read_csv(PROCESSED_DIR / "energy_augmented_release_calendar.csv")
    detail_diag = read_csv(PROCESSED_DIR / "detailed_industry_constraint_diagnostics.csv")
    ecos_cross = read_csv(PROCESSED_DIR / "ecos_kosis_gdp_crosscheck.csv")

    yearly_fig = FIGURE_DIR / "fig07_release_aware_yearly_errors.svg"
    sector_fig = FIGURE_DIR / "fig08_release_aware_sector_mape.svg"
    energy_fig = FIGURE_DIR / "fig09_release_aware_energy_adjustment.svg"

    svg_bar_chart(
        yearly_fig,
        "연도별 예측 오차",
        yearly,
        "target_year",
        [("mape", "MAPE", "#2f72c8"), ("wmape", "WMAPE", "#3e8f50")],
    )
    top_sector = sorted(sector, key=lambda row: parse_number(row.get("mape")) or -1, reverse=True)[:10]
    svg_horizontal_bar(sector_fig, "산업별 MAPE 상위", top_sector, "sector_name", "mape")
    feature_counts = Counter(row.get("selected_feature", "baseline") for row in energy_rows).most_common()
    svg_energy_comparison(energy_fig, energy_summary, feature_counts)

    comparable_count = sum(int(row["comparison_count"]) for row in yearly)
    overall_mape = mean(parse_number(row["mape"]) or 0 for row in yearly)
    overall_wmape = sum((parse_number(row["absolute_error_sum"]) or 0) for row in yearly) / sum((parse_number(row["actual_sum"]) or 0) for row in yearly) * 100
    max_detail_error = max((parse_number(row.get("absolute_constraint_error")) or 0) for row in detail_diag)
    ecos_same = sum(1 for row in ecos_cross if row.get("comparison_status") == "same_value")
    ecos_base_diff = sum(1 for row in ecos_cross if row.get("comparison_status") == "different_index_base_or_table_version")

    yearly_table = [
        {
            "year": row["target_year"],
            "n": row["comparison_count"],
            "mape": pct(row["mape"]),
            "wmape": pct(row["wmape"]),
            "aggregate_percent_error": pct(row["aggregate_percent_error"], 3),
        }
        for row in yearly
    ]
    sector_table = [
        {
            "sector": row["sector_name"],
            "n": row["comparison_count"],
            "mape": pct(row["mape"]),
            "wmape": pct(row["wmape"]),
            "aggregate_percent_error": pct(row["aggregate_percent_error"], 3),
        }
        for row in top_sector
    ]
    energy_table = [
        {"metric": "Baseline MAPE", "value": pct(energy_summary["baseline_mape"])},
        {"metric": "Adjusted MAPE", "value": pct(energy_summary["adjusted_mape"])},
        {"metric": "MAPE delta", "value": f"{fmt(energy_summary['mape_delta'])}%p"},
        {"metric": "Baseline WMAPE", "value": pct(energy_summary["baseline_wmape"])},
        {"metric": "Adjusted WMAPE", "value": pct(energy_summary["adjusted_wmape"])},
        {"metric": "Adopt", "value": energy_summary["adopt_augmented_indicator"]},
    ]
    release_table = [
        {
            "indicator": row["indicator"],
            "source": row["source"],
            "frequency": row["frequency"],
            "lag": row["publication_lag_months"],
            "rule": row["application_rule"],
        }
        for row in release_calendar[:8]
    ]

    report = f"""# 공표시점 기준 예측 오차 보고서

## 요약

이 보고서는 예측 시점에 이미 공표된 데이터만 사용했을 때의 예측값과 실제 공표값 차이를 정리한다. 사후에 알게 된 연간 proxy나 목표연도 전체 외생변수 평균은 사용하지 않는다.

- 전체 rolling backtest 비교 건수: `{comparable_count:,}`건
- 연도별 MAPE 평균: `{overall_mape:.2f}%`
- 전체 WMAPE: `{overall_wmape:.2f}%`
- 전기·가스 외생변수 보정 채택 여부: `{energy_summary['adopt_augmented_indicator']}`
- 상세산업 배분 총량 제약 최대 오차: `{max_detail_error:.8f}`
- ECOS 실질 GDP와 KOSIS 실질 GDP 일치: `{ecos_same:,}`건
- 디플레이터 기준연도/표체계 차이로 분류: `{ecos_base_diff:,}`건

## 적용 기준

예측 기준일은 연간 backtest의 경우 목표연도 1월 1일로 둔다. 분기 또는 연간 입력자료는 `관측기간 종료일 + 공표 지연 개월 수 < forecast_as_of` 조건을 만족할 때만 사용할 수 있다.

예를 들어 목표연도 2024년을 2024-01-01에 예측한다면, 1개월 지연 분기자료는 2023Q3까지 사용할 수 있고 2023Q4는 사용할 수 없다. 연간 proxy가 12개월 지연으로 공개된다고 보면, 2024년 예측에는 2022년 proxy까지만 사용할 수 있다.

## 연도별 오차

![연도별 예측 오차](figures/{yearly_fig.name})

{markdown_table(yearly_table, [('year', '연도'), ('n', '비교 건수'), ('mape', 'MAPE'), ('wmape', 'WMAPE'), ('aggregate_percent_error', '총량 오차율')])}

연도별로 보면 MAPE는 2019년에 가장 낮고 2023년에 가장 높다. 다만 총량 오차율은 대체로 절대값 2% 내외에 머물러, 개별 지역·산업 조합의 오차가 서로 상쇄되는 경향이 있다.

## 산업별 오차

![산업별 MAPE 상위](figures/{sector_fig.name})

{markdown_table(sector_table, [('sector', '산업'), ('n', '비교 건수'), ('mape', 'MAPE'), ('wmape', 'WMAPE'), ('aggregate_percent_error', '총량 오차율')])}

산업별로는 광업과 전기·가스 부문 오차가 크다. 전기·가스는 총량 기준 오차율은 거의 0에 가까우나 지역별 분포 오차가 커서 MAPE와 WMAPE가 높다. 이 때문에 ECOS 가격·환율 변수를 붙여 보정 실험을 진행했다.

## 전기·가스 외생변수 보정 실험

![전기·가스 외생변수 보정 결과](figures/{energy_fig.name})

{markdown_table(energy_table, [('metric', '지표'), ('value', '값')])}

보정 모델은 `energy_exogenous_with_ecos_quarterly.csv`의 FRED·ECOS 외생변수를 사용하되, 목표연도 1월 1일 현재 공표된 최신 4개 분기만 feature로 사용했다. 이 조건에서 보정 MAPE가 기준 MAPE보다 높아졌으므로 자동 보정 factor는 채택하지 않는다.

선택 feature 빈도:

{markdown_table([{'feature': feature, 'count': count} for feature, count in feature_counts], [('feature', '선택 feature'), ('count', '건수')])}

## 공표 지연 적용 테이블

{markdown_table(release_table, [('indicator', '지표'), ('source', '출처'), ('frequency', '주기'), ('lag', '공표 지연(월)'), ('rule', '적용 규칙')])}

현재 외생변수는 1개월 지연 분기자료로 처리했다. 실제 공식 공표 일정이 확인되는 항목은 이후 `publication_lag_months`를 더 세분화해 조정해야 한다.

## 상세산업 배분 검증

상세산업 추정은 연간 KSIC proxy가 목표연도 예측 기준일 전에 공표된 경우에만 사용한다. 또한 ECOS 산업연관표의 자기부문 부가가치유발계수를 구조 prior로 곱한 뒤, 시군구 제조업 총량에 다시 정규화한다.

| 항목 | 값 |
|---|---:|
| 상세산업 제약 진단 행 | {len(detail_diag):,} |
| 최대 총량 제약 오차 | {max_detail_error:.8f} |
| 적용 방식 | lag-aware proxy × ECOS IO prior |

이 검증은 예측값이 실제 상세산업 GVA와 일치한다는 뜻이 아니다. 하위 상세산업 총합이 예측 기준의 시군구 제조업 총량과 일관되도록 유지된다는 회계 제약 검증이다.

## 해석

이번 결과는 두 가지를 보여준다.

1. 공표 시점을 엄격히 지키면 사용할 수 있는 정보량이 줄어들고, 사후 자료를 쓴 것처럼 성능이 좋아 보이지 않는다.
2. ECOS 외생변수와 산업연관표는 유용하지만, actual이 아니라 각각 `exogenous`와 `prior`로 다뤄야 한다.

따라서 현재 기준에서는 전기·가스 외생변수 자동 보정은 보류하고, 상세산업 배분에는 ECOS IO prior를 구조 가중치로 사용하는 것이 합리적이다.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    build_report()
    print(f"wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
