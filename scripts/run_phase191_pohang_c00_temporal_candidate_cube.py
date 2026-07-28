from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_partial_statistics_phase42_gva import multiresolution
from run_partial_statistics_phase45_gva import common_proxy_audit


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase191_pohang_c00_temporal_candidate_cube"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase191_pohang_c00_temporal_candidate_cube.md"
RUN_ID = "partial_statistics_estimation_phase191_pohang_c00_temporal_candidate_cube"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def stamp(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    payload = out.head(100_000).to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp(df).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame, digits: int = 2, limit: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if limit is not None and len(view) > limit:
        view = view.head(limit).copy()
    for c in view.columns:
        if pd.api.types.is_float_dtype(view[c]):
            view[c] = view[c].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
        else:
            view[c] = view[c].map(lambda x: "" if pd.isna(x) else str(x))
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    if limit is not None and len(df) > limit:
        lines.append(f"\n_상위 {limit:,}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def c00_replacement_controls(base_controls: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    phase188 = DATA / "phase188_manufacturing_production_index_extension" / "phase188_pohang_c00_index_power_monthly_panel.csv"
    if not phase188.exists():
        raise FileNotFoundError(f"Run Phase188 first: {phase188}")
    c00 = pd.read_csv(phase188, encoding="utf-8-sig")
    replacement = c00[
        ["year", "quarter", "month", "period", "industrial_index_power_monthly_gva"]
    ].rename(columns={"industrial_index_power_monthly_gva": "estimated_city_parent_monthly_gva"})
    replacement["gva_parent_code"] = "C00"
    replacement["temporal_source"] = "경북 제조업 산업생산지수+포항 산업용 전력"
    qsrc = base_controls[base_controls["gva_parent_code"].eq("C00")][
        ["year", "quarter", "quarterly_parent_source"]
    ].drop_duplicates()
    replacement = replacement.merge(qsrc, on=["year", "quarter"], how="left")
    cols = [
        "year",
        "quarter",
        "month",
        "period",
        "gva_parent_code",
        "estimated_city_parent_monthly_gva",
        "temporal_source",
        "quarterly_parent_source",
    ]
    original = base_controls[base_controls["gva_parent_code"].eq("C00")][cols].copy()
    controls = pd.concat(
        [base_controls[~base_controls["gva_parent_code"].eq("C00")][cols], replacement[cols]],
        ignore_index=True,
    ).sort_values(["year", "quarter", "month", "gva_parent_code"])
    diff = original.merge(
        replacement[cols],
        on=["year", "quarter", "month", "period", "gva_parent_code", "quarterly_parent_source"],
        suffixes=("_old", "_new"),
    )
    diff["delta_gva_eok"] = (
        diff["estimated_city_parent_monthly_gva_new"] - diff["estimated_city_parent_monthly_gva_old"]
    ) / 100.0
    diff["old_gva_eok"] = diff["estimated_city_parent_monthly_gva_old"] / 100.0
    diff["new_gva_eok"] = diff["estimated_city_parent_monthly_gva_new"] / 100.0
    return controls, diff


def accounting_from_base(base: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    rows = []
    monthly = (
        base.groupby(["year", "month", "gva_parent_code"], as_index=False)["estimated_emd_group_monthly_gva"]
        .sum()
        .rename(columns={"estimated_emd_group_monthly_gva": "estimated_sum"})
    )
    target = controls[["year", "month", "gva_parent_code", "estimated_city_parent_monthly_gva"]]
    m = monthly.merge(target, on=["year", "month", "gva_parent_code"], how="left")
    err = m["estimated_sum"] - m["estimated_city_parent_monthly_gva"]
    rows.append(
        {
            "check": "읍면동·소분류→시·GVA상위 / 월",
            "cells": len(m),
            "max_abs_error": float(err.abs().max()),
            "mean_abs_error": float(err.abs().mean()),
        }
    )
    quarterly = (
        base.groupby(["year", "quarter", "gva_parent_code"], as_index=False)["estimated_emd_group_monthly_gva"]
        .sum()
        .rename(columns={"estimated_emd_group_monthly_gva": "estimated_sum"})
    )
    qtarget = (
        controls.groupby(["year", "quarter", "gva_parent_code"], as_index=False)["estimated_city_parent_monthly_gva"]
        .sum()
        .rename(columns={"estimated_city_parent_monthly_gva": "target_sum"})
    )
    q = quarterly.merge(qtarget, on=["year", "quarter", "gva_parent_code"], how="left")
    qerr = q["estimated_sum"] - q["target_sum"]
    rows.append(
        {
            "check": "월→분기 / GVA상위",
            "cells": len(q),
            "max_abs_error": float(qerr.abs().max()),
            "mean_abs_error": float(qerr.abs().mean()),
        }
    )
    return pd.DataFrame(rows)


def apply_c00_scale(old_base: pd.DataFrame, control_diff: pd.DataFrame) -> pd.DataFrame:
    new_base = old_base.copy()
    scale = control_diff[["year", "month", "gva_parent_code", "estimated_city_parent_monthly_gva_old", "estimated_city_parent_monthly_gva_new", "temporal_source_new"]].copy()
    scale["scale_factor"] = np.where(
        scale["estimated_city_parent_monthly_gva_old"].abs() > 0,
        scale["estimated_city_parent_monthly_gva_new"] / scale["estimated_city_parent_monthly_gva_old"],
        1.0,
    )
    idx = new_base["gva_parent_code"].eq("C00")
    scaled = new_base.loc[idx].merge(
        scale[["year", "month", "gva_parent_code", "estimated_city_parent_monthly_gva_new", "temporal_source_new", "scale_factor"]],
        on=["year", "month", "gva_parent_code"],
        how="left",
    )
    scaled["estimated_city_parent_monthly_gva"] = scaled["estimated_city_parent_monthly_gva_new"].fillna(
        scaled["estimated_city_parent_monthly_gva"]
    )
    scaled["temporal_source"] = scaled["temporal_source_new"].fillna(scaled["temporal_source"])
    scaled["estimated_city_group_monthly_gva"] = scaled["estimated_city_group_monthly_gva"] * scaled["scale_factor"].fillna(1.0)
    scaled["estimated_emd_group_monthly_gva"] = scaled["estimated_emd_group_monthly_gva"] * scaled["scale_factor"].fillna(1.0)
    for col in ["estimated_city_parent_monthly_gva_new", "temporal_source_new", "scale_factor"]:
        scaled = scaled.drop(columns=[col], errors="ignore")
    new_base = pd.concat([new_base.loc[~idx], scaled], ignore_index=True).sort_values(
        ["year", "month", "gva_parent_code", "division_code", "group_code", "emd_code"]
    )
    return new_base


def c00_downstream_compare(old_base: pd.DataFrame, new_base: pd.DataFrame) -> pd.DataFrame:
    keys = ["year", "quarter", "month", "period", "section_code", "division_code", "group_code", "emd_code", "emd_name"]
    old = old_base[old_base["gva_parent_code"].eq("C00")][keys + ["estimated_emd_group_monthly_gva"]].rename(
        columns={"estimated_emd_group_monthly_gva": "old_emd_group_monthly_gva"}
    )
    new = new_base[new_base["gva_parent_code"].eq("C00")][keys + ["estimated_emd_group_monthly_gva"]].rename(
        columns={"estimated_emd_group_monthly_gva": "new_emd_group_monthly_gva"}
    )
    m = old.merge(new, on=keys, how="inner")
    m["delta_eok"] = (m["new_emd_group_monthly_gva"] - m["old_emd_group_monthly_gva"]) / 100.0
    m["old_eok"] = m["old_emd_group_monthly_gva"] / 100.0
    m["new_eok"] = m["new_emd_group_monthly_gva"] / 100.0
    summary = (
        m.groupby(["year", "period"], as_index=False)
        .agg(
            c00_rows=("group_code", "size"),
            old_sum_eok=("old_eok", "sum"),
            new_sum_eok=("new_eok", "sum"),
            max_abs_cell_delta_eok=("delta_eok", lambda s: float(s.abs().max())),
            sum_abs_cell_delta_eok=("delta_eok", lambda s: float(s.abs().sum())),
        )
    )
    summary["city_delta_eok"] = summary["new_sum_eok"] - summary["old_sum_eok"]
    return summary


def write_report(control_diff: pd.DataFrame, accounting_checks: pd.DataFrame, downstream: pd.DataFrame, status: dict) -> None:
    annual = (
        control_diff.groupby("year", as_index=False)
        .agg(
            old_c00_gva_eok=("old_gva_eok", "sum"),
            new_c00_gva_eok=("new_gva_eok", "sum"),
            max_abs_month_delta_eok=("delta_gva_eok", lambda s: float(s.abs().max())),
            mean_abs_month_delta_eok=("delta_gva_eok", lambda s: float(s.abs().mean())),
        )
    )
    annual["annual_delta_eok"] = annual["new_c00_gva_eok"] - annual["old_c00_gva_eok"]
    top_months = control_diff.reindex(control_diff["delta_gva_eok"].abs().sort_values(ascending=False).index).head(12)
    downstream_year = (
        downstream.groupby("year", as_index=False)
        .agg(
            rows=("c00_rows", "sum"),
            old_sum_eok=("old_sum_eok", "sum"),
            new_sum_eok=("new_sum_eok", "sum"),
            max_abs_cell_delta_eok=("max_abs_cell_delta_eok", "max"),
            sum_abs_cell_delta_eok=("sum_abs_cell_delta_eok", "sum"),
            city_delta_eok=("city_delta_eok", "sum"),
        )
    )
    text = f"""# Phase191 포항 제조업 C00 월 경로 교체 후보

## 목적

Phase188에서 포항 제조업 월 통제값이 `분기 내 균등`으로 생성되어 있음을 확인했다. Phase191은 기존 최종 큐브를 직접 덮어쓰지 않고, **C00 제조업 월 경로만** `경북 제조업 산업생산지수 + 포항 산업용 전력량`으로 교체한 별도 후보 큐브를 만든다.

## 산출물

- 후보 읍면동×소분류×월 큐브: `data/processed/phase191_pohang_c00_temporal_candidate_cube/phase191_pohang_emd_group_monthly.parquet`
- 후보 다해상도 큐브: `data/processed/phase191_pohang_c00_temporal_candidate_cube/phase191_pohang_multiresolution_cube.parquet`
- 후보 월 통제값: `phase191_pohang_parent_monthly_controls.csv`

## C00 연간 총량 보존 및 월 경로 변화

단위: 억원. 연간 총량은 보존하고 월별 배분만 바꾼다.

{md_table(annual.rename(columns={
    "year": "연도",
    "old_c00_gva_eok": "기존 C00 연합계",
    "new_c00_gva_eok": "후보 C00 연합계",
    "max_abs_month_delta_eok": "최대 월 차이",
    "mean_abs_month_delta_eok": "평균 월 차이",
    "annual_delta_eok": "연간 총량 차이",
}), 4)}

## 월별 변화 상위

단위: 억원.

{md_table(top_months[["year","month","period","old_gva_eok","new_gva_eok","delta_gva_eok","temporal_source_new"]].rename(columns={
    "year": "연도",
    "month": "월",
    "period": "시점",
    "old_gva_eok": "기존 월 GVA",
    "new_gva_eok": "후보 월 GVA",
    "delta_gva_eok": "차이",
    "temporal_source_new": "후보 시간자료",
}), 2)}

## 회계 정합성 검증

{md_table(accounting_checks.rename(columns={
    "check": "검증",
    "cells": "셀수",
    "max_abs_error": "최대오차",
    "mean_abs_error": "평균오차",
}), 8)}

## 하위 읍면동·소분류 영향

{md_table(downstream_year.rename(columns={
    "year": "연도",
    "rows": "C00 하위행",
    "old_sum_eok": "기존 하위합계",
    "new_sum_eok": "후보 하위합계",
    "max_abs_cell_delta_eok": "최대 셀 차이",
    "sum_abs_cell_delta_eok": "셀 차이 절대합",
    "city_delta_eok": "시 합계 차이",
}), 4)}

## 판정

1. 이 후보는 중분류 금액오차를 줄이는 실험이 아니라, 포항 제조업 **월별 시간 해상도**를 개선하는 실험이다.
2. 분기·연간 제조업 총량은 보존된다. 따라서 상위 실제값과의 집계 정합성은 유지된다.
3. 기존 Phase45 최종 큐브는 보존했다. 운영 반영은 포스터/보고서 문구와 downstream 분석 의존성을 확인한 뒤 별도 단계에서 수행하는 것이 안전하다.

## 상태

```json
{json.dumps(status, ensure_ascii=False, indent=2)}
```
"""
    REPORT.write_text(text, encoding="utf-8")


def main() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    old_base = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_emd_small_monthly.parquet")
    base_controls = pd.read_csv(DATA / "partial_stats_phase42_pohang_parent_monthly_controls.csv", encoding="utf-8-sig")
    base_controls = base_controls[
        [
            "year",
            "quarter",
            "month",
            "period",
            "gva_parent_code",
            "estimated_city_parent_monthly_gva",
            "temporal_source",
            "quarterly_parent_source",
        ]
    ].copy()
    new_controls, control_diff = c00_replacement_controls(base_controls)
    new_base = apply_c00_scale(old_base, control_diff)
    multi = multiresolution(new_base)
    checks = accounting_from_base(new_base, new_controls)
    common = common_proxy_audit(new_base)
    downstream = c00_downstream_compare(old_base, new_base)

    new_base.to_parquet(OUT / "phase191_pohang_emd_group_monthly.parquet", index=False)
    multi.to_parquet(OUT / "phase191_pohang_multiresolution_cube.parquet", index=False)
    write_csv("phase191_pohang_parent_monthly_controls.csv", new_controls)
    write_csv("phase191_c00_monthly_control_diff.csv", control_diff)
    write_csv("phase191_accounting_checks.csv", checks)
    write_csv("phase191_common_proxy_audit.csv", common)
    write_csv("phase191_c00_downstream_change_summary.csv", downstream)
    status = {
        "phase": RUN_ID,
        "rows_emd_group_monthly": int(len(new_base)),
        "rows_multiresolution": int(len(multi)),
        "changed_parent": "C00",
        "new_temporal_source": "경북 제조업 산업생산지수+포항 산업용 전력",
        "accounting_max_abs_error": float(checks["max_abs_error"].max()),
        "annual_c00_delta_abs_max_eok": float(control_diff.groupby("year")["delta_gva_eok"].sum().abs().max()),
        "created_at": CREATED_AT,
    }
    (OUT / "phase191_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(control_diff, checks, downstream, status)
    print(REPORT)
    return status


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
