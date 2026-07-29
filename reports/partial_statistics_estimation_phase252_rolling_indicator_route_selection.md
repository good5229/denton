# Phase252 rolling 활동지표 route 선택 검증

생성시각: 2026-07-29T18:24:09+09:00

## 1. 목적

기존 hard-region no-worse 실험은 목표연도 actual을 보고 셀별로 좋아지는 후보만 채택할 수 있어 운영 채택 근거로는 데이터 유출 위험이 있다. 이번 실험은 17개 시도 전체에 대해 목표연도 `y` 이전 연도만으로 route를 선택하고, 선택된 route만 `y`에 적용하는 rolling holdout 검증이다.

## 2. 설계

| 항목 | 내용 |
| --- | --- |
| 검증 범위 | 17개 시도, 2021~2025 시도×업종×운영시점 |
| holdout 성능 집계 | 2022~2025, 2021년은 prior training 부재로 선택 성능에서 제외 |
| 후보 지표 | 제조업 생산지수, 시도별 서비스업생산지수, 건설수주 원지표, 건설수주 BOK식 12·24분기 분산 |
| 후보 예측식 | 전년도 official annual × 목표연도 누적 지표 / 전년도 동일누적 지표 |
| route 선택 | `track×activity×available_quarters×holdout_year`별로 holdout 이전 연도만 사용 |
| strict 채택 | training WAPE 개선, 10% 초과 셀 비증가, 20% 초과 셀 비증가, max APE 비악화 |
| 최소 훈련기간 | 목표연도 이전 2개년 이상. 2022년은 2021년 1개년만 있어 route 채택 금지 |
| practical 후보 | p95 APE 비악화와 max APE +5%p 이내까지는 후보로 기록하되 적용하지 않음 |

## 2.1 누수 방지 감사

| 점검항목 | 판정 |
| --- | --- |
| 후보식의 금액 기준 | `basis_year = target_year - 1`의 official annual만 사용 |
| target-year official annual | 후보 예측값 계산에는 미사용, 선택 후 holdout 평가와 merge 검산에만 사용 |
| route 선택 단위 | `track×activity×available_quarters×holdout_year`; 특정 시도 holdout 결과를 보고 route를 바꾸지 않음 |
| 실패 route 기록 | `phase252_route_training_gate.csv`에 strict/practical 통과·탈락 사유 전체 저장 |
| 지표 공표시점 | historical release calendar lock 미적용. 따라서 Q+1개월 strict 속보가 아니라 최신 빈티지 공개지표 기반 rolling holdout으로 제한 |

## 3. 전체 운영시점별 holdout 결과

| 트랙 | 사용분기수 | 운영시점 | 검증행 | 기준WAPE_pct | rolling_route_WAPE_pct | 변화_pp | 기준_10pct초과 | route_10pct초과 | 기준_20pct초과 | route_20pct초과 | 기준최대APE_pct | route최대APE_pct | route적용행 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 1 | 1분기+1개월 | 1,020 | 2.532 | 2.568 | 0.036 | 59 | 61 | 9 | 9 | 31.714 | 31.714 | 17 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 1,020 | 2.019 | 2.026 | 0.007 | 38 | 41 | 6 | 6 | 28.495 | 28.495 | 17 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 1,020 | 1.815 | 1.815 | 0.000 | 36 | 36 | 6 | 6 | 26.439 | 26.439 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 1,020 | 1.668 | 1.668 | 0.000 | 37 | 37 | 7 | 7 | 26.190 | 26.190 | 0 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 1,020 | 3.119 | 3.155 | 0.036 | 110 | 112 | 21 | 21 | 46.935 | 46.935 | 17 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 1,020 | 2.655 | 2.663 | 0.007 | 89 | 92 | 16 | 16 | 39.443 | 39.443 | 17 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 1,020 | 2.479 | 2.479 | 0.000 | 84 | 84 | 13 | 13 | 41.202 | 41.202 | 0 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 1,020 | 2.336 | 2.336 | 0.000 | 84 | 84 | 14 | 14 | 42.106 | 42.106 | 0 |

## 4. 개선 상위 업종·운영시점

| 트랙 | 업종 | 사용분기수 | 검증행 | 기준WAPE_pct | route_WAPE_pct | 변화_pp | 기준_10pct초과 | route_10pct초과 | baseline_over20_cells | rolling_over20_cells | 기준최대APE_pct | route최대APE_pct | route적용행 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 교육 서비스업 | 4 | 68 | 0.792 | 0.792 | 0.000 | 0 | 0 | 0 | 0 | 4.338 | 4.338 | 0 |
| prior_year_province_anchor | 공공 행정, 국방·사회보장 | 4 | 68 | 0.822 | 0.822 | 0.000 | 0 | 0 | 0 | 0 | 5.585 | 5.585 | 0 |
| prior_year_province_anchor | 교육 서비스업 | 3 | 68 | 0.822 | 0.822 | 0.000 | 0 | 0 | 0 | 0 | 4.471 | 4.471 | 0 |
| prior_year_province_anchor | 공공 행정, 국방·사회보장 | 3 | 68 | 0.832 | 0.832 | 0.000 | 0 | 0 | 0 | 0 | 5.556 | 5.556 | 0 |
| prior_year_province_anchor | 서비스업 | 4 | 68 | 0.836 | 0.836 | 0.000 | 0 | 0 | 0 | 0 | 7.047 | 7.047 | 0 |
| prior_year_province_anchor | 공공 행정, 국방·사회보장 | 2 | 68 | 0.848 | 0.848 | 0.000 | 0 | 0 | 0 | 0 | 5.577 | 5.577 | 0 |
| prior_year_province_anchor | 공공 행정, 국방·사회보장 | 1 | 68 | 0.849 | 0.849 | 0.000 | 0 | 0 | 0 | 0 | 5.876 | 5.876 | 0 |
| prior_year_province_anchor | 교육 서비스업 | 2 | 68 | 0.895 | 0.895 | 0.000 | 0 | 0 | 0 | 0 | 4.806 | 4.806 | 0 |
| prior_year_province_anchor | 교육 서비스업 | 1 | 68 | 0.940 | 0.940 | 0.000 | 0 | 0 | 0 | 0 | 4.631 | 4.631 | 0 |
| recursive_no_target_actual | 교육 서비스업 | 4 | 68 | 0.941 | 0.941 | 0.000 | 0 | 0 | 0 | 0 | 6.822 | 6.822 | 0 |
| recursive_no_target_actual | 교육 서비스업 | 3 | 68 | 0.964 | 0.964 | 0.000 | 0 | 0 | 0 | 0 | 6.951 | 6.951 | 0 |
| recursive_no_target_actual | 교육 서비스업 | 2 | 68 | 1.022 | 1.022 | 0.000 | 0 | 0 | 0 | 0 | 7.278 | 7.278 | 0 |
| prior_year_province_anchor | 서비스업 | 3 | 68 | 1.026 | 1.026 | 0.000 | 0 | 0 | 0 | 0 | 6.681 | 6.681 | 0 |
| recursive_no_target_actual | 교육 서비스업 | 1 | 68 | 1.076 | 1.076 | 0.000 | 0 | 0 | 0 | 0 | 7.107 | 7.107 | 0 |
| prior_year_province_anchor | 도매 및 소매업 | 4 | 68 | 1.087 | 1.087 | 0.000 | 0 | 0 | 0 | 0 | 7.258 | 7.258 | 0 |
| recursive_no_target_actual | 서비스업 | 4 | 68 | 1.112 | 1.112 | 0.000 | 0 | 0 | 0 | 0 | 7.047 | 7.047 | 0 |
| recursive_no_target_actual | 공공 행정, 국방·사회보장 | 4 | 68 | 1.119 | 1.119 | 0.000 | 0 | 0 | 0 | 0 | 5.585 | 5.585 | 0 |
| recursive_no_target_actual | 공공 행정, 국방·사회보장 | 2 | 68 | 1.122 | 1.122 | 0.000 | 0 | 0 | 0 | 0 | 5.577 | 5.577 | 0 |
| recursive_no_target_actual | 공공 행정, 국방·사회보장 | 3 | 68 | 1.132 | 1.132 | 0.000 | 0 | 0 | 0 | 0 | 5.556 | 5.556 | 0 |
| recursive_no_target_actual | 공공 행정, 국방·사회보장 | 1 | 68 | 1.159 | 1.159 | 0.000 | 0 | 0 | 0 | 0 | 5.876 | 5.876 | 0 |

## 5. 악화 상위 업종·운영시점

| 트랙 | 업종 | 사용분기수 | 검증행 | 기준WAPE_pct | route_WAPE_pct | 변화_pp | 기준_10pct초과 | route_10pct초과 | baseline_over20_cells | rolling_over20_cells | 기준최대APE_pct | route최대APE_pct | route적용행 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 사업서비스업 | 1 | 68 | 2.187 | 2.950 | 0.763 | 3 | 5 | 0 | 0 | 12.692 | 12.692 | 17 |
| recursive_no_target_actual | 사업서비스업 | 1 | 68 | 2.632 | 3.395 | 0.763 | 4 | 6 | 0 | 0 | 14.988 | 14.988 | 17 |
| prior_year_province_anchor | 숙박 및 음식점업 | 2 | 68 | 3.338 | 3.878 | 0.540 | 3 | 6 | 0 | 0 | 12.032 | 16.640 | 17 |
| recursive_no_target_actual | 숙박 및 음식점업 | 2 | 68 | 4.515 | 5.054 | 0.540 | 4 | 7 | 0 | 0 | 12.032 | 16.640 | 17 |
| recursive_no_target_actual | 운수 및 창고업 | 1 | 68 | 10.450 | 10.450 | 0.000 | 22 | 22 | 7 | 7 | 46.935 | 46.935 | 0 |
| recursive_no_target_actual | 운수 및 창고업 | 2 | 68 | 9.526 | 9.526 | 0.000 | 20 | 20 | 6 | 6 | 39.443 | 39.443 | 0 |
| recursive_no_target_actual | 운수 및 창고업 | 3 | 68 | 9.449 | 9.449 | 0.000 | 22 | 22 | 5 | 5 | 37.739 | 37.739 | 0 |
| recursive_no_target_actual | 운수 및 창고업 | 4 | 68 | 9.411 | 9.411 | 0.000 | 21 | 21 | 5 | 5 | 36.098 | 36.098 | 0 |
| recursive_no_target_actual | 건설업 | 1 | 68 | 9.079 | 9.079 | 0.000 | 25 | 25 | 6 | 6 | 37.219 | 37.219 | 0 |
| recursive_no_target_actual | 건설업 | 2 | 68 | 8.883 | 8.883 | 0.000 | 27 | 27 | 6 | 6 | 38.894 | 38.894 | 0 |
| recursive_no_target_actual | 건설업 | 3 | 68 | 8.787 | 8.787 | 0.000 | 26 | 26 | 4 | 4 | 41.202 | 41.202 | 0 |
| recursive_no_target_actual | 건설업 | 4 | 68 | 8.708 | 8.708 | 0.000 | 29 | 29 | 5 | 5 | 42.106 | 42.106 | 0 |
| recursive_no_target_actual | 숙박 및 음식점업 | 1 | 68 | 7.634 | 7.634 | 0.000 | 18 | 18 | 3 | 3 | 22.424 | 22.424 | 0 |
| prior_year_province_anchor | 운수 및 창고업 | 1 | 68 | 6.722 | 6.722 | 0.000 | 11 | 11 | 2 | 2 | 25.852 | 25.852 | 0 |
| prior_year_province_anchor | 숙박 및 음식점업 | 1 | 68 | 6.617 | 6.617 | 0.000 | 17 | 17 | 3 | 3 | 22.424 | 22.424 | 0 |
| prior_year_province_anchor | 건설업 | 1 | 68 | 6.332 | 6.332 | 0.000 | 14 | 14 | 3 | 3 | 31.714 | 31.714 | 0 |
| prior_year_province_anchor | 건설업 | 2 | 68 | 5.866 | 5.866 | 0.000 | 13 | 13 | 2 | 2 | 28.495 | 28.495 | 0 |
| prior_year_province_anchor | 건설업 | 3 | 68 | 5.630 | 5.630 | 0.000 | 13 | 13 | 2 | 2 | 25.176 | 25.176 | 0 |
| prior_year_province_anchor | 건설업 | 4 | 68 | 5.553 | 5.553 | 0.000 | 15 | 15 | 3 | 3 | 23.363 | 23.363 | 0 |
| prior_year_province_anchor | 운수 및 창고업 | 2 | 68 | 5.391 | 5.391 | 0.000 | 11 | 11 | 3 | 3 | 25.600 | 25.600 | 0 |

## 6. 선택된 strict route

| 트랙 | 업종 | 사용분기수 | 평가연도 | 선택route | 선택판정 | 훈련WAPE개선_pp |
| --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 사업서비스업 | 1 | 2,023 | regional_service_production_index_M_N | strict_pass | -0.419 |
| prior_year_province_anchor | 숙박 및 음식점업 | 2 | 2,023 | regional_service_production_index_I | strict_pass | -0.411 |
| recursive_no_target_actual | 사업서비스업 | 1 | 2,023 | regional_service_production_index_M_N | strict_pass | -0.419 |
| recursive_no_target_actual | 숙박 및 음식점업 | 2 | 2,023 | regional_service_production_index_I | strict_pass | -0.411 |

## 7. Gate 탈락·후보 현황

| strict통과 | practical후보 | 판정사유 | route평가건수 |
| --- | --- | --- | --- |
| True | True | strict_pass | 4 |
| False | False | wape_not_improved+over10_worse+over20_worse+max_ape_worse | 128 |
| False | False | too_few_training_years | 112 |
| False | False | wape_not_improved+max_ape_worse | 70 |
| False | False | wape_not_improved+over10_worse+max_ape_worse | 51 |
| False | False | wape_not_improved | 36 |
| False | False | wape_not_improved+over10_worse | 28 |
| False | False | wape_not_improved+over20_worse+max_ape_worse | 6 |
| False | False | over10_worse+max_ape_worse | 5 |
| False | False | over10_worse | 3 |
| False | False | max_ape_worse | 2 |
| False | False | over10_worse+over20_worse+max_ape_worse | 1 |
| False | False | wape_not_improved+over10_worse+over20_worse | 1 |
| False | False | wape_not_improved+over20_worse | 1 |

### practical only 후보

_해당 없음_

## 8. 해석

- 운영 판정: `reject_for_operational_adoption`.
- strict training gate만으로도 holdout 전체 WAPE 또는 10% 초과 셀이 악화되어, Phase252 route는 현재 운영 산출물에 반영하지 않는다.
- 본 실험은 목표연도 actual을 route 선택에 사용하지 않는 rolling holdout 구조다.
- 각 목표연도 `y`의 route는 `y` 이전 연도 성과만으로 선택하고, `y` actual은 선택 후 사후 평가에만 사용한다.
- 기존 hard-region no-worse 선택은 목표연도 actual을 셀별 채택 판단에 사용할 수 있으므로 운영 채택 근거가 아니라 탐색적 후보 발굴 결과로만 해석한다.
- 전국·시도 지표는 시군구 공간배분 근거가 아니라 시도×업종 시간경로 후보로만 사용한다.
- Q+1개월 속보 성과로 표현하려면 각 후보 지표의 공표시점 vintage lock이 추가로 필요하다.
- route가 선택되지 않은 업종·운영시점은 성능개선 실패가 아니라 baseline 유지가 더 안전하다는 판정이다.
- 이번 결과는 공공 활동지표가 유용하지 않다는 뜻이 아니라, 현재의 `track×activity×available_quarters` 단위 전역 route 선택 규칙으로는 holdout 안정성이 부족하다는 뜻이다.

## 9. 산출물

- `nationwide/outputs/phase252_candidate_detail.csv`
- `nationwide/outputs/phase252_route_training_gate.csv`
- `nationwide/outputs/phase252_route_selection_by_holdout.csv`
- `nationwide/outputs/phase252_rolling_indicator_route_detail.csv`
- `nationwide/outputs/phase252_summary_by_track_quarter.csv`
- `nationwide/outputs/phase252_summary_by_activity.csv`
- `nationwide/outputs/phase252_summary_by_year.csv`
