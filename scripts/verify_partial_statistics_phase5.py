from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from run_partial_statistics_phase5 import CSV_OUTPUTS, MASK_REPETITIONS, MASK_SCENARIOS, REPORT
from kosis_common import PROCESSED_DIR


EXTRA_OUTPUTS = ["partial_stats_model_selection.csv"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing output: {name}")
    path.read_text(encoding="cp949")
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    frames = {name: frame(name) for name in CSV_OUTPUTS + EXTRA_OUTPUTS}
    manifest_path = PROCESSED_DIR / "partial_stats_experiment_manifest.json"
    require(manifest_path.exists(), "missing partial_stats_experiment_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    ksic = frames["ksic8_9_official_crosswalk_phase5.csv"]
    require(len(ksic) == 1277, f"unexpected KSIC 8->9 rows: {len(ksic)}")
    require(ksic["ksic8_code"].str.fullmatch(r"\d{5}").all(), "KSIC8 code width invalid")
    require(ksic["ksic9_code"].str.fullmatch(r"\d{5}").all(), "KSIC9 code width invalid")
    require("one_to_many" in set(ksic["mapping_type"]), "KSIC one-to-many evidence missing")

    crosswalk = frames["partial_stats_region_crosswalk_audit.csv"]
    require(len(crosswalk) == 262, "region crosswalk audit should preserve 262 source sigungu codes")
    require((crosswalk["match_status"] == "matched").any(), "no matched source regions")

    cells = frames["partial_stats_cell_registry.csv"]
    require(len(cells) == 39672, f"unexpected cell registry rows: {len(cells)}")
    require((cells["observation_status"] == "observed").sum() == 17520, "observed anchor cell count changed")
    require(set(cells["target_name"]) == {"establishments", "employees"}, "target variables changed")
    require(set(cells["period"]) == {"2021", "2022", "2023"}, "development period changed")
    require("suppressed" not in set(cells["observation_status"]), "suppressed was asserted without source evidence")

    missing = frames["partial_stats_missingness_audit.csv"]
    overall = missing[missing["audit_axis"].eq("overall")].iloc[0]
    require(overall["observed_cells"] == "17520", "overall missingness observed count changed")
    require(float(overall["observation_rate"]) > 0.4, "observation rate unexpectedly low")
    structural_zero = frames["partial_stats_structural_zero_registry.csv"]
    require((structural_zero["structural_zero_status"] == "not_asserted").all(), "structural zero was asserted without official evidence")

    constraints = frames["partial_stats_aggregate_constraints.csv"]
    require(len(constraints) == 2531, f"unexpected constraint rows: {len(constraints)}")
    require((constraints["constraint_reliability"] == "C1_same_local_anchor_scope").all(), "constraint reliability changed")

    mask_registry = frames["partial_stats_mask_registry.csv"]
    masked = frames["partial_stats_masked_cells.csv"]
    require(mask_registry["mask_id"].nunique() == len(MASK_SCENARIOS) * MASK_REPETITIONS, "mask run count changed")
    require(set(mask_registry["mask_scenario"]) == set(MASK_SCENARIOS), "mask scenario set changed")
    require((mask_registry["actual_value_hidden_from_training"] == "Y").all(), "mask leakage guard missing")
    require(len(masked) > 0, "masked cells missing")
    coverage = frames["partial_stats_mask_coverage_audit.csv"]
    require((coverage["status"] == "pass").all(), "mask coverage audit failed")

    model_registry = frames["partial_stats_model_registry.csv"]
    require("M1_hierarchical_ridge" in set(model_registry["model_id"]), "Ridge model registry missing")
    require("B6_IPF" in set(model_registry["model_id"]), "IPF baseline registry missing")

    baseline = frames["partial_stats_baseline_results.csv"]
    model = frames["partial_stats_model_results.csv"]
    require(len(baseline) == 1440, f"unexpected baseline result rows: {len(baseline)}")
    require(len(model) == 480, f"unexpected model result rows: {len(model)}")
    selection = frames["partial_stats_model_selection.csv"]
    require(len(selection) == 2, "selection should have two target rows")
    require((selection["best_candidate_model"] == "M1_hierarchical_ridge").all(), "best candidate changed")
    require((selection["grade"] == "B").all(), "Phase 5 first pass should produce Grade B development candidates")
    require((selection["production_use"] == "false").all(), "production use was improperly enabled")
    require((selection["confirmatory_claim"] == "false").all(), "confirmatory claim was improperly enabled")
    require((selection["block_mask_consistency_pass"] == "Y").all(), "block mask consistency did not pass")
    require((selection["relative_improvement"].astype(float) > 0.05).all(), "relative improvement gate failed")

    placebo = frames["partial_stats_placebo.csv"]
    bootstrap = frames["partial_stats_selection_aware_bootstrap.csv"]
    uncertainty_calibration = frames["partial_stats_uncertainty_calibration.csv"]
    require((placebo["status"] == "registered_not_run").all(), "placebo was executed or status changed unexpectedly")
    require((bootstrap["status"] == "registered_not_run").all(), "bootstrap was executed or status changed unexpectedly")
    require((uncertainty_calibration["status"] == "registered_not_run").all(), "uncertainty calibration status changed")

    est = frames["estimated_establishment_cells.csv"]
    emp = frames["estimated_employee_cells.csv"]
    require(len(est) == 19836 and len(emp) == 19836, "estimated cell row counts changed")
    require("estimated_mask_validated" in set(est["estimate_status"]), "establishment unobserved estimates missing")
    require("estimated_mask_validated" in set(emp["estimate_status"]), "employee unobserved estimates missing")
    require((est["reconciliation_method"] == "R0_none_development").all(), "unexpected establishment reconciliation method")
    require((emp["reconciliation_method"] == "R0_none_development").all(), "unexpected employee reconciliation method")

    require(manifest["production_use"] is False, "manifest production use changed")
    require(manifest["confirmatory_use"] is False, "manifest confirmatory use changed")
    require(manifest["same_actual_retuning_allowed"] is False, "same-actual retuning was enabled")
    require(manifest["mask_registry_hash"], "mask registry hash missing")
    require(manifest["random_seeds"] == [20260718], "random seed changed")

    report = REPORT.read_text(encoding="utf-8")
    for section in range(1, 28):
        require(f"## {section}." in report, f"report section {section} missing")
    require("Grade B development 후보" in report, "report does not describe Grade B development candidate")
    require("production_use=false" in report, "report does not preserve production prohibition")

    print(
        json.dumps(
            {
                "cp949_csv_count": len(CSV_OUTPUTS) + len(EXTRA_OUTPUTS),
                "ksic8_9_rows": len(ksic),
                "cell_registry_rows": len(cells),
                "observed_cells": int((cells["observation_status"] == "observed").sum()),
                "mask_runs": int(mask_registry["mask_id"].nunique()),
                "baseline_rows": len(baseline),
                "model_rows": len(model),
                "selection": selection[["target_name", "best_candidate_wmape", "relative_improvement", "grade"]].to_dict("records"),
                "production_use": manifest["production_use"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
