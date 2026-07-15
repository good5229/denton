# ECOS 데이터 통합 결과

## 목적

`reports/ecos_data_feasibility.md`에서 제안한 ECOS 보강 작업을 실제 데이터 수집 단계로 진행했다. 목표는 ECOS 자료를 지역 actual로 오인하지 않으면서, 전국 계정 검산, 산업연관 기반 prior, 전기·가스 외생변수 보강에 사용할 수 있는 형태로 정리하는 것이다.

## 생성 산출물

| 파일 | 행 수 | 내용 |
|---|---:|---|
| `data/processed/ecos_national_accounts.csv` | 5,960 | ECOS GDP/GNI, GDP 디플레이터, 연간 명목 GVA |
| `data/processed/ecos_kosis_gdp_crosscheck.csv` | 3,156 | ECOS와 KOSIS GDP/디플레이터 검산 |
| `data/processed/ecos_io_middle_matrix.csv` | 14,281 | 2019년 중분류 투입산출 생산/부가가치유발 계수 행렬 |
| `data/processed/ecos_io_middle_industry_prior.csv` | 7,055 | 생산유발·부가가치유발 계수를 병합한 중분류 산업 prior |
| `data/processed/ecos_energy_price_fx_quarterly.csv` | 1,144 | 환율, 수입물가, 생산자물가 기반 전기·가스 보강 변수 |
| `data/processed/energy_exogenous_with_ecos_quarterly.csv` | 1,276 | 기존 FRED 외생변수와 ECOS 외생변수 병합본 |
| `data/processed/ecos_augmented_data_summary.csv` | 8 | 통합 결과 요약 |

모든 CSV는 CP949로 저장했다.

## 1. 전국 계정 검산

ECOS에서 다음 계열을 수집했다.

- `200Y103`: 경제활동별 GDP 및 GNI(계절조정, 명목, 분기)
- `200Y106`: 경제활동별 GDP 및 GNI(원계열, 실질, 분기 및 연간)
- `200Y111`: 경제활동별 국내총생산 디플레이터(분기 및 연간)
- `200Y114`: 경제활동별 국내총부가가치와 요소소득(명목, 연간)

검산 결과, ECOS `200Y106` 실질 GDP는 기존 KOSIS `rolling_national_quarterly_gdp_real.csv`와 2,508개 중복 관측치가 모두 일치했다. 즉 현재 프로젝트에서 쓰는 전국 실질 GDP 경로는 ECOS와 같은 값을 보고 있다.

디플레이터는 648개 중복 관측치가 원값 기준으로 일치하지 않았다. 다만 이는 값 오류라기보다 기준연도/표체계 차이다. 현재 로컬 KOSIS 파일은 `2015=100`, ECOS `200Y111`은 `2020=100`으로 들어오므로, 그대로 같은 수치를 기대하면 안 된다. 따라서 이후 디플레이터는 한 소스 안에서 기준연도를 통일해서 사용해야 한다. 새 작업에서는 ECOS `2020=100` 기준을 우선 소스로 두는 편이 낫다.

## 2. 산업연관 prior

ECOS `271Y070`, `271Y072`에서 2019년 중분류 기준 생산유발계수와 부가가치유발계수를 수집했다. 이는 지역 actual이 아니라 전국 산업 간 구조를 나타내는 prior다.

`ecos_io_middle_industry_prior.csv`는 다음 필드를 제공한다.

- `demand_code`, `demand_name`: 수요부문, 즉 배분 대상 산업
- `input_code`, `input_name`: 투입부문, 즉 연결되는 산업
- `production_inducement`: 생산유발계수
- `value_added_inducement`: 부가가치유발계수
- `production_share_within_demand`: 해당 수요부문 안에서 생산유발계수를 정규화한 비중
- `value_added_share_within_demand`: 해당 수요부문 안에서 부가가치유발계수를 정규화한 비중

전기·가스 관련 예시는 다음과 같다.

| 수요부문 | 주요 투입부문 | 생산유발계수 | 해석 |
|---|---|---:|---|
| 전력 및 신재생에너지 | 전력 및 신재생에너지 | 1.020116 | 자기 산업 영향이 가장 큼 |
| 전력 및 신재생에너지 | 가스, 증기 및 온수 | 0.184592 | 전력과 가스 공급의 연결성 |
| 전력 및 신재생에너지 | 석탄 및 석유제품 | 0.054860 | 연료 가격 변수 편입 근거 |
| 가스, 증기 및 온수 | 석탄, 원유 및 천연가스 | 0.014733 | 원유·천연가스 가격 변수 편입 근거 |

이 prior는 시군구/읍면동 세부산업 추정에서 단순 사업체·종사자 비중을 보정하는 데 사용할 수 있다. 예를 들어 제조업 소분류 배분 시 `지역 proxy 비중 × 산업연관 prior`를 결합하면, 단순 규모 배분보다 산업 구조를 반영한 배분이 가능하다.

## 3. 전기·가스 외생변수 보강

기존 `energy_exogenous_quarterly.csv`는 FRED 기반 WTI, USD/KRW, 석탄, 천연가스 계열을 갖고 있었다. 이번 작업으로 ECOS 기반 국내 물가/환율 계열을 추가했다.

추가한 주요 지표는 다음과 같다.

- `ecos_usd_krw_avg`: 원/미국달러 매매기준율 평균
- `ecos_import_price_bituminous_coal`: 수입물가지수 유연탄
- `ecos_import_price_crude_oil`: 수입물가지수 원유
- `ecos_import_price_lng`: 수입물가지수 천연가스(LNG)
- `ecos_import_price_lpg`: 수입물가지수 액화석유가스
- `ecos_ppi_power`: 생산자물가지수 전력
- `ecos_ppi_city_gas`: 생산자물가지수 도시가스
- `ecos_ppi_power_gas_steam`: 생산자물가지수 전력,가스및증기

이 계열은 전기·가스 산업 전용 보강 모델에서 후보 feature로 쓸 수 있다. 특히 수입물가지수는 국제 원자재 가격을 국내 가격 체계로 변환한 지표이므로, FRED 원자료보다 국내 GVA/생산지수와 직접 연결될 가능성이 있다.

## 대시보드/모델 적용 원칙

1. ECOS 전국 계정은 상위 검산 기준으로 사용한다.
2. ECOS 산업연관표는 산업구조 prior로만 사용하고, 지역 actual로 표시하지 않는다.
3. ECOS 가격·환율 계열은 전기·가스 및 일부 제조업의 외생변수 후보로 사용한다.
4. 디플레이터는 기준연도 차이를 반드시 메타데이터에 표시한다.

## 다음 구현 순서

1. 전기·가스 산업 예측 스크립트에 `energy_exogenous_with_ecos_quarterly.csv`를 연결해 기존 FRED-only feature와 성능을 비교한다.
2. 상세산업 배분 스크립트에 `ecos_io_middle_industry_prior.csv`를 선택적 가중치로 결합한다.
3. 대시보드의 데이터 설명 또는 메타데이터 패널에 `actual`, `benchmark`, `prior`, `exogenous`의 출처 구분을 표시한다.
