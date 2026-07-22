#!/usr/bin/env python3
"""Phase103: middle-industry GVA table with actual, flash, and refinement estimates."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase103_flash_refinement_comparison"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase103_flash_refinement_comparison.md"
REGISTRY = DATA / "phase98_final_middle_industry_accuracy_registry" / "phase98_final_middle_industry_accuracy_registry.csv"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "pp")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            value = row.get(key, "")
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}" if abs(value) < 100 else f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(REGISTRY, dtype={"middle_code": str})
    reg["middle_code"] = reg.middle_code.astype(str).str.zfill(2)
    out = reg[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "initial_predicted_gva_eok",
            "initial_error_gva_eok",
            "initial_error_rate_pct",
            "protected_predicted_gva_eok",
            "protected_error_gva_eok",
            "protected_error_rate_pct",
            "required_next_data",
        ]
    ].rename(
        columns={
            "initial_predicted_gva_eok": "flash_predicted_gva_eok",
            "initial_error_gva_eok": "flash_error_gva_eok",
            "initial_error_rate_pct": "flash_error_rate_pct",
            "protected_predicted_gva_eok": "refined_predicted_gva_eok",
            "protected_error_gva_eok": "refined_error_gva_eok",
            "protected_error_rate_pct": "refined_error_rate_pct",
        }
    )
    out["refinement_error_reduction_eok"] = out.flash_error_gva_eok - out.refined_error_gva_eok
    out["refinement_error_reduction_pp"] = out.flash_error_rate_pct - out.refined_error_rate_pct
    out["display_group"] = np.select(
        [
            out.refined_error_rate_pct <= 10,
            out.refined_error_gva_eok >= 500,
            out.refined_error_rate_pct > 10,
        ],
        ["정밀화 후 활용후보", "정밀화 후 금액주의", "정밀화 후 비율주의"],
        default="정밀화 후 활용후보",
    )
    summary = (
        out.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            flash_error_sum_eok=("flash_error_gva_eok", "sum"),
            refined_error_sum_eok=("refined_error_gva_eok", "sum"),
            flash_over10=("flash_error_rate_pct", lambda s: int((s > 10).sum())),
            refined_over10=("refined_error_rate_pct", lambda s: int((s > 10).sum())),
            flash_over20=("flash_error_rate_pct", lambda s: int((s > 20).sum())),
            refined_over20=("refined_error_rate_pct", lambda s: int((s > 20).sum())),
        )
    )
    summary["flash_wape_pct"] = summary.flash_error_sum_eok / summary.actual_sum_eok * 100
    summary["refined_wape_pct"] = summary.refined_error_sum_eok / summary.actual_sum_eok * 100
    summary["wape_reduction_pp"] = summary.flash_wape_pct - summary.refined_wape_pct
    summary["error_reduction_eok"] = summary.flash_error_sum_eok - summary.refined_error_sum_eok

    examples = pd.concat(
        [
            out[out.city.eq(city)].sort_values("refinement_error_reduction_eok", ascending=False).head(8)
            for city in sorted(out.city.unique())
        ],
        ignore_index=True,
    )
    remaining = out[(out.refined_error_rate_pct > 10) | (out.refined_error_gva_eok >= 500)].sort_values(
        ["city", "refined_error_gva_eok"], ascending=[True, False]
    )

    out.to_csv(OUTDIR / "phase103_middle_flash_refinement_comparison.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase103_city_summary.csv", index=False, encoding="utf-8-sig")
    examples.to_csv(OUTDIR / "phase103_largest_refinement_reductions.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase103_remaining_refined_gaps.csv", index=False, encoding="utf-8-sig")

    report = f"""# 중분류 GVA 속보성·정밀화 비교표

## 목적

중분류 집계검증 표에서 실제값과 정밀화 결과만 제시하면 사용자가 속보성 지표의 흔들림을 알 수 없다. 따라서 각 중분류에 대해 `실제 GVA`, `속보성 추정`, `공표 후 정밀화 추정`, `속보성 오차`, `정밀화 오차`를 같은 표에 놓는다.

## 도시별 요약

{md_table(summary, [("city", "지역"), ("cells", "중분류 개"), ("actual_sum_eok", "실제합계 억원"), ("flash_error_sum_eok", "속보성 오차 억원"), ("refined_error_sum_eok", "정밀화 오차 억원"), ("error_reduction_eok", "오차감소 억원"), ("flash_wape_pct", "속보성 WAPE %"), ("refined_wape_pct", "정밀화 WAPE %"), ("wape_reduction_pp", "WAPE 감소 pp"), ("flash_over10", "속보 10%초과 개"), ("refined_over10", "정밀화 10%초과 개")])}

## 정밀화로 오차가 크게 줄어든 중분류

{md_table(examples, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("flash_predicted_gva_eok", "속보성 억원"), ("refined_predicted_gva_eok", "정밀화 억원"), ("flash_error_gva_eok", "속보오차 억원"), ("flash_error_rate_pct", "속보오차 %"), ("refined_error_gva_eok", "정밀오차 억원"), ("refined_error_rate_pct", "정밀오차 %")], 20)}

## 정밀화 후에도 남은 주의 산업

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("flash_predicted_gva_eok", "속보성 억원"), ("refined_predicted_gva_eok", "정밀화 억원"), ("flash_error_gva_eok", "속보오차 억원"), ("flash_error_rate_pct", "속보오차 %"), ("refined_error_gva_eok", "정밀오차 억원"), ("refined_error_rate_pct", "정밀오차 %"), ("required_next_data", "필요자료")], 60)}

## 판정

1. 포스터 중분류 표는 실제/속보성/정밀화/속보오차/정밀화오차를 함께 보여준다.
2. 속보성 지표는 전월·전분기 경보용이며, 정밀화 지표는 공표 후 재산출·검증용이다.
3. 정밀화 후에도 10% 초과 또는 500억원 이상 금액오차가 남는 산업은 자료보강 대상으로 표시한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase103_middle_flash_refinement_comparison.csv")


if __name__ == "__main__":
    main()
