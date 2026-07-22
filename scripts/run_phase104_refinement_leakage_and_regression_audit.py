#!/usr/bin/env python3
"""Phase104: audit refined middle-industry GVA values for leakage/regression.

The public poster now shows both flash and refined estimates.  This script
checks whether very small refined errors can be interpreted as predictive
accuracy, and lists industries where the refined value is worse than the flash
value.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REGISTRY = DATA / "phase98_final_middle_industry_accuracy_registry" / "phase98_final_middle_industry_accuracy_registry.csv"
PHASE97 = DATA / "phase97_goyang_augmented_activity_screen"
OUTDIR = DATA / "phase104_refinement_leakage_and_regression_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase104_refinement_leakage_and_regression_audit.md"


LEAKAGE_FINDINGS = [
    {
        "audit_item": "상위산업 actual 총량 사용",
        "logic_location": "run_phase86_structural_template_screen.py / run_phase87_remaining_family_template_screen.py / run_phase95_composite_activity_indicator_screen.py::normalize_parent",
        "finding": "후보값을 city×parent actual 합계에 맞춰 정규화한다. Phase92 현재 기준도 Phase88→Phase87→Phase86 계열을 상속한다.",
        "risk": "정밀화 단계에서는 허용 가능하지만, 공표 전 속보성 예측 성능으로 주장하면 누수다.",
    },
    {
        "audit_item": "후보 선택에서 중분류 actual 사용",
        "logic_location": "run_phase86_structural_template_screen.py::select_safe / run_phase87_remaining_family_template_screen.py::select_safe / run_phase93_no_cell_worse_grouped_transfer.py::screen_candidates / run_phase95_composite_activity_indicator_screen.py::select_options / run_phase96_protected_weak_queue_selection.py::select",
        "finding": "각 후보의 중분류 actual 대비 오차·오차율·판정 악화를 계산한 뒤 후보를 고른다.",
        "risk": "1% 이내 정밀오차는 사후 후보선택/진단 결과이며, blind forecast 성능으로 해석하면 안 된다.",
    },
    {
        "audit_item": "보호 기준의 선택 목적",
        "logic_location": "run_phase96_protected_weak_queue_selection.py::select",
        "finding": "취약큐 오차와 상위산업 오차가 줄면 일부 비취약 셀의 금액오차 증가는 허용될 수 있다.",
        "risk": "전체 오차는 줄어도 특정 중분류는 속보값보다 나빠질 수 있다.",
    },
]


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "pp")) else "---" for _, label in cols) + " |")
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


def classify_option(option_name: str, refined_rate: float) -> tuple[str, str]:
    option = str(option_name)
    if refined_rate <= 1:
        if option == "Phase92 현재 기준":
            return "높음", "Phase92 기준값도 Phase86~93의 상위 actual 총량 정규화·중분류 actual 기반 후보선택 계열을 상속"
        return "높음", "actual 기반 후보 평가를 거쳐 선택된 정밀화 값"
    if option == "Phase92 현재 기준":
        return "중간", "정밀화 신규 후보는 아니지만 Phase92 계열 자체가 사후 actual 기반 평가를 포함"
    return "중간", "actual 기반 후보 평가가 포함된 정밀화 값"


def likely_reason(row: pd.Series) -> str:
    if row["protected_option_name"] == "Phase92 현재 기준":
        return "정밀화 후보 미채택; 기준값 자체가 속보값보다 나쁨"
    if row["protected_exact_worse_than_phase92"]:
        return "취약큐/상위산업 총오차 축소를 우선해 개별 금액오차 증가 허용"
    if row["protected_error_gva_eok"] > row["initial_error_gva_eok"]:
        return "상위총량 정규화와 후보 혼합 과정에서 해당 중분류 배분비 악화"
    return "기타"


def improvement(row: pd.Series) -> str:
    label = str(row["middle_label"])
    cause = str(row.get("cause_group", ""))
    if "건축" in label or "과학기술" in label or "전문 서비스" in label or cause == "전문·지원서비스형":
        return "전문인력·임금총액·용역계약액 등 중분류 직접 활동자료로 별도 후보군 구성"
    if "금융" in label or "보험" in label or cause == "거래·자산형":
        return "거래금액·자산잔액·공시가격·임대면적 기반 거래/자산형 지표로 분리"
    if "제조업" in label or "수리업" in label:
        return "중분류별 출하액·전력·공장면적·대형사업장 규모를 결합하되 지역 핵심산업은 별도 보호"
    if "수도" in label or "하수" in label or "환경" in label:
        return "처리량·시설용량·위탁계약액을 월/분기 활동량으로 사용"
    if "운송" in label or "창고" in label:
        return "여객·화물·창고면적·물동량을 중분류별로 분리"
    return "일괄 보호 기준 대신 해당 상위산업 내부의 직접 활동자료 후보만 허용"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(REGISTRY)
    reg["middle_code"] = reg.middle_code.astype(str).str.zfill(2)
    reg["refined_minus_flash_error_eok"] = reg.protected_error_gva_eok - reg.initial_error_gva_eok
    reg["refined_minus_flash_error_pp"] = reg.protected_error_rate_pct - reg.initial_error_rate_pct
    reg["refined_worse_than_flash"] = reg.refined_minus_flash_error_eok.gt(1e-9)
    reg["within_1pct_refined"] = reg.protected_error_rate_pct.le(1.0)

    risk_pairs = reg.apply(lambda r: classify_option(r.protected_option_name, r.protected_error_rate_pct), axis=1)
    reg["leakage_risk_level"] = [x[0] for x in risk_pairs]
    reg["leakage_risk_reason"] = [x[1] for x in risk_pairs]
    reg["refined_worse_reason"] = reg.apply(likely_reason, axis=1)
    reg["improvement_proposal"] = reg.apply(improvement, axis=1)

    within = reg[reg.within_1pct_refined].sort_values(["city", "protected_error_rate_pct", "protected_error_gva_eok"])
    worse = reg[reg.refined_worse_than_flash].sort_values(["city", "refined_minus_flash_error_eok"], ascending=[True, False])
    summary = (
        reg.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            within_1pct_refined_cells=("within_1pct_refined", "sum"),
            high_leakage_risk_cells=("leakage_risk_level", lambda s: int((s == "높음").sum())),
            refined_worse_than_flash_cells=("refined_worse_than_flash", "sum"),
            flash_error_sum_eok=("initial_error_gva_eok", "sum"),
            refined_error_sum_eok=("protected_error_gva_eok", "sum"),
        )
    )
    summary["flash_wape_pct"] = summary.flash_error_sum_eok / reg.groupby("city").actual_gva_eok.sum().reindex(summary.city).to_numpy() * 100
    summary["refined_wape_pct"] = summary.refined_error_sum_eok / reg.groupby("city").actual_gva_eok.sum().reindex(summary.city).to_numpy() * 100

    pd.DataFrame(LEAKAGE_FINDINGS).to_csv(OUTDIR / "phase104_logic_leakage_findings.csv", index=False, encoding="utf-8-sig")
    reg.to_csv(OUTDIR / "phase104_middle_refinement_audit_registry.csv", index=False, encoding="utf-8-sig")
    within.to_csv(OUTDIR / "phase104_within_1pct_refined_cells.csv", index=False, encoding="utf-8-sig")
    worse.to_csv(OUTDIR / "phase104_refined_worse_than_flash_cells.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase104_refinement_audit_summary.csv", index=False, encoding="utf-8-sig")

    report = f"""# 중분류 정밀화 오차 누수·악화 감사

## 결론

정밀오차 1% 이내 업종은 `사후 정밀화/진단`으로만 해석해야 한다. Phase86~98 계열은 상위산업 actual 총량 정규화와 중분류 actual GVA 대비 후보 평가를 포함하므로, 이 값을 공표 전 예측 성능으로 주장하면 데이터 유출이다. 포스터에서는 속보성 지표와 공표 후 정밀화 지표를 분리해 보여주되, 정밀화의 1% 이내 값을 “예측 성공”으로 표현하지 않는다.

## 도시별 요약

{md_table(summary, [("city", "지역"), ("cells", "중분류 개"), ("within_1pct_refined_cells", "정밀오차 1%이하 개"), ("high_leakage_risk_cells", "고위험 해석 개"), ("refined_worse_than_flash_cells", "정밀화 악화 개"), ("flash_error_sum_eok", "속보오차 억원"), ("refined_error_sum_eok", "정밀오차 억원"), ("flash_wape_pct", "속보 WAPE %"), ("refined_wape_pct", "정밀화 WAPE %")])}

## 로직 감사

{md_table(pd.DataFrame(LEAKAGE_FINDINGS), [("audit_item", "감사항목"), ("logic_location", "코드 위치"), ("finding", "확인내용"), ("risk", "해석위험")])}

## 정밀오차 1% 이하 업종 전수

{md_table(within, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("initial_predicted_gva_eok", "속보성 억원"), ("protected_predicted_gva_eok", "정밀화 억원"), ("initial_error_rate_pct", "속보오차 %"), ("protected_error_rate_pct", "정밀오차 %"), ("protected_option_name", "정밀화 기준"), ("leakage_risk_level", "누수해석 위험"), ("leakage_risk_reason", "판정이유")], 80)}

## 속보오차보다 정밀오차가 큰 업종

{md_table(worse, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("initial_error_gva_eok", "속보오차 억원"), ("protected_error_gva_eok", "정밀오차 억원"), ("refined_minus_flash_error_eok", "악화 억원"), ("initial_error_rate_pct", "속보오차 %"), ("protected_error_rate_pct", "정밀오차 %"), ("protected_option_name", "정밀화 기준"), ("refined_worse_reason", "원인"), ("improvement_proposal", "개선안")], 80)}

## 반영 원칙

1. 포스터의 중분류 표는 실제/속보성/정밀화/속보오차/정밀오차를 함께 보이되, 정밀화는 `공표 후 재산출·진단`으로 설명한다.
2. 정밀오차 1% 이하 업종은 성능 자랑용 문구로 쓰지 않는다.
3. 정밀화가 속보성보다 악화되는 업종은 `정밀화 후보 선택 보호장치 보완 대상`으로 내부 관리한다.
4. 다음 실험에서는 후보 선택을 과거연도 또는 타지역에서만 학습하고, 대상 도시·대상연도의 중분류 actual은 마지막 집계검증에만 사용해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase104_middle_refinement_audit_registry.csv")


if __name__ == "__main__":
    main()
