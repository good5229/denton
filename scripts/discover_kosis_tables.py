from __future__ import annotations

import csv
import json
import subprocess
import sys
import urllib.parse
from collections import deque
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, get_kosis_key, write_csv, write_json


BASE = "https://kosis.kr/openapi/statisticsList.do"
KEYWORDS = [
    "지역내총생산",
    "지역내총부가가치",
    "시군구",
    "읍면동",
    "사업체",
    "종사자",
    "광업제조업조사",
    "서비스업조사",
    "전국사업체조사",
    "경제총조사",
    "산업분류",
    "KSIC",
]


def request_json(params: dict[str, str]) -> Any:
    query = urllib.parse.urlencode(params)
    completed = subprocess.run(
        ["curl", "-sS", f"{BASE}?{query}"],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(completed.stdout)
    if isinstance(data, dict) and data.get("err"):
        raise RuntimeError(f"KOSIS error {data.get('err')}: {data.get('errMsg')}")
    return data


def children(api_key: str, parent: str) -> list[dict[str, Any]]:
    data = request_json(
        {
            "method": "getList",
            "apiKey": api_key,
            "vwCd": "MT_ZTITLE",
            "parentListId": parent,
            "format": "json",
            "jsonVD": "Y",
        }
    )
    if not isinstance(data, list):
        return []
    return data


def row_text(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(key, "")) for key in sorted(row))


def main() -> int:
    api_key = get_kosis_key()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    roots = sys.argv[2:] if len(sys.argv) > 2 else ["A"]
    queue: deque[tuple[str, int]] = deque((root, 0) for root in roots)
    seen: set[str] = set()
    matched: list[dict[str, Any]] = []
    visited: list[dict[str, Any]] = []
    max_nodes = int(sys.argv[1]) if len(sys.argv) > 1 else 2500

    while queue and len(seen) < max_nodes:
        parent, depth = queue.popleft()
        if parent in seen:
            continue
        seen.add(parent)
        try:
            rows = children(api_key, parent)
        except Exception as exc:
            visited.append({"parent": parent, "depth": depth, "error": str(exc)})
            continue
        for row in rows:
            out = {
                "parent": parent,
                "depth": depth,
                "vw_cd": row.get("VW_CD"),
                "list_id": row.get("LIST_ID"),
                "list_nm": row.get("LIST_NM"),
                "org_id": row.get("ORG_ID"),
                "tbl_id": row.get("TBL_ID"),
                "tbl_nm": row.get("TBL_NM"),
                "prd_se": row.get("PRD_SE"),
            }
            visited.append(out)
            text = row_text(row)
            if any(keyword.lower() in text.lower() for keyword in KEYWORDS):
                matched.append(out | {"matched_text": text[:500]})
            child_id = row.get("LIST_ID")
            if child_id and not row.get("TBL_ID"):
                queue.append((str(child_id), depth + 1))

    write_json(RAW_DIR / "kosis_catalog_discovery.json", {"visited": visited, "matched": matched})
    write_csv(PROCESSED_DIR / "kosis_catalog_discovery_visited.csv", visited)
    write_csv(PROCESSED_DIR / "kosis_catalog_discovery_matches.csv", matched)
    print(f"visited parents: {len(seen)}")
    print(f"visited rows: {len(visited)}")
    print(f"matched rows: {len(matched)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
