# 시군구 오차 분해

## Parent × Share 조합

| scenario | count | wmape | mape | improvement_vs_forecast_baseline_pct | actual_sum | absolute_error_sum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| actual_parent_baseline_share | 5211 | 5.998639 | 39.032004 | 30.255926 | 3594975107.009207 | 215649584.927546 |
| actual_parent_ml_share | 5211 | 6.041785 | 44.935037 | 29.754282 | 3594975107.009207 | 217200666.855353 |
| forecast_parent_baseline_share | 5211 | 8.60093 | 43.604314 | 0.0 | 3594975107.009207 | 309201291.280908 |
| forecast_parent_ml_share | 5211 | 8.632153 | 48.897559 | -0.363019 | 3594975107.009207 | 310323744.979621 |

## 해석

actual parent에서도 ML share가 baseline share보다 나쁘면 문제는 부모 총량보다 하위 share 모델에 있다.