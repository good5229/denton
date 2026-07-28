#!/usr/bin/env python3
"""Phase227: residual threshold tradeoff gate.

Phase226 used a very strict no-worse rule and rejected a PPS ERS candidate that
reduced Pohang ERS37 from 46% to single digits while slightly worsening ERS90
from ~1.6% to around 10%.  Since the user's operational target is to pull
high-error industries toward a 10% band, this phase tests a different gate:

* residual 20%+ cell must improve and fall at or below the target threshold;
* no covered cell may exceed a threshold buffer;
* block total error must improve;
* the result is reported separately as a controlled tradeoff, not as the
  strict no-worse Phase226 result.
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
OUT = DATA / "phase227_residual_threshold_tradeoff_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase227_residual_threshold_tradeoff_gate.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

PHASE226_DETAIL = DATA / "phase226_residual_local_candidate_refinement" / "phase226_candidate_detail.csv"
PHASE217 = DATA / "phase217_public_safe_candidate_rerank_audit" / "phase217_reranked_guarded_registry.csv"
TARGET = 10.0
BUFFER = 11.0


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


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


def summarize(df: pd.DataFrame, pred_col: str, err_col: str, rate_col: str, label: str) -> pd.DataFrame:
    rows = []
    for city, g in df.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].abs().sum())
        rows.append(
            {
                "기준": label,
                "지역": city,
                "셀수": len(g),
                "오차합계_억원": float(g[err_col].sum()),
                "WAPE_pct": float(g[err_col].sum() / actual * 100) if actual else np.nan,
                "10pct초과": int((g[rate_col] > 10).sum()),
                "20pct초과": int((g[rate_col] > 20).sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    detail = pd.read_csv(PHASE226_DETAIL, dtype={"middle_code": str})
    base = pd.read_csv(PHASE217, dtype={"middle_code": str}, low_memory=False)
    base["middle_code"] = base["middle_code"].astype(str).str.extract(r"(\d+)")[0].str.zfill(2)
    base["phase227_predicted_gva_eok"] = base["phase217_guarded_predicted_gva_eok"]
    base["phase227_source"] = "Phase217 유지"

    candidates = []
    group_cols = ["city", "parent_code", "candidate_source_id", "candidate_source_label", "alpha"]
    for key, g in detail.groupby(group_cols, sort=False):
        residual = g[g["is_residual20"]]
        if residual.empty:
            continue
        residual_all_under_target = bool((residual["candidate_error_rate_pct"] <= TARGET + 1e-9).all())
        residual_improves = bool((residual["candidate_error_gva_eok"] < residual["base_error_gva_eok"] - 1e-9).all())
        block_under_buffer = bool((g["candidate_error_rate_pct"] <= BUFFER + 1e-9).all())
        block_error_reduction = float(g["base_error_gva_eok"].sum() - g["candidate_error_gva_eok"].sum())
        max_worsening_pp = float((g["candidate_error_rate_pct"] - g["base_error_rate_pct"]).max())
        candidates.append(
            {
                "city": key[0],
                "parent_code": key[1],
                "candidate_source_id": key[2],
                "candidate_source_label": key[3],
                "alpha": key[4],
                "covered_middle_codes": ",".join(g["middle_code"].astype(str)),
                "residual_cells": int(len(residual)),
                "base_error_sum_eok": float(g["base_error_gva_eok"].sum()),
                "candidate_error_sum_eok": float(g["candidate_error_gva_eok"].sum()),
                "block_error_reduction_eok": block_error_reduction,
                "residual_max_error_pct": float(residual["candidate_error_rate_pct"].max()),
                "block_max_error_pct": float(g["candidate_error_rate_pct"].max()),
                "max_worsening_pp": max_worsening_pp,
                "residual_all_under_target": residual_all_under_target,
                "residual_improves": residual_improves,
                "block_under_buffer": block_under_buffer,
                "adoptable_tradeoff": bool(residual_all_under_target and residual_improves and block_under_buffer and block_error_reduction > 1e-9),
            }
        )
    cand = pd.DataFrame(candidates)
    if cand.empty:
        selected = cand
    else:
        selected = (
            cand.sort_values(
                ["adoptable_tradeoff", "block_error_reduction_eok", "block_max_error_pct", "max_worsening_pp", "alpha"],
                ascending=[False, False, True, True, True],
            )
            .drop_duplicates(["city", "parent_code", "candidate_source_id"], keep="first")
            .copy()
        )
    adopted = selected[selected.get("adoptable_tradeoff", False)].copy() if not selected.empty else selected

    if not adopted.empty:
        chosen_detail = detail.merge(adopted[group_cols], on=group_cols, how="inner")
        for row in chosen_detail.itertuples():
            mask = base["city"].eq(row.city) & base["parent_code"].eq(row.parent_code) & base["middle_code"].eq(str(row.middle_code).zfill(2))
            base.loc[mask, "phase227_predicted_gva_eok"] = row.candidate_predicted_gva_eok
            base.loc[mask, "phase227_source"] = row.candidate_source_label
    base["phase227_error_gva_eok"] = (base["phase227_predicted_gva_eok"] - base["actual_gva_eok"]).abs()
    base["phase227_error_rate_pct"] = base["phase227_error_gva_eok"] / base["actual_gva_eok"].abs() * 100

    changed = base[(base["phase227_error_gva_eok"] - base["phase217_guarded_error_gva_eok"]).abs() > 1e-9].copy()
    residual = base[base["phase227_error_rate_pct"] > 20].copy().sort_values(["city", "phase227_error_rate_pct"], ascending=[True, False])
    summary = pd.concat(
        [
            summarize(base, "phase217_guarded_predicted_gva_eok", "phase217_guarded_error_gva_eok", "phase217_guarded_error_rate_pct", "Phase217"),
            summarize(base, "phase227_predicted_gva_eok", "phase227_error_gva_eok", "phase227_error_rate_pct", "Phase227"),
        ],
        ignore_index=True,
    )
    audit = pd.DataFrame(
        [
            {"검사": "채택 tradeoff 블록", "값": len(adopted), "판정": "정보"},
            {"검사": "20% 초과 감소 셀", "값": int((base["phase227_error_rate_pct"].le(20) & base["phase217_guarded_error_rate_pct"].gt(20)).sum()), "판정": "정보"},
            {"검사": "Phase217 대비 악화 셀", "값": int((base["phase227_error_gva_eok"] > base["phase217_guarded_error_gva_eok"] + 1e-9).sum()), "판정": "허용: 단 11% 버퍼 이내"},
            {"검사": "11% 초과로 악화된 셀", "값": int(((base["phase227_error_gva_eok"] > base["phase217_guarded_error_gva_eok"] + 1e-9) & (base["phase227_error_rate_pct"] > BUFFER)).sum()), "판정": "0"},
            {"검사": "속보보다 나쁜 최종 셀", "값": int((base["phase227_error_gva_eok"] > base["flash_error_gva_eok"] + 1e-9).sum()), "판정": "진단"},
        ]
    )

    cand.to_csv(OUT / "phase227_threshold_candidates.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase227_selected_candidates.csv", index=False, encoding="utf-8-sig")
    base.to_csv(OUT / "phase227_registry.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(OUT / "phase227_changed_cells.csv", index=False, encoding="utf-8-sig")
    residual.to_csv(OUT / "phase227_residual_gt20.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase227_city_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "git_hash": git_hash(),
                "inputs": [str(PHASE226_DETAIL.relative_to(ROOT)), str(PHASE217.relative_to(ROOT))],
                "target_error_pct": TARGET,
                "buffer_error_pct": BUFFER,
                "caution": "Controlled tradeoff validation. Not a strict no-worse public reporting contract.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    selected_view = selected.rename(
        columns={
            "city": "지역",
            "parent_code": "상위산업",
            "candidate_source_label": "후보자료",
            "covered_middle_codes": "대상중분류",
            "base_error_sum_eok": "기준오차_억원",
            "candidate_error_sum_eok": "후보오차_억원",
            "block_error_reduction_eok": "감소_억원",
            "residual_max_error_pct": "잔여셀최대오차_pct",
            "block_max_error_pct": "묶음최대오차_pct",
            "max_worsening_pp": "최대악화_pp",
            "adoptable_tradeoff": "채택가능",
        }
    )[
        ["지역", "상위산업", "후보자료", "alpha", "대상중분류", "기준오차_억원", "후보오차_억원", "감소_억원", "잔여셀최대오차_pct", "묶음최대오차_pct", "최대악화_pp", "채택가능"]
    ] if not selected.empty else selected
    changed_view = changed[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase217_guarded_predicted_gva_eok",
            "phase217_guarded_error_rate_pct",
            "phase227_predicted_gva_eok",
            "phase227_error_rate_pct",
            "phase227_source",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase217_guarded_predicted_gva_eok": "Phase217추정_억원",
            "phase217_guarded_error_rate_pct": "Phase217오차_pct",
            "phase227_predicted_gva_eok": "Phase227추정_억원",
            "phase227_error_rate_pct": "Phase227오차_pct",
            "phase227_source": "적용자료",
        }
    )
    residual_view = residual[
        ["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "phase227_predicted_gva_eok", "phase227_error_rate_pct", "phase227_source"]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase227_predicted_gva_eok": "추정GVA_억원",
            "phase227_error_rate_pct": "오차_pct",
            "phase227_source": "경로",
        }
    )
    report = f"""# Phase227 10% 목표형 고오차 압축 게이트

생성시각: {CREATED_AT}

## 목적

Phase226의 셀 단위 무악화 기준은 매우 보수적이었다. 포항시 하수·폐수 처리업은 조달청 공공발주 금액을 일부 반영하면 10% 안쪽으로 내려가지만, 같은 묶음의 저오차 셀이 소폭 악화되어 채택되지 않았다.

이번 단계는 사용자의 운영 목표인 `가능하면 10% 전후`에 맞춰, 고오차 셀을 10% 이하로 낮추고 묶음 내 다른 셀도 11% 버퍼 안에 남는 경우를 별도 진단했다.

## 도시별 성능

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

1. 포항시 `하수 폐수 및 분뇨 처리업`은 조달청 공공발주 금액 부분묶음을 적용하면 46.27%에서 8.43%로 내려간다.
2. 대신 같은 묶음의 `창작 예술 및 여가관련 서비스업`은 1.58%에서 10.71%로 악화된다. 이 값은 11% 버퍼 안이지만 엄격 무악화 기준은 아니다.
3. 따라서 Phase227은 포스터의 공개 성능 기준보다는 내부 운영 후보로 적합하다. 대외 표기는 Phase217/225의 속보우위 계약을 유지하는 편이 안전하다.
4. 이 결과는 “자료가 전혀 소용없다”가 아니라, 직접 계약액·요금수입 자료가 있으면 ERS37 계열은 10%권 진입 가능성이 높다는 근거다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(summary.to_string(index=False))
    print(audit.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
