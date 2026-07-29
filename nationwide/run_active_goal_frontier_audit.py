#!/usr/bin/env python3
"""Summarize the active WAPE goal frontier across validation levels."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "nationwide" / "active_goal_wape_frontier.md"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ["WAPE", "%", "셀", "업종", "개", "행"]) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            v = row.get(key, "")
            if isinstance(v, (float, np.floating)):
                vals.append(f"{v:,.3f}")
            elif isinstance(v, (int, np.integer)):
                vals.append(f"{v:,}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    minimal = pd.read_csv(OUT / "minimal_activity_routing_sido_operating_summary.csv")
    sigungu = pd.read_csv(OUT / "minimal_activity_routing_sigungu_scenarios.csv")
    region = pd.read_csv(OUT / "region_level_minimal_routing_scenario_summary.csv")
    three = pd.read_csv(OUT / "three_activity_nationwide_recommended_policy.csv")
    construction_priority = pd.read_csv(OUT / "construction_buildinghub_collection_priority.csv")

    # 1) Industry x operating point max WAPE by scenario.
    ind_frontier = (
        minimal.groupby(["scenario", "available_quarters", "operating_label"], as_index=False)
        .agg(industry_max_wape_pct=("wape_pct", "max"), over10_activity_groups=("wape_pct", lambda s: int((s > 10).sum())))
        .sort_values(["available_quarters", "industry_max_wape_pct"])
    )
    ind_best = ind_frontier.groupby("available_quarters", as_index=False).head(2)

    # 2) Region x industry cell frontier.
    region_sorted = region.sort_values(["available_quarters", "over10_cells", "routed_activity_count", "overall_region_activity_wape_pct"])
    region_best = region_sorted.groupby("available_quarters", as_index=False).head(4)

    # 3) Sigungu x industry annual frontier.
    sigungu_sorted = sigungu.sort_values(["wape_pct", "over10_cells", "scenario"])
    sigungu_top = sigungu_sorted.groupby("activity", as_index=False).head(1).sort_values("wape_pct", ascending=False)
    sigungu_scenario = (
        sigungu.groupby("scenario", as_index=False)
        .agg(activity_max_wape_pct=("wape_pct", "max"), over10_activities=("wape_pct", lambda s: int((s > 10).sum())), cell_over10=("over10_cells", "sum"), cell_over20=("over20_cells", "sum"))
        .sort_values(["activity_max_wape_pct", "over10_activities"])
    )

    # 4) Recommended activity policy at sido level.
    policy = three[["activity", "available_quarters", "baseline_wape_pct", "selected_wape_pct", "baseline_over10_cells", "selected_over10_cells", "baseline_max_ape_pct", "selected_max_ape_pct", "recommended_action", "reason"]].copy()
    policy["delta_wape_pp"] = policy["selected_wape_pct"] - policy["baseline_wape_pct"]
    adopted_policy = policy[policy["recommended_action"].str.contains("채택", na=False)].copy()

    # 5) Construction collection burden.
    first50 = construction_priority[construction_priority["collection_priority"].eq("1차")].copy()
    burden = pd.DataFrame(
        [
            {
                "scope": "건설업 오차기여 50%",
                "cities": int(len(first50)),
                "legal_dong_requests": int(first50["active_legal_dong_requests"].sum()),
                "cum_error_share_pct": float(first50["cum_abs_error_share_pct"].max()),
            },
            {
                "scope": "건설업 오차기여 70%",
                "cities": int((construction_priority["cum_abs_error_share_pct"] <= 70).sum()),
                "legal_dong_requests": int(construction_priority.loc[construction_priority["cum_abs_error_share_pct"] <= 70, "active_legal_dong_requests"].sum()),
                "cum_error_share_pct": float(construction_priority.loc[construction_priority["cum_abs_error_share_pct"] <= 70, "cum_abs_error_share_pct"].max()),
            },
        ]
    )

    ind_best.to_csv(OUT / "active_goal_industry_operating_frontier.csv", index=False, encoding="utf-8-sig")
    region_best.to_csv(OUT / "active_goal_region_activity_frontier.csv", index=False, encoding="utf-8-sig")
    sigungu_scenario.to_csv(OUT / "active_goal_sigungu_scenario_frontier.csv", index=False, encoding="utf-8-sig")
    sigungu_top.to_csv(OUT / "active_goal_sigungu_remaining_activity_frontier.csv", index=False, encoding="utf-8-sig")
    adopted_policy.to_csv(OUT / "active_goal_adopted_sido_policy.csv", index=False, encoding="utf-8-sig")
    burden.to_csv(OUT / "active_goal_construction_collection_burden.csv", index=False, encoding="utf-8-sig")

    baseline_q1 = ind_frontier[(ind_frontier["scenario"].eq("strict_baseline")) & (ind_frontier["available_quarters"].eq(1))].iloc[0]
    minimal_q1 = ind_frontier[(ind_frontier["scenario"].eq("minimal_activity_hybrid")) & (ind_frontier["available_quarters"].eq(1))].iloc[0]
    sig_best = sigungu_scenario.iloc[0]

    report = [
        "# Active goal WAPE frontier audit",
        "",
        "## 결론",
        "",
        "- 목표를 전국 합산 하나로 보면 너무 느슨하므로, `업종×운영시점`, `광역시도×업종`, `시군구×업종` 세 층으로 분리한다.",
        f"- 업종×운영시점 총괄은 `운수 및 창고업` 1개 route로 Q1 최대 WAPE {baseline_q1.industry_max_wape_pct:.3f}% → {minimal_q1.industry_max_wape_pct:.3f}%가 되어 10% 이하에 들어온다.",
        "- 광역시도×업종 셀은 운수 route가 가장 안전하고, 건설·숙박·제조 일괄 route는 악화 사례가 있어 자동채택하지 않는다.",
        f"- 시군구×업종 연간은 최선 scenario에서도 업종 최대 WAPE {sig_best.activity_max_wape_pct:.3f}%로, 건설업 1개가 잔류한다.",
        "- 따라서 현재 goal frontier는 `운수 및 창고업 채택 + 건설업 staged data collection`이다.",
        "",
        "## 1. 업종×운영시점 총괄 frontier",
        "",
        md_table(ind_best, [("scenario", "시나리오"), ("available_quarters", "분기수"), ("operating_label", "운영시점"), ("industry_max_wape_pct", "업종최대 WAPE_%"), ("over10_activity_groups", "10%초과 업종수")]),
        "",
        "해석: `prior_year_anchor_all`은 전업종 직전연도 anchor를 쓰는 정밀화 참고 기준이다. 목표인 “최대한 적은 산업군” 기준의 운영 후보는 `minimal_activity_hybrid`, 즉 운수 및 창고업 1개 route다.",
        "",
        "## 2. 광역시도×업종 셀 frontier",
        "",
        md_table(region_best, [("scenario", "시나리오"), ("available_quarters", "분기수"), ("routed_activity_count", "route 업종수"), ("routed_activities", "route 업종"), ("over10_cells", "10%초과 셀"), ("overall_region_activity_wape_pct", "전체 WAPE_%")], 20),
        "",
        "## 3. 시군구×업종 연간 scenario frontier",
        "",
        md_table(sigungu_scenario, [("scenario", "시나리오"), ("activity_max_wape_pct", "업종최대 WAPE_%"), ("over10_activities", "10%초과 업종수"), ("cell_over10", "셀 10%초과"), ("cell_over20", "셀 20%초과")]),
        "",
        "## 4. 시군구 잔류 업종",
        "",
        md_table(sigungu_top, [("activity", "업종"), ("scenario", "최선 시나리오"), ("wape_pct", "WAPE_%"), ("over10_cells", "10%초과 셀"), ("over20_cells", "20%초과 셀")], 12),
        "",
        "## 5. 현재 채택 가능한 시도 시간경로 policy",
        "",
        md_table(adopted_policy, [("activity", "업종"), ("available_quarters", "분기수"), ("baseline_wape_pct", "기준 WAPE_%"), ("selected_wape_pct", "선택 WAPE_%"), ("delta_wape_pp", "변화 pp"), ("baseline_over10_cells", "기준10%셀"), ("selected_over10_cells", "선택10%셀"), ("recommended_action", "권고")]),
        "",
        "## 6. 건설업 staged collection 부담",
        "",
        md_table(burden, [("scope", "범위"), ("cities", "시군구 개"), ("legal_dong_requests", "법정동 요청 개"), ("cum_error_share_pct", "누적오차기여_%")]),
        "",
        "## 평가관/과학자 반영",
        "",
        "- 과학자: 전량 수집 전 오차 집중 시군구와 건축활동 방향성을 먼저 보라는 제안을 반영했다.",
        "- 평가관: 2023 상위오차 표본은 탐색 표본이며, 채택 평가는 rolling out-of-year로 해야 한다는 조건을 반영했다.",
        "- 현재 외부 API 수집은 세션 사용량 제한으로 실행하지 못했으므로, 건설업 route 채택은 아직 보류다.",
        "",
        "## 다음 실행 명령",
        "",
        "```bash",
        ".venv/bin/python nationwide/collect_buildinghub_priority_events.py \\",
        "  --limit-cities 1 --priority-stage 1차 \\",
        "  --output-tag construction_priority_top1_pyeongtaek",
        "```",
        "",
        "그 다음 top1 event를 이용해 `기존 share + 착공/사용승인 면적 share + PPS 금액 share` 후보를 rolling 검증한다.",
    ]
    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(REPORT)
    print(OUT / "active_goal_sigungu_scenario_frontier.csv")


if __name__ == "__main__":
    main()
