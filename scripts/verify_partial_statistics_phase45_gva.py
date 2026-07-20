from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def main() -> int:
    status = json.loads((DATA / "partial_stats_phase45_pohang_status.json").read_text())
    base = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_emd_small_monthly.parquet")
    cube = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet")
    checks = pd.read_csv(DATA / "partial_stats_phase45_pohang_final_accounting.csv", encoding="utf-8-sig")
    common = pd.read_csv(DATA / "partial_stats_phase45_pohang_final_common_proxy_audit.csv", encoding="utf-8-sig")
    diagnostics = pd.read_csv(DATA / "partial_stats_phase45_pohang_final_industry_diagnostics.csv", encoding="utf-8-sig")
    assert (status["emd"], status["months"], status["sections"], status["divisions"], status["groups"]) == (29, 36, 19, 74, 228)
    assert not base.duplicated(["period", "emd_code", "group_code"]).any()
    assert set(cube.geo_level) == {"시", "구", "읍면동"} and set(cube.time_level) == {"연", "분기", "월"}
    assert checks.max_abs_error.max() < 1e-6
    assert status["full_replication_sections"] == 4 and common.section_code.nunique() == 19
    replicated = set(common.loc[common.identical_profile_rate.eq(1), "section_code"])
    assert replicated == {"B", "D", "F", "O"}
    assert {"예측 양호", "예측 보통", "예측 취약"} <= set(diagnostics.prediction_group)
    print(f"phase45 final verification: PASS base={len(base)} cube={len(cube)} accounting={checks.max_abs_error.max():.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
