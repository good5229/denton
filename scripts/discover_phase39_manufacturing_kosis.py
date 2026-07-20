from __future__ import annotations

import json
import subprocess
import urllib.parse
from pathlib import Path

import pandas as pd

from kosis_common import get_kosis_key


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://kosis.kr/openapi/statisticsSearch.do"
TERMS = (
    "산업별 광공업생산지수", "산업별 생산 출하 재고 지수", "제조업 생산지수 중분류",
    "품목별 광공업생산지수", "산업중분류 생산지수", "식료품 제조업 생산지수",
)


def main() -> int:
    api_key = get_kosis_key()
    rows = []
    seen = set()
    for term in TERMS:
        params = {
            "method": "getList", "apiKey": api_key, "searchNm": term, "orgId": "101",
            "sort": "DATE", "startCount": "1", "resultCount": "1000",
            "format": "json", "jsonVD": "Y",
        }
        url = f"{BASE}?{urllib.parse.urlencode(params)}"
        response = subprocess.run(["curl", "-sS", url], check=True, text=True, capture_output=True)
        payload = json.loads(response.stdout)
        for row in payload if isinstance(payload, list) else []:
            key = (row.get("ORG_ID"), row.get("TBL_ID"))
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "org_id": row.get("ORG_ID"), "table_id": row.get("TBL_ID"),
                "table_name": row.get("TBL_NM"), "statistics_name": row.get("STAT_NM"),
                "start_period": row.get("STRT_PRD_DE"), "end_period": row.get("END_PRD_DE"),
                "path": row.get("MT_ATITLE"), "link_url": row.get("LINK_URL"), "matched_search": term,
            })
    out = ROOT / "data" / "processed" / "partial_stats_phase39_manufacturing_kosis_catalog.csv"
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
    (ROOT / "data" / "raw" / "phase39_manufacturing_kosis_catalog.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"catalog_rows={len(rows)}")
    if rows:
        print(pd.DataFrame(rows)[["table_id", "table_name", "end_period"]].head(30).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
