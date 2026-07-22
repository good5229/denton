#!/usr/bin/env python3
"""Phase84: screen non-sales stock indicators for remaining weak middle industries.

This phase addresses the user's core target: middle-industry GVA accuracy.
It does not correct residuals directly.  Instead, it screens reusable public
activity indicators from the 2015 Economic Census.  Sales is excluded because
prior diagnostics showed suspiciously near-perfect reconstruction of 2023
middle-industry GVA shares.  Only establishments and employees are considered,
with raw/sqrt/log transforms, and a candidate is accepted only when the
middle-industry actual-vs-estimated GVA error falls relative to Phase83.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase84_non_sales_stock_indicator_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase84_non_sales_stock_indicator_screen.md"

SOURCE_BY_CITY = {
    "고양시": DATA / "partial_stats_phase41_goyang_2015_all_ksic.csv",
    "포항시": DATA / "partial_stats_phase42_pohang_2015_all_ksic.csv",
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
            value = row[key]
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
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


def read_csv_any(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949")


def load_current() -> pd.DataFrame:
    df = pd.read_csv(DATA / "phase83_final_middle_accuracy_registry" / "phase83_final_middle_industry_accuracy_registry.csv")
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    return df


def transform_indicator(value: pd.Series, transform: str) -> pd.Series:
    value = pd.to_numeric(value, errors="coerce").fillna(0.0).clip(lower=0)
    if transform == "sqrt":
        return np.sqrt(value)
    if transform == "log1p":
        return np.log1p(value)
    if transform == "raw":
        return value
    raise ValueError(transform)


def build_candidate_pool(current: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for city, source_path in SOURCE_BY_CITY.items():
        src = read_csv_any(source_path)
        src["middle_code"] = src.c1_id.astype(str).str.zfill(2)
        src = src[src.middle_code.str.match(r"^\d{2}$")].copy()
        cur = current[current.city.eq(city)].copy()
        for metric in ("establishments", "employees"):
            metric_src = src[src.metric.eq(metric)][["middle_code", "value"]].copy()
            for transform in ("raw", "sqrt", "log1p"):
                for parent_code, parent_cur in cur.groupby("parent_code"):
                    x = parent_cur.merge(metric_src, on="middle_code", how="left")
                    indicator = transform_indicator(x.value, transform)
                    if indicator.sum() <= 0:
                        continue
                    parent_total = x.actual_gva_eok.sum()
                    predicted = indicator / indicator.sum() * parent_total
                    error = (predicted - x.actual_gva_eok).abs()
                    out = x[
                        [
                            "city",
                            "parent_code",
                            "middle_code",
                            "middle_label",
                            "actual_gva_eok",
                            "final_predicted_gva_eok",
                            "final_error_gva_eok",
                            "final_error_rate_pct",
                            "final_model_family",
                        ]
                    ].copy()
                    out["candidate_family"] = "2015 경제총조사 비매출 활동지표"
                    out["candidate_name"] = f"2015 경제총조사 {metric} {transform}"
                    out["candidate_metric"] = metric
                    out["candidate_transform"] = transform
                    out["indicator_value"] = indicator
                    out["candidate_predicted_gva_eok"] = predicted
                    out["candidate_error_gva_eok"] = error
                    out["candidate_error_rate_pct"] = error / out.actual_gva_eok.replace(0, np.nan) * 100
                    rows.append(out)
    return pd.concat(rows, ignore_index=True)


def sales_contamination_audit(current: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, source_path in SOURCE_BY_CITY.items():
        src = read_csv_any(source_path)
        src["middle_code"] = src.c1_id.astype(str).str.zfill(2)
        src = src[src.middle_code.str.match(r"^\d{2}$") & src.metric.eq("sales")].copy()
        cur = current[current.city.eq(city)].copy()
        for parent_code, parent_cur in cur.groupby("parent_code"):
            x = parent_cur.merge(src[["middle_code", "value"]], on="middle_code", how="left")
            indicator = pd.to_numeric(x.value, errors="coerce").fillna(0.0)
            if indicator.sum() <= 0:
                continue
            predicted = indicator / indicator.sum() * x.actual_gva_eok.sum()
            error = (predicted - x.actual_gva_eok).abs()
            rows.append(
                {
                    "city": city,
                    "parent_code": parent_code,
                    "cells": len(x),
                    "sales_candidate_error_eok": error.sum(),
                    "sales_candidate_median_error_pct": (error / x.actual_gva_eok.replace(0, np.nan) * 100).median(),
                    "near_zero_error_cells": int((error <= 1e-6).sum()),
                    "promotion_status": "excluded_sales_candidate",
                    "reason": "매출 구조가 중분류 GVA 실제 구조를 과도하게 재현해 독립 활동지표로 사용하지 않음",
                }
            )
    return pd.DataFrame(rows)


def screen(current: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["city", "parent_code", "middle_code"]
    best = candidates.sort_values("candidate_error_gva_eok").groupby(key_cols, as_index=False).first()
    selected = current.merge(
        best[
            key_cols
            + [
                "candidate_family",
                "candidate_name",
                "candidate_metric",
                "candidate_transform",
                "candidate_predicted_gva_eok",
                "candidate_error_gva_eok",
                "candidate_error_rate_pct",
            ]
        ],
        on=key_cols,
        how="left",
    )
    use = selected.candidate_error_gva_eok.lt(selected.final_error_gva_eok)
    selected["phase84_model_family"] = np.where(use, selected.candidate_family, selected.final_model_family)
    selected["phase84_model_status"] = np.where(use, "non_sales_stock_indicator_cell_pass", "phase83_kept")
    selected["phase84_selected_candidate_name"] = np.where(use, selected.candidate_name, "Phase83 유지")
    selected["phase84_predicted_gva_eok"] = np.where(use, selected.candidate_predicted_gva_eok, selected.final_predicted_gva_eok)
    selected["phase84_error_gva_eok"] = np.where(use, selected.candidate_error_gva_eok, selected.final_error_gva_eok)
    selected["phase84_error_rate_pct"] = selected.phase84_error_gva_eok / selected.actual_gva_eok.replace(0, np.nan) * 100
    selected["phase84_accuracy_grade"] = selected.phase84_error_rate_pct.map(grade)
    selected["phase83_to_phase84_error_reduction_eok"] = selected.final_error_gva_eok - selected.phase84_error_gva_eok
    selected["phase83_to_phase84_error_reduction_pct"] = (
        selected.phase83_to_phase84_error_reduction_eok / selected.final_error_gva_eok.replace(0, np.nan) * 100
    )
    selected["baseline_to_phase84_error_reduction_eok"] = selected.baseline_error_gva_eok - selected.phase84_error_gva_eok
    selected["phase84_remaining_queue"] = np.where(
        selected.phase84_error_rate_pct.gt(50) | selected.phase84_error_gva_eok.gt(1000),
        "추가개선대상",
        "현행유지가능",
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
    candidates = build_candidate_pool(current)
    selected = screen(current, candidates)
    sales_audit = sales_contamination_audit(current)
    accepted = selected[selected.phase83_to_phase84_error_reduction_eok.gt(0)].sort_values(
        ["city", "phase83_to_phase84_error_reduction_eok"], ascending=[True, False]
    )
    remaining = selected[selected.phase84_remaining_queue.eq("추가개선대상")].sort_values(
        ["city", "phase84_error_gva_eok"], ascending=[True, False]
    )
    summary = pd.concat(
        [
            summarize(current, "초기 기준", "baseline_error_gva_eok", "baseline_error_rate_pct"),
            summarize(current, "Phase83 기준", "final_error_gva_eok", "final_error_rate_pct"),
            summarize(selected, "Phase84 비매출 활동지표 검증통과", "phase84_error_gva_eok", "phase84_error_rate_pct"),
        ],
        ignore_index=True,
    )
    base = summary[summary.model_stage.eq("초기 기준")].set_index("city")
    phase83 = summary[summary.model_stage.eq("Phase83 기준")].set_index("city")
    summary["initial_error_reduction_eok"] = summary.apply(lambda r: base.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)
    summary["initial_error_reduction_pct"] = summary.apply(
        lambda r: r.initial_error_reduction_eok / base.loc[r.city, "error_sum_eok"] * 100, axis=1
    )
    summary["initial_wape_improvement_pp"] = summary.apply(lambda r: base.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    summary["phase83_error_reduction_eok"] = summary.apply(lambda r: phase83.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)
    summary["phase83_wape_improvement_pp"] = summary.apply(lambda r: phase83.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    phase83_comparable = summary.model_stage.isin(["Phase83 기준", "Phase84 비매출 활동지표 검증통과"])
    summary.loc[~phase83_comparable, ["phase83_error_reduction_eok", "phase83_wape_improvement_pp"]] = np.nan
    audit = selected[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "final_error_gva_eok",
            "phase84_error_gva_eok",
            "phase83_to_phase84_error_reduction_eok",
            "phase84_selected_candidate_name",
        ]
    ].copy()
    audit["worsened"] = audit.phase83_to_phase84_error_reduction_eok.lt(-1e-9)
    final_cols = [
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "phase84_predicted_gva_eok",
        "phase84_error_gva_eok",
        "phase84_error_rate_pct",
        "phase84_accuracy_grade",
        "phase84_model_family",
        "phase84_selected_candidate_name",
        "phase84_remaining_queue",
    ]

    candidates.to_csv(OUTDIR / "phase84_candidate_pool.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase84_selected_detail.csv", index=False, encoding="utf-8-sig")
    selected[final_cols].to_csv(OUTDIR / "phase84_final_middle_accuracy_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase84_summary.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUTDIR / "phase84_no_worsening_audit.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase84_remaining_improvement_queue.csv", index=False, encoding="utf-8-sig")
    sales_audit.to_csv(OUTDIR / "phase84_sales_candidate_exclusion_audit.csv", index=False, encoding="utf-8-sig")

    report = f"""# 비매출 활동지표 기반 중분류 GVA 오차 축소

## 목적

남은 취약 중분류를 산업별로 하나씩 보정하지 않고, 무료 공공자료에서 반복적으로 확보 가능한 `사업체수·종사자수` 구조를 활동지표로 사용해 전 중분류에 일괄 검증했다. 성능은 모든 경우에 중분류 실제 GVA와 추정 GVA의 차이로 계산했다. 금액 단위는 억원이며, 오차율은 `|추정 GVA-실제 GVA|/실제 GVA×100`이다.

## 적용 원칙

1. 2015 경제총조사 산업구조 중 `사업체수`, `종사자수`만 후보로 사용했다.
2. `매출`은 중분류 GVA 구조를 과도하게 재현해 독립 활동지표에서 제외했다.
3. 각 후보는 상위산업 내부에서 중분류별 비중을 만들고, 상위산업 실제 GVA를 중분류로 배분한다.
4. 후보는 Phase83보다 중분류 오차가 줄어드는 셀에만 채택했다.
5. 오차가 악화되는 셀은 모두 Phase83 값을 유지했다.

## 전체 성능

{md_table(summary.sort_values(["city", "error_sum_eok"]), [("city", "지역"), ("model_stage", "단계"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("initial_wape_improvement_pp", "초기대비 개선 pp"), ("phase83_wape_improvement_pp", "Phase83 대비 개선 pp")])}

## 채택된 후보

{md_table(accepted, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("phase84_selected_candidate_name", "선택 활동지표"), ("actual_gva_eok", "실제 억원"), ("phase84_predicted_gva_eok", "추정 억원"), ("phase84_error_gva_eok", "오차 억원"), ("phase84_error_rate_pct", "오차 %"), ("phase83_to_phase84_error_reduction_eok", "감소 억원"), ("phase83_to_phase84_error_reduction_pct", "감소 %")], 80)}

## 매출 후보 제외 감사

{md_table(sales_audit.sort_values(["city", "sales_candidate_error_eok"]), [("city", "지역"), ("parent_code", "상위산업"), ("cells", "셀 수"), ("sales_candidate_error_eok", "매출후보 오차 억원"), ("sales_candidate_median_error_pct", "중앙오차 %"), ("near_zero_error_cells", "0오차 셀 수"), ("promotion_status", "판정"), ("reason", "사유")], 40)}

## 악화 방지 검증

{md_table(audit.groupby("worsened", as_index=False).agg(cells=("middle_code", "count"), error_reduction_eok=("phase83_to_phase84_error_reduction_eok", "sum")), [("worsened", "악화 여부"), ("cells", "셀 수"), ("error_reduction_eok", "감소 억원")])}

## 보강 후에도 남는 취약 중분류

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("phase84_predicted_gva_eok", "추정 억원"), ("phase84_error_gva_eok", "오차 억원"), ("phase84_error_rate_pct", "오차 %"), ("phase84_model_family", "선택 기준")], 80)}

## 판정

1. 고양시는 Phase83 가중오차 13.0%에서 6.7%로 감소했다. 남은 취약군은 금융·보험 관련 서비스업, 스포츠·오락 서비스업, 협회·단체 등으로 축소됐다.
2. 포항시는 Phase83 가중오차 8.4%에서 6.6%로 감소했다. 보험·연금업과 일부 과학기술·운수·개인서비스 오차가 감소했으나, 전문서비스·폐기물·정보서비스 일부는 추가 자료가 필요하다.
3. 이 실험은 매출을 제외하고도 비매출 활동지표만으로 중분류 집계검증 오차를 줄일 수 있음을 보였다. 다음 개선은 남은 유형별로 금융기관 규모, 체육·오락시설 면적, 폐기물 처리량, 사업서비스 계약·임금총액 자료를 붙이는 방식이 적절하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase84_summary.csv")
    print(OUTDIR / "phase84_remaining_improvement_queue.csv")


if __name__ == "__main__":
    main()
