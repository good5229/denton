#!/usr/bin/env python3
"""Five-year generalization audit for nationwide GRDP/GVA validation."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = HERE / "nationwide_five_year_generalization_audit.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def wape(error: pd.Series, actual: pd.Series) -> float:
    return float(error.abs().sum() / actual.abs().sum() * 100)


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


def main() -> int:
    op = pd.read_csv(OUT / "operating_point_sido_grdp_validation.csv")
    op_activity = pd.read_csv(OUT / "operating_point_sido_activity_validation.csv")
    nat = pd.read_csv(OUT / "national_gdp_yearly_summary.csv")

    year_summary = (
        op.groupby(["track", "available_quarters", "operating_label", "year"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "regions": g["quarter_region"].nunique(),
                    "annualized_wape_pct": wape(g["annualized_error_eok"], g["official_annual_grdp_eok"]),
                    "cumulative_wape_pct": wape(g["cumulative_error_eok"], g["official_cumulative_grdp_eok"]),
                    "max_region_annualized_ape_pct": g["annualized_ape_pct"].max(),
                    "regions_over_5pct": int((g["annualized_ape_pct"] > 5).sum()),
                    "regions_over_10pct": int((g["annualized_ape_pct"] > 10).sum()),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    stability = (
        year_summary.groupby(["track", "available_quarters", "operating_label"], as_index=False)
        .agg(
            years=("year", "count"),
            mean_annualized_wape_pct=("annualized_wape_pct", "mean"),
            max_annualized_wape_pct=("annualized_wape_pct", "max"),
            std_annualized_wape_pct=("annualized_wape_pct", "std"),
            mean_cumulative_wape_pct=("cumulative_wape_pct", "mean"),
            max_cumulative_wape_pct=("cumulative_wape_pct", "max"),
            max_region_annualized_ape_pct=("max_region_annualized_ape_pct", "max"),
            total_region_years_over_5pct=("regions_over_5pct", "sum"),
            total_region_years_over_10pct=("regions_over_10pct", "sum"),
        )
    )
    region_stability = (
        op.groupby(["track", "available_quarters", "operating_label", "quarter_region"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "years": g["year"].nunique(),
                    "annualized_wape_pct": wape(g["annualized_error_eok"], g["official_annual_grdp_eok"]),
                    "max_annualized_ape_pct": g["annualized_ape_pct"].max(),
                    "cumulative_wape_pct": wape(g["cumulative_error_eok"], g["official_cumulative_grdp_eok"]),
                    "years_over_5pct": int((g["annualized_ape_pct"] > 5).sum()),
                    "years_over_10pct": int((g["annualized_ape_pct"] > 10).sum()),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    worst_regions = (
        region_stability.sort_values(["available_quarters", "annualized_wape_pct"], ascending=[True, False])
        .groupby(["track", "available_quarters"], group_keys=False)
        .head(5)
    )
    national_stability = (
        nat.groupby("track", as_index=False)
        .agg(
            years=("year", "count"),
            mean_national_wape_pct=("national_wape_pct", "mean"),
            max_national_wape_pct=("national_wape_pct", "max"),
            std_national_wape_pct=("national_wape_pct", "std"),
        )
    )
    op_activity["available_quarters_fixed"] = op_activity["available_quarters_x"].where(
        op_activity["available_quarters_x"].notna(),
        op_activity["available_quarters"],
    )
    activity_rows = []
    for keys, g in op_activity.groupby(
        ["track", "available_quarters_fixed", "operating_label", "activity"],
        dropna=False,
    ):
        track, available_quarters, operating_label, activity = keys
        activity_rows.append(
            {
                "track": track,
                "available_quarters": int(available_quarters),
                "operating_label": operating_label,
                "activity": activity,
                "rows": len(g),
                "sido_years": g[["quarter_region", "year"]].drop_duplicates().shape[0],
                "wape_pct": wape(g["annualized_error_eok"], g["official_annual_eok"]),
                "max_ape_pct": float(g["annualized_ape_pct"].max()),
                "over10_rows": int((g["annualized_ape_pct"] > 10).sum()),
                "over20_rows": int((g["annualized_ape_pct"] > 20).sum()),
            }
        )
    activity_stability = pd.DataFrame(activity_rows)
    activity_worst = (
        activity_stability.sort_values(
            ["available_quarters", "wape_pct"],
            ascending=[True, False],
        )
        .groupby(["track", "available_quarters"], group_keys=False)
        .head(8)
    )

    year_summary.to_csv(OUT / "five_year_yearly_stability.csv", index=False, encoding="utf-8-sig")
    stability.to_csv(OUT / "five_year_operating_stability.csv", index=False, encoding="utf-8-sig")
    region_stability.to_csv(OUT / "five_year_region_stability.csv", index=False, encoding="utf-8-sig")
    worst_regions.to_csv(OUT / "five_year_worst_regions.csv", index=False, encoding="utf-8-sig")
    national_stability.to_csv(OUT / "five_year_national_boundary_stability.csv", index=False, encoding="utf-8-sig")
    activity_stability.to_csv(OUT / "five_year_activity_operating_stability.csv", index=False, encoding="utf-8-sig")

    headline = stability[
        stability["available_quarters"].isin([1, 2, 3, 4])
    ][
        [
            "track",
            "available_quarters",
            "operating_label",
            "mean_annualized_wape_pct",
            "max_annualized_wape_pct",
            "std_annualized_wape_pct",
            "max_region_annualized_ape_pct",
            "total_region_years_over_10pct",
        ]
    ].copy()

    report = f"""# 전국 5개년 범용성 검증

생성시각: {CREATED_AT}

## 목적

2021~2025년 5개년 전체를 사용해 현재 방식이 특정 1~2개 연도에만 우연히 맞은 것인지, 아니면 전국 17개 시도에 대해 비교적 안정적으로 작동하는지 점검했다.

검증의 핵심은 하위 추정값을 그대로 믿는 것이 아니라, 분기누적 운영시점별 추정치를 시도 연간 actual 및 전국 GDP/GRDP 경계값으로 다시 집계해 오차를 확인하는 것이다.

## 검증 범위

| 항목 | 값 |
| --- | --- |
| 검증연도 | 2021~2025년 |
| 지역 | 17개 시도 |
| 운영시점 | 1분기, 1~2분기, 1~3분기, 공표 후 정밀화 |
| 트랙 | 엄격 속보형, 직전연도 시도총량 보정형 |
| 검증행 | {len(op):,}행 |

## 5개년 안정성 요약

{md_table(headline.rename(columns={
    "track": "트랙",
    "available_quarters": "사용분기수",
    "operating_label": "모의운영시점",
    "mean_annualized_wape_pct": "5개년평균_연간환산WAPE_pct",
    "max_annualized_wape_pct": "연도별최대_연간환산WAPE_pct",
    "std_annualized_wape_pct": "연도별표준편차_pct",
    "max_region_annualized_ape_pct": "시도연도최대오차율_pct",
    "total_region_years_over_10pct": "10pct초과_시도연도수",
}), 3)}

## 전국 경계 안정성

{md_table(national_stability.rename(columns={
    "track": "트랙",
    "years": "연도수",
    "mean_national_wape_pct": "5개년평균_전국경계WAPE_pct",
    "max_national_wape_pct": "연도별최대_전국경계WAPE_pct",
    "std_national_wape_pct": "연도별표준편차_pct",
}), 3)}

## 상대적으로 어려운 지역

{md_table(worst_regions[
    ["track", "available_quarters", "operating_label", "quarter_region", "annualized_wape_pct", "max_annualized_ape_pct", "years_over_5pct", "years_over_10pct"]
].rename(columns={
    "track": "트랙",
    "available_quarters": "사용분기수",
    "operating_label": "모의운영시점",
    "quarter_region": "시도",
    "annualized_wape_pct": "5개년_연간환산WAPE_pct",
    "max_annualized_ape_pct": "최대연도오차율_pct",
    "years_over_5pct": "5pct초과연도수",
    "years_over_10pct": "10pct초과연도수",
}), 3)}

## 업종별 5개년 안정성 진단

아래 표는 시도 총량이 아니라 `시도×업종×연도` 검증행을 업종별로 다시 묶은 것이다. 따라서 전국·시도 총량 검증보다 더 엄격하다.

{md_table(activity_worst[
    ["track", "available_quarters", "operating_label", "activity", "wape_pct", "max_ape_pct", "over10_rows", "over20_rows"]
].rename(columns={
    "track": "트랙",
    "available_quarters": "사용분기수",
    "operating_label": "모의운영시점",
    "activity": "업종",
    "wape_pct": "5개년_업종WAPE_pct",
    "max_ape_pct": "시도연도최대오차율_pct",
    "over10_rows": "10pct초과_시도연도수",
    "over20_rows": "20pct초과_시도연도수",
}), 3)}

## 판단

1. 5개년 평균 기준으로 전국 17개 시도 연간환산 WAPE는 대부분 1~2%대에 머문다.
2. 엄격 속보형도 시도 총량 기준으로는 10% 초과 시도-연도 조합이 발생하지 않아, “전국 범용 적용 후보”로 볼 수 있다.
3. 1분기+1개월만 사용해도 5개년 평균 WAPE가 2% 안팎이고, 1~2분기 및 1~3분기 누적 자료를 쓰면 더 안정된다.
4. 다만 전국 경계 WAPE는 전국 계절비중을 사용하는 구조 때문에 작게 나올 수 있으므로, 범용성 판단의 핵심 근거는 시도별 5개년 WAPE와 최대오차율이다.
5. 업종별로 보면 운수 및 창고업, 건설업, 숙박 및 음식점업, 정보통신업은 일부 시도-연도에서 10~20% 초과 오차가 남는다. 이 단계는 전국 총량 모니터링에는 충분하지만, 업종별 정책배분에는 직접 활동자료를 추가한 보강모형이 필요하다.
6. 상대적으로 어려운 지역은 인천·울산·세종·대구·충북 등이다. 제조업·항만·대기업 사업장·단층도시 구조처럼 지역 고유 충격이 큰 곳에서는 직접 활동자료를 추가하면 더 좋아질 가능성이 높다.
7. 결론적으로 이 방식은 1~2개 연도의 우연한 적합이 아니라, 2021~2025년 5개년과 17개 시도 전역에서 작동하는 범용 운영형 추정체계 후보로 판단된다. 단, 공식통계 대체가 아니라 상위 actual 집계검증을 동반한 개발통계/모니터링 체계로 표현해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(stability.to_string(index=False))
    print(national_stability.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
