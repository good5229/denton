#!/usr/bin/env python3
"""Phase181: probe newly approved high-priority public activity APIs.

The probe is intentionally small:
- no bulk collection;
- never prints or persists serviceKey values;
- records only connection status, API result messages, counts and sample fields.
"""

from __future__ import annotations

import csv
import json
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
RAW = ROOT / "data" / "raw" / "phase181_priority_public_activity_api_probe"
OUT = ROOT / "data" / "processed" / "phase181_priority_public_activity_api_probe"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase181_priority_public_activity_api_probe.md"


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
    priority: str


def specs() -> list[ProbeSpec]:
    return [
        ProbeSpec(
            group="Factory",
            label="한국산업단지공단 공장등록 생산정보 목록",
            url="http://apis.data.go.kr/B550624/fctryRegistInfo/getFctryPrdctnList",
            params={"pageNo": "1", "numOfRows": "5", "type": "json"},
            key_param="serviceKey",
            source_url="https://www.data.go.kr/data/15087611/openapi.do",
            gva_target="C00 제조업 중분류/소분류",
            use_note="품목·생산정보가 실제로 열리면 제조업 세부 배분근거 후보. 시군구/공장주소 필드 확인 필요.",
            priority="high",
        ),
        ProbeSpec(
            group="Factory",
            label="한국산업단지공단 공장등록 공장 목록 v2",
            url="http://apis.data.go.kr/B550624/fctryRegistInfo/getFctryListV2",
            params={"pageNo": "1", "numOfRows": "5", "type": "json"},
            key_param="serviceKey",
            source_url="https://www.data.go.kr/data/15087611/openapi.do",
            gva_target="C00 제조업 공간 배분",
            use_note="주소·업종·종업원/생산품 필드가 열리면 제조업 공간구조 보조. 생산금액 actual은 아님.",
            priority="high",
        ),
        ProbeSpec(
            group="PPS",
            label="조달청 나라장터 공공데이터 개방표준 계약정보",
            url="http://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdCntrctInfo",
            params={"pageNo": "1", "numOfRows": "5", "type": "json"},
            key_param="serviceKey",
            source_url="https://www.data.go.kr/data/15058815/openapi.do",
            gva_target="MN0/F00/사업지원/전문서비스",
            use_note="계약금액·수요기관·계약업체 지역이 열리면 공공수요 의존 업종의 금액형 활동자료 후보.",
            priority="high",
        ),
        ProbeSpec(
            group="PPS",
            label="조달청 나라장터 공공데이터 개방표준 낙찰정보",
            url="http://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdScsbidInfo",
            params={"pageNo": "1", "numOfRows": "5", "type": "json"},
            key_param="serviceKey",
            source_url="https://www.data.go.kr/data/15058815/openapi.do",
            gva_target="MN0/F00/사업지원/전문서비스",
            use_note="낙찰금액·업체명·수요기관이 열리면 계약정보 보완 후보.",
            priority="high",
        ),
        ProbeSpec(
            group="Finance",
            label="금융위원회 금융회사 기본정보",
            url="http://apis.data.go.kr/1160100/service/GetFnCoBasiInfoService/getFnCoOutl",
            params={"pageNo": "1", "numOfRows": "5", "resultType": "json"},
            key_param="serviceKey",
            source_url="https://www.data.go.kr/data/15043232/openapi.do",
            gva_target="K00 금융·보험",
            use_note="본점·기관 분포 구조자료. 예수금/대출금 같은 금액형 지역 활동자료가 아니면 단독 개선력은 제한.",
            priority="medium",
        ),
        ProbeSpec(
            group="Kwater",
            label="한국수자원공사 하수처리장 일일 수질",
            url="http://apis.data.go.kr/B500001/sewerage/waterQuality/day/daylist",
            params={"pageNo": "1", "numOfRows": "5", "resultType": "json"},
            key_param="serviceKey",
            source_url="https://www.data.go.kr/data/15099046/openapi.do",
            gva_target="E37/E38/ERS 환경·수도",
            use_note="처리장·수질 일자료가 열리면 환경·수도 시간축 보조. 처리량/요금 필드 유무 확인 필요.",
            priority="medium",
        ),
    ]


def candidate_urls(spec: ProbeSpec, env: dict[str, str]) -> list[tuple[str, str]]:
    decoded = env.get("DATA_GO_KR_DECODING", "")
    encoded = env.get("DATA_GO_KR_ENCODING", "")
    urls: list[tuple[str, str]] = []
    bases = [spec.url]
    if spec.url.startswith("http://apis.data.go.kr/"):
        bases.append("https://" + spec.url[len("http://") :])

    for base in bases:
        scheme = "https" if base.startswith("https://") else "http"
        if decoded:
            urls.append((f"{scheme}_decoded_urlencode", base + "?" + urlencode({spec.key_param: decoded, **spec.params})))
        if encoded:
            qs = spec.key_param + "=" + encoded
            if spec.params:
                qs += "&" + urlencode(spec.params)
            urls.append((f"{scheme}_encoded_raw", base + "?" + qs))
    return urls


def redact(text: str, env: dict[str, str]) -> str:
    out = text
    for key_name in [
        "DATA_GO_KR_DECODING",
        "DATA_GO_KR_ENCODING",
        "MOF_API_KEY",
        "DATA_GOYANG_KEY",
        "DATA_GG_KEY",
        "KOBIS_API_KEY",
        "KOSIS_API_KEY",
        "ECOS_API_KEY",
    ]:
        value = env.get(key_name, "")
        if value:
            out = out.replace(value, "[REDACTED_SERVICE_KEY]")
    return out


def parse_response(text: str) -> dict[str, Any]:
    stripped = text.lstrip("\ufeff \t\r\n")
    if not stripped:
        return {"result_code": "", "result_msg": "empty response", "total_count": "", "item_count": 0, "sample_fields": ""}

    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(stripped)
        if isinstance(data, dict):
            response = data.get("response", data)
            if isinstance(response, dict):
                header = response.get("header", {})
                body = response.get("body", {})
                if not isinstance(header, dict):
                    header = {}
                if not isinstance(body, dict):
                    body = {}
                items = body.get("items", [])
                item = items.get("item", []) if isinstance(items, dict) else items
                if isinstance(item, dict):
                    normalized = [item]
                elif isinstance(item, list):
                    normalized = [x for x in item if isinstance(x, dict)]
                else:
                    normalized = []
                fields = ", ".join(list(normalized[0].keys())[:24]) if normalized else ""
                return {
                    "result_code": str(header.get("resultCode", "")),
                    "result_msg": str(header.get("resultMsg", "")),
                    "total_count": str(body.get("totalCount", "")),
                    "item_count": len(normalized),
                    "sample_fields": fields,
                }
            if "data" in data:
                arr = data.get("data", [])
                fields = ", ".join(list(arr[0].keys())[:24]) if isinstance(arr, list) and arr and isinstance(arr[0], dict) else ""
                return {
                    "result_code": str(data.get("currentCount", "")),
                    "result_msg": "ODCloud-style JSON",
                    "total_count": str(data.get("totalCount", "")),
                    "item_count": len(arr) if isinstance(arr, list) else 0,
                    "sample_fields": fields,
                }

    root = ET.fromstring(stripped.encode("utf-8"))

    def txt(path: str) -> str:
        node = root.find(path)
        return node.text.strip() if node is not None and node.text else ""

    items = root.findall(".//item")
    fields = ", ".join(child.tag for child in list(items[0])[:24]) if items else ""
    return {
        "result_code": txt(".//resultCode"),
        "result_msg": txt(".//resultMsg"),
        "total_count": txt(".//totalCount"),
        "item_count": len(items),
        "sample_fields": fields,
    }


def fetch(url: str) -> tuple[dict[str, Any], str]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    kwargs: dict[str, Any] = {"timeout": 20}
    if url.startswith("https://"):
        kwargs["context"] = ssl._create_unverified_context()
    try:
        with urlopen(req, **kwargs) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            parsed = parse_response(text)
            status = "ok_items" if parsed.get("item_count", 0) else "ok_empty_or_needs_params"
            if parsed.get("result_code") and str(parsed["result_code"]) not in {"00", "0", "NORMAL_CODE", "1"}:
                status = "api_error"
            return {"status": status, "http_status": resp.status, **parsed}, text
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return {
            "status": "http_error",
            "http_status": exc.code,
            "result_code": "",
            "result_msg": text[:600],
            "total_count": "",
            "item_count": 0,
            "sample_fields": "",
        }, text
    except URLError as exc:
        return {
            "status": "url_error",
            "http_status": "",
            "result_code": "",
            "result_msg": str(exc.reason)[:600],
            "total_count": "",
            "item_count": 0,
            "sample_fields": "",
        }, ""
    except Exception as exc:
        return {
            "status": "parse_or_request_error",
            "http_status": "",
            "result_code": "",
            "result_msg": f"{type(exc).__name__}: {exc}"[:600],
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
            value = str(row.get(key, ""))
            vals.append(value.replace("|", "/").replace("\n", " ")[:220])
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def main() -> int:
    env = load_dotenv(ROOT / ".env")
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    for spec in specs():
        attempts: list[dict[str, Any]] = []
        best: dict[str, Any] | None = None
        best_mode = ""
        best_raw = ""
        for mode, url in candidate_urls(spec, env):
            result, raw = fetch(url)
            attempts.append({"mode": mode, **result})
            if best is None:
                best = result
                best_mode = mode
                best_raw = raw
            elif result["status"] == "ok_items":
                best = result
                best_mode = mode
                best_raw = raw
                break
            elif best["status"] not in {"ok_items", "ok_empty_or_needs_params"} and result["status"] == "ok_empty_or_needs_params":
                best = result
                best_mode = mode
                best_raw = raw

        if best is None:
            best = {
                "status": "missing_key",
                "http_status": "",
                "result_code": "",
                "result_msg": "DATA_GO_KR key missing",
                "total_count": "",
                "item_count": 0,
                "sample_fields": "",
            }

        raw_file = ""
        if best_raw:
            raw_path = RAW / f"{safe_name(spec.label)}_{safe_name(best_mode)}.txt"
            raw_path.write_text(redact(best_raw[:12000], env), encoding="utf-8")
            raw_file = str(raw_path.relative_to(ROOT))

        rows.append(
            {
                "group": spec.group,
                "priority": spec.priority,
                "label": spec.label,
                "status": best["status"],
                "mode": best_mode,
                "http_status": best.get("http_status", ""),
                "result_code": best.get("result_code", ""),
                "result_msg": str(best.get("result_msg", "")).replace("\n", " "),
                "total_count": best.get("total_count", ""),
                "item_count": best.get("item_count", 0),
                "sample_fields": best.get("sample_fields", ""),
                "gva_target": spec.gva_target,
                "use_note": spec.use_note,
                "source_url": spec.source_url,
                "raw_file": raw_file,
                "attempts": json.dumps(attempts, ensure_ascii=False),
            }
        )

    csv_path = OUT / "phase181_priority_api_probe_summary.csv"
    fieldnames = [
        "group",
        "priority",
        "label",
        "status",
        "mode",
        "http_status",
        "result_code",
        "result_msg",
        "total_count",
        "item_count",
        "sample_fields",
        "gva_target",
        "use_note",
        "source_url",
        "raw_file",
        "attempts",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    usable = [r for r in rows if r["status"] == "ok_items"]
    weak = [r for r in rows if r["status"] == "ok_empty_or_needs_params"]
    blocked = [r for r in rows if r["status"] not in {"ok_items", "ok_empty_or_needs_params"}]

    report = f"""# Phase181 우선순위 공개 활동자료 API 재점검

## 목적

사용자가 추가 활용신청을 완료한 뒤, Phase180 잔여 취약 블록에 직접적으로 붙일 수 있는 무료·공개 활동자료 API가 실제로 열렸는지 소량 호출로 확인했다. 이 단계는 총부가가치(GVA)를 직접 내려받는 것이 아니라, 제조업·전문서비스·사업지원·금융·환경수도 업종의 **배분근거/시간축 보조지표** 확보 가능성을 판정하는 절차다.

## 점검 결과

{md_table(rows, [
    ("label", "자료"),
    ("status", "상태"),
    ("result_code", "API코드"),
    ("result_msg", "메시지"),
    ("item_count", "표본행"),
    ("gva_target", "대상 업종"),
    ("use_note", "활용 판정"),
])}

## 즉시 수집 가능 후보

{md_table(usable, [
    ("label", "자료"),
    ("total_count", "총건수"),
    ("sample_fields", "표본 필드"),
    ("gva_target", "대상"),
    ("use_note", "활용 방식"),
]) if usable else "이번 실행에서 표본행을 반환한 후보는 없다."}

## 추가 확인 대상

{md_table(weak + blocked, [
    ("label", "자료"),
    ("status", "상태"),
    ("http_status", "HTTP"),
    ("result_msg", "메시지"),
    ("source_url", "출처"),
]) if weak or blocked else "추가 확인 대상 없음."}

## 모델 반영 원칙

1. `ok_items` 후보만 다음 추정모형 입력으로 사용한다.
2. 업체·기관 목록형 자료는 금액형 actual이 아니므로, 단독으로 “정확 예측”을 주장하지 않는다.
3. 계약·생산·처리량처럼 금액 또는 물량 필드가 있는 자료는 중분류/소분류 추정값을 만든 뒤 상위 중분류·대분류 actual 집계와 비교한다.
4. 공표시점이 확인되지 않는 자료는 정밀화 후보로만 두고, 속보성 후보로 쓰지 않는다.

## 산출물

- 점검 CSV: `{csv_path.relative_to(ROOT)}`
- 원문 응답 캐시: `data/raw/phase181_priority_public_activity_api_probe/`
- 캐시는 serviceKey 문자열을 `[REDACTED_SERVICE_KEY]`로 치환했다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"rows": len(rows), "usable": len(usable), "weak": len(weak), "blocked": len(blocked), "report": str(REPORT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
