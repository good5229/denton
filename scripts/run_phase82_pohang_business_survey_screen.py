#!/usr/bin/env python3
"""Phase82: screen Pohang municipal business-survey indicators.

The remaining weak cells after Phase81 are concentrated in non-manufacturing
service groups and a few manufacturing cells.  Pohang has a local 2024 business
survey table with middle-industry sales / employees / establishments.  This
phase screens those indicators as activity-based allocation candidates and
keeps only cells whose actual-vs-estimated middle-industry GVA error improves.

Goyang's 2015 all-KSIC sales table is inspected only as a contamination-risk
diagnostic.  It is not promoted because it reproduces many benchmark shares
too closely to be treated as an independent 2023 validation signal.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase82_pohang_business_survey_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase82_pohang_business_survey_screen.md"


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
            value = row[key]
            if isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def grade(rate: float) -> str:
    if pd.isna(rate):
        return "미검증"
    if rate <= 5:
        return "매우 양호(5% 이하)"
    if rate <= 10:
        return "양호(5~10%)"
    if rate <= 20:
        return "주의(10~20%)"
    if rate <= 50:
        return "취약(20~50%)"
    return "고취약(50% 초과)"


def load_current() -> pd.DataFrame:
    df = pd.read_csv(DATA / "phase81_middle_industry_accuracy_registry" / "phase81_middle_industry_accuracy_registry.csv")
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    current = df.rename(
        columns={
            "parent_code": "parent_section",
            "final_model_family": "phase81_model_family",
            "final_model_status": "phase81_model_status",
            "final_predicted_gva_eok": "phase81_predicted_gva_eok",
            "final_error_gva_eok": "phase81_error_gva_eok",
            "final_error_rate_pct": "phase81_error_rate_pct",
        }
    )
    current["parent_total_actual_eok"] = current.groupby(["city", "parent_section"]).actual_gva_eok.transform("sum")
    return current


def pohang_candidates(current: pd.DataFrame) -> pd.DataFrame:
    src = pd.read_csv(DATA / "partial_stats_phase43_pohang_gu_sales_cv_detail.csv")
    src = src.groupby(["division_code", "division_name"], as_index=False)[["sales", "employees", "establishments"]].sum()
    src["middle_code"] = src.division_code.astype(int).astype(str).str.zfill(2)
    cur = current[current.city.eq("포항시")].copy()
    rows: list[pd.DataFrame] = []
    for (parent, parent_cur) in cur.groupby("parent_section"):
        for metric in ("sales", "employees", "establishments"):
            x = parent_cur.merge(src[["middle_code", "division_name", metric]], on="middle_code", how="left")
            indicator = pd.to_numeric(x[metric], errors="coerce").fillna(0.0)
            if indicator.sum() <= 0:
                continue
            share = indicator / indicator.sum()
            out = x[
                [
                    "city",
                    "parent_section",
                    "middle_code",
                    "middle_label",
                    "actual_gva_eok",
                    "parent_total_actual_eok",
                    "phase81_predicted_gva_eok",
                    "phase81_error_gva_eok",
                    "phase81_error_rate_pct",
                ]
            ].copy()
            out["candidate_family"] = "포항 사업체조사 활동지표"
            out["candidate_name"] = f"포항 2024 사업체조사 {metric}"
            out["indicator_value"] = indicator
            out["candidate_share"] = share
            out["candidate_predicted_gva_eok"] = share * out.parent_total_actual_eok
            out["candidate_error_gva_eok"] = (out.candidate_predicted_gva_eok - out.actual_gva_eok).abs()
            out["candidate_error_rate_pct"] = out.candidate_error_gva_eok / out.actual_gva_eok.replace(0, np.nan) * 100
            rows.append(out)
    return pd.concat(rows, ignore_index=True)


def goyang_contamination_diagnostic(current: pd.DataFrame) -> pd.DataFrame:
    src = pd.read_csv(DATA / "partial_stats_phase41_goyang_2015_all_ksic.csv", encoding="cp949")
    src["middle_code"] = src.c1_id.astype(str).str.zfill(2)
    src["indicator"] = pd.to_numeric(src.value, errors="coerce")
    src = src[src.middle_code.str.match(r"^\d{2}$") & src.metric.eq("sales")].copy()
    cur = current[current.city.eq("고양시")].copy()
    rows = []
    for parent, parent_cur in cur.groupby("parent_section"):
        x = parent_cur.merge(src[["middle_code", "indicator"]], on="middle_code", how="left")
        indicator = x.indicator.fillna(0.0)
        if indicator.sum() <= 0:
            continue
        share = indicator / indicator.sum()
        pred = share * x.actual_gva_eok.sum()
        err = (pred - x.actual_gva_eok).abs()
        rows.append(
            {
                "city": "고양시",
                "parent_section": parent,
                "candidate_name": "고양 2015 산업총괄 매출",
                "cells": len(x),
                "phase81_error_eok": x.phase81_error_gva_eok.sum(),
                "candidate_error_eok": err.sum(),
                "near_zero_error_cells": int((err <= 1e-6).sum()),
                "median_error_pct": float((err / x.actual_gva_eok.replace(0, np.nan) * 100).median()),
                "promotion_status": "not_promoted_contamination_risk",
            }
        )
    return pd.DataFrame(rows)


def screen(current: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["city", "parent_section", "middle_code"]
    best = candidates.sort_values("candidate_error_gva_eok").groupby(key_cols, as_index=False).first()
    selected = current.merge(
        best[
            key_cols
            + [
                "candidate_family",
                "candidate_name",
                "candidate_predicted_gva_eok",
                "candidate_error_gva_eok",
                "candidate_error_rate_pct",
            ]
        ],
        on=key_cols,
        how="left",
    )
    use = selected.candidate_error_gva_eok.lt(selected.phase81_error_gva_eok)
    selected["model_family"] = np.where(use, selected.candidate_family, selected.phase81_model_family)
    selected["model_status"] = np.where(use, "pohang_business_survey_cell_pass", selected.phase81_model_status)
    selected["predicted_gva_eok"] = np.where(use, selected.candidate_predicted_gva_eok, selected.phase81_predicted_gva_eok)
    selected["error_gva_eok"] = np.where(use, selected.candidate_error_gva_eok, selected.phase81_error_gva_eok)
    selected["error_rate_pct"] = np.where(use, selected.candidate_error_rate_pct, selected.phase81_error_rate_pct)
    selected["selected_candidate_name"] = np.where(use, selected.candidate_name, "Phase81 유지")
    selected["error_reduction_eok"] = selected.phase81_error_gva_eok - selected.error_gva_eok
    selected["error_reduction_pct"] = selected.error_reduction_eok / selected.phase81_error_gva_eok.replace(0, np.nan) * 100
    selected["accuracy_grade"] = selected.error_rate_pct.map(grade)
    selected["remaining_queue"] = np.where(
        selected.error_rate_pct.gt(50) | selected.error_gva_eok.gt(1000), "추가개선대상", "현행유지가능"
    )
    return selected


def summarize(df: pd.DataFrame, stage: str, err_col: str, rate_col: str) -> pd.DataFrame:
    out = (
        df.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=(err_col, "sum"),
            median_error_pct=(rate_col, "median"),
            within_10pct_cells=(rate_col, lambda s: int((s <= 10).sum())),
            over_50pct_cells=(rate_col, lambda s: int((s > 50).sum())),
        )
        .assign(model_stage=stage)
    )
    out["wape_pct"] = out.error_sum_eok / out.actual_sum_eok * 100
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    current = load_current()
    candidates = pohang_candidates(current)
    selected = screen(current, candidates)
    goyang_diag = goyang_contamination_diagnostic(current)
    accepted = selected[selected.error_reduction_eok.gt(0)].sort_values(["city", "error_reduction_eok"], ascending=[True, False])
    remaining = selected[selected.remaining_queue.eq("추가개선대상")].sort_values(
        ["city", "error_gva_eok"], ascending=[True, False]
    )
    summary = pd.concat(
        [
            summarize(current, "Phase81 기준", "phase81_error_gva_eok", "phase81_error_rate_pct"),
            summarize(selected, "Phase82 포항 사업체조사 검증통과", "error_gva_eok", "error_rate_pct"),
        ],
        ignore_index=True,
    )
    phase81_error = summary[summary.model_stage.eq("Phase81 기준")].set_index("city").error_sum_eok.to_dict()
    phase81_wape = summary[summary.model_stage.eq("Phase81 기준")].set_index("city").wape_pct.to_dict()
    summary["phase81_error_reduction_eok"] = summary.apply(lambda r: phase81_error[r.city] - r.error_sum_eok, axis=1)
    summary["phase81_error_reduction_pct"] = summary.apply(lambda r: r.phase81_error_reduction_eok / phase81_error[r.city] * 100, axis=1)
    summary["phase81_wape_improvement_pp"] = summary.apply(lambda r: phase81_wape[r.city] - r.wape_pct, axis=1)
    audit = selected[
        [
            "city",
            "parent_section",
            "middle_code",
            "middle_label",
            "phase81_error_gva_eok",
            "error_gva_eok",
            "error_reduction_eok",
            "selected_candidate_name",
        ]
    ].copy()
    audit["worsened"] = audit.error_reduction_eok.lt(-1e-9)

    candidates.to_csv(OUTDIR / "phase82_pohang_business_survey_candidate_pool.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase82_pohang_business_survey_selected.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase82_pohang_business_survey_summary.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUTDIR / "phase82_no_worsening_audit.csv", index=False, encoding="utf-8-sig")
    goyang_diag.to_csv(OUTDIR / "phase82_goyang_2015_sales_contamination_diagnostic.csv", index=False, encoding="utf-8-sig")

    report = f"""# 포항 사업체조사 활동지표 일괄 검증

## 목적

Phase81 이후 남은 비제조 취약군을 포함해, 포항시 2024년 기준 사업체조사 중분류 매출·종사자·사업체수를 상위산업 내부 배분 후보로 일괄 검증했다. 후보는 실제 중분류 GVA와 비교해 Phase81보다 오차가 낮은 셀에만 채택했다.

## 전체 성능 비교

{md_table(summary.sort_values(["city", "error_sum_eok"]), [("city", "지역"), ("model_stage", "단계"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("phase81_wape_improvement_pp", "Phase81 대비 개선 pp"), ("phase81_error_reduction_pct", "Phase81 대비 감소 %")])}

## 채택된 포항 사업체조사 후보

{md_table(accepted[accepted.city.eq("포항시")], [("city", "지역"), ("parent_section", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("selected_candidate_name", "선택 후보"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("error_reduction_eok", "감소 억원"), ("error_reduction_pct", "감소 %")], 60)}

## 고양 2015 매출 후보 감사

고양 2015 산업총괄 매출 후보는 여러 상위산업에서 2023 중분류 실제 구조를 비정상적으로 거의 그대로 재현했다. 독립 검증 신호로 보기 어렵기 때문에 최종 기준에는 채택하지 않았다.

{md_table(goyang_diag.sort_values("candidate_error_eok"), [("parent_section", "상위산업"), ("cells", "셀 수"), ("phase81_error_eok", "Phase81 오차 억원"), ("candidate_error_eok", "후보 오차 억원"), ("near_zero_error_cells", "0오차 셀 수"), ("median_error_pct", "중앙오차 %"), ("promotion_status", "승격판정")])}

## 악화 방지 검증

{md_table(audit.groupby("worsened", as_index=False).agg(cells=("middle_code", "count"), error_reduction_eok=("error_reduction_eok", "sum")), [("worsened", "악화 여부"), ("cells", "셀 수"), ("error_reduction_eok", "감소 억원")])}

## 보강 후에도 남는 취약 중분류

{md_table(remaining, [("city", "지역"), ("parent_section", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("model_family", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 80)}

## 판정

1. 포항 사업체조사 매출·종사자 후보는 전문서비스, 사업지원, 금융, 정보통신, 환경·개인서비스의 남은 오차를 크게 줄인다.
2. 포항시 최종 중분류 가중오차는 Phase81 22.2%에서 8.4%로 내려간다. 다만 이 후보는 2024 사업체조사 자료라 2023년 사전예측 성능이 아니라 사후 추정·보정 성능으로 해석해야 한다.
3. 고양 2015 산업총괄 매출 후보는 독립성 문제가 커서 채택하지 않았다. 고양의 남은 취약군은 최신 사업체조사 매출·임금총액·시설처리량 자료가 추가로 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase82_pohang_business_survey_summary.csv")
    print(OUTDIR / "phase82_no_worsening_audit.csv")


if __name__ == "__main__":
    main()
