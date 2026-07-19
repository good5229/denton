from __future__ import annotations

import pandas as pd

from phase33_common import add_audit, write_csv


def build_confirmatory_scorecard() -> pd.DataFrame:
    rows = [
        ("A1", "Seoul outside/new EMD×section snapshot", "missing", 0, "Phase31/32 Seoul target is development-contaminated", "Retained"),
        ("A2", "new independent sigungu×middle presence/composition", "missing", 0, "business and employment share a source family; factory is broad only", "Retained"),
        ("B", "new period service-compatible GVA target", "missing", 0, "RQ1 broad service growth allows external direction only", "Retained"),
        ("C", "direct EMD GVA or independent allocation holdout", "missing", 0, "no direct EMD GVA target", "Retained"),
        ("D", "local×fine×time interaction holdout", "missing", 0, "interaction source absent", "Blocked"),
    ]
    frame = pd.DataFrame(rows, columns=["product_id", "holdout_target", "holdout_status", "confirmatory_rows", "reason", "decision"])
    frame["target_reused"] = "N"
    frame["threshold_retuned"] = "N"
    frame["confirmatory_c_count"] = 0
    frame["production_use"] = "false"
    frame["official_statistics_claim"] = "false"
    return add_audit(frame)


def main() -> int:
    write_csv("phase33_confirmatory_scorecard.csv", build_confirmatory_scorecard())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
