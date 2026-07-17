from __future__ import annotations

import json
import sys

import pandas as pd

from kosis_common import PROCESSED_DIR, ROOT
from run_partial_statistics_phase5b import BOOTSTRAP_ITERATIONS, CSV_OUTPUTS, REPORT, TARGETS


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing output: {name}")
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    frames = {name: frame(name) for name in CSV_OUTPUTS}

    repeat = frames["partial_stats_mask_repeat_metrics.csv"]
    require(len(repeat) == 16320, f"unexpected repeat metric rows: {len(repeat)}")
    require(repeat["mask_id"].nunique() == 240, "mask run count changed")
    require(set(repeat["target_name"]) == set(TARGETS), "target set changed")
    require({"U_unconstrained", "C_constraint_assisted"}.issubset(set(repeat["track"])), "evaluation tracks missing")

    constraints = frames["partial_stats_independent_constraint_inventory.csv"]
    require(len(constraints) == 204, f"unexpected independent constraint rows: {len(constraints)}")
    require((constraints["constraint_grade"] == "C1_same_survey_independent_table").all(), "unexpected constraint grade")
    require((constraints["constraint_role"] == "hard_constraint").all(), "unexpected constraint role")

    leakage = frames["partial_stats_phase5b_leakage_audit.csv"]
    require(len(leakage) == 480, f"unexpected leakage audit rows: {len(leakage)}")
    require((leakage["audit_status"] == "pass").all(), "leakage audit failed")
    require((leakage["hidden_cell_in_training"] == "0").all(), "hidden cells leaked into training")

    grade = frames["partial_stats_phase5_grade_reassessment.csv"]
    require(len(grade) == 2, "grade reassessment should have two target rows")
    require((grade["provisional_grade_recalculated"] == "D").all(), "Phase 5B should reject current candidates")
    require((grade["production_use"] == "false").all(), "production use was enabled")
    require((grade["confirmatory_claim"] == "false").all(), "confirmatory claim was enabled")
    require((grade["best_baseline_model"] == "B3_latest_observed_share").all(), "best baseline changed")

    bootstrap = frames["partial_stats_phase5b_selection_aware_bootstrap.csv"]
    require(len(bootstrap) == BOOTSTRAP_ITERATIONS * len(TARGETS), "bootstrap iteration count changed")
    freq = frames["partial_stats_phase5b_selected_policy_frequency.csv"]
    require(set(freq["target_name"]) == set(TARGETS), "bootstrap target summary missing")
    require((freq["bootstrap_iterations"] == str(BOOTSTRAP_ITERATIONS)).all(), "bootstrap summary iteration count changed")

    intervals = frames["partial_stats_phase5b_prediction_intervals.csv"]
    require(list(intervals.columns) == ["target_name", "model_id", "reconciliation_method", "q80_absolute_percentage_error", "q95_absolute_percentage_error", "interval_source"], "interval schema changed")
    calibration = frames["partial_stats_phase5b_uncertainty_calibration.csv"]
    require("status" in calibration.columns, "calibration schema missing status")

    est = frames["estimated_establishment_cells_phase5b.csv"]
    emp = frames["estimated_employee_cells_phase5b.csv"]
    require(len(est) == 19836 and len(emp) == 19836, "estimated cell row counts changed")
    require("S4_not_estimable" in set(est["support_level"]), "establishment risk support status missing")
    require("S4_not_estimable" in set(emp["support_level"]), "employee risk support status missing")

    manifest_path = PROCESSED_DIR / "partial_stats_phase5b_experiment_manifest.json"
    status_path = PROCESSED_DIR / "partial_stats_phase5b_final_status.json"
    require(manifest_path.exists(), "missing experiment manifest")
    require(status_path.exists(), "missing final status")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    require(manifest["production_use"] is False and manifest["confirmatory_use"] is False, "manifest enables prohibited use")
    require(manifest["same_actual_retuning_allowed"] is False, "same-actual retuning was enabled")
    require(manifest["bootstrap_iterations"] == BOOTSTRAP_ITERATIONS, "manifest bootstrap count changed")
    require(status["production_use"] is False and status["confirmatory_use"] is False, "final status enables prohibited use")

    execution = frames["partial_stats_phase5b_execution_manifest.csv"]
    require(execution["status"].str.startswith("completed").all(), "execution manifest has incomplete outputs")

    report = REPORT.read_text(encoding="utf-8")
    for section in range(1, 31):
        require(f"## {section}." in report, f"report section {section} missing")
    require("provisional_grade_recalculated" in report, "report grade table missing")
    require("production_use=false" in report, "report does not preserve production prohibition")

    print(
        json.dumps(
            {
                "cp949_csv_count": len(CSV_OUTPUTS),
                "repeat_metric_rows": len(repeat),
                "constraint_rows": len(constraints),
                "bootstrap_rows": len(bootstrap),
                "grades": grade[["target_name", "provisional_grade_recalculated", "best_baseline_model", "best_candidate_model"]].to_dict("records"),
                "report": str(REPORT.relative_to(ROOT)),
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
