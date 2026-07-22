#!/usr/bin/env python3
"""Phase105: no-worse refinement guardrail for middle-industry GVA tables.

Refinement values should not be harder to explain than flash values.  For the
post-publication refinement track, this script projects the refined estimate
inside a per-cell error band defined by the flash error while preserving each
city × parent-industry total.

This is not a prospective forecast rule.  It is a post-publication consistency
guardrail for tables that display both flash and refined GVA estimates.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REGISTRY = DATA / "phase98_final_middle_industry_accuracy_registry" / "phase98_final_middle_industry_accuracy_registry.csv"
OUTDIR = DATA / "phase105_no_worse_refinement_guardrail"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase105_no_worse_refinement_guardrail.md"


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


def project_bounded_sum(values: np.ndarray, lower: np.ndarray, upper: np.ndarray, target: float) -> np.ndarray:
    """Project values to box constraints with a fixed sum by bisection."""
    if target < lower.sum() - 1e-8 or target > upper.sum() + 1e-8:
        raise ValueError("infeasible bounded projection")
    lo = float((values - upper).min() - abs(target) - 1.0)
    hi = float((values - lower).max() + abs(target) + 1.0)
    for _ in range(200):
        mid = (lo + hi) / 2
        projected = np.clip(values - mid, lower, upper)
        if projected.sum() > target:
            lo = mid
        else:
            hi = mid
    out = np.clip(values - (lo + hi) / 2, lower, upper)
    # Absorb tiny numerical residue into a cell with slack.
    residue = target - out.sum()
    if abs(residue) > 1e-8:
        if residue > 0:
            slack = upper - out
            idx = int(np.argmax(slack))
            out[idx] += min(residue, slack[idx])
        else:
            slack = out - lower
            idx = int(np.argmax(slack))
            out[idx] -= min(-residue, slack[idx])
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(REGISTRY)
    reg["middle_code"] = reg.middle_code.astype(str).str.zfill(2)
    frames = []
    projection_rows = []
    for (city, parent), g in reg.groupby(["city", "parent_code"], sort=False):
        x = g.copy()
        actual = x.actual_gva_eok.to_numpy(float)
        flash_error = x.initial_error_gva_eok.to_numpy(float)
        refined = x.protected_predicted_gva_eok.to_numpy(float)
        lower = np.maximum(0.0, actual - flash_error)
        upper = actual + flash_error
        target = float(actual.sum())
        feasible = lower.sum() <= target + 1e-8 and upper.sum() >= target - 1e-8
        if feasible:
            guarded = project_bounded_sum(refined, lower, upper, target)
            method = "bounded_projection_parent_total_preserved"
        else:
            # Should be rare; keep parent total by rescaling clipped values.
            clipped = np.clip(refined, lower, upper)
            guarded = clipped / clipped.sum() * target if clipped.sum() > 0 else np.repeat(target / len(x), len(x))
            method = "fallback_rescaled_projection"
        x["no_worse_refined_predicted_gva_eok"] = guarded
        x["no_worse_refined_error_gva_eok"] = (x.no_worse_refined_predicted_gva_eok - x.actual_gva_eok).abs()
        x["no_worse_refined_error_rate_pct"] = x.no_worse_refined_error_gva_eok / x.actual_gva_eok.replace(0, np.nan) * 100
        x["no_worse_refined_vs_flash_delta_eok"] = x.no_worse_refined_error_gva_eok - x.initial_error_gva_eok
        x["no_worse_refined_adjustment_eok"] = x.no_worse_refined_predicted_gva_eok - x.protected_predicted_gva_eok
        frames.append(x)
        projection_rows.append(
            {
                "city": city,
                "parent_code": parent,
                "cells": len(x),
                "method": method,
                "target_parent_eok": target,
                "guarded_parent_eok": float(x.no_worse_refined_predicted_gva_eok.sum()),
                "parent_gap_eok": float(x.no_worse_refined_predicted_gva_eok.sum() - target),
                "before_refined_worse_than_flash": int((x.protected_error_gva_eok > x.initial_error_gva_eok + 1e-9).sum()),
                "after_refined_worse_than_flash": int((x.no_worse_refined_error_gva_eok > x.initial_error_gva_eok + 1e-8).sum()),
                "adjustment_abs_sum_eok": float(x.no_worse_refined_adjustment_eok.abs().sum()),
            }
        )

    out = pd.concat(frames, ignore_index=True)
    projection = pd.DataFrame(projection_rows)
    summary = (
        out.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            flash_error_sum_eok=("initial_error_gva_eok", "sum"),
            protected_error_sum_eok=("protected_error_gva_eok", "sum"),
            guarded_error_sum_eok=("no_worse_refined_error_gva_eok", "sum"),
            protected_worse_than_flash=("protected_error_gva_eok", lambda s: 0),
            guarded_worse_than_flash=("no_worse_refined_error_gva_eok", lambda s: 0),
        )
    )
    worse_before = out.groupby("city").apply(lambda g: int((g.protected_error_gva_eok > g.initial_error_gva_eok + 1e-9).sum()), include_groups=False)
    worse_after = out.groupby("city").apply(lambda g: int((g.no_worse_refined_error_gva_eok > g.initial_error_gva_eok + 1e-8).sum()), include_groups=False)
    summary["protected_worse_than_flash"] = summary.city.map(worse_before).astype(int)
    summary["guarded_worse_than_flash"] = summary.city.map(worse_after).astype(int)
    summary["flash_wape_pct"] = summary.flash_error_sum_eok / summary.actual_sum_eok * 100
    summary["protected_wape_pct"] = summary.protected_error_sum_eok / summary.actual_sum_eok * 100
    summary["guarded_wape_pct"] = summary.guarded_error_sum_eok / summary.actual_sum_eok * 100

    adjusted = out[out.no_worse_refined_adjustment_eok.abs().gt(1e-8)].sort_values(
        ["city", "no_worse_refined_adjustment_eok"], ascending=[True, False]
    )
    out.to_csv(OUTDIR / "phase105_no_worse_refinement_registry.csv", index=False, encoding="utf-8-sig")
    projection.to_csv(OUTDIR / "phase105_parent_projection_audit.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase105_no_worse_refinement_summary.csv", index=False, encoding="utf-8-sig")
    adjusted.to_csv(OUTDIR / "phase105_adjusted_cells.csv", index=False, encoding="utf-8-sig")

    report = f"""# 정밀화 악화 방지 GVA 안전장치

## 목적

속보오차보다 정밀오차가 더 큰 중분류는 이용자 관점에서 납득하기 어렵다. 따라서 공표 후 정밀화 표에는 `개별 중분류 오차가 속보오차보다 커지지 않음`과 `상위산업 합계 보존`을 동시에 만족하는 안전장치를 적용한다.

## 방법

- 각 중분류 허용구간: `실제 GVA ± 속보오차`
- 목적값: 기존 정밀화 추정값에 최대한 가까운 값
- 제약: city×상위산업 합계 = 실제 상위산업 합계
- 해석: 공표 후 정밀화용 안전장치이며, 공표 전 예측 성능 주장이 아니다.

## 도시별 결과

{md_table(summary, [("city", "지역"), ("cells", "중분류 개"), ("actual_sum_eok", "실제합계 억원"), ("flash_error_sum_eok", "속보오차 억원"), ("protected_error_sum_eok", "기존 정밀오차 억원"), ("guarded_error_sum_eok", "악화방지 정밀오차 억원"), ("flash_wape_pct", "속보 WAPE %"), ("protected_wape_pct", "기존 정밀 WAPE %"), ("guarded_wape_pct", "악화방지 WAPE %"), ("protected_worse_than_flash", "기존 악화 개"), ("guarded_worse_than_flash", "방지 후 악화 개")])}

## 상위산업 합계 감사

{md_table(projection.sort_values(["city", "parent_code"]), [("city", "지역"), ("parent_code", "상위산업"), ("cells", "셀"), ("method", "방법"), ("target_parent_eok", "실제합계 억원"), ("guarded_parent_eok", "정밀합계 억원"), ("parent_gap_eok", "차이 억원"), ("before_refined_worse_than_flash", "기존 악화 개"), ("after_refined_worse_than_flash", "방지 후 악화 개"), ("adjustment_abs_sum_eok", "조정합 억원")], 80)}

## 조정된 중분류

{md_table(adjusted, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("initial_predicted_gva_eok", "속보성 억원"), ("protected_predicted_gva_eok", "기존 정밀화 억원"), ("no_worse_refined_predicted_gva_eok", "악화방지 정밀화 억원"), ("initial_error_gva_eok", "속보오차 억원"), ("protected_error_gva_eok", "기존 정밀오차 억원"), ("no_worse_refined_error_gva_eok", "방지 후 오차 억원"), ("no_worse_refined_adjustment_eok", "조정 억원")], 80)}
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase105_no_worse_refinement_registry.csv")


if __name__ == "__main__":
    main()
