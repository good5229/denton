#!/usr/bin/env python3
"""Phase96: protected weak-queue selection for middle-industry GVA gaps.

Phase95 is the strictest public claim: no individual middle industry may get
worse.  It is safe but conservative.  This phase tests an operational rule for
reducing the remaining weak queue:

* use the same parent-balanced candidate pool as Phase95;
* require parent error and weak-queue error to decrease;
* prohibit grade-boundary deterioration: a cell that was <=10%, <=20%, or <=50%
  cannot move beyond that boundary;
* keep all city × parent totals intact.

This does not replace the strict registry; it identifies where a practical
weak-industry improvement rule can reduce gaps without damaging the visible
accuracy classes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE95 = DATA / "phase95_composite_activity_indicator_screen"
OUTDIR = DATA / "phase96_protected_weak_queue_selection"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase96_protected_weak_queue_selection.md"


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


def grade(rate: float) -> str:
    if pd.isna(rate):
        return "미검증"
    if rate <= 5:
        return "매우 양호(5% 이하)"
    if rate <= 10:
        return "양호(5~10%)"
    if rate <= 20:
        return "주의(10~20%)"
    if rate <= 50:
        return "취약(20~50%)"
    return "고취약(50% 초과)"


def load_options() -> pd.DataFrame:
    x = pd.read_csv(PHASE95 / "phase95_composite_activity_options.csv")
    x["middle_code"] = x.middle_code.astype(str).str.zfill(2)
    x["is_queue"] = x.phase92_queue.ne("현행유지가능")
    x["ref_error_rate_pct"] = x.reference_error_gva_eok / x.actual_gva_eok.replace(0, np.nan) * 100
    return x


def grade_boundary_worse(x: pd.DataFrame) -> pd.Series:
    ref = x.ref_error_rate_pct
    cand = x.error_rate_pct
    return (
        (ref.le(10) & cand.gt(10 + 1e-9))
        | (ref.le(20) & cand.gt(20 + 1e-9))
        | (ref.le(50) & cand.gt(50 + 1e-9))
    )


def select(options: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    selected = []
    ref_name = "Phase92 현재 기준"
    for (city, parent_code), g in options.groupby(["city", "parent_code"], sort=False):
        g = g.copy()
        g["grade_boundary_worse"] = grade_boundary_worse(g)
        g["error_delta_eok"] = g.error_gva_eok - g.reference_error_gva_eok
        score = (
            g.groupby(["option_name", "option_family"], as_index=False)
            .agg(
                parent_actual_eok=("actual_gva_eok", "sum"),
                parent_error_eok=("error_gva_eok", "sum"),
                reference_parent_error_eok=("reference_error_gva_eok", "sum"),
                queue_error_eok=("error_gva_eok", lambda s: 0),
                reference_queue_error_eok=("reference_error_gva_eok", lambda s: 0),
                queue_gap10_eok=("gap_to_10pct_eok", lambda s: 0),
                reference_queue_gap10_eok=("reference_gap_to_10pct_eok", lambda s: 0),
                grade_boundary_worse_cells=("grade_boundary_worse", "sum"),
                over50_cells=("error_rate_pct", lambda s: int((s > 50).sum())),
                reference_over50_cells=("ref_error_rate_pct", lambda s: int((s > 50).sum())),
                max_error_rate_increase_pp=("error_delta_eok", lambda s: 0.0),
            )
        )
        queue = (
            g[g.is_queue]
            .groupby("option_name", as_index=False)
            .agg(
                queue_error_eok=("error_gva_eok", "sum"),
                reference_queue_error_eok=("reference_error_gva_eok", "sum"),
                queue_gap10_eok=("gap_to_10pct_eok", "sum"),
                reference_queue_gap10_eok=("reference_gap_to_10pct_eok", "sum"),
            )
        )
        # Parents without queue cells can only retain the reference.
        score = score.drop(
            columns=["queue_error_eok", "reference_queue_error_eok", "queue_gap10_eok", "reference_queue_gap10_eok"]
        ).merge(queue, on="option_name", how="left")
        score[["queue_error_eok", "reference_queue_error_eok", "queue_gap10_eok", "reference_queue_gap10_eok"]] = score[
            ["queue_error_eok", "reference_queue_error_eok", "queue_gap10_eok", "reference_queue_gap10_eok"]
        ].fillna(0)
        max_pp = (
            g.assign(error_rate_delta_pp=lambda z: z.error_rate_pct - z.ref_error_rate_pct)
            .groupby("option_name", as_index=False)
            .agg(max_error_rate_increase_pp=("error_rate_delta_pp", "max"))
        )
        score = score.drop(columns=["max_error_rate_increase_pp"]).merge(max_pp, on="option_name", how="left")
        score["city"] = city
        score["parent_code"] = parent_code
        score["parent_wape_pct"] = score.parent_error_eok / score.parent_actual_eok * 100
        score["parent_error_reduction_eok"] = score.reference_parent_error_eok - score.parent_error_eok
        score["queue_error_reduction_eok"] = score.reference_queue_error_eok - score.queue_error_eok
        score["queue_gap10_reduction_eok"] = score.reference_queue_gap10_eok - score.queue_gap10_eok
        rows.append(score)

        pool = score[
            score.queue_error_reduction_eok.gt(1e-9)
            & score.parent_error_reduction_eok.ge(-1e-9)
            & score.queue_gap10_reduction_eok.ge(-1e-9)
            & score.grade_boundary_worse_cells.eq(0)
            & score.over50_cells.le(score.reference_over50_cells)
        ].sort_values(["queue_error_reduction_eok", "parent_error_reduction_eok"], ascending=[False, False])
        if pool.empty:
            choice = score[score.option_name.eq(ref_name)].iloc[0]
        else:
            choice = pool.iloc[0]
        selected.append(g[g.option_name.eq(choice.option_name)].copy())
    return pd.concat(selected, ignore_index=True), pd.concat(rows, ignore_index=True)


def finalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["accuracy_grade"] = out.error_rate_pct.map(grade)
    out["remaining_queue"] = np.where(
        out.error_rate_pct.gt(10) | out.error_gva_eok.gt(500),
        "추가개선대상",
        "현행유지가능",
    )
    out["error_reduction_eok"] = out.reference_error_gva_eok - out.error_gva_eok
    out["error_rate_delta_pp"] = out.error_rate_pct - out.ref_error_rate_pct
    out["grade_boundary_worse"] = grade_boundary_worse(out)
    return out[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "cause_group",
            "option_name",
            "option_family",
            "actual_gva_eok",
            "reference_predicted_gva_eok",
            "reference_error_gva_eok",
            "predicted_gva_eok",
            "error_gva_eok",
            "error_rate_pct",
            "error_rate_delta_pp",
            "accuracy_grade",
            "remaining_queue",
            "error_reduction_eok",
            "grade_boundary_worse",
        ]
    ]


def summarize(df: pd.DataFrame, label: str) -> pd.DataFrame:
    out = (
        df.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("error_gva_eok", "sum"),
            median_error_pct=("error_rate_pct", "median"),
            within_10pct_cells=("error_rate_pct", lambda s: int((s <= 10).sum())),
            over_20pct_cells=("error_rate_pct", lambda s: int((s > 20).sum())),
            over_50pct_cells=("error_rate_pct", lambda s: int((s > 50).sum())),
            remaining_queue_cells=("remaining_queue", lambda s: int((s == "추가개선대상").sum())),
        )
        .assign(model_stage=label)
    )
    out["wape_pct"] = out.error_sum_eok / out.actual_sum_eok * 100
    return out


def accounting_check(df: pd.DataFrame) -> pd.DataFrame:
    chk = (
        df.groupby(["city", "parent_code"], as_index=False)
        .agg(actual_parent_eok=("actual_gva_eok", "sum"), predicted_parent_eok=("predicted_gva_eok", "sum"))
    )
    chk["gap_eok"] = chk.predicted_parent_eok - chk.actual_parent_eok
    chk["gap_pct"] = chk.gap_eok / chk.actual_parent_eok.replace(0, np.nan) * 100
    chk["pass"] = chk.gap_eok.abs().lt(1e-6)
    return chk


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    options = load_options()
    selected_raw, scorecard = select(options)
    selected = finalize(selected_raw)

    ref = options[options.option_name.eq("Phase92 현재 기준")].copy()
    ref["accuracy_grade"] = ref.error_rate_pct.map(grade)
    ref["remaining_queue"] = np.where(ref.error_rate_pct.gt(10) | ref.error_gva_eok.gt(500), "추가개선대상", "현행유지가능")
    ref_summary = summarize(ref, "Phase92 현재 기준")
    sel_summary = summarize(selected, "Phase96 취약큐 보호 기준")
    summary = pd.concat([ref_summary, sel_summary], ignore_index=True)
    base = ref_summary.set_index("city")
    summary["wape_improvement_pp"] = summary.apply(lambda r: base.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    summary["error_reduction_eok"] = summary.apply(lambda r: base.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)

    selected_choices = (
        scorecard.merge(selected[["city", "parent_code", "option_name"]].drop_duplicates(), on=["city", "parent_code", "option_name"], how="inner")
        .sort_values(["city", "queue_error_reduction_eok"], ascending=[True, False])
    )
    improved_choices = selected_choices[selected_choices.queue_error_reduction_eok.gt(1e-9)].copy()
    improved_cells = selected[selected.error_reduction_eok.gt(1e-9)].sort_values(
        ["city", "error_reduction_eok"], ascending=[True, False]
    )
    worsened_cells = selected[selected.error_reduction_eok.lt(-1e-9)].sort_values(
        ["city", "error_reduction_eok"], ascending=[True, True]
    )
    remaining = selected[selected.remaining_queue.eq("추가개선대상")].sort_values(
        ["city", "error_gva_eok"], ascending=[True, False]
    )
    acct = accounting_check(selected)
    grade_audit = selected[selected.grade_boundary_worse].copy()

    selected.to_csv(OUTDIR / "phase96_selected_protected_registry.csv", index=False, encoding="utf-8-sig")
    scorecard.to_csv(OUTDIR / "phase96_parent_option_scorecard.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase96_summary.csv", index=False, encoding="utf-8-sig")
    acct.to_csv(OUTDIR / "phase96_accounting_checks.csv", index=False, encoding="utf-8-sig")
    grade_audit.to_csv(OUTDIR / "phase96_grade_boundary_audit.csv", index=False, encoding="utf-8-sig")
    worsened_cells.to_csv(OUTDIR / "phase96_worsened_cells.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase96_remaining_queue.csv", index=False, encoding="utf-8-sig")

    report = f"""# 취약 중분류 보호 기준에 의한 GVA 격차 축소

## 목적

Phase95의 개별 중분류 악화 금지 기준은 가장 안전하지만 개선 폭이 작다. 이번 단계에서는 취약 중분류의 오차를 줄이되, 양호 산업이 더 낮은 판정 구간으로 떨어지지 않도록 보호하는 운영 기준을 검증했다.

## 요약 성능

{md_table(summary.sort_values(["city", "model_stage"]), [("city", "지역"), ("model_stage", "단계"), ("cells", "중분류 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_20pct_cells", "20% 초과"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "추가개선대상"), ("wape_improvement_pp", "개선 pp"), ("error_reduction_eok", "감소 억원")])}

## 채택된 상위산업 후보

{md_table(improved_choices, [("city", "지역"), ("parent_code", "상위산업"), ("option_name", "선택 기준"), ("option_family", "기준 유형"), ("parent_error_eok", "상위산업 오차 억원"), ("parent_wape_pct", "상위산업 오차 %"), ("parent_error_reduction_eok", "상위산업 감소 억원"), ("queue_error_reduction_eok", "취약큐 감소 억원"), ("queue_gap10_reduction_eok", "10%초과 감소 억원"), ("grade_boundary_worse_cells", "판정악화 셀")], 80)}

## 오차가 줄어든 중분류

{md_table(improved_cells, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("option_name", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("error_reduction_eok", "감소 억원")], 80)}

## 오차가 증가한 중분류

{md_table(worsened_cells, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("option_name", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("error_reduction_eok", "감소 억원")], 60)}

## 남은 개선 큐

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("option_name", "현재 선택 기준")], 80)}

## 집계 및 판정 감사

상위산업 합계 불일치 건수: {int((~acct["pass"]).sum())}개.

{md_table(acct[~acct["pass"]], [("city", "지역"), ("parent_code", "상위산업"), ("actual_parent_eok", "실제합계 억원"), ("predicted_parent_eok", "추정합계 억원"), ("gap_eok", "차이 억원"), ("gap_pct", "차이 %")], 40)}

판정 구간 악화 건수: {len(grade_audit)}개.

{md_table(grade_audit, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("error_rate_pct", "선택 오차 %"), ("error_rate_delta_pp", "오차율 변화 pp"), ("option_name", "선택 기준")], 40)}

## 판정

1. 이 기준은 엄격 기준보다 실무적으로 더 많은 취약 중분류 격차를 줄일 수 있는지 확인하기 위한 운영안이다.
2. 상위산업 합계는 모두 보존하며, 판정 구간 악화는 허용하지 않는다.
3. 오차가 증가한 중분류는 별도 표로 공개해, 전체 개선이 특정 산업의 악화를 가리는지 확인한다.
4. 포스터에는 엄격 기준을 기본으로 두고, 운영안은 취약 산업 개선 가능성 또는 후속 고도화 방향으로만 사용한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase96_summary.csv")


if __name__ == "__main__":
    main()
