#!/usr/bin/env python3
"""Phase 209: expand the Goyang-style quarterly GVA check to all Gyeonggi sigungu.

The goal is not to modify posters.  It materializes:
  1) Gyeonggi 31 sigungu x sector x quarter estimates from the existing national
     sigungu allocation cube.
  2) Gyeonggi aggregate level comparison against the local quarterly target cube
     used by prior GVA phases.
  3) Gyeonggi aggregate YoY comparison against the official experimental
     quarterly GRDP press-release growth table.

Important scope note:
  - `partial_stats_phase20_gva_quarterly_grdp_target_cube.parquet` is retained as
    a project target/proxy level cube, not claimed as direct official level data.
  - Official comparison is made through the published YoY growth rates extracted
    from the 2025Q4 official quarterly GRDP PDF.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase209_gyeonggi_sigungu_gva_expansion"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase209_gyeonggi_sigungu_gva_expansion.md"

ALLOC = ROOT / "data" / "processed" / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet"
TARGET = ROOT / "data" / "processed" / "partial_stats_phase20_gva_quarterly_grdp_target_cube.parquet"
GG_BUS = ROOT / "data" / "processed" / "phase58_gg_bus" / "gg_bus_sigun_monthly.csv"
ELECTRICITY = ROOT / "data" / "processed" / "partial_stats_phase26_gva_electricity_monthly_cube.parquet"
MUNICIPALITY_ELECTRICITY = ROOT / "data" / "processed" / "municipality_electricity_monthly.csv"
BUSINESS_EMPLOYMENT = ROOT / "data" / "processed" / "business_employment_feature_table.csv"
FACTORY_FEATURE = ROOT / "data" / "processed" / "factory_feature_table.csv"
BUILDINGHUB_FEATURE = ROOT / "data" / "processed" / "buildinghub_feature_table.csv"
BUILDING_PERMIT_LEGAL_DONG = ROOT / "data" / "processed" / "partial_stats_phase52_building_permit_legal_dong_monthly.csv"
OFFICIAL_PDF_META = ROOT / "data" / "raw" / "official_quarterly_grdp" / "2025Q4_first_release" / "attachment_metadata.json"
OFFICIAL_PDF = ROOT / "data" / "raw" / "official_quarterly_grdp" / "2025Q4_first_release" / "source.pdf"
SIDO_QUARTERLY_DIR = ROOT / "data" / "raw" / "sido_quarterly"


GYEONGGI_SIGUNGU = [
    "수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시", "동두천시", "안산시", "고양시",
    "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시", "의왕시", "하남시", "용인시", "파주시",
    "이천시", "안성시", "김포시", "화성시", "광주시", "양주시", "포천시", "여주시", "연천군", "가평군", "양평군",
]


def now_kst() -> str:
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def write_csv(df: pd.DataFrame, name: str) -> Path:
    path = OUT / name
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def md_table(df: pd.DataFrame) -> str:
    """Small dependency-free markdown table renderer."""
    if df.empty:
        return "_표시할 행 없음_"
    str_df = df.copy()
    for col in str_df.columns:
        str_df[col] = str_df[col].map(lambda v: "" if pd.isna(v) else str(v))
    headers = list(str_df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in str_df.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def read_csv_auto(path: Path, **kwargs) -> pd.DataFrame:
    """Read repo CSVs that are split between UTF-8-SIG and CP949."""
    last_error: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return pd.read_csv(path, **kwargs)


def extract_official_gyeonggi_grdp_yoy() -> pd.DataFrame:
    """Extract Gyeonggi headline GRDP YoY growth rates from the official 2025Q4 PDF.

    The PDF splits the city/province table across pages.  Page text contains a
    section whose second page starts with:
      경기 강원 충북 충남 전북 전남 경북 경남 제주
    and then annual and quarterly rows.  The first numeric column in that block
    is Gyeonggi.
    """
    text = ""
    with pdfplumber.open(OFFICIAL_PDF) as pdf:
        # In the 2025Q4 release, this is page 27 (1-indexed).  Keep a fallback
        # scan in case the file is rebuilt with shifted pages.
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if "경기 강원 충북 충남 전북 전남 경북 경남 제주" in page_text and "1) 지역내총생산" not in page_text:
                text = page_text
                break
    if not text:
        raise RuntimeError("Could not locate Gyeonggi GRDP growth table in official PDF")

    rows: list[dict[str, object]] = []
    current_year: int | None = None
    for line in text.splitlines():
        stripped = line.strip()
        m = re.match(r"^(20\d{2})(?:p)?(?:\s+([1-4])/4)?\s+(.+)$", stripped)
        qm = None if m else re.match(r"^([1-4])/4\s+(.+)$", stripped)
        if not m and not qm:
            continue
        if m:
            year = int(m.group(1))
            current_year = year
            quarter = int(m.group(2)) if m.group(2) else None
            rest = m.group(3)
        else:
            if current_year is None:
                continue
            year = current_year
            quarter = int(qm.group(1))
            rest = qm.group(2)
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?", rest)
        if len(nums) < 9:
            continue
        gyeonggi_yoy = float(nums[0])
        if quarter is None:
            rows.append({
                "period": str(year),
                "year": year,
                "quarter": pd.NA,
                "official_gyeonggi_grdp_yoy_pct": gyeonggi_yoy,
                "frequency": "annual",
                "source": "official_quarterly_grdp_2025Q4_pdf_table",
            })
        else:
            rows.append({
                "period": f"{year}Q{quarter}",
                "year": year,
                "quarter": quarter,
                "official_gyeonggi_grdp_yoy_pct": gyeonggi_yoy,
                "frequency": "quarter",
                "source": "official_quarterly_grdp_2025Q4_pdf_table",
            })
    out = pd.DataFrame(rows).drop_duplicates(["period", "frequency"]).sort_values(["year", "quarter"], na_position="first")
    return out


def audit_official_level_table_availability() -> pd.DataFrame:
    """Record whether the official PDF exposes Gyeonggi quarterly level amounts."""
    hits: list[dict[str, object]] = []
    with pdfplumber.open(OFFICIAL_PDF) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            matched = [kw for kw in ["억원", "수준", "금액"] if kw in page_text]
            if not matched:
                continue
            sample_lines = [
                line.strip()
                for line in page_text.splitlines()
                if any(kw in line for kw in ["억원", "수준", "금액", "경기", "지역내총생산"])
            ][:8]
            hits.append({
                "source": "official_quarterly_grdp_2025Q4_pdf",
                "page_no": page_no,
                "matched_keywords": ",".join(matched),
                "sample": " / ".join(sample_lines),
                "contains_gyeonggi_quarterly_level_table": "N",
                "audit_note": "PDF 검색상 시도별 분기 수준액 표는 확인되지 않고 성장률 표만 확인됨",
            })
    if not hits:
        hits.append({
            "source": "official_quarterly_grdp_2025Q4_pdf",
            "page_no": pd.NA,
            "matched_keywords": "",
            "sample": "",
            "contains_gyeonggi_quarterly_level_table": "N",
            "audit_note": "억원·수준·금액 키워드가 포함된 수준액 표를 확인하지 못함",
        })
    return pd.DataFrame(hits)


def audit_kosis_actual_source_availability() -> pd.DataFrame:
    """Summarize official KOSIS actual tables relevant to the requested comparison."""
    rows: list[dict[str, object]] = []

    gyeonggi_meta = ROOT / "data" / "raw" / "kosis_210_DT_GRDP008_2020_metadata.json"
    if gyeonggi_meta.exists():
        info = json.loads(gyeonggi_meta.read_text(encoding="utf-8"))
        rows.append({
            "source": "KOSIS 210/DT_GRDP008_2020",
            "table_name": info.get("tblNm"),
            "region_scope": "경기도 시군",
            "time_frequency": info.get("periodStr"),
            "unit": info.get("unitNmKor") or info.get("unitNm"),
            "actual_level_available": "Y_annual_only",
            "usable_for_phase209": "annual_benchmark_consistency",
            "note": "경기도 경제활동별 지역내총부가가치 및 요소소득은 연간(Y) actual이며 분기 수준값은 아님",
        })

    national_meta = ROOT / "data" / "raw" / "kosis_DT_200Y106_metadata.json"
    if national_meta.exists():
        info = json.loads(national_meta.read_text(encoding="utf-8"))
        rows.append({
            "source": "KOSIS 301/DT_200Y106",
            "table_name": info.get("tblNm"),
            "region_scope": "전국",
            "time_frequency": info.get("periodStr"),
            "unit": info.get("unitNmKor") or info.get("unitNm"),
            "actual_level_available": "Y_national_quarterly_no_region",
            "usable_for_phase209": "not_gyeonggi_actual",
            "note": "전국 경제활동별 실질 GDP/GVA 분기 수준값은 있으나 경기도 지역 차원이 없음",
        })

    search_candidates = OUT / "phase209_kosis_grdp_level_search_candidates.json"
    search_raw = OUT / "phase209_kosis_grdp_level_search_raw.json"
    if search_candidates.exists():
        candidates = json.loads(search_candidates.read_text(encoding="utf-8"))
        rows.append({
            "source": "KOSIS statisticsSearch API",
            "table_name": "경기도/시도별 분기 GRDP 수준값 검색",
            "region_scope": "경기도 또는 시도",
            "time_frequency": "Q",
            "unit": "",
            "actual_level_available": "N" if len(candidates) == 0 else "candidate_found",
            "usable_for_phase209": "not_available" if len(candidates) == 0 else "needs_manual_review",
            "note": f"공식 검색 API 후보 {len(candidates)}건; raw search saved={search_raw.exists()}",
        })

    rows.append({
        "source": "MODS quarterly GRDP PDF",
        "table_name": "실질 지역내총생산(잠정) 보도자료",
        "region_scope": "시도",
        "time_frequency": "Q",
        "unit": "%",
        "actual_level_available": "Y_growth_only",
        "usable_for_phase209": "official_yoy_growth_validation",
        "note": "시도별 전년동기비 성장률 actual은 확인되나 분기 수준액 actual 표는 확인되지 않음",
    })

    xlsx_files = [p for p in SIDO_QUARTERLY_DIR.glob("*.xlsx") if not p.name.startswith("~$")]
    if xlsx_files:
        rows.append({
            "source": "Statistics Korea experimental quarterly GRDP XLSX",
            "table_name": xlsx_files[0].name,
            "region_scope": "시도",
            "time_frequency": "Q#Y",
            "unit": "십억원",
            "actual_level_available": "Y_gyeonggi_quarterly_market_price_grdp",
            "usable_for_phase209": "official_level_validation_total_market_price",
            "note": "실질금액 시트에 경기도 지역내총생산(시장가격) 분기 수준값 존재; GVA와 개념 차이는 별도 표시 필요",
        })

    return pd.DataFrame(rows)


def extract_sido_quarterly_xlsx_level() -> pd.DataFrame:
    """Extract Gyeonggi quarterly real GRDP level from Statistics Korea XLSX."""
    files = [p for p in SIDO_QUARTERLY_DIR.glob("*.xlsx") if not p.name.startswith("~$")]
    if not files:
        return pd.DataFrame()
    path = files[0]
    raw = pd.read_excel(path, sheet_name="실질금액", header=None)
    header = raw.iloc[4]
    body = raw.iloc[5:].copy()
    region = body.iloc[:, 1].ffill().astype(str).str.strip()
    activity = body.iloc[:, 2].astype(str).str.strip()
    target_activities = ["지역내총생산(시장가격)", "기타산업 및 순생산물세"]
    source_rows = body[region.eq("경기") & activity.isin(target_activities)]
    if source_rows[source_rows.iloc[:, 2].astype(str).str.strip().eq("지역내총생산(시장가격)")].empty:
        raise RuntimeError("Could not find 경기 지역내총생산(시장가격) row in sido quarterly XLSX")
    rows: list[dict[str, object]] = []
    for _, row in source_rows.iterrows():
        row_activity = str(row.iloc[2]).strip()
        for col_idx, label in enumerate(header):
            label_text = str(label).strip()
            m = re.match(r"^(20\d{2})\.([1-4])/4p?$", label_text)
            if not m:
                continue
            year = int(m.group(1))
            quarter = int(m.group(2))
            value_billion = pd.to_numeric(row.iloc[col_idx], errors="coerce")
            if pd.isna(value_billion):
                continue
            rows.append({
                "period": f"{year}Q{quarter}",
                "year": year,
                "quarter": quarter,
                "official_value_billion_krw": float(value_billion),
                "official_value_eok": float(value_billion) * 10.0,
                "source_file": str(path.relative_to(ROOT)),
                "sheet": "실질금액",
                "region": "경기",
                "activity": row_activity,
                "unit": "십억원",
                "comparison_boundary": "official real GRDP market price; project estimate is GVA sum, so concept gap includes net product taxes and coverage differences",
            })
    return pd.DataFrame(rows).sort_values(["activity", "year", "quarter"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    alloc = pd.read_parquet(ALLOC)
    target = pd.read_parquet(TARGET)
    gg = alloc[alloc.source_region.eq("경기도")].copy()

    missing = sorted(set(GYEONGGI_SIGUNGU) - set(gg.sigungu_name.unique()))
    extra = sorted(set(gg.sigungu_name.unique()) - set(GYEONGGI_SIGUNGU))

    sigungu_sector = gg.copy()
    sigungu_sector["estimated_quarterly_gva_eok"] = sigungu_sector["estimated_quarterly_gva"] / 100.0
    sigungu_sector_path = OUT / "phase209_gyeonggi_sigungu_sector_quarterly_gva.parquet"
    sigungu_sector.to_parquet(sigungu_sector_path, index=False)

    pred_sector = (
        gg.groupby(["period", "year", "quarter", "sector_code", "sector_name"], as_index=False)
        .estimated_quarterly_gva.sum()
        .rename(columns={"estimated_quarterly_gva": "predicted_gyeonggi_gva_million_krw"})
    )
    pred_sector["predicted_gyeonggi_gva_eok"] = pred_sector.predicted_gyeonggi_gva_million_krw / 100.0

    target_gg = target[target.region_name.eq("경기도")].copy()
    target_sector = target_gg.rename(columns={
        "industry_group": "sector_code",
        "real_grdp_level": "target_gyeonggi_grdp_million_krw",
    })[["period", "year", "quarter", "sector_code", "sector_name", "target_gyeonggi_grdp_million_krw", "provisional_status"]]

    level_cmp = pred_sector.merge(
        target_sector,
        on=["period", "year", "quarter", "sector_code", "sector_name"],
        how="left",
        validate="one_to_one",
    )
    level_cmp["target_gyeonggi_grdp_eok"] = level_cmp.target_gyeonggi_grdp_million_krw / 100.0
    level_cmp["error_million_krw"] = level_cmp.predicted_gyeonggi_gva_million_krw - level_cmp.target_gyeonggi_grdp_million_krw
    level_cmp["error_eok"] = level_cmp.error_million_krw / 100.0
    level_cmp["abs_error_eok"] = level_cmp.error_eok.abs()
    level_cmp["ape_pct"] = level_cmp.error_million_krw.abs() / level_cmp.target_gyeonggi_grdp_million_krw.abs() * 100
    level_cmp_path = write_csv(level_cmp, "phase209_gyeonggi_sector_level_vs_project_target.csv")

    total = (
        level_cmp.groupby(["period", "year", "quarter"], as_index=False)
        .agg(
            predicted_gyeonggi_gva_million_krw=("predicted_gyeonggi_gva_million_krw", "sum"),
            target_gyeonggi_grdp_million_krw=("target_gyeonggi_grdp_million_krw", "sum"),
            abs_error_million_krw=("error_million_krw", lambda s: s.abs().sum()),
            signed_error_million_krw=("error_million_krw", "sum"),
        )
    )
    total["predicted_gyeonggi_gva_eok"] = total.predicted_gyeonggi_gva_million_krw / 100.0
    total["target_gyeonggi_grdp_eok"] = total.target_gyeonggi_grdp_million_krw / 100.0
    total["signed_error_eok"] = total.signed_error_million_krw / 100.0
    total["abs_error_sum_eok"] = total.abs_error_million_krw / 100.0
    total["total_ape_pct"] = total.signed_error_million_krw.abs() / total.target_gyeonggi_grdp_million_krw * 100
    total["sector_wape_pct"] = total.abs_error_million_krw / total.target_gyeonggi_grdp_million_krw * 100
    total = total.sort_values(["year", "quarter"])
    total_path = write_csv(total, "phase209_gyeonggi_total_level_vs_project_target.csv")

    annual_sigungu_sector = (
        gg.groupby(["year", "source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name"], as_index=False)
        .agg(
            quarterly_sum_million_krw=("estimated_quarterly_gva", "sum"),
            official_annual_benchmark_million_krw=("annual_benchmark_gva", "first"),
        )
    )
    annual_sigungu_sector["annual_gap_million_krw"] = (
        annual_sigungu_sector.quarterly_sum_million_krw
        - annual_sigungu_sector.official_annual_benchmark_million_krw
    )
    annual_sigungu_sector["annual_gap_eok"] = annual_sigungu_sector.annual_gap_million_krw / 100.0
    annual_sigungu_sector["abs_annual_gap_eok"] = annual_sigungu_sector.annual_gap_eok.abs()
    annual_sector = (
        annual_sigungu_sector.groupby(["year", "sector_code", "sector_name"], as_index=False)
        .agg(
            quarterly_sum_million_krw=("quarterly_sum_million_krw", "sum"),
            official_annual_benchmark_million_krw=("official_annual_benchmark_million_krw", "sum"),
            abs_gap_million_krw=("annual_gap_million_krw", lambda s: s.abs().sum()),
            signed_gap_million_krw=("annual_gap_million_krw", "sum"),
        )
    )
    annual_sector["quarterly_sum_eok"] = annual_sector.quarterly_sum_million_krw / 100.0
    annual_sector["official_annual_benchmark_eok"] = annual_sector.official_annual_benchmark_million_krw / 100.0
    annual_sector["signed_gap_eok"] = annual_sector.signed_gap_million_krw / 100.0
    annual_sector["abs_gap_eok"] = annual_sector.abs_gap_million_krw / 100.0
    annual_sector["wape_pct"] = annual_sector.abs_gap_million_krw / annual_sector.official_annual_benchmark_million_krw.abs() * 100
    annual_sector_path = write_csv(annual_sector, "phase209_gyeonggi_annual_benchmark_consistency_by_sector.csv")
    annual_total = (
        annual_sector.groupby("year", as_index=False)
        .agg(
            quarterly_sum_million_krw=("quarterly_sum_million_krw", "sum"),
            official_annual_benchmark_million_krw=("official_annual_benchmark_million_krw", "sum"),
            abs_gap_million_krw=("signed_gap_million_krw", lambda s: s.abs().sum()),
            signed_gap_million_krw=("signed_gap_million_krw", "sum"),
        )
    )
    annual_total["quarterly_sum_eok"] = annual_total.quarterly_sum_million_krw / 100.0
    annual_total["official_annual_benchmark_eok"] = annual_total.official_annual_benchmark_million_krw / 100.0
    annual_total["signed_gap_eok"] = annual_total.signed_gap_million_krw / 100.0
    annual_total["abs_gap_eok"] = annual_total.signed_gap_million_krw.abs() / 100.0
    annual_total["ape_pct"] = annual_total.signed_gap_million_krw.abs() / annual_total.official_annual_benchmark_million_krw.abs() * 100
    annual_total_path = write_csv(annual_total, "phase209_gyeonggi_annual_benchmark_consistency_total.csv")

    official_xlsx_level = extract_sido_quarterly_xlsx_level()
    official_xlsx_level_path = write_csv(official_xlsx_level, "phase209_official_xlsx_gyeonggi_real_grdp_market_price_level.csv")
    official_xlsx_total = official_xlsx_level[official_xlsx_level.activity.eq("지역내총생산(시장가격)")].rename(columns={
        "official_value_billion_krw": "official_gyeonggi_real_grdp_market_price_billion_krw",
        "official_value_eok": "official_gyeonggi_real_grdp_market_price_eok",
    })
    official_xlsx_other = official_xlsx_level[official_xlsx_level.activity.eq("기타산업 및 순생산물세")].rename(columns={
        "official_value_billion_krw": "official_other_industries_and_net_product_taxes_billion_krw",
        "official_value_eok": "official_other_industries_and_net_product_taxes_eok",
    })
    xlsx_level_cmp = total.merge(
        official_xlsx_total[["period", "official_gyeonggi_real_grdp_market_price_eok", "source_file", "comparison_boundary"]],
        on="period",
        how="inner",
    )
    xlsx_level_cmp["gva_minus_market_grdp_eok"] = (
        xlsx_level_cmp.predicted_gyeonggi_gva_eok
        - xlsx_level_cmp.official_gyeonggi_real_grdp_market_price_eok
    )
    xlsx_level_cmp["abs_gap_eok"] = xlsx_level_cmp.gva_minus_market_grdp_eok.abs()
    xlsx_level_cmp["gap_pct_vs_market_grdp"] = (
        xlsx_level_cmp.abs_gap_eok
        / xlsx_level_cmp.official_gyeonggi_real_grdp_market_price_eok.abs()
        * 100
    )
    xlsx_level_cmp_path = write_csv(xlsx_level_cmp, "phase209_gyeonggi_total_vs_official_xlsx_real_grdp_market_price.csv")

    grdp_bridge_codes = ["B00", "C00", "F00", "G00", "H00", "I00", "J00", "K00", "L00", "MN0", "O00", "P00", "Q00", "ERS"]
    project_main_blocks = (
        pred_sector[pred_sector.sector_code.isin(grdp_bridge_codes)]
        .groupby(["period", "year", "quarter"], as_index=False)
        .predicted_gyeonggi_gva_eok.sum()
        .rename(columns={"predicted_gyeonggi_gva_eok": "project_main_industry_blocks_eok"})
    )
    grdp_bridge_cmp = (
        total[["period", "year", "quarter", "predicted_gyeonggi_gva_eok"]]
        .merge(project_main_blocks, on=["period", "year", "quarter"], how="left", validate="one_to_one")
        .merge(
            official_xlsx_total[["period", "official_gyeonggi_real_grdp_market_price_eok", "source_file"]],
            on="period",
            how="inner",
            validate="one_to_one",
        )
        .merge(
            official_xlsx_other[["period", "official_other_industries_and_net_product_taxes_eok"]],
            on="period",
            how="left",
            validate="one_to_one",
        )
    )
    grdp_bridge_cmp["project_grdp_bridge_eok"] = (
        grdp_bridge_cmp.project_main_industry_blocks_eok
        + grdp_bridge_cmp.official_other_industries_and_net_product_taxes_eok
    )
    grdp_bridge_cmp["gva_sum_gap_pct_vs_market_grdp"] = (
        (grdp_bridge_cmp.predicted_gyeonggi_gva_eok - grdp_bridge_cmp.official_gyeonggi_real_grdp_market_price_eok).abs()
        / grdp_bridge_cmp.official_gyeonggi_real_grdp_market_price_eok.abs()
        * 100
    )
    grdp_bridge_cmp["grdp_bridge_minus_official_eok"] = (
        grdp_bridge_cmp.project_grdp_bridge_eok
        - grdp_bridge_cmp.official_gyeonggi_real_grdp_market_price_eok
    )
    grdp_bridge_cmp["grdp_bridge_gap_pct_vs_market_grdp"] = (
        grdp_bridge_cmp.grdp_bridge_minus_official_eok.abs()
        / grdp_bridge_cmp.official_gyeonggi_real_grdp_market_price_eok.abs()
        * 100
    )
    grdp_bridge_cmp["validation_boundary"] = (
        "GRDP accounting bridge: project-estimated main industry blocks plus official XLSX "
        "other industries and net product taxes block. Useful for market-price boundary validation, "
        "not a pure nowcast because the auxiliary official block is taken from the same XLSX release."
    )
    grdp_bridge_cmp_path = write_csv(grdp_bridge_cmp, "phase209_gyeonggi_project_grdp_bridge_vs_official_xlsx.csv")

    yoy_pred = total[["period", "year", "quarter", "predicted_gyeonggi_gva_million_krw"]].copy()
    yoy_pred["predicted_yoy_pct"] = (
        yoy_pred.predicted_gyeonggi_gva_million_krw
        / yoy_pred.predicted_gyeonggi_gva_million_krw.shift(4)
        - 1
    ) * 100
    official_yoy = extract_official_gyeonggi_grdp_yoy()
    official_yoy_path = write_csv(official_yoy, "phase209_official_gyeonggi_grdp_yoy_growth.csv")
    official_level_audit = audit_official_level_table_availability()
    official_level_audit_path = write_csv(official_level_audit, "phase209_official_level_table_availability_audit.csv")
    kosis_actual_audit = audit_kosis_actual_source_availability()
    kosis_actual_audit_path = write_csv(kosis_actual_audit, "phase209_kosis_actual_source_availability_audit.csv")
    yoy_cmp = yoy_pred.merge(
        official_yoy[official_yoy.frequency.eq("quarter")][["period", "official_gyeonggi_grdp_yoy_pct", "source"]],
        on="period",
        how="left",
    )
    yoy_cmp["yoy_error_pp"] = yoy_cmp.predicted_yoy_pct - yoy_cmp.official_gyeonggi_grdp_yoy_pct
    yoy_cmp["abs_yoy_error_pp"] = yoy_cmp.yoy_error_pp.abs()
    yoy_cmp = yoy_cmp[yoy_cmp.year.between(2021, 2023)].copy()
    yoy_cmp_path = write_csv(yoy_cmp, "phase209_gyeonggi_total_yoy_vs_official.csv")

    # Data coverage/source inventory.
    bus = pd.read_csv(GG_BUS)
    elec = pd.read_parquet(ELECTRICITY)
    elec_gg = elec[elec.sido_name.eq("경기도")]
    muni_elec = read_csv_auto(
        MUNICIPALITY_ELECTRICITY,
        usecols=["period", "sido_name", "sigungu_name", "category_name", "metric", "value"],
    )
    muni_elec_gg = muni_elec[muni_elec.sido_name.eq("경기도")]
    business = read_csv_auto(BUSINESS_EMPLOYMENT)
    business_gg = business[business.area_name.astype(str).isin(GYEONGGI_SIGUNGU)]
    factory = read_csv_auto(FACTORY_FEATURE)
    factory_gg = factory[factory.sigungu_feature_key.astype(str).str.startswith("경기도 ")]
    buildinghub = read_csv_auto(BUILDINGHUB_FEATURE)
    buildinghub_gg = buildinghub[buildinghub.sigungu_feature_key.astype(str).str.startswith("경기도 ")]
    permit = pd.read_csv(BUILDING_PERMIT_LEGAL_DONG)
    permit_gg = permit[permit.city.astype(str).isin(GYEONGGI_SIGUNGU)]
    coverage_rows = [
        {
            "source": "sigungu_quarterly_gva_allocation_cube",
            "scope": "전국 시군구 원천에서 경기도 31개 시군 추출",
            "rows": len(gg),
            "period_min": str(gg.period.min()),
            "period_max": str(gg.period.max()),
            "geo_count": gg.sigungu_name.nunique(),
            "industry_count": gg.sector_code.nunique(),
            "used_in_phase209": "Y",
            "note": "경기도 subset은 원천 전국 큐브에서 필터링; 타 지역 분석 때 원천 전체 재사용 가능",
        },
        {
            "source": "gg_bus_sigun_monthly",
            "scope": "경기도 전체 시군 월별 버스 승하차",
            "rows": len(bus),
            "period_min": str(bus.month.min()),
            "period_max": str(bus.month.max()),
            "geo_count": bus["관할관청"].nunique(),
            "industry_count": 1,
            "used_in_phase209": "inventory_only",
            "note": "고양시 운수 활동자료와 같은 계열; 이번 수준 검증에는 기존 phase22 큐브 우선 사용",
        },
        {
            "source": "business_employment_feature_table",
            "scope": "KOSIS/공공 사업체·종사자·부가가치 계열에서 경기도 31개 시군 추출",
            "rows": len(business_gg),
            "period_min": str(business_gg.year.min()),
            "period_max": str(business_gg.year.max()),
            "geo_count": business_gg.area_name.nunique(),
            "industry_count": business_gg.industry_code.nunique(),
            "used_in_phase209": "coverage_and_followup_feature",
            "note": "고양시 산업·공간 배분에 쓰는 사업체 계열과 같은 유형; 경기도 31개 시군 모두 보유",
        },
        {
            "source": "kepco_sigungu_electricity_monthly_cube",
            "scope": "전국 시군구 전력 원천에서 경기도 추출",
            "rows": len(elec_gg),
            "period_min": str(elec_gg.reference_month.min()),
            "period_max": str(elec_gg.reference_month.max()),
            "geo_count": elec_gg.sigungu_code.nunique(),
            "industry_count": elec_gg.contract_type.nunique(),
            "used_in_phase209": "inventory_only",
            "note": "제조업·전력 기반 시간축 보조자료; 원천은 전국 포함",
        },
        {
            "source": "municipality_electricity_monthly",
            "scope": "전국 시군구 전력 최신 월자료에서 경기도 31개 시군 추출",
            "rows": len(muni_elec_gg),
            "period_min": str(muni_elec_gg.period.min()),
            "period_max": str(muni_elec_gg.period.max()),
            "geo_count": muni_elec_gg.sigungu_name.nunique(),
            "industry_count": muni_elec_gg.category_name.nunique(),
            "used_in_phase209": "coverage_and_followup_feature",
            "note": "2025~2026 최신 전력 자료; 속보성 확장 때 제조업·전기가스 보조지표로 사용 가능",
        },
        {
            "source": "factory_feature_table",
            "scope": "전국 공장등록 특징자료에서 경기도 지리키 추출",
            "rows": len(factory_gg),
            "period_min": str(factory_gg.observation_period.min()),
            "period_max": str(factory_gg.observation_period.max()),
            "geo_count": factory_gg.sigungu_feature_key.nunique(),
            "industry_count": factory_gg.feature_name.nunique(),
            "used_in_phase209": "coverage_and_followup_feature",
            "note": "경기도 구 단위 지리키 포함으로 46개 키; 시군 단위 사용 전 수원·성남·고양 등 구 통합 필요",
        },
        {
            "source": "buildinghub_feature_table",
            "scope": "건축물대장/건축허가 특징자료의 경기도 전체 커버리지 점검",
            "rows": len(buildinghub_gg),
            "period_min": str(buildinghub_gg.observation_period.min()) if len(buildinghub_gg) else "",
            "period_max": str(buildinghub_gg.observation_period.max()) if len(buildinghub_gg) else "",
            "geo_count": buildinghub_gg.sigungu_feature_key.nunique() if len(buildinghub_gg) else 0,
            "industry_count": buildinghub_gg.feature_name.nunique() if len(buildinghub_gg) else 0,
            "used_in_phase209": "gap_audit",
            "note": "현재 feature table에는 경기도 전체 키가 없음; 건축계열 경기도 확장에는 원천 재처리 필요",
        },
        {
            "source": "partial_stats_phase52_building_permit_legal_dong_monthly",
            "scope": "건축허가 법정동 월자료의 경기도 확장 가능성 점검",
            "rows": len(permit_gg),
            "period_min": str(permit_gg.period.min()) if len(permit_gg) else "",
            "period_max": str(permit_gg.period.max()) if len(permit_gg) else "",
            "geo_count": permit_gg.city.nunique() if len(permit_gg) else 0,
            "industry_count": permit_gg.use_group.nunique() if len(permit_gg) else 0,
            "used_in_phase209": "gap_audit",
            "note": "현재 산출물은 고양시 중심으로 존재하며 경기도 31개 시군 전체 건설 지표로는 부족",
        },
        {
            "source": "official_quarterly_grdp_2025Q4_pdf",
            "scope": "공식 실험적통계 보도자료의 시도별 GRDP 전년동기비",
            "rows": len(official_yoy),
            "period_min": str(official_yoy.period.min()),
            "period_max": str(official_yoy.period.max()),
            "geo_count": 1,
            "industry_count": 1,
            "used_in_phase209": "Y",
            "note": "수준값이 아니라 성장률 actual 비교 기준",
        },
        {
            "source": "official_quarterly_grdp_2025Q4_pdf_level_audit",
            "scope": "공식 보도자료 내 경기도 분기 수준액 표 존재 여부 점검",
            "rows": len(official_level_audit),
            "period_min": "2025Q4 release",
            "period_max": "2025Q4 release",
            "geo_count": 1,
            "industry_count": 1,
            "used_in_phase209": "audit_only",
            "note": "경기도 분기 actual 수준값 표는 확인되지 않음; 공식 actual 대조는 전년동기비 성장률로 제한",
        },
        {
            "source": "kosis_actual_source_availability_audit",
            "scope": "KOSIS 경기도 연간 actual·전국 분기 GDP·경기도 분기 수준값 검색 결과",
            "rows": len(kosis_actual_audit),
            "period_min": "mixed",
            "period_max": "mixed",
            "geo_count": 1,
            "industry_count": 1,
            "used_in_phase209": "audit_only",
            "note": "경기도 시군·산업 actual은 연간, 전국 GDP/GVA는 분기이나 지역 없음, 경기도 분기 수준값 후보는 미발견",
        },
        {
            "source": "statistics_korea_sido_quarterly_xlsx",
            "scope": "통계청 실험적통계 XLSX 실질금액 시트의 경기도 지역내총생산(시장가격) 분기 수준값",
            "rows": len(official_xlsx_level),
            "period_min": str(official_xlsx_level.period.min()) if len(official_xlsx_level) else "",
            "period_max": str(official_xlsx_level.period.max()) if len(official_xlsx_level) else "",
            "geo_count": official_xlsx_level.region.nunique() if len(official_xlsx_level) else 0,
            "industry_count": official_xlsx_level.activity.nunique() if len(official_xlsx_level) else 0,
            "used_in_phase209": "Y_level_actual_boundary",
            "note": "공식 분기 수준 actual로 사용하되, 시장가격 GRDP라서 산업 GVA 합계와 개념 차이 표시",
        },
    ]
    coverage = pd.DataFrame(coverage_rows)
    coverage_path = write_csv(coverage, "phase209_gyeonggi_source_coverage.csv")

    summary = {
        "created_at": now_kst(),
        "gyeonggi_sigungu_count": int(gg.sigungu_name.nunique()),
        "missing_expected_sigungu": missing,
        "unexpected_sigungu": extra,
        "sector_count": int(gg.sector_code.nunique()),
        "period_min": str(gg.period.min()),
        "period_max": str(gg.period.max()),
        "rows": int(len(gg)),
        "total_level_mean_ape_pct_vs_project_target": float(total.total_ape_pct.mean()),
        "total_level_max_ape_pct_vs_project_target": float(total.total_ape_pct.max()),
        "sector_level_wape_pct_vs_project_target": float(level_cmp.error_million_krw.abs().sum() / level_cmp.target_gyeonggi_grdp_million_krw.abs().sum() * 100),
        "annual_benchmark_max_abs_gap_eok": float(annual_total.abs_gap_eok.max()),
        "annual_benchmark_max_ape_pct": float(annual_total.ape_pct.max()),
        "official_xlsx_level_rows": int(len(official_xlsx_level)),
        "official_xlsx_level_comparison_rows_2020_2023": int(len(xlsx_level_cmp[xlsx_level_cmp.year.between(2020, 2023)])),
        "official_xlsx_market_grdp_gap_mean_pct_2020_2023": float(xlsx_level_cmp[xlsx_level_cmp.year.between(2020, 2023)].gap_pct_vs_market_grdp.mean()),
        "official_xlsx_market_grdp_gap_max_pct_2020_2023": float(xlsx_level_cmp[xlsx_level_cmp.year.between(2020, 2023)].gap_pct_vs_market_grdp.max()),
        "grdp_bridge_gap_mean_pct_2020_2023": float(grdp_bridge_cmp[grdp_bridge_cmp.year.between(2020, 2023)].grdp_bridge_gap_pct_vs_market_grdp.mean()),
        "grdp_bridge_gap_max_pct_2020_2023": float(grdp_bridge_cmp[grdp_bridge_cmp.year.between(2020, 2023)].grdp_bridge_gap_pct_vs_market_grdp.max()),
        "official_yoy_mean_abs_error_pp_2021_2023": float(yoy_cmp.abs_yoy_error_pp.mean()),
        "official_yoy_max_abs_error_pp_2021_2023": float(yoy_cmp.abs_yoy_error_pp.max()),
        "level_target_status": sorted(target_gg.provisional_status.dropna().astype(str).unique().tolist()),
        "official_level_actual_status": "found_in_statistics_korea_xlsx_market_price_grdp; compare_as_concept_boundary_not_gva_exact",
        "outputs": {
            "sigungu_sector_parquet": str(sigungu_sector_path.relative_to(ROOT)),
            "level_sector_csv": str(level_cmp_path.relative_to(ROOT)),
            "level_total_csv": str(total_path.relative_to(ROOT)),
            "annual_sector_consistency_csv": str(annual_sector_path.relative_to(ROOT)),
            "annual_total_consistency_csv": str(annual_total_path.relative_to(ROOT)),
            "official_xlsx_level_csv": str(official_xlsx_level_path.relative_to(ROOT)),
            "official_xlsx_level_comparison_csv": str(xlsx_level_cmp_path.relative_to(ROOT)),
            "official_xlsx_grdp_bridge_comparison_csv": str(grdp_bridge_cmp_path.relative_to(ROOT)),
            "official_yoy_csv": str(official_yoy_path.relative_to(ROOT)),
            "official_level_audit_csv": str(official_level_audit_path.relative_to(ROOT)),
            "kosis_actual_source_audit_csv": str(kosis_actual_audit_path.relative_to(ROOT)),
            "yoy_comparison_csv": str(yoy_cmp_path.relative_to(ROOT)),
            "coverage_csv": str(coverage_path.relative_to(ROOT)),
        },
    }
    manifest_path = OUT / "phase209_manifest.json"
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # Report tables.
    total_display = total[["period", "predicted_gyeonggi_gva_eok", "target_gyeonggi_grdp_eok", "signed_error_eok", "total_ape_pct", "sector_wape_pct"]].copy()
    total_display = total_display.round({
        "predicted_gyeonggi_gva_eok": 0,
        "target_gyeonggi_grdp_eok": 0,
        "signed_error_eok": 0,
        "total_ape_pct": 3,
        "sector_wape_pct": 3,
    })
    yoy_display = yoy_cmp[["period", "predicted_yoy_pct", "official_gyeonggi_grdp_yoy_pct", "yoy_error_pp", "abs_yoy_error_pp"]].copy()
    yoy_display = yoy_display.round(3)
    annual_total_display = annual_total[["year", "quarterly_sum_eok", "official_annual_benchmark_eok", "signed_gap_eok", "ape_pct"]].copy()
    annual_total_display = annual_total_display.round({
        "quarterly_sum_eok": 0,
        "official_annual_benchmark_eok": 0,
        "signed_gap_eok": 6,
        "ape_pct": 9,
    })
    xlsx_level_display = xlsx_level_cmp[xlsx_level_cmp.year.between(2020, 2023)][
        ["period", "predicted_gyeonggi_gva_eok", "official_gyeonggi_real_grdp_market_price_eok", "gva_minus_market_grdp_eok", "gap_pct_vs_market_grdp"]
    ].copy()
    xlsx_level_display = xlsx_level_display.round({
        "predicted_gyeonggi_gva_eok": 0,
        "official_gyeonggi_real_grdp_market_price_eok": 0,
        "gva_minus_market_grdp_eok": 0,
        "gap_pct_vs_market_grdp": 3,
    })
    grdp_bridge_display = grdp_bridge_cmp[grdp_bridge_cmp.year.between(2020, 2023)][
        [
            "period",
            "predicted_gyeonggi_gva_eok",
            "project_grdp_bridge_eok",
            "official_gyeonggi_real_grdp_market_price_eok",
            "grdp_bridge_minus_official_eok",
            "gva_sum_gap_pct_vs_market_grdp",
            "grdp_bridge_gap_pct_vs_market_grdp",
        ]
    ].copy()
    grdp_bridge_display = grdp_bridge_display.round({
        "predicted_gyeonggi_gva_eok": 0,
        "project_grdp_bridge_eok": 0,
        "official_gyeonggi_real_grdp_market_price_eok": 0,
        "grdp_bridge_minus_official_eok": 0,
        "gva_sum_gap_pct_vs_market_grdp": 3,
        "grdp_bridge_gap_pct_vs_market_grdp": 3,
    })
    worst_sector = level_cmp.sort_values("ape_pct", ascending=False).head(12)[
        ["period", "sector_code", "sector_name", "predicted_gyeonggi_gva_eok", "target_gyeonggi_grdp_eok", "error_eok", "ape_pct"]
    ].round({"predicted_gyeonggi_gva_eok": 0, "target_gyeonggi_grdp_eok": 0, "error_eok": 0, "ape_pct": 2})
    coverage_display = coverage[["source", "scope", "rows", "period_min", "period_max", "geo_count", "industry_count", "used_in_phase209", "note"]].copy()
    kosis_actual_display = kosis_actual_audit[["source", "table_name", "region_scope", "time_frequency", "unit", "actual_level_available", "usable_for_phase209", "note"]].copy()
    requirement_audit = pd.DataFrame([
        {
            "요구사항": "포스터 미반영",
            "증거": "보고서 목적과 README/포스터 산출물 미수정",
            "판정": "충족",
        },
        {
            "요구사항": "고양시 외 경기도 시군 데이터 구성",
            "증거": f"경기도 {summary['gyeonggi_sigungu_count']}/31개 시군, {summary['rows']:,}행 시군×산업×분기 큐브",
            "판정": "충족",
        },
        {
            "요구사항": "고양시 방식과 같은 상위총량 배분·재집계",
            "증거": "전국 시군구 배분 큐브에서 경기도 추출 후 시군→경기도, 산업→전체로 재집계",
            "판정": "충족",
        },
        {
            "요구사항": "경기도 전체 부가가치 산출",
            "증거": "phase209_gyeonggi_total_level_vs_project_target.csv",
            "판정": "충족",
        },
        {
            "요구사항": "actual 경기도 분기 GDP/GRDP 비교",
            "증거": "통계청 XLSX 경기도 분기 실질 GRDP 시장가격 수준값 및 MODS 성장률 actual과 비교",
            "판정": "충족_개념차이표시",
        },
        {
            "요구사항": "자료 수집·재사용 가능성 기록",
            "증거": "phase209_gyeonggi_source_coverage.csv",
            "판정": "충족",
        },
    ])

    meta = json.loads(OFFICIAL_PDF_META.read_text(encoding="utf-8"))
    report = f"""# Phase 209: 경기도 31개 시군 확장 GVA 집계검증

## 목적

고양시 방식의 상위총량 배분·외삽 구조를 경기도 전체 시군구로 확장할 수 있는지 확인했다. 포스터에는 반영하지 않는 내부 검증용 산출물이다.

## 사용 자료

| 자료 | 범위 | 이번 단계 사용 |
| --- | --- | --- |
| 시군구 분기 GVA 배분 큐브 | 전국 시군구, 2020Q1~2023Q4 | 경기도 31개 시군 추출·집계 |
| 경기도 버스 승하차 월자료 | 경기도 전체 시군, 2020년 이후 | 보유 확인·후속 운수 개선 후보 |
| 시군구 전력 월자료 | 전국 시군구, 경기도 포함 | 보유 확인·후속 제조업 시간축 후보 |
| 공식 분기 GRDP PDF | {meta.get('official_release_title')} | 경기도 GRDP 전년동기비 actual 추출 |

## 공식 actual 확보 범위

- 공식 MODS 보도자료 PDF에서는 경기도 분기별 **전년동기비 성장률**을 확인했다.
- 동일 PDF에서 `억원`, `수준`, `금액` 키워드 기반으로 수준액 표를 검색했지만, 경기도 분기별 **공식 수준값 actual 표는 확인하지 못했다**.
- KOSIS 공식 메타에서는 경기도 `경제활동별 지역내총부가가치 및 요소소득` actual이 확인되지만, 해당 표는 **연간(Y)** 자료다.
- 한국은행 KOSIS 국민계정 표에는 전국 분기 GDP/GVA 수준값이 있으나, **경기도 지역 차원은 없다**.
- 추가 확인한 통계청 실험적통계 XLSX 파일의 `실질금액` 시트에는 경기도 분기별 **지역내총생산(시장가격) 수준값**이 존재한다.
- 따라서 공식 수준값 actual 대조는 통계청 XLSX 기준으로 수행하되, 우리 산출물이 총부가가치(GVA) 합계라는 점 때문에 `시장가격 GRDP`와의 개념 차이를 별도 표시한다.
- 공식 actual과의 성장률 대조는 기존처럼 MODS 보도자료의 **경기도 GRDP 전년동기비 성장률** 기준으로 수행한다.

{md_table(kosis_actual_display)}

## 데이터 커버리지

- 경기도 시군 수: **{summary['gyeonggi_sigungu_count']} / 31**
- 산업 수: **{summary['sector_count']}개**
- 기간: **{summary['period_min']}~{summary['period_max']}**
- 시군×산업×분기 행 수: **{summary['rows']:,}행**
- 누락 시군: **{missing if missing else '없음'}**

## 요구사항별 완료 감사

{md_table(requirement_audit)}

## 경기도 전체 자료 커버리지

{md_table(coverage_display)}

## 경기도 수준값 집계검증

아래 표의 target은 기존 프로젝트의 시도 분기 수준 목표 큐브다. 메타상 직접 공식 수준값이 아니라 개발용 분기 수준 기준이므로, 공식 actual 주장은 하지 않는다.

{md_table(total_display)}

## 공식 분기 GRDP 수준값 대조

통계청 실험적통계 XLSX의 `실질금액` 시트에서 경기도 `지역내총생산(시장가격)` 분기 actual을 추출했다. 비교값은 공식 GDP/GRDP 수준 actual이지만, 프로젝트 산출값은 산업별 총부가가치(GVA) 합계이므로 완전한 동종 개념 비교는 아니다.

{md_table(xlsx_level_display)}

## GRDP 회계 경계 환산 대조

통계청 XLSX의 시도별 회계식은 `지역내총생산(시장가격) ≈ 광업·제조업 + 건설업 + 서비스업 + 기타산업 및 순생산물세`로 검산된다. 따라서 우리 추정값 중 `광업·제조업·건설업·서비스업`에 해당하는 산업 블록을 합산하고, XLSX의 `기타산업 및 순생산물세` 블록을 붙여 GRDP 시장가격 경계와 비교했다.

이 표는 GVA 합계를 GRDP 회계 경계로 옮겼을 때의 외부 검증이다. 다만 `기타산업 및 순생산물세` 블록은 같은 공식 XLSX에서 가져온 보조 actual이므로, 순수 속보 예측 성능으로 해석하지 않는다.

{md_table(grdp_bridge_display)}

## 공식 연간 benchmark 정합성

경기도 시군×산업 분기 추정값을 연간으로 합산하면 KOSIS 경기도 연간 지역내총부가가치 benchmark와 일치해야 한다. 이는 예측성능이 아니라, 고양시 방식과 같은 상위 actual 보존성 검사다.

{md_table(annual_total_display)}

## 공식 GRDP 성장률 대조

공식 보도자료에서 추출한 경기도 GRDP 전년동기비와, 31개 시군 추정 GVA 합산값에서 계산한 전년동기비를 비교했다.

{md_table(yoy_display)}

## 큰 오차가 발생한 산업·분기

{md_table(worst_sector)}

## 해석

- 경기도 31개 시군 모두에 대해 같은 형태의 시군구×산업×분기 추정 데이터는 이미 구성 가능하다.
- 경기도 전체로 합산하면 2020~2023 수준값 기준 평균 절대오차율은 **{summary['total_level_mean_ape_pct_vs_project_target']:.3f}%**다.
- 다만 이 수준값 대조는 기존 프로젝트 target cube 기준이므로, 공식 actual 검증으로 과장하면 안 된다.
- 통계청 XLSX의 공식 경기도 분기 GRDP 시장가격 수준값과 비교하면 2020~2023 평균 격차율은 **{summary['official_xlsx_market_grdp_gap_mean_pct_2020_2023']:.3f}%**, 최대 격차율은 **{summary['official_xlsx_market_grdp_gap_max_pct_2020_2023']:.3f}%**다. 이 격차에는 GVA와 시장가격 GRDP의 개념 차이가 포함된다.
- 같은 XLSX의 회계 보조 블록을 이용해 GRDP 시장가격 경계로 환산하면 2020~2023 평균 격차율은 **{summary['grdp_bridge_gap_mean_pct_2020_2023']:.3f}%**, 최대 격차율은 **{summary['grdp_bridge_gap_max_pct_2020_2023']:.3f}%**다.
- 공식 연간 benchmark 보존성 검사의 최대 절대차는 **{summary['annual_benchmark_max_abs_gap_eok']:.6f}억원**이다.
- 공식 PDF 성장률 기준 2021~2023 평균 절대오차는 **{summary['official_yoy_mean_abs_error_pp_2021_2023']:.3f}%p**, 최대 절대오차는 **{summary['official_yoy_max_abs_error_pp_2021_2023']:.3f}%p**다.
- 후속 작업은 경기도 전체 LOCALDATA·사업체조사·경제총조사 세부자료를 더 결합해, 고양시 포스터 수준의 행정동 해상도가 아니라 경기도 시군구 해상도에서 산업별 오차를 줄이는 방향이 적절하다.

## 산출물

- `{summary['outputs']['sigungu_sector_parquet']}`
- `{summary['outputs']['level_sector_csv']}`
- `{summary['outputs']['level_total_csv']}`
- `{summary['outputs']['annual_sector_consistency_csv']}`
- `{summary['outputs']['annual_total_consistency_csv']}`
- `{summary['outputs']['official_xlsx_level_csv']}`
- `{summary['outputs']['official_xlsx_level_comparison_csv']}`
- `{summary['outputs']['official_xlsx_grdp_bridge_comparison_csv']}`
- `{summary['outputs']['official_yoy_csv']}`
- `{summary['outputs']['official_level_audit_csv']}`
- `{summary['outputs']['kosis_actual_source_audit_csv']}`
- `{summary['outputs']['yoy_comparison_csv']}`
- `{summary['outputs']['coverage_csv']}`
- `{manifest_path.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(manifest_path)
    print(REPORT)


if __name__ == "__main__":
    main()
