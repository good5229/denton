#!/usr/bin/env python3
"""Audit completeness of robust PPS construction raw cache."""

from __future__ import annotations

import argparse
import json
import re
from math import ceil
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase122_pps_bid_notices_robust"
OUT = ROOT / "nationwide" / "outputs"


def body_of(data: dict[str, Any]) -> dict[str, Any]:
    res = data.get("response", data)
    body = res.get("body", {})
    return body if isinstance(body, dict) else {}


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


def audit(start: str, end: str, num_rows: int) -> pd.DataFrame:
    rows = []
    pattern = re.compile(rf"cnstwk_(20\d{{4}})_n{num_rows}_(\d{{4}})\.json$")
    by_period: dict[str, list[tuple[int, Path]]] = {}
    for path in RAW.glob(f"cnstwk_*_n{num_rows}_*.json"):
        m = pattern.match(path.name)
        if not m:
            continue
        by_period.setdefault(m.group(1), []).append((int(m.group(2)), path))
    for period in month_range(start, end):
        pages = sorted(by_period.get(period, []))
        total_count = 0
        item_sum = 0
        page_nums = []
        for page, path in pages:
            data = json.loads(path.read_text(encoding="utf-8"))
            body = body_of(data)
            if not total_count:
                total_count = int(body.get("totalCount") or 0)
            items = body.get("items", [])
            n = 0
            if isinstance(items, list):
                n = len(items)
            elif isinstance(items, dict):
                item = items.get("item", items)
                if isinstance(item, list):
                    n = len(item)
                elif isinstance(item, dict):
                    n = 1
            item_sum += n
            page_nums.append(page)
        expected_pages = ceil(total_count / num_rows) if total_count else 0
        missing = [p for p in range(1, expected_pages + 1) if p not in set(page_nums)] if expected_pages else []
        rows.append(
            {
                "period": period,
                "num_rows": num_rows,
                "total_count": total_count,
                "expected_pages": expected_pages,
                "cached_pages": len(page_nums),
                "cached_items": item_sum,
                "complete": bool(expected_pages and len(page_nums) >= expected_pages and not missing),
                "missing_page_count": len(missing),
                "missing_pages_head": ",".join(map(str, missing[:30])),
                "cached_pages_head": ",".join(map(str, page_nums[:30])),
                "cached_pages_tail": ",".join(map(str, page_nums[-10:])),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="202101")
    parser.add_argument("--end", default="202512")
    parser.add_argument("--num-rows", type=int, default=100)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    df = audit(args.start, args.end, args.num_rows)
    tag = f"{args.start}_{args.end}_n{args.num_rows}"
    out = OUT / f"pps_construction_robust_completeness_{tag}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"wrote {out.relative_to(ROOT)}")
    print(df[df["cached_pages"].gt(0)].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
