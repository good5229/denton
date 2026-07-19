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


def test_phase28_value_status_and_quality_reclassification() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase28_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["phase27_reproduction_status"] == "pass"
    assert final["target_unchanged"] is True
    assert final["quality_grade_O_count"] == final["observed_official_anchor_count"]

    value = read_csv("partial_stats_phase28_gva_value_status_audit.csv")
    observed = value[value["value_status"].eq("observed_official_actual")].iloc[0]
    assert observed["quality_grade"] == "O"
    assert observed["actual_available"] == "Y"
    assert observed["actual_used_in_generation"] == "Y"
    assert set(value["value_status"]).issuperset({"observed_official_actual", "development_allocation", "experimental_allocation"})


def test_phase28_na1_completeness_and_missing_registry() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase28_gva_final_status.json").read_text(encoding="utf-8"))
    na1 = read_csv("partial_stats_phase28_gva_na1_completeness_audit.csv").iloc[0]
    assert int(na1["theoretical_cell_count"]) == 14272
    assert int(na1["observed_cell_count"]) == final["NA1_observed_cell_count"]
    assert int(na1["missing_cell_count"]) == final["missing_source_cell_count"]
    assert int(na1["observed_cell_count"]) + int(na1["missing_cell_count"]) == int(na1["theoretical_cell_count"])

    missing = read_csv("partial_stats_phase28_gva_missing_cell_registry.csv")
    assert len(missing) == int(na1["missing_cell_count"])
    assert missing["missing_reason"].eq("missing_source").all()


def test_phase28_annual_forecast_and_no_leakage() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase28_gva_final_status.json").read_text(encoding="utf-8"))
    backtest = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase28_gva_annual_anchor_backtest.parquet")
    assert backtest["value_status"].eq("backtest_prediction").all()
    assert backtest["actual_used_in_generation"].eq("N").all()
    assert len(backtest) == final["annual_backtest_prediction_count"]

    forecast = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase28_gva_annual_anchor_forecast.parquet")
    assert forecast["value_status"].eq("prospective_forecast").all()
    assert forecast["actual_used_in_generation"].eq("N").all()
    assert len(forecast) == final["prospective_annual_forecast_count"]
    assert final["selected_annual_policy"] == "AN0_lag_level"
    assert final["quality_grade_A_count"] == final["prospective_annual_forecast_count"]


def test_phase28_population_pr1_and_interval_guards() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase28_gva_final_status.json").read_text(encoding="utf-8"))
    pop = read_csv("partial_stats_phase28_gva_population_identity_audit.csv").iloc[0]
    assert pop["identity_status"] == "population_drift_explained_do_not_directly_compare"

    pr1 = read_csv("partial_stats_phase28_gva_contaminated_hypothesis_registry.csv").iloc[0]
    assert pr1["reuse_for_2026q4"] == "forbidden"

    interval = read_csv("partial_stats_phase28_gva_interval_calibration.csv")
    assert interval["coverage"].eq("not_calibrated").all()
    assert final["50_percent_annual_interval_coverage"] == "not_calibrated"

    structural = read_csv("partial_stats_phase28_gva_structural_feature_coverage.csv")
    assert structural["release_qualified"].eq("N").all()


def test_phase28_prospective_manifest_and_report() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase28_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["holdout_2026q2_status"] == "waiting_first_release"
    assert "new_asof_only" in final["archive_2026q3_integrity"]
    assert final["manifest_2026q4_status"] == "frozen_manifest_created_not_backdated"
    assert final["production_use"] is False
    assert final["official_statistics_claim"] is False

    q4 = json.loads((PROCESSED_DIR / "partial_stats_phase28_gva_2026q4_frozen_manifest.json").read_text(encoding="utf-8"))
    required = ["annual_anchor_policy", "parent_policy", "spatial_policy", "industry_policy", "quarterly_profile_policy", "monthly_profile_policy", "reconciliation_policy", "interval_policy", "fallback_policy", "feature_release_rules", "parameter_hashes", "population_hashes"]
    for key in required:
        assert q4[key]
    assert q4["official_actual_used"] is False
    assert q4["archive_status"] == "frozen_manifest_not_backdated"

    report = (ROOT / "reports" / "partial_statistics_estimation_phase28_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 35))
    assert "Population Identity Audit" in report
    assert "Forward Release Ledger" in report

    topic = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase28_gva.md" in topic
