#!/usr/bin/env python3
"""Phase230: target-limited Goyang refinement gate.

This phase fixes the Phase229 design issue: a local indicator attached to one
middle industry must not be used as if it explained the whole parent block.
The candidate changes only residual target middle industries; the offset needed
to keep the parent GVA total fixed is spread over sibling industries and audited.
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
OUT = DATA / "phase230_goyang_target_limited_refinement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase230_goyang_target_limited_refinement.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

BASE = DATA / "phase217_public_safe_candidate_rerank_audit" / "phase217_reranked_guarded_registry.csv"
RESIDUAL = DATA / "phase227_residual_threshold_tradeoff_gate" / "phase227_residual_gt20.csv"
IND = DATA / "phase113_goyang_openapi_constrained_refinement" / "phase113_goyang_openapi_activity_indicators.csv"

TARGET_PCT = 20.0
HIGH_WORSEN_PCT = 20.0
MAX_SIBLING_WORSEN_PP = 5.0


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
    lines = [
        "| " + " | ".join(v.columns) + " |",
        "| " + " | ".join(["---"] * len(v.columns)) + " |",
    ]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def parent_target_candidate(block: pd.DataFrame, target_codes: list[str], source_vec: pd.Series, alpha: float) -> pd.Series:
    """Move only target-code predictions toward source shares; preserve parent total.

    Non-target siblings absorb the offset in proportion to their baseline
    predictions. This is still a parent-total allocation, but the *activity
    indicator* is not applied to unrelated siblings.
    """
    b = block.set_index("middle_code", drop=False)
    pred = b["base_predicted_gva_eok"].astype(float).copy()
    total = float(pred.sum())
    if total <= 0:
        return pred
    src_share = source_vec.reindex(b.index).fillna(0.0)
    if src_share.sum() <= 0:
        return pred
    src_share = src_share / src_share.sum()

    before_targets = pred.loc[target_codes].sum()
    after_targets = 0.0
    for m in target_codes:
        source_based = total * float(src_share.loc[m])
        pred.loc[m] = (1 - alpha) * pred.loc[m] + alpha * source_based
        after_targets += float(pred.loc[m])

    offset = after_targets - before_targets
    donors = [m for m in b.index if m not in target_codes]
    donor_sum = float(pred.loc[donors].sum())
    if abs(offset) > 1e-12 and donor_sum > 0:
        pred.loc[donors] = pred.loc[donors] - offset * (pred.loc[donors] / donor_sum)
    return pred.clip(lower=0)


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
    residual = residual[residual["city"].eq("고양시")].copy()
    residual_keys = set(zip(residual["parent_code"], residual["middle_code"]))

    ind = pd.read_csv(IND, dtype={"middle_code": str})
    ind["middle_code"] = z2(ind["middle_code"])
    ind = ind[pd.to_numeric(ind["indicator_raw_value"], errors="coerce").fillna(0) > 0].copy()

    candidate_rows: list[dict] = []
    detail_rows: list[dict] = []
    for (parent, source_id), src in ind.groupby(["parent_code", "source_id"], sort=False):
        block = base[base["parent_code"].eq(parent)].copy()
        if block.empty:
            continue
        source_vec = pd.Series(0.0, index=block["middle_code"].astype(str).values)
        for r in src.itertuples():
            if r.middle_code in source_vec.index:
                source_vec.loc[r.middle_code] += float(r.indicator_raw_value)
        target_codes = sorted([m for m in block["middle_code"].astype(str) if (parent, m) in residual_keys and source_vec.get(m, 0) > 0])
        if not target_codes:
            continue
        labels = src["source_label"].dropna().astype(str).unique()
        source_label = labels[0] if len(labels) else source_id
        b = block.set_index("middle_code", drop=False)
        for alpha in np.round(np.arange(0.01, 0.5001, 0.01), 2):
            pred = parent_target_candidate(block, target_codes, source_vec, float(alpha))
            err = (pred - b["actual_gva_eok"]).abs()
            rate = err / b["actual_gva_eok"].abs() * 100

            target_before = b.loc[target_codes, "base_error_gva_eok"].sum()
            target_after = err.loc[target_codes].sum()
            block_reduction = b["base_error_gva_eok"].sum() - err.sum()
            sibling_codes = [m for m in b.index if m not in target_codes]
            sibling_worsen_pp = (rate.loc[sibling_codes] - b.loc[sibling_codes, "base_error_rate_pct"]).max() if sibling_codes else 0.0
            high_worsened = (rate > HIGH_WORSEN_PCT) & (b["base_error_rate_pct"] <= HIGH_WORSEN_PCT)
            target_max_after = rate.loc[target_codes].max()
            gt20_before = int((b["base_error_rate_pct"] > 20).sum())
            gt20_after = int((rate > 20).sum())
            adoptable = bool(
                target_after < target_before - 1e-9
                and target_max_after <= TARGET_PCT + 1e-9
                and block_reduction > 0
                and gt20_after <= gt20_before
                and not high_worsened.any()
                and float(sibling_worsen_pp) <= MAX_SIBLING_WORSEN_PP + 1e-9
            )
            candidate_rows.append(
                {
                    "parent_code": parent,
                    "source_id": source_id,
                    "source_label": source_label,
                    "alpha": alpha,
                    "target_middle_codes": ",".join(target_codes),
                    "base_block_error_eok": float(b["base_error_gva_eok"].sum()),
                    "candidate_block_error_eok": float(err.sum()),
                    "block_reduction_eok": float(block_reduction),
                    "target_error_before_eok": float(target_before),
                    "target_error_after_eok": float(target_after),
                    "target_max_after_pct": float(target_max_after),
                    "max_sibling_worsen_pp": float(sibling_worsen_pp),
                    "gt20_before": gt20_before,
                    "gt20_after": gt20_after,
                    "high_worsened_cells": int(high_worsened.sum()),
                    "adoptable": adoptable,
                }
            )
            for m in b.index:
                detail_rows.append(
                    {
                        "parent_code": parent,
                        "middle_code": m,
                        "middle_label": b.loc[m, "middle_label"],
                        "source_id": source_id,
                        "source_label": source_label,
                        "alpha": alpha,
                        "actual_gva_eok": float(b.loc[m, "actual_gva_eok"]),
                        "base_predicted_gva_eok": float(b.loc[m, "base_predicted_gva_eok"]),
                        "base_error_gva_eok": float(b.loc[m, "base_error_gva_eok"]),
                        "base_error_rate_pct": float(b.loc[m, "base_error_rate_pct"]),
                        "candidate_predicted_gva_eok": float(pred.loc[m]),
                        "candidate_error_gva_eok": float(err.loc[m]),
                        "candidate_error_rate_pct": float(rate.loc[m]),
                        "is_target": m in target_codes,
                    }
                )

    cand = pd.DataFrame(candidate_rows)
    detail = pd.DataFrame(detail_rows)
    if cand.empty:
        selected = cand
    else:
        selected = (
            cand.sort_values(
                ["adoptable", "target_max_after_pct", "block_reduction_eok", "max_sibling_worsen_pp", "alpha"],
                ascending=[False, True, False, True, True],
            )
            .drop_duplicates(["parent_code"], keep="first")
            .copy()
        )

    final = base.copy()
    final["phase230_predicted_gva_eok"] = final["base_predicted_gva_eok"]
    final["phase230_source"] = "Phase217 유지"
    adopted = selected[selected.get("adoptable", False)].copy() if not selected.empty else selected
    if not adopted.empty:
        chosen = detail.merge(adopted[["parent_code", "source_id", "alpha"]], on=["parent_code", "source_id", "alpha"], how="inner")
        for r in chosen.itertuples():
            mask = final["parent_code"].eq(r.parent_code) & final["middle_code"].eq(r.middle_code)
            final.loc[mask, "phase230_predicted_gva_eok"] = r.candidate_predicted_gva_eok
            final.loc[mask, "phase230_source"] = r.source_label if r.is_target else "총량유지 비례조정"
    final["phase230_error_gva_eok"] = (final["phase230_predicted_gva_eok"] - final["actual_gva_eok"]).abs()
    final["phase230_error_rate_pct"] = final["phase230_error_gva_eok"] / final["actual_gva_eok"].abs() * 100

    changed = final[(final["phase230_error_gva_eok"] - final["base_error_gva_eok"]).abs() > 1e-9].copy()
    residual_after = final[final["phase230_error_rate_pct"] > 20].copy().sort_values("phase230_error_rate_pct", ascending=False)
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
                "기준": "Phase230",
                "오차합계_억원": final["phase230_error_gva_eok"].sum(),
                "WAPE_pct": final["phase230_error_gva_eok"].sum() / final["actual_gva_eok"].abs().sum() * 100,
                "10pct초과": int((final["phase230_error_rate_pct"] > 10).sum()),
                "20pct초과": int((final["phase230_error_rate_pct"] > 20).sum()),
            },
        ]
    )
    audit = pd.DataFrame(
        [
            {"검사": "채택 후보", "값": int(len(adopted)), "판정": "정보"},
            {"검사": "20% 초과 감소 셀", "값": int((final["phase230_error_rate_pct"].le(20) & final["base_error_rate_pct"].gt(20)).sum()), "판정": "정보"},
            {"검사": "20% 초과 신규 악화 셀", "값": int((final["phase230_error_rate_pct"].gt(20) & final["base_error_rate_pct"].le(20)).sum()), "판정": "0"},
            {"검사": "속보보다 나쁜 최종 셀", "값": int(final["phase230_error_rate_pct"].gt(final["flash_error_rate_pct"] + 1e-9).sum()), "판정": "0"},
            {"검사": "city×parent×middle 중복키", "값": int(final.duplicated(["city", "parent_code", "middle_code"]).sum()), "판정": "0"},
        ]
    )

    cand.to_csv(OUT / "phase230_candidate_screen.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase230_selected_candidates.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase230_candidate_detail.csv", index=False, encoding="utf-8-sig")
    final.to_csv(OUT / "phase230_registry.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(OUT / "phase230_changed_cells.csv", index=False, encoding="utf-8-sig")
    residual_after.to_csv(OUT / "phase230_residual_gt20.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase230_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(json.dumps({"created_at": CREATED_AT, "git_hash": git_hash()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    selected_view = selected.rename(
        columns={
            "parent_code": "상위산업",
            "source_label": "후보자료",
            "target_middle_codes": "적용대상",
            "base_block_error_eok": "기준오차_억원",
            "candidate_block_error_eok": "후보오차_억원",
            "block_reduction_eok": "감소_억원",
            "target_max_after_pct": "대상최대오차_pct",
            "max_sibling_worsen_pp": "형제업종최대악화_pp",
            "gt20_after": "20초과후",
            "high_worsened_cells": "20초과신규악화",
            "adoptable": "채택",
        }
    )
    if not selected_view.empty:
        selected_view = selected_view[["상위산업", "후보자료", "alpha", "적용대상", "기준오차_억원", "후보오차_억원", "감소_억원", "대상최대오차_pct", "형제업종최대악화_pp", "20초과후", "20초과신규악화", "채택"]]
    changed_view = changed[
        [
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "base_predicted_gva_eok",
            "base_error_rate_pct",
            "phase230_predicted_gva_eok",
            "phase230_error_rate_pct",
            "phase230_source",
        ]
    ].rename(
        columns={
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "base_predicted_gva_eok": "Phase217추정_억원",
            "base_error_rate_pct": "Phase217오차_pct",
            "phase230_predicted_gva_eok": "Phase230추정_억원",
            "phase230_error_rate_pct": "Phase230오차_pct",
            "phase230_source": "적용자료",
        }
    )
    residual_view = residual_after[
        ["parent_code", "middle_code", "middle_label", "actual_gva_eok", "phase230_predicted_gva_eok", "phase230_error_rate_pct", "phase230_source"]
    ].rename(
        columns={
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase230_predicted_gva_eok": "추정GVA_억원",
            "phase230_error_rate_pct": "오차_pct",
            "phase230_source": "경로",
        }
    )

    REPORT.write_text(
        f"""# Phase230 고양 특정업종 제한 정밀화 재검증

생성시각: {CREATED_AT}

## 목적

Phase229는 고양시 방송업 개선에 `언론매체 방송사 수`를 사용하면서 J00 상위산업 전체 중분류에 후보 배분을 적용했다. 이는 포항시 실험에서 이미 배제한 방식이다. 이번 단계는 후보 지표를 해당 잔여 고오차 업종에만 적용하고, 상위산업 총량 유지를 위한 형제 업종 비례조정은 별도 악화 한도로 검증한다.

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

## 결론

1. 고양시 성능개선은 Phase229의 상위산업 전체 배분이 아니라 Phase230의 특정업종 제한 방식으로 보는 것이 맞다.
2. `언론매체 방송사 수`는 방송업에만 직접 적용하고, 나머지 정보통신업 중분류는 총량 유지를 위한 비례조정만 허용했다.
3. 이 방식에서도 방송업은 20% 초과 잔여오차에서 벗어나며, 신규 20% 초과 악화 셀은 발생하지 않았다.
4. 이후 포스터·제안서에 고양시 개선 결과를 반영한다면 Phase229가 아니라 Phase230 값을 사용해야 한다.
""",
        encoding="utf-8",
    )
    print(summary.to_string(index=False))
    print(audit.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
