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
