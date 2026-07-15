# 부모 총량 예측 및 오차 분해

- XGBoost 상태: `available`
- 운영 후보 부모 모델: `parent_baseline`
- 모든 부모 모델은 target year 이전의 부모 오차만 사용했다.

## 부모 총량 모델 비교

| model | WMAPE | MAPE | bias | improved years | improved sectors | worst sector |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| parent_baseline | 3.049944 | 3.387301 | 0.824806 | 0 | 0 | 0.0 |
| parent_ensemble | 3.356946 | 3.704488 | -0.396843 | 2 | 6 | -357.184614 |
| parent_global_mean_log_ratio | 3.256218 | 3.505263 | 1.102634 | 0 | 7 | -294.87134 |
| parent_ridge_log_ratio | 3.673105 | 4.0029 | -0.618964 | 3 | 5 | -553.296336 |
| parent_rolling2_log_ratio | 3.353785 | 3.856463 | 0.262521 | 2 | 3 | -73.814699 |
| parent_sector_mean_log_ratio | 3.250145 | 3.721638 | 0.635975 | 2 | 4 | -69.585018 |
| parent_sector_median_log_ratio | 3.284605 | 3.853699 | 0.842621 | 1 | 4 | -67.875268 |
| parent_shrunken_sector_log_ratio | 3.195671 | 3.506772 | 0.88217 | 1 | 6 | -175.861608 |
| parent_xgboost_log_ratio | 3.191052 | 3.562313 | -0.164647 | 1 | 6 | -441.142245 |

## 해석

부모 총량은 하위 지역 share와 독립된 병목이다. 부모 예측을 바꾸면 모든 하위 셀에 같은 방향의 스케일 오차가 전파되므로, 하위 ML의 개선폭은 부모 모델 정확도와 함께 해석해야 한다.