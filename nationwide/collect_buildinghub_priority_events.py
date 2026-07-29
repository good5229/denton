#!/usr/bin/env python3
"""Collect BuildingHUB permit/start/approval events for priority sigungu.

The collector is intentionally staged: it uses
``construction_buildinghub_collection_priority.csv`` and only collects the
highest-priority sigungu requested by command-line limits.  This avoids a
premature nationwide pull while preserving a reproducible path to expansion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from kosis_common import load_env


RAW = ROOT / "data" / "raw" / "buildinghub_priority_events"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "nationwide" / "outputs"
PRIORITY = OUT / "construction_buildinghub_collection_priority.csv"
LEGAL = PROCESSED / "buildinghub_legal_dong_request_universe.csv"
ENDPOINT = "http://apis.data.go.kr/1613000/ArchPmsHubService/getApBasisOulnInfo"


def read_csv_fallback(path: Path, **kwargs) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return pd.read_csv(path, **kwargs)


def data_go_key() -> str:
    env = load_env()
    for name in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING"):
        if env.get(name):
            return str(env[name])
    raise SystemExit("DATA_GO_KR_DECODING or DATA_GO_KR_ENCODING not found in .env")


def cache_path(params: dict[str, Any], tag: str) -> Path:
    clean = {k: v for k, v in params.items() if k != "serviceKey"}
    key = hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:16]
    return RAW / tag / f"ap_basis_{clean['sigunguCd']}_{clean['bjdongCd']}_{clean['pageNo']}_{key}.json"


def ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def request_page(params: dict[str, Any], tag: str, timeout: int, refresh: bool = False) -> dict[str, Any]:
    path = cache_path(params, tag)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{ENDPOINT}?{query}", headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
            text = response.read().decode("utf-8-sig", errors="replace")
            data = json.loads(text) if text.strip() else {}
            payload = {
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type", ""),
                "request_parameters": {k: v for k, v in params.items() if k != "serviceKey"},
                "data": data,
                "error": "",
            }
    except Exception as exc:
        payload = {
            "http_status": "",
            "content_type": "",
            "request_parameters": {k: v for k, v in params.items() if k != "serviceKey"},
            "data": {},
            "error": repr(exc),
        }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def response_body(payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("data", {}).get("response", {})
    body = response.get("body", {}) if isinstance(response, dict) else {}
    return body if isinstance(body, dict) else {}


def response_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = response_body(payload)
    items = body.get("items", {})
    if isinstance(items, dict):
        item = items.get("item", [])
        if isinstance(item, dict):
            return [item]
        if isinstance(item, list):
            return [x for x in item if isinstance(x, dict)]
    return []


def parse_day(x: Any) -> pd.Timestamp | None:
    s = str(x or "").strip()
    if len(s) == 8 and s.isdigit():
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    return None


def parse_float(x: Any) -> float:
    try:
        s = str(x or "").replace(",", "").strip()
        return float(s) if s else 0.0
    except Exception:
        return 0.0


def use_group(name: str) -> str:
    name = str(name or "").strip()
    if "주택" in name:
        return "주거"
    if any(k in name for k in ["근린", "판매", "업무"]):
        return "상업·업무"
    if any(k in name for k in ["공장", "창고", "위험물"]):
        return "산업·창고"
    if any(k in name for k in ["교육", "의료", "복지", "수련"]):
        return "공공·사회서비스"
    if any(k in name for k in ["운수", "숙박", "위락", "관광"]):
        return "숙박·운수·여가"
    return "기타"


def normalize_name(name: str) -> str:
    return str(name).replace(" ", "").strip()


def target_legal_dongs(limit_cities: int | None, priority_stage: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    priority = pd.read_csv(PRIORITY)
    if priority_stage:
        priority = priority[priority["collection_priority"].eq(priority_stage)].copy()
    priority = priority.sort_values("priority_rank")
    if limit_cities:
        priority = priority.head(limit_cities).copy()
    priority["norm_city"] = priority["city"].map(normalize_name)

    legal = read_csv_fallback(LEGAL)
    legal["norm_city"] = legal["sigungu_name"].map(normalize_name)
    legal["request_key"] = legal["request_key"].astype(str)
    # Prefer exact province+sigungu matches.  If source province naming is
    # historical/merged, fall back to sigungu-only matches only when that name is
    # unique in the legal universe.
    exact = legal.merge(
        priority[["province_full", "city", "norm_city", "priority_rank", "collection_priority"]],
        left_on=["sido_name", "norm_city"],
        right_on=["province_full", "norm_city"],
        how="inner",
    )
    matched_keys = set(zip(exact["priority_rank"], exact["request_key"]))
    name_counts = legal.groupby("norm_city")["sido_name"].nunique()
    unmatched_priority = priority[~priority["priority_rank"].isin(exact["priority_rank"].unique())].copy()
    fallback_parts = []
    for row in unmatched_priority.itertuples(index=False):
        if int(name_counts.get(row.norm_city, 0)) == 1:
            part = legal[legal["norm_city"].eq(row.norm_city)].copy()
            part["province_full"] = row.province_full
            part["city"] = row.city
            part["priority_rank"] = row.priority_rank
            part["collection_priority"] = row.collection_priority
            fallback_parts.append(part)
    fallback = pd.concat(fallback_parts, ignore_index=True) if fallback_parts else pd.DataFrame(columns=exact.columns)
    out = pd.concat([exact, fallback], ignore_index=True, sort=False)
    if not out.empty:
        out = out.drop_duplicates(["priority_rank", "request_key"])
    return out, priority


def collect(args: argparse.Namespace) -> None:
    targets, selected_priority = target_legal_dongs(args.limit_cities, args.priority_stage)
    tag = args.output_tag
    summary_path = OUT / f"buildinghub_priority_collection_plan_{tag}.csv"
    plan = (
        targets.groupby(["priority_rank", "collection_priority", "province_full", "city"], as_index=False)
        .agg(legal_dong_requests=("request_key", "nunique"))
        .sort_values("priority_rank")
    )
    plan.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"selected_cities={len(selected_priority)} legal_dong_requests={len(targets)} plan={summary_path}")
    if args.dry_run:
        return

    key = data_go_key()
    rows: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    request_count = 0
    for i, target in enumerate(targets.itertuples(index=False), start=1):
        if args.max_legal_dongs and i > args.max_legal_dongs:
            break
        sigungu = str(target.sigungu_cd)
        bjdong = str(target.bjdong_cd).zfill(5)
        base = {"serviceKey": key, "_type": "json", "numOfRows": args.num_rows, "sigunguCd": sigungu, "bjdongCd": bjdong}
        first = request_page({**base, "pageNo": 1}, tag, args.timeout, args.refresh)
        request_count += 1
        body = response_body(first)
        total = int(body.get("totalCount") or 0)
        pages = max(1, (total + args.num_rows - 1) // args.num_rows)
        payloads = [first]
        for page in range(2, pages + 1):
            if args.max_pages_per_legal_dong and page > args.max_pages_per_legal_dong:
                break
            payloads.append(request_page({**base, "pageNo": page}, tag, args.timeout, args.refresh))
            request_count += 1
            time.sleep(args.sleep)
        got = 0
        for payload in payloads:
            for item in response_items(payload):
                got += 1
                main_name = item.get("mainPurpsCdNm", "")
                rows.append(
                    {
                        "priority_rank": target.priority_rank,
                        "collection_priority": target.collection_priority,
                        "province_full": target.province_full,
                        "city": target.city,
                        "sigungu_cd": sigungu,
                        "bjdong_cd": bjdong,
                        "legal_dong_name": getattr(target, "bjdong_name", ""),
                        "permit_register_pk": item.get("mgmPmsrgstPk", ""),
                        "building_register_pk": item.get("mgmBldrgstPk", ""),
                        "main_purpose_name": main_name,
                        "use_group": use_group(main_name),
                        "total_floor_area": parse_float(item.get("totArea")),
                        "site_area": parse_float(item.get("platArea")),
                        "permit_date": parse_day(item.get("archPmsDay")),
                        "start_date": parse_day(item.get("realStcnsDay")),
                        "approval_date": parse_day(item.get("useAprDay")),
                        "created_at": parse_day(item.get("crtnDay")),
                    }
                )
        manifest.append(
            {
                "priority_rank": target.priority_rank,
                "province_full": target.province_full,
                "city": target.city,
                "sigungu_cd": sigungu,
                "bjdong_cd": bjdong,
                "total_count": total,
                "requested_pages": len(payloads),
                "expected_pages": pages,
                "received_rows": got,
                "error": first.get("error", ""),
            }
        )
        if i % args.progress_every == 0:
            print(f"legal_dongs={i}/{len(targets)} requests={request_count} rows={len(rows)}", flush=True)
        time.sleep(args.sleep)

    events = pd.DataFrame(rows)
    manifest = pd.DataFrame(manifest)
    event_path = PROCESSED / f"buildinghub_priority_events_{tag}.csv"
    manifest_path = PROCESSED / f"buildinghub_priority_events_manifest_{tag}.csv"
    events.to_csv(event_path, index=False, encoding="utf-8-sig")
    manifest.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    print(f"wrote {event_path}")
    print(f"wrote {manifest_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-cities", type=int, default=1)
    parser.add_argument("--priority-stage", default=None)
    parser.add_argument("--output-tag", default="construction_priority_top")
    parser.add_argument("--num-rows", type=int, default=1000)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--sleep", type=float, default=0.12)
    parser.add_argument("--max-legal-dongs", type=int, default=None)
    parser.add_argument("--max-pages-per-legal-dong", type=int, default=None)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


def main() -> None:
    collect(parse_args())


if __name__ == "__main__":
    main()
