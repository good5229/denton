# Phase187 제조업 산업생산지수 정밀 감사

## 결론

사용자 지적이 맞다. 제조업 부가가치 추정에서 **광공업생산지수/제조업 산업생산지수는 핵심 시간변화 지표**다. 기존 작업을 다시 확인한 결과, 이 지표는 Phase39의 고양시 제조업 월별 총부가가치 시간배분에는 사용됐다. 그러나 Phase186의 “제조업 취약 중분류 개선 후보 선별”에서는 산업생산지수를 별도 후보로 감사하지 않았고, 이 부분은 **범위 누락**이다.

정확한 판정은 다음과 같다.

- **제대로 된 부분**: 고양시 제조업 월별 GVA 경로는 경기도 제조업 산업생산지수와 고양시 산업용 전력량을 결합해 만들었고, 월 합계는 분기 제조업 GVA 통제총량과 일치한다. 최대 분기 합계 오차는 `8.73115e-10`로 사실상 0이다.
- **부족한 부분**: 중분류별 구조 개선 실험에서는 산업생산지수를 별도 후보로 비교하지 않았다. 또한 세부 생산지수는 전체 KSIC 중분류를 덮지 못해 대부분 중분류가 광역 제조업 공통 월 경로를 공유한다.
- **속보성 주의**: 현재 로컬에는 최신 스냅샷과 최신 갱신일 근거만 있고, 각 과거 분기별 실제 공표일 장부가 없다. 따라서 “예측시점에 알 수 있었던 값만 사용”하는 속보성 검증에는 historical vintage 보강이 필요하다.
- **Phase186 오해 정정**: Phase186에서 leakage-risk로 둔 것은 산업생산지수가 아니라 2023년 제조업 city×middle 부가가치형 지표다. 그 판정은 유지한다.

## 원천 자료 커버리지

| source_file | role | exists | rows | table_id | table_name | period_min | period_max | period_count | region_count | region_examples | industry_count | industry_examples | unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index.csv | 2019~2023 시도×제조업 광공업생산지수 원천 | True | 360 | DT_1F02001 | 시도/산업별 광공업생산지수(2020＝100) | 2019Q1 | 2023Q4 | 20 | 18 | 전국, 서울특별시, 부산광역시, 대구광역시, 인천광역시, 광주광역시 | 1 | c2_nm: 제조업 | 2020＝100 |
| rolling_mining_manufacturing_production_index.csv | 2015~2025 확장 시도×제조업 광공업생산지수 원천 | True | 792 | DT_1F02001 | 시도/산업별 광공업생산지수(2020＝100) | 2015Q1 | 2025Q4 | 44 | 18 | 전국, 서울특별시, 부산광역시, 대구광역시, 인천광역시, 광주광역시 | 1 | c2_nm: 제조업 | 2020＝100 |
| partial_stats_phase39_manufacturing_middle_production_index.csv | 전국 일부 제조업 세부 광공업생산지수 원천 | True | 660 | DT_1F02011 | 기본분류 일부항목 제외 광공업생산지수(2020＝100) | 2020Q1 | 2024Q4 | 20 | 0 | 전국 세부항목형 | 6 | c1_nm: 총지수, 광업 및 제조업, 제조업, 사무회계·통신기기·반도체, 영상음향, 반도체 및 부품 | 2020＝100 |

## 기존 실험 사용 감사

| check_item | verdict | evidence | rows | period_min | period_max | non_null_production_index | non_null_industrial_kwh | non_null_indicator | max_abs_error_won_or_source_unit | mean_abs_error_won_or_source_unit | broad_middle_code_count | detailed_middle_code_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 제조업 월별 총부가가치 시간배분 | PASS | 경기도 제조업 광공업생산지수와 고양시 산업용 전력을 결합한 indicator가 존재 | 36 | 2021-01 | 2023-12 | 36.0 | 36.0 | 36.0 |  |  |  |  |
| 분기 통제총량 일치성 | PASS | Denton 제약 후 월별 합계가 분기 제조업 GVA 통제총량과 일치 | 12 |  |  |  |  |  | 8.73114913702011e-10 | 3.637978807091713e-10 |  |  |
| 중분류별 월 경로 차별화 | PARTIAL | C26 등 1개 중분류만 세부 생산지수 경로, 18개 중분류는 광역 제조업 공통 경로 사용 | 684 |  |  |  |  |  |  |  | 18.0 | 1.0 |

## 중분류별 월 경로 출처 분포

| monthly_profile_source | rows | middle_code_count | middle_codes |
| --- | --- | --- | --- |
| Gyeonggi manufacturing index + Goyang industrial electricity | 648 | 18 | C10, C13, C14, C15, C16, C17, C18, C20, C21, C22, C23, C25, C27, C28, C29, C30, C32, C33 |
| national semiconductor/components index | 36 | 1 | C26 |

## 누락·유출·공표시점 판정

| audit_item | verdict | evidence | local_check |
| --- | --- | --- | --- |
| Phase186 제조업 후보 선별의 산업생산지수 포함 여부 | FAIL_SCOPE_OMISSION | Phase186은 personal-business indicator와 2023 제조업 부가가치형 지표를 선별했지만 DT_1F02001/DT_1F02011 산업생산지수 후보를 별도 평가하지 않음 | False |
| Phase186에서 leakage-risk 처리한 2023 제조업 지표의 성격 | PASS_CLASSIFICATION | Phase186의 leakage-risk 대상은 산업생산지수가 아니라 2023 city×middle 제조업 부가가치형 지표임. 동일연도 목적변수 구조를 직접 반영할 수 있어 정밀·속보 후보로 엄격 제한한 판정은 타당 | True |
| Phase39 제조업 시간배분의 산업생산지수 사용 | PASS_USED_FOR_TEMPORAL_ALLOCATION | Phase39는 경기도 제조업 광공업생산지수와 고양시 산업용 전력을 결합해 고양시 제조업 월 경로를 만들고 분기 제조업 GVA 통제총량에 맞춤 | True |
| 중분류·소분류 횡단면 추정에서 산업생산지수 단독 사용 가능성 | INSUFFICIENT_ALONE | 시도×제조업 지수는 제조업 전체의 시간 변화에는 강하지만 고양/포항 시군구×중분류 횡단면을 직접 주지 않음. 전국 일부 세부지수도 전체 KSIC 중분류를 덮지 않아 공장·전력·물동량 등 지역 활동자료와 결합해야 함 | True |
| 속보성 예측에서 공표시점 사용 가능성 | PARTIAL_RISK_NEEDS_HISTORICAL_VINTAGE | Phase26에는 DT_1F02001 최신 갱신일과 최신 수록시점만 있고 2019~2023 각 분기별 역사적 공표일 장부는 없음. 따라서 정밀화/회고 분석에는 사용 가능하지만, 1개월 이내 속보성 실험에는 분기별 historical vintage ledger를 보강해야 함 | True |

## 후속 조치

1. Phase186은 “제조업 횡단면 후보 선별”로 명확히 재명명하거나, Phase187 판정을 붙여 산업생산지수 누락을 보정해야 한다.
2. 제조업 속보성 실험에는 DT_1F02001/DT_1F02011의 historical release ledger를 붙여야 한다. 없는 경우에는 “정밀화/회고 지표”로만 사용한다.
3. 중분류·소분류 추정에는 산업생산지수를 단독으로 쓰지 말고, 공장등록·산업용 전력·항만 물동량·조달/계약 등 지역 활동자료와 결합한 gated ensemble로 써야 한다.
4. 포항 제조업에는 경북 제조업 산업생산지수와 포항 산업용 전력/항만 물동량의 결합 경로를 고양 Phase39 방식과 동일하게 추가 점검해야 한다.
