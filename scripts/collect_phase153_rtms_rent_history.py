#!/usr/bin/env python3
"""Collect MOLIT rent RTMS rows for Phase153.

Default collection is intentionally conservative: only APIs that are confirmed
usable with the current DATA_GO_KR key are collected.  Service-key values are
never written to stdout or manifests.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import ssl

import pandas as pd

from kosis_common import load_env


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase153_rtms_rent_history"
OUT = ROOT / "data" / "processed" / "phase153_rtms_rent_history"

APIS = {
    "apt_rent": {
        "source_id": "molit_apt_rent_15126474",
        "source_name": "국토교통부_아파트 전월세 실거래가 자료",
        "portal_url": "https://www.data.go.kr/data/15126474/openapi.do",
        "endpoint": "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
        "asset_name_field": "aptNm",
        "area_field": "excluUseAr",
        "asset_type": "아파트",
    },
    "offi_rent": {
        "source_id": "molit_officetel_rent_15126475",
        "source_name": "국토교통부_오피스텔 전월세 실거래가 자료",
        "portal_url": "https://www.data.go.kr/data/15126475/openapi.do",
        "endpoint": "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent",
        "asset_name_field": "offiNm",
        "area_field": "excluUseAr",
        "asset_type": "오피스텔",
    },
    "single_multi_rent": {
        "source_id": "molit_single_multi_rent_15126472",
        "source_name": "국토교통부_단독/다가구 전월세 실거래가 자료",
        "portal_url": "https://www.data.go.kr/data/15126472/openapi.do",
        "endpoint": "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent",
        "asset_name_field": "",
        "area_field": "totalFloorAr",
        "asset_type": "단독/다가구",
    },
}

TARGET_SIGUNGU = {
    "41281": ("고양시", "덕양구"),
    "41285": ("고양시", "일산동구"),
    "41287": ("고양시", "일산서구"),
    "47111": ("포항시", "남구"),
    "47113": ("포항시", "북구"),
}


def env_keys() -> list[tuple[str, str, str]]:
    env = load_env()
    keys: list[tuple[str, str, str]] = []
    if env.get("DATA_GO_KR_ENCODING"):
        keys.append(("DATA_GO_KR_ENCODING", str(env["DATA_GO_KR_ENCODING"]), "as_is"))
    if env.get("DATA_GO_KR_DECODING"):
        keys.append(("DATA_GO_KR_DECODING", str(env["DATA_GO_KR_DECODING"]), "urlencode"))
    return keys


def build_url(endpoint: str, params: dict[str, Any], key: str, mode: str) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    if mode == "as_is":
        q = urllib.parse.urlencode(clean)
        return f"{endpoint}?{q}&serviceKey={key}"
    clean["serviceKey"] = key
    return f"{endpoint}?{urllib.parse.urlencode(clean)}"


def curl_xml(url: str, max_time: int = 30) -> tuple[int, float, bytes, str]:
    if "RTMSDataSvcAptRent" in url or "RTMSDataSvcOffiRent" in url or "RTMSDataSvcSHRent" in url:
        t0 = time.time()
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/xml"})
            with urlopen(req, timeout=max_time, context=ssl._create_unverified_context()) as resp:
                return int(resp.status), time.time() - t0, resp.read(), ""
        except HTTPError as exc:
            return int(exc.code), time.time() - t0, exc.read(), f"HTTPError {exc.code}"
        except URLError as exc:
            return 0, time.time() - t0, b"", f"URLError {str(exc.reason)[:200]}"
        except Exception as exc:
            return 0, time.time() - t0, b"", f"{type(exc).__name__}: {str(exc)[:200]}"

    t0 = time.time()
    cp = subprocess.run(
        [
            "curl",
            "-sS",
            "-k",
            "-L",
            "--connect-timeout",
            "8",
            "--max-time",
            str(max_time),
            "-A",
            "Mozilla/5.0",
            "-H",
            "Accept: application/xml",
            "-w",
            "\n__CURL__ http=%{http_code} time=%{time_total} size=%{size_download}\n",
            url,
        ],
        capture_output=True,
    )
    elapsed = time.time() - t0
    stdout = cp.stdout
    marker = b"\n__CURL__ "
    body = stdout.split(marker)[0] if marker in stdout else stdout
    status = 0
    match = re.search(rb"http=(\d+)", stdout)
    if match:
        status = int(match.group(1))
    err = cp.stderr.decode("utf-8", errors="replace")[:200]
    if cp.returncode != 0:
        err = f"curl_return={cp.returncode}; {err}"
    return status, elapsed, body, err


def parse_xml(body: bytes) -> tuple[str, str, int, list[dict[str, str]]]:
    try:
        root = ET.fromstring(body)
    except Exception as exc:
        return "", f"xml_parse_failed:{exc}", 0, []
    code = root.findtext(".//resultCode") or ""
    msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg") or ""
    total = int(float(root.findtext(".//totalCount") or 0))
    rows = [{child.tag: (child.text or "").strip() for child in item} for item in root.findall(".//item")]
    return code, msg, total, rows


def number(text: str) -> float:
    return float(re.sub(r"[^0-9.]", "", str(text or "")) or 0.0)


def select_key(api: dict[str, str]) -> tuple[str, str, str, list[dict[str, object]]]:
    attempts: list[dict[str, object]] = []
    params = {"LAWD_CD": "41281", "DEAL_YMD": "202301", "pageNo": 1, "numOfRows": 5}
    for key_name, key, mode in env_keys():
        status, elapsed, body, err = curl_xml(build_url(api["endpoint"], params, key, mode))
        code, msg, total, rows = parse_xml(body)
        attempts.append(
            {
                "source_id": api["source_id"],
                "key_slot": key_name,
                "key_mode": mode,
                "http_status": status,
                "elapsed_sec": round(elapsed, 3),
                "result_code": code,
                "result_msg": msg,
                "total_count": total,
                "item_count": len(rows),
                "error": err,
            }
        )
        if status == 200 and code == "000":
            return key_name, key, mode, attempts
    return "", "", "", attempts


def collect_one(api_key: str, years: list[int], refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    api = APIS[api_key]
    key_name, key, mode, probe = select_key(api)
    if not key:
        return pd.DataFrame(probe), pd.DataFrame(), pd.DataFrame()

    calls: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    for lawd, (city, gu) in TARGET_SIGUNGU.items():
        for year in years:
            for month in range(1, 13):
                period = f"{year}{month:02d}"
                page = 1
                while True:
                    cache = RAW / api_key / f"rtms_{api_key}_{lawd}_{period}_p{page}.xml"
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    if cache.exists() and not refresh:
                        body = cache.read_bytes()
                        status = 200
                        elapsed = 0.0
                        err = ""
                    else:
                        params = {"LAWD_CD": lawd, "DEAL_YMD": period, "pageNo": page, "numOfRows": 1000}
                        status, elapsed, body, err = curl_xml(build_url(api["endpoint"], params, key, mode))
                        cache.write_bytes(body)
                    code, msg, total_count, items = parse_xml(body)
                    calls.append(
                        {
                            "source_id": api["source_id"],
                            "source_name": api["source_name"],
                            "portal_url": api["portal_url"],
                            "endpoint_host": api["endpoint"].replace("https://", ""),
                            "key_slot_used": key_name,
                            "key_mode": mode,
                            "lawd_cd": lawd,
                            "city": city,
                            "general_gu": gu,
                            "period": period,
                            "page": page,
                            "http_status": status,
                            "elapsed_sec": round(elapsed, 3),
                            "result_code": code,
                            "result_msg": msg,
                            "total_count": total_count,
                            "item_count": len(items),
                            "local_path": str(cache.relative_to(ROOT)),
                            "error": err,
                        }
                    )
                    for item in items:
                        rows.append(
                            {
                                "source_id": api["source_id"],
                                "source_name": api["source_name"],
                                "asset_type": api["asset_type"],
                                "city": city,
                                "general_gu": gu,
                                "lawd_cd": lawd,
                                "period": period,
                                "legal_dong": item.get("umdNm", ""),
                                "sgg_name": item.get("sggNm", ""),
                                "asset_name": item.get(api["asset_name_field"], "") if api["asset_name_field"] else "",
                                "deal_year": item.get("dealYear", ""),
                                "deal_month": item.get("dealMonth", ""),
                                "deal_day": item.get("dealDay", ""),
                                "deposit_10k_krw": number(item.get("deposit", "")),
                                "monthly_rent_10k_krw": number(item.get("monthlyRent", "")),
                                "area_sqm": number(item.get(api["area_field"], "")),
                                "floor": item.get("floor", ""),
                                "build_year": item.get("buildYear", ""),
                                "contract_term": item.get("contractTerm", ""),
                                "contract_type": item.get("contractType", ""),
                                "renewal_right_used": item.get("useRRRight", ""),
                                "pre_deposit_10k_krw": number(item.get("preDeposit", "")),
                                "pre_monthly_rent_10k_krw": number(item.get("preMonthlyRent", "")),
                                "source_url": api["portal_url"],
                                "source_vintage_note": "계약월 기준 회고 수집. 행별 공표일자는 별도 제공되지 않아 strict 속보에는 보수적 공표시차 가정 필요.",
                            }
                        )
                    if code != "000":
                        break
                    if page * 1000 >= total_count:
                        break
                    page += 1

    return pd.DataFrame(probe), pd.DataFrame(calls), pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apis", nargs="+", default=["apt_rent"], choices=sorted(APIS))
    parser.add_argument("--years", nargs="+", type=int, default=[2020, 2021, 2022, 2023])
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    all_probe, all_calls, all_rows = [], [], []
    for api_key in args.apis:
        probe, calls, rows = collect_one(api_key, args.years, args.refresh)
        all_probe.append(probe)
        if not calls.empty:
            all_calls.append(calls)
        if not rows.empty:
            all_rows.append(rows)
        print(f"{api_key}: probe={len(probe)} calls={len(calls)} rows={len(rows)}")

    probe_df = pd.concat(all_probe, ignore_index=True) if all_probe else pd.DataFrame()
    calls_df = pd.concat(all_calls, ignore_index=True) if all_calls else pd.DataFrame()
    rows_df = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    probe_df.to_csv(OUT / "phase153_rtms_rent_key_probe.csv", index=False, encoding="utf-8-sig")
    calls_df.to_csv(OUT / "phase153_rtms_rent_call_manifest.csv", index=False, encoding="utf-8-sig")
    rows_df.to_csv(OUT / "phase153_rtms_rent_rows.csv", index=False, encoding="utf-8-sig")

    if rows_df.empty:
        monthly = pd.DataFrame()
    else:
        monthly = rows_df.groupby(["source_id", "asset_type", "city", "general_gu", "period"], as_index=False).agg(
            rent_contract_count=("deposit_10k_krw", "size"),
            deposit_10k_krw=("deposit_10k_krw", "sum"),
            monthly_rent_10k_krw=("monthly_rent_10k_krw", "sum"),
            area_sqm=("area_sqm", "sum"),
        )
    monthly.to_csv(OUT / "phase153_rtms_rent_gu_monthly.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "phase": "phase153_rtms_rent_history",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_apis": args.apis,
        "years": args.years,
        "target_sigungu": TARGET_SIGUNGU,
        "collected_rows": int(len(rows_df)),
        "call_count": int(len(calls_df)),
        "usable_sources": sorted(rows_df["source_id"].dropna().unique().tolist()) if not rows_df.empty else [],
        "strict_asof_limit": "행별 공표일자/확정일자 공개시점이 없으므로 Q+1개월 속보에는 보수적 lag 또는 별도 공표시차 감사 필요.",
    }
    (OUT / "phase153_rtms_rent_collection_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ok = int(calls_df["result_code"].astype(str).eq("000").sum()) if not calls_df.empty else 0
    print(f"total_calls={len(calls_df)} ok_calls={ok} total_rows={len(rows_df)}")


if __name__ == "__main__":
    main()
