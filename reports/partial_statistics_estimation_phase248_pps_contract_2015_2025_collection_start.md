# Phase248 조달청 계약정보 2015~2025 전국 수집 착수 및 중단 지점

생성일: 2026-07-29

## 1. 목적

건설업 시군구 GVA 추정 성능 개선을 위해 조달청 나라장터 공사 계약정보를 2015년부터 2025년까지 전국 단위로 수집하려 했다.

핵심 이유:

- 기존 BuildingHUB는 민간 건축활동 일부만 설명한다.
- CALS는 도로·하천 중심 공공/SOC 자료다.
- 조달청 계약정보는 공공공사 계약금액·계약일·착공/준공 관련 필드를 전국 단위로 제공하므로, 건설업 시군구 금액격차를 줄일 가능성이 가장 큰 공개자료다.

## 2. 수집기

수집기:

- `nationwide/collect_phase248_pps_contract_incremental.py`

특징:

- 월별 raw JSON 캐시 저장
- 월별 normalized CSV 즉시 저장
- 월별 manifest 즉시 갱신
- 중단 후 재개 가능
- `.env`의 `DATA_GO_KR_DECODING` 사용
- raw/processed 데이터는 `data/` 아래 저장되며 `.gitignore` 대상

주요 산출 경로:

- raw: `data/raw/phase248_pps_contract_incremental/YYYYMM/`
- 월별 CSV: `data/processed/phase248_pps_contract_monthly/pps_contract_YYYYMM.csv`
- manifest: `data/processed/phase248_pps_contract_collection_manifest.csv`
- 시군구×연도 집계: `data/processed/phase248_pps_contract_sigungu_year_201501_201502.csv`
- 시도×연도 집계: `data/processed/phase248_pps_contract_province_year_201501_201502.csv`

## 3. 현재 수집 완료 범위

2026-07-29 13:39 KST 기준 manifest/월별 CSV 재감사 결과:

| 항목 | 값 |
| --- | ---: |
| manifest 대상 월 | 132 |
| `quality_complete=True` 월 | 21 |
| 연간 채택 가능 연도 | 1개년(2015) |
| 확보 행 수 | 613,790 |
| API totalCount 합계 | 910,191 |
| 전체 수집률 | 67.44% |
| complete 월 평균 시도 매칭률 | 87.62% |
| complete 월 평균 시군구 매칭률 | 73.85% |

완전 월:

- 2015년 1~12월
- 2016년 1~9월

연간 GVA 검증에 바로 투입 가능한 최소 조건(12개월 모두 complete)을 만족한 것은 2015년뿐이다.

## 4. 중단 원인

2015~2025 전량 수집을 시작했으나, 일부 월에서 중단/timeout/빈 월별 CSV가 남아 아직 전량 수집 상태가 아니다.

중요한 점:

- 조달청 API 자체 실패가 아니다.
- 공공데이터포털 인증키 실패도 아니다.
- 수집기 로직은 2015년 전체와 2016년 1~9월에서 정상 동작했다.
- 2016년 10월 이후에는 raw page 일부 또는 빈 monthly CSV가 있어 `quality_complete=False`로 분리한다.
- 본분석은 `quality_complete=True` 월만 사용하고, 연간 검증은 12개월 모두 complete인 연도만 채택한다.

## 5. 수집량 추정

확인된 월별 규모:

- 2015-01: 12,590건, 13페이지
- 2015-02: 19,852건, 약 20페이지
- 2021-01: 27,844건, 약 28페이지
- 2021-02: 43,018건, 약 44페이지

`numOfRows=999`가 실질 상한이다. 3,000 이상을 넣으면 오히려 10건만 반환되어 호출 수를 줄일 수 없다.

2015~2025 전체 132개월을 수집하려면 월평균 20~40페이지 기준 약 2,600~5,300회 호출이 필요하다. 따라서 긴 세션 또는 별도 백그라운드 수집 작업으로 돌리는 편이 맞다.

## 6. 다음 재개 명령

외부 API 호출 가능 상태에서 아래 명령으로 재개한다. 기존 complete 월은 건너뛰고, 불완전 월은 `--refresh`로 재수집하는 편이 안전하다.

```bash
.venv/bin/python nationwide/collect_phase248_pps_contract_incremental.py \
  --start 201610 --end 202512 \
  --num-rows 999 --timeout 45 --sleep 0.03 \
  --retries 8 --retry-sleep 45 --stop-on-error --refresh
```

병렬 수집은 가능하지만 API timeout/할당량 리스크가 있으므로 안정화 전에는 `--workers 1`을 기본으로 둔다.

월 전체 쿼리가 특정 page에서 반복 timeout이면 일자 단위 쿼리로 쪼개는 우회 경로를 사용한다.

```bash
.venv/bin/python nationwide/collect_phase248_pps_contract_incremental.py \
  --start 201610 --end 201610 --daily-split \
  --num-rows 999 --timeout 45 --sleep 0.02 \
  --retries 8 --retry-sleep 45 --stop-on-error
```

실패한 refresh가 기존 partial manifest를 0건으로 덮지 않도록, 수집기는 실패 행을 기록할 때 기존 `total_count`, `rows_collected`, `pages_collected`의 더 큰 값을 보존한다.

특정 구간만 재개하려면 예:

```bash
.venv/bin/python nationwide/collect_phase248_pps_contract_incremental.py --start 201503 --end 201512 --sleep 0.02
```

## 7. 분석 계획

전량 수집이 완료되면 다음 순서로 분석한다.

1. phase249로 월별 수집률, raw JSON 수, monthly CSV 존재, 중복 계약번호, 금액 결측/0, 시도·시군구 매칭률을 감사한다.
2. 12개월 모두 `quality_complete=True`인 연도만 연간 GVA 검증에 투입한다.
3. 계약일, 착공일, 착공~준공 기간균등배분 신호를 월·분기·연 단위로 산출한다.
4. 기존 건설업 시군구 기준선과 조달청 계약금액 share를 비교한다.
5. `기존 share + 조달청 계약금액 share` 제한혼합 후보를 생성한다.
6. 2021~2023 actual이 존재하는 구간에서 WAPE, 10% 초과 셀, 20% 초과 셀, 최대 APE를 검증한다.
7. rolling out-of-year 방식으로 후보가 특정 연도에만 의존하지 않는지 검증한다.
8. 기준연도 100이 다른 지수형 입력은 bridge year로 재기준화한 뒤 전국합/시도합 보존을 확인한다.

## 8. 현재 결론

조달청 계약정보는 수집 가능하고 자료 규모도 충분하다. 그러나 현재 확보분은 2015년만 연간 채택 가능하며, 시군구 매칭률도 80~90% 권장 기준보다 낮아 시군구 본모형 채택에는 아직 부족하다.

수집기, 품질 감사, 계약일/착공일/기간배분 검증, rolling guardrail 경로는 마련했다. 외부 호출 가능 상태에서 2016년 10월~2025년 12월 불완전 월을 재수집한 뒤 phase249/phase250을 재실행해야 한다.
