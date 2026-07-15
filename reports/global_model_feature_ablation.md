# Global Model Feature Ablation

공통 feature global model은 F6/F7 외생·indicator feature를 애초에 포함하지 않는다. 따라서 이번 비교는 residual, core, sector/region ID 제거 중심으로 수행했다.

## 결과

| policy | WMAPE | MAPE | imp | material | worst |
| --- | ---: | ---: | ---: | ---: | ---: |
| global_baseline_only | 4.383005 | 6.857004 | 0.128796 | 18 | -24.407891 |
| global_core | 4.146101 | 6.529968 | 5.526896 | 16 | -31.068616 |
| global_fixed_full | 4.124072 | 6.520107 | 6.028854 | 14 | -40.729135 |
| global_no_region_id | 4.137599 | 6.493424 | 5.72062 | 15 | -28.550244 |
| global_no_residual_features | 4.155938 | 6.552091 | 5.302759 | 16 | -26.59212 |
| global_no_sector_id | 4.123385 | 6.476411 | 6.044502 | 14 | -35.939848 |
| global_pruned_no_F4 | 4.127842 | 6.517236 | 5.942959 | 17 | -40.844469 |
| global_residual_only | 4.376168 | 6.623138 | 0.284583 | 8 | -25.9399 |
| global_tuned_full | 4.106585 | 6.576717 | 6.42732 | 16 | -59.388193 |
| global_tuned_pruned_no_F4 | 4.127613 | 6.5244 | 5.948175 | 20 | -55.997982 |