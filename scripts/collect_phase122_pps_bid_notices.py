#!/usr/bin/env python3
"""Collect PPS/Nara procurement bid notices for Goyang/Pohang GVA features.

The API service itself is nationwide.  This collector therefore keeps two
separate notions of scope:

* raw cached API pages are nationwide pages for the requested operation/month;
* processed CSV files contain only Goyang/Pohang-related notices selected by
  text matching over institution, notice, region-limit and product fields.

The script is intentionally resumable.  Existing cache files are reused unless
`--refresh` is supplied.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase122_pps_bid_notices"
OUT = ROOT / "data" / "processed" / "phase122_pps_bid_notices"

BASE_URL = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService"

OPS = {
    "servc": "getBidPblancListInfoServc",
    "cnstwk": "getBidPblancListInfoCnstwk",
    "thng": "getBidPblancListInfoThng",
    "servc_pps": "getBidPblancListInfoServcPPSSrch",
    "cnstwk_pps": "getBidPblancListInfoCnstwkPPSSrch",
    "thng_pps": "getBidPblancListInfoThngPPSSrch",
}

CITY_PATTERNS = {
    "고양시": ["고양", "고양시", "고양특례시", "일산동구", "일산서구", "덕양구"],
    "포항시": ["포항", "포항시", "포항남구", "포항북구", "포항시 남구", "포항시 북구"],
}

TEXT_FIELDS = [
    "bidNtceNm",
    "ntceInsttNm",
    "dminsttNm",
    "refNo",
    "crdtrNm",
    "rgnLmtBidLocplcJdgmBssNm",
    "rgnDutyJntcontrctRt",
    "jntcontrctDutyRgnNm1",
    "jntcontrctDutyRgnNm2",
    "jntcontrctDutyRgnNm3",
    "incntvRgnNm1",
    "incntvRgnNm2",
    "incntvRgnNm3",
    "incntvRgnNm4",
    "pubPrcrmntLrgClsfcNm",
    "pubPrcrmntMidClsfcNm",
    "pubPrcrmntClsfcNm",
    "purchsObjPrdctList",
    "srvceDivNm",
    "cnstrtsiteRgnNm",
]

KEEP_FIELDS = [
    "city",
    "op",
    "period",
    "matched_patterns",
    "bidNtceNo",
    "bidNtceOrd",
    "reNtceYn",
    "ntceKindNm",
    "bidNtceDt",
    "bidNtceNm",
    "ntceInsttNm",
    "dminsttNm",
    "bidMethdNm",
    "cntrctCnclsMthdNm",
    "srvceDivNm",
    "pubPrcrmntLrgClsfcNm",
    "pubPrcrmntMidClsfcNm",
    "pubPrcrmntClsfcNo",
    "pubPrcrmntClsfcNm",
    "asignBdgtAmt",
    "presmptPrce",
    "VAT",
    "bidBeginDt",
    "bidClseDt",
    "opengDt",
    "rgnLmtBidLocplcJdgmBssNm",
    "jntcontrctDutyRgnNm1",
    "jntcontrctDutyRgnNm2",
    "jntcontrctDutyRgnNm3",
    "bidNtceDtlUrl",
]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, value = s.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def public_data_key() -> str:
    load_dotenv(ROOT / ".env")
    for name in (
        "DATA_GO_KR_DECODING",
        "DATA_GO_KR_ENCODING",
        "PUBLIC_DATA_API_KEY",
        "DATA_GO_API_KEY",
        "SERVICE_KEY",
    ):
        value = os.environ.get(name)
        if value:
            return value
    raise SystemExit("공공데이터포털 serviceKey를 찾지 못했습니다. .env의 DATA_GO_KR_DECODING 또는 DATA_GO_KR_ENCODING을 확인하세요.")


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
    import calendar

    y, m = int(period[:4]), int(period[4:])
    last = calendar.monthrange(y, m)[1]
    return f"{period}010000", f"{period}{last:02d}2359"


def normalize_items(body: dict[str, Any]) -> list[dict[str, Any]]:
    items = body.get("items", [])
    if items is None:
        return []
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    if isinstance(items, dict):
        item = items.get("item", items)
        if isinstance(item, list):
            return [x for x in item if isinstance(x, dict)]
        if isinstance(item, dict):
            return [item]
    return []


def safe_suffix(extra_params: dict[str, str]) -> str:
    if not extra_params:
        return ""
    parts = []
    for key, value in sorted(extra_params.items()):
        s = re.sub(r"[^0-9A-Za-z가-힣]+", "-", f"{key}-{value}").strip("-")
        parts.append(s[:80])
    return "_" + "__".join(parts)


def fetch_page(op: str, period: str, page: int, num_rows: int, key: str, refresh: bool, extra_params: dict[str, str], timeout: float) -> dict[str, Any]:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{op}_{period}{safe_suffix(extra_params)}_{page:03d}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))

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
    params.update(extra_params)
    url = f"{BASE_URL}/{OPS[op]}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8", errors="replace")
    data = json.loads(payload)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def response_body(data: dict[str, Any]) -> dict[str, Any]:
    res = data.get("response", data)
    header = res.get("header", {})
    code = str(header.get("resultCode", ""))
    if code and code != "00":
        raise RuntimeError(f"API resultCode={code} resultMsg={header.get('resultMsg', '')}")
    body = res.get("body", {})
    return body if isinstance(body, dict) else {}


def city_match(item: dict[str, Any]) -> list[tuple[str, list[str]]]:
    text = " ".join(str(item.get(field, "") or "") for field in TEXT_FIELDS)
    out = []
    for city, pats in CITY_PATTERNS.items():
        matched = [p for p in pats if p in text]
        if matched:
            out.append((city, matched))
    return out


def collect(
    op: str,
    period: str,
    num_rows: int,
    max_pages: int | None,
    sleep_sec: float,
    key: str,
    refresh: bool,
    extra_params: dict[str, str],
    timeout: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total_count = None
    pages_done = 0
    for page in range(1, (max_pages or 999999) + 1):
        data = fetch_page(op, period, page, num_rows, key, refresh, extra_params, timeout)
        body = response_body(data)
        items = normalize_items(body)
        if total_count is None:
            total_count = int(body.get("totalCount") or 0)
        pages_done += 1
        for item in items:
            for city, pats in city_match(item):
                row = {k: item.get(k, "") for k in KEEP_FIELDS if k not in {"city", "op", "period", "matched_patterns"}}
                row.update({"city": city, "op": op, "period": period, "matched_patterns": "|".join(pats)})
                rows.append(row)
        if page * num_rows >= total_count:
            break
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return rows, {
        "op": op,
        "period": period,
        "query_params": json.dumps(extra_params, ensure_ascii=False, sort_keys=True),
        "total_count": total_count or 0,
        "pages_done": pages_done,
        "filtered_rows": len(rows),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({field: row.get(field, "") for field in fields})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="202301")
    parser.add_argument("--end", default="202309")
    parser.add_argument("--ops", default="servc,cnstwk,thng", help="comma-separated: servc,cnstwk,thng")
    parser.add_argument("--num-rows", type=int, default=999)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.15)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--query-param",
        action="append",
        default=[],
        help="extra API query parameter, e.g. dminsttNm=고양시. Can be repeated.",
    )
    parser.add_argument("--output-tag", default="", help="suffix for output CSV/manifest names")
    args = parser.parse_args()

    key = public_data_key()
    selected_ops = [x.strip() for x in args.ops.split(",") if x.strip()]
    bad = sorted(set(selected_ops) - set(OPS))
    if bad:
        raise SystemExit(f"Unknown ops: {bad}")
    extra_params: dict[str, str] = {}
    for item in args.query_param:
        if "=" not in item:
            raise SystemExit(f"--query-param must be name=value: {item}")
        k, v = item.split("=", 1)
        extra_params[k.strip()] = v.strip()

    OUT.mkdir(parents=True, exist_ok=True)
    tag = f"_{re.sub(r'[^0-9A-Za-z가-힣]+', '_', args.output_tag).strip('_')}" if args.output_tag else ""
    all_rows: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for period in month_range(args.start, args.end):
        for op in selected_ops:
            try:
                rows, info = collect(op, period, args.num_rows, args.max_pages, args.sleep, key, args.refresh, extra_params, args.timeout)
                all_rows.extend(rows)
                summary.append(info)
                print(f"{period} {op}: total={info['total_count']} pages={info['pages_done']} filtered={info['filtered_rows']} query={info['query_params']}", flush=True)
            except Exception as exc:  # keep a durable audit instead of aborting the whole batch
                err = {"op": op, "period": period, "query_params": json.dumps(extra_params, ensure_ascii=False, sort_keys=True), "error": repr(exc)}
                errors.append(err)
                print(f"ERROR {period} {op}: {exc}", file=sys.stderr)

    filtered_path = OUT / f"phase122_pps_goyang_pohang_filtered_notices{tag}.csv"
    summary_path = OUT / f"phase122_pps_collection_summary{tag}.csv"
    errors_path = OUT / f"phase122_pps_collection_errors{tag}.csv"
    manifest_path = OUT / f"phase122_pps_manifest{tag}.json"
    write_csv(filtered_path, all_rows, KEEP_FIELDS)
    write_csv(summary_path, summary, ["op", "period", "query_params", "total_count", "pages_done", "filtered_rows"])
    write_csv(errors_path, errors, ["op", "period", "query_params", "error"])

    manifest = {
        "source_name": "조달청_나라장터 입찰공고정보서비스",
        "source_url": "https://www.data.go.kr/data/15129394/openapi.do",
        "api_base_used": BASE_URL,
        "raw_scope": "nationwide API pages for requested operation/month",
        "processed_scope": "Goyang/Pohang text-matched subset",
        "period_start": args.start,
        "period_end": args.end,
        "ops": selected_ops,
        "query_params": extra_params,
        "raw_cache_dir": str(RAW.relative_to(ROOT)),
        "filtered_csv": str(filtered_path.relative_to(ROOT)),
        "summary_csv": str(summary_path.relative_to(ROOT)),
        "errors_csv": str(errors_path.relative_to(ROOT)),
        "note": "Do not treat text matching as final city attribution. Use as a candidate public-demand activity source for construction/professional-service GVA refinement.",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(filtered_path)


if __name__ == "__main__":
    main()
