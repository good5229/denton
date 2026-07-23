#!/usr/bin/env python3
"""Phase125: COMWEL workplace/employment refinement screen.

Use the collected Korea Workers' Compensation & Welfare Service employment/
industrial-insurance workplace file as a city×KSIC-middle activity source.

The source is a 2025-12-31 snapshot in the local file name, so this phase does
not claim flash availability for 2023.  It is screened as a refinement/structure
candidate.  Adoption is conservative: a candidate sub-block is applied only if
it improves total error and does not worsen any middle-industry cell relative
to Phase124.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import run_phase115_flash_gt20_source_improvement as p115


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase125_comwel_workplace_refinement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase125_comwel_workplace_refinement.md"
BASE = DATA / "phase124_pps_subblock_no_worse" / "phase124_registry.csv"
COMWEL = DATA / "phase121_direct_activity_sources" / "phase121_comwel_workplaces_middle_agg.csv"


PARENT_RANGES = {
    "C00": list(range(10, 35)),
    "F00": [41, 42],
    "G00": [45, 46, 47],
    "H00": [49, 50, 51, 52],
    "I00": [55, 56],
    "J00": [58, 59, 60, 61, 62, 63],
    "K00": [64, 65, 66],
    "MN0": [70, 71, 72, 73, 74, 75, 76],
    "Q00": [86, 87],
    "ERS": [36, 37, 38, 39, 90, 91, 94, 95, 96],
}


SUBBLOCKS: dict[tuple[str, str], list[str]] = {
    ("C00", "mfg_light_10_18"): ["10", "13", "14", "15", "16", "17", "18"],
    ("C00", "mfg_material_20_25"): ["20", "21", "22", "23", "24", "25"],
    ("C00", "mfg_equipment_26_34"): ["26", "27", "28", "29", "30", "31", "32", "33", "34"],
    ("F00", "construction_41_42"): ["41", "42"],
    ("G00", "trade_45_47"): ["45", "46", "47"],
    ("H00", "transport_49_52"): ["49", "50", "51", "52"],
    ("J00", "content_58_60"): ["58", "59", "60"],
    ("J00", "telecom_it_61_63"): ["61", "62", "63"],
    ("K00", "finance_insurance_64_66"): ["64", "65", "66"],
    ("MN0", "professional_70_73"): ["70", "71", "72", "73"],
    ("MN0", "facility_support_74_76"): ["74", "75", "76"],
    ("ERS", "environment_36_39"): ["36", "37", "38", "39"],
    ("ERS", "culture_leisure_90_91"): ["90", "91"],
    ("ERS", "association_personal_94_96"): ["94", "95", "96"],
}


def parent_for_middle(code: str) -> str | None:
    try:
        c = int(str(code).zfill(2))
    except Exception:
        return None
    for parent, vals in PARENT_RANGES.items():
        if c in vals:
            return parent
    return None


def load_base() -> pd.DataFrame:
    df = pd.read_csv(BASE, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["phase125_predicted_gva_eok"] = df["phase124_predicted_gva_eok"]
    df["phase125_error_gva_eok"] = df["phase124_error_gva_eok"]
    df["phase125_error_rate_pct"] = df["phase124_error_rate_pct"]
    df["phase125_option_id"] = df["phase124_option_id"]
    return df


def load_comwel() -> pd.DataFrame:
    df = pd.read_csv(COMWEL, dtype={"middle_code": str})
    df = df[df["middle_code"].notna()].copy()
    df["middle_code"] = df["middle_code"].astype(str).str.extract(r"(\d+)")[0].str.zfill(2)
    df["parent_code"] = df["middle_code"].map(parent_for_middle)
    df = df[df["parent_code"].notna()].copy()
    for col in ["workplace_count", "employment_workers", "industrial_workers"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def block_specs(base: pd.DataFrame) -> list[dict[str, Any]]:
    specs = []
    for (city, parent), g in base.groupby(["city", "parent_code"]):
        codes = sorted(g["middle_code"].dropna().astype(str).str.zfill(2).unique())
        if len(codes) >= 2:
            specs.append({"city": city, "parent_code": parent, "block_id": f"{parent}_all", "codes": codes, "scope": "parent"})
    for (parent, block_id), codes in SUBBLOCKS.items():
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
    screen_rows: list[dict[str, Any]] = []
    detail_rows: list[pd.DataFrame] = []

    for spec in block_specs(base):
        city = spec["city"]
        parent = spec["parent_code"]
        codes = spec["codes"]
        g = base[base["city"].eq(city) & base["parent_code"].eq(parent) & base["middle_code"].isin(codes)].copy()
        if len(g) < 2:
            continue
        c = comwel[comwel["city"].eq(city) & comwel["parent_code"].eq(parent) & comwel["middle_code"].isin(codes)].copy()
        if c.empty:
            continue
        cm = g[["middle_code"]].merge(c, on="middle_code", how="left")
        old_pred = g["phase124_predicted_gva_eok"].to_numpy(float)
        old_err = g["phase124_error_gva_eok"].to_numpy(float)
        old_rate = g["phase124_error_rate_pct"].to_numpy(float)
        actual = g["actual_gva_eok"].to_numpy(float)
        total = float(old_pred.sum())
        base_share = old_pred / old_pred.sum() if old_pred.sum() else np.ones(len(g)) / len(g)
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
                        "option_id": f"phase125_comwel_{metric}_{spec['block_id']}",
                        "alpha": alpha,
                        "baseline_floor": floor,
                        "phase124_error_eok": float(old_err.sum()),
                        "candidate_error_eok": float(err.sum()),
                        "incremental_reduction_eok": reduction,
                        "phase124_gt20_cells": int((old_rate > 20).sum()),
                        "candidate_gt20_cells": int((rate > 20).sum()),
                        "phase124_gt10_cells": int((old_rate > 10).sum()),
                        "candidate_gt10_cells": int((rate > 10).sum()),
                        "worsened_cells": int((delta > 1e-9).sum()),
                        "worsen_sum_eok": float(np.maximum(delta, 0).sum()),
                        "max_worsen_pp": float(np.nanmax(rate - old_rate)),
                    }
                    row["adoptable"] = (
                        reduction > 1e-9
                        and row["worsened_cells"] == 0
                        and row["candidate_gt20_cells"] <= row["phase124_gt20_cells"]
                        and row["candidate_gt10_cells"] <= row["phase124_gt10_cells"]
                    )
                    screen_rows.append(row)
                    d = g[[
                        "city",
                        "parent_code",
                        "middle_code",
                        "middle_label",
                        "actual_gva_eok",
                        "phase124_predicted_gva_eok",
                        "phase124_error_gva_eok",
                        "phase124_error_rate_pct",
                    ]].copy()
                    d["block_id"] = spec["block_id"]
                    d["scope"] = spec["scope"]
                    d["metric"] = metric
                    d["option_id"] = row["option_id"]
                    d["alpha"] = alpha
                    d["baseline_floor"] = floor
                    d["candidate_predicted_gva_eok"] = pred
                    d["candidate_error_gva_eok"] = err
                    d["candidate_error_rate_pct"] = rate
                    d["incremental_reduction_eok"] = old_err - err
                    d["candidate_worse"] = delta > 1e-9
                    detail_rows.append(d)

    screen = pd.DataFrame(screen_rows)
    if not screen.empty:
        screen = screen.sort_values(["adoptable", "incremental_reduction_eok", "candidate_gt20_cells"], ascending=[False, False, True])
    detail = pd.concat(detail_rows, ignore_index=True) if detail_rows else pd.DataFrame()
    return screen, detail


def select_nonoverlap(screen: pd.DataFrame) -> pd.DataFrame:
    if screen.empty:
        return screen
    candidates = screen[screen["adoptable"]].copy()
    if candidates.empty:
        return candidates
    candidates["code_set"] = candidates["middle_codes"].astype(str).map(lambda s: set(s.split(",")))
    chosen = []
    used: dict[tuple[str, str], set[str]] = {}
    for _, r in candidates.sort_values("incremental_reduction_eok", ascending=False).iterrows():
        key = (r.city, r.parent_code)
        already = used.setdefault(key, set())
        if already & r.code_set:
            continue
        chosen.append(r.drop(labels=["code_set"]).to_dict())
        already.update(r.code_set)
    return pd.DataFrame(chosen)


def apply_selected(base: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
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
            out.loc[idx, "phase125_predicted_gva_eok"] = r.candidate_predicted_gva_eok
            out.loc[idx, "phase125_error_gva_eok"] = r.candidate_error_gva_eok
            out.loc[idx, "phase125_error_rate_pct"] = r.candidate_error_rate_pct
            out.loc[idx, "phase125_option_id"] = s.option_id
    out["phase125_incremental_reduction_eok"] = out["phase124_error_gva_eok"] - out["phase125_error_gva_eok"]
    return out


def city_summary(reg: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in reg.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        p124 = float(g["phase124_error_gva_eok"].sum())
        p125 = float(g["phase125_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "phase124_error_eok": p124,
                "phase124_wape_pct": p124 / actual * 100,
                "phase125_error_eok": p125,
                "phase125_wape_pct": p125 / actual * 100,
                "incremental_reduction_eok": p124 - p125,
                "incremental_reduction_pp": (p124 - p125) / actual * 100,
                "phase124_gt20_cells": int((g["phase124_error_rate_pct"] > 20).sum()),
                "phase125_gt20_cells": int((g["phase125_error_rate_pct"] > 20).sum()),
                "phase124_gt10_cells": int((g["phase124_error_rate_pct"] > 10).sum()),
                "phase125_gt10_cells": int((g["phase125_error_rate_pct"] > 10).sum()),
                "worsened_vs_phase124_cells": int((g["phase125_error_gva_eok"] > g["phase124_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_base()
    comwel = load_comwel()
    screen, detail = evaluate(base, comwel)
    selected = select_nonoverlap(screen)
    registry = apply_selected(base, selected, detail)
    summary = city_summary(registry)
    improved = registry[registry["phase125_incremental_reduction_eok"].gt(1e-9)].sort_values(["city", "phase125_incremental_reduction_eok"], ascending=[True, False])
    remaining_gt20 = registry[registry["phase125_error_rate_pct"].gt(20)].sort_values(["city", "phase125_error_gva_eok"], ascending=[True, False])
    best_rejected = (
        screen[~screen["adoptable"]]
        .sort_values(["city", "incremental_reduction_eok"], ascending=[True, False])
        .groupby(["city", "parent_code", "block_id"], as_index=False)
        .head(1)
        if not screen.empty
        else pd.DataFrame()
    )

    comwel.to_csv(OUT / "phase125_comwel_middle_values.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(OUT / "phase125_candidate_screen.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase125_candidate_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase125_selected_blocks.csv", index=False, encoding="utf-8-sig")
    registry.to_csv(OUT / "phase125_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase125_city_summary.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUT / "phase125_improved_cells.csv", index=False, encoding="utf-8-sig")
    remaining_gt20.to_csv(OUT / "phase125_remaining_gt20.csv", index=False, encoding="utf-8-sig")
    best_rejected.to_csv(OUT / "phase125_best_rejected_candidates.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase125 고용·산재보험 사업장 자료 기반 정밀화 후보 실험

## 목적

Phase121에서 수집한 근로복지공단 고용·산재보험 가입 사업장 자료를 `지역×KSIC 중분류` 활동지표로 변환해 Phase124 이후 남은 GVA 오차를 줄일 수 있는지 검증했다.

이 자료는 로컬 파일명이 2025-12-31 기준 사업장 스냅샷이므로 2023년 속보성 자료로 주장하지 않는다. 이번 단계에서는 **정밀화/구조 개선 후보**로만 평가한다.

## 채택 기준

1. Phase124 대비 후보 블록 총오차가 줄어야 한다.
2. 해당 블록 안의 어떤 중분류도 Phase124보다 악화되면 안 된다.
3. 20% 초과 셀과 10% 초과 셀 개수가 늘면 안 된다.
4. 서로 겹치는 블록은 개선폭이 큰 후보를 우선 채택한다.

## 도시별 성능

{p115.md_table(summary, [("city", "지역"), ("phase124_error_eok", "Phase124 오차 억원"), ("phase124_wape_pct", "Phase124 오차 %"), ("phase125_error_eok", "Phase125 오차 억원"), ("phase125_wape_pct", "Phase125 오차 %"), ("incremental_reduction_eok", "추가 감소 억원"), ("incremental_reduction_pp", "추가 감소 pp"), ("phase124_gt20_cells", "Phase124 20%초과"), ("phase125_gt20_cells", "Phase125 20%초과"), ("phase124_gt10_cells", "Phase124 10%초과"), ("phase125_gt10_cells", "Phase125 10%초과"), ("worsened_vs_phase124_cells", "악화 셀")])}

## 채택된 COMWEL 후보

{p115.md_table(selected, [("city", "지역"), ("parent_code", "상위산업"), ("block_id", "블록"), ("scope", "범위"), ("middle_codes", "중분류"), ("metric_label", "지표"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("phase124_error_eok", "Phase124 오차 억원"), ("candidate_error_eok", "후보 오차 억원"), ("incremental_reduction_eok", "감소 억원"), ("phase124_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("worsened_cells", "악화 셀")], 80)}

## 개선된 중분류

{p115.md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase124_error_gva_eok", "Phase124 오차 억원"), ("phase125_error_gva_eok", "Phase125 오차 억원"), ("phase125_error_rate_pct", "Phase125 오차 %"), ("phase125_incremental_reduction_eok", "감소 억원"), ("phase125_option_id", "적용 지표")], 100)}

## 남은 20% 초과 중분류

{p115.md_table(remaining_gt20, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase125_predicted_gva_eok", "추정 억원"), ("phase125_error_gva_eok", "오차 억원"), ("phase125_error_rate_pct", "오차 %"), ("phase125_option_id", "적용 지표")], 120)}

## 주요 보류 후보

{p115.md_table(best_rejected, [("city", "지역"), ("parent_code", "상위산업"), ("block_id", "블록"), ("metric_label", "지표"), ("incremental_reduction_eok", "감소 억원"), ("worsened_cells", "악화 셀"), ("worsen_sum_eok", "악화합계 억원"), ("phase124_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("adoptable", "채택가능")], 80)}

## 판정

COMWEL 사업장 자료는 일부 업종의 구조 개선에는 도움이 되지만, 전체 취약 업종을 자동으로 해결하지는 못한다. 특히 2025년 스냅샷이므로 공개 성능에는 속보성 지표가 아니라 정밀화 후보로만 표기해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
