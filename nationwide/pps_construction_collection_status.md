# 조달청 공사공고 전국 수집 상태

생성일: 2026-07-29

## 목적

건설업 시군구 공간배분 개선을 위해 조달청 나라장터 공사공고(`cnstwk`) 전국 raw를 2021~2025년으로 확장 수집하려 했다. 목표는 PPS 공공공사 소재지·금액 신호를 rolling out-of-year 검증에 사용하는 것이다.

## 수집 명령

```bash
.venv/bin/python scripts/collect_phase122_pps_bid_notices.py \
  --start 202101 --end 202512 --ops cnstwk \
  --num-rows 999 --sleep 0.05 --timeout 45 \
  --output-tag nationwide_cnstwk_2021_2025
```

네트워크 샌드박스 DNS 실패 후 escalated 실행으로 재시도했다.

이후 느린 API 응답 때문에 다음 resume 명령을 사용했다.

```bash
.venv/bin/python scripts/collect_phase122_pps_bid_notices.py \
  --start 202104 --end 202512 --ops cnstwk \
  --num-rows 999 --sleep 0.03 --timeout 12 \
  --output-tag nationwide_cnstwk_2021_2025_resume
```

## 현재 raw cache

| 기간 | 전국 raw page | 상태 |
| --- | ---: | --- |
| 202101 | 9 | 수집 완료 |
| 202102 | 13 | 수집 완료 |
| 202103 | 15 | 수집 완료 |
| 202104 | 5 | 불완전, timeout |
| 202105 | 5 | 불완전, timeout |
| 202106 | 7 | 불완전, timeout |
| 202301 | 8 | 기존 cache |

2021년 4~8월은 API timeout이 반복되어 완전 수집하지 못했다.
2023년 2~9월에는 고양·포항 필터 공사공고 cache가 있으나 전국 rolling 검증용 raw로 사용하지 않는다.

## Robust collector 보강

`numRows=999` 응답이 긴 월에서 timeout이 반복되어, 별도 raw 디렉터리와 작은 페이지 크기를 사용하는 collector를 추가했다.

- 스크립트: `nationwide/collect_pps_construction_robust.py`
- raw 디렉터리: `data/raw/phase122_pps_bid_notices_robust`
- 파일명 예시: `cnstwk_202104_n100_0003.json`
- 안전장치: `numRows`를 파일명에 포함해 기존 999행 페이지 cache와 섞이지 않도록 분리
- 추가 옵션: `--start-page`, `--end-page`로 page chunk/resume 가능

2021년 4~7월 robust 수집 결과:

| 기간 | totalCount | 필요 page 수 (`numRows=100`) | 수집 성공 page | 현재 확보 건수 | 남은 page | 현재 판정 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 202104 | 17,438 | 175 | 175 | 17,438 | 0 | 완전월 확보 |
| 202105 | 14,074 | 141 | 141 | 14,074 | 0 | 완전월 확보 |
| 202106 | 16,602 | 167 | 167 | 16,602 | 0 | 완전월 확보 |
| 202107 | 12,322 | 124 | 124 | 12,322 | 0 | 완전월 확보 |
| 202108 | 9,161 | 92 | 5 | 500 | 87 | 불완전, 실험 미사용 |

명령 예시:

```bash
.venv/bin/python nationwide/collect_pps_construction_robust.py \
  --start 202104 --end 202104 --num-rows 100 \
  --timeout 12 --sleep 0.02 --start-page 1 --end-page 20
```

누락 page만 재시도:

```bash
.venv/bin/python nationwide/collect_pps_construction_robust.py \
  --start 202104 --end 202104 --num-rows 100 \
  --timeout 20 --sleep 0.05 --start-page 1 --end-page 2
```

## Robust cache completeness audit

완전성 감사 스크립트:

- `nationwide/audit_pps_robust_completeness.py`

실행 결과:

| 기간 | totalCount | 필요 page | 확보 page | 확보 item | 완전성 |
| --- | ---: | ---: | ---: | ---: | --- |
| 202104 | 17,438 | 175 | 175 | 17,438 | 완전 |
| 202105 | 14,074 | 141 | 141 | 14,074 | 완전 |
| 202106 | 16,602 | 167 | 167 | 16,602 | 완전 |

2026-07-29 15~16시대 재시도에서 2021년 6월 167개 page 전체를 확보했다. 이후 2021년 7월도 124개 page 전체를 확보했다. 따라서 2021년 4~7월은 `numRows=100` robust cache 기준 완전월이며, feasibility audit에 투입할 수 있다. 2021년 8월은 5개 page만 받은 부분월이므로 성능 감사에 투입하지 않는다.

raw 파싱 sanity check:

- 2021년 4월 명령: `.venv/bin/python nationwide/run_pps_construction_nationwide_signal.py --start 202104 --end 202104 --raw-dir data/raw/phase122_pps_bid_notices_robust --output-suffix robust_n100_complete`
- 2021년 Q2 명령: `.venv/bin/python nationwide/run_pps_construction_nationwide_signal.py --start 202104 --end 202106 --raw-dir data/raw/phase122_pps_bid_notices_robust --output-suffix robust_202104_202106_complete`
- 2021년 4월 결과: 전체자료 17,438건 중 시군구 정확 귀속 15,100건, 33,790억원
- 2021년 Q2 결과: 전체자료 48,114건 중 시군구 정확 귀속 40,792건, 107,330억원
- 2021년 7월 결과: 전체자료 12,322건 중 시군구 정확 귀속 10,587건, 32,304억원
- 판정: 파싱·시군구 귀속 정상, 2021년 Q2와 2021년 7월 완전월 신호로 feasibility audit 가능

2021년 4~7월 추가 수집 로그:

| chunk | 결과 |
| --- | --- |
| page 61~100 | 대부분 성공, page 80 timeout |
| page 101~140 | page 101~119 일부 성공, 120~123 timeout 후 중단 |
| page 141~175 | page 141,143~145,147,150~155,157 성공, 일부 timeout 후 중단 |
| 202106 page 1~167 | 여러 차례 timeout 재시도 후 전체 page 확보 |
| 202107 page 1~124 | 전·중·후반 page chunk 병렬 재시도 후 전체 page 확보 |

현재 대표 누락 page:

- 없음

## 2021년 4~7월 완전월 성능 감사

2021년 4월, 5월, 6월, 7월, 1~6월 누적 PPS 신호를 2021년 건설업 시군구 actual에 대해 감사했다.

| 신호 | 기준 WAPE | 최선 WAPE | Guardrail 통과 |
| --- | ---: | ---: | --- |
| 2021년 4월 단독 | 13.415% | 13.365% | 없음 |
| 2021년 1~4월 누적 | 13.415% | 13.296% | 없음 |
| 2021년 5월 단독 | 13.415% | 13.356% | 없음 |
| 2021년 1~5월 누적 | 13.415% | 13.287% | 없음 |
| 2021년 6월 단독 | 13.415% | 13.400% | `기존 share 99% + PPS 공고수 share 1%` |
| 2021년 1~6월 누적 | 13.415% | 13.322% | 없음 |
| 2021년 7월 단독 | 13.415% | 13.415% | 없음 |

해석:

- 4~6월 완전월을 추가해도 PPS 공사공고는 WAPE를 소폭 낮추는 데 그친다.
- 2021년 1~5월 누적 기준 WAPE 최선 후보는 WAPE를 13.415%→13.287%로 낮추지만 10% 초과 셀을 117→120, 20% 초과 셀을 60→61, 최대 APE를 89.249%→105.665%로 악화시켜 채택하지 않는다.
- 2021년 6월 단독 기준 최선 후보는 WAPE 13.415%→13.400%, 10% 초과 셀 117→116, 20% 초과 셀 60→58, 최대 APE 89.249%→88.814%로 모두 개선되어 guardrail을 통과한다.
- 그러나 2021년 1~6월 누적 기준 WAPE 최선 후보는 WAPE 13.415%→13.322%, 20% 초과 셀 60→57로 낮추지만 최대 APE가 89.249%→92.790%로 악화되어 채택하지 않는다.
- 2021년 7월 단독 기준에서는 PPS 혼합 후보가 기준 WAPE보다 낮아지지 않았다. 6월 단독의 통과 결과가 월별로 안정적으로 재현된다고 보기 어렵다.
- 따라서 6월 단독 결과는 PPS가 보조 신호로 의미 있음을 보여주는 근거일 뿐, 운영 route 채택 근거가 아니다.
- 따라서 PPS는 여전히 건설업 공간배분의 단독 route가 아니라 건축HUB·재건축/재개발 자료와 결합할 보조 신호다.

## 현재 가능한 검증

| 검증 | 가능 여부 | 산출물 |
| --- | --- | --- |
| 2023 부분기간 PPS 미세 보정 감사 | 가능 | `construction_pps_sigungu_spatial_audit.md` |
| 2021 Q1 속보형 PPS 감사 | 가능 | `construction_pps_sigungu_spatial_audit_2021q1_flash.md` |
| 2021 4~7월 완전월 추가 감사 | 가능 | `construction_pps_sigungu_spatial_audit_2021m04_flash.md`, `construction_pps_sigungu_spatial_audit_2021m05_flash.md`, `construction_pps_sigungu_spatial_audit_2021m06_flash.md`, `construction_pps_sigungu_spatial_audit_2021m07_flash.md`, `construction_pps_sigungu_spatial_audit_2021m01_m06_flash.md` |
| 2021~2025 rolling out-of-year PPS 검증 | 불가 | 전 기간 raw 불완전. 2021년 4~6월은 완전월이지만 2021년 하반기 이후가 아직 부족 |

## 현재 판정

- 2023 부분기간에서는 `기존 share 98% + PPS 금액 share 2%`가 guardrail을 통과했다.
- 2021 Q1, 4월, 5월, 7월, 1~5월 누적, 1~6월 누적 속보형에서는 WAPE가 일부 낮아져도 10% 초과 셀·20% 초과 셀·최대오차율 중 하나 이상이 악화되거나 기준 WAPE를 넘어서 guardrail 통과 후보가 없었다.
- 2021년 6월 단독은 guardrail 통과 후보가 있었지만, 단일 월 결과이므로 운영 route 채택 근거가 아니라 보조 신호 후보 근거로만 남긴다.
- 따라서 PPS는 아직 운영 route가 아니라 건축HUB·재건축/재개발 자료와 결합할 후보 신호다.

## 다음 수집 제안

1. 조달청 공사공고 API는 월 단위 전량 수집을 유지하되, timeout 발생 월은 페이지 단위 retry/resume manifest를 남기도록 collector를 보강한다.
2. 가능하면 공사공고보다 계약/낙찰 API를 우선한다. 입찰공고보다 계약금액·계약일·공사기간이 GVA 발생시점에 더 가깝다.
3. 2021~2025 전체 PPS가 채워진 뒤에만 과거연도 가중치 선택 → 목표연도 평가 방식의 rolling out-of-year 검증을 수행한다.
