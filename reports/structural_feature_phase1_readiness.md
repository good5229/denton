# Structural Feature Phase 1 Readiness

## 실행 요약

이번 Phase 1은 모델 학습을 실행하지 않고, 공장등록·산업단지 source readiness와 한국형 지리 feature registry를 재현 가능한 산출물로 고정했다. 로컬에 확보된 공장등록 CSV 2개와 산업단지 XLSX 1개는 끝까지 inventory/schema/crosswalk 감사했지만, 2021-2023 공통 historical stock/activity와 공식 KSIC/단지 allocation이 부족해 아직 ML-ready source는 없다.

- restart_decision: `blocked_no_ml_ready_structural_source`
- eligible_structural_sources: `0`
- korea_geography_feature_registry: `complete_rule_registry_distance_transport_terrain_sources_pending`
- at_least_one_adjacency_graph: `false_geometry_source_required`
- new_ml_training: `prohibited`

## Source Readiness

| source | status | key evidence | blocking issue |
| --- | --- | --- | --- |
| factory_registration | development_only | 415,283 rows, unresolved address rate 0.00504475 | 2021-2023 snapshot inventory and official KSIC crosswalk are incomplete; flow features require registration/closure dates or dense snapshots |
| industrial_complex_activity | development_only | 585 non-empty workbook rows, 42 observed complex names | latest industrial-complex workbook is available, but historical files, official complex codes, and sigungu allocation weights are not complete |
| building_activity | blocked | prior event-route/bulk-route probes only | event-specific route and nationwide collection route not selected |
| business_employment_activity | prospective_only | source scoring only | source choice and publication lag not fixed |
| electricity_pipeline | retained_auxiliary_only | historical KEPCO panel retained | standalone correction closed; interaction only after structural baseline |

## Geography Registry

한국형 지리 feature는 결과를 본 뒤 조정하지 않도록 registry에 사전 고정했다. 현재 구현된 것은 행정유형, 수도권, 도시위계, 산업벨트, 해안/도서/접경 rule 기반 feature이며, 거리·교통·지형 feature는 공식 GIS/교통/DEM source가 들어오기 전까지 `source_required`로 남긴다.

## Spatial Graph

산업벨트 동일 소속 graph는 diagnostic용으로 만들었지만, 이것은 행정경계 adjacency가 아니다. 시군구 polygon 또는 centroid source가 아직 committed되지 않았으므로 `queen_contiguity`, 거리 기반 graph, 통근 graph는 blocked로 둔다.

## Residual Diagnostics

2022-2023 baseline residual을 지리 그룹별로 집계했다. 이 actual은 development diagnostic으로만 사용하며 confirmatory 근거가 아니다. 동일 평가기간 residual을 spatial lag feature로 쓰는 것은 계속 금지한다.

## Phase 1 Gate

| gate | status |
| --- | --- |
| at_least_one_structural_source_ml_ready | false |
| korea_geography_feature_registry | complete_rule_registry_distance_transport_terrain_sources_pending |
| region_crosswalk | partial_factory_official_name_match_complete_official_actual_unmatched_not_final |
| at_least_one_adjacency_graph | false_geometry_source_required |
| leakage_future_information_rows | 0 |
| same_period_actual_residual_as_feature | 0 |
| candidate_bundles | frozen_names_definitions_only_no_training |

## 다음 작업

1. 공장등록 2021-2023 snapshot 또는 등록/폐쇄일 source를 확보해 historical_common_period gate를 해결한다.
2. 공식 KSIC crosswalk와 공장 주소 예외 crosswalk를 추가해 unresolved address rate를 1% 이하로 낮춘다.
3. 산업단지 공식 단지코드와 단지-시군구 allocation weight를 확보한다.
4. 시군구 boundary/centroid source를 추가해 adjacency 또는 거리 graph를 완성한다.
5. 적어도 하나의 structural source가 ML-ready가 된 뒤에만 Ridge/ElasticNet preregistration으로 넘어간다.

## 산출물

- `data/processed/factory_snapshot_inventory.csv`
- `data/processed/factory_schema_audit.csv`
- `data/processed/factory_address_crosswalk.csv`
- `data/processed/factory_ksic_crosswalk.csv`
- `data/processed/factory_feature_table.csv`
- `data/processed/industrial_complex_file_inventory.csv`
- `data/processed/industrial_complex_code_crosswalk.csv`
- `data/processed/industrial_complex_sigungu_allocation.csv`
- `data/processed/korea_geography_feature_registry.csv`
- `data/processed/korea_sigungu_geography_features.csv`
- `data/processed/korea_spatial_graph_audit.csv`
- `data/processed/korea_geography_residual_diagnostics.csv`
- `data/processed/structural_phase1_restart_manifest.json`
