# Phase33 Final Executive Decision

## 1. Final status

```json
{
  "status": "phase33_final_completed;reproduction_passed;industry_dimension_repaired;share_lineage_passed;eligibility_passed;product_a1_retained;product_a2_retained;rq1_bridge_aggregate_only;product_b_proxy_retained;product_c_allocation_retained;product_d_blocked;confirmatory_missing;reliability_evidence_only;unresolved_decisions_0;private_paid_data_false;production_use_false;official_statistics_claim_false",
  "target": "RECI-LF supported marginal products",
  "phase32_reproduction_passed": true,
  "phase32_current_product_retired": true,
  "product_a1_rows": 55438,
  "product_a2_rows": 12536,
  "product_b_rows": 13804,
  "product_c_rows": 76266,
  "product_d_rows": 0,
  "confirmatory_c_count": 0,
  "unresolved_decision_count": 0,
  "paid_private_source_used": false,
  "production_use": false,
  "official_statistics_claim": false,
  "generated_at": "2026-07-20T02:17:43+09:00"
}
```

## 2. Product decisions

| product_id | product_name | effective_grain | decision | allowed_claim | prohibited_claim | evidence_grade | production_use | official_statistics_claim | unavailable_reason | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Local Spatial Structure | emd_admin_2015×KSIC_section×snapshot | Retained | historical public spatial structure proxy | EMD GVA or current industry structure | D | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| A2 | Fine Industry Structure | sigungu×KSIC_middle×annual | Retained | middle-industry composition/LQ | direct fine GVA accuracy | D | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| B | Temporal Service Signal | sido×service_series×quarter | Retained | observed official service activity index | fine GVA RECI | O_proxy | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| C | GVA-consistent Allocation | emd_admin_2015×project_broad×annual | Retained | parent-consistent allocation | observed EMD GVA | D | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| D | Joint Local/Fine/Temporal | local×fine×time | Blocked | none | any joint value | U | false | false | interaction evidence absent | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| A32 | Phase32 Current Spatial Product | Seoul_EMD×project_broad×2024_snapshot | Retired | none | industry-specific current spatial structure | U | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| C32 | Phase32 Current GVA Allocation | Seoul_EMD×project_broad×2024_snapshot | Retired | none | industry-specific current allocation | U | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |

## 3. Critical finding

Phase32 current EMD×industry vectors were mostly duplicated across industries. Those products are retired; only the repaired evidence-supported marginal products remain.

## 4. What is trustworthy

A1 is a dated historical spatial-structure proxy, A2 is a sigungu fine-industry structure proxy, B is an observed service activity signal, and C is an accounting-consistent allocation. None is official EMD fine GVA.

## 5. What is unavailable

A current nationwide EMD×section product, direct EMD GVA accuracy, calibrated confidence, and EMD×middle×quarter joint estimates are unavailable.
