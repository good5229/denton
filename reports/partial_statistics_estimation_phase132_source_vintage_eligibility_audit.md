# Phase132 고양·포항 자료 공표시차 및 속보 적격성 감사

## 목적

Phase131의 분기별 rolling GVA 갱신을 실제 속보 체계로 승격하기 위해, 로컬에 남아 있는 source/audit/manifest 파일을 기준으로 자료별 Q+1개월 사용 가능성을 분리했다. 원 공표일자나 as-of archive가 없으면 엄격 속보에는 넣지 않는 보수 기준을 적용했다.

## 소스 등급 요약

| city | strict flash class | source count |
| --- | --- | --- |
| 고양시 | needs_publication_calendar | 20 |
| 고양시 | not_flash_precision_or_unknown | 9 |
| 고양시 | not_strict_flash_current_snapshot | 26 |
| 고양시 | not_strict_flash_without_asof_archive | 19 |
| 고양시 | strict_flash_event_source | 6 |
| 고양시 | strict_flash_static_structure | 13 |
| 공통 | needs_publication_calendar | 1 |
| 공통 | strict_flash_only_after_release | 3 |
| 포항시 | needs_publication_calendar | 22 |
| 포항시 | not_flash_precision_or_unknown | 9 |
| 포항시 | strict_flash_event_source | 6 |
| 포항시 | strict_flash_static_structure | 13 |

## 빈티지별 적격성 요약

| city | vintage label | strict flash eligible | source count |
| --- | --- | --- | --- |
| 고양시 | 1~2분기+1개월 | N | 45 |
| 고양시 | 1~2분기+1개월 | PARTIAL | 3 |
| 고양시 | 1~2분기+1개월 | UNKNOWN | 29 |
| 고양시 | 1~2분기+1개월 | Y | 16 |
| 고양시 | 1~3분기+1개월 | N | 45 |
| 고양시 | 1~3분기+1개월 | PARTIAL | 3 |
| 고양시 | 1~3분기+1개월 | UNKNOWN | 29 |
| 고양시 | 1~3분기+1개월 | Y | 16 |
| 고양시 | 1~4분기+1개월 | N | 45 |
| 고양시 | 1~4분기+1개월 | PARTIAL | 6 |
| 고양시 | 1~4분기+1개월 | UNKNOWN | 29 |
| 고양시 | 1~4분기+1개월 | Y | 13 |
| 고양시 | 1분기+1개월 | N | 45 |
| 고양시 | 1분기+1개월 | PARTIAL | 3 |
| 고양시 | 1분기+1개월 | UNKNOWN | 29 |
| 고양시 | 1분기+1개월 | Y | 16 |
| 공통 | 1~2분기+1개월 | N | 3 |
| 공통 | 1~2분기+1개월 | UNKNOWN | 1 |
| 공통 | 1~3분기+1개월 | N | 2 |
| 공통 | 1~3분기+1개월 | PARTIAL | 1 |
| 공통 | 1~3분기+1개월 | UNKNOWN | 1 |
| 공통 | 1~4분기+1개월 | N | 2 |
| 공통 | 1~4분기+1개월 | PARTIAL | 1 |
| 공통 | 1~4분기+1개월 | UNKNOWN | 1 |
| 공통 | 1분기+1개월 | N | 3 |
| 공통 | 1분기+1개월 | UNKNOWN | 1 |
| 포항시 | 1~2분기+1개월 | PARTIAL | 3 |
| 포항시 | 1~2분기+1개월 | UNKNOWN | 31 |
| 포항시 | 1~2분기+1개월 | Y | 16 |
| 포항시 | 1~3분기+1개월 | PARTIAL | 3 |
| 포항시 | 1~3분기+1개월 | UNKNOWN | 31 |
| 포항시 | 1~3분기+1개월 | Y | 16 |
| 포항시 | 1~4분기+1개월 | PARTIAL | 6 |
| 포항시 | 1~4분기+1개월 | UNKNOWN | 31 |
| 포항시 | 1~4분기+1개월 | Y | 13 |
| 포항시 | 1분기+1개월 | PARTIAL | 3 |
| 포항시 | 1분기+1개월 | UNKNOWN | 31 |
| 포항시 | 1분기+1개월 | Y | 16 |

## 엄격 속보에 넣을 수 있는 자료

| city | source id | source label | source family | strict flash class | reason | evidence files |
| --- | --- | --- | --- | --- | --- | --- |
| 고양시 | pps_bid_notice_cnstwk | 조달청 입찰공고 cnstwk | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 고양시 | pps_bid_notice_cnstwk_pps | 조달청 입찰공고 cnstwk_pps | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 고양시 | pps_bid_notice_servc | 조달청 입찰공고 servc | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 고양시 | pps_bid_notice_servc_pps | 조달청 입찰공고 servc_pps | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 고양시 | pps_bid_notice_thng | 조달청 입찰공고 thng | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 고양시 | pps_bid_notice_thng_pps | 조달청 입찰공고 thng_pps | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 고양시 | flash_agri_2015_small_sales_middle | 2015 농림어업 세부매출 중분류 집계 | A00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_kosis_2021_sigungu_middle_establishments_raw | KOSIS 2021 이전 시군구×중분류 사업체수 | C00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_kosis_mfg_2021_employees | KOSIS 제조·광업 2021 employees | C00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_kosis_mfg_2021_establishments | KOSIS 제조·광업 2021 establishments | C00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_kosis_mfg_2021_value_added | KOSIS 제조·광업 2021 value_added | C00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | phase120_personal_business_finance_abs_sale_lag2021 | 개인사업자 절대 매출합계 | C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 고양시 | phase120_personal_business_finance_asset_pos_lag2021 | 개인사업자 양수 자산합계 | C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 고양시 | phase120_personal_business_finance_positive_sale_lag2021 | 개인사업자 양수 매출합계 | C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 고양시 | phase120_personal_business_finance_profit_pos_lag2021 | 개인사업자 양수 영업이익합계 | C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 고양시 | phase120_personal_business_finance_rows_lag2021 | 개인사업자 재무/매출 행수 | C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 고양시 | phase120_personal_business_sales_abs_sale_lag2021 | 개인사업자 절대 매출합계 | C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 고양시 | phase120_personal_business_sales_positive_sale_lag2021 | 개인사업자 양수 매출합계 | C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 고양시 | phase120_personal_business_sales_rows_lag2021 | 개인사업자 재무/매출 행수 | C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 공통 | kepco_industry_2023 | KEPCO electricity | KSIC broad and middle | strict_flash_only_after_release | 명시 release_date가 있으므로 cutoff와 직접 비교 | partial_stats_phase35_source_inventory.csv |
| 공통 | kepco_industry_2024 | KEPCO electricity | KSIC broad and middle | strict_flash_only_after_release | 명시 release_date가 있으므로 cutoff와 직접 비교 | partial_stats_phase35_source_inventory.csv |
| 공통 | kepco_industry_2025 | KEPCO electricity | KSIC broad and middle | strict_flash_only_after_release | 명시 release_date가 있으므로 cutoff와 직접 비교 | partial_stats_phase35_source_inventory.csv |
| 포항시 | pps_bid_notice_cnstwk | 조달청 입찰공고 cnstwk | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 포항시 | pps_bid_notice_cnstwk_pps | 조달청 입찰공고 cnstwk_pps | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 포항시 | pps_bid_notice_servc | 조달청 입찰공고 servc | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 포항시 | pps_bid_notice_servc_pps | 조달청 입찰공고 servc_pps | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 포항시 | pps_bid_notice_thng | 조달청 입찰공고 thng | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 포항시 | pps_bid_notice_thng_pps | 조달청 입찰공고 thng_pps | procurement | strict_flash_event_source | 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능 | phase122_pps_goyang_pohang_monthly_summary.csv |
| 포항시 | flash_agri_2015_small_sales_middle | 2015 농림어업 세부매출 중분류 집계 | A00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_kosis_2021_sigungu_middle_establishments_raw | KOSIS 2021 이전 시군구×중분류 사업체수 | C00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_kosis_mfg_2021_employees | KOSIS 제조·광업 2021 employees | C00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_kosis_mfg_2021_establishments | KOSIS 제조·광업 2021 establishments | C00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_kosis_mfg_2021_value_added | KOSIS 제조·광업 2021 value_added | C00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | phase120_personal_business_finance_abs_sale_lag2021 | 개인사업자 절대 매출합계 | A00, C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 포항시 | phase120_personal_business_finance_asset_pos_lag2021 | 개인사업자 양수 자산합계 | A00, C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 포항시 | phase120_personal_business_finance_positive_sale_lag2021 | 개인사업자 양수 매출합계 | A00, C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 포항시 | phase120_personal_business_finance_profit_pos_lag2021 | 개인사업자 양수 영업이익합계 | A00, C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 포항시 | phase120_personal_business_finance_rows_lag2021 | 개인사업자 재무/매출 행수 | A00, C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 포항시 | phase120_personal_business_sales_abs_sale_lag2021 | 개인사업자 절대 매출합계 | A00, C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 포항시 | phase120_personal_business_sales_positive_sale_lag2021 | 개인사업자 양수 매출합계 | A00, C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |
| 포항시 | phase120_personal_business_sales_rows_lag2021 | 개인사업자 재무/매출 행수 | A00, C00, ERS, F00, G00, H00, I00, J00, MN0, Q00 | strict_flash_static_structure | 과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시 | phase120_all_candidate_indicators.csv |

## 정밀화 전용 또는 monitoring 전용 자료

| city | source id | source label | source family | strict flash class | precision class | reason |
| --- | --- | --- | --- | --- | --- | --- |
| 고양시 | goyang_kosis_media_count | 언론매체 방송사 수 | J00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_kosis_sewer_capacity | 공공하수처리시설 시설용량 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_kosis_sewer_volume | 공공하수처리시설 처리량 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_kosis_waste_volume | 쓰레기 배출·처리량 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_localdata_food | LOCALDATA 음식점 영업재고 | I00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_localdata_large_retail | LOCALDATA 대규모점포 영업재고 | G00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_localdata_lodging | LOCALDATA 숙박업 영업재고 | I00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_localdata_personal_service | LOCALDATA 개인서비스 영업재고 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_apt_trade_value | 아파트 실거래 금액 | MN0 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_auto_building_count | 자동차관련 건축물 수 | G00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_business_building_count | 업무시설 건축물 수 | MN0 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_culture_building_count | 문화·집회 건축물 수 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_facility_management_count | 대형 관리대상 건축물 수 | MN0 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_hospital_area | 병의원 연면적 | Q00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_hospital_beds | 병의원 병상 수 | Q00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_library_area | 도서관 건축면적 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_park_area | 고양 도시공원 면적 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_parking_slots | 주차장 주차면수 | G00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_realestate_building_count | 주거·상업 건축물 수 | MN0 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_research_building_count | 교육연구시설 건축물 수 | MN0 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_retail_building_count | 판매·근린생활 건축물 수 | G00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_sports_building_count | 운동시설 건축물 수 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_sports_facilities | 고양 체육시설 수 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_openapi_waste_building_count | 분뇨·쓰레기·자원순환 건축물 수 | ERS | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_saupm78_mfg_16118ED_1 | 고용노동부 2024 제조업 사업체수 | C00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_saupm78_mfg_16118ED_9A | 고용노동부 2024 제조업 종사자수 | C00 | not_strict_flash_current_snapshot | precision_only_current_snapshot | 현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지 |
| 고양시 | goyang_localdata_barber_shops | 이용업 | S00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_beauty_salons | 미용업 | S00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_billiard_halls | 당구장업 | R00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_clinics | 의원 | Q00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_fitness_centers | 체력단련장업 | R00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_general_restaurants | 일반음식점 | I00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_golf_practice_ranges | 골프연습장업 | R00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_hospitals | 병원 | Q00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_large_scale_retail_stores | 대규모점포 | G00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_laundries | 세탁업 | S00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_lodgings | 숙박업 | I00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_martial_arts_dojo | 체육도장업 | R00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_museums_and_art_galleries | 박물관·미술관 | R00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_pc_bangs | 인터넷컴퓨터게임시설제공업 | R00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_performance_halls | 공연장 | R00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_pharmacies | 약국 | Q00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_public_baths | 목욕장업 | S00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_rest_cafes | 휴게음식점 | I00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |
| 고양시 | goyang_localdata_tourist_accommodations | 관광숙박업 | I00 | not_strict_flash_without_asof_archive | precision_or_monitoring_after_collection | 인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음 |

## 공표일자 확인 필요 자료

| city | source id | source label | source family | strict flash class | reason | request to user | evidence files |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | flash_building_permit_area_ytd | 고양시 허가면적 누적 | F00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_building_start_area_ytd | 고양시 착공면적 누적 | F00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_goyang_bus_passenger_ytd | 고양 버스 승하차 누적 | H00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_ERS_90_active_area | 고양시 인허가 영업면적 90 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_ERS_90_active_count | 고양시 인허가 영업재고 90 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_ERS_91_active_area | 고양시 인허가 영업면적 91 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_ERS_91_active_count | 고양시 인허가 영업재고 91 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_ERS_96_active_area | 고양시 인허가 영업면적 96 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_ERS_96_active_count | 고양시 인허가 영업재고 96 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_G00_47_active_area | 고양시 인허가 영업면적 47 | G00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_G00_47_active_count | 고양시 인허가 영업재고 47 | G00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_H52_logistics_warehouse_capacity | 고양시 물류창고 영업면적·사업장 | H00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_I00_55_active_area | 고양시 인허가 영업면적 55 | I00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_I00_55_active_count | 고양시 인허가 영업재고 55 | I00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_I00_56_active_area | 고양시 인허가 영업면적 56 | I00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_I00_56_active_count | 고양시 인허가 영업재고 56 | I00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_Q00_86_active_area | 고양시 인허가 영업면적 86 | Q00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_localdata_Q00_86_active_count | 고양시 인허가 영업재고 86 | Q00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | flash_rail_passenger_ytd | 고양시 철도 승하차 누적 | H00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 고양시 | molit_apt_trade_15126469 | 국토부 아파트 실거래가 | real_estate | needs_publication_calendar | 월별 조회 가능하지만 각 거래월의 최초 공개일자가 로컬 manifest에 없음 | 국토부 실거래가 API의 거래월별 최초 공개 가능일/갱신주기 확인 필요 | partial_stats_phase55_rtms_apt_trade_call_manifest.csv |
| 공통 | nts_lifestyle_monthly_2021_2023 | National Tax Service business registry | NTS 100 lifestyle industries (122 labels across revisions) | needs_publication_calendar | 월별 vintage라 적혀 있으나 월별 실제 공표일자가 없음 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | partial_stats_phase35_source_inventory.csv |
| 포항시 | flash_building_permit_area_ytd | 포항시 허가면적 누적 | F00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_building_start_area_ytd | 포항시 착공면적 누적 | F00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_ERS_90_active_area | 포항시 인허가 영업면적 90 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_ERS_90_active_count | 포항시 인허가 영업재고 90 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_ERS_91_active_area | 포항시 인허가 영업면적 91 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_ERS_91_active_count | 포항시 인허가 영업재고 91 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_ERS_96_active_area | 포항시 인허가 영업면적 96 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_ERS_96_active_count | 포항시 인허가 영업재고 96 | ERS | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_G00_47_active_area | 포항시 인허가 영업면적 47 | G00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_G00_47_active_count | 포항시 인허가 영업재고 47 | G00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_H52_logistics_warehouse_capacity | 포항시 물류창고 영업면적·사업장 | H00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_I00_55_active_area | 포항시 인허가 영업면적 55 | I00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_I00_55_active_count | 포항시 인허가 영업재고 55 | I00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_I00_56_active_area | 포항시 인허가 영업면적 56 | I00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_I00_56_active_count | 포항시 인허가 영업재고 56 | I00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_Q00_86_active_area | 포항시 인허가 영업면적 86 | Q00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_localdata_Q00_86_active_count | 포항시 인허가 영업재고 86 | Q00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_mof_pohang_port_cargo_total_ytd_lag2 | 포항항 총 화물처리량 누적 | H00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 해양수산통계 DT_MLTM_1310의 월별 공표일/갱신주기 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_mof_pohang_steel_related_port_cargo_ytd_lag2 | 포항항 철강 관련 화물처리량 누적 | C00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 해양수산통계 DT_MLTM_1310의 월별 공표일/갱신주기 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | flash_rail_passenger_ytd | 포항시 철도 승하차 누적 | H00 | needs_publication_calendar | 속보성 후보지만 원 공표일자/시차 확인 필요 | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 | phase117_flash_indicators.csv, phase120_all_candidate_indicators.csv |
| 포항시 | mof_DT_MLTM_1310_pohang_port_cargo | 해양수산통계 포항항 품목별 화물 입출항현황 | port_logistics | needs_publication_calendar | 포항항 월별 물동량 자료는 확보했지만 Q+1개월 적격성을 판단할 공표일자 메타데이터가 없음 | 해양수산통계 DT_MLTM_1310의 월별 공표일/갱신주기 확인 필요 | phase118_public_sources |
| 포항시 | molit_apt_trade_15126469 | 국토부 아파트 실거래가 | real_estate | needs_publication_calendar | 월별 조회 가능하지만 각 거래월의 최초 공개일자가 로컬 manifest에 없음 | 국토부 실거래가 API의 거래월별 최초 공개 가능일/갱신주기 확인 필요 | partial_stats_phase55_rtms_apt_trade_call_manifest.csv |

## 판정

1. KEPCO처럼 release_date가 명시된 자료는 Q+1개월 cutoff와 직접 비교해야 한다. 로컬 inventory 기준 2023년 1~3월 전력자료는 2023-08-16 공개라 2023-04-30 Q1+1개월 strict flash에는 부적격이다.
2. KOSIS 2021/2015 구조자료처럼 과거 구조로 명시된 자료는 2023년 strict flash 구조축에 사용할 수 있다.
3. 고양 LOCALDATA/OpenAPI 현재 snapshot, COMWEL 사업장 구조, 고양시 통계시설 자료는 정밀화/운영경보에는 유용하지만 과거 as-of archive가 없으면 strict flash에는 넣지 않는다.
4. 조달청 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 쓰는 조건에서 strict flash 후보가 될 수 있다.
5. 해양수산통계 포항항 물동량과 국토부 실거래가는 자료는 확보했지만, 월별 최초 공표일/갱신주기 메타데이터가 로컬에 없어 strict flash 투입 전 원 출처 확인이 필요하다.
