#!/usr/bin/env python3
"""Phase162: similar-peer prior routing for middle-industry GVA.

Phase160 used a simple external median prior.  That helped some blocks but
hurt others.  This phase selects peers by similarity of *observable predicted
middle shares* inside each parent industry:

* external validation: leave one external sigungu out, find k nearest external
  peers using baseline predicted shares, use their actual shares as a prior;
* target application: find nearest external peers for Goyang/Pohang using their
  Phase124 middle-share vector; apply only parameters selected from external
  validation.

Goyang/Pohang actuals are used only for final evaluation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase162_similar_peer_prior_routing"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase162_similar_peer_prior_routing.md"
EXTERNAL = DATA / "phase108_collected_10_sigungu_generalization" / "phase108_collected_10_sigungu_middle_accuracy_detail.csv"
BASE = DATA / "phase124_pps_subblock_no_worse" / "phase124_registry.csv"

ALPHAS = [0.0, 0.10, 0.20, 0.35, 0.50, 0.65, 0.80]
K_VALUES = [1, 3, 5]
MIN_EXTERNAL_REDUCTION_PP = 1.0
MAX_EXTERNAL_P90_WORSEN_PP = 3.0


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
        lines.append("| " + " | ".join(row[col].replace("|", "\\|") for col in view.columns) + " |")
    if max_rows is not None and len(df) > max_rows:
        lines.append(f"\n_상위 {max_rows}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def normalize_group(df: pd.DataFrame, group_cols: list[str], source_col: str, out_col: str) -> pd.DataFrame:
    out = df.copy()
    total = out.groupby(group_cols)[source_col].transform("sum")
    n = out.groupby(group_cols)[source_col].transform("size")
    out[out_col] = np.where(total > 0, out[source_col] / total, 1.0 / n)
    return out


def load_external() -> pd.DataFrame:
    df = pd.read_csv(EXTERNAL)
    df = df[df["split_evaluable"].astype(bool)].copy()
    df["division_code"] = df["division_code"].astype(str).str.zfill(2)
    df["region_key"] = df["source_region"].astype(str) + "|" + df["sigungu_name"].astype(str)
    for c in ["actual_share", "predicted_share", "parent_gva_eok", "actual_gva_eok"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return normalize_group(df, ["region_key", "parent_code"], "predicted_share", "baseline_share")


def load_target() -> pd.DataFrame:
    df = pd.read_csv(BASE)
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["division_code"] = df["middle_code"]
    df["region_key"] = df["city"]
    for c in ["actual_gva_eok", "phase124_predicted_gva_eok", "phase124_error_gva_eok"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["parent_actual_eok"] = df.groupby(["city", "parent_code"])["actual_gva_eok"].transform("sum")
    df["phase124_parent_predicted_sum_eok"] = df.groupby(["city", "parent_code"])["phase124_predicted_gva_eok"].transform("sum")
    df["baseline_share_raw"] = df["phase124_predicted_gva_eok"] / df["phase124_parent_predicted_sum_eok"].replace(0, np.nan)
    df = normalize_group(df, ["city", "parent_code"], "baseline_share_raw", "baseline_share")
    df["parent_controlled_predicted_gva_eok"] = df["baseline_share"] * df["parent_actual_eok"]
    df["parent_controlled_error_gva_eok"] = (df["parent_controlled_predicted_gva_eok"] - df["actual_gva_eok"]).abs()
    df["parent_controlled_error_rate_pct"] = df["parent_controlled_error_gva_eok"] / df["actual_gva_eok"].replace(0, np.nan) * 100
    return df


def vector_for(g: pd.DataFrame, divisions: list[str], share_col: str) -> np.ndarray:
    s = g.set_index("division_code")[share_col]
    return np.array([float(s.get(d, 0.0)) for d in divisions], dtype=float)


def nearest_regions(parent_df: pd.DataFrame, holdout_or_target: pd.DataFrame, divisions: list[str], k: int, exclude: str | None) -> list[tuple[str, float]]:
    target_vec = vector_for(holdout_or_target, divisions, "baseline_share")
    distances = []
    for region, rg in parent_df.groupby("region_key", sort=False):
        if exclude is not None and region == exclude:
            continue
        vec = vector_for(rg, divisions, "baseline_share")
        distances.append((region, float(np.abs(target_vec - vec).sum())))
    distances.sort(key=lambda x: (x[1], x[0]))
    return distances[: max(1, min(k, len(distances)))]


def prior_from_peers(parent_df: pd.DataFrame, peers: list[str], divisions: list[str], fallback: np.ndarray) -> np.ndarray:
    rows = []
    for region in peers:
        rg = parent_df[parent_df["region_key"].eq(region)]
        rows.append(vector_for(rg, divisions, "actual_share"))
    if not rows:
        prior = fallback.copy()
    else:
        prior = np.nanmedian(np.vstack(rows), axis=0)
    prior = np.where(np.isfinite(prior), prior, 0.0)
    # Avoid turning unseen external industries into hard zeros in target regions.
    prior = np.where(prior > 0, prior, fallback * 0.25)
    total = prior.sum()
    return prior / total if total > 0 else fallback


def evaluate_external(parent_df: pd.DataFrame, alpha: float, k: int) -> pd.DataFrame:
    divisions = sorted(parent_df["division_code"].unique())
    parts = []
    for region, rg in parent_df.groupby("region_key", sort=False):
        tmp = rg.copy()
        baseline = vector_for(tmp, divisions, "baseline_share")
        peers_with_dist = nearest_regions(parent_df, tmp, divisions, k=k, exclude=region)
        peers = [p for p, _ in peers_with_dist]
        prior = prior_from_peers(parent_df, peers, divisions, baseline)
        cand_share = (1 - alpha) * baseline + alpha * prior
        cand_share = cand_share / cand_share.sum() if cand_share.sum() > 0 else baseline
        share_map = dict(zip(divisions, cand_share))
        tmp["peer_regions"] = ",".join(peers)
        tmp["peer_mean_l1_distance"] = float(np.mean([d for _, d in peers_with_dist])) if peers_with_dist else np.nan
        tmp["candidate_share"] = tmp["division_code"].map(share_map).astype(float)
        tmp["candidate_gva_eok"] = tmp["candidate_share"] * tmp["parent_gva_eok"]
        tmp["candidate_error_eok"] = (tmp["candidate_gva_eok"] - tmp["actual_gva_eok"]).abs()
        tmp["candidate_error_rate_pct"] = tmp["candidate_error_eok"] / tmp["actual_gva_eok"].replace(0, np.nan) * 100
        parts.append(tmp)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def screen_external(ext: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries, details = [], []
    for parent, g in ext.groupby("parent_code", sort=False):
        if g["region_key"].nunique() < 3 or g["division_code"].nunique() < 2:
            continue
        base_error = float((g["baseline_share"] * g["parent_gva_eok"] - g["actual_gva_eok"]).abs().sum())
        base_actual = float(g["actual_gva_eok"].sum())
        base_wape = base_error / base_actual * 100 if base_actual else np.nan
        base_p90 = float(g["error_rate_pct"].quantile(0.9))
        for k in K_VALUES:
            if k >= g["region_key"].nunique():
                continue
            for alpha in ALPHAS:
                cand = evaluate_external(g, alpha=alpha, k=k)
                err = float(cand["candidate_error_eok"].sum())
                actual = float(cand["actual_gva_eok"].sum())
                wape = err / actual * 100 if actual else np.nan
                p90 = float(cand["candidate_error_rate_pct"].quantile(0.9))
                summaries.append(
                    {
                        "parent_code": parent,
                        "k": k,
                        "alpha": alpha,
                        "external_regions": int(g["region_key"].nunique()),
                        "external_cells": int(len(g)),
                        "baseline_wape_pct": base_wape,
                        "candidate_wape_pct": wape,
                        "wape_reduction_pp": base_wape - wape,
                        "baseline_p90_error_pct": base_p90,
                        "candidate_p90_error_pct": p90,
                        "p90_delta_pp": p90 - base_p90,
                        "candidate_gt20_cells": int((cand["candidate_error_rate_pct"] > 20).sum()),
                    }
                )
                details.append(cand.assign(k=k, alpha=alpha))
    return pd.DataFrame(summaries), pd.concat(details, ignore_index=True) if details else pd.DataFrame()


def choose_params(screen: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for parent, g in screen.groupby("parent_code", sort=False):
        base = g[g["alpha"].eq(0.0)].sort_values("k").iloc[0]
        ok = g[
            (g["wape_reduction_pp"] >= MIN_EXTERNAL_REDUCTION_PP)
            & (g["p90_delta_pp"] <= MAX_EXTERNAL_P90_WORSEN_PP)
        ].copy()
        if ok.empty:
            row = base.copy()
            row["selected"] = False
            row["decision"] = "미채택: 유사 peer 외부 LOO 안정개선 미확인"
        else:
            row = ok.sort_values(["candidate_wape_pct", "candidate_gt20_cells", "k", "alpha"]).iloc[0].copy()
            row["selected"] = bool(row["alpha"] > 0)
            row["decision"] = "채택: 유사 peer 외부 LOO 개선"
        rows.append(row)
    return pd.DataFrame(rows)


def apply_to_target(target: pd.DataFrame, ext: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    param = selected.set_index("parent_code")[["k", "alpha", "decision"]].to_dict("index")
    parts = []
    for (city, parent), g in target.groupby(["city", "parent_code"], sort=False):
        tmp = g.copy()
        pg = ext[ext["parent_code"].eq(parent)].copy()
        p = param.get(parent, {"k": 1, "alpha": 0.0, "decision": "미채택: 외부 기준 없음"})
        alpha = float(p["alpha"])
        k = int(p["k"])
        divisions = sorted(set(pg["division_code"].astype(str)) | set(tmp["division_code"].astype(str)))
        baseline = vector_for(tmp, divisions, "baseline_share")
        if pg.empty or alpha <= 0:
            peers_with_dist = []
            prior = baseline
        else:
            peers_with_dist = nearest_regions(pg, tmp, divisions, k=k, exclude=None)
            peers = [x[0] for x in peers_with_dist]
            prior = prior_from_peers(pg, peers, divisions, baseline)
        cand_share = (1 - alpha) * baseline + alpha * prior
        cand_share = cand_share / cand_share.sum() if cand_share.sum() > 0 else baseline
        share_map = dict(zip(divisions, cand_share))
        tmp["phase162_k"] = k
        tmp["phase162_alpha"] = alpha
        tmp["phase162_parent_decision"] = str(p["decision"])
        tmp["phase162_peer_regions"] = ",".join([x[0] for x in peers_with_dist])
        tmp["phase162_peer_mean_l1_distance"] = float(np.mean([x[1] for x in peers_with_dist])) if peers_with_dist else np.nan
        tmp["phase162_share"] = tmp["division_code"].map(share_map).fillna(tmp["baseline_share"]).astype(float)
        # Re-normalize inside target's own middle universe.
        tmp["phase162_share"] = tmp["phase162_share"] / tmp["phase162_share"].sum()
        tmp["phase162_predicted_gva_eok"] = tmp["phase162_share"] * tmp["parent_actual_eok"]
        tmp["phase162_error_gva_eok"] = (tmp["phase162_predicted_gva_eok"] - tmp["actual_gva_eok"]).abs()
        tmp["phase162_error_rate_pct"] = tmp["phase162_error_gva_eok"] / tmp["actual_gva_eok"].replace(0, np.nan) * 100
        tmp["phase162_error_delta_vs_parent_controlled_eok"] = (
            tmp["phase162_error_gva_eok"] - tmp["parent_controlled_error_gva_eok"]
        )
        parts.append(tmp)
    return pd.concat(parts, ignore_index=True)


def summarize_city(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in detail.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        base = float(g["parent_controlled_error_gva_eok"].sum())
        err = float(g["phase162_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "parent_controlled_baseline_error_eok": base,
                "parent_controlled_baseline_wape_pct": base / actual * 100,
                "phase162_error_eok": err,
                "phase162_wape_pct": err / actual * 100,
                "reduction_eok": base - err,
                "reduction_pp": base / actual * 100 - err / actual * 100,
                "baseline_gt20_cells": int((g["parent_controlled_error_rate_pct"] > 20).sum()),
                "phase162_gt20_cells": int((g["phase162_error_rate_pct"] > 20).sum()),
                "worsened_cells": int((g["phase162_error_gva_eok"] > g["parent_controlled_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_parent(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (city, parent), g in detail.groupby(["city", "parent_code"], sort=False):
        actual = float(g["actual_gva_eok"].sum())
        base = float(g["parent_controlled_error_gva_eok"].sum())
        err = float(g["phase162_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "parent_code": parent,
                "cells": int(len(g)),
                "k": int(g["phase162_k"].iloc[0]),
                "alpha": float(g["phase162_alpha"].iloc[0]),
                "peer_regions": str(g["phase162_peer_regions"].iloc[0]),
                "peer_mean_l1_distance": float(g["phase162_peer_mean_l1_distance"].iloc[0]) if pd.notna(g["phase162_peer_mean_l1_distance"].iloc[0]) else np.nan,
                "decision": str(g["phase162_parent_decision"].iloc[0]),
                "actual_sum_eok": actual,
                "baseline_error_eok": base,
                "baseline_wape_pct": base / actual * 100 if actual else np.nan,
                "phase162_error_eok": err,
                "phase162_wape_pct": err / actual * 100 if actual else np.nan,
                "reduction_eok": base - err,
                "worsened_cells": int((g["phase162_error_gva_eok"] > g["parent_controlled_error_gva_eok"] + 1e-9).sum()),
                "phase162_gt20_cells": int((g["phase162_error_rate_pct"] > 20).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["city", "reduction_eok"], ascending=[True, False])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ext = load_external()
    target = load_target()
    screen, external_detail = screen_external(ext)
    selected = choose_params(screen)
    detail = apply_to_target(target, ext, selected)
    city = summarize_city(detail)
    parent = summarize_parent(detail)
    improved = detail[detail["phase162_error_delta_vs_parent_controlled_eok"].lt(-1e-9)].copy()
    worsened = detail[detail["phase162_error_delta_vs_parent_controlled_eok"].gt(1e-9)].copy()
    remaining = detail[detail["phase162_error_rate_pct"].gt(20)].copy()

    screen.to_csv(OUT / "phase162_external_similar_peer_screen.csv", index=False, encoding="utf-8-sig")
    external_detail.to_csv(OUT / "phase162_external_similar_peer_screen_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase162_selected_params.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase162_goyang_pohang_similar_peer_registry.csv", index=False, encoding="utf-8-sig")
    city.to_csv(OUT / "phase162_city_summary.csv", index=False, encoding="utf-8-sig")
    parent.to_csv(OUT / "phase162_parent_summary.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUT / "phase162_improved_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUT / "phase162_worsened_cells.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUT / "phase162_remaining_gt20_cells.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "phase": "phase162_similar_peer_prior_routing",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "inputs": {
                    "external_10": str(EXTERNAL.relative_to(ROOT)),
                    "goyang_pohang_base": str(BASE.relative_to(ROOT)),
                },
                "selection": {
                    "uses_goyang_pohang_actual": False,
                    "external_validation": "leave-one-external-sigungu-out nearest peer by predicted middle-share vector",
                    "alpha_grid": ALPHAS,
                    "k_values": K_VALUES,
                    "min_external_reduction_pp": MIN_EXTERNAL_REDUCTION_PP,
                    "max_external_p90_worsen_pp": MAX_EXTERNAL_P90_WORSEN_PP,
                    "comparison_baseline": "Phase124 shares normalized to parent actual total for structure-only validation",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    selected_view = selected[
        [
            "parent_code", "k", "alpha", "external_regions", "external_cells",
            "baseline_wape_pct", "candidate_wape_pct", "wape_reduction_pp",
            "p90_delta_pp", "decision",
        ]
    ].sort_values(["decision", "wape_reduction_pp"], ascending=[True, False])
    adopted_parent = parent[parent["alpha"].gt(0)].copy()
    top_improved = improved.sort_values("phase162_error_delta_vs_parent_controlled_eok").copy()
    top_worsened = worsened.sort_values("phase162_error_delta_vs_parent_controlled_eok", ascending=False).copy()

    REPORT.write_text(
        f"""# Phase162 유사 시군구 peer 기반 업종구조 라우팅

## 목적

Phase160의 단순 외부 평균 사전값은 일부 업종군을 개선했지만, 도시 특성이 맞지 않는 블록에서는 큰 악화를 만들었다. 이번 단계는 외부 10개 시군구 중에서 **사업체·종사자 기반 중분류 예측구조가 비슷한 지역**만 골라 사전값을 만든다.

고양·포항 actual은 모형 선택에 쓰지 않았다. 선택은 외부 10개 지역의 leave-one-region-out 검증으로만 수행했고, 고양·포항 actual은 마지막 평가표 작성에만 사용했다.

## 방법

1. 상위산업별로 중분류 예측비중 벡터를 만든다.
2. 외부 10개 지역에서 한 지역을 빼고, 나머지 중 예측비중 벡터가 가장 가까운 k개 지역을 찾는다.
3. 가까운 peer들의 실제 중분류 구조비 중앙값을 사전값으로 둔다.
4. 기존 예측비중과 peer 사전값을 alpha로 혼합한다.
5. 외부 LOO에서 WAPE가 1%p 이상 줄고 P90 오차가 3%p보다 많이 악화되지 않는 조합만 채택한다.

## 외부 LOO 선택 결과

{md_table(selected_view.rename(columns={
    'parent_code': '상위산업',
    'k': 'peer 수',
    'alpha': '혼합비',
    'external_regions': '외부지역',
    'external_cells': '외부셀',
    'baseline_wape_pct': '기준 외부 WAPE(%)',
    'candidate_wape_pct': '후보 외부 WAPE(%)',
    'wape_reduction_pp': '외부 감소 pp',
    'p90_delta_pp': 'P90 변화 pp',
    'decision': '판정',
}), 2)}

## 고양·포항 적용 결과

{md_table(city.rename(columns={
    'city': '지역',
    'actual_sum_eok': '실제합계(억원)',
    'parent_controlled_baseline_error_eok': '정규화 기준오차(억원)',
    'parent_controlled_baseline_wape_pct': '정규화 기준 WAPE(%)',
    'phase162_error_eok': 'Phase162 오차(억원)',
    'phase162_wape_pct': 'Phase162 WAPE(%)',
    'reduction_eok': '감소(억원)',
    'reduction_pp': '감소 pp',
    'baseline_gt20_cells': '기준 20%초과',
    'phase162_gt20_cells': 'Phase162 20%초과',
    'worsened_cells': '악화 셀',
}), 2)}

## 채택 상위산업별 효과

{md_table(adopted_parent.rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'cells': '중분류 수',
    'k': 'peer 수',
    'alpha': '혼합비',
    'peer_regions': '선택 peer',
    'peer_mean_l1_distance': 'peer거리',
    'decision': '판정',
    'actual_sum_eok': '실제합계(억원)',
    'baseline_error_eok': '기준오차(억원)',
    'baseline_wape_pct': '기준 WAPE(%)',
    'phase162_error_eok': '후보오차(억원)',
    'phase162_wape_pct': '후보 WAPE(%)',
    'reduction_eok': '감소(억원)',
    'worsened_cells': '악화 셀',
    'phase162_gt20_cells': '20%초과',
}), 2, 24)}

## 개선 셀 상위

{md_table(top_improved[[
    'city', 'parent_code', 'middle_code', 'middle_label', 'actual_gva_eok',
    'parent_controlled_error_gva_eok', 'phase162_error_gva_eok',
    'phase162_error_rate_pct', 'phase162_error_delta_vs_parent_controlled_eok',
    'phase162_peer_regions'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'middle_code': '코드',
    'middle_label': '중분류',
    'actual_gva_eok': '실제(억원)',
    'parent_controlled_error_gva_eok': '기준오차(억원)',
    'phase162_error_gva_eok': '후보오차(억원)',
    'phase162_error_rate_pct': '후보오차(%)',
    'phase162_error_delta_vs_parent_controlled_eok': '오차변화(억원)',
    'phase162_peer_regions': '선택 peer',
}), 2, 20)}

## 악화 셀 상위

{md_table(top_worsened[[
    'city', 'parent_code', 'middle_code', 'middle_label', 'actual_gva_eok',
    'parent_controlled_error_gva_eok', 'phase162_error_gva_eok',
    'phase162_error_rate_pct', 'phase162_error_delta_vs_parent_controlled_eok',
    'phase162_peer_regions'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'middle_code': '코드',
    'middle_label': '중분류',
    'actual_gva_eok': '실제(억원)',
    'parent_controlled_error_gva_eok': '기준오차(억원)',
    'phase162_error_gva_eok': '후보오차(억원)',
    'phase162_error_rate_pct': '후보오차(%)',
    'phase162_error_delta_vs_parent_controlled_eok': '오차변화(억원)',
    'phase162_peer_regions': '선택 peer',
}), 2, 20)}

## 남은 20% 초과 중분류

{md_table(remaining.sort_values(['city', 'phase162_error_gva_eok'], ascending=[True, False])[[
    'city', 'parent_code', 'middle_code', 'middle_label', 'actual_gva_eok',
    'phase162_predicted_gva_eok', 'phase162_error_gva_eok',
    'phase162_error_rate_pct', 'phase162_parent_decision'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'middle_code': '코드',
    'middle_label': '중분류',
    'actual_gva_eok': '실제(억원)',
    'phase162_predicted_gva_eok': '추정(억원)',
    'phase162_error_gva_eok': '오차(억원)',
    'phase162_error_rate_pct': '오차(%)',
    'phase162_parent_decision': '판정',
}), 2, 40)}

## 판정

1. 유사 peer 방식은 단순 외부 평균보다 원리적으로 안전하지만, 여전히 모든 블록에 바로 적용할 수 있는 운영 규칙은 아니다.
2. 성능 개선이 나는 블록과 악화 블록이 함께 존재하므로, 다음 단계는 `외부 LOO 안정성 + 대상도시 악화위험 예측`을 결합한 채택 게이트다.
3. 즉시 필요한 공개자료는 VWorld 공인중개사무소 전국자료다. 이 자료가 들어오면 부동산 682 서비스축도 같은 외부 peer 검증 구조에 넣을 수 있다.
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
