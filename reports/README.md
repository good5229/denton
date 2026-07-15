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

The most recent ML work is summarized in [municipality_oracle_upper_bound.md](municipality_oracle_upper_bound.md) and [municipality_ml_stop_decision.md](municipality_ml_stop_decision.md). The current practical conclusion is that even fine-grained municipality oracle policies improve WMAPE by less than 1%, so 시군구 operation should keep the Denton/indicator baseline and pause direct ML share correction until stronger municipality-level features are available.
