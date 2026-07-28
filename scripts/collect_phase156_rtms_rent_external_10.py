#!/usr/bin/env python3
"""Collect MOLIT RTMS rent rows for the Phase156 external 10-sigungu audit.

The Phase153 collector is fixed to Goyang/Pohang.  This script keeps the same
RTMS parsing and source metadata, but builds the target list from the Phase106
external sample and an official legal-dong-code file.  It intentionally does
not print service keys.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import time
import urllib.parse
import zipfile
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
RAW = ROOT / "data" / "raw" / "phase156_rtms_rent_external_10"
OUT = ROOT / "data" / "processed" / "phase156_rtms_rent_external_10"
SAMPLE = ROOT / "data" / "processed" / "phase106_generalization_pilot_10_sigungu" / "phase106_sample_10_sigungu.csv"
BJD_ZIP = ROOT / "data" / "raw" / "buildinghub" / "bjdcode.zip"

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

# RTMS OpenAPI currently expects the active legal-dong 5-digit code even when
# querying 2020~2023 deal months.  Some Phase106/KOSIS regions were renamed by
# later administrative changes, so keep KOSIS area_code for actual matching and
# use these current LAWD_CD values only for RTMS collection.
RTMS_LAWD_OVERRIDES = {
    ("광주광역시", "북구"): ("12300", "전남광주통합특별시 북구", "현행RTMS코드"),
    ("인천광역시", "동구"): ("28125", "인천광역시 제물포구", "현행RTMS코드"),
    ("전라남도", "강진군"): ("12780", "전남광주통합특별시 강진군", "현행RTMS코드"),
    ("전라남도", "영암군"): ("12800", "전남광주통합특별시 영암군", "현행RTMS코드"),
    ("전라남도", "함평군"): ("12820", "전남광주통합특별시 함평군", "현행RTMS코드"),
    ("전북특별자치도", "익산시"): ("52140", "전북특별자치도 익산시", "현행RTMS코드"),
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


def fetch_xml(url: str, max_time: int = 30) -> tuple[int, float, bytes, str]:
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


def select_key(api: dict[str, str], probe_lawd: str) -> tuple[str, str, str, list[dict[str, object]]]:
    attempts: list[dict[str, object]] = []
    params = {"LAWD_CD": probe_lawd, "DEAL_YMD": "202301", "pageNo": 1, "numOfRows": 5}
    for key_name, key, mode in env_keys():
        status, elapsed, body, err = fetch_xml(build_url(api["endpoint"], params, key, mode))
        code, msg, total, rows = parse_xml(body)
        attempts.append(
            {
                "source_id": api["source_id"],
                "key_slot": key_name,
                "key_mode": mode,
                "probe_lawd_cd": probe_lawd,
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


def read_legal_dong_sgg() -> pd.DataFrame:
    with zipfile.ZipFile(BJD_ZIP) as zf:
        name = zf.namelist()[0]
        data = zf.read(name)
    text = data.decode("cp949")
    df = pd.read_csv(io.StringIO(text), sep="\t", dtype={"법정동코드": str})
    df = df.copy()
    df["lawd_cd"] = df["법정동코드"].str.slice(0, 5)
    df["name"] = df["법정동명"].astype(str)
    # 시군구 본청 행: 10자리 중 뒤 5자리가 00000이고 명칭 토큰이 2~3개.
    sgg = df[df["법정동코드"].str.endswith("00000")].copy()
    sgg["token_count"] = sgg["name"].str.split().str.len()
    sgg = sgg[sgg["token_count"].between(2, 3)].copy()
    sgg["source_region"] = sgg["name"].str.split().str[0]
    sgg["c1_nm"] = sgg["name"].str.split().str[-1]
    return sgg[["lawd_cd", "name", "source_region", "c1_nm", "폐지여부"]].drop_duplicates("lawd_cd")


def normalize_region(name: str) -> str:
    alias = {
        "전북특별자치도": "전북특별자치도",
        "전라북도": "전북특별자치도",
    }
    return alias.get(str(name), str(name))


def build_targets() -> pd.DataFrame:
    sample = pd.read_csv(SAMPLE, dtype={"area_code": str})
    sample["source_region_norm"] = sample["source_region"].map(normalize_region)
    sgg = read_legal_dong_sgg()
    sgg["source_region_norm"] = sgg["source_region"].map(normalize_region)
    targets = sample.merge(sgg, on=["source_region_norm", "c1_nm"], how="left", suffixes=("_kosis", "_bjd"))
    missing = targets[targets["lawd_cd"].isna()]
    if not missing.empty:
        display_cols = [c for c in ["source_region_kosis", "c1_nm", "area_code"] if c in missing.columns]
        raise SystemExit("법정동코드 매핑 실패:\n" + missing[display_cols].to_string(index=False))
    targets["source_region"] = targets["source_region_kosis"].astype(str)
    targets["city"] = targets["source_region"].astype(str)
    targets["general_gu"] = targets["c1_nm"].astype(str)
    # First select a deterministic name match.  This code is retained as
    # historical metadata; RTMS collection codes can be overridden below.
    targets["_name_priority"] = targets["폐지여부"].map({"존재": 0, "폐지": 1}).fillna(2)
    targets = targets.sort_values(["area_code", "c1_nm", "_name_priority", "lawd_cd"]).drop_duplicates(
        ["area_code", "c1_nm"],
        keep="first",
    )
    targets["rtms_lawd_cd"] = targets["lawd_cd"]
    targets["rtms_lawd_name"] = targets["name"]
    targets["rtms_code_policy"] = targets["폐지여부"].map(lambda x: "법정동원본명칭매핑")
    for idx, row in targets.iterrows():
        override = RTMS_LAWD_OVERRIDES.get((row["source_region"], row["c1_nm"]))
        if override:
            targets.at[idx, "rtms_lawd_cd"] = override[0]
            targets.at[idx, "rtms_lawd_name"] = override[1]
            targets.at[idx, "rtms_code_policy"] = override[2]
    return targets[
        [
            "source_region",
            "area_code",
            "c1_nm",
            "actual_sum_eok",
            "lawd_cd",
            "name",
            "폐지여부",
            "rtms_lawd_cd",
            "rtms_lawd_name",
            "rtms_code_policy",
            "city",
            "general_gu",
        ]
    ].sort_values(["source_region", "c1_nm"])


def collect_one(api_key: str, targets: pd.DataFrame, years: list[int], refresh: bool, dry_run: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    api = APIS[api_key]
    probe_lawd = str(targets["lawd_cd"].iloc[0])
    key_name, key, mode, probe = select_key(api, probe_lawd)
    if not key:
        return pd.DataFrame(probe), pd.DataFrame(), pd.DataFrame()
    if dry_run:
        return pd.DataFrame(probe), pd.DataFrame(), pd.DataFrame()

    calls: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    for target in targets.to_dict("records"):
        lawd = str(target["rtms_lawd_cd"])
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
                        status, elapsed, body, err = fetch_xml(build_url(api["endpoint"], params, key, mode))
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
                            "kosis_area_code": target["area_code"],
                            "lawd_cd": lawd,
                            "kosis_lawd_cd": target["lawd_cd"],
                            "source_region": target["source_region"],
                            "sigungu_name": target["c1_nm"],
                            "legal_sgg_name": target["rtms_lawd_name"],
                            "rtms_code_policy": target["rtms_code_policy"],
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
                                "kosis_area_code": target["area_code"],
                                "lawd_cd": lawd,
                                "kosis_lawd_cd": target["lawd_cd"],
                                "source_region": target["source_region"],
                                "sigungu_name": target["c1_nm"],
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
                    if code != "000" or page * 1000 >= total_count:
                        break
                    page += 1
    return pd.DataFrame(probe), pd.DataFrame(calls), pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apis", nargs="+", default=sorted(APIS), choices=sorted(APIS))
    parser.add_argument("--years", nargs="+", type=int, default=[2020, 2021, 2022, 2023])
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    targets = build_targets()
    targets.to_csv(OUT / "phase156_external_10_lawd_crosswalk.csv", index=False, encoding="utf-8-sig")
    all_probe, all_calls, all_rows = [], [], []
    for api_key in args.apis:
        probe, calls, rows = collect_one(api_key, targets, args.years, args.refresh, args.dry_run)
        all_probe.append(probe)
        if not calls.empty:
            all_calls.append(calls)
        if not rows.empty:
            all_rows.append(rows)
        print(f"{api_key}: probe={len(probe)} calls={len(calls)} rows={len(rows)}")

    probe_df = pd.concat(all_probe, ignore_index=True) if all_probe else pd.DataFrame()
    calls_df = pd.concat(all_calls, ignore_index=True) if all_calls else pd.DataFrame()
    rows_df = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    probe_df.to_csv(OUT / "phase156_rtms_rent_key_probe.csv", index=False, encoding="utf-8-sig")
    calls_df.to_csv(OUT / "phase156_rtms_rent_call_manifest.csv", index=False, encoding="utf-8-sig")
    rows_df.to_csv(OUT / "phase156_rtms_rent_rows.csv", index=False, encoding="utf-8-sig")

    if rows_df.empty:
        monthly = pd.DataFrame()
    else:
        monthly = rows_df.groupby(
            ["source_id", "asset_type", "source_region", "sigungu_name", "kosis_area_code", "lawd_cd", "period"],
            as_index=False,
        ).agg(
            rent_contract_count=("deposit_10k_krw", "size"),
            deposit_10k_krw=("deposit_10k_krw", "sum"),
            monthly_rent_10k_krw=("monthly_rent_10k_krw", "sum"),
            area_sqm=("area_sqm", "sum"),
        )
    monthly.to_csv(OUT / "phase156_rtms_rent_sigungu_monthly.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "phase": "phase156_rtms_rent_external_10",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_apis": args.apis,
        "years": args.years,
        "sample_source": str(SAMPLE.relative_to(ROOT)),
        "legal_dong_source": str(BJD_ZIP.relative_to(ROOT)),
        "target_sigungu_count": int(len(targets)),
        "collected_rows": int(len(rows_df)),
        "call_count": int(len(calls_df)),
        "usable_sources": sorted(rows_df["source_id"].dropna().unique().tolist()) if not rows_df.empty else [],
        "strict_asof_limit": "행별 공표일자/확정일자 공개시점이 없으므로 Q+1개월 속보에는 보수적 lag 또는 별도 공표시차 감사 필요.",
    }
    (OUT / "phase156_rtms_rent_collection_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ok = int(calls_df["result_code"].astype(str).eq("000").sum()) if not calls_df.empty else 0
    print(f"target_sigungu={len(targets)} total_calls={len(calls_df)} ok_calls={ok} total_rows={len(rows_df)}")


if __name__ == "__main__":
    main()
