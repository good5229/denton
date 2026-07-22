#!/usr/bin/env python3
"""Re-enrich Goyang station-month bus features with coordinate fallback matching."""

from __future__ import annotations

import csv
import json
from pathlib import Path


COORD = Path("data/processed/phase60_gg_bus_station_coordinates/gg_bus_station_coordinates.csv")
SRC = Path("data/processed/phase58_gg_bus/gg_bus_station_monthly_goyang.csv")
OUT = Path("data/processed/phase60_gg_bus_station_coordinates/goyang_bus_station_monthly_with_coordinates.csv")
MANIFEST = Path("data/processed/phase60_gg_bus_station_coordinates/phase60_enrichment_manifest.json")


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    coords = read_csv(COORD)
    src = read_csv(SRC)
    by_id = {r["STATION_ID"]: r for r in coords if r.get("STATION_ID")}
    by_manage = {r["STATION_MANAGE_NO"]: r for r in coords if r.get("STATION_MANAGE_NO")}
    by_sigun_name = {
        (r.get("SIGUN_NM", ""), r.get("STATION_NM_INFO", "").strip()): r
        for r in coords
        if r.get("SIGUN_NM") and r.get("STATION_NM_INFO")
    }
    out = []
    method_counts = {}
    for row in src:
        c = by_id.get(row["station_id"])
        method = "station_id" if c else ""
        if not c:
            c = by_manage.get(row.get("station_no", ""))
            method = "station_manage_no" if c else ""
        if not c:
            c = by_sigun_name.get(("고양시", row.get("station_name", "").strip()))
            method = "sigun_station_name" if c else ""
        method_counts[method or "unmatched"] = method_counts.get(method or "unmatched", 0) + 1
        new = dict(row)
        new.update(
            {
                "coord_matched": "Y" if c else "N",
                "coord_match_method": method,
                "sigun_nm": c.get("SIGUN_NM", "") if c else "",
                "sigun_cd": c.get("SIGUN_CD", "") if c else "",
                "station_nm_info": c.get("STATION_NM_INFO", "") if c else "",
                "station_manage_no": c.get("STATION_MANAGE_NO", "") if c else "",
                "station_div_nm": c.get("STATION_DIV_NM", "") if c else "",
                "jurisd_inst_nm": c.get("JURISD_INST_NM", "") if c else "",
                "locplc_loc": c.get("LOCPLC_LOC", "") if c else "",
                "wgs84_lat": c.get("WGS84_LAT", "") if c else "",
                "wgs84_logt": c.get("WGS84_LOGT", "") if c else "",
            }
        )
        out.append(new)
    write_csv(OUT, out)
    manifest = {
        "source": str(SRC),
        "coordinates": str(COORD),
        "output": str(OUT),
        "rows": len(out),
        "matched": sum(v for k, v in method_counts.items() if k != "unmatched"),
        "match_rate": sum(v for k, v in method_counts.items() if k != "unmatched") / len(out) if out else 0,
        "method_counts": method_counts,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
