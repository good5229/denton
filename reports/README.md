# Reports Index

This directory contains generated research notes, validation reports, dashboard assets, and portfolio materials. To keep the large number of markdown files navigable, use the topic hubs below.

## Topic Hubs

| Topic | Index |
| --- | --- |
| Project overview and operating rules | [topics/overview.md](topics/overview.md) |
| Data collection and feasibility | [topics/data.md](topics/data.md) |
| Denton, benchmarking, and allocation methods | [topics/methods.md](topics/methods.md) |
| Phase36 Seoul/Goyang spatiotemporal benchmarking | [partial_statistics_estimation_phase36_gva.md](partial_statistics_estimation_phase36_gva.md) |
| Phase37 Goyang current-EMD source collection | [partial_statistics_estimation_phase37_goyang_emd_sources.md](partial_statistics_estimation_phase37_goyang_emd_sources.md) |
| Phase38 Goyang current-44-EMD monthly GVA allocation | [partial_statistics_estimation_phase38_gva.md](partial_statistics_estimation_phase38_gva.md) |
| Phase40 Goyang KSIC×time×geography hierarchy validation | [partial_statistics_estimation_phase40_gva.md](partial_statistics_estimation_phase40_gva.md) |
| Phase41 Goyang all-industry KSIC hierarchy validation | [partial_statistics_estimation_phase41_gva.md](partial_statistics_estimation_phase41_gva.md) |
| Validation and confidence scoring | [topics/validation.md](topics/validation.md) |
| Reconciled ML experiments | [topics/ml.md](topics/ml.md) |
| Dashboard, figures, and portfolio assets | [topics/presentation.md](topics/presentation.md) |

## Current Main Result

The corrected all-industry hierarchy experiment is summarized in [partial_statistics_estimation_phase41_gva.md](partial_statistics_estimation_phase41_gva.md). It covers all estimable KSIC A–S sections: 19 sections, 74 divisions, 228 groups, 44 current administrative dongs, and 36 months. A 2015 Goyang Economic Census holdout gives 6.76 percentage-point MAE for division shares and 4.38 for hierarchical group shares, both better than uniform allocation overall. Parent-level diagnostics show that construction, health/social work, and transport/storage are the weakest division allocations, while real estate and agriculture are the weakest group allocations; several are worse than uniform allocation. All 27 industry×time×geography resolutions are materialized, while quarterly/monthly and detailed local cells remain D-grade constrained estimates rather than observed GVA.

The latest hierarchy-resolution audit is summarized in [partial_statistics_estimation_phase40_gva.md](partial_statistics_estimation_phase40_gva.md). It materializes all 27 KSIC-resolution×time-resolution×geography-resolution views for Goyang manufacturing, while separating accuracy evidence from accounting constraints. City×middle×annual has direct 2023/2024 holdout MAE of 0.670/0.567 percentage points. Small-class transfer validation against province actuals yields 11.44 percentage points versus 17.87 for uniform allocation; it is not a Goyang direct-accuracy claim. All nested sums reconcile within 0.001 million won, but identical small-class monthly profiles inside each EMD-middle group remain 100%, blocking claims of small-class-specific monthly dynamics.

The latest Goyang allocation experiment is summarized in [partial_statistics_estimation_phase38_gva.md](partial_statistics_estimation_phase38_gva.md). It produces 4,752 accounting-consistent cells for the current 44 EMDs, three supported parent sectors, and 36 months. A prospective 2023 gu-share holdout selects a 100% prior-year KOSIS weight: carry-forward MAE is 0.384 percentage points versus 2.097 for the licensing proxy alone. The licensing panel is therefore retained only for within-gu EMD-month interaction, not as a gu-share forecast. All accounting constraints pass within 1.17e-10 and the Phase36 identical-profile defect falls from 100% to 0%, but no official or observed EMD GVA claim is permitted.

The latest Goyang source-collection experiment is summarized in [partial_statistics_estimation_phase37_goyang_emd_sources.md](partial_statistics_estimation_phase37_goyang_emd_sources.md). It replaces the 2015 39-dong source frame with the current 44-dong geography, collects 19 free LOCALDATA licensing histories and Goyang education layers, builds a 14,520-row EMD×industry×month proxy panel, and validates it against 2021-2023 KOSIS gu×industry actuals. I00/S00 pass the strong spatial gate, Q00/R00 are supplementary, and G00 is rejected as a standalone proxy.

The preceding constrained-allocation experiment is summarized in [partial_statistics_estimation_phase36_gva.md](partial_statistics_estimation_phase36_gva.md). It produces Seoul gu×service-sector×month and Goyang 2015-administrative-dong×service-sector×month tables with exact quarterly and annual reconciliation. Seoul passes the raw common-profile check, while Goyang is retained only as a separable accounting allocation because every EMD inside a general-gu-sector inherits an identical normalized monthly profile.

The latest free-data interaction experiment is summarized in [partial_statistics_estimation_phase35_gva.md](partial_statistics_estimation_phase35_gva.md). KEPCO sigungu×KSIC-middle×month electricity and the NTS 36-month sigungu×lifestyle-industry panel break the Phase 34 common-proxy/rank-one defect on supported scopes without paid card data or API keys. The full sigungu×KSIC-middle×quarter GVA product remains blocked because exact-KSIC electricity is available for only three isolated quarters, small cells are heavily suppressed, releases are lagged, and no direct child GVA actual exists.

The preceding resolution-feasibility experiment is summarized in [partial_statistics_estimation_phase34_gva.md](partial_statistics_estimation_phase34_gva.md). A sigungu×KSIC-middle×quarter shadow table can be made by allocation, but it is blocked as joint GVA: its temporal matrix is rank one, every middle industry inherits the same parent-quarter profile, direct child actuals and historical temporal vintages are absent, and even an industry-permutation negative control preserves all parent sums.

The latest partial-statistics reconstruction decision is summarized in [partial_statistics_estimation_phase5c.md](partial_statistics_estimation_phase5c.md). Constraint-safe nested evaluation rejected the complex ML routers for both establishments and employees (Grade D); the development champion remains the transparent bidirectional temporal-share baseline, and no unpublished cells are released as estimates.

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

The current structural Phase 0 gate decision is summarized in [structural_feature_phase0_readiness.md](structural_feature_phase0_readiness.md). No structural source is ML-ready yet, so the restart decision remains blocked and electricity is retained only as a future interaction or auxiliary feature.

The current structural Phase 1 readiness pass is summarized in [structural_feature_phase1_readiness.md](structural_feature_phase1_readiness.md). Factory address crosswalk now passes the 1% unresolved threshold on local snapshots, but historical common-period and KSIC gates still block ML restart; Korea-specific geography features are registered for later ablation.

The current structural Phase 2 long-running discovery pass is summarized in [structural_phase2_long_running_data_discovery.md](structural_phase2_long_running_data_discovery.md). FactoryOn and public-data sources were cached and audited, but ML restart remains blocked because 2021-2023 factory historical snapshots, KSIC crosswalks, and geometry-derived spatial graphs are still incomplete.

The structural Phase 3 data-native pass is summarized in [structural_phase3_data_native_ksic_and_spatial_readiness.md](structural_phase3_data_native_ksic_and_spatial_readiness.md). The official KSIC 10/11 workbook is now parsed without collapsing one-to-many relationships, and the 228-node official municipality model universe now has audited SGIS geometry plus Queen, Rook, and distance graphs. ML restart remains blocked because historical KSIC 8/9 rows miss the mapping thresholds, the VWorld industrial-complex SHP download is not locally valid, and 2021-2023 structural history is incomplete.
