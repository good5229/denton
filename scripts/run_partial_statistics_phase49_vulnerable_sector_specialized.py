#!/usr/bin/env python3
"""Phase49 vulnerable-industry specialized allocation experiments.

This script runs the four experiments requested after Phase48:

1. Agriculture small-category allocation using city-level detailed KSIC census
   shares, benchmarked against the general activity allocation.
2. Construction allocation using a BOK-style order-to-work-done progression
   signal: building orders spread over 12 quarters and civil engineering over
   24 quarters, benchmarked against actual province-level construction GVA.
3. Real-estate readiness and first-pass feature coverage audit from free local
   BuildingHub-derived features.
4. Transport/warehouse readiness audit from the free local transport feature
   table.

The report intentionally distinguishes independent validation from calibrated
or readiness-only evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
RUN_ID = "partial_statistics_estimation_phase49_vulnerable_sector_specialized"


REGION_RENAME = {
    "강원도": "강원특별자치도",
    "전라북도": "전북특별자치도",
}


@dataclass(frozen=True)
class OutputPaths:
    agri: Path = DATA / "partial_stats_phase49_agriculture_small_validation.csv"
    construction_quarterly: Path = DATA / "partial_stats_phase49_construction_workdone_signal.csv"
    construction_validation: Path = DATA / "partial_stats_phase49_construction_signal_validation.csv"
    construction_summary: Path = DATA / "partial_stats_phase49_construction_signal_summary.csv"
    real_estate: Path = DATA / "partial_stats_phase49_real_estate_readiness.csv"
    transport: Path = DATA / "partial_stats_phase49_transport_readiness.csv"
    status: Path = DATA / "partial_stats_phase49_status.json"
    report: Path = REPORTS / "partial_statistics_estimation_phase49_vulnerable_sector_specialized.md"


OUT = OutputPaths()


def read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def safe_share(values: pd.Series) -> pd.Series:
    total = float(values.sum())
    if not np.isfinite(total) or total <= 0:
        return pd.Series(np.nan, index=values.index)
    return values / total


def weighted_mae_pp(df: pd.DataFrame, pred_col: str, actual_col: str = "actual_share") -> float:
    return float((df[pred_col].sub(df[actual_col]).abs() * 100).mean())


def improvement_pct(baseline: float, candidate: float) -> float:
    if baseline <= 0 or not np.isfinite(baseline):
        return np.nan
    return (baseline - candidate) / baseline * 100


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_표시할 행 없음_"
    cols = list(df.columns)
    rows = ["| " + " | ".join(map(str, cols)) + " |"]
    rows.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(row[c]).replace("\n", "<br>") for c in cols) + " |")
    return "\n".join(rows)


def run_agriculture_small() -> tuple[pd.DataFrame, dict]:
    city_files = {
        "고양시": DATA / "partial_stats_phase41_goyang_2015_all_ksic.csv",
        "포항시": DATA / "partial_stats_phase42_pohang_2015_all_ksic.csv",
    }
    rows: list[dict] = []
    agri_small_codes = {"011", "014", "020", "031", "032"}
    for city, path in city_files.items():
        raw = read_csv(path)
        raw["value_numeric"] = pd.to_numeric(raw["value"], errors="coerce")
        raw["is_suppressed_or_non_numeric"] = raw["value_numeric"].isna() & raw["value"].notna()
        raw["c1_id_str"] = raw["c1_id"].astype(str).str.strip()
        small = raw[raw["c1_id_str"].isin(agri_small_codes)].copy()
        pivot = (
            small.pivot_table(index=["c1_id_str", "c1_nm"], columns="metric", values="value_numeric", aggfunc="sum")
            .reset_index()
            .rename_axis(None, axis=1)
        )
        suppression = (
            small.groupby(["c1_id_str", "c1_nm"], as_index=False)["is_suppressed_or_non_numeric"]
            .sum()
            .rename(columns={"is_suppressed_or_non_numeric": "suppressed_cell_count"})
        )
        pivot = pivot.merge(suppression, on=["c1_id_str", "c1_nm"], how="left")
        for col in ("establishments", "employees", "sales"):
            if col not in pivot:
                pivot[col] = 0.0
            pivot[col] = pd.to_numeric(pivot[col], errors="coerce").fillna(0.0)
        if pivot.empty:
            continue
        pivot["est_share"] = safe_share(pivot["establishments"])
        pivot["emp_share"] = safe_share(pivot["employees"])
        pivot["actual_share"] = safe_share(pivot["sales"])
        pivot["general_activity_share"] = 0.5 * pivot["est_share"] + 0.5 * pivot["emp_share"]
        pivot["uniform_share"] = 1.0 / len(pivot)
        pivot["specialized_sales_share"] = pivot["actual_share"]
        for _, r in pivot.iterrows():
            rows.append(
                {
                    "city": city,
                    "year": 2015,
                    "parent_industry": "농림어업",
                    "ksic_small_code": str(r["c1_id_str"]).zfill(3),
                    "industry_name": r["c1_nm"],
                    "establishments": float(r["establishments"]),
                    "employees": float(r["employees"]),
                    "sales": float(r["sales"]),
                    "suppressed_cell_count": int(r["suppressed_cell_count"]),
                    "actual_sales_share": float(r["actual_share"]),
                    "general_activity_share": float(r["general_activity_share"]),
                    "uniform_share": float(r["uniform_share"]),
                    "specialized_sales_share": float(r["specialized_sales_share"]),
                    "general_abs_error_pp": abs(float(r["general_activity_share"] - r["actual_share"])) * 100,
                    "uniform_abs_error_pp": abs(float(r["uniform_share"] - r["actual_share"])) * 100,
                    "specialized_abs_error_pp": abs(float(r["specialized_sales_share"] - r["actual_share"])) * 100,
                    "validation_type": "calibrated_lower_level_benchmark",
                    "caution": "소분류 매출구성으로 배분기준을 보정한 상한 성능이며, 독립 시점 검증은 추가 연도 소분류 매출/산출 자료가 필요"
                    + ("; 포항 일부 셀은 X 처리되어 0으로 보수 반영" if city == "포항시" else ""),
                }
            )
    out = pd.DataFrame(rows)
    complete = out[out["suppressed_cell_count"].eq(0)].copy()
    summary = {
        "cities": sorted(out["city"].unique().tolist()),
        "general_mae_pp": float(out["general_abs_error_pp"].mean()),
        "uniform_mae_pp": float(out["uniform_abs_error_pp"].mean()),
        "specialized_mae_pp": float(out["specialized_abs_error_pp"].mean()),
        "improvement_vs_general_pct": improvement_pct(
            float(out["general_abs_error_pp"].mean()), float(out["specialized_abs_error_pp"].mean())
        ),
        "complete_cell_general_mae_pp": float(complete["general_abs_error_pp"].mean()) if len(complete) else np.nan,
        "suppressed_cells": int(out["suppressed_cell_count"].sum()),
        "city_metrics": {
            city: {
                "general_mae_pp": float(g["general_abs_error_pp"].mean()),
                "specialized_mae_pp": float(g["specialized_abs_error_pp"].mean()),
                "suppressed_cells": int(g["suppressed_cell_count"].sum()),
                "validation_scope": "complete" if int(g["suppressed_cell_count"].sum()) == 0 else "partial_with_suppressed_cells",
            }
            for city, g in out.groupby("city")
        },
        "validation_type": "calibrated lower-level benchmark, not independent out-of-sample",
    }
    out.to_csv(OUT.agri, index=False, encoding="utf-8-sig")
    return out, summary


def quarter_to_period(q: int | str) -> pd.Period:
    s = str(q)
    year = int(s[:4])
    quarter = int(s[-2:])
    return pd.Period(f"{year}Q{quarter}", freq="Q")


def build_construction_workdone_signal() -> pd.DataFrame:
    raw = read_csv(DATA / "rolling_construction_orders_by_region_type.csv")
    raw = raw[raw["c1_nm"].isin([r for r in raw["c1_nm"].unique() if r not in ("전국", "수도권", "지방")])].copy()
    raw["region"] = raw["c1_nm"].replace(REGION_RENAME)
    raw["quarter"] = raw["prd_de"].map(quarter_to_period)
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce").fillna(0.0)
    typed = raw[raw["c2_nm"].isin(["건축", "토목"])].copy()

    records: list[dict] = []
    for _, r in typed.iterrows():
        horizon = 12 if r["c2_nm"] == "건축" else 24
        amount = float(r["value"]) / horizon
        for lag in range(horizon):
            target = r["quarter"] + lag
            records.append(
                {
                    "region": r["region"],
                    "quarter": str(target),
                    "year": int(target.year),
                    "source_quarter": str(r["quarter"]),
                    "construction_type": r["c2_nm"],
                    "workdone_signal": amount,
                }
            )
    signal = pd.DataFrame(records)
    q = (
        signal.groupby(["region", "quarter", "year", "construction_type"], as_index=False)["workdone_signal"]
        .sum()
        .sort_values(["year", "quarter", "region", "construction_type"])
    )
    q.to_csv(OUT.construction_quarterly, index=False, encoding="utf-8-sig")
    return q


def run_construction_validation() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    q_signal = build_construction_workdone_signal()
    work = (
        q_signal.groupby(["region", "year"], as_index=False)["workdone_signal"]
        .sum()
        .rename(columns={"workdone_signal": "workdone_signal_annual"})
    )

    orders = read_csv(DATA / "rolling_construction_orders_by_region_type.csv")
    orders = orders[orders["c2_nm"].eq("계") & ~orders["c1_nm"].isin(["전국", "수도권", "지방"])].copy()
    orders["region"] = orders["c1_nm"].replace(REGION_RENAME)
    orders["year"] = orders["prd_de"].astype(str).str[:4].astype(int)
    orders["value"] = pd.to_numeric(orders["value"], errors="coerce").fillna(0.0)
    raw_orders = (
        orders.groupby(["region", "year"], as_index=False)["value"].sum().rename(columns={"value": "raw_order_annual"})
    )

    actual = read_csv(DATA / "rolling_annual_grva_real.csv")
    actual = actual[
        actual["c2_id"].astype(str).eq("F00")
        & ~actual["c1_nm"].isin(["전국"])
        & actual["prd_de"].between(2015, 2023)
    ].copy()
    actual["region"] = actual["c1_nm"].replace(REGION_RENAME)
    actual = actual[["region", "prd_de", "value"]].rename(columns={"prd_de": "year", "value": "actual_gva"})
    actual["actual_gva"] = pd.to_numeric(actual["actual_gva"], errors="coerce")

    df = actual.merge(raw_orders, on=["region", "year"], how="inner").merge(work, on=["region", "year"], how="inner")
    shares = []
    for year, g in df.groupby("year"):
        g = g.copy()
        g["actual_share"] = safe_share(g["actual_gva"])
        g["raw_order_share"] = safe_share(g["raw_order_annual"])
        g["workdone_share"] = safe_share(g["workdone_signal_annual"])
        lag = (
            actual[actual["year"].eq(year - 1)][["region", "actual_gva"]]
            .rename(columns={"actual_gva": "lag_actual_gva"})
        )
        g = g.merge(lag, on="region", how="left")
        g["lag_actual_share"] = safe_share(g["lag_actual_gva"])
        g["hybrid_workdone_lag_share"] = 0.7 * g["workdone_share"] + 0.3 * g["lag_actual_share"]
        shares.append(g)
    val = pd.concat(shares, ignore_index=True)
    for col in ("raw_order_share", "workdone_share", "lag_actual_share", "hybrid_workdone_lag_share"):
        val[f"{col}_abs_error_pp"] = (val[col] - val["actual_share"]).abs() * 100
    val.to_csv(OUT.construction_validation, index=False, encoding="utf-8-sig")

    metric_rows = []
    for col, label in [
        ("raw_order_share", "당해 수주액 구성"),
        ("workdone_share", "건축12·토목24분기 기성전환"),
        ("lag_actual_share", "전년 실제 구성"),
        ("hybrid_workdone_lag_share", "기성전환70+전년실제30"),
    ]:
        metric_rows.append(
            {
                "method": label,
                "share_column": col,
                "mae_pp": float(val[f"{col}_abs_error_pp"].mean()),
                "median_ae_pp": float(val[f"{col}_abs_error_pp"].median()),
                "p90_ae_pp": float(val[f"{col}_abs_error_pp"].quantile(0.9)),
                "n": int(val[f"{col}_abs_error_pp"].notna().sum()),
            }
        )
    summary_df = pd.DataFrame(metric_rows).sort_values("mae_pp")
    raw_mae = float(summary_df.loc[summary_df["share_column"].eq("raw_order_share"), "mae_pp"].iloc[0])
    best = summary_df.iloc[0].to_dict()
    summary = {
        "years": [int(val["year"].min()), int(val["year"].max())],
        "regions": int(val["region"].nunique()),
        "best_method": best["method"],
        "best_mae_pp": float(best["mae_pp"]),
        "raw_order_mae_pp": raw_mae,
        "improvement_vs_raw_orders_pct": improvement_pct(raw_mae, float(best["mae_pp"])),
    }
    summary_df.to_csv(OUT.construction_summary, index=False, encoding="utf-8-sig")
    return val, summary_df, summary


def run_real_estate_readiness() -> tuple[pd.DataFrame, dict]:
    features = read_csv(DATA / "buildinghub_feature_table.csv")
    features["has_value"] = pd.to_numeric(features["feature_value"], errors="coerce").notna()
    keys = features["sigungu_feature_key"].astype(str)
    wanted = keys.str.contains("고양|포항", na=False)
    subset = features[wanted].copy()
    candidates = features[
        features["feature_name"].astype(str).str.contains("permit|floor|area|count|land|building", case=False, na=False)
    ].copy()

    rows = []
    for city in ["고양시", "포항시"]:
        city_features = features[keys.str.contains(city.replace("시", ""), na=False)].copy()
        rows.append(
            {
                "sector": "부동산업",
                "city": city,
                "usable_now": bool(len(city_features) > 0 and city_features["has_value"].any()),
                "feature_rows": int(len(city_features)),
                "non_null_feature_rows": int(city_features["has_value"].sum()) if len(city_features) else 0,
                "feature_names": ", ".join(sorted(city_features["feature_name"].dropna().astype(str).unique())[:8]),
                "available_resolution": "시군구-월" if len(city_features) else "현재 로컬 테이블에서 미확인",
                "validation_status": "성능검증 가능" if len(city_features) and city_features["has_value"].any() else "성능검증 보류",
                "reason": "고양/포항 건축물 인허가·면적 관측값 존재"
                if len(city_features) and city_features["has_value"].any()
                else "현재 로컬 BuildingHub 테이블에 해당 도시 관측값이 없어 부동산 특화모델 검증 불가",
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUT.real_estate, index=False, encoding="utf-8-sig")
    summary = {
        "total_rows": int(len(features)),
        "candidate_feature_rows": int(len(candidates)),
        "goyang_pohang_rows": int(len(subset)),
        "usable_cities": out[out["usable_now"]]["city"].tolist(),
        "status": "ready" if out["usable_now"].any() else "source_collection_required",
    }
    return out, summary


def run_transport_readiness() -> tuple[pd.DataFrame, dict]:
    features = read_csv(DATA / "korea_transport_access_features.csv")
    measure_cols = [c for c in features.columns if c.startswith("distance_to_")]
    features["non_null_measure_count"] = features[measure_cols].notna().sum(axis=1)
    rows = []
    for city in ["고양시", "포항시"]:
        city_features = features[features["sigungu_feature_key"].astype(str).str.contains(city.replace("시", ""), na=False)]
        rows.append(
            {
                "sector": "운수 및 창고업",
                "city": city,
                "usable_now": bool(len(city_features) > 0 and city_features["non_null_measure_count"].gt(0).any()),
                "feature_rows": int(len(city_features)),
                "non_null_measure_rows": int(city_features["non_null_measure_count"].gt(0).sum()) if len(city_features) else 0,
                "available_resolution": "시군구 정적 접근성" if len(city_features) else "현재 로컬 테이블에서 미확인",
                "validation_status": "성능검증 가능" if len(city_features) and city_features["non_null_measure_count"].gt(0).any() else "성능검증 보류",
                "reason": "거리형 접근성 관측값 존재"
                if len(city_features) and city_features["non_null_measure_count"].gt(0).any()
                else "현재 로컬 운수 접근성 테이블은 관측값이 비어 있어 물량 기반 특화모델 검증 불가",
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUT.transport, index=False, encoding="utf-8-sig")
    summary = {
        "total_rows": int(len(features)),
        "measure_columns": measure_cols,
        "non_null_measure_rows": int(features["non_null_measure_count"].gt(0).sum()),
        "usable_cities": out[out["usable_now"]]["city"].tolist(),
        "status": "ready" if out["usable_now"].any() else "source_collection_required",
    }
    return out, summary


def make_report(status: dict, agri: pd.DataFrame, construction_summary: pd.DataFrame, real_estate: pd.DataFrame, transport: pd.DataFrame) -> None:
    ag = status["agriculture_small"]
    co = status["construction"]
    re = status["real_estate"]
    tr = status["transport_warehouse"]
    construction_table = construction_summary.copy()
    construction_table["mae_pp"] = construction_table["mae_pp"].map(lambda x: f"{x:.3f}")
    construction_table["median_ae_pp"] = construction_table["median_ae_pp"].map(lambda x: f"{x:.3f}")
    construction_table["p90_ae_pp"] = construction_table["p90_ae_pp"].map(lambda x: f"{x:.3f}")

    top_agri = agri.sort_values("general_abs_error_pp", ascending=False).head(4)
    agri_table = top_agri[
        [
            "city",
            "industry_name",
            "actual_sales_share",
            "general_activity_share",
            "general_abs_error_pp",
            "specialized_abs_error_pp",
            "caution",
        ]
    ].copy()
    for c in ["actual_sales_share", "general_activity_share"]:
        agri_table[c] = agri_table[c].map(lambda x: f"{x*100:.1f}%")
    for c in ["general_abs_error_pp", "specialized_abs_error_pp"]:
        agri_table[c] = agri_table[c].map(lambda x: f"{x:.2f}%p")

    lines = [
        "# Phase49 취약 산업 특화 배분 실험",
        "",
        "## 결론 요약",
        "",
        f"- 농림어업 소분류: 고양시는 비공개 셀 없이 검증 가능했고, 일반 활동기준 평균오차 {ag['city_metrics']['고양시']['general_mae_pp']:.2f}%p를 소분류 매출구성 배분으로 0.00%p까지 낮출 수 있다. 단, 이는 같은 소분류 매출구성으로 보정한 하한/상한 성능이라 독립 검증은 추가 연도 자료가 필요하다.",
        f"- 포항시 농림어업: 비공개 셀 {ag['city_metrics']['포항시']['suppressed_cells']}개가 있어 부분 검증으로만 해석한다. 공모전·보고서에는 성능개선 수치보다 ‘비공개 하위셀 보완 필요’와 ‘농림어업 별도 배분 필요성’으로 쓰는 편이 안전하다.",
        f"- 건설업: 시도별 2015~2023 실제 건설업 부가가치 구성 검증에서 최선 방식은 `{co['best_method']}`이고 평균오차는 {co['best_mae_pp']:.3f}%p이다. 당해 수주액만 쓰는 방식({co['raw_order_mae_pp']:.3f}%p) 대비 {co['improvement_vs_raw_orders_pct']:.1f}% 개선된다.",
        f"- 부동산업: 현재 로컬 무료 BuildingHub 테이블 기준 고양·포항 직접 관측 행은 {re['goyang_pohang_rows']}개다. 즉시 성능검증은 {', '.join(re['usable_cities']) if re['usable_cities'] else '불가'}이며, 도시별 건축물 면적·용도·공시가격 또는 거래/전월세 자료 수집이 선행되어야 한다.",
        f"- 운수 및 창고업: 현재 로컬 운수 접근성 테이블의 유효 거리 관측 행은 {tr['non_null_measure_rows']}개다. 물량자료가 없어 즉시 성능 개선 검증은 보류한다.",
        "",
        "## 1. 농림어업 소분류 배분 및 외삽",
        "",
        "농림어업은 사업체수·종사자수 같은 일반 활동기준이 소분류 매출구성을 크게 빗나갔다. 따라서 중분류 또는 대분류 총액을 먼저 맞춘 뒤, 소분류에는 경제총조사 소분류 매출구성을 적용하는 방식이 타당하다. BOK 문서의 배분·외삽 논리를 적용하면, 새 연도 소분류 실제값이 없을 때 직전 기준연도 구성비를 유지하거나 상위 총액 변화율로 외삽할 수 있다.",
        "",
        markdown_table(agri_table),
        "",
        "검증 해석: 위 표의 특화 배분 오차 0은 독립 예측 성공이 아니라, 소분류 매출구성을 하위 배분기준으로 삼았을 때 상위합계 보존 조건 안에서 달성 가능한 기준선이다. 공모전 포스터에서는 “소분류 배분 안정화 가능” 정도로 쓰는 것이 안전하다.",
        "",
        "## 2. 건설업 수주액→기성 전환 실험",
        "",
        "건설업은 수주 시점과 실제 생산 시점이 다르므로 당해 수주액을 그대로 쓰면 시점 오차가 커진다. BOK 문서의 취지에 맞춰 건축 수주는 12분기, 토목 수주는 24분기에 나누어 진행되는 신호로 바꾸고, 이를 시도별 실제 건설업 부가가치 구성과 비교했다.",
        "",
        markdown_table(construction_table[["method", "mae_pp", "median_ae_pp", "p90_ae_pp", "n"]]),
        "",
        "검증 해석: 이 검증은 시도·연 단위 실제값을 사용한 독립 검증이다. 다만 수주액 자료가 시도 단위라서 고양시·포항시 행정동까지 직접 내려가는 공간 개선에는 추가 지역별 인허가·착공·준공·공사면적 자료가 필요하다.",
        "",
        "## 3. 부동산업 특화모델 판정",
        "",
        markdown_table(real_estate),
        "",
        "현재 로컬 자료만으로는 고양·포항 부동산업 성능 개선을 수치로 입증하기 어렵다. 적합한 무료 데이터는 건축물대장 또는 인허가의 용도별 연면적, 주택/상가 공시가격, 부동산 거래·전월세 신고 집계, 빈집·노후건축물 분포다.",
        "",
        "## 4. 운수 및 창고업 특화모델 판정",
        "",
        markdown_table(transport),
        "",
        "현재 로컬 접근성 테이블은 물량 관측값이 비어 있다. 운수 및 창고업 개선에는 버스·철도 승하차, 화물자동차/물류창고 등록, 항만 물동량, 택배·소화물 집계 같은 무료 행정자료가 필요하다.",
        "",
        "## 산출 파일",
        "",
        f"- `{OUT.agri.relative_to(ROOT)}`",
        f"- `{OUT.construction_quarterly.relative_to(ROOT)}`",
        f"- `{OUT.construction_validation.relative_to(ROOT)}`",
        f"- `{OUT.construction_summary.relative_to(ROOT)}`",
        f"- `{OUT.real_estate.relative_to(ROOT)}`",
        f"- `{OUT.transport.relative_to(ROOT)}`",
        f"- `{OUT.status.relative_to(ROOT)}`",
        "",
    ]
    OUT.report.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    agri, agri_summary = run_agriculture_small()
    construction_validation, construction_summary, construction_status = run_construction_validation()
    real_estate, real_estate_summary = run_real_estate_readiness()
    transport, transport_summary = run_transport_readiness()

    status = {
        "run_id": RUN_ID,
        "created_at": pd.Timestamp.now(tz="Asia/Seoul").isoformat(),
        "agriculture_small": agri_summary,
        "construction": construction_status,
        "real_estate": real_estate_summary,
        "transport_warehouse": transport_summary,
        "poster_implications": {
            "use": [
                "농림어업은 일반 사업체 기준이 아니라 소분류 매출구성/농지·어업 특화자료로 별도 배분",
                "건설업은 수주액을 생산시점으로 전환한 뒤 반영",
            ],
            "avoid": [
                "부동산·운수창고업의 성능 개선을 현 단계에서 수치로 단정",
                "프록시, actual, holdout 같은 은어 사용",
            ],
        },
    }
    OUT.status.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    make_report(status, agri, construction_summary, real_estate, transport)

    print(json.dumps(status, ensure_ascii=False, indent=2))
    print(f"report={OUT.report}")


if __name__ == "__main__":
    main()
