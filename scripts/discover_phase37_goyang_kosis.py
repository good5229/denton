from __future__ import annotations

import json
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any

import pandas as pd

from kosis_common import get_kosis_key


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "phase37_goyang_emd" / "kosis_620_catalog.json"
OUT_PATH = ROOT / "data" / "processed" / "partial_stats_phase37_goyang_kosis_catalog.csv"
BASE = "https://kosis.kr/openapi/statisticsSearch.do"
SEARCH_TERMS = ("사업체", "읍면동", "동별", "종사자", "산업")
KEYWORDS = ("읍면동", "동별", "사업체", "종사자", "산업", "지역별")


def search(api_key: str, term: str) -> list[dict[str, Any]]:
    params = {
        "method": "getList",
        "apiKey": api_key,
        "searchNm": term,
        "orgId": "620",
        "sort": "DATE",
        "startCount": "1",
        "resultCount": "1000",
        "format": "json",
        "jsonVD": "Y",
    }
    url = f"{BASE}?{urllib.parse.urlencode(params)}"
    response = subprocess.run(["curl", "-sS", url], check=True, text=True, capture_output=True)
    payload = json.loads(response.stdout)
    if isinstance(payload, dict) and payload.get("err"):
        raise RuntimeError(f"KOSIS error {payload.get('err')}: {payload.get('errMsg')}")
    return payload if isinstance(payload, list) else []


def main() -> int:
    api_key = get_kosis_key()
    rows: list[dict[str, Any]] = []
    seen_tables: set[tuple[str, str]] = set()
    for term in SEARCH_TERMS:
        for row in search(api_key, term):
            key = (str(row.get("ORG_ID") or ""), str(row.get("TBL_ID") or ""))
            if key in seen_tables:
                continue
            seen_tables.add(key)
            record = {
                "org_id": row.get("ORG_ID"),
                "org_name": row.get("ORG_NM"),
                "table_id": row.get("TBL_ID"),
                "table_name": row.get("TBL_NM"),
                "statistics_name": row.get("STAT_NM"),
                "start_period": row.get("STRT_PRD_DE"),
                "end_period": row.get("END_PRD_DE"),
                "path": row.get("MT_ATITLE"),
                "link_url": row.get("LINK_URL"),
                "matched_search": term,
            }
            text = " ".join(str(value or "") for value in row.values())
            record["relevance_keyword"] = next((word for word in KEYWORDS if word in text), "")
            rows.append(record)
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps({"org_id": "620", "search_terms": SEARCH_TERMS, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT_PATH, index=False)
    relevant = sum(bool(row["relevance_keyword"]) for row in rows)
    print(f"catalog rows: {len(rows)}; relevant rows: {relevant}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
