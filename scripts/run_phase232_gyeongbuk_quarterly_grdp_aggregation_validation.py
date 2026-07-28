#!/usr/bin/env python3
"""Phase232: Gyeongbuk sigungu-industry quarterly GRDP aggregation validation.

Goal
----
Estimate quarterly industry GVA for all Gyeongbuk sigungu using only prior-year
sigungu annual industry GVA plus national same-activity quarterly movement, then
aggregate to Gyeongbuk and compare with Statistics Korea's experimental
quarterly regional GRDP table.

This intentionally does *not* use Gyeongbuk target-quarter actual values as
allocation weights.  That would make the validation tautological.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_SIGUNGU = ROOT / "data" / "raw" / "expanded_sigungu_grva_real.json"
XLSX_LONG = ROOT / "data" / "processed" / "phase211_gyeonggi_2024_2025_grdp_extension" / "phase211_sido_quarterly_xlsx_long.csv"
OUT = ROOT / "data" / "processed" / "phase232_gyeongbuk_quarterly_grdp_aggregation_validation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase232_gyeongbuk_quarterly_grdp_aggregation_validation.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

GYEONGBUK_TABLE = "216_DT_GRDP202037_02"
TOTAL_ACTIVITY = "지역내총생산(시장가격)"
OTHER_NPT_ACTIVITY = "기타산업 및 순생산물세"

CODE_TO_GROUP = {
    "03": "광업, 제조업",
    "04": "광업, 제조업",
    "06": "건설업",
    "07": "도매 및 소매업",
    "08": "운수 및 창고업",
    "09": "숙박 및 음식점업",
    "10": "정보통신업",
    "11": "금융 및 보험업",
    "12": "부동산업",
    "13": "사업서비스업",
    "14": "공공 행정, 국방·사회보장",
    "15": "교육 서비스업",
    "16": "보건 및 사회복지업",
    "17": "문화 및 기타서비스업",
}
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


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if str(c).lower() in {"year", "연도", "quarter", "분기수", "분기"}:
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


def normalize_region(region: str) -> str:
    return {"경상북도": "경북"}.get(str(region), str(region))


def load_gyeongbuk_sigungu_annual() -> pd.DataFrame:
    obj = json.loads(RAW_SIGUNGU.read_text())
    raw = pd.DataFrame(obj[GYEONGBUK_TABLE])
    raw = raw[raw["C2"].isin(CODE_TO_GROUP)].copy()
    raw["year"] = raw["PRD_DE"].astype(int)
    raw["city"] = raw["C1_NM"].astype(str)
    raw["activity_group"] = raw["C2"].map(CODE_TO_GROUP)
    raw["value_eok"] = pd.to_numeric(raw["DT"], errors="coerce") / 100.0
    # Drop the province aggregate; the exercise is to rebuild it from sigungu.
    raw = raw[raw["city"].ne("경상북도")].copy()
    annual = (
        raw.groupby(["year", "city", "activity_group"], as_index=False)
        .agg(annual_gva_eok=("value_eok", "sum"), source_latest_change_date=("LST_CHN_DE", "max"))
    )
    return annual


def load_quarterly_official() -> pd.DataFrame:
    x = pd.read_csv(XLSX_LONG)
    x["region"] = x["region"].map(normalize_region)
    return x


def national_quarter_factor(x: pd.DataFrame) -> pd.DataFrame:
    nat = x[x["region"].eq("전국") & x["activity"].isin(VALIDATION_ACTIVITIES)].copy()
    nat["previous_year_annual_eok"] = nat.groupby(["activity", "year"])["official_value_eok"].transform("sum")
    prev_annual = (
        nat.groupby(["activity", "year"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"official_value_eok": "national_annual_eok"})
    )
    prev_annual["target_year"] = prev_annual["year"] + 1
    f = nat.merge(
        prev_annual[["activity", "target_year", "national_annual_eok"]],
        left_on=["activity", "year"],
        right_on=["activity", "target_year"],
        how="left",
    )
    f["quarter_factor_from_prev_annual"] = f["official_value_eok"] / f["national_annual_eok"]
    return f[["activity", "year", "quarter", "period", "quarter_factor_from_prev_annual"]].dropna()


def official_region_activity(x: pd.DataFrame) -> pd.DataFrame:
    gb = x[x["region"].eq("경북") & x["activity"].isin([TOTAL_ACTIVITY, *VALIDATION_ACTIVITIES])].copy()
    return gb[["activity", "year", "quarter", "period", "official_value_eok"]].copy()


def prior_other_npt_annual_for_year(x: pd.DataFrame, track: str, year: int, predicted_other_annual: dict[int, float]) -> pd.DataFrame:
    official = official_region_activity(x)
    other_y = (
        official[official["activity"].eq(OTHER_NPT_ACTIVITY)]
        .groupby("year", as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"official_value_eok": "official_other_npt_annual_eok"})
    )
    prev_year = year - 1
    if track == "prior_year_province_anchor" or prev_year <= 2023:
        val = float(other_y.loc[other_y.year.eq(prev_year), "official_other_npt_annual_eok"].iloc[0])
        source = f"official_prior_year_{prev_year}"
    else:
        val = float(predicted_other_annual[prev_year])
        source = f"recursive_predicted_prior_year_{prev_year}"
    return pd.DataFrame([{"year": year, "prior_other_npt_annual_eok": val, "other_npt_source": source}])


def build_predictions(track: str, annual: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    factors = national_quarter_factor(x)
    official = official_region_activity(x)
    city_basis = annual.copy()
    predicted_other_annual: dict[int, float] = {}
    all_city_quarters = []
    all_other = []

    for year in range(2021, 2026):
        prev_year = year - 1
        if prev_year <= 2023:
            basis = city_basis[city_basis["year"].eq(prev_year)].copy()
            basis["basis_source"] = f"official_sigungu_annual_{prev_year}"
        else:
            prior_pred = pd.concat(all_city_quarters, ignore_index=True)
            basis = (
                prior_pred[prior_pred["year"].eq(prev_year)]
                .groupby(["city", "activity_group"], as_index=False)["predicted_gva_eok"]
                .sum()
                .rename(columns={"predicted_gva_eok": "annual_gva_eok"})
            )
            if track == "prior_year_province_anchor":
                official_y = (
                    official[
                        official["year"].eq(prev_year)
                        & official["activity"].isin(["광업, 제조업", "건설업", *SERVICE_COMPONENTS])
                    ]
                    .groupby("activity", as_index=False)["official_value_eok"]
                    .sum()
                    .rename(columns={"activity": "activity_group", "official_value_eok": "official_group_annual_eok"})
                )
                pred_y = basis.groupby("activity_group", as_index=False)["annual_gva_eok"].sum().rename(columns={"annual_gva_eok": "pred_group_annual_eok"})
                scale = official_y.merge(pred_y, on="activity_group", how="left")
                scale["scale_factor"] = scale["official_group_annual_eok"] / scale["pred_group_annual_eok"]
                basis = basis.merge(scale[["activity_group", "scale_factor"]], on="activity_group", how="left")
                basis["annual_gva_eok"] = basis["annual_gva_eok"] * basis["scale_factor"].fillna(1.0)
                basis["basis_source"] = f"predicted_sigungu_{prev_year}_scaled_to_official_gyeongbuk_activity"
            else:
                basis["basis_source"] = f"recursive_predicted_sigungu_{prev_year}"

        q = factors[factors["year"].eq(year)].copy()
        q = q[q["activity"].isin(["광업, 제조업", "건설업", *SERVICE_COMPONENTS])]
        pred = basis.merge(q, left_on="activity_group", right_on="activity", how="inner")
        pred["year"] = year
        pred["predicted_gva_eok"] = pred["annual_gva_eok"] * pred["quarter_factor_from_prev_annual"]
        all_city_quarters.append(
            pred[
                [
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
        )

        other_basis = prior_other_npt_annual_for_year(x, track, year, predicted_other_annual)
        other_f = factors[factors["year"].eq(year) & factors["activity"].eq(OTHER_NPT_ACTIVITY)].copy()
        other = other_basis.merge(other_f, on="year", how="inner")
        other["predicted_other_npt_eok"] = other["prior_other_npt_annual_eok"] * other["quarter_factor_from_prev_annual"]
        predicted_other_annual[year] = float(other["predicted_other_npt_eok"].sum())
        all_other.append(other[["year", "quarter", "period", "predicted_other_npt_eok", "other_npt_source", "quarter_factor_from_prev_annual"]])

    city_quarters = pd.concat(all_city_quarters, ignore_index=True)
    other_q = pd.concat(all_other, ignore_index=True)
    city_quarters["track"] = track
    other_q["track"] = track
    return city_quarters, other_q


def validate(track: str, city_q: pd.DataFrame, other_q: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    official = official_region_activity(x)
    activity_pred = (
        city_q.groupby(["track", "year", "quarter", "period", "activity_group"], as_index=False)["predicted_gva_eok"]
        .sum()
        .rename(columns={"activity_group": "activity", "predicted_gva_eok": "predicted_value_eok"})
    )
    service = (
        activity_pred[activity_pred["activity"].isin(SERVICE_COMPONENTS)]
        .groupby(["track", "year", "quarter", "period"], as_index=False)["predicted_value_eok"]
        .sum()
    )
    service["activity"] = "서비스업"
    other = other_q.rename(columns={"predicted_other_npt_eok": "predicted_value_eok"})
    other["activity"] = OTHER_NPT_ACTIVITY
    other = other[["track", "year", "quarter", "period", "activity", "predicted_value_eok"]]
    activity_all = pd.concat([activity_pred, service, other], ignore_index=True)

    actual = official[official["activity"].isin(VALIDATION_ACTIVITIES)].rename(columns={"official_value_eok": "official_value_eok"})
    activity_val = activity_all.merge(actual, on=["activity", "year", "quarter", "period"], how="left")
    activity_val["error_eok"] = activity_val["predicted_value_eok"] - activity_val["official_value_eok"]
    activity_val["abs_error_eok"] = activity_val["error_eok"].abs()
    activity_val["ape_pct"] = activity_val["abs_error_eok"] / activity_val["official_value_eok"].abs() * 100

    main = activity_all[activity_all["activity"].isin(["광업, 제조업", "건설업", "서비스업", OTHER_NPT_ACTIVITY])]
    total_pred = main.groupby(["track", "year", "quarter", "period"], as_index=False)["predicted_value_eok"].sum().rename(columns={"predicted_value_eok": "predicted_grdp_market_price_eok"})
    total_actual = official[official["activity"].eq(TOTAL_ACTIVITY)][["year", "quarter", "period", "official_value_eok"]].rename(columns={"official_value_eok": "official_grdp_market_price_eok"})
    total_val = total_pred.merge(total_actual, on=["year", "quarter", "period"], how="left")
    total_val["error_eok"] = total_val["predicted_grdp_market_price_eok"] - total_val["official_grdp_market_price_eok"]
    total_val["abs_error_eok"] = total_val["error_eok"].abs()
    total_val["ape_pct"] = total_val["abs_error_eok"] / total_val["official_grdp_market_price_eok"].abs() * 100

    summary = (
        total_val.groupby(["track", "year"], as_index=False)
        .agg(
            quarters=("period", "count"),
            official_sum_eok=("official_grdp_market_price_eok", "sum"),
            predicted_sum_eok=("predicted_grdp_market_price_eok", "sum"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            wape_pct=("abs_error_eok", lambda s: s.sum() / total_val.loc[s.index, "official_grdp_market_price_eok"].abs().sum() * 100),
            max_ape_pct=("ape_pct", "max"),
        )
    )
    return activity_val, total_val, summary


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    annual = load_gyeongbuk_sigungu_annual()
    x = load_quarterly_official()

    outputs = []
    total_outputs = []
    summaries = []
    city_outputs = []
    other_outputs = []
    for track in ["recursive_no_target_actual", "prior_year_province_anchor"]:
        city_q, other_q = build_predictions(track, annual, x)
        activity_val, total_val, summary = validate(track, city_q, other_q, x)
        outputs.append(activity_val)
        total_outputs.append(total_val)
        summaries.append(summary)
        city_outputs.append(city_q)
        other_outputs.append(other_q)

    city_all = pd.concat(city_outputs, ignore_index=True)
    other_all = pd.concat(other_outputs, ignore_index=True)
    activity_all = pd.concat(outputs, ignore_index=True)
    total_all = pd.concat(total_outputs, ignore_index=True)
    summary_all = pd.concat(summaries, ignore_index=True)
    activity_summary = (
        activity_all.groupby(["track", "activity"], as_index=False)
        .agg(
            official_sum_eok=("official_value_eok", "sum"),
            predicted_sum_eok=("predicted_value_eok", "sum"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            wape_pct=("abs_error_eok", lambda s: s.sum() / activity_all.loc[s.index, "official_value_eok"].abs().sum() * 100),
            max_ape_pct=("ape_pct", "max"),
        )
        .sort_values(["track", "wape_pct"], ascending=[True, False])
    )
    city_annual_2023 = (
        annual[annual["year"].eq(2023)]
        .groupby("city", as_index=False)["annual_gva_eok"]
        .sum()
        .sort_values("annual_gva_eok", ascending=False)
    )
    audit = pd.DataFrame(
        [
            {"검사": "경북 시군 수(2023)", "값": int(city_annual_2023["city"].nunique()), "판정": "정보"},
            {"검사": "시군×업종 분기 추정 행", "값": int(len(city_all)), "판정": "정보"},
            {"검사": "공식 경북 분기 actual 누락", "값": int(total_all["official_grdp_market_price_eok"].isna().sum()), "판정": "0"},
            {"검사": "업종 actual 누락", "값": int(activity_all["official_value_eok"].isna().sum()), "판정": "0"},
        ]
    )
    city_list = pd.DataFrame({"경북_연간표_시군": sorted(city_annual_2023["city"].unique())})

    city_all.to_csv(OUT / "phase232_gyeongbuk_sigungu_industry_quarterly_predictions.csv", index=False, encoding="utf-8-sig")
    other_all.to_csv(OUT / "phase232_gyeongbuk_other_npt_quarterly_predictions.csv", index=False, encoding="utf-8-sig")
    total_all.to_csv(OUT / "phase232_gyeongbuk_quarterly_grdp_validation.csv", index=False, encoding="utf-8-sig")
    activity_all.to_csv(OUT / "phase232_gyeongbuk_activity_quarterly_validation.csv", index=False, encoding="utf-8-sig")
    summary_all.to_csv(OUT / "phase232_gyeongbuk_yearly_summary.csv", index=False, encoding="utf-8-sig")
    activity_summary.to_csv(OUT / "phase232_gyeongbuk_activity_summary.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUT / "phase232_audit.csv", index=False, encoding="utf-8-sig")
    city_list.to_csv(OUT / "phase232_gyeongbuk_sigungu_list.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(json.dumps({"created_at": CREATED_AT, "git_hash": git_hash()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    focus_total = total_all[total_all["year"].between(2024, 2025)].copy()
    focus_total_view = focus_total[
        ["track", "period", "predicted_grdp_market_price_eok", "official_grdp_market_price_eok", "error_eok", "ape_pct"]
    ].rename(
        columns={
            "track": "트랙",
            "period": "분기",
            "predicted_grdp_market_price_eok": "예측GRDP_억원",
            "official_grdp_market_price_eok": "공식GRDP_억원",
            "error_eok": "오차_억원",
            "ape_pct": "오차율_pct",
        }
    )
    summary_view = summary_all[summary_all["year"].between(2021, 2025)].rename(
        columns={
            "track": "트랙",
            "year": "연도",
            "quarters": "분기수",
            "official_sum_eok": "공식합계_억원",
            "predicted_sum_eok": "예측합계_억원",
            "abs_error_sum_eok": "절대오차합_억원",
            "wape_pct": "WAPE_pct",
            "max_ape_pct": "최대분기오차율_pct",
        }
    )
    activity_view = activity_summary.groupby("track", group_keys=False).head(8).rename(
        columns={
            "track": "트랙",
            "activity": "업종",
            "official_sum_eok": "공식합계_억원",
            "predicted_sum_eok": "예측합계_억원",
            "abs_error_sum_eok": "절대오차합_억원",
            "wape_pct": "WAPE_pct",
            "max_ape_pct": "최대분기오차율_pct",
        }
    )

    REPORT.write_text(
        f"""# Phase232 경북 시군·업종 분기 GRDP 집계검증

생성시각: {CREATED_AT}

## 목적

포항시 단독 업종 추정값을 더 고치는 단계는 일단 중단하고, 같은 구조를 경상북도 전체 시군으로 확장했을 때 상위 공식 분기 GRDP와 맞는지 검증했다. 핵심은 `시군·업종 하위 추정 → 경북 상위 actual 집계검증`이다.

## 누수 방지 기준

| 항목 | 사용 여부 |
| --- | --- |
| 목표 분기의 경북 공식 업종값을 배분비로 사용 | 미사용 |
| 전년도 경북 시군·업종 연간 GVA | 사용 |
| 전국 동업종 분기 변화 | 사용 |
| 목표 분기 경북 GRDP actual | 검증에만 사용 |
| 2025년 전년도 경북 상위 공식값 | `prior_year_province_anchor` 트랙에서만 사용 |

## 추정 트랙

| 트랙 | 의미 |
| --- | --- |
| `recursive_no_target_actual` | 2025년에도 2024년 예측 시군·업종값을 이어 쓰는 완전 외삽형 |
| `prior_year_province_anchor` | 2025년 예측 전 이미 알 수 있는 2024년 경북 상위 연간 공식값으로 전년도 기준만 정렬한 정밀형 |

## 검증 감사

{md_table(audit, 0)}

연간 시군·업종표의 경북 경계는 2023년 KOSIS 원천표 기준 23개 시군이다. 이 표에는 군위군이 포함되어 있으므로, 행정구역 기준연도 변경을 적용하는 별도 실험에서는 경계 재정렬이 필요하다.

## 연도별 경북 GRDP 시장가격 검증

{md_table(summary_view, 3)}

## 2024~2025 분기별 경북 GRDP 시장가격 검증

{md_table(focus_total_view, 3)}

## 업종별 집계검증: 오차가 큰 업종

{md_table(activity_view, 3)}

## 해석

1. 경북 23개 시군의 업종별 연간 GVA를 모두 분기화해 합산하면, 경북 공식 분기 GRDP와 직접 비교할 수 있다.
2. 이 검증은 포항 한 도시의 숫자만 맞추는 것이 아니라, 같은 추정 방식이 경북 전체 회계경계에서 어느 정도 닫히는지 보는 외부 검증이다.
3. 공식 XLSX의 업종 구분은 제조업 세부 중분류가 아니라 광업·제조업/건설업/서비스업 및 서비스 세부 업종이므로, 제조업 중분류별 공식 분기 대조는 현재 불가능하다.
4. 업종별로는 서비스 세부 업종과 기타산업·순생산물세에서 오차가 커지는지 확인해야 하며, 이 부분이 포항시 잔여 고오차 업종과 연결된다.

## 산출물

- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_sigungu_industry_quarterly_predictions.csv`
- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_quarterly_grdp_validation.csv`
- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_activity_quarterly_validation.csv`
- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_yearly_summary.csv`
- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_activity_summary.csv`
""",
        encoding="utf-8",
    )
    print(summary_all.to_string(index=False))
    print(audit.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
