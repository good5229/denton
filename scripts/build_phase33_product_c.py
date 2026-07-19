from __future__ import annotations

import numpy as np
import pandas as pd

from phase33_common import DERIVED_DIR, PROCESSED_DIR, add_audit, assert_unique, num, read_csv, read_table, safe_div, write_csv


SECTION_TO_PARENT = {
    "A": "A00", "B": "B00", "C": "C00", "D": "D00", "E": "ERS", "F": "F00",
    "G": "G00", "H": "H00", "I": "I00", "J": "J00", "K": "K00", "L": "L00",
    "M": "MN0", "N": "MN0", "O": "O00", "P": "P00", "Q": "Q00", "R": "ERS", "S": "ERS",
}


def build_product_c() -> tuple[pd.DataFrame, pd.DataFrame]:
    a1 = read_csv(DERIVED_DIR / "phase33_product_a1_spatial.csv")
    for column in ["business_count", "employee_count"]:
        a1[column] = num(a1[column])
    a1["parent_sector_code"] = a1["ksic_section_code"].map(SECTION_TO_PARENT)
    broad = a1.groupby(
        ["emd_code", "emd_name", "sigungu_code", "parent_sector_code"], as_index=False
    ).agg(business_count=("business_count", "sum"), employee_count=("employee_count", "sum"))
    group = ["sigungu_code", "parent_sector_code"]
    broad["business_share"] = safe_div(broad["business_count"], broad.groupby(group)["business_count"].transform("sum"))
    broad["employee_share"] = safe_div(broad["employee_count"], broad.groupby(group)["employee_count"].transform("sum"))
    broad["allocation_share"] = broad[["business_share", "employee_share"]].mean(axis=1, skipna=True)
    broad["allocation_share"] = safe_div(broad["allocation_share"], broad.groupby(group)["allocation_share"].transform("sum"))

    parent = read_table(PROCESSED_DIR / "partial_stats_phase28_gva_annual_target_cube.parquet").copy()
    parent = parent[
        parent["region_level"].eq("sigungu")
        & parent["period_frequency"].eq("annual")
        & parent["price_basis"].eq("nominal")
        & parent["actual_status"].astype(str).str.contains("direct_annual")
    ].copy()
    parent["year"] = parent["year"].astype(str)
    parent["target_value"] = num(parent["target_value"])
    parent = parent[["year", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "target_value", "actual_status", "estimate_status"]]
    merged = parent.merge(
        broad,
        left_on=["sigungu_code", "sector_code"],
        right_on=["sigungu_code", "parent_sector_code"],
        how="inner",
        validate="many_to_many",
    )
    merged["allocated_gva"] = merged["target_value"] * merged["allocation_share"]
    merged["parent_gva_source_id"] = "phase28_NA1_official_annual_anchor"
    merged["share_source_id"] = "S_EMD_2015"
    merged["source_family_count"] = 2
    merged["allocation_policy_id"] = "C1_HISTORICAL_INDUSTRY_SPECIFIC_COMPOSITE_SHARE"
    merged["reconciliation_method"] = "exact_parent_sum_normalized_share"
    merged["reconciliation_adjustment"] = 0.0
    merged["price_basis"] = "nominal"
    merged["unit"] = "source_parent_unit"
    merged["chain_volume_additivity_warning"] = "not_applicable_nominal_track; do_not_sum_real_chain_volume_without_review"
    merged["spatial_component_grade"] = "D"
    merged["parent_component_grade"] = "O"
    merged["evidence_grade"] = "D"
    merged["claim_scope"] = "GVA_consistent_historical_share_allocation_not_observed_EMD_GVA"
    merged["effective_region_level"] = "emd_admin_2015"
    merged["effective_industry_level"] = "project_broad_sector"
    merged["effective_time_level"] = "annual"
    merged["unavailable_reason"] = ""
    merged["production_use"] = "false"
    merged["official_statistics_claim"] = "false"
    output = merged[
        [
            "year", "sigungu_code", "sigungu_name", "emd_code", "emd_name", "sector_code",
            "sector_name", "target_value", "allocation_share", "allocated_gva", "parent_gva_source_id",
            "share_source_id", "source_family_count", "allocation_policy_id", "reconciliation_method",
            "reconciliation_adjustment", "price_basis", "unit", "chain_volume_additivity_warning",
            "spatial_component_grade", "parent_component_grade", "evidence_grade", "claim_scope",
            "effective_region_level", "effective_industry_level", "effective_time_level",
            "unavailable_reason", "production_use", "official_statistics_claim",
        ]
    ].sort_values(["year", "sigungu_code", "sector_code", "emd_code"]).reset_index(drop=True)
    assert_unique(output, ["year", "sigungu_code", "sector_code", "emd_code"], "Product C")
    checks = output.groupby(["year", "sigungu_code", "sector_code"], as_index=False).agg(
        parent_gva=("target_value", "first"),
        allocated_sum=("allocated_gva", lambda values: num(values).sum()),
        share_sum=("allocation_share", lambda values: num(values).sum()),
        row_count=("emd_code", "size"),
    )
    checks["absolute_conservation_error"] = (checks["parent_gva"] - checks["allocated_sum"]).abs()
    checks["status"] = np.where(checks["absolute_conservation_error"].lt(1e-6), "pass", "fail")
    return add_audit(output), add_audit(checks)


def main() -> int:
    output, checks = build_product_c()
    write_csv("phase33_product_c_allocation.csv", output)
    write_csv("phase33_conservation_checks.csv", checks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
