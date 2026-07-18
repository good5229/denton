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


def test_phase15_keeps_gva_target_and_leakage_guards() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase15_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["target_unchanged"] is True
    assert final["actual_used_for_indicator_construction"] is False
    assert final["actual_used_for_weight_selection"] is False
    assert final["raw_proxy_direct_to_gva"] is False
    assert final["national_indicator_broadcast_to_municipality"] is False
    assert final["official_statistics_claim"] is False
    assert final["production_use"] is False

    riaf = read_csv("partial_stats_phase15_gva_riaf.csv")
    assert riaf["actual_used_for_weight_selection"].eq("N").all()


def test_phase15_generates_required_indicator_blocks_and_quality_gate() -> None:
    for block in ["output", "labor", "energy", "demand", "business", "narrative"]:
        factor = read_csv(f"partial_stats_phase15_gva_{block}_factor.csv")
        assert len(factor) > 0
        assert factor["actual_used_for_factor_construction"].eq("N").all()
        parquet = PROCESSED_DIR / f"partial_stats_phase15_gva_{block}_variables.parquet"
        fallback = PROCESSED_DIR / f"partial_stats_phase15_gva_{block}_variables_fallback.csv"
        assert parquet.exists() or fallback.exists()

    quality = read_csv("partial_stats_phase15_gva_indicator_quality.csv")
    blocked = quality[quality["quality_grade"].isin(["Q4", "Q5"])]
    assert blocked["primary_eligible"].eq("N").all()


def test_phase15_policy_outputs_and_ablation_are_complete() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase15_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["status"] in {
        "literature_indicator_policy_selected",
        "sector_limited_indicator_selected",
        "diagnostic_indicators_only",
        "baseline_retained_after_indicator_test",
    }
    for name in [
        "partial_stats_phase15_gva_b0_results.csv",
        "partial_stats_phase15_gva_riaf_bridge_results.csv",
        "partial_stats_phase15_gva_factor_residual_results.csv",
        "partial_stats_phase15_gva_exposure_allocation_results.csv",
        "partial_stats_phase15_gva_ensemble_results.csv",
    ]:
        result = read_csv(name)
        assert len(result) == 8
        assert pd.to_numeric(result["wmape"], errors="coerce").notna().all()

    midas = read_csv("partial_stats_phase15_gva_riaf_midas_results.csv")
    assert midas["evaluation_status"].eq("blocked_insufficient_historical_monthly_indicators").all()
    ablation = read_csv("partial_stats_phase15_gva_indicator_ablation.csv")
    assert set(ablation["model_id"].unique()) == {"A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7"}


def test_phase15_temporal_current_estimates_and_report() -> None:
    temporal = read_csv("partial_stats_phase15_gva_temporal_consistency.csv")
    quarter = temporal[temporal["check_id"].eq("2025_quarter_sum_equals_annual")].iloc[0]
    assert quarter["status"] == "pass"
    assert float(quarter["max_absolute_gap"]) < 1e-4
    assert temporal[temporal["check_id"].eq("monthly_primary")]["status"].iloc[0] == "blocked_insufficient_historical_monthly_indicators"

    annual_2025 = read_csv("partial_stats_phase15_gva_annual_estimates_2025.csv")
    quarterly_2025 = read_csv("partial_stats_phase15_gva_quarterly_estimates_2025.csv")
    annual_2026 = read_csv("partial_stats_phase15_gva_annual_nowcast_2026.csv")
    quarterly_2026 = read_csv("partial_stats_phase15_gva_quarterly_nowcast_2026.csv")
    assert len(annual_2025) > 0 and len(quarterly_2025) > 0
    assert len(annual_2026) > 0 and len(quarterly_2026) > 0
    assert annual_2025["actual_used"].eq("N").all()
    assert annual_2026["actual_used"].eq("N").all()

    report = (ROOT / "reports" / "partial_statistics_estimation_phase15_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 36))
    assert "Indicator Quality" in report
    assert "monthly_primary_blocked" in report
