#!/usr/bin/env python3
"""Phase92: strict current middle-industry GVA accuracy registry.

This phase turns the strict Phase93 no-cell-worse experiment into a clean,
reportable accuracy registry: actual GVA, estimated GVA, error amount, error
rate, grade, adopted group rule, and remaining remediation queue for every
middle industry.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE93 = DATA / "phase93_no_cell_worse_grouped_transfer"
OUTDIR = DATA / "phase92_current_accuracy_after_grouped_transfer"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase92_current_accuracy_after_grouped_transfer.md"


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


def needed_data(row: pd.Series) -> str:
    if row.phase92_error_rate_pct <= 10 and row.phase92_error_gva_eok < 500 and not row.phase92_initial_worsened:
        return "추가 자료 불필요"
    if isinstance(row.needed_data_type, str) and row.needed_data_type != "추가 자료 불필요":
        return row.needed_data_type
    return {
        "생산시설형": "공장·제조시설·설비 규모, 제조업 중분류 부가가치 구조",
        "계약·공사형": "계약액·수주실적·착공/기성·전문기술인력",
        "거래·자산형": "거래금액·자산가치·연면적·금융기관 규모",
        "이동·물량형": "여객·화물·창고·항만 물동량",
        "공공·비영리형": "예산·회원·시설정원·환경처리량",
        "디지털·콘텐츠형": "방송매출·콘텐츠 제작규모·서버/플랫폼 규모",
        "전문·지원서비스형": "사업장 규모·전문인력·인허가·서비스 생산활동",
    }.get(row.cause_group, "산업별 직접 활동자료")


def load_registry() -> pd.DataFrame:
    df = pd.read_csv(PHASE93 / "phase93_grouped_transfer_final_detail.csv")
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    df["phase92_predicted_gva_eok"] = df.current_predicted_gva_eok
    df["phase92_error_gva_eok"] = df.current_error_gva_eok
    df["phase92_error_rate_pct"] = df.current_error_rate_pct
    df["phase92_gap_to_10pct_eok"] = df.current_gap_to_10pct_eok
    df["phase92_accuracy_grade"] = df.phase92_error_rate_pct.map(grade)
    df["phase92_queue"] = np.select(
        [
            df.phase92_error_rate_pct > 50,
            df.phase92_error_rate_pct > 20,
            df.phase92_error_rate_pct > 10,
            df.phase92_error_gva_eok >= 500,
        ],
        ["고취약", "취약", "주의", "금액주의"],
        default="현행유지가능",
    )
    df["phase92_initial_worsened"] = df.phase92_error_gva_eok > df.initial_error_gva_eok + 1e-9
    df["phase93_adopted"] = ~df.current_model_note.eq(df.final_option_family)
    df["phase93_error_reduction_eok"] = df.final_error_gva_eok - df.phase92_error_gva_eok
    df["phase93_error_rate_delta_pp"] = df.final_error_rate_pct - df.phase92_error_rate_pct
    df["phase92_needed_data"] = df.apply(needed_data, axis=1)
    cols = [
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "initial_predicted_gva_eok",
        "initial_error_gva_eok",
        "initial_error_rate_pct",
        "final_option_family",
        "final_predicted_gva_eok",
        "final_error_gva_eok",
        "final_error_rate_pct",
        "phase92_predicted_gva_eok",
        "phase92_error_gva_eok",
        "phase92_error_rate_pct",
        "phase92_gap_to_10pct_eok",
        "phase92_accuracy_grade",
        "phase92_queue",
        "phase92_initial_worsened",
        "phase93_adopted",
        "phase93_error_reduction_eok",
        "phase93_error_rate_delta_pp",
        "current_model_note",
        "cause_group",
        "phase92_needed_data",
        "diagnostic_note",
    ]
    return df[cols].copy()


def summarize(reg: pd.DataFrame) -> pd.DataFrame:
    out = (
        reg.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "size"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("phase92_error_gva_eok", "sum"),
            median_error_pct=("phase92_error_rate_pct", "median"),
            within_5pct_cells=("phase92_error_rate_pct", lambda s: int((s <= 5).sum())),
            within_10pct_cells=("phase92_error_rate_pct", lambda s: int((s <= 10).sum())),
            over_20pct_cells=("phase92_error_rate_pct", lambda s: int((s > 20).sum())),
            over_50pct_cells=("phase92_error_rate_pct", lambda s: int((s > 50).sum())),
            remaining_queue_cells=("phase92_queue", lambda s: int((s != "현행유지가능").sum())),
            adopted_cells=("phase93_adopted", "sum"),
            initial_worsened_cells=("phase92_initial_worsened", "sum"),
            gap_to_10pct_eok=("phase92_gap_to_10pct_eok", "sum"),
        )
    )
    out["wape_pct"] = out.error_sum_eok / out.actual_sum_eok * 100
    return out


def compare_to_phase88(reg: pd.DataFrame) -> pd.DataFrame:
    out = (
        reg.groupby("city", as_index=False)
        .agg(
            phase88_error_sum_eok=("final_error_gva_eok", "sum"),
            phase92_error_sum_eok=("phase92_error_gva_eok", "sum"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            phase88_within_10pct=("final_error_rate_pct", lambda s: int((s <= 10).sum())),
            phase92_within_10pct=("phase92_error_rate_pct", lambda s: int((s <= 10).sum())),
            phase88_over_20pct=("final_error_rate_pct", lambda s: int((s > 20).sum())),
            phase92_over_20pct=("phase92_error_rate_pct", lambda s: int((s > 20).sum())),
        )
    )
    out["phase88_wape_pct"] = out.phase88_error_sum_eok / out.actual_sum_eok * 100
    out["phase92_wape_pct"] = out.phase92_error_sum_eok / out.actual_sum_eok * 100
    out["error_reduction_eok"] = out.phase88_error_sum_eok - out.phase92_error_sum_eok
    out["wape_improvement_pp"] = out.phase88_wape_pct - out.phase92_wape_pct
    return out


def accounting(reg: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (city, parent), g in reg.groupby(["city", "parent_code"]):
        actual = g.actual_gva_eok.sum()
        pred = g.phase92_predicted_gva_eok.sum()
        rows.append(
            {
                "city": city,
                "parent_code": parent,
                "actual_parent_sum_eok": actual,
                "predicted_parent_sum_eok": pred,
                "absolute_error_eok": abs(pred - actual),
                "status": "pass" if abs(pred - actual) < 1e-6 else "fail",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = load_registry()
    summ = summarize(reg)
    comp = compare_to_phase88(reg)
    acct = accounting(reg)
    remaining = reg[reg.phase92_queue.ne("현행유지가능")].sort_values(["city", "phase92_gap_to_10pct_eok", "phase92_error_gva_eok"], ascending=[True, False, False])
    improved = reg[reg.phase93_error_reduction_eok.gt(1e-9)].sort_values("phase93_error_reduction_eok", ascending=False)
    worsened = reg[reg.phase93_error_reduction_eok.lt(-1e-9)].sort_values("phase93_error_reduction_eok")

    reg.to_csv(OUTDIR / "phase92_current_middle_industry_accuracy_registry.csv", index=False, encoding="utf-8-sig")
    summ.to_csv(OUTDIR / "phase92_current_middle_industry_accuracy_summary.csv", index=False, encoding="utf-8-sig")
    comp.to_csv(OUTDIR / "phase92_phase88_comparison.csv", index=False, encoding="utf-8-sig")
    acct.to_csv(OUTDIR / "phase92_accounting_checks.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase92_remaining_industry_queue.csv", index=False, encoding="utf-8-sig")

    report = f"""# 개별 산업 악화 금지 기준 최신 중분류 GVA 정확도 레지스트리

## 목적

Phase93의 개별 산업 악화 금지 기준을 통과한 원인군별 교차도시 전이 결과를 반영해, 고양시·포항시의 각 중분류 산업별 실제 GVA, 추정 GVA, 오차금액, 오차율, 판정, 남은 필요자료를 최신 기준으로 재정리했다. 이 기준에서는 개별 중분류가 하나라도 악화되는 후보를 채택하지 않는다.

## 전체 성능

{md_table(summ, [("city", "지역"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_5pct_cells", "5% 이하"), ("within_10pct_cells", "10% 이하"), ("over_20pct_cells", "20% 초과"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "개선큐"), ("gap_to_10pct_eok", "10% 목표 초과오차 억원")])}

## Phase88 대비 변화

{md_table(comp, [("city", "지역"), ("phase88_error_sum_eok", "Phase88 오차 억원"), ("phase92_error_sum_eok", "Phase92 오차 억원"), ("error_reduction_eok", "감소 억원"), ("phase88_wape_pct", "Phase88 WAPE %"), ("phase92_wape_pct", "Phase92 WAPE %"), ("wape_improvement_pp", "개선 pp"), ("phase88_within_10pct", "Phase88 10%이하"), ("phase92_within_10pct", "Phase92 10%이하"), ("phase88_over_20pct", "Phase88 20%초과"), ("phase92_over_20pct", "Phase92 20%초과")])}

## Phase93에서 실제 개선된 산업

{md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("cause_group", "원인군"), ("actual_gva_eok", "실제 억원"), ("final_predicted_gva_eok", "Phase88 추정 억원"), ("phase92_predicted_gva_eok", "Phase92 추정 억원"), ("final_error_gva_eok", "Phase88 오차 억원"), ("phase92_error_gva_eok", "Phase92 오차 억원"), ("phase93_error_reduction_eok", "감소 억원"), ("phase92_error_rate_pct", "Phase92 오차 %"), ("current_model_note", "적용 기준")], 40)}

## Phase93에서 악화된 산업

{md_table(worsened, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("cause_group", "원인군"), ("final_error_gva_eok", "Phase88 오차 억원"), ("phase92_error_gva_eok", "Phase92 오차 억원"), ("phase93_error_reduction_eok", "감소 억원"), ("phase92_error_rate_pct", "Phase92 오차 %"), ("current_model_note", "적용 기준")], 40)}

## 남은 개선 큐

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("cause_group", "원인군"), ("actual_gva_eok", "실제 억원"), ("phase92_predicted_gva_eok", "추정 억원"), ("phase92_error_gva_eok", "오차 억원"), ("phase92_error_rate_pct", "오차 %"), ("phase92_gap_to_10pct_eok", "10% 초과오차 억원"), ("phase92_queue", "큐"), ("phase92_needed_data", "필요 자료")], 60)}

## 집계 정합성

- 상위산업 합계 불일치 건수: {(acct.status != "pass").sum()}개
- 최대 상위산업 합계 오차: {acct.absolute_error_eok.max():.6g}억원

## 판정

1. 개별 산업 악화 금지 최신 기준은 고양시 WAPE {summ.loc[summ.city.eq('고양시'), 'wape_pct'].iloc[0]:.2f}%, 포항시 WAPE {summ.loc[summ.city.eq('포항시'), 'wape_pct'].iloc[0]:.2f}%다.
2. 개별 산업 악화 금지 기준에서는 고양시와 포항시 모두 교차도시 원인군 전이 후보가 채택되지 않았다. 따라서 최신 엄격 기준은 Phase88 수준을 유지한다.
3. 남은 큐는 고양시 {int(summ.loc[summ.city.eq('고양시'), 'remaining_queue_cells'].iloc[0])}개, 포항시 {int(summ.loc[summ.city.eq('포항시'), 'remaining_queue_cells'].iloc[0])}개다. 다음 실험은 이 큐에 대해 직접 활동자료를 붙이는 방식이어야 한다.
4. 각 산업별 설명에는 반드시 실제 GVA, 추정 GVA, 오차 억원, 오차율을 함께 제시한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase92_current_middle_industry_accuracy_registry.csv")


if __name__ == "__main__":
    main()
