from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase202_kicox_middle_share_external_validation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase202_kicox_middle_share_external_validation.md"
RUN_ID = "partial_statistics_estimation_phase202_kicox_middle_share_external_validation"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, **kwargs)


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
        & raw["c1_nm"].isin(["고양시", "포항시"])
        & raw["c2_id"].astype(str).str.startswith("C")
    ].copy()
    x["actual"] = pd.to_numeric(x["value"], errors="coerce")
    x = x.dropna(subset=["actual"])
    x["city"] = x["c1_nm"]
    x["year"] = x["prd_de"].astype(int)
    x["middle_code"] = x["c2_id"].astype(str)
    x["middle_name"] = x["c2_nm"]
    x["actual_share"] = x["actual"] / x.groupby(["city", "year"])["actual"].transform("sum")
    return x[["city", "year", "middle_code", "middle_name", "actual", "actual_share"]]


def load_kicox_signal() -> pd.DataFrame:
    k = read_csv(DATA / "phase199_kicox_high_error_factory_enrichment" / "phase199_registration_eligibility_summary.csv")
    k = k[k["registration_status"].eq("eligible_by_registration_date")].copy()
    k = k.rename(
        columns={
            "target_city": "city",
            "target_middle_code": "middle_code",
            "target_year": "year",
            "employees": "kicox_employees",
            "matched_factories": "kicox_factories",
        }
    )
    return k[["city", "year", "middle_code", "kicox_employees", "kicox_factories"]]


def evaluate_alpha(actual: pd.DataFrame, kicox: pd.DataFrame, city: str, year: int, alpha: float) -> pd.DataFrame:
    cur = actual[(actual["city"].eq(city)) & (actual["year"].eq(year))].copy()
    prev = actual[(actual["city"].eq(city)) & (actual["year"].eq(year - 1))][
        ["middle_code", "actual_share"]
    ].rename(columns={"actual_share": "baseline_share"})
    cur = cur.merge(prev, on="middle_code", how="inner")
    cur["baseline_share"] = cur["baseline_share"] / cur["baseline_share"].sum()

    sig = kicox[(kicox["city"].eq(city)) & (kicox["year"].eq(year))].copy()
    target_codes = sorted(sig["middle_code"].dropna().unique())
    cur["is_kicox_target"] = cur["middle_code"].isin(target_codes)
    target_total = cur.loc[cur["is_kicox_target"], "baseline_share"].sum()

    cur = cur.merge(sig[["middle_code", "kicox_employees", "kicox_factories"]], on="middle_code", how="left")
    cur["kicox_employees"] = cur["kicox_employees"].fillna(0)
    cur["kicox_factories"] = cur["kicox_factories"].fillna(0)
    # Mild smoothing prevents one missing target from collapsing to exactly zero.
    cur["kicox_signal_raw"] = np.where(cur["is_kicox_target"], cur["kicox_employees"] + 1.0, 0.0)
    ksum = cur.loc[cur["is_kicox_target"], "kicox_signal_raw"].sum()
    cur["kicox_within_target_share"] = 0.0
    if ksum > 0 and target_total > 0:
        cur.loc[cur["is_kicox_target"], "kicox_within_target_share"] = (
            cur.loc[cur["is_kicox_target"], "kicox_signal_raw"] / ksum
        )
    cur["baseline_within_target_share"] = 0.0
    if target_total > 0:
        cur.loc[cur["is_kicox_target"], "baseline_within_target_share"] = (
            cur.loc[cur["is_kicox_target"], "baseline_share"] / target_total
        )

    cur["predicted_share"] = cur["baseline_share"]
    if target_total > 0:
        mixed_within = (
            alpha * cur["baseline_within_target_share"] + (1 - alpha) * cur["kicox_within_target_share"]
        )
        cur.loc[cur["is_kicox_target"], "predicted_share"] = target_total * mixed_within
    # Re-normalize for numerical safety.
    cur["predicted_share"] = cur["predicted_share"] / cur["predicted_share"].sum()
    cur["alpha_prev_year_share"] = alpha
    cur["share_error_pp"] = (cur["predicted_share"] - cur["actual_share"]) * 100
    cur["abs_share_error_pp"] = cur["share_error_pp"].abs()
    cur["actual_share_pct"] = cur["actual_share"] * 100
    cur["predicted_share_pct"] = cur["predicted_share"] * 100
    cur["actual_eok"] = cur["actual"] / 100
    return cur


def score(detail: pd.DataFrame) -> pd.DataFrame:
    return (
        detail.groupby(["city", "year", "alpha_prev_year_share"], as_index=False)
        .agg(
            cells=("middle_code", "nunique"),
            target_cells=("is_kicox_target", "sum"),
            actual_sum_eok=("actual_eok", "sum"),
            mae_share_pp=("abs_share_error_pp", "mean"),
            sum_abs_share_error_pp=("abs_share_error_pp", "sum"),
            gt5pp_cells=("abs_share_error_pp", lambda s: int((s > 5).sum())),
            gt10pp_cells=("abs_share_error_pp", lambda s: int((s > 10).sum())),
            max_abs_share_error_pp=("abs_share_error_pp", "max"),
        )
        .sort_values(["city", "year", "alpha_prev_year_share"])
    )


def main() -> int:
    actual = load_actual()
    kicox = load_kicox_signal()
    alphas = [round(a, 2) for a in np.linspace(0, 1, 11)]
    detail = pd.concat(
        [evaluate_alpha(actual, kicox, city, year, alpha) for city in ["고양시", "포항시"] for year in [2023, 2024] for alpha in alphas],
        ignore_index=True,
    )
    summary = score(detail)

    selected_rows = []
    eval_rows = []
    for city in ["고양시", "포항시"]:
        train = summary[(summary["city"].eq(city)) & (summary["year"].eq(2023))].copy()
        # Choose the most conservative alpha among tied minima.
        min_err = train["sum_abs_share_error_pp"].min()
        selected_alpha = train[train["sum_abs_share_error_pp"].eq(min_err)]["alpha_prev_year_share"].max()
        selected_rows.append(
            {
                "city": city,
                "train_year": 2023,
                "selected_alpha_prev_year_share": selected_alpha,
                "train_sum_abs_share_error_pp": min_err,
                "train_baseline_sum_abs_share_error_pp": float(train[train["alpha_prev_year_share"].eq(1.0)]["sum_abs_share_error_pp"].iloc[0]),
            }
        )
        eval_2024 = summary[
            summary["city"].eq(city)
            & summary["year"].eq(2024)
            & summary["alpha_prev_year_share"].isin([1.0, selected_alpha])
        ].copy()
        eval_2024["selected_in_2023"] = eval_2024["alpha_prev_year_share"].eq(selected_alpha)
        eval_rows.append(eval_2024)

    selected = pd.DataFrame(selected_rows)
    evaluation = pd.concat(eval_rows, ignore_index=True)
    detail_selected = detail.merge(
        selected[["city", "selected_alpha_prev_year_share"]],
        left_on="city",
        right_on="city",
        how="left",
    )
    detail_selected = detail_selected[
        detail_selected["alpha_prev_year_share"].eq(detail_selected["selected_alpha_prev_year_share"])
        & detail_selected["year"].eq(2024)
    ].copy()
    worst = detail_selected.sort_values(["city", "abs_share_error_pp"], ascending=[True, False]).groupby("city").head(8)

    write_csv("phase202_kicox_alpha_screen.csv", summary)
    write_csv("phase202_kicox_selected_alpha.csv", selected)
    write_csv("phase202_kicox_2024_external_evaluation.csv", evaluation)
    write_csv("phase202_kicox_2024_selected_detail.csv", detail_selected)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase202 KICOX 생산정보 기반 제조업 중분류 구성 외부검증

## 목적

Phase201에서 월간 제조업 산업생산지수는 C00 월별 시간경로에는 필수지만 중분류 구성비를 바꾸지 않는다는 점을 확인했다. 이번 단계는 Phase199에서 제한 수집한 KICOX 공장등록 생산정보의 종업원 신호가 고오차 제조업 중분류 묶음 내부 배분을 개선하는지 검증한다.

## 방법

- 기준선: 전년 중분류 부가가치 구성비
- 후보: 고오차 중분류 묶음 내부에서 `전년 구성비`와 `KICOX 등록일 적격 공장 종업원 구성비`를 혼합
- 학습/선택: 2023년 actual 구성비로 혼합비 선택
- 외부검증: 선택된 혼합비를 2024년에 적용
- 단위: 중분류 구성비 오차 `%p`

주의: KICOX 수집은 고오차 업종 상위 공장 중심의 제한 수집이므로, 개선되더라도 전체 운영모형 채택 전에는 전수 또는 더 넓은 범위 수집이 필요하다.

## 2023 선택 결과

{md_table(selected.rename(columns={
    "city": "지역",
    "train_year": "선택연도",
    "selected_alpha_prev_year_share": "선택 혼합비: 전년구성",
    "train_sum_abs_share_error_pp": "선택오차 합(%p)",
    "train_baseline_sum_abs_share_error_pp": "기준선오차 합(%p)",
}))}

## 2024 외부검증

{md_table(evaluation.rename(columns={
    "city": "지역",
    "year": "검증연도",
    "alpha_prev_year_share": "혼합비: 전년구성",
    "cells": "중분류수",
    "target_cells": "KICOX 대상 중분류수",
    "actual_sum_eok": "actual 합계(억원)",
    "mae_share_pp": "평균 구성비 오차(%p)",
    "sum_abs_share_error_pp": "오차 합(%p)",
    "gt5pp_cells": "5%p 초과",
    "gt10pp_cells": "10%p 초과",
    "max_abs_share_error_pp": "최대 오차(%p)",
    "selected_in_2023": "2023 선택값 여부",
}))}

## 2024 선택모형 잔여 고오차

{md_table(worst[[
    "city",
    "middle_code",
    "middle_name",
    "is_kicox_target",
    "actual_eok",
    "actual_share_pct",
    "predicted_share_pct",
    "abs_share_error_pp",
]].rename(columns={
    "city": "지역",
    "middle_code": "KSIC",
    "middle_name": "업종명",
    "is_kicox_target": "KICOX 대상",
    "actual_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
    "predicted_share_pct": "추정 구성비(%)",
    "abs_share_error_pp": "구성비 오차(%p)",
}))}

## 판정

KICOX 제한수집 종업원 신호는 고오차 제조업 중분류를 설명할 후보이지만, 현재 제한 수집 범위만으로는 운영 채택을 보장할 수 없다. 특히 포항은 C24 1차 금속 제조업의 지배적 비중을 제대로 포착해야 하므로, 단순 종업원 신호보다 생산액·출하액·대형공장 규모·항만 품목 물동량을 함께 쓰는 별도 블록이 필요하다.

다음 개선은 두 갈래다.

1. 고양: C13, C21, C23, C29는 KICOX 생산품 텍스트와 공장면적을 결합해 중분류 경계 혼동을 줄인다.
2. 포항: C24, C25, C28은 전년 구성비 기준선을 유지하되, 철강·금속·전기장비 전용 블록에서 항만 물동량, 대형공장 등록정보, 공장면적을 함께 쓰는 후보식을 별도로 검증한다.
""",
        encoding="utf-8",
    )
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
