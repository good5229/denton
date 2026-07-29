#!/usr/bin/env python3
"""Phase259: leakage-guarded electricity share holdout for mining/manufacturing.

This experiment tests whether annual industrial electricity can improve the
sigungu spatial distribution of `광업, 제조업` without changing the province-year
parent total.  It does not adopt a route.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase259_mfg_electricity_holdout.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

BASE = OUT / "annual_sigungu_activity_error_audit.csv"
ELEC = ROOT / "data" / "processed" / "municipality_electricity_features_2021_2023.csv"
FACTORY = ROOT / "data" / "raw" / "public_data_portal" / "factory_full_snapshot_15106170_download.csv"

BASELINE_WEIGHT_GRID = [1.0, 0.75, 0.5, 0.25, 0.0]


def read_csv_fallback(path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError(f"cannot read {path}")


def md_table(df: pd.DataFrame, limit: int | None = None, digits: int = 3) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if str(c).lower() in {"year", "holdout_year"}:
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else str(int(v)))
        elif pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{float(v):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def metric(df: pd.DataFrame, pred_col: str, label: str) -> dict[str, Any]:
    actual = pd.to_numeric(df["actual_eok"], errors="coerce")
    pred = pd.to_numeric(df[pred_col], errors="coerce")
    abs_err = (pred - actual).abs()
    ape = np.where(actual.gt(0), abs_err / actual * 100, np.nan)
    large = actual.abs().ge(1000)
    return {
        "scenario": label,
        "rows": int(len(df)),
        "actual_sum_eok": float(actual.sum()),
        "predicted_sum_eok": float(pred.sum()),
        "abs_error_sum_eok": float(abs_err.sum()),
        "wape_pct": float(abs_err.sum() / actual.sum() * 100) if actual.sum() else np.nan,
        "over10_cells": int((ape > 10).sum()),
        "over20_cells": int((ape > 20).sum()),
        "large_actual_over10_cells": int(((ape > 10) & large).sum()),
        "max_ape_pct": float(np.nanmax(ape)) if len(ape) else np.nan,
    }


def province_key(name: object) -> str:
    text = "" if pd.isna(name) else str(name)
    return text.replace("전라북도", "전북특별자치도").replace("강원도", "강원특별자치도")


def load_base() -> pd.DataFrame:
    x = pd.read_csv(BASE)
    x = x[x["activity"].eq("광업, 제조업") & x["year"].between(2021, 2023)].copy()
    for c in ["predicted_eok", "actual_eok"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    parent = (
        x.groupby(["province_full", "year"], as_index=False)
        .agg(parent_predicted_eok=("predicted_eok", "sum"), parent_actual_eok=("actual_eok", "sum"))
    )
    x = x.merge(parent, on=["province_full", "year"], how="left")
    x["baseline_share"] = np.where(x["parent_predicted_eok"].abs().gt(0), x["predicted_eok"] / x["parent_predicted_eok"], np.nan)
    return x


def load_electricity() -> pd.DataFrame:
    e = read_csv_fallback(ELEC)
    e = e[e["year"].between(2021, 2023)].copy()
    e["province_full"] = e["sido_name_normalized"].map(province_key)
    e["city"] = e["sigungu_name_normalized"].astype(str)
    e["industrial_kwh"] = pd.to_numeric(e["electricity_industrial_kwh"], errors="coerce").fillna(0)
    e["leakage_ok"] = e["leakage_check_passed"].astype(str).eq("Y")
    annual = (
        e.groupby(["province_full", "city", "year"], as_index=False)
        .agg(
            electricity_months=("observation_period", "nunique"),
            industrial_kwh=("industrial_kwh", "sum"),
            leakage_ok_months=("leakage_ok", "sum"),
            source_publication_min=("source_publication_date", "min"),
            source_publication_max=("source_publication_date", "max"),
        )
    )
    total = annual.groupby(["province_full", "year"], as_index=False).agg(province_industrial_kwh=("industrial_kwh", "sum"))
    annual = annual.merge(total, on=["province_full", "year"], how="left")
    annual["electricity_share"] = np.where(
        annual["province_industrial_kwh"].gt(0), annual["industrial_kwh"] / annual["province_industrial_kwh"], np.nan
    )
    return annual


def factory_diagnostic(base: pd.DataFrame) -> pd.DataFrame:
    f = read_csv_fallback(FACTORY)
    f["province_full"] = f["시도명"].map(province_key)
    f["city"] = [factory_city_rollup(p, c) for p, c in zip(f["시도명"], f["시군구명"], strict=False)]
    for c in ["종업원합계", "제조시설면적"]:
        f[c] = pd.to_numeric(f[c], errors="coerce").fillna(0)
    agg = (
        f.groupby(["province_full", "city"], as_index=False)
        .agg(factory_rows=("회사명", "count"), factory_employee_sum=("종업원합계", "sum"), factory_mfg_area_sum=("제조시설면적", "sum"))
    )
    joined = base[["province_full", "city", "year", "actual_eok", "predicted_eok"]].merge(agg, on=["province_full", "city"], how="left")
    joined[["factory_rows", "factory_employee_sum", "factory_mfg_area_sum"]] = joined[
        ["factory_rows", "factory_employee_sum", "factory_mfg_area_sum"]
    ].fillna(0)
    return (
        joined.groupby("year", as_index=False)
        .agg(
            validation_cells=("city", "size"),
            cells_with_factory=("factory_rows", lambda s: int((pd.to_numeric(s, errors="coerce").fillna(0) > 0).sum())),
            factory_rows=("factory_rows", "sum"),
            factory_employee_sum=("factory_employee_sum", "sum"),
            factory_mfg_area_sum=("factory_mfg_area_sum", "sum"),
        )
    )


def factory_city_rollup(province: object, city: object) -> str:
    prov = "" if pd.isna(province) else str(province).strip()
    text = "" if pd.isna(city) else str(city).strip()
    if "세종" in prov and not text:
        return "세종시"
    first = text.split()[0] if text else ""
    if first.endswith("시"):
        return first
    return text


def make_candidates(base: pd.DataFrame, elec: pd.DataFrame) -> pd.DataFrame:
    x = base.merge(
        elec[
            [
                "province_full",
                "city",
                "year",
                "electricity_months",
                "leakage_ok_months",
                "industrial_kwh",
                "electricity_share",
                "source_publication_min",
                "source_publication_max",
            ]
        ],
        on=["province_full", "city", "year"],
        how="left",
    )
    x["electricity_share"] = x["electricity_share"].fillna(x["baseline_share"])
    x["electricity_months"] = pd.to_numeric(x["electricity_months"], errors="coerce").fillna(0)
    x["leakage_ok_months"] = pd.to_numeric(x["leakage_ok_months"], errors="coerce").fillna(0)
    rows = []
    for bw in BASELINE_WEIGHT_GRID:
        y = x.copy()
        y["baseline_weight"] = bw
        y["indicator_weight"] = 1.0 - bw
        raw = bw * y["baseline_share"] + (1.0 - bw) * y["electricity_share"]
        raw = raw.clip(lower=0)
        raw_sum = raw.groupby([y["province_full"], y["year"]]).transform("sum")
        y["candidate_share"] = np.where(raw_sum.gt(0), raw / raw_sum, y["baseline_share"])
        # Primary parent uses the original model's province-year predicted total.
        y["candidate_predicted_eok"] = y["parent_predicted_eok"] * y["candidate_share"]
        y["scenario"] = f"electricity_share_baseline_weight_{bw:.2f}"
        rows.append(y)
    return pd.concat(rows, ignore_index=True)


def summarize_candidates(cand: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario, g in cand.groupby("scenario"):
        rows.append(metric(g, "candidate_predicted_eok", scenario))
    out = pd.DataFrame(rows).sort_values(["wape_pct", "over10_cells", "max_ape_pct"])
    return out


def metrics_for_years(cand: pd.DataFrame, scenario: str, years: list[int]) -> dict[str, Any]:
    x = cand[cand["scenario"].eq(scenario) & cand["year"].isin(years)].copy()
    return metric(x, "candidate_predicted_eok", scenario)


def rolling_holdout(cand: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenarios = sorted(cand["scenario"].unique())
    rows = []
    selected_parts = []
    baseline_scenario = "electricity_share_baseline_weight_1.00"
    for holdout in [2022, 2023]:
        train_years = [y for y in [2021, 2022, 2023] if y < holdout and y in set(cand["year"])]
        holdout_years = [holdout]
        train_base = metrics_for_years(cand, baseline_scenario, train_years)
        hold_base = metrics_for_years(cand, baseline_scenario, holdout_years)
        safe = []
        for scenario in scenarios:
            if scenario == baseline_scenario:
                continue
            train = metrics_for_years(cand, scenario, train_years)
            is_safe = (
                train["wape_pct"] <= train_base["wape_pct"]
                and train["over10_cells"] <= train_base["over10_cells"]
                and train["over20_cells"] <= train_base["over20_cells"]
                and train["large_actual_over10_cells"] <= train_base["large_actual_over10_cells"]
                and train["max_ape_pct"] <= train_base["max_ape_pct"]
            )
            safe.append({**train, "holdout_year": holdout, "train_years": ",".join(map(str, train_years)), "train_safe": is_safe})
        safe_df = pd.DataFrame(safe)
        if not safe_df.empty and safe_df["train_safe"].any():
            chosen = safe_df[safe_df["train_safe"]].sort_values(["wape_pct", "over10_cells", "max_ape_pct"]).iloc[0]["scenario"]
            reason = "train_guardrail_pass"
        else:
            chosen = baseline_scenario
            reason = "fallback_no_nonbaseline_train_safe_candidate"
        hold = metrics_for_years(cand, str(chosen), holdout_years)
        rows.append(
            {
                "holdout_year": holdout,
                "train_years": ",".join(map(str, train_years)),
                "selected_scenario": chosen,
                "selection_reason": reason,
                "baseline_wape_pct": hold_base["wape_pct"],
                "selected_wape_pct": hold["wape_pct"],
                "wape_delta_pp": hold["wape_pct"] - hold_base["wape_pct"],
                "baseline_over10_cells": hold_base["over10_cells"],
                "selected_over10_cells": hold["over10_cells"],
                "baseline_over20_cells": hold_base["over20_cells"],
                "selected_over20_cells": hold["over20_cells"],
                "baseline_large_actual_over10_cells": hold_base["large_actual_over10_cells"],
                "selected_large_actual_over10_cells": hold["large_actual_over10_cells"],
                "baseline_max_ape_pct": hold_base["max_ape_pct"],
                "selected_max_ape_pct": hold["max_ape_pct"],
            }
        )
        part = cand[cand["scenario"].eq(str(chosen)) & cand["year"].eq(holdout)].copy()
        part["selected_by_rolling_policy"] = True
        selected_parts.append(part)
    return pd.DataFrame(rows), pd.concat(selected_parts, ignore_index=True)


def coverage_summary(base: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    cov = cand[cand["baseline_weight"].eq(1.0)].copy()
    return (
        cov.groupby("year", as_index=False)
        .agg(
            validation_cells=("city", "size"),
            province_count=("province_full", "nunique"),
            city_count=("city", "nunique"),
            electricity_full12_cells=("electricity_months", lambda s: int((pd.to_numeric(s, errors="coerce") >= 12).sum())),
            electricity_leakage_ok12_cells=("leakage_ok_months", lambda s: int((pd.to_numeric(s, errors="coerce") >= 12).sum())),
            actual_sum_eok=("actual_eok", "sum"),
            baseline_predicted_sum_eok=("predicted_eok", "sum"),
            primary_parent_sum_eok=("predicted_eok", "sum"),
        )
    )


def oracle_parent_diagnostic(cand: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario, g in cand.groupby("scenario"):
        x = g.copy()
        x["oracle_parent_predicted_eok"] = x["parent_actual_eok"] * x["candidate_share"]
        m = metric(x, "oracle_parent_predicted_eok", scenario)
        rows.append(m)
    out = pd.DataFrame(rows).sort_values("wape_pct")
    out["diagnostic_only"] = True
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_base()
    elec = load_electricity()
    cand = make_candidates(base, elec)
    coverage = coverage_summary(base, cand)
    factory_cov = factory_diagnostic(base)
    candidate_summary = summarize_candidates(cand)
    rolling, selected_detail = rolling_holdout(cand)
    oracle = oracle_parent_diagnostic(cand)

    cand.to_csv(OUT / "phase259_mfg_electricity_candidate_detail.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(OUT / "phase259_mfg_electricity_coverage_summary.csv", index=False, encoding="utf-8-sig")
    factory_cov.to_csv(OUT / "phase259_mfg_factory_snapshot_diagnostic.csv", index=False, encoding="utf-8-sig")
    candidate_summary.to_csv(OUT / "phase259_mfg_electricity_candidate_summary.csv", index=False, encoding="utf-8-sig")
    rolling.to_csv(OUT / "phase259_mfg_electricity_rolling_holdout_summary.csv", index=False, encoding="utf-8-sig")
    selected_detail.to_csv(OUT / "phase259_mfg_electricity_rolling_selected_detail.csv", index=False, encoding="utf-8-sig")
    oracle.to_csv(OUT / "phase259_mfg_electricity_oracle_parent_diagnostic.csv", index=False, encoding="utf-8-sig")

    best_all = candidate_summary.sort_values("wape_pct").head(8)
    report = f"""# Phase259 광업·제조업 전력 share holdout 검증

생성시각: {CREATED_AT}

## 1. 목적

Phase256에서 광업·제조업 tail의 자료준비도는 확인했지만 route는 채택하지 않았다. 이번 실험은 2021~2023 공개 actual 구간에서 시군구별 산업용 전력 share가 기존 광업·제조업 공간배분을 개선하는지 rolling holdout으로 점검한다. 새 route를 채택하지 않는다.

## 2. 누수 방지 설계

| 항목 | 설정 |
| --- | --- |
| 대상 | `광업, 제조업` 시군구×연간 GVA, 2021~2023 |
| primary parent total | 기존 baseline의 시도×연도 예측 합계 유지 |
| 금지 | target 시군구 actual 합계로 province-year parent를 재주입해 성능 주장 금지 |
| 후보식 | `baseline_weight × 기존 share + (1-baseline_weight) × 산업용 전력 share` |
| grid | `{', '.join(f'{x:.2f}' for x in BASELINE_WEIGHT_GRID)}` |
| rolling 선택 | 2021→2022, 2021~2022→2023. 훈련연도에서 WAPE·10%·20%·대형 actual 10%·max APE 모두 비악화일 때만 후보 선택 |
| 공장등록 | 현재 snapshot 성격이므로 성능 route가 아니라 coverage 진단만 수행 |

## 3. coverage

{md_table(coverage, digits=2)}

## 4. 공장등록 snapshot 진단

{md_table(factory_cov, digits=2)}

## 5. 전체기간 후보 성능 탐색표

이 표는 discovery용이다. 같은 기간 전체 actual로 최선 후보를 고른 것이므로 route 채택 근거가 아니다.

{md_table(best_all, digits=3)}

## 6. rolling holdout 결과

{md_table(rolling, digits=3)}

## 7. actual parent oracle 진단

이 표는 순수 공간배분 한계 진단이다. target children actual의 합계를 parent로 재주입하므로 운영 성능으로 사용하지 않는다.

{md_table(oracle.head(5), digits=3)}

## 8. 판정

1. 산업용 전력은 2021~2023 공개 actual 구간의 모든 광업·제조업 검증 셀에 12개월 단위로 연결된다.
2. 전체기간 discovery에서도 산업용 전력 share 단독 혼합은 기존 share보다 나아지지 않았고, 전력 비중을 높일수록 WAPE·초과오차 셀이 크게 악화됐다.
3. rolling holdout에서도 baseline 이외 후보가 훈련연도 guardrail을 통과하지 못해 baseline으로 fallback했다.
4. 공장등록은 연결률이 높아 구조 진단에는 유용하지만, 현재 snapshot/vintage 한계 때문에 2021~2023 성능 route로 쓰지 않는다.
5. 다음 승격 조건은 제조업 대형 도시를 discovery/holdout으로 분리하고, 전력·공장규모 interaction 후보를 사전 고정한 뒤 WAPE뿐 아니라 10%/20% 초과 셀과 max APE까지 비악화시키는 것이다.

## 9. 산출물

- `nationwide/outputs/phase259_mfg_electricity_candidate_detail.csv`
- `nationwide/outputs/phase259_mfg_electricity_coverage_summary.csv`
- `nationwide/outputs/phase259_mfg_factory_snapshot_diagnostic.csv`
- `nationwide/outputs/phase259_mfg_electricity_candidate_summary.csv`
- `nationwide/outputs/phase259_mfg_electricity_rolling_holdout_summary.csv`
- `nationwide/outputs/phase259_mfg_electricity_rolling_selected_detail.csv`
- `nationwide/outputs/phase259_mfg_electricity_oracle_parent_diagnostic.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(rolling.to_string(index=False))


if __name__ == "__main__":
    main()
