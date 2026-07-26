#!/usr/bin/env python3
"""Phase133: amount-weighted Goyang precision diagnostic and guarded routing.

The previous precision diagnostics focused heavily on percentage errors.  That
is useful for detecting unstable small industries, but it can overstate the
policy importance of tiny value-added cells and understate large absolute gaps
in high-GVA industries.  This phase re-ranks Goyang middle-industry diagnostics
by absolute GVA error and tests whether already-collected block/source packages
can reduce the amount-weighted gap without simply erasing residuals.

Important guardrail: this is a retrospective precision-routing screen.  It does
not certify strict flash eligibility; Phase132 remains the source-vintage gate.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase133_goyang_amount_weighted_refinement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase133_goyang_amount_weighted_refinement.md"

BASE = DATA / "phase130_goyang_precision_adoption" / "phase130_goyang_precision_registry.csv"
CANDIDATE_FILES = [
    (
        "phase113_goyang_openapi",
        DATA / "phase113_goyang_openapi_constrained_refinement" / "phase113_candidate_detail.csv",
    ),
    (
        "phase114_block_activity",
        DATA / "phase114_block_routed_refinement_audit" / "phase114_block_candidate_detail.csv",
    ),
    (
        "phase127_comwel",
        DATA / "phase127_precision_comwel_after_phase114" / "phase127_candidate_detail.csv",
    ),
]

LARGE_EOK = 1000.0
MIN_PACKAGE_REDUCTION_EOK = 50.0
MAX_HIGH_VALUE_WORSEN_EOK = 75.0
MAX_HIGH_VALUE_WORSEN_PP = 5.0


def read_base() -> pd.DataFrame:
    df = pd.read_csv(BASE, dtype={"middle_code": str})
    df = df[df["city"].eq("고양시")].copy()
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["current_prediction_eok"] = df["phase130_predicted_gva_eok"]
    df["current_error_eok"] = df["phase130_error_gva_eok"]
    df["current_error_rate_pct"] = df["phase130_error_rate_pct"]
    df["amount_tier"] = np.where(df["actual_gva_eok"].ge(LARGE_EOK), "large_1000eok_plus", "small_medium")
    total_actual = float(df["actual_gva_eok"].sum())
    df["actual_share_pct"] = df["actual_gva_eok"] / total_actual * 100 if total_actual else np.nan
    df["error_contribution_pct"] = df["current_error_eok"] / float(df["current_error_eok"].sum()) * 100
    return df


def normalize_candidate(source_phase: str, path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype={"middle_code": str})
    df = df[df["city"].eq("고양시")].copy()
    if df.empty:
        return df
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    if "block_id" not in df.columns:
        df["block_id"] = df["parent_code"] + "_parent"
    if "baseline_floor" not in df.columns:
        df["baseline_floor"] = np.nan
    if "option_label" not in df.columns:
        df["option_label"] = df.get("metric", df["option_id"])
    keep = [
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "block_id",
        "option_id",
        "option_label",
        "alpha",
        "baseline_floor",
        "candidate_predicted_gva_eok",
        "candidate_error_gva_eok",
        "candidate_error_rate_pct",
    ]
    out = df[keep].copy()
    out["source_phase"] = source_phase
    out["package_id"] = (
        out["source_phase"].astype(str)
        + "__"
        + out["parent_code"].astype(str)
        + "__"
        + out["block_id"].astype(str)
        + "__"
        + out["option_id"].astype(str)
        + "__a"
        + out["alpha"].astype(str)
        + "__f"
        + out["baseline_floor"].astype(str)
    )
    return out


def load_candidates() -> pd.DataFrame:
    frames = [normalize_candidate(name, path) for name, path in CANDIDATE_FILES]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def score_packages(base: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    if cand.empty:
        return pd.DataFrame()
    current = base[[
        "city",
        "parent_code",
        "middle_code",
        "current_prediction_eok",
        "current_error_eok",
        "current_error_rate_pct",
        "actual_gva_eok",
        "amount_tier",
    ]]
    d = cand.merge(current, on=["city", "parent_code", "middle_code", "actual_gva_eok"], how="inner")
    d["error_reduction_vs_current_eok"] = d["current_error_eok"] - d["candidate_error_gva_eok"]
    d["worsen_eok"] = np.maximum(d["candidate_error_gva_eok"] - d["current_error_eok"], 0)
    d["worsen_pp"] = np.maximum(d["candidate_error_rate_pct"] - d["current_error_rate_pct"], 0)
    d["high_value"] = d["actual_gva_eok"].ge(LARGE_EOK)
    d.to_csv(OUT / "phase133_candidate_cell_detail.csv", index=False)

    rows = []
    for pid, g in d.groupby("package_id", sort=False):
        high = g[g["high_value"]]
        current_error = float(g["current_error_eok"].sum())
        cand_error = float(g["candidate_error_gva_eok"].sum())
        high_current = float(high["current_error_eok"].sum()) if len(high) else 0.0
        high_cand = float(high["candidate_error_gva_eok"].sum()) if len(high) else 0.0
        rows.append({
            "package_id": pid,
            "source_phase": g["source_phase"].iloc[0],
            "parent_code": g["parent_code"].iloc[0],
            "block_id": g["block_id"].iloc[0],
            "option_id": g["option_id"].iloc[0],
            "option_label": g["option_label"].iloc[0],
            "alpha": g["alpha"].iloc[0],
            "baseline_floor": g["baseline_floor"].iloc[0],
            "middle_codes": ",".join(sorted(g["middle_code"].unique())),
            "cell_count": int(len(g)),
            "high_value_cell_count": int(len(high)),
            "current_error_eok": current_error,
            "candidate_error_eok": cand_error,
            "error_reduction_eok": current_error - cand_error,
            "current_high_value_error_eok": high_current,
            "candidate_high_value_error_eok": high_cand,
            "high_value_error_reduction_eok": high_current - high_cand,
            "worsened_cells": int((g["worsen_eok"] > 1e-9).sum()),
            "worsen_sum_eok": float(g["worsen_eok"].sum()),
            "high_value_worsen_sum_eok": float(g.loc[g["high_value"], "worsen_eok"].sum()),
            "max_high_value_worsen_eok": float(g.loc[g["high_value"], "worsen_eok"].max()) if len(high) else 0.0,
            "max_high_value_worsen_pp": float(g.loc[g["high_value"], "worsen_pp"].max()) if len(high) else 0.0,
        })
    screen = pd.DataFrame(rows)
    if screen.empty:
        return screen
    screen["amount_weighted_score"] = (
        screen["error_reduction_eok"]
        + 0.5 * screen["high_value_error_reduction_eok"]
        - 0.75 * screen["worsen_sum_eok"]
        - 2.0 * screen["high_value_worsen_sum_eok"]
    )
    screen["guarded_adoptable"] = (
        screen["error_reduction_eok"].ge(MIN_PACKAGE_REDUCTION_EOK)
        & screen["high_value_error_reduction_eok"].ge(0)
        & screen["max_high_value_worsen_eok"].le(MAX_HIGH_VALUE_WORSEN_EOK)
        & screen["max_high_value_worsen_pp"].le(MAX_HIGH_VALUE_WORSEN_PP)
        & screen["amount_weighted_score"].gt(0)
    )
    screen["rejection_reason"] = np.select(
        [
            screen["guarded_adoptable"],
            screen["error_reduction_eok"].lt(MIN_PACKAGE_REDUCTION_EOK),
            screen["high_value_error_reduction_eok"].lt(0),
            screen["max_high_value_worsen_eok"].gt(MAX_HIGH_VALUE_WORSEN_EOK),
            screen["max_high_value_worsen_pp"].gt(MAX_HIGH_VALUE_WORSEN_PP),
            screen["amount_weighted_score"].le(0),
        ],
        [
            "채택 가능",
            "총 금액오차 감소가 50억원 미만",
            "1,000억원 이상 업종 총오차 악화",
            "고액 업종 개별 악화액 초과",
            "고액 업종 개별 악화율 초과",
            "개선보다 악화·해석비용이 큼",
        ],
        default="기타",
    )
    return screen.sort_values(["guarded_adoptable", "amount_weighted_score"], ascending=[False, False]).reset_index(drop=True)


def greedy_route(base: pd.DataFrame, cand: pd.DataFrame, screen: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    registry = base.copy()
    registry["phase133_prediction_eok"] = registry["current_prediction_eok"]
    registry["phase133_selected_package_id"] = ""
    registry["phase133_selected_source_phase"] = "phase130_current"
    registry["phase133_selected_option_label"] = "기존 Phase130"
    selected_rows = []
    if cand.empty or screen.empty:
        return registry, pd.DataFrame()

    current = base[["city", "parent_code", "middle_code", "actual_gva_eok", "current_error_eok", "current_error_rate_pct"]]
    detail = cand.merge(current, on=["city", "parent_code", "middle_code", "actual_gva_eok"], how="inner")
    used: set[tuple[str, str]] = set()
    for _, pkg in screen[screen["guarded_adoptable"]].iterrows():
        rows = detail[detail["package_id"].eq(pkg["package_id"])].copy()
        keys = {(r.parent_code, r.middle_code) for r in rows.itertuples()}
        if used.intersection(keys):
            continue
        # Re-score against the current registry after earlier package adoption.
        recheck = rows.merge(
            registry[["parent_code", "middle_code", "phase133_prediction_eok", "actual_gva_eok"]],
            on=["parent_code", "middle_code", "actual_gva_eok"],
            how="inner",
        )
        current_error = (recheck["phase133_prediction_eok"] - recheck["actual_gva_eok"]).abs().sum()
        candidate_error = recheck["candidate_error_gva_eok"].sum()
        if current_error - candidate_error < MIN_PACKAGE_REDUCTION_EOK:
            continue
        value_map = rows.set_index(["parent_code", "middle_code"])["candidate_predicted_gva_eok"].to_dict()
        for key, value in value_map.items():
            mask = registry["parent_code"].eq(key[0]) & registry["middle_code"].eq(key[1])
            registry.loc[mask, "phase133_prediction_eok"] = float(value)
            registry.loc[mask, "phase133_selected_package_id"] = str(pkg["package_id"])
            registry.loc[mask, "phase133_selected_source_phase"] = str(pkg["source_phase"])
            registry.loc[mask, "phase133_selected_option_label"] = str(pkg["option_label"])
        selected_rows.append(pkg.to_dict() | {
            "rechecked_error_reduction_eok": float(current_error - candidate_error),
        })
        used.update(keys)

    registry["phase133_error_eok"] = (registry["phase133_prediction_eok"] - registry["actual_gva_eok"]).abs()
    registry["phase133_error_rate_pct"] = np.where(
        registry["actual_gva_eok"] > 0,
        registry["phase133_error_eok"] / registry["actual_gva_eok"] * 100,
        np.nan,
    )
    registry["phase133_error_reduction_eok"] = registry["current_error_eok"] - registry["phase133_error_eok"]
    registry["phase133_worse_vs_phase130"] = registry["phase133_error_eok"] > registry["current_error_eok"] + 1e-9
    return registry, pd.DataFrame(selected_rows)


def city_metrics(df: pd.DataFrame, pred_col: str, err_col: str, rate_col: str) -> dict[str, object]:
    actual = float(df["actual_gva_eok"].sum())
    err = float(df[err_col].sum())
    large = df[df["actual_gva_eok"].ge(LARGE_EOK)]
    small = df[df["actual_gva_eok"].lt(LARGE_EOK)]
    return {
        "actual_sum_eok": actual,
        "error_sum_eok": err,
        "wape_pct": err / actual * 100 if actual else np.nan,
        "large_cell_count": int(len(large)),
        "large_error_sum_eok": float(large[err_col].sum()),
        "large_wape_pct": float(large[err_col].sum()) / float(large["actual_gva_eok"].sum()) * 100 if len(large) else np.nan,
        "small_medium_gt20_cells": int((small[rate_col] > 20).sum()),
        "gt10_cells": int((df[rate_col] > 10).sum()),
        "gt20_cells": int((df[rate_col] > 20).sum()),
        "max_abs_gap_eok": float(df[err_col].max()),
        "prediction_sum_eok": float(df[pred_col].sum()),
    }


def summarize(base: pd.DataFrame, registry: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    before = city_metrics(base, "current_prediction_eok", "current_error_eok", "current_error_rate_pct")
    before["scenario"] = "phase130_current"
    after = city_metrics(registry, "phase133_prediction_eok", "phase133_error_eok", "phase133_error_rate_pct")
    after["scenario"] = "phase133_guarded_amount_route"
    summary = pd.DataFrame([before, after])
    summary["selected_package_count"] = [0, int(len(selected))]
    return summary[[
        "scenario",
        "actual_sum_eok",
        "prediction_sum_eok",
        "error_sum_eok",
        "wape_pct",
        "large_cell_count",
        "large_error_sum_eok",
        "large_wape_pct",
        "small_medium_gt20_cells",
        "gt10_cells",
        "gt20_cells",
        "max_abs_gap_eok",
        "selected_package_count",
    ]]


def accounting_checks(base: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for parent, g in registry.groupby("parent_code"):
        base_g = base[base["parent_code"].eq(parent)]
        actual = float(g["actual_gva_eok"].sum())
        pred = float(g["phase133_prediction_eok"].sum())
        base_pred = float(base_g["current_prediction_eok"].sum())
        rows.append({
            "parent_code": parent,
            "actual_sum_eok": actual,
            "phase130_prediction_sum_eok": base_pred,
            "phase133_prediction_sum_eok": pred,
            "phase130_parent_gap_eok": base_pred - actual,
            "phase133_parent_gap_eok": pred - actual,
        })
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    labels = [c.replace("_eok", " 억원").replace("_pct", " %").replace("_", " ") for c in d.columns]

    def fmt(v: object) -> str:
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            return f"{float(v):,.2f}"
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        return str(v).replace("|", "\\|")

    body = ["| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *body])


def write_report(base: pd.DataFrame, screen: pd.DataFrame, selected: pd.DataFrame, registry: pd.DataFrame, summary: pd.DataFrame, checks: pd.DataFrame) -> None:
    current_top = base.sort_values("current_error_eok", ascending=False).head(12)
    selected_view = selected.sort_values("rechecked_error_reduction_eok", ascending=False) if not selected.empty else selected
    rejected_view = screen[
        ~screen["guarded_adoptable"] & screen["error_reduction_eok"].gt(0)
    ].sort_values("error_reduction_eok", ascending=False).drop_duplicates(
        ["source_phase", "parent_code", "block_id", "option_label", "middle_codes", "rejection_reason"]
    )
    remaining_top = registry.sort_values("phase133_error_eok", ascending=False).head(12)
    small_high_pct = base[base["actual_gva_eok"].lt(LARGE_EOK) & base["current_error_rate_pct"].gt(20)].sort_values("current_error_eok", ascending=False)
    REPORT.write_text("\n".join([
        "# Phase133 고양시 금액가중 GVA 정밀진단 및 보수적 개선 후보",
        "",
        "## 목적",
        "",
        "고양시 중분류 GVA 진단을 상대오차 중심에서 금액가중 관점으로 재정렬했다. 실제 금액이 작은 업종은 %오차가 커도 정책 총량 영향이 작을 수 있으므로, `억원 격차`, `전체 오차 기여도`, `1,000억원 이상 업종 WAPE`를 함께 본다.",
        "",
        "## 적용 기준",
        "",
        "- 기준값: Phase130 고양시 정밀화 레지스트리.",
        "- 후보값: 기존 Phase113/114/127에서 이미 산출된 고양시 블록 단위 활동자료 후보.",
        "- 채택조건: 블록 패키지 단위 오차 50억원 이상 감소, 1,000억원 이상 업종 총오차 악화 없음, 고액 업종 개별 악화 75억원·5%p 이하.",
        "- 주의: 실제값을 이용한 사후 검증 화면이므로 엄격 속보 성능 주장이 아니다. 속보 투입 가능성은 Phase132 공표시차 감사 결과를 따라야 한다.",
        "",
        "## 전체 성능 요약",
        "",
        md_table(summary, summary.columns.tolist()),
        "",
        "## 현재 금액격차 상위 중분류",
        "",
        md_table(current_top, ["parent_code", "middle_code", "middle_label", "actual_gva_eok", "current_prediction_eok", "current_error_eok", "current_error_rate_pct", "actual_share_pct", "error_contribution_pct"]),
        "",
        "## 선택된 금액가중 개선 패키지",
        "",
        md_table(selected_view, ["source_phase", "parent_code", "block_id", "option_label", "middle_codes", "current_error_eok", "candidate_error_eok", "error_reduction_eok", "high_value_error_reduction_eok", "rechecked_error_reduction_eok"], n=20),
        "",
        "## 채택하지 않은 개선 후보",
        "",
        md_table(rejected_view, ["source_phase", "parent_code", "block_id", "option_label", "middle_codes", "error_reduction_eok", "high_value_error_reduction_eok", "worsen_sum_eok", "amount_weighted_score", "rejection_reason"], n=12),
        "",
        "## 개선 후 잔여 금액격차 상위 중분류",
        "",
        md_table(remaining_top, ["parent_code", "middle_code", "middle_label", "actual_gva_eok", "phase133_prediction_eok", "phase133_error_eok", "phase133_error_rate_pct", "phase133_selected_source_phase", "phase133_selected_option_label"]),
        "",
        "## 작은 금액·높은 상대오차 업종 분리",
        "",
        md_table(small_high_pct, ["parent_code", "middle_code", "middle_label", "actual_gva_eok", "current_error_eok", "current_error_rate_pct", "error_contribution_pct"], n=15),
        "",
        "## 상위산업 합계 점검",
        "",
        md_table(checks, checks.columns.tolist()),
        "",
        "## 판정",
        "",
        "1. 고양시는 `%오차 고위험`과 `금액격차 고위험`이 완전히 같지 않다. 협회·단체처럼 상대오차가 큰 업종도 중요하지만, 스포츠·오락·금융·전문서비스처럼 금액이 큰 업종의 억원 격차가 정책 설명력에 더 직접적으로 작용한다.",
        "2. 기존 후보 중 금액가중 기준을 통과해 바로 바꿀 수 있는 패키지는 없었다. 도시공원·운동시설 계열 후보는 ERS 총오차를 조금 줄이지만 다른 세부 업종 악화가 커서 채택하지 않는 것이 안전하다.",
        "3. 다음 개선은 `큰 금액·잔여오차 상위` 업종을 우선 대상으로 삼아야 한다. 특히 스포츠·오락 서비스업, 방송업, 영상·오디오 제작업은 전용 활동자료가 필요하다. 작은 금액 업종의 20% 초과 상대오차는 별도 보조지표로 관리하되, 포스터/정책 메시지에서는 억원 격차와 오차 기여도를 병기하는 편이 더 정직하다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = read_base()
    cand = load_candidates()
    screen = score_packages(base, cand)
    registry, selected = greedy_route(base, cand, screen)
    summary = summarize(base, registry, selected)
    checks = accounting_checks(base, registry)

    base.to_csv(OUT / "phase133_current_amount_diagnostics.csv", index=False)
    cand.to_csv(OUT / "phase133_candidate_packages_raw.csv", index=False)
    screen.to_csv(OUT / "phase133_candidate_package_screen.csv", index=False)
    selected.to_csv(OUT / "phase133_selected_packages.csv", index=False)
    registry.to_csv(OUT / "phase133_guarded_amount_route_registry.csv", index=False)
    summary.to_csv(OUT / "phase133_summary.csv", index=False)
    checks.to_csv(OUT / "phase133_parent_accounting_checks.csv", index=False)
    write_report(base, screen, selected, registry, summary, checks)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
