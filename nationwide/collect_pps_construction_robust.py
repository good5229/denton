#!/usr/bin/env python3
"""Robust collector for PPS construction bid notices.

The older Phase122 collector stores files as `cnstwk_YYYYMM_page.json`.
Changing `numOfRows` with that layout is unsafe because page numbers no
longer refer to the same row ranges.  This collector writes to a separate raw
directory and includes `numOfRows` in file names.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase122_pps_bid_notices_robust"
OUT = ROOT / "nationwide" / "outputs"
BASE_URL = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def public_data_key() -> str:
    load_dotenv(ROOT / ".env")
    for name in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING", "PUBLIC_DATA_API_KEY", "DATA_GO_API_KEY", "SERVICE_KEY"):
        val = os.environ.get(name)
        if val:
            return val
    raise SystemExit("Missing public data API key in .env")


def month_range(start: str, end: str) -> list[str]:
    y, m = int(start[:4]), int(start[4:])
    ey, em = int(end[:4]), int(end[4:])
    out: list[str] = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}{m:02d}")
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


def month_bounds(period: str) -> tuple[str, str]:
    y, m = int(period[:4]), int(period[4:])
    return f"{period}010000", f"{period}{monthrange(y, m)[1]:02d}2359"


def body_of(data: dict[str, Any]) -> dict[str, Any]:
    res = data.get("response", data)
    header = res.get("header", {})
    code = str(header.get("resultCode", ""))
    if code and code != "00":
        raise RuntimeError(f"resultCode={code} resultMsg={header.get('resultMsg', '')}")
    body = res.get("body", {})
    return body if isinstance(body, dict) else {}


def items_count(data: dict[str, Any]) -> int:
    items = body_of(data).get("items", [])
    if isinstance(items, dict):
        item = items.get("item", items)
        if isinstance(item, list):
            return len(item)
        if isinstance(item, dict):
            return 1
    if isinstance(items, list):
        return len(items)
    return 0


def fetch(period: str, page: int, num_rows: int, key: str, timeout: float, refresh: bool) -> tuple[dict[str, Any], Path]:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"cnstwk_{period}_n{num_rows}_{page:04d}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8")), path
    begin, end = month_bounds(period)
    params = {
        "serviceKey": key,
        "pageNo": page,
        "numOfRows": num_rows,
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": begin,
        "inqryEndDt": end,
    }
    req = Request(f"{BASE_URL}?{urlencode(params)}", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8", errors="replace")
    data = json.loads(payload)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data, path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="202104")
    parser.add_argument("--end", default="202104")
    parser.add_argument("--num-rows", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--max-consecutive-errors", type=int, default=3)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    key = public_data_key()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    errors = []
    for period in month_range(args.start, args.end):
        total_count = None
        page = args.start_page
        pages_done = 0
        rows_done = 0
        consecutive_errors = 0
        while True:
            try:
                data, path = fetch(period, page, args.num_rows, key, args.timeout, args.refresh)
                body = body_of(data)
                if total_count is None:
                    total_count = int(body.get("totalCount") or 0)
                n = items_count(data)
                pages_done += 1
                rows_done += n
                consecutive_errors = 0
                print(f"{period} page={page} rows={n} total={total_count} file={path.name}", flush=True)
                if page * args.num_rows >= total_count:
                    break
                if args.end_page is not None and page >= args.end_page:
                    break
                page += 1
                if args.sleep:
                    time.sleep(args.sleep)
            except Exception as exc:
                errors.append({"period": period, "page": page, "num_rows": args.num_rows, "error": repr(exc)})
                print(f"ERROR {period} page={page}: {exc}", flush=True)
                consecutive_errors += 1
                if consecutive_errors >= args.max_consecutive_errors:
                    break
                page += 1
        manifest.append(
            {
                "created_at": CREATED_AT,
                "period": period,
                "num_rows": args.num_rows,
                "total_count": total_count if total_count is not None else 0,
                "pages_done": pages_done,
                "rows_done": rows_done,
                "complete": bool(total_count is not None and pages_done * args.num_rows >= total_count),
                "raw_dir": str(RAW.relative_to(ROOT)),
            }
        )
    tag = f"{args.start}_{args.end}_n{args.num_rows}"
    (OUT / f"pps_construction_robust_manifest_{tag}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / f"pps_construction_robust_errors_{tag}.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote nationwide/outputs/pps_construction_robust_manifest_{tag}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
