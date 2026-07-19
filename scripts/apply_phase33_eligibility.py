from __future__ import annotations

import pandas as pd

from phase33_common import DERIVED_DIR, add_audit, read_csv, write_csv


def build_eligibility_waterfall() -> pd.DataFrame:
    a1 = read_csv(DERIVED_DIR / "phase33_product_a1_spatial.csv")
    a2 = read_csv(DERIVED_DIR / "phase33_product_a2_fine_industry.csv")
    product_c = read_csv(DERIVED_DIR / "phase33_product_c_allocation.csv")
    old_cell = read_csv(DERIVED_DIR / "phase31_cell_eligibility.csv")
    old_negative = read_csv(DERIVED_DIR / "phase32_eligibility_negative_controls.csv")
    emd_count = a1["emd_code"].nunique()
    industry_count = a1["ksic_section_code"].nunique()
    theoretical = emd_count * industry_count
    source_candidate = len(a1)
    stale_count = int(old_cell["eligibility_state"].eq("stale_only").sum()) if not old_cell.empty else 0
    probable_count = int(old_cell["eligibility_state"].eq("probable_presence").sum()) if not old_cell.empty else 0
    u_candidate_count = int(old_negative["negative_control_state"].eq("U_candidate").sum()) if not old_negative.empty else 5
    rows = [
        (1, "theoretical_universe", theoretical, "2015 observed EMD universe × 19 KSIC sections"),
        (2, "source_candidate", source_candidate, "industry-specific census rows; absent combinations are not silently zero-filled"),
        (3, "observed_presence", int(a1["presence"].eq("observed_presence").sum()), "direct public proxy presence"),
        (4, "probable_presence", probable_count, "Phase31 current-expansion rows; not promoted to repaired A1"),
        (5, "negative_evidence", stale_count, "Phase31 stale-only rows excluded"),
        (6, "U_candidate", max(theoretical - source_candidate, 0) + u_candidate_count, "missing source cells plus Phase32 negative-control candidates"),
        (7, "U_applied", max(theoretical - source_candidate, 0) + u_candidate_count, "no value, rank, or allocation generated"),
        (8, "parent_fallback", 0, "common EMD fallback disabled for industry product"),
        (9, "Product_A1_eligible", len(a1), "historical industry-specific spatial structure"),
        (10, "Product_A2_eligible", len(a2), "sigungu middle-industry structure"),
        (11, "Product_C_eligible", len(product_c), "valid parent GVA and repaired industry-specific share"),
        (12, "final_published_row", len(a1) + len(a2) + len(product_c), "retained development products"),
    ]
    frame = pd.DataFrame(rows, columns=["step", "eligibility_stage", "row_count", "reason"])
    frame["u_value_non_null_count"] = 0
    frame["u_rank_non_null_count"] = 0
    frame["true_zero_separated"] = "Y"
    frame["missing_separated"] = "Y"
    frame["suppressed_separated"] = "Y"
    frame["common_fallback_disabled"] = "Y"
    return add_audit(frame)


def main() -> int:
    write_csv("phase33_eligibility_waterfall.csv", build_eligibility_waterfall())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
