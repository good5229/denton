# Partial Statistics Estimation Phase 35 - Free Interaction Proxies

## 1. 결론

무료 공식자료만으로 Phase 34의 `공통 사업체 프록시 동일 적용` 결함은 부분적으로 해소됐다. 한전 자료는 시군구×KSIC 중분류×월을 원자료에서 동시에 관측하므로, 2023Q1 지원 셀의 월별 중분류 프로필은 더 이상 rank one이 아니다. 다만 공개 파일은 2023Q1·2024Q1·2025Q2의 세 분기만 담고 공표도 각 기준분기 종료 뒤이므로, 2021-2023 전체 시군구×중분류×분기 GVA를 검증·생산할 정도의 연속 패널은 아니다.

국세청 자료는 2021-2023의 36개월 연속 시군구×100대 생활업종 상호작용을 제공하며 공통 프록시 결함을 통과한다. 그러나 100대 생활업종은 KSIC 중분류가 아니므로 임의 매핑하지 않고 서비스 활동 진단용 별도 제품으로 유지했다.

## 2. 무료 원자료와 역할

| source_id | source_family | cost | reference_period_min | reference_period_max | release_date | rows | classification | role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kepco_industry_2023 | KEPCO electricity | free | 2023-01 | 2023-03 | 2023-08-16 | 516787 | KSIC broad and middle | native sigungu x middle-industry x month interaction proxy |
| kepco_industry_2024 | KEPCO electricity | free | 2024-01 | 2024-03 | 2024-08-06 | 550020 | KSIC broad and middle | native sigungu x middle-industry x month interaction proxy |
| kepco_industry_2025 | KEPCO electricity | free | 2025-04 | 2025-06 | 2025-11-17 | 554748 | KSIC broad and middle | native sigungu x middle-industry x month interaction proxy |
| nts_lifestyle_monthly_2021_2023 | National Tax Service business registry | free | 2021-01 | 2023-12 | monthly vintage-specific | 740919 | NTS 100 lifestyle industries (122 labels across revisions) | native sigungu x custom-industry x month interaction diagnostic |

유료 카드 자료는 수집·사용하지 않았다. 한전과 국세청 파일은 공개 파일 다운로드 경로로 수집했으며 API 키가 필요하지 않았다.

## 3. 상호작용·rank 감사

| source | audit_id | value | numerator | denominator | status | note |
| --- | --- | --- | --- | --- | --- | --- |
| KEPCO KSIC middle electricity | median_effective_temporal_rank | 3.0 | 422 | 422 | pass_interaction | three months per published vintage; exact KSIC-middle interaction but not a full multi-quarter panel |
| KEPCO KSIC middle electricity | all_industries_identical_profile_group_rate | 0.0 | 0 | 422 | pass_no_common_proxy | three months per published vintage; exact KSIC-middle interaction but not a full multi-quarter panel |
| KEPCO-joined Phase34 candidate | all_joined_industries_identical_profile_group_rate | 0.0 | 0 | 38 | pass_no_common_proxy | direct test of the Phase34 common-industry-proxy defect after joining KEPCO |
| NTS 100 lifestyle industries | median_effective_temporal_rank | 12.0 | 651 | 651 | pass_interaction | native custom lifestyle-industry classification; diagnostic only, not forced into KSIC |
| NTS 100 lifestyle industries | all_industries_identical_profile_group_rate | 0.0 | 0 | 651 | pass_no_common_proxy | native custom lifestyle-industry classification; diagnostic only, not forced into KSIC |

Phase 34에서 중분류별 프로필 동일률은 100%, 중앙 유효 rank는 1이었다. Phase 35는 실제 지역×산업×월 전력자료를 붙여 이 결함이 단순 정규화나 라벨 복제로 가려지지 않았는지 다시 계산했다.

## 4. KEPCO 결합 지원 범위

| parent_cells | parent_cells_with_support | median_middle_count_coverage | median_middle_gva_support_rate | median_observed_legal_dong_rate |
| --- | --- | --- | --- | --- |
| 61 | 47 | 0.6666666666666666 | 0.8642730943967692 | 0.26666666666666666 |

`5호미만제거` 행은 0으로 대체하지 않았다. 전력 판매량이 공개된 법정동만 합산하고, 각 셀의 관측 법정동 비율과 지원 GVA 비율을 함께 내보냈다. 따라서 결과는 완전관측 GVA가 아니라 suppression-aware 부분지원 월간 proxy allocation이다.

## 5. 공표시차·누수 감사

| NTS_months | median_release_lag_days | max_release_lag_days | available_by_reference_month_end | KEPCO_2023_release_used | KEPCO_2023_available_by_2023Q1_end |
| --- | --- | --- | --- | --- | --- |
| 36 | 67.5 | 271 | 0 | 2023-08-16 | N |

한전 2023Q1 자료는 2023-08-16 수정 빈티지이므로 2023Q1 실시간 추정에는 사용할 수 없다. 국세청도 기준월 말에 사용 가능했던 빈티지가 없어 contemporaneous nowcast 입력으로 backdate하지 않았다.

## 6. 정합성과 negative control

지원되는 467개 중분류×분기 셀의 월 합은 원래 Phase 34 분기 중분류 배분값과 모두 일치했다. 하지만 산업 프로필 순열 control도 정합을 통과하므로 정합성은 산업 의미나 GVA 정확도의 증거가 아니다.

| control_id | max_industry_quarter_share_error | conservation_still_passes | semantic_alignment_destroyed | interpretation |
| --- | --- | --- | --- | --- |
| within_month_industry_profile_permutation | 1.1102230246251565e-16 | Y | Y | accounting conservation still cannot validate whether a temporal profile belongs to the labeled industry |

## 7. 엄격 검증에서 발견한 추가 이슈

1. 기존 `sigungu_code` 중 일부는 전국 유일 코드가 아니라 시도 내부 코드다. 시군구 코드만으로 묶으면 다른 시도의 지역이 합쳐질 수 있어 Phase 35의 모든 검증 키를 `시도+시군구+산업+기간` 복합키로 바꿨다.
2. 한전 원행의 약 절반이 `5호미만제거`이고, 결합 후보의 중앙 관측 법정동 비율도 약 26.7%다. 억제 셀을 0으로 채우면 지역·산업별 월 프로필이 체계적으로 왜곡된다.
3. 국세청은 각 월 파일에 100개 업종이 있지만 명칭 개편 때문에 2021-2023 합집합은 122개이고 36개월 모두 이어지는 라벨은 80개뿐이다. rank 검사는 이 80개 공통 라벨로 제한했다.
4. 한전 전력과 KOSIS 사업체·종사자는 서로 다른 source family라 Phase 34보다 독립성은 좋아졌지만, 전력집약도와 GVA의 관계는 산업마다 다르다. rank 상승은 상호작용 존재의 증거이지 GVA 정확도의 증거가 아니다.
5. 산업 프로필 순열 뒤에도 월합 정합은 유지됐다. 따라서 이번에도 정합성만으로 산업 라벨의 의미를 검증하지 않았다.

## 8. 결정

- `시군구×KSIC 중분류×월`: 2023Q1 지원 셀에 한해 회고적 연구용 proxy allocation으로 개선. 직접 GVA actual이나 생산통계로 주장 금지.
- `시군구×KSIC 중분류×분기`: 전 기간 제품은 계속 Blocked. 한전 공개 파일이 세 개의 분기 스냅샷뿐이라 연속 분기 지표가 아니다.
- `시군구×생활업종×월`: 2021-2023 연속 관측 활동 패널로 Retain. KSIC/GVA로 이름을 바꾸거나 강제 매핑 금지.
- `시군구×KSIC 소분류`: 계속 Blocked. 무료 공개 원자료에서 동일 입도의 상호작용 자료를 확보하지 못했다.

## 9. API 및 사용자 조치

현재 완료한 한전·국세청 실험에는 API 키가 필요 없다. 고용행정통계 대시보드는 공개 화면에서 시군구×KSIC 중·소분류×월을 제공하지만, 공개 OpenAPI 응답에는 산업 차원이 없고 뷰어 내보내기는 세션형이다. 다음 단계에서 이것을 자동화하려면 API 키보다 먼저 사용자가 공개 대시보드에서 엑셀을 수동 내려받아 제공하는 방식이 가장 안전하다. 별도 유료 데이터나 카드사 계약은 요구하지 않는다.

## 10. 최종 상태

```json
{
  "status": "phase35_completed;free_interaction_signal_found;partial_retrospective_monthly_proxy_only;full_quarterly_product_blocked",
  "paid_card_data_used": false,
  "api_key_required_for_completed_experiment": false,
  "kepco_raw_rows": 1621555,
  "kepco_supported_monthly_rows_2023q1": 1401,
  "kepco_supported_middle_quarter_cells": 467,
  "kepco_all_supported_cells_conserve": true,
  "kepco_median_effective_rank": 3.0,
  "kepco_joined_common_proxy_group_rate": 0.0,
  "nts_panel_rows": 740919,
  "nts_continuous_months": 36,
  "nts_common_label_count": 80,
  "nts_median_effective_rank": 12.0,
  "release_aware": true,
  "direct_monthly_middle_gva_actual_available": false,
  "full_sigungu_middle_quarter_product_decision": "Blocked",
  "partial_2023q1_sigungu_middle_month_proxy_decision": "Retain_research_only",
  "nts_sigungu_lifestyle_month_panel_decision": "Retain_as_activity_diagnostic_not_KSIC_GVA",
  "employment_dashboard_next_action": "manual free Excel export preferred; public OpenAPI lacks industry dimension",
  "production_use": false,
  "official_statistics_claim": false,
  "generated_at": "2026-07-20T10:04:28+09:00"
}
```
