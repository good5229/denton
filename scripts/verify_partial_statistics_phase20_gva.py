from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase20_gva_quarterly_grdp_source_registry.csv",
    "partial_stats_phase20_gva_quarterly_grdp_release_ledger.csv",
    "partial_stats_phase20_gva_quarterly_indicator_registry.csv",
    "partial_stats_phase20_gva_indicator_frequency_mapping.csv",
    "partial_stats_phase20_gva_indicator_industry_mapping.csv",
    "partial_stats_phase20_gva_qp0_seasonal_results.csv",
    "partial_stats_phase20_gva_qp1_national_bridge_results.csv",
    "partial_stats_phase20_gva_qp2_indicator_bridge_results.csv",
    "partial_stats_phase20_gva_qp3_hierarchical_results.csv",
    "partial_stats_phase20_gva_qp4_factor_results.csv",
    "partial_stats_phase20_gva_qp5_midas_results.csv",
    "partial_stats_phase20_gva_qp7_ensemble_results.csv",
    "partial_stats_phase20_gva_quarterly_child_baseline.csv",
    "partial_stats_phase20_gva_quarterly_activity_share.csv",
    "partial_stats_phase20_gva_quarterly_sparse_share.csv",
    "partial_stats_phase20_gva_quarterly_child_allocation_results.csv",
    "partial_stats_phase20_gva_equal_quarter_results.csv",
    "partial_stats_phase20_gva_seasonal_share_results.csv",
    "partial_stats_phase20_gva_indicator_proportional_results.csv",
    "partial_stats_phase20_gva_denton_results.csv",
    "partial_stats_phase20_gva_chow_lin_results.csv",
    "partial_stats_phase20_gva_fernandez_litterman_results.csv",
    "partial_stats_phase20_gva_spatial_constraints.csv",
    "partial_stats_phase20_gva_temporal_constraints.csv",
    "partial_stats_phase20_gva_reconciliation_results.csv",
    "partial_stats_phase20_gva_reconciliation_adjustments.csv",
    "partial_stats_phase20_gva_consistency_audit.csv",
    "partial_stats_phase20_gva_quarterly_parent_accuracy.csv",
    "partial_stats_phase20_gva_quarterly_growth_accuracy.csv",
    "partial_stats_phase20_gva_quarterly_revision_results.csv",
    "partial_stats_phase20_gva_quarterly_turning_points.csv",
    "partial_stats_phase20_gva_quarterly_child_validation.csv",
    "partial_stats_phase20_gva_worst_group_results.csv",
    "partial_stats_phase20_gva_quarterly_replay_2025.csv",
    "partial_stats_phase20_gva_quarterly_benchmark_2025.csv",
    "partial_stats_phase20_gva_quarterly_nowcast_2026.csv",
    "partial_stats_phase20_gva_annual_from_quarters_2026.csv",
    "partial_stats_phase20_gva_quarterly_current_status.csv",
    "partial_stats_phase20_gva_target_measure_registry.csv",
    "partial_stats_phase20_gva_execution_manifest.csv",
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
    final = json.loads((PROCESSED_DIR / "partial_stats_phase20_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "GVA target changed")
    require(final["annual_primary_status"] == "active", "annual primary not active")
    require(final["quarterly_parent_primary_status"] in {"quarterly_parent_primary_activated", "quarterly_parent_baseline_retained"}, "bad quarterly parent status")
    require(final["quarterly_child_status"] in {"quarterly_child_development_activated", "quarterly_child_primary_activated"}, "bad quarterly child status")
    require(final["monthly_primary_status"] == "monthly_primary_blocked", "monthly primary should remain independently blocked")
    require(final["official_quarterly_grdp_direct_source"] is False, "direct official province quarterly GRDP should not be claimed")
    require(final["official_statistics_claim"] is False and final["production_use"] is False, "official or production claim not allowed")
    require(final["parent_exactness_status"] == "pass", "parent exactness failed")

    for name in REQUIRED_CSVS:
        df = frame(name)
        require(len(df) > 0, f"empty artifact: {name}")
    for name in [
        "partial_stats_phase20_gva_quarterly_grdp_vintages.parquet",
        "partial_stats_phase20_gva_quarterly_grdp_target_cube.parquet",
        "partial_stats_phase20_gva_quarterly_indicator_cube.parquet",
    ]:
        require((PROCESSED_DIR / name).exists(), f"missing artifact: {name}")
    require((PROCESSED_DIR / "partial_stats_phase20_gva_experiment_manifest.json").exists(), "missing experiment manifest json")

    source = frame("partial_stats_phase20_gva_quarterly_grdp_source_registry.csv")
    require("PROJECT_SIDO_QUARTERLY_GVA_BENCHMARK" in set(source["source_id"]), "missing project benchmark source")
    require(source[source["source_id"].eq("PROJECT_SIDO_QUARTERLY_GVA_BENCHMARK")]["official_direct_actual"].iloc[0] == "N", "project benchmark mislabeled as official actual")

    target = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase20_gva_quarterly_grdp_target_cube.parquet")
    require({"period", "region_code", "industry_group", "real_grdp_level", "vintage_id"}.issubset(target.columns), "target cube schema mismatch")
    require(num(target["real_grdp_level"]).notna().all(), "target cube value missing")

    parent = frame("partial_stats_phase20_gva_quarterly_parent_accuracy.csv")
    require(set(parent["parent_policy_id"]) == {"QP0_seasonal", "QP1_national_bridge", "QP2_indicator_bridge", "QP3_hierarchical", "QP4_factor", "QP5_midas", "QP7_ensemble"}, "missing quarterly parent policies")
    require(num(parent["quarterly_wmape"]).between(0, 10).all(), "quarterly WMAPE out of range")

    child = frame("partial_stats_phase20_gva_quarterly_child_validation.csv")
    require(child["parent_exactness_status"].eq("pass").all(), "child parent exactness failed")
    require(num(child["parent_exactness_max_gap"]).fillna(0).max() < 1e-5, "child-parent gap too large")

    temporal = frame("partial_stats_phase20_gva_temporal_constraints.csv")
    require(temporal[temporal["constraint_id"].eq("quarter_sum_to_annual")]["status"].iloc[0] == "pass", "quarter sum constraint failed")
    consistency = frame("partial_stats_phase20_gva_consistency_audit.csv")
    require(consistency[consistency["check_id"].eq("quarter_sum_equals_annual")]["status"].iloc[0] == "pass", "annual consistency failed")
    require(consistency[consistency["check_id"].eq("child_sum_to_parent")]["status"].iloc[0] == "pass", "spatial consistency failed")

    nowcast = frame("partial_stats_phase20_gva_quarterly_nowcast_2026.csv")
    require(nowcast["actual_used"].eq("N").all(), "2026 actual should not be used")
    require(nowcast["official_parent_status"].eq("not_materialized").all(), "2026 official parent status mislabeled")
    monthly = frame("partial_stats_phase20_gva_quarterly_current_status.csv")
    require(monthly["monthly_primary"].eq("blocked").all(), "monthly gate should be independent")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase20_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 50)), "report sections must be 1..49")
    for phrase in ["연간·분기·월별 Gate 분리", "공식 분기 GRDP Source", "Parent Direct Accuracy", final["quarterly_child_status"]]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(
        json.dumps(
            {
                "status": final["status"],
                "quarterly_parent_primary_status": final["quarterly_parent_primary_status"],
                "quarterly_child_status": final["quarterly_child_status"],
                "monthly_primary_status": final["monthly_primary_status"],
                "report": "reports/partial_statistics_estimation_phase20_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
