#!/usr/bin/env python3
"""Build nationwide sigungu construction signals from PPS construction notices.

This script uses raw JSON pages cached by `collect_phase122_pps_bid_notices.py`.
The previous collector cached nationwide API pages but only wrote a processed
Goyang/Pohang subset.  Here we expand the raw pages into a nationwide candidate
indicator table for construction GVA spatial allocation.

It is intentionally conservative:

* It does not use target-year GRVA actuals.
* It separates `sigungu_exact` attribution from province-only or ambiguous rows.
* Missing raw months are reported rather than silently treated as zero.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase122_pps_bid_notices"
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "nationwide" / "pps_construction_nationwide_signal.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

TEXT_FIELDS = [
    "cnstrtsiteRgnNm",
    "bidNtceNm",
    "ntceInsttNm",
    "dminsttNm",
    "rgnLmtBidLocplcJdgmBssNm",
    "jntcontrctDutyRgnNm1",
    "jntcontrctDutyRgnNm2",
    "jntcontrctDutyRgnNm3",
    "incntvRgnNm1",
    "incntvRgnNm2",
    "incntvRgnNm3",
    "incntvRgnNm4",
]

KEEP_FIELDS = [
    "period",
    "bidNtceNo",
    "bidNtceOrd",
    "bidNtceDt",
    "bidNtceNm",
    "ntceInsttNm",
    "dminsttNm",
    "cnstrtsiteRgnNm",
    "rgnLmtBidLocplcJdgmBssNm",
    "mtltyAdvcPsblYnCnstwkNm",
    "mainCnsttyNm",
    "presmptPrce",
    "bdgtAmt",
    "asignBdgtAmt",
    "govsplyAmt",
    "bidNtceDtlUrl",
]

PROVINCE_ALIASES = {
    "서울": ["서울", "서울특별시"],
    "부산": ["부산", "부산광역시"],
    "대구": ["대구", "대구광역시"],
    "인천": ["인천", "인천광역시"],
    "광주": ["광주", "광주광역시"],
    "대전": ["대전", "대전광역시"],
    "울산": ["울산", "울산광역시"],
    "세종": ["세종", "세종시", "세종특별자치시"],
    "경기도": ["경기", "경기도"],
    "강원": ["강원", "강원도", "강원특별자치도"],
    "충북": ["충북", "충청북도"],
    "충남": ["충남", "충청남도"],
    "전북": ["전북", "전라북도", "전북특별자치도"],
    "전남": ["전남", "전라남도"],
    "경북": ["경북", "경상북도"],
    "경남": ["경남", "경상남도"],
    "제주": ["제주", "제주도", "제주특별자치도"],
}


def month_range(start: str, end: str) -> list[str]:
    y, m = int(start[:4]), int(start[4:])
    ey, em = int(end[:4]), int(end[4:])
    out: list[str] = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}{m:02d}")
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


def normalize_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    body = data.get("response", {}).get("body", {})
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    return []


def raw_pages(raw_dir: Path, period: str) -> list[Path]:
    return sorted(raw_dir.glob(f"cnstwk_{period}_*.json")) + sorted(raw_dir.glob(f"cnstwk_pps_{period}_*.json"))


def number(row: dict[str, Any], key: str) -> float:
    value = str(row.get(key, "") or "").replace(",", "").strip()
    try:
        return float(value) if value else 0.0
    except ValueError:
        return 0.0


def amount(row: dict[str, Any]) -> float:
    for key in ["presmptPrce", "bdgtAmt", "asignBdgtAmt", "govsplyAmt"]:
        v = number(row, key)
        if v > 0:
            return v
    return 0.0


def load_sigungu_reference() -> pd.DataFrame:
    sig = pd.read_csv(OUT / "annual_sigungu_activity_error_audit.csv")
    ref = sig[["quarter_region", "province_full", "city"]].drop_duplicates().copy()
    ref["city_norm"] = ref["city"].astype(str).str.replace(" ", "", regex=False)
    ref["province_aliases"] = ref["quarter_region"].map(PROVINCE_ALIASES)
    ref["province_aliases"] = ref["province_aliases"].apply(lambda x: x if isinstance(x, list) else [])
    return ref


def row_text(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(c, "") or "") for c in TEXT_FIELDS)


def attribute_region(row: dict[str, Any], ref: pd.DataFrame) -> dict[str, Any]:
    text = row_text(row)
    text_norm = text.replace(" ", "")
    province_hits = []
    for province, aliases in PROVINCE_ALIASES.items():
        if any(alias and alias in text for alias in aliases):
            province_hits.append(province)
    candidates = []
    for r in ref.itertuples(index=False):
        if r.city_norm and r.city_norm in text_norm:
            province_match = bool(set(province_hits) & set([r.quarter_region]))
            # For unique non-gu city/county names, city hit alone is informative.
            candidates.append(
                {
                    "quarter_region": r.quarter_region,
                    "province_full": r.province_full,
                    "city": r.city,
                    "province_match": province_match,
                }
            )
    if candidates:
        cdf = pd.DataFrame(candidates)
        if cdf["province_match"].any():
            cdf = cdf[cdf["province_match"]]
        cdf = cdf.drop_duplicates(["quarter_region", "city"])
        if len(cdf) == 1:
            r = cdf.iloc[0]
            return {
                "attribution_status": "sigungu_exact",
                "quarter_region": r["quarter_region"],
                "province_full": r["province_full"],
                "city": r["city"],
                "province_hits": ",".join(province_hits),
            }
        return {
            "attribution_status": "ambiguous_sigungu",
            "quarter_region": "",
            "province_full": "",
            "city": "",
            "province_hits": ",".join(province_hits),
        }
    if len(province_hits) == 1:
        return {
            "attribution_status": "province_only",
            "quarter_region": province_hits[0],
            "province_full": "",
            "city": "",
            "province_hits": province_hits[0],
        }
    if len(province_hits) > 1:
        return {
            "attribution_status": "ambiguous_province",
            "quarter_region": "",
            "province_full": "",
            "city": "",
            "province_hits": ",".join(province_hits),
        }
    return {
        "attribution_status": "unattributed",
        "quarter_region": "",
        "province_full": "",
        "city": "",
        "province_hits": "",
    }


def load_rows(start: str, end: str, raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    ref = load_sigungu_reference()
    rows = []
    manifest = []
    for period in month_range(start, end):
        pages = raw_pages(raw_dir, period)
        item_count = 0
        for path in pages:
            data = json.loads(path.read_text(encoding="utf-8"))
            items = normalize_items(data)
            item_count += len(items)
            for item in items:
                out = {k: item.get(k, "") for k in KEEP_FIELDS if k != "period"}
                out["period"] = period
                out["amount_won"] = amount(item)
                out.update(attribute_region(item, ref))
                rows.append(out)
        manifest.append({"period": period, "raw_pages": len(pages), "raw_items": item_count})
    return pd.DataFrame(rows), pd.DataFrame(manifest)


def summarize(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if rows.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    rows["year"] = rows["period"].astype(str).str[:4].astype(int)
    rows["month"] = rows["period"].astype(str).str[4:6].astype(int)
    rows["amount_eok"] = rows["amount_won"] / 1e8
    status = (
        rows.groupby(["period", "attribution_status"], as_index=False)
        .agg(notices=("bidNtceNo", "count"), amount_eok=("amount_eok", "sum"))
        .sort_values(["period", "attribution_status"])
    )
    sigungu = (
        rows[rows["attribution_status"].eq("sigungu_exact")]
        .groupby(["quarter_region", "province_full", "city", "year"], as_index=False)
        .agg(pps_construction_notices=("bidNtceNo", "count"), pps_construction_amount_eok=("amount_eok", "sum"))
    )
    province = (
        rows[rows["quarter_region"].astype(str).ne("")]
        .groupby(["quarter_region", "year"], as_index=False)
        .agg(pps_construction_notices=("bidNtceNo", "count"), pps_construction_amount_eok=("amount_eok", "sum"))
    )
    return status, sigungu, province


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="202301")
    parser.add_argument("--end", default="202301")
    parser.add_argument("--raw-dir", default=str(RAW.relative_to(ROOT)))
    parser.add_argument("--output-suffix", default="")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    raw_dir = (ROOT / args.raw_dir).resolve() if not Path(args.raw_dir).is_absolute() else Path(args.raw_dir)
    rows, manifest = load_rows(args.start, args.end, raw_dir)
    status, sigungu, province = summarize(rows)
    tag = f"{args.start}_{args.end}{('_' + args.output_suffix) if args.output_suffix else ''}"
    rows.to_csv(OUT / f"pps_construction_nationwide_rows_{tag}.csv", index=False, encoding="utf-8-sig")
    manifest.to_csv(OUT / f"pps_construction_nationwide_manifest_{tag}.csv", index=False, encoding="utf-8-sig")
    status.to_csv(OUT / f"pps_construction_nationwide_attribution_status_{tag}.csv", index=False, encoding="utf-8-sig")
    sigungu.to_csv(OUT / f"pps_construction_nationwide_sigungu_year_{tag}.csv", index=False, encoding="utf-8-sig")
    province.to_csv(OUT / f"pps_construction_nationwide_province_year_{tag}.csv", index=False, encoding="utf-8-sig")

    status_summary = (
        rows.groupby("attribution_status", as_index=False)
        .agg(notices=("bidNtceNo", "count"), amount_eok=("amount_won", lambda s: float(s.sum()) / 1e8))
        .sort_values("notices", ascending=False)
        if not rows.empty
        else pd.DataFrame()
    )
    report = f"""# 조달청 공사공고 전국 시군구 신호 변환

생성시각: {CREATED_AT}

## 목적

현재 시군구×건설업 WAPE 병목은 시군구 내부 공간배분 문제다.
조달청 공사공고 raw cache를 전국 시군구 후보 지표로 변환할 수 있는지 확인한다.

## 처리 범위

- 기간: {args.start}~{args.end}
- 입력: `{raw_dir.relative_to(ROOT) if raw_dir.is_relative_to(ROOT) else raw_dir}/cnstwk*_YYYYMM_*.json`
- 출력: `nationwide/outputs/pps_construction_nationwide_*_{tag}.csv`

## raw 수집 매니페스트

{md_table(manifest, 3)}

## 귀속 상태

{md_table(status_summary.rename(columns={
    "attribution_status": "귀속상태",
    "notices": "공고수",
    "amount_eok": "금액_억원",
}), 3)}

## 시군구 정확 귀속 예시

{md_table(sigungu.sort_values("pps_construction_amount_eok", ascending=False).head(20).rename(columns={
    "quarter_region": "시도",
    "province_full": "광역명",
    "city": "시군구",
    "year": "연도",
    "pps_construction_notices": "공고수",
    "pps_construction_amount_eok": "금액_억원",
}), 3)}

## 판정

- 이 변환은 target-year GRVA actual을 사용하지 않는다.
- 단, `cnstrtsiteRgnNm`이 광역시도까지만 있는 공고가 많으면 시군구 건설업 공간배분에는 한계가 있다.
- 전국 2021~2023년 전체 공사공고 raw cache가 확보되면 `sigungu_exact` 행만 사용해 건설업 공간배분 후보로 시험할 수 있다.
- 공고지표는 공공공사 중심이므로 민간 건설경기까지 대표하지 못한다. 건축HUB 허가·착공·준공 면적과 결합하는 것이 다음 단계다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(status_summary.to_string(index=False) if not status_summary.empty else "no rows")
    print(sigungu.head().to_string(index=False) if not sigungu.empty else "no exact sigungu rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
