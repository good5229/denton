# Partial Statistics Estimation Phase 13-GVA

## 1. 실행 요약

Phase 13 converts Phase 12's repeated origin labels into an explicit origin-identity audit and a chronology-incomplete sensitivity experiment with genuinely changing as-of feature hashes.

| status | target | target_years | origin_count | model_count | independent_origin_count | collapsed_origin_count | independent_model_origin_count | collapsed_model_origin_count | feature_hash_unique_count | prediction_hash_unique_count | monthly_primary_status | strict_vintage_status | sensitivity_track | actual_used_for_selection | production_use | official_statistics_claim | generated_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| strict_vintage_blocked_sensitivity_completed | GVA | [2022, 2023] | 8 | 6 | 8 | 0 | 48 | 0 | 8 | 26 | blocked_no_eligible_monthly_source | blocked_current_snapshot_release_assumptions | completed | False | False | False | 2026-07-18T16:50:40+09:00 |

## 2. Phase 12 판정 반영

Phase 12 restored GVA as the primary target, but its prediction origins collapsed because the same parent-share prediction was repeated across origin labels. This report treats that as a limitation, not as evidence of true multi-origin performance.

## 3. Observation Release Ledger

| source_id | source_file | observation_period | observation_year | release_date | first_eligible_origin | vintage_id | revision_date | availability_confidence | region_name | industry_code | industry_name | metric | value | strict_track_eligible | region_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2021Q1 | 2021 | 2021-05-28 | 2021-05-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 103.6 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2021Q2 | 2021 | 2021-08-28 | 2021-08-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 108 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2021Q3 | 2021 | 2021-11-28 | 2021-11-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 107.7 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2021Q4 | 2021 | 2022-02-28 | 2022-02-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 115.5 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2022Q1 | 2022 | 2022-05-28 | 2022-05-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 110.2 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2022Q2 | 2022 | 2022-08-28 | 2022-08-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 114.2 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2022Q3 | 2022 | 2022-11-28 | 2022-11-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 107.1 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2022Q4 | 2022 | 2023-02-28 | 2023-02-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 107.7 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2023Q1 | 2023 | 2023-05-28 | 2023-05-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 100.8 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2023Q2 | 2023 | 2023-08-28 | 2023-08-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 107.2 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2023Q3 | 2023 | 2023-11-28 | 2023-11-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 106.8 | N |  |
| mining_manufacturing_production_index | mining_manufacturing_production_index.csv | 2023Q4 | 2023 | 2024-02-28 | 2024-02-28 | mining_manufacturing_production_index:assumed_lag_current_snapshot |  | C_assumed_release_lag_current_snapshot | 전국 | C | 제조업 | 생산지수(원지수) | 113.3 | N |  |

## 4. Origin Information Growth

| target_year | origin_id | prediction_origin | eligible_source_count | eligible_observation_count | latest_available_observation_period | feature_count | nonmissing_feature_count | feature_content_hash | strict_track_status | eligible_observation_delta | feature_hash_changed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O1 | 2022-03-31 | 4 | 17304 | 2021Q4 | 8 | 10650 | 841e8df4e05f54a39ac94f6dda34cc4a9690936f33fdf44504a7944a1a1934ff | blocked_current_snapshot_release_assumptions | 0 | True |
| 2022 | O2 | 2022-06-30 | 4 | 17560 | 2022Q1 | 8 | 10650 | 4fd776c91f5c4123115964d039aeaed8f00645247343e18395070cbe162ae634 | blocked_current_snapshot_release_assumptions | 256 | True |
| 2022 | O3 | 2022-09-30 | 4 | 17816 | 2022Q2 | 8 | 10650 | aa5f5c0df4074668f7bc96cdd51662c88d993c46b1ecb98da8d2904014be9d1c | blocked_current_snapshot_release_assumptions | 256 | True |
| 2022 | O4 | 2022-12-31 | 4 | 18072 | 2022Q3 | 8 | 10650 | 58c4d217d9f3a058963bc43adad1216073d016148771d2e04f4ddfa9fcf11efd | blocked_current_snapshot_release_assumptions | 256 | True |
| 2023 | O1 | 2023-03-31 | 4 | 19297 | 2022Q4 | 8 | 6891 | 8f91f8279a95d536936b830692c9ed18fc5b1b4b900c16524e625759c7fbbe16 | blocked_current_snapshot_release_assumptions | 0 | True |
| 2023 | O2 | 2023-06-30 | 4 | 19553 | 2023Q1 | 8 | 6891 | b992f24381dd7c9ea3903920387ec1ac31132e67fa2a78ca2264a5f725fcd8a9 | blocked_current_snapshot_release_assumptions | 256 | True |
| 2023 | O3 | 2023-09-30 | 4 | 19809 | 2023Q2 | 8 | 6891 | 3679d69383bdbeb903d51aca4696324982b184ca9db631b2276dabb5f13fe65c | blocked_current_snapshot_release_assumptions | 256 | True |
| 2023 | O4 | 2023-12-31 | 4 | 20065 | 2023Q3 | 8 | 6891 | d0aa34c524e259c68513a49102b06c6e547dc9d8cd5990a80b529d16ca8d3b89 | blocked_current_snapshot_release_assumptions | 256 | True |

## 5. Origin Collapse Audit

| target_year | origin_id | prediction_origin | model_id | eligible_source_hash | feature_content_hash | model_config_hash | prediction_hash | collapse_group_id | independent_origin | origin_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O1 | 2022-03-31 | B0_parent_share | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | 841e8df4e05f54a39ac94f6dda34cc4a9690936f33fdf44504a7944a1a1934ff | fd439fb57869aebeec3b499436a7d7afe4c544d18bbfeb51ba9ca411b6565dd7 | 0d3a725bf3b576a4479f71bec6016b6aa7201feba41028e3ce76a8d3e98799ee | CG0002 | True | independent_origin |
| 2022 | O2 | 2022-06-30 | B0_parent_share | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | 4fd776c91f5c4123115964d039aeaed8f00645247343e18395070cbe162ae634 | fd439fb57869aebeec3b499436a7d7afe4c544d18bbfeb51ba9ca411b6565dd7 | 0d3a725bf3b576a4479f71bec6016b6aa7201feba41028e3ce76a8d3e98799ee | CG0000 | True | independent_origin |
| 2022 | O3 | 2022-09-30 | B0_parent_share | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | aa5f5c0df4074668f7bc96cdd51662c88d993c46b1ecb98da8d2904014be9d1c | fd439fb57869aebeec3b499436a7d7afe4c544d18bbfeb51ba9ca411b6565dd7 | 0d3a725bf3b576a4479f71bec6016b6aa7201feba41028e3ce76a8d3e98799ee | CG0003 | True | independent_origin |
| 2022 | O4 | 2022-12-31 | B0_parent_share | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | 58c4d217d9f3a058963bc43adad1216073d016148771d2e04f4ddfa9fcf11efd | fd439fb57869aebeec3b499436a7d7afe4c544d18bbfeb51ba9ca411b6565dd7 | 0d3a725bf3b576a4479f71bec6016b6aa7201feba41028e3ce76a8d3e98799ee | CG0001 | True | independent_origin |
| 2023 | O1 | 2023-03-31 | B0_parent_share | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | 8f91f8279a95d536936b830692c9ed18fc5b1b4b900c16524e625759c7fbbe16 | fd439fb57869aebeec3b499436a7d7afe4c544d18bbfeb51ba9ca411b6565dd7 | d23f6cc254163e376edb78651cf3ee4230a65174c4ce4ade1a3077bb04f4f88b | CG0025 | True | independent_origin |
| 2023 | O2 | 2023-06-30 | B0_parent_share | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | b992f24381dd7c9ea3903920387ec1ac31132e67fa2a78ca2264a5f725fcd8a9 | fd439fb57869aebeec3b499436a7d7afe4c544d18bbfeb51ba9ca411b6565dd7 | d23f6cc254163e376edb78651cf3ee4230a65174c4ce4ade1a3077bb04f4f88b | CG0026 | True | independent_origin |
| 2023 | O3 | 2023-09-30 | B0_parent_share | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | 3679d69383bdbeb903d51aca4696324982b184ca9db631b2276dabb5f13fe65c | fd439fb57869aebeec3b499436a7d7afe4c544d18bbfeb51ba9ca411b6565dd7 | d23f6cc254163e376edb78651cf3ee4230a65174c4ce4ade1a3077bb04f4f88b | CG0024 | True | independent_origin |
| 2023 | O4 | 2023-12-31 | B0_parent_share | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | d0aa34c524e259c68513a49102b06c6e547dc9d8cd5990a80b529d16ca8d3b89 | fd439fb57869aebeec3b499436a7d7afe4c544d18bbfeb51ba9ca411b6565dd7 | d23f6cc254163e376edb78651cf3ee4230a65174c4ce4ade1a3077bb04f4f88b | CG0027 | True | independent_origin |
| 2022 | O1 | 2022-03-31 | M1_direct_growth | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | 841e8df4e05f54a39ac94f6dda34cc4a9690936f33fdf44504a7944a1a1934ff | eb1f2d18f0e353b3e849bbd321e35c13329aa67d35888ec5d1e62e858a447eb6 | 75596b392c5c9a7809619b1481b2d079e7a31caab66e9e7d4d5f45123ee51e1b | CG0006 | True | independent_origin |
| 2022 | O2 | 2022-06-30 | M1_direct_growth | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | 4fd776c91f5c4123115964d039aeaed8f00645247343e18395070cbe162ae634 | eb1f2d18f0e353b3e849bbd321e35c13329aa67d35888ec5d1e62e858a447eb6 | 61202b8b2828d7491906cad55fb90f74df9448c13c22ec1bd96bc77701b126da | CG0004 | True | independent_origin |
| 2022 | O3 | 2022-09-30 | M1_direct_growth | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | aa5f5c0df4074668f7bc96cdd51662c88d993c46b1ecb98da8d2904014be9d1c | eb1f2d18f0e353b3e849bbd321e35c13329aa67d35888ec5d1e62e858a447eb6 | a135fb4e31e8b0074083d76b57d2ef0c93a6234c1d97a3f4fea1fbf5ea53c3d5 | CG0007 | True | independent_origin |
| 2022 | O4 | 2022-12-31 | M1_direct_growth | 3addca3fd76dd146e43e46c6724be863e570d184e237cbf28dc0f9e5fca25613 | 58c4d217d9f3a058963bc43adad1216073d016148771d2e04f4ddfa9fcf11efd | eb1f2d18f0e353b3e849bbd321e35c13329aa67d35888ec5d1e62e858a447eb6 | 76c1aa022824e5cd6db99e470e2b6ec7b6cea5fb3fdf1d50fe70a3ca9522508d | CG0005 | True | independent_origin |

## 6. Model Results

| target_year | origin_id | prediction_origin | model_id | model_family | wmape | pooled_wmape | mae | median_absolute_error | rmsle | median_ape | p90_ape | poisson_deviance | actual_sum | prediction_sum | n | evaluation_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O1 | 2022-03-31 | B0_parent_share | parent_share | 0.09712282457331847 | 0.09712282457331847 | 55459.140597253805 | 11535.340992500041 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 12861.96648602605 | 2027123387.1665812 | 2092014218.1060982 | 3550 | outer_evaluation_sensitivity |
| 2022 | O2 | 2022-06-30 | B0_parent_share | parent_share | 0.09712282457331847 | 0.09712282457331847 | 55459.140597253805 | 11535.340992500041 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 12861.96648602605 | 2027123387.1665812 | 2092014218.1060982 | 3550 | outer_evaluation_sensitivity |
| 2022 | O3 | 2022-09-30 | B0_parent_share | parent_share | 0.09712282457331847 | 0.09712282457331847 | 55459.140597253805 | 11535.340992500041 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 12861.96648602605 | 2027123387.1665812 | 2092014218.1060982 | 3550 | outer_evaluation_sensitivity |
| 2022 | O4 | 2022-12-31 | B0_parent_share | parent_share | 0.09712282457331847 | 0.09712282457331847 | 55459.140597253805 | 11535.340992500041 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 12861.96648602605 | 2027123387.1665812 | 2092014218.1060982 | 3550 | outer_evaluation_sensitivity |
| 2023 | O1 | 2023-03-31 | B0_parent_share | parent_share | 0.07967679907924165 | 0.07967679907924165 | 53638.25587498302 | 10965.33166799997 | 0.35397760661170186 | 0.06488731566492892 | 0.3250588546392832 | 13168.838285202915 | 1546335635.575694 | 1536586261.881776 | 2297 | outer_evaluation_sensitivity |
| 2023 | O2 | 2023-06-30 | B0_parent_share | parent_share | 0.07967679907924165 | 0.07967679907924165 | 53638.25587498302 | 10965.33166799997 | 0.35397760661170186 | 0.06488731566492892 | 0.3250588546392832 | 13168.838285202915 | 1546335635.575694 | 1536586261.881776 | 2297 | outer_evaluation_sensitivity |
| 2023 | O3 | 2023-09-30 | B0_parent_share | parent_share | 0.07967679907924165 | 0.07967679907924165 | 53638.25587498302 | 10965.33166799997 | 0.35397760661170186 | 0.06488731566492892 | 0.3250588546392832 | 13168.838285202915 | 1546335635.575694 | 1536586261.881776 | 2297 | outer_evaluation_sensitivity |
| 2023 | O4 | 2023-12-31 | B0_parent_share | parent_share | 0.07967679907924165 | 0.07967679907924165 | 53638.25587498302 | 10965.33166799997 | 0.35397760661170186 | 0.06488731566492892 | 0.3250588546392832 | 13168.838285202915 | 1546335635.575694 | 1536586261.881776 | 2297 | outer_evaluation_sensitivity |
| 2022 | O1 | 2022-03-31 | M1_direct_growth | direct_growth | 0.09489817221521187 | 0.09489817221521187 | 54188.81811177966 | 11497.108120301491 | 0.3011402791188838 | 0.0731603385303575 | 0.3267908431631806 | 12249.649494089683 | 2027123387.1665812 | 2087029551.9353304 | 3550 | outer_evaluation_sensitivity |
| 2022 | O2 | 2022-06-30 | M1_direct_growth | direct_growth | 0.10399297892179299 | 0.10399297892179299 | 59382.14075309518 | 11485.117191322235 | 0.3021883419624232 | 0.07800756555808731 | 0.3354644343636447 | 13458.73056122371 | 2027123387.1665812 | 2139804655.9263465 | 3550 | outer_evaluation_sensitivity |
| 2022 | O3 | 2022-09-30 | M1_direct_growth | direct_growth | 0.10939612075317576 | 0.10939612075317576 | 62467.446434947036 | 12293.34074235207 | 0.3043219366729741 | 0.08587746058775389 | 0.34034507957488325 | 14030.228793600265 | 2027123387.1665812 | 2163094970.92967 | 3550 | outer_evaluation_sensitivity |
| 2022 | O4 | 2022-12-31 | M1_direct_growth | direct_growth | 0.10837713057185058 | 0.10837713057185058 | 61885.58197639566 | 12510.240828678798 | 0.3047271598161349 | 0.08569858667144278 | 0.34121322079522237 | 13954.631430639567 | 2027123387.1665812 | 2159453739.964423 | 3550 | outer_evaluation_sensitivity |

## 7. Forecast Revision

| target_year | model_id | cell_id | origin_id | previous_origin_id | prediction | revision_from_previous_origin | absolute_revision | relative_revision | actual_direction_match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/A00 | O1 |  | 140588.536463 |  |  |  |  |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/A00 | O2 | O1 | 140588.536463 | 0.0 | 0.0 | 0.0 | False |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/A00 | O3 | O2 | 140588.536463 | 0.0 | 0.0 | 0.0 | False |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/A00 | O4 | O3 | 140588.536463 | 0.0 | 0.0 | 0.0 | False |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/B00 | O1 |  | 11146.797001 |  |  |  |  |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/B00 | O2 | O1 | 11146.797001 | 0.0 | 0.0 | 0.0 | False |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/B00 | O3 | O2 | 11146.797001 | 0.0 | 0.0 | 0.0 | False |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/B00 | O4 | O3 | 11146.797001 | 0.0 | 0.0 | 0.0 | False |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/C00 | O1 |  | 622293.721254 |  |  |  |  |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/C00 | O2 | O1 | 622293.721254 | 0.0 | 0.0 | 0.0 | False |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/C00 | O3 | O2 | 622293.721254 | 0.0 | 0.0 | 0.0 | False |
| 2022 | B0_parent_share | 2022/강원특별자치도/32010/C00 | O4 | O3 | 622293.721254 | 0.0 | 0.0 | 0.0 | False |

## 8. Monthly Activity Decision

| source_id | frequency | historical_2022_2023_available | primary_monthly_eligible | reason |
| --- | --- | --- | --- | --- |
| kepco_sigungu_electricity_long.csv | monthly | N | N | local file starts after historical evaluation years |
| mining_manufacturing_production_index.csv | quarterly | Y | N | quarterly source cannot justify monthly primary estimate alone |
| service_production_index.csv | quarterly | Y | N | quarterly source cannot justify monthly primary estimate alone |

## 9. Interval Diagnostics

| target_year | origin_id | model_id | coverage_80 | coverage_95 | mean_width_80 | mean_width_95 | calibration_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O1 | B0_parent_share | 0.8 | 0.9498591549295775 | 98694.84637584387 | 397586.58612353774 | posthoc_diagnostic_not_deployable |
| 2022 | O2 | B0_parent_share | 0.8 | 0.9498591549295775 | 98694.84637584387 | 397586.58612353774 | posthoc_diagnostic_not_deployable |
| 2022 | O3 | B0_parent_share | 0.8 | 0.9498591549295775 | 98694.84637584387 | 397586.58612353774 | posthoc_diagnostic_not_deployable |
| 2022 | O4 | B0_parent_share | 0.8 | 0.9498591549295775 | 98694.84637584387 | 397586.58612353774 | posthoc_diagnostic_not_deployable |
| 2023 | O1 | B0_parent_share | 0.7997387897257292 | 0.9499346974314323 | 93413.73126341059 | 384243.4838073017 | posthoc_diagnostic_not_deployable |
| 2023 | O2 | B0_parent_share | 0.7997387897257292 | 0.9499346974314323 | 93413.73126341059 | 384243.4838073017 | posthoc_diagnostic_not_deployable |
| 2023 | O3 | B0_parent_share | 0.7997387897257292 | 0.9499346974314323 | 93413.73126341059 | 384243.4838073017 | posthoc_diagnostic_not_deployable |
| 2023 | O4 | B0_parent_share | 0.7997387897257292 | 0.9499346974314323 | 93413.73126341059 | 384243.4838073017 | posthoc_diagnostic_not_deployable |
| 2022 | O1 | M1_direct_growth | 0.8 | 0.9498591549295775 | 98263.99766639931 | 393073.2297339449 | posthoc_diagnostic_not_deployable |
| 2022 | O2 | M1_direct_growth | 0.8 | 0.9498591549295775 | 109155.9683580337 | 429260.7836293161 | posthoc_diagnostic_not_deployable |
| 2022 | O3 | M1_direct_growth | 0.8 | 0.9498591549295775 | 118807.70174075072 | 445837.6764589291 | posthoc_diagnostic_not_deployable |
| 2022 | O4 | M1_direct_growth | 0.8 | 0.9498591549295775 | 118810.33645280865 | 447555.89202924387 | posthoc_diagnostic_not_deployable |

## 10. Current 2025 and 2026 Estimates

2025 estimates are carried forward from the Phase 12 reconciled quarterly cube. 2026 remains a baseline scenario, not a current-indicator nowcast.

## 11. 최종 결론

1. 실제 독립 Origin 수: 8
2. Collapsed Origin 수: 0
3. Origin별 Source 증가량: see `partial_stats_phase13_gva_origin_information_growth.csv`.
4. Origin별 Feature Hash 차이: 8 unique hashes.
5. Origin별 Prediction Hash 차이: 26 unique hashes.
6. 2022 Early/Mid/Late 성능: recorded in origin accuracy.
7. 2023 Early/Mid/Late 성능: recorded in origin accuracy.
8. Early-to-late 개선: diagnostic only; actual was not used for model selection.
9. Forecast Revision 안정성: recorded in revision results.
10. Parent-share 성능: baseline retained.
11. Direct GVA 성능: independently executed as direct growth sensitivity model.
12. Employee Productivity 성능: independently executed with lagged employee features.
13. Establishment Productivity 성능: independently executed with lagged establishment features.
14. Proxy Residual 성능: independently executed with bounded proxy correction.
15. 월별 Activity Source: no eligible 2022-2023 region-industry monthly source.
16. 월별 Placeholder 여부: monthly output remains placeholder-only.
17. Origin별 Interval Coverage: posthoc diagnostic only, not deployable calibration.
18. 2025 GVA 수정 결과: carried from Phase 12 reconciled quarterly cube.
19. 2026 Nowcast 수정 결과: baseline scenario only.
20. 아직 주장할 수 없는 내용: strict official vintage performance, production/official statistics use, 2025 actual performance, and activity-based monthly nowcast.
