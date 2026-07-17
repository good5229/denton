# Next Structural Feature Experiment Protocol

## Status

This is a preregistration template. No new ML run is allowed until at least one required structural source reaches ML-ready status and this protocol is updated and committed before viewing any unused official actual.

## Target Sectors

- C00: manufacturing, after factory registration or industrial complex activity is ML-ready
- F00/L00: construction and real estate, after building permit/start/approval data is ML-ready
- all: only after non-electricity activity source is ML-ready

## Candidate Feature Bundles

| sector | bundle | definition |
| --- | --- | --- |
| C00 | B0 | global only |
| C00 | B1 | global + factory registration |
| C00 | B2 | global + industrial complex activity |
| C00 | B3 | global + factory + industrial complex |
| C00 | B4 | global + factory + electricity intensity |
| C00 | B5 | global + factory + industrial complex + electricity intensity |
| all | A0 | global only |
| all | A1 | global + business activity |
| all | A2 | global + employment |
| all | A3 | global + building activity |
| all | A4 | global + business + employment |
| all | A5 | global + business + employment + electricity |

## Fixed Principles

- Electricity-only correction is closed and cannot be revived without a new structural source.
- 2022-2023 actual cannot be used for new post-hoc tuning of electricity-only policies.
- Every source must include or derive `publication_date`, `source_vintage`, and `first_eligible_period`.
- An unused actual cannot be both development and confirmatory data.

## Gates Before ML Restart

- regional coverage >= 90% for C00/F00/L00/all national models
- official actual common period exists
- first eligible period implemented
- source vintage preserved
- quality audit passed
- candidate count and acceptance gates frozen before model results are inspected
