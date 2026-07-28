from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
P189 = DATA / "phase189_manufacturing_factory_metric_screen"
OUT = DATA / "phase190_manufacturing_middle_routed_activity"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase190_manufacturing_middle_routed_activity.md"
RUN_ID = "partial_statistics_estimation_phase190_manufacturing_middle_routed_activity"
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


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    payload = out.to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    out.to_csv(OUT / name, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame, digits: int = 2, limit: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if limit is not None and len(view) > limit:
        view = view.head(limit).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
        else:
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else str(x))
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    if limit is not None and len(df) > limit:
        lines.append(f"\n_상위 {limit:,}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def load_phase189_detail() -> pd.DataFrame:
    path = P189 / "phase189_factory_metric_detail.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    d = read_csv(path)
    # Drop audit columns if present.
    return d[[c for c in d.columns if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]].copy()


def route_middle(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline_key = {"metric": "factory_count", "alpha_prev_gva": 1.0}
    rows = []
    applied_rows = []
    for city in sorted(detail["city"].unique()):
        train = detail[(detail["city"].eq(city)) & (detail["target_year"].eq(2023))].copy()
        test = detail[(detail["city"].eq(city)) & (detail["target_year"].eq(2024))].copy()
        for code in sorted(set(train["middle_code"]) & set(test["middle_code"])):
            tr = train[train["middle_code"].eq(code)].copy()
            te = test[test["middle_code"].eq(code)].copy()
            if tr.empty or te.empty:
                continue
            tr_base = tr[
                tr["metric"].eq(baseline_key["metric"]) & tr["alpha_prev_gva"].eq(baseline_key["alpha_prev_gva"])
            ].iloc[0]
            te_base = te[
                te["metric"].eq(baseline_key["metric"]) & te["alpha_prev_gva"].eq(baseline_key["alpha_prev_gva"])
            ].iloc[0]
            tr = tr.assign(
                train_error_delta_vs_base=lambda x: x["error_gva_eok"] - float(tr_base["error_gva_eok"]),
                train_rate_delta_vs_base=lambda x: x["error_rate_pct"] - float(tr_base["error_rate_pct"]),
            )
            # Candidate must improve in train by either >=10억원 or >=10% relative
            # error reduction, otherwise keep baseline. This avoids changing cells
            # for noise-sized gains.
            tr["material_train_gain"] = (
                (float(tr_base["error_gva_eok"]) - tr["error_gva_eok"] >= 10)
                | ((float(tr_base["error_gva_eok"]) - tr["error_gva_eok"]) / max(float(tr_base["error_gva_eok"]), 1e-9) >= 0.10)
            )
            candidates = tr[tr["material_train_gain"]].sort_values(["error_gva_eok", "error_rate_pct"])
            selected = candidates.iloc[0] if len(candidates) else tr_base
            te_sel = te[te["metric"].eq(selected["metric"]) & te["alpha_prev_gva"].eq(selected["alpha_prev_gva"])].iloc[0]
            improved_2024 = float(te_sel["error_gva_eok"]) < float(te_base["error_gva_eok"]) - 1e-9
            rows.append(
                {
                    "city": city,
                    "middle_code": code,
                    "middle_name": te_base["middle_name"],
                    "selected_metric": selected["metric"],
                    "selected_alpha_prev_gva": float(selected["alpha_prev_gva"]),
                    "train_2023_actual_eok": float(selected["actual_gva_eok"]),
                    "train_2023_baseline_error_eok": float(tr_base["error_gva_eok"]),
                    "train_2023_selected_error_eok": float(selected["error_gva_eok"]),
                    "train_2023_error_reduction_eok": float(tr_base["error_gva_eok"] - selected["error_gva_eok"]),
                    "test_2024_actual_eok": float(te_base["actual_gva_eok"]),
                    "test_2024_baseline_pred_eok": float(te_base["predicted_gva_eok"]),
                    "test_2024_selected_pred_eok": float(te_sel["predicted_gva_eok"]),
                    "test_2024_baseline_error_eok": float(te_base["error_gva_eok"]),
                    "test_2024_selected_error_eok": float(te_sel["error_gva_eok"]),
                    "test_2024_error_delta_eok": float(te_sel["error_gva_eok"] - te_base["error_gva_eok"]),
                    "test_2024_baseline_error_pct": float(te_base["error_rate_pct"]),
                    "test_2024_selected_error_pct": float(te_sel["error_rate_pct"]),
                    "improved_2024": improved_2024,
                    "route_judgement": "후보 유지 가능" if improved_2024 and selected["metric"] != baseline_key["metric"] else "기준 유지",
                    "vintage_scope": "정밀화 후보: 공장등록 current snapshot 사용",
                }
            )
            if improved_2024 and selected["metric"] != baseline_key["metric"]:
                applied_rows.append(te_sel.to_dict())
    routed = pd.DataFrame(rows)
    applied = pd.DataFrame(applied_rows)

    summary_rows = []
    for city, g in routed.groupby("city"):
        base_error = float(g["test_2024_baseline_error_eok"].sum())
        selected_error = float(g["test_2024_selected_error_eok"].sum())
        actual = float(g["test_2024_actual_eok"].sum())
        safe = g.copy()
        safe["safe_error_eok"] = np.where(g["improved_2024"], g["test_2024_selected_error_eok"], g["test_2024_baseline_error_eok"])
        safe_error = float(safe["safe_error_eok"].sum())
        summary_rows.extend(
            [
                {
                    "city": city,
                    "candidate": "전년 중분류 구조 기준선",
                    "actual_sum_eok": actual,
                    "error_sum_eok": base_error,
                    "wape_pct": base_error / actual * 100,
                    "improved_cells": 0,
                    "worsened_cells": 0,
                    "gt20_cells": int((g["test_2024_baseline_error_pct"] > 20).sum()),
                },
                {
                    "city": city,
                    "candidate": "2023 선택후보 단순적용",
                    "actual_sum_eok": actual,
                    "error_sum_eok": selected_error,
                    "wape_pct": selected_error / actual * 100,
                    "improved_cells": int((g["test_2024_error_delta_eok"] < -1e-9).sum()),
                    "worsened_cells": int((g["test_2024_error_delta_eok"] > 1e-9).sum()),
                    "gt20_cells": int((g["test_2024_selected_error_pct"] > 20).sum()),
                },
                {
                    "city": city,
                    "candidate": "무악화 사후상한 진단값",
                    "actual_sum_eok": actual,
                    "error_sum_eok": safe_error,
                    "wape_pct": safe_error / actual * 100,
                    "improved_cells": int(g["improved_2024"].sum()),
                    "worsened_cells": 0,
                    "gt20_cells": int(
                        (
                            np.where(g["improved_2024"], g["test_2024_selected_error_pct"], g["test_2024_baseline_error_pct"])
                            > 20
                        ).sum()
                    ),
                },
            ]
        )
    summary = pd.DataFrame(summary_rows)
    return routed, applied, summary


def write_report(routed: pd.DataFrame, summary: pd.DataFrame) -> None:
    gains = routed.sort_values("test_2024_error_delta_eok").head(15)
    losses = routed.sort_values("test_2024_error_delta_eok", ascending=False).head(15)
    adopted = routed[routed["route_judgement"].eq("후보 유지 가능")].sort_values("test_2024_error_delta_eok")
    text = f"""# Phase190 제조업 중분류별 활동자료 라우팅 검증

## 목적

Phase189의 전체 공장등록 혼합은 채택되지 않았다. Phase190은 더 좁게, **중분류별로만** 공장등록 활동자료 후보를 고르는 실험이다. 2022→2023 검증에서 후보를 고르고, 같은 후보를 2023→2024에 적용해 성능을 확인했다.

## 검증 규칙

- 기준선: 전년 중분류 GVA 구조 유지.
- 후보: 공장 수, 종업원, 제조시설면적, 건축면적, 용지면적, 종업원×면적 결합.
- 선택: 2023년에서 기준선 대비 10억원 이상 또는 10% 이상 오차가 줄어드는 후보만 선택.
- 평가: 2024년에 그대로 적용.
- 주의: 공장등록은 current snapshot이므로 속보성 지표가 아니라 **정밀화 후보**다.

## 2024 집계 성능

{md_table(summary.rename(columns={
    "city": "지역",
    "candidate": "후보",
    "actual_sum_eok": "실제합계(억원)",
    "error_sum_eok": "오차합계(억원)",
    "wape_pct": "WAPE(%)",
    "improved_cells": "개선셀",
    "worsened_cells": "악화셀",
    "gt20_cells": "20%초과",
}), 2)}

## 실제 개선 셀

{md_table(adopted[["city","middle_code","middle_name","selected_metric","selected_alpha_prev_gva","test_2024_actual_eok","test_2024_baseline_error_eok","test_2024_selected_error_eok","test_2024_error_delta_eok","test_2024_selected_error_pct"]].rename(columns={
    "city": "지역",
    "middle_code": "코드",
    "middle_name": "중분류",
    "selected_metric": "선택 활동자료",
    "selected_alpha_prev_gva": "전년구조 비중",
    "test_2024_actual_eok": "2024 실제(억원)",
    "test_2024_baseline_error_eok": "기준오차(억원)",
    "test_2024_selected_error_eok": "후보오차(억원)",
    "test_2024_error_delta_eok": "오차증감(억원)",
    "test_2024_selected_error_pct": "후보오차율(%)",
}), 2, 20)}

## 개선폭 상위

{md_table(gains[["city","middle_code","middle_name","selected_metric","selected_alpha_prev_gva","test_2024_baseline_error_eok","test_2024_selected_error_eok","test_2024_error_delta_eok"]].rename(columns={
    "city": "지역",
    "middle_code": "코드",
    "middle_name": "중분류",
    "selected_metric": "선택 활동자료",
    "selected_alpha_prev_gva": "전년구조 비중",
    "test_2024_baseline_error_eok": "기준오차(억원)",
    "test_2024_selected_error_eok": "후보오차(억원)",
    "test_2024_error_delta_eok": "오차증감(억원)",
}), 2)}

## 악화폭 상위

{md_table(losses[["city","middle_code","middle_name","selected_metric","selected_alpha_prev_gva","test_2024_baseline_error_eok","test_2024_selected_error_eok","test_2024_error_delta_eok"]].rename(columns={
    "city": "지역",
    "middle_code": "코드",
    "middle_name": "중분류",
    "selected_metric": "선택 활동자료",
    "selected_alpha_prev_gva": "전년구조 비중",
    "test_2024_baseline_error_eok": "기준오차(억원)",
    "test_2024_selected_error_eok": "후보오차(억원)",
    "test_2024_error_delta_eok": "오차증감(억원)",
}), 2)}

## 판정

1. 중분류별 후보 선택은 전체 혼합보다 낫지만, 2023에서 좋아 보인 후보가 2024에서 악화되는 경우가 남는다.
2. 따라서 운영값에는 `2023 선택후보 단순적용`을 넣으면 안 된다.
3. `무악화 사후상한 진단값`은 목표연도 actual을 본 사후진단이므로 예측성능으로 주장할 수 없다. 다만 어느 업종에 활동자료가 먹히는지 확인하는 상한선으로만 사용한다.
4. 실제 운영 가능한 개선을 위해서는 중분류별로 공장등록 current snapshot이 아니라 해당연도/해당분기 활동자료가 필요하다. 특히 포항 전기장비·금속가공·비금속·기계수리, 고양 섬유·의약품·기계 쪽은 연도별 갱신 자료가 없으면 10% 목표가 불안정하다.
"""
    REPORT.write_text(text, encoding="utf-8")


def main() -> None:
    detail = load_phase189_detail()
    routed, applied, summary = route_middle(detail)
    write_csv("phase190_middle_route_detail.csv", routed)
    write_csv("phase190_middle_route_applied_if_improved.csv", applied)
    write_csv("phase190_middle_route_summary.csv", summary)
    write_report(routed, summary)
    print(REPORT)


if __name__ == "__main__":
    main()
