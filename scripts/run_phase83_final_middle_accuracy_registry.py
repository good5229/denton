#!/usr/bin/env python3
"""Phase83: final middle-industry accuracy registry after Phase82."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase83_final_middle_accuracy_registry"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase83_final_middle_accuracy_registry.md"


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


def load() -> pd.DataFrame:
    base = pd.read_csv(DATA / "phase81_middle_industry_accuracy_registry" / "phase81_middle_industry_accuracy_registry.csv")
    base["middle_code"] = base.middle_code.astype(str).str.zfill(2)
    phase82 = pd.read_csv(DATA / "phase82_pohang_business_survey_screen" / "phase82_pohang_business_survey_selected.csv")
    phase82["middle_code"] = phase82.middle_code.astype(str).str.zfill(2)
    p82 = phase82.rename(
        columns={
            "parent_section": "parent_code",
            "model_family": "phase82_model_family",
            "model_status": "phase82_model_status",
            "predicted_gva_eok": "phase82_predicted_gva_eok",
            "error_gva_eok": "phase82_error_gva_eok",
            "error_rate_pct": "phase82_error_rate_pct",
            "selected_candidate_name": "phase82_selected_candidate_name",
        }
    )[
        [
            "city",
            "parent_code",
            "middle_code",
            "phase82_model_family",
            "phase82_model_status",
            "phase82_selected_candidate_name",
            "phase82_predicted_gva_eok",
            "phase82_error_gva_eok",
            "phase82_error_rate_pct",
        ]
    ]
    reg = base.merge(p82, on=["city", "parent_code", "middle_code"], how="left")
    reg["final_model_family"] = reg.phase82_model_family
    reg["final_model_status"] = reg.phase82_model_status
    reg["final_selected_candidate_name"] = reg.phase82_selected_candidate_name
    reg["final_predicted_gva_eok"] = reg.phase82_predicted_gva_eok
    reg["final_error_gva_eok"] = reg.phase82_error_gva_eok
    reg["final_error_rate_pct"] = reg.phase82_error_rate_pct
    reg["final_accuracy_grade"] = reg.final_error_rate_pct.map(grade)
    reg["baseline_to_final_error_reduction_eok"] = reg.baseline_error_gva_eok - reg.final_error_gva_eok
    reg["baseline_to_final_error_reduction_pct"] = (
        reg.baseline_to_final_error_reduction_eok / reg.baseline_error_gva_eok.replace(0, np.nan) * 100
    )
    # The Phase81 registry already stores its final columns before Phase82.
    phase81_error = pd.read_csv(DATA / "phase81_middle_industry_accuracy_registry" / "phase81_middle_industry_accuracy_registry.csv")
    phase81_error["middle_code"] = phase81_error.middle_code.astype(str).str.zfill(2)
    phase81_error = phase81_error[["city", "parent_code", "middle_code", "final_error_gva_eok", "final_error_rate_pct"]].rename(
        columns={"final_error_gva_eok": "phase81_error_gva_eok_for_delta", "final_error_rate_pct": "phase81_error_rate_pct_for_delta"}
    )
    reg = reg.merge(phase81_error, on=["city", "parent_code", "middle_code"], how="left")
    reg["phase81_to_final_error_reduction_eok"] = reg.phase81_error_gva_eok_for_delta - reg.final_error_gva_eok
    reg["phase81_to_final_error_reduction_pct"] = (
        reg.phase81_to_final_error_reduction_eok / reg.phase81_error_gva_eok_for_delta.replace(0, np.nan) * 100
    )
    reg["remaining_queue"] = np.where(
        reg.final_error_rate_pct.gt(50) | reg.final_error_gva_eok.gt(1000), "추가개선대상", "현행유지가능"
    )
    return reg


def summary(reg: pd.DataFrame) -> pd.DataFrame:
    stages = [
        ("초기 기준", "baseline_error_gva_eok", "baseline_error_rate_pct"),
        ("Phase81 기준", "phase81_error_gva_eok_for_delta", "phase81_error_rate_pct_for_delta"),
        ("Phase83 최종", "final_error_gva_eok", "final_error_rate_pct"),
    ]
    rows = []
    for stage, err_col, rate_col in stages:
        g = (
            reg.groupby("city", as_index=False)
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
        g["wape_pct"] = g.error_sum_eok / g.actual_sum_eok * 100
        rows.append(g)
    out = pd.concat(rows, ignore_index=True)
    base_err = out[out.model_stage.eq("초기 기준")].set_index("city").error_sum_eok.to_dict()
    base_wape = out[out.model_stage.eq("초기 기준")].set_index("city").wape_pct.to_dict()
    out["baseline_error_reduction_eok"] = out.apply(lambda r: base_err[r.city] - r.error_sum_eok, axis=1)
    out["baseline_error_reduction_pct"] = out.apply(lambda r: r.baseline_error_reduction_eok / base_err[r.city] * 100, axis=1)
    out["baseline_wape_improvement_pp"] = out.apply(lambda r: base_wape[r.city] - r.wape_pct, axis=1)
    return out.sort_values(["city", "error_sum_eok"])


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = load()
    summ = summary(reg)
    improved = reg[reg.baseline_to_final_error_reduction_eok.gt(0)].sort_values(
        ["city", "baseline_to_final_error_reduction_eok"], ascending=[True, False]
    )
    weak = reg[reg.remaining_queue.eq("추가개선대상")].sort_values(["city", "final_error_gva_eok"], ascending=[True, False])
    good = reg.sort_values(["city", "final_error_rate_pct"]).groupby("city").head(20)
    worsened = reg[reg.baseline_to_final_error_reduction_eok.lt(-1e-9)].copy()

    reg.to_csv(OUTDIR / "phase83_final_middle_industry_accuracy_registry.csv", index=False, encoding="utf-8-sig")
    summ.to_csv(OUTDIR / "phase83_final_middle_industry_accuracy_summary.csv", index=False, encoding="utf-8-sig")
    weak.to_csv(OUTDIR / "phase83_remaining_improvement_queue.csv", index=False, encoding="utf-8-sig")

    report = f"""# 최종 중분류 산업별 GVA 추정 정확도 레지스트리

## 목적

Phase82까지 반영해 고양시·포항시의 각 중분류 산업별 실제 GVA, 최종 추정 GVA, 오차금액, 오차율, 판정을 정리했다. 모든 금액은 억원이고, 오차율은 `|추정 GVA-실제 GVA|/실제 GVA×100`이다.

## 단계별 전체 성능

{md_table(summ, [("city", "지역"), ("model_stage", "단계"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("baseline_wape_improvement_pp", "초기대비 개선 pp"), ("baseline_error_reduction_pct", "초기대비 감소 %")])}

## 개선 폭 상위 산업

{md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("baseline_predicted_gva_eok", "초기 추정 억원"), ("baseline_error_gva_eok", "초기 오차 억원"), ("final_predicted_gva_eok", "최종 추정 억원"), ("final_error_gva_eok", "최종 오차 억원"), ("final_error_rate_pct", "최종 오차 %"), ("baseline_to_final_error_reduction_eok", "감소 억원"), ("final_model_family", "최종 기준")], 80)}

## 예측 양호 산업 예시

{md_table(good, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("final_predicted_gva_eok", "최종 추정 억원"), ("final_error_gva_eok", "오차 억원"), ("final_error_rate_pct", "오차 %"), ("final_accuracy_grade", "판정")], 50)}

## 추가개선대상 산업

{md_table(weak, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("final_predicted_gva_eok", "최종 추정 억원"), ("final_error_gva_eok", "오차 억원"), ("final_error_rate_pct", "오차 %"), ("final_model_family", "최종 기준")], 80)}

## 악화 점검

초기 기준보다 최종 오차가 악화된 셀 수: {len(worsened)}개.

{md_table(worsened, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("baseline_error_gva_eok", "초기 오차 억원"), ("final_error_gva_eok", "최종 오차 억원"), ("baseline_to_final_error_reduction_eok", "감소 억원")], 40)}

## 판정

1. 고양시는 초기 중분류 가중오차 44.1%에서 최종 13.0%로 감소했다. 고양 2015 매출 후보는 독립성 문제가 있어 반영하지 않았다.
2. 포항시는 초기 73.5%에서 최종 8.4%로 감소했다. 포항 2024 사업체조사 매출·종사자 후보가 전문서비스, 사업지원, 1차 금속, 정보통신, 환경·개인서비스의 잔여 오차를 크게 낮췄다.
3. 최종 기준에서도 남는 취약 산업은 고양 금융·보험 관련 서비스업, 고양 운수·창고, 고양 스포츠·오락, 포항 보험·연금, 포항 폐기물 처리 등이다. 추가 개선에는 최신 사업체조사 매출, 임금총액, 시설처리량, 물동량, 금융사업장 규모 자료가 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase83_final_middle_industry_accuracy_registry.csv")
    print(OUTDIR / "phase83_remaining_improvement_queue.csv")


if __name__ == "__main__":
    main()
