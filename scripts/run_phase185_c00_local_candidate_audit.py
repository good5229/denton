#!/usr/bin/env python3
"""Phase185: C00 local candidate audit after Phase179.

This phase audits whether existing local manufacturing activity sources can
improve the remaining C00 errors without violating Phase183 guardrails.

It does not change the operational prediction.  The goal is to prevent unsafe
"looks better on Pohang/Goyang target actual" adoption and to identify the next
data collection gap for each weak manufacturing middle industry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase185_c00_local_candidate_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase185_c00_local_candidate_audit.md"

P179 = DATA / "phase179_metadata_guarded_middle_gate" / "phase179_metadata_guarded_registry.csv"
P120 = DATA / "phase120_finance_procurement_source_integration" / "phase120_candidate_registry.csv"
P170_C00_SUM = DATA / "phase170_pohang_port_cargo_split_diagnostic" / "phase170_c00_steel_cargo_summary.csv"
P170_C00_DETAIL = DATA / "phase170_pohang_port_cargo_split_diagnostic" / "phase170_c00_steel_cargo_detail.csv"
P71_SUM = DATA / "phase71_pohang_manufacturing_stabilization" / "phase71_pohang_manufacturing_stabilization_summary.csv"
P109_REC = DATA / "phase109_goyang_pohang_gt10_precision_improvement" / "phase109_manufacturing_blend_recommendation.csv"
P184_MATRIX = DATA / "phase184_local_activity_source_availability" / "phase184_local_source_availability_matrix.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.DataFrame()


def md_table(rows: list[dict[str, Any]], cols: list[tuple[str, str]]) -> str:
    out = ["| " + " | ".join(h for _, h in cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        vals = []
        for key, _ in cols:
            val = str(row.get(key, ""))
            vals.append(val.replace("|", "/").replace("\n", " ")[:240])
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def need_for_middle(code: int, label: str, city: str) -> tuple[str, str]:
    if code in {10, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 26, 27, 28, 29, 30, 31, 32, 33}:
        if code in {10, 14, 15, 16, 17, 18, 21, 26, 27, 30, 32, 33}:
            return (
                "공장등록 생산품·공장면적·종업원 + 산업용 전력 중분류 매핑",
                "소규모/다품종 제조업은 2021 제조업 부가가치 구조만으로 2023 지역 산업구조를 따라가지 못함",
            )
        if code in {23, 29}:
            return (
                "공장규모·전력 + 지역 수요/건설·설비투자 보조",
                "비금속·기계장비는 지역 프로젝트/투자 수요 영향이 커서 공장 수만으로 부족",
            )
        return (
            "중분류별 생산품 매핑 + 전력/고용 결합",
            "현재 후보가 중분류 내 생산성 차이를 충분히 반영하지 못함",
        )
    if code == 34:
        return (
            "수리업 사업장·정비계약·대형 설비 보유 사업장 자료",
            "산업용 기계 수리업은 제조업 생산이 아니라 유지보수 서비스 성격이 강해 공장 생산품 지표와 괴리",
        )
    return ("중분류 직접 활동자료", "잔여오차 원인 추가 진단 필요")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    p179 = read_csv(P179)
    p120 = read_csv(P120)
    p170_sum = read_csv(P170_C00_SUM)
    p170_detail = read_csv(P170_C00_DETAIL)
    p71_sum = read_csv(P71_SUM)
    p109 = read_csv(P109_REC)
    p184 = read_csv(P184_MATRIX)

    if p179.empty:
        raise SystemExit(f"missing {P179}")

    c00 = p179[p179["parent_code"].eq("C00")].copy()
    c00["gt20"] = c00["phase179_error_rate_pct"] > 20
    c00_summary = (
        c00.groupby("city")
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("phase179_error_gva_eok", "sum"),
            gt20_cells=("gt20", "sum"),
            gt50_cells=("phase179_error_rate_pct", lambda s: int((s > 50).sum())),
        )
        .reset_index()
    )
    c00_summary["wape_pct"] = (c00_summary["error_sum_eok"] / c00_summary["actual_sum_eok"] * 100).round(2)
    c00_summary[["actual_sum_eok", "error_sum_eok"]] = c00_summary[["actual_sum_eok", "error_sum_eok"]].round(2)
    c00_summary_path = OUT / "phase185_c00_phase179_summary.csv"
    c00_summary.to_csv(c00_summary_path, index=False, encoding="utf-8-sig")

    residual = c00[c00["gt20"]].copy()
    rows = []
    for _, r in residual.sort_values(["phase179_error_gva_eok"], ascending=False).iterrows():
        source_gap, diagnosis = need_for_middle(int(r["middle_code"]), str(r["middle_label"]), str(r["city"]))
        rows.append(
            {
                "city": r["city"],
                "middle_code": int(r["middle_code"]),
                "middle_label": r["middle_label"],
                "actual_gva_eok": round(float(r["actual_gva_eok"]), 2),
                "phase179_predicted_gva_eok": round(float(r["phase179_predicted_gva_eok"]), 2),
                "phase179_error_gva_eok": round(float(r["phase179_error_gva_eok"]), 2),
                "phase179_error_rate_pct": round(float(r["phase179_error_rate_pct"]), 2),
                "needed_activity_data": source_gap,
                "diagnosis": diagnosis,
            }
        )
    residual_df = pd.DataFrame(rows)
    residual_path = OUT / "phase185_c00_residual_middle_routebook.csv"
    residual_df.to_csv(residual_path, index=False, encoding="utf-8-sig")

    p120_cmp = pd.DataFrame()
    if not p120.empty:
        key = ["city", "parent_code", "middle_code"]
        p120_cmp = c00[key + ["middle_label", "actual_gva_eok", "phase179_error_gva_eok", "phase179_error_rate_pct"]].merge(
            p120[key + ["phase120_candidate_error_gva_eok", "phase120_candidate_error_rate_pct", "phase120_candidate_option_id"]],
            on=key,
            how="left",
        )
        p120_cmp["delta_p120_vs_p179_eok"] = p120_cmp["phase120_candidate_error_gva_eok"] - p120_cmp["phase179_error_gva_eok"]
        p120_cmp_path = OUT / "phase185_phase120_vs_phase179_c00.csv"
        p120_cmp.to_csv(p120_cmp_path, index=False, encoding="utf-8-sig")
    else:
        p120_cmp_path = OUT / "phase185_phase120_vs_phase179_c00.csv"
        p120_cmp_path.write_text("", encoding="utf-8")

    candidate_rows: list[dict[str, Any]] = []
    if not p120_cmp.empty:
        candidate_rows.append(
            {
                "candidate": "Phase120 KOSIS 제조업 2021 부가가치 구조",
                "scope": "고양·포항 C00 전체",
                "evidence": f"Phase179 C00와 동일: max_delta={p120_cmp['delta_p120_vs_p179_eok'].abs().max():.6f}억원",
                "adoption_decision": "이미 Phase179 기준선에 반영됨; 추가 개선 아님",
            }
        )
    if not p170_sum.empty:
        best = p170_sum.sort_values("wape_pct").iloc[0]
        candidate_rows.append(
            {
                "candidate": str(best.get("candidate", "Phase170 port cargo")),
                "scope": "포항 C00 철강·광물 물동량 진단",
                "evidence": f"WAPE={float(best.get('wape_pct', 0)):.2f}%, gt20={int(best.get('gt20_cells', 0))}, status={best.get('adoption_status', '')}",
                "adoption_decision": "포항 철강/광물 진단 후보. C00 전체 또는 고양 적용 금지; 외부 항만도시 검증 전 운영 채택 금지",
            }
        )
    if not p71_sum.empty:
        best = p71_sum.sort_values("manufacturing_wape_pct").iloc[0]
        candidate_rows.append(
            {
                "candidate": str(best.get("candidate", "Phase71 factory area")),
                "scope": "포항 제조업 공장면적 안정화",
                "evidence": f"WAPE={float(best.get('manufacturing_wape_pct', 0)):.2f}%, C24오차율={float(best.get('primary_metal_error_rate_pct', 0)):.2f}%",
                "adoption_decision": "현 Phase179보다 잔여 C00 개선 근거로 약함; 단독 채택 금지",
            }
        )
    if not p109.empty:
        for _, r in p109.iterrows():
            candidate_rows.append(
                {
                    "candidate": f"Phase109 {r.get('metric')} alpha={r.get('alpha')}",
                    "scope": f"{r.get('city')} legacy manufacturing blend",
                    "evidence": f"baseline WAPE={float(r.get('baseline_wape_pct', 0)):.2f}%, candidate WAPE={float(r.get('candidate_wape_pct', 0)):.2f}%, worse_cells={int(r.get('worse_cells', 0))}",
                    "adoption_decision": f"{r.get('recommendation')}; Phase183 no-worse/target-actual guard 재검증 전 채택 금지",
                }
            )
    candidate_df = pd.DataFrame(candidate_rows)
    candidate_path = OUT / "phase185_c00_candidate_adoption_audit.csv"
    candidate_df.to_csv(candidate_path, index=False, encoding="utf-8-sig")

    local_c00 = p184[p184["blocks"].astype(str).str.contains("C00", regex=False)].copy() if not p184.empty else pd.DataFrame()
    local_c00_path = OUT / "phase185_c00_local_source_subset.csv"
    local_c00.to_csv(local_c00_path, index=False, encoding="utf-8-sig")

    report = f"""# Phase185 C00 제조업 로컬 후보 채택 감사

## 목적

Phase184에서 C00 제조업은 네트워크 없이도 공장등록·전력·항만·개인사업자 계열 로컬 자료가 있는 것으로 확인됐다. Phase185는 이 자료와 기존 제조업 실험 결과가 Phase179 이후 남은 C00 오차를 **안전하게** 줄일 수 있는지 감사한다.

이번 단계는 새 예측값을 운영 기준선에 반영하지 않는다. Phase183 규칙에 따라 target actual만 보고 좋아 보이는 후보, 외부검증 전 후보, 중분류 구분 없이 C00 전체에 덮는 후보를 걸러낸다.

## Phase179 C00 현재 성능

{md_table(c00_summary.to_dict("records"), [
    ("city", "지역"),
    ("cells", "중분류 셀"),
    ("actual_sum_eok", "실제합계(억원)"),
    ("error_sum_eok", "오차합계(억원)"),
    ("wape_pct", "WAPE(%)"),
    ("gt20_cells", "20%초과"),
    ("gt50_cells", "50%초과"),
])}

## C00 20% 초과 잔여 중분류

{md_table(residual_df.to_dict("records"), [
    ("city", "지역"),
    ("middle_code", "코드"),
    ("middle_label", "중분류"),
    ("actual_gva_eok", "실제(억원)"),
    ("phase179_predicted_gva_eok", "추정(억원)"),
    ("phase179_error_gva_eok", "오차(억원)"),
    ("phase179_error_rate_pct", "오차율(%)"),
    ("needed_activity_data", "필요 활동자료"),
    ("diagnosis", "진단"),
])}

## 기존 C00 후보 채택 감사

{md_table(candidate_df.to_dict("records"), [
    ("candidate", "후보"),
    ("scope", "범위"),
    ("evidence", "증거"),
    ("adoption_decision", "채택 판정"),
])}

## 로컬 C00 자료

{md_table(local_c00.to_dict("records"), [
    ("source_id", "자료ID"),
    ("rows", "행"),
    ("detected_spatial", "공간"),
    ("detected_temporal", "시간"),
    ("industry_track", "산업/트랙"),
    ("caveat", "제한"),
]) if not local_c00.empty else "- Phase184 C00 자료 subset 없음."}

## 판정

1. Phase179의 C00는 이미 Phase120의 KOSIS 제조업 2021 부가가치 구조 후보와 동일하다. 따라서 같은 후보를 다시 적용해도 추가 개선은 없다.
2. 포항항 철강·광물 물동량 후보는 포항 C00 일부에는 강한 설명력을 보이나, 현재 잔여 고오차의 상당수는 C24가 아니라 식료품·비금속·기계수리·전자·가구 등이다. 항만 물동량을 C00 전체에 덮으면 Phase183의 업종군 일괄 보정 금지 원칙을 위반한다.
3. 공장면적 단독 후보는 기존 Phase71에서 포항 제조업 WAPE가 높아 단독 채택이 어렵다. 다만 공장등록 생산품·면적·종업원과 전력을 중분류별로 결합하는 다음 실험의 재료로는 유효하다.
4. C00 다음 개선은 **중분류별 제한 라우팅**이어야 한다.
   - 고양: 식료품, 전자부품·컴퓨터, 가구, 기타제품, 비금속, 인쇄, 의복/가죽 등은 공장등록 생산품/면적/종업원 + 전력 결합 후보.
   - 포항: 산업용 기계 수리업은 제조 생산품보다 정비계약/대형설비 보유 사업장 자료가 필요.
   - 포항 비금속·기계장비는 공장규모+전력+지역 프로젝트 수요 결합 후보.
5. 네트워크 없이 바로 할 수 있는 다음 실험은 C00 전체 보정이 아니라, 공장등록·전력 기반 **중분류별 후보 screen**을 만들고 외부 도시 또는 상위 제조업 집계검증으로 채택 여부를 가르는 방식이다.

## 산출물

- C00 현재 요약: `{c00_summary_path.relative_to(ROOT)}`
- C00 잔여 중분류 라우트북: `{residual_path.relative_to(ROOT)}`
- 기존 후보 채택 감사: `{candidate_path.relative_to(ROOT)}`
- Phase120 비교: `{p120_cmp_path.relative_to(ROOT)}`
- 로컬 C00 자료 subset: `{local_c00_path.relative_to(ROOT)}`
"""

    REPORT.write_text(report, encoding="utf-8")
    manifest = {
        "phase": 185,
        "c00_rows": int(len(c00)),
        "c00_residual_gt20": int(len(residual_df)),
        "candidate_audits": int(len(candidate_df)),
        "outputs": [
            str(c00_summary_path.relative_to(ROOT)),
            str(residual_path.relative_to(ROOT)),
            str(candidate_path.relative_to(ROOT)),
            str(p120_cmp_path.relative_to(ROOT)),
            str(local_c00_path.relative_to(ROOT)),
            str(REPORT.relative_to(ROOT)),
        ],
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
