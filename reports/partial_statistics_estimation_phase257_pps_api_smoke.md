# Phase257 조달청 PPS API smoke 재시도

생성시각: 2026-07-29T21:06:32+09:00

## 목적

사용자가 공공데이터포털 활용신청/키 상태를 갱신한 뒤, 기존에 막혔던 조달청 공사계약·공사공고 API가 다시 접근 가능한지만 극소량으로 확인했다. 이 smoke는 raw 페이지를 저장하지 않으며, 건설업 route 성능검증이나 채택 근거가 아니다.

## 호출 결과

| check | endpoint | http_status | http_error | resultCode | resultMsg | totalCount | raw_saved | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pps_contract_20161001_n1 | getCntrctInfoListCnstwk |  | 429 |  |  |  | False | Too Many Requests |
| pps_bid_202108_page34_n100 | getBidPblancListInfoCnstwk |  | 429 |  |  |  | False | Too Many Requests |

## 판정

- API 접근 판정: `blocked_by_api_or_rate_limit`
- 공사계약: 20161001 하루, 1행 요청만 수행. 성공해도 201610 월 전체 수집 완료가 아니다.
- 공사공고: 202108 page 34, 100행 요청만 수행. 성공해도 202108은 92/92 page 완전월 전까지 성능검증에서 제외한다.
- raw 저장 여부: 모든 호출 `False`.
- route 사용 여부: 변경 없음. PPS 계약은 quality complete 월만, PPS 공사공고는 완전월만 rolling 검증에 투입한다.

## 후속 기준

1. smoke가 성공하면 202108 공사공고는 page 34 단일 저장 → completeness 재감사 → 작은 page chunk 순으로만 확장한다.
2. 계약정보는 201610 월 전체 또는 일별 split이 complete될 때까지 건설업 전국 route 채택에 쓰지 않는다.
3. 부분월·부분 page는 성능표, route ranking, 포스터/대외 주장에 사용하지 않는다.
