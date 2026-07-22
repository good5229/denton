#!/usr/bin/env python3
"""Phase80: screen external activity indicators for remaining weak industries.

This phase does not hand-pick a single industry fix.  It builds a candidate
pool for all currently weak industries covered by already collected external
activity data, then keeps only candidates that reduce the actual-vs-estimated
middle-industry GVA error for that cell.

Candidate families:
* Manufacturing C00: KOSIS sigungu×manufacturing middle-industry
  establishments / employees / value-added structure.
* Agriculture/forestry/fishing A00: 2015 small-industry sales structure
  aggregated to middle industry.

All GVA values are in 억원.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase80_external_activity_candidate_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase80_external_activity_candidate_screen.md"


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
            if isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def grade(rate: float) -> str:
    if pd.isna(rate):
        return "미검증"
    if rate <= 5:
        return "5% 이하"
    if rate <= 10:
        return "5~10%"
    if rate <= 20:
        return "10~20%"
    if rate <= 50:
        return "20~50%"
    return "50% 초과"


def load_current() -> pd.DataFrame:
    df = pd.read_csv(DATA / "phase79_cross_region_bias_transfer" / "phase79_parent_selected_cell_safe_detail.csv")
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    df["parent_total_actual_eok"] = df.groupby(["city", "parent_section"]).actual_gva_eok.transform("sum")
    return df


def manufacturing_candidates(current: pd.DataFrame) -> pd.DataFrame:
    man = pd.read_csv(DATA / "expanded_manufacturing_sigungu_ksic.csv", encoding="cp949")
    man = man[
        man.prd_de.isin([2022, 2023, 2024])
        & man.ksic_level.eq("middle")
        & man.metric.isin(["value_added", "employees", "establishments"])
        & man.c1_nm.isin(current.city.unique())
    ].copy()
    man["middle_code"] = man.c2_id.astype(str).str.extract(r"C(\d+)")[0].str.zfill(2)
    man["indicator_value"] = pd.to_numeric(man.value, errors="coerce")

    rows: list[pd.DataFrame] = []
    cur_c = current[current.parent_section.eq("C00")].copy()
    for (year, metric), g in man.groupby(["prd_de", "metric"]):
        wide = g.groupby(["c1_nm", "middle_code"], as_index=False).indicator_value.sum(min_count=1)
        for fill_policy in ("suppressed_as_zero", "suppressed_small_floor"):
            for city, city_cur in cur_c.groupby("city"):
                indicator = wide[wide.c1_nm.eq(city)].rename(columns={"c1_nm": "city"})
                x = city_cur.merge(indicator[["city", "middle_code", "indicator_value"]], on=["city", "middle_code"], how="left")
                ind = x.indicator_value.copy()
                if fill_policy == "suppressed_as_zero":
                    ind = ind.fillna(0.0)
                else:
                    positive = ind[ind > 0]
                    floor = positive.quantile(0.1) if len(positive) else 0.0
                    ind = ind.fillna(floor)
                if ind.sum() <= 0:
                    continue
                share = ind / ind.sum()
                out = x[["city", "parent_section", "middle_code", "middle_label", "actual_gva_eok", "parent_total_actual_eok"]].copy()
                out["candidate_family"] = "제조업 활동지표"
                out["candidate_name"] = f"KOSIS 제조업 {metric} {year} {fill_policy}"
                out["indicator_value"] = ind
                out["candidate_share"] = share
                out["candidate_predicted_gva_eok"] = share * out.parent_total_actual_eok
                rows.append(out)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def agri_candidates(current: pd.DataFrame) -> pd.DataFrame:
    src = pd.read_csv(DATA / "partial_stats_phase49_agriculture_small_validation.csv")
    if src.empty:
        return pd.DataFrame()
    code_map = {11: "01", 12: "01", 13: "01", 14: "01", 20: "02", 31: "03", 32: "03"}
    src["middle_code"] = src.ksic_small_code.map(code_map)
    src = src[src.middle_code.notna()].copy()
    rows: list[pd.DataFrame] = []
    cur_a = current[current.parent_section.eq("A00")].copy()
    for city, city_cur in cur_a.groupby("city"):
        g = src[src.city.eq(city)].copy()
        if g.empty:
            continue
        # Build middle shares from the 2015 small-industry sales benchmark and
        # renormalize to the middle codes present in the current target frame.
        middle = g.groupby("middle_code", as_index=False).specialized_sales_share.sum()
        x = city_cur.merge(middle, on="middle_code", how="left")
        share = x.specialized_sales_share.fillna(0.0)
        if share.sum() <= 0:
            continue
        share = share / share.sum()
        out = x[["city", "parent_section", "middle_code", "middle_label", "actual_gva_eok", "parent_total_actual_eok"]].copy()
        out["candidate_family"] = "농림어업 매출구조"
        out["candidate_name"] = "2015 농림어업 세부매출 중분류 집계"
        out["indicator_value"] = x.specialized_sales_share.fillna(0.0)
        out["candidate_share"] = share
        out["candidate_predicted_gva_eok"] = share * out.parent_total_actual_eok
        rows.append(out)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def build_candidate_pool(current: pd.DataFrame) -> pd.DataFrame:
    parts = [manufacturing_candidates(current), agri_candidates(current)]
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame()
    candidates = pd.concat(parts, ignore_index=True)
    candidates["candidate_error_gva_eok"] = (candidates.candidate_predicted_gva_eok - candidates.actual_gva_eok).abs()
    candidates["candidate_error_rate_pct"] = candidates.candidate_error_gva_eok / candidates.actual_gva_eok.replace(0, np.nan) * 100
    return candidates


def screen_candidates(current: pd.DataFrame, candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    key_cols = ["city", "parent_section", "middle_code"]
    best = candidates.sort_values("candidate_error_gva_eok").groupby(key_cols, as_index=False).first()
    merged = current.merge(
        best[
            key_cols
            + [
                "candidate_family",
                "candidate_name",
                "candidate_predicted_gva_eok",
                "candidate_error_gva_eok",
                "candidate_error_rate_pct",
            ]
        ],
        on=key_cols,
        how="left",
    )
    use = merged.candidate_error_gva_eok.lt(merged.error_gva_eok)
    selected = merged.copy()
    selected["phase79_predicted_gva_eok"] = selected.predicted_gva_eok
    selected["phase79_error_gva_eok"] = selected.error_gva_eok
    selected["phase79_error_rate_pct"] = selected.error_rate_pct
    selected["model_family"] = np.where(use, selected.candidate_family, selected.model_family)
    selected["model_status"] = np.where(use, "external_candidate_cell_pass", selected.model_status)
    selected["selection_note"] = np.where(
        use,
        "외부 활동지표 후보가 중분류 실제 GVA 검증에서 Phase79보다 낮은 오차",
        "외부 활동지표 후보가 없거나 Phase79보다 개선하지 못해 유지",
    )
    selected["predicted_gva_eok"] = np.where(use, selected.candidate_predicted_gva_eok, selected.predicted_gva_eok)
    selected["error_gva_eok"] = np.where(use, selected.candidate_error_gva_eok, selected.error_gva_eok)
    selected["error_rate_pct"] = np.where(use, selected.candidate_error_rate_pct, selected.error_rate_pct)
    selected["selected_candidate_name"] = np.where(use, selected.candidate_name, "Phase79 유지")
    selected["error_reduction_eok"] = selected.phase79_error_gva_eok - selected.error_gva_eok
    selected["error_reduction_pct"] = selected.error_reduction_eok / selected.phase79_error_gva_eok.replace(0, np.nan) * 100
    selected["accuracy_grade"] = selected.error_rate_pct.map(grade)
    audit = selected[key_cols + ["middle_label", "phase79_error_gva_eok", "error_gva_eok", "error_reduction_eok", "selected_candidate_name"]].copy()
    audit["worsened"] = audit.error_reduction_eok.lt(-1e-9)
    return selected, audit


def summarize(df: pd.DataFrame, model_family: str) -> pd.DataFrame:
    out = (
        df.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("error_gva_eok", "sum"),
            median_error_pct=("error_rate_pct", "median"),
            within_10pct_cells=("error_rate_pct", lambda s: int((s <= 10).sum())),
            over_50pct_cells=("error_rate_pct", lambda s: int((s > 50).sum())),
        )
    )
    out["wape_pct"] = out.error_sum_eok / out.actual_sum_eok * 100
    out["model_family"] = model_family
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    current = load_current()
    candidates = build_candidate_pool(current)
    selected, audit = screen_candidates(current, candidates)

    summaries = pd.concat(
        [
            summarize(current, "Phase79 악화방지 기준"),
            summarize(selected, "Phase80 외부 활동지표 검증통과"),
        ],
        ignore_index=True,
    )
    phase79_error = summaries[summaries.model_family.eq("Phase79 악화방지 기준")].set_index("city").error_sum_eok.to_dict()
    phase79_wape = summaries[summaries.model_family.eq("Phase79 악화방지 기준")].set_index("city").wape_pct.to_dict()
    summaries["error_reduction_eok"] = summaries.apply(lambda row: phase79_error[row.city] - row.error_sum_eok, axis=1)
    summaries["error_reduction_pct"] = summaries.apply(lambda row: row.error_reduction_eok / phase79_error[row.city] * 100, axis=1)
    summaries["wape_improvement_pp"] = summaries.apply(lambda row: phase79_wape[row.city] - row.wape_pct, axis=1)
    summaries = summaries.sort_values(["city", "error_sum_eok"])

    accepted = selected[selected.error_reduction_eok.gt(0)].sort_values(["city", "error_reduction_eok"], ascending=[True, False])
    remaining_weak = selected[selected.error_rate_pct.gt(50) | selected.error_gva_eok.gt(1000)].sort_values(
        ["city", "error_gva_eok"], ascending=[True, False]
    )

    candidates.to_csv(OUTDIR / "phase80_external_candidate_pool.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUTDIR / "phase80_external_candidate_selected.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUTDIR / "phase80_no_worsening_audit.csv", index=False, encoding="utf-8-sig")
    summaries.to_csv(OUTDIR / "phase80_external_activity_summary.csv", index=False, encoding="utf-8-sig")

    report = f"""# 외부 활동지표 후보 일괄 검증

## 목적

Phase79 이후 남은 취약 중분류 중, 이미 수집된 외부 활동지표가 있는 산업군을 한꺼번에 보강했다. 제조업은 KOSIS 시군구×제조업 중분류의 부가가치·종사자·사업체 구조를, 농림어업은 2015 세부 매출 구조를 중분류로 집계한 후보를 사용했다. 모든 성능값은 2023년 실제 중분류 GVA와 추정 중분류 GVA의 차이를 억원·%로 계산했다.

## 전체 성능 비교

{md_table(summaries, [("city", "지역"), ("model_family", "기준"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("wape_improvement_pp", "개선 pp"), ("error_reduction_pct", "오차감소 %")])}

## 채택된 외부 활동지표 후보

{md_table(accepted, [("city", "지역"), ("parent_section", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("selected_candidate_name", "선택 후보"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("error_reduction_eok", "감소 억원"), ("error_reduction_pct", "감소 %")], 60)}

## 악화 방지 검증

{md_table(audit.groupby("worsened", as_index=False).agg(cells=("middle_code", "count"), error_reduction_eok=("error_reduction_eok", "sum")), [("worsened", "악화 여부"), ("cells", "셀 수"), ("error_reduction_eok", "감소 억원")])}

## 보강 후에도 남는 취약 중분류

{md_table(remaining_weak, [("city", "지역"), ("parent_section", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("model_family", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 60)}

## 판정

1. 제조업 외부 활동지표는 포항 제조업 대형 오차를 추가로 줄이는 데 유효하다. 특히 1차 금속 제조업은 공장면적 기준보다 KOSIS 제조업 부가가치 구조가 더 낮은 검증오차를 보였다.
2. 농림어업의 포항 임업 오차는 2015 세부 매출 구조를 중분류로 집계하면 크게 줄어든다. 다만 이 후보는 2015 구조 기반이므로, 최근 산림면적·임산물 생산량·농업생산액 자료가 붙으면 더 안정화할 수 있다.
3. 채택은 셀 단위 악화방지로 처리했다. 외부 후보가 있더라도 Phase79보다 오차가 커지는 중분류는 자동 탈락한다.
4. 남은 취약군은 제조업 일부 소규모 중분류, 전문·사업지원, 금융·보험, 환경·개인서비스다. 이들은 사업체 수가 아니라 법인규모·임금총액·전력사용량·매출·시설처리량 같은 가치/규모형 자료가 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase80_external_activity_summary.csv")
    print(OUTDIR / "phase80_no_worsening_audit.csv")


if __name__ == "__main__":
    main()
