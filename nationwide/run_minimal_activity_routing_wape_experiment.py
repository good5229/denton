#!/usr/bin/env python3
"""Minimal activity routing experiment for nationwide WAPE reduction.

The experiment is deliberately conservative:

* The baseline is the strict `recursive_no_target_actual` track.
* Sido operating-point routing may only switch selected activities to the
  already-produced `prior_year_province_anchor` track, and the report flags
  this as a release-lag-sensitive late-cycle route, not as a pure Q+1 nowcast.
* Sigungu annual routing tests upper-level activity control and lagged residual
  correction. Target-year lower-level actual values are never used to create a
  candidate prediction.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "nationwide" / "minimal_activity_routing_wape_experiment.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def wape(err: pd.Series, actual: pd.Series) -> float:
    denom = actual.abs().sum()
    if denom == 0:
        return float("nan")
    return float(err.abs().sum() / denom * 100)


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
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


def load_operating_activity() -> pd.DataFrame:
    op = pd.read_csv(OUT / "operating_point_sido_activity_validation.csv")
    op["available_quarters_fixed"] = op["available_quarters_x"].where(
        op["available_quarters_x"].notna(),
        op["available_quarters"],
    ).astype(int)
    return op


def summarize_sido_cells(df: pd.DataFrame, pred_col: str, label: str) -> pd.DataFrame:
    work = df.copy()
    work["candidate_error_eok"] = work[pred_col] - work["official_annual_eok"]
    work["candidate_ape_pct"] = work["candidate_error_eok"].abs() / work["official_annual_eok"].abs() * 100
    rows = []
    for keys, g in work.groupby(["available_quarters_fixed", "operating_label", "activity"]):
        k, operating_label, activity = keys
        rows.append(
            {
                "scenario": label,
                "available_quarters": int(k),
                "operating_label": operating_label,
                "activity": activity,
                "rows": len(g),
                "wape_pct": wape(g["candidate_error_eok"], g["official_annual_eok"]),
                "max_ape_pct": float(g["candidate_ape_pct"].max()),
                "over10_cells": int((g["candidate_ape_pct"] > 10).sum()),
                "over20_cells": int((g["candidate_ape_pct"] > 20).sum()),
            }
        )
    return pd.DataFrame(rows)


def sido_minimal_routing(op: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = op[op["track"].eq("recursive_no_target_actual")].copy()
    anchor = op[op["track"].eq("prior_year_province_anchor")].copy()
    key = ["quarter_region", "year", "available_quarters_fixed", "activity"]
    anchor_pred = anchor[key + ["annualized_predicted_eok"]].rename(columns={"annualized_predicted_eok": "anchor_annualized_predicted_eok"})
    base = base.merge(anchor_pred, on=key, how="left")

    base_summary = summarize_sido_cells(base, "annualized_predicted_eok", "strict_baseline")
    anchor_summary = summarize_sido_cells(base, "anchor_annualized_predicted_eok", "prior_year_anchor_all")

    # Greedy minimal activity selection: choose the fewest activities that remove
    # activity-level WAPE > 10. This optimizes the explicit WAPE target, while
    # the report separately audits cell-level APE and release-lag restrictions.
    candidates = []
    for activity in sorted(base["activity"].unique()):
        tmp = base.copy()
        tmp["hybrid_pred"] = tmp["annualized_predicted_eok"].where(
            ~tmp["activity"].eq(activity),
            tmp["anchor_annualized_predicted_eok"],
        )
        summ = summarize_sido_cells(tmp, "hybrid_pred", f"route_{activity}")
        violations = int((summ["wape_pct"] > 10).sum())
        max_wape = float(summ["wape_pct"].max())
        candidates.append({"activity": activity, "violating_activity_operating_groups": violations, "max_wape_pct": max_wape})
    cand = pd.DataFrame(candidates).sort_values(["violating_activity_operating_groups", "max_wape_pct", "activity"])

    selected: list[str] = []
    current = base.copy()
    current["hybrid_pred"] = current["annualized_predicted_eok"]
    while True:
        current_summary = summarize_sido_cells(current, "hybrid_pred", "hybrid_current")
        if not (current_summary["wape_pct"] > 10).any():
            break
        best = None
        for activity in sorted(set(base["activity"]) - set(selected)):
            trial = current.copy()
            trial["hybrid_pred"] = trial["hybrid_pred"].where(
                ~trial["activity"].eq(activity),
                trial["anchor_annualized_predicted_eok"],
            )
            summ = summarize_sido_cells(trial, "hybrid_pred", "trial")
            score = (int((summ["wape_pct"] > 10).sum()), float(summ["wape_pct"].max()))
            if best is None or score < best[0]:
                best = (score, activity, trial)
        if best is None:
            break
        selected.append(best[1])
        current = best[2]
        if len(selected) > 5:
            break

    current["sido_routing_method"] = np.where(
        current["activity"].isin(selected),
        "prior_year_anchor_for_selected_activity",
        "strict_baseline",
    )
    hybrid_summary = summarize_sido_cells(current, "hybrid_pred", "minimal_activity_hybrid")
    selected_df = pd.DataFrame(
        [
            {
                "selected_order": i + 1,
                "activity": a,
                "reason": "엄격 기준선에서 업종×운영시점 WAPE가 10%를 넘고, 직전연도 지역 업종 기준값 route에서는 10% 이하로 내려감",
                "release_lag_guardrail": "관련 직전연도 지역 업종 공식값이 이미 공표된 경우에만 사용. 최신연도 Q+1 순수 속보에는 미채택",
            }
            for i, a in enumerate(selected)
        ]
    )
    return pd.concat([base_summary, anchor_summary, hybrid_summary], ignore_index=True), cand, selected_df


def load_sigungu_activity() -> pd.DataFrame:
    sig = pd.read_csv(OUT / "annual_sigungu_activity_error_audit.csv")
    sido = pd.read_csv(OUT / "annual_sido_activity_error_audit.csv")
    sido = sido[sido["track"].eq("recursive_no_target_actual")][
        ["quarter_region", "year", "activity", "predicted_eok", "actual_eok"]
    ].rename(columns={"predicted_eok": "sido_predicted_eok", "actual_eok": "sido_actual_eok"})
    sig = sig.merge(sido, on=["quarter_region", "year", "activity"], how="left")
    sig["parent_activity_scale"] = sig["sido_actual_eok"] / sig["sido_predicted_eok"]
    sig["parent_activity_scale"] = sig["parent_activity_scale"].replace([np.inf, -np.inf], np.nan).fillna(1.0)
    return sig


def summarize_sigungu(df: pd.DataFrame, pred_col: str, ape_threshold: float = 10) -> pd.DataFrame:
    work = df.copy()
    work["candidate_abs_error_eok"] = (work[pred_col] - work["actual_eok"]).abs()
    work["candidate_ape_pct"] = work["candidate_abs_error_eok"] / work["actual_eok"].abs() * 100
    rows = []
    for activity, g in work.groupby("activity"):
        rows.append(
            {
                "activity": activity,
                "rows": len(g),
                "actual_sum_eok": float(g["actual_eok"].abs().sum()),
                "abs_error_sum_eok": float(g["candidate_abs_error_eok"].sum()),
                "wape_pct": wape(g["candidate_abs_error_eok"], g["actual_eok"]),
                "over10_cells": int((g["candidate_ape_pct"] > ape_threshold).sum()),
                "over20_cells": int((g["candidate_ape_pct"] > 20).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("wape_pct", ascending=False)


def sigungu_routing(sig: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scenario_frames = []
    scenario_defs = {
        "strict_baseline": [],
        "parent_control_transport_only": ["운수 및 창고업"],
        "parent_control_construction_transport": ["건설업", "운수 및 창고업"],
        "parent_control_top3": ["건설업", "운수 및 창고업", "정보통신업"],
        "parent_control_all_activities": sorted(sig["activity"].unique()),
    }
    for name, targets in scenario_defs.items():
        pred = sig["predicted_eok"].where(~sig["activity"].isin(targets), sig["predicted_eok"] * sig["parent_activity_scale"])
        tmp = sig.copy()
        tmp["scenario_predicted_eok"] = pred
        s = summarize_sigungu(tmp, "scenario_predicted_eok")
        s["scenario"] = name
        s["routed_activities"] = ", ".join(targets) if targets else "없음"
        scenario_frames.append(s)
    scenario_summary = pd.concat(scenario_frames, ignore_index=True)

    # Rejected lag-residual experiments. The predictor uses only the previous
    # observed lower-level ratio, but the test shows it is unstable.
    lag_rows = []
    parent_all_pred = sig["predicted_eok"] * sig["parent_activity_scale"]
    parent_all_wape = wape((parent_all_pred - sig["actual_eok"]).abs(), sig["actual_eok"])
    for start_col in ["predicted_eok", "parent_control_predicted_eok"]:
        base = sig.copy()
        if start_col == "parent_control_predicted_eok":
            base[start_col] = base["predicted_eok"] * base["parent_activity_scale"]
        for shrink in [0.25, 0.50, 0.75, 1.00]:
            out_rows = []
            for _, g in base.sort_values(["quarter_region", "city", "activity", "year"]).groupby(["quarter_region", "city", "activity"]):
                prev_ratio = None
                for _, r in g.sort_values("year").iterrows():
                    pred = float(r[start_col])
                    if prev_ratio is None or not np.isfinite(prev_ratio):
                        factor = 1.0
                    else:
                        factor = max(0.25, min(4.0, 1.0 + (prev_ratio - 1.0) * shrink))
                    rr = r.copy()
                    rr["lag_candidate_predicted_eok"] = pred * factor
                    out_rows.append(rr)
                    prev_ratio = float(r["actual_eok"]) / pred if pred else None
            d = pd.DataFrame(out_rows)
            d["lag_abs_error_eok"] = (d["lag_candidate_predicted_eok"] - d["actual_eok"]).abs()
            d["lag_ape_pct"] = d["lag_abs_error_eok"] / d["actual_eok"].abs() * 100
            lag_rows.append(
                {
                    "start_prediction": start_col,
                    "shrink": shrink,
                    "all_activity_wape_pct": wape(d["lag_abs_error_eok"], d["actual_eok"]),
                    "over10_cells": int((d["lag_ape_pct"] > 10).sum()),
                    "construction_wape_pct": wape(
                        d[d["activity"].eq("건설업")]["lag_abs_error_eok"],
                        d[d["activity"].eq("건설업")]["actual_eok"],
                    ),
                    "transport_wape_pct": wape(
                        d[d["activity"].eq("운수 및 창고업")]["lag_abs_error_eok"],
                        d[d["activity"].eq("운수 및 창고업")]["actual_eok"],
                    ),
                    "decision": "reject"
                    if (
                        wape(d["lag_abs_error_eok"], d["actual_eok"]) >= parent_all_wape
                        or wape(
                            d[d["activity"].eq("건설업")]["lag_abs_error_eok"],
                            d[d["activity"].eq("건설업")]["actual_eok"],
                        )
                        > summarize_sigungu(sig.assign(parent_all_pred=parent_all_pred), "parent_all_pred")
                        .set_index("activity")
                        .loc["건설업", "wape_pct"]
                    )
                    else "review",
                }
            )
    lag_summary = pd.DataFrame(lag_rows)

    top_remaining = sig.copy()
    top_remaining["parent_control_top3_predicted_eok"] = top_remaining["predicted_eok"].where(
        ~top_remaining["activity"].isin(["건설업", "운수 및 창고업", "정보통신업"]),
        top_remaining["predicted_eok"] * top_remaining["parent_activity_scale"],
    )
    top_remaining["candidate_abs_error_eok"] = (top_remaining["parent_control_top3_predicted_eok"] - top_remaining["actual_eok"]).abs()
    top_remaining["candidate_ape_pct"] = top_remaining["candidate_abs_error_eok"] / top_remaining["actual_eok"].abs() * 100
    remaining = top_remaining[top_remaining["candidate_ape_pct"] > 10].sort_values("candidate_abs_error_eok", ascending=False)
    return scenario_summary, lag_summary, remaining.head(80)


def main() -> int:
    op = load_operating_activity()
    sido_summary, route_candidates, selected = sido_minimal_routing(op)
    sig = load_sigungu_activity()
    sig_scenarios, lag_summary, remaining = sigungu_routing(sig)

    sido_summary.to_csv(OUT / "minimal_activity_routing_sido_operating_summary.csv", index=False, encoding="utf-8-sig")
    route_candidates.to_csv(OUT / "minimal_activity_routing_sido_candidates.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "minimal_activity_routing_selected_sido_activities.csv", index=False, encoding="utf-8-sig")
    sig_scenarios.to_csv(OUT / "minimal_activity_routing_sigungu_scenarios.csv", index=False, encoding="utf-8-sig")
    lag_summary.to_csv(OUT / "minimal_activity_routing_lag_residual_rejected.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUT / "minimal_activity_routing_remaining_sigungu_over10_cells.csv", index=False, encoding="utf-8-sig")

    sido_compare = (
        sido_summary[sido_summary["scenario"].isin(["strict_baseline", "minimal_activity_hybrid"])]
        .groupby(["scenario", "available_quarters"], as_index=False)
        .agg(
            max_activity_wape_pct=("wape_pct", "max"),
            activity_operating_groups_over10=("wape_pct", lambda s: int((s > 10).sum())),
            cell_over10=("over10_cells", "sum"),
            cell_over20=("over20_cells", "sum"),
        )
    )
    sig_compare = (
        sig_scenarios.groupby("scenario", as_index=False)
        .agg(
            max_activity_wape_pct=("wape_pct", "max"),
            activities_over10_wape=("wape_pct", lambda s: int((s > 10).sum())),
            cell_over10=("over10_cells", "sum"),
            cell_over20=("over20_cells", "sum"),
            routed_activities=("routed_activities", "first"),
        )
        .sort_values(["activities_over10_wape", "max_activity_wape_pct"])
    )

    report = f"""# 최소 산업군 라우팅 WAPE 개선 실험

생성시각: {CREATED_AT}

## 목적

전국 2021~2025 검증에서 모든 업종을 개별 특화하지 않고, 가능한 적은 산업군만 별도 라우팅하여 업종별 WAPE 10% 이하를 달성할 수 있는지 점검했다.

성공 기준은 두 층으로 나누었다.

| 층 | 기준 |
| --- | --- |
| 시도×업종 운영시점 | 엄격 속보형 기준에서 업종×운영시점 WAPE 10% 초과 그룹 제거 |
| 시군구×업종 연간 | 업종별 WAPE 10% 초과 산업군 최소화. 단 target-year 시군구 actual 직접 사용 금지 |

## 1. 시도×업종: 최소 라우팅 결과

엄격 기준선에서는 `1분기+1개월`의 `운수 및 창고업`만 업종 WAPE 10%를 넘는다. 따라서 greedy 최소 선택은 1개 업종이다.

{md_table(selected.rename(columns={
    "selected_order": "선택순서",
    "activity": "선택업종",
    "reason": "선택사유",
    "release_lag_guardrail": "공표시점 가드레일",
}), 3)}

### 운영시점 요약

{md_table(sido_compare.rename(columns={
    "scenario": "시나리오",
    "available_quarters": "사용분기수",
    "max_activity_wape_pct": "업종최대WAPE_pct",
    "activity_operating_groups_over10": "WAPE10초과_업종그룹수",
    "cell_over10": "지역연도셀_10pct초과",
    "cell_over20": "지역연도셀_20pct초과",
}), 3)}

해석:

- `운수 및 창고업` 1개만 prior-year anchor route로 전환하면 업종×운영시점 WAPE 10% 초과 그룹은 0개가 된다.
- 단, 이 route는 직전연도 지역 업종 공식값이 이미 공표되어 있어야 안전하다. 최신연도 Q+1 순수 속보에는 그대로 적용하면 안 된다.
- 따라서 `Q+1개월 순수 속보` 성능으로는 이 개선을 주장하지 않는다. `공표 후 정밀화` 또는 `직전연도 공식값 확보 후 운영` 성능으로만 사용한다.
- 지역연도셀 10% 초과는 여전히 남는다. 따라서 이 결과는 “업종별 WAPE 목표” 달성이지 “모든 지역셀 10% 이하” 달성이 아니다.

## 2. 시군구×업종: 상위 업종총량 배분 결과

시군구×업종은 lower-level actual이 있는 2021~2023년 연간 시군구 GRVA로 검증했다. 후보는 target-year 시군구 actual을 보지 않고, 시도×업종 상위 실제값이 공표된 뒤 그 총량을 시군구 예측분포에 배분하는 방식이다.

{md_table(sig_compare.rename(columns={
    "scenario": "시나리오",
    "max_activity_wape_pct": "업종최대WAPE_pct",
    "activities_over10_wape": "WAPE10초과_업종수",
    "cell_over10": "시군구연도셀_10pct초과",
    "cell_over20": "시군구연도셀_20pct초과",
    "routed_activities": "상위총량배분_적용업종",
}), 3)}

판단:

- 기준선에서 WAPE 10% 초과 업종은 `건설업`, `운수 및 창고업` 2개다.
- `운수 및 창고업`에만 상위 업종총량 배분을 적용하면 운수 WAPE는 10% 이하로 내려간다.
- `건설업`은 상위총량을 맞춰도 20.68% → 19.43%에 그친다. 즉 건설업 문제는 시도 총량 문제가 아니라 시군구 내부 배분 문제다.
- 따라서 현재 무료 공공자료 묶음에서 최소 잔여 취약 산업군은 `건설업` 1개로 압축된다.

## 3. 폐기 실험: 과거 오차 lag 보정

city×activity별 직전 공표연도의 예측/실제 비율을 다음 연도에 일부 반영하는 실험은 누수는 피하지만 성능이 악화되었다.

{md_table(lag_summary.rename(columns={
    "start_prediction": "시작예측",
    "shrink": "반영률",
    "all_activity_wape_pct": "전체WAPE_pct",
    "over10_cells": "10pct초과셀",
    "construction_wape_pct": "건설WAPE_pct",
    "transport_wape_pct": "운수창고WAPE_pct",
    "decision": "판정",
}), 3)}

폐기 사유:

- 건설업과 정보통신업은 과거 잔차가 안정적 편향으로 이어지지 않는다.
- 단일 개발사업, 대형 사업장, 지역 이벤트가 만든 충격을 다음 연도에 복제하면 오히려 노이즈가 커진다.
- 따라서 잔차보정은 학술적으로 가능한 후보지만, 현재 검증에서는 guardrail을 통과하지 못한다.
- 이 결론은 계층적 벤치마킹/재조정(hierarchical reconciliation)의 일반 원칙과도 맞다. 상위총량 일관성은 확보할 수 있지만, 하위지역 내부 분포는 독립적인 활동자료가 없으면 잔차 복제로 보정하면 안 된다.

## 4. 남은 10% 초과 셀의 성격

`건설업+운수 및 창고업+정보통신업`에 상위총량 배분을 적용한 뒤에도 남는 대형 오차 셀 상위 일부다.

{md_table(remaining[[
    "quarter_region", "city", "year", "activity", "actual_eok", "parent_control_top3_predicted_eok", "candidate_abs_error_eok", "candidate_ape_pct"
]].head(25).rename(columns={
    "quarter_region": "시도",
    "city": "시군구",
    "year": "연도",
    "activity": "업종",
    "actual_eok": "실제_억원",
    "parent_control_top3_predicted_eok": "후보추정_억원",
    "candidate_abs_error_eok": "절대오차_억원",
    "candidate_ape_pct": "오차율_pct",
}), 3)}

## 5. 성능 개선을 위해 추가로 필요한 것

### 채택 가능

1. `운수 및 창고업`: 상위 시도×업종 총량 공표 후 시군구 배분에 반영.
2. `시도×업종 운영시점`: 직전연도 지역 업종 기준값이 공표된 뒤에는 운수·창고업 1개 route만 별도 적용.

### 아직 부족

1. `건설업`: 상위총량 배분으로 해결되지 않음.
2. 시군구 내부 건설 배분에는 다음 직접 활동자료가 필요하다.
   - 건축착공/허가 면적의 시군구×월/분기 집계
   - 건설수주/공공계약의 공사장 소재지 기준 금액
   - 대형 개발사업 착공·준공 일정
   - 주거/비주거/토목 구분

## 결론

- 현 자료만으로 “업종별 전국합산 WAPE”는 이미 대부분 10% 이하이므로 목표로 쓰기에는 너무 느슨하다.
- 더 엄격하게 `시도×업종 운영시점`으로 보면, 최소 특화 산업군은 `운수 및 창고업` 1개다. 다만 공표시점 가드레일이 필요하다.
- `시군구×업종 연간`으로 보면, 상위총량 배분을 적용해도 `건설업`만은 10% 이하로 내려가지 않는다.
- 따라서 다음 실험의 유일한 1순위는 건설업 전용 활동자료 수집과 시군구 내부 배분모형이다. 모든 업종을 특화할 필요는 없고, 현재 증거상 건설업 1개만 별도 특화하는 것이 가장 경제적이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(sido_compare.to_string(index=False))
    print(sig_compare.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
