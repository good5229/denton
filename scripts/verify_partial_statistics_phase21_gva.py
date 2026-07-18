from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase21_gva_official_source_registry.csv",
    "partial_stats_phase21_gva_official_release_ledger.csv",
    "partial_stats_phase21_gva_official_vintage_registry.csv",
    "partial_stats_phase21_gva_warmup_audit.csv",
    "partial_stats_phase21_gva_zero_error_audit.csv",
    "partial_stats_phase21_gva_leakage_audit.csv",
    "partial_stats_phase21_gva_origin_identity_audit.csv",
    "partial_stats_phase21_gva_selection_consistency_audit.csv",
    "partial_stats_phase21_gva_qp0_results.csv",
    "partial_stats_phase21_gva_qp1_results.csv",
    "partial_stats_phase21_gva_qp2_results.csv",
    "partial_stats_phase21_gva_qp3_results.csv",
    "partial_stats_phase21_gva_qp4_results.csv",
    "partial_stats_phase21_gva_qp5_results.csv",
    "partial_stats_phase21_gva_parent_policy_selection.csv",
    "partial_stats_phase21_gva_child_activity_share.csv",
    "partial_stats_phase21_gva_child_validation.csv",
    "partial_stats_phase21_gva_temporal_policy_results.csv",
    "partial_stats_phase21_gva_spatial_constraints.csv",
    "partial_stats_phase21_gva_temporal_constraints.csv",
    "partial_stats_phase21_gva_reconciliation_results.csv",
    "partial_stats_phase21_gva_reconciliation_adjustments.csv",
    "partial_stats_phase21_gva_distortion_audit.csv",
    "partial_stats_phase21_gva_official_parent_accuracy.csv",
    "partial_stats_phase21_gva_growth_accuracy.csv",
    "partial_stats_phase21_gva_turning_point_accuracy.csv",
    "partial_stats_phase21_gva_revision_results.csv",
    "partial_stats_phase21_gva_worst_group_results.csv",
    "partial_stats_phase21_gva_quarterly_replay_2025.csv",
    "partial_stats_phase21_gva_quarterly_nowcast_2026.csv",
    "partial_stats_phase21_gva_annual_from_quarters_2026.csv",
    "partial_stats_phase21_gva_forecast_archive.csv",
    "partial_stats_phase21_gva_execution_manifest.csv",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def main() -> int:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase21_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "GVA target changed")
    require(final["official_quarterly_source_materialized"] is False, "official source should not be claimed materialized")
    require(final["first_release_target_count"] == 0 and final["latest_revision_target_count"] == 0, "official targets should be absent")
    require(final["official_proxy_tracks_separated"] is True, "official/proxy tracks not separated")
    require(final["warmup_rows"] > 0, "warmup rows should be audited")
    require(final["zero_error_rows"] > 0, "zero-error rows should be audited")
    require(final["metric_best_policy"] == "QP1_national_bridge", "metric-best policy mismatch")
    require(final["gate_selected_policy"] == "QP0_seasonal", "gate-selected policy mismatch")
    require(final["prospective_archive_status"] == "frozen_waiting_release", "forecast archive not frozen")
    require(final["monthly_primary_status"] == "monthly_primary_blocked", "monthly primary should remain blocked")
    require(final["official_statistics_claim"] is False and final["production_use"] is False, "official or production claim not allowed")

    for name in REQUIRED_CSVS:
        df = frame(name)
        require(len(df) > 0, f"empty artifact: {name}")
    for name in [
        "partial_stats_phase21_gva_official_target_cube.parquet",
        "partial_stats_phase21_gva_child_unreconciled.parquet",
        "partial_stats_phase21_gva_child_reconciled.parquet",
    ]:
        require((PROCESSED_DIR / name).exists(), f"missing artifact: {name}")
    require((PROCESSED_DIR / "partial_stats_phase21_gva_forecast_archive_manifest.json").exists(), "missing archive manifest")
    require((PROCESSED_DIR / "partial_stats_phase21_gva_experiment_manifest.json").exists(), "missing experiment manifest")

    source = frame("partial_stats_phase21_gva_official_source_registry.csv")
    official = source[source["source_id"].eq("KOSIS_EXPERIMENTAL_QUARTERLY_GRDP")].iloc[0]
    require(official["direct_source_gate"] == "fail", "official source gate must fail without raw body")
    proxy = source[source["source_id"].eq("PROJECT_SIDO_QUARTERLY_GVA_BENCHMARK")].iloc[0]
    require(proxy["direct_source_gate"] == "fail_proxy_not_official", "proxy source mislabeled")

    official_cube = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase21_gva_official_target_cube.parquet")
    require(len(official_cube) == 0, "official target cube should be empty until materialized")

    warmup = frame("partial_stats_phase21_gva_warmup_audit.csv")
    require(warmup["evaluation_role"].eq("warmup_seed").all(), "warmup role mismatch")
    require(warmup["scored"].eq("N").all(), "warmup rows should not be scored")
    zero = frame("partial_stats_phase21_gva_zero_error_audit.csv")
    require(zero["zero_error_reason"].isin(["warmup_target_copy", "rounding_or_constraint_identity"]).all(), "zero-error reason missing")

    leakage = frame("partial_stats_phase21_gva_leakage_audit.csv")
    require(leakage[leakage["check_id"].eq("same_period_actual_used")]["status"].iloc[0] == "pass", "same-period actual leakage check failed")
    origin = frame("partial_stats_phase21_gva_origin_identity_audit.csv")
    require(origin["origin_status"].eq("independent_origin").sum() == 1, "independent origin count mismatch")
    require(origin["origin_status"].eq("collapsed_origin").sum() == 6, "collapsed origin count mismatch")

    selection = frame("partial_stats_phase21_gva_parent_policy_selection.csv")
    require(selection[selection["metric_best"].eq("Y")]["parent_policy_id"].iloc[0] == "QP1_national_bridge", "metric-best row mismatch")
    require(selection[selection["gate_selected_policy"].eq("Y")]["parent_policy_id"].iloc[0] == "QP0_seasonal", "gate-selected row mismatch")
    require(selection[selection["parent_policy_id"].eq("QP1_national_bridge")]["gate_failure_reason"].str.contains("official direct source not materialized", regex=False).all(), "QP1 failure reason missing")

    growth = frame("partial_stats_phase21_gva_growth_accuracy.csv")
    require(growth["growth_unit"].eq("percentage_point").all(), "growth unit must be percentage points")
    require(num(growth["yoy_growth_mae_pp"]).notna().all(), "YoY growth metric missing")

    unreconciled = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase21_gva_child_unreconciled.parquet")
    reconciled = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase21_gva_child_reconciled.parquet")
    require(len(unreconciled) == len(reconciled) and len(unreconciled) > 0, "child forecast parquet mismatch")

    archive = frame("partial_stats_phase21_gva_forecast_archive.csv")
    require(archive["archive_status"].eq("frozen_waiting_release").all(), "archive not frozen")
    require(archive["one_shot_consumed"].eq("false").all(), "one-shot should not be consumed")
    nowcast = frame("partial_stats_phase21_gva_quarterly_nowcast_2026.csv")
    require(nowcast["actual_used"].eq("N").all(), "2026 actual should not be used")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase21_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 46)), "report sections must be 1..45")
    for phrase in ["Warm-up Audit", "Official·Proxy Track 분리", "Prospective Forecast Archive", final["metric_best_policy"]]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(
        json.dumps(
            {
                "status": final["status"],
                "official_quarterly_source_materialized": final["official_quarterly_source_materialized"],
                "metric_best_policy": final["metric_best_policy"],
                "gate_selected_policy": final["gate_selected_policy"],
                "report": "reports/partial_statistics_estimation_phase21_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
