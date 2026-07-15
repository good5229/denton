# 시군구 Share Stability Regime

## Regime 정책 비교

| policy | count | wmape | mape | baseline_wmape | improvement_pct | material_degradation_count | worst_sector_year_improvement | ml_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_all | 5211 | 8.587335 | 43.634419 | 8.587335 | 0.0 | 0 | 0.0 | 0.0 |
| ml_all | 5211 | 8.632153 | 48.897559 | 8.587335 | -0.52191 | 4 | -6.741615 | 0.935137 |
| ml_low_uncertainty_only | 5211 | 8.586885 | 43.633959 | 8.587335 | 0.005241 | 0 | -0.018332 | 0.265208 |
| ml_stable_intermediate | 5211 | 8.596219 | 43.637046 | 8.587335 | -0.103454 | 0 | -1.331261 | 0.146037 |
| ml_stable_large_cell_only | 5211 | 8.587374 | 43.634313 | 8.587335 | -0.000454 | 0 | -0.023607 | 0.047208 |
| ml_stable_only | 5211 | 8.587397 | 43.634738 | 8.587335 | -0.00073 | 0 | -0.025969 | 0.057954 |

## 해석

Stable group에만 ML을 적용해도 baseline을 이기지 못하면 share stability만으로는 현재 ML의 적용 대상을 충분히 선별하지 못한다.