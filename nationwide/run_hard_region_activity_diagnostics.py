#!/usr/bin/env python3
"""Diagnose weak activities in harder nationwide validation regions."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = HERE / "hard_region_activity_diagnostics.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
HARD_REGIONS = ["인천", "울산", "세종", "대구", "충북"]


def wape(err: pd.Series, actual: pd.Series) -> float:
    return float(err.abs().sum() / actual.abs().sum() * 100)


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def route(activity: str) -> tuple[str, str, str]:
    """Return cause class, likely missing direct data, and possible action."""
    mapping = {
        "광업, 제조업": (
            "지역 제조업 구조·대형사업장 충격",
            "시도/시군구 제조업 중분류 생산·출하·공장가동·전력·수출",
            "중분류 제조업 생산지수/공장등록/전력/수출을 결합한 제조업 특화 시간배분",
        ),
        "건설업": (
            "지역 건설수주·착공·준공 시차",
            "건축허가·착공·사용승인, 건설수주 공종별 지역자료",
            "BOK식 건축 12분기·토목 24분기 분산지표와 건축물대장 이벤트 결합",
        ),
        "운수 및 창고업": (
            "항만·공항·물류거점 활동량의 지역차",
            "항만 물동량, 공항 여객/화물, 물류창고 인허가, 대중교통 승하차",
            "항만/공항/물류 활동량이 큰 지역만 독립 라우팅",
        ),
        "부동산업": (
            "거래·임대·공시가격·입주물량의 지역 시차",
            "실거래, 전월세, 건축물대장, 공동주택 공시가격, 입주/준공",
            "거래·임대 flow와 stock 지표를 구분한 부동산 특화 라우팅",
        ),
        "정보통신업": (
            "플랫폼·방송·통신사업자 집중과 지역 사업장 구조",
            "방송/통신/콘텐츠 사업자 매출·사업체·고용",
            "대형 사업자 집중 지역은 사업체·고용 구조 보정",
        ),
        "금융 및 보험업": (
            "본점/지점 소재와 생산 귀속 차이",
            "금융기관 점포·예수금·대출금·보험계약",
            "시도 단위 금융활동 보조지표로만 완만 보정",
        ),
        "공공 행정, 국방·사회보장": (
            "정부·군·행정기관 지출의 지역 귀속",
            "지방재정 집행, 정부기관/군부대 고용, 예산집행",
            "전국분기비중 + 지역 공공고용/재정집행 보조",
        ),
        "교육 서비스업": (
            "학령인구·대학·공공교육 지출 구조",
            "학교/학생/교직원, 대학 재정, 교육청 집행",
            "교육통계 stock과 교육재정 flow 결합",
        ),
        "보건 및 사회복지업": (
            "의료기관·요양·복지시설 집중",
            "병상수, 의료기관, 건강보험 진료비, 복지시설",
            "의료이용·시설 stock 기반 특화 라우팅",
        ),
    }
    return mapping.get(
        activity,
        (
            "전국 공통 분기비중과 지역 구조 차이",
            "시도/시군구 직접 활동자료",
            "활동자료가 확인되는 지역·업종만 독립 라우팅",
        ),
    )


def main() -> int:
    df = pd.read_csv(OUT / "operating_point_sido_activity_validation.csv")
    df["k"] = df["available_quarters_x"].fillna(df.get("available_quarters", pd.Series(index=df.index))).astype(int)
    hard = df[df["quarter_region"].isin(HARD_REGIONS)].copy()

    rows = []
    for keys, g in hard.groupby(["track", "quarter_region", "k", "operating_label", "activity"], dropna=False):
        track, region, k, label, activity = keys
        cause, missing, action = route(activity)
        rows.append(
            {
                "track": track,
                "quarter_region": region,
                "available_quarters": k,
                "operating_label": label,
                "activity": activity,
                "years": g["year"].nunique(),
                "annualized_official_sum_eok": g["official_annual_eok"].abs().sum(),
                "annualized_abs_error_sum_eok": g["annualized_error_eok"].abs().sum(),
                "annualized_wape_pct": wape(g["annualized_error_eok"], g["official_annual_eok"]),
                "max_annualized_ape_pct": g["annualized_ape_pct"].max(),
                "years_over_5pct": int((g["annualized_ape_pct"] > 5).sum()),
                "years_over_10pct": int((g["annualized_ape_pct"] > 10).sum()),
                "cause_class": cause,
                "needed_direct_data": missing,
                "candidate_action": action,
            }
        )
    act = pd.DataFrame(rows)
    act.to_csv(OUT / "hard_region_activity_diagnostics.csv", index=False, encoding="utf-8-sig")

    # Prioritize by strict flash Q1 because that is the hardest operating point.
    q1 = act[(act["track"].eq("recursive_no_target_actual")) & (act["available_quarters"].eq(1))].copy()
    q1["priority_score"] = q1["annualized_abs_error_sum_eok"] * (1 + q1["annualized_wape_pct"] / 100)
    priority = (
        q1.sort_values(["quarter_region", "priority_score"], ascending=[True, False])
        .groupby("quarter_region", group_keys=False)
        .head(8)
    )
    priority.to_csv(OUT / "hard_region_activity_priority_q1_strict.csv", index=False, encoding="utf-8-sig")

    activity_rollup = (
        q1.groupby("activity", as_index=False)
        .agg(
            regions=("quarter_region", "nunique"),
            official_sum_eok=("annualized_official_sum_eok", "sum"),
            abs_error_sum_eok=("annualized_abs_error_sum_eok", "sum"),
            mean_wape_pct=("annualized_wape_pct", "mean"),
            max_ape_pct=("max_annualized_ape_pct", "max"),
            region_years_over_10pct=("years_over_10pct", "sum"),
        )
    )
    activity_rollup["combined_wape_pct"] = activity_rollup["abs_error_sum_eok"] / activity_rollup["official_sum_eok"] * 100
    activity_rollup = activity_rollup.sort_values(["abs_error_sum_eok", "combined_wape_pct"], ascending=False)
    activity_rollup.to_csv(OUT / "hard_region_activity_rollup_q1_strict.csv", index=False, encoding="utf-8-sig")

    report = f"""# 어려운 5개 지역 업종별 오차 진단

생성시각: {CREATED_AT}

## 대상

- 지역: 인천, 울산, 세종, 대구, 충북
- 우선 진단 기준: 엄격 속보형 `1분기+1개월`
- 이유: 5개년 범용성 감사에서 상대적으로 어려운 지역으로 반복 등장했고, Q1 속보 시점이 가장 정보가 적다.

## 지역별 우선 점검 업종

{md_table(priority[[
    "quarter_region", "activity", "annualized_official_sum_eok", "annualized_abs_error_sum_eok",
    "annualized_wape_pct", "max_annualized_ape_pct", "years_over_5pct", "years_over_10pct",
    "cause_class", "needed_direct_data", "candidate_action"
]].rename(columns={
    "quarter_region": "지역",
    "activity": "업종",
    "annualized_official_sum_eok": "5개년실제합_억원",
    "annualized_abs_error_sum_eok": "5개년절대오차합_억원",
    "annualized_wape_pct": "5개년WAPE_pct",
    "max_annualized_ape_pct": "최대연도오차율_pct",
    "years_over_5pct": "5pct초과연도수",
    "years_over_10pct": "10pct초과연도수",
    "cause_class": "추정취약원인",
    "needed_direct_data": "필요자료",
    "candidate_action": "개선방향",
}), 3)}

## 업종별 공통 우선순위

{md_table(activity_rollup[[
    "activity", "regions", "official_sum_eok", "abs_error_sum_eok", "combined_wape_pct",
    "mean_wape_pct", "max_ape_pct", "region_years_over_10pct"
]].head(12).rename(columns={
    "activity": "업종",
    "regions": "문제지역수",
    "official_sum_eok": "5개지역실제합_억원",
    "abs_error_sum_eok": "5개지역절대오차합_억원",
    "combined_wape_pct": "통합WAPE_pct",
    "mean_wape_pct": "지역평균WAPE_pct",
    "max_ape_pct": "최대연도오차율_pct",
    "region_years_over_10pct": "10pct초과_지역연도수",
}), 3)}

## 1차 판단

1. 5개 지역의 Q1 속보 오차는 특정 한 업종만의 문제가 아니라, 제조업·서비스업 세부업종·건설·부동산·운수창고처럼 지역 고유 활동량이 큰 업종에서 주로 커진다.
2. 고양·포항에서 사용했던 방식처럼 모든 업종을 별도 모형화하기보다는, 지역별 오차기여가 큰 업종에만 독립 라우팅을 적용하는 것이 타당하다.
3. 우선 수집·개선 후보는 제조업, 건설업, 운수 및 창고업, 부동산업이다. 이들은 이미 프로젝트 내에서 고양·포항 개선 실험을 했던 계열과 연결된다.
4. 금융·공공행정·교육·보건은 직접 활동자료가 있어도 생산 귀속과 공표시차 문제가 크므로, 단기적으로는 완만한 보정 또는 해석 제한이 더 안전하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(priority.head(50).to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
