# Regional GVA Denton Reconstruction

This project reconstructs quarterly regional gross value added (GVA) estimates for Korea using public KOSIS data and the proportional Denton method. It is inspired by the Bank of Korea issue note on developing and using regional economic activity indicators.

## What This Repository Contains

- KOSIS OpenAPI collection scripts for regional GVA, production indices, GDP benchmarks, deflators, construction indicators, and subregional feasibility data.
- Proportional Denton estimation scripts for converting annual regional GVA benchmarks into quarterly estimates.
- Expanded data-discovery logic for checking whether the model can move from `시도 × 대분류` to `시군구`, `읍면동`, and detailed KSIC industry classes.
- ECOS data augmentation for national account cross-checks, GDP deflators, input-output priors, and energy/price/fx exogenous variables.
- Release-aware backtesting logic that uses only data available as of the forecast origin.
- Confidence scoring outputs that label estimates by actual/benchmark/prior/exogenous role and A-D reliability grade.
- Portfolio-oriented documentation and figure generation scripts that explain the methodology and implementation flow.

The collected data files, local harness instructions, and PowerPoint files are intentionally excluded from git. Re-run the collection scripts with a valid KOSIS API key to reproduce local outputs.

CSV outputs are written in `cp949` so Korean text opens cleanly in Korean MS Office environments. Legacy UTF-8 outputs can still be read by the helper and rewritten as `cp949`.

## Project Structure

```text
scripts/
  collect_kosis.py              # Collect baseline KOSIS datasets
  collect_expanded_kosis.py     # Collect subregional and detailed-industry feasibility datasets
  denton_reci.py                # Core proportional Denton implementation for selected sectors
  denton_all_industries.py      # All-industry 시도 quarterly estimation
  denton_sigungu.py             # 시군구 quarterly estimation using annual GRVA benchmarks
  allocate_detailed_industry.py # 시군구 제조업 KSIC 세부산업 allocation
  collect_emd_economic_census.py # 읍면동 economic census proxy collection
  allocate_emd_gva.py           # 읍면동 proxy GVA allocation
  collect_ecos_augmented_data.py # ECOS national accounts, IO priors, and exogenous indicators
  data_availability.py          # Forecast-origin and publication-lag filters
  build_confidence_scores.py    # A-D confidence grading from backtest diagnostics
  build_reci.py                 # RECI index construction and validation
  make_figures.py               # Generate SVG/PNG documentation figures
  make_portfolio_ppt.py         # Generate editable portfolio PPT assets
reports/
  dashboard/                    # Static HTML dashboard reading local CSV outputs
  data_requirements.md          # Data requirements from the BOK note
  run_summary.md                # Baseline reconstruction summary
  expanded_data_feasibility.md  # 시군구/읍면동/KSIC feasibility findings
  release_aware_modeling_policy.md # Publication-lag policy
  release_aware_backtest_report.md # Forecast-vs-actual diagnostics under as-of rules
  confidence_scoring.md         # Confidence score policy and outputs
```

## Method Summary

The proportional Denton method estimates quarterly GVA values `X_t` from annual benchmarks `A_y` and quarterly indicators `I_t` by minimizing changes in the ratio `X_t / I_t`, subject to annual sum constraints:

```text
min Σ [(X_t / I_t) - (X_{t-1} / I_{t-1})]^2
s.t. Σ_q X_{y,q} = A_y
```

The baseline implementation uses regional production/service indices and national GDP profiles where direct regional quarterly indicators are unavailable. The 시군구 extension uses annual 시군구 GRVA as the benchmark and parent 시도 quarterly estimates as the quarterly movement indicator.

For forecast-style validation, the project now applies a release-aware policy: an input is usable only if its estimated publication date is before the forecast origin. This prevents target-year annual proxies or full-year exogenous averages from leaking into historical backtests.

Outputs are separated by role:

| Role | Meaning |
|---|---|
| `actual` | Officially published government or local-government statistic |
| `benchmark` | Official aggregate used as a Denton or allocation constraint |
| `forecast` | Out-of-sample estimate made without the target actual |
| `allocation` | Benchmark-constrained distribution to lower geography/time/detail |
| `prior` | Structural information such as ECOS input-output coefficients |
| `exogenous` | Price, fx, commodity, or other explanatory candidate variable |

## Reproducing Locally

1. Create `.env` with `KOSIS_API_KEY`.
2. Install dependencies:

```bash
.venv/bin/pip install numpy python-pptx
```

Optional sector-specific ML experiments can evaluate XGBoost when the native
runtime is available:

```bash
.venv/bin/pip install xgboost
brew install libomp
```

On macOS, the Python/XGBoost architecture and the `libomp` architecture must
match. If they do not, `scripts/run_sector_specific_models.py` skips XGBoost
and records the unavailable status in the report.

On a machine with x86_64 Homebrew under `/usr/local`, use a matching x86_64
experiment environment:

```bash
arch -x86_64 python3 -m venv .venv_x86
arch -x86_64 .venv_x86/bin/pip install numpy xgboost
PYTHONPATH=scripts arch -x86_64 .venv_x86/bin/python scripts/run_sector_specific_models.py
```

3. Collect baseline data:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/collect_kosis.py
```

4. Estimate 시도 quarterly GVA:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/denton_all_industries.py
```

5. Collect expanded 시군구/KSIC feasibility data:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/collect_expanded_kosis.py
```

6. Estimate 시군구 quarterly GVA:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/denton_sigungu.py
```

7. Check Seoul district-to-city quarterly consistency:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/check_seoul_sigungu_consistency.py
```

8. Allocate detailed manufacturing industries:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/allocate_detailed_industry.py
```

9. Collect and allocate eup/myeon/dong proxy GVA:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/collect_emd_economic_census.py
PYTHONPATH=scripts .venv/bin/python scripts/allocate_emd_gva.py
```

10. Collect energy exogenous indicators and build RECI:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/collect_energy_exogenous.py
PYTHONPATH=scripts .venv/bin/python scripts/build_reci.py
```

11. Collect ECOS augmentation datasets:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/probe_ecos_sources.py
PYTHONPATH=scripts .venv/bin/python scripts/collect_ecos_augmented_data.py
```

12. Run release-aware exogenous backtests and confidence scoring:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/test_energy_augmented_indicator.py
PYTHONPATH=scripts .venv/bin/python scripts/build_confidence_scores.py
PYTHONPATH=scripts .venv/bin/python scripts/make_release_aware_report.py
```

13. Verify or rewrite local CSV outputs as CP949:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/ensure_cp949_csv.py
```

14. Stop any previous dashboard server before starting a refreshed one:

```bash
python3 scripts/stop_dashboard_server.py 8000
```

15. Open the local dashboard:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000/reports/dashboard/`.

## Current Feasibility Findings

- 시군구 annual GRVA benchmarks are available for 16 provincial tables, with full common availability over `2020-2022`.
- Seoul district quarterly estimates can be checked against the parent Seoul quarterly path by summing the 25 district rows and comparing them with the Seoul 시도 estimate.
- Mining/manufacturing supports stable `시군구 × KSIC 중분류` coverage for 2020-2024.
- KSIC 소분류 and 세분류 rows are mostly limited to 시도 or national coverage in KOSIS.
- 읍면동 economic GVA/production benchmarks were not found in KOSIS, but 2015 economic census proxy data can allocate 시군구 quarterly GVA down to 읍면동. These estimates should be treated as proxy allocations, not official GVA.
- ECOS did not expose direct regional GRDP/GVA actuals in the 1st-pass scan, but it is useful for national account cross-checks, GDP deflators, input-output priors, and domestic price/fx exogenous variables.
- Release-aware electric/gas exogenous correction worsened MAPE in the current backtest, so it is kept as a diagnostic candidate rather than adopted automatically.
- Dynamic confidence grades are generated in `estimate_confidence_scores.csv` and displayed in the dashboard when the local processed data is available.
