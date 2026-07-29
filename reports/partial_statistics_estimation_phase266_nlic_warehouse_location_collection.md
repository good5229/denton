# Phase266 국가물류통합정보센터 물류창고업 등록현황 수집

생성시각: 2026-07-29T21:50:41+09:00

## 결론

2015~2025년 국가물류통합정보센터 `지역별 물류창고업 등록현황` XLS 11개를 수집·파싱했다. 이 자료는 `운수 및 창고업` 중 창고업 관련 시도 단위 보조 신호로는 유용하지만, GVA actual이나 시군구 공간배분 자료는 아니다.

## 1. Coverage

| year | province_count | source_row_province_count | source_row_missing_province_count | category_count | total_registered_count |
| --- | --- | --- | --- | --- | --- |
| 2015 | 17 | 17 | 0 | 8 | 147 |
| 2016 | 17 | 15 | 2 | 8 | 141 |
| 2017 | 17 | 15 | 2 | 8 | 229 |
| 2018 | 17 | 16 | 1 | 8 | 208 |
| 2019 | 17 | 16 | 1 | 8 | 252 |
| 2020 | 17 | 16 | 1 | 8 | 339 |
| 2021 | 17 | 17 | 0 | 8 | 319 |
| 2022 | 17 | 16 | 1 | 8 | 367 |
| 2023 | 17 | 16 | 1 | 8 | 512 |
| 2024 | 17 | 16 | 1 | 8 | 583 |
| 2025 | 17 | 16 | 1 | 8 | 658 |

## 2. 2015~2025 변화 상위

| province_full | count_2015 | count_2020 | count_2025 | change_2015_2025_count | change_2015_2025_pct |
| --- | --- | --- | --- | --- | --- |
| 경기도 | 43 | 157 | 285 | 242 | 562.79 |
| 경상남도 | 21 | 29 | 72 | 51 | 242.86 |
| 인천광역시 | 16 | 18 | 58 | 42 | 262.50 |
| 전라남도 | 6 | 20 | 37 | 31 | 516.67 |
| 경상북도 | 8 | 21 | 33 | 25 | 312.50 |
| 부산광역시 | 9 | 8 | 34 | 25 | 277.78 |
| 울산광역시 | 2 | 7 | 23 | 21 | 1,050.00 |
| 전북특별자치도 | 4 | 12 | 22 | 18 | 450.00 |
| 충청남도 | 5 | 14 | 20 | 15 | 300.00 |
| 충청북도 | 6 | 24 | 17 | 11 | 183.33 |
| 서울특별시 | 4 | 5 | 14 | 10 | 250.00 |
| 제주특별자치도 | 2 | 3 | 11 | 9 | 450.00 |

## 3. 산출물

| 산출물 | 역할 | git 처리 |
| --- | --- | --- |
| `data/raw/phase266_nlic_warehouse_location/nlic_warehouse_location_YYYY.xls` | 연도별 원본 XLS | `data/` ignore |
| `data/processed/phase266_nlic_warehouse_location/nlic_warehouse_location_2015_2025_long.csv` | province×year×법령×창고구분 long table | `data/`·`*.csv` ignore |
| `data/processed/phase266_nlic_warehouse_location/nlic_warehouse_location_2015_2025_province_wide.csv` | 시도×연도 wide table | `data/`·`*.csv` ignore |
| `nationwide/outputs/phase266_nlic_warehouse_location_coverage.csv` | coverage 감사 | `nationwide/outputs/*.csv` ignore |
| `nationwide/outputs/phase266_nlic_warehouse_location_top_change.csv` | 변화 상위 감사 | `nationwide/outputs/*.csv` ignore |
| `nationwide/nlic_warehouse_location_source_metadata.md` | 출처·공표주기·금지해석 | tracked |

## 4. 적용 판정

| 항목 | 판정 |
| --- | --- |
| H52 창고업 시도 단위 보조 신호 | 후보 |
| 운수 및 창고업 전체 GVA actual | 아님 |
| 시군구 공간배분 근거 | 아님 |
| 월별·분기별 속보 지표 | 아님 |
| 운영 route 채택 | 미채택 |

다음 실험에서 쓰려면 `항만 물동량`, `전력`, `사업체`, `상위 시도 운수·창고업 actual`과 함께 rolling out-of-year gate를 통과해야 한다.
