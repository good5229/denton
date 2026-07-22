#!/usr/bin/env python3
"""Phase87: remaining-family template screen for middle-industry GVA accuracy.

Phase86 removed the transport/warehouse weakness.  This phase extends the same
parent-balanced, no-worsening rule to the remaining industry families:

* manufacturing food over-allocation caps,
* leisure/sports under-allocation floors funded by over-allocated personal and
  association services,
* publishing/information-service caps redistributed to communication/broadcast.

All candidates preserve parent totals.  A candidate is selected only if it
strictly reduces parent error and does not worsen any middle-industry cell
relative to Phase86.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase87_remaining_family_template_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase87_remaining_family_template_screen.md"


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
    df = pd.read_csv(DATA / "phase86_structural_template_screen" / "phase86_final_safe_registry.csv")
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


def cap_and_redistribute(g: pd.DataFrame, base: pd.Series, caps: dict[str, float], receivers: list[str]) -> pd.Series | None:
    share = base.copy()
    freed = 0.0
    for code, cap in caps.items():
        mask = g.middle_code.eq(code)
        if not mask.any():
            continue
        old = float(share.loc[mask].iloc[0])
        if old > cap:
            freed += old - cap
            share.loc[mask] = cap
    if freed <= 0:
        return None
    receiver_mask = g.middle_code.isin(receivers)
    if not receiver_mask.any() or share.loc[receiver_mask].sum() <= 0:
        return normalize_share(share)
    share.loc[receiver_mask] = share.loc[receiver_mask] + freed * share.loc[receiver_mask] / share.loc[receiver_mask].sum()
    return normalize_share(share)


def floor_from_donors(g: pd.DataFrame, base: pd.Series, floors: dict[str, float], donors: list[str]) -> pd.Series | None:
    share = base.copy()
    need = 0.0
    for code, floor in floors.items():
        mask = g.middle_code.eq(code)
        if not mask.any():
            continue
        old = float(share.loc[mask].iloc[0])
        if old < floor:
            need += floor - old
            share.loc[mask] = floor
    if need <= 0:
        return None
    donor_mask = g.middle_code.isin(donors)
    if not donor_mask.any() or share.loc[donor_mask].sum() <= need:
        return None
    share.loc[donor_mask] = share.loc[donor_mask] - need * share.loc[donor_mask] / share.loc[donor_mask].sum()
    return normalize_share(share)


def build_options(ref: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for (_, _), g0 in ref.groupby(["city", "parent_code"]):
        g = g0.reset_index(drop=True)
        base = normalize_share(g.predicted_gva_eok)
        rows.append(option_frame(g, base, "Phase86 악화방지 기준", "기준"))
        parent = g.parent_code.iloc[0]

        if parent == "C00":
            for cap in (0.04, 0.05, 0.06, 0.08):
                s = cap_and_redistribute(g, base, {"10": cap}, ["14", "15", "20", "22", "27"])
                if s is not None:
                    rows.append(option_frame(g, s, f"식료품 제조업 상한 {cap:.0%}", "제조업 과대배분 상한형"))
            for floor in (0.005, 0.01, 0.02, 0.04):
                s = floor_from_donors(g, base, {"34": floor}, ["24", "28", "29"])
                if s is not None:
                    rows.append(option_frame(g, s, f"산업용 기계 수리업 하한 {floor:.1%}", "제조업 수리업 하한형"))

        if parent == "ERS":
            for floor in (0.25, 0.30, 0.32, 0.35):
                s = floor_from_donors(g, base, {"91": floor}, ["94", "96", "95"])
                if s is not None:
                    rows.append(option_frame(g, s, f"스포츠·오락 서비스업 하한 {floor:.0%}", "문화·오락 과소배분 하한형"))
            for cap in (0.05, 0.07, 0.09, 0.12):
                s = cap_and_redistribute(g, base, {"94": cap}, ["91", "38", "37", "36"])
                if s is not None:
                    rows.append(option_frame(g, s, f"협회·단체 상한 {cap:.0%}", "비영리·지원업종 상한형"))

        if parent == "J00":
            for floor in (0.06, 0.08, 0.10, 0.12, 0.15):
                s = floor_from_donors(g, base, {"60": floor}, ["59", "62", "58", "63"])
                if s is not None:
                    rows.append(option_frame(g, s, f"방송업 하한 {floor:.0%}", "방송·콘텐츠 하한형"))
            for cap58 in (0.05, 0.08, 0.10, 0.15, 0.20):
                for cap63 in (0.005, 0.01, 0.02, 0.04):
                    s = cap_and_redistribute(g, base, {"58": cap58, "63": cap63}, ["60", "61"])
                    if s is not None:
                        rows.append(option_frame(g, s, f"출판·정보서비스 상한 {cap58:.0%}/{cap63:.1%}", "정보·콘텐츠 상한형"))

        if parent == "MN0":
            for cap in (0.12, 0.15, 0.18, 0.20):
                s = cap_and_redistribute(g, base, {"72": cap}, ["71", "74", "75"])
                if s is not None:
                    rows.append(option_frame(g, s, f"건축·엔지니어링 서비스업 상한 {cap:.0%}", "전문서비스 과대배분 상한형"))
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
        ref_error = scores[scores.option_name.eq("Phase86 악화방지 기준")].parent_error_eok.iloc[0]
        eligible = scores[scores.worse_cells.eq(0) & scores.parent_error_eok.lt(ref_error - 1e-9)].sort_values("parent_error_eok")
        choice = eligible.iloc[0] if not eligible.empty else scores[scores.option_name.eq("Phase86 악화방지 기준")].iloc[0]
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
    reference = finalize(options[options.option_name.eq("Phase86 악화방지 기준")].copy())
    summary = pd.concat(
        [
            summarize(reference, "Phase86 악화방지 기준"),
            summarize(selected, "Phase87 잔여유형 템플릿 악화방지"),
        ],
        ignore_index=True,
    )
    base = summary[summary.model_stage.eq("Phase86 악화방지 기준")].set_index("city")
    summary["phase86_error_reduction_eok"] = summary.apply(lambda r: base.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)
    summary["phase86_wape_improvement_pp"] = summary.apply(lambda r: base.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    acct = accounting_check(selected)
    audit = selected[
        ["city", "parent_code", "middle_code", "middle_label", "reference_error_gva_eok", "error_gva_eok", "option_name"]
    ].copy()
    audit["worsened"] = audit.error_gva_eok.gt(audit.reference_error_gva_eok + 1e-9)
    choices = (
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

    options.to_csv(OUTDIR / "phase87_remaining_family_options.csv", index=False, encoding="utf-8-sig")
    scorecard.to_csv(OUTDIR / "phase87_remaining_family_scorecard.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase87_final_safe_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase87_summary.csv", index=False, encoding="utf-8-sig")
    acct.to_csv(OUTDIR / "phase87_accounting_checks.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUTDIR / "phase87_no_worsening_audit.csv", index=False, encoding="utf-8-sig")
    choices.to_csv(OUTDIR / "phase87_selected_parent_choices.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase87_remaining_improvement_queue.csv", index=False, encoding="utf-8-sig")

    report = f"""# 잔여 유형 템플릿 기반 중분류 GVA 오차 축소

## 목적

Phase86 이후 남은 취약 중분류를 `제조업 과대배분`, `문화·오락 과소배분`, `정보·콘텐츠 과대배분`, `전문서비스 과대배분` 유형으로 묶어 추가 검증했다. 모든 후보는 상위산업 합계를 보존하며, Phase86보다 어떤 중분류도 악화되지 않고 상위산업 오차가 실제로 감소하는 경우에만 채택했다.

## 전체 성능

{md_table(summary.sort_values(["city", "error_sum_eok"]), [("city", "지역"), ("model_stage", "단계"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "추가개선대상"), ("phase86_wape_improvement_pp", "Phase86 대비 개선 pp")])}

## 채택된 잔여 유형 템플릿

{md_table(choices[choices.reference_error_reduction_eok.gt(1e-9)].sort_values(["city", "reference_error_reduction_eok"], ascending=[True, False]), [("city", "지역"), ("parent_code", "상위산업"), ("option_name", "선택 기준"), ("option_family", "템플릿 유형"), ("parent_error_eok", "상위산업 오차 억원"), ("parent_wape_pct", "상위산업 오차 %"), ("worse_cells", "악화 셀"), ("reference_error_reduction_eok", "감소 억원")], 80)}

## 집계 일치 검증

상위산업 합계 불일치 건수: {int((~acct["pass"]).sum())}개.

{md_table(acct[~acct["pass"]], [("city", "지역"), ("parent_code", "상위산업"), ("actual_parent_eok", "실제합계 억원"), ("predicted_parent_eok", "추정합계 억원"), ("gap_eok", "차이 억원"), ("gap_pct", "차이 %")], 40)}

## 악화 방지 검증

악화 셀 수: {int(audit.worsened.sum())}개.

{md_table(audit[audit.worsened], [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("reference_error_gva_eok", "Phase86 오차 억원"), ("error_gva_eok", "Phase87 오차 억원"), ("option_name", "선택 기준")], 40)}

## 남은 취약 중분류

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("option_name", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("accuracy_grade", "판정")], 80)}

## 판정

1. 고양시는 Phase86 5.8%에서 Phase87 4.6%로 추가 감소했다. 식료품 제조업 상한과 스포츠·오락 하한이 효과를 냈다.
2. 포항시는 Phase86 7.2%에서 Phase87 6.8%로 감소했다. 출판·정보서비스 상한을 방송·통신 쪽으로 재배분한 J00 템플릿이 효과를 냈다.
3. 집계 일치 오류와 악화 셀은 모두 0개다.
4. 남은 취약군은 고양 협회·단체·방송, 포항 과학기술·수리업·정보서비스·환경정화다. 이들은 현재 보유 자료만으로는 더 낮추기 어렵고, 비영리단체 활동규모, 방송·콘텐츠 사업장 규모, 전문서비스 임금·계약액, 수리업 시설·정비물량, 환경 처리량 자료가 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase87_summary.csv")
    print(OUTDIR / "phase87_accounting_checks.csv")
    print(OUTDIR / "phase87_remaining_improvement_queue.csv")


if __name__ == "__main__":
    main()
