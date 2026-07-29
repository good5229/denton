#!/usr/bin/env python3
"""Phase257: no-raw PPS API smoke check after approval/key updates.

This script intentionally does not write API response bodies or raw pages.  It
only checks whether the previously blocked PPS contract/bid endpoints are
reachable and records redacted status in a markdown report.
"""

from __future__ import annotations

import json
import os
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase257_pps_api_smoke.md"
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
    for name in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING", "PUBLIC_DATA_API_KEY", "DATA_GO_API_KEY", "SERVICE_KEY"):
        val = os.environ.get(name)
        if val:
            return val
    raise SystemExit("public data API key missing in .env")


def redact(text: str, key: str) -> str:
    return text.replace(key, "[REDACTED_DATA_GO_KR_KEY]")


def body_header_sample(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"parse": "not_json", "sample": text[:240]}
    response = data.get("response") if isinstance(data, dict) else None
    header = response.get("header") if isinstance(response, dict) else None
    body = response.get("body") if isinstance(response, dict) else None
    return {
        "parse": "json",
        "resultCode": "" if not isinstance(header, dict) else str(header.get("resultCode", "")),
        "resultMsg": "" if not isinstance(header, dict) else str(header.get("resultMsg", "")),
        "totalCount": "" if not isinstance(body, dict) else str(body.get("totalCount", "")),
        "sample": text[:240],
    }


def check(name: str, url: str, params: dict[str, object], key: str) -> dict[str, Any]:
    req = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    ctx = ssl._create_unverified_context() if url.startswith("https://") else None
    out: dict[str, Any] = {"check": name, "endpoint": url.rsplit("/", 1)[-1], "raw_saved": False}
    try:
        with urlopen(req, timeout=20, context=ctx) as resp:
            text = redact(resp.read(2000).decode("utf-8", errors="replace"), key)
            out.update({"http_status": getattr(resp, "status", ""), "http_error": "", "error": ""})
            out.update(body_header_sample(text))
    except HTTPError as exc:
        out.update({"http_status": "", "http_error": exc.code, "error": str(exc.reason), "parse": "", "sample": ""})
    except URLError as exc:
        out.update({"http_status": "", "http_error": "", "error": repr(exc), "parse": "", "sample": ""})
    except Exception as exc:  # noqa: BLE001
        out.update({"http_status": "", "http_error": "", "error": repr(exc), "parse": "", "sample": ""})
    return out


def md_table(rows: list[dict[str, Any]]) -> str:
    cols = ["check", "endpoint", "http_status", "http_error", "resultCode", "resultMsg", "totalCount", "raw_saved", "error"]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")).replace("|", "/") for c in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    key = service_key()
    checks = [
        (
            "pps_contract_20161001_n1",
            "https://apis.data.go.kr/1230000/ao/CntrctInfoService/getCntrctInfoListCnstwk",
            {
                "serviceKey": key,
                "pageNo": 1,
                "numOfRows": 1,
                "type": "json",
                "inqryDiv": "1",
                "inqryBgnDt": "201610010000",
                "inqryEndDt": "201610012359",
            },
        ),
        (
            "pps_bid_202108_page34_n100",
            "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk",
            {
                "serviceKey": key,
                "pageNo": 34,
                "numOfRows": 100,
                "type": "json",
                "inqryDiv": "1",
                "inqryBgnDt": "202108010000",
                "inqryEndDt": "202108312359",
            },
        ),
    ]
    rows = [check(name, url, params, key) for name, url, params in checks]
    api_reachable = all(str(r.get("http_status")) == "200" and not r.get("http_error") for r in rows)
    route_status = "blocked_for_route_adoption_until_complete_months" if api_reachable else "blocked_by_api_or_rate_limit"
    report = f"""# Phase257 조달청 PPS API smoke 재시도

생성시각: {CREATED_AT}

## 목적

사용자가 공공데이터포털 활용신청/키 상태를 갱신한 뒤, 기존에 막혔던 조달청 공사계약·공사공고 API가 다시 접근 가능한지만 극소량으로 확인했다. 이 smoke는 raw 페이지를 저장하지 않으며, 건설업 route 성능검증이나 채택 근거가 아니다.

## 호출 결과

{md_table(rows)}

## 판정

- API 접근 판정: `{route_status}`
- 공사계약: 20161001 하루, 1행 요청만 수행. 성공해도 201610 월 전체 수집 완료가 아니다.
- 공사공고: 202108 page 34, 100행 요청만 수행. 성공해도 202108은 92/92 page 완전월 전까지 성능검증에서 제외한다.
- raw 저장 여부: 모든 호출 `False`.
- route 사용 여부: 변경 없음. PPS 계약은 quality complete 월만, PPS 공사공고는 완전월만 rolling 검증에 투입한다.

## 후속 기준

1. smoke가 성공하면 202108 공사공고는 page 34 단일 저장 → completeness 재감사 → 작은 page chunk 순으로만 확장한다.
2. 계약정보는 201610 월 전체 또는 일별 split이 complete될 때까지 건설업 전국 route 채택에 쓰지 않는다.
3. 부분월·부분 page는 성능표, route ranking, 포스터/대외 주장에 사용하지 않는다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(md_table(rows))


if __name__ == "__main__":
    main()
