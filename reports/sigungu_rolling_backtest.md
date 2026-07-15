# 시군구 대분류 Rolling Backtest

## 목적

시군구 대분류 연간 값의 기존 `0%` 오차는 공식 벤치마크로 닫힌 회계 정합성이다. 예측력 검증을 위해 target year의 시군구 actual을 숨기고, target 이전에 관측된 최신 시군구/시도 비중만 사용해 예측했다.

## 방법

```text
share_{sigungu, sector, base_year}
  = actual_sigungu_gva / actual_parent_sido_gva

prediction_{target_year}
  = parent_sido_rolling_prediction_{target_year}
    * latest_pre_target_share
```

예측 기준일은 매 target year의 1월 1일로 보고, target year의 시군구 actual은 평가에만 사용한다. 따라서 이 검증은 데이터 유출을 피하는 out-of-sample 방식이다.

## 산출물

| 파일 | 설명 |
| --- | --- |
| `sigungu_annual_rolling_backtest.csv` | 시군구×대분류×연도 rolling backtest 결과 |
| `sigungu_annual_rolling_backtest_by_year.csv` | 연도별 요약 |
| `sigungu_annual_rolling_backtest_by_sector.csv` | 산업별 요약 |
| `sigungu_annual_rolling_backtest_by_region.csv` | 시도별 요약 |
| `sigungu_annual_rolling_backtest_skipped.csv` | 부모 예측 또는 과거 share 부재로 제외된 조합 |

## 1차 결과

전체 비교 행은 `11,732`건이다. 연도별 WMAPE는 `7.42~9.71%` 수준으로, 시군구 연간 벤치마크 정합성의 `0%` 오차와 달리 실제 out-of-sample 난이도를 보여준다.

산업별로는 제조업(`C00`) WMAPE `6.61%`, 도매 및 소매업(`G00`) WMAPE `6.39%`처럼 비교적 안정적인 업종이 있는 반면, 광업(`B00`) MAPE `207.95%`, 전기·가스(`D00`) MAPE `132.87%`처럼 지역별 규모가 작거나 구조 변화가 큰 업종은 단순 최신 share 방식만으로는 부족하다.

이 결과는 다음 단계를 뒷받침한다.

1. 시군구 대분류 예측은 official actual 기준 검증 가능하다.
2. 산업별로 동일한 모델을 쓰기보다 고오차 업종에는 별도 예측식을 적용해야 한다.
3. 세부산업·읍면동 추정은 부모 시군구 예측의 오차까지 함께 전파되므로 신뢰등급에 이 backtest 결과를 반영해야 한다.
