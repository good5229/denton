from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase204_pohang_manufacturing_prevalidated_volatility_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase204_pohang_manufacturing_prevalidated_volatility_gate.md"
RUN_ID = "partial_statistics_estimation_phase204_pohang_manufacturing_prevalidated_volatility_gate"
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


def smooth_value(vals: np.ndarray, method: str) -> float:
    if method == "prev":
        return float(vals[-1])
    if method == "mean2":
        return float(vals[-2:].mean())
    if method == "mean3":
        return float(vals[-3:].mean())
    if method == "median3":
        return float(np.median(vals[-3:]))
    if method == "cap_change_2pp":
        if len(vals) < 2:
            return float(vals[-1])
        delta = np.clip(vals[-1] - vals[-2], -0.02, 0.02)
        return float(vals[-1] + delta)
    if method == "cap_change_5pp":
        if len(vals) < 2:
            return float(vals[-1])
        delta = np.clip(vals[-1] - vals[-2], -0.05, 0.05)
        return float(vals[-1] + delta)
    raise ValueError(method)


def predict(actual: pd.DataFrame, target_year: int, gate_threshold_pp: float, volatile_method: str) -> pd.DataFrame:
    rows = []
    for code, group in actual[actual["year"] < target_year].groupby("middle_code"):
        h = group.sort_values("year")
        vals = h["actual_share"].to_numpy()
        if len(vals) == 0:
            continue
        window = vals[-3:] if len(vals) >= 3 else vals[-2:]
        vol_pp = float(np.std(window) * 100)
        is_volatile = vol_pp >= gate_threshold_pp
        pred = smooth_value(vals, volatile_method if is_volatile else "prev")
        rows.append(
            {
                "target_year": target_year,
                "middle_code": code,
                "gate_threshold_pp": gate_threshold_pp,
                "volatile_method": volatile_method,
                "history_volatility_pp": vol_pp,
                "is_volatile": is_volatile,
                "predicted_share_raw": max(pred, 0.0),
            }
        )
    out = pd.DataFrame(rows)
    out["predicted_share"] = out["predicted_share_raw"] / out["predicted_share_raw"].sum()
    return out


def evaluate(actual: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    x = actual.rename(columns={"year": "target_year"}).merge(pred, on=["target_year", "middle_code"], how="inner")
    x["actual_share_pct"] = x["actual_share"] * 100
    x["predicted_share_pct"] = x["predicted_share"] * 100
    x["share_error_pp"] = x["predicted_share_pct"] - x["actual_share_pct"]
    x["abs_share_error_pp"] = x["share_error_pp"].abs()
    x["actual_eok"] = x["actual"] / 100
    return x


def main() -> int:
    actual = load_actual()
    thresholds = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0]
    methods = ["mean2", "mean3", "median3", "cap_change_2pp", "cap_change_5pp"]
    rows = []
    for year in [2022, 2023, 2024]:
        for th in thresholds:
            for method in methods:
                rows.append(evaluate(actual, predict(actual, year, th, method)))
    detail = pd.concat(rows, ignore_index=True)
    summary = (
        detail.groupby(["target_year", "gate_threshold_pp", "volatile_method"], as_index=False)
        .agg(
            cells=("middle_code", "nunique"),
            volatile_cells=("is_volatile", "sum"),
            actual_sum_eok=("actual_eok", "sum"),
            sum_abs_share_error_pp=("abs_share_error_pp", "sum"),
            mae_share_pp=("abs_share_error_pp", "mean"),
            max_abs_share_error_pp=("abs_share_error_pp", "max"),
            gt5pp_cells=("abs_share_error_pp", lambda s: int((s > 5).sum())),
            gt10pp_cells=("abs_share_error_pp", lambda s: int((s > 10).sum())),
        )
        .sort_values(["target_year", "sum_abs_share_error_pp"])
    )
    train = summary[summary["target_year"].isin([2022, 2023])].copy()
    train_agg = (
        train.groupby(["gate_threshold_pp", "volatile_method"], as_index=False)
        .agg(
            train_years=("target_year", "nunique"),
            train_error_sum_pp=("sum_abs_share_error_pp", "sum"),
            train_mae_pp=("mae_share_pp", "mean"),
            train_max_pp=("max_abs_share_error_pp", "max"),
            train_gt5_cells=("gt5pp_cells", "sum"),
            train_gt10_cells=("gt10pp_cells", "sum"),
        )
        .sort_values(["train_error_sum_pp", "train_max_pp", "gate_threshold_pp", "volatile_method"])
    )
    selected = train_agg.iloc[0].to_dict()
    selected_th = float(selected["gate_threshold_pp"])
    selected_method = str(selected["volatile_method"])

    baseline_detail = evaluate(actual, predict(actual, 2024, 999.0, "mean3"))
    baseline_detail["gate_threshold_pp"] = 999.0
    baseline_detail["volatile_method"] = "baseline_prev_year"
    selected_detail = evaluate(actual, predict(actual, 2024, selected_th, selected_method))
    selected_detail["volatile_method_selected"] = selected_method
    eval_detail = pd.concat([baseline_detail, selected_detail], ignore_index=True)
    eval_summary = (
        eval_detail.groupby(["target_year", "gate_threshold_pp", "volatile_method"], as_index=False)
        .agg(
            cells=("middle_code", "nunique"),
            volatile_cells=("is_volatile", "sum"),
            actual_sum_eok=("actual_eok", "sum"),
            sum_abs_share_error_pp=("abs_share_error_pp", "sum"),
            mae_share_pp=("abs_share_error_pp", "mean"),
            max_abs_share_error_pp=("abs_share_error_pp", "max"),
            gt5pp_cells=("abs_share_error_pp", lambda s: int((s > 5).sum())),
            gt10pp_cells=("abs_share_error_pp", lambda s: int((s > 10).sum())),
        )
        .sort_values("sum_abs_share_error_pp")
    )
    worst = selected_detail.sort_values("abs_share_error_pp", ascending=False).head(10)
    changed = selected_detail[selected_detail["is_volatile"]].sort_values("history_volatility_pp", ascending=False)

    write_csv("phase204_volatility_gate_detail.csv", detail)
    write_csv("phase204_volatility_gate_summary.csv", summary)
    write_csv("phase204_train_selection_grid.csv", train_agg)
    write_csv("phase204_2024_external_eval_summary.csv", eval_summary)
    write_csv("phase204_2024_selected_detail.csv", selected_detail)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase204 포항 제조업 중분류 사전검증 변동성 게이트

## 목적

Phase203은 2024년에 3년 평균이 전년 구성비 기준선보다 좋다는 사실을 확인했지만, 2024를 본 뒤 선택하면 사후최적화가 된다. 이번 실험은 2022~2023 롤링 검증만으로 변동성 게이트를 선택하고, 선택된 규칙을 2024에 외부검증한다.

## 후보 규칙

각 중분류의 최근 2~3년 구성비 표준편차가 기준치 이상이면 변동성 업종으로 보고, 해당 업종만 안정화한다. 기준치와 안정화 방식은 2022~2023에서만 선택했다.

## 2022~2023 사전 선택 결과

{md_table(pd.DataFrame([selected]).rename(columns={
    "gate_threshold_pp": "변동성 기준(%p)",
    "volatile_method": "변동 업종 안정화",
    "train_years": "학습연도수",
    "train_error_sum_pp": "학습 오차 합(%p)",
    "train_mae_pp": "학습 평균오차(%p)",
    "train_max_pp": "학습 최대오차(%p)",
    "train_gt5_cells": "학습 5%p 초과",
    "train_gt10_cells": "학습 10%p 초과",
}))}

## 2024 외부검증

{md_table(eval_summary.rename(columns={
    "target_year": "검증연도",
    "gate_threshold_pp": "변동성 기준(%p)",
    "volatile_method": "후보",
    "cells": "중분류수",
    "volatile_cells": "변동성 처리 중분류수",
    "actual_sum_eok": "actual 합계(억원)",
    "sum_abs_share_error_pp": "오차 합(%p)",
    "mae_share_pp": "평균오차(%p)",
    "max_abs_share_error_pp": "최대오차(%p)",
    "gt5pp_cells": "5%p 초과",
    "gt10pp_cells": "10%p 초과",
}))}

## 2024에서 안정화 적용된 중분류

{md_table(changed[[
    "middle_code",
    "middle_name",
    "history_volatility_pp",
    "actual_eok",
    "actual_share_pct",
    "predicted_share_pct",
    "abs_share_error_pp",
]].rename(columns={
    "middle_code": "KSIC",
    "middle_name": "업종명",
    "history_volatility_pp": "과거 변동성(%p)",
    "actual_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
    "predicted_share_pct": "추정 구성비(%)",
    "abs_share_error_pp": "구성비 오차(%p)",
}))}

## 2024 선택 규칙 잔여 고오차

{md_table(worst[[
    "middle_code",
    "middle_name",
    "is_volatile",
    "actual_eok",
    "actual_share_pct",
    "predicted_share_pct",
    "abs_share_error_pp",
]].rename(columns={
    "middle_code": "KSIC",
    "middle_name": "업종명",
    "is_volatile": "변동성 처리",
    "actual_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
    "predicted_share_pct": "추정 구성비(%)",
    "abs_share_error_pp": "구성비 오차(%p)",
}))}

## 판정

이 실험은 2024 actual을 선택에 쓰지 않는다는 점에서 Phase203보다 운영 검증에 가깝다. 다만 학습연도가 2022~2023 두 개뿐이므로, 채택 여부는 `2024 외부검증에서 기준선을 명확히 개선하는지`와 `오차가 특정 업종으로 이동하지 않는지`를 함께 보고 결정해야 한다.

선택 규칙이 전년 기준선을 이기면 포항 제조업 중분류에는 `전년 구성비 + 변동성 업종 안정화`를 후보 운영모형으로 승격할 수 있다. 이기지 못하면 C24/C25/C28은 여전히 항만·대형공장·업종별 전력 같은 직접 활동자료가 필요하다.
""",
        encoding="utf-8",
    )
    print(f"selected threshold={selected_th}, method={selected_method}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
