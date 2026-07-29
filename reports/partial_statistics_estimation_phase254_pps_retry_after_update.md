# Phase254 조달청 PPS 재시도 감사

생성시각: 2026-07-29T18:32:00+09:00

## 1. 목적

전국 2015~2025 시군구·업종 GVA/GRDP 추정에서 건설업은 잔여오차가 큰 업종이다. 조달청 나라장터 공사계약과 공사공고는 무료 공개자료 중 공공공사 위치·금액 신호를 가장 직접적으로 제공하는 후보지만, 이전 수집은 `HTTP 429 Too Many Requests`로 중단되어 있었다.

사용자가 API 승인·키 업데이트를 완료했다고 알려준 뒤, 첫 미완료 구간을 작게 재시도해 수집 재개 가능성을 확인했다.

## 2. 재시도 결과

| 구분 | 대상 | 명령 | 결과 |
| --- | --- | --- | --- |
| 공사계약 | `201610` | `.venv/bin/python nationwide/collect_phase248_pps_contract_incremental.py --start 201610 --end 201610 --daily-split --num-rows 999 --sleep 0.2 --retries 1 --retry-sleep 1 --progress-every 5` | 첫 호출부터 `HTTP 429`, 완료행 0 |
| 공사공고 | `202108`, page 34~35 | `.venv/bin/python nationwide/collect_pps_construction_robust.py --start 202108 --end 202108 --num-rows 100 --start-page 34 --end-page 35 --sleep 0.2` | page 34에서 `HTTP 429`, 중단 |

## 3. 최신 수집 감사

| 항목 | 값 |
| --- | ---: |
| 공사계약 기대 월 | 132 |
| 공사계약 완료 월 | 21 |
| 공사계약 미완료 월 | 111 |
| 첫 미완료 월 | 201610 |
| 공사계약 CSV 행 수 | 613,790 |
| 공사계약 시도 매칭률 | 87.33% |
| 공사계약 시군구 매칭률 | 74.51% |
| 공사공고 완전월 | 202104, 202105, 202106, 202107 |
| 공사공고 첫 미완전월 | 202108 |

## 4. 판정

| 항목 | 판정 |
| --- | --- |
| 키·승인 문제 | 단정 불가. 승인 후에도 429가 재현되어 대량조회 rate-limit 또는 기관 API 제한 가능성이 큼 |
| 건설업 PPS 계약 route | 미채택 유지 |
| 건설업 PPS 공고 route | 미채택 유지 |
| partial raw 사용 | 금지. 월별/일별 totalCount 대비 complete가 아닌 raw는 성능검증에 투입하지 않음 |
| 성능 개선 실험 승격 | 불가. 2021~2025 rolling out-of-year 검증에 필요한 완전월/완전연도 coverage가 없음 |

## 5. 해석

- 이번 실패는 “PPS 자료가 건설업 설명력이 없다”는 증거가 아니다.
- 현재 증거는 “PPS 계약·공고 raw가 전기간 품질완료 상태가 아니므로 운영 route로 검증하거나 채택할 수 없다”는 뜻이다.
- 부분 raw를 0으로 대체하거나, 부분월만 사용해 WAPE를 계산하면 지역별 coverage 차이를 성능으로 오해하게 된다.
- 건설업 route는 계속 `기본 계층배분 유지 + PPS/건축HUB/정비사업 보조 후보 보관` 상태로 둔다.

## 6. 다음 작업

1. 조달청 API 쿨다운 후 `201610`을 하루 단위로 재시도한다.
2. 429가 계속되면 `numOfRows` 축소, 날짜 범위 `1일→반일` 분할, 호출 간격 장기화 방식으로 별도 long-run collector를 사용한다.
3. 2016Q4부터 3개월 완전성을 확보한 뒤 중복·금액·지역매칭 품질감사를 재실행한다.
4. 2021~2025 중 최소 2개 이상 완전연도가 확보될 때만 건설업 rolling out-of-year route 검증을 다시 수행한다.

## 7. 평가자 사후검토 반영

| 점검항목 | 평가 |
| --- | --- |
| route 미채택 판단 | 타당. 승인·키 업데이트 후에도 계약·공고 모두 429가 재현되어 수집 보류가 맞음 |
| partial raw 제외 | 타당. 페이지 절단·기간 대표성 부족·지역 매칭 bias가 있어 성능검증에 넣으면 안 됨 |
| 다음 요구 | API 제한조건 공식 확인, complete 판정 기준 유지, 안정적 대체 건설업 자료 우선 검토 |
| 문서 주의 | PPS는 `blocked_api_incomplete / partial_complete_months`이며, 전체 건설업 actual 또는 민간건설 활동으로 표현 금지 |

평가자 결론에 따라 Phase254는 성능개선 실험이 아니라 `수집 재시도 및 route gate 유지` 실험으로 기록한다.

## 8. 갱신 산출물

- `reports/partial_statistics_estimation_phase249_pps_contract_collection_audit.md`
- `nationwide/source_coverage_audit_2015_2025.md`
- `nationwide/active_goal_requirement_audit_2015_2025.md`
