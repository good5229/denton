from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False)


def test_phase35_uses_only_free_non_card_sources() -> None:
    inventory = read_csv("partial_stats_phase35_source_inventory.csv")
    assert inventory["cost"].eq("free").all()
    assert not inventory["source_family"].str.contains("card", case=False).any()


def test_phase35_breaks_common_proxy_only_on_supported_scope() -> None:
    identity = read_csv("partial_stats_phase35_interaction_identity_audit.csv")
    lookup = identity.set_index(["source", "audit_id"])["value"]
    assert float(lookup.loc[("KEPCO KSIC middle electricity", "median_effective_temporal_rank")]) > 1
    assert float(lookup.loc[("KEPCO-joined Phase34 candidate", "all_joined_industries_identical_profile_group_rate")]) == 0
    assert float(lookup.loc[("NTS 100 lifestyle industries", "median_effective_temporal_rank")]) > 1


def test_phase35_conserves_but_negative_control_warns() -> None:
    conservation = read_csv("partial_stats_phase35_kepco_conservation.csv")
    negative = read_csv("partial_stats_phase35_negative_controls.csv")
    assert conservation["status"].eq("pass").all()
    assert pd.to_numeric(conservation["absolute_error"]).max() <= 1e-6
    assert negative["conservation_still_passes"].eq("Y").all()
    assert negative["semantic_alignment_destroyed"].eq("Y").all()


def test_phase35_release_and_claim_guardrails() -> None:
    candidate = read_csv("partial_stats_phase35_kepco_monthly_candidate.csv")
    release = read_csv("partial_stats_phase35_release_audit.csv")
    status = json.loads((PROCESSED_DIR / "partial_stats_phase35_final_status.json").read_text(encoding="utf-8"))
    assert candidate["release_asof_quarter_end"].eq("N").all()
    assert release["available_by_reference_month_end"].eq("N").all()
    assert status["full_sigungu_middle_quarter_product_decision"] == "Blocked"
    assert status["direct_monthly_middle_gva_actual_available"] is False
    assert status["production_use"] is False
    assert status["official_statistics_claim"] is False
    assert (ROOT / "reports" / "partial_statistics_estimation_phase35_gva.md").exists()
