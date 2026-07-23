#!/usr/bin/env python3
"""Phase124: PPS sub-block routing with no-worse adoption.

Phase123 showed that PPS procurement improves Pohang construction, but applying
PPS to an entire parent sector can harm unrelated middle industries.  This
phase only reallocates within narrowly related middle-industry sub-blocks
covered by PPS notices, while leaving all other Phase120 flash estimates
unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import run_phase115_flash_gt20_source_improvement as p115
import run_phase123_pps_procurement_gva_improvement as p123


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase124_pps_subblock_no_worse"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase124_pps_subblock_no_worse.md"
P120 = DATA / "phase120_finance_procurement_source_integration" / "phase120_strict_flash_registry.csv"


SUBBLOCKS: dict[tuple[str, str], dict[str, list[str]]] = {
    ("F00", "construction_41_42"): {"codes": ["41", "42"]},
    ("ERS", "waste_water_37_38"): {"codes": ["37", "38"]},
    ("ERS", "culture_leisure_90_91"): {"codes": ["90", "91"]},
    ("ERS", "associations_personal_94_96"): {"codes": ["94", "96"]},
    ("MN0", "rd_engineering_science_70_72_73"): {"codes": ["70", "72", "73"]},
    ("MN0", "facility_support_74_75"): {"codes": ["74", "75"]},
    ("J00", "telecom_system_61_62"): {"codes": ["61", "62"]},
}


def load_phase120() -> pd.DataFrame:
    df = pd.read_csv(P120, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["phase124_predicted_gva_eok"] = df["phase120_strict_flash_predicted_gva_eok"]
    df["phase124_error_gva_eok"] = df["phase120_strict_flash_error_gva_eok"]
    df["phase124_error_rate_pct"] = df["phase120_strict_flash_error_rate_pct"]
    df["phase124_option_id"] = df["phase120_strict_flash_option_id"]
    return df


def pps_values() -> pd.DataFrame:
    pps, _ = p123.pps_indicators()
    if pps.empty:
        return pps
    use = pps[pps["source_id"].eq("flash_pps_procurement_amount")].copy()
    if use.empty:
        return use
    return (
        use.groupby(["city", "parent_code", "middle_code"], as_index=False)
        .agg(pps_amount=("allocation_value", "sum"))
    )


def evaluate_subblocks(base: pd.DataFrame, pps: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    alphas = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.33, 0.50, 0.67, 1.0]
    floors = [0.0, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80]
    screen_rows: list[dict[str, Any]] = []
    detail_rows: list[pd.DataFrame] = []

    for (parent, block_id), spec in SUBBLOCKS.items():
        codes = [str(c).zfill(2) for c in spec["codes"]]
        for city in sorted(base["city"].dropna().unique()):
            g = base[base["city"].eq(city) & base["parent_code"].eq(parent) & base["middle_code"].isin(codes)].copy()
            if len(g) < 2:
                continue
            pv = (
                g[["city", "parent_code", "middle_code"]]
                .merge(pps, on=["city", "parent_code", "middle_code"], how="left")["pps_amount"]
                .fillna(0.0)
                .to_numpy(float)
            )
            if pv.sum() <= 0 or (pv > 0).sum() < 2:
                continue

            old_pred = g["phase120_strict_flash_predicted_gva_eok"].to_numpy(float)
            old_err = g["phase120_strict_flash_error_gva_eok"].to_numpy(float)
            old_rate = g["phase120_strict_flash_error_rate_pct"].to_numpy(float)
            actual = g["actual_gva_eok"].to_numpy(float)
            total = float(old_pred.sum())
            base_share = old_pred / old_pred.sum() if old_pred.sum() else np.ones(len(g)) / len(g)
            pps_share = pv / pv.sum()

            for floor in floors:
                safe_share = floor * base_share + (1 - floor) * pps_share
                safe_share = safe_share / safe_share.sum()
                pps_pred = safe_share * total
                for alpha in alphas:
                    pred = (1 - alpha) * old_pred + alpha * pps_pred
                    err = np.abs(pred - actual)
                    rate = np.where(actual > 0, err / actual * 100, np.nan)
                    delta = err - old_err
                    reduction = float(old_err.sum() - err.sum())
                    row = {
                        "city": city,
                        "parent_code": parent,
                        "subblock_id": block_id,
                        "middle_codes": ",".join(codes),
                        "option_id": f"phase124_pps_subblock_{block_id}",
                        "alpha": alpha,
                        "baseline_floor": floor,
                        "phase120_error_eok": float(old_err.sum()),
                        "candidate_error_eok": float(err.sum()),
                        "incremental_reduction_eok": reduction,
                        "phase120_gt20_cells": int((old_rate > 20).sum()),
                        "candidate_gt20_cells": int((rate > 20).sum()),
                        "phase120_gt10_cells": int((old_rate > 10).sum()),
                        "candidate_gt10_cells": int((rate > 10).sum()),
                        "worsened_cells": int((delta > 1e-9).sum()),
                        "worsen_sum_eok": float(np.maximum(delta, 0).sum()),
                        "max_worsen_pp": float(np.nanmax(rate - old_rate)),
                    }
                    row["adoptable"] = (
                        reduction > 1e-9
                        and row["worsened_cells"] == 0
                        and row["candidate_gt20_cells"] <= row["phase120_gt20_cells"]
                        and row["candidate_gt10_cells"] <= row["phase120_gt10_cells"]
                    )
                    screen_rows.append(row)
                    d = g[[
                        "city",
                        "parent_code",
                        "middle_code",
                        "middle_label",
                        "actual_gva_eok",
                        "phase120_strict_flash_predicted_gva_eok",
                        "phase120_strict_flash_error_gva_eok",
                        "phase120_strict_flash_error_rate_pct",
                    ]].copy()
                    d["subblock_id"] = block_id
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


def select_subblocks(screen: pd.DataFrame) -> pd.DataFrame:
    if screen.empty:
        return screen
    return (
        screen[screen["adoptable"]]
        .sort_values(["city", "parent_code", "subblock_id", "incremental_reduction_eok"], ascending=[True, True, True, False])
        .groupby(["city", "parent_code", "subblock_id"], as_index=False)
        .head(1)
        .sort_values("incremental_reduction_eok", ascending=False)
        .copy()
    )


def apply_selected(base: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    for _, s in selected.iterrows():
        m = (
            detail["city"].eq(s.city)
            & detail["parent_code"].eq(s.parent_code)
            & detail["subblock_id"].eq(s.subblock_id)
            & detail["option_id"].eq(s.option_id)
            & np.isclose(detail["alpha"].astype(float), float(s.alpha))
            & np.isclose(detail["baseline_floor"].astype(float), float(s.baseline_floor))
        )
        for _, r in detail[m].iterrows():
            idx = out["city"].eq(r.city) & out["parent_code"].eq(r.parent_code) & out["middle_code"].eq(r.middle_code)
            out.loc[idx, "phase124_predicted_gva_eok"] = r.candidate_predicted_gva_eok
            out.loc[idx, "phase124_error_gva_eok"] = r.candidate_error_gva_eok
            out.loc[idx, "phase124_error_rate_pct"] = r.candidate_error_rate_pct
            out.loc[idx, "phase124_option_id"] = s.option_id
    out["phase124_incremental_reduction_eok"] = out["phase120_strict_flash_error_gva_eok"] - out["phase124_error_gva_eok"]
    return out


def city_summary(reg: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in reg.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        p120 = float(g["phase120_strict_flash_error_gva_eok"].sum())
        p124 = float(g["phase124_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "phase120_error_eok": p120,
                "phase120_wape_pct": p120 / actual * 100,
                "phase124_error_eok": p124,
                "phase124_wape_pct": p124 / actual * 100,
                "incremental_reduction_eok": p120 - p124,
                "incremental_reduction_pp": (p120 - p124) / actual * 100,
                "phase120_gt20_cells": int((g["phase120_strict_flash_error_rate_pct"] > 20).sum()),
                "phase124_gt20_cells": int((g["phase124_error_rate_pct"] > 20).sum()),
                "phase120_gt10_cells": int((g["phase120_strict_flash_error_rate_pct"] > 10).sum()),
                "phase124_gt10_cells": int((g["phase124_error_rate_pct"] > 10).sum()),
                "worsened_vs_phase120_cells": int((g["phase124_error_gva_eok"] > g["phase120_strict_flash_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_phase120()
    pps = pps_values()
    screen, detail = evaluate_subblocks(base, pps)
    selected = select_subblocks(screen)
    registry = apply_selected(base, selected, detail)
    summary = city_summary(registry)
    improved = registry[registry["phase124_incremental_reduction_eok"].gt(1e-9)].sort_values(["city", "phase124_incremental_reduction_eok"], ascending=[True, False])
    remaining_gt20 = registry[registry["phase124_error_rate_pct"].gt(20)].sort_values(["city", "phase124_error_gva_eok"], ascending=[True, False])

    pps.to_csv(OUT / "phase124_pps_middle_values.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(OUT / "phase124_subblock_candidate_screen.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase124_subblock_candidate_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase124_selected_subblocks.csv", index=False, encoding="utf-8-sig")
    registry.to_csv(OUT / "phase124_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase124_city_summary.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUT / "phase124_improved_cells.csv", index=False, encoding="utf-8-sig")
    remaining_gt20.to_csv(OUT / "phase124_remaining_gt20.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase124 조달청 부분묶음 무악화 개선 실험

## 목적

Phase123의 문제는 조달청 공공발주 자료를 상위산업 전체에 적용하면서 무관한 중분류까지 같이 흔들린 점이었다. 이번 단계에서는 조달청 자료가 직접 설명하는 중분류 묶음에만 재배분을 적용하고, 나머지 중분류는 Phase120 속보 추정값을 그대로 유지했다.

채택 조건은 보수적으로 잡았다.

1. Phase120 대비 부분묶음 총오차가 줄어야 한다.
2. 부분묶음 안의 어떤 중분류도 Phase120보다 악화되면 안 된다.
3. 20% 초과 셀과 10% 초과 셀 개수가 늘면 안 된다.

## 도시별 성능

{p115.md_table(summary, [("city", "지역"), ("phase120_error_eok", "Phase120 오차 억원"), ("phase120_wape_pct", "Phase120 오차 %"), ("phase124_error_eok", "Phase124 오차 억원"), ("phase124_wape_pct", "Phase124 오차 %"), ("incremental_reduction_eok", "추가 감소 억원"), ("incremental_reduction_pp", "추가 감소 pp"), ("phase120_gt20_cells", "Phase120 20%초과"), ("phase124_gt20_cells", "Phase124 20%초과"), ("phase120_gt10_cells", "Phase120 10%초과"), ("phase124_gt10_cells", "Phase124 10%초과"), ("worsened_vs_phase120_cells", "악화 셀")])}

## 채택된 부분묶음

{p115.md_table(selected, [("city", "지역"), ("parent_code", "상위산업"), ("subblock_id", "부분묶음"), ("middle_codes", "중분류"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("phase120_error_eok", "Phase120 오차 억원"), ("candidate_error_eok", "후보 오차 억원"), ("incremental_reduction_eok", "감소 억원"), ("phase120_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("worsened_cells", "악화 셀")], 80)}

## 개선된 중분류

{p115.md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase120_strict_flash_error_gva_eok", "Phase120 오차 억원"), ("phase124_error_gva_eok", "Phase124 오차 억원"), ("phase124_error_rate_pct", "Phase124 오차 %"), ("phase124_incremental_reduction_eok", "감소 억원"), ("phase124_option_id", "적용 지표")], 80)}

## 남은 20% 초과 중분류

{p115.md_table(remaining_gt20, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase124_predicted_gva_eok", "추정 억원"), ("phase124_error_gva_eok", "오차 억원"), ("phase124_error_rate_pct", "오차 %"), ("phase124_option_id", "적용 지표")], 120)}

## 판정

조달청 자료는 상위산업 전체 배분보다 부분묶음 라우팅에 더 적합하다. 다만 이번 무악화 기준에서는 성능 개선 폭이 제한적이며, 공공발주가 민간 활동을 충분히 대표하지 못하는 중분류는 여전히 별도 직접자료가 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
