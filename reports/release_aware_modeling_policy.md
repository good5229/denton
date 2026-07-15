# 공표 시점 기준 데이터 적용 정책

## 왜 필요한가

예측 모델에서는 데이터의 관측시점과 공표시점을 구분해야 한다. 예를 들어 2024년 지표를 2024년 중에 예측하면서, 2025년 12월에야 공개되는 2024년 연간 자료를 feature로 쓰면 사후 정보를 사용한 것이다. 이런 누수는 backtest 성능을 과대평가한다.

따라서 이번 작업부터 예측용 산출물에는 다음 원칙을 적용한다.

> 예측 기준일(`forecast_as_of`) 이전에 공표되었다고 볼 수 있는 데이터만 feature/proxy로 사용한다.

## 구현 원칙

`scripts/data_availability.py`에 공통 유틸을 추가했다.

- `period_end(period, frequency)`: 연/분기/월 관측기간의 종료일 계산
- `available_date(period, frequency, publication_lag_months)`: 관측기간 종료일에 공표 지연 개월 수를 더한 공개 가능일
- `is_available_as_of(...)`: 특정 예측 기준일에 해당 데이터가 사용 가능한지 판정
- `annual_forecast_origin(target_year)`: 연간 예측의 기준일. 현재는 목표연도 1월 1일을 기본값으로 둔다.

판정식은 다음과 같다.

```text
period_end + publication_lag_months < forecast_as_of
```

## 전기·가스 외생변수 적용

`scripts/test_energy_augmented_indicator.py`를 수정해 기존 FRED-only 자료가 아니라 `energy_exogenous_with_ecos_quarterly.csv`를 사용하도록 했다.

다만 목표연도 전체의 외생변수 평균을 쓰지 않는다. 목표연도 1월 1일 현재 공표된 최신 4개 분기만 사용한다.

예시는 다음과 같다.

| 목표연도 | 예측 기준일 | 공표 지연 | 사용 가능한 최신 분기 예시 |
|---:|---|---:|---|
| 2024 | 2024-01-01 | 1개월 | 2023Q3 |
| 2025 | 2025-01-01 | 1개월 | 2024Q3 |

생성된 산출물:

- `energy_augmented_backtest.csv`
- `energy_augmented_feature_diagnostics.csv`
- `energy_augmented_summary.csv`
- `energy_augmented_release_calendar.csv`

결과적으로 lag-aware 조건에서는 ECOS 외생변수를 붙인 보정 모델의 MAPE가 기준 Denton 예측보다 악화되었다.

| 항목 | 값 |
|---|---:|
| 비교 건수 | 126 |
| 기준 MAPE | 16.103114 |
| 보정 MAPE | 19.175563 |
| MAPE 변화 | +3.072449 |
| 채택 여부 | no |

따라서 현재 전기·가스 추정에는 ECOS 외생변수를 자동 보정 factor로 채택하지 않는다. 다만 진단 변수와 설명 변수 후보로는 유지한다.

## 상세산업 proxy 적용

`scripts/allocate_detailed_industry.py`도 수정했다. 기존에는 가장 가까운 proxy 연도를 선택했기 때문에 미래 proxy가 섞일 수 있었다. 이제는 목표연도 1월 1일 기준으로 공개된 최신 proxy 연도만 사용한다.

현재 연간 구조 proxy의 공표 지연은 보수적으로 12개월로 둔다. 따라서 2024년 예측의 경우 2024년 또는 2023년 proxy가 아니라 2022년 이하의 공개된 proxy만 사용할 수 있다.

예시는 다음과 같다.

| 목표연도 | 예측 기준일 | annual proxy lag | 사용 가능한 최신 연도 |
|---:|---|---:|---:|
| 2022 | 2022-01-01 | 12개월 | 2020 |
| 2023 | 2023-01-01 | 12개월 | 2021 |
| 2024 | 2024-01-01 | 12개월 | 2022 |

또한 ECOS 산업연관 prior를 상세산업 배분식에 결합했다.

```text
adjusted_proxy = local_proxy_value * ECOS_IO_self_value_added_inducement
allocation_share = adjusted_proxy / sum(adjusted_proxy within sigungu × detail_level)
quarterly_detail_gva = parent_sigungu_manufacturing_gva * allocation_share
```

이 방식은 ECOS 산업연관표를 actual로 쓰는 것이 아니라, 전국 산업구조 prior로 쓰는 것이다. 지역별 총량 제약은 계속 시군구 제조업 GVA에 맞춘다.

검증 결과:

- 상세산업 분기 추정 행: 21,960
- 상세산업 연간 추정 행: 5,490
- 제약 진단 행: 424
- 최대 총량 제약 오차: 약 `0.00000006`

## 운영상 해석

1. `actual`: 정부/지자체가 직접 공표한 값
2. `benchmark`: Denton 또는 배분 제약으로 쓰는 상위 공식 통계
3. `prior`: ECOS 산업연관표처럼 구조를 보정하는 정보
4. `exogenous`: 가격, 환율, 원자재처럼 예측 설명력을 검정하는 외생변수

대시보드와 보고서에서는 이 네 범주를 섞어 쓰지 않아야 한다. 특히 `prior`와 `exogenous`는 실제 GVA가 아니므로 actual로 표시하면 안 된다.

## 다음 적용 대상

- 대시보드 메타데이터 패널에 `actual/benchmark/prior/exogenous` 구분 표시
- 월간 지표 예측을 만들 경우 `forecast_as_of`를 월별로 두고 동일한 공표 지연 필터 적용
- 읍면동 추정에서 경제총조사/사업체 자료의 공표 지연을 명시적으로 반영
