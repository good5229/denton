#!/usr/bin/env python3
"""Phase68: middle-industry GVA prediction accuracy.

This is the performance question the poster/report should answer:

    How accurately did we estimate each middle KSIC industry's GVA?

The metric deliberately does NOT treat accounting reconciliation to an upper
control total as prediction accuracy.  It compares a middle industry's hidden
actual structure with the middle value implied by aggregated lower-industry
estimates, converted to 2023 GVA amounts.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
INFILE = DATA / "phase64_hierarchical_aggregate_validation" / "phase64_small_to_middle_aggregate_validation_detail.csv"
OUTDIR = DATA / "phase68_middle_industry_accuracy"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase68_middle_industry_accuracy.md"


KSIC_MIDDLE_NAME = {
    "01": "농업",
    "02": "임업",
    "10": "식료품 제조업",
    "11": "음료 제조업",
    "13": "섬유제품 제조업",
    "14": "의복·모피 제조업",
    "15": "가죽·가방·신발 제조업",
    "16": "목재·나무제품 제조업",
    "17": "펄프·종이 제조업",
    "18": "인쇄·기록매체 복제업",
    "19": "코크스·석유정제품 제조업",
    "20": "화학물질·화학제품 제조업",
    "21": "의약품 제조업",
    "22": "고무·플라스틱 제조업",
    "23": "비금속 광물제품 제조업",
    "24": "1차 금속 제조업",
    "25": "금속가공제품 제조업",
    "26": "전자부품·컴퓨터 제조업",
    "27": "의료·정밀기기 제조업",
    "28": "전기장비 제조업",
    "29": "기계·장비 제조업",
    "30": "자동차·트레일러 제조업",
    "31": "기타 운송장비 제조업",
    "32": "가구 제조업",
    "33": "기타 제품 제조업",
    "34": "산업용 기계 수리업",
    "35": "전기·가스 공급업",
    "36": "수도업",
    "37": "하수·폐수 처리업",
    "38": "폐기물 처리·재생업",
    "39": "환경 정화·복원업",
    "41": "종합 건설업",
    "42": "전문직별 공사업",
    "45": "자동차·부품 판매업",
    "46": "도매·상품중개업",
    "47": "소매업",
    "49": "육상운송업",
    "50": "수상 운송업",
    "51": "항공 운송업",
    "52": "창고·운송관련 서비스업",
    "55": "숙박업",
    "56": "음식점·주점업",
    "58": "출판업",
    "59": "영상·오디오 제작업",
    "60": "방송업",
    "61": "우편·통신업",
    "62": "컴퓨터·시스템통합업",
    "63": "정보서비스업",
    "64": "금융업",
    "65": "보험·연금업",
    "66": "금융·보험 관련 서비스업",
    "68": "부동산업",
    "70": "연구개발업",
    "71": "전문 서비스업",
    "72": "건축·엔지니어링 서비스업",
    "73": "과학기술 서비스업",
    "74": "사업시설 관리업",
    "75": "사업지원 서비스업",
    "76": "임대업",
    "84": "공공행정",
    "85": "교육 서비스업",
    "86": "보건업",
    "87": "사회복지 서비스업",
    "90": "창작·예술 서비스업",
    "91": "스포츠·오락 서비스업",
    "94": "협회·단체",
    "95": "개인용품 수리업",
    "96": "기타 개인 서비스업",
}


def parent_letters(parent_section: str) -> list[str]:
    parent_section = str(parent_section)
    if parent_section == "ERS":
        return ["E", "R", "S"]
    if parent_section == "MN0":
        return ["M", "N"]
    return [parent_section[0]]


def large_gva_by_code(city: str) -> dict[str, float]:
    path = (
        DATA / "partial_stats_phase41_all_ksic_multiresolution_cube.parquet"
        if city == "고양시"
        else DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet"
    )
    cube = pd.read_parquet(path, columns=["industry_level", "industry_code", "time_level", "period", "geo_level", "estimated_gva"])
    large = cube[
        cube.industry_level.eq("대분류")
        & cube.time_level.eq("연")
        & cube.period.astype(str).eq("2023")
        & cube.geo_level.eq("시")
    ].copy()
    return large.groupby(large.industry_code.astype(str)).estimated_gva.sum().to_dict()


def fmt_eok(value: float) -> str:
    return f"{value:,.0f}"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int = 20) -> str:
    if df.empty:
        return "\n해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(token in label for token in ("억원", "%", "순위")) else "---" for _, label in cols) + " |")
    for _, row in df.head(limit).iterrows():
        vals = []
        for key, _ in cols:
            value = row[key]
            if isinstance(value, float):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INFILE)
    maps = {city: large_gva_by_code(city) for city in sorted(df.city.unique())}
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    df["middle_label"] = np.where(
        df.middle_name.fillna("").astype(str).str.len().gt(0),
        df.middle_name,
        df.middle_code.map(KSIC_MIDDLE_NAME).fillna(df.middle_code),
    )
    df["parent_gva_eok"] = df.apply(
        lambda row: sum(maps[row.city].get(letter, 0.0) for letter in parent_letters(row.parent_section)) / 100,
        axis=1,
    )
    df = df[df.actual_middle_share.between(0.001, 0.999)].copy()
    df["actual_gva_eok"] = df.actual_middle_share * df.parent_gva_eok
    df["predicted_gva_eok"] = df.predicted_small_aggregated_share * df.parent_gva_eok
    df["error_gva_eok"] = (df.predicted_gva_eok - df.actual_gva_eok).abs()
    df["error_rate_pct"] = df.error_gva_eok / df.actual_gva_eok.replace(0, np.nan) * 100
    df["signed_error_gva_eok"] = df.predicted_gva_eok - df.actual_gva_eok
    df["direction"] = np.where(df.signed_error_gva_eok > 0, "과대", "과소")
    df["accuracy_grade"] = pd.cut(
        df.error_rate_pct,
        bins=[-np.inf, 5, 10, 20, 50, np.inf],
        labels=["5% 이하", "5~10%", "10~20%", "20~50%", "50% 초과"],
    ).astype(str)
    df = df.sort_values(["city", "error_gva_eok"], ascending=[True, False])

    detail_cols = [
        "city",
        "parent_section",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "predicted_gva_eok",
        "error_gva_eok",
        "error_rate_pct",
        "signed_error_gva_eok",
        "direction",
        "accuracy_grade",
        "actual_middle_share",
        "predicted_small_aggregated_share",
    ]
    df[detail_cols].to_csv(OUTDIR / "phase68_middle_industry_accuracy_detail.csv", index=False, encoding="utf-8-sig")

    summary_rows = []
    for city, sub in df.groupby("city"):
        summary_rows.append(
            {
                "city": city,
                "middle_cells": int(len(sub)),
                "actual_sum_eok": round(float(sub.actual_gva_eok.sum()), 3),
                "error_sum_eok": round(float(sub.error_gva_eok.sum()), 3),
                "wape_pct": round(float(sub.error_gva_eok.sum() / sub.actual_gva_eok.sum() * 100), 3),
                "median_error_rate_pct": round(float(sub.error_rate_pct.median()), 3),
                "p90_error_rate_pct": round(float(sub.error_rate_pct.quantile(0.9)), 3),
                "within_5pct_cells": int(sub.error_rate_pct.le(5).sum()),
                "within_10pct_cells": int(sub.error_rate_pct.le(10).sum()),
                "over_50pct_cells": int(sub.error_rate_pct.gt(50).sum()),
                "largest_error_industry": str(sub.iloc[0].middle_label),
                "largest_error_eok": round(float(sub.iloc[0].error_gva_eok), 3),
                "largest_error_rate_pct": round(float(sub.iloc[0].error_rate_pct), 3),
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUTDIR / "phase68_middle_industry_accuracy_summary.csv", index=False, encoding="utf-8-sig")

    good = df.sort_values(["city", "error_rate_pct"], ascending=[True, True]).groupby("city").head(8)
    bad = df.sort_values(["city", "error_gva_eok"], ascending=[True, False]).groupby("city").head(8)
    first_metal = df[df.middle_code.eq("24")].copy()

    report = f"""# 중분류 산업별 GVA 추정 정확도

## 목적

궁극적으로 설명해야 할 대상은 `각 산업별 총부가가치(GVA)를 얼마나 정확히 추정했는가`다. 따라서 이 보고서는 통제총량을 맞춘 뒤의 회계잔차가 아니라, 중분류 산업별 실제 환산액과 추정 환산액을 직접 비교한다.

## 단위와 정의

- 실제: `2023년 대분류 GVA × 중분류 actual 비중`
- 추정: `2023년 대분류 GVA × 소분류 추정값의 중분류 합산 비중`
- 오차: `|추정 - 실제|`
- 오차율: `오차 / 실제 × 100`
- 단위: 억원

통제총량 보정은 배포 산출물의 상위합계를 맞추는 회계정합화 절차이며, 예측 정확도 성과로 해석하지 않는다.

## 전체 요약

{md_table(summary, [("city", "지역"), ("middle_cells", "중분류 셀"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_rate_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("largest_error_industry", "최대오차 산업"), ("largest_error_eok", "최대오차 억원")])}

## 핵심 사례: 1차 금속 제조업

{md_table(first_metal, [("city", "지역"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("direction", "방향")])}

포항시는 1차 금속 제조업이 실제 47,010억 원 규모인데 추정은 15,774억 원으로 31,237억 원 과소추정된다. 이 항목은 포항 산업구조의 핵심이므로, 포스터에서 가장 중요한 취약 사례로 표시해야 한다.

## 오차가 작은 중분류

{md_table(good, [("city", "지역"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 16)}

## 금액 기준 오차가 큰 중분류

{md_table(bad, [("city", "지역"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("direction", "방향")], 16)}

## 개선 방향

- 포항 1차 금속 제조업은 사업체·종사자 중심 배분으로는 대규모 제철 생산 구조를 복원하지 못한다. 공장 면적, 산업용 전력, 철강 생산·출하, 항만 물동량, 산단 대규모 사업장 가중치를 결합해야 한다.
- 고양시는 보건·사회복지, 운수·창고, 건설업에서 금액 오차가 크다. 시설 이용량, 버스·물류, 건축 인허가·착공·사용승인 자료를 업종별로 분리해야 한다.
- 포스터에서는 “보정후 0”이 아니라 `실제·추정·오차(억원·%)`를 제시해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase68_middle_industry_accuracy_detail.csv")
    print(OUTDIR / "phase68_middle_industry_accuracy_summary.csv")


if __name__ == "__main__":
    main()
