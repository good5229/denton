#!/usr/bin/env python3
"""Audit and aggregate Phase248 PPS contract monthly collection.

This script is intentionally read-only with respect to raw/monthly source CSVs.
It verifies whether the 2015~2025 monthly files are truly complete, then writes
streaming aggregates that downstream construction GVA allocation experiments can
consume without re-reading every raw row.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MONTHLY = ROOT / "data" / "processed" / "phase248_pps_contract_monthly"
OUT = ROOT / "nationwide" / "outputs"
MANIFEST = ROOT / "data" / "processed" / "phase248_pps_contract_collection_manifest.csv"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase249_pps_contract_collection_audit.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def expected_months() -> list[str]:
    return [f"{year}{month:02d}" for year in range(2015, 2026) for month in range(1, 13)]


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def md_table(df: pd.DataFrame, limit: int | None = None, digits: int = 2) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for col in x.columns:
        if pd.api.types.is_float_dtype(x[col]):
            x[col] = x[col].map(lambda v: "" if pd.isna(v) else f"{float(v):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[col]):
            x[col] = x[col].map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            x[col] = x[col].fillna("").astype(str)
    lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
    for _, row in x.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in x.columns) + " |")
    return "\n".join(lines)


def load_manifest() -> pd.DataFrame:
    if not MANIFEST.exists():
        return pd.DataFrame(columns=["period", "complete", "rows_collected", "total_count"])
    m = pd.read_csv(MANIFEST, dtype={"period": str})
    m["period"] = m["period"].astype(str).str.zfill(6)
    return m


def quarter(period: str) -> str:
    month = int(period[4:])
    return f"{period[:4]}Q{((month - 1) // 3) + 1}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    manifest_latest = manifest.drop_duplicates("period", keep="last").set_index("period") if not manifest.empty else pd.DataFrame()

    monthly_rows: list[dict[str, object]] = []
    province_parts: list[pd.DataFrame] = []
    sigungu_parts: list[pd.DataFrame] = []

    for period in expected_months():
        path = MONTHLY / f"pps_contract_{period}.csv"
        status = {
            "period": period,
            "year": int(period[:4]),
            "quarter": quarter(period),
            "month": int(period[4:]),
            "csv_exists": path.exists(),
            "csv_rows": 0,
            "contract_amount_eok": 0.0,
            "current_contract_amount_eok": 0.0,
            "province_matched_rows": 0,
            "sigungu_matched_rows": 0,
            "manifest_complete": False,
            "manifest_total_count": np.nan,
            "manifest_rows_collected": np.nan,
            "is_complete": False,
        }
        if period in manifest_latest.index:
            row = manifest_latest.loc[period]
            status["manifest_complete"] = truthy(row.get("complete"))
            status["manifest_total_count"] = pd.to_numeric(row.get("total_count"), errors="coerce")
            status["manifest_rows_collected"] = pd.to_numeric(row.get("rows_collected"), errors="coerce")
        if path.exists():
            try:
                df = pd.read_csv(path, dtype={"source_period": str}, low_memory=False)
            except pd.errors.EmptyDataError:
                df = pd.DataFrame()
            status["csv_rows"] = int(len(df))
            if not df.empty:
                df["source_period"] = df.get("source_period", period).astype(str).str.zfill(6)
                for col in ["contract_amount_eok", "current_contract_amount_eok"]:
                    if col not in df:
                        df[col] = 0.0
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
                df["matched_province_full"] = df.get("matched_province_full", "").fillna("").astype(str)
                df["matched_city"] = df.get("matched_city", "").fillna("").astype(str)
                status["contract_amount_eok"] = float(df["contract_amount_eok"].sum())
                status["current_contract_amount_eok"] = float(df["current_contract_amount_eok"].sum())
                status["province_matched_rows"] = int(df["matched_province_full"].ne("").sum())
                status["sigungu_matched_rows"] = int((df["matched_province_full"].ne("") & df["matched_city"].ne("")).sum())

                f = df[df["matched_province_full"].ne("")].copy()
                if not f.empty:
                    f["year"] = int(period[:4])
                    f["quarter"] = quarter(period)
                    f["period"] = period
                    province_parts.append(
                        f.groupby(["matched_province_full", "year", "quarter", "period"], as_index=False).agg(
                            pps_contract_rows=("source_period", "count"),
                            pps_contract_amount_eok=("contract_amount_eok", "sum"),
                            pps_current_contract_amount_eok=("current_contract_amount_eok", "sum"),
                        )
                    )
                    g = f[f["matched_city"].ne("")].copy()
                    if not g.empty:
                        sigungu_parts.append(
                            g.groupby(["matched_province_full", "matched_city", "year", "quarter", "period"], as_index=False).agg(
                                pps_contract_rows=("source_period", "count"),
                                pps_contract_amount_eok=("contract_amount_eok", "sum"),
                                pps_current_contract_amount_eok=("current_contract_amount_eok", "sum"),
                            )
                        )
        status["is_complete"] = bool(
            status["csv_exists"]
            and status["manifest_complete"]
            and int(status["csv_rows"]) > 0
            and pd.notna(status["manifest_total_count"])
            and int(status["csv_rows"]) >= int(status["manifest_total_count"])
        )
        monthly_rows.append(status)

    monthly = pd.DataFrame(monthly_rows)
    monthly["province_match_rate_pct"] = np.where(monthly["csv_rows"].gt(0), monthly["province_matched_rows"] / monthly["csv_rows"] * 100, np.nan)
    monthly["sigungu_match_rate_pct"] = np.where(monthly["csv_rows"].gt(0), monthly["sigungu_matched_rows"] / monthly["csv_rows"] * 100, np.nan)
    monthly.to_csv(OUT / "phase248_pps_contract_collection_audit_monthly.csv", index=False, encoding="utf-8-sig")

    if province_parts:
        province_month = pd.concat(province_parts, ignore_index=True)
    else:
        province_month = pd.DataFrame()
    if sigungu_parts:
        sigungu_month = pd.concat(sigungu_parts, ignore_index=True)
    else:
        sigungu_month = pd.DataFrame()

    province_month.to_csv(OUT / "phase248_pps_contract_province_month.csv", index=False, encoding="utf-8-sig")
    sigungu_month.to_csv(OUT / "phase248_pps_contract_sigungu_month.csv", index=False, encoding="utf-8-sig")
    for name, frame, keys in [
        ("province", province_month, ["matched_province_full", "year", "quarter"]),
        ("sigungu", sigungu_month, ["matched_province_full", "matched_city", "year", "quarter"]),
    ]:
        if frame.empty:
            continue
        frame.groupby(keys, as_index=False).agg(
            pps_contract_rows=("pps_contract_rows", "sum"),
            pps_contract_amount_eok=("pps_contract_amount_eok", "sum"),
            pps_current_contract_amount_eok=("pps_current_contract_amount_eok", "sum"),
        ).to_csv(OUT / f"phase248_pps_contract_{name}_quarter.csv", index=False, encoding="utf-8-sig")
        year_keys = [k for k in keys if k != "quarter"]
        frame.groupby(year_keys, as_index=False).agg(
            pps_contract_rows=("pps_contract_rows", "sum"),
            pps_contract_amount_eok=("pps_contract_amount_eok", "sum"),
            pps_current_contract_amount_eok=("pps_current_contract_amount_eok", "sum"),
        ).to_csv(OUT / f"phase248_pps_contract_{name}_year.csv", index=False, encoding="utf-8-sig")

    complete_months = int(monthly["is_complete"].sum())
    incomplete = monthly[~monthly["is_complete"]].copy()
    by_year = monthly.groupby("year", as_index=False).agg(
        complete_months=("is_complete", "sum"),
        csv_rows=("csv_rows", "sum"),
        contract_amount_eok=("contract_amount_eok", "sum"),
        sigungu_match_rate_pct=("sigungu_matched_rows", lambda s: np.nan),
    )
    matched_by_year = monthly.groupby("year", as_index=False).agg(
        csv_rows=("csv_rows", "sum"),
        sigungu_matched_rows=("sigungu_matched_rows", "sum"),
        province_matched_rows=("province_matched_rows", "sum"),
    )
    by_year = by_year.drop(columns=["sigungu_match_rate_pct"]).merge(matched_by_year, on=["year", "csv_rows"], how="left")
    by_year["province_match_rate_pct"] = np.where(by_year["csv_rows"].gt(0), by_year["province_matched_rows"] / by_year["csv_rows"] * 100, np.nan)
    by_year["sigungu_match_rate_pct"] = np.where(by_year["csv_rows"].gt(0), by_year["sigungu_matched_rows"] / by_year["csv_rows"] * 100, np.nan)

    report = f"""# Phase249 조달청 공사 계약정보 2015~2025 수집 감사

생성시각: {CREATED_AT}

## 완료 판정

- 기대 월 수: 132개월
- 완료 월 수: {complete_months}개월
- 미완료 월 수: {132 - complete_months}개월
- 현재 CSV 행 수 합계: {int(monthly["csv_rows"].sum()):,}건
- 현재 계약금액 합계: {float(monthly["contract_amount_eok"].sum()):,.1f}억원
- 시도 매칭률: {float(monthly["province_matched_rows"].sum() / monthly["csv_rows"].sum() * 100) if monthly["csv_rows"].sum() else np.nan:.2f}%
- 시군구 매칭률: {float(monthly["sigungu_matched_rows"].sum() / monthly["csv_rows"].sum() * 100) if monthly["csv_rows"].sum() else np.nan:.2f}%

## 연도별 수집 상태

{md_table(by_year)}

## 미완료 월

{md_table(incomplete[["period", "csv_exists", "csv_rows", "manifest_total_count", "manifest_rows_collected", "manifest_complete"]], limit=40)}

## 산출물

- `nationwide/outputs/phase248_pps_contract_collection_audit_monthly.csv`
- `nationwide/outputs/phase248_pps_contract_province_month.csv`
- `nationwide/outputs/phase248_pps_contract_province_quarter.csv`
- `nationwide/outputs/phase248_pps_contract_province_year.csv`
- `nationwide/outputs/phase248_pps_contract_sigungu_month.csv`
- `nationwide/outputs/phase248_pps_contract_sigungu_quarter.csv`
- `nationwide/outputs/phase248_pps_contract_sigungu_year.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT / "phase248_pps_contract_collection_audit_monthly.csv")


if __name__ == "__main__":
    main()
