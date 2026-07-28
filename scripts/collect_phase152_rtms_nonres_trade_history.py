#!/usr/bin/env python3
"""Collect MOLIT non-residential real-estate trade rows for Phase152.

The source is the official data.go.kr OpenAPI:

* 국토교통부_상업업무용 부동산 매매 실거래가 자료
* https://www.data.go.kr/data/15126463/openapi.do

This collector deliberately records source/vintage metadata and never prints
service-key values.  The output is an activity indicator for real-estate
transaction/service split diagnostics, not a direct GVA total.
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

import pandas as pd

from kosis_common import load_env


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase152_rtms_nonres_trade_history"
OUT = ROOT / "data" / "processed" / "phase152_rtms_nonres_trade_history"
ENDPOINT = "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
PORTAL_URL = "https://www.data.go.kr/data/15126463/openapi.do"
SOURCE_NAME = "국토교통부_상업업무용 부동산 매매 실거래가 자료"
SOURCE_DATASET_REGISTERED_DATE = "2024-01-25"
SOURCE_DATASET_MODIFIED_DATE = "2026-07-22"
SOURCE_UPDATE_CYCLE = "실시간"

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


def build_url(params: dict[str, Any], key: str, mode: str) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    if mode == "as_is":
        q = urllib.parse.urlencode(clean)
        return f"{ENDPOINT}?{q}&serviceKey={key}"
    clean["serviceKey"] = key
    return f"{ENDPOINT}?{urllib.parse.urlencode(clean)}"


def curl_xml(url: str, max_time: int = 30) -> tuple[int, float, bytes, str]:
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


def select_key() -> tuple[str, str, str, list[dict[str, object]]]:
    attempts: list[dict[str, object]] = []
    params = {"LAWD_CD": "41281", "DEAL_YMD": "202301", "pageNo": 1, "numOfRows": 10}
    for key_name, key, mode in env_keys():
        status, elapsed, body, err = curl_xml(build_url(params, key, mode))
        code, msg, total, rows = parse_xml(body)
        attempts.append(
            {
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
    raise SystemExit("No working DATA_GO_KR key for non-residential RTMS. Probe attempts are kept without key values.")


def number(text: str) -> float:
    return float(re.sub(r"[^0-9.]", "", str(text or "")) or 0.0)


def collect(years: list[int], refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    key_name, key, mode, probe_attempts = select_key()
    calls: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []

    for lawd, (city, gu) in TARGET_SIGUNGU.items():
        for year in years:
            for month in range(1, 13):
                period = f"{year}{month:02d}"
                page = 1
                while True:
                    cache = RAW / f"rtms_nonres_trade_{lawd}_{period}_p{page}.xml"
                    if cache.exists() and not refresh:
                        body = cache.read_bytes()
                        status = 200
                        elapsed = 0.0
                        err = ""
                    else:
                        params = {
                            "LAWD_CD": lawd,
                            "DEAL_YMD": period,
                            "pageNo": page,
                            "numOfRows": 1000,
                        }
                        status, elapsed, body, err = curl_xml(build_url(params, key, mode))
                        cache.write_bytes(body)
                    code, msg, total_count, items = parse_xml(body)
                    calls.append(
                        {
                            "source_id": "molit_nonres_trade_15126463",
                            "source_name": SOURCE_NAME,
                            "portal_url": PORTAL_URL,
                            "endpoint_host": "apis.data.go.kr/1613000/RTMSDataSvcNrgTrade",
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
                                "city": city,
                                "general_gu": gu,
                                "lawd_cd": lawd,
                                "period": period,
                                "legal_dong": item.get("umdNm", ""),
                                "sgg_name": item.get("sggNm", ""),
                                "building_type": item.get("buildingType", ""),
                                "building_use": item.get("buildingUse", ""),
                                "land_use": item.get("landUse", ""),
                                "deal_year": item.get("dealYear", ""),
                                "deal_month": item.get("dealMonth", ""),
                                "deal_day": item.get("dealDay", ""),
                                "deal_amount_10k_krw": number(item.get("dealAmount", "")),
                                "plottage_area_sqm": number(item.get("plottageAr", "")),
                                "building_area_sqm": number(item.get("buildingAr", "")),
                                "floor": item.get("floor", ""),
                                "build_year": item.get("buildYear", ""),
                                "dealing_type": item.get("dealingGbn", ""),
                                "agent_sigungu": item.get("estateAgentSggNm", ""),
                                "seller_type": item.get("slerGbn", ""),
                                "buyer_type": item.get("buyerGbn", ""),
                                "cancel_type": item.get("cdealType", ""),
                                "cancel_day": item.get("cdealDay", ""),
                                "source_dataset_registered_date": SOURCE_DATASET_REGISTERED_DATE,
                                "source_dataset_modified_date": SOURCE_DATASET_MODIFIED_DATE,
                                "source_dataset_update_cycle": SOURCE_UPDATE_CYCLE,
                                "source_vintage_note": "계약년월 기준 회고 수집. 행별 공표일자는 별도 제공되지 않아 strict 속보에는 보수적 공표시차 가정 필요.",
                                "source_url": PORTAL_URL,
                            }
                        )
                    if code != "000":
                        break
                    if page * 1000 >= total_count:
                        break
                    page += 1

    probe_df = pd.DataFrame(probe_attempts)
    calls_df = pd.DataFrame(calls)
    rows_df = pd.DataFrame(rows)
    probe_df.to_csv(OUT / "phase152_nonres_rtms_key_probe.csv", index=False, encoding="utf-8-sig")
    calls_df.to_csv(OUT / "phase152_nonres_rtms_call_manifest.csv", index=False, encoding="utf-8-sig")
    rows_df.to_csv(OUT / "phase152_nonres_rtms_trade_rows.csv", index=False, encoding="utf-8-sig")

    if rows_df.empty:
        monthly = pd.DataFrame()
    else:
        monthly = rows_df.groupby(["city", "general_gu", "period"], as_index=False).agg(
            deal_count=("deal_amount_10k_krw", "size"),
            deal_amount_10k_krw=("deal_amount_10k_krw", "sum"),
            building_area_sqm=("building_area_sqm", "sum"),
            plottage_area_sqm=("plottage_area_sqm", "sum"),
        )
    monthly.to_csv(OUT / "phase152_nonres_rtms_trade_gu_monthly.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "phase": "phase152_rtms_nonres_trade_history",
        "source_name": SOURCE_NAME,
        "source_url": PORTAL_URL,
        "endpoint": "RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade",
        "source_dataset_registered_date": SOURCE_DATASET_REGISTERED_DATE,
        "source_dataset_modified_date": SOURCE_DATASET_MODIFIED_DATE,
        "source_update_cycle": SOURCE_UPDATE_CYCLE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "years": years,
        "target_sigungu": TARGET_SIGUNGU,
        "raw_rows": int(len(rows_df)),
        "call_count": int(len(calls_df)),
        "key_slots_recorded_without_key_values": sorted(set(calls_df["key_slot_used"].astype(str))) if not calls_df.empty else [],
        "strict_asof_limit": "행별 공표일자/등기일자가 없어 Q+1개월 속보에는 직접 채택하지 않고 보수적 lag 또는 정밀화 구조자료로 우선 사용.",
    }
    (OUT / "phase152_nonres_rtms_collection_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return probe_df, calls_df, rows_df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, default=[2020, 2021, 2022, 2023])
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    probe, calls, rows = collect(args.years, args.refresh)
    print(f"probe_rows={len(probe)} calls={len(calls)} trade_rows={len(rows)}")
    if not calls.empty:
        ok = int(calls["result_code"].astype(str).eq("000").sum())
        print(f"ok_calls={ok} failed_calls={len(calls)-ok}")


if __name__ == "__main__":
    main()
