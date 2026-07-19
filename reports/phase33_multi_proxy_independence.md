# Phase33 Multi-proxy Independence

## 1. Scorecard

| product_id | sources | source_families | independent_family_count | independence_interpretation | validation_scope | decision | c_promotion_allowed | leave_one_family_out_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | business_count;employee_count | economic_census_2015 | 1 | same census family | composition agreement descriptive only | Retained | N | not_identified_for_C_promotion | 38b21781a9773d8c63cc37ac61a4d061f5eec473020f5bcd5eeb3c716b47e56f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| A2_all | business_count;employee_count | manufacturing_mining_sigungu_ksic | 1 | same KOSIS table family | no independent fine composition target | Retained | N | not_identified_for_C_promotion | 38b21781a9773d8c63cc37ac61a4d061f5eec473020f5bcd5eeb3c716b47e56f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| A2_manufacturing_presence | business/employment;factory | manufacturing_mining_sigungu_ksic;factory_admin_snapshot | 2 | independent broad presence only | factory cannot validate middle-industry shares | Retained | N | not_identified_for_C_promotion | 38b21781a9773d8c63cc37ac61a4d061f5eec473020f5bcd5eeb3c716b47e56f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| B | service_index;RQ1_service_growth | service_production_index;official_quarterly_grdp_release | 2 | independent but semantic mismatch | external direction diagnostic only | Retained | N | not_identified_for_C_promotion | 38b21781a9773d8c63cc37ac61a4d061f5eec473020f5bcd5eeb3c716b47e56f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| C | A1_share;official_sigungu_GVA | economic_census_2015;official_sigungu_GVA | 2 | independent accounting inputs | no direct EMD GVA accuracy target | Retained | N | not_identified_for_C_promotion | 38b21781a9773d8c63cc37ac61a4d061f5eec473020f5bcd5eeb3c716b47e56f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| D | none | none | 0 | interaction source absent | no joint rows generated | Blocked | N | not_identified_for_C_promotion | 38b21781a9773d8c63cc37ac61a4d061f5eec473020f5bcd5eeb3c716b47e56f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |

## 2. Decision

Independent family count alone is not enough when grain or concept differs; no component is promoted to confirmatory C.
