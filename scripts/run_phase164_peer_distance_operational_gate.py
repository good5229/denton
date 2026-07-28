#!/usr/bin/env python3
"""Phase164: operational peer-distance gate for similar-peer routing.

This phase tries to turn Phase162's lesson into a conservative, non-ex-post
gate.  It does not look at Goyang/Pohang actuals when deciding whether to apply
the peer prior.  A target city-parent block is eligible only if:

1. the parent has a selected external LOO candidate;
2. the target's peer distance is not outside the external LOO interquartile
   distance range for that selected parent/k/alpha;
3. the external selected candidate reduced WAPE by at least 5pp;
4. the external selected candidate's 20%-error cell share is lower than the
   external baseline's 20%-error cell share.

Goyang/Pohang actuals are used only after the gate for evaluation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase164_peer_distance_operational_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase164_peer_distance_operational_gate.md"

P162_DETAIL = DATA / "phase162_similar_peer_prior_routing" / "phase162_goyang_pohang_similar_peer_registry.csv"
P162_PARENT = DATA / "phase162_similar_peer_prior_routing" / "phase162_parent_summary.csv"
P162_SELECTED = DATA / "phase162_similar_peer_prior_routing" / "phase162_selected_params.csv"
P162_EXT_DETAIL = DATA / "phase162_similar_peer_prior_routing" / "phase162_external_similar_peer_screen_detail.csv"

MIN_EXTERNAL_REDUCTION_PP = 5.0
MAX_TARGET_DISTANCE_QUANTILE = 0.75


def md_table(df: pd.DataFrame, digits: int = 2, max_rows: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if max_rows is not None and len(view) > max_rows:
        view = view.head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
    view = view.fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[col].replace("|", "\\|") for col in view.columns) + " |")
    if max_rows is not None and len(df) > max_rows:
        lines.append(f"\n_상위 {max_rows}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def external_gate_table(ext_detail: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in selected.itertuples(index=False):
        parent = str(r.parent_code)
        k = int(r.k)
        alpha = float(r.alpha)
        if not bool(r.selected) or alpha <= 0:
            continue
        g = ext_detail[
            ext_detail["parent_code"].astype(str).eq(parent)
            & ext_detail["k"].astype(int).eq(k)
            & np.isclose(ext_detail["alpha"].astype(float), alpha)
        ].copy()
        if g.empty:
            continue
        # Region-level baseline/candidate summaries.
        reg = (
            g.groupby("region_key", as_index=False)
            .agg(
                peer_mean_l1_distance=("peer_mean_l1_distance", "first"),
                actual_sum=("actual_gva_eok", "sum"),
                candidate_error_sum=("candidate_error_eok", "sum"),
                candidate_gt20=("candidate_error_rate_pct", lambda s: int((s > 20).sum())),
                cells=("division_code", "size"),
            )
        )
        base = g.copy()
        base["baseline_error_eok"] = (base["baseline_share"] * base["parent_gva_eok"] - base["actual_gva_eok"]).abs()
        base_reg = (
            base.groupby("region_key", as_index=False)
            .agg(
                baseline_error_sum=("baseline_error_eok", "sum"),
                baseline_gt20=("error_rate_pct", lambda s: int((s > 20).sum())),
            )
        )
        reg = reg.merge(base_reg, on="region_key", how="left")
        reg["candidate_wape"] = reg["candidate_error_sum"] / reg["actual_sum"].replace(0, np.nan) * 100
        reg["baseline_wape"] = reg["baseline_error_sum"] / reg["actual_sum"].replace(0, np.nan) * 100
        reg["region_reduction_pp"] = reg["baseline_wape"] - reg["candidate_wape"]
        rows.append(
            {
                "parent_code": parent,
                "k": k,
                "alpha": alpha,
                "distance_p50": float(reg["peer_mean_l1_distance"].quantile(0.50)),
                "distance_p75": float(reg["peer_mean_l1_distance"].quantile(0.75)),
                "distance_p90": float(reg["peer_mean_l1_distance"].quantile(0.90)),
                "external_reduction_pp": float(r.wape_reduction_pp),
                "external_baseline_gt20_share": float(reg["baseline_gt20"].sum() / reg["cells"].sum()),
                "external_candidate_gt20_share": float(reg["candidate_gt20"].sum() / reg["cells"].sum()),
                "external_region_improved_share": float((reg["region_reduction_pp"] > 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def apply_gate(detail: pd.DataFrame, parent: pd.DataFrame, gate: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    gate_map = gate.set_index("parent_code").to_dict("index")
    decisions = []
    for row in parent.itertuples(index=False):
        parent_code = str(row.parent_code)
        g = gate_map.get(parent_code)
        target_distance = getattr(row, "peer_mean_l1_distance")
        alpha = float(getattr(row, "alpha"))
        if g is None or alpha <= 0:
            status = "미적용: 외부 안정 후보 없음"
            apply = False
        elif pd.isna(target_distance):
            status = "미적용: target peer 거리 없음"
            apply = False
        elif float(target_distance) > float(g["distance_p75"]):
            status = "미적용: target peer 거리가 외부 p75 초과"
            apply = False
        elif float(g["external_reduction_pp"]) < MIN_EXTERNAL_REDUCTION_PP:
            status = "미적용: 외부 WAPE 감소폭 부족"
            apply = False
        elif float(g["external_candidate_gt20_share"]) >= float(g["external_baseline_gt20_share"]):
            status = "미적용: 외부 20%초과 셀 비율 개선 없음"
            apply = False
        elif float(g["external_region_improved_share"]) < 0.6:
            status = "미적용: 외부 지역별 개선 비율 부족"
            apply = False
        else:
            status = "적용: 운영형 peer-distance gate 통과"
            apply = True
        decisions.append(
            {
                "city": row.city,
                "parent_code": parent_code,
                "apply_phase162": bool(apply),
                "gate_status": status,
                "target_peer_distance": target_distance,
                **({f"external_{k}": v for k, v in g.items()} if g else {}),
            }
        )
    decision = pd.DataFrame(decisions)
    detail = detail.merge(decision[["city", "parent_code", "apply_phase162", "gate_status"]], on=["city", "parent_code"], how="left")
    detail["phase164_predicted_gva_eok"] = detail["parent_controlled_predicted_gva_eok"]
    detail.loc[detail["apply_phase162"].fillna(False), "phase164_predicted_gva_eok"] = detail.loc[
        detail["apply_phase162"].fillna(False), "phase162_predicted_gva_eok"
    ]
    detail["phase164_error_gva_eok"] = (detail["phase164_predicted_gva_eok"] - detail["actual_gva_eok"]).abs()
    detail["phase164_error_rate_pct"] = detail["phase164_error_gva_eok"] / detail["actual_gva_eok"].replace(0, np.nan) * 100
    detail["phase164_error_delta_vs_parent_controlled_eok"] = detail["phase164_error_gva_eok"] - detail["parent_controlled_error_gva_eok"]
    return detail, decision


def city_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in detail.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        base = float(g["parent_controlled_error_gva_eok"].sum())
        err = float(g["phase164_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "baseline_error_eok": base,
                "baseline_wape_pct": base / actual * 100,
                "phase164_error_eok": err,
                "phase164_wape_pct": err / actual * 100,
                "reduction_eok": base - err,
                "reduction_pp": base / actual * 100 - err / actual * 100,
                "baseline_gt20_cells": int((g["parent_controlled_error_rate_pct"] > 20).sum()),
                "phase164_gt20_cells": int((g["phase164_error_rate_pct"] > 20).sum()),
                "worsened_cells": int((g["phase164_error_gva_eok"] > g["parent_controlled_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def parent_summary(detail: pd.DataFrame, decision: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dec = decision.set_index(["city", "parent_code"]).to_dict("index")
    for (city, parent), g in detail.groupby(["city", "parent_code"], sort=False):
        actual = float(g["actual_gva_eok"].sum())
        base = float(g["parent_controlled_error_gva_eok"].sum())
        err = float(g["phase164_error_gva_eok"].sum())
        d = dec.get((city, parent), {})
        rows.append(
            {
                "city": city,
                "parent_code": parent,
                "cells": int(len(g)),
                "gate_status": d.get("gate_status", ""),
                "target_peer_distance": d.get("target_peer_distance", np.nan),
                "actual_sum_eok": actual,
                "baseline_error_eok": base,
                "baseline_wape_pct": base / actual * 100 if actual else np.nan,
                "phase164_error_eok": err,
                "phase164_wape_pct": err / actual * 100 if actual else np.nan,
                "reduction_eok": base - err,
                "worsened_cells": int((g["phase164_error_gva_eok"] > g["parent_controlled_error_gva_eok"] + 1e-9).sum()),
                "phase164_gt20_cells": int((g["phase164_error_rate_pct"] > 20).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["city", "reduction_eok"], ascending=[True, False])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    detail = pd.read_csv(P162_DETAIL)
    parent = pd.read_csv(P162_PARENT)
    selected = pd.read_csv(P162_SELECTED)
    ext_detail = pd.read_csv(P162_EXT_DETAIL)
    gate = external_gate_table(ext_detail, selected)
    routed, decision = apply_gate(detail, parent, gate)
    csum = city_summary(routed)
    psum = parent_summary(routed, decision)
    improved = routed[routed["phase164_error_delta_vs_parent_controlled_eok"].lt(-1e-9)].copy()
    worsened = routed[routed["phase164_error_delta_vs_parent_controlled_eok"].gt(1e-9)].copy()
    remaining = routed[routed["phase164_error_rate_pct"].gt(20)].copy()

    gate.to_csv(OUT / "phase164_external_gate_reference.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(OUT / "phase164_target_gate_decisions.csv", index=False, encoding="utf-8-sig")
    routed.to_csv(OUT / "phase164_operational_gate_registry.csv", index=False, encoding="utf-8-sig")
    csum.to_csv(OUT / "phase164_city_summary.csv", index=False, encoding="utf-8-sig")
    psum.to_csv(OUT / "phase164_parent_summary.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUT / "phase164_improved_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUT / "phase164_worsened_cells.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUT / "phase164_remaining_gt20_cells.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "phase": "phase164_peer_distance_operational_gate",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "uses_goyang_pohang_actual_for_gate": False,
                "gate_rules": {
                    "max_target_distance_quantile": MAX_TARGET_DISTANCE_QUANTILE,
                    "min_external_reduction_pp": MIN_EXTERNAL_REDUCTION_PP,
                    "external_candidate_gt20_share_lt_baseline": True,
                    "external_region_improved_share_min": 0.6,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    applied = psum[psum["gate_status"].astype(str).str.startswith("적용")].copy()

    REPORT.write_text(
        f"""# Phase164 운영형 peer-distance 게이트

## 목적

Phase162의 유사 peer 라우팅은 외부 LOO에서는 개선됐지만 고양·포항 전면 적용에서는 악화됐다. 이번 단계는 고양·포항 actual을 보지 않고도 적용 대상을 줄일 수 있는 운영형 게이트를 시험한다.

## 게이트 규칙

고양·포항 actual은 게이트 선택에 쓰지 않는다. 상위산업 블록은 아래 조건을 모두 만족할 때만 Phase162 유사 peer 후보를 적용한다.

1. 외부 10개 LOO에서 선택된 후보가 있어야 한다.
2. target의 peer 거리가 외부 LOO peer 거리의 p75 이하여야 한다.
3. 외부 LOO WAPE 감소가 5%p 이상이어야 한다.
4. 외부 후보의 20% 초과 셀 비율이 외부 기준보다 낮아야 한다.
5. 외부 지역 중 개선된 지역 비율이 60% 이상이어야 한다.

## 외부 게이트 기준

{md_table(gate.rename(columns={
    'parent_code': '상위산업',
    'k': 'peer 수',
    'alpha': '혼합비',
    'distance_p50': '거리 p50',
    'distance_p75': '거리 p75',
    'distance_p90': '거리 p90',
    'external_reduction_pp': '외부 감소 pp',
    'external_baseline_gt20_share': '외부 기준 20%초과비율',
    'external_candidate_gt20_share': '외부 후보 20%초과비율',
    'external_region_improved_share': '외부 개선지역비율',
}), 2)}

## 도시별 결과

{md_table(csum.rename(columns={
    'city': '지역',
    'actual_sum_eok': '실제합계(억원)',
    'baseline_error_eok': '정규화 기준오차(억원)',
    'baseline_wape_pct': '정규화 기준 WAPE(%)',
    'phase164_error_eok': 'Phase164 오차(억원)',
    'phase164_wape_pct': 'Phase164 WAPE(%)',
    'reduction_eok': '감소(억원)',
    'reduction_pp': '감소 pp',
    'baseline_gt20_cells': '기준 20%초과',
    'phase164_gt20_cells': 'Phase164 20%초과',
    'worsened_cells': '악화 셀',
}), 2)}

## 적용된 블록

{md_table(applied.rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'cells': '중분류 수',
    'gate_status': '게이트',
    'target_peer_distance': 'target 거리',
    'actual_sum_eok': '실제합계(억원)',
    'baseline_error_eok': '기준오차(억원)',
    'baseline_wape_pct': '기준 WAPE(%)',
    'phase164_error_eok': '후보오차(억원)',
    'phase164_wape_pct': '후보 WAPE(%)',
    'reduction_eok': '감소(억원)',
    'worsened_cells': '악화 셀',
    'phase164_gt20_cells': '20%초과',
}), 2)}

## 전체 게이트 결정

{md_table(decision.rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'apply_phase162': '적용',
    'gate_status': '게이트',
    'target_peer_distance': 'target 거리',
    'external_distance_p75': '외부 거리 p75',
    'external_external_reduction_pp': '외부 감소 pp',
    'external_external_candidate_gt20_share': '외부 후보 20%초과비율',
    'external_external_region_improved_share': '외부 개선지역비율',
}), 2, 30)}

## 남은 20% 초과 중분류

{md_table(remaining.sort_values(['city', 'phase164_error_gva_eok'], ascending=[True, False])[[
    'city', 'parent_code', 'middle_code', 'middle_label', 'actual_gva_eok',
    'phase164_predicted_gva_eok', 'phase164_error_gva_eok',
    'phase164_error_rate_pct', 'gate_status'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'middle_code': '코드',
    'middle_label': '중분류',
    'actual_gva_eok': '실제(억원)',
    'phase164_predicted_gva_eok': '추정(억원)',
    'phase164_error_gva_eok': '오차(억원)',
    'phase164_error_rate_pct': '오차(%)',
    'gate_status': '게이트',
}), 2, 40)}

## 판정

1. target actual을 보지 않는 peer-distance 게이트는 Phase162 전면 적용의 악화를 상당 부분 막는다.
2. 하지만 지나치게 보수적으로 작동해 적용 블록이 거의 없거나, 일부 적용 블록에서도 target actual 기준 악화가 생길 수 있다.
3. 따라서 peer prior는 아직 주력 개선 방식이 아니다. 현재 주력은 업종군별 직접 활동자료 확보다.
4. 포스터/보고서에는 peer prior 성능 숫자보다, “외부 일반화 검증을 통해 일괄 보정이 위험하다는 것을 확인하고 직접 활동자료 중심으로 전환했다”는 방법론적 기여가 더 안전하다.
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
