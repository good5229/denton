# Phase33 Reliability and Uncertainty

## 1. Calibration

| product_id | evidence_status | numerical_reliability_status | calibration_reason | user_display_policy | holdout_error_monotonicity | confidence_score | interval_coverage | development_confidence_user_visible | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | development_evidence_only | not_calibrated | new independent holdout missing | do_not_show_numeric_confidence | not_testable |  |  | N | ab34111d19455dd64f6da6815a297f18871f00f62de7b5da21fe87b96340565f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| A2 | development_evidence_only | not_calibrated | fine composition holdout missing | show source family and freshness only | not_testable |  |  | N | ab34111d19455dd64f6da6815a297f18871f00f62de7b5da21fe87b96340565f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| B | observed_proxy | not_GVA_calibrated | observed service index; no compatible fine GVA target | show observed proxy status | not_testable |  |  | N | ab34111d19455dd64f6da6815a297f18871f00f62de7b5da21fe87b96340565f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| C | allocation_evidence_only | not_calibrated | allocation uncertainty not empirically identified | show weakest component D | not_testable |  |  | N | ab34111d19455dd64f6da6815a297f18871f00f62de7b5da21fe87b96340565f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| D | unavailable | blocked | interaction evidence missing | show unavailable reason | not_testable |  |  | N | ab34111d19455dd64f6da6815a297f18871f00f62de7b5da21fe87b96340565f | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |

## 2. Decision

Numerical confidence and prediction intervals are not exposed without monotonic holdout calibration.
