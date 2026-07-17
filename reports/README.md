# Reports Index

This directory contains generated research notes, validation reports, dashboard assets, and portfolio materials. To keep the large number of markdown files navigable, use the topic hubs below.

## Topic Hubs

| Topic | Index |
| --- | --- |
| Project overview and operating rules | [topics/overview.md](topics/overview.md) |
| Data collection and feasibility | [topics/data.md](topics/data.md) |
| Denton, benchmarking, and allocation methods | [topics/methods.md](topics/methods.md) |
| Validation and confidence scoring | [topics/validation.md](topics/validation.md) |
| Reconciled ML experiments | [topics/ml.md](topics/ml.md) |
| Dashboard, figures, and portfolio assets | [topics/presentation.md](topics/presentation.md) |

## Current Main Result

The most recent ML decision is summarized in [municipality_oracle_upper_bound.md](municipality_oracle_upper_bound.md) and [municipality_ml_stop_decision.md](municipality_ml_stop_decision.md). The current practical conclusion is that even fine-grained municipality oracle policies improve WMAPE by less than 1%, so 시군구 operation should keep the Denton/indicator baseline and pause direct ML share correction.

The follow-up data step is summarized in [municipality_new_feature_dataset.md](municipality_new_feature_dataset.md). It builds a new municipality feature mart from KOSIS structural business statistics, mining/manufacturing 시군구 KSIC statistics, and economic-census 읍면동 proxy data before any future ML restart.

The latest public-source collection is summarized in [public_feature_source_collection.md](public_feature_source_collection.md). KEPCO 시군구 monthly electricity usage has been collected and normalized as an immediately usable external feature; MOLIT building permits and KICOX factory registration remain acquisition/schema follow-ups.

The electricity feature readiness result is summarized in [electricity_feature_report.md](electricity_feature_report.md), with the operational ML restart decision in [ml_restart_decision.md](ml_restart_decision.md). KEPCO electricity features are ML-ready, but ablation is blocked until a common official-actual evaluation period is available.

The historical KEPCO collection result is summarized in [kepco_historical_electricity_collection.md](kepco_historical_electricity_collection.md). It found 2021-2023 historical electricity coverage for all 36 target months and produced a historical municipality electricity feature table for the next ablation harness.

The first vintage-aware electricity dry-run is summarized in [electricity_vintage_aware_dry_run_report.md](electricity_vintage_aware_dry_run_report.md). The current decision is a guardrailed candidate, not operational acceptance.

The guardrail robustness round is summarized in [electricity_guardrail_robustness_round.md](electricity_guardrail_robustness_round.md). The current best electricity policy improves pooled O1 WMAPE but remains a refinement candidate because C00 deteriorates while all-sector totals improve.

The all-only refinement round is summarized in [electricity_all_only_refinement_round.md](electricity_all_only_refinement_round.md). It keeps the electricity feature as an all-sector shadow candidate, but does not freeze it as an operating policy because 2023 and placebo gates remain weak.

The pre-confirmatory policy selection is summarized in [electricity_preconfirmatory_policy_selection.md](electricity_preconfirmatory_policy_selection.md). Neither R2 nor R3b passed all final gates, so the operating policy remains global and no frozen electricity challenger is promoted.

The electricity-only closure decision and next workstreams are summarized in [electricity_only_policy_closure_and_next_workstreams.md](electricity_only_policy_closure_and_next_workstreams.md). Electricity-only residual correction is closed without a confirmatory challenger; the electricity pipeline remains active for future combined structural models.

The structural-feature restart plan is summarized in [next_structural_feature_workstreams.md](next_structural_feature_workstreams.md), with preregistration gates in [next_structural_feature_experiment_protocol.md](next_structural_feature_experiment_protocol.md). It keeps electricity inactive as a standalone ML correction and shifts the next restart criteria to factory registration, industrial complex activity, building permits, and business/employment sources.
