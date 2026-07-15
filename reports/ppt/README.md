# Editable Portfolio PPT

## Output

- `portfolio_implementation_editable.pptx`: one-slide portfolio implementation deck.
- `portfolio_fill_blocks_editable.pptx`: copy-ready right-side and bottom supplemental blocks for the user's composed slide.
- `ai_industry_monitoring_editable.pptx`: one-slide editable deck summarizing the BOK AI industry monitoring report process.
- `ai_industry_monitoring_fill_blocks_editable.pptx`: two-slide copy-ready supplemental block deck for the AI monitoring slide.
- `preview/portfolio_implementation_editable.pptx.png`: QuickLook-rendered preview used for visual verification.
- `preview/portfolio_fill_blocks_editable.pptx.png`: QuickLook-rendered preview for the supplemental block deck.
- `preview/ai_industry_monitoring_editable.pptx.png`: QuickLook-rendered preview for the AI monitoring deck.

## Source

- Generator: `../../scripts/make_portfolio_ppt.py`
- Supplemental block generator: `../../scripts/make_portfolio_fill_blocks_ppt.py`
- AI monitoring generator: `../../scripts/make_ai_monitoring_ppt.py`
- AI monitoring supplemental block generator: `../../scripts/make_ai_monitoring_fill_blocks_ppt.py`

## Editability

The PPT slide is built from separate PowerPoint shapes and text boxes. It does not use a flattened PNG for the main slide content.

Current structure:

- 1 slide
- 77 selectable elements
- 73 text-bearing elements

Supplemental block deck structure:

- 1 slide
- 46 selectable elements
- 46 text-bearing elements

AI monitoring deck structure:

- 1 slide
- 72 selectable elements
- 48 text-bearing elements

AI monitoring supplemental block deck structure:

- 2 slides
- Slide size: 20 x 11.25 inches, matching `/Users/bellhundred/Documents/Portfolio_202607.pptx`
- Slide 1: portfolio-positioned overlay blocks for direct paste into the AI monitoring slide
- Slide 2: full-page block catalog
- Slide 3: compressed block catalog

## Verification Notes

- Initial PPT generation produced separate elements, but a connector arrow setting caused readback errors in `python-pptx`; replaced arrowheads with separate triangle shapes.
- QuickLook preview initially showed Korean text fallback and overflow; added explicit East Asian font settings and shortened labels.
- Final preview was checked for text overlap, clipped text, excessive wrapping, and readability at 16:9 slide size.
- Supplemental block preview initially had overflow in long descriptions and the `2019-2023` label; shortened the copy and changed the data label to `5년` with `2019~2023` as the note.
- AI monitoring preview initially had wrapped date text and overlaps in the process blocks; shortened labels and widened the date/title blocks before regenerating the final preview.
- AI monitoring supplemental preview initially had clipped section headings, a long validation line, and a wrapped `Implementation` label; shortened the headings and labels before regenerating the final deck.
- The user's portfolio deck uses a 20 x 11.25 inch canvas, while the first supplemental deck used the default 13.333 x 7.5 inch widescreen canvas. PowerPoint paste preserves physical size, so copied elements appeared about two-thirds as large. Regenerated the supplemental deck on the portfolio canvas and made slide 1 a sparse overlay with only the center/bottom elements.
