#!/usr/bin/env python3
"""Phase130: adopt the Phase129 balanced precision route for Goyang.

This script makes a clean Goyang-only registry for poster/report use.  It does
not create new predicted values; it audits and packages the Phase129 balanced
precision route against the Phase127 strict no-worse route.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase130_goyang_precision_adoption"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase130_goyang_precision_adoption.md"

STRICT127 = DATA / "phase127_precision_comwel_after_phase114" / "phase127_strict_registry.csv"
BALANCED129 = DATA / "phase129_balanced_precision_routing" / "phase129_balanced_registry.csv"


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

    rows = ["| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *rows])


def city_metrics(df: pd.DataFrame, err_col: str, rate_col: str) -> dict[str, float | int]:
    total = float(df["actual_gva_eok"].sum())
    err = float(df[err_col].sum())
    return {
        "actual_sum_eok": total,
        "error_eok": err,
        "wape_pct": err / total * 100,
        "gt10_cells": int((df[rate_col] > 10).sum()),
        "gt20_cells": int((df[rate_col] > 20).sum()),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    strict = pd.read_csv(STRICT127, dtype={"middle_code": str})
    balanced = pd.read_csv(BALANCED129, dtype={"middle_code": str})
    strict["middle_code"] = strict["middle_code"].astype(str).str.zfill(2)
    balanced["middle_code"] = balanced["middle_code"].astype(str).str.zfill(2)
    strict = strict[strict["city"].eq("고양시")].copy()
    balanced = balanced[balanced["city"].eq("고양시")].copy()

    key = ["city", "parent_code", "middle_code"]
    keep_bal = key + [
        "phase129_balanced_predicted_gva_eok",
        "phase129_balanced_error_gva_eok",
        "phase129_balanced_error_rate_pct",
        "phase129_balanced_option_id",
        "phase129_balanced_reduction_vs_base_eok",
        "phase129_balanced_worse_vs_base",
    ]
    reg = strict.merge(balanced[keep_bal], on=key, how="left")
    reg["phase130_predicted_gva_eok"] = reg["phase129_balanced_predicted_gva_eok"].fillna(reg["phase127_strict_predicted_gva_eok"])
    reg["phase130_error_gva_eok"] = reg["phase129_balanced_error_gva_eok"].fillna(reg["phase127_strict_error_gva_eok"])
    reg["phase130_error_rate_pct"] = reg["phase129_balanced_error_rate_pct"].fillna(reg["phase127_strict_error_rate_pct"])
    reg["phase130_option_id"] = reg["phase129_balanced_option_id"].fillna("phase127_strict")
    reg["phase130_error_reduction_vs_phase127_strict_eok"] = reg["phase127_strict_error_gva_eok"] - reg["phase130_error_gva_eok"]
    reg["phase130_worse_vs_phase127_strict"] = reg["phase130_error_gva_eok"] > reg["phase127_strict_error_gva_eok"] + 1e-9

    strict_metrics = city_metrics(reg, "phase127_strict_error_gva_eok", "phase127_strict_error_rate_pct")
    phase130_metrics = city_metrics(reg, "phase130_error_gva_eok", "phase130_error_rate_pct")
    summary = pd.DataFrame([{
        "city": "고양시",
        "phase127_strict_error_eok": strict_metrics["error_eok"],
        "phase127_strict_wape_pct": strict_metrics["wape_pct"],
        "phase127_strict_gt10_cells": strict_metrics["gt10_cells"],
        "phase127_strict_gt20_cells": strict_metrics["gt20_cells"],
        "phase130_error_eok": phase130_metrics["error_eok"],
        "phase130_wape_pct": phase130_metrics["wape_pct"],
        "phase130_gt10_cells": phase130_metrics["gt10_cells"],
        "phase130_gt20_cells": phase130_metrics["gt20_cells"],
        "error_reduction_eok": strict_metrics["error_eok"] - phase130_metrics["error_eok"],
        "worsened_cells": int(reg["phase130_worse_vs_phase127_strict"].sum()),
        "worsen_sum_eok": float((reg["phase130_error_gva_eok"] - reg["phase127_strict_error_gva_eok"]).clip(lower=0).sum()),
    }])

    improved = reg[reg["phase130_error_reduction_vs_phase127_strict_eok"] > 1e-9].sort_values(
        "phase130_error_reduction_vs_phase127_strict_eok", ascending=False
    )
    worsened = reg[reg["phase130_worse_vs_phase127_strict"]].sort_values("phase130_error_gva_eok", ascending=False)
    remaining = reg[reg["phase130_error_rate_pct"] > 10].sort_values("phase130_error_gva_eok", ascending=False)

    reg.to_csv(OUT / "phase130_goyang_precision_registry.csv", index=False)
    summary.to_csv(OUT / "phase130_goyang_precision_summary.csv", index=False)
    improved.to_csv(OUT / "phase130_goyang_improved_cells.csv", index=False)
    worsened.to_csv(OUT / "phase130_goyang_worsened_cells.csv", index=False)
    remaining.to_csv(OUT / "phase130_goyang_remaining_gt10.csv", index=False)

    REPORT.write_text("\n".join([
        "# Phase130 고양시 정밀오차 개선안 채택 감사",
        "",
        "## 목적",
        "",
        "Phase129 균형형 정밀 라우팅을 고양시 정밀화 산출물에 적용할 수 있는지 감사했다. 예측값은 실제 GVA를 직접 대입하지 않고, Phase127 후보자료에서 검증된 고용·산재 사업장 구조 및 활동자료 비중을 사용한 값이다.",
        "",
        "## 요약",
        "",
        md_table(summary, summary.columns.tolist()),
        "",
        "## 개선 셀",
        "",
        md_table(improved, ["parent_code","middle_code","middle_label","actual_gva_eok","phase127_strict_error_gva_eok","phase130_error_gva_eok","phase130_error_rate_pct","phase130_error_reduction_vs_phase127_strict_eok","phase130_option_id"], n=40),
        "",
        "## 악화 셀 감사",
        "",
        md_table(worsened, ["parent_code","middle_code","middle_label","actual_gva_eok","phase127_strict_error_gva_eok","phase130_error_gva_eok","phase130_error_rate_pct","phase130_option_id"], n=40),
        "",
        "## 남은 10% 초과 셀",
        "",
        md_table(remaining, ["parent_code","middle_code","middle_label","actual_gva_eok","phase130_predicted_gva_eok","phase130_error_gva_eok","phase130_error_rate_pct","phase130_option_id"], n=60),
        "",
        "## 판정",
        "",
        "고양시는 Phase130 개선안을 적용하면 총 정밀오차와 10% 초과 셀 수가 함께 감소한다. 다만 일부 저오차 셀이 소폭 악화되므로, 포스터에는 총오차 개선과 남은 취약 산업을 함께 표시하는 방식이 안전하다.",
    ]) + "\n", encoding="utf-8")

    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
