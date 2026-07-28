from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase205_pohang_port_product_routed_manufacturing_validation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase205_pohang_port_product_routed_manufacturing_validation.md"
RUN_ID = "partial_statistics_estimation_phase205_pohang_port_product_routed_manufacturing_validation"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


PRODUCT_MAP = {
    "C23": ["시멘트", "모 래", "기타광석 및 생산품"],
    "C24": ["철광석", "유연탄", "철강 및 그제품", "고 철", "비철금속 및 그제품"],
    "C25": ["철강 및 그제품", "고 철", "비철금속 및 그제품"],
    "C28": ["전기기기 및 그부품"],
    "C29": ["기계류 및 그부품"],
}


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


def actual() -> pd.DataFrame:
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


def cargo_signal() -> pd.DataFrame:
    cargo = read_csv(DATA / "phase170_pohang_port_cargo_split_diagnostic" / "phase170_pohang_port_product_year.csv")
    rows = []
    for code, products in PRODUCT_MAP.items():
        sub = cargo[cargo["product"].isin(products)].groupby("year", as_index=False)["value_rt"].sum()
        sub["middle_code"] = code
        sub["mapped_products"] = ", ".join(products)
        rows.append(sub)
    sig = pd.concat(rows, ignore_index=True).sort_values(["middle_code", "year"])
    sig["prev_value_rt"] = sig.groupby("middle_code")["value_rt"].shift(1)
    sig["cargo_growth"] = np.where(sig["prev_value_rt"] > 0, sig["value_rt"] / sig["prev_value_rt"], 1.0)
    return sig


def predict(a: pd.DataFrame, sig: pd.DataFrame, target_year: int, beta: float, cap: float) -> pd.DataFrame:
    prev = a[a["year"].eq(target_year - 1)][["middle_code", "actual_share"]].rename(
        columns={"actual_share": "prev_share"}
    )
    cur_codes = a[a["year"].eq(target_year)][["middle_code", "middle_name"]].drop_duplicates()
    x = cur_codes.merge(prev, on="middle_code", how="inner")
    s = sig[sig["year"].eq(target_year)][["middle_code", "cargo_growth", "mapped_products"]]
    x = x.merge(s, on="middle_code", how="left")
    x["cargo_growth"] = x["cargo_growth"].fillna(1.0)
    x["mapped_products"] = x["mapped_products"].fillna("")
    x["capped_growth"] = x["cargo_growth"].clip(lower=1 / cap, upper=cap)
    x["is_port_routed"] = x["middle_code"].isin(PRODUCT_MAP)
    x["predicted_share_raw"] = x["prev_share"] * np.where(
        x["is_port_routed"], np.power(x["capped_growth"], beta), 1.0
    )
    x["predicted_share"] = x["predicted_share_raw"] / x["predicted_share_raw"].sum()
    x["target_year"] = target_year
    x["beta"] = beta
    x["growth_cap"] = cap
    return x


def evaluate(a: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    y = a.rename(columns={"year": "target_year"}).merge(pred, on=["target_year", "middle_code"], how="inner")
    y["actual_share_pct"] = y["actual_share"] * 100
    y["predicted_share_pct"] = y["predicted_share"] * 100
    y["share_error_pp"] = y["predicted_share_pct"] - y["actual_share_pct"]
    y["abs_share_error_pp"] = y["share_error_pp"].abs()
    y["actual_eok"] = y["actual"] / 100
    return y


def main() -> int:
    a = actual()
    sig = cargo_signal()
    betas = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
    caps = [1.25, 1.5, 2.0, 3.0]
    detail = pd.concat(
        [evaluate(a, predict(a, sig, year, beta, cap)) for year in [2023, 2024] for beta in betas for cap in caps],
        ignore_index=True,
    )
    summary = (
        detail.groupby(["target_year", "beta", "growth_cap"], as_index=False)
        .agg(
            cells=("middle_code", "nunique"),
            routed_cells=("is_port_routed", "sum"),
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
    selected_beta = float(selected["beta"])
    selected_cap = float(selected["growth_cap"])
    eval_summary = summary[
        summary["target_year"].eq(2024)
        & (
            (summary["beta"].eq(0.0) & summary["growth_cap"].eq(1.25))
            | (summary["beta"].eq(selected_beta) & summary["growth_cap"].eq(selected_cap))
        )
    ].copy()
    eval_summary["selected_by_2023"] = eval_summary["beta"].eq(selected_beta) & eval_summary["growth_cap"].eq(selected_cap)
    selected_detail = detail[
        detail["target_year"].eq(2024) & detail["beta"].eq(selected_beta) & detail["growth_cap"].eq(selected_cap)
    ].copy()
    worst = selected_detail.sort_values("abs_share_error_pp", ascending=False).head(10)
    routed = selected_detail[selected_detail["is_port_routed"]].sort_values("middle_code")

    write_csv("phase205_port_product_signal.csv", sig)
    write_csv("phase205_port_routed_detail.csv", detail)
    write_csv("phase205_port_routed_summary.csv", summary)
    write_csv("phase205_2024_external_eval_summary.csv", eval_summary)
    write_csv("phase205_2024_selected_detail.csv", selected_detail)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase205 포항항 품목별 물동량 라우팅 제조업 중분류 외부검증

## 목적

Phase198은 철강·광물 물동량을 큰 블록으로만 섞어 외부검증에서 기각됐다. 이번 실험은 포항항 품목별 월/연 물동량을 C23/C24/C25/C28/C29 중분류에 각각 연결해, 전년 구성비 기준선보다 중분류 구성비 예측이 좋아지는지 확인한다.

## 품목 라우팅

{md_table(pd.DataFrame([
    {"KSIC": code, "연결 품목": ", ".join(products)} for code, products in PRODUCT_MAP.items()
]))}

## 검증 방식

- 기준선: 전년 중분류 구성비
- 후보: 라우팅된 중분류에 한해 `전년 구성비 × 품목 물동량 성장률^beta`
- 성장률 상한/하한: cap으로 제한
- 선택: 2023년 actual 구성비로 beta/cap 선택
- 외부검증: 2024년 actual 구성비

## 2023 선택 결과

| beta | 성장률 cap | 2023 오차 합(%p) |
|---:|---:|---:|
| {selected_beta:.3f} | {selected_cap:.3f} | {float(selected['sum_abs_share_error_pp']):.3f} |

## 2024 외부검증

{md_table(eval_summary.rename(columns={
    "target_year": "검증연도",
    "beta": "beta",
    "growth_cap": "성장률 cap",
    "cells": "중분류수",
    "routed_cells": "항만 라우팅 중분류수",
    "actual_sum_eok": "actual 합계(억원)",
    "sum_abs_share_error_pp": "오차 합(%p)",
    "mae_share_pp": "평균오차(%p)",
    "max_abs_share_error_pp": "최대오차(%p)",
    "gt5pp_cells": "5%p 초과",
    "gt10pp_cells": "10%p 초과",
    "selected_by_2023": "2023 선택값",
}))}

## 2024 항만 라우팅 중분류

{md_table(routed[[
    "middle_code",
    "middle_name_x",
    "mapped_products",
    "cargo_growth",
    "actual_eok",
    "actual_share_pct",
    "predicted_share_pct",
    "abs_share_error_pp",
]].rename(columns={
    "middle_code": "KSIC",
    "middle_name_x": "업종명",
    "mapped_products": "연결 품목",
    "cargo_growth": "품목 물동량 성장률",
    "actual_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
    "predicted_share_pct": "추정 구성비(%)",
    "abs_share_error_pp": "구성비 오차(%p)",
}))}

## 2024 잔여 고오차

{md_table(worst[[
    "middle_code",
    "middle_name_x",
    "is_port_routed",
    "actual_eok",
    "actual_share_pct",
    "predicted_share_pct",
    "abs_share_error_pp",
]].rename(columns={
    "middle_code": "KSIC",
    "middle_name_x": "업종명",
    "is_port_routed": "항만 라우팅",
    "actual_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
    "predicted_share_pct": "추정 구성비(%)",
    "abs_share_error_pp": "구성비 오차(%p)",
}))}

## 판정

항만 품목별 물동량은 포항 제조업의 구조를 설명하는 중요한 보조자료지만, 중분류 부가가치 구성비를 그대로 대체할 수 있는 직접 생산지표는 아니다. 특히 `전기기기 및 그부품` 물동량은 2024년에 증가했지만 C28 전기장비 제조업 부가가치 비중은 하락했다. 따라서 C28은 항만 물동량보다 공장 생산품/대형업체/업종별 전력 같은 자료가 더 필요하다.

2023에서 선택된 라우팅 후보가 2024 기준선을 명확히 이기지 못하면 운영 채택하지 않는다. 이 경우 항만 자료는 수상운송업·항만활동 및 C24 진단 보조지표로 유지하고, 제조업 중분류 구조 개선에는 추가 직접자료를 요구한다.
""",
        encoding="utf-8",
    )
    print(f"selected beta={selected_beta}, cap={selected_cap}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
