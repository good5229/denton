from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase203_pohang_manufacturing_temporal_smoothing_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase203_pohang_manufacturing_temporal_smoothing_gate.md"
RUN_ID = "partial_statistics_estimation_phase203_pohang_manufacturing_temporal_smoothing_gate"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


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


def load_actual_shares() -> pd.DataFrame:
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


def predict(history: pd.DataFrame, target_year: int, model: str) -> pd.DataFrame:
    codes = sorted(history["middle_code"].unique())
    rows = []
    for code in codes:
        h = history[(history["middle_code"].eq(code)) & (history["year"] < target_year)].sort_values("year")
        if h.empty:
            continue
        vals = h["actual_share"].to_numpy()
        if model == "prev_year":
            pred = vals[-1]
        elif model == "mean_2y":
            pred = vals[-2:].mean()
        elif model == "mean_3y":
            pred = vals[-3:].mean()
        elif model == "median_3y":
            pred = float(np.median(vals[-3:]))
        elif model == "damped_trend_50":
            if len(vals) >= 2:
                pred = vals[-1] + 0.5 * (vals[-1] - vals[-2])
            else:
                pred = vals[-1]
        elif model == "anti_spike_mean3_for_volatile":
            if len(vals) >= 3 and np.std(vals[-3:]) > 0.025:
                pred = vals[-3:].mean()
            else:
                pred = vals[-1]
        else:
            raise ValueError(model)
        rows.append({"middle_code": code, "predicted_share_raw": max(pred, 0.0), "model": model})
    out = pd.DataFrame(rows)
    out["predicted_share"] = out["predicted_share_raw"] / out["predicted_share_raw"].sum()
    out["target_year"] = target_year
    return out[["target_year", "middle_code", "model", "predicted_share"]]


def evaluate(actual: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    x = actual.rename(columns={"year": "target_year"}).merge(pred, on=["target_year", "middle_code"], how="inner")
    x["actual_share_pct"] = x["actual_share"] * 100
    x["predicted_share_pct"] = x["predicted_share"] * 100
    x["share_error_pp"] = x["predicted_share_pct"] - x["actual_share_pct"]
    x["abs_share_error_pp"] = x["share_error_pp"].abs()
    x["actual_eok"] = x["actual"] / 100
    return x


def main() -> int:
    actual = load_actual_shares()
    models = [
        "prev_year",
        "mean_2y",
        "mean_3y",
        "median_3y",
        "damped_trend_50",
        "anti_spike_mean3_for_volatile",
    ]
    detail = pd.concat(
        [evaluate(actual, predict(actual, year, model)) for year in [2023, 2024] for model in models],
        ignore_index=True,
    )
    summary = (
        detail.groupby(["target_year", "model"], as_index=False)
        .agg(
            cells=("middle_code", "nunique"),
            actual_sum_eok=("actual_eok", "sum"),
            mae_share_pp=("abs_share_error_pp", "mean"),
            sum_abs_share_error_pp=("abs_share_error_pp", "sum"),
            gt5pp_cells=("abs_share_error_pp", lambda s: int((s > 5).sum())),
            gt10pp_cells=("abs_share_error_pp", lambda s: int((s > 10).sum())),
            max_abs_share_error_pp=("abs_share_error_pp", "max"),
        )
        .sort_values(["target_year", "sum_abs_share_error_pp", "model"])
    )
    train = summary[summary["target_year"].eq(2023)].copy()
    selected_model = train.iloc[0]["model"]
    eval_2024 = summary[
        summary["target_year"].eq(2024) & summary["model"].isin(["prev_year", selected_model])
    ].copy()
    eval_2024["selected_by_2023"] = eval_2024["model"].eq(selected_model)
    selected_detail = detail[(detail["target_year"].eq(2024)) & (detail["model"].eq(selected_model))].copy()
    worst = selected_detail.sort_values("abs_share_error_pp", ascending=False).head(10)
    path_panel = actual[actual["middle_code"].isin(["C24", "C25", "C28", "C23", "C34", "C20"])].copy()
    path_panel["actual_share_pct"] = path_panel["actual_share"] * 100
    path_panel["actual_eok"] = path_panel["actual"] / 100

    write_csv("phase203_temporal_smoothing_screen.csv", summary)
    write_csv("phase203_temporal_smoothing_detail.csv", detail)
    write_csv("phase203_selected_2024_eval.csv", eval_2024)
    write_csv("phase203_key_middle_actual_path.csv", path_panel)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase203 포항 제조업 중분류 시간 안정화 게이트

## 목적

포항 제조업 중분류는 2022~2023년에 C28 전기장비 비중이 급등했고 2024년에 다시 낮아졌다. 단순 전년 구성비 기준선은 이런 일시적 급등을 다음 해로 그대로 이월해 C28을 과대추정하고 C24 1차 금속을 과소추정한다.

이번 실험은 외부 자료를 추가로 억지 적용하지 않고, 공개 actual의 과거연도만 사용해 `전년 유지`, `2년 평균`, `3년 평균`, `3년 중앙값`, `추세연장`, `변동성 큰 업종만 3년 평균`을 비교했다.

## 핵심 업종 실제 경로

{md_table(path_panel[[
    "year",
    "middle_code",
    "middle_name",
    "actual_eok",
    "actual_share_pct",
]].rename(columns={
    "year": "연도",
    "middle_code": "KSIC",
    "middle_name": "업종명",
    "actual_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
}))}

## 후보별 검증

{md_table(summary.rename(columns={
    "target_year": "검증연도",
    "model": "후보",
    "cells": "중분류수",
    "actual_sum_eok": "actual 합계(억원)",
    "mae_share_pp": "평균 구성비 오차(%p)",
    "sum_abs_share_error_pp": "오차 합(%p)",
    "gt5pp_cells": "5%p 초과",
    "gt10pp_cells": "10%p 초과",
    "max_abs_share_error_pp": "최대 오차(%p)",
}))}

## 2023 선택 후 2024 외부검증

2023년 성능만 보고 선택한 후보는 `{selected_model}`이다.

{md_table(eval_2024.rename(columns={
    "target_year": "검증연도",
    "model": "후보",
    "cells": "중분류수",
    "actual_sum_eok": "actual 합계(억원)",
    "mae_share_pp": "평균 구성비 오차(%p)",
    "sum_abs_share_error_pp": "오차 합(%p)",
    "gt5pp_cells": "5%p 초과",
    "gt10pp_cells": "10%p 초과",
    "max_abs_share_error_pp": "최대 오차(%p)",
    "selected_by_2023": "2023 선택값",
}))}

## 2024 선택 후보 잔여 오차

{md_table(worst[[
    "middle_code",
    "middle_name",
    "actual_eok",
    "actual_share_pct",
    "predicted_share_pct",
    "abs_share_error_pp",
]].rename(columns={
    "middle_code": "KSIC",
    "middle_name": "업종명",
    "actual_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
    "predicted_share_pct": "추정 구성비(%)",
    "abs_share_error_pp": "구성비 오차(%p)",
}))}

## 판정

포항 제조업 중분류는 일시적 급등 업종을 그대로 이월하지 않는 안정화 게이트가 필요하다. 다만 2023년에 가장 좋은 후보가 2024에서도 가장 좋다는 보장은 없으므로, 운영 적용은 다음 규칙이 안전하다.

1. 기본은 `전년 구성비`를 유지한다.
2. 최근 3년 표준편차가 큰 중분류는 `3년 평균/중앙값` 후보를 함께 계산한다.
3. 후보가 2개 이상의 외부연도에서 기준선보다 안정적으로 낮은 오차를 보일 때만 채택한다.
4. C24/C25/C28은 시간 안정화만으로는 부족하므로 항만 품목 물동량과 대형공장 규모 지표를 결합한 블록 검증을 계속해야 한다.
""",
        encoding="utf-8",
    )
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
