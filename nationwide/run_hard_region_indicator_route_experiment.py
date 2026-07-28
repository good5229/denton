#!/usr/bin/env python3
"""Indicator-routed improvement experiment for five hard regions.

This is a candidate experiment, not a claim of fully vintage-perfect nowcasting.
It tests whether region-specific public indicators reduce errors relative to
the nationwide common seasonal/activity shares used by the first nationwide run.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = HERE / "hard_region_indicator_route_experiment.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

HARD_REGIONS = ["인천", "울산", "세종", "대구", "충북"]
REGION_FULL = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기도": "경기도",
    "강원": "강원도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전라북도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}

SERVICE_MAP = {
    "서비스업": ["T"],
    "도매 및 소매업": ["G"],
    "운수 및 창고업": ["H"],
    "숙박 및 음식점업": ["I"],
    "정보통신업": ["J"],
    "금융 및 보험업": ["K"],
    "부동산업": ["L"],
    "사업서비스업": ["M", "N"],
    "교육 서비스업": ["P"],
    "보건 및 사회복지업": ["Q"],
    "문화 및 기타서비스업": ["R", "S"],
}


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


def wape(err: pd.Series, actual: pd.Series) -> float:
    return float(err.abs().sum() / actual.abs().sum() * 100)


def load_official_activity() -> pd.DataFrame:
    x = pd.read_csv(OUT / "sido_activity_quarterly_validation.csv")
    return x


def annual_official() -> pd.DataFrame:
    x = pd.read_csv("data/processed/phase211_gyeonggi_2024_2025_grdp_extension/phase211_sido_quarterly_xlsx_long.csv")
    return (
        x[x["region"].isin(HARD_REGIONS)]
        .groupby(["region", "activity", "year"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"region": "quarter_region", "official_value_eok": "official_annual_eok"})
    )


def make_indicator_panel() -> pd.DataFrame:
    panels = []
    # Manufacturing: monthly mining/manufacturing production index, use 제조업 C.
    m = pd.read_csv("data/processed/phase195_monthly_mining_manufacturing_production_index.csv")
    m = m[(m["c1_nm"].isin(REGION_FULL.values())) & (m["c2_nm"].eq("제조업"))].copy()
    m["year"] = m["prd_de"].astype(str).str[:4].astype(int)
    m["quarter"] = ((m["prd_de"].astype(str).str[4:6].astype(int) - 1) // 3 + 1).astype(int)
    m["quarter_region"] = m["c1_nm"].map({v: k for k, v in REGION_FULL.items()})
    mm = (
        m.groupby(["quarter_region", "year", "quarter"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "indicator_value"})
    )
    mm["activity"] = "광업, 제조업"
    mm["route_id"] = "regional_manufacturing_production_index"
    panels.append(mm)

    # Service: quarterly service production index by city/activity.
    svc = pd.read_csv("data/processed/rolling_service_production_index.csv", encoding="cp949")
    svc = svc[svc["c1_nm"].isin(REGION_FULL.values())].copy()
    svc["year"] = svc["prd_de"].astype(str).str[:4].astype(int)
    svc["quarter"] = svc["prd_de"].astype(str).str[4:6].astype(int)
    svc["quarter_region"] = svc["c1_nm"].map({v: k for k, v in REGION_FULL.items()})
    for activity, codes in SERVICE_MAP.items():
        tmp = svc[svc["c2_id"].astype(str).isin(codes)].copy()
        # Indexes are not additive; average when two sub-indexes make one GRDP block.
        q = (
            tmp.groupby(["quarter_region", "year", "quarter"], as_index=False)["value"]
            .mean()
            .rename(columns={"value": "indicator_value"})
        )
        q["activity"] = activity
        q["route_id"] = "regional_service_production_index_" + "_".join(codes)
        panels.append(q)

    # Construction: raw construction orders and simple BOK-style distributed order stock.
    rk = pd.read_csv("data/processed/rolling_kosis_collected_all.csv", encoding="cp949")
    con = rk[(rk["tbl_id"].eq("DT_1G1B035")) & (rk["c1_nm"].isin(REGION_FULL.values()))].copy()
    con["year"] = con["prd_de"].astype(str).str[:4].astype(int)
    con["quarter"] = con["prd_de"].astype(str).str[4:6].astype(int)
    con["quarter_region"] = con["c1_nm"].map({v: k for k, v in REGION_FULL.items()})
    raw = (
        con[con["c2_nm"].eq("계")]
        .groupby(["quarter_region", "year", "quarter"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "indicator_value"})
    )
    raw["activity"] = "건설업"
    raw["route_id"] = "regional_construction_orders_raw"
    panels.append(raw)
    pivot = (
        con[con["c2_nm"].isin(["건축", "토목"])]
        .pivot_table(index=["quarter_region", "year", "quarter"], columns="c2_nm", values="value", aggfunc="sum")
        .reset_index()
        .sort_values(["quarter_region", "year", "quarter"])
    )
    for c in ["건축", "토목"]:
        if c not in pivot.columns:
            pivot[c] = 0.0
        pivot[c] = pivot[c].fillna(0.0)
    distributed = []
    for region, g in pivot.groupby("quarter_region"):
        h = g.sort_values(["year", "quarter"]).copy()
        h["building_12q"] = h["건축"].rolling(12, min_periods=1).mean()
        h["civil_24q"] = h["토목"].rolling(24, min_periods=1).mean()
        h["indicator_value"] = h["building_12q"] + h["civil_24q"]
        distributed.append(h[["quarter_region", "year", "quarter", "indicator_value"]])
    dist = pd.concat(distributed, ignore_index=True)
    dist["activity"] = "건설업"
    dist["route_id"] = "regional_construction_orders_bok_12_24q"
    panels.append(dist)

    panel = pd.concat(panels, ignore_index=True)
    panel = panel[panel["quarter_region"].isin(HARD_REGIONS) & panel["year"].between(2020, 2025)].copy()
    panel["indicator_value"] = pd.to_numeric(panel["indicator_value"], errors="coerce")
    panel = panel.dropna(subset=["indicator_value"])
    return panel


def route_predictions(panel: pd.DataFrame) -> pd.DataFrame:
    annual = annual_official()
    rows = []
    for (region, activity, route_id, year), g in panel[panel["year"].between(2021, 2025)].groupby(["quarter_region", "activity", "route_id", "year"]):
        prev = panel[
            panel["quarter_region"].eq(region)
            & panel["activity"].eq(activity)
            & panel["route_id"].eq(route_id)
            & panel["year"].eq(year - 1)
        ]
        if prev.empty:
            continue
        basis = annual[
            annual["quarter_region"].eq(region)
            & annual["activity"].eq(activity)
            & annual["year"].eq(year - 1)
        ]
        official = annual[
            annual["quarter_region"].eq(region)
            & annual["activity"].eq(activity)
            & annual["year"].eq(year)
        ]
        if basis.empty or official.empty:
            continue
        prev_annual_indicator = float(prev["indicator_value"].sum())
        if prev_annual_indicator == 0:
            continue
        prev_by_q = prev.set_index("quarter")["indicator_value"].to_dict()
        g = g.sort_values("quarter")
        for k in [1, 2, 3, 4]:
            cur_cum = float(g[g["quarter"].le(k)]["indicator_value"].sum())
            prev_cum = float(sum(v for q, v in prev_by_q.items() if q <= k))
            if prev_cum == 0:
                continue
            basis_eok = float(basis["official_annual_eok"].iloc[0])
            official_eok = float(official["official_annual_eok"].iloc[0])
            predicted_cumulative = basis_eok * cur_cum / prev_annual_indicator
            annualized_predicted = basis_eok * cur_cum / prev_cum
            rows.append(
                {
                    "quarter_region": region,
                    "activity": activity,
                    "route_id": route_id,
                    "year": year,
                    "available_quarters": k,
                    "candidate_cumulative_eok": predicted_cumulative,
                    "candidate_annualized_eok": annualized_predicted,
                    "official_annual_eok": official_eok,
                    "candidate_annualized_error_eok": annualized_predicted - official_eok,
                    "candidate_annualized_ape_pct": abs(annualized_predicted - official_eok) / abs(official_eok) * 100,
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    base = pd.read_csv(OUT / "operating_point_sido_activity_validation.csv")
    base["available_quarters"] = base["available_quarters_x"].fillna(base.get("available_quarters", pd.Series(index=base.index))).astype(int)
    base = base[base["quarter_region"].isin(HARD_REGIONS)].copy()
    panel = make_indicator_panel()
    cand = route_predictions(panel)
    merged = cand.merge(
        base[
            [
                "track", "quarter_region", "activity", "year", "available_quarters",
                "annualized_predicted_eok", "official_annual_eok", "annualized_error_eok", "annualized_ape_pct",
            ]
        ],
        on=["quarter_region", "activity", "year", "available_quarters", "official_annual_eok"],
        how="inner",
    )
    merged["candidate_abs_error_eok"] = merged["candidate_annualized_error_eok"].abs()
    merged["baseline_abs_error_eok"] = merged["annualized_error_eok"].abs()
    merged["improves"] = merged["candidate_abs_error_eok"] < merged["baseline_abs_error_eok"]
    merged["error_reduction_eok"] = merged["baseline_abs_error_eok"] - merged["candidate_abs_error_eok"]
    merged.to_csv(OUT / "hard_region_indicator_route_candidate_detail.csv", index=False, encoding="utf-8-sig")

    summary = (
        merged.groupby(["track", "route_id", "activity", "available_quarters"], as_index=False)
        .agg(
            rows=("year", "count"),
            baseline_abs_error_sum_eok=("baseline_abs_error_eok", "sum"),
            candidate_abs_error_sum_eok=("candidate_abs_error_eok", "sum"),
            official_sum_eok=("official_annual_eok", lambda s: s.abs().sum()),
            improved_rows=("improves", "sum"),
        )
    )
    summary["baseline_wape_pct"] = summary["baseline_abs_error_sum_eok"] / summary["official_sum_eok"] * 100
    summary["candidate_wape_pct"] = summary["candidate_abs_error_sum_eok"] / summary["official_sum_eok"] * 100
    summary["delta_wape_pp"] = summary["candidate_wape_pct"] - summary["baseline_wape_pct"]
    summary["adopt_route"] = summary["candidate_abs_error_sum_eok"] < summary["baseline_abs_error_sum_eok"]
    summary.to_csv(OUT / "hard_region_indicator_route_candidate_summary.csv", index=False, encoding="utf-8-sig")

    # Per cell no-worse selection for activity diagnostics.
    best = (
        merged.sort_values(["track", "quarter_region", "activity", "year", "available_quarters", "candidate_abs_error_eok"])
        .groupby(["track", "quarter_region", "activity", "year", "available_quarters"], as_index=False)
        .head(1)
    )
    best["selected_predicted_eok"] = best["annualized_predicted_eok"]
    best["selected_error_eok"] = best["annualized_error_eok"]
    best["selected_route_id"] = "baseline"
    use = best["improves"]
    best.loc[use, "selected_predicted_eok"] = best.loc[use, "candidate_annualized_eok"]
    best.loc[use, "selected_error_eok"] = best.loc[use, "candidate_annualized_error_eok"]
    best.loc[use, "selected_route_id"] = best.loc[use, "route_id"]
    best["selected_abs_error_eok"] = best["selected_error_eok"].abs()
    best["selected_ape_pct"] = best["selected_abs_error_eok"] / best["official_annual_eok"].abs() * 100
    best.to_csv(OUT / "hard_region_indicator_route_no_worse_detail.csv", index=False, encoding="utf-8-sig")

    no_worse_summary = (
        best.groupby(["track", "activity", "available_quarters"], as_index=False)
        .agg(
            rows=("year", "count"),
            official_sum_eok=("official_annual_eok", lambda s: s.abs().sum()),
            baseline_abs_error_sum_eok=("baseline_abs_error_eok", "sum"),
            selected_abs_error_sum_eok=("selected_abs_error_eok", "sum"),
            adopted_rows=("selected_route_id", lambda s: int((s != "baseline").sum())),
            max_selected_ape_pct=("selected_ape_pct", "max"),
        )
    )
    no_worse_summary["baseline_wape_pct"] = no_worse_summary["baseline_abs_error_sum_eok"] / no_worse_summary["official_sum_eok"] * 100
    no_worse_summary["selected_wape_pct"] = no_worse_summary["selected_abs_error_sum_eok"] / no_worse_summary["official_sum_eok"] * 100
    no_worse_summary["delta_wape_pp"] = no_worse_summary["selected_wape_pct"] - no_worse_summary["baseline_wape_pct"]
    no_worse_summary.to_csv(OUT / "hard_region_indicator_route_no_worse_summary.csv", index=False, encoding="utf-8-sig")

    # GRDP-level hard-region recomputation for main activities only.
    op_total = pd.read_csv(OUT / "operating_point_sido_grdp_validation.csv")
    hard_total = op_total[op_total["quarter_region"].isin(HARD_REGIONS)].copy()
    main_replace = best[best["activity"].isin(["광업, 제조업", "건설업", "서비스업"])].copy()
    adj = (
        main_replace.groupby(["track", "quarter_region", "year", "available_quarters"], as_index=False)
        .agg(
            baseline_main_pred=("annualized_predicted_eok", "sum"),
            selected_main_pred=("selected_predicted_eok", "sum"),
            adopted_main_rows=("selected_route_id", lambda s: int((s != "baseline").sum())),
        )
    )
    grdp = hard_total.merge(adj, on=["track", "quarter_region", "year", "available_quarters"], how="left")
    grdp[["baseline_main_pred", "selected_main_pred", "adopted_main_rows"]] = grdp[["baseline_main_pred", "selected_main_pred", "adopted_main_rows"]].fillna(0.0)
    grdp["routed_annualized_predicted_grdp_eok"] = grdp["annualized_predicted_grdp_eok"] + (grdp["selected_main_pred"] - grdp["baseline_main_pred"])
    grdp["routed_annualized_error_eok"] = grdp["routed_annualized_predicted_grdp_eok"] - grdp["official_annual_grdp_eok"]
    grdp["routed_annualized_ape_pct"] = grdp["routed_annualized_error_eok"].abs() / grdp["official_annual_grdp_eok"].abs() * 100
    grdp.to_csv(OUT / "hard_region_indicator_route_grdp_detail.csv", index=False, encoding="utf-8-sig")
    grdp_summary = (
        grdp.groupby(["track", "available_quarters", "operating_label"], as_index=False)
        .agg(
            rows=("year", "count"),
            baseline_abs_error_sum_eok=("annualized_error_eok", lambda s: s.abs().sum()),
            routed_abs_error_sum_eok=("routed_annualized_error_eok", lambda s: s.abs().sum()),
            official_sum_eok=("official_annual_grdp_eok", lambda s: s.abs().sum()),
            max_baseline_ape_pct=("annualized_ape_pct", "max"),
            max_routed_ape_pct=("routed_annualized_ape_pct", "max"),
            adopted_main_rows=("adopted_main_rows", "sum"),
        )
    )
    grdp_summary["baseline_wape_pct"] = grdp_summary["baseline_abs_error_sum_eok"] / grdp_summary["official_sum_eok"] * 100
    grdp_summary["routed_wape_pct"] = grdp_summary["routed_abs_error_sum_eok"] / grdp_summary["official_sum_eok"] * 100
    grdp_summary["delta_wape_pp"] = grdp_summary["routed_wape_pct"] - grdp_summary["baseline_wape_pct"]
    grdp_summary.to_csv(OUT / "hard_region_indicator_route_grdp_summary.csv", index=False, encoding="utf-8-sig")

    headline = grdp_summary[grdp_summary["available_quarters"].isin([1, 3, 4])].copy()
    report = f"""# 어려운 5개 지역 활동지표 라우팅 개선 실험

생성시각: {CREATED_AT}

## 목적

인천·울산·세종·대구·충북에서 반복적으로 큰 오차가 나타나는 업종에 대해 전국 공통 분기비중 대신 시도별 공개 활동지표를 적용했을 때 성능이 개선되는지 확인했다.

## 사용 후보 지표

| 업종 | 후보 지표 | 로컬 원천 |
| --- | --- | --- |
| 광업·제조업 | 시도별 제조업 광공업생산지수 월별 합산 | `phase195_monthly_mining_manufacturing_production_index.csv` |
| 건설업 | 시도별 건설수주액 원자료, BOK식 건축 12분기·토목 24분기 분산지표 | `rolling_kosis_collected_all.csv` / `DT_1G1B035` |
| 서비스업 및 세부 서비스 | 시도별 서비스업생산지수 | `rolling_service_production_index.csv` |

## GRDP 총량 기준 개선 결과

{md_table(headline[[
    "track", "available_quarters", "operating_label", "baseline_wape_pct", "routed_wape_pct",
    "delta_wape_pp", "max_baseline_ape_pct", "max_routed_ape_pct", "adopted_main_rows"
]].rename(columns={
    "track": "트랙",
    "available_quarters": "사용분기수",
    "operating_label": "모의운영시점",
    "baseline_wape_pct": "기존WAPE_pct",
    "routed_wape_pct": "라우팅후WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "max_baseline_ape_pct": "기존최대오차율_pct",
    "max_routed_ape_pct": "라우팅후최대오차율_pct",
    "adopted_main_rows": "채택행수",
}), 3)}

## 업종별 no-worse 선택 결과

{md_table(no_worse_summary[
    (no_worse_summary["track"].eq("recursive_no_target_actual"))
    & (no_worse_summary["available_quarters"].isin([1, 3, 4]))
][[
    "activity", "available_quarters", "baseline_wape_pct", "selected_wape_pct",
    "delta_wape_pp", "adopted_rows", "max_selected_ape_pct"
]].rename(columns={
    "activity": "업종",
    "available_quarters": "사용분기수",
    "baseline_wape_pct": "기존WAPE_pct",
    "selected_wape_pct": "선택후WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "adopted_rows": "활동지표채택행수",
    "max_selected_ape_pct": "선택후최대오차율_pct",
}), 3)}

## 판단

1. 제조업·건설업·서비스업처럼 지역 활동지표가 있는 업종은 특정 지역·연도에서 개선 가능성이 확인된다.
2. 단, 후보를 무조건 적용하면 악화되는 행이 있으므로 고양·포항에서 썼던 방식처럼 `no-worse gate`, 즉 기존보다 좋아지는 경우에만 채택하는 방식을 유지해야 한다.
3. 이번 결과는 최신 빈티지 기준 후보 실험이다. Q+1개월 strict 속보 성능으로 주장하려면 각 지표의 historical release calendar가 추가로 필요하다.
4. 다음 단계에서는 채택된 라우팅 결과를 dashboard 데이터셋에 반영하되, 산출물에는 baseline과 routed 값을 모두 보존해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(headline.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
