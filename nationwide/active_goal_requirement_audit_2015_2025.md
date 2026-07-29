# 2015~2025 전국 목표 요구사항 감사

생성시각: 2026-07-29T15:04:16+09:00

## 판정 요약

이 문서는 현재 `/goal`의 완료 증명서가 아니라, 남은 요구사항을 숨기지 않기 위한 진행 감사다. 현재 산출물은 `시도·전국 상위 경계 검증`과 `사용자료 coverage/기준연도 감사`까지는 강한 증거가 있으나, `2015~2025 전기간 시군구×업종 직접 actual 검증`은 공표자료 범위상 아직 완료로 볼 수 없다.

## 요구사항별 현재 상태

| requirement | current_status | evidence | next_action |
| --- | --- | --- | --- |
| 2015~2025 사용자료 전체 수집 | partial | 6개 자료군은 2015~2025 직접 coverage, PPS=blocked_api_incomplete, 시군구 GVA actual=2019~2023 | PPS API 쿨다운 후 건설 공사계약 전량 수집; 시군구 actual 공표 공백은 상위 집계검증으로 분리 표기 |
| 기준연도 다른 지수 조정 | satisfied_for_current_local_inputs | coverage audit상 주요 생산·서비스 지수는 2020=100 소급계열, index_base_bridge=metadata_ok | legacy 2015=100 계열 추가 시 bridge-year 재기준화 후 투입 |
| 전국 17개 시도 분기/연간환산 검증 | satisfied | 680개 시도×연도×운영시점 검증행, 전국경계 5개년 | 해석은 최신 빈티지 사후 백테스트로 제한 |
| 2015~2025 장기 시도 안정성 검증 | satisfied_with_initialization_limit | 2016~2025 10개년×17개 시도, Q1 연간환산 WAPE=1.778%, 최대오차율=11.755% | 2015년은 전년도 기준값이 없어 초기화 연도로 표기; 성능 검증은 2016~2025로 유지 |
| 전국 시군구×업종 월별 산출 | partial_bridge_2021_2025 | 2021~2025, 357,240행, 월별 시간경로 적용 84.914%, 분기 재집계 오류셀 0개 | 월별 actual 검증이 아니라 분기 재집계 보존형 bridge로 표기; 2015~2020 시군구 월별 산출은 별도 기준값 필요 |
| 전국 시군구×업종 전기간 직접 actual 검증 | not_satisfied_due_publication_scope | 시군구 actual 로컬 공표범위 2019~2023, 공표 시도 17개 | 공표된 연도는 직접검증, 2024~2025 및 미공표 시도는 시도·전국 상위 actual 집계검증으로 대체 |
| 건설업 직접 활동자료 route 전국 채택 | blocked_by_pps_api_quota | PPS first incomplete=201610, adoptable_years=1 | 429 해제 후 월/일 단위 재개; quality_complete 연도만 rolling 검증에 투입 |
| 과학자/평가자 검증 | latest_monthly_bridge_postaudit_reflected | 월별 bridge 사후평가에서 전국 월별 지표를 공간배분 근거로 오해하지 않도록 indicator_rows_pct 해석 보강 필요 지적 | 후속 실험마다 사전/사후 검증을 반복하고, 자동채택 표현은 rolling gate 통과분으로 제한 |

## 사용자료 coverage 요약

| coverage_status | source_count | rows |
| --- | --- | --- |
| blocked_api_incomplete | 1 | 132 |
| covers_2015_2025 | 6 | 31,700 |
| limited_period | 1 | 148,616 |
| metadata_ok | 1 | 5 |
| partial_by_definition | 4 | 13,769 |
| usable_for_2021_2025_backtest_with_limits | 5 | 106,674 |

## 시군구 annual actual 공표 범위

| year | province_count | sigungu_count | rows |
| --- | --- | --- | --- |
| 2019 | 9 | 152 | 1,976 |
| 2020 | 17 | 229 | 2,977 |
| 2021 | 17 | 229 | 2,977 |
| 2022 | 17 | 229 | 2,977 |
| 2023 | 11 | 149 | 1,937 |

## 시도 분기/연간환산 검증 요약

| track | available_quarters | operating_label | validation_rows | annualized_wape_pct | max_ape_pct |
| --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 1 | 1분기+1개월 | 85 | 1.643 | 6.654 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 85 | 1.139 | 5.361 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 85 | 1.054 | 4.749 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 85 | 1.073 | 4.076 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 85 | 1.894 | 9.384 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 85 | 1.402 | 8.073 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 85 | 1.304 | 7.453 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 85 | 1.321 | 6.763 |

## 전국 GDP/GRDP 경계 요약

| track | years | national_boundary_wape_mean_pct | national_boundary_wape_max_pct |
| --- | --- | --- | --- |
| prior_year_province_anchor | 5 | 0.059 | 0.127 |
| recursive_no_target_actual | 5 | 0.042 | 0.069 |

## 업종별 잔여 오차 상위

| track | activity | rows | activity_wape_pct | max_ape_pct | over_10pct_cells |
| --- | --- | --- | --- | --- | --- |
| recursive_no_target_actual | 운수 및 창고업 | 340 | 9.500 | 45.988 | 100 |
| recursive_no_target_actual | 건설업 | 340 | 8.264 | 48.196 | 120 |
| prior_year_province_anchor | 운수 및 창고업 | 340 | 6.125 | 43.262 | 59 |
| prior_year_province_anchor | 건설업 | 340 | 5.827 | 35.104 | 76 |
| recursive_no_target_actual | 광업, 제조업 | 340 | 4.636 | 22.407 | 46 |
| recursive_no_target_actual | 숙박 및 음식점업 | 340 | 4.463 | 23.873 | 27 |
| recursive_no_target_actual | 문화 및 기타서비스업 | 340 | 4.289 | 22.862 | 46 |
| prior_year_province_anchor | 문화 및 기타서비스업 | 340 | 4.132 | 22.862 | 36 |
| prior_year_province_anchor | 광업, 제조업 | 340 | 3.716 | 15.089 | 20 |
| recursive_no_target_actual | 기타산업 및 순생산물세 | 340 | 3.623 | 26.641 | 42 |
| prior_year_province_anchor | 기타산업 및 순생산물세 | 340 | 3.583 | 20.454 | 42 |
| prior_year_province_anchor | 숙박 및 음식점업 | 340 | 3.492 | 18.088 | 24 |

## 운영 결론

- 현 상태는 `전국 17개 시도 총량 모니터링`에는 사용 가능한 후보 체계다.
- `시군구×업종`은 공표연도 직접검증과 상위 집계검증을 병행해야 하며, 2015~2025 전기간 직접검증으로 표현하면 안 된다.
- 건설업은 PPS 전량 수집과 품질게이트가 끝나기 전에는 전국 route로 채택하지 않는다.
- 활동지표 route는 업종별 잔여오차 축소 후보지만, 자동채택이 아니라 rolling out-of-year gate 통과분만 채택한다.

## 산출물

- `nationwide/outputs/active_goal_requirement_audit_2015_2025.csv`
- `nationwide/outputs/active_goal_requirement_source_counts.csv`
- `nationwide/outputs/active_goal_sigungu_actual_publication_matrix.csv`
- `nationwide/outputs/active_goal_sido_validation_summary.csv`
- `nationwide/outputs/active_goal_national_boundary_summary.csv`
- `nationwide/outputs/active_goal_activity_validation_summary.csv`
