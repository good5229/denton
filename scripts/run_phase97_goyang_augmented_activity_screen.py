#!/usr/bin/env python3
"""Phase97: augment the activity-indicator pool with Goyang local sources.

Phase95/96 used the Phase94 direct-indicator pool.  That pool contained useful
Pohang municipal survey signals but only limited Goyang signals.  This phase
adds Goyang indicators that can be mapped directly to KSIC middle industries:

* LOCALDATA business permissions by source type;
* Goyang health/welfare facility aggregates;
* Goyang bus passenger activity for land transport;
* Goyang factory-derived middle-industry weights.

The augmented pool is then evaluated twice:

1. strict no-middle-worse selection, for strong industry-accuracy claims;
2. protected weak-queue selection, for operational gap reduction.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "phase37_goyang_emd"
PHASE92 = DATA / "phase92_current_accuracy_after_grouped_transfer"
PHASE94 = DATA / "phase94_direct_activity_source_screen"
OUTDIR = DATA / "phase97_goyang_augmented_activity_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase97_goyang_augmented_activity_screen.md"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p95 = load_module("phase95", ROOT / "scripts" / "run_phase95_composite_activity_indicator_screen.py")
p96 = load_module("phase96", ROOT / "scripts" / "run_phase96_protected_weak_queue_selection.py")


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, **kwargs)


def active_localdata(frame: pd.DataFrame) -> pd.Series:
    status = frame.get("영업상태명", pd.Series("", index=frame.index)).astype(str)
    detail = frame.get("상세영업상태명", pd.Series("", index=frame.index)).astype(str)
    return status.str.contains("영업|정상", na=False) | detail.str.contains("영업|정상", na=False)


def active_count(slug: str) -> float:
    path = RAW / f"localdata_{slug}_goyang.csv"
    if not path.exists():
        return 0.0
    frame = read_csv(path, low_memory=False, dtype=str)
    return float(active_localdata(frame).sum())


def add_row(rows: list[dict], source_id: str, source_label: str, middle_code: str, value: float, family: str) -> None:
    if value <= 0:
        return
    rows.append(
        {
            "source_id": source_id,
            "source_label": source_label,
            "city": "고양시",
            "middle_code": str(middle_code).zfill(2),
            "indicator_value": float(value),
            "source_status": "current_local_public_activity",
            "source_family": family,
        }
    )


def goyang_local_indicators(reg: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []

    # Accommodation and food service.
    add_row(rows, "goyang_localdata_lodging_active", "고양 LOCALDATA 숙박업 영업재고", "55", active_count("lodgings") + active_count("tourist_accommodations"), "숙박·음식형")
    add_row(rows, "goyang_localdata_food_active", "고양 LOCALDATA 음식점 영업재고", "56", active_count("general_restaurants") + active_count("rest_cafes"), "숙박·음식형")

    # Health/welfare split.
    summary_path = DATA / "phase73_goyang_health_welfare_split" / "phase73_goyang_health_welfare_source_summary.csv"
    if summary_path.exists():
        s = pd.read_csv(summary_path).iloc[0]
        health_scale = float(s.health_facilities + s.health_beds / 10 + s.health_staff / 10 + s.health_area_sqm / 200)
        welfare_scale = float(s.welfare_facilities + s.welfare_capacity / 10)
        add_row(rows, "goyang_health_welfare_facility_scale", "고양 보건·복지 시설규모", "86", health_scale, "공공·비영리형")
        add_row(rows, "goyang_health_welfare_facility_scale", "고양 보건·복지 시설규모", "87", welfare_scale, "공공·비영리형")

    # Culture/sports/personal service permissions.
    add_row(rows, "goyang_localdata_culture_active", "고양 LOCALDATA 문화시설 영업재고", "90", active_count("performance_halls") + active_count("museums_and_art_galleries"), "공공·비영리형")
    add_row(
        rows,
        "goyang_localdata_sports_active",
        "고양 LOCALDATA 스포츠·오락 영업재고",
        "91",
        active_count("fitness_centers") + active_count("golf_practice_ranges") + active_count("billiard_halls") + active_count("martial_arts_dojo") + active_count("pc_bangs"),
        "공공·비영리형",
    )
    add_row(rows, "goyang_localdata_personal_active", "고양 LOCALDATA 개인서비스 영업재고", "96", active_count("beauty_salons") + active_count("barber_shops") + active_count("laundries") + active_count("public_baths"), "공공·비영리형")

    # Retail and land-transport activity.
    add_row(rows, "goyang_localdata_large_retail_active", "고양 대규모점포 영업재고", "47", active_count("large_scale_retail_stores"), "전문·지원서비스형")
    bus_path = DATA / "phase61_goyang_bus_emd" / "goyang_bus_emd_monthly.csv"
    if bus_path.exists():
        bus = pd.read_csv(bus_path)
        value = float(pd.to_numeric(bus.passenger_total, errors="coerce").sum())
        add_row(rows, "goyang_bus_passenger_total", "고양 버스 승하차 활동량", "49", value, "이동·물량형")

    # Factory-derived manufacturing middle weights.  These are not GVA; they
    # are facility-location activity weights that can be blended with the
    # current parent-balanced estimate.
    factory_path = DATA / "partial_stats_phase40_goyang_factory_small_weights.csv"
    if factory_path.exists():
        f = pd.read_csv(factory_path, dtype={"middle_code": str})
        f["middle_code"] = f.middle_code.astype(str).str.extract(r"(\d{2})")[0].str.zfill(2)
        fac = f.groupby("middle_code", as_index=False).allocated_factory_weight.sum()
        for r in fac.itertuples(index=False):
            add_row(rows, "goyang_factory_allocated_weight", "고양 공장등록 기반 제조업 활동가중치", r.middle_code, float(r.allocated_factory_weight), "생산시설형")

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    meta = reg[["city", "middle_code", "parent_code", "cause_group"]].drop_duplicates()
    out = out.merge(meta, on=["city", "middle_code"], how="inner")
    return out[out.indicator_value.gt(0)].copy()


def summarize_strict(selected: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    reference = reg.copy()
    reference["predicted_gva_eok"] = reference.reference_predicted_gva_eok
    reference["error_gva_eok"] = reference.reference_error_gva_eok
    reference["error_rate_pct"] = reference.reference_error_rate_pct
    reference["remaining_queue"] = np.where(reference.error_rate_pct.gt(10) | reference.error_gva_eok.gt(500), "추가개선대상", "현행유지가능")
    summary = pd.concat(
        [
            p95.summarize(reference, "Phase92 현재 기준"),
            p95.summarize(selected, "Phase97 고양증강 엄격 기준"),
        ],
        ignore_index=True,
    )
    base = summary[summary.model_stage.eq("Phase92 현재 기준")].set_index("city")
    summary["wape_improvement_pp"] = summary.apply(lambda r: base.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    summary["error_reduction_eok"] = summary.apply(lambda r: base.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)
    return summary


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = p95.load_registry()
    phase94_ind = pd.read_csv(PHASE94 / "phase94_direct_activity_indicators.csv")
    phase94_ind["middle_code"] = phase94_ind.middle_code.astype(str).str.zfill(2)
    goyang_ind = goyang_local_indicators(reg)
    augmented = pd.concat([phase94_ind, goyang_ind], ignore_index=True).drop_duplicates(
        ["source_id", "city", "middle_code", "indicator_value"]
    )

    strict_options = p95.build_options(reg, augmented)
    strict_options["is_queue"] = strict_options.phase92_queue.ne("현행유지가능")
    strict_options["ref_error_rate_pct"] = (
        strict_options.reference_error_gva_eok / strict_options.actual_gva_eok.replace(0, np.nan) * 100
    )
    strict_raw, strict_scorecard, _ = p95.select_options(strict_options)
    strict_selected = p95.finalize(strict_raw)
    strict_summary = summarize_strict(strict_selected, reg)
    strict_acct = p95.accounting_check(strict_selected)
    strict_audit = strict_selected[strict_selected.error_gva_eok.gt(strict_selected.reference_error_gva_eok + 1e-9)].copy()
    strict_choices = (
        strict_scorecard.merge(strict_selected[["city", "parent_code", "option_name"]].drop_duplicates(), on=["city", "parent_code", "option_name"], how="inner")
        .sort_values(["city", "error_reduction_eok"], ascending=[True, False])
    )

    protected_raw, protected_scorecard = p96.select(strict_options)
    protected_selected = p96.finalize(protected_raw)
    protected_acct = p96.accounting_check(protected_selected)
    protected_grade_audit = protected_selected[protected_selected.grade_boundary_worse].copy()
    reference_options = strict_options[strict_options.option_name.eq("Phase92 현재 기준")].copy()
    reference_options["remaining_queue"] = np.where(
        reference_options.error_rate_pct.gt(10) | reference_options.error_gva_eok.gt(500),
        "추가개선대상",
        "현행유지가능",
    )
    protected_summary = pd.concat(
        [
            p96.summarize(reference_options, "Phase92 현재 기준"),
            p96.summarize(protected_selected, "Phase97 고양증강 취약큐 보호"),
        ],
        ignore_index=True,
    )
    base = protected_summary[protected_summary.model_stage.eq("Phase92 현재 기준")].set_index("city")
    protected_summary["wape_improvement_pp"] = protected_summary.apply(lambda r: base.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    protected_summary["error_reduction_eok"] = protected_summary.apply(lambda r: base.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)
    protected_choices = (
        protected_scorecard.merge(protected_selected[["city", "parent_code", "option_name"]].drop_duplicates(), on=["city", "parent_code", "option_name"], how="inner")
        .sort_values(["city", "queue_error_reduction_eok"], ascending=[True, False])
    )
    protected_improved_choices = protected_choices[protected_choices.queue_error_reduction_eok.gt(1e-9)].copy()
    protected_improved_cells = protected_selected[protected_selected.error_reduction_eok.gt(1e-9)].sort_values(
        ["city", "error_reduction_eok"], ascending=[True, False]
    )
    protected_worse_cells = protected_selected[protected_selected.error_reduction_eok.lt(-1e-9)].sort_values(
        ["city", "error_reduction_eok"], ascending=[True, True]
    )
    protected_remaining = protected_selected[protected_selected.remaining_queue.eq("추가개선대상")].sort_values(
        ["city", "error_gva_eok"], ascending=[True, False]
    )

    augmented.to_csv(OUTDIR / "phase97_augmented_activity_indicators.csv", index=False, encoding="utf-8-sig")
    goyang_ind.to_csv(OUTDIR / "phase97_goyang_added_activity_indicators.csv", index=False, encoding="utf-8-sig")
    strict_options.to_csv(OUTDIR / "phase97_augmented_activity_options.csv", index=False, encoding="utf-8-sig")
    strict_scorecard.to_csv(OUTDIR / "phase97_strict_parent_scorecard.csv", index=False, encoding="utf-8-sig")
    strict_selected.to_csv(OUTDIR / "phase97_strict_selected_registry.csv", index=False, encoding="utf-8-sig")
    strict_summary.to_csv(OUTDIR / "phase97_strict_summary.csv", index=False, encoding="utf-8-sig")
    strict_acct.to_csv(OUTDIR / "phase97_strict_accounting_checks.csv", index=False, encoding="utf-8-sig")
    strict_audit.to_csv(OUTDIR / "phase97_strict_no_worsening_audit.csv", index=False, encoding="utf-8-sig")
    protected_scorecard.to_csv(OUTDIR / "phase97_protected_parent_scorecard.csv", index=False, encoding="utf-8-sig")
    protected_selected.to_csv(OUTDIR / "phase97_protected_selected_registry.csv", index=False, encoding="utf-8-sig")
    protected_summary.to_csv(OUTDIR / "phase97_protected_summary.csv", index=False, encoding="utf-8-sig")
    protected_acct.to_csv(OUTDIR / "phase97_protected_accounting_checks.csv", index=False, encoding="utf-8-sig")
    protected_grade_audit.to_csv(OUTDIR / "phase97_protected_grade_boundary_audit.csv", index=False, encoding="utf-8-sig")
    protected_worse_cells.to_csv(OUTDIR / "phase97_protected_worsened_cells.csv", index=False, encoding="utf-8-sig")
    protected_remaining.to_csv(OUTDIR / "phase97_protected_remaining_queue.csv", index=False, encoding="utf-8-sig")

    strict_improved_choices = strict_choices[strict_choices.error_reduction_eok.gt(1e-9)].copy()
    report = f"""# 고양 로컬 활동자료 증강에 의한 중분류 GVA 격차 재검증

## 목적

포항은 2024 사업체조사 활동자료가 있어 취약 중분류 오차를 줄일 수 있었지만, 고양은 Phase95/96 후보군에서 직접 활동자료가 부족했다. 이번 단계에서는 고양 LOCALDATA, 보건·복지 시설규모, 버스 승하차, 공장등록 기반 제조업 활동가중치를 KSIC 중분류에 직접 연결되는 경우에만 추가했다.

## 추가한 고양 활동지표

{p95.md_table(goyang_ind.groupby(["source_id", "source_label", "source_status", "source_family", "parent_code"], as_index=False).agg(cells=("middle_code", "nunique"), indicator_sum=("indicator_value", "sum")), [("source_id", "자료ID"), ("source_label", "자료명"), ("source_family", "유형"), ("parent_code", "상위산업"), ("cells", "중분류 수"), ("indicator_sum", "지표합계")], 80)}

## 엄격 기준 요약

{p95.md_table(strict_summary.sort_values(["city", "model_stage"]), [("city", "지역"), ("model_stage", "단계"), ("cells", "중분류 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_20pct_cells", "20% 초과"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "추가개선대상"), ("wape_improvement_pp", "개선 pp"), ("error_reduction_eok", "감소 억원")])}

## 엄격 기준 채택 후보

{p95.md_table(strict_improved_choices, [("city", "지역"), ("parent_code", "상위산업"), ("option_name", "선택 기준"), ("option_family", "기준 유형"), ("parent_error_eok", "상위산업 오차 억원"), ("parent_wape_pct", "상위산업 오차 %"), ("error_reduction_eok", "감소 억원"), ("gap10_reduction_eok", "10%초과 감소 억원"), ("worse_cells", "악화 셀")], 80)}

## 취약큐 보호 기준 요약

{p95.md_table(protected_summary.sort_values(["city", "model_stage"]), [("city", "지역"), ("model_stage", "단계"), ("cells", "중분류 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_20pct_cells", "20% 초과"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "추가개선대상"), ("wape_improvement_pp", "개선 pp"), ("error_reduction_eok", "감소 억원")])}

## 취약큐 보호 기준 채택 후보

{p95.md_table(protected_improved_choices, [("city", "지역"), ("parent_code", "상위산업"), ("option_name", "선택 기준"), ("option_family", "기준 유형"), ("parent_error_eok", "상위산업 오차 억원"), ("parent_wape_pct", "상위산업 오차 %"), ("parent_error_reduction_eok", "상위산업 감소 억원"), ("queue_error_reduction_eok", "취약큐 감소 억원"), ("queue_gap10_reduction_eok", "10%초과 감소 억원"), ("grade_boundary_worse_cells", "판정악화 셀")], 80)}

## 취약큐 보호 기준에서 오차가 줄어든 중분류

{p95.md_table(protected_improved_cells, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("option_name", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("error_reduction_eok", "감소 억원")], 80)}

## 취약큐 보호 기준에서 오차가 증가한 중분류

{p95.md_table(protected_worse_cells, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("option_name", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("error_reduction_eok", "감소 억원")], 60)}

## 남은 개선 큐

{p95.md_table(protected_remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("option_name", "현재 선택 기준")], 100)}

## 감사

- 엄격 기준 상위산업 합계 불일치: {int((~strict_acct["pass"]).sum())}개
- 엄격 기준 개별 중분류 악화: {len(strict_audit)}개
- 취약큐 보호 기준 상위산업 합계 불일치: {int((~protected_acct["pass"]).sum())}개
- 취약큐 보호 기준 판정 구간 악화: {len(protected_grade_audit)}개

## 판정

1. 고양 로컬자료를 추가해도 엄격 기준과 취약큐 보호 기준 모두에서 고양의 신규 채택 후보는 없다. 이는 협회·단체, 방송, 연구개발, 과학기술 등 남은 취약 산업에 직접 연결되는 활동자료가 부족하기 때문이다.
2. 중분류와 직접 연결 가능한 고양 LOCALDATA는 숙박·음식, 보건·복지, 문화·스포츠·개인서비스, 대규모점포, 버스, 제조업 공장가중치 정도다.
3. 포항처럼 시 자체 사업체조사 중분류 매출·종사자·사업체 자료가 제공되면 고양도 같은 방식으로 개선 가능성이 크다.
4. 다음 자료 확보 우선순위는 고양 협회·단체 활동규모, 방송·콘텐츠 사업장 규모, 연구개발·과학기술 인력/계약, 자동차판매 등록·매출, 제조업 세부 출하·전력이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase97_strict_summary.csv")
    print(OUTDIR / "phase97_protected_summary.csv")


if __name__ == "__main__":
    main()
