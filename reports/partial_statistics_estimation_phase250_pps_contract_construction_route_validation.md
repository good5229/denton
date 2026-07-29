# Phase250 조달청 계약정보 기반 건설업 route 검증

생성시각: 2026-07-29T13:39:41+09:00

## 1. 입력 상태

- 사용 월 수: 21
- 계약행 수: 613,790
- 지역매칭 신호행: 15,036

이 스크립트는 complete 월만 사용한다. 2015~2025 전량 수집 전에는 결과가 부분 검증이라는 점을 유지한다.

## 2. 후보 성능 상위

| scenario | signal_type | alpha | rows | actual_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | over20_cells | max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_parent_control | baseline | 0.000 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| start_date_alpha0.005 | start_date | 0.005 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| start_date_alpha0.010 | start_date | 0.010 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| start_date_alpha0.020 | start_date | 0.020 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| start_date_alpha0.030 | start_date | 0.030 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| start_date_alpha0.050 | start_date | 0.050 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| start_date_alpha0.080 | start_date | 0.080 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| start_date_alpha0.100 | start_date | 0.100 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| start_date_alpha0.150 | start_date | 0.150 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| start_date_alpha0.200 | start_date | 0.200 | 607 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 294.569 |
| duration_allocated_alpha0.005 | duration_allocated | 0.005 | 607 | 2,985,125.440 | 581,778.492 | 19.489 | 364 | 223 | 294.569 |
| duration_allocated_alpha0.010 | duration_allocated | 0.010 | 607 | 2,985,125.440 | 583,762.246 | 19.556 | 364 | 225 | 294.569 |
| contract_date_alpha0.005 | contract_date | 0.005 | 607 | 2,985,125.440 | 583,820.782 | 19.558 | 364 | 225 | 294.569 |
| contract_date_alpha0.010 | contract_date | 0.010 | 607 | 2,985,125.440 | 587,966.918 | 19.697 | 363 | 227 | 294.569 |
| duration_allocated_alpha0.020 | duration_allocated | 0.020 | 607 | 2,985,125.440 | 588,783.112 | 19.724 | 368 | 228 | 294.569 |
| duration_allocated_alpha0.030 | duration_allocated | 0.030 | 607 | 2,985,125.440 | 594,239.548 | 19.907 | 367 | 232 | 294.569 |
| contract_date_alpha0.020 | contract_date | 0.020 | 607 | 2,985,125.440 | 596,532.090 | 19.983 | 365 | 228 | 294.569 |
| contract_date_alpha0.030 | contract_date | 0.030 | 607 | 2,985,125.440 | 605,251.895 | 20.276 | 365 | 231 | 294.569 |
| duration_allocated_alpha0.050 | duration_allocated | 0.050 | 607 | 2,985,125.440 | 606,039.687 | 20.302 | 369 | 236 | 472.374 |
| contract_date_alpha0.050 | contract_date | 0.050 | 607 | 2,985,125.440 | 623,561.909 | 20.889 | 367 | 235 | 294.569 |

## 3. Guardrail 통과 후보

_없음_

## 4. Rolling holdout 검증

| scenario | signal_type | alpha | holdout_folds | improved_folds | mean_baseline_wape_pct | mean_holdout_wape_pct | mean_wape_improvement_pctp | max_holdout_wape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| start_date_alpha0.200 | start_date | 0.200 | 3 | 1 | 19.797 | 19.797 | 0.000 | 23.703 |
| start_date_alpha0.005 | start_date | 0.005 | 3 | 1 | 19.797 | 19.797 | 0.000 | 23.703 |
| start_date_alpha0.150 | start_date | 0.150 | 3 | 1 | 19.797 | 19.797 | 0.000 | 23.703 |
| start_date_alpha0.100 | start_date | 0.100 | 3 | 1 | 19.797 | 19.797 | 0.000 | 23.703 |
| start_date_alpha0.080 | start_date | 0.080 | 3 | 1 | 19.797 | 19.797 | 0.000 | 23.703 |
| start_date_alpha0.050 | start_date | 0.050 | 3 | 1 | 19.797 | 19.797 | 0.000 | 23.703 |
| start_date_alpha0.030 | start_date | 0.030 | 3 | 1 | 19.797 | 19.797 | 0.000 | 23.703 |
| start_date_alpha0.020 | start_date | 0.020 | 3 | 1 | 19.797 | 19.797 | 0.000 | 23.703 |
| start_date_alpha0.010 | start_date | 0.010 | 3 | 1 | 19.797 | 19.797 | 0.000 | 23.703 |
| duration_allocated_alpha0.005 | duration_allocated | 0.005 | 3 | 1 | 19.797 | 19.852 | -0.055 | 23.703 |
| duration_allocated_alpha0.010 | duration_allocated | 0.010 | 3 | 1 | 19.797 | 19.912 | -0.116 | 23.703 |
| contract_date_alpha0.005 | contract_date | 0.005 | 3 | 0 | 19.797 | 19.914 | -0.117 | 23.703 |
| contract_date_alpha0.010 | contract_date | 0.010 | 3 | 0 | 19.797 | 20.040 | -0.243 | 23.703 |
| duration_allocated_alpha0.020 | duration_allocated | 0.020 | 3 | 1 | 19.797 | 20.066 | -0.270 | 23.703 |
| duration_allocated_alpha0.030 | duration_allocated | 0.030 | 3 | 1 | 19.797 | 20.234 | -0.437 | 23.703 |
| contract_date_alpha0.020 | contract_date | 0.020 | 3 | 0 | 19.797 | 20.301 | -0.505 | 23.703 |
| contract_date_alpha0.030 | contract_date | 0.030 | 3 | 0 | 19.797 | 20.567 | -0.771 | 23.703 |
| duration_allocated_alpha0.050 | duration_allocated | 0.050 | 3 | 1 | 19.797 | 20.595 | -0.799 | 23.703 |
| contract_date_alpha0.050 | contract_date | 0.050 | 3 | 0 | 19.797 | 21.126 | -1.329 | 24.309 |
| duration_allocated_alpha0.080 | duration_allocated | 0.080 | 3 | 1 | 19.797 | 21.249 | -1.452 | 23.703 |

## 5. 월·분기 추정 산출물

안전 후보가 있을 때 `phase250_selected_sigungu_month_estimates.csv`, `phase250_selected_sigungu_quarter_estimates.csv`를 생성한다. 연간 검증 가능한 GVA를 먼저 통과한 후보만 월·분기로 배분하며, city-year 신호가 없으면 연간 합 보존을 위해 균등 12개월 fallback을 명시적으로 적용한다.

## 6. 판정

전량 수집 완료 후 `contract_date`, `start_date`, `duration_allocated` 세 기준을 비교해 운영 route를 선택한다. 본모형 채택은 전체 WAPE 개선, over10/over20 셀 비증가, max APE 비악화, rolling holdout 평균 개선을 동시에 요구한다. 현재 산출값은 수집 완료월 기준의 중간 점검값이다.
