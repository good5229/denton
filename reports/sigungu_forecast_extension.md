# 시군구 2024-2025 예측 확장

## 문제

기존 대시보드의 시군구 연간 화면은 `sigungu_denton_constraint_diagnostics.csv`를 사용했다. 이 파일의 `estimated_annual_sum`은 독립 예측값이 아니라, 공식 시군구 연간 GRVA를 벤치마크로 놓고 분기 추정치를 합산한 값이다. 따라서 `benchmark_annual_gva`와 반드시 일치한다.

이 값이 실제값과 같게 나오는 것은 모델이 예측을 완벽하게 맞혔다는 의미가 아니다. 연간 공식값을 제약조건으로 넣었기 때문에 회계적으로 닫힌 것이다.

## 추가 산출

공식 시군구 GRVA가 아직 없는 2024-2025년 예측을 별도 산출했다.

입력:

- `sigungu_quarterly_gva_estimates.csv`: 2019-2023 시군구 분기 benchmarked estimate
- `rolling_quarterly_gva_predictions.csv`: 2024-2025 시도 산업별 rolling 분기 예측

방법:

```text
share_{r,s,q} = GVA_{sigungu r, sector s, 2023 same quarter q}
                / sum(GVA_{same parent sido, sector s, 2023 same quarter q})

forecast_{r,s,t} = parent_sido_forecast_{s,t} * share_{r,s,same quarter}
```

즉, 2023년 같은 분기의 시군구/부모 시도 비중을 2024-2025년 부모 시도 rolling 예측에 적용했다.

## 산출물

모든 CSV는 CP949로 저장했다.

| 파일 | 행 수 | 설명 |
| --- | ---: | --- |
| `sigungu_quarterly_gva_forecasts.csv` | 19,600 | 2024-2025 시군구 × 산업 × 분기 예측 |
| `sigungu_annual_gva_forecasts.csv` | 4,868 | 분기 예측의 연간 합산 |
| `sigungu_gva_forecast_skipped.csv` | 56 | 부모 시도 rolling 예측이 없어 산출하지 못한 조합 |
| `sigungu_gva_forecast_summary.csv` | 1 | 산출 요약 |

## 대시보드 해석

- 2019-2023: 공식 시군구 연간 GRVA를 벤치마크로 사용한 구간이다. annual 화면에서는 예측값과 actual이 같아야 정상이다.
- 2024-2025: 공식 시군구 GRVA가 아직 없는 예측 구간이다. actual은 비어 있고 predicted만 표시된다.
- 분기: 공식 시군구 분기 GRVA는 없으므로 전 기간이 추정/예측 경로다.

## 한계

2024-2025 예측은 시군구별 고유 충격을 직접 반영하지 못한다. 같은 시도 안에서 2023년의 시군구 비중이 유지된다는 보수적 가정에 기반한다. 향후 공식 시군구 GRVA가 공개되면 동일 구조로 오차를 재검증해야 한다.
