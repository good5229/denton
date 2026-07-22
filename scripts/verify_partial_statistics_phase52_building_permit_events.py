#!/usr/bin/env python3
"""Verify Phase52 BuildingHUB permit event collection."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase52_building_permit_events.md"


def main() -> None:
    paths = {
        "events": DATA / "partial_stats_phase52_building_permit_events_goyang_pohang.csv",
        "monthly": DATA / "partial_stats_phase52_building_permit_legal_dong_monthly.csv",
        "manifest": DATA / "partial_stats_phase52_building_permit_collection_manifest.csv",
        "status": DATA / "partial_stats_phase52_status.json",
    }
    for path in list(paths.values()) + [REPORT]:
        if not path.exists():
            raise SystemExit(f"missing output: {path}")
    events = pd.read_csv(paths["events"])
    monthly = pd.read_csv(paths["monthly"])
    manifest = pd.read_csv(paths["manifest"])
    status = json.loads(paths["status"].read_text(encoding="utf-8"))

    if set(events["city"]) != {"고양시", "포항시"}:
        raise SystemExit("event city coverage mismatch")
    if int(status["target_legal_dongs"]) != 310 or len(manifest) != 310:
        raise SystemExit("legal dong collection count mismatch")
    if len(events) != int(status["raw_event_rows"]):
        raise SystemExit("raw event row count mismatch")
    if set(monthly["event_type"]) != {"허가", "착공", "사용승인"}:
        raise SystemExit("monthly event types mismatch")
    if monthly["period"].min() < "2021-01" or monthly["period"].max() > "2026-06":
        raise SystemExit("monthly period outside expected range")
    if monthly["event_count"].sum() <= 0 or monthly["event_floor_area"].sum() <= 0:
        raise SystemExit("monthly event features are empty")
    if "legal-to-admin" not in status["guardrail"]:
        raise SystemExit("legal-to-admin guardrail missing")

    text = REPORT.read_text(encoding="utf-8")
    for token in ["법정동", "건축인허가", "행정동 배분", "착공"]:
        if token not in text:
            raise SystemExit(f"report missing token: {token}")
    print("Phase52 verification: PASS")
    print(
        {
            "events": int(len(events)),
            "monthly_rows": int(len(monthly)),
            "period_min": str(monthly["period"].min()),
            "period_max": str(monthly["period"].max()),
        }
    )


if __name__ == "__main__":
    main()
