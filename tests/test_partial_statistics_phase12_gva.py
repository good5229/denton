from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase12_goal_and_final_status_preserve_gva_target() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase12_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["status"] == "annual_quarterly_multi_origin"
    assert final["target"] == "GVA"
    assert final["target_years"] == [2022, 2023, 2024, 2025]
    assert final["prediction_origin_count"] >= 18
    assert final["target_origin_combinations"] == 72
    assert final["production_use"] is False
    assert final["official_statistics_claim"] is False

    goal = json.loads((PROCESSED_DIR / "partial_stats_phase12_gva_goal_charter.json").read_text(encoding="utf-8"))
    assert goal["PRIMARY_TARGET"] == "Gross Value Added"
    assert set(goal["PRIMARY_OUTPUT_FREQUENCIES"]) == {"annual", "quarterly", "monthly"}
    assert goal["ACTUAL_RELEASE_REQUIRED_FOR_EXECUTION"] is False


def test_phase12_origin_grid_and_actual_policy_are_explicit() -> None:
    targets = read_csv("partial_stats_phase12_gva_target_year_registry.csv")
    assert set(targets["target_year"].astype(int)) == {2022, 2023, 2024, 2025}
    assert targets[targets["target_year"].eq("2025")].iloc[0]["actual_role"] == "unused_or_unavailable"
    assert targets[targets["target_year"].eq("2024")].iloc[0]["confirmatory_role"] == "false_development_outer"

    grid = read_csv("partial_stats_phase12_gva_target_origin_grid.csv")
    assert len(grid) == 72
    assert set(["O0", "O1", "O2", "O3", "O4", "O5"]).issubset(set(grid["origin_id"]))
    assert {f"O_M{month:02d}" for month in range(1, 13)}.issubset(set(grid["origin_id"]))
    assert set(grid["target_actual_as_feature"]) == {"prohibited"}


def test_phase12_leakage_and_auxiliary_targets_are_blocked() -> None:
    leakage = read_csv("partial_stats_phase12_gva_leakage_audit.csv")
    assert pd.to_numeric(leakage["target_actual_feature_rows"], errors="coerce").fillna(0).eq(0).all()
    assert pd.to_numeric(leakage["future_feature_rows"], errors="coerce").fillna(0).eq(0).all()
    assert leakage["leakage_status"].isin({"pass", "pass_no_target_actual", "sensitivity_only_current_snapshot_blocked_from_strict"}).all()

    sources = read_csv("partial_stats_phase12_gva_source_inventory.csv")
    auxiliary = sources[sources["source_id"].eq("expanded_manufacturing_sigungu_ksic.csv")].iloc[0]
    assert auxiliary["primary_target"] == "N_auxiliary"


def test_phase12_2025_estimates_do_not_use_actuals_and_are_time_consistent() -> None:
    annual = read_csv("partial_stats_phase12_gva_annual_estimates_2025.csv")
    quarterly = read_csv("partial_stats_phase12_gva_quarterly_estimates_2025.csv")
    monthly = read_csv("partial_stats_phase12_gva_monthly_estimates_2025.csv")
    assert len(annual) > 0 and len(quarterly) > 0 and len(monthly) > 0
    assert set(annual["actual_used"]) == {"N"}
    assert set(quarterly["actual_used"]) == {"N"}
    assert set(monthly["actual_used"]) == {"N"}
    assert set(annual["annual_source_status"]) == {"reconciled_from_quarterly_estimates"}

    consistency = read_csv("partial_stats_phase12_gva_temporal_consistency_audit.csv")
    month_row = consistency[consistency["constraint"].eq("month_sum_equals_quarter")].iloc[0]
    annual_row = consistency[consistency["constraint"].eq("quarter_sum_equals_annual")].iloc[0]
    assert month_row["status"] == "pass"
    assert float(month_row["max_abs_diff"]) < 1e-6
    assert float(annual_row["max_abs_diff"]) < 1e-6


def test_phase12_report_has_required_sections_and_no_overclaim() -> None:
    report = (ROOT / "reports" / "partial_statistics_estimation_phase12_gva.md").read_text(encoding="utf-8")
    section_numbers = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert section_numbers == list(range(1, 37))
    assert "2025 detailed GVA actual is unavailable and unused" in report
    assert "Monthly GVA is a temporal allocation from quarterly estimates" in report
    assert "official-statistics use remain false" in report
