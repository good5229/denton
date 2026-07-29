#!/usr/bin/env python3
"""Audit phase248 PPS contract collection and regional attribution quality."""

from __future__ import annotations

import argparse
from calendar import monthrange
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase248_pps_contract_incremental"
MONTHLY = ROOT / "data" / "processed" / "phase248_pps_contract_monthly"
OUT = ROOT / "nationwide" / "outputs"
MANIFEST = ROOT / "data" / "processed" / "phase248_pps_contract_collection_manifest.csv"


def month_iter(start: str, end: str) -> list[str]:
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


def safe_read_csv(path: Path, **kwargs) -> pd.DataFrame:
    try:
        return pd.read_csv(path, **kwargs)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return pd.DataFrame()


def boolish(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def audit_month(period: str, manifest_row: dict[str, object]) -> dict[str, object]:
    csv_path = MONTHLY / f"pps_contract_{period}.csv"
    raw_dir = RAW / period
    df = safe_read_csv(csv_path, dtype={"source_period": str})

    api_total = int(float(manifest_row.get("total_count") or 0))
    rows_collected = int(float(manifest_row.get("rows_collected") or 0))
    if not df.empty:
        rows_collected = len(df)

    amount = pd.to_numeric(df.get("totCntrctAmt", pd.Series(dtype=float)), errors="coerce") if not df.empty else pd.Series(dtype=float)
    id_cols = [c for c in ["untyCntrctNo", "cntrctRefNo"] if c in df.columns]
    duplicate_contract_id_count = 0
    if id_cols and not df.empty:
        duplicate_contract_id_count = int(df.duplicated(id_cols).sum())

    province = df.get("matched_province_full", pd.Series(dtype=object)).fillna("").astype(str) if not df.empty else pd.Series(dtype=object)
    sigungu = df.get("matched_city", pd.Series(dtype=object)).fillna("").astype(str) if not df.empty else pd.Series(dtype=object)
    province_matched = int(province.ne("").sum()) if not df.empty else 0
    sigungu_matched = int((province.ne("") & sigungu.ne("")).sum()) if not df.empty else 0

    raw_json_count = len(list(raw_dir.glob("contract_*.json"))) if raw_dir.exists() else 0
    expected_pages = (api_total + 998) // 999 if api_total else 0
    collection_rate = rows_collected / api_total if api_total else 0.0

    return {
        "period": period,
        "year": period[:4],
        "month": period[4:],
        "days_in_month": monthrange(int(period[:4]), int(period[4:]))[1],
        "api_total_count": api_total,
        "rows_collected": rows_collected,
        "collection_rate": collection_rate,
        "pages_collected": int(float(manifest_row.get("pages_collected") or 0)),
        "expected_pages": expected_pages,
        "raw_json_count": raw_json_count,
        "complete": boolish(manifest_row.get("complete")),
        "ok": boolish(manifest_row.get("ok")),
        "error": manifest_row.get("error", ""),
        "monthly_csv_exists": csv_path.exists(),
        "duplicate_contract_id_count": duplicate_contract_id_count,
        "zero_or_missing_amount_count": int((amount.fillna(0).le(0)).sum()) if not df.empty else 0,
        "province_matched_rows": province_matched,
        "sigungu_matched_rows": sigungu_matched,
        "province_match_rate": province_matched / rows_collected if rows_collected else 0.0,
        "sigungu_match_rate": sigungu_matched / rows_collected if rows_collected else 0.0,
        "contract_amount_eok": float(pd.to_numeric(df.get("contract_amount_eok", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        if not df.empty
        else 0.0,
    }


def run(start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest = safe_read_csv(MANIFEST, dtype={"period": str})
    if manifest.empty:
        manifest = pd.DataFrame(columns=["period"])
    manifest["period"] = manifest["period"].astype(str).str.zfill(6)
    manifest = manifest.drop_duplicates("period", keep="last").set_index("period", drop=False)

    rows = []
    for period in month_iter(start, end):
        row = manifest.loc[period].to_dict() if period in manifest.index else {"period": period}
        rows.append(audit_month(period, row))
    detail = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [
            {
                "start": start,
                "end": end,
                "months": len(detail),
                "complete_months": int(detail["complete"].sum()),
                "incomplete_months": int((~detail["complete"]).sum()),
                "rows_collected": int(detail["rows_collected"].sum()),
                "api_total_count": int(detail["api_total_count"].sum()),
                "collection_rate": detail["rows_collected"].sum() / detail["api_total_count"].sum()
                if detail["api_total_count"].sum()
                else 0.0,
                "province_match_rate": detail["province_matched_rows"].sum() / detail["rows_collected"].sum()
                if detail["rows_collected"].sum()
                else 0.0,
                "sigungu_match_rate": detail["sigungu_matched_rows"].sum() / detail["rows_collected"].sum()
                if detail["rows_collected"].sum()
                else 0.0,
                "duplicate_contract_id_count": int(detail["duplicate_contract_id_count"].sum()),
                "zero_or_missing_amount_count": int(detail["zero_or_missing_amount_count"].sum()),
                "contract_amount_eok": float(detail["contract_amount_eok"].sum()),
            }
        ]
    )
    return detail, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="201501")
    parser.add_argument("--end", default="202512")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    detail, summary = run(args.start, args.end)
    tag = f"{args.start}_{args.end}"
    detail_path = OUT / f"phase248_pps_contract_quality_detail_{tag}.csv"
    summary_path = OUT / f"phase248_pps_contract_quality_summary_{tag}.csv"
    detail.to_csv(detail_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"wrote {detail_path.relative_to(ROOT)}")
    print(f"wrote {summary_path.relative_to(ROOT)}")
    print(summary.to_string(index=False))
    incomplete = detail[~detail["complete"]]
    if not incomplete.empty:
        print("incomplete periods:", ",".join(incomplete["period"].astype(str).head(30)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
