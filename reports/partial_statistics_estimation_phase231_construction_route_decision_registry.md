# 건설업 route decision registry

생성시각: 2026-07-29T10:05:04+09:00

## 결론

- 현재 건설업은 시군구×업종 WAPE 10% 목표의 마지막 병목이다.
- 채택 가능한 건설업 대분류 공간배분 route는 아직 없다.
- 고양·포항 41/42 내부 분할은 건축활동 gate가 유망하지만 local proof에 그친다.
- BuildingHUB 단일/제한혼합, PPS 서울 pair, lag-share는 운영 route로 미채택한다.
- PPS는 공공·토목형 지역 보조 feature 후보, BuildingHUB는 민간건축·세부구조 보조 feature 후보로만 유지한다.
- 다음 실험은 지역유형 gate를 전제로 top1/top5→top28→top52 staged collection이다.

## decision summary

| 판정 | 층위 | route 수 |
| --- | --- | --- |
| 미채택 | 시군구 대분류 공간배분 | 4 |
| 수집필요 | 수집전략 | 1 |
| 후보유지 | 시군구 대분류 공간배분 | 1 |
| 후보유지 | 중분류 내부 분할 | 1 |


## route registry

| route | 층위 | 신호군 | 검증범위 | 기준 WAPE % | 후보 WAPE % | 변화 pp | guardrail | 판정 | 채택수준 | 사유 |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| construction_41_42_building_activity_gate | 중분류 내부 분할 | 건축활동 | 고양·포항 41/42 local proof | 68.779 | 3.424 | -65.355 | 1 | 후보유지 | local_proof_only | 2개 도시 41/42 분할은 10% 이하이나 threshold 사후선택 가능성과 외부 holdout 부족 |
| construction_pps_nationwide_partial_2023 | 시군구 대분류 공간배분 | PPS 공공공사 | 2023 부분기간 전국 일부 시도 | 23.703 | 23.207 | -0.497 | 1 | 후보유지 | feasibility_only | 일부 guardrail 후보는 있으나 2023 부분기간·전국 raw 불완전으로 운영 채택 불가 |
| construction_staged_collection_frontier | 수집전략 | 건축HUB·정비사업·PPS | 전국 건설업 오차기여 상위 시군구 | 20.675 | nan | nan | 0 | 수집필요 | collection_plan | WAPE 10% 이하에는 현재 절대오차의 51.6% 감축 필요. top52에서 75% 감축 가정 시 oracle 9.907% |
| construction_buildinghub_limited_mix | 시군구 대분류 공간배분 | 건축활동 | 서울 강남·종로 pair 2021~2023 | 10.361 | 9.535 | -0.825 | 0 | 미채택 | rejected_guardrail | pooled WAPE는 일부 개선되나 전연도 WAPE·최대APE guardrail 통과 후보 0개 |
| construction_buildinghub_single_spatial_share | 시군구 대분류 공간배분 | 건축활동 | 서울 강남·종로 pair 2021~2023 | 10.361 | 108.987 | 98.627 | 0 | 미채택 | rejected_single_route | 건축활동 단일 share가 현행보다 크게 악화 |
| construction_lag_share_refinement | 시군구 대분류 공간배분 | 전년도 share | 전국 시군구 2021~2023 | 19.432 | 19.432 | 0.000 | 0 | 미채택 | identity_rejected | 현재 예측 share가 전년도 actual share와 사실상 동일해 새 정보가 아님 |
| construction_pps_public_works_mix | 시군구 대분류 공간배분 | PPS 공공공사 | 서울 강남·종로 pair 2021 | 9.141 | 9.637 | 0.496 | 0 | 미채택 | rejected_guardrail | PPS가 강남 share를 낮추는 방향으로 작동해 현행보다 악화 |


## 표현 원칙

- `채택`이 아닌 route는 포스터·보고서에서 성능개선으로 표현하지 않는다.
- pooled WAPE만 개선된 후보는 guardrail 실패 시 미채택으로 쓴다.
- 건설업 41/42 local proof는 세부구조 진단으로만 표현하고 전국 공간배분으로 일반화하지 않는다.
- PPS는 공공·토목형 지역 gate 안에서만 재검증한다.
- BuildingHUB는 민간건축/정밀화 보조 feature로만 유지한다.

## 다음 실험 요구사항

1. top1/top5 건설업 오차지역 BuildingHUB event 수집
2. 지역유형 gate 사전정의: 민간건축형, 공공·토목형, 혼합형, fallback형
3. 각 gate별 허용 feature 제한
4. rolling out-of-year로 threshold/혼합비 선택
5. WAPE, 10% 초과 셀, 20% 초과 셀, 최대 APE, 대형 actual 셀 절대오차 guardrail 동시 적용
