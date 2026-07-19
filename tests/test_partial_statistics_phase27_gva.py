from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase27_service_full_collection_and_track_split() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase27_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["phase26_reproduction_status"] == "pass"
    assert final["service_observed_region_count"] == 17
    assert final["service_collection_completeness"] == "pass"

    service = read_csv("partial_stats_phase27_gva_service_collection_audit.csv").iloc[0]
    assert int(service["observed_row_count"]) == 9520
    assert int(service["duplicate_key_count"]) == 0
    assert float(service["region_coverage_rate"]) == 1.0
    assert float(service["industry_coverage_rate"]) == 1.0

    chunks = read_csv("partial_stats_phase27_gva_service_chunk_audit.csv")
    assert len(chunks) == 34
    assert chunks["collection_status"].eq("pass").all()

    strict = read_csv("partial_stats_phase27_gva_strict_source_registry.csv")
    pseudo = read_csv("partial_stats_phase27_gva_pseudo_source_registry.csv")
    assert strict["track"].eq("strict_asof").all()
    assert strict["evidence_grade"].isin(["R1", "R2", "R3"]).all()
    assert pseudo["track"].eq("pseudo_realtime_development").all()
    assert pseudo["evidence_grade"].isin(["R4", "R5"]).all()


def test_phase27_fine_output_quality_and_constraints() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase27_gva_final_status.json").read_text(encoding="utf-8"))
    layers = read_csv("partial_stats_phase27_gva_target_layer_registry.csv")
    assert layers["target_layer"].nunique() == 6
    assert layers[layers["target_layer"].eq("NQ1")]["direct_actual"].iloc[0] == "N"
    assert layers[layers["target_layer"].eq("NM1")]["status"].iloc[0] == "experimental_estimate"

    output = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase27_gva_fine_grained_output.parquet")
    assert (output["target_layer"] == "NQ1").sum() == final["fine_quarterly_output_row_count"]
    assert (output["target_layer"] == "NM1").sum() == final["fine_monthly_output_row_count"]
    assert output[output["target_layer"].eq("NA1")]["quality_grade"].eq("A").all()
    assert output[output["target_layer"].eq("NQ1")]["quality_grade"].eq("D").all()
    assert output[output["target_layer"].eq("NM1")]["quality_grade"].eq("E").all()

    rec = read_csv("partial_stats_phase27_gva_reconciliation_results.csv")
    assert pd.to_numeric(rec["adjustment_rate"], errors="coerce").max() < 1e-9


def test_phase27_challengers_not_overpromoted() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase27_gva_final_status.json").read_text(encoding="utf-8"))
    parent = read_csv("partial_stats_phase27_gva_parent_residual_results.csv")
    challenger = parent[parent["policy_id"].str.startswith("PR1")].iloc[0]
    assert float(challenger["mae_pp"]) < float(parent[parent["policy_id"].eq("QP1_G_national_growth_bridge")]["mae_pp"].iloc[0])
    assert challenger["selection_status"] == "not_selected_official_target_visible"
    assert final["selected_parent_policy"] == "QP1_G_national_growth_bridge"

    spatial = read_csv("partial_stats_phase27_gva_dynamic_spatial_share_results.csv")
    sw0 = spatial[spatial["policy_id"].eq("SW0")].iloc[0]
    swd = spatial[spatial["policy_id"].eq("SWD_Guarded_electricity_delta")].iloc[0]
    assert float(swd["share_mae"]) > float(sw0["share_mae"])
    assert swd["selection_status"] == "failed_SW0_better"
    assert final["selected_spatial_policy"] == "SW0_last_annual_gva_share"

    assert final["production_use"] is False
    assert final["official_statistics_claim"] is False


def test_phase27_prospective_and_report() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase27_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["holdout_2026q2_status"] == "waiting_first_release"
    assert "not_backdated" in final["archive_2026q3_integrity"]
    assert final["q4_preregistration_status"] == "created_policy_skeleton"

    q4 = json.loads((PROCESSED_DIR / "partial_stats_phase27_gva_2026q4_preregistration.json").read_text(encoding="utf-8"))
    assert q4["official_actual_used"] is False
    assert q4["archive_status"] == "preregistered_policy_skeleton_not_frozen_forecast"

    report = (ROOT / "reports" / "partial_statistics_estimation_phase27_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 33))
    assert "서비스업생산 전체수집" in report
    assert "Fine-grained Output Coverage" in report

    topic = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase27_gva.md" in topic
