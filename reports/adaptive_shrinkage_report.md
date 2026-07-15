# Adaptive Residual Shrinkage

## 결과

| policy | WMAPE | MAPE | improvement % | degraded | material degraded | worst |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| adaptive_shrinkage | 4.282983 | 6.574093 | 2.40791 | 15 | 13 | -26.057692 |

## 해석

행별 baseline-ML 괴리가 클수록 residual 적용 강도를 낮추는 정책이다. gamma는 같은 산업의 target 이전 연도에서만 선택했다.