from __future__ import annotations

import json

import pandas as pd

from kosis_common import PROCESSED_DIR, ROOT
from run_partial_statistics_phase6 import BOOTSTRAP_ITERATIONS, CSV_OUTPUTS, MODELS, PLACEBO_ITERATIONS, TARGETS


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    frames = {name: frame(name) for name in CSV_OUTPUTS}
    origins = frames["partial_stats_phase6_prediction_origins.csv"]
    require({"nowcast", "one_year_ahead", "delayed_anchor"}.issubset(set(origins["forecast_horizon"])), "prediction origins missing horizons")
    require((origins["target_values_hidden_at_origin"] == "Y").all(), "target values not marked hidden")

    leakage = frames["partial_stats_phase6_vintage_leakage_audit.csv"]
    require((pd.to_numeric(leakage["leakage_rows"], errors="coerce").fillna(0) == 0).all(), "future leakage audit failed")
    require((leakage["status"] == "pass").all(), "leakage audit has non-pass rows")

    rolling = frames["partial_stats_phase6_rolling_origin_results.csv"]
    require("B3B_bidirectional_temporal_share" not in set(rolling["model_id"]), "B3B used as prospective candidate")
    require((rolling["future_anchor_used"] == "N").all(), "future anchor flag failed")
    require((rolling["target_actual_used_for_selection"] == "N").all(), "target actual selection firewall failed")
    require(set(MODELS).issubset(set(rolling["model_id"])), "one or more prospective model candidates missing")

    horizon = frames["partial_stats_phase6_horizon_results.csv"]
    require({"nowcast", "one_year_ahead", "delayed_anchor"}.issubset(set(horizon["forecast_horizon"])), "horizon result missing")
    require(not frames["partial_stats_phase6_forecast_results.csv"].empty, "forecast results empty")

    selection = frames["partial_stats_phase6_inner_selection.csv"]
    require(set(selection["target_name"]) == set(TARGETS), "selection target missing")
    require((selection["outer_actual_used_for_selection"] == "N").all(), "outer actual leaked into selection")
    require((selection["selected_pipeline"] != "B3B_bidirectional_temporal_share").all(), "B3B selected")

    region = frames["partial_stats_phase6_region_cold_start_registry.csv"]
    if not region.empty:
        require((region["cold_start_region_history_used"] == "N").all(), "region cold-start history used")
    industry = frames["partial_stats_phase6_industry_cold_start_registry.csv"]
    if not industry.empty:
        require((industry["cold_start_industry_history_used"] == "N").all(), "industry cold-start history used")
    joint = frames["partial_stats_phase6_joint_cold_start_results.csv"]
    require("PS5_combination_cold_start" in set(joint["support_class"]) or not joint.empty, "joint cold-start not represented")

    bootstrap = frames["partial_stats_phase6_selection_aware_bootstrap.csv"]
    require(len(bootstrap) == BOOTSTRAP_ITERATIONS * len(TARGETS), f"bootstrap rows changed: {len(bootstrap)}")
    placebo = frames["partial_stats_phase6_placebo.csv"]
    require(len(placebo) == PLACEBO_ITERATIONS * 6 * len(TARGETS), f"placebo rows changed: {len(placebo)}")

    archive = frames["partial_stats_phase6_forecast_archive.csv"]
    eval_archive = frames["partial_stats_phase6_forecast_evaluation_archive.csv"]
    require(not archive.empty, "forecast archive empty")
    require(set(archive["forecast_id"]).issubset(set(eval_archive["forecast_id"])), "evaluation archive missing forecast ids")
    require((eval_archive["evaluation_status"] == "pending_official_release").all(), "forecast archive overwritten with official values")

    final_status = json.loads((PROCESSED_DIR / "partial_stats_phase6_final_status.json").read_text(encoding="utf-8"))
    require(final_status["status"] in {"success", "partial_success", "baseline_only_success", "rejected", "blocked_external_holdout"}, "invalid final status")
    require(final_status["b3b_prospective_eligible"] is False, "B3B prospective flag changed")
    require(final_status["production_use"] is False, "production flag must remain false")
    require(final_status["confirmatory_use"] is False, "confirmatory flag must remain false")
    require(final_status["official_statistics_claim"] is False, "official-statistics flag must remain false")
    manifest = json.loads((PROCESSED_DIR / "partial_stats_phase6_experiment_manifest.json").read_text(encoding="utf-8"))
    require(manifest["actual_role"] == "development_prospective_simulation", "actual role changed")
    require(manifest["same_actual_retuning_allowed"] is False, "same actual retuning allowed")
    holdout = json.loads((PROCESSED_DIR / "partial_stats_phase6_holdout_manifest.json").read_text(encoding="utf-8"))
    require(holdout["current_confirmatory_holdout"] is None, "unsealed holdout promoted")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase6.md").read_text(encoding="utf-8")
    for section in range(1, 36):
        require(f"## {section}." in report, f"report section {section} missing")
    require("Complex prospective ML rejected" in report, "final decision language missing")

    execution = frames["partial_stats_phase6_execution_manifest.csv"]
    require((execution["status"] == "completed").all(), "execution manifest incomplete")
    print(
        json.dumps(
            {
                "cp949_csv_count": len(frames),
                "origins": len(origins),
                "rolling_rows": len(rolling),
                "selected_rows": len(selection),
                "bootstrap_rows": len(bootstrap),
                "placebo_rows": len(placebo),
                "final_status": final_status["status"],
                "report": "reports/partial_statistics_estimation_phase6.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

