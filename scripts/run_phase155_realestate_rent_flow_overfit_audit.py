#!/usr/bin/env python3
"""Phase155 audit for Phase154 rent-flow real-estate split.

The purpose is not to find another lower error.  It separates real modelling
evidence from two-city calibration and ex-post micro-search.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
P154 = DATA / "phase154_realestate_rent_flow_refinement"
OUT = DATA / "phase155_realestate_rent_flow_overfit_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase155_realestate_rent_flow_overfit_audit.md"


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy().where(pd.notna(df), "")
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if x == "" else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: f"{int(x):,}" if x != "" else "")
    view = view.astype(str).replace({"nan": "", "NaN": "", "None": ""})
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[col].replace("|", "\\|") for col in view.columns) + " |")
    return "\n".join(lines)


def risk_label(family: str, status: str) -> str:
    if "micro" in family:
        return "채택금지: 사후 미세탐색"
    if "two_city_calibrated" in family:
        return "보류: 2도시 보정"
    if "routed" in family:
        return "채택금지: 2도시 라우팅"
    if "stock_broker_saturation_common_k" in family:
        return "보류: 공통식이나 K 선택 검증 필요"
    if "diagnostic" in family:
        return "진단용"
    if "baseline" in family:
        return "기준"
    return "참고"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    overall = pd.read_csv(P154 / "phase154_realestate_rent_flow_overall.csv", encoding="utf-8-sig")
    city = pd.read_csv(P154 / "phase154_realestate_rent_flow_city_summary.csv", encoding="utf-8-sig")
    features = pd.read_csv(P154 / "phase154_realestate_rent_flow_features.csv", encoding="utf-8-sig")

    overall["audit_label"] = overall.apply(lambda r: risk_label(str(r["candidate_family"]), str(r["validation_status"])), axis=1)
    audit_rank = overall.sort_values(["max_city_wape_pct", "two_city_wape_pct"]).head(20).copy()

    conservative = overall[
        ~overall["candidate_family"].str.contains("micro|routed", na=False)
        & overall["all_cities_improved"].astype(bool)
    ].sort_values(["max_city_wape_pct", "two_city_wape_pct"]).head(15)

    city_best = city[city["candidate_family"].str.contains("rent_flow", na=False)].copy()
    city_best = city_best.sort_values(["city", "combined_wape_pct"]).groupby("city", as_index=False).head(1)
    cross_rows = []
    for row in city_best.itertuples(index=False):
        same_candidate = city[city["candidate"].eq(row.candidate)].copy()
        for r in same_candidate.itertuples(index=False):
            cross_rows.append(
                {
                    "선정도시": row.city,
                    "후보": row.candidate,
                    "평가도시": r.city,
                    "합산 WAPE(%)": r.combined_wape_pct,
                    "681 추정비중(%)": r.predicted_share_pct,
                    "681 실제비중(%)": r.actual_share_pct,
                    "검증상태": r.validation_status,
                }
            )
    cross = pd.DataFrame(cross_rows)

    contribution = pd.DataFrame(
        [
            {
                "항목": "자료 확장",
                "판정": "강함",
                "근거": "아파트·오피스텔·단독/다가구 전월세 238,705건을 확보해 아파트 편중을 줄임",
            },
            {
                "항목": "방향성",
                "판정": "강함",
                "근거": "전월세 면적밀도·계약단가가 681 비중 차이를 설명하는 신호로 작동",
            },
            {
                "항목": "성능수치",
                "판정": "보류",
                "근거": "10% 이내 후보는 2도시 미세탐색 결과라 외부 시군구 검증 전 채택 불가",
            },
            {
                "항목": "속보성",
                "판정": "보류",
                "근거": "행별 공표일자/확정일자 공개시점이 없어 Q+1개월 성능 주장 불가",
            },
        ]
    )

    audit_rank.to_csv(OUT / "phase155_candidate_risk_rank.csv", index=False, encoding="utf-8-sig")
    conservative.to_csv(OUT / "phase155_conservative_candidates.csv", index=False, encoding="utf-8-sig")
    cross.to_csv(OUT / "phase155_city_specific_candidate_crosscheck.csv", index=False, encoding="utf-8-sig")
    contribution.to_csv(OUT / "phase155_contribution_boundary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "phase": "phase155_realestate_rent_flow_overfit_audit",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "inputs": [
                    "phase154_realestate_rent_flow_overall.csv",
                    "phase154_realestate_rent_flow_city_summary.csv",
                    "phase154_realestate_rent_flow_features.csv",
                ],
                "outputs": [
                    "phase155_candidate_risk_rank.csv",
                    "phase155_conservative_candidates.csv",
                    "phase155_city_specific_candidate_crosscheck.csv",
                    "phase155_contribution_boundary.csv",
                    str(REPORT.relative_to(ROOT)),
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = f"""# Phase155 주거 전월세 부동산 소분류 개선 후보 사후적합 감사

## 목적

Phase154에서 주거 전월세 3종을 넣자 681/682 소분류 배분 오차가 크게 줄었다. 그러나 고양·포항 두 도시만으로 후보를 고른 결과이므로, 낮은 오차를 그대로 성능으로 주장하면 사후적합 위험이 있다. 이번 감사는 수치가 아니라 **채택 가능성의 경계**를 정한다.

## 후보 위험 등급 상위

{md_table(audit_rank[[
    'candidate', 'candidate_family', 'audit_label', 'two_city_wape_pct',
    'max_city_wape_pct', 'mean_share_error_pp', 'target_10pct_status'
]].rename(columns={
    'candidate': '후보',
    'candidate_family': '후보군',
    'audit_label': '감사판정',
    'two_city_wape_pct': '2도시 WAPE(%)',
    'max_city_wape_pct': '최대 도시 WAPE(%)',
    'mean_share_error_pp': '평균 681 비중오차(%p)',
    'target_10pct_status': '10% 목표'
}))}

## 보수적으로 볼 수 있는 후보

사후 미세탐색과 2도시 라우팅을 제외했다. 이 표의 후보도 아직 외부 시군구 검증 전에는 운영 채택안이 아니다.

{md_table(conservative[[
    'candidate', 'candidate_family', 'audit_label', 'two_city_wape_pct',
    'max_city_wape_pct', 'mean_share_error_pp', 'min_improvement_vs_current_pct',
]].rename(columns={
    'candidate': '후보',
    'candidate_family': '후보군',
    'audit_label': '감사판정',
    'two_city_wape_pct': '2도시 WAPE(%)',
    'max_city_wape_pct': '최대 도시 WAPE(%)',
    'mean_share_error_pp': '평균 681 비중오차(%p)',
    'min_improvement_vs_current_pct': '최소 현행개선율(%)',
}))}

## 도시별 최적 후보의 교차 확인

도시별 최적 후보가 서로 다르면 사후적합 위험이 커진다. 아래는 각 도시에서 가장 잘 맞은 후보를 다른 도시에도 그대로 적용했을 때의 결과다.

{md_table(cross)}

## 결론 경계

{md_table(contribution)}

## 판정

1. 주거 전월세 자료는 `681 부동산 임대 및 공급업` 배분 개선에 필요한 직접 활동자료다.
2. 다만 현재 10% 이내 결과는 대부분 사후 미세탐색 또는 2도시 보정 결과다. 포스터에는 “오차 4% 달성”처럼 쓰면 안 된다.
3. 안전하게 말할 수 있는 contribution은 “전월세 면적밀도·계약단가를 추가하면 기존 재고·중개업소 중심 배분보다 고양형 고밀도 임대시장과 포항형 저밀도 시장을 더 잘 구분한다”이다.
4. 다음 단계는 같은 전월세 3종을 임의 10개 시군구에 수집하고, K/보정강도를 고정한 뒤 외부지역에서 WAPE가 10% 전후로 유지되는지 확인하는 것이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    print(f"top_audit={audit_rank.iloc[0]['audit_label']} max_wape={audit_rank.iloc[0]['max_city_wape_pct']:.4f}")


if __name__ == "__main__":
    main()
