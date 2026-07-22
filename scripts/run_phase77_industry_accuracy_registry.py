#!/usr/bin/env python3
"""Phase77: integrated industry-level GVA accuracy registry.

The user-facing end goal is to say, industry by industry, how accurately GVA
was estimated.  Earlier phases each improved one family.  This script combines
the baseline middle-industry accuracy table with the specialized experiments
into one registry with consistent units:

    actual GVA, estimated GVA, absolute error in 억원, error rate %, decision.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase77_industry_accuracy_registry"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase77_industry_accuracy_registry.md"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "순위")) else "---" for _, label in cols) + " |")
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
        return "5% 이하"
    if rate <= 10:
        return "5~10%"
    if rate <= 20:
        return "10~20%"
    if rate <= 50:
        return "20~50%"
    return "50% 초과"


def baseline_rows() -> pd.DataFrame:
    df = pd.read_csv(DATA / "phase68_middle_industry_accuracy" / "phase68_middle_industry_accuracy_detail.csv")
    out = pd.DataFrame(
        {
            "city": df.city,
            "industry_level": "중분류",
            "parent_code": df.parent_section,
            "industry_code": df.middle_code.astype(str).str.zfill(2),
            "industry_name": df.middle_label,
            "model_family": "현행 소분류 합산 기준",
            "model_status": "baseline",
            "actual_gva_eok": df.actual_gva_eok,
            "predicted_gva_eok": df.predicted_gva_eok,
            "error_gva_eok": df.error_gva_eok,
            "error_rate_pct": df.error_rate_pct,
            "source_phase": "Phase68",
            "decision_note": "전 중분류 공통 기준선",
        }
    )
    return out


def append_health_welfare(rows: list[pd.DataFrame]) -> None:
    path = DATA / "phase73_goyang_health_welfare_split" / "phase73_goyang_health_welfare_split_detail.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    best = df[df.candidate.eq("의료면적 강화 기준")].copy()
    if best.empty:
        return
    rows.append(
        pd.DataFrame(
            {
                "city": "고양시",
                "industry_level": "중분류",
                "parent_code": "Q00",
                "industry_code": best.middle_code.astype(str).str.zfill(2),
                "industry_name": best.middle_label,
                "model_family": "의료면적 강화 기준",
                "model_status": "local_candidate",
                "actual_gva_eok": best.actual_gva_eok,
                "predicted_gva_eok": best.predicted_gva_eok,
                "error_gva_eok": best.error_gva_eok,
                "error_rate_pct": best.error_rate_pct,
                "source_phase": "Phase73",
                "decision_note": "고양 반복검증 전 지역 후보; 포항 복지정원 자료 필요",
            }
        )
    )


def append_realestate(rows: list[pd.DataFrame]) -> None:
    path = DATA / "phase74_realestate_small_split" / "phase74_realestate_small_split_detail.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    keep = df[df.candidate.isin(["현행 소분류 합산 기준", "재고가치/중개업소 포화 기준 K=500"])].copy()
    if keep.empty:
        return
    keep["status"] = np.where(keep.candidate.eq("현행 소분류 합산 기준"), "baseline_small", "two_city_candidate")
    rows.append(
        pd.DataFrame(
            {
                "city": keep.city,
                "industry_level": "소분류",
                "parent_code": "L00",
                "industry_code": keep.industry_code.astype(str),
                "industry_name": keep.industry_name,
                "model_family": keep.candidate,
                "model_status": keep.status,
                "actual_gva_eok": keep.actual_gva_eok,
                "predicted_gva_eok": keep.predicted_gva_eok,
                "error_gva_eok": keep.error_gva_eok,
                "error_rate_pct": keep.error_rate_pct,
                "source_phase": "Phase74",
                "decision_note": np.where(
                    keep.candidate.eq("현행 소분류 합산 기준"),
                    "부동산 소분류 기준선",
                    "고양·포항 모두 개선되지만 공통식 승격은 추가 지역 검증 필요",
                ),
            }
        )
    )


def append_construction(rows: list[pd.DataFrame]) -> None:
    path = DATA / "phase75_construction_middle_split" / "phase75_construction_middle_split_detail.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    keep = df[df.candidate.eq("허가 면적/건수 포화 K=1000")].copy()
    if keep.empty:
        return
    rows.append(
        pd.DataFrame(
            {
                "city": keep.city,
                "industry_level": "중분류",
                "parent_code": "F00",
                "industry_code": keep.middle_code.astype(str).str.zfill(2),
                "industry_name": keep.middle_label,
                "model_family": keep.candidate,
                "model_status": "two_city_candidate",
                "actual_gva_eok": keep.actual_gva_eok,
                "predicted_gva_eok": keep.predicted_gva_eok,
                "error_gva_eok": keep.error_gva_eok,
                "error_rate_pct": keep.error_rate_pct,
                "source_phase": "Phase75",
                "decision_note": "고양·포항 모두 개선. 포항 산업·창고 대형 프로젝트 완화 추가 검증 필요",
            }
        )
    )


def append_transport(rows: list[pd.DataFrame]) -> None:
    path = DATA / "phase76_transport_warehouse_split" / "phase76_transport_warehouse_split_detail.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    keep = df[df.candidate.eq("승객·창고 로그 기준 + 수상 현행유지")].copy()
    if keep.empty:
        return
    status = np.where(keep.middle_code.astype(str).str.zfill(2).eq("50"), "hold_water_transport", "two_city_candidate")
    note = np.where(
        keep.middle_code.astype(str).str.zfill(2).eq("50"),
        "항만 물동량 부재로 50 수상운송은 승격 보류",
        "승객·창고 활동지표로 49/52 분할 개선",
    )
    rows.append(
        pd.DataFrame(
            {
                "city": keep.city,
                "industry_level": "중분류",
                "parent_code": "H00",
                "industry_code": keep.middle_code.astype(str).str.zfill(2),
                "industry_name": keep.middle_label,
                "model_family": keep.candidate,
                "model_status": status,
                "actual_gva_eok": keep.actual_gva_eok,
                "predicted_gva_eok": keep.predicted_gva_eok,
                "error_gva_eok": keep.error_gva_eok,
                "error_rate_pct": keep.error_rate_pct,
                "source_phase": "Phase76",
                "decision_note": note,
            }
        )
    )


def append_pohang_manufacturing(rows: list[pd.DataFrame]) -> None:
    path = DATA / "phase71_pohang_manufacturing_stabilization" / "phase71_pohang_manufacturing_stabilization_detail.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    keep = df[df.candidate.eq("manufacturing_facility_area_all")].copy()
    if keep.empty:
        return
    rows.append(
        pd.DataFrame(
            {
                "city": "포항시",
                "industry_level": "중분류",
                "parent_code": "C00",
                "industry_code": keep.middle_code.astype(str).str.zfill(2),
                "industry_name": keep.middle_name,
                "model_family": "공장 제조시설면적 기준",
                "model_status": "two_city_missing_pohang_candidate",
                "actual_gva_eok": keep.actual_gva_eok,
                "predicted_gva_eok": keep.predicted_gva_eok,
                "error_gva_eok": keep.error_gva_eok,
                "error_rate_pct": keep.error_rate_pct,
                "source_phase": "Phase71",
                "decision_note": "포항 제조업 개선 후보. 고양 제조업 반복검증은 별도 필요",
            }
        )
    )


def selected_registry(registry: pd.DataFrame) -> pd.DataFrame:
    priority = {
        "two_city_candidate": 1,
        "local_candidate": 2,
        "two_city_missing_pohang_candidate": 3,
        "hold_water_transport": 4,
        "baseline_small": 8,
        "baseline": 9,
    }
    work = registry.copy()
    work["priority"] = work.model_status.map(priority).fillna(9)
    # For each city/level/code choose the best operational row.  For water
    # transport, hold_water_transport is retained as the current conservative
    # row because no port cargo feature exists.
    selected = work.sort_values(["city", "industry_level", "industry_code", "priority", "error_gva_eok"]).drop_duplicates(
        ["city", "industry_level", "industry_code"], keep="first"
    )
    return selected.drop(columns="priority")


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    parts: list[pd.DataFrame] = [baseline_rows()]
    append_health_welfare(parts)
    append_realestate(parts)
    append_construction(parts)
    append_transport(parts)
    append_pohang_manufacturing(parts)
    registry = pd.concat(parts, ignore_index=True)
    registry["accuracy_grade"] = registry.error_rate_pct.map(grade)
    registry = registry.sort_values(["city", "industry_level", "parent_code", "industry_code", "model_status"])
    selected = selected_registry(registry)
    selected["accuracy_grade"] = selected.error_rate_pct.map(grade)
    registry.to_csv(OUTDIR / "phase77_industry_accuracy_registry_all_models.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase77_industry_accuracy_registry_selected.csv", index=False, encoding="utf-8-sig")

    city_summary = (
        selected.groupby(["city", "industry_level"], as_index=False)
        .agg(
            cells=("industry_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("error_gva_eok", "sum"),
            median_error_pct=("error_rate_pct", "median"),
            over_50pct_cells=("error_rate_pct", lambda s: int((s > 50).sum())),
            within_10pct_cells=("error_rate_pct", lambda s: int((s <= 10).sum())),
        )
    )
    city_summary["wape_pct"] = city_summary.error_sum_eok / city_summary.actual_sum_eok * 100
    baseline_summary = (
        registry[registry.model_status.isin(["baseline", "baseline_small"])]
        .groupby(["city", "industry_level"], as_index=False)
        .agg(baseline_error_sum_eok=("error_gva_eok", "sum"), baseline_actual_sum_eok=("actual_gva_eok", "sum"))
    )
    baseline_summary["baseline_wape_pct"] = (
        baseline_summary.baseline_error_sum_eok / baseline_summary.baseline_actual_sum_eok * 100
    )
    city_summary = city_summary.merge(baseline_summary, on=["city", "industry_level"], how="left")
    city_summary["error_reduction_eok"] = city_summary.baseline_error_sum_eok - city_summary.error_sum_eok
    city_summary["wape_improvement_pp"] = city_summary.baseline_wape_pct - city_summary.wape_pct
    city_summary["error_reduction_pct"] = city_summary.error_reduction_eok / city_summary.baseline_error_sum_eok * 100
    status_summary = (
        selected.groupby(["city", "industry_level", "model_status"], as_index=False)
        .agg(cells=("industry_code", "count"), error_sum_eok=("error_gva_eok", "sum"))
        .sort_values(["city", "industry_level", "model_status"])
    )
    city_summary.to_csv(OUTDIR / "phase77_industry_accuracy_city_summary.csv", index=False, encoding="utf-8-sig")
    status_summary.to_csv(OUTDIR / "phase77_industry_accuracy_status_summary.csv", index=False, encoding="utf-8-sig")

    middle_selected = selected[selected.industry_level.eq("중분류")].copy()
    bad = middle_selected.sort_values(["city", "error_gva_eok"], ascending=[True, False]).groupby("city").head(12)
    good = middle_selected.sort_values(["city", "error_rate_pct"], ascending=[True, True]).groupby("city").head(10)
    improved = selected[~selected.model_status.isin(["baseline", "baseline_small"])].copy()
    improved = improved.sort_values(["city", "industry_level", "parent_code", "industry_code"])

    report = f"""# 산업별 GVA 추정 정확도 통합 장부

## 목적

이 보고서는 지금까지의 개별 실험을 하나의 장부로 통합해, **각 산업별 총부가가치(GVA)를 얼마나 정확히 추정했는가**를 같은 단위로 비교한다. 단위는 모두 억원이며, 오차율은 `|추정-실제| / 실제 × 100`이다.

## 장부 구성

- 기준선: Phase68 중분류 전체 실제·추정·오차
- 개선 후보: 보건·사회복지, 부동산, 건설, 운수·창고, 포항 제조업 특화 실험
- 선택 장부: 각 산업별로 현재 가장 운영 가능한 행을 선택하되, 반복검증이 부족한 후보는 상태값으로 표시

## 선택 장부 요약

{md_table(city_summary, [("city", "지역"), ("industry_level", "해상도"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("baseline_error_sum_eok", "기준선 오차 억원"), ("error_sum_eok", "선택 오차 억원"), ("baseline_wape_pct", "기준선 가중오차 %"), ("wape_pct", "선택 가중오차 %"), ("wape_improvement_pp", "개선 pp"), ("error_reduction_pct", "오차감소 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과")])}

## 상태별 적용 현황

{md_table(status_summary, [("city", "지역"), ("industry_level", "해상도"), ("model_status", "상태"), ("cells", "셀 수"), ("error_sum_eok", "오차합계 억원")])}

## 개선 후보가 반영된 산업

{md_table(improved, [("city", "지역"), ("industry_level", "해상도"), ("industry_code", "코드"), ("industry_name", "산업"), ("model_family", "선택 기준"), ("model_status", "상태"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 60)}

## 선택 장부 기준 금액오차 상위 중분류

{md_table(bad, [("city", "지역"), ("industry_code", "코드"), ("industry_name", "산업"), ("model_family", "선택 기준"), ("model_status", "상태"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 24)}

## 선택 장부 기준 오차율 낮은 중분류

{md_table(good, [("city", "지역"), ("industry_code", "코드"), ("industry_name", "산업"), ("model_family", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 20)}

## 해석

1. 이 장부의 모든 성능값은 실제 산업 GVA와 추정 산업 GVA의 격차로 계산했다.
2. 고양시는 보건·사회복지, 건설, 운수·창고에서 큰 개선 후보가 생겼다. 부동산은 소분류 장부로 별도 관리한다.
3. 포항시는 제조업, 건설, 운수·창고에서 개선 후보가 생겼지만, 제조업은 포항 중심 후보이고 수상운송은 항만 물동량 부재로 보류 상태다.
4. 이 장부는 포스터의 성능 수치 원천으로 쓸 수 있고, 다음 실험에서는 `model_status`가 baseline 또는 hold인 고오차 산업부터 줄이면 된다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase77_industry_accuracy_registry_selected.csv")
    print(OUTDIR / "phase77_industry_accuracy_city_summary.csv")


if __name__ == "__main__":
    main()
