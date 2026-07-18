from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


VALID_FINAL_STATUSES = {
    "multi_origin_gva_estimates_generated",
    "annual_multi_origin_only",
    "annual_quarterly_multi_origin",
    "support_limited_multi_origin",
    "baseline_dominant_multi_origin",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def json_artifact(name: str) -> dict:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def max_numeric(frame_: pd.DataFrame, column: str) -> float:
    return float(pd.to_numeric(frame_[column], errors="coerce").max())


def main() -> int:
    final = json_artifact("partial_stats_phase12_gva_final_status.json")
    require(final["status"] in VALID_FINAL_STATUSES, "unexpected final status")
    require(final["target"] == "GVA", "primary target must remain GVA")
    require(final["target_years"] == [2022, 2023, 2024, 2025], "target years mismatch")
    require(final["prediction_origin_count"] >= 18, "monthly and quarterly origins are missing")
    require(final["target_origin_combinations"] == 72, "target-origin grid should have 4 x 18 rows")
    require(final["production_use"] is False, "production use must remain false")
    require(final["official_statistics_claim"] is False, "official-statistics claim must remain false")

    goal = json_artifact("partial_stats_phase12_gva_goal_charter.json")
    require(goal["PRIMARY_TARGET"] == "Gross Value Added", "goal charter target mismatch")
    require(goal["ACTUAL_RELEASE_REQUIRED_FOR_EXECUTION"] is False, "2025 actual must not be required")
    require(goal["PRODUCTION_USE"] is False, "goal charter production use must be false")
    require(goal["OFFICIAL_STATISTICS_CLAIM"] is False, "goal charter official claim must be false")
    require(set(goal["PRIMARY_OUTPUT_FREQUENCIES"]) == {"annual", "quarterly", "monthly"}, "frequency goal mismatch")

    targets = frame("partial_stats_phase12_gva_target_year_registry.csv")
    require(set(targets["target_year"].astype(int)) == {2022, 2023, 2024, 2025}, "target year registry mismatch")
    require(targets[targets["target_year"].eq("2025")].iloc[0]["actual_role"] == "unused_or_unavailable", "2025 actual role mismatch")
    require(targets[targets["target_year"].eq("2024")].iloc[0]["confirmatory_role"] == "false_development_outer", "2024 confirmatory role mismatch")

    origins = frame("partial_stats_phase12_gva_origin_registry.csv")
    for origin_id in ["O0", "O1", "O2", "O3", "O4", "O5"]:
        require(origin_id in set(origins["origin_id"]), f"{origin_id} missing")
    for month in range(1, 13):
        require(f"O_M{month:02d}" in set(origins["origin_id"]), f"monthly origin {month:02d} missing")

    grid = frame("partial_stats_phase12_gva_target_origin_grid.csv")
    require(len(grid) == 72, "target-origin grid row count mismatch")
    require((grid["target_actual_as_feature"] == "prohibited").all(), "actual target must be prohibited as feature")

    sources = frame("partial_stats_phase12_gva_source_inventory.csv")
    auxiliary = sources[sources["source_id"].eq("expanded_manufacturing_sigungu_ksic.csv")].iloc[0]
    require(auxiliary["primary_target"] == "N_auxiliary", "establishment/employee source must remain auxiliary")

    leakage = frame("partial_stats_phase12_gva_leakage_audit.csv")
    require((pd.to_numeric(leakage["target_actual_feature_rows"], errors="coerce").fillna(0) == 0).all(), "actual target leakage detected")
    require((pd.to_numeric(leakage["future_feature_rows"], errors="coerce").fillna(0) == 0).all(), "future feature leakage detected")
    historical = leakage[leakage["target_year"].astype(int).isin([2022, 2023, 2024])]
    require(
        historical["leakage_status"].isin({"pass", "sensitivity_only_current_snapshot_blocked_from_strict"}).all(),
        "historical leakage status should be pass or sensitivity blocked",
    )

    asof = frame("partial_stats_phase12_gva_asof_dataset_registry.csv")
    require(len(asof) == 72, "as-of registry row count mismatch")
    require(asof["content_hash"].astype(str).str.len().gt(0).all(), "empty as-of content hash")
    require(
        (PROCESSED_DIR / "partial_stats_phase12_gva_asof_feature_matrix.parquet").exists()
        or (PROCESSED_DIR / "partial_stats_phase12_gva_asof_feature_matrix_fallback.csv").exists(),
        "as-of feature matrix parquet or fallback is missing",
    )

    annual_2025 = frame("partial_stats_phase12_gva_annual_estimates_2025.csv")
    quarterly_2025 = frame("partial_stats_phase12_gva_quarterly_estimates_2025.csv")
    monthly_2025 = frame("partial_stats_phase12_gva_monthly_estimates_2025.csv")
    require(len(annual_2025) > 0 and len(quarterly_2025) > 0 and len(monthly_2025) > 0, "2025 outputs are empty")
    require((annual_2025["actual_used"] == "N").all(), "2025 annual actual must not be used")
    require((quarterly_2025["actual_used"] == "N").all(), "2025 quarterly actual must not be used")
    require((monthly_2025["actual_used"] == "N").all(), "2025 monthly actual must not be used")
    require(annual_2025["annual_source_status"].eq("reconciled_from_quarterly_estimates").all(), "annual 2025 should be reconciled from quarter estimates")

    consistency = frame("partial_stats_phase12_gva_temporal_consistency_audit.csv")
    month_row = consistency[consistency["constraint"].eq("month_sum_equals_quarter")].iloc[0]
    require(month_row["status"] == "pass" and float(month_row["max_abs_diff"]) < 1e-6, "monthly-to-quarterly consistency failed")
    annual_row = consistency[consistency["constraint"].eq("quarter_sum_equals_annual")].iloc[0]
    require(float(annual_row["max_abs_diff"]) < 1e-6, "quarterly-to-annual consistency failed")

    annual_2026 = frame("partial_stats_phase12_gva_annual_nowcast_2026.csv")
    quarterly_2026 = frame("partial_stats_phase12_gva_quarterly_nowcast_2026.csv")
    monthly_2026 = frame("partial_stats_phase12_gva_monthly_nowcast_2026.csv")
    require(len(annual_2026) > 0 and len(quarterly_2026) > 0 and len(monthly_2026) > 0, "2026 nowcast outputs are empty")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase12_gva.md").read_text(encoding="utf-8")
    section_numbers = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(section_numbers == list(range(1, 37)), "report must contain exact sections 1 through 36")
    for prohibited_claim in ["2025 actual 기반 성능", "production-ready official", "공식통계로 사용"]:
        require(prohibited_claim not in report, f"prohibited claim appears in report: {prohibited_claim}")

    print(
        json.dumps(
            {
                "final_status": final["status"],
                "target_origin_combinations": len(grid),
                "annual_2025_rows": len(annual_2025),
                "quarterly_2025_rows": len(quarterly_2025),
                "monthly_2025_rows": len(monthly_2025),
                "max_month_quarter_diff": max_numeric(consistency[consistency["constraint"].eq("month_sum_equals_quarter")], "max_abs_diff"),
                "max_quarter_annual_diff": max_numeric(consistency[consistency["constraint"].eq("quarter_sum_equals_annual")], "max_abs_diff"),
                "report": "reports/partial_statistics_estimation_phase12_gva.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
