#!/usr/bin/env python3
"""Phase100: screen candidate rules against Phase99 weak-industry bundles.

The user goal is industry-level GVA accuracy, not accounting residuals.  This
phase therefore evaluates existing activity-indicator candidates at the same
unit introduced in Phase99: city × cause group × parent industry.  It does not
hand-tune one middle industry at a time.

Baseline:
    Phase98 protected registry, because Phase99's remaining queue is defined
    from that registry.

Candidate pool:
    Phase97 augmented activity options, which include KOSIS manufacturing,
    Pohang business survey, Pohang factory, Goyang LOCALDATA/factory/bus, and
    other direct public activity indicators generated in earlier phases.

Selection gates:
    * strict_public: target weak-bundle error decreases, parent error
      decreases, and no middle industry in the parent worsens.
    * bundle_operational: target weak-bundle error decreases and parent error
      decreases, even if some individual cells still require review.
    * no_candidate: no available candidate beats the Phase98 protected baseline
      at the bundle level.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE98 = DATA / "phase98_final_middle_industry_accuracy_registry"
PHASE99 = DATA / "phase99_remaining_weak_industry_backlog"
PHASE97 = DATA / "phase97_goyang_augmented_activity_screen"
OUTDIR = DATA / "phase100_bundle_candidate_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase100_bundle_candidate_screen.md"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append(
        "| "
        + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "감소")) else "---" for _, label in cols)
        + " |"
    )
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


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    reg = pd.read_csv(PHASE98 / "phase98_final_middle_industry_accuracy_registry.csv")
    weak = pd.read_csv(PHASE99 / "phase99_remaining_weak_industry_backlog.csv")
    bundles = pd.read_csv(PHASE99 / "phase99_grouped_improvement_bundles.csv")
    options = pd.read_csv(PHASE97 / "phase97_augmented_activity_options.csv")
    for frame in (reg, weak, bundles, options):
        if "middle_code" in frame.columns:
            frame["middle_code"] = frame.middle_code.astype(str).str.zfill(2)
    return reg, weak, bundles, options


def score_options(reg: pd.DataFrame, weak: pd.DataFrame, options: pd.DataFrame) -> pd.DataFrame:
    baseline = reg[
        [
            "city",
            "parent_code",
            "middle_code",
            "protected_predicted_gva_eok",
            "protected_error_gva_eok",
            "protected_error_rate_pct",
            "protected_accuracy_grade",
        ]
    ].copy()
    weak_keys = weak[["city", "parent_code", "middle_code", "cause_group", "bundle_key"]].drop_duplicates()
    opts = options.merge(baseline, on=["city", "parent_code", "middle_code"], how="inner")
    opts = opts.merge(weak_keys, on=["city", "parent_code", "middle_code"], how="left", suffixes=("", "_weak"))
    opts["is_phase99_weak"] = opts.bundle_key.notna()

    rows: list[dict] = []
    for (city, parent_code, option_name), g in opts.groupby(["city", "parent_code", "option_name"], sort=False):
        family = g.option_family.iloc[0]
        parent_error_base = g.protected_error_gva_eok.sum()
        parent_error_option = g.error_gva_eok.sum()
        parent_worse_cells = int(g.error_gva_eok.gt(g.protected_error_gva_eok + 1e-9).sum())
        parent_error_reduction = parent_error_base - parent_error_option

        for (cause_group, bundle_key), wg in g[g.is_phase99_weak].groupby(["cause_group_weak", "bundle_key"], sort=False):
            if wg.empty:
                continue
            target_error_base = wg.protected_error_gva_eok.sum()
            target_error_option = wg.error_gva_eok.sum()
            target_reduction = target_error_base - target_error_option
            target_actual = wg.actual_gva_eok.sum()
            rows.append(
                {
                    "city": city,
                    "cause_group": cause_group,
                    "parent_code": parent_code,
                    "bundle_key": bundle_key,
                    "option_name": option_name,
                    "option_family": family,
                    "target_cells": int(len(wg)),
                    "target_actual_eok": target_actual,
                    "target_error_base_eok": target_error_base,
                    "target_error_option_eok": target_error_option,
                    "target_error_reduction_eok": target_reduction,
                    "target_wape_base_pct": target_error_base / target_actual * 100 if target_actual else np.nan,
                    "target_wape_option_pct": target_error_option / target_actual * 100 if target_actual else np.nan,
                    "target_worse_cells": int(wg.error_gva_eok.gt(wg.protected_error_gva_eok + 1e-9).sum()),
                    "parent_error_base_eok": parent_error_base,
                    "parent_error_option_eok": parent_error_option,
                    "parent_error_reduction_eok": parent_error_reduction,
                    "parent_worse_cells": parent_worse_cells,
                }
            )
    score = pd.DataFrame(rows)
    if score.empty:
        return score
    score["strict_public_pass"] = (
        score.target_error_reduction_eok.gt(1e-9)
        & score.parent_error_reduction_eok.gt(1e-9)
        & score.target_worse_cells.eq(0)
        & score.parent_worse_cells.eq(0)
    )
    score["bundle_operational_pass"] = score.target_error_reduction_eok.gt(1e-9) & score.parent_error_reduction_eok.gt(1e-9)
    return score


def select_bundle_candidates(score: pd.DataFrame, bundles: pd.DataFrame) -> pd.DataFrame:
    selected: list[pd.Series] = []
    for bundle in bundles.itertuples(index=False):
        g = score[score.bundle_key.eq(bundle.bundle_key)].copy()
        if g.empty:
            row = pd.Series(
                {
                    "city": bundle.city,
                    "cause_group": bundle.cause_group,
                    "parent_code": bundle.parent_code,
                    "bundle_key": bundle.bundle_key,
                    "option_name": "후보 없음",
                    "option_family": "미평가",
                    "decision": "no_candidate",
                    "target_cells": bundle.cells,
                    "target_actual_eok": bundle.actual_sum_eok,
                    "target_error_base_eok": bundle.protected_error_sum_eok,
                    "target_error_option_eok": bundle.protected_error_sum_eok,
                    "target_error_reduction_eok": 0.0,
                    "target_wape_base_pct": bundle.bundle_wape_pct,
                    "target_wape_option_pct": bundle.bundle_wape_pct,
                    "target_worse_cells": np.nan,
                    "parent_error_reduction_eok": 0.0,
                    "parent_worse_cells": np.nan,
                }
            )
            selected.append(row)
            continue
        strict = g[g.strict_public_pass].sort_values(["target_error_reduction_eok", "parent_error_reduction_eok"], ascending=False)
        operational = g[g.bundle_operational_pass].sort_values(
            ["target_error_reduction_eok", "parent_error_reduction_eok"], ascending=False
        )
        if not strict.empty:
            choice = strict.iloc[0].copy()
            choice["decision"] = "strict_public"
        elif not operational.empty:
            choice = operational.iloc[0].copy()
            choice["decision"] = "bundle_operational"
        else:
            base = g[g.option_name.eq("Phase92 현재 기준")]
            choice = (base.iloc[0] if not base.empty else g.sort_values("target_error_option_eok").iloc[0]).copy()
            choice["decision"] = "no_candidate"
            # Keep the baseline, not an overfit lower-error candidate that
            # failed the parent/bundle improvement gate.
            choice["target_error_option_eok"] = choice["target_error_base_eok"]
            choice["target_error_reduction_eok"] = 0.0
            choice["target_wape_option_pct"] = choice["target_wape_base_pct"]
            choice["parent_error_reduction_eok"] = 0.0
            choice["option_name"] = "Phase98 protected baseline"
            choice["option_family"] = "기준"
        selected.append(choice)
    return pd.DataFrame(selected)


def summarize(selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_city = (
        selected.groupby("city", as_index=False)
        .agg(
            bundles=("bundle_key", "count"),
            strict_public=("decision", lambda s: int((s == "strict_public").sum())),
            bundle_operational=("decision", lambda s: int((s == "bundle_operational").sum())),
            no_candidate=("decision", lambda s: int((s == "no_candidate").sum())),
            target_actual_eok=("target_actual_eok", "sum"),
            target_error_base_eok=("target_error_base_eok", "sum"),
            target_error_option_eok=("target_error_option_eok", "sum"),
            target_error_reduction_eok=("target_error_reduction_eok", "sum"),
        )
    )
    by_city["target_wape_base_pct"] = by_city.target_error_base_eok / by_city.target_actual_eok * 100
    by_city["target_wape_option_pct"] = by_city.target_error_option_eok / by_city.target_actual_eok * 100
    by_city["wape_reduction_pp"] = by_city.target_wape_base_pct - by_city.target_wape_option_pct

    by_decision = (
        selected.groupby("decision", as_index=False)
        .agg(
            bundles=("bundle_key", "count"),
            target_actual_eok=("target_actual_eok", "sum"),
            target_error_base_eok=("target_error_base_eok", "sum"),
            target_error_option_eok=("target_error_option_eok", "sum"),
            target_error_reduction_eok=("target_error_reduction_eok", "sum"),
        )
        .sort_values("target_error_reduction_eok", ascending=False)
    )
    by_decision["target_wape_base_pct"] = by_decision.target_error_base_eok / by_decision.target_actual_eok * 100
    by_decision["target_wape_option_pct"] = by_decision.target_error_option_eok / by_decision.target_actual_eok * 100
    return by_city, by_decision


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg, weak, bundles, options = load_inputs()
    score = score_options(reg, weak, options)
    selected = select_bundle_candidates(score, bundles)
    by_city, by_decision = summarize(selected)

    score.to_csv(OUTDIR / "phase100_bundle_candidate_scorecard.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase100_selected_bundle_candidates.csv", index=False, encoding="utf-8-sig")
    by_city.to_csv(OUTDIR / "phase100_summary_by_city.csv", index=False, encoding="utf-8-sig")
    by_decision.to_csv(OUTDIR / "phase100_summary_by_decision.csv", index=False, encoding="utf-8-sig")

    selected_view = selected.sort_values(["decision", "target_error_reduction_eok"], ascending=[True, False]).copy()
    operational = selected[selected.decision.eq("bundle_operational")].sort_values(
        "target_error_reduction_eok", ascending=False
    )
    blocked = selected[selected.decision.eq("no_candidate")].sort_values("target_error_base_eok", ascending=False)
    strict = selected[selected.decision.eq("strict_public")]

    report = f"""# 취약 중분류 묶음 후보 스크린

## 목적

Phase99에서 남은 취약 중분류를 14개 `지역×원인군×상위산업` 묶음으로 정리했다. 이번 실험은 기존에 수집·생성한 무료 공공 활동지표 후보가 이 묶음들의 실제-추정 총부가가치 격차를 줄이는지 한 번에 평가했다. 단일 중분류를 하나씩 고치지 않고, 묶음 단위 후보만 비교했다.

## 판정 기준

| 판정 | 의미 |
| --- | --- |
| strict_public | 묶음 오차와 상위산업 오차가 모두 줄고, 상위산업 내부 중분류 악화가 0건 |
| bundle_operational | 묶음 오차와 상위산업 오차가 모두 줄지만, 일부 중분류 악화가 있어 대외 성능 주장에는 미사용 |
| no_candidate | 현재 후보군으로는 Phase98 protected 기준보다 묶음 단위 격차를 줄이지 못함 |

## 도시별 결과

{md_table(by_city, [("city", "지역"), ("bundles", "묶음 개"), ("strict_public", "strict 개"), ("bundle_operational", "운영후보 개"), ("no_candidate", "후보없음 개"), ("target_actual_eok", "취약 실제합계 억원"), ("target_error_base_eok", "기준 오차 억원"), ("target_error_option_eok", "후보 오차 억원"), ("target_error_reduction_eok", "오차감소 억원"), ("target_wape_base_pct", "기준 WAPE %"), ("target_wape_option_pct", "후보 WAPE %"), ("wape_reduction_pp", "WAPE 감소 pp")])}

## 판정별 요약

{md_table(by_decision, [("decision", "판정"), ("bundles", "묶음 개"), ("target_actual_eok", "취약 실제합계 억원"), ("target_error_base_eok", "기준 오차 억원"), ("target_error_option_eok", "후보 오차 억원"), ("target_error_reduction_eok", "오차감소 억원"), ("target_wape_base_pct", "기준 WAPE %"), ("target_wape_option_pct", "후보 WAPE %")])}

## 운영 후보

{md_table(operational, [("city", "지역"), ("cause_group", "원인군"), ("parent_code", "상위산업"), ("option_name", "후보"), ("target_cells", "취약 중분류 개"), ("target_error_base_eok", "기준 오차 억원"), ("target_error_option_eok", "후보 오차 억원"), ("target_error_reduction_eok", "오차감소 억원"), ("target_wape_base_pct", "기준 WAPE %"), ("target_wape_option_pct", "후보 WAPE %"), ("target_worse_cells", "취약 악화 개"), ("parent_worse_cells", "상위내 악화 개")], 30)}

## strict public 후보

{md_table(strict, [("city", "지역"), ("cause_group", "원인군"), ("parent_code", "상위산업"), ("option_name", "후보"), ("target_error_reduction_eok", "오차감소 억원")], 30)}

## 후보가 아직 없는 주요 묶음

{md_table(blocked, [("city", "지역"), ("cause_group", "원인군"), ("parent_code", "상위산업"), ("target_cells", "취약 중분류 개"), ("target_error_base_eok", "기준 오차 억원"), ("target_wape_base_pct", "기준 WAPE %"), ("option_name", "현재 선택")], 30)}

## 결론

1. 기존 후보군만으로는 `strict_public`을 통과한 묶음이 없다. 즉, 이번 후보군은 아직 “각 산업별 정확도”를 강하게 주장할 수 있는 최종 개선안이 아니다.
2. `bundle_operational` 기준으로는 포항의 일부 묶음에서 실제-추정 GVA 격차가 줄었다. 특히 포항 생산시설형 C00은 제조업·사업체조사·공장등록 계열 복수 활동지표가 묶음 오차를 낮춘다.
3. 고양시는 현재 후보군으로 Phase99 취약 묶음 전체를 줄이는 후보가 없다. 고양의 핵심 병목은 협회·단체, 방송·콘텐츠, 연구개발·과학기술, 자동차판매, 일부 제조업에 직접 대응하는 무료 활동자료 부족이다.
4. 다음 개선은 새 산업을 하나씩 고치는 것이 아니라, `공공·비영리형`, `디지털·콘텐츠형`, `전문·지원서비스형`, `계약·공사형`에 대해 묶음 전체를 설명하는 직접 활동자료를 추가 수집한 뒤 같은 Phase100 gate로 재검증해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase100_selected_bundle_candidates.csv")


if __name__ == "__main__":
    main()
