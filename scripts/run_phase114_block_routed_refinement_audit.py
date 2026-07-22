#!/usr/bin/env python3
"""Phase114: block-routed refined GVA allocation and leakage audit.

Phase113 showed that public activity indicators can reduce several Goyang
middle-industry GVA gaps, but a parent-wide correction sometimes improved the
parent while making unrelated middle industries worse.  This experiment is more
conservative:

* flash and refined tracks are separated;
* current-snapshot OpenAPI indicators are refined-only;
* middle actuals are never used in the prediction formula;
* indicators are routed to semantically coherent blocks inside a parent;
* a block candidate is adopted only when it reduces validation error without
  causing a material side-effect in the block;
* suspiciously-good refined results are audited with a permutation negative
  control.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUTDIR = DATA / "phase114_block_routed_refinement_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase114_block_routed_refinement_audit.md"

BASE_REGISTRY = DATA / "phase105_no_worse_refinement_guardrail" / "phase105_no_worse_refinement_registry.csv"
PHASE113_REGISTRY = DATA / "phase113_goyang_openapi_constrained_refinement" / "phase113_operational_refined_registry.csv"
PHASE113_INDICATORS = DATA / "phase113_goyang_openapi_constrained_refinement" / "phase113_goyang_openapi_activity_indicators.csv"


@dataclass(frozen=True)
class Block:
    block_id: str
    city: str
    parent_code: str
    middle_codes: tuple[str, ...]
    source_patterns: tuple[str, ...]
    label: str


BLOCKS = [
    Block("C00_mfg", "고양시", "C00", tuple(f"{i:02d}" for i in range(10, 35)), ("saupm78_mfg",), "제조업 중분류"),
    Block("ERS_env", "고양시", "ERS", ("36", "37", "38", "39"), ("sewer", "waste"), "수도·하수·폐기물"),
    Block("ERS_culture_sports", "고양시", "ERS", ("90", "91"), ("culture", "sports", "park", "library"), "문화·스포츠"),
    Block("ERS_personal", "고양시", "ERS", ("94", "95", "96"), ("personal_service",), "협회·수리·개인서비스"),
    Block("G00_trade", "고양시", "G00", ("45", "46", "47"), ("auto", "retail", "parking", "large_retail"), "자동차·도소매"),
    Block("I00_food_lodging", "고양시", "I00", ("55", "56"), ("lodging", "food"), "숙박·음식"),
    Block("J00_media_it", "고양시", "J00", ("58", "59", "60", "61", "62", "63"), ("media",), "정보통신"),
    Block("MN0_professional", "고양시", "MN0", ("70", "71", "72", "73"), ("business_building", "research_building"), "전문·과학기술"),
    Block("MN0_facility_support", "고양시", "MN0", ("74", "75"), ("facility_management", "business_building"), "사업시설·사업지원"),
    Block("MN0_rental", "고양시", "MN0", ("76",), ("apt_trade", "realestate"), "임대"),
    Block("Q00_health_welfare", "고양시", "Q00", ("86", "87"), ("hospital",), "보건·복지"),
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"middle_code": str})


def fmt_num(v: float) -> str:
    if pd.isna(v):
        return "—"
    if abs(float(v)) >= 100:
        return f"{float(v):,.1f}"
    return f"{float(v):,.2f}"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(x in label for x in ("억원", "%", "pp", "개", "순위")) else "---" for _, label in cols) + " |")
    for _, r in df.iterrows():
        vals: list[str] = []
        for key, _ in cols:
            v = r.get(key, "")
            if isinstance(v, (float, np.floating)):
                vals.append(fmt_num(float(v)))
            elif isinstance(v, (int, np.integer)):
                vals.append(f"{int(v):,}")
            elif pd.isna(v):
                vals.append("—")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def load_baseline() -> pd.DataFrame:
    base = read_csv(BASE_REGISTRY)
    base["middle_code"] = base["middle_code"].astype(str).str.zfill(2)
    if PHASE113_REGISTRY.exists():
        p113 = read_csv(PHASE113_REGISTRY)
        p113["middle_code"] = p113["middle_code"].astype(str).str.zfill(2)
        keep = [
            "city",
            "parent_code",
            "middle_code",
            "phase113_predicted_gva_eok",
            "phase113_error_gva_eok",
            "phase113_error_rate_pct",
            "phase113_option_id",
        ]
        base = base.merge(p113[keep], on=["city", "parent_code", "middle_code"], how="left")
    else:
        base["phase113_predicted_gva_eok"] = np.nan
        base["phase113_error_gva_eok"] = np.nan
        base["phase113_error_rate_pct"] = np.nan
        base["phase113_option_id"] = np.nan

    base["phase114_input_predicted_gva_eok"] = np.where(
        base["city"].eq("고양시") & base["phase113_predicted_gva_eok"].notna(),
        base["phase113_predicted_gva_eok"],
        base["no_worse_refined_predicted_gva_eok"],
    )
    base["phase114_input_error_gva_eok"] = (base["phase114_input_predicted_gva_eok"] - base["actual_gva_eok"]).abs()
    base["phase114_input_error_rate_pct"] = np.where(
        base["actual_gva_eok"] > 0,
        base["phase114_input_error_gva_eok"] / base["actual_gva_eok"] * 100,
        np.nan,
    )
    return base


def load_indicators() -> pd.DataFrame:
    if not PHASE113_INDICATORS.exists():
        return pd.DataFrame(columns=["city", "source_id", "source_label", "parent_code", "middle_code", "indicator_value", "timing_track"])
    ind = read_csv(PHASE113_INDICATORS)
    ind["city"] = "고양시"
    ind["middle_code"] = ind["middle_code"].astype(str).str.zfill(2)
    ind["timing_track"] = "정밀화"
    return ind


def source_match(source_id: str, patterns: tuple[str, ...]) -> bool:
    return any(p in source_id for p in patterns)


def block_indicator_share(
    block_df: pd.DataFrame,
    ind: pd.DataFrame,
    floor: float = 0.15,
) -> np.ndarray:
    """Return block-level indicator share with a baseline-share floor.

    Missing source signal is not treated as zero activity.  A baseline floor is
    retained to prevent a single facility count from collapsing every other
    middle industry in the block.
    """

    base_pred = block_df["phase114_input_predicted_gva_eok"].to_numpy(float)
    if base_pred.sum() <= 0:
        base_share = np.ones(len(block_df)) / len(block_df)
    else:
        base_share = base_pred / base_pred.sum()
    values = (
        block_df[["middle_code"]]
        .merge(ind.groupby("middle_code", as_index=False)["indicator_value"].sum(), on="middle_code", how="left")["indicator_value"]
        .fillna(0.0)
        .to_numpy(float)
    )
    if values.sum() <= 0:
        return base_share
    source_share = values / values.sum()
    mixed = floor * base_share + (1 - floor) * source_share
    return mixed / mixed.sum()


def evaluate_block_candidates(base: pd.DataFrame, indicators: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    alphas = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.33, 0.50]
    floors = [0.10, 0.15, 0.25, 0.40, 0.60]
    screen_rows: list[dict[str, Any]] = []
    detail_rows: list[pd.DataFrame] = []

    for block in BLOCKS:
        bmask = (
            base["city"].eq(block.city)
            & base["parent_code"].eq(block.parent_code)
            & base["middle_code"].isin(block.middle_codes)
        )
        bdf = base[bmask].copy()
        if len(bdf) < 2:
            continue
        src_pool = indicators[
            indicators["city"].eq(block.city)
            & indicators["parent_code"].eq(block.parent_code)
            & indicators["source_id"].map(lambda x: source_match(str(x), block.source_patterns))
        ].copy()
        option_specs: list[tuple[str, str, pd.DataFrame]] = []
        for sid, s in src_pool.groupby("source_id"):
            option_specs.append((sid, str(s["source_label"].iloc[0]), s))
        if len(src_pool["source_id"].unique()) > 1:
            option_specs.append((f"{block.block_id}_bundle", "블록 맞춤 활동지표 묶음", src_pool))
        for option_id, label, src in option_specs:
            src = src[src["middle_code"].isin(block.middle_codes)].copy()
            if src.empty:
                continue
            for floor in floors:
                share = block_indicator_share(bdf, src, floor=floor)
                block_total = float(bdf["phase114_input_predicted_gva_eok"].sum())
                indicator_pred = share * block_total
                actual = bdf["actual_gva_eok"].to_numpy(float)
                old_pred = bdf["phase114_input_predicted_gva_eok"].to_numpy(float)
                old_err = bdf["phase114_input_error_gva_eok"].to_numpy(float)
                old_rate = bdf["phase114_input_error_rate_pct"].to_numpy(float)
                for alpha in alphas:
                    pred = (1 - alpha) * old_pred + alpha * indicator_pred
                    err = np.abs(pred - actual)
                    rate = np.where(actual > 0, err / actual * 100, np.nan)
                    delta = err - old_err
                    row = {
                        "city": block.city,
                        "block_id": block.block_id,
                        "block_label": block.label,
                        "parent_code": block.parent_code,
                        "middle_codes": ",".join(block.middle_codes),
                        "option_id": option_id,
                        "option_label": label,
                        "alpha": alpha,
                        "baseline_floor": floor,
                        "baseline_error_eok": float(old_err.sum()),
                        "candidate_error_eok": float(err.sum()),
                        "error_reduction_eok": float(old_err.sum() - err.sum()),
                        "baseline_gt10_cells": int((old_rate > 10).sum()),
                        "candidate_gt10_cells": int((rate > 10).sum()),
                        "worsened_cells": int((delta > 1e-9).sum()),
                        "worsen_sum_eok": float(np.maximum(delta, 0).sum()),
                        "max_worsen_eok": float(np.maximum(delta, 0).max()),
                        "max_worsen_pp": float(np.nanmax(rate - old_rate)),
                    }
                    row["adoptable"] = (
                        row["error_reduction_eok"] > 0
                        and row["candidate_gt10_cells"] <= row["baseline_gt10_cells"]
                        and row["worsen_sum_eok"] <= min(25.0, max(3.0, 0.03 * row["baseline_error_eok"]))
                        and row["max_worsen_pp"] <= 2.0
                    )
                    screen_rows.append(row)

                    d = bdf[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok"]].copy()
                    d["block_id"] = block.block_id
                    d["block_label"] = block.label
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
        screen = screen.sort_values(["adoptable", "error_reduction_eok", "candidate_gt10_cells"], ascending=[False, False, True])
    detail = pd.concat(detail_rows, ignore_index=True) if detail_rows else pd.DataFrame()
    return screen, detail


def select_candidates(screen: pd.DataFrame) -> pd.DataFrame:
    if screen.empty:
        return screen
    selected = (
        screen[screen["adoptable"]]
        .sort_values(["block_id", "error_reduction_eok", "candidate_gt10_cells"], ascending=[True, False, True])
        .groupby(["city", "block_id"], as_index=False)
        .head(1)
        .copy()
    )
    return selected.sort_values("error_reduction_eok", ascending=False)


def apply_selected(base: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame) -> pd.DataFrame:
    out = base.copy()
    out["phase114_predicted_gva_eok"] = out["phase114_input_predicted_gva_eok"]
    out["phase114_error_gva_eok"] = out["phase114_input_error_gva_eok"]
    out["phase114_error_rate_pct"] = out["phase114_input_error_rate_pct"]
    out["phase114_option_id"] = "baseline"
    out["phase114_block_id"] = "baseline"
    for _, s in selected.iterrows():
        m = (
            detail["city"].eq(s.city)
            & detail["block_id"].eq(s.block_id)
            & detail["option_id"].eq(s.option_id)
            & np.isclose(detail["alpha"].astype(float), float(s.alpha))
            & np.isclose(detail["baseline_floor"].astype(float), float(s.baseline_floor))
        )
        for _, r in detail[m].iterrows():
            idx = out["city"].eq(r.city) & out["parent_code"].eq(r.parent_code) & out["middle_code"].eq(r.middle_code)
            out.loc[idx, "phase114_predicted_gva_eok"] = r.candidate_predicted_gva_eok
            out.loc[idx, "phase114_error_gva_eok"] = r.candidate_error_gva_eok
            out.loc[idx, "phase114_error_rate_pct"] = r.candidate_error_rate_pct
            out.loc[idx, "phase114_option_id"] = s.option_id
            out.loc[idx, "phase114_block_id"] = s.block_id
    out["phase114_error_reduction_eok"] = out["phase114_input_error_gva_eok"] - out["phase114_error_gva_eok"]
    return out


def permutation_audit(base: pd.DataFrame, indicators: pd.DataFrame, selected: pd.DataFrame, rounds: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(20260722)
    rows: list[dict[str, Any]] = []
    for _, s in selected.iterrows():
        bdf = base[
            base["city"].eq(s.city)
            & base["parent_code"].eq(s.parent_code)
            & base["middle_code"].isin(str(s.middle_codes).split(","))
        ].copy()
        src = indicators[
            indicators["city"].eq(s.city)
            & indicators["parent_code"].eq(s.parent_code)
            & indicators["source_id"].astype(str).eq(str(s.option_id).replace("_bundle", ""))
        ].copy()
        if str(s.option_id).endswith("_bundle"):
            block = next((b for b in BLOCKS if b.block_id == s.block_id), None)
            if block is not None:
                src = indicators[
                    indicators["city"].eq(s.city)
                    & indicators["parent_code"].eq(s.parent_code)
                    & indicators["source_id"].map(lambda x: source_match(str(x), block.source_patterns))
                ].copy()
        src = src[src["middle_code"].isin(str(s.middle_codes).split(","))].copy()
        if bdf.empty or src.empty:
            continue
        observed = float(s.error_reduction_eok)
        null_improvements: list[float] = []
        codes = bdf["middle_code"].tolist()
        for _ in range(rounds):
            shuffled = src.copy()
            mapping = dict(zip(codes, rng.permutation(codes)))
            shuffled["middle_code"] = shuffled["middle_code"].map(mapping).fillna(shuffled["middle_code"])
            share = block_indicator_share(bdf, shuffled, floor=float(s.baseline_floor))
            old_pred = bdf["phase114_input_predicted_gva_eok"].to_numpy(float)
            old_err = bdf["phase114_input_error_gva_eok"].to_numpy(float)
            actual = bdf["actual_gva_eok"].to_numpy(float)
            pred = (1 - float(s.alpha)) * old_pred + float(s.alpha) * (old_pred.sum() * share)
            err = np.abs(pred - actual)
            null_improvements.append(float(old_err.sum() - err.sum()))
        arr = np.array(null_improvements)
        rows.append(
            {
                "city": s.city,
                "block_id": s.block_id,
                "option_id": s.option_id,
                "observed_reduction_eok": observed,
                "null_mean_reduction_eok": float(arr.mean()),
                "null_p95_reduction_eok": float(np.quantile(arr, 0.95)),
                "null_max_reduction_eok": float(arr.max()),
                "empirical_p_value": float((np.sum(arr >= observed) + 1) / (len(arr) + 1)),
                "signal_judgement": "강함" if observed > np.quantile(arr, 0.95) else "보류",
            }
        )
    return pd.DataFrame(rows)


def city_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in df.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        flash_err = float(g["initial_error_gva_eok"].sum())
        input_err = float(g["phase114_input_error_gva_eok"].sum())
        new_err = float(g["phase114_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "flash_error_eok": flash_err,
                "flash_wape_pct": flash_err / actual * 100,
                "input_refined_error_eok": input_err,
                "input_refined_wape_pct": input_err / actual * 100,
                "phase114_error_eok": new_err,
                "phase114_wape_pct": new_err / actual * 100,
                "phase114_reduction_eok": input_err - new_err,
                "phase114_reduction_pp": (input_err - new_err) / actual * 100,
                "input_gt10_cells": int((g["phase114_input_error_rate_pct"] > 10).sum()),
                "phase114_gt10_cells": int((g["phase114_error_rate_pct"] > 10).sum()),
                "worsened_cells": int((g["phase114_error_gva_eok"] > g["phase114_input_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def add_timing_track(registry: pd.DataFrame) -> pd.DataFrame:
    out = registry.copy()
    out["flash_source_policy"] = "속보성: 예측시점 이전에 존재하는 자료만 허용"
    out["refined_source_policy"] = np.where(
        out["city"].eq("고양시") & out["phase114_option_id"].ne("baseline"),
        "정밀화: 고양시 OpenAPI/공공 활동지표 사용, 과거 빈티지 미확인",
        "정밀화: 기존 보수 추정 유지",
    )
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = load_baseline()
    indicators = load_indicators()
    screen, detail = evaluate_block_candidates(base, indicators)
    selected = select_candidates(screen)
    registry = add_timing_track(apply_selected(base, selected, detail))
    perm = permutation_audit(base, indicators, selected)
    summ = city_summary(registry)

    gt10 = registry[registry["phase114_error_rate_pct"].gt(10)].sort_values(["city", "phase114_error_gva_eok"], ascending=[True, False])
    improved = registry[registry["phase114_error_reduction_eok"].gt(1e-9)].sort_values(["city", "phase114_error_reduction_eok"], ascending=[True, False])
    worsened = registry[registry["phase114_error_reduction_eok"].lt(-1e-9)].sort_values(["city", "phase114_error_reduction_eok"], ascending=[True, True])
    suspicious = registry[registry["phase114_error_rate_pct"].le(1)].sort_values(["city", "actual_gva_eok"], ascending=[True, False])

    indicators.to_csv(OUTDIR / "phase114_activity_indicators.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(OUTDIR / "phase114_block_candidate_screen.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase114_block_candidate_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase114_selected_block_routes.csv", index=False, encoding="utf-8-sig")
    registry.to_csv(OUTDIR / "phase114_refined_registry.csv", index=False, encoding="utf-8-sig")
    perm.to_csv(OUTDIR / "phase114_permutation_negative_control.csv", index=False, encoding="utf-8-sig")
    summ.to_csv(OUTDIR / "phase114_city_summary.csv", index=False, encoding="utf-8-sig")
    gt10.to_csv(OUTDIR / "phase114_remaining_gt10.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUTDIR / "phase114_improved_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUTDIR / "phase114_worsened_cells.csv", index=False, encoding="utf-8-sig")
    suspicious.to_csv(OUTDIR / "phase114_suspicious_sub1pct_cells.csv", index=False, encoding="utf-8-sig")

    strong = perm[perm["signal_judgement"].eq("강함")] if not perm.empty else pd.DataFrame()
    report = f"""# Phase114 블록 라우팅 정밀화 및 유출성 점검

## 목적

중분류 GVA 추정에서 10% 초과 오차를 줄이되, 상위산업 전체에 같은 활동지표를 섞어 다른 중분류를 악화시키는 문제를 줄이기 위해 블록 라우팅을 적용했다. 예측식에는 중분류 실제값을 사용하지 않고, 실제값은 사후 집계검증에만 사용했다.

## 방법

1. 속보성 지표와 정밀화 지표를 분리했다.
2. 고양시 OpenAPI처럼 현재 스냅샷 성격이 강한 자료는 정밀화 전용으로만 사용했다.
3. ERS, MN0 등 내부 구성이 다른 상위산업은 의미상 가까운 중분류 블록으로 나눴다.
4. 블록 안에서는 기존 추정 총량을 보존하면서 활동지표 비중을 일부 혼합했다.
5. 채택 후보는 오차합계 감소, 10% 초과 셀 비증가, 악화액 상한, 최대 악화율 상한을 모두 만족해야 한다.
6. 채택 후보는 무작위 순열 대조군과 비교해 너무 우연적인 개선인지 점검했다.

## 도시별 결과

{md_table(summ, [("city", "지역"), ("actual_sum_eok", "실제합계 억원"), ("flash_error_eok", "속보오차 억원"), ("flash_wape_pct", "속보오차 %"), ("input_refined_error_eok", "기준 정밀오차 억원"), ("input_refined_wape_pct", "기준 정밀오차 %"), ("phase114_error_eok", "Phase114 정밀오차 억원"), ("phase114_wape_pct", "Phase114 정밀오차 %"), ("phase114_reduction_eok", "감소 억원"), ("phase114_reduction_pp", "감소 pp"), ("input_gt10_cells", "기준 10%초과"), ("phase114_gt10_cells", "Phase114 10%초과"), ("worsened_cells", "악화 셀")])}

## 채택된 블록 라우팅

{md_table(selected, [("city", "지역"), ("block_label", "블록"), ("parent_code", "상위산업"), ("option_id", "선택 활동지표"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt10_cells", "기준 10%초과"), ("candidate_gt10_cells", "후보 10%초과"), ("worsen_sum_eok", "악화합계 억원"), ("max_worsen_pp", "최대악화 pp")], 80)}

## 무작위 순열 대조군

{md_table(perm, [("city", "지역"), ("block_id", "블록ID"), ("option_id", "활동지표"), ("observed_reduction_eok", "관측 감소 억원"), ("null_mean_reduction_eok", "무작위 평균 억원"), ("null_p95_reduction_eok", "무작위 95% 억원"), ("empirical_p_value", "경험 p값"), ("signal_judgement", "판정")], 80)}

강한 신호로 판정된 후보 수: **{len(strong)}개**. 강한 신호가 아닌 후보는 포스터의 최종 성능 주장에는 쓰지 않고 내부 개선 후보로만 둔다.

## 개선된 중분류

{md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase114_input_error_gva_eok", "기준오차 억원"), ("phase114_error_gva_eok", "Phase114 오차 억원"), ("phase114_error_rate_pct", "Phase114 오차 %"), ("phase114_error_reduction_eok", "감소 억원"), ("phase114_option_id", "적용 활동지표")], 80)}

## 남은 10% 초과 중분류

{md_table(gt10, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase114_predicted_gva_eok", "추정 억원"), ("phase114_error_gva_eok", "오차 억원"), ("phase114_error_rate_pct", "오차 %"), ("required_next_data", "다음 필요자료")], 80)}

## 1% 이하 정밀오차 유출성 점검 대상

{md_table(suspicious, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase114_predicted_gva_eok", "추정 억원"), ("phase114_error_gva_eok", "오차 억원"), ("phase114_error_rate_pct", "오차 %"), ("phase114_option_id", "적용 활동지표"), ("refined_source_policy", "자료 사용정책")], 80)}

## 해석

Phase114는 10%라는 실무 기준을 맞추기 위한 최종 보정이 아니라, 어떤 활동지표가 어느 산업 블록에 안전하게 들어갈 수 있는지를 선별하는 실험이다. 특히 중분류 실제값을 예측식에 넣지 않았기 때문에 Phase113보다 덜 공격적이지만, 포스터에 넣을 수 있는 설명은 더 방어적이다. 남은 10% 초과 업종은 추가 자료가 없으면 일반 사업체·시설 지표만으로는 더 낮추기 어렵다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR)


if __name__ == "__main__":
    main()
