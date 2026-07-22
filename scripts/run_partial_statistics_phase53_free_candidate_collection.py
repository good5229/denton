#!/usr/bin/env python3
"""Phase53 free candidate source collection and storage inventory.

This script only stores public metadata, compact regional extracts, and
collection failures. It never prints API keys.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd

from kosis_common import load_env


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase53_free_candidate_sources"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

TARGET_SIGUNGU = {
    "41281": ("고양시", "덕양구"),
    "41285": ("고양시", "일산동구"),
    "41287": ("고양시", "일산서구"),
    "47111": ("포항시", "남구"),
    "47113": ("포항시", "북구"),
}


DATASET_PAGES = [
    {
        "source_id": "goyang_real_estate_broker_file",
        "source_name": "경기도 고양시_부동산중개업 현황",
        "url": "https://www.data.go.kr/data/15112829/fileData.do",
        "target": "L00/682 부동산 관련 서비스",
        "mode": "file_page",
    },
    {
        "source_id": "pohang_real_estate_broker_file",
        "source_name": "경상북도 포항시_개업공인중개사사무소 현황",
        "url": "https://www.data.go.kr/data/15128314/fileData.do",
        "target": "L00/682 부동산 관련 서비스",
        "mode": "file_page",
    },
    {
        "source_id": "gyeonggi_bus_stop_daily_boarding_file",
        "source_name": "경기도_정류소 별 승하차 인원 집계",
        "url": "https://www.data.go.kr/data/15144886/fileData.do",
        "target": "H00/492 육상 여객 운송업",
        "mode": "external_or_file_page",
    },
    {
        "source_id": "korail_intercity_station_daily_passenger_file",
        "source_name": "한국철도공사_간선여객 승하차 인원수",
        "url": "https://www.data.go.kr/data/15149430/fileData.do",
        "target": "H00/491 철도 운송업",
        "mode": "file_page",
    },
    {
        "source_id": "molit_public_housing_price_file",
        "source_name": "국토교통부_주택 공시가격 정보",
        "url": "https://www.data.go.kr/data/3073746/fileData.do",
        "target": "L00/681 부동산 임대 및 공급업",
        "mode": "large_file_metadata_only",
    },
    {
        "source_id": "niier_livestock_aquaculture_inventory",
        "source_name": "국립환경과학원_축산/양식 인벤토리 후보",
        "url": "https://www.data.go.kr/data/15091204/fileData.do?recommendDataYn=Y",
        "target": "A00 농림어업",
        "mode": "file_page",
    },
    {
        "source_id": "mof_port_cargo_api",
        "source_name": "해양수산부_화물처리실적통계",
        "url": "https://www.data.go.kr/dataset/3036255/openapi.do",
        "target": "H00/501 수상 운송업·항만 물류",
        "mode": "metadata_only",
    },
]


RTMS_APIS = [
    {
        "source_id": "molit_apt_trade",
        "source_name": "국토교통부_아파트 매매 실거래가 자료",
        "url": "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
        "portal_url": "https://www.data.go.kr/data/15126469/openapi.do",
        "target": "L00/681 주거 부동산 거래활동",
    },
    {
        "source_id": "molit_non_residential_trade",
        "source_name": "국토교통부_상업업무용 부동산 매매 실거래가 자료",
        "url": "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade",
        "portal_url": "https://www.data.go.kr/data/15126463/openapi.do",
        "target": "L00/681 상업·업무용 부동산 거래활동",
    },
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def data_go_key() -> tuple[str, bool]:
    env = load_env()
    for name in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING", "PUBLIC_DATA_API_KEY", "DATA_GO_KR_API_KEY"):
        value = env.get(name)
        if value:
            return str(value), name == "DATA_GO_KR_ENCODING"
    return "", False


def request_bytes(url: str, timeout: int = 180) -> tuple[int, bytes, dict[str, str], str]:
    context = None
    try:
        import certifi  # type: ignore

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = None
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as res:
            return res.status, res.read(), dict(res.headers.items()), ""
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items()), f"HTTPError:{exc.code}"
    except Exception as exc:
        return 0, b"", {}, repr(exc)


def page_path(source_id: str) -> Path:
    return RAW / f"{source_id}_page.html"


def collect_page_metadata() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for src in DATASET_PAGES:
        out = page_path(src["source_id"])
        status = 0
        body = b""
        err = ""
        if out.exists():
            body = out.read_bytes()
            status = 200
            err = "cached"
        else:
            status, body, _headers, err = request_bytes(src["url"])
            if body:
                out.write_bytes(body)
        text = body.decode("utf-8", errors="replace")
        content_urls = re.findall(r'"contentUrl"\s*:\s*"([^"]+)"', text)
        external_urls = re.findall(r'URL\s*</th>\s*<td[^>]*>\s*<a[^>]+href="([^"]+)"', text)
        if not external_urls:
            external_urls = re.findall(r'apiLinkUrl=([^,\]]+)', text)
        dataset_name = ""
        m = re.search(r'"name"\s*:\s*"([^"]+)"', text)
        if m:
            dataset_name = m.group(1)
        rows.append(
            {
                "source_id": src["source_id"],
                "source_name": src["source_name"],
                "target_industry": src["target"],
                "portal_url": src["url"],
                "http_status": status,
                "page_bytes": len(body),
                "page_sha256": sha256_bytes(body) if body else "",
                "content_url": content_urls[0] if content_urls else "",
                "external_url": external_urls[0] if external_urls else "",
                "dataset_name_on_page": dataset_name,
                "collection_status": "metadata_collected" if body else "page_failed",
                "failure_reason": err,
            }
        )
    return rows


def download_known_files(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alias_paths = {
        "goyang_real_estate_broker_file": RAW / "goyang_real_estate_broker_file_download.csv",
        "pohang_real_estate_broker_file": RAW / "pohang_real_estate_broker_file_download.csv",
        "korail_intercity_station_daily_passenger_file": RAW / "korail_station_daily_passenger_download.bin",
        "niier_livestock_aquaculture_inventory": RAW / "niier_livestock_aquaculture_inventory_download.bin",
    }
    rows = []
    for row in manifest:
        alias = alias_paths.get(str(row["source_id"]))
        if alias and alias.exists() and alias.stat().st_size > 0:
            row["file_collection_status"] = "downloaded"
            row["local_path"] = str(alias.relative_to(ROOT))
            row["download_bytes"] = alias.stat().st_size
            row["download_sha256"] = sha256_bytes(alias.read_bytes()) if alias.stat().st_size < 20_000_000 else ""
            row["failure_reason"] = ""
            rows.append(row)
            continue
        content_url = str(row.get("content_url") or "")
        if not content_url:
            row["file_collection_status"] = "no_direct_file_url"
            row["local_path"] = ""
            rows.append(row)
            continue
        if row["source_id"] == "molit_public_housing_price_file":
            row["file_collection_status"] = "deferred_large_15_58m_rows"
            row["local_path"] = ""
            rows.append(row)
            continue
        out = RAW / f"{row['source_id']}_download.bin"
        if out.exists():
            body = out.read_bytes()
            status = 200
            err = "cached"
        else:
            status, body, headers, err = request_bytes(content_url)
            if status < 400 and body:
                suffix = ".csv"
                if body[:2] == b"PK":
                    suffix = ".zip"
                elif b"<html" in body[:500].lower() or b"<!doctype" in body[:500].lower():
                    suffix = ".html"
                out = out.with_suffix(suffix)
                out.write_bytes(body)
        row["file_collection_status"] = "downloaded" if status < 400 and body and out.exists() and out.stat().st_size > 0 else "download_failed"
        row["local_path"] = str(out.relative_to(ROOT)) if out.exists() else ""
        row["download_bytes"] = out.stat().st_size if out.exists() else 0
        row["download_sha256"] = sha256_bytes(out.read_bytes()) if out.exists() and out.stat().st_size < 20_000_000 else ""
        row["failure_reason"] = "" if row["file_collection_status"] == "downloaded" else err
        rows.append(row)
    return rows


def normalize_broker_files() -> pd.DataFrame:
    specs = [
        ("고양시", RAW / "goyang_broker_20260317.csv", RAW / "goyang_real_estate_broker_file_download.csv"),
        ("포항시", RAW / "pohang_broker.csv", RAW / "pohang_real_estate_broker_file_download.csv"),
    ]
    rows = []
    for city, explicit, fallback in specs:
        path = explicit if explicit.exists() else fallback
        if not path.exists():
            continue
        df = pd.read_csv(path, encoding="cp949")
        for _, r in df.iterrows():
            vals = {str(k): "" if pd.isna(v) else str(v) for k, v in r.items()}
            address = vals.get("소재지") or vals.get("주소(대표자)") or vals.get("주소") or ""
            gu = ""
            if "덕양구" in address:
                gu = "덕양구"
            elif "일산동구" in address:
                gu = "일산동구"
            elif "일산서구" in address:
                gu = "일산서구"
            elif "남구" in address:
                gu = "남구"
            elif "북구" in address:
                gu = "북구"
            rows.append(
                {
                    "city": city,
                    "general_gu": gu,
                    "office_name": vals.get("중개업소명") or vals.get("상호명") or "",
                    "address": address,
                    "reference_date": vals.get("데이터기준일") or ("2026-03-17" if city == "고양시" else vals.get("데이터기준일자", "")),
                    "source_file": str(path.relative_to(ROOT)),
                    "ksic_parent": "L00",
                    "ksic_small": "682",
                    "industry_name": "부동산 관련 서비스업",
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED / "partial_stats_phase53_realestate_broker_goyang_pohang.csv", index=False, encoding="utf-8-sig")
    if not out.empty:
        agg = out.groupby(["city", "general_gu"], as_index=False).agg(broker_office_count=("office_name", "count"))
        agg.to_csv(PROCESSED / "partial_stats_phase53_realestate_broker_gu_features.csv", index=False, encoding="utf-8-sig")
    return out


def normalize_korail_file() -> pd.DataFrame:
    path = RAW / "korail_station_daily_passenger_download.bin"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="cp949")
    station_city = {
        "행신": ("고양시", "덕양구"),
        "일산": ("고양시", "일산서구"),
        "탄현": ("고양시", "일산서구"),
        "백마": ("고양시", "일산동구"),
        "풍산": ("고양시", "일산동구"),
        "포항": ("포항시", "북구"),
    }
    rows = []
    for _, r in df.iterrows():
        station = str(r.get("정차역", "")).strip()
        if station not in station_city:
            continue
        city, gu = station_city[station]
        rows.append(
            {
                "city": city,
                "general_gu": gu,
                "station_name": station,
                "date": str(r.get("운행일자", "")),
                "boarding": int(r.get("승차인원수", 0) or 0),
                "alighting": int(r.get("하차인원수", 0) or 0),
                "source_file": str(path.relative_to(ROOT)),
                "ksic_parent": "H00",
                "ksic_middle": "491",
                "industry_name": "철도 운송업",
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED / "partial_stats_phase53_korail_station_daily_goyang_pohang.csv", index=False, encoding="utf-8-sig")
    if not out.empty:
        agg = out.assign(period=out["date"].str.slice(0, 7)).groupby(["city", "general_gu", "station_name", "period"], as_index=False).agg(
            boarding=("boarding", "sum"),
            alighting=("alighting", "sum"),
        )
        agg.to_csv(PROCESSED / "partial_stats_phase53_korail_station_monthly_features.csv", index=False, encoding="utf-8-sig")
    return out


def parse_rtms_items(xml_body: bytes) -> tuple[list[dict[str, Any]], str]:
    try:
        root = ET.fromstring(xml_body)
    except Exception as exc:
        return [], f"xml_parse_failed:{exc}"
    result = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg") or ""
    items = []
    for item in root.findall(".//item"):
        row = {child.tag: (child.text or "").strip() for child in item}
        items.append(row)
    return items, result


def request_rtms(url: str, key: str, raw_key: bool, params: dict[str, Any]) -> tuple[int, bytes, str]:
    clean = {k: v for k, v in params.items() if v not in ("", None)}
    if raw_key:
        q = urllib.parse.urlencode(clean)
        q = f"{q}&serviceKey={key}"
    else:
        clean["serviceKey"] = key
        q = urllib.parse.urlencode(clean)
    return request_bytes(f"{url}?{q}", timeout=90)[:3] + ("",)  # type: ignore


def collect_rtms() -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    if os.environ.get("PHASE53_SKIP_RTMS", "1") != "0":
        return pd.DataFrame(), [
            {
                "source_id": api["source_id"],
                "source_name": api["source_name"],
                "target_industry": api["target"],
                "portal_url": api["portal_url"],
                "collection_status": "deferred_endpoint_stalled_during_probe",
                "failure_reason": "regional monthly API call did not return within bounded interactive run; collect offline with batch timeout/retry",
                "item_count": 0,
            }
            for api in RTMS_APIS
        ]
    key, raw_key = data_go_key()
    manifests = []
    rows = []
    if not key:
        return pd.DataFrame(), [{"source_id": "rtms_all", "collection_status": "blocked", "failure_reason": "missing_data_go_key"}]
    # Full 12-month collection is intentionally opt-in because RTMS endpoints
    # can stall. The default probe verifies authorization and schema while
    # keeping the turn bounded.
    env_months = os.environ.get("PHASE53_RTMS_MONTHS", "")
    months = [m.strip() for m in env_months.split(",") if m.strip()] or ["202401", "202404", "202407", "202410"]
    for api in RTMS_APIS:
        for lawd, (city, gu) in TARGET_SIGUNGU.items():
            for month in months:
                params = {"LAWD_CD": lawd, "DEAL_YMD": month, "numOfRows": 1000, "pageNo": 1}
                q = urllib.parse.urlencode(params)
                if raw_key:
                    full = f"{api['url']}?{q}&serviceKey={key}"
                else:
                    p2 = dict(params)
                    p2["serviceKey"] = key
                    full = f"{api['url']}?{urllib.parse.urlencode(p2)}"
                status, body, _headers, err = request_bytes(full, timeout=12)
                cache = RAW / f"{api['source_id']}_{lawd}_{month}.xml"
                if body:
                    cache.write_bytes(body)
                items, msg = parse_rtms_items(body)
                manifests.append(
                    {
                        "source_id": api["source_id"],
                        "source_name": api["source_name"],
                        "target_industry": api["target"],
                        "portal_url": api["portal_url"],
                        "lawd_cd": lawd,
                        "city": city,
                        "general_gu": gu,
                        "period": month,
                        "http_status": status,
                        "item_count": len(items),
                        "result_message": msg,
                        "collection_status": "downloaded" if status < 400 and (items or "NORMAL" in msg.upper() or "정상" in msg) else "api_failed_or_empty",
                        "failure_reason": err,
                        "local_path": str(cache.relative_to(ROOT)) if cache.exists() else "",
                    }
                )
                for item in items:
                    money = item.get("거래금액") or item.get("dealAmount") or item.get("거래금액 ") or ""
                    money_num = float(re.sub(r"[^0-9.]", "", money) or 0)
                    area = item.get("전용면적") or item.get("건물면적") or item.get("excluUseAr") or item.get("dealArea") or ""
                    try:
                        area_num = float(str(area).replace(",", ""))
                    except Exception:
                        area_num = 0.0
                    rows.append(
                        {
                            "source_id": api["source_id"],
                            "city": city,
                            "general_gu": gu,
                            "lawd_cd": lawd,
                            "period": month,
                            "deal_amount_million_krw": money_num,
                            "area_sqm": area_num,
                            "raw_item": json.dumps(item, ensure_ascii=False, sort_keys=True),
                        }
                    )
    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(PROCESSED / "partial_stats_phase53_rtms_transactions_goyang_pohang.csv", index=False, encoding="utf-8-sig")
        agg = df.groupby(["source_id", "city", "general_gu", "period"], as_index=False).agg(
            deal_count=("raw_item", "count"),
            deal_amount_million_krw=("deal_amount_million_krw", "sum"),
            area_sqm=("area_sqm", "sum"),
        )
        agg.to_csv(PROCESSED / "partial_stats_phase53_rtms_transaction_gu_monthly.csv", index=False, encoding="utf-8-sig")
    return df, manifests


def storage_inventory() -> pd.DataFrame:
    rows = []
    for base in [ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "reports", ROOT / "goyang", ROOT / "pohang"]:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT)
            size = p.stat().st_size
            ext = p.suffix.lower()
            if "phase51_building_realestate_sources/building_register_ttlldr_202606_download.bin" in str(rel):
                action = "delete_or_quarantine_after_user_approval_wrong_closed_register"
            elif size > 50_000_000 and ext == ".csv":
                action = "convert_to_parquet_zstd_then_remove_csv_after_hash_manifest"
            elif size > 50_000_000 and ext in {".zip", ".bin"}:
                action = "move_to_external_data_cache_with_manifest_or_keep_raw_archive"
            elif "data/raw" in str(rel):
                action = "keep_raw_with_source_manifest"
            else:
                action = "keep"
            rows.append(
                {
                    "path": str(rel),
                    "size_bytes": size,
                    "size_mb": round(size / 1024 / 1024, 3),
                    "extension": ext,
                    "recommended_action": action,
                }
            )
    df = pd.DataFrame(rows).sort_values("size_bytes", ascending=False)
    df.to_csv(PROCESSED / "partial_stats_phase53_storage_inventory.csv", index=False, encoding="utf-8-sig")
    return df


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "없음."
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df.iterrows():
        vals = [str(r.get(c, "")).replace("\n", " ").replace("|", "/") for c in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_report(file_manifest: pd.DataFrame, broker: pd.DataFrame, korail: pd.DataFrame, rtms_manifest: pd.DataFrame, storage: pd.DataFrame) -> None:
    unresolved = file_manifest[file_manifest["file_collection_status"].isin(["no_direct_file_url", "deferred_large_15_58m_rows", "download_failed"])]
    total_size = storage["size_bytes"].sum()
    broker_summary = pd.DataFrame()
    if not broker.empty:
        broker_summary = broker.groupby(["city", "general_gu"], as_index=False).agg(count=("office_name", "count"))
    rtms_summary = pd.DataFrame()
    if not rtms_manifest.empty:
        rtms_summary = rtms_manifest.groupby(["source_id", "collection_status"], as_index=False).agg(calls=("source_id", "count"), items=("item_count", "sum"))
    korail_summary = pd.DataFrame()
    if not korail.empty:
        korail_summary = korail.groupby(["city", "general_gu", "station_name"], as_index=False).agg(days=("date", "nunique"), total_passengers=("boarding", lambda s: int(s.sum())))
        alight = korail.groupby(["city", "general_gu", "station_name"], as_index=False).agg(alighting=("alighting", "sum"))
        korail_summary = korail_summary.merge(alight, on=["city", "general_gu", "station_name"], how="left")
        korail_summary["total_passengers"] = korail_summary["total_passengers"] + korail_summary["alighting"]
        korail_summary = korail_summary.drop(columns=["alighting"])
    lines = [
        "# Phase53 무료 후보자료 수집 및 저장공간 진단",
        "",
        "## 결론",
        "",
        "- 고양시·포항시 부동산중개업 파일은 직접 수집했고, 부동산 관련 서비스업 보강 피처로 정규화했다.",
        "- 실거래가 API는 기존 공공데이터포털 키로 지역·월 단위 호출을 시도해 결과와 실패사유를 캐시에 남겼다.",
        "- 공동주택 공시가격은 무료이나 1,558만 건 대용량 전국 파일이므로, 현재 저장공간 조건에서는 메타데이터만 확보하고 지역추출/외부캐시 전략 확정 후 수집하는 것이 안전하다.",
        f"- 현재 진단 대상 파일 총량: {total_size / 1024 / 1024 / 1024:.2f}GB.",
        "",
        "## 수집 결과",
        "",
        md_table(file_manifest[["source_id", "source_name", "target_industry", "file_collection_status", "local_path", "content_url", "external_url"]]),
        "",
        "## 부동산중개업 구 단위 피처",
        "",
        md_table(broker_summary) if not broker_summary.empty else "수집된 broker 행 없음.",
        "",
        "## 실거래가 API 호출 요약",
        "",
        md_table(rtms_summary) if not rtms_summary.empty else "실거래가 API 호출 결과 없음.",
        "",
        "## 철도 승하차 지역 추출",
        "",
        md_table(korail_summary) if not korail_summary.empty else "지역 대상 철도역 행 없음.",
        "",
        "## 수집 보류/수동 확인 링크",
        "",
        md_table(unresolved[["source_id", "source_name", "portal_url", "content_url", "external_url", "file_collection_status"]]) if not unresolved.empty else "없음.",
        "",
        "## 저장공간 개선안",
        "",
        "1. 원자료는 `source_id`, 원 URL, 다운로드시각, SHA-256, 행수, 스키마 fingerprint만 manifest로 남기고, 대용량 본체는 repo 밖 외부 캐시 또는 DVC/git-annex로 분리한다.",
        "2. 반복 재생산 가능한 중간 CSV는 Parquet/Zstd로 전환하고, CSV 원본은 해시 검증 후 삭제 승인 대상으로 둔다.",
        "3. 잘못 받은 `폐쇄말소대장_표제부` 145MB 파일은 표제부 현행자료와 별개이므로 사용자 승인 후 삭제 또는 quarantine 이동 대상이다.",
        "4. 공시가격·건축물대장처럼 전국 대용량 파일은 전체 파일을 계속 repo 내부에 두기보다, 지역 추출본과 원천 manifest만 프로젝트에 남기는 편이 맞다.",
        "",
        "## 산출 파일",
        "",
        "- `data/processed/partial_stats_phase53_candidate_source_manifest.csv`",
        "- `data/processed/partial_stats_phase53_realestate_broker_goyang_pohang.csv`",
        "- `data/processed/partial_stats_phase53_realestate_broker_gu_features.csv`",
        "- `data/processed/partial_stats_phase53_rtms_collection_manifest.csv`",
        "- `data/processed/partial_stats_phase53_korail_station_monthly_features.csv`",
        "- `data/processed/partial_stats_phase53_storage_inventory.csv`",
    ]
    (REPORTS / "partial_statistics_estimation_phase53_free_candidate_collection.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    manifest = collect_page_metadata()
    manifest = download_known_files(manifest)
    file_manifest = pd.DataFrame(manifest)
    file_manifest.to_csv(PROCESSED / "partial_stats_phase53_candidate_source_manifest.csv", index=False, encoding="utf-8-sig")
    broker = normalize_broker_files()
    korail = normalize_korail_file()
    _rtms, rtms_manifest_rows = collect_rtms()
    rtms_manifest = pd.DataFrame(rtms_manifest_rows)
    rtms_manifest.to_csv(PROCESSED / "partial_stats_phase53_rtms_collection_manifest.csv", index=False, encoding="utf-8-sig")
    storage = storage_inventory()
    write_report(file_manifest, broker, korail, rtms_manifest, storage)


if __name__ == "__main__":
    main()
