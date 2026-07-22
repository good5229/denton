#!/usr/bin/env python3
"""Probe whether the Gyeonggi Data Dream bus boarding file can be automated.

The script intentionally does not need or print any API keys.  It mimics the
browser flow enough to test:
  1) landing page + cookies + CSRF extraction
  2) sheet sample download endpoint
  3) file download endpoint with candidate fileSeq values

It writes small response samples and a JSON manifest under
data/raw/phase58_gg_bus_auto/.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request
import ssl


BASE = "https://data.gg.go.kr"
INF_ID = "MZCREO5CKHZM6PJEA55P37391662"
OUT_DIR = Path("data/raw/phase58_gg_bus_auto")
PROBE_DIR = OUT_DIR / "probes"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def sample_bytes(content: bytes, limit: int = 600) -> str:
    text = content[:limit].decode("utf-8", errors="replace")
    return re.sub(r"\s+", " ", text).strip()


def classify(content: bytes, headers: dict[str, str]) -> str:
    low = content[:1000].lower()
    ctype = headers.get("Content-Type", "")
    dispo = headers.get("Content-Disposition", "")
    if content.startswith(b"PK\x03\x04"):
        return "zip_or_xlsx"
    if content.startswith(b"\x1f\x8b"):
        return "gzip"
    if b"\xec\xa0\x95\xec\x83\x81\xec\xa0\x81\xec\x9d\xb8 \xec\xa0\x91\xea\xb7\xbc" in content:
        return "blocked_not_normal_access"
    if "text/csv" in ctype.lower() or ".csv" in dispo.lower():
        return "csv_like"
    if b"<html" in low or b"<script" in low or "text/html" in ctype.lower():
        return "html_or_script"
    if len(content) > 10_000:
        return "large_unknown_possible_data"
    return "small_unknown"


def request_bytes(
    opener: urllib.request.OpenerDirector,
    method: str,
    url: str,
    params: dict[str, str] | None = None,
    data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    final_url = url
    body: bytes | None = None
    request_headers = dict(headers or {})
    if params:
        query = urllib.parse.urlencode(params)
        final_url = f"{url}?{query}"
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(final_url, data=body, headers=request_headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as resp:
            content = resp.read()
            return {
                "url": resp.geturl(),
                "status_code": resp.getcode(),
                "headers": dict(resp.headers.items()),
                "content": content,
                "history": [],
            }
    except urllib.error.HTTPError as e:
        content = e.read()
        return {
            "url": e.geturl(),
            "status_code": e.code,
            "headers": dict(e.headers.items()),
            "content": content,
            "history": [],
        }
    except urllib.error.URLError as e:
        msg = str(e).encode("utf-8", errors="replace")
        return {
            "url": final_url,
            "status_code": 0,
            "headers": {"Content-Type": "text/plain"},
            "content": msg,
            "history": [],
            "error": str(e),
        }


def save_probe(name: str, response: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    body_path = PROBE_DIR / f"{safe_name}.bin"
    content = response["content"]
    headers = response["headers"]
    body_path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    rec: dict[str, Any] = {
        "name": name,
        "url": response["url"],
        "status_code": response["status_code"],
        "history": response.get("history", []),
        "content_type": headers.get("Content-Type", ""),
        "content_disposition": headers.get("Content-Disposition", ""),
        "content_length_header": headers.get("Content-Length", ""),
        "bytes": len(content),
        "sha256": digest,
        "classification": classify(content, headers),
        "body_path": str(body_path),
    }
    if response.get("error"):
        rec["error"] = response["error"]
    if extra:
        rec.update(extra)
    return rec


def extract_csrf(html: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for key in ("_csrf", "_csrf_header", "_csrf_param"):
        m = re.search(
            rf'<meta\s+name="{re.escape(key)}"\s+content="([^"]*)"',
            html,
            flags=re.IGNORECASE,
        )
        if m:
            values[key] = m.group(1)
    return values


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROBE_DIR.mkdir(parents=True, exist_ok=True)

    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar),
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
        # urllib follows redirects automatically.  For the file endpoint that is
        # acceptable here; redirects to the main page are classified as HTML.
    )
    base_headers = (
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
        }
    )

    manifest: list[dict[str, Any]] = []
    landing_by_seq: dict[int, str] = {}
    csrf_by_seq: dict[int, dict[str, str]] = {}

    for inf_seq in (1, 2):
        url = f"{BASE}/portal/data/service/selectServicePage.do"
        params = {"infId": INF_ID, "infSeq": str(inf_seq)}
        r = request_bytes(opener, "GET", url, params=params, headers=base_headers, timeout=30)
        landing_by_seq[inf_seq] = r["url"]
        html = r["content"].decode("utf-8", errors="ignore")
        csrf_by_seq[inf_seq] = extract_csrf(html)
        (OUT_DIR / f"landing_infseq{inf_seq}.html").write_text(html, encoding="utf-8", errors="ignore")
        manifest.append(
            save_probe(
                f"landing_infseq{inf_seq}",
                r,
                {
                    "inf_seq": inf_seq,
                    "csrf_keys_found": sorted(csrf_by_seq[inf_seq].keys()),
                    "contains_file_seq": "fileSeq" in html,
                    "contains_download_sheet": "downloadSheetData" in html,
                    "contains_file_download": "fileDownload.do" in html,
                    "contains_research_text": "연구" in html,
                },
            )
        )

    # The public mirror exposed this endpoint, but the direct call was blocked.
    # Re-test it with a live session, referer, X-CSRF-TOKEN, and both GET/POST.
    for inf_seq in (1, 2):
        csrf = csrf_by_seq.get(inf_seq, {})
        csrf_token = csrf.get("_csrf", "")
        csrf_header = csrf.get("_csrf_header", "X-CSRF-TOKEN")
        referer = landing_by_seq.get(inf_seq) or (
            f"{BASE}/portal/data/service/selectServicePage.do?infId={INF_ID}&infSeq={inf_seq}"
        )
        headers = {
            **base_headers,
            "Referer": referer,
            "Accept": "text/csv,application/vnd.ms-excel,application/octet-stream,*/*",
        }
        if csrf_token:
            headers[csrf_header] = csrf_token
        for method in ("GET", "POST"):
            for download_type in ("C", "F", "X", "E"):
                params = {"downloadType": download_type, "infId": INF_ID, "infSeq": str(inf_seq)}
                if csrf_token:
                    params[csrf.get("_csrf_param", "_csrf")] = csrf_token
                url = f"{BASE}/portal/data/sheet/downloadSheetData.do"
                if method == "GET":
                    r = request_bytes(opener, "GET", url, params=params, headers=headers, timeout=12)
                else:
                    r = request_bytes(opener, "POST", url, data=params, headers=headers, timeout=12)
                manifest.append(
                    save_probe(
                        f"sheet_{method.lower()}_seq{inf_seq}_type{download_type}",
                        r,
                        {"inf_seq": inf_seq, "method": method, "download_type": download_type},
                    )
                )

    # Try file download with plausible fileSeq values.  We do not assume success;
    # the goal is to identify whether the button flow can be reproduced by HTTP.
    for inf_seq in (1, 2, 3):
        csrf = csrf_by_seq.get(inf_seq, csrf_by_seq.get(1, {}))
        csrf_token = csrf.get("_csrf", "")
        csrf_header = csrf.get("_csrf_header", "X-CSRF-TOKEN")
        referer = f"{BASE}/portal/data/service/selectServicePage.do?infId={INF_ID}&infSeq={inf_seq}"
        headers = {
            **base_headers,
            "Referer": referer,
            "Accept": "application/octet-stream,text/csv,application/vnd.ms-excel,*/*",
            "Origin": BASE,
        }
        if csrf_token:
            headers[csrf_header] = csrf_token
        for file_seq in range(1, 16):
            data = {
                "infId": INF_ID,
                "infSeq": str(inf_seq),
                "fileSeq": str(file_seq),
                "fileSize": "0",
                "srvCd": "F",
            }
            if csrf_token:
                data[csrf.get("_csrf_param", "_csrf")] = csrf_token
            r = request_bytes(
                opener,
                "POST",
                f"{BASE}/portal/service/fileDownload.do",
                data=data,
                headers=headers,
                timeout=12,
            )
            manifest.append(
                save_probe(
                    f"file_post_seq{inf_seq}_file{file_seq}",
                    r,
                    {"inf_seq": inf_seq, "file_seq": file_seq, "method": "POST"},
                )
            )
            if classify(r["content"], r["headers"]) in {"zip_or_xlsx", "gzip", "csv_like", "large_unknown_possible_data"}:
                # Continue a few probes is unnecessary once a data-like response appears.
                break

    out = OUT_DIR / "gg_bus_download_probe_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "total_probes": len(manifest),
        "class_counts": {},
        "possible_data": [
            {
                "name": r["name"],
                "status_code": r["status_code"],
                "bytes": r["bytes"],
                "classification": r["classification"],
                "content_type": r["content_type"],
                "content_disposition": r["content_disposition"],
                "body_path": r["body_path"],
            }
            for r in manifest
            if r["classification"] in {"zip_or_xlsx", "gzip", "csv_like", "large_unknown_possible_data"}
        ],
    }
    for rec in manifest:
        summary["class_counts"][rec["classification"]] = summary["class_counts"].get(rec["classification"], 0) + 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"manifest={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
