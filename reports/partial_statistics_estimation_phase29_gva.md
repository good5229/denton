# Partial Statistics Estimation Phase 29-GVA

## 1. 실행 요약

첨부된 GPT 답변의 우선순위에 따라 Annual Regime-Residual Challenger, Forecastability Router, 서비스업 Temporal Component 가림검증을 실행했다. 새 자료를 추가 수집하지 않고 Phase28/Phase27 산출물을 사용했으며, 모든 결과는 development 또는 component validation으로만 해석한다.

## 2. Phase28 재현 및 목표 불변

- target: `GVA`
- target unchanged: `True`
- phase28 reproduction status: `pass`

## 3. GPT 권고사항 반영 방식

| 권고 | Phase29 반영 | 주장 범위 |
| --- | --- | --- |
| lag-level 기준선을 전면 대체하지 말 것 | AN0/AN1/AN2와 RR1을 동일 모집단에서 비교 | development backtest |
| 잔차 또는 점유율 변화 target | parent-adjusted group residual을 예측 | annual anchor challenger |
| 예측 가능한 셀에만 challenger 적용 | OOF 기대개선 기반 router | development router |
| 서비스업 temporal component 실험 | 서비스업생산 분기 share 가림검증 | proxy component validation |

## 4. Annual Regime-Residual 결과

| policy_id | prediction_count | wmape | mape | median_ape | status | selection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AN0_lag_level | 8167 | 0.07597875249742157 | 0.24759386560336274 | 0.06361940803476301 | baseline | incumbent_retained | 4f229ddaeb72204e1d942d7a42f4fd50b1760d05bcd0a798e5ed8fa47124bd4e | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| AN1_lag_growth | 8167 | 0.09670892345162935 | 0.35542264324237177 | 0.07627993970185919 | baseline | not_selected | 4f229ddaeb72204e1d942d7a42f4fd50b1760d05bcd0a798e5ed8fa47124bd4e | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| AN2_parent_growth | 8167 | 0.07843441799824287 | 0.2614771869329675 | 0.06578551040605861 | baseline | not_selected | 4f229ddaeb72204e1d942d7a42f4fd50b1760d05bcd0a798e5ed8fa47124bd4e | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| RR1_group_residual | 8167 | 0.08406987593896115 | 0.2709774377286632 | 0.07188861106514728 | challenger_development | not_selected | 4f229ddaeb72204e1d942d7a42f4fd50b1760d05bcd0a798e5ed8fa47124bd4e | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |

## 5. Annual Backtest Sample

| annual_population_key | source_region | sigungu_code | sigungu_name | sector_code | sector_name | year | actual_gva | RR1_status | RR1_train_rows | RR1_residual_estimate | policy_id | predicted_gva | absolute_error | ape | value_status | actual_used_in_generation | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 강원특별자치도/32010/A00/2021 | 강원특별자치도 | 32010 | 춘천시 | A00 | 농업, 임업 및 어업 | 2021 | 140847.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 143868.0 | 3021.0 | 0.021448806151355727 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/B00/2021 | 강원특별자치도 | 32010 | 춘천시 | B00 | 광업 | 2021 | 11440.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 12528.0 | 1088.0 | 0.0951048951048951 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/C00/2021 | 강원특별자치도 | 32010 | 춘천시 | C00 | 제조업 | 2021 | 581420.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 615831.0 | 34411.0 | 0.059184410580991366 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/D00/2021 | 강원특별자치도 | 32010 | 춘천시 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 2021 | 127410.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 140177.0 | 12767.0 | 0.10020406561494388 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/ERS/2021 | 강원특별자치도 | 32010 | 춘천시 | ERS | 문화 및 기타서비스업 | 2021 | 475622.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 398367.0 | 77255.0 | 0.16242940822754204 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/F00/2021 | 강원특별자치도 | 32010 | 춘천시 | F00 | 건설업 | 2021 | 512959.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 567963.0 | 55004.0 | 0.10722884285098809 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/G00/2021 | 강원특별자치도 | 32010 | 춘천시 | G00 | 도매 및 소매업 | 2021 | 466341.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 467878.0 | 1537.0 | 0.0032958714760229105 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/H00/2021 | 강원특별자치도 | 32010 | 춘천시 | H00 | 운수 및 창고업 | 2021 | 344348.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 315527.0 | 28821.0 | 0.0836973062134817 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/I00/2021 | 강원특별자치도 | 32010 | 춘천시 | I00 | 숙박 및 음식점업 | 2021 | 302397.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 271924.0 | 30473.0 | 0.10077150236278799 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/J00/2021 | 강원특별자치도 | 32010 | 춘천시 | J00 | 정보통신업 | 2021 | 222118.0 | fallback_no_prior_train | 0 | 0.0 | AN0_lag_level | 214212.0 | 7906.0 | 0.035593693442224406 | backtest_prediction | N | b4894234aa81f5888a2264ecd9fb19b0c32b10ae8ad3708ab647ca1796f8ef94 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |

## 6. Forecastability Router 결과

| policy_id | wmape | prediction_count | applied_rate | status | selection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AN0_lag_level | 0.07597875249742157 | 8167 | 0.0 | baseline | incumbent_retained | 6940fd641f384bc3d19c0112dc24eb0bb0cfae67d886608aa2300c45b6e7b877 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| FR1_oof_selective_router | 0.07707712096189001 | 8167 | 0.018121709317987022 | router_development | not_promoted | 6940fd641f384bc3d19c0112dc24eb0bb0cfae67d886608aa2300c45b6e7b877 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |

## 7. Router Application Sample

| annual_population_key | source_region | sigungu_code | sigungu_name | sector_code | sector_name | year | actual_gva | AN0_lag_level | AN1_lag_growth | AN2_parent_growth | RR1_group_residual | baseline_pred | challenger_pred | router_policy | router_reason | expected_delta | router_pred | baseline_error | router_error | delta_good | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 강원특별자치도/32010/A00/2021 | 강원특별자치도 | 32010 | 춘천시 | A00 | 농업, 임업 및 어업 | 2021 | 140847.0 | 143868.0 | 143868.0 | 143868.0 | 143868.0 | 143868.0 | 143868.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 143868.0 | 3021.0 | 3021.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/B00/2021 | 강원특별자치도 | 32010 | 춘천시 | B00 | 광업 | 2021 | 11440.0 | 12528.0 | 12528.0 | 12528.0 | 12528.0 | 12528.0 | 12528.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 12528.0 | 1088.0 | 1088.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/C00/2021 | 강원특별자치도 | 32010 | 춘천시 | C00 | 제조업 | 2021 | 581420.0 | 615831.0 | 615831.0 | 615831.0 | 615831.0 | 615831.0 | 615831.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 615831.0 | 34411.0 | 34411.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/D00/2021 | 강원특별자치도 | 32010 | 춘천시 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 2021 | 127410.0 | 140177.0 | 140177.0 | 140177.0 | 140177.0 | 140177.0 | 140177.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 140177.0 | 12767.0 | 12767.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/ERS/2021 | 강원특별자치도 | 32010 | 춘천시 | ERS | 문화 및 기타서비스업 | 2021 | 475622.0 | 398367.0 | 398367.0 | 398367.0 | 398367.0 | 398367.0 | 398367.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 398367.0 | 77255.0 | 77255.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/F00/2021 | 강원특별자치도 | 32010 | 춘천시 | F00 | 건설업 | 2021 | 512959.0 | 567963.0 | 567963.0 | 567963.0 | 567963.0 | 567963.0 | 567963.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 567963.0 | 55004.0 | 55004.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/G00/2021 | 강원특별자치도 | 32010 | 춘천시 | G00 | 도매 및 소매업 | 2021 | 466341.0 | 467878.0 | 467878.0 | 467878.0 | 467878.0 | 467878.0 | 467878.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 467878.0 | 1537.0 | 1537.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/H00/2021 | 강원특별자치도 | 32010 | 춘천시 | H00 | 운수 및 창고업 | 2021 | 344348.0 | 315527.0 | 315527.0 | 315527.0 | 315527.0 | 315527.0 | 315527.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 315527.0 | 28821.0 | 28821.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/I00/2021 | 강원특별자치도 | 32010 | 춘천시 | I00 | 숙박 및 음식점업 | 2021 | 302397.0 | 271924.0 | 271924.0 | 271924.0 | 271924.0 | 271924.0 | 271924.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 271924.0 | 30473.0 | 30473.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 강원특별자치도/32010/J00/2021 | 강원특별자치도 | 32010 | 춘천시 | J00 | 정보통신업 | 2021 | 222118.0 | 214212.0 | 214212.0 | 214212.0 | 214212.0 | 214212.0 | 214212.0 | AN0_lag_level | fallback_no_prior_router_evidence | 0.0 | 214212.0 | 7906.0 | 7906.0 | 0.0 | b6500093a29bd966514f9a33bdb722d3f29d4a453aac05ad5b5b74111ac15358 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |

## 8. Cohort Diagnostics

| group_type | group_id | baseline_wmape | challenger_wmape | delta_good | row_count | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| region | 강원특별자치도 | 0.069378111393411 | 0.08898961004689127 | -0.01961149865348026 | 570 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 경기도 | 0.07192912902174947 | 0.08248135117504722 | -0.01055222215329775 | 1415 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 경상남도 | 0.04732047035590623 | 0.04732047035590623 | 0.0 | 287 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 경상북도 | 0.07411907114806707 | 0.08026599867041743 | -0.006146927522350368 | 734 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 광주광역시 | 0.058717238958444995 | 0.07222026283896958 | -0.013503023880524587 | 235 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 대구광역시 | 0.07636673722665259 | 0.07636673722665259 | 0.0 | 123 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 대전광역시 | 0.06650363541987492 | 0.07594172190670016 | -0.009438086486825245 | 152 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 부산광역시 | 0.08602189871259537 | 0.08644419447763982 | -0.00042229576504444755 | 480 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 서울특별시 | 0.0787184970005932 | 0.0856413123038947 | -0.006922815303301494 | 1149 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 울산광역시 | 0.08286647165339335 | 0.08286647165339335 | 0.0 | 79 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 인천광역시 | 0.10699029920209506 | 0.10208822888202351 | 0.004902070320071547 | 450 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 전라남도 | 0.09193373046737875 | 0.10295864826672158 | -0.011024917799342823 | 1049 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 전북특별자치도 | 0.0631362679278753 | 0.07210404826572255 | -0.008967780337847245 | 621 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 제주특별자치도 | 0.07567977339896607 | 0.08619871407853293 | -0.010518940679566852 | 64 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 충청남도 | 0.06446068740010764 | 0.06446068740010764 | 0.0 | 237 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| region | 충청북도 | 0.06990216306334805 | 0.09247884364940769 | -0.022576680586059633 | 522 | 20d4dd1dbbae42bd173e254e71374ec1a6b05c670b7a1014178ad068cca31f14 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |

## 9. 서비스업 Temporal Component 결과

| policy_id | proxy_target | share_mae | weighted_share_mae | turning_point_proxy_accuracy | status | selection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TQ0_equal_quarter | service_production_quarter_share | 0.012457355959545604 | 0.013056686690638924 | 0.0061624649859943975 | baseline_component_proxy | component_baseline | 4325f3d8c636f51d206f7dcd6611a4d7e626d0309e6927b1140413bfbbfb5aaf | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| TQ3_service_prior_profile | service_production_quarter_share | 0.009433526502665058 | 0.009866055343345358 | 0.5929971988795518 | component_development_not_direct_gva | development_component_improved_not_promoted_to_direct_gva | 4325f3d8c636f51d206f7dcd6611a4d7e626d0309e6927b1140413bfbbfb5aaf | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |

## 10. 서비스업 Profile Sample

| c1_id | c1_nm | c2_id | c2_nm | year | quarter | value | actual_quarter_share | TQ0_equal_share | TQ3_service_prior_share | equal_abs_share_error | service_abs_share_error | TQ3_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11 | 서울특별시 | E | 수도 하수 및 폐기물 처리 원료 재생업 | 2019 | 1 | 75.2 | 0.20614035087719298 | 0.25 | 0.25 | 0.043859649122807015 | 0.043859649122807015 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 11 | 서울특별시 | E | 수도 하수 및 폐기물 처리 원료 재생업 | 2019 | 2 | 91.4 | 0.2505482456140351 | 0.25 | 0.25 | 0.0005482456140351033 | 0.0005482456140351033 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 11 | 서울특별시 | E | 수도 하수 및 폐기물 처리 원료 재생업 | 2019 | 3 | 97.0 | 0.26589912280701755 | 0.25 | 0.25 | 0.01589912280701755 | 0.01589912280701755 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 11 | 서울특별시 | E | 수도 하수 및 폐기물 처리 원료 재생업 | 2019 | 4 | 101.2 | 0.2774122807017544 | 0.25 | 0.25 | 0.027412280701754388 | 0.027412280701754388 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 11 | 서울특별시 | G | 도매 및 소매업 | 2019 | 1 | 101.6 | 0.24110109159943047 | 0.25 | 0.25 | 0.008898908400569533 | 0.008898908400569533 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 11 | 서울특별시 | G | 도매 및 소매업 | 2019 | 2 | 106.5 | 0.25272899857617465 | 0.25 | 0.25 | 0.002728998576174646 | 0.002728998576174646 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 11 | 서울특별시 | G | 도매 및 소매업 | 2019 | 3 | 103.2 | 0.2448979591836735 | 0.25 | 0.25 | 0.0051020408163265085 | 0.0051020408163265085 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 11 | 서울특별시 | G | 도매 및 소매업 | 2019 | 4 | 110.1 | 0.2612719506407214 | 0.25 | 0.25 | 0.011271950640721395 | 0.011271950640721395 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 11 | 서울특별시 | H | 운수 및 창고업 | 2019 | 1 | 133.7 | 0.244647758462946 | 0.25 | 0.25 | 0.005352241537053992 | 0.005352241537053992 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |
| 11 | 서울특별시 | H | 운수 및 창고업 | 2019 | 2 | 138.2 | 0.25288197621225983 | 0.25 | 0.25 | 0.002881976212259829 | 0.002881976212259829 | fallback_no_prior_service_profile | 2ba1754be14b51a8792d855f80f9e2fa01433233f0506fad63ea43db5cfe4d29 | 2628e66f87223228075e6faa187a8095c7a13eda | partial_statistics_estimation_phase29_gva | 2026-07-19T18:51:15+09:00 |

## 11. Promotion Decision

- Annual residual challenger는 최강 baseline보다 WMAPE가 낮을 때만 승격한다.
- Router는 OOF 적용률과 전체 WMAPE가 함께 개선될 때만 승격한다.
- 서비스업 profile은 direct GVA actual이 아니므로 개선되어도 분기 GVA forecast로 승격하지 않고 component 후보로만 둔다.

## 12. 최종 상태

```json
{
  "status": "phase29_gpt_recommendations_tested;annual_residual_not_promoted;router_not_promoted_if_no_material_gain;service_temporal_component_development",
  "target": "GVA",
  "target_unchanged": true,
  "phase28_reproduction_status": "pass",
  "annual_population_policy": "same_phase28_annual_backtest_population",
  "annual_best_baseline_policy": "AN0_lag_level",
  "annual_best_baseline_wmape": 0.07597875249742157,
  "annual_regime_residual_wmape": 0.08406987593896115,
  "annual_regime_residual_delta_good": -0.008091123441539574,
  "annual_regime_residual_selection": "not_selected",
  "router_baseline_wmape": 0.07597875249742157,
  "router_wmape": 0.07707712096189001,
  "router_delta_good": -0.0010983684644684383,
  "router_application_rate": 0.018121709317987022,
  "router_selection": "not_promoted",
  "service_equal_weighted_share_mae": 0.013056686690638924,
  "service_prior_weighted_share_mae": 0.009866055343345358,
  "service_prior_delta_good": 0.0031906313472935665,
  "service_temporal_selection": "development_component_improved_not_promoted_to_direct_gva",
  "material_degradation_group_count": 23,
  "recommended_next_primary": "build_release_qualified_employee_business_cube_and_sector_specific_A_B_D_F_features",
  "production_use": false,
  "official_statistics_claim": false,
  "claims_still_prohibited": "direct quarterly/monthly GVA accuracy, production use, official statistics equivalence, unqualified structural-feature promotion",
  "generated_at": "2026-07-19T18:51:15+09:00"
}
```

## 13. 다음 실행 권고

1. 종사자·사업체 cube의 release qualification을 완료해 IS1/SWD 계열을 strict track에서 평가한다.
2. A/B/D/F 업종별 특화 feature를 별도 수집하고, 공통 model이 아니라 sector module로 평가한다.
3. 서비스업 temporal profile은 forward release archive를 누적한 뒤 strict prospective component score로 전환한다.
4. Router는 oracle이 아니라 OOF/forward-only expected improvement로만 학습한다.

## 14. 아직 주장할 수 없는 내용

direct quarterly/monthly GVA accuracy, 읍면동×세부업종 official GVA equivalence, calibrated interval coverage, production use, official statistics equivalence.
