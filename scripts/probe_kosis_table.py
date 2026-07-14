from __future__ import annotations

import json
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, get_kosis_key, write_csv, write_json


BASE = "https://kosis.kr/openapi/Param/statisticsParameterData.do"


def request_json(params: dict[str, str]) -> Any:
    completed = subprocess.run(
        ["curl", "-sS", f"{BASE}?{urllib.parse.urlencode(params)}"],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(completed.stdout)
    if isinstance(data, dict) and data.get("err"):
        raise RuntimeError(f"KOSIS error {data.get('err')}: {data.get('errMsg')}")
    return data


def probe(org_id: str, tbl_id: str) -> list[dict[str, Any]]:
    api_key = get_kosis_key()
    params = {
        "method": "getList",
        "apiKey": api_key,
        "orgId": org_id,
        "tblId": tbl_id,
        "itmId": "ALL",
        "objL1": "ALL",
        "objL2": "ALL",
        "objL3": "ALL",
        "objL4": "ALL",
        "objL5": "ALL",
        "prdSe": "Y",
        "startPrdDe": "2023",
        "endPrdDe": "2023",
        "format": "json",
        "jsonVD": "Y",
    }
    return request_json(params)


def normalize_sample(org_id: str, tbl_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows[:200]:
        norm = {
            "org_id": org_id,
            "tbl_id": tbl_id,
            "tbl_nm": row.get("TBL_NM"),
            "prd_de": row.get("PRD_DE"),
            "item_id": row.get("ITM_ID"),
            "item_nm": row.get("ITM_NM"),
            "unit_nm": row.get("UNIT_NM"),
            "value": row.get("DT"),
        }
        for idx in range(1, 9):
            code = row.get(f"C{idx}")
            name = row.get(f"C{idx}_NM")
            if code is not None or name is not None:
                norm[f"c{idx}_id"] = code
                norm[f"c{idx}_nm"] = name
        out.append(norm)
    return out


def main() -> int:
    if len(sys.argv) < 3:
        raise SystemExit("usage: probe_kosis_table.py ORG_ID TBL_ID [ORG_ID TBL_ID ...]")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    for i in range(1, len(sys.argv), 2):
        org_id, tbl_id = sys.argv[i], sys.argv[i + 1]
        try:
            rows = probe(org_id, tbl_id)
        except Exception as exc:
            summary.append({"org_id": org_id, "tbl_id": tbl_id, "status": "error", "error": str(exc)})
            continue
        write_json(RAW_DIR / f"probe_{org_id}_{tbl_id}.json", rows)
        sample = normalize_sample(org_id, tbl_id, rows)
        write_csv(PROCESSED_DIR / f"probe_{org_id}_{tbl_id}.csv", sample)
        dims = sorted({key for row in sample for key in row if key.startswith("c") and key.endswith("_id")})
        summary.append(
            {
                "org_id": org_id,
                "tbl_id": tbl_id,
                "status": "ok",
                "rows": len(rows),
                "tbl_nm": rows[0].get("TBL_NM") if rows else "",
                "dimensions": ",".join(dims),
            }
        )
    write_csv(PROCESSED_DIR / "probe_kosis_tables_summary.csv", summary)
    for row in summary:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
