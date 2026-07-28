#!/usr/bin/env python3
"""Probe related MOLIT RTMS APIs without printing service keys."""

from __future__ import annotations

import ssl
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from kosis_common import load_env


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase152_rtms_nonres_trade_history"

APIS = [
    {
        "public_data_pk": "15126463",
        "name": "국토교통부_상업업무용 부동산 매매 실거래가 자료",
        "url": "https://www.data.go.kr/data/15126463/openapi.do",
        "endpoint": "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade",
        "model_use": "682 거래·중개서비스축, 상업업무용 매매",
    },
    {
        "public_data_pk": "15126472",
        "name": "국토교통부_단독/다가구 전월세 실거래가 자료",
        "url": "https://www.data.go.kr/data/15126472/openapi.do",
        "endpoint": "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent",
        "model_use": "681 임대흐름·682 중개서비스축, 비아파트 임대차",
    },
    {
        "public_data_pk": "15126474",
        "name": "국토교통부_아파트 전월세 실거래가 자료",
        "url": "https://www.data.go.kr/data/15126474/openapi.do",
        "endpoint": "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
        "model_use": "681 임대흐름·682 중개서비스축, 아파트 임대차",
    },
    {
        "public_data_pk": "15126475",
        "name": "국토교통부_오피스텔 전월세 실거래가 자료",
        "url": "https://www.data.go.kr/data/15126475/openapi.do",
        "endpoint": "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent",
        "model_use": "681 임대흐름·682 중개서비스축, 오피스텔 임대차",
    },
]


def env_key() -> tuple[str, str]:
    env = load_env()
    for name in ("DATA_GO_KR_ENCODING", "DATA_GO_KR_DECODING"):
        if env.get(name):
            return name, str(env[name])
    raise SystemExit("DATA_GO_KR key not found")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    key_name, key = env_key()
    ctx = ssl._create_unverified_context()
    rows = []
    for api in APIS:
        params = {
            "LAWD_CD": "41281",
            "DEAL_YMD": "202301",
            "serviceKey": key,
            "numOfRows": "5",
            "pageNo": "1",
        }
        status = ""
        code = ""
        msg = ""
        total = ""
        item_count = ""
        err = ""
        try:
            url = api["endpoint"] + "?" + urlencode(params, safe="%")
            with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20, context=ctx) as resp:
                status = str(resp.status)
                body = resp.read(300000)
            root = ET.fromstring(body)
            code = root.findtext(".//resultCode") or ""
            msg = root.findtext(".//resultMsg") or ""
            total = root.findtext(".//totalCount") or ""
            item_count = str(len(root.findall(".//item")))
        except HTTPError as exc:
            status = str(exc.code)
            err = f"HTTPError {exc.code}"
        except URLError as exc:
            err = f"URLError {str(exc.reason)[:120]}"
        except Exception as exc:
            err = f"{type(exc).__name__}: {str(exc)[:120]}"
        rows.append(
            {
                **{k: v for k, v in api.items() if k != "endpoint"},
                "endpoint_host_path": api["endpoint"].replace("https://", ""),
                "probe_key_slot": key_name,
                "probe_lawd_cd": "41281",
                "probe_deal_ymd": "202301",
                "http_status": status,
                "result_code": code,
                "result_msg": msg,
                "total_count": total,
                "item_count": item_count,
                "access_status": "usable" if status == "200" and code == "000" else "needs_approval_or_unavailable",
                "error": err,
                "probed_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "phase152_rtms_related_api_probe.csv", index=False, encoding="utf-8-sig")
    print(df[["public_data_pk", "access_status", "http_status", "result_code", "total_count", "item_count"]].to_string(index=False))


if __name__ == "__main__":
    main()
