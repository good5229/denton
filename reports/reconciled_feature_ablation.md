# Reconciled Feature Ablation

- 대상: XGBoost log-ratio residual, rolling target-year backtest
- 튜닝 비용을 통제하기 위해 고정 파라미터를 사용했다. 따라서 기존 full-grid tuned 결과와 절대값을 직접 동일시하지 않고, feature group 간 상대 비교로 해석한다.

## Feature Variant 비교

| variant | WMAPE | MAPE | improvement % | degraded | material degraded | worst |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| core_F0 | 4.423741 | 7.015508 | -0.799405 | 47 | 31 | -55.901763 |
| core_F0_F3 | 4.409676 | 6.910806 | -0.478921 | 41 | 32 | -81.045511 |
| core_F0_F3_F5 | 4.411766 | 6.922627 | -0.526549 | 45 | 32 | -82.222311 |
| core_F0_F3_F5_F6F7 | 4.449979 | 7.117967 | -1.397262 | 43 | 32 | -79.519821 |
| core_F0_F5 | 4.428197 | 7.002242 | -0.900938 | 46 | 27 | -54.690536 |
| drop_F10_time | 4.243576 | 6.90851 | 3.305837 | 32 | 27 | -151.500756 |
| drop_F1_lagged_share | 4.211825 | 6.848268 | 4.029307 | 27 | 20 | -151.500756 |
| drop_F2_rolling_share | 4.484979 | 7.129129 | -2.194773 | 40 | 26 | -78.229203 |
| drop_F3_lagged_residual | 4.22001 | 6.852941 | 3.842811 | 28 | 20 | -141.425604 |
| drop_F4_rolling_residual | 4.185982 | 6.79911 | 4.618184 | 26 | 21 | -153.209543 |
| drop_F5_structural | 4.200917 | 6.85143 | 4.277859 | 24 | 20 | -148.653604 |
| drop_F6_F7_indicator_exogenous | 4.152036 | 6.610731 | 5.391659 | 28 | 21 | -150.342616 |
| drop_F8_area_static | 4.2093 | 6.839135 | 4.086855 | 27 | 22 | -150.485789 |
| drop_F9_method_static | 4.204746 | 6.859243 | 4.190607 | 26 | 20 | -151.922134 |
| full | 4.206694 | 6.829643 | 4.146221 | 28 | 20 | -148.027896 |
| no_lagged_residual | 4.22001 | 6.852941 | 3.842811 | 28 | 20 | -141.425604 |
| no_residual_features | 4.20294 | 6.849819 | 4.231773 | 30 | 22 | -154.627701 |
| residual_features_only | 4.481641 | 6.91592 | -2.118721 | 40 | 35 | -69.423863 |
| structural_features_only | 4.428197 | 7.002242 | -0.900938 | 46 | 27 | -54.690536 |

## 해석

`drop_*`는 해당 feature group 제거 후 성능이다. `core_*`는 baseline/share와 지정 feature만 사용한 축약 모델이다. residual feature 제거와 structural-only 결과를 함께 보아 XGBoost 개선이 단순 잔차 복사인지 확인한다.