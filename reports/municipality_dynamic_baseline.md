# 시군구 Dynamic Baseline

## 과거 share smoothing 후보

| model | count | wmape | mape | baseline_wmape | improvement_pct | material_degradation_count | worst_sector_year_improvement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ewma_0_4_share | 3233 | 9.438167 | 49.996205 | 9.174139 | -2.877961 | 6 | -34.59357 |
| ewma_0_7_share | 3233 | 9.238424 | 49.651305 | 9.174139 | -0.70072 | 3 | -14.50093 |
| last_share | 3233 | 9.191897 | 49.608291 | 9.174139 | -0.193567 | 1 | -3.522731 |
| mean2_share | 3233 | 9.359194 | 49.828475 | 9.174139 | -2.017132 | 4 | -27.542209 |
| mean3_share | 3233 | 9.359194 | 49.828475 | 9.174139 | -2.017132 | 4 | -27.542209 |

## 해석

ML residual보다 baseline share 자체의 smoothing이 더 나은지 확인하기 위한 통계적 baseline 비교다.