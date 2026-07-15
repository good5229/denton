# 시군구 ML 보정 중단 판단

## 실험 결과

| oracle_group | oracle_improvement_pct | best_alpha_zero_rate |
| --- | ---: | ---: |
| sector_year | 0.048205 | 0.555556 |
| province_sector_year | 0.435441 | 0.538874 |
| sector_size_year | 0.383616 | 0.518519 |
| province_type_sector_year | 0.088648 | 0.444444 |
| stability_regime_sector_year | 0.050227 | 0.6 |

## Baseline 유지 근거

현재 데이터의 ML residual은 세분화 oracle에서도 개선 상한이 작고, share stability regime만으로 적용 대상을 안정적으로 선별하지 못한다면 시군구 운영은 baseline을 유지한다.

## 권장 운영

- 시도×산업: locked global policy 유지
- 시군구×산업: Denton/indicator baseline 유지
- 읍면동×산업: proxy 배분과 confidence grade만 제공