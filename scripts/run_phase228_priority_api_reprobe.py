#!/usr/bin/env python3
"""Phase228: priority residual API reprobe.

Reprobe APIs that could reduce remaining 20%+ precision residuals:

* broadcasting industry survey for J60;
* life insurance join status and automobile insurance contract information for
  K66/K65 context.

The script stores only response metadata and row samples without exposing API
keys.  It does not adopt indicators unless city-level, 2023-compatible rows are
available.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase228_priority_api_reprobe"
OUT = ROOT / "data" / "processed" / "phase228_priority_api_reprobe"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase228_priority_api_reprobe.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def service_key(env: dict[str, str]) -> str:
    for key in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING"):
        if env.get(key):
            return env[key]
    return ""


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def fetch_json(url: str, params: dict[str, str], name: str) -> dict[str, Any]:
    safe_params = {k: v for k, v in params.items() if k != "serviceKey"}
    out: dict[str, Any] = {"name": name, "url": url, "params": safe_params}
    full = url + "?" + urllib.parse.urlencode(params, doseq=True, safe="%")
    try:
        with urllib.request.urlopen(full, timeout=20) as resp:
            body = resp.read()
            out["http_status"] = getattr(resp, "status", None)
            out["content_type"] = resp.headers.get("Content-Type", "")
            out["bytes"] = len(body)
            text = body.decode("utf-8", errors="replace")
            out["body_head"] = text[:500]
            try:
                out["json"] = json.loads(text)
            except Exception:
                out["json"] = None
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    (RAW / f"{name}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def extract_items(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    body = data.get("response", {}).get("body", data.get("body", {}))
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    return items if isinstance(items, list) else []


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    env = load_env()
    key = service_key(env)

    probes = []
    if not key:
        probes.append({"name": "all", "error": "DATA_GO_KR_DECODING/ENCODING key missing"})
    else:
        probes.append(
            fetch_json(
                "http://apis.data.go.kr/1570100/KccBisiInfoService/getMediastat",
                {"serviceKey": key, "pageNo": "1", "numOfRows": "10", "resultType": "json"},
                "broadcast_mediastat",
            )
        )
        probes.append(
            fetch_json(
                "http://apis.data.go.kr/1160100/service/GetFPLifeInsuJoinInfoService/getLifeInsuJoinStatus",
                {"serviceKey": key, "pageNo": "1", "numOfRows": "100", "resultType": "json", "likeSttsAccmlTrgtYr": "2023"},
                "life_insurance_2023",
            )
        )
        probes.append(
            fetch_json(
                "http://apis.data.go.kr/1160100/service/GetFPAtmbInsujoinInfoService/getContractInfo",
                {"serviceKey": key, "pageNo": "1", "numOfRows": "100", "resultType": "json", "likeIsuCmpyOfrYm": "2023"},
                "auto_insurance_contract_2023",
            )
        )

    rows = []
    samples = {}
    for p in probes:
        data = p.get("json")
        items = extract_items(data)
        samples[p["name"]] = items[:5]
        cols = sorted({k for item in items[:20] for k in item.keys()}) if items else []
        body = data.get("response", {}).get("body", {}) if isinstance(data, dict) else {}
        header = data.get("response", {}).get("header", {}) if isinstance(data, dict) else {}
        text = (p.get("body_head") or "") + " " + json.dumps(header, ensure_ascii=False)
        area_cols = [c for c in cols if any(tok in c.lower() for tok in ["area", "rgn", "sido", "sigungu", "ctprvn", "signgu"]) or any(tok in c for tok in ["지역", "시도", "시군구"])]
        year_cols = [c for c in cols if "yr" in c.lower() or "year" in c.lower() or "년도" in c or "연도" in c]
        rows.append(
            {
                "자료": p["name"],
                "HTTP": p.get("http_status", ""),
                "오류": p.get("error", ""),
                "resultCode": header.get("resultCode", ""),
                "resultMsg": header.get("resultMsg", ""),
                "totalCount": body.get("totalCount", ""),
                "sample_rows": len(items),
                "지역필드후보": ", ".join(area_cols),
                "연도필드후보": ", ".join(year_cols),
                "2023직접성": "가능성" if items and ("2023" in json.dumps(items[:20], ensure_ascii=False)) else "미확인",
                "채택판정": "후속파싱필요" if items and area_cols else "직접채택불가",
            }
        )
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "phase228_api_reprobe_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "phase228_api_samples.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "git_hash": git_hash(),
                "inputs": [".env: DATA_GO_KR_DECODING/ENCODING only, value not stored in outputs"],
                "outputs": ["phase228_api_reprobe_summary.csv", "phase228_api_samples.json"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    REPORT.write_text(
        f"""# Phase228 잔여 고오차 우선 API 재시도

생성시각: {CREATED_AT}

## 목적

고양·포항 잔여 20% 초과 업종 중 `방송업(J60)`과 `금융 및 보험 관련 서비스업(K66)`에 직접 연결될 수 있는 API를 재호출했다. API 키 값은 저장하지 않았다.

## 재시도 결과

{md_table(summary, 2)}

## 해석

- `sample_rows`가 0이거나 지역필드 후보가 없으면 고양·포항 시군구 정밀화에는 바로 사용할 수 없다.
- 지역필드가 있어도 시도 단위에 그치면 고양·포항 직접 배분에는 약하다.
- 2023년 행과 시군구/사업자 소재지/매출·보험료·계약금액 계열 필드가 동시에 있어야 Phase229 정밀화 후보가 된다.
""",
        encoding="utf-8",
    )
    print(summary.to_string(index=False))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
