#!/usr/bin/env python3
"""Verify Phase53/54 outputs."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> None:
    required = [
        PROCESSED / "partial_stats_phase53_candidate_source_manifest.csv",
        PROCESSED / "partial_stats_phase53_realestate_broker_goyang_pohang.csv",
        PROCESSED / "partial_stats_phase53_realestate_broker_gu_features.csv",
        PROCESSED / "partial_stats_phase53_korail_station_monthly_features.csv",
        PROCESSED / "partial_stats_phase53_storage_inventory.csv",
        PROCESSED / "partial_stats_phase54_specialized_allocation_cell_errors.csv",
        PROCESSED / "partial_stats_phase54_specialized_allocation_summary.csv",
        REPORTS / "partial_statistics_estimation_phase53_free_candidate_collection.md",
        REPORTS / "partial_statistics_estimation_phase54_specialized_allocation_improvement.md",
    ]
    for path in required:
        require(path.exists(), f"missing output: {path}")
        require(path.stat().st_size > 0, f"empty output: {path}")

    manifest = pd.read_csv(PROCESSED / "partial_stats_phase53_candidate_source_manifest.csv")
    require({"downloaded", "deferred_large_15_58m_rows", "no_direct_file_url", "download_failed"}.issuperset(set(manifest["file_collection_status"])), "unknown collection status")
    require((manifest["source_id"].eq("goyang_real_estate_broker_file") & manifest["file_collection_status"].eq("downloaded")).any(), "goyang broker not marked downloaded")
    require((manifest["source_id"].eq("pohang_real_estate_broker_file") & manifest["file_collection_status"].eq("downloaded")).any(), "pohang broker not marked downloaded")
    require((manifest["source_id"].eq("korail_intercity_station_daily_passenger_file") & manifest["file_collection_status"].eq("downloaded")).any(), "korail not marked downloaded")
    require((manifest["source_id"].eq("niier_livestock_aquaculture_inventory") & manifest["file_collection_status"].eq("downloaded")).any(), "agriculture candidate not marked downloaded")

    broker = pd.read_csv(PROCESSED / "partial_stats_phase53_realestate_broker_gu_features.csv")
    require(set(broker["city"]) == {"고양시", "포항시"}, "broker cities incomplete")
    require((broker["broker_office_count"] > 0).all(), "broker counts should be positive")

    scores = pd.read_csv(PROCESSED / "partial_stats_phase54_specialized_allocation_summary.csv")
    require({"F", "H", "L"}.issubset(set(scores["sector"])), "missing specialized sectors")
    require((scores["mae_pp"] >= 0).all(), "negative MAE")
    require(scores["basis_id"].astype(str).str.contains("구 균등배분").any(), "missing equal-gu baseline")
    require(scores["basis_id"].astype(str).str.contains("중개업소").any(), "missing broker basis")
    require(scores["basis_id"].astype(str).str.contains("착공").any(), "missing construction start basis")

    print("phase53/54 verification passed")


if __name__ == "__main__":
    main()
