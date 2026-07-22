# Phase53 무료 후보자료 수집 및 저장공간 진단

## 결론

- 고양시·포항시 부동산중개업 파일은 직접 수집했고, 부동산 관련 서비스업 보강 피처로 정규화했다.
- 실거래가 API는 기존 공공데이터포털 키로 지역·월 단위 호출을 시도해 결과와 실패사유를 캐시에 남겼다.
- 공동주택 공시가격은 무료이나 1,558만 건 대용량 전국 파일이므로, 현재 저장공간 조건에서는 메타데이터만 확보하고 지역추출/외부캐시 전략 확정 후 수집하는 것이 안전하다.
- 현재 진단 대상 파일 총량: 6.58GB.

## 수집 결과

| source_id | source_name | target_industry | file_collection_status | local_path | content_url | external_url |
| --- | --- | --- | --- | --- | --- | --- |
| goyang_real_estate_broker_file | 경기도 고양시_부동산중개업 현황 | L00/682 부동산 관련 서비스 | downloaded | data/raw/phase53_free_candidate_sources/goyang_real_estate_broker_file_download.csv | https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003612428&fileDetailSn=1&insertDataPrcus=N | https://data.gg.go.kr/portal/data/service/selectServicePage.do?page=1&sortColumn=&sortDirection=&infId=PCG359G8UAD471M0GE9K15277158&infSeq=3 |
| pohang_real_estate_broker_file | 경상북도 포항시_개업공인중개사사무소 현황 | L00/682 부동산 관련 서비스 | downloaded | data/raw/phase53_free_candidate_sources/pohang_real_estate_broker_file_download.csv | https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003616635&fileDetailSn=1&insertDataPrcus=N | null |
| gyeonggi_bus_stop_daily_boarding_file | 경기도_정류소 별 승하차 인원 집계 | H00/492 육상 여객 운송업 | download_failed |  | https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId=MZCREO5CKHZM6PJEA55P37391662&infSeq=1 | # |
| korail_intercity_station_daily_passenger_file | 한국철도공사_간선여객 승하차 인원수 | H00/491 철도 운송업 | downloaded | data/raw/phase53_free_candidate_sources/korail_station_daily_passenger_download.bin | https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003249358&fileDetailSn=1&insertDataPrcus=N | null |
| molit_public_housing_price_file | 국토교통부_주택 공시가격 정보 | L00/681 부동산 임대 및 공급업 | deferred_large_15_58m_rows |  | https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003525375&fileDetailSn=1&insertDataPrcus=N |  |
| niier_livestock_aquaculture_inventory | 국립환경과학원_축산/양식 인벤토리 후보 | A00 농림어업 | downloaded | data/raw/phase53_free_candidate_sources/niier_livestock_aquaculture_inventory_download.bin | https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003546074&fileDetailSn=1&insertDataPrcus=N |  |
| mof_port_cargo_api | 해양수산부_화물처리실적통계 | H00/501 수상 운송업·항만 물류 | no_direct_file_url |  |  |  |

## 부동산중개업 구 단위 피처

| city | general_gu | count |
| --- | --- | --- |
| 고양시 | 덕양구 | 973 |
| 고양시 | 일산동구 | 700 |
| 고양시 | 일산서구 | 514 |
| 포항시 | 남구 | 305 |
| 포항시 | 북구 | 566 |

## 실거래가 API 호출 요약

| source_id | collection_status | calls | items |
| --- | --- | --- | --- |
| molit_apt_trade | deferred_endpoint_stalled_during_probe | 1 | 0 |
| molit_non_residential_trade | deferred_endpoint_stalled_during_probe | 1 | 0 |

## 철도 승하차 지역 추출

| city | general_gu | station_name | days | total_passengers |
| --- | --- | --- | --- | --- |
| 고양시 | 덕양구 | 행신 | 365 | 2081381 |
| 포항시 | 북구 | 포항 | 365 | 2963151 |

## 수집 보류/수동 확인 링크

| source_id | source_name | portal_url | content_url | external_url | file_collection_status |
| --- | --- | --- | --- | --- | --- |
| gyeonggi_bus_stop_daily_boarding_file | 경기도_정류소 별 승하차 인원 집계 | https://www.data.go.kr/data/15144886/fileData.do | https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId=MZCREO5CKHZM6PJEA55P37391662&infSeq=1 | # | download_failed |
| molit_public_housing_price_file | 국토교통부_주택 공시가격 정보 | https://www.data.go.kr/data/3073746/fileData.do | https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003525375&fileDetailSn=1&insertDataPrcus=N |  | deferred_large_15_58m_rows |
| mof_port_cargo_api | 해양수산부_화물처리실적통계 | https://www.data.go.kr/dataset/3036255/openapi.do |  |  | no_direct_file_url |

## 저장공간 개선안

1. 원자료는 `source_id`, 원 URL, 다운로드시각, SHA-256, 행수, 스키마 fingerprint만 manifest로 남기고, 대용량 본체는 repo 밖 외부 캐시 또는 DVC/git-annex로 분리한다.
2. 반복 재생산 가능한 중간 CSV는 Parquet/Zstd로 전환하고, CSV 원본은 해시 검증 후 삭제 승인 대상으로 둔다.
3. 잘못 받은 `폐쇄말소대장_표제부` 145MB 파일은 표제부 현행자료와 별개이므로 사용자 승인 후 삭제 또는 quarantine 이동 대상이다.
4. 공시가격·건축물대장처럼 전국 대용량 파일은 전체 파일을 계속 repo 내부에 두기보다, 지역 추출본과 원천 manifest만 프로젝트에 남기는 편이 맞다.

## 산출 파일

- `data/processed/partial_stats_phase53_candidate_source_manifest.csv`
- `data/processed/partial_stats_phase53_realestate_broker_goyang_pohang.csv`
- `data/processed/partial_stats_phase53_realestate_broker_gu_features.csv`
- `data/processed/partial_stats_phase53_rtms_collection_manifest.csv`
- `data/processed/partial_stats_phase53_korail_station_monthly_features.csv`
- `data/processed/partial_stats_phase53_storage_inventory.csv`