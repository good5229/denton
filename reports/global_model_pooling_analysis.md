# Global Model Pooling Analysis

## 산업·지역 식별자 비교

| policy | WMAPE | MAPE | imp | material | worst |
| --- | ---: | ---: | ---: | ---: | ---: |
| global_baseline_only | 4.383005 | 6.857004 | 0.128796 | 18 | -24.407891 |
| global_fixed_full | 4.124072 | 6.520107 | 6.028854 | 14 | -40.729135 |
| global_no_region_id | 4.137599 | 6.493424 | 5.72062 | 15 | -28.550244 |
| global_no_residual_features | 4.155938 | 6.552091 | 5.302759 | 16 | -26.59212 |
| global_no_sector_id | 4.123385 | 6.476411 | 6.044502 | 14 | -35.939848 |
| global_residual_only | 4.376168 | 6.623138 | 0.284583 | 8 | -25.9399 |

## 해석

산업 one-hot 또는 지역 one-hot 제거 시 성능이 얼마나 유지되는지를 통해 pooling이 단순 ID 암기인지 공통 패턴 학습인지 진단한다.