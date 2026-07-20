# Partial Statistics Estimation Phase 34 - Sigungu Fine-Quarterly Feasibility

## 1. 결론

시군구×중분류×분기 표를 회계적으로 생성하는 것은 가능하지만, 현재 자료로는 이를 중분류별 분기 GVA 추정치로 승격할 수 없다. 생성된 결합행렬은 연간 중분류 가중치와 광역산업 공통 분기 프로필의 외적이어서 유효 rank가 1이며, 중분류별 고유한 분기 신호가 없다.

## 2. 사전등록된 후보

- `R0_contemporaneous_structure`: 같은 연도 구조를 사용한 회고적 회계 배분. 구조자료 공표시차 2년을 위반하므로 예측에는 사용할 수 없다.
- `S0_lag2_structure`: 2년 전 구조를 사용한 구조축 as-of 후보. 구조축 누수는 막지만 과거 분기 지표의 release archive가 없어 전체 제품은 strict vintage가 아니다.
- 두 후보 모두 direct 시군구×중분류×분기 actual이 없으므로 정확도 평가는 하지 않는다.

## 3. Coverage

| policy_id | parent_sector_code | universe_parent_cells | expected_parent_cells | matched_parent_cells | parent_cell_coverage_rate | all_year_universe_coverage_rate | matched_sigungu_count | matched_year_min | matched_year_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R0_contemporaneous_structure | B00 | 496 | 416 | 94 | 0.22596153846153846 | 0.18951612903225806 | 39 | 2021 | 2023 |
| R0_contemporaneous_structure | C00 | 746 | 594 | 216 | 0.36363636363636365 | 0.289544235924933 | 87 | 2021 | 2023 |
| R0_contemporaneous_structure | ALL | 1242 | 1010 | 310 | 0.3069306930693069 | 0.249597423510467 | 87 | 2021 | 2023 |
| S0_lag2_structure | B00 | 496 | 105 | 21 | 0.2 | 0.04233870967741935 | 21 | 2023 | 2023 |
| S0_lag2_structure | C00 | 746 | 148 | 42 | 0.28378378378378377 | 0.05630026809651475 | 42 | 2023 | 2023 |
| S0_lag2_structure | ALL | 1242 | 253 | 63 | 0.2490118577075099 | 0.050724637681159424 | 42 | 2023 | 2023 |
| source_inventory | ALL | 12536 | 12536 | 262 |  |  | 262 | 2021 | 2023 |

## 4. 공통 프록시·유효차원 감사

| policy_id | audit_id | value | numerator | denominator | status | interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| R0_contemporaneous_structure | fine_temporal_matrix_rank | 1.0 | 225 | 225 | fail_joint_interaction | rank one means the joint cube is an outer product of annual fine weights and one broad quarterly profile |
| R0_contemporaneous_structure | within_parent_identical_industry_temporal_profile_rate | 1.0 | 225 | 225 | fail_common_proxy | all middle industries inherit the same quarterly movement within a parent cell |
| R0_contemporaneous_structure | within_sido_identical_sigungu_temporal_profile_rate | 1.0 | 50 | 50 | fail_common_proxy | all sigungu inherit the same sido-level quarterly movement where the parent profile is shared |
| S0_lag2_structure | fine_temporal_matrix_rank | 1.0 | 43 | 43 | fail_joint_interaction | rank one means the joint cube is an outer product of annual fine weights and one broad quarterly profile |
| S0_lag2_structure | within_parent_identical_industry_temporal_profile_rate | 1.0 | 43 | 43 | fail_common_proxy | all middle industries inherit the same quarterly movement within a parent cell |
| S0_lag2_structure | within_sido_identical_sigungu_temporal_profile_rate | 1.0 | 12 | 12 | fail_common_proxy | all sigungu inherit the same sido-level quarterly movement where the parent profile is shared |
| structure_source | business_employee_share_correlation | 0.9080314049372329 | 8200 | 12536 | related_same_family_not_independent | business and employee measures come from one source family and cannot count as two independent proxies |
| structure_source | single_component_weight_rate | 0.34588385449904274 | 4336 | 12536 | warning_proxy_fallback | rows with only business or employee share silently reduce the blend to one component |

## 5. 구조 프록시 안정성

| parent_sector_code | comparison_rows | weight_correlation | mean_absolute_weight_change | p95_absolute_weight_change | validation_scope |
| --- | --- | --- | --- | --- | --- |
| B00 | 261 | 0.9580852656928589 | 0.014102924365451696 | 0.08333333333333337 | proxy_stability_not_GVA_accuracy |
| C00 | 7792 | 0.9827719921378574 | 0.0074041981218226855 | 0.029263892320205792 | proxy_stability_not_GVA_accuracy |

## 6. 정합성과 negative control

정합 검사는 1,865개 그룹 모두 통과했고 최대 절대오차는 3.73e-09이다. 그러나 산업 라벨 내부 순열 negative control도 똑같이 정합을 통과했다. 따라서 정합성은 계산 정확성만 보장하며 산업 의미나 GVA 정확도를 검증하지 못한다.

| policy_id | control_id | max_parent_conservation_error | conservation_still_passes | interpretation |
| --- | --- | --- | --- | --- |
| R0_contemporaneous_structure | within_parent_industry_label_permutation | 9.313225746154785e-10 | Y | parent conservation cannot validate industry semantics because permuted industry weights also conserve exactly |
| S0_lag2_structure | within_parent_industry_label_permutation | 4.656612873077393e-10 | Y | parent conservation cannot validate industry semantics because permuted industry weights also conserve exactly |

## 7. 해상도별 결정

| candidate_grain | data_support | decision | reason |
| --- | --- | --- | --- |
| sigungu×KSIC_middle×annual | B/C only; 2021-2023; partial sigungu coverage | retain_as_structure_allocation_only | no direct middle-industry GVA actual |
| sigungu×KSIC_middle×quarter | separable annual structure plus broad quarterly profile | blocked_as_joint_GVA | rank-one cube; identical temporal proxy by middle industry; no interaction source or direct actual |
| sigungu×KSIC_small×quarter | no compatible nationwide small-industry structure source | blocked | industry source grain unavailable |
| sigungu×KSIC_middle×month | quarterly parent only in current experiment | blocked | would require equal-month or another unsupported common proxy |
| sigungu×service_middle×quarter | quarterly service signal is sido×service section; A2 excludes services | blocked | spatial fine-service structure margin unavailable |

## 8. 엄격 검증에서 추가로 발견한 이슈

1. Phase 33 A2의 `industry_structure_index`는 B/C 전체에서 합이 1이므로 B00 또는 C00 GVA를 배분할 때 그대로 쓰면 안 된다. Phase 34는 B와 C 내부에서 다시 조건부 정규화했다.
2. 사업체와 종사자는 같은 KOSIS 제조·광업 source family이므로 독립 프록시 2개로 계산할 수 없다.
3. 일부 행은 종사자 또는 사업체 중 하나가 비어 있어 평균 가중치가 사실상 단일 프록시 fallback이 된다.
4. 시군구 분기 부모 자체도 공식 시군구 분기 actual이 아니라 연간 anchor의 development allocation이다. 하위 중분류 값은 한 단계 더 내려간 allocation이다.
5. 같은 시도 안의 시군구가 동일한 분기 프로필을 상속하고, 같은 부모산업 안의 모든 중분류도 동일한 분기 프로필을 상속한다.
6. 공표시차를 지킨 S0도 temporal historical vintage가 없으므로 완전한 strict-as-of 제품은 아니다.

## 9. 최종 상태

```json
{
  "status": "phase34_completed;sigungu_middle_annual_structure_retained;sigungu_middle_quarter_joint_blocked;monthly_blocked;small_industry_blocked",
  "target": "GVA",
  "retrospective_joint_shadow_rows": 14516,
  "lag2_structure_shadow_rows": 2864,
  "covered_parent_cells_retrospective": 310,
  "covered_parent_cells_lag2": 63,
  "median_effective_temporal_rank": 1.0,
  "identical_middle_industry_temporal_profile_rate": 1.0,
  "all_parent_conservation_checks_passed": true,
  "permutation_negative_control_also_conserves": true,
  "direct_quarterly_middle_actual_available": false,
  "historical_temporal_release_vintage_available": false,
  "interaction_source_available": false,
  "joint_product_decision": "Blocked",
  "allowed_claim": "sigungu manufacturing/mining middle-industry annual structure allocation and broad quarterly marginal signal, separately",
  "prohibited_claim": "observed or validated sigungu x middle-industry x quarter GVA; monthly GVA; small-industry GVA; production use; official statistics equivalence",
  "production_use": false,
  "official_statistics_claim": false,
  "generated_at": "2026-07-20T09:41:50+09:00"
}
```

## 10. 다음 실험 조건

시군구×중분류×분기를 다시 열려면 최소 하나의 `시군구×중분류×분기` 상호작용 자료가 필요하다. 후보는 산업별 전력/카드/매출/고용보험 피보험자/부가세·전자세금계산서처럼 지역·업종·월을 동시에 식별하는 자료다. 확보 전에는 `시군구×중분류×연간 구조`와 `시도×산업×분기 활동`을 별도 marginal product로 제공하는 것이 정직하다.
