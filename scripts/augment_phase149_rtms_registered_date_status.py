#!/usr/bin/env python3
"""Augment Phase149 RTMS rows with registered-date disclosure status.

MOLIT apartment trade API includes the `rgstDate` element in the XML, but
official public guidance limits ownership-registration date disclosure to
apartment sale contracts from 2023-01-01 onward.  For pre-2023 rows, blank
`rgstDate` is therefore a source disclosure limit, not a parser failure.

This script does not fabricate dates.  It adds explicit status columns:

* registered_date_filled: actual date when provided, otherwise a sentinel
* registered_date_is_actual: whether the value is a real source date
* registered_date_status: source-disclosure interpretation
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase149_realestate_rtms_asof_candidate"
RAW = ROOT / "data" / "raw" / "phase149_rtms_apt_trade_history"
ROWS = OUT / "phase149_rtms_apt_trade_rows.csv"
STATUS_SUMMARY = OUT / "phase149_rtms_registered_date_status_summary.csv"
MANIFEST = OUT / "phase149_rtms_registered_date_status_manifest.json"
SOURCE_URL = "https://www.data.go.kr/data/15126469/openapi.do"
OFFICIAL_RULE = "등기일자 공개대상: 2023년 1월 1일 이후 아파트 매매 계약 체결 건"
SOURCE_DATASET_REGISTERED_DATE = "2024-01-25"
SOURCE_DATASET_MODIFIED_DATE = "2026-07-22"
SOURCE_UPDATE_CYCLE = "실시간"


def clean_text(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip()


def raw_sort_key(path: Path) -> tuple[str, str, int]:
    match = re.search(r"rtms_apt_trade_(\d+)_(\d{6})_p(\d+)\.xml$", path.name)
    if not match:
        return (path.name, "", 0)
    return (match.group(1), match.group(2), int(match.group(3)))


def parse_raw_registered_dates() -> list[str]:
    """Re-read source XML files and return row-level `rgstDate` values.

    This is intentionally based on the local raw source files rather than the
    existing processed CSV, so rerunning the augmentation can repair a missing
    or stale processed `registered_date` column.
    """

    if not RAW.exists():
        return []
    values: list[str] = []
    for path in sorted(RAW.glob("rtms_apt_trade_*_*.xml"), key=raw_sort_key):
        root = ET.fromstring(path.read_bytes())
        for item in root.findall(".//item"):
            values.append((item.findtext("rgstDate") or "").strip())
    return values


def status(row: pd.Series) -> str:
    raw = str(row["registered_date"]).strip()
    year = int(row["deal_year"])
    if raw:
        return "actual_rgstDate_provided_by_molit"
    if year < 2023:
        return "not_disclosed_pre_2023_contract_by_molit_rule"
    return "blank_after_2023_probably_not_registered_or_not_disclosed"


def main() -> None:
    if not ROWS.exists():
        raise FileNotFoundError(ROWS)
    df = pd.read_csv(ROWS, dtype=str)

    raw_registered_dates = parse_raw_registered_dates()
    if raw_registered_dates:
        if len(raw_registered_dates) != len(df):
            raise ValueError(
                f"Raw XML row count ({len(raw_registered_dates)}) does not match processed rows ({len(df)})."
            )
        df["registered_date_from_raw_xml"] = raw_registered_dates
        df["registered_date"] = clean_text(df["registered_date_from_raw_xml"])
    else:
        df["registered_date"] = clean_text(df.get("registered_date", pd.Series([""] * len(df))))
        df["registered_date_from_raw_xml"] = df["registered_date"]

    df["deal_year"] = clean_text(df["deal_year"])
    df["registered_date_status"] = df.apply(status, axis=1)
    df["registered_date_is_actual"] = df["registered_date_status"].eq("actual_rgstDate_provided_by_molit")
    df["registered_date_filled"] = df["registered_date"]
    df.loc[
        ~df["registered_date_is_actual"] & df["deal_year"].astype(int).lt(2023),
        "registered_date_filled",
    ] = "PRE_2023_NOT_DISCLOSED_BY_SOURCE"
    df.loc[
        ~df["registered_date_is_actual"] & df["deal_year"].astype(int).ge(2023),
        "registered_date_filled",
    ] = "POST_2023_BLANK_IN_SOURCE"
    df["registered_date_source_url"] = SOURCE_URL
    df["registered_date_source_rule"] = OFFICIAL_RULE
    df["source_dataset_registered_date"] = SOURCE_DATASET_REGISTERED_DATE
    df["source_dataset_modified_date"] = SOURCE_DATASET_MODIFIED_DATE
    df["source_dataset_update_cycle"] = SOURCE_UPDATE_CYCLE
    df["source_dataset_registered_date_basis"] = (
        "공공데이터포털 OpenAPI 정보의 데이터셋 등록일. 행별 소유권 이전등기일자(rgstDate)가 아님."
    )
    df["registerd_date"] = df["registered_date_filled"]
    df["registerd_date_basis"] = (
        "사용자 요청의 오타형 호환 컬럼. 실제 XML rgstDate가 있으면 그 값을, "
        "공식 미공개/공백이면 registered_date_filled 상태값을 기록."
    )
    df.to_csv(ROWS, index=False, encoding="utf-8-sig")

    summary = (
        df.groupby(["city", "deal_year", "registered_date_status"], as_index=False)
        .agg(rows=("period", "size"))
    )
    total = summary.groupby(["city", "deal_year"])["rows"].transform("sum")
    summary["share_pct"] = summary["rows"] / total * 100
    summary.to_csv(STATUS_SUMMARY, index=False, encoding="utf-8-sig")

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_output": str(ROWS.relative_to(ROOT)),
        "summary": str(STATUS_SUMMARY.relative_to(ROOT)),
        "source_url": SOURCE_URL,
        "official_rule": OFFICIAL_RULE,
        "source_dataset_registered_date": SOURCE_DATASET_REGISTERED_DATE,
        "source_dataset_modified_date": SOURCE_DATASET_MODIFIED_DATE,
        "source_update_cycle": SOURCE_UPDATE_CYCLE,
        "no_imputation_of_actual_dates": True,
        "raw_xml_reparsed": bool(raw_registered_dates),
        "rows": int(len(df)),
        "actual_registered_date_rows": int(df["registered_date_is_actual"].sum()),
        "compatibility_alias_added": "registerd_date",
        "compatibility_alias_warning": "registerd_date is a misspelled compatibility column and must not be interpreted as a guaranteed actual ownership-registration date.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated_rows={len(df)} actual_registered_date_rows={int(df['registered_date_is_actual'].sum())}")
    print(f"Wrote {STATUS_SUMMARY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
