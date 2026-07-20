from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def main() -> int:
    status = json.loads((DATA / "partial_stats_phase44_pohang_status.json").read_text())
    detail = pd.read_csv(DATA / "partial_stats_phase44_pohang_industry_weight_cv_detail.csv", encoding="utf-8-sig")
    selection = pd.read_csv(DATA / "partial_stats_phase44_pohang_industry_weight_selection.csv", encoding="utf-8-sig")
    assert set(detail.industry_level) == {"중분류", "소분류"}
    assert selection.heldout_parent.nunique() >= 14
    assert selection[["selected_establishment_weight", "selected_employee_weight"]].sum(axis=1).sub(1).abs().max() < 1e-12
    assert status["middle_cv_mae_pp"] < status["middle_equal_weight_mae_pp"]
    assert status["small_cv_mae_pp"] < status["small_equal_weight_mae_pp"]
    print(f"phase44 industry verification: PASS middle={status['middle_cv_mae_pp']:.3f} small={status['small_cv_mae_pp']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
