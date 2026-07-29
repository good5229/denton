#!/usr/bin/env python3
"""Collect PPS contract/order-plan and LH notice activity for construction routing.

The collector stores raw monthly JSON and normalized CSV summaries.  It uses
the public data decoding key because the newly approved PPS/LH endpoints reject
the encoded key in this environment.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import time
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase243_public_construction_activity"
OUT = ROOT / "data" / "processed"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

PPS_CONTRACT_URL = "https://apis.data.go.kr/1230000/ao/CntrctInfoService/getCntrctInfoListCnstwk"
PPS_ORDER_URL = "https://apis.data.go.kr/1230000/ao/OrderPlanSttusService/getOrderPlanSttusListCnstwkPPSSrch"
LH_URL = "https://apis.data.go.kr/B552555/lhLeaseNoticeInfo1/lhLeaseNoticeInfo1"


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api_key() -> str:
    load_env()
    key = os.environ.get("DATA_GO_KR_DECODING")
    if not key:
        raise SystemExit("DATA_GO_KR_DECODING missing in .env")
    return key


def ssl_context() -> ssl.SSLContext:
    # apis.data.go.kr presents a certificate chain that can fail on the local
    # Python build.  Restrict this bypass to official public-data hosts.
    return ssl._create_unverified_context()


def month_iter(start: str, end: str) -> list[str]:
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


def month_bounds_yyyymmddhhmm(period: str) -> tuple[str, str]:
    y, m = int(period[:4]), int(period[4:])
    return f"{period}010000", f"{period}{monthrange(y, m)[1]:02d}2359"


def month_bounds_dot(period: str) -> tuple[str, str]:
    y, m = int(period[:4]), int(period[4:])
    return f"{y:04d}.{m:02d}.01", f"{y:04d}.{m:02d}.{monthrange(y, m)[1]:02d}"


def request_json(url: str, params: dict[str, Any], key: str, timeout: int) -> tuple[Any, str]:
    req = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json, */*"})
    with urlopen(req, timeout=timeout, context=ssl_context()) as response:
        text = response.read().decode("utf-8", errors="replace")
    text = text.replace(key, "[REDACTED_DATA_GO_KR_KEY]")
    return json.loads(text), text


def pps_body(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    response = data.get("response") or {}
    if not isinstance(response, dict):
        return {}
    header = response.get("header") or {}
    code = str(header.get("resultCode", ""))
    if code and code != "00":
        raise RuntimeError(f"PPS resultCode={code} resultMsg={header.get('resultMsg')}")
    body = response.get("body") or {}
    return body if isinstance(body, dict) else {}


def pps_items(data: Any) -> list[dict[str, Any]]:
    body = pps_body(data)
    items = body.get("items") or []
    if isinstance(items, dict):
        item = items.get("item", items)
        if isinstance(item, list):
            return [x for x in item if isinstance(x, dict)]
        if isinstance(item, dict):
            return [item]
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    return []


def collect_pps_contract(start: str, end: str, num_rows: int, timeout: int, sleep: float, refresh: bool, max_pages: int | None) -> None:
    key = api_key()
    raw_dir = RAW / "pps_contract"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for period in month_iter(start, end):
        begin, finish = month_bounds_yyyymmddhhmm(period)
        page = 1
        total = None
        period_rows = 0
        while True:
            path = raw_dir / f"pps_contract_{period}_n{num_rows}_{page:04d}.json"
            try:
                if path.exists() and not refresh:
                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    data, text = request_json(
                        PPS_CONTRACT_URL,
                        {
                            "serviceKey": key,
                            "pageNo": page,
                            "numOfRows": num_rows,
                            "type": "json",
                            "inqryDiv": "1",
                            "inqryBgnDt": begin,
                            "inqryEndDt": finish,
                        },
                        key,
                        timeout,
                    )
                    path.write_text(text, encoding="utf-8")
                body = pps_body(data)
                if total is None:
                    total = int(body.get("totalCount") or 0)
                items = pps_items(data)
                for item in items:
                    item["source_period"] = period
                    rows.append(item)
                period_rows += len(items)
                print(f"pps_contract {period} page={page} rows={len(items)} total={total}", flush=True)
                if page * num_rows >= total:
                    break
                if max_pages is not None and page >= max_pages:
                    break
                page += 1
                if sleep:
                    time.sleep(sleep)
            except Exception as exc:
                manifest.append({"source": "pps_contract", "period": period, "page": page, "ok": False, "error": repr(exc), "created_at": CREATED_AT})
                print(f"ERROR pps_contract {period} page={page}: {exc}", flush=True)
                break
        manifest.append({"source": "pps_contract", "period": period, "total_count": total or 0, "rows_collected": period_rows, "complete": bool(total is not None and (max_pages is None) and period_rows >= total), "ok": True, "error": "", "created_at": CREATED_AT})
    pd.DataFrame(rows).to_csv(OUT / f"phase243_pps_contract_rows_{start}_{end}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(manifest).to_csv(OUT / f"phase243_pps_contract_manifest_{start}_{end}.csv", index=False, encoding="utf-8-sig")


def collect_pps_order(start: str, end: str, num_rows: int, timeout: int, sleep: float, refresh: bool, max_pages: int | None) -> None:
    key = api_key()
    raw_dir = RAW / "pps_order_plan"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for period in month_iter(start, end):
        # As of the 2026-07-29 probe, the PPSSrch endpoint returns a normal
        # response but ignores the tested historical date/year filters and
        # returns current 2026 rows.  Keep this collector for future diagnosis,
        # but downstream adoption must filter and audit the returned orderYear.
        page = 1
        total = None
        period_rows = 0
        while True:
            path = raw_dir / f"pps_order_{period}_n{num_rows}_{page:04d}.json"
            try:
                if path.exists() and not refresh:
                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    data, text = request_json(
                        PPS_ORDER_URL,
                        {
                            "serviceKey": key,
                            "pageNo": page,
                            "numOfRows": num_rows,
                            "type": "json",
                            "orderYear": period[:4],
                            "orderMnth": str(int(period[4:])),
                        },
                        key,
                        timeout,
                    )
                    path.write_text(text, encoding="utf-8")
                body = pps_body(data)
                if total is None:
                    total = int(body.get("totalCount") or 0)
                items = pps_items(data)
                for item in items:
                    item["source_period"] = period
                    rows.append(item)
                period_rows += len(items)
                print(f"pps_order {period} page={page} rows={len(items)} total={total}", flush=True)
                if page * num_rows >= total:
                    break
                if max_pages is not None and page >= max_pages:
                    break
                page += 1
                if sleep:
                    time.sleep(sleep)
            except Exception as exc:
                manifest.append({"source": "pps_order", "period": period, "page": page, "ok": False, "error": repr(exc), "created_at": CREATED_AT})
                print(f"ERROR pps_order {period} page={page}: {exc}", flush=True)
                break
        manifest.append({"source": "pps_order", "period": period, "total_count": total or 0, "rows_collected": period_rows, "complete": bool(total is not None and (max_pages is None) and period_rows >= total), "ok": True, "error": "", "created_at": CREATED_AT})
    pd.DataFrame(rows).to_csv(OUT / f"phase243_pps_order_plan_rows_{start}_{end}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(manifest).to_csv(OUT / f"phase243_pps_order_plan_manifest_{start}_{end}.csv", index=False, encoding="utf-8-sig")


def collect_lh(start: str, end: str, num_rows: int, timeout: int, sleep: float, refresh: bool, max_pages: int | None) -> None:
    key = api_key()
    raw_dir = RAW / "lh_notice"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for period in month_iter(start, end):
        y, m = int(period[:4]), int(period[4:])
        begin = f"{y:04d}{m:02d}01"
        finish = f"{y:04d}{m:02d}{monthrange(y, m)[1]:02d}"
        page = 1
        total = None
        period_rows = 0
        while True:
            path = raw_dir / f"lh_notice_{period}_n{num_rows}_{page:04d}.json"
            try:
                if path.exists() and not refresh:
                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    data, text = request_json(
                        LH_URL,
                        {
                            "ServiceKey": key,
                            "PG_SZ": num_rows,
                            "PAGE": page,
                            "PAN_ST_DT": begin,
                            "PAN_ED_DT": finish,
                        },
                        key,
                        timeout,
                    )
                    path.write_text(text, encoding="utf-8")
                ds_list: list[dict[str, Any]] = []
                if isinstance(data, list):
                    for part in data:
                        if isinstance(part, dict) and isinstance(part.get("dsList"), list):
                            ds_list.extend([x for x in part["dsList"] if isinstance(x, dict)])
                if total is None:
                    for part in data if isinstance(data, list) else []:
                        if isinstance(part, dict) and isinstance(part.get("dsList"), list) and part["dsList"]:
                            try:
                                total = int(part["dsList"][0].get("ALL_CNT") or 0)
                            except Exception:
                                total = 0
                            break
                    total = total or 0
                for item in ds_list:
                    item["source_period"] = period
                    rows.append(item)
                period_rows += len(ds_list)
                print(f"lh_notice {period} page={page} rows={len(ds_list)} total={total}", flush=True)
                if page * num_rows >= total:
                    break
                if max_pages is not None and page >= max_pages:
                    break
                page += 1
                if sleep:
                    time.sleep(sleep)
            except Exception as exc:
                manifest.append({"source": "lh_notice", "period": period, "page": page, "ok": False, "error": repr(exc), "created_at": CREATED_AT})
                print(f"ERROR lh_notice {period} page={page}: {exc}", flush=True)
                break
        manifest.append({"source": "lh_notice", "period": period, "total_count": total or 0, "rows_collected": period_rows, "complete": bool(total is not None and (max_pages is None) and period_rows >= total), "ok": True, "error": "", "created_at": CREATED_AT})
    pd.DataFrame(rows).to_csv(OUT / f"phase243_lh_notice_rows_{start}_{end}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(manifest).to_csv(OUT / f"phase243_lh_notice_manifest_{start}_{end}.csv", index=False, encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["pps_contract", "pps_order", "lh", "all"], default="all")
    parser.add_argument("--start", default="202101")
    parser.add_argument("--end", default="202312")
    parser.add_argument("--num-rows", type=int, default=999)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=0.03)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.source in ("pps_contract", "all"):
        collect_pps_contract(args.start, args.end, args.num_rows, args.timeout, args.sleep, args.refresh, args.max_pages)
    if args.source in ("pps_order", "all"):
        collect_pps_order(args.start, args.end, args.num_rows, args.timeout, args.sleep, args.refresh, args.max_pages)
    if args.source in ("lh", "all"):
        collect_lh(args.start, args.end, args.num_rows, args.timeout, args.sleep, args.refresh, args.max_pages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
