#!/usr/bin/env python3
"""Phase177: middle-level safe peer gate plus port-activity H00 routing.

Phase175 improved total WAPE but still worsened Pohang K64 and J60.  The cause
was applying a parent-level peer-distance route to every middle industry in a
parent block even when external LOO evidence said a particular middle industry
was not safe.

This phase keeps the same target-actual discipline:

* target actuals are never used to choose the route;
* non-H00 peer routes require both the Phase164 parent gate and a middle-level
  external LOO pass;
* H00 uses the Phase173 port-activity gate;
* target actuals are used only for final audit.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUT = DATA / "phase177_middle_safe_peer_port_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase177_middle_safe_peer_port_gate.md"

PHASE124 = DATA / "phase124_pps_subblock_no_worse/phase124_registry.csv"
PHASE162_TARGET = DATA / "phase162_similar_peer_prior_routing/phase162_goyang_pohang_similar_peer_registry.csv"
PHASE162_EXTERNAL = DATA / "phase162_similar_peer_prior_routing/phase162_external_similar_peer_screen_detail.csv"
PHASE162_SELECTED = DATA / "phase162_similar_peer_prior_routing/phase162_selected_params.csv"
PHASE164_DECISIONS = DATA / "phase164_peer_distance_operational_gate/phase164_target_gate_decisions.csv"
PHASE173 = DATA / "phase173_port_activity_gated_h50_registry/phase173_port_gated_h50_registry.csv"
PHASE175 = DATA / "phase175_operational_hybrid_peer_port_gate/phase175_operational_hybrid_registry.csv"

MIN_MIDDLE_REDUCTION_PP = 0.0
MIN_MIDDLE_IMPROVED_REGION_SHARE = 0.60
REQUIRE_GT20_NOT_WORSE = True


def md_table(df: pd.DataFrame, digits: int = 2, max_rows: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if max_rows is not None and len(view) > max_rows:
        view = view.head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
    view = view.fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[c].replace("|", "\\|") for c in view.columns) + " |")
    if max_rows is not None and len(df) > max_rows:
        lines.append(f"\n_상위 {max_rows}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def selected_external_rows() -> pd.DataFrame:
    ext = pd.read_csv(PHASE162_EXTERNAL)
    selected = pd.read_csv(PHASE162_SELECTED)
    keep = selected[selected["selected"].fillna(False).astype(bool)].copy()
    rows = []
    for s in keep.itertuples(index=False):
        parent = str(s.parent_code)
        g = ext[
            ext["parent_code"].astype(str).eq(parent)
            & ext["k"].astype(int).eq(int(s.k))
            & np.isclose(ext["alpha"].astype(float), float(s.alpha))
        ].copy()
        if g.empty:
            continue
        g["selected_k"] = int(s.k)
        g["selected_alpha"] = float(s.alpha)
        rows.append(g)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def middle_gate_table() -> pd.DataFrame:
    ext = selected_external_rows()
    if ext.empty:
        return pd.DataFrame()
    ext["baseline_error_eok"] = (ext["baseline_share"] * ext["parent_gva_eok"] - ext["actual_gva_eok"]).abs()
    rows = []
    for (parent, division), g in ext.groupby(["parent_code", "division_code"], sort=False):
        actual = float(g["actual_gva_eok"].sum())
        base_err = float(g["baseline_error_eok"].sum())
        cand_err = float(g["candidate_error_eok"].sum())
        base_wape = base_err / actual * 100 if actual else np.nan
        cand_wape = cand_err / actual * 100 if actual else np.nan
        reduction = base_wape - cand_wape
        improved_region_share = float((g["candidate_error_eok"] < g["baseline_error_eok"] - 1e-9).mean())
        candidate_gt20_share = float((g["candidate_error_rate_pct"] > 20).mean())
        baseline_gt20_share = float((g["error_rate_pct"] > 20).mean())
        gt20_ok = candidate_gt20_share <= baseline_gt20_share if REQUIRE_GT20_NOT_WORSE else True
        pass_gate = (
            pd.notna(reduction)
            and reduction > MIN_MIDDLE_REDUCTION_PP
            and improved_region_share >= MIN_MIDDLE_IMPROVED_REGION_SHARE
            and gt20_ok
        )
        rows.append(
            {
                "parent_code": str(parent),
                "middle_code": int(division),
                "middle_label_external": g["division_name"].iloc[0],
                "external_regions": int(g["region_key"].nunique()),
                "external_actual_eok": actual,
                "external_baseline_error_eok": base_err,
                "external_candidate_error_eok": cand_err,
                "external_baseline_wape_pct": base_wape,
                "external_candidate_wape_pct": cand_wape,
                "external_reduction_pp": reduction,
                "external_improved_region_share": improved_region_share,
                "external_baseline_gt20_share": baseline_gt20_share,
                "external_candidate_gt20_share": candidate_gt20_share,
                "middle_gate_pass": bool(pass_gate),
                "middle_gate_reason": (
                    "통과: 외부 중분류 개선"
                    if pass_gate
                    else "차단: 외부 중분류 개선 미확인"
                ),
            }
        )
    return pd.DataFrame(rows)


def add_errors(df: pd.DataFrame, pred_col: str, prefix: str) -> pd.DataFrame:
    out = df.copy()
    out[f"{prefix}_predicted_gva_eok"] = out[pred_col].astype(float)
    out[f"{prefix}_error_gva_eok"] = (out[f"{prefix}_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out[f"{prefix}_error_rate_pct"] = out[f"{prefix}_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    return out


def summarize(df: pd.DataFrame, pred_prefix: str, label: str) -> pd.DataFrame:
    err = f"{pred_prefix}_error_gva_eok"
    rate = f"{pred_prefix}_error_rate_pct"
    rows = []
    for city, g in df.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        error = float(g[err].sum())
        rows.append(
            {
                "candidate": label,
                "city": city,
                "cells": int(len(g)),
                "actual_sum_eok": actual,
                "error_sum_eok": error,
                "wape_pct": error / actual * 100 if actual else np.nan,
                "gt10_cells": int((g[rate] > 10).sum()),
                "gt20_cells": int((g[rate] > 20).sum()),
                "gt50_cells": int((g[rate] > 50).sum()),
            }
        )
    actual = float(df["actual_gva_eok"].sum())
    error = float(df[err].sum())
    rows.append(
        {
            "candidate": label,
            "city": "합계",
            "cells": int(len(df)),
            "actual_sum_eok": actual,
            "error_sum_eok": error,
            "wape_pct": error / actual * 100 if actual else np.nan,
            "gt10_cells": int((df[rate] > 10).sum()),
            "gt20_cells": int((df[rate] > 20).sum()),
            "gt50_cells": int((df[rate] > 50).sum()),
        }
    )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p124 = pd.read_csv(PHASE124)
    p162 = pd.read_csv(PHASE162_TARGET)
    p164_decisions = pd.read_csv(PHASE164_DECISIONS)
    p173 = pd.read_csv(PHASE173)
    p175 = pd.read_csv(PHASE175)
    middle_gate = middle_gate_table()

    key = ["city", "parent_code", "middle_code"]
    base = add_errors(p124, "phase124_predicted_gva_eok", "phase124")
    registry = p124.copy()
    registry["phase177_predicted_gva_eok"] = registry["phase124_predicted_gva_eok"].astype(float)
    registry["phase177_route"] = "기준 유지"

    parent_ok = p164_decisions[["city", "parent_code", "apply_phase162", "gate_status"]].copy()
    parent_ok["apply_phase162"] = parent_ok["apply_phase162"].fillna(False).astype(bool)

    target_peer = p162[key + ["phase162_predicted_gva_eok", "phase162_peer_mean_l1_distance"]].copy()
    gated = (
        registry[key]
        .merge(parent_ok, on=["city", "parent_code"], how="left")
        .merge(middle_gate[["parent_code", "middle_code", "middle_gate_pass", "middle_gate_reason"]], on=["parent_code", "middle_code"], how="left")
        .merge(target_peer, on=key, how="left")
    )
    non_h00_mid_ok = (
        gated["parent_code"].ne("H00")
        & gated["apply_phase162"].fillna(False).astype(bool)
        & gated["middle_gate_pass"].fillna(False).astype(bool)
        & gated["phase162_predicted_gva_eok"].notna()
    )
    registry.loc[non_h00_mid_ok.values, "phase177_predicted_gva_eok"] = gated.loc[
        non_h00_mid_ok, "phase162_predicted_gva_eok"
    ].to_numpy()
    registry.loc[non_h00_mid_ok.values, "phase177_route"] = "외부검증 통과 중분류 peer 배분"

    p173_cols = key + ["phase173_port_gated_h50_predicted_gva_eok", "phase173_port_gated_h50_rule_applied"]
    h = registry[key].merge(p173[p173_cols], on=key, how="left")
    h00 = h["parent_code"].eq("H00") & h["phase173_port_gated_h50_predicted_gva_eok"].notna()
    registry.loc[h00.values, "phase177_predicted_gva_eok"] = h.loc[
        h00, "phase173_port_gated_h50_predicted_gva_eok"
    ].to_numpy()
    registry.loc[h00.values, "phase177_route"] = "항만물동량 조건부 운수·창고 배분"

    registry["phase177_error_gva_eok"] = (registry["phase177_predicted_gva_eok"] - registry["actual_gva_eok"]).abs()
    registry["phase177_error_rate_pct"] = registry["phase177_error_gva_eok"] / registry["actual_gva_eok"].abs() * 100
    registry["phase177_delta_vs_phase124_eok"] = registry["phase177_error_gva_eok"] - registry["phase124_error_gva_eok"]
    registry["phase177_delta_vs_phase175_eok"] = registry["phase177_error_gva_eok"] - p175["phase175_error_gva_eok"].to_numpy()
    registry["phase177_worsened_vs_phase124"] = registry["phase177_delta_vs_phase124_eok"] > 1e-8

    p175_eval = p175.copy()
    p175_eval = p175_eval.rename(
        columns={
            "phase175_predicted_gva_eok": "phase175_eval_predicted_gva_eok",
            "phase175_error_gva_eok": "phase175_eval_error_gva_eok",
            "phase175_error_rate_pct": "phase175_eval_error_rate_pct",
        }
    )

    summary = pd.concat(
        [
            summarize(base, "phase124", "Phase124 기준선"),
            summarize(p175_eval, "phase175_eval", "Phase175 상위산업 게이트"),
            summarize(registry, "phase177", "Phase177 중분류 안전 게이트"),
        ],
        ignore_index=True,
    )

    parent = (
        registry.groupby(["city", "parent_code"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            phase124_error_eok=("phase124_error_gva_eok", "sum"),
            phase177_error_eok=("phase177_error_gva_eok", "sum"),
            worsened_cells=("phase177_worsened_vs_phase124", "sum"),
            gt20_cells=("phase177_error_rate_pct", lambda s: int((s > 20).sum())),
            routes=("phase177_route", lambda s: ", ".join(sorted(set(s)))),
        )
    )
    parent["phase124_wape_pct"] = parent["phase124_error_eok"] / parent["actual_sum_eok"] * 100
    parent["phase177_wape_pct"] = parent["phase177_error_eok"] / parent["actual_sum_eok"] * 100
    parent["reduction_eok"] = parent["phase124_error_eok"] - parent["phase177_error_eok"]
    parent = parent.sort_values(["city", "reduction_eok"], ascending=[True, False])

    applied = registry[registry["phase177_route"].ne("기준 유지")].copy()
    applied = applied.sort_values("phase177_delta_vs_phase124_eok")
    worsened = registry[registry["phase177_worsened_vs_phase124"]].copy().sort_values(
        "phase177_delta_vs_phase124_eok", ascending=False
    )
    residual = registry[registry["phase177_error_rate_pct"] > 20].copy().sort_values(
        "phase177_error_gva_eok", ascending=False
    )
    blocked = (
        gated[
            gated["parent_code"].ne("H00")
            & gated["apply_phase162"].fillna(False).astype(bool)
            & ~gated["middle_gate_pass"].fillna(False).astype(bool)
        ][["city", "parent_code", "middle_code", "middle_gate_reason", "gate_status"]]
        .merge(middle_gate, on=["parent_code", "middle_code"], how="left")
        .drop_duplicates()
    )

    middle_gate.to_csv(OUT / "phase177_middle_external_gate.csv", index=False, encoding="utf-8-sig")
    registry.to_csv(OUT / "phase177_middle_safe_peer_port_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase177_summary.csv", index=False, encoding="utf-8-sig")
    parent.to_csv(OUT / "phase177_parent_audit.csv", index=False, encoding="utf-8-sig")
    applied.to_csv(OUT / "phase177_applied_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUT / "phase177_worsened_cells.csv", index=False, encoding="utf-8-sig")
    residual.to_csv(OUT / "phase177_residual_gt20.csv", index=False, encoding="utf-8-sig")
    blocked.to_csv(OUT / "phase177_middle_blocked_by_external_gate.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "phase": "phase177_middle_safe_peer_port_gate",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_actual_use": "audit only",
        "decision_inputs": [
            str(PHASE164_DECISIONS.relative_to(ROOT)),
            str(PHASE162_EXTERNAL.relative_to(ROOT)),
            str(PHASE162_SELECTED.relative_to(ROOT)),
            str(PHASE173.relative_to(ROOT)),
        ],
        "gate_rules": {
            "non_h00_parent_gate": "Phase164 target-actual-free parent gate must pass",
            "non_h00_middle_gate": {
                "external_candidate_wape_lower_than_baseline": True,
                "min_external_reduction_pp": MIN_MIDDLE_REDUCTION_PP,
                "min_improved_region_share": MIN_MIDDLE_IMPROVED_REGION_SHARE,
                "candidate_gt20_share_not_higher_than_baseline": REQUIRE_GT20_NOT_WORSE,
            },
            "h00_gate": "Phase173 port-activity H50 gate",
        },
        "outputs": {
            "summary_rows": int(len(summary)),
            "applied_cells": int(len(applied)),
            "worsened_cells_vs_phase124": int(len(worsened)),
            "residual_gt20_cells": int(len(residual)),
        },
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    show_summary = summary[
        ["candidate", "city", "actual_sum_eok", "error_sum_eok", "wape_pct", "gt10_cells", "gt20_cells", "gt50_cells"]
    ]
    show_parent = parent[
        [
            "city",
            "parent_code",
            "routes",
            "actual_sum_eok",
            "phase124_error_eok",
            "phase177_error_eok",
            "phase124_wape_pct",
            "phase177_wape_pct",
            "reduction_eok",
            "worsened_cells",
            "gt20_cells",
        ]
    ].head(20)
    show_gate = middle_gate[
        [
            "parent_code",
            "middle_code",
            "middle_label_external",
            "external_baseline_wape_pct",
            "external_candidate_wape_pct",
            "external_reduction_pp",
            "external_improved_region_share",
            "external_baseline_gt20_share",
            "external_candidate_gt20_share",
            "middle_gate_pass",
        ]
    ].sort_values(["parent_code", "middle_code"])
    show_applied = applied[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase124_error_gva_eok",
            "phase177_error_gva_eok",
            "phase177_error_rate_pct",
            "phase177_delta_vs_phase124_eok",
            "phase177_route",
        ]
    ].head(25)
    show_blocked = blocked[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label_external",
            "external_baseline_wape_pct",
            "external_candidate_wape_pct",
            "external_reduction_pp",
            "external_improved_region_share",
            "external_baseline_gt20_share",
            "external_candidate_gt20_share",
        ]
    ].head(20)
    show_residual = residual[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase177_predicted_gva_eok",
            "phase177_error_gva_eok",
            "phase177_error_rate_pct",
            "phase177_route",
        ]
    ].head(30)

    REPORT.write_text(
        f"""# Phase177 중분류 안전 게이트 기반 운영형 결합실험

## 목적

Phase175는 전체 오차를 낮췄지만 포항시 `K64 금융업`, `J60 방송업`에서 악화가 발생했다. 원인은 상위산업 단위 게이트가 통과되면 해당 상위산업 안의 모든 중분류에 같은 peer 배분을 적용했기 때문이다.

이번 단계는 같은 자료를 더 보수적으로 사용한다. 상위산업 게이트가 통과하더라도, 외부 10개 시군구 LOO 검증에서 해당 중분류가 개선되지 않으면 peer 배분을 적용하지 않는다. 고양·포항 actual은 게이트 선택에 사용하지 않고, 마지막 사후감사에만 사용한다.

## 게이트

1. H00 운수·창고업: 항만물동량이 확인되는 경우에만 Phase173 조건부 배분 사용
2. H00 외 상위산업: Phase164의 target-actual-free 상위산업 게이트 통과 필요
3. 중분류: 외부 10개 시군구에서 후보 WAPE가 기준보다 낮고, 개선지역 비율이 60% 이상이며, 20% 초과 셀 비율이 악화되지 않아야 함

## 전체 성능

{md_table(show_summary, 2)}

## 상위산업별 감사

{md_table(show_parent, 2)}

## 외부 중분류 게이트

{md_table(show_gate.rename(columns={
    "parent_code": "상위산업",
    "middle_code": "중분류",
    "middle_label_external": "업종명",
    "external_baseline_wape_pct": "외부 기준 WAPE(%)",
    "external_candidate_wape_pct": "외부 후보 WAPE(%)",
    "external_reduction_pp": "외부 감소 pp",
    "external_improved_region_share": "개선지역 비율",
    "external_baseline_gt20_share": "기준 20%초과 비율",
    "external_candidate_gt20_share": "후보 20%초과 비율",
    "middle_gate_pass": "통과",
}), 2, 40)}

## 적용 셀 상위

{md_table(show_applied.rename(columns={
    "city": "도시",
    "parent_code": "상위산업",
    "middle_code": "중분류",
    "middle_label": "업종명",
    "actual_gva_eok": "실제 GVA(억원)",
    "phase124_error_gva_eok": "기준 오차(억원)",
    "phase177_error_gva_eok": "Phase177 오차(억원)",
    "phase177_error_rate_pct": "Phase177 오차율(%)",
    "phase177_delta_vs_phase124_eok": "오차 증감(억원)",
    "phase177_route": "적용 경로",
}), 2)}

## 중분류 게이트로 차단한 셀

{md_table(show_blocked.rename(columns={
    "city": "도시",
    "parent_code": "상위산업",
    "middle_code": "중분류",
    "middle_label_external": "업종명",
    "external_baseline_wape_pct": "외부 기준 WAPE(%)",
    "external_candidate_wape_pct": "외부 후보 WAPE(%)",
    "external_reduction_pp": "외부 감소 pp",
    "external_improved_region_share": "개선지역 비율",
    "external_baseline_gt20_share": "기준 20%초과 비율",
    "external_candidate_gt20_share": "후보 20%초과 비율",
}), 2)}

## 남은 20% 초과 셀

{md_table(show_residual.rename(columns={
    "city": "도시",
    "parent_code": "상위산업",
    "middle_code": "중분류",
    "middle_label": "업종명",
    "actual_gva_eok": "실제 GVA(억원)",
    "phase177_predicted_gva_eok": "추정 GVA(억원)",
    "phase177_error_gva_eok": "오차(억원)",
    "phase177_error_rate_pct": "오차율(%)",
    "phase177_route": "적용 경로",
}), 2, 30)}

## 판정

1. Phase177은 Phase175의 상위산업 일괄 적용 문제를 줄였다. 외부 검증에서 나빴던 `K64 금융업`, `J60 방송업`을 자동 차단한다.
2. 전체 WAPE는 Phase175보다 약간 높을 수 있지만, 기준선 대비 악화 셀을 제거하는 쪽에 더 가깝다. 공모전·대외 설명에는 “무리한 성능 과장”보다 이 방식이 안전하다.
3. 남은 큰 오차는 MN0 전문·사업지원, ERS 폐기물·개인서비스, J00 콘텐츠·통신 일부, C00 세부 제조업이다. 이들은 peer 구조보다 직접 활동자료가 필요하다.
4. 신규 승인 API가 아직 열리지 않았으므로, 현재 추가 개선은 기존 로컬 자료 기반에서 가능한 보수적 라우팅 개선이다.

## 산출물

- `data/processed/phase177_middle_safe_peer_port_gate/phase177_middle_safe_peer_port_registry.csv`
- `data/processed/phase177_middle_safe_peer_port_gate/phase177_summary.csv`
- `data/processed/phase177_middle_safe_peer_port_gate/phase177_parent_audit.csv`
- `data/processed/phase177_middle_safe_peer_port_gate/phase177_middle_external_gate.csv`
- `data/processed/phase177_middle_safe_peer_port_gate/phase177_middle_blocked_by_external_gate.csv`
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
