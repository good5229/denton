from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, ROOT


DERIVED_DIR = ROOT / "data" / "derived"


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DERIVED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase31_claims_and_static_snapshot_guardrails() -> None:
    final = json.loads((DERIVED_DIR / "phase31_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "RECI-LF"
    assert final["phase30_reproduction_status"] == "pass"
    assert final["production_use"] is False
    assert final["official_statistics_claim"] is False
    assert final["paid_private_source_used"] is False
    assert final["static_snapshot_quarter_observation_violation_count"] == 0
    assert final["u_value_violation_count"] == 0

    lineage = read_csv("phase31_source_lineage.csv")
    snapshots = lineage[lineage["source_id"].isin(["emd_2015_economic_census_proxy", "seoul_2024_business_map_proxy"])]
    assert snapshots["raw_observation_grain"].str.contains("snapshot").all()
    assert not snapshots["raw_observation_grain"].str.contains("quarter", case=False).any()
    assert lineage["source_family_id"].ne("").all()


def test_phase31_eligibility_and_adaptive_resolution() -> None:
    cell = read_csv("phase31_cell_eligibility.csv")
    assert len(cell) > 0
    assert cell["eligibility_state"].isin(
        ["observed_presence", "probable_presence", "structural_zero", "suppressed_unknown", "mapping_unknown", "stale_only"]
    ).all()
    assert cell["value_policy"].ne("").all()

    adaptive = read_csv("phase31_adaptive_resolution.csv")
    assert adaptive["row_count"].astype(int).sum() == len(cell)
    assert {"effective_region_level", "effective_industry_level"}.issubset(adaptive.columns)


def test_phase31_normalized_validation_and_industry_audit() -> None:
    normalized = read_csv("phase31_2015_2024_normalized_validation.csv")
    assert len(normalized) > 0
    assert {"weighted_share_mae", "spearman_rank_corr", "presence_agreement"}.issubset(normalized.columns)

    spatial = read_csv("phase31_spatial_transfer_scorecard.csv")
    assert "S1_2015_prior_normalized_share" in set(spatial["component_id"])
    assert spatial["validated_grain"].str.contains("EMD").any()

    industry = read_csv("phase31_industry_lineage_scorecard.csv")
    i1 = industry[industry["component_id"].eq("I1_manufacturing_lagged_proxy_share")].iloc[0]
    assert i1["phase31_grade"] == "D"
    assert "not_independent" in i1["lineage_independence"]


def test_phase31_shadow_confidence_and_event_gates() -> None:
    shadow = read_csv("phase31_reci_lf_shadow.csv")
    assert len(shadow) > 0
    assert shadow["production_use"].eq("false").all()
    assert shadow["official_statistics_claim"].eq("false").all()
    assert not shadow["claim_grade"].isin(["O", "A"]).any()
    assert shadow[shadow["claim_grade"].eq("C")]["source_family_count"].astype(int).ge(2).all()
    assert shadow["direction"].eq("").all()
    assert shadow["anomaly_score"].eq("").all()
    assert shadow["rank_universe"].str.contains("same_period").all()

    confidence = read_csv("phase31_confidence_calibration.csv")
    assert "confidence_error_monotonicity" in confidence.columns

    event = read_csv("phase31_event_scorecard.csv")
    assert not event["validation_status"].str.contains("passed").any()


def test_phase31_reports_exist_and_topic_indexed() -> None:
    reports = [
        "partial_statistics_estimation_phase31_reci_evidence.md",
        "phase31_source_lineage_audit.md",
        "phase31_cell_eligibility.md",
        "phase31_emd_spatial_validation.md",
        "phase31_industry_evidence.md",
        "phase31_tq3_rq1_bridge.md",
        "phase31_public_proxy_and_event_validation.md",
        "phase31_confidence_calibration.md",
    ]
    for report in reports:
        assert (ROOT / "reports" / report).exists()

    topic = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase31_reci_evidence.md" in topic
