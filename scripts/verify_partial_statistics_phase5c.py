from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from kosis_common import PROCESSED_DIR, ROOT
from run_partial_statistics_phase5c import (
    BOOTSTRAP_ITERATIONS,
    CSV_OUTPUTS,
    INNER_REPETITIONS,
    MODEL_IDS,
    OUTER_REPETITIONS,
    OUTER_SCENARIOS,
    PLACEBO_ITERATIONS,
    TARGETS,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    frames = {name: frame(name) for name in CSV_OUTPUTS}
    masks = frames["partial_stats_phase5c_mask_results.csv"]
    require(len(masks) == len(OUTER_SCENARIOS) * OUTER_REPETITIONS, f"unexpected outer mask rows: {len(masks)}")
    require(set(masks["mask_scenario"]) == set(OUTER_SCENARIOS), "outer scenarios incomplete")
    require((masks["actual_value_hidden_from_training"] == "Y").all(), "outer actual firewall flag failed")

    baseline = frames["partial_stats_phase5c_baseline_results.csv"]
    models = frames["partial_stats_phase5c_model_results.csv"]
    require(set(models["model_id"]) == {model for model in MODEL_IDS if model.startswith("M")}, "one or more model candidates never completed")
    require(set(baseline["model_id"]) == {model for model in MODEL_IDS if model.startswith("B")}, "one or more strong baselines never completed")
    selection = frames["partial_stats_phase5c_inner_selection.csv"]
    require(selection[["mask_id", "target_name"]].drop_duplicates().shape[0] == len(OUTER_SCENARIOS) * OUTER_REPETITIONS * len(TARGETS), "nested inner selections incomplete")
    require((selection["inner_repetitions"].astype(int) == INNER_REPETITIONS).all(), "inner repetition count changed")
    require((selection["outer_actual_used_for_selection"] == "N").all(), "outer actual leaked into selection")

    outer = frames["partial_stats_phase5c_outer_results.csv"]
    require(set(outer["target_name"]) == set(TARGETS), "outer target missing")
    require((outer.groupby(["target_name", "mask_scenario"])["mask_id"].nunique() == OUTER_REPETITIONS).all(), "frozen outer run coverage incomplete")
    require(outer.groupby(["target_name", "mask_id"])["selected_frozen_pipeline"].apply(lambda s: int((s == "Y").sum()) == 1).all(), "more or fewer than one frozen pipeline per target-mask")

    constraints = frames["partial_stats_phase5c_constraint_population_audit.csv"]
    conflicts = frames["partial_stats_phase5c_constraint_conflicts.csv"]
    require(len(constraints) == 204, f"constraint inventory changed: {len(constraints)}")
    require(len(conflicts) >= 7, "known negative-residual parent conflicts disappeared")
    conflict_ids = set(conflicts["constraint_id"])
    require((constraints[constraints["constraint_id"].isin(conflict_ids)]["hard_constraint_allowed"] == "N").all(), "invalid parent allowed as hard constraint")
    require((frames["partial_stats_phase5c_constraint_unit_tests.csv"]["status"] == "pass").all(), "constraint toy test failed")
    require((frames["partial_stats_phase5c_metric_unit_tests.csv"]["status"] == "pass").all(), "metric/toy test failed")

    bootstrap = frames["partial_stats_phase5c_selection_aware_bootstrap.csv"]
    require(len(bootstrap) == BOOTSTRAP_ITERATIONS * len(TARGETS), f"bootstrap rows changed: {len(bootstrap)}")
    placebo = frames["partial_stats_phase5c_placebo.csv"]
    require(len(placebo) == PLACEBO_ITERATIONS * 7 * len(TARGETS), f"placebo rows changed: {len(placebo)}")
    require(placebo.groupby(["target_name", "placebo_id"])["placebo_iteration"].nunique().eq(PLACEBO_ITERATIONS).all(), "placebo iteration coverage incomplete")

    support = frames["partial_stats_phase5c_support_registry.csv"]
    require((support["support_uses_actual_value"] == "N").all(), "support label used target actual")
    estimates = pd.concat([frames["estimated_establishment_cells_phase5c.csv"], frames["estimated_employee_cells_phase5c.csv"]], ignore_index=True)
    forced_s6 = estimates[(estimates["support_class"] == "S6_not_estimable") & (estimates["estimate_status"] != "not_estimable") & (estimates["estimate_status"] != "observed_official")]
    require(forced_s6.empty, "S6 cells were force-estimated")
    observed = estimates[estimates["estimate_status"] == "observed_official"]
    require((pd.to_numeric(observed["official_value"], errors="coerce") == pd.to_numeric(observed["reconciled_estimate"], errors="coerce")).all(), "official observed values changed")

    final_status = json.loads((PROCESSED_DIR / "partial_stats_phase5c_final_status.json").read_text(encoding="utf-8"))
    require(final_status["status"] in {"success", "partial_success", "blocked_external_source", "rejected"}, "invalid final status")
    require(final_status["production_use"] is False, "production flag must remain false")
    require(final_status["confirmatory_use"] is False, "confirmatory flag must remain false")
    require(final_status["same_actual_retuning_allowed_after_completion"] is False, "same-actual retuning flag must remain false")
    manifest = json.loads((PROCESSED_DIR / "partial_stats_phase5c_experiment_manifest.json").read_text(encoding="utf-8"))
    require(manifest["actual_role"] == "development_extension", "actual role changed")
    require(manifest["same_actual_retuning_allowed"] is False, "manifest allows same-actual retuning")
    holdout = json.loads((PROCESSED_DIR / "partial_stats_phase5c_holdout_manifest.json").read_text(encoding="utf-8"))
    require(holdout["current_confirmatory_holdout"] is None, "contaminated holdout promoted")

    report = (ROOT / "reports" / "partial_statistics_estimation_phase5c.md").read_text(encoding="utf-8")
    for section in range(1, 36):
        require(f"## {section}." in report, f"report section {section} missing")
    require("Complex ML rejected" in report or "Grade A/B" in report, "final decision language missing")

    execution = frames["partial_stats_phase5c_execution_manifest.csv"]
    require((execution["status"] == "completed").all(), "execution manifest contains incomplete artifact")
    print(
        json.dumps(
            {
                "cp949_csv_count": len(frames),
                "outer_masks": len(masks),
                "nested_selection_rows": len(selection),
                "model_candidates": sorted(models["model_id"].unique()),
                "constraint_conflicts_excluded": len(conflicts),
                "bootstrap_rows": len(bootstrap),
                "placebo_rows": len(placebo),
                "final_status": final_status["status"],
                "report": "reports/partial_statistics_estimation_phase5c.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
