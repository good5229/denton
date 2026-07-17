# Structural Feature Phase 0 Readiness

## 실행 요약

전력 단독 residual correction은 `closed_no_confirmatory_challenger`로 종료됐고, 차기 실험은 structural source가 ML-ready gate를 통과한 뒤에만 시작한다. 이번 Phase 0 판정에서는 공장등록, 산업단지, 건축, 사업체·고용 중 어느 source도 아직 ML-ready가 아니다.

- restart_decision: `blocked_no_ml_ready_structural_source`
- operating_policy: `global`
- eligible_structural_sources: `0`
- same_actual_retuning_allowed: `false`

## Source Gate Matrix

| source | status | access | historical | region | crosswalk | vintage | eligibility | quality | feature table | next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| factory_registration | development_only | pass | fail | fail | fail | pass | partial | fail | pass | Build full factory snapshot inventory and validate address-to-sigungu/KSIC schema before C1/C3/C4/C5 bundles |
| industrial_complex_activity | development_only | pass | fail | fail | fail | pass | partial | fail | fail | Create complex-to-sigungu allocation table and production/export/employment long feature table |
| building_activity | blocked | pass | partial | partial | partial | partial | fail | fail | partial | Do not run nationwide row collection until bulk route or broad-collection post-filter pilot is manually approved |
| business_employment_activity | prospective_only | partial | partial | partial | unknown | unknown | unknown | unknown | fail | Select one business/employment source and build first-eligible-period aware long feature table |
| electricity_pipeline | retained_auxiliary_only | pass | pass | pass | pass | pass | pass | pass | pass | Use only as intensity/interaction feature after C1/C3/A4 structural baseline is frozen |

## Bundle Eligibility

| sector | bundle | definition | required sources | eligible | status | electricity role |
| --- | --- | --- | --- | --- | --- | --- |
| C00 | C0 | Global only |  | N | champion_only | not_used |
| C00 | C1 | Global + factory registration | factory_registration | N | blocked_until_factory_ml_ready | not_used |
| C00 | C2 | Global + industrial complex activity | industrial_complex_activity | N | blocked_until_industrial_complex_ml_ready | not_used |
| C00 | C3 | Global + factory + industrial complex | factory_registration,industrial_complex_activity | N | blocked_until_C1_C2_sources_ml_ready | not_used |
| C00 | C4 | Global + factory + electricity intensity | factory_registration,electricity_pipeline | N | blocked_until_factory_ml_ready | interaction_only |
| C00 | C5 | Global + factory + industrial complex + electricity intensity | factory_registration,industrial_complex_activity,electricity_pipeline | N | blocked_until_C3_sources_ml_ready | interaction_only |
| F00,L00 | BL0 | Global only |  | N | champion_only | not_used |
| F00,L00 | BL1 | Global + building permits | building_activity | N | blocked_until_building_ml_ready | not_used |
| F00,L00 | BL2 | Global + construction starts | building_activity | N | blocked_until_building_ml_ready | not_used |
| F00,L00 | BL3 | Global + approvals | building_activity | N | blocked_until_building_ml_ready | not_used |
| F00,L00 | BL4 | Global + permit + start | building_activity | N | blocked_until_building_ml_ready | not_used |
| F00,L00 | BL5 | Global + permit + start + approval | building_activity | N | blocked_until_building_ml_ready | not_used |
| all | A0 | Global only |  | N | champion_only | not_used |
| all | A1 | Global + business activity | business_employment_activity | N | blocked_until_business_activity_ml_ready | not_used |
| all | A2 | Global + employment activity | business_employment_activity | N | blocked_until_employment_activity_ml_ready | not_used |
| all | A3 | Global + building activity | building_activity | N | blocked_until_building_ml_ready | not_used |
| all | A4 | Global + business + employment | business_employment_activity | N | blocked_until_business_employment_ml_ready | not_used |
| all | A5 | Global + business + employment + electricity | business_employment_activity,electricity_pipeline | N | blocked_until_A4_structural_baseline_frozen | interaction_only |

## 운영 결론

1. `global + electricity only`, R2/R3b 파생형, 전력 혼합 정책은 차기 후보에서 제외한다.
2. 전력은 공장등록·산업단지·사업체·고용 source가 먼저 통과한 뒤 intensity 또는 interaction 변수로만 평가한다.
3. 2022~2023 actual은 development actual로 이미 사용됐으므로, 새 structural policy의 confirmatory 근거가 될 수 없다.
4. 미사용 official actual은 frozen challenger, frozen feature bundle, frozen model procedure, frozen gates, committed manifest가 있을 때만 confirmatory로 사용한다.

## 다음 작업 우선순위

1. 공장등록: 전체 snapshot의 주소-시군구 crosswalk와 KSIC/종업원/면적 schema를 확정한다.
2. 산업단지: 단지-시군구 allocation과 생산·수출·고용 long feature table을 만든다.
3. 건축HUB: broad collection + event-date post-filter pilot은 수동 승인 후 작은 표본으로만 수행한다.
4. 사업체·고용: 전국사업체조사, LOCALDATA 대체 source, 고용보험 source 중 하나를 선택해 first eligible period를 구현한다.

## 산출물

- `data/processed/structural_phase0_source_gates.csv`
- `data/processed/structural_phase0_bundle_registry.csv`
- `data/processed/structural_phase0_restart_manifest.json`
