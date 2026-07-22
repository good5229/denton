#!/usr/bin/env python3
"""Phase81: final middle-industry accuracy registry after bulk remediation.

The registry is the user-facing answer to "how accurately did we estimate each
industry?"  It joins the original baseline, Phase79 safe result, and Phase80
external-candidate result for every Goyang/Pohang middle-industry cell.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase81_middle_industry_accuracy_registry"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase81_middle_industry_accuracy_registry.md"


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


def load_registry() -> pd.DataFrame:
    baseline = pd.read_csv(DATA / "phase68_middle_industry_accuracy" / "phase68_middle_industry_accuracy_detail.csv")
    baseline["middle_code"] = baseline.middle_code.astype(str).str.zfill(2)
    baseline = baseline.rename(
        columns={
            "parent_section": "parent_code",
            "predicted_gva_eok": "baseline_predicted_gva_eok",
            "error_gva_eok": "baseline_error_gva_eok",
            "error_rate_pct": "baseline_error_rate_pct",
        }
    )[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "baseline_predicted_gva_eok",
            "baseline_error_gva_eok",
            "baseline_error_rate_pct",
        ]
    ]

    phase79 = pd.read_csv(DATA / "phase79_cross_region_bias_transfer" / "phase79_parent_selected_cell_safe_detail.csv")
    phase79["middle_code"] = phase79.middle_code.astype(str).str.zfill(2)
    phase79 = phase79.rename(
        columns={
            "parent_section": "parent_code",
            "predicted_gva_eok": "phase79_predicted_gva_eok",
            "error_gva_eok": "phase79_error_gva_eok",
            "error_rate_pct": "phase79_error_rate_pct",
            "model_family": "phase79_model_family",
            "model_status": "phase79_model_status",
        }
    )[
        [
            "city",
            "parent_code",
            "middle_code",
            "phase79_model_family",
            "phase79_model_status",
            "phase79_predicted_gva_eok",
            "phase79_error_gva_eok",
            "phase79_error_rate_pct",
        ]
    ]

    final = pd.read_csv(DATA / "phase80_external_activity_candidate_screen" / "phase80_external_candidate_selected.csv")
    final["middle_code"] = final.middle_code.astype(str).str.zfill(2)
    final = final.rename(
        columns={
            "parent_section": "parent_code",
            "model_family": "final_model_family",
            "model_status": "final_model_status",
            "predicted_gva_eok": "final_predicted_gva_eok",
            "error_gva_eok": "final_error_gva_eok",
            "error_rate_pct": "final_error_rate_pct",
        }
    )
    keep_cols = [
        "city",
        "parent_code",
        "middle_code",
        "final_model_family",
        "final_model_status",
        "selected_candidate_name",
        "selection_note",
        "final_predicted_gva_eok",
        "final_error_gva_eok",
        "final_error_rate_pct",
    ]
    final = final[keep_cols]

    reg = baseline.merge(phase79, on=["city", "parent_code", "middle_code"], how="left").merge(
        final, on=["city", "parent_code", "middle_code"], how="left"
    )
    reg["baseline_to_final_error_reduction_eok"] = reg.baseline_error_gva_eok - reg.final_error_gva_eok
    reg["baseline_to_final_error_reduction_pct"] = (
        reg.baseline_to_final_error_reduction_eok / reg.baseline_error_gva_eok.replace(0, np.nan) * 100
    )
    reg["phase79_to_final_error_reduction_eok"] = reg.phase79_error_gva_eok - reg.final_error_gva_eok
    reg["phase79_to_final_error_reduction_pct"] = (
        reg.phase79_to_final_error_reduction_eok / reg.phase79_error_gva_eok.replace(0, np.nan) * 100
    )
    reg["final_accuracy_grade"] = reg.final_error_rate_pct.map(grade)
    reg["remaining_queue"] = np.where(
        reg.final_error_rate_pct.gt(50) | reg.final_error_gva_eok.gt(1000),
        "추가개선대상",
        "현행유지가능",
    )
    return reg


def summarize(reg: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, err_col, rate_col in [
        ("초기 기준", "baseline_error_gva_eok", "baseline_error_rate_pct"),
        ("Phase79 악화방지", "phase79_error_gva_eok", "phase79_error_rate_pct"),
        ("Phase80 최종", "final_error_gva_eok", "final_error_rate_pct"),
    ]:
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
            .assign(model_stage=label)
        )
        g["wape_pct"] = g.error_sum_eok / g.actual_sum_eok * 100
        rows.append(g)
    out = pd.concat(rows, ignore_index=True)
    baseline_error = out[out.model_stage.eq("초기 기준")].set_index("city").error_sum_eok.to_dict()
    baseline_wape = out[out.model_stage.eq("초기 기준")].set_index("city").wape_pct.to_dict()
    out["baseline_error_reduction_eok"] = out.apply(lambda r: baseline_error[r.city] - r.error_sum_eok, axis=1)
    out["baseline_error_reduction_pct"] = out.apply(lambda r: r.baseline_error_reduction_eok / baseline_error[r.city] * 100, axis=1)
    out["baseline_wape_improvement_pp"] = out.apply(lambda r: baseline_wape[r.city] - r.wape_pct, axis=1)
    return out.sort_values(["city", "error_sum_eok"])


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = load_registry()
    summary = summarize(reg)
    good = reg.sort_values(["city", "final_error_rate_pct"]).groupby("city").head(15)
    weak = reg[reg.remaining_queue.eq("추가개선대상")].sort_values(["city", "final_error_gva_eok"], ascending=[True, False])
    improved = reg[reg.baseline_to_final_error_reduction_eok.gt(0)].sort_values(
        ["city", "baseline_to_final_error_reduction_eok"], ascending=[True, False]
    )
    worsened = reg[reg.baseline_to_final_error_reduction_eok.lt(-1e-9)].sort_values(
        ["city", "baseline_to_final_error_reduction_eok"]
    )

    reg.to_csv(OUTDIR / "phase81_middle_industry_accuracy_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase81_middle_industry_accuracy_summary.csv", index=False, encoding="utf-8-sig")
    weak.to_csv(OUTDIR / "phase81_remaining_improvement_queue.csv", index=False, encoding="utf-8-sig")

    report = f"""# 중분류 산업별 GVA 추정 정확도 레지스트리

## 목적

각 산업별로 총부가가치(GVA)를 얼마나 정확히 추정했는지 한 표로 관리하기 위해 초기 기준, Phase79 악화방지 기준, Phase80 외부 활동지표 검증통과 기준을 연결했다. 모든 금액은 억원이고, 오차율은 `|추정 GVA-실제 GVA|/실제 GVA×100`이다.

## 단계별 전체 성능

{md_table(summary, [("city", "지역"), ("model_stage", "단계"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("baseline_wape_improvement_pp", "초기대비 개선 pp"), ("baseline_error_reduction_pct", "초기대비 감소 %")])}

## 개선 폭 상위 산업

{md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("baseline_predicted_gva_eok", "초기 추정 억원"), ("baseline_error_gva_eok", "초기 오차 억원"), ("final_predicted_gva_eok", "최종 추정 억원"), ("final_error_gva_eok", "최종 오차 억원"), ("final_error_rate_pct", "최종 오차 %"), ("baseline_to_final_error_reduction_eok", "감소 억원"), ("final_model_family", "최종 기준")], 60)}

## 예측 양호 산업 예시

{md_table(good, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("final_predicted_gva_eok", "최종 추정 억원"), ("final_error_gva_eok", "오차 억원"), ("final_error_rate_pct", "오차 %"), ("final_accuracy_grade", "판정")], 40)}

## 추가개선대상 산업

{md_table(weak, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("final_predicted_gva_eok", "최종 추정 억원"), ("final_error_gva_eok", "오차 억원"), ("final_error_rate_pct", "오차 %"), ("final_model_family", "최종 기준")], 80)}

## 악화 점검

초기 기준보다 최종 오차가 악화된 셀 수: {len(worsened)}개.

{md_table(worsened, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("baseline_error_gva_eok", "초기 오차 억원"), ("final_error_gva_eok", "최종 오차 억원"), ("baseline_to_final_error_reduction_eok", "감소 억원")], 40)}

## 판정

1. 고양시는 초기 중분류 가중오차 44.1%에서 최종 13.0%로 내려갔다. 외부 제조업 활동지표가 제조업 중분류 다수를 10% 안팎으로 낮췄다.
2. 포항시는 초기 73.5%에서 최종 22.2%로 내려갔다. 1차 금속 제조업은 66.4%에서 10.4%, 금속가공제품 제조업은 187.9%에서 3.6%, 농업·임업은 0.0%까지 개선됐다.
3. 남은 취약 산업은 전문·사업지원, 금융·보험, 환경·개인서비스, 정보통신 일부다. 이들은 사업체 수보다 법인규모, 임금총액, 매출, 시설처리량, 네트워크 인프라 같은 가치·규모형 자료가 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase81_middle_industry_accuracy_registry.csv")
    print(OUTDIR / "phase81_remaining_improvement_queue.csv")


if __name__ == "__main__":
    main()
