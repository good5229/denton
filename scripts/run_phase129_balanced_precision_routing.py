#!/usr/bin/env python3
"""Phase129: balanced precision routing for high-gap middle industries.

The goal is to reduce precision-error dispersion without using actual values as
direct correction totals.  Candidate values are still generated from external
activity structures evaluated in Phase127.  This script only changes the
selection rule:

* keep parent/block totals implicit in each candidate option;
* do not allow gt10/gt20 cell counts to increase;
* allow at most two small worsened cells when aggregate error drops enough;
* rank by aggregate error reduction, then by reduced high-error cell counts.

This is a precision-only route because the COMWEL snapshot and several
structural sources are post-publication or current-state sources.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase129_balanced_precision_routing"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase129_balanced_precision_routing.md"

BASE = DATA / "phase114_block_routed_refinement_audit" / "phase114_refined_registry.csv"
SCREEN = DATA / "phase127_precision_comwel_after_phase114" / "phase127_candidate_screen.csv"
DETAIL = DATA / "phase127_precision_comwel_after_phase114" / "phase127_candidate_detail.csv"
STRICT127 = DATA / "phase127_precision_comwel_after_phase114" / "phase127_strict_registry.csv"
RISK127 = DATA / "phase127_precision_comwel_after_phase114" / "phase127_risk_registry.csv"


def load_base() -> pd.DataFrame:
    df = pd.read_csv(BASE, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["phase129_base_predicted_gva_eok"] = df["phase114_predicted_gva_eok"]
    df["phase129_base_error_gva_eok"] = df["phase114_error_gva_eok"]
    df["phase129_base_error_rate_pct"] = df["phase114_error_rate_pct"]
    return df


def mark_adoptable(screen: pd.DataFrame) -> pd.DataFrame:
    s = screen.copy()
    s["gt20_reduction"] = s["base_gt20_cells"] - s["candidate_gt20_cells"]
    s["gt10_reduction"] = s["base_gt10_cells"] - s["candidate_gt10_cells"]
    s["balanced_adoptable"] = (
        (s["error_reduction_eok"] >= 25.0)
        & (s["candidate_gt20_cells"] <= s["base_gt20_cells"])
        & (s["candidate_gt10_cells"] <= s["base_gt10_cells"])
        & (s["worsened_cells"] <= 2)
        & (s["max_worsen_pp"] <= 5.0)
        & (s["worsen_sum_eok"] <= np.maximum(200.0, s["error_reduction_eok"] * 1.20))
    )
    s["balanced_score"] = (
        s["error_reduction_eok"] * 10
        + s["gt20_reduction"] * 600
        + s["gt10_reduction"] * 250
        - s["worsen_sum_eok"] * 1.25
        - s["worsened_cells"] * 45
    )
    return s


def select_nonoverlap(screen: pd.DataFrame) -> pd.DataFrame:
    pool = screen[screen["balanced_adoptable"]].copy()
    if pool.empty:
        return pool
    pool["code_set"] = pool["middle_codes"].map(lambda v: {x for x in str(v).split(",") if x})
    chosen: list[dict[str, object]] = []
    used: dict[tuple[str, str], set[str]] = {}
    for _, row in pool.sort_values(
        ["balanced_score", "error_reduction_eok", "worsen_sum_eok"],
        ascending=[False, False, True],
    ).iterrows():
        key = (row["city"], row["parent_code"])
        already = used.setdefault(key, set())
        if already & row["code_set"]:
            continue
        chosen.append(row.drop(labels=["code_set"], errors="ignore").to_dict())
        already.update(row["code_set"])
    return pd.DataFrame(chosen)


def apply_selected(base: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    out["phase129_balanced_predicted_gva_eok"] = out["phase129_base_predicted_gva_eok"]
    out["phase129_balanced_error_gva_eok"] = out["phase129_base_error_gva_eok"]
    out["phase129_balanced_error_rate_pct"] = out["phase129_base_error_rate_pct"]
    out["phase129_balanced_option_id"] = "phase114_precision_base"
    out["phase129_source_policy"] = "정밀화 전용: 공표 후 구조자료 사용"
    detail = detail.copy()
    detail["middle_code"] = detail["middle_code"].astype(str).str.zfill(2)
    for _, s in selected.iterrows():
        mask = (
            detail["city"].eq(s["city"])
            & detail["parent_code"].eq(s["parent_code"])
            & detail["block_id"].eq(s["block_id"])
            & detail["metric"].eq(s["metric"])
            & detail["option_id"].eq(s["option_id"])
            & np.isclose(detail["alpha"].astype(float), float(s["alpha"]))
            & np.isclose(detail["baseline_floor"].astype(float), float(s["baseline_floor"]))
        )
        for _, r in detail[mask].iterrows():
            idx = out["city"].eq(r["city"]) & out["parent_code"].eq(r["parent_code"]) & out["middle_code"].eq(r["middle_code"])
            out.loc[idx, "phase129_balanced_predicted_gva_eok"] = r["candidate_predicted_gva_eok"]
            out.loc[idx, "phase129_balanced_error_gva_eok"] = r["candidate_error_gva_eok"]
            out.loc[idx, "phase129_balanced_error_rate_pct"] = r["candidate_error_rate_pct"]
            out.loc[idx, "phase129_balanced_option_id"] = s["option_id"]
    out["phase129_balanced_reduction_vs_base_eok"] = out["phase129_base_error_gva_eok"] - out["phase129_balanced_error_gva_eok"]
    out["phase129_balanced_worse_vs_base"] = out["phase129_balanced_error_gva_eok"] > out["phase129_base_error_gva_eok"] + 1e-9
    return out


def city_summary(reg: pd.DataFrame, prefix: str) -> pd.DataFrame:
    rows = []
    for city, g in reg.groupby("city", sort=False):
        actual_sum = float(g["actual_gva_eok"].sum())
        base_err = float(g["phase129_base_error_gva_eok"].sum())
        err = float(g[f"{prefix}_error_gva_eok"].sum())
        rows.append({
            "city": city,
            "actual_sum_eok": actual_sum,
            "base_error_eok": base_err,
            "base_wape_pct": base_err / actual_sum * 100,
            f"{prefix}_error_eok": err,
            f"{prefix}_wape_pct": err / actual_sum * 100,
            "reduction_eok": base_err - err,
            "base_gt20_cells": int((g["phase129_base_error_rate_pct"] > 20).sum()),
            f"{prefix}_gt20_cells": int((g[f"{prefix}_error_rate_pct"] > 20).sum()),
            "base_gt10_cells": int((g["phase129_base_error_rate_pct"] > 10).sum()),
            f"{prefix}_gt10_cells": int((g[f"{prefix}_error_rate_pct"] > 10).sum()),
            "worsened_cells": int(g[f"{prefix}_worse_vs_base"].sum()),
            "worsen_sum_eok": float((g[f"{prefix}_error_gva_eok"] - g["phase129_base_error_gva_eok"]).clip(lower=0).sum()),
        })
    return pd.DataFrame(rows)


def compare_existing(reg129: pd.DataFrame) -> pd.DataFrame:
    strict = pd.read_csv(STRICT127, dtype={"middle_code": str})
    risk = pd.read_csv(RISK127, dtype={"middle_code": str})
    strict["middle_code"] = strict["middle_code"].astype(str).str.zfill(2)
    risk["middle_code"] = risk["middle_code"].astype(str).str.zfill(2)
    key = ["city", "parent_code", "middle_code"]
    m = reg129[key + ["actual_gva_eok", "phase129_balanced_error_gva_eok", "phase129_balanced_error_rate_pct"]].merge(
        strict[key + ["phase127_strict_error_gva_eok", "phase127_strict_error_rate_pct"]],
        on=key,
        how="left",
    ).merge(
        risk[key + ["phase127_risk_error_gva_eok", "phase127_risk_error_rate_pct"]],
        on=key,
        how="left",
    )
    rows = []
    for city, g in m.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        rows.append({
            "city": city,
            "phase127_strict_error_eok": float(g["phase127_strict_error_gva_eok"].sum()),
            "phase127_strict_wape_pct": float(g["phase127_strict_error_gva_eok"].sum()) / actual * 100,
            "phase127_strict_gt10_cells": int((g["phase127_strict_error_rate_pct"] > 10).sum()),
            "phase127_risk_error_eok": float(g["phase127_risk_error_gva_eok"].sum()),
            "phase127_risk_wape_pct": float(g["phase127_risk_error_gva_eok"].sum()) / actual * 100,
            "phase127_risk_gt10_cells": int((g["phase127_risk_error_rate_pct"] > 10).sum()),
            "phase129_error_eok": float(g["phase129_balanced_error_gva_eok"].sum()),
            "phase129_wape_pct": float(g["phase129_balanced_error_gva_eok"].sum()) / actual * 100,
            "phase129_gt10_cells": int((g["phase129_balanced_error_rate_pct"] > 10).sum()),
        })
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    labels = [c.replace("_eok", " 억원").replace("_pct", " %").replace("_", " ") for c in d.columns]
    def fmt(v: object) -> str:
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            return f"{float(v):,.2f}"
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        return str(v).replace("|", "\\|")
    body = ["| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *body])


def write_report(summary: pd.DataFrame, compare: pd.DataFrame, selected: pd.DataFrame, reg: pd.DataFrame) -> None:
    improved = reg[reg["phase129_balanced_reduction_vs_base_eok"] > 1e-9].copy()
    remaining = reg[reg["phase129_balanced_error_rate_pct"] > 10].copy()
    worsened = reg[reg["phase129_balanced_worse_vs_base"]].copy()
    REPORT.write_text("\n".join([
        "# Phase129 균형형 정밀 라우팅 실험",
        "",
        "## 목적",
        "",
        "정밀오차가 산업별로 크게 갈리는 문제를 줄이기 위해, Phase127 후보자료를 더 적극적으로 선택하되 고오차 셀 수 증가와 악화폭을 제한했다. 실제 GVA를 후보값으로 직접 대입하지 않고, 고용·산재 사업장 구조 같은 외부 활동자료 비중으로 만든 후보만 사용했다.",
        "",
        "## 기존 대비 성능",
        "",
        md_table(compare, compare.columns.tolist()),
        "",
        "## Phase114 기준 균형 선택 요약",
        "",
        md_table(summary, summary.columns.tolist()),
        "",
        "## 채택 라우팅",
        "",
        md_table(selected.sort_values("balanced_score", ascending=False), ["city","parent_code","block_id","middle_codes","metric_label","alpha","baseline_floor","error_reduction_eok","base_gt20_cells","candidate_gt20_cells","base_gt10_cells","candidate_gt10_cells","worsened_cells","worsen_sum_eok","max_worsen_pp"], n=40),
        "",
        "## 개선 셀",
        "",
        md_table(improved.sort_values("phase129_balanced_reduction_vs_base_eok", ascending=False), ["city","parent_code","middle_code","middle_label","actual_gva_eok","phase129_base_error_gva_eok","phase129_balanced_error_gva_eok","phase129_balanced_error_rate_pct","phase129_balanced_reduction_vs_base_eok","phase129_balanced_option_id"], n=50),
        "",
        "## 악화 셀 감사",
        "",
        md_table(worsened.sort_values(["city","phase129_balanced_error_gva_eok"], ascending=[True, False]), ["city","parent_code","middle_code","middle_label","actual_gva_eok","phase129_base_error_gva_eok","phase129_balanced_error_gva_eok","phase129_balanced_error_rate_pct","phase129_balanced_option_id"], n=50),
        "",
        "## 남은 10% 초과 셀",
        "",
        md_table(remaining.sort_values(["city","phase129_balanced_error_gva_eok"], ascending=[True, False]), ["city","parent_code","middle_code","middle_label","actual_gva_eok","phase129_balanced_predicted_gva_eok","phase129_balanced_error_gva_eok","phase129_balanced_error_rate_pct","phase129_balanced_option_id"], n=80),
        "",
        "## 판정",
        "",
        "균형형 라우팅은 포스터에 바로 넣기보다는 내부 정밀화 후보로 쓰는 것이 안전하다. 다만 고양·포항 모두 총오차와 10% 초과 셀 수를 추가로 줄였고, 남은 큰 오차는 협회·단체, 방송·정보서비스, 시설처리·환경, 일부 제조 소분류처럼 공개 활동자료 설명력이 낮은 군에 집중된다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_base()
    screen = mark_adoptable(pd.read_csv(SCREEN))
    detail = pd.read_csv(DETAIL, dtype={"middle_code": str})
    selected = select_nonoverlap(screen)
    reg = apply_selected(base, selected, detail)
    summary = city_summary(reg, "phase129_balanced")
    compare = compare_existing(reg)

    screen.to_csv(OUT / "phase129_candidate_screen.csv", index=False)
    selected.to_csv(OUT / "phase129_selected_routes.csv", index=False)
    reg.to_csv(OUT / "phase129_balanced_registry.csv", index=False)
    summary.to_csv(OUT / "phase129_city_summary.csv", index=False)
    compare.to_csv(OUT / "phase129_compare_existing.csv", index=False)
    write_report(summary, compare, selected, reg)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
