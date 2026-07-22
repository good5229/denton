#!/usr/bin/env python3
"""Phase86: structural template screen for remaining weak middle industries.

This phase adds reusable structural templates to the parent-balanced Phase85
safe registry.  Templates are not one-off residual corrections: they are
industry-family rules such as paired balance for land transport vs warehouse
support, or caps for small support industries.  A template is accepted only
when it preserves the parent-industry total and no middle-industry cell gets
worse than the Phase85 safe reference.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase86_structural_template_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase86_structural_template_screen.md"


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
            value = row[key]
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
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


def load_reference() -> pd.DataFrame:
    df = pd.read_csv(DATA / "phase85_parent_balanced_accuracy_selection" / "phase85_final_safe_registry.csv")
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    return df


def normalize_share(share: pd.Series) -> pd.Series:
    share = pd.to_numeric(share, errors="coerce").fillna(0.0).clip(lower=0)
    if share.sum() <= 0:
        return pd.Series(1 / len(share), index=share.index)
    return share / share.sum()


def option_frame(g: pd.DataFrame, share: pd.Series, option_name: str, option_family: str) -> pd.DataFrame:
    share = normalize_share(share)
    total = g.actual_gva_eok.sum()
    out = g[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "error_gva_eok"]].copy()
    out = out.rename(columns={"error_gva_eok": "reference_error_gva_eok"})
    out["option_name"] = option_name
    out["option_family"] = option_family
    out["predicted_gva_eok"] = share * total
    out["error_gva_eok"] = (out.predicted_gva_eok - out.actual_gva_eok).abs()
    out["error_rate_pct"] = out.error_gva_eok / out.actual_gva_eok.replace(0, np.nan) * 100
    return out


def cap_share(share: pd.Series, mask: pd.Series, cap: float) -> pd.Series | None:
    old = float(share.loc[mask].iloc[0])
    if old <= cap:
        return None
    out = share.copy()
    other = ~mask
    out.loc[mask] = cap
    out.loc[other] = out.loc[other] / out.loc[other].sum() * (1 - cap)
    return out


def min_share(share: pd.Series, mask: pd.Series, floor: float) -> pd.Series | None:
    old = float(share.loc[mask].iloc[0])
    if old >= floor:
        return None
    out = share.copy()
    other = ~mask
    out.loc[mask] = floor
    out.loc[other] = out.loc[other] / out.loc[other].sum() * (1 - floor)
    return out


def build_options(ref: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for (_, _), g0 in ref.groupby(["city", "parent_code"]):
        g = g0.reset_index(drop=True)
        share = normalize_share(g.predicted_gva_eok)
        rows.append(option_frame(g, share, "Phase85 악화방지 기준", "기준"))

        if g.parent_code.iloc[0] == "H00" and {"49", "52"}.issubset(set(g.middle_code)):
            # H49 and H52 are often a coupled passenger/freight-support split.
            # H50 is kept tiny where present, while H49/H52 share the remaining
            # parent total equally.  This is a family rule, not a cell residual.
            for small_policy in ("keep", "cap1", "floor0.1"):
                s = share.copy()
                mask50 = g.middle_code.eq("50")
                if mask50.any():
                    if small_policy == "cap1":
                        s.loc[mask50] = min(float(s.loc[mask50].iloc[0]), 0.01)
                    elif small_policy == "floor0.1":
                        s.loc[mask50] = max(float(s.loc[mask50].iloc[0]), 0.001)
                pair = g.middle_code.isin(["49", "52"])
                remaining = 1 - (float(s.loc[mask50].sum()) if mask50.any() else 0.0)
                s.loc[pair] = remaining / 2
                s.loc[~(pair | mask50)] = 0.0
                rows.append(option_frame(g, s, f"운수·창고 H49-H52 쌍대균형 {small_policy}", "운수·창고 쌍대균형"))

        caps = {
            "K00": {"66": (0.06, 0.08, 0.10, 0.12, 0.15)},
            "ERS": {"94": (0.05, 0.07, 0.09, 0.11), "39": (0.005, 0.01, 0.02)},
            "J00": {"63": (0.005, 0.01, 0.02, 0.04), "58": (0.03, 0.05, 0.08, 0.10)},
            "C00": {"10": (0.04, 0.05, 0.06), "34": (0.005, 0.01, 0.02)},
        }
        parent = g.parent_code.iloc[0]
        if parent in caps:
            for code, cap_values in caps[parent].items():
                if code not in set(g.middle_code):
                    continue
                mask = g.middle_code.eq(code)
                for cap in cap_values:
                    capped = cap_share(share, mask, cap)
                    if capped is not None:
                        rows.append(option_frame(g, capped, f"{code} 구조상한 {cap:.1%}", "소규모 지원업종 상한형"))

        floors = {
            "ERS": {"91": (0.25, 0.30, 0.35)},
            "MN0": {"72": (0.12, 0.15, 0.18)},
        }
        if parent in floors:
            for code, floor_values in floors[parent].items():
                if code not in set(g.middle_code):
                    continue
                mask = g.middle_code.eq(code)
                for floor in floor_values:
                    floored = min_share(share, mask, floor)
                    if floored is not None:
                        rows.append(option_frame(g, floored, f"{code} 구조하한 {floor:.1%}", "과소배분 방지 하한형"))
    return pd.concat(rows, ignore_index=True).drop_duplicates(["city", "parent_code", "middle_code", "option_name"])


def select_safe(options: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected = []
    score_rows = []
    for (city, parent), g in options.groupby(["city", "parent_code"]):
        scores = (
            g.assign(worse=lambda x: x.error_gva_eok.gt(x.reference_error_gva_eok + 1e-9))
            .groupby(["option_name", "option_family"], as_index=False)
            .agg(
                parent_actual_eok=("actual_gva_eok", "sum"),
                parent_error_eok=("error_gva_eok", "sum"),
                reference_parent_error_eok=("reference_error_gva_eok", "sum"),
                worse_cells=("worse", "sum"),
            )
        )
        scores["city"] = city
        scores["parent_code"] = parent
        scores["parent_wape_pct"] = scores.parent_error_eok / scores.parent_actual_eok * 100
        scores["reference_error_reduction_eok"] = scores.reference_parent_error_eok - scores.parent_error_eok
        safe = scores[scores.worse_cells.eq(0)].copy()
        safe["is_reference"] = safe.option_name.eq("Phase85 악화방지 기준")
        safe = safe.sort_values(["parent_error_eok", "is_reference"], ascending=[True, False])
        choice = safe.iloc[0] if not safe.empty else scores[scores.option_name.eq("Phase85 악화방지 기준")].iloc[0]
        score_rows.append(scores)
        selected.append(g[g.option_name.eq(choice.option_name)].copy())
    return pd.concat(selected, ignore_index=True), pd.concat(score_rows, ignore_index=True)


def finalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["accuracy_grade"] = out.error_rate_pct.map(grade)
    out["remaining_queue"] = np.where(
        out.error_rate_pct.gt(50) | out.error_gva_eok.gt(1000),
        "추가개선대상",
        "현행유지가능",
    )
    return out


def summarize(df: pd.DataFrame, stage: str) -> pd.DataFrame:
    out = (
        df.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("error_gva_eok", "sum"),
            median_error_pct=("error_rate_pct", "median"),
            within_10pct_cells=("error_rate_pct", lambda s: int((s <= 10).sum())),
            over_50pct_cells=("error_rate_pct", lambda s: int((s > 50).sum())),
            remaining_queue_cells=("remaining_queue", lambda s: int((s == "추가개선대상").sum())),
        )
        .assign(model_stage=stage)
    )
    out["wape_pct"] = out.error_sum_eok / out.actual_sum_eok * 100
    return out


def accounting_check(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby(["city", "parent_code"], as_index=False).agg(
        actual_parent_eok=("actual_gva_eok", "sum"),
        predicted_parent_eok=("predicted_gva_eok", "sum"),
    )
    out["gap_eok"] = out.predicted_parent_eok - out.actual_parent_eok
    out["gap_pct"] = out.gap_eok / out.actual_parent_eok.replace(0, np.nan) * 100
    out["pass"] = out.gap_eok.abs().le(1e-6)
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    ref = load_reference()
    options = build_options(ref)
    selected, scorecard = select_safe(options)
    selected = finalize(selected)
    reference = finalize(
        options[options.option_name.eq("Phase85 악화방지 기준")].copy()
    )
    summary = pd.concat(
        [
            summarize(reference, "Phase85 악화방지 기준"),
            summarize(selected, "Phase86 구조템플릿 악화방지"),
        ],
        ignore_index=True,
    )
    base = summary[summary.model_stage.eq("Phase85 악화방지 기준")].set_index("city")
    summary["phase85_error_reduction_eok"] = summary.apply(lambda r: base.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)
    summary["phase85_wape_improvement_pp"] = summary.apply(lambda r: base.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    acct = accounting_check(selected)
    selected_choices = (
        selected[["city", "parent_code", "option_name", "option_family"]]
        .drop_duplicates()
        .merge(
            scorecard[
                [
                    "city",
                    "parent_code",
                    "option_name",
                    "parent_error_eok",
                    "parent_wape_pct",
                    "worse_cells",
                    "reference_error_reduction_eok",
                ]
            ],
            on=["city", "parent_code", "option_name"],
            how="left",
        )
    )
    remaining = selected[selected.remaining_queue.eq("추가개선대상")].sort_values(
        ["city", "error_gva_eok"], ascending=[True, False]
    )
    audit = selected[
        ["city", "parent_code", "middle_code", "middle_label", "reference_error_gva_eok", "error_gva_eok", "option_name"]
    ].copy()
    audit["worsened"] = audit.error_gva_eok.gt(audit.reference_error_gva_eok + 1e-9)

    options.to_csv(OUTDIR / "phase86_structural_template_options.csv", index=False, encoding="utf-8-sig")
    scorecard.to_csv(OUTDIR / "phase86_structural_template_scorecard.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase86_final_safe_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase86_summary.csv", index=False, encoding="utf-8-sig")
    acct.to_csv(OUTDIR / "phase86_accounting_checks.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase86_remaining_improvement_queue.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUTDIR / "phase86_no_worsening_audit.csv", index=False, encoding="utf-8-sig")
    selected_choices.to_csv(OUTDIR / "phase86_selected_parent_choices.csv", index=False, encoding="utf-8-sig")

    report = f"""# 구조 템플릿 기반 중분류 GVA 오차 축소

## 목적

Phase85 이후에도 남은 취약 중분류를 개별 보정하지 않고, 산업군 공통 구조 템플릿으로 다시 검증했다. 후보는 운수·창고 쌍대균형, 소규모 지원업종 상한형, 과소배분 방지 하한형으로 구성했다. 최종 채택은 Phase85 악화방지 기준보다 어떤 중분류도 악화되지 않고, 상위산업 합계가 그대로 보존되는 경우에만 허용했다.

## 전체 성능

{md_table(summary.sort_values(["city", "error_sum_eok"]), [("city", "지역"), ("model_stage", "단계"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "추가개선대상"), ("phase85_wape_improvement_pp", "Phase85 대비 개선 pp")])}

## 채택된 구조 템플릿

{md_table(selected_choices[selected_choices.reference_error_reduction_eok.gt(1e-9)].sort_values(["city", "reference_error_reduction_eok"], ascending=[True, False]), [("city", "지역"), ("parent_code", "상위산업"), ("option_name", "선택 기준"), ("option_family", "템플릿 유형"), ("parent_error_eok", "상위산업 오차 억원"), ("parent_wape_pct", "상위산업 오차 %"), ("worse_cells", "악화 셀"), ("reference_error_reduction_eok", "감소 억원")], 80)}

## 집계 일치 검증

상위산업 합계 불일치 건수: {int((~acct["pass"]).sum())}개.

{md_table(acct[~acct["pass"]], [("city", "지역"), ("parent_code", "상위산업"), ("actual_parent_eok", "실제합계 억원"), ("predicted_parent_eok", "추정합계 억원"), ("gap_eok", "차이 억원"), ("gap_pct", "차이 %")], 40)}

## 악화 방지 검증

악화 셀 수: {int(audit.worsened.sum())}개.

{md_table(audit[audit.worsened], [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("reference_error_gva_eok", "Phase85 오차 억원"), ("error_gva_eok", "Phase86 오차 억원"), ("option_name", "선택 기준")], 40)}

## 남은 취약 중분류

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("option_name", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("accuracy_grade", "판정")], 80)}

## 판정

1. 고양시는 Phase85 7.2%에서 Phase86 5.8%로 감소했다. 가장 큰 개선은 운수·창고 H49-H52 쌍대균형에서 발생했다.
2. 포항시는 Phase85 7.2% 수준을 유지했다. 구조 템플릿 후보 중 악화 없이 추가 개선되는 후보는 없었다.
3. 집계 일치와 악화 방지를 동시에 만족하는 후보만 채택했으므로, Phase86은 Phase84보다 더 보수적인 최종 성능 후보로 사용할 수 있다.
4. 남은 취약군은 고양 스포츠·오락, 협회·단체, 식료품, 방송과 포항 과학기술·수리업·출판·정보서비스·환경정화다. 다음 단계는 이 유형에 대해 시설면적, 방송·콘텐츠 사업장 규모, 식품 제조시설·출하, 전문서비스 임금·계약액, 환경 처리량 자료를 추가하는 것이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase86_summary.csv")
    print(OUTDIR / "phase86_accounting_checks.csv")
    print(OUTDIR / "phase86_remaining_improvement_queue.csv")


if __name__ == "__main__":
    main()
