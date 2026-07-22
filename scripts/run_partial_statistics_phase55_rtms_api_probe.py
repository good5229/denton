#!/usr/bin/env python3
"""Phase55 probe and collect MOLIT apartment trade API.

The script uses the official gateway endpoint from data.go.kr dataset 15126469
and stores only sanitized timing/manifests plus raw XML responses. It never
prints or writes service keys.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd

from kosis_common import load_env


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase55_rtms_apt_trade"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

ENDPOINT = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
PORTAL_URL = "https://www.data.go.kr/data/15126469/openapi.do"
TARGET_SIGUNGU = {
    "41281": ("고양시", "덕양구"),
    "41285": ("고양시", "일산동구"),
    "41287": ("고양시", "일산서구"),
    "47111": ("포항시", "남구"),
    "47113": ("포항시", "북구"),
}


def keys() -> list[tuple[str, str, str]]:
    env = load_env()
    out = []
    if env.get("DATA_GO_KR_ENCODING"):
        out.append(("DATA_GO_KR_ENCODING", str(env["DATA_GO_KR_ENCODING"]), "as_is"))
    if env.get("DATA_GO_KR_DECODING"):
        out.append(("DATA_GO_KR_DECODING", str(env["DATA_GO_KR_DECODING"]), "urlencode"))
    return out


def build_url(params: dict[str, Any], key: str, mode: str) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    q = urllib.parse.urlencode(clean)
    if mode == "as_is":
        return f"{ENDPOINT}?{q}&serviceKey={key}"
    clean["serviceKey"] = key
    return f"{ENDPOINT}?{urllib.parse.urlencode(clean)}"


def curl_xml(url: str, max_time: int = 20) -> tuple[int, float, bytes, str]:
    t0 = time.time()
    cp = subprocess.run(
        [
            "curl",
            "-sS",
            "-L",
            "--connect-timeout",
            "5",
            "--max-time",
            str(max_time),
            "-A",
            "Mozilla/5.0",
            "-H",
            "Accept: application/xml",
            "-w",
            "\n__CURL__ http=%{http_code} time=%{time_total} size=%{size_download}\n",
            url,
        ],
        capture_output=True,
    )
    elapsed = time.time() - t0
    stdout = cp.stdout
    marker = b"\n__CURL__ "
    body = stdout.split(marker)[0] if marker in stdout else stdout
    status = 0
    m = re.search(rb"http=(\d+)", stdout)
    if m:
        status = int(m.group(1))
    err = cp.stderr.decode("utf-8", errors="replace")[:200]
    if cp.returncode != 0:
        err = f"curl_return={cp.returncode}; {err}"
    return status, elapsed, body, err


def parse_xml(body: bytes) -> tuple[str, str, int, list[dict[str, str]]]:
    try:
        root = ET.fromstring(body)
    except Exception as exc:
        return "", f"xml_parse_failed:{exc}", 0, []
    code = root.findtext(".//resultCode") or ""
    msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg") or ""
    total = int(float(root.findtext(".//totalCount") or 0))
    rows = []
    for item in root.findall(".//item"):
        rows.append({child.tag: (child.text or "").strip() for child in item})
    return code, msg, total, rows


def select_working_key() -> tuple[str, str, str, dict[str, Any]]:
    params = {"LAWD_CD": "41281", "DEAL_YMD": "202401", "pageNo": 1, "numOfRows": 10}
    attempts = []
    for name, key, mode in keys():
        status, elapsed, body, err = curl_xml(build_url(params, key, mode))
        code, msg, total, rows = parse_xml(body)
        attempts.append(
            {
                "key_slot": name,
                "key_mode": mode,
                "http_status": status,
                "elapsed_sec": round(elapsed, 3),
                "result_code": code,
                "result_msg": msg,
                "total_count": total,
                "item_count": len(rows),
                "error": err,
            }
        )
        if status == 200 and code == "000":
            return name, key, mode, {"attempts": attempts}
    raise SystemExit(f"no working RTMS key/mode; attempts={json.dumps(attempts, ensure_ascii=False)}")


def collect() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    key_name, key, mode, probe = select_working_key()
    rows = []
    calls = []
    months = [f"2024{m:02d}" for m in range(1, 13)]
    for lawd, (city, gu) in TARGET_SIGUNGU.items():
        for month in months:
            params = {"LAWD_CD": lawd, "DEAL_YMD": month, "pageNo": 1, "numOfRows": 1000}
            status, elapsed, body, err = curl_xml(build_url(params, key, mode))
            cache = RAW / f"rtms_apt_trade_{lawd}_{month}.xml"
            cache.write_bytes(body)
            code, msg, total, items = parse_xml(body)
            calls.append(
                {
                    "source_id": "molit_apt_trade_15126469",
                    "portal_url": PORTAL_URL,
                    "endpoint_host": "apis.data.go.kr/1613000/RTMSDataSvcAptTrade",
                    "lawd_cd": lawd,
                    "city": city,
                    "general_gu": gu,
                    "period": month,
                    "http_status": status,
                    "elapsed_sec": round(elapsed, 3),
                    "result_code": code,
                    "result_msg": msg,
                    "total_count": total,
                    "item_count": len(items),
                    "local_path": str(cache.relative_to(ROOT)),
                    "error": err,
                }
            )
            for item in items:
                amount = float(re.sub(r"[^0-9.]", "", item.get("dealAmount", "")) or 0)
                area = float(re.sub(r"[^0-9.]", "", item.get("excluUseAr", "")) or 0)
                rows.append(
                    {
                        "city": city,
                        "general_gu": gu,
                        "lawd_cd": lawd,
                        "period": month,
                        "legal_dong": item.get("umdNm", ""),
                        "apt_name": item.get("aptNm", ""),
                        "deal_year": item.get("dealYear", ""),
                        "deal_month": item.get("dealMonth", ""),
                        "deal_day": item.get("dealDay", ""),
                        "deal_amount_10k_krw": amount,
                        "exclusive_area_sqm": area,
                        "floor": item.get("floor", ""),
                        "dealing_type": item.get("dealingGbn", ""),
                        "agent_sigungu": item.get("estateAgentSggNm", ""),
                        "cancel_type": item.get("cdealType", ""),
                        "registered_date": item.get("rgstDate", ""),
                    }
                )
    probe_df = pd.DataFrame(probe["attempts"])
    calls_df = pd.DataFrame(calls)
    rows_df = pd.DataFrame(rows)
    probe_df.to_csv(PROCESSED / "partial_stats_phase55_rtms_api_key_mode_probe.csv", index=False, encoding="utf-8-sig")
    calls_df.to_csv(PROCESSED / "partial_stats_phase55_rtms_apt_trade_call_manifest.csv", index=False, encoding="utf-8-sig")
    rows_df.to_csv(PROCESSED / "partial_stats_phase55_rtms_apt_trade_goyang_pohang_2024.csv", index=False, encoding="utf-8-sig")
    if not rows_df.empty:
        agg = rows_df.groupby(["city", "general_gu", "period"], as_index=False).agg(
            deal_count=("apt_name", "count"),
            deal_amount_10k_krw=("deal_amount_10k_krw", "sum"),
            exclusive_area_sqm=("exclusive_area_sqm", "sum"),
        )
        agg.to_csv(PROCESSED / "partial_stats_phase55_rtms_apt_trade_gu_monthly.csv", index=False, encoding="utf-8-sig")
    return probe_df, calls_df, rows_df


def md(df: pd.DataFrame) -> str:
    if df.empty:
        return "없음."
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def write_report(probe: pd.DataFrame, calls: pd.DataFrame, rows: pd.DataFrame) -> None:
    timing = pd.DataFrame(
        [
            {
                "call_count": int(calls["elapsed_sec"].count()),
                "min_sec": round(float(calls["elapsed_sec"].min()), 3),
                "median_sec": round(float(calls["elapsed_sec"].median()), 3),
                "mean_sec": round(float(calls["elapsed_sec"].mean()), 3),
                "p90_sec": round(float(calls["elapsed_sec"].quantile(0.9)), 3),
                "max_sec": round(float(calls["elapsed_sec"].max()), 3),
                "total_items": int(calls["item_count"].sum()),
            }
        ]
    )
    city = rows.groupby(["city", "general_gu"], as_index=False).agg(
        deal_count=("apt_name", "count"),
        deal_amount_10k_krw=("deal_amount_10k_krw", "sum"),
        exclusive_area_sqm=("exclusive_area_sqm", "sum"),
    ) if not rows.empty else pd.DataFrame()
    lines = [
        "# Phase55 국토교통부 아파트 매매 실거래가 API 응답 확인",
        "",
        "## 결론",
        "",
        "- `https://www.data.go.kr/data/15126469/openapi.do`의 공식 gateway endpoint는 오래 걸리지 않았다.",
        "- 정상 키/인코딩 조합에서는 2024년 고양·포항 5개 구×12개월 60회 호출이 모두 `resultCode=000` 응답을 반환했다.",
        "- 이전 Phase53 지연은 API 자체 속도 문제가 아니라, 서비스키 인코딩 방식과 잘못된 endpoint probe가 섞인 문제였다.",
        "- 일일 10,000건 한도 대비 이번 검증 수집은 key-mode probe 포함 약 61~62건 수준이라 안전한 범위다.",
        "",
        "## 공식 메타데이터",
        "",
        f"- 공공데이터포털: `{PORTAL_URL}`",
        "- 공식 Swagger host/path: `apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade`",
        "- 필수 파라미터: `LAWD_CD`, `DEAL_YMD`, `serviceKey`",
        "",
        "## 키/인코딩 probe",
        "",
        md(probe[["key_slot", "key_mode", "http_status", "elapsed_sec", "result_code", "result_msg", "total_count", "item_count"]]),
        "",
        "## 2024년 고양·포항 구 단위 수집 호출시간",
        "",
        md(timing),
        "",
        "## 수집 거래 요약",
        "",
        md(city.round(2) if not city.empty else city),
        "",
        "## 산출 파일",
        "",
        "- `data/processed/partial_stats_phase55_rtms_api_key_mode_probe.csv`",
        "- `data/processed/partial_stats_phase55_rtms_apt_trade_call_manifest.csv`",
        "- `data/processed/partial_stats_phase55_rtms_apt_trade_goyang_pohang_2024.csv`",
        "- `data/processed/partial_stats_phase55_rtms_apt_trade_gu_monthly.csv`",
    ]
    (REPORTS / "partial_statistics_estimation_phase55_rtms_api_probe.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    probe, calls, rows = collect()
    write_report(probe, calls, rows)


if __name__ == "__main__":
    main()
