from __future__ import annotations

import numpy as np
import pandas as pd

from phase33_common import MIN_RANK_N, PROCESSED_DIR, add_audit, assert_unique, num, read_csv, safe_div, write_csv


def build_product_a1() -> pd.DataFrame:
    source = read_csv(PROCESSED_DIR / "emd_economic_census_2015.csv")
    source = source[source["c2_id"].str.len().eq(7) & source["metric"].isin(["establishments", "employees"])].copy()
    source["source_value"] = num(source["value"])
    pivot = source.pivot_table(
        index=["c2_id", "c2_nm", "c1_id", "c1_nm"],
        columns="metric",
        values="source_value",
        aggfunc="sum",
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(
        columns={
            "c2_id": "emd_code",
            "c2_nm": "emd_name",
            "c1_id": "ksic_section_code",
            "c1_nm": "ksic_section_name",
            "establishments": "business_count",
            "employees": "employee_count",
        }
    )
    pivot["sigungu_code"] = pivot["emd_code"].str[:5]
    group = ["sigungu_code", "ksic_section_code"]
    pivot["business_share"] = safe_div(pivot["business_count"], pivot.groupby(group)["business_count"].transform("sum"))
    pivot["employee_share"] = safe_div(pivot["employee_count"], pivot.groupby(group)["employee_count"].transform("sum"))
    pivot["spatial_activity_share"] = pivot[["business_share", "employee_share"]].mean(axis=1, skipna=True)
    pivot["spatial_activity_share"] = safe_div(
        pivot["spatial_activity_share"], pivot.groupby(group)["spatial_activity_share"].transform("sum")
    )
    positive_median = pivot.groupby(group)["spatial_activity_share"].transform(
        lambda values: values[values.gt(0)].median()
    )
    pivot["spatial_intensity_index"] = safe_div(pivot["spatial_activity_share"], positive_median) * 100
    pivot["rank_n"] = pivot.groupby(group)["emd_code"].transform("count")
    raw_rank = pivot.groupby(group)["spatial_activity_share"].rank(ascending=False, method="min")
    pivot["rank_value"] = raw_rank.where(pivot["rank_n"].ge(MIN_RANK_N))
    pivot["rank_percentile"] = (
        1 - safe_div(pivot["rank_value"] - 1, pivot["rank_n"] - 1)
    ).where(pivot["rank_n"].ge(MIN_RANK_N))
    pivot["presence"] = np.where(
        pivot[["business_count", "employee_count"]].fillna(0).max(axis=1).gt(0),
        "observed_presence",
        "source_zero",
    )
    pivot["reference_period"] = "2015_snapshot"
    pivot["source_id"] = "S_EMD_2015"
    pivot["source_family_id"] = "economic_census_2015"
    pivot["source_row_id"] = (
        "S_EMD_2015|" + pivot["emd_code"] + "|" + pivot["ksic_section_code"]
    )
    pivot["transform_id"] = "A1_COMPOSITE_EQUAL_BUSINESS_EMPLOYMENT_WITHIN_SIGUNGU_SECTION"
    pivot["effective_region_level"] = "emd_admin_2015"
    pivot["effective_industry_level"] = "KSIC_section"
    pivot["effective_time_level"] = "2015_snapshot"
    pivot["evidence_grade"] = "D"
    pivot["claim_scope"] = "observed_historical_spatial_structure_proxy_not_GVA"
    pivot["source_family_count"] = 1
    pivot["source_freshness"] = "historical_snapshot_2015"
    pivot["fallback_used"] = "N"
    pivot["unavailable_reason"] = ""
    pivot["production_use"] = "false"
    pivot["official_statistics_claim"] = "false"
    output_columns = [
        "reference_period", "emd_code", "emd_name", "sigungu_code", "ksic_section_code",
        "ksic_section_name", "business_count", "employee_count", "business_share",
        "employee_share", "spatial_activity_share", "spatial_intensity_index", "rank_n",
        "rank_value", "rank_percentile", "presence", "source_id", "source_family_id",
        "source_row_id", "transform_id", "effective_region_level", "effective_industry_level",
        "effective_time_level", "evidence_grade", "claim_scope", "source_family_count",
        "source_freshness", "fallback_used", "unavailable_reason", "production_use",
        "official_statistics_claim",
    ]
    output = pivot[output_columns].sort_values(
        ["sigungu_code", "ksic_section_code", "emd_code"]
    ).reset_index(drop=True)
    assert_unique(output, ["reference_period", "emd_code", "ksic_section_code"], "Product A1")
    return add_audit(output)


def main() -> int:
    write_csv("phase33_product_a1_spatial.csv", build_product_a1())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
