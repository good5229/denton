#!/usr/bin/env python3
"""Phase160: external-10 peer-prior routing for Goyang/Pohang middle GVA.

The central problem after Phase124 is not lack of accounting controls; it is
middle-industry structure.  This experiment learns a conservative
industry-structure prior from the external 10-sigungu validation sample only,
then applies it to Goyang/Pohang.  Goyang/Pohang actuals are used only for final
evaluation, not for choosing alpha.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase160_external_peer_prior_routing"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase160_external_peer_prior_routing.md"

EXTERNAL = DATA / "phase108_collected_10_sigungu_generalization" / "phase108_collected_10_sigungu_middle_accuracy_detail.csv"
BASE = DATA / "phase124_pps_subblock_no_worse" / "phase124_registry.csv"

ALPHAS = [0.0, 0.10, 0.20, 0.35, 0.50, 0.65, 0.80]
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


def normalize_parent_shares(df: pd.DataFrame, share_col: str, out_col: str) -> pd.DataFrame:
    out = df.copy()
    total = out.groupby(["region_key", "parent_code"])[share_col].transform("sum")
    n = out.groupby(["region_key", "parent_code"])[share_col].transform("size")
    out[out_col] = np.where(total > 0, out[share_col] / total, 1.0 / n)
    return out


def load_external() -> pd.DataFrame:
    df = pd.read_csv(EXTERNAL)
    df = df[df["split_evaluable"].astype(bool)].copy()
    df["division_code"] = df["division_code"].astype(str).str.zfill(2)
    df["region_key"] = df["source_region"].astype(str) + "|" + df["sigungu_name"].astype(str)
    for c in ["actual_share", "predicted_share", "parent_gva_eok", "actual_gva_eok"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return normalize_parent_shares(df, "predicted_share", "baseline_share")


def peer_template_for_group(g: pd.DataFrame, holdout_region: str | None) -> pd.Series:
    train = g if holdout_region is None else g[g["region_key"].ne(holdout_region)]
    med = train.groupby("division_code")["actual_share"].median()
    return med


def evaluate_group_alpha(g: pd.DataFrame, alpha: float) -> pd.DataFrame:
    parts = []
    for region, rg in g.groupby("region_key", sort=False):
        peer = peer_template_for_group(g, region)
        tmp = rg.copy()
        tmp["peer_share_raw"] = tmp["division_code"].map(peer)
        fallback = 1.0 / len(tmp) if len(tmp) else 0.0
        tmp["peer_share_raw"] = tmp["peer_share_raw"].fillna(fallback)
        # Keep the peer prior inside the evaluated middle universe.
        psum = tmp["peer_share_raw"].sum()
        tmp["peer_share"] = tmp["peer_share_raw"] / psum if psum > 0 else fallback
        tmp["candidate_share_raw"] = (1 - alpha) * tmp["baseline_share"] + alpha * tmp["peer_share"]
        csum = tmp["candidate_share_raw"].sum()
        tmp["candidate_share"] = tmp["candidate_share_raw"] / csum if csum > 0 else fallback
        tmp["candidate_gva_eok"] = tmp["candidate_share"] * tmp["parent_gva_eok"]
        tmp["candidate_error_eok"] = (tmp["candidate_gva_eok"] - tmp["actual_gva_eok"]).abs()
        tmp["candidate_error_rate_pct"] = tmp["candidate_error_eok"] / tmp["actual_gva_eok"].replace(0, np.nan) * 100
        parts.append(tmp)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def external_alpha_screen(ext: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    details = []
    summaries = []
    for parent, g in ext.groupby("parent_code", sort=False):
        if g["region_key"].nunique() < 3 or g["division_code"].nunique() < 2:
            continue
        base_error = float((g["baseline_share"] * g["parent_gva_eok"] - g["actual_gva_eok"]).abs().sum())
        base_actual = float(g["actual_gva_eok"].sum())
        base_wape = base_error / base_actual * 100 if base_actual else np.nan
        base_p90 = float(g["error_rate_pct"].quantile(0.9))
        for alpha in ALPHAS:
            cand = evaluate_group_alpha(g, alpha)
            err = float(cand["candidate_error_eok"].sum())
            actual = float(cand["actual_gva_eok"].sum())
            wape = err / actual * 100 if actual else np.nan
            p90 = float(cand["candidate_error_rate_pct"].quantile(0.9))
            gt20 = int((cand["candidate_error_rate_pct"] > 20).sum())
            details.append(cand.assign(alpha=alpha))
            summaries.append(
                {
                    "parent_code": parent,
                    "alpha": alpha,
                    "external_regions": int(g["region_key"].nunique()),
                    "external_cells": int(len(g)),
                    "external_actual_eok": actual,
                    "baseline_wape_pct": base_wape,
                    "candidate_wape_pct": wape,
                    "wape_reduction_pp": base_wape - wape,
                    "baseline_p90_error_pct": base_p90,
                    "candidate_p90_error_pct": p90,
                    "p90_delta_pp": p90 - base_p90,
                    "candidate_gt20_cells": gt20,
                }
            )
    summary = pd.DataFrame(summaries)
    detail = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    return summary, detail


def choose_alphas(summary: pd.DataFrame) -> pd.DataFrame:
    chosen = []
    for parent, g in summary.groupby("parent_code", sort=False):
        g = g.sort_values(["candidate_wape_pct", "alpha"]).copy()
        baseline = g[g["alpha"].eq(0.0)].iloc[0]
        ok = g[
            (g["wape_reduction_pp"] >= MIN_EXTERNAL_REDUCTION_PP)
            & (g["p90_delta_pp"] <= MAX_EXTERNAL_P90_WORSEN_PP)
        ].copy()
        if ok.empty:
            row = baseline.copy()
            row["selected"] = False
            row["decision"] = "미채택: 외부 10개에서 안정 개선 미확인"
        else:
            row = ok.sort_values(["candidate_wape_pct", "alpha"]).iloc[0].copy()
            row["selected"] = row["alpha"] > 0
            row["decision"] = "채택: 외부 10개 LOO 개선"
        chosen.append(row)
    return pd.DataFrame(chosen)


def apply_to_goyang_pohang(base: pd.DataFrame, ext: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    df = base.copy()
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["division_code"] = df["middle_code"]
    df["region_key"] = df["city"]
    for c in ["actual_gva_eok", "phase124_predicted_gva_eok"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["parent_actual_eok"] = df.groupby(["city", "parent_code"])["actual_gva_eok"].transform("sum")
    df["phase124_parent_predicted_sum_eok"] = df.groupby(["city", "parent_code"])["phase124_predicted_gva_eok"].transform("sum")
    df["phase124_share_raw"] = df["phase124_predicted_gva_eok"] / df["phase124_parent_predicted_sum_eok"].replace(0, np.nan)
    df = normalize_parent_shares(df, "phase124_share_raw", "phase124_share")
    df["phase124_parent_controlled_predicted_gva_eok"] = df["phase124_share"] * df["parent_actual_eok"]
    df["phase124_parent_controlled_error_gva_eok"] = (
        df["phase124_parent_controlled_predicted_gva_eok"] - df["actual_gva_eok"]
    ).abs()
    df["phase124_parent_controlled_error_rate_pct"] = (
        df["phase124_parent_controlled_error_gva_eok"] / df["actual_gva_eok"].replace(0, np.nan) * 100
    )

    selected_alpha = selected.set_index("parent_code")["alpha"].to_dict()
    selected_decision = selected.set_index("parent_code")["decision"].to_dict()
    out_parts = []
    for (city, parent), g in df.groupby(["city", "parent_code"], sort=False):
        alpha = float(selected_alpha.get(parent, 0.0))
        peer = peer_template_for_group(ext[ext["parent_code"].eq(parent)], holdout_region=None)
        tmp = g.copy()
        tmp["phase160_alpha"] = alpha
        tmp["phase160_parent_decision"] = selected_decision.get(parent, "미채택: 외부 기준 없음")
        tmp["phase160_peer_share_raw"] = tmp["division_code"].map(peer)
        fallback = 1.0 / len(tmp) if len(tmp) else 0.0
        tmp["phase160_peer_share_raw"] = tmp["phase160_peer_share_raw"].fillna(fallback)
        psum = tmp["phase160_peer_share_raw"].sum()
        tmp["phase160_peer_share"] = tmp["phase160_peer_share_raw"] / psum if psum > 0 else fallback
        tmp["phase160_share_raw"] = (1 - alpha) * tmp["phase124_share"] + alpha * tmp["phase160_peer_share"]
        ssum = tmp["phase160_share_raw"].sum()
        tmp["phase160_share"] = tmp["phase160_share_raw"] / ssum if ssum > 0 else fallback
        tmp["phase160_predicted_gva_eok"] = tmp["phase160_share"] * tmp["parent_actual_eok"]
        tmp["phase160_error_gva_eok"] = (tmp["phase160_predicted_gva_eok"] - tmp["actual_gva_eok"]).abs()
        tmp["phase160_error_rate_pct"] = tmp["phase160_error_gva_eok"] / tmp["actual_gva_eok"].replace(0, np.nan) * 100
        tmp["phase160_error_delta_vs_phase124_parent_controlled_eok"] = (
            tmp["phase160_error_gva_eok"] - tmp["phase124_parent_controlled_error_gva_eok"]
        )
        tmp["phase160_error_delta_vs_phase124_raw_eok"] = tmp["phase160_error_gva_eok"] - tmp["phase124_error_gva_eok"]
        out_parts.append(tmp)
    return pd.concat(out_parts, ignore_index=True)


def city_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, g in detail.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        e124_raw = float(g["phase124_error_gva_eok"].sum())
        e124 = float(g["phase124_parent_controlled_error_gva_eok"].sum())
        e160 = float(g["phase160_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "phase124_raw_error_eok": e124_raw,
                "phase124_raw_wape_pct": e124_raw / actual * 100,
                "phase124_parent_controlled_error_eok": e124,
                "phase124_parent_controlled_wape_pct": e124 / actual * 100,
                "phase160_error_eok": e160,
                "phase160_wape_pct": e160 / actual * 100,
                "error_reduction_eok": e124 - e160,
                "wape_reduction_pp": e124 / actual * 100 - e160 / actual * 100,
                "phase124_raw_gt20_cells": int((g["phase124_error_rate_pct"] > 20).sum()),
                "phase124_parent_controlled_gt20_cells": int((g["phase124_parent_controlled_error_rate_pct"] > 20).sum()),
                "phase160_gt20_cells": int((g["phase160_error_rate_pct"] > 20).sum()),
                "worsened_cells": int(
                    (g["phase160_error_gva_eok"] > g["phase124_parent_controlled_error_gva_eok"] + 1e-9).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def parent_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (city, parent), g in detail.groupby(["city", "parent_code"], sort=False):
        actual = float(g["actual_gva_eok"].sum())
        e124_raw = float(g["phase124_error_gva_eok"].sum())
        e124 = float(g["phase124_parent_controlled_error_gva_eok"].sum())
        e160 = float(g["phase160_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "parent_code": parent,
                "cells": int(len(g)),
                "alpha": float(g["phase160_alpha"].iloc[0]),
                "decision": str(g["phase160_parent_decision"].iloc[0]),
                "actual_sum_eok": actual,
                "phase124_raw_error_eok": e124_raw,
                "phase124_raw_wape_pct": e124_raw / actual * 100 if actual else np.nan,
                "phase124_parent_controlled_error_eok": e124,
                "phase124_parent_controlled_wape_pct": e124 / actual * 100 if actual else np.nan,
                "phase160_error_eok": e160,
                "phase160_wape_pct": e160 / actual * 100 if actual else np.nan,
                "error_reduction_eok": e124 - e160,
                "worsened_cells": int(
                    (g["phase160_error_gva_eok"] > g["phase124_parent_controlled_error_gva_eok"] + 1e-9).sum()
                ),
                "phase160_gt20_cells": int((g["phase160_error_rate_pct"] > 20).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["city", "error_reduction_eok"], ascending=[True, False])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ext = load_external()
    base = pd.read_csv(BASE)
    screen, external_detail = external_alpha_screen(ext)
    selected = choose_alphas(screen)
    detail = apply_to_goyang_pohang(base, ext, selected)
    csum = city_summary(detail)
    psum = parent_summary(detail)
    improved = detail[detail["phase160_error_delta_vs_phase124_parent_controlled_eok"].lt(-1e-9)].copy()
    worsened = detail[detail["phase160_error_delta_vs_phase124_parent_controlled_eok"].gt(1e-9)].copy()
    remaining_gt20 = detail[detail["phase160_error_rate_pct"].gt(20)].copy()

    screen.to_csv(OUT / "phase160_external_alpha_screen.csv", index=False, encoding="utf-8-sig")
    external_detail.to_csv(OUT / "phase160_external_alpha_screen_detail.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase160_selected_parent_alphas.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase160_goyang_pohang_peer_prior_registry.csv", index=False, encoding="utf-8-sig")
    csum.to_csv(OUT / "phase160_city_summary.csv", index=False, encoding="utf-8-sig")
    psum.to_csv(OUT / "phase160_parent_summary.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUT / "phase160_improved_cells.csv", index=False, encoding="utf-8-sig")
    worsened.to_csv(OUT / "phase160_worsened_cells.csv", index=False, encoding="utf-8-sig")
    remaining_gt20.to_csv(OUT / "phase160_remaining_gt20_cells.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "phase": "phase160_external_peer_prior_routing",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "external_10_middle_actual": str(EXTERNAL.relative_to(ROOT)),
            "goyang_pohang_base_registry": str(BASE.relative_to(ROOT)),
        },
            "selection_rule": {
            "alpha_grid": ALPHAS,
            "selection_data": "external 10 sigungu only, leave-one-region-out by parent_code",
            "min_external_reduction_pp": MIN_EXTERNAL_REDUCTION_PP,
            "max_external_p90_worsen_pp": MAX_EXTERNAL_P90_WORSEN_PP,
            "goyang_pohang_actual_used_for_selection": False,
            "comparison_baseline": "Phase124 middle shares re-normalized to the same parent actual total. Raw Phase124 error is kept separately and is not mixed with peer-prior effects.",
        },
        "outputs": [str(p.relative_to(ROOT)) for p in sorted(OUT.glob("*.csv"))],
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    selected_view = selected[
        [
            "parent_code",
            "alpha",
            "external_regions",
            "external_cells",
            "baseline_wape_pct",
            "candidate_wape_pct",
            "wape_reduction_pp",
            "p90_delta_pp",
            "decision",
        ]
    ].sort_values(["decision", "wape_reduction_pp"], ascending=[True, False])
    pview = psum[psum["alpha"].gt(0)].copy()
    top_improved = improved.sort_values("phase160_error_delta_vs_phase124_parent_controlled_eok").copy()
    top_worsened = worsened.sort_values("phase160_error_delta_vs_phase124_parent_controlled_eok", ascending=False).copy()

    REPORT.write_text(
        f"""# Phase160 외부 10개 시군구 기반 업종구조 사전값 라우팅

## 목적

Phase124 이후에도 고양·포항의 20% 초과 중분류가 많이 남았다. 이번 단계는 고양·포항 실제값으로 계수를 맞추지 않고, Phase108의 외부 10개 시군구 중분류 실제 구조비만 사용해 상위산업별 `업종구조 사전값`을 만든 뒤 고양·포항에 적용한다.

핵심은 **외부 표본으로만 alpha를 고르는 것**이다. 고양·포항 actual은 마지막 평가표 작성에만 사용했다.

주의: 이번 후보는 중분류 배분 검증이므로 같은 상위산업 안에서 합이 상위산업 actual과 일치하도록 정규화한다. 따라서 아래 비교는 `원 Phase124 금액오차`가 아니라 **상위산업 총량을 같게 둔 Phase124 구조비 오차**와 비교한다. 상위총량 정규화로 줄어드는 부분은 새 자료 성능으로 해석하지 않는다.

## 방법

1. 외부 10개 시군구에서 같은 상위산업 안의 중분류별 실제 구조비 중앙값을 계산한다.
2. 각 외부 지역을 하나씩 빼는 leave-one-region-out 방식으로 `기존 활동비중`과 `외부 업종구조 사전값`을 혼합한다.
3. alpha는 `{ALPHAS}` 중에서 고른다.
4. 외부 WAPE가 1%p 이상 줄고 P90 오차가 3%p보다 많이 악화되지 않는 상위산업만 채택한다.
5. 선택된 alpha를 고양·포항에 고정 적용한다.

## 외부 10개 기준 alpha 선택

{md_table(selected_view.rename(columns={
    'parent_code': '상위산업',
    'alpha': '혼합비',
    'external_regions': '외부지역',
    'external_cells': '외부셀',
    'baseline_wape_pct': '기존 외부 WAPE(%)',
    'candidate_wape_pct': '후보 외부 WAPE(%)',
    'wape_reduction_pp': '외부 감소 pp',
    'p90_delta_pp': 'P90 변화 pp',
    'decision': '판정',
}), 2)}

## 고양·포항 적용 결과

{md_table(csum.rename(columns={
    'city': '지역',
    'actual_sum_eok': '실제합계(억원)',
    'phase124_raw_error_eok': '원 Phase124 오차(억원)',
    'phase124_raw_wape_pct': '원 Phase124 WAPE(%)',
    'phase124_parent_controlled_error_eok': '상위총량 정규화 기준오차(억원)',
    'phase124_parent_controlled_wape_pct': '상위총량 정규화 기준 WAPE(%)',
    'phase160_error_eok': 'Phase160 오차(억원)',
    'phase160_wape_pct': 'Phase160 WAPE(%)',
    'error_reduction_eok': '감소(억원)',
    'wape_reduction_pp': '감소 pp',
    'phase124_raw_gt20_cells': '원 20%초과',
    'phase124_parent_controlled_gt20_cells': '정규화 기준 20%초과',
    'phase160_gt20_cells': 'Phase160 20%초과',
    'worsened_cells': '악화 셀',
}), 2)}

## 채택 상위산업별 효과

{md_table(pview.rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'cells': '중분류 수',
    'alpha': '혼합비',
    'decision': '판정',
    'actual_sum_eok': '실제합계(억원)',
    'phase124_raw_error_eok': '원오차(억원)',
    'phase124_raw_wape_pct': '원 WAPE(%)',
    'phase124_parent_controlled_error_eok': '정규화 기준오차(억원)',
    'phase124_parent_controlled_wape_pct': '정규화 기준 WAPE(%)',
    'phase160_error_eok': '후보오차(억원)',
    'phase160_wape_pct': '후보 WAPE(%)',
    'error_reduction_eok': '감소(억원)',
    'worsened_cells': '악화 셀',
    'phase160_gt20_cells': '20%초과',
}), 2, 20)}

## 개선 셀 상위

{md_table(top_improved[[
    'city', 'parent_code', 'middle_code', 'middle_label', 'actual_gva_eok',
    'phase124_parent_controlled_error_gva_eok', 'phase160_error_gva_eok', 'phase160_error_rate_pct',
    'phase160_error_delta_vs_phase124_parent_controlled_eok', 'phase160_alpha'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'middle_code': '코드',
    'middle_label': '중분류',
    'actual_gva_eok': '실제(억원)',
    'phase124_parent_controlled_error_gva_eok': '정규화 기준오차(억원)',
    'phase160_error_gva_eok': '후보오차(억원)',
    'phase160_error_rate_pct': '후보오차(%)',
    'phase160_error_delta_vs_phase124_parent_controlled_eok': '오차변화(억원)',
    'phase160_alpha': '혼합비',
}), 2, 20)}

## 악화 셀 상위

{md_table(top_worsened[[
    'city', 'parent_code', 'middle_code', 'middle_label', 'actual_gva_eok',
    'phase124_parent_controlled_error_gva_eok', 'phase160_error_gva_eok', 'phase160_error_rate_pct',
    'phase160_error_delta_vs_phase124_parent_controlled_eok', 'phase160_alpha'
]].rename(columns={
    'city': '지역',
    'parent_code': '상위산업',
    'middle_code': '코드',
    'middle_label': '중분류',
    'actual_gva_eok': '실제(억원)',
    'phase124_parent_controlled_error_gva_eok': '정규화 기준오차(억원)',
    'phase160_error_gva_eok': '후보오차(억원)',
    'phase160_error_rate_pct': '후보오차(%)',
    'phase160_error_delta_vs_phase124_parent_controlled_eok': '오차변화(억원)',
    'phase160_alpha': '혼합비',
}), 2, 20)}

## 판정

1. 이 실험은 고양·포항 actual로 계수를 맞춘 것이 아니라 외부 10개 시군구에서 선택한 사전값 라우팅이다.
2. 따라서 Phase154/155의 부동산 2도시 미세탐색보다 일반화 위험이 낮다.
3. 다만 외부 10개 표본의 중분류 실제 구조비가 2015 경제총조사 기반이므로, 최신 산업구조 변화가 큰 도시에는 낡은 사전값이 오히려 일부 셀을 악화시킬 수 있다.
4. 운영 채택은 도시별 총오차 감소만으로 하지 말고, `악화 셀`과 금액상위 악화 업종을 함께 제한해야 한다.
5. 다음 단계는 이 라우팅을 포스터용 성능 숫자로 바로 쓰는 것이 아니라, 고양·포항에서 악화되는 상위산업을 제외한 `무악화 부분채택안`으로 다시 걸러내는 것이다.
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
