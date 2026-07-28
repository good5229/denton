# Phase 209: 경기도 31개 시군 확장 GVA 집계검증

## 목적

고양시 방식의 상위총량 배분·외삽 구조를 경기도 전체 시군구로 확장할 수 있는지 확인했다. 포스터에는 반영하지 않는 내부 검증용 산출물이다.

## 사용 자료

| 자료 | 범위 | 이번 단계 사용 |
| --- | --- | --- |
| 시군구 분기 GVA 배분 큐브 | 전국 시군구, 2020Q1~2023Q4 | 경기도 31개 시군 추출·집계 |
| 경기도 버스 승하차 월자료 | 경기도 전체 시군, 2020년 이후 | 보유 확인·후속 운수 개선 후보 |
| 시군구 전력 월자료 | 전국 시군구, 경기도 포함 | 보유 확인·후속 제조업 시간축 후보 |
| 공식 분기 GRDP PDF | 2025년 4/4분기 및 연간 실질 지역내총생산(잠정) 보도자료(실험적통계) | 경기도 GRDP 전년동기비 actual 추출 |

## 공식 actual 확보 범위

- 공식 MODS 보도자료 PDF에서는 경기도 분기별 **전년동기비 성장률**을 확인했다.
- 동일 PDF에서 `억원`, `수준`, `금액` 키워드 기반으로 수준액 표를 검색했지만, 경기도 분기별 **공식 수준값 actual 표는 확인하지 못했다**.
- KOSIS 공식 메타에서는 경기도 `경제활동별 지역내총부가가치 및 요소소득` actual이 확인되지만, 해당 표는 **연간(Y)** 자료다.
- 한국은행 KOSIS 국민계정 표에는 전국 분기 GDP/GVA 수준값이 있으나, **경기도 지역 차원은 없다**.
- 추가 확인한 통계청 실험적통계 XLSX 파일의 `실질금액` 시트에는 경기도 분기별 **지역내총생산(시장가격) 수준값**이 존재한다.
- 따라서 공식 수준값 actual 대조는 통계청 XLSX 기준으로 수행하되, 우리 산출물이 총부가가치(GVA) 합계라는 점 때문에 `시장가격 GRDP`와의 개념 차이를 별도 표시한다.
- 공식 actual과의 성장률 대조는 기존처럼 MODS 보도자료의 **경기도 GRDP 전년동기비 성장률** 기준으로 수행한다.

| source | table_name | region_scope | time_frequency | unit | actual_level_available | usable_for_phase209 | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| KOSIS 210/DT_GRDP008_2020 | 경기도 경제활동별 지역내총부가가치 및 요소소득 | 경기도 시군 | Y | 백만원 | Y_annual_only | annual_benchmark_consistency | 경기도 경제활동별 지역내총부가가치 및 요소소득은 연간(Y) actual이며 분기 수준값은 아님 |
| KOSIS 301/DT_200Y106 | 경제활동별 GDP 및 GNI(원계열, 실질, 분기 및 연간) | 전국 | Q#Y | 십억원 | Y_national_quarterly_no_region | not_gyeonggi_actual | 전국 경제활동별 실질 GDP/GVA 분기 수준값은 있으나 경기도 지역 차원이 없음 |
| KOSIS statisticsSearch API | 경기도/시도별 분기 GRDP 수준값 검색 | 경기도 또는 시도 | Q |  | N | not_available | 공식 검색 API 후보 0건; raw search saved=True |
| MODS quarterly GRDP PDF | 실질 지역내총생산(잠정) 보도자료 | 시도 | Q | % | Y_growth_only | official_yoy_growth_validation | 시도별 전년동기비 성장률 actual은 확인되나 분기 수준액 actual 표는 확인되지 않음 |
| Statistics Korea experimental quarterly GRDP XLSX | 2026년_1분기_실질_지역내총생산(잠정).xlsx | 시도 | Q#Y | 십억원 | Y_gyeonggi_quarterly_market_price_grdp | official_level_validation_total_market_price | 실질금액 시트에 경기도 지역내총생산(시장가격) 분기 수준값 존재; GVA와 개념 차이는 별도 표시 필요 |

## 데이터 커버리지

- 경기도 시군 수: **31 / 31**
- 산업 수: **16개**
- 기간: **2020Q1~2023Q4**
- 시군×산업×분기 행 수: **7,576행**
- 누락 시군: **없음**

## 요구사항별 완료 감사

| 요구사항 | 증거 | 판정 |
| --- | --- | --- |
| 포스터 미반영 | 보고서 목적과 README/포스터 산출물 미수정 | 충족 |
| 고양시 외 경기도 시군 데이터 구성 | 경기도 31/31개 시군, 7,576행 시군×산업×분기 큐브 | 충족 |
| 고양시 방식과 같은 상위총량 배분·재집계 | 전국 시군구 배분 큐브에서 경기도 추출 후 시군→경기도, 산업→전체로 재집계 | 충족 |
| 경기도 전체 부가가치 산출 | phase209_gyeonggi_total_level_vs_project_target.csv | 충족 |
| actual 경기도 분기 GDP/GRDP 비교 | 통계청 XLSX 경기도 분기 실질 GRDP 시장가격 수준값 및 MODS 성장률 actual과 비교 | 충족_개념차이표시 |
| 자료 수집·재사용 가능성 기록 | phase209_gyeonggi_source_coverage.csv | 충족 |

## 경기도 전체 자료 커버리지

| source | scope | rows | period_min | period_max | geo_count | industry_count | used_in_phase209 | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sigungu_quarterly_gva_allocation_cube | 전국 시군구 원천에서 경기도 31개 시군 추출 | 7576 | 2020Q1 | 2023Q4 | 31 | 16 | Y | 경기도 subset은 원천 전국 큐브에서 필터링; 타 지역 분석 때 원천 전체 재사용 가능 |
| gg_bus_sigun_monthly | 경기도 전체 시군 월별 버스 승하차 | 2325 | 202001 | 202603 | 31 | 1 | inventory_only | 고양시 운수 활동자료와 같은 계열; 이번 수준 검증에는 기존 phase22 큐브 우선 사용 |
| business_employment_feature_table | KOSIS/공공 사업체·종사자·부가가치 계열에서 경기도 31개 시군 추출 | 4900 | 2021 | 2023 | 31 | 27 | coverage_and_followup_feature | 고양시 산업·공간 배분에 쓰는 사업체 계열과 같은 유형; 경기도 31개 시군 모두 보유 |
| kepco_sigungu_electricity_monthly_cube | 전국 시군구 전력 원천에서 경기도 추출 | 1116 | 202101 | 202312 | 31 | 1 | inventory_only | 제조업·전력 기반 시간축 보조자료; 원천은 전국 포함 |
| municipality_electricity_monthly | 전국 시군구 전력 최신 월자료에서 경기도 31개 시군 추출 | 21388 | 202501 | 202604 | 31 | 46 | coverage_and_followup_feature | 2025~2026 최신 전력 자료; 속보성 확장 때 제조업·전기가스 보조지표로 사용 가능 |
| factory_feature_table | 전국 공장등록 특징자료에서 경기도 지리키 추출 | 810 | 2020 | 2024 | 46 | 9 | coverage_and_followup_feature | 경기도 구 단위 지리키 포함으로 46개 키; 시군 단위 사용 전 수원·성남·고양 등 구 통합 필요 |
| buildinghub_feature_table | 건축물대장/건축허가 특징자료의 경기도 전체 커버리지 점검 | 0 |  |  | 0 | 0 | gap_audit | 현재 feature table에는 경기도 전체 키가 없음; 건축계열 경기도 확장에는 원천 재처리 필요 |
| partial_stats_phase52_building_permit_legal_dong_monthly | 건축허가 법정동 월자료의 경기도 확장 가능성 점검 | 2260 | 2021-01 | 2026-06 | 1 | 6 | gap_audit | 현재 산출물은 고양시 중심으로 존재하며 경기도 31개 시군 전체 건설 지표로는 부족 |
| official_quarterly_grdp_2025Q4_pdf | 공식 실험적통계 보도자료의 시도별 GRDP 전년동기비 | 39 | 2018 | 2025Q4 | 1 | 1 | Y | 수준값이 아니라 성장률 actual 비교 기준 |
| official_quarterly_grdp_2025Q4_pdf_level_audit | 공식 보도자료 내 경기도 분기 수준액 표 존재 여부 점검 | 1 | 2025Q4 release | 2025Q4 release | 1 | 1 | audit_only | 경기도 분기 actual 수준값 표는 확인되지 않음; 공식 actual 대조는 전년동기비 성장률로 제한 |
| kosis_actual_source_availability_audit | KOSIS 경기도 연간 actual·전국 분기 GDP·경기도 분기 수준값 검색 결과 | 5 | mixed | mixed | 1 | 1 | audit_only | 경기도 시군·산업 actual은 연간, 전국 GDP/GVA는 분기이나 지역 없음, 경기도 분기 수준값 후보는 미발견 |
| statistics_korea_sido_quarterly_xlsx | 통계청 실험적통계 XLSX 실질금액 시트의 경기도 지역내총생산(시장가격) 분기 수준값 | 90 | 2015Q1 | 2026Q1 | 1 | 2 | Y_level_actual_boundary | 공식 분기 수준 actual로 사용하되, 시장가격 GRDP라서 산업 GVA 합계와 개념 차이 표시 |

## 경기도 수준값 집계검증

아래 표의 target은 기존 프로젝트의 시도 분기 수준 목표 큐브다. 메타상 직접 공식 수준값이 아니라 개발용 분기 수준 기준이므로, 공식 actual 주장은 하지 않는다.

| period | predicted_gyeonggi_gva_eok | target_gyeonggi_grdp_eok | signed_error_eok | total_ape_pct | sector_wape_pct |
| --- | --- | --- | --- | --- | --- |
| 2020Q1 | 1166184.0 | 1154444.0 | 11739.0 | 1.017 | 2.781 |
| 2020Q2 | 1197058.0 | 1197908.0 | -850.0 | 0.071 | 2.56 |
| 2020Q3 | 1215389.0 | 1213008.0 | 2381.0 | 0.196 | 2.261 |
| 2020Q4 | 1295139.0 | 1292121.0 | 3018.0 | 0.234 | 2.543 |
| 2021Q1 | 1200511.0 | 1203249.0 | -2738.0 | 0.228 | 2.789 |
| 2021Q2 | 1278472.0 | 1286493.0 | -8020.0 | 0.623 | 2.544 |
| 2021Q3 | 1294523.0 | 1296177.0 | -1654.0 | 0.128 | 2.428 |
| 2021Q4 | 1388398.0 | 1370716.0 | 17682.0 | 1.29 | 2.459 |
| 2022Q1 | 1301602.0 | 1293830.0 | 7772.0 | 0.601 | 3.954 |
| 2022Q2 | 1382111.0 | 1370312.0 | 11799.0 | 0.861 | 2.231 |
| 2022Q3 | 1318460.0 | 1335935.0 | -17475.0 | 1.308 | 3.608 |
| 2022Q4 | 1351735.0 | 1354089.0 | -2354.0 | 0.174 | 4.017 |
| 2023Q1 | 1234201.0 | 1222135.0 | 12067.0 | 0.987 | 3.236 |
| 2023Q2 | 1333588.0 | 1333422.0 | 166.0 | 0.012 | 2.146 |
| 2023Q3 | 1388539.0 | 1401955.0 | -13416.0 | 0.957 | 3.139 |
| 2023Q4 | 1472828.0 | 1480161.0 | -7333.0 | 0.495 | 2.498 |

## 공식 분기 GRDP 수준값 대조

통계청 실험적통계 XLSX의 `실질금액` 시트에서 경기도 `지역내총생산(시장가격)` 분기 actual을 추출했다. 비교값은 공식 GDP/GRDP 수준 actual이지만, 프로젝트 산출값은 산업별 총부가가치(GVA) 합계이므로 완전한 동종 개념 비교는 아니다.

| period | predicted_gyeonggi_gva_eok | official_gyeonggi_real_grdp_market_price_eok | gva_minus_market_grdp_eok | gap_pct_vs_market_grdp |
| --- | --- | --- | --- | --- |
| 2020Q1 | 1166184.0 | 1244461.0 | -78277.0 | 6.29 |
| 2020Q2 | 1197058.0 | 1294349.0 | -97291.0 | 7.517 |
| 2020Q3 | 1215389.0 | 1306277.0 | -90888.0 | 6.958 |
| 2020Q4 | 1295139.0 | 1386533.0 | -91394.0 | 6.592 |
| 2021Q1 | 1200511.0 | 1294470.0 | -93959.0 | 7.258 |
| 2021Q2 | 1278472.0 | 1400049.0 | -121577.0 | 8.684 |
| 2021Q3 | 1294523.0 | 1383807.0 | -89284.0 | 6.452 |
| 2021Q4 | 1388398.0 | 1461737.0 | -73339.0 | 5.017 |
| 2022Q1 | 1301602.0 | 1353128.0 | -51526.0 | 3.808 |
| 2022Q2 | 1382111.0 | 1458413.0 | -76302.0 | 5.232 |
| 2022Q3 | 1318460.0 | 1435491.0 | -117031.0 | 8.153 |
| 2022Q4 | 1351735.0 | 1472389.0 | -120654.0 | 8.194 |
| 2023Q1 | 1234201.0 | 1322680.0 | -88478.0 | 6.689 |
| 2023Q2 | 1333588.0 | 1430484.0 | -96896.0 | 6.774 |
| 2023Q3 | 1388539.0 | 1473392.0 | -84853.0 | 5.759 |
| 2023Q4 | 1472828.0 | 1546546.0 | -73718.0 | 4.767 |

## GRDP 회계 경계 환산 대조

통계청 XLSX의 시도별 회계식은 `지역내총생산(시장가격) ≈ 광업·제조업 + 건설업 + 서비스업 + 기타산업 및 순생산물세`로 검산된다. 따라서 우리 추정값 중 `광업·제조업·건설업·서비스업`에 해당하는 산업 블록을 합산하고, XLSX의 `기타산업 및 순생산물세` 블록을 붙여 GRDP 시장가격 경계와 비교했다.

이 표는 GVA 합계를 GRDP 회계 경계로 옮겼을 때의 외부 검증이다. 다만 `기타산업 및 순생산물세` 블록은 같은 공식 XLSX에서 가져온 보조 actual이므로, 순수 속보 예측 성능으로 해석하지 않는다.

| period | predicted_gyeonggi_gva_eok | project_grdp_bridge_eok | official_gyeonggi_real_grdp_market_price_eok | grdp_bridge_minus_official_eok | gva_sum_gap_pct_vs_market_grdp | grdp_bridge_gap_pct_vs_market_grdp |
| --- | --- | --- | --- | --- | --- | --- |
| 2020Q1 | 1166184.0 | 1246512.0 | 1244461.0 | 2052.0 | 6.29 | 0.165 |
| 2020Q2 | 1197058.0 | 1288353.0 | 1294349.0 | -5995.0 | 7.517 | 0.463 |
| 2020Q3 | 1215389.0 | 1310937.0 | 1306277.0 | 4660.0 | 6.958 | 0.357 |
| 2020Q4 | 1295139.0 | 1385731.0 | 1386533.0 | -802.0 | 6.592 | 0.058 |
| 2021Q1 | 1200511.0 | 1286621.0 | 1294470.0 | -7849.0 | 7.258 | 0.606 |
| 2021Q2 | 1278472.0 | 1376704.0 | 1400049.0 | -23346.0 | 8.684 | 1.667 |
| 2021Q3 | 1294523.0 | 1391997.0 | 1383807.0 | 8189.0 | 6.452 | 0.592 |
| 2021Q4 | 1388398.0 | 1484742.0 | 1461737.0 | 23005.0 | 5.017 | 1.574 |
| 2022Q1 | 1301602.0 | 1383739.0 | 1353128.0 | 30612.0 | 3.808 | 2.262 |
| 2022Q2 | 1382111.0 | 1476066.0 | 1458413.0 | 17653.0 | 5.232 | 1.21 |
| 2022Q3 | 1318460.0 | 1415817.0 | 1435491.0 | -19674.0 | 8.153 | 1.371 |
| 2022Q4 | 1351735.0 | 1444929.0 | 1472389.0 | -27461.0 | 8.194 | 1.865 |
| 2023Q1 | 1234201.0 | 1305161.0 | 1322680.0 | -17519.0 | 6.689 | 1.324 |
| 2023Q2 | 1333588.0 | 1421224.0 | 1430484.0 | -9261.0 | 6.774 | 0.647 |
| 2023Q3 | 1388539.0 | 1482184.0 | 1473392.0 | 8792.0 | 5.759 | 0.597 |
| 2023Q4 | 1472828.0 | 1566979.0 | 1546546.0 | 20433.0 | 4.767 | 1.321 |

## 공식 연간 benchmark 정합성

경기도 시군×산업 분기 추정값을 연간으로 합산하면 KOSIS 경기도 연간 지역내총부가가치 benchmark와 일치해야 한다. 이는 예측성능이 아니라, 고양시 방식과 같은 상위 actual 보존성 검사다.

| year | quarterly_sum_eok | official_annual_benchmark_eok | signed_gap_eok | ape_pct |
| --- | --- | --- | --- | --- |
| 2020 | 4873769.0 | 4873769.0 | 0.0 | 0.0 |
| 2021 | 5161905.0 | 5161905.0 | 0.0 | 0.0 |
| 2022 | 5353909.0 | 5353909.0 | 0.0 | 0.0 |
| 2023 | 5429156.0 | 5429156.0 | 0.0 | 0.0 |

## 공식 GRDP 성장률 대조

공식 보도자료에서 추출한 경기도 GRDP 전년동기비와, 31개 시군 추정 GVA 합산값에서 계산한 전년동기비를 비교했다.

| period | predicted_yoy_pct | official_gyeonggi_grdp_yoy_pct | yoy_error_pp | abs_yoy_error_pp |
| --- | --- | --- | --- | --- |
| 2021Q1 | 2.944 | 4.0 | -1.056 | 1.056 |
| 2021Q2 | 6.801 | 8.2 | -1.399 | 1.399 |
| 2021Q3 | 6.511 | 5.9 | 0.611 | 0.611 |
| 2021Q4 | 7.201 | 5.4 | 1.801 | 1.801 |
| 2022Q1 | 8.421 | 4.5 | 3.921 | 3.921 |
| 2022Q2 | 8.106 | 4.2 | 3.906 | 3.906 |
| 2022Q3 | 1.849 | 3.7 | -1.851 | 1.851 |
| 2022Q4 | -2.641 | 0.7 | -3.341 | 3.341 |
| 2023Q1 | -5.178 | -2.3 | -2.878 | 2.878 |
| 2023Q2 | -3.511 | -1.9 | -1.611 | 1.611 |
| 2023Q3 | 5.315 | 2.6 | 2.715 | 2.715 |
| 2023Q4 | 8.958 | 5.0 | 3.958 | 3.958 |

## 큰 오차가 발생한 산업·분기

| period | sector_code | sector_name | predicted_gyeonggi_gva_eok | target_gyeonggi_grdp_eok | error_eok | ape_pct |
| --- | --- | --- | --- | --- | --- | --- |
| 2023Q2 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 11381.0 | 19448.0 | -8067.0 | 41.48 |
| 2023Q4 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 14630.0 | 23887.0 | -9257.0 | 38.75 |
| 2020Q2 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 9208.0 | 14794.0 | -5586.0 | 37.76 |
| 2021Q2 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 11460.0 | 18074.0 | -6614.0 | 36.59 |
| 2022Q2 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 12158.0 | 18047.0 | -5889.0 | 32.63 |
| 2023Q3 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 12488.0 | 18445.0 | -5957.0 | 32.3 |
| 2021Q1 | B00 | 광업 | 643.0 | 487.0 | 156.0 | 32.1 |
| 2022Q1 | B00 | 광업 | 630.0 | 479.0 | 151.0 | 31.6 |
| 2021Q1 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 17704.0 | 24765.0 | -7061.0 | 28.51 |
| 2020Q1 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 16868.0 | 23357.0 | -6489.0 | 27.78 |
| 2023Q1 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 16747.0 | 22820.0 | -6073.0 | 26.61 |
| 2022Q4 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 14933.0 | 20160.0 | -5227.0 | 25.93 |

## 해석

- 경기도 31개 시군 모두에 대해 같은 형태의 시군구×산업×분기 추정 데이터는 이미 구성 가능하다.
- 경기도 전체로 합산하면 2020~2023 수준값 기준 평균 절대오차율은 **0.574%**다.
- 다만 이 수준값 대조는 기존 프로젝트 target cube 기준이므로, 공식 actual 검증으로 과장하면 안 된다.
- 통계청 XLSX의 공식 경기도 분기 GRDP 시장가격 수준값과 비교하면 2020~2023 평균 격차율은 **6.509%**, 최대 격차율은 **8.684%**다. 이 격차에는 GVA와 시장가격 GRDP의 개념 차이가 포함된다.
- 같은 XLSX의 회계 보조 블록을 이용해 GRDP 시장가격 경계로 환산하면 2020~2023 평균 격차율은 **1.005%**, 최대 격차율은 **2.262%**다.
- 공식 연간 benchmark 보존성 검사의 최대 절대차는 **0.000000억원**이다.
- 공식 PDF 성장률 기준 2021~2023 평균 절대오차는 **2.421%p**, 최대 절대오차는 **3.958%p**다.
- 후속 작업은 경기도 전체 LOCALDATA·사업체조사·경제총조사 세부자료를 더 결합해, 고양시 포스터 수준의 행정동 해상도가 아니라 경기도 시군구 해상도에서 산업별 오차를 줄이는 방향이 적절하다.

## 산출물

- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_gyeonggi_sigungu_sector_quarterly_gva.parquet`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_gyeonggi_sector_level_vs_project_target.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_gyeonggi_total_level_vs_project_target.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_gyeonggi_annual_benchmark_consistency_by_sector.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_gyeonggi_annual_benchmark_consistency_total.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_official_xlsx_gyeonggi_real_grdp_market_price_level.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_gyeonggi_total_vs_official_xlsx_real_grdp_market_price.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_gyeonggi_project_grdp_bridge_vs_official_xlsx.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_official_gyeonggi_grdp_yoy_growth.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_official_level_table_availability_audit.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_kosis_actual_source_availability_audit.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_gyeonggi_total_yoy_vs_official.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_gyeonggi_source_coverage.csv`
- `data/processed/phase209_gyeonggi_sigungu_gva_expansion/phase209_manifest.json`
