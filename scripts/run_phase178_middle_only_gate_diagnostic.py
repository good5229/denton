#!/usr/bin/env python3
"""Phase178: middle-only external gate diagnostic.

Phase177 removed all worsening versus Phase124 by requiring both parent and
middle gates.  This phase asks whether the parent gate is too conservative for
some residual-heavy middle industries.  It applies peer estimates when the
middle industry itself passes external LOO safety, regardless of the parent
gate.  H00 remains governed by the port-activity gate.

This is an operational-candidate diagnostic: target actuals are used only for
audit, never for route selection.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUT = DATA / "phase178_middle_only_gate_diagnostic"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase178_middle_only_gate_diagnostic.md"

PHASE124 = DATA / "phase124_pps_subblock_no_worse/phase124_registry.csv"
PHASE162_TARGET = DATA / "phase162_similar_peer_prior_routing/phase162_goyang_pohang_similar_peer_registry.csv"
PHASE162_EXTERNAL = DATA / "phase162_similar_peer_prior_routing/phase162_external_similar_peer_screen_detail.csv"
PHASE162_SELECTED = DATA / "phase162_similar_peer_prior_routing/phase162_selected_params.csv"
PHASE173 = DATA / "phase173_port_activity_gated_h50_registry/phase173_port_gated_h50_registry.csv"
PHASE177 = DATA / "phase177_middle_safe_peer_port_gate/phase177_middle_safe_peer_port_registry.csv"

MIN_REDUCTION_PP = 0.0
MIN_IMPROVED_REGION_SHARE = 0.60
REQUIRE_GT20_NOT_WORSE = True


def md_table(df: pd.DataFrame, digits: int = 2, max_rows: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if max_rows is not None and len(view) > max_rows:
        view = view.head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
    view = view.fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[c].replace("|", "\\|") for c in view.columns) + " |")
    if max_rows is not None and len(df) > max_rows:
        lines.append(f"\n_상위 {max_rows}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def build_middle_gate() -> pd.DataFrame:
    ext = pd.read_csv(PHASE162_EXTERNAL)
    selected = pd.read_csv(PHASE162_SELECTED)
    pieces = []
    for s in selected[selected["selected"].fillna(False).astype(bool)].itertuples(index=False):
        g = ext[
            ext["parent_code"].astype(str).eq(str(s.parent_code))
            & ext["k"].astype(int).eq(int(s.k))
            & np.isclose(ext["alpha"].astype(float), float(s.alpha))
        ].copy()
        if not g.empty:
            pieces.append(g)
    ext = pd.concat(pieces, ignore_index=True)
    ext["baseline_error_eok"] = (ext["baseline_share"] * ext["parent_gva_eok"] - ext["actual_gva_eok"]).abs()
    rows = []
    for (parent, div), g in ext.groupby(["parent_code", "division_code"], sort=False):
        actual = float(g["actual_gva_eok"].sum())
        base = float(g["baseline_error_eok"].sum())
        cand = float(g["candidate_error_eok"].sum())
        base_wape = base / actual * 100 if actual else np.nan
        cand_wape = cand / actual * 100 if actual else np.nan
        red = base_wape - cand_wape
        improved = float((g["candidate_error_eok"] < g["baseline_error_eok"] - 1e-9).mean())
        base_gt20 = float((g["error_rate_pct"] > 20).mean())
        cand_gt20 = float((g["candidate_error_rate_pct"] > 20).mean())
        pass_gate = (
            pd.notna(red)
            and red > MIN_REDUCTION_PP
            and improved >= MIN_IMPROVED_REGION_SHARE
            and (cand_gt20 <= base_gt20 if REQUIRE_GT20_NOT_WORSE else True)
        )
        rows.append(
            {
                "parent_code": str(parent),
                "middle_code": int(div),
                "middle_label_external": g["division_name"].iloc[0],
                "external_regions": int(g["region_key"].nunique()),
                "external_baseline_wape_pct": base_wape,
                "external_candidate_wape_pct": cand_wape,
                "external_reduction_pp": red,
                "external_improved_region_share": improved,
                "external_baseline_gt20_share": base_gt20,
                "external_candidate_gt20_share": cand_gt20,
                "middle_gate_pass": bool(pass_gate),
            }
        )
    return pd.DataFrame(rows)


def add_error(df: pd.DataFrame, pred_col: str, prefix: str) -> pd.DataFrame:
    out = df.copy()
    out[f"{prefix}_predicted_gva_eok"] = out[pred_col].astype(float)
    out[f"{prefix}_error_gva_eok"] = (out[f"{prefix}_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out[f"{prefix}_error_rate_pct"] = out[f"{prefix}_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    return out


def summary(df: pd.DataFrame, prefix: str, label: str) -> pd.DataFrame:
    err = f"{prefix}_error_gva_eok"
    rate = f"{prefix}_error_rate_pct"
    rows = []
    for city, g in df.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        error = float(g[err].sum())
        rows.append(
            {
                "candidate": label,
                "city": city,
                "cells": len(g),
                "actual_sum_eok": actual,
                "error_sum_eok": error,
                "wape_pct": error / actual * 100 if actual else np.nan,
                "gt10_cells": int((g[rate] > 10).sum()),
                "gt20_cells": int((g[rate] > 20).sum()),
                "gt50_cells": int((g[rate] > 50).sum()),
            }
        )
    actual = float(df["actual_gva_eok"].sum())
    error = float(df[err].sum())
    rows.append(
        {
            "candidate": label,
            "city": "합계",
            "cells": len(df),
            "actual_sum_eok": actual,
            "error_sum_eok": error,
            "wape_pct": error / actual * 100 if actual else np.nan,
            "gt10_cells": int((df[rate] > 10).sum()),
            "gt20_cells": int((df[rate] > 20).sum()),
            "gt50_cells": int((df[rate] > 50).sum()),
        }
    )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p124 = pd.read_csv(PHASE124)
    p162 = pd.read_csv(PHASE162_TARGET)
    p173 = pd.read_csv(PHASE173)
    p177 = pd.read_csv(PHASE177)
    gate = build_middle_gate()
    key = ["city", "parent_code", "middle_code"]

    reg = p124.copy()
    reg["phase178_predicted_gva_eok"] = reg["phase124_predicted_gva_eok"].astype(float)
    reg["phase178_route"] = "기준 유지"
    peer = p162[key + ["phase162_predicted_gva_eok", "phase162_peer_regions", "phase162_peer_mean_l1_distance"]].copy()
    g = reg[key].merge(gate[["parent_code", "middle_code", "middle_gate_pass"]], on=["parent_code", "middle_code"], how="left").merge(peer, on=key, how="left")
    mid_ok = (
        g["parent_code"].ne("H00")
        & g["middle_gate_pass"].fillna(False).astype(bool)
        & g["phase162_predicted_gva_eok"].notna()
    )
    reg.loc[mid_ok.values, "phase178_predicted_gva_eok"] = g.loc[mid_ok, "phase162_predicted_gva_eok"].to_numpy()
    reg.loc[mid_ok.values, "phase178_route"] = "외부검증 통과 중분류 독립 peer 배분"

    h = reg[key].merge(
        p173[key + ["phase173_port_gated_h50_predicted_gva_eok"]],
        on=key,
        how="left",
    )
    h00 = h["parent_code"].eq("H00") & h["phase173_port_gated_h50_predicted_gva_eok"].notna()
    reg.loc[h00.values, "phase178_predicted_gva_eok"] = h.loc[h00, "phase173_port_gated_h50_predicted_gva_eok"].to_numpy()
    reg.loc[h00.values, "phase178_route"] = "항만물동량 조건부 운수·창고 배분"

    reg["phase178_error_gva_eok"] = (reg["phase178_predicted_gva_eok"] - reg["actual_gva_eok"]).abs()
    reg["phase178_error_rate_pct"] = reg["phase178_error_gva_eok"] / reg["actual_gva_eok"].abs() * 100
    reg["phase178_delta_vs_phase124_eok"] = reg["phase178_error_gva_eok"] - reg["phase124_error_gva_eok"]
    reg["phase178_delta_vs_phase177_eok"] = reg["phase178_error_gva_eok"] - p177["phase177_error_gva_eok"].to_numpy()
    reg["phase178_worsened_vs_phase124"] = reg["phase178_delta_vs_phase124_eok"] > 1e-8

    base = add_error(p124, "phase124_predicted_gva_eok", "phase124")
    p177_eval = p177.rename(
        columns={
            "phase177_predicted_gva_eok": "phase177_eval_predicted_gva_eok",
            "phase177_error_gva_eok": "phase177_eval_error_gva_eok",
            "phase177_error_rate_pct": "phase177_eval_error_rate_pct",
        }
    )
    summ = pd.concat(
        [
            summary(base, "phase124", "Phase124 기준선"),
            summary(p177_eval, "phase177_eval", "Phase177 중분류 안전 게이트"),
            summary(reg, "phase178", "Phase178 중분류 독립 게이트"),
        ],
        ignore_index=True,
    )
    parent = (
        reg.groupby(["city", "parent_code"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            phase124_error_eok=("phase124_error_gva_eok", "sum"),
            phase177_error_eok=("phase178_error_gva_eok", "sum"),
            worsened_cells=("phase178_worsened_vs_phase124", "sum"),
            gt20_cells=("phase178_error_rate_pct", lambda s: int((s > 20).sum())),
            routes=("phase178_route", lambda s: ", ".join(sorted(set(s)))),
        )
    )
    parent["phase124_wape_pct"] = parent["phase124_error_eok"] / parent["actual_sum_eok"] * 100
    parent["phase178_wape_pct"] = parent["phase177_error_eok"] / parent["actual_sum_eok"] * 100
    parent["reduction_eok"] = parent["phase124_error_eok"] - parent["phase177_error_eok"]
    parent = parent.sort_values(["city", "reduction_eok"], ascending=[True, False])

    applied = reg[reg["phase178_route"].ne("기준 유지")].copy().sort_values("phase178_delta_vs_phase124_eok")
    worsened = reg[reg["phase178_worsened_vs_phase124"]].copy().sort_values("phase178_delta_vs_phase124_eok", ascending=False)
    residual = reg[reg["phase178_error_rate_pct"] > 20].copy().sort_values("phase178_error_gva_eok", ascending=False)

    reg.to_csv(OUT / "phase178_middle_only_gate_registry.csv", index=False, encoding="utf-8-sig")
    gate.to_csv(OUT / "phase178_middle_external_gate.csv", index=False, encoding="utf-8-sig")
    summ.to_csv(OUT / "phase178_summary.csv", index=False, encoding="utf-8-sig")
    parent.to_csv(OUT / "phase178_parent_audit.csv", index=False, encoding="utf-8-sig")
    applied.to_csv(OUT / "phase178_applied_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUT / "phase178_worsened_cells.csv", index=False, encoding="utf-8-sig")
    residual.to_csv(OUT / "phase178_residual_gt20.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "phase": "phase178_middle_only_gate_diagnostic",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "target_actual_use": "audit only",
                "decision_rule": "Apply non-H00 peer route when middle-level external LOO gate passes, without parent gate; H00 uses Phase173 port gate.",
                "outputs": {
                    "summary_rows": len(summ),
                    "applied_cells": len(applied),
                    "worsened_cells_vs_phase124": len(worsened),
                    "residual_gt20_cells": len(residual),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    REPORT.write_text(
        f"""# Phase178 중분류 독립 외부게이트 진단

## 목적

Phase177은 기준선 대비 악화 셀을 0개로 줄였지만, 상위산업 게이트가 막힌 MN0·ERS·J00 일부 중분류를 그대로 남겼다. 이번 단계는 상위산업 전체가 불안정하더라도 외부 10개 시군구에서 **중분류 자체가 안정적으로 개선**된 경우에는 그 중분류만 독립 적용할 수 있는지 점검한다.

타깃 actual은 적용 판단에 쓰지 않고, 사후 감사에만 사용한다.

## 전체 성능

{md_table(summ[["candidate","city","actual_sum_eok","error_sum_eok","wape_pct","gt10_cells","gt20_cells","gt50_cells"]], 2)}

## 상위산업별 감사

{md_table(parent[["city","parent_code","routes","actual_sum_eok","phase124_error_eok","phase177_error_eok","phase124_wape_pct","phase178_wape_pct","reduction_eok","worsened_cells","gt20_cells"]].head(20), 2)}

## 적용 셀 상위

{md_table(applied[["city","parent_code","middle_code","middle_label","actual_gva_eok","phase124_error_gva_eok","phase178_error_gva_eok","phase178_error_rate_pct","phase178_delta_vs_phase124_eok","phase178_route"]].head(30).rename(columns={
    "city":"도시",
    "parent_code":"상위산업",
    "middle_code":"중분류",
    "middle_label":"업종명",
    "actual_gva_eok":"실제 GVA(억원)",
    "phase124_error_gva_eok":"기준 오차(억원)",
    "phase178_error_gva_eok":"Phase178 오차(억원)",
    "phase178_error_rate_pct":"Phase178 오차율(%)",
    "phase178_delta_vs_phase124_eok":"오차 증감(억원)",
    "phase178_route":"적용 경로",
}), 2)}

## 기준선 대비 악화 셀

{md_table(worsened[["city","parent_code","middle_code","middle_label","actual_gva_eok","phase124_error_gva_eok","phase178_error_gva_eok","phase178_error_rate_pct","phase178_delta_vs_phase124_eok","phase178_route"]].head(30).rename(columns={
    "city":"도시",
    "parent_code":"상위산업",
    "middle_code":"중분류",
    "middle_label":"업종명",
    "actual_gva_eok":"실제 GVA(억원)",
    "phase124_error_gva_eok":"기준 오차(억원)",
    "phase178_error_gva_eok":"Phase178 오차(억원)",
    "phase178_error_rate_pct":"Phase178 오차율(%)",
    "phase178_delta_vs_phase124_eok":"오차 증감(억원)",
    "phase178_route":"적용 경로",
}), 2)}

## 남은 20% 초과 셀

{md_table(residual[["city","parent_code","middle_code","middle_label","actual_gva_eok","phase178_predicted_gva_eok","phase178_error_gva_eok","phase178_error_rate_pct","phase178_route"]].head(30).rename(columns={
    "city":"도시",
    "parent_code":"상위산업",
    "middle_code":"중분류",
    "middle_label":"업종명",
    "actual_gva_eok":"실제 GVA(억원)",
    "phase178_predicted_gva_eok":"추정 GVA(억원)",
    "phase178_error_gva_eok":"오차(억원)",
    "phase178_error_rate_pct":"오차율(%)",
    "phase178_route":"적용 경로",
}), 2, 30)}

## 판정

1. Phase178은 상위산업 게이트를 우회해 잔여오차를 더 낮출 수 있는지 보는 공격적 진단이다.
2. 기준선 대비 악화 셀이 발생하면 운영 채택은 Phase177보다 위험하다.
3. 악화가 없거나 작고 WAPE 감소가 크다면, 다음 단계에서는 “중분류 독립 게이트 + 악화위험 사전점수”로 운영 후보를 다듬는다.
4. 여전히 큰 오차가 남는 중분류는 peer 구조가 아니라 직접 활동자료 수집 대상이다.
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
