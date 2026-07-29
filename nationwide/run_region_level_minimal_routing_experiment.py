#!/usr/bin/env python3
"""Region-level minimal activity routing experiment.

The success criterion is not national aggregate WAPE.  It is the number of
`sido x activity` five-year cells whose WAPE remains above 10%.

This experiment uses only public/direct activity indicators already available
in the repository:

* regional service production index for service sub-industries
* regional construction orders with a BOK-style 12/24-quarter stock transform
* regional mining/manufacturing production index

It then asks: how many activity groups must be routed away from the common
baseline before regional cells fall below the 10% WAPE threshold?
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = HERE / "region_level_minimal_routing_experiment.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
TRACK = "recursive_no_target_actual"

REGION_FULL = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종시",
    "경기도": "경기도",
    "강원": "강원도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전라북도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주도",
}
FULL_REGION = {v: k for k, v in REGION_FULL.items()}
FULL_REGION.update(
    {
        "세종특별자치시": "세종",
        "강원특별자치도": "강원",
        "전북특별자치도": "전북",
        "제주특별자치도": "제주",
    }
)

SERVICE_MAP = {
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
    "서비스업": ["T"],
}

PREFERRED_ROUTE = {
    "건설업": "regional_construction_orders_bok_12_24q",
    "운수 및 창고업": "regional_service_production_index_H",
    "숙박 및 음식점업": "regional_service_production_index_I",
    "정보통신업": "regional_service_production_index_J",
    "광업, 제조업": "regional_manufacturing_production_index",
}


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


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


def load_baseline() -> pd.DataFrame:
    b = pd.read_csv(OUT / "operating_point_sido_activity_validation.csv")
    b["available_quarters"] = b["available_quarters_x"].fillna(b["available_quarters"]).astype(int)
    b = b[b["track"].eq(TRACK)].copy()
    b = b.rename(
        columns={
            "annualized_predicted_eok": "baseline_predicted_eok",
            "annualized_error_eok": "baseline_error_eok",
            "annualized_ape_pct": "baseline_ape_pct",
        }
    )
    b["baseline_abs_error_eok"] = b["baseline_error_eok"].abs()
    return b[
        [
            "track",
            "quarter_region",
            "activity",
            "year",
            "available_quarters",
            "baseline_predicted_eok",
            "official_annual_eok",
            "baseline_error_eok",
            "baseline_abs_error_eok",
            "baseline_ape_pct",
        ]
    ]


def load_annual_official() -> pd.DataFrame:
    """Annual official controls for route prediction basis and validation.

    Baseline validation contains 2021-2025 target-year official annual values.
    Candidate year 2021 also needs 2020 as the previous-year basis.  The
    quarterly GRDP XLSX-derived long table stores quarter values, so annual
    values are constructed by summing Q1-Q4 by region and activity.
    """
    base = (
        load_baseline()[["quarter_region", "activity", "year", "official_annual_eok"]]
        .drop_duplicates()
        .copy()
    )
    xlsx_path = ROOT / "data/processed/phase211_gyeonggi_2024_2025_grdp_extension/phase211_sido_quarterly_xlsx_long.csv"
    if xlsx_path.exists():
        q = pd.read_csv(xlsx_path)
        q = q[q["quarter"].isin([1, 2, 3, 4])].copy()
        q = q[~q["region"].eq("전국")].copy()
        q = (
            q.groupby(["region", "activity", "year"], as_index=False)["official_value_eok"]
            .sum()
            .rename(columns={"region": "quarter_region", "official_value_eok": "official_annual_eok"})
        )
        q = q[q["activity"].isin(base["activity"].unique())].copy()
        base = pd.concat([q, base], ignore_index=True)
    base = (
        base.sort_values(["quarter_region", "activity", "year"])
        .drop_duplicates(["quarter_region", "activity", "year"], keep="last")
        .reset_index(drop=True)
    )
    return base


def build_indicator_panel() -> pd.DataFrame:
    panels: list[pd.DataFrame] = []

    m = read_csv_any(ROOT / "data/processed/phase195_monthly_mining_manufacturing_production_index.csv")
    m = m[m["c2_nm"].eq("제조업")].copy()
    m["year"] = m["prd_de"].astype(str).str[:4].astype(int)
    m["month"] = m["prd_de"].astype(str).str[4:6].astype(int)
    m["quarter"] = ((m["month"] - 1) // 3 + 1).astype(int)
    m["quarter_region"] = m["c1_nm"].map(FULL_REGION)
    q = (
        m.dropna(subset=["quarter_region"])
        .groupby(["quarter_region", "year", "quarter"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "indicator_value"})
    )
    q["activity"] = "광업, 제조업"
    q["route_id"] = "regional_manufacturing_production_index"
    panels.append(q)

    svc = read_csv_any(ROOT / "data/processed/rolling_service_production_index.csv")
    svc["year"] = svc["prd_de"].astype(str).str[:4].astype(int)
    svc["quarter"] = svc["prd_de"].astype(str).str[4:6].astype(int)
    svc["quarter_region"] = svc["c1_nm"].map(FULL_REGION)
    svc = svc.dropna(subset=["quarter_region"]).copy()
    for activity, codes in SERVICE_MAP.items():
        tmp = svc[svc["c2_id"].astype(str).isin(codes)].copy()
        if tmp.empty:
            continue
        q = (
            tmp.groupby(["quarter_region", "year", "quarter"], as_index=False)["value"]
            .mean()
            .rename(columns={"value": "indicator_value"})
        )
        q["activity"] = activity
        q["route_id"] = "regional_service_production_index_" + "_".join(codes)
        panels.append(q)

    rk = read_csv_any(ROOT / "data/processed/rolling_kosis_collected_all.csv")
    con = rk[(rk["tbl_id"].eq("DT_1G1B035"))].copy()
    con["year"] = con["prd_de"].astype(str).str[:4].astype(int)
    con["quarter"] = con["prd_de"].astype(str).str[4:6].astype(int)
    con["quarter_region"] = con["c1_nm"].map(FULL_REGION)
    con = con.dropna(subset=["quarter_region"]).copy()

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
    return panel.dropna(subset=["indicator_value", "quarter_region", "activity", "route_id"])


def route_predictions(panel: pd.DataFrame, annual: pd.DataFrame) -> pd.DataFrame:
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
        prev_by_q = prev.groupby("quarter")["indicator_value"].sum().to_dict()
        g_by_q = g.groupby("quarter")["indicator_value"].sum().to_dict()
        basis_eok = float(basis["official_annual_eok"].iloc[0])
        official_eok = float(official["official_annual_eok"].iloc[0])
        for k in [1, 2, 3, 4]:
            prev_cum = sum(v for q, v in prev_by_q.items() if q <= k)
            cur_cum = sum(v for q, v in g_by_q.items() if q <= k)
            if not prev_cum:
                continue
            pred = basis_eok * cur_cum / prev_cum
            err = pred - official_eok
            rows.append(
                {
                    "quarter_region": region,
                    "activity": activity,
                    "route_id": route_id,
                    "year": int(year),
                    "available_quarters": int(k),
                    "candidate_predicted_eok": pred,
                    "candidate_error_eok": err,
                    "candidate_abs_error_eok": abs(err),
                    "official_annual_eok": official_eok,
                    "candidate_ape_pct": abs(err) / abs(official_eok) * 100 if official_eok else pd.NA,
                }
            )
    return pd.DataFrame(rows)


def apply_routes(base: pd.DataFrame, candidates: pd.DataFrame, routed_activities: set[str]) -> pd.DataFrame:
    x = base.copy()
    x["selected_predicted_eok"] = x["baseline_predicted_eok"]
    x["selected_error_eok"] = x["baseline_error_eok"]
    x["selected_route_id"] = "baseline"

    chosen = candidates[candidates["activity"].isin(routed_activities)].copy()
    if chosen.empty:
        x["selected_abs_error_eok"] = x["selected_error_eok"].abs()
        x["selected_ape_pct"] = x["selected_error_eok"].abs() / x["official_annual_eok"].abs() * 100
        return x
    preferred = pd.DataFrame(
        [{"activity": k, "preferred_route_id": v} for k, v in PREFERRED_ROUTE.items() if k in routed_activities]
    )
    chosen = chosen.merge(preferred, on="activity", how="left")
    chosen = chosen[chosen["route_id"].eq(chosen["preferred_route_id"])].copy()
    idx_cols = ["quarter_region", "activity", "year", "available_quarters"]
    rep = chosen.set_index(idx_cols)
    base_idx = x.set_index(idx_cols).index
    mask = base_idx.isin(rep.index)
    x.loc[mask, "selected_predicted_eok"] = [rep.loc[key, "candidate_predicted_eok"] for key in base_idx[mask]]
    x.loc[mask, "selected_error_eok"] = [rep.loc[key, "candidate_error_eok"] for key in base_idx[mask]]
    x.loc[mask, "selected_route_id"] = [rep.loc[key, "route_id"] for key in base_idx[mask]]
    x["selected_abs_error_eok"] = x["selected_error_eok"].abs()
    x["selected_ape_pct"] = x["selected_error_eok"].abs() / x["official_annual_eok"].abs() * 100
    return x


def summarize_region_activity(x: pd.DataFrame, value_prefix: str = "selected") -> pd.DataFrame:
    err_col = f"{value_prefix}_abs_error_eok"
    ape_col = f"{value_prefix}_ape_pct"
    rows = []
    for (region, activity, k), g in x.groupby(["quarter_region", "activity", "available_quarters"]):
        rows.append(
            {
                "quarter_region": region,
                "activity": activity,
                "available_quarters": int(k),
                "years": g["year"].nunique(),
                "official_sum_eok": g["official_annual_eok"].abs().sum(),
                "abs_error_sum_eok": g[err_col].sum(),
                "wape_pct": g[err_col].sum() / g["official_annual_eok"].abs().sum() * 100,
                "max_ape_pct": g[ape_col].max(),
                "over10_years": int((g[ape_col] > 10).sum()),
                "routed_years": int((g["selected_route_id"] != "baseline").sum()) if "selected_route_id" in g else 0,
            }
        )
    return pd.DataFrame(rows)



def summarize_by_year_split(selected: pd.DataFrame, scenario: str) -> pd.DataFrame:
    rows = []
    for split_name, years in {"dev_2021_2023": [2021, 2022, 2023], "holdout_2024_2025": [2024, 2025], "all_2021_2025": [2021, 2022, 2023, 2024, 2025]}.items():
        z = selected[selected["year"].isin(years)].copy()
        if z.empty:
            continue
        for k, kk in z.groupby("available_quarters"):
            regional = summarize_region_activity(kk)
            rows.append(
                {
                    "scenario": scenario,
                    "split": split_name,
                    "available_quarters": int(k),
                    "region_activity_cells": len(regional),
                    "over10_cells": int((regional["wape_pct"] > 10).sum()),
                    "over10_official_sum_eok": regional.loc[regional["wape_pct"] > 10, "official_sum_eok"].sum(),
                    "overall_region_activity_wape_pct": kk["selected_abs_error_eok"].sum() / kk["official_annual_eok"].abs().sum() * 100,
                }
            )
    return pd.DataFrame(rows)


def select_cell_routes_from_dev(base: pd.DataFrame, candidates: pd.DataFrame, k: int = 1) -> pd.DataFrame:
    """Select region-activity routes using 2021-2023 only, then evaluate holdout.

    This prevents choosing a route because it accidentally matches 2024-2025 actuals.
    A route is accepted only when it improves dev WAPE by at least 1 percentage
    point and the dev candidate WAPE is <= 10%; otherwise baseline remains.
    """
    rows = []
    dev_years = [2021, 2022, 2023]
    for (region, activity, route_id), g in candidates[candidates["available_quarters"].eq(k)].groupby(["quarter_region", "activity", "route_id"]):
        gd = g[g["year"].isin(dev_years)].copy()
        if gd["year"].nunique() < 2:
            continue
        official = gd["official_annual_eok"].abs().sum()
        if not official:
            continue
        base_wape = gd["baseline_abs_error_eok"].sum() / official * 100
        cand_wape = gd["candidate_abs_error_eok"].sum() / official * 100
        improvement = base_wape - cand_wape
        accept = (improvement >= 1.0) and (cand_wape <= 10.0)
        rows.append(
            {
                "quarter_region": region,
                "activity": activity,
                "route_id": route_id,
                "available_quarters": int(k),
                "dev_years": "2021-2023",
                "dev_baseline_wape_pct": base_wape,
                "dev_candidate_wape_pct": cand_wape,
                "dev_improvement_pctp": improvement,
                "accepted": bool(accept),
            }
        )
    return pd.DataFrame(rows)


def apply_cell_route_table(base: pd.DataFrame, candidates: pd.DataFrame, selected_routes: pd.DataFrame, scenario: str) -> pd.DataFrame:
    x = base.copy()
    x["selected_predicted_eok"] = x["baseline_predicted_eok"]
    x["selected_error_eok"] = x["baseline_error_eok"]
    x["selected_route_id"] = "baseline"
    accepted = selected_routes[selected_routes["accepted"]].copy()
    if accepted.empty:
        x["selected_abs_error_eok"] = x["selected_error_eok"].abs()
        x["selected_ape_pct"] = x["selected_error_eok"].abs() / x["official_annual_eok"].abs() * 100
        x["scenario"] = scenario
        return x
    idx_cols = ["quarter_region", "activity", "available_quarters"]
    c = candidates.merge(accepted[idx_cols + ["route_id"]], on=idx_cols + ["route_id"], how="inner")
    rep_cols = ["quarter_region", "activity", "year", "available_quarters"]
    rep = c.set_index(rep_cols)
    base_idx = x.set_index(rep_cols).index
    mask = base_idx.isin(rep.index)
    x.loc[mask, "selected_predicted_eok"] = [rep.loc[key, "candidate_predicted_eok"] for key in base_idx[mask]]
    x.loc[mask, "selected_error_eok"] = [rep.loc[key, "candidate_error_eok"] for key in base_idx[mask]]
    x.loc[mask, "selected_route_id"] = [rep.loc[key, "route_id"] for key in base_idx[mask]]
    x["selected_abs_error_eok"] = x["selected_error_eok"].abs()
    x["selected_ape_pct"] = x["selected_error_eok"].abs() / x["official_annual_eok"].abs() * 100
    x["scenario"] = scenario
    return x

def scenario_summary(base: pd.DataFrame, candidates: pd.DataFrame, routed_activities: set[str], scenario: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected = apply_routes(base, candidates, routed_activities)
    regional = summarize_region_activity(selected)
    scenario_rows = []
    for k, g in regional.groupby("available_quarters"):
        scenario_rows.append(
            {
                "scenario": scenario,
                "available_quarters": int(k),
                "routed_activity_count": len(routed_activities),
                "routed_activities": ", ".join(sorted(routed_activities)) if routed_activities else "none",
                "region_activity_cells": len(g),
                "over10_cells": int((g["wape_pct"] > 10).sum()),
                "over10_official_sum_eok": g.loc[g["wape_pct"] > 10, "official_sum_eok"].sum(),
                "overall_region_activity_wape_pct": selected[selected["available_quarters"].eq(k)]["selected_abs_error_eok"].sum()
                / selected[selected["available_quarters"].eq(k)]["official_annual_eok"].abs().sum()
                * 100,
            }
        )
    return pd.DataFrame(scenario_rows), regional.assign(scenario=scenario)


def greedy_minimal_routes(base: pd.DataFrame, candidates: pd.DataFrame, k: int = 1) -> pd.DataFrame:
    activities = [a for a in PREFERRED_ROUTE if a in set(candidates["activity"])]
    selected: set[str] = set()
    rows = []
    current_summary, _ = scenario_summary(base, candidates, selected, "baseline")
    current_over10 = int(current_summary[current_summary["available_quarters"].eq(k)]["over10_cells"].iloc[0])
    for step in range(1, len(activities) + 1):
        options = []
        for activity in activities:
            if activity in selected:
                continue
            ss, _ = scenario_summary(base, candidates, selected | {activity}, f"try_{activity}")
            row = ss[ss["available_quarters"].eq(k)].iloc[0].to_dict()
            row["candidate_activity"] = activity
            row["over10_reduction"] = current_over10 - int(row["over10_cells"])
            options.append(row)
        if not options:
            break
        opt = pd.DataFrame(options).sort_values(
            ["over10_reduction", "overall_region_activity_wape_pct"],
            ascending=[False, True],
        ).iloc[0]
        if int(opt["over10_reduction"]) <= 0:
            break
        selected.add(str(opt["candidate_activity"]))
        current_over10 = int(opt["over10_cells"])
        rows.append(
            {
                "step": step,
                "added_activity": opt["candidate_activity"],
                "selected_activities": ", ".join(sorted(selected)),
                "over10_cells": current_over10,
                "over10_reduction": int(opt["over10_reduction"]),
                "overall_region_activity_wape_pct": float(opt["overall_region_activity_wape_pct"]),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    base = load_baseline()
    base["selected_abs_error_eok"] = base["baseline_abs_error_eok"]
    base["selected_ape_pct"] = base["baseline_ape_pct"]
    base["selected_route_id"] = "baseline"
    annual = load_annual_official()
    panel = build_indicator_panel()
    candidates = route_predictions(panel, annual)
    candidate_detail = candidates.merge(
        base[
            [
                "quarter_region",
                "activity",
                "year",
                "available_quarters",
                "official_annual_eok",
                "baseline_predicted_eok",
                "baseline_error_eok",
                "baseline_abs_error_eok",
                "baseline_ape_pct",
            ]
        ],
        on=["quarter_region", "activity", "year", "available_quarters", "official_annual_eok"],
        how="inner",
    )
    candidate_detail["candidate_improvement_eok"] = (
        candidate_detail["baseline_abs_error_eok"] - candidate_detail["candidate_abs_error_eok"]
    )
    candidate_detail.to_csv(OUT / "region_level_indicator_candidate_detail.csv", index=False, encoding="utf-8-sig")

    scenarios = []
    regional_outputs = []
    scenario_defs = {
        "baseline": set(),
        "transport_only": {"운수 및 창고업"},
        "top4_sido_q1": {"운수 및 창고업", "건설업", "숙박 및 음식점업", "정보통신업"},
        "top5_with_manufacturing": {"운수 및 창고업", "건설업", "숙박 및 음식점업", "정보통신업", "광업, 제조업"},
    }
    for name, acts in scenario_defs.items():
        s, r = scenario_summary(base, candidate_detail, acts, name)
        scenarios.append(s)
        regional_outputs.append(r)
    # A small theoretically motivated scenario: only the two direct service
    # indicators that are not construction-order or broad manufacturing proxies.
    s, r = scenario_summary(base, candidate_detail, {"운수 및 창고업", "정보통신업"}, "transport_info_only")
    scenarios.append(s)
    regional_outputs.append(r)
    scenario_df = pd.concat(scenarios, ignore_index=True)
    regional_df = pd.concat(regional_outputs, ignore_index=True)
    greedy = greedy_minimal_routes(base, candidate_detail, k=1)

    gated_routes = select_cell_routes_from_dev(base, candidate_detail, k=1)
    gated_selected = apply_cell_route_table(base, candidate_detail, gated_routes, "dev_gated_region_activity_q1")
    gated_split = summarize_by_year_split(gated_selected, "dev_gated_region_activity_q1")
    gated_regional = summarize_region_activity(gated_selected).assign(scenario="dev_gated_region_activity_q1")
    split_frames = [gated_split]
    split_selected_defs = {
        "baseline": set(),
        "transport_only": {"운수 및 창고업"},
        "transport_info_only": {"운수 및 창고업", "정보통신업"},
    }
    for split_name, split_acts in split_selected_defs.items():
        split_selected = apply_routes(base, candidate_detail, split_acts)
        split_frames.append(summarize_by_year_split(split_selected, split_name))
    split_summary = pd.concat(split_frames, ignore_index=True)

    scenario_df.to_csv(OUT / "region_level_minimal_routing_scenario_summary.csv", index=False, encoding="utf-8-sig")
    regional_df.to_csv(OUT / "region_level_minimal_routing_regional_wape.csv", index=False, encoding="utf-8-sig")
    greedy.to_csv(OUT / "region_level_minimal_routing_greedy_q1.csv", index=False, encoding="utf-8-sig")
    gated_routes.to_csv(OUT / "region_level_dev_gated_route_selection.csv", index=False, encoding="utf-8-sig")
    gated_selected.to_csv(OUT / "region_level_dev_gated_selected_detail.csv", index=False, encoding="utf-8-sig")
    split_summary.to_csv(OUT / "region_level_dev_gated_split_summary.csv", index=False, encoding="utf-8-sig")
    gated_regional.to_csv(OUT / "region_level_dev_gated_regional_wape.csv", index=False, encoding="utf-8-sig")

    q1 = scenario_df[scenario_df["available_quarters"].eq(1)].copy()
    q4 = scenario_df[scenario_df["available_quarters"].eq(4)].copy()
    top_fail = (
        regional_df[
            regional_df["scenario"].eq("top4_sido_q1")
            & regional_df["available_quarters"].eq(1)
            & regional_df["wape_pct"].gt(10)
        ]
        .sort_values("wape_pct", ascending=False)
        .head(25)
    )
    gated_accepted = gated_routes[gated_routes["accepted"]].sort_values(
        ["dev_improvement_pctp", "dev_candidate_wape_pct"], ascending=[False, True]
    )
    gated_fail = (
        gated_regional[gated_regional["available_quarters"].eq(1) & gated_regional["wape_pct"].gt(10)]
        .sort_values("wape_pct", ascending=False)
        .head(25)
    )
    report = f"""# 지역 레벨 최소 산업군 라우팅 실험

생성시각: {CREATED_AT}

## 목적

전국 합산 WAPE가 아니라 `광역시도×업종` 5개년 WAPE가 10%를 넘는 셀을 줄이는 것이 목표다.  
이번 첫 실험은 로컬에 이미 있는 시도 단위 직접 활동지표만 사용한다. 시군구×업종은 별도 직접 월/분기 지표가 부족하므로 이 실험의 성능개선 대상이 아니라 다음 수집 과제로 둔다.

## 사용 후보

| 업종 | 후보 지표 | 적용 이유 |
| --- | --- | --- |
| 운수 및 창고업 | 시도별 서비스업생산지수 H | 업종명과 직접 대응되는 시도별 생산활동 지수 |
| 숙박 및 음식점업 | 시도별 서비스업생산지수 I | 업종명과 직접 대응되는 시도별 생산활동 지수 |
| 정보통신업 | 시도별 서비스업생산지수 J | 업종명과 직접 대응되는 시도별 생산활동 지수 |
| 건설업 | 건축 12분기·토목 24분기 건설수주 분산지표 | BOK RECI식 장기 프로젝트 분산 개념에 맞춘 후보 |
| 광업, 제조업 | 시도별 제조업 생산지수 | 광업·제조업 결합 actual의 제조업 시간경로 후보 |

## Q1: 1분기+1개월 운영시점

{md_table(q1[[
    "scenario", "routed_activity_count", "routed_activities", "region_activity_cells",
    "over10_cells", "over10_official_sum_eok", "overall_region_activity_wape_pct"
]].rename(columns={
    "scenario": "시나리오",
    "routed_activity_count": "라우팅산업수",
    "routed_activities": "라우팅산업",
    "region_activity_cells": "지역×업종셀",
    "over10_cells": "WAPE10초과셀",
    "over10_official_sum_eok": "10초과셀_실제합_억원",
    "overall_region_activity_wape_pct": "전체지역업종WAPE_pct",
}), 3)}

## Q4/정밀화 운영시점

{md_table(q4[[
    "scenario", "routed_activity_count", "routed_activities", "region_activity_cells",
    "over10_cells", "over10_official_sum_eok", "overall_region_activity_wape_pct"
]].rename(columns={
    "scenario": "시나리오",
    "routed_activity_count": "라우팅산업수",
    "routed_activities": "라우팅산업",
    "region_activity_cells": "지역×업종셀",
    "over10_cells": "WAPE10초과셀",
    "over10_official_sum_eok": "10초과셀_실제합_억원",
    "overall_region_activity_wape_pct": "전체지역업종WAPE_pct",
}), 3)}

## Q1 greedy 선택

{md_table(greedy.rename(columns={
    "step": "단계",
    "added_activity": "추가산업",
    "selected_activities": "누적선택",
    "over10_cells": "WAPE10초과셀",
    "over10_reduction": "감소셀수",
    "overall_region_activity_wape_pct": "전체지역업종WAPE_pct",
}), 3)}

## 누수방지형 지역×업종 제한 적용

2021~2023년만 보고 후보 지표가 기준 추정보다 1%p 이상 개선되고 후보 WAPE가 10% 이하인 `시도×업종` 조합만 선택했다.  
선택 규칙에는 2024~2025년 실제값을 쓰지 않았다.

### split 검증

{md_table(split_summary.rename(columns={
    "scenario": "시나리오",
    "split": "검증구간",
    "available_quarters": "운영시점",
    "region_activity_cells": "지역×업종셀",
    "over10_cells": "WAPE10초과셀",
    "over10_official_sum_eok": "10초과셀_실제합_억원",
    "overall_region_activity_wape_pct": "전체지역업종WAPE_pct",
}), 3)}

### 채택된 지역×업종 후보

{md_table(gated_accepted[[
    "quarter_region", "activity", "route_id", "dev_baseline_wape_pct",
    "dev_candidate_wape_pct", "dev_improvement_pctp"
]].rename(columns={
    "quarter_region": "시도",
    "activity": "업종",
    "route_id": "사용지표",
    "dev_baseline_wape_pct": "2021~2023_기준WAPE_pct",
    "dev_candidate_wape_pct": "2021~2023_후보WAPE_pct",
    "dev_improvement_pctp": "개선폭_p%p",
}), 3)}

## top4 적용 후에도 남는 Q1 WAPE 10% 초과 셀

{md_table(top_fail[[
    "quarter_region", "activity", "official_sum_eok", "abs_error_sum_eok", "wape_pct", "max_ape_pct", "over10_years", "routed_years"
]].rename(columns={
    "quarter_region": "시도",
    "activity": "업종",
    "official_sum_eok": "5개년실제합_억원",
    "abs_error_sum_eok": "5개년절대오차합_억원",
    "wape_pct": "WAPE_pct",
    "max_ape_pct": "최대연도APE_pct",
    "over10_years": "10초과연도수",
    "routed_years": "라우팅연도수",
}), 3)}

## 제한 적용 후에도 남는 Q1 WAPE 10% 초과 셀

{md_table(gated_fail[[
    "quarter_region", "activity", "official_sum_eok", "abs_error_sum_eok", "wape_pct", "max_ape_pct", "over10_years", "routed_years"
]].rename(columns={
    "quarter_region": "시도",
    "activity": "업종",
    "official_sum_eok": "5개년실제합_억원",
    "abs_error_sum_eok": "5개년절대오차합_억원",
    "wape_pct": "WAPE_pct",
    "max_ape_pct": "최대연도APE_pct",
    "over10_years": "10초과연도수",
    "routed_years": "라우팅연도수",
}), 3)}

## 판단

1. 지역 레벨 기준에서는 전국 평균보다 훨씬 많은 실패 셀이 드러난다.
2. 업종 일괄 교체는 위험하다. 건설·숙박·제조를 함께 교체하면 10% 초과 셀이 늘어난다.
3. 현재 결과만 놓고 운영안으로 삼을 수 있는 후보는 `운수 및 창고업` 또는 `운수 및 창고업+정보통신업`의 제한적 직접지표 적용이다.
   - 전체 2021~2025년 Q1 기준: 20개 → 18개 또는 17개.
   - 2024~2025년 holdout Q1 기준: 33개 → 25개 또는 20개.
   - 단, 2021~2023년 dev 구간은 악화되므로 모든 기간에 항상 우수하다고 주장하면 안 된다.
4. 2021~2023년으로 지역×업종 후보를 고르는 dev-gated 방식은 누수 방지에는 유리하지만, holdout 개선폭이 약해 현 단계 성능개선안으로 채택하기 어렵다.
5. 시군구×업종 846개 초과 셀은 시도 지표만으로 직접 해결했다고 주장하면 안 된다. 시군구 월/분기 직접 활동자료를 확보해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(q1.to_string(index=False))
    print(greedy.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
