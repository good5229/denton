#!/usr/bin/env python3
"""Phase52 BuildingHUB permit/start/approval event features for Goyang/Pohang."""

from __future__ import annotations

import hashlib
import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

from kosis_common import load_env


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase52_building_permit_events"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
ENDPOINT = "http://apis.data.go.kr/1613000/ArchPmsHubService/getApBasisOulnInfo"
TARGET_SIGUNGU = {
    "41281": ("고양시", "덕양구"),
    "41285": ("고양시", "일산동구"),
    "41287": ("고양시", "일산서구"),
    "47111": ("포항시", "남구"),
    "47113": ("포항시", "북구"),
}


def data_go_key() -> str:
    env = load_env()
    for name in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING"):
        if env.get(name):
            return str(env[name])
    raise SystemExit("DATA_GO_KR_DECODING or DATA_GO_KR_ENCODING not found in .env")


def cache_path(params: dict[str, Any]) -> Path:
    clean = {k: v for k, v in params.items() if k != "serviceKey"}
    key = hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:18]
    return RAW / f"ap_basis_{clean['sigunguCd']}_{clean['bjdongCd']}_{clean['pageNo']}_{key}.json"


def request_page(params: dict[str, Any]) -> dict[str, Any]:
    RAW.mkdir(parents=True, exist_ok=True)
    path = cache_path(params)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{ENDPOINT}?{query}", headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    context = None
    try:
        import certifi  # type: ignore

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = None
    try:
        with urllib.request.urlopen(request, timeout=90, context=context) as response:
            text = response.read().decode("utf-8-sig", errors="replace")
            data = json.loads(text) if text.strip() else {}
            payload = {
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type", ""),
                "request_parameters": {k: v for k, v in params.items() if k != "serviceKey"},
                "data": data,
                "error": "",
            }
    except Exception as exc:
        payload = {
            "http_status": "",
            "content_type": "",
            "request_parameters": {k: v for k, v in params.items() if k != "serviceKey"},
            "data": {},
            "error": repr(exc),
        }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.12)
    return payload


def response_body(payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("data", {}).get("response", {})
    body = response.get("body", {}) if isinstance(response, dict) else {}
    return body if isinstance(body, dict) else {}


def response_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = response_body(payload)
    items = body.get("items", {})
    if isinstance(items, dict):
        item = items.get("item", [])
        if isinstance(item, dict):
            return [item]
        if isinstance(item, list):
            return [x for x in item if isinstance(x, dict)]
    return []


def parse_float(x: Any) -> float:
    try:
        return float(str(x).strip()) if str(x).strip() else 0.0
    except Exception:
        return 0.0


def parse_day(x: Any) -> pd.Timestamp | None:
    s = str(x or "").strip()
    if len(s) == 8 and s.isdigit():
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    return None


def use_group(name: str) -> str:
    name = str(name or "").strip()
    if "주택" in name:
        return "주거"
    if any(k in name for k in ["근린", "판매", "업무"]):
        return "상업·업무"
    if any(k in name for k in ["공장", "창고", "위험물"]):
        return "산업·창고"
    if any(k in name for k in ["교육", "의료", "복지", "수련"]):
        return "공공·사회서비스"
    if any(k in name for k in ["운수", "숙박", "위락", "관광"]):
        return "숙박·운수·여가"
    return "기타"


def target_legal_dongs() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "buildinghub_legal_dong_request_universe.csv", encoding="cp949")
    df["sigungu_cd"] = df["sigungu_cd"].astype(str)
    df["bjdong_cd"] = df["bjdong_cd"].astype(str).str.zfill(5)
    return df[df["sigungu_cd"].isin(TARGET_SIGUNGU)].drop_duplicates(["sigungu_cd", "bjdong_cd"])


def collect() -> tuple[pd.DataFrame, pd.DataFrame]:
    key = data_go_key()
    legal = target_legal_dongs()
    rows: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for i, r in enumerate(legal.itertuples(index=False), start=1):
        sigungu = str(r.sigungu_cd)
        bjdong = str(r.bjdong_cd)
        base = {"serviceKey": key, "_type": "json", "numOfRows": 1000, "sigunguCd": sigungu, "bjdongCd": bjdong}
        first = request_page({**base, "pageNo": 1})
        body = response_body(first)
        total = int(body.get("totalCount") or 0)
        pages = max(1, (total + 999) // 1000)
        payloads = [first]
        for page in range(2, pages + 1):
            payloads.append(request_page({**base, "pageNo": page}))
        got = 0
        for payload in payloads:
            for item in response_items(payload):
                got += 1
                city, gu = TARGET_SIGUNGU[sigungu]
                main_name = item.get("mainPurpsCdNm", "")
                rows.append(
                    {
                        "city": city,
                        "general_gu": gu,
                        "sigungu_cd": sigungu,
                        "bjdong_cd": bjdong,
                        "legal_dong_name": getattr(r, "bjdong_name", ""),
                        "permit_register_pk": item.get("mgmPmsrgstPk", ""),
                        "building_register_pk": item.get("mgmBldrgstPk", ""),
                        "main_purpose_name": main_name,
                        "use_group": use_group(main_name),
                        "total_floor_area": parse_float(item.get("totArea")),
                        "site_area": parse_float(item.get("platArea")),
                        "permit_date": parse_day(item.get("archPmsDay")),
                        "start_date": parse_day(item.get("realStcnsDay")),
                        "approval_date": parse_day(item.get("useAprDay")),
                        "created_at": parse_day(item.get("crtnDay")),
                    }
                )
        manifest.append({"sigungu_cd": sigungu, "bjdong_cd": bjdong, "total_count": total, "pages": pages, "received_rows": got})
        if i % 50 == 0:
            print(f"collected legal_dongs={i}/{len(legal)} rows={len(rows)}", flush=True)
    return pd.DataFrame(rows), pd.DataFrame(manifest)


def monthly(events: pd.DataFrame) -> pd.DataFrame:
    long_rows = []
    for event_col, event_name in [
        ("permit_date", "허가"),
        ("start_date", "착공"),
        ("approval_date", "사용승인"),
    ]:
        sub = events.dropna(subset=[event_col]).copy()
        sub["period"] = pd.to_datetime(sub[event_col]).dt.to_period("M").astype(str)
        sub = sub[sub["period"].between("2021-01", "2026-06")]
        if sub.empty:
            continue
        agg = (
            sub.groupby(["city", "general_gu", "sigungu_cd", "bjdong_cd", "legal_dong_name", "use_group", "period"], as_index=False)
            .agg(event_count=("permit_register_pk", "count"), event_floor_area=("total_floor_area", "sum"))
        )
        agg["event_type"] = event_name
        long_rows.append(agg)
    if not long_rows:
        return pd.DataFrame()
    return pd.concat(long_rows, ignore_index=True).sort_values(["city", "period", "event_type", "sigungu_cd", "bjdong_cd"])


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    events, manifest = collect()
    monthly_df = monthly(events)
    events_path = PROCESSED / "partial_stats_phase52_building_permit_events_goyang_pohang.csv"
    monthly_path = PROCESSED / "partial_stats_phase52_building_permit_legal_dong_monthly.csv"
    manifest_path = PROCESSED / "partial_stats_phase52_building_permit_collection_manifest.csv"
    status_path = PROCESSED / "partial_stats_phase52_status.json"
    report_path = REPORTS / "partial_statistics_estimation_phase52_building_permit_events.md"
    events.to_csv(events_path, index=False, encoding="utf-8-sig")
    monthly_df.to_csv(monthly_path, index=False, encoding="utf-8-sig")
    manifest.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    summary = (
        monthly_df.groupby(["city", "event_type"], as_index=False)
        .agg(monthly_rows=("period", "count"), event_count=("event_count", "sum"), event_floor_area=("event_floor_area", "sum"))
        if len(monthly_df)
        else pd.DataFrame()
    )
    status = {
        "run_id": "partial_statistics_estimation_phase52_building_permit_events",
        "source": "국토교통부_건축HUB_건축인허가정보 서비스/getApBasisOulnInfo",
        "source_url": "https://www.data.go.kr/data/15136267/openapi.do",
        "target_legal_dongs": int(len(manifest)),
        "raw_event_rows": int(len(events)),
        "monthly_rows_2021_2026": int(len(monthly_df)),
        "summary": summary.to_dict(orient="records"),
        "guardrail": "legal-dong/month event features; administrative-dong allocation requires legal-to-admin mapping",
    }
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Phase52 건축인허가 이벤트 월별 보강자료",
        "",
        "## 결론",
        "",
        "- 공공데이터포털 키로 건축HUB 건축인허가 기본개요 API를 호출해 고양시·포항시 현행 법정동 전체의 허가·착공·사용승인 이벤트를 수집했다.",
        "- 2021-01~2026-06 월별 법정동×용도그룹 피처를 생성했으며, 건설업의 월별 생산시점 전환과 부동산업의 신규 공급 흐름 보강에 사용할 수 있다.",
        "- 단, API는 법정동 기반이므로 행정동 배분에는 법정동→행정동 공식 매핑 또는 주소/좌표 보강이 필요하다.",
        "",
        "## 수집 요약",
        "",
        f"- 대상 법정동: {len(manifest)}개",
        f"- 원천 이벤트 행: {len(events):,}행",
        f"- 2021~2026 월별 피처 행: {len(monthly_df):,}행",
        "",
        "| 도시 | 이벤트 | 월별 행 | 이벤트 수 | 이벤트 연면적 |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for _, r in summary.iterrows():
        lines.append(
            f"| {r['city']} | {r['event_type']} | {int(r['monthly_rows'])} | {int(r['event_count'])} | {r['event_floor_area']:,.0f} |"
        )
    lines += [
        "",
        "## 산출 파일",
        "",
        f"- `{events_path.relative_to(ROOT)}`",
        f"- `{monthly_path.relative_to(ROOT)}`",
        f"- `{manifest_path.relative_to(ROOT)}`",
        f"- `{status_path.relative_to(ROOT)}`",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
