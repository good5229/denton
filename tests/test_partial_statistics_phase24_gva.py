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


def test_phase24_policy_equivalence_and_unique_registry() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase24_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["qp1_qp2_qp3_equivalent"] is True
    assert final["independent_parent_policy_count"] == 2
    assert final["qp1_frozen"] is True
    assert final["production_use"] is False
    assert final["official_statistics_claim"] is False

    eq = read_csv("partial_stats_phase24_gva_policy_equivalence_matrix.csv")
    q12 = eq[(eq["left_policy_id"].eq("QP1_G_national_growth_bridge")) & (eq["right_policy_id"].eq("QP2_G_indicator_growth_bridge"))].iloc[0]
    q13 = eq[(eq["left_policy_id"].eq("QP1_G_national_growth_bridge")) & (eq["right_policy_id"].eq("QP3_G_pooled_robust_growth"))].iloc[0]
    assert float(q12["maximum_prediction_difference"]) < 1e-9
    assert float(q13["maximum_prediction_difference"]) < 1e-9
    assert q12["equivalence_status"] == "alias_registration_error"
    assert q13["equivalence_status"] == "alias_registration_error"

    registry = read_csv("partial_stats_phase24_gva_unique_policy_registry.csv")
    retained = set(registry[registry["unique_registry_status"].eq("retained_unique_policy")]["policy_id"])
    removed = set(registry[registry["unique_registry_status"].eq("removed_alias_prediction_equivalent_to_qp1")]["policy_id"])
    assert retained == {"QP0_G_seasonal_growth", "QP1_G_national_growth_bridge"}
    assert removed == {"QP2_G_indicator_growth_bridge", "QP3_G_pooled_robust_growth"}


def test_phase24_artifact_source_and_origin_guards() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase24_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["superseded_invalid_artifact_count"] >= 1
    assert final["qualified_quarterly_source_count"] == 0
    assert final["responsive_origin_count"] == 0

    superseded = read_csv("partial_stats_phase24_gva_superseded_artifact_registry.csv")
    assert superseded["allowed_for_training"].astype(str).str.lower().eq("false").all()
    assert superseded["artifact_status"].str.contains("superseded_invalid_period_key", regex=False).any()

    sources = read_csv("partial_stats_phase24_gva_quarterly_source_registry.csv")
    assert sources["source_status"].eq("materialized").sum() == final["materialized_quarterly_source_count"]
    assert sources["qualified_for_primary_origin_responsive"].eq("Y").sum() == 0

    response = read_csv("partial_stats_phase24_gva_model_response_audit.csv")
    expected = response[response["response_expected"].astype(str).str.lower().eq("true")]
    assert len(expected) > 0
    assert expected["origin_response_status"].eq("expected_response_missing").all()


def test_phase24_spatial_temporal_deflator_and_archives() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase24_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["spatial_registered_source_count"] >= 3
    assert final["spatial_materialized_source_count"] == 1
    assert final["selected_spatial_policy"] == "SW0_last_annual_gva_share"
    assert final["selected_temporal_policy"] == "TP1_project_parent_proxy_profile"
    assert final["real_nominal_bridge_status"] == "real_nominal_bridge_blocked"
    assert final["archive_2026q2_integrity"] == "pass_existing_archive_preserved"

    spatial = read_csv("partial_stats_phase24_gva_spatial_policy_selection.csv").iloc[0]
    assert int(spatial["materialized_source_count"]) == 1
    assert spatial["selection_status"] == "spatial_last_share_retained"

    temporal = read_csv("partial_stats_phase24_gva_temporal_policy_selection.csv").iloc[0]
    assert temporal["selection_status"] == "temporal_profile_baseline_retained"

    archive = read_csv("partial_stats_phase24_gva_2026q2_archive_integrity.csv").iloc[0]
    assert str(archive["archive_immutable"]).lower() == "true"
    assert archive["original_prediction_hash"] == archive["current_prediction_hash"]

    q3 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_2026q3_forecast_archive.parquet")
    assert q3["target_period"].eq("2026Q3").all()
    assert q3["official_actual_used"].eq("N").all()


def test_phase24_report_and_topic_index() -> None:
    report = (ROOT / "reports" / "partial_statistics_estimation_phase24_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 38))
    assert "Model Identity Audit" in report
    assert "Policy Equivalence" in report
    assert "2026Q2 Prospective Archive" in report
    assert "아직 주장" in report

    topic_index = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase24_gva.md" in topic_index
