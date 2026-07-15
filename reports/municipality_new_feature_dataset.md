# 시군구 ML 재개용 신규 Feature 데이터셋 확보

## 목적

시군구 ML 보정은 기존 feature만으로 oracle 상한이 낮았으므로, 모델 변경 전에 시군구×산업 생산활동을 더 직접적으로 설명하는 변수를 확보했다.

## 산출물

| 파일 | 내용 |
| --- | --- |
| `data/processed/business_sido_industry_all.csv` | 시도×산업 사업체수·종사자수·매출액 전체 산업 확장 |
| `data/processed/business_size_sido_industry.csv` | 시도×산업×종사자규모 사업체수·종사자수 |
| `data/processed/municipality_feature_mart_long.csv` | source/지역/산업/연도/지표 단위 long feature mart |
| `data/processed/municipality_feature_mart_wide.csv` | 모델링 결합용 wide feature mart |
| `data/processed/municipality_direct_feature_inventory.csv` | source별 coverage와 공표지연 정책 요약 |

- long mart rows: 271,223
- wide mart rows: 95,156

## 확보 Source 요약

| Source | 행 수 | 기간 | 지역 레벨 | 산업 레벨 | 지표 |
| --- | ---: | --- | --- | --- | --- |
| emd_economic_census_2015 | 162024 | 2015 | eupmyeondong,national,sido,sigungu | section | employees,establishments,sales |
| manufacturing_mining_sigungu_ksic | 74468 | 2020,2021,2022,2023,2024 | national,sido,sigungu | class,middle,small | employees,establishments,value_added |
| sido_industry_business | 5400 | 2020,2021,2022,2023,2024 | national,sido | all,section | employees,establishments,sales |
| sido_industry_employee_size | 29331 | 2020,2021,2022,2023,2024 | national,sido | all,section | employees_size_0,employees_size_1,employees_size_2,employees_size_3,employees_size_4,employees_size_5,employees_size_6,employees_size_7,employees_size_8,employees_size_9,establishments_size_0,establishments_size_1,establishments_size_2,establishments_size_3,establishments_size_4,establishments_size_5,establishments_size_6,establishments_size_7,establishments_size_8,establishments_size_9 |

## 공표지연 및 데이터 유출 방지

연간 구조통계는 목표연도 초에 같은 해 값이 공개되어 있다고 볼 수 없다. 현재 mart에는 보수적으로 `first_eligible_target_year = source_year + 2`를 부여했다.

예를 들어 2024년을 2024년 1월 1일 기준으로 예측하는 backtest에서는 2022년 이하 구조변수만 사용할 수 있다.

## 해석

- 시군구에 직접 붙는 강한 신규 feature는 광업·제조업 주요지표와 2015년 경제총조사 읍면동 proxy다.
- 전국사업체조사 계열은 현재 시도 단위라 시군구 직접 signal은 아니지만, 부모 시도 산업구조와 규모별 분포를 설명하는 보조 feature로 사용할 수 있다.
- 서비스업·도소매·건설·전기가스의 시군구 직접 변수는 아직 제한적이므로, 다음 단계에서는 공장등록, 건축허가, 전력판매량, 산업단지 자료 같은 외부 행정자료 연결이 필요하다.

## 추가 탐색 후보

`municipality_feature_source_candidates.csv`에는 아직 확보하지 못했지만 ML 재개 조건을 만족시키기 위해 우선 탐색해야 할 후보를 정리했다.

| 우선순위 | 후보 | 대상 산업 | 희망 지역 레벨 | 이유 |
| ---: | --- | --- | --- | --- |
| 1 | factory_registration | B00,C00 | sigungu | 광업·제조업 시군구 share를 직접 설명할 수 있는 입지/설비 stock 변수 |
| 2 | industrial_complex_activity | C00 | sigungu | 제조업 생산·수출·고용 변동을 시군구별로 직접 반영 가능 |
| 3 | electricity_sales_by_use | C00,D00,E00,all | sigungu | 산업생산과 사업장 활동의 고빈도 proxy 후보 |
| 4 | building_permits_and_starts | F00,L00 | sigungu | 건설업·부동산업 지역 변동을 설명할 수 있는 직접 activity 변수 |
| 5 | agriculture_livestock_fishery | A00 | sigungu | 농림어업은 사업체수보다 생산량·면적·사육두수 신호가 직접적 |
| 6 | local_card_sales_and_foot_traffic | G00,I00,R00 | sigungu,eupmyeondong | 도소매·숙박음식·여가서비스의 하위지역 수요 proxy |
