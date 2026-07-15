# Reconciled ML 운영정책 통합 결과

- 부모 총량 후보: `parent_baseline`
- XGBoost 상태: `available`

## 최종 정책 비교

| policy | WMAPE | MAPE | improvement % | improved years | degraded | material degraded | worst | oracle regret | effective ML rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 4.388658 | 6.652706 | 0.0 | 0 | 0 | 0 | 0.0 | 0.250438 | 0.0 |
| current_safe | 4.286962 | 6.600451 | 2.317235 | 3 | 11 | 6 | -11.467425 | 0.148742 | 0.474074 |
| full_ml | 4.230372 | 6.702529 | 3.606707 | 5 | 28 | 21 | -62.748315 | 0.092152 | 1.0 |
| hard_reconciliation_best_parent | 4.230372 | 6.702529 | 3.606707 | 5 | 28 | 21 | -62.748315 | 0.092152 | 1.0 |
| soft_reconciliation_uncertainty | 4.230372 | 6.702529 | 3.606707 | 5 | 28 | 21 | -62.748315 | 0.092152 | 1.0 |
| adaptive_shrinkage | 4.282983 | 6.574093 | 2.40791 | 3 | 15 | 13 | -26.057692 | 0.144763 | 0.6 |
| regret_mean_gt_0.0 | 4.253818 | 6.603694 | 3.072458 | 4 | 14 | 9 | -40.498293 | 0.115598 | 0.548148 |
| regret_mean_gt_0.1 | 4.254405 | 6.60332 | 3.059076 | 4 | 14 | 9 | -40.498293 | 0.116185 | 0.522963 |

## 판단

운영 후보는 전체 WMAPE 개선과 downside 제한을 함께 봐야 한다. `current_safe`, `adaptive_shrinkage`, `expected regret gate`, `soft reconciliation` 중 WMAPE와 material degradation이 동시에 낮은 정책을 시군구 pilot 후보로 올리는 것이 합리적이다.