# Phase236 active goal frontier synthesis

생성시각: 2026-07-29T10:21:58+09:00

## 결론

- “전국 합산 WAPE”가 아니라 세 층으로 판단한다: 업종×운영시점, 광역시도×업종, 시군구×업종.
- 업종×운영시점 총괄은 운수 및 창고업 1개 route로 10% 이하 목표를 충족한다.
- 광역시도×업종에서는 운수 및 창고업 route가 안정적이고, 건설업은 Phase235 기준 Q1/Q2 시간경로에 한해 제한 채택 후보가 생겼다.
- 시군구×업종 연간에서는 건설업 WAPE 19.432%가 남아 전체 목표는 아직 미완료다.
- 따라서 현재 최소 산업군 전략은 `운수 및 창고업 채택 + 건설업 Q1/Q2 시간경로 제한 후보 + 건설업 시군구 공간배분 자료수집`이다.
- 현재 방식은 총량·광역시도 업종 모니터링에는 실용성이 있으나, 시군구×건설업처럼 위치성이 강한 업종은 추가 event 자료 기반 공간배분이 필요하다.

## 목표층별 상태

| 검증층 | 목표 | 상태 | 채택/후보 범위 | 근거 | 잔여 |
| --- | --- | --- | --- | --- | --- |
| 업종×운영시점 총괄 | 최대한 적은 산업군으로 업종 최대 WAPE≤10% | 충족 | 운수 및 창고업 1개 route | minimal_activity_hybrid Q1 업종최대 WAPE 9.581%, 10%초과 업종 0 | 광역시도/시군구 세부셀은 별도 검증 필요 |
| 광역시도×업종 운영시점 | 10% 초과 셀 축소 및 업종별 시간경로 개선 | 부분충족 | 운수 및 창고업 전분기, 건설업 Q1/Q2 시간경로 제한 후보 | 운수 route 10%초과 셀 감소, Phase235 건설 Q1/Q2 pooled WAPE≤10 | 건설 Q1/Q2 2025 단년 WAPE>10, Q3/Q4 BOK 미채택 |
| 시군구×업종 연간 | 업종별 WAPE≤10% | 미달 | 운수 등 대부분 업종 상위총량 배분 가능 | 건설업 최선 WAPE 19.432% | 건설업 시군구 공간배분 staged collection 필요 |


## 업종×운영시점 총괄

| 사용분기 | 운영시점 | 업종최대 WAPE_% | 10%초과 업종수 |
| --- | --- | ---: | ---: |
| 1 | 1분기+1개월 | 9.581 | 0 |
| 2 | 1~2분기+1개월 | 8.165 | 0 |
| 3 | 1~3분기+1개월 | 8.069 | 0 |
| 4 | 공표 후 정밀화 | 7.983 | 0 |


## 광역시도×업종: 운수 route

| 사용분기 | route 업종수 | route 업종 | 10%초과 셀 | 전체 WAPE_% |
| --- | --- | --- | ---: | ---: |
| 1 | 1 | 운수 및 창고업 | 18 | 3.093 |
| 2 | 1 | 운수 및 창고업 | 9 | 2.514 |
| 3 | 1 | 운수 및 창고업 | 8 | 2.296 |
| 4 | 1 | 운수 및 창고업 | 7 | 2.148 |


## 광역시도×건설업 시간경로: Phase235 엄격 정책

| 사용분기 | BOK적용셀 | 기준 WAPE_% | 선택 WAPE_% | 변화 pp | 기준 10%초과 | 선택 10%초과 | 기준 최대APE_% | 선택 최대APE_% | 판정 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 10 | 9.987 | 8.843 | -1.144 | 20 | 16 | 37.219 | 34.921 | Q1 제한 채택 후보 |
| 2 | 7 | 9.670 | 8.889 | -0.781 | 22 | 19 | 38.894 | 38.894 | Q2 제한 채택 후보 |
| 3 | 0 | 9.635 | 9.635 | 0.000 | 21 | 21 | 41.202 | 41.202 | baseline 유지 |
| 4 | 0 | 9.577 | 9.577 | 0.000 | 24 | 24 | 42.106 | 42.106 | baseline 유지 |


주의:

- 건설업 Phase235 route는 광역시도×건설업 시간경로에 한정한다.
- Q1/Q2 pooled WAPE는 10% 이하이나, 2025년 일부 단년 WAPE가 10%를 소폭 초과한다.
- Q3/Q4는 BOK gate를 운영 채택하지 않고 baseline을 유지한다.
- 시군구 공간배분 개선으로 해석하지 않는다.

## 시군구×업종 잔류 병목

| 업종 | WAPE_% | 10%초과 셀 | 20%초과 셀 | 최선 시나리오 |
| --- | ---: | ---: | ---: | --- |
| 건설업 | 19.432 | 361 | 224 | parent_control_all_activities |
| 운수 및 창고업 | 8.124 | 235 | 88 | parent_control_all_activities |
| 정보통신업 | 7.980 | 241 | 137 | parent_control_all_activities |
| 사업서비스업 | 6.641 | 219 | 100 | parent_control_all_activities |
| 금융 및 보험업 | 6.361 | 162 | 69 | parent_control_all_activities |
| 문화 및 기타서비스업 | 5.998 | 135 | 38 | parent_control_all_activities |
| 광업, 제조업 | 5.032 | 162 | 44 | parent_control_all_activities |
| 숙박 및 음식점업 | 4.637 | 101 | 29 | parent_control_all_activities |


## 다음 작업

1. 건설업 시군구 공간배분 자료수집: top1/top5→top28→top52 staged collection.
2. 민간건축, 정비사업, 공공·토목, fallback형 지역유형 gate 사전정의.
3. rolling out-of-year에서 WAPE, 10%/20% 초과 셀, 최대 APE, 대형 셀 절대오차 guardrail 동시 통과 여부 검증.
4. Q+1개월 속보성으로 표현하려면 건설수주 자료 공표시차 확인.

## 산출 파일

- `data/processed/phase236_active_goal_frontier_synthesis/phase236_goal_level_status.csv`
- `data/processed/phase236_active_goal_frontier_synthesis/phase236_construction_time_policy.csv`
- `data/processed/phase236_active_goal_frontier_synthesis/phase236_remaining_sigungu_bottlenecks.csv`
