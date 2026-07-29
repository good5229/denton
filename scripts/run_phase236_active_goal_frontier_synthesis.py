#!/usr/bin/env python3
"""Phase236: current active-goal frontier synthesis.

Summarize what is currently achieved, conditionally adopted, and still open
after Phase235. This prevents accidental overclaiming across levels.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "data" / "processed" / "phase236_active_goal_frontier_synthesis"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase236_active_goal_frontier_synthesis.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None, digits: int = 3) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("WAPE", "%", "pp", "셀", "개")) else "---" for _, label in cols) + " |")
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


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    industry = pd.read_csv(ROOT / "nationwide" / "outputs" / "active_goal_industry_operating_frontier.csv")
    region = pd.read_csv(ROOT / "nationwide" / "outputs" / "active_goal_region_activity_frontier.csv")
    sigungu = pd.read_csv(ROOT / "nationwide" / "outputs" / "active_goal_sigungu_remaining_activity_frontier.csv")
    construction_policy = pd.read_csv(
        ROOT
        / "data"
        / "processed"
        / "phase235_construction_bok_regional_gate"
        / "phase235_construction_bok_regional_gate_strict_policy_summary.csv"
    )

    achieved = pd.DataFrame(
        [
            {
                "level": "업종×운영시점 총괄",
                "target": "최대한 적은 산업군으로 업종 최대 WAPE≤10%",
                "status": "충족",
                "adopted_scope": "운수 및 창고업 1개 route",
                "evidence": "minimal_activity_hybrid Q1 업종최대 WAPE 9.581%, 10%초과 업종 0",
                "remaining": "광역시도/시군구 세부셀은 별도 검증 필요",
            },
            {
                "level": "광역시도×업종 운영시점",
                "target": "10% 초과 셀 축소 및 업종별 시간경로 개선",
                "status": "부분충족",
                "adopted_scope": "운수 및 창고업 전분기, 건설업 Q1/Q2 시간경로 제한 후보",
                "evidence": "운수 route 10%초과 셀 감소, Phase235 건설 Q1/Q2 pooled WAPE≤10",
                "remaining": "건설 Q1/Q2 2025 단년 WAPE>10, Q3/Q4 BOK 미채택",
            },
            {
                "level": "시군구×업종 연간",
                "target": "업종별 WAPE≤10%",
                "status": "미달",
                "adopted_scope": "운수 등 대부분 업종 상위총량 배분 가능",
                "evidence": "건설업 최선 WAPE 19.432%",
                "remaining": "건설업 시군구 공간배분 staged collection 필요",
            },
        ]
    )

    construction_policy = construction_policy.rename(
        columns={
            "available_quarters": "quarter_count",
            "baseline_wape_pct": "baseline_wape_pct",
            "selected_wape_pct": "selected_wape_pct",
            "delta_pp": "delta_pp",
            "baseline_over10": "baseline_over10",
            "selected_over10": "selected_over10",
            "policy_pass": "policy_pass",
        }
    )
    construction_policy["decision"] = construction_policy["quarter_count"].map(
        {
            1: "Q1 제한 채택 후보",
            2: "Q2 제한 채택 후보",
            3: "baseline 유지",
            4: "baseline 유지",
        }
    )

    remaining = sigungu.sort_values("wape_pct", ascending=False).head(8).copy()

    achieved.to_csv(OUTDIR / "phase236_goal_level_status.csv", index=False, encoding="utf-8-sig")
    construction_policy.to_csv(OUTDIR / "phase236_construction_time_policy.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase236_remaining_sigungu_bottlenecks.csv", index=False, encoding="utf-8-sig")

    minimal = industry[industry["scenario"].eq("minimal_activity_hybrid")].copy()
    transport = region[region["scenario"].eq("transport_only")].copy()

    report = f"""# Phase236 active goal frontier synthesis

생성시각: {CREATED_AT}

## 결론

- “전국 합산 WAPE”가 아니라 세 층으로 판단한다: 업종×운영시점, 광역시도×업종, 시군구×업종.
- 업종×운영시점 총괄은 운수 및 창고업 1개 route로 10% 이하 목표를 충족한다.
- 광역시도×업종에서는 운수 및 창고업 route가 안정적이고, 건설업은 Phase235 기준 Q1/Q2 시간경로에 한해 제한 채택 후보가 생겼다.
- 시군구×업종 연간에서는 건설업 WAPE 19.432%가 남아 전체 목표는 아직 미완료다.
- 따라서 현재 최소 산업군 전략은 `운수 및 창고업 채택 + 건설업 Q1/Q2 시간경로 제한 후보 + 건설업 시군구 공간배분 자료수집`이다.
- 현재 방식은 총량·광역시도 업종 모니터링에는 실용성이 있으나, 시군구×건설업처럼 위치성이 강한 업종은 추가 event 자료 기반 공간배분이 필요하다.

## 목표층별 상태

{md_table(achieved, [
    ("level", "검증층"),
    ("target", "목표"),
    ("status", "상태"),
    ("adopted_scope", "채택/후보 범위"),
    ("evidence", "근거"),
    ("remaining", "잔여"),
])}

## 업종×운영시점 총괄

{md_table(minimal, [
    ("available_quarters", "사용분기"),
    ("operating_label", "운영시점"),
    ("industry_max_wape_pct", "업종최대 WAPE_%"),
    ("over10_activity_groups", "10%초과 업종수"),
])}

## 광역시도×업종: 운수 route

{md_table(transport, [
    ("available_quarters", "사용분기"),
    ("routed_activity_count", "route 업종수"),
    ("routed_activities", "route 업종"),
    ("over10_cells", "10%초과 셀"),
    ("overall_region_activity_wape_pct", "전체 WAPE_%"),
])}

## 광역시도×건설업 시간경로: Phase235 엄격 정책

{md_table(construction_policy, [
    ("quarter_count", "사용분기"),
    ("adopted_cells", "BOK적용셀"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("selected_wape_pct", "선택 WAPE_%"),
    ("delta_pp", "변화 pp"),
    ("baseline_over10", "기준 10%초과"),
    ("selected_over10", "선택 10%초과"),
    ("max_baseline_ape_pct", "기준 최대APE_%"),
    ("max_selected_ape_pct", "선택 최대APE_%"),
    ("decision", "판정"),
])}

주의:

- 건설업 Phase235 route는 광역시도×건설업 시간경로에 한정한다.
- Q1/Q2 pooled WAPE는 10% 이하이나, 2025년 일부 단년 WAPE가 10%를 소폭 초과한다.
- Q3/Q4는 BOK gate를 운영 채택하지 않고 baseline을 유지한다.
- 시군구 공간배분 개선으로 해석하지 않는다.

## 시군구×업종 잔류 병목

{md_table(remaining, [
    ("activity", "업종"),
    ("wape_pct", "WAPE_%"),
    ("over10_cells", "10%초과 셀"),
    ("over20_cells", "20%초과 셀"),
    ("scenario", "최선 시나리오"),
], limit=8)}

## 다음 작업

1. 건설업 시군구 공간배분 자료수집: top1/top5→top28→top52 staged collection.
2. 민간건축, 정비사업, 공공·토목, fallback형 지역유형 gate 사전정의.
3. rolling out-of-year에서 WAPE, 10%/20% 초과 셀, 최대 APE, 대형 셀 절대오차 guardrail 동시 통과 여부 검증.
4. Q+1개월 속보성으로 표현하려면 건설수주 자료 공표시차 확인.

## 산출 파일

- `data/processed/phase236_active_goal_frontier_synthesis/phase236_goal_level_status.csv`
- `data/processed/phase236_active_goal_frontier_synthesis/phase236_construction_time_policy.csv`
- `data/processed/phase236_active_goal_frontier_synthesis/phase236_remaining_sigungu_bottlenecks.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR)


if __name__ == "__main__":
    main()
