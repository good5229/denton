# Partial Statistics Estimation Phase 10

## 1. 실행 요약

The official-source cube is active for data integrity, while historical chronology remains incomplete. A genuine future-vintage forecast archive has been frozen and is waiting for observed release evidence.

| status | official_cube | candidate_target_period | forecast_rows | forecast_archive_hash | forecast_created_at | release_watcher | first_observed_availability | holdout_raw_seal_status | one_shot_consumed | production_use | confirmatory_use | official_statistics_claim | generated_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| forecast_frozen_waiting_release | active_primary_for_data_integrity | 2025 | 14028 | 10e46f86fc79924d758bbf5e51a0952cae5ed5fe0af5d71a793ab229936dd322 | 2026-07-18T15:32:30+09:00 | implemented_metadata_only |  | not_available | False | False | False | False | 2026-07-18T15:32:30+09:00 |

## 2. Phase 9 기준선

| phase9_status | official_raw_rows | primary_stable_cube_rows | raw_R4_conflict_cells | forecast_archive_2024 | phase7_incumbent_retained |
| --- | --- | --- | --- | --- | --- |
| blocked_release_evidence | 92634 | 41808 | 0 | development_shadow_forecast | true |

## 3. Gate Architecture

Historical availability is deliberately separated from future observed availability, so missing historical release dates do not block the 2025 forecast archive.

| gate_id | gate_scope | gate_description | required_evidence | current_status | blocking_effect | threshold_value | threshold_origin | evidence_artifact | reviewed_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G1 | source_authenticity | official KOSIS response bodies and hashes exist | R2 raw source manifest | pass_conditional | does not block forecast; request/header hardening remains | official table id and hashes present | frozen_existing | partial_stats_phase9_raw_source_manifest.csv | 2026-07-18T15:32:30+09:00 |
| G2 | cell_integrity | stable keys, suppression, provenance, and R4 reconciliation | official cube audit and raw/R4 conflicts | pass | none | 0 duplicate, 0 conflict | frozen_existing | partial_stats_phase10_official_cube_audit.csv | 2026-07-18T15:32:30+09:00 |
| G3 | historical_availability | first public release date for 2020-2024 | A_exact or B_month official source | blocked_release_evidence | blocks historical prospective promotion only; future forecast generation not blocked | release confidence A/B | proposed_gate | partial_stats_phase10_historical_release_evidence.csv | 2026-07-18T15:32:30+09:00 |
| G4 | future_observed_availability | release watcher observes first availability of future vintage | watcher probe log and first_seen row | not_detected | holdout scoring pending; forecast archive not blocked | first_observed_available_at after forecast_created_at | frozen_existing | partial_stats_phase10_release_first_seen.csv | 2026-07-18T15:32:30+09:00 |
| G5 | policy_identity | P7 incumbent and C3 shadow hashes frozen | policy identity audit | pass | forecast archive allowed | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | frozen_existing | partial_stats_phase10_policy_identity_audit.csv | 2026-07-18T15:32:30+09:00 |
| G6 | holdout_integrity | forecast precedes observed availability and local target absence | holdout integrity audit | pending_release | one-shot scoring pending | forecast time < first observed availability | frozen_existing | partial_stats_phase10_holdout_integrity_audit.csv | 2026-07-18T15:32:30+09:00 |
| G7 | model_promotion | frozen gate-based promotion decision | one-shot holdout result | blocked_pending_unseen_holdout | production release blocked | no material degradation | frozen_existing | partial_stats_phase10_holdout_decision.json | 2026-07-18T15:32:30+09:00 |
| G8 | production_release | official/statistical use approval | separate user approval | blocked_no_approval | production_use false | manual approval | not_applicable |  | 2026-07-18T15:32:30+09:00 |

## 4. Official Stable Cube

The cube is promoted from Phase 9's release-blocked state to `primary_official_source_cube` for data integrity only, not for historical prospective promotion.

| cube_id | row_count | data_integrity_status | primary_for_data_integrity | primary_for_retrospective_reconstruction | primary_for_historical_prospective_promotion | primary_for_future_pre_release_forecast | source_grade | raw_R4_conflict_count | generated_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P10_OFFICIAL_RAW_STABLE_CUBE | 41808 | primary_official_source_cube | True | True | False | True | R2_official_api_body_header_missing | 0 | 2026-07-18T15:32:30+09:00 |

## 5. Source 및 Cell Integrity

| audit_id | value | status |
| --- | --- | --- |
| row_count | 41808 | pass |
| cell_count | 41808 | pass |
| year_coverage | 2020-2024 | pass |
| region_coverage | 265 | pass |
| industry_coverage | 29 | pass |
| target_coverage | employees,establishments | pass |
| suppression_count | 7202 | pass_preserved |
| duplicate_count | 0 | pass |
| raw_R4_conflict_count | 0 | pass |
| source_hash_completeness | 41808 | pass |

## 6. Historical Release Evidence

| reference_year | evidence_class | official_first_release_date | official_first_release_month | table_update_date | used_as_first_release | evidence_summary |
| --- | --- | --- | --- | --- | --- | --- |
| 2020 | C_update |  |  | 2026-01-27 | N | Only LST_CHN_DE/update evidence is locally available; it is not treated as first release evidence. |
| 2021 | C_update |  |  | 2026-01-27 | N | Only LST_CHN_DE/update evidence is locally available; it is not treated as first release evidence. |
| 2022 | C_update |  |  | 2026-01-13,2026-01-14,2026-01-15 | N | Only LST_CHN_DE/update evidence is locally available; it is not treated as first release evidence. |
| 2023 | C_update |  |  | 2025-02-21 | N | Only LST_CHN_DE/update evidence is locally available; it is not treated as first release evidence. |
| 2024 | C_update |  |  | 2026-02-26 | N | Only LST_CHN_DE/update evidence is locally available; it is not treated as first release evidence. |

## 7. Historical Search 종료판정

| reference_year | historical_release_status | backtest_classification | future_forecast_blocked |
| --- | --- | --- | --- |
| 2020 | unavailable_after_exhaustive_local_search | chronology_approximation | N |
| 2021 | unavailable_after_exhaustive_local_search | chronology_approximation | N |
| 2022 | unavailable_after_exhaustive_local_search | chronology_approximation | N |
| 2023 | unavailable_after_exhaustive_local_search | chronology_approximation | N |
| 2024 | unavailable_after_exhaustive_local_search | chronology_approximation | N |

## 8. P7 Incumbent Identity

| audit_id | expected | observed | status | exact_match_rate | nonzero_adjustment_rate | mean_adjustment | p90_adjustment | maximum_adjustment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P7_policy_hash | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | pass |  |  |  |  |  |
| C3_source_function | phase8.median_growth_predictions(shrink=0.5) | phase8.median_growth_predictions(shrink=0.5) | pass |  |  |  |  |  |
| C3_prediction_distinct |  |  | pass | 0.6029369831765041 | 0.3970630168234959 | 1.5037024227830638 | 6.2187619051176615 | 1017.6993749999965 |

## 9. C3 Shadow Challenger

C3 is frozen as a shadow challenger only because it produces non-identical predictions. It is not a production candidate.

| model_id | policy_role | shadow_frozen | production_candidate | confirmatory_comparison_candidate | implementation_hash | source_file | function_name | hyperparameters | fallback_rule | frozen_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C3_hierarchical_shrinkage_growth | shadow_challenger | True | False | True | d214a1e0c8bb65f76ce8eef0d27b7261dc68b31ac3a85c12eb59addef68d93f8 | scripts/run_partial_statistics_phase8.py | median_growth_predictions | {'shrink': 0.5} | cell latest, industry median growth, global target median growth | 2026-07-18T15:32:30+09:00 |

## 10. Evaluation Protocol

| protocol_id | incumbent_policy_hash | shadow_policy_hash | primary_metric | secondary_metrics | comparison_population | material_degradation_rule | same_holdout_retuning | automatic_promotion | frozen_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P10_ONE_SHOT_FUTURE_VINTAGE_PROTOCOL | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | d214a1e0c8bb65f76ce8eef0d27b7261dc68b31ac3a85c12eb59addef68d93f8 | M_WMAPE_POOLED_ABS | ['MAE', 'RMSLE', 'median_APE', 'p90_APE', 'aggregate_error'] | same official observed non-suppressed cells for target_period | no_material_degradation_allowed | prohibited | prohibited_without_frozen_gate_and_manual_approval | 2026-07-18T15:32:30+09:00 |

## 11. Public Period Inventory

| inventory_source | latest_local_reference_year | latest_public_reference_year | metadata_probe_mode | target_values_requested |
| --- | --- | --- | --- | --- |
| phase9_official_raw_cube | 2024 | 2024 | local_metadata_only_no_target_value_request | N |

## 12. Holdout Candidate

| candidate_target_period | information_cutoff | classification | confirmatory_eligible_after_release |
| --- | --- | --- | --- |
| 2025 | 2024 | pre_release_candidate_waiting_watcher | pending_true_pre_release_check |

## 13. Forecast 생성시각

| forecast_archive_hash | forecast_rows | candidate_target_period | physical_forecast_created_at | append_only | input_cube_hash | protocol_hash | target_values_accessed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10e46f86fc79924d758bbf5e51a0952cae5ed5fe0af5d71a793ab229936dd322 | 14028 | 2025 | 2026-07-18T15:32:30+09:00 | True | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 | False |

## 14. Forecast Archive

| forecast_id | policy_id | policy_role | physical_forecast_created_at | logical_prediction_origin | information_cutoff | target_period | target_name | region_key | industry_code | prediction | lower_80 | upper_80 | lower_95 | upper_95 | support_class | estimate_status | fallback_used | fallback_reason | input_cube_hash | policy_hash | code_commit_hash | protocol_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 366bc78690e5f9ec617e20d4 | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 32050 | B05 | 1.0 | 0.75 | 1.25 | 0.0 | 2.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| 5b152643630c71d8b345d662 | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 32070 | B05 | 3.0 | 2.25 | 3.75 | 0.0 | 6.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| cd8e14363de92c7d3a5013e2 | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 36570 | B05 | 1.0 | 0.75 | 1.25 | 0.0 | 2.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| 73203364b38d99c09d9db8f6 | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 37010 | B05 | 1.0 | 0.75 | 1.25 | 0.0 | 2.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| 0549c579eeac4e0463d56472 | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 37012 | B05 | 1.0 | 0.75 | 1.25 | 0.0 | 2.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| 90524f3e60c4b98fec6786ca | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | employees | 32070 | B05 | 932.0 | 723.9196946759785 | 1140.0803053240215 | 281.73082860055376 | 1582.2691713994463 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| f96b643f85de3bf435ff9f91 | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 11240 | B06 | 1.0 | 0.75 | 1.25 | 0.0 | 2.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| 255d431ac35ae14dd487ffc9 | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 31270 | B06 | 1.0 | 0.75 | 1.25 | 0.0 | 2.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| 695b3a9c7e618224fcc3e7e6 | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 32530 | B06 | 1.0 | 0.75 | 1.25 | 0.0 | 2.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| 3750d60f19017e54e11d81ca | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 32550 | B06 | 1.0 | 0.75 | 1.25 | 0.0 | 2.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| 2c9127b6548b2599aa19967d | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 32610 | B06 | 1.0 | 0.75 | 1.25 | 0.0 | 2.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |
| 7a4a5a63d5193739497db06b | P7_FROZEN_LAST_OBSERVATION | incumbent | 2026-07-18T15:32:30+09:00 | 2024-12-31 | 2024 | 2025 | establishments | 33030 | B06 | 3.0 | 2.25 | 3.75 | 0.0 | 6.0 | PS1_recent_temporal | estimated | N |  | 17b2e765d6911841d17a6d1601fa27c8bffa06e693bd9a2239b9c75bc39c4fca | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 6654dd8c1a801d92ac3a58929d79846d5664f74e | 634dd71a638eef2f6f8baba4e976b0ff45164fce4013591468211cf155d50c32 |

## 15. Release Watcher

| watcher_status | script | modes | candidate_target_period | first_observed_available_at | target_values_requested | api_key_persisted |
| --- | --- | --- | --- | --- | --- | --- |
| implemented_metadata_only | scripts/partial_stats_phase10_release_watcher.py | ['--check-only', '--record-metadata', '--capture-new-vintage', '--status'] | 2025 |  | False | False |

## 16. First Observed Availability

| candidate_target_period | first_observed_available_at | first_observed_probe_id | first_observed_response_hash | availability_status |
| --- | --- | --- | --- | --- |
| 2025 |  |  |  | not_detected |

## 17. Raw Holdout Seal

| target_period | holdout_raw_status | sealed_unparsed | target_body_parsed |
| --- | --- | --- | --- |
| 2025 | not_available | False | False |

## 18. Holdout Integrity

Holdout integrity is pending until the watcher records first observed official availability. Target values have not been parsed.

| audit_id | target_period | forecast_time | first_observed_available_at | status |
| --- | --- | --- | --- | --- |
| forecast_before_first_availability | 2025 | 2026-07-18T15:32:30+09:00 |  | pending_release |
| target_local_presence_before_forecast | 2025 |  |  | pass_not_present |
| target_not_parsed_before_freeze | 2025 |  |  | pass |
| holdout_classification | 2025 |  |  | forecast_frozen_waiting_release |

## 19. Incumbent One-shot 결과

| target_period | evaluation_status | one_shot_consumed |
| --- | --- | --- |
| 2025 | pending_release | N |

## 20. Shadow One-shot 결과

| target_period | evaluation_status | one_shot_consumed |
| --- | --- | --- |
| 2025 | pending_release | N |

## 21. Material Degradation

| target_period | evaluation_status | one_shot_consumed |
| --- | --- | --- |
| 2025 | pending_release | N |

## 22. Prediction Interval

| forecast_id | policy_role | target_name | lower_80 | upper_80 | lower_95 | upper_95 |
| --- | --- | --- | --- | --- | --- | --- |
| 366bc78690e5f9ec617e20d4 | incumbent | establishments | 0.75 | 1.25 | 0.0 | 2.0 |
| 5b152643630c71d8b345d662 | incumbent | establishments | 2.25 | 3.75 | 0.0 | 6.0 |
| cd8e14363de92c7d3a5013e2 | incumbent | establishments | 0.75 | 1.25 | 0.0 | 2.0 |
| 73203364b38d99c09d9db8f6 | incumbent | establishments | 0.75 | 1.25 | 0.0 | 2.0 |
| 0549c579eeac4e0463d56472 | incumbent | establishments | 0.75 | 1.25 | 0.0 | 2.0 |
| 90524f3e60c4b98fec6786ca | incumbent | employees | 723.9196946759785 | 1140.0803053240215 | 281.73082860055376 | 1582.2691713994463 |
| f96b643f85de3bf435ff9f91 | incumbent | establishments | 0.75 | 1.25 | 0.0 | 2.0 |
| 255d431ac35ae14dd487ffc9 | incumbent | establishments | 0.75 | 1.25 | 0.0 | 2.0 |
| 695b3a9c7e618224fcc3e7e6 | incumbent | establishments | 0.75 | 1.25 | 0.0 | 2.0 |
| 3750d60f19017e54e11d81ca | incumbent | establishments | 0.75 | 1.25 | 0.0 | 2.0 |
| 2c9127b6548b2599aa19967d | incumbent | establishments | 0.75 | 1.25 | 0.0 | 2.0 |
| 7a4a5a63d5193739497db06b | incumbent | establishments | 2.25 | 3.75 | 0.0 | 6.0 |

## 23. Region·Industry 안정성

| target_period | evaluation_status | one_shot_consumed |
| --- | --- | --- |
| 2025 | pending_release | N |

## 24. Cold-start 및 Not-estimable

| forecast_id | policy_role | target_period | target_name | region_key | industry_code | support_class | estimate_status | fallback_used | fallback_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 366bc78690e5f9ec617e20d4 | incumbent | 2025 | establishments | 32050 | B05 | PS1_recent_temporal | estimated | N |  |
| 5b152643630c71d8b345d662 | incumbent | 2025 | establishments | 32070 | B05 | PS1_recent_temporal | estimated | N |  |
| cd8e14363de92c7d3a5013e2 | incumbent | 2025 | establishments | 36570 | B05 | PS1_recent_temporal | estimated | N |  |
| 73203364b38d99c09d9db8f6 | incumbent | 2025 | establishments | 37010 | B05 | PS1_recent_temporal | estimated | N |  |
| 0549c579eeac4e0463d56472 | incumbent | 2025 | establishments | 37012 | B05 | PS1_recent_temporal | estimated | N |  |
| 90524f3e60c4b98fec6786ca | incumbent | 2025 | employees | 32070 | B05 | PS1_recent_temporal | estimated | N |  |
| f96b643f85de3bf435ff9f91 | incumbent | 2025 | establishments | 11240 | B06 | PS1_recent_temporal | estimated | N |  |
| 255d431ac35ae14dd487ffc9 | incumbent | 2025 | establishments | 31270 | B06 | PS1_recent_temporal | estimated | N |  |
| 695b3a9c7e618224fcc3e7e6 | incumbent | 2025 | establishments | 32530 | B06 | PS1_recent_temporal | estimated | N |  |
| 3750d60f19017e54e11d81ca | incumbent | 2025 | establishments | 32550 | B06 | PS1_recent_temporal | estimated | N |  |
| 2c9127b6548b2599aa19967d | incumbent | 2025 | establishments | 32610 | B06 | PS1_recent_temporal | estimated | N |  |
| 7a4a5a63d5193739497db06b | incumbent | 2025 | establishments | 33030 | B06 | PS1_recent_temporal | estimated | N |  |

## 25. 최종 판정

Final status is `forecast_frozen_waiting_release` unless a future vintage is detected and sealed in a later run.

| target_period | decision | one_shot_consumed | same_holdout_retuning | final_status |
| --- | --- | --- | --- | --- |
| 2025 | pending_first_observed_availability | False | prohibited | forecast_frozen_waiting_release |

## 26. 사용자 개입 요청

| request_id | priority | required | blocks_future_forecast | status | blocks_one_shot |
| --- | --- | --- | --- | --- | --- |
| P10-HIST-REL-001 | P2 | DT_1FS1101 2020-2024 official first release date/month evidence | N | pending |  |
| P10-WATCH-001 | P1 | Run scripts/partial_stats_phase10_release_watcher.py periodically until 2025 vintage appears | N | pending_external_schedule |  |
| P10-HOLDOUT-RAW-001 | P1_after_detection | If watcher detects 2025 but capture cannot run, store official raw API bodies without parsing values |  | pending_detection | Y |

## 27. 한계

| limit_id | description |
| --- | --- |
| historical_release_missing | 2020-2024 first release evidence remains C_update/local only |
| watcher_not_scheduled | script exists, but external scheduler setup is outside this run |
| one_shot_pending | no holdout actual has been parsed or evaluated yet |

## 28. 다음 Vintage 정책

| policy | action |
| --- | --- |
| wait_for_2025_first_observed_availability | run watcher metadata-only until new period appears |
| seal_before_parse | capture raw bodies and hashes before actual parsing |
| one_shot_only | evaluate once; do not retune on the consumed holdout |
