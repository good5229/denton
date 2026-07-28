#!/usr/bin/env python3
"""Rolling pre-validation gate for hard-region indicator routes.

The previous no-worse table is useful as an upper-bound diagnostic, but it is
not an operational decision rule because it can inspect target-year actuals.
This script uses only prior years to decide whether an indicator route should
be adopted for the target year.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = HERE / "hard_region_indicator_route_rolling_gate.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

MAIN_GRDP_REPLACE_ACTIVITIES = ["광업, 제조업", "건설업", "서비스업"]


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{float(v):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = [
        "| " + " | ".join(x.columns) + " |",
        "| " + " | ".join(["---"] * len(x.columns)) + " |",
    ]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def make_rolling_selection(cand: pd.DataFrame) -> pd.DataFrame:
    keys = ["track", "quarter_region", "activity", "available_quarters"]
    rows = []
    for key, g in cand.groupby(keys):
        g = g.sort_values(["year", "route_id"]).copy()
        years = sorted(g["year"].unique())
        for year in years:
            current = g[g["year"].eq(year)].copy()
            if current.empty:
                continue
            base_row = current.iloc[0].copy()
            prior = g[g["year"].lt(year)].copy()
            selected_route_id = "baseline"
            selected_basis = "no_prior_positive_route"
            if not prior.empty:
                score = (
                    prior.groupby("route_id", as_index=False)
                    .agg(
                        prior_rows=("year", "count"),
                        prior_baseline_abs_error_eok=("baseline_abs_error_eok", "sum"),
                        prior_candidate_abs_error_eok=("candidate_abs_error_eok", "sum"),
                    )
                )
                score["prior_improvement_eok"] = (
                    score["prior_baseline_abs_error_eok"] - score["prior_candidate_abs_error_eok"]
                )
                score = score.sort_values(
                    ["prior_improvement_eok", "prior_rows", "route_id"],
                    ascending=[False, False, True],
                )
                if not score.empty and float(score.iloc[0]["prior_improvement_eok"]) > 0:
                    selected_route_id = str(score.iloc[0]["route_id"])
                    selected_basis = (
                        f"prior_positive_improvement_{float(score.iloc[0]['prior_improvement_eok']):.3f}_eok"
                    )
            selected = current[current["route_id"].eq(selected_route_id)]
            if selected_route_id == "baseline" or selected.empty:
                pred = float(base_row["annualized_predicted_eok"])
                err = float(base_row["annualized_error_eok"])
                candidate_ape = pd.NA
            else:
                selected = selected.iloc[0]
                pred = float(selected["candidate_annualized_eok"])
                err = float(selected["candidate_annualized_error_eok"])
                candidate_ape = float(selected["candidate_annualized_ape_pct"])
            official = float(base_row["official_annual_eok"])
            rows.append(
                {
                    "track": key[0],
                    "quarter_region": key[1],
                    "activity": key[2],
                    "available_quarters": key[3],
                    "year": int(year),
                    "selected_route_id": selected_route_id,
                    "selected_basis": selected_basis,
                    "baseline_predicted_eok": float(base_row["annualized_predicted_eok"]),
                    "selected_predicted_eok": pred,
                    "official_annual_eok": official,
                    "baseline_error_eok": float(base_row["annualized_error_eok"]),
                    "selected_error_eok": err,
                    "baseline_abs_error_eok": float(base_row["baseline_abs_error_eok"]),
                    "selected_abs_error_eok": abs(err),
                    "baseline_ape_pct": float(base_row["annualized_ape_pct"]),
                    "selected_ape_pct": abs(err) / abs(official) * 100 if official else pd.NA,
                    "target_candidate_ape_pct_if_adopted": candidate_ape,
                }
            )
    return pd.DataFrame(rows)


def summarize_activity(sel: pd.DataFrame) -> pd.DataFrame:
    s = (
        sel.groupby(["track", "activity", "available_quarters"], as_index=False)
        .agg(
            rows=("year", "count"),
            adopted_rows=("selected_route_id", lambda x: int((x != "baseline").sum())),
            official_sum_eok=("official_annual_eok", lambda x: x.abs().sum()),
            baseline_abs_error_sum_eok=("baseline_abs_error_eok", "sum"),
            selected_abs_error_sum_eok=("selected_abs_error_eok", "sum"),
            max_selected_ape_pct=("selected_ape_pct", "max"),
        )
    )
    s["baseline_wape_pct"] = s["baseline_abs_error_sum_eok"] / s["official_sum_eok"] * 100
    s["selected_wape_pct"] = s["selected_abs_error_sum_eok"] / s["official_sum_eok"] * 100
    s["delta_wape_pp"] = s["selected_wape_pct"] - s["baseline_wape_pct"]
    return s


def recompute_grdp(sel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    op_total = pd.read_csv(OUT / "operating_point_sido_grdp_validation.csv")
    hard_regions = sel["quarter_region"].dropna().unique().tolist()
    hard_total = op_total[op_total["quarter_region"].isin(hard_regions)].copy()
    main = sel[sel["activity"].isin(MAIN_GRDP_REPLACE_ACTIVITIES)].copy()
    adj = (
        main.groupby(["track", "quarter_region", "year", "available_quarters"], as_index=False)
        .agg(
            baseline_main_pred=("baseline_predicted_eok", "sum"),
            selected_main_pred=("selected_predicted_eok", "sum"),
            adopted_main_rows=("selected_route_id", lambda x: int((x != "baseline").sum())),
        )
    )
    grdp = hard_total.merge(adj, on=["track", "quarter_region", "year", "available_quarters"], how="left")
    for c in ["baseline_main_pred", "selected_main_pred", "adopted_main_rows"]:
        grdp[c] = grdp[c].fillna(0.0)
    grdp["rolling_routed_annualized_predicted_grdp_eok"] = (
        grdp["annualized_predicted_grdp_eok"] + grdp["selected_main_pred"] - grdp["baseline_main_pred"]
    )
    grdp["rolling_routed_error_eok"] = (
        grdp["rolling_routed_annualized_predicted_grdp_eok"] - grdp["official_annual_grdp_eok"]
    )
    grdp["rolling_routed_ape_pct"] = (
        grdp["rolling_routed_error_eok"].abs() / grdp["official_annual_grdp_eok"].abs() * 100
    )
    summary = (
        grdp.groupby(["track", "available_quarters", "operating_label"], as_index=False)
        .agg(
            rows=("year", "count"),
            baseline_abs_error_sum_eok=("annualized_error_eok", lambda x: x.abs().sum()),
            rolling_abs_error_sum_eok=("rolling_routed_error_eok", lambda x: x.abs().sum()),
            official_sum_eok=("official_annual_grdp_eok", lambda x: x.abs().sum()),
            max_baseline_ape_pct=("annualized_ape_pct", "max"),
            max_rolling_ape_pct=("rolling_routed_ape_pct", "max"),
            adopted_main_rows=("adopted_main_rows", "sum"),
        )
    )
    summary["baseline_wape_pct"] = summary["baseline_abs_error_sum_eok"] / summary["official_sum_eok"] * 100
    summary["rolling_wape_pct"] = summary["rolling_abs_error_sum_eok"] / summary["official_sum_eok"] * 100
    summary["delta_wape_pp"] = summary["rolling_wape_pct"] - summary["baseline_wape_pct"]
    return grdp, summary


def main() -> int:
    cand = pd.read_csv(OUT / "hard_region_indicator_route_candidate_detail.csv")
    required = {
        "track",
        "quarter_region",
        "activity",
        "available_quarters",
        "year",
        "route_id",
        "annualized_predicted_eok",
        "annualized_error_eok",
        "annualized_ape_pct",
        "candidate_annualized_eok",
        "candidate_annualized_error_eok",
        "candidate_annualized_ape_pct",
        "official_annual_eok",
        "baseline_abs_error_eok",
        "candidate_abs_error_eok",
    }
    missing = required - set(cand.columns)
    if missing:
        raise SystemExit(f"missing columns in candidate detail: {sorted(missing)}")
    sel = make_rolling_selection(cand)
    activity_summary = summarize_activity(sel)
    grdp, grdp_summary = recompute_grdp(sel)

    sel.to_csv(OUT / "hard_region_indicator_route_rolling_gate_detail.csv", index=False, encoding="utf-8-sig")
    activity_summary.to_csv(
        OUT / "hard_region_indicator_route_rolling_gate_activity_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    grdp.to_csv(OUT / "hard_region_indicator_route_rolling_gate_grdp_detail.csv", index=False, encoding="utf-8-sig")
    grdp_summary.to_csv(
        OUT / "hard_region_indicator_route_rolling_gate_grdp_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    headline = grdp_summary[
        grdp_summary["track"].eq("recursive_no_target_actual")
        & grdp_summary["available_quarters"].isin([1, 2, 3, 4])
    ].copy()
    activity_headline = activity_summary[
        activity_summary["track"].eq("recursive_no_target_actual")
        & activity_summary["available_quarters"].isin([1, 2, 3, 4])
    ].sort_values(["available_quarters", "delta_wape_pp"]).head(32)

    report = f"""# 어려운 5개 지역 활동지표 사전검증 채택 실험

생성시각: {CREATED_AT}

## 목적

기존 no-worse 실험은 목표연도 actual을 확인한 뒤 좋아진 후보만 고르는 상한 진단이었다. 이 문서는 목표연도 actual을 보지 않고, **이전 연도까지의 누적 성과가 좋은 지표만 다음 연도에 채택**하는 운영형 규칙을 검증한다.

## 채택 규칙

| 단계 | 내용 |
| --- | --- |
| 후보 | 제조업 생산지수, 서비스업 생산지수, 건설수주액 원자료·분산지표 |
| 평가단위 | 트랙 × 시도 × 업종 × 사용분기수 × 후보지표 |
| 채택조건 | 목표연도 이전 연도들에서 후보지표 누적 절대오차가 기본방식보다 작을 것 |
| 선택방식 | 이전 연도 누적 개선액이 가장 큰 후보 1개 선택 |
| 미충족 | 기본방식 유지 |
| 첫 연도 | 이전 검증연도가 없으므로 기본방식 유지 |

## GRDP 총량 기준 결과: 어려운 5개 지역

{md_table(headline[[
    "available_quarters", "operating_label", "baseline_wape_pct", "rolling_wape_pct",
    "delta_wape_pp", "max_baseline_ape_pct", "max_rolling_ape_pct", "adopted_main_rows"
]].rename(columns={
    "available_quarters": "사용분기수",
    "operating_label": "모의운영시점",
    "baseline_wape_pct": "기존WAPE_pct",
    "rolling_wape_pct": "사전채택WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "max_baseline_ape_pct": "기존최대오차율_pct",
    "max_rolling_ape_pct": "사전채택최대오차율_pct",
    "adopted_main_rows": "주요업종채택행수",
}), 3)}

## 업종별 개선 후보

{md_table(activity_headline[[
    "activity", "available_quarters", "baseline_wape_pct", "selected_wape_pct",
    "delta_wape_pp", "adopted_rows", "max_selected_ape_pct"
]].rename(columns={
    "activity": "업종",
    "available_quarters": "사용분기수",
    "baseline_wape_pct": "기존WAPE_pct",
    "selected_wape_pct": "사전채택WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "adopted_rows": "채택행수",
    "max_selected_ape_pct": "채택후최대오차율_pct",
}), 3)}

## 판단

1. 목표연도 actual을 보지 않는 사전검증 규칙에서는 **1분기+1개월과 1~2분기+1개월 총량 오차가 개선**됐다.
2. 1~3분기와 공표 후 정밀화에서는 단순 과거성과 채택이 오히려 악화됐다. 활동지표가 모든 시점에서 자동으로 우월하다는 주장은 부적절하다.
3. 운영 규칙은 “상반기 조기점검의 보조지표”로 제한하고, 3분기 이후와 정밀화는 기본 계층배분을 우선하는 것이 더 안전하다.
4. no-worse 결과는 후보 지표의 가능성을 보는 상한 진단이고, 실제 운영 성능 주장은 이 사전채택 결과를 우선해야 한다.
5. 단, Q+1개월 속보 주장에는 지표별 실제 공표일 검증이 추가로 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(headline.to_string(index=False))
    print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
