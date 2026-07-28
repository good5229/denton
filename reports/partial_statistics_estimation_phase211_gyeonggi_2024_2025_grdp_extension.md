# Phase 211: 2024·2025 경기도 GRDP 확장 검증

## 목적

포스터에는 아직 반영하지 않고, 평가시점이 2026년이라는 점을 고려해 2024년과 2025년까지 추정값-공식값 비교가 가능한지 내부 검증했다.

## 실제값 확보 여부

- 통계청 실험적 통계 XLSX `실질금액` 시트에는 경기도 `지역내총생산(시장가격)` 분기 수준값이 **2015Q1~2026Q1**까지 존재한다.
- 이번 검증은 완결 연도인 **2024Q1~2025Q4**를 사용했다.
- 2026Q1도 존재하지만 1개 분기만 있으므로 이번 연간 비교에서는 제외했다.

## 추정 방식

| 구분 | 사용 정보 | 경기도 2024·2025 공식값 사용 여부 |
| --- | --- | --- |
| 광업·제조업 | 2023 경기도 프로젝트 GVA × 전국 동업종 분기 전년동기 성장률 | 미사용 |
| 건설업 | 2023 경기도 프로젝트 GVA × 전국 건설업 분기 전년동기 성장률 | 미사용 |
| 서비스업 | 2023 경기도 프로젝트 GVA × 전국 서비스업 분기 전년동기 성장률 | 미사용 |
| 기타산업·순생산물세 | 전년도 경기도 회계비율 × 전국 분기 배분비중 | 같은 해 공식값 미사용 |
| 검증값 | 통계청 XLSX 경기도 GRDP 시장가격 | 사후 대조에만 사용 |

## 트랙 구분

| 트랙 | 의미 |
| --- | --- |
| `recursive_no_target_actual` | 2025년에도 2024년 경기도 공식 회계비율을 쓰지 않고, 2024년 예측 비율을 이어 붙인 순수 외삽형 |
| `prior_year_official_ratio` | 2025년 예측 때 이미 공표된 전년도(2024년) 공식 회계비율은 사용할 수 있다고 보는 정밀화형 |

## 2024·2025 주 산업블록 추정 규모

| year | block_label | predicted_main_block_gva_eok |
| --- | --- | --- |
| 2024 | 건설업 | 311844.0 |
| 2024 | 광업·제조업 | 2215874.0 |
| 2024 | 서비스업 | 2939107.0 |
| 2025 | 건설업 | 283064.0 |
| 2025 | 광업·제조업 | 2265697.0 |
| 2025 | 서비스업 | 2988446.0 |

## 분기별 GRDP 시장가격 검증

| ratio_track | period | predicted_main_blocks_eok | predicted_other_npt_eok | predicted_grdp_market_price_eok | official_grdp_market_price_eok | error_eok | ape_pct | ratio_source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| recursive_no_target_actual | 2024Q1 | 1260869.0 | 103101.0 | 1363971.0 | 1439702.0 | -75732.0 | 5.26 | prior_year_official_ratio_2023 |
| recursive_no_target_actual | 2024Q2 | 1347568.0 | 107615.0 | 1455183.0 | 1489713.0 | -34530.0 | 2.318 | prior_year_official_ratio_2023 |
| recursive_no_target_actual | 2024Q3 | 1392790.0 | 114423.0 | 1507212.0 | 1489794.0 | 17418.0 | 1.169 | prior_year_official_ratio_2023 |
| recursive_no_target_actual | 2024Q4 | 1465599.0 | 116341.0 | 1581940.0 | 1559051.0 | 22889.0 | 1.468 | prior_year_official_ratio_2023 |
| recursive_no_target_actual | 2025Q1 | 1260935.0 | 105376.0 | 1366311.0 | 1444256.0 | -77945.0 | 5.397 | prior_year_predicted_ratio_2024 |
| recursive_no_target_actual | 2025Q2 | 1359725.0 | 107311.0 | 1467036.0 | 1528942.0 | -61907.0 | 4.049 | prior_year_predicted_ratio_2024 |
| recursive_no_target_actual | 2025Q3 | 1425606.0 | 117427.0 | 1543034.0 | 1555740.0 | -12707.0 | 0.817 | prior_year_predicted_ratio_2024 |
| recursive_no_target_actual | 2025Q4 | 1490940.0 | 117050.0 | 1607990.0 | 1593965.0 | 14025.0 | 0.88 | prior_year_predicted_ratio_2024 |
| prior_year_official_ratio | 2024Q1 | 1260869.0 | 103101.0 | 1363971.0 | 1439702.0 | -75732.0 | 5.26 | prior_year_official_ratio_2023 |
| prior_year_official_ratio | 2024Q2 | 1347568.0 | 107615.0 | 1455183.0 | 1489713.0 | -34530.0 | 2.318 | prior_year_official_ratio_2023 |
| prior_year_official_ratio | 2024Q3 | 1392790.0 | 114423.0 | 1507212.0 | 1489794.0 | 17418.0 | 1.169 | prior_year_official_ratio_2023 |
| prior_year_official_ratio | 2024Q4 | 1465599.0 | 116341.0 | 1581940.0 | 1559051.0 | 22889.0 | 1.468 | prior_year_official_ratio_2023 |
| prior_year_official_ratio | 2025Q1 | 1260935.0 | 101586.0 | 1362521.0 | 1444256.0 | -81735.0 | 5.659 | prior_year_official_ratio_2024 |
| prior_year_official_ratio | 2025Q2 | 1359725.0 | 103452.0 | 1463177.0 | 1528942.0 | -65766.0 | 4.301 | prior_year_official_ratio_2024 |
| prior_year_official_ratio | 2025Q3 | 1425606.0 | 113204.0 | 1538810.0 | 1555740.0 | -16930.0 | 1.088 | prior_year_official_ratio_2024 |
| prior_year_official_ratio | 2025Q4 | 1490940.0 | 112840.0 | 1603780.0 | 1593965.0 | 9815.0 | 0.616 | prior_year_official_ratio_2024 |

## 연도별 요약

| ratio_track | year | quarters | official_grdp_sum_eok | predicted_grdp_sum_eok | abs_error_sum_eok | wape_pct | max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| prior_year_official_ratio | 2024 | 4 | 5978260.0 | 5908306.0 | 150568.0 | 2.519 | 5.26 |
| prior_year_official_ratio | 2025 | 4 | 6122903.0 | 5968289.0 | 174245.0 | 2.846 | 5.659 |
| recursive_no_target_actual | 2024 | 4 | 5978260.0 | 5908306.0 | 150568.0 | 2.519 | 5.26 |
| recursive_no_target_actual | 2025 | 4 | 6122903.0 | 5984370.0 | 166583.0 | 2.721 | 5.397 |

## 판정

- 2024년과 2025년 모두 공식 actual이 존재하므로, 포스터 밖 내부 검증으로는 비교 가능하다.
- 단, 현재 고양시·포항시 동·업종 GVA 파이프라인은 2023년 공식 시군구·산업 기준에서 출발하므로, 2024·2025는 **경기도 상위 GRDP 경계의 외삽 검증**으로 해석해야 한다.
- `recursive_no_target_actual`은 완전 외삽에 가깝고, `prior_year_official_ratio`는 전년도 공식값 공표 후 정밀화에 가깝다.
- 포스터에 반영하려면 `2024·2025p 경기도 상위 GRDP 외부검증`이라고 좁게 표기해야 하며, 고양시 행정동 GVA의 2024·2025 공식 검증처럼 쓰면 안 된다.

## 산출물

- `data/processed/phase211_gyeonggi_2024_2025_grdp_extension/phase211_sido_quarterly_xlsx_long.csv`
- `data/processed/phase211_gyeonggi_2024_2025_grdp_extension/phase211_gyeonggi_main_block_extrapolation_2024_2025.csv`
- `data/processed/phase211_gyeonggi_2024_2025_grdp_extension/phase211_gyeonggi_grdp_extension_validation_2024_2025.csv`
- `data/processed/phase211_gyeonggi_2024_2025_grdp_extension/phase211_gyeonggi_grdp_extension_summary_2024_2025.csv`
