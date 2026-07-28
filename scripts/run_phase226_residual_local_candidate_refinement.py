#!/usr/bin/env python3
"""Phase226: residual local candidate refinement.

Test already-collected local public activity sources against the remaining
20%+ precision residuals from Phase217.  This phase is intentionally strict:

* candidates only reallocate inside the source-covered city×parent subblock;
* a candidate is adoptable only if every covered middle-industry cell is no
  worse than Phase217 and at least one residual cell improves;
* results are a validation screen, not an operational rule frozen for future
  years.
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
OUT = DATA / "phase226_residual_local_candidate_refinement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase226_residual_local_candidate_refinement.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

REGISTRY = DATA / "phase217_public_safe_candidate_rerank_audit" / "phase217_reranked_guarded_registry.csv"
RESIDUAL20 = DATA / "phase217_public_safe_candidate_rerank_audit" / "phase217_residual_gt20.csv"
PPS_INDICATORS = DATA / "phase123_pps_procurement_gva_improvement" / "phase123_pps_indicators.csv"
FACTORYON = DATA / "phase224_factoryon_v2_manufacturing_residual_test" / "phase224_factoryon_v2_rows.csv"


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
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def load_base() -> pd.DataFrame:
    reg = pd.read_csv(REGISTRY, dtype={"middle_code": str}, low_memory=False)
    reg["middle_code"] = z2(reg["middle_code"])
    reg["base_predicted_gva_eok"] = reg["phase217_guarded_predicted_gva_eok"]
    reg["base_error_gva_eok"] = reg["phase217_guarded_error_gva_eok"]
    reg["base_error_rate_pct"] = reg["phase217_guarded_error_rate_pct"]
    return reg


def source_rows_pps() -> pd.DataFrame:
    if not PPS_INDICATORS.exists():
        return pd.DataFrame()
    ind = pd.read_csv(PPS_INDICATORS, dtype={"middle_code": str}, low_memory=False)
    ind["middle_code"] = z2(ind["middle_code"])
    # Amount is stronger than notice count, and the _ERS variant duplicates the
    # same values.  Keep one explicit amount source.
    ind = ind[ind["source_id"].eq("flash_pps_procurement_amount")].copy()
    ind = ind[ind["allocation_value"].fillna(0) > 0]
    return ind[["city", "parent_code", "middle_code", "allocation_value"]].assign(
        candidate_source_id="phase226_pps_procurement_amount_subblock",
        candidate_source_label="조달청 공공발주 금액 부분묶음",
        candidate_note="입찰공고 추정가격·배정예산 합계. 계약/낙찰금액이 아니므로 공공발주 의존 중분류에 한해 진단.",
    )


def source_rows_factory() -> pd.DataFrame:
    if not FACTORYON.exists():
        return pd.DataFrame()
    fac = pd.read_csv(FACTORYON, dtype=str, low_memory=False)
    if fac.empty:
        return pd.DataFrame()
    fac = fac[fac["frstFctryRegistDe"].fillna("").str.extract(r"(\d{4})")[0].astype(float).le(2023).fillna(False)].copy()
    fac["middle_code"] = fac["rprsntvIndutyCode"].astype(str).str.extract(r"(\d{2})")[0].str.zfill(2)
    fac["allocation_value"] = pd.to_numeric(fac["allEmplyCo"], errors="coerce").fillna(0)
    fac = fac[fac["allocation_value"] > 0]
    if fac.empty:
        return pd.DataFrame()
    out = fac.groupby(["city", "middle_code"], as_index=False)["allocation_value"].sum()
    out["parent_code"] = "C00"
    return out.assign(
        candidate_source_id="phase226_factoryon_registered_employee_subblock",
        candidate_source_label="FactoryOn 등록공장 종사자 부분묶음",
        candidate_note="2023년 이전 등록공장의 종사자 합계. 출하액/생산액이 아니므로 제조업 일부 중분류 진단용.",
    )


def evaluate_candidate(base: pd.DataFrame, source: pd.DataFrame, residual_keys: set[tuple[str, str, str]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail_rows = []
    selected_blocks = []
    if source.empty:
        return pd.DataFrame(), pd.DataFrame()

    for (city, parent, source_id), src in source.groupby(["city", "parent_code", "candidate_source_id"], sort=False):
        block = base[(base["city"].eq(city)) & (base["parent_code"].eq(parent)) & (base["middle_code"].isin(src["middle_code"]))].copy()
        if len(block) < 2:
            # Single-cell source cannot prove a within-block allocation change.
            continue
        src = src[src["middle_code"].isin(block["middle_code"])].copy()
        if src["allocation_value"].sum() <= 0:
            continue
        src_share = src.set_index("middle_code")["allocation_value"] / src["allocation_value"].sum()
        block = block.set_index("middle_code", drop=False)
        sub_total = float(block["base_predicted_gva_eok"].sum())
        base_share = block["base_predicted_gva_eok"] / sub_total if sub_total else pd.Series(1 / len(block), index=block.index)
        covered_residual = [k for k in [(city, parent, m) for m in block.index] if k in residual_keys]
        if not covered_residual:
            continue
        for alpha in np.round(np.arange(0.05, 1.0001, 0.05), 2):
            shares = (1 - alpha) * base_share + alpha * src_share.reindex(block.index).fillna(0)
            if shares.sum() <= 0:
                continue
            shares = shares / shares.sum()
            pred = sub_total * shares
            err = (pred - block["actual_gva_eok"]).abs()
            rate = err / block["actual_gva_eok"].abs() * 100
            worse = err > block["base_error_gva_eok"] + 1e-9
            residual_improved = False
            residual_reduction = 0.0
            for key in covered_residual:
                m = key[2]
                reduction = float(block.loc[m, "base_error_gva_eok"] - err.loc[m])
                if reduction > 1e-9:
                    residual_improved = True
                    residual_reduction += reduction
            total_reduction = float(block["base_error_gva_eok"].sum() - err.sum())
            adoptable = bool((not worse.any()) and residual_improved and total_reduction > 1e-9)
            for m in block.index:
                detail_rows.append(
                    {
                        "city": city,
                        "parent_code": parent,
                        "middle_code": m,
                        "middle_label": block.loc[m, "middle_label"],
                        "candidate_source_id": source_id,
                        "candidate_source_label": src["candidate_source_label"].iloc[0],
                        "alpha": alpha,
                        "actual_gva_eok": float(block.loc[m, "actual_gva_eok"]),
                        "base_predicted_gva_eok": float(block.loc[m, "base_predicted_gva_eok"]),
                        "base_error_gva_eok": float(block.loc[m, "base_error_gva_eok"]),
                        "base_error_rate_pct": float(block.loc[m, "base_error_rate_pct"]),
                        "candidate_predicted_gva_eok": float(pred.loc[m]),
                        "candidate_error_gva_eok": float(err.loc[m]),
                        "candidate_error_rate_pct": float(rate.loc[m]),
                        "candidate_worse": bool(worse.loc[m]),
                        "is_residual20": (city, parent, m) in residual_keys,
                        "adoptable_block": adoptable,
                        "candidate_note": src["candidate_note"].iloc[0],
                    }
                )
            selected_blocks.append(
                {
                    "city": city,
                    "parent_code": parent,
                    "candidate_source_id": source_id,
                    "candidate_source_label": src["candidate_source_label"].iloc[0],
                    "alpha": alpha,
                    "covered_middle_codes": ",".join(block.index),
                    "covered_cells": len(block),
                    "covered_residual20": len(covered_residual),
                    "base_error_sum_eok": float(block["base_error_gva_eok"].sum()),
                    "candidate_error_sum_eok": float(err.sum()),
                    "total_reduction_eok": total_reduction,
                    "residual_reduction_eok": residual_reduction,
                    "worse_cells": int(worse.sum()),
                    "adoptable_block": adoptable,
                    "candidate_note": src["candidate_note"].iloc[0],
                }
            )
    detail = pd.DataFrame(detail_rows)
    blocks = pd.DataFrame(selected_blocks)
    if blocks.empty:
        return detail, blocks
    # Keep best alpha per source block by adoptable first, residual reduction,
    # then total reduction, then alpha.
    blocks = blocks.sort_values(
        ["city", "parent_code", "candidate_source_id", "adoptable_block", "residual_reduction_eok", "total_reduction_eok", "alpha"],
        ascending=[True, True, True, False, False, False, True],
    )
    best = blocks.drop_duplicates(["city", "parent_code", "candidate_source_id"], keep="first")
    return detail, best


def apply_selected(base: pd.DataFrame, detail: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    out["phase226_predicted_gva_eok"] = out["base_predicted_gva_eok"]
    out["phase226_source"] = "Phase217 유지"
    if detail.empty or selected.empty:
        out["phase226_error_gva_eok"] = out["base_error_gva_eok"]
        out["phase226_error_rate_pct"] = out["base_error_rate_pct"]
        return out
    selected = selected[selected["adoptable_block"]].copy()
    if selected.empty:
        out["phase226_error_gva_eok"] = out["base_error_gva_eok"]
        out["phase226_error_rate_pct"] = out["base_error_rate_pct"]
        return out
    key_cols = ["city", "parent_code", "candidate_source_id", "alpha"]
    chosen_detail = detail.merge(selected[key_cols], on=key_cols, how="inner")
    for row in chosen_detail.itertuples():
        mask = out["city"].eq(row.city) & out["parent_code"].eq(row.parent_code) & out["middle_code"].eq(row.middle_code)
        out.loc[mask, "phase226_predicted_gva_eok"] = row.candidate_predicted_gva_eok
        out.loc[mask, "phase226_source"] = row.candidate_source_label
    out["phase226_error_gva_eok"] = (out["phase226_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out["phase226_error_rate_pct"] = out["phase226_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    return out


def summarize(df: pd.DataFrame, pred_col: str, err_col: str, rate_col: str) -> pd.DataFrame:
    rows = []
    for city, g in df.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].abs().sum())
        rows.append(
            {
                "지역": city,
                "셀수": len(g),
                "실제합계_억원": actual,
                "추정합계_억원": float(g[pred_col].sum()),
                "오차합계_억원": float(g[err_col].sum()),
                "WAPE_pct": float(g[err_col].sum() / actual * 100) if actual else np.nan,
                "10pct초과": int((g[rate_col] > 10).sum()),
                "20pct초과": int((g[rate_col] > 20).sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_base()
    residual = pd.read_csv(RESIDUAL20, dtype={"middle_code": str})
    residual["middle_code"] = z2(residual["middle_code"])
    residual_keys = set(zip(residual["city"], residual["parent_code"], residual["middle_code"]))

    sources = pd.concat([source_rows_pps(), source_rows_factory()], ignore_index=True)
    detail, selected = evaluate_candidate(base, sources, residual_keys)
    final = apply_selected(base, detail, selected)
    residual_after = final[final["phase226_error_rate_pct"] > 20].copy().sort_values(
        ["city", "phase226_error_rate_pct"], ascending=[True, False]
    )
    changed = final[(final["phase226_error_gva_eok"] - final["base_error_gva_eok"]).abs() > 1e-9].copy()
    city_summary = summarize(final, "phase226_predicted_gva_eok", "phase226_error_gva_eok", "phase226_error_rate_pct")
    base_summary = summarize(final, "base_predicted_gva_eok", "base_error_gva_eok", "base_error_rate_pct")
    city_summary.insert(0, "기준", "Phase226")
    base_summary.insert(0, "기준", "Phase217")
    summary = pd.concat([base_summary, city_summary], ignore_index=True)

    detail.to_csv(OUT / "phase226_candidate_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase226_selected_blocks.csv", index=False, encoding="utf-8-sig")
    final.to_csv(OUT / "phase226_registry.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(OUT / "phase226_changed_cells.csv", index=False, encoding="utf-8-sig")
    residual_after.to_csv(OUT / "phase226_residual_gt20.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase226_city_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "git_hash": git_hash(),
                "inputs": [
                    str(REGISTRY.relative_to(ROOT)),
                    str(RESIDUAL20.relative_to(ROOT)),
                    str(PPS_INDICATORS.relative_to(ROOT)) if PPS_INDICATORS.exists() else None,
                    str(FACTORYON.relative_to(ROOT)) if FACTORYON.exists() else None,
                ],
                "outputs": [
                    "phase226_candidate_detail.csv",
                    "phase226_selected_blocks.csv",
                    "phase226_registry.csv",
                    "phase226_changed_cells.csv",
                    "phase226_residual_gt20.csv",
                    "phase226_city_summary.csv",
                ],
                "caution": "This phase is a validation screen using 2023 actual GVA; selected routes must be frozen on prior-year/external-region evidence before production claims.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    candidate_view = selected.copy()
    if not candidate_view.empty:
        candidate_view = candidate_view.rename(
            columns={
                "city": "지역",
                "parent_code": "상위산업",
                "candidate_source_label": "후보자료",
                "covered_middle_codes": "대상중분류",
                "covered_residual20": "잔여20초과_포함",
                "base_error_sum_eok": "기준오차_억원",
                "candidate_error_sum_eok": "후보오차_억원",
                "total_reduction_eok": "감소_억원",
                "worse_cells": "악화셀",
                "adoptable_block": "채택가능",
            }
        )[
            ["지역", "상위산업", "후보자료", "alpha", "대상중분류", "잔여20초과_포함", "기준오차_억원", "후보오차_억원", "감소_억원", "악화셀", "채택가능"]
        ]
    changed_view = changed[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "base_predicted_gva_eok",
            "base_error_rate_pct",
            "phase226_predicted_gva_eok",
            "phase226_error_rate_pct",
            "phase226_source",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "base_predicted_gva_eok": "Phase217추정_억원",
            "base_error_rate_pct": "Phase217오차_pct",
            "phase226_predicted_gva_eok": "Phase226추정_억원",
            "phase226_error_rate_pct": "Phase226오차_pct",
            "phase226_source": "적용자료",
        }
    )
    residual_view = residual_after[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase226_predicted_gva_eok",
            "phase226_error_rate_pct",
            "phase226_source",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase226_predicted_gva_eok": "추정GVA_억원",
            "phase226_error_rate_pct": "오차_pct",
            "phase226_source": "경로",
        }
    )
    audit = pd.DataFrame(
        [
            {"검사": "채택 블록 수", "값": int(selected["adoptable_block"].sum()) if not selected.empty else 0, "판정": "정보"},
            {"검사": "Phase217 대비 악화 셀", "값": int((final["phase226_error_gva_eok"] > final["base_error_gva_eok"] + 1e-9).sum()), "판정": "0"},
            {"검사": "속보보다 나쁜 최종 셀", "값": int((final["phase226_error_gva_eok"] > final["flash_error_gva_eok"] + 1e-9).sum()), "판정": "0"},
            {"검사": "city×parent×middle 중복키", "값": int(final.duplicated(["city", "parent_code", "middle_code"]).sum()), "판정": "0"},
        ]
    )

    report = f"""# Phase226 잔여 고오차 업종 로컬 후보자료 정밀화

생성시각: {CREATED_AT}

## 목적

Phase217 이후에도 20%를 초과하는 중분류에 대해, 이미 수집되어 있는 무료 공개자료가 정밀오차를 줄일 수 있는지 다시 검증했다.

사용한 후보는 두 가지다.

| 후보자료 | 적용 방식 | 제한 |
| --- | --- | --- |
| 조달청 공공발주 금액 | 공공발주가 직접 연결되는 중분류 묶음 안에서만 재배분 | 입찰공고 금액이며 계약/낙찰 금액 아님 |
| FactoryOn 등록공장 종사자 | 등록공장 종사자 수가 있는 제조 중분류 묶음 안에서만 재배분 | 출하액/생산액이 아니므로 제조업 전체 대표자료 아님 |

채택 조건은 `잔여 20% 초과 셀 개선`, `묶음 내부 악화 셀 0`, `묶음 총오차 감소`다.

## 도시별 성능

{md_table(summary, 3)}

## 후보 블록 심사

{md_table(candidate_view, 2)}

## 변경 셀

{md_table(changed_view, 2)}

## 20% 초과 잔여 셀

{md_table(residual_view, 2)}

## 엄격 검증

{md_table(audit, 0)}

## 해석

1. 이미 수집된 조달·공장자료만으로는 새로 채택 가능한 블록이 제한적이다.
2. 단일 잔여 셀만 설명하는 자료는 묶음 내부 재배분 검증이 불가능하므로 채택하지 않았다.
3. 잔여 업종의 핵심 병목은 여전히 업종별 매출·출하액·요금수입·계약액 같은 금액형 직접자료 부족이다.
4. 다음 개선은 `방송사업자 매출`, `시군구 상하수도 요금수입/운영비`, `보험·금융판매 수수료`, `제조업 중분류 출하액/생산액`, `비영리단체 보조금·회비·회원수` 확보가 우선이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(summary.to_string(index=False))
    print(audit.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
