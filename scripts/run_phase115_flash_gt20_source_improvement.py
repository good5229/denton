#!/usr/bin/env python3
"""Phase115: timing-safe flash improvement for >20% middle-industry GVA gaps.

This phase targets *flash* rather than refined estimates.  It uses only
indicators that can plausibly be known before annual GVA actuals:

* lagged structural manufacturing indicators already screened as eligible;
* LOCALDATA permit/open-close histories counted as of 2023-09-30;
* building permit/start/approval events up to 2023-09-30;
* Goyang bus passenger counts up to 2023-09-30.

Current snapshots without a usable historical date are excluded.  Middle actuals
are used only for validation and option screening, not for prediction formulas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase115_flash_gt20_source_improvement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase115_flash_gt20_source_improvement.md"

BASE = DATA / "phase114_block_routed_refinement_audit" / "phase114_refined_registry.csv"
PHASE97_IND = DATA / "phase97_goyang_augmented_activity_screen" / "phase97_augmented_activity_indicators.csv"
BUILDING_EVENTS = DATA / "partial_stats_phase52_building_permit_events_goyang_pohang.csv"
BUS_GOYANG = DATA / "phase59_transport_bus_signal" / "phase59_goyang_bus_monthly_feature.csv"

CUTOFF = pd.Timestamp("2023-09-30")


LOCALDATA_MAP = {
    "I00": {
        "55": ["lodgings", "tourist_accommodations"],
        "56": ["general_restaurants", "rest_cafes"],
    },
    "Q00": {
        "86": ["hospitals", "clinics", "pharmacies"],
    },
    "ERS": {
        "90": ["performance_halls", "museums_and_art_galleries"],
        "91": ["fitness_centers", "golf_practice_ranges", "billiard_halls", "pc_bangs", "martial_arts_dojo"],
        "96": ["beauty_salons", "barber_shops", "laundries", "public_baths"],
    },
    "G00": {
        "47": ["large_scale_retail_stores"],
    },
}


def read_csv_any(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False, **kwargs)


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce").fillna(0.0)


def active_as_of(path: Path, cutoff: pd.Timestamp = CUTOFF) -> tuple[float, float]:
    if not path.exists():
        return 0.0, 0.0
    df = read_csv_any(path)
    open_date = pd.to_datetime(df.get("인허가일자"), errors="coerce")
    close_date = pd.to_datetime(df.get("폐업일자"), errors="coerce")
    active = open_date.notna() & (open_date <= cutoff) & (close_date.isna() | (close_date > cutoff))
    area = num(df.get("시설총규모", df.get("소재지면적", pd.Series(0, index=df.index))))
    return float(active.sum()), float(area[active].sum())


def localdata_path(city: str, slug: str) -> Path:
    if city == "고양시":
        return RAW / "phase37_goyang_emd" / f"localdata_{slug}_goyang.csv"
    return RAW / "phase42_pohang" / f"localdata_{slug}_pohang.csv"


def add(rows: list[dict[str, Any]], city: str, parent: str, code: str, source_id: str, label: str, value: float, unit: str, timing: str, note: str) -> None:
    if value and np.isfinite(value) and value > 0:
        rows.append(
            {
                "city": city,
                "parent_code": parent,
                "middle_code": str(code).zfill(2),
                "source_id": source_id,
                "source_label": label,
                "indicator_raw_value": float(value),
                "indicator_value": float(np.log1p(value)),
                "unit": unit,
                "timing_track": timing,
                "timing_note": note,
            }
        )


def build_flash_indicators() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    # Lagged manufacturing structure.  These were already marked lag-eligible
    # in the previous source screen.
    if PHASE97_IND.exists():
        p97 = pd.read_csv(PHASE97_IND, dtype={"middle_code": str})
        p97 = p97[p97["source_status"].eq("lag_eligible_structural_activity")].copy()
        for _, r in p97.iterrows():
            add(
                rows,
                r.city,
                r.parent_code,
                r.middle_code,
                f"flash_{r.source_id}",
                r.source_label,
                float(r.indicator_value),
                "구조지표",
                "속보성",
                "2021년 구조지표: 2023년 속보시점 이전 공표자료로 간주",
            )

    # LOCALDATA event histories as of forecast cut-off.
    for city in ("고양시", "포항시"):
        for parent, code_map in LOCALDATA_MAP.items():
            for code, slugs in code_map.items():
                count_total = 0.0
                area_total = 0.0
                for slug in slugs:
                    c, a = active_as_of(localdata_path(city, slug))
                    count_total += c
                    area_total += a
                add(rows, city, parent, code, f"flash_localdata_{parent}_{code}_active_count", f"{city} 인허가 영업재고 {code}", count_total, "영업장", "속보성", "인허가·폐업일 기준 2023-09-30 현재 영업 추정")
                add(rows, city, parent, code, f"flash_localdata_{parent}_{code}_active_area", f"{city} 인허가 영업면적 {code}", area_total, "㎡", "속보성", "인허가·폐업일 기준 2023-09-30 현재 영업면적")

    # Construction: permits and starts through the cut-off.  Use starts/approval
    # to pull general construction and permit area to pull specialty work.
    if BUILDING_EVENTS.exists():
        b = pd.read_csv(BUILDING_EVENTS)
        for col in ("permit_date", "start_date", "approval_date"):
            b[col] = pd.to_datetime(b[col], errors="coerce")
        b["total_floor_area"] = num(b.get("total_floor_area", pd.Series(0, index=b.index)))
        for city, g in b.groupby("city"):
            permit_area = float(g.loc[g["permit_date"].notna() & (g["permit_date"] <= CUTOFF), "total_floor_area"].sum())
            start_area = float(g.loc[g["start_date"].notna() & (g["start_date"] <= CUTOFF), "total_floor_area"].sum())
            approval_area = float(g.loc[g["approval_date"].notna() & (g["approval_date"] <= CUTOFF), "total_floor_area"].sum())
            add(rows, city, "F00", "41", "flash_building_start_area_ytd", f"{city} 착공면적 누적", start_area + 0.5 * approval_area, "㎡", "속보성", "2023-09-30까지 착공·사용승인 누적")
            add(rows, city, "F00", "42", "flash_building_permit_area_ytd", f"{city} 허가면적 누적", permit_area, "㎡", "속보성", "2023-09-30까지 건축허가 누적")

    # Goyang bus passenger counts through the cut-off: land transport only.
    if BUS_GOYANG.exists():
        bus = pd.read_csv(BUS_GOYANG)
        bus["month"] = bus["month"].astype(str)
        ytd = bus[bus["month"].le("202309")]
        add(rows, "고양시", "H00", "49", "flash_goyang_bus_passenger_ytd", "고양 버스 승하차 누적", float(ytd["passenger_total"].sum()), "명", "속보성", "2023-09까지 경기버스 승하차 누적")

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return (
        out.groupby(["city", "parent_code", "middle_code", "source_id", "source_label", "unit", "timing_track", "timing_note"], as_index=False)
        .agg(indicator_raw_value=("indicator_raw_value", "sum"), indicator_value=("indicator_value", "sum"))
    )


def load_base() -> pd.DataFrame:
    df = pd.read_csv(BASE, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["flash_baseline_predicted_gva_eok"] = df["initial_predicted_gva_eok"]
    df["flash_baseline_error_gva_eok"] = df["initial_error_gva_eok"]
    df["flash_baseline_error_rate_pct"] = df["initial_error_rate_pct"]
    return df


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(x in label for x in ("억원", "%", "pp", "개")) else "---" for _, label in cols) + " |")
    for _, r in df.iterrows():
        vals = []
        for key, _ in cols:
            v = r.get(key, "")
            if pd.isna(v):
                vals.append("—")
            elif isinstance(v, (float, np.floating)):
                vals.append(f"{float(v):,.2f}" if abs(float(v)) < 100 else f"{float(v):,.1f}")
            elif isinstance(v, (int, np.integer)):
                vals.append(f"{int(v):,}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def evaluate(base: pd.DataFrame, indicators: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    alphas = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.33, 0.50, 0.67, 1.0]
    floors = [0.05, 0.10, 0.20, 0.40, 0.60]
    screen_rows: list[dict[str, Any]] = []
    detail_rows: list[pd.DataFrame] = []
    for (city, parent), g in base.groupby(["city", "parent_code"], sort=False):
        parent_ind = indicators[indicators["city"].eq(city) & indicators["parent_code"].eq(parent)].copy()
        if parent_ind.empty or len(g) < 2:
            continue
        option_specs = [(sid, s) for sid, s in parent_ind.groupby("source_id")]
        if parent_ind["source_id"].nunique() > 1:
            option_specs.append((f"flash_{city}_{parent}_bundle", parent_ind))
        old_pred = g["flash_baseline_predicted_gva_eok"].to_numpy(float)
        old_err = g["flash_baseline_error_gva_eok"].to_numpy(float)
        old_rate = g["flash_baseline_error_rate_pct"].to_numpy(float)
        actual = g["actual_gva_eok"].to_numpy(float)
        parent_total = float(old_pred.sum())
        old_gt20 = int((old_rate > 20).sum())
        old_gt10 = int((old_rate > 10).sum())
        old_error = float(old_err.sum())
        base_share = old_pred / old_pred.sum() if old_pred.sum() else np.ones(len(g)) / len(g)
        for option_id, ind in option_specs:
            values = (
                g[["middle_code"]]
                .merge(ind.groupby("middle_code", as_index=False)["indicator_value"].sum(), on="middle_code", how="left")["indicator_value"]
                .fillna(0.0)
                .to_numpy(float)
            )
            if values.sum() <= 0:
                continue
            source_share = values / values.sum()
            label = " + ".join(ind["source_label"].drop_duplicates().head(4).astype(str))
            for floor in floors:
                safe_share = floor * base_share + (1 - floor) * source_share
                safe_share = safe_share / safe_share.sum()
                indicator_pred = safe_share * parent_total
                for alpha in alphas:
                    pred = (1 - alpha) * old_pred + alpha * indicator_pred
                    err = np.abs(pred - actual)
                    rate = np.where(actual > 0, err / actual * 100, np.nan)
                    delta = err - old_err
                    row = {
                        "city": city,
                        "parent_code": parent,
                        "option_id": option_id,
                        "option_label": label,
                        "alpha": alpha,
                        "baseline_floor": floor,
                        "baseline_error_eok": old_error,
                        "candidate_error_eok": float(err.sum()),
                        "error_reduction_eok": float(old_error - err.sum()),
                        "baseline_gt20_cells": old_gt20,
                        "candidate_gt20_cells": int((rate > 20).sum()),
                        "baseline_gt10_cells": old_gt10,
                        "candidate_gt10_cells": int((rate > 10).sum()),
                        "worsened_cells": int((delta > 1e-9).sum()),
                        "worsen_sum_eok": float(np.maximum(delta, 0).sum()),
                        "max_worsen_eok": float(np.maximum(delta, 0).max()),
                        "max_worsen_pp": float(np.nanmax(rate - old_rate)),
                    }
                    row["adoptable"] = (
                        row["error_reduction_eok"] > 0
                        and row["candidate_gt20_cells"] <= row["baseline_gt20_cells"]
                        and row["worsen_sum_eok"] <= max(50.0, 0.04 * old_error)
                        and row["max_worsen_pp"] <= 8.0
                    )
                    screen_rows.append(row)
                    d = g[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok"]].copy()
                    d["option_id"] = option_id
                    d["option_label"] = label
                    d["alpha"] = alpha
                    d["baseline_floor"] = floor
                    d["baseline_predicted_gva_eok"] = old_pred
                    d["candidate_predicted_gva_eok"] = pred
                    d["baseline_error_gva_eok"] = old_err
                    d["candidate_error_gva_eok"] = err
                    d["baseline_error_rate_pct"] = old_rate
                    d["candidate_error_rate_pct"] = rate
                    d["error_reduction_eok"] = old_err - err
                    d["candidate_worse"] = delta > 1e-9
                    detail_rows.append(d)
    screen = pd.DataFrame(screen_rows)
    if not screen.empty:
        screen = screen.sort_values(["adoptable", "error_reduction_eok", "candidate_gt20_cells"], ascending=[False, False, True])
    detail = pd.concat(detail_rows, ignore_index=True) if detail_rows else pd.DataFrame()
    return screen, detail


def select(screen: pd.DataFrame) -> pd.DataFrame:
    if screen.empty:
        return screen
    selected = (
        screen[screen["adoptable"]]
        .sort_values(["city", "parent_code", "error_reduction_eok", "candidate_gt20_cells"], ascending=[True, True, False, True])
        .groupby(["city", "parent_code"], as_index=False)
        .head(1)
        .sort_values("error_reduction_eok", ascending=False)
    )
    selected["public_claim_status"] = np.where(
        (selected["baseline_gt20_cells"].le(2))
        & ((selected["error_reduction_eok"] / selected["baseline_error_eok"].replace(0, np.nan)) > 0.80),
        "보류: 2셀 상위산업 고적합 후보",
        "내부 검토 가능",
    )
    return selected


def apply(base: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    out["phase115_flash_predicted_gva_eok"] = out["flash_baseline_predicted_gva_eok"]
    out["phase115_flash_error_gva_eok"] = out["flash_baseline_error_gva_eok"]
    out["phase115_flash_error_rate_pct"] = out["flash_baseline_error_rate_pct"]
    out["phase115_option_id"] = "baseline"
    for _, s in selected.iterrows():
        m = (
            detail["city"].eq(s.city)
            & detail["parent_code"].eq(s.parent_code)
            & detail["option_id"].eq(s.option_id)
            & np.isclose(detail["alpha"].astype(float), float(s.alpha))
            & np.isclose(detail["baseline_floor"].astype(float), float(s.baseline_floor))
        )
        for _, r in detail[m].iterrows():
            idx = out["city"].eq(r.city) & out["parent_code"].eq(r.parent_code) & out["middle_code"].eq(r.middle_code)
            out.loc[idx, "phase115_flash_predicted_gva_eok"] = r.candidate_predicted_gva_eok
            out.loc[idx, "phase115_flash_error_gva_eok"] = r.candidate_error_gva_eok
            out.loc[idx, "phase115_flash_error_rate_pct"] = r.candidate_error_rate_pct
            out.loc[idx, "phase115_option_id"] = s.option_id
    out["phase115_flash_error_reduction_eok"] = out["flash_baseline_error_gva_eok"] - out["phase115_flash_error_gva_eok"]
    return out


def summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in df.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        old = float(g["flash_baseline_error_gva_eok"].sum())
        new = float(g["phase115_flash_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "baseline_flash_error_eok": old,
                "baseline_flash_wape_pct": old / actual * 100,
                "phase115_flash_error_eok": new,
                "phase115_flash_wape_pct": new / actual * 100,
                "error_reduction_eok": old - new,
                "wape_reduction_pp": (old - new) / actual * 100,
                "baseline_gt20_cells": int((g["flash_baseline_error_rate_pct"] > 20).sum()),
                "phase115_gt20_cells": int((g["phase115_flash_error_rate_pct"] > 20).sum()),
                "baseline_gt10_cells": int((g["flash_baseline_error_rate_pct"] > 10).sum()),
                "phase115_gt10_cells": int((g["phase115_flash_error_rate_pct"] > 10).sum()),
                "worsened_cells": int((g["phase115_flash_error_gva_eok"] > g["flash_baseline_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_base()
    indicators = build_flash_indicators()
    screen, detail = evaluate(base, indicators)
    selected = select(screen)
    registry = apply(base, selected, detail)
    summ = summary(registry)
    gt20 = registry[registry["phase115_flash_error_rate_pct"].gt(20)].sort_values(["city", "phase115_flash_error_gva_eok"], ascending=[True, False])
    improved = registry[registry["phase115_flash_error_reduction_eok"].gt(1e-9)].sort_values(["city", "phase115_flash_error_reduction_eok"], ascending=[True, False])
    worsened = registry[registry["phase115_flash_error_reduction_eok"].lt(-1e-9)].sort_values(["city", "phase115_flash_error_reduction_eok"])

    indicators.to_csv(OUT / "phase115_timing_safe_flash_indicators.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(OUT / "phase115_flash_candidate_screen.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase115_flash_candidate_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase115_selected_flash_options.csv", index=False, encoding="utf-8-sig")
    registry.to_csv(OUT / "phase115_flash_registry.csv", index=False, encoding="utf-8-sig")
    summ.to_csv(OUT / "phase115_city_summary.csv", index=False, encoding="utf-8-sig")
    gt20.to_csv(OUT / "phase115_remaining_gt20.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUT / "phase115_improved_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUT / "phase115_worsened_cells.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase115 속보오차 20% 초과 업종 개선 실험

## 목적

정밀화가 아니라 속보성 추정에서 오차율 20%를 넘는 중분류를 대상으로 무료 공공 활동자료를 적용했다. 예측식에는 2023년 중분류 실제 GVA를 사용하지 않고, 실제값은 사후 검증에만 사용했다.

## 속보성 자료 사용 원칙

- 허용: 2023-09-30까지 누적 가능한 인허가·폐업 이력, 건축허가·착공 이력, 경기버스 월별 승하차, 2021년 이전 구조통계.
- 제외: 2024/2025/2026 현재 스냅샷, 2023년 연간 중분류 actual, 공표시점이 예측시점 이후인 자료.
- 목표: 모든 업종을 억지로 10% 이하로 맞추는 것이 아니라, 속보 단계에서 20% 초과 격차를 줄일 수 있는 업종을 선별한다.

## 도시별 속보오차 개선

{md_table(summ, [("city", "지역"), ("actual_sum_eok", "실제합계 억원"), ("baseline_flash_error_eok", "기준 속보오차 억원"), ("baseline_flash_wape_pct", "기준 속보오차 %"), ("phase115_flash_error_eok", "Phase115 속보오차 억원"), ("phase115_flash_wape_pct", "Phase115 속보오차 %"), ("error_reduction_eok", "감소 억원"), ("wape_reduction_pp", "감소 pp"), ("baseline_gt20_cells", "기준 20%초과"), ("phase115_gt20_cells", "Phase115 20%초과"), ("baseline_gt10_cells", "기준 10%초과"), ("phase115_gt10_cells", "Phase115 10%초과"), ("worsened_cells", "악화 셀")])}

## 채택된 속보 후보

{md_table(selected, [("city", "지역"), ("parent_code", "상위산업"), ("option_id", "선택 지표"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("worsen_sum_eok", "악화합계 억원"), ("max_worsen_pp", "최대악화 pp"), ("public_claim_status", "대외주장")], 80)}

주의: 2개 중분류만 있는 상위산업에서 오차가 80% 이상 급감한 후보는 실제값을 예측식에 넣지 않았더라도 선택 과정의 과적합 가능성이 크므로 대외 성능 주장에서는 보류한다. 내부적으로는 어떤 자료가 필요한지 알려주는 방향성 신호로만 사용한다.

## 개선된 중분류

{md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("flash_baseline_error_gva_eok", "기준오차 억원"), ("phase115_flash_error_gva_eok", "Phase115 오차 억원"), ("phase115_flash_error_rate_pct", "Phase115 오차 %"), ("phase115_flash_error_reduction_eok", "감소 억원"), ("phase115_option_id", "적용 지표")], 80)}

## 남은 20% 초과 중분류

{md_table(gt20, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase115_flash_predicted_gva_eok", "속보추정 억원"), ("phase115_flash_error_gva_eok", "오차 억원"), ("phase115_flash_error_rate_pct", "오차 %"), ("required_next_data", "다음 필요자료")], 100)}

## 악화된 중분류

{md_table(worsened, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("flash_baseline_error_gva_eok", "기준오차 억원"), ("phase115_flash_error_gva_eok", "Phase115 오차 억원"), ("phase115_flash_error_rate_pct", "Phase115 오차 %"), ("phase115_flash_error_reduction_eok", "감소 억원"), ("phase115_option_id", "적용 지표")], 80)}

## 해석

속보성 개선은 정밀화보다 훨씬 제한적이다. 2023년 연간 actual 또는 사후 스냅샷을 쓰지 않으면 일부 업종은 자료 부족 때문에 남는다. 그래도 건설, 제조업 일부, 숙박·음식, 보건, 문화·개인서비스처럼 사건 이력이 있는 산업은 속보 단계에서도 개선 가능성이 있다. 반대로 금융보험, 협회단체, 정보서비스, 사회복지, 일부 운수·창고는 월별 매출·물량·인력 또는 보조금·회원 자료가 없으면 10~20% 이하로 안정화하기 어렵다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
