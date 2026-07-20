from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def main() -> int:
    status = json.loads((DATA / "partial_stats_phase43_pohang_status.json").read_text())
    spatial = pd.read_csv(DATA / "partial_stats_phase43_pohang_spatial_cv_detail.csv", encoding="utf-8-sig", dtype={"division_code": str, "emd_code": str})
    gu = pd.read_csv(DATA / "partial_stats_phase43_pohang_gu_sales_cv_detail.csv", encoding="utf-8-sig", dtype={"division_code": str})
    common = pd.read_csv(DATA / "partial_stats_phase43_pohang_common_proxy_audit.csv", encoding="utf-8-sig")
    assert spatial.division_code.nunique() == 74 and spatial.emd_code.nunique() == 29
    assert not spatial.duplicated(["division_code", "emd_code"]).any()
    assert np_close(spatial.groupby("division_code").cv_predicted_share.sum(), 1)
    assert gu.division_code.nunique() >= 65 and gu.cv_predicted_sales_share.between(0, 1).all()
    assert common.section_code.nunique() == 19
    assert status["factory_both_match_rate"] >= .70
    assert status["full_replication_sections"] == 0
    assert status["improved_spatial_cv_mae_pp"] < status["baseline_spatial_mae_pp"]
    assert status["improved_gu_sales_cv_mae_pp"] < status["baseline_gu_sales_mae_pp"]
    print(f"phase43 improvement verification: PASS spatial={status['improved_spatial_cv_mae_pp']:.3f} gu_sales={status['improved_gu_sales_cv_mae_pp']:.3f}")
    return 0


def np_close(values: pd.Series, target: float) -> bool:
    return bool(((values - target).abs() < 1e-9).all())


if __name__ == "__main__":
    raise SystemExit(main())
