# Phase256 광업·제조업 tail 자료준비도 감사

생성시각: 2026-07-29T18:52:09+09:00

## 1. 목적

Phase255에서 `광업, 제조업`은 시군구×업종 공개 actual 구간의 절대오차 1위로 확인됐다. 이번 감사는 새 route를 채택하는 실험이 아니라, 이미 로컬에 있는 제조업 생산지수·전력·공장등록 자료가 이 tail을 설명할 준비가 되어 있는지 점검한다.

## 2. 자료별 역할 판정

| 자료 | 로컬 coverage | 역할 | 운영 채택 여부 |
| --- | --- | --- | --- |
| 시도별 월간 제조업 생산지수 | 2015-01~2025-05, 2020=100 | 제조업 C00 월별 시간경로 | 시간경로 후보로 사용 가능 |
| 전국 세부 제조업 생산지수 | 2020-01~2025-05, 일부 항목 | 중분류 시간경로 후보 | 지역 차원이 없어 시군구 공간배분 단독 근거 금지 |
| 시군구 전력사용량 historical feature | 2021~2023 주요 검증 구간 | 지역 규모·전력집약도 보조 | 전력 단독 route 미채택, 구조자료와 결합 후보 |
| 공장등록 snapshot | 현재 스냅샷, 일반구는 시 단위 roll-up | 시군구 제조업 규모·업종구성 보조 | 등록일/vintage 불완전, 단독 route 미채택 |

## 3. 세부 제조업 생산지수 coverage

| c1_nm | months | min_period | max_period |
| --- | --- | --- | --- |
| 광업 및 제조업 | 65 | 202001 | 202505 |
| 반도체 및 부품 | 65 | 202001 | 202505 |
| 사무회계·통신기기·반도체 | 65 | 202001 | 202505 |
| 영상음향 | 65 | 202001 | 202505 |
| 제조업 | 65 | 202001 | 202505 |
| 총지수 | 65 | 202001 | 202505 |

## 4. 자료준비도별 tail 규모

| source_readiness | city_activity_groups | city_count | actual_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | over20_cells | large_actual_over10_cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| candidate_bundle_ready_for_holdout_design | 228 | 228 | 15,403,163.08 | 879,375.61 | 5.71 | 172 | 45 | 122 |
| insufficient_local_sources | 1 | 1 | 98,102.21 | 3,104.21 | 3.16 | 0 | 0 | 0 |

## 5. 광업·제조업 시군구 tail 상위와 자료 연결 상태

| province_full | city | actual_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | large_actual_over10_cells | mfg_index_months | electricity_months | industrial_share_mean | factory_rows | factory_employee_sum | factory_mfg_area_sum | source_readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 경기도 | 화성시 | 1,973,674.25 | 84,953.70 | 4.30 | 0 | 0 | 125 | 36 | 0.77 | 10,741 | 199,544 | 12,221,871.61 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 이천시 | 465,104.47 | 46,866.85 | 10.08 | 2 | 2 | 125 | 36 | 0.78 | 1,101 | 43,622 | 2,062,203.10 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 평택시 | 614,451.07 | 46,302.50 | 7.54 | 1 | 1 | 125 | 36 | 0.81 | 2,097 | 89,241 | 5,596,484.61 | candidate_bundle_ready_for_holdout_design |
| 충청북도 | 청주시 | 566,331.52 | 28,675.65 | 5.06 | 0 | 0 | 125 | 36 | 0.71 | 3,274 | 81,722 | 6,558,215.37 | candidate_bundle_ready_for_holdout_design |
| 충청남도 | 서산시 | 188,449.08 | 27,529.03 | 14.61 | 2 | 2 | 125 | 36 | 0.89 | 446 | 17,045 | 2,040,104.29 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 용인시 | 303,075.33 | 23,766.23 | 7.84 | 1 | 1 | 125 | 36 | 0.52 | 2,213 | 58,752 | 2,179,009.65 | candidate_bundle_ready_for_holdout_design |
| 경상북도 | 구미시 | 648,600.50 | 23,153.00 | 3.57 | 0 | 0 | 125 | 36 | 0.83 | 2,639 | 88,842 | 7,076,343.06 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 파주시 | 376,096.14 | 20,697.76 | 5.50 | 0 | 0 | 125 | 36 | 0.74 | 4,499 | 78,873 | 4,759,327.37 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 안산시 | 413,863.83 | 18,991.84 | 4.59 | 0 | 0 | 125 | 36 | 0.70 | 6,606 | 121,559 | 7,482,434.02 | candidate_bundle_ready_for_holdout_design |
| 경상북도 | 포항시 | 178,499.33 | 17,787.43 | 9.96 | 2 | 2 | 125 | 36 | 0.77 | 1,167 | 27,114 | 4,052,496.71 | candidate_bundle_ready_for_holdout_design |
| 울산광역시 | 울주군 | 203,962.97 | 16,170.80 | 7.93 | 0 | 0 | 125 | 36 | 0.91 | 1,568 | 46,782 | 5,291,146.00 | candidate_bundle_ready_for_holdout_design |
| 울산광역시 | 남구 | 239,160.18 | 16,122.90 | 6.74 | 0 | 0 | 125 | 36 | 0.92 | 536 | 30,838 | 3,746,913.61 | candidate_bundle_ready_for_holdout_design |
| 전라남도 | 여수시 | 370,519.27 | 14,592.60 | 3.94 | 0 | 0 | 125 | 36 | 0.91 | 608 | 23,805 | 2,826,397.71 | candidate_bundle_ready_for_holdout_design |
| 인천광역시 | 연수구 | 138,580.53 | 13,810.39 | 9.97 | 1 | 1 | 125 | 36 | 0.42 | 268 | 12,728 | 658,219.74 | candidate_bundle_ready_for_holdout_design |
| 경상남도 | 창원시 | 328,550.06 | 13,709.08 | 4.17 | 0 | 0 | 125 | 36 | 0.60 | 4,748 | 119,604 | 10,175,505.65 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 시흥시 | 243,585.11 | 13,071.45 | 5.37 | 1 | 1 | 125 | 36 | 0.59 | 6,158 | 69,865 | 4,809,544.66 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 안양시 | 146,950.68 | 12,621.88 | 8.59 | 1 | 1 | 125 | 36 | 0.16 | 1,932 | 33,550 | 825,874.23 | candidate_bundle_ready_for_holdout_design |
| 충청남도 | 당진시 | 107,697.97 | 11,922.94 | 11.07 | 1 | 1 | 125 | 36 | 0.85 | 894 | 26,726 | 5,431,184.12 | candidate_bundle_ready_for_holdout_design |
| 서울특별시 | 강남구 | 92,812.95 | 11,224.11 | 12.09 | 3 | 3 | 125 | 36 | 0.06 | 228 | 3,196 | 20,517.42 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 성남시 | 209,411.07 | 11,095.22 | 5.30 | 1 | 1 | 125 | 36 | 0.16 | 3,343 | 41,523 | 927,114.96 | candidate_bundle_ready_for_holdout_design |
| 대구광역시 | 달성군 | 94,158.01 | 10,368.82 | 11.01 | 1 | 1 | 125 | 36 | 0.75 | 1,906 | 41,441 | 4,060,099.40 | candidate_bundle_ready_for_holdout_design |
| 울산광역시 | 북구 | 232,301.03 | 9,902.60 | 4.26 | 0 | 0 | 125 | 36 | 0.70 | 688 | 44,736 | 3,064,728.38 | candidate_bundle_ready_for_holdout_design |
| 인천광역시 | 남동구 | 173,567.63 | 9,630.45 | 5.55 | 0 | 0 | 125 | 36 | 0.53 | 4,890 | 76,801 | 4,206,359.88 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 수원시 | 246,972.23 | 9,426.81 | 3.82 | 0 | 0 | 125 | 36 | 0.11 | 1,226 | 59,607 | 1,127,432.45 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 김포시 | 188,560.72 | 9,413.69 | 4.99 | 0 | 0 | 125 | 36 | 0.50 | 6,661 | 71,503 | 6,437,509.98 | candidate_bundle_ready_for_holdout_design |
| 충청북도 | 충주시 | 99,140.06 | 9,260.94 | 9.34 | 2 | 2 | 125 | 36 | 0.56 | 797 | 20,044 | 1,889,501.93 | candidate_bundle_ready_for_holdout_design |
| 대구광역시 | 북구 | 38,098.78 | 9,175.46 | 24.08 | 1 | 1 | 125 | 36 | 0.30 | 2,018 | 17,891 | 1,018,581.08 | candidate_bundle_ready_for_holdout_design |
| 광주광역시 | 서구 | 94,180.80 | 8,701.42 | 9.24 | 1 | 1 | 125 | 36 | 0.19 | 393 | 9,199 | 524,701.85 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 안성시 | 156,268.05 | 8,585.65 | 5.49 | 0 | 0 | 125 | 36 | 0.58 | 2,098 | 43,394 | 3,424,487.21 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 광명시 | 89,971.74 | 8,145.52 | 9.05 | 1 | 1 | 125 | 36 | 0.22 | 616 | 11,390 | 328,417.25 | candidate_bundle_ready_for_holdout_design |

## 6. 대형 actual·10% 초과 제조업 셀

| province_full | city | year | actual_eok | predicted_eok | abs_error_eok | ape_pct | electricity_months | industrial_share_mean | factory_rows | factory_employee_sum | source_readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 경기도 | 이천시 | 2023 | 139,041.33 | 165,927.80 | 26,886.47 | 19.34 | 36 | 0.78 | 1,101 | 43,622 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 평택시 | 2023 | 230,963.27 | 206,515.84 | 24,447.43 | 10.58 | 36 | 0.81 | 2,097 | 89,241 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 이천시 | 2021 | 162,539.62 | 145,510.85 | 17,028.77 | 10.48 | 36 | 0.78 | 1,101 | 43,622 | candidate_bundle_ready_for_holdout_design |
| 충청남도 | 서산시 | 2021 | 86,764.88 | 72,054.37 | 14,710.51 | 16.95 | 36 | 0.89 | 446 | 17,045 | candidate_bundle_ready_for_holdout_design |
| 충청남도 | 서산시 | 2022 | 101,684.20 | 88,865.69 | 12,818.51 | 12.61 | 36 | 0.89 | 446 | 17,045 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 용인시 | 2022 | 100,129.21 | 111,123.14 | 10,993.93 | 10.98 | 36 | 0.52 | 2,213 | 58,752 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 성남시 | 2023 | 78,012.61 | 67,478.88 | 10,533.73 | 13.50 | 36 | 0.16 | 3,343 | 41,523 | candidate_bundle_ready_for_holdout_design |
| 인천광역시 | 연수구 | 2022 | 48,501.41 | 38,377.38 | 10,124.03 | 20.87 | 36 | 0.42 | 268 | 12,728 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 안양시 | 2023 | 56,823.56 | 47,181.42 | 9,642.14 | 16.97 | 36 | 0.16 | 1,932 | 33,550 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 시흥시 | 2022 | 78,848.71 | 88,331.82 | 9,483.11 | 12.03 | 36 | 0.59 | 6,158 | 69,865 | candidate_bundle_ready_for_holdout_design |
| 경상북도 | 포항시 | 2022 | 55,966.35 | 64,582.91 | 8,616.56 | 15.40 | 36 | 0.77 | 1,167 | 27,114 | candidate_bundle_ready_for_holdout_design |
| 대구광역시 | 달성군 | 2021 | 45,417.84 | 37,271.67 | 8,146.17 | 17.94 | 36 | 0.75 | 1,906 | 41,441 | candidate_bundle_ready_for_holdout_design |
| 대구광역시 | 북구 | 2021 | 19,680.89 | 27,116.82 | 7,435.93 | 37.78 | 36 | 0.30 | 2,018 | 17,891 | candidate_bundle_ready_for_holdout_design |
| 경기도 | 광명시 | 2021 | 29,661.18 | 22,379.94 | 7,281.24 | 24.55 | 36 | 0.22 | 616 | 11,390 | candidate_bundle_ready_for_holdout_design |
| 충청남도 | 당진시 | 2021 | 55,604.43 | 62,670.14 | 7,065.71 | 12.71 | 36 | 0.85 | 894 | 26,726 | candidate_bundle_ready_for_holdout_design |
| 경상북도 | 포항시 | 2021 | 63,056.15 | 69,539.42 | 6,483.27 | 10.28 | 36 | 0.77 | 1,167 | 27,114 | candidate_bundle_ready_for_holdout_design |
| 광주광역시 | 서구 | 2023 | 36,536.58 | 30,618.41 | 5,918.17 | 16.20 | 36 | 0.19 | 393 | 9,199 | candidate_bundle_ready_for_holdout_design |
| 전라남도 | 영암군 | 2023 | 20,039.48 | 14,964.74 | 5,074.74 | 25.32 | 36 | 0.63 | 522 | 17,208 | candidate_bundle_ready_for_holdout_design |
| 충청북도 | 충주시 | 2022 | 34,990.80 | 30,391.12 | 4,599.68 | 13.15 | 36 | 0.56 | 797 | 20,044 | candidate_bundle_ready_for_holdout_design |
| 전라남도 | 광양시 | 2022 | 39,395.98 | 43,858.57 | 4,462.59 | 11.33 | 36 | 0.86 | 561 | 19,288 | candidate_bundle_ready_for_holdout_design |

## 7. 판정

1. 시도별 월간 제조업 생산지수는 제조업 GVA의 월별 시간경로에는 필수지만, 시군구 내부 구조를 바꾸는 자료가 아니다.
2. 전국 세부 제조업 생산지수는 일부 항목만 있고 지역 차원이 없으므로 중분류 시간경로 후보일 뿐, 대형 제조업 도시의 공간배분 단독 근거가 아니다.
3. 시군구 전력과 공장등록은 광업·제조업 tail 대부분에 연결된다. 단, 공장등록은 일반구를 시 단위로 합친 현재 snapshot이므로 과거연도 속보자료로 직접 쓰면 안 되고, 기존 전력 단독·공장 단독 실험도 운영 gate를 통과하지 못했다.
4. 따라서 현 단계의 제조업 tail 대부분은 `candidate_bundle_ready_for_holdout_design`이며, 이는 route 채택 상태가 아니라 holdout 검증 설계를 시작할 수 있다는 뜻이다.
5. 다음 실험은 top-error 셀에서 바로 성능을 주장하지 말고, 제조업 대형 도시를 discovery/holdout으로 분리한 뒤 `월간 생산지수 × 전력집약도 × 공장규모` 묶음의 out-of-year 또는 holdout-city 검증으로 진행해야 한다.

## 8. 금지 해석

- 월간 제조업 생산지수 반영을 중분류·시군구 구조 개선으로 표현하지 않는다.
- 현재 공장등록 snapshot을 2021~2023 당시의 정확한 공장 stock으로 표현하지 않는다.
- 전력 단독 feature를 운영 route로 채택했다고 표현하지 않는다.
- Phase255의 top-error 도시를 보고 만든 가중치를 같은 도시·같은 연도에서 성과로 보고하지 않는다.

## 9. 다음 수집·검증 우선순위

1. 공장등록의 등록일·폐업/휴업·변경이력 또는 연도별 snapshot 확보.
2. 제조업 중분류별 출하액·부가가치·종사자·급여액의 시군구 또는 산업단지 단위 자료 확보.
3. 대형 제조업 도시(화성·이천·평택·구미·서산 등)는 공장규모와 전력집약도 interaction 후보를 사전 고정한 뒤 holdout 검증.
4. 포항·울산·인천 등 항만/중화학 비중이 큰 도시는 항만 품목 물동량·대형사업장 자료를 별도 후보로 유지.

## 10. 산출물

- `nationwide/outputs/phase256_manufacturing_tail_source_readiness_by_city.csv`
- `nationwide/outputs/phase256_manufacturing_tail_source_readiness_summary.csv`
- `nationwide/outputs/phase256_manufacturing_tail_source_readiness_cells.csv`
- `nationwide/outputs/phase256_manufacturing_detail_index_coverage.csv`
