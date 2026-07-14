from __future__ import annotations

import csv
import html
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, write_csv, write_json


BASE = "https://kosis.kr/statHtml/statHtmlContent.do"


def fetch(org_id: str, tbl_id: str) -> str:
    params = urllib.parse.urlencode({"orgId": org_id, "tblId": tbl_id, "conn_path": "C1"})
    completed = subprocess.run(
        ["curl", "-L", "-sS", f"{BASE}?{params}"],
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout


def parse_info(text: str) -> dict[str, Any]:
    match = re.search(r"var\s+g_jsonStatInfo\s*=\s*'(.+?)';", text, re.S)
    if not match:
        raise RuntimeError("g_jsonStatInfo not found")
    return json.loads(html.unescape(match.group(1)))


def metadata_rows(org_id: str, tbl_id: str, info: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dims = []
    codes = []
    item_info = info.get("itemInfo") or {}
    dims.append(
        {
            "org_id": org_id,
            "tbl_id": tbl_id,
            "tbl_nm": info.get("tblNm"),
            "dimension_id": "ITM_ID",
            "dimension_name": item_info.get("itmNm", "항목"),
            "item_count": item_info.get("itmCnt"),
            "levels": "",
            "period": info.get("periodStr"),
            "period_range": info.get("containPeriod"),
        }
    )
    for item in item_info.get("itmList", []):
        codes.append(
            {
                "org_id": org_id,
                "tbl_id": tbl_id,
                "dimension_id": "ITM_ID",
                "dimension_name": item_info.get("itmNm", "항목"),
                "code": item.get("itmId"),
                "name": item.get("scrKor"),
                "level": item.get("lvl"),
                "parent_code": item.get("upItmId"),
                "leaf": item.get("leaf"),
            }
        )
    for class_info in info.get("classInfoList", []):
        dims.append(
            {
                "org_id": org_id,
                "tbl_id": tbl_id,
                "tbl_nm": info.get("tblNm"),
                "dimension_id": class_info.get("classId"),
                "dimension_name": class_info.get("classNm"),
                "item_count": class_info.get("itmCnt"),
                "levels": class_info.get("depthLvl"),
                "period": info.get("periodStr"),
                "period_range": info.get("containPeriod"),
            }
        )
        for item in class_info.get("itmList", []):
            codes.append(
                {
                    "org_id": org_id,
                    "tbl_id": tbl_id,
                    "dimension_id": class_info.get("classId"),
                    "dimension_name": class_info.get("classNm"),
                    "code": item.get("itmId"),
                    "name": item.get("scrKor"),
                    "level": item.get("lvl"),
                    "parent_code": item.get("upItmId"),
                    "leaf": item.get("leaf"),
                }
            )
    return dims, codes


def main() -> int:
    if len(sys.argv) < 3 or len(sys.argv[1:]) % 2:
        raise SystemExit("usage: fetch_kosis_metadata.py ORG_ID TBL_ID [ORG_ID TBL_ID ...]")
    all_dims = []
    all_codes = []
    for i in range(1, len(sys.argv), 2):
        org_id, tbl_id = sys.argv[i], sys.argv[i + 1]
        try:
            text = fetch(org_id, tbl_id)
            info = parse_info(text)
        except Exception as exc:
            all_dims.append({"org_id": org_id, "tbl_id": tbl_id, "error": str(exc)})
            continue
        (RAW_DIR / f"kosis_{org_id}_{tbl_id}_statHtmlContent.html").write_text(text, encoding="utf-8")
        write_json(RAW_DIR / f"kosis_{org_id}_{tbl_id}_metadata.json", info)
        dims, codes = metadata_rows(org_id, tbl_id, info)
        all_dims.extend(dims)
        all_codes.extend(codes)
    write_csv(PROCESSED_DIR / "kosis_candidate_metadata_dimensions.csv", all_dims)
    write_csv(PROCESSED_DIR / "kosis_candidate_metadata_codes.csv", all_codes)
    for row in all_dims:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
