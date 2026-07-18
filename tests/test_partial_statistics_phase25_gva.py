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


def test_phase25_reproduction_release_and_join_gates() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase25_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["phase24_reproduction_status"] == "pass"
    assert final["archive_2026q2_integrity"] == "pass_existing_archive_preserved"
    assert final["many_to_many_join_count"] == 0
    assert float(final["join_row_inflation_rate"]) == 0.0
    assert final["r1_r3_qualified_source_count"] == 0
    assert final["production_use"] is False
    assert final["official_statistics_claim"] is False

    reproduction = read_csv("partial_stats_phase25_gva_phase24_reproduction.csv")
    assert reproduction["reproduction_status"].eq("pass").all()

    indicator = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_indicator_cube.parquet")
    key = [
        "source_family",
        "series_id",
        "region_code",
        "industry_code",
        "measure_type",
        "unit",
        "seasonal_adjustment",
        "price_basis",
        "observation_period",
        "vintage_id",
    ]
    assert not indicator.duplicated(key).any()

    join = read_csv("partial_stats_phase25_gva_join_cardinality_audit.csv").iloc[0]
    assert join["join_status"] == "pass"
    assert int(join["many_to_many_join_count"]) == 0

    evidence = read_csv("partial_stats_phase25_gva_release_evidence_registry.csv")
    assert evidence["primary_origin_allowed"].eq("N").all()


def test_phase25_qp2_blocked_with_complete_fallback() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase25_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["qp2_r_prediction_row_count"] == 340
    assert final["qp2_r_changed_prediction_row_count"] == 0
    assert final["revision_row_count"] == 0
    assert final["qp2_fallback_rate"] == 1.0
    assert final["qp2_prospective_status"] == "blocked_not_2026Q3_shadow_qualified"

    asof = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_asof_feature_store.parquet")
    assert asof["eligibility_status"].eq("blocked_no_R1_R3_release_timestamp").all()

    qp2 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_qp2_responsive_results.parquet")
    assert len(qp2) == 340
    assert qp2["prediction_changed_from_qp1"].eq("N").all()
    assert qp2["fallback_reason"].astype(str).ne("").all()

    revision = read_csv("partial_stats_phase25_gva_revision_utility.csv").iloc[0]
    assert revision["revision_status"] == "not_scored_no_changed_prediction"
    assert revision["harmful_revision_rate"] == "not_scored"


def test_phase25_spatial_and_prospective_archives() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase25_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["electricity_spatial_source_status"].startswith("materialized")
    assert final["spatial_holdout_result"] == "spatial_challenger_failed_or_blocked"
    assert final["selected_spatial_policy"] == "SW0_last_annual_gva_share"
    assert final["archive_2026q3_status"] == "frozen_qp0_qp1_rows_qp2_diagnostic_fallback"

    electricity = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_electricity_spatial_features.parquet")
    assert len(electricity) > 0
    assert electricity["source_status"].eq("materialized").all()

    spatial = read_csv("partial_stats_phase25_gva_spatial_policy_selection.csv").iloc[0]
    assert spatial["selected_spatial_policy"] == "SW0_last_annual_gva_share"

    for name, status in [
        ("partial_stats_phase25_gva_2026q3_qp0_archive.parquet", "frozen_forecast_rows"),
        ("partial_stats_phase25_gva_2026q3_qp1_archive.parquet", "frozen_forecast_rows"),
        ("partial_stats_phase25_gva_2026q3_qp2_shadow_archive.parquet", "diagnostic_fallback_archive_not_prospective_shadow"),
    ]:
        archive = pd.read_parquet(PROCESSED_DIR / name)
        assert archive["target_period"].eq("2026Q3").all()
        assert archive["official_actual_used"].eq("N").all()
        assert archive["forecast_status"].eq(status).all()

    event = json.loads((PROCESSED_DIR / "partial_stats_phase25_gva_2026q2_holdout_event_status.json").read_text(encoding="utf-8"))
    assert event["event_status"] == "waiting_first_release"
    assert event["official_actual_used"] is False


def test_phase25_report_and_topic_index() -> None:
    report = (ROOT / "reports" / "partial_statistics_estimation_phase25_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 29))
    assert "Series Grain Audit" in report
    assert "Release Evidence Registry" in report
    assert "2026Q3 Forecast Archive" in report
    assert "아직 주장" in report

    topic_index = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase25_gva.md" in topic_index
