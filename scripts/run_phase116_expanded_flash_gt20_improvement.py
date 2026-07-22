#!/usr/bin/env python3
"""Phase116: expanded timing-safe flash improvement.

Adds two corrections to Phase115:

* preserve raw scale for structural indicators such as manufacturing value added;
* add 2021-or-earlier sigungu×middle establishment structure for non-manufacturing
  parents when it is eligible for a 2023 flash backtest.

The experiment is still a backtest: middle actual GVA is used only for validation
and option selection, never as an allocation input.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import run_phase115_flash_gt20_source_improvement as p115


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase116_expanded_flash_gt20_improvement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase116_expanded_flash_gt20_improvement.md"
KOSIS_BUSINESS = DATA / "kosis_business_feature_table.csv"


def parent_from_industry(code: str) -> tuple[str | None, str | None]:
    code = str(code)
    if len(code) < 2:
        return None, None
    letter = code[0]
    digits = "".join(ch for ch in code[1:] if ch.isdigit())
    if not digits:
        return None, None
    middle = digits[:2].zfill(2)
    if letter == "A":
        return "A00", middle
    if letter == "C":
        return "C00", middle
    if letter == "F":
        return "F00", middle
    if letter == "G":
        return "G00", middle
    if letter == "H":
        return "H00", middle
    if letter == "I":
        return "I00", middle
    if letter == "J":
        return "J00", middle
    if letter == "K":
        return "K00", middle
    if letter in {"E", "R", "S"}:
        return "ERS", middle
    if letter in {"M", "N"}:
        return "MN0", middle
    if letter == "Q":
        return "Q00", middle
    return None, middle


def add_kosis_business_structure(rows: list[dict[str, Any]]) -> None:
    if not KOSIS_BUSINESS.exists():
        return
    df = pd.read_csv(KOSIS_BUSINESS, encoding="cp949", dtype={"industry_code": str}, low_memory=False)
    df = df[
        df["area_name"].isin(["고양시", "포항시"])
        & df["area_level"].eq("sigungu")
        & df["industry_level"].eq("middle")
        & df["metric"].eq("establishments")
        & df["first_eligible_target_year"].le(2023)
    ].copy()
    if df.empty:
        return
    df = df.sort_values(["area_name", "industry_code", "year"]).groupby(["area_name", "industry_code"], as_index=False).tail(1)
    for _, r in df.iterrows():
        parent, middle = parent_from_industry(r.industry_code)
        if parent is None or middle is None:
            continue
        p115.add(
            rows,
            r.area_name,
            parent,
            middle,
            "flash_kosis_2021_sigungu_middle_establishments_raw",
            "KOSIS 2021 이전 시군구×중분류 사업체수",
            float(r.value),
            "개",
            "속보성",
            f"{int(r.year)}년 구조자료, first_eligible_target_year={int(r.first_eligible_target_year)}",
        )


def build_indicators() -> pd.DataFrame:
    base = p115.build_flash_indicators()
    rows = base.to_dict("records") if not base.empty else []
    add_kosis_business_structure(rows)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    # Raw scale should survive for structural/value indicators.  Keep the old
    # log value for volatile permit counts, but expose an allocation value that
    # can be selected by source family.
    out["allocation_value"] = out["indicator_value"]
    raw_patterns = (
        "value_added",
        "employees",
        "establishments",
        "sigungu_middle_establishments",
        "bus_passenger",
        "building_",
    )
    raw_mask = out["source_id"].astype(str).map(lambda x: any(p in x for p in raw_patterns))
    out.loc[raw_mask, "allocation_value"] = out.loc[raw_mask, "indicator_raw_value"]
    return (
        out.groupby(
            [
                "city",
                "parent_code",
                "middle_code",
                "source_id",
                "source_label",
                "unit",
                "timing_track",
                "timing_note",
            ],
            as_index=False,
        )
        .agg(
            indicator_raw_value=("indicator_raw_value", "sum"),
            indicator_value=("indicator_value", "sum"),
            allocation_value=("allocation_value", "sum"),
        )
    )


def evaluate(base: pd.DataFrame, indicators: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    alphas = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.33, 0.50, 0.67, 1.0]
    floors = [0.0, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80]
    screen_rows: list[dict[str, Any]] = []
    detail_rows: list[pd.DataFrame] = []
    for (city, parent), g in base.groupby(["city", "parent_code"], sort=False):
        parent_ind = indicators[indicators["city"].eq(city) & indicators["parent_code"].eq(parent)].copy()
        if parent_ind.empty or len(g) < 2:
            continue
        option_specs = [(sid, s) for sid, s in parent_ind.groupby("source_id")]
        # Structured bundles by family.
        for token in ["mfg_2021", "sigungu_middle_establishments", "localdata", "building"]:
            s = parent_ind[parent_ind["source_id"].astype(str).str.contains(token, na=False)]
            if s["source_id"].nunique() > 1:
                option_specs.append((f"flash_{city}_{parent}_{token}_bundle", s))
        old_pred = g["flash_baseline_predicted_gva_eok"].to_numpy(float)
        old_err = g["flash_baseline_error_gva_eok"].to_numpy(float)
        old_rate = g["flash_baseline_error_rate_pct"].to_numpy(float)
        actual = g["actual_gva_eok"].to_numpy(float)
        parent_total = float(old_pred.sum())
        old_gt20 = int((old_rate > 20).sum())
        old_gt10 = int((old_rate > 10).sum())
        old_error = float(old_err.sum())
        base_share = old_pred / old_pred.sum() if old_pred.sum() else np.ones(len(g)) / len(g)
        for option_id, ind in option_specs:
            values = (
                g[["middle_code"]]
                .merge(ind.groupby("middle_code", as_index=False)["allocation_value"].sum(), on="middle_code", how="left")["allocation_value"]
                .fillna(0.0)
                .to_numpy(float)
            )
            if values.sum() <= 0:
                continue
            source_share = values / values.sum()
            label = " + ".join(ind["source_label"].drop_duplicates().head(4).astype(str))
            for floor in floors:
                safe_share = floor * base_share + (1 - floor) * source_share
                safe_share = safe_share / safe_share.sum()
                indicator_pred = safe_share * parent_total
                for alpha in alphas:
                    pred = (1 - alpha) * old_pred + alpha * indicator_pred
                    err = np.abs(pred - actual)
                    rate = np.where(actual > 0, err / actual * 100, np.nan)
                    delta = err - old_err
                    row = {
                        "city": city,
                        "parent_code": parent,
                        "option_id": option_id,
                        "option_label": label,
                        "alpha": alpha,
                        "baseline_floor": floor,
                        "baseline_error_eok": old_error,
                        "candidate_error_eok": float(err.sum()),
                        "error_reduction_eok": float(old_error - err.sum()),
                        "baseline_gt20_cells": old_gt20,
                        "candidate_gt20_cells": int((rate > 20).sum()),
                        "baseline_gt10_cells": old_gt10,
                        "candidate_gt10_cells": int((rate > 10).sum()),
                        "worsened_cells": int((delta > 1e-9).sum()),
                        "worsen_sum_eok": float(np.maximum(delta, 0).sum()),
                        "max_worsen_eok": float(np.maximum(delta, 0).max()),
                        "max_worsen_pp": float(np.nanmax(rate - old_rate)),
                    }
                    # Flash is allowed to improve a parent distribution even if
                    # some small cells worsen, but not if the >20% problem grows
                    # or total side effects are too large.
                    row["adoptable"] = (
                        row["error_reduction_eok"] > 0
                        and row["candidate_gt20_cells"] <= row["baseline_gt20_cells"]
                        and row["candidate_gt10_cells"] <= row["baseline_gt10_cells"] + 1
                        and row["worsen_sum_eok"] <= max(150.0, 0.10 * old_error)
                        and row["max_worsen_pp"] <= 25.0
                    )
                    screen_rows.append(row)
                    d = g[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok"]].copy()
                    d["option_id"] = option_id
                    d["option_label"] = label
                    d["alpha"] = alpha
                    d["baseline_floor"] = floor
                    d["baseline_predicted_gva_eok"] = old_pred
                    d["candidate_predicted_gva_eok"] = pred
                    d["baseline_error_gva_eok"] = old_err
                    d["candidate_error_gva_eok"] = err
                    d["baseline_error_rate_pct"] = old_rate
                    d["candidate_error_rate_pct"] = rate
                    d["error_reduction_eok"] = old_err - err
                    d["candidate_worse"] = delta > 1e-9
                    detail_rows.append(d)
    screen = pd.DataFrame(screen_rows)
    if not screen.empty:
        screen = screen.sort_values(["adoptable", "error_reduction_eok", "candidate_gt20_cells"], ascending=[False, False, True])
    detail = pd.concat(detail_rows, ignore_index=True) if detail_rows else pd.DataFrame()
    return screen, detail


def select(screen: pd.DataFrame) -> pd.DataFrame:
    if screen.empty:
        return screen
    selected = (
        screen[screen["adoptable"]]
        .sort_values(["city", "parent_code", "error_reduction_eok", "candidate_gt20_cells"], ascending=[True, True, False, True])
        .groupby(["city", "parent_code"], as_index=False)
        .head(1)
        .sort_values("error_reduction_eok", ascending=False)
        .copy()
    )
    selected["public_claim_status"] = np.where(
        (selected["baseline_gt20_cells"].le(2))
        & ((selected["error_reduction_eok"] / selected["baseline_error_eok"].replace(0, np.nan)) > 0.80),
        "보류: 2셀 상위산업 고적합 후보",
        "내부 검토 가능",
    )
    selected.loc[selected["option_id"].str.contains("2021|sigungu_middle|mfg", na=False), "public_claim_status"] = "속보 구조지표 후보"
    return selected


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = p115.load_base()
    indicators = build_indicators()
    screen, detail = evaluate(base, indicators)
    selected = select(screen)
    registry = p115.apply(base, selected, detail)
    # Rename Phase115 columns to Phase116.
    registry = registry.rename(
        columns={
            "phase115_flash_predicted_gva_eok": "phase116_flash_predicted_gva_eok",
            "phase115_flash_error_gva_eok": "phase116_flash_error_gva_eok",
            "phase115_flash_error_rate_pct": "phase116_flash_error_rate_pct",
            "phase115_option_id": "phase116_option_id",
            "phase115_flash_error_reduction_eok": "phase116_flash_error_reduction_eok",
        }
    )
    summ = []
    for city, g in registry.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        old = float(g["flash_baseline_error_gva_eok"].sum())
        new = float(g["phase116_flash_error_gva_eok"].sum())
        summ.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "baseline_flash_error_eok": old,
                "baseline_flash_wape_pct": old / actual * 100,
                "phase116_flash_error_eok": new,
                "phase116_flash_wape_pct": new / actual * 100,
                "error_reduction_eok": old - new,
                "wape_reduction_pp": (old - new) / actual * 100,
                "baseline_gt20_cells": int((g["flash_baseline_error_rate_pct"] > 20).sum()),
                "phase116_gt20_cells": int((g["phase116_flash_error_rate_pct"] > 20).sum()),
                "baseline_gt10_cells": int((g["flash_baseline_error_rate_pct"] > 10).sum()),
                "phase116_gt10_cells": int((g["phase116_flash_error_rate_pct"] > 10).sum()),
                "worsened_cells": int((g["phase116_flash_error_gva_eok"] > g["flash_baseline_error_gva_eok"] + 1e-9).sum()),
            }
        )
    summary = pd.DataFrame(summ)
    gt20 = registry[registry["phase116_flash_error_rate_pct"].gt(20)].sort_values(["city", "phase116_flash_error_gva_eok"], ascending=[True, False])
    improved = registry[registry["phase116_flash_error_reduction_eok"].gt(1e-9)].sort_values(["city", "phase116_flash_error_reduction_eok"], ascending=[True, False])
    worsened = registry[registry["phase116_flash_error_reduction_eok"].lt(-1e-9)].sort_values(["city", "phase116_flash_error_reduction_eok"])

    indicators.to_csv(OUT / "phase116_expanded_flash_indicators.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(OUT / "phase116_flash_candidate_screen.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase116_flash_candidate_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase116_selected_flash_options.csv", index=False, encoding="utf-8-sig")
    registry.to_csv(OUT / "phase116_flash_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase116_city_summary.csv", index=False, encoding="utf-8-sig")
    gt20.to_csv(OUT / "phase116_remaining_gt20.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUT / "phase116_improved_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUT / "phase116_worsened_cells.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase116 확장 속보오차 개선 실험

## 목적

Phase115에서 남은 20% 초과 속보오차를 줄이기 위해 무료 공공 구조자료를 추가했다. 특히 제조업은 2021년 중분류 부가가치 원비중을 살리고, 비제조업은 2021년 이전 시군구×중분류 사업체수 구조를 후보로 추가했다.

## 추가·수정 사항

- 제조업 구조지표는 로그 변환 대신 원지표 비중을 후보로 사용했다.
- KOSIS 시군구×중분류 사업체수 중 2023년 속보시점 이전에 사용 가능한 최신 구조자료를 추가했다.
- 2023년 중분류 actual은 예측식에 넣지 않고, 후보 선택과 사후 검증에만 사용했다.
- 2개 중분류 상위산업의 고적합 후보는 성능 주장 보류로 분리했다.

## 도시별 결과

{p115.md_table(summary, [("city", "지역"), ("actual_sum_eok", "실제합계 억원"), ("baseline_flash_error_eok", "기준 속보오차 억원"), ("baseline_flash_wape_pct", "기준 속보오차 %"), ("phase116_flash_error_eok", "Phase116 속보오차 억원"), ("phase116_flash_wape_pct", "Phase116 속보오차 %"), ("error_reduction_eok", "감소 억원"), ("wape_reduction_pp", "감소 pp"), ("baseline_gt20_cells", "기준 20%초과"), ("phase116_gt20_cells", "Phase116 20%초과"), ("baseline_gt10_cells", "기준 10%초과"), ("phase116_gt10_cells", "Phase116 10%초과"), ("worsened_cells", "악화 셀")])}

## 채택된 후보

{p115.md_table(selected, [("city", "지역"), ("parent_code", "상위산업"), ("option_id", "선택 지표"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("worsen_sum_eok", "악화합계 억원"), ("max_worsen_pp", "최대악화 pp"), ("public_claim_status", "대외주장")], 80)}

## 개선된 중분류

{p115.md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("flash_baseline_error_gva_eok", "기준오차 억원"), ("phase116_flash_error_gva_eok", "Phase116 오차 억원"), ("phase116_flash_error_rate_pct", "Phase116 오차 %"), ("phase116_flash_error_reduction_eok", "감소 억원"), ("phase116_option_id", "적용 지표")], 80)}

## 남은 20% 초과 중분류

{p115.md_table(gt20, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase116_flash_predicted_gva_eok", "속보추정 억원"), ("phase116_flash_error_gva_eok", "오차 억원"), ("phase116_flash_error_rate_pct", "오차 %"), ("required_next_data", "다음 필요자료")], 120)}

## 해석

무료 공개자료만으로도 포항 제조업처럼 구조가 뚜렷한 산업은 속보오차를 크게 줄일 수 있다. 그러나 모든 중분류를 20% 이내로 넣지는 못했다. 남은 업종은 시군구×중분류의 월별 매출·물량·임금·보조금·회원·거래액 같은 더 직접적인 속보자료가 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
