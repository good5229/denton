#!/usr/bin/env python3
"""Phase113: Goyang OpenAPI constrained refined-error experiment.

The experiment uses Goyang OpenAPI/local public activity data as post-publication
refinement indicators.  It does not change flash/nowcast error, because most
Goyang OpenAPI endpoints are current snapshots.

Candidate rules are evaluated at city×parent-industry level:

    pred = (1-alpha) * current_parent-balanced_pred
           + alpha * parent_actual_total * indicator_share

The adopted "operational" rule is intentionally less brittle than the previous
no-single-cell-worse rule:

* parent absolute error must decline;
* number of >10% middle cells must not increase;
* high-value middle cells must not materially worsen;
* total worsening amount is capped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUTDIR = DATA / "phase113_goyang_openapi_constrained_refinement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase113_goyang_openapi_constrained_refinement.md"
BASE_REGISTRY = DATA / "phase105_no_worse_refinement_guardrail" / "phase105_no_worse_refinement_registry.csv"
SAUPM78_RAW = RAW / "phase111_saupm78_2024_all_total_size.json"


def load_json_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce").fillna(0.0)


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False)


def active_localdata_count(slug: str) -> float:
    path = RAW / "phase37_goyang_emd" / f"localdata_{slug}_goyang.csv"
    if not path.exists():
        return 0.0
    df = read_csv_any(path)
    status = df.get("영업상태명", pd.Series("", index=df.index)).astype(str)
    detail = df.get("상세영업상태명", pd.Series("", index=df.index)).astype(str)
    return float((status.str.contains("영업|정상", na=False) | detail.str.contains("영업|정상", na=False)).sum())


def load_base() -> pd.DataFrame:
    df = pd.read_csv(BASE_REGISTRY)
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    return df[df["city"].eq("고양시")].copy()


def add(rows: list[dict[str, Any]], source_id: str, label: str, parent: str, code: str, value: float, raw_unit: str, timing: str) -> None:
    if value and np.isfinite(value) and value > 0:
        rows.append(
            {
                "source_id": source_id,
                "source_label": label,
                "parent_code": parent,
                "middle_code": str(code).zfill(2),
                "indicator_raw_value": float(value),
                "indicator_value": float(np.log1p(value)),
                "raw_unit": raw_unit,
                "timing_track": timing,
            }
        )


def build_indicators() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    # Goyang OpenAPI samples.
    sports = load_json_frame(RAW / "phase112_goyang_openapi_alsfcSttus.json")
    parks = load_json_frame(RAW / "phase112_goyang_openapi_ctyparkInfo.json")
    buildings = load_json_frame(RAW / "phase112_goyang_openapi_bildTitleledger.json")
    apt = load_json_frame(RAW / "phase112_goyang_openapi_aptDlpc.json")
    hospitals = load_json_frame(RAW / "phase112_goyang_openapi_hsptlAsembySttus.json")
    parking = load_json_frame(RAW / "phase112_goyang_openapi_prkplceInfoSttus.json")
    libraries = load_json_frame(RAW / "phase112_goyang_openapi_lbrrySttus.json")

    # ERS: culture/sports/personal/water-waste.
    add(rows, "goyang_openapi_sports_facilities", "고양 체육시설 수", "ERS", "91", len(sports), "시설수", "정밀화")
    if not parks.empty and "park_area" in parks:
        add(rows, "goyang_openapi_park_area", "고양 도시공원 면적", "ERS", "91", float(num(parks["park_area"]).sum()), "㎡", "정밀화")
    if not buildings.empty and "main_prpos_cd_nm" in buildings:
        purpose = buildings["main_prpos_cd_nm"].astype(str)
        # Culture/sports related buildings.
        add(rows, "goyang_openapi_culture_building_count", "문화·집회 건축물 수", "ERS", "90", float(purpose.str.contains("문화|집회", na=False).sum()), "동", "정밀화")
        add(rows, "goyang_openapi_sports_building_count", "운동시설 건축물 수", "ERS", "91", float(purpose.str.contains("운동시설", na=False).sum()), "동", "정밀화")
        add(rows, "goyang_openapi_waste_building_count", "분뇨·쓰레기·자원순환 건축물 수", "ERS", "38", float(purpose.str.contains("분뇨|쓰레기|자원순환", na=False).sum()), "동", "정밀화")
        add(rows, "goyang_openapi_auto_building_count", "자동차관련 건축물 수", "G00", "45", float(purpose.str.contains("자동차", na=False).sum()), "동", "정밀화")
        add(rows, "goyang_openapi_retail_building_count", "판매·근린생활 건축물 수", "G00", "47", float(purpose.str.contains("판매|근린생활", na=False).sum()), "동", "정밀화")
        add(rows, "goyang_openapi_business_building_count", "업무시설 건축물 수", "MN0", "71", float(purpose.str.contains("업무시설", na=False).sum()), "동", "정밀화")
        add(rows, "goyang_openapi_research_building_count", "교육연구시설 건축물 수", "MN0", "70", float(purpose.str.contains("교육연구", na=False).sum()), "동", "정밀화")
        add(rows, "goyang_openapi_facility_management_count", "대형 관리대상 건축물 수", "MN0", "74", float(len(buildings)), "동", "정밀화")
        add(rows, "goyang_openapi_realestate_building_count", "주거·상업 건축물 수", "MN0", "76", float(purpose.str.contains("주택|판매|근린생활|업무", na=False).sum()), "동", "정밀화")
    add(rows, "goyang_localdata_personal_service", "LOCALDATA 개인서비스 영업재고", "ERS", "96", active_localdata_count("beauty_salons") + active_localdata_count("barber_shops") + active_localdata_count("laundries") + active_localdata_count("public_baths"), "영업장", "정밀화")

    # KOSIS city basic statistics collected in Phase111.
    sewer = load_json_frame(RAW / "phase111_kosis_620_DT_1L00012_2023_2024.json")
    if not sewer.empty:
        s2023 = sewer[sewer.get("PRD_DE", "").astype(str).eq("2023")]
        add(rows, "goyang_kosis_sewer_capacity", "공공하수처리시설 시설용량", "ERS", "37", float(num(s2023.loc[s2023.get("C2_NM", "").astype(str).str.contains("시설용량", na=False), "DT"]).sum()), "시설용량", "정밀화")
        add(rows, "goyang_kosis_sewer_volume", "공공하수처리시설 처리량", "ERS", "37", float(num(s2023.loc[s2023.get("C2_NM", "").astype(str).str.contains("처리량", na=False), "DT"]).sum()), "처리량", "정밀화")
    waste = load_json_frame(RAW / "phase111_kosis_620_DT_1L00004_2023_2024.json")
    if not waste.empty:
        w2023 = waste[waste.get("PRD_DE", "").astype(str).eq("2023")]
        add(rows, "goyang_kosis_waste_volume", "쓰레기 배출·처리량", "ERS", "38", float(num(w2023["DT"]).sum()), "톤/일 등", "정밀화")
    media = load_json_frame(RAW / "phase111_kosis_620_DT_1M00037_2023_2024.json")
    if not media.empty:
        m2023 = media[media.get("PRD_DE", "").astype(str).eq("2023")]
        add(rows, "goyang_kosis_media_count", "언론매체 방송사 수", "J00", "60", float(num(m2023["DT"]).sum()), "개", "정밀화")

    # Local/open API for I/Q/G/MN.
    add(rows, "goyang_localdata_lodging", "LOCALDATA 숙박업 영업재고", "I00", "55", active_localdata_count("lodgings") + active_localdata_count("tourist_accommodations"), "영업장", "정밀화")
    add(rows, "goyang_localdata_food", "LOCALDATA 음식점 영업재고", "I00", "56", active_localdata_count("general_restaurants") + active_localdata_count("rest_cafes"), "영업장", "정밀화")
    add(rows, "goyang_openapi_hospital_beds", "병의원 병상 수", "Q00", "86", float(num(hospitals.get("sckbd_co", pd.Series(dtype=str))).sum()) if not hospitals.empty else 0.0, "병상", "정밀화")
    add(rows, "goyang_openapi_hospital_area", "병의원 연면적", "Q00", "86", float(num(hospitals.get("tot_ar", pd.Series(dtype=str))).sum()) if not hospitals.empty else 0.0, "㎡", "정밀화")
    add(rows, "goyang_openapi_parking_slots", "주차장 주차면수", "G00", "45", float(num(parking.get("parkng_cmprt_co", pd.Series(dtype=str))).sum()) if not parking.empty else 0.0, "면", "정밀화")
    add(rows, "goyang_localdata_large_retail", "LOCALDATA 대규모점포 영업재고", "G00", "47", active_localdata_count("large_scale_retail_stores"), "영업장", "정밀화")
    add(rows, "goyang_openapi_library_area", "도서관 건축면적", "ERS", "90", float(num(libraries.get("bild_ar", pd.Series(dtype=str))).sum()) if not libraries.empty else 0.0, "㎡", "정밀화")
    if not apt.empty:
        add(rows, "goyang_openapi_apt_trade_value", "아파트 실거래 금액", "MN0", "76", float(num(apt.get("dlamt", pd.Series(dtype=str))).sum()), "만원", "정밀화")

    # 2024 labor survey manufacturing middle indicators.
    saup = load_json_frame(SAUPM78_RAW)
    if not saup.empty:
        saup = saup[saup.get("C1_NM", "").astype(str).eq("고양시") & saup.get("C2", "").astype(str).str.match(r"INDUSTRY_11SC\d\d")]
        for metric_id, label in [("16118ED_1", "고용노동부 2024 제조업 사업체수"), ("16118ED_9A", "고용노동부 2024 제조업 종사자수")]:
            s = saup[saup["ITM_ID"].eq(metric_id)].copy()
            for _, r in s.iterrows():
                code = re.search(r"SC(\d\d)", str(r.get("C2")))
                if code:
                    add(rows, f"goyang_saupm78_mfg_{metric_id}", label, "C00", code.group(1), float(pd.to_numeric(r.get("DT"), errors="coerce") or 0), "개/명", "정밀화")

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    # Merge same source/parent/middle by summing log-transformed components.
    out = (
        out.groupby(["source_id", "source_label", "parent_code", "middle_code", "raw_unit", "timing_track"], as_index=False)
        .agg(indicator_raw_value=("indicator_raw_value", "sum"), indicator_value=("indicator_value", "sum"))
    )
    return out


def candidate_options(base: pd.DataFrame, indicators: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    detail_frames: list[pd.DataFrame] = []
    alphas = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.33, 0.50, 0.67, 1.00]
    for parent, g in base.groupby("parent_code", sort=False):
        parent_actual = float(g["actual_gva_eok"].sum())
        baseline_pred = g["no_worse_refined_predicted_gva_eok"].to_numpy(float)
        actual = g["actual_gva_eok"].to_numpy(float)
        old_err = g["no_worse_refined_error_gva_eok"].to_numpy(float)
        old_rate = g["no_worse_refined_error_rate_pct"].to_numpy(float)
        old_gt10 = int((old_rate > 10).sum())
        old_parent_error = float(old_err.sum())
        parent_ind = indicators[indicators["parent_code"].eq(parent)]
        source_ids = list(parent_ind["source_id"].unique())
        # single source options
        option_specs: list[tuple[str, pd.DataFrame]] = [(sid, parent_ind[parent_ind["source_id"].eq(sid)]) for sid in source_ids]
        # grouped source option
        if len(source_ids) > 1:
            option_specs.append((f"{parent}_all_openapi_activity_bundle", parent_ind))
        for source_id, ind in option_specs:
            values = g[["middle_code"]].merge(
                ind.groupby("middle_code", as_index=False)["indicator_value"].sum(), on="middle_code", how="left"
            )["indicator_value"].fillna(0).to_numpy(float)
            if values.sum() <= 0:
                continue
            indicator_pred = values / values.sum() * parent_actual
            label = " + ".join(ind["source_label"].drop_duplicates().head(4).astype(str))
            for alpha in alphas:
                pred = (1 - alpha) * baseline_pred + alpha * indicator_pred
                err = np.abs(pred - actual)
                rate = np.where(actual > 0, err / actual * 100, np.nan)
                delta = err - old_err
                high_value = actual >= max(500.0, float(np.median(actual)))
                high_worsen_eok = float(np.maximum(delta[high_value], 0).sum()) if high_value.any() else 0.0
                row = {
                    "city": "고양시",
                    "parent_code": parent,
                    "option_id": source_id,
                    "option_label": label,
                    "alpha": alpha,
                    "parent_actual_eok": parent_actual,
                    "baseline_error_eok": old_parent_error,
                    "candidate_error_eok": float(err.sum()),
                    "error_reduction_eok": float(old_parent_error - err.sum()),
                    "baseline_wape_pct": old_parent_error / parent_actual * 100 if parent_actual else np.nan,
                    "candidate_wape_pct": float(err.sum()) / parent_actual * 100 if parent_actual else np.nan,
                    "baseline_gt10_cells": old_gt10,
                    "candidate_gt10_cells": int((rate > 10).sum()),
                    "worsened_cells": int((delta > 1e-9).sum()),
                    "worsen_sum_eok": float(np.maximum(delta, 0).sum()),
                    "max_worsen_eok": float(np.maximum(delta, 0).max()),
                    "high_value_worsen_eok": high_worsen_eok,
                    "max_error_rate_increase_pp": float(np.nanmax(rate - old_rate)),
                }
                row["strict_adopt"] = (
                    row["error_reduction_eok"] > 0
                    and row["candidate_gt10_cells"] <= row["baseline_gt10_cells"]
                    and row["worsened_cells"] == 0
                )
                row["operational_adopt"] = (
                    row["error_reduction_eok"] > 0
                    and row["candidate_gt10_cells"] <= row["baseline_gt10_cells"]
                    and row["high_value_worsen_eok"] <= 25
                    and row["worsen_sum_eok"] <= max(100.0, 0.08 * old_parent_error)
                    and row["max_error_rate_increase_pp"] <= 10
                )
                rows.append(row)
                d = g[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok"]].copy()
                d["option_id"] = source_id
                d["option_label"] = label
                d["alpha"] = alpha
                d["baseline_predicted_gva_eok"] = baseline_pred
                d["candidate_predicted_gva_eok"] = pred
                d["baseline_error_gva_eok"] = old_err
                d["candidate_error_gva_eok"] = err
                d["baseline_error_rate_pct"] = old_rate
                d["candidate_error_rate_pct"] = rate
                d["error_reduction_eok"] = old_err - err
                d["candidate_worse"] = delta > 1e-9
                detail_frames.append(d)
    screen = pd.DataFrame(rows).sort_values(["operational_adopt", "error_reduction_eok"], ascending=[False, False])
    detail = pd.concat(detail_frames, ignore_index=True) if detail_frames else pd.DataFrame()
    return screen, detail


def select_operational(screen: pd.DataFrame) -> pd.DataFrame:
    accepted = screen[screen["operational_adopt"]].copy()
    if accepted.empty:
        return accepted
    accepted = accepted.sort_values(["parent_code", "error_reduction_eok", "candidate_gt10_cells"], ascending=[True, False, True])
    return accepted.groupby("parent_code", as_index=False).head(1).copy()


def apply_selection(base: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    out["phase113_predicted_gva_eok"] = out["no_worse_refined_predicted_gva_eok"]
    out["phase113_error_gva_eok"] = out["no_worse_refined_error_gva_eok"]
    out["phase113_error_rate_pct"] = out["no_worse_refined_error_rate_pct"]
    out["phase113_option_id"] = "baseline"
    for _, s in selected.iterrows():
        m = (
            detail["parent_code"].eq(s.parent_code)
            & detail["option_id"].eq(s.option_id)
            & np.isclose(detail["alpha"].astype(float), float(s.alpha))
        )
        d = detail[m][["parent_code", "middle_code", "candidate_predicted_gva_eok", "candidate_error_gva_eok", "candidate_error_rate_pct"]]
        for _, r in d.iterrows():
            idx = out["parent_code"].eq(r.parent_code) & out["middle_code"].eq(r.middle_code)
            out.loc[idx, "phase113_predicted_gva_eok"] = r.candidate_predicted_gva_eok
            out.loc[idx, "phase113_error_gva_eok"] = r.candidate_error_gva_eok
            out.loc[idx, "phase113_error_rate_pct"] = r.candidate_error_rate_pct
            out.loc[idx, "phase113_option_id"] = s.option_id
    out["phase113_error_reduction_eok"] = out["no_worse_refined_error_gva_eok"] - out["phase113_error_gva_eok"]
    return out


def summary(df: pd.DataFrame) -> pd.DataFrame:
    base_error = df["no_worse_refined_error_gva_eok"].sum()
    new_error = df["phase113_error_gva_eok"].sum()
    actual = df["actual_gva_eok"].sum()
    return pd.DataFrame(
        [
            {
                "city": "고양시",
                "actual_sum_eok": actual,
                "baseline_refined_error_eok": base_error,
                "phase113_refined_error_eok": new_error,
                "error_reduction_eok": base_error - new_error,
                "baseline_refined_wape_pct": base_error / actual * 100,
                "phase113_refined_wape_pct": new_error / actual * 100,
                "wape_reduction_pp": (base_error - new_error) / actual * 100,
                "baseline_gt10_cells": int((df["no_worse_refined_error_rate_pct"] > 10).sum()),
                "phase113_gt10_cells": int((df["phase113_error_rate_pct"] > 10).sum()),
                "worsened_cells": int((df["phase113_error_gva_eok"] > df["no_worse_refined_error_gva_eok"] + 1e-9).sum()),
            }
        ]
    )


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "pp", "행수")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            v = row.get(key, "")
            if pd.isna(v):
                vals.append("—")
            elif isinstance(v, (float, np.floating)):
                vals.append(f"{v:,.2f}" if abs(float(v)) < 100 else f"{v:,.1f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = load_base()
    indicators = build_indicators()
    screen, detail = candidate_options(base, indicators)
    selected = select_operational(screen)
    registry = apply_selection(base, selected, detail)
    summ = summary(registry)
    remaining = registry[registry["phase113_error_rate_pct"].gt(10)].sort_values("phase113_error_gva_eok", ascending=False)
    improved = registry[registry["phase113_error_reduction_eok"].gt(1e-9)].sort_values("phase113_error_reduction_eok", ascending=False)
    worsened = registry[registry["phase113_error_reduction_eok"].lt(-1e-9)].sort_values("phase113_error_reduction_eok")

    indicators.to_csv(OUTDIR / "phase113_goyang_openapi_activity_indicators.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(OUTDIR / "phase113_candidate_screen.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase113_candidate_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase113_operational_selected_options.csv", index=False, encoding="utf-8-sig")
    registry.to_csv(OUTDIR / "phase113_operational_refined_registry.csv", index=False, encoding="utf-8-sig")
    summ.to_csv(OUTDIR / "phase113_summary.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase113_remaining_gt10.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUTDIR / "phase113_improved_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUTDIR / "phase113_worsened_cells.csv", index=False, encoding="utf-8-sig")

    report = f"""# 고양시 OpenAPI 기반 제약형 정밀화 실험

## 목적

고양시 OpenAPI key로 확인한 시설·건축물·실거래·보건·체육 자료를 중분류 GVA 정밀화 지표로 사용했다. 대부분 현재 스냅샷이므로 속보오차에는 반영하지 않고, 사후 정밀화 후보로만 평가했다.

## 사용 지표

{md_table(indicators, [("source_id", "지표ID"), ("source_label", "지표"), ("parent_code", "상위산업"), ("middle_code", "중분류"), ("indicator_raw_value", "원지표"), ("raw_unit", "단위"), ("timing_track", "시점")], 80)}

## 채택 기준

- 상위산업 오차합계가 감소해야 한다.
- 10% 초과 중분류 수가 증가하면 안 된다.
- 실제 규모가 큰 중분류의 악화액은 25억원 이하로 제한한다.
- 전체 악화액은 100억원 또는 기준 상위산업 오차의 8% 이하로 제한한다.
- 최대 오차율 악화는 10%p 이하로 제한한다.

## 채택된 운영 후보

{md_table(selected, [("parent_code", "상위산업"), ("option_id", "선택 지표"), ("alpha", "혼합비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt10_cells", "기준 10%초과"), ("candidate_gt10_cells", "후보 10%초과"), ("worsened_cells", "악화 셀"), ("worsen_sum_eok", "악화합계 억원"), ("max_error_rate_increase_pp", "최대악화 pp")], 80)}

## 정밀오차 재계산 결과

{md_table(summ, [("city", "지역"), ("actual_sum_eok", "실제합계 억원"), ("baseline_refined_error_eok", "기준 정밀오차 억원"), ("phase113_refined_error_eok", "개선 정밀오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_refined_wape_pct", "기준오차 %"), ("phase113_refined_wape_pct", "개선오차 %"), ("wape_reduction_pp", "개선 pp"), ("baseline_gt10_cells", "기준 10%초과"), ("phase113_gt10_cells", "개선 10%초과"), ("worsened_cells", "악화 셀")])}

## 개선된 중분류

{md_table(improved, [("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("no_worse_refined_error_gva_eok", "기준오차 억원"), ("phase113_error_gva_eok", "개선오차 억원"), ("phase113_error_rate_pct", "개선오차 %"), ("phase113_error_reduction_eok", "감소 억원"), ("phase113_option_id", "적용 지표")], 60)}

## 악화된 중분류

{md_table(worsened, [("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("no_worse_refined_error_gva_eok", "기준오차 억원"), ("phase113_error_gva_eok", "개선오차 억원"), ("phase113_error_rate_pct", "개선오차 %"), ("phase113_error_reduction_eok", "감소 억원"), ("phase113_option_id", "적용 지표")], 40)}

## 남은 10% 초과 업종

{md_table(remaining, [("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase113_predicted_gva_eok", "추정 억원"), ("phase113_error_gva_eok", "오차 억원"), ("phase113_error_rate_pct", "오차 %"), ("required_next_data", "다음 필요자료")], 80)}

## 해석

이번 실험은 대외 최종 성능값이라기보다 운영 개선 후보에 가깝다. 고양시 OpenAPI는 공간·시설 기반 정밀화에는 유용하지만, 대부분 현재 스냅샷이므로 속보 성능 주장에는 아직 쓰면 안 된다. 다만 업종군별 활동지표를 제한적으로 섞으면 특정 상위산업의 중분류 격차를 줄일 수 있는지 확인하는 기반은 마련됐다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR)


if __name__ == "__main__":
    main()
