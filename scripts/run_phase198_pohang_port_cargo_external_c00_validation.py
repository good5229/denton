from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase198_pohang_port_cargo_external_c00_validation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase198_pohang_port_cargo_external_c00_validation.md"
RUN_ID = "partial_statistics_estimation_phase198_pohang_port_cargo_external_c00_validation"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

STEEL_MINERAL_CODES = {"C23", "C24", "C25"}
ALPHAS = [0.0, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


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


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
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
    raw = pd.read_csv(DATA / "expanded_manufacturing_sigungu_ksic.csv", encoding="cp949", dtype=str)
    x = raw[
        raw["c1_nm"].eq("포항시")
        & raw["c2_id"].astype(str).str.startswith("C", na=False)
        & raw["metric"].eq("value_added")
    ].copy()
    x["year"] = x["prd_de"].astype(int)
    x["middle_code"] = x["c2_id"].astype(str)
    x["middle_name"] = x["c2_nm"].astype(str)
    x["actual_gva_eok"] = pd.to_numeric(x["value"], errors="coerce") / 100.0
    x = x[x["year"].between(2022, 2024)].dropna(subset=["actual_gva_eok"])
    total = x.groupby("year", as_index=False)["actual_gva_eok"].sum().rename(columns={"actual_gva_eok": "c00_total_eok"})
    return x.merge(total, on="year", how="left")


def load_port() -> pd.DataFrame:
    p = DATA / "phase170_pohang_port_cargo_split_diagnostic" / "phase170_pohang_port_annual_summary.csv"
    port = pd.read_csv(p, encoding="utf-8-sig")
    port["cargo_steel_mineral_share"] = port["steel_mineral_share_pct"] / 100.0
    return port[["year", "cargo_steel_mineral_share", "steel_mineral_share_pct", "total_rt"]]


def predict(actual: pd.DataFrame, port: pd.DataFrame, target_year: int, alpha: float) -> pd.DataFrame:
    prev = actual[actual["year"].eq(target_year - 1)].copy()
    tgt = actual[actual["year"].eq(target_year)].copy()
    common = sorted(set(prev["middle_code"]) & set(tgt["middle_code"]))
    prev = prev[prev["middle_code"].isin(common)].copy()
    tgt = tgt[tgt["middle_code"].isin(common)].copy()
    prev_total = prev["actual_gva_eok"].sum()
    target_total = tgt["actual_gva_eok"].sum()
    base_share = prev.set_index("middle_code")["actual_gva_eok"] / prev_total

    port_row = port[port["year"].eq(target_year)]
    if port_row.empty:
        cargo_share = np.nan
    else:
        cargo_share = float(port_row.iloc[0]["cargo_steel_mineral_share"])
    pred_share = base_share.copy()
    block = [c for c in pred_share.index if c in STEEL_MINERAL_CODES]
    other = [c for c in pred_share.index if c not in STEEL_MINERAL_CODES]
    baseline_block_share = float(pred_share.loc[block].sum())
    target_block_share = (1 - alpha) * baseline_block_share + alpha * cargo_share
    target_block_share = min(max(target_block_share, 0.0), 0.98)
    if block and baseline_block_share > 0:
        pred_share.loc[block] = pred_share.loc[block] / baseline_block_share * target_block_share
    other_sum = float(base_share.loc[other].sum())
    if other and other_sum > 0:
        pred_share.loc[other] = base_share.loc[other] / other_sum * (1 - target_block_share)
    pred_share = pred_share / pred_share.sum()

    rows = []
    for _, r in tgt.iterrows():
        code = r["middle_code"]
        pred = float(pred_share.loc[code] * target_total)
        actual_eok = float(r["actual_gva_eok"])
        rows.append(
            {
                "target_year": target_year,
                "alpha": alpha,
                "middle_code": code,
                "middle_name": r["middle_name"],
                "actual_gva_eok": actual_eok,
                "predicted_gva_eok": pred,
                "error_gva_eok": abs(pred - actual_eok),
                "error_rate_pct": abs(pred - actual_eok) / actual_eok * 100 if actual_eok else np.nan,
                "target_total_c00_eok": target_total,
                "baseline_block_share_pct": baseline_block_share * 100,
                "cargo_steel_mineral_share_pct": cargo_share * 100,
                "target_block_share_pct": target_block_share * 100,
                "method": "prev_year_structure_with_port_steel_mineral_block_share",
            }
        )
    return pd.DataFrame(rows)


def summarize(detail: pd.DataFrame) -> pd.DataFrame:
    s = (
        detail.groupby(["target_year", "alpha"], as_index=False)
        .agg(
            cells=("middle_code", "nunique"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("error_gva_eok", "sum"),
            gt10_cells=("error_rate_pct", lambda x: int((x > 10).sum())),
            gt20_cells=("error_rate_pct", lambda x: int((x > 20).sum())),
            gt50_cells=("error_rate_pct", lambda x: int((x > 50).sum())),
            baseline_block_share_pct=("baseline_block_share_pct", "first"),
            cargo_steel_mineral_share_pct=("cargo_steel_mineral_share_pct", "first"),
            target_block_share_pct=("target_block_share_pct", "first"),
        )
    )
    s["wape_pct"] = s["error_sum_eok"] / s["actual_sum_eok"] * 100
    return s.sort_values(["target_year", "wape_pct", "alpha"])


def main() -> int:
    actual = load_actual()
    port = load_port()
    detail = pd.concat([predict(actual, port, year, alpha) for year in [2023, 2024] for alpha in ALPHAS], ignore_index=True)
    summary = summarize(detail)

    train = summary[summary["target_year"].eq(2023)].sort_values(["wape_pct", "alpha"]).iloc[0]
    selected_alpha = float(train["alpha"])
    eval_2024 = summary[(summary["target_year"].eq(2024)) & (summary["alpha"].eq(selected_alpha))].iloc[0]
    baseline_2024 = summary[(summary["target_year"].eq(2024)) & (summary["alpha"].eq(0.0))].iloc[0]
    selected_detail = detail[(detail["target_year"].eq(2024)) & (detail["alpha"].eq(selected_alpha))].copy()
    baseline_detail = detail[(detail["target_year"].eq(2024)) & (detail["alpha"].eq(0.0))].copy()
    comp = selected_detail.merge(
        baseline_detail[["middle_code", "error_gva_eok", "error_rate_pct", "predicted_gva_eok"]].rename(
            columns={
                "error_gva_eok": "baseline_error_gva_eok",
                "error_rate_pct": "baseline_error_rate_pct",
                "predicted_gva_eok": "baseline_predicted_gva_eok",
            }
        ),
        on="middle_code",
        how="left",
    )
    comp["error_change_eok"] = comp["error_gva_eok"] - comp["baseline_error_gva_eok"]
    comp["adoption_verdict"] = np.where(comp["error_change_eok"] < 0, "improved", np.where(comp["error_change_eok"] > 0, "worsened", "same"))
    eval_summary = pd.DataFrame(
        [
            {
                "train_year": 2023,
                "selected_alpha": selected_alpha,
                "train_wape_pct": float(train["wape_pct"]),
                "eval_year": 2024,
                "baseline_2024_wape_pct": float(baseline_2024["wape_pct"]),
                "selected_2024_wape_pct": float(eval_2024["wape_pct"]),
                "wape_change_pp": float(eval_2024["wape_pct"] - baseline_2024["wape_pct"]),
                "baseline_2024_error_sum_eok": float(baseline_2024["error_sum_eok"]),
                "selected_2024_error_sum_eok": float(eval_2024["error_sum_eok"]),
                "error_sum_change_eok": float(eval_2024["error_sum_eok"] - baseline_2024["error_sum_eok"]),
                "adoptable": bool(selected_alpha > 0 and eval_2024["wape_pct"] < baseline_2024["wape_pct"]),
                "decision": "adopt_external_validated_route"
                if selected_alpha > 0 and eval_2024["wape_pct"] < baseline_2024["wape_pct"]
                else "reject_no_external_improvement",
            }
        ]
    )

    write_csv("phase198_port_cargo_alpha_summary.csv", summary)
    write_csv("phase198_port_cargo_detail.csv", detail)
    write_csv("phase198_2024_selected_vs_baseline_detail.csv", comp.sort_values("error_change_eok"))
    write_csv("phase198_external_eval_summary.csv", eval_summary)

    top = comp.reindex(comp["baseline_error_gva_eok"].abs().sort_values(ascending=False).index).head(12)
    report = f"""# Phase198 포항항 물동량 기반 제조업 중분류 외부연도 검증

## 목적

포항 제조업 C00 중분류 금액오차를 줄이기 위해 포항항 품목 물동량을 직접 활동자료로 사용할 수 있는지 외부연도 방식으로 검증했다. 2023년에서 혼합강도 alpha를 선택하고, 같은 alpha를 2024년에 적용했다.

## 방법

- 기준선: 전년 제조업 중분류 GVA 구조 유지
- 후보: C23 비금속광물, C24 1차금속, C25 금속가공 블록의 비중을 포항항 철강·광물 물동량 비중 방향으로 일부 이동
- alpha: 0이면 기준선, 값이 클수록 항만 물동량 비중을 더 반영
- 선택: 2023년 WAPE 최소 alpha 선택
- 평가: 선택 alpha를 2024년에 고정 적용

## 외부연도 평가 요약

{md_table(eval_summary.rename(columns={
    "train_year": "선택연도",
    "selected_alpha": "선택 alpha",
    "train_wape_pct": "선택연도 WAPE(%)",
    "eval_year": "평가연도",
    "baseline_2024_wape_pct": "2024 기준 WAPE(%)",
    "selected_2024_wape_pct": "2024 후보 WAPE(%)",
    "wape_change_pp": "WAPE 변화(pp)",
    "baseline_2024_error_sum_eok": "기준 오차합(억원)",
    "selected_2024_error_sum_eok": "후보 오차합(억원)",
    "error_sum_change_eok": "오차합 변화(억원)",
    "adoptable": "채택가능",
    "decision": "판정",
}), 4)}

## 2024 중분류별 후보 vs 기준

단위: 억원, %.

{md_table(top[["middle_code","middle_name","actual_gva_eok","baseline_predicted_gva_eok","predicted_gva_eok","baseline_error_gva_eok","error_gva_eok","error_change_eok","baseline_error_rate_pct","error_rate_pct","adoption_verdict"]].rename(columns={
    "middle_code": "중분류",
    "middle_name": "업종명",
    "actual_gva_eok": "실제",
    "baseline_predicted_gva_eok": "기준추정",
    "predicted_gva_eok": "후보추정",
    "baseline_error_gva_eok": "기준오차",
    "error_gva_eok": "후보오차",
    "error_change_eok": "오차변화",
    "baseline_error_rate_pct": "기준오차율",
    "error_rate_pct": "후보오차율",
    "adoption_verdict": "판정",
}), 2)}

## 판정

1. 포항항 철강·광물 물동량은 C24 1차금속 등 일부 중분류의 방향성 진단에는 유용하다.
2. 그러나 2023에서 고른 alpha를 2024에 고정 적용했을 때 기준선을 이기는지 여부로만 채택한다.
3. 이 검증에서는 2023 선택 alpha가 0이므로 항만 물동량 혼합은 운영값에 넣지 않는다. 포항 제조업 설명에는 `항만 물동량은 후보 활동자료이나 외부연도 검증에서 독립 개선 미확인`으로 둔다.
4. C24는 금액 규모가 커서 오차율은 낮아도 오차금액이 크다. C25/C28/C23 같은 고오차 업종은 항만 물동량만으로 부족하며 공장 생산품·전력·출하 자료가 추가로 필요하다.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
