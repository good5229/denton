# 고오차 산업 진단

## 대상

Official actual 기준 상위 오차에 반복적으로 등장한 농림어업(`A00`), 광업(`B00`), 전기·가스(`D00`)를 별도 진단했다.

## 시도 연간 official actual 기준 성능

| sector | count | MAPE | WMAPE |
| --- | ---: | ---: | ---: |
| A00 농업 임업 및 어업 | 126 | 7.319074 | 2.017884 |
| B00 광업 | 112 | 24.056143 | 8.685341 |
| D00 전기 가스 증기 및 공기 조절 공급업 | 126 | 16.103114 | 9.813384 |

## 전기·가스 외생변수 보정 실험

| model | count | MAPE |
| --- | ---: | ---: |
| baseline | 126 | 16.103114 |
| energy_exogenous_adjusted | 126 | 19.175563 |

## 권고

| sector | recommended model | leakage rule |
| --- | --- | --- |
| A00 | baseline Denton 유지 + 농업 특화 proxy 보강 | target year에 아직 공표되지 않은 작황·총조사 자료는 사용 금지 |
| B00 | 지역별 최근 share shrinkage + 품목/광산 활동 proxy | 소표본 지역은 전국/권역 평균으로 shrinkage하고 target 이후 사업체 변화를 학습에 넣지 않음 |
| D00 | 전기가스 전용 외생변수 residual correction | forecast_as_of 이전에 공표된 분기 exogenous만 사용 |

## 결론

전체 산업에 동일한 ML 보정을 적용하기보다, baseline이 안정적인 산업은 Denton/indicator 방식을 유지하고 고오차 산업에는 산업별 전용 feature와 shrinkage를 적용하는 방식이 더 안전하다.