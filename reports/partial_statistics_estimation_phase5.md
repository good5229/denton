# Partial Statistics Estimation Phase 5

## 1. 실행 요약

- 실행일: `2026-07-18T06:48:05+09:00`
- 목적: 완전한 원표 부재를 실험 차단 사유가 아니라 부분관측 통계 복원 문제로 재정의했다.
- 입력 Anchor: 시군구×제조업·광업 중분류×2021~2023 사업체 수/종사자 수.
- KSIC 8→9 공식 연계표 `data/raw/9차개정 연계표.xls`를 파싱해 legacy mapping evidence를 보강했다.
- 개발용 모델 학습은 수행했지만 production·confirmatory 주장은 금지 상태로 유지했다.

## 2. 연구 문제 재정의

`Y[지역, 업종, 기간]` 중 공개된 셀은 Anchor, 공개되지 않은 셀은 추정 대상, 상위 합계는 Constraint 후보로 분리했다.

## 3. 추정 대상 Cube

- Target E: 사업체 수
- Target W: 종사자 수
- Region universe: crosswalk 후 model sigungu key
- Industry level: KSIC middle-level manufacturing/mining anchor
- Period: 2021, 2022, 2023

## 4. 관측자료와 Constraint

- Constraint rows: `2,531`. 이번 1차 실행에서는 hidden validation cell leakage를 피하기 위해 reconciliation은 R0만 적용했다.

## 5. 결측 원인 분류

- 관측 셀은 `observed`, 공개되지 않은 cube 셀은 `not_published`로 분리했다.
- suppressed/true_zero는 공식 근거가 없어 주장하지 않았다.

## 6. 관측 Coverage

| audit_axis | axis_value | total_possible_cells | observed_cells | true_zero_cells | suppressed_cells | not_published_cells | unknown_missing_cells | observation_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| overall | all | 39672 | 17520 | 0 | 0 | 22152 | 0 | 0.44162129461585 |
| region_key | 강원특별자치도 강릉시 | 174 | 81 | 0 | 0 | 93 | 0 | 0.46551724137931033 |
| region_key | 강원특별자치도 고성군 | 174 | 21 | 0 | 0 | 153 | 0 | 0.1206896551724138 |
| region_key | 강원특별자치도 동해시 | 174 | 67 | 0 | 0 | 107 | 0 | 0.3850574712643678 |
| region_key | 강원특별자치도 삼척시 | 174 | 52 | 0 | 0 | 122 | 0 | 0.2988505747126437 |
| region_key | 강원특별자치도 속초시 | 174 | 12 | 0 | 0 | 162 | 0 | 0.06896551724137931 |
| region_key | 강원특별자치도 양구군 | 174 | 23 | 0 | 0 | 151 | 0 | 0.13218390804597702 |
| region_key | 강원특별자치도 양양군 | 174 | 39 | 0 | 0 | 135 | 0 | 0.22413793103448276 |
| region_key | 강원특별자치도 영월군 | 174 | 60 | 0 | 0 | 114 | 0 | 0.3448275862068966 |
| region_key | 강원특별자치도 원주시 | 174 | 129 | 0 | 0 | 45 | 0 | 0.7413793103448276 |
| region_key | 강원특별자치도 인제군 | 174 | 19 | 0 | 0 | 155 | 0 | 0.10919540229885058 |
| region_key | 강원특별자치도 정선군 | 174 | 39 | 0 | 0 | 135 | 0 | 0.22413793103448276 |

## 7. Masking Protocol

- Mask scenarios: `8`개
- Repetitions per scenario: `30`
- Minimum total mask runs: `240`
- Validation actual은 training과 직접 파생 constraint에서 제외했다.

## 8. Baseline

- B0 group mean, B2 region total share proxy, B5 sido neighbor mean proxy를 실행했다.
- IPF는 hidden-cell leakage 없는 독립 constraint가 부족해 이번 실행에서는 등록만 하고 적용하지 않았다.

## 9. 후보모델

- M1 hierarchical Ridge를 실행했다.
- ElasticNet, matrix/tensor completion, graph regularized model, constrained ensemble은 registry에 등록하되 1차 pass에서는 보류했다.

## 10. 한국형 공간 Feature

- Phase 4B의 region archetype, static geography, Queen/nearest-5 feature를 사용했다.
- 시군구 이름/ID 자체는 feature로 직접 넣지 않았다.

## 11. Aggregate Reconciliation

- R0 none만 실행했다. C1 anchor-derived constraints는 audit table로 유지했다.

## 12. Cell-level 정확도

| target_name | best_baseline_model | best_baseline_wmape | best_candidate_model | best_candidate_wmape | relative_improvement | block_mask_consistency_pass | grade | production_use | confirmatory_claim |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| establishments | B0_group_mean | 1.0209107155080748 | M1_hierarchical_ridge | 0.7797111261545489 | 0.2362592396079304 | Y | B | false | false |
| employees | B0_group_mean | 1.3477251399152494 | M1_hierarchical_ridge | 0.7961465791087021 | 0.4092663588966166 | Y | B | false | false |

## 13. 공간 합계 정확도

- Full reconciliation은 미적용. Anchor-derived aggregate validation table을 생성했다.

## 14. 업종 합계 정확도

- 업종별 constraint audit은 `partial_stats_constraint_audit.csv`에 남겼다.

## 15. 시간 일관성

- Year-level 결과는 `partial_stats_year_results.csv`에 저장했다.

## 16. Region Block 결과

| model_id | mask_scenario | target_name | wmape | p90_ape | n |
| --- | --- | --- | --- | --- | --- |
| B0_group_mean | M1_region_block | employees | 0.719732033063687 | 2.4027634928928037 | 1158 |
| B0_group_mean | M1_region_block | establishments | 0.6222391998498947 | 3.0424308191808196 | 3209 |
| B2_region_total_share | M1_region_block | employees | 2.956126897113945 | 18.41864268162403 | 1158 |
| B2_region_total_share | M1_region_block | establishments | 2.706747412177307 | 17.151055857435235 | 3209 |
| B5_neighbor_sido_mean | M1_region_block | employees | 0.7786458826472071 | 3.6095591655090025 | 1158 |
| B5_neighbor_sido_mean | M1_region_block | establishments | 1.0238254795336796 | 4.616950478090128 | 3209 |
| M1_hierarchical_ridge | M1_region_block | employees | 0.6326846184968284 | 0.9105347756939859 | 1158 |
| M1_hierarchical_ridge | M1_region_block | establishments | 0.7156346884456134 | 1.2495514633313596 | 3209 |

## 17. Industry Block 결과

| model_id | mask_scenario | target_name | wmape | p90_ape | n |
| --- | --- | --- | --- | --- | --- |
| B0_group_mean | M2_industry_block | employees | 1.399868103641779 | 8.099539802895508 | 5633 |
| B0_group_mean | M2_industry_block | establishments | 1.0245037737183262 | 5.633349414877765 | 12974 |
| B2_region_total_share | M2_industry_block | employees | 2.369328346770034 | 19.89511866295747 | 5633 |
| B2_region_total_share | M2_industry_block | establishments | 2.9873785233906935 | 23.434337542747247 | 12974 |
| B5_neighbor_sido_mean | M2_industry_block | employees | 0.9343911383348332 | 5.416243128777003 | 5633 |
| B5_neighbor_sido_mean | M2_industry_block | establishments | 1.0228475325582156 | 4.999884552269446 | 12974 |
| M1_hierarchical_ridge | M2_industry_block | employees | 0.720064076107416 | 3.189338277624402 | 5633 |
| M1_hierarchical_ridge | M2_industry_block | establishments | 0.7288344899410446 | 2.4786305351578237 | 12974 |

## 18. Small-value Mask 결과

| model_id | mask_scenario | target_name | wmape | p90_ape | n |
| --- | --- | --- | --- | --- | --- |
| B0_group_mean | M5_small_value | employees | 2.79900969683869 | 19.335162746765604 | 18728 |
| B0_group_mean | M5_small_value | establishments | 1.5050367038158874 | 15.842784745715846 | 86392 |
| B2_region_total_share | M5_small_value | employees | 2.3536535073075084 | 16.061528888017335 | 18728 |
| B2_region_total_share | M5_small_value | establishments | 1.3319395854058584 | 12.792396497147733 | 86392 |
| B5_neighbor_sido_mean | M5_small_value | employees | 3.249387031019781 | 26.138931954346138 | 18728 |
| B5_neighbor_sido_mean | M5_small_value | establishments | 1.743769043215941 | 26.61869898110995 | 86392 |
| M1_hierarchical_ridge | M5_small_value | employees | 0.9478418225264295 | 5.59326041380358 | 18728 |
| M1_hierarchical_ridge | M5_small_value | establishments | 0.8281418563546968 | 5.70985126252881 | 86392 |

## 19. Spatial Validation

- M4 regional cluster mask를 spatial validation proxy로 실행했다.

## 20. Placebo

- Placebo는 registry에 등록했다. 이번 1차 실행에서는 Cube/Mask/Baseline/Ridge 검증을 우선했고, Grade B 후보에 대한 placebo는 후속 안정성 검증으로 남겼다.

## 21. Bootstrap

- Cluster bootstrap 2,000회는 manifest에 등록했다. 이번 1차 실행에서는 미실행이므로 Grade B는 development 등급이며 confirmatory 근거가 아니다.

## 22. 불확실성 Calibration

- Prediction interval 방법은 등록했다. 현재 interval은 개발용 휴리스틱이며 bootstrap/conformal calibration 전까지 production uncertainty로 쓰지 않는다.

## 23. 모델 선택

- Grade B 이상 모델에서만 미공개 셀 추정치를 생성한다는 규칙을 유지했다.

## 24. 미공개 셀 추정치

- Grade B development 후보가 있어 미공개 셀 추정치를 생성했다. 다만 reconciliation은 R0이고 uncertainty calibration이 미완료이므로 `production_use=false`이다.

## 25. Aggregate Validation

- Observed anchor aggregate validation은 생성했지만 production 통계로 해석하지 않는다.

## 26. 한계

- 현재 anchor는 제조업·광업 중심이며 전 산업 시군구 원표가 아니다.
- 일부 행정구는 parent city로 집계되어 세부 지역 복원에는 추가 crosswalk가 필요하다.
- 상위 constraint가 독립 공식표가 아니라 anchor-derived인 축은 reconciliation에 직접 쓰지 않았다.

## 27. 후속 검증계획

1. 시군구×전산업 사업체·종사자 원표를 확보해 anchor coverage를 늘린다.
2. 독립적인 시도×업종 공식 constraint를 확보해 IPF/CLS reconciliation을 실행한다.
3. Grade B 후보가 나오면 placebo와 cluster bootstrap을 실행한다.
4. 실제 미공개 셀 추정치는 uncertainty interval을 붙인 뒤에만 생성한다.
