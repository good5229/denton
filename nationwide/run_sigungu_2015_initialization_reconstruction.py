#!/usr/bin/env python3
"""2015 initialization-year sigungu quarterly/monthly reconstruction.

The ordinary out-of-year rule needs a prior-year sigungu-by-activity basis.
2015 has no 2014 local basis in the current public-data bundle, so it is
handled separately as an initialization-year *post-hoc reconstruction*.

This is not a forecast and not Q+1-month flash performance:
* 2015 city-by-activity shares are scaled to 2015 province-by-activity official
  annual totals.
* 2015 national same-year quarterly shares are used for the quarterly path.
* 2015 actuals are used to create the initialization boundary and to validate
  upper-level consistency.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "nationwide"))

from run_nationwide_quarterly_grdp_validation import (  # noqa: E402
    MAIN_ACTIVITIES,
    OTHER_NPT_ACTIVITY,
    SERVICE_COMPONENTS,
    VALIDATION_ACTIVITIES,
    activity_group,
    load_quarterly,
    md_table,
    official_region_activity,
    province_activity_predictions,
    validate_quarters,
)
from run_nationwide_monthly_bridge_validation import short_region  # noqa: E402
from run_sigungu_2016_2020_fullcoverage_share_bridge_backcast import (  # noqa: E402
    ACTIVITIES,
    REGIONS,
    build_scaled_basis,
    collect_shares,
)
from run_sigungu_2020_backcast_monthly_bridge_pilot import (  # noqa: E402
    build_monthly_weights_for_year,
    equal_month_rows,
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = HERE / "sigungu_2015_initialization_reconstruction.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
YEAR = 2015


def same_year_quarter_share(x: pd.DataFrame) -> pd.DataFrame:
    nat = x[x["region"].eq("전국") & x["activity"].isin(VALIDATION_ACTIVITIES)].copy()
    nat["national_annual_eok"] = nat.groupby(["activity", "year"])["official_value_eok"].transform("sum")
    nat["quarter_share_same_year"] = nat["official_value_eok"] / nat["national_annual_eok"]
    return nat[["activity", "year", "quarter", "period", "quarter_share_same_year"]].dropna()


def build_quarterly_2015(basis: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    b = basis[basis["year"].eq(YEAR)].copy()
    shares = same_year_quarter_share(x)
    q = shares[shares["year"].eq(YEAR) & shares["activity"].isin(ACTIVITIES)].copy()
    pred = b.merge(q, left_on="activity_group", right_on="activity", how="inner")
    pred["year"] = YEAR
    pred["predicted_gva_eok"] = pred["annual_gva_eok"] * pred["quarter_share_same_year"]
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
            "quarter_share_same_year",
        ]
    ].copy()
    city_q["quarter_factor_from_prev_annual"] = city_q["quarter_share_same_year"]
    city_q["track"] = "initialization_2015_same_year_reconstruction"

    official = official_region_activity(x)
    other_y = (
        official[
            official["activity"].eq(OTHER_NPT_ACTIVITY)
            & official["region"].isin(REGIONS)
            & official["year"].eq(YEAR)
        ]
        .groupby(["region", "year"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"region": "quarter_region", "official_value_eok": "official_other_npt_annual_eok"})
    )
    other_factor = shares[shares["year"].eq(YEAR) & shares["activity"].eq(OTHER_NPT_ACTIVITY)].copy()
    rows: list[pd.DataFrame] = []
    for region in REGIONS:
        vals = other_y[other_y["quarter_region"].eq(region)]["official_other_npt_annual_eok"]
        if vals.empty:
            continue
        tmp = other_factor.copy()
        tmp["quarter_region"] = region
        tmp["year"] = YEAR
        tmp["predicted_other_npt_eok"] = float(vals.iloc[0]) * tmp["quarter_share_same_year"]
        tmp["other_npt_source"] = "same_year_2015_official_initialization"
        tmp["quarter_factor_from_prev_annual"] = tmp["quarter_share_same_year"]
        tmp["track"] = "initialization_2015_same_year_reconstruction"
        rows.append(tmp)
    other_q = pd.concat(rows, ignore_index=True)[
        ["track", "quarter_region", "year", "quarter", "period", "predicted_other_npt_eok", "other_npt_source", "quarter_factor_from_prev_annual"]
    ]
    return city_q, other_q


def build_monthly_2015(city_q: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q = city_q.copy()
    q["region_short"] = q["quarter_region"].map(short_region)
    weights = build_monthly_weights_for_year(q, YEAR)
    key = ["region_short", "activity_group", "year", "quarter"]
    if weights.empty:
        monthly = equal_month_rows(q)
    else:
        with_w = q.merge(weights, on=key, how="left", suffixes=("", "_indicator"))
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
    monthly = monthly[
        [
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
    ].copy()
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
    coverage = (
        monthly.groupby(["activity_group", "monthly_indicator_coverage", "monthly_indicator_source"], as_index=False)
        .agg(rows=("estimated_monthly_gva_eok", "size"), estimated_sum_eok=("estimated_monthly_gva_eok", "sum"), city_count=("city", "nunique"), quarter_count=("quarter", "nunique"))
        .sort_values(["activity_group", "monthly_indicator_coverage"])
    )
    summary = pd.DataFrame(
        [
            {
                "year": YEAR,
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
    return monthly, q_audit, share_audit, coverage, summary


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    x = load_quarterly()
    shares, specs = collect_shares()
    basis, basis_audit = build_scaled_basis(shares, x)
    basis = basis[basis["year"].eq(YEAR)].copy()
    basis_audit = basis_audit[basis_audit["year"].eq(YEAR)].copy()
    city_q, other_q = build_quarterly_2015(basis, x)
    pred_act = province_activity_predictions(city_q, other_q)
    act_val, total_val, _ = validate_quarters(pred_act, x)
    monthly, monthly_q_audit, monthly_share_audit, monthly_coverage, monthly_summary = build_monthly_2015(city_q)

    total_summary = (
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
    top_total_errors = total_val.sort_values("ape_pct", ascending=False).head(12)[
        ["quarter_region", "year", "quarter", "period", "predicted_grdp_eok", "official_grdp_eok", "error_eok", "ape_pct"]
    ].copy()
    basis_summary = pd.DataFrame(
        [
            {
                "year": YEAR,
                "province_count": basis["quarter_region"].nunique(),
                "city_count": basis[["quarter_region", "city"]].drop_duplicates().shape[0],
                "activity_count": basis["activity_group"].nunique(),
                "basis_rows": len(basis),
                "max_abs_basis_scale_error_eok": float(basis_audit["abs_basis_scale_error_eok"].max()),
                "bad_basis_scale_cells_gt_1won_equiv": int(basis_audit["abs_basis_scale_error_eok"].gt(1e-8).sum()),
            }
        ]
    )

    specs.to_csv(OUT / "sigungu_2015_initialization_share_table_specs.csv", index=False, encoding="utf-8-sig")
    basis.to_csv(OUT / "sigungu_2015_initialization_share_scaled_basis.csv", index=False, encoding="utf-8-sig")
    basis_audit.to_csv(OUT / "sigungu_2015_initialization_share_scaled_basis_audit.csv", index=False, encoding="utf-8-sig")
    city_q.to_csv(OUT / "sigungu_industry_quarterly_predictions_2015_initialization.csv", index=False, encoding="utf-8-sig")
    other_q.to_csv(OUT / "sido_other_npt_quarterly_predictions_2015_initialization.csv", index=False, encoding="utf-8-sig")
    total_val.to_csv(OUT / "sido_quarterly_grdp_validation_2015_initialization.csv", index=False, encoding="utf-8-sig")
    act_val.to_csv(OUT / "sido_activity_quarterly_validation_2015_initialization.csv", index=False, encoding="utf-8-sig")
    total_summary.to_csv(OUT / "sido_quarterly_grdp_summary_2015_initialization.csv", index=False, encoding="utf-8-sig")
    act_summary.to_csv(OUT / "sido_activity_quarterly_summary_2015_initialization.csv", index=False, encoding="utf-8-sig")
    top_total_errors.to_csv(OUT / "sido_quarterly_grdp_top_errors_2015_initialization.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(OUT / "sigungu_industry_monthly_predictions_2015_initialization.csv", index=False, encoding="utf-8-sig")
    monthly_q_audit.to_csv(OUT / "monthly_bridge_quarter_reaggregation_audit_2015_initialization.csv", index=False, encoding="utf-8-sig")
    monthly_share_audit.to_csv(OUT / "monthly_bridge_share_integrity_audit_2015_initialization.csv", index=False, encoding="utf-8-sig")
    monthly_coverage.to_csv(OUT / "monthly_bridge_indicator_coverage_2015_initialization.csv", index=False, encoding="utf-8-sig")
    monthly_summary.to_csv(OUT / "monthly_bridge_summary_2015_initialization.csv", index=False, encoding="utf-8-sig")

    report = f"""# 2015 전국 시군구×업종 초기화 연도 사후 재구성

생성시각: {CREATED_AT}

## 1. 목적

2015년은 현재 공개자료 묶음 안에 2014년 시군구×업종 기준값이 없어, 2016~2020과 같은 out-of-year 예측 검증을 수행할 수 없다. 따라서 2015년은 `초기화 연도 사후 재구성`으로 별도 분리한다.

## 2. 설계

| 항목 | 내용 |
| --- | --- |
| 기준값 | 2015 시군구×업종 구성비 × 2015 시도×업종 공식총량 |
| 분기화 | 2015 전국 업종별 동년 분기/연간 비중 |
| 월별화 | 2015 월별 지표가 있는 업종은 시간경로 적용, 없는 업종은 균등분할 |
| 검증 | 시도×분기 actual 집계와 월합→분기 보존성 |
| 금지 해석 | 예측 성능, Q+1개월 속보 성능, 시군구 내부 구성비 actual 검증 |

## 3. 기준값 규모

{md_table(basis_summary.rename(columns={
    'year':'연도','province_count':'시도수','city_count':'시군구수','activity_count':'업종수','basis_rows':'기준값행',
    'max_abs_basis_scale_error_eok':'최대재스케일오차_억원','bad_basis_scale_cells_gt_1won_equiv':'재스케일오류셀'
}), 9)}

## 4. 시도 GRDP 집계검증

{md_table(total_summary.rename(columns={
    'track':'트랙','province_count':'시도수','quarter_rows':'분기검증행','predicted_sum_eok':'예측합_억원',
    'actual_sum_eok':'실제합_억원','abs_error_sum_eok':'절대오차합_억원','wape_pct':'WAPE_pct','max_ape_pct':'최대오차율_pct'
}), 3)}

## 5. 업종별 집계검증

{md_table(act_summary.rename(columns={
    'activity':'업종','province_quarter_rows':'시도분기행','predicted_sum_eok':'예측합_억원','actual_sum_eok':'실제합_억원',
    'abs_error_sum_eok':'절대오차합_억원','wape_pct':'WAPE_pct','max_ape_pct':'최대오차율_pct'
}), 3)}

## 6. 최대오차 상위 시도·분기

{md_table(top_total_errors.rename(columns={
    'quarter_region':'시도','year':'연도','quarter':'분기','period':'시점','predicted_grdp_eok':'예측_GRDP_억원',
    'official_grdp_eok':'실제_GRDP_억원','error_eok':'오차_억원','ape_pct':'오차율_pct'
}), 3)}

## 7. 월별 bridge 보존성

{md_table(monthly_summary.rename(columns={
    'year':'연도','monthly_rows':'월별행','province_count':'시도수','city_count':'시군구수','activity_count':'업종수',
    'indicator_rows_pct':'월별지표적용행_pct','fallback_equal_split_rows_pct':'균등분할행_pct',
    'max_abs_quarter_reaggregation_error_eok':'최대분기재집계오차_억원','bad_quarter_cells_gt_1won_equiv':'분기재집계오류셀',
    'bad_month_count_cells':'월수오류셀','bad_month_share_sum_cells':'월비중오류셀','negative_month_value_cells':'음수월값셀'
}), 6)}

## 8. 해석

- 2015년 전국 17개 시도·229개 하위단위·13개 업종의 분기·월 초기화 파일은 생성 가능하다.
- 이 결과는 목표연도 공식 연간총량과 목표연도 전국 분기경로를 쓰므로 예측 성능이 아니다.
- 따라서 WAPE/APE는 모델 예측 정확도 지표가 아니라 계층 보존성·분기 재구성 일관성 지표다.
- 기준값 재스케일 오류 0셀은 상위합 보존성 검증이며 시군구 내부 구성비의 actual 정확도 증명은 아니다.
- 월별 값은 분기값 보존형 bridge이며 월별 actual 검증으로 해석하지 않는다. 특히 월별 시간경로 적용률이 {float(monthly_summary.iloc[0]['indicator_rows_pct']):.3f}%라 월별 경기변동 분석용보다는 장기 패널 정합성 보존용에 가깝다.

## 9. 산출물

- `nationwide/outputs/sigungu_industry_quarterly_predictions_2015_initialization.csv`
- `nationwide/outputs/sigungu_industry_monthly_predictions_2015_initialization.csv`
- `nationwide/outputs/sido_quarterly_grdp_validation_2015_initialization.csv`
- `nationwide/outputs/monthly_bridge_summary_2015_initialization.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(total_summary.to_string(index=False))
    print(monthly_summary.to_string(index=False))
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
