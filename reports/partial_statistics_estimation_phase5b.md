# Partial Statistics Estimation Phase 5B

## 1. 실행 요약

- 실행일: `2026-07-18T07:52:59+09:00`
- 목적: Phase 5의 Ridge 개선을 반복 수준, 독립 상위합계, reconciliation, placebo, bootstrap, uncertainty 관점에서 재검토했다.
- 운영 판정: `production_use=false`, `confirmatory_use=false`, `official_statistics_claim=false`.
- 중요한 변경: Phase 5의 pooled Grade B를 그대로 승계하지 않고 repeat-level primary metric으로 재판정했다.

| target_name | best_baseline_model | best_baseline_track | best_baseline_mean_repeat_wmape | best_candidate_model | best_candidate_track | best_candidate_mean_repeat_wmape | relative_improvement | primary_mask_pass_count | region_block_baseline_wmape | region_block_candidate_wmape | region_block_pass | material_degradation_gate | provisional_grade_recalculated | production_use | confirmatory_claim |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| establishments | B3_latest_observed_share | U_unconstrained | 0.6184526489126286 | M1_hierarchical_ridge | U_unconstrained | 0.7797111261545489 | -0.2607450667815021 | 2 | 0.6139345320056102 | 0.7156346884456134 | N | N | D | false | false |
| employees | B3_latest_observed_share | U_unconstrained | 0.7906011455193714 | M1_hierarchical_ridge | U_unconstrained | 0.7961465791087021 | -0.0070141987786872095 | 4 | 0.7199629675464825 | 0.6326846184968286 | Y | Y | D | false | false |

## 2. Phase 5 결과 재검토

- Phase 5 입력 산출물은 hash로 고정했다.
- Pooled metric은 보조지표로만 남기고, 모델 선택은 반복별 WMAPE 평균을 사용했다.
| artifact | exists | row_count | sha256 | protocol_status |
| --- | --- | --- | --- | --- |
| partial_stats_cell_registry.csv | Y | 39672 | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | frozen_input |
| partial_stats_observation_mask.csv | Y | 39672 | 66215e46a9046d6e5897ed9e48df00fd0254e8e738f26c00008c62393b0fdf58 | frozen_input |
| partial_stats_aggregate_constraints.csv | Y | 2531 | 6d786f13b615b026e2610da7a93fb278a47e3eef3237f50420d1898c66feaf00 | frozen_input |
| partial_stats_mask_registry.csv | Y | 240 | 53a2931d59c311165a43dc9a4e54a69b1dc7cc49176162f92961b825adafc303 | frozen_input |
| partial_stats_region_features.csv | Y | 228 | c5dbf9de8a0a5b1854b92f8cf6aa33e28cf678927326dfdd3b73515a844cdadf | frozen_input |
| partial_stats_industry_features.csv | Y | 29 | 1c95766d825cca24d4af2185c15bd8fc60286133eef9a71d7187dfa5fd06f24e | frozen_input |
| partial_stats_period_features.csv | Y | 3 | 30e1b448b1a59951c5ec44d8ea9e372f20373f03e1d94f389cc40d0022da43c4 | frozen_input |
| partial_stats_spatial_features.csv | Y | 456 | d01b965b441d5549638016d3efeae4b3520bda0411990e6fbee3f09bbeccd829 | frozen_input |
| partial_stats_auxiliary_features.csv | Y | 446 | 249c6ea2eee0dcfa6111553de32ccea969b253a190085bc0d9242d149f917367 | frozen_input |

## 3. Mask 반복 재현성

| mask_scenario | target_name | mean_repeat_wmape | runs |
| --- | --- | --- | --- |
| M0_random | employees | 1.4234774106041606 | 30 |
| M0_random | establishments | 17.019565252064233 | 30 |
| M1_region_block | employees | 3.9682490026917008 | 30 |
| M1_region_block | establishments | 28.38470985963651 | 30 |
| M2_industry_block | employees | 1.798389574636451 | 30 |
| M2_industry_block | establishments | 13.311020328330176 | 30 |
| M3_time_block | employees | 1.3145809913683943 | 30 |
| M3_time_block | establishments | 14.215537978353169 | 30 |
| M4_regional_cluster | employees | 1.7004459342983749 | 30 |
| M4_regional_cluster | establishments | 11.099601116960812 | 30 |
| M5_small_value | employees | 6.9894223802492546 | 30 |
| M5_small_value | establishments | 22.615986981588676 | 30 |
| M6_rare_industry | employees | 37.46016256740387 | 30 |
| M6_rare_industry | establishments | 3113.089481395709 | 30 |
| M7_noncapital_rural | employees | 1.3554819501375062 | 30 |
| M7_noncapital_rural | establishments | 16.672476007091834 | 30 |

## 4. Leakage Audit

| audit_status | runs |
| --- | --- |
| pass | 480 |

## 5. 독립 Aggregate Constraint

- `sido_industry_business`의 시도×대분류(B/C)×연도×target 합계를 독립 공식 parent total 후보로 사용했다.
| constraint_id | source_table_id | source_name | target_name | region_level | region_key | industry_level | industry_section | industry_name | period | official_total | unit | population_definition | release_date | revision_date | source_vintage | constraint_grade | constraint_role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1_SIDO_SECTION_서울특별시_B_2021_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 서울특별시 | section | B | 광업(05~08) | 2021 | 25.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_서울특별시_B_2022_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 서울특별시 | section | B | 광업(05~08) | 2022 | 26.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_서울특별시_B_2023_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 서울특별시 | section | B | 광업(05~08) | 2023 | 21.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_부산광역시_B_2021_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 부산광역시 | section | B | 광업(05~08) | 2021 | 20.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_부산광역시_B_2022_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 부산광역시 | section | B | 광업(05~08) | 2022 | 16.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_부산광역시_B_2023_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 부산광역시 | section | B | 광업(05~08) | 2023 | 13.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_대구광역시_B_2021_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 대구광역시 | section | B | 광업(05~08) | 2021 | 9.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_대구광역시_B_2022_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 대구광역시 | section | B | 광업(05~08) | 2022 | 9.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_대구광역시_B_2023_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 대구광역시 | section | B | 광업(05~08) | 2023 | 10.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_인천광역시_B_2021_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 인천광역시 | section | B | 광업(05~08) | 2021 | 35.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_인천광역시_B_2022_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 인천광역시 | section | B | 광업(05~08) | 2022 | 35.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |
| C1_SIDO_SECTION_인천광역시_B_2023_establishments | 101/DT_1K52F08 | 시도 산업별 사업체수·종사자수 | establishments | sido | 인천광역시 | section | B | 광업(05~08) | 2023 | 36.0 | 개 | same survey family, official sido-section table |  |  | municipality_feature_mart_long_current | C1_same_survey_independent_table | hard_constraint |

## 6. 모집단 및 KSIC 정합성

- 중분류 제조·광업 셀은 KSIC section B/C parent total 아래에 매핑했다.
- anchor-derived 합계는 hard constraint로 쓰지 않았고, 독립 표와 모집단 관계만 감사했다.
| constraint_id | region_key | industry_section | period | target_name | official_total | anchor_observed_total | anchor_to_official_ratio | population_alignment_status | audit_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1_SIDO_SECTION_서울특별시_B_2021_establishments | 서울특별시 | B | 2021 | establishments | 25.0 | 1.0 | 0.04 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_서울특별시_B_2022_establishments | 서울특별시 | B | 2022 | establishments | 26.0 | 0.0 | 0.0 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_서울특별시_B_2023_establishments | 서울특별시 | B | 2023 | establishments | 21.0 | 1.0 | 0.047619047619047616 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_부산광역시_B_2021_establishments | 부산광역시 | B | 2021 | establishments | 20.0 | 2.0 | 0.1 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_부산광역시_B_2022_establishments | 부산광역시 | B | 2022 | establishments | 16.0 | 1.0 | 0.0625 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_부산광역시_B_2023_establishments | 부산광역시 | B | 2023 | establishments | 13.0 | 1.0 | 0.07692307692307693 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_대구광역시_B_2021_establishments | 대구광역시 | B | 2021 | establishments | 9.0 | 1.0 | 0.1111111111111111 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_대구광역시_B_2022_establishments | 대구광역시 | B | 2022 | establishments | 9.0 | 1.0 | 0.1111111111111111 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_대구광역시_B_2023_establishments | 대구광역시 | B | 2023 | establishments | 10.0 | 1.0 | 0.1 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_인천광역시_B_2021_establishments | 인천광역시 | B | 2021 | establishments | 35.0 | 15.0 | 0.42857142857142855 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_인천광역시_B_2022_establishments | 인천광역시 | B | 2022 | establishments | 35.0 | 16.0 | 0.45714285714285713 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |
| C1_SIDO_SECTION_인천광역시_B_2023_establishments | 인천광역시 | B | 2023 | establishments | 36.0 | 16.0 | 0.4444444444444444 | usable_parent_total | Official section total can exceed middle-level observed anchor because unpublished sigungu cells are included. |

## 7. Constraint Firewall

- Track U: hidden cell actual과 parent total을 쓰지 않는 unconstrained recovery.
- Track C: hidden cell actual은 쓰지 않고 독립 parent total만 쓰는 constraint-assisted recovery.
- 두 track은 별도 컬럼과 별도 WMAPE로 보고한다.

## 8. Baseline

| model_id | track | target_name | mean_repeat_wmape | runs |
| --- | --- | --- | --- | --- |
| B0_group_mean | C_constraint_assisted | employees | 12.142762078050962 | 240 |
| B0_group_mean | C_constraint_assisted | establishments | 758.9522848991289 | 240 |
| B0_group_mean | U_unconstrained | employees | 1.3477251399152494 | 240 |
| B0_group_mean | U_unconstrained | establishments | 1.0209107155080748 | 240 |
| B2_region_total_share | C_constraint_assisted | employees | 12.023415340736301 | 240 |
| B2_region_total_share | C_constraint_assisted | establishments | 758.9419837612484 | 240 |
| B2_region_total_share | U_unconstrained | employees | 2.0479990621283113 | 240 |
| B2_region_total_share | U_unconstrained | establishments | 2.966076798155824 | 240 |
| B3_latest_observed_share | C_constraint_assisted | employees | 11.960290805975887 | 240 |
| B3_latest_observed_share | C_constraint_assisted | establishments | 758.9404976770325 | 240 |
| B3_latest_observed_share | U_unconstrained | employees | 0.7906011455193714 | 240 |
| B3_latest_observed_share | U_unconstrained | establishments | 0.6184526489126286 | 240 |
| B4_sido_industry_share | C_constraint_assisted | employees | 12.081014978561113 | 240 |
| B4_sido_industry_share | C_constraint_assisted | establishments | 758.9405929090639 | 240 |
| B4_sido_industry_share | U_unconstrained | employees | 1.1981421953634406 | 240 |
| B4_sido_industry_share | U_unconstrained | establishments | 0.9422123547772381 | 240 |
| B5_nearest5_mean | C_constraint_assisted | employees | 12.072527981552717 | 240 |
| B5_nearest5_mean | C_constraint_assisted | establishments | 758.9360124587915 | 240 |
| B5_nearest5_mean | U_unconstrained | employees | 1.4554272308457135 | 240 |
| B5_nearest5_mean | U_unconstrained | establishments | 1.9884407718126165 | 240 |

## 9. Hierarchical Ridge

| model_id | track | target_name | mask_scenario | mean_repeat_wmape | p90_repeat_wmape | runs |
| --- | --- | --- | --- | --- | --- | --- |
| M1_hierarchical_ridge | C_constraint_assisted | employees | M0_random | 1.8427242495779128 | 1.9184041736457236 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | employees | M1_region_block | 6.342956587452363 | 7.517817094443061 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | employees | M2_industry_block | 1.8659085326436993 | 3.0831221769819446 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | employees | M3_time_block | 1.6426438522760982 | 1.7643994345884497 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | employees | M4_regional_cluster | 1.7051041155796756 | 2.8991269300159503 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | employees | M5_small_value | 11.176216330794196 | 12.23592303506121 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | employees | M6_rare_industry | 69.52775605821886 | 105.65356860714986 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | employees | M7_noncapital_rural | 1.6669990799399832 | 1.7312118670891985 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | establishments | M0_random | 28.98956380929437 | 30.933958210081627 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | establishments | M1_region_block | 49.80272392583537 | 55.44200683780837 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | establishments | M2_industry_block | 19.333956254548127 | 25.133549783549796 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | establishments | M3_time_block | 23.692622174623803 | 25.460737117581875 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | establishments | M4_regional_cluster | 15.328729653086485 | 28.710491256286232 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | establishments | M5_small_value | 37.360340314623386 | 39.56144568407079 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | establishments | M6_rare_industry | 5841.369296595366 | 6647.766729963331 | 30 |
| M1_hierarchical_ridge | C_constraint_assisted | establishments | M7_noncapital_rural | 27.65863159559395 | 30.055486882023086 | 30 |

## 10. Count GLM

Count GLM은 전체 mask 재실행 가능성을 우선해 수치형 구조 feature 기반 fast-screening으로 실행했다. 고카디널리티 지역·업종 one-hot은 M1 계열에서만 검증하고, Count 후보에서는 제외했다.

| model_id | track | target_name | mean_wmape | p90_ape | runs |
| --- | --- | --- | --- | --- | --- |
| M2_poisson_glm | C_constraint_assisted | employees | 11.991075814260471 | 161.23428319649915 | 240 |
| M2_poisson_glm | C_constraint_assisted | establishments | 758.9377585441273 | 2896.615214148654 | 240 |
| M2_poisson_glm | U_unconstrained | employees | 0.8662633601508359 | 4.198580633193658 | 240 |
| M2_poisson_glm | U_unconstrained | establishments | 37.844163681919795 | 258.9814459646875 | 240 |
| M2_tweedie_glm | C_constraint_assisted | employees | 11.984706904855221 | 161.56319668630042 | 240 |
| M2_tweedie_glm | C_constraint_assisted | establishments | 758.9346513934081 | 2989.559033949414 | 240 |
| M2_tweedie_glm | U_unconstrained | employees | 0.8601820517135763 | 4.421297220049041 | 240 |
| M2_tweedie_glm | U_unconstrained | establishments | 38.29249905457854 | 260.5740987707144 | 240 |

## 11. Parent-share Model

| track | target_name | mask_scenario | mean_wmape | runs |
| --- | --- | --- | --- | --- |
| C_constraint_assisted | employees | M0_random | 1.827011079931064 | 30 |
| C_constraint_assisted | employees | M1_region_block | 6.383225408453299 | 30 |
| C_constraint_assisted | employees | M2_industry_block | 2.224507713742366 | 30 |
| C_constraint_assisted | employees | M3_time_block | 1.623913875010288 | 30 |
| C_constraint_assisted | employees | M4_regional_cluster | 2.037862169751199 | 30 |
| C_constraint_assisted | employees | M5_small_value | 11.196325617774017 | 30 |
| C_constraint_assisted | employees | M6_rare_industry | 69.51554099309602 | 30 |
| C_constraint_assisted | employees | M7_noncapital_rural | 1.6543302520222272 | 30 |
| C_constraint_assisted | establishments | M0_random | 28.985519346510877 | 30 |
| C_constraint_assisted | establishments | M1_region_block | 49.795080028587115 | 30 |
| C_constraint_assisted | establishments | M2_industry_block | 19.30842939396448 | 30 |
| C_constraint_assisted | establishments | M3_time_block | 23.686320260910453 | 30 |

## 12. Matrix·Tensor Completion

- 이번 구현은 연도별 지역×업종 matrix completion을 rank 3/5/8의 row/column latent-mean proxy로 실행했다. Tensor completion은 동일 cube 후보군에 등록하되 현 단계에서는 빠른 matrix path로 제한했다.
| model_id | track | target_name | mean_wmape | runs |
| --- | --- | --- | --- | --- |
| M4_low_rank_rank3 | C_constraint_assisted | employees | 12.012922683410368 | 240 |
| M4_low_rank_rank3 | C_constraint_assisted | establishments | 758.9310332630715 | 240 |
| M4_low_rank_rank3 | U_unconstrained | employees | 1.8805430956071054 | 240 |
| M4_low_rank_rank3 | U_unconstrained | establishments | 2.318642331210223 | 240 |
| M4_low_rank_rank5 | C_constraint_assisted | employees | 12.00542481554675 | 240 |
| M4_low_rank_rank5 | C_constraint_assisted | establishments | 758.9311665916765 | 240 |
| M4_low_rank_rank5 | U_unconstrained | employees | 1.8276261202339896 | 240 |
| M4_low_rank_rank5 | U_unconstrained | establishments | 2.185277817337618 | 240 |
| M4_low_rank_rank8 | C_constraint_assisted | employees | 11.998856511251596 | 240 |
| M4_low_rank_rank8 | C_constraint_assisted | establishments | 758.9314733205575 | 240 |
| M4_low_rank_rank8 | U_unconstrained | employees | 1.777175346334098 | 240 |
| M4_low_rank_rank8 | U_unconstrained | establishments | 2.0533015283302216 | 240 |

## 13. 사업체·종사자 결합모델

| track | target_name | mean_wmape | runs |
| --- | --- | --- | --- |
| C_constraint_assisted | employees | 12.028387256118817 | 240 |
| C_constraint_assisted | establishments | 758.9405929090639 | 240 |
| U_unconstrained | employees | 1.0090851549384683 | 240 |
| U_unconstrained | establishments | 0.9422123547772381 | 240 |

## 14. Spatial Regularization

| track | target_name | mask_scenario | mean_wmape | runs |
| --- | --- | --- | --- | --- |
| C_constraint_assisted | employees | M0_random | 1.8451721533508254 | 30 |
| C_constraint_assisted | employees | M1_region_block | 6.344733040597386 | 30 |
| C_constraint_assisted | employees | M2_industry_block | 2.251699980452098 | 30 |
| C_constraint_assisted | employees | M3_time_block | 1.6418697621872789 | 30 |
| C_constraint_assisted | employees | M4_regional_cluster | 2.0632344851539033 | 30 |
| C_constraint_assisted | employees | M5_small_value | 11.186323120424868 | 30 |
| C_constraint_assisted | employees | M6_rare_industry | 69.52775605821886 | 30 |
| C_constraint_assisted | employees | M7_noncapital_rural | 1.663541203569956 | 30 |
| C_constraint_assisted | establishments | M0_random | 28.984787754185206 | 30 |
| C_constraint_assisted | establishments | M1_region_block | 49.795080028587115 | 30 |
| C_constraint_assisted | establishments | M2_industry_block | 19.31739145741068 | 30 |
| C_constraint_assisted | establishments | M3_time_block | 23.686321838455534 | 30 |

## 15. Reconciliation

| model_id | target_name | raw_unconstrained_wmape | constraint_assisted_wmape | mean_wmape_delta | runs |
| --- | --- | --- | --- | --- | --- |
| B0_group_mean | employees | 1.3477251399152494 | 12.142762078050962 | 10.795036938135713 | 240 |
| B0_group_mean | establishments | 1.0209107155080748 | 758.9522848991289 | 757.9313741836208 | 240 |
| B2_region_total_share | employees | 2.0479990621283113 | 12.023415340736301 | 9.97541627860799 | 240 |
| B2_region_total_share | establishments | 2.966076798155824 | 758.9419837612484 | 755.9759069630926 | 240 |
| B3_latest_observed_share | employees | 0.7906011455193714 | 11.960290805975887 | 11.169689660456516 | 240 |
| B3_latest_observed_share | establishments | 0.6184526489126286 | 758.9404976770325 | 758.3220450281199 | 240 |
| B4_sido_industry_share | employees | 1.1981421953634406 | 12.081014978561113 | 10.882872783197673 | 240 |
| B4_sido_industry_share | establishments | 0.9422123547772381 | 758.9405929090639 | 757.9983805542867 | 240 |
| B5_nearest5_mean | employees | 1.4554272308457135 | 12.072527981552717 | 10.617100750707005 | 240 |
| B5_nearest5_mean | establishments | 1.9884407718126165 | 758.9360124587915 | 756.9475716869789 | 240 |
| B5_queen_mean | employees | 1.4572099065086748 | 12.07202294969544 | 10.614813043186762 | 240 |
| B5_queen_mean | establishments | 2.043842511236214 | 758.9358005747271 | 756.8919580634908 | 240 |

## 16. Region Block

| model_id | track | target_name | mask_scenario | mean_repeat_wmape | p90_repeat_wmape | runs |
| --- | --- | --- | --- | --- | --- | --- |
| M5_coupled_employee | U_unconstrained | employees | M1_region_block | 0.5893116264590874 | 0.6206607554758218 | 30 |
| M3_parent_share_ridge | U_unconstrained | establishments | M1_region_block | 0.6128204080404447 | 0.6535956585317062 | 30 |
| M5_coupled_employee | U_unconstrained | establishments | M1_region_block | 0.6139345320056102 | 0.6539715253375151 | 30 |
| B4_sido_industry_share | U_unconstrained | establishments | M1_region_block | 0.6139345320056102 | 0.6539715253375151 | 30 |
| B3_latest_observed_share | U_unconstrained | establishments | M1_region_block | 0.6139345320056102 | 0.6539715253375151 | 30 |
| B0_group_mean | U_unconstrained | establishments | M1_region_block | 0.6222391998498947 | 0.6656937151006656 | 30 |
| M1_hierarchical_ridge | U_unconstrained | employees | M1_region_block | 0.6326846184968284 | 0.6840774256652157 | 30 |
| M6_spatial_regularized | U_unconstrained | establishments | M1_region_block | 0.691078553790012 | 0.7149776282101842 | 30 |
| M1_hierarchical_ridge | U_unconstrained | establishments | M1_region_block | 0.7156346884456134 | 0.7261521810067403 | 30 |
| B0_group_mean | U_unconstrained | employees | M1_region_block | 0.719732033063687 | 0.7613931903687552 | 30 |
| B4_sido_industry_share | U_unconstrained | employees | M1_region_block | 0.7199629675464825 | 0.7631159539464133 | 30 |
| B3_latest_observed_share | U_unconstrained | employees | M1_region_block | 0.7199629675464825 | 0.7631159539464133 | 30 |

## 17. Industry Block

| model_id | track | target_name | mask_scenario | mean_repeat_wmape | p90_repeat_wmape | runs |
| --- | --- | --- | --- | --- | --- | --- |
| M1_hierarchical_ridge | U_unconstrained | employees | M2_industry_block | 0.720064076107416 | 0.7668430422341224 | 30 |
| M1_hierarchical_ridge | U_unconstrained | establishments | M2_industry_block | 0.7288344899410446 | 0.7773484505127112 | 30 |
| M3_parent_share_ridge | U_unconstrained | establishments | M2_industry_block | 0.7488549632176944 | 0.7974237290561317 | 30 |
| M2_tweedie_glm | U_unconstrained | employees | M2_industry_block | 0.7900121537483458 | 0.8311670147255479 | 30 |
| M2_poisson_glm | U_unconstrained | employees | M2_industry_block | 0.8114337915270424 | 0.8626564309423154 | 30 |
| M3_parent_share_ridge | U_unconstrained | employees | M2_industry_block | 0.8852005690949772 | 0.9787666104326871 | 30 |
| M5_coupled_employee | U_unconstrained | employees | M2_industry_block | 0.9260826170087636 | 1.2686427510629072 | 30 |
| B5_queen_mean | U_unconstrained | employees | M2_industry_block | 0.9343911383348332 | 0.8913178600019246 | 30 |
| B5_nearest5_mean | U_unconstrained | employees | M2_industry_block | 0.9393185808179653 | 0.919734571810738 | 30 |
| M6_spatial_regularized | U_unconstrained | establishments | M2_industry_block | 0.9531550658207062 | 1.4299092679107928 | 30 |
| M5_coupled_employee | U_unconstrained | establishments | M2_industry_block | 0.9733903092867924 | 1.7714038878965392 | 30 |
| B3_latest_observed_share | U_unconstrained | establishments | M2_industry_block | 0.9733903092867924 | 1.7714038878965392 | 30 |

## 18. Regional Cluster

| model_id | track | target_name | mask_scenario | mean_repeat_wmape | p90_repeat_wmape | runs |
| --- | --- | --- | --- | --- | --- | --- |
| M1_hierarchical_ridge | U_unconstrained | employees | M4_regional_cluster | 0.7205292586068537 | 0.7756851720131325 | 30 |
| M1_hierarchical_ridge | U_unconstrained | establishments | M4_regional_cluster | 0.7310157174151359 | 0.805739288192971 | 30 |
| M3_parent_share_ridge | U_unconstrained | establishments | M4_regional_cluster | 0.7816408946408306 | 0.9194561630466412 | 30 |
| M2_tweedie_glm | U_unconstrained | employees | M4_regional_cluster | 0.7926444389809641 | 0.8328642160629784 | 30 |
| M2_poisson_glm | U_unconstrained | employees | M4_regional_cluster | 0.8147003471471151 | 0.8656829362171826 | 30 |
| B5_queen_mean | U_unconstrained | employees | M4_regional_cluster | 0.9065365539090712 | 0.8886825513556506 | 30 |
| B5_nearest5_mean | U_unconstrained | employees | M4_regional_cluster | 0.9100636127286145 | 0.9180724146881181 | 30 |
| M3_parent_share_ridge | U_unconstrained | employees | M4_regional_cluster | 0.9227210571222899 | 1.0086893203121456 | 30 |
| M6_spatial_regularized | U_unconstrained | establishments | M4_regional_cluster | 0.9559089032919948 | 2.0552135815252215 | 30 |
| B5_queen_mean | U_unconstrained | establishments | M4_regional_cluster | 0.9659015830246376 | 1.0775213205074252 | 30 |
| B5_nearest5_mean | U_unconstrained | establishments | M4_regional_cluster | 0.9678208272556793 | 1.0887192753167712 | 30 |
| M5_coupled_employee | U_unconstrained | employees | M4_regional_cluster | 0.9685001836728254 | 1.7274544485466272 | 30 |

## 19. Small-value Mask

| model_id | track | target_name | mask_scenario | mean_repeat_wmape | p90_repeat_wmape | runs |
| --- | --- | --- | --- | --- | --- | --- |
| B3_latest_observed_share | U_unconstrained | establishments | M5_small_value | 0.6932137003824512 | 0.7441892940331114 | 30 |
| M1_hierarchical_ridge | U_unconstrained | establishments | M5_small_value | 0.8281418563546968 | 0.8420067779014282 | 30 |
| M1_hierarchical_ridge | U_unconstrained | employees | M5_small_value | 0.9478418225264295 | 0.9998695310842786 | 30 |
| M2_tweedie_glm | U_unconstrained | employees | M5_small_value | 1.1157569517622723 | 1.2097533899954065 | 30 |
| B3_latest_observed_share | U_unconstrained | employees | M5_small_value | 1.1272441820993906 | 1.304146167103295 | 30 |
| M2_poisson_glm | U_unconstrained | employees | M5_small_value | 1.1315928454473296 | 1.227334669056221 | 30 |
| M4_low_rank_rank8 | U_unconstrained | establishments | M5_small_value | 1.2729457966738347 | 1.312621076934815 | 30 |
| B2_region_total_share | U_unconstrained | establishments | M5_small_value | 1.3319395854058584 | 1.405965738292669 | 30 |
| M4_low_rank_rank5 | U_unconstrained | establishments | M5_small_value | 1.35087432188648 | 1.3908091058490784 | 30 |
| M5_coupled_employee | U_unconstrained | establishments | M5_small_value | 1.3990562017112194 | 1.4481176344693512 | 30 |
| B4_sido_industry_share | U_unconstrained | establishments | M5_small_value | 1.3990562017112194 | 1.4481176344693512 | 30 |
| M3_parent_share_ridge | U_unconstrained | establishments | M5_small_value | 1.4001867251461553 | 1.4483292841893913 | 30 |

## 20. Rural·Rare-industry Stress Test

| model_id | track | target_name | mask_scenario | mean_repeat_wmape | p90_repeat_wmape | runs |
| --- | --- | --- | --- | --- | --- | --- |
| B3_latest_observed_share | U_unconstrained | establishments | M6_rare_industry | 0.3272208694199577 | 0.4283415413533834 | 30 |
| B3_latest_observed_share | U_unconstrained | employees | M6_rare_industry | 0.38970439107450827 | 0.6405860970712296 | 30 |
| B3_latest_observed_share | U_unconstrained | establishments | M7_noncapital_rural | 0.4912867026907847 | 0.5330981324259982 | 30 |
| B3_latest_observed_share | U_unconstrained | employees | M7_noncapital_rural | 0.5218785876212619 | 0.5892377093849023 | 30 |
| M5_coupled_employee | U_unconstrained | establishments | M6_rare_industry | 0.5295009910233699 | 0.6025308099098396 | 30 |
| B4_sido_industry_share | U_unconstrained | establishments | M6_rare_industry | 0.5295009910233699 | 0.6025308099098396 | 30 |
| M3_parent_share_ridge | U_unconstrained | establishments | M6_rare_industry | 0.5723965521691168 | 0.6657888734734436 | 30 |
| M5_coupled_employee | U_unconstrained | employees | M6_rare_industry | 0.5848767100319463 | 0.7747573441429716 | 30 |
| M3_parent_share_ridge | U_unconstrained | employees | M6_rare_industry | 0.5850611991609348 | 0.7778034258155064 | 30 |
| B4_sido_industry_share | U_unconstrained | employees | M6_rare_industry | 0.6020233505902058 | 0.8281279635476767 | 30 |
| B7_empirical_bayes | U_unconstrained | establishments | M6_rare_industry | 0.6027566171591157 | 0.6370387959461598 | 30 |
| B0_group_mean | U_unconstrained | establishments | M6_rare_industry | 0.6818248941352464 | 0.7657215989648681 | 30 |

## 21. Placebo

| target_name | model_id | track | placebo_type | iterations | actual_model_wmape | placebo_p05_wmape | placebo_mean_wmape | pass_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| establishments | M1_hierarchical_ridge | U_unconstrained | P1_region_feature_placebo | 100 | 0.7797111261545489 | 0.8398101090453263 | 0.8501806752460211 | pass |
| establishments | M1_hierarchical_ridge | U_unconstrained | P3_industry_label_placebo | 100 | 0.7797111261545489 | 0.8398395921837621 | 0.8514722266280564 | pass |
| establishments | M1_hierarchical_ridge | U_unconstrained | P4_temporal_placebo | 100 | 0.7797111261545489 | 0.8401893661903564 | 0.8501533230264344 | pass |
| establishments | M1_hierarchical_ridge | U_unconstrained | P6_noise_feature | 100 | 0.7797111261545489 | 0.8387957025016216 | 0.8496675831792903 | pass |
| employees | M1_hierarchical_ridge | U_unconstrained | P1_region_feature_placebo | 100 | 0.7961465791087021 | 0.8543977498620995 | 0.8679368325773654 | pass |
| employees | M1_hierarchical_ridge | U_unconstrained | P3_industry_label_placebo | 100 | 0.7961465791087021 | 0.8581404463266991 | 0.8693261889988884 | pass |
| employees | M1_hierarchical_ridge | U_unconstrained | P4_temporal_placebo | 100 | 0.7961465791087021 | 0.8537117046943108 | 0.8670521038404212 | pass |
| employees | M1_hierarchical_ridge | U_unconstrained | P6_noise_feature | 100 | 0.7961465791087021 | 0.8580953633032901 | 0.86897778735641 | pass |

## 22. Selection-aware Bootstrap

| target_name | selected_model | selected_reconciliation | selected_baseline | selection_count | selection_share | bootstrap_iterations | P_cell_improve | P_aggregate_improve | median_cell_wmape_delta | p05_cell_wmape_delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| employees | M1_hierarchical_ridge | U_unconstrained | B3_latest_observed_share | 2000 | 1.0 | 2000 | 0.445 | 0.445 | -0.004698889412086016 | -0.05665606698636694 |
| establishments | M1_hierarchical_ridge | U_unconstrained | B3_latest_observed_share | 2000 | 1.0 | 2000 | 0.0 | 0.0 | -0.16182490105144148 | -0.2062768328437518 |

## 23. Prediction Interval

_No rows_
_No rows_

## 24. Support 및 Extrapolation

| target_name | support_level | cells |
| --- | --- | --- |
| employees | S4_not_estimable | 12990 |
| employees | observed_official | 6846 |
| establishments | S4_not_estimable | 9162 |
| establishments | observed_official | 10674 |

## 25. 사업체 수 최종 판정

| target_name | best_baseline_model | best_baseline_track | best_baseline_mean_repeat_wmape | best_candidate_model | best_candidate_track | best_candidate_mean_repeat_wmape | relative_improvement | primary_mask_pass_count | region_block_baseline_wmape | region_block_candidate_wmape | region_block_pass | material_degradation_gate | provisional_grade_recalculated | production_use | confirmatory_claim |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| establishments | B3_latest_observed_share | U_unconstrained | 0.6184526489126286 | M1_hierarchical_ridge | U_unconstrained | 0.7797111261545489 | -0.2607450667815021 | 2 | 0.6139345320056102 | 0.7156346884456134 | N | N | D | false | false |

## 26. 종사자 수 최종 판정

| target_name | best_baseline_model | best_baseline_track | best_baseline_mean_repeat_wmape | best_candidate_model | best_candidate_track | best_candidate_mean_repeat_wmape | relative_improvement | primary_mask_pass_count | region_block_baseline_wmape | region_block_candidate_wmape | region_block_pass | material_degradation_gate | provisional_grade_recalculated | production_use | confirmatory_claim |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| employees | B3_latest_observed_share | U_unconstrained | 0.7906011455193714 | M1_hierarchical_ridge | U_unconstrained | 0.7961465791087021 | -0.0070141987786872095 | 4 | 0.7199629675464825 | 0.6326846184968286 | Y | Y | D | false | false |

## 27. 미공개 Cell 추정

- 관측 공식값은 유지하고, Grade B 이상으로 재판정된 target에 대해서만 `S1_in_support_interpolation` 셀을 생성했다.
- Grade C/D 또는 calibration review 셀은 운영 배포 대상이 아니다.

## 28. Aggregate Validation

| source_region | industry_code | period | target_name | estimated_total |
| --- | --- | --- | --- | --- |
| 강원특별자치도 | B05 | 2021 | employees | 1163.0 |
| 강원특별자치도 | B05 | 2021 | establishments | 9.0 |
| 강원특별자치도 | B05 | 2022 | employees | 981.0 |
| 강원특별자치도 | B05 | 2022 | establishments | 7.0 |
| 강원특별자치도 | B05 | 2023 | employees | 989.0 |
| 강원특별자치도 | B05 | 2023 | establishments | 5.0 |
| 강원특별자치도 | B06 | 2021 | employees | 0.0 |
| 강원특별자치도 | B06 | 2021 | establishments | 2.0 |
| 강원특별자치도 | B06 | 2022 | employees | 0.0 |
| 강원특별자치도 | B06 | 2022 | establishments | 3.0 |
| 강원특별자치도 | B06 | 2023 | employees | 0.0 |
| 강원특별자치도 | B06 | 2023 | establishments | 3.0 |

## 29. 한계

- 독립 constraint는 section-level parent total이므로 중분류 내부 배분의 진실을 직접 보장하지 않는다.
- 2,000회 bootstrap은 frozen mask outcome 위에서 selection 절차를 재표집한 안정성 감사이며, 새 표본 원표가 아닌 개발용 검증이다.
- Count GLM, Matrix completion, Spatial regularization은 전체 mask 재실행 가능성을 위해 fast-screening/proxy 형태로 구현했다. 이 후보들이 Grade를 통과하려면 별도 정교화가 필요하다.
- Spatial regularization은 현재 Queen/Nearest-5의 완전한 graph penalty가 아니라 보수적 spatial proxy다.
- 동일 actual을 사용한 개발 검증이므로 confirmatory claim은 금지된다.

## 30. 다음 검증계획

1. 전산업 시군구 원표와 인구·사업체 총량 feature를 확보해 B1/B6를 완전 실행한다.
2. 독립 parent total의 release date와 vintage를 보강해 예측시점 기준 데이터 유출 방지 레이어를 추가한다.
3. Region Block 실패 target은 지역 일반화 모델 구조를 새 actual 공개 전까지 추가 튜닝하지 않는다.
4. 다음 공식 세부통계가 공개되면 preconfirmatory holdout으로 현재 frozen policy를 검증한다.
