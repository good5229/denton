#!/usr/bin/env python3
"""Phase99: grouped backlog for remaining weak middle-industry GVA estimates.

Phase98 provides the final per-industry accuracy registry.  This phase turns
the remaining weak middle industries into a grouped improvement backlog.  The
unit of action is not one industry at a time; it is a cause group × city ×
parent-industry bundle with shared data requirements and a common model recipe.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE98 = DATA / "phase98_final_middle_industry_accuracy_registry"
OUTDIR = DATA / "phase99_remaining_weak_industry_backlog"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase99_remaining_weak_industry_backlog.md"


GROUP_RECIPE = {
    "생산시설형": {
        "model_recipe": "상위 제조업 GVA를 중분류별 출하액·전력·공장면적·종사자 규모의 가중 결합으로 재배분",
        "priority_sources": "제조업 중분류별 출하액/부가가치, 한전 중분류 전력, 공장등록 제조시설면적, 산단 대형사업장 규모",
        "validation_gate": "C00 내부 중분류 합계가 제조업 실제와 일치하고, 기존 대비 중분류 오차·판정구간이 악화되지 않을 것",
    },
    "공공·비영리형": {
        "model_recipe": "예산·시설정원·처리량·회원/종사자 규모를 묶어 공공·비영리 세부활동 기준 생성",
        "priority_sources": "비영리단체 활동규모, 체육·문화시설 이용/면적, 상하수도·폐기물 처리량, 복지시설 정원, 보조금/위탁계약",
        "validation_gate": "ERS/Q 등 내부 중분류의 10% 초과오차가 감소하고 10/20/50% 판정 경계가 악화되지 않을 것",
    },
    "디지털·콘텐츠형": {
        "model_recipe": "방송·콘텐츠·정보서비스 매출/제작규모/플랫폼 활동량을 기존 사업체 기준과 결합",
        "priority_sources": "방송사업자 매출, 콘텐츠 제작·배급 실적, 정보서비스 매출, 데이터센터/서버·플랫폼 활동량",
        "validation_gate": "J00 내부 방송·영상·정보서비스 과대/과소가 동시에 완화될 것",
    },
    "전문·지원서비스형": {
        "model_recipe": "전문인력·임금총액·계약액·사업장 규모를 결합해 지식서비스와 단순 사업장 수를 분리",
        "priority_sources": "고용보험 임금총액, 전문인력 수, R&D비, 용역·공공계약액, 자동차 등록/판매, 사업장 규모",
        "validation_gate": "MN0/G/I 내부 취약큐 오차가 감소하고 양호 산업이 주의 이상으로 악화되지 않을 것",
    },
    "계약·공사형": {
        "model_recipe": "건축허가·착공·사용승인·기성·계약액을 공사단계별로 분리해 건설/엔지니어링 기준 생성",
        "priority_sources": "건축허가·착공·사용승인 면적, 공공/민간 공사계약액, 건설기성, 엔지니어링 용역계약",
        "validation_gate": "F00 및 MN0 계약형 내부 중분류 합계와 실제 GVA 오차가 함께 감소할 것",
    },
    "거래·자산형": {
        "model_recipe": "거래금액·자산가치·임대면적·금융거래 규모를 결합해 사업체수 중심 배분을 대체",
        "priority_sources": "공시가격 총액, 부동산 거래량/거래금액, 임대면적, 금융·보험 수입/자산 규모",
        "validation_gate": "K/L 내부 과대·과소 방향이 동시에 완화되고 상대오차 20% 초과 셀이 줄어들 것",
    },
    "이동·물량형": {
        "model_recipe": "여객·화물·창고면적·항만물동량을 분리해 운송·창고 세부활동 기준 생성",
        "priority_sources": "여객 승하차, 화물 수송량, 창고면적, 항만 물동량, 물류시설 입지/면적",
        "validation_gate": "H00 내부 49/50/52 분할오차와 10% 초과오차가 동시에 감소할 것",
    },
}


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "점수", "개")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
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


def urgency(row: pd.Series) -> str:
    if row["protected_error_gva_eok"] >= 1_000 or row["protected_error_rate_pct"] >= 50:
        return "최우선"
    if row["protected_error_gva_eok"] >= 300 or row["protected_error_rate_pct"] >= 20:
        return "우선"
    if row["protected_error_rate_pct"] >= 10:
        return "관리"
    return "관찰"


def build_backlog(reg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    weak = reg[reg.protected_remaining_queue.eq("추가개선대상")].copy()
    weak["urgency"] = weak.apply(urgency, axis=1)
    urgency_rank = {"최우선": 1, "우선": 2, "관리": 3, "관찰": 4}
    weak["urgency_rank"] = weak.urgency.map(urgency_rank).fillna(9).astype(int)
    # Priority score: amount matters most, but high relative error and large
    # actual industries should not disappear behind small-error-rate giants.
    weak["priority_score"] = (
        weak.protected_error_gva_eok
        + weak.protected_error_rate_pct.clip(upper=100) * 5
        + np.log1p(weak.actual_gva_eok) * 20
    )
    for field in ("model_recipe", "priority_sources", "validation_gate"):
        weak[field] = weak.cause_group.map(lambda g: GROUP_RECIPE.get(g, {}).get(field, "중분류 직접 활동자료 기반 재배분"))
    weak["bundle_key"] = weak.city + "|" + weak.cause_group + "|" + weak.parent_code

    bundles = (
        weak.groupby(["city", "cause_group", "parent_code", "bundle_key"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            protected_error_sum_eok=("protected_error_gva_eok", "sum"),
            max_error_rate_pct=("protected_error_rate_pct", "max"),
            priority_score=("priority_score", "sum"),
            industries=("middle_label", lambda s: ", ".join(s.astype(str))),
            top_required_data=("required_next_data", lambda s: " / ".join(pd.Series(s).drop_duplicates().head(4))),
            model_recipe=("model_recipe", "first"),
            priority_sources=("priority_sources", "first"),
            validation_gate=("validation_gate", "first"),
        )
    )
    bundles["bundle_wape_pct"] = bundles.protected_error_sum_eok / bundles.actual_sum_eok.replace(0, np.nan) * 100
    bundles["target_error_after_10pct_eok"] = bundles.actual_sum_eok * 0.10
    bundles["gap_to_10pct_eok"] = (bundles.protected_error_sum_eok - bundles.target_error_after_10pct_eok).clip(lower=0)
    bundles["bundle_priority"] = np.where(
        bundles.gap_to_10pct_eok.gt(500) | bundles.max_error_rate_pct.gt(50),
        "A",
        np.where(bundles.protected_error_sum_eok.gt(500) | bundles.max_error_rate_pct.gt(20), "B", "C"),
    )
    bundles = bundles.sort_values(["bundle_priority", "priority_score"], ascending=[True, False])
    weak = weak.sort_values(["urgency_rank", "priority_score"], ascending=[True, False])
    return weak, bundles


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(PHASE98 / "phase98_final_middle_industry_accuracy_registry.csv")
    reg["middle_code"] = reg.middle_code.astype(str).str.zfill(2)
    weak, bundles = build_backlog(reg)
    by_city = (
        weak.groupby("city", as_index=False)
        .agg(
            weak_cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            protected_error_sum_eok=("protected_error_gva_eok", "sum"),
            max_error_rate_pct=("protected_error_rate_pct", "max"),
            priority_score=("priority_score", "sum"),
        )
    )
    by_city["weak_wape_pct"] = by_city.protected_error_sum_eok / by_city.actual_sum_eok * 100
    by_cause = (
        weak.groupby(["city", "cause_group"], as_index=False)
        .agg(
            weak_cells=("middle_code", "count"),
            protected_error_sum_eok=("protected_error_gva_eok", "sum"),
            max_error_rate_pct=("protected_error_rate_pct", "max"),
            priority_score=("priority_score", "sum"),
            model_recipe=("model_recipe", "first"),
            priority_sources=("priority_sources", "first"),
        )
        .sort_values(["city", "priority_score"], ascending=[True, False])
    )

    weak.to_csv(OUTDIR / "phase99_remaining_weak_industry_backlog.csv", index=False, encoding="utf-8-sig")
    bundles.to_csv(OUTDIR / "phase99_grouped_improvement_bundles.csv", index=False, encoding="utf-8-sig")
    by_city.to_csv(OUTDIR / "phase99_backlog_by_city.csv", index=False, encoding="utf-8-sig")
    by_cause.to_csv(OUTDIR / "phase99_backlog_by_cause_group.csv", index=False, encoding="utf-8-sig")

    report = f"""# 남은 취약 중분류 GVA 개선 backlog

## 목적

Phase98에서 각 산업별 실제·추정·오차를 정리했으므로, 이번 단계에서는 남은 취약 중분류를 개별 수작업 대상이 아니라 원인군별 개선 묶음으로 재편했다. 단위는 `지역 × 원인군 × 상위산업`이며, 같은 자료와 같은 모형 처방으로 여러 중분류를 동시에 개선하는 것을 목표로 한다.

## 격차 축소 판단

이후 작업의 목적은 총량을 맞췄다는 회계 설명이 아니라, 실제 중분류 총부가가치와 추정 중분류 총부가가치의 금액 격차를 줄이는 것이다. 모든 산업을 개별 특화모델로 만들면 재현성과 운영성이 떨어지므로, 개선 단위는 `원인군 × 상위산업`으로 고정한다.

따라서 다음 실험은 취약 중분류 45개를 각각 고치는 방식이 아니라, 14개 개선 묶음별로 공통 활동지표를 만들고 같은 검증표에서 비교한다. 후보가 채택되려면 (1) 상위산업 합계가 유지되고, (2) 묶음 전체 오차금액이 감소하며, (3) 금액오차 상위 중분류의 실제-추정 격차가 줄어야 한다. 포스터와 대외 설명은 이 금액 격차 축소 결과만 사용한다.

## 도시별 잔여 규모

{md_table(by_city, [("city", "지역"), ("weak_cells", "취약 중분류 개"), ("actual_sum_eok", "취약 실제합계 억원"), ("protected_error_sum_eok", "오차합계 억원"), ("weak_wape_pct", "취약군 WAPE %"), ("max_error_rate_pct", "최대오차 %"), ("priority_score", "우선순위 점수")])}

## 원인군별 backlog

{md_table(by_cause, [("city", "지역"), ("cause_group", "원인군"), ("weak_cells", "취약 중분류 개"), ("protected_error_sum_eok", "오차합계 억원"), ("max_error_rate_pct", "최대오차 %"), ("priority_score", "우선순위 점수"), ("priority_sources", "우선 자료"), ("model_recipe", "공통 처방")], 80)}

## 개선 묶음 우선순위

{md_table(bundles, [("bundle_priority", "등급"), ("city", "지역"), ("cause_group", "원인군"), ("parent_code", "상위산업"), ("cells", "중분류 개"), ("industries", "대상 산업"), ("actual_sum_eok", "실제합계 억원"), ("protected_error_sum_eok", "오차합계 억원"), ("bundle_wape_pct", "묶음 WAPE %"), ("gap_to_10pct_eok", "10% 목표초과 억원"), ("priority_sources", "우선 자료"), ("validation_gate", "채택검증")], 80)}

## 최우선 중분류

{md_table(weak, [("urgency", "긴급도"), ("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("cause_group", "원인군"), ("actual_gva_eok", "실제 억원"), ("protected_error_gva_eok", "오차 억원"), ("protected_error_rate_pct", "오차 %"), ("priority_score", "우선순위 점수"), ("required_next_data", "필요자료")], 100)}

## 실행 원칙

1. 같은 원인군 안에서는 단일 중분류만 고치지 않고, 상위산업 내부 후보 전체를 만들어 한 번에 검증한다.
2. 후보는 실제 중분류 GVA와 비교하되, 상위산업 합계 보존을 반드시 통과해야 한다.
3. 후보 선택 기준은 회계잔차가 아니라 `실제 GVA`, `추정 GVA`, `오차 억원`, `오차율`의 개선이다.
4. 같은 묶음 안에서 작은 산업의 상대오차가 커 보이는 경우에도 금액오차와 함께 판단한다.
5. 다음 실험 우선순위는 A등급 묶음부터 진행한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase99_grouped_improvement_bundles.csv")


if __name__ == "__main__":
    main()
