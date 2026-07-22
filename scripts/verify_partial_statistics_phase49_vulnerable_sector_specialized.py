#!/usr/bin/env python3
"""Verify Phase49 vulnerable-industry specialized experiments."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase49_vulnerable_sector_specialized.md"


def require(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"missing required output: {path}")


def main() -> None:
    paths = {
        "agri": DATA / "partial_stats_phase49_agriculture_small_validation.csv",
        "construction_signal": DATA / "partial_stats_phase49_construction_workdone_signal.csv",
        "construction_validation": DATA / "partial_stats_phase49_construction_signal_validation.csv",
        "construction_summary": DATA / "partial_stats_phase49_construction_signal_summary.csv",
        "real_estate": DATA / "partial_stats_phase49_real_estate_readiness.csv",
        "transport": DATA / "partial_stats_phase49_transport_readiness.csv",
        "status": DATA / "partial_stats_phase49_status.json",
    }
    for p in paths.values():
        require(p)
    require(REPORT)

    status = json.loads(paths["status"].read_text(encoding="utf-8"))
    agri = pd.read_csv(paths["agri"])
    bad_agri_names = agri[
        agri["industry_name"].astype(str).str.contains("음료|의복|제조업", na=False)
    ]
    if len(bad_agri_names):
        raise SystemExit("agriculture selector leaked non-agriculture industries")
    agri_codes = set(agri["ksic_small_code"].astype(str).str.extract(r"(\d+)")[0].str.zfill(3))
    if not agri_codes.issubset({"011", "014", "020", "031", "032"}):
        raise SystemExit("agriculture small-code universe is unexpected")
    if status["agriculture_small"]["general_mae_pp"] <= status["agriculture_small"]["specialized_mae_pp"]:
        raise SystemExit("agriculture specialized allocation did not improve over general activity allocation")
    if status["agriculture_small"]["suppressed_cells"] < 1:
        raise SystemExit("suppressed-cell caution disappeared; expected Pohang X cells to be flagged")

    construction = pd.read_csv(paths["construction_summary"])
    cols = set(construction["share_column"].astype(str))
    expected = {
        "raw_order_share",
        "workdone_share",
        "lag_actual_share",
        "hybrid_workdone_lag_share",
    }
    if cols != expected:
        raise SystemExit(f"construction method set mismatch: {cols}")
    raw = float(construction.loc[construction["share_column"].eq("raw_order_share"), "mae_pp"].iloc[0])
    work = float(construction.loc[construction["share_column"].eq("workdone_share"), "mae_pp"].iloc[0])
    if work >= raw:
        raise SystemExit("BOK-style construction work-done signal did not improve over raw orders")
    validation = pd.read_csv(paths["construction_validation"])
    if validation["year"].min() != 2015 or validation["year"].max() != 2023:
        raise SystemExit("construction validation period changed unexpectedly")
    if validation["region"].nunique() < 15:
        raise SystemExit("construction validation lost province coverage")

    real_estate = pd.read_csv(paths["real_estate"])
    transport = pd.read_csv(paths["transport"])
    if real_estate["usable_now"].astype(bool).any():
        raise SystemExit("real estate unexpectedly marked usable; update report interpretation if source coverage changed")
    if transport["usable_now"].astype(bool).any():
        raise SystemExit("transport unexpectedly marked usable; update report interpretation if source coverage changed")

    report_text = REPORT.read_text(encoding="utf-8")
    for token in ["농림어업 소분류", "건축12·토목24분기", "성능검증 보류", "프록시"]:
        if token == "프록시":
            if token in report_text:
                raise SystemExit("report still contains jargon: 프록시")
        elif token not in report_text:
            raise SystemExit(f"report missing expected token: {token}")

    print("Phase49 verification: PASS")
    print(
        {
            "agriculture_general_mae_pp": status["agriculture_small"]["general_mae_pp"],
            "construction_workdone_mae_pp": float(
                construction.loc[construction["share_column"].eq("workdone_share"), "mae_pp"].iloc[0]
            ),
            "construction_raw_order_mae_pp": raw,
            "real_estate_status": status["real_estate"]["status"],
            "transport_status": status["transport_warehouse"]["status"],
        }
    )


if __name__ == "__main__":
    main()
