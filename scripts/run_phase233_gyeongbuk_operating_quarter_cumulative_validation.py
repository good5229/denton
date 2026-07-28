#!/usr/bin/env python3
"""Phase233: Gyeongbuk operating-quarter cumulative validation.

This phase reformats Phase232 into the same operating logic used in the Goyang
poster/proposal work:

* Q1+1 month: use Q1 estimates only
* Q1~Q2+1 month: use Q1-Q2 estimates
* Q1~Q3+1 month: use Q1-Q3 estimates
* post-release precision: use all four quarters

For Q1-Q3, the script reports two diagnostics:

1. cumulative GRDP error for the quarters available so far; and
2. annualized GRDP error, where the available cumulative estimate is expanded
   with the *prior-year national seasonal share* for each activity.  This avoids
   using target-year Gyeongbuk official quarterly values as features.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE232 = ROOT / "data" / "processed" / "phase232_gyeongbuk_quarterly_grdp_aggregation_validation"
XLSX_LONG = ROOT / "data" / "processed" / "phase211_gyeonggi_2024_2025_grdp_extension" / "phase211_sido_quarterly_xlsx_long.csv"
OUT = ROOT / "data" / "processed" / "phase233_gyeongbuk_operating_quarter_cumulative_validation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase233_gyeongbuk_operating_quarter_cumulative_validation.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

TOTAL_ACTIVITY = "지역내총생산(시장가격)"
OTHER_NPT_ACTIVITY = "기타산업 및 순생산물세"
MAIN_ACTIVITIES = ["광업, 제조업", "건설업", "서비스업", OTHER_NPT_ACTIVITY]
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
REPORT_ACTIVITIES = ["광업, 제조업", "건설업", "서비스업", *SERVICE_COMPONENTS, OTHER_NPT_ACTIVITY]
LABELS = {
    1: "1분기+1개월",
    2: "1~2분기+1개월",
    3: "1~3분기+1개월",
    4: "공표 후 정밀화",
}


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
        if str(c).lower() in {"year", "연도", "quarter", "available_quarters", "사용분기수", "분기수"}:
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


def official() -> pd.DataFrame:
    x = pd.read_csv(XLSX_LONG)
    x["region"] = x["region"].map(normalize_region)
    return x[x["region"].eq("경북") & x["activity"].isin([TOTAL_ACTIVITY, *REPORT_ACTIVITIES])].copy()


def national_prior_year_cum_share() -> pd.DataFrame:
    x = pd.read_csv(XLSX_LONG)
    nat = x[x["region"].eq("전국") & x["activity"].isin(REPORT_ACTIVITIES)].copy()
    nat["annual_eok"] = nat.groupby(["activity", "year"])["official_value_eok"].transform("sum")
    nat["cum_eok"] = nat.sort_values(["activity", "year", "quarter"]).groupby(["activity", "year"])["official_value_eok"].cumsum()
    nat["cum_share"] = nat["cum_eok"] / nat["annual_eok"]
    nat["target_year"] = nat["year"] + 1
    return nat[["activity", "target_year", "quarter", "cum_share"]].rename(columns={"target_year": "year", "quarter": "available_quarters", "cum_share": "prior_year_national_cum_share"})


def predicted_activity_quarters() -> pd.DataFrame:
    activity = pd.read_csv(PHASE232 / "phase232_gyeongbuk_activity_quarterly_validation.csv")
    # This file already contains province-level predictions by activity for both tracks.
    activity = activity[activity["activity"].isin(REPORT_ACTIVITIES)].copy()
    return activity[["track", "year", "quarter", "period", "activity", "predicted_value_eok"]]


def build_operating_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pred = predicted_activity_quarters()
    off = official()
    shares = national_prior_year_cum_share()
    off_activity = off[off["activity"].isin(REPORT_ACTIVITIES)].copy()

    rows = []
    activity_rows = []
    for track in sorted(pred["track"].unique()):
        for year in range(2021, 2026):
            for k in [1, 2, 3, 4]:
                p_sub = pred[(pred["track"].eq(track)) & (pred["year"].eq(year)) & (pred["quarter"].le(k))].copy()
                o_sub = off_activity[(off_activity["year"].eq(year)) & (off_activity["quarter"].le(k))].copy()
                p_cum = (
                    p_sub.groupby("activity", as_index=False)["predicted_value_eok"]
                    .sum()
                    .rename(columns={"predicted_value_eok": "predicted_cumulative_eok"})
                )
                o_cum = (
                    o_sub.groupby("activity", as_index=False)["official_value_eok"]
                    .sum()
                    .rename(columns={"official_value_eok": "official_cumulative_eok"})
                )
                annual_off = (
                    off_activity[off_activity["year"].eq(year)]
                    .groupby("activity", as_index=False)["official_value_eok"]
                    .sum()
                    .rename(columns={"official_value_eok": "official_annual_eok"})
                )
                act = p_cum.merge(o_cum, on="activity", how="left").merge(annual_off, on="activity", how="left")
                act["track"] = track
                act["year"] = year
                act["available_quarters"] = k
                act["operating_label"] = LABELS[k]
                if k < 4:
                    act = act.drop(columns=[c for c in ["prior_year_national_cum_share"] if c in act.columns])
                    act = act.merge(
                        shares[shares["available_quarters"].eq(k)][["activity", "year", "prior_year_national_cum_share"]],
                        on=["activity", "year"],
                        how="left",
                    )
                    act["annualized_predicted_eok"] = act["predicted_cumulative_eok"] / act["prior_year_national_cum_share"]
                    act["annualization_method"] = "available_cumulative_divided_by_prior_year_national_cum_share"
                else:
                    act["prior_year_national_cum_share"] = 1.0
                    act["annualized_predicted_eok"] = act["predicted_cumulative_eok"]
                    act["annualization_method"] = "four_quarter_sum_precision"
                act["cumulative_error_eok"] = act["predicted_cumulative_eok"] - act["official_cumulative_eok"]
                act["cumulative_ape_pct"] = act["cumulative_error_eok"].abs() / act["official_cumulative_eok"].abs() * 100
                act["annualized_error_eok"] = act["annualized_predicted_eok"] - act["official_annual_eok"]
                act["annualized_ape_pct"] = act["annualized_error_eok"].abs() / act["official_annual_eok"].abs() * 100
                activity_rows.append(act)

                main = act[act["activity"].isin(MAIN_ACTIVITIES)].copy()
                pred_cum_total = float(main["predicted_cumulative_eok"].sum())
                pred_annual_total = float(main["annualized_predicted_eok"].sum())
                official_cum_total = float(
                    off[(off["activity"].eq(TOTAL_ACTIVITY)) & (off["year"].eq(year)) & (off["quarter"].le(k))]["official_value_eok"].sum()
                )
                official_annual_total = float(
                    off[(off["activity"].eq(TOTAL_ACTIVITY)) & (off["year"].eq(year))]["official_value_eok"].sum()
                )
                rows.append(
                    {
                        "track": track,
                        "year": year,
                        "available_quarters": k,
                        "operating_label": LABELS[k],
                        "predicted_cumulative_grdp_eok": pred_cum_total,
                        "official_cumulative_grdp_eok": official_cum_total,
                        "cumulative_error_eok": pred_cum_total - official_cum_total,
                        "cumulative_ape_pct": abs(pred_cum_total - official_cum_total) / abs(official_cum_total) * 100,
                        "annualized_predicted_grdp_eok": pred_annual_total,
                        "official_annual_grdp_eok": official_annual_total,
                        "annualized_error_eok": pred_annual_total - official_annual_total,
                        "annualized_ape_pct": abs(pred_annual_total - official_annual_total) / abs(official_annual_total) * 100,
                        "annualization_method": "four_quarter_sum_precision" if k == 4 else "prior_year_national_cum_share",
                    }
                )

    total = pd.DataFrame(rows)
    activity = pd.concat(activity_rows, ignore_index=True)
    yearly = (
        total.groupby(["track", "available_quarters", "operating_label"], as_index=False)
        .agg(
            years=("year", "count"),
            annualized_abs_error_sum_eok=("annualized_error_eok", lambda s: s.abs().sum()),
            annualized_wape_pct=("annualized_error_eok", lambda s: s.abs().sum() / total.loc[s.index, "official_annual_grdp_eok"].abs().sum() * 100),
            annualized_max_ape_pct=("annualized_ape_pct", "max"),
            cumulative_wape_pct=("cumulative_error_eok", lambda s: s.abs().sum() / total.loc[s.index, "official_cumulative_grdp_eok"].abs().sum() * 100),
            cumulative_max_ape_pct=("cumulative_ape_pct", "max"),
        )
    )
    return total, activity, yearly


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    total, activity, scenario = build_operating_tables()

    total.to_csv(OUT / "phase233_gyeongbuk_operating_grdp_total_validation.csv", index=False, encoding="utf-8-sig")
    activity.to_csv(OUT / "phase233_gyeongbuk_operating_activity_validation.csv", index=False, encoding="utf-8-sig")
    scenario.to_csv(OUT / "phase233_gyeongbuk_operating_scenario_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(json.dumps({"created_at": CREATED_AT, "git_hash": git_hash()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audit = pd.DataFrame(
        [
            {"검사": "연도 범위", "값": f"{int(total.year.min())}~{int(total.year.max())}", "판정": "2021~2025"},
            {"검사": "운영시점 수", "값": int(total.available_quarters.nunique()), "판정": "4"},
            {"검사": "트랙 수", "값": int(total.track.nunique()), "판정": "2"},
            {"검사": "총량 검증 행", "값": int(len(total)), "판정": "2×5×4"},
            {"검사": "annualized actual 누락", "값": int(total.official_annual_grdp_eok.isna().sum()), "판정": "0"},
        ]
    )
    focus = total[
        [
            "track",
            "year",
            "available_quarters",
            "operating_label",
            "annualized_predicted_grdp_eok",
            "official_annual_grdp_eok",
            "annualized_error_eok",
            "annualized_ape_pct",
            "cumulative_ape_pct",
        ]
    ].rename(
        columns={
            "track": "트랙",
            "year": "연도",
            "available_quarters": "사용분기수",
            "operating_label": "운영시점",
            "annualized_predicted_grdp_eok": "연간환산예측_억원",
            "official_annual_grdp_eok": "공식연간GRDP_억원",
            "annualized_error_eok": "연간환산오차_억원",
            "annualized_ape_pct": "연간환산오차율_pct",
            "cumulative_ape_pct": "누적분기오차율_pct",
        }
    )
    scenario_view = scenario.rename(
        columns={
            "track": "트랙",
            "available_quarters": "사용분기수",
            "operating_label": "운영시점",
            "years": "연도수",
            "annualized_abs_error_sum_eok": "연간환산절대오차합_억원",
            "annualized_wape_pct": "연간환산WAPE_pct",
            "annualized_max_ape_pct": "연간환산최대오차율_pct",
            "cumulative_wape_pct": "누적분기WAPE_pct",
            "cumulative_max_ape_pct": "누적분기최대오차율_pct",
        }
    )
    activity_top = (
        activity.groupby(["track", "available_quarters", "operating_label", "activity"], as_index=False)
        .agg(
            official_annual_sum_eok=("official_annual_eok", "sum"),
            annualized_abs_error_sum_eok=("annualized_error_eok", lambda s: s.abs().sum()),
            annualized_wape_pct=("annualized_error_eok", lambda s: s.abs().sum() / activity.loc[s.index, "official_annual_eok"].abs().sum() * 100),
            annualized_max_ape_pct=("annualized_ape_pct", "max"),
        )
        .sort_values(["track", "available_quarters", "annualized_wape_pct"], ascending=[True, True, False])
        .groupby(["track", "available_quarters"], group_keys=False)
        .head(5)
    ).rename(
        columns={
            "track": "트랙",
            "available_quarters": "사용분기수",
            "operating_label": "운영시점",
            "activity": "업종",
            "official_annual_sum_eok": "공식연간합계_억원",
            "annualized_abs_error_sum_eok": "연간환산절대오차합_억원",
            "annualized_wape_pct": "연간환산WAPE_pct",
            "annualized_max_ape_pct": "연간환산최대오차율_pct",
        }
    )

    REPORT.write_text(
        f"""# Phase233 경북 분기누적 운영시점별 GRDP 검증

생성시각: {CREATED_AT}

## 목적

Phase232는 2021~2025년 전체 분기열을 만든 뒤 공식 경북 GRDP와 비교했다. 이번 단계는 고양시 포스터·제안서에서 사용한 운영방식에 맞춰 `1분기+1개월`, `1~2분기+1개월`, `1~3분기+1개월`, `공표 후 정밀화` 시점별로 다시 검증한다.

## 운영시점 정의

| 운영시점 | 사용자료 | 검증 |
| --- | --- | --- |
| 1분기+1개월 | Q1 추정 분기값 | Q1 누적오차 + 전년도 전국 계절비중 기반 연간환산오차 |
| 1~2분기+1개월 | Q1~Q2 추정 분기값 | 상반기 누적오차 + 연간환산오차 |
| 1~3분기+1개월 | Q1~Q3 추정 분기값 | 3분기 누적오차 + 연간환산오차 |
| 공표 후 정밀화 | Q1~Q4 추정 분기값 | 4분기 합계와 공식 연간 GRDP 비교 |

목표 분기의 경북 공식 GRDP나 경북 공식 업종값은 배분비로 쓰지 않고, 사후 검증값으로만 사용했다. Q1~Q3의 연간환산은 목표연도 전체 분기 정보를 쓰지 않기 위해 전년도 전국 업종별 누적 계절비중을 사용했다.

## 검증 감사

{md_table(audit, 3)}

## 운영시점별 2021~2025 전체 요약

{md_table(scenario_view, 3)}

## 연도×운영시점별 GRDP 오차

{md_table(focus, 3)}

## 업종별 고오차 요약

{md_table(activity_top, 3)}

## 해석

1. 2021~2025년 모든 연도에 대해 4개 운영시점별 오차를 산출했다.
2. Q1~Q3는 누적분기 자체의 오차와 연간환산 오차를 분리했다. 이 둘을 섞으면 고양시 때 지적했던 속보성/정밀화 해석 혼동이 다시 생긴다.
3. Q4는 이미 4개 분기 추정값이 있으므로 전년도 계절비중으로 다시 연간화하지 않고 4개 분기 합계를 공식 연간 GRDP와 비교한다.
4. 업종별 공식 분기 actual은 통계청 실험적 통계가 제공하는 수준까지만 검증했다. 제조업 중분류별 분기 actual은 제공되지 않아 광업·제조업 합산으로만 검증된다.

## 산출물

- `data/processed/phase233_gyeongbuk_operating_quarter_cumulative_validation/phase233_gyeongbuk_operating_grdp_total_validation.csv`
- `data/processed/phase233_gyeongbuk_operating_quarter_cumulative_validation/phase233_gyeongbuk_operating_activity_validation.csv`
- `data/processed/phase233_gyeongbuk_operating_quarter_cumulative_validation/phase233_gyeongbuk_operating_scenario_summary.csv`
""",
        encoding="utf-8",
    )
    print(scenario.to_string(index=False))
    print(audit.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
