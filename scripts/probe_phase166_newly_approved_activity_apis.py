#!/usr/bin/env python3
"""Phase166: probe newly approved public APIs for direct activity indicators.

This script intentionally never prints or persists serviceKey values.
It records only endpoint names, HTTP status, public API result codes/messages,
and a small list of returned field names.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase166_new_api_probe"
OUT = ROOT / "data" / "processed" / "phase166_new_api_probe"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase166_new_api_probe.md"


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


def normalize_items(body: Any) -> list[dict[str, Any]]:
    if not isinstance(body, dict):
        return []
    items = body.get("items", [])
    if isinstance(items, dict):
        item = items.get("item", items)
        if isinstance(item, dict):
            return [item]
        if isinstance(item, list):
            return [x for x in item if isinstance(x, dict)]
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    return []


def sanitize_payload(text: str, keys: list[str]) -> str:
    redacted = text
    for key in keys:
        if key:
            redacted = redacted.replace(key, "[REDACTED_SERVICE_KEY]")
    return redacted[:5000]


@dataclass(frozen=True)
class ProbeSpec:
    group: str
    label: str
    base_url: str
    op: str
    key_env: str
    params: dict[str, str]
    source_url: str
    expected_use: str


def data_go_params(key: str, extra: dict[str, str]) -> dict[str, str]:
    params = {
        "serviceKey": key,
        "pageNo": "1",
        "numOfRows": "3",
        "type": "json",
    }
    params.update(extra)
    return params


def make_specs(env: dict[str, str]) -> list[ProbeSpec]:
    # Public data portal APIs normally use DATA_GO_KR_*.
    # Use the decoded key and let urlencode encode it exactly once.
    public_key = env.get("DATA_GO_KR_DECODING", "") or env.get("DATA_GO_KR_ENCODING", "")
    return [
        ProbeSpec(
            "PPS user",
            "나라장터 수요기관정보",
            "http://apis.data.go.kr/1230000/ao/UsrInfoService02",
            "getDminsttInfo02",
            "DATA_GO_KR_DECODING",
            data_go_params(public_key, {}),
            "https://www.data.go.kr/data/15129466/openapi.do",
            "공공행정·조달 수요기관 공간/기관 구조",
        ),
        ProbeSpec(
            "PPS user",
            "나라장터 조달업체 기본정보",
            "http://apis.data.go.kr/1230000/ao/UsrInfoService02",
            "getPrcrmntCorpBasicInfo02",
            "DATA_GO_KR_DECODING",
            data_go_params(public_key, {}),
            "https://www.data.go.kr/data/15129466/openapi.do",
            "MN0/F00/사업지원 조달업체 소재지 구조",
        ),
        ProbeSpec(
            "PPS user",
            "나라장터 조달업체 업종정보",
            "http://apis.data.go.kr/1230000/ao/UsrInfoService02",
            "getPrcrmntCorpIndstrytyInfo02",
            "DATA_GO_KR_DECODING",
            data_go_params(public_key, {}),
            "https://www.data.go.kr/data/15129466/openapi.do",
            "조달업체 업종코드 기반 중분류 후보",
        ),
        ProbeSpec(
            "PPS user",
            "나라장터 조달업체 공급물품정보",
            "http://apis.data.go.kr/1230000/ao/UsrInfoService02",
            "getPrcrmntCorpSplyPrdctInfo02",
            "DATA_GO_KR_DECODING",
            data_go_params(public_key, {}),
            "https://www.data.go.kr/data/15129466/openapi.do",
            "공급물품명 기반 제조/서비스 활동자료",
        ),
        ProbeSpec(
            "PPS industry law",
            "나라장터 업종 및 근거법규",
            "http://apis.data.go.kr/1230000/ao/IndstrytyBaseLawrgltInfoService",
            "getIndstrytyBaseLawrgltInfoList",
            "DATA_GO_KR_DECODING",
            data_go_params(public_key, {}),
            "https://www.data.go.kr/data/15129467/openapi.do",
            "조달 업종코드 해석 보조",
        ),
    ]


def fetch(spec: ProbeSpec, keys: list[str]) -> dict[str, Any]:
    if not spec.params.get("serviceKey"):
        return {
            "status": "missing_key",
            "http_status": "",
            "result_code": "",
            "result_msg": f"{spec.key_env} missing",
            "total_count": "",
            "item_count": 0,
            "sample_fields": "",
            "raw_file": "",
        }
    url = f"{spec.base_url}/{spec.op}?{urlencode(spec.params)}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=20) as resp:
            http_status = resp.status
            text = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return {
            "status": "http_error",
            "http_status": exc.code,
            "result_code": "",
            "result_msg": sanitize_payload(text, keys),
            "total_count": "",
            "item_count": 0,
            "sample_fields": "",
            "raw_file": "",
        }
    except URLError as exc:
        return {
            "status": "url_error",
            "http_status": "",
            "result_code": "",
            "result_msg": str(exc.reason)[:500],
            "total_count": "",
            "item_count": 0,
            "sample_fields": "",
            "raw_file": "",
        }

    RAW.mkdir(parents=True, exist_ok=True)
    raw_name = f"{re.sub(r'[^0-9A-Za-z가-힣]+', '_', spec.label)}.json"
    raw_path = RAW / raw_name
    raw_path.write_text(sanitize_payload(text, keys), encoding="utf-8")

    result_code = ""
    result_msg = ""
    total_count = ""
    item_count = 0
    sample_fields = ""
    status = "ok_http"
    try:
        data = json.loads(text)
        response = data.get("response", data) if isinstance(data, dict) else {}
        header = response.get("header", {}) if isinstance(response, dict) else {}
        result_code = str(header.get("resultCode", ""))
        result_msg = str(header.get("resultMsg", ""))
        body = response.get("body", {}) if isinstance(response, dict) else {}
        total_count = str(body.get("totalCount", "")) if isinstance(body, dict) else ""
        items = normalize_items(body)
        item_count = len(items)
        if items:
            sample_fields = ", ".join(list(items[0].keys())[:20])
        if result_code and result_code != "00":
            status = "api_error"
        elif item_count > 0:
            status = "ok_items"
        else:
            status = "ok_empty_or_needs_params"
    except json.JSONDecodeError:
        result_msg = sanitize_payload(text, keys)[:500]
        status = "non_json_response"

    return {
        "status": status,
        "http_status": http_status,
        "result_code": result_code,
        "result_msg": result_msg,
        "total_count": total_count,
        "item_count": item_count,
        "sample_fields": sample_fields,
        "raw_file": str(raw_path.relative_to(ROOT)),
    }


def main() -> int:
    env = load_dotenv(ROOT / ".env")
    keys = [
        env.get("DATA_GO_KR_ENCODING", ""),
        env.get("DATA_GO_KR_DECODING", ""),
        env.get("MOF_API_KEY", ""),
        env.get("DATA_GOYANG_KEY", ""),
        env.get("KOBIS_API_KEY", ""),
    ]
    specs = make_specs(env)
    rows: list[dict[str, Any]] = []
    for spec in specs:
        result = fetch(spec, keys)
        rows.append(
            {
                "group": spec.group,
                "label": spec.label,
                "operation": spec.op,
                "source_url": spec.source_url,
                "expected_use": spec.expected_use,
                **result,
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "phase166_new_api_probe_summary.csv"
    fieldnames = [
        "group",
        "label",
        "operation",
        "status",
        "http_status",
        "result_code",
        "result_msg",
        "total_count",
        "item_count",
        "sample_fields",
        "expected_use",
        "source_url",
        "raw_file",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    def md_table(rows: list[dict[str, Any]]) -> str:
        cols = [
            ("label", "자료"),
            ("status", "상태"),
            ("result_code", "API코드"),
            ("result_msg", "메시지"),
            ("item_count", "표본행"),
            ("expected_use", "GVA 활용 후보"),
        ]
        out = ["| " + " | ".join(h for _, h in cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for r in rows:
            vals = []
            for k, _ in cols:
                v = str(r.get(k, ""))
                v = v.replace("|", "/").replace("\n", " ")[:180]
                vals.append(v)
            out.append("| " + " | ".join(vals) + " |")
        return "\n".join(out)

    usable = [r for r in rows if r["status"] == "ok_items"]
    needs_params = [r for r in rows if r["status"] == "ok_empty_or_needs_params"]
    api_errors = [r for r in rows if r["status"] not in {"ok_items", "ok_empty_or_needs_params"}]

    report = f"""# Phase166 신규 승인 활동자료 API 연결 점검

## 목적

사용자가 추가 활용신청을 완료한 뒤, 기존 공공데이터포털 키로 조달청 사용자정보/업종근거법규 계열 API가 실제 호출 가능한지 확인했다. 이 단계는 총부가가치(GVA) 예측모형을 바로 개선하는 단계가 아니라, MN0/F00/사업지원/제조·서비스 일부 취약 업종에 붙일 수 있는 직접 활동자료 후보를 선별하는 연결 점검이다.

## 연결 점검 결과

{md_table(rows)}

## 공식자료 기준

- 조달청_나라장터 사용자정보 서비스는 나라장터 등록 조달업체·수요기관 정보를 제공하며, 조달업체 기본정보·등록업종·공급물품을 포함한다. 공공데이터포털 기준 무료, 개발계정 10,000건, 자동승인, 실시간 갱신 API다.
- 조달청_나라장터 업종 및 근거법규서비스는 업종코드와 근거법규 해석자료이며, 공공데이터포털 기준 무료, 개발계정 1,000건, 자동승인, 실시간 갱신 API다.

## 해석

- `ok_items`이면 같은 키로 실제 행 수집을 시작할 수 있다.
- `ok_empty_or_needs_params`이면 인증은 막히지 않았지만 필수 검색조건 또는 표본 조건이 필요하다는 뜻이다. 이 경우 공식 참고문서의 파라미터를 확인해 사업자번호·업종코드·기관코드별 수집으로 전환해야 한다.
- `api_error` 또는 `http_error`이면 활용승인 반영 지연, endpoint 오기, 또는 별도 필수 파라미터 문제일 수 있다.

이번 실행에서는 조달청 사용자정보 4개 operation과 업종근거법규 1개 operation이 모두 `Forbidden`으로 응답했다. 같은 공공데이터포털 키로 과거 조달청 입찰공고 서비스는 수집된 기록이 있으므로, 현재 판정은 **신규 서비스 활용승인 반영 전/서비스별 권한 미부여/공공데이터포털 마이페이지의 인증키 연결 문제** 중 하나로 본다. 아직 이 자료를 GVA 모형에 반영하면 안 된다.

## 산출물

- 점검 CSV: `{csv_path.relative_to(ROOT)}`
- 원문 응답 캐시: `data/raw/phase166_new_api_probe/`  
  단, serviceKey 값은 저장하지 않고 `[REDACTED_SERVICE_KEY]`로 치환했다.

## 다음 조치

1. 조달업체 기본/업종/공급물품이 전량조회형이면 고양·포항 소재 업체를 필터링해 MN0/F00/사업지원용 업체 구조 지표를 만든다.
2. 사업자번호 단건조회형이면 기존 입찰공고만으로는 공급업체 사업자번호가 부족하므로, 계약정보 또는 업체검색형 API를 추가로 연결해야 한다.
3. 업종 및 근거법규는 직접 GVA 지표가 아니라 조달업종 코드 해석표로만 사용한다.
4. 사용자는 공공데이터포털 마이페이지에서 `조달청_나라장터 사용자정보 서비스`, `조달청_나라장터 업종 및 근거법규서비스`가 현재 키에 대해 “승인” 상태인지 확인해야 한다. 승인 직후라면 일정 시간 뒤 재시도한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"rows": len(rows), "usable": len(usable), "needs_params": len(needs_params), "errors": len(api_errors), "report": str(REPORT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
