#!/usr/bin/env python3
"""Phase117: push flash GVA errors below 20% where free sources exist.

This phase extends Phase116 with additional timing-audited free public sources
that were already collected locally:

* logistics warehouse permit histories for H52;
* Korail/metro station daily passengers up to the 2023-09-30 flash cut-off;
* 2015 agriculture/forestry/fishing detailed sales structure for A00;
* KEPCO same-year eligible electricity contract use through the cut-off.

The experiment remains a backtest.  Middle-industry actual GVA is never used as
an allocation input; it is used only for candidate screening and validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import run_phase115_flash_gt20_source_improvement as p115
import run_phase116_expanded_flash_gt20_improvement as p116


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase117_max_source_flash_push"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase117_max_source_flash_push.md"
CUTOFF = pd.Timestamp("2023-09-30")
CUTOFF_PERIOD = 202309


def read_any(path: Path, **kwargs: Any) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False, **kwargs)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("-", "", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0.0)


def add_indicator(rows: list[dict[str, Any]], city: str, parent: str, code: str, source_id: str, label: str, value: float, unit: str, note: str) -> None:
    if pd.notna(value) and np.isfinite(value) and value > 0:
        rows.append(
            {
                "city": city,
                "parent_code": parent,
                "middle_code": str(code).zfill(2),
                "source_id": source_id,
                "source_label": label,
                "indicator_raw_value": float(value),
                "indicator_value": float(np.log1p(value)),
                "allocation_value": float(value),
                "unit": unit,
                "timing_track": "속보성",
                "timing_note": note,
            }
        )


def add_logistics_warehouses(rows: list[dict[str, Any]]) -> None:
    """Add H52 warehouse activity from LOCALDATA logistics warehouse histories."""
    paths = {
        "고양시": RAW / "phase50_free_vulnerable_sources" / "localdata_logistics_warehouses_goyang.csv",
        "포항시": RAW / "phase50_free_vulnerable_sources" / "localdata_logistics_warehouses_pohang.csv",
    }
    for city, path in paths.items():
        if not path.exists():
            continue
        df = read_any(path)
        open_date = pd.to_datetime(df.get("인허가일자"), errors="coerce")
        close_date = pd.to_datetime(df.get("폐업일자"), errors="coerce")
        active = open_date.notna() & (open_date <= CUTOFF) & (close_date.isna() | (close_date > CUTOFF))
        area_cols = [c for c in ("일반창고면적", "냉동냉장창고면적", "보관장소면적", "시설총규모", "소재지면적") if c in df.columns]
        area = sum((numeric(df.loc[active, c]) for c in area_cols), start=pd.Series(0.0, index=df.loc[active].index))
        staff = numeric(df.loc[active, "직원수"]) if "직원수" in df.columns else pd.Series(0.0, index=df.loc[active].index)
        score = float(area.sum() + 100.0 * active.sum() + 10.0 * staff.sum())
        add_indicator(rows, city, "H00", "52", "flash_localdata_H52_logistics_warehouse_capacity", f"{city} 물류창고 영업면적·사업장", score, "복합점수", "인허가·폐업일 기준 2023-09-30 영업 창고 규모")


def add_rail_passengers(rows: list[dict[str, Any]]) -> None:
    path = DATA / "partial_stats_phase53_korail_station_daily_goyang_pohang.csv"
    if not path.exists():
        return
    df = read_any(path)
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    df["boarding"] = numeric(df.get("boarding", pd.Series(0, index=df.index)))
    df["alighting"] = numeric(df.get("alighting", pd.Series(0, index=df.index)))
    cut = df[df["date"].notna() & (df["date"] <= CUTOFF)].copy()
    for city, g in cut.groupby("city"):
        add_indicator(rows, city, "H00", "49", "flash_rail_passenger_ytd", f"{city} 철도 승하차 누적", float((g.boarding + g.alighting).sum()), "명", "2023-09-30까지 역별 일별 승하차 누적")


def add_agriculture_structure(rows: list[dict[str, Any]]) -> None:
    path = DATA / "partial_stats_phase49_agriculture_small_validation.csv"
    if not path.exists():
        return
    df = read_any(path)
    if df.empty:
        return
    code_map = {11: "01", 12: "01", 13: "01", 14: "01", 20: "02", 31: "03", 32: "03"}
    df["middle_code"] = pd.to_numeric(df.get("ksic_small_code"), errors="coerce").map(code_map)
    df = df[df["middle_code"].notna()].copy()
    val_col = "specialized_sales_share" if "specialized_sales_share" in df.columns else None
    if val_col is None:
        return
    for (city, middle), g in df.groupby(["city", "middle_code"]):
        add_indicator(rows, city, "A00", str(middle), "flash_agri_2015_small_sales_middle", "2015 농림어업 세부매출 중분류 집계", float(g[val_col].sum()), "비중", "2015 구조 벤치마크: 2023 속보시점 이전 이용 가능")


def add_electricity_contract(rows: list[dict[str, Any]]) -> None:
    """Add broad same-year electricity signals where they map to parent blocks.

    These are parent-block hints, not precise middle indicators, so they are
    intentionally weak candidates.  They help only if screening shows reduced
    parent-level distribution error without expanding >20% cells.
    """
    path = DATA / "kepco_sigungu_electricity_long.csv"
    if not path.exists():
        return
    df = read_any(path)
    df = df[df["sigungu_name"].isin(["고양시", "포항시"])].copy()
    df["first_eligible_period"] = pd.to_numeric(df.get("first_eligible_period"), errors="coerce")
    df["period"] = pd.to_numeric(df.get("period"), errors="coerce")
    df["value"] = numeric(df.get("value", pd.Series(0, index=df.index)))
    df = df[(df["period"].between(202301, 202309)) & (df["first_eligible_period"].le(CUTOFF_PERIOD))].copy()
    mapping = {
        "농사용": [("A00", "01"), ("A00", "02")],
        "산업용": [("C00", "10"), ("C00", "23"), ("C00", "29"), ("C00", "34")],
        "일반용": [("G00", "46"), ("G00", "47"), ("J00", "58"), ("J00", "61"), ("MN0", "71"), ("MN0", "75")],
        "교육용": [("MN0", "70")],
    }
    for (city, cat), g in df.groupby(["sigungu_name", "category_name"]):
        targets = mapping.get(str(cat), [])
        if not targets:
            continue
        val = float(g.value.sum()) / len(targets)
        for parent, middle in targets:
            add_indicator(rows, city, parent, middle, f"flash_kepco_contract_{cat}_ytd", f"{city} 전력사용량 {cat} 누적", val, "kWh", "공표시차 2개월 가정, 2023-09까지 중 2023-09-30 이전 공표분만 사용")


def add_mof_pohang_port_cargo(rows: list[dict[str, Any]]) -> None:
    """Add Pohang port cargo throughput from MOF statistics sharing API.

    The collected table is `DT_MLTM_1310 외내항 품목별 화물 입출항현황`.
    It is monthly and port/product-specific.  For flash use, keep a conservative
    two-month publication lag at the 2023-09-30 cut-off, so only 2023-01~2023-07
    observations are used.
    """
    path = RAW / "phase118_public_sources" / "mof_DT_MLTM_1310_pohang_all_products_latest60.csv"
    if not path.exists():
        return
    df = read_any(path)
    df["period"] = pd.to_numeric(df.get("PRD_DE"), errors="coerce")
    df["value"] = numeric(df.get("DT", pd.Series(0, index=df.index)))
    cut = df[df["period"].between(202301, 202307)].copy()
    if cut.empty:
        return

    total = float(cut.loc[cut.get("C2_NM").astype(str).eq("총계"), "value"].sum())
    add_indicator(
        rows,
        "포항시",
        "H00",
        "50",
        "flash_mof_pohang_port_cargo_total_ytd_lag2",
        "포항항 총 화물처리량 누적",
        total,
        "R/T",
        "해양수산통계 DT_MLTM_1310, 2023-01~07 누적; 2023-09-30 기준 2개월 공표시차 가정",
    )

    # Steel-related throughput is not a GVA actual.  It is only a physical
    # activity candidate for the C24/C25 steel-heavy manufacturing split.
    steel_products = {"철광석", "유연탄", "철강 및 그제품", "고 철", "비철금속 및 그제품"}
    steel = float(cut.loc[cut.get("C2_NM").astype(str).isin(steel_products), "value"].sum())
    for middle in ("24", "25"):
        add_indicator(
            rows,
            "포항시",
            "C00",
            middle,
            "flash_mof_pohang_steel_related_port_cargo_ytd_lag2",
            "포항항 철강 관련 화물처리량 누적",
            steel,
            "R/T",
            "해양수산통계 DT_MLTM_1310, 철광석·유연탄·철강제품 등 2023-01~07 누적",
        )


def build_indicators() -> pd.DataFrame:
    base = p116.build_indicators()
    rows = base.to_dict("records") if not base.empty else []
    add_logistics_warehouses(rows)
    add_rail_passengers(rows)
    add_agriculture_structure(rows)
    add_electricity_contract(rows)
    add_mof_pohang_port_cargo(rows)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    if "allocation_value" not in out.columns:
        out["allocation_value"] = out["indicator_raw_value"]
    raw_patterns = ("warehouse", "rail", "agri", "kepco", "value_added", "employees", "establishments", "building", "bus")
    raw_mask = out["source_id"].astype(str).map(lambda x: any(p in x for p in raw_patterns))
    out.loc[raw_mask, "allocation_value"] = out.loc[raw_mask, "indicator_raw_value"]
    return (
        out.groupby(["city", "parent_code", "middle_code", "source_id", "source_label", "unit", "timing_track", "timing_note"], as_index=False)
        .agg(indicator_raw_value=("indicator_raw_value", "sum"), indicator_value=("indicator_value", "sum"), allocation_value=("allocation_value", "sum"))
    )


def select(screen: pd.DataFrame) -> pd.DataFrame:
    if screen.empty:
        return screen
    # Stronger than Phase116: prioritize reducing the count of >20% cells, then
    # reduce total error.  This matches the current user target.
    s = screen[screen["adoptable"]].copy()
    if s.empty:
        return s
    s["gt20_reduction"] = s["baseline_gt20_cells"] - s["candidate_gt20_cells"]
    s["gt10_reduction"] = s["baseline_gt10_cells"] - s["candidate_gt10_cells"]
    selected = (
        s.sort_values(["city", "parent_code", "gt20_reduction", "error_reduction_eok", "gt10_reduction", "worsen_sum_eok"], ascending=[True, True, False, False, False, True])
        .groupby(["city", "parent_code"], as_index=False)
        .head(1)
        .sort_values(["gt20_reduction", "error_reduction_eok"], ascending=[False, False])
        .copy()
    )
    selected["public_claim_status"] = "속보 후보: 검증 통과"
    selected.loc[
        (selected["baseline_gt20_cells"].le(2)) & ((selected["error_reduction_eok"] / selected["baseline_error_eok"].replace(0, np.nan)) > 0.80),
        "public_claim_status",
    ] = "보류: 2셀 고적합 후보"
    selected.loc[selected["option_id"].astype(str).str.contains("2022|2023|2024", na=False), "public_claim_status"] = "보류: 공표시점 재확인 필요"
    return selected


def summarize(registry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in registry.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        old = float(g["flash_baseline_error_gva_eok"].sum())
        new = float(g["phase117_flash_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "baseline_flash_error_eok": old,
                "baseline_flash_wape_pct": old / actual * 100,
                "phase117_flash_error_eok": new,
                "phase117_flash_wape_pct": new / actual * 100,
                "error_reduction_eok": old - new,
                "wape_reduction_pp": (old - new) / actual * 100,
                "baseline_gt20_cells": int((g["flash_baseline_error_rate_pct"] > 20).sum()),
                "phase117_gt20_cells": int((g["phase117_flash_error_rate_pct"] > 20).sum()),
                "baseline_gt10_cells": int((g["flash_baseline_error_rate_pct"] > 10).sum()),
                "phase117_gt10_cells": int((g["phase117_flash_error_rate_pct"] > 10).sum()),
                "worsened_cells": int((g["phase117_flash_error_gva_eok"] > g["flash_baseline_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def source_gap_table(registry: pd.DataFrame) -> pd.DataFrame:
    gt = registry[registry["phase117_flash_error_rate_pct"].gt(20)].copy()
    def need(row: pd.Series) -> str:
        p = row.parent_code
        m = row.middle_code
        if p == "G00":
            return "도소매 중분류별 월 매출·사업자 과세매출·차량판매 등록"
        if p == "H00" and m == "50":
            return "포항항 월별 물동량 수집 완료; H49·H50·H52 혼합 배분모형 필요"
        if p == "J00":
            return "통신가입·콘텐츠매출·방송/정보서비스 매출 월지표"
        if p == "K00":
            return "금융기관 여수신·보험계약·중개수수료 지역 월지표"
        if p == "MN0":
            return "전문서비스 인력·임금·계약액·조달/용역 월지표"
        if p == "ERS":
            return "환경처리량·상하수도 처리량·문화시설 이용·단체 보조금"
        if p == "C00":
            return "중분류별 월 전력·공장가동·출하액·주요 사업장 생산량"
        if p == "A00":
            return "작물·임산물 생산량/출하액 월·분기 자료"
        return str(row.get("required_next_data", "중분류 직접 활동자료"))
    gt["phase117_required_data"] = gt.apply(need, axis=1)
    return gt.sort_values(["city", "phase117_flash_error_gva_eok"], ascending=[True, False])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = p115.load_base()
    indicators = build_indicators()
    screen, detail = p116.evaluate(base, indicators)
    selected = select(screen)
    registry = p115.apply(base, selected, detail).rename(
        columns={
            "phase115_flash_predicted_gva_eok": "phase117_flash_predicted_gva_eok",
            "phase115_flash_error_gva_eok": "phase117_flash_error_gva_eok",
            "phase115_flash_error_rate_pct": "phase117_flash_error_rate_pct",
            "phase115_option_id": "phase117_option_id",
            "phase115_flash_error_reduction_eok": "phase117_flash_error_reduction_eok",
        }
    )
    strict_selected = selected[~selected["public_claim_status"].astype(str).str.contains("보류", na=False)].copy()
    strict_registry = p115.apply(base, strict_selected, detail).rename(
        columns={
            "phase115_flash_predicted_gva_eok": "phase117_strict_flash_predicted_gva_eok",
            "phase115_flash_error_gva_eok": "phase117_strict_flash_error_gva_eok",
            "phase115_flash_error_rate_pct": "phase117_strict_flash_error_rate_pct",
            "phase115_option_id": "phase117_strict_option_id",
            "phase115_flash_error_reduction_eok": "phase117_strict_error_reduction_eok",
        }
    )
    summary = summarize(registry)
    strict_for_summary = strict_registry.rename(
        columns={
            "phase117_strict_flash_predicted_gva_eok": "phase117_flash_predicted_gva_eok",
            "phase117_strict_flash_error_gva_eok": "phase117_flash_error_gva_eok",
            "phase117_strict_flash_error_rate_pct": "phase117_flash_error_rate_pct",
            "phase117_strict_option_id": "phase117_option_id",
            "phase117_strict_error_reduction_eok": "phase117_flash_error_reduction_eok",
        }
    )
    strict_summary = summarize(strict_for_summary).rename(
        columns={
            "phase117_flash_error_eok": "phase117_strict_flash_error_eok",
            "phase117_flash_wape_pct": "phase117_strict_flash_wape_pct",
            "phase117_gt20_cells": "phase117_strict_gt20_cells",
            "phase117_gt10_cells": "phase117_strict_gt10_cells",
        }
    )
    gt20 = source_gap_table(registry)
    strict_gt20 = source_gap_table(strict_for_summary).rename(
        columns={
            "phase117_flash_predicted_gva_eok": "phase117_strict_flash_predicted_gva_eok",
            "phase117_flash_error_gva_eok": "phase117_strict_flash_error_gva_eok",
            "phase117_flash_error_rate_pct": "phase117_strict_flash_error_rate_pct",
            "phase117_option_id": "phase117_strict_option_id",
        }
    )
    improved = registry[registry["phase117_flash_error_reduction_eok"].gt(1e-9)].sort_values(["city", "phase117_flash_error_reduction_eok"], ascending=[True, False])
    worsened = registry[registry["phase117_flash_error_reduction_eok"].lt(-1e-9)].sort_values(["city", "phase117_flash_error_reduction_eok"])
    source_summary = (
        indicators.groupby(["city", "parent_code", "source_id", "source_label", "timing_note"], as_index=False)
        .agg(middle_cells=("middle_code", "nunique"), indicator_total=("allocation_value", "sum"))
        .sort_values(["city", "parent_code", "source_id"])
    )

    indicators.to_csv(OUT / "phase117_flash_indicators.csv", index=False, encoding="utf-8-sig")
    source_summary.to_csv(OUT / "phase117_source_summary.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(OUT / "phase117_candidate_screen.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase117_candidate_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase117_selected_options.csv", index=False, encoding="utf-8-sig")
    registry.to_csv(OUT / "phase117_flash_registry.csv", index=False, encoding="utf-8-sig")
    strict_registry.to_csv(OUT / "phase117_strict_flash_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase117_city_summary.csv", index=False, encoding="utf-8-sig")
    strict_summary.to_csv(OUT / "phase117_strict_city_summary.csv", index=False, encoding="utf-8-sig")
    gt20.to_csv(OUT / "phase117_remaining_gt20.csv", index=False, encoding="utf-8-sig")
    strict_gt20.to_csv(OUT / "phase117_strict_remaining_gt20.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUT / "phase117_improved_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUT / "phase117_worsened_cells.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase117 속보성 GVA 20% 초과 업종 최대 보강 실험

## 목적

고양시·포항시의 중분류 총부가가치(GVA) 속보 추정에서 오차율 20%를 넘는 셀을 줄이기 위해, 로컬에 이미 수집된 무료 공공자료 후보를 추가 적용했다. 예측식에는 중분류 실제 GVA를 넣지 않았고, 실제값은 후보 선택과 사후 검증에만 사용했다.

## 추가 활용자료

- 물류창고 인허가 이력: 창고·운송관련 서비스업(H52) 활동 규모 후보
- 철도·버스 승하차 누적: 육상운송업(H49) 활동 규모 후보
- 농림어업 2015 세부 매출 구조: 농업·임업·어업(A01~A03) 구조 후보
- KEPCO 전력사용량: 농사용·산업용·일반용·교육용 계약별 누적 후보
- 해양수산통계 포항항 월별 화물처리실적: 수상운송업(H50) 및 철강 물량형 제조업 후보
- 기존 Phase116 후보: 건축 인허가, LOCALDATA 영업재고, KOSIS 2021 이전 사업체·제조업 구조자료

## 도시별 성능

아래 표는 모든 검증통과 후보를 적용한 탐색 성능이다. 단, `보류` 후보는 입력 누수가 확인된 것은 아니지만 중분류 2개짜리 상위산업에서 고적합된 후보이므로 대외 성능 주장에는 제외하는 것이 안전하다.

{p115.md_table(summary, [("city", "지역"), ("actual_sum_eok", "실제합계 억원"), ("baseline_flash_error_eok", "기준 속보오차 억원"), ("baseline_flash_wape_pct", "기준 속보오차 %"), ("phase117_flash_error_eok", "Phase117 속보오차 억원"), ("phase117_flash_wape_pct", "Phase117 속보오차 %"), ("error_reduction_eok", "감소 억원"), ("wape_reduction_pp", "감소 pp"), ("baseline_gt20_cells", "기준 20%초과"), ("phase117_gt20_cells", "Phase117 20%초과"), ("baseline_gt10_cells", "기준 10%초과"), ("phase117_gt10_cells", "Phase117 10%초과"), ("worsened_cells", "악화 셀")])}

## 엄격 성능: 보류 후보 제외

{p115.md_table(strict_summary, [("city", "지역"), ("actual_sum_eok", "실제합계 억원"), ("baseline_flash_error_eok", "기준 속보오차 억원"), ("baseline_flash_wape_pct", "기준 속보오차 %"), ("phase117_strict_flash_error_eok", "엄격 속보오차 억원"), ("phase117_strict_flash_wape_pct", "엄격 속보오차 %"), ("error_reduction_eok", "감소 억원"), ("wape_reduction_pp", "감소 pp"), ("baseline_gt20_cells", "기준 20%초과"), ("phase117_strict_gt20_cells", "엄격 20%초과"), ("baseline_gt10_cells", "기준 10%초과"), ("phase117_strict_gt10_cells", "엄격 10%초과"), ("worsened_cells", "악화 셀")])}

## 채택된 상위산업별 후보

{p115.md_table(selected, [("city", "지역"), ("parent_code", "상위산업"), ("option_id", "선택 지표"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("public_claim_status", "판정")], 80)}

## 개선된 중분류

{p115.md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("flash_baseline_error_gva_eok", "기준오차 억원"), ("phase117_flash_error_gva_eok", "Phase117 오차 억원"), ("phase117_flash_error_rate_pct", "Phase117 오차 %"), ("phase117_flash_error_reduction_eok", "감소 억원"), ("phase117_option_id", "적용 지표")], 100)}

## 남은 20% 초과 중분류와 추가 필요자료

{p115.md_table(gt20, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase117_flash_predicted_gva_eok", "속보추정 억원"), ("phase117_flash_error_gva_eok", "오차 억원"), ("phase117_flash_error_rate_pct", "오차 %"), ("phase117_required_data", "20% 이하에 필요한 직접자료")], 140)}

## 추가 수집 결과와 남은 한계

| 자료 | 링크 | 결과 | 조치 |
| --- | --- | --- | --- |
| 해양수산부 품목별 화물처리실적 월별 API | https://www.data.go.kr/data/15056791/openapi.do | 승인 후 `DATA_GO_KR_ENCODING` 키로 정상 응답. 다만 `/SsopCargFrghtPrdlst2/YM`은 월×품목 전국합계로 항만코드가 없음 | 전국 월별 품목 계절성 보조자료로만 사용 |
| 해양수산통계 공유서비스 `DT_MLTM_1310 외내항 품목별 화물 입출항현황` | https://www.mof.go.kr/statPortal/api/idx/main.do | `MOF_API_KEY`로 포항항×품목×월 자료 수집 성공. `data/raw/phase118_public_sources/mof_DT_MLTM_1310_pohang_all_products_latest60.csv` 저장 | H50 단일지표는 기존 parent 단일후보 평가기에 바로 채택되지 않음. H49 여객·H50 항만·H52 창고를 각각 분리하는 혼합 배분모형이 다음 단계 |

## 판정

이번 단계는 무료 후보자료를 최대한 추가했지만, 두 도시의 모든 중분류를 20% 이내로 넣지는 못했다. 특히 도소매, 금융보험, 정보통신, 전문서비스, 환경·개인서비스는 사업체 수나 일반 전력 같은 간접 지표만으로는 중분류별 GVA 구조를 안정적으로 분리하기 어렵다. 이 업종들은 월별 매출·계약액·처리량·가입자·보조금처럼 중분류 활동에 직접 가까운 자료가 필요하다.

포항 수상운송업은 필요한 핵심 자료인 포항항 월별 물동량을 확보했지만, 현재 평가는 상위산업 내부를 하나의 지표로 재배분하는 방식이어서 H50 전용 지표가 H00 후보로 채택되지 않는다. 따라서 다음 실험은 H00을 육상운송(H49)·수상운송(H50)·창고/운송관련(H52)으로 나누고, 각각 철도/버스 승하차·항만 물동량·창고면적을 결합하는 혼합 배분식으로 전환해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
