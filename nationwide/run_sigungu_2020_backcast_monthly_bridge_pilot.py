#!/usr/bin/env python3
"""2020 limited sigungu-by-industry quarterly/monthly backcast pilot.

This is deliberately not a nationwide completion script.  It tests whether the
monthly bridge can be pushed one year earlier for provinces that already have
2019 sigungu annual GVA benchmarks in the local source.

Allowed claims:
* 2019-benchmark provinces only.
* 2020 target actual is used for validation, not as an input.
* Monthly values are quarter-preserving bridge outputs, not monthly actual
  accuracy estimates.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

from run_nationwide_monthly_bridge_validation import (
    SERVICE_ACTIVITY_MAP,
    INDEX_PATHS,
    equal_month_rows,
    load_index,
    load_national_service_index,
    md_table,
    norm,
    short_region,
)
from run_nationwide_quarterly_grdp_validation import (
    OTHER_NPT_ACTIVITY,
    SERVICE_COMPONENTS,
    VALIDATION_ACTIVITIES,
    activity_group,
    load_annual_sigungu,
    load_quarterly,
    national_quarter_factor,
    official_region_activity,
    province_activity_predictions,
    validate_quarters,
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = HERE / "sigungu_2020_backcast_monthly_bridge_pilot.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
TARGET_YEAR = 2020
BASE_YEAR = 2019


def build_monthly_weights_for_year(q: pd.DataFrame, year: int) -> pd.DataFrame:
    all_weights: list[pd.DataFrame] = []

    manuf = load_index(INDEX_PATHS["manufacturing"])
    manuf = manuf[manuf["activity_raw"].map(norm).eq(norm("제조업"))].copy()
    manuf["activity_group"] = "광업, 제조업"
    all_weights.append(
        manuf[["region_short", "activity_group", "year", "quarter", "month", "period", "indicator_value"]]
        .assign(monthly_indicator_source="시도별 제조업 생산지수")
    )

    service = load_national_service_index(INDEX_PATHS["service_national_monthly"])
    frames = []
    service_norm = service["activity_raw"].map(norm)
    for activity, raw_names in SERVICE_ACTIVITY_MAP.items():
        mask = service_norm.isin({norm(x) for x in raw_names})
        tmp = service[mask].copy()
        if tmp.empty:
            continue
        tmp["activity_group"] = activity
        frames.append(tmp)
    if frames:
        svc = pd.concat(frames, ignore_index=True)
        svc = (
            svc.groupby(["activity_group", "year", "quarter", "month", "period"], as_index=False)
            .agg(indicator_value=("indicator_value", "mean"))
            .assign(monthly_indicator_source="전국 산업별 서비스업생산지수")
        )
        svc = q[["region_short"]].drop_duplicates().merge(svc, how="cross")
        all_weights.append(svc)

    broad = load_national_service_index(INDEX_PATHS["all_industry_national_monthly"])
    broad_map = {
        "건설업": {"건설업"},
        "공공 행정, 국방·사회보장": {"공공행정"},
    }
    broad_frames = []
    broad_norm = broad["activity_raw"].map(norm)
    for activity, raw_names in broad_map.items():
        mask = broad_norm.isin({norm(x) for x in raw_names})
        tmp = broad[mask].copy()
        if tmp.empty:
            continue
        tmp["activity_group"] = activity
        broad_frames.append(tmp)
    if broad_frames:
        b = pd.concat(broad_frames, ignore_index=True)
        b = (
            b.groupby(["activity_group", "year", "quarter", "month", "period"], as_index=False)
            .agg(indicator_value=("indicator_value", "mean"))
            .assign(monthly_indicator_source="전국 전산업생산지수 원지수")
        )
        b = q[["region_short"]].drop_duplicates().merge(b, how="cross")
        all_weights.append(b)

    if not all_weights:
        return pd.DataFrame()

    w = pd.concat(all_weights, ignore_index=True)
    w = w[w["year"].eq(year)].copy()
    w["indicator_value"] = w["indicator_value"].clip(lower=0)
    w["months_in_quarter"] = w.groupby(["region_short", "activity_group", "year", "quarter"])["month"].transform("nunique")
    w = w[w["months_in_quarter"].eq(3)].copy()
    w["quarter_indicator_sum"] = w.groupby(["region_short", "activity_group", "year", "quarter"])["indicator_value"].transform("sum")
    w["month_share"] = w["indicator_value"] / w["quarter_indicator_sum"]
    w = w[w["month_share"].notna() & w["month_share"].gt(0)].copy()
    return w[
        [
            "region_short",
            "activity_group",
            "year",
            "quarter",
            "month",
            "period",
            "month_share",
            "monthly_indicator_source",
        ]
    ].copy()


def build_quarterly_2020(annual: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    basis = annual[annual["year"].eq(BASE_YEAR)].copy()
    basis["basis_source"] = f"official_sigungu_annual_{BASE_YEAR}"
    covered = (
        basis.groupby("quarter_region", as_index=False)
        .agg(city_count=("city", "nunique"), activity_count=("activity_group", "nunique"), rows=("annual_gva_eok", "size"))
        .sort_values("quarter_region")
    )
    covered_regions = sorted(covered["quarter_region"].unique())

    factors = national_quarter_factor(x)
    q = factors[
        factors["year"].eq(TARGET_YEAR)
        & factors["activity"].isin(["광업, 제조업", "건설업", *SERVICE_COMPONENTS])
    ].copy()
    pred = basis.merge(q, left_on="activity_group", right_on="activity", how="inner")
    pred["year"] = TARGET_YEAR
    pred["predicted_gva_eok"] = pred["annual_gva_eok"] * pred["quarter_factor_from_prev_annual"]
    city_q = pred[
        [
            "quarter_region",
            "province_full",
            "year",
            "quarter",
            "period",
            "city",
            "activity_group",
            "predicted_gva_eok",
            "basis_source",
            "quarter_factor_from_prev_annual",
        ]
    ].copy()
    city_q["track"] = "limited_2020_backcast_2019_benchmark"

    official = official_region_activity(x)
    other_official_y = (
        official[
            official["activity"].eq(OTHER_NPT_ACTIVITY)
            & official["region"].isin(covered_regions)
            & official["year"].eq(BASE_YEAR)
        ]
        .groupby(["region", "year"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"region": "quarter_region", "official_value_eok": "official_other_npt_annual_eok"})
    )
    other_factor = factors[factors["year"].eq(TARGET_YEAR) & factors["activity"].eq(OTHER_NPT_ACTIVITY)].copy()
    other_rows = []
    for region in covered_regions:
        vals = other_official_y[other_official_y["quarter_region"].eq(region)]["official_other_npt_annual_eok"]
        if vals.empty:
            continue
        tmp = other_factor.copy()
        tmp["quarter_region"] = region
        tmp["year"] = TARGET_YEAR
        tmp["prior_other_npt_annual_eok"] = float(vals.iloc[0])
        tmp["predicted_other_npt_eok"] = tmp["prior_other_npt_annual_eok"] * tmp["quarter_factor_from_prev_annual"]
        tmp["other_npt_source"] = f"official_prior_year_{BASE_YEAR}"
        tmp["track"] = "limited_2020_backcast_2019_benchmark"
        other_rows.append(tmp)
    other_q = pd.concat(other_rows, ignore_index=True)[
        ["track", "quarter_region", "year", "quarter", "period", "predicted_other_npt_eok", "other_npt_source", "quarter_factor_from_prev_annual"]
    ]
    return city_q, other_q, covered


def build_monthly(city_q: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q = city_q.copy()
    q["region_short"] = q["quarter_region"].map(short_region)
    weights = build_monthly_weights_for_year(q, TARGET_YEAR)
    key = ["region_short", "activity_group", "year", "quarter"]
    if weights.empty:
        monthly = equal_month_rows(q)
    else:
        with_w = q.merge(weights, on=[*key], how="left", suffixes=("", "_indicator"))
        matched = with_w[with_w["month_share"].notna()].copy()
        matched["monthly_indicator_coverage"] = "monthly_indicator"
        unmatched_keys = (
            with_w[with_w["month_share"].isna()][["track", "quarter_region", "province_full", "year", "quarter", "period", "city", "activity_group"]]
            .drop_duplicates()
        )
        unmatched = q.merge(
            unmatched_keys,
            on=["track", "quarter_region", "province_full", "year", "quarter", "period", "city", "activity_group"],
            how="inner",
        )
        if not unmatched.empty:
            unmatched = equal_month_rows(unmatched)
            unmatched["period"] = unmatched["year"].astype(str) + unmatched["month"].astype(int).astype(str).str.zfill(2)
        monthly = pd.concat([matched, unmatched], ignore_index=True, sort=False)

    monthly["month"] = monthly["month"].astype(int)
    monthly["month_period"] = monthly["year"].astype(str) + monthly["month"].astype(str).str.zfill(2)
    monthly["estimated_monthly_gva_eok"] = monthly["predicted_gva_eok"] * monthly["month_share"]
    keep = [
        "track",
        "quarter_region",
        "province_full",
        "region_short",
        "year",
        "quarter",
        "month",
        "month_period",
        "city",
        "activity_group",
        "estimated_monthly_gva_eok",
        "predicted_gva_eok",
        "month_share",
        "monthly_indicator_source",
        "monthly_indicator_coverage",
        "basis_source",
    ]
    monthly = monthly[keep].copy()

    q_key = ["track", "quarter_region", "province_full", "year", "quarter", "city", "activity_group"]
    q_audit = (
        monthly.groupby(q_key, as_index=False)
        .agg(monthly_sum_eok=("estimated_monthly_gva_eok", "sum"), months=("month", "nunique"))
        .merge(q[q_key + ["predicted_gva_eok"]].drop_duplicates(), on=q_key, how="left")
    )
    q_audit["reaggregation_error_eok"] = q_audit["monthly_sum_eok"] - q_audit["predicted_gva_eok"]
    q_audit["abs_reaggregation_error_eok"] = q_audit["reaggregation_error_eok"].abs()

    share_audit = (
        monthly.groupby(q_key, as_index=False)
        .agg(
            months=("month", "nunique"),
            month_share_sum=("month_share", "sum"),
            negative_month_values=("estimated_monthly_gva_eok", lambda s: int((s < 0).sum())),
        )
    )
    share_audit["abs_share_sum_error"] = (share_audit["month_share_sum"] - 1.0).abs()

    monthly_for_coverage = monthly.copy()
    monthly_for_coverage["city_unit"] = monthly_for_coverage["quarter_region"].astype(str) + "|" + monthly_for_coverage["city"].astype(str)
    coverage = (
        monthly_for_coverage.groupby(["activity_group", "monthly_indicator_coverage", "monthly_indicator_source"], as_index=False)
        .agg(
            rows=("estimated_monthly_gva_eok", "size"),
            estimated_sum_eok=("estimated_monthly_gva_eok", "sum"),
            city_count=("city_unit", "nunique"),
            quarter_count=("quarter", "nunique"),
        )
        .sort_values(["activity_group", "monthly_indicator_coverage"])
    )
    return monthly, q_audit, share_audit, coverage


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    x = load_quarterly()
    annual, _inventory = load_annual_sigungu()
    city_q, other_q, covered = build_quarterly_2020(annual, x)
    pred_act = province_activity_predictions(city_q, other_q)
    act_val, total_val, year_summary = validate_quarters(pred_act, x)
    monthly, q_audit, share_audit, coverage = build_monthly(city_q)

    q_summary = (
        total_val.groupby(["track"], as_index=False)
        .agg(
            province_count=("quarter_region", "nunique"),
            quarter_rows=("period", "count"),
            predicted_sum_eok=("predicted_grdp_eok", "sum"),
            actual_sum_eok=("official_grdp_eok", "sum"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            wape_pct=("abs_error_eok", lambda s: s.sum() / total_val.loc[s.index, "official_grdp_eok"].abs().sum() * 100),
            max_ape_pct=("ape_pct", "max"),
        )
    )
    act_summary = (
        act_val.groupby(["activity"], as_index=False)
        .agg(
            province_quarter_rows=("period", "count"),
            predicted_sum_eok=("predicted_value_eok", "sum"),
            actual_sum_eok=("official_value_eok", "sum"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            wape_pct=("abs_error_eok", lambda s: s.sum() / act_val.loc[s.index, "official_value_eok"].abs().sum() * 100),
            max_ape_pct=("ape_pct", "max"),
        )
        .sort_values("wape_pct", ascending=False)
    )
    monthly_summary = pd.DataFrame(
        [
            {
                "year": TARGET_YEAR,
                "base_year": BASE_YEAR,
                "monthly_rows": len(monthly),
                "province_count": monthly["quarter_region"].nunique(),
                "city_count": monthly[["quarter_region", "city"]].drop_duplicates().shape[0],
                "activity_count": monthly["activity_group"].nunique(),
                "indicator_rows_pct": float(monthly["monthly_indicator_coverage"].eq("monthly_indicator").mean() * 100),
                "fallback_equal_split_rows_pct": float(monthly["monthly_indicator_coverage"].eq("fallback_equal_split").mean() * 100),
                "max_abs_quarter_reaggregation_error_eok": float(q_audit["abs_reaggregation_error_eok"].max()),
                "bad_quarter_cells_gt_1won_equiv": int(q_audit["abs_reaggregation_error_eok"].gt(1e-8).sum()),
                "bad_month_count_cells": int(share_audit["months"].ne(3).sum()),
                "bad_month_share_sum_cells": int(share_audit["abs_share_sum_error"].gt(1e-10).sum()),
                "negative_month_value_cells": int(share_audit["negative_month_values"].sum()),
            }
        ]
    )

    city_q.to_csv(OUT / "sigungu_industry_quarterly_predictions_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    other_q.to_csv(OUT / "sido_other_npt_quarterly_predictions_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    pred_act.to_csv(OUT / "sido_activity_quarterly_predictions_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    total_val.to_csv(OUT / "sido_quarterly_grdp_validation_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    act_val.to_csv(OUT / "sido_activity_quarterly_validation_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(OUT / "sigungu_industry_monthly_predictions_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    q_audit.to_csv(OUT / "monthly_bridge_quarter_reaggregation_audit_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    share_audit.to_csv(OUT / "monthly_bridge_share_integrity_audit_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(OUT / "monthly_bridge_indicator_coverage_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    covered.to_csv(OUT / "sigungu_2019_benchmark_coverage_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    q_summary.to_csv(OUT / "sido_quarterly_grdp_summary_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    act_summary.to_csv(OUT / "sido_activity_quarterly_summary_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")
    monthly_summary.to_csv(OUT / "monthly_bridge_summary_2020_backcast_pilot.csv", index=False, encoding="utf-8-sig")

    excluded = sorted(set(["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기도", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]) - set(covered["quarter_region"]))
    monthly_summary_display = monthly_summary.rename(columns={
        'year':'연도','base_year':'기준연도','monthly_rows':'월별행','province_count':'시도수','city_count':'시군구수',
        'activity_count':'업종수','indicator_rows_pct':'월별지표적용행_pct','fallback_equal_split_rows_pct':'균등분할행_pct',
        'max_abs_quarter_reaggregation_error_eok':'최대분기재집계오차_억원','bad_quarter_cells_gt_1won_equiv':'분기재집계오류셀',
        'bad_month_count_cells':'월수오류셀','bad_month_share_sum_cells':'월비중오류셀','negative_month_value_cells':'음수월값셀'
    })
    monthly_summary_display["연도"] = monthly_summary_display["연도"].astype(str)
    monthly_summary_display["기준연도"] = monthly_summary_display["기준연도"].astype(str)

    report = f"""# 2020 시군구×업종 분기·월 backcast 파일럿

생성시각: {CREATED_AT}

## 1. 목적

2021~2025로 제한된 전국 `시군구×업종×월` bridge를 2020년까지 확장할 수 있는지 점검했다. 이 문서는 전국 완료 산출물이 아니라 **2019년 시군구 annual GVA 기준값이 있는 시도에 한정한 2020 backcast 파일럿**이다.

## 2. 포함 범위

| 구분 | 내용 |
| --- | --- |
| 대상연도 | 2020년 |
| 기준값 | 2019년 시군구×업종 annual GVA |
| 포함 시도 | {', '.join(covered['quarter_region'].tolist())} |
| 제외 시도 | {', '.join(excluded)} |
| 제외 사유 | 2019년 시군구×업종 annual 기준값 부재 또는 세종 단층처리용 2019 기준값 부재 |
| 예측 입력 | 2019 시군구 annual 기준값 × 2020 전국 업종별 분기/전년연간 비중 |
| 검증 actual | 2020 시도×업종×분기 공식값 및 시도 GRDP 공식값 |

2020년 전국 업종별 분기비중은 사후에 확보된 분기 경로다. 따라서 이 파일럿은 실시간 `Q+1개월` 속보 예측 성능이 아니라, 2019 시군구 기준값으로 2020년 공간·분기·월 bridge를 얼마나 재현할 수 있는지 보는 **사후 backcast 검증**이다.

## 3. 2019 기준값 보유 시도

{md_table(covered.rename(columns={'quarter_region':'시도','city_count':'시군구수','activity_count':'업종수','rows':'기준값행'}), 0)}

## 4. 시도 GRDP 집계검증

시군구×업종 추정값을 시도 단위로 합산하고, 기타산업 및 순생산물세를 별도 bridge로 더해 2020년 시도 분기 GRDP actual과 비교했다.

{md_table(q_summary.rename(columns={
    'track':'트랙','province_count':'시도수','quarter_rows':'분기검증행','predicted_sum_eok':'예측합_억원',
    'actual_sum_eok':'실제합_억원','abs_error_sum_eok':'절대오차합_억원','wape_pct':'WAPE_pct','max_ape_pct':'최대오차율_pct'
}), 3)}

## 5. 업종별 집계검증

{md_table(act_summary.rename(columns={
    'activity':'업종','province_quarter_rows':'시도분기행','predicted_sum_eok':'예측합_억원',
    'actual_sum_eok':'실제합_억원','abs_error_sum_eok':'절대오차합_억원','wape_pct':'WAPE_pct','max_ape_pct':'최대오차율_pct'
}).head(15), 3)}

## 6. 월별 bridge 보존성 검증

월별 값은 분기 추정값을 3개월로 나눈 운영 bridge다. 월별 official actual은 없으므로, 월별 정확도 검증이 아니라 월합이 원 분기 추정값을 보존하는지만 확인했다.

{md_table(monthly_summary_display, 6)}

## 7. 월별 시간배분 자료 coverage

{md_table(coverage.rename(columns={
    'activity_group':'업종','monthly_indicator_coverage':'월별배분상태','monthly_indicator_source':'월별배분자료',
    'rows':'행수','estimated_sum_eok':'월별추정합_억원','city_count':'시군구수','quarter_count':'분기수'
}).head(30), 3)}

## 8. 해석

- 이번 결과는 2020년 전체 전국 시군구 월별 산출 완료가 아니다.
- 포함 시도는 2019년 시군구×업종 annual 기준값이 있는 9개 시도다.
- 2020년 official 값은 검증에만 사용했고, 시군구 기준값·지역 share 보정에는 사용하지 않았다.
- 2020년 전국 업종별 분기비중을 사용하므로 실시간 속보 성능으로 주장하지 않는다.
- 월별 bridge는 월합→분기 재집계 보존성 검증만 통과한 산출물이다.
- 2015~2019 확장은 시군구 annual 기준값 재구성 또는 상위 시도 backcast 레이어가 먼저 필요하다.

## 9. 산출물

- `nationwide/outputs/sigungu_industry_quarterly_predictions_2020_backcast_pilot.csv`
- `nationwide/outputs/sido_quarterly_grdp_validation_2020_backcast_pilot.csv`
- `nationwide/outputs/sigungu_industry_monthly_predictions_2020_backcast_pilot.csv`
- `nationwide/outputs/monthly_bridge_summary_2020_backcast_pilot.csv`
- `nationwide/outputs/sigungu_2019_benchmark_coverage_2020_backcast_pilot.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(q_summary.to_string(index=False))
    print(monthly_summary.to_string(index=False))
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
