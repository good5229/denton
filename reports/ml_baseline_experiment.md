# ML Baseline 실험

## 목적

시도 대분류 official actual 구간에서 기존 Denton/indicator baseline 대비 ML 보정이 실제로 개선되는지 확인했다. 현재 환경에서는 `scikit-learn`이 아키텍처 문제로 사용할 수 없어, `numpy` 기반 Ridge와 작은 회귀트리/부스팅을 직접 구현했다.

## 모델

- Baseline: 기존 rolling annual prediction
- Ridge log-level: `log(actual)`을 직접 예측
- Ridge residual correction: `log(actual / baseline)`을 예측한 뒤 baseline에 곱해 보정
- Tree residual correction: 회귀트리로 `log(actual / baseline)` 보정
- Boosted tree residual correction: 작은 회귀트리를 순차적으로 더해 residual 보정

모든 모델은 target year 이전의 official actual만 학습한다. target year 또는 그 이후의 값은 학습에 들어가지 않으므로 데이터 유출을 피한다.

## 전체 성능

| model | comparison_count | MAPE | WMAPE |
| --- | ---: | ---: | ---: |
| Denton/indicator baseline | 1430 | 6.4012 | 2.947683 |
| Ridge log-level | 1430 | 6.859974 | 3.806656 |
| Ridge residual correction | 1430 | 6.770334 | 3.607363 |
| Tree residual correction | 1430 | 6.60846 | 3.29769 |
| Boosted tree residual correction | 1430 | 6.510591 | 3.162085 |

가장 낮은 WMAPE 모델은 `Denton/indicator baseline`이다.

## 해석

이 실험은 최종 산출값을 대체하기 위한 것이 아니라, ML 보정이 baseline의 체계적 오차를 줄일 수 있는지 보는 진단이다. 다음 단계에서는 시군구·상세산업에 바로 level 예측을 적용하기보다, 상위 총량 정합성을 유지하는 residual correction 또는 share correction으로 제한하는 것이 안전하다.