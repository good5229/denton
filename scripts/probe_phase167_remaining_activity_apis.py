#!/usr/bin/env python3
"""Phase167: probe remaining free/public direct-activity candidate APIs.

Scope:
- HIRA non-payment/treatment material APIs for Q86 health-service signals.
- KECO waste/recycling APIs for E38/E39/ERS environmental-service signals.
- MOIS international logistics forwarders for H52 logistics-service signals.
- ODCloud health insurance annual file API as a low-resolution national-only check.

The script redacts service keys in every persisted response.
"""

from __future__ import annotations

import csv
import json
import os
import re
import ssl
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase167_remaining_activity_api_probe"
OUT = ROOT / "data" / "processed" / "phase167_remaining_activity_api_probe"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase167_remaining_activity_api_probe.md"


def load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, value = s.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


@dataclass(frozen=True)
class ProbeSpec:
    group: str
    label: str
    url: str
    params: dict[str, str]
    key_param: str
    source_url: str
    gva_target: str
    use_note: str


def specs(env: dict[str, str]) -> list[ProbeSpec]:
    key = env.get("DATA_GO_KR_DECODING", "") or env.get("DATA_GO_KR_ENCODING", "")
    return [
        ProbeSpec(
            "HIRA",
            "비급여 항목 코드",
            "http://apis.data.go.kr/B551182/nonPaymentDamtInfoService/getNonPaymentItemCodeList",
            {"pageNo": "1", "numOfRows": "5"},
            "ServiceKey",
            "https://www.data.go.kr/data/15001700/openapi.do",
            "Q86 보건업",
            "비급여 항목 분류표. 지역 금액이 아니라 의료서비스 가격/항목 구조 보조.",
        ),
        ProbeSpec(
            "HIRA",
            "비급여 병원별 가격정보",
            "http://apis.data.go.kr/B551182/nonPaymentDamtInfoService/getNonPaymentItemHospDtlList",
            {"pageNo": "1", "numOfRows": "5", "sidoCd": "310000", "sgguCd": "311040"},
            "ServiceKey",
            "https://www.data.go.kr/data/15001700/openapi.do",
            "Q86 보건업",
            "시군구 의료기관 가격·항목 분포 후보. 총진료비 actual은 아니므로 금액가중 보조에 한정.",
        ),
        ProbeSpec(
            "HIRA",
            "치료재료 급여비급여 목록",
            "http://apis.data.go.kr/B551182/mcatInfoService1.2/getPaymentNonPaymentList1.2",
            {"pageNo": "1", "numOfRows": "5"},
            "ServiceKey",
            "https://www.data.go.kr/data/3074384/openapi.do",
            "Q86 보건업/C21 의료물질",
            "치료재료 가격·분류 보조. 지역 활동량은 아님.",
        ),
        ProbeSpec(
            "KECO",
            "폐기물 처리업체 정보",
            "http://apis.data.go.kr/B552584/kecoapi/wstdspBzentyService/getWstdspBzentyInfo",
            {"pageNo": "1", "numOfRows": "5", "type": "json"},
            "serviceKey",
            "https://www.data.go.kr/data/15141649/openapi.do",
            "E38/E39/ERS",
            "사업장폐기물 처리업체 업종·전문분야·주소·관할청. 공간구조 보조.",
        ),
        ProbeSpec(
            "KECO",
            "폐기물처분부담금 시군구 정보",
            "http://apis.data.go.kr/B552584/kecoapi/WstDsfService/getWstDsfSggInfo",
            {"pageNo": "1", "numOfRows": "5", "type": "json"},
            "serviceKey",
            "https://www.data.go.kr/data/15125003/openapi.do",
            "E38/E39",
            "시군구 코드/폐기물처분부담금 관련 구조. 처리량 직접자료 여부 확인.",
        ),
        ProbeSpec(
            "KECO",
            "재활용가능자원 가격조사",
            "http://apis.data.go.kr/B552584/reutilMrktPrcExmn/getlist",
            {"pageNo": "1", "numOfRows": "5", "type": "json"},
            "serviceKey",
            "https://www.data.go.kr/data/15156640/openapi.do",
            "E38/제조 원자재 보조",
            "월별 권역 가격. 시군구 수량은 아니나 recycling/철스크랩 가격 시간축 후보.",
        ),
        ProbeSpec(
            "MOIS",
            "기타 국제물류주선업",
            "http://apis.data.go.kr/1741000/international_logistics_forwarders/info",
            {"pageNo": "1", "numOfRows": "5", "returnType": "json"},
            "serviceKey",
            "https://www.data.go.kr/en/data/15155056/openapi.do",
            "H52 운송관련 서비스",
            "전국 허가업체 주소·영업상태·인허가일. 시군구 공간구조 보조.",
        ),
        ProbeSpec(
            "ODCloud",
            "건강보험 보험료 및 요양급여 급여액",
            "https://api.odcloud.kr/api/15127753/v1/uddi:cfe30abb-7b7b-441a-b8fd-d0b92218bc36",
            {"page": "1", "perPage": "5", "returnType": "JSON"},
            "serviceKey",
            "https://www.data.go.kr/data/15127753/fileData.do",
            "Q86 보건업",
            "전국 연간 22행 수준. 시군구/월 GVA 개선에는 부적합할 가능성 높음.",
        ),
    ]


def build_urls(spec: ProbeSpec, env: dict[str, str]) -> list[tuple[str, str]]:
    decoded = env.get("DATA_GO_KR_DECODING", "")
    encoded = env.get("DATA_GO_KR_ENCODING", "")
    out: list[tuple[str, str]] = []
    base_urls = [spec.url]
    if spec.url.startswith("http://apis.data.go.kr/"):
        base_urls.append("https://" + spec.url[len("http://"):])
    for base_url in base_urls:
        scheme_tag = "https" if base_url.startswith("https://") else "http"
        if decoded:
            params = {spec.key_param: decoded, **spec.params}
            out.append((f"{scheme_tag}_decoded_urlencode", base_url + "?" + urlencode(params)))
        if encoded:
            # Keep already encoded public-data keys raw; other params are encoded.
            qs = spec.key_param + "=" + encoded
            if spec.params:
                qs += "&" + urlencode(spec.params)
            out.append((f"{scheme_tag}_encoded_raw", base_url + "?" + qs))
    return out


def redact(text: str, env: dict[str, str]) -> str:
    out = text
    for name in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING", "MOF_API_KEY", "DATA_GOYANG_KEY", "KOBIS_API_KEY"):
        value = env.get(name, "")
        if value:
            out = out.replace(value, "[REDACTED_SERVICE_KEY]")
    return out


def parse_response(text: str, content_type: str) -> dict[str, Any]:
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(text)
        if isinstance(data, dict):
            if "response" in data:
                response = data.get("response", {})
                header = response.get("header", {}) if isinstance(response, dict) else {}
                body = response.get("body", {}) if isinstance(response, dict) else {}
                items = body.get("items", []) if isinstance(body, dict) else []
                if isinstance(items, dict):
                    item = items.get("item", items)
                    item_count = len(item) if isinstance(item, list) else (1 if isinstance(item, dict) else 0)
                    sample_fields = ", ".join(list(item[0].keys())[:20]) if isinstance(item, list) and item else (", ".join(item.keys()) if isinstance(item, dict) else "")
                elif isinstance(items, list):
                    item_count = len(items)
                    sample_fields = ", ".join(list(items[0].keys())[:20]) if items and isinstance(items[0], dict) else ""
                else:
                    item_count = 0
                    sample_fields = ""
                return {
                    "result_code": str(header.get("resultCode", "")),
                    "result_msg": str(header.get("resultMsg", "")),
                    "total_count": str(body.get("totalCount", "")) if isinstance(body, dict) else "",
                    "item_count": item_count,
                    "sample_fields": sample_fields,
                }
            if "data" in data:
                arr = data.get("data", [])
                return {
                    "result_code": str(data.get("currentCount", "")),
                    "result_msg": "ODCloud JSON",
                    "total_count": str(data.get("totalCount", "")),
                    "item_count": len(arr) if isinstance(arr, list) else 0,
                    "sample_fields": ", ".join(list(arr[0].keys())[:20]) if isinstance(arr, list) and arr and isinstance(arr[0], dict) else "",
                }
        return {"result_code": "", "result_msg": "JSON parsed", "total_count": "", "item_count": 0, "sample_fields": ""}

    root = ET.fromstring(text.encode("utf-8"))
    def txt(path: str) -> str:
        node = root.find(path)
        return node.text.strip() if node is not None and node.text else ""
    items = root.findall(".//item")
    fields = ""
    if items:
        fields = ", ".join([child.tag for child in list(items[0])[:20]])
    return {
        "result_code": txt(".//resultCode"),
        "result_msg": txt(".//resultMsg"),
        "total_count": txt(".//totalCount"),
        "item_count": len(items),
        "sample_fields": fields,
    }


def fetch_one(label: str, url: str, env: dict[str, str], timeout: int = 20) -> tuple[dict[str, Any], str]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl._create_unverified_context()
    try:
        kwargs: dict[str, Any] = {"timeout": timeout}
        if url.startswith("https://"):
            kwargs["context"] = ctx
        with urlopen(req, **kwargs) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = parse_response(raw, resp.headers.get("Content-Type", ""))
            return {
                "status": "ok_items" if parsed.get("item_count", 0) else "ok_empty_or_needs_params",
                "http_status": resp.status,
                **parsed,
            }, raw
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {
            "status": "http_error",
            "http_status": exc.code,
            "result_code": "",
            "result_msg": raw[:500],
            "total_count": "",
            "item_count": 0,
            "sample_fields": "",
        }, raw
    except URLError as exc:
        return {
            "status": "url_error",
            "http_status": "",
            "result_code": "",
            "result_msg": str(exc.reason)[:500],
            "total_count": "",
            "item_count": 0,
            "sample_fields": "",
        }, ""
    except Exception as exc:
        return {
            "status": "parse_or_request_error",
            "http_status": "",
            "result_code": "",
            "result_msg": f"{type(exc).__name__}: {exc}"[:500],
            "total_count": "",
            "item_count": 0,
            "sample_fields": "",
        }, ""


def safe_name(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "_", text).strip("_")


def md_table(rows: list[dict[str, Any]], cols: list[tuple[str, str]]) -> str:
    out = ["| " + " | ".join(h for _, h in cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        vals = []
        for key, _ in cols:
            val = str(row.get(key, ""))
            vals.append(val.replace("|", "/").replace("\n", " ")[:220])
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def main() -> int:
    env = load_dotenv(ROOT / ".env")
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for spec in specs(env):
        attempts = []
        best: dict[str, Any] | None = None
        best_raw = ""
        best_mode = ""
        for mode, url in build_urls(spec, env):
            result, raw = fetch_one(spec.label, url, env)
            attempts.append({"mode": mode, **result})
            if best is None or result["status"] == "ok_items" or (best["status"] != "ok_items" and result["status"] == "ok_empty_or_needs_params"):
                best = result
                best_raw = raw
                best_mode = mode
            if result["status"] == "ok_items":
                break
        assert best is not None
        raw_file = ""
        if best_raw:
            raw_path = RAW / f"{safe_name(spec.label)}_{best_mode}.txt"
            raw_path.write_text(redact(best_raw[:10000], env), encoding="utf-8")
            raw_file = str(raw_path.relative_to(ROOT))
        rows.append(
            {
                "group": spec.group,
                "label": spec.label,
                "status": best["status"],
                "mode": best_mode,
                "http_status": best["http_status"],
                "result_code": best["result_code"],
                "result_msg": str(best["result_msg"]).replace("\n", " "),
                "total_count": best["total_count"],
                "item_count": best["item_count"],
                "sample_fields": best["sample_fields"],
                "gva_target": spec.gva_target,
                "use_note": spec.use_note,
                "source_url": spec.source_url,
                "raw_file": raw_file,
                "attempts": json.dumps(attempts, ensure_ascii=False),
            }
        )

    csv_path = OUT / "phase167_remaining_activity_api_probe_summary.csv"
    fieldnames = [
        "group", "label", "status", "mode", "http_status", "result_code", "result_msg",
        "total_count", "item_count", "sample_fields", "gva_target", "use_note", "source_url", "raw_file", "attempts",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    usable = [r for r in rows if r["status"] == "ok_items"]
    weak = [r for r in rows if r["status"] == "ok_empty_or_needs_params"]
    blocked = [r for r in rows if r["status"] not in {"ok_items", "ok_empty_or_needs_params"}]

    report = f"""# Phase167 잔여 직접 활동자료 API 연결 점검

## 목적

조달청 사용자정보가 현재 `Forbidden`으로 막힌 상태에서, 남아 있는 무료·공개 직접 활동자료 후보가 실제로 호출 가능한지 점검했다. 목표는 고양시·포항시 중분류 GVA 취약 업종에 대해 “실제 GVA”가 아닌 **배분근거/활동자료**로 사용할 수 있는 자료를 찾는 것이다.

## 점검 결과

{md_table(rows, [
    ("label", "자료"),
    ("status", "상태"),
    ("result_msg", "메시지"),
    ("total_count", "총건수"),
    ("item_count", "표본행"),
    ("gva_target", "대상 GVA 업종"),
    ("use_note", "활용 판정"),
])}

## 즉시 활용 가능 후보

{md_table(usable, [
    ("label", "자료"),
    ("total_count", "총건수"),
    ("sample_fields", "주요 필드"),
    ("gva_target", "대상"),
    ("use_note", "활용 방식"),
]) if usable else "현재 실행에서 바로 행을 받은 후보는 없다."}

## 주의가 필요한 후보

{md_table(weak + blocked, [
    ("label", "자료"),
    ("status", "상태"),
    ("result_msg", "메시지"),
    ("use_note", "주의"),
])}

## 산출물

- 점검 CSV: `{csv_path.relative_to(ROOT)}`
- 원문 응답 캐시: `data/raw/phase167_remaining_activity_api_probe/`
- 캐시는 serviceKey를 저장하지 않도록 치환했다.

## 다음 모델링 판정

1. `ok_items`인 자료만 다음 GVA 실험 후보로 이동한다.
2. Q86 보건업은 비급여 가격/항목 자료가 열리더라도 총진료비·부가가치 actual이 아니므로, 병원 수·종별·가격분포를 결합한 보조지표로만 사용한다.
3. E38/E39/ERS는 폐기물 처리업체·처리시설·가격이 열리면 공간구조/월 시간축 후보로 사용할 수 있다. 단 처리량이 없는 업체 목록만으로는 금액 예측력이 제한된다.
4. H52 물류는 국제물류주선업 허가업체 주소·상태를 공간구조 후보로 쓰되, 운송량/매출이 아니므로 수상운송·항만 물동량과 구분해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"rows": len(rows), "usable": len(usable), "weak": len(weak), "blocked": len(blocked), "report": str(REPORT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
