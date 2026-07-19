from __future__ import annotations

import numpy as np
import pandas as pd

from phase33_common import DERIVED_DIR, add_audit, num, read_csv, write_csv


def build_share_lineage() -> pd.DataFrame:
    rows = []
    a1 = read_csv(DERIVED_DIR / "phase33_product_a1_spatial.csv")
    for row in a1.to_dict("records"):
        rows.append(
            {
                "value_id": f"A1|{row['reference_period']}|{row['emd_code']}|{row['ksic_section_code']}",
                "product_id": "A1",
                "source_id": row["source_id"],
                "source_family_id": row["source_family_id"],
                "source_row_id": row["source_row_id"],
                "source_period": row["reference_period"],
                "source_grain": "emd×KSIC_section×snapshot",
                "source_value": f"business={row['business_count']};employees={row['employee_count']}",
                "transform_id": row["transform_id"],
                "share_policy_id": "equal_business_employee_composite",
                "fallback_policy_id": "none",
                "fallback_reason": "",
                "reconciliation_method": "within_sigungu_industry_normalization",
                "reconciliation_adjustment": 0.0,
                "output_value": row["spatial_activity_share"],
                "effective_region_level": row["effective_region_level"],
                "effective_industry_level": row["effective_industry_level"],
                "effective_time_level": row["effective_time_level"],
                "evidence_grade": row["evidence_grade"],
                "claim_scope": row["claim_scope"],
            }
        )
    a2 = read_csv(DERIVED_DIR / "phase33_product_a2_fine_industry.csv")
    for row in a2.to_dict("records"):
        metric_missing = row["business_count"] == "" or row["employee_count"] == ""
        rows.append(
            {
                "value_id": f"A2|{row['year']}|{row['area_code']}|{row['industry_code']}",
                "product_id": "A2",
                "source_id": "S_FINE_BE",
                "source_family_id": row["source_family_id"],
                "source_row_id": f"S_FINE_BE|{row['year']}|{row['area_code']}|{row['industry_code']}",
                "source_period": row["year"],
                "source_grain": "sigungu×KSIC_middle×annual",
                "source_value": f"business={row['business_count']};employees={row['employee_count']}",
                "transform_id": "A2_COMPOSITE_AND_LQ",
                "share_policy_id": "within_sigungu_middle_composition",
                "fallback_policy_id": "single_metric_when_other_missing" if metric_missing else "none",
                "fallback_reason": "metric_missing" if metric_missing else "",
                "reconciliation_method": "within_sigungu_normalization",
                "reconciliation_adjustment": 0.0,
                "output_value": row["industry_structure_index"],
                "effective_region_level": row["effective_region_level"],
                "effective_industry_level": row["effective_industry_level"],
                "effective_time_level": row["effective_time_level"],
                "evidence_grade": row["evidence_grade"],
                "claim_scope": row["claim_scope"],
            }
        )
    c = read_csv(DERIVED_DIR / "phase33_product_c_allocation.csv")
    for row in c.to_dict("records"):
        rows.append(
            {
                "value_id": f"C|{row['year']}|{row['emd_code']}|{row['sector_code']}",
                "product_id": "C",
                "source_id": f"{row['parent_gva_source_id']}+{row['share_source_id']}",
                "source_family_id": "official_sigungu_GVA+economic_census_2015",
                "source_row_id": f"C_PARENT|{row['year']}|{row['sigungu_code']}|{row['sector_code']}",
                "source_period": f"parent={row['year']};share=2015",
                "source_grain": "sigungu×broad×annual + emd×section×snapshot",
                "source_value": f"parent={row['target_value']};share={row['allocation_share']}",
                "transform_id": row["allocation_policy_id"],
                "share_policy_id": "historical_industry_specific_composite",
                "fallback_policy_id": "none",
                "fallback_reason": "",
                "reconciliation_method": row["reconciliation_method"],
                "reconciliation_adjustment": row["reconciliation_adjustment"],
                "output_value": row["allocated_gva"],
                "effective_region_level": row["effective_region_level"],
                "effective_industry_level": row["effective_industry_level"],
                "effective_time_level": row["effective_time_level"],
                "evidence_grade": row["evidence_grade"],
                "claim_scope": row["claim_scope"],
            }
        )
    return add_audit(pd.DataFrame(rows))


def main() -> int:
    lineage = build_share_lineage()
    required = ["source_id", "source_family_id", "source_row_id", "transform_id", "claim_scope"]
    if lineage[required].eq("").any().any():
        raise AssertionError("missing required value lineage")
    if np.isinf(num(lineage["output_value"])).any():
        raise AssertionError("infinite output value")
    write_csv("phase33_share_lineage.csv", lineage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
