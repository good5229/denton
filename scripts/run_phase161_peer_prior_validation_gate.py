#!/usr/bin/env python3
"""Phase161: validation-gated reading of Phase160 peer-prior routing.

This is deliberately not a prospective operating rule.  It separates two
questions:

1. Which external peer-prior blocks improved Goyang/Pohang without worsening
   any middle industry in the final validation table?
2. Which blocks looked promising externally but are unsafe for poster/performance
   claims because they worsen target-city cells?
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase161_peer_prior_validation_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase161_peer_prior_validation_gate.md"
P160_DETAIL = DATA / "phase160_external_peer_prior_routing" / "phase160_goyang_pohang_peer_prior_registry.csv"
P160_PARENT = DATA / "phase160_external_peer_prior_routing" / "phase160_parent_summary.csv"


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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    detail = pd.read_csv(P160_DETAIL)
    parent = pd.read_csv(P160_PARENT)

    parent["validation_gate"] = "미채택"
    parent.loc[
        (parent["alpha"] > 0)
        & (parent["error_reduction_eok"] > 0)
        & (parent["worsened_cells"] == 0),
        "validation_gate",
    ] = "진단상 무악화 개선"
    parent.loc[
        (parent["alpha"] > 0)
        & (parent["error_reduction_eok"] > 0)
        & (parent["worsened_cells"] > 0),
        "validation_gate",
    ] = "개선되나 악화셀 존재"
    parent.loc[
        (parent["alpha"] > 0)
        & (parent["error_reduction_eok"] <= 0),
        "validation_gate",
    ] = "외부선택이나 대상도시 악화"

    gated_detail = detail.copy()
    gate_map = parent.set_index(["city", "parent_code"])["validation_gate"].to_dict()
    gated_detail["validation_gate"] = [
        gate_map.get((r.city, r.parent_code), "미채택") for r in gated_detail.itertuples()
    ]
    use = gated_detail["validation_gate"].eq("진단상 무악화 개선")
    gated_detail["phase161_predicted_gva_eok"] = gated_detail["phase124_parent_controlled_predicted_gva_eok"]
    gated_detail.loc[use, "phase161_predicted_gva_eok"] = gated_detail.loc[use, "phase160_predicted_gva_eok"]
    gated_detail["phase161_error_gva_eok"] = (
        gated_detail["phase161_predicted_gva_eok"] - gated_detail["actual_gva_eok"]
    ).abs()
    gated_detail["phase161_error_rate_pct"] = (
        gated_detail["phase161_error_gva_eok"] / gated_detail["actual_gva_eok"].replace(0, pd.NA) * 100
    )
    gated_detail["phase161_error_delta_vs_parent_controlled_eok"] = (
        gated_detail["phase161_error_gva_eok"] - gated_detail["phase124_parent_controlled_error_gva_eok"]
    )

    city_rows = []
    for city, g in gated_detail.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        base_err = float(g["phase124_parent_controlled_error_gva_eok"].sum())
        err = float(g["phase161_error_gva_eok"].sum())
        city_rows.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "parent_controlled_baseline_error_eok": base_err,
                "parent_controlled_baseline_wape_pct": base_err / actual * 100,
                "phase161_error_eok": err,
                "phase161_wape_pct": err / actual * 100,
                "reduction_eok": base_err - err,
                "reduction_pp": base_err / actual * 100 - err / actual * 100,
                "baseline_gt20_cells": int((g["phase124_parent_controlled_error_rate_pct"] > 20).sum()),
                "phase161_gt20_cells": int((g["phase161_error_rate_pct"] > 20).sum()),
                "worsened_cells": int(
                    (g["phase161_error_gva_eok"] > g["phase124_parent_controlled_error_gva_eok"] + 1e-9).sum()
                ),
            }
        )
    city_summary = pd.DataFrame(city_rows)

    parent.to_csv(OUT / "phase161_parent_validation_gate.csv", index=False, encoding="utf-8-sig")
    gated_detail.to_csv(OUT / "phase161_peer_prior_gated_registry.csv", index=False, encoding="utf-8-sig")
    city_summary.to_csv(OUT / "phase161_city_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "phase": "phase161_peer_prior_validation_gate",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "inputs": {
                    "phase160_detail": str(P160_DETAIL.relative_to(ROOT)),
                    "phase160_parent": str(P160_PARENT.relative_to(ROOT)),
                },
                "important_limit": "The validation gate uses Goyang/Pohang actuals, so this is a diagnostic candidate filter, not a prospective operating rule.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    no_worse = parent[parent["validation_gate"].eq("진단상 무악화 개선")].copy()
    risky = parent[parent["validation_gate"].ne("진단상 무악화 개선") & parent["alpha"].gt(0)].copy()
    improved_cells = gated_detail[gated_detail["phase161_error_delta_vs_parent_controlled_eok"].lt(-1e-9)].copy()
    remaining = gated_detail[gated_detail["phase161_error_rate_pct"].gt(20)].copy()

    REPORT.write_text(
        f"""# Phase161 외부 업종구조 사전값의 검증 게이트

## 목적

Phase160은 외부 10개 시군구만으로 업종구조 사전값을 선택했지만, 고양·포항에 전체 적용하면 일부 상위산업에서 큰 악화가 생겼다. 이번 단계는 그 결과를 무리하게 성능으로 포장하지 않고, **악화 셀이 없는 개선 블록**과 **위험 블록**을 분리한다.

중요한 한계: 이 게이트는 고양·포항 actual을 보고 판정하므로 운영 규칙이 아니다. 다만 어떤 업종군에 추가 자료/사전값 방식이 실제로 먹히는지 확인하는 진단이다.

## 도시별 게이트 적용 결과

{md_table(city_summary.rename(columns={
    'city': '지역',
    'actual_sum_eok': '실제합계(억원)',
    'parent_controlled_baseline_error_eok': '정규화 기준오차(억원)',
    'parent_controlled_baseline_wape_pct': '정규화 기준 WAPE(%)',
    'phase161_error_eok': '게이트 후 오차(억원)',
    'phase161_wape_pct': '게이트 후 WAPE(%)',
    'reduction_eok': '감소(억원)',
    'reduction_pp': '감소 pp',
    'baseline_gt20_cells': '기준 20%초과',
    'phase161_gt20_cells': '게이트 후 20%초과',
    'worsened_cells': '악화 셀',
}), 2)}

## 악화 없는 개선 블록

{md_table(no_worse[[
    'city', 'parent_code', 'cells', 'alpha', 'actual_sum_eok',
    'phase124_parent_controlled_error_eok', 'phase124_parent_controlled_wape_pct',
    'phase160_error_eok', 'phase160_wape_pct', 'error_reduction_eok',
    'phase160_gt20_cells', 'validation_gate'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'cells': '중분류 수',
    'alpha': '혼합비',
    'actual_sum_eok': '실제합계(억원)',
    'phase124_parent_controlled_error_eok': '정규화 기준오차(억원)',
    'phase124_parent_controlled_wape_pct': '정규화 기준 WAPE(%)',
    'phase160_error_eok': '후보오차(억원)',
    'phase160_wape_pct': '후보 WAPE(%)',
    'error_reduction_eok': '감소(억원)',
    'phase160_gt20_cells': '20%초과',
    'validation_gate': '게이트',
}), 2)}

## 위험 블록

{md_table(risky[[
    'city', 'parent_code', 'cells', 'alpha', 'actual_sum_eok',
    'phase124_parent_controlled_error_eok', 'phase160_error_eok',
    'error_reduction_eok', 'worsened_cells', 'phase160_gt20_cells', 'validation_gate'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'cells': '중분류 수',
    'alpha': '혼합비',
    'actual_sum_eok': '실제합계(억원)',
    'phase124_parent_controlled_error_eok': '정규화 기준오차(억원)',
    'phase160_error_eok': '후보오차(억원)',
    'error_reduction_eok': '감소(억원)',
    'worsened_cells': '악화 셀',
    'phase160_gt20_cells': '20%초과',
    'validation_gate': '게이트',
}), 2, 30)}

## 개선 셀

{md_table(improved_cells.sort_values('phase161_error_delta_vs_parent_controlled_eok')[[
    'city', 'parent_code', 'middle_code', 'middle_label', 'actual_gva_eok',
    'phase124_parent_controlled_error_gva_eok', 'phase161_error_gva_eok',
    'phase161_error_rate_pct', 'phase161_error_delta_vs_parent_controlled_eok',
    'validation_gate'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'middle_code': '코드',
    'middle_label': '중분류',
    'actual_gva_eok': '실제(억원)',
    'phase124_parent_controlled_error_gva_eok': '기준오차(억원)',
    'phase161_error_gva_eok': '게이트 후 오차(억원)',
    'phase161_error_rate_pct': '게이트 후 오차(%)',
    'phase161_error_delta_vs_parent_controlled_eok': '오차변화(억원)',
    'validation_gate': '게이트',
}), 2, 20)}

## 남은 20% 초과 중분류

{md_table(remaining.sort_values(['city', 'phase161_error_gva_eok'], ascending=[True, False])[[
    'city', 'parent_code', 'middle_code', 'middle_label', 'actual_gva_eok',
    'phase161_predicted_gva_eok', 'phase161_error_gva_eok',
    'phase161_error_rate_pct', 'validation_gate'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'middle_code': '코드',
    'middle_label': '중분류',
    'actual_gva_eok': '실제(억원)',
    'phase161_predicted_gva_eok': '추정(억원)',
    'phase161_error_gva_eok': '오차(억원)',
    'phase161_error_rate_pct': '오차(%)',
    'validation_gate': '게이트',
}), 2, 40)}

## 판정

1. 외부 업종구조 사전값은 일부 업종군에는 강력하다. 특히 고양 K00과 포항 J00은 악화 셀 없이 큰 폭으로 줄었다.
2. 그러나 Q00, F00처럼 현재 이미 잘 맞는 블록에 외부 평균 구조를 강하게 주입하면 오히려 큰 악화가 생긴다.
3. 따라서 다음 운영형 개선은 `외부 평균 구조 일괄 적용`이 아니라, 도시 특성이 비슷한 peer를 고르는 기준 또는 블록별 악화방지 규칙이 필요하다.
4. 포스터나 제출자료에는 “외부 10개 기반으로 업종군별 사전값을 검증했고, 금융·정보통신 일부처럼 사업체수 기반 오차가 큰 영역에서 개선 가능성을 확인했다” 정도가 안전하다.
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
