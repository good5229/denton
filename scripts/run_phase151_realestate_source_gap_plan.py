#!/usr/bin/env python3
"""Phase151 source-gap plan for real-estate small split generalization.

Phase150 showed that the two-city routed rule can look good ex post, while
common non-routed candidates miss the 10% target.  This phase does not claim a
new performance number.  It records the free/public source candidates needed to
move from a two-city diagnostic to a defensible general model.
"""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase151_realestate_source_gap_plan"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase151_realestate_source_gap_plan.md"


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_해당 없음_"
    out = df.fillna("").astype(str)
    cols = list(out.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in out.iterrows():
        lines.append("| " + " | ".join(row[col].replace("|", "\\|") for col in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = pd.DataFrame(
        [
            {
                "priority": "상",
                "source_name": "국토교통부_실거래가 정보",
                "url": "https://www.data.go.kr/data/3050988/fileData.do",
                "access_type": "기관 자체 CSV 다운로드",
                "free": "예",
                "key_or_approval": "대체로 키 불필요. 자동화 가능성 별도 확인",
                "coverage": "매매·임대차, 여러 건물유형, 계약일 기준",
                "phase151_use": "전월세·비아파트·오피스텔·상업업무용까지 포함해 681/682 split의 거래서비스축 보강",
                "as_of_risk": "계약일 기준 다운로드라 과거 as-of 재현에는 공표/반영시차 감사 필요",
                "request_to_user": "자동 다운로드가 막히면 rt.molit.go.kr 다운로드 절차 확인 필요",
            },
            {
                "priority": "상",
                "source_name": "국토교통부_아파트 매매 실거래가 자료",
                "url": "https://www.data.go.kr/data/15126469/openapi.do",
                "access_type": "공공데이터포털 OpenAPI",
                "free": "예",
                "key_or_approval": "기존 DATA_GO_KR 키 사용 가능 확인됨",
                "coverage": "아파트 매매. 2023 이후 rgstDate 일부 제공",
                "phase151_use": "현재 Phase149/150의 거래축. 단독 사용 금지, benchmark로 유지",
                "as_of_risk": "2020~2022 rgstDate 원천 미공개",
                "request_to_user": "추가 키 불필요",
            },
            {
                "priority": "상",
                "source_name": "국토교통부 실거래 관련 API 13종",
                "url": "https://www.data.go.kr/tcs/dss/selectDataSetList.do?dType=API&detailKeyword=&keyword=&publicData=",
                "access_type": "공공데이터포털 OpenAPI 검색·활용신청",
                "free": "예",
                "key_or_approval": "아파트 전월세, 연립다세대 전월세, 오피스텔 매매/전월세, 상업업무용 매매 등 개별 신청 필요 가능",
                "coverage": "부동산 거래/임대차 세부 유형",
                "phase151_use": "682 관련 서비스업의 거래·중개 활동을 건물유형별로 분리",
                "as_of_risk": "각 API별 등록일·수정일·등기/확정일자 공개범위 확인 필요",
                "request_to_user": "신청 페이지에서 전월세·오피스텔·상업업무용 API가 미승인이라면 활용신청 필요",
            },
            {
                "priority": "중",
                "source_name": "국토교통부_공동주택 단지 목록제공 서비스",
                "url": "https://www.data.go.kr/data/15057332/openapi.do",
                "access_type": "공공데이터포털 OpenAPI",
                "free": "예",
                "key_or_approval": "활용신청 필요 가능",
                "coverage": "K-APT 가입 공동주택 단지 목록, 법정동/도로명 기반",
                "phase151_use": "681 재고축의 단지·세대 stock 보강 및 행정동/법정동 공간배분 보조",
                "as_of_risk": "실시간 stock 성격. 과거 snapshot 복원 가능성 낮음",
                "request_to_user": "미승인 시 활용신청",
            },
            {
                "priority": "중",
                "source_name": "국토교통부_공동주택 기본 정보제공 서비스",
                "url": "https://www.data.go.kr/data/15058453/openapi.do",
                "access_type": "공공데이터포털 OpenAPI",
                "free": "예",
                "key_or_approval": "활용신청 필요 가능",
                "coverage": "단지 관리방식, 연면적, 동수, 세대수, 관리인원 등",
                "phase151_use": "682 관리서비스축 및 681 stock축 분리",
                "as_of_risk": "현재/실시간 성격. 정밀화 구조자료로 우선 사용",
                "request_to_user": "미승인 시 활용신청",
            },
            {
                "priority": "중",
                "source_name": "국토교통부_부동산개발업정보(WMS/WFS/속성정보)",
                "url": "https://www.data.go.kr/data/15123996/openapi.do",
                "access_type": "VWorld LINK API",
                "free": "예",
                "key_or_approval": "VWorld API key 필요 가능",
                "coverage": "부동산개발업 기본정보·사무소 등 공간정보",
                "phase151_use": "681 개발·공급업 stock/사업자 축 보강",
                "as_of_risk": "현재 snapshot이면 과거 검증에는 구조자료로만 사용",
                "request_to_user": "VWorld key가 없으면 발급 필요",
            },
            {
                "priority": "중",
                "source_name": "국토교통부_개별주택가격정보(WMS/WFS/속성정보)",
                "url": "https://www.data.go.kr/data/15124006/openapi.do",
                "access_type": "VWorld LINK API",
                "free": "예",
                "key_or_approval": "VWorld API key 필요 가능",
                "coverage": "개별주택가격·공간정보",
                "phase151_use": "아파트 공시가격 편중을 낮추고 단독/다가구 stock축 보강",
                "as_of_risk": "연간 공시 기준일/공표일 확인 필요",
                "request_to_user": "VWorld key가 없으면 발급 필요",
            },
        ]
    )
    sources.to_csv(OUT / "phase151_realestate_source_candidates.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "phase": "phase151_realestate_source_gap_plan",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "outputs": [
            "phase151_realestate_source_candidates.csv",
            str(REPORT.relative_to(ROOT)),
        ],
        "scope": "No new performance claim; source plan for 681/682 generalization and future 10-city validation.",
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = f"""# Phase151 부동산업 소분류 일반화 자료 공백 계획

## 목적

Phase150은 두 도시 사후 라우팅을 쓰면 10% 이내처럼 보이지만, 공통 후보는 목표에 미달한다는 결론을 냈다. 따라서 다음 단계는 새 성능 수치를 주장하는 것이 아니라, `681 부동산 임대 및 공급업`과 `682 부동산 관련 서비스업`을 일반화하기 위한 무료 공개자료 공백을 정리하는 것이다.

## 현재 판정

- 채택 유지: `부동산업(KSIC 68)` 총량은 Phase145 baseline 유지
- 채택 금지: K=300/700 2도시 라우팅 수치
- 개선 방향: 681은 재고·면적·공시가격, 682는 거래·전월세·중개·관리서비스 활동으로 분리
- 다음 성능 검증: 고양·포항 외 임의 10개 시군구에서 같은 후보식을 평가해야 함

## 무료 공개자료 후보

{md_table(sources.rename(columns={
    'priority': '우선순위',
    'source_name': '자료명',
    'url': '링크',
    'access_type': '접근방식',
    'free': '무료',
    'key_or_approval': '키/승인',
    'coverage': '범위',
    'phase151_use': '활용방향',
    'as_of_risk': '시점위험',
    'request_to_user': '사용자 요청',
}))}

## 다음 실행 순서

1. 통합 실거래 CSV 또는 API 13종에서 전월세·오피스텔·상업업무용 거래를 우선 수집한다.
2. 2023년 소분류 검증에는 2023 자료만, 정밀화에는 공표 후 자료만 사용하도록 source-vintage를 분리한다.
3. 공동주택 단지/기본정보는 정밀화 구조자료로만 붙인다.
4. K=300/700 라우팅은 고양·포항 외부 시군구에서 재검증되기 전까지 포스터 수치로 쓰지 않는다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    print(f"Wrote {(OUT / 'phase151_realestate_source_candidates.csv').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
