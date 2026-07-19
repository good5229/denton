from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def parquet(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_parquet(path)


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase27_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "target changed")
    require(final["phase26_reproduction_status"] == "pass", "Phase26 reproduction failed")
    require(final["price_basis_separation_status"] == "real_growth_and_nominal_level_tracks_separated", "price basis mixed")
    require(final["holdout_2026q2_status"] == "waiting_first_release", "2026Q2 holdout consumed")
    require("not_backdated" in final["archive_2026q3_integrity"], "2026Q3 archive backdated or altered")
    require(final["q4_preregistration_status"] == "created_policy_skeleton", "2026Q4 preregistration missing")
    require(final["production_use"] is False and final["official_statistics_claim"] is False, "forbidden claim")

    service = csv("partial_stats_phase27_gva_service_collection_audit.csv").iloc[0]
    require(int(service["observed_region_count"]) == 17, "service regions incomplete")
    require(int(service["observed_industry_count"]) == 14, "service industries incomplete")
    require(int(service["observed_period_count"]) == 20, "service periods incomplete")
    require(int(service["duplicate_key_count"]) == 0, "service duplicate keys")
    require(int(service["observed_row_count"]) == 9520, "service row count mismatch")
    require(service["collection_status"] == "pass", "service collection not pass")

    chunks = csv("partial_stats_phase27_gva_service_chunk_audit.csv")
    require(len(chunks) == 34, "expected 17 regions x 2 item chunks")
    require(chunks["collection_status"].eq("pass").all(), "service chunk failure")

    strict = csv("partial_stats_phase27_gva_strict_source_registry.csv")
    pseudo = csv("partial_stats_phase27_gva_pseudo_source_registry.csv")
    require(strict["track"].eq("strict_asof").all(), "strict registry has non-strict track")
    require(strict["evidence_grade"].isin(["R1", "R2", "R3"]).all(), "strict registry contains R4/R5")
    require(pseudo["track"].eq("pseudo_realtime_development").all(), "pseudo registry has wrong track")
    require(pseudo["evidence_grade"].isin(["R4", "R5"]).all(), "pseudo registry should hold R4/R5 only here")

    layers = csv("partial_stats_phase27_gva_target_layer_registry.csv")
    require(layers["target_layer"].nunique() == 6, "target layer registry incomplete")
    require(layers[layers["target_layer"].eq("NQ1")]["direct_actual"].iloc[0] == "N", "quarterly child actual overclaimed")
    require(layers[layers["target_layer"].eq("NM1")]["status"].iloc[0] == "experimental_estimate", "monthly layer should be experimental")

    fine = parquet("partial_stats_phase27_gva_fine_grained_output.parquet")
    require((fine["target_layer"] == "NQ1").sum() == final["fine_quarterly_output_row_count"], "quarterly output count mismatch")
    require((fine["target_layer"] == "NM1").sum() == final["fine_monthly_output_row_count"], "monthly output count mismatch")
    require(fine[fine["target_layer"].eq("NM1")]["quality_grade"].eq("E").all(), "monthly output should be quality E")
    require(fine[fine["target_layer"].eq("NQ1")]["quality_grade"].eq("D").all(), "quarterly output should be quality D")
    require(fine[fine["target_layer"].eq("NA1")]["direct_actual_validation"].eq("Y").all(), "annual anchor should be direct validation")

    parent = csv("partial_stats_phase27_gva_parent_residual_results.csv")
    challenger = parent[parent["policy_id"].str.startswith("PR1")].iloc[0]
    require(challenger["selection_status"] == "not_selected_official_target_visible", "diagnostic parent challenger overpromoted")
    require(final["selected_parent_policy"] == "QP1_G_national_growth_bridge", "parent incumbent not retained")

    spatial = csv("partial_stats_phase27_gva_dynamic_spatial_share_results.csv")
    sw0 = spatial[spatial["policy_id"].eq("SW0")].iloc[0]
    swd = spatial[spatial["policy_id"].eq("SWD_Guarded_electricity_delta")].iloc[0]
    require(float(swd["share_mae"]) > float(sw0["share_mae"]), "SWD should not beat SW0 in this run")
    require(swd["selection_status"] == "failed_SW0_better", "SWD overpromoted")
    require(final["selected_spatial_policy"] == "SW0_last_annual_gva_share", "spatial incumbent not retained")

    industry = csv("partial_stats_phase27_gva_industry_share_results.csv")
    temporal = csv("partial_stats_phase27_gva_temporal_profile_results.csv")
    require(industry[industry["policy_id"].str.startswith("IS1")]["result"].iloc[0].startswith("not_scored"), "industry challenger overpromoted")
    require(temporal[temporal["policy_id"].str.startswith("TP9")]["result"].iloc[0].startswith("not_promoted"), "temporal challenger overpromoted")

    rec = csv("partial_stats_phase27_gva_reconciliation_results.csv")
    require(pd.to_numeric(rec["adjustment_rate"], errors="coerce").max() < 1e-9, "reconciliation overadjusted")
    material = csv("partial_stats_phase27_gva_material_degradation.csv")
    require(material["promotion_status"].eq("blocked").all(), "material degradation not blocking")

    q4 = json.loads((PROCESSED_DIR / "partial_stats_phase27_gva_2026q4_preregistration.json").read_text(encoding="utf-8"))
    require(q4["official_actual_used"] is False, "Q4 preregistration used actual")
    require(q4["archive_status"] == "preregistered_policy_skeleton_not_frozen_forecast", "unexpected Q4 archive status")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase27_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 33)), "report sections must be 1..32")
    for phrase in ["서비스업생산 전체수집", "Strict·Pseudo Track 분리", "Fine-grained Output Coverage", "아직 주장"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
