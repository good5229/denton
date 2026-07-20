from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from kosis_common import PROCESSED_DIR, ROOT


def main() -> None:
    status = json.loads((PROCESSED_DIR / "partial_stats_phase36_gva_status.json").read_text(encoding="utf-8"))
    accounting = pd.read_csv(PROCESSED_DIR / "partial_stats_phase36_gva_accounting_checks.csv", encoding="cp949")
    common = pd.read_csv(PROCESSED_DIR / "partial_stats_phase36_gva_common_proxy_audit.csv", encoding="cp949")
    assert status["seoul_gu"] == 25
    assert status["goyang_emd"] == 39
    assert status["sectors"] == ["ERS", "G00", "H00", "I00", "L00", "MN0", "P00", "Q00"]
    assert accounting["max_abs_error"].max() < 1e-5
    goyang = common[common["scope"].str.startswith("Goyang")]
    seoul = common[common["scope"].str.startswith("Seoul")]
    assert goyang["effective_rank"].eq(1).all()
    assert goyang["all_profiles_identical"].all()
    assert not seoul["all_profiles_identical"].any()
    assert "block_emd_specific_monthly_dynamics_claim" in status["decision"]
    assert (ROOT / "reports" / "partial_statistics_estimation_phase36_gva.md").exists()
    print("Phase36 verification passed")


if __name__ == "__main__":
    main()
