from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase29_annual_residual_common_population_and_no_promotion() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase29_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["phase28_reproduction_status"] == "pass"
    assert final["target_unchanged"] is True
    assert final["annual_best_baseline_policy"] == "AN0_lag_level"
    assert final["annual_regime_residual_delta_good"] < 0
    assert final["annual_regime_residual_selection"] == "not_selected"

    annual = read_csv("partial_stats_phase29_gva_annual_regime_residual_metrics.csv")
    counts = annual.set_index("policy_id")["prediction_count"].astype(int)
    assert counts.nunique() == 1
    assert {"AN0_lag_level", "AN1_lag_growth", "AN2_parent_growth", "RR1_group_residual"}.issubset(set(counts.index))


def test_phase29_annual_backtest_is_oof_prediction_status() -> None:
    backtest = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase29_gva_annual_regime_residual_backtest.parquet")
    assert backtest["value_status"].eq("backtest_prediction").all()
    assert backtest["actual_used_in_generation"].eq("N").all()
    assert backtest["RR1_status"].isin(["fallback_no_prior_train", "oof_group_shrunk_residual"]).all()
    assert backtest["annual_population_key"].nunique() > 0


def test_phase29_router_is_conservative_and_not_promoted() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase29_gva_final_status.json").read_text(encoding="utf-8"))
    router = read_csv("partial_stats_phase29_gva_forecastability_router_metrics.csv")
    assert "FR1_oof_selective_router" in set(router["policy_id"])
    assert final["router_selection"] == "not_promoted"
    assert 0 <= final["router_application_rate"] <= 1

    rows = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase29_gva_forecastability_router_rows.parquet")
    assert rows["router_policy"].isin(["AN0_lag_level", "RR1_group_residual"]).all()
    assert rows["router_reason"].ne("").all()


def test_phase29_service_temporal_component_improves_equal_proxy() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase29_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["service_prior_delta_good"] > 0
    assert final["service_temporal_selection"] == "development_component_improved_not_promoted_to_direct_gva"

    temporal = read_csv("partial_stats_phase29_gva_service_temporal_component_metrics.csv")
    tq0 = temporal[temporal["policy_id"].eq("TQ0_equal_quarter")].iloc[0]
    tq3 = temporal[temporal["policy_id"].eq("TQ3_service_prior_profile")].iloc[0]
    assert float(tq3["weighted_share_mae"]) < float(tq0["weighted_share_mae"])


def test_phase29_report_and_topic_index() -> None:
    report = (ROOT / "reports" / "partial_statistics_estimation_phase29_gva.md").read_text(encoding="utf-8")
    assert "Annual Regime-Residual" in report
    assert "Forecastability Router" in report
    assert "서비스업 Temporal Component" in report
    assert "아직 주장할 수 없는 내용" in report

    topic = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase29_gva.md" in topic
