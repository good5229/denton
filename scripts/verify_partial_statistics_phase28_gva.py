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
    final = json.loads((PROCESSED_DIR / "partial_stats_phase28_gva_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "GVA" and final["target_unchanged"] is True, "target changed")
    require(final["phase27_reproduction_status"] == "pass", "Phase27 reproduction failed")
    require(final["price_basis_separation_status"] == "real_growth_and_nominal_level_tracks_separated", "price basis mixed")
    require(final["holdout_2026q2_status"] == "waiting_first_release", "2026Q2 consumed unexpectedly")
    require("new_asof_only" in final["archive_2026q3_integrity"], "2026Q3 archive integrity failed")
    require(final["manifest_2026q4_status"] == "frozen_manifest_created_not_backdated", "2026Q4 manifest missing")
    require(final["production_use"] is False and final["official_statistics_claim"] is False, "forbidden claim")

    pop = csv("partial_stats_phase28_gva_population_identity_audit.csv").iloc[0]
    require(pop["identity_status"] == "population_drift_explained_do_not_directly_compare", "population drift not flagged")
    sw0 = csv("partial_stats_phase28_gva_sw0_score_reconciliation.csv")
    require(sw0["explanation_status"].eq("fully_explained_by_population_and_metric_scope_change").all(), "SW0 score drift not explained")

    value = csv("partial_stats_phase28_gva_value_status_audit.csv")
    require(value["value_status"].isin(["observed_official_actual", "development_allocation", "experimental_allocation"]).all(), "invalid value status")
    observed = value[value["value_status"].eq("observed_official_actual")].iloc[0]
    require(observed["quality_grade"] == "O", "observed annual anchors must be Grade O")
    require(observed["actual_used_in_generation"] == "Y", "observed anchors should mark actual use")

    na1 = csv("partial_stats_phase28_gva_na1_completeness_audit.csv").iloc[0]
    require(int(na1["theoretical_cell_count"]) == 14272, "NA1 theoretical cell count mismatch")
    require(int(na1["observed_cell_count"]) + int(na1["missing_cell_count"]) == int(na1["theoretical_cell_count"]), "NA1 missing classification incomplete")
    missing = csv("partial_stats_phase28_gva_missing_cell_registry.csv")
    require(len(missing) == int(na1["missing_cell_count"]), "missing registry count mismatch")
    require(missing["missing_reason"].ne("").all(), "missing reason blank")

    target = parquet("partial_stats_phase28_gva_annual_target_cube.parquet")
    require(target["forecast_population_status"].eq("eligible_observed_lag_target").all(), "annual target population status invalid")
    backtest = parquet("partial_stats_phase28_gva_annual_anchor_backtest.parquet")
    require(backtest["value_status"].eq("backtest_prediction").all(), "annual backtest status invalid")
    require(backtest["actual_used_in_generation"].eq("N").all(), "backtest leaked actual")
    forecast = parquet("partial_stats_phase28_gva_annual_anchor_forecast.parquet")
    require(forecast["value_status"].eq("prospective_forecast").all(), "future annual forecast status invalid")
    require(forecast["actual_used_in_generation"].eq("N").all(), "future forecast leaked actual")
    require(len(forecast) == final["prospective_annual_forecast_count"], "forecast row count mismatch")

    emp = parquet("partial_stats_phase28_gva_employee_feature_cube.parquet")
    biz = parquet("partial_stats_phase28_gva_business_feature_cube.parquet")
    require(len(emp) > 0 and len(biz) > 0, "structural feature cubes missing")
    structural = csv("partial_stats_phase28_gva_structural_feature_coverage.csv")
    require(structural["release_qualified"].eq("N").all(), "unqualified structural features promoted")

    contaminated = csv("partial_stats_phase28_gva_contaminated_hypothesis_registry.csv").iloc[0]
    require(contaminated["reuse_for_2026q4"] == "forbidden", "contaminated PR1 reused")
    interval = csv("partial_stats_phase28_gva_interval_calibration.csv")
    require(interval["coverage"].eq("not_calibrated").all(), "placeholder interval not removed")
    fine = parquet("partial_stats_phase28_gva_fine_forecast_output.parquet")
    require(fine["value_status"].eq("prospective_forecast").all(), "fine annual forecast status invalid")

    q4 = json.loads((PROCESSED_DIR / "partial_stats_phase28_gva_2026q4_frozen_manifest.json").read_text(encoding="utf-8"))
    for key in ["annual_anchor_policy", "parent_policy", "spatial_policy", "industry_policy", "quarterly_profile_policy", "monthly_profile_policy", "reconciliation_policy", "interval_policy", "fallback_policy", "feature_release_rules", "parameter_hashes", "population_hashes"]:
        require(key in q4 and str(q4[key]) != "", f"Q4 manifest missing {key}")
    require(q4["official_actual_used"] is False, "Q4 manifest used actual")
    require(q4["archive_status"] == "frozen_manifest_not_backdated", "Q4 manifest backdated")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase28_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    require(sections == list(range(1, 35)), "report sections must be 1..34")
    for phrase in ["Population Identity Audit", "Value Status Audit", "Annual Anchor Baseline", "Forward Release Ledger", "아직 주장"]:
        require(phrase in report, f"report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
