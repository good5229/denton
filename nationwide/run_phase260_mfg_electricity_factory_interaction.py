#!/usr/bin/env python3
"""Phase260: manufacturing electricity × factory-structure interaction holdout.

This is a retrospective holdout experiment, not a route adoption.  Factory
snapshot variables are treated as static structural moderators only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase260_mfg_electricity_factory_interaction.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")

BASE = OUT / "annual_sigungu_activity_error_audit.csv"
ELEC = ROOT / "data" / "processed" / "municipality_electricity_features_2021_2023.csv"
FACTORY = ROOT / "data" / "raw" / "public_data_portal" / "factory_full_snapshot_15106170_download.csv"

BASELINE_WEIGHTS = [0.95, 0.90, 0.75]

KSIC_BUCKETS = {
    "materials": {19, 20, 22, 23, 24, 25},
    "machinery_transport_electronics": {26, 27, 28, 29, 30, 31},
    "consumer_light": {10, 11, 12, 13, 14, 15, 16, 17, 18, 32},
}


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


def province_key(name: object) -> str:
    text = "" if pd.isna(name) else str(name)
    return text.replace("전라북도", "전북특별자치도").replace("강원도", "강원특별자치도")


def factory_city_rollup(province: object, city: object) -> str:
    prov = "" if pd.isna(province) else str(province).strip()
    text = "" if pd.isna(city) else str(city).strip()
    if "세종" in prov and not text:
        return "세종시"
    first = text.split()[0] if text else ""
    if first.endswith("시"):
        return first
    return text


def ksic_bucket(code: object) -> str:
    s = "" if pd.isna(code) else str(code).strip()
    try:
        div = int(s[:2])
    except Exception:
        return "unresolved"
    for name, divs in KSIC_BUCKETS.items():
        if div in divs:
            return name
    if 10 <= div <= 34:
        return "other_manufacturing"
    return "unresolved"


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


def load_base() -> pd.DataFrame:
    x = pd.read_csv(BASE)
    x = x[x["activity"].eq("광업, 제조업") & x["year"].between(2021, 2023)].copy()
    for c in ["predicted_eok", "actual_eok"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    parent = x.groupby(["province_full", "year"], as_index=False).agg(parent_predicted_eok=("predicted_eok", "sum"), parent_actual_eok=("actual_eok", "sum"))
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
    annual = e.groupby(["province_full", "city", "year"], as_index=False).agg(
        electricity_months=("observation_period", "nunique"),
        leakage_ok_months=("leakage_ok", "sum"),
        industrial_kwh=("industrial_kwh", "sum"),
    )
    return annual


def load_factory_structure() -> pd.DataFrame:
    f = read_csv_fallback(FACTORY)
    f["province_full"] = f["시도명"].map(province_key)
    f["city"] = [factory_city_rollup(p, c) for p, c in zip(f["시도명"], f["시군구명"], strict=False)]
    for c in ["종업원합계", "제조시설면적"]:
        f[c] = pd.to_numeric(f[c], errors="coerce").fillna(0).clip(lower=0)
    f["bucket"] = f["대표업종"].map(ksic_bucket)
    f["large_flag"] = f["공장규모"].astype(str).eq("대기업")
    f["large_employee"] = np.where(f["large_flag"], f["종업원합계"], 0.0)
    f["large_area"] = np.where(f["large_flag"], f["제조시설면적"], 0.0)
    agg = f.groupby(["province_full", "city"], as_index=False).agg(
        factory_rows=("회사명", "count"),
        employee_sum=("종업원합계", "sum"),
        mfg_area_sum=("제조시설면적", "sum"),
        large_employee_sum=("large_employee", "sum"),
        large_area_sum=("large_area", "sum"),
    )
    bucket = (
        f.pivot_table(index=["province_full", "city"], columns="bucket", values="종업원합계", aggfunc="sum", fill_value=0)
        .reset_index()
    )
    for b in ["materials", "machinery_transport_electronics", "consumer_light", "other_manufacturing", "unresolved"]:
        if b not in bucket:
            bucket[b] = 0.0
    out = agg.merge(bucket, on=["province_full", "city"], how="left")
    out["large_employee_ratio"] = np.where(out["employee_sum"].gt(0), out["large_employee_sum"] / out["employee_sum"], 0.0)
    out["large_area_ratio"] = np.where(out["mfg_area_sum"].gt(0), out["large_area_sum"] / out["mfg_area_sum"], 0.0)
    bucket_total = out[["materials", "machinery_transport_electronics", "consumer_light", "other_manufacturing", "unresolved"]].sum(axis=1)
    for b in ["materials", "machinery_transport_electronics", "consumer_light"]:
        out[f"{b}_employee_share"] = np.where(bucket_total.gt(0), out[b] / bucket_total, 0.0)
    out["top_bucket_share"] = np.where(
        bucket_total.gt(0),
        out[["materials", "machinery_transport_electronics", "consumer_light", "other_manufacturing", "unresolved"]].max(axis=1) / bucket_total,
        0.0,
    )
    return out


def add_shares(x: pd.DataFrame, value_col: str, share_col: str) -> pd.Series:
    total = x.groupby(["province_full", "year"])[value_col].transform("sum")
    return np.where(total.gt(0), x[value_col] / total, np.nan)


def make_feature_frame(base: pd.DataFrame) -> pd.DataFrame:
    elec = load_electricity()
    factory = load_factory_structure()
    x = base.merge(elec, on=["province_full", "city", "year"], how="left").merge(factory, on=["province_full", "city"], how="left")
    for c in [
        "industrial_kwh",
        "electricity_months",
        "leakage_ok_months",
        "employee_sum",
        "mfg_area_sum",
        "large_employee_ratio",
        "large_area_ratio",
        "materials_employee_share",
        "machinery_transport_electronics_employee_share",
        "consumer_light_employee_share",
        "top_bucket_share",
        "factory_rows",
    ]:
        x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0)
    x["electricity_share"] = add_shares(x, "industrial_kwh", "electricity_share")
    x["employee_share"] = add_shares(x, "employee_sum", "employee_share")
    x["area_share"] = add_shares(x, "mfg_area_sum", "area_share")
    # Pre-registered static factory moderators.
    x["large_factory_multiplier"] = 1.0 + 0.5 * x["large_employee_ratio"].clip(0, 1)
    x["materials_multiplier"] = 1.0 + 0.25 * x["materials_employee_share"].clip(0, 1)
    x["machinery_multiplier"] = 1.0 + 0.25 * x["machinery_transport_electronics_employee_share"].clip(0, 1)
    x["concentration_multiplier"] = 1.0 + 0.25 * x["top_bucket_share"].clip(0, 1)
    x["elec_x_large"] = x["industrial_kwh"] * x["large_factory_multiplier"]
    x["elec_x_materials"] = x["industrial_kwh"] * x["materials_multiplier"]
    x["elec_x_machinery"] = x["industrial_kwh"] * x["machinery_multiplier"]
    x["elec_x_concentration"] = x["industrial_kwh"] * x["concentration_multiplier"]
    x["emp_area_geomean"] = np.sqrt(x["employee_sum"].clip(lower=0) * x["mfg_area_sum"].clip(lower=0))
    x["elec_emp_area_geomean"] = np.cbrt(
        x["industrial_kwh"].clip(lower=0) * x["employee_sum"].clip(lower=0) * x["mfg_area_sum"].clip(lower=0)
    )
    for col in ["elec_x_large", "elec_x_materials", "elec_x_machinery", "elec_x_concentration", "emp_area_geomean", "elec_emp_area_geomean"]:
        x[f"{col}_share"] = add_shares(x, col, f"{col}_share")
        x[f"{col}_share"] = pd.Series(x[f"{col}_share"], index=x.index).fillna(x["baseline_share"])
    return x


def make_candidates(features: pd.DataFrame) -> pd.DataFrame:
    indicators = [
        ("employee_share", "factory_employee_share"),
        ("area_share", "factory_area_share"),
        ("elec_x_large_share", "electricity_x_large_factory"),
        ("elec_x_materials_share", "electricity_x_materials"),
        ("elec_x_machinery_share", "electricity_x_machinery_transport_electronics"),
        ("elec_x_concentration_share", "electricity_x_top_bucket_concentration"),
        ("emp_area_geomean_share", "factory_emp_area_geomean"),
        ("elec_emp_area_geomean_share", "electricity_factory_emp_area_geomean"),
    ]
    rows = []
    base = features.copy()
    base["scenario"] = "baseline"
    base["baseline_weight"] = 1.0
    base["indicator"] = "baseline"
    base["candidate_share"] = base["baseline_share"]
    base["candidate_predicted_eok"] = base["parent_predicted_eok"] * base["candidate_share"]
    rows.append(base)
    for col, name in indicators:
        for bw in BASELINE_WEIGHTS:
            y = features.copy()
            y["indicator"] = name
            y["baseline_weight"] = bw
            raw = bw * y["baseline_share"] + (1 - bw) * y[col].fillna(y["baseline_share"])
            raw = raw.clip(lower=0)
            raw_sum = raw.groupby([y["province_full"], y["year"]]).transform("sum")
            y["candidate_share"] = np.where(raw_sum.gt(0), raw / raw_sum, y["baseline_share"])
            y["candidate_predicted_eok"] = y["parent_predicted_eok"] * y["candidate_share"]
            y["scenario"] = f"{name}_baseline_weight_{bw:.2f}"
            rows.append(y)
    return pd.concat(rows, ignore_index=True)


def summarize_candidates(cand: pd.DataFrame) -> pd.DataFrame:
    rows = [metric(g, "candidate_predicted_eok", s) for s, g in cand.groupby("scenario")]
    return pd.DataFrame(rows).sort_values(["wape_pct", "over10_cells", "max_ape_pct"])


def metrics_for_years(cand: pd.DataFrame, scenario: str, years: list[int]) -> dict[str, Any]:
    x = cand[cand["scenario"].eq(scenario) & cand["year"].isin(years)].copy()
    return metric(x, "candidate_predicted_eok", scenario)


def rolling_holdout(cand: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenarios = sorted(s for s in cand["scenario"].unique() if s != "baseline")
    rows = []
    selected_parts = []
    for holdout in [2022, 2023]:
        train_years = [y for y in [2021, 2022, 2023] if y < holdout and y in set(cand["year"])]
        holdout_years = [holdout]
        train_base = metrics_for_years(cand, "baseline", train_years)
        hold_base = metrics_for_years(cand, "baseline", holdout_years)
        safe_rows = []
        for scenario in scenarios:
            train = metrics_for_years(cand, scenario, train_years)
            safe = (
                train["wape_pct"] <= train_base["wape_pct"]
                and train["over10_cells"] <= train_base["over10_cells"]
                and train["over20_cells"] <= train_base["over20_cells"]
                and train["large_actual_over10_cells"] <= train_base["large_actual_over10_cells"]
                and train["max_ape_pct"] <= train_base["max_ape_pct"]
            )
            safe_rows.append({**train, "train_safe": safe})
        safe_df = pd.DataFrame(safe_rows)
        if not safe_df.empty and safe_df["train_safe"].any():
            chosen = safe_df[safe_df["train_safe"]].sort_values(["wape_pct", "over10_cells", "max_ape_pct"]).iloc[0]["scenario"]
            reason = "train_guardrail_pass"
        else:
            chosen = "baseline"
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


def coverage_summary(features: pd.DataFrame) -> pd.DataFrame:
    return features.groupby("year", as_index=False).agg(
        validation_cells=("city", "size"),
        electricity_full12_cells=("electricity_months", lambda s: int((pd.to_numeric(s, errors="coerce") >= 12).sum())),
        electricity_leakage_ok12_cells=("leakage_ok_months", lambda s: int((pd.to_numeric(s, errors="coerce") >= 12).sum())),
        cells_with_factory=("factory_rows", lambda s: int((pd.to_numeric(s, errors="coerce").fillna(0) > 0).sum())),
        actual_sum_eok=("actual_eok", "sum"),
        baseline_predicted_sum_eok=("predicted_eok", "sum"),
    )


def feature_summary(features: pd.DataFrame) -> pd.DataFrame:
    return features.groupby("year", as_index=False).agg(
        employee_sum=("employee_sum", "sum"),
        mfg_area_sum=("mfg_area_sum", "sum"),
        avg_large_employee_ratio=("large_employee_ratio", "mean"),
        avg_materials_share=("materials_employee_share", "mean"),
        avg_machinery_share=("machinery_transport_electronics_employee_share", "mean"),
        avg_top_bucket_share=("top_bucket_share", "mean"),
    )


def oracle_parent_diagnostic(cand: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario, g in cand.groupby("scenario"):
        x = g.copy()
        x["oracle_parent_predicted_eok"] = x["parent_actual_eok"] * x["candidate_share"]
        rows.append(metric(x, "oracle_parent_predicted_eok", scenario))
    out = pd.DataFrame(rows).sort_values("wape_pct")
    out["diagnostic_only"] = True
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_base()
    features = make_feature_frame(base)
    cand = make_candidates(features)
    coverage = coverage_summary(features)
    feature_cov = feature_summary(features)
    candidate_summary = summarize_candidates(cand)
    rolling, selected = rolling_holdout(cand)
    oracle = oracle_parent_diagnostic(cand)

    features.to_csv(OUT / "phase260_mfg_interaction_feature_frame.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(OUT / "phase260_mfg_interaction_coverage_summary.csv", index=False, encoding="utf-8-sig")
    feature_cov.to_csv(OUT / "phase260_mfg_interaction_factory_feature_summary.csv", index=False, encoding="utf-8-sig")
    cand.to_csv(OUT / "phase260_mfg_interaction_candidate_detail.csv", index=False, encoding="utf-8-sig")
    candidate_summary.to_csv(OUT / "phase260_mfg_interaction_candidate_summary.csv", index=False, encoding="utf-8-sig")
    rolling.to_csv(OUT / "phase260_mfg_interaction_rolling_holdout_summary.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase260_mfg_interaction_rolling_selected_detail.csv", index=False, encoding="utf-8-sig")
    oracle.to_csv(OUT / "phase260_mfg_interaction_oracle_parent_diagnostic.csv", index=False, encoding="utf-8-sig")

    best = candidate_summary.head(12)
    report = f"""# Phase260 광업·제조업 전력×공장구조 interaction holdout

생성시각: {CREATED_AT}

## 1. 목적

Phase259에서 산업용 전력 share 단독혼합은 baseline을 이기지 못했다. 이번 실험은 전력에 공장규모·업종구성 moderator를 결합한 사전정의 interaction 후보가 rolling holdout에서 기준선을 넘는지 점검한다. 공장등록은 current snapshot이므로 strict nowcast route가 아니라 retrospective diagnostic/refinement 후보로만 사용한다.

## 2. 사전정의 설계

| 항목 | 설정 |
| --- | --- |
| 대상 | `광업, 제조업` 시군구×연간 GVA, 2021~2023 |
| primary parent total | 기존 baseline의 시도×연도 예측 합계 유지 |
| 금지 | target actual parent 재주입, city-specific boost, sparse 대표업종 직접학습 |
| factory 사용 | 2021~2023 공통 정적 구조 moderator. 연도별 공장 stock 변화로 해석 금지 |
| KSIC bucket | 소재형, 기계·전기·전자·운송장비형, 소비재·경공업형, 기타, 미해결 |
| 후보 | 공장 종업원 share, 제조시설면적 share, 전력×대기업비중, 전력×소재형, 전력×기계·전자·운송장비형, 전력×업종집중도, 공장 종업원×면적, 전력×종업원×면적 |
| baseline weight | `{', '.join(f'{x:.2f}' for x in BASELINE_WEIGHTS)}` |
| rolling 선택 | 2021→2022, 2021~2022→2023. 훈련연도에서 WAPE·10%·20%·대형 actual 10%·max APE 모두 비악화일 때만 선택 |

## 3. coverage

{md_table(coverage, digits=2)}

## 4. 공장구조 feature 요약

{md_table(feature_cov, digits=3)}

## 5. 전체기간 후보 성능 탐색표

이 표는 discovery용이며 route 채택 근거가 아니다.

{md_table(best, digits=3)}

## 6. rolling holdout 결과

{md_table(rolling, digits=3)}

## 7. actual parent oracle 진단

운영 성능이 아니라 순수 공간배분 한계 진단이다.

{md_table(oracle.head(8), digits=3)}

## 8. 판정

1. 전력×공장구조 interaction은 전력 단독보다 훨씬 보수적인 후보지만, 공장등록 snapshot 한계 때문에 운영 route로 채택하지 않는다.
2. rolling holdout에서 baseline 이외 후보가 guardrail을 통과하지 못하면 baseline으로 fallback한다.
3. 만약 특정 후보가 훈련 gate를 통과하더라도 2023 coverage가 11개 시도/149셀로 축소되어 있으므로, 추가 외부연도 또는 city holdout 확인 전에는 채택하지 않는다.
4. 다음 자료 개선 우선순위는 공장등록 vintage/폐업·변경이력, 제조업 중분류 금액형 구조자료, 대형사업장/산단 단위 생산·출하·투자 자료다.

## 9. 산출물

- `nationwide/outputs/phase260_mfg_interaction_feature_frame.csv`
- `nationwide/outputs/phase260_mfg_interaction_coverage_summary.csv`
- `nationwide/outputs/phase260_mfg_interaction_factory_feature_summary.csv`
- `nationwide/outputs/phase260_mfg_interaction_candidate_detail.csv`
- `nationwide/outputs/phase260_mfg_interaction_candidate_summary.csv`
- `nationwide/outputs/phase260_mfg_interaction_rolling_holdout_summary.csv`
- `nationwide/outputs/phase260_mfg_interaction_rolling_selected_detail.csv`
- `nationwide/outputs/phase260_mfg_interaction_oracle_parent_diagnostic.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(rolling.to_string(index=False))


if __name__ == "__main__":
    main()
