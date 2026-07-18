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


def test_phase16_final_status_and_target_guards() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase16_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["target_unchanged"] is True
    assert final["fully_evaluable_target_years"] >= 3
    assert final["actual_used_for_indicator_construction"] is False
    assert final["actual_used_for_weight_or_lag_selection"] is False
    assert final["current_snapshot_backdated_to_strict"] is False
    assert final["official_statistics_claim"] is False
    assert final["production_use"] is False
    assert final["monthly_primary_status"] == "monthly_primary_blocked"
    assert (PROCESSED_DIR / final["asof_feature_store_artifact"]).exists()


def test_phase16_release_ledger_and_leakage_audit() -> None:
    ledger = read_csv("partial_stats_phase16_gva_release_ledger.csv")
    assert "A_exact" in set(ledger["release_confidence"])
    assert ledger[ledger["release_confidence"].eq("D_current_snapshot")]["track"].eq("sensitivity").all()

    leakage = read_csv("partial_stats_phase16_gva_leakage_audit.csv")
    pass_checks = {"feature_release_before_origin", "target_actual_hidden", "target_derived_feature_absent", "future_month_excluded"}
    assert leakage[leakage["check_id"].isin(pass_checks)]["status"].eq("pass").all()


def test_phase16_targets_and_indicators_are_qualified() -> None:
    targets = read_csv("partial_stats_phase16_gva_target_registry.csv")
    assert targets["fully_evaluable"].eq("Y").sum() >= 3
    assert set(targets["target_year"].astype(int)) == {2020, 2021, 2022, 2023}

    coverage = read_csv("partial_stats_phase16_gva_indicator_coverage.csv")
    assert set(coverage["block"]) == {"output", "labor", "energy", "demand", "business"}
    assert pd.to_numeric(coverage[coverage["block"].eq("output")]["coverage"], errors="coerce").iloc[0] > 0

    qualification = read_csv("partial_stats_phase16_gva_indicator_qualification.csv")
    assert set(qualification["block"]) == {"output", "labor", "energy", "demand", "business"}
    assert qualification["primary_eligible"].isin(["Y", "N"]).all()


def test_phase16_model_temporal_and_report_outputs() -> None:
    for name in [
        "partial_stats_phase16_gva_b0_results.csv",
        "partial_stats_phase16_gva_output_bridge_results.csv",
        "partial_stats_phase16_gva_labor_bridge_results.csv",
        "partial_stats_phase16_gva_energy_bridge_results.csv",
        "partial_stats_phase16_gva_multiblock_results.csv",
        "partial_stats_phase16_gva_residual_results.csv",
        "partial_stats_phase16_gva_exposure_allocation_results.csv",
        "partial_stats_phase16_gva_ensemble_results.csv",
    ]:
        result = read_csv(name)
        assert len(result) == 16
        assert pd.to_numeric(result["wmape"], errors="coerce").notna().all()

    temporal = read_csv("partial_stats_phase16_gva_temporal_consistency.csv")
    assert temporal["status"].eq("pass").any()
    monthly = read_csv("partial_stats_phase16_gva_monthly_activation_gate.csv")
    assert monthly[monthly["gate"].eq("monthly_primary")]["status"].iloc[0] == "blocked"

    report = (ROOT / "reports" / "partial_statistics_estimation_phase16_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 44))
    assert "Electricity Source" in report
    assert "Monthly Activation Gate" in report
