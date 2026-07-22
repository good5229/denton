#!/usr/bin/env python3
"""Verify Phase50 free-source fill outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase50_free_source_fill.md"


def main() -> None:
    monthly_path = DATA / "partial_stats_phase50_logistics_warehouse_emd_monthly.csv"
    audit_path = DATA / "partial_stats_phase50_logistics_warehouse_source_audit.csv"
    readiness_path = DATA / "partial_stats_phase50_free_source_readiness.csv"
    status_path = DATA / "partial_stats_phase50_status.json"
    for path in [monthly_path, audit_path, readiness_path, status_path, REPORT]:
        if not path.exists():
            raise SystemExit(f"missing output: {path}")

    monthly = pd.read_csv(monthly_path)
    audit = pd.read_csv(audit_path)
    readiness = pd.read_csv(readiness_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))

    if set(audit["city"]) != {"고양시", "포항시"}:
        raise SystemExit("audit city coverage mismatch")
    if audit["raw_rows"].sum() != 69:
        raise SystemExit("unexpected raw logistics row count")
    if audit["matched_emd_rate"].min() < 0.95:
        raise SystemExit("warehouse coordinate-to-EMD match rate below guardrail")
    if monthly["ksic_small"].astype(str).str.zfill(3).nunique() != 1:
        raise SystemExit("monthly logistics feature should map only to KSIC 521")
    if set(monthly["industry_name"].astype(str)) != {"보관 및 창고업"}:
        raise SystemExit("monthly logistics industry name mismatch")
    if monthly["period"].min() != "2021-01" or monthly["period"].max() != "2026-06":
        raise SystemExit("monthly feature period mismatch")
    if not readiness.query("sector == '운수 및 창고업'")["usable_now"].astype(bool).all():
        raise SystemExit("transport/warehouse readiness should be partially usable")
    if readiness.query("sector == '부동산업'")["usable_now"].astype(bool).any():
        raise SystemExit("real-estate readiness should remain blocked without building/transaction data")
    if "LOCALDATA logistics_warehouses for Goyang and Pohang" not in status["downloaded_without_api_key"]:
        raise SystemExit("status does not record no-key logistics download")

    text = REPORT.read_text(encoding="utf-8")
    for token in ["보관 및 창고업", "운수·창고업 전체 성능 개선이 아니라", "건축물대장"]:
        if token not in text:
            raise SystemExit(f"report missing token: {token}")

    print("Phase50 verification: PASS")
    print(
        {
            "monthly_rows": int(len(monthly)),
            "goyang_raw_rows": int(audit.loc[audit["city"].eq("고양시"), "raw_rows"].iloc[0]),
            "pohang_raw_rows": int(audit.loc[audit["city"].eq("포항시"), "raw_rows"].iloc[0]),
            "min_match_rate": float(audit["matched_emd_rate"].min()),
        }
    )


if __name__ == "__main__":
    main()
