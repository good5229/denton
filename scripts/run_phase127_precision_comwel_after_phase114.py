#!/usr/bin/env python3
"""Phase127: COMWEL refinement on top of the Phase114 precision registry.

Phase125/126 evaluated COMWEL candidates against the strict flash path.  This
script answers a different question: can the already stronger Phase114
precision registry be improved further without damaging many cells?

The source remains a 2025-12-31 COMWEL snapshot, so candidates are labelled as
precision-only.  Two selections are reported:

1. strict: no middle-industry cell may worsen;
2. risk-budgeted: bounded worsening is allowed only if gt10/gt20 counts do not
   increase and aggregate error falls materially.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import run_phase125_comwel_workplace_refinement as p125


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase127_precision_comwel_after_phase114"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase127_precision_comwel_after_phase114.md"
BASE = DATA / "phase114_block_routed_refinement_audit" / "phase114_refined_registry.csv"


RISK_MIN_REDUCTION_EOK = 50.0
RISK_MAX_WORSENED_CELLS = 1
RISK_MAX_WORSEN_SUM_EOK = 100.0
RISK_MAX_WORSEN_PP = 8.0


def load_base() -> pd.DataFrame:
    df = pd.read_csv(BASE, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["phase127_base_predicted_gva_eok"] = df["phase114_predicted_gva_eok"]
    df["phase127_base_error_gva_eok"] = df["phase114_error_gva_eok"]
    df["phase127_base_error_rate_pct"] = df["phase114_error_rate_pct"]
    return df


def block_specs(base: pd.DataFrame) -> list[dict[str, Any]]:
    specs = []
    for (city, parent), g in base.groupby(["city", "parent_code"]):
        codes = sorted(g["middle_code"].dropna().astype(str).str.zfill(2).unique())
        if len(codes) >= 2:
            specs.append({"city": city, "parent_code": parent, "block_id": f"{parent}_all", "codes": codes, "scope": "parent"})
    for (parent, block_id), codes in p125.SUBBLOCKS.items():
        for city in sorted(base["city"].dropna().unique()):
            present = sorted(set(codes) & set(base.loc[base["city"].eq(city) & base["parent_code"].eq(parent), "middle_code"].astype(str).str.zfill(2)))
            if len(present) >= 2:
                specs.append({"city": city, "parent_code": parent, "block_id": block_id, "codes": present, "scope": "subblock"})
    return specs


def evaluate(base: pd.DataFrame, comwel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    alphas = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.33, 0.50, 0.67, 1.0]
    floors = [0.0, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80]
    metrics = [
        ("workplace_count", "사업장수"),
        ("employment_workers", "고용보험 상시근로자수"),
        ("industrial_workers", "산재보험 상시근로자수"),
    ]
    screen_rows = []
    detail_rows = []
    for spec in block_specs(base):
        city = spec["city"]
        parent = spec["parent_code"]
        codes = spec["codes"]
        g = base[base["city"].eq(city) & base["parent_code"].eq(parent) & base["middle_code"].isin(codes)].copy()
        c = comwel[comwel["city"].eq(city) & comwel["parent_code"].eq(parent) & comwel["middle_code"].isin(codes)].copy()
        if len(g) < 2 or c.empty:
            continue
        cm = g[["middle_code"]].merge(c, on="middle_code", how="left")
        old_pred = g["phase127_base_predicted_gva_eok"].to_numpy(float)
        old_err = g["phase127_base_error_gva_eok"].to_numpy(float)
        old_rate = g["phase127_base_error_rate_pct"].to_numpy(float)
        actual = g["actual_gva_eok"].to_numpy(float)
        total = float(old_pred.sum())
        if total <= 0:
            continue
        base_share = old_pred / total
        for metric, metric_label in metrics:
            values = pd.to_numeric(cm[metric], errors="coerce").fillna(0.0).to_numpy(float)
            if values.sum() <= 0 or (values > 0).sum() < 2:
                continue
            source_share = values / values.sum()
            for floor in floors:
                safe_share = floor * base_share + (1 - floor) * source_share
                safe_share = safe_share / safe_share.sum()
                source_pred = safe_share * total
                for alpha in alphas:
                    pred = (1 - alpha) * old_pred + alpha * source_pred
                    err = np.abs(pred - actual)
                    rate = np.where(actual > 0, err / actual * 100, np.nan)
                    delta = err - old_err
                    reduction = float(old_err.sum() - err.sum())
                    row = {
                        "city": city,
                        "parent_code": parent,
                        "block_id": spec["block_id"],
                        "scope": spec["scope"],
                        "middle_codes": ",".join(codes),
                        "metric": metric,
                        "metric_label": metric_label,
                        "option_id": f"phase127_comwel_{metric}_{spec['block_id']}",
                        "alpha": alpha,
                        "baseline_floor": floor,
                        "base_error_eok": float(old_err.sum()),
                        "candidate_error_eok": float(err.sum()),
                        "error_reduction_eok": reduction,
                        "base_gt20_cells": int((old_rate > 20).sum()),
                        "candidate_gt20_cells": int((rate > 20).sum()),
                        "base_gt10_cells": int((old_rate > 10).sum()),
                        "candidate_gt10_cells": int((rate > 10).sum()),
                        "worsened_cells": int((delta > 1e-9).sum()),
                        "worsen_sum_eok": float(np.maximum(delta, 0).sum()),
                        "max_worsen_pp": float(np.nanmax(rate - old_rate)),
                    }
                    row["strict_adoptable"] = (
                        reduction > 1e-9
                        and row["worsened_cells"] == 0
                        and row["candidate_gt20_cells"] <= row["base_gt20_cells"]
                        and row["candidate_gt10_cells"] <= row["base_gt10_cells"]
                    )
                    row["risk_adoptable"] = (
                        reduction >= RISK_MIN_REDUCTION_EOK
                        and row["candidate_gt20_cells"] <= row["base_gt20_cells"]
                        and row["candidate_gt10_cells"] <= row["base_gt10_cells"]
                        and row["worsened_cells"] <= RISK_MAX_WORSENED_CELLS
                        and row["worsen_sum_eok"] <= RISK_MAX_WORSEN_SUM_EOK
                        and row["max_worsen_pp"] <= RISK_MAX_WORSEN_PP
                    )
                    screen_rows.append(row)
                    d = g[[
                        "city",
                        "parent_code",
                        "middle_code",
                        "middle_label",
                        "actual_gva_eok",
                        "phase127_base_predicted_gva_eok",
                        "phase127_base_error_gva_eok",
                        "phase127_base_error_rate_pct",
                    ]].copy()
                    d["block_id"] = spec["block_id"]
                    d["metric"] = metric
                    d["option_id"] = row["option_id"]
                    d["alpha"] = alpha
                    d["baseline_floor"] = floor
                    d["candidate_predicted_gva_eok"] = pred
                    d["candidate_error_gva_eok"] = err
                    d["candidate_error_rate_pct"] = rate
                    d["candidate_worse"] = delta > 1e-9
                    detail_rows.append(d)
    screen = pd.DataFrame(screen_rows)
    detail = pd.concat(detail_rows, ignore_index=True) if detail_rows else pd.DataFrame()
    if not screen.empty:
        screen = screen.sort_values(["strict_adoptable", "risk_adoptable", "error_reduction_eok"], ascending=[False, False, False])
    return screen, detail


def select_nonoverlap(screen: pd.DataFrame, flag: str) -> pd.DataFrame:
    pool = screen[screen[flag]].copy()
    if pool.empty:
        return pool
    pool["code_set"] = pool["middle_codes"].map(lambda s: {x for x in str(s).split(",") if x})
    if flag == "risk_adoptable":
        pool["gt20_reduction"] = pool["base_gt20_cells"] - pool["candidate_gt20_cells"]
        pool["gt10_reduction"] = pool["base_gt10_cells"] - pool["candidate_gt10_cells"]
        pool["score"] = pool["gt20_reduction"] * 100000 + pool["gt10_reduction"] * 10000 + pool["error_reduction_eok"] - pool["worsen_sum_eok"] * 2
        sort_cols = ["score", "error_reduction_eok", "worsen_sum_eok"]
        asc = [False, False, True]
    else:
        sort_cols = ["error_reduction_eok", "candidate_gt20_cells", "candidate_gt10_cells"]
        asc = [False, True, True]
    chosen = []
    used: dict[tuple[str, str], set[str]] = {}
    for _, r in pool.sort_values(sort_cols, ascending=asc).iterrows():
        key = (r.city, r.parent_code)
        already = used.setdefault(key, set())
        if already & r.code_set:
            continue
        chosen.append(r.drop(labels=["code_set"], errors="ignore").to_dict())
        already.update(r.code_set)
    return pd.DataFrame(chosen)


def apply_selected(base: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = base.copy()
    out[f"{prefix}_predicted_gva_eok"] = out["phase127_base_predicted_gva_eok"]
    out[f"{prefix}_error_gva_eok"] = out["phase127_base_error_gva_eok"]
    out[f"{prefix}_error_rate_pct"] = out["phase127_base_error_rate_pct"]
    out[f"{prefix}_option_id"] = "phase114_precision_base"
    for _, s in selected.iterrows():
        m = (
            detail["city"].eq(s.city)
            & detail["parent_code"].eq(s.parent_code)
            & detail["block_id"].eq(s.block_id)
            & detail["metric"].eq(s.metric)
            & detail["option_id"].eq(s.option_id)
            & np.isclose(detail["alpha"].astype(float), float(s.alpha))
            & np.isclose(detail["baseline_floor"].astype(float), float(s.baseline_floor))
        )
        for _, r in detail[m].iterrows():
            idx = out["city"].eq(r.city) & out["parent_code"].eq(r.parent_code) & out["middle_code"].eq(r.middle_code)
            out.loc[idx, f"{prefix}_predicted_gva_eok"] = r.candidate_predicted_gva_eok
            out.loc[idx, f"{prefix}_error_gva_eok"] = r.candidate_error_gva_eok
            out.loc[idx, f"{prefix}_error_rate_pct"] = r.candidate_error_rate_pct
            out.loc[idx, f"{prefix}_option_id"] = s.option_id
    out[f"{prefix}_reduction_vs_base_eok"] = out["phase127_base_error_gva_eok"] - out[f"{prefix}_error_gva_eok"]
    out[f"{prefix}_worse_vs_base"] = out[f"{prefix}_error_gva_eok"] > out["phase127_base_error_gva_eok"] + 1e-9
    return out


def summary(reg: pd.DataFrame, pred_prefix: str) -> pd.DataFrame:
    rows = []
    for city, g in reg.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        base = float(g["phase127_base_error_gva_eok"].sum())
        err = float(g[f"{pred_prefix}_error_gva_eok"].sum())
        rows.append({
            "city": city,
            "base_error_eok": base,
            "base_wape_pct": base / actual * 100,
            f"{pred_prefix}_error_eok": err,
            f"{pred_prefix}_wape_pct": err / actual * 100,
            "reduction_eok": base - err,
            "base_gt20_cells": int((g["phase127_base_error_rate_pct"] > 20).sum()),
            f"{pred_prefix}_gt20_cells": int((g[f"{pred_prefix}_error_rate_pct"] > 20).sum()),
            "base_gt10_cells": int((g["phase127_base_error_rate_pct"] > 10).sum()),
            f"{pred_prefix}_gt10_cells": int((g[f"{pred_prefix}_error_rate_pct"] > 10).sum()),
            "worsened_cells": int(g[f"{pred_prefix}_worse_vs_base"].sum()),
            "worsen_sum_eok": float((g[f"{pred_prefix}_error_gva_eok"] - g["phase127_base_error_gva_eok"]).clip(lower=0).sum()),
        })
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    def fmt(x: object) -> str:
        if pd.isna(x):
            return ""
        if isinstance(x, (float, np.floating)):
            return f"{float(x):,.2f}"
        if isinstance(x, (int, np.integer)):
            return f"{int(x):,}"
        return str(x).replace("|", "\\|")
    labels = [c.replace("_eok", " 억원").replace("_pct", " %").replace("_", " ") for c in d.columns]
    rows = [[fmt(x) for x in row] for row in d.to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *["| " + " | ".join(r) + " |" for r in rows]])


def write_report(strict_sum: pd.DataFrame, risk_sum: pd.DataFrame, strict_sel: pd.DataFrame, risk_sel: pd.DataFrame, risk_reg: pd.DataFrame) -> None:
    remaining = risk_reg[risk_reg["phase127_risk_error_rate_pct"] > 10].copy()
    improved = risk_reg[risk_reg["phase127_risk_reduction_vs_base_eok"] > 1e-9].copy()
    REPORT.write_text("\n".join([
        "# Phase127 Phase114 정밀 기준 COMWEL 재평가",
        "",
        "## 목적",
        "",
        "COMWEL 사업장 자료를 속보 경로가 아니라 Phase114 정밀 기준 위에서 다시 평가했다. 자료 시점상 정밀화 전용 후보로만 해석한다.",
        "",
        "## 무악화 선택 결과",
        "",
        md_table(strict_sum, strict_sum.columns.tolist()),
        "",
        "## 리스크 예산 선택 결과",
        "",
        md_table(risk_sum, risk_sum.columns.tolist()),
        "",
        "## 무악화 채택 후보",
        "",
        md_table(strict_sel, ["city","parent_code","block_id","middle_codes","metric_label","alpha","baseline_floor","error_reduction_eok","base_gt10_cells","candidate_gt10_cells","worsened_cells"], n=30),
        "",
        "## 리스크 예산 채택 후보",
        "",
        md_table(risk_sel, ["city","parent_code","block_id","middle_codes","metric_label","alpha","baseline_floor","error_reduction_eok","base_gt20_cells","candidate_gt20_cells","base_gt10_cells","candidate_gt10_cells","worsened_cells","worsen_sum_eok","max_worsen_pp"], n=30),
        "",
        "## 리스크 기준 개선 셀",
        "",
        md_table(improved.sort_values("phase127_risk_reduction_vs_base_eok", ascending=False), ["city","parent_code","middle_code","middle_label","actual_gva_eok","phase127_base_error_gva_eok","phase127_risk_error_gva_eok","phase127_risk_error_rate_pct","phase127_risk_reduction_vs_base_eok","phase127_risk_option_id"], n=40),
        "",
        "## 남은 10% 초과 셀",
        "",
        md_table(remaining.sort_values(["city","phase127_risk_error_gva_eok"], ascending=[True,False]), ["city","parent_code","middle_code","middle_label","actual_gva_eok","phase127_risk_predicted_gva_eok","phase127_risk_error_gva_eok","phase127_risk_error_rate_pct","phase127_risk_option_id"], n=80),
        "",
        "## 판정",
        "",
        "Phase114 정밀 기준은 이미 강해서 COMWEL의 추가 기여는 제한적이다. 무악화 후보는 공모전 최종 성능에 넣어도 비교적 안전하지만, 리스크 예산 후보는 일부 셀 악화를 동반하므로 내부 개선 후보로만 분리하는 편이 좋다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_base()
    comwel = p125.load_comwel()
    screen, detail = evaluate(base, comwel)
    strict_sel = select_nonoverlap(screen, "strict_adoptable")
    strict_reg = apply_selected(base, strict_sel, detail, "phase127_strict")
    risk_sel = select_nonoverlap(screen, "risk_adoptable")
    risk_reg = apply_selected(base, risk_sel, detail, "phase127_risk")
    strict_sum = summary(strict_reg, "phase127_strict")
    risk_sum = summary(risk_reg, "phase127_risk")

    screen.to_csv(OUT / "phase127_candidate_screen.csv", index=False)
    detail.to_csv(OUT / "phase127_candidate_detail.csv", index=False)
    strict_sel.to_csv(OUT / "phase127_strict_selected.csv", index=False)
    strict_reg.to_csv(OUT / "phase127_strict_registry.csv", index=False)
    strict_sum.to_csv(OUT / "phase127_strict_city_summary.csv", index=False)
    risk_sel.to_csv(OUT / "phase127_risk_selected.csv", index=False)
    risk_reg.to_csv(OUT / "phase127_risk_registry.csv", index=False)
    risk_sum.to_csv(OUT / "phase127_risk_city_summary.csv", index=False)
    write_report(strict_sum, risk_sum, strict_sel, risk_sel, risk_reg)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
