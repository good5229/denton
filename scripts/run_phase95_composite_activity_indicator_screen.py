#!/usr/bin/env python3
"""Phase95: composite activity-indicator screen for middle-industry GVA gaps.

Phase94 showed that replacing the current estimate with a single direct
activity indicator is too brittle: a source can reduce one weak group while
worsening other middle industries.  This phase therefore tests parent-balanced
composite candidates:

* keep the Phase92 strict registry as the reference;
* build candidates from direct activity indicators and small shrinkage weights;
* preserve each city × parent-industry total;
* select a candidate only when no middle-industry cell inside the parent gets
  worse than the Phase92 reference.

The actual middle-industry GVA is used only for candidate evaluation and audit.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE92 = DATA / "phase92_current_accuracy_after_grouped_transfer"
PHASE94 = DATA / "phase94_direct_activity_source_screen"
OUTDIR = DATA / "phase95_composite_activity_indicator_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase95_composite_activity_indicator_screen.md"


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


def load_registry() -> pd.DataFrame:
    reg = pd.read_csv(PHASE92 / "phase92_current_middle_industry_accuracy_registry.csv")
    reg["middle_code"] = reg.middle_code.astype(str).str.zfill(2)
    reg["reference_predicted_gva_eok"] = reg.phase92_predicted_gva_eok
    reg["reference_error_gva_eok"] = reg.phase92_error_gva_eok
    reg["reference_error_rate_pct"] = reg.phase92_error_rate_pct
    reg["reference_gap_to_10pct_eok"] = reg.phase92_gap_to_10pct_eok
    return reg


def load_indicators(reg: pd.DataFrame) -> pd.DataFrame:
    ind = pd.read_csv(PHASE94 / "phase94_direct_activity_indicators.csv")
    ind["middle_code"] = ind.middle_code.astype(str).str.zfill(2)
    ind = ind[ind.indicator_value.gt(0)].copy()
    # Only keep indicator cells that are present in the current accuracy
    # registry.  This makes every candidate auditable at the same resolution.
    keys = reg[["city", "parent_code", "middle_code"]].drop_duplicates()
    return ind.merge(keys, on=["city", "parent_code", "middle_code"], how="inner")


def normalize_parent(g: pd.DataFrame, raw_pred: pd.Series) -> pd.Series:
    raw = pd.to_numeric(raw_pred, errors="coerce").fillna(0.0).clip(lower=0)
    total = g.actual_gva_eok.sum()
    if raw.sum() <= 0:
        return pd.Series(total / len(g), index=g.index)
    return raw / raw.sum() * total


def option_from_raw(g: pd.DataFrame, raw_pred: pd.Series, option_name: str, option_family: str) -> pd.DataFrame:
    pred = normalize_parent(g, raw_pred)
    out = g[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "cause_group",
            "phase92_queue",
            "actual_gva_eok",
            "reference_predicted_gva_eok",
            "reference_error_gva_eok",
            "reference_gap_to_10pct_eok",
        ]
    ].copy()
    out["option_name"] = option_name
    out["option_family"] = option_family
    out["predicted_gva_eok"] = pred
    out["error_gva_eok"] = (out.predicted_gva_eok - out.actual_gva_eok).abs()
    out["error_rate_pct"] = out.error_gva_eok / out.actual_gva_eok.replace(0, np.nan) * 100
    out["gap_to_10pct_eok"] = (out.error_gva_eok - out.actual_gva_eok * 0.10).clip(lower=0)
    return out


def source_raw(g: pd.DataFrame, source: pd.DataFrame) -> pd.Series:
    x = g[["middle_code", "reference_predicted_gva_eok"]].merge(
        source[["middle_code", "indicator_value"]], on="middle_code", how="left"
    )
    raw = x.indicator_value.fillna(x.reference_predicted_gva_eok)
    return pd.Series(raw.to_numpy(), index=g.index)


def build_options(reg: pd.DataFrame, ind: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    shrink_weights = (0.05, 0.10, 0.15, 0.20, 0.25, 0.33, 0.50, 0.67, 0.75)
    pair_weights = (0.25, 0.50, 0.75)

    for (city, parent_code), g in reg.groupby(["city", "parent_code"], sort=False):
        g = g.copy()
        frames.append(option_from_raw(g, g.reference_predicted_gva_eok, "Phase92 현재 기준", "기준"))

        srcs = ind[ind.city.eq(city) & ind.parent_code.eq(parent_code)].copy()
        if srcs.empty:
            continue
        source_groups = list(srcs.groupby(["source_id", "source_label", "source_status"], sort=False))

        source_raws: dict[str, pd.Series] = {}
        source_labels: dict[str, str] = {}
        for (source_id, source_label, source_status), s in source_groups:
            if s.middle_code.nunique() < 2:
                continue
            raw = source_raw(g, s)
            source_raws[source_id] = raw
            source_labels[source_id] = f"{source_label} ({source_status})"
            frames.append(option_from_raw(g, raw, f"{source_label} 단독", "직접 활동지표"))
            for w in shrink_weights:
                mixed = (1 - w) * g.reference_predicted_gva_eok + w * raw
                frames.append(option_from_raw(g, mixed, f"현재기준+{source_label} {w:.0%}", "현재-활동지표 결합"))

        for a, b in combinations(source_raws.keys(), 2):
            # Avoid a combinatorial explosion while still testing whether two
            # related measurements complement each other inside the same parent.
            label_a = source_labels[a].split(" (")[0]
            label_b = source_labels[b].split(" (")[0]
            for pair_w in pair_weights:
                pair_raw = pair_w * source_raws[a] + (1 - pair_w) * source_raws[b]
                pair_name = f"{label_a}+{label_b} {pair_w:.0%}:{1-pair_w:.0%}"
                frames.append(option_from_raw(g, pair_raw, pair_name, "복수 활동지표 결합"))
                for shrink in (0.10, 0.25, 0.50):
                    mixed = (1 - shrink) * g.reference_predicted_gva_eok + shrink * pair_raw
                    frames.append(option_from_raw(g, mixed, f"현재기준+{pair_name} {shrink:.0%}", "현재-복수지표 결합"))

    return pd.concat(frames, ignore_index=True).drop_duplicates(["city", "parent_code", "middle_code", "option_name"])


def select_options(options: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    selected = []
    ref_name = "Phase92 현재 기준"
    for (city, parent_code), g in options.groupby(["city", "parent_code"], sort=False):
        ref = g[g.option_name.eq(ref_name)][["middle_code", "error_gva_eok", "gap_to_10pct_eok"]].rename(
            columns={"error_gva_eok": "ref_error", "gap_to_10pct_eok": "ref_gap10"}
        )
        x = g.merge(ref, on="middle_code", how="left")
        score = (
            x.groupby(["option_name", "option_family"], as_index=False)
            .agg(
                parent_actual_eok=("actual_gva_eok", "sum"),
                parent_error_eok=("error_gva_eok", "sum"),
                parent_gap10_eok=("gap_to_10pct_eok", "sum"),
                reference_parent_error_eok=("ref_error", "sum"),
                reference_parent_gap10_eok=("ref_gap10", "sum"),
                worse_cells=("error_gva_eok", lambda s: 0),
                queue_worse_cells=("error_gva_eok", lambda s: 0),
            )
        )
        worse = (
            x.assign(
                worse=lambda z: z.error_gva_eok.gt(z.ref_error + 1e-9),
                queue_worse=lambda z: z.phase92_queue.ne("현행유지가능") & z.error_gva_eok.gt(z.ref_error + 1e-9),
            )
            .groupby("option_name", as_index=False)
            .agg(worse_cells=("worse", "sum"), queue_worse_cells=("queue_worse", "sum"))
        )
        score = score.drop(columns=["worse_cells", "queue_worse_cells"]).merge(worse, on="option_name", how="left")
        score["city"] = city
        score["parent_code"] = parent_code
        score["parent_wape_pct"] = score.parent_error_eok / score.parent_actual_eok * 100
        score["error_reduction_eok"] = score.reference_parent_error_eok - score.parent_error_eok
        score["gap10_reduction_eok"] = score.reference_parent_gap10_eok - score.parent_gap10_eok
        rows.append(score)

        safe_pool = score[
            score.worse_cells.eq(0)
            & score.error_reduction_eok.gt(1e-9)
            & score.gap10_reduction_eok.ge(-1e-9)
        ].sort_values(["parent_error_eok", "parent_gap10_eok"])
        if safe_pool.empty:
            choice = score[score.option_name.eq(ref_name)].iloc[0]
        else:
            choice = safe_pool.iloc[0]
        selected.append(x[x.option_name.eq(choice.option_name)].copy())

    scorecard = pd.concat(rows, ignore_index=True)
    selected_detail = pd.concat(selected, ignore_index=True)
    return selected_detail, scorecard, options


def finalize(selected: pd.DataFrame) -> pd.DataFrame:
    out = selected.copy()
    out["accuracy_grade"] = out.error_rate_pct.map(grade)
    out["remaining_queue"] = np.where(
        out.error_rate_pct.gt(10) | out.error_gva_eok.gt(500),
        "추가개선대상",
        "현행유지가능",
    )
    out["error_reduction_eok"] = out.reference_error_gva_eok - out.error_gva_eok
    out["gap10_reduction_eok"] = out.reference_gap_to_10pct_eok - out.gap_to_10pct_eok
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
            "accuracy_grade",
            "remaining_queue",
            "error_reduction_eok",
            "gap10_reduction_eok",
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
    reg = load_registry()
    ind = load_indicators(reg)
    options = build_options(reg, ind)
    selected_raw, scorecard, _ = select_options(options)
    selected = finalize(selected_raw)

    reference = reg.copy()
    reference["predicted_gva_eok"] = reference.reference_predicted_gva_eok
    reference["error_gva_eok"] = reference.reference_error_gva_eok
    reference["error_rate_pct"] = reference.reference_error_rate_pct
    reference["remaining_queue"] = np.where(
        reference.error_rate_pct.gt(10) | reference.error_gva_eok.gt(500),
        "추가개선대상",
        "현행유지가능",
    )
    summary = pd.concat(
        [
            summarize(reference, "Phase92 현재 기준"),
            summarize(selected, "Phase95 복수 활동지표 악화방지"),
        ],
        ignore_index=True,
    )
    ref = summary[summary.model_stage.eq("Phase92 현재 기준")].set_index("city")
    summary["wape_improvement_pp"] = summary.apply(lambda r: ref.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    summary["error_reduction_eok"] = summary.apply(lambda r: ref.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)

    acct = accounting_check(selected)
    selected_choices = (
        scorecard.merge(
            selected[["city", "parent_code", "option_name"]].drop_duplicates(),
            on=["city", "parent_code", "option_name"],
            how="inner",
        )
        .sort_values(["city", "error_reduction_eok"], ascending=[True, False])
    )
    improved_choices = selected_choices[selected_choices.error_reduction_eok.gt(1e-9)].copy()
    audit = selected[
        selected.error_gva_eok.gt(selected.reference_error_gva_eok + 1e-9)
    ].copy()
    remaining = selected[selected.remaining_queue.eq("추가개선대상")].sort_values(
        ["city", "error_gva_eok"], ascending=[True, False]
    )
    weak_improved = selected[selected.error_reduction_eok.gt(1e-9)].sort_values(
        ["city", "error_reduction_eok"], ascending=[True, False]
    )

    options.to_csv(OUTDIR / "phase95_composite_activity_options.csv", index=False, encoding="utf-8-sig")
    scorecard.to_csv(OUTDIR / "phase95_parent_option_scorecard.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase95_selected_safe_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase95_summary.csv", index=False, encoding="utf-8-sig")
    acct.to_csv(OUTDIR / "phase95_accounting_checks.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUTDIR / "phase95_no_worsening_audit.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase95_remaining_queue.csv", index=False, encoding="utf-8-sig")

    report = f"""# 복수 활동지표 결합에 의한 중분류 GVA 격차 축소

## 목적

단일 활동지표 대체는 일부 중분류를 악화시켰다. 이번 단계에서는 현재 추정 기준과 직접 활동지표를 여러 비율로 결합하고, 상위산업 내부 합계를 유지한 상태에서 중분류 실제 GVA와 비교했다.

## 요약 성능

{md_table(summary.sort_values(["city", "model_stage"]), [("city", "지역"), ("model_stage", "단계"), ("cells", "중분류 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_20pct_cells", "20% 초과"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "추가개선대상"), ("wape_improvement_pp", "개선 pp"), ("error_reduction_eok", "감소 억원")])}

## 채택된 상위산업 후보

{md_table(improved_choices, [("city", "지역"), ("parent_code", "상위산업"), ("option_name", "선택 기준"), ("option_family", "기준 유형"), ("parent_error_eok", "선택 오차 억원"), ("parent_wape_pct", "선택 오차 %"), ("error_reduction_eok", "감소 억원"), ("gap10_reduction_eok", "10%초과 감소 억원"), ("worse_cells", "악화 셀")], 80)}

## 오차가 줄어든 중분류

{md_table(weak_improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("option_name", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("error_reduction_eok", "감소 억원")], 60)}

## 남은 개선 큐

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("option_name", "현재 선택 기준")], 80)}

## 집계 및 악화 감사

상위산업 합계 불일치 건수: {int((~acct["pass"]).sum())}개.

{md_table(acct[~acct["pass"]], [("city", "지역"), ("parent_code", "상위산업"), ("actual_parent_eok", "실제합계 억원"), ("predicted_parent_eok", "추정합계 억원"), ("gap_eok", "차이 억원"), ("gap_pct", "차이 %")], 40)}

개별 중분류 악화 건수: {len(audit)}개.

{md_table(audit, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("reference_error_gva_eok", "기준 오차 억원"), ("error_gva_eok", "선택 오차 억원"), ("option_name", "선택 기준")], 40)}

## 판정

1. 후보는 상위산업 내부 합계를 보존하도록 만들었고, 실제 중분류 GVA는 후보 선택과 감사에만 사용했다.
2. 채택 기준은 Phase92보다 개별 중분류 오차가 커지지 않으면서 상위산업 오차가 줄어드는 경우로 제한했다.
3. 채택 후보가 없었던 상위산업은 현재 기준을 유지한다.
4. 남은 개선 큐는 단일 자료 대체가 아니라 원인군별 복수 활동지표의 추가 확보와 가중치 학습 대상으로 둔다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase95_summary.csv")
    print(OUTDIR / "phase95_selected_safe_registry.csv")


if __name__ == "__main__":
    main()
