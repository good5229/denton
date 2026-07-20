from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "phase35_free_interaction"
NTS_PUBLIC_DATA_PK = "15061118"
NTS_CURRENT_DPK = "uddi:7848286e-4caa-4c35-8343-8ee0663b2e14"
HISTORY_URL = "https://www.data.go.kr/tcs/dss/selectHistAndCsvData.do"
DETAIL_URL = "https://www.data.go.kr/tcs/dss/selectDpkDetailInfo.do"
DOWNLOAD_URL = "https://www.data.go.kr/cmm/cmm/fileDownload.do"
TARGET_START = "20210131"
TARGET_END = "20231231"


def fetch(url: str) -> bytes:
    return subprocess.check_output(
        ["curl", "-L", "-sS", "--max-time", "60", "-A", "Mozilla/5.0 phase35-research", url]
    )


def portal_url(base: str, dpk: str) -> str:
    return base + "?" + urllib.parse.urlencode(
        {"publicDataPk": NTS_PUBLIC_DATA_PK, "publicDataDetailPk": dpk}
    )


def parse_history(html: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r'title="상세 보기 : 국세청_사업자현황_100대 생활업종_(\d{8})"[^>]*'
        r"fn_fileDataDetail\('(uddi:[0-9a-f-]+)'",
        re.I,
    )
    rows = [
        {"reference_date": date, "public_data_detail_pk": dpk}
        for date, dpk in pattern.findall(html)
        if TARGET_START <= date <= TARGET_END
    ]
    if len(rows) != 36:
        raise RuntimeError(f"expected 36 monthly NTS vintages for 2021-2023, found {len(rows)}")
    return sorted(rows, key=lambda row: row["reference_date"])


def parse_detail(row: dict[str, str]) -> dict[str, str]:
    html = fetch(portal_url(DETAIL_URL, row["public_data_detail_pk"])).decode("utf-8", errors="replace")
    attachment = re.search(
        r"fn_fileDataDown\('[^']+',\s*'[^']+',\s*'(FILE_\d+)',\s*'(\d+)',\s*'csv'\)",
        html,
        re.I,
    )
    registered = re.search(r"등록일</th>\s*<td[^>]*>\s*(\d{4}-\d{2}-\d{2})", html)
    modified = re.search(r"수정일</th>\s*<td[^>]*>\s*(\d{4}-\d{2}-\d{2})", html)
    if not attachment or not registered:
        raise RuntimeError(f"missing attachment/release metadata for {row['reference_date']}")
    return {
        **row,
        "attachment_id": attachment.group(1),
        "file_detail_sn": attachment.group(2),
        "registered_date": registered.group(1),
        "modified_date": modified.group(1) if modified else "",
    }


def download_one(row: dict[str, str]) -> dict[str, str | int]:
    path = RAW_DIR / f"nts_lifestyle_{row['reference_date']}.csv"
    url = DOWNLOAD_URL + "?" + urllib.parse.urlencode(
        {
            "atchFileId": row["attachment_id"],
            "fileDetailSn": row["file_detail_sn"],
            "insertDataPrcus": "N",
        }
    )
    payload = fetch(url)
    if len(payload) < 10_000 or b"<html" in payload[:500].lower():
        raise RuntimeError(f"invalid download for {row['reference_date']}: {len(payload)} bytes")
    path.write_bytes(payload)
    return {
        **row,
        "local_file": str(path.relative_to(ROOT)),
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "source_url": url,
    }


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    history = fetch(portal_url(HISTORY_URL, NTS_CURRENT_DPK)).decode("utf-8", errors="replace")
    rows = parse_history(history)
    with ThreadPoolExecutor(max_workers=6) as pool:
        details = list(pool.map(parse_detail, rows))
        futures = {pool.submit(download_one, row): row for row in details}
        downloaded = []
        for future in as_completed(futures):
            result = future.result()
            downloaded.append(result)
            print(f"downloaded {result['reference_date']}", flush=True)
    downloaded.sort(key=lambda row: str(row["reference_date"]))
    manifest = RAW_DIR / "nts_lifestyle_manifest_2021_2023.csv"
    with manifest.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(downloaded[0]))
        writer.writeheader()
        writer.writerows(downloaded)
    print(f"wrote {manifest.relative_to(ROOT)} ({len(downloaded)} files)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"collection failed: {exc}", file=sys.stderr)
        raise
