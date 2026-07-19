# Phase33 Reproduction and Freeze

## 1. Phase32 reproduction

| metric | expected | observed | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| corrected_shadow_row_count | 6579 | 6579 | pass | dbfe84068606261f5490d9a2ff29aa7d9f974479dcc1c4cb23dd8721444dc6ff | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| product_a_row_count | 6529 | 6529 | pass | dbfe84068606261f5490d9a2ff29aa7d9f974479dcc1c4cb23dd8721444dc6ff | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| product_b_row_count | 0 | 0 | pass | dbfe84068606261f5490d9a2ff29aa7d9f974479dcc1c4cb23dd8721444dc6ff | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| product_c_row_count | 6529 | 6529 | pass | dbfe84068606261f5490d9a2ff29aa7d9f974479dcc1c4cb23dd8721444dc6ff | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| runtime | recorded | {"python": "3.10.2", "platform": "macOS-14.5-arm64-arm-64bit", "locale_policy": "CSV=cp949; markdown/json=utf-8", "timezone": "KST", "random_seed": 20260720, "code_commit_hash": "510c8c96d97b5bb0c1e409466478d006c49b0bd0", "generated_at": "2026-07-20T02:17:43+09:00"} | pass | dbfe84068606261f5490d9a2ff29aa7d9f974479dcc1c4cb23dd8721444dc6ff | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |

## 2. Frozen manifest

| artifact | exists | size_bytes | sha256 | role | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data/processed/partial_stats_phase27_gva_final_status.json | Y | 4229 | d98dac18761204ac60aec0b06b415c92b18701cda5fb59082a2d6f10f40e411f | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| data/processed/partial_stats_phase28_gva_final_status.json | Y | 4954 | 1c0531920b0d90b1918623709abedb7003e320e9ac646e2f6bae23c06855c986 | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| data/processed/partial_stats_phase29_gva_final_status.json | Y | 1516 | babc8ceb82e1d05f9a49a4eb745ddb6d47dc1e6772447c9f0483e5ae6cbb2f26 | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| data/derived/phase30_final_status.json | Y | 1011 | fe0e9803265acd551b5c7f8c326b66b231195d29f1d42c951d95c6572dfd5266 | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| data/derived/phase31_final_status.json | Y | 920 | ccde794775cc793fda96c0fd6b6be15110fa1991915afad55a1a295f7546ef1c | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| data/derived/phase31_prospective_snapshot.csv | Y | 4575362 | e3586a187a2ff2e34e4f9f44371aedd9c0842953e74beb045a05ed6bbb5c81fb | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| data/derived/phase32_final_status.json | Y | 956 | 09589c7d65e0119dacfd24c2ef9880eabe6b82e8a8a25b6a137db2c742850931 | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| data/derived/phase32_product_a_spatial_snapshot.csv | Y | 2877887 | 5305778dcf87c87a89136e786d88fa4b507371b8274fdc6bd2c296de265f9eac | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| data/derived/phase32_product_b_temporal_reci.csv | Y | 841 | e67eb16ab0d1ba30eccb7e7d1c4542e60b332b0b740a2bb9d8ae24426af57a54 | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| data/derived/phase32_product_c_gva_allocation.csv | Y | 2250743 | 43a4ed4523683d96c12bba5274149b7c62c3a63dc88cdf6172c8c7053718e7ee | frozen_input | 2b14f5bcb09a5334781d4cbe42c78c9a7de0a4e35e8d09e99c59cc6f5e719604 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |

## 3. Runtime

```json
{
  "python": "3.10.2",
  "platform": "macOS-14.5-arm64-arm-64bit",
  "locale_policy": "CSV=cp949; markdown/json=utf-8",
  "timezone": "KST",
  "random_seed": 20260720,
  "code_commit_hash": "510c8c96d97b5bb0c1e409466478d006c49b0bd0",
  "generated_at": "2026-07-20T02:17:43+09:00"
}
```
