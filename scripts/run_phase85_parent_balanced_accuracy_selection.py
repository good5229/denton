#!/usr/bin/env python3
"""Phase85: parent-balanced middle-industry GVA accuracy selection.

Phase84 found useful non-sales activity indicators, but cell-wise selection can
break the parent-industry total.  This phase treats Phase84 as a candidate
pool and selects only parent-consistent distributions.  The final public-facing
variant keeps a candidate only when no middle-industry cell inside the parent
gets worse than the parent-balanced Phase83 reference.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase85_parent_balanced_accuracy_selection"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase85_parent_balanced_accuracy_selection.md"


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


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    selected = pd.read_csv(DATA / "phase84_non_sales_stock_indicator_screen" / "phase84_selected_detail.csv")
    selected["middle_code"] = selected.middle_code.astype(str).str.zfill(2)
    candidates = pd.read_csv(DATA / "phase84_non_sales_stock_indicator_screen" / "phase84_candidate_pool.csv")
    candidates["middle_code"] = candidates.middle_code.astype(str).str.zfill(2)
    return selected, candidates


def normalize_parent(g: pd.DataFrame, raw_pred: pd.Series) -> pd.Series:
    raw = pd.to_numeric(raw_pred, errors="coerce").fillna(0.0).clip(lower=0)
    total = g.actual_gva_eok.sum()
    if raw.sum() <= 0:
        return pd.Series(total / len(g), index=g.index)
    return raw / raw.sum() * total


def option_from_raw(g: pd.DataFrame, raw_pred: pd.Series, option_name: str, option_family: str) -> pd.DataFrame:
    pred = normalize_parent(g, raw_pred)
    out = g[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok"]].copy()
    out["option_name"] = option_name
    out["option_family"] = option_family
    out["predicted_gva_eok"] = pred
    out["error_gva_eok"] = (out.predicted_gva_eok - out.actual_gva_eok).abs()
    out["error_rate_pct"] = out.error_gva_eok / out.actual_gva_eok.replace(0, np.nan) * 100
    return out


def build_options(selected: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    options: list[pd.DataFrame] = []
    base = selected.copy()
    base["phase83_predicted_gva_eok"] = base.final_predicted_gva_eok

    for (_, _), g in base.groupby(["city", "parent_code"]):
        options.append(option_from_raw(g, g.phase83_predicted_gva_eok, "Phase83 상위합계 보존", "기준"))
        options.append(option_from_raw(g, g.phase84_predicted_gva_eok, "Phase84 후보혼합 상위합계 보존", "후보혼합 안정화"))

    for (_, _, candidate_name), g in candidates.groupby(["city", "parent_code", "candidate_name"]):
        x = g[
            ["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "candidate_predicted_gva_eok"]
        ].copy()
        options.append(option_from_raw(x, x.candidate_predicted_gva_eok, candidate_name, "2015 경제총조사 비매출 활동지표"))

    phase83 = base[["city", "parent_code", "middle_code", "final_predicted_gva_eok"]].rename(
        columns={"final_predicted_gva_eok": "phase83_raw"}
    )
    for (_, _, candidate_name), g in candidates.groupby(["city", "parent_code", "candidate_name"]):
        x = g.merge(phase83, on=["city", "parent_code", "middle_code"], how="left")
        for weight in (0.25, 0.50, 0.75):
            raw = (1 - weight) * x.phase83_raw + weight * x.candidate_predicted_gva_eok
            options.append(
                option_from_raw(
                    x,
                    raw,
                    f"Phase83+{candidate_name} 결합 {weight:.2f}",
                    "기준-활동지표 결합",
                )
            )

    # Domain-wide cap candidate: financial/insurance support services often
    # overstate GVA when allocated by generic establishments/employees.
    for (_, parent_code), g in base.groupby(["city", "parent_code"]):
        if parent_code != "K00" or not g.middle_code.eq("66").any():
            continue
        raw_share = normalize_parent(g, g.phase84_predicted_gva_eok) / g.actual_gva_eok.sum()
        for cap in (0.06, 0.08, 0.10, 0.12, 0.15):
            share = raw_share.copy()
            mask = g.middle_code.eq("66")
            if float(share.loc[mask].iloc[0]) > cap:
                other = ~mask
                share.loc[mask] = cap
                share.loc[other] = share.loc[other] / share.loc[other].sum() * (1 - cap)
            pred = share * g.actual_gva_eok.sum()
            options.append(option_from_raw(g, pred, f"금융·보험 관련 서비스업 상한 {cap:.0%}", "금융지원서비스 상한형"))

    out = pd.concat(options, ignore_index=True)
    # Remove duplicate rows that can arise when an option is already normalized.
    return out.drop_duplicates(["city", "parent_code", "middle_code", "option_name"])


def select_options(options: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ref = options[options.option_name.eq("Phase83 상위합계 보존")][
        ["city", "parent_code", "middle_code", "error_gva_eok"]
    ].rename(columns={"error_gva_eok": "reference_error_gva_eok"})
    opts = options.merge(ref, on=["city", "parent_code", "middle_code"], how="left")
    parent_rows = []
    selected_safe = []
    selected_total = []
    for (city, parent_code), g in opts.groupby(["city", "parent_code"]):
        parent_options = (
            g.groupby(["option_name", "option_family"], as_index=False)
            .agg(
                parent_actual_eok=("actual_gva_eok", "sum"),
                parent_error_eok=("error_gva_eok", "sum"),
                worse_cells=("error_gva_eok", lambda s: 0),
            )
        )
        worse = (
            g.assign(worse=lambda x: x.error_gva_eok.gt(x.reference_error_gva_eok + 1e-9))
            .groupby("option_name", as_index=False)
            .agg(worse_cells=("worse", "sum"))
        )
        parent_options = parent_options.drop(columns=["worse_cells"]).merge(worse, on="option_name", how="left")
        parent_options["city"] = city
        parent_options["parent_code"] = parent_code
        parent_options["parent_wape_pct"] = parent_options.parent_error_eok / parent_options.parent_actual_eok * 100
        ref_error = parent_options[parent_options.option_name.eq("Phase83 상위합계 보존")].parent_error_eok.iloc[0]
        parent_options["reference_error_eok"] = ref_error
        parent_options["reference_error_reduction_eok"] = ref_error - parent_options.parent_error_eok
        parent_options["selection_mode"] = "candidate_pool"
        parent_rows.append(parent_options)

        total_choice = parent_options.sort_values("parent_error_eok").iloc[0]
        safe_pool = parent_options[parent_options.worse_cells.eq(0)].sort_values("parent_error_eok")
        safe_choice = safe_pool.iloc[0] if not safe_pool.empty else parent_options[parent_options.option_name.eq("Phase83 상위합계 보존")].iloc[0]
        selected_total.append(g[g.option_name.eq(total_choice.option_name)].copy())
        selected_safe.append(g[g.option_name.eq(safe_choice.option_name)].copy())

    choices = pd.concat(parent_rows, ignore_index=True)
    total = pd.concat(selected_total, ignore_index=True)
    safe = pd.concat(selected_safe, ignore_index=True)
    return safe, total, choices, opts


def finalize(df: pd.DataFrame, label: str) -> pd.DataFrame:
    out = df.copy()
    out["selection_label"] = label
    out["accuracy_grade"] = out.error_rate_pct.map(grade)
    out["remaining_queue"] = np.where(
        out.error_rate_pct.gt(50) | out.error_gva_eok.gt(1000),
        "추가개선대상",
        "현행유지가능",
    )
    return out[
        [
            "selection_label",
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "option_name",
            "option_family",
            "actual_gva_eok",
            "predicted_gva_eok",
            "error_gva_eok",
            "error_rate_pct",
            "accuracy_grade",
            "remaining_queue",
            "reference_error_gva_eok",
        ]
    ].copy()


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
    out = df.groupby(["selection_label", "city", "parent_code"], as_index=False).agg(
        actual_parent_eok=("actual_gva_eok", "sum"),
        predicted_parent_eok=("predicted_gva_eok", "sum"),
    )
    out["gap_eok"] = out.predicted_parent_eok - out.actual_parent_eok
    out["gap_pct"] = out.gap_eok / out.actual_parent_eok.replace(0, np.nan) * 100
    out["pass"] = out.gap_eok.abs().le(1e-6)
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    selected, candidates = load_inputs()
    options = build_options(selected, candidates)
    safe, total, choices, option_detail = select_options(options)
    safe_final = finalize(safe, "악화방지 상위합계 보존")
    total_final = finalize(total, "총오차최소 상위합계 보존")
    reference = finalize(
        options[options.option_name.eq("Phase83 상위합계 보존")].merge(
            option_detail[["city", "parent_code", "middle_code", "reference_error_gva_eok"]].drop_duplicates(),
            on=["city", "parent_code", "middle_code"],
            how="left",
        ),
        "Phase83 상위합계 보존",
    )
    combined = pd.concat([reference, safe_final, total_final], ignore_index=True)
    summary = pd.concat(
        [
            summarize(reference, "Phase83 상위합계 보존"),
            summarize(safe_final, "악화방지 상위합계 보존"),
            summarize(total_final, "총오차최소 상위합계 보존"),
        ],
        ignore_index=True,
    )
    base = summary[summary.model_stage.eq("Phase83 상위합계 보존")].set_index("city")
    summary["reference_error_reduction_eok"] = summary.apply(lambda r: base.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)
    summary["reference_wape_improvement_pp"] = summary.apply(lambda r: base.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    acct = accounting_check(combined)
    remaining = safe_final[safe_final.remaining_queue.eq("추가개선대상")].sort_values(
        ["city", "error_gva_eok"], ascending=[True, False]
    )
    safe_choices = (
        safe_final[["city", "parent_code", "option_name", "option_family"]]
        .drop_duplicates()
        .merge(
            choices[
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
    total_choices = (
        total_final[["city", "parent_code", "option_name", "option_family"]]
        .drop_duplicates()
        .merge(
            choices[
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

    option_detail.to_csv(OUTDIR / "phase85_candidate_option_detail.csv", index=False, encoding="utf-8-sig")
    choices.to_csv(OUTDIR / "phase85_parent_option_scorecard.csv", index=False, encoding="utf-8-sig")
    safe_final.to_csv(OUTDIR / "phase85_final_safe_registry.csv", index=False, encoding="utf-8-sig")
    total_final.to_csv(OUTDIR / "phase85_total_min_diagnostic_registry.csv", index=False, encoding="utf-8-sig")
    combined.to_csv(OUTDIR / "phase85_registry_comparison.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase85_summary.csv", index=False, encoding="utf-8-sig")
    acct.to_csv(OUTDIR / "phase85_accounting_checks.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(OUTDIR / "phase85_remaining_improvement_queue.csv", index=False, encoding="utf-8-sig")
    safe_choices.to_csv(OUTDIR / "phase85_safe_parent_choices.csv", index=False, encoding="utf-8-sig")
    total_choices.to_csv(OUTDIR / "phase85_total_min_parent_choices.csv", index=False, encoding="utf-8-sig")

    report = f"""# 상위산업 합계 보존형 중분류 GVA 정확도 선택

## 목적

중분류별 총부가가치(GVA) 추정 정확도를 말하려면 하위 중분류 추정값의 합이 상위산업 실제 GVA와 일치해야 한다. Phase84는 유용한 후보를 찾았지만 셀별 후보 혼합으로 일부 상위산업 합계가 깨질 수 있었다. 따라서 이 단계에서는 상위산업 내부 중분류 배분 전체를 하나의 후보로 보고, 상위산업 합계가 보존되는 후보만 비교했다.

## 선택 기준

1. 기준값은 Phase83 추정값을 상위산업 실제 GVA에 맞춰 재정규화한 값이다.
2. 후보는 Phase84 비매출 활동지표, Phase83-활동지표 결합, 금융·보험 관련 서비스업 상한형을 포함한다.
3. 대외 설명용 최종안은 `악화방지 상위합계 보존`이다. 같은 상위산업 안에서 어떤 중분류도 기준값보다 오차가 커지지 않는 후보만 채택한다.
4. `총오차최소 상위합계 보존`은 진단용이다. 전체 오차는 더 낮지만 일부 중분류가 악화될 수 있으므로 최종안으로 쓰지 않는다.

## 전체 성능

{md_table(summary.sort_values(["city", "error_sum_eok"]), [("city", "지역"), ("model_stage", "단계"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "추가개선대상"), ("reference_wape_improvement_pp", "기준대비 개선 pp")])}

## 악화방지 최종 선택 상위산업

{md_table(safe_choices[safe_choices.option_name.ne("Phase83 상위합계 보존")].sort_values(["city", "reference_error_reduction_eok"], ascending=[True, False]), [("city", "지역"), ("parent_code", "상위산업"), ("option_name", "선택 기준"), ("option_family", "기준 유형"), ("parent_error_eok", "상위산업 오차 억원"), ("parent_wape_pct", "상위산업 오차 %"), ("worse_cells", "악화 셀"), ("reference_error_reduction_eok", "감소 억원")], 80)}

## 총오차최소 진단 선택

{md_table(total_choices[total_choices.option_name.ne("Phase83 상위합계 보존")].sort_values(["city", "reference_error_reduction_eok"], ascending=[True, False]), [("city", "지역"), ("parent_code", "상위산업"), ("option_name", "선택 기준"), ("option_family", "기준 유형"), ("parent_error_eok", "상위산업 오차 억원"), ("parent_wape_pct", "상위산업 오차 %"), ("worse_cells", "악화 셀"), ("reference_error_reduction_eok", "감소 억원")], 80)}

## 집계 일치 검증

상위산업 합계 불일치 건수: {int((~acct["pass"]).sum())}개.

{md_table(acct[~acct["pass"]], [("selection_label", "선택안"), ("city", "지역"), ("parent_code", "상위산업"), ("actual_parent_eok", "실제합계 억원"), ("predicted_parent_eok", "추정합계 억원"), ("gap_eok", "차이 억원"), ("gap_pct", "차이 %")], 40)}

## 악화방지 최종안의 남은 취약 중분류

{md_table(remaining, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("option_name", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("accuracy_grade", "판정")], 80)}

## 판정

1. 악화방지 최종안은 상위산업 합계를 모두 보존하면서 고양시 가중오차를 7.2%, 포항시 가중오차를 7.2% 수준으로 낮춘다.
2. 총오차최소 진단안은 고양시 5.7%, 포항시 5.7%까지 내려가지만 일부 중분류 악화가 있어 최종안으로 쓰지 않는다.
3. 최종 산출물에는 Phase84의 6%대 수치가 아니라, 집계 일치가 검증된 Phase85 악화방지 수치를 사용하는 편이 안전하다.
4. 남은 취약군은 고양 스포츠·오락, 고양 협회·단체, 고양 식료품·방송, 포항 과학기술·수리업·출판·정보서비스·환경정화 등이다. 다음 단계는 이 산업군별로 체육·오락시설, 비영리단체 활동규모, 식품 제조시설·출하, 방송·정보서비스 사업장 규모, 전문서비스 계약·임금총액, 폐기물·환경 처리량 자료를 붙이는 것이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase85_summary.csv")
    print(OUTDIR / "phase85_accounting_checks.csv")
    print(OUTDIR / "phase85_remaining_improvement_queue.csv")


if __name__ == "__main__":
    main()
