#!/usr/bin/env python3
"""Collect Gyeonggi bus stop boarding/alighting original ZIP files.

Dataset:
  경기도 정류소 별 승하차 인원 집계
  https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId=MZCREO5CKHZM6PJEA55P37391662&infSeq=2

The Sheet tab is only a one-day sample.  Full data are exposed in the File tab
as ZIP files with fileSeq IDs, and the actual endpoint is:
  /portal/data/file/downloadFileData.do?infId=...&infSeq=2&fileSeq=...

Usage:
  python scripts/collect_gg_bus_boarding_files.py --list
  python scripts/collect_gg_bus_boarding_files.py --period 202602
  python scripts/collect_gg_bus_boarding_files.py --all
"""

from __future__ import annotations

import argparse
import email.message
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


BASE = "https://data.gg.go.kr"
INF_ID = "MZCREO5CKHZM6PJEA55P37391662"
INF_SEQ = "2"
PAGE_URL = f"{BASE}/portal/data/service/selectServicePage.do?infId={INF_ID}&infSeq={INF_SEQ}"
DOWNLOAD_URL = f"{BASE}/portal/data/file/downloadFileData.do"
OUT_DIR = Path("data/raw/phase58_gg_bus_auto/original_zips")
MANIFEST_PATH = Path("data/raw/phase58_gg_bus_auto/gg_bus_original_file_manifest.json")
CACHED_FILE_TAB_HTML = Path("data/raw/phase58_gg_bus_auto/selenium_file_tab/file_tab.html")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150 Safari/537.36"
)


@dataclass
class FileEntry:
    period: str
    freshness: str
    file_seq: str
    filename: str
    size_text: str
    url: str


def opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
    )


def request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, timeout: int = 60):
    h = {
        "User-Agent": UA,
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    }
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, method=method)
    return opener().open(req, timeout=timeout)


def fetch_file_tab_html() -> str:
    try:
        with request(PAGE_URL, timeout=30) as resp:
            body = resp.read()
        return body.decode("utf-8", errors="ignore")
    except (TimeoutError, urllib.error.URLError) as exc:
        print(f"warning: live page fetch failed; falling back to cached Selenium HTML: {exc}", file=sys.stderr)
        return ""


def parse_file_entries(html: str) -> list[FileEntry]:
    # Each file row has a <p> with the filename/size followed by a button with data-file-seq.
    pattern = re.compile(
        r"<p[^>]*>\s*(경기도\s+정류소\s+별\s+승하차\s+인원\s+집계_(?P<period>\d{4,6})_(?P<fresh>D-\d+)\.zip\s+\[zip,\s*(?P<size>[^\]]+)\])\s*</p>.*?"
        r'data-file-seq="(?P<file_seq>\d+)"',
        flags=re.DOTALL,
    )
    entries: list[FileEntry] = []
    for m in pattern.finditer(html):
        filename = f"경기도 정류소 별 승하차 인원 집계_{m.group('period')}_{m.group('fresh')}.zip"
        params = urllib.parse.urlencode({"infId": INF_ID, "infSeq": INF_SEQ, "fileSeq": m.group("file_seq")})
        entries.append(
            FileEntry(
                period=m.group("period"),
                freshness=m.group("fresh"),
                file_seq=m.group("file_seq"),
                filename=filename,
                size_text=m.group("size").strip(),
                url=f"{DOWNLOAD_URL}?{params}",
            )
        )
    return entries


def safe_filename_from_disposition(disposition: str, fallback: str) -> str:
    if not disposition:
        return fallback
    msg = email.message.Message()
    msg["content-disposition"] = disposition
    filename = msg.get_filename()
    if filename:
        return urllib.parse.unquote(filename)
    m = re.search(r'filename="([^"]+)"', disposition)
    if m:
        return urllib.parse.unquote(m.group(1))
    return fallback


def download_entry(entry: FileEntry, out_dir: Path, *, overwrite: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / entry.filename
    if target.exists() and target.stat().st_size > 0 and not overwrite:
        return {
            **asdict(entry),
            "status": "skipped_exists",
            "path": str(target),
            "bytes": target.stat().st_size,
        }

    tmp = target.with_suffix(target.suffix + ".part")
    headers = {"Referer": PAGE_URL, "Accept": "application/octet-stream,*/*"}
    started = time.time()
    with request(entry.url, headers=headers, timeout=300) as resp:
        disposition = resp.headers.get("Content-Disposition", "")
        expected = int(resp.headers.get("Content-Length", "0") or "0")
        real_name = safe_filename_from_disposition(disposition, entry.filename)
        if real_name != entry.filename:
            target = out_dir / real_name
            tmp = target.with_suffix(target.suffix + ".part")
        with tmp.open("wb") as f:
            received = 0
            while True:
                if expected and received >= expected:
                    break
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
        if expected and tmp.stat().st_size < expected:
            raise RuntimeError(f"incomplete download: {tmp.stat().st_size} < {expected} bytes for {entry.period}")
    tmp.replace(target)
    return {
        **asdict(entry),
        "status": "downloaded",
        "path": str(target),
        "bytes": target.stat().st_size,
        "seconds": round(time.time() - started, 2),
    }


def select_entries(entries: list[FileEntry], periods: Iterable[str], all_entries: bool) -> list[FileEntry]:
    if all_entries:
        return entries
    wanted = {p.strip() for p in periods if p.strip()}
    if not wanted:
        # Conservative default: latest cleaned file, not D-4 provisional.
        wanted = {"202602"}
    selected = [e for e in entries if e.period in wanted]
    missing = sorted(wanted - {e.period for e in selected})
    if missing:
        print(f"missing periods in file tab: {missing}", file=sys.stderr)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="List available files and exit.")
    parser.add_argument("--all", action="store_true", help="Download all files shown in the File tab.")
    parser.add_argument("--period", action="append", default=[], help="Period to download, e.g. 202602 or 2024. Repeatable.")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    html = fetch_file_tab_html()
    entries = parse_file_entries(html)
    if not entries and CACHED_FILE_TAB_HTML.exists():
        html = CACHED_FILE_TAB_HTML.read_text(encoding="utf-8", errors="ignore")
        entries = parse_file_entries(html)
    if not entries:
        raise SystemExit("No file entries parsed from File tab.")

    if args.list:
        print(json.dumps([asdict(e) for e in entries], ensure_ascii=False, indent=2))
        return 0

    selected = select_entries(entries, args.period, args.all)
    results = []
    for entry in selected:
        print(f"download {entry.period} {entry.freshness} fileSeq={entry.file_seq} {entry.size_text}", flush=True)
        results.append(download_entry(entry, Path(args.out_dir), overwrite=args.overwrite))

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_name": "경기도 정류소 별 승하차 인원 집계",
        "source_url": PAGE_URL,
        "download_endpoint": DOWNLOAD_URL,
        "entries_found": len(entries),
        "selected": [e.period for e in selected],
        "results": results,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
