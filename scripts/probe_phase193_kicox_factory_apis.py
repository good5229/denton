#!/usr/bin/env python3
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
RAW = ROOT / "data" / "raw" / "phase193_kicox_factory_api_probe"
OUT = ROOT / "data" / "processed" / "phase193_kicox_factory_api_probe"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase193_kicox_factory_api_probe.md"


def load_dotenv(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def data_go_keys(env: dict[str, str]) -> list[tuple[str, str, str]]:
    keys = []
    if env.get("DATA_GO_KR_DECODING"):
        keys.append(("DATA_GO_KR_DECODING", env["DATA_GO_KR_DECODING"], "urlencode"))
    if env.get("DATA_GO_KR_ENCODING"):
        keys.append(("DATA_GO_KR_ENCODING", env["DATA_GO_KR_ENCODING"], "raw"))
    return keys


def redact(text: str, env: dict[str, str]) -> str:
    out = text
    for k, v in env.items():
        if any(t in k.upper() for t in ["KEY", "TOKEN"]) and v:
            out = out.replace(v, "[REDACTED_SERVICE_KEY]")
    return out


@dataclass(frozen=True)
class Probe:
    source_id: str
    source_name: str
    source_url: str
    endpoint: str
    params: dict[str, str]
    target: str
    use_note: str


def probes() -> list[Probe]:
    return [
        Probe(
            "kicox_factory_production_posco",
            "공장등록생산정보: 포스코 회사명 검색",
            "https://www.data.go.kr/data/15087611/openapi.do",
            "http://apis.data.go.kr/B550624/fctryRegistInfo/getFctryPrdctnService_v2",
            {"pageNo": "1", "numOfRows": "5", "type": "json", "cmpnyNm": "포스코"},
            "포항 C24/C25/C28/C34",
            "포항 철강·금속·전기장비 관련 대표 기업 필드 확인",
        ),
        Probe(
            "kicox_factory_production_samsung",
            "공장등록생산정보: 삼성전자 회사명 검색",
            "https://www.data.go.kr/data/15087611/openapi.do",
            "http://apis.data.go.kr/B550624/fctryRegistInfo/getFctryPrdctnService_v2",
            {"pageNo": "1", "numOfRows": "5", "type": "json", "cmpnyNm": "삼성전자"},
            "C26/C28 endpoint sanity check",
            "공공데이터포털 샘플성 회사명으로 정상 응답 여부 확인",
        ),
        Probe(
            "kicox_factory_lot_posco",
            "공장등록필지정보: 포스코 회사명 검색",
            "https://www.data.go.kr/data/15087615/openapi.do",
            "http://apis.data.go.kr/B550624/fctryRegistLndpclInfo/getFctryLndpclService",
            {"pageNo": "1", "numOfRows": "5", "type": "json", "cmpnyNm": "포스코"},
            "포항 C24/C25 공간·면적",
            "필지·건축면적 필드 확인",
        ),
        Probe(
            "kicox_factory_lot_samsung",
            "공장등록필지정보: 삼성전자 회사명 검색",
            "https://www.data.go.kr/data/15087615/openapi.do",
            "http://apis.data.go.kr/B550624/fctryRegistLndpclInfo/getFctryLndpclService",
            {"pageNo": "1", "numOfRows": "5", "type": "json", "cmpnyNm": "삼성전자"},
            "endpoint sanity check",
            "공공데이터포털 샘플성 회사명으로 정상 응답 여부 확인",
        ),
    ]


def build_url(endpoint: str, params: dict[str, str], key_value: str, mode: str) -> str:
    clean = dict(params)
    if mode == "raw":
        return endpoint + "?serviceKey=" + key_value + "&" + urlencode(clean)
    return endpoint + "?" + urlencode({"serviceKey": key_value, **clean})


def parse(text: str) -> dict[str, Any]:
    s = text.lstrip("\ufeff \r\n\t")
    if not s:
        return {"result_code": "", "result_msg": "empty", "total_count": "", "item_count": 0, "sample_fields": ""}
    if s.startswith("{"):
        obj = json.loads(s)
        resp = obj.get("response", obj)
        header = resp.get("header", {}) if isinstance(resp, dict) else {}
        body = resp.get("body", {}) if isinstance(resp, dict) else {}
        items = body.get("items", []) if isinstance(body, dict) else []
        item = items.get("item", []) if isinstance(items, dict) else items
        if isinstance(item, dict):
            rows = [item]
        elif isinstance(item, list):
            rows = [x for x in item if isinstance(x, dict)]
        else:
            rows = []
        return {
            "result_code": str(header.get("resultCode", "")),
            "result_msg": str(header.get("resultMsg", "")),
            "total_count": str(body.get("totalCount", "")),
            "item_count": len(rows),
            "sample_fields": ", ".join(list(rows[0].keys())[:40]) if rows else "",
        }
    root = ET.fromstring(s.encode("utf-8"))
    def txt(path: str) -> str:
        node = root.find(path)
        return node.text.strip() if node is not None and node.text else ""
    items = root.findall(".//item")
    return {
        "result_code": txt(".//resultCode"),
        "result_msg": txt(".//resultMsg"),
        "total_count": txt(".//totalCount"),
        "item_count": len(items),
        "sample_fields": ", ".join(child.tag for child in list(items[0])[:40]) if items else "",
    }


def safe_name(label: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", label).strip("_")


def md_table(df: "pd.DataFrame") -> str:
    if df.empty:
        return "_없음_"
    view = df.copy()
    for col in view.columns:
        view[col] = view[col].map(lambda x: "" if x is None else str(x).replace("\n", "<br>").replace("|", "/"))
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    env = load_dotenv(ROOT / ".env")
    keys = data_go_keys(env)
    rows = []
    for spec in probes():
        attempts = []
        best: dict[str, Any] | None = None
        for key_name, key_value, key_mode in keys:
            for scheme_endpoint in [spec.endpoint, "https://" + spec.endpoint[len("http://") :]]:
                mode = f"{scheme_endpoint.split(':', 1)[0]}_{key_name}_{key_mode}"
                url = build_url(scheme_endpoint, spec.params, key_value, key_mode)
                try:
                    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urlopen(req, timeout=20, context=ssl._create_unverified_context()) as resp:
                        raw = resp.read()
                        text = raw.decode("utf-8", errors="replace")
                    parsed = parse(text)
                    status = "ok_items" if parsed["item_count"] else "ok_empty_or_param"
                    result = {"mode": mode, "status": status, "http_status": 200, **parsed}
                    cache = RAW / f"{safe_name(spec.source_id + '_' + mode)}.txt"
                    cache.write_text(redact(text[:20000], env), encoding="utf-8")
                except HTTPError as e:
                    msg = e.read().decode("utf-8", errors="replace")
                    result = {"mode": mode, "status": "http_error", "http_status": e.code, "result_code": "", "result_msg": msg[:300], "total_count": "", "item_count": 0, "sample_fields": ""}
                except (URLError, TimeoutError, Exception) as e:
                    result = {"mode": mode, "status": "url_error", "http_status": "", "result_code": "", "result_msg": str(e)[:300], "total_count": "", "item_count": 0, "sample_fields": ""}
                attempts.append(result)
                if result["status"] == "ok_items":
                    best = result
                    break
            if best:
                break
        if not best and attempts:
            # Prefer reachable mandatory-parameter messages over hard errors.
            best = sorted(attempts, key=lambda r: (r["status"] not in {"ok_empty_or_param"}, r.get("http_status") != 200))[0]
        if not best:
            best = {"mode": "", "status": "missing_key", "http_status": "", "result_code": "", "result_msg": "DATA_GO_KR key missing", "total_count": "", "item_count": 0, "sample_fields": ""}
        rows.append({
            "source_id": spec.source_id,
            "source_name": spec.source_name,
            "status": best["status"],
            "mode": best["mode"],
            "http_status": best["http_status"],
            "result_code": best["result_code"],
            "result_msg": best["result_msg"],
            "total_count": best["total_count"],
            "item_count": best["item_count"],
            "sample_fields": best["sample_fields"],
            "target": spec.target,
            "use_note": spec.use_note,
            "source_url": spec.source_url,
            "attempts": json.dumps(attempts, ensure_ascii=False),
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "phase193_kicox_factory_api_probe_summary.csv", index=False, encoding="utf-8-sig")
    ok = df[df["status"].eq("ok_items")]
    needs = df[~df["status"].eq("ok_items")]
    REPORT.write_text(
        "# Phase193 KICOX 공장등록 API 전용 프로브\n\n"
        "## 목적\n\n"
        "Phase181의 KICOX 구 endpoint 404를 보정하기 위해, 공공데이터포털 문서/공지에 맞춘 생산정보 v2와 필지정보 endpoint를 회사명 조건으로 소량 재점검했다. serviceKey는 캐시와 보고서에 저장하지 않는다.\n\n"
        "## 결과\n\n"
        + md_table(df[["source_name","status","http_status","result_code","result_msg","total_count","item_count","sample_fields","target"]])
        + "\n\n## 즉시 활용 가능\n\n"
        + md_table(ok[["source_name","total_count","sample_fields","target","use_note"]])
        + "\n\n## 추가 조치 필요\n\n"
        + md_table(needs[["source_name","status","http_status","result_msg","source_url"]])
        + "\n\n## 산출물\n\n"
        "- `data/processed/phase193_kicox_factory_api_probe/phase193_kicox_factory_api_probe_summary.csv`\n"
        "- `data/raw/phase193_kicox_factory_api_probe/` 원문 응답 캐시(serviceKey 마스킹)\n",
        encoding="utf-8",
    )
    print(json.dumps({"rows": len(df), "usable": int(len(ok)), "report": str(REPORT)}, ensure_ascii=False))


if __name__ == "__main__":
    import pandas as pd
    main()
