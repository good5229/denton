# 지역·산업별 GVA 모델 개선 최종 보고서

## 1. 작업 목적

기존 ML 실험은 Ridge/XGBoost를 적용했음에도 비례형 Denton/indicator baseline보다 낮은 성능을 보였다. 이번 작업에서는 모델 복잡도만 늘리는 대신, 현재 문제가 계층적 총량 제약을 갖는 배분·benchmarking 문제라는 점을 반영해 다음 개선안을 검증했다.

1. 하위 지역 GVA를 독립적으로 예측하지 않고, 부모 총량 안의 share 또는 Denton 대비 log-ratio residual을 예측한다.
2. 예측 후 `연도 × 산업` 부모 총량과 일치하도록 reconciliation한다.
3. 현재 저장소 데이터로 적용 가능한 lagged share, rolling share, baseline share, lagged residual, 구조통계 share/productivity feature를 추가한다.
4. Ridge는 표준화 후 학습하고, XGBoost는 `reg:squarederror`와 `reg:absoluteerror`를 모두 포함해 파라미터 탐색한다.
5. 모든 학습·튜닝은 target year 이전 데이터만 사용한다.

## 2. 구현 산출물

| 산출물 | 설명 |
| --- | --- |
| `scripts/run_reconciled_model_experiment.py` | share/log-ratio residual + parent reconciliation 통합 실험 |
| `reports/reconciled_model_experiment.md` | 모델별·산업별 WMAPE, 개선율, 총량 정합성 보고서 |
| `data/processed/reconciled_model_predictions.csv` | 행 단위 예측값. CP949 |
| `data/processed/reconciled_model_comparison.csv` | 모델별 성능 비교. CP949 |
| `data/processed/reconciled_model_tuning.csv` | target year별 선택 파라미터. CP949 |

`data/`는 `.gitignore` 정책상 저장소에 포함하지 않는다.

## 3. 검증 설계

검증 단위는 official actual이 존재하는 `시도 × 대분류 × 연간` rolling backtest 구간이다.

- target year의 actual은 학습과 파라미터 튜닝에 사용하지 않는다.
- 파라미터 튜닝은 target year 이전 학습 구간 중 마지막 연도를 validation year로 사용한다.
- 구조통계는 `target-year 1월 1일` 기준 공표 가능 연도만 사용한다.
- 전기·가스 관련 외생변수는 공표 지연을 고려해 사용 가능한 최신 분기만 사용한다.
- ML raw prediction은 최종 산출 전 `연도 × 산업` 부모 baseline 총량으로 정규화한다.

## 4. 비교 모델

| 모델 | 설명 |
| --- | --- |
| `baseline` | 기존 Denton/indicator rolling prediction |
| `ridge_share_reconciled` | 지역 share를 Ridge로 예측 후 부모 총량 정규화 |
| `ridge_log_ratio_reconciled` | Denton 대비 log-ratio residual을 Ridge로 예측 후 부모 총량 정규화 |
| `xgboost_share_reconciled` | 지역 share를 XGBoost로 예측 후 부모 총량 정규화 |
| `xgboost_log_ratio_reconciled` | Denton 대비 log-ratio residual을 XGBoost로 예측 후 부모 총량 정규화 |

XGBoost는 `objective`, `n_estimators`, `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`, `reg_lambda`, `min_child_weight` 조합을 target year별 validation WMAPE 기준으로 탐색했다.

## 5. 전체 결과

| 모델 | 비교 건수 | MAPE | WMAPE | baseline 대비 개선율 |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1,350 | 6.652706 | 4.388658 | 0.000000% |
| ridge_share_reconciled | 1,350 | 8.889162 | 5.166916 | -17.733394% |
| ridge_log_ratio_reconciled | 1,350 | 7.701073 | 4.541873 | -3.491158% |
| xgboost_share_reconciled | 1,350 | 31.401361 | 14.726020 | -235.547222% |
| xgboost_log_ratio_reconciled | 1,350 | 6.702529 | 4.230372 | 3.606706% |

전체 기준 최저 WMAPE는 `xgboost_log_ratio_reconciled`다. 기존 baseline 대비 WMAPE가 `4.388658`에서 `4.230372`로 낮아져 `3.606706%` 개선되었다.

## 6. 산업별 최저 모델

| 산업 | baseline WMAPE | 최저 모델 | 최저 WMAPE | 개선율 |
| --- | ---: | --- | ---: | ---: |
| A00 | 3.377710 | baseline | 3.377710 | 0.000000% |
| B00 | 14.432879 | ridge_log_ratio_reconciled | 11.894833 | 17.585168% |
| C00 | 3.428507 | xgboost_log_ratio_reconciled | 3.227615 | 5.859460% |
| D00 | 10.016612 | baseline | 10.016612 | 0.000000% |
| ERS | 7.207249 | ridge_log_ratio_reconciled | 7.163908 | 0.601353% |
| F00 | 9.311858 | xgboost_log_ratio_reconciled | 8.162108 | 12.347160% |
| G00 | 2.708341 | xgboost_log_ratio_reconciled | 2.638490 | 2.579107% |
| H00 | 7.360306 | baseline | 7.360306 | 0.000000% |
| I00 | 4.325618 | xgboost_log_ratio_reconciled | 4.318539 | 0.163653% |
| J00 | 3.494074 | baseline | 3.494074 | 0.000000% |
| K00 | 3.645751 | xgboost_log_ratio_reconciled | 3.630302 | 0.423754% |
| L00 | 10.631291 | ridge_log_ratio_reconciled | 9.792366 | 7.891092% |
| MN0 | 3.069596 | xgboost_log_ratio_reconciled | 3.001755 | 2.210095% |
| O00 | 1.715613 | xgboost_log_ratio_reconciled | 1.566327 | 8.701613% |
| P00 | 2.227541 | xgboost_log_ratio_reconciled | 2.128573 | 4.442926% |
| Q00 | 1.488346 | baseline | 1.488346 | 0.000000% |

## 7. 해석

이번 실험의 핵심 결론은 세 가지다.

1. 단순 share 직접 예측은 부적합하다. `xgboost_share_reconciled`는 대부분 산업에서 크게 악화되었다. share 자체가 지역별 고정효과와 sparse cell에 민감하고, 관측 연수가 짧아 XGBoost가 불안정하게 반응한 것으로 보인다.
2. Denton log-ratio residual 방식은 유효하다. baseline을 완전히 대체하지 않고, baseline의 체계적 오차만 제한적으로 보정하기 때문에 성능이 안정적이다.
3. 모든 ML 예측을 부모 총량에 reconciliation한 결과, aggregation error는 부동소수점 오차 수준으로 유지되었다. 즉, ML 개선과 계층 정합성은 동시에 달성 가능하다.

## 8. 남은 문제

전기·가스(`D00`)와 농림어업(`A00`)은 이번 구조에서도 baseline이 최저였다. 기존 가설대로 가격·환율 변수만으로는 지역별 구조 차이를 충분히 설명하지 못한다.

| 산업 | 추가 필요 feature |
| --- | --- |
| A00 | 경지면적, 품목별 생산량, 축산 사육두수, 기상·재해 지표 |
| B00 | 광산 수, 광종별 생산량, 광산 개폐, 광업 세부 생산지수 |
| D00 | 지역별 발전량, 발전원 구성, 전력판매량, 도시가스 판매량 |

## 9. 다음 구현 우선순위

1. `xgboost_log_ratio_reconciled`를 시군구 rolling backtest에 적용한다.
2. 시군구에서는 parent를 `시도 × 산업 × 연도`로 두고, 하위 시군구 share/log-ratio residual을 예측한다.
3. 세부산업에서는 official GVA가 없으므로 proxy share backtest에 동일한 구조를 적용한다.
4. 읍면동은 official actual이 없으므로 서울시 2024 proxy stability 검증과 결합한다.
5. 대시보드에는 baseline과 reconciled ML을 나란히 표시하되, ML 채택 여부는 산업별 confidence rule로 제한한다.

## 10. 운영 판단

현재 단계에서 전체 산출값을 무조건 ML로 대체하는 것은 적절하지 않다. 권장 운영 방식은 다음과 같다.

| 조건 | 운영 판단 |
| --- | --- |
| 산업별 backtest에서 reconciled ML이 baseline보다 개선 | 해당 산업에 한해 ML 보정 후보로 채택 |
| baseline이 최저 | 기존 Denton/indicator 유지 |
| direct share 모델만 개선 | 추가 검증 전 채택 보류 |
| official actual이 없는 세부산업·읍면동 | proxy 검증과 confidence grade를 함께 표시 |

따라서 현재 가장 유망한 방향은 `Denton/indicator baseline + XGBoost 또는 Ridge log-ratio residual + parent reconciliation`이다.
