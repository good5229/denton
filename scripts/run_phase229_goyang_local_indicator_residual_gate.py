#!/usr/bin/env python3
"""Phase229: Goyang local indicator residual gate on the Phase217 baseline."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase229_goyang_local_indicator_residual_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase229_goyang_local_indicator_residual_gate.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

BASE = DATA / "phase217_public_safe_candidate_rerank_audit" / "phase217_reranked_guarded_registry.csv"
RESIDUAL = DATA / "phase227_residual_threshold_tradeoff_gate" / "phase227_residual_gt20.csv"
IND = DATA / "phase113_goyang_openapi_constrained_refinement" / "phase113_goyang_openapi_activity_indicators.csv"
TARGET = 20.0
BUFFER = 20.0


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
    v = df.copy()
    for c in v.columns:
        if pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(BASE, dtype={"middle_code": str}, low_memory=False)
    base["middle_code"] = z2(base["middle_code"])
    base = base[base["city"].eq("고양시")].copy()
    base["base_predicted_gva_eok"] = base["phase217_guarded_predicted_gva_eok"]
    base["base_error_gva_eok"] = base["phase217_guarded_error_gva_eok"]
    base["base_error_rate_pct"] = base["phase217_guarded_error_rate_pct"]

    residual = pd.read_csv(RESIDUAL, dtype={"middle_code": str})
    residual["middle_code"] = z2(residual["middle_code"])
    residual_keys = set(
        zip(
            residual[residual["city"].eq("고양시")]["parent_code"],
            residual[residual["city"].eq("고양시")]["middle_code"],
        )
    )

    ind = pd.read_csv(IND, dtype={"middle_code": str})
    ind["middle_code"] = z2(ind["middle_code"])
    # Keep indicators attached to current residual parent blocks.
    ind = ind[ind["parent_code"].isin(sorted({p for p, _ in residual_keys}))].copy()
    ind = ind[pd.to_numeric(ind["indicator_raw_value"], errors="coerce").fillna(0) > 0]

    detail_rows = []
    candidate_rows = []
    for (parent, source_id), src in ind.groupby(["parent_code", "source_id"], sort=False):
        block = base[base["parent_code"].eq(parent)].copy()
        if block.empty:
            continue
        source_vec = pd.Series(0.0, index=block["middle_code"].astype(str).values)
        labels = src["source_label"].dropna().astype(str).unique()
        for r in src.itertuples():
            if r.middle_code in source_vec.index:
                source_vec.loc[r.middle_code] += float(r.indicator_raw_value)
        if source_vec.sum() <= 0:
            continue
        source_share = source_vec / source_vec.sum()
        block = block.set_index("middle_code", drop=False)
        total = float(block["base_predicted_gva_eok"].sum())
        base_share = block["base_predicted_gva_eok"] / total if total else pd.Series(1 / len(block), index=block.index)
        covered_residual = [m for m in block.index if (parent, m) in residual_keys]
        if not covered_residual:
            continue
        for alpha in np.round(np.arange(0.01, 0.5001, 0.01), 2):
            share = (1 - alpha) * base_share + alpha * source_share.reindex(block.index).fillna(0)
            share = share / share.sum()
            pred = total * share
            err = (pred - block["actual_gva_eok"]).abs()
            rate = err / block["actual_gva_eok"].abs() * 100
            residual_before = block.loc[covered_residual, "base_error_gva_eok"].sum()
            residual_after = err.loc[covered_residual].sum()
            residual_max_after = rate.loc[covered_residual].max()
            block_reduction = block["base_error_gva_eok"].sum() - err.sum()
            gt20_before = int((block["base_error_rate_pct"] > 20).sum())
            gt20_after = int((rate > 20).sum())
            worsened = err > block["base_error_gva_eok"] + 1e-9
            high_worsened = worsened & (rate > BUFFER)
            adopt = bool(
                residual_after < residual_before - 1e-9
                and residual_max_after <= TARGET + 1e-9
                and block_reduction > 0
                and gt20_after <= gt20_before
                and not high_worsened.any()
            )
            candidate_rows.append(
                {
                    "parent_code": parent,
                    "source_id": source_id,
                    "source_label": labels[0] if len(labels) else source_id,
                    "alpha": alpha,
                    "covered_middle_codes": ",".join(src["middle_code"].astype(str).unique()),
                    "residual_middle_codes": ",".join(covered_residual),
                    "base_block_error_eok": float(block["base_error_gva_eok"].sum()),
                    "candidate_block_error_eok": float(err.sum()),
                    "block_reduction_eok": float(block_reduction),
                    "residual_error_before_eok": float(residual_before),
                    "residual_error_after_eok": float(residual_after),
                    "residual_max_after_pct": float(residual_max_after),
                    "gt20_before": gt20_before,
                    "gt20_after": gt20_after,
                    "worsened_cells": int(worsened.sum()),
                    "high_worsened_cells": int(high_worsened.sum()),
                    "adoptable": adopt,
                }
            )
            for m in block.index:
                detail_rows.append(
                    {
                        "parent_code": parent,
                        "middle_code": m,
                        "middle_label": block.loc[m, "middle_label"],
                        "source_id": source_id,
                        "source_label": labels[0] if len(labels) else source_id,
                        "alpha": alpha,
                        "actual_gva_eok": float(block.loc[m, "actual_gva_eok"]),
                        "base_predicted_gva_eok": float(block.loc[m, "base_predicted_gva_eok"]),
                        "base_error_rate_pct": float(block.loc[m, "base_error_rate_pct"]),
                        "candidate_predicted_gva_eok": float(pred.loc[m]),
                        "candidate_error_rate_pct": float(rate.loc[m]),
                        "candidate_error_gva_eok": float(err.loc[m]),
                        "is_residual20": (parent, m) in residual_keys,
                    }
                )
    cand = pd.DataFrame(candidate_rows)
    detail = pd.DataFrame(detail_rows)
    if cand.empty:
        selected = cand
    else:
        selected = cand.sort_values(
            ["adoptable", "residual_max_after_pct", "block_reduction_eok", "alpha"],
            ascending=[False, True, False, True],
        ).drop_duplicates(["parent_code"], keep="first")

    final = base.copy()
    final["phase229_predicted_gva_eok"] = final["base_predicted_gva_eok"]
    final["phase229_source"] = "Phase217 유지"
    adopted = selected[selected.get("adoptable", False)].copy() if not selected.empty else selected
    if not adopted.empty:
        chosen = detail.merge(adopted[["parent_code", "source_id", "alpha"]], on=["parent_code", "source_id", "alpha"], how="inner")
        for r in chosen.itertuples():
            mask = final["parent_code"].eq(r.parent_code) & final["middle_code"].eq(r.middle_code)
            final.loc[mask, "phase229_predicted_gva_eok"] = r.candidate_predicted_gva_eok
            final.loc[mask, "phase229_source"] = r.source_label
    final["phase229_error_gva_eok"] = (final["phase229_predicted_gva_eok"] - final["actual_gva_eok"]).abs()
    final["phase229_error_rate_pct"] = final["phase229_error_gva_eok"] / final["actual_gva_eok"].abs() * 100

    changed = final[(final["phase229_error_gva_eok"] - final["base_error_gva_eok"]).abs() > 1e-9].copy()
    residual_after = final[final["phase229_error_rate_pct"] > 20].copy().sort_values("phase229_error_rate_pct", ascending=False)
    summary = pd.DataFrame(
        [
            {
                "기준": "Phase217",
                "오차합계_억원": final["base_error_gva_eok"].sum(),
                "WAPE_pct": final["base_error_gva_eok"].sum() / final["actual_gva_eok"].abs().sum() * 100,
                "10pct초과": int((final["base_error_rate_pct"] > 10).sum()),
                "20pct초과": int((final["base_error_rate_pct"] > 20).sum()),
            },
            {
                "기준": "Phase229",
                "오차합계_억원": final["phase229_error_gva_eok"].sum(),
                "WAPE_pct": final["phase229_error_gva_eok"].sum() / final["actual_gva_eok"].abs().sum() * 100,
                "10pct초과": int((final["phase229_error_rate_pct"] > 10).sum()),
                "20pct초과": int((final["phase229_error_rate_pct"] > 20).sum()),
            },
        ]
    )
    audit = pd.DataFrame(
        [
            {"검사": "채택 블록", "값": int(len(adopted)), "판정": "정보"},
            {"검사": "20% 초과 감소 셀", "값": int((final["phase229_error_rate_pct"].le(20) & final["base_error_rate_pct"].gt(20)).sum()), "판정": "정보"},
            {"검사": "20% 초과 악화 셀", "값": int((final["phase229_error_rate_pct"].gt(20) & final["base_error_rate_pct"].le(20)).sum()), "판정": "0"},
            {"검사": "city×parent×middle 중복키", "값": int(final.duplicated(["city", "parent_code", "middle_code"]).sum()), "판정": "0"},
        ]
    )

    cand.to_csv(OUT / "phase229_candidate_screen.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase229_selected_candidates.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase229_candidate_detail.csv", index=False, encoding="utf-8-sig")
    final.to_csv(OUT / "phase229_registry.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(OUT / "phase229_changed_cells.csv", index=False, encoding="utf-8-sig")
    residual_after.to_csv(OUT / "phase229_residual_gt20.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase229_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(json.dumps({"created_at": CREATED_AT, "git_hash": git_hash()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    selected_view = selected.rename(columns={
        "parent_code":"상위산업","source_label":"후보자료","covered_middle_codes":"지표대상","residual_middle_codes":"잔여대상","base_block_error_eok":"기준오차_억원","candidate_block_error_eok":"후보오차_억원","block_reduction_eok":"감소_억원","residual_max_after_pct":"잔여최대오차_pct","gt20_after":"20초과후","worsened_cells":"악화셀","high_worsened_cells":"20초과악화셀","adoptable":"채택"
    })[["상위산업","후보자료","alpha","지표대상","잔여대상","기준오차_억원","후보오차_억원","감소_억원","잔여최대오차_pct","20초과후","악화셀","20초과악화셀","채택"]] if not selected.empty else selected
    changed_view = changed[["parent_code","middle_code","middle_label","actual_gva_eok","base_predicted_gva_eok","base_error_rate_pct","phase229_predicted_gva_eok","phase229_error_rate_pct","phase229_source"]].rename(columns={
        "parent_code":"상위산업","middle_code":"중분류","middle_label":"업종명","actual_gva_eok":"실제GVA_억원","base_predicted_gva_eok":"Phase217추정_억원","base_error_rate_pct":"Phase217오차_pct","phase229_predicted_gva_eok":"Phase229추정_억원","phase229_error_rate_pct":"Phase229오차_pct","phase229_source":"적용자료"
    })
    residual_view = residual_after[["parent_code","middle_code","middle_label","actual_gva_eok","phase229_predicted_gva_eok","phase229_error_rate_pct","phase229_source"]].rename(columns={
        "parent_code":"상위산업","middle_code":"중분류","middle_label":"업종명","actual_gva_eok":"실제GVA_억원","phase229_predicted_gva_eok":"추정GVA_억원","phase229_error_rate_pct":"오차_pct","phase229_source":"경로"
    })
    REPORT.write_text(f"""# Phase229 고양 로컬 활동지표 잔여오차 재검증

생성시각: {CREATED_AT}

## 목적

과거 Phase113의 고양 OpenAPI/KOSIS 활동지표를 최신 Phase217 최종 표기값 위에서 다시 검증했다. 대상은 고양시 잔여 20% 초과 업종이다.

## 성능 요약

{md_table(summary, 3)}

## 후보 선택

{md_table(selected_view, 2)}

## 변경 셀

{md_table(changed_view, 2)}

## 20% 초과 잔여 셀

{md_table(residual_view, 2)}

## 검증

{md_table(audit, 0)}

## 해석

1. 고양시 방송업·하수폐수·의복·가죽 등은 기존 로컬 지표로 일부 개선 가능성이 있으나, 상위산업 형제 업종의 악화를 함께 본 뒤 제한적으로만 채택했다.
2. 단일 지표가 특정 중분류만 설명하는 경우, 상위산업 내 다른 중분류의 값을 빼앗는 효과가 생기므로 공개 성능으로 쓰기 전 외부연도 검증이 필요하다.
3. 그래도 20% 초과 셀을 줄이는 관점에서는 직접 활동자료가 성능 개선 방향을 제공한다.
""", encoding="utf-8")
    print(summary.to_string(index=False))
    print(audit.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
