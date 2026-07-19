from __future__ import annotations

import pandas as pd

from phase33_common import add_audit, write_csv


def build_reliability_calibration() -> pd.DataFrame:
    rows = [
        ("A1", "development_evidence_only", "not_calibrated", "new independent holdout missing", "do_not_show_numeric_confidence"),
        ("A2", "development_evidence_only", "not_calibrated", "fine composition holdout missing", "show source family and freshness only"),
        ("B", "observed_proxy", "not_GVA_calibrated", "observed service index; no compatible fine GVA target", "show observed proxy status"),
        ("C", "allocation_evidence_only", "not_calibrated", "allocation uncertainty not empirically identified", "show weakest component D"),
        ("D", "unavailable", "blocked", "interaction evidence missing", "show unavailable reason"),
    ]
    frame = pd.DataFrame(rows, columns=["product_id", "evidence_status", "numerical_reliability_status", "calibration_reason", "user_display_policy"])
    frame["holdout_error_monotonicity"] = "not_testable"
    frame["confidence_score"] = ""
    frame["interval_coverage"] = ""
    frame["development_confidence_user_visible"] = "N"
    return add_audit(frame)


def main() -> int:
    write_csv("phase33_reliability_calibration.csv", build_reliability_calibration())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
