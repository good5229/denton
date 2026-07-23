#!/usr/bin/env python3
"""Phase126: risk-budgeted COMWEL candidate adoption.

Phase125 used a strict no-worse rule.  That is safe, but it rejects candidates
that reduce large aggregate gaps while causing a small and bounded worsening in
one middle-industry cell.  This phase tests a second, explicitly labelled
selection layer:

* start from Phase125 registry;
* use Phase125 candidate details, which all preserve the candidate block total;
* adopt only non-overlapping candidates that satisfy a numeric risk budget.

This remains a refinement/structure experiment because the COMWEL source is a
2025-12-31 snapshot in the local filename.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "processed" / "phase125_comwel_workplace_refinement"
OUT = ROOT / "data" / "processed" / "phase126_risk_budgeted_comwel_selection"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase126_risk_budgeted_comwel_selection.md"


MIN_REDUCTION_EOK = 100.0
MAX_WORSENED_CELLS = 1
MAX_WORSEN_SUM_EOK = 200.0
MAX_WORSEN_PP = 12.0


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    reg = pd.read_csv(IN / "phase125_registry.csv", dtype={"middle_code": str})
    reg["middle_code"] = reg["middle_code"].astype(str).str.zfill(2)
    screen = pd.read_csv(IN / "phase125_candidate_screen.csv")
    detail = pd.read_csv(IN / "phase125_candidate_detail.csv", dtype={"middle_code": str})
    detail["middle_code"] = detail["middle_code"].astype(str).str.zfill(2)
    selected125 = pd.read_csv(IN / "phase125_selected_blocks.csv")
    return reg, screen, detail, selected125


def code_set(s: object) -> set[str]:
    return {str(x).zfill(2) for x in str(s).split(",") if str(x).strip()}


def select_candidates(screen: pd.DataFrame, selected125: pd.DataFrame) -> pd.DataFrame:
    s = screen.copy()
    s["code_set"] = s["middle_codes"].map(code_set)
    s["risk_budget_pass"] = (
        (s["incremental_reduction_eok"] >= MIN_REDUCTION_EOK)
        & (s["candidate_gt20_cells"] <= s["phase124_gt20_cells"])
        & (s["candidate_gt10_cells"] <= s["phase124_gt10_cells"])
        & (s["worsened_cells"] <= MAX_WORSENED_CELLS)
        & (s["worsen_sum_eok"] <= MAX_WORSEN_SUM_EOK)
        & (s["max_worsen_pp"] <= MAX_WORSEN_PP)
    )
    pool = s[s["risk_budget_pass"]].copy()
    if pool.empty:
        return pool.drop(columns=["code_set"], errors="ignore")

    # Phase125 already changed these blocks without worsening.  Do not override
    # overlapping middle codes unless the exact block was not selected.
    used: dict[tuple[str, str], set[str]] = {}
    for _, r in selected125.iterrows():
        used.setdefault((r.city, r.parent_code), set()).update(code_set(r.middle_codes))

    chosen = []
    pool["gt20_reduction"] = pool["phase124_gt20_cells"] - pool["candidate_gt20_cells"]
    pool["gt10_reduction"] = pool["phase124_gt10_cells"] - pool["candidate_gt10_cells"]
    pool["net_score"] = (
        pool["gt20_reduction"] * 100000
        + pool["gt10_reduction"] * 10000
        + pool["incremental_reduction_eok"]
        - pool["worsen_sum_eok"] * 2
    )
    pool = pool.sort_values(
        ["net_score", "incremental_reduction_eok", "worsen_sum_eok"],
        ascending=[False, False, True],
    )
    for _, r in pool.iterrows():
        key = (r.city, r.parent_code)
        already = used.setdefault(key, set())
        codes = set(r.code_set)
        if already & codes:
            continue
        chosen.append(r.to_dict())
        already.update(codes)

    out = pd.DataFrame(chosen)
    return out.drop(columns=["code_set"], errors="ignore")


def apply_selected(reg: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    out = reg.copy()
    out["phase126_predicted_gva_eok"] = out["phase125_predicted_gva_eok"]
    out["phase126_error_gva_eok"] = out["phase125_error_gva_eok"]
    out["phase126_error_rate_pct"] = out["phase125_error_rate_pct"]
    out["phase126_option_id"] = out["phase125_option_id"]

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
            out.loc[idx, "phase126_predicted_gva_eok"] = r.candidate_predicted_gva_eok
            out.loc[idx, "phase126_error_gva_eok"] = r.candidate_error_gva_eok
            out.loc[idx, "phase126_error_rate_pct"] = r.candidate_error_rate_pct
            out.loc[idx, "phase126_option_id"] = s.option_id

    out["phase126_incremental_reduction_vs_phase125_eok"] = out["phase125_error_gva_eok"] - out["phase126_error_gva_eok"]
    out["phase126_total_reduction_vs_phase124_eok"] = out["phase124_error_gva_eok"] - out["phase126_error_gva_eok"]
    out["phase126_worse_vs_phase125"] = out["phase126_error_gva_eok"] > out["phase125_error_gva_eok"] + 1e-9
    return out


def city_summary(reg: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in reg.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        p124 = float(g["phase124_error_gva_eok"].sum())
        p125 = float(g["phase125_error_gva_eok"].sum())
        p126 = float(g["phase126_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "phase124_error_eok": p124,
                "phase124_wape_pct": p124 / actual * 100,
                "phase125_error_eok": p125,
                "phase125_wape_pct": p125 / actual * 100,
                "phase126_error_eok": p126,
                "phase126_wape_pct": p126 / actual * 100,
                "reduction_vs_phase125_eok": p125 - p126,
                "reduction_vs_phase124_eok": p124 - p126,
                "phase125_gt20_cells": int((g["phase125_error_rate_pct"] > 20).sum()),
                "phase126_gt20_cells": int((g["phase126_error_rate_pct"] > 20).sum()),
                "phase125_gt10_cells": int((g["phase125_error_rate_pct"] > 10).sum()),
                "phase126_gt10_cells": int((g["phase126_error_rate_pct"] > 10).sum()),
                "worsened_vs_phase125_cells": int(g["phase126_worse_vs_phase125"].sum()),
                "worsened_vs_phase125_sum_eok": float(
                    (g["phase126_error_gva_eok"] - g["phase125_error_gva_eok"]).clip(lower=0).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n is not None:
        d = d.head(n)
    labels = []
    for c in cols:
        labels.append(
            c.replace("_eok", " 억원")
            .replace("_pct", " %")
            .replace("_", " ")
        )
    d.columns = labels

    def fmt(v: object) -> str:
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            return f"{float(v):,.2f}"
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        return str(v).replace("|", "\\|")

    rows = [[fmt(x) for x in row] for row in d.to_numpy()]
    header = "| " + " | ".join(labels) + " |"
    align = "| " + " | ".join(["---"] * len(labels)) + " |"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([header, align, *body])


def write_report(summary: pd.DataFrame, selected: pd.DataFrame, changed: pd.DataFrame, remaining: pd.DataFrame) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase126 리스크 예산형 COMWEL 후보 채택 실험",
        "",
        "## 목적",
        "",
        "Phase125의 무악화 기준에서 탈락한 후보 중, 총오차와 20% 초과 셀을 줄이면서 악화폭이 수치적으로 작게 통제되는 후보만 제한적으로 채택했다.",
        "",
        "COMWEL 자료는 2025-12-31 사업장 스냅샷이므로 이 단계 역시 **정밀화/구조 개선 후보**이며 속보성 지표로 주장하지 않는다.",
        "",
        "## 리스크 예산",
        "",
        f"- 후보 블록 총오차 감소: {MIN_REDUCTION_EOK:,.0f}억원 이상",
        "- 20% 초과 셀 수 증가 금지",
        "- 10% 초과 셀 수 증가 금지",
        f"- 악화 셀: {MAX_WORSENED_CELLS}개 이하",
        f"- 악화합계: {MAX_WORSEN_SUM_EOK:,.0f}억원 이하",
        f"- 최대 악화: {MAX_WORSEN_PP:,.0f}%p 이하",
        "",
        "## 도시별 성능",
        "",
        md_table(
            summary,
            [
                "city",
                "phase124_error_eok",
                "phase124_wape_pct",
                "phase125_error_eok",
                "phase125_wape_pct",
                "phase126_error_eok",
                "phase126_wape_pct",
                "reduction_vs_phase125_eok",
                "phase125_gt20_cells",
                "phase126_gt20_cells",
                "worsened_vs_phase125_cells",
                "worsened_vs_phase125_sum_eok",
            ],
        ),
        "",
        "## 추가 채택 후보",
        "",
        md_table(
            selected,
            [
                "city",
                "parent_code",
                "block_id",
                "middle_codes",
                "metric_label",
                "alpha",
                "baseline_floor",
                "incremental_reduction_eok",
                "phase124_gt20_cells",
                "candidate_gt20_cells",
                "worsened_cells",
                "worsen_sum_eok",
                "max_worsen_pp",
            ],
        ),
        "",
        "## 변화 중분류",
        "",
        md_table(
            changed.sort_values("phase126_incremental_reduction_vs_phase125_eok", ascending=False),
            [
                "city",
                "parent_code",
                "middle_code",
                "middle_label",
                "actual_gva_eok",
                "phase125_error_gva_eok",
                "phase126_error_gva_eok",
                "phase126_error_rate_pct",
                "phase126_incremental_reduction_vs_phase125_eok",
                "phase126_option_id",
            ],
            n=40,
        ),
        "",
        "## 남은 20% 초과 중분류",
        "",
        md_table(
            remaining.sort_values(["city", "phase126_error_gva_eok"], ascending=[True, False]),
            [
                "city",
                "parent_code",
                "middle_code",
                "middle_label",
                "actual_gva_eok",
                "phase126_predicted_gva_eok",
                "phase126_error_gva_eok",
                "phase126_error_rate_pct",
                "phase126_option_id",
            ],
            n=80,
        ),
        "",
        "## 판정",
        "",
        "리스크 예산형 선택은 무악화 방식보다 포항 제조업 일부를 더 개선할 수 있지만, 고양·포항 전체 취약 업종을 20% 이내로 끌어내리기에는 부족하다. 다음 단계는 남은 대형 오차 업종별 직접 활동자료 확보 또는 도시 특화 보조자료가 필요하다.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reg, screen, detail, selected125 = read_inputs()
    selected = select_candidates(screen, selected125)
    final = apply_selected(reg, selected, detail)
    summary = city_summary(final)
    changed = final[final["phase126_option_id"].ne(final["phase125_option_id"])].copy()
    remaining = final[final["phase126_error_rate_pct"] > 20].copy()

    selected.to_csv(OUT / "phase126_selected_candidates.csv", index=False)
    final.to_csv(OUT / "phase126_registry.csv", index=False)
    summary.to_csv(OUT / "phase126_city_summary.csv", index=False)
    changed.to_csv(OUT / "phase126_changed_cells.csv", index=False)
    remaining.to_csv(OUT / "phase126_remaining_gt20.csv", index=False)
    write_report(summary, selected, changed, remaining)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
