#!/usr/bin/env python3
"""Collect CALS construction list and annual contract rows.

This collector is intentionally narrow: it only touches the CALS public
construction list and the annual contract endpoint needed for the construction
GVA allocation experiment.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase241_cals_construction_contracts"
OUT = ROOT / "data" / "processed"
LIST_URL = "https://www.calspia.go.kr/io/openapi/cm/selectIoCmConstructionList.do"
CONTRACT_URL = "https://www.calspia.go.kr/io/openapi/cm/selectIoCmProjConstYearContractList.do"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


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


def service_key() -> str:
    load_env()
    key = os.environ.get("CALS_API_KEY")
    if not key:
        raise SystemExit("CALS_API_KEY missing in .env")
    return key


def ssl_context() -> ssl.SSLContext:
    # CALS currently presents a certificate chain that the local Python build
    # does not trust.  This collector is only used against the official CALS
    # host and stores responses without the service key.
    return ssl._create_unverified_context()


def fetch_json(url: str, params: dict[str, Any], key: str, timeout: int) -> dict[str, Any]:
    request = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(request, timeout=timeout, context=ssl_context()) as response:
        text = response.read().decode("utf-8", errors="replace")
    # The key is not returned by CALS, but keep this belt-and-suspenders guard.
    text = text.replace(key, "[REDACTED_CALS_API_KEY]")
    return json.loads(text)


def body(data: dict[str, Any]) -> dict[str, Any]:
    response = data.get("response", {})
    header = response.get("header", {}) if isinstance(response, dict) else {}
    code = str(header.get("resultCode", ""))
    if code not in ("", "0"):
        raise RuntimeError(f"CALS resultCode={code} msg={header.get('resultMsg')} kor={header.get('resultKorMsg')}")
    b = response.get("body", {}) if isinstance(response, dict) else {}
    return b if isinstance(b, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-rows", type=int, default=200)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=0.03)
    parser.add_argument("--limit-contracts", type=int, default=0, help="0 means all construction rows")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    key = service_key()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    list_rows: list[dict[str, Any]] = []
    page = 1
    total = None
    while True:
        path = RAW / f"construction_list_p{page:04d}_n{args.num_rows}.json"
        if path.exists() and not args.refresh:
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = fetch_json(
                LIST_URL,
                {"serviceKey": key, "type": "json", "pageNo": page, "numOfRows": args.num_rows},
                key,
                args.timeout,
            )
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        b = body(data)
        if total is None:
            total = int(b.get("totalCount") or 0)
        items = b.get("items") or []
        if isinstance(items, dict):
            items = [items]
        list_rows.extend([x for x in items if isinstance(x, dict)])
        print(f"list page={page} rows={len(items)} total={total}", flush=True)
        if page * args.num_rows >= total:
            break
        page += 1
        if args.sleep:
            time.sleep(args.sleep)

    contract_rows: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    targets = list_rows[: args.limit_contracts] if args.limit_contracts else list_rows
    for i, item in enumerate(targets, start=1):
        spt_no = str(item.get("sptNo") or "").strip()
        if not spt_no:
            continue
        path = RAW / f"contract_{spt_no}.json"
        try:
            if path.exists() and not args.refresh:
                data = json.loads(path.read_text(encoding="utf-8"))
            else:
                data = fetch_json(CONTRACT_URL, {"serviceKey": key, "type": "json", "sptNo": spt_no}, key, args.timeout)
                path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            b = body(data)
            detail = b.get("detail1") or {}
            items = b.get("items") or []
            if isinstance(items, dict):
                items = [items]
            for row in items:
                if not isinstance(row, dict):
                    continue
                contract_rows.append({**detail, **{f"contract_{k}": v for k, v in row.items()}})
            manifest.append(
                {
                    "created_at": CREATED_AT,
                    "sptNo": spt_no,
                    "cwkNm": item.get("cwkNm"),
                    "pdznNm": item.get("pdznNm"),
                    "bzarNm": item.get("bzarNm"),
                    "contract_rows": len(items),
                    "ok": True,
                    "error": "",
                }
            )
        except Exception as exc:  # keep going; a partial CALS cache is still useful
            manifest.append(
                {
                    "created_at": CREATED_AT,
                    "sptNo": spt_no,
                    "cwkNm": item.get("cwkNm"),
                    "pdznNm": item.get("pdznNm"),
                    "bzarNm": item.get("bzarNm"),
                    "contract_rows": 0,
                    "ok": False,
                    "error": repr(exc),
                }
            )
        if i % 100 == 0:
            print(f"contracts probed={i}/{len(targets)} rows={len(contract_rows)}", flush=True)
        if args.sleep:
            time.sleep(args.sleep)

    (OUT / "phase241_cals_construction_list.csv").write_text("", encoding="utf-8")
    try:
        import pandas as pd

        pd.DataFrame(list_rows).to_csv(OUT / "phase241_cals_construction_list.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(contract_rows).to_csv(OUT / "phase241_cals_construction_contract_rows.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(manifest).to_csv(OUT / "phase241_cals_construction_contract_manifest.csv", index=False, encoding="utf-8-sig")
    except Exception:
        (OUT / "phase241_cals_construction_list.json").write_text(json.dumps(list_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT / "phase241_cals_construction_contract_rows.json").write_text(json.dumps(contract_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT / "phase241_cals_construction_contract_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"done list_rows={len(list_rows)} contract_rows={len(contract_rows)} manifest_rows={len(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
