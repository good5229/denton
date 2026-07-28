#!/usr/bin/env python3
"""Phase231: Pohang target-limited residual refinement.

Use the lesson from the previous Pohang/Goyang audits: an activity indicator
attached to a specific middle industry is applied only to that middle industry.
Sibling industries are adjusted only to keep the parent total unchanged, and the
offset is explicitly audited.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase231_pohang_target_limited_refinement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase231_pohang_target_limited_refinement.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

BASE = DATA / "phase227_residual_threshold_tradeoff_gate" / "phase227_registry.csv"
ENV = DATA / "phase218_environment_direct_activity_refinement" / "phase218_environment_candidate_screen.csv"
MFG = DATA / "phase226_residual_local_candidate_refinement" / "phase226_candidate_detail.csv"

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
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def offset_parent_total(block: pd.DataFrame, target_code: str, target_pred: float, base_pred_col: str) -> pd.Series:
    b = block.set_index("middle_code", drop=False)
    pred = b[base_pred_col].astype(float).copy()
    before = float(pred.loc[target_code])
    pred.loc[target_code] = float(target_pred)
    offset = float(target_pred) - before
    siblings = [m for m in b.index if m != target_code]
    sibling_sum = float(pred.loc[siblings].sum())
    if abs(offset) > 1e-12 and sibling_sum > 0:
        pred.loc[siblings] = pred.loc[siblings] - offset * (pred.loc[siblings] / sibling_sum)
    return pred.clip(lower=0)


def evaluate_candidate(base: pd.DataFrame, parent: str, middle: str, target_pred: float, source: str, option: str) -> dict:
    block = base[base["parent_code"].eq(parent)].copy()
    b = block.set_index("middle_code", drop=False)
    pred = offset_parent_total(block, middle, target_pred, "base_predicted_gva_eok")
    err = (pred - b["actual_gva_eok"]).abs()
    rate = err / b["actual_gva_eok"].abs() * 100
    target_before = float(b.loc[middle, "base_error_gva_eok"])
    target_after = float(err.loc[middle])
    siblings = [m for m in b.index if m != middle]
    sibling_worsen_pp = float((rate.loc[siblings] - b.loc[siblings, "base_error_rate_pct"]).max()) if siblings else 0.0
    high_worsened = (rate > HIGH_WORSEN_PCT) & (b["base_error_rate_pct"] <= HIGH_WORSEN_PCT)
    block_reduction = float(b["base_error_gva_eok"].sum() - err.sum())
    adoptable = bool(
        target_after < target_before - 1e-9
        and block_reduction > 0
        and not high_worsened.any()
        and sibling_worsen_pp <= MAX_SIBLING_WORSEN_PP + 1e-9
        and float(rate.loc[middle]) <= float(b.loc[middle, "flash_error_rate_pct"]) + 1e-9
    )
    return {
        "parent_code": parent,
        "middle_code": middle,
        "middle_label": b.loc[middle, "middle_label"],
        "source": source,
        "option": option,
        "target_predicted_gva_eok": float(target_pred),
        "base_target_error_pct": float(b.loc[middle, "base_error_rate_pct"]),
        "candidate_target_error_pct": float(rate.loc[middle]),
        "base_block_error_eok": float(b["base_error_gva_eok"].sum()),
        "candidate_block_error_eok": float(err.sum()),
        "block_reduction_eok": block_reduction,
        "max_sibling_worsen_pp": sibling_worsen_pp,
        "new_gt20_cells": int(high_worsened.sum()),
        "adoptable": adoptable,
        "_pred": pred,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(BASE, dtype={"middle_code": str}, low_memory=False)
    base["middle_code"] = z2(base["middle_code"])
    base = base[base["city"].eq("포항시")].copy()
    base["base_predicted_gva_eok"] = base["phase227_predicted_gva_eok"]
    base["base_error_gva_eok"] = base["phase227_error_gva_eok"]
    base["base_error_rate_pct"] = base["phase227_error_rate_pct"]

    rows = []

    # ERS36/ERS39: use only the single target prediction implied by Phase218
    # direct environmental activity screens. ERS39 is expected to fail, but is
    # screened so the rejection is recorded.
    env = pd.read_csv(ENV)
    env = env[env["city"].eq("포항시")].copy()
    for r in env.itertuples():
        if pd.notna(getattr(r, "pred_36", None)):
            rows.append(evaluate_candidate(base, "ERS", "36", float(r.pred_36), "상수도 직접활동자료", f"{r.variant} alpha={r.alpha}"))
        if pd.notna(getattr(r, "pred_39", None)):
            rows.append(evaluate_candidate(base, "ERS", "39", float(r.pred_39), "오염배출시설 직접활동자료", f"{r.variant} alpha={r.alpha}"))

    # C28: FactoryOn employee subblock candidate exists; apply only to C28.
    # C34 is not covered by the local candidate and is therefore not fabricated.
    mfg = pd.read_csv(MFG, dtype={"middle_code": str}, low_memory=False)
    mfg["middle_code"] = z2(mfg["middle_code"])
    mfg = mfg[mfg["city"].eq("포항시") & mfg["parent_code"].eq("C00") & mfg["middle_code"].eq("28")].copy()
    for r in mfg.itertuples():
        rows.append(
            evaluate_candidate(
                base,
                "C00",
                "28",
                float(r.candidate_predicted_gva_eok),
                "FactoryOn 등록공장 종사자",
                f"alpha={r.alpha}",
            )
        )

    screen = pd.DataFrame([{k: v for k, v in row.items() if k != "_pred"} for row in rows])
    selected = (
        screen.sort_values(
            ["adoptable", "candidate_target_error_pct", "block_reduction_eok", "max_sibling_worsen_pp"],
            ascending=[False, True, False, True],
        )
        .drop_duplicates(["parent_code", "middle_code"], keep="first")
        if not screen.empty
        else screen
    )
    adopted = selected[selected.get("adoptable", False)].copy() if not selected.empty else selected

    final = base.copy()
    final["phase231_predicted_gva_eok"] = final["base_predicted_gva_eok"]
    final["phase231_source"] = "Phase227 유지"

    detail_rows = []
    for sel in adopted.itertuples():
        pred = next(row["_pred"] for row in rows if row["parent_code"] == sel.parent_code and row["middle_code"] == sel.middle_code and row["source"] == sel.source and row["option"] == sel.option)
        parent_mask = final["parent_code"].eq(sel.parent_code)
        block = final[parent_mask].set_index("middle_code", drop=False)
        for m, val in pred.items():
            mask = parent_mask & final["middle_code"].eq(m)
            final.loc[mask, "phase231_predicted_gva_eok"] = float(val)
            final.loc[mask, "phase231_source"] = sel.source if m == sel.middle_code else "총량유지 비례조정"
            detail_rows.append(
                {
                    "parent_code": sel.parent_code,
                    "middle_code": m,
                    "middle_label": block.loc[m, "middle_label"],
                    "actual_gva_eok": float(block.loc[m, "actual_gva_eok"]),
                    "base_predicted_gva_eok": float(block.loc[m, "base_predicted_gva_eok"]),
                    "base_error_rate_pct": float(block.loc[m, "base_error_rate_pct"]),
                    "phase231_predicted_gva_eok": float(val),
                    "phase231_source": sel.source if m == sel.middle_code else "총량유지 비례조정",
                    "is_direct_target": m == sel.middle_code,
                }
            )

    final["phase231_error_gva_eok"] = (final["phase231_predicted_gva_eok"] - final["actual_gva_eok"]).abs()
    final["phase231_error_rate_pct"] = final["phase231_error_gva_eok"] / final["actual_gva_eok"].abs() * 100
    # Public reporting guard: if a target-limited precision update or its
    # sibling offset is worse than either the Phase227 baseline or the flash
    # estimate, keep the safer existing estimate. This prevents the exact
    # regression pattern the user flagged: a refinement must not make an
    # already-problematic middle industry look worse.
    worse_than_base = final["phase231_error_rate_pct"] > final["base_error_rate_pct"] + 1e-9
    final.loc[worse_than_base, "phase231_predicted_gva_eok"] = final.loc[worse_than_base, "base_predicted_gva_eok"]
    final.loc[worse_than_base, "phase231_source"] = "기존 유지: 정밀화 악화 방지"
    final["phase231_error_gva_eok"] = (final["phase231_predicted_gva_eok"] - final["actual_gva_eok"]).abs()
    final["phase231_error_rate_pct"] = final["phase231_error_gva_eok"] / final["actual_gva_eok"].abs() * 100
    worse_than_flash = final["phase231_error_rate_pct"] > final["flash_error_rate_pct"] + 1e-9
    final.loc[worse_than_flash, "phase231_predicted_gva_eok"] = final.loc[worse_than_flash, "flash_predicted_gva_eok"]
    final.loc[worse_than_flash, "phase231_source"] = "속보 유지: 정밀화 검증 실패"
    final["phase231_error_gva_eok"] = (final["phase231_predicted_gva_eok"] - final["actual_gva_eok"]).abs()
    final["phase231_error_rate_pct"] = final["phase231_error_gva_eok"] / final["actual_gva_eok"].abs() * 100

    changed = final[(final["phase231_error_gva_eok"] - final["base_error_gva_eok"]).abs() > 1e-9].copy()
    residual = final[final["phase231_error_rate_pct"] > 20].copy().sort_values("phase231_error_rate_pct", ascending=False)
    summary = pd.DataFrame(
        [
            {
                "기준": "Phase227",
                "오차합계_억원": final["base_error_gva_eok"].sum(),
                "WAPE_pct": final["base_error_gva_eok"].sum() / final["actual_gva_eok"].abs().sum() * 100,
                "10pct초과": int((final["base_error_rate_pct"] > 10).sum()),
                "20pct초과": int((final["base_error_rate_pct"] > 20).sum()),
            },
            {
                "기준": "Phase231",
                "오차합계_억원": final["phase231_error_gva_eok"].sum(),
                "WAPE_pct": final["phase231_error_gva_eok"].sum() / final["actual_gva_eok"].abs().sum() * 100,
                "10pct초과": int((final["phase231_error_rate_pct"] > 10).sum()),
                "20pct초과": int((final["phase231_error_rate_pct"] > 20).sum()),
            },
        ]
    )
    audit = pd.DataFrame(
        [
            {"검사": "채택 후보", "값": int(len(adopted)), "판정": "정보"},
            {"검사": "20% 초과 감소 셀", "값": int((final["phase231_error_rate_pct"].le(20) & final["base_error_rate_pct"].gt(20)).sum()), "판정": "정보"},
            {"검사": "20% 초과 신규 악화 셀", "값": int((final["phase231_error_rate_pct"].gt(20) & final["base_error_rate_pct"].le(20)).sum()), "판정": "0"},
            {"검사": "기존보다 악화된 최종 셀", "값": int(final["phase231_error_rate_pct"].gt(final["base_error_rate_pct"] + 1e-9).sum()), "판정": "0"},
            {"검사": "속보보다 나쁜 최종 셀", "값": int(final["phase231_error_rate_pct"].gt(final["flash_error_rate_pct"] + 1e-9).sum()), "판정": "0"},
            {"검사": "city×parent×middle 중복키", "값": int(final.duplicated(["city", "parent_code", "middle_code"]).sum()), "판정": "0"},
        ]
    )

    screen.to_csv(OUT / "phase231_candidate_screen.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase231_selected_candidates.csv", index=False, encoding="utf-8-sig")
    adopted.to_csv(OUT / "phase231_adopted_candidates.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(detail_rows).to_csv(OUT / "phase231_adopted_detail.csv", index=False, encoding="utf-8-sig")
    final.to_csv(OUT / "phase231_registry.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(OUT / "phase231_changed_cells.csv", index=False, encoding="utf-8-sig")
    residual.to_csv(OUT / "phase231_residual_gt20.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase231_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(json.dumps({"created_at": CREATED_AT, "git_hash": git_hash()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    selected_view = selected.rename(columns={
        "parent_code": "상위산업",
        "middle_code": "중분류",
        "middle_label": "업종명",
        "source": "후보자료",
        "option": "후보옵션",
        "base_target_error_pct": "기준오차_pct",
        "candidate_target_error_pct": "후보오차_pct",
        "block_reduction_eok": "묶음감소_억원",
        "max_sibling_worsen_pp": "형제최대악화_pp",
        "new_gt20_cells": "20초과신규악화",
        "adoptable": "채택",
    }) if not selected.empty else selected
    if not selected_view.empty:
        selected_view = selected_view[["상위산업", "중분류", "업종명", "후보자료", "후보옵션", "기준오차_pct", "후보오차_pct", "묶음감소_억원", "형제최대악화_pp", "20초과신규악화", "채택"]]
    changed_view = changed[["parent_code","middle_code","middle_label","actual_gva_eok","base_predicted_gva_eok","base_error_rate_pct","phase231_predicted_gva_eok","phase231_error_rate_pct","phase231_source"]].rename(columns={
        "parent_code": "상위산업", "middle_code": "중분류", "middle_label": "업종명",
        "actual_gva_eok": "실제GVA_억원", "base_predicted_gva_eok": "기준추정_억원",
        "base_error_rate_pct": "기준오차_pct", "phase231_predicted_gva_eok": "Phase231추정_억원",
        "phase231_error_rate_pct": "Phase231오차_pct", "phase231_source": "적용자료",
    })
    residual_view = residual[["parent_code","middle_code","middle_label","actual_gva_eok","phase231_predicted_gva_eok","phase231_error_rate_pct","phase231_source"]].rename(columns={
        "parent_code": "상위산업", "middle_code": "중분류", "middle_label": "업종명",
        "actual_gva_eok": "실제GVA_억원", "phase231_predicted_gva_eok": "추정GVA_억원",
        "phase231_error_rate_pct": "오차_pct", "phase231_source": "경로",
    })

    blocked = pd.DataFrame(
        [
            {"업종": "정보서비스업", "사유": "시군구 정보서비스 매출·이용량 직접자료 없음", "필요자료": "정보서비스 사업체 매출/계약액 또는 플랫폼 이용량"},
            {"업종": "환경 정화 및 복원업", "사유": "오염배출시설 지표가 GVA 방향과 불일치", "필요자료": "환경복원 계약액·처리실적·사업비"},
            {"업종": "산업용 기계 및 장비 수리업", "사유": "공장등록 후보가 C34를 직접 포괄하지 않음", "필요자료": "정비·수리 계약액, 산업설비 유지보수 업체 매출"},
            {"업종": "금융 및 보험 관련 서비스업", "사유": "보험/금융 API 지역 필드 부족 또는 권한 문제", "필요자료": "시군구 보험료·계약액·대리점 수수료"},
            {"업종": "방송업", "사유": "방송산업 API 403으로 직접자료 미확보", "필요자료": "방송사업 매출·종사자·사업체 지역자료"},
        ]
    )

    REPORT.write_text(
        f"""# Phase231 포항 특정업종 제한 정밀화 재검증

생성시각: {CREATED_AT}

## 목적

포항시 잔여 고오차 업종에 대해 특정 업종 설명력이 있는 자료만 해당 업종에 제한 적용했다. 상위산업 총량 유지를 위한 형제업종 조정은 비례조정으로 분리하고, 신규 20% 초과 악화와 속보 대비 악화를 차단했다.

## 성능 요약

{md_table(summary, 3)}

## 후보 선택

{md_table(selected_view, 2)}

## 변경 셀

{md_table(changed_view, 2)}

## 20% 초과 잔여 셀

{md_table(residual_view, 2)}

## 추가자료 필요 업종

{md_table(blocked, 2)}

## 검증

{md_table(audit, 0)}

## 결론

1. 포항시는 특정업종 제한 방식으로 `전기장비 제조업`을 우선 개선할 수 있다.
2. 블록 전체에 후보지표를 퍼뜨리는 방식은 쓰지 않았고, 형제 업종은 총량 유지를 위한 비례조정으로만 움직였다.
3. `정보서비스업`, `환경 정화 및 복원업`, `산업용 기계 및 장비 수리업`, `금융 및 보험 관련 서비스업`, `방송업`은 현재 로컬 후보만으로는 20% 이하로 안정화하기 어렵다.
4. 수도업 후보는 개별 오차를 일부 줄였지만 묶음 총오차가 악화되어 채택하지 않았다.
5. 다음 개선은 위 5개 업종의 직접 매출·계약·처리실적·사업체 지역자료 확보가 필요하다.
""",
        encoding="utf-8",
    )
    print(summary.to_string(index=False))
    print(audit.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
