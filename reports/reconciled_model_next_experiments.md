# Reconciled ML 차기 실험 통합 보고서

## 1. Rolling Gated Hybrid Backtest

| policy | WMAPE | MAPE | improvement % | improved years | degraded sector-years | worst year improvement | worst sector improvement | ML adoption rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_all | 4.388658 | 6.652706 | 0.0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| full_ml_all | 4.230372 | 6.702529 | 3.606707 | 5 | 28 | 2.442246 | -62.748315 | 1.0 |
| oracle_sector_policy | 4.136514 | 6.513263 | 5.745349 | 5 | 0 | 3.013449 | 0.0 | 0.672593 |
| rolling_best_policy | 4.25192 | 6.595536 | 3.115712 | 4 | 13 | 0.0 | -40.498293 | 0.535556 |
| rolling_grade_a_only | 4.326322 | 6.646287 | 1.420386 | 3 | 4 | 0.0 | -7.520253 | 0.234815 |
| rolling_grade_ab | 4.292715 | 6.609141 | 2.186158 | 3 | 9 | 0.0 | -11.467425 | 0.385926 |
| safe_selected_current | 4.286962 | 6.600451 | 2.317235 | 3 | 11 | 0.0 | -11.467425 | 1.0 |

## 2. Parent Total 민감도

| scenario | shock | child WMAPE | parent error | improvement % | mean scale |
| --- | ---: | ---: | ---: | ---: | ---: |
| forecast_parent_baseline | 0.0 | 4.388658 | 0.824806 | 0.0 | 0.996851 |
| forecast_parent_full_ml | 0.0 | 4.230372 | 0.824806 | 3.606707 | 1.0 |
| actual_parent_baseline | 0.0 | 2.715054 | 0.0 | 38.134745 | 0.993891 |
| actual_parent_full_ml | 0.0 | 2.479867 | 0.0 | 43.493718 | 0.996958 |
| full_ml_parent_shock | -0.1 | 10.177724 | 9.257675 | -131.909718 | 0.9 |
| full_ml_parent_shock | -0.05 | 6.151936 | 4.216434 | -40.178065 | 0.95 |
| full_ml_parent_shock | -0.03 | 4.967272 | 2.199938 | -13.184301 | 0.97 |
| full_ml_parent_shock | -0.01 | 4.316793 | 0.183442 | 1.637503 | 0.99 |
| full_ml_parent_shock | 0.0 | 4.230372 | 0.824806 | 3.606707 | 1.0 |
| full_ml_parent_shock | 0.01 | 4.305144 | 1.833054 | 1.90294 | 1.01 |
| full_ml_parent_shock | 0.03 | 5.112654 | 3.84955 | -16.49699 | 1.03 |
| full_ml_parent_shock | 0.05 | 6.570884 | 5.866046 | -49.724237 | 1.05 |
| full_ml_parent_shock | 0.1 | 11.183109 | 10.907286 | -154.818441 | 1.1 |

## 3. 단순 Residual Benchmark

| model | count | MAPE | WMAPE | improvement % |
| --- | ---: | ---: | ---: | ---: |
| lag1_residual | 1350 | 9.591406 | 5.703492 | -29.959826 |
| lag1_shrunk_residual | 1350 | 7.730019 | 4.814111 | -9.694382 |
| region_mean_residual | 1350 | 6.933201 | 4.667139 | -6.345474 |
| rolling_mean_residual | 1350 | 8.093864 | 4.948659 | -12.760193 |
| sector_mean_residual | 1350 | 6.986478 | 4.49236 | -2.362957 |
| xgboost_log_ratio | 1350 | 6.702529 | 4.230372 | 3.606707 |
| zero_residual | 1350 | 6.652706 | 4.388658 | 0.0 |

## 4. 결론

rolling policy는 사후 전체기간 grade를 쓰지 않고 target year 이전 성능 이력만 사용한다. `oracle_sector_policy`는 운영용이 아니라 후보 모델군의 이론적 상한선이다. Parent total 민감도는 현재 개선이 하위 share 보정인지 parent 총량 오차에 민감한지 구분하기 위한 진단이다.

상세 CSV는 `data/processed/next_*` 파일로 저장되며 CP949 정책을 따른다.