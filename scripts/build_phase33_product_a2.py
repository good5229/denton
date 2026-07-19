from __future__ import annotations

import numpy as np
import pandas as pd

from phase33_common import PROCESSED_DIR, add_audit, assert_unique, num, read_csv, safe_div, write_csv


def build_product_a2() -> pd.DataFrame:
    source = read_csv(PROCESSED_DIR / "business_employment_feature_table.csv")
    source = source[
        source["industry_level"].eq("middle")
        & source["metric"].isin(["establishments", "employees"])
        & source["area_code"].str.len().eq(5)
    ].copy()
    source["source_value"] = num(source["value"])
    pivot = source.pivot_table(
        index=["year", "area_code", "area_name", "industry_code", "industry_name"],
        columns="metric",
        values="source_value",
        aggfunc="sum",
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(columns={"establishments": "business_count", "employees": "employee_count"})
    for column in ["business_count", "employee_count"]:
        if column not in pivot:
            pivot[column] = np.nan

    region_group = ["year", "area_code"]
    pivot["business_share"] = safe_div(
        pivot["business_count"], pivot.groupby(region_group)["business_count"].transform("sum")
    )
    pivot["employee_share"] = safe_div(
        pivot["employee_count"], pivot.groupby(region_group)["employee_count"].transform("sum")
    )
    pivot["industry_structure_index"] = pivot[["business_share", "employee_share"]].mean(axis=1, skipna=True)
    pivot["industry_structure_index"] = safe_div(
        pivot["industry_structure_index"], pivot.groupby(region_group)["industry_structure_index"].transform("sum")
    )

    national = pivot.groupby(["year", "industry_code"], as_index=False)["employee_count"].sum(min_count=1)
    national["national_employee_share"] = safe_div(
        national["employee_count"], national.groupby("year")["employee_count"].transform("sum")
    )
    pivot = pivot.merge(
        national[["year", "industry_code", "national_employee_share"]],
        on=["year", "industry_code"],
        how="left",
        validate="many_to_one",
    )
    pivot["location_quotient"] = safe_div(pivot["employee_share"], pivot["national_employee_share"])
    pivot["rank_within_region"] = pivot.groupby(region_group)["industry_structure_index"].rank(ascending=False, method="min")
    pivot["rank_within_industry"] = pivot.groupby(["year", "industry_code"])["industry_structure_index"].rank(ascending=False, method="min")

    factory = read_csv(PROCESSED_DIR / "factory_feature_table.csv")
    factory_keys = set(factory.loc[num(factory["feature_value"]).gt(0), "sigungu_feature_key"].astype(str)) if not factory.empty else set()
    pivot["factory_presence_support"] = np.where(
        pivot["industry_code"].str.startswith("C")
        & pivot["area_name"].map(lambda name: any(key.endswith(str(name)) for key in factory_keys)),
        "broad_manufacturing_presence_only",
        "not_applicable_or_unmatched",
    )
    pivot["presence_support"] = np.where(
        pivot[["business_count", "employee_count"]].fillna(0).max(axis=1).gt(0),
        "observed_same_family_business_employment",
        "missing_or_zero",
    )
    pivot["source_status"] = "public_related_family_development_snapshot"
    pivot["source_family_id"] = "manufacturing_mining_sigungu_ksic"
    pivot["independent_family_count"] = np.where(
        pivot["factory_presence_support"].eq("broad_manufacturing_presence_only"), 2, 1
    )
    pivot["ksic_version"] = "KSIC10_source_table_assumed; official crosswalk registry retained"
    pivot["suppression_status"] = "not_explicitly_identified_in_materialized_source"
    pivot["evidence_grade"] = "D"
    pivot["claim_scope"] = "sigungu_middle_industry_structure_proxy_not_fine_GVA"
    pivot["effective_region_level"] = "sigungu"
    pivot["effective_industry_level"] = "KSIC_middle"
    pivot["effective_time_level"] = "annual_snapshot"
    pivot["production_use"] = "false"
    pivot["official_statistics_claim"] = "false"
    output = pivot[
        [
            "area_code", "area_name", "industry_code", "industry_name", "year",
            "business_count", "employee_count", "business_share", "employee_share",
            "industry_structure_index", "location_quotient", "rank_within_region",
            "rank_within_industry", "presence_support", "factory_presence_support",
            "source_status", "source_family_id", "independent_family_count", "ksic_version",
            "suppression_status", "evidence_grade", "claim_scope", "effective_region_level",
            "effective_industry_level", "effective_time_level", "production_use",
            "official_statistics_claim",
        ]
    ].sort_values(["year", "area_code", "industry_code"]).reset_index(drop=True)
    assert_unique(output, ["year", "area_code", "industry_code"], "Product A2")
    return add_audit(output)


def main() -> int:
    write_csv("phase33_product_a2_fine_industry.csv", build_product_a2())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
