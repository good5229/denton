#!/usr/bin/env python3
"""Nationwide sigungu-to-sido quarterly GRDP validation.

This script generalizes the Gyeonggi/Gyeongbuk validation:

1. Read annual sigungu-by-industry real GVA for all available provinces.
   Sejong is a one-tier metropolitan city, so it is preserved as one pseudo
   lower unit ("세종시") following the 17-metropolitan-region frame used in
   the BOK RECI reference.
2. Estimate quarterly sigungu-by-industry GVA using prior-year annual GVA and
   national same-activity quarterly movement.
3. Add a separate "other industries + net product taxes" bridge at the province
   level using lagged province official values and national quarterly shares.
4. Validate:
   * each province's cumulative and annualized GRDP errors by operating point;
   * the sum of all 17 provinces against the official national GDP/GRDP
     boundary.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
RAW_SIGUNGU = ROOT / "data" / "raw" / "expanded_sigungu_grva_real.json"
XLSX_LONG = ROOT / "data" / "processed" / "phase211_gyeonggi_2024_2025_grdp_extension" / "phase211_sido_quarterly_xlsx_long.csv"
OUT = HERE / "outputs"
REPORT = HERE / "nationwide_quarterly_grdp_validation_report.md"
SOURCE_DOC = HERE / "data_sources_and_release_cycles.md"
REVIEW_DOC = HERE / "bank_policy_reviewer_feedback.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

TOTAL_ACTIVITY = "지역내총생산(시장가격)"
OTHER_NPT_ACTIVITY = "기타산업 및 순생산물세"
SERVICE_COMPONENTS = [
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
]
VALIDATION_ACTIVITIES = ["광업, 제조업", "건설업", "서비스업", *SERVICE_COMPONENTS, OTHER_NPT_ACTIVITY]
MAIN_ACTIVITIES = ["광업, 제조업", "건설업", "서비스업", OTHER_NPT_ACTIVITY]
LABELS = {1: "1분기+1개월", 2: "1~2분기+1개월", 3: "1~3분기+1개월", 4: "공표 후 정밀화"}

TABLE_PROVINCE_MAP = {
    "201_DT_201012_D040031": ("서울", "서울특별시"),
    "202_DT_F10108": ("부산", "부산광역시"),
    "203_DT_2020Y22GRDP2": ("대구", "대구광역시"),
    "204_DT_2020Y23GRDP2": ("인천", "인천광역시"),
    "205_DT_2020Y24GRDP2": ("광주", "광주광역시"),
    "206_DT_2020Y25GRDP2": ("대전", "대전광역시"),
    "207_DT_GRDP_2020_02": ("울산", "울산광역시"),
    # Sejong has no lower-level sigungu GRVA table in the local annual source.
    # It is added separately as one pseudo lower unit from lagged official
    # regional quarterly/annual values, rather than being excluded.
    "210_DT_GRDP008_2020": ("경기도", "경기도"),
    "211_DT_2020Y32GRDP2": ("강원", "강원특별자치도"),
    "212_DT_2020Y33GRDP2": ("충북", "충청북도"),
    "213_DT_2020Y34GRDP2": ("충남", "충청남도"),
    "214_DT_2020Y35GRDP2": ("전북", "전북특별자치도"),
    "215_DT_2020Y36GRDP2": ("전남", "전라남도"),
    "216_DT_GRDP202037_02": ("경북", "경상북도"),
    "217_DT_2020Y38GRDP2": ("경남", "경상남도"),
    "218_DT_2020GRDP39_02": ("제주", "제주특별자치도"),
}
COVERED_REGIONS = [v[0] for v in TABLE_PROVINCE_MAP.values()] + ["세종"]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def norm_text(s: str) -> str:
    return re.sub(r"\s+", "", str(s)).replace("·", "").replace(",", "")


def activity_group(label: str) -> str | None:
    t = norm_text(label)
    if "총부가가치" in t or t == "합계":
        return None
    if t in {"광업", "제조업"}:
        return "광업, 제조업"
    if t == "건설업":
        return "건설업"
    if t == "도매및소매업":
        return "도매 및 소매업"
    if t == "운수및창고업":
        return "운수 및 창고업"
    if t == "숙박및음식점업":
        return "숙박 및 음식점업"
    if t == "정보통신업":
        return "정보통신업"
    if t in {"금융및보험업", "금융보험업"}:
        return "금융 및 보험업"
    if t == "부동산업":
        return "부동산업"
    if t == "사업서비스업":
        return "사업서비스업"
    if t in {"공공행정국방및사회보장행정", "공공행정국방사회보장행정"}:
        return "공공 행정, 국방·사회보장"
    if t in {"교육서비스업"}:
        return "교육 서비스업"
    if t in {"보건업및사회복지서비스업", "보건업및사회복지서비스업"}:
        return "보건 및 사회복지업"
    if t in {"문화및기타서비스업", "문화및기타서비스업"}:
        return "문화 및 기타서비스업"
    return None


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if str(c).lower() in {"year", "연도", "quarter", "available_quarters", "사용분기수", "연도수", "시군구수"}:
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else str(int(x)) if isinstance(x, (int, float)) and float(x).is_integer() else str(x))
        elif pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def load_annual_sigungu() -> tuple[pd.DataFrame, pd.DataFrame]:
    obj = json.loads(RAW_SIGUNGU.read_text())
    all_rows = []
    inventory = []
    for table_id, (quarter_region, province_full) in TABLE_PROVINCE_MAP.items():
        d = pd.DataFrame(obj[table_id]).copy()
        aggregate_name = str(d["C1_NM"].dropna().iloc[0])
        d["activity_group"] = d["C2_NM"].map(activity_group)
        use = d[d["activity_group"].notna()].copy()
        use["value_eok"] = pd.to_numeric(use["DT"], errors="coerce") / 100.0
        use["year"] = use["PRD_DE"].astype(int)
        use["quarter_region"] = quarter_region
        use["province_full"] = province_full
        use["table_id"] = table_id
        use["table_name"] = use["TBL_NM"]
        use["city"] = use["C1_NM"].astype(str)
        use = use[use["city"].ne(aggregate_name)].copy()
        annual = (
            use.groupby(["quarter_region", "province_full", "table_id", "table_name", "year", "city", "activity_group"], as_index=False)
            .agg(annual_gva_eok=("value_eok", "sum"), latest_change_date=("LST_CHN_DE", "max"))
        )
        all_rows.append(annual)
        inventory.append(
            {
                "quarter_region": quarter_region,
                "province_full": province_full,
                "table_id": table_id,
                "table_name": str(d["TBL_NM"].iloc[0]),
                "aggregate_name_removed": aggregate_name,
                "sigungu_count_2023": int(annual[annual["year"].eq(2023)]["city"].nunique()),
                "year_min": int(annual["year"].min()),
                "year_max": int(annual["year"].max()),
                "latest_change_date_max": str(annual["latest_change_date"].max()),
            }
        )
    return pd.concat(all_rows, ignore_index=True), pd.DataFrame(inventory)


def load_quarterly() -> pd.DataFrame:
    x = pd.read_csv(XLSX_LONG)
    return x


def add_sejong_one_tier_annual(annual: pd.DataFrame, inventory: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add Sejong as a one-tier city, not as a passthrough.

    The BOK RECI reference uses 17 metropolitan regions. The local annual
    sigungu GRVA bundle has 16 province tables because Sejong has no lower
    sigungu split. For nationwide lower-to-upper validation, the least
    distortive hierarchy is therefore:

        세종특별자치시 → 세종시

    The annual benchmark for this pseudo lower unit is built from official
    Sejong quarterly values summed by year for years that are only used as
    lagged bases. The target year's quarterly actual is still used only for
    validation.
    """
    sejong_annual = (
        x[
            x["region"].eq("세종")
            & x["activity"].isin(["광업, 제조업", "건설업", *SERVICE_COMPONENTS])
            & x["year"].between(2020, 2023)
        ]
        .groupby(["year", "activity"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"activity": "activity_group", "official_value_eok": "annual_gva_eok"})
    )
    sejong_annual["quarter_region"] = "세종"
    sejong_annual["province_full"] = "세종특별자치시"
    sejong_annual["table_id"] = "pseudo_sejong_one_tier_from_quarterly_grdp"
    sejong_annual["table_name"] = "세종 단층 시군구 annual GVA benchmark from official quarterly GRDP/GVA"
    sejong_annual["city"] = "세종시"
    sejong_annual["latest_change_date"] = "quarterly_grdp_xlsx_derived"
    sejong_annual = sejong_annual[
        ["quarter_region", "province_full", "table_id", "table_name", "year", "city", "activity_group", "annual_gva_eok", "latest_change_date"]
    ].copy()
    inventory = pd.concat(
        [
            inventory,
            pd.DataFrame(
                [
                    {
                        "quarter_region": "세종",
                        "province_full": "세종특별자치시",
                        "table_id": "pseudo_sejong_one_tier_from_quarterly_grdp",
                        "table_name": "세종 단층 시군구 annual GVA benchmark from official quarterly GRDP/GVA",
                        "aggregate_name_removed": "해당 없음: 단층 지자체",
                        "sigungu_count_2023": 1,
                        "year_min": int(sejong_annual["year"].min()),
                        "year_max": int(sejong_annual["year"].max()),
                        "latest_change_date_max": "quarterly_grdp_xlsx_derived",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    return pd.concat([annual, sejong_annual], ignore_index=True), inventory


def national_quarter_factor(x: pd.DataFrame) -> pd.DataFrame:
    nat = x[x["region"].eq("전국") & x["activity"].isin(VALIDATION_ACTIVITIES)].copy()
    annual = nat.groupby(["activity", "year"], as_index=False)["official_value_eok"].sum().rename(columns={"official_value_eok": "national_annual_eok"})
    annual["target_year"] = annual["year"] + 1
    f = nat.merge(annual[["activity", "target_year", "national_annual_eok"]], left_on=["activity", "year"], right_on=["activity", "target_year"], how="left")
    f["quarter_factor_from_prev_annual"] = f["official_value_eok"] / f["national_annual_eok"]
    return f[["activity", "year", "quarter", "period", "quarter_factor_from_prev_annual"]].dropna()


def official_region_activity(x: pd.DataFrame) -> pd.DataFrame:
    return x[x["activity"].isin([TOTAL_ACTIVITY, *VALIDATION_ACTIVITIES])].copy()


def build_predictions(track: str, annual: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    factors = national_quarter_factor(x)
    official = official_region_activity(x)
    predicted_other_annual: dict[tuple[str, int], float] = {}
    all_city_quarters = []
    all_other = []
    for year in range(2021, 2026):
        prev_year = year - 1
        if track == "recursive_no_target_actual" and year > 2023:
            prior_pred = pd.concat(all_city_quarters, ignore_index=True)
            basis = (
                prior_pred[prior_pred["year"].eq(prev_year)]
                .groupby(["quarter_region", "province_full", "city", "activity_group"], as_index=False)["predicted_gva_eok"]
                .sum()
                .rename(columns={"predicted_gva_eok": "annual_gva_eok"})
            )
            basis["basis_source"] = f"recursive_predicted_sigungu_{prev_year}"
        else:
            basis = annual[annual["year"].eq(prev_year)].copy()
            basis["basis_source"] = f"official_sigungu_annual_{prev_year}"
            missing_regions = sorted(set(COVERED_REGIONS) - set(basis["quarter_region"].unique()))
            if missing_regions and all_city_quarters:
                prior_pred = pd.concat(all_city_quarters, ignore_index=True)
                fill = (
                    prior_pred[prior_pred["year"].eq(prev_year) & prior_pred["quarter_region"].isin(missing_regions)]
                    .groupby(["quarter_region", "province_full", "city", "activity_group"], as_index=False)["predicted_gva_eok"]
                    .sum()
                    .rename(columns={"predicted_gva_eok": "annual_gva_eok"})
                )
                fill["table_id"] = "filled_missing_sigungu_annual_from_prior_prediction"
                fill["table_name"] = "missing local annual sigungu benchmark filled from prior quarterly prediction"
                fill["year"] = prev_year
                fill["latest_change_date"] = "model_filled"
                fill["basis_source"] = f"missing_official_sigungu_{prev_year}_filled_from_prediction"
                basis = pd.concat([basis, fill[basis.columns]], ignore_index=True)
            if track == "prior_year_province_anchor" and year > 2023:
                official_y = (
                    official[
                        official["year"].eq(prev_year)
                        & official["region"].isin(COVERED_REGIONS)
                        & official["activity"].isin(["광업, 제조업", "건설업", *SERVICE_COMPONENTS])
                    ]
                    .groupby(["region", "activity"], as_index=False)["official_value_eok"]
                    .sum()
                    .rename(columns={"region": "quarter_region", "activity": "activity_group", "official_value_eok": "official_group_annual_eok"})
                )
                pred_y = basis.groupby(["quarter_region", "activity_group"], as_index=False)["annual_gva_eok"].sum().rename(columns={"annual_gva_eok": "pred_group_annual_eok"})
                scale = official_y.merge(pred_y, on=["quarter_region", "activity_group"], how="left")
                scale["scale_factor"] = scale["official_group_annual_eok"] / scale["pred_group_annual_eok"]
                basis = basis.merge(scale[["quarter_region", "activity_group", "scale_factor"]], on=["quarter_region", "activity_group"], how="left")
                basis["annual_gva_eok"] = basis["annual_gva_eok"] * basis["scale_factor"].fillna(1.0)
                basis["basis_source"] = f"lagged_basis_{prev_year}_scaled_to_prior_year_official_sido_activity"
        q = factors[factors["year"].eq(year) & factors["activity"].isin(["광업, 제조업", "건설업", *SERVICE_COMPONENTS])].copy()
        pred = basis.merge(q, left_on="activity_group", right_on="activity", how="inner")
        pred["year"] = year
        pred["predicted_gva_eok"] = pred["annual_gva_eok"] * pred["quarter_factor_from_prev_annual"]
        all_city_quarters.append(
            pred[
                [
                    "quarter_region", "province_full", "year", "quarter", "period", "city",
                    "activity_group", "predicted_gva_eok", "basis_source", "quarter_factor_from_prev_annual",
                ]
            ].copy()
        )

        other_official_y = (
            official[
                official["activity"].eq(OTHER_NPT_ACTIVITY)
                & official["region"].isin(COVERED_REGIONS)
            ]
            .groupby(["region", "year"], as_index=False)["official_value_eok"]
            .sum()
            .rename(columns={"region": "quarter_region", "official_value_eok": "official_other_npt_annual_eok"})
        )
        other_factor = factors[factors["year"].eq(year) & factors["activity"].eq(OTHER_NPT_ACTIVITY)].copy()
        other_rows = []
        for region in sorted(annual["quarter_region"].unique()):
            if track == "prior_year_province_anchor" or prev_year <= 2023:
                val = float(other_official_y[(other_official_y["quarter_region"].eq(region)) & (other_official_y["year"].eq(prev_year))]["official_other_npt_annual_eok"].iloc[0])
                source = f"official_prior_year_{prev_year}"
            else:
                val = predicted_other_annual[(region, prev_year)]
                source = f"recursive_predicted_prior_year_{prev_year}"
            tmp = other_factor.copy()
            tmp["quarter_region"] = region
            tmp["year"] = year
            tmp["prior_other_npt_annual_eok"] = val
            tmp["predicted_other_npt_eok"] = tmp["prior_other_npt_annual_eok"] * tmp["quarter_factor_from_prev_annual"]
            tmp["other_npt_source"] = source
            other_rows.append(tmp)
            predicted_other_annual[(region, year)] = float(tmp["predicted_other_npt_eok"].sum())
        all_other.append(pd.concat(other_rows, ignore_index=True)[["quarter_region", "year", "quarter", "period", "predicted_other_npt_eok", "other_npt_source", "quarter_factor_from_prev_annual"]])
    city_q = pd.concat(all_city_quarters, ignore_index=True)
    other_q = pd.concat(all_other, ignore_index=True)
    city_q["track"] = track
    other_q["track"] = track
    return city_q, other_q


def province_activity_predictions(city_q: pd.DataFrame, other_q: pd.DataFrame) -> pd.DataFrame:
    act = (
        city_q.groupby(["track", "quarter_region", "year", "quarter", "period", "activity_group"], as_index=False)["predicted_gva_eok"]
        .sum()
        .rename(columns={"activity_group": "activity", "predicted_gva_eok": "predicted_value_eok"})
    )
    svc = (
        act[act["activity"].isin(SERVICE_COMPONENTS)]
        .groupby(["track", "quarter_region", "year", "quarter", "period"], as_index=False)["predicted_value_eok"]
        .sum()
    )
    svc["activity"] = "서비스업"
    other = other_q.rename(columns={"predicted_other_npt_eok": "predicted_value_eok"})
    other["activity"] = OTHER_NPT_ACTIVITY
    other = other[["track", "quarter_region", "year", "quarter", "period", "activity", "predicted_value_eok"]]
    return pd.concat([act, svc, other], ignore_index=True)


def validate_quarters(pred_act: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    off = official_region_activity(x)
    off = off[off["region"].isin(COVERED_REGIONS)]
    activity_val = pred_act.merge(
        off[off["activity"].isin(VALIDATION_ACTIVITIES)][["region", "activity", "year", "quarter", "period", "official_value_eok"]],
        left_on=["quarter_region", "activity", "year", "quarter", "period"],
        right_on=["region", "activity", "year", "quarter", "period"],
        how="left",
    )
    activity_val["error_eok"] = activity_val["predicted_value_eok"] - activity_val["official_value_eok"]
    activity_val["abs_error_eok"] = activity_val["error_eok"].abs()
    activity_val["ape_pct"] = activity_val["abs_error_eok"] / activity_val["official_value_eok"].abs() * 100

    main = pred_act[pred_act["activity"].isin(MAIN_ACTIVITIES)]
    total_pred = main.groupby(["track", "quarter_region", "year", "quarter", "period"], as_index=False)["predicted_value_eok"].sum().rename(columns={"predicted_value_eok": "predicted_grdp_eok"})
    total_off = off[off["activity"].eq(TOTAL_ACTIVITY)][["region", "year", "quarter", "period", "official_value_eok"]].rename(columns={"official_value_eok": "official_grdp_eok"})
    total_val = total_pred.merge(total_off, left_on=["quarter_region", "year", "quarter", "period"], right_on=["region", "year", "quarter", "period"], how="left")
    total_val["error_eok"] = total_val["predicted_grdp_eok"] - total_val["official_grdp_eok"]
    total_val["abs_error_eok"] = total_val["error_eok"].abs()
    total_val["ape_pct"] = total_val["abs_error_eok"] / total_val["official_grdp_eok"].abs() * 100

    summary = (
        total_val.groupby(["track", "quarter_region", "year"], as_index=False)
        .agg(
            official_sum_eok=("official_grdp_eok", "sum"),
            predicted_sum_eok=("predicted_grdp_eok", "sum"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            wape_pct=("abs_error_eok", lambda s: s.sum() / total_val.loc[s.index, "official_grdp_eok"].abs().sum() * 100),
            max_ape_pct=("ape_pct", "max"),
        )
    )
    return activity_val, total_val, summary


def national_prior_year_cum_share(x: pd.DataFrame) -> pd.DataFrame:
    nat = x[x["region"].eq("전국") & x["activity"].isin(VALIDATION_ACTIVITIES)].copy()
    nat["annual_eok"] = nat.groupby(["activity", "year"])["official_value_eok"].transform("sum")
    nat["cum_eok"] = nat.sort_values(["activity", "year", "quarter"]).groupby(["activity", "year"])["official_value_eok"].cumsum()
    nat["cum_share"] = nat["cum_eok"] / nat["annual_eok"]
    nat["year"] = nat["year"] + 1
    return nat.rename(columns={"quarter": "available_quarters", "cum_share": "prior_year_national_cum_share"})[["activity", "year", "available_quarters", "prior_year_national_cum_share"]]


def operating_validation(pred_act: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    off = official_region_activity(x)
    shares = national_prior_year_cum_share(x)
    rows = []
    act_rows = []
    for track in sorted(pred_act["track"].unique()):
        for region in COVERED_REGIONS:
            for year in range(2021, 2026):
                for k in [1, 2, 3, 4]:
                    p = pred_act[(pred_act["track"].eq(track)) & (pred_act["quarter_region"].eq(region)) & (pred_act["year"].eq(year)) & (pred_act["quarter"].le(k))]
                    o = off[(off["region"].eq(region)) & (off["activity"].isin(VALIDATION_ACTIVITIES)) & (off["year"].eq(year)) & (off["quarter"].le(k))]
                    p_cum = p.groupby("activity", as_index=False)["predicted_value_eok"].sum().rename(columns={"predicted_value_eok": "predicted_cumulative_eok"})
                    o_cum = o.groupby("activity", as_index=False)["official_value_eok"].sum().rename(columns={"official_value_eok": "official_cumulative_eok"})
                    o_ann = (
                        off[(off["region"].eq(region)) & (off["activity"].isin(VALIDATION_ACTIVITIES)) & (off["year"].eq(year))]
                        .groupby("activity", as_index=False)["official_value_eok"]
                        .sum()
                        .rename(columns={"official_value_eok": "official_annual_eok"})
                    )
                    a = p_cum.merge(o_cum, on="activity", how="left").merge(o_ann, on="activity", how="left")
                    a["track"] = track
                    a["quarter_region"] = region
                    a["year"] = year
                    a["available_quarters"] = k
                    a["operating_label"] = LABELS[k]
                    if k < 4:
                        a = a.merge(shares[shares["available_quarters"].eq(k)], on=["activity", "year"], how="left")
                        a["annualized_predicted_eok"] = a["predicted_cumulative_eok"] / a["prior_year_national_cum_share"]
                    else:
                        a["prior_year_national_cum_share"] = 1.0
                        a["annualized_predicted_eok"] = a["predicted_cumulative_eok"]
                    a["annualized_error_eok"] = a["annualized_predicted_eok"] - a["official_annual_eok"]
                    a["annualized_ape_pct"] = a["annualized_error_eok"].abs() / a["official_annual_eok"].abs() * 100
                    a["cumulative_error_eok"] = a["predicted_cumulative_eok"] - a["official_cumulative_eok"]
                    a["cumulative_ape_pct"] = a["cumulative_error_eok"].abs() / a["official_cumulative_eok"].abs() * 100
                    act_rows.append(a)
                    main = a[a["activity"].isin(MAIN_ACTIVITIES)]
                    pred_cum = float(main["predicted_cumulative_eok"].sum())
                    pred_ann = float(main["annualized_predicted_eok"].sum())
                    off_cum = float(off[(off["region"].eq(region)) & (off["activity"].eq(TOTAL_ACTIVITY)) & (off["year"].eq(year)) & (off["quarter"].le(k))]["official_value_eok"].sum())
                    off_ann = float(off[(off["region"].eq(region)) & (off["activity"].eq(TOTAL_ACTIVITY)) & (off["year"].eq(year))]["official_value_eok"].sum())
                    rows.append(
                        {
                            "track": track, "quarter_region": region, "year": year, "available_quarters": k,
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
    total = pd.DataFrame(rows)
    act = pd.concat(act_rows, ignore_index=True)
    scenario = (
        total.groupby(["track", "quarter_region", "available_quarters", "operating_label"], as_index=False)
        .agg(
            years=("year", "count"),
            annualized_abs_error_sum_eok=("annualized_error_eok", lambda s: s.abs().sum()),
            annualized_wape_pct=("annualized_error_eok", lambda s: s.abs().sum() / total.loc[s.index, "official_annual_grdp_eok"].abs().sum() * 100),
            annualized_max_ape_pct=("annualized_ape_pct", "max"),
            cumulative_wape_pct=("cumulative_error_eok", lambda s: s.abs().sum() / total.loc[s.index, "official_cumulative_grdp_eok"].abs().sum() * 100),
            cumulative_max_ape_pct=("cumulative_ape_pct", "max"),
        )
    )
    return total, act, scenario


def national_coverage_validation(pred_act: pd.DataFrame, x: pd.DataFrame) -> pd.DataFrame:
    off = official_region_activity(x)
    main = pred_act[pred_act["activity"].isin(MAIN_ACTIVITIES)]
    pred = main.groupby(["track", "year", "quarter", "period"], as_index=False)["predicted_value_eok"].sum().rename(columns={"predicted_value_eok": "covered17_predicted_grdp_eok"})
    national = off[(off["region"].eq("전국")) & (off["activity"].eq(TOTAL_ACTIVITY))][["year", "quarter", "period", "official_value_eok"]].rename(columns={"official_value_eok": "official_national_gdp_eok"})
    val = pred.merge(national, on=["year", "quarter", "period"], how="left")
    val["national_error_eok"] = val["covered17_predicted_grdp_eok"] - val["official_national_gdp_eok"]
    val["national_ape_pct"] = val["national_error_eok"].abs() / val["official_national_gdp_eok"].abs() * 100
    return val


def write_source_doc(inventory: pd.DataFrame) -> None:
    latest_annual = inventory[~inventory["table_id"].astype(str).str.startswith("pseudo_")]["latest_change_date_max"].max()
    SOURCE_DOC.write_text(
        f"""# 전국 확장 검증 데이터 출처와 공표주기

생성시각: {CREATED_AT}

## 사용 데이터

| 데이터 | 로컬 경로 | 원 출처 | 사용 내용 | 공표주기/공표시점 |
| --- | --- | --- | --- | --- |
| 시도별 시군구 경제활동별 지역내총부가가치 및 요소소득 | `data/raw/expanded_sigungu_grva_real.json` | KOSIS 국가통계포털 지역소득 연간 시군구 GRVA 표 | 2020~2023년 시군구×경제활동별 실질 GVA, 16개 시도 | 연간. 로컬 원천의 최신 변경일 최대값: `{latest_annual}` |
| 세종 단층 하위단위 연간 벤치마크 | `data/processed/phase211.../phase211_sido_quarterly_xlsx_long.csv` | 통계청/지역통계 실험적 통계의 세종 분기 업종값 | 세종특별자치시를 `세종시` 1개 하위단위로 보존하기 위한 직전연도 업종별 연간합 | 분기 원천의 연간합. 목표연도 actual은 예측 입력에서 제외 |
| 실질 지역내총생산(잠정) 실험적 통계 XLSX | `data/raw/sido_quarterly/2026년*1분기*실질_지역내총생산(잠정).xlsx` 및 파생 `data/processed/phase211.../phase211_sido_quarterly_xlsx_long.csv` | 통계청/지역통계 실험적 통계 | 전국·시도별 분기 GRDP/업종별 분기값, 2015Q1~2026Q1 | 분기. 통상 분기 종료 후 약 3개월 내 잠정 공표 |
| 전국 분기 GDP/순생산물세 | 위 XLSX의 전국 행 및 기존 `data/raw/national_quarterly_gdp_real.json` | 통계청/한국은행 계열 국민계정·지역소득 파생 | 전국 계절비중, 전국 GDP actual 비교 경계 | 분기 |

## 공표시점 기준

| 자료군 | 기준 공표시차 | 이번 검증에서의 처리 |
| --- | --- | --- |
| 국민소득 GDP | BOK 문서 기준 분기말 후 속보 약 28일, 잠정 약 70일 | 전국 분기 움직임 및 전국 경계 비교에 사용 |
| 지역소득 GRDP | BOK 문서 기준 연간 잠정 익년 12월, 확정 익익년 8월 | 실시간 성과가 아니라 최신 빈티지 기준 사후 백테스트로 표시 |
| 통계청 실험적 분기 GRDP | 로컬 Phase22 기준 2025Q1 2025-06-26, 2025Q2 2025-09-26, 2025Q3 2025-12-26, 2025Q4 2026-03-30, 2026Q1 2026-06-29 공표 확인 | 분기 actual 검증 경계. Q+1개월 엄격 속보 성과로 직접 주장하지 않음 |
| 시군구 연간 GRVA | 시도별 KOSIS 표 최신 변경일 상이 | 2023년 원천 부재 시도는 직전 예측 또는 시도 공식총량 보정으로 별도 감사 |

## 시도별 연간 원천표 인벤토리

{md_table(inventory.rename(columns={
    'quarter_region':'분기표지역명',
    'province_full':'시도명',
    'table_id':'KOSIS테이블',
    'table_name':'자료명',
    'aggregate_name_removed':'제거한상위행',
    'sigungu_count_2023':'2023시군구수',
    'year_min':'시작연도',
    'year_max':'종료연도',
    'latest_change_date_max':'최신변경일'
}), 0)}

## 세종 처리

BOK 이슈노트의 RECI 기준은 17개 광역자치단체다. 세종은 하위 시군구가 없는 단층 광역지자체이므로, 전국 확장 검증에서는 세종을 제외하지 않고 `세종특별자치시 → 세종시` 1개 하위단위로 둔다. 이때 세종의 목표연도 분기 actual을 입력값으로 쓰지 않고 직전연도 연간 업종합만 lagged benchmark로 사용한다.

## 해석 제한

- 본 검증은 최신 공표 빈티지 기준의 사후 백테스트다. 공표시점별 원천 빈티지를 완전 재현한 실시간 운용성과로 해석하지 않는다.
- 기타산업 및 순생산물세는 시도 단위 bridge로 처리했으므로, 산출물은 시도 및 전국 경계 검증용이다. 시군구별 총 GRDP 확정치나 순위 산출에는 직접 사용하지 않는다.
- 실질 연쇄가격 계열은 하위항목 합계가 상위 총량과 완전히 일치하지 않을 수 있다. 전국 경계 WAPE는 공식 국민계정 대체값이 아니라 외부 일관성 참고지표다.
""",
        encoding="utf-8",
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    x = load_quarterly()
    annual, inventory = load_annual_sigungu()
    annual, inventory = add_sejong_one_tier_annual(annual, inventory, x)
    city_parts = []
    other_parts = []
    for track in ["recursive_no_target_actual", "prior_year_province_anchor"]:
        c, o = build_predictions(track, annual, x)
        city_parts.append(c)
        other_parts.append(o)
    city_q = pd.concat(city_parts, ignore_index=True)
    other_q = pd.concat(other_parts, ignore_index=True)
    pred_act = province_activity_predictions(city_q, other_q)
    act_val, total_val, province_year_summary = validate_quarters(pred_act, x)
    op_total, op_activity, op_scenario = operating_validation(pred_act, x)
    nat_val = national_coverage_validation(pred_act, x)
    nat_summary = (
        nat_val.groupby(["track", "year"], as_index=False)
        .agg(
            quarters=("period", "count"),
            official_national_gdp_sum_eok=("official_national_gdp_eok", "sum"),
            covered17_predicted_sum_eok=("covered17_predicted_grdp_eok", "sum"),
            national_abs_error_sum_eok=("national_error_eok", lambda s: s.abs().sum()),
            national_wape_pct=("national_error_eok", lambda s: s.abs().sum() / nat_val.loc[s.index, "official_national_gdp_eok"].abs().sum() * 100),
        )
    )
    audit = pd.DataFrame(
        [
            {"check": "covered_provinces", "value": int(inventory["quarter_region"].nunique()), "status": "17; Sejong handled as one-tier pseudo sigungu"},
            {"check": "sigungu_with_2023_local_source", "value": int(inventory["sigungu_count_2023"].sum()), "status": "2023 local source coverage, not total national municipalities"},
            {"check": "city_quarter_prediction_rows", "value": int(len(city_q)), "status": "information"},
            {"check": "province_total_validation_missing_actual", "value": int(total_val["official_grdp_eok"].isna().sum()), "status": "0"},
            {"check": "activity_validation_missing_actual", "value": int(act_val["official_value_eok"].isna().sum()), "status": "0"},
            {"check": "national_validation_missing_actual", "value": int(nat_val["official_national_gdp_eok"].isna().sum()), "status": "0"},
        ]
    )
    basis_audit = (
        city_q.groupby(["track", "year", "basis_source"], as_index=False)
        .size()
        .rename(columns={"size": "prediction_rows"})
    )
    source_gap_audit = inventory[inventory["sigungu_count_2023"].eq(0)][
        ["quarter_region", "province_full", "table_id", "year_max", "latest_change_date_max"]
    ].copy()

    annual.to_csv(OUT / "annual_sigungu_gva_normalized.csv", index=False, encoding="utf-8-sig")
    inventory.to_csv(OUT / "source_inventory.csv", index=False, encoding="utf-8-sig")
    city_q.to_csv(OUT / "sigungu_industry_quarterly_predictions.csv", index=False, encoding="utf-8-sig")
    other_q.to_csv(OUT / "sido_other_npt_quarterly_predictions.csv", index=False, encoding="utf-8-sig")
    pred_act.to_csv(OUT / "sido_activity_quarterly_predictions.csv", index=False, encoding="utf-8-sig")
    total_val.to_csv(OUT / "sido_quarterly_grdp_validation.csv", index=False, encoding="utf-8-sig")
    act_val.to_csv(OUT / "sido_activity_quarterly_validation.csv", index=False, encoding="utf-8-sig")
    province_year_summary.to_csv(OUT / "sido_yearly_grdp_summary.csv", index=False, encoding="utf-8-sig")
    op_total.to_csv(OUT / "operating_point_sido_grdp_validation.csv", index=False, encoding="utf-8-sig")
    op_activity.to_csv(OUT / "operating_point_sido_activity_validation.csv", index=False, encoding="utf-8-sig")
    op_scenario.to_csv(OUT / "operating_point_sido_scenario_summary.csv", index=False, encoding="utf-8-sig")
    nat_val.to_csv(OUT / "national_gdp_coverage_validation.csv", index=False, encoding="utf-8-sig")
    nat_summary.to_csv(OUT / "national_gdp_yearly_summary.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUT / "audit.csv", index=False, encoding="utf-8-sig")
    basis_audit.to_csv(OUT / "basis_source_audit.csv", index=False, encoding="utf-8-sig")
    source_gap_audit.to_csv(OUT / "missing_2023_sigungu_source_audit.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(json.dumps({"created_at": CREATED_AT, "git_hash": git_hash()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_source_doc(inventory)

    op_overall = (
        op_total.groupby(["track", "available_quarters", "operating_label"], as_index=False)
        .agg(
            rows=("year", "count"),
            annualized_wape_pct=("annualized_error_eok", lambda s: s.abs().sum() / op_total.loc[s.index, "official_annual_grdp_eok"].abs().sum() * 100),
            annualized_max_ape_pct=("annualized_ape_pct", "max"),
            cumulative_wape_pct=("cumulative_error_eok", lambda s: s.abs().sum() / op_total.loc[s.index, "official_cumulative_grdp_eok"].abs().sum() * 100),
            cumulative_max_ape_pct=("cumulative_ape_pct", "max"),
        )
    )
    worst_sido = (
        op_scenario.sort_values("annualized_wape_pct", ascending=False)
        .groupby(["track", "available_quarters"], group_keys=False)
        .head(5)
    )
    report = f"""# 전국 시군구 기반 분기누적 GRDP/GDP 집계검증

생성시각: {CREATED_AT}

## 목적

경기도·경북에서 수행한 `시군구×업종 하위 추정 → 시도 분기 GRDP actual 집계검증` 절차를 전국으로 확장했다. BOK RECI 문서의 17개 광역자치단체 기준에 맞춰 세종은 `세종시` 1개 하위단위로 처리했다. 17개 시도의 하위단위·업종 연간 GVA를 분기화하고, 시도별 분기누적/연간환산 WAPE를 계산한 뒤, 17개 시도 합계를 전국 공식 분기 GDP/GRDP 경계와 비교했다.

## 핵심 원칙

| 원칙 | 적용 |
| --- | --- |
| 목표분기 시도 actual 배분비 사용 금지 | 사용하지 않음 |
| 하위 추정값의 상위 집계검증 | 시군구/단층시→시도, 17개 시도→전국 |
| GVA와 GRDP 구분 | 시군구 업종 GVA + 별도 기타산업·순생산물세 bridge |
| 세종 처리 | BOK 17개 광역 기준 반영. `세종특별자치시→세종시` 1개 하위단위로 보존 |

## 검증 감사

{md_table(audit.rename(columns={'check':'검사','value':'값','status':'판정'}), 3)}

## 기준값 사용 감사

| 항목 | 내용 |
| --- | --- |
| 2023년 시군구 원천 부재 시도 | {', '.join(source_gap_audit['quarter_region'].tolist()) if not source_gap_audit.empty else '없음'} |
| 처리 | 엄격 속보형은 직전 예측 연간합을 이어 쓰고, 정밀형은 직전연도 시도 공식 업종합으로 구조를 보정 |
| 주의 | 정밀형은 사후 또는 충분한 공표시차 이후 활용 지표이며, Q+1개월 엄격 속보 지표로 해석하지 않음 |

{md_table(basis_audit.rename(columns={'track':'트랙','year':'연도','basis_source':'기준값출처','prediction_rows':'예측행'}), 0)}

## 모의 운영시점별 전국 17개 시도 전체 요약

본 표는 최신 공표 빈티지 기준의 사후 백테스트다. `1분기+1개월` 등은 사용 분기 수를 구분하기 위한 운영 화면 명칭이며, 과거 각 시점의 원천 빈티지를 완전 복원한 실시간 성과가 아니다.

{md_table(op_overall.rename(columns={
    'track':'트랙','available_quarters':'사용분기수','operating_label':'모의운영시점','rows':'검증행',
    'annualized_wape_pct':'연간환산WAPE_pct','annualized_max_ape_pct':'연간환산최대오차율_pct',
    'cumulative_wape_pct':'누적분기WAPE_pct','cumulative_max_ape_pct':'누적분기최대오차율_pct'
}), 3)}

## 전국 GDP 경계 검증: 17개 시도 합계 vs 전국

전국 계절비중을 사용하기 때문에 전국 경계 WAPE는 구조적으로 작아질 수 있다. 따라서 이 표는 시군구·시도 추정값의 외부 일관성 참고지표이며, 시도별·업종별 예측력이 모두 높다는 뜻은 아니다.

{md_table(nat_summary.rename(columns={
    'track':'트랙','year':'연도','quarters':'분기수','official_national_gdp_sum_eok':'공식전국GDP_억원',
    'covered17_predicted_sum_eok':'17개시도예측합_억원','national_abs_error_sum_eok':'절대오차합_억원',
    'national_wape_pct':'전국경계WAPE_pct'
}), 3)}

## 연간환산 WAPE가 큰 시도·운영시점

{md_table(worst_sido.rename(columns={
    'track':'트랙','quarter_region':'시도','available_quarters':'사용분기수','operating_label':'모의운영시점','years':'연도수',
    'annualized_abs_error_sum_eok':'연간환산절대오차합_억원','annualized_wape_pct':'연간환산WAPE_pct',
    'annualized_max_ape_pct':'연간환산최대오차율_pct','cumulative_wape_pct':'누적분기WAPE_pct',
    'cumulative_max_ape_pct':'누적분기최대오차율_pct'
}), 3)}

## 해석

1. 현재 로컬 원천으로는 17개 시도 전체에 대해 하위단위×업종 분기 추정이 가능하다. 세종은 하위 시군구가 없는 단층 지자체이므로 1개 하위단위로 처리한다.
2. 부산·대구·울산·강원·충남·경남은 2023년 시군구 연간 원천이 부재하여 일부 연도는 직전 예측값 또는 직전연도 시도 공식 업종합 보정을 사용했다. 해당 지역의 성과지표는 원천 공백 보정 효과를 포함한다.
3. 전국 비교는 `시도 추정합계`와 `전국 공식 분기 GDP/GRDP 경계`의 WAPE로 해석한다.
4. 실질 연쇄가격 계열은 엄밀한 회계 항등식처럼 완전 가산되는 값이 아닐 수 있으므로, 전국 합계 비교는 외부 집계검증 지표이지 공식 국민계정 대체값이 아니다.
5. 일부 광역시는 시군구 원천표의 경계연도·행정구역 변경(예: 군위군, 특별자치도 전환)을 별도 경계재정렬로 보강해야 한다.

## 산출물

- `nationwide/outputs/sigungu_industry_quarterly_predictions.csv`
- `nationwide/outputs/sido_quarterly_grdp_validation.csv`
- `nationwide/outputs/operating_point_sido_grdp_validation.csv`
- `nationwide/outputs/national_gdp_coverage_validation.csv`
- `nationwide/outputs/national_gdp_yearly_summary.csv`
- `nationwide/data_sources_and_release_cycles.md`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(audit.to_string(index=False))
    print(op_overall.to_string(index=False))
    print(nat_summary.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
