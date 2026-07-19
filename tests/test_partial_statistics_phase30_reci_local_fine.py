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


def test_phase30_claim_grade_and_guardrails() -> None:
    final = json.loads((DERIVED_DIR / "phase30_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "RECI-LF"
    assert final["phase29_reproduction_status"] == "pass"
    assert final["production_use"] is False
    assert final["official_statistics_claim"] is False
    assert final["paid_private_source_used"] is False
    assert final["grade_a_for_emd_fine_count"] == 0

    claim = read_csv("phase30_claim_grade.csv")
    assert set(claim["claim_grade"]) == {"O", "A", "B", "C", "D", "E", "U"}
    assert claim[claim["claim_grade"].eq("A")]["allowed_for_emd_fine_reci"].iloc[0] == "N"


def test_phase30_source_readiness_and_pre2020_audit() -> None:
    ledger = read_csv("phase30_source_release_ledger.csv")
    assert len(ledger) >= 8
    assert ledger["evidence_grade"].isin(["R1", "R2", "R3", "R4", "R5"]).all()

    paid = read_csv("phase30_paid_private_source_exclusion_log.csv")
    assert paid["status"].eq("excluded").all()

    pre2020 = read_csv("phase30_pre2020_gva_audit.csv")
    assert "source_file" in pre2020.columns
    assert pre2020["use_policy"].ne("").all()


def test_phase30_component_scorecards() -> None:
    spatial = read_csv("phase30_spatial_component_scorecard.csv")
    assert "S0_previous_sigungu_share" in set(spatial["component_id"])

    industry = read_csv("phase30_industry_component_scorecard.csv")
    assert len(industry) >= 1

    temporal = read_csv("phase30_temporal_component_scorecard.csv")
    tq3 = temporal[temporal["component_id"].eq("TQ3_service_prior_profile")].iloc[0]
    assert tq3["claim_grade_candidate"] in {"C", "D"}
    assert tq3["selection_status"] == "development_component_improved_not_promoted_to_direct_gva"


def test_phase30_shadow_cube_claims_are_limited() -> None:
    final = json.loads((DERIVED_DIR / "phase30_final_status.json").read_text(encoding="utf-8"))
    shadow = read_csv("phase30_reci_local_fine_shadow.csv")
    assert len(shadow) == final["shadow_row_count"]
    assert shadow["claim_grade"].isin(["B", "C", "D", "E", "U"]).all()
    assert not shadow["claim_grade"].eq("A").any()
    assert shadow["direct_actual_available"].eq("N").all()
    assert shadow["production_use"].eq("false").all()
    assert shadow["official_statistics_claim"].eq("false").all()
    assert shadow["effective_region_level"].ne("").all()
    assert shadow["effective_industry_level"].ne("").all()


def test_phase30_reports_exist_and_topic_indexed() -> None:
    reports = [
        "partial_statistics_estimation_phase30_reci_local_fine.md",
        "phase30_public_data_readiness.md",
        "phase30_spatial_downscaling_validation.md",
        "phase30_industry_downscaling_validation.md",
        "phase30_temporal_component_validation.md",
        "phase30_external_validation.md",
        "phase30_poc_claim_and_confidence.md",
    ]
    for report in reports:
        assert (ROOT / "reports" / report).exists()

    topic = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase30_reci_local_fine.md" in topic
