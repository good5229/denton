# Phase33 RQ1 Compatibility

## 1. Cardinality

| dimension | value | interpretation | is_17_by_20 | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| row_count | 340 | primary RQ1 evaluation rows | Y | 3715ce03f895f138500383c163f21f2183cdd294604f60ef69560d40ae18ddd8 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| region | 17 | region_code | Y | 3715ce03f895f138500383c163f21f2183cdd294604f60ef69560d40ae18ddd8 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| region_name | 17 | region_name | Y | 3715ce03f895f138500383c163f21f2183cdd294604f60ef69560d40ae18ddd8 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| period | 0 | missing | Y | 3715ce03f895f138500383c163f21f2183cdd294604f60ef69560d40ae18ddd8 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| industry | 4 | official_industry_group | Y | 3715ce03f895f138500383c163f21f2183cdd294604f60ef69560d40ae18ddd8 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| unique_key | 0 | region×period | Y | 3715ce03f895f138500383c163f21f2183cdd294604f60ef69560d40ae18ddd8 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| duplicate_key | 0 | region×period duplicates | Y | 3715ce03f895f138500383c163f21f2183cdd294604f60ef69560d40ae18ddd8 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |

## 2. Compatibility

| bridge_id | tq3_semantics | rq1_semantics | region_compatibility | industry_compatibility | period_compatibility | concept_compatibility | price_basis_compatibility | decision | allowed_use | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TQ3_quarter_share_to_RQ1_real_yoy | service_index_quarter_share | total_GRDP_real_YoY_growth | sido | fail_RQ1_has_no_service_industry_axis | quarter | fail_share_vs_growth | not_directly_comparable | Retired | none | b3eef211de04959c87e0186c415a3d6225bcefa1776d9f1a4a7d9c2f18d3031c | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| service_composite_yoy_to_RQ1_total_grdp_yoy | service_index_equal_weight_composite_YoY | total_GRDP_real_YoY_growth | sido | aggregate_only | quarter | direction_only_external_validation | index_current_price_vs_real_growth_mismatch | Retained | external_direction_diagnostic_not_direct_accuracy | b3eef211de04959c87e0186c415a3d6225bcefa1776d9f1a4a7d9c2f18d3031c | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |

## 3. Correction

The 340 rows are 17 regions × 4 broad groups × 5 periods, not 17×20. Service aggregate direction can be checked, but service-series direct accuracy cannot.
