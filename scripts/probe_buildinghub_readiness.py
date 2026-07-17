from __future__ import annotations

import hashlib
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, load_env, parse_number, write_csv, write_json


ENDPOINT = "http://apis.data.go.kr/1613000/ArchPmsHubService/getApBasisOulnInfo"
SOURCE_ID = "data_go_kr_buildinghub_ap_basis"
REQUEST_INTERVAL_SECONDS = 0.5
MAXIMUM_RETRIES = 3
TODAY = datetime.now().date().isoformat()
VINTAGE_DIR = RAW_DIR / "buildinghub" / f"vintage_{datetime.now().strftime('%Y%m%d')}"

CORE_FIELD_CANDIDATES = {
    "sigunguCd": "sigungu_cd",
    "bjdongCd": "bjdong_cd",
    "platGbCd": "plat_gb_cd",
    "bun": "bun",
    "ji": "ji",
    "mgmBldrgstPk": "building_register_pk",
    "mgmPmsrgstPk": "permit_register_pk",
    "archPmsDay": "permit_date",
    "realStcnsDay": "start_date",
    "stcnsSchedDay": "scheduled_start_date",
    "stcnsDelayDay": "start_delay_date",
    "useAprDay": "approval_date",
    "mainPurpsCd": "main_purpose_code",
    "mainPurpsCdNm": "main_purpose_name",
    "totArea": "total_floor_area",
    "platArea": "site_area",
    "bcRat": "building_coverage_ratio",
    "vlRat": "floor_area_ratio",
    "hhldCnt": "household_count",
    "hoCnt": "unit_count",
    "crtnDay": "created_at",
    "updtDay": "updated_at",
}


def data_go_key() -> str:
    env = load_env()
    for name in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING"):
        if env.get(name):
            return str(env[name])
    raise SystemExit("DATA_GO_KR_DECODING or DATA_GO_KR_ENCODING not found in .env")


def cache_key(params: dict[str, Any]) -> str:
    canonical = json.dumps({"endpoint": ENDPOINT, "params": params}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def build_request_url(params: dict[str, Any]) -> str:
    clean = {key: value for key, value in params.items() if value is not None}
    return f"{ENDPOINT}?{urllib.parse.urlencode(clean)}"


def request_json(params: dict[str, Any], request_id: str, manifest_rows: list[dict[str, Any]]) -> dict[str, Any]:
    VINTAGE_DIR.mkdir(parents=True, exist_ok=True)
    key = cache_key(params)
    cache_path = VINTAGE_DIR / f"{request_id}_{key}.json"
    started = datetime.now().isoformat(timespec="seconds")
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        manifest_rows.append(manifest_row(request_id, params, payload, cache_path, started, "skipped_cached", 0))
        return payload

    url = build_request_url(params)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, application/xml, text/xml, */*",
        },
    )
    context = None
    try:
        import certifi  # type: ignore

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = None

    last_payload: dict[str, Any] = {}
    for retry in range(MAXIMUM_RETRIES):
        if retry:
            time.sleep(REQUEST_INTERVAL_SECONDS * (2**retry))
        try:
            with urllib.request.urlopen(request, timeout=60, context=context) as response:
                body = response.read()
                text = body.decode("utf-8-sig", errors="replace")
                try:
                    data = json.loads(text) if text.strip() else {}
                    parse_error = ""
                except json.JSONDecodeError as exc:
                    data = {}
                    parse_error = str(exc)
                payload = {
                    "request_id": request_id,
                    "retrieval_timestamp": started,
                    "endpoint": ENDPOINT,
                    "request_parameters": {k: v for k, v in params.items() if k != "serviceKey"},
                    "http_status": response.status,
                    "content_type": response.headers.get("Content-Type", ""),
                    "body_size": len(body),
                    "response_hash": hashlib.sha256(body).hexdigest(),
                    "text_prefix": text[:500],
                    "data": data,
                    "parse_error": parse_error,
                }
        except urllib.error.HTTPError as exc:
            body = exc.read()
            payload = {
                "request_id": request_id,
                "retrieval_timestamp": started,
                "endpoint": ENDPOINT,
                "request_parameters": {k: v for k, v in params.items() if k != "serviceKey"},
                "http_status": exc.code,
                "content_type": exc.headers.get("Content-Type", ""),
                "body_size": len(body),
                "response_hash": hashlib.sha256(body).hexdigest(),
                "text_prefix": body.decode("utf-8-sig", errors="replace")[:500],
                "data": {},
                "parse_error": "",
            }
        except Exception as exc:
            payload = {
                "request_id": request_id,
                "retrieval_timestamp": started,
                "endpoint": ENDPOINT,
                "request_parameters": {k: v for k, v in params.items() if k != "serviceKey"},
                "http_status": "",
                "content_type": "",
                "body_size": 0,
                "response_hash": "",
                "text_prefix": repr(exc),
                "data": {},
                "parse_error": repr(exc),
            }
        last_payload = payload
        status = response_status(payload)
        if status not in {"empty_body", "http_error", "rate_limited"}:
            break

    write_json(cache_path, last_payload)
    manifest_rows.append(manifest_row(request_id, params, last_payload, cache_path, started, response_status(last_payload), retry))
    time.sleep(REQUEST_INTERVAL_SECONDS)
    return last_payload


def response_body(data: dict[str, Any]) -> dict[str, Any]:
    response = data.get("response") if isinstance(data, dict) else {}
    body = response.get("body") if isinstance(response, dict) else {}
    return body if isinstance(body, dict) else {}


def response_header(data: dict[str, Any]) -> dict[str, Any]:
    response = data.get("response") if isinstance(data, dict) else {}
    header = response.get("header") if isinstance(response, dict) else {}
    return header if isinstance(header, dict) else {}


def xml_tag(text: str, tag: str) -> str:
    match = re.search(fr"<{tag}>(.*?)</{tag}>", text, re.S)
    return match.group(1).strip() if match else ""


def response_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = response_body(payload.get("data", {}))
    items = body.get("items", {})
    if isinstance(items, dict):
        item = items.get("item", [])
        if isinstance(item, dict):
            return [item]
        if isinstance(item, list):
            return [row for row in item if isinstance(row, dict)]
    if isinstance(items, list):
        return [row for row in items if isinstance(row, dict)]
    return []


def response_status(payload: dict[str, Any]) -> str:
    if not payload.get("http_status"):
        return "http_error"
    if int(payload.get("http_status") or 0) >= 400:
        return "http_error"
    if not int(payload.get("body_size") or 0):
        return "empty_body"
    if payload.get("parse_error"):
        prefix = str(payload.get("text_prefix") or "")
        if prefix.lstrip().startswith("<response"):
            result_code = xml_tag(prefix, "resultCode")
            if result_code == "00":
                return "success"
            return "api_error"
        return "parse_error"
    header = response_header(payload.get("data", {}))
    result_code = str(header.get("resultCode") or "")
    result_msg = str(header.get("resultMsg") or "")
    if result_code and result_code != "00":
        if "LIMIT" in result_msg.upper():
            return "rate_limited"
        return "api_error"
    return "success"


def manifest_row(
    request_id: str,
    params: dict[str, Any],
    payload: dict[str, Any],
    cache_path: Path,
    request_time: str,
    status: str,
    retry_count: int,
) -> dict[str, Any]:
    data = payload.get("data", {})
    body = response_body(data)
    header = response_header(data)
    if not header and payload.get("text_prefix"):
        header = {
            "resultCode": xml_tag(str(payload.get("text_prefix")), "resultCode"),
            "resultMsg": xml_tag(str(payload.get("text_prefix")), "resultMsg"),
        }
    rows = response_items(payload)
    return {
        "request_id": request_id,
        "endpoint": ENDPOINT,
        "sigungu_cd": params.get("sigunguCd", ""),
        "bjdong_cd": params.get("bjdongCd", ""),
        "page_no": params.get("pageNo", ""),
        "num_of_rows": params.get("numOfRows", ""),
        "request_time": request_time,
        "http_status": payload.get("http_status", ""),
        "content_type": payload.get("content_type", ""),
        "body_size": payload.get("body_size", ""),
        "result_code": header.get("resultCode", ""),
        "result_message": header.get("resultMsg", ""),
        "total_count": body.get("totalCount", ""),
        "returned_rows": len(rows),
        "cache_path": str(cache_path),
        "retry_count": retry_count,
        "status": status,
    }


def infer_type(value: Any) -> str:
    if value is None or value == "":
        return "missing"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    text = str(value)
    if re.fullmatch(r"\d{8}", text):
        return "yyyymmdd_string"
    if parse_number(text) is not None:
        return "numeric_string"
    return "string"


def is_valid_yyyymmdd(value: Any) -> bool:
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{8}", text):
        return False
    try:
        datetime.strptime(text, "%Y%m%d")
        return True
    except ValueError:
        return False


def schema_rows(sample: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for field, value in sample.items():
        rows.append(
            {
                "field_name": field,
                "standard_field_name": CORE_FIELD_CANDIDATES.get(field, ""),
                "raw_value": value,
                "inferred_type": infer_type(value),
                "nullable": "unknown_single_row",
                "description": "",
                "date_candidate": "Y" if ("Day" in field or "date" in field.lower()) else "N",
                "identifier_candidate": "Y" if field.endswith("Cd") or field.endswith("Pk") or field in {"bun", "ji"} else "N",
                "code_candidate": "Y" if field.endswith("Cd") else "N",
                "required_core_candidate": "Y" if field in CORE_FIELD_CANDIDATES else "N",
            }
        )
    return rows


def compact_sample_row(sample: dict[str, Any]) -> dict[str, Any]:
    out = {"source_id": SOURCE_ID, "retrieval_date": TODAY}
    out.update(sample)
    return out


def date_quality_rows(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = {
        "archPmsDay": "permit_date",
        "realStcnsDay": "start_date",
        "useAprDay": "approval_date",
    }
    out = []
    today_text = datetime.now().strftime("%Y%m%d")
    for raw_field, standard in fields.items():
        values = [row.get(raw_field) for row in samples]
        valid = [str(value).strip() for value in values if is_valid_yyyymmdd(value)]
        invalid = [value for value in values if str(value or "").strip() and not is_valid_yyyymmdd(value)]
        future = [value for value in valid if value > today_text]
        out.append(
            {
                "raw_field": raw_field,
                "standard_field": standard,
                "row_count": len(values),
                "valid_date_count": len(valid),
                "missing_date_count": sum(1 for value in values if value in (None, "")),
                "invalid_date_count": len(invalid),
                "future_date_count": len(future),
                "minimum_date": min(valid) if valid else "",
                "maximum_date": max(valid) if valid else "",
            }
        )
    return out


def sequence_flag(row: dict[str, Any]) -> str:
    permit = str(row.get("archPmsDay") or "")
    start = str(row.get("realStcnsDay") or "")
    approval = str(row.get("useAprDay") or "")
    valid = {name: is_valid_yyyymmdd(value) for name, value in {"permit": permit, "start": start, "approval": approval}.items()}
    if not any(valid.values()):
        return "unresolved"
    if not all(valid.values()):
        return "missing_intermediate"
    if permit <= start <= approval:
        return "valid"
    return "reversed"


def purpose_group(name: str) -> tuple[str, str, str]:
    text = str(name or "")
    if not text.strip():
        return "unknown", "", "missing_main_purpose"
    if any(token in text for token in ("주택", "아파트", "연립", "다세대", "다가구")):
        return "residential", "L00", "name_contains_residential_token"
    if any(token in text for token in ("공장", "창고")):
        return "industrial", "C00", "name_contains_industrial_token"
    if any(token in text for token in ("근린", "판매", "상업", "위락")):
        return "commercial", "L00", "name_contains_commercial_token"
    if "업무" in text:
        return "office", "L00", "name_contains_office_token"
    if "교육" in text:
        return "education", "P00", "name_contains_education_token"
    if "의료" in text:
        return "medical", "Q00", "name_contains_medical_token"
    if "숙박" in text:
        return "accommodation", "I00", "name_contains_accommodation_token"
    if text:
        return "other", "F00,L00", "fallback_named_purpose"
    return "unknown", "", "missing_main_purpose"


def parse_region_from_plat_plc(row: dict[str, Any]) -> tuple[str, str, str]:
    text = re.sub(r"\s+", " ", str(row.get("platPlc") or "")).strip()
    parts = text.split()
    sido = parts[0] if len(parts) >= 1 else ""
    sigungu = ""
    legal = ""
    if len(parts) >= 2:
        sigungu = parts[1]
    if len(parts) >= 3 and parts[1].endswith("시") and parts[2].endswith(("구", "군")):
        sigungu = f"{parts[1]} {parts[2]}"
        legal = parts[3] if len(parts) >= 4 else ""
    elif len(parts) >= 3:
        legal = parts[2]
    return sido, sigungu, legal


def feature_rows(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[tuple[str, str, str], float] = {}
    for sample in samples:
        sido, sigungu, _legal = parse_region_from_plat_plc(sample)
        area_key = f"{sido} {sigungu}".strip()
        purpose, _sector, _rule = purpose_group(str(sample.get("mainPurpsCdNm") or ""))
        area = parse_number(sample.get("totArea")) or 0.0
        for raw_date, event in (("archPmsDay", "permit"), ("realStcnsDay", "start"), ("useAprDay", "approval")):
            value = str(sample.get(raw_date) or "")
            if not is_valid_yyyymmdd(value) or not area_key:
                continue
            period = value[:6]
            rows[(area_key, period, f"{event}_count")] = rows.get((area_key, period, f"{event}_count"), 0.0) + 1
            rows[(area_key, period, f"{event}_floor_area")] = rows.get((area_key, period, f"{event}_floor_area"), 0.0) + area
            rows[(area_key, period, f"{purpose}_{event}_count")] = rows.get((area_key, period, f"{purpose}_{event}_count"), 0.0) + 1
            rows[(area_key, period, f"{purpose}_{event}_area")] = rows.get((area_key, period, f"{purpose}_{event}_area"), 0.0) + area
    out = []
    for (area_key, period, feature), value in sorted(rows.items()):
        out.append(
            {
                "sigungu_feature_key": area_key,
                "observation_period": period,
                "prediction_origin": "",
                "feature_name": feature,
                "feature_value": value,
                "first_eligible_period": "",
                "source_version": f"buildinghub_vintage_{datetime.now().strftime('%Y%m%d')}",
            }
        )
    return out


def main() -> int:
    service_key = data_go_key()
    base = {"serviceKey": service_key, "_type": "json", "pageNo": 1, "numOfRows": 1}
    probe_specs = [
        ("schema_sample_11680_10300", {"sigunguCd": "11680", "bjdongCd": "10300"}),
        ("query_a_sigungu_only", {"sigunguCd": "11680"}),
        ("query_b_empty_bjdong", {"sigunguCd": "11680", "bjdongCd": ""}),
        ("query_c_jongno_legal_dong", {"sigunguCd": "11110", "bjdongCd": "10100"}),
        ("query_c_busan_haeundae_legal_dong", {"sigunguCd": "26350", "bjdongCd": "10100"}),
        ("hist_202101_probe", {"sigunguCd": "11680", "bjdongCd": "10300", "startDate": "20210101", "endDate": "20210131"}),
        ("hist_202201_probe", {"sigunguCd": "11680", "bjdongCd": "10300", "startDate": "20220101", "endDate": "20220131"}),
        ("hist_202301_probe", {"sigunguCd": "11680", "bjdongCd": "10300", "startDate": "20230101", "endDate": "20230131"}),
        ("hist_202312_probe", {"sigunguCd": "11680", "bjdongCd": "10300", "startDate": "20231201", "endDate": "20231231"}),
    ]
    manifest: list[dict[str, Any]] = []
    payloads = []
    for request_id, extra in probe_specs:
        params = dict(base)
        params.update(extra)
        payloads.append(request_json(params, request_id, manifest))

    sample_payload = payloads[0]
    sample_rows = response_items(sample_payload)
    sample = sample_rows[0] if sample_rows else {}
    write_json(PROCESSED_DIR / "buildinghub_response_schema.json", {"source_id": SOURCE_ID, "sample_row": sample, "schema": schema_rows(sample)})
    write_csv(PROCESSED_DIR / "buildinghub_sample_row.csv", [compact_sample_row(sample)] if sample else [])
    write_csv(PROCESSED_DIR / "buildinghub_schema_fingerprint.csv", schema_rows(sample))

    all_samples: list[dict[str, Any]] = []
    for payload in payloads:
        all_samples.extend(response_items(payload))
    unique_samples = {str(row.get("mgmPmsrgstPk") or row): row for row in all_samples}
    samples = list(unique_samples.values())

    write_csv(PROCESSED_DIR / "buildinghub_request_manifest.csv", manifest)
    write_csv(PROCESSED_DIR / "buildinghub_date_quality_audit.csv", date_quality_rows(samples))
    write_csv(
        PROCESSED_DIR / "buildinghub_event_sequence_audit.csv",
        [
            {
                "mgm_pmsrgst_pk": row.get("mgmPmsrgstPk", ""),
                "plat_plc": row.get("platPlc", ""),
                "permit_date": row.get("archPmsDay", ""),
                "start_date": row.get("realStcnsDay", ""),
                "approval_date": row.get("useAprDay", ""),
                "date_sequence_flag": sequence_flag(row),
            }
            for row in samples
        ],
    )

    purposes = {}
    for row in samples:
        code = str(row.get("mainPurpsCd") or "")
        name = str(row.get("mainPurpsCdNm") or "")
        if code or name:
            group, sector, rule = purpose_group(name)
            purposes[(code, name)] = {
                "main_purpose_code": code,
                "main_purpose_name": name,
                "standard_group": group,
                "target_sector": sector,
                "mapping_rule": rule,
                "mapping_quality": "sample_observed_rule_based",
            }
    write_csv(PROCESSED_DIR / "buildinghub_main_purpose_crosswalk.csv", sorted(purposes.values(), key=lambda row: (row["main_purpose_code"], row["main_purpose_name"])))

    regions = {}
    for row in samples:
        sido, sigungu, legal = parse_region_from_plat_plc(row)
        key = (str(row.get("sigunguCd") or ""), str(row.get("bjdongCd") or ""))
        if key != ("", ""):
            regions[key] = {
                "sigungu_cd": key[0],
                "bjdong_cd": key[1],
                "sido_name": sido,
                "sigungu_name": sigungu,
                "legal_dong_name": legal,
                "sigungu_feature_key": f"{sido} {sigungu}".strip(),
                "mapping_method": "parsed_from_platPlc_sample",
                "mapping_quality": "sample_only_requires_official_code_table",
                "effective_from": "",
                "effective_to": "",
            }
    write_csv(PROCESSED_DIR / "buildinghub_region_crosswalk.csv", sorted(regions.values(), key=lambda row: (row["sigungu_cd"], row["bjdong_cd"])))
    write_csv(PROCESSED_DIR / "buildinghub_feature_table_pilot.csv", feature_rows(samples))
    write_csv(
        PROCESSED_DIR / "buildinghub_ml_ready_gate_status.csv",
        [
            {"gate": "access", "status": "pass", "evidence": "actual row received"},
            {"gate": "schema", "status": "partial", "evidence": "single-row schema fingerprint generated"},
            {"gate": "historical_coverage", "status": "probe_only", "evidence": "202101/202201/202301/202312 one-row probes logged"},
            {"gate": "regional_coverage", "status": "not_started", "evidence": "sample regions only"},
            {"gate": "region_crosswalk", "status": "partial", "evidence": "sample platPlc parsing only; official code table required"},
            {"gate": "event_quality", "status": "partial", "evidence": "single-row date audit generated"},
            {"gate": "vintage", "status": "partial", "evidence": "retrieval snapshot cache generated; publication lag not implemented"},
            {"gate": "feature_table", "status": "partial", "evidence": "pilot feature rows generated only when valid event dates exist"},
            {"gate": "ml_ready", "status": "blocked", "evidence": "all gates not passed"},
        ],
    )

    for path in [
        "buildinghub_sample_row.csv",
        "buildinghub_schema_fingerprint.csv",
        "buildinghub_request_manifest.csv",
        "buildinghub_date_quality_audit.csv",
        "buildinghub_event_sequence_audit.csv",
        "buildinghub_main_purpose_crosswalk.csv",
        "buildinghub_region_crosswalk.csv",
        "buildinghub_feature_table_pilot.csv",
        "buildinghub_ml_ready_gate_status.csv",
    ]:
        rows_text = (PROCESSED_DIR / path).read_text(encoding="cp949")
        (PROCESSED_DIR / path).write_text(rows_text, encoding="cp949")

    print(f"buildinghub requests logged: {len(manifest)}")
    print(f"unique sample rows: {len(samples)}")
    print(f"schema fields: {len(sample)}")
    print(f"vintage cache: {VINTAGE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
