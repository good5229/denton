#!/usr/bin/env python3
"""Phase69: prioritize middle-industry error reduction.

Not every industry can or should receive a bespoke model.  This script turns
the middle-industry GVA accuracy table into an error-reduction portfolio:

- Tier 1: high monetary-error / structurally important industries requiring
  specialized indicators.
- Tier 2: sector-family models shared by several industries.
- Tier 3: common allocation model, monitored with aggregate validation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
INFILE = DATA / "phase68_middle_industry_accuracy" / "phase68_middle_industry_accuracy_detail.csv"
OUTDIR = DATA / "phase69_error_reduction_strategy"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase69_error_reduction_strategy.md"


FAMILY_RULES = {
    "metal_heavy_manufacturing": {
        "codes": {"24", "25", "29", "34"},
        "label": "철강·금속·기계 제조",
        "indicators": "공장면적·산업용 전력·산단 대형사업장·철강/기계 출하",
    },
    "construction": {
        "codes": {"41", "42"},
        "label": "건설",
        "indicators": "건축허가·착공·사용승인 면적, 공사종류별 기성",
    },
    "health_welfare": {
        "codes": {"86", "87"},
        "label": "보건·사회복지",
        "indicators": "병상·의료기관 종별·장기요양 정원·복지시설 이용",
    },
    "transport_logistics": {
        "codes": {"49", "52"},
        "label": "운수·창고",
        "indicators": "버스승하차·창고면적·물류시설·화물/항만 물동량",
    },
    "commerce": {
        "codes": {"46", "47"},
        "label": "도소매",
        "indicators": "상권 업종밀도·사업체 규모·유동인구·소매 인허가",
    },
    "food_manufacturing": {
        "codes": {"10"},
        "label": "식료품 제조",
        "indicators": "식품공장 규모·농수산 가공시설·출하/수출입 보조지표",
    },
    "professional_business": {
        "codes": {"70", "71", "75"},
        "label": "전문·사업지원",
        "indicators": "법인·고용보험·지식서비스 사업체 규모·공공계약",
    },
    "finance_services": {
        "codes": {"61", "65", "66"},
        "label": "통신·금융 보조서비스",
        "indicators": "본점/지점 규모·종사자·사업체 규모 보정",
    },
    "personal_leisure": {
        "codes": {"91", "96"},
        "label": "여가·개인서비스",
        "indicators": "인허가 월변화·시설면적·상권/인구 접근성",
    },
}


def family_for(code: str) -> tuple[str, str, str]:
    code = str(code).zfill(2)
    for key, rule in FAMILY_RULES.items():
        if code in rule["codes"]:
            return key, rule["label"], rule["indicators"]
    return "common", "공통모델", "사업체·종사자·인허가·공간분포 공통 배분"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int = 20) -> str:
    if df.empty:
        return "\n해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(token in label for token in ("억원", "%", "순위")) else "---" for _, label in cols) + " |")
    for _, row in df.head(limit).iterrows():
        vals = []
        for key, _ in cols:
            val = row[key]
            if isinstance(val, float):
                vals.append(f"{val:,.1f}")
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INFILE)
    rows = []
    for city, sub in df.groupby("city"):
        sub = sub.sort_values("error_gva_eok", ascending=False).copy()
        total_error = sub.error_gva_eok.sum()
        sub["rank_by_error"] = range(1, len(sub) + 1)
        sub["error_share_pct"] = sub.error_gva_eok / total_error * 100
        sub["cum_error_share_pct"] = sub.error_share_pct.cumsum()
        for row in sub.itertuples(index=False):
            family_key, family_label, indicators = family_for(row.middle_code)
            if row.cum_error_share_pct <= 70 or row.rank_by_error <= 10:
                tier = "T1 특화 우선"
            elif family_key != "common" and row.error_rate_pct > 30:
                tier = "T2 업종군 보강"
            else:
                tier = "T3 공통모델 유지"
            rows.append(
                {
                    **row._asdict(),
                    "family_key": family_key,
                    "family_label": family_label,
                    "recommended_indicators": indicators,
                    "priority_tier": tier,
                }
            )

    out = pd.DataFrame(rows)
    out.to_csv(OUTDIR / "phase69_error_reduction_strategy_detail.csv", index=False, encoding="utf-8-sig")

    family = (
        out.groupby(["city", "priority_tier", "family_label", "recommended_indicators"], as_index=False)
        .agg(
            industries=("middle_code", "count"),
            error_gva_eok=("error_gva_eok", "sum"),
            actual_gva_eok=("actual_gva_eok", "sum"),
        )
        .sort_values(["city", "priority_tier", "error_gva_eok"], ascending=[True, True, False])
    )
    family["error_share_within_city_pct"] = family.error_gva_eok / family.groupby("city").error_gva_eok.transform("sum") * 100
    family.to_csv(OUTDIR / "phase69_error_reduction_strategy_by_family.csv", index=False, encoding="utf-8-sig")

    top = out[out.priority_tier.eq("T1 특화 우선")].sort_values(["city", "error_gva_eok"], ascending=[True, False])
    summary_rows = []
    for city, sub in out.groupby("city"):
        t1 = sub[sub.priority_tier.eq("T1 특화 우선")]
        summary_rows.append(
            {
                "city": city,
                "total_middle_cells": len(sub),
                "t1_cells": len(t1),
                "t1_error_gva_eok": t1.error_gva_eok.sum(),
                "t1_error_share_pct": t1.error_gva_eok.sum() / sub.error_gva_eok.sum() * 100,
                "top_error_industry": sub.sort_values("error_gva_eok", ascending=False).iloc[0].middle_label,
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUTDIR / "phase69_error_reduction_strategy_summary.csv", index=False, encoding="utf-8-sig")

    report = f"""# 산업별 GVA 추정오차 축소 전략

## 결론

모든 산업을 개별 특화모델로 만들 필요는 없다. 금액오차가 큰 산업이 전체 오차의 대부분을 만든다. 따라서 `T1 특화 우선 → T2 업종군 보강 → T3 공통모델 유지`의 3단 구조가 가장 현실적이다.

## 우선순위 요약

{md_table(summary, [("city", "지역"), ("total_middle_cells", "중분류 수"), ("t1_cells", "T1 산업 수"), ("t1_error_gva_eok", "T1 오차 억원"), ("t1_error_share_pct", "T1 오차비중 %"), ("top_error_industry", "최대오차 산업")])}

## T1 특화 우선 산업

{md_table(top, [("city", "지역"), ("rank_by_error", "순위"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("direction", "방향"), ("family_label", "보강모델")], 24)}

## 업종군별 보강 방식

{md_table(family[family.priority_tier.ne("T3 공통모델 유지")], [("city", "지역"), ("priority_tier", "단계"), ("family_label", "업종군"), ("industries", "산업 수"), ("error_gva_eok", "오차 억원"), ("error_share_within_city_pct", "오차비중 %"), ("recommended_indicators", "우선 자료")], 30)}

## 운영 원칙

1. 먼저 금액오차 기준 상위 산업을 줄인다. 상대오차가 크더라도 실제액이 작은 산업은 후순위로 둔다.
2. 같은 대분류 안에서 한쪽은 과대, 다른 한쪽은 과소인 경우는 “총량 문제”가 아니라 “내부 분할 문제”다. 건설, 보건·복지, 운수·창고가 여기에 해당한다.
3. 포항 1차 금속 제조업처럼 지역 핵심 산업은 별도 특화가 필요하다. 사업체 수보다 공장면적·전력·산단 대형사업장·물동량이 우선이다.
4. T3 산업은 공통 배분을 유지하되, 연 1회 중분류 actual 집계검증으로 악화 여부만 감시한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase69_error_reduction_strategy_detail.csv")
    print(OUTDIR / "phase69_error_reduction_strategy_by_family.csv")


if __name__ == "__main__":
    main()
