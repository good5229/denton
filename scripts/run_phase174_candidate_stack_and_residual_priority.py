#!/usr/bin/env python3
"""Phase174: candidate stack and residual priority after port-gated H50.

This phase does not invent a new actual-calibrated correction.  It puts the
existing candidate families on a common decision table and creates two
registries:

* conservative_activity_stack: Phase124 + port-cargo gated H50 only.
* precision_candidate_stack: Phase126 COMWEL precision registry + port-cargo
  gated H50.

COMWEL is a 2025 snapshot, so it remains a precision/refinement candidate, not
a strict flash claim.  Peer-prior diagnostics are summarized but not stacked as
operational rules when their gates used target actuals or created target
worsening.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/phase174_candidate_stack_and_residual_priority"
REPORT = ROOT / "reports/partial_statistics_estimation_phase174_candidate_stack_and_residual_priority.md"

PHASE124 = ROOT / "data/processed/phase124_pps_subblock_no_worse/phase124_registry.csv"
PHASE126 = ROOT / "data/processed/phase126_risk_budgeted_comwel_selection/phase126_registry.csv"
PHASE161_SUM = ROOT / "data/processed/phase161_peer_prior_validation_gate/phase161_city_summary.csv"
PHASE164_SUM = ROOT / "data/processed/phase164_peer_distance_operational_gate/phase164_city_summary.csv"
PHASE173_SUM = ROOT / "data/processed/phase173_port_activity_gated_h50_registry/phase173_summary.csv"
PORT_CARGO = ROOT / "data/raw/phase118_public_sources/mof_DT_MLTM_1310_pohang_all_products_latest60.csv"


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)


def simple_markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "\n"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(str(c) for c in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if pd.isna(v):
                vals.append("")
            elif isinstance(v, float):
                vals.append(f"{v:,.2f}")
            else:
                vals.append(str(v).replace("|", "\\|"))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def error_cols(df: pd.DataFrame, pred_col: str, prefix: str) -> pd.DataFrame:
    out = df.copy()
    out[f"{prefix}_predicted_gva_eok"] = out[pred_col].astype(float)
    out[f"{prefix}_error_gva_eok"] = (out[f"{prefix}_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out[f"{prefix}_error_rate_pct"] = out[f"{prefix}_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    return out


def apply_port_gate(
    df: pd.DataFrame,
    *,
    base_pred_col: str,
    prefix: str,
    floor_share: float = 0.07,
) -> pd.DataFrame:
    out = error_cols(df, base_pred_col, prefix)
    out[f"{prefix}_rule_applied"] = False
    port_cities = {"포항시"} if PORT_CARGO.exists() else set()

    pred_col = f"{prefix}_predicted_gva_eok"
    for city in port_cities:
        mask = (out["city"] == city) & (out["parent_code"] == "H00")
        h = out.loc[mask]
        if h.empty or 50 not in set(h["middle_code"].astype(int)):
            continue
        parent_sum = h[pred_col].sum()
        if parent_sum <= 0:
            continue
        h50_mask = mask & (out["middle_code"].astype(int) == 50)
        non50_mask = mask & (out["middle_code"].astype(int) != 50)
        current_h50 = out.loc[h50_mask, pred_col].sum()
        target_h50 = max(current_h50, parent_sum * floor_share)
        if target_h50 <= current_h50 + 1e-9:
            continue
        non50_sum = out.loc[non50_mask, pred_col].sum()
        if non50_sum <= 0:
            continue
        scale = (parent_sum - target_h50) / non50_sum
        out.loc[non50_mask, pred_col] = out.loc[non50_mask, pred_col] * scale
        out.loc[h50_mask, pred_col] = target_h50
        out.loc[mask, f"{prefix}_rule_applied"] = True

    out[f"{prefix}_error_gva_eok"] = (out[pred_col] - out["actual_gva_eok"]).abs()
    out[f"{prefix}_error_rate_pct"] = out[f"{prefix}_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    return out


def summarize(df: pd.DataFrame, prefix: str, label: str, track: str) -> pd.DataFrame:
    err = f"{prefix}_error_gva_eok"
    rate = f"{prefix}_error_rate_pct"
    rows = []
    for city, g in df.groupby("city", sort=False):
        rows.append(
            {
                "track": track,
                "candidate": label,
                "city": city,
                "cells": len(g),
                "actual_sum_eok": g["actual_gva_eok"].sum(),
                "error_sum_eok": g[err].sum(),
                "wape_pct": g[err].sum() / g["actual_gva_eok"].sum() * 100,
                "gt10_cells": int((g[rate] > 10).sum()),
                "gt20_cells": int((g[rate] > 20).sum()),
                "gt50_cells": int((g[rate] > 50).sum()),
            }
        )
    rows.append(
        {
            "track": track,
            "candidate": label,
            "city": "합계",
            "cells": len(df),
            "actual_sum_eok": df["actual_gva_eok"].sum(),
            "error_sum_eok": df[err].sum(),
            "wape_pct": df[err].sum() / df["actual_gva_eok"].sum() * 100,
            "gt10_cells": int((df[rate] > 10).sum()),
            "gt20_cells": int((df[rate] > 20).sum()),
            "gt50_cells": int((df[rate] > 50).sum()),
        }
    )
    return pd.DataFrame(rows)


def residual(df: pd.DataFrame, prefix: str, track: str) -> pd.DataFrame:
    pred = f"{prefix}_predicted_gva_eok"
    err = f"{prefix}_error_gva_eok"
    rate = f"{prefix}_error_rate_pct"
    cols = [
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        pred,
        err,
        rate,
    ]
    out = df.loc[df[rate] > 20, cols].copy()
    out["track"] = track
    out["rank_by_error_eok"] = out[err].rank(method="first", ascending=False).astype(int)
    out = out.sort_values(err, ascending=False)
    return out


def candidate_decision_table(p126_summary: pd.DataFrame | None = None) -> pd.DataFrame:
    rows: list[dict] = []
    if PHASE161_SUM.exists():
        s = pd.read_csv(PHASE161_SUM)
        rows.append(
            {
                "candidate_family": "Phase161 외부 peer 사전값",
                "track": "진단",
                "best_use": "고양 K00·포항 J00처럼 실제로 먹히는 블록 확인",
                "adoption": "운영채택 불가",
                "reason": "보고서상 고양·포항 actual을 보고 게이트했으므로 성능 주장은 누수 위험",
                "goyang_wape_pct": float(s.loc[s["city"].eq("고양시"), "phase161_wape_pct"].iloc[0]),
                "pohang_wape_pct": float(s.loc[s["city"].eq("포항시"), "phase161_wape_pct"].iloc[0]),
            }
        )
    if PHASE164_SUM.exists():
        s = pd.read_csv(PHASE164_SUM)
        rows.append(
            {
                "candidate_family": "Phase164 peer-distance 운영 게이트",
                "track": "운영 후보",
                "best_use": "외부 LOO와 거리 기준으로 타깃 actual 없이 적용범위 축소",
                "adoption": "보류",
                "reason": "타깃 actual 미사용 장점은 있으나 적용 후 악화 셀 3개씩 발생",
                "goyang_wape_pct": float(s.loc[s["city"].eq("고양시"), "phase164_wape_pct"].iloc[0]),
                "pohang_wape_pct": float(s.loc[s["city"].eq("포항시"), "phase164_wape_pct"].iloc[0]),
            }
        )
    if PHASE173_SUM.exists():
        s = pd.read_csv(PHASE173_SUM)
        t = s[s["candidate"].eq("항만물동량 존재지역 H50 7% 하한")]
        rows.append(
            {
                "candidate_family": "Phase173 항만물동량 H50 게이트",
                "track": "제한적 운영 후보",
                "best_use": "항만물동량 자료가 있는 도시의 H50 수상운송 배분",
                "adoption": "제한채택 후보",
                "reason": "고양 음성대조를 통과하고 포항 H00 개선. 다만 항만도시 외부 검증 추가 필요",
                "goyang_wape_pct": float(t.loc[t["city"].eq("고양시"), "wape_pct"].iloc[0]),
                "pohang_wape_pct": float(t.loc[t["city"].eq("포항시"), "wape_pct"].iloc[0]),
            }
        )
    rows.append(
        {
            "candidate_family": "Phase126 COMWEL 리스크 예산",
            "track": "정밀화 후보",
            "best_use": "2025 사업장 스냅샷으로 구조 재배분",
            "adoption": "정밀화 한정",
            "reason": "성과는 있으나 2025 스냅샷이므로 2023 속보성 지표로 주장 불가",
            "goyang_wape_pct": (
                float(p126_summary.loc[p126_summary["city"].eq("고양시"), "wape_pct"].iloc[0])
                if p126_summary is not None and (p126_summary["city"].eq("고양시")).any()
                else None
            ),
            "pohang_wape_pct": (
                float(p126_summary.loc[p126_summary["city"].eq("포항시"), "wape_pct"].iloc[0])
                if p126_summary is not None and (p126_summary["city"].eq("포항시")).any()
                else None
            ),
        }
    )
    return pd.DataFrame(rows)


def main() -> None:
    ensure_dirs()
    p124 = pd.read_csv(PHASE124)
    p126 = pd.read_csv(PHASE126)

    conservative = apply_port_gate(
        p124,
        base_pred_col="phase124_predicted_gva_eok",
        prefix="phase174_conservative",
    )
    precision = apply_port_gate(
        p126,
        base_pred_col="phase126_predicted_gva_eok",
        prefix="phase174_precision",
    )

    base = error_cols(p124, "phase124_predicted_gva_eok", "phase174_base")
    p126_base = error_cols(p126, "phase126_predicted_gva_eok", "phase174_phase126")
    p126_summary = summarize(p126_base, "phase174_phase126", "Phase126 COMWEL 정밀화", "정밀화 후보")

    summary = pd.concat(
        [
            summarize(base, "phase174_base", "Phase124 기준선", "기준"),
            summarize(conservative, "phase174_conservative", "Phase124+항만물동량 H50 게이트", "보수 운영 후보"),
            p126_summary,
            summarize(precision, "phase174_precision", "Phase126+항만물동량 H50 게이트", "정밀화 후보"),
        ],
        ignore_index=True,
    )
    decision = candidate_decision_table(p126_summary)
    res_con = residual(conservative, "phase174_conservative", "보수 운영 후보")
    res_pre = residual(precision, "phase174_precision", "정밀화 후보")

    conservative.to_csv(OUT / "phase174_conservative_activity_stack_registry.csv", index=False, encoding="utf-8-sig")
    precision.to_csv(OUT / "phase174_precision_candidate_stack_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase174_stack_summary.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(OUT / "phase174_candidate_decision_table.csv", index=False, encoding="utf-8-sig")
    res_con.to_csv(OUT / "phase174_conservative_residual_gt20.csv", index=False, encoding="utf-8-sig")
    res_pre.to_csv(OUT / "phase174_precision_residual_gt20.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "inputs": {
                    "phase124": str(PHASE124.relative_to(ROOT)),
                    "phase126": str(PHASE126.relative_to(ROOT)),
                    "phase173": str(PHASE173_SUM.relative_to(ROOT)),
                },
                "target": "GVA, middle-industry annual validation registry",
                "leakage_boundary": "No new target-actual-calibrated coefficients are introduced. COMWEL remains precision-only.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    top_con = res_con.head(20).copy()
    top_pre = res_pre.head(20).copy()
    for df in (top_con, top_pre):
        for c in list(df.columns):
            if c.endswith("_eok") or c.endswith("_pct"):
                df[c] = df[c].astype(float).round(2)

    report = f"""# Phase174 후보 스택과 잔여 고오차 우선순위

## 목적

신규 공공데이터포털 API가 아직 `403 Forbidden` 상태이므로, 현재 로컬에서 검증 가능한 후보들을 같은 기준으로 재정렬했다. 이 단계의 핵심은 총부가가치(GVA) 추정 성능을 높이되, 다음 경계를 지키는 것이다.

- 타깃 도시 actual을 보고 새 보정계수를 고르지 않는다.
- 속보성 후보와 사후 정밀화 후보를 섞어 주장하지 않는다.
- “그럴듯한 보조지표”라도 악화·누수·공표시점 문제가 있으면 보류한다.

## 후보군 판정

{simple_markdown_table(decision)}

## 스택별 성능

{simple_markdown_table(summary[['track','candidate','city','cells','actual_sum_eok','error_sum_eok','wape_pct','gt10_cells','gt20_cells','gt50_cells']])}

## 보수 운영 후보: 남은 20% 초과 상위 오차

{simple_markdown_table(top_con[['track','rank_by_error_eok','city','parent_code','middle_code','middle_label','actual_gva_eok','phase174_conservative_predicted_gva_eok','phase174_conservative_error_gva_eok','phase174_conservative_error_rate_pct']])}

## 정밀화 후보: 남은 20% 초과 상위 오차

{simple_markdown_table(top_pre[['track','rank_by_error_eok','city','parent_code','middle_code','middle_label','actual_gva_eok','phase174_precision_predicted_gva_eok','phase174_precision_error_gva_eok','phase174_precision_error_rate_pct']])}

## 판정

1. **현재 가장 안전한 추가 적용 후보는 항만물동량 게이트 기반 H50 수상운송 배분**이다. 포항에는 적용되지만 고양에는 적용되지 않아 음성대조를 통과한다.
2. **COMWEL 사업장 자료는 정밀화 성능을 개선하지만 속보성 지표가 아니다.** 2025 스냅샷이므로 “공표 후 구조 재산출”에만 둔다.
3. **peer 계열은 방법론 진단으로 남긴다.** Phase161은 성능이 좋아 보이지만 타깃 actual 게이트라 운영 성능 주장이 어렵고, Phase164는 타깃 actual 미사용이지만 악화 셀이 남는다.
4. 잔여 상위 오차는 여전히 고양 J00/ERS/C00/MN0, 포항 MN0/K00/ERS/C00에 집중된다. 이들은 조달업체·금융취급액·폐기물 처리량·콘텐츠/통신 사업장 매출·제조업 출하/전력처럼 업종별 직접 활동자료가 열려야 10~20% 이하로 안정화될 가능성이 높다.

## 산출물

- `data/processed/phase174_candidate_stack_and_residual_priority/phase174_stack_summary.csv`
- `data/processed/phase174_candidate_stack_and_residual_priority/phase174_candidate_decision_table.csv`
- `data/processed/phase174_candidate_stack_and_residual_priority/phase174_conservative_activity_stack_registry.csv`
- `data/processed/phase174_candidate_stack_and_residual_priority/phase174_precision_candidate_stack_registry.csv`
- `data/processed/phase174_candidate_stack_and_residual_priority/phase174_conservative_residual_gt20.csv`
- `data/processed/phase174_candidate_stack_and_residual_priority/phase174_precision_residual_gt20.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
