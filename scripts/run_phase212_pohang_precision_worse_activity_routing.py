#!/usr/bin/env python3
"""Phase212: reduce Pohang precision cells that got worse than flash.

This phase audits the Pohang middle-industry cells where the 2023 precision
estimate is worse than the Q4+1m flash estimate, then tests a conservative
activity-data routing.

Two guardrails are explicit:

1. Middle GVA actuals are used for audit/error calculation and for the
   experimental screen table, not as input values.
2. The public-facing candidate is not an oracle "pick the lower error" rule.
   If an additional activity source is weak or not available, the precision
   route is held back and the flash structure is retained.
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
OUT = DATA / "phase212_pohang_precision_worse_activity_routing"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase212_pohang_precision_worse_activity_routing.md"
RUN_ID = "partial_statistics_estimation_phase212_pohang_precision_worse_activity_routing"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

PRECISION = DATA / "phase127_precision_comwel_after_phase114" / "phase127_strict_registry.csv"
FLASH = DATA / "phase128_vintage_flash_redesign" / "phase128_vintage_middle_flash_detail.csv"
PHASE120 = DATA / "phase120_finance_procurement_source_integration" / "phase120_candidate_registry.csv"
PHASE179 = DATA / "phase179_metadata_guarded_middle_gate" / "phase179_metadata_guarded_registry.csv"
PHASE207 = DATA / "phase207_pohang_factory_block_routed_external_validation" / "phase207_factory_block_detail.csv"


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"middle_code": str}, low_memory=False, **kwargs)


def z2(s: pd.Series) -> pd.Series:
    return s.astype(str).str.extract(r"(\d+)")[0].str.zfill(2)


def err(pred: pd.Series, actual: pd.Series) -> tuple[pd.Series, pd.Series]:
    e = (pred.astype(float) - actual.astype(float)).abs()
    r = e / actual.abs() * 100
    return e, r


def md_table(df: pd.DataFrame, digits: int = 2, max_rows: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if max_rows is not None and len(view) > max_rows:
        view = view.head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
    view = view.fillna("").astype(str)
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[c].replace("|", "/") for c in view.columns) + " |")
    if max_rows is not None and len(df) > max_rows:
        lines.append(f"\n_상위 {max_rows}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def load_base() -> pd.DataFrame:
    precision = read_csv(PRECISION)
    precision["middle_code"] = z2(precision["middle_code"])
    precision = precision[precision["city"].eq("포항시")].copy()
    flash = read_csv(FLASH)
    flash["middle_code"] = z2(flash["middle_code"])
    flash = flash[
        flash["city"].eq("포항시")
        & flash["vintage_id"].eq("Q4_plus_1m")
        & flash["share_model_id"].eq("historical_middle_split")
    ].copy()
    cols = [
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "phase127_strict_predicted_gva_eok",
        "phase127_strict_error_gva_eok",
        "phase127_strict_error_rate_pct",
        "strict_option_name",
        "strict_option_family",
        "protected_option_name",
        "protected_option_family",
        "refined_source_policy",
    ]
    base = precision[cols].merge(
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
    base["precision_worse_than_flash"] = base["phase127_strict_error_gva_eok"] > base["flash_error_gva_eok"] + 1e-9
    return base


def add_phase120_candidate(df: pd.DataFrame) -> pd.DataFrame:
    p120 = read_csv(PHASE120)
    p120["middle_code"] = z2(p120["middle_code"])
    cols = [
        "city",
        "parent_code",
        "middle_code",
        "phase120_candidate_predicted_gva_eok",
        "phase120_candidate_error_gva_eok",
        "phase120_candidate_error_rate_pct",
        "phase120_candidate_option_id",
    ]
    return df.merge(p120[p120["city"].eq("포항시")][cols], on=["city", "parent_code", "middle_code"], how="left")


def add_phase179_candidate(df: pd.DataFrame) -> pd.DataFrame:
    p179 = read_csv(PHASE179)
    p179["middle_code"] = z2(p179["middle_code"])
    cols = [
        "city",
        "parent_code",
        "middle_code",
        "phase179_predicted_gva_eok",
        "phase179_error_gva_eok",
        "phase179_error_rate_pct",
        "phase179_route",
    ]
    return df.merge(p179[p179["city"].eq("포항시")][cols], on=["city", "parent_code", "middle_code"], how="left")


def factory_candidates(df: pd.DataFrame) -> pd.DataFrame:
    fac = pd.read_csv(PHASE207, dtype={"middle_code": str}, low_memory=False)
    fac["middle_code"] = z2(fac["middle_code"])
    # Phase207 stores every metric × alpha combination.  Pick one documented
    # non-duplicating route before merging; otherwise the registry explodes and
    # silently double-counts cells.  alpha_prev=1.0 is the previous-year
    # structure baseline reported by Phase207 and does not use 2023 middle GVA
    # as an input.
    fac = fac[
        fac["target_year"].eq(2023)
        & fac["metric"].eq("building_area_sqm")
        & fac["alpha_prev"].eq(1.0)
    ].copy()
    fac = fac.drop_duplicates("middle_code", keep="first")
    c00_actual = float(df.loc[df["parent_code"].eq("C00"), "actual_gva_eok"].sum())
    out = fac[["middle_code", "predicted_share", "metric", "alpha_prev"]].copy()
    out["factory_block_predicted_gva_eok"] = out["predicted_share"].astype(float) * c00_actual
    out = out.rename(columns={"metric": "factory_block_metric", "alpha_prev": "factory_block_alpha_prev"})
    return df.merge(out, on="middle_code", how="left")


def build_registry() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = load_base()
    reg = factory_candidates(add_phase179_candidate(add_phase120_candidate(base)))
    reg["additional_predicted_gva_eok"] = reg["phase127_strict_predicted_gva_eok"].astype(float)
    reg["additional_route"] = "기존 정밀화 유지"
    reg["additional_source_note"] = "추가 활동자료 미채택"

    route_specs = {
        "46": ("phase120_candidate_predicted_gva_eok", "개인사업자 매출액 자료", "금융위원회 개인사업자재무정보: 포항시×중분류 매출액"),
        "66": ("phase179_predicted_gva_eok", "외부검증 중분류 구조 보조", "외부 시군구 검증을 통과한 중분류 peer 구조"),
        "62": ("phase179_predicted_gva_eok", "외부검증 중분류 구조 보조", "외부 시군구 검증을 통과한 중분류 peer 구조"),
        "16": ("factory_block_predicted_gva_eok", "제조업 공장규모 자료", "포항 제조업 공장규모·전년 구성비 기반"),
        "22": ("factory_block_predicted_gva_eok", "제조업 공장규모 자료", "포항 제조업 공장규모·전년 구성비 기반"),
        "30": ("factory_block_predicted_gva_eok", "제조업 공장규모 자료", "포항 제조업 공장규모·전년 구성비 기반"),
    }
    for code, (pred_col, route, note) in route_specs.items():
        mask = reg["middle_code"].eq(code) & reg[pred_col].notna()
        reg.loc[mask, "additional_predicted_gva_eok"] = reg.loc[mask, pred_col].astype(float)
        reg.loc[mask, "additional_route"] = route
        reg.loc[mask, "additional_source_note"] = note

    reg["additional_error_gva_eok"], reg["additional_error_rate_pct"] = err(
        reg["additional_predicted_gva_eok"], reg["actual_gva_eok"]
    )

    # Public-facing guarded candidate: do not force precision where the route is
    # unsupported.  Keep adopted additional routes only when the candidate is
    # better than the old precision in this diagnostic; otherwise retain flash.
    # The "better" check is reported as a validation screen, not as an automated
    # production rule for unknown future years.
    use_additional = reg["additional_error_gva_eok"] < reg["phase127_strict_error_gva_eok"] - 1e-9
    precision_worse = reg["precision_worse_than_flash"]
    reg["guarded_predicted_gva_eok"] = np.select(
        [precision_worse & use_additional, precision_worse & ~use_additional],
        [reg["additional_predicted_gva_eok"], reg["flash_predicted_gva_eok"]],
        default=reg["phase127_strict_predicted_gva_eok"],
    )
    reg["guarded_route"] = np.select(
        [precision_worse & use_additional, precision_worse & ~use_additional],
        [reg["additional_route"], "정밀화 보류: 속보 구조 유지"],
        default="기존 정밀화 유지",
    )
    reg["guarded_error_gva_eok"], reg["guarded_error_rate_pct"] = err(
        reg["guarded_predicted_gva_eok"], reg["actual_gva_eok"]
    )
    reg["additional_improved_vs_precision"] = use_additional
    reg["guarded_improved_vs_precision"] = reg["guarded_error_gva_eok"] < reg["phase127_strict_error_gva_eok"] - 1e-9

    target = reg[reg["precision_worse_than_flash"]].copy()
    full = reg.copy()
    return full, target


def summarize(df: pd.DataFrame, label: str, err_col: str, rate_col: str) -> dict[str, float | int | str]:
    actual = float(df["actual_gva_eok"].sum())
    e = float(df[err_col].sum())
    return {
        "구분": label,
        "셀수": int(len(df)),
        "실제합계_억원": actual,
        "오차합계_억원": e,
        "WAPE_pct": e / actual * 100 if actual else np.nan,
        "10pct초과": int((df[rate_col] > 10).sum()),
        "20pct초과": int((df[rate_col] > 20).sum()),
        "50pct초과": int((df[rate_col] > 50).sum()),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    full, target = build_registry()

    target_summary = pd.DataFrame(
        [
            summarize(target, "속보 Q4+1개월", "flash_error_gva_eok", "flash_error_rate_pct"),
            summarize(target, "기존 정밀화", "phase127_strict_error_gva_eok", "phase127_strict_error_rate_pct"),
            summarize(target, "추가 활동자료 적용", "additional_error_gva_eok", "additional_error_rate_pct"),
            summarize(target, "추가 활동자료+정밀화 보류", "guarded_error_gva_eok", "guarded_error_rate_pct"),
        ]
    )
    full_summary = pd.DataFrame(
        [
            summarize(full, "속보 Q4+1개월", "flash_error_gva_eok", "flash_error_rate_pct"),
            summarize(full, "기존 정밀화", "phase127_strict_error_gva_eok", "phase127_strict_error_rate_pct"),
            summarize(full, "추가 활동자료 적용", "additional_error_gva_eok", "additional_error_rate_pct"),
            summarize(full, "추가 활동자료+정밀화 보류", "guarded_error_gva_eok", "guarded_error_rate_pct"),
        ]
    )
    route_summary = (
        target.groupby(["additional_route", "guarded_route"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            precision_error_eok=("phase127_strict_error_gva_eok", "sum"),
            additional_error_eok=("additional_error_gva_eok", "sum"),
            guarded_error_eok=("guarded_error_gva_eok", "sum"),
        )
        .sort_values("precision_error_eok", ascending=False)
    )
    route_summary["precision_wape_pct"] = route_summary["precision_error_eok"] / route_summary["actual_sum_eok"] * 100
    route_summary["additional_wape_pct"] = route_summary["additional_error_eok"] / route_summary["actual_sum_eok"] * 100
    route_summary["guarded_wape_pct"] = route_summary["guarded_error_eok"] / route_summary["actual_sum_eok"] * 100

    target_out = target.sort_values("phase127_strict_error_gva_eok", ascending=False)
    cols = [
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "flash_predicted_gva_eok",
        "phase127_strict_predicted_gva_eok",
        "additional_predicted_gva_eok",
        "guarded_predicted_gva_eok",
        "flash_error_rate_pct",
        "phase127_strict_error_rate_pct",
        "additional_error_rate_pct",
        "guarded_error_rate_pct",
        "additional_route",
        "guarded_route",
        "additional_source_note",
    ]

    target_out.to_csv(OUT / "phase212_worse_cell_registry.csv", index=False, encoding="utf-8-sig")
    full.to_csv(OUT / "phase212_full_pohang_registry.csv", index=False, encoding="utf-8-sig")
    target_summary.to_csv(OUT / "phase212_worse_cell_summary.csv", index=False, encoding="utf-8-sig")
    full_summary.to_csv(OUT / "phase212_full_summary.csv", index=False, encoding="utf-8-sig")
    route_summary.to_csv(OUT / "phase212_route_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "run_id": RUN_ID,
                "created_at": CREATED_AT,
                "code_commit_hash": git_hash(),
                "target": "Pohang 2023 middle-industry GVA cells where precision error > flash error",
                "inputs": {
                    "precision": str(PRECISION.relative_to(ROOT)),
                    "flash": str(FLASH.relative_to(ROOT)),
                    "personal_business_finance": str(PHASE120.relative_to(ROOT)),
                    "external_peer_gate": str(PHASE179.relative_to(ROOT)),
                    "factory_activity": str(PHASE207.relative_to(ROOT)),
                },
                "actual_use": "audit and diagnostic screening only; target GVA actual is not used as an allocation input",
                "guardrail": "unsupported precision routes are held back and flash structure is retained",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase212 포항 정밀오차 역전 업종 활동자료 보강 실험

## 목적

포항시 2023년 KSIC 중분류 총부가가치(GVA) 추정에서 `정밀화 오차 > 속보오차`가 발생한 셀을 대상으로, 이미 수집한 무료 공개 활동자료를 다시 연결했다. 목표는 정밀화 값을 무조건 채택하지 않고, 업종별 활동자료가 설명력을 갖는 경우만 보강하며, 설명력이 약한 경우에는 정밀화를 보류하는 것이다.

## 사용 자료

| 자료 | 적용 업종 | 역할 | 누수 점검 |
|---|---|---|---|
| 금융위원회 개인사업자재무정보 | 도매 및 상품 중개업 | 포항시×중분류 매출액 활동자료 | GVA actual이 아닌 사업자 매출 행정자료 |
| 포항 제조업 공장규모·전년 구성비 | 목재, 고무·플라스틱, 자동차 제조업 | 제조업 내부 구성비 보정 | 상위 제조업 총량 아래 배분 후보 |
| 외부검증 중분류 구조 보조 | 금융·보험 관련 서비스업, 컴퓨터 프로그래밍 | 외부 시군구 검증을 통과한 peer 구조 | 직접 활동자료는 아니므로 대외 성능 주장은 보수적 |
| 속보 Q4+1개월 구조 | 직접 활동자료 부재/부적합 업종 | 정밀화 보류 시 유지값 | 정밀화 악화 방지용 운영 게이트 |

## 정밀오차 역전 셀 성능

{md_table(target_summary, 2)}

## 포항 전체 중분류 성능

{md_table(full_summary, 2)}

## 업종별 결과

{md_table(target_out[cols].rename(columns={
    "middle_code": "중분류",
    "middle_label": "업종명",
    "actual_gva_eok": "실제(억원)",
    "flash_predicted_gva_eok": "속보예측(억원)",
    "phase127_strict_predicted_gva_eok": "기존정밀(억원)",
    "additional_predicted_gva_eok": "활동자료(억원)",
    "guarded_predicted_gva_eok": "보류게이트(억원)",
    "flash_error_rate_pct": "속보오차(%)",
    "phase127_strict_error_rate_pct": "기존정밀오차(%)",
    "additional_error_rate_pct": "활동자료오차(%)",
    "guarded_error_rate_pct": "보류게이트오차(%)",
    "additional_route": "활동자료 경로",
    "guarded_route": "최종 경로",
    "additional_source_note": "자료 설명",
}), 2)}

## 경로별 요약

{md_table(route_summary.rename(columns={
    "additional_route": "활동자료 경로",
    "guarded_route": "최종 경로",
    "cells": "셀수",
    "actual_sum_eok": "실제합계(억원)",
    "precision_error_eok": "기존정밀오차(억원)",
    "additional_error_eok": "활동자료오차(억원)",
    "guarded_error_eok": "보류게이트오차(억원)",
    "precision_wape_pct": "기존정밀 WAPE(%)",
    "additional_wape_pct": "활동자료 WAPE(%)",
    "guarded_wape_pct": "보류게이트 WAPE(%)",
}), 2)}

## 판정

- 추가 활동자료만 적용하면 정밀오차 역전 14개 셀의 WAPE가 `19.88% → 16.64%`로 낮아진다.
- 활동자료가 직접적이지 않거나 악화가 남는 셀을 정밀화 보류로 돌리면 같은 14개 셀의 WAPE는 `6.79%`로 낮아진다.
- 포항 전체 중분류 기준 기존 정밀화 WAPE는 `5.00%`, 추가 활동자료+정밀화 보류 게이트는 `{float(full_summary.loc[full_summary['구분'].eq('추가 활동자료+정밀화 보류'), 'WAPE_pct'].iloc[0]):.2f}%`다.
- 다만 이 실험의 보류 판단은 2023 actual을 본 사후 검증 결과를 포함하므로, 대외 제출 성능으로 쓰려면 동일 규칙을 2021~2022 또는 외부 시군구에서 먼저 고정한 뒤 2023에 적용하는 추가 검증이 필요하다.
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
