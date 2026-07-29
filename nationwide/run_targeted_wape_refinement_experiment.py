#!/usr/bin/env python3
"""Targeted activity-routing experiment for 2021-2025 WAPE refinement.

Goal
----
Reduce >10% errors with as few routed industries as possible.  This script is
intentionally conservative: route/weight decisions for a target year use only
prior years in the same region × activity × operating point.  Target-year
actuals are used only after the decision, for evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = HERE / "targeted_wape_refinement_experiment.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

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

WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    title: str
    target_activities: tuple[str, ...]
    min_prior_years: int
    recent_guard: bool
    allowed_quarters: tuple[int, ...] | None = None


SCENARIOS = [
    Scenario(
        "transport_only_recent_guard",
        "운수·창고업 1개 산업군 / 최근연도 악화방지",
        ("운수 및 창고업",),
        2,
        True,
    ),
    Scenario(
        "transport_construction_recent_guard",
        "운수·창고업+건설업 2개 산업군 / 최근연도 악화방지",
        ("운수 및 창고업", "건설업"),
        2,
        True,
    ),
    Scenario(
        "transport_construction_lodging_recent_guard",
        "운수·창고업+건설업+숙박·음식점업 3개 산업군 / 최근연도 악화방지",
        ("운수 및 창고업", "건설업", "숙박 및 음식점업"),
        2,
        True,
    ),
    Scenario(
        "transport_construction_lodging_q12_only",
        "3개 산업군 / 1~2분기 조기점검 전용",
        ("운수 및 창고업", "건설업", "숙박 및 음식점업"),
        2,
        True,
        (1, 2),
    ),
]


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
    lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def wape(abs_error: pd.Series, actual: pd.Series) -> float:
    denom = actual.abs().sum()
    return float(abs_error.sum() / denom * 100) if denom else float("nan")


def load_base() -> pd.DataFrame:
    base = pd.read_csv(OUT / "operating_point_sido_activity_validation.csv")
    base["available_quarters"] = base["available_quarters_x"].where(
        base["available_quarters_x"].notna(),
        base.get("available_quarters", pd.Series(index=base.index)),
    ).astype(int)
    return base[
        [
            "track",
            "quarter_region",
            "activity",
            "year",
            "available_quarters",
            "operating_label",
            "annualized_predicted_eok",
            "official_annual_eok",
            "annualized_error_eok",
            "annualized_ape_pct",
        ]
    ].copy()


def annual_official() -> pd.DataFrame:
    src = ROOT / "data/processed/phase211_gyeonggi_2024_2025_grdp_extension/phase211_sido_quarterly_xlsx_long.csv"
    x = pd.read_csv(src)
    return (
        x[x["region"].isin(REGION_FULL.keys())]
        .groupby(["region", "activity", "year"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"region": "quarter_region", "official_value_eok": "official_annual_eok"})
    )


def make_indicator_panel() -> pd.DataFrame:
    panels: list[pd.DataFrame] = []
    full_to_short = {v: k for k, v in REGION_FULL.items()}

    # 시도별 제조업 생산지수: 광업·제조업 보조실험 후보로 보존한다.
    m = pd.read_csv(ROOT / "data/processed/phase195_monthly_mining_manufacturing_production_index.csv")
    m = m[(m["c1_nm"].isin(REGION_FULL.values())) & (m["c2_nm"].eq("제조업"))].copy()
    m["year"] = m["prd_de"].astype(str).str[:4].astype(int)
    m["quarter"] = ((m["prd_de"].astype(str).str[4:6].astype(int) - 1) // 3 + 1).astype(int)
    m["quarter_region"] = m["c1_nm"].map(full_to_short)
    mm = (
        m.groupby(["quarter_region", "year", "quarter"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "indicator_value"})
    )
    mm["activity"] = "광업, 제조업"
    mm["route_id"] = "regional_manufacturing_production_index"
    panels.append(mm)

    # 시도별 서비스업생산지수: 서비스 세부업종 시간경로 후보.
    svc = pd.read_csv(ROOT / "data/processed/rolling_service_production_index.csv", encoding="cp949")
    svc = svc[svc["c1_nm"].isin(REGION_FULL.values())].copy()
    svc["year"] = svc["prd_de"].astype(str).str[:4].astype(int)
    svc["quarter"] = svc["prd_de"].astype(str).str[4:6].astype(int)
    svc["quarter_region"] = svc["c1_nm"].map(full_to_short)
    for activity, codes in SERVICE_MAP.items():
        tmp = svc[svc["c2_id"].astype(str).isin(codes)].copy()
        q = (
            tmp.groupby(["quarter_region", "year", "quarter"], as_index=False)["value"]
            .mean()
            .rename(columns={"value": "indicator_value"})
        )
        q["activity"] = activity
        q["route_id"] = "regional_service_production_index_" + "_".join(codes)
        panels.append(q)

    # 건설수주: 원자료와 BOK식 장기 분산 후보.
    rk = pd.read_csv(ROOT / "data/processed/rolling_kosis_collected_all.csv", encoding="cp949")
    con = rk[(rk["tbl_id"].eq("DT_1G1B035")) & (rk["c1_nm"].isin(REGION_FULL.values()))].copy()
    con["year"] = con["prd_de"].astype(str).str[:4].astype(int)
    con["quarter"] = con["prd_de"].astype(str).str[4:6].astype(int)
    con["quarter_region"] = con["c1_nm"].map(full_to_short)
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
    for _, g in pivot.groupby("quarter_region"):
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
    panel = panel[panel["year"].between(2020, 2025)].copy()
    panel["indicator_value"] = pd.to_numeric(panel["indicator_value"], errors="coerce")
    return panel.dropna(subset=["indicator_value"])


def route_candidates(panel: pd.DataFrame) -> pd.DataFrame:
    annual = annual_official()
    rows = []
    for (region, activity, route_id, year), g in panel[panel["year"].between(2021, 2025)].groupby(
        ["quarter_region", "activity", "route_id", "year"]
    ):
        prev = panel[
            panel["quarter_region"].eq(region)
            & panel["activity"].eq(activity)
            & panel["route_id"].eq(route_id)
            & panel["year"].eq(year - 1)
        ]
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
        if prev.empty or basis.empty or official.empty:
            continue
        prev_by_q = prev.set_index("quarter")["indicator_value"].to_dict()
        basis_eok = float(basis["official_annual_eok"].iloc[0])
        official_eok = float(official["official_annual_eok"].iloc[0])
        for k in [1, 2, 3, 4]:
            prev_cum = float(sum(v for q, v in prev_by_q.items() if q <= k))
            if prev_cum == 0:
                continue
            cur_cum = float(g[g["quarter"].le(k)]["indicator_value"].sum())
            pred = basis_eok * cur_cum / prev_cum
            rows.append(
                {
                    "quarter_region": region,
                    "activity": activity,
                    "route_id": route_id,
                    "year": int(year),
                    "available_quarters": int(k),
                    "candidate_annualized_eok": pred,
                    "official_annual_eok": official_eok,
                    "candidate_error_eok": pred - official_eok,
                }
            )
    return pd.DataFrame(rows)


def merge_candidate_base(base: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    merged = cand.merge(
        base,
        on=["quarter_region", "activity", "year", "available_quarters", "official_annual_eok"],
        how="inner",
    )
    merged["baseline_error_eok"] = merged["annualized_error_eok"]
    for w in WEIGHTS:
        merged[f"weighted_error_{w}"] = (1 - w) * merged["baseline_error_eok"] + w * merged["candidate_error_eok"]
        merged[f"weighted_abs_error_{w}"] = merged[f"weighted_error_{w}"].abs()
    return merged


def select_for_scenario(base: pd.DataFrame, merged: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    selected_rows = []
    target_set = set(scenario.target_activities)
    index_cols = ["track", "quarter_region", "activity", "available_quarters", "year"]

    route_groups = {
        key: g.copy()
        for key, g in merged.groupby(["track", "quarter_region", "activity", "available_quarters", "route_id"], dropna=False)
    }

    for _, b in base.iterrows():
        activity = str(b["activity"])
        k = int(b["available_quarters"])
        use_activity = activity in target_set and (scenario.allowed_quarters is None or k in scenario.allowed_quarters)
        chosen_route = "baseline"
        chosen_weight = 0.0
        chosen_basis = "baseline_not_target_or_no_prior"
        chosen_error = float(b["annualized_error_eok"])

        if use_activity:
            candidate_scores = []
            # Score each candidate route/weight from prior years only.
            for (track, region, act, kk, route_id), g in route_groups.items():
                if (
                    track != b["track"]
                    or region != b["quarter_region"]
                    or act != b["activity"]
                    or int(kk) != k
                ):
                    continue
                prior = g[g["year"].lt(int(b["year"]))].copy()
                current = g[g["year"].eq(int(b["year"]))].copy()
                if len(prior) < scenario.min_prior_years or current.empty:
                    continue
                baseline_prior = float(prior["weighted_abs_error_0.0"].sum())
                for w in WEIGHTS[1:]:
                    candidate_prior = float(prior[f"weighted_abs_error_{w}"].sum())
                    if candidate_prior >= baseline_prior:
                        continue
                    if scenario.recent_guard:
                        recent = prior.sort_values("year").tail(2)
                        if not (recent[f"weighted_abs_error_{w}"] <= recent["weighted_abs_error_0.0"]).all():
                            continue
                    improvement = baseline_prior - candidate_prior
                    candidate_scores.append((improvement, -candidate_prior, str(route_id), float(w), current.iloc[0]))
            if candidate_scores:
                candidate_scores.sort(reverse=True)
                improvement, _, chosen_route, chosen_weight, cur = candidate_scores[0]
                chosen_error = float((1 - chosen_weight) * cur["baseline_error_eok"] + chosen_weight * cur["candidate_error_eok"])
                chosen_basis = f"prior_only_improvement_{improvement:.3f}_eok_recent_guard_{scenario.recent_guard}"

        out = b.to_dict()
        out.update(
            {
                "scenario_id": scenario.scenario_id,
                "scenario_title": scenario.title,
                "selected_route_id": chosen_route,
                "selected_weight": chosen_weight,
                "selected_basis": chosen_basis,
                "selected_error_eok": chosen_error,
                "selected_abs_error_eok": abs(chosen_error),
                "selected_ape_pct": abs(chosen_error) / abs(float(b["official_annual_eok"])) * 100
                if float(b["official_annual_eok"]) != 0
                else pd.NA,
                "baseline_abs_error_eok": abs(float(b["annualized_error_eok"])),
            }
        )
        selected_rows.append(out)

    selected = pd.DataFrame(selected_rows)
    # Ensure there are no accidental duplicates against the evaluation grain.
    duplicates = selected.duplicated(index_cols + ["scenario_id"]).sum()
    if duplicates:
        raise SystemExit(f"unexpected duplicate selected rows: {duplicates}")
    return selected


def summarize(selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    activity = (
        selected.groupby(["scenario_id", "scenario_title", "track", "activity", "available_quarters", "operating_label"], as_index=False)
        .agg(
            rows=("year", "count"),
            official_sum_eok=("official_annual_eok", lambda s: s.abs().sum()),
            baseline_abs_error_sum_eok=("baseline_abs_error_eok", "sum"),
            selected_abs_error_sum_eok=("selected_abs_error_eok", "sum"),
            baseline_over10_rows=("annualized_ape_pct", lambda s: int((s > 10).sum())),
            selected_over10_rows=("selected_ape_pct", lambda s: int((s > 10).sum())),
            baseline_over20_rows=("annualized_ape_pct", lambda s: int((s > 20).sum())),
            selected_over20_rows=("selected_ape_pct", lambda s: int((s > 20).sum())),
            baseline_max_ape_pct=("annualized_ape_pct", "max"),
            selected_max_ape_pct=("selected_ape_pct", "max"),
            adopted_rows=("selected_weight", lambda s: int((s > 0).sum())),
        )
    )
    activity["baseline_wape_pct"] = activity["baseline_abs_error_sum_eok"] / activity["official_sum_eok"] * 100
    activity["selected_wape_pct"] = activity["selected_abs_error_sum_eok"] / activity["official_sum_eok"] * 100
    activity["delta_wape_pp"] = activity["selected_wape_pct"] - activity["baseline_wape_pct"]
    activity["delta_over10_rows"] = activity["selected_over10_rows"] - activity["baseline_over10_rows"]

    scenario = (
        selected.groupby(["scenario_id", "scenario_title", "track", "available_quarters", "operating_label"], as_index=False)
        .agg(
            rows=("year", "count"),
            official_sum_eok=("official_annual_eok", lambda s: s.abs().sum()),
            baseline_abs_error_sum_eok=("baseline_abs_error_eok", "sum"),
            selected_abs_error_sum_eok=("selected_abs_error_eok", "sum"),
            baseline_over10_rows=("annualized_ape_pct", lambda s: int((s > 10).sum())),
            selected_over10_rows=("selected_ape_pct", lambda s: int((s > 10).sum())),
            adopted_rows=("selected_weight", lambda s: int((s > 0).sum())),
        )
    )
    scenario["baseline_wape_pct"] = scenario["baseline_abs_error_sum_eok"] / scenario["official_sum_eok"] * 100
    scenario["selected_wape_pct"] = scenario["selected_abs_error_sum_eok"] / scenario["official_sum_eok"] * 100
    scenario["delta_wape_pp"] = scenario["selected_wape_pct"] - scenario["baseline_wape_pct"]
    scenario["delta_over10_rows"] = scenario["selected_over10_rows"] - scenario["baseline_over10_rows"]

    route = (
        selected[selected["selected_weight"].gt(0)]
        .groupby(["scenario_id", "track", "activity", "selected_route_id", "selected_weight"], as_index=False)
        .agg(rows=("year", "count"), regions=("quarter_region", "nunique"))
        .sort_values(["scenario_id", "rows"], ascending=[True, False])
    )
    return activity, scenario, route


def sigungu_error_context() -> tuple[pd.DataFrame, pd.DataFrame]:
    sig_path = OUT / "annual_sigungu_activity_error_audit.csv"
    if not sig_path.exists():
        return pd.DataFrame(), pd.DataFrame()
    sig = pd.read_csv(sig_path)
    activity_col = "activity_group" if "activity_group" in sig.columns else "activity"
    gt = sig[sig["ape_pct"].gt(10)].copy()
    roll = (
        gt.groupby(activity_col, as_index=False)
        .agg(
            over10_rows=("ape_pct", "count"),
            max_ape_pct=("ape_pct", "max"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
        )
        .sort_values(["over10_rows", "abs_error_sum_eok"], ascending=False)
    )
    roll = roll.rename(columns={activity_col: "activity_group"})
    large = sig[sig["actual_eok"].abs().ge(1000)].copy()
    large_gt = large[large["ape_pct"].gt(10)]
    large_roll = (
        large_gt.groupby(activity_col, as_index=False)
        .agg(
            over10_rows=("ape_pct", "count"),
            max_ape_pct=("ape_pct", "max"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
        )
        .sort_values(["over10_rows", "abs_error_sum_eok"], ascending=False)
    )
    large_roll = large_roll.rename(columns={activity_col: "activity_group"})
    return roll, large_roll


def write_report(
    activity_summary: pd.DataFrame,
    scenario_summary: pd.DataFrame,
    route_summary: pd.DataFrame,
    sigungu_roll: pd.DataFrame,
    sigungu_large_roll: pd.DataFrame,
) -> None:
    strict_activity = activity_summary[activity_summary["track"].eq("recursive_no_target_actual")].copy()
    q1_focus = strict_activity[
        strict_activity["available_quarters"].eq(1)
        & strict_activity["activity"].isin(["운수 및 창고업", "건설업", "숙박 및 음식점업", "정보통신업", "광업, 제조업"])
    ].sort_values(["scenario_id", "selected_wape_pct"])
    transport = strict_activity[
        strict_activity["activity"].eq("운수 및 창고업")
        & strict_activity["available_quarters"].eq(1)
    ].sort_values("selected_wape_pct")
    scenario_q1 = scenario_summary[
        scenario_summary["track"].eq("recursive_no_target_actual")
        & scenario_summary["available_quarters"].eq(1)
    ].sort_values("selected_over10_rows")
    route_head = route_summary[route_summary["track"].eq("recursive_no_target_actual")].head(20)

    report = f"""# 전국 목표산업 WAPE 개선 실험

생성시각: {CREATED_AT}

## 목적

2021~2025년 전국 17개 시도 검증에서 10% 초과 오차가 반복되는 셀을 줄이되, 특화 산업군 수를 최소화한다. 목표연도 actual을 보고 후보를 고르는 방식은 사용하지 않고, 각 목표연도 이전 자료만으로 지표와 혼합가중치를 선택했다.

## 사용 후보

| 업종 | 후보자료 | 사용방식 |
| --- | --- | --- |
| 운수 및 창고업 | 시도별 서비스업생산지수 H | 기존 추정값과 25/50/75/100% 혼합 |
| 건설업 | 시도별 건설수주액, 건축 12분기·토목 24분기 분산지표 | 기존 추정값과 혼합 |
| 숙박 및 음식점업 | 시도별 서비스업생산지수 I | 기존 추정값과 혼합 |
| 광업·제조업 | 시도별 제조업 생산지수 | 이번 채택 시나리오에는 넣지 않고 보조 후보로만 보존 |

## 누수 방지 규칙

| 항목 | 규칙 |
| --- | --- |
| 목표연도 actual | 선택에 사용 금지, 사후 검증에만 사용 |
| 선택 단위 | 트랙×시도×업종×운영시점×후보지표 |
| 혼합가중치 | 0/25/50/75/100% |
| 기본 채택조건 | 과거연도 누적 절대오차가 기존방식보다 작을 것 |
| 보수 게이트 | 최근 2개 과거연도에서 모두 기존방식보다 악화되지 않을 것 |
| 최소 과거연도 | 2개년 |

## 엄격 속보형 Q1 핵심 결과

{md_table(q1_focus[[
    "scenario_title", "activity", "baseline_wape_pct", "selected_wape_pct",
    "delta_wape_pp", "baseline_over10_rows", "selected_over10_rows",
    "selected_max_ape_pct", "adopted_rows"
]].rename(columns={
    "scenario_title": "시나리오",
    "activity": "업종",
    "baseline_wape_pct": "기존WAPE_pct",
    "selected_wape_pct": "개선WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_rows": "기존10pct초과",
    "selected_over10_rows": "개선10pct초과",
    "selected_max_ape_pct": "개선최대오차율_pct",
    "adopted_rows": "채택행수",
}), 3)}

## 운수·창고업 최소산업군 판정

{md_table(transport[[
    "scenario_title", "baseline_wape_pct", "selected_wape_pct",
    "delta_wape_pp", "baseline_over10_rows", "selected_over10_rows",
    "baseline_over20_rows", "selected_over20_rows", "adopted_rows"
]].rename(columns={
    "scenario_title": "시나리오",
    "baseline_wape_pct": "기존WAPE_pct",
    "selected_wape_pct": "개선WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_rows": "기존10pct초과",
    "selected_over10_rows": "개선10pct초과",
    "baseline_over20_rows": "기존20pct초과",
    "selected_over20_rows": "개선20pct초과",
    "adopted_rows": "채택행수",
}), 3)}

## 전체 시도×업종 셀 영향: Q1

{md_table(scenario_q1[[
    "scenario_title", "baseline_wape_pct", "selected_wape_pct",
    "delta_wape_pp", "baseline_over10_rows", "selected_over10_rows",
    "delta_over10_rows", "adopted_rows"
]].rename(columns={
    "scenario_title": "시나리오",
    "baseline_wape_pct": "전체기존WAPE_pct",
    "selected_wape_pct": "전체개선WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_rows": "기존10pct초과셀",
    "selected_over10_rows": "개선10pct초과셀",
    "delta_over10_rows": "10pct초과변화",
    "adopted_rows": "채택행수",
}), 3)}

## 채택된 지표·가중치

{md_table(route_head.rename(columns={
    "scenario_id": "시나리오ID",
    "track": "트랙",
    "activity": "업종",
    "selected_route_id": "선택지표",
    "selected_weight": "혼합가중치",
    "rows": "채택행",
    "regions": "지역수",
}), 3)}

## 시군구×업종 잔여오차 맥락

시군구 연간 actual 검증은 공간 배분 검증이다. 이번 시도 단위 분기 활동지표 라우팅은 시간경로 개선에는 유효하지만, 시군구×업종 연간오차를 직접 줄이지 않는다. 시군구 성능 개선에는 시군구별 사업체·공장·전력·항만·건축허가·인허가 같은 공간 활동자료가 필요하다.

### 전체 시군구×업종 10% 초과 상위

{md_table(sigungu_roll.head(12).rename(columns={
    "activity_group": "업종",
    "over10_rows": "10pct초과행",
    "max_ape_pct": "최대오차율_pct",
    "abs_error_sum_eok": "절대오차합_억원",
}), 3)}

### actual 1,000억원 이상 셀만

{md_table(sigungu_large_roll.head(12).rename(columns={
    "activity_group": "업종",
    "over10_rows": "10pct초과행",
    "max_ape_pct": "최대오차율_pct",
    "abs_error_sum_eok": "절대오차합_억원",
}), 3)}

## 결론

1. 최소 산업군 목표만 보면 `운수 및 창고업` 1개 산업군에 보수적 혼합 게이트를 적용하는 것이 가장 작고 안전한 개선이다.
2. 엄격 속보형 Q1 운수·창고업은 기존 WAPE가 10%를 넘었으나, 최근연도 악화방지 혼합 규칙으로 10% 이하 진입 여부를 확인할 수 있다.
3. 건설업은 전체 WAPE는 이미 10% 이하이나 10% 초과 셀이 많아, 정책 진단용으로는 2순위 특화 대상이다. 다만 최대오차율이 남으므로 건설수주 단독이 아니라 착공·사용승인 자료가 추가되어야 한다.
4. 숙박·음식점업은 이번 전국 자동채택에서 채택하지 않는 편이 낫다. 서비스업생산지수 I만으로는 WAPE가 소폭 악화되고 최대오차율이 커져, 관광·방문객 자료가 확보된 지역에 한정한 별도 실험이 필요하다.
5. 따라서 현재 운영 후보는 `운수 및 창고업 1개 산업군`이고, 확장 후보는 `운수 및 창고업+건설업 2개 산업군`이다. `숙박 및 음식점업`은 보류한다.
6. 시군구×업종 10% 초과 셀은 이번 시도 단위 시간지표만으로 해결할 수 없고, 공간 배분용 직접자료 수집이 별도 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")


def main() -> int:
    base = load_base()
    cand = route_candidates(make_indicator_panel())
    merged = merge_candidate_base(base, cand)
    merged.to_csv(OUT / "targeted_wape_refinement_candidate_detail.csv", index=False, encoding="utf-8-sig")

    selected = pd.concat([select_for_scenario(base, merged, s) for s in SCENARIOS], ignore_index=True)
    selected.to_csv(OUT / "targeted_wape_refinement_selected_detail.csv", index=False, encoding="utf-8-sig")

    activity_summary, scenario_summary, route_summary = summarize(selected)
    activity_summary.to_csv(OUT / "targeted_wape_refinement_activity_summary.csv", index=False, encoding="utf-8-sig")
    scenario_summary.to_csv(OUT / "targeted_wape_refinement_scenario_summary.csv", index=False, encoding="utf-8-sig")
    route_summary.to_csv(OUT / "targeted_wape_refinement_route_summary.csv", index=False, encoding="utf-8-sig")

    sigungu_roll, sigungu_large_roll = sigungu_error_context()
    sigungu_roll.to_csv(OUT / "targeted_wape_refinement_sigungu_over10_context.csv", index=False, encoding="utf-8-sig")
    sigungu_large_roll.to_csv(
        OUT / "targeted_wape_refinement_sigungu_large_over10_context.csv",
        index=False,
        encoding="utf-8-sig",
    )

    write_report(activity_summary, scenario_summary, route_summary, sigungu_roll, sigungu_large_roll)

    strict = activity_summary[
        activity_summary["track"].eq("recursive_no_target_actual")
        & activity_summary["available_quarters"].eq(1)
        & activity_summary["activity"].eq("운수 및 창고업")
    ].sort_values("selected_wape_pct")
    print(strict[["scenario_id", "baseline_wape_pct", "selected_wape_pct", "baseline_over10_rows", "selected_over10_rows", "adopted_rows"]].to_string(index=False))
    print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
