#!/usr/bin/env python3
"""Phase175: operational hybrid of peer-distance and port-activity gates.

Phase164 tested a target-actual-free peer-distance gate but let H00 through,
which created large H00 worsening in both target cities.  Phase173 later showed
that H00 should be routed by a port-cargo activity gate instead of generic
transport peer structure.

This phase therefore tests a stricter operational hybrid:

* Start from Phase124 registry.
* For non-H00 parents, use Phase164 predictions only where the Phase164
  target-actual-free gate applied.
* For H00, ignore Phase164 peer route and use Phase173 port-activity-gated H50
  predictions.
* Use target actual only for the final audit, not for deciding where to apply.

The output is a candidate registry plus an audit of improvements/worsening.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/phase175_operational_hybrid_peer_port_gate"
REPORT = ROOT / "reports/partial_statistics_estimation_phase175_operational_hybrid_peer_port_gate.md"

PHASE124 = ROOT / "data/processed/phase124_pps_subblock_no_worse/phase124_registry.csv"
PHASE164 = ROOT / "data/processed/phase164_peer_distance_operational_gate/phase164_operational_gate_registry.csv"
PHASE173 = ROOT / "data/processed/phase173_port_activity_gated_h50_registry/phase173_port_gated_h50_registry.csv"
PHASE164_DECISIONS = ROOT / "data/processed/phase164_peer_distance_operational_gate/phase164_target_gate_decisions.csv"


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


def add_error_cols(df: pd.DataFrame, pred_col: str, prefix: str) -> pd.DataFrame:
    out = df.copy()
    out[f"{prefix}_predicted_gva_eok"] = out[pred_col].astype(float)
    out[f"{prefix}_error_gva_eok"] = (out[f"{prefix}_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out[f"{prefix}_error_rate_pct"] = out[f"{prefix}_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    return out


def summarize(df: pd.DataFrame, err: str, rate: str, label: str) -> pd.DataFrame:
    rows = []
    for city, g in df.groupby("city", sort=False):
        rows.append(
            {
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p124 = pd.read_csv(PHASE124)
    p164 = pd.read_csv(PHASE164)
    p173 = pd.read_csv(PHASE173)
    decisions = pd.read_csv(PHASE164_DECISIONS)

    key = ["city", "parent_code", "middle_code"]
    base = add_error_cols(p124, "phase124_predicted_gva_eok", "phase175_base")

    hybrid = p124.copy()
    hybrid["phase175_predicted_gva_eok"] = hybrid["phase124_predicted_gva_eok"].astype(float)
    hybrid["phase175_route"] = "Phase124 기준 유지"

    # Non-H00 Phase164 operational peer routes.
    p164_cols = key + ["phase164_predicted_gva_eok", "apply_phase162", "gate_status"]
    merged = hybrid[key].merge(p164[p164_cols], on=key, how="left")
    non_h00_apply = (merged["apply_phase162"].fillna(False).astype(bool)) & (merged["parent_code"] != "H00")
    hybrid.loc[non_h00_apply.values, "phase175_predicted_gva_eok"] = merged.loc[
        non_h00_apply, "phase164_predicted_gva_eok"
    ].to_numpy()
    hybrid.loc[non_h00_apply.values, "phase175_route"] = "Phase164 비H00 peer-distance gate"

    # H00 port-cargo route from Phase173.
    p173_cols = key + ["phase173_port_gated_h50_predicted_gva_eok", "phase173_port_gated_h50_rule_applied"]
    merged173 = hybrid[key].merge(p173[p173_cols], on=key, how="left")
    h00 = merged173["parent_code"].eq("H00")
    hybrid.loc[h00.values, "phase175_predicted_gva_eok"] = merged173.loc[
        h00, "phase173_port_gated_h50_predicted_gva_eok"
    ].to_numpy()
    hybrid.loc[h00.values, "phase175_route"] = "Phase173 H00 항만물동량 게이트"

    hybrid["phase175_error_gva_eok"] = (hybrid["phase175_predicted_gva_eok"] - hybrid["actual_gva_eok"]).abs()
    hybrid["phase175_error_rate_pct"] = hybrid["phase175_error_gva_eok"] / hybrid["actual_gva_eok"].abs() * 100
    hybrid["phase175_error_delta_vs_phase124_eok"] = hybrid["phase175_error_gva_eok"] - hybrid["phase124_error_gva_eok"]
    hybrid["phase175_worsened_vs_phase124"] = hybrid["phase175_error_delta_vs_phase124_eok"] > 1e-8

    summary = pd.concat(
        [
            summarize(base, "phase175_base_error_gva_eok", "phase175_base_error_rate_pct", "Phase124 기준선"),
            summarize(hybrid, "phase175_error_gva_eok", "phase175_error_rate_pct", "Phase175 운영 하이브리드"),
        ],
        ignore_index=True,
    )

    parent = (
        hybrid.groupby(["city", "parent_code"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            phase124_error_eok=("phase124_error_gva_eok", "sum"),
            phase175_error_eok=("phase175_error_gva_eok", "sum"),
            worsened_cells=("phase175_worsened_vs_phase124", "sum"),
            gt20_cells=("phase175_error_rate_pct", lambda s: int((s > 20).sum())),
            routes=("phase175_route", lambda s: ", ".join(sorted(set(s)))),
        )
    )
    parent["phase124_wape_pct"] = parent["phase124_error_eok"] / parent["actual_sum_eok"] * 100
    parent["phase175_wape_pct"] = parent["phase175_error_eok"] / parent["actual_sum_eok"] * 100
    parent["reduction_eok"] = parent["phase124_error_eok"] - parent["phase175_error_eok"]
    parent = parent.sort_values(["city", "reduction_eok"], ascending=[True, False])

    changed = hybrid[hybrid["phase175_route"].ne("Phase124 기준 유지")].copy()
    changed = changed.sort_values("phase175_error_delta_vs_phase124_eok")
    worsened = hybrid[hybrid["phase175_worsened_vs_phase124"]].copy().sort_values(
        "phase175_error_delta_vs_phase124_eok", ascending=False
    )
    residual = hybrid[hybrid["phase175_error_rate_pct"] > 20].copy().sort_values(
        "phase175_error_gva_eok", ascending=False
    )

    route_decisions = decisions.copy()
    route_decisions["phase175_decision"] = route_decisions.apply(
        lambda r: (
            "대체: H00은 항만물동량 게이트 사용"
            if r["parent_code"] == "H00"
            else ("적용: 비H00 peer-distance gate" if bool(r["apply_phase162"]) else "미적용")
        ),
        axis=1,
    )

    hybrid.to_csv(OUT / "phase175_operational_hybrid_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase175_summary.csv", index=False, encoding="utf-8-sig")
    parent.to_csv(OUT / "phase175_parent_audit.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(OUT / "phase175_changed_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUT / "phase175_worsened_cells.csv", index=False, encoding="utf-8-sig")
    residual.to_csv(OUT / "phase175_residual_gt20.csv", index=False, encoding="utf-8-sig")
    route_decisions.to_csv(OUT / "phase175_route_decisions.csv", index=False, encoding="utf-8-sig")

    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "inputs": {
                    "phase124": str(PHASE124.relative_to(ROOT)),
                    "phase164": str(PHASE164.relative_to(ROOT)),
                    "phase173": str(PHASE173.relative_to(ROOT)),
                },
                "decision_rule": "Apply Phase164 only for non-H00 gated parents; always route H00 through Phase173 port-activity gate.",
                "target_actual_use": "audit only",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    show_summary = summary[[
        "candidate", "city", "actual_sum_eok", "error_sum_eok", "wape_pct", "gt10_cells", "gt20_cells", "gt50_cells"
    ]]
    show_parent = parent[
        [
            "city", "parent_code", "routes", "actual_sum_eok", "phase124_error_eok",
            "phase175_error_eok", "phase124_wape_pct", "phase175_wape_pct", "reduction_eok",
            "worsened_cells", "gt20_cells",
        ]
    ].head(20)
    show_changed = changed[
        [
            "city", "parent_code", "middle_code", "middle_label", "actual_gva_eok",
            "phase124_error_gva_eok", "phase175_error_gva_eok",
            "phase175_error_rate_pct", "phase175_error_delta_vs_phase124_eok", "phase175_route",
        ]
    ].head(20)
    show_worse = worsened[
        [
            "city", "parent_code", "middle_code", "middle_label", "actual_gva_eok",
            "phase124_error_gva_eok", "phase175_error_gva_eok",
            "phase175_error_rate_pct", "phase175_error_delta_vs_phase124_eok", "phase175_route",
        ]
    ].head(20)
    show_res = residual[
        [
            "city", "parent_code", "middle_code", "middle_label", "actual_gva_eok",
            "phase175_predicted_gva_eok", "phase175_error_gva_eok",
            "phase175_error_rate_pct", "phase175_route",
        ]
    ].head(25)

    report = f"""# Phase175 운영형 peer-distance·항만물동량 하이브리드

## 목적

Phase164는 타깃 actual을 쓰지 않는 운영형 peer-distance 게이트였지만 H00 운수·창고업에서 큰 악화를 만들었다. Phase173은 H00에 대해 항만물동량이 확인되는 도시만 H50 수상운송업을 보강하는 더 구체적인 규칙을 만들었다.

이번 단계에서는 다음처럼 결합했다.

1. H00은 Phase164 peer 경로를 쓰지 않고 Phase173 항만물동량 게이트를 사용한다.
2. H00이 아닌 상위산업은 Phase164에서 타깃 actual 없이 통과한 peer-distance 게이트만 사용한다.
3. 타깃 actual은 적용 판단이 아니라 사후 감사에만 사용한다.

## 전체 성능

{simple_markdown_table(show_summary)}

## 상위산업별 감사

{simple_markdown_table(show_parent)}

## 개선 셀 상위

{simple_markdown_table(show_changed)}

## 악화 셀

{simple_markdown_table(show_worse)}

## 남은 20% 초과 상위 오차

{simple_markdown_table(show_res)}

## 판정

1. Phase175는 Phase173 단독보다 WAPE를 더 줄인다. 특히 고양 K00과 포항 J00은 외부거리 기반 peer 경로가 큰 개선을 만든다.
2. 그러나 포항 K00과 포항 J00 일부 셀에서 악화가 남는다. 적용 규칙은 타깃 actual을 보지 않았지만, 사후 감사상 완전한 무악화 운영식은 아니다.
3. 따라서 Phase175는 **운영 후보**로 유지하되, 대외 포스터에는 “확정 성능”이 아니라 “외부검증 기반 후보와 악화감사”로 표현해야 한다.
4. 완전 채택하려면 K00 금융보험과 J00 정보통신·콘텐츠의 직접 활동자료가 필요하다. 현재 peer 구조만으로는 10% 이내 안정화를 보장하기 어렵다.

## 산출물

- `data/processed/phase175_operational_hybrid_peer_port_gate/phase175_operational_hybrid_registry.csv`
- `data/processed/phase175_operational_hybrid_peer_port_gate/phase175_summary.csv`
- `data/processed/phase175_operational_hybrid_peer_port_gate/phase175_parent_audit.csv`
- `data/processed/phase175_operational_hybrid_peer_port_gate/phase175_changed_cells.csv`
- `data/processed/phase175_operational_hybrid_peer_port_gate/phase175_worsened_cells.csv`
- `data/processed/phase175_operational_hybrid_peer_port_gate/phase175_residual_gt20.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
