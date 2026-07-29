#!/usr/bin/env python3
"""Incrementally collect PPS construction contract rows by month.

The official PPS contract endpoint can return 20k~40k+ rows per month, and
`numOfRows` effectively caps at 999.  This collector therefore:

1. stores raw JSON page caches by month;
2. writes a normalized monthly CSV immediately after each month;
3. writes/updates a collection manifest after each month;
4. resumes from existing raw/monthly outputs unless `--refresh` is set.

Raw and processed data stay under ignored `data/` paths; scripts/reports are
the reproducible tracked artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import time
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase248_pps_contract_incremental"
MONTHLY = ROOT / "data" / "processed" / "phase248_pps_contract_monthly"
OUT = ROOT / "data" / "processed"
ENDPOINT = "https://apis.data.go.kr/1230000/ao/CntrctInfoService/getCntrctInfoListCnstwk"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
MANIFEST_LOCK = Lock()
PERIOD_RE = re.compile(r"^\d{6}$")

PROVINCES = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "강원도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]


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
    key = os.environ.get("DATA_GO_KR_DECODING")
    if not key:
        raise SystemExit("DATA_GO_KR_DECODING missing in .env")
    return key


def ssl_context() -> ssl.SSLContext:
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


def validate_period(value: object) -> str:
    period = str(value).strip()
    if not PERIOD_RE.fullmatch(period):
        raise ValueError(f"invalid period: {period!r}")
    month = int(period[4:6])
    if not 1 <= month <= 12:
        raise ValueError(f"invalid period month: {period!r}")
    return period


def bounds(period: str) -> tuple[str, str]:
    period = validate_period(period)
    y, m = int(period[:4]), int(period[4:])
    return f"{period}010000", f"{period}{monthrange(y, m)[1]:02d}2359"


def day_bounds(period: str, day: int) -> tuple[str, str]:
    period = validate_period(period)
    return f"{period}{day:02d}0000", f"{period}{day:02d}2359"


def normalize_province(p: str) -> str:
    if p == "강원도":
        return "강원특별자치도"
    if p == "전라북도":
        return "전북특별자치도"
    return p


def parse_region(text: object) -> tuple[str, str]:
    s = str(text or "").strip()
    if not s or s.lower() == "nan":
        return "", ""
    province = ""
    rest = ""
    for p in PROVINCES:
        idx = s.find(p)
        if idx >= 0:
            province = normalize_province(p)
            rest = s[idx + len(p) :].strip()
            break
    if not province:
        return "", ""
    if province == "세종특별자치시":
        return province, "세종특별자치시"
    m = re.search(r"([가-힣A-Za-z0-9]+(?:시|군|구))", rest)
    return province, (m.group(1) if m else "")


def body_of(data: dict[str, Any]) -> dict[str, Any]:
    response = data.get("response") or {}
    header = response.get("header") or {}
    code = str(header.get("resultCode", ""))
    if code and code != "00":
        raise RuntimeError(f"resultCode={code} resultMsg={header.get('resultMsg')}")
    body = response.get("body") or {}
    return body if isinstance(body, dict) else {}


def items_of(data: dict[str, Any]) -> list[dict[str, Any]]:
    items = body_of(data).get("items") or []
    if isinstance(items, dict):
        item = items.get("item", items)
        if isinstance(item, list):
            return [x for x in item if isinstance(x, dict)]
        if isinstance(item, dict):
            return [item]
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    return []


def fetch_page(
    period: str,
    page: int,
    num_rows: int,
    key: str,
    timeout: int,
    refresh: bool,
    retries: int,
    retry_sleep: float,
) -> dict[str, Any]:
    begin, end = bounds(period)
    return fetch_page_range(period, begin, end, page, num_rows, key, timeout, refresh, retries, retry_sleep, "")


def fetch_page_range(
    period: str,
    begin: str,
    end: str,
    page: int,
    num_rows: int,
    key: str,
    timeout: int,
    refresh: bool,
    retries: int,
    retry_sleep: float,
    cache_suffix: str,
) -> dict[str, Any]:
    raw_dir = RAW / period
    raw_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{cache_suffix}" if cache_suffix else ""
    path = raw_dir / f"contract_{period}{suffix}_n{num_rows}_{page:04d}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    params = {
        "serviceKey": key,
        "pageNo": page,
        "numOfRows": num_rows,
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": begin,
        "inqryEndDt": end,
    }
    req = Request(f"{ENDPOINT}?{urlencode(params)}", headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=timeout, context=ssl_context()) as response:
                text = response.read().decode("utf-8", errors="replace")
            break
        except HTTPError as exc:
            last_exc = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt >= retries:
                raise
            print(
                f"{period} page={page} retry={attempt + 1}/{retries} after HTTP {exc.code}; sleep={retry_sleep * (attempt + 1):.1f}s",
                flush=True,
            )
            time.sleep(retry_sleep * (attempt + 1))
        except URLError as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            print(
                f"{period} page={page} retry={attempt + 1}/{retries} after {type(exc).__name__}; sleep={retry_sleep * (attempt + 1):.1f}s",
                flush=True,
            )
            time.sleep(retry_sleep * (attempt + 1))
    else:
        raise RuntimeError(f"request failed after retries: {last_exc!r}")
    text = text.replace(key, "[REDACTED_DATA_GO_KR_KEY]")
    data = json.loads(text)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def normalize_month(period: str, rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["source_period"] = period
    amount = pd.to_numeric(df.get("totCntrctAmt"), errors="coerce").fillna(0)
    current_amount = pd.to_numeric(df.get("thtmCntrctAmt"), errors="coerce").fillna(0)
    df["contract_amount_eok"] = amount / 100_000_000
    df["current_contract_amount_eok"] = current_amount / 100_000_000
    df["contract_date"] = pd.to_datetime(df.get("cntrctDate"), errors="coerce")
    df["start_date"] = pd.to_datetime(df.get("cbgnDate"), errors="coerce")
    df["completion_date"] = pd.to_datetime(df.get("ttalCcmpltDate"), errors="coerce")
    region_text = (
        df.get("cntrctInsttNm", pd.Series("", index=df.index)).fillna("").astype(str)
        + " "
        + df.get("dminsttList", pd.Series("", index=df.index)).fillna("").astype(str)
        + " "
        + df.get("cnstwkNm", pd.Series("", index=df.index)).fillna("").astype(str)
    )
    parsed = region_text.map(parse_region)
    df["matched_province_full"] = parsed.map(lambda x: x[0])
    df["matched_city"] = parsed.map(lambda x: x[1])
    keep = [
        "source_period",
        "untyCntrctNo",
        "cntrctRefNo",
        "cnstwkNm",
        "cntrctInsttNm",
        "dminsttList",
        "pubPrcrmntClsfcNm",
        "pubPrcrmntMidClsfcNm",
        "pubPrcrmntLrgClsfcNm",
        "cntrctDate",
        "cbgnDate",
        "ttalCcmpltDate",
        "totCntrctAmt",
        "thtmCntrctAmt",
        "contract_amount_eok",
        "current_contract_amount_eok",
        "matched_province_full",
        "matched_city",
    ]
    keep = [c for c in keep if c in df.columns]
    return df[keep].copy()


def update_manifest(row: dict[str, Any]) -> None:
    with MANIFEST_LOCK:
        path = OUT / "phase248_pps_contract_collection_manifest.csv"
        row["period"] = validate_period(row["period"])
        previous = pd.DataFrame()
        if path.exists():
            try:
                m = pd.read_csv(path, dtype={"period": str})
            except pd.errors.EmptyDataError:
                m = pd.DataFrame()
            if not m.empty and "period" in m.columns:
                valid = m["period"].astype(str).map(lambda x: bool(PERIOD_RE.fullmatch(x)) and 1 <= int(x[4:6]) <= 12)
                m = m[valid].copy()
                m["period"] = m["period"].astype(str)
            previous = m[m["period"].astype(str).eq(row["period"])].copy()
            if not previous.empty and not row.get("complete") and not row.get("ok"):
                prev = previous.iloc[-1]
                prev_complete = str(prev.get("complete", "")).strip().lower() in {"true", "1", "yes"}
                prev_ok = str(prev.get("ok", "")).strip().lower() in {"true", "1", "yes"}
                if prev_complete and prev_ok:
                    preserved = prev.to_dict()
                    preserved["last_failed_at"] = CREATED_AT
                    preserved["last_error"] = row.get("error", "")
                    row = preserved
            if not previous.empty and not row.get("complete") and not row.get("ok"):
                prev = previous.iloc[-1]
                # Do not let a failed refresh attempt with no response body erase
                # the best known API total/partial progress for this month.
                for col in ["total_count", "rows_collected", "pages_collected"]:
                    try:
                        old_value = int(float(prev.get(col, 0) or 0))
                    except (TypeError, ValueError):
                        old_value = 0
                    try:
                        new_value = int(float(row.get(col, 0) or 0))
                    except (TypeError, ValueError):
                        new_value = 0
                    if old_value > new_value:
                        row[col] = old_value
            m = m[m["period"].astype(str).ne(row["period"])]
            m = pd.concat([m, pd.DataFrame([row])], ignore_index=True)
        else:
            m = pd.DataFrame([row])
        m["period"] = m["period"].map(validate_period)
        m = m.sort_values("period")
        tmp = path.with_suffix(path.suffix + ".tmp")
        m.to_csv(tmp, index=False, encoding="utf-8-sig")
        tmp.replace(path)


def manifest_complete(period: str) -> bool:
    period = validate_period(period)
    path = OUT / "phase248_pps_contract_collection_manifest.csv"
    if not path.exists():
        return False
    try:
        m = pd.read_csv(path, dtype={"period": str})
    except (pd.errors.EmptyDataError, OSError):
        return False
    if m.empty or "period" not in m.columns or "complete" not in m.columns:
        return False
    raw_period = m["period"].astype(str).str.strip()
    valid_period = raw_period.map(lambda x: bool(PERIOD_RE.fullmatch(x)) and 1 <= int(x[4:6]) <= 12)
    hit = m[valid_period & raw_period.eq(period)]
    if hit.empty:
        return False
    value = hit.iloc[-1]["complete"]
    return str(value).strip().lower() in {"true", "1", "yes"}


def collect_month(
    period: str,
    num_rows: int,
    key: str,
    timeout: int,
    sleep: float,
    refresh: bool,
    max_pages: int | None,
    retries: int,
    retry_sleep: float,
    progress_every: int,
) -> dict[str, Any]:
    out_path = MONTHLY / f"pps_contract_{period}.csv"
    if out_path.exists() and not refresh and manifest_complete(period):
        existing = pd.read_csv(out_path)
        row = {
            "period": period,
            "total_count": len(existing),
            "rows_collected": len(existing),
            "pages_collected": len(list((RAW / period).glob("contract_*.json"))),
            "complete": True,
            "skipped_existing": True,
            "ok": True,
            "error": "",
            "created_at": CREATED_AT,
            "raw_dir": str((RAW / period).relative_to(ROOT)),
            "monthly_csv": str(out_path.relative_to(ROOT)),
        }
        update_manifest(row)
        print(f"{period} skip existing rows={len(existing)}", flush=True)
        return row
    page = 1
    total = None
    rows: list[dict[str, Any]] = []
    pages = 0
    error = ""
    while True:
        try:
            data = fetch_page(period, page, num_rows, key, timeout, refresh, retries, retry_sleep)
            b = body_of(data)
            if total is None:
                total = int(b.get("totalCount") or 0)
            items = items_of(data)
            rows.extend(items)
            pages += 1
            if progress_every and pages % progress_every == 0:
                print(f"{period} progress pages={pages} rows={len(rows):,}/{int(total or 0):,}", flush=True)
            if page * num_rows >= total:
                break
            if max_pages is not None and page >= max_pages:
                break
            page += 1
            if sleep:
                time.sleep(sleep)
        except Exception as exc:
            error = repr(exc)
            break
    if error:
        row = {
            "period": period,
            "total_count": int(total or 0),
            "rows_collected": int(len(rows)),
            "pages_collected": int(pages),
            "complete": False,
            "skipped_existing": False,
            "ok": False,
            "error": error,
            "created_at": CREATED_AT,
            "raw_dir": str((RAW / period).relative_to(ROOT)),
            "monthly_csv": str(out_path.relative_to(ROOT)),
        }
        update_manifest(row)
        print(
            f"{period} rows={len(rows):,}/{int(total or 0):,} pages={pages} complete=False error=yes",
            flush=True,
        )
        return row
    df = normalize_month(period, rows)
    MONTHLY.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    row = {
        "period": period,
        "total_count": int(total or 0),
        "rows_collected": int(len(df)),
        "pages_collected": int(pages),
        "complete": bool(total is not None and len(df) >= total and not error and max_pages is None),
        "skipped_existing": False,
        "ok": not bool(error),
        "error": error,
        "created_at": CREATED_AT,
        "raw_dir": str((RAW / period).relative_to(ROOT)),
        "monthly_csv": str(out_path.relative_to(ROOT)),
    }
    update_manifest(row)
    print(
        f"{period} rows={len(df):,}/{int(total or 0):,} pages={pages} complete={row['complete']} error={'yes' if error else 'no'}",
        flush=True,
    )
    return row


def collect_month_daily_split(
    period: str,
    num_rows: int,
    key: str,
    timeout: int,
    sleep: float,
    refresh: bool,
    max_pages: int | None,
    retries: int,
    retry_sleep: float,
    progress_every: int,
) -> dict[str, Any]:
    out_path = MONTHLY / f"pps_contract_{period}.csv"
    if out_path.exists() and not refresh and manifest_complete(period):
        existing = pd.read_csv(out_path)
        row = {
            "period": period,
            "total_count": len(existing),
            "rows_collected": len(existing),
            "pages_collected": len(list((RAW / period).glob("contract_*.json"))),
            "complete": True,
            "skipped_existing": True,
            "ok": True,
            "error": "",
            "created_at": CREATED_AT,
            "raw_dir": str((RAW / period).relative_to(ROOT)),
            "monthly_csv": str(out_path.relative_to(ROOT)),
        }
        update_manifest(row)
        print(f"{period} skip existing rows={len(existing)}", flush=True)
        return row

    year, month = int(period[:4]), int(period[4:])
    rows: list[dict[str, Any]] = []
    total = 0
    pages = 0
    error = ""
    for day in range(1, monthrange(year, month)[1] + 1):
        begin, end = day_bounds(period, day)
        page = 1
        day_total = None
        while True:
            try:
                data = fetch_page_range(
                    period,
                    begin,
                    end,
                    page,
                    num_rows,
                    key,
                    timeout,
                    refresh,
                    retries,
                    retry_sleep,
                    f"d{day:02d}",
                )
                b = body_of(data)
                if day_total is None:
                    day_total = int(b.get("totalCount") or 0)
                    total += day_total
                items = items_of(data)
                rows.extend(items)
                pages += 1
                if page * num_rows >= day_total:
                    break
                if max_pages is not None and page >= max_pages:
                    break
                page += 1
                if sleep:
                    time.sleep(sleep)
            except Exception as exc:
                error = repr(exc)
                break
        if error:
            break
        if progress_every and day % progress_every == 0:
            print(f"{period} daily progress day={day:02d} rows={len(rows):,}/{total:,} pages={pages}", flush=True)
        if sleep:
            time.sleep(sleep)

    if error:
        row = {
            "period": period,
            "total_count": int(total or 0),
            "rows_collected": int(len(rows)),
            "pages_collected": int(pages),
            "complete": False,
            "skipped_existing": False,
            "ok": False,
            "error": error,
            "created_at": CREATED_AT,
            "raw_dir": str((RAW / period).relative_to(ROOT)),
            "monthly_csv": str(out_path.relative_to(ROOT)),
        }
        update_manifest(row)
        print(f"{period} daily rows={len(rows):,}/{int(total or 0):,} pages={pages} complete=False error=yes", flush=True)
        return row

    df = normalize_month(period, rows)
    if {"untyCntrctNo", "cntrctRefNo"}.issubset(df.columns):
        df = df.drop_duplicates(["untyCntrctNo", "cntrctRefNo"], keep="last")
    MONTHLY.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    row = {
        "period": period,
        "total_count": int(total or 0),
        "rows_collected": int(len(df)),
        "pages_collected": int(pages),
        "complete": bool(total is not None and len(df) >= total and max_pages is None),
        "skipped_existing": False,
        "ok": True,
        "error": "",
        "created_at": CREATED_AT,
        "raw_dir": str((RAW / period).relative_to(ROOT)),
        "monthly_csv": str(out_path.relative_to(ROOT)),
    }
    update_manifest(row)
    print(f"{period} daily rows={len(df):,}/{int(total or 0):,} pages={pages} complete={row['complete']} error=no", flush=True)
    return row


def write_aggregate(start: str, end: str) -> None:
    files = sorted(MONTHLY.glob("pps_contract_*.csv"))
    frames = []
    for p in files:
        period = p.stem.rsplit("_", 1)[-1]
        if start <= period <= end:
            try:
                frame = pd.read_csv(p)
            except pd.errors.EmptyDataError:
                continue
            if frame.empty or "source_period" not in frame.columns:
                continue
            frames.append(frame)
    if not frames:
        return
    df = pd.concat(frames, ignore_index=True)
    df["period"] = df["source_period"].astype(str).str.zfill(6)
    df["year"] = df["period"].str[:4].astype(int)
    df["quarter"] = pd.PeriodIndex(pd.to_datetime(df["period"] + "01", format="%Y%m%d"), freq="Q").astype(str)
    sig_base = df[df["matched_province_full"].fillna("").ne("") & df["matched_city"].fillna("").ne("")]
    prov_base = df[df["matched_province_full"].fillna("").ne("")]
    sig_year = (
        sig_base
        .groupby(["matched_province_full", "matched_city", "year"], as_index=False)
        .agg(
            pps_contract_rows=("untyCntrctNo", "count"),
            pps_contract_amount_eok=("contract_amount_eok", "sum"),
            pps_current_contract_amount_eok=("current_contract_amount_eok", "sum"),
        )
    )
    sig_quarter = (
        sig_base
        .groupby(["matched_province_full", "matched_city", "year", "quarter"], as_index=False)
        .agg(
            pps_contract_rows=("untyCntrctNo", "count"),
            pps_contract_amount_eok=("contract_amount_eok", "sum"),
            pps_current_contract_amount_eok=("current_contract_amount_eok", "sum"),
        )
    )
    sig_month = (
        sig_base
        .groupby(["matched_province_full", "matched_city", "year", "period"], as_index=False)
        .agg(
            pps_contract_rows=("untyCntrctNo", "count"),
            pps_contract_amount_eok=("contract_amount_eok", "sum"),
            pps_current_contract_amount_eok=("current_contract_amount_eok", "sum"),
        )
    )
    prov_year = (
        prov_base
        .groupby(["matched_province_full", "year"], as_index=False)
        .agg(
            pps_contract_rows=("untyCntrctNo", "count"),
            pps_contract_amount_eok=("contract_amount_eok", "sum"),
            pps_current_contract_amount_eok=("current_contract_amount_eok", "sum"),
        )
    )
    prov_quarter = (
        prov_base
        .groupby(["matched_province_full", "year", "quarter"], as_index=False)
        .agg(
            pps_contract_rows=("untyCntrctNo", "count"),
            pps_contract_amount_eok=("contract_amount_eok", "sum"),
            pps_current_contract_amount_eok=("current_contract_amount_eok", "sum"),
        )
    )
    prov_month = (
        prov_base
        .groupby(["matched_province_full", "year", "period"], as_index=False)
        .agg(
            pps_contract_rows=("untyCntrctNo", "count"),
            pps_contract_amount_eok=("contract_amount_eok", "sum"),
            pps_current_contract_amount_eok=("current_contract_amount_eok", "sum"),
        )
    )
    OUT.mkdir(parents=True, exist_ok=True)
    sig_year.to_csv(OUT / f"phase248_pps_contract_sigungu_year_{start}_{end}.csv", index=False, encoding="utf-8-sig")
    sig_quarter.to_csv(OUT / f"phase248_pps_contract_sigungu_quarter_{start}_{end}.csv", index=False, encoding="utf-8-sig")
    sig_month.to_csv(OUT / f"phase248_pps_contract_sigungu_month_{start}_{end}.csv", index=False, encoding="utf-8-sig")
    prov_year.to_csv(OUT / f"phase248_pps_contract_province_year_{start}_{end}.csv", index=False, encoding="utf-8-sig")
    prov_quarter.to_csv(OUT / f"phase248_pps_contract_province_quarter_{start}_{end}.csv", index=False, encoding="utf-8-sig")
    prov_month.to_csv(OUT / f"phase248_pps_contract_province_month_{start}_{end}.csv", index=False, encoding="utf-8-sig")
    # Stable latest aliases for downstream scripts/manual inspection.
    sig_year.to_csv(OUT / "phase248_pps_contract_sigungu_year_latest.csv", index=False, encoding="utf-8-sig")
    sig_quarter.to_csv(OUT / "phase248_pps_contract_sigungu_quarter_latest.csv", index=False, encoding="utf-8-sig")
    sig_month.to_csv(OUT / "phase248_pps_contract_sigungu_month_latest.csv", index=False, encoding="utf-8-sig")
    prov_year.to_csv(OUT / "phase248_pps_contract_province_year_latest.csv", index=False, encoding="utf-8-sig")
    prov_quarter.to_csv(OUT / "phase248_pps_contract_province_quarter_latest.csv", index=False, encoding="utf-8-sig")
    prov_month.to_csv(OUT / "phase248_pps_contract_province_month_latest.csv", index=False, encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="201501")
    parser.add_argument("--end", default="202512")
    parser.add_argument("--num-rows", type=int, default=999)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=0.02)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true", help="stop at the first incomplete or failed month")
    parser.add_argument("--workers", type=int, default=1, help="parallel month collectors; each month still fetches pages sequentially")
    parser.add_argument("--retries", type=int, default=8)
    parser.add_argument("--retry-sleep", type=float, default=45.0)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--daily-split", action="store_true", help="split incomplete months into day-sized API queries")
    args = parser.parse_args()
    key = service_key()
    RAW.mkdir(parents=True, exist_ok=True)
    MONTHLY.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    periods = month_iter(args.start, args.end)
    collector = collect_month_daily_split if args.daily_split else collect_month
    if args.workers <= 1:
        for period in periods:
            row = collector(
                period,
                args.num_rows,
                key,
                args.timeout,
                args.sleep,
                args.refresh,
                args.max_pages,
                args.retries,
                args.retry_sleep,
                args.progress_every,
            )
            if args.stop_on_error and not row.get("complete"):
                raise SystemExit(2)
    else:
        if args.stop_on_error:
            print("--stop-on-error is ignored when --workers > 1; all submitted months finish first.", flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    collector,
                    period,
                    args.num_rows,
                    key,
                    args.timeout,
                    args.sleep,
                    args.refresh,
                    args.max_pages,
                    args.retries,
                    args.retry_sleep,
                    args.progress_every,
                ): period
                for period in periods
            }
            failed = []
            for future in as_completed(futures):
                period = futures[future]
                try:
                    row = future.result()
                except Exception as exc:
                    failed.append((period, repr(exc)))
                    print(f"{period} worker_exception={exc!r}", flush=True)
                    continue
                if not row.get("complete"):
                    failed.append((period, row.get("error", "")))
            if failed:
                print(f"incomplete_or_failed_months={len(failed)}", flush=True)
                for period, error in failed[:20]:
                    print(f"  {period}: {error}", flush=True)
    write_aggregate(args.start, args.end)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
