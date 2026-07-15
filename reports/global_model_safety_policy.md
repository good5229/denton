# Global Model Safety Policy

## 정책 비교

| policy | WMAPE | MAPE | imp | years | material | worst | p05 | ML rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| global_adaptive_shrinkage | 4.070304 | 6.471429 | 7.254024 | 5 | 14 | -24.114262 | -13.795036 | 1.0 |
| global_full_strength | 4.106585 | 6.576717 | 6.42732 | 5 | 16 | -59.388193 | -22.114825 | 1.0 |
| global_regret_adaptive | 4.216585 | 6.540841 | 3.920857 | 5 | 2 | -4.817736 | -0.37865 | 0.60963 |
| global_regret_lower_bound | 4.339367 | 6.681335 | 1.123141 | 3 | 3 | -22.664298 | -0.570941 | 0.211111 |
| global_regret_mean | 4.224058 | 6.65118 | 3.750583 | 5 | 11 | -59.388193 | -22.114825 | 0.60963 |

## Downside-Constrained 선택

| policy | WMAPE | MAPE | tier | material | worst |
| --- | ---: | ---: | ---: | ---: | ---: |
| global_regret_adaptive | 4.216585 | 6.540841 | strict | 2 | -4.817736 |