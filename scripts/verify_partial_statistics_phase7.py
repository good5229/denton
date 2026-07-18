from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT
from run_partial_statistics_phase7 import CSV_OUTPUTS, FULL_REFIT_BOOTSTRAP, POLICY_BOOTSTRAP, TARGETS


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    frames = {name: frame(name) for name in CSV_OUTPUTS}

    reproduction = frames["partial_stats_phase7_phase6_reproduction.csv"]
    require(not reproduction.empty, "Phase 6 reproduction table is empty")
    require((reproduction["status"] == "pass").all(), "Phase 6 reproduction failed")

    implementation = frames["partial_stats_phase7_model_implementation_registry.csv"]
    statuses = set(implementation["implementation_status"])
    require({"fully_implemented", "proxy_only", "alias", "fallback_dominant", "partially_implemented"}.issubset(statuses), "implementation audit statuses incomplete")
    pm2 = implementation[implementation["model_id"].eq("PM2_hierarchical_negative_binomial_proxy")]
    require(not pm2.empty and pm2.iloc[0]["implementation_status"] == "proxy_only", "PM2 proxy status not enforced")

    alias = frames["partial_stats_phase7_alias_registry.csv"]
    require(not alias.empty, "alias registry is empty")
    require((alias["promotion_allowed"] == "N").all(), "alias promotion gate failed")
    fallback = frames["partial_stats_phase7_fallback_audit.csv"]
    require({"requested_model_id", "executed_model_id", "fallback_used", "fallback_reason"}.issubset(fallback.columns), "fallback audit schema missing")

    inventory = frames["partial_stats_phase7_target_year_inventory.csv"]
    require("2020" in set(inventory["available_year"]) or "2024" in set(inventory["available_year"]), "historical target inventory did not detect expanded years")
    require("development_contaminated" in set(inventory["data_role"]), "contaminated development role missing")

    leakage = frames["partial_stats_phase7_vintage_leakage_audit.csv"]
    require((pd.to_numeric(leakage["leakage_rows"], errors="coerce").fillna(0) == 0).all(), "vintage leakage rows detected")
    require((leakage["status"] == "pass").all(), "vintage leakage audit not pass")

    feature_bundles = frames["partial_stats_phase7_feature_bundle_registry.csv"]
    require("F0" in set(feature_bundles["feature_bundle"]), "F0 feature bundle missing")
    require(feature_bundles[feature_bundles["feature_bundle"].eq("F0")].iloc[0]["status"] == "active_primary", "F0 not primary")

    full_refit = frames["partial_stats_phase7_full_refit_bootstrap.csv"]
    require(len(full_refit) == FULL_REFIT_BOOTSTRAP * len(TARGETS) * 2, "full-refit bootstrap row count changed")
    require((full_refit["full_refit_executed"] == "N").all(), "full-refit bootstrap should be blocked until stable cube rebuild")
    policy_bootstrap = frames["partial_stats_phase7_policy_bootstrap.csv"]
    require(len(policy_bootstrap) == POLICY_BOOTSTRAP * len(TARGETS), "policy bootstrap row count changed")

    holdout = json.loads((PROCESSED_DIR / "partial_stats_phase7_holdout_manifest.json").read_text(encoding="utf-8"))
    require(holdout["current_confirmatory_holdout"] is None, "unsealed holdout promoted")
    frozen = json.loads((PROCESSED_DIR / "partial_stats_phase7_frozen_policy_manifest.json").read_text(encoding="utf-8"))
    require(frozen["frozen_policy_status"] == "baseline_policy_frozen", "frozen manifest status changed")
    require(frozen["holdout_evaluation_allowed_before_new_sealed_vintage"] is False, "holdout firewall failed")

    final_status = json.loads((PROCESSED_DIR / "partial_stats_phase7_final_status.json").read_text(encoding="utf-8"))
    require(final_status["status"] == "baseline_policy_frozen", "final status must freeze baseline")
    require(final_status["complex_ml_promoted"] is False, "complex ML was promoted")
    require(final_status["confirmatory_use"] is False, "confirmatory flag must remain false")
    require(final_status["official_statistics_claim"] is False, "official-statistics flag must remain false")

    archive = frames["partial_stats_phase7_forecast_archive.csv"]
    eval_archive = frames["partial_stats_phase7_forecast_evaluation_archive.csv"]
    require(not archive.empty, "forecast archive empty")
    require(set(archive["forecast_id"]).issubset(set(eval_archive["forecast_id"])), "forecast evaluation archive missing ids")
    require((eval_archive["evaluation_status"] == "pending_official_release").all(), "forecast archive evaluated before official release")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase7.md").read_text(encoding="utf-8")
    for section in range(1, 38):
        require(f"## {section}." in report, f"report section {section} missing")
    require("baseline_policy_frozen" in report, "baseline freeze conclusion missing")

    execution = frames["partial_stats_phase7_execution_manifest.csv"]
    require((execution["status"] == "completed").all(), "execution manifest incomplete")

    print(
        json.dumps(
            {
                "cp949_csv_count": len(frames),
                "phase6_reproduction_rows": len(reproduction),
                "implementation_models": implementation["model_id"].nunique(),
                "alias_rows": len(alias),
                "full_refit_bootstrap_rows": len(full_refit),
                "policy_bootstrap_rows": len(policy_bootstrap),
                "final_status": final_status["status"],
                "report": "reports/partial_statistics_estimation_phase7.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
