#!/usr/bin/env python3
"""Audit whether lagged sigungu construction shares can improve WAPE.

The remaining region-level WAPE bottleneck is construction at
`sigungu x activity` level.  A tempting no-new-data refinement is to blend the
current predicted construction share with the previous published sigungu
construction actual share within each province.  This script tests that idea
without target-year lower-level actual leakage.

Result to watch: in the current pipeline the predicted construction share is
already identical to the previous-year actual share for rows where a lag exists.
Therefore the lag-share blend adds no information and cannot reduce WAPE.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "nationwide" / "construction_sigungu_share_refinement_audit.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def wape(abs_error: pd.Series, actual: pd.Series) -> float:
    denom = actual.abs().sum()
    if denom == 0:
        return float("nan")
    return float(abs_error.sum() / denom * 100)


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def load_construction() -> pd.DataFrame:
    sig = pd.read_csv(OUT / "annual_sigungu_activity_error_audit.csv")
    sido = pd.read_csv(OUT / "annual_sido_activity_error_audit.csv")
    sido = sido[sido["track"].eq("recursive_no_target_actual")][
        ["quarter_region", "year", "activity", "predicted_eok", "actual_eok"]
    ].rename(columns={"predicted_eok": "sido_predicted_eok", "actual_eok": "sido_actual_eok"})
    f = sig[sig["activity"].eq("건설업")].merge(sido, on=["quarter_region", "year", "activity"], how="left")
    f["parent_control_predicted_eok"] = f["predicted_eok"] * (
        f["sido_actual_eok"] / f["sido_predicted_eok"]
    ).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    f["pred_share"] = f["predicted_eok"] / f.groupby(["quarter_region", "year"])["predicted_eok"].transform("sum")
    f["actual_share"] = f["actual_eok"] / f.groupby(["quarter_region", "year"])["actual_eok"].transform("sum")
    lag = f[["quarter_region", "city", "year", "actual_share"]].copy()
    lag["year"] = lag["year"] + 1
    lag = lag.rename(columns={"actual_share": "lag_actual_share"})
    f = f.merge(lag, on=["quarter_region", "city", "year"], how="left")
    return f


def evaluate_blends(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for alpha in np.linspace(0, 1, 11):
        # alpha = 1: current predicted share
        # alpha = 0: previous published actual share, if available
        g = f.copy()
        raw = alpha * g["pred_share"] + (1 - alpha) * g["lag_actual_share"].fillna(g["pred_share"])
        g["raw_share"] = raw.clip(lower=0)
        g["blend_share"] = g["raw_share"] / g.groupby(["quarter_region", "year"])["raw_share"].transform("sum")
        g["candidate_predicted_eok"] = g["sido_actual_eok"] * g["blend_share"]
        g["candidate_abs_error_eok"] = (g["candidate_predicted_eok"] - g["actual_eok"]).abs()
        g["candidate_ape_pct"] = g["candidate_abs_error_eok"] / g["actual_eok"].abs() * 100
        rows.append(
            {
                "alpha_current_pred_share": round(float(alpha), 2),
                "candidate_wape_pct": wape(g["candidate_abs_error_eok"], g["actual_eok"]),
                "over10_cells": int((g["candidate_ape_pct"] > 10).sum()),
                "over20_cells": int((g["candidate_ape_pct"] > 20).sum()),
                "candidate_abs_error_sum_eok": float(g["candidate_abs_error_eok"].sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    f = load_construction()
    f["parent_control_abs_error_eok"] = (f["parent_control_predicted_eok"] - f["actual_eok"]).abs()
    f["parent_control_ape_pct"] = f["parent_control_abs_error_eok"] / f["actual_eok"].abs() * 100

    blends = evaluate_blends(f)
    lag_rows = f[f["lag_actual_share"].notna()].copy()
    lag_rows["share_abs_diff"] = (lag_rows["pred_share"] - lag_rows["lag_actual_share"]).abs()
    share_audit = pd.DataFrame(
        [
            {
                "rows_total": len(f),
                "rows_with_lag_share": len(lag_rows),
                "max_abs_share_diff": float(lag_rows["share_abs_diff"].max()) if len(lag_rows) else np.nan,
                "mean_abs_share_diff": float(lag_rows["share_abs_diff"].mean()) if len(lag_rows) else np.nan,
                "allclose_pred_share_lag_actual_share": bool(
                    np.allclose(lag_rows["pred_share"], lag_rows["lag_actual_share"]) if len(lag_rows) else False
                ),
            }
        ]
    )
    parent = pd.DataFrame(
        [
            {
                "scenario": "parent_control_current_pipeline",
                "wape_pct": wape(f["parent_control_abs_error_eok"], f["actual_eok"]),
                "over10_cells": int((f["parent_control_ape_pct"] > 10).sum()),
                "over20_cells": int((f["parent_control_ape_pct"] > 20).sum()),
                "abs_error_sum_eok": float(f["parent_control_abs_error_eok"].sum()),
            }
        ]
    )
    top = f.sort_values("parent_control_abs_error_eok", ascending=False).head(25)[
        [
            "quarter_region",
            "city",
            "year",
            "actual_eok",
            "parent_control_predicted_eok",
            "parent_control_abs_error_eok",
            "parent_control_ape_pct",
            "pred_share",
            "lag_actual_share",
        ]
    ]

    blends.to_csv(OUT / "construction_sigungu_lag_share_blend_summary.csv", index=False, encoding="utf-8-sig")
    share_audit.to_csv(OUT / "construction_sigungu_lag_share_identity_audit.csv", index=False, encoding="utf-8-sig")
    top.to_csv(OUT / "construction_sigungu_lag_share_top_errors.csv", index=False, encoding="utf-8-sig")

    report = f"""# 건설업 시군구 lag-share 정밀화 감사

생성시각: {CREATED_AT}

## 목적

시군구×업종에서 마지막으로 남은 WAPE 10% 초과 업종은 건설업이다.  
이번 감사는 추가 공공자료 없이 전년도 공표 시군구 건설업 실제 비중을 섞으면 성능이 개선되는지 확인한다.

## 기준 성능

{md_table(parent.rename(columns={
    "scenario": "시나리오",
    "wape_pct": "WAPE_pct",
    "over10_cells": "10초과셀",
    "over20_cells": "20초과셀",
    "abs_error_sum_eok": "절대오차합_억원",
}), 3)}

## lag-share 중복성 검사

{md_table(share_audit.rename(columns={
    "rows_total": "전체행",
    "rows_with_lag_share": "전년도share존재행",
    "max_abs_share_diff": "최대share차이",
    "mean_abs_share_diff": "평균share차이",
    "allclose_pred_share_lag_actual_share": "예측share와전년도actual_share동일",
}), 6)}

## 혼합비율별 결과

`alpha=1`은 현 예측 share, `alpha=0`은 전년도 actual share를 뜻한다.  
전년도 share가 없는 행은 현 예측 share로 대체했다.

{md_table(blends.rename(columns={
    "alpha_current_pred_share": "현예측share_가중치",
    "candidate_wape_pct": "후보WAPE_pct",
    "over10_cells": "10초과셀",
    "over20_cells": "20초과셀",
    "candidate_abs_error_sum_eok": "절대오차합_억원",
}), 3)}

## 대형 오차 셀

{md_table(top.rename(columns={
    "quarter_region": "시도",
    "city": "시군구",
    "year": "연도",
    "actual_eok": "실제_억원",
    "parent_control_predicted_eok": "상위총량반영추정_억원",
    "parent_control_abs_error_eok": "절대오차_억원",
    "parent_control_ape_pct": "오차율_pct",
    "pred_share": "현예측share",
    "lag_actual_share": "전년도actual_share",
}), 4)}

## 판정

- 전년도 actual share 혼합은 성능을 개선하지 못한다.
- 이유는 현재 건설업 시군구 예측 share가 이미 전년도 actual share와 사실상 동일하기 때문이다.
- 따라서 남은 건설업 오차는 과거 share 반복으로 해결되지 않는다.
- 필요한 것은 새 공간 활동자료다. 예: 시군구×월 건축허가·착공·준공 면적, 공사장 소재지 기준 공공계약 금액, 대형 개발사업 일정.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(parent.to_string(index=False))
    print(share_audit.to_string(index=False))
    print(blends.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
