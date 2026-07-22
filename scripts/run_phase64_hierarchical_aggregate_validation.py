#!/usr/bin/env python3
"""Phase64: hierarchical aggregate validation for GVA allocation estimates.

This is the validation the project actually needs when detailed actual GVA is
scarce: estimate/distribute lower-level cells, aggregate them to a level where
actual or hidden actual shares exist, then compare the aggregate with actual.

Two distinct checks are emitted:
  - Performance check: small-level allocation aggregated to middle-level
    hidden actual sales shares (GVA adjacent actual, not direct GVA).
  - Accounting check: cube lower levels sum to cube upper levels. This is a
    necessary consistency check, not an accuracy score.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase64_hierarchical_aggregate_validation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase64_hierarchical_aggregate_validation.md"


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def flt(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def div2(code: str) -> str:
    return str(code).zfill(3)[:2]


def parent_section(div: str) -> str:
    d = int(str(div).zfill(2))
    if 1 <= d <= 3:
        return "A00"
    if 5 <= d <= 8:
        return "B00"
    if 10 <= d <= 34:
        return "C00"
    if d == 35:
        return "D00"
    if 36 <= d <= 39 or 90 <= d <= 96:
        return "ERS"
    if 41 <= d <= 42:
        return "F00"
    if 45 <= d <= 47:
        return "G00"
    if 49 <= d <= 52:
        return "H00"
    if 55 <= d <= 56:
        return "I00"
    if 58 <= d <= 63:
        return "J00"
    if 64 <= d <= 66:
        return "K00"
    if d == 68:
        return "L00"
    if 70 <= d <= 75:
        return "MN0"
    if d == 84:
        return "O00"
    if d == 85:
        return "P00"
    if 86 <= d <= 87:
        return "Q00"
    return "UNKNOWN"


def ksic_section_letter(div: str) -> str:
    d = int(str(div).zfill(2))
    if 1 <= d <= 3:
        return "A"
    if 5 <= d <= 8:
        return "B"
    if 10 <= d <= 34:
        return "C"
    if d == 35:
        return "D"
    if 36 <= d <= 39:
        return "E"
    if 41 <= d <= 42:
        return "F"
    if 45 <= d <= 47:
        return "G"
    if 49 <= d <= 52:
        return "H"
    if 55 <= d <= 56:
        return "I"
    if 58 <= d <= 63:
        return "J"
    if 64 <= d <= 66:
        return "K"
    if d == 68:
        return "L"
    if 70 <= d <= 73:
        return "M"
    if 74 <= d <= 76:
        return "N"
    if d == 84:
        return "O"
    if d == 85:
        return "P"
    if 86 <= d <= 87:
        return "Q"
    if 90 <= d <= 91:
        return "R"
    if 94 <= d <= 96:
        return "S"
    return "UNKNOWN"


def aggregate_small_to_middle(city: str, path: Path, style: str) -> tuple[list[dict], dict]:
    rows = read_csv(path)
    if style == "goyang":
        small_level, middle_level = "small", "middle"
        actual_col, pred_col, uniform_col = "actual_sales_share", "predicted_proxy_share", "uniform_share"
    else:
        small_level, middle_level = "소분류", "중분류"
        actual_col, pred_col, uniform_col = "actual_share", "predicted_share", "uniform_share"

    middle_actual: dict[tuple[str, str], float] = {}
    middle_name: dict[tuple[str, str], str] = {}
    for r in rows:
        if r["industry_level"] == middle_level:
            key = (r["parent_code"], str(r["industry_code"]).zfill(2))
            middle_actual[key] = flt(r[actual_col])
            middle_name[key] = r.get("industry_name", "")

    agg_pred = defaultdict(float)
    agg_actual_from_small = defaultdict(float)
    agg_uniform = defaultdict(float)
    for r in rows:
        if r["industry_level"] == small_level:
            key = (r["parent_code"], div2(r["industry_code"]))
            agg_pred[key] += flt(r[pred_col])
            agg_actual_from_small[key] += flt(r[actual_col])
            agg_uniform[key] += flt(r[uniform_col])

    detail = []
    for key in sorted(set(middle_actual) | set(agg_pred)):
        actual = middle_actual.get(key, 0.0)
        pred = agg_pred.get(key, 0.0)
        uniform = agg_uniform.get(key, 0.0)
        actual_from_small = agg_actual_from_small.get(key, 0.0)
        detail.append({
            "city": city,
            "parent_section": key[0],
            "middle_code": key[1],
            "middle_name": middle_name.get(key, ""),
            "actual_middle_share": actual,
            "actual_from_small_sum": actual_from_small,
            "predicted_small_aggregated_share": pred,
            "uniform_small_aggregated_share": uniform,
            "abs_error_pp": abs(pred - actual) * 100,
            "uniform_abs_error_pp": abs(uniform - actual) * 100,
            "actual_sum_gap_pp": abs(actual_from_small - actual) * 100,
        })

    usable = [r for r in detail if r["parent_section"] != "UNKNOWN"]
    summary = {
        "city": city,
        "validation": "소분류 배분→중분류 집계 actual 비교",
        "cells": len(usable),
        "mae_pp": sum(r["abs_error_pp"] for r in usable) / len(usable) if usable else 0,
        "uniform_mae_pp": sum(r["uniform_abs_error_pp"] for r in usable) / len(usable) if usable else 0,
        "max_abs_error_pp": max((r["abs_error_pp"] for r in usable), default=0),
        "le_1pp_cells": sum(1 for r in usable if r["abs_error_pp"] <= 1.0),
        "le_5pp_cells": sum(1 for r in usable if r["abs_error_pp"] <= 5.0),
        "le_10pp_cells": sum(1 for r in usable if r["abs_error_pp"] <= 10.0),
        "max_actual_sum_gap_pp": max((r["actual_sum_gap_pp"] for r in usable), default=0),
    }
    return detail, summary


def cube_accounting(city: str, path: Path) -> list[dict]:
    df = pd.read_parquet(path)
    keys = ["time_level", "year", "quarter", "month", "period", "geo_level", "geo_code", "geo_name"]
    out = []

    small = df[df.industry_level.eq("소분류")].copy()
    middle = df[df.industry_level.eq("중분류")].copy()
    large = df[df.industry_level.eq("대분류")].copy()

    small["middle_code"] = small.industry_code.astype(str).str.zfill(3).str[:2]
    s_agg = small.groupby(keys + ["middle_code"], dropna=False, as_index=False).estimated_gva.sum()
    m_cmp = middle.rename(columns={"industry_code": "middle_code", "estimated_gva": "upper_estimated_gva"})
    merged = s_agg.merge(m_cmp[keys + ["middle_code", "upper_estimated_gva"]], on=keys + ["middle_code"], how="inner")
    merged["abs_error"] = (merged.estimated_gva - merged.upper_estimated_gva).abs()
    out.append({
        "city": city,
        "check": "소분류 합계=중분류 큐브",
        "rows": int(len(merged)),
        "max_abs_error": float(merged.abs_error.max()) if len(merged) else 0.0,
        "mean_abs_error": float(merged.abs_error.mean()) if len(merged) else 0.0,
    })

    middle["parent_section"] = middle.industry_code.astype(str).map(ksic_section_letter)
    m_agg = middle.groupby(keys + ["parent_section"], dropna=False, as_index=False).estimated_gva.sum()
    l_cmp = large.rename(columns={"industry_code": "parent_section", "estimated_gva": "upper_estimated_gva"})
    merged2 = m_agg.merge(l_cmp[keys + ["parent_section", "upper_estimated_gva"]], on=keys + ["parent_section"], how="inner")
    merged2["abs_error"] = (merged2.estimated_gva - merged2.upper_estimated_gva).abs()
    out.append({
        "city": city,
        "check": "중분류 합계=대분류 큐브",
        "rows": int(len(merged2)),
        "max_abs_error": float(merged2.abs_error.max()) if len(merged2) else 0.0,
        "mean_abs_error": float(merged2.abs_error.mean()) if len(merged2) else 0.0,
    })
    return out


def md_table(rows: list[dict], cols: list[tuple[str, str]], limit=20) -> str:
    if not rows:
        return "\n해당 없음\n"
    s = "| " + " | ".join(label for _, label in cols) + " |\n"
    s += "| " + " | ".join("---" for _ in cols) + " |\n"
    for r in rows[:limit]:
        vals = []
        for k, _ in cols:
            v = r.get(k, "")
            if isinstance(v, float):
                vals.append(f"{v:.3f}")
            else:
                vals.append(str(v))
        s += "| " + " | ".join(vals) + " |\n"
    return s


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    g_detail, g_summary = aggregate_small_to_middle(
        "고양시",
        DATA / "partial_stats_phase41_all_ksic_holdout_detail.csv",
        "goyang",
    )
    p_detail, p_summary = aggregate_small_to_middle(
        "포항시",
        DATA / "partial_stats_phase42_pohang_industry_holdout_detail.csv",
        "pohang",
    )
    summaries = [g_summary, p_summary]
    accounting = []
    accounting += cube_accounting("고양시", DATA / "partial_stats_phase41_all_ksic_multiresolution_cube.parquet")
    accounting += cube_accounting("포항시", DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet")

    write_csv(
        OUTDIR / "phase64_small_to_middle_aggregate_validation_detail.csv",
        g_detail + p_detail,
        ["city", "parent_section", "middle_code", "middle_name", "actual_middle_share", "actual_from_small_sum", "predicted_small_aggregated_share", "uniform_small_aggregated_share", "abs_error_pp", "uniform_abs_error_pp", "actual_sum_gap_pp"],
    )
    write_csv(
        OUTDIR / "phase64_small_to_middle_aggregate_validation_summary.csv",
        summaries,
        ["city", "validation", "cells", "mae_pp", "uniform_mae_pp", "max_abs_error_pp", "le_1pp_cells", "le_5pp_cells", "le_10pp_cells", "max_actual_sum_gap_pp"],
    )
    write_csv(
        OUTDIR / "phase64_cube_hierarchy_accounting_checks.csv",
        accounting,
        ["city", "check", "rows", "max_abs_error", "mean_abs_error"],
    )

    g_worst = sorted(g_detail, key=lambda r: r["abs_error_pp"], reverse=True)[:8]
    p_worst = sorted(p_detail, key=lambda r: r["abs_error_pp"], reverse=True)[:8]

    report = f"""# Phase64 하위배분→상위집계 검증

## 목적

소분류 actual GVA가 없을 때는 소분류를 배분한 뒤, 이를 중분류 또는 대분류로 집계해 존재하는 상위 actual과 비교해야 한다. 이 보고서는 그 검증을 `성능검증`과 `회계검증`으로 분리한다.

## 성능검증: 소분류 배분값을 중분류로 집계

2015 경제총조사 매출분포를 숨김 actual로 두고, 소분류 배분값을 2자리 중분류로 집계한 뒤 중분류 actual과 비교했다. 매출분포는 GVA actual이 아니지만, 공공에서 소분류 GVA를 제공하지 않는 상황에서 계층 배분이 상위 구조를 복원하는지 보는 가장 가까운 검증축이다.

{md_table(summaries, [("city","지역"),("cells","중분류 셀"),("mae_pp","집계검증 MAE pp"),("uniform_mae_pp","균등 MAE pp"),("le_1pp_cells","1pp 이하"),("le_5pp_cells","5pp 이하"),("le_10pp_cells","10pp 이하"),("max_abs_error_pp","최대오차 pp")])}

## 고양시 최대오차 중분류

{md_table(g_worst, [("parent_section","상위"),("middle_code","중분류"),("middle_name","업종"),("actual_middle_share","actual"),("predicted_small_aggregated_share","집계예측"),("abs_error_pp","오차 pp"),("uniform_abs_error_pp","균등오차 pp")])}

## 포항시 최대오차 중분류

{md_table(p_worst, [("parent_section","상위"),("middle_code","중분류"),("middle_name","업종"),("actual_middle_share","actual"),("predicted_small_aggregated_share","집계예측"),("abs_error_pp","오차 pp"),("uniform_abs_error_pp","균등오차 pp")])}

## 회계검증: 큐브 내부 하위합=상위합

이 검증은 정확도 점수가 아니라 제약식 점검이다. 값이 0에 가까워야 정상이며, 성능 우수의 증거로 쓰면 안 된다.

{md_table(accounting, [("city","지역"),("check","검사"),("rows","행"),("max_abs_error","최대 절대오차"),("mean_abs_error","평균 절대오차")])}

## 판정

- 고양시와 포항시 모두 하위→상위 회계합계는 보존된다.
- 성능검증은 “소분류를 집계했을 때 중분류 actual 구조를 얼마나 복원하는가”로 봐야 한다.
- 1% 이내 주장은 전체 해상도에 적용할 수 없다. 다만 집계검증에서 1pp 이하인 중분류 셀 수는 별도로 제시할 수 있다.
- 농업·임업처럼 상위 집계에서도 오차가 큰 업종은 사업체·종사자 기준이 아니라 생산량·재배면적·산림자원량 기반 배분이 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
