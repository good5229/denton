#!/usr/bin/env python3
"""Leakage-safe rolling selection for public indicator activity routes.

Phase252 replaces the exploratory hard-region no-worse selector with a
rolling holdout gate:

* route choice for target year y uses only years < y;
* target-year actuals are used only after the route has been selected;
* strict adoption requires WAPE improvement, over10/over20 non-increase, and
  max-APE non-worsening on the training years;
* practical candidates are reported separately and are not applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase252_rolling_indicator_route_selection.md"
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
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}
REGION_SHORT = {v: k for k, v in REGION_FULL.items()}

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


def md_table(df: pd.DataFrame, max_rows: int | None = None, digits: int = 3) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
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


def metrics(df: pd.DataFrame, pred_col: str) -> dict[str, float | int]:
    if df.empty:
        return {
            "rows": 0,
            "abs_error_sum_eok": np.nan,
            "official_sum_eok": np.nan,
            "wape_pct": np.nan,
            "over10_cells": 0,
            "over20_cells": 0,
            "max_ape_pct": np.nan,
            "p95_ape_pct": np.nan,
        }
    actual = df["official_annual_eok"].abs()
    err = (df[pred_col] - df["official_annual_eok"]).abs()
    ape = np.where(actual.gt(0), err / actual * 100, np.nan)
    return {
        "rows": int(len(df)),
        "abs_error_sum_eok": float(err.sum()),
        "official_sum_eok": float(actual.sum()),
        "wape_pct": float(err.sum() / actual.sum() * 100) if actual.sum() else np.nan,
        "over10_cells": int(np.nansum(ape > 10)),
        "over20_cells": int(np.nansum(ape > 20)),
        "max_ape_pct": float(np.nanmax(ape)) if len(ape) else np.nan,
        "p95_ape_pct": float(np.nanpercentile(ape, 95)) if len(ape) else np.nan,
    }


def load_base() -> pd.DataFrame:
    base = pd.read_csv(OUT / "operating_point_sido_activity_validation.csv")
    if "available_quarters_x" in base:
        base["available_quarters"] = pd.to_numeric(base["available_quarters_x"], errors="coerce").fillna(
            pd.to_numeric(base.get("available_quarters"), errors="coerce")
        )
    base["available_quarters"] = base["available_quarters"].astype(int)
    base = base[base["year"].between(2021, 2025)].copy()
    base["baseline_abs_error_eok"] = base["annualized_error_eok"].abs()
    base["baseline_ape_pct"] = base["annualized_ape_pct"]
    return base


def annual_official() -> pd.DataFrame:
    x = pd.read_csv("data/processed/phase211_gyeonggi_2024_2025_grdp_extension/phase211_sido_quarterly_xlsx_long.csv")
    return (
        x[x["region"].isin(REGION_FULL.keys())]
        .groupby(["region", "activity", "year"], as_index=False)["official_value_eok"]
        .sum()
        .rename(columns={"region": "quarter_region", "official_value_eok": "official_annual_eok"})
    )


def indicator_panel() -> pd.DataFrame:
    panels: list[pd.DataFrame] = []

    m = pd.read_csv("data/processed/phase195_monthly_mining_manufacturing_production_index.csv")
    m = m[(m["c1_nm"].isin(REGION_FULL.values())) & (m["c2_nm"].eq("제조업"))].copy()
    m["year"] = m["prd_de"].astype(str).str[:4].astype(int)
    m["quarter"] = ((m["prd_de"].astype(str).str[4:6].astype(int) - 1) // 3 + 1).astype(int)
    m["quarter_region"] = m["c1_nm"].map(REGION_SHORT)
    mm = m.groupby(["quarter_region", "year", "quarter"], as_index=False)["value"].mean().rename(columns={"value": "indicator_value"})
    mm["activity"] = "광업, 제조업"
    mm["route_id"] = "regional_manufacturing_production_index"
    panels.append(mm)

    svc = pd.read_csv("data/processed/rolling_service_production_index.csv", encoding="cp949")
    svc = svc[svc["c1_nm"].isin(REGION_FULL.values())].copy()
    svc["year"] = svc["prd_de"].astype(str).str[:4].astype(int)
    svc["quarter"] = svc["prd_de"].astype(str).str[4:6].astype(int)
    svc["quarter_region"] = svc["c1_nm"].map(REGION_SHORT)
    for activity, codes in SERVICE_MAP.items():
        tmp = svc[svc["c2_id"].astype(str).isin(codes)].copy()
        q = tmp.groupby(["quarter_region", "year", "quarter"], as_index=False)["value"].mean().rename(columns={"value": "indicator_value"})
        q["activity"] = activity
        q["route_id"] = "regional_service_production_index_" + "_".join(codes)
        panels.append(q)

    rk = pd.read_csv("data/processed/rolling_kosis_collected_all.csv", encoding="cp949")
    con = rk[(rk["tbl_id"].eq("DT_1G1B035")) & (rk["c1_nm"].isin(REGION_FULL.values()))].copy()
    con["year"] = con["prd_de"].astype(str).str[:4].astype(int)
    con["quarter"] = con["prd_de"].astype(str).str[4:6].astype(int)
    con["quarter_region"] = con["c1_nm"].map(REGION_SHORT)
    raw = con[con["c2_nm"].eq("계")].groupby(["quarter_region", "year", "quarter"], as_index=False)["value"].sum().rename(columns={"value": "indicator_value"})
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
        if c not in pivot:
            pivot[c] = 0.0
        pivot[c] = pivot[c].fillna(0.0)
    dist_parts = []
    for _, g in pivot.groupby("quarter_region"):
        h = g.sort_values(["year", "quarter"]).copy()
        h["building_12q"] = h["건축"].rolling(12, min_periods=1).mean()
        h["civil_24q"] = h["토목"].rolling(24, min_periods=1).mean()
        h["indicator_value"] = h["building_12q"] + h["civil_24q"]
        dist_parts.append(h[["quarter_region", "year", "quarter", "indicator_value"]])
    dist = pd.concat(dist_parts, ignore_index=True)
    dist["activity"] = "건설업"
    dist["route_id"] = "regional_construction_orders_bok_12_24q"
    panels.append(dist)

    panel = pd.concat(panels, ignore_index=True)
    panel = panel[panel["year"].between(2020, 2025)].copy()
    panel["indicator_value"] = pd.to_numeric(panel["indicator_value"], errors="coerce")
    return panel.dropna(subset=["quarter_region", "activity", "route_id", "indicator_value"])


def candidate_predictions(panel: pd.DataFrame) -> pd.DataFrame:
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
        prev_by_q = prev.groupby("quarter")["indicator_value"].sum().to_dict()
        basis_eok = float(basis["official_annual_eok"].iloc[0])
        official_eok = float(official["official_annual_eok"].iloc[0])
        for k in [1, 2, 3, 4]:
            cur_cum = float(g[g["quarter"].le(k)]["indicator_value"].sum())
            prev_cum = float(sum(v for q, v in prev_by_q.items() if int(q) <= k))
            if prev_cum == 0:
                continue
            rows.append(
                {
                    "quarter_region": region,
                    "activity": activity,
                    "route_id": route_id,
                    "year": int(year),
                    "basis_year": int(year) - 1,
                    "available_quarters": int(k),
                    "basis_annual_eok": basis_eok,
                    "current_indicator_cum": cur_cum,
                    "previous_indicator_cum": prev_cum,
                    "candidate_annualized_eok": basis_eok * cur_cum / prev_cum,
                    "official_annual_eok": official_eok,
                }
            )
    cand = pd.DataFrame(rows)
    if not cand.empty:
        cand["candidate_error_eok"] = cand["candidate_annualized_eok"] - cand["official_annual_eok"]
        cand["candidate_ape_pct"] = cand["candidate_error_eok"].abs() / cand["official_annual_eok"].abs() * 100
    return cand


@dataclass
class GateResult:
    strict_pass: bool
    practical_pass: bool
    reason: str


def gate(base_m: dict[str, float | int], cand_m: dict[str, float | int]) -> GateResult:
    if int(cand_m["rows"]) < 8:
        return GateResult(False, False, "too_few_training_rows")
    wape_improves = float(cand_m["wape_pct"]) < float(base_m["wape_pct"])
    over10_ok = int(cand_m["over10_cells"]) <= int(base_m["over10_cells"])
    over20_ok = int(cand_m["over20_cells"]) <= int(base_m["over20_cells"])
    max_ok = float(cand_m["max_ape_pct"]) <= float(base_m["max_ape_pct"])
    p95_ok = float(cand_m["p95_ape_pct"]) <= float(base_m["p95_ape_pct"])
    max_capped = float(cand_m["max_ape_pct"]) <= float(base_m["max_ape_pct"]) + 5.0
    if wape_improves and over10_ok and over20_ok and max_ok:
        return GateResult(True, True, "strict_pass")
    if wape_improves and over10_ok and over20_ok and p95_ok and max_capped:
        return GateResult(False, True, "practical_only_max_guard")
    failed = []
    if not wape_improves:
        failed.append("wape_not_improved")
    if not over10_ok:
        failed.append("over10_worse")
    if not over20_ok:
        failed.append("over20_worse")
    if not max_ok:
        failed.append("max_ape_worse")
    return GateResult(False, False, "+".join(failed))


def select_routes(merged: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    chosen_rows = []
    for (track, activity, k, holdout_year), _ in merged.groupby(["track", "activity", "available_quarters", "year"]):
        train = merged[
            merged["track"].eq(track)
            & merged["activity"].eq(activity)
            & merged["available_quarters"].eq(k)
            & merged["year"].lt(holdout_year)
        ].copy()
        train_year_count = int(train["year"].nunique()) if not train.empty else 0
        if train.empty:
            chosen_rows.append(
                {
                    "track": track,
                    "activity": activity,
                    "available_quarters": k,
                    "holdout_year": int(holdout_year),
                    "selected_route_id": "baseline",
                    "selection_status": "no_prior_training",
                }
            )
            continue
        if train_year_count < 2:
            for route_id, g in train.groupby("route_id"):
                base_m = metrics(g.drop_duplicates(["track", "quarter_region", "activity", "year", "available_quarters"]), "annualized_predicted_eok")
                cand_m = metrics(g, "candidate_annualized_eok")
                rows.append(
                    {
                        "track": track,
                        "activity": activity,
                        "available_quarters": int(k),
                        "holdout_year": int(holdout_year),
                        "route_id": route_id,
                        "train_years": ",".join(map(str, sorted(train["year"].unique()))),
                        "train_year_count": train_year_count,
                        "train_rows": int(cand_m["rows"]),
                        "baseline_train_wape_pct": base_m["wape_pct"],
                        "candidate_train_wape_pct": cand_m["wape_pct"],
                        "train_delta_wape_pp": float(cand_m["wape_pct"]) - float(base_m["wape_pct"]),
                        "baseline_over10_cells": base_m["over10_cells"],
                        "candidate_over10_cells": cand_m["over10_cells"],
                        "baseline_over20_cells": base_m["over20_cells"],
                        "candidate_over20_cells": cand_m["over20_cells"],
                        "baseline_max_ape_pct": base_m["max_ape_pct"],
                        "candidate_max_ape_pct": cand_m["max_ape_pct"],
                        "baseline_p95_ape_pct": base_m["p95_ape_pct"],
                        "candidate_p95_ape_pct": cand_m["p95_ape_pct"],
                        "strict_pass": False,
                        "practical_pass": False,
                        "gate_reason": "too_few_training_years",
                    }
                )
            chosen_rows.append(
                {
                    "track": track,
                    "activity": activity,
                    "available_quarters": int(k),
                    "holdout_year": int(holdout_year),
                    "selected_route_id": "baseline",
                    "selection_status": "too_few_training_years",
                }
            )
            continue
        route_eval = []
        for route_id, g in train.groupby("route_id"):
            base_m = metrics(g.drop_duplicates(["track", "quarter_region", "activity", "year", "available_quarters"]), "annualized_predicted_eok")
            cand_m = metrics(g, "candidate_annualized_eok")
            gr = gate(base_m, cand_m)
            row = {
                "track": track,
                "activity": activity,
                "available_quarters": int(k),
                "holdout_year": int(holdout_year),
                "route_id": route_id,
                "train_years": ",".join(map(str, sorted(train["year"].unique()))),
                "train_year_count": train_year_count,
                "train_rows": int(cand_m["rows"]),
                "baseline_train_wape_pct": base_m["wape_pct"],
                "candidate_train_wape_pct": cand_m["wape_pct"],
                "train_delta_wape_pp": float(cand_m["wape_pct"]) - float(base_m["wape_pct"]),
                "baseline_over10_cells": base_m["over10_cells"],
                "candidate_over10_cells": cand_m["over10_cells"],
                "baseline_over20_cells": base_m["over20_cells"],
                "candidate_over20_cells": cand_m["over20_cells"],
                "baseline_max_ape_pct": base_m["max_ape_pct"],
                "candidate_max_ape_pct": cand_m["max_ape_pct"],
                "baseline_p95_ape_pct": base_m["p95_ape_pct"],
                "candidate_p95_ape_pct": cand_m["p95_ape_pct"],
                "strict_pass": gr.strict_pass,
                "practical_pass": gr.practical_pass,
                "gate_reason": gr.reason,
            }
            route_eval.append(row)
            rows.append(row)
        strict = [r for r in route_eval if r["strict_pass"]]
        if strict:
            selected = sorted(strict, key=lambda r: (r["candidate_train_wape_pct"], r["candidate_max_ape_pct"]))[0]
            chosen_rows.append(
                {
                    "track": track,
                    "activity": activity,
                    "available_quarters": int(k),
                    "holdout_year": int(holdout_year),
                    "selected_route_id": selected["route_id"],
                    "selection_status": "strict_pass",
                    "train_delta_wape_pp": selected["train_delta_wape_pp"],
                }
            )
        else:
            chosen_rows.append(
                {
                    "track": track,
                    "activity": activity,
                    "available_quarters": int(k),
                    "holdout_year": int(holdout_year),
                    "selected_route_id": "baseline",
                    "selection_status": "no_strict_pass",
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(chosen_rows)


def apply_selection(base: pd.DataFrame, merged: pd.DataFrame, chosen: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    out["holdout_year"] = out["year"].astype(int)
    out = out.merge(
        chosen,
        on=["track", "activity", "available_quarters", "holdout_year"],
        how="left",
    )
    out["selected_route_id"] = out["selected_route_id"].fillna("baseline")
    out["selection_status"] = out["selection_status"].fillna("no_candidate")
    out["rolling_predicted_eok"] = out["annualized_predicted_eok"]
    route_rows = []
    for route_id, g in out[out["selected_route_id"].ne("baseline")].groupby("selected_route_id"):
        key = ["track", "quarter_region", "activity", "year", "available_quarters"]
        cand = merged[merged["route_id"].eq(route_id)][key + ["route_id", "candidate_annualized_eok"]].copy()
        idx = g.reset_index().merge(cand, on=key, how="left")
        route_rows.append(idx[["index", "candidate_annualized_eok"]])
    if route_rows:
        repl = pd.concat(route_rows, ignore_index=True)
        repl = repl.dropna(subset=["candidate_annualized_eok"])
        out.loc[repl["index"].astype(int), "rolling_predicted_eok"] = repl["candidate_annualized_eok"].to_numpy()
    out["rolling_error_eok"] = out["rolling_predicted_eok"] - out["official_annual_eok"]
    out["rolling_ape_pct"] = out["rolling_error_eok"].abs() / out["official_annual_eok"].abs() * 100
    return out


def summarize(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows = []
    for keys, g in df.groupby(group_cols):
        if not isinstance(keys, tuple):
            keys = (keys,)
        d = dict(zip(group_cols, keys))
        base_m = metrics(g, "annualized_predicted_eok")
        roll_m = metrics(g.rename(columns={"rolling_predicted_eok": "pred_for_metric"}), "pred_for_metric")
        d.update(
            {
                "rows": base_m["rows"],
                "baseline_wape_pct": base_m["wape_pct"],
                "rolling_wape_pct": roll_m["wape_pct"],
                "delta_wape_pp": float(roll_m["wape_pct"]) - float(base_m["wape_pct"]),
                "baseline_over10_cells": base_m["over10_cells"],
                "rolling_over10_cells": roll_m["over10_cells"],
                "baseline_over20_cells": base_m["over20_cells"],
                "rolling_over20_cells": roll_m["over20_cells"],
                "baseline_max_ape_pct": base_m["max_ape_pct"],
                "rolling_max_ape_pct": roll_m["max_ape_pct"],
                "adopted_rows": int(g["selected_route_id"].ne("baseline").sum()),
            }
        )
        rows.append(d)
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_base()
    panel = indicator_panel()
    cand = candidate_predictions(panel)
    key = ["quarter_region", "activity", "year", "available_quarters", "official_annual_eok"]
    merged = cand.merge(
        base[
            [
                "track",
                "quarter_region",
                "activity",
                "year",
                "available_quarters",
                "annualized_predicted_eok",
                "official_annual_eok",
                "annualized_error_eok",
                "annualized_ape_pct",
            ]
        ],
        on=key,
        how="inner",
    )
    merged.to_csv(OUT / "phase252_candidate_detail.csv", index=False, encoding="utf-8-sig")
    route_eval, chosen = select_routes(merged)
    route_eval.to_csv(OUT / "phase252_route_training_gate.csv", index=False, encoding="utf-8-sig")
    chosen.to_csv(OUT / "phase252_route_selection_by_holdout.csv", index=False, encoding="utf-8-sig")
    rolled = apply_selection(base, merged, chosen)
    rolled.to_csv(OUT / "phase252_rolling_indicator_route_detail.csv", index=False, encoding="utf-8-sig")

    holdout = rolled[rolled["year"].ge(2022)].copy()
    summary_track = summarize(holdout, ["track", "available_quarters", "operating_label"])
    summary_activity = summarize(holdout, ["track", "activity", "available_quarters"])
    summary_year = summarize(holdout, ["track", "year", "available_quarters"])
    summary_track.to_csv(OUT / "phase252_summary_by_track_quarter.csv", index=False, encoding="utf-8-sig")
    summary_activity.to_csv(OUT / "phase252_summary_by_activity.csv", index=False, encoding="utf-8-sig")
    summary_year.to_csv(OUT / "phase252_summary_by_year.csv", index=False, encoding="utf-8-sig")

    gate_counts = (
        route_eval.groupby(["strict_pass", "practical_pass", "gate_reason"], as_index=False)
        .agg(cells=("route_id", "count"))
        .sort_values(["strict_pass", "practical_pass", "cells"], ascending=[False, False, False])
    )
    selected_routes = chosen[chosen["selected_route_id"].ne("baseline")].copy()
    practical_only = route_eval[(route_eval["practical_pass"].eq(True)) & (route_eval["strict_pass"].eq(False))].copy()

    headline = summary_track[summary_track["available_quarters"].isin([1, 2, 3, 4])].copy()
    headline = headline.sort_values(["track", "available_quarters"])
    headline_delta = float(headline["delta_wape_pp"].sum()) if not headline.empty else 0.0
    headline_over10_delta = int((headline["rolling_over10_cells"] - headline["baseline_over10_cells"]).sum()) if not headline.empty else 0
    operational_decision = (
        "reject_for_operational_adoption"
        if headline_delta > 0 or headline_over10_delta > 0
        else "candidate_for_guarded_adoption"
    )

    activity_top = summary_activity.sort_values(["delta_wape_pp", "rolling_wape_pct"]).head(20)
    activity_bad = summary_activity.sort_values(["delta_wape_pp", "rolling_wape_pct"], ascending=[False, False]).head(20)

    report = f"""# Phase252 rolling 활동지표 route 선택 검증

생성시각: {CREATED_AT}

## 1. 목적

기존 hard-region no-worse 실험은 목표연도 actual을 보고 셀별로 좋아지는 후보만 채택할 수 있어 운영 채택 근거로는 데이터 유출 위험이 있다. 이번 실험은 17개 시도 전체에 대해 목표연도 `y` 이전 연도만으로 route를 선택하고, 선택된 route만 `y`에 적용하는 rolling holdout 검증이다.

## 2. 설계

| 항목 | 내용 |
| --- | --- |
| 검증 범위 | 17개 시도, 2021~2025 시도×업종×운영시점 |
| holdout 성능 집계 | 2022~2025, 2021년은 prior training 부재로 선택 성능에서 제외 |
| 후보 지표 | 제조업 생산지수, 시도별 서비스업생산지수, 건설수주 원지표, 건설수주 BOK식 12·24분기 분산 |
| 후보 예측식 | 전년도 official annual × 목표연도 누적 지표 / 전년도 동일누적 지표 |
| route 선택 | `track×activity×available_quarters×holdout_year`별로 holdout 이전 연도만 사용 |
| strict 채택 | training WAPE 개선, 10% 초과 셀 비증가, 20% 초과 셀 비증가, max APE 비악화 |
| 최소 훈련기간 | 목표연도 이전 2개년 이상. 2022년은 2021년 1개년만 있어 route 채택 금지 |
| practical 후보 | p95 APE 비악화와 max APE +5%p 이내까지는 후보로 기록하되 적용하지 않음 |

## 2.1 누수 방지 감사

| 점검항목 | 판정 |
| --- | --- |
| 후보식의 금액 기준 | `basis_year = target_year - 1`의 official annual만 사용 |
| target-year official annual | 후보 예측값 계산에는 미사용, 선택 후 holdout 평가와 merge 검산에만 사용 |
| route 선택 단위 | `track×activity×available_quarters×holdout_year`; 특정 시도 holdout 결과를 보고 route를 바꾸지 않음 |
| 실패 route 기록 | `phase252_route_training_gate.csv`에 strict/practical 통과·탈락 사유 전체 저장 |
| 지표 공표시점 | historical release calendar lock 미적용. 따라서 Q+1개월 strict 속보가 아니라 최신 빈티지 공개지표 기반 rolling holdout으로 제한 |

## 3. 전체 운영시점별 holdout 결과

{md_table(headline.rename(columns={
    "track": "트랙",
    "available_quarters": "사용분기수",
    "operating_label": "운영시점",
    "rows": "검증행",
    "baseline_wape_pct": "기준WAPE_pct",
    "rolling_wape_pct": "rolling_route_WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_cells": "기준_10pct초과",
    "rolling_over10_cells": "route_10pct초과",
    "baseline_over20_cells": "기준_20pct초과",
    "rolling_over20_cells": "route_20pct초과",
    "baseline_max_ape_pct": "기준최대APE_pct",
    "rolling_max_ape_pct": "route최대APE_pct",
    "adopted_rows": "route적용행",
}), digits=3)}

## 4. 개선 상위 업종·운영시점

{md_table(activity_top.rename(columns={
    "track": "트랙",
    "activity": "업종",
    "available_quarters": "사용분기수",
    "rows": "검증행",
    "baseline_wape_pct": "기준WAPE_pct",
    "rolling_wape_pct": "route_WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_cells": "기준_10pct초과",
    "rolling_over10_cells": "route_10pct초과",
    "baseline_max_ape_pct": "기준최대APE_pct",
    "rolling_max_ape_pct": "route최대APE_pct",
    "adopted_rows": "route적용행",
}), max_rows=20, digits=3)}

## 5. 악화 상위 업종·운영시점

{md_table(activity_bad.rename(columns={
    "track": "트랙",
    "activity": "업종",
    "available_quarters": "사용분기수",
    "rows": "검증행",
    "baseline_wape_pct": "기준WAPE_pct",
    "rolling_wape_pct": "route_WAPE_pct",
    "delta_wape_pp": "변화_pp",
    "baseline_over10_cells": "기준_10pct초과",
    "rolling_over10_cells": "route_10pct초과",
    "baseline_max_ape_pct": "기준최대APE_pct",
    "rolling_max_ape_pct": "route최대APE_pct",
    "adopted_rows": "route적용행",
}), max_rows=20, digits=3)}

## 6. 선택된 strict route

{md_table(selected_routes[[
    "track", "activity", "available_quarters", "holdout_year", "selected_route_id", "selection_status", "train_delta_wape_pp"
]].rename(columns={
    "track": "트랙",
    "activity": "업종",
    "available_quarters": "사용분기수",
    "holdout_year": "평가연도",
    "selected_route_id": "선택route",
    "selection_status": "선택판정",
    "train_delta_wape_pp": "훈련WAPE개선_pp",
}), max_rows=40, digits=3)}

## 7. Gate 탈락·후보 현황

{md_table(gate_counts.rename(columns={
    "strict_pass": "strict통과",
    "practical_pass": "practical후보",
    "gate_reason": "판정사유",
    "cells": "route평가건수",
}), digits=0)}

### practical only 후보

{md_table(practical_only[[
    "track", "activity", "available_quarters", "holdout_year", "route_id", "train_delta_wape_pp", "gate_reason"
]].rename(columns={
    "track": "트랙",
    "activity": "업종",
    "available_quarters": "사용분기수",
    "holdout_year": "평가연도",
    "route_id": "후보route",
    "train_delta_wape_pp": "훈련WAPE개선_pp",
    "gate_reason": "판정사유",
}), max_rows=30, digits=3)}

## 8. 해석

- 운영 판정: `{operational_decision}`.
- strict training gate만으로도 holdout 전체 WAPE 또는 10% 초과 셀이 악화되어, Phase252 route는 현재 운영 산출물에 반영하지 않는다.
- 본 실험은 목표연도 actual을 route 선택에 사용하지 않는 rolling holdout 구조다.
- 각 목표연도 `y`의 route는 `y` 이전 연도 성과만으로 선택하고, `y` actual은 선택 후 사후 평가에만 사용한다.
- 기존 hard-region no-worse 선택은 목표연도 actual을 셀별 채택 판단에 사용할 수 있으므로 운영 채택 근거가 아니라 탐색적 후보 발굴 결과로만 해석한다.
- 전국·시도 지표는 시군구 공간배분 근거가 아니라 시도×업종 시간경로 후보로만 사용한다.
- Q+1개월 속보 성과로 표현하려면 각 후보 지표의 공표시점 vintage lock이 추가로 필요하다.
- route가 선택되지 않은 업종·운영시점은 성능개선 실패가 아니라 baseline 유지가 더 안전하다는 판정이다.
- 이번 결과는 공공 활동지표가 유용하지 않다는 뜻이 아니라, 현재의 `track×activity×available_quarters` 단위 전역 route 선택 규칙으로는 holdout 안정성이 부족하다는 뜻이다.

## 9. 산출물

- `nationwide/outputs/phase252_candidate_detail.csv`
- `nationwide/outputs/phase252_route_training_gate.csv`
- `nationwide/outputs/phase252_route_selection_by_holdout.csv`
- `nationwide/outputs/phase252_rolling_indicator_route_detail.csv`
- `nationwide/outputs/phase252_summary_by_track_quarter.csv`
- `nationwide/outputs/phase252_summary_by_activity.csv`
- `nationwide/outputs/phase252_summary_by_year.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(headline.to_string(index=False))
    print(selected_routes.head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
