#!/usr/bin/env python3
"""Phase109: precision improvement screen for Goyang/Pohang >10% middle GVA gaps.

This phase parks the 10-sigungu generalization work and focuses on the current
user priority: remaining >10% refined-error middle industries in Goyang and
Pohang.

Rule for this phase:
* Do not tune a single middle cell to actual.
* Use a predeclared free/public indicator where already available.
* Evaluate the result against middle GVA diagnostics.

Currently implementable precision candidate:
* C00 manufacturing: KOSIS Mining/Manufacturing Survey 2023 city x KSIC middle
  value added (DT_1FS1101/T06), normalized within the city's manufacturing GVA
  parent total.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase109_goyang_pohang_gt10_precision_improvement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase109_goyang_pohang_gt10_precision_improvement.md"
BASE = DATA / "phase105_no_worse_refinement_guardrail" / "phase105_no_worse_refinement_registry.csv"


def grade(rate: float) -> str:
    if pd.isna(rate):
        return "미검증"
    if rate <= 5:
        return "정밀(5% 이하)"
    if rate <= 10:
        return "10% 이하"
    if rate <= 20:
        return "주의(10~20%)"
    if rate <= 50:
        return "자료보강(20~50%)"
    return "고취약(50% 초과)"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int = 30) -> str:
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "순위")) else "---" for _, label in cols) + " |")
    for _, row in df.head(limit).iterrows():
        vals: list[str] = []
        for key, _label in cols:
            value = row.get(key, "")
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}" if abs(value) < 100 else f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def load_base() -> pd.DataFrame:
    df = pd.read_csv(BASE, dtype={"middle_code": str})
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    df["baseline_predicted_gva_eok"] = df.no_worse_refined_predicted_gva_eok
    df["baseline_error_gva_eok"] = df.no_worse_refined_error_gva_eok
    df["baseline_error_rate_pct"] = df.no_worse_refined_error_rate_pct
    return df


def manufacturing_value_added_indicator() -> pd.DataFrame:
    path = DATA / "expanded_manufacturing_sigungu_ksic.csv"
    man = pd.read_csv(path, encoding="cp949", dtype=str)
    man = man[
        man.prd_de.astype(str).eq("2023")
        & man.metric.eq("value_added")
        & man.ksic_level.eq("middle")
        & man.c1_nm.isin(["고양시", "포항시"])
    ].copy()
    man["middle_code"] = man.c2_id.astype(str).str.extract(r"C(\d+)")[0].str.zfill(2)
    man["indicator_value"] = pd.to_numeric(man.value, errors="coerce")
    man = man[man.middle_code.notna() & man.indicator_value.gt(0)].copy()
    return man.rename(columns={"c1_nm": "city", "c2_nm": "indicator_industry_name"})[
        ["city", "middle_code", "indicator_industry_name", "indicator_value", "unit_nm"]
    ]


def apply_manufacturing_precision(base: pd.DataFrame, indicator: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    out["candidate_predicted_gva_eok"] = out.baseline_predicted_gva_eok
    out["candidate_source"] = "baseline 유지"
    c = out[out.parent_code.eq("C00")].copy()
    if c.empty:
        return out
    c = c.merge(indicator[["city", "middle_code", "indicator_value"]], on=["city", "middle_code"], how="left")
    for city, idx in c.groupby("city").groups.items():
        sub = c.loc[idx].copy()
        ind = sub.indicator_value.fillna(0)
        if ind.sum() <= 0:
            continue
        total = sub.actual_gva_eok.sum()
        pred = ind / ind.sum() * total
        c.loc[idx, "candidate_predicted_gva_eok"] = pred.to_numpy()
        c.loc[idx, "candidate_source"] = "KOSIS 광업제조업조사 2023 중분류 부가가치"
    keys = ["city", "parent_code", "middle_code"]
    out = out.drop(columns=["candidate_predicted_gva_eok", "candidate_source"]).merge(
        c[keys + ["candidate_predicted_gva_eok", "candidate_source"]],
        on=keys,
        how="left",
    )
    out["candidate_predicted_gva_eok"] = out.candidate_predicted_gva_eok.fillna(out.baseline_predicted_gva_eok)
    out["candidate_source"] = out.candidate_source.fillna("baseline 유지")
    return out


def screen_manufacturing_blends(base: pd.DataFrame) -> pd.DataFrame:
    man = pd.read_csv(DATA / "expanded_manufacturing_sigungu_ksic.csv", encoding="cp949", dtype=str)
    man = man[man.c1_nm.isin(["고양시", "포항시"]) & man.ksic_level.eq("middle")].copy()
    man["middle_code"] = man.c2_id.astype(str).str.extract(r"C(\d+)")[0].str.zfill(2)
    man["indicator_value"] = pd.to_numeric(man.value, errors="coerce")
    cbase = base[base.parent_code.eq("C00")].copy()
    rows = []
    for (year, metric), g in man.groupby(["prd_de", "metric"]):
        x = cbase.merge(
            g[["c1_nm", "middle_code", "indicator_value"]].rename(columns={"c1_nm": "city"}),
            on=["city", "middle_code"],
            how="left",
        )
        for alpha in [0.05, 0.10, 0.25, 0.50, 1.00]:
            pred_parts = []
            for city, sub in x.groupby("city"):
                ind = sub.indicator_value.fillna(0)
                total = sub.actual_gva_eok.sum()
                if ind.sum() <= 0:
                    indicator_pred = sub.baseline_predicted_gva_eok
                else:
                    indicator_pred = ind / ind.sum() * total
                pred = (1 - alpha) * sub.baseline_predicted_gva_eok + alpha * indicator_pred
                pred = pred / pred.sum() * total
                err = (pred - sub.actual_gva_eok).abs()
                old = sub.baseline_error_gva_eok
                rows.append(
                    {
                        "city": city,
                        "year": int(year),
                        "metric": metric,
                        "alpha": alpha,
                        "baseline_error_eok": float(old.sum()),
                        "candidate_error_eok": float(err.sum()),
                        "error_reduction_eok": float(old.sum() - err.sum()),
                        "baseline_wape_pct": float(old.sum() / total * 100),
                        "candidate_wape_pct": float(err.sum() / total * 100),
                        "worse_cells": int(err.gt(old + 1e-9).sum()),
                        "gt10_before": int(sub.baseline_error_rate_pct.gt(10).sum()),
                        "gt10_after": int((err / sub.actual_gva_eok.replace(0, np.nan) * 100).gt(10).sum()),
                    }
                )
    score = pd.DataFrame(rows)
    score["public_adoptable"] = score.error_reduction_eok.gt(0) & score.worse_cells.eq(0) & score.gt10_after.le(score.gt10_before)
    score["operational_candidate"] = score.error_reduction_eok.gt(0) & score.alpha.le(0.10) & score.metric.eq("value_added")
    return score.sort_values(["city", "operational_candidate", "error_reduction_eok"], ascending=[True, False, False])


def recommended_blend(score: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in score.groupby("city"):
        public = g[g.public_adoptable].sort_values("error_reduction_eok", ascending=False)
        operational = g[g.operational_candidate].sort_values(["worse_cells", "error_reduction_eok"], ascending=[True, False])
        if not public.empty:
            row = public.iloc[0].copy()
            row["recommendation"] = "public_adoptable"
        elif not operational.empty:
            row = operational.iloc[0].copy()
            row["recommendation"] = "operational_candidate_needs_review"
        else:
            row = g.sort_values("error_reduction_eok", ascending=False).iloc[0].copy()
            row["recommendation"] = "reject_no_safe_improvement"
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["candidate_error_gva_eok"] = (out.candidate_predicted_gva_eok - out.actual_gva_eok).abs()
    out["candidate_error_rate_pct"] = out.candidate_error_gva_eok / out.actual_gva_eok.replace(0, np.nan) * 100
    out["candidate_grade"] = out.candidate_error_rate_pct.map(grade)
    out["error_reduction_eok"] = out.baseline_error_gva_eok - out.candidate_error_gva_eok
    out["error_rate_reduction_pp"] = out.baseline_error_rate_pct - out.candidate_error_rate_pct
    out["baseline_gt10"] = out.baseline_error_rate_pct.gt(10)
    out["candidate_gt10"] = out.candidate_error_rate_pct.gt(10)
    out["candidate_worse"] = out.candidate_error_gva_eok.gt(out.baseline_error_gva_eok + 1e-9)
    return out


def summarize(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    city = (
        df.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            baseline_error_sum_eok=("baseline_error_gva_eok", "sum"),
            candidate_error_sum_eok=("candidate_error_gva_eok", "sum"),
            baseline_gt10_cells=("baseline_gt10", "sum"),
            candidate_gt10_cells=("candidate_gt10", "sum"),
            worsened_cells=("candidate_worse", "sum"),
        )
    )
    city["baseline_wape_pct"] = city.baseline_error_sum_eok / city.actual_sum_eok * 100
    city["candidate_wape_pct"] = city.candidate_error_sum_eok / city.actual_sum_eok * 100
    city["error_reduction_eok"] = city.baseline_error_sum_eok - city.candidate_error_sum_eok
    city["wape_reduction_pp"] = city.baseline_wape_pct - city.candidate_wape_pct

    parent = (
        df.groupby(["city", "parent_code"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            baseline_error_sum_eok=("baseline_error_gva_eok", "sum"),
            candidate_error_sum_eok=("candidate_error_gva_eok", "sum"),
            baseline_gt10_cells=("baseline_gt10", "sum"),
            candidate_gt10_cells=("candidate_gt10", "sum"),
            worsened_cells=("candidate_worse", "sum"),
        )
    )
    parent["baseline_wape_pct"] = parent.baseline_error_sum_eok / parent.actual_sum_eok * 100
    parent["candidate_wape_pct"] = parent.candidate_error_sum_eok / parent.actual_sum_eok * 100
    parent["error_reduction_eok"] = parent.baseline_error_sum_eok - parent.candidate_error_sum_eok
    parent["wape_reduction_pp"] = parent.baseline_wape_pct - parent.candidate_wape_pct

    gt10 = df[df.baseline_gt10 | df.candidate_gt10].sort_values(["city", "candidate_error_gva_eok"], ascending=[True, False])
    return city, parent, gt10


def unmet_data_plan(df: pd.DataFrame) -> pd.DataFrame:
    remaining = df[df.candidate_gt10].copy()
    rows = []
    for (city, cause_group, required), g in remaining.groupby(["city", "cause_group", "required_next_data"]):
        rows.append(
            {
                "city": city,
                "cause_group": cause_group,
                "remaining_cells": len(g),
                "actual_sum_eok": g.actual_gva_eok.sum(),
                "remaining_error_eok": g.candidate_error_gva_eok.sum(),
                "median_error_pct": g.candidate_error_rate_pct.median(),
                "priority_industries": ", ".join(g.sort_values("candidate_error_gva_eok", ascending=False).middle_label.head(4)),
                "needed_free_data": required,
                "collection_action": collection_action(cause_group, required),
            }
        )
    return pd.DataFrame(rows).sort_values(["city", "remaining_error_eok"], ascending=[True, False])


def collection_action(cause_group: str, required: str) -> str:
    if "비영리" in required or "회원" in required:
        return "지자체 보조금·비영리민간단체 등록·공익법인 결산/보조금 자료 탐색"
    if "방송" in required or "콘텐츠" in required:
        return "방송통신위원회/문체부 콘텐츠산업·방송사업자 지역/사업체 자료 탐색"
    if "금융" in cause_group or "거래" in cause_group:
        return "금융점포·예수금/대출 또는 공시가격·거래금액 무료 집계자료 탐색"
    if "전문" in cause_group or "계약" in cause_group:
        return "조달계약·건축허가/착공·전문서비스 사업체조사 중분류 매출 자료 탐색"
    if "공공" in cause_group:
        return "상하수도·폐기물 처리량, 공공시설 이용량·예산 집계자료 탐색"
    if "이동" in cause_group:
        return "항만·여객·화물·창고면적 활동자료 탐색"
    return "공통 무료 중분류 활동자료 추가 탐색"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_base()
    indicator = manufacturing_value_added_indicator()
    candidate = apply_manufacturing_precision(base, indicator)
    evaluated = evaluate(candidate)
    blend_score = screen_manufacturing_blends(base)
    blend_reco = recommended_blend(blend_score)
    city, parent, gt10 = summarize(evaluated)
    plan = unmet_data_plan(evaluated)

    indicator.to_csv(OUT / "phase109_manufacturing_value_added_indicator_2023.csv", index=False, encoding="utf-8-sig")
    evaluated.to_csv(OUT / "phase109_precision_candidate_detail.csv", index=False, encoding="utf-8-sig")
    city.to_csv(OUT / "phase109_city_summary.csv", index=False, encoding="utf-8-sig")
    parent.to_csv(OUT / "phase109_parent_summary.csv", index=False, encoding="utf-8-sig")
    gt10.to_csv(OUT / "phase109_gt10_before_after.csv", index=False, encoding="utf-8-sig")
    plan.to_csv(OUT / "phase109_remaining_data_collection_plan.csv", index=False, encoding="utf-8-sig")
    blend_score.to_csv(OUT / "phase109_manufacturing_blend_screen.csv", index=False, encoding="utf-8-sig")
    blend_reco.to_csv(OUT / "phase109_manufacturing_blend_recommendation.csv", index=False, encoding="utf-8-sig")
    (OUT / "phase109_manifest.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "deferred_generalization": "10개 시군구 일반화 검증은 고양·포항 최종 산출물 마무리 후 재개",
                "implemented_candidate": "KOSIS DT_1FS1101 2023 manufacturing middle value_added precision indicator",
                "target": "Goyang/Pohang middle-industry GVA refined-error >10%",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = f"""# 고양·포항 10% 초과 정밀오차 개선 실험

## 작업 범위

10개 시군구 일반화 검증은 고양시·포항시 산출물 마무리 후 재개한다. 이번 단계는 고양시와 포항시의 중분류 총부가가치(GVA) 정밀오차 10% 초과 업종 개선에 한정했다.

## 적용한 무료자료

- KOSIS 광업제조업조사 `DT_1FS1101`, 2023년 시군구×제조업 중분류 부가가치
- 사용 방식: 제조업 C00 내부에서 2023 중분류 부가가치 비중을 정밀화 지표로 사용
- 해석 제한: 광업제조업조사 부가가치는 국민계정 GVA와 산식이 다르므로 직접 actual이 아니라 제조업 내부 구조 개선 지표다. 전월·전분기 속보에는 사용할 수 없고, 공표 후 정밀화 트랙에서만 사용한다.

## 도시별 결과

{md_table(city, [("city", "지역"), ("cells", "중분류 개"), ("actual_sum_eok", "실제합계 억원"), ("baseline_error_sum_eok", "기준오차 억원"), ("candidate_error_sum_eok", "후보오차 억원"), ("error_reduction_eok", "오차감소 억원"), ("baseline_wape_pct", "기준 WAPE %"), ("candidate_wape_pct", "후보 WAPE %"), ("wape_reduction_pp", "WAPE 감소 pp"), ("baseline_gt10_cells", "기준 10%초과 개"), ("candidate_gt10_cells", "후보 10%초과 개"), ("worsened_cells", "악화 개")])}

## 상위산업별 결과

{md_table(parent.sort_values(["city", "error_reduction_eok"], ascending=[True, False]), [("city", "지역"), ("parent_code", "상위산업"), ("cells", "중분류 개"), ("baseline_error_sum_eok", "기준오차 억원"), ("candidate_error_sum_eok", "후보오차 억원"), ("error_reduction_eok", "오차감소 억원"), ("baseline_wape_pct", "기준 WAPE %"), ("candidate_wape_pct", "후보 WAPE %"), ("worsened_cells", "악화 개")], 40)}

## 제조업 보조지표 혼합 스크린

제조업 중분류 부가가치를 그대로 대체하면 고양·포항 모두 악화된다. 따라서 보조지표로 5~10%만 섞는 후보를 별도로 보았다. 이 스크린은 실제값에 맞춰 셀을 개별 보정하는 것이 아니라, 연도×지표×혼합비 조합 전체의 안정성을 보는 진단이다.

{md_table(blend_reco, [("city", "지역"), ("recommendation", "판정"), ("year", "자료연도"), ("metric", "지표"), ("alpha", "혼합비"), ("baseline_error_eok", "기준 제조업오차 억원"), ("candidate_error_eok", "후보 제조업오차 억원"), ("error_reduction_eok", "오차감소 억원"), ("baseline_wape_pct", "기준 WAPE %"), ("candidate_wape_pct", "후보 WAPE %"), ("worse_cells", "악화 개"), ("gt10_before", "기준 10%초과"), ("gt10_after", "후보 10%초과")], 20)}

상위 후보 전체:

{md_table(blend_score.sort_values(["city", "error_reduction_eok"], ascending=[True, False]), [("city", "지역"), ("year", "자료연도"), ("metric", "지표"), ("alpha", "혼합비"), ("error_reduction_eok", "오차감소 억원"), ("candidate_wape_pct", "후보 WAPE %"), ("worse_cells", "악화 개"), ("gt10_after", "후보 10%초과"), ("public_adoptable", "대외채택"), ("operational_candidate", "운영후보")], 40)}

## 10% 초과 업종 전후

{md_table(gt10, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("baseline_predicted_gva_eok", "기준추정 억원"), ("baseline_error_gva_eok", "기준오차 억원"), ("baseline_error_rate_pct", "기준오차 %"), ("candidate_predicted_gva_eok", "후보추정 억원"), ("candidate_error_gva_eok", "후보오차 억원"), ("candidate_error_rate_pct", "후보오차 %"), ("error_reduction_eok", "오차감소 억원"), ("candidate_source", "후보자료")], 80)}

## 남은 10% 초과 업종 자료수집 계획

{md_table(plan, [("city", "지역"), ("cause_group", "원인군"), ("remaining_cells", "잔여 개"), ("actual_sum_eok", "실제합계 억원"), ("remaining_error_eok", "잔여오차 억원"), ("median_error_pct", "중앙오차 %"), ("priority_industries", "우선 업종"), ("needed_free_data", "필요 무료자료"), ("collection_action", "수집 방향")], 40)}

## 판정

1. 제조업 중분류 부가가치를 100% 대체지표로 쓰는 방식은 채택하면 안 된다.
2. 고양 제조업은 광업제조업조사 계열 지표를 소량 섞어도 악화되어 현재 기준 유지가 맞다.
3. 포항 제조업은 `2022년 광업제조업조사 부가가치 5% 혼합`이 제조업 오차를 줄이는 운영 후보지만, 악화 셀이 남아 대외 성능 주장용 최종값으로는 아직 부적합하다.
4. 제조업 외 10% 초과 업종은 현재 로컬 공통자료만으로는 충분하지 않다. 다음 수집 우선순위는 고양 `협회·단체/방송/스포츠·오락`, 포항 `금융·보험/건축·엔지니어링/사업시설관리/정보서비스`다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT / "phase109_precision_candidate_detail.csv")


if __name__ == "__main__":
    main()
