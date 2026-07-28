from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase207_pohang_factory_block_routed_external_validation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase207_pohang_factory_block_routed_external_validation.md"
RUN_ID = "partial_statistics_estimation_phase207_pohang_factory_block_routed_external_validation"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

BLOCK_CODES = ["C23", "C24", "C25", "C28", "C29", "C34"]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def stamp(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    payload = out.to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp(df).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
        else:
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else str(x))
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    return "\n".join(lines)


def load_actual() -> pd.DataFrame:
    raw = read_csv(DATA / "expanded_manufacturing_sigungu_ksic.csv")
    x = raw[
        raw["metric"].eq("value_added")
        & raw["ksic_level"].eq("middle")
        & raw["c1_nm"].eq("포항시")
        & raw["c2_id"].astype(str).str.startswith("C")
    ].copy()
    x["actual"] = pd.to_numeric(x["value"], errors="coerce")
    x = x.dropna(subset=["actual"])
    x["year"] = x["prd_de"].astype(int)
    x["middle_code"] = x["c2_id"].astype(str)
    x["middle_name"] = x["c2_nm"].astype(str)
    x["actual_share"] = x["actual"] / x.groupby("year")["actual"].transform("sum")
    return x[["year", "middle_code", "middle_name", "actual", "actual_share"]]


def load_factory() -> pd.DataFrame:
    f = read_csv(DATA / "phase189_manufacturing_factory_metric_screen" / "phase189_factory_middle_metrics.csv")
    f = f[f["city"].eq("포항시") & f["middle_code"].isin(BLOCK_CODES)].copy()
    for col in ["factory_count", "employee_count", "manufacturing_area_sqm", "building_area_sqm", "land_area_sqm", "sqrt_employee_area"]:
        f[col] = pd.to_numeric(f[col], errors="coerce").fillna(0)
    return f


def predict(actual: pd.DataFrame, factory: pd.DataFrame, target_year: int, metric: str, alpha_prev: float) -> pd.DataFrame:
    cur_codes = actual[actual["year"].eq(target_year)][["middle_code", "middle_name"]].drop_duplicates()
    prev = actual[actual["year"].eq(target_year - 1)][["middle_code", "actual_share"]].rename(
        columns={"actual_share": "prev_share"}
    )
    x = cur_codes.merge(prev, on="middle_code", how="inner")
    x["is_block"] = x["middle_code"].isin(BLOCK_CODES)
    block_total = x.loc[x["is_block"], "prev_share"].sum()
    x = x.merge(factory[["middle_code", metric]], on="middle_code", how="left")
    x[metric] = x[metric].fillna(0)
    x["factory_share_within_block"] = 0.0
    fsum = x.loc[x["is_block"], metric].sum()
    if fsum > 0:
        x.loc[x["is_block"], "factory_share_within_block"] = x.loc[x["is_block"], metric] / fsum
    x["prev_share_within_block"] = 0.0
    if block_total > 0:
        x.loc[x["is_block"], "prev_share_within_block"] = x.loc[x["is_block"], "prev_share"] / block_total
    mixed_within = alpha_prev * x["prev_share_within_block"] + (1 - alpha_prev) * x["factory_share_within_block"]
    x["predicted_share"] = x["prev_share"]
    x.loc[x["is_block"], "predicted_share"] = block_total * mixed_within[x["is_block"]]
    x["predicted_share"] = x["predicted_share"] / x["predicted_share"].sum()
    x["target_year"] = target_year
    x["metric"] = metric
    x["alpha_prev"] = alpha_prev
    return x


def evaluate(actual: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    y = actual.rename(columns={"year": "target_year"}).merge(pred, on=["target_year", "middle_code"], how="inner")
    y["actual_share_pct"] = y["actual_share"] * 100
    y["predicted_share_pct"] = y["predicted_share"] * 100
    y["share_error_pp"] = y["predicted_share_pct"] - y["actual_share_pct"]
    y["abs_share_error_pp"] = y["share_error_pp"].abs()
    y["actual_eok"] = y["actual"] / 100
    return y


def main() -> int:
    actual = load_actual()
    factory = load_factory()
    metrics = ["factory_count", "employee_count", "manufacturing_area_sqm", "building_area_sqm", "land_area_sqm", "sqrt_employee_area"]
    alphas = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    detail = pd.concat(
        [evaluate(actual, predict(actual, factory, year, metric, alpha)) for year in [2023, 2024] for metric in metrics for alpha in alphas],
        ignore_index=True,
    )
    summary = (
        detail.groupby(["target_year", "metric", "alpha_prev"], as_index=False)
        .agg(
            cells=("middle_code", "nunique"),
            block_cells=("is_block", "sum"),
            actual_sum_eok=("actual_eok", "sum"),
            sum_abs_share_error_pp=("abs_share_error_pp", "sum"),
            mae_share_pp=("abs_share_error_pp", "mean"),
            max_abs_share_error_pp=("abs_share_error_pp", "max"),
            gt5pp_cells=("abs_share_error_pp", lambda s: int((s > 5).sum())),
            gt10pp_cells=("abs_share_error_pp", lambda s: int((s > 10).sum())),
        )
        .sort_values(["target_year", "sum_abs_share_error_pp"])
    )
    train = summary[summary["target_year"].eq(2023)].copy()
    selected = train.iloc[0]
    selected_metric = str(selected["metric"])
    selected_alpha = float(selected["alpha_prev"])
    eval_summary = summary[
        summary["target_year"].eq(2024)
        & (
            (summary["metric"].eq("factory_count") & summary["alpha_prev"].eq(1.0))
            | (summary["metric"].eq(selected_metric) & summary["alpha_prev"].eq(selected_alpha))
        )
    ].copy()
    eval_summary["selected_by_2023"] = eval_summary["metric"].eq(selected_metric) & eval_summary["alpha_prev"].eq(selected_alpha)
    selected_detail = detail[
        detail["target_year"].eq(2024) & detail["metric"].eq(selected_metric) & detail["alpha_prev"].eq(selected_alpha)
    ].copy()
    block_detail = selected_detail[selected_detail["is_block"]].sort_values("middle_code")
    worst = selected_detail.sort_values("abs_share_error_pp", ascending=False).head(10)

    fshow = factory.copy()
    for col in metrics:
        fshow[col + "_share_pct"] = fshow[col] / fshow[col].sum() * 100 if fshow[col].sum() else 0

    write_csv("phase207_factory_block_metric_source.csv", fshow)
    write_csv("phase207_factory_block_detail.csv", detail)
    write_csv("phase207_factory_block_summary.csv", summary)
    write_csv("phase207_2024_external_eval_summary.csv", eval_summary)
    write_csv("phase207_2024_selected_detail.csv", selected_detail)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase207 포항 제조업 공장규모 블록 제한 외부검증

## 목적

KICOX 공장등록필지정보 API는 여전히 403이지만, 로컬 전국 공장 스냅샷에는 포항 제조업 중분류별 종업원·제조시설면적·건축면적·용지면적이 있다. 이번 실험은 이 정밀화 자료를 전체 제조업에 무차별 적용하지 않고, 포항 잔여오차의 핵심인 C23/C24/C25/C28/C29/C34 블록 내부에만 제한 적용해 전년 구성비 기준선을 이기는지 확인한다.

## 공장규모 원천 신호

{md_table(fshow[[
    "middle_code",
    "factory_count",
    "employee_count",
    "manufacturing_area_sqm",
    "building_area_sqm",
    "land_area_sqm",
    "sqrt_employee_area",
    "manufacturing_area_sqm_share_pct",
    "employee_count_share_pct",
]].rename(columns={
    "middle_code": "KSIC",
    "factory_count": "공장수",
    "employee_count": "종업원수",
    "manufacturing_area_sqm": "제조시설면적",
    "building_area_sqm": "건축면적",
    "land_area_sqm": "용지면적",
    "sqrt_employee_area": "종업원×면적 결합",
    "manufacturing_area_sqm_share_pct": "제조시설면적 비중(%)",
    "employee_count_share_pct": "종업원 비중(%)",
}))}

## 검증 방식

- 기준선: 전년 중분류 구성비
- 후보: C23/C24/C25/C28/C29/C34 블록 내부에서만 `전년 구성비`와 `공장규모 신호`를 혼합
- 2023년 actual 구성비로 metric/혼합비 선택
- 2024년 외부검증

## 2023 선택 결과

| 선택 metric | 전년 구성비 혼합비 | 2023 오차 합(%p) |
|---|---:|---:|
| {selected_metric} | {selected_alpha:.3f} | {float(selected['sum_abs_share_error_pp']):.3f} |

## 2024 외부검증

{md_table(eval_summary.rename(columns={
    "target_year": "검증연도",
    "metric": "공장규모 신호",
    "alpha_prev": "전년 구성비 혼합비",
    "cells": "중분류수",
    "block_cells": "블록 중분류수",
    "actual_sum_eok": "actual 합계(억원)",
    "sum_abs_share_error_pp": "오차 합(%p)",
    "mae_share_pp": "평균오차(%p)",
    "max_abs_share_error_pp": "최대오차(%p)",
    "gt5pp_cells": "5%p 초과",
    "gt10pp_cells": "10%p 초과",
    "selected_by_2023": "2023 선택값",
}))}

## 2024 선택 후보 블록 상세

{md_table(block_detail[[
    "middle_code",
    "middle_name_x",
    "actual_eok",
    "actual_share_pct",
    "predicted_share_pct",
    "abs_share_error_pp",
]].rename(columns={
    "middle_code": "KSIC",
    "middle_name_x": "업종명",
    "actual_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
    "predicted_share_pct": "추정 구성비(%)",
    "abs_share_error_pp": "구성비 오차(%p)",
}))}

## 잔여 고오차

{md_table(worst[[
    "middle_code",
    "middle_name_x",
    "is_block",
    "actual_eok",
    "actual_share_pct",
    "predicted_share_pct",
    "abs_share_error_pp",
]].rename(columns={
    "middle_code": "KSIC",
    "middle_name_x": "업종명",
    "is_block": "블록대상",
    "actual_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
    "predicted_share_pct": "추정 구성비(%)",
    "abs_share_error_pp": "구성비 오차(%p)",
}))}

## 판정

공장규모 신호가 2023 선택과 2024 외부검증에서 기준선을 이기면, 포항 제조업 블록에 한해 정밀화 후보로 승격한다. 이기지 못하면 current snapshot 기반 면적·종업원은 연도별 충격을 설명하기 부족하므로, KICOX 필지정보 API 승인 또는 업종별 전력/대형공장 생산활동 자료가 필요하다.
""",
        encoding="utf-8",
    )
    print(f"selected metric={selected_metric}, alpha={selected_alpha}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
