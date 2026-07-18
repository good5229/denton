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


def test_phase18_final_status_and_target_guards() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase18_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["target_unchanged"] is True
    assert final["development_target_years"] == [2020, 2021, 2022, 2023]
    assert final["confirmatory_target_exists"] is False
    assert final["selected_parent_policy"] == "Parent_Baseline"
    assert final["selected_share_policy"]
    assert final["actual_used_for_policy_selection"] is False
    assert final["share_sum_status"] == "pass"
    assert final["monthly_primary_status"] == "monthly_primary_blocked"
    assert final["official_statistics_claim"] is False
    assert final["production_use"] is False


def test_phase18_error_decomposition_and_share_cube() -> None:
    decomp = read_csv("partial_stats_phase18_gva_error_decomposition.csv")
    assert {"c0_abs_error", "c1_share_abs_error", "c2_parent_abs_error", "interaction_component"}.issubset(decomp.columns)
    assert pd.to_numeric(decomp["c3_consistency_gap"], errors="coerce").max() < 1e-4

    registry = read_csv("partial_stats_phase18_gva_error_type_registry.csv").iloc[0]
    assert float(registry["share_dominant_cells"]) >= 0
    assert float(registry["parent_dominant_cells"]) >= 0
    assert float(registry["parent_error_contribution"]) >= 0
    assert float(registry["share_error_contribution"]) >= 0

    share_cube = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase18_gva_share_cube.parquet")
    assert {"year", "source_region", "sector_code", "sigungu_code", "gva_share"}.issubset(share_cube.columns)
    assert pd.to_numeric(share_cube["gva_share"], errors="coerce").ge(-1e-12).all()

    audit = read_csv("partial_stats_phase18_gva_share_audit.csv")
    assert audit["status"].eq("pass").all()
    assert pd.to_numeric(audit["absolute_gap_from_one"], errors="coerce").max() < 1e-8


def test_phase18_share_policies_and_update_diagnostics() -> None:
    policy_files = [
        "partial_stats_phase18_gva_last_share_results.csv",
        "partial_stats_phase18_gva_damped_share_results.csv",
        "partial_stats_phase18_gva_mean_reverting_share_results.csv",
        "partial_stats_phase18_gva_dynamic_logistic_share_results.csv",
        "partial_stats_phase18_gva_empirical_bayes_share_results.csv",
        "partial_stats_phase18_gva_change_gated_share_results.csv",
        "partial_stats_phase18_gva_share_router_results.csv",
    ]
    for name in policy_files:
        result = read_csv(name)
        assert len(result) == 16
        assert pd.to_numeric(result["wmape"], errors="coerce").notna().all()
        assert pd.to_numeric(result["share_mae"], errors="coerce").notna().all()

    accuracy = read_csv("partial_stats_phase18_gva_gva_accuracy.csv")
    assert set(accuracy["policy_id"]) == {
        "P0_last_share",
        "P1_damped_share_trend",
        "P2_mean_reverting_share",
        "P3_dynamic_logistic_share",
        "P4_empirical_bayes_share",
        "P5_change_gated_share",
        "P6_share_router",
    }

    confusion = read_csv("partial_stats_phase18_gva_update_confusion_matrix.csv")
    assert pd.to_numeric(confusion["false_update_rate"], errors="coerce").between(0, 1).all()
    assert pd.to_numeric(confusion["missed_change_rate"], errors="coerce").between(0, 1).all()


def test_phase18_current_outputs_report_and_topic_index() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase18_gva_final_status.json").read_text(encoding="utf-8"))
    annual_2026 = read_csv("partial_stats_phase18_gva_annual_nowcast_2026.csv")
    assert annual_2026["actual_used"].eq("N").all()
    assert annual_2026["current_status"].eq(final["current_nowcast_status"]).all()

    monthly = read_csv("partial_stats_phase18_gva_monthly_experimental_results.csv")
    assert monthly["monthly_primary"].eq("blocked").all()
    assert monthly["monthly_experimental"].eq("sector_limited_profile_only").all()
    assert monthly["official_monthly_gva"].eq("false").all()

    report = (ROOT / "reports" / "partial_statistics_estimation_phase18_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 42))
    assert "B0 Error Decomposition" in report
    assert "Selective Router" in report
    assert final["status"] in report

    topic_index = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase18_gva.md" in topic_index
    assert "Baseline error decomposition" in topic_index
