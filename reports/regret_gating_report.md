# Expected Regret Gating

## 정책 비교

| policy | WMAPE | MAPE | improvement % | degraded | material degraded | worst | ML rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| regret_lower_bound_gt_0 | 4.314728 | 6.61696 | 1.684563 | 4 | 3 | -7.520253 | 0.247407 |
| regret_mean_gt_0.0 | 4.253818 | 6.603694 | 3.072458 | 14 | 9 | -40.498293 | 0.548148 |
| regret_mean_gt_0.1 | 4.254405 | 6.60332 | 3.059076 | 14 | 9 | -40.498293 | 0.522963 |
| regret_mean_gt_0.2 | 4.260208 | 6.601404 | 2.926848 | 14 | 9 | -40.498293 | 0.51037 |
| regret_mean_gt_0.5 | 4.258395 | 6.597815 | 2.96818 | 11 | 8 | -40.498293 | 0.472593 |

## 해석

사전 gating은 target year 이전 산업별 WMAPE 개선 이력으로 다음 연도 ML 적용 여부를 고른다. Oracle과 달리 평가연도 actual/loss는 선택에 쓰지 않는다.