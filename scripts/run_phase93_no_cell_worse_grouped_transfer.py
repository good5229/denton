#!/usr/bin/env python3
"""Phase93: no-cell-worse grouped transfer screen for middle-industry GVA errors.

Phase90 identified all weak/worsened middle-industry cells and grouped them by
error mechanism.  Phase93 tests whether the over/under-estimation pattern
observed in the other city can improve each grouped queue.  The candidate is
not a direct fit to the target actual value:

* same-middle transfer: use the peer city's actual/predicted ratio for the same
  middle industry;
* cause-group median transfer: use the peer city's median actual/predicted
  ratio inside the same error-mechanism group;
* parent median transfer: use the peer city's median ratio inside the same
  parent industry.

Each candidate is applied to a whole city × cause-group at once, then parent
industry totals are re-normalised.  A candidate is adopted only if it reduces
the selected group's queue error, does not increase whole-city WAPE, and does
not worsen any middle-industry cell in the target city.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE88 = DATA / "phase88_current_industry_accuracy_registry"
PHASE90 = DATA / "phase90_grouped_weak_industry_queue"
OUTDIR = DATA / "phase93_no_cell_worse_grouped_transfer"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase93_no_cell_worse_grouped_transfer.md"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "pp")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            value = row.get(key, "")
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}" if abs(value) < 100 else f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def load_base() -> pd.DataFrame:
    reg = pd.read_csv(PHASE88 / "phase88_current_middle_industry_accuracy_registry.csv")
    cls = pd.read_csv(PHASE90 / "phase90_all_middle_industry_classified.csv")
    q = pd.read_csv(PHASE90 / "phase90_grouped_weak_industry_queue.csv")
    for df in (reg, cls, q):
        df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    meta = cls[["city", "parent_code", "middle_code", "cause_group_id", "cause_group", "group_action", "needed_signal"]]
    queue_key = q[["city", "parent_code", "middle_code", "queue_reason", "gap_to_10pct_eok"]].copy()
    df = reg.merge(meta, on=["city", "parent_code", "middle_code"], how="left")
    df = df.merge(queue_key, on=["city", "parent_code", "middle_code"], how="left")
    df["in_phase90_queue"] = df.queue_reason.notna()
    df["gap_to_10pct_eok"] = df.gap_to_10pct_eok.fillna((df.final_error_gva_eok - df.actual_gva_eok * 0.10).clip(lower=0))
    df["parent_total_actual_eok"] = df.groupby(["city", "parent_code"]).actual_gva_eok.transform("sum")
    df["base_share"] = df.final_predicted_gva_eok / df.groupby(["city", "parent_code"]).final_predicted_gva_eok.transform("sum")
    df["actual_share"] = df.actual_gva_eok / df.parent_total_actual_eok.replace(0, np.nan)
    df["base_ratio_actual_to_pred"] = df.actual_gva_eok / df.final_predicted_gva_eok.replace(0, np.nan)
    df["current_predicted_gva_eok"] = df.final_predicted_gva_eok
    df["current_model_note"] = df.final_option_family
    return df


def calculate_errors(df: pd.DataFrame, pred_col: str = "current_predicted_gva_eok") -> pd.DataFrame:
    out = df.copy()
    out["current_error_gva_eok"] = (out[pred_col] - out.actual_gva_eok).abs()
    out["current_error_rate_pct"] = out.current_error_gva_eok / out.actual_gva_eok.replace(0, np.nan) * 100
    out["current_gap_to_10pct_eok"] = (out.current_error_gva_eok - out.actual_gva_eok * 0.10).clip(lower=0)
    return out


def city_wape(df: pd.DataFrame) -> pd.Series:
    grouped = df.groupby("city")[["current_error_gva_eok", "actual_gva_eok"]].sum()
    return grouped.current_error_gva_eok / grouped.actual_gva_eok * 100


def queue_error(df: pd.DataFrame, city: str, group_id: str) -> float:
    m = df.city.eq(city) & df.cause_group_id.eq(group_id) & df.in_phase90_queue
    return float(df.loc[m, "current_error_gva_eok"].sum())


def queue_gap10(df: pd.DataFrame, city: str, group_id: str) -> float:
    m = df.city.eq(city) & df.cause_group_id.eq(group_id) & df.in_phase90_queue
    return float(df.loc[m, "current_gap_to_10pct_eok"].sum())


def city_within10(df: pd.DataFrame, city: str) -> int:
    return int((df.loc[df.city.eq(city), "current_error_rate_pct"] <= 10).sum())


def city_over20(df: pd.DataFrame, city: str) -> int:
    return int((df.loc[df.city.eq(city), "current_error_rate_pct"] > 20).sum())


def renormalise_parent(df: pd.DataFrame, pred_col: str) -> pd.Series:
    raw = df[pred_col].clip(lower=0)
    denom = raw.groupby([df.city, df.parent_code]).transform("sum")
    total = df.groupby(["city", "parent_code"]).actual_gva_eok.transform("sum")
    return raw / denom.replace(0, np.nan) * total


def peer_ratios(base: pd.DataFrame) -> pd.DataFrame:
    ratio = base[["city", "parent_code", "middle_code", "cause_group_id", "base_ratio_actual_to_pred"]].copy()
    ratio["base_ratio_actual_to_pred"] = ratio.base_ratio_actual_to_pred.replace([np.inf, -np.inf], np.nan).clip(0.05, 20.0)
    return ratio


def candidate_for_group(current: pd.DataFrame, city: str, group_id: str, candidate: str, lam: float) -> pd.DataFrame:
    cities = sorted(current.city.unique())
    peers = [c for c in cities if c != city]
    if not peers:
        return current.copy()
    peer = peers[0]
    ratios = peer_ratios(current)
    peer_same = ratios[ratios.city.eq(peer)][["parent_code", "middle_code", "base_ratio_actual_to_pred"]].rename(
        columns={"base_ratio_actual_to_pred": "same_middle_ratio"}
    )
    peer_cause = (
        ratios[ratios.city.eq(peer)]
        .groupby("cause_group_id", as_index=False)
        .base_ratio_actual_to_pred.median()
        .rename(columns={"base_ratio_actual_to_pred": "cause_group_ratio"})
    )
    peer_parent = (
        ratios[ratios.city.eq(peer)]
        .groupby("parent_code", as_index=False)
        .base_ratio_actual_to_pred.median()
        .rename(columns={"base_ratio_actual_to_pred": "parent_ratio"})
    )
    x = current.merge(peer_same, on=["parent_code", "middle_code"], how="left")
    x = x.merge(peer_cause, on="cause_group_id", how="left")
    x = x.merge(peer_parent, on="parent_code", how="left")
    target = x.city.eq(city) & x.cause_group_id.eq(group_id)
    if candidate == "same_middle_transfer":
        ratio = x.same_middle_ratio
    elif candidate == "cause_group_median_transfer":
        ratio = x.cause_group_ratio
    elif candidate == "parent_median_transfer":
        ratio = x.parent_ratio
    else:
        raise ValueError(candidate)
    ratio = ratio.fillna(1.0).clip(0.1, 10.0)
    x["candidate_raw_pred"] = x.current_predicted_gva_eok
    x.loc[target, "candidate_raw_pred"] = x.loc[target, "current_predicted_gva_eok"] * ((1 - lam) + lam * ratio.loc[target])
    x["candidate_predicted_gva_eok"] = renormalise_parent(x, "candidate_raw_pred")
    x["candidate_error_gva_eok"] = (x.candidate_predicted_gva_eok - x.actual_gva_eok).abs()
    x["candidate_error_rate_pct"] = x.candidate_error_gva_eok / x.actual_gva_eok.replace(0, np.nan) * 100
    return x


def screen_candidates(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    current = calculate_errors(base)
    decisions = []
    candidate_rows = []
    group_order = (
        current[current.in_phase90_queue]
        .groupby(["city", "cause_group_id", "cause_group"], as_index=False)
        .agg(base_group_error_eok=("current_error_gva_eok", "sum"), group_gap_to_10pct_eok=("current_gap_to_10pct_eok", "sum"))
        .sort_values("group_gap_to_10pct_eok", ascending=False)
    )
    for row in group_order.itertuples():
        city = row.city
        group_id = row.cause_group_id
        before_city_wape = float(city_wape(current).loc[city])
        before_group_error = queue_error(current, city, group_id)
        before_group_gap10 = queue_gap10(current, city, group_id)
        before_city_within10 = city_within10(current, city)
        before_city_over20 = city_over20(current, city)
        options = []
        for candidate in ("same_middle_transfer", "cause_group_median_transfer", "parent_median_transfer"):
            for lam in (0.25, 0.5, 0.75, 1.0):
                cand = candidate_for_group(current, city, group_id, candidate, lam)
                cand_city = cand[cand.city.eq(city)].copy()
                after_city_wape = cand_city.candidate_error_gva_eok.sum() / cand_city.actual_gva_eok.sum() * 100
                m = cand.city.eq(city) & cand.cause_group_id.eq(group_id) & cand.in_phase90_queue
                after_group_error = float(cand.loc[m, "candidate_error_gva_eok"].sum())
                after_group_gap10 = float((cand.loc[m, "candidate_error_gva_eok"] - cand.loc[m, "actual_gva_eok"] * 0.10).clip(lower=0).sum())
                impacted = cand[m].copy()
                worsened_cells = int((impacted.candidate_error_gva_eok > impacted.current_error_gva_eok + 1e-9).sum())
                worsened_city_cells = int((cand_city.candidate_error_gva_eok > cand_city.current_error_gva_eok + 1e-9).sum())
                after_city_within10 = int((cand_city.candidate_error_rate_pct <= 10).sum())
                after_city_over20 = int((cand_city.candidate_error_rate_pct > 20).sum())
                option = {
                    "city": city,
                    "cause_group_id": group_id,
                    "cause_group": row.cause_group,
                    "candidate": candidate,
                    "lambda": lam,
                    "before_city_wape_pct": before_city_wape,
                    "after_city_wape_pct": after_city_wape,
                    "city_wape_delta_pp": after_city_wape - before_city_wape,
                    "before_group_error_eok": before_group_error,
                    "after_group_error_eok": after_group_error,
                    "group_error_reduction_eok": before_group_error - after_group_error,
                    "group_error_reduction_pct": (before_group_error - after_group_error) / before_group_error * 100 if before_group_error else 0,
                    "before_group_gap10_eok": before_group_gap10,
                    "after_group_gap10_eok": after_group_gap10,
                    "group_gap10_reduction_eok": before_group_gap10 - after_group_gap10,
                    "before_city_within10_cells": before_city_within10,
                    "after_city_within10_cells": after_city_within10,
                    "city_within10_delta": after_city_within10 - before_city_within10,
                    "before_city_over20_cells": before_city_over20,
                    "after_city_over20_cells": after_city_over20,
                    "city_over20_delta": after_city_over20 - before_city_over20,
                    "worsened_queue_cells": worsened_cells,
                    "worsened_city_cells": worsened_city_cells,
                }
                options.append(option)
        opt = pd.DataFrame(options)
        candidate_rows.append(opt)
        viable = opt[
            (opt.group_error_reduction_eok > 1e-9)
            & (opt.group_gap10_reduction_eok >= -1e-9)
            & (opt.city_wape_delta_pp <= 1e-9)
            & (opt.city_within10_delta >= 0)
            & (opt.city_over20_delta <= 0)
            & (opt.worsened_city_cells == 0)
        ].copy()
        if viable.empty:
            decisions.append(
                {
                    "city": city,
                    "cause_group_id": group_id,
                    "cause_group": row.cause_group,
                    "decision": "retain_current",
                    "selected_candidate": "none",
                    "lambda": 0.0,
                    "before_city_wape_pct": before_city_wape,
                    "after_city_wape_pct": before_city_wape,
                    "before_group_error_eok": before_group_error,
                    "after_group_error_eok": before_group_error,
                    "group_error_reduction_eok": 0.0,
                    "before_group_gap10_eok": before_group_gap10,
                    "after_group_gap10_eok": before_group_gap10,
                    "group_gap10_reduction_eok": 0.0,
                    "reason": "WAPE·10%초과오차·10%이하 셀 수·개별 산업 비악화를 동시에 통과한 후보 없음",
                }
            )
            continue
        best = viable.sort_values(["group_gap10_reduction_eok", "group_error_reduction_eok", "city_wape_delta_pp"], ascending=[False, False, True]).iloc[0].to_dict()
        cand = candidate_for_group(current, city, group_id, best["candidate"], float(best["lambda"]))
        use_city = cand.city.eq(city)
        current.loc[use_city, "current_predicted_gva_eok"] = cand.loc[use_city, "candidate_predicted_gva_eok"].to_numpy()
        current = calculate_errors(current)
        current.loc[use_city & current.cause_group_id.eq(group_id), "current_model_note"] = f"{best['candidate']} λ={best['lambda']}"
        decisions.append(
            {
                "city": city,
                "cause_group_id": group_id,
                "cause_group": row.cause_group,
                "decision": "adopt",
                "selected_candidate": best["candidate"],
                "lambda": best["lambda"],
                "before_city_wape_pct": before_city_wape,
                "after_city_wape_pct": float(city_wape(current).loc[city]),
                "before_group_error_eok": before_group_error,
                "after_group_error_eok": queue_error(current, city, group_id),
                "group_error_reduction_eok": before_group_error - queue_error(current, city, group_id),
                "before_group_gap10_eok": before_group_gap10,
                "after_group_gap10_eok": queue_gap10(current, city, group_id),
                "group_gap10_reduction_eok": before_group_gap10 - queue_gap10(current, city, group_id),
                "reason": "그룹 큐오차·10%초과오차 감소, 도시 전체 지표 비악화, 개별 산업 악화 0건",
            }
        )
    return current, pd.DataFrame(decisions), pd.concat(candidate_rows, ignore_index=True)


def summarize(df: pd.DataFrame, label: str, pred_col: str, error_col: str, rate_col: str) -> pd.DataFrame:
    out = (
        df.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "size"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=(error_col, "sum"),
            median_error_pct=(rate_col, "median"),
            within_10pct_cells=(rate_col, lambda s: int((s <= 10).sum())),
            over_20pct_cells=(rate_col, lambda s: int((s > 20).sum())),
            over_50pct_cells=(rate_col, lambda s: int((s > 50).sum())),
        )
    )
    out["wape_pct"] = out.error_sum_eok / out.actual_sum_eok * 100
    out["stage"] = label
    return out


def queue_summary(df: pd.DataFrame) -> pd.DataFrame:
    q = df[df.in_phase90_queue].copy()
    out = (
        q.groupby("city", as_index=False)
        .agg(
            queue_cells=("middle_code", "size"),
            queue_actual_sum_eok=("actual_gva_eok", "sum"),
            queue_error_sum_eok=("current_error_gva_eok", "sum"),
            queue_gap_to_10pct_eok=("current_gap_to_10pct_eok", "sum"),
            queue_within_10pct_cells=("current_error_rate_pct", lambda s: int((s <= 10).sum())),
        )
    )
    out["queue_wape_pct"] = out.queue_error_sum_eok / out.queue_actual_sum_eok * 100
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = calculate_errors(load_base(), "current_predicted_gva_eok")
    final, decisions, candidates = screen_candidates(load_base())
    baseline_summary = summarize(base, "Phase88 current", "current_predicted_gva_eok", "current_error_gva_eok", "current_error_rate_pct")
    final_summary = summarize(final, "Phase91 grouped transfer", "current_predicted_gva_eok", "current_error_gva_eok", "current_error_rate_pct")
    summary = pd.concat([baseline_summary, final_summary], ignore_index=True)
    wide = baseline_summary[["city", "error_sum_eok", "wape_pct", "within_10pct_cells", "over_20pct_cells", "over_50pct_cells"]].merge(
        final_summary[["city", "error_sum_eok", "wape_pct", "within_10pct_cells", "over_20pct_cells", "over_50pct_cells"]],
        on="city",
        suffixes=("_baseline", "_phase91"),
    )
    wide["error_reduction_eok"] = wide.error_sum_eok_baseline - wide.error_sum_eok_phase91
    wide["wape_improvement_pp"] = wide.wape_pct_baseline - wide.wape_pct_phase91
    qbase = queue_summary(base).rename(columns={c: f"{c}_baseline" for c in queue_summary(base).columns if c != "city"})
    qfinal = queue_summary(final).rename(columns={c: f"{c}_phase91" for c in queue_summary(final).columns if c != "city"})
    qwide = qbase.merge(qfinal, on="city")
    qwide["queue_error_reduction_eok"] = qwide.queue_error_sum_eok_baseline - qwide.queue_error_sum_eok_phase91
    qwide["queue_gap10_reduction_eok"] = qwide.queue_gap_to_10pct_eok_baseline - qwide.queue_gap_to_10pct_eok_phase91

    final.to_csv(OUTDIR / "phase93_grouped_transfer_final_detail.csv", index=False, encoding="utf-8-sig")
    decisions.to_csv(OUTDIR / "phase93_group_decisions.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(OUTDIR / "phase93_candidate_screen.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase93_summary_by_city.csv", index=False, encoding="utf-8-sig")
    qwide.to_csv(OUTDIR / "phase93_queue_improvement_summary.csv", index=False, encoding="utf-8-sig")

    adopted = decisions[decisions.decision.eq("adopt")].sort_values("group_error_reduction_eok", ascending=False)
    remaining = final[final.in_phase90_queue & (final.current_error_rate_pct > 10)].sort_values("current_error_gva_eok", ascending=False)
    report = f"""# 개별 산업 악화 금지 원인군 전이 실험

## 목적

Phase90의 취약 중분류 큐를 단일 산업별로 손보지 않고, 도시×원인군 단위로 한꺼번에 개선할 수 있는지 검증했다. Phase91보다 더 엄격하게, 도시 전체 WAPE와 10% 목표 초과오차뿐 아니라 **개별 중분류 오차가 하나라도 악화되면 후보를 탈락**시켰다.

## 전체 성능 변화

{md_table(wide, [("city", "지역"), ("error_sum_eok_baseline", "기준 오차 억원"), ("error_sum_eok_phase91", "Phase93 오차 억원"), ("error_reduction_eok", "감소 억원"), ("wape_pct_baseline", "기준 WAPE %"), ("wape_pct_phase91", "Phase93 WAPE %"), ("wape_improvement_pp", "개선 pp"), ("within_10pct_cells_baseline", "기준 10%이하"), ("within_10pct_cells_phase91", "Phase93 10%이하"), ("over_20pct_cells_baseline", "기준 20%초과"), ("over_20pct_cells_phase91", "Phase93 20%초과")])}

## Phase90 큐 개선

{md_table(qwide, [("city", "지역"), ("queue_cells_baseline", "큐 셀 개수"), ("queue_error_sum_eok_baseline", "기준 큐오차 억원"), ("queue_error_sum_eok_phase91", "Phase93 큐오차 억원"), ("queue_error_reduction_eok", "큐오차 감소 억원"), ("queue_gap_to_10pct_eok_baseline", "기준 10%초과 억원"), ("queue_gap_to_10pct_eok_phase91", "Phase93 10%초과 억원"), ("queue_gap10_reduction_eok", "10%초과 감소 억원"), ("queue_within_10pct_cells_baseline", "기준 10%이하"), ("queue_within_10pct_cells_phase91", "Phase93 10%이하")])}

## 채택된 원인군 후보

{md_table(adopted, [("city", "지역"), ("cause_group", "원인군"), ("selected_candidate", "선택 후보"), ("lambda", "강도"), ("before_city_wape_pct", "전 도시WAPE %"), ("after_city_wape_pct", "후 도시WAPE %"), ("before_group_error_eok", "전 그룹오차 억원"), ("after_group_error_eok", "후 그룹오차 억원"), ("group_error_reduction_eok", "오차감소 억원"), ("before_group_gap10_eok", "전 10%초과 억원"), ("after_group_gap10_eok", "후 10%초과 억원"), ("group_gap10_reduction_eok", "10%초과 감소 억원"), ("reason", "판정")], 30)}

## 미채택 원인군

{md_table(decisions[decisions.decision.ne("adopt")], [("city", "지역"), ("cause_group", "원인군"), ("before_city_wape_pct", "도시WAPE %"), ("before_group_error_eok", "그룹오차 억원"), ("reason", "미채택 사유")], 30)}

## 여전히 10% 초과인 큐 셀

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("cause_group", "원인군"), ("actual_gva_eok", "실제 억원"), ("current_predicted_gva_eok", "추정 억원"), ("current_error_gva_eok", "오차 억원"), ("current_error_rate_pct", "오차 %"), ("current_gap_to_10pct_eok", "10%초과 억원"), ("current_model_note", "적용 기준")], 50)}

## 판정

1. 교차도시 전이는 전 산업에 무차별 적용하지 않고, 도시×원인군 단위로 검증 통과한 후보만 채택했다.
2. 도시 전체 WAPE, 10% 목표 초과오차, 10% 이하 셀 수, 20% 초과 셀 수, 개별 중분류 악화 0건을 모두 통과해야 채택했다.
3. 이번 방식으로 줄지 않는 원인군은 교차도시 패턴만으로는 부족하므로, Phase89에서 정리한 직접 활동자료를 붙이는 다음 실험 대상으로 남긴다.
4. 다음 라운드의 목표는 남은 큐 셀의 `10% 초과오차`를 줄이는 것이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase93_grouped_transfer_final_detail.csv")


if __name__ == "__main__":
    main()
