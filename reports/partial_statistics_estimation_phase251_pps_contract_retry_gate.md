# Phase251 조달청 공사계약 201610 재시도 및 건설업 route 게이트

생성시각: 2026-07-29T18:09:00+09:00

## 1. 목적

전국 2015~2025 시군구·업종 GVA/GRDP 추정 목표에서 건설업은 잔여오차가 큰 업종이다. 조달청 나라장터 공사계약정보는 공공공사 계약금액·계약일·착공일을 제공하므로 건설업 보조 활동자료 후보지만, 기존 수집은 API 429 제한으로 2016년 10월 이후 전량 완료되지 않았다.

이번 실험은 첫 미완료월인 `201610`만 일별 분할 방식으로 재시도해, 월 단위 대량조회 실패가 데이터량 문제인지 API 제한 문제인지 확인하는 게 목적이다.

## 2. 실행

```bash
.venv/bin/python nationwide/collect_phase248_pps_contract_incremental.py \
  --start 201610 --end 201610 \
  --daily-split --refresh \
  --sleep 0.02 --retries 3 --retry-sleep 10 --progress-every 5
```

## 3. 결과

| 항목 | 값 |
| --- | --- |
| 대상월 | 201610 |
| 실행 방식 | 일별 분할, 단일 worker |
| 결과 | 실패 |
| 오류 | HTTP 429 Too Many Requests |
| 기존 manifest 기준 API totalCount | 31,271 |
| 기존 manifest 부분 raw rows | 25,974 |
| monthly CSV 생성 | False |
| quality_complete | False |
| 완료월 수 변화 | 21개월 유지 |
| 채택 가능 완전연도 | 1개년 유지 |

201610은 이전 부분 raw가 보존되어 있지만, monthly CSV와 품질완료 조건을 만족하지 못한다. 따라서 부분 raw를 0으로 보정하거나 성능검증에 투입하지 않는다.

## 4. Phase249/250 재검증

| 감사 | 최신 판정 |
| --- | --- |
| Phase249 수집 품질 | 132개월 중 quality_complete 21개월, manifest rows 706,697, 품질완료 rows 613,790, 부분 raw 보존월 8개월 |
| Phase250 건설 route | safe candidate 0개 |
| 검증연도 신호 coverage | contract_date 기준 2021년 2.183%, 2022년 0.873%, 2023년 0.000% |
| 운영 route 채택 | 불가 |

현재 complete 월만 쓰면 검증연도 2021~2023의 시군구 건설업 actual 셀과 PPS 계약 신호가 거의 겹치지 않는다. 따라서 후보 성능표의 동일/악화 결과는 “PPS가 효과 없음”이라기보다 “완료월 coverage 부족으로 아직 rolling 검증 불가”에 가깝다.

## 5. 사전검토 반영 guardrail

과학자 검토 의견에 따라 다음 기준을 고정한다.

| 게이트 | 판정 기준 |
| --- | --- |
| collection_complete | 월별 또는 일별 API totalCount/page coverage 완료 |
| dedupe_complete | 계약번호·계약참조번호 등 중복 제거 기준 고정, raw/dedup 행수 동시 기록 |
| amount_valid | 금액 0·결측·음수·극단값 별도 카운트 |
| geo_match_usable | 시도·시군구 매칭률과 금액 기준 미매칭 비중 확인 |
| production_timing | 계약월, 착공월, 공사기간 분산 배분을 분리 비교 |
| route_candidate | 위 조건 통과 후에도 후보 단계 |
| route_adopted | 충분한 연도에 대해 rolling out-of-year 검증 통과 후에만 채택 |

## 6. 금지 해석

- PPS 계약정보를 전체 건설업 GVA actual로 표현하지 않는다.
- 공공공사 계약액을 민간건설 포함 전체 건설업 생산액·기성액으로 표현하지 않는다.
- 부분 raw 월을 0으로 대체해 성능검증에 투입하지 않는다.
- 단월 수집 성공이나 단월 WAPE 개선만으로 전국 건설업 route를 채택하지 않는다.

## 7. 다음 작업

1. API 429 해제 후 `201610`을 다시 일별 분할로 완료한다.
2. `201611`, `201612`를 같은 방식으로 완료해 2016Q4 3개월 완전성을 먼저 만든다.
3. 2016Q4 기준 중복·금액·지역매칭 감사 통과 여부를 확인한다.
4. 이후 연도 단위 complete가 늘어날 때만 Phase250 rolling 검증을 재실행한다.

현재 결론은 `건설업 PPS 계약 route 미채택 유지`다.
