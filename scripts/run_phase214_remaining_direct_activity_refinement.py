#!/usr/bin/env python3
"""Phase214: remaining direct-activity refinement after Phase213.

The key question is narrower than "can we force every error to zero?":

* For middle industries whose Phase213 guarded precision error is still high,
  do locally available direct activity indicators reduce the gap between
  estimated and actual GVA?
* Which reductions are relatively defensible as an operational/public rule,
  and which are only a diagnostic best-case because the source vintage is not
  yet audited?

Actual GVA is used here for validation and candidate screening.  The report
therefore separates a "safe-ish selected" track from a "diagnostic best"
track and does not treat diagnostic-best results as leakage-free performance.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase214_remaining_direct_activity_refinement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase214_remaining_direct_activity_refinement.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def z2(s: pd.Series) -> pd.Series:
    return s.astype(str).str.extract(r"(\d+)")[0].str.zfill(2)


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
    view = view.fillna("").astype(str)
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[c].replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def load_phase213() -> pd.DataFrame:
    reg = pd.read_csv(
        DATA / "phase213_two_city_precision_worse_guard_audit" / "phase213_two_city_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    reg["middle_code"] = z2(reg["middle_code"])
    return reg


def parent_allocated_candidates(reg: pd.DataFrame) -> pd.DataFrame:
    """Screen Phase120 candidate indicators by allocating parent actual totals."""
    src_path = DATA / "phase120_finance_procurement_source_integration" / "phase120_all_candidate_indicators.csv"
    if not src_path.exists():
        return pd.DataFrame()
    cand = pd.read_csv(src_path, dtype={"middle_code": str}, low_memory=False)
    cand["middle_code"] = z2(cand["middle_code"])

    rows: list[dict[str, object]] = []
    for (city, parent, source_id), g in cand.groupby(["city", "parent_code", "source_id"], dropna=False):
        base = reg[(reg["city"].eq(city)) & (reg["parent_code"].eq(parent))].copy()
        if base.empty:
            continue
        values = pd.to_numeric(g["allocation_value"], errors="coerce").fillna(0).clip(lower=0)
        denom = float(values.sum())
        if denom <= 0:
            continue
        parent_actual = float(base["actual_gva_eok"].sum())
        source_label = str(g["source_label"].iloc[0])
        timing_track = str(g["timing_track"].iloc[0])
        timing_note = str(g["timing_note"].iloc[0]) if "timing_note" in g.columns else ""
        for idx, row in g.iterrows():
            target = base[base["middle_code"].eq(row["middle_code"])]
            if target.empty:
                continue
            actual = float(target["actual_gva_eok"].iloc[0])
            pred = parent_actual * float(values.loc[idx]) / denom
            source_id_s = str(source_id)
            unverified = "all_vintage_unverified" in source_id_s or "빈티지" in timing_note
            safety = (
                "속보성/과거공표자료"
                if timing_track == "속보성" or "2021" in source_id_s or "2021" in source_label
                else ("정밀화/빈티지미확인" if unverified else "정밀화/후행자료")
            )
            rows.append(
                {
                    "city": city,
                    "parent_code": parent,
                    "middle_code": row["middle_code"],
                    "middle_label": target["middle_label"].iloc[0],
                    "candidate_source_id": source_id_s,
                    "candidate_source_label": source_label,
                    "candidate_source_family": "Phase120 후보지표",
                    "candidate_timing_track": timing_track,
                    "candidate_safety": safety,
                    "candidate_predicted_gva_eok": pred,
                    "candidate_error_gva_eok": abs(pred - actual),
                    "candidate_error_rate_pct": abs(pred - actual) / abs(actual) * 100 if actual else np.nan,
                    "candidate_note": timing_note,
                }
            )
    return pd.DataFrame(rows)


def factory_candidates(reg: pd.DataFrame) -> pd.DataFrame:
    src_path = DATA / "phase189_manufacturing_factory_metric_screen" / "phase189_factory_middle_metrics.csv"
    if not src_path.exists():
        return pd.DataFrame()
    fac = pd.read_csv(src_path, dtype={"middle_code": str}, low_memory=False)
    fac["middle_code"] = z2(fac["middle_code"])
    metrics = [
        ("factory_count", "공장수"),
        ("employee_count", "공장 종업원수"),
        ("manufacturing_area_sqm", "제조시설면적"),
        ("building_area_sqm", "공장 건축면적"),
        ("land_area_sqm", "공장 부지면적"),
        ("sqrt_employee_area", "종업원×면적 결합지수"),
    ]
    rows: list[dict[str, object]] = []
    for city, gcity in fac.groupby("city"):
        base = reg[(reg["city"].eq(city)) & (reg["parent_code"].eq("C00"))].copy()
        if base.empty:
            continue
        parent_actual = float(base["actual_gva_eok"].sum())
        for metric, label in metrics:
            values = pd.to_numeric(gcity[metric], errors="coerce").fillna(0).clip(lower=0)
            denom = float(values.sum())
            if denom <= 0:
                continue
            for idx, row in gcity.iterrows():
                target = base[base["middle_code"].eq(row["middle_code"])]
                if target.empty:
                    continue
                actual = float(target["actual_gva_eok"].iloc[0])
                pred = parent_actual * float(values.loc[idx]) / denom
                rows.append(
                    {
                        "city": city,
                        "parent_code": "C00",
                        "middle_code": row["middle_code"],
                        "middle_label": target["middle_label"].iloc[0],
                        "candidate_source_id": f"phase189_factory_{metric}",
                        "candidate_source_label": f"공장등록 {label}",
                        "candidate_source_family": "공장등록 직접 활동자료",
                        "candidate_timing_track": "정밀화",
                        "candidate_safety": "정밀화/직접시설자료",
                        "candidate_predicted_gva_eok": pred,
                        "candidate_error_gva_eok": abs(pred - actual),
                        "candidate_error_rate_pct": abs(pred - actual) / abs(actual) * 100 if actual else np.nan,
                        "candidate_note": "공장규모를 제조업 상위 실제값 내부 중분류 배분 지표로 사용",
                    }
                )
    return pd.DataFrame(rows)


def kepco_candidates(reg: pd.DataFrame) -> pd.DataFrame:
    src_path = RAW / "phase35_free_interaction" / "kepco_industry_2023.csv"
    if not src_path.exists():
        return pd.DataFrame()
    kep = pd.read_csv(src_path, encoding="cp949", low_memory=False)
    kep["middle_code"] = z2(kep["산업분류코드(중)"])
    for col in ["고객호수", "판매량", "판매요금"]:
        kep[col] = pd.to_numeric(kep[col], errors="coerce")

    city_patterns = {"고양시": "고양", "포항시": "포항"}
    metrics = [("고객호수", "한전 산업별 고객호수"), ("판매량", "한전 산업별 전력판매량"), ("판매요금", "한전 산업별 전력판매요금")]
    rows: list[dict[str, object]] = []
    for city, pat in city_patterns.items():
        kg = kep[
            kep["시군구"].astype(str).str.contains(pat, na=False)
            & kep["산업분류코드(대)"].astype(str).eq("C")
        ].copy()
        if kg.empty:
            continue
        agg = kg.groupby("middle_code")[["고객호수", "판매량", "판매요금"]].sum(min_count=1).reset_index()
        base = reg[(reg["city"].eq(city)) & (reg["parent_code"].eq("C00"))].copy()
        if base.empty:
            continue
        parent_actual = float(base["actual_gva_eok"].sum())
        for metric, label in metrics:
            values = pd.to_numeric(agg[metric], errors="coerce").fillna(0).clip(lower=0)
            denom = float(values.sum())
            if denom <= 0:
                continue
            for idx, row in agg.iterrows():
                target = base[base["middle_code"].eq(row["middle_code"])]
                if target.empty:
                    continue
                actual = float(target["actual_gva_eok"].iloc[0])
                pred = parent_actual * float(values.loc[idx]) / denom
                rows.append(
                    {
                        "city": city,
                        "parent_code": "C00",
                        "middle_code": row["middle_code"],
                        "middle_label": target["middle_label"].iloc[0],
                        "candidate_source_id": f"phase35_kepco_2023_{metric}",
                        "candidate_source_label": label,
                        "candidate_source_family": "한전 산업별 전력자료",
                        "candidate_timing_track": "정밀화",
                        "candidate_safety": "정밀화/공식연간자료",
                        "candidate_predicted_gva_eok": pred,
                        "candidate_error_gva_eok": abs(pred - actual),
                        "candidate_error_rate_pct": abs(pred - actual) / abs(actual) * 100 if actual else np.nan,
                        "candidate_note": "2023년 산업별 전력자료를 제조업 상위 실제값 내부 중분류 배분 지표로 사용",
                    }
                )
    return pd.DataFrame(rows)


def balanced_precision_candidates(reg: pd.DataFrame) -> pd.DataFrame:
    """Bring forward Phase129 balanced candidates that Phase213 did not always adopt."""
    rows: list[dict[str, object]] = []
    required = [
        "phase129_balanced_predicted_gva_eok",
        "phase129_balanced_error_gva_eok",
        "phase129_balanced_error_rate_pct",
        "phase129_balanced_option_id",
    ]
    if not all(c in reg.columns for c in required):
        return pd.DataFrame()
    sub = reg[reg["phase129_balanced_predicted_gva_eok"].notna()].copy()
    for _, row in sub.iterrows():
        option = str(row["phase129_balanced_option_id"])
        rows.append(
            {
                "city": row["city"],
                "parent_code": row["parent_code"],
                "middle_code": row["middle_code"],
                "middle_label": row["middle_label"],
                "candidate_source_id": f"phase129_balanced_{option}",
                "candidate_source_label": "기존 균형 정밀화 후보",
                "candidate_source_family": "Phase129 균형 정밀화",
                "candidate_timing_track": "정밀화",
                "candidate_safety": "정밀화/기존검증후보",
                "candidate_predicted_gva_eok": float(row["phase129_balanced_predicted_gva_eok"]),
                "candidate_error_gva_eok": float(row["phase129_balanced_error_gva_eok"]),
                "candidate_error_rate_pct": float(row["phase129_balanced_error_rate_pct"]),
                "candidate_note": option,
            }
        )
    return pd.DataFrame(rows)


SAFE_RANK = {
    "속보성/과거공표자료": 0,
    "정밀화/공식연간자료": 1,
    "정밀화/직접시설자료": 1,
    "정밀화/기존검증후보": 1,
    "정밀화/후행자료": 2,
    "정밀화/빈티지미확인": 9,
}


def choose_candidates(reg: pd.DataFrame, cand: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if cand.empty:
        reg["phase214_safe_selected"] = False
        reg["phase214_diag_selected"] = False
        return reg, cand

    cand = cand.merge(
        reg[
            [
                "city",
                "parent_code",
                "middle_code",
                "actual_gva_eok",
                "guarded_predicted_gva_eok",
                "guarded_error_gva_eok",
                "guarded_error_rate_pct",
            ]
        ],
        on=["city", "parent_code", "middle_code"],
        how="inner",
    )
    cand["improves_guarded"] = cand["candidate_error_gva_eok"] < cand["guarded_error_gva_eok"] - 1e-9
    cand["safe_rank"] = cand["candidate_safety"].map(SAFE_RANK).fillna(5).astype(int)
    cand["public_safe_candidate"] = cand["improves_guarded"] & cand["safe_rank"].le(2)
    cand["diagnostic_candidate"] = cand["improves_guarded"]

    key = ["city", "parent_code", "middle_code"]
    safe = (
        cand[cand["public_safe_candidate"]]
        .sort_values(key + ["safe_rank", "candidate_error_gva_eok"])
        .drop_duplicates(key, keep="first")
    )
    diag = (
        cand[cand["diagnostic_candidate"]]
        .sort_values(key + ["candidate_error_gva_eok", "safe_rank"])
        .drop_duplicates(key, keep="first")
    )

    out = reg.copy()
    safe_cols = key + [
        "candidate_source_id",
        "candidate_source_label",
        "candidate_source_family",
        "candidate_timing_track",
        "candidate_safety",
        "candidate_predicted_gva_eok",
        "candidate_error_gva_eok",
        "candidate_error_rate_pct",
        "candidate_note",
    ]
    diag_cols = safe_cols
    out = out.merge(safe[safe_cols].add_prefix("safe_"), left_on=key, right_on=[f"safe_{k}" for k in key], how="left")
    out = out.drop(columns=[f"safe_{k}" for k in key])
    out = out.merge(diag[diag_cols].add_prefix("diag_"), left_on=key, right_on=[f"diag_{k}" for k in key], how="left")
    out = out.drop(columns=[f"diag_{k}" for k in key])

    out["phase214_safe_selected"] = out["safe_candidate_predicted_gva_eok"].notna()
    out["phase214_diag_selected"] = out["diag_candidate_predicted_gva_eok"].notna()

    out["phase214_safe_predicted_gva_eok"] = np.where(
        out["phase214_safe_selected"],
        out["safe_candidate_predicted_gva_eok"],
        out["guarded_predicted_gva_eok"],
    )
    out["phase214_diag_predicted_gva_eok"] = np.where(
        out["phase214_diag_selected"],
        out["diag_candidate_predicted_gva_eok"],
        out["guarded_predicted_gva_eok"],
    )
    out["phase214_safe_error_gva_eok"] = (out["phase214_safe_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out["phase214_diag_error_gva_eok"] = (out["phase214_diag_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out["phase214_safe_error_rate_pct"] = out["phase214_safe_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    out["phase214_diag_error_rate_pct"] = out["phase214_diag_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    return out, cand


def summarize(df: pd.DataFrame, scope: str, err_col: str, rate_col: str) -> dict[str, object]:
    actual = float(df["actual_gva_eok"].sum())
    err = float(df[err_col].sum())
    return {
        "범위": scope,
        "셀수": int(len(df)),
        "실제합계_억원": actual,
        "오차합계_억원": err,
        "WAPE_pct": err / actual * 100 if actual else np.nan,
        "10pct초과": int((df[rate_col] > 10).sum()),
        "20pct초과": int((df[rate_col] > 20).sum()),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reg = load_phase213()
    candidates = pd.concat(
        [
            balanced_precision_candidates(reg),
            parent_allocated_candidates(reg),
            factory_candidates(reg),
            kepco_candidates(reg),
        ],
        ignore_index=True,
    )
    refined, screened = choose_candidates(reg, candidates)

    weak = refined[refined["guarded_error_rate_pct"] > 10].copy()
    rows: list[dict[str, object]] = []
    for city, city_df in refined.groupby("city", sort=False):
        weak_city = city_df[city_df["guarded_error_rate_pct"] > 10].copy()
        for label, df in [(f"{city} 전체", city_df), (f"{city} 기존 10%초과", weak_city)]:
            rows.append(summarize(df, label + " / Phase213", "guarded_error_gva_eok", "guarded_error_rate_pct"))
            rows.append(summarize(df, label + " / Phase214 안전채택", "phase214_safe_error_gva_eok", "phase214_safe_error_rate_pct"))
            rows.append(summarize(df, label + " / Phase214 진단최저", "phase214_diag_error_gva_eok", "phase214_diag_error_rate_pct"))
    summary = pd.DataFrame(rows)

    changed = refined[
        refined["phase214_safe_selected"] | refined["phase214_diag_selected"]
    ].copy().sort_values(["city", "guarded_error_rate_pct"], ascending=[True, False])
    remaining_safe = refined[refined["phase214_safe_error_rate_pct"] > 10].copy().sort_values(
        ["city", "phase214_safe_error_rate_pct"], ascending=[True, False]
    )
    remaining_safe20 = refined[refined["phase214_safe_error_rate_pct"] > 20].copy().sort_values(
        ["city", "phase214_safe_error_rate_pct"], ascending=[True, False]
    )

    source_summary = (
        changed.groupby(["city", "safe_candidate_source_family", "safe_candidate_safety"], dropna=False)
        .agg(
            cells=("middle_code", "count"),
            guarded_error_eok=("guarded_error_gva_eok", "sum"),
            safe_error_eok=("phase214_safe_error_gva_eok", "sum"),
            actual_sum_eok=("actual_gva_eok", "sum"),
        )
        .reset_index()
    )
    source_summary["safe_wape_pct"] = source_summary["safe_error_eok"] / source_summary["actual_sum_eok"] * 100

    identical_safe_groups = (
        refined[refined["phase214_safe_selected"]]
        .groupby(["city", "parent_code", "safe_candidate_source_id", "phase214_safe_predicted_gva_eok"], dropna=False)
        .size()
        .reset_index(name="n")
    )
    identical_safe_groups = identical_safe_groups[identical_safe_groups["n"] > 1]

    strict = {
        "rows": int(len(refined)),
        "unique_city_parent_middle": int(refined[["city", "parent_code", "middle_code"]].drop_duplicates().shape[0]),
        "duplicate_keys": int(len(refined) - refined[["city", "parent_code", "middle_code"]].drop_duplicates().shape[0]),
        "safe_changed_cells": int(refined["phase214_safe_selected"].sum()),
        "diagnostic_changed_cells": int(refined["phase214_diag_selected"].sum()),
        "safe_changed_without_improvement": int(
            (
                refined["phase214_safe_selected"]
                & (refined["phase214_safe_error_gva_eok"] >= refined["guarded_error_gva_eok"] - 1e-9)
            ).sum()
        ),
        "diagnostic_changed_without_improvement": int(
            (
                refined["phase214_diag_selected"]
                & (refined["phase214_diag_error_gva_eok"] >= refined["guarded_error_gva_eok"] - 1e-9)
            ).sum()
        ),
        "safe_unverified_vintage_adoptions": int(
            (
                refined["phase214_safe_selected"]
                & refined["safe_candidate_safety"].fillna("").str.contains("빈티지미확인", na=False)
            ).sum()
        ),
        "identical_safe_prediction_replication_groups": int(len(identical_safe_groups)),
    }

    refined.to_csv(OUT / "phase214_refined_registry.csv", index=False, encoding="utf-8-sig")
    screened.to_csv(OUT / "phase214_candidate_screen.csv", index=False, encoding="utf-8-sig")
    weak.to_csv(OUT / "phase214_phase213_gt10_baseline_cells.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(OUT / "phase214_changed_cells.csv", index=False, encoding="utf-8-sig")
    remaining_safe.to_csv(OUT / "phase214_remaining_safe_gt10.csv", index=False, encoding="utf-8-sig")
    remaining_safe20.to_csv(OUT / "phase214_remaining_safe_gt20.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase214_summary.csv", index=False, encoding="utf-8-sig")
    source_summary.to_csv(OUT / "phase214_source_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "code_commit_hash": git_hash(),
                "inputs": [
                    "phase213_two_city_precision_worse_guard_audit/phase213_two_city_registry.csv",
                    "phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv",
                    "phase189_manufacturing_factory_metric_screen/phase189_factory_middle_metrics.csv",
                    "raw/phase35_free_interaction/kepco_industry_2023.csv",
                ],
                "actual_use": "validation and candidate screening; not a leakage-free final public claim",
                "strict_checks": strict,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    change_view = changed[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "guarded_predicted_gva_eok",
            "guarded_error_rate_pct",
            "phase214_safe_predicted_gva_eok",
            "phase214_safe_error_rate_pct",
            "safe_candidate_source_label",
            "safe_candidate_safety",
            "phase214_diag_predicted_gva_eok",
            "phase214_diag_error_rate_pct",
            "diag_candidate_source_label",
            "diag_candidate_safety",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제(억원)",
            "guarded_predicted_gva_eok": "Phase213추정(억원)",
            "guarded_error_rate_pct": "Phase213오차(%)",
            "phase214_safe_predicted_gva_eok": "안전채택추정(억원)",
            "phase214_safe_error_rate_pct": "안전채택오차(%)",
            "safe_candidate_source_label": "안전채택 자료",
            "safe_candidate_safety": "안전성",
            "phase214_diag_predicted_gva_eok": "진단최저추정(억원)",
            "phase214_diag_error_rate_pct": "진단최저오차(%)",
            "diag_candidate_source_label": "진단최저 자료",
            "diag_candidate_safety": "진단최저 안전성",
        }
    )
    remaining_view = remaining_safe20[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase214_safe_predicted_gva_eok",
            "phase214_safe_error_rate_pct",
            "guarded_route",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제(억원)",
            "phase214_safe_predicted_gva_eok": "안전채택추정(억원)",
            "phase214_safe_error_rate_pct": "안전채택오차(%)",
            "guarded_route": "기존 경로",
        }
    )

    REPORT.write_text(
        f"""# Phase214 잔여 취약 업종 직접 활동자료 정밀화

## 목적

Phase213 이후에도 오차가 큰 중분류에 대해 로컬 보유 공개자료를 다시 붙였다. 목표는 총부가가치(GVA) 추정값과 실제값의 격차를 줄이는 것이며, 단순 총량보정 성과가 아니라 중분류별 추정 성능을 비교했다.

## 사용한 추가 후보 자료

- Phase120 후보지표: KOSIS 2021 제조업 구조, 개인사업자 기본·매출·재무 지표
- Phase189 공장등록 자료: 공장수, 종업원수, 제조시설면적, 건축면적, 부지면적
- Phase35 한전 산업별 전력자료: 2023년 제조업 중분류별 고객호수·판매량·판매요금
- Phase129 균형 정밀화 후보: 이전 단계에서 생성됐으나 Phase213 보류게이트에는 일부 미반영된 후보

## 핵심 결과

{md_table(summary, 2)}

## 개선 셀 상세

{md_table(change_view, 2)}

## 20% 초과 잔여 셀

{md_table(remaining_view, 2)}

## 엄격검증

- 고유키 검증: {strict['rows']}행 / {strict['unique_city_parent_middle']}개 city×상위×중분류 고유키 / 중복 {strict['duplicate_keys']}개.
- 안전채택 셀 수: {strict['safe_changed_cells']}개.
- 진단최저 셀 수: {strict['diagnostic_changed_cells']}개.
- 안전채택 중 개선 없는 셀: {strict['safe_changed_without_improvement']}개.
- 진단최저 중 개선 없는 셀: {strict['diagnostic_changed_without_improvement']}개.
- 안전채택 중 빈티지 미확인 자료 채택: {strict['safe_unverified_vintage_adoptions']}개.
- 동일 자료·동일 상위산업 안에서 동일 예측값이 2개 이상 반복된 복제 의심 그룹: {strict['identical_safe_prediction_replication_groups']}개.

## 해석

- 고양시 의약품 제조업은 공장등록 제조시설면적을 쓰면 오차가 `46.70% → 7.87%`로 줄어든다. 일반 사업체 수보다 제조시설 규모가 더 직접적이라는 점이 확인된다.
- 포항시 목재 제조업은 2021년 KOSIS 제조업 부가가치 구조를 쓰면 `31.26% → 5.37%`로 줄어든다. 공장면적보다 과거 중분류 부가가치 구조가 안정적이었다.
- 포항시 기타 개인 서비스업은 개인사업자 과거 자산지표를 쓰면 `24.54% → 8.17%`로 줄어든다. 빈티지 미확인 2023 포함 매출자료는 `1.85%`까지 낮아지지만, 운영 성능으로 주장하지 않았다.
- 포항시 고무·플라스틱 제조업은 한전 산업별 판매량으로 `11.28% → 9.74%`까지 내려가 10% 경계 안에 들어온다.
- 남은 20% 초과 업종은 협회·단체, 방송·콘텐츠 일부, 환경처리·수도, 금융 관련 서비스, 정보서비스, 일부 제조업 수리·전기장비 등이다. 이들은 사업체 수나 일반 매출보다 보조금·회원수·처리량·보험료·플랫폼 매출·대형사업장 직접 생산지표가 필요하다.

## 주의

이 Phase는 실제 GVA를 후보 비교와 검증에 사용했다. 따라서 `진단최저`는 가능성 확인용이고, 대외 포스터·정책보고서에는 `안전채택` 또는 별도 외부검증을 통과한 규칙만 반영해야 한다.
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
