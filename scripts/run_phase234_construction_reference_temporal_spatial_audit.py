#!/usr/bin/env python3
"""Phase234: audit BOK-style construction timing vs spatial block routes.

The goal is to keep the construction conclusion honest:

* BOK-style 12/24 quarter dispersion is useful for province-level timing.
* It does not solve sigungu-level construction spatial allocation.
* Building/PPS/redevelopment data should be treated as spatial block candidates
  until rolling guardrails pass.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NATION = ROOT / "nationwide"
OUTDIR = ROOT / "data" / "processed" / "phase234_construction_reference_temporal_spatial_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase234_construction_reference_temporal_spatial_audit.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None, digits: int = 3) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    aligns = []
    for _, label in cols:
        aligns.append("---:" if any(t in label for t in ("WAPE", "pp", "억원", "개", "%", "분기")) else "---")
    lines.append("| " + " | ".join(aligns) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            v = row.get(key, "")
            if pd.isna(v):
                vals.append("")
            elif isinstance(v, (float, np.floating)):
                vals.append(f"{float(v):,.{digits}f}")
            elif isinstance(v, (int, np.integer)):
                vals.append(f"{int(v):,}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    summary_path = NATION / "outputs" / "hard_region_indicator_route_candidate_summary.csv"
    detail_path = NATION / "outputs" / "region_level_indicator_candidate_detail.csv"
    registry_path = ROOT / "data" / "processed" / "phase231_construction_route_decision_registry" / "phase231_construction_route_decision_registry.csv"
    frontier_path = NATION / "outputs" / "construction_wape_reduction_thresholds.csv"

    summary = read_csv(summary_path)
    detail = read_csv(detail_path)
    registry = read_csv(registry_path)
    frontier = read_csv(frontier_path)

    construction_summary = summary[summary["activity"].eq("건설업")].copy()
    construction_summary["route_label"] = construction_summary["route_id"].map(
        {
            "regional_construction_orders_bok_12_24q": "BOK식 건축12·토목24분기 분산",
            "regional_construction_orders_raw": "당기 건설수주 원자료",
        }
    ).fillna(construction_summary["route_id"])
    construction_summary["track_label"] = construction_summary["track"].map(
        {
            "recursive_no_target_actual": "target-year actual 미사용 재귀기준",
            "prior_year_province_anchor": "전년도 시도 anchor 기준",
        }
    ).fillna(construction_summary["track"])

    bok = construction_summary[construction_summary["route_id"].eq("regional_construction_orders_bok_12_24q")].copy()
    raw = construction_summary[construction_summary["route_id"].eq("regional_construction_orders_raw")].copy()

    # Pivot for direct raw-vs-BOK comparison.
    cmp = bok.merge(
        raw[
            [
                "track",
                "available_quarters",
                "candidate_wape_pct",
                "delta_wape_pp",
                "candidate_abs_error_sum_eok",
            ]
        ],
        on=["track", "available_quarters"],
        suffixes=("_bok", "_raw"),
    )
    cmp["raw_minus_bok_wape_pp"] = cmp["candidate_wape_pct_raw"] - cmp["candidate_wape_pct_bok"]
    cmp["raw_to_bok_abs_error_reduction_eok"] = (
        cmp["candidate_abs_error_sum_eok_raw"] - cmp["candidate_abs_error_sum_eok_bok"]
    )
    cmp["bok_beats_raw"] = cmp["candidate_wape_pct_bok"] < cmp["candidate_wape_pct_raw"]
    cmp = cmp.rename(
        columns={
            "candidate_wape_pct_bok": "bok_wape_pct",
            "candidate_wape_pct_raw": "raw_wape_pct",
            "delta_wape_pp_bok": "bok_vs_baseline_delta_pp",
            "delta_wape_pp_raw": "raw_vs_baseline_delta_pp",
        }
    )
    cmp["track_label"] = cmp["track"].map(
        {
            "recursive_no_target_actual": "target-year actual 미사용 재귀기준",
            "prior_year_province_anchor": "전년도 시도 anchor 기준",
        }
    )

    # Region-year guardrail for the recursively valid track, because that is
    # closest to the user's no-target-actual forecasting requirement.
    d = detail[
        detail["activity"].eq("건설업")
        & detail["route_id"].eq("regional_construction_orders_bok_12_24q")
        & detail["year"].between(2021, 2025)
    ].copy()
    d["candidate_better"] = d["candidate_abs_error_eok"] < d["baseline_abs_error_eok"]
    d["candidate_over10"] = d["candidate_ape_pct"] > 10
    d["baseline_over10"] = d["baseline_ape_pct"] > 10
    by_q = (
        d.groupby("available_quarters", as_index=False)
        .agg(
            rows=("candidate_abs_error_eok", "size"),
            official_sum_eok=("official_annual_eok", "sum"),
            baseline_abs_error_eok=("baseline_abs_error_eok", "sum"),
            candidate_abs_error_eok=("candidate_abs_error_eok", "sum"),
            improved_rows=("candidate_better", "sum"),
            baseline_over10=("baseline_over10", "sum"),
            candidate_over10=("candidate_over10", "sum"),
            max_candidate_ape_pct=("candidate_ape_pct", "max"),
            max_baseline_ape_pct=("baseline_ape_pct", "max"),
        )
    )
    by_q["baseline_wape_pct"] = by_q["baseline_abs_error_eok"] / by_q["official_sum_eok"] * 100
    by_q["candidate_wape_pct"] = by_q["candidate_abs_error_eok"] / by_q["official_sum_eok"] * 100
    by_q["delta_wape_pp"] = by_q["candidate_wape_pct"] - by_q["baseline_wape_pct"]
    by_q["adopt_timing_route"] = (
        (by_q["candidate_wape_pct"] <= 10)
        & (by_q["candidate_wape_pct"] < by_q["baseline_wape_pct"])
        & (by_q["candidate_over10"] <= by_q["baseline_over10"])
    )

    # Weakness map: where BOK timing still fails badly.
    weak = d[d["candidate_ape_pct"] > 10].copy()
    weak = weak.sort_values(["candidate_ape_pct"], ascending=False)[
        [
            "quarter_region",
            "year",
            "available_quarters",
            "official_annual_eok",
            "candidate_predicted_eok",
            "candidate_ape_pct",
            "baseline_ape_pct",
        ]
    ].head(20)

    # Phase231 route classification, simplified.
    route_registry = registry[
        [
            "route_id",
            "route_layer",
            "signal_family",
            "scope",
            "baseline_wape_pct",
            "candidate_wape_pct",
            "guardrail_pass",
            "decision",
            "adoption_level",
            "reason",
        ]
    ].copy()

    # Frontier threshold for spatial problem.
    threshold = frontier.copy()
    if "assumed_reduction_pct" in threshold.columns:
        threshold75 = threshold[threshold["assumed_reduction_pct"].eq(75)].head(12)
    else:
        threshold75 = threshold.head(12)

    cmp.to_csv(OUTDIR / "phase234_raw_vs_bok_timing_comparison.csv", index=False, encoding="utf-8-sig")
    by_q.to_csv(OUTDIR / "phase234_bok_timing_guardrail_by_quarter.csv", index=False, encoding="utf-8-sig")
    weak.to_csv(OUTDIR / "phase234_bok_timing_remaining_weak_cells.csv", index=False, encoding="utf-8-sig")
    route_registry.to_csv(OUTDIR / "phase234_construction_route_registry_excerpt.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase234 건설업 reference 시간분산 및 공간 route 분리 감사

생성시각: {CREATED_AT}

## 결론

- BOK reference의 건축 12분기·토목 24분기 분산은 건설업의 **시간경로 후보**로 타당하다.
- 당기 건설수주 원자료를 그대로 쓰면 WAPE가 크게 악화되지만, 12/24분기 분산은 원자료 대비 모든 운영시점에서 훨씬 안정적이다.
- 단, 전체 광역시도×건설업 guardrail에서는 기준보다 악화되는 셀이 남아 있어 **전국 공통 시간route로 즉시 채택하지 않는다**.
- 현재 채택 가능한 표현은 “취약 광역시도·특정 운영기준에서 유망한 후보”이며, “전국 건설업 성능개선 완료”가 아니다.
- 본 단계의 건설업 결과는 운영 route 채택이 아니라 후보 검증이다. 실제 채택은 지역유형별 rolling out-of-year 검증에서 WAPE, 10% 초과 셀, 20% 초과 셀, 최대 APE가 모두 기준선보다 악화되지 않을 때로 제한한다.
- 다만 이 결과는 **시군구 공간배분 성능**이 아니다.
- 시군구×건설업 병목은 건축HUB·재건축/재개발·PPS·토목사업 자료를 지역유형별로 결합해야 하며, Phase231 기준 현재 운영 채택 route는 없다.

## 1. 취약 광역시도 후보표: 건설수주 원자료 vs BOK식 시간분산

{md_table(cmp.sort_values(["track_label", "available_quarters"]), [
    ("track_label", "검증기준"),
    ("available_quarters", "사용 분기"),
    ("raw_wape_pct", "원자료 WAPE_%"),
    ("bok_wape_pct", "12/24분산 WAPE_%"),
    ("raw_minus_bok_wape_pp", "원자료-분산 pp"),
    ("bok_vs_baseline_delta_pp", "분산 vs 기준 pp"),
    ("bok_beats_raw", "분산이 원자료보다 양호"),
])}

해석:

- `당기 건설수주 원자료`는 수주와 생산 발생 시점이 어긋나기 때문에 건설업 GVA 시간경로로 부적합하다.
- `BOK식 건축12·토목24분기 분산`은 원자료 대비 모든 운영시점에서 크게 안정적이다.
- 취약 광역시도 후보표의 target-year actual 미사용 재귀기준에서는 Q1부터 Q4까지 모두 기준보다 개선되며, Q2 이후 10% 이하에 들어온다.
- 전년도 시도 anchor 기준은 이미 강한 기준이라 Q4에서만 소폭 개선된다.
- 따라서 이 표는 “BOK식 분산이 시간경로 후보로 볼 가치가 있다”는 근거이지, 전체 광역시도 채택 근거는 아니다.

## 2. 전체 광역시도 상세 guardrail

{md_table(by_q, [
    ("available_quarters", "사용 분기"),
    ("rows", "검증 셀"),
    ("official_sum_eok", "실제합_억원"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("candidate_wape_pct", "분산 WAPE_%"),
    ("delta_wape_pp", "변화 pp"),
    ("baseline_over10", "기준 10%초과"),
    ("candidate_over10", "분산 10%초과"),
    ("max_baseline_ape_pct", "기준 최대APE_%"),
    ("max_candidate_ape_pct", "분산 최대APE_%"),
    ("adopt_timing_route", "시간route 채택"),
])}

판정:

- 전체 광역시도×건설업 시간경로 route로는 `BOK식 건축12·토목24분기 분산`을 즉시 채택하지 않는다.
- 기준 WAPE가 이미 낮은 지역까지 모두 포함하면, BOK식 분산이 기준보다 WAPE·10% 초과 셀을 악화시키는 경우가 있다.
- 단, 공간배분 route와 혼동하지 않는다.
- 따라서 다음 실험은 모든 지역에 일괄 적용하는 방식이 아니라, 건설수주 시간분산이 과거 rolling에서 유효했던 지역에만 적용하는 지역 gate 방식이어야 한다.

## 3. 시간분산으로도 남는 취약 셀

{md_table(weak, [
    ("quarter_region", "시도"),
    ("year", "연도"),
    ("available_quarters", "사용 분기"),
    ("official_annual_eok", "실제_억원"),
    ("candidate_predicted_eok", "분산추정_억원"),
    ("candidate_ape_pct", "분산 APE_%"),
    ("baseline_ape_pct", "기준 APE_%"),
], limit=20)}

해석:

- BOK식 시간분산도 지역별 건설경기 전환점이나 대형 프로젝트 충격은 완전히 잡지 못한다.
- 이 잔차가 바로 건축물·정비사업·PPS·토목사업 event 자료가 필요한 이유다.

## 4. 공간 route 판정 요약

{md_table(route_registry, [
    ("route_id", "route"),
    ("route_layer", "층위"),
    ("signal_family", "자료군"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("candidate_wape_pct", "후보 WAPE_%"),
    ("guardrail_pass", "guardrail"),
    ("decision", "판정"),
    ("adoption_level", "채택수준"),
    ("reason", "사유"),
], limit=20)}

판정:

- 건축HUB는 민간건축·세부구조 보조자료다.
- 재건축/재개발은 대형 주거정비사업 보조자료로 추가 수집 필요하다.
- PPS는 공공·토목형 지역에서만 보조자료다.
- 이 셋을 하나의 지표로 합치지 않고, 지역유형 gate별 제한혼합으로 검증한다.

## 5. 다음 실험

1. `BOK식 건축12·토목24분기 분산`은 광역시도×건설업 시간경로 후보로 유지한다.
2. 광역시도 시간route도 전체 일괄 적용하지 않고, rolling 검증에서 유효한 지역에만 적용한다.
3. 시군구 공간배분은 top1/top5 오차지역부터 건축HUB·정비사업·PPS 자료를 수집한다.
4. 지역유형을 사전분류한다: 민간건축형, 정비사업형, 공공·토목형, 혼합형, fallback형.
5. 각 유형별로 허용자료를 제한한다.
6. rolling out-of-year로 WAPE, 10%/20% 초과 셀, 최대 APE, 대형 셀 절대오차 guardrail을 동시에 통과할 때만 채택한다.

## 산출 파일

- `data/processed/phase234_construction_reference_temporal_spatial_audit/phase234_raw_vs_bok_timing_comparison.csv`
- `data/processed/phase234_construction_reference_temporal_spatial_audit/phase234_bok_timing_guardrail_by_quarter.csv`
- `data/processed/phase234_construction_reference_temporal_spatial_audit/phase234_bok_timing_remaining_weak_cells.csv`
- `data/processed/phase234_construction_reference_temporal_spatial_audit/phase234_construction_route_registry_excerpt.csv`
"""

    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR)


if __name__ == "__main__":
    main()
