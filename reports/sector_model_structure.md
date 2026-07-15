# 산업별 모델 구조 비교

- 대상: XGBoost log-ratio residual, rolling target-year backtest
- 같은 고정 파라미터로 global, sector, 사전 산업군 모델을 비교했다.

## 구조별 성능

| structure | WMAPE | MAPE | improvement % | degraded | material degraded | worst |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| global_model | 3.958199 | 6.564673 | 5.364796 | 34 | 14 | -40.729135 |
| sector_group_model:A00 | 4.13471 | 7.362601 | -22.411643 | 3 | 3 | -148.027896 |
| sector_group_model:B00 | 12.267104 | 25.813733 | 15.005845 | 1 | 0 | -0.508037 |
| sector_group_model:C00 | 3.259044 | 3.583059 | 4.942757 | 2 | 2 | -9.521961 |
| sector_group_model:D00 | 12.277894 | 17.708181 | -22.57532 | 4 | 3 | -57.529342 |
| sector_group_model:F00 | 7.914097 | 9.39962 | 15.010553 | 0 | 0 | 2.780971 |
| sector_group_model:market_services | 4.757127 | 5.009164 | 4.691719 | 9 | 6 | -30.745581 |
| sector_group_model:public_social_services | 2.677622 | 3.137028 | -2.629081 | 12 | 8 | -30.303426 |
| sector_group_model:trade_transport_food | 3.871598 | 4.613735 | -0.004042 | 7 | 5 | -44.473554 |
| sector_model | 4.206694 | 6.829643 | 4.146221 | 28 | 20 | -148.027896 |

## 해석

표본 수가 작은 산업에서는 sector model의 분산이 커질 수 있으므로, global 또는 사전 산업군 모델이 downside를 줄이는지 함께 확인해야 한다.