# 전력 단독 정책 종료 및 다음 Workstream

## 최종 종료 결정

- experiment_status: `closed_no_confirmatory_challenger`
- champion: `global`
- confirmatory_challenger: `none`
- electricity_only_policy_status: `research_candidate_only`
- production_replacement: `prohibited`
- same_actual_retuning_allowed: `false`

R2와 R3b는 pooled WMAPE, tail stability, LOSO, large-observation removal에서 일부 긍정적 신호를 보였지만, 사전 Gate 전체를 통과하지 못했다. 따라서 전력 단독 residual correction 정책은 종료하고, 전력 데이터는 향후 구조 Feature 결합용으로만 보존한다.

## R2 및 R3b Gate 실패 사유

| policy | gate | pass | note |
| --- | --- | --- | --- |
| R2_all_only_trainalpha_B6_rel5 | data_integrity | Y | primary vintage audit has zero leakage |
| R2_all_only_trainalpha_B6_rel5 | year_consistency | N | 2022=0.312914, 2023=-0.221146, pooled=0.090573 |
| R2_all_only_trainalpha_B6_rel5 | placebo | N | requires all three placebo p95 passes |
| R2_all_only_trainalpha_B6_rel5 | selection_aware_bootstrap | N | P(improve)=0.8175 |
| R2_all_only_trainalpha_B6_rel5 | tail_stability | Y | material=0, +5pp=0, +10pp=0 |
| R2_all_only_trainalpha_B6_rel5 | region_generalization | Y | improved=11, worst=-0.184183 |
| R2_all_only_trainalpha_B6_rel5 | large_observation_removal | Y | requires positive improvement after every removal |
| R3b_all_only_conservative_B4_rel5 | data_integrity | Y | primary vintage audit has zero leakage |
| R3b_all_only_conservative_B4_rel5 | year_consistency | Y | 2022=0.227336, 2023=-0.077404, pooled=0.100466 |
| R3b_all_only_conservative_B4_rel5 | placebo | N | requires all three placebo p95 passes |
| R3b_all_only_conservative_B4_rel5 | selection_aware_bootstrap | N | P(improve)=0.8175 |
| R3b_all_only_conservative_B4_rel5 | tail_stability | Y | material=0, +5pp=0, +10pp=0 |
| R3b_all_only_conservative_B4_rel5 | region_generalization | Y | improved=11, worst=-0.168469 |
| R3b_all_only_conservative_B4_rel5 | large_observation_removal | Y | requires positive improvement after every removal |

## 전력 Feature 결과 해석

| policy | WMAPE | global WMAPE | delta +good | relative % | material | +5pp | +10pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R2_all_only_trainalpha_B6_rel5 | 5.379586 | 5.470158 | 0.090573 | 1.655762 | 0 | 0 | 0 |
| R3b_all_only_conservative_B4_rel5 | 5.369693 | 5.470158 | 0.100466 | 1.836613 | 0 | 0 | 0 |

## 추가 튜닝 금지

2022-2023 actual을 이용해 alpha, clipping, feature bundle, residual target, 지역별 적용 규칙, R2/R3b 혼합 정책을 추가 탐색하지 않는다. 이는 사후 과적합으로 간주한다.

## Temporal Signal 진단

- selection-aware P(improve): `0.8175`
- temporal placebo 실패는 모델 재튜닝 사유가 아니라 feature 성격 진단 대상으로 처리한다.

| feature | between/total | within/total | lag1 autocorr | lag12 autocorr | yoy variance | interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| electricity_total_kwh | 0.984197 | 0.015803 | 0.55004 | 0.809086 | 0.0078228553 | mostly_cross_sectional_scale_or_structure |
| electricity_industrial_kwh | 0.986308 | 0.013692 | 0.503949 | 0.585125 | 0.0241728149 | mostly_cross_sectional_scale_or_structure |
| electricity_commercial_kwh | 0.949658 | 0.050342 | 0.573977 | 0.912602 | 0.0075777481 | mostly_cross_sectional_scale_or_structure |
| industrial_share | 0.982998 | 0.017002 | 0.540257 | 0.767243 | 0.0103773364 | mostly_cross_sectional_scale_or_structure |
| commercial_share | 0.977734 | 0.022266 | 0.536055 | 0.725025 | 0.0134741667 | mostly_cross_sectional_scale_or_structure |
| log_total_kwh | 0.935695 | 0.064305 | 0.555445 | 0.80737 | 0.001328815 | mostly_cross_sectional_scale_or_structure |
| log_industrial_kwh | 0.962735 | 0.037265 | 0.504485 | 0.580227 | 0.0010795276 | mostly_cross_sectional_scale_or_structure |
| log_commercial_kwh | 0.922472 | 0.077528 | 0.579991 | 0.910966 | 0.0011860339 | mostly_cross_sectional_scale_or_structure |

## Between/Within Variance

| feature | total variance | between variance | within variance | between/total | scale corr |
| --- | ---: | ---: | ---: | ---: | ---: |
| electricity_total_kwh | 6.6013852132720824e+16 | 6.497062936097906e+16 | 1043222771741766.1 | 0.984197 | 1.0 |
| electricity_industrial_kwh | 4.5608108777364584e+16 | 4.498364673707314e+16 | 624462040291430.8 | 0.986308 | 0.959087 |
| electricity_commercial_kwh | 2352170171618534.5 | 2233758183019185.5 | 118411988599351.38 | 0.949658 | 0.595756 |
| industrial_share | 0.0662798428 | 0.06515297 | 0.0011268728 | 0.982998 | 0.549647 |
| commercial_share | 0.0265623358 | 0.0259709037 | 0.0005914321 | 0.977734 | -0.299756 |
| log_total_kwh | 2.1308248803 | 1.9938023126 | 0.1370225677 | 0.935695 | 0.610293 |
| log_industrial_kwh | 3.723027882 | 3.584289808 | 0.138738074 | 0.962735 | 0.661372 |
| log_commercial_kwh | 2.0095828935 | 1.8537845468 | 0.1557983467 | 0.922472 | 0.441893 |

## Autocorrelation Audit

| feature | lag1 mean | lag12 mean | yoy variance |
| --- | ---: | ---: | ---: |
| electricity_total_kwh | 0.55004 | 0.809086 | 0.0078228553 |
| electricity_industrial_kwh | 0.503949 | 0.585125 | 0.0241728149 |
| electricity_commercial_kwh | 0.573977 | 0.912602 | 0.0075777481 |
| industrial_share | 0.540257 | 0.767243 | 0.0103773364 |
| commercial_share | 0.536055 | 0.725025 | 0.0134741667 |
| log_total_kwh | 0.555445 | 0.80737 | 0.001328815 |
| log_industrial_kwh | 0.504485 | 0.580227 | 0.0010795276 |
| log_commercial_kwh | 0.579991 | 0.910966 | 0.0011860339 |

## 전력 Pipeline 유지계획

- data pipeline: `active`
- ML correction policy: `inactive`
- monthly source manifest, file hash, publication date, source vintage, region crosswalk, schema fingerprint, duplicate key, negative value, publication lag drift를 계속 점검한다.

## 다음 Feature Source Workstreams

| workstream | priority | status | target sectors | next action |
| --- | ---: | --- | --- | --- |
| factory_registration | 1 | not_yet_ml_ready | C00 | FactoryOn and local-government file routes; verify historical reconstruction |
| industrial_complex_activity | 2 | not_yet_ml_ready | C00 | Collect quarterly complex files, standardize complex codes, build sigungu allocation rule |
| building_permits_and_starts | 3 | not_yet_ml_ready | F00,L00 | Confirm BuildingHub bulk/API access and event classification |
| electricity_pipeline | 0 | active_data_pipeline_inactive_ml_correction | research_context | Continue monthly collection and schema/quality audits |

## 차기 ML 재개 Gate

- C00: factory registration 또는 industrial complex activity가 ML-ready이고 시군구 coverage가 90% 이상이며 first eligible period가 구현된 뒤 재개한다.
- all: building activity, business openings/closures, employment, card sales, foot traffic 중 하나 이상의 신규 source가 ML-ready일 때 재개한다.
- D00: 별도 직접 Feature가 확보될 때까지 global fallback을 유지한다.

## 미사용 Actual 관리원칙

confirmatory challenger가 없으므로 2024 이후 official actual로 R2/R3b를 자동 평가하지 않는다. 향후 actual은 결합 정책이 actual 공개 전에 완전히 동결된 경우에만 confirmatory로 사용하고, 그렇지 않으면 development_extension으로 명시해 confirmatory 자격을 포기한다.

## 산출물

- `data/processed/electricity_policy_closure_manifest.json`
- `data/processed/electricity_temporal_signal_diagnostics.csv`
- `data/processed/electricity_between_within_variance.csv`
- `data/processed/electricity_autocorrelation_audit.csv`
- `data/processed/next_feature_source_status.csv`
