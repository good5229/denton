# Project Figures

Source-driven figures for the Denton/RECI reconstruction project.

## Outputs

- `fig01_pipeline.svg` / `fig01_pipeline.png`: data collection and estimation pipeline.
- `fig02_methods.svg` / `fig02_methods.png`: industry-specific indicator and benchmark strategy.
- `fig03_errors.svg` / `fig03_errors.png`: 2023 extrapolation error summary.
- `fig04_proportional_denton_method.svg` / `fig04_proportional_denton_method.png`: annual GVA to quarterly GVA allocation method.
- `fig05_proportional_denton_detail.svg` / `fig05_proportional_denton_detail.png`: detailed proportional Denton allocation logic.
- `fig06_portfolio_implementation.svg` / `fig06_portfolio_implementation.png`: portfolio/PPT technical implementation slide.

All PNG files are rendered at `1920 x 1080` from the SVG sources.

## Source

- Generator: `../../scripts/make_figures.py`
- Data inputs:
  - `../processed/kosis_collected_all.csv`
  - `../processed/all_industries_2023_extrapolation_errors.csv`
  - `../processed/all_industries_error_summary.csv`

## Verification Notes

- Used code-generated SVG as the editable source and regenerated raster PNG outputs from source.
- Avoided subtitle blocks, long file paths, and internal code names inside figures.
- Increased labels and values for document-scale readability, with compact labels where space was tight.
- Re-rendered with Chrome headless after QuickLook produced square cropped thumbnails.
- Fixed overlap in the pipeline figure by separating item labels and counts.
- Fixed overlap in the method figure by shortening service-industry labels and moving chips above the formula row.
- Added a method diagram that adapts the reference layout to the current logic: annual regional-industry GVA, quarterly indicators, proportional Denton smoothing, and 2023 last-ratio extrapolation.
- Fixed SVG text color precedence so labels inside colored cells render with sufficient contrast.
- Added a detailed method figure with input vectors, initial indicator-share allocation, proportional Denton objective and annual constraints, allocation output, and 2023 extrapolation validation.
- Used unequal-width indicator and output cells in the detailed figure to show that allocation follows indicator proportions but is smoothed by the Denton ratio constraint.
- Added a portfolio-oriented implementation figure that emphasizes data engineering, mapping logic, proportional Denton optimization, extrapolation validation, and reproducible outputs.
- Shortened bottom capability labels in the portfolio figure after visual verification found overflow risk in the initial wording.
- Visually checked the final PNG outputs for text overlap, broken line wrapping, excessive blank bands, and small unreadable text.

## Intentional Non-Changes

- Did not use an AI bitmap generator; these are structured diagrams and charts that should remain reproducible from source.
- Did not force ambiguous GDP benchmark splits into the method figure, because the underlying estimates already mark ambiguous national GDP mappings explicitly.
