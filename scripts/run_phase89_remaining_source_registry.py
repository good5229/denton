#!/usr/bin/env python3
"""Phase89: source registry for remaining weak middle industries.

The current accuracy registry (Phase88) leaves six weak middle-industry cells.
This phase does not force another model change.  It records which free/public
data sources are plausible for each remaining weakness, whether they are
already local, immediately downloadable, API/application based, or likely
blocked for now.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase89_remaining_source_registry"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase89_remaining_source_registry.md"


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
            value = row[key]
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def remaining() -> pd.DataFrame:
    df = pd.read_csv(DATA / "phase88_current_industry_accuracy_registry" / "phase88_remaining_improvement_queue.csv")
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    return df


def local_inventory() -> pd.DataFrame:
    rows = []
    candidates = [
        ("building_use_area", DATA / "partial_stats_phase51_realestate_legal_dong_use_features.csv", "건축물 용도별 연면적·건수"),
        ("building_permit_events", DATA / "partial_stats_phase52_building_permit_legal_dong_monthly.csv", "건축 인허가·착공·사용승인 이벤트"),
        ("pohang_business_survey", DATA / "partial_stats_phase43_pohang_gu_sales_cv_detail.csv", "포항 2024 사업체조사 중분류 매출·종사자·사업체수"),
        ("pohang_factory_mapping", DATA / "partial_stats_phase43_pohang_factory_industry_mapping.csv", "포항 공장 업종 매핑"),
        ("kosis_manufacturing_mining", DATA / "business_employment_feature_table.csv", "KOSIS 제조·광업 중분류 사업체·종사자·부가가치"),
        ("phase88_registry", DATA / "phase88_current_industry_accuracy_registry" / "phase88_current_middle_industry_accuracy_registry.csv", "현재 중분류 정확도 레지스트리"),
    ]
    for source_id, path, desc in candidates:
        rows.append(
            {
                "source_id": source_id,
                "local_path": str(path.relative_to(ROOT)),
                "exists": path.exists(),
                "description": desc,
                "use_status": "local_available" if path.exists() else "missing",
            }
        )
    return pd.DataFrame(rows)


def source_registry(rem: pd.DataFrame) -> pd.DataFrame:
    base_rows = []
    source_map = {
        ("고양시", "ERS", "94"): [
            {
                "candidate_source": "근로복지공단 고용·산재보험 가입 사업장 현황",
                "url": "https://www.data.go.kr/data/15129538/fileData.do",
                "free_status": "무료",
                "collection_status": "candidate_download_or_api",
                "expected_signal": "협회·단체/기타 개인서비스 사업장·가입자 규모",
                "fit_grade": "보조",
                "reason": "공개 설명상 산업별 가입자·사업장 합계가 있으나 중분류/지역 세밀도 확인 필요",
            },
            {
                "candidate_source": "공익법인/비영리단체 공시·등록 자료",
                "url": "manual_search_required",
                "free_status": "무료 후보",
                "collection_status": "needs_discovery",
                "expected_signal": "단체 예산·수입·회원·종사자 규모",
                "fit_grade": "핵심 후보",
                "reason": "협회·단체 GVA는 사업체 수보다 예산·회비·사업수입 규모가 더 직접적",
            },
        ],
        ("고양시", "J00", "60"): [
            {
                "candidate_source": "방송미디어통신위원회_방송사업자 재산상황 공표 현황",
                "url": "https://www.data.go.kr/data/15030809/fileData.do",
                "free_status": "무료 파일데이터",
                "collection_status": "candidate_download",
                "expected_signal": "방송사업자 매출·손익·자산 규모",
                "fit_grade": "핵심 후보",
                "reason": "방송업은 사업체 수보다 방송사업자 재무 규모가 GVA에 가까움",
            },
        ],
        ("포항시", "MN0", "72"): [
            {
                "candidate_source": "ETIS 엔지니어링종합정보시스템",
                "url": "https://www.etis.or.kr/webs/cmp/report_new.jsp",
                "free_status": "무료 조회 후보",
                "collection_status": "web_query_or_manual_export",
                "expected_signal": "엔지니어링 사업자 신고, 수주실적, 매출실적, 임금실태",
                "fit_grade": "핵심 후보",
                "reason": "건축·엔지니어링 서비스업은 계약·수주·기술인력 규모가 GVA에 가까움",
            },
            {
                "candidate_source": "전국건설업체정보표준데이터",
                "url": "https://www.data.go.kr/data/15129444/standard.do?recommendDataYn=Y",
                "free_status": "무료 API",
                "collection_status": "api_application_required",
                "expected_signal": "건설 관련 업체 소재지·업종·공시 정보",
                "fit_grade": "보조",
                "reason": "건축·엔지니어링 자체가 아니라 건설 생태계 보조 신호",
            },
        ],
        ("포항시", "C00", "34"): [
            {
                "candidate_source": "포항 공장 업종 매핑",
                "url": "local:data/processed/partial_stats_phase43_pohang_factory_industry_mapping.csv",
                "free_status": "로컬 수집 완료",
                "collection_status": "local_available_but_sparse",
                "expected_signal": "산업용 기계·장비 수리업 공장/사업체 존재",
                "fit_grade": "부족",
                "reason": "로컬 공장 매핑에서 C34 직접 행이 적어 수리 물량·매출을 대체하기 어려움",
            },
            {
                "candidate_source": "기계설비·정비업 사업자/수리실적 자료",
                "url": "manual_search_required",
                "free_status": "무료 후보",
                "collection_status": "needs_discovery",
                "expected_signal": "정비 건수, 정비 대상 설비, 수리 매출",
                "fit_grade": "핵심 후보",
                "reason": "C34는 제조시설 면적보다 정비·수리 활동량이 필요",
            },
        ],
        ("포항시", "ERS", "39"): [
            {
                "candidate_source": "환경부/한국환경공단 환경정화·복원 또는 오염처리 실적",
                "url": "manual_search_required",
                "free_status": "무료 후보",
                "collection_status": "needs_discovery",
                "expected_signal": "환경정화 처리량, 복원사업 계약액, 오염처리 실적",
                "fit_grade": "핵심 후보",
                "reason": "ERS39는 사업체 수가 작아 처리량·계약액 없이는 상대오차가 크게 남음",
            },
        ],
        ("포항시", "J00", "63"): [
            {
                "candidate_source": "근로복지공단 고용·산재보험 가입 사업장 현황",
                "url": "https://www.data.go.kr/data/15129538/fileData.do",
                "free_status": "무료",
                "collection_status": "candidate_download_or_api",
                "expected_signal": "정보통신업 사업장·가입자 규모",
                "fit_grade": "보조",
                "reason": "공개 설명상 대분류 산업별 신호라 정보서비스업 중분류 분리는 어려울 수 있음",
            },
            {
                "candidate_source": "정보서비스·데이터센터·플랫폼 사업자 자료",
                "url": "manual_search_required",
                "free_status": "무료 후보",
                "collection_status": "needs_discovery",
                "expected_signal": "서버·데이터센터·플랫폼 매출 또는 사업장 규모",
                "fit_grade": "핵심 후보",
                "reason": "J63은 매우 작은 실제 GVA라 일반 사업체 지표가 과대 배분을 일으킴",
            },
        ],
    }
    for _, row in rem.iterrows():
        key = (row.city, row.parent_code, str(row.middle_code).zfill(2))
        entries = source_map.get(key, [])
        if not entries:
            entries = [
                {
                    "candidate_source": "미정",
                    "url": "manual_search_required",
                    "free_status": "확인 필요",
                    "collection_status": "needs_discovery",
                    "expected_signal": row.needed_data_type,
                    "fit_grade": "미정",
                    "reason": "잔여 취약군이나 아직 구체 후보 없음",
                }
            ]
        for entry in entries:
            base = row[
                [
                    "city",
                    "parent_code",
                    "middle_code",
                    "middle_label",
                    "actual_gva_eok",
                    "final_predicted_gva_eok",
                    "final_error_gva_eok",
                    "final_error_rate_pct",
                    "needed_data_type",
                ]
            ].to_dict()
            base.update(entry)
            base_rows.append(base)
    return pd.DataFrame(base_rows)


def priority(source: pd.DataFrame) -> pd.DataFrame:
    grade_order = {"핵심 후보": 0, "보조": 1, "부족": 2, "미정": 3}
    out = source.copy()
    out["priority_rank"] = out.fit_grade.map(grade_order).fillna(9)
    out["error_weighted_priority"] = out.final_error_gva_eok / (out.priority_rank + 1)
    return out.sort_values(["priority_rank", "error_weighted_priority"], ascending=[True, False])


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rem = remaining()
    local = local_inventory()
    src = source_registry(rem)
    pr = priority(src)
    rem.to_csv(OUTDIR / "phase89_remaining_weak_industries.csv", index=False, encoding="utf-8-sig")
    local.to_csv(OUTDIR / "phase89_local_source_inventory.csv", index=False, encoding="utf-8-sig")
    src.to_csv(OUTDIR / "phase89_remaining_source_registry.csv", index=False, encoding="utf-8-sig")
    pr.to_csv(OUTDIR / "phase89_source_collection_priority.csv", index=False, encoding="utf-8-sig")

    report = f"""# 잔여 취약 중분류 보강자료 레지스트리

## 목적

Phase88 최종 레지스트리에서 남은 6개 취약 중분류에 대해, 추가 오차 축소에 필요한 무료·공개 자료 후보를 정리했다. 이번 단계는 수치를 억지로 더 낮추는 실험이 아니라, 다음 실험에서 실제로 투입할 수 있는 자료 후보를 선별하는 단계다.

## 운영 전략

모든 산업을 개별 특화모델로 만들지 않는다. 전 산업 공통 기준을 먼저 유지하고, 실제 중분류 GVA와의 격차가 큰 산업만 원인군별로 묶어 처리한다.

| 원인군 | 대상 | 필요한 신호 | 적용 방식 |
| --- | --- | --- | --- |
| 생산시설형 | 제조업·기계수리 | 공장·설비·제조시설 규모 | 공장등록·제조시설면적·중분류 제조업 구조 결합 |
| 계약·공사형 | 건설·엔지니어링 | 계약액·수주·착공·기성 | 건축허가와 엔지니어링 수주/기술인력 자료 결합 |
| 거래·자산형 | 부동산·금융 | 거래금액·자산·연면적 | 공시가격·연면적·거래·중개업소 지표 결합 |
| 이동·물량형 | 운수·창고 | 승객·화물·창고·항만 물동량 | 여객·창고·항만 신호를 중분류별로 분리 |
| 공공·비영리형 | 협회·복지·환경정화 | 예산·회원·시설정원·처리량 | 비영리 공시·복지시설·환경처리 실적 결합 |
| 디지털·콘텐츠형 | 방송·정보서비스 | 방송매출·콘텐츠·서버·플랫폼 규모 | 방송사업자 재산상황과 정보서비스 사업장 규모 결합 |

## 남은 취약 중분류

{md_table(rem, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("final_predicted_gva_eok", "추정 억원"), ("final_error_gva_eok", "오차 억원"), ("final_error_rate_pct", "오차 %"), ("needed_data_type", "필요 자료")])}

## 로컬 보유자료 점검

{md_table(local, [("source_id", "자료ID"), ("exists", "존재"), ("description", "설명"), ("use_status", "상태"), ("local_path", "경로")])}

## 무료 공개자료 후보

{md_table(pr, [("city", "지역"), ("middle_code", "코드"), ("middle_label", "산업"), ("candidate_source", "후보 자료"), ("free_status", "무료 여부"), ("collection_status", "수집 상태"), ("fit_grade", "적합도"), ("expected_signal", "기대 신호"), ("url", "URL")], 80)}

## 수집 우선순위

1. 고양 방송업: 방송사업자 재산상황 공표 자료가 가장 직접적이다. 방송사업자별 매출·손익·자산을 지역 또는 사업자 소재지와 연결할 수 있는지 확인한다.
2. 포항 건축·엔지니어링 서비스업: ETIS의 엔지니어링 사업자, 수주실적, 매출실적, 임금실태 메뉴가 가장 직접적이다. 자동 수집이 어려우면 수동 export 가능성을 확인한다.
3. 포항 산업용 기계 수리업: 현재 로컬 공장 매핑은 C34 직접 행이 희소하다. 수리업 매출·정비물량·정비시설 자료가 새로 필요하다.
4. 고양 협회·단체: 비영리단체 활동규모나 예산/회원/종사자 자료가 필요하다. 일반 사업체 수로는 과대 배분이 남는다.
5. 포항 정보서비스업·환경정화복원업: 실제 GVA가 작아 일반 활동지표가 쉽게 과대 배분된다. 서버·데이터센터·플랫폼 규모, 환경정화 처리량·계약액 같은 직접 물량자료가 필요하다.

## 판정

현재 보유자료만으로 추가 실험을 강행하면 임의 상한·하한에 가까워질 위험이 크다. 다음 실험은 위 후보 중 실제 파일/API 수집이 가능한 자료를 확보한 뒤, 개별 중분류의 실제 GVA 대비 오차가 줄어드는 경우에만 채택한다. 성능 표기는 항상 실제 GVA, 추정 GVA, 오차금액, 오차율을 함께 사용한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase89_remaining_source_registry.csv")
    print(OUTDIR / "phase89_source_collection_priority.csv")


if __name__ == "__main__":
    main()
