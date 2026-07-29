#!/usr/bin/env python3
"""Phase258: construction alternative-source readiness audit.

PPS remains blocked by API/rate limiting, so this audit reviews already
collected alternative public construction sources without adopting a new route.
It writes ignored CSV registries plus a tracked markdown report.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase258_construction_alt_source_readiness.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


FILES = {
    "buildinghub_feature_table": ROOT / "data" / "processed" / "buildinghub_feature_table.csv",
    "buildinghub_monthly_total_count": ROOT / "data" / "processed" / "buildinghub_monthly_total_count.csv",
    "buildinghub_request_manifest": ROOT / "data" / "processed" / "buildinghub_request_manifest.csv",
    "buildinghub_priority_top5_features": ROOT
    / "data"
    / "processed"
    / "phase239_construction_top5_buildinghub_guarded_grid"
    / "phase239_top5_buildinghub_annual_features.csv",
    "cals_contract_rows": ROOT / "data" / "processed" / "phase241_cals_construction_contract_rows.csv",
    "cals_contract_list": ROOT / "data" / "processed" / "phase241_cals_construction_list.csv",
    "lh_notice_rows": ROOT / "data" / "processed" / "phase243_lh_notice_rows_202101_202312.csv",
    "seoul_redevelopment_summary": ROOT / "data" / "processed" / "phase241_seoul_redevelopment_summary.csv",
    "phase244_candidate_summary": ROOT
    / "data"
    / "processed"
    / "phase244_construction_multi_source_activity_route"
    / "phase244_candidate_summary.csv",
    "phase244_guardrail_safe": ROOT
    / "data"
    / "processed"
    / "phase244_construction_multi_source_activity_route"
    / "phase244_guardrail_safe_candidates.csv",
    "phase245_policy_summary": ROOT
    / "data"
    / "processed"
    / "phase245_construction_rolling_gated_activity_route"
    / "phase245_policy_summary.csv",
    "phase246_lh_candidate_summary": ROOT
    / "data"
    / "processed"
    / "phase246_construction_lh_augmented_route"
    / "phase246_lh_candidate_summary.csv",
    "phase246_lh_guardrail_safe": ROOT
    / "data"
    / "processed"
    / "phase246_construction_lh_augmented_route"
    / "phase246_lh_guardrail_safe_candidates.csv",
    "construction_error_by_city": OUT / "construction_error_by_city.csv",
    "construction_error_top_cells": OUT / "construction_error_top_cells.csv",
}


def read_csv_fallback(path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:  # noqa: BLE001
            continue
    return pd.DataFrame()


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


def file_inventory() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for source_id, path in FILES.items():
        exists = path.exists()
        df = read_csv_fallback(path) if exists and path.suffix.lower() == ".csv" else pd.DataFrame()
        rows.append(
            {
                "source_id": source_id,
                "path": str(path.relative_to(ROOT)),
                "exists": exists,
                "rows": len(df) if exists and path.suffix.lower() == ".csv" else np.nan,
                "columns": len(df.columns) if exists and path.suffix.lower() == ".csv" else np.nan,
                "tracked_role": source_role(source_id),
            }
        )
    return pd.DataFrame(rows)


def source_role(source_id: str) -> str:
    if source_id.startswith("buildinghub"):
        return "민간건축 면적·건수 보조"
    if source_id.startswith("cals"):
        return "공공/SOC 공사 보조"
    if source_id.startswith("lh"):
        return "공공주택·토지 공고 이벤트"
    if "redevelopment" in source_id:
        return "서울 정비사업 단계·세대수"
    if source_id.startswith("phase"):
        return "기존 후보 route 검증 결과"
    return "건설업 오차 진단"


def period_summary(source_id: str, df: pd.DataFrame) -> dict[str, Any]:
    row: dict[str, Any] = {"source_id": source_id}
    if df.empty:
        return row
    for col in ["source_period", "period", "year", "observation_period", "request_month", "contract_year", "PAN_NT_ST_DT", "PAN_DT", "stwrDt", "ccwDt"]:
        if col not in df.columns:
            continue
        s = df[col].dropna().astype(str)
        if s.empty:
            continue
        if col == "contract_year":
            s = s.str.extract(r"(\d{4})", expand=False).dropna()
            if s.empty:
                continue
        row[f"{col}_min"] = s.min()
        row[f"{col}_max"] = s.max()
        row[f"{col}_nunique"] = s.nunique()
    for col in ["province_full", "city", "matched_province_full", "matched_city", "CNP_CD_NM"]:
        if col in df.columns:
            row[f"{col}_nunique"] = df[col].dropna().astype(str).replace("", np.nan).dropna().nunique()
    for col in ["actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct"]:
        if col in df.columns:
            row[col] = pd.to_numeric(df[col], errors="coerce").dropna().iloc[0] if not pd.to_numeric(df[col], errors="coerce").dropna().empty else np.nan
    return row


def source_coverage_summary() -> pd.DataFrame:
    rows = []
    for source_id, path in FILES.items():
        df = read_csv_fallback(path) if path.exists() and path.suffix.lower() == ".csv" else pd.DataFrame()
        x = period_summary(source_id, df)
        x["rows"] = len(df)
        rows.append(x)
    return pd.DataFrame(rows)


def candidate_performance() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    # Phase244 multi-source.
    p244 = read_csv_fallback(FILES["phase244_candidate_summary"])
    p244_safe = read_csv_fallback(FILES["phase244_guardrail_safe"])
    if not p244.empty:
        base = p244[p244["scenario"].astype(str).str.contains("baseline", case=False, na=False)]
        best = p244.sort_values("wape_pct").head(1)
        rows.append(performance_row("phase244_multi_source", base, best, p244_safe, "탐색 결과 일부 safe 후보 있으나 rolling 채택 전 단계"))
    # Phase245 rolling gated.
    p245 = read_csv_fallback(FILES["phase245_policy_summary"])
    if not p245.empty:
        base = p245[p245["policy"].eq("baseline_parent_control")]
        best = p245[p245["policy"].eq("rolling_city_gated")]
        rows.append(performance_row("phase245_rolling_city_gate", base, best, pd.DataFrame(), "rolling 적용 결과 기준보다 WAPE 악화"))
    # Phase246 LH.
    p246 = read_csv_fallback(FILES["phase246_lh_candidate_summary"])
    p246_safe = read_csv_fallback(FILES["phase246_lh_guardrail_safe"])
    if not p246.empty:
        base = p246[p246["scenario"].astype(str).str.contains("baseline", case=False, na=False)]
        best = p246.sort_values("wape_pct").head(1)
        rows.append(performance_row("phase246_lh_augmented", base, best, p246_safe, "LH 단독/미세혼합 safe 후보 없음"))
    return pd.DataFrame(rows)


def performance_row(name: str, base: pd.DataFrame, candidate: pd.DataFrame, safe: pd.DataFrame, note: str) -> dict[str, Any]:
    def get(df: pd.DataFrame, col: str) -> float:
        if df.empty or col not in df:
            return np.nan
        return float(pd.to_numeric(df[col], errors="coerce").iloc[0])

    base_wape = get(base, "wape_pct")
    cand_wape = get(candidate, "wape_pct")
    return {
        "experiment": name,
        "baseline_wape_pct": base_wape,
        "best_or_selected_wape_pct": cand_wape,
        "wape_delta_pp": cand_wape - base_wape if pd.notna(cand_wape) and pd.notna(base_wape) else np.nan,
        "baseline_over10_cells": get(base, "over10_cells"),
        "candidate_over10_cells": get(candidate, "over10_cells"),
        "baseline_max_ape_pct": get(base, "max_ape_pct"),
        "candidate_max_ape_pct": get(candidate, "max_ape_pct"),
        "safe_candidate_count": len(safe),
        "route_adoption": "not_adopted",
        "note": note,
    }


def readiness_registry() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source_block": "BuildingHUB 건축물 인허가·착공·사용승인",
                "coverage_label": "limited_priority_city_or_partial_historical",
                "signal_type": "면적·건수·용도별 이벤트",
                "best_use": "민간건축형 도시의 구조 진단 및 refinement 후보",
                "route_readiness": "diagnostic_only",
                "main_blocker": "전국 전기간 완전성·공표시점/vintage·금액형 자료 부족",
            },
            {
                "source_block": "CALS 공사목록/계약",
                "coverage_label": "public_soc_snapshot",
                "signal_type": "공공/SOC 공사 금액·기간 일부",
                "best_use": "도로·하천·토목형 지역 보조 신호",
                "route_readiness": "not_route_ready",
                "main_blocker": "민간건설 미포착, 전국 GVA 전체 대체 불가",
            },
            {
                "source_block": "LH 분양·임대 공고",
                "coverage_label": "2021_2023_notice_events",
                "signal_type": "공공주택·토지 공고건수",
                "best_use": "공공주택 이벤트 진단",
                "route_readiness": "rejected_by_guardrail",
                "main_blocker": "금액형 기성/투자액 부재, Phase246 safe 후보 0개",
            },
            {
                "source_block": "서울 도시정비사업",
                "coverage_label": "seoul_only_snapshot",
                "signal_type": "정비사업 단계·세대수",
                "best_use": "서울 재개발·재건축형 구 보조",
                "route_readiness": "local_only",
                "main_blocker": "전국 자료 아님, 서울 외 일반화 불가",
            },
            {
                "source_block": "PPS 공사공고/계약",
                "coverage_label": "partial_complete_months_or_api_blocked",
                "signal_type": "공공공사 예산·계약금액",
                "best_use": "공공·토목형 보조 신호",
                "route_readiness": "blocked_by_429_and_partial_coverage",
                "main_blocker": "Phase257 429, 완전월/완전연도 부족, 공공공사 편향",
            },
        ]
    )


def risk_register() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"risk": "snapshot_vintage_leakage", "description": "2026년 수집 snapshot을 과거 속보 route처럼 쓰는 위험", "mitigation": "retrieved_at/source_period 기준 분리, strict nowcast에서는 제외"},
            {"risk": "private_construction_undercoverage", "description": "PPS/CALS/LH가 민간 주거·상업·산업건축을 충분히 포착하지 못함", "mitigation": "민간건축형·공공토목형 지역유형 gate 사전 정의"},
            {"risk": "money_proxy_gap", "description": "BuildingHUB/LH/정비사업은 건수·면적·단계 중심으로 GVA 금액형 proxy가 약함", "mitigation": "금액형 계약/기성/착공예정액 확보 전 단독 route 금지"},
            {"risk": "spatial_attribution_error", "description": "기관명·공고명 텍스트 기반 지역귀속은 실제 공사 수행지와 다를 수 있음", "mitigation": "위치 필드 우선, confidence tier와 매칭률 gate 적용"},
            {"risk": "same_cell_selection_leakage", "description": "오차 큰 도시를 보고 후보를 붙인 뒤 같은 도시·연도에서 성능 주장", "mitigation": "discovery/holdout city 또는 out-of-year rolling 검증"},
        ]
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inventory = file_inventory()
    coverage = source_coverage_summary()
    perf = candidate_performance()
    readiness = readiness_registry()
    risks = risk_register()

    inventory.to_csv(OUT / "phase258_construction_alt_source_file_inventory.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(OUT / "phase258_construction_alt_source_coverage_summary.csv", index=False, encoding="utf-8-sig")
    perf.to_csv(OUT / "phase258_construction_alt_source_performance_registry.csv", index=False, encoding="utf-8-sig")
    readiness.to_csv(OUT / "phase258_construction_alt_source_readiness_registry.csv", index=False, encoding="utf-8-sig")
    risks.to_csv(OUT / "phase258_construction_alt_source_risk_register.csv", index=False, encoding="utf-8-sig")

    top_error = read_csv_fallback(FILES["construction_error_by_city"]).head(10)
    report = f"""# Phase258 건설업 대체 공개자료 자료준비도 감사

생성시각: {CREATED_AT}

## 1. 목적

Phase257 no-raw smoke에서도 PPS 공사계약·공사공고 API가 `HTTP 429`로 막혔다. 이번 감사는 이미 로컬에 수집된 BuildingHUB·CALS·LH·서울 정비사업·PPS 부분자료가 건설업 시군구 GVA 배분 개선에 어느 정도 준비되어 있는지 점검한다. 새 route를 채택하거나 성능개선을 주장하지 않는다.

## 2. 자료별 readiness 판정

{md_table(readiness, digits=2)}

## 3. 로컬 파일 인벤토리

{md_table(inventory[["source_id", "exists", "rows", "columns", "tracked_role"]], digits=0)}

## 4. coverage 요약

{md_table(coverage.fillna(""), digits=2)}

주의: CALS의 `ccwDt`·`ccwXpcDt` 계열에는 준공일 또는 준공예정일 성격의 미래 날짜가 포함될 수 있다. 따라서 coverage 표의 미래 최대일자는 수집시점 이후의 실제 관측기간 확장이 아니라 공사 예정·계획 기간 정보로 해석한다.

## 5. 기존 후보 실험 성능 레지스트리

{md_table(perf, digits=3)}

## 6. 건설업 잔여오차 상위 시군구

{md_table(top_error[["province_full", "city", "years", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct"]], digits=2)}

## 7. 누수·과잉주장 위험

{md_table(risks, digits=2)}

## 8. 운영 판정

1. BuildingHUB는 민간건축형 도시의 구조 진단에는 필요하지만, 현재 로컬 범위와 snapshot/vintage 한계 때문에 전국 2015~2025 건설업 route로 채택하지 않는다.
2. CALS와 PPS는 공공·토목형 보조 신호다. 민간 건설업 전체 GVA를 대표한다고 쓰면 안 된다.
3. LH는 2021~2023 공공주택·토지 공고 이벤트로 의미가 있지만, Phase246에서 guardrail safe 후보가 0개였으므로 단독 route로 채택하지 않는다.
4. 서울 도시정비사업은 서울 재개발·재건축형 구의 보조자료다. 전국 일반화 근거가 아니다.
5. 다음 성능개선은 자료별 단독 route가 아니라 지역유형 gate를 사전 고정한 뒤 `민간건축형(BuildingHUB)`, `공공·토목형(PPS/CALS)`, `공공주택형(LH)`, `정비사업형(지자체 정비사업)`을 분리해 rolling holdout으로 검증해야 한다.

## 9. route 승격 최소조건

- 2015~2025 또는 명시된 검증기간의 전월/전분기 completeness 통과.
- target-year actual을 보지 않은 사전 route·가중치·지역유형 gate 고정.
- 기준선 대비 WAPE 개선, 10% 초과 셀·20% 초과 셀·최대 APE·대형 actual 셀 절대오차 비악화.
- 공표시점 또는 최소 retrieved_at/source_period 기준 명시.
- 공공자료를 전체 민간+공공 건설업 GVA actual로 표현하지 않는 해석 제한.

## 10. 산출물

- `nationwide/outputs/phase258_construction_alt_source_file_inventory.csv`
- `nationwide/outputs/phase258_construction_alt_source_coverage_summary.csv`
- `nationwide/outputs/phase258_construction_alt_source_performance_registry.csv`
- `nationwide/outputs/phase258_construction_alt_source_readiness_registry.csv`
- `nationwide/outputs/phase258_construction_alt_source_risk_register.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(perf.to_string(index=False))


if __name__ == "__main__":
    main()
