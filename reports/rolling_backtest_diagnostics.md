# Rolling Backtest 진단 리포트

## 목적

기존 rolling 예측 검증은 전체 평균 MAPE 중심이라, 어느 지역·산업·연도에서 오차가 커지는지 파악하기 어려웠다. 이번 단계에서는 동일한 비교 원자료를 분해해 모델 개선 우선순위를 볼 수 있는 진단 테이블을 생성했다.

## 입력

- `data/processed/rolling_annual_prediction_comparisons.csv`
  - 2017-2023년 타깃 연도별 one-year-ahead 예측 연간합
  - 실제 연간 GRVA가 존재하는 조합만 비교 가능

## 산출물

모든 CSV는 CP949로 저장했다.

| 파일 | 설명 |
| --- | --- |
| `rolling_backtest_summary.csv` | 전체 비교 건수, 기간, MAPE, WMAPE |
| `rolling_backtest_by_year.csv` | 타깃 연도별 오차 |
| `rolling_backtest_by_region.csv` | 지역별 오차 |
| `rolling_backtest_by_sector.csv` | 산업별 오차 |
| `rolling_backtest_by_method.csv` | 지표/추정 방법별 오차 |
| `rolling_backtest_error_matrix.csv` | 지역 × 산업별 오차 행렬 |
| `rolling_backtest_top_errors.csv` | 절대 percent error 기준 상위 100건 |

## 지표 해석

- `mape`: 개별 비교 건의 절대 percent error 평균이다. 작은 산업·지역의 상대 오차도 동일 가중으로 반영한다.
- `wmape`: 절대오차 합계를 실제값 합계로 나눈 값이다. 부가가치 규모가 큰 산업·지역의 오차를 더 크게 반영한다.
- `signed_mpe`: percent error의 평균이다. 양수면 과대추정, 음수면 과소추정 경향이 있다.
- `aggregate_percent_error`: 그룹 전체 합계 기준의 과대/과소 추정률이다.

## 현재 결과

비교 가능한 rolling backtest는 총 2,002건이다. 전체 MAPE는 기존 리포트와 같은 `6.407741%`이며, WMAPE는 `2.762787%`다. 평균 상대오차는 소규모 지역·산업의 변동성까지 민감하게 반영하고, WMAPE는 전체 부가가치 총량 관점의 정합성을 보여준다.

## 개선 우선순위

1. `rolling_backtest_top_errors.csv`에서 반복적으로 등장하는 지역·산업 조합을 먼저 확인한다.
2. `rolling_backtest_by_method.csv`에서 national GDP share 방식의 오차가 특정 산업에 집중되는지 확인한다.
3. `rolling_backtest_error_matrix.csv`를 대시보드 또는 히트맵으로 연결해 지역 × 산업별 취약 구간을 표시한다.
4. 개선 실험은 전체 MAPE보다 해당 취약 조합의 MAPE와 WMAPE를 같이 낮추는지를 기준으로 평가한다.

## 한계

이 진단은 연간 실제 GRVA가 존재하는 기간까지만 평가할 수 있다. 2024-2025년 분기 추정치는 실제 연간 벤치마크가 공개되기 전까지 동일한 방식으로 오차를 확정할 수 없으며, 추후 실제값 공개 시 같은 스크립트로 재검증해야 한다.
