# 인천·울산·세종·대구·충북 개선 및 전국 대시보드 목표 완료 감사

생성일: 2026-07-28

## 요구사항별 판정

| 요구 | 판정 | 증거 |
| --- | --- | --- |
| 1. 인천·울산·세종·대구·충북에서 예측이 어려운 업종 파악 | 충족 | `nationwide/hard_region_activity_diagnostics.md`, `nationwide/outputs/hard_region_activity_diagnostics.csv` |
| 2. 예측 취약 원인이 특정 업종 데이터 부족인지 조사 | 충족 | `cause_class`, `needed_direct_data`, `candidate_action` 컬럼과 `nationwide/hard_region_data_availability_and_collection_plan.md` |
| 3. 수집 가능한 데이터 수집 및 고양·포항식 독립 라우팅 가능성 실험 | 충족 | 제조업 생산지수, 서비스업 생산지수, 건설수주액 등 후보를 `nationwide/run_hard_region_indicator_route_experiment.py`, `nationwide/run_hard_region_indicator_route_rolling_gate.py`에서 검증 |
| 4. 예측 성능 개선 가능한 범위 수행 | 충족 | `nationwide/hard_region_indicator_route_rolling_gate.md`: Q1 WAPE 3.417%→2.948%, Q1~Q2 WAPE 2.863%→2.503%. Q1~Q3·정밀화 자동채택 금지까지 명시 |
| 5-a. `dashboard/` 폴더 대시보드 생성 | 충족 | `dashboard/index.html`, `dashboard/app.js`, `dashboard/styles.css`, `dashboard/data/dashboard_data.json` |
| 5-b. 전국 지도 | 충족 | `dashboard/data/province_features.js`, SVG 지도 렌더 |
| 5-c. 좌상단 지역 검색, 특정 시·시군구 검색 | 충족 | 17개 시도 + 229개 시군구/통합시, `dashboard/data/manifest.json` 및 `findRegion()` |
| 5-d. 검색 후 도청·시청·군청·구청 등 행정 중심 소재지로 이동 | 충족 | 246개 전 지역 `coordinateStatus=admin_office_coordinate_sourced`; 인천 11개는 공공데이터포털 인천 원천, 나머지 235개는 ESRI/MOIS 기반 좌표 |
| 5-e. 모달에서 2021~2025 실제·추정 GRDP/GVA 표시 | 충족 | 시도 total은 GRDP actual/estimate, 시군구는 GVA actual 및 GRDP형 참고값 분리 |
| 5-f. 업종 검색창, KSIC 업종명 자동완성, 전체 기능 | 충족 | `industrySearch`, `industryOptions`, `industrySelect`, `전체` |
| 5-g. 특정 업종 선택 시 추정값 및 actual 표시 | 충족 | `metric.industries` 기반 업종 GVA 추정·actual 비교 |
| 5-h. 평가관·디자이너 agent 반복 검토 | 충족 | 취약 업종 진단 추가 후 재검토, 좌표 원천 변경 후 재검토 모두 최종 `필수 수정 없음` |

## 최종 기계 검증

| 항목 | 확인값 |
| --- | ---: |
| 지역 수 | 246 |
| metric 수 | 246 |
| 시도 | 17 |
| 시군구/통합시 | 229 |
| 업종 선택지 | 15 (`전체` 포함) |
| total 표시 연도 | 2021~2025 |
| 행정청사 좌표 적용 지역 | 246 |
| 대표점 fallback | 0 |
| 어려운 5개 시도 취약 업종 진단 | 5개 시도 × TOP 5 |

검증 명령:

```bash
.venv/bin/python dashboard/prepare_dashboard_data.py
node --check dashboard/app.js
```

## 좌표 원천 주의

- 인천 11개 지역: `data/raw/admin_center_coordinates/incheon_facility_info_15076595.csv`
- 그 외 235개 지역: `data/processed/admin_center_coordinates/esri_local_government_offices_2025.csv`
- ESRI/MOIS 좌표는 공개 조회 가능한 FeatureServer에서 수집했으나, 원천 메타데이터의 사용권 표기는 `All rights reserved by Korean Ministry of Interior and Safety`다.
- 외부 재배포·상업적 이용 가능 범위는 원천 사용조건 확인이 필요하다.
- ESRI/MOIS 원자료 기준일은 2016.12, 서비스 갱신 표기는 2025.02다.

## 최종 판단

기능 요구사항과 검증 요구사항은 현재 상태에서 충족된다. 남은 사항은 필수 결함이 아니라 선택 개선이다. 예를 들어 더 최신의 지역별 청사 좌표 원천이 확보되면 ESRI/MOIS 기반 좌표보다 우선 적용할 수 있다.
