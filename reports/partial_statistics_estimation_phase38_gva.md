# Phase 38: 고양시 현행 44개 행정동 산업·월 GVA 재배분

## 결론

Phase 38은 Phase 36의 2015년 39개 동 고정배분을 현행 44개 동의 월별 인허가 신호로 교체했다. 결과는 2021~2023년 **44개 동 × 3개 상위 산업 × 36개월 = 4,752행**이다. 시×산업×월, 구×산업×연, 분기·연간 합계를 동시에 보존한다.

그러나 행정동 GVA actual은 존재하지 않는다. 이 결과는 `행정동 월간 GVA 배분 추정치`이며 공식 통계·관측 GVA가 아니다. 회계 제약 통과는 정확도 증거와 분리한다.

## 실험 설계

1. Phase 36의 고양시×산업×월 총량을 변경하지 않는다.
2. KOSIS 3개 구×산업 사업체·종사자 actual의 평균 비중을 연간 구 마진으로 사용한다.
3. I00·Q00은 동일 산업 인허가 stock, ERS는 R00·S00을 구별 연간 구성비로 결합한다.
4. RAS로 월별 시 총량과 연간 구 마진을 동시에 맞춘 후, 구 내부를 44개 동 월별 프록시로 배분한다.
5. 결합 가중치는 2022년 개발구간에서만 선택하고 2023년 구×산업 actual을 prospective holdout으로 평가한다.

## 2023 Prospective Holdout

선택된 전년도 actual 가중치 α는 **1.00**다. `selected_blend = α×전년도 구 비중 + (1-α)×당해 인허가 비중`이다.

| evaluation_year | split | model | sector_code | mae_pp | correlation |
|---|---|---|---|---|---|
| 2023 | prospective_holdout | uniform | ERS | 5.621195 |  |
| 2023 | prospective_holdout | uniform | I00 | 7.751499 |  |
| 2023 | prospective_holdout | uniform | Q00 | 5.3406 |  |
| 2023 | prospective_holdout | uniform | ALL | 6.237765 |  |
| 2023 | prospective_holdout | proxy_current | ERS | 1.59572 | 0.961016 |
| 2023 | prospective_holdout | proxy_current | I00 | 0.895073 | 0.999069 |
| 2023 | prospective_holdout | proxy_current | Q00 | 3.799042 | 0.858596 |
| 2023 | prospective_holdout | proxy_current | ALL | 2.096612 | 0.926253 |
| 2023 | prospective_holdout | carry_forward | ERS | 0.317038 | 0.999998 |
| 2023 | prospective_holdout | carry_forward | I00 | 0.581537 | 0.997303 |
| 2023 | prospective_holdout | carry_forward | Q00 | 0.252348 | 0.999987 |
| 2023 | prospective_holdout | carry_forward | ALL | 0.383641 | 0.998231 |
| 2023 | prospective_holdout | selected_blend | ERS | 0.317038 | 0.999998 |
| 2023 | prospective_holdout | selected_blend | I00 | 0.581537 | 0.997303 |
| 2023 | prospective_holdout | selected_blend | Q00 | 0.252348 | 0.999987 |
| 2023 | prospective_holdout | selected_blend | ALL | 0.383641 | 0.998231 |

### 가중치 선택 경로

| alpha_previous_actual | evaluation_year | split | mae_pp |
|---|---|---|---|
| 0.0 | 2022 | development | 2.302103 |
| 0.0 | 2023 | heldout | 2.096612 |
| 0.25 | 2022 | development | 1.733695 |
| 0.25 | 2023 | heldout | 1.602748 |
| 0.5 | 2022 | development | 1.179043 |
| 0.5 | 2023 | heldout | 1.108884 |
| 0.75 | 2022 | development | 0.650067 |
| 0.75 | 2023 | heldout | 0.653765 |
| 1.0 | 2022 | development | 0.522062 |
| 1.0 | 2023 | heldout | 0.383641 |

holdout은 구 수준 공간갱신의 외삽력을 평가한다. 최종 산출물은 같은 연도 KOSIS 구 마진에 맞추므로 holdout 결과를 최종 행정동 정확도로 오해하면 안 된다.

## 회계 검증

| scope | cells | max_abs_error |
|---|---|---|
| EMD to gu monthly | 324 | 0.0 |
| gu to city monthly | 108 | 0.0 |
| gu annual KOSIS-derived margin | 27 | 0.0 |
| EMD to city quarter | 36 | 0.0 |

## 공통 프록시 재발 검사

| general_gu | sector_code | year | emd_count | effective_rank | unique_normalized_profiles | all_emd_profiles_identical | mean_pairwise_correlation |
|---|---|---|---|---|---|---|---|
| 덕양구 | ERS | 2021 | 21 | 12 | 21 | False | 0.925657 |
| 덕양구 | ERS | 2022 | 21 | 12 | 21 | False | 0.897977 |
| 덕양구 | ERS | 2023 | 21 | 12 | 21 | False | 0.969774 |
| 덕양구 | I00 | 2021 | 21 | 12 | 21 | False | 0.980572 |
| 덕양구 | I00 | 2022 | 21 | 12 | 21 | False | 0.978211 |
| 덕양구 | I00 | 2023 | 21 | 12 | 21 | False | 0.729323 |
| 덕양구 | Q00 | 2021 | 21 | 12 | 18 | False | 0.839519 |
| 덕양구 | Q00 | 2022 | 21 | 11 | 18 | False | 0.57007 |
| 덕양구 | Q00 | 2023 | 21 | 12 | 18 | False | 0.581938 |
| 일산동구 | ERS | 2021 | 12 | 12 | 12 | False | 0.948682 |
| 일산동구 | ERS | 2022 | 12 | 12 | 12 | False | 0.985696 |
| 일산동구 | ERS | 2023 | 12 | 12 | 12 | False | 0.985715 |
| 일산동구 | I00 | 2021 | 12 | 12 | 12 | False | 0.990202 |
| 일산동구 | I00 | 2022 | 12 | 12 | 12 | False | 0.991529 |
| 일산동구 | I00 | 2023 | 12 | 12 | 12 | False | 0.879052 |
| 일산동구 | Q00 | 2021 | 12 | 10 | 10 | False | 0.916846 |
| 일산동구 | Q00 | 2022 | 12 | 9 | 10 | False | 0.342249 |
| 일산동구 | Q00 | 2023 | 12 | 9 | 9 | False | 0.840456 |
| 일산서구 | ERS | 2021 | 11 | 11 | 11 | False | 0.934103 |
| 일산서구 | ERS | 2022 | 11 | 11 | 11 | False | 0.990906 |
| 일산서구 | ERS | 2023 | 11 | 11 | 11 | False | 0.984647 |
| 일산서구 | I00 | 2021 | 11 | 11 | 11 | False | 0.983372 |
| 일산서구 | I00 | 2022 | 11 | 11 | 11 | False | 0.981252 |
| 일산서구 | I00 | 2023 | 11 | 11 | 11 | False | 0.843901 |
| 일산서구 | Q00 | 2021 | 11 | 9 | 9 | False | 0.451903 |
| 일산서구 | Q00 | 2022 | 11 | 9 | 9 | False | 0.684882 |
| 일산서구 | Q00 | 2023 | 11 | 7 | 8 | False | 0.500621 |

Phase 36의 동일 프로필률은 100%였다. Phase 38의 동일 프로필 그룹률은 **0.0%**다. 산업별·동별 고유 월 신호가 생겼지만, 이것은 actual 정확도 승격이 아니라 상호작용 결손 제거다.

## 산업별 사용 판정

| sector_code | sector_name | source_gate | holdout_mae_pp | output_decision | claim_limit |
|---|---|---|---|---|---|
| I00 | 숙박·음식점 | strong | 0.581537 | primary_allocation | no EMD actual; accounting-consistent estimate only |
| Q00 | 보건·사회복지 | supplementary | 0.252348 | supplementary_allocation | no EMD actual; accounting-consistent estimate only |
| ERS | 예술·여가·개인서비스 | mixed_strong_supplementary | 0.317038 | supplementary_allocation | no EMD actual; accounting-consistent estimate only |

## 한계

- 2021~2023 행정동은 2026년 현행 44개 경계로 소급 표현한다.
- LOCALDATA는 전체 사업체나 매출이 아니라 인허가 대상의 영업 상태다.
- Q00과 ERS의 R00 구성은 보조적 근거다. 세부 업종별 수치 발표보다 상위 묶음과 민감도 범위를 사용한다.
- 2024~2026은 상위 GVA 통제가 없어 경제활력 지수로만 제공하고 GVA로 외삽하지 않는다.

## 재현

```bash
.venv/bin/python scripts/run_partial_statistics_phase38_gva.py
.venv/bin/python scripts/verify_partial_statistics_phase38_gva.py
.venv/bin/pytest -q tests/test_partial_statistics_phase38_gva.py
```
