# Reconciled ML 차기 실험 통합 보고서

## 핵심 결론

이번 라운드는 부모 총량, soft reconciliation, adaptive shrinkage, expected regret gating, feature ablation, 모델 구조를 같은 rolling backtest 관점에서 확장했다. 모든 모델 선택과 강도 선택은 target year 이전 정보만 사용했다.

가장 중요한 결과는 다음과 같다.

1. 부모 총량 보정 ML은 아직 baseline을 이기지 못했다. 따라서 현재 운영에서는 부모 총량을 강제로 ML 보정하지 않는 것이 낫다.
2. Full ML은 WMAPE 최저권이지만 downside가 크다.
3. Expected regret gating은 WMAPE 4.254 수준까지 개선하면서 material degradation을 9건까지 줄였다.
4. Adaptive shrinkage는 MAPE를 6.574까지 낮추지만 downside가 아직 남아 있다.
5. 고정 파라미터 재학습 기준으로는 공통 feature 기반 global model이 WMAPE 3.958로 가장 좋았다. 이 결과는 다음 실험에서 full grid tuning 대상으로 올려야 한다.

## 1. 부모 총량 모델

| model | WMAPE | MAPE | bias | 판단 |
| --- | ---: | ---: | ---: | --- |
| parent_baseline | 3.049944 | 3.387301 | 0.824806 | 현재 최선 |
| parent_xgboost_log_ratio | 3.191052 | 3.562313 | -0.164647 | bias는 줄지만 WMAPE 악화 |
| parent_shrunken_sector_log_ratio | 3.195671 | 3.506772 | 0.88217 | WMAPE 악화 |
| parent_global_mean_log_ratio | 3.256218 | 3.505263 | 1.102634 | WMAPE 악화 |

부모 총량 ML은 체계적 bias를 줄이는 효과는 일부 있었지만 전체 WMAPE 기준으로는 baseline보다 나빴다. 따라서 soft reconciliation의 운영 부모값도 `parent_baseline`을 유지했다.

## 2. Soft Reconciliation

부모 총량 후보가 baseline으로 유지되면서 shock이 없는 실제 forecast parent 조건에서는 hard, soft, no reconciliation이 동일한 결과가 됐다.

| method | WMAPE | MAPE | degraded sector-years | worst sector-year |
| --- | ---: | ---: | ---: | ---: |
| hard/no/soft, shock 0 | 4.230372 | 6.702529 | 28 | -62.748315 |

다만 parent shock에서는 soft reconciliation이 의미가 있었다. 예를 들어 parent가 -3% 잘못 들어왔을 때 hard는 WMAPE 4.967272였지만 soft 0.25는 4.276287까지 완화됐다. 즉 soft reconciliation은 “부모 총량을 개선하는 모델”이 아니라 “부모 총량 오류가 클 때 하위 셀로 전파되는 충격을 줄이는 안전장치”로 보는 것이 맞다.

## 3. Adaptive Shrinkage

| policy | WMAPE | MAPE | improvement % | material degraded | worst |
| --- | ---: | ---: | ---: | ---: | ---: |
| adaptive_shrinkage | 4.282983 | 6.574093 | 2.40791 | 13 | -26.057692 |

Adaptive shrinkage는 MAPE를 baseline 6.652706보다 낮췄고 current safe보다도 낮았다. 다만 material degradation이 13건으로 목표치 9건 이하에는 아직 못 미친다.

## 4. Expected Regret Gating

| policy | WMAPE | MAPE | improvement % | material degraded | worst | ML rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| regret_mean_gt_0.0 | 4.253818 | 6.603694 | 3.072458 | 9 | -40.498293 | 0.548148 |
| regret_mean_gt_0.1 | 4.254405 | 6.603320 | 3.059076 | 9 | -40.498293 | 0.522963 |
| regret_lower_bound_gt_0 | 4.314728 | 6.616960 | 1.684563 | 3 | -7.520253 | 0.247407 |

`regret_mean_gt_0.0`은 WMAPE와 material degradation의 균형이 가장 좋다. 반대로 `regret_lower_bound_gt_0`은 보수적이라 worst-case를 -10% 안쪽으로 묶지만 WMAPE 개선폭이 작다.

## 5. Feature Ablation

고정 파라미터 기준 feature ablation에서는 `full` WMAPE가 4.206694였다. 이는 기존 full-grid tuned 결과와 파라미터 체계가 다르므로 절대 비교보다는 feature group의 방향성을 본다.

주요 결과:

| variant | WMAPE | improvement % |
| --- | ---: | ---: |
| full | 4.206694 | 4.146221 |
| drop_F6_F7_indicator_exogenous | 4.152036 | 5.391659 |
| drop_F4_rolling_residual | 4.185982 | 4.618184 |
| no_residual_features | 4.202940 | 4.231773 |
| residual_features_only | 4.481641 | -2.118721 |

잔차 feature만으로는 baseline보다 나빠졌다. 즉 XGBoost 개선은 단순 residual persistence가 아니라 baseline/share, 구조통계, 지역 정적 특성과의 상호작용에서 나온 것으로 해석된다.

## 6. 모델 구조

| structure | WMAPE | MAPE | improvement % | material degraded |
| --- | ---: | ---: | ---: | ---: |
| global_model | 3.958199 | 6.564673 | 5.364796 | 14 |
| sector_model | 4.206694 | 6.829643 | 4.146221 | 20 |
| sector_group_model:F00 | 7.914097 | 9.399620 | 15.010553 | 0 |
| sector_group_model:B00 | 12.267104 | 25.813733 | 15.005845 | 0 |

가장 큰 발견은 global model이다. 업종별 외생변수까지 모두 쓰지는 않고 공통 feature만 사용했는데도 sector model보다 WMAPE가 낮았다. 이는 산업별 표본 부족 문제가 더 컸고, 시도×산업×연도 전체를 함께 학습하는 편이 안정적일 수 있음을 뜻한다.

## 운영 후보

현재 기준 운영 후보는 두 갈래다.

1. 안정형: `regret_lower_bound_gt_0`
   - worst-case가 -7.52%로 목표 범위 안이다.
   - 다만 WMAPE 개선은 1.68%로 작다.

2. 성능형: `regret_mean_gt_0.0`
   - WMAPE 4.253818, MAPE 6.603694, material degradation 9건이다.
   - worst-case가 -40.50%라 산업별 추가 안전장치가 필요하다.

다음 라운드의 최우선 과제는 `global_model`에 대해 full grid tuning, regret gating, adaptive shrinkage를 결합해 운영정책 표에 다시 올리는 것이다. 이 결과가 유지되면 시군구 pilot의 기본 모델도 sector model이 아니라 global/common-feature model을 우선 후보로 삼는 편이 합리적이다.

## 산출물

- `reports/parent_total_model_report.md`
- `reports/soft_reconciliation_report.md`
- `reports/adaptive_shrinkage_report.md`
- `reports/regret_gating_report.md`
- `reports/reconciled_feature_ablation.md`
- `reports/sector_model_structure.md`
- `reports/reconciled_operational_policy_report.md`
- `data/processed/parent_total_predictions.csv`
- `data/processed/soft_reconciliation_predictions.csv`
- `data/processed/adaptive_shrinkage_predictions.csv`
- `data/processed/regret_gating_predictions.csv`
- `data/processed/reconciled_feature_ablation_predictions.csv`
- `data/processed/sector_model_structure_predictions.csv`
