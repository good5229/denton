#!/usr/bin/env python3
"""Phase70: Pohang steel-heavy manufacturing scale proxy experiment.

The largest Pohang middle-industry error is primary metal manufacturing
(KSIC 24).  The common proxy underestimates it because a single integrated
steelworks is not comparable to one ordinary factory.  This experiment compares
available free factory-scale variables against the current common proxy.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "public_data_portal" / "factory_full_snapshot_15106170_download.csv"
ACCURACY = DATA / "phase68_middle_industry_accuracy" / "phase68_middle_industry_accuracy_detail.csv"
HIERARCHY = DATA / "phase64_hierarchical_aggregate_validation" / "phase64_small_to_middle_aggregate_validation_detail.csv"
OUTDIR = DATA / "phase70_pohang_steel_factory_scale"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase70_pohang_steel_factory_scale.md"


SCALE_COLUMNS = {
    "factory_count": "공장 수",
    "employee_count": "종업원합계",
    "land_area": "용지면적",
    "manufacturing_facility_area": "제조시설면적",
    "building_area": "건축면적",
    "support_facility_area": "부대시설면적",
    "parcel_count": "필지수",
}


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int = 20) -> str:
    if df.empty:
        return "\n해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "pp")) else "---" for _, label in cols) + " |")
    for _, row in df.head(limit).iterrows():
        vals = []
        for key, _ in cols:
            val = row[key]
            if isinstance(val, float):
                vals.append(f"{val:,.1f}")
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def load_pohang_manufacturing_factories() -> pd.DataFrame:
    raw = pd.read_csv(RAW, encoding="cp949", low_memory=False)
    pohang = raw[
        raw["시도명"].astype(str).str.contains("경상북도", na=False)
        & raw["시군구명"].astype(str).str.contains("포항", na=False)
    ].copy()
    for korean_col in SCALE_COLUMNS.values():
        if korean_col != "공장 수":
            pohang[korean_col] = pd.to_numeric(pohang[korean_col], errors="coerce").fillna(0).clip(lower=0)
    pohang["대표업종"] = pd.to_numeric(pohang["대표업종"], errors="coerce")
    pohang["middle_code"] = pohang["대표업종"].dropna().astype(int).astype(str).str.zfill(5).str[:2]
    manufacturing = pohang[pohang.middle_code.astype(str).str.match(r"^(1[0-9]|2[0-9]|3[0-4])$", na=False)].copy()
    return manufacturing


def candidate_shares(factories: pd.DataFrame, actual_codes: list[str]) -> dict[str, dict[str, float]]:
    candidates: dict[str, dict[str, float]] = {}
    weights: dict[str, pd.Series] = {
        "factory_count": pd.Series(1.0, index=factories.index),
        "employee_count": factories["종업원합계"],
        "land_area": factories["용지면적"],
        "manufacturing_facility_area": factories["제조시설면적"],
        "building_area": factories["건축면적"],
        "support_facility_area": factories["부대시설면적"],
        "parcel_count": factories["필지수"],
    }
    for name, weight in weights.items():
        w = pd.to_numeric(weight, errors="coerce").fillna(0).clip(lower=0)
        if float(w.sum()) <= 0:
            w = pd.Series(1.0, index=factories.index)
        sums = w.groupby(factories.middle_code).sum()
        total = float(sums.sum())
        candidates[name] = {code: float(sums.get(code, 0.0) / total) for code in actual_codes}

    normalized = []
    for name in ["employee_count", "land_area", "manufacturing_facility_area", "building_area"]:
        w = weights[name]
        normalized.append(w / w.sum() if float(w.sum()) > 0 else w)
    composite = sum(normalized) / len(normalized)
    sums = composite.groupby(factories.middle_code).sum()
    total = float(sums.sum())
    candidates["avg_employee_land_mfg_building_area"] = {code: float(sums.get(code, 0.0) / total) for code in actual_codes}
    return candidates


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    hierarchy = pd.read_csv(HIERARCHY)
    c_actual = hierarchy[
        hierarchy.city.eq("포항시")
        & hierarchy.parent_section.eq("C00")
        & hierarchy.actual_middle_share.between(0.001, 0.999)
    ].copy()
    c_actual["middle_code"] = c_actual.middle_code.astype(str).str.zfill(2)
    actual_codes = sorted(c_actual.middle_code.tolist())
    actual_share = dict(zip(c_actual.middle_code, c_actual.actual_middle_share))
    current_share = dict(zip(c_actual.middle_code, c_actual.predicted_small_aggregated_share))

    accuracy = pd.read_csv(ACCURACY)
    c_acc = accuracy[accuracy.city.eq("포항시") & accuracy.parent_section.eq("C00")].copy()
    parent_gva_eok = float((c_acc.actual_gva_eok / c_acc.actual_middle_share).median())

    factories = load_pohang_manufacturing_factories()
    candidates = {"current_common_proxy": current_share}
    candidates.update(candidate_shares(factories, actual_codes))

    detail_rows = []
    summary_rows = []
    for candidate, shares in candidates.items():
        for code in actual_codes:
            actual = actual_share[code]
            pred = shares.get(code, 0.0)
            actual_eok = actual * parent_gva_eok
            pred_eok = pred * parent_gva_eok
            detail_rows.append(
                {
                    "candidate": candidate,
                    "middle_code": code,
                    "actual_share_pct": actual * 100,
                    "predicted_share_pct": pred * 100,
                    "abs_error_pp": abs(pred - actual) * 100,
                    "actual_gva_eok": actual_eok,
                    "predicted_gva_eok": pred_eok,
                    "error_gva_eok": abs(pred_eok - actual_eok),
                    "error_rate_pct": abs(pred_eok - actual_eok) / actual_eok * 100 if actual_eok else np.nan,
                }
            )
    detail = pd.DataFrame(detail_rows)
    detail = detail.merge(c_actual[["middle_code", "middle_name"]], on="middle_code", how="left")
    for candidate, sub in detail.groupby("candidate"):
        metal = sub[sub.middle_code.eq("24")].iloc[0]
        summary_rows.append(
            {
                "candidate": candidate,
                "manufacturing_wape_pct": sub.error_gva_eok.sum() / sub.actual_gva_eok.sum() * 100,
                "manufacturing_mae_pp": sub.abs_error_pp.mean(),
                "primary_metal_predicted_share_pct": metal.predicted_share_pct,
                "primary_metal_error_gva_eok": metal.error_gva_eok,
                "primary_metal_error_rate_pct": metal.error_rate_pct,
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values("manufacturing_wape_pct")
    detail.to_csv(OUTDIR / "phase70_pohang_steel_factory_scale_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase70_pohang_steel_factory_scale_summary.csv", index=False, encoding="utf-8-sig")

    base = summary[summary.candidate.eq("current_common_proxy")].iloc[0]
    best = summary.iloc[0]
    selected_name = str(best.candidate)
    selected_detail = detail[detail.candidate.eq(selected_name)].sort_values("error_gva_eok", ascending=False)
    current_detail = detail[detail.candidate.eq("current_common_proxy")].sort_values("error_gva_eok", ascending=False)
    improvement = {
        "wape_delta_pp": float(base.manufacturing_wape_pct - best.manufacturing_wape_pct),
        "wape_reduction_pct": float((base.manufacturing_wape_pct - best.manufacturing_wape_pct) / base.manufacturing_wape_pct * 100),
        "metal_error_delta_eok": float(base.primary_metal_error_gva_eok - best.primary_metal_error_gva_eok),
        "metal_error_reduction_pct": float((base.primary_metal_error_gva_eok - best.primary_metal_error_gva_eok) / base.primary_metal_error_gva_eok * 100),
    }

    report = f"""# 포항 1차 금속 제조업 오차축소 1차 실험

## 목적

포항시 중분류 GVA 추정에서 가장 큰 오차는 1차 금속 제조업이다. 기존 공통모델은 실제 47,010억 원 규모의 1차 금속 제조업을 15,774억 원으로 추정해 31,237억 원 과소추정했다. 이번 실험은 무료 공장등록 원자료의 규모 변수로 제조업 내부 배분을 바꾸면 오차가 얼마나 줄어드는지 확인한다.

## 사용 자료

- 공공데이터포털 공장등록 전체 스냅샷: 종업원합계, 용지면적, 제조시설면적, 부대시설면적, 건축면적, 필지수
- 포항시 2015 경제총조사 중분류 검증비중
- 2023년 포항시 제조업 GVA 총량

## 후보별 성능

{md_table(summary, [("candidate", "후보"), ("manufacturing_wape_pct", "제조업 WAPE %"), ("manufacturing_mae_pp", "제조업 MAE pp"), ("primary_metal_predicted_share_pct", "1차금속 추정비중 %"), ("primary_metal_error_gva_eok", "1차금속 오차 억원"), ("primary_metal_error_rate_pct", "1차금속 오차 %")])}

## 선택 후보

가장 성능이 좋은 후보는 `제조시설면적` 배분이다. 제조업 전체 WAPE는 {base.manufacturing_wape_pct:.1f}%에서 {best.manufacturing_wape_pct:.1f}%로 낮아졌고, 1차 금속 제조업 오차는 {base.primary_metal_error_gva_eok:,.0f}억 원에서 {best.primary_metal_error_gva_eok:,.0f}억 원으로 줄었다.

- 제조업 WAPE 개선: {improvement['wape_delta_pp']:.1f}%p, 상대 개선 {improvement['wape_reduction_pct']:.1f}%
- 1차 금속 오차 개선: {improvement['metal_error_delta_eok']:,.0f}억 원 감소, 상대 개선 {improvement['metal_error_reduction_pct']:.1f}%

## 기존 공통모델의 금액오차 상위

{md_table(current_detail, [("middle_name", "중분류"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 10)}

## 제조시설면적 후보의 금액오차 상위

{md_table(selected_detail, [("middle_name", "중분류"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 10)}

## 판정

- 포항 1차 금속 제조업은 공장 수가 아니라 공장 규모 변수로 배분해야 한다.
- 보유 무료자료만으로도 1차 금속 제조업 오차율을 {base.primary_metal_error_rate_pct:.1f}%에서 {best.primary_metal_error_rate_pct:.1f}%로 낮출 수 있다.
- 아직 목표인 10% 전후에는 부족하다. 추가 개선에는 사업장별 산업용 전력, 제철 생산·출하, 산단 대형사업장 가중치가 필요하다.
- 다음 실험은 `제조시설면적 + 산업용 전력 + 대형 제철소 앵커` 조합을 사전 정의하고, 제조업 전체 WAPE가 더 낮아지는지 확인하는 것이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase70_pohang_steel_factory_scale_summary.csv")
    print(OUTDIR / "phase70_pohang_steel_factory_scale_detail.csv")


if __name__ == "__main__":
    main()
