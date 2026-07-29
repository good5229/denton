#!/usr/bin/env python3
"""Phase262: readiness audit for non-construction residual service sectors.

This is a source-readiness and route-boundary audit, not a route adoption.  It
combines the current nationwide residual bottleneck table with existing local
activity-source inventories and monthly KOSIS indicator coverage.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase262_service_residual_source_readiness.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

BOTTLENECKS = ROOT / "data" / "processed" / "phase236_active_goal_frontier_synthesis" / "phase236_remaining_sigungu_bottlenecks.csv"
BLOCK_COVERAGE = ROOT / "data" / "processed" / "phase184_local_activity_source_availability" / "phase184_block_source_coverage.csv"
SOURCE_MATRIX = ROOT / "data" / "processed" / "phase184_local_activity_source_availability" / "phase184_local_source_availability_matrix.csv"
MONTHLY_USE = ROOT / "data" / "processed" / "phase208_monthly_indicator_collection" / "phase208_monthly_indicator_gva_use_map.csv"
MONTHLY_SUMMARY = ROOT / "data" / "processed" / "phase208_monthly_indicator_collection" / "phase208_monthly_indicator_collection_summary.csv"

TARGET_ACTIVITIES = {
    "운수 및 창고업": "H00",
    "숙박 및 음식점업": "I00",
    "정보통신업": "J00",
    "사업서비스업": "MN0",
    "문화 및 기타서비스업": "ERS",
    "금융 및 보험업": "K00",
}

BLOCK_TO_ACTIVITY = {
    "H00": "운수 및 창고업",
    "I00": "숙박 및 음식점업",
    "J00": "정보통신업",
    "MN0": "사업서비스업",
    "ERS": "문화 및 기타서비스업",
    "K00": "금융 및 보험업",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:  # noqa: BLE001
            continue
    return pd.read_csv(path)


def md_table(df: pd.DataFrame, limit: int | None = None, digits: int = 3) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{float(v):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def source_matrix_target(matrix: pd.DataFrame) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame()
    rows = []
    for _, r in matrix.iterrows():
        blocks = str(r.get("blocks", ""))
        for block, activity in BLOCK_TO_ACTIVITY.items():
            matched = block in blocks or (block == "J00" and "J59" in blocks)
            if matched:
                rows.append(
                    {
                        "activity": activity,
                    "block": block,
                        "source_id": r.get("source_id", ""),
                        "rows": int(r.get("rows", 0) or 0),
                        "detected_spatial": r.get("detected_spatial", ""),
                        "detected_temporal": r.get("detected_temporal", ""),
                        "source_status": r.get("source_status", ""),
                        "original_scope_note": r.get("original_scope_note", ""),
                        "caveat": r.get("caveat", ""),
                    }
                )
    return pd.DataFrame(rows)


def monthly_target(monthly_use: pd.DataFrame, monthly_summary: pd.DataFrame) -> pd.DataFrame:
    if monthly_use.empty:
        return pd.DataFrame()
    x = monthly_use.copy()
    txt = (x["tbl_nm"].fillna("") + " " + x["use_in_gva"].fillna("") + " " + x["dimensions"].fillna("")).astype(str)
    masks = {
        "운수 및 창고업": txt.str.contains("서비스업|운수|창고", regex=True),
        "숙박 및 음식점업": txt.str.contains("서비스업|음식|숙박|소매", regex=True),
        "정보통신업": txt.str.contains("서비스업|정보|통신|온라인|콘텐츠", regex=True),
        "사업서비스업": txt.str.contains("서비스업|사업|기업규모", regex=True),
        "문화 및 기타서비스업": txt.str.contains("서비스업|문화|영화|특수분류", regex=True),
        "금융 및 보험업": txt.str.contains("서비스업|금융|보험", regex=True),
    }
    rows = []
    summary = monthly_summary[["dataset", "rows", "period_min", "period_max", "item_names", "dimension_unique_counts"]].copy() if not monthly_summary.empty else pd.DataFrame()
    for activity, mask in masks.items():
        sub = x[mask].copy()
        if summary.empty:
            sub["rows"] = 0
            sub["period_min"] = ""
            sub["period_max"] = ""
            sub["item_names"] = ""
        else:
            # dataset names contain table id in the local convention; use a
            # contains join rather than requiring exact normalized file names.
            add_rows = []
            for _, r in sub.iterrows():
                m = summary[summary["dataset"].astype(str).str.contains(str(r["tbl_id"]), regex=False)]
                d = r.to_dict()
                if not m.empty:
                    d.update(m.iloc[0].to_dict())
                add_rows.append(d)
            sub = pd.DataFrame(add_rows)
        for _, r in sub.iterrows():
            rows.append(
                {
                    "activity": activity,
                    "tbl_id": r.get("tbl_id", ""),
                    "tbl_nm": r.get("tbl_nm", ""),
                    "period": r.get("period", ""),
                    "collection_status": r.get("collection_status", ""),
                    "scope": r.get("scope", ""),
                    "rows": r.get("rows", 0),
                    "period_min": "" if pd.isna(r.get("period_min", "")) else str(r.get("period_min", "")),
                    "period_max": "" if pd.isna(r.get("period_max", "")) else str(r.get("period_max", "")),
                    "use_limit": r.get("use_in_gva", ""),
                }
            )
    return pd.DataFrame(rows).drop_duplicates()


def readiness_table(bottlenecks: pd.DataFrame, block_cov: pd.DataFrame, local_sources: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for activity, block in TARGET_ACTIVITIES.items():
        b = bottlenecks[bottlenecks["activity"].eq(activity)]
        cov = block_cov[block_cov["block"].eq(block)]
        local = local_sources[local_sources["activity"].eq(activity)]
        mon = monthly[monthly["activity"].eq(activity)]
        if b.empty:
            residual = {}
        else:
            residual = b.iloc[0].to_dict()
        local_rows = int(local["rows"].sum()) if not local.empty else 0
        local_sources_n = int(local["source_id"].nunique()) if not local.empty else 0
        monthly_sources_n = int(mon["tbl_id"].nunique()) if not mon.empty else 0
        route_class = "time_path_only"
        route_status = "not_route_ready"
        key_gap = "시군구 공간식별 직접 활동자료 부족"
        if activity == "운수 및 창고업":
            route_class = "sido_time_path_ok_sigungu_direct_partial"
            key_gap = "항만/버스/물류창고 등은 지역특화·부분자료이고 전국 시군구 금액형 물류활동 장기패널 부족"
        elif activity == "숙박 및 음식점업":
            route_class = "national_time_path_ok_sigungu_space_weak"
            key_gap = "음식점포함 소매지수는 시간경로용; 시군구 객실·가동률·음식점 매출/면적 장기패널 부족"
        elif activity == "정보통신업":
            route_class = "national_time_path_ok_content_subsector_sparse"
            key_gap = "KOBIS는 영화 일부 시간경로뿐이고 방송·통신·정보서비스 지역 매출/사업장 규모자료 부족"
        elif activity == "사업서비스업":
            route_class = "procurement_business_registry_partial"
            key_gap = "조달·개인사업자 구조는 부분자료; 전문인력·임금총액·용역계약 금액형 전국 패널 부족"
        elif activity == "문화 및 기타서비스업":
            route_class = "facility_event_partial"
            key_gap = "KOBIS·시설자료는 일부 세부업종만 설명; 협회·스포츠·개인서비스 활동량 부족"
        elif activity == "금융 및 보험업":
            route_class = "structure_only_money_activity_missing"
            key_gap = "금융회사/개인사업자 구조자료는 금액형 지역 영업활동 대체 불가"
        rows.append(
            {
                "activity": activity,
                "block": block,
                "wape_pct": residual.get("wape_pct", pd.NA),
                "abs_error_sum_eok": residual.get("abs_error_sum_eok", pd.NA),
                "over10_cells": residual.get("over10_cells", pd.NA),
                "over20_cells": residual.get("over20_cells", pd.NA),
                "local_candidate_sources": local_sources_n,
                "local_candidate_rows": local_rows,
                "monthly_indicator_sources": monthly_sources_n,
                "route_class": route_class,
                "route_status": route_status,
                "key_gap": key_gap,
            }
        )
    return pd.DataFrame(rows).sort_values(["wape_pct", "over20_cells"], ascending=[False, False])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bottlenecks = read_csv(BOTTLENECKS)
    block_cov = read_csv(BLOCK_COVERAGE)
    matrix = read_csv(SOURCE_MATRIX)
    monthly_use = read_csv(MONTHLY_USE)
    monthly_summary = read_csv(MONTHLY_SUMMARY)
    local_sources = source_matrix_target(matrix)
    monthly_sources = monthly_target(monthly_use, monthly_summary)
    readiness = readiness_table(bottlenecks, block_cov, local_sources, monthly_sources)

    readiness.to_csv(OUT / "phase262_service_residual_readiness_summary.csv", index=False, encoding="utf-8-sig")
    local_sources.to_csv(OUT / "phase262_service_residual_local_sources.csv", index=False, encoding="utf-8-sig")
    monthly_sources.to_csv(OUT / "phase262_service_residual_monthly_indicators.csv", index=False, encoding="utf-8-sig")

    top_local = local_sources.sort_values(["activity", "rows"], ascending=[True, False])
    top_monthly = monthly_sources.sort_values(["activity", "rows"], ascending=[True, False])

    report = f"""# Phase262 비건설 잔여 서비스업 자료준비도 감사

생성시각: {CREATED_AT}

## 1. 목적

건설업 다음의 잔여 병목인 운수·창고업, 숙박·음식점업, 정보통신업 및 관련 서비스 업종군에 대해 현재 로컬 자료가 전국 시군구 route로 쓸 수 있는지 점검한다. 이 문서는 route 채택이 아니라 수집·검증 우선순위 감사다.

## 2. 업종별 readiness 요약

{md_table(readiness, digits=3)}

## 3. 로컬 후보자료

{md_table(top_local[["activity", "block", "source_id", "rows", "detected_spatial", "detected_temporal", "source_status", "original_scope_note", "caveat"]], limit=30, digits=0)}

## 4. 월별 지표 후보

{md_table(top_monthly[["activity", "tbl_id", "tbl_nm", "period", "collection_status", "scope", "rows", "period_min", "period_max", "use_limit"]], limit=36, digits=0)}

## 5. 판정

1. 운수·창고업은 시도·업종 시간경로에서는 이미 유의미한 route 후보가 있지만, 시군구 공간배분에는 전국 장기 금액형 물류활동 자료가 부족하다. 항만 물동량·경기버스·물류창고 자료는 지역특화 또는 부분자료로 gate가 필요하다.
2. 숙박·음식점업은 전국 월별 서비스·음식점 관련 지수로 시간경로를 만들 수 있지만, 시군구 공간구조는 객실수·가동률·음식점 매출·면적·종사자 장기패널이 있어야 한다.
3. 정보통신업은 KOBIS가 영화 세부 시간경로에는 쓸 수 있으나 방송·통신·정보서비스 전체 GVA를 대표하지 않는다. 방송사업자 매출, 통신/우편 물량, 데이터센터·콘텐츠 사업장 규모자료가 필요하다.
4. 사업서비스·문화기타·금융보험은 로컬 후보가 있으나 대부분 구조 또는 일부 세부업종 신호다. 금액형 지역 활동량이 없으면 시군구 route 채택이 아니라 진단/정밀화 후보로만 유지한다.
5. 현재 월별 KOSIS 지표는 대부분 `2020=100` 현재 스냅샷이다. 월별 시간경로에는 쓰되, 속보성 주장에는 공표시점 ledger가 필요하고 시군구 공간배분 근거로 쓰면 안 된다.

## 6. 다음 수집 우선순위

| 우선순위 | 업종 | 필요한 공개자료 | 이유 |
| --- | --- | --- | --- |
| 1 | 운수·창고업 | 전국 항만 품목별 물동량 장기패널, 물류창고 면적·업종, 버스/철도/여객·화물 지역 실적 | 시도 시간경로는 가능하나 시군구 공간오차가 많음 |
| 2 | 숙박·음식점업 | 시군구 숙박 객실·가동률, 관광숙박업 매출/객실, 음식점 인허가 면적·영업상태·종사자 | 전국 지수는 시간경로 전용이라 공간배분 부족 |
| 3 | 정보통신업 | 방송사업자 지역 매출, 통신/우편 물량, 콘텐츠 제작/유통 매출, 데이터센터·플랫폼 사업장 규모 | KOBIS만으로 J00 전체 설명 불가 |
| 4 | 사업서비스업 | 전문인력·임금총액·용역/조달 계약금액, 사업지원 사업장 규모 | 조달·개인사업자 구조만으로는 금액형 활동 부족 |
| 5 | 금융보험업 | 지역별 예수금·대출·보험료·계약건수·판매수수료 | 지점/사업자 구조보다 금액형 영업활동이 필요 |

## 7. 산출물

- `nationwide/outputs/phase262_service_residual_readiness_summary.csv`
- `nationwide/outputs/phase262_service_residual_local_sources.csv`
- `nationwide/outputs/phase262_service_residual_monthly_indicators.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(readiness.to_string(index=False))


if __name__ == "__main__":
    main()
