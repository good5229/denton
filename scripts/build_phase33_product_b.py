from __future__ import annotations

import numpy as np
import pandas as pd

from phase33_common import PROCESSED_DIR, add_audit, assert_unique, num, read_table, write_csv


NEUTRAL_BAND_PERCENT = 0.5


def build_product_b() -> pd.DataFrame:
    current = PROCESSED_DIR.parent / "derived" / "phase33_service_source_current.parquet"
    source_path = current if current.exists() else PROCESSED_DIR / "partial_stats_phase27_gva_service_full_cube.parquet"
    source = read_table(source_path).copy()
    source["year"] = source["prd_de"].astype(str).str[:4].astype(int)
    source["quarter"] = source["prd_de"].astype(str).str[-2:].astype(int)
    source["reference_period"] = source["year"].astype(str) + "Q" + source["quarter"].astype(str)
    source["service_index"] = num(source["value"])
    source = source.sort_values(["c1_id", "c2_id", "year", "quarter"]).reset_index(drop=True)
    group = ["c1_id", "c2_id", "item_id"]
    source["service_index_lag4"] = source.groupby(group)["service_index"].shift(4)
    source["yoy_growth_percent"] = (source["service_index"] / source["service_index_lag4"] - 1) * 100
    source["direction"] = np.select(
        [source["yoy_growth_percent"].gt(NEUTRAL_BAND_PERCENT), source["yoy_growth_percent"].lt(-NEUTRAL_BAND_PERCENT)],
        ["up", "down"],
        default="neutral",
    )
    source.loc[source["yoy_growth_percent"].isna(), "direction"] = "unavailable_initial_lag"
    prior_direction = source.groupby(group)["direction"].shift(1)
    source["turning_point"] = np.where(
        source["direction"].isin(["up", "down"])
        & prior_direction.isin(["up", "down"])
        & source["direction"].ne(prior_direction),
        "Y",
        "N",
    )
    source["lag4_prediction"] = source["service_index_lag4"]
    source["lag4_absolute_percentage_error"] = (
        (source["service_index"] - source["lag4_prediction"]).abs() / source["service_index"].replace(0, np.nan)
    )
    source["source_id"] = "S_SERVICE_Q"
    source["source_family_id"] = "service_production_index"
    source["source_row_id"] = "S_SERVICE_Q|" + source["c1_id"].astype(str) + "|" + source["c2_id"].astype(str) + "|" + source["item_id"].astype(str) + "|" + source["reference_period"]
    source["service_index_type"] = np.where(source["item_id"].eq("T2"), "constant_volume_index", "current_price_index")
    source["value_type"] = "observed_official_service_activity_proxy"
    source["effective_region_level"] = "sido"
    source["effective_industry_level"] = "service_series"
    source["effective_time_level"] = "quarter"
    source["price_basis"] = np.where(source["item_id"].eq("T2"), "constant_volume_index_2020_100", "current_price_index_2020_100")
    source["seasonal_adjustment_status"] = "unadjusted_original"
    source["evidence_grade"] = "O_proxy"
    source["claim_scope"] = "observed_service_activity_index_not_GVA_RECI"
    source["release_vintage"] = "current_snapshot_release_archive_missing"
    source["unavailable_reason"] = np.where(source["yoy_growth_percent"].isna(), "four_quarter_lag_not_available", "")
    source["production_use"] = "false"
    source["official_statistics_claim"] = "false"
    output = source[
        [
            "reference_period", "year", "quarter", "c1_id", "c1_nm", "c2_id", "c2_nm", "item_id", "item_nm", "service_index_type",
            "service_index", "yoy_growth_percent", "direction", "turning_point", "lag4_prediction",
            "lag4_absolute_percentage_error", "source_id", "source_family_id", "source_row_id",
            "value_type", "effective_region_level", "effective_industry_level", "effective_time_level",
            "price_basis", "seasonal_adjustment_status", "evidence_grade", "claim_scope",
            "release_vintage", "unavailable_reason", "production_use", "official_statistics_claim",
        ]
    ].rename(columns={"c1_id": "sido_code", "c1_nm": "sido_name", "c2_id": "service_series_code", "c2_nm": "service_series_name"})
    assert_unique(output, ["reference_period", "sido_code", "service_series_code", "item_id"], "Product B")
    return add_audit(output)


def main() -> int:
    write_csv("phase33_product_b_temporal.csv", build_product_b())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
