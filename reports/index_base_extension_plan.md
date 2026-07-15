# 산업생산지수 기준연도 연결 및 데이터 확장 계획

## 현재 확인 결과

현재 로컬 KOSIS 장기 입력 파일은 산업생산지수와 서비스업생산지수를 `2020=100` 기준으로 보유하고 있으며, 주요 분기 지표가 2015년까지 소급되어 있다.

| 파일 | 성격 |
|---|---|
| `rolling_mining_manufacturing_production_index.csv` | 광공업/제조업 생산지수, 2020=100 |
| `rolling_mining_production_index.csv` | 광업 생산지수, 2020=100 |
| `rolling_electricity_gas_production_index.csv` | 전기·가스 생산지수, 2020=100 |
| `rolling_service_production_index.csv` | 시도별 서비스업생산지수, 2020=100 |
| `expanded_national_service_ksic_production_index.csv` | 전국 서비스업 세부 생산지수, 2020=100 |

따라서 현재 기본 모델에서는 2015년까지의 기간을 구 기준지수로 별도 추정하지 않아도 된다. KOSIS가 같은 표 안에서 2020 기준 소급계열을 제공하기 때문이다.

## 2015 기준 자료를 추가로 사용할 때의 방식

구 기준연도 자료가 별도 파일로 확보되면 다음 방식으로 2020 기준 계열에 연결한다.

```text
bridge_factor = mean(I_2020base[t] / I_2015base[t]) over overlap periods
I_2020base_estimated[t] = I_2015base[t] * bridge_factor
```

이 방식은 지수의 수준만 2020 기준으로 맞추고, 구 기준계열의 증감률 패턴은 유지한다. Denton 추정에서 중요한 것은 분기별 상대 움직임이므로, 공통기간 bridge가 안정적이면 과거 구간 확장에 사용할 수 있다.

## 추가한 스크립트

`scripts/build_index_base_bridge.py`를 추가했다.

산출물:

| 산출물 | 설명 |
|---|---|
| `index_base_bridge_source_summary.csv` | 현재 2020 기준 소급자료의 기간·단위 요약 |
| `index_base_bridge_factors.csv` | 구 2015 기준 파일이 있을 때 계산되는 series별 bridge factor |
| `index_base_bridge_converted_2020_base.csv` | 2015 기준 값을 2020 기준으로 환산한 결과 |

현재 로컬에는 별도 2015 기준 구 계열 파일이 없으므로 계산된 bridge factor는 생성되지 않는다. `index_base_bridge_factors.csv`에는 실제 factor가 아니라 `no_legacy_2015_base_files` 상태 안내 행이 남는다. 대신 source summary를 통해 현재 2020 기준 계열이 어느 기간까지 있는지 점검한다.

현재 확인된 기간:

| 계열 | 현재 기간 |
|---|---|
| 광공업/제조업 생산지수 | 2015Q1-2025Q4 |
| 광업 생산지수 | 2015Q1-2025Q4 |
| 전기·가스 생산지수 | 2015Q1-2025Q4 |
| 시도별 서비스업생산지수 | 2015Q1-2025Q4 |
| 전국 서비스업 세부 생산지수 | 2019Q1-2024Q4 |

## 세부산업 예측 확장과의 관계

이번 작업에서 `forecast_sigungu.py`는 2023년 고정 비중 대신 지역·산업·분기별 최신 가용 비중을 사용하도록 바뀌었다. 또한 `allocate_detailed_industry.py`는 `sigungu_quarterly_gva_forecasts.csv`까지 부모 데이터로 사용한다.

그 결과 강원특별자치도 `가구 제조업(C32)`은 기존 `2022년`만 존재하던 상태에서 `2022, 2024, 2025년`까지 확장된다.

## 다음 확장 방향

1. KOSIS에서 별도 2015 기준 구 계열 표가 확인되면 `data/processed/legacy_2015_base_production_index.csv` 또는 `legacy_2015_base_service_index.csv`로 저장한다.
2. `scripts/build_index_base_bridge.py`를 실행해 2020 기준 환산 계열을 만든다.
3. 환산 계열을 기존 2020 기준 소급계열과 중복 점검한 뒤, 현재 2015년보다 더 이른 기간의 indicator로 편입한다.
4. GRDP/GVA도 기준년이 다른 실질계열을 섞을 경우 같은 방식이 아니라 체인연쇄가격의 기준년·표체계 차이를 별도 검산해야 한다. 이 경우 단순 지수 bridge보다 공식 동일 기준 소급계열을 우선한다.
