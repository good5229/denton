# Global Reconciled ML 최종 검증 보고서

## 핵심 표

| policy | WMAPE | MAPE | imp | years | material | worst | ML rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| global_adaptive_shrinkage | 4.070304 | 6.471429 | 7.254024 | 5 | 14 | -24.114262 | 1.0 |
| global_full_strength | 4.106585 | 6.576717 | 6.42732 | 5 | 16 | -59.388193 | 1.0 |
| global_regret_adaptive | 4.216585 | 6.540841 | 3.920857 | 5 | 2 | -4.817736 | 0.60963 |
| global_regret_lower_bound | 4.339367 | 6.681335 | 1.123141 | 3 | 3 | -22.664298 | 0.211111 |
| global_regret_mean | 4.224058 | 6.65118 | 3.750583 | 5 | 11 | -59.388193 | 0.60963 |

## 결론

공통 평가 1,350건 기준 `global_fixed_full`의 WMAPE는 4.124072이고 baseline 대비 개선율은 6.028854%다. 기존 3.958199는 2018년을 포함한 1,620건 모집단의 값이었으므로 sector/full ML과 직접 비교하면 안 된다.

성능형 후보는 `global_adaptive_shrinkage`다. WMAPE 4.070304, MAPE 6.471429로 가장 좋지만 material degradation 14건과 worst -24.114262가 남는다.

안정형 후보는 `global_regret_adaptive`다. WMAPE 4.216585로 성능형보다 낮지는 않지만 MAPE 6.540841, material degradation 2건, worst -4.817736으로 strict downside 조건을 통과했다.

## 지시서 질문 답변

1. 실제 baseline 대비 개선율: 공통 평가 기준 `global_fixed_full` 6.028854%, `global_tuned_full` 6.427320%.
2. WMAPE 3.958199는 동일 모집단에서는 재현되지 않는다. 2019~2023 공통 모집단에서는 4.124072다.
3. seed 5개 모두 baseline보다 개선됐다. WMAPE 범위는 4.124072~4.152353이다.
4. global model이 sector model보다 좋은 이유는 표본 pooling 효과가 크기 때문으로 보인다. `global_no_sector_id`도 WMAPE 4.123385로 유지됐다.
5. 산업코드 제거 시 성능은 유지됐고, 지역코드 제거 시에도 WMAPE 4.137599로 개선이 유지됐다.
6. F6/F7은 common global feature에 포함되지 않았다. 즉 현재 global full은 사실상 F6/F7 제거 모델이다.
7. nested tuning은 `global_tuned_full`을 4.106585까지 낮췄지만 MAPE와 worst-case는 악화됐다.
8. tuning 후보는 2,304개 fold-candidate로 평가됐다. outer year별 선택 파라미터는 `data/processed/global_model_tuning_results.csv`에 저장했다.
9. global regret/adaptive 정책 중 `global_regret_adaptive`가 downside를 크게 줄였다.
10. adaptive shrinkage 단독은 material degradation 14건으로 9건 이하를 달성하지 못했다.
11. `global_adaptive_shrinkage`, `global_regret_adaptive` 모두 MAPE가 baseline보다 낮다.
12. worst -10% 이내 제한은 `global_regret_adaptive`가 달성했다.
13. region/sector ID 제거 실험상 대규모 ID 암기만으로 설명되지는 않는다. 다만 규모 가중치 구조 실험은 다음 과제로 남는다.
14. target shuffle은 baseline보다 악화됐고 baseline-only reconstruction은 개선폭 0.128796%에 그쳤다. 큰 누수 신호는 발견되지 않았다.
15. 시군구 pilot의 기본 후보는 sector별 독립 모델보다 global/common-feature log-ratio residual model이 더 타당하다. 다만 성능형과 안정형 정책을 병행해 pilot해야 한다.
