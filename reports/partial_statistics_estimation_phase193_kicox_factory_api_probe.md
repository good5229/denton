# Phase193 KICOX 공장등록 API 전용 프로브

## 목적

Phase181의 KICOX 구 endpoint 404를 보정하기 위해, 공공데이터포털 문서/공지에 맞춘 생산정보 v2와 필지정보 endpoint를 회사명 조건으로 소량 재점검했다. serviceKey는 캐시와 보고서에 저장하지 않는다.

## 결과

| source_name | status | http_status | result_code | result_msg | total_count | item_count | sample_fields | target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 공장등록생산정보: 포스코 회사명 검색 | ok_items | 200 | 00 | NORMAL_SERVICE | 74 | 5 | fctryManageNo, cmpnyNm, rnAdres, rprsntvNm, cvplChrgOrgnztNm, cmpnyTelno, cmpnyFxnum, allEmplyCo, frstFctryRegistDe, rprsntvIndutyCode, indutyCodes, indutyNm, mainProductCn, hmpadr, irsttNm | 포항 C24/C25/C28/C34 |
| 공장등록생산정보: 삼성전자 회사명 검색 | ok_items | 200 | 00 | NORMAL_SERVICE | 14 | 5 | fctryManageNo, cmpnyNm, rnAdres, rprsntvNm, cvplChrgOrgnztNm, cmpnyTelno, cmpnyFxnum, allEmplyCo, frstFctryRegistDe, rprsntvIndutyCode, indutyCodes, indutyNm, mainProductCn, hmpadr, irsttNm | C26/C28 endpoint sanity check |
| 공장등록필지정보: 포스코 회사명 검색 | http_error | 403 |  | Forbidden<br> |  | 0 |  | 포항 C24/C25 공간·면적 |
| 공장등록필지정보: 삼성전자 회사명 검색 | http_error | 403 |  | Forbidden<br> |  | 0 |  | endpoint sanity check |

## 즉시 활용 가능

| source_name | total_count | sample_fields | target | use_note |
| --- | --- | --- | --- | --- |
| 공장등록생산정보: 포스코 회사명 검색 | 74 | fctryManageNo, cmpnyNm, rnAdres, rprsntvNm, cvplChrgOrgnztNm, cmpnyTelno, cmpnyFxnum, allEmplyCo, frstFctryRegistDe, rprsntvIndutyCode, indutyCodes, indutyNm, mainProductCn, hmpadr, irsttNm | 포항 C24/C25/C28/C34 | 포항 철강·금속·전기장비 관련 대표 기업 필드 확인 |
| 공장등록생산정보: 삼성전자 회사명 검색 | 14 | fctryManageNo, cmpnyNm, rnAdres, rprsntvNm, cvplChrgOrgnztNm, cmpnyTelno, cmpnyFxnum, allEmplyCo, frstFctryRegistDe, rprsntvIndutyCode, indutyCodes, indutyNm, mainProductCn, hmpadr, irsttNm | C26/C28 endpoint sanity check | 공공데이터포털 샘플성 회사명으로 정상 응답 여부 확인 |

## 추가 조치 필요

| source_name | status | http_status | result_msg | source_url |
| --- | --- | --- | --- | --- |
| 공장등록필지정보: 포스코 회사명 검색 | http_error | 403 | Forbidden<br> | https://www.data.go.kr/data/15087615/openapi.do |
| 공장등록필지정보: 삼성전자 회사명 검색 | http_error | 403 | Forbidden<br> | https://www.data.go.kr/data/15087615/openapi.do |

## 산출물

- `data/processed/phase193_kicox_factory_api_probe/phase193_kicox_factory_api_probe_summary.csv`
- `data/raw/phase193_kicox_factory_api_probe/` 원문 응답 캐시(serviceKey 마스킹)
