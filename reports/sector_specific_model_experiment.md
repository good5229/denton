# A/B/D 산업별 전용 모델 실험

## 원칙

- target year의 actual은 학습에 사용하지 않는다.
- 구조변수는 target-year 1월 1일 기준 공개 가능하다고 볼 수 있는 최신 연도만 사용한다.
- `sector_structural_business_stats.csv`의 사업체수·종사자수·매출액은 보수적으로 `target_year-2` 이하만 feature로 사용한다.
- 전기가스 외생변수는 공표 지연 2개월을 가정하고, 예측 기준일 이전에 공표 가능한 분기만 사용한다.
- XGBoost는 선택 의존성으로 두며, 로컬 런타임에서 로드 가능한 경우에만 `xgboost_residual` 후보를 평가한다.

## XGBoost 실행 상태

사용 가능

## 성능

| sector | model | count | MAPE | WMAPE |
| --- | --- | ---: | ---: | ---: |
| A00 | baseline | 90 | 5.899851 | 1.797803 |
| A00 | ridge_residual | 90 | 6.153773 | 2.500063 |
| A00 | tree_residual | 90 | 6.150631 | 1.985339 |
| A00 | boosted_tree_residual | 90 | 5.890988 | 1.961636 |
| A00 | xgboost_residual | 90 | 6.287555 | 1.939266 |
| B00 | baseline | 80 | 23.514604 | 9.343151 |
| B00 | ridge_residual | 80 | 26.833854 | 11.397997 |
| B00 | tree_residual | 80 | 29.769451 | 12.256364 |
| B00 | boosted_tree_residual | 80 | 24.847224 | 10.026531 |
| B00 | xgboost_residual | 80 | 26.928584 | 11.826337 |
| D00 | baseline | 90 | 14.325351 | 9.324589 |
| D00 | ridge_residual | 90 | 19.15904 | 13.876146 |
| D00 | tree_residual | 90 | 21.282216 | 11.253885 |
| D00 | boosted_tree_residual | 90 | 17.456888 | 9.984279 |
| D00 | xgboost_residual | 90 | 16.813108 | 10.624145 |
| __ALL__ | baseline | 260 | 14.236294 | 5.60281 |
| __ALL__ | ridge_residual | 260 | 17.018698 | 8.179897 |
| __ALL__ | tree_residual | 260 | 18.655817 | 6.698649 |
| __ALL__ | boosted_tree_residual | 260 | 15.727257 | 6.01795 |
| __ALL__ | xgboost_residual | 260 | 16.282102 | 6.363223 |

## 해석

이 실험은 산업별 특화 feature와 파라미터 탐색이 baseline을 개선하는지 검정한다. 성능이 개선되지 않는 산업은 기존 Denton/indicator baseline을 유지하고, 개선되는 산업만 제한적으로 residual correction을 채택하는 것이 안전하다.

## 결론

- `A00`: baseline WMAPE 1.797803가 최저이므로 ML 보정은 진단용으로만 보관한다.
- `B00`: baseline WMAPE 9.343151가 최저이므로 ML 보정은 진단용으로만 보관한다.
- `D00`: baseline WMAPE 9.324589가 최저이므로 ML 보정은 진단용으로만 보관한다.

현재 수집된 구조변수와 외생변수만으로는 `A00/B00/D00` 어느 산업에서도 baseline보다 낮은 WMAPE를 안정적으로 얻지 못했다. 따라서 기본 산출에는 기존 Denton/indicator baseline을 유지하고, ML 보정값은 진단용 후보로만 보관한다.

다음 보강 후보는 산업별로 더 직접적인 설명변수다. 농림어업은 경지면적·품목별 생산량·기상 및 재해 지표, 광업은 광산 수·광종별 생산량·광산 개폐 정보, 전기·가스는 지역별 발전량·발전원 구성·전력판매량이 우선순위다.