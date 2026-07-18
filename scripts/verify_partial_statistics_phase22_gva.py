from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


REQUIRED_CSVS = [
    "partial_stats_phase22_gva_official_source_manifest.csv",
    "partial_stats_phase22_gva_official_release_ledger.csv",
    "partial_stats_phase22_gva_official_vintage_registry.csv",
    "partial_stats_phase22_gva_target_measure_registry.csv",
    "partial_stats_phase22_gva_official_industry_crosswalk.csv",
    "partial_stats_phase22_gva_growth_metric_audit.csv",
    "partial_stats_phase22_gva_extreme_growth_error_audit.csv",
    "partial_stats_phase22_gva_warmup_audit.csv",
    "partial_stats_phase22_gva_leakage_audit.csv",
    "partial_stats_phase22_gva_origin_registry.csv",
    "partial_stats_phase22_gva_origin_collapse_registry.csv",
    "partial_stats_phase22_gva_parent_policy_selection.csv",
    "partial_stats_phase22_gva_structural_weight_registry.csv",
    "partial_stats_phase22_gva_child_validation.csv",
    "partial_stats_phase22_gva_temporal_identity_audit.csv",
    "partial_stats_phase22_gva_reconciliation_distortion.csv",
    "partial_stats_phase22_gva_execution_manifest.csv",
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
    final = json.loads((PROCESSED_DIR / "partial_stats_phase22_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "GVA target changed")
    require(final["official_quarterly_source_materialized"] is True, "official source should be materialized")
    require(final["official_source_period_count"] >= 5, "official source period count too small")
    require(final["official_quarterly_target_materialized"] is True, "official growth target cube should be materialized")
    require(final["official_first_release_target_count"] > 0, "official target rows missing")
    require(final["official_statistics_claim"] is False and final["production_use"] is False, "official/production claim not allowed")
    require(final["sigungu_quarterly_allocation_rows"] > 0, "sigungu quarterly allocation missing")
    require(final["sigungu_annual_recovery_max_abs_pct"] < 1e-9, "sigungu annual recovery constraint failed")
    require(final["warmup_scored_rows"] == 0 and final["target_copy_scored_rows"] == 0, "warmup/target-copy leakage")

    for name in REQUIRED_CSVS:
        require(len(frame(name)) > 0, f"empty artifact: {name}")
    require((PROCESSED_DIR / "partial_stats_phase22_gva_official_target_cube.parquet").exists(), "missing official target cube")
    require((PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet").exists(), "missing sigungu allocation cube")
    require((PROCESSED_DIR / "partial_stats_phase22_gva_experiment_manifest.json").exists(), "missing experiment manifest")

    source = frame("partial_stats_phase22_gva_official_source_manifest.csv")
    require(source["source_body_exists"].eq("pass").all(), "some official source files missing")
    require(source["attachment_hash"].str.len().eq(64).all(), "source hash missing")
    require(source["direct_source_gate"].eq("pass_source_only").all(), "source gate should pass source-only")
    require(source["target_extraction_gate"].eq("pass").all(), "target extraction gate mismatch")
    require(num(source["extracted_target_rows"]).gt(0).all(), "some releases have no extracted targets")

    official_cube = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_official_target_cube.parquet")
    require(len(official_cube) == final["official_first_release_target_count"], "official target row count mismatch")
    require(official_cube["measure_type"].eq("yoy_growth").all(), "only direct growth targets should be extracted")
    require(official_cube["price_basis"].eq("real").all(), "official growth target should be real")
    require(official_cube["target_type"].str.contains("official_direct", regex=False).all(), "target type mismatch")
    key = ["reference_period", "region_code", "official_industry_group", "measure_type", "target_type", "vintage_id"]
    require(not official_cube.duplicated(key).any(), "official target key has duplicates")
    require(set(["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1"]).issubset(set(official_cube["reference_period"])), "missing target periods")

    growth = frame("partial_stats_phase22_gva_growth_metric_audit.csv")
    require(growth["growth_unit"].eq("percentage_point").all(), "growth unit must be pp")
    require(num(growth["unit_double_scaling_errors"]).eq(0).all(), "unit double scaling error")

    allocation = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    require(len(allocation) == final["sigungu_quarterly_allocation_rows"], "allocation row count mismatch")
    require(allocation["actual_claim"].eq("N").all(), "child quarterly estimates should not be actuals")
    annual = allocation.groupby(["source_region", "sigungu_code", "sector_code", "year"], as_index=False).agg(
        quarter_sum=("estimated_quarterly_gva", "sum"),
        annual=("annual_benchmark_gva", "first"),
    )
    require(((annual["quarter_sum"] - annual["annual"]).abs() < 1e-6).all(), "annual recovery failed")
    require(allocation["allocation_basis"].isin(["quarterly_industrial_production_index", "project_sido_quarterly_gva_proxy", "equal_quarter_fallback"]).all(), "unknown allocation basis")

    structural = frame("partial_stats_phase22_gva_structural_weight_registry.csv")
    for required in ["sigungu_annual_grdp", "farmland_area_by_sigungu", "factory_count_by_sigungu"]:
        require(required in set(structural["source_name"]), f"missing structural source: {required}")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase22_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 47)), "report sections must be 1..46")
    for phrase in ["공식 분기 GRDP 원문", "시군구 연간 GRDP 분기배분", "아직 주장할 수 없는 내용"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
