from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def main() -> int:
    status = json.loads((DATA / "partial_stats_phase42_pohang_status.json").read_text())
    base = pd.read_parquet(DATA / "partial_stats_phase42_pohang_emd_group_monthly.parquet")
    multi = pd.read_parquet(DATA / "partial_stats_phase42_pohang_multiresolution_cube.parquet")
    checks = pd.read_csv(DATA / "partial_stats_phase42_pohang_accounting.csv", encoding="utf-8-sig")
    holdout = pd.read_csv(DATA / "partial_stats_phase42_pohang_industry_holdout_summary.csv", encoding="utf-8-sig")
    diagnostics = pd.read_csv(DATA / "partial_stats_phase42_pohang_industry_diagnostics.csv", encoding="utf-8-sig")
    assert status["emd"] == 29 and status["months"] == 36 and status["sections"] == 19
    assert status["divisions"] >= 70 and status["groups"] >= 220
    assert base.emd_code.nunique() == 29 and base.period.nunique() == 36
    assert not base.duplicated(["period", "emd_code", "group_code"]).any()
    assert set(multi.geo_level) == {"시", "구", "읍면동"} and set(multi.time_level) == {"연", "분기", "월"}
    assert set(multi.industry_level) == {"대분류", "중분류", "소분류"}
    assert checks.max_abs_error.max() < 1e-6
    assert set(holdout.industry_level) == {"중분류", "소분류"}
    assert set(diagnostics.prediction_group) == {"예측 양호", "예측 보통", "예측 취약"}
    print(f"phase42 model verification: PASS base={len(base)} multi={len(multi)} accounting={checks.max_abs_error.max():.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
