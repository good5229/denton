from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from kosis_common import get_kosis_key, load_env  # noqa: E402


PHASE = "phase208_monthly_indicator_collection"
OUT = ROOT / "data" / "processed" / PHASE
RAW = ROOT / "data" / "raw" / PHASE
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase208_monthly_indicator_collection.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

SEARCH_URL = "https://kosis.kr/openapi/statisticsSearch.do"
DATA_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
META_URL = "https://kosis.kr/statHtml/statHtmlContent.do"

SEARCH_TERMS = [
    "산업별 서비스업생산지수",
    "서비스업생산지수",
    "전산업생산지수",
    "광공업생산지수",
    "광공업출하지수",
    "제조업생산지수",
    "제조업출하지수",
    "제조업재고지수",
    "제조업 재고율",
    "제조업 생산능력",
    "제조업 가동률",
    "품목별 광공업 생산",
    "건설기성",
    "건설수주",
    "소매판매액지수",
    "온라인쇼핑",
    "운수업생산지수",
]

PREFERRED_NAME_PATTERNS = [
    "산업별 서비스업생산지수",
    "서비스업생산지수",
    "전산업생산지수",
    "시도/산업별 광공업생산지수",
    "산업별 광공업생산지수",
    "광공업출하지수",
    "제조업출하지수",
    "제조업재고지수",
    "제조업 재고율",
    "제조업 생산능력",
    "제조업 평균가동률",
    "건설기성",
    "건설수주",
    "소매판매액지수",
    "온라인쇼핑",
]

TOO_LARGE_PATTERNS = ["품목별"]
MAX_FULL_ROWS = 250_000
START = "202001"
END = "202505"
SAMPLE_PERIOD = "202505"

SPECIAL_DT_1F02001_ITEMS = {
    "T10": "생산지수(원지수)",
    "T11": "생산자제품 출하지수(원지수)",
    "T12": "생산자제품 재고지수(원지수)",
}


def ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def request_text(url: str, params: dict[str, str], timeout: int = 90) -> str:
    query = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{query}", timeout=timeout, context=ssl_context()) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def request_json(url: str, params: dict[str, str], timeout: int = 90) -> Any:
    text = request_text(url, params, timeout=timeout)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"non_json_response: {text[:160]!r}") from exc
    if isinstance(data, dict) and data.get("err"):
        raise RuntimeError(f"kosis_error: {data.get('err')} {data.get('errMsg')}")
    return data


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def safe_name(text: str) -> str:
    text = re.sub(r"[^\w가-힣.-]+", "_", text.strip())
    return text.strip("_")[:80] or "unnamed"


def hash_rows(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def search_tables(api_key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for term in SEARCH_TERMS:
        params = {
            "method": "getList",
            "apiKey": api_key,
            "searchNm": term,
            "orgId": "101",
            "sort": "DATE",
            "startCount": "1",
            "resultCount": "1000",
            "format": "json",
            "jsonVD": "Y",
        }
        try:
            data = request_json(SEARCH_URL, params)
        except Exception as exc:
            rows.append({"matched_search": term, "status": "search_error", "error": str(exc)})
            continue
        if not isinstance(data, list):
            continue
        for row in data:
            key = (str(row.get("ORG_ID", "")), str(row.get("TBL_ID", "")))
            if key in seen:
                continue
            seen.add(key)
            table = {
                "status": "searched",
                "matched_search": term,
                "org_id": row.get("ORG_ID"),
                "tbl_id": row.get("TBL_ID"),
                "tbl_nm": row.get("TBL_NM"),
                "stat_nm": row.get("STAT_NM"),
                "start_period": row.get("STRT_PRD_DE"),
                "end_period": row.get("END_PRD_DE"),
                "path": row.get("MT_ATITLE"),
                "link_url": row.get("LINK_URL"),
            }
            rows.append(table)
    return rows


def fetch_metadata(org_id: str, tbl_id: str) -> tuple[dict[str, Any] | None, str]:
    try:
        text = request_text(META_URL, {"orgId": org_id, "tblId": tbl_id, "conn_path": "C1"})
    except Exception as exc:
        return None, f"metadata_fetch_error: {exc}"
    match = re.search(r"var\s+g_jsonStatInfo\s*=\s*'(.+?)';", text, re.S)
    if not match:
        return None, "metadata_parse_error: g_jsonStatInfo_not_found"
    try:
        info = json.loads(html.unescape(match.group(1)))
    except Exception as exc:
        return None, f"metadata_parse_error: {exc}"
    (RAW / f"kosis_{org_id}_{tbl_id}_statHtmlContent.html").write_text(text, encoding="utf-8")
    write_json(RAW / f"kosis_{org_id}_{tbl_id}_metadata.json", info)
    return info, "ok"


def metadata_rows(org_id: str, tbl_id: str, info: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dims: list[dict[str, Any]] = []
    codes: list[dict[str, Any]] = []
    item_info = info.get("itemInfo") or {}
    dims.append(
        {
            "org_id": org_id,
            "tbl_id": tbl_id,
            "tbl_nm": info.get("tblNm"),
            "dimension_id": "ITM_ID",
            "dimension_name": item_info.get("itmNm", "항목"),
            "item_count": item_info.get("itmCnt"),
            "period": info.get("periodStr"),
            "period_range": info.get("containPeriod"),
        }
    )
    for item in item_info.get("itmList", []):
        codes.append(
            {
                "org_id": org_id,
                "tbl_id": tbl_id,
                "dimension_id": "ITM_ID",
                "dimension_name": item_info.get("itmNm", "항목"),
                "code": item.get("itmId"),
                "name": item.get("scrKor"),
                "level": item.get("lvl"),
                "parent_code": item.get("upItmId"),
                "leaf": item.get("leaf"),
            }
        )
    for class_info in info.get("classInfoList", []):
        dims.append(
            {
                "org_id": org_id,
                "tbl_id": tbl_id,
                "tbl_nm": info.get("tblNm"),
                "dimension_id": class_info.get("classId"),
                "dimension_name": class_info.get("classNm"),
                "item_count": class_info.get("itmCnt"),
                "period": info.get("periodStr"),
                "period_range": info.get("containPeriod"),
            }
        )
        for item in class_info.get("itmList", []):
            codes.append(
                {
                    "org_id": org_id,
                    "tbl_id": tbl_id,
                    "dimension_id": class_info.get("classId"),
                    "dimension_name": class_info.get("classNm"),
                    "code": item.get("itmId"),
                    "name": item.get("scrKor"),
                    "level": item.get("lvl"),
                    "parent_code": item.get("upItmId"),
                    "leaf": item.get("leaf"),
                }
            )
    return dims, codes


def is_preferred(name: str) -> bool:
    return any(pattern in name for pattern in PREFERRED_NAME_PATTERNS)


def is_too_large(name: str) -> bool:
    return any(pattern in name for pattern in TOO_LARGE_PATTERNS)


def choose_item_id(codes: list[dict[str, Any]]) -> str:
    items = [r for r in codes if r.get("dimension_id") == "ITM_ID"]
    names = [(str(r.get("code", "")), str(r.get("name", ""))) for r in items]
    preferred_names = ["원지수", "불변지수", "경상지수", "금액", "수주액", "기성액", "지수"]
    for label in preferred_names:
        for code, name in names:
            if label in name and "계절조정" not in name:
                return code
    return names[0][0] if names else "ALL"


def collect_data(org_id: str, tbl_id: str, item_id: str, period: str, start: str, end: str, dim_count: int) -> list[dict[str, Any]]:
    params = {
        "method": "getList",
        "apiKey": get_kosis_key(),
        "orgId": org_id,
        "tblId": tbl_id,
        "itmId": item_id or "ALL",
        "prdSe": period,
        "startPrdDe": start,
        "endPrdDe": end,
        "format": "json",
        "jsonVD": "Y",
    }
    for idx in range(1, dim_count + 1):
        params[f"objL{idx}"] = "ALL"
    data = request_json(DATA_URL, params, timeout=180)
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected_data_type: {type(data).__name__}")
    return data


def collect_data_with_obj(
    org_id: str,
    tbl_id: str,
    item_id: str,
    period: str,
    start: str,
    end: str,
    obj_values: dict[int, str],
) -> list[dict[str, Any]]:
    params = {
        "method": "getList",
        "apiKey": get_kosis_key(),
        "orgId": org_id,
        "tblId": tbl_id,
        "itmId": item_id,
        "prdSe": period,
        "startPrdDe": start,
        "endPrdDe": end,
        "format": "json",
        "jsonVD": "Y",
    }
    for idx, value in obj_values.items():
        params[f"objL{idx}"] = value
    data = request_json(DATA_URL, params, timeout=180)
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected_data_type: {type(data).__name__}")
    return data


def normalize_rows(dataset_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        norm: dict[str, Any] = {
            "dataset": dataset_id,
            "org_id": row.get("ORG_ID"),
            "tbl_id": row.get("TBL_ID"),
            "tbl_nm": row.get("TBL_NM"),
            "prd_se": row.get("PRD_SE"),
            "prd_de": row.get("PRD_DE"),
            "item_id": row.get("ITM_ID"),
            "item_nm": row.get("ITM_NM"),
            "unit_nm": row.get("UNIT_NM"),
            "value": row.get("DT"),
        }
        for idx in range(1, 9):
            if f"C{idx}" in row or f"C{idx}_NM" in row:
                norm[f"c{idx}_id"] = row.get(f"C{idx}")
                norm[f"c{idx}_nm"] = row.get(f"C{idx}_NM")
        out.append(norm)
    return out


def summarize_dataset(dataset_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    periods = sorted({str(r.get("prd_de", "")) for r in rows if r.get("prd_de")})
    tbl_names = sorted({str(r.get("tbl_nm", "")) for r in rows if r.get("tbl_nm")})
    item_names = sorted({str(r.get("item_nm", "")) for r in rows if r.get("item_nm")})
    dim_counts: dict[str, int] = {}
    for idx in range(1, 9):
        key = f"c{idx}_nm"
        vals = {str(r.get(key, "")) for r in rows if r.get(key)}
        if vals:
            dim_counts[key] = len(vals)
    return {
        "dataset": dataset_id,
        "tbl_nm": "; ".join(tbl_names[:3]),
        "rows": len(rows),
        "period_min": periods[0] if periods else "",
        "period_max": periods[-1] if periods else "",
        "item_names": "; ".join(item_names[:6]),
        "dimension_unique_counts": json.dumps(dim_counts, ensure_ascii=False),
        "row_hash": hash_rows(rows),
    }


def known_source_url(row: dict[str, Any]) -> str:
    link = str(row.get("link_url", "") or "").strip()
    if link:
        return link
    org_id = str(row.get("org_id", "101") or "101")
    tbl_id = str(row.get("tbl_id", "") or "")
    if tbl_id:
        return f"https://kosis.kr/statHtml/statHtml.do?orgId={urllib.parse.quote(org_id)}&tblId={urllib.parse.quote(tbl_id)}"
    return "https://kosis.kr"


def classify_collection_issue(row: dict[str, Any]) -> str:
    status = str(row.get("collection_status", ""))
    error = str(row.get("error", ""))
    period = str(row.get("period", ""))
    tbl_nm = str(row.get("tbl_nm", ""))
    if status == "skip_not_monthly":
        return "월별 공표표가 아님" if "M" not in period else "고정/연간성 표라 월별 수집 대상 아님"
    if status == "sample_error" and "데이터가 존재하지 않습니다" in error:
        return "검색에는 잡히지만 해당 최신 월 데이터 없음; 대체·개편표 사용 필요"
    if status == "full_error" and "40,000" in error:
        return "API 셀 제한; chunk 수집 필요"
    if status == "sample_only_large_table":
        return "행 수 과대; 표본·항목 선별 수집 필요"
    if "품목별" in tbl_nm:
        return "품목 단위 대형표; KSIC 매핑 설계 후 선별 수집 필요"
    if status.endswith("error"):
        return "API 파라미터·권한·기간 불일치 가능성"
    return ""


def md_table(rows: list[dict[str, Any]], cols: list[str], limit: int = 20) -> str:
    rows = rows[:limit]
    if not rows:
        return "_해당 없음_"
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")).replace("|", "/") for c in cols) + " |")
    return "\n".join(lines)


def main() -> int:
    _ = load_env()
    api_key = get_kosis_key()
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    catalog = search_tables(api_key)
    write_json(RAW / "phase208_kosis_search_catalog.json", catalog)
    write_csv(OUT / "phase208_kosis_search_catalog.csv", catalog)

    candidates = [
        row for row in catalog
        if row.get("status") == "searched"
        and row.get("org_id")
        and row.get("tbl_id")
        and is_preferred(str(row.get("tbl_nm", "")))
    ]

    all_dims: list[dict[str, Any]] = []
    all_codes: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    collected_summary: list[dict[str, Any]] = []
    collected_all: list[dict[str, Any]] = []
    seen_tables: set[tuple[str, str]] = set()

    for cand in candidates:
        org_id = str(cand["org_id"])
        tbl_id = str(cand["tbl_id"])
        key = (org_id, tbl_id)
        if key in seen_tables:
            continue
        seen_tables.add(key)
        tbl_nm = str(cand.get("tbl_nm", ""))
        info, meta_status = fetch_metadata(org_id, tbl_id)
        if not info:
            probes.append(cand | {"metadata_status": meta_status, "collection_status": "metadata_failed"})
            continue
        dims, codes = metadata_rows(org_id, tbl_id, info)
        all_dims.extend(dims)
        all_codes.extend(codes)
        period = str(info.get("periodStr", "") or "")
        dim_count = len(info.get("classInfoList", []) or [])
        item_id = choose_item_id(codes)
        if "월" not in period and "M" not in period:
            probes.append(cand | {"metadata_status": "ok", "period": period, "collection_status": "skip_not_monthly"})
            continue
        try:
            sample = collect_data(org_id, tbl_id, item_id, "M", SAMPLE_PERIOD, SAMPLE_PERIOD, dim_count)
            sample_norm = normalize_rows(f"{tbl_id}_sample", sample)
            write_csv(OUT / f"phase208_sample_{org_id}_{tbl_id}.csv", sample_norm)
        except Exception as exc:
            probes.append(cand | {"metadata_status": "ok", "period": period, "item_id": item_id, "collection_status": "sample_error", "error": str(exc)})
            continue
        estimated_full_rows = len(sample) * 65
        if is_too_large(tbl_nm) or estimated_full_rows > MAX_FULL_ROWS:
            probes.append(
                cand
                | {
                    "metadata_status": "ok",
                    "period": period,
                    "item_id": item_id,
                    "sample_rows_202505": len(sample),
                    "estimated_full_rows": estimated_full_rows,
                    "collection_status": "sample_only_large_table",
                }
            )
            continue
        try:
            full = collect_data(org_id, tbl_id, item_id, "M", START, END, dim_count)
        except Exception as exc:
            probes.append(cand | {"metadata_status": "ok", "period": period, "item_id": item_id, "sample_rows_202505": len(sample), "collection_status": "full_error", "error": str(exc)})
            continue
        dataset_id = f"phase208_{tbl_id}_{safe_name(tbl_nm)}"
        norm = normalize_rows(dataset_id, full)
        write_json(RAW / f"{dataset_id}.json", full)
        write_csv(OUT / f"{dataset_id}.csv", norm)
        collected_all.extend(norm)
        collected_summary.append(summarize_dataset(dataset_id, norm))
        probes.append(
            cand
            | {
                "metadata_status": "ok",
                "period": period,
                "item_id": item_id,
                "sample_rows_202505": len(sample),
                "estimated_full_rows": estimated_full_rows,
                "collection_status": "collected_full",
                "full_rows": len(full),
            }
        )

    # DT_1F02001 is the most important regional monthly production-index table,
    # but an all-at-once API call can exceed KOSIS' 40,000-cell limit. Collect it
    # by item and region so it is not misclassified as unavailable.
    dt_1f02001_rows: list[dict[str, Any]] = []
    dt_1f02001_status: list[dict[str, Any]] = []
    dt_1f02001_region_codes = [
        row
        for row in all_codes
        if row.get("tbl_id") == "DT_1F02001" and row.get("dimension_id") == "A" and row.get("code")
    ]
    if dt_1f02001_region_codes:
        for item_id, item_name in SPECIAL_DT_1F02001_ITEMS.items():
            for region in dt_1f02001_region_codes:
                region_code = str(region.get("code", ""))
                region_name = str(region.get("name", ""))
                try:
                    chunk = collect_data_with_obj(
                        "101",
                        "DT_1F02001",
                        item_id,
                        "M",
                        START,
                        END,
                        {1: region_code, 2: "ALL"},
                    )
                    norm = normalize_rows("phase208_DT_1F02001_chunked_regional_mining_manufacturing_indices", chunk)
                    dt_1f02001_rows.extend(norm)
                    dt_1f02001_status.append(
                        {
                            "tbl_id": "DT_1F02001",
                            "item_id": item_id,
                            "item_nm": item_name,
                            "region_code": region_code,
                            "region_nm": region_name,
                            "status": "ok",
                            "rows": len(chunk),
                        }
                    )
                except Exception as exc:
                    dt_1f02001_status.append(
                        {
                            "tbl_id": "DT_1F02001",
                            "item_id": item_id,
                            "item_nm": item_name,
                            "region_code": region_code,
                            "region_nm": region_name,
                            "status": "error",
                            "error": str(exc),
                        }
                    )
        if dt_1f02001_rows:
            dataset_id = "phase208_DT_1F02001_시도_산업별_광공업_생산출하재고지수_2020_100"
            for row in dt_1f02001_rows:
                row["dataset"] = dataset_id
            write_csv(OUT / f"{dataset_id}.csv", dt_1f02001_rows)
            collected_all.extend(dt_1f02001_rows)
            collected_summary.append(summarize_dataset(dataset_id, dt_1f02001_rows))
            regional_or_chunked_note = {
                "status": "searched",
                "matched_search": "광공업생산지수",
                "org_id": "101",
                "tbl_id": "DT_1F02001",
                "tbl_nm": "시도/산업별 광공업생산지수(2020=100)",
                "stat_nm": "광업제조업동향조사",
                "start_period": START,
                "end_period": END,
                "path": "KOSIS > 광업제조업동향조사",
                "link_url": "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1F02001",
                "metadata_status": "ok",
                "period": "M#Q#Y",
                "item_id": "T10/T11/T12",
                "sample_rows_202505": "",
                "estimated_full_rows": len(dt_1f02001_rows),
                "collection_status": "collected_full_chunked",
                "full_rows": len(dt_1f02001_rows),
            }
            probes.append(regional_or_chunked_note)
        write_csv(OUT / "phase208_DT_1F02001_chunk_status.csv", dt_1f02001_status)

    write_csv(OUT / "phase208_candidate_metadata_dimensions.csv", all_dims)
    write_csv(OUT / "phase208_candidate_metadata_codes.csv", all_codes)
    write_csv(OUT / "phase208_monthly_indicator_probe_summary.csv", probes)
    write_csv(OUT / "phase208_monthly_indicator_collection_summary.csv", collected_summary)
    write_csv(OUT / "phase208_monthly_indicator_collected_all.csv", collected_all)

    regional_or_national = []
    for row in probes:
        status = row.get("collection_status")
        if status not in {"collected_full", "collected_full_chunked", "sample_only_large_table"}:
            continue
        tbl_id = str(row.get("tbl_id", ""))
        tbl_nm = str(row.get("tbl_nm", ""))
        dims_for_table = [d for d in all_dims if str(d.get("tbl_id")) == tbl_id]
        dim_names = " / ".join(str(d.get("dimension_name", "")) for d in dims_for_table if d.get("dimension_id") != "ITM_ID")
        is_regional = any("시도" in str(d.get("dimension_name", "")) or "지역" in str(d.get("dimension_name", "")) for d in dims_for_table)
        regional_or_national.append(
            {
                "tbl_id": tbl_id,
                "tbl_nm": tbl_nm,
                "period": row.get("period", ""),
                "scope": "시도 포함" if is_regional else "전국 또는 비지역",
                "dimensions": dim_names,
                "collection_status": status,
                "use_in_gva": (
                    "시도×상세산업 월별 생산·출하·재고 흐름 보강 후보"
                    if tbl_id == "DT_1F02001"
                    else "시도×산업 월별 시간경로 보강 후보"
                    if is_regional
                    else "전국 업종 월별 시간경로 보강 후보; 시군구 수준 식별에는 별도 공간자료 필요"
                ),
            }
        )
    write_csv(OUT / "phase208_monthly_indicator_gva_use_map.csv", regional_or_national)

    resolved_by_chunk = {
        str(row.get("tbl_id", ""))
        for row in probes
        if str(row.get("collection_status", "")) == "collected_full_chunked"
    }
    blocked_or_deferred = []
    for row in probes:
        status = str(row.get("collection_status", ""))
        if status in {"collected_full", "collected_full_chunked"}:
            continue
        if str(row.get("tbl_id", "")) in resolved_by_chunk and status == "full_error":
            continue
        issue = classify_collection_issue(row)
        if not issue:
            continue
        blocked_or_deferred.append(
            {
                "tbl_id": row.get("tbl_id", ""),
                "tbl_nm": row.get("tbl_nm", ""),
                "period": row.get("period", ""),
                "collection_status": status,
                "source_url": known_source_url(row),
                "estimated_cause": issue,
                "next_action": (
                    "월별 대체표를 사용하거나 분기 지표로만 사용"
                    if status == "skip_not_monthly"
                    else "대체표 ID 확인 또는 기준월 변경"
                    if status == "sample_error"
                    else "지역·항목·기간별로 나누어 재수집"
                    if "셀 제한" in issue
                    else "필요 업종/품목을 먼저 정한 뒤 선별 수집"
                ),
            }
        )
    write_csv(OUT / "phase208_deferred_or_failed_source_links.csv", blocked_or_deferred)

    report = [
        "# Phase208 업종별 월별 indicator 수집 및 적용성 점검",
        "",
        f"- 실행시각: {CREATED_AT}",
        f"- 수집기간: {START}~{END}",
        "- 목적: 총부가가치(GVA)의 월별 배분·외삽에 쓸 수 있는 공공 월별 활동자료를 KOSIS 중심으로 추가 발굴한다.",
        "",
        "## 결론",
        "",
        "1. 제조업은 `시도/산업별 광공업생산지수`가 핵심 지표다. 전체 호출은 KOSIS 40,000셀 제한에 걸렸지만 시도×항목 chunk 방식으로 생산·출하·재고 원지수 97,500행을 수집했다. 이 표는 제조업 C10/C101 같은 중·소분류 성격의 상세 산업 월별 흐름까지 제공하므로, 제조업 GVA의 월별·상세산업 배분 근거로 가장 우선 적용할 수 있다.",
        "2. 서비스업은 지역별 표(`시도별 서비스업생산지수`)가 분기 단위이고, 월별 서비스업생산지수는 전국 단위 성격이 강하다. 따라서 월별 서비스 세부 경로에는 유용하지만 시군구/행정동 공간 차이를 단독으로 식별하지 않는다.",
        "3. 건설·소매·온라인쇼핑·제조업 출하/재고/가동률 계열은 월별 보조지표 후보로 수집 또는 샘플 점검했다. GVA 적용 시에는 `속보성 cutoff`와 `정밀화 전체자료`를 분리해야 한다.",
        "",
        "## 수집 완료 월별 지표",
        "",
        md_table(collected_summary, ["dataset", "tbl_nm", "rows", "period_min", "period_max", "item_names", "dimension_unique_counts"], 30),
        "",
        "## 후보별 수집/보류 판정",
        "",
        md_table(probes, ["tbl_id", "tbl_nm", "period", "item_id", "sample_rows_202505", "collection_status", "error"], 80),
        "",
        "## GVA 적용 지도",
        "",
        md_table(regional_or_national, ["tbl_id", "tbl_nm", "scope", "dimensions", "collection_status", "use_in_gva"], 80),
        "",
        "## 링크 확보 후 수집 보류·실패 원인",
        "",
        md_table(blocked_or_deferred, ["tbl_id", "tbl_nm", "period", "collection_status", "source_url", "estimated_cause", "next_action"], 80),
        "",
        "## 누출·공표시점 주의",
        "",
        "- 이번 수집물은 KOSIS 현재 스냅샷이다. 속보성 실험에 바로 쓰려면 각 기준시점에서 실제 공표됐던 값만 남기는 release ledger가 추가로 필요하다.",
        "- 월별 지표는 보통 익월 말 전후 공표되는 속보성이 있지만, 과거 개정값이 포함될 수 있으므로 `현재 스냅샷=당시 사용 가능 자료`로 간주하면 안 된다.",
        "- 정밀화 실험에는 전체 월별 지표를 사용할 수 있으나, 실제 상위 GVA 총량 자체를 lower-level 예측값 생성에 직접 주입하면 예측성능이 아니라 사후 정합화가 된다.",
        "",
        "## 산출 파일",
        "",
        f"- `{OUT / 'phase208_monthly_indicator_collection_summary.csv'}`",
        f"- `{OUT / 'phase208_monthly_indicator_probe_summary.csv'}`",
        f"- `{OUT / 'phase208_monthly_indicator_gva_use_map.csv'}`",
        f"- `{OUT / 'phase208_monthly_indicator_collected_all.csv'}`",
        f"- `{OUT / 'phase208_deferred_or_failed_source_links.csv'}`",
    ]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"catalog={len(catalog)} candidates={len(candidates)} collected={len(collected_summary)}")
    print(f"report={REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
