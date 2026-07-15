# Global Model Leakage Checks

## Negative Control

| check | count | WMAPE | MAPE | imp | material | worst |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_only_reconstruction | 1350 | 4.383005 | 6.857004 | 0.128796 | 18 | -24.407891 |
| region_code_shuffle | 1350 | 4.387251 | 6.847128 | 0.032067 | 14 | -12.592918 |
| sector_code_shuffle | 1350 | 4.341919 | 6.694459 | 1.064987 | 7 | -7.708296 |
| target_shuffle | 1350 | 4.568092 | 6.883214 | -4.088578 | 32 | -91.420494 |

## 판단 기준

Target shuffle 또는 baseline-only reconstruction이 baseline을 유의미하게 이기면 누수 또는 baseline 재구성 위험을 의심한다.