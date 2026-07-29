#!/usr/bin/env python3
"""2020 full-coverage sigungu-by-industry quarterly/monthly backcast bridge.

This expands the earlier 2020 limited pilot without mixing base-year money
levels.  For provinces whose current 2020-base sigungu GRVA table does not
cover 2019, old KOSIS 2015-base tables are used only to extract within-province
2019 city-by-activity shares.  Those shares are then scaled to the official
2019 province-by-activity annual total from the KOSTAT quarterly GRDP/GVA xlsx.

Allowed claim:
* 2020 is a post-hoc backcast bridge, not a Q+1-month flash forecast.
* old-base values are never used as money levels; only same-province shares.
* 2020 actual values are used only for validation.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))
sys.path.append(str(ROOT / "nationwide"))

from collect_expanded_kosis import (  # noqa: E402
    fetch_metadata,
    filter_real_gva_rows,
    get_data,
    object_selection,
    real_gva_item_id,
    years_available,
)
from kosis_common import get_kosis_key  # noqa: E402
from run_nationwide_quarterly_grdp_validation import (  # noqa: E402
    OTHER_NPT_ACTIVITY,
    SERVICE_COMPONENTS,
    VALIDATION_ACTIVITIES,
    activity_group,
    load_annual_sigungu,
    load_quarterly,
    md_table,
    national_quarter_factor,
    official_region_activity,
    province_activity_predictions,
    validate_quarters,
)
from run_sigungu_2020_backcast_monthly_bridge_pilot import build_monthly  # noqa: E402


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
RAW = ROOT / "data" / "raw" / "nationwide_2020_fullcoverage_share_bridge"
REPORT = HERE / "sigungu_2020_fullcoverage_share_bridge_backcast.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

BASE_YEAR = 2019
TARGET_YEAR = 2020
ACTIVITIES = ["광업, 제조업", "건설업", *SERVICE_COMPONENTS]
REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기도", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

OLD_SHARE_TABLES = {
    "대구": ("203", "DT_2015Y22GRDP2", "대구광역시"),
    "대전": ("206", "DT_2015Y25GRDP2", "대전광역시"),
    "울산": ("207", "DT_GRDP_2015_02", "울산광역시"),
    "충남": ("213", "DT_2015Y34GRDP2", "충청남도"),
    "경북": ("216", "DT_I30003", "경상북도"),
    "경남": ("217", "DT_2015Y38GRDP2", "경상남도"),
    "제주": ("218", "DT_2015Y39GRDP2", "제주특별자치도"),
}


def norm_text(value: Any) -> str:
    return str(value or "").replace(" ", "").replace("·", "").replace(",", "")


def find_dimension(rows: list[dict[str, Any]], hints: tuple[str, ...], fallback: int) -> int:
    scores: list[tuple[int, int]] = []
    for idx in range(1, 9):
        obj_names = {str(row.get(f"C{idx}_OBJ_NM") or "") for row in rows[:200]}
        labels = {str(row.get(f"C{idx}_NM") or "") for row in rows[:200]}
        text = " ".join(obj_names | labels)
        score = sum(1 for h in hints if h in text)
        nonempty = sum(1 for row in rows[:200] if row.get(f"C{idx}_NM"))
        if nonempty:
            scores.append((score, idx))
    scores.sort(reverse=True)
    if scores and scores[0][0] > 0:
        return scores[0][1]
    return fallback


def official_2019_totals(x: pd.DataFrame) -> pd.DataFrame:
    return (
        x[x["year"].eq(BASE_YEAR) & x["region"].isin(REGIONS) & x["activity"].isin(ACTIVITIES)]
        .groupby(["region", "activity"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"region": "quarter_region", "activity": "activity_group", "official_value_eok": "official_2019_sido_activity_eok"})
    )


def shares_from_values(df: pd.DataFrame, source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = df[df["year"].eq(BASE_YEAR) & df["activity_group"].isin(ACTIVITIES)].copy()
    d = (
        d.groupby(["quarter_region", "province_full", "city", "activity_group"], as_index=False)
        .agg(share_value=("share_value", "sum"))
    )
    denom = (
        d.groupby(["quarter_region", "activity_group"], as_index=False)["share_value"]
        .sum()
        .rename(columns={"share_value": "province_activity_share_value"})
    )
    d = d.merge(denom, on=["quarter_region", "activity_group"], how="left")
    d["city_activity_share"] = d["share_value"] / d["province_activity_share_value"]
    d["share_source"] = source
    d = d[d["city_activity_share"].replace([math.inf, -math.inf], pd.NA).notna()].copy()
    audit = (
        d.groupby(["quarter_region", "activity_group", "share_source"], as_index=False)
        .agg(city_count=("city", "nunique"), share_sum=("city_activity_share", "sum"), source_value_sum=("share_value", "sum"))
    )
    audit["share_sum_error"] = audit["share_sum"] - 1.0
    return d[["quarter_region", "province_full", "city", "activity_group", "city_activity_share", "share_source"]], audit


def current_source_shares() -> tuple[pd.DataFrame, pd.DataFrame]:
    annual, _inventory = load_annual_sigungu()
    d = annual[annual["year"].eq(BASE_YEAR)].copy()
    d = d.rename(columns={"annual_gva_eok": "share_value"})
    d["share_source"] = "2020기준 KOSIS 시군구 자료 구성비"
    return shares_from_values(
        d[["quarter_region", "province_full", "city", "activity_group", "year", "share_value"]],
        "2020기준 KOSIS 시군구 자료 구성비",
    )


def collect_old_table(api_key: str, region: str, org_id: str, tbl_id: str, province_full: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    info = fetch_metadata(org_id, tbl_id)
    period = years_available(info, ("2019",))
    if period is None:
        raise RuntimeError(f"{org_id}/{tbl_id} has no 2019 period")
    item_id = real_gva_item_id(info)
    if not item_id:
        raise RuntimeError(f"{org_id}/{tbl_id} real GVA item not identified")
    obj = object_selection(info)
    rows = get_data(api_key, org_id=org_id, tbl_id=tbl_id, item_id=item_id, period="Y", start="2019", end="2019", obj=obj)
    rows, filtered_item_code = filter_real_gva_rows(rows)
    if not rows:
        raise RuntimeError(f"{org_id}/{tbl_id} returned no rows after real-GVA filter")
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"kosis_{org_id}_{tbl_id}_2019_real_gva_rows.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    city_dim = find_dimension(rows, ("시군구", "시군별", "구군", "행정구역"), 1)
    activity_dim = find_dimension(rows, ("경제활동", "산업", "업종"), 2 if city_dim != 2 else 1)
    d = pd.DataFrame(rows)
    d["year"] = pd.to_numeric(d["PRD_DE"], errors="coerce").astype("Int64")
    d["city"] = d[f"C{city_dim}_NM"].astype(str)
    d["activity_group"] = d[f"C{activity_dim}_NM"].map(activity_group)
    d["share_value"] = pd.to_numeric(d["DT"], errors="coerce")
    aggregate_city = str(d["city"].dropna().iloc[0])
    out = d[
        d["year"].eq(BASE_YEAR)
        & d["activity_group"].isin(ACTIVITIES)
        & d["share_value"].notna()
        & d["city"].ne(aggregate_city)
    ].copy()
    out["quarter_region"] = region
    out["province_full"] = province_full
    spec = {
        "quarter_region": region,
        "province_full": province_full,
        "org_id": org_id,
        "tbl_id": tbl_id,
        "item_id": item_id,
        "city_dimension": city_dim,
        "activity_dimension": activity_dim,
        "filtered_item_code": filtered_item_code,
        "aggregate_city_removed": aggregate_city,
        "rows": int(len(out)),
        "city_count": int(out["city"].nunique()),
        "activity_count": int(out["activity_group"].nunique()),
    }
    return out[["quarter_region", "province_full", "city", "activity_group", "year", "share_value"]], spec


def old_source_shares() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    api_key = get_kosis_key()
    frames: list[pd.DataFrame] = []
    specs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for region, (org_id, tbl_id, province_full) in OLD_SHARE_TABLES.items():
        try:
            d, spec = collect_old_table(api_key, region, org_id, tbl_id, province_full)
            frames.append(d)
            specs.append(spec)
        except Exception as exc:
            failures.append({"quarter_region": region, "org_id": org_id, "tbl_id": tbl_id, "error": str(exc)})
    if not frames:
        return pd.DataFrame(), pd.DataFrame(specs), pd.DataFrame(failures)
    shares, audit = shares_from_values(pd.concat(frames, ignore_index=True), "2015기준 구계열 내부구성비")
    spec_df = pd.DataFrame(specs)
    if failures:
        spec_df = pd.concat([spec_df, pd.DataFrame(failures)], ignore_index=True, sort=False)
    return shares, audit, spec_df


def build_scaled_basis(x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    current_shares, current_audit = current_source_shares()
    old_shares, old_audit, old_specs = old_source_shares()
    all_shares = pd.concat([current_shares, old_shares], ignore_index=True)
    all_shares = all_shares.sort_values(["quarter_region", "activity_group", "share_source"])
    all_shares = all_shares.drop_duplicates(["quarter_region", "city", "activity_group"], keep="first")

    official = official_2019_totals(x)
    basis = all_shares.merge(official, on=["quarter_region", "activity_group"], how="left")
    missing = basis[basis["official_2019_sido_activity_eok"].isna()]
    if not missing.empty:
        raise RuntimeError(f"missing 2019 official totals: {missing[['quarter_region','activity_group']].drop_duplicates().to_dict('records')[:10]}")
    basis["annual_gva_eok"] = basis["city_activity_share"] * basis["official_2019_sido_activity_eok"]
    basis["year"] = BASE_YEAR
    basis["table_id"] = "share_scaled_2019_basis"
    basis["table_name"] = "2019 city-by-activity shares scaled to official 2019 province-by-activity total"
    basis["latest_change_date"] = "share_bridge_scaled_to_2019_official_sido_activity"
    basis["basis_source"] = basis["share_source"] + "→2019 시도×업종 공식총량"

    sejong = official[official["quarter_region"].eq("세종")].copy()
    sejong["province_full"] = "세종특별자치시"
    sejong["city"] = "세종시"
    sejong["city_activity_share"] = 1.0
    sejong["share_source"] = "세종 단층"
    sejong["annual_gva_eok"] = sejong["official_2019_sido_activity_eok"]
    sejong["year"] = BASE_YEAR
    sejong["table_id"] = "pseudo_sejong_one_tier_from_2019_official_sido_activity"
    sejong["table_name"] = "세종 단층 basis from official 2019 province-by-activity total"
    sejong["latest_change_date"] = "share_bridge_scaled_to_2019_official_sido_activity"
    sejong["basis_source"] = "세종 단층→2019 시도×업종 공식총량"

    basis = pd.concat([basis, sejong], ignore_index=True, sort=False)
    keep = ["quarter_region", "province_full", "table_id", "table_name", "year", "city", "activity_group", "annual_gva_eok", "latest_change_date", "basis_source", "city_activity_share", "official_2019_sido_activity_eok", "share_source"]
    basis = basis[keep].copy()

    basis_audit = (
        basis.groupby(["quarter_region", "activity_group", "share_source"], as_index=False)
        .agg(
            city_count=("city", "nunique"),
            basis_sum_eok=("annual_gva_eok", "sum"),
            official_2019_sido_activity_eok=("official_2019_sido_activity_eok", "first"),
            share_sum=("city_activity_share", "sum"),
        )
    )
    basis_audit["basis_scale_error_eok"] = basis_audit["basis_sum_eok"] - basis_audit["official_2019_sido_activity_eok"]
    basis_audit["abs_basis_scale_error_eok"] = basis_audit["basis_scale_error_eok"].abs()
    share_audit = pd.concat([current_audit, old_audit], ignore_index=True, sort=False)
    return basis, basis_audit, pd.concat([share_audit, old_specs], ignore_index=True, sort=False)


def build_quarterly_2020(basis: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    factors = national_quarter_factor(x)
    q = factors[factors["year"].eq(TARGET_YEAR) & factors["activity"].isin(ACTIVITIES)].copy()
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
    city_q["track"] = "fullcoverage_2020_share_bridge_backcast"

    official = official_region_activity(x)
    other_official_y = (
        official[
            official["activity"].eq(OTHER_NPT_ACTIVITY)
            & official["region"].isin(REGIONS)
            & official["year"].eq(BASE_YEAR)
        ]
        .groupby(["region", "year"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"region": "quarter_region", "official_value_eok": "official_other_npt_annual_eok"})
    )
    other_factor = factors[factors["year"].eq(TARGET_YEAR) & factors["activity"].eq(OTHER_NPT_ACTIVITY)].copy()
    other_rows: list[pd.DataFrame] = []
    for region in REGIONS:
        vals = other_official_y[other_official_y["quarter_region"].eq(region)]["official_other_npt_annual_eok"]
        if vals.empty:
            continue
        tmp = other_factor.copy()
        tmp["quarter_region"] = region
        tmp["year"] = TARGET_YEAR
        tmp["prior_other_npt_annual_eok"] = float(vals.iloc[0])
        tmp["predicted_other_npt_eok"] = tmp["prior_other_npt_annual_eok"] * tmp["quarter_factor_from_prev_annual"]
        tmp["other_npt_source"] = f"official_prior_year_{BASE_YEAR}"
        tmp["track"] = "fullcoverage_2020_share_bridge_backcast"
        other_rows.append(tmp)
    other_q = pd.concat(other_rows, ignore_index=True)[
        ["track", "quarter_region", "year", "quarter", "period", "predicted_other_npt_eok", "other_npt_source", "quarter_factor_from_prev_annual"]
    ]
    return city_q, other_q


def write_outputs(
    basis: pd.DataFrame,
    basis_audit: pd.DataFrame,
    share_audit: pd.DataFrame,
    city_q: pd.DataFrame,
    other_q: pd.DataFrame,
    pred_act: pd.DataFrame,
    act_val: pd.DataFrame,
    total_val: pd.DataFrame,
    q_summary: pd.DataFrame,
    act_summary: pd.DataFrame,
    monthly: pd.DataFrame,
    monthly_summary: pd.DataFrame,
    q_audit: pd.DataFrame,
    month_share_audit: pd.DataFrame,
    coverage: pd.DataFrame,
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    basis.to_csv(OUT / "sigungu_2019_share_scaled_basis_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    basis_audit.to_csv(OUT / "sigungu_2019_share_scaled_basis_audit_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    share_audit.to_csv(OUT / "sigungu_2019_share_source_audit_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    city_q.to_csv(OUT / "sigungu_industry_quarterly_predictions_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    other_q.to_csv(OUT / "sido_other_npt_quarterly_predictions_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    pred_act.to_csv(OUT / "sido_activity_quarterly_predictions_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    act_val.to_csv(OUT / "sido_activity_quarterly_validation_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    total_val.to_csv(OUT / "sido_quarterly_grdp_validation_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    q_summary.to_csv(OUT / "sido_quarterly_grdp_summary_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    act_summary.to_csv(OUT / "sido_activity_quarterly_summary_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(OUT / "sigungu_industry_monthly_predictions_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    monthly_summary.to_csv(OUT / "monthly_bridge_summary_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    q_audit.to_csv(OUT / "monthly_bridge_quarter_reaggregation_audit_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    month_share_audit.to_csv(OUT / "monthly_bridge_share_integrity_audit_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(OUT / "monthly_bridge_indicator_coverage_2020_fullcoverage_backcast.csv", index=False, encoding="utf-8-sig")


def main() -> int:
    x = load_quarterly()
    basis, basis_audit, share_audit = build_scaled_basis(x)
    city_q, other_q = build_quarterly_2020(basis, x)
    pred_act = province_activity_predictions(city_q, other_q)
    act_val, total_val, _year_summary = validate_quarters(pred_act, x)
    monthly, q_audit, month_share_audit, coverage = build_monthly(city_q)

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
                "bad_month_count_cells": int(month_share_audit["months"].ne(3).sum()),
                "bad_month_share_sum_cells": int(month_share_audit["abs_share_sum_error"].gt(1e-10).sum()),
                "negative_month_value_cells": int(month_share_audit["negative_month_values"].sum()),
                "max_abs_basis_scale_error_eok": float(basis_audit["abs_basis_scale_error_eok"].max()),
                "bad_basis_scale_cells_gt_1won_equiv": int(basis_audit["abs_basis_scale_error_eok"].gt(1e-8).sum()),
            }
        ]
    )

    write_outputs(
        basis,
        basis_audit,
        share_audit,
        city_q,
        other_q,
        pred_act,
        act_val,
        total_val,
        q_summary,
        act_summary,
        monthly,
        monthly_summary,
        q_audit,
        month_share_audit,
        coverage,
    )

    source_summary = (
        basis.groupby(["share_source"], as_index=False)
        .agg(province_count=("quarter_region", "nunique"), city_units=("city", "nunique"), rows=("city", "size"), annual_sum_eok=("annual_gva_eok", "sum"))
        .sort_values("share_source")
    )
    basis_region_summary = (
        basis.groupby(["quarter_region", "share_source"], as_index=False)
        .agg(city_count=("city", "nunique"), activity_count=("activity_group", "nunique"), annual_sum_eok=("annual_gva_eok", "sum"))
        .sort_values(["quarter_region", "share_source"])
    )

    monthly_summary_display = monthly_summary.rename(
        columns={
            "year": "연도",
            "base_year": "기준연도",
            "monthly_rows": "월별행",
            "province_count": "시도수",
            "city_count": "시군구수",
            "activity_count": "업종수",
            "indicator_rows_pct": "월별지표적용행_pct",
            "fallback_equal_split_rows_pct": "균등분할행_pct",
            "max_abs_quarter_reaggregation_error_eok": "최대분기재집계오차_억원",
            "bad_quarter_cells_gt_1won_equiv": "분기재집계오류셀",
            "bad_month_count_cells": "월수오류셀",
            "bad_month_share_sum_cells": "월비중오류셀",
            "negative_month_value_cells": "음수월값셀",
            "max_abs_basis_scale_error_eok": "최대기준값재스케일오차_억원",
            "bad_basis_scale_cells_gt_1won_equiv": "기준값재스케일오류셀",
        }
    )
    report = f"""# 2020 전국 시군구×업종 분기·월 share-bridge backcast

생성시각: {CREATED_AT}

## 1. 목적

2021~2025 전국 `시군구×업종×월` bridge를 2020년까지 확장할 때, 현재 2020 기준 KOSIS 표가 2019년을 제공하지 않는 시도를 어떻게 보강할 수 있는지 검증했다. 이 결과는 **전국 17개 시도 경계를 모두 보존한 2020 사후 backcast bridge**이며, 실시간 속보 성능으로 주장하지 않는다.

## 2. 기준값 생성 원칙

| 원칙 | 적용 |
| --- | --- |
| 구계열 금액 직접 사용 금지 | 2015 기준 구계열 표는 동일 시도·동일 업종 안의 2019 시군구 구성비만 사용 |
| 기준년 통일 | 모든 시군구 구성비를 2020 기준 2019 시도×업종 공식 총량에 곱해 재스케일 |
| 2020 actual 유출 차단 | 2020 공식값은 시도×분기 actual 검증에만 사용 |
| 세종 처리 | 세종은 하위 시군구가 없는 단층 지역으로 `세종시` 1개 단위 처리 |

## 3. 기준값 출처별 규모

{md_table(source_summary.rename(columns={'share_source':'기준값_출처','province_count':'시도수','city_units':'시군구수','rows':'행수','annual_sum_eok':'2019_기준값합_억원'}), 3)}

## 4. 시도별 기준값 출처

{md_table(basis_region_summary.rename(columns={'quarter_region':'시도','share_source':'기준값_출처','city_count':'시군구수','activity_count':'업종수','annual_sum_eok':'2019_기준값합_억원'}), 3)}

## 5. 기준값 재스케일 검증

시군구 기준값 합계가 2019 시도×업종 공식 총량과 일치하는지 검증했다. 이 검증은 구계열 비중을 사용한 시도에서도 기준년 혼합 금액이 남지 않았는지를 확인하는 절차다.

{md_table(monthly_summary_display[['연도','기준연도','시도수','시군구수','업종수','최대기준값재스케일오차_억원','기준값재스케일오류셀']], 9)}

## 6. 2020 시도 GRDP 집계검증

시군구×업종 추정값을 시도 단위로 합산하고, 기타산업 및 순생산물세를 별도 bridge로 더해 2020년 시도 분기 GRDP actual과 비교했다.

{md_table(q_summary.rename(columns={
    'track':'트랙','province_count':'시도수','quarter_rows':'분기검증행','predicted_sum_eok':'예측합_억원',
    'actual_sum_eok':'실제합_억원','abs_error_sum_eok':'절대오차합_억원','wape_pct':'WAPE_pct','max_ape_pct':'최대오차율_pct'
}), 3)}

## 7. 2020 업종별 집계검증

{md_table(act_summary.rename(columns={
    'activity':'업종','province_quarter_rows':'시도분기행','predicted_sum_eok':'예측합_억원',
    'actual_sum_eok':'실제합_억원','abs_error_sum_eok':'절대오차합_억원','wape_pct':'WAPE_pct','max_ape_pct':'최대오차율_pct'
}), 3)}

## 8. 월별 bridge 보존성 검증

월별 값은 분기 추정값을 3개월로 배분한 운영 bridge다. 월별 official actual이 없으므로 월별 정확도 검증이 아니라 `월합 = 분기 추정값` 보존성을 검증했다.

{md_table(monthly_summary_display.drop(columns=['최대기준값재스케일오차_억원','기준값재스케일오류셀']), 6)}

## 9. 해석

- 2020년 전체 17개 시도 시군구×업종×월 **사후 backcast 산출**은 가능하다.
- 단, 2020년 전국 업종별 분기 경로를 사용하므로 `Q+1개월` 속보 산출이 아니라 사후 backcast다.
- 2015 기준 구계열은 금액 수준이 아니라 내부 구성비로만 사용했다.
- 기준값 재스케일 검증과 월합→분기 재집계 검증은 모두 산술 보존성 검증이다.
- 재스케일 오류 0셀은 시군구 기준값 합계가 2019 시도×업종 공식총량과 일치한다는 뜻이며, 시군구 내부 구성비의 actual 정확도를 직접 증명하지는 않는다.
- 구계열 업종명은 2020 기준 업종명과 완전히 같다고 단정하지 않고, `광업+제조업` 결합 및 `교육서비스업(정부)` 같은 명칭 예외를 매핑 감사 대상으로 유지한다.
- 세종은 하위 시군구 배분이 없는 단층 처리이므로 전국 17개 시도 경계 보존에는 포함하되, 세종 자체를 시군구 공간배분 성능 사례로 해석하지 않는다.
- 2015~2019로 더 내려가려면 같은 방식의 구계열 구성비와 시도 공식 총량 연결이 필요하다.

## 10. 산출물

- `nationwide/outputs/sigungu_2019_share_scaled_basis_2020_fullcoverage_backcast.csv`
- `nationwide/outputs/sido_quarterly_grdp_validation_2020_fullcoverage_backcast.csv`
- `nationwide/outputs/sido_activity_quarterly_validation_2020_fullcoverage_backcast.csv`
- `nationwide/outputs/sigungu_industry_monthly_predictions_2020_fullcoverage_backcast.csv`
- `nationwide/outputs/monthly_bridge_summary_2020_fullcoverage_backcast.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(q_summary.to_string(index=False))
    print(monthly_summary.to_string(index=False))
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
