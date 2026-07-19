# Phase33 Commercial PoC

## 1. Product catalog

| product_id | product_name | effective_grain | decision | allowed_claim | prohibited_claim | evidence_grade | production_use | official_statistics_claim | unavailable_reason | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Local Spatial Structure | emd_admin_2015×KSIC_section×snapshot | Retained | historical public spatial structure proxy | EMD GVA or current industry structure | D | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| A2 | Fine Industry Structure | sigungu×KSIC_middle×annual | Retained | middle-industry composition/LQ | direct fine GVA accuracy | D | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| B | Temporal Service Signal | sido×service_series×quarter | Retained | observed official service activity index | fine GVA RECI | O_proxy | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| C | GVA-consistent Allocation | emd_admin_2015×project_broad×annual | Retained | parent-consistent allocation | observed EMD GVA | D | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| D | Joint Local/Fine/Temporal | local×fine×time | Blocked | none | any joint value | U | false | false | interaction evidence absent | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| A32 | Phase32 Current Spatial Product | Seoul_EMD×project_broad×2024_snapshot | Retired | none | industry-specific current spatial structure | U | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| C32 | Phase32 Current GVA Allocation | Seoul_EMD×project_broad×2024_snapshot | Retired | none | industry-specific current allocation | U | false | false |  | 82077509217b25b8aeafe73fe30db1f14a627c1daf4d06c54713921362074f2a | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |

## 2. Supported scenarios

A1 historical EMD industry structure, A2 sigungu fine-industry structure, B sido service time signal, and C parent-consistent annual allocation are supported with explicit grain and evidence labels.

## 3. Unsupported scenario

EMD×middle×quarter requests return unavailable because Product D is blocked.
