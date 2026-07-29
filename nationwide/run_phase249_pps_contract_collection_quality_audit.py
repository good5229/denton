#!/usr/bin/env python3
"""Audit PPS construction contract collection completeness and match quality."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MONTHLY = ROOT / "data" / "processed" / "phase248_pps_contract_monthly"
OUT = ROOT / "data" / "processed" / "phase249_pps_contract_quality_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase249_pps_contract_quality_audit.md"
MANIFEST = ROOT / "data" / "processed" / "phase248_pps_contract_collection_manifest.csv"
PERIOD_RE = re.compile(r"^\d{6}$")


def safe_read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return pd.DataFrame()


def md_table(df: pd.DataFrame, max_rows: int | None = None, digits: int = 2) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{v:,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def clean_manifest_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


def valid_period_text(value: object) -> bool:
    text = clean_manifest_text(value).strip()
    if not PERIOD_RE.fullmatch(text):
        return False
    return 1 <= int(text[4:6]) <= 12


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = safe_read(MANIFEST)
    if manifest.empty:
        raise SystemExit(f"Missing or empty manifest: {MANIFEST}")
    invalid_manifest_period_rows = 0
    if "period" in manifest.columns:
        valid_manifest_period = manifest["period"].map(valid_period_text)
        invalid_manifest_period_rows = int((~valid_manifest_period).sum())
        manifest = manifest[valid_manifest_period].copy()
        manifest["period"] = manifest["period"].astype(str).str.strip()
    else:
        invalid_manifest_period_rows = len(manifest)
        manifest = pd.DataFrame(columns=["period"])
    rows = []
    province_rows = []
    unmatched_samples = []
    for p in sorted(MONTHLY.glob("pps_contract_*.csv")):
        period = p.stem.rsplit("_", 1)[-1]
        df = safe_read(p)
        hit = manifest[manifest["period"].eq(period)]
        total_count = int(float(hit.iloc[-1]["total_count"])) if not hit.empty and "total_count" in hit else len(df)
        manifest_rows_collected = (
            int(float(hit.iloc[-1]["rows_collected"]))
            if not hit.empty and "rows_collected" in hit and pd.notna(hit.iloc[-1]["rows_collected"])
            else len(df)
        )
        pages_collected = int(float(hit.iloc[-1]["pages_collected"])) if not hit.empty and "pages_collected" in hit else 0
        manifest_complete = (
            str(hit.iloc[-1].get("complete", "")).strip().lower() in {"true", "1", "yes"}
            if not hit.empty
            else False
        )
        manifest_ok = (
            str(hit.iloc[-1].get("ok", "")).strip().lower() in {"true", "1", "yes"}
            if not hit.empty
            else False
        )
        manifest_error = clean_manifest_text(hit.iloc[-1].get("error", "")) if not hit.empty else ""
        raw_json_count = len(list((ROOT / "data" / "raw" / "phase248_pps_contract_incremental" / period).glob("contract_*.json")))
        monthly_csv_exists = p.exists() and p.stat().st_size > 4
        raw_partial_preserved = bool((not monthly_csv_exists) and manifest_rows_collected > 0 and total_count > manifest_rows_collected)
        if df.empty:
            rows.append(
                {
                    "period": period,
                    "api_total_count": total_count,
                    "manifest_rows_collected": manifest_rows_collected,
                    "rows_collected": 0,
                    "pages_collected": pages_collected,
                    "raw_json_count": raw_json_count,
                    "raw_partial_preserved": raw_partial_preserved,
                    "monthly_csv_exists": monthly_csv_exists,
                    "collection_rate_pct": 0.0 if total_count else np.nan,
                    "manifest_complete": manifest_complete,
                    "quality_complete": False,
                    "manifest_ok": manifest_ok,
                    "manifest_error": manifest_error,
                    "duplicate_contract_id_count": 0,
                    "missing_or_zero_amount_count": 0,
                    "province_matched_rows": 0,
                    "sigungu_matched_rows": 0,
                    "province_match_rate_pct": 0.0,
                    "sigungu_match_rate_pct": 0.0,
                }
            )
            continue
        amount = pd.to_numeric(df.get("contract_amount_eok"), errors="coerce").fillna(0)
        province_match = df.get("matched_province_full", pd.Series("", index=df.index)).fillna("").astype(str).ne("")
        sigungu_match = province_match & df.get("matched_city", pd.Series("", index=df.index)).fillna("").astype(str).ne("")
        dup = int(df.get("untyCntrctNo", pd.Series([], dtype=str)).duplicated().sum()) if "untyCntrctNo" in df else 0
        collection_rate = len(df) / total_count * 100 if total_count else np.nan
        quality_complete = bool(
            manifest_complete
            and manifest_ok
            and monthly_csv_exists
            and (not manifest_error)
            and (not pd.isna(collection_rate))
            and collection_rate >= 99.9
            and len(df) >= total_count
        )
        rows.append(
            {
                "period": period,
                "api_total_count": total_count,
                "manifest_rows_collected": manifest_rows_collected,
                "rows_collected": len(df),
                "pages_collected": pages_collected,
                "raw_json_count": raw_json_count,
                "raw_partial_preserved": raw_partial_preserved,
                "monthly_csv_exists": monthly_csv_exists,
                "collection_rate_pct": collection_rate,
                "manifest_complete": manifest_complete,
                "quality_complete": quality_complete,
                "manifest_ok": manifest_ok,
                "manifest_error": manifest_error,
                "duplicate_contract_id_count": dup,
                "missing_or_zero_amount_count": int(amount.le(0).sum()),
                "province_matched_rows": int(province_match.sum()),
                "sigungu_matched_rows": int(sigungu_match.sum()),
                "province_match_rate_pct": province_match.mean() * 100,
                "sigungu_match_rate_pct": sigungu_match.mean() * 100,
            }
        )
        if province_match.any():
            g = (
                df.assign(
                    contract_amount_eok=amount,
                    matched_province_full=df["matched_province_full"].fillna(""),
                    sigungu_matched=sigungu_match,
                )
                .groupby(["matched_province_full"], as_index=False)
                .agg(rows=("untyCntrctNo", "count"), amount_eok=("contract_amount_eok", "sum"), sigungu_matched_rows=("sigungu_matched", "sum"))
            )
            g["period"] = period
            province_rows.append(g)
        sample = df[~sigungu_match].head(5).copy()
        if not sample.empty:
            sample["period"] = period
            keep = [c for c in ["period", "cnstwkNm", "cntrctInsttNm", "dminsttList", "contract_amount_eok"] if c in sample.columns]
            unmatched_samples.append(sample[keep])

    audit = pd.DataFrame(rows).sort_values("period")
    audit.to_csv(OUT / "phase249_monthly_collection_quality.csv", index=False, encoding="utf-8-sig")
    if province_rows:
        pd.concat(province_rows, ignore_index=True).to_csv(OUT / "phase249_province_month_quality.csv", index=False, encoding="utf-8-sig")
    if unmatched_samples:
        pd.concat(unmatched_samples, ignore_index=True).to_csv(OUT / "phase249_unmatched_samples.csv", index=False, encoding="utf-8-sig")

    completed = audit[audit["quality_complete"].eq(True)]
    if not audit.empty:
        audit["year"] = audit["period"].astype(str).str[:4]
        annual_gate = (
            audit.groupby("year", as_index=False)
            .agg(
                months_seen=("period", "count"),
                months_quality_complete=("quality_complete", "sum"),
                min_collection_rate_pct=("collection_rate_pct", "min"),
                mean_province_match_rate_pct=("province_match_rate_pct", "mean"),
                mean_sigungu_match_rate_pct=("sigungu_match_rate_pct", "mean"),
            )
        )
        annual_gate["adoptable_year"] = annual_gate["months_quality_complete"].eq(12) & annual_gate["min_collection_rate_pct"].ge(99.9)
        annual_gate.to_csv(OUT / "phase249_annual_collection_gate.csv", index=False, encoding="utf-8-sig")
    else:
        annual_gate = pd.DataFrame()
    summary = {
        "months_seen": len(audit),
        "months_quality_complete": int(audit["quality_complete"].sum()),
        "adoptable_years": int(annual_gate["adoptable_year"].sum()) if not annual_gate.empty else 0,
        "invalid_manifest_period_rows": invalid_manifest_period_rows,
        "rows_collected": int(audit["rows_collected"].sum()),
        "manifest_rows_collected": int(audit["manifest_rows_collected"].sum()) if "manifest_rows_collected" in audit else int(audit["rows_collected"].sum()),
        "api_total_count_seen": int(audit["api_total_count"].sum()),
        "raw_partial_preserved_months": int(audit["raw_partial_preserved"].sum()) if "raw_partial_preserved" in audit else 0,
        "overall_collection_rate_pct": float(audit["rows_collected"].sum() / audit["api_total_count"].sum() * 100) if audit["api_total_count"].sum() else np.nan,
        "mean_province_match_rate_pct": float(completed["province_match_rate_pct"].mean()) if not completed.empty else np.nan,
        "mean_sigungu_match_rate_pct": float(completed["sigungu_match_rate_pct"].mean()) if not completed.empty else np.nan,
    }
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(OUT / "phase249_collection_quality_summary.csv", index=False, encoding="utf-8-sig")
    blockers = audit[audit["quality_complete"].ne(True)].copy()
    if not blockers.empty:
        blocker_cols = [
            "period",
            "api_total_count",
            "manifest_rows_collected",
            "rows_collected",
            "pages_collected",
            "raw_json_count",
            "raw_partial_preserved",
            "monthly_csv_exists",
            "collection_rate_pct",
            "manifest_complete",
            "manifest_ok",
            "manifest_error",
        ]
        blockers = blockers[[c for c in blocker_cols if c in blockers.columns]].head(12)

    report = f"""# Phase249 조달청 공사계약 수집 품질 감사

생성시각: {datetime.now().astimezone().isoformat(timespec='seconds')}

## 1. 요약

{md_table(summary_df, digits=2)}

## 2. 첫 미완료 원인

{md_table(blockers, max_rows=12, digits=2) if not blockers.empty else "_미완료 월 없음_"}

첫 미완료 월은 후속 수집 재개의 시작점이다. `HTTPError 429: Too Many Requests`가 남아 있으면 해당 시점의 API 일일/분당 제한 또는 서버 측 제한에 걸린 것으로 보고, 부분 수집 파일은 downstream 건설업 route 검증에 투입하지 않는다.

## 3. 월별 수집·매칭 품질

{md_table(audit[["period", "api_total_count", "manifest_rows_collected", "rows_collected", "pages_collected", "raw_json_count", "raw_partial_preserved", "monthly_csv_exists", "collection_rate_pct", "manifest_complete", "quality_complete", "duplicate_contract_id_count", "missing_or_zero_amount_count", "province_match_rate_pct", "sigungu_match_rate_pct"]], max_rows=60, digits=2)}

## 4. 연도별 채택 가능성 게이트

{md_table(annual_gate, max_rows=20, digits=2)}

## 5. 판정 기준

| 항목 | 기준 | 해석 |
| --- | --- | --- |
| 월별 수집률 | 99.9% 이상 | 미완료 월은 본 검증에서 제외하거나 재수집 |
| 연도 채택 | 12개월 모두 `quality_complete=True` | 연간 GVA 검증에 포함 가능한 최소 조건 |
| 시도 매칭률 | 95% 이상 권장 | 광역시도 분석 채택 조건 |
| 시군구 매칭률 | 80~90% 이상 권장 | 시군구 분석 채택 조건 |
| 중복 계약번호 | dedup 전후 비교 | 계약변경/중복 가능성 확인 |
| 금액 0/결측 | 별도 집계 | 금액 share 산식에서 제외/보조 처리 |

## 6. 기준연도 100 지수 혼재 처리 원칙

2015=100, 2020=100 등 기준이 다른 지수형 입력은 사용 전 공통 bridge year로 재기준화한다. 기본식은 `rebased = raw / raw[bridge_year] * 100`이며, 2020년 충격 가능성이 큰 지표는 2019년·2021년 bridge 민감도도 같이 본다. 재기준화 후에는 전국합/시도합 보존과 연도별 변동률 왜곡 여부를 감사한다.

## 7. 주의

조달청 계약정보의 지역 텍스트는 계약기관·수요기관·공사명에 섞여 있다. 따라서 이 감사의 `matched_city`는 실제 공사 수행지를 확정한 값이 아니라, 공개 계약정보 텍스트 기반 보수적 지역 귀속값이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(summary_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
