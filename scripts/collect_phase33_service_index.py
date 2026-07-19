from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from kosis_common import ROOT, get_kosis_key, kosis_data, normalize_kosis_rows
from phase33_common import DERIVED_DIR, GENERATED_AT, add_audit, stable_hash, write_csv


REGION_CODES = ["11", "21", "22", "23", "24", "25", "26", "29", "31", "32", "33", "34", "35", "36", "37", "38", "39"]
ITEM_IDS = ["T1", "T2"]
START_PERIOD = "201901"
END_PERIOD = "202602"
RAW_CHUNK_DIR = ROOT / "data" / "raw" / "phase33_service_index"
OUTPUT_PARQUET = DERIVED_DIR / "phase33_service_source_current.parquet"


def collect() -> tuple[pd.DataFrame, pd.DataFrame]:
    api_key = get_kosis_key()
    RAW_CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    audit_rows = []
    for item_id in ITEM_IDS:
        for region_code in REGION_CODES:
            chunk_id = f"DT_1KC2023_{item_id}_{region_code}_{START_PERIOD}_{END_PERIOD}"
            raw_path = RAW_CHUNK_DIR / f"{chunk_id}.json"
            if raw_path.exists():
                rows = json.loads(raw_path.read_text(encoding="utf-8"))
                source_status = "cache_reused"
            else:
                rows = kosis_data(
                    api_key=api_key,
                    org_id="101",
                    tbl_id="DT_1KC2023",
                    item_id=item_id,
                    period="Q",
                    start=START_PERIOD,
                    end=END_PERIOD,
                    obj={1: region_code, 2: "ALL"},
                )
                raw_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
                source_status = "api_downloaded"
                time.sleep(0.05)
            normalized_rows = normalize_kosis_rows(rows, "service_production_index_phase33_current")
            normalized = pd.DataFrame(normalized_rows)
            if not normalized.empty:
                frames.append(normalized)
            audit_rows.append(
                {
                    "chunk_id": chunk_id,
                    "item_id": item_id,
                    "region_code": region_code,
                    "requested_start": START_PERIOD,
                    "requested_end": END_PERIOD,
                    "row_count": len(normalized),
                    "source_status": source_status,
                    "raw_path": str(raw_path.relative_to(ROOT)),
                    "response_hash": stable_hash(rows),
                    "retrieval_date": GENERATED_AT[:10],
                }
            )
    service = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    key = ["prd_de", "item_id", "c1_id", "c2_id"]
    if service.empty or service.duplicated(key).any():
        raise RuntimeError("phase33 service collection empty or duplicate key")
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    add_audit(service).to_parquet(OUTPUT_PARQUET, index=False)
    return service, add_audit(pd.DataFrame(audit_rows))


def main() -> int:
    service, audit = collect()
    write_csv("phase33_service_collection_audit.csv", audit)
    print(json.dumps({"rows": len(service), "period_min": service["prd_de"].min(), "period_max": service["prd_de"].max(), "chunks": len(audit)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
