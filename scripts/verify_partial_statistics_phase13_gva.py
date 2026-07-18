from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase13_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA", "target must remain GVA")
    require(final["status"] == "strict_vintage_blocked_sensitivity_completed", "unexpected final status")
    require(final["independent_origin_count"] >= 6, "at least three independent origins per year are required")
    require(final["collapsed_origin_count"] == 0, "origin-level collapse should be zero after feature differentiation")
    require(final["feature_hash_unique_count"] == final["origin_count"], "each origin should have a distinct feature hash")
    require(final["prediction_hash_unique_count"] > final["origin_count"], "model predictions should not collapse to a single hash")
    require(final["monthly_primary_status"] == "blocked_no_eligible_monthly_source", "monthly primary estimate should be blocked")
    require(final["actual_used_for_selection"] is False, "outer actual must not be used for selection")
    require(final["production_use"] is False and final["official_statistics_claim"] is False, "no official/production claim allowed")

    growth = frame("partial_stats_phase13_gva_origin_information_growth.csv")
    require(set(growth["target_year"].astype(int)) == {2022, 2023}, "growth audit target years mismatch")
    for year, group in growth.groupby(growth["target_year"].astype(int)):
        require(group["feature_content_hash"].nunique() >= 3, f"{year} should have at least 3 feature hashes")
        require(pd.to_numeric(group["eligible_observation_count"], errors="coerce").is_monotonic_increasing, f"{year} observations should not decrease")
        require(group["latest_available_observation_period"].nunique() >= 3, f"{year} latest observation period should advance")

    identity = frame("partial_stats_phase13_gva_origin_identity_audit.csv")
    require({"B0_parent_share", "M1_direct_growth", "M2_employee_productivity", "M3_establishment_productivity", "M4_proxy_residual", "M5_fixed_ensemble"}.issubset(set(identity["model_id"])), "missing model identity rows")
    changing_models = identity[identity["model_id"].isin(["M1_direct_growth", "M4_proxy_residual", "M5_fixed_ensemble"])]
    for keys, group in changing_models.groupby(["target_year", "model_id"]):
        require(group["prediction_hash"].nunique() >= 3, f"{keys} prediction hash should vary by origin")

    accuracy = frame("partial_stats_phase13_gva_origin_accuracy.csv")
    require(set(accuracy["evaluation_status"]) == {"outer_evaluation_sensitivity"}, "unexpected evaluation status")
    require(set(accuracy["target_year"].astype(int)) == {2022, 2023}, "accuracy target years mismatch")

    monthly = frame("partial_stats_phase13_gva_monthly_source_registry.csv")
    require((monthly["primary_monthly_eligible"] == "N").all(), "monthly primary source should not be eligible")
    placeholder = frame("partial_stats_phase13_gva_monthly_placeholder_registry.csv")
    require(placeholder.iloc[0]["allowed"] == "Y_display_only", "monthly placeholder should be display-only")

    calibration = frame("partial_stats_phase13_gva_interval_calibration.csv")
    require(set(calibration["calibration_status"]) == {"posthoc_diagnostic_not_deployable"}, "intervals must remain posthoc diagnostics")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase13_gva.md").read_text(encoding="utf-8")
    for phrase in [
        "Phase 12 restored GVA as the primary target",
        "monthly output remains placeholder-only",
        "strict official vintage performance",
        "production/official statistics use",
    ]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(
        json.dumps(
            {
                "status": final["status"],
                "independent_origin_count": final["independent_origin_count"],
                "independent_model_origin_count": final["independent_model_origin_count"],
                "feature_hash_unique_count": final["feature_hash_unique_count"],
                "prediction_hash_unique_count": final["prediction_hash_unique_count"],
                "monthly_primary_status": final["monthly_primary_status"],
                "report": "reports/partial_statistics_estimation_phase13_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
