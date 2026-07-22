#!/usr/bin/env python3
"""Phase94: direct activity-source screen for grouped weak middle industries.

Phase93 showed that cross-city pattern transfer cannot be adopted when every
middle industry must be non-worsening.  This phase screens local direct
activity sources that are already available in the workspace.  Candidates are
applied by source family and city/cause group, then parent totals are
renormalised.  A candidate is "strict-adoptable" only when no middle-industry
cell in the city worsens.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE92 = DATA / "phase92_current_accuracy_after_grouped_transfer"
OUTDIR = DATA / "phase94_direct_activity_source_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase94_direct_activity_source_screen.md"


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    try:
        return pd.read_csv(path, **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", **kwargs)


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


def load_registry() -> pd.DataFrame:
    df = read_csv(PHASE92 / "phase92_current_middle_industry_accuracy_registry.csv")
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    df["current_predicted_gva_eok"] = df.phase92_predicted_gva_eok
    df["current_error_gva_eok"] = df.phase92_error_gva_eok
    df["current_error_rate_pct"] = df.phase92_error_rate_pct
    df["current_gap_to_10pct_eok"] = df.phase92_gap_to_10pct_eok
    return df


def indicator_sources(reg: pd.DataFrame) -> pd.DataFrame:
    rows = []

    # KOSIS manufacturing/mining middle-industry structure.  Use 2021 only as
    # release-lag eligible for a 2023 target according to the local metadata.
    kosis_path = DATA / "business_employment_feature_table.csv"
    if kosis_path.exists():
        k = read_csv(kosis_path)
        k = k[k.area_name.isin(["고양시", "포항시"]) & k.year.eq(2021)].copy()
        k["middle_code"] = k.industry_code.astype(str).str.extract(r"(\d{2})")[0]
        k = k[k.middle_code.notna()]
        for r in k.itertuples():
            rows.append(
                {
                    "source_id": f"kosis_mfg_2021_{r.metric}",
                    "source_label": f"KOSIS 제조·광업 2021 {r.metric}",
                    "city": r.area_name,
                    "middle_code": str(r.middle_code).zfill(2),
                    "indicator_value": float(r.value),
                    "source_status": "lag_eligible_structural_activity",
                    "source_family": "생산시설형",
                }
            )

    # Pohang 2024 municipal business survey: after-target activity diagnostic.
    pohang_survey_path = DATA / "partial_stats_phase43_pohang_gu_sales_cv_detail.csv"
    if pohang_survey_path.exists():
        p = read_csv(pohang_survey_path, dtype={"division_code": str})
        for metric in ["establishments", "employees", "sales"]:
            agg = p.groupby("division_code", as_index=False)[metric].sum()
            for r in agg.itertuples():
                rows.append(
                    {
                        "source_id": f"pohang_business_2024_{metric}",
                        "source_label": f"포항 2024 사업체조사 {metric}",
                        "city": "포항시",
                        "middle_code": str(r.division_code).zfill(2),
                        "indicator_value": float(getattr(r, metric)),
                        "source_status": "after_target_diagnostic",
                        "source_family": "전 산업 직접조사",
                    }
                )

    # Pohang factory registration middle-industry count.
    factory_path = DATA / "partial_stats_phase43_pohang_factory_industry_mapping.csv"
    if factory_path.exists():
        f = read_csv(factory_path)
        f = f[f.division_code.notna()].copy()
        f["middle_code"] = f.division_code.astype(float).astype(int).astype(str).str.zfill(2)
        metrics = {
            "factory_rows": f.groupby("middle_code").size(),
            "factory_spatial_matched_rows": f[f.matched_for_spatial_model.astype(str).str.lower().eq("true")].groupby("middle_code").size(),
        }
        for metric, series in metrics.items():
            for middle_code, value in series.items():
                rows.append(
                    {
                        "source_id": f"pohang_factory_{metric}",
                        "source_label": f"포항 공장등록 {metric}",
                        "city": "포항시",
                        "middle_code": str(middle_code).zfill(2),
                        "indicator_value": float(value),
                        "source_status": "current_snapshot_activity",
                        "source_family": "생산시설형",
                    }
                )

    ind = pd.DataFrame(rows)
    if ind.empty:
        return ind
    meta = reg[["city", "middle_code", "parent_code", "cause_group"]].drop_duplicates()
    ind = ind.merge(meta, on=["city", "middle_code"], how="inner")
    return ind[ind.indicator_value.gt(0)].copy()


def renormalise_parent(df: pd.DataFrame, raw_col: str) -> pd.Series:
    raw = df[raw_col].clip(lower=0)
    parent_total = df.groupby(["city", "parent_code"]).actual_gva_eok.transform("sum")
    denom = raw.groupby([df.city, df.parent_code]).transform("sum")
    return raw / denom.replace(0, np.nan) * parent_total


def evaluate_candidate(reg: pd.DataFrame, ind: pd.DataFrame, source_id: str, city: str, cause_group: str) -> tuple[dict, pd.DataFrame]:
    base = reg.copy()
    source = ind[ind.source_id.eq(source_id) & ind.city.eq(city)].copy()
    target_codes = set(source[source.cause_group.eq(cause_group)].middle_code)
    apply_mask = base.city.eq(city) & base.middle_code.isin(target_codes)
    x = base.merge(source[["middle_code", "indicator_value"]], on="middle_code", how="left")
    x["candidate_raw_pred"] = x.current_predicted_gva_eok
    x.loc[apply_mask, "candidate_raw_pred"] = x.loc[apply_mask, "indicator_value"]
    x["candidate_predicted_gva_eok"] = renormalise_parent(x, "candidate_raw_pred")
    x["candidate_error_gva_eok"] = (x.candidate_predicted_gva_eok - x.actual_gva_eok).abs()
    x["candidate_error_rate_pct"] = x.candidate_error_gva_eok / x.actual_gva_eok.replace(0, np.nan) * 100
    x["candidate_gap_to_10pct_eok"] = (x.candidate_error_gva_eok - x.actual_gva_eok * 0.10).clip(lower=0)
    city_mask = x.city.eq(city)
    group_mask = city_mask & x.cause_group.eq(cause_group) & x.phase92_queue.ne("현행유지가능")
    affected_mask = city_mask & x.middle_code.isin(target_codes)
    rec = {
        "source_id": source_id,
        "source_label": source.source_label.iloc[0],
        "source_status": source.source_status.iloc[0],
        "city": city,
        "cause_group": cause_group,
        "indicator_cells": len(target_codes),
        "affected_cells": int(affected_mask.sum()),
        "queue_cells": int(group_mask.sum()),
        "baseline_city_wape_pct": base.loc[city_mask, "current_error_gva_eok"].sum() / base.loc[city_mask, "actual_gva_eok"].sum() * 100,
        "candidate_city_wape_pct": x.loc[city_mask, "candidate_error_gva_eok"].sum() / x.loc[city_mask, "actual_gva_eok"].sum() * 100,
        "baseline_group_error_eok": base.loc[group_mask, "current_error_gva_eok"].sum(),
        "candidate_group_error_eok": x.loc[group_mask, "candidate_error_gva_eok"].sum(),
        "baseline_group_gap10_eok": base.loc[group_mask, "current_gap_to_10pct_eok"].sum(),
        "candidate_group_gap10_eok": x.loc[group_mask, "candidate_gap_to_10pct_eok"].sum(),
        "worsened_city_cells": int((x.loc[city_mask, "candidate_error_gva_eok"].to_numpy() > base.loc[city_mask, "current_error_gva_eok"].to_numpy() + 1e-9).sum()),
        "worsened_affected_cells": int((x.loc[affected_mask, "candidate_error_gva_eok"] > x.loc[affected_mask, "current_error_gva_eok"] + 1e-9).sum()),
    }
    rec["city_wape_delta_pp"] = rec["candidate_city_wape_pct"] - rec["baseline_city_wape_pct"]
    rec["group_error_reduction_eok"] = rec["baseline_group_error_eok"] - rec["candidate_group_error_eok"]
    rec["group_gap10_reduction_eok"] = rec["baseline_group_gap10_eok"] - rec["candidate_group_gap10_eok"]
    rec["strict_adoptable"] = (
        rec["group_error_reduction_eok"] > 1e-9
        and rec["group_gap10_reduction_eok"] >= -1e-9
        and rec["city_wape_delta_pp"] <= 1e-9
        and rec["worsened_city_cells"] == 0
    )
    detail = x.loc[affected_mask, [
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "cause_group",
        "actual_gva_eok",
        "current_predicted_gva_eok",
        "current_error_gva_eok",
        "candidate_predicted_gva_eok",
        "candidate_error_gva_eok",
        "candidate_error_rate_pct",
    ]].copy()
    detail["source_id"] = source_id
    return rec, detail


def screen(reg: pd.DataFrame, ind: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = []
    details = []
    if ind.empty:
        return pd.DataFrame(), pd.DataFrame()
    for (source_id, city, cause_group), g in ind.groupby(["source_id", "city", "cause_group"]):
        if g.middle_code.nunique() < 2:
            continue
        rec, detail = evaluate_candidate(reg, ind, source_id, city, cause_group)
        records.append(rec)
        details.append(detail)
    return pd.DataFrame(records).sort_values(["strict_adoptable", "group_gap10_reduction_eok", "group_error_reduction_eok"], ascending=[False, False, False]), pd.concat(details, ignore_index=True) if details else pd.DataFrame()


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = load_registry()
    ind = indicator_sources(reg)
    candidates, detail = screen(reg, ind)
    strict = candidates[candidates.strict_adoptable].copy() if not candidates.empty else pd.DataFrame()
    best_diag = candidates.sort_values("group_gap10_reduction_eok", ascending=False).head(20) if not candidates.empty else pd.DataFrame()

    ind.to_csv(OUTDIR / "phase94_direct_activity_indicators.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(OUTDIR / "phase94_direct_activity_candidate_screen.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase94_direct_activity_candidate_detail.csv", index=False, encoding="utf-8-sig")

    report = f"""# 직접 활동자료 원인군 후보 스크린

## 목적

Phase93에서 교차도시 패턴 전이가 개별 중분류 악화 금지 조건을 통과하지 못했으므로, 로컬에 이미 확보된 직접 활동자료를 중분류 개선 후보로 스크린했다. 후보는 중분류 코드와 직접 연결되는 자료만 사용했다.

## 사용 후보자료

{md_table(ind.groupby(["source_id", "source_label", "source_status", "city", "cause_group"], as_index=False).agg(cells=("middle_code", "nunique"), indicator_sum=("indicator_value", "sum")), [("source_id", "자료ID"), ("source_label", "자료명"), ("source_status", "자료상태"), ("city", "지역"), ("cause_group", "원인군"), ("cells", "중분류 개수"), ("indicator_sum", "지표합계")], 80)}

## 엄격 채택 가능 후보

{md_table(strict, [("source_id", "자료ID"), ("source_label", "자료명"), ("source_status", "자료상태"), ("city", "지역"), ("cause_group", "원인군"), ("indicator_cells", "지표셀"), ("baseline_group_error_eok", "기준 그룹오차 억원"), ("candidate_group_error_eok", "후보 그룹오차 억원"), ("group_error_reduction_eok", "그룹오차 감소 억원"), ("baseline_group_gap10_eok", "기준 10%초과 억원"), ("candidate_group_gap10_eok", "후보 10%초과 억원"), ("group_gap10_reduction_eok", "10%초과 감소 억원"), ("city_wape_delta_pp", "도시WAPE 변화 pp"), ("worsened_city_cells", "악화셀")], 40)}

## 진단상 개선 폭 상위 후보

{md_table(best_diag, [("source_id", "자료ID"), ("source_label", "자료명"), ("source_status", "자료상태"), ("city", "지역"), ("cause_group", "원인군"), ("indicator_cells", "지표셀"), ("baseline_group_error_eok", "기준 그룹오차 억원"), ("candidate_group_error_eok", "후보 그룹오차 억원"), ("group_error_reduction_eok", "그룹오차 감소 억원"), ("group_gap10_reduction_eok", "10%초과 감소 억원"), ("city_wape_delta_pp", "도시WAPE 변화 pp"), ("worsened_city_cells", "악화셀"), ("strict_adoptable", "엄격채택")], 30)}

## 판정

1. 현재 로컬 직접자료 중 개별 중분류 악화 0건까지 만족하는 엄격 채택 후보는 {len(strict)}개다.
2. 진단상 일부 자료는 특정 원인군의 오차를 줄이지만, 동시에 다른 중분류를 악화시키거나 도시 전체 WAPE를 악화시켜 최종 채택하지 않는다.
3. 다음 실험은 엄격 채택 후보가 있으면 이를 Phase92 최신 레지스트리에 반영하고, 없으면 Phase89/92의 필요자료 목록을 실제 수집 대상으로 좁힌다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase94_direct_activity_candidate_screen.csv")


if __name__ == "__main__":
    main()
