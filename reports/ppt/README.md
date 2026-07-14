# Editable Portfolio PPT

## Output

- `portfolio_implementation_editable.pptx`: one-slide portfolio implementation deck.
- `portfolio_fill_blocks_editable.pptx`: copy-ready right-side and bottom supplemental blocks for the user's composed slide.
- `preview/portfolio_implementation_editable.pptx.png`: QuickLook-rendered preview used for visual verification.
- `preview/portfolio_fill_blocks_editable.pptx.png`: QuickLook-rendered preview for the supplemental block deck.

## Source

- Generator: `../../scripts/make_portfolio_ppt.py`
- Supplemental block generator: `../../scripts/make_portfolio_fill_blocks_ppt.py`

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

## Verification Notes

- Initial PPT generation produced separate elements, but a connector arrow setting caused readback errors in `python-pptx`; replaced arrowheads with separate triangle shapes.
- QuickLook preview initially showed Korean text fallback and overflow; added explicit East Asian font settings and shortened labels.
- Final preview was checked for text overlap, clipped text, excessive wrapping, and readability at 16:9 slide size.
- Supplemental block preview initially had overflow in long descriptions and the `2019-2023` label; shortened the copy and changed the data label to `5년` with `2019~2023` as the note.
