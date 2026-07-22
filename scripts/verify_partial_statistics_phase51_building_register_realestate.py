#!/usr/bin/env python3
"""Verify Phase51 building-register real-estate source fill."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote
from zipfile import ZipFile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase51_building_realestate_sources"
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase51_building_register_realestate.md"


def main() -> None:
    zip_path = RAW / "building_register_current_ttlldr_202606.zip"
    headers = RAW / "hub_bdrg_ttlldr_download_headers.txt"
    status_path = DATA / "partial_stats_phase51_status.json"
    rows_path = DATA / "partial_stats_phase51_building_register_goyang_pohang_rows.csv"
    legal_path = DATA / "partial_stats_phase51_realestate_legal_dong_use_features.csv"
    gu_path = DATA / "partial_stats_phase51_realestate_gu_use_features.csv"
    admin_path = DATA / "partial_stats_phase51_realestate_admin_name_direct_features.csv"
    for path in [zip_path, headers, status_path, rows_path, legal_path, gu_path, admin_path, REPORT]:
        if not path.exists():
            raise SystemExit(f"missing output: {path}")

    header_text = unquote(headers.read_text(encoding="utf-8", errors="replace"))
    if "건축물대장" not in header_text or "폐쇄말소대장" in header_text:
        raise SystemExit("download header does not confirm current building register title file")
    with ZipFile(zip_path) as zf:
        if zf.namelist() != ["mart_djy_03.txt"]:
            raise SystemExit(f"unexpected ZIP member: {zf.namelist()[:5]}")

    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status["source"]["download_id"] != "OPN202607201251380890":
        raise SystemExit("unexpected BuildingHUB download id")
    if "legal-dong" not in status["guardrail"]:
        raise SystemExit("legal/admin guardrail missing")

    rows = pd.read_csv(rows_path)
    if set(rows["city"]) != {"고양시", "포항시"}:
        raise SystemExit("city coverage mismatch")
    if rows["sigungu_cd"].astype(str).str[:5].isin(["41281", "41285", "41287", "47111", "47113"]).mean() != 1.0:
        raise SystemExit("unexpected sigungu code outside Goyang/Pohang")
    if rows["tot_area"].sum() <= 0:
        raise SystemExit("total floor area is empty")

    legal = pd.read_csv(legal_path)
    gu = pd.read_csv(gu_path)
    admin = pd.read_csv(admin_path)
    if not {"주거", "상업·업무", "산업·창고"}.issubset(set(legal["use_group"])):
        raise SystemExit("major use groups missing")
    legal_total = round(float(legal["total_floor_area"].sum()), 3)
    gu_total = round(float(gu["total_floor_area"].sum()), 3)
    if legal_total != gu_total:
        raise SystemExit("legal-dong and gu aggregations do not reconcile")
    if len(admin) == 0:
        raise SystemExit("direct administrative-name match output is empty")

    report_text = REPORT.read_text(encoding="utf-8")
    for token in ["법정동", "행정동 직접매칭", "강제 배분", "OPN202607201251380890"]:
        if token == "OPN202607201251380890":
            if token not in status_path.read_text(encoding="utf-8"):
                raise SystemExit("download id missing from status")
        elif token not in report_text:
            raise SystemExit(f"report missing guardrail token: {token}")

    print("Phase51 verification: PASS")
    print(
        {
            "rows": int(len(rows)),
            "total_floor_area": float(rows["tot_area"].sum()),
            "admin_direct_match_rate": float(rows["admin_emd_name_direct"].fillna("").ne("").mean()),
        }
    )


if __name__ == "__main__":
    main()
