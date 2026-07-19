from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def parquet(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_parquet(path)


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase29_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "target changed")
    require(final["phase28_reproduction_status"] == "pass", "Phase28 reproduction failed")
    require(final["production_use"] is False and final["official_statistics_claim"] is False, "forbidden claim")
    require(final["annual_best_baseline_policy"] == "AN0_lag_level", "unexpected annual baseline")

    annual = csv("partial_stats_phase29_gva_annual_regime_residual_metrics.csv")
    require(set(annual["policy_id"]).issuperset({"AN0_lag_level", "AN2_parent_growth", "RR1_group_residual"}), "annual policies missing")
    rr = annual[annual["policy_id"].eq("RR1_group_residual")].iloc[0]
    require(rr["status"] == "challenger_development", "RR1 status invalid")
    require(rr["selection_status"] != "promotable_development", "RR1 should not be promoted in current run")

    backtest = parquet("partial_stats_phase29_gva_annual_regime_residual_backtest.parquet")
    require(backtest["actual_used_in_generation"].eq("N").all(), "annual backtest leaked actual")
    require(backtest["value_status"].eq("backtest_prediction").all(), "annual backtest status invalid")
    require(backtest["policy_id"].nunique() >= 4, "annual policy long output incomplete")

    router = csv("partial_stats_phase29_gva_forecastability_router_metrics.csv")
    require("FR1_oof_selective_router" in set(router["policy_id"]), "router metrics missing")
    router_rows = parquet("partial_stats_phase29_gva_forecastability_router_rows.parquet")
    require(router_rows["router_policy"].isin(["AN0_lag_level", "RR1_group_residual"]).all(), "invalid router policy")
    require(float(final["router_application_rate"]) >= 0.0, "router application rate invalid")

    temporal = csv("partial_stats_phase29_gva_service_temporal_component_metrics.csv")
    require(set(temporal["policy_id"]) == {"TQ0_equal_quarter", "TQ3_service_prior_profile"}, "temporal policies missing")
    require(float(final["service_prior_weighted_share_mae"]) < float(final["service_equal_weighted_share_mae"]), "service component did not improve equal quarter")
    temporal_rows = parquet("partial_stats_phase29_gva_service_temporal_component_rows.parquet")
    require(temporal_rows["TQ3_status"].ne("").all(), "service profile status missing")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase29_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 15)), "report sections must be 1..14")
    for phrase in ["Annual Regime-Residual", "Forecastability Router", "서비스업 Temporal Component", "아직 주장할 수 없는 내용"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
