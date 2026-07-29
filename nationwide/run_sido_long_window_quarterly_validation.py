#!/usr/bin/env python3
"""Long-window province-level quarterly validation for 2016~2025.

The sigungu-level nationwide experiment is necessarily bounded by the public
annual sigungu GVA source window.  This companion audit uses the official
experimental quarterly GRDP table directly at the province/activity level to
answer a narrower but important question:

    If all 2015~2025 province quarterly actuals are available for validation,
    does the lagged-annual + national quarterly movement rule stay stable for
    a longer period than the 2021~2025 sigungu rollout?

The model input for year Y is:

* province/activity annual value from Y-1, or a recursive previous prediction;
* national activity quarterly movement in Y relative to national annual Y-1.

It does not use the target province's quarter value as an input.  The first
usable validation year is 2016 because 2015 is the initialization year for the
lagged annual basis.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
XLSX_LONG = ROOT / "data" / "processed" / "phase211_gyeonggi_2024_2025_grdp_extension" / "phase211_sido_quarterly_xlsx_long.csv"
REPORT = HERE / "sido_long_window_quarterly_validation.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

TOTAL_ACTIVITY = "지역내총생산(시장가격)"
OTHER_NPT_ACTIVITY = "기타산업 및 순생산물세"
ACTIVITIES = [
    "광업, 제조업",
    "건설업",
    "도매 및 소매업",
    "운수 및 창고업",
    "숙박 및 음식점업",
    "정보통신업",
    "금융 및 보험업",
    "부동산업",
    "사업서비스업",
    "공공 행정, 국방·사회보장",
    "교육 서비스업",
    "보건 및 사회복지업",
    "문화 및 기타서비스업",
    OTHER_NPT_ACTIVITY,
]
TOTAL_COMPONENTS = ["광업, 제조업", "건설업", "서비스업", OTHER_NPT_ACTIVITY]
SERVICE_COMPONENTS = [a for a in ACTIVITIES if a not in {"광업, 제조업", "건설업", OTHER_NPT_ACTIVITY}]
PROVINCES = [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기도",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]
LABELS = {1: "1분기+1개월", 2: "1~2분기+1개월", 3: "1~3분기+1개월", 4: "공표 후 정밀화"}


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if str(c).lower() in {"year", "연도"}:
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(round(float(x)))}")
        elif str(c).lower() in {
            "years",
            "regions",
            "available_quarters",
            "sido_years",
            "region_years_over_10pct",
            "sido_years_over_10pct",
            "sido_years_over_20pct",
            "연도수",
            "시도수",
            "사용분기수",
            "시도연도수",
            "10pct초과_시도연도수",
            "20pct초과_시도연도수",
            "10pct초과_시도수",
        }:
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(round(float(x))):,}")
        elif pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, row in v.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def wape(error: pd.Series, actual: pd.Series) -> float:
    denom = actual.abs().sum()
    if denom == 0:
        return float("nan")
    return float(error.abs().sum() / denom * 100)


def load_quarterly() -> pd.DataFrame:
    x = pd.read_csv(XLSX_LONG)
    x = x[x["year"].between(2015, 2025)].copy()
    return x


def annual_actual(x: pd.DataFrame) -> pd.DataFrame:
    return (
        x[x["region"].isin(PROVINCES) & x["activity"].isin(ACTIVITIES)]
        .groupby(["region", "activity", "year"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"official_value_eok": "annual_actual_eok"})
    )


def national_quarter_factors(x: pd.DataFrame) -> pd.DataFrame:
    nat = x[x["region"].eq("전국") & x["activity"].isin(ACTIVITIES)].copy()
    prev_annual = (
        nat.groupby(["activity", "year"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"official_value_eok": "national_prev_annual_eok", "year": "prev_year"})
    )
    nat["prev_year"] = nat["year"] - 1
    f = nat.merge(prev_annual, on=["activity", "prev_year"], how="left")
    f["quarter_factor_from_prev_annual"] = f["official_value_eok"] / f["national_prev_annual_eok"]
    return f[["activity", "year", "quarter", "period", "quarter_factor_from_prev_annual"]].dropna()


def prior_year_cumulative_shares(x: pd.DataFrame) -> pd.DataFrame:
    nat = x[x["region"].eq("전국") & x["activity"].isin([*ACTIVITIES, "서비스업"])].copy()
    nat["annual"] = nat.groupby(["activity", "year"])["official_value_eok"].transform("sum")
    nat["cum"] = nat.sort_values(["activity", "year", "quarter"]).groupby(["activity", "year"])["official_value_eok"].cumsum()
    nat["prior_year_cum_share"] = nat["cum"] / nat["annual"]
    nat["target_year"] = nat["year"] + 1
    return nat.rename(columns={"quarter": "available_quarters"})[
        ["activity", "target_year", "available_quarters", "prior_year_cum_share"]
    ]


def build_predictions(track: str, x: pd.DataFrame) -> pd.DataFrame:
    annual = annual_actual(x)
    factors = national_quarter_factors(x)
    recursive_basis: dict[tuple[str, str, int], float] = {}
    rows = []
    for year in range(2016, 2026):
        for region in PROVINCES:
            for activity in ACTIVITIES:
                if track == "recursive_no_target_actual" and year > 2016:
                    basis = recursive_basis[(region, activity, year - 1)]
                    basis_source = f"recursive_predicted_annual_{year - 1}"
                else:
                    basis = float(
                        annual[
                            annual["region"].eq(region)
                            & annual["activity"].eq(activity)
                            & annual["year"].eq(year - 1)
                        ]["annual_actual_eok"].iloc[0]
                    )
                    basis_source = f"official_prior_year_annual_{year - 1}"
                qf = factors[factors["activity"].eq(activity) & factors["year"].eq(year)]
                predicted_annual = 0.0
                for _, q in qf.iterrows():
                    pred = basis * float(q["quarter_factor_from_prev_annual"])
                    predicted_annual += pred
                    rows.append(
                        {
                            "track": track,
                            "region": region,
                            "activity": activity,
                            "year": year,
                            "quarter": int(q["quarter"]),
                            "period": q["period"],
                            "basis_eok": basis,
                            "basis_source": basis_source,
                            "quarter_factor_from_prev_annual": float(q["quarter_factor_from_prev_annual"]),
                            "predicted_value_eok": pred,
                        }
                    )
                recursive_basis[(region, activity, year)] = predicted_annual
    pred = pd.DataFrame(rows)
    svc = (
        pred[pred["activity"].isin(SERVICE_COMPONENTS)]
        .groupby(["track", "region", "year", "quarter", "period"], as_index=False)["predicted_value_eok"]
        .sum()
    )
    svc["activity"] = "서비스업"
    svc["basis_eok"] = pd.NA
    svc["basis_source"] = "sum_of_service_components"
    svc["quarter_factor_from_prev_annual"] = pd.NA
    return pd.concat([pred, svc[pred.columns]], ignore_index=True)


def validate(pred: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    off = x[x["region"].isin(PROVINCES)].copy()
    act_val = pred.merge(
        off[off["activity"].isin([*ACTIVITIES, "서비스업"])][["region", "activity", "year", "quarter", "period", "official_value_eok"]],
        on=["region", "activity", "year", "quarter", "period"],
        how="left",
    )
    act_val["error_eok"] = act_val["predicted_value_eok"] - act_val["official_value_eok"]
    act_val["abs_error_eok"] = act_val["error_eok"].abs()
    act_val["ape_pct"] = act_val["abs_error_eok"] / act_val["official_value_eok"].abs() * 100

    total_pred = (
        pred[pred["activity"].isin(TOTAL_COMPONENTS)]
        .groupby(["track", "region", "year", "quarter", "period"], as_index=False)["predicted_value_eok"]
        .sum()
        .rename(columns={"predicted_value_eok": "predicted_grdp_eok"})
    )
    total_off = off[off["activity"].eq(TOTAL_ACTIVITY)][["region", "year", "quarter", "period", "official_value_eok"]].rename(
        columns={"official_value_eok": "official_grdp_eok"}
    )
    grdp_val = total_pred.merge(total_off, on=["region", "year", "quarter", "period"], how="left")
    grdp_val["error_eok"] = grdp_val["predicted_grdp_eok"] - grdp_val["official_grdp_eok"]
    grdp_val["abs_error_eok"] = grdp_val["error_eok"].abs()
    grdp_val["ape_pct"] = grdp_val["abs_error_eok"] / grdp_val["official_grdp_eok"].abs() * 100

    shares = prior_year_cumulative_shares(x)
    op_rows = []
    op_act_rows = []
    for track in sorted(pred["track"].unique()):
        for region in PROVINCES:
            for year in range(2016, 2026):
                for k in [1, 2, 3, 4]:
                    pc = (
                        pred[
                            pred["track"].eq(track)
                            & pred["region"].eq(region)
                            & pred["year"].eq(year)
                            & pred["quarter"].le(k)
                            & pred["activity"].isin([*ACTIVITIES, "서비스업"])
                        ]
                        .groupby("activity", as_index=False)["predicted_value_eok"]
                        .sum()
                        .rename(columns={"predicted_value_eok": "predicted_cumulative_eok"})
                    )
                    oc = (
                        off[
                            off["region"].eq(region)
                            & off["year"].eq(year)
                            & off["quarter"].le(k)
                            & off["activity"].isin([*ACTIVITIES, "서비스업"])
                        ]
                        .groupby("activity", as_index=False)["official_value_eok"]
                        .sum()
                        .rename(columns={"official_value_eok": "official_cumulative_eok"})
                    )
                    oa = (
                        off[
                            off["region"].eq(region)
                            & off["year"].eq(year)
                            & off["activity"].isin([*ACTIVITIES, "서비스업"])
                        ]
                        .groupby("activity", as_index=False)["official_value_eok"]
                        .sum()
                        .rename(columns={"official_value_eok": "official_annual_eok"})
                    )
                    a = pc.merge(oc, on="activity", how="left").merge(oa, on="activity", how="left")
                    a["track"] = track
                    a["region"] = region
                    a["year"] = year
                    a["available_quarters"] = k
                    a["operating_label"] = LABELS[k]
                    if k < 4:
                        a = a.merge(
                            shares[shares["target_year"].eq(year) & shares["available_quarters"].eq(k)],
                            left_on=["activity", "available_quarters"],
                            right_on=["activity", "available_quarters"],
                            how="left",
                        )
                        a["annualized_predicted_eok"] = a["predicted_cumulative_eok"] / a["prior_year_cum_share"]
                    else:
                        a["prior_year_cum_share"] = 1.0
                        a["annualized_predicted_eok"] = a["predicted_cumulative_eok"]
                    a["annualized_error_eok"] = a["annualized_predicted_eok"] - a["official_annual_eok"]
                    a["annualized_ape_pct"] = a["annualized_error_eok"].abs() / a["official_annual_eok"].abs() * 100
                    a["cumulative_error_eok"] = a["predicted_cumulative_eok"] - a["official_cumulative_eok"]
                    a["cumulative_ape_pct"] = a["cumulative_error_eok"].abs() / a["official_cumulative_eok"].abs() * 100
                    op_act_rows.append(a)
                    main = a[a["activity"].isin(TOTAL_COMPONENTS)]
                    pred_cum = float(main["predicted_cumulative_eok"].sum())
                    pred_ann = float(main["annualized_predicted_eok"].sum())
                    off_cum = float(
                        off[
                            off["region"].eq(region)
                            & off["activity"].eq(TOTAL_ACTIVITY)
                            & off["year"].eq(year)
                            & off["quarter"].le(k)
                        ]["official_value_eok"].sum()
                    )
                    off_ann = float(
                        off[off["region"].eq(region) & off["activity"].eq(TOTAL_ACTIVITY) & off["year"].eq(year)][
                            "official_value_eok"
                        ].sum()
                    )
                    op_rows.append(
                        {
                            "track": track,
                            "region": region,
                            "year": year,
                            "available_quarters": k,
                            "operating_label": LABELS[k],
                            "predicted_cumulative_grdp_eok": pred_cum,
                            "official_cumulative_grdp_eok": off_cum,
                            "cumulative_error_eok": pred_cum - off_cum,
                            "cumulative_ape_pct": abs(pred_cum - off_cum) / abs(off_cum) * 100,
                            "annualized_predicted_grdp_eok": pred_ann,
                            "official_annual_grdp_eok": off_ann,
                            "annualized_error_eok": pred_ann - off_ann,
                            "annualized_ape_pct": abs(pred_ann - off_ann) / abs(off_ann) * 100,
                        }
                    )
    return act_val, grdp_val, pd.DataFrame(op_rows), pd.concat(op_act_rows, ignore_index=True)


def summarize(op: pd.DataFrame, op_act: pd.DataFrame, grdp_val: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    operating = (
        op.groupby(["track", "available_quarters", "operating_label"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "years": g["year"].nunique(),
                    "regions": g["region"].nunique(),
                    "annualized_wape_pct": wape(g["annualized_error_eok"], g["official_annual_grdp_eok"]),
                    "annualized_max_ape_pct": g["annualized_ape_pct"].max(),
                    "cumulative_wape_pct": wape(g["cumulative_error_eok"], g["official_cumulative_grdp_eok"]),
                    "cumulative_max_ape_pct": g["cumulative_ape_pct"].max(),
                    "region_years_over_10pct": int((g["annualized_ape_pct"] > 10).sum()),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    by_year = (
        op.groupby(["track", "available_quarters", "operating_label", "year"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "regions": g["region"].nunique(),
                    "annualized_wape_pct": wape(g["annualized_error_eok"], g["official_annual_grdp_eok"]),
                    "annualized_max_ape_pct": g["annualized_ape_pct"].max(),
                    "regions_over_10pct": int((g["annualized_ape_pct"] > 10).sum()),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    by_activity = (
        op_act.groupby(["track", "available_quarters", "operating_label", "activity"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "sido_years": g[["region", "year"]].drop_duplicates().shape[0],
                    "annualized_wape_pct": wape(g["annualized_error_eok"], g["official_annual_eok"]),
                    "annualized_max_ape_pct": g["annualized_ape_pct"].max(),
                    "sido_years_over_10pct": int((g["annualized_ape_pct"] > 10).sum()),
                    "sido_years_over_20pct": int((g["annualized_ape_pct"] > 20).sum()),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    quarter_boundary = (
        grdp_val.groupby(["track", "year"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "quarters": g["period"].nunique(),
                    "quarterly_wape_pct": wape(g["error_eok"], g["official_grdp_eok"]),
                    "max_quarter_ape_pct": g["ape_pct"].max(),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    return operating, by_year, by_activity, quarter_boundary


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    x = load_quarterly()
    predictions = pd.concat(
        [
            build_predictions("recursive_no_target_actual", x),
            build_predictions("prior_year_province_anchor", x),
        ],
        ignore_index=True,
    )
    act_val, grdp_val, op, op_act = validate(predictions, x)
    operating, by_year, by_activity, quarter_boundary = summarize(op, op_act, grdp_val)

    predictions.to_csv(OUT / "sido_long_window_activity_quarterly_predictions.csv", index=False, encoding="utf-8-sig")
    act_val.to_csv(OUT / "sido_long_window_activity_quarterly_validation.csv", index=False, encoding="utf-8-sig")
    grdp_val.to_csv(OUT / "sido_long_window_grdp_quarterly_validation.csv", index=False, encoding="utf-8-sig")
    op.to_csv(OUT / "sido_long_window_operating_grdp_validation.csv", index=False, encoding="utf-8-sig")
    op_act.to_csv(OUT / "sido_long_window_operating_activity_validation.csv", index=False, encoding="utf-8-sig")
    operating.to_csv(OUT / "sido_long_window_operating_summary.csv", index=False, encoding="utf-8-sig")
    by_year.to_csv(OUT / "sido_long_window_yearly_summary.csv", index=False, encoding="utf-8-sig")
    by_activity.to_csv(OUT / "sido_long_window_activity_summary.csv", index=False, encoding="utf-8-sig")
    quarter_boundary.to_csv(OUT / "sido_long_window_quarter_boundary_summary.csv", index=False, encoding="utf-8-sig")

    headline = operating[
        ["track", "available_quarters", "operating_label", "years", "regions", "annualized_wape_pct", "annualized_max_ape_pct", "region_years_over_10pct"]
    ]
    worst_activity = (
        by_activity.sort_values(["available_quarters", "annualized_wape_pct"], ascending=[True, False])
        .groupby(["track", "available_quarters"], group_keys=False)
        .head(7)
    )
    worst_years = (
        by_year.sort_values(["available_quarters", "annualized_wape_pct"], ascending=[True, False])
        .groupby(["track", "available_quarters"], group_keys=False)
        .head(5)
    )
    boundary = quarter_boundary.groupby("track", as_index=False).agg(
        years=("year", "count"),
        mean_quarterly_wape_pct=("quarterly_wape_pct", "mean"),
        max_year_quarterly_wape_pct=("quarterly_wape_pct", "max"),
        max_quarter_ape_pct=("max_quarter_ape_pct", "max"),
    )

    report = f"""# 시도 분기 GRDP 장기 검증: 2016~2025

생성시각: {CREATED_AT}

## 목적

시군구 annual actual의 공표범위 한계와 별도로, 통계청 실험적 시도 분기 GRDP 표가 제공하는 2015~2025 장기 actual을 이용해 `직전연도 연간값 × 전국 분기 움직임` 규칙이 10년 창에서도 안정적인지 검증했다.

2015년은 전년도 기준값이 없는 초기화 연도이므로 자료 coverage에는 포함하되 성능 검증은 2016~2025년으로 수행했다.

## 검증 설계

| 항목 | 내용 |
| --- | --- |
| 자료 | `phase211_sido_quarterly_xlsx_long.csv` |
| 검증연도 | 2016~2025년 |
| 지역 | 17개 시도 |
| 업종 | 광업·제조업, 건설업, 서비스 세부업종, 기타산업 및 순생산물세 |
| 예측입력 | 전년도 시도×업종 연간값, 목표연도 전국×업종 분기 움직임 |
| 금지 | 목표 시도×업종 분기 actual을 예측 입력으로 사용하지 않음 |
| 해석 | 시군구 검증의 대체가 아니라 2015~2025 장기 안정성 보조검증 |

## 운영시점별 GRDP 성능

{md_table(headline.rename(columns={
    "track": "트랙",
    "available_quarters": "사용분기수",
    "operating_label": "모의운영시점",
    "years": "연도수",
    "regions": "시도수",
    "annualized_wape_pct": "연간환산WAPE_pct",
    "annualized_max_ape_pct": "최대시도연도오차율_pct",
    "region_years_over_10pct": "10pct초과_시도연도수",
}), 3)}

## 연도별 취약 구간

{md_table(worst_years[[
    "track", "available_quarters", "operating_label", "year", "regions", "annualized_wape_pct", "annualized_max_ape_pct", "regions_over_10pct"
]].rename(columns={
    "track": "트랙",
    "available_quarters": "사용분기수",
    "operating_label": "모의운영시점",
    "year": "연도",
    "regions": "시도수",
    "annualized_wape_pct": "연간환산WAPE_pct",
    "annualized_max_ape_pct": "최대시도오차율_pct",
    "regions_over_10pct": "10pct초과_시도수",
}), 3)}

## 업종별 취약 구간

{md_table(worst_activity[[
    "track", "available_quarters", "operating_label", "activity", "sido_years", "annualized_wape_pct", "annualized_max_ape_pct", "sido_years_over_10pct", "sido_years_over_20pct"
]].rename(columns={
    "track": "트랙",
    "available_quarters": "사용분기수",
    "operating_label": "모의운영시점",
    "activity": "업종",
    "sido_years": "시도연도수",
    "annualized_wape_pct": "업종WAPE_pct",
    "annualized_max_ape_pct": "최대시도연도오차율_pct",
    "sido_years_over_10pct": "10pct초과_시도연도수",
    "sido_years_over_20pct": "20pct초과_시도연도수",
}), 3)}

## 분기 직접검증 경계

{md_table(boundary.rename(columns={
    "track": "트랙",
    "years": "연도수",
    "mean_quarterly_wape_pct": "연평균_분기WAPE_pct",
    "max_year_quarterly_wape_pct": "연도최대_분기WAPE_pct",
    "max_quarter_ape_pct": "최대분기오차율_pct",
}), 3)}

## 판정

1. 2016~2025 장기 창에서도 시도 총량 GRDP는 대체로 낮은 WAPE를 유지하는지 확인한다.
2. 업종별로 10% 초과 시도연도 조합이 남는 경우, 해당 업종은 시군구 세부 추정에서도 직접 활동자료 route를 우선 검토해야 한다.
3. 이 검증은 목표 시도 분기 actual을 입력하지 않는 장기 안정성 감사다. 다만 전국 분기 움직임 자체는 사후 백테스트 빈티지이므로, 실시간 운용 성과라고 주장하려면 원천별 공표시점 빈티지를 별도로 잠가야 한다.

## 산출물

- `nationwide/outputs/sido_long_window_activity_quarterly_predictions.csv`
- `nationwide/outputs/sido_long_window_activity_quarterly_validation.csv`
- `nationwide/outputs/sido_long_window_grdp_quarterly_validation.csv`
- `nationwide/outputs/sido_long_window_operating_grdp_validation.csv`
- `nationwide/outputs/sido_long_window_operating_activity_validation.csv`
- `nationwide/outputs/sido_long_window_operating_summary.csv`
- `nationwide/outputs/sido_long_window_yearly_summary.csv`
- `nationwide/outputs/sido_long_window_activity_summary.csv`
- `nationwide/outputs/sido_long_window_quarter_boundary_summary.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(operating.to_string(index=False))
    print(boundary.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
