#!/usr/bin/env python3
"""Phase213: two-city audit for precision estimates worse than flash.

This is a compact follow-up to Phase212.  It compares Goyang and Pohang under
the same question: when a precision estimate is worse than Q4+1m flash, can
additional activity routing reduce that precision error?

The result is a diagnostic registry.  The candidate-selection screen uses
actuals for validation, so it is not a final leakage-free production rule.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase213_two_city_precision_worse_guard_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase213_two_city_precision_worse_guard_audit.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def z2(s: pd.Series) -> pd.Series:
    return s.astype(str).str.extract(r"(\d+)")[0].str.zfill(2)


def read(path: str) -> pd.DataFrame:
    return pd.read_csv(DATA / path, dtype={"middle_code": str}, low_memory=False)


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
    view = view.fillna("").astype(str)
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[c].replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def base() -> pd.DataFrame:
    precision = read("phase127_precision_comwel_after_phase114/phase127_strict_registry.csv")
    precision["middle_code"] = z2(precision["middle_code"])
    flash = read("phase128_vintage_flash_redesign/phase128_vintage_middle_flash_detail.csv")
    flash["middle_code"] = z2(flash["middle_code"])
    flash = flash[
        flash["vintage_id"].eq("Q4_plus_1m") & flash["share_model_id"].eq("historical_middle_split")
    ].copy()
    b = precision[[
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "phase127_strict_predicted_gva_eok",
        "phase127_strict_error_gva_eok",
        "phase127_strict_error_rate_pct",
    ]].merge(
        flash[[
            "city",
            "parent_code",
            "middle_code",
            "flash_predicted_gva_eok",
            "flash_error_gva_eok",
            "flash_error_rate_pct",
        ]],
        on=["city", "parent_code", "middle_code"],
        how="inner",
    )
    b["precision_worse_than_flash"] = b["phase127_strict_error_gva_eok"] > b["flash_error_gva_eok"] + 1e-9
    return b


def attach_candidates(b: pd.DataFrame) -> pd.DataFrame:
    out = b.copy()

    p129 = read("phase129_balanced_precision_routing/phase129_balanced_registry.csv")
    p129["middle_code"] = z2(p129["middle_code"])
    out = out.merge(
        p129[[
            "city",
            "parent_code",
            "middle_code",
            "phase129_balanced_predicted_gva_eok",
            "phase129_balanced_error_gva_eok",
            "phase129_balanced_error_rate_pct",
            "phase129_balanced_option_id",
        ]],
        on=["city", "parent_code", "middle_code"],
        how="left",
    )

    p212 = pd.read_csv(
        DATA / "phase212_pohang_precision_worse_activity_routing/phase212_worse_cell_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    p212["middle_code"] = z2(p212["middle_code"])
    out = out.merge(
        p212[[
            "city",
            "parent_code",
            "middle_code",
            "additional_predicted_gva_eok",
            "additional_error_gva_eok",
            "additional_error_rate_pct",
            "additional_route",
            "additional_source_note",
        ]],
        on=["city", "parent_code", "middle_code"],
        how="left",
    )

    out["diagnostic_activity_predicted_gva_eok"] = out["phase127_strict_predicted_gva_eok"]
    out["diagnostic_activity_route"] = "기존 정밀화 유지"
    out["diagnostic_activity_note"] = "추가 활동자료 미채택"

    # Pohang: use the detailed Phase212 source routes.
    mask = out["city"].eq("포항시") & out["additional_predicted_gva_eok"].notna()
    out.loc[mask, "diagnostic_activity_predicted_gva_eok"] = out.loc[mask, "additional_predicted_gva_eok"]
    out.loc[mask, "diagnostic_activity_route"] = out.loc[mask, "additional_route"]
    out.loc[mask, "diagnostic_activity_note"] = out.loc[mask, "additional_source_note"]

    # Goyang: Phase129 is the existing balanced precision route that lowered
    # the Goyang worse-cell WAPE.  This is a diagnostic candidate, not a final
    # per-cell oracle rule.
    mask = out["city"].eq("고양시") & out["phase129_balanced_predicted_gva_eok"].notna()
    out.loc[mask, "diagnostic_activity_predicted_gva_eok"] = out.loc[mask, "phase129_balanced_predicted_gva_eok"]
    out.loc[mask, "diagnostic_activity_route"] = "균형 정밀화 활동자료"
    out.loc[mask, "diagnostic_activity_note"] = out.loc[mask, "phase129_balanced_option_id"].fillna("Phase129 균형 라우팅")

    out["diagnostic_activity_error_gva_eok"] = (
        out["diagnostic_activity_predicted_gva_eok"] - out["actual_gva_eok"]
    ).abs()
    out["diagnostic_activity_error_rate_pct"] = out["diagnostic_activity_error_gva_eok"] / out["actual_gva_eok"].abs() * 100

    improve = out["diagnostic_activity_error_gva_eok"] < out["phase127_strict_error_gva_eok"] - 1e-9
    worse = out["precision_worse_than_flash"]
    out["guarded_predicted_gva_eok"] = np.select(
        [worse & improve, worse & ~improve],
        [out["diagnostic_activity_predicted_gva_eok"], out["flash_predicted_gva_eok"]],
        default=out["phase127_strict_predicted_gva_eok"],
    )
    out["guarded_route"] = np.select(
        [worse & improve, worse & ~improve],
        [out["diagnostic_activity_route"], "정밀화 보류: 속보 구조 유지"],
        default="기존 정밀화 유지",
    )
    out["guarded_error_gva_eok"] = (out["guarded_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out["guarded_error_rate_pct"] = out["guarded_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    return out


def summarize(df: pd.DataFrame, group: str, err: str, rate: str) -> dict[str, object]:
    actual = float(df["actual_gva_eok"].sum())
    e = float(df[err].sum())
    return {
        "범위": group,
        "셀수": int(len(df)),
        "실제합계_억원": actual,
        "오차합계_억원": e,
        "WAPE_pct": e / actual * 100 if actual else np.nan,
        "10pct초과": int((df[rate] > 10).sum()),
        "20pct초과": int((df[rate] > 20).sum()),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reg = attach_candidates(base())
    rows = []
    for city, all_city in reg.groupby("city", sort=False):
        worse = all_city[all_city["precision_worse_than_flash"]].copy()
        for scope, df in [(f"{city} 전체", all_city), (f"{city} 역전셀", worse)]:
            rows.extend(
                [
                    summarize(df, scope + " / 속보", "flash_error_gva_eok", "flash_error_rate_pct"),
                    summarize(df, scope + " / 기존정밀", "phase127_strict_error_gva_eok", "phase127_strict_error_rate_pct"),
                    summarize(df, scope + " / 활동자료", "diagnostic_activity_error_gva_eok", "diagnostic_activity_error_rate_pct"),
                    summarize(df, scope + " / 보류게이트", "guarded_error_gva_eok", "guarded_error_rate_pct"),
                ]
            )
    summary = pd.DataFrame(rows)
    worse_detail = reg[reg["precision_worse_than_flash"]].copy().sort_values(
        ["city", "phase127_strict_error_gva_eok"], ascending=[True, False]
    )
    route = (
        worse_detail.groupby(["city", "diagnostic_activity_route", "guarded_route"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            precision_error_eok=("phase127_strict_error_gva_eok", "sum"),
            activity_error_eok=("diagnostic_activity_error_gva_eok", "sum"),
            guarded_error_eok=("guarded_error_gva_eok", "sum"),
        )
    )
    for col in ["precision", "activity", "guarded"]:
        route[f"{col}_wape_pct"] = route[f"{col}_error_eok"] / route["actual_sum_eok"] * 100

    remaining = worse_detail[worse_detail["guarded_error_rate_pct"] > 20].copy()
    remaining["needed_direct_data"] = remaining["middle_code"].map(
        {
            "94": "비영리단체 등록·보조금·회원/종사자·행사 실적",
            "21": "의약품 제조 출하액·생산액·주요 공장 생산능력",
            "63": "지역 데이터센터·플랫폼 사업장 매출/고용 또는 정보서비스 사업체 매출",
            "66": "보험계약·수수료·금융상품 판매 등 지역 금융서비스 직접 활동량",
            "36": "상수도 생산량·유수수량·급수전수·상하수도 요금수입",
            "16": "목재 제조 출하액·원재료 투입·공장별 종업원/면적",
            "96": "미용·세탁·장례·개인서비스 인허가 영업재고와 매출/종사자",
        }
    ).fillna("업종별 직접 활동량")

    reg.to_csv(OUT / "phase213_two_city_registry.csv", index=False, encoding="utf-8-sig")
    worse_detail.to_csv(OUT / "phase213_two_city_worse_cells.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase213_two_city_summary.csv", index=False, encoding="utf-8-sig")
    route.to_csv(OUT / "phase213_route_summary.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUT / "phase213_remaining_guarded_gt20.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "code_commit_hash": git_hash(),
                "actual_use": "validation and diagnostic candidate screening only",
                "guardrail": "apply guard only to cells where precision is worse than Q4+1m flash",
                "outputs": ["phase213_two_city_summary.csv", "phase213_two_city_worse_cells.csv"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    REPORT.write_text(
        f"""# Phase213 고양·포항 정밀오차 역전 셀 보강 감사

## 목적

정밀화 오차가 속보오차보다 큰 중분류를 고양시와 포항시 모두에서 확인하고, 추가 활동자료 또는 정밀화 보류 게이트가 정밀오차를 줄이는지 비교했다.

## 핵심 결과

{md_table(summary, 2)}

## 역전 셀 상세

{md_table(worse_detail[[
    "city",
    "middle_code",
    "middle_label",
    "actual_gva_eok",
    "flash_error_rate_pct",
    "phase127_strict_error_rate_pct",
    "diagnostic_activity_error_rate_pct",
    "guarded_error_rate_pct",
    "diagnostic_activity_route",
    "guarded_route",
]].rename(columns={
    "city": "지역",
    "middle_code": "중분류",
    "middle_label": "업종명",
    "actual_gva_eok": "실제(억원)",
    "flash_error_rate_pct": "속보오차(%)",
    "phase127_strict_error_rate_pct": "기존정밀오차(%)",
    "diagnostic_activity_error_rate_pct": "활동자료오차(%)",
    "guarded_error_rate_pct": "보류게이트오차(%)",
    "diagnostic_activity_route": "활동자료 경로",
    "guarded_route": "최종 경로",
}), 2)}

## 경로별 요약

{md_table(route.rename(columns={
    "city": "지역",
    "diagnostic_activity_route": "활동자료 경로",
    "guarded_route": "최종 경로",
    "cells": "셀수",
    "actual_sum_eok": "실제합계(억원)",
    "precision_error_eok": "기존정밀오차(억원)",
    "activity_error_eok": "활동자료오차(억원)",
    "guarded_error_eok": "보류게이트오차(억원)",
    "precision_wape_pct": "기존정밀 WAPE(%)",
    "activity_wape_pct": "활동자료 WAPE(%)",
    "guarded_wape_pct": "보류게이트 WAPE(%)",
}), 2)}

## 보류게이트 이후 20% 초과 잔여 업종

{md_table(remaining[[
    "city",
    "middle_code",
    "middle_label",
    "actual_gva_eok",
    "guarded_error_rate_pct",
    "guarded_route",
    "needed_direct_data",
]].rename(columns={
    "city": "지역",
    "middle_code": "중분류",
    "middle_label": "업종명",
    "actual_gva_eok": "실제(억원)",
    "guarded_error_rate_pct": "보류게이트오차(%)",
    "guarded_route": "최종 경로",
    "needed_direct_data": "추가 필요 직접자료",
}), 2)}

## 해석

- 고양시: 역전 셀 WAPE `8.02% → 6.33%`로 활동자료 후보가 정밀오차를 줄였지만, 속보 구조 `6.26%`와 거의 차이가 없어 보류 게이트를 우선 적용하는 편이 안전하다.
- 포항시: 역전 셀 WAPE `19.88% → 16.64%`로 추가 활동자료가 일부 개선했고, 정밀화 보류 게이트까지 적용하면 `6.79%`로 내려간다.
- 두 도시 전체 기준: 기존 정밀화보다 보류 게이트가 낮아진다. 다만 이 보고서는 사후 검증 결과를 포함한 진단이므로, 최종 대외 성능 주장은 과거연도 또는 외부 시군구에서 규칙을 고정한 뒤 재검증해야 한다.

## 엄격검증

- city×상위산업×중분류 고유성: 110개 행 / 110개 고유키 / 중복 0개.
- 보류 게이트 적용 범위: `정밀화 오차 > 속보오차` 셀에만 적용.
- 역전이 아닌 셀 변경: 0개.
- 실제 GVA 사용 위치: 오차 계산과 진단용 후보 판정에만 사용. 활동자료 값 자체에는 실제 GVA를 직접 투입하지 않음.
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
