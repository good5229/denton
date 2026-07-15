# A/B/D 산업별 전용 모델 실험

## 원칙

- target year의 actual은 학습에 사용하지 않는다.
- 구조변수는 target-year 1월 1일 기준 공개 가능하다고 볼 수 있는 최신 연도만 사용한다.
- `sector_structural_business_stats.csv`의 사업체수·종사자수·매출액은 보수적으로 `target_year-2` 이하만 feature로 사용한다.
- 전기가스 외생변수는 공표 지연 2개월을 가정하고, 예측 기준일 이전에 공표 가능한 분기만 사용한다.

## 성능

| sector | model | count | MAPE | WMAPE |
| --- | --- | ---: | ---: | ---: |
| A00 | baseline | 90 | 5.899851 | 1.797803 |
| A00 | ridge_residual | 90 | 6.153773 | 2.500063 |
| A00 | tree_residual | 90 | 6.150631 | 1.985339 |
| A00 | boosted_tree_residual | 90 | 5.890988 | 1.961636 |
| B00 | baseline | 80 | 23.514604 | 9.343151 |
| B00 | ridge_residual | 80 | 26.833854 | 11.397997 |
| B00 | tree_residual | 80 | 29.769451 | 12.256364 |
| B00 | boosted_tree_residual | 80 | 24.847224 | 10.026531 |
| D00 | baseline | 90 | 14.325351 | 9.324589 |
| D00 | ridge_residual | 90 | 19.15904 | 13.876146 |
| D00 | tree_residual | 90 | 21.282216 | 11.253885 |
| D00 | boosted_tree_residual | 90 | 17.456888 | 9.984279 |
| __ALL__ | baseline | 260 | 14.236294 | 5.60281 |
| __ALL__ | ridge_residual | 260 | 17.018698 | 8.179897 |
| __ALL__ | tree_residual | 260 | 18.655817 | 6.698649 |
| __ALL__ | boosted_tree_residual | 260 | 15.727257 | 6.01795 |

## 해석

이 실험은 산업별 특화 feature와 파라미터 탐색이 baseline을 개선하는지 검정한다. 성능이 개선되지 않는 산업은 기존 Denton/indicator baseline을 유지하고, 개선되는 산업만 제한적으로 residual correction을 채택하는 것이 안전하다.

## 결론

현재 수집된 구조변수와 외생변수만으로는 `A00/B00/D00` 어느 산업에서도 baseline보다 낮은 WMAPE를 얻지 못했다. 특히 광업과 전기·가스는 비선형 모델을 쓰더라도 표본 수가 작고 지역별 구조 변화가 커서 과적합 위험이 더 크게 나타났다.

따라서 현 단계의 운영 정책은 다음과 같다.

1. 세 산업 모두 기본 산출에는 기존 Denton/indicator baseline을 유지한다.
2. ML 보정값은 채택하지 않고 진단용 후보로만 보관한다.
3. 광업은 광산 수, 광종별 생산량, 광산 개폐 정보 같은 더 직접적인 지역 feature가 필요하다.
4. 농림어업은 경지면적, 품목별 생산량, 기상·재해 지표가 필요하다.
5. 전기·가스는 가격지표만으로는 부족하며 지역별 발전량, 발전원 구성, 전력판매량 feature가 필요하다.
