#!/usr/bin/env python3
"""Phase101: compare raw middle-industry allocation with final guarded GVA estimates.

The large 1000%+ errors shown in the poster came from the raw small-to-middle
aggregation diagnostic.  That diagnostic is useful as a failure detector, but
it is not the final structural allocation result.  This phase compares that
raw baseline with the Phase98 protected registry and documents which problems
are actually solved by existing structural guardrails and which remain as
data-limited gaps.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase101_structural_guardrail_finalization"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase101_structural_guardrail_finalization.md"
PHASE98 = DATA / "phase98_final_middle_industry_accuracy_registry" / "phase98_final_middle_industry_accuracy_registry.csv"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append(
        "| "
        + " | ".join("---:" if any(token in label for token in ("억원", "%", "개", "감소", "축소")) else "---" for _, label in cols)
        + " |"
    )
    for _, row in df.iterrows():
        vals: list[str] = []
        for key, _ in cols:
            value = row.get(key, "")
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}" if abs(value) < 100 else f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def grade(error_rate: float, error_eok: float) -> str:
    if error_rate <= 5:
        return "정밀(5% 이하)"
    if error_rate <= 10:
        return "활용후보(10% 이하)"
    if error_rate <= 20:
        return "주의(10~20%)"
    if error_rate <= 50:
        return "자료보강(20~50%)"
    return "현 기준 부적합(50% 초과)"


def cause(row: pd.Series) -> str:
    parent = row.parent_code
    code = str(row.middle_code).zfill(2)
    if row.protected_error_rate_pct > 100 and row.actual_gva_eok < 100:
        return "소규모 분모로 상대오차 폭발"
    if parent == "C00":
        return "제조업 내부 생산집중·시설규모 차이"
    if parent == "J00":
        return "콘텐츠·디지털 활동자료 부족"
    if parent == "ERS":
        return "공공·비영리 활동규모 자료 부족"
    if parent == "MN0":
        return "전문인력·계약액 자료 부족"
    if parent == "K00":
        return "거래·자산 규모 자료 부족"
    if parent == "F00":
        return "공사 발생지·계약액 자료 부족"
    if parent == "G00" and code == "45":
        return "자동차 판매대수·딜러 매출 자료 부족"
    if parent == "H00":
        return "물동량·운송량 자료 부족"
    return "중분류 직접 활동자료 부족"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(PHASE98, dtype={"middle_code": str})
    reg["middle_code"] = reg.middle_code.astype(str).str.zfill(2)
    reg["initial_error_rate_pct"] = reg.initial_error_gva_eok / reg.actual_gva_eok.replace(0, np.nan) * 100
    reg["protected_error_rate_pct"] = reg.protected_error_gva_eok / reg.actual_gva_eok.replace(0, np.nan) * 100
    reg["initial_grade2"] = [grade(r.initial_error_rate_pct, r.initial_error_gva_eok) for r in reg.itertuples()]
    reg["protected_grade2"] = [grade(r.protected_error_rate_pct, r.protected_error_gva_eok) for r in reg.itertuples()]
    reg["error_reduction_eok"] = reg.initial_error_gva_eok - reg.protected_error_gva_eok
    reg["error_rate_reduction_pp"] = reg.initial_error_rate_pct - reg.protected_error_rate_pct
    reg["remaining_cause"] = reg.apply(cause, axis=1)

    summary = (
        reg.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            initial_error_sum_eok=("initial_error_gva_eok", "sum"),
            protected_error_sum_eok=("protected_error_gva_eok", "sum"),
            initial_median_error_pct=("initial_error_rate_pct", "median"),
            protected_median_error_pct=("protected_error_rate_pct", "median"),
            initial_over_20=("initial_error_rate_pct", lambda s: int((s > 20).sum())),
            protected_over_20=("protected_error_rate_pct", lambda s: int((s > 20).sum())),
            initial_over_100=("initial_error_rate_pct", lambda s: int((s > 100).sum())),
            protected_over_100=("protected_error_rate_pct", lambda s: int((s > 100).sum())),
        )
    )
    summary["initial_wape_pct"] = summary.initial_error_sum_eok / summary.actual_sum_eok * 100
    summary["protected_wape_pct"] = summary.protected_error_sum_eok / summary.actual_sum_eok * 100
    summary["error_reduction_eok"] = summary.initial_error_sum_eok - summary.protected_error_sum_eok
    summary["wape_reduction_pp"] = summary.initial_wape_pct - summary.protected_wape_pct

    improved = reg[reg.error_reduction_eok.gt(1e-9)].sort_values(["city", "error_reduction_eok"], ascending=[True, False])
    remaining = reg[
        reg.protected_error_rate_pct.gt(20) | reg.protected_error_gva_eok.gt(500)
    ].sort_values(["city", "protected_error_gva_eok"], ascending=[True, False])
    exploded_initial = reg[reg.initial_error_rate_pct.gt(100)].sort_values(
        ["city", "initial_error_rate_pct"], ascending=[True, False]
    )
    exploded_remaining = reg[reg.protected_error_rate_pct.gt(100)].sort_values(
        ["city", "protected_error_rate_pct"], ascending=[True, False]
    )
    by_cause = (
        remaining.groupby(["city", "remaining_cause"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("protected_error_gva_eok", "sum"),
            max_error_pct=("protected_error_rate_pct", "max"),
        )
        .sort_values(["city", "error_sum_eok"], ascending=[True, False])
    )
    by_cause["wape_pct"] = by_cause.error_sum_eok / by_cause.actual_sum_eok * 100

    reg.to_csv(OUTDIR / "phase101_middle_accuracy_before_after.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase101_city_summary.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUTDIR / "phase101_error_reduced_middle_industries.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase101_remaining_gap_middle_industries.csv", index=False, encoding="utf-8-sig")
    by_cause.to_csv(OUTDIR / "phase101_remaining_gap_by_cause.csv", index=False, encoding="utf-8-sig")

    report = f"""# 구조형 배분 기준 최종 점검

## 목적

원시 소분류→중분류 집계표에서 1000%대 오차가 나타난 이유를 확인하고, 현재 최종 기준으로 사용하는 Phase98 보호 기준이 그 문제를 얼마나 줄였는지 점검했다. 검증 대상은 모두 총부가가치(GVA)이며, 금액 단위는 억원이다.

## 도시별 원시 기준 대비 최종 기준

{md_table(summary, [("city", "지역"), ("cells", "중분류 개"), ("actual_sum_eok", "실제합계 억원"), ("initial_error_sum_eok", "원시오차 억원"), ("protected_error_sum_eok", "최종오차 억원"), ("error_reduction_eok", "오차감소 억원"), ("initial_wape_pct", "원시 WAPE %"), ("protected_wape_pct", "최종 WAPE %"), ("wape_reduction_pp", "WAPE 감소 pp"), ("initial_over_20", "원시 20%초과 개"), ("protected_over_20", "최종 20%초과 개"), ("initial_over_100", "원시 100%초과 개"), ("protected_over_100", "최종 100%초과 개")])}

## 100% 초과오차 처리 결과

### 원시 기준 100% 초과

{md_table(exploded_initial, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("initial_predicted_gva_eok", "원시추정 억원"), ("initial_error_gva_eok", "원시오차 억원"), ("initial_error_rate_pct", "원시오차 %"), ("protected_predicted_gva_eok", "최종추정 억원"), ("protected_error_gva_eok", "최종오차 억원"), ("protected_error_rate_pct", "최종오차 %")], 30)}

### 최종 기준에도 남은 100% 초과

{md_table(exploded_remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("protected_predicted_gva_eok", "최종추정 억원"), ("protected_error_gva_eok", "최종오차 억원"), ("protected_error_rate_pct", "최종오차 %"), ("remaining_cause", "원인")], 30)}

## 최종 기준에서 오차가 크게 줄어든 중분류

{md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("initial_error_gva_eok", "원시오차 억원"), ("protected_error_gva_eok", "최종오차 억원"), ("error_reduction_eok", "감소 억원"), ("initial_error_rate_pct", "원시오차 %"), ("protected_error_rate_pct", "최종오차 %"), ("protected_option_name", "최종 기준")], 30)}

## 최종 기준에도 남은 금액격차

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("protected_predicted_gva_eok", "최종추정 억원"), ("protected_error_gva_eok", "최종오차 억원"), ("protected_error_rate_pct", "최종오차 %"), ("remaining_cause", "원인")], 40)}

## 원인군 요약

{md_table(by_cause, [("city", "지역"), ("remaining_cause", "원인군"), ("cells", "중분류 개"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "WAPE %"), ("max_error_pct", "최대오차 %")], 30)}

## 결론

1. 1000%대 오차는 최종 구조형 기준의 결론이 아니라 원시 배분 실패 신호다. 포스터와 대외 산출물은 Phase98 보호 기준을 기준표로 사용해야 한다.
2. 포항 제조업의 식료품 제조업 1731% 원시오차는 최종 기준에서 2.16%로 축소되었다. 이는 포항 제조업 내부의 1차 금속 집중 구조를 반영한 결과다.
3. 최종 기준에서도 포항 정보서비스업은 250.5%가 남는다. 다만 실제 GVA가 3.95억원인 소규모 분모 문제이므로 금액오차는 9.88억원이다.
4. 고양은 협회·단체, 방송업, 스포츠·오락 서비스업의 금액격차가 남는다. 이는 무료 후보군에 단체 예산·회원·방송매출·제작규모 같은 직접 활동자료가 없기 때문이다.
5. 따라서 다음 산출물은 “원시 집계 양호/취약”이 아니라 “최종 기준 격차 작은/금액격차 큰 중분류”로 표시해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase101_city_summary.csv")


if __name__ == "__main__":
    main()
