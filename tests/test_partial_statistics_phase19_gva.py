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


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def test_phase19_final_status_and_target_coverage() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase19_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["target_unchanged"] is True
    assert final["registered_target_years"] == [2020, 2021, 2022, 2023]
    assert final["evaluated_target_years"] == [2020, 2021, 2022, 2023]
    assert final["target_2023_status"] == "evaluated"
    assert final["model_identity_audit"] == "pass"
    assert final["monthly_primary_status"] == "monthly_primary_blocked"
    assert final["official_statistics_claim"] is False
    assert final["production_use"] is False

    coverage = read_csv("partial_stats_phase19_gva_target_coverage_audit.csv")
    assert coverage["coverage_identity_status"].eq("pass").all()
    assert coverage[coverage["registered_target_year"].eq("2023")]["model_executed"].iloc[0] == "Y"


def test_phase19_exact_error_decomposition() -> None:
    signed = read_csv("partial_stats_phase19_gva_signed_error_decomposition.csv")
    assert num(signed["signed_reconstruction_gap"]).max() < 1e-5
    assert {"parent_signed_component", "share_signed_component", "interaction_signed_component"}.issubset(signed.columns)

    absolute = read_csv("partial_stats_phase19_gva_absolute_shapley_decomposition.csv")
    assert num(absolute["abs_shapley_gap"]).max() < 1e-5
    squared = read_csv("partial_stats_phase19_gva_squared_shapley_decomposition.csv")
    assert num(squared["sq_shapley_gap"]).max() < 1e-2

    registry = read_csv("partial_stats_phase19_gva_error_type_registry.csv")
    assert set(registry["count_level"]) == {"row_level", "cell_year_level", "unique_cell_level"}
    cell_year = registry[registry["count_level"].eq("cell_year_level")].iloc[0]
    counted = sum(int(cell_year[col]) for col in ["parent_dominant", "share_dominant", "compensating_error", "mixed_error", "low_error"])
    assert counted == int(cell_year["total_units"])


def test_phase19_parent_and_sparse_share_policies() -> None:
    parent_results = read_csv("partial_stats_phase19_gva_parent_baseline_results.csv")
    assert set(parent_results["parent_policy_id"]) == {
        "PB0_parent_baseline",
        "PB1_last_parent",
        "PB2_national_industry_growth",
        "PB3_damped_national_growth",
        "PB4_hierarchical_parent_growth",
        "PB5_parent_bridge",
    }
    assert num(parent_results["parent_wmape"]).between(0, 10).all()
    assert (PROCESSED_DIR / "partial_stats_phase19_gva_parent_target_cube.parquet").exists()
    assert (PROCESSED_DIR / "partial_stats_phase19_gva_parent_feature_store.parquet").exists()

    material = read_csv("partial_stats_phase19_gva_material_share_change.csv")
    assert material["outer_actual_used_for_threshold"].eq("N").all()
    assert material["material_share_change"].isin(["Y", "N"]).all()

    pr = read_csv("partial_stats_phase19_gva_update_precision_recall.csv")
    assert set(pr["share_policy_id"]) == {
        "PS0_last_share",
        "PS1_sparse_damped_trend",
        "PS2_sparse_hierarchical_change",
        "PS3_sparse_empirical_bayes",
        "PS4_event_gated_change",
        "PS5_auxiliary_share_classifier",
        "PS6_precision_first_router",
    }
    assert num(pr["false_update_rate"]).between(0, 1).all()
    assert num(pr["precision"]).between(0, 1).all()

    budget = read_csv("partial_stats_phase19_gva_sparse_update_budget.csv")
    assert budget["zero_sum_required"].eq("Y").all()
    assert budget["outer_actual_used_for_budget"].eq("N").all()


def test_phase19_current_outputs_report_and_topic_index() -> None:
    current = read_csv("partial_stats_phase19_gva_annual_nowcast_2026.csv")
    assert current["actual_used"].eq("N").all()
    assert current["estimate_status"].isin(["baseline_scenario", "parent_only_current_nowcast"]).all()

    monthly = read_csv("partial_stats_phase19_gva_monthly_experimental_results.csv")
    assert monthly["monthly_primary"].eq("blocked").all()
    assert monthly["official_monthly_gva"].eq("false").all()

    report = (ROOT / "reports" / "partial_statistics_estimation_phase19_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 38))
    assert "Target Coverage Audit" in report
    assert "Shapley Error Decomposition" in report

    topic_index = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase19_gva.md" in topic_index
    assert "Exact error attribution" in topic_index
