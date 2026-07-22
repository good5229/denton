#!/usr/bin/env python3
"""Phase102: split GVA products into flash and accuracy-refinement tracks.

The recent poster tables exposed a conceptual problem: very small final errors
can be produced by retrospective structural calibration, but those values are
not necessarily available at a monthly/quarterly prediction origin.  This phase
formalises a two-track policy:

* flash track: only information knowable as of the prediction origin;
* accuracy-refinement track: after annual/structural data are published, use
  them to improve the allocation and audit gaps.

The primary target remains GVA.  The track label defines the allowed claim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase102_dual_track_release_policy"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase102_dual_track_release_policy.md"
PHASE98 = DATA / "phase98_final_middle_industry_accuracy_registry" / "phase98_final_middle_industry_accuracy_registry.csv"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append(
        "| "
        + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "pp")) else "---" for _, label in cols)
        + " |"
    )
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


def source_policy_table() -> pd.DataFrame:
    rows = [
        {
            "source_family": "월별 인허가·폐업·행정 이벤트",
            "examples": "LOCALDATA, 건축 인허가·착공·사용승인, 버스 승하차, 전력 사용량",
            "knowledge_time": "이벤트월 이후 단기 지연 또는 API 조회시점",
            "flash_use": "가능: 공표/조회 가능월까지만",
            "refinement_use": "가능",
            "claim": "월 변화·경보·방향성 지표",
            "leakage_guard": "관측월이 아니라 조회 가능일 또는 보수적 지연월로 필터",
        },
        {
            "source_family": "당해 연도 연간 GVA·GRDP 총량",
            "examples": "KOSIS 지역계정, 시도/시군구 연간 부가가치",
            "knowledge_time": "대체로 목표연도 종료 후 장기 지연",
            "flash_use": "불가",
            "refinement_use": "가능",
            "claim": "상위합계 고정·사후 정밀화",
            "leakage_guard": "전월·전분기 추정 origin에서는 금지",
        },
        {
            "source_family": "경제총조사·사업체조사·광업제조업 구조자료",
            "examples": "중분류 매출·사업체·종사자, 포항 2024 사업체조사",
            "knowledge_time": "조사 기준연도 이후 공표",
            "flash_use": "과거 공표연도만 가능",
            "refinement_use": "가능",
            "claim": "산업 내부 구조 보정",
            "leakage_guard": "목표연도 또는 차후 조사자료를 조기 사용 금지",
        },
        {
            "source_family": "실제 중분류 GVA·숨김검증 actual",
            "examples": "actual_gva_eok, peer actual/predicted ratio, 후보 선택용 actual",
            "knowledge_time": "평가·검증 시점",
            "flash_use": "불가",
            "refinement_use": "검증·보정 후보 평가만 가능",
            "claim": "사후 집계검증·오차진단",
            "leakage_guard": "모형 입력이 아니라 평가값으로만 사용",
        },
        {
            "source_family": "동년 전체 행정동/구 산업분포",
            "examples": "2023 읍면동×중분류, 2024 구×중분류 매출",
            "knowledge_time": "해당 조사/집계 공표 이후",
            "flash_use": "불가 또는 과거연도만 가능",
            "refinement_use": "가능",
            "claim": "공간 구조 정밀화",
            "leakage_guard": "예측 대상 기간 이후 전체 구조를 조기 사용 금지",
        },
    ]
    return pd.DataFrame(rows)


def cell_track_audit(reg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    reg = reg.copy()
    reg["too_precise_flag"] = reg.protected_error_rate_pct.le(1)
    reg["large_raw_to_final_drop"] = reg.initial_error_rate_pct.sub(reg.protected_error_rate_pct).gt(20)
    reg["actual_selected_flag"] = reg.protected_option_name.astype(str).str.contains("Phase92|사업체조사|현재기준", na=False)
    reg["claim_track"] = np.select(
        [
            reg.too_precise_flag & reg.large_raw_to_final_drop,
            reg.protected_error_rate_pct.gt(10) | reg.protected_error_gva_eok.gt(500),
        ],
        [
            "정확성 개선 전용: 사후 구조보정 결과",
            "정확성 개선 후에도 주의/자료보강",
        ],
        default="정확성 개선 기준 활용후보",
    )
    reg["flash_claim_allowed"] = "N"
    reg["flash_claim_reason"] = "Phase98 protected 값은 actual 비교·상위합계·사후 구조자료 기반 검증 레지스트리이므로 전월/전분기 속보 성능으로 주장 금지"
    suspicious = reg[reg.too_precise_flag | reg.large_raw_to_final_drop].sort_values(
        ["city", "protected_error_rate_pct", "protected_error_gva_eok"]
    )
    remaining = reg[reg.protected_error_rate_pct.gt(10) | reg.protected_error_gva_eok.gt(500)].sort_values(
        ["city", "protected_error_gva_eok"], ascending=[True, False]
    )
    summary = (
        reg.groupby(["city", "claim_track"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("protected_error_gva_eok", "sum"),
            median_error_pct=("protected_error_rate_pct", "median"),
        )
        .sort_values(["city", "claim_track"])
    )
    summary["wape_pct"] = summary.error_sum_eok / summary.actual_sum_eok * 100
    return suspicious, remaining, summary


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(PHASE98, dtype={"middle_code": str})
    reg["middle_code"] = reg.middle_code.astype(str).str.zfill(2)
    sources = source_policy_table()
    suspicious, remaining, summary = cell_track_audit(reg)

    sources.to_csv(OUTDIR / "phase102_source_track_policy.csv", index=False, encoding="utf-8-sig")
    suspicious.to_csv(OUTDIR / "phase102_too_precise_cell_audit.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase102_remaining_over10_or_large_gap.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase102_claim_track_summary.csv", index=False, encoding="utf-8-sig")

    report = f"""# GVA 속보성 지표와 정확성 개선 지표 분리 정책

## 목적

총부가가치(GVA)를 전월·전분기 단위로 빠르게 추정하는 일과, 연간·구조 자료가 모두 공표된 뒤 더 정확하게 재배분하는 일은 같은 작업이 아니다. 이번 단계에서는 고양시·포항시 포스터와 산출물을 `속보성 지표`와 `정확성 개선 지표`로 분리한다.

## 두 단계 정의

| 단계 | 사용 시점 | 허용 자료 | 금지 자료 | 허용 주장 |
| --- | --- | --- | --- | --- |
| 속보성 지표 | 전월·전분기 추정 시점 | 예측 기준일 이전에 공표/조회 가능한 월별 행정·활동자료, 과거연도 구조자료 | 당해연도 연간 GVA, 아직 공표되지 않은 사업체조사·경제총조사, actual 기반 보정계수 | 월 변화, 위험 신호, 우선점검 후보 |
| 정확성 개선 지표 | 연간·구조 자료 공표 이후 | 공식 상위 GVA, 경제총조사·사업체조사, 중분류 실제와의 집계검증 | 속보 성능 주장, 공표 전 자료 조기 사용 | 사후 정밀화, 실제-추정 격차 진단, 자료보강 우선순위 |

## 자료군별 사용 정책

{md_table(sources, [("source_family", "자료군"), ("examples", "예시"), ("knowledge_time", "알 수 있는 시점"), ("flash_use", "속보 사용"), ("refinement_use", "정확성 개선 사용"), ("claim", "허용 주장"), ("leakage_guard", "누수 방지")])}

## 너무 작은 오차에 대한 감사

아래 항목은 최종 오차가 작더라도 전월·전분기 예측력으로 주장하면 안 된다. 원시오차가 컸는데 최종오차가 급감한 항목은 상위합계·사후 구조보정·actual 기반 후보 선택의 영향을 받았을 가능성이 크므로 `정확성 개선 전용`으로 분리한다.

{md_table(suspicious, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("initial_error_rate_pct", "원시오차 %"), ("protected_error_rate_pct", "최종오차 %"), ("protected_error_gva_eok", "최종오차 억원"), ("protected_option_name", "최종 기준"), ("claim_track", "판정")], 40)}

## 트랙별 셀 요약

{md_table(summary, [("city", "지역"), ("claim_track", "판정"), ("cells", "중분류 개"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "WAPE %"), ("median_error_pct", "중앙오차 %")])}

## 정확성 개선 후에도 10% 초과 또는 금액격차가 남은 산업

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("protected_predicted_gva_eok", "추정 억원"), ("protected_error_gva_eok", "오차 억원"), ("protected_error_rate_pct", "오차 %"), ("required_next_data", "필요 자료")], 50)}

## 운영 제안

1. 포스터와 제출자료에는 `정확하게 예측`이라는 표현을 쓰지 않는다. 대신 `속보성 경보`와 `공표 후 정밀화`를 분리한다.
2. 전월·전분기 추정에서는 공식 연간 GVA와 동년 전체 구조자료를 쓰지 않는다. 월별 인허가, 전력, 교통, 건축 이벤트처럼 예측 기준일 이전 자료만 사용한다.
3. 연간 자료가 공표된 뒤에는 정확성 개선 지표로 재산출한다. 이때 상위 총량과 중분류 실제값을 이용한 집계검증은 허용되지만, 그 결과를 과거 시점의 속보 성능으로 소급 주장하지 않는다.
4. 10% 초과 산업은 속보 단계에서 수치 확정값이 아니라 `주의·자료보강`으로 표시하고, 정확성 개선 단계에서 직접 활동자료를 추가한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase102_claim_track_summary.csv")


if __name__ == "__main__":
    main()
