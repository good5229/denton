from __future__ import annotations

import hashlib
import json
import re
import ssl
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, load_env, write_csv, write_json
from probe_buildinghub_readiness import response_items, response_status


TODAY = datetime.now().date().isoformat()
BASE_URL = "http://apis.data.go.kr/1613000/ArchPmsHubService"
RAW_ROUTE_DIR = RAW_DIR / "buildinghub" / f"route_probe_{datetime.now().strftime('%Y%m%d')}"
SAMPLE_PARAMS = {"sigunguCd": "11680", "bjdongCd": "10300", "pageNo": 1, "numOfRows": 1, "_type": "json"}
TARGET_EVENT_FIELDS = {
    "permit": "archPmsDay",
    "start": "realStcnsDay",
    "approval": "useAprDay",
}


OPERATIONS = [
    ("getApBasisOulnInfo", "건축인허가 기본개요", "core_basis", "contains permit/start/approval date fields but D1 filter semantics failed"),
    ("getApDongOulnInfo", "건축인허가 동별개요", "detail", ""),
    ("getApFlrOulnInfo", "건축인허가 층별개요", "detail", ""),
    ("getApHoOulnInfo", "건축인허가 호별개요", "detail", ""),
    ("getApImprprInfo", "건축인허가 대수선", "detail", ""),
    ("getApExposPubuseAreaInfo", "건축인허가 전유공용면적", "detail", ""),
    ("getApHdcrMgmRgstInfo", "건축인허가 공작물관리대장", "detail", ""),
    ("getApDemolExtngMgmRgstInfo", "건축인허가 철거멸실관리대장", "other_event", "demolition/removal, not permit/start/approval"),
    ("getApTmpBldInfo", "건축인허가 가설건축물", "detail", ""),
    ("getApWclfInfo", "건축인허가 오수정화시설", "detail", ""),
    ("getApPklotInfo", "건축인허가 주차장", "detail", ""),
    ("getApAtchPklotInfo", "건축인허가 부설주차장", "detail", ""),
    ("getApHoExposPubuseAreaInfo", "건축인허가 호별전유공용면적", "detail", ""),
    ("getApJijiguInfo", "건축인허가 지역지구구역", "detail", ""),
    ("getApRoadRgstInfo", "건축인허가 도로명대장", "detail", ""),
    ("getApPlatPlcInfo", "건축인허가 대지위치", "detail", ""),
    ("getApHsTpInfo", "건축인허가 주택유형", "detail", ""),
]


BULK_PAGES = [
    (
        "hub_arch_data_landing",
        "원하는대로 건축데이터",
        "https://www.hub.go.kr/portal/psg/idx-arch-data-sub.do",
        "Hub page says building permit bulk/raw data service exists and major formats include CSV/JSON/XLSX.",
    ),
    (
        "hub_large_data_service",
        "대용량 제공 서비스",
        "https://www.hub.go.kr/portal/opn/lps/idx-lgcpt-pvsn-srvc-list.do",
        "Hub page describes monthly large data generated from Seumter operational data; recent month is previous-month updates around the 20th.",
    ),
    (
        "data_go_kr_archpms_openapi",
        "국토교통부_건축HUB_건축인허가정보 서비스",
        "https://www.data.go.kr/data/15136267/openapi.do",
        "OpenAPI metadata page; monthly update and traffic limits are documented.",
    ),
    (
        "data_go_kr_archpms_standard",
        "전국건축인허가기본정보표준데이터",
        "https://www.data.go.kr/data/15029176/standard.do",
        "Standard data page points back to the same BuildingHUB OpenAPI service rather than a directly fetched historical file.",
    ),
]


def data_go_key() -> str:
    env = load_env()
    for name in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING"):
        if env.get(name):
            return str(env[name])
    raise SystemExit("DATA_GO_KR_DECODING or DATA_GO_KR_ENCODING not found in .env")


def ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def request_text(url: str, timeout: int = 90) -> tuple[int | str, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/html, application/xml, text/xml, */*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
            body = response.read()
            return response.status, response.headers.get("Content-Type", ""), body.decode("utf-8-sig", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, exc.headers.get("Content-Type", ""), body.decode("utf-8-sig", errors="replace")
    except Exception as exc:
        return "", "", repr(exc)


def cache_path_for(operation: str, params: dict[str, Any]) -> Path:
    RAW_ROUTE_DIR.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps({"operation": operation, "params": params}, ensure_ascii=False, sort_keys=True)
    key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return RAW_ROUTE_DIR / f"{operation}_{key}.json"


def probe_operation(operation: str) -> dict[str, Any]:
    params = {"serviceKey": data_go_key(), **SAMPLE_PARAMS}
    cache_path = cache_path_for(operation, {key: value for key, value in params.items() if key != "serviceKey"})
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        payload["cache_status"] = "skipped_cached"
        return payload
    endpoint = f"{BASE_URL}/{operation}"
    url = f"{endpoint}?{urllib.parse.urlencode(params)}"
    status, content_type, text = request_text(url)
    try:
        data = json.loads(text) if text.strip() else {}
        parse_error = ""
    except json.JSONDecodeError as exc:
        data = {}
        parse_error = str(exc)
    payload = {
        "operation_name": operation,
        "endpoint": endpoint,
        "request_parameters": {key: value for key, value in params.items() if key != "serviceKey"},
        "retrieval_timestamp": datetime.now().isoformat(timespec="seconds"),
        "http_status": status,
        "content_type": content_type,
        "text_prefix": text[:1000],
        "data": data,
        "parse_error": parse_error,
        "cache_status": "new_request",
    }
    write_json(cache_path, payload)
    return payload


def response_fields(items: list[dict[str, Any]]) -> list[str]:
    return sorted({field for row in items for field in row})


def operation_response_status(payload: dict[str, Any], items: list[dict[str, Any]]) -> str:
    if payload.get("http_status") not in (200, "200"):
        return "http_error"
    if payload.get("parse_error"):
        return "parse_error"
    if items:
        return "success"
    return response_status(payload)


def operation_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inventory = []
    probe_rows = []
    for operation, label, category, note in OPERATIONS:
        payload = probe_operation(operation)
        items = response_items(payload)
        fields = response_fields(items)
        event_fields = [field for field in TARGET_EVENT_FIELDS.values() if field in fields]
        event_specific_candidate = "N"
        if operation == "getApBasisOulnInfo" and event_fields:
            event_specific_candidate = "N_core_mixed_event_fields"
        elif any(token in label for token in ("착공", "사용승인", "허가취소")):
            event_specific_candidate = "Y_name_based_candidate"
        status = operation_response_status(payload, items)
        actual_row_received = bool(items)
        date_parameters = "startDate,endDate" if operation == "getApBasisOulnInfo" else "not_documented_in_script"
        inventory.append(
            {
                "service_name": "국토교통부_건축HUB_건축인허가정보 서비스",
                "operation_name": operation,
                "operation_label": label,
                "operation_category": category,
                "endpoint": f"{BASE_URL}/{operation}",
                "http_method": "GET",
                "required_parameters": "serviceKey",
                "optional_parameters": "sigunguCd,bjdongCd,pageNo,numOfRows,_type,startDate,endDate",
                "date_parameters": date_parameters,
                "date_parameter_definition": "unresolved" if operation == "getApBasisOulnInfo" else "not_found",
                "region_parameters": "sigunguCd,bjdongCd",
                "response_format": "JSON+XML",
                "response_fields": ",".join(fields),
                "event_date_fields_in_sample": ",".join(event_fields),
                "event_specific_candidate": event_specific_candidate,
                "pagination_rule": "pageNo,numOfRows",
                "maximum_page_size": "not_verified",
                "update_cycle": "monthly_from_metadata",
                "sample_request_status": payload.get("cache_status", ""),
                "sample_response_status": status,
                "actual_row_received": "Y" if actual_row_received else "N",
                "event_definition": note or "not event-specific for permit/start/approval",
            }
        )
        probe_rows.append(
            {
                "operation_name": operation,
                "endpoint": f"{BASE_URL}/{operation}",
                "http_status": payload.get("http_status", ""),
                "content_type": payload.get("content_type", ""),
                "response_status": status,
                "actual_row_received": "Y" if actual_row_received else "N",
                "sample_row_count": len(items),
                "sample_fields": ",".join(fields),
                "event_date_fields_in_sample": ",".join(event_fields),
                "result_msg": payload.get("data", {}).get("response", {}).get("header", {}).get("resultMsg", "") if isinstance(payload.get("data"), dict) else "",
                "cache_status": payload.get("cache_status", ""),
                "traffic_policy": "single_probe_only_numOfRows_1",
            }
        )
    return inventory, probe_rows


def compact_text(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:1200]


def bulk_rows() -> list[dict[str, Any]]:
    rows = []
    for source_id, source_name, url, expected in BULK_PAGES:
        cache_path = RAW_ROUTE_DIR / f"{source_id}.html"
        if cache_path.exists():
            text = cache_path.read_text(encoding="utf-8", errors="replace")
            status = "cached"
            content_type = ""
        else:
            status, content_type, text = request_text(url)
            RAW_ROUTE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8", errors="replace")
        lowered = text.lower()
        rows.append(
            {
                "source_id": source_id,
                "source_name": source_name,
                "url": url,
                "http_status": status,
                "content_type": content_type,
                "bulk_route_mentions": "Y" if any(token in text for token in ("대용량", "월별", "누적분", "변동분", "CSV", "XLSX")) else "N",
                "historical_archive_confirmed": "N",
                "monthly_vintage_confirmed": "N",
                "direct_download_confirmed": "N",
                "login_or_membership_likely": "Y" if "회원" in text or "로그인" in text else "unknown",
                "file_format_observed": ",".join(fmt for fmt in ("CSV", "JSON", "XLSX", "ZIP") if fmt.lower() in lowered or fmt in text),
                "event_fields_observed": ",".join(field for field in ("건축인허가", "착공", "사용승인", "건축물대장") if field in text),
                "expected_signal": expected,
                "page_excerpt": compact_text(text),
            }
        )
    return rows


def final_status(operation_inventory: list[dict[str, Any]], bulk_inventory: list[dict[str, Any]]) -> dict[str, Any]:
    event_specific = [
        row
        for row in operation_inventory
        if row["event_specific_candidate"].startswith("Y") and row["actual_row_received"] == "Y"
    ]
    direct_historical_bulk = [
        row
        for row in bulk_inventory
        if row["historical_archive_confirmed"] == "Y" and row["direct_download_confirmed"] == "Y"
    ]
    if event_specific:
        status = "continue_event_specific_api_readiness"
        route = "event_specific_api"
        reason = "At least one event-specific operation candidate returned an actual row."
    elif direct_historical_bulk:
        status = "switch_to_bulk_pipeline"
        route = "historical_bulk"
        reason = "Direct historical bulk archive was confirmed."
    else:
        status = "blocked_pending_broad_collection_pilot"
        route = "proceed_to_broad_collection_pilot_after_manual_review"
        reason = "No permit/start/approval-specific operation was found, and no unauthenticated direct historical bulk archive was confirmed."
    return {
        "as_of": datetime.now().isoformat(timespec="seconds"),
        "experiment": "O1_B1_event_specific_collection_route",
        "source_status": status,
        "selected_collection_route": route,
        "reason": reason,
        "event_specific_operation_count": len(event_specific),
        "bulk_page_count": len(bulk_inventory),
        "historical_backtest": "prohibited",
        "nationwide_row_collection": "prohibited",
        "production_feature_table": "prohibited",
        "next_action": "Run broad collection + event-date post-filter pilot only if manual review confirms no usable bulk download route.",
    }


def main() -> int:
    operations, probes = operation_rows()
    bulk = bulk_rows()
    write_csv(PROCESSED_DIR / "buildinghub_operation_inventory.csv", operations)
    write_csv(PROCESSED_DIR / "buildinghub_event_endpoint_probe.csv", probes)
    write_csv(PROCESSED_DIR / "buildinghub_bulk_download_inventory.csv", bulk)
    write_json(PROCESSED_DIR / "buildinghub_source_final_status.json", final_status(operations, bulk))
    print(f"operation candidates: {len(operations)}")
    print(f"operation probes: {len(probes)}")
    print(f"actual row operations: {sum(1 for row in probes if row['actual_row_received'] == 'Y')}")
    print(f"bulk pages checked: {len(bulk)}")
    print(f"status: {final_status(operations, bulk)['source_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
