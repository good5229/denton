#!/usr/bin/env python3
"""Aggregate Gyeonggi bus boarding/alighting ZIP->TAR->CSV.GZ files.

Outputs:
  - data/processed/phase58_gg_bus/gg_bus_sigun_monthly.csv
  - data/processed/phase58_gg_bus/gg_bus_goyang_daily.csv
  - data/processed/phase58_gg_bus/gg_bus_station_monthly_goyang.csv
  - data/processed/phase58_gg_bus/gg_bus_processing_manifest.json

The script streams compressed members and does not extract raw CSV files.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import re
import tarfile
import time
import zipfile
from collections import defaultdict
from pathlib import Path


RAW_DIR = Path("data/raw/phase58_gg_bus_auto/original_zips")
OUT_DIR = Path("data/processed/phase58_gg_bus")


def iter_csv_rows_from_zip(zip_path: Path):
    with zipfile.ZipFile(zip_path) as z:
        for zinfo in z.infolist():
            if not zinfo.filename.endswith(".tar"):
                continue
            tar_bytes = z.read(zinfo)
            with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
                for member in tar.getmembers():
                    if not member.name.endswith(".csv.gz"):
                        continue
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    with gzip.GzipFile(fileobj=f) as gz:
                        text = io.TextIOWrapper(gz, encoding="cp949", newline="")
                        reader = csv.DictReader(text)
                        for row in reader:
                            yield row


def to_int(value: str) -> int:
    if value is None or value == "":
        return 0
    return int(float(value))


def pick(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row:
            return row.get(name, "")
    return ""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zips = sorted(p for p in RAW_DIR.glob("*.zip") if not p.name.endswith(".part"))
    if not zips:
        raise SystemExit(f"No ZIP files found in {RAW_DIR}")

    sigun_month = defaultdict(lambda: [0, 0, 0, 0, 0])  # rows, board, first, transfer, alight
    goyang_day = defaultdict(lambda: [0, 0, 0, 0, 0])
    goyang_station_month = defaultdict(lambda: [0, 0, 0, 0, 0])
    file_stats = []
    started = time.time()

    for zip_path in zips:
        f_rows = 0
        f_board = 0
        f_alight = 0
        period_match = re.search(r"_(\d{4,6})_", zip_path.name)
        period = period_match.group(1) if period_match else ""
        for row in iter_csv_rows_from_zip(zip_path):
            date = pick(row, "승하차일자", "RIDE_DATE")
            month = date[:6]
            sigun = pick(row, "관할관청", "ORG_NM")
            station_id = pick(row, "정류소ID", "STATION_ID")
            station_no = pick(row, "정류소번호", "MOBILE_NO")
            station_name = pick(row, "정류소명", "ST_NM")
            board = to_int(pick(row, "승차합계", "RIDE_TOT_CNT"))
            first = to_int(pick(row, "초승", "RIDE_CNT"))
            transfer = to_int(pick(row, "환승", "TNS_CNT"))
            alight = to_int(pick(row, "하차", "ALIGHT_TOT_CNT"))
            vals = sigun_month[(sigun, month)]
            vals[0] += 1
            vals[1] += board
            vals[2] += first
            vals[3] += transfer
            vals[4] += alight
            if sigun == "고양시":
                dvals = goyang_day[date]
                dvals[0] += 1
                dvals[1] += board
                dvals[2] += first
                dvals[3] += transfer
                dvals[4] += alight
                svals = goyang_station_month[(month, station_id, station_no, station_name)]
                svals[0] += 1
                svals[1] += board
                svals[2] += first
                svals[3] += transfer
                svals[4] += alight
            f_rows += 1
            f_board += board
            f_alight += alight
        file_stats.append({"file": zip_path.name, "period": period, "rows": f_rows, "board": f_board, "alight": f_alight})
        print(f"processed {zip_path.name}: rows={f_rows:,}", flush=True)

    sigun_path = OUT_DIR / "gg_bus_sigun_monthly.csv"
    with sigun_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["관할관청", "month", "rows", "board_total", "first_board_total", "transfer_total", "alight_total"])
        for (sigun, month), vals in sorted(sigun_month.items()):
            w.writerow([sigun, month, *vals])

    goyang_day_path = OUT_DIR / "gg_bus_goyang_daily.csv"
    with goyang_day_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "rows", "board_total", "first_board_total", "transfer_total", "alight_total"])
        for date, vals in sorted(goyang_day.items()):
            w.writerow([date, *vals])

    goyang_station_path = OUT_DIR / "gg_bus_station_monthly_goyang.csv"
    with goyang_station_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "station_id", "station_no", "station_name", "rows", "board_total", "first_board_total", "transfer_total", "alight_total"])
        for key, vals in sorted(goyang_station_month.items()):
            w.writerow([*key, *vals])

    manifest = {
        "source_dir": str(RAW_DIR),
        "out_dir": str(OUT_DIR),
        "zip_files": len(zips),
        "elapsed_seconds": round(time.time() - started, 2),
        "sigun_month_rows": len(sigun_month),
        "goyang_day_rows": len(goyang_day),
        "goyang_station_month_rows": len(goyang_station_month),
        "outputs": {
            "sigun_monthly": str(sigun_path),
            "goyang_daily": str(goyang_day_path),
            "goyang_station_monthly": str(goyang_station_path),
        },
        "file_stats": file_stats,
    }
    manifest_path = OUT_DIR / "gg_bus_processing_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
