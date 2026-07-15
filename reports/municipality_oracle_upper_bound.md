# 시군구 Oracle Upper Bound

## Oracle 단위별 전체 상한

| oracle_group | count | baseline_wmape | oracle_wmape | oracle_improvement_pct | best_alpha_zero_rate | ml_selected_group_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sector_year | 5211 | 8.587335 | 8.583195 | 0.048205 | 0.555556 | 0.407407 |
| province_sector_year | 5211 | 8.587335 | 8.549942 | 0.435441 | 0.538874 | 0.391421 |
| sector_size_year | 5211 | 8.587335 | 8.554392 | 0.383616 | 0.518519 | 0.419753 |
| province_type_sector_year | 5211 | 8.587335 | 8.579722 | 0.088648 | 0.444444 | 0.481481 |
| stability_regime_sector_year | 5211 | 8.587335 | 8.583021 | 0.050227 | 0.6 | 0.375 |

## 판단

province×sector×year oracle 개선율이 1% 미만이므로 현재 ML residual에는 실용적으로 이용 가능한 신호가 부족하다.