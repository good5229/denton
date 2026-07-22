#!/usr/bin/env python3
"""Collect Gyeonggi BusStation coordinates using DATA_GG_KEY."""

from __future__ import annotations

import csv
import json
import ssl
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path


RAW_DIR = Path("data/raw/phase60_gg_bus_station_coordinates")
OUT_DIR = Path("data/processed/phase60_gg_bus_station_coordinates")
API = "https://openapi.gg.go.kr/BusStation"


def load_key() -> str:
    vals = {}
    for line in Path(".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    key = vals.get("DATA_GG_KEY")
    if not key:
        raise SystemExit("DATA_GG_KEY is missing in .env")
    return key


def call_api(key: str, p_index: int, p_size: int = 1000, sigun_nm: str | None = None) -> dict:
    params = {"KEY": key, "Type": "json", "pIndex": str(p_index), "pSize": str(p_size)}
    if sigun_nm:
        params["SIGUN_NM"] = sigun_nm
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context()
    last_exc = None
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except (TimeoutError, urllib.error.URLError) as exc:
            last_exc = exc
            wait = min(2 * attempt, 10)
            print(f"warning: page={p_index} attempt={attempt} failed: {exc}; retry in {wait}s", flush=True)
            time.sleep(wait)
    raise last_exc


def parse_response(obj: dict) -> tuple[int, list[dict]]:
    root = obj.get("BusStation", [])
    total = 0
    rows = []
    for part in root:
        if "head" in part:
            for h in part["head"]:
                if "list_total_count" in h:
                    total = int(h["list_total_count"])
        if "row" in part:
            rows.extend(part["row"])
    return total, rows


def collect_all(key: str) -> list[dict]:
    all_rows: list[dict] = []
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint = RAW_DIR / "bus_station_rows_checkpoint.json"
    if checkpoint.exists():
        all_rows = json.loads(checkpoint.read_text(encoding="utf-8"))
        print(f"resume checkpoint rows={len(all_rows)}", flush=True)
    page = 1
    total = None
    if all_rows:
        page = len(all_rows) // 1000 + 1
    while True:
        obj = call_api(key, page, 1000)
        if page == 1:
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            (RAW_DIR / "bus_station_page1_sample.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        t, rows = parse_response(obj)
        total = total or t
        all_rows.extend(rows)
        checkpoint.write_text(json.dumps(all_rows, ensure_ascii=False), encoding="utf-8")
        print(f"page={page} rows={len(rows)} collected={len(all_rows)} total={total}", flush=True)
        if not rows or len(all_rows) >= total:
            break
        page += 1
        time.sleep(0.15)
    return all_rows


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def enrich_goyang_station_month(rows: list[dict]) -> dict:
    coord_by_id = {str(r.get("STATION_ID", "")): r for r in rows if r.get("STATION_ID")}
    coord_by_manage = {str(r.get("STATION_MANAGE_NO", "")): r for r in rows if r.get("STATION_MANAGE_NO")}
    coord_by_sigun_name = {
        (str(r.get("SIGUN_NM", "")), str(r.get("STATION_NM_INFO", "")).strip()): r
        for r in rows
        if r.get("SIGUN_NM") and r.get("STATION_NM_INFO")
    }
    src = Path("data/processed/phase58_gg_bus/gg_bus_station_monthly_goyang.csv")
    out_path = OUT_DIR / "goyang_bus_station_monthly_with_coordinates.csv"
    out_rows = []
    matched = 0
    total = 0
    with src.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            c = coord_by_id.get(str(row["station_id"]))
            match_method = "station_id" if c else ""
            if not c:
                c = coord_by_manage.get(str(row.get("station_no", "")))
                match_method = "station_manage_no" if c else ""
            if not c:
                c = coord_by_sigun_name.get(("고양시", str(row.get("station_name", "")).strip()))
                match_method = "sigun_station_name" if c else ""
            if c:
                matched += 1
            out = dict(row)
            out.update(
                {
                    "coord_matched": "Y" if c else "N",
                    "coord_match_method": match_method,
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
            out_rows.append(out)
    fields = list(out_rows[0].keys()) if out_rows else []
    write_csv(out_path, out_rows, fields)
    return {"path": str(out_path), "rows": total, "matched": matched, "match_rate": matched / total if total else 0}


def main() -> int:
    key = load_key()
    rows = collect_all(key)
    fields = [
        "SIGUN_NM",
        "SIGUN_CD",
        "STATION_NM_INFO",
        "ENG_STATION_NM_INFO",
        "STATION_ID",
        "STATION_MANAGE_NO",
        "STATION_DIV_NM",
        "JURISD_INST_NM",
        "LOCPLC_LOC",
        "WGS84_LAT",
        "WGS84_LOGT",
    ]
    all_path = OUT_DIR / "gg_bus_station_coordinates.csv"
    write_csv(all_path, rows, fields)
    goyang_rows = [r for r in rows if r.get("SIGUN_NM") == "고양시"]
    goyang_path = OUT_DIR / "gg_bus_station_coordinates_goyang.csv"
    write_csv(goyang_path, goyang_rows, fields)
    enrich = enrich_goyang_station_month(rows)
    manifest = {
        "source": API,
        "api_key_env": "DATA_GG_KEY",
        "rows": len(rows),
        "goyang_rows": len(goyang_rows),
        "outputs": {
            "all_coordinates": str(all_path),
            "goyang_coordinates": str(goyang_path),
            "goyang_station_month_enriched": enrich["path"],
        },
        "goyang_station_month_match": enrich,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "phase60_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
