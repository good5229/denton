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


def test_phase23_official_target_semantics_and_cardinality() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase23_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["official_target_rows"] == 1740
    assert final["primary_target_rows"] == 340
    assert final["deduplicated_target_rows"] == 1650
    assert final["growth_contribution_separated"] is True
    assert final["official_statistics_claim"] is False
    assert final["production_use"] is False

    semantic = read_csv("partial_stats_phase23_gva_official_target_semantic_audit.csv")
    assert semantic["primary_evaluation_flag"].eq("Y").sum() == 340
    assert semantic["row_role"].eq("duplicate_print").sum() == 90

    cardinality = read_csv("partial_stats_phase23_gva_official_target_cardinality.csv")
    assert cardinality["status"].str.contains("pass", regex=False).all()


def test_phase23_period_identity_and_prospective_archive() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase23_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["period_key_error_rows_phase23"] == 0
    assert final["official_2026q1_parent_reflected"] is True
    assert final["prospective_holdout_status"] == "frozen_waiting_first_release"

    period = read_csv("partial_stats_phase23_gva_period_key_registry.csv")
    expected = period["year"].astype(str) + "Q" + period["quarter"].astype(str)
    assert period["period"].eq(period["target_period"]).all()
    assert period["period"].eq(expected).all()

    output = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_quarterly_output_2026.parquet")
    expected_output = output["year"].astype(str) + "Q" + output["quarter"].astype(str)
    assert output["period"].eq(output["target_period"]).all()
    assert output["period"].eq(expected_output).all()

    archive = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_prospective_forecast_archive.parquet")
    assert archive["target_period"].eq("2026Q2").all()
    assert archive["period"].eq(archive["target_period"]).all()
    assert archive["archive_status"].eq("frozen_waiting_first_release").all()


def test_phase23_official_alignment_and_policy_selection() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase23_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["official_alignable_policy_count"] == 4
    assert final["missing_prediction_blocked_policy_count"] == 2
    assert final["real_growth_track_status"] == "official_aligned_growth_track_materialized"
    assert final["nominal_level_track_status"] == "development_estimate_track_retained"

    alignment = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_official_prediction_alignment.parquet")
    assert alignment["alignment_status"].eq("aligned_primary").all()
    assert alignment["absolute_error_pp"].notna().all()
    assert set(alignment["policy_id"]) == {
        "QP0_G_seasonal_growth",
        "QP1_G_national_growth_bridge",
        "QP2_G_indicator_growth_bridge",
        "QP3_G_pooled_robust_growth",
    }

    accuracy = read_csv("partial_stats_phase23_gva_official_growth_accuracy.csv")
    assert pd.to_numeric(accuracy["official_mae_pp"], errors="coerce").notna().all()
    selection = read_csv("partial_stats_phase23_gva_official_policy_selection.csv")
    assert selection["production_use"].astype(str).str.lower().eq("false").all()
    assert selection["official_statistics_claim"].astype(str).str.lower().eq("false").all()


def test_phase23_spatial_temporal_and_report() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase23_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["spatial_weight_source_count"] >= 3
    assert 0 <= final["indicator_profile_rate"] <= 1
    assert 0 <= final["fallback_profile_rate"] <= 1
    assert final["monthly_primary_status"] == "blocked"
    assert final["uncertainty_status"] == "scenario_only"

    coverage = read_csv("partial_stats_phase23_gva_profile_coverage.csv")
    assert pd.to_numeric(coverage["indicator_profile_rate"], errors="coerce").between(0, 1).all()
    assert pd.to_numeric(coverage["fallback_profile_rate"], errors="coerce").between(0, 1).all()

    report = (ROOT / "reports" / "partial_statistics_estimation_phase23_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 45))
    assert "Official Prediction Alignment" in report
    assert "Prospective Holdout" in report
    assert "아직 주장" in report

    topic_index = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase23_gva.md" in topic_index
