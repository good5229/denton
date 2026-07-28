#!/usr/bin/env python3
"""Phase222: source request pack for residual high-precision-error industries.

Phase220/221 proved that the currently opened sources do not safely reduce the
remaining residual errors.  This phase packages the next concrete public/free
data requests, including already-tested links, failure reasons, and the exact
GVA residual cells each source would target.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase222_residual_source_request_pack"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase222_residual_source_request_pack.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    residual = pd.read_csv(
        ROOT / "data/processed/phase220_residual_precision_candidate_gate/phase220_guarded_residual_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    residual["middle_code"] = residual["middle_code"].astype(str).str.extract(r"(\d+)")[0].str.zfill(2)

    rows = [
        {
            "우선순위": 1,
            "자료명": "방송산업 실태조사 정보",
            "링크": "https://www.data.go.kr/data/15108104/openapi.do?recommendDataYn=Y",
            "현재상태": "현재 공공데이터포털 키 호출 시 403 Forbidden",
            "필요조치": "활용신청/승인 후 재호출",
            "대상셀": "고양 J60 방송업, 포항 J60 방송업",
            "필요필드": "연도, 방송사업자/지역/매출액, 종사자, 채널·송출·제작 관련 항목",
            "사용방식": "J00 상위 실제 GVA 내부에서 J60 배분근거로 사용 후 J 중분류 actual 집계검증",
            "판정": "가장 직접적인 방송업 정밀화 후보",
        },
        {
            "우선순위": 2,
            "자료명": "금융·보험 지역 활동 금액자료",
            "링크": "금융공공데이터 API 후보 추가 탐색 필요",
            "현재상태": "금융회사 기본정보는 수집됐으나 K66 직접행 0개로 부적합",
            "필요조치": "지역별 보험료/계약건수/판매수수료/금융서비스 매출 API 신청",
            "대상셀": "포항 K66 금융 및 보험 관련 서비스업",
            "필요필드": "시군구, 연도, 보험/금융상품 계약건수, 보험료, 수수료, 영업점 활동금액",
            "사용방식": "K00 상위 실제 GVA 내부에서 K66 배분근거로 사용",
            "판정": "회사 본점 목록이 아니라 영업활동 금액자료 필요",
        },
        {
            "우선순위": 3,
            "자료명": "상하수도 요금수입·총괄원가·운영비 시군구 자료",
            "링크": "KOSIS 행정안전부 상하수도 회계표는 시군구 행 없음",
            "현재상태": "Phase219에서 고양/포항 직접행 없음 확인",
            "필요조치": "지자체/행안부 원천 시군구표 또는 파일자료 확보",
            "대상셀": "고양 ERS37, 포항 ERS36/37",
            "필요필드": "시군구, 연도, 급수수익, 사용료수익, 총괄원가, 운영비, 위탁계약액",
            "사용방식": "ERS36/37 내부 배분 및 상위 ERS actual 집계검증",
            "판정": "물량형 처리량보다 GVA에 가까운 금액형 자료 필요",
        },
        {
            "우선순위": 4,
            "자료명": "환경정화·폐기물 계약액/사업비 자료",
            "링크": "환경·폐기물 공공데이터 API는 Phase167 재점검에서도 usable 0",
            "현재상태": "폐기물 처리업체/처분부담금 API 권한 또는 endpoint 문제",
            "필요조치": "폐기물 처리량이 아니라 시군구별 계약액·사업비·처리수수료 자료 확보",
            "대상셀": "포항 ERS39 환경 정화 및 복원업",
            "필요필드": "시군구, 연도/월, 환경정화 계약액, 복원사업비, 처리수수료",
            "사용방식": "ERS39 직접 활동금액으로 정밀화 후 ERS 상위 집계검증",
            "판정": "처리업체 수만으로는 10%권 진입 어려움",
        },
        {
            "우선순위": 5,
            "자료명": "제조업 중분류별 출하액·공장 생산액·임금총액",
            "링크": "https://www.data.go.kr/data/15087611/openapi.do",
            "현재상태": "한국산업단지공단 공장등록 생산정보 endpoint가 404 API not found",
            "필요조치": "최신 endpoint 확인 또는 파일자료/대체 API 확보",
            "대상셀": "고양 C14/C15, 포항 C28/C34",
            "필요필드": "시군구, KSIC 중분류, 출하액, 생산액, 종업원수, 임금총액, 공장면적",
            "사용방식": "C00 상위 실제 GVA 내부에서 제조업 중분류 배분 후 C actual 집계검증",
            "판정": "공장 수보다 금액/규모형 지표 필요",
        },
        {
            "우선순위": 6,
            "자료명": "비영리·직능단체 활동규모 자료",
            "링크": "고양시/행안부 비영리민간단체·보조금 공개자료 추가 탐색 필요",
            "현재상태": "LocalData 계열 사후 후보는 좋으나 실제값 기반 그리드라 채택 불가",
            "필요조치": "단체 등록수, 회원수, 보조금, 회비/수입, 종사자 자료 확보",
            "대상셀": "고양 ERS94 협회·단체",
            "필요필드": "행정동/시군구, 연도, 단체유형, 회원수, 보조금, 회비/사업수입",
            "사용방식": "ERS94 직접 활동규모로 정밀화 후 ERS 상위 집계검증",
            "판정": "일반 사업체 수와 구분되는 비영리 활동규모 필요",
        },
        {
            "우선순위": 7,
            "자료명": "정보서비스 매출·플랫폼/데이터센터 활동자료",
            "링크": "공공 무료 API 추가 탐색 필요",
            "현재상태": "포항 J63 actual 규모가 작아 비율오차가 과대; 직접자료 없음",
            "필요조치": "정보서비스 사업체 매출/서버·플랫폼 활동량 자료 확보",
            "대상셀": "포항 J63 정보서비스업",
            "필요필드": "시군구, 연도, KSIC, 매출, 종업원, 서버/플랫폼 활동량",
            "사용방식": "J00 상위 실제 GVA 내부에서 J63 배분근거로 사용",
            "판정": "소액 셀이라 금액오차 기준 병행 필요",
        },
        {
            "우선순위": 8,
            "자료명": "수상운송 실적·매출 자료",
            "링크": "MOF/항만자료는 포항 항만 중심, 고양 H50 직접자료 부족",
            "현재상태": "고양 H50 actual이 매우 작고 직접 해상/수상운송 활동자료 없음",
            "필요조치": "수상여객·화물·운항업체 매출 또는 운항실적 자료 확보",
            "대상셀": "고양 H50 수상 운송업",
            "필요필드": "시군구, 연도/월, 여객, 화물, 운항횟수, 업체매출",
            "사용방식": "H00 내부 배분 및 H 상위 actual 집계검증",
            "판정": "금액 규모가 작아 우선순위는 낮음",
        },
    ]
    requests = pd.DataFrame(rows)
    requests.to_csv(OUT / "phase222_residual_source_request_pack.csv", index=False, encoding="utf-8-sig")

    residual_view = residual[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase220_predicted_gva_eok",
            "phase220_error_rate_pct",
            "needed_direct_data",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase220_predicted_gva_eok": "현재추정_억원",
            "phase220_error_rate_pct": "현재오차_pct",
            "needed_direct_data": "필요자료",
        }
    )
    residual_view.to_csv(OUT / "phase222_residual_cells.csv", index=False, encoding="utf-8-sig")

    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "git_hash": git_hash(),
                "inputs": [
                    "data/processed/phase220_residual_precision_candidate_gate/phase220_guarded_residual_registry.csv",
                    "reports/partial_statistics_estimation_phase219_water_sewer_accounting_feasibility_audit.md",
                    "reports/partial_statistics_estimation_phase221_newly_opened_api_residual_test.md",
                    "public web search / mediastat OpenAPI page check",
                ],
                "outputs": [
                    "phase222_residual_source_request_pack.csv",
                    "phase222_residual_cells.csv",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    REPORT.write_text(
        f"""# Phase222 잔여 정밀오차 자료요청 패키지

생성시각: {CREATED_AT}

## 목적

Phase220/221에서 현재 열려 있는 자료만으로는 잔여 20% 초과 정밀오차를 안전하게 낮출 수 없음을 확인했다. 이번 단계는 추가 수집이 필요한 무료·공개자료 후보를 잔여 업종별로 정리한다.

## 잔여 오차 셀

{md_table(residual_view, 2)}

## 우선 수집/신청 후보

{md_table(requests, 2)}

## 즉시 조치

1. `방송산업 실태조사 정보` API는 고양·포항 J60 방송업에 가장 직접적이다. 현재 키로는 403이므로 활용신청 후 재시도한다.
2. K66은 금융회사 기본정보가 아니라 지역별 보험료·계약건수·수수료 같은 영업활동 금액자료가 필요하다.
3. 상하수도·환경은 처리량/시설용량보다 요금수입·총괄원가·위탁계약액이 필요하다.
4. 제조업 잔여 셀은 공장 수가 아니라 중분류별 출하액·생산액·임금총액 자료가 필요하다.
5. 위 자료가 확보되면 Phase220의 사후선택 제거 게이트를 그대로 적용해 정밀오차를 다시 계산한다.
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
