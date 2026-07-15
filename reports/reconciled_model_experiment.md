# 계층 정합 ML 개선 실험

## 목적

기존 ML 실험이 개별 행의 GVA를 독립적으로 보정하던 한계를 줄이기 위해, `연도 × 산업` 부모 총량 안에서 지역별 share 또는 Denton log-ratio residual을 예측한 뒤 부모 baseline 총량에 다시 정규화했다.

## 적용한 개선

1. `baseline_share`, lagged actual share, rolling share, lagged Denton log-ratio를 feature로 추가했다.
2. 사업체수·종사자수·매출액은 target-year 1월 1일 기준 공표 가능 연도만 사용했다.
3. Ridge는 표준화 후 학습했다.
4. XGBoost는 `reg:squarederror`와 `reg:absoluteerror`를 모두 튜닝 후보로 둔다.
5. 모든 ML 예측은 `연도 × 산업` 부모 baseline 총량과 일치하도록 reconciliation했다.

## XGBoost 상태

available

## 성능

| sector | model | count | MAPE | WMAPE | improvement vs baseline % | max aggregation error % | mean aggregation error % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A00 | baseline | 85 | 6.234074 | 3.37771 | 0.0 | 0.0 | 0.0 |
| A00 | ridge_share_reconciled | 85 | 13.97112 | 7.029503 | -108.114462 | 0.0 | 0.0 |
| A00 | ridge_log_ratio_reconciled | 85 | 12.929448 | 5.487283 | -62.455717 | 0.0 | 0.0 |
| A00 | xgboost_share_reconciled | 85 | 49.632008 | 14.36641 | -325.329883 | 0.0 | 0.0 |
| A00 | xgboost_log_ratio_reconciled | 85 | 7.071625 | 3.81644 | -12.988978 | 0.0 | 0.0 |
| B00 | baseline | 75 | 24.792847 | 14.432879 | 0.0 | 0.0 | 0.0 |
| B00 | ridge_share_reconciled | 75 | 24.902235 | 15.050752 | -4.28101 | 1e-10 | 0.0 |
| B00 | ridge_log_ratio_reconciled | 75 | 24.758377 | 11.894833 | 17.585168 | 1e-10 | 1e-10 |
| B00 | xgboost_share_reconciled | 75 | 89.60518 | 25.722308 | -78.220215 | 1e-10 | 0.0 |
| B00 | xgboost_log_ratio_reconciled | 75 | 25.331446 | 12.223197 | 15.310057 | 2e-10 | 1e-10 |
| C00 | baseline | 85 | 3.344871 | 3.428507 | 0.0 | 0.0 | 0.0 |
| C00 | ridge_share_reconciled | 85 | 4.009154 | 3.541835 | -3.305462 | 0.0 | 0.0 |
| C00 | ridge_log_ratio_reconciled | 85 | 3.34961 | 3.319018 | 3.193489 | 0.0 | 0.0 |
| C00 | xgboost_share_reconciled | 85 | 30.115265 | 12.493098 | -264.388872 | 0.0 | 0.0 |
| C00 | xgboost_log_ratio_reconciled | 85 | 3.615495 | 3.227615 | 5.85946 | 0.0 | 0.0 |
| D00 | baseline | 85 | 14.627973 | 10.016612 | 0.0 | 0.0 | 0.0 |
| D00 | ridge_share_reconciled | 85 | 26.304838 | 20.069698 | -100.364135 | 0.0 | 0.0 |
| D00 | ridge_log_ratio_reconciled | 85 | 21.763334 | 15.988327 | -59.618112 | 0.0 | 0.0 |
| D00 | xgboost_share_reconciled | 85 | 29.188723 | 15.831572 | -58.053162 | 0.0 | 0.0 |
| D00 | xgboost_log_ratio_reconciled | 85 | 15.828069 | 11.399397 | -13.804917 | 0.0 | 0.0 |
| ERS | baseline | 85 | 6.721624 | 7.207249 | 0.0 | 0.0 | 0.0 |
| ERS | ridge_share_reconciled | 85 | 7.52564 | 7.195678 | 0.160547 | 0.0 | 0.0 |
| ERS | ridge_log_ratio_reconciled | 85 | 7.639976 | 7.163908 | 0.601353 | 0.0 | 0.0 |
| ERS | xgboost_share_reconciled | 85 | 27.25528 | 20.958687 | -190.800096 | 0.0 | 0.0 |
| ERS | xgboost_log_ratio_reconciled | 85 | 6.921791 | 7.173618 | 0.466627 | 0.0 | 0.0 |
| F00 | baseline | 85 | 10.553488 | 9.311858 | 0.0 | 0.0 | 0.0 |
| F00 | ridge_share_reconciled | 85 | 14.159588 | 9.852116 | -5.801828 | 0.0 | 0.0 |
| F00 | ridge_log_ratio_reconciled | 85 | 10.277547 | 9.179248 | 1.424098 | 0.0 | 0.0 |
| F00 | xgboost_share_reconciled | 85 | 26.01123 | 21.464956 | -130.512063 | 0.0 | 0.0 |
| F00 | xgboost_log_ratio_reconciled | 85 | 9.852894 | 8.162108 | 12.34716 | 0.0 | 0.0 |
| G00 | baseline | 85 | 2.816885 | 2.708341 | 0.0 | 0.0 | 0.0 |
| G00 | ridge_share_reconciled | 85 | 3.780429 | 3.989391 | -47.300174 | 0.0 | 0.0 |
| G00 | ridge_log_ratio_reconciled | 85 | 3.037644 | 2.771283 | -2.324006 | 0.0 | 0.0 |
| G00 | xgboost_share_reconciled | 85 | 31.939646 | 14.498943 | -435.344072 | 0.0 | 0.0 |
| G00 | xgboost_log_ratio_reconciled | 85 | 3.063245 | 2.63849 | 2.579107 | 0.0 | 0.0 |
| H00 | baseline | 85 | 6.227758 | 7.360306 | 0.0 | 0.0 | 0.0 |
| H00 | ridge_share_reconciled | 85 | 8.934072 | 9.772425 | -32.771993 | 0.0 | 0.0 |
| H00 | ridge_log_ratio_reconciled | 85 | 6.995347 | 8.257326 | -12.187265 | 0.0 | 0.0 |
| H00 | xgboost_share_reconciled | 85 | 24.462532 | 15.116674 | -105.381053 | 0.0 | 0.0 |
| H00 | xgboost_log_ratio_reconciled | 85 | 6.321132 | 7.628169 | -3.639292 | 0.0 | 0.0 |
| I00 | baseline | 85 | 4.92436 | 4.325618 | 0.0 | 0.0 | 0.0 |
| I00 | ridge_share_reconciled | 85 | 5.96826 | 6.671463 | -54.231442 | 0.0 | 0.0 |
| I00 | ridge_log_ratio_reconciled | 85 | 4.810259 | 5.458739 | -26.195586 | 0.0 | 0.0 |
| I00 | xgboost_share_reconciled | 85 | 23.662473 | 19.300534 | -346.191365 | 0.0 | 0.0 |
| I00 | xgboost_log_ratio_reconciled | 85 | 4.63352 | 4.318539 | 0.163653 | 0.0 | 0.0 |
| J00 | baseline | 85 | 4.156309 | 3.494074 | 0.0 | 0.0 | 0.0 |
| J00 | ridge_share_reconciled | 85 | 9.697657 | 5.322341 | -52.324793 | 0.0 | 0.0 |
| J00 | ridge_log_ratio_reconciled | 85 | 4.979587 | 3.933151 | -12.566334 | 0.0 | 0.0 |
| J00 | xgboost_share_reconciled | 85 | 48.311901 | 18.068 | -417.104103 | 0.0 | 0.0 |
| J00 | xgboost_log_ratio_reconciled | 85 | 3.934673 | 3.525524 | -0.900095 | 0.0 | 0.0 |
| K00 | baseline | 85 | 2.885566 | 3.645751 | 0.0 | 0.0 | 0.0 |
| K00 | ridge_share_reconciled | 85 | 3.453544 | 4.955288 | -35.91954 | 0.0 | 0.0 |
| K00 | ridge_log_ratio_reconciled | 85 | 3.162727 | 3.705487 | -1.63851 | 0.0 | 0.0 |
| K00 | xgboost_share_reconciled | 85 | 26.966433 | 14.761414 | -304.893642 | 0.0 | 0.0 |
| K00 | xgboost_log_ratio_reconciled | 85 | 2.754825 | 3.630302 | 0.423754 | 0.0 | 0.0 |
| L00 | baseline | 85 | 10.754781 | 10.631291 | 0.0 | 0.0 | 0.0 |
| L00 | ridge_share_reconciled | 85 | 9.887469 | 9.827072 | 7.564641 | 0.0 | 0.0 |
| L00 | ridge_log_ratio_reconciled | 85 | 10.739032 | 9.792366 | 7.891092 | 0.0 | 0.0 |
| L00 | xgboost_share_reconciled | 85 | 34.503626 | 21.989451 | -106.837072 | 0.0 | 0.0 |
| L00 | xgboost_log_ratio_reconciled | 85 | 9.939843 | 9.981435 | 6.112672 | 0.0 | 0.0 |
| MN0 | baseline | 85 | 4.645286 | 3.069596 | 0.0 | 0.0 | 0.0 |
| MN0 | ridge_share_reconciled | 85 | 4.885557 | 3.829924 | -24.769644 | 0.0 | 0.0 |
| MN0 | ridge_log_ratio_reconciled | 85 | 4.883529 | 3.395919 | -10.630813 | 0.0 | 0.0 |
| MN0 | xgboost_share_reconciled | 85 | 28.400269 | 16.276321 | -430.2431 | 0.0 | 0.0 |
| MN0 | xgboost_log_ratio_reconciled | 85 | 4.384525 | 3.001755 | 2.210095 | 0.0 | 0.0 |
| O00 | baseline | 85 | 1.845232 | 1.715613 | 0.0 | 0.0 | 0.0 |
| O00 | ridge_share_reconciled | 85 | 2.373387 | 2.311106 | -34.710217 | 0.0 | 0.0 |
| O00 | ridge_log_ratio_reconciled | 85 | 1.920493 | 1.812858 | -5.668236 | 0.0 | 0.0 |
| O00 | xgboost_share_reconciled | 85 | 9.46993 | 7.587965 | -342.28885 | 0.0 | 0.0 |
| O00 | xgboost_log_ratio_reconciled | 85 | 1.796202 | 1.566327 | 8.701613 | 0.0 | 0.0 |
| P00 | baseline | 85 | 2.332779 | 2.227541 | 0.0 | 0.0 | 0.0 |
| P00 | ridge_share_reconciled | 85 | 2.324002 | 2.401492 | -7.809104 | 0.0 | 0.0 |
| P00 | ridge_log_ratio_reconciled | 85 | 2.129982 | 2.171229 | 2.527989 | 0.0 | 0.0 |
| P00 | xgboost_share_reconciled | 85 | 12.492731 | 10.444632 | -368.886184 | 0.0 | 0.0 |
| P00 | xgboost_log_ratio_reconciled | 85 | 2.240225 | 2.128573 | 4.442926 | 0.0 | 0.0 |
| Q00 | baseline | 85 | 1.713591 | 1.488346 | 0.0 | 0.0 | 0.0 |
| Q00 | ridge_share_reconciled | 85 | 1.933539 | 1.621696 | -8.95961 | 0.0 | 0.0 |
| Q00 | ridge_log_ratio_reconciled | 85 | 1.847016 | 1.540647 | -3.514035 | 0.0 | 0.0 |
| Q00 | xgboost_share_reconciled | 85 | 17.252054 | 10.162885 | -582.830807 | 0.0 | 0.0 |
| Q00 | xgboost_log_ratio_reconciled | 85 | 1.74259 | 1.539531 | -3.439052 | 0.0 | 0.0 |
| __ALL__ | baseline | 1350 | 6.652706 | 4.388658 | 0.0 | 0.0 | 0.0 |
| __ALL__ | ridge_share_reconciled | 1350 | 8.889162 | 5.166916 | -17.733394 | 1e-10 | 0.0 |
| __ALL__ | ridge_log_ratio_reconciled | 1350 | 7.701073 | 4.541873 | -3.491158 | 1e-10 | 0.0 |
| __ALL__ | xgboost_share_reconciled | 1350 | 31.401361 | 14.72602 | -235.547222 | 1e-10 | 0.0 |
| __ALL__ | xgboost_log_ratio_reconciled | 1350 | 6.702529 | 4.230372 | 3.606706 | 2e-10 | 0.0 |

## 최저 WMAPE 모델

| sector | baseline WMAPE | best model | best WMAPE | improvement % |
| --- | ---: | --- | ---: | ---: |
| A00 | 3.37771 | baseline | 3.37771 | 0.0 |
| B00 | 14.432879 | ridge_log_ratio_reconciled | 11.894833 | 17.585168 |
| C00 | 3.428507 | xgboost_log_ratio_reconciled | 3.227615 | 5.85946 |
| D00 | 10.016612 | baseline | 10.016612 | 0.0 |
| ERS | 7.207249 | ridge_log_ratio_reconciled | 7.163908 | 0.601353 |
| F00 | 9.311858 | xgboost_log_ratio_reconciled | 8.162108 | 12.34716 |
| G00 | 2.708341 | xgboost_log_ratio_reconciled | 2.63849 | 2.579107 |
| H00 | 7.360306 | baseline | 7.360306 | 0.0 |
| I00 | 4.325618 | xgboost_log_ratio_reconciled | 4.318539 | 0.163653 |
| J00 | 3.494074 | baseline | 3.494074 | 0.0 |
| K00 | 3.645751 | xgboost_log_ratio_reconciled | 3.630302 | 0.423754 |
| L00 | 10.631291 | ridge_log_ratio_reconciled | 9.792366 | 7.891092 |
| MN0 | 3.069596 | xgboost_log_ratio_reconciled | 3.001755 | 2.210095 |
| O00 | 1.715613 | xgboost_log_ratio_reconciled | 1.566327 | 8.701613 |
| P00 | 2.227541 | xgboost_log_ratio_reconciled | 2.128573 | 4.442926 |
| Q00 | 1.488346 | baseline | 1.488346 | 0.0 |
| __ALL__ | 4.388658 | xgboost_log_ratio_reconciled | 4.230372 | 3.606706 |

## 해석 기준

`baseline`은 기존 Denton/indicator rolling 예측이다. `*_share_reconciled`는 지역 share를 직접 예측하고, `*_log_ratio_reconciled`는 Denton 예측값 대비 실제값의 로그비율을 예측한 뒤 정규화한다. 양수 개선은 같은 official actual 구간에서 baseline WMAPE보다 낮을 때만 인정한다.

## 결론

현재 통합 실험에서는 직접 share 예측보다 Denton log-ratio residual을 예측한 뒤 부모 총량에 reconciliation하는 방식이 가장 안정적이다. 전체 기준 최저 WMAPE가 baseline보다 낮다면, 다음 단계는 이 방식을 시군구 rolling backtest와 세부산업 proxy share 검증으로 확장하는 것이다.