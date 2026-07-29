# 2015~2025 전국 추정·검증 실험 산출물 큐레이션

생성일: 2026-07-29

## 목적

전국 2015~2025 시도·시군구 GVA/GRDP 추정 목표에서 생성된 건설업·PPS·활동자료 실험 파일을 증거체계 관점으로 분류한다. 모든 실험 산출물을 같은 무게로 커밋하지 않고, 재현 가능성·검증 범위·과대해석 위험을 기준으로 `핵심 증거`, `보조 증거`, `보류 산출물`을 구분한다.

## 분류 원칙

| 구분 | 포함 기준 | 커밋 원칙 |
| --- | --- | --- |
| 핵심 증거 | active goal의 현재 결론을 직접 뒷받침하고, 숫자·guardrail·한계가 문서 안에 함께 적힌 산출물 | 우선 커밋 |
| 보조 증거 | 특정 route를 왜 미채택했는지 보여주는 단발/부분 실험 | synthesis 문서가 참조할 때 선별 커밋 |
| 보류 산출물 | 일부 지역·일부 기간·부분월·oracle/진단 성격이 강해 운영 route로 오해될 수 있는 파일 | 원칙적으로 보류. 필요 시 “feasibility only” 표기 후 별도 커밋 |
| raw/processed 대용량 | API 원본, CSV/JSON 산출물 | `.gitignore` 유지, 문서에 출처·coverage·완전성만 기록 |

## 현재 핵심 증거 후보

| 파일 | 역할 | 판정 |
| --- | --- | --- |
| `nationwide/active_goal_wape_frontier.md` | 업종×운영시점, 광역시도×업종, 시군구×업종의 frontier 결론 통합 | 커밋 후보 |
| `nationwide/region_level_wape_refinement_synthesis.md` | “전국 합산이 아니라 광역시도·시군구 레벨”이라는 목표 재정의와 guardrail | 커밋 후보 |
| `reports/partial_statistics_estimation_phase236_active_goal_frontier_synthesis.md` | active goal frontier의 보고서형 요약 | 커밋 후보 |
| `nationwide/construction_special_route_harness.md` | 건설업이 시군구 잔류 병목이며 공간배분 자료수집이 필요하다는 harness | 커밋 후보 |
| `reports/partial_statistics_estimation_phase237_construction_special_route_harness.md` | 위 harness의 보고서 경로 복사본 | 중복. 둘 중 하나만 핵심 경로로 사용 |
| `reports/partial_statistics_estimation_phase231_construction_route_decision_registry.md` | 건설업 route별 채택/미채택 registry | 커밋 후보 |
| `reports/partial_statistics_estimation_phase247_construction_public_activity_synthesis.md` | 공개활동자료 수집 이후 건설업 route 미채택 종합 | 커밋 후보 |

## 보조 증거 후보

| 파일군 | 역할 | 커밋 조건 |
| --- | --- | --- |
| `construction_pps_sigungu_spatial_audit_2021m04/m05/q1/...` | PPS 공사공고 단월·누적 feasibility audit | 해당 월이 완전월이고, 문서가 “운영 route 아님”을 명확히 적을 때 |
| `reports/partial_statistics_estimation_phase227~240_*` | 건설업 BuildingHUB/PPS/BOK식 시간분산 단계별 실험 | phase231/236/237/247 synthesis의 근거로 필요한 최소 세트만 커밋 |
| `nationwide/*_routing_*`, `nationwide/*_wape_*` | 업종 라우팅과 WAPE frontier 세부 실험 | active goal frontier 재현에 필요한 스크립트와 md를 묶어 커밋 |

## 보류 기준

다음 조건 중 하나라도 해당하면 운영 route 근거로 커밋하지 않는다.

- target-year actual 또는 사후 actual을 threshold·혼합비 선택에 사용한 진단 실험
- 일부 지역 pair, 2개 도시 local proof, 일부 월 단독 결과
- PPS 공사공고·계약정보의 불완전월 또는 `numRows`가 섞인 raw
- pooled WAPE만 낮아지고 10% 초과 셀·20% 초과 셀·최대 APE 중 하나가 악화되는 후보
- 건축HUB·PPS·LH·CALS를 전체 건설업 GVA actual처럼 해석할 위험이 큰 산출물

## 커밋 전 최소 검증

| 항목 | 최소 조건 |
| --- | --- |
| Python 스크립트 | `python3 -m py_compile` 통과 |
| 수집 스크립트 | API key 출력 금지, raw/CSV/JSON 대용량 산출물 미추적 |
| 성능 보고서 | 기준 WAPE, 후보 WAPE, 10% 초과 셀, 20% 초과 셀, 최대 APE, 채택/미채택 사유 명시 |
| PPS 자료 | 완전월 조건(`expected_pages == cached_pages`, `cached_items == totalCount`, missing page 0) 명시 |
| 기준연도 지수 | 2020=100 등 기준값 표기, 혼재 시 bridge 방법 표기 |
| 공표시점 | 속보/정밀화 구분과 사용할 수 있는 자료 시점 명시 |

## 현재 결론

현재 목표의 깨끗한 증거체계는 `active goal frontier synthesis + 건설업 route decision registry + PPS/공개활동자료 수집 gate`를 중심으로 구성한다. 단발 개선 실험은 “채택 route”가 아니라 “왜 아직 자료수집/rolling 검증이 필요한지”를 설명하는 보조 증거로만 둔다.
