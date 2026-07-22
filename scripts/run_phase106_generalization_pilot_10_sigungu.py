#!/usr/bin/env python3
"""Phase106: 10-sigungu generalization pilot for flash/refinement GVA errors.

Full middle-industry actual-share validation currently exists only for Goyang
and Pohang.  This pilot therefore tests the nationally available layer:
sigungu × broad-industry × annual GVA actuals, with 2022 lag actual as a flash
baseline and 2023 business/employment structural allocation as a post-publication
refinement proxy.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase106_generalization_pilot_10_sigungu"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase106_generalization_pilot_10_sigungu.md"

GRVA = DATA / "expanded_sigungu_grva_real.csv"
BUSINESS = DATA / "kosis_business_feature_table.csv"


PARENT_NAME_TO_CODE = {
    "농업 임업 및 어업": "A00",
    "광업": "B00",
    "제조업": "C00",
    "전기 가스 증기 및 공기 조절 공급업": "D00",
    "전기 가스 증기 및 공기조절 공급업": "D00",
    "건설업": "F00",
    "도매 및 소매업": "G00",
    "운수 및 창고업": "H00",
    "숙박 및 음식점업": "I00",
    "정보통신업": "J00",
    "금융 및 보험업": "K00",
    "부동산업": "L00",
    "사업서비스업": "MN0",
    "공공 행정 국방 및 사회보장 행정": "O00",
    "공공행정 국방 및 사회보장 행정": "O00",
    "교육서비스업": "P00",
    "교육 서비스업": "P00",
    "보건업 및 사회복지서비스업": "Q00",
    "보건업 및 사회복지 서비스업": "Q00",
    "문화 및 기타 서비스업": "ERS",
    "문화 및 기타서비스업": "ERS",
}
PARENT_TO_LETTERS = {
    "A00": ["A"],
    "B00": ["B"],
    "C00": ["C"],
    "D00": ["D"],
    "ERS": ["E", "R", "S"],
    "F00": ["F"],
    "G00": ["G"],
    "H00": ["H"],
    "I00": ["I"],
    "J00": ["J"],
    "K00": ["K"],
    "L00": ["L"],
    "MN0": ["M", "N"],
    "O00": ["O"],
    "P00": ["P"],
    "Q00": ["Q"],
}


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "pp")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            value = row.get(key, "")
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}" if abs(value) < 100 else f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def load_actual() -> pd.DataFrame:
    g = pd.read_csv(GRVA, encoding="cp949")
    g = g.copy()
    g["year"] = pd.to_numeric(g.prd_de, errors="coerce").astype("Int64")
    g["area_code"] = pd.to_numeric(g.c1_id, errors="coerce").astype("Int64").astype(str)
    g["parent_code"] = g.c2_nm.astype(str).str.strip().map(PARENT_NAME_TO_CODE)
    g["actual_gva_eok"] = pd.to_numeric(g.value, errors="coerce") / 100.0
    g = g[g.parent_code.notna() & g.year.isin([2022, 2023])].copy()
    # Keep only codes that also exist in business feature table; this avoids
    # ambiguous Seoul-style legacy GRDP codes.
    b = pd.read_csv(BUSINESS, encoding="cp949", usecols=["area_code", "area_level"])
    sigungu_codes = set(b[b.area_level.eq("sigungu")].area_code.astype(str))
    g = g[g.area_code.isin(sigungu_codes)].copy()
    return g[["source_region", "area_code", "c1_nm", "year", "parent_code", "actual_gva_eok"]]


def choose_sample(actual: pd.DataFrame) -> pd.DataFrame:
    eligible = (
        actual[actual.year.eq(2023)]
        .groupby(["source_region", "area_code", "c1_nm"], as_index=False)
        .agg(parent_count=("parent_code", "nunique"), actual_sum_eok=("actual_gva_eok", "sum"))
    )
    eligible = eligible[eligible.parent_count.ge(10)].copy()
    # Stratified random: at most one from a broad region first, then fill.
    rng = np.random.default_rng(106)
    rows = []
    for region, group in eligible.groupby("source_region", sort=True):
        if group.empty:
            continue
        rows.append(group.sample(1, random_state=int(rng.integers(0, 1_000_000))))
    first_pass = pd.concat(rows, ignore_index=True) if rows else eligible.head(0)
    if len(first_pass) < 10:
        used = set(first_pass.area_code.astype(str))
        pool = eligible[~eligible.area_code.astype(str).isin(used)].copy()
        fill = pool.sample(min(10 - len(first_pass), len(pool)), random_state=106)
        sample = pd.concat([first_pass, fill], ignore_index=True)
    else:
        sample = first_pass
    return sample.sample(frac=1, random_state=106).head(10).sort_values(["source_region", "area_code"]).reset_index(drop=True)


def load_business(crosswalk: pd.DataFrame) -> pd.DataFrame:
    cols = ["year", "area_code", "area_name", "area_level", "industry_code", "metric", "value"]
    b = pd.read_csv(BUSINESS, encoding="cp949", usecols=cols)
    b = b[b.area_level.eq("sigungu") & b.year.eq(2023)].copy()
    b["area_code"] = b.area_code.astype(str)
    b = b.merge(crosswalk[["area_code", "source_region"]].drop_duplicates(), on="area_code", how="inner")
    b["industry_code"] = b.industry_code.astype(str)
    b = b[b.metric.isin(["establishments", "employees"])].copy()
    b["industry_letter"] = b.industry_code.str[0]
    frames = []
    for parent, letters in PARENT_TO_LETTERS.items():
        x = b[b.industry_letter.isin(letters)].copy()
        if x.empty:
            continue
        agg = (
            x.groupby(["source_region", "area_code", "area_name", "metric"], as_index=False)
            .value.sum()
            .assign(parent_code=parent)
        )
        frames.append(agg)
    out = pd.concat(frames, ignore_index=True)
    return out


def build_predictions(actual: pd.DataFrame, sample: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    crosswalk = actual[["source_region", "area_code", "c1_nm"]].drop_duplicates()
    business = load_business(crosswalk)
    target = actual[actual.year.eq(2023)].rename(columns={"actual_gva_eok": "actual_2023_eok"})
    lag = actual[actual.year.eq(2022)][["area_code", "parent_code", "actual_gva_eok"]].rename(columns={"actual_gva_eok": "flash_predicted_eok"})
    target = target.merge(lag, on=["area_code", "parent_code"], how="left")
    # Business/employment refinement: allocate the region's 2023 parent actual
    # by 2023 business structure.  This is a post-publication refinement proxy.
    metric_wide = business.pivot_table(
        index=["source_region", "area_code", "area_name", "parent_code"], columns="metric", values="value", aggfunc="sum"
    ).reset_index()
    for col in ["establishments", "employees"]:
        if col not in metric_wide:
            metric_wide[col] = np.nan
    metric_wide["est_share"] = metric_wide.establishments / metric_wide.groupby(["source_region", "parent_code"]).establishments.transform("sum")
    metric_wide["emp_share"] = metric_wide.employees / metric_wide.groupby(["source_region", "parent_code"]).employees.transform("sum")
    metric_wide["structure_share"] = metric_wide[["est_share", "emp_share"]].mean(axis=1).fillna(metric_wide.est_share).fillna(metric_wide.emp_share)
    region_total = (
        target.groupby(["source_region", "parent_code"], as_index=False)
        .actual_2023_eok.sum()
        .rename(columns={"actual_2023_eok": "region_parent_actual_2023_eok"})
    )
    metric_wide = metric_wide.merge(region_total, on=["source_region", "parent_code"], how="left")
    metric_wide["refined_predicted_eok"] = metric_wide.structure_share * metric_wide.region_parent_actual_2023_eok
    pred = target.merge(metric_wide[["area_code", "parent_code", "refined_predicted_eok"]], on=["area_code", "parent_code"], how="left")
    pred = pred.merge(sample[["area_code"]].assign(in_sample=True), on="area_code", how="inner")
    pred = pred.dropna(subset=["flash_predicted_eok", "refined_predicted_eok"]).copy()
    pred["flash_error_eok"] = (pred.flash_predicted_eok - pred.actual_2023_eok).abs()
    pred["refined_error_eok"] = (pred.refined_predicted_eok - pred.actual_2023_eok).abs()
    pred["flash_error_rate_pct"] = pred.flash_error_eok / pred.actual_2023_eok.replace(0, np.nan) * 100
    pred["refined_error_rate_pct"] = pred.refined_error_eok / pred.actual_2023_eok.replace(0, np.nan) * 100
    pred["refined_worse_than_flash"] = pred.refined_error_eok.gt(pred.flash_error_eok + 1e-9)
    summary = (
        pred.groupby(["source_region", "area_code", "c1_nm"], as_index=False)
        .agg(
            cells=("parent_code", "count"),
            actual_sum_eok=("actual_2023_eok", "sum"),
            flash_error_sum_eok=("flash_error_eok", "sum"),
            refined_error_sum_eok=("refined_error_eok", "sum"),
            refined_worse_cells=("refined_worse_than_flash", "sum"),
        )
    )
    summary["flash_wape_pct"] = summary.flash_error_sum_eok / summary.actual_sum_eok * 100
    summary["refined_wape_pct"] = summary.refined_error_sum_eok / summary.actual_sum_eok * 100
    summary["refined_minus_flash_pp"] = summary.refined_wape_pct - summary.flash_wape_pct
    overall = pd.DataFrame(
        [
            {
                "sample_sigungu": summary.area_code.nunique(),
                "cells": len(pred),
                "actual_sum_eok": pred.actual_2023_eok.sum(),
                "flash_error_sum_eok": pred.flash_error_eok.sum(),
                "refined_error_sum_eok": pred.refined_error_eok.sum(),
                "flash_wape_pct": pred.flash_error_eok.sum() / pred.actual_2023_eok.sum() * 100,
                "refined_wape_pct": pred.refined_error_eok.sum() / pred.actual_2023_eok.sum() * 100,
                "refined_worse_cells": int(pred.refined_worse_than_flash.sum()),
            }
        ]
    )
    return pred, summary, overall


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    actual = load_actual()
    sample = choose_sample(actual)
    pred, summary, overall = build_predictions(actual, sample)
    unavailable = pd.DataFrame(
        [
            {
                "needed_layer": "시군구×KSIC 중분류 actual share",
                "current_status": "고양·포항 holdout만 로컬 존재",
                "impact": "고양·포항과 동일한 중분류 집계검증은 10개 표본에 즉시 불가",
                "next_action": "각 지자체 사업체조사/경제총조사 중분류 매출·사업체·종사자 파일 수집 필요",
            },
            {
                "needed_layer": "공표일자 원장",
                "current_status": "GRDP·사업체조사 일반 공표시차는 확인, 파일별 게시일은 추가 크롤링 필요",
                "impact": "strict as-of 속보성 검증은 아직 불완전",
                "next_action": "KOSIS/지자체 게시일을 source vintage ledger로 고정",
            },
        ]
    )
    sample.to_csv(OUTDIR / "phase106_sample_10_sigungu.csv", index=False, encoding="utf-8-sig")
    pred.to_csv(OUTDIR / "phase106_broad_industry_flash_refinement_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase106_broad_industry_flash_refinement_summary.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUTDIR / "phase106_broad_industry_overall.csv", index=False, encoding="utf-8-sig")
    unavailable.to_csv(OUTDIR / "phase106_middle_validation_data_gap.csv", index=False, encoding="utf-8-sig")

    report = f"""# 임의 10개 시군구 전국 확장 파일럿

## 목적

고양·포항에서 사용한 중분류 집계검증을 전국 어디서나 적용할 수 있는지 확인하기 위한 1차 파일럿이다. 현재 로컬에는 고양·포항 외 중분류 actual share가 없고, 2023년 전국 시군구 사업체 구조자료도 광업·제조업 중심으로만 정밀화값이 구성되어 있다. 따라서 이번 파일럿은 전국적으로 즉시 가능한 `시군구×광업·제조업 대분류×연간 GVA` 층에서 속보성·정밀화 오차를 비교한다.

## 표본

광역시도 편중을 줄이기 위해 source_region별 1개 후보를 무작위 추출한 뒤 10개를 선택했다. 고양·포항은 제외하지 않았지만, 무작위 표본 결과에 따라 포함되지 않을 수 있다.

{md_table(sample, [("source_region", "광역"), ("area_code", "시군구코드"), ("c1_nm", "시군구"), ("parent_count", "대분류 수"), ("actual_sum_eok", "2023 실제합계 억원")], 20)}

## 광업·제조업 대분류 파일럿 결과

속보성은 2022년 같은 시군구×대분류 GVA를 2023년 추정치로 둔 lag 기준이다. 정밀화는 2023년 사업체수 구조로 광역 내 시군구 비중을 재배분한 사후 구조 기준이다. 현재 로컬의 2023년 시군구 사업체 구조자료는 광업·제조업 중분류 중심이므로, 이 표는 전 산업 중분류 본검증이 아니라 전국 확장 가능성의 하한 파일럿이다.

{md_table(overall, [("sample_sigungu", "표본 시군구"), ("cells", "셀"), ("actual_sum_eok", "실제합계 억원"), ("flash_error_sum_eok", "속보오차 억원"), ("refined_error_sum_eok", "정밀오차 억원"), ("flash_wape_pct", "속보 WAPE %"), ("refined_wape_pct", "정밀화 WAPE %"), ("refined_worse_cells", "정밀화 악화 셀")])}

## 시군구별 결과

{md_table(summary.sort_values("refined_wape_pct"), [("source_region", "광역"), ("area_code", "코드"), ("c1_nm", "시군구"), ("cells", "셀"), ("actual_sum_eok", "실제합계 억원"), ("flash_error_sum_eok", "속보오차 억원"), ("refined_error_sum_eok", "정밀오차 억원"), ("flash_wape_pct", "속보 WAPE %"), ("refined_wape_pct", "정밀화 WAPE %"), ("refined_minus_flash_pp", "정밀-속보 pp"), ("refined_worse_cells", "악화 셀")], 20)}

## 중분류 본검증 자료 공백

{md_table(unavailable, [("needed_layer", "필요 계층"), ("current_status", "현재 상태"), ("impact", "영향"), ("next_action", "다음 조치")])}

## 판정

1. 전국 10개 시군구로 확장할 때도 속보성과 정밀화를 분리해 계산하는 구조는 가능하다.
2. 다만 현재 파일럿은 광업·제조업 대분류 actual 기준이다. 고양·포항과 같은 전 산업 중분류 집계검증은 각 시군구의 중분류 actual share 또는 전 산업 중분류 사업체조사 파일을 추가 수집해야 한다.
3. 정밀화가 속보보다 악화되는 셀이 존재하면 Phase105와 같은 no-worse projection을 적용해야 한다.
4. 전국 통용형으로 만들려면 `source vintage ledger`가 필수다. 특히 2023년 GRDP와 2023년 사업체조사는 공표 후 정밀화에만 사용하고, 전월·전분기 속보에는 사용할 수 없다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase106_broad_industry_flash_refinement_summary.csv")


if __name__ == "__main__":
    main()
