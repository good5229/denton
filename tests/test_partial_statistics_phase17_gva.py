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


def test_phase17_canonical_feature_store_and_hash_integrity() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase17_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["canonical_asof_store"] == "partial_stats_phase17_gva_asof_feature_store.parquet"
    assert (PROCESSED_DIR / final["canonical_asof_store"]).exists()
    assert final["fallback_equivalence"] == "pass"
    assert final["origin_materialization_pass"] is True
    assert final["hash_integrity"] == "pass"
    assert final["feature_lineage_completion_rate"] == 1.0

    eq = read_csv("partial_stats_phase17_gva_fallback_equivalence.csv").iloc[0]
    assert eq["canonical_content_hash"] == eq["fallback_content_hash"]
    assert eq["fallback_equivalence_status"] == "pass"

    lineage = read_csv("partial_stats_phase17_gva_feature_lineage.csv")
    assert lineage["lineage_complete"].eq("Y").all()


def test_phase17_tracks_and_indicator_certification_are_separated() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase17_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["strict_source_count"] >= 1
    assert final["sensitivity_source_count"] >= 1
    assert final["sensitivity_mixed_into_strict"] is False

    cert = read_csv("partial_stats_phase17_gva_indicator_certification.csv")
    assert set(cert["block"]) == {"output", "labor", "energy", "demand", "business"}
    assert cert[cert["block"].eq("energy")]["release_gate"].iloc[0] == "pass"
    assert cert[cert["block"].isin(["output", "demand"])]["release_gate"].eq("sensitivity_only").all()

    mapping = read_csv("partial_stats_phase17_gva_energy_contract_mapping.csv")
    industrial = mapping[mapping["contract_class"].eq("산업용")].iloc[0]
    assert industrial["primary_energy_signal"] == "Y"
    assert industrial["allowed_industries"] == "B00,C00,D00"


def test_phase17_model_results_and_monthly_gate() -> None:
    for name in [
        "partial_stats_phase17_gva_b0_results.csv",
        "partial_stats_phase17_gva_strict_energy_results.csv",
        "partial_stats_phase17_gva_energy_share_results.csv",
        "partial_stats_phase17_gva_output_sensitivity_results.csv",
        "partial_stats_phase17_gva_demand_sensitivity_results.csv",
        "partial_stats_phase17_gva_selective_router_results.csv",
    ]:
        result = read_csv(name)
        assert len(result) == 16
        assert pd.to_numeric(result["wmape"], errors="coerce").notna().all()

    monthly = read_csv("partial_stats_phase17_gva_monthly_activation_gate.csv")
    assert monthly[monthly["gate"].eq("monthly_primary")]["status"].iloc[0] == "blocked"
    assert monthly[monthly["gate"].eq("monthly_sector_experimental")]["status"].iloc[0] == "generated"


def test_phase17_report_and_current_estimate_labels() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase17_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["monthly_primary_status"] == "monthly_primary_blocked"
    assert final["official_statistics_claim"] is False
    assert final["production_use"] is False

    annual_2026 = read_csv("partial_stats_phase17_gva_annual_nowcast_2026.csv")
    assert annual_2026["actual_used"].eq("N").all()
    assert annual_2026["phase17_policy"].eq(final["selected_policy"]).all()

    report = (ROOT / "reports" / "partial_statistics_estimation_phase17_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 44))
    assert "Feature Store Integrity" in report
    assert "Monthly Experimental Track" in report
