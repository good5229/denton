#!/usr/bin/env python3
"""Search KOSIS for older sigungu GRVA tables covering missing 2019 provinces.

The current 2020 backcast pilot can include only provinces whose cached KOSIS
sigungu annual GRVA table has a 2019 benchmark.  Several 2020-base tables start
at 2020.  This probe searches the KOSIS catalog for older/alternate tables
before deciding that the 2020 pilot cannot be expanded with public API data.

It does not print API keys and only writes catalog metadata.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))
from kosis_common import get_kosis_key  # noqa: E402

OUT = ROOT / "nationwide" / "outputs"
RAW = ROOT / "data" / "raw" / "nationwide_missing_2019_sigungu_gva_probe"
REPORT = ROOT / "nationwide" / "missing_2019_sigungu_gva_table_probe.md"
BASE = "https://kosis.kr/openapi/statisticsSearch.do"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

MISSING_PROVINCES = ["대구", "대전", "울산", "충남", "경북", "경남", "제주"]
TERMS = [
    "{province} 경제활동별 지역내총부가가치",
    "{province} 지역내총부가가치",
    "{province} 시군구 지역내총부가가치",
    "{province} 구군별 지역내총부가가치",
    "{province} 지역내총생산 시군구",
]
KEYWORDS = ("지역내총부가가치", "경제활동별", "시군구", "구군별", "시군별", "총부가가치")


def request_json(params: dict[str, str]) -> Any:
    url = f"{BASE}?{urllib.parse.urlencode(params)}"
    completed = subprocess.run(
        ["curl", "-sS", "--connect-timeout", "10", "--max-time", "60", "--retry", "2", "--retry-delay", "1", url],
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        safe_params = {k: ("***" if k == "apiKey" else v) for k, v in params.items()}
        safe_query = urllib.parse.urlencode(safe_params)
        stderr = (completed.stderr or "").strip().splitlines()[-1:] or [""]
        raise RuntimeError(f"curl_exit_{completed.returncode}; url={BASE}?{safe_query}; stderr={stderr[0][:200]}")
    payload = json.loads(completed.stdout)
    if isinstance(payload, dict) and payload.get("err"):
        raise RuntimeError(f"KOSIS error {payload.get('err')}: {payload.get('errMsg')}")
    return payload if isinstance(payload, list) else []


def search(api_key: str, province: str, term_template: str) -> list[dict[str, Any]]:
    term = term_template.format(province=province)
    params = {
        "method": "getList",
        "apiKey": api_key,
        "searchNm": term,
        "sort": "DATE",
        "startCount": "1",
        "resultCount": "1000",
        "format": "json",
        "jsonVD": "Y",
    }
    rows = request_json(params)
    out = []
    for row in rows:
        text = " ".join(str(v or "") for v in row.values())
        score = sum(1 for k in KEYWORDS if k in text)
        out.append(
            {
                "target_province": province,
                "search_term": term,
                "org_id": row.get("ORG_ID"),
                "org_name": row.get("ORG_NM"),
                "tbl_id": row.get("TBL_ID"),
                "tbl_name": row.get("TBL_NM"),
                "stat_name": row.get("STAT_NM"),
                "start_period": row.get("STRT_PRD_DE"),
                "end_period": row.get("END_PRD_DE"),
                "prd_se": row.get("PRD_SE"),
                "path": row.get("MT_ATITLE"),
                "link_url": row.get("LINK_URL"),
                "keyword_score": score,
            }
        )
    return out


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.fillna("").astype(str).copy()
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    api_key = get_kosis_key()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for province in MISSING_PROVINCES:
        for term in TERMS:
            try:
                rows.extend(search(api_key, province, term))
            except Exception as exc:
                failures.append({"province": province, "term": term.format(province=province), "error": str(exc)})

    raw_path = RAW / "statistics_search_missing_2019_sigungu_gva.json"
    raw_path.write_text(json.dumps({"created_at": CREATED_AT, "rows": rows, "failures": failures}, ensure_ascii=False, indent=2), encoding="utf-8")
    df = pd.DataFrame(rows)
    if df.empty:
        candidates = pd.DataFrame()
    else:
        candidates = (
            df[df["keyword_score"].gt(0)]
            .drop_duplicates(["target_province", "org_id", "tbl_id"])
            .sort_values(["target_province", "keyword_score", "end_period"], ascending=[True, False, False])
        )
    df.to_csv(OUT / "missing_2019_sigungu_gva_search_raw.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(OUT / "missing_2019_sigungu_gva_search_candidates.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(failures).to_csv(OUT / "missing_2019_sigungu_gva_search_failures.csv", index=False, encoding="utf-8-sig")

    summary = (
        candidates.groupby("target_province", as_index=False)
        .agg(candidate_tables=("tbl_id", "nunique"), earliest_start=("start_period", "min"), latest_end=("end_period", "max"))
        if not candidates.empty
        else pd.DataFrame(columns=["target_province", "candidate_tables", "earliest_start", "latest_end"])
    )

    top = candidates[
        ["target_province", "org_id", "tbl_id", "tbl_name", "stat_name", "start_period", "end_period", "prd_se", "keyword_score"]
    ].head(40) if not candidates.empty else pd.DataFrame()
    report = f"""# 2020 파일럿 제외 시도 2019 시군구 GVA KOSIS 후보 탐색

생성시각: {CREATED_AT}

## 1. 목적

2020 `시군구×업종` backcast 파일럿에서 제외된 시도는 현재 로컬 2020 기준 KOSIS 표가 2019년을 제공하지 않는다. 이 탐색은 KOSIS `statisticsSearch`에서 같은 주제의 구표 또는 대체표가 있는지 확인하기 위한 메타데이터 탐색이다.

## 2. 탐색 대상

| 항목 | 내용 |
| --- | --- |
| 대상 시도 | {', '.join(MISSING_PROVINCES)} |
| 검색어 | 시도명 + 지역내총부가가치/경제활동별/시군구/구군별 |
| 산출물 | 후보 메타데이터. 실제 수치 수집·투입은 별도 검증 후 진행 |

## 3. 후보 요약

{md_table(summary)}

## 4. 상위 후보

{md_table(top)}

## 5. 실패

{md_table(pd.DataFrame(failures).head(20))}

## 6. 해석 원칙

- 후보 표가 있더라도 2019년 실질 지역내총부가가치, 시군구/구군, 경제활동별 차원이 모두 존재해야 2020 파일럿 확장에 쓸 수 있다.
- 기준연도 또는 표체계가 다르면 기존 2020=100/2020 기준 실질계열과 직접 연결하지 않고 bridge year를 둬 재기준화 또는 비중화한다.
- 후보가 없거나 period가 2020 이후뿐이면 2020 파일럿 제외 사유를 “KOSIS 공개 API 기준 2019 시군구 annual benchmark 미확보”로 고정한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"raw_rows={len(df)} candidates={len(candidates)} failures={len(failures)}")
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
