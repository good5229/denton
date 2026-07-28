#!/usr/bin/env python3
"""Collect public local-government office coordinates from ESRI Korea.

The source item describes geocoded Korean local-government offices based on
MOIS local-government office address data. It is used only as a coordinate
source for dashboard map movement; it is not part of the GRDP/GVA estimation.
"""

from __future__ import annotations

import csv
import json
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "admin_center_coordinates" / "esri_local_government_offices"
PROCESSED = ROOT / "data" / "processed" / "admin_center_coordinates"
BASE = "https://portal.esrikr.com/arcgis/rest/services/Hosted/KR_Local_Government_Office/FeatureServer"
ITEM = "https://portal.esrikr.com/portal/sharing/rest/content/items/4417b15bfaa84eb3af14e527f2a135ca?f=json"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

LAYERS = {
    0: "도청",
    1: "시청",
    2: "구청",
    3: "군청",
}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def query_layer(layer_id: int) -> dict:
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
    }
    return fetch_json(f"{BASE}/{layer_id}/query?{urllib.parse.urlencode(params)}")


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    item = fetch_json(ITEM)
    (RAW / "item_metadata.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    service = fetch_json(f"{BASE}?f=json")
    (RAW / "service_metadata.json").write_text(json.dumps(service, ensure_ascii=False, indent=2), encoding="utf-8")

    rows: list[dict] = []
    for layer_id, office_type in LAYERS.items():
        obj = query_layer(layer_id)
        (RAW / f"layer_{layer_id}_{office_type}.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        for feature in obj.get("features", []):
            attr = feature.get("attributes", {}) or {}
            geom = feature.get("geometry", {}) or {}
            lon = attr.get("x", geom.get("x"))
            lat = attr.get("y", geom.get("y"))
            rows.append(
                {
                    "source_id": "esri_kr_local_government_office_4417b15bfaa84eb3af14e527f2a135ca",
                    "source_title": item.get("title"),
                    "source_url": item.get("url") or BASE,
                    "source_access_information": item.get("accessInformation"),
                    "source_license_info": item.get("licenseInfo"),
                    "source_modified_epoch_ms": item.get("modified"),
                    "service_updated": "2025.02",
                    "raw_data_source": "행정안전부",
                    "data_reference_date": "2016.12",
                    "collected_at": CREATED_AT,
                    "layer_id": layer_id,
                    "office_type": office_type,
                    "objectid": attr.get("objectid"),
                    "name": attr.get("name"),
                    "address": attr.get("address"),
                    "postal": attr.get("postal"),
                    "tel": attr.get("tel"),
                    "homepage": attr.get("homepage"),
                    "lat": lat,
                    "lon": lon,
                }
            )

    out = PROCESSED / "esri_local_government_offices_2025.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "created_at": CREATED_AT,
        "rows": len(rows),
        "layers": LAYERS,
        "raw_dir": str(RAW.relative_to(ROOT)),
        "processed_csv": str(out.relative_to(ROOT)),
        "source_item": "https://portal.esrikr.com/portal/home/item.html?id=4417b15bfaa84eb3af14e527f2a135ca",
        "feature_server": BASE,
    }
    (PROCESSED / "esri_local_government_offices_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
