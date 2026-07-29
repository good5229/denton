#!/usr/bin/env python3
"""2016-2020 full-coverage sigungu share-bridge quarterly backcast.

This extends the 2020 share-bridge idea to the longest defensible pre-2021
window.  2015 is an initialization year because the model needs a prior-year
city-by-activity basis.  Therefore validation is 2016-2020.

The script uses city-by-activity shares from KOSIS sigungu GRVA tables and
rescales every year to the same-year official province-by-activity annual total
from the KOSTAT quarterly GRDP/GVA xlsx.  Target-year actuals are used only for
validation.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
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
    MAIN_ACTIVITIES,
    OTHER_NPT_ACTIVITY,
    SERVICE_COMPONENTS,
    activity_group,
    load_quarterly,
    md_table,
    national_quarter_factor,
    official_region_activity,
    province_activity_predictions,
    validate_quarters,
)
from run_sigungu_2020_backcast_monthly_bridge_pilot import (  # noqa: E402
    build_monthly_weights_for_year,
    equal_month_rows,
)
from run_nationwide_monthly_bridge_validation import short_region  # noqa: E402


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
RAW = ROOT / "data" / "raw" / "nationwide_2016_2020_fullcoverage_share_bridge"
REPORT = HERE / "sigungu_2016_2020_fullcoverage_share_bridge_backcast.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

BASIS_YEARS = tuple(str(y) for y in range(2015, 2020))
TARGET_YEARS = list(range(2016, 2021))
ACTIVITIES = ["광업, 제조업", "건설업", *SERVICE_COMPONENTS]
REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기도", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

SHARE_TABLES = {
    "서울": ("201", "DT_201012_D040031", "서울특별시", "2020기준 또는 장기 현행 KOSIS 구성비"),
    "부산": ("202", "DT_F10108", "부산광역시", "2020기준 또는 장기 현행 KOSIS 구성비"),
    "대구": ("203", "DT_2015Y22GRDP2", "대구광역시", "2015기준 구계열 내부구성비"),
    "인천": ("204", "DT_2020Y23GRDP2", "인천광역시", "2020기준 또는 장기 현행 KOSIS 구성비"),
    "광주": ("205", "DT_2020Y24GRDP2", "광주광역시", "2020기준 또는 장기 현행 KOSIS 구성비"),
    "대전": ("206", "DT_2015Y25GRDP2", "대전광역시", "2015기준 구계열 내부구성비"),
    "울산": ("207", "DT_GRDP_2015_02", "울산광역시", "2015기준 구계열 내부구성비"),
    "경기도": ("210", "DT_GRDP008_2020", "경기도", "2020기준 또는 장기 현행 KOSIS 구성비"),
    "강원": ("211", "DT_2020Y32GRDP2", "강원특별자치도", "2020기준 또는 장기 현행 KOSIS 구성비"),
    "충북": ("212", "DT_2020Y33GRDP2", "충청북도", "2020기준 또는 장기 현행 KOSIS 구성비"),
    "충남": ("213", "DT_2015Y34GRDP2", "충청남도", "2015기준 구계열 내부구성비"),
    "전북": ("214", "DT_2020Y35GRDP2", "전북특별자치도", "2020기준 또는 장기 현행 KOSIS 구성비"),
    "전남": ("215", "DT_2020Y36GRDP2", "전라남도", "2020기준 또는 장기 현행 KOSIS 구성비"),
    "경북": ("216", "DT_I30003", "경상북도", "2015기준 구계열 내부구성비"),
    "경남": ("217", "DT_2015Y38GRDP2", "경상남도", "2015기준 구계열 내부구성비"),
    "제주": ("218", "DT_2015Y39GRDP2", "제주특별자치도", "2015기준 구계열 내부구성비"),
}


def find_dimension(rows: list[dict[str, Any]], hints: tuple[str, ...], fallback: int) -> int:
    best = (0, fallback)
    for idx in range(1, 9):
        text = " ".join(
            str(row.get(f"C{idx}_OBJ_NM") or "") + " " + str(row.get(f"C{idx}_NM") or "")
            for row in rows[:300]
        )
        score = sum(1 for h in hints if h in text)
        if score > best[0]:
            best = (score, idx)
    return best[1]


def collect_table(api_key: str, region: str, org_id: str, tbl_id: str, province_full: str, source_label: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    info = fetch_metadata(org_id, tbl_id)
    period = years_available(info, BASIS_YEARS)
    if period is None:
        raise RuntimeError(f"{org_id}/{tbl_id} has no overlap with {BASIS_YEARS[0]}-{BASIS_YEARS[-1]}")
    item_id = real_gva_item_id(info)
    if not item_id:
        raise RuntimeError(f"{org_id}/{tbl_id} real GVA item not identified")
    obj = object_selection(info)
    rows = get_data(api_key, org_id=org_id, tbl_id=tbl_id, item_id=item_id, period="Y", start=period[0], end=period[1], obj=obj)
    rows, filtered_item_code = filter_real_gva_rows(rows)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"kosis_{org_id}_{tbl_id}_{period[0]}_{period[1]}_real_gva_rows.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    city_dim = find_dimension(rows, ("시군구", "시군별", "구군", "행정구역"), 1)
    activity_dim = find_dimension(rows, ("경제활동", "산업", "업종"), 2 if city_dim != 2 else 1)
    d = pd.DataFrame(rows)
    d["year"] = pd.to_numeric(d["PRD_DE"], errors="coerce").astype("Int64")
    d["city"] = d[f"C{city_dim}_NM"].astype(str)
    d["activity_group"] = d[f"C{activity_dim}_NM"].map(activity_group)
    d["share_value"] = pd.to_numeric(d["DT"], errors="coerce")
    aggregate_city = str(d["city"].dropna().iloc[0])
    out = d[
        d["year"].between(int(period[0]), int(period[1]))
        & d["activity_group"].isin(ACTIVITIES)
        & d["share_value"].notna()
        & d["city"].ne(aggregate_city)
    ].copy()
    out["quarter_region"] = region
    out["province_full"] = province_full
    out["share_source"] = source_label
    spec = {
        "quarter_region": region,
        "province_full": province_full,
        "org_id": org_id,
        "tbl_id": tbl_id,
        "start_year": period[0],
        "end_year": period[1],
        "item_id": item_id,
        "filtered_item_code": filtered_item_code,
        "city_dimension": city_dim,
        "activity_dimension": activity_dim,
        "aggregate_city_removed": aggregate_city,
        "rows": int(len(out)),
        "city_count": int(out["city"].nunique()),
        "activity_count": int(out["activity_group"].nunique()),
        "share_source": source_label,
    }
    return out[["quarter_region", "province_full", "year", "city", "activity_group", "share_value", "share_source"]], spec


def collect_shares() -> tuple[pd.DataFrame, pd.DataFrame]:
    api_key = get_kosis_key()
    frames: list[pd.DataFrame] = []
    specs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for region, (org_id, tbl_id, province_full, source_label) in SHARE_TABLES.items():
        try:
            d, spec = collect_table(api_key, region, org_id, tbl_id, province_full, source_label)
            frames.append(d)
            specs.append(spec)
        except Exception as exc:
            failures.append({"quarter_region": region, "org_id": org_id, "tbl_id": tbl_id, "error": str(exc)})
    if not frames:
        raise RuntimeError("no share tables collected")
    raw = pd.concat(frames, ignore_index=True)
    raw = (
        raw.groupby(["quarter_region", "province_full", "year", "city", "activity_group", "share_source"], as_index=False)
        .agg(share_value=("share_value", "sum"))
    )
    denom = raw.groupby(["quarter_region", "year", "activity_group"], as_index=False)["share_value"].sum().rename(columns={"share_value": "denom"})
    shares = raw.merge(denom, on=["quarter_region", "year", "activity_group"], how="left")
    shares["city_activity_share"] = shares["share_value"] / shares["denom"]
    spec_df = pd.DataFrame(specs)
    if failures:
        spec_df = pd.concat([spec_df, pd.DataFrame(failures)], ignore_index=True, sort=False)
    return shares[["quarter_region", "province_full", "year", "city", "activity_group", "city_activity_share", "share_source"]], spec_df


def build_scaled_basis(shares: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    official = (
        x[x["year"].between(2015, 2019) & x["region"].isin(REGIONS) & x["activity"].isin(ACTIVITIES)]
        .groupby(["region", "year", "activity"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"region": "quarter_region", "activity": "activity_group", "official_value_eok": "official_sido_activity_eok"})
    )
    basis = shares.merge(official, on=["quarter_region", "year", "activity_group"], how="left")
    missing = basis[basis["official_sido_activity_eok"].isna()]
    if not missing.empty:
        raise RuntimeError(f"missing official totals: {missing[['quarter_region','year','activity_group']].drop_duplicates().to_dict('records')[:10]}")
    basis["annual_gva_eok"] = basis["city_activity_share"] * basis["official_sido_activity_eok"]
    basis["table_id"] = "share_scaled_long_window_basis"
    basis["table_name"] = "city-by-activity shares scaled to same-year official province-by-activity total"
    basis["latest_change_date"] = "share_bridge_scaled_to_same_year_official_sido_activity"
    basis["basis_source"] = basis["share_source"] + "→동년 시도×업종 공식총량"

    sejong = official[official["quarter_region"].eq("세종")].copy()
    sejong["province_full"] = "세종특별자치시"
    sejong["city"] = "세종시"
    sejong["city_activity_share"] = 1.0
    sejong["share_source"] = "세종 단층"
    sejong["annual_gva_eok"] = sejong["official_sido_activity_eok"]
    sejong["table_id"] = "pseudo_sejong_one_tier"
    sejong["table_name"] = "Sejong one-tier basis from official province-by-activity total"
    sejong["latest_change_date"] = "share_bridge_scaled_to_same_year_official_sido_activity"
    sejong["basis_source"] = "세종 단층→동년 시도×업종 공식총량"
    basis = pd.concat([basis, sejong], ignore_index=True, sort=False)

    audit = (
        basis.groupby(["quarter_region", "year", "activity_group", "share_source"], as_index=False)
        .agg(city_count=("city", "nunique"), basis_sum_eok=("annual_gva_eok", "sum"), official_sido_activity_eok=("official_sido_activity_eok", "first"), share_sum=("city_activity_share", "sum"))
    )
    audit["basis_scale_error_eok"] = audit["basis_sum_eok"] - audit["official_sido_activity_eok"]
    audit["abs_basis_scale_error_eok"] = audit["basis_scale_error_eok"].abs()
    return basis, audit


def build_quarterly(basis: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    factors = national_quarter_factor(x)
    official = official_region_activity(x)
    city_frames: list[pd.DataFrame] = []
    other_frames: list[pd.DataFrame] = []
    for year in TARGET_YEARS:
        prev_year = year - 1
        b = basis[basis["year"].eq(prev_year)].copy()
        q = factors[factors["year"].eq(year) & factors["activity"].isin(ACTIVITIES)].copy()
        pred = b.merge(q, left_on="activity_group", right_on="activity", how="inner")
        pred["year"] = year
        pred["predicted_gva_eok"] = pred["annual_gva_eok"] * pred["quarter_factor_from_prev_annual"]
        out = pred[["quarter_region", "province_full", "year", "quarter", "period", "city", "activity_group", "predicted_gva_eok", "basis_source", "quarter_factor_from_prev_annual"]].copy()
        city_frames.append(out)

        other_y = (
            official[
                official["activity"].eq(OTHER_NPT_ACTIVITY)
                & official["region"].isin(REGIONS)
                & official["year"].eq(prev_year)
            ]
            .groupby(["region", "year"], as_index=False)["official_value_eok"]
            .sum()
            .rename(columns={"region": "quarter_region", "official_value_eok": "official_other_npt_annual_eok"})
        )
        other_factor = factors[factors["year"].eq(year) & factors["activity"].eq(OTHER_NPT_ACTIVITY)].copy()
        rows = []
        for region in REGIONS:
            vals = other_y[other_y["quarter_region"].eq(region)]["official_other_npt_annual_eok"]
            if vals.empty:
                continue
            tmp = other_factor.copy()
            tmp["quarter_region"] = region
            tmp["year"] = year
            tmp["predicted_other_npt_eok"] = float(vals.iloc[0]) * tmp["quarter_factor_from_prev_annual"]
            tmp["other_npt_source"] = f"official_prior_year_{prev_year}"
            rows.append(tmp)
        other_frames.append(pd.concat(rows, ignore_index=True)[["quarter_region", "year", "quarter", "period", "predicted_other_npt_eok", "other_npt_source", "quarter_factor_from_prev_annual"]])
    city_q = pd.concat(city_frames, ignore_index=True)
    other_q = pd.concat(other_frames, ignore_index=True)
    city_q["track"] = "fullcoverage_2016_2020_share_bridge_backcast"
    other_q["track"] = "fullcoverage_2016_2020_share_bridge_backcast"
    return city_q, other_q


def build_monthly_multi(city_q: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q = city_q.copy()
    q["region_short"] = q["quarter_region"].map(short_region)
    monthly_frames: list[pd.DataFrame] = []
    for year in TARGET_YEARS:
        qy = q[q["year"].eq(year)].copy()
        weights = build_monthly_weights_for_year(qy, year)
        key = ["region_short", "activity_group", "year", "quarter"]
        if weights.empty:
            monthly_frames.append(equal_month_rows(qy))
            continue
        with_w = qy.merge(weights, on=key, how="left", suffixes=("", "_indicator"))
        matched = with_w[with_w["month_share"].notna()].copy()
        matched["monthly_indicator_coverage"] = "monthly_indicator"
        unmatched_keys = (
            with_w[with_w["month_share"].isna()][["track", "quarter_region", "province_full", "year", "quarter", "period", "city", "activity_group"]]
            .drop_duplicates()
        )
        unmatched = qy.merge(
            unmatched_keys,
            on=["track", "quarter_region", "province_full", "year", "quarter", "period", "city", "activity_group"],
            how="inner",
        )
        if not unmatched.empty:
            unmatched = equal_month_rows(unmatched)
            unmatched["period"] = unmatched["year"].astype(str) + unmatched["month"].astype(int).astype(str).str.zfill(2)
        monthly_frames.append(pd.concat([matched, unmatched], ignore_index=True, sort=False))
    monthly = pd.concat(monthly_frames, ignore_index=True, sort=False)
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
    coverage = (
        monthly.groupby(["year", "activity_group", "monthly_indicator_coverage", "monthly_indicator_source"], as_index=False)
        .agg(rows=("estimated_monthly_gva_eok", "size"), estimated_sum_eok=("estimated_monthly_gva_eok", "sum"), city_count=("city", "nunique"), quarter_count=("quarter", "nunique"))
        .sort_values(["year", "activity_group", "monthly_indicator_coverage"])
    )
    summary = pd.DataFrame(
        [
            {
                "target_year_min": min(TARGET_YEARS),
                "target_year_max": max(TARGET_YEARS),
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
    city_q, other_q = build_quarterly(basis, x)
    pred_act = province_activity_predictions(city_q, other_q)
    act_val, total_val, _summary = validate_quarters(pred_act, x)
    monthly, monthly_q_audit, monthly_share_audit, monthly_coverage, monthly_summary = build_monthly_multi(city_q)

    total_summary = (
        total_val.groupby(["track", "year"], as_index=False)
        .agg(
            province_count=("quarter_region", "nunique"),
            quarter_rows=("period", "count"),
            predicted_sum_eok=("predicted_grdp_eok", "sum"),
            actual_sum_eok=("official_grdp_eok", "sum"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            wape_pct=("abs_error_eok", lambda s: s.sum() / total_val.loc[s.index, "official_grdp_eok"].abs().sum() * 100),
            max_ape_pct=("ape_pct", "max"),
        )
        .sort_values("year")
    )
    total_all = (
        total_val.groupby(["track"], as_index=False)
        .agg(
            years=("year", "nunique"),
            province_quarter_rows=("period", "count"),
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
                "basis_year_min": int(basis["year"].min()),
                "basis_year_max": int(basis["year"].max()),
                "target_year_min": min(TARGET_YEARS),
                "target_year_max": max(TARGET_YEARS),
                "province_count": basis["quarter_region"].nunique(),
                "city_count": basis[["quarter_region", "city"]].drop_duplicates().shape[0],
                "activity_count": basis["activity_group"].nunique(),
                "basis_rows": len(basis),
                "max_abs_basis_scale_error_eok": float(basis_audit["abs_basis_scale_error_eok"].max()),
                "bad_basis_scale_cells_gt_1won_equiv": int(basis_audit["abs_basis_scale_error_eok"].gt(1e-8).sum()),
            }
        ]
    )

    specs.to_csv(OUT / "sigungu_2015_2019_share_table_specs.csv", index=False, encoding="utf-8-sig")
    basis.to_csv(OUT / "sigungu_2015_2019_share_scaled_basis.csv", index=False, encoding="utf-8-sig")
    basis_audit.to_csv(OUT / "sigungu_2015_2019_share_scaled_basis_audit.csv", index=False, encoding="utf-8-sig")
    city_q.to_csv(OUT / "sigungu_industry_quarterly_predictions_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    other_q.to_csv(OUT / "sido_other_npt_quarterly_predictions_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    total_val.to_csv(OUT / "sido_quarterly_grdp_validation_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    act_val.to_csv(OUT / "sido_activity_quarterly_validation_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    total_summary.to_csv(OUT / "sido_quarterly_grdp_summary_by_year_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    total_all.to_csv(OUT / "sido_quarterly_grdp_summary_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    act_summary.to_csv(OUT / "sido_activity_quarterly_summary_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    top_total_errors.to_csv(OUT / "sido_quarterly_grdp_top_errors_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    basis_summary.to_csv(OUT / "sigungu_2016_2020_backcast_basis_summary.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(OUT / "sigungu_industry_monthly_predictions_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    monthly_q_audit.to_csv(OUT / "monthly_bridge_quarter_reaggregation_audit_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    monthly_share_audit.to_csv(OUT / "monthly_bridge_share_integrity_audit_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    monthly_coverage.to_csv(OUT / "monthly_bridge_indicator_coverage_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")
    monthly_summary.to_csv(OUT / "monthly_bridge_summary_2016_2020_backcast.csv", index=False, encoding="utf-8-sig")

    source_summary = (
        basis.groupby(["share_source"], as_index=False)
        .agg(province_count=("quarter_region", "nunique"), city_units=("city", "nunique"), rows=("city", "size"), annual_sum_eok=("annual_gva_eok", "sum"))
    )
    report = f"""# 2016~2020 전국 시군구×업종 share-bridge 분기 backcast

생성시각: {CREATED_AT}

## 1. 목적

2020 full-coverage backcast에서 검증한 `시군구 구성비 → 시도×업종 공식총량 재스케일` 방식을 2016~2020 장기 구간에 적용했다. 2015년은 전년도 기준값이 없어 초기화 연도이며, 성능 검증은 2016~2020년이다.

## 2. 설계

| 항목 | 내용 |
| --- | --- |
| 기준값 | 2015~2019 시군구×업종 구성비 × 동년 시도×업종 공식총량 |
| 예측 대상 | 2016~2020 시군구×업종×분기 GVA 및 시도 GRDP 집계 |
| 구계열 처리 | 2015 기준 구계열 금액 직접 사용 금지, 내부 구성비만 사용 |
| 속보성 | 2016~2020 전국 업종별 분기 경로를 사용한 사후 backcast. Q+1개월 속보 아님 |
| 2015년 | 초기화 연도. 전년도 기준값 부재로 검증 대상 제외 |

## 3. 기준값 규모

{md_table(basis_summary.rename(columns={
    'basis_year_min':'기준연도_min','basis_year_max':'기준연도_max','target_year_min':'예측연도_min','target_year_max':'예측연도_max',
    'province_count':'시도수','city_count':'시군구수','activity_count':'업종수','basis_rows':'기준값행',
    'max_abs_basis_scale_error_eok':'최대재스케일오차_억원','bad_basis_scale_cells_gt_1won_equiv':'재스케일오류셀'
}), 9)}

## 4. 기준값 출처별 규모

{md_table(source_summary.rename(columns={'share_source':'구성비_출처','province_count':'시도수','city_units':'시군구수','rows':'행수','annual_sum_eok':'기준값합_억원'}), 3)}

## 5. 시도 GRDP 집계검증

{md_table(total_all.rename(columns={
    'track':'트랙','years':'연도수','province_quarter_rows':'시도분기행','predicted_sum_eok':'예측합_억원','actual_sum_eok':'실제합_억원',
    'abs_error_sum_eok':'절대오차합_억원','wape_pct':'WAPE_pct','max_ape_pct':'최대오차율_pct'
}), 3)}

## 6. 연도별 시도 GRDP 집계검증

{md_table(total_summary.rename(columns={
    'track':'트랙','year':'연도','province_count':'시도수','quarter_rows':'분기검증행','predicted_sum_eok':'예측합_억원','actual_sum_eok':'실제합_억원',
    'abs_error_sum_eok':'절대오차합_억원','wape_pct':'WAPE_pct','max_ape_pct':'최대오차율_pct'
}), 3)}

## 7. 업종별 집계검증

{md_table(act_summary.rename(columns={
    'activity':'업종','province_quarter_rows':'시도분기행','predicted_sum_eok':'예측합_억원','actual_sum_eok':'실제합_억원',
    'abs_error_sum_eok':'절대오차합_억원','wape_pct':'WAPE_pct','max_ape_pct':'최대오차율_pct'
}), 3)}

## 8. 최대오차 상위 시도·분기

{md_table(top_total_errors.rename(columns={
    'quarter_region':'시도','year':'연도','quarter':'분기','period':'시점','predicted_grdp_eok':'예측_GRDP_억원',
    'official_grdp_eok':'실제_GRDP_억원','error_eok':'오차_억원','ape_pct':'오차율_pct'
}), 3)}

## 9. 월별 bridge 보존성

월별 값은 분기 추정값을 월 단위로 나누는 운영 bridge다. 월별 official actual이 없으므로, 월별 정확도 검증이 아니라 월합이 원 분기 추정값을 보존하는지 검증한다.

{md_table(monthly_summary.rename(columns={
    'target_year_min':'예측연도_min','target_year_max':'예측연도_max','monthly_rows':'월별행','province_count':'시도수',
    'city_count':'시군구수','activity_count':'업종수','indicator_rows_pct':'월별지표적용행_pct',
    'fallback_equal_split_rows_pct':'균등분할행_pct','max_abs_quarter_reaggregation_error_eok':'최대분기재집계오차_억원',
    'bad_quarter_cells_gt_1won_equiv':'분기재집계오류셀','bad_month_count_cells':'월수오류셀',
    'bad_month_share_sum_cells':'월비중오류셀','negative_month_value_cells':'음수월값셀'
}), 6)}

## 10. 매핑 및 경계 감사

| 항목 | 처리 |
| --- | --- |
| 광업·제조업 | 구계열과 현행계열에서 분리 제공되는 `광업`, `제조업`을 검증 단위 `광업, 제조업`으로 합산 |
| 교육 서비스업 | 경북 구계열의 `교육서비스업(정부)`를 `교육 서비스업`으로 매핑 |
| 서비스업 | 세부 서비스업을 합산한 상위 검증값으로 별도 확인 |
| 기타산업 및 순생산물세 | 시군구 basis가 아니라 시도 단층 prior-year 공식값과 전국 분기비중으로 별도 bridge |
| 세종 | 하위 시군구가 없는 단층 지역으로 `세종시` 1개 단위 처리. 공간배분 성능 사례로 해석 금지 |
| 행정구역 경계 | 2016~2020 장기 패널은 KOSIS 해당 연도 시군구 명칭을 사용한다. 장기 공간비교에는 군위군 이전, 특별자치도 전환, 통합·분구 등 별도 경계 연결표 필요 |

## 11. 해석

- 2016~2020은 전국 17개 시도 경계를 보존한 시군구×업종 분기 사후 backcast로 산출 가능하다.
- 기준값 재스케일 오류 0셀은 시군구 기준값 합계가 동년 시도×업종 공식총량과 일치한다는 산술 보존성 검증이다.
- 구계열 구성비의 시군구 내부 actual 정확도는 직접 증명하지 못하므로, 공간배분 정확도 claim은 상위 시도 집계검증으로 제한한다.
- 이 장기 backcast는 사후 분기 경로를 사용하므로 실시간 속보 성능으로 표기하지 않는다.
- 월별 값은 분기값 보존형 운영 bridge이며, 월별 actual 정확도 검증으로 해석하지 않는다.
- 5개년 전체 WAPE는 낮지만, 일부 시도·분기에는 10% 초과 오차가 남는다. 따라서 “모든 시도·분기 10% 이내”로 표현하지 않는다.

## 12. 산출물

- `nationwide/outputs/sigungu_2015_2019_share_scaled_basis.csv`
- `nationwide/outputs/sigungu_industry_quarterly_predictions_2016_2020_backcast.csv`
- `nationwide/outputs/sigungu_industry_monthly_predictions_2016_2020_backcast.csv`
- `nationwide/outputs/sido_quarterly_grdp_validation_2016_2020_backcast.csv`
- `nationwide/outputs/sido_activity_quarterly_validation_2016_2020_backcast.csv`
- `nationwide/outputs/sido_quarterly_grdp_top_errors_2016_2020_backcast.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(total_all.to_string(index=False))
    print(basis_summary.to_string(index=False))
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
