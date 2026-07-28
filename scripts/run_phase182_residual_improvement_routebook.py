#!/usr/bin/env python3
"""Phase182: build a residual improvement routebook after Phase179/180.

This phase does not change predictions.  It converts the remaining high-error
middle-industry cells into a modelling/source routebook so that the next
collection round can be targeted and auditable.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IN_RESIDUAL = ROOT / "data" / "processed" / "phase180_residual_source_retriage" / "phase180_residual_cells_retriaged.csv"
IN_BLOCK = ROOT / "data" / "processed" / "phase180_residual_source_retriage" / "phase180_source_priority_by_block.csv"
IN_SUMMARY = ROOT / "data" / "processed" / "phase179_metadata_guarded_middle_gate" / "phase179_summary.csv"
IN_KOBIS_J59 = ROOT / "data" / "processed" / "phase136_kobis_boxoffice_temporal_proxy" / "phase136_goyang_j59_route_decision.csv"
OUT = ROOT / "data" / "processed" / "phase182_residual_improvement_routebook"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase182_residual_improvement_routebook.md"


def parent_block(parent_code: str) -> str:
    return {
        "MN0": "전문·사업지원",
        "ERS": "환경·수도·개인서비스",
        "C00": "제조업",
        "J00": "정보통신·콘텐츠",
        "K00": "금융·보험",
        "H00": "운수·창고",
    }.get(parent_code, parent_code)


def route(row: pd.Series) -> dict[str, str]:
    parent = str(row["parent_code"])
    mid = int(row["middle_code"])
    label = str(row["middle_label"])
    city = str(row["city"])
    stale = bool(row["stale_meta_flag"])
    small_base = float(row["actual_gva_eok"]) < 300

    if parent == "MN0":
        if mid in {70, 71, 72, 73}:
            return {
                "root_cause": "전문인력·용역계약 금액 축 누락",
                "source_pack": "조달청 계약/낙찰금액, 조달업체 업종·공급물품, 연구개발·전문인력, 임금총액",
                "model_action": "중분류별 계약금액/전문인력 결합지표를 만들고, 외부 도시 LOO 게이트를 통과한 경우에만 Phase179 값을 대체",
                "api_dependency": "조달청 공공데이터개방표준서비스, 조달청 사용자정보서비스, 금융공공데이터 사업자 기본/매출",
            }
        return {
            "root_cause": "시설관리·임대·사업지원의 서비스 활동량이 사업체 수와 불일치",
            "source_pack": "LOCALDATA 인허가·영업상태, 조달 계약금액, 사업장 규모·종사자, 시설관리/임대 품목명",
            "model_action": "사업체 수 대신 영업중 사업장×계약금액×종사자 축의 보수적 앙상블, 악화 방지 게이트 적용",
            "api_dependency": "조달청 계약/낙찰, LOCALDATA 파일/API, 금융공공데이터 개인사업자 기본/매출",
        }

    if parent == "ERS":
        if mid in {36, 37, 38, 39}:
            return {
                "root_cause": "시설 수가 아니라 처리량·시설용량·위탁계약액이 GVA를 좌우",
                "source_pack": "상수도/하수처리량, 폐기물 처리량·처리업체, 처리장 용량, 위탁계약금액",
                "model_action": "E36/E37/E38/E39를 별도 환경처리량 블록으로 분리하고 물량·용량 우선 배분",
                "api_dependency": "한국수자원공사 하수처리장 일일수질, 환경공단 폐기물 API/파일, 지자체 위탁계약",
            }
        return {
            "root_cause": "개인서비스·협회·예술/스포츠는 사업체 수보다 이용자·회원·시설·행사 수요가 중요",
            "source_pack": "인허가 영업상태, 문화·체육시설 이용/면적, 단체·협회 등록, 행사·공연·영화 관람",
            "model_action": "ERS90/91/94/96을 분리하고 KOBIS/시설/인허가 조합으로 공간·시간축을 보강",
            "api_dependency": "KOBIS 가능, KOPIS 불가, 고양시/포항시 공공시설·인허가 자료",
        }

    if parent == "C00":
        return {
            "root_cause": "제조업 중분류별 생산품·공장규모·전력·물동량 차이를 일반 사업체 지표가 흡수하지 못함",
            "source_pack": "공장등록 생산품·업종, 공장면적·종업원, 산업용 전력, 포항항 품목별 물동량",
            "model_action": "C00 전체 일괄 보정 금지; 중분류별 공장등록/전력/물동량 지표를 선택하고 상위 제조업 집계로 검증",
            "api_dependency": "한국산업단지공단 공장등록생산정보, FactoryOn, 전력 데이터, MOF 항만물동량",
        }

    if parent == "J00":
        if mid == 61:
            return {
                "root_cause": "우편·통신은 통신망·가입자·물류처리량이 사업체 수와 약하게 연결",
                "source_pack": "유선통신서비스 통계, 통신국/사업장, 우편·택배 물량, 데이터센터/플랫폼 활동",
                "model_action": "J61을 정보통신 일반 블록에서 분리하고 전국/시도 시간축+지역 구조지표로 제한적 개선",
                "api_dependency": "과기정통부 유선통신서비스 파일, 우편/택배 공개통계 후보 추가 탐색 필요",
            }
        return {
            "root_cause": "콘텐츠·방송·정보서비스는 사업장 위치와 매출 발생지가 다를 수 있음",
            "source_pack": "방송·콘텐츠 사업체, 플랫폼/서버 활동, 출판/영상 사업장, KOBIS 영화관람/매출",
            "model_action": "J58/J59/J60/J62/J63을 서로 분리한다. KOBIS는 Phase136 검증처럼 기존 계절비중보다 나을 때만 J59 시간축에 제한 적용",
            "api_dependency": "KOBIS 사용 가능, KOPIS 사용 불가, 콘텐츠 매출 공개자료 추가 탐색 필요",
        }

    if parent == "K00":
        return {
            "root_cause": "금융·보험 부가가치는 본점/지점 수보다 예수금·대출·보험료·자산운용 규모에 민감",
            "source_pack": "금융회사 지점/본점, 예수금·대출금, 보험료·계약건수, 지역 사업체 금융수요",
            "model_action": "금융회사 기본정보는 구조 보조로만 쓰고, 금액형 지역 금융지표가 없으면 peer 대체를 보수적으로 제한",
            "api_dependency": "금융위원회 금융회사기본정보, 금융공공데이터 세부 금액형 API 추가 확인",
        }

    if parent == "H00":
        return {
            "root_cause": "수상운송은 항만 접근성·선박/화물 물동량이 핵심이나 고양시는 actual 규모가 작아 상대오차가 커짐",
            "source_pack": "항만 물동량, 선박 입출항, 물류창고·운송업 인허가, 여객/화물 처리량",
            "model_action": "항만이 없는 지역은 항만자료 적용 금지; H50/H52 등 중분류별 floor와 지역 적합도 게이트 유지",
            "api_dependency": "MOF 항만물동량, LOCALDATA 물류창고/운송업",
        }

    note = "소규모 actual이라 상대오차가 과대 표시될 수 있음" if small_base else "직접 활동자료 필요"
    if stale:
        note += "; 과거 메타데이터 폐기 필요"
    return {
        "root_cause": note,
        "source_pack": "업종별 직접 활동자료",
        "model_action": "외부 도시 검증 게이트 통과 시에만 대체",
        "api_dependency": "추가 탐색",
    }


def grade(error_rate: float, error_eok: float) -> str:
    if error_rate > 50 or error_eok >= 1000:
        return "1순위"
    if error_rate > 20 or error_eok >= 300:
        return "2순위"
    return "감시"


def md_table(rows: list[dict[str, Any]], cols: list[tuple[str, str]]) -> str:
    out = ["| " + " | ".join(h for _, h in cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        vals = []
        for key, _ in cols:
            val = str(row.get(key, ""))
            vals.append(val.replace("|", "/").replace("\n", " ")[:220])
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    residual = pd.read_csv(IN_RESIDUAL)
    block = pd.read_csv(IN_BLOCK)
    summary = pd.read_csv(IN_SUMMARY) if IN_SUMMARY.exists() else pd.DataFrame()
    kobis = pd.read_csv(IN_KOBIS_J59) if IN_KOBIS_J59.exists() else pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for _, r in residual.iterrows():
        rec = route(r)
        error_rate = float(r["phase179_error_rate_pct"])
        error_eok = float(r["phase179_error_gva_eok"])
        rows.append(
            {
                "city": r["city"],
                "parent_code": r["parent_code"],
                "block": parent_block(str(r["parent_code"])),
                "middle_code": int(r["middle_code"]),
                "middle_label": r["middle_label"],
                "actual_gva_eok": round(float(r["actual_gva_eok"]), 3),
                "phase179_predicted_gva_eok": round(float(r["phase179_predicted_gva_eok"]), 3),
                "phase179_error_gva_eok": round(error_eok, 3),
                "phase179_error_rate_pct": round(error_rate, 3),
                "priority": grade(error_rate, error_eok),
                "stale_meta_flag": bool(r["stale_meta_flag"]),
                "root_cause": rec["root_cause"],
                "source_pack": rec["source_pack"],
                "model_action": rec["model_action"],
                "api_dependency": rec["api_dependency"],
                "phase179_route": r["phase179_route"],
            }
        )

    routebook = pd.DataFrame(rows).sort_values(
        ["priority", "phase179_error_gva_eok", "phase179_error_rate_pct"],
        ascending=[True, False, False],
    )
    routebook_path = OUT / "phase182_residual_routebook.csv"
    routebook.to_csv(routebook_path, index=False, encoding="utf-8-sig")

    by_block = (
        routebook.groupby(["parent_code", "block"], dropna=False)
        .agg(
            residual_cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("phase179_error_gva_eok", "sum"),
            priority1_cells=("priority", lambda x: int((x == "1순위").sum())),
            stale_meta_cells=("stale_meta_flag", "sum"),
        )
        .reset_index()
    )
    by_block["wape_pct"] = by_block["error_sum_eok"] / by_block["actual_sum_eok"] * 100
    for col in ["actual_sum_eok", "error_sum_eok", "wape_pct"]:
        by_block[col] = by_block[col].round(2)
    by_block = by_block.sort_values(["error_sum_eok", "wape_pct"], ascending=[False, False])
    by_block_path = OUT / "phase182_routebook_by_block.csv"
    by_block.to_csv(by_block_path, index=False, encoding="utf-8-sig")

    source_pack = (
        routebook.groupby(["block", "source_pack", "api_dependency", "model_action"], dropna=False)
        .agg(cells=("middle_code", "count"), error_sum_eok=("phase179_error_gva_eok", "sum"))
        .reset_index()
        .sort_values("error_sum_eok", ascending=False)
    )
    source_pack["error_sum_eok"] = source_pack["error_sum_eok"].round(2)
    source_pack_path = OUT / "phase182_source_pack_priority.csv"
    source_pack.to_csv(source_pack_path, index=False, encoding="utf-8-sig")

    top = routebook.head(18).to_dict("records")
    block_rows = by_block.to_dict("records")
    source_rows = source_pack.head(10).to_dict("records")
    stale_count = int(routebook["stale_meta_flag"].sum())
    total_error = float(routebook["phase179_error_gva_eok"].sum())

    summary_text = ""
    if not summary.empty:
        if {"candidate", "city", "wape_pct", "gt20_cells", "gt50_cells", "error_sum_eok"}.issubset(summary.columns):
            display = summary.copy()
            display["wape_pct"] = display["wape_pct"].round(2)
            display["error_sum_eok"] = display["error_sum_eok"].round(1)
            summary_text = md_table(display.to_dict("records"), [
                ("candidate", "후보"),
                ("city", "지역"),
                ("error_sum_eok", "오차합계(억원)"),
                ("wape_pct", "WAPE(%)"),
                ("gt20_cells", "20%초과"),
                ("gt50_cells", "50%초과"),
            ])

    kobis_text = ""
    if not kobis.empty and {"vintage_label", "adopt_for_j59_temporal_nowcast", "best_track", "error_reduction_eok", "decision_note"}.issubset(kobis.columns):
        display_kobis = kobis.copy()
        display_kobis["error_reduction_eok"] = display_kobis["error_reduction_eok"].round(2)
        kobis_text = md_table(display_kobis.to_dict("records"), [
            ("vintage_label", "빈티지"),
            ("adopt_for_j59_temporal_nowcast", "J59 채택"),
            ("best_track", "우수 경로"),
            ("error_reduction_eok", "오차감소(억원)"),
            ("decision_note", "판정"),
        ])

    report = f"""# Phase182 잔여 고오차 업종 개선 라우트북

## 목적

Phase179는 Phase124 대비 악화 셀 없이 총 WAPE를 낮춘 가장 안전한 후보였지만, Phase180에서 여전히 20% 초과 중분류가 56개 남았다. Phase182는 예측값을 새로 만들기 전 단계로, 잔여 고오차 셀을 업종군·원인·필요 공개자료·모형 변경 방식으로 재분류했다.

이 보고서는 **총부가가치(GVA) 추정 성능 개선을 위한 작업지시서**다. 업체 수나 시설 수 자체를 성과로 주장하지 않고, 해당 자료는 중분류/소분류 GVA를 배분·외삽하기 위한 활동자료로만 사용한다.

## 현재 기준 성능

{summary_text if summary_text else "- Phase179 요약 파일을 찾을 수 없어 표 생성을 생략했다."}

## 잔여 오차 블록

{md_table(block_rows, [
    ("block", "업종군"),
    ("residual_cells", "20%초과 셀"),
    ("priority1_cells", "1순위 셀"),
    ("actual_sum_eok", "실제 합계(억원)"),
    ("error_sum_eok", "오차 합계(억원)"),
    ("wape_pct", "WAPE(%)"),
    ("stale_meta_cells", "폐기할 과거판정"),
])}

## 최우선 셀

{md_table(top, [
    ("city", "지역"),
    ("middle_label", "중분류"),
    ("actual_gva_eok", "실제(억원)"),
    ("phase179_predicted_gva_eok", "추정(억원)"),
    ("phase179_error_gva_eok", "오차(억원)"),
    ("phase179_error_rate_pct", "오차율(%)"),
    ("root_cause", "주요 원인"),
    ("source_pack", "필요 활동자료"),
])}

## 활동자료 수집 우선순위

{md_table(source_rows, [
    ("block", "업종군"),
    ("cells", "대상 셀"),
    ("error_sum_eok", "잔여오차(억원)"),
    ("source_pack", "자료 묶음"),
    ("api_dependency", "필요 API/자료"),
    ("model_action", "모형 반영 방식"),
])}

## 이미 검증된 보조지표의 채택/기각 사례

KOBIS는 사용 가능한 공개 API지만, 기존 Phase136 검증에서 고양시 J59 시간축에는 채택하지 않는 것으로 판정됐다. 즉 “자료가 있다”와 “GVA 예측에 도움이 된다”는 별개이며, 다음 실험에서도 이 원칙을 유지해야 한다.

{kobis_text if kobis_text else "- KOBIS Phase136 판정표를 찾지 못해 생략했다."}

## 판정

1. 잔여 56개 셀의 오차 합계는 {total_error:,.1f}억원이다. 이 중 큰 비중은 MN0, ERS, C00에 집중되어 있다.
2. `추가 자료 불필요` 또는 `현행유지가능`으로 남아 있던 과거 메타데이터는 현재 성능과 모순된다. Phase180/182 기준에서는 20% 초과 셀을 모두 **추가개선 필요**로 재분류해야 한다.
3. 다음 실험은 전 산업 일괄 보정이 아니라 다음 순서가 타당하다.
   - 1순위: MN0 전문서비스·사업지원 — 조달 계약/낙찰금액과 전문인력·임금총액 결합.
   - 2순위: ERS 환경·개인서비스 — 처리량/시설용량/영업상태/이용수요 분리.
   - 3순위: C00 제조업 — 공장등록 생산품·공장규모·전력·항만물동량 중분류 선택.
   - 4순위: J00/K00/H00 — KOBIS·통신·금융·항만 자료를 업종별로 제한 적용.
4. 모든 대체는 고양/포항 target actual을 선택 기준으로 쓰지 않고, 외부 도시 leave-one-out 또는 상위산업 집계검증을 통과할 때만 적용한다.
5. 공표시점이 확인되지 않은 자료는 속보성 지표에서 제외하고 정밀화 지표에만 사용한다.

## Phase181 API 점검과 연결

Phase181 스크립트는 공장등록, 조달 계약/낙찰, 금융회사 기본정보, 하수처리장 일일수질 API를 소량 점검하도록 준비되어 있다. 현재 Codex 네트워크 실행은 사용량 제한으로 승인되지 않았으므로, 다음 실행 가능 시점에 아래 명령을 먼저 실행한다.

```bash
.venv/bin/python scripts/probe_phase181_priority_public_activity_apis.py
```

`ok_items`가 확인된 자료만 실제 수집 단계로 이동한다. `Forbidden`이면 활용승인-인증키 연결 또는 승인 반영 지연으로 보고, 해당 링크를 사용자에게 다시 전달한다.

## 산출물

- 셀별 라우트북: `{routebook_path.relative_to(ROOT)}`
- 블록별 요약: `{by_block_path.relative_to(ROOT)}`
- 자료묶음 우선순위: `{source_pack_path.relative_to(ROOT)}`
"""

    REPORT.write_text(report, encoding="utf-8")
    manifest = {
        "phase": 182,
        "inputs": [str(IN_RESIDUAL.relative_to(ROOT)), str(IN_BLOCK.relative_to(ROOT)), str(IN_SUMMARY.relative_to(ROOT)), str(IN_KOBIS_J59.relative_to(ROOT))],
        "outputs": [str(routebook_path.relative_to(ROOT)), str(by_block_path.relative_to(ROOT)), str(source_pack_path.relative_to(ROOT)), str(REPORT.relative_to(ROOT))],
        "residual_cells": int(len(routebook)),
        "stale_meta_cells": stale_count,
        "total_error_eok": total_error,
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
