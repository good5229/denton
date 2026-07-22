#!/usr/bin/env python3
"""Spatially join Goyang bus station-month activity to administrative dong."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path


BOUNDARY = Path("data/raw/phase37_goyang_emd/goyang_top_adstrd.geojson")
SRC = Path("data/processed/phase60_gg_bus_station_coordinates/goyang_bus_station_monthly_with_coordinates.csv")
OUT_DIR = Path("data/processed/phase61_goyang_bus_emd")
OUT = OUT_DIR / "goyang_bus_emd_monthly.csv"
STATION_OUT = OUT_DIR / "goyang_bus_station_monthly_with_emd.csv"
MANIFEST = OUT_DIR / "phase61_manifest.json"
REPORT = Path("reports/partial_statistics_estimation_phase61_goyang_bus_emd_monthly.md")


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-30) + xi):
            inside = not inside
        j = i
    return inside


def point_in_polygon(x: float, y: float, geom: dict) -> bool:
    if geom["type"] == "Polygon":
        rings = geom["coordinates"]
        if not point_in_ring(x, y, rings[0]):
            return False
        return not any(point_in_ring(x, y, hole) for hole in rings[1:])
    if geom["type"] == "MultiPolygon":
        return any(point_in_polygon(x, y, {"type": "Polygon", "coordinates": poly}) for poly in geom["coordinates"])
    return False


def load_polygons() -> list[dict]:
    gj = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    polys = []
    for feat in gj["features"]:
        props = feat["properties"]
        geom = feat["geometry"]
        # bbox for quick reject
        coords = []
        if geom["type"] == "Polygon":
            coords = [pt for ring in geom["coordinates"] for pt in ring]
        elif geom["type"] == "MultiPolygon":
            coords = [pt for poly in geom["coordinates"] for ring in poly for pt in ring]
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]
        polys.append({"emd_cd": props.get("cd", ""), "emd_nm": props.get("nm", ""), "geom": geom, "bbox": (min(xs), min(ys), max(xs), max(ys))})
    return polys


def assign_emd(lon: float, lat: float, polygons: list[dict]) -> tuple[str, str]:
    for p in polygons:
        minx, miny, maxx, maxy = p["bbox"]
        if not (minx <= lon <= maxx and miny <= lat <= maxy):
            continue
        if point_in_polygon(lon, lat, p["geom"]):
            return p["emd_cd"], p["emd_nm"]
    return "", ""


def wgs84_to_epsg5179(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """Approximate GRS80 Transverse Mercator forward projection for EPSG:5179.

    EPSG:5179 / Korea 2000 Unified CS:
      lat_0=38, lon_0=127.5, k=0.9996, x_0=1000000, y_0=2000000.
    """
    a = 6378137.0
    inv_f = 298.257222101
    f = 1.0 / inv_f
    e2 = 2 * f - f * f
    ep2 = e2 / (1 - e2)
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    lat0 = math.radians(38.0)
    lon0 = math.radians(127.5)
    k0 = 0.9996
    x0 = 1_000_000.0
    y0 = 2_000_000.0

    def meridian_arc(phi: float) -> float:
        e4 = e2 * e2
        e6 = e4 * e2
        return a * (
            (1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
            - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
            + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi)
            - (35 * e6 / 3072) * math.sin(6 * phi)
        )

    n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    t = math.tan(lat) ** 2
    c = ep2 * math.cos(lat) ** 2
    aa = (lon - lon0) * math.cos(lat)
    m = meridian_arc(lat)
    m0 = meridian_arc(lat0)
    x = x0 + k0 * n * (
        aa
        + (1 - t + c) * aa**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * ep2) * aa**5 / 120
    )
    y = y0 + k0 * (
        (m - m0)
        + n
        * math.tan(lat)
        * (
            aa**2 / 2
            + (5 - t + 9 * c + 4 * c**2) * aa**4 / 24
            + (61 - 58 * t + t**2 + 600 * c - 330 * ep2) * aa**6 / 720
        )
    )
    return x, y


def to_int(v: str) -> int:
    try:
        return int(float(v))
    except Exception:
        return 0


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    polygons = load_polygons()
    station_rows = []
    agg = defaultdict(lambda: [0, 0, 0, 0, 0, 0])  # station_month_rows, unique_station slots later, board, first, transfer, alight
    station_seen = defaultdict(set)
    counts = defaultdict(int)
    with SRC.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            emd_cd = emd_nm = ""
            if row.get("coord_matched") == "Y" and row.get("wgs84_lat") and row.get("wgs84_logt"):
                try:
                    lon = float(row["wgs84_logt"])
                    lat = float(row["wgs84_lat"])
                    x, y = wgs84_to_epsg5179(lon, lat)
                    emd_cd, emd_nm = assign_emd(x, y, polygons)
                except Exception:
                    pass
            new = dict(row)
            new["emd_cd"] = emd_cd
            new["emd_nm"] = emd_nm
            new["emd_matched"] = "Y" if emd_cd else "N"
            station_rows.append(new)
            counts["rows"] += 1
            counts["coord_matched" if row.get("coord_matched") == "Y" else "coord_unmatched"] += 1
            counts["emd_matched" if emd_cd else "emd_unmatched"] += 1
            if emd_cd:
                key = (row["month"], emd_cd, emd_nm)
                vals = agg[key]
                vals[0] += 1
                vals[2] += to_int(row["board_total"])
                vals[3] += to_int(row["first_board_total"])
                vals[4] += to_int(row["transfer_total"])
                vals[5] += to_int(row["alight_total"])
                station_seen[key].add(row["station_id"])

    for key, stations in station_seen.items():
        agg[key][1] = len(stations)

    with STATION_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(station_rows[0].keys()))
        w.writeheader()
        w.writerows(station_rows)

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "emd_cd", "emd_nm", "station_month_rows", "unique_stations", "board_total", "first_board_total", "transfer_total", "alight_total", "passenger_total"])
        for (month, emd_cd, emd_nm), vals in sorted(agg.items()):
            passenger = vals[2] + vals[5]
            w.writerow([month, emd_cd, emd_nm, *vals, passenger])

    manifest = {
        "boundary": str(BOUNDARY),
        "source": str(SRC),
        "station_output": str(STATION_OUT),
        "emd_monthly_output": str(OUT),
        "boundary_polygons": len(polygons),
        "rows": counts["rows"],
        "coord_match_rate": counts["coord_matched"] / counts["rows"] if counts["rows"] else 0,
        "emd_match_rate": counts["emd_matched"] / counts["rows"] if counts["rows"] else 0,
        "emd_monthly_rows": len(agg),
        "counts": dict(counts),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Phase61 고양시 행정동×월 버스 승하차 활동지표",
        "",
        "## 결론",
        "",
        f"- 고양 정류소×월 승하차 자료 {counts['rows']:,}행을 행정동 경계 44개와 공간결합했다.",
        f"- 좌표 매칭률은 {manifest['coord_match_rate']:.1%}, 행정동 공간결합률은 {manifest['emd_match_rate']:.1%}다.",
        f"- 최종 `행정동×월` 활동지표는 {len(agg):,}행이다.",
        "- 이 지표는 H00 전체 GVA를 단독 대체하지 않고, 운수·창고업 중 여객 운송/이동수요 활동의 월별·공간별 배분근거로 사용해야 한다.",
        "",
        "## 산출물",
        "",
        f"- `{OUT}`",
        f"- `{STATION_OUT}`",
        f"- `{MANIFEST}`",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
