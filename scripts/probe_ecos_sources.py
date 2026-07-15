from __future__ import annotations

import json
import ssl
import sys
import urllib.parse
import urllib.request
from collections import Counter
import os
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, load_env, write_csv, write_json


BASE_URL = "https://ecos.bok.or.kr/api"
RAW_ECOS_DIR = RAW_DIR / "ecos"

SEARCH_TERMS = [
    "지역",
    "시도",
    "시군구",
    "GRDP",
    "지역내총생산",
    "지역내총부가가치",
    "총부가가치",
    "부가가치",
    "GDP",
    "경제활동별",
    "산업별",
    "산업연관",
    "투입산출",
    "투입산출표",
    "산업연관표",
    "생산유발",
    "부가가치유발",
    "생산자물가",
    "수입물가",
    "수출물가",
    "환율",
    "원유",
    "유가",
    "석탄",
    "전력",
    "전기",
    "가스",
]

DIRECT_BENCHMARK_TERMS = [
    "지역내총생산",
    "지역내총부가가치",
    "GRDP",
    "시도",
    "시군구",
    "지역",
]

IO_TERMS = ["산업연관", "투입산출", "산업연관표", "투입산출표", "생산유발", "부가가치유발"]
PRICE_EXOG_TERMS = [
    "생산자물가",
    "수입물가",
    "수출물가",
    "환율",
    "원유",
    "유가",
    "석탄",
    "전력",
    "전기",
    "가스",
]

ITEM_TABLE_LIMIT = int(os.environ.get("ECOS_ITEM_TABLE_LIMIT", "30"))


def get_ecos_key() -> str:
    env = load_env()
    for name in ("ECOS_API_KEY", "BOK_ECOS_API_KEY", "BOK_API_KEY"):
        value = env.get(name)
        if value:
            return value
    raise SystemExit("ECOS API key not found. Add ECOS_API_KEY=... to .env and rerun.")


def ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def ecos_request(service: str, api_key: str, start: int, end: int, *args: str) -> dict[str, Any]:
    parts = [service, api_key, "json", "kr", str(start), str(end), *args]
    quoted = [urllib.parse.quote(part, safe="") for part in parts]
    url = f"{BASE_URL}/{'/'.join(quoted)}"
    with urllib.request.urlopen(url, timeout=8, context=ssl_context()) as response:
        body = response.read().decode("utf-8-sig")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON ECOS response from {service}: {body[:300]}") from exc
    if isinstance(data, dict) and "RESULT" in data:
        result = data.get("RESULT", {})
        code = result.get("CODE")
        if code and code != "INFO-000":
            raise RuntimeError(f"ECOS {service} error {code}: {result.get('MESSAGE')}")
    return data


def rows_from_response(data: dict[str, Any], service: str) -> list[dict[str, Any]]:
    node = data.get(service)
    if not isinstance(node, dict):
        return []
    rows = node.get("row", [])
    if isinstance(rows, dict):
        return [rows]
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def match_terms(row: dict[str, Any], terms: list[str]) -> list[str]:
    haystack = " ".join(str(value) for value in row.values() if value is not None).lower()
    return [term for term in terms if term.lower() in haystack]


def classify_table(row: dict[str, Any]) -> str:
    text = " ".join(str(value) for value in row.values() if value is not None)
    direct = [term for term in DIRECT_BENCHMARK_TERMS if term.lower() in text.lower()]
    if any(term in text for term in ("지역내총생산", "지역내총부가가치", "GRDP")):
        return "direct_candidate_grdp_gva"
    if len(direct) >= 2 and any(term in text for term in ("경제활동별", "산업별", "총생산", "부가가치")):
        return "direct_candidate_regional_macro"
    if any(term in text for term in IO_TERMS):
        return "io_or_industry_linkage"
    if any(term in text for term in PRICE_EXOG_TERMS):
        return "price_energy_fx_exogenous"
    return "related_context"


def relevance_score(row: dict[str, Any]) -> int:
    text = " ".join(str(value) for value in row.values() if value is not None)
    score = 0
    for term in ("지역내총생산", "지역내총부가가치", "GRDP"):
        if term.lower() in text.lower():
            score += 12
    for term in ("시도", "시군구", "지역"):
        if term in text:
            score += 4
    for term in ("총부가가치", "경제활동별", "산업별", "GDP"):
        if term in text:
            score += 3
    for term in IO_TERMS:
        if term in text:
            score += 5
    for term in PRICE_EXOG_TERMS:
        if term in text:
            score += 2
    if row.get("SRCH_YN") == "Y":
        score += 1
    if row.get("CYCLE") in {"M", "Q"}:
        score += 1
    return score


def table_code(row: dict[str, Any]) -> str:
    for key in ("STAT_CODE", "stat_code", "통계표코드"):
        value = row.get(key)
        if value:
            return str(value)
    return ""


def table_name(row: dict[str, Any]) -> str:
    for key in ("STAT_NAME", "stat_name", "통계명"):
        value = row.get(key)
        if value:
            return str(value)
    return ""


def fetch_table_catalog(api_key: str) -> list[dict[str, Any]]:
    cached = RAW_ECOS_DIR / "StatisticTableList.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        return rows_from_response(data, "StatisticTableList")
    data = ecos_request("StatisticTableList", api_key, 1, 10000)
    write_json(RAW_ECOS_DIR / "StatisticTableList.json", data)
    return rows_from_response(data, "StatisticTableList")


def fetch_items(api_key: str, stat_code: str) -> tuple[list[dict[str, Any]], str | None]:
    cached = RAW_ECOS_DIR / "items" / f"{stat_code}.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        return rows_from_response(data, "StatisticItemList"), None
    try:
        data = ecos_request("StatisticItemList", api_key, 1, 10000, stat_code)
    except Exception as exc:
        return [], str(exc)
    write_json(RAW_ECOS_DIR / "items" / f"{stat_code}.json", data)
    return rows_from_response(data, "StatisticItemList"), None


def normalized_table_rows(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in catalog:
        terms = match_terms(row, SEARCH_TERMS)
        if not terms:
            continue
        code = table_code(row)
        name = table_name(row)
        out.append(
            {
                "stat_code": code,
                "stat_name": name,
                "cycle": row.get("CYCLE") or row.get("cycle") or "",
                "org_name": row.get("ORG_NAME") or "",
                "start_time": row.get("START_TIME") or "",
                "end_time": row.get("END_TIME") or "",
                "matched_terms": ", ".join(terms),
                "use_category": classify_table(row),
                "relevance_score": relevance_score(row),
                "searchable": row.get("SRCH_YN") or "",
                "raw_text": " | ".join(str(value) for value in row.values() if value is not None),
            }
        )
    out.sort(key=lambda r: (-int(r["relevance_score"]), r["use_category"], r["stat_code"], r["stat_name"]))
    return out


def normalized_item_rows(api_key: str, tables: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    seen: set[str] = set()
    item_tables = [
        table
        for table in tables
        if table.get("searchable") == "Y"
        and (
            int(table.get("relevance_score") or 0) >= 5
            or table.get("use_category")
            in {"direct_candidate_grdp_gva", "direct_candidate_regional_macro", "io_or_industry_linkage", "price_energy_fx_exogenous"}
        )
    ][:ITEM_TABLE_LIMIT]
    for table in item_tables:
        code = str(table.get("stat_code") or "")
        if not code or code in seen:
            continue
        seen.add(code)
        rows, error = fetch_items(api_key, code)
        if error:
            failures.append({"stat_code": code, "stat_name": table.get("stat_name"), "error": error})
            continue
        for row in rows:
            terms = match_terms(row, SEARCH_TERMS)
            items.append(
                {
                    "stat_code": code,
                    "stat_name": table.get("stat_name"),
                    "item_code": row.get("ITEM_CODE") or row.get("ITEM_CODE1") or "",
                    "item_name": row.get("ITEM_NAME") or row.get("ITEM_NAME1") or "",
                    "cycle": row.get("CYCLE") or "",
                    "start_time": row.get("START_TIME") or "",
                    "end_time": row.get("END_TIME") or "",
                    "matched_terms": ", ".join(terms),
                    "raw_text": " | ".join(str(value) for value in row.values() if value is not None),
                }
            )
    return items, failures


def build_summary(tables: list[dict[str, Any]], items: list[dict[str, Any]], failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    category_counts = Counter(str(row.get("use_category") or "") for row in tables)
    direct_tables = [
        row
        for row in tables
        if str(row.get("use_category")).startswith("direct_candidate")
        or any(term in str(row.get("raw_text", "")) for term in ("지역내총생산", "지역내총부가가치", "GRDP"))
    ]
    io_tables = [row for row in tables if row.get("use_category") == "io_or_industry_linkage"]
    exog_tables = [row for row in tables if row.get("use_category") == "price_energy_fx_exogenous"]
    direct_quarterly = [
        row
        for row in direct_tables
        if any(token in str(row.get("cycle", "")) + str(row.get("raw_text", "")) for token in ("Q", "분기", "월"))
    ]
    rows = [
        {"metric": "matched_tables", "value": len(tables), "note": "SEARCH_TERMS에 걸린 ECOS 통계표 수"},
        {"metric": "matched_items", "value": len(items), "note": "걸린 통계표에서 수집한 항목 수"},
        {"metric": "item_failures", "value": len(failures), "note": "항목목록 조회 실패 건수"},
        {"metric": "direct_candidate_tables", "value": len(direct_tables), "note": "지역 GRDP/GVA 직접 후보"},
        {"metric": "direct_candidate_quarterly_or_monthly_tables", "value": len(direct_quarterly), "note": "직접 후보 중 분기/월 단서가 있는 표"},
        {"metric": "io_or_industry_linkage_tables", "value": len(io_tables), "note": "투입산출/산업연관 보강 후보"},
        {"metric": "price_energy_fx_exogenous_tables", "value": len(exog_tables), "note": "가격·에너지·환율 보강 후보"},
    ]
    for category, count in sorted(category_counts.items()):
        rows.append({"metric": f"category:{category}", "value": count, "note": "use_category count"})
    return rows


def main() -> None:
    api_key = get_ecos_key()
    RAW_ECOS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    catalog = fetch_table_catalog(api_key)
    tables = normalized_table_rows(catalog)
    write_csv(PROCESSED_DIR / "ecos_relevant_tables.csv", tables)
    items, failures = normalized_item_rows(api_key, tables)
    summary = build_summary(tables, items, failures)

    write_csv(PROCESSED_DIR / "ecos_relevant_items.csv", items)
    write_csv(PROCESSED_DIR / "ecos_item_failures.csv", failures)
    write_csv(PROCESSED_DIR / "ecos_probe_summary.csv", summary)

    print(f"ECOS matched tables: {len(tables)}")
    print(f"ECOS matched items: {len(items)}")
    print(f"ECOS item failures: {len(failures)}")
    for row in summary:
        print(f"{row['metric']}: {row['value']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ECOS probe failed: {exc}", file=sys.stderr)
        raise
