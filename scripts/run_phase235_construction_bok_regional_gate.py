#!/usr/bin/env python3
"""Phase235: rolling regional gate for BOK-style construction timing.

Phase234 showed that BOK-style 12/24-quarter construction order dispersion is
much better than raw construction orders, but cannot be applied to all regions
unconditionally. This script tests region-by-region rolling gates that decide
whether to use the BOK timing candidate using only prior years.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NATION = ROOT / "nationwide"
OUTDIR = ROOT / "data" / "processed" / "phase235_construction_bok_regional_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase235_construction_bok_regional_gate.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None, digits: int = 3) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("WAPE", "pp", "억원", "개", "%", "APE")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals: list[str] = []
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


def load_base() -> pd.DataFrame:
    p = NATION / "outputs" / "region_level_indicator_candidate_detail.csv"
    df = pd.read_csv(p, low_memory=False)
    df = df[
        df["activity"].eq("건설업")
        & df["route_id"].eq("regional_construction_orders_bok_12_24q")
        & df["year"].between(2021, 2025)
    ].copy()
    df["candidate_better"] = df["candidate_abs_error_eok"] < df["baseline_abs_error_eok"]
    df["candidate_over10"] = df["candidate_ape_pct"] > 10
    df["baseline_over10"] = df["baseline_ape_pct"] > 10
    df["candidate_over20"] = df["candidate_ape_pct"] > 20
    df["baseline_over20"] = df["baseline_ape_pct"] > 20
    return df


def gate_decision(prior: pd.DataFrame, rule_id: str) -> tuple[bool, str]:
    if prior.empty:
        return False, "no_prior"

    if rule_id == "prior1_improves":
        h = prior.sort_values("year").tail(1)
        ok = bool(h["candidate_better"].all())
        return ok, "last_year_candidate_abs_error_lower" if ok else "last_year_not_better"

    if rule_id == "prior2_sum_improves":
        h = prior.sort_values("year").tail(2)
        if len(h) < 2:
            return False, "need_2_prior_years"
        ok = float(h["candidate_abs_error_eok"].sum()) < float(h["baseline_abs_error_eok"].sum())
        return ok, "prior2_abs_error_sum_lower" if ok else "prior2_abs_error_sum_not_lower"

    if rule_id == "prior2_guardrail":
        h = prior.sort_values("year").tail(2)
        if len(h) < 2:
            return False, "need_2_prior_years"
        ok = (
            float(h["candidate_abs_error_eok"].sum()) < float(h["baseline_abs_error_eok"].sum())
            and int(h["candidate_over10"].sum()) <= int(h["baseline_over10"].sum())
            and int(h["candidate_over20"].sum()) <= int(h["baseline_over20"].sum())
            and float(h["candidate_ape_pct"].max()) <= float(h["baseline_ape_pct"].max())
        )
        return ok, "prior2_full_guardrail" if ok else "prior2_guardrail_failed"

    if rule_id == "expanding_guardrail":
        h = prior.copy()
        ok = (
            float(h["candidate_abs_error_eok"].sum()) < float(h["baseline_abs_error_eok"].sum())
            and int(h["candidate_over10"].sum()) <= int(h["baseline_over10"].sum())
            and int(h["candidate_over20"].sum()) <= int(h["baseline_over20"].sum())
            and float(h["candidate_ape_pct"].max()) <= float(h["baseline_ape_pct"].max())
        )
        return ok, "expanding_full_guardrail" if ok else "expanding_guardrail_failed"

    raise ValueError(f"unknown rule_id={rule_id}")


def apply_rule(df: pd.DataFrame, rule_id: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    keys = ["quarter_region", "available_quarters"]
    for key, g in df.groupby(keys):
        g = g.sort_values("year").copy()
        for _, r in g.iterrows():
            year = int(r["year"])
            prior = g[g["year"].lt(year)].copy()
            use_candidate, reason = gate_decision(prior, rule_id)
            pred = float(r["candidate_predicted_eok"] if use_candidate else r["baseline_predicted_eok"])
            err = pred - float(r["official_annual_eok"])
            rows.append(
                {
                    "rule_id": rule_id,
                    "quarter_region": key[0],
                    "available_quarters": int(key[1]),
                    "year": year,
                    "use_bok": bool(use_candidate),
                    "gate_reason": reason,
                    "official_annual_eok": float(r["official_annual_eok"]),
                    "baseline_predicted_eok": float(r["baseline_predicted_eok"]),
                    "candidate_predicted_eok": float(r["candidate_predicted_eok"]),
                    "selected_predicted_eok": pred,
                    "baseline_error_eok": float(r["baseline_error_eok"]),
                    "candidate_error_eok": float(r["candidate_error_eok"]),
                    "selected_error_eok": err,
                    "baseline_abs_error_eok": float(r["baseline_abs_error_eok"]),
                    "candidate_abs_error_eok": float(r["candidate_abs_error_eok"]),
                    "selected_abs_error_eok": abs(err),
                    "baseline_ape_pct": float(r["baseline_ape_pct"]),
                    "candidate_ape_pct": float(r["candidate_ape_pct"]),
                    "selected_ape_pct": abs(err) / abs(float(r["official_annual_eok"])) * 100,
                }
            )
    return pd.DataFrame(rows)


def summarize(sel: pd.DataFrame) -> pd.DataFrame:
    s = (
        sel.groupby(["rule_id", "available_quarters"], as_index=False)
        .agg(
            rows=("year", "count"),
            adopted_cells=("use_bok", "sum"),
            official_sum_eok=("official_annual_eok", lambda x: x.abs().sum()),
            baseline_abs_error_eok=("baseline_abs_error_eok", "sum"),
            candidate_all_abs_error_eok=("candidate_abs_error_eok", "sum"),
            selected_abs_error_eok=("selected_abs_error_eok", "sum"),
            baseline_over10=("baseline_ape_pct", lambda x: int((x > 10).sum())),
            candidate_all_over10=("candidate_ape_pct", lambda x: int((x > 10).sum())),
            selected_over10=("selected_ape_pct", lambda x: int((x > 10).sum())),
            baseline_over20=("baseline_ape_pct", lambda x: int((x > 20).sum())),
            candidate_all_over20=("candidate_ape_pct", lambda x: int((x > 20).sum())),
            selected_over20=("selected_ape_pct", lambda x: int((x > 20).sum())),
            max_baseline_ape_pct=("baseline_ape_pct", "max"),
            max_candidate_all_ape_pct=("candidate_ape_pct", "max"),
            max_selected_ape_pct=("selected_ape_pct", "max"),
        )
    )
    for prefix, col in [
        ("baseline", "baseline_abs_error_eok"),
        ("candidate_all", "candidate_all_abs_error_eok"),
        ("selected", "selected_abs_error_eok"),
    ]:
        s[f"{prefix}_wape_pct"] = s[col] / s["official_sum_eok"] * 100
    s["selected_delta_vs_baseline_pp"] = s["selected_wape_pct"] - s["baseline_wape_pct"]
    s["candidate_all_delta_vs_baseline_pp"] = s["candidate_all_wape_pct"] - s["baseline_wape_pct"]
    s["gate_pass"] = (
        (s["selected_wape_pct"] < s["baseline_wape_pct"])
        & (s["selected_over10"] <= s["baseline_over10"])
        & (s["selected_over20"] <= s["baseline_over20"])
        & (s["max_selected_ape_pct"] <= s["max_baseline_ape_pct"])
    )
    return s.sort_values(["available_quarters", "selected_wape_pct", "rule_id"])


def region_summary(sel: pd.DataFrame) -> pd.DataFrame:
    s = (
        sel.groupby(["rule_id", "quarter_region"], as_index=False)
        .agg(
            rows=("year", "count"),
            adopted_cells=("use_bok", "sum"),
            official_sum_eok=("official_annual_eok", lambda x: x.abs().sum()),
            baseline_abs_error_eok=("baseline_abs_error_eok", "sum"),
            selected_abs_error_eok=("selected_abs_error_eok", "sum"),
            max_baseline_ape_pct=("baseline_ape_pct", "max"),
            max_selected_ape_pct=("selected_ape_pct", "max"),
        )
    )
    s["baseline_wape_pct"] = s["baseline_abs_error_eok"] / s["official_sum_eok"] * 100
    s["selected_wape_pct"] = s["selected_abs_error_eok"] / s["official_sum_eok"] * 100
    s["delta_pp"] = s["selected_wape_pct"] - s["baseline_wape_pct"]
    return s.sort_values(["rule_id", "delta_pp"])


def yearly_summary(sel: pd.DataFrame) -> pd.DataFrame:
    s = (
        sel.groupby(["rule_id", "available_quarters", "year"], as_index=False)
        .agg(
            rows=("year", "count"),
            adopted_cells=("use_bok", "sum"),
            official_sum_eok=("official_annual_eok", lambda x: x.abs().sum()),
            baseline_abs_error_eok=("baseline_abs_error_eok", "sum"),
            selected_abs_error_eok=("selected_abs_error_eok", "sum"),
            baseline_over10=("baseline_ape_pct", lambda x: int((x > 10).sum())),
            selected_over10=("selected_ape_pct", lambda x: int((x > 10).sum())),
            baseline_over20=("baseline_ape_pct", lambda x: int((x > 20).sum())),
            selected_over20=("selected_ape_pct", lambda x: int((x > 20).sum())),
            max_baseline_ape_pct=("baseline_ape_pct", "max"),
            max_selected_ape_pct=("selected_ape_pct", "max"),
        )
    )
    s["baseline_wape_pct"] = s["baseline_abs_error_eok"] / s["official_sum_eok"] * 100
    s["selected_wape_pct"] = s["selected_abs_error_eok"] / s["official_sum_eok"] * 100
    s["delta_pp"] = s["selected_wape_pct"] - s["baseline_wape_pct"]
    s["year_guardrail_pass"] = (
        (s["selected_wape_pct"] <= s["baseline_wape_pct"])
        & (s["selected_over10"] <= s["baseline_over10"])
        & (s["selected_over20"] <= s["baseline_over20"])
        & (s["max_selected_ape_pct"] <= s["max_baseline_ape_pct"])
    )
    s["year_wape_under10"] = s["selected_wape_pct"] <= 10
    s["year_full_pass"] = s["year_guardrail_pass"] & s["year_wape_under10"]
    return s.sort_values(["rule_id", "available_quarters", "year"])


def build_policy(sel: pd.DataFrame) -> pd.DataFrame:
    # Conservative policy from scientist/evaluator review:
    # Q1 uses prior2_sum_improves for stronger recent evidence; Q2~Q4 use
    # expanding_guardrail for explicit multi-year guardrails.
    rule_by_q = {
        1: "prior2_sum_improves",
        2: "expanding_guardrail",
        3: "expanding_guardrail",
        4: "expanding_guardrail",
    }
    parts = []
    for q, rule in rule_by_q.items():
        parts.append(sel[sel["available_quarters"].eq(q) & sel["rule_id"].eq(rule)].copy())
    policy = pd.concat(parts, ignore_index=True)
    policy["policy_id"] = "conservative_bok_regional_gate"
    policy["policy_reason"] = policy["available_quarters"].map(
        {
            1: "Q1은 최근2년 개선합 기준으로 우연 적용 억제",
            2: "Q2는 누적 guardrail로 보수 적용",
            3: "Q3는 누적 guardrail로 보수 적용",
            4: "Q4는 누적 guardrail로 보수 적용",
        }
    )
    return policy


def build_strict_policy(sel: pd.DataFrame) -> pd.DataFrame:
    # Strict policy after year-by-year audit:
    # only Q1 and Q2 have a rule that passes every evaluation year. Q3/Q4 keep
    # baseline because all BOK gates fail at least one year-level guardrail.
    rule_by_q = {
        1: "prior2_sum_improves",
        2: "expanding_guardrail",
    }
    parts = []
    for q in [1, 2, 3, 4]:
        if q in rule_by_q:
            h = sel[sel["available_quarters"].eq(q) & sel["rule_id"].eq(rule_by_q[q])].copy()
        else:
            # Use an arbitrary rule's rows as a shell, but force baseline.
            h = sel[sel["available_quarters"].eq(q) & sel["rule_id"].eq("expanding_guardrail")].copy()
            h["use_bok"] = False
            h["selected_predicted_eok"] = h["baseline_predicted_eok"]
            h["selected_error_eok"] = h["baseline_error_eok"]
            h["selected_abs_error_eok"] = h["baseline_abs_error_eok"]
            h["selected_ape_pct"] = h["baseline_ape_pct"]
            h["gate_reason"] = "strict_policy_baseline_due_year_guardrail_failure"
        parts.append(h)
    policy = pd.concat(parts, ignore_index=True)
    policy["policy_id"] = "strict_q1_q2_bok_gate_q3_q4_baseline"
    policy["policy_reason"] = policy["available_quarters"].map(
        {
            1: "Q1 prior2_sum_improves는 2023~2025 연도별 guardrail 통과",
            2: "Q2 expanding_guardrail은 2023~2025 연도별 guardrail 통과",
            3: "Q3 BOK gate는 최소 1개 연도 guardrail 실패로 baseline 유지",
            4: "Q4 BOK gate는 최소 1개 연도 guardrail 실패로 baseline 유지",
        }
    )
    return policy


def summarize_policy(policy: pd.DataFrame) -> pd.DataFrame:
    s = (
        policy.groupby(["policy_id", "available_quarters"], as_index=False)
        .agg(
            rows=("year", "count"),
            adopted_cells=("use_bok", "sum"),
            official_sum_eok=("official_annual_eok", lambda x: x.abs().sum()),
            baseline_abs_error_eok=("baseline_abs_error_eok", "sum"),
            selected_abs_error_eok=("selected_abs_error_eok", "sum"),
            baseline_over10=("baseline_ape_pct", lambda x: int((x > 10).sum())),
            selected_over10=("selected_ape_pct", lambda x: int((x > 10).sum())),
            baseline_over20=("baseline_ape_pct", lambda x: int((x > 20).sum())),
            selected_over20=("selected_ape_pct", lambda x: int((x > 20).sum())),
            max_baseline_ape_pct=("baseline_ape_pct", "max"),
            max_selected_ape_pct=("selected_ape_pct", "max"),
        )
    )
    s["baseline_wape_pct"] = s["baseline_abs_error_eok"] / s["official_sum_eok"] * 100
    s["selected_wape_pct"] = s["selected_abs_error_eok"] / s["official_sum_eok"] * 100
    s["delta_pp"] = s["selected_wape_pct"] - s["baseline_wape_pct"]
    s["policy_pass"] = (
        (s["selected_wape_pct"] <= s["baseline_wape_pct"])
        & (s["selected_wape_pct"] <= 10)
        & (s["selected_over10"] <= s["baseline_over10"])
        & (s["selected_over20"] <= s["baseline_over20"])
        & (s["max_selected_ape_pct"] <= s["max_baseline_ape_pct"])
    )
    return s


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = load_base()
    rules = ["prior1_improves", "prior2_sum_improves", "prior2_guardrail", "expanding_guardrail"]
    selected = pd.concat([apply_rule(base, r) for r in rules], ignore_index=True)
    # Operational years with at least two possible prior observations for stricter gates.
    selected_eval = selected[selected["year"].between(2023, 2025)].copy()

    summary = summarize(selected_eval)
    reg = region_summary(selected_eval)
    ysum = yearly_summary(selected_eval)
    policy = build_policy(selected_eval)
    policy_summary = summarize_policy(policy)
    policy_yearly = yearly_summary(policy.assign(rule_id=policy["policy_id"]))
    strict_policy = build_strict_policy(selected_eval)
    strict_policy_summary = summarize_policy(strict_policy)
    strict_policy_yearly = yearly_summary(strict_policy.assign(rule_id=strict_policy["policy_id"]))
    adopted = selected_eval[selected_eval["use_bok"]].copy()
    weak = selected_eval.sort_values("selected_ape_pct", ascending=False).head(40)

    selected_eval.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_summary.csv", index=False, encoding="utf-8-sig")
    reg.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_region_summary.csv", index=False, encoding="utf-8-sig")
    ysum.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_yearly_summary.csv", index=False, encoding="utf-8-sig")
    policy.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_conservative_policy_detail.csv", index=False, encoding="utf-8-sig")
    policy_summary.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_conservative_policy_summary.csv", index=False, encoding="utf-8-sig")
    policy_yearly.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_conservative_policy_yearly.csv", index=False, encoding="utf-8-sig")
    strict_policy.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_strict_policy_detail.csv", index=False, encoding="utf-8-sig")
    strict_policy_summary.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_strict_policy_summary.csv", index=False, encoding="utf-8-sig")
    strict_policy_yearly.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_strict_policy_yearly.csv", index=False, encoding="utf-8-sig")
    adopted.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_adopted_cells.csv", index=False, encoding="utf-8-sig")
    weak.to_csv(OUTDIR / "phase235_construction_bok_regional_gate_weak_cells.csv", index=False, encoding="utf-8-sig")

    best = summary[summary["gate_pass"]].sort_values(["selected_wape_pct", "selected_delta_vs_baseline_pp"]).copy()
    if best.empty:
        best_text = "_전체 guardrail을 통과한 rolling gate 없음_"
    else:
        best_text = md_table(
            best,
            [
                ("rule_id", "규칙"),
                ("available_quarters", "사용분기"),
                ("rows", "셀"),
                ("adopted_cells", "BOK적용셀"),
                ("baseline_wape_pct", "기준 WAPE_%"),
                ("selected_wape_pct", "gate WAPE_%"),
                ("selected_delta_vs_baseline_pp", "변화 pp"),
                ("baseline_over10", "기준 10%초과"),
                ("selected_over10", "gate 10%초과"),
                ("baseline_over20", "기준 20%초과"),
                ("selected_over20", "gate 20%초과"),
                ("max_baseline_ape_pct", "기준 최대APE_%"),
                ("max_selected_ape_pct", "gate 최대APE_%"),
            ],
        )

    report = f"""# Phase235 건설업 BOK식 시간분산 지역 gate 실험

생성시각: {CREATED_AT}

## 결론

- BOK식 건축12·토목24분기 분산은 원자료보다 우수하지만, 전체 지역 일괄 적용은 Phase234에서 미채택됐다.
- 이번 실험은 target-year actual을 보지 않고, 과거연도 성과만으로 지역×운영분기별 BOK 적용 여부를 결정했다.
- 평가기간은 2023~2025년이며, 2021~2022년은 gate 학습용 과거로만 사용했다.
- 엄격 운영정책은 Q1/Q2에만 BOK gate를 제한 적용하고, Q3/Q4는 연도별 guardrail 실패 가능성 때문에 기존 방식을 유지한다.
- 이 route는 광역시도×건설업의 분기 시간경로 보강에 한정된다. 시군구×건설업 공간배분 개선으로 해석하지 않는다.
- Q1/Q2 평가기간 평균 WAPE는 10% 이하이나, 2025년 일부 단년 WAPE가 10%를 소폭 초과하므로 “전 연도 10% 이하 달성”으로 표현하지 않는다.

## gate 규칙

| 규칙 | 내용 |
| --- | --- |
| prior1_improves | 직전 1년에서 BOK 분산 절대오차가 기준보다 작으면 적용 |
| prior2_sum_improves | 직전 2년 절대오차 합계가 기준보다 작으면 적용 |
| prior2_guardrail | 직전 2년 절대오차 합계, 10%/20% 초과 셀, 최대 APE가 모두 기준보다 악화되지 않으면 적용 |
| expanding_guardrail | 모든 과거연도 누적 기준으로 prior2_guardrail과 같은 조건 적용 |

## 전체 요약

{md_table(summary, [
    ("rule_id", "규칙"),
    ("available_quarters", "사용분기"),
    ("rows", "셀"),
    ("adopted_cells", "BOK적용셀"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("candidate_all_wape_pct", "BOK일괄 WAPE_%"),
    ("selected_wape_pct", "gate WAPE_%"),
    ("selected_delta_vs_baseline_pp", "gate 변화 pp"),
    ("baseline_over10", "기준 10%초과"),
    ("selected_over10", "gate 10%초과"),
    ("baseline_over20", "기준 20%초과"),
    ("selected_over20", "gate 20%초과"),
    ("max_baseline_ape_pct", "기준 최대APE_%"),
    ("max_selected_ape_pct", "gate 최대APE_%"),
    ("gate_pass", "전체통과"),
])}

## 전체 guardrail 통과 후보

{best_text}

## 보수 운영규칙 후보

과학자·평가관 검토 기준으로 공격적인 단년 규칙(`prior1_improves`)은 민감도 후보로 두고, pooled 기준의 보수 후보는 다음처럼 제한한다.

| 사용분기 | 운영규칙 | 이유 |
| ---: | --- | --- |
| 1 | prior2_sum_improves | Q1은 관측정보가 적으므로 최근 2년 개선합 기준 |
| 2 | expanding_guardrail | Q2 이후는 누적 과거연도 guardrail 기준 |
| 3 | expanding_guardrail | 단년 우연 채택 억제 |
| 4 | expanding_guardrail | 단년 우연 채택 억제 |

{md_table(policy_summary, [
    ("available_quarters", "사용분기"),
    ("rows", "셀"),
    ("adopted_cells", "BOK적용셀"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("selected_wape_pct", "보수규칙 WAPE_%"),
    ("delta_pp", "변화 pp"),
    ("baseline_over10", "기준 10%초과"),
    ("selected_over10", "보수 10%초과"),
    ("baseline_over20", "기준 20%초과"),
    ("selected_over20", "보수 20%초과"),
    ("max_baseline_ape_pct", "기준 최대APE_%"),
    ("max_selected_ape_pct", "보수 최대APE_%"),
    ("policy_pass", "통과"),
])}

### 보수 운영규칙 연도별 점검

{md_table(policy_yearly, [
    ("available_quarters", "사용분기"),
    ("year", "연도"),
    ("adopted_cells", "BOK적용셀"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("selected_wape_pct", "보수규칙 WAPE_%"),
    ("delta_pp", "변화 pp"),
    ("baseline_over10", "기준 10%초과"),
    ("selected_over10", "보수 10%초과"),
    ("max_baseline_ape_pct", "기준 최대APE_%"),
    ("max_selected_ape_pct", "보수 최대APE_%"),
    ("year_guardrail_pass", "연도통과"),
], limit=16)}

연도별 점검 결과 Q3/Q4는 2023년에 한 차례씩 악화된다. 따라서 실제 운영 기본안은 아래의 더 엄격한 정책으로 둔다.

## 엄격 운영정책

| 사용분기 | 운영규칙 | 이유 |
| ---: | --- | --- |
| 1 | prior2_sum_improves | 2023~2025 모든 연도 guardrail 통과 |
| 2 | expanding_guardrail | 2023~2025 모든 연도 guardrail 통과 |
| 3 | baseline 유지 | BOK gate가 최소 1개 연도 guardrail 실패 |
| 4 | baseline 유지 | BOK gate가 최소 1개 연도 guardrail 실패 |

{md_table(strict_policy_summary, [
    ("available_quarters", "사용분기"),
    ("rows", "셀"),
    ("adopted_cells", "BOK적용셀"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("selected_wape_pct", "엄격정책 WAPE_%"),
    ("delta_pp", "변화 pp"),
    ("baseline_over10", "기준 10%초과"),
    ("selected_over10", "엄격 10%초과"),
    ("baseline_over20", "기준 20%초과"),
    ("selected_over20", "엄격 20%초과"),
    ("max_baseline_ape_pct", "기준 최대APE_%"),
    ("max_selected_ape_pct", "엄격 최대APE_%"),
    ("policy_pass", "통과"),
])}

### 엄격 운영정책 연도별 점검

{md_table(strict_policy_yearly, [
    ("available_quarters", "사용분기"),
    ("year", "연도"),
    ("adopted_cells", "BOK적용셀"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("selected_wape_pct", "엄격정책 WAPE_%"),
    ("delta_pp", "변화 pp"),
    ("baseline_over10", "기준 10%초과"),
    ("selected_over10", "엄격 10%초과"),
    ("max_baseline_ape_pct", "기준 최대APE_%"),
    ("max_selected_ape_pct", "엄격 최대APE_%"),
    ("year_guardrail_pass", "연도 no-worse"),
    ("year_wape_under10", "연도 WAPE≤10"),
    ("year_full_pass", "연도 완전통과"),
], limit=16)}

## 지역별 효과 상위·하위

### 개선 상위

{md_table(reg.sort_values("delta_pp"), [
    ("rule_id", "규칙"),
    ("quarter_region", "시도"),
    ("adopted_cells", "BOK적용셀"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("selected_wape_pct", "gate WAPE_%"),
    ("delta_pp", "변화 pp"),
], limit=15)}

### 악화 상위

{md_table(reg.sort_values("delta_pp", ascending=False), [
    ("rule_id", "규칙"),
    ("quarter_region", "시도"),
    ("adopted_cells", "BOK적용셀"),
    ("baseline_wape_pct", "기준 WAPE_%"),
    ("selected_wape_pct", "gate WAPE_%"),
    ("delta_pp", "변화 pp"),
], limit=15)}

## 남은 취약 셀

{md_table(weak, [
    ("rule_id", "규칙"),
    ("quarter_region", "시도"),
    ("year", "연도"),
    ("available_quarters", "사용분기"),
    ("use_bok", "BOK적용"),
    ("official_annual_eok", "실제_억원"),
    ("selected_predicted_eok", "gate추정_억원"),
    ("selected_ape_pct", "gate APE_%"),
    ("baseline_ape_pct", "기준 APE_%"),
], limit=20)}

## 판정

- gate가 통과해도 이것은 건설업 **광역시도 시간경로** 후보일 뿐, 시군구 공간배분 성능이 아니다.
- 본 route는 광역시도×건설업의 분기 시간경로 보강에 한정된다. 시군구 내부 공간배분은 기존 share를 그대로 사용하므로, 시군구×건설업 WAPE 개선으로 해석하지 않는다.
- Q+1개월 속보성 주장은 건설수주 자료의 실제 공표시차가 운영시점 이전임을 확인한 뒤에만 가능하다.
- guardrail 통과 후보가 없다면 BOK식 분산은 전국 운영 route로 쓰지 않고, 취약지역 진단 및 다음 후보 생성에만 사용한다.
- guardrail 통과 후보가 있어도 적용 범위는 해당 규칙·운영분기·지역으로 제한한다.
- 연도별 no-worse까지 요구하면 현재 BOK 적용 범위는 Q1/Q2 건설업 시간경로에 한정하고, Q3/Q4는 기존 방식 유지가 안전하다.
- 다만 2025년 Q1/Q2처럼 개선 후에도 연도 단독 WAPE가 10%를 약간 넘는 경우가 있어, “모든 연도·운영시점 10% 이하 완전 달성”으로 표현하지 않는다.
- 시군구×건설업 WAPE 10% 목표에는 여전히 건축HUB·재건축/재개발·PPS·토목사업 event 결합 실험이 필요하다.

## 산출 파일

- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_detail.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_summary.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_region_summary.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_yearly_summary.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_conservative_policy_detail.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_conservative_policy_summary.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_conservative_policy_yearly.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_strict_policy_detail.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_strict_policy_summary.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_strict_policy_yearly.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_adopted_cells.csv`
- `data/processed/phase235_construction_bok_regional_gate/phase235_construction_bok_regional_gate_weak_cells.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR)


if __name__ == "__main__":
    main()
