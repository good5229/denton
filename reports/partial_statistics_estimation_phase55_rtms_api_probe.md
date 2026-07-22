# Phase55 국토교통부 아파트 매매 실거래가 API 응답 확인

## 결론

- `https://www.data.go.kr/data/15126469/openapi.do`의 공식 gateway endpoint는 사용 가능하다.
- 2024년 고양·포항 5개 구×12개월 60회 호출이 모두 정상 응답을 반환했다.
- 호출시간은 중앙값 1.023초, 평균 1.856초, p90 4.958초, 최대 10.737초였다. 느린 API라기보다는 일부 호출 편차가 있는 API다.
- 이전 Phase53 지연은 API 자체 속도 문제가 아니라, 서비스키 인코딩 방식과 잘못된 endpoint/source endpoint probe가 섞인 문제였다.
- 일일 10,000건 한도 대비 이번 검증 수집은 key-mode probe 포함 약 61건 수준이라 안전한 범위다. 월별 전국 전체 수집은 호출 수를 따로 계산해야 한다.

## 공식 메타데이터

- 공공데이터포털: `https://www.data.go.kr/data/15126469/openapi.do`
- 공식 Swagger host/path: `apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade`
- 필수 파라미터: `LAWD_CD`, `DEAL_YMD`, `serviceKey`

## 키/인코딩 probe

| key_slot | key_mode | http_status | elapsed_sec | result_code | result_msg | total_count | item_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DATA_GO_KR_ENCODING | as_is | 200 | 9.952 | 0 | OK | 295 | 10 |

## 2024년 고양·포항 구 단위 수집 호출시간

| call_count | min_sec | median_sec | mean_sec | p90_sec | max_sec | total_items |
| --- | --- | --- | --- | --- | --- | --- |
| 60.0 | 0.124 | 1.022 | 1.856 | 4.958 | 10.737 | 14458.0 |

## 느린 호출 상위

| city | general_gu | period | elapsed_sec | item_count | result_code | result_msg |
| --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 덕양구 | 202401 | 10.737 | 295 | 0 | OK |
| 고양시 | 일산서구 | 202405 | 9.524 | 266 | 0 | OK |
| 고양시 | 일산서구 | 202401 | 8.599 | 206 | 0 | OK |
| 고양시 | 일산동구 | 202412 | 8.333 | 119 | 0 | OK |
| 고양시 | 덕양구 | 202402 | 5.979 | 256 | 0 | OK |
| 고양시 | 일산서구 | 202407 | 5.356 | 351 | 0 | OK |
| 고양시 | 덕양구 | 202406 | 4.914 | 417 | 0 | OK |
| 고양시 | 일산동구 | 202409 | 4.602 | 169 | 0 | OK |

## 수집 거래 요약

| city | general_gu | deal_count | deal_amount_10k_krw | exclusive_area_sqm |
| --- | --- | --- | --- | --- |
| 고양시 | 덕양구 | 3907 | 202273080.0 | 290237.91 |
| 고양시 | 일산동구 | 2156 | 114522063.0 | 189019.85 |
| 고양시 | 일산서구 | 2842 | 120777021.0 | 233663.8 |
| 포항시 | 남구 | 2352 | 45843149.0 | 172771.38 |
| 포항시 | 북구 | 3201 | 61457761.0 | 246715.24 |

## 산출 파일

- `data/processed/partial_stats_phase55_rtms_api_key_mode_probe.csv`
- `data/processed/partial_stats_phase55_rtms_apt_trade_call_manifest.csv`
- `data/processed/partial_stats_phase55_rtms_apt_trade_goyang_pohang_2024.csv`
- `data/processed/partial_stats_phase55_rtms_apt_trade_gu_monthly.csv`