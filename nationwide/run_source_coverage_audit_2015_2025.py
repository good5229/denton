#!/usr/bin/env python3
"""Audit 2015~2025 source coverage for nationwide GVA/GRDP experiments.

This is intentionally conservative: a source is not marked as operationally
usable simply because a file exists.  The audit records period coverage,
geographic scope, index base, publication/vintage caveats, and whether the
source can currently support nationwide 시도/시군구 monthly/quarterly
estimation/validation.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "nationwide" / "source_coverage_audit_2015_2025.md"
CSV = OUT / "source_coverage_audit_2015_2025.csv"


SOURCE_SPECS: list[dict[str, Any]] = [
    {
        "source_id": "sigungu_annual_gva",
        "label": "시군구 경제활동별 연간 실질 GVA",
        "path": "nationwide/outputs/annual_sigungu_gva_normalized.csv",
        "provider": "KOSIS 지역소득",
        "expected_time": "annual",
        "expected_geo": "sigungu",
        "expected_scope": "nationwide_with_publication_gaps",
        "index_base": "real_value_not_index",
        "role": "시군구×업종 연간 actual/상위 집계검증",
        "notes": "공표 시도별 연도 범위가 다르며 일부 광역시는 2023 시군구 원천이 없다.",
    },
    {
        "source_id": "sido_quarterly_grdp_experimental",
        "label": "시도별 분기 실질 GRDP/GDP 실험적 통계",
        "path": "data/processed/phase211_gyeonggi_2024_2025_grdp_extension/phase211_sido_quarterly_xlsx_long.csv",
        "provider": "통계청 지역통계 실험적 통계",
        "expected_time": "quarter",
        "expected_geo": "sido",
        "expected_scope": "nationwide",
        "index_base": "real_value_not_index",
        "role": "시도 분기 actual 및 전국 GDP 경계 검증",
        "notes": "세종 단층처리와 순생산물세 bridge에 사용.",
    },
    {
        "source_id": "national_quarterly_gdp",
        "label": "전국 분기 GDP",
        "path": "data/processed/rolling_national_quarterly_gdp_real.csv",
        "provider": "국민계정/통계청·한국은행 계열",
        "expected_time": "quarter",
        "expected_geo": "national",
        "expected_scope": "national",
        "index_base": "real_value_not_index",
        "role": "17개 시도 합계의 전국 경계 검증",
        "notes": "전국 경계 WAPE는 외부 일관성 참고지표로만 해석.",
    },
    {
        "source_id": "manufacturing_production_index",
        "label": "시도별 제조업 광공업생산지수",
        "path": "data/processed/rolling_mining_manufacturing_production_index.csv",
        "provider": "KOSIS 광업제조업동향조사",
        "expected_time": "month",
        "expected_geo": "sido",
        "expected_scope": "nationwide",
        "index_base": "2020=100",
        "role": "광업·제조업 월별 시간경로 후보",
        "notes": "공개 actual 검증은 광업+제조업 합산 경계에서 수행.",
    },
    {
        "source_id": "mining_production_index",
        "label": "시도별 광업 생산지수",
        "path": "data/processed/rolling_mining_production_index.csv",
        "provider": "KOSIS 광업제조업동향조사",
        "expected_time": "month_or_quarter",
        "expected_geo": "sido",
        "expected_scope": "nationwide",
        "index_base": "2020=100",
        "role": "광업·제조업 내부 분리 후보",
        "notes": "일부 기간/지역 결측 가능.",
    },
    {
        "source_id": "manufacturing_detail_production_index",
        "label": "제조업 세부 생산지수",
        "path": "data/processed/phase195_monthly_detail_manufacturing_production_index.csv",
        "provider": "KOSIS 광업제조업동향조사",
        "expected_time": "month",
        "expected_geo": "national_or_partial",
        "expected_scope": "partial_industry",
        "index_base": "2020=100",
        "role": "제조업 중분류·세부업종 시간경로 후보",
        "notes": "전체 KSIC 중분류를 덮지 못하므로 보조 후보.",
    },
    {
        "source_id": "service_production_index",
        "label": "시도별 서비스업생산지수",
        "path": "data/processed/rolling_service_production_index.csv",
        "provider": "KOSIS 서비스업동향조사",
        "expected_time": "month_or_quarter",
        "expected_geo": "sido",
        "expected_scope": "nationwide",
        "index_base": "2020=100",
        "role": "서비스업 및 세부 서비스 시간경로 후보",
        "notes": "상반기 조기점검 보조에는 유효하나 자동채택은 rolling gate 필요.",
    },
    {
        "source_id": "service_detail_national_index",
        "label": "전국 세부 서비스업생산지수",
        "path": "data/processed/expanded_national_service_ksic_production_index.csv",
        "provider": "KOSIS 서비스업동향조사",
        "expected_time": "month_or_quarter",
        "expected_geo": "national",
        "expected_scope": "national_detail",
        "index_base": "2020=100",
        "role": "세부 서비스업 시간 profile 후보",
        "notes": "지역 차원이 없어 시군구 공간배분 단독 근거로 사용 금지.",
    },
    {
        "source_id": "electricity_sigungu_monthly",
        "label": "시군구 전력사용량 historical as-of 패널",
        "path": "data/processed/municipality_electricity_asof_long.csv",
        "provider": "한국전력/전력 사용량 공개자료",
        "expected_time": "month",
        "expected_geo": "sigungu",
        "expected_scope": "nationwide_or_large_panel",
        "index_base": "usage_not_index",
        "role": "제조업·전력/가스·상업활동 보조 지표",
        "notes": "업종귀속이 거칠어 단독 route보다 보조 후보.",
    },
    {
        "source_id": "electricity_sigungu_current_monthly",
        "label": "시군구 전력사용량 최신 월별 원천",
        "path": "data/processed/municipality_electricity_monthly.csv",
        "provider": "한국전력/전력 사용량 공개자료",
        "expected_time": "month",
        "expected_geo": "sigungu",
        "expected_scope": "nationwide_current_snapshot",
        "index_base": "usage_not_index",
        "role": "최신 2025년 이후 nowcast 후보",
        "notes": "최신 공표분 중심 자료. 과거 backtest에는 historical as-of 패널을 우선 사용.",
    },
    {
        "source_id": "electricity_gas_production_index",
        "label": "전기·가스 생산지수",
        "path": "data/processed/rolling_electricity_gas_production_index.csv",
        "provider": "KOSIS 생산지수",
        "expected_time": "month_or_quarter",
        "expected_geo": "sido",
        "expected_scope": "nationwide",
        "index_base": "2020=100",
        "role": "전기·가스업 시간경로 후보",
        "notes": "지수형 입력. 기준연도 bridge 감사 대상.",
    },
    {
        "source_id": "pps_contract_info",
        "label": "조달청 나라장터 공사계약 정보",
        "path": "data/processed/phase248_pps_contract_collection_manifest.csv",
        "provider": "공공데이터포털/조달청",
        "expected_time": "month/day",
        "expected_geo": "nationwide_text_attribution",
        "expected_scope": "nationwide_public_contracts",
        "index_base": "amount_not_index",
        "role": "건설업 공공공사 계약금액 보조자료",
        "notes": "API 429로 전량 미완료. 공공공사 계약액이지 전체 건설업 actual이 아니다.",
        "special": "pps_manifest",
    },
    {
        "source_id": "cals_contracts",
        "label": "CALS 공사계약/목록",
        "path": "data/processed/phase241_cals_construction_contract_rows.csv",
        "provider": "건설CALS/공공공사 정보",
        "expected_time": "event_snapshot",
        "expected_geo": "project_location_text",
        "expected_scope": "public_soc_partial",
        "index_base": "amount_not_index",
        "role": "도로·하천 공공/SOC 건설업 보조자료",
        "notes": "민간건축 및 전체 건설업 대표자료 아님.",
    },
    {
        "source_id": "lh_notices",
        "label": "LH 분양임대공고",
        "path": "data/processed/phase243_lh_notice_rows_202101_202312.csv",
        "provider": "LH",
        "expected_time": "event",
        "expected_geo": "project_location_text",
        "expected_scope": "public_housing_land_partial",
        "index_base": "count_not_index",
        "role": "공공주택·토지 위치/시점 보조자료",
        "notes": "금액자료가 아니므로 단독 GVA 배분 기준으로 사용 금지.",
    },
    {
        "source_id": "seoul_redevelopment",
        "label": "서울 도시정비사업 통계",
        "path": "data/raw/phase241_seoul_redevelopment/seoul_redevelopment_oa22856_seq1.xlsx",
        "provider": "서울 열린데이터광장",
        "expected_time": "snapshot",
        "expected_geo": "seoul",
        "expected_scope": "local_only",
        "index_base": "not_index",
        "role": "서울권 민간 정비사업 보조자료",
        "notes": "전국 원본이 아니므로 전국 일반화에는 별도 지방정부 자료 필요.",
    },
    {
        "source_id": "index_base_bridge",
        "label": "지수 기준연도 bridge 감사",
        "path": "data/processed/index_base_bridge_source_summary.csv",
        "provider": "내부 감사 산출물",
        "expected_time": "metadata",
        "expected_geo": "metadata",
        "expected_scope": "all_index_inputs",
        "index_base": "bridge_metadata",
        "role": "2015=100/2020=100 혼재 여부 감사",
        "notes": "현재 로컬 주요 지수는 2020=100 소급계열.",
        "special": "index_bridge_metadata",
    },
]


def read_table(path: Path) -> tuple[pd.DataFrame, str, str]:
    if not path.exists():
        return pd.DataFrame(), "", "missing"
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return pd.DataFrame(data), "json", "ok"
            if isinstance(data, dict):
                return pd.json_normalize(data), "json", "ok"
        except Exception as exc:  # noqa: BLE001
            return pd.DataFrame(), "", f"read_error:{type(exc).__name__}"
    if path.suffix.lower() in {".xlsx", ".xls"}:
        try:
            return pd.read_excel(path), "excel", "ok"
        except Exception as exc:  # noqa: BLE001
            return pd.DataFrame(), "", f"read_error:{type(exc).__name__}"
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False), enc, "ok"
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            return pd.DataFrame(), enc, "empty"
        except Exception as exc:  # noqa: BLE001
            return pd.DataFrame(), enc, f"read_error:{type(exc).__name__}"
    return pd.DataFrame(), "", "read_error:encoding"


def first_col(df: pd.DataFrame, names: list[str]) -> str | None:
    lowered = {c.lower(): c for c in df.columns}
    for name in names:
        if name in df.columns:
            return name
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def period_stats(df: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {"period_min": "", "period_max": "", "year_min": "", "year_max": "", "period_count": ""}
    if df.empty:
        return out
    candidates = [
        "observation_period",
        "period",
        "prd_de",
        "source_period",
        "PRD_DE",
        "time",
        "date",
        "quarter",
        "year",
        "연도",
        "시점",
    ]
    col = first_col(df, candidates)
    values: pd.Series
    if col is None:
        # Try any column containing period/year/date.
        maybe = [c for c in df.columns if re.search(r"period|year|date|prd|시점|연도", c, re.I)]
        col = maybe[0] if maybe else None
    if col is None:
        return out
    values = df[col].dropna().astype(str)
    if values.empty:
        return out
    years = values.str.extract(r"((?:19|20)\d{2})", expand=False).dropna()
    out["period_min"] = values.min()
    out["period_max"] = values.max()
    out["period_count"] = int(values.nunique())
    if not years.empty:
        out["year_min"] = int(years.astype(int).min())
        out["year_max"] = int(years.astype(int).max())
    return out


def geo_stats(df: pd.DataFrame) -> dict[str, Any]:
    out = {"region_col": "", "region_count": "", "province_count": "", "sigungu_count": ""}
    if df.empty:
        return out
    region_col = first_col(
        df,
        [
            "province_full",
            "quarter_region",
            "matched_province_full",
            "sido_name_normalized",
            "sido_name",
            "c1_nm",
            "region",
            "region_name",
            "시도",
            "지역",
            "city",
            "sigungu",
            "matched_city",
        ],
    )
    if region_col:
        out["region_col"] = region_col
        out["region_count"] = int(df[region_col].dropna().astype(str).nunique())
    province_col = first_col(df, ["province_full", "matched_province_full", "quarter_region", "sido_name_normalized", "sido_name", "c1_nm", "시도"])
    if province_col:
        out["province_count"] = int(df[province_col].dropna().astype(str).nunique())
    sigungu_col = first_col(df, ["city", "sigungu", "matched_city", "sigungu_name_normalized", "sigungu_name", "시군구", "sigungu_name"])
    if sigungu_col:
        out["sigungu_count"] = int(df[sigungu_col].dropna().astype(str).nunique())
    return out


def pps_manifest_stats(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty or "period" not in df.columns:
        return {}
    d = df.copy()
    valid = d["period"].astype(str).str.fullmatch(r"\d{6}", na=False)
    d = d[valid].copy()
    d["period"] = d["period"].astype(str)
    complete = d["complete"].astype(str).str.lower().isin({"true", "1", "yes"}) if "complete" in d else pd.Series(False, index=d.index)
    d["year"] = d["period"].str[:4]
    annual = d.groupby("year")["period"].count().rename("months_seen").reset_index()
    annual_complete = d[complete].groupby("year")["period"].count().rename("months_complete").reset_index()
    annual = annual.merge(annual_complete, on="year", how="left").fillna({"months_complete": 0})
    adoptable = int((annual["months_complete"].astype(int) == 12).sum())
    return {
        "pps_months_complete": int(complete.sum()),
        "pps_adoptable_years": adoptable,
        "pps_first_incomplete_period": d.loc[~complete, "period"].min() if (~complete).any() else "",
    }


def coverage_status(row: dict[str, Any]) -> str:
    if not row["exists"]:
        return "missing"
    if row["source_id"] == "pps_contract_info":
        return "blocked_api_incomplete" if row.get("pps_adoptable_years", 0) < 11 else "complete"
    if row["source_id"] == "index_base_bridge":
        return "metadata_ok"
    if row["expected_scope"] in {"local_only", "partial_industry", "public_soc_partial", "public_housing_land_partial"}:
        return "partial_by_definition"
    y_min = row.get("year_min")
    y_max = row.get("year_max")
    try:
        y_min_i = int(y_min)
        y_max_i = int(y_max)
    except (TypeError, ValueError):
        return "metadata_only_or_period_unknown"
    if y_min_i <= 2015 and y_max_i >= 2025:
        return "covers_2015_2025"
    if y_max_i >= 2023 and y_min_i <= 2021:
        return "usable_for_2021_2025_backtest_with_limits"
    return "limited_period"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for spec in SOURCE_SPECS:
        path = ROOT / spec["path"]
        df, encoding, read_status = read_table(path)
        row: dict[str, Any] = {
            **spec,
            "local_path": spec["path"],
            "exists": path.exists(),
            "read_status": read_status,
            "encoding_or_type": encoding,
            "rows": int(len(df)) if read_status == "ok" else 0,
            "columns": int(len(df.columns)) if read_status == "ok" else 0,
        }
        row.update(period_stats(df))
        row.update(geo_stats(df))
        if spec.get("special") == "pps_manifest":
            row.update(pps_manifest_stats(df))
        row["coverage_status"] = coverage_status(row)
        rows.append(row)

    audit = pd.DataFrame(rows)
    audit.to_csv(CSV, index=False, encoding="utf-8-sig")

    status_summary = audit.groupby("coverage_status", as_index=False).size().rename(columns={"size": "source_count"})

    def md_table(df: pd.DataFrame) -> str:
        if df.empty:
            return "_해당 없음_"
        x = df.copy()
        for c in x.columns:
            x[c] = x[c].fillna("").astype(str)
        lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
        for _, r in x.iterrows():
            lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
        return "\n".join(lines)

    display_cols = [
        "source_id",
        "label",
        "exists",
        "rows",
        "period_min",
        "period_max",
        "year_min",
        "year_max",
        "province_count",
        "sigungu_count",
        "index_base",
        "expected_scope",
        "coverage_status",
        "notes",
    ]
    report = f"""# 2015~2025 전국 자료 coverage 감사

생성시각: {datetime.now().astimezone().isoformat(timespec='seconds')}

## 1. 목적

전국 광역시도·시군구 월/분기 GVA·GRDP 추정에 사용하는 주요 자료군이 2015~2025 기간, 지역 범위, 기준연도, 공표/수집 상태 측면에서 충분한지 점검했다. 이 감사는 자료가 존재한다는 사실과 운영 채택 가능성을 구분한다.

## 2. 상태 요약

{md_table(status_summary)}

## 3. 자료별 판정

{md_table(audit[display_cols])}

## 4. 핵심 판정

- `시도별 분기 GRDP/GDP`, 생산·서비스 지수 계열은 2015~2025 전국/시도 검증에 대체로 사용 가능하다.
- 시군구 연간 GVA actual은 공식 공표 범위가 2020~2023 중심이고 시도별 누락연도가 있다. 따라서 2015~2025 전기간 시군구 actual 검증은 불가능하며, 2021~2025 backtest는 직전연도/재귀 기준값과 상위 집계검증을 병행해야 한다.
- 조달청 공사계약은 전국 원본 성격이 맞지만 API 429로 전량 수집이 끝나지 않았다. 현재는 건설업 전국 route 채택이 아니라 수집·품질게이트 보류 상태다.
- CALS, LH, 서울 도시정비사업은 보조자료이며, 각각 공공/SOC·공공주택·서울 정비사업으로 범위가 제한된다.
- 현재 로컬 주요 지수는 2020=100 소급계열이므로 2015=100/2020=100 혼재 왜곡은 확인되지 않았다. 향후 legacy 2015=100 계열이 추가되면 bridge year 재기준화가 필요하다.

## 5. 산출물

- `{CSV.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(audit[["source_id", "coverage_status", "year_min", "year_max", "rows"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
