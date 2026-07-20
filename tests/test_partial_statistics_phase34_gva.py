from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase34_blocks_rank_one_joint_product() -> None:
    identity = read_csv("partial_stats_phase34_gva_proxy_identity_audit.csv")
    rank = identity[identity["audit_id"].eq("fine_temporal_matrix_rank")]
    common = identity[identity["audit_id"].eq("within_parent_identical_industry_temporal_profile_rate")]
    assert pd.to_numeric(rank["value"]).eq(1).all()
    assert rank["status"].eq("fail_joint_interaction").all()
    assert pd.to_numeric(common["value"]).eq(1).all()
    assert common["status"].eq("fail_common_proxy").all()


def test_phase34_separates_asof_structure_from_temporal_vintage() -> None:
    shadow = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase34_gva_joint_shadow.parquet")
    retrospective = shadow[shadow["policy_id"].eq("R0_contemporaneous_structure")]
    lag2 = shadow[shadow["policy_id"].eq("S0_lag2_structure")]
    assert retrospective["structure_asof_eligible"].eq("N").all()
    assert lag2["structure_asof_eligible"].eq("Y").all()
    assert shadow["temporal_vintage_eligible"].eq("N").all()
    assert shadow["interaction_source_id"].eq("").all()


def test_phase34_conservation_is_not_misread_as_accuracy() -> None:
    conservation = read_csv("partial_stats_phase34_gva_conservation.csv")
    negative = read_csv("partial_stats_phase34_gva_negative_controls.csv")
    assert conservation["status"].eq("pass").all()
    assert pd.to_numeric(conservation["absolute_error"]).max() <= 1e-6
    assert negative["conservation_still_passes"].eq("Y").all()


def test_phase34_final_claims_are_closed() -> None:
    status = json.loads((PROCESSED_DIR / "partial_stats_phase34_gva_final_status.json").read_text(encoding="utf-8"))
    assert status["joint_product_decision"] == "Blocked"
    assert status["direct_quarterly_middle_actual_available"] is False
    assert status["interaction_source_available"] is False
    assert status["production_use"] is False
    assert status["official_statistics_claim"] is False
    assert (ROOT / "reports" / "partial_statistics_estimation_phase34_gva.md").exists()
