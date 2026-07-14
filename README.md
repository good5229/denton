# Regional GVA Denton Reconstruction

This project reconstructs quarterly regional gross value added (GVA) estimates for Korea using public KOSIS data and the proportional Denton method. It is inspired by the Bank of Korea issue note on developing and using regional economic activity indicators.

## What This Repository Contains

- KOSIS OpenAPI collection scripts for regional GVA, production indices, GDP benchmarks, deflators, construction indicators, and subregional feasibility data.
- Proportional Denton estimation scripts for converting annual regional GVA benchmarks into quarterly estimates.
- Expanded data-discovery logic for checking whether the model can move from `시도 × 대분류` to `시군구`, `읍면동`, and detailed KSIC industry classes.
- Portfolio-oriented documentation and figure generation scripts that explain the methodology and implementation flow.

The collected data files, local harness instructions, and PowerPoint files are intentionally excluded from git. Re-run the collection scripts with a valid KOSIS API key to reproduce local outputs.

## Project Structure

```text
scripts/
  collect_kosis.py              # Collect baseline KOSIS datasets
  collect_expanded_kosis.py     # Collect subregional and detailed-industry feasibility datasets
  denton_reci.py                # Core proportional Denton implementation for selected sectors
  denton_all_industries.py      # All-industry 시도 quarterly estimation
  denton_sigungu.py             # 시군구 quarterly estimation using annual GRVA benchmarks
  make_figures.py               # Generate SVG/PNG documentation figures
  make_portfolio_ppt.py         # Generate editable portfolio PPT assets
reports/
  data_requirements.md          # Data requirements from the BOK note
  run_summary.md                # Baseline reconstruction summary
  expanded_data_feasibility.md  # 시군구/읍면동/KSIC feasibility findings
```

## Method Summary

The proportional Denton method estimates quarterly GVA values `X_t` from annual benchmarks `A_y` and quarterly indicators `I_t` by minimizing changes in the ratio `X_t / I_t`, subject to annual sum constraints:

```text
min Σ [(X_t / I_t) - (X_{t-1} / I_{t-1})]^2
s.t. Σ_q X_{y,q} = A_y
```

The baseline implementation uses regional production/service indices and national GDP profiles where direct regional quarterly indicators are unavailable. The 시군구 extension uses annual 시군구 GRVA as the benchmark and parent 시도 quarterly estimates as the quarterly movement indicator.

## Reproducing Locally

1. Create `.env` with `KOSIS_API_KEY`.
2. Install dependencies:

```bash
.venv/bin/pip install numpy python-pptx
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

## Current Feasibility Findings

- 시군구 annual GRVA benchmarks are available for 16 provincial tables, with full common availability over `2020-2022`.
- Mining/manufacturing supports stable `시군구 × KSIC 중분류` coverage for 2020-2024.
- KSIC 소분류 and 세분류 rows are mostly limited to 시도 or national coverage in KOSIS.
- 읍면동 economic GVA/production benchmarks were not found in KOSIS, so 읍면동 extension should be treated as a proxy allocation problem.
