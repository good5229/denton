#!/usr/bin/env python3
"""Phase186: C00 middle-industry indicator screen.

This phase screens locally cached manufacturing indicators against Phase179 C00
middle-industry errors.  It is an audit/screen only:

- same-year city-middle value-added indicators are marked as leakage-risk;
- all-vintage indicators are precision-only until publication timing is proven;
- lagged personal-business indicators can be considered flash-eligible;
- no candidate is adopted operationally here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase186_c00_indicator_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase186_c00_indicator_screen.md"

P179 = DATA / "phase179_metadata_guarded_middle_gate" / "phase179_metadata_guarded_registry.csv"
PBIZ = DATA / "phase120_finance_procurement_source_integration" / "phase120_personal_business_indicators.csv"
MFG_VA_2023 = DATA / "phase109_goyang_pohang_gt10_precision_improvement" / "phase109_manufacturing_value_added_indicator_2023.csv"
P185_ROUTE = DATA / "phase185_c00_local_candidate_audit" / "phase185_c00_residual_middle_routebook.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.DataFrame()


def md_table(rows: list[dict[str, Any]], cols: list[tuple[str, str]]) -> str:
    out = ["| " + " | ".join(h for _, h in cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        vals = []
        for key, _ in cols:
            val = str(row.get(key, ""))
            vals.append(val.replace("|", "/").replace("\n", " ")[:240])
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def candidate_meta(source_id: str, source_label: str) -> tuple[str, str, str]:
    sid = str(source_id)
    if "lag2021" in sid:
        return "속보 후보", "fnafBasYr<=2021 지연 구조자료", "publication-lag 확인은 필요하지만 target-year actual 직접 사용 위험은 낮음"
    if "all_vintage_unverified" in sid:
        return "정밀화 후보", "현재 API 빈티지/공표시점 미확인", "2023 예측시점에서 알 수 있었는지 미확인; 속보 사용 금지"
    if sid == "phase109_mfg_value_added_2023":
        return "누수위험 후보", "2023 시군구×중분류 제조업 부가가치 지표", "예측 대상과 너무 가까운 same-year lower-level value-added 지표이므로 운영 채택 금지"
    return "검토 후보", str(source_label), "공표시점/정의 확인 필요"


def short_source_id(source_id: str) -> str:
    sid = str(source_id)
    sid = sid.replace("phase120_personal_business_finance_", "pbiz_fin_")
    sid = sid.replace("phase120_personal_business_basic_", "pbiz_basic_")
    sid = sid.replace("phase109_mfg_value_added_2023", "mfg_va_2023")
    return sid


def make_candidate_predictions(target: pd.DataFrame, indicators: pd.DataFrame) -> pd.DataFrame:
    out_rows: list[dict[str, Any]] = []
    target = target.copy()
    target["middle_code"] = target["middle_code"].astype(int)
    total_by_city = target.groupby("city")["actual_gva_eok"].sum().to_dict()

    for (source_id, source_label, unit, timing_track, timing_note), g in indicators.groupby(
        ["source_id", "source_label", "unit", "timing_track", "timing_note"], dropna=False
    ):
        meta_track, meta_basis, meta_caveat = candidate_meta(str(source_id), str(source_label))
        for city, cg in g.groupby("city"):
            city_target = target[target["city"].eq(city)].copy()
            if city_target.empty:
                continue
            vals = cg[["middle_code", "indicator_value"]].copy()
            vals["middle_code"] = vals["middle_code"].astype(int)
            vals["indicator_value"] = pd.to_numeric(vals["indicator_value"], errors="coerce").clip(lower=0)
            merged = city_target.merge(vals, on="middle_code", how="left")
            covered = merged["indicator_value"].notna() & (merged["indicator_value"] > 0)
            if covered.sum() < 2:
                continue
            denom = merged.loc[covered, "indicator_value"].sum()
            total = total_by_city[city]
            merged["candidate_predicted_gva_eok"] = merged["phase179_predicted_gva_eok"]
            merged.loc[covered, "candidate_predicted_gva_eok"] = total * merged.loc[covered, "indicator_value"] / denom
            merged["candidate_error_gva_eok"] = (merged["candidate_predicted_gva_eok"] - merged["actual_gva_eok"]).abs()
            merged["candidate_error_rate_pct"] = merged["candidate_error_gva_eok"] / merged["actual_gva_eok"].abs() * 100
            merged["delta_vs_phase179_eok"] = merged["candidate_error_gva_eok"] - merged["phase179_error_gva_eok"]
            for _, r in merged.iterrows():
                out_rows.append(
                    {
                        "city": city,
                        "source_id": source_id,
                        "source_id_short": short_source_id(str(source_id)),
                        "source_label": source_label,
                        "unit": unit,
                        "timing_track": timing_track,
                        "timing_note": timing_note,
                        "candidate_track": meta_track,
                        "candidate_basis": meta_basis,
                        "candidate_caveat": meta_caveat,
                        "middle_code": int(r["middle_code"]),
                        "middle_label": r["middle_label"],
                        "actual_gva_eok": float(r["actual_gva_eok"]),
                        "phase179_predicted_gva_eok": float(r["phase179_predicted_gva_eok"]),
                        "phase179_error_gva_eok": float(r["phase179_error_gva_eok"]),
                        "phase179_error_rate_pct": float(r["phase179_error_rate_pct"]),
                        "indicator_value": float(r["indicator_value"]) if pd.notna(r["indicator_value"]) else 0.0,
                        "indicator_covered": bool(covered.loc[r.name] if r.name in covered.index else False),
                        "candidate_predicted_gva_eok": float(r["candidate_predicted_gva_eok"]),
                        "candidate_error_gva_eok": float(r["candidate_error_gva_eok"]),
                        "candidate_error_rate_pct": float(r["candidate_error_rate_pct"]),
                        "delta_vs_phase179_eok": float(r["delta_vs_phase179_eok"]),
                    }
                )
    return pd.DataFrame(out_rows)


def summarize(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (city, source_id, source_label, candidate_track, candidate_caveat), g in detail.groupby(
        ["city", "source_id", "source_label", "candidate_track", "candidate_caveat"], dropna=False
    ):
        actual_sum = g["actual_gva_eok"].sum()
        base_error = g["phase179_error_gva_eok"].sum()
        cand_error = g["candidate_error_gva_eok"].sum()
        rows.append(
            {
                "city": city,
                "source_id": source_id,
                "source_id_short": short_source_id(str(source_id)),
                "source_label": source_label,
                "candidate_track": candidate_track,
                "candidate_caveat": candidate_caveat,
                "cells": int(len(g)),
                "covered_cells": int(g["indicator_covered"].sum()),
                "actual_sum_eok": actual_sum,
                "phase179_error_sum_eok": base_error,
                "candidate_error_sum_eok": cand_error,
                "error_reduction_eok": base_error - cand_error,
                "phase179_wape_pct": base_error / actual_sum * 100 if actual_sum else pd.NA,
                "candidate_wape_pct": cand_error / actual_sum * 100 if actual_sum else pd.NA,
                "worsened_cells": int((g["delta_vs_phase179_eok"] > 1e-8).sum()),
                "improved_cells": int((g["delta_vs_phase179_eok"] < -1e-8).sum()),
                "gt20_before": int((g["phase179_error_rate_pct"] > 20).sum()),
                "gt20_after": int((g["candidate_error_rate_pct"] > 20).sum()),
            }
        )
    s = pd.DataFrame(rows)
    for col in ["actual_sum_eok", "phase179_error_sum_eok", "candidate_error_sum_eok", "error_reduction_eok", "phase179_wape_pct", "candidate_wape_pct"]:
        if col in s.columns:
            s[col] = s[col].round(3)
    if not s.empty:
        s["guardrail_decision"] = "reject"
        s.loc[
            (s["candidate_track"].eq("속보 후보"))
            & (s["error_reduction_eok"] > 0)
            & (s["worsened_cells"] == 0),
            "guardrail_decision",
        ] = "flash_candidate_needs_external_validation"
        s.loc[
            (s["candidate_track"].eq("정밀화 후보"))
            & (s["error_reduction_eok"] > 0)
            & (s["worsened_cells"] == 0),
            "guardrail_decision",
        ] = "precision_candidate_needs_publication_audit"
        s.loc[s["candidate_track"].eq("누수위험 후보"), "guardrail_decision"] = "reject_leakage_risk"
    return s.sort_values(["guardrail_decision", "error_reduction_eok"], ascending=[True, False])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    p179 = read_csv(P179)
    pbiz = read_csv(PBIZ)
    mfgva = read_csv(MFG_VA_2023)
    route = read_csv(P185_ROUTE)

    target = p179[p179["parent_code"].eq("C00")].copy()
    target["middle_code"] = target["middle_code"].astype(int)

    indicators = []
    if not pbiz.empty:
        sub = pbiz[pbiz["parent_code"].eq("C00")].copy()
        sub["middle_code"] = sub["middle_code"].astype(int)
        indicators.append(sub[["city", "middle_code", "source_id", "source_label", "unit", "timing_track", "timing_note", "indicator_value"]])
    if not mfgva.empty:
        sub = mfgva.copy()
        sub["source_id"] = "phase109_mfg_value_added_2023"
        sub["source_label"] = "2023 제조업 중분류 부가가치 지표"
        sub["unit"] = sub.get("unit_nm", "백만원")
        sub["timing_track"] = "누수위험"
        sub["timing_note"] = "same-year city-middle value-added-like indicator; not allowed for operational prediction"
        sub = sub.rename(columns={"indicator_industry_name": "middle_label"})
        sub["middle_code"] = sub["middle_code"].astype(int)
        indicators.append(sub[["city", "middle_code", "source_id", "source_label", "unit", "timing_track", "timing_note", "indicator_value"]])

    all_ind = pd.concat(indicators, ignore_index=True) if indicators else pd.DataFrame()
    detail = make_candidate_predictions(target, all_ind) if not all_ind.empty else pd.DataFrame()
    summary = summarize(detail) if not detail.empty else pd.DataFrame()

    detail_path = OUT / "phase186_c00_indicator_screen_detail.csv"
    summary_path = OUT / "phase186_c00_indicator_screen_summary.csv"
    top_detail_path = OUT / "phase186_c00_top_candidate_cell_changes.csv"
    detail.to_csv(detail_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    if not summary.empty:
        nonleak = summary[~summary["candidate_track"].eq("누수위험 후보")]
        best_ids = nonleak.sort_values("error_reduction_eok", ascending=False).head(4)[["city", "source_id"]]
        chunks = []
        for _, x in best_ids.iterrows():
            chunks.append(detail[(detail["city"].eq(x["city"])) & (detail["source_id"].eq(x["source_id"]))].sort_values("delta_vs_phase179_eok"))
        top_detail = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    else:
        top_detail = pd.DataFrame()
    top_detail.to_csv(top_detail_path, index=False, encoding="utf-8-sig")

    safe = summary[summary["guardrail_decision"].str.contains("candidate", na=False)].copy() if not summary.empty else pd.DataFrame()
    leakage = summary[summary["candidate_track"].eq("누수위험 후보")].copy() if not summary.empty else pd.DataFrame()
    best_nonleak = summary[~summary["candidate_track"].eq("누수위험 후보")].head(12).to_dict("records") if not summary.empty else []

    route_text = ""
    if not route.empty:
        route_text = md_table(route.head(12).to_dict("records"), [
            ("city", "지역"),
            ("middle_label", "중분류"),
            ("phase179_error_gva_eok", "오차(억원)"),
            ("phase179_error_rate_pct", "오차율(%)"),
            ("needed_activity_data", "필요 활동자료"),
        ])

    report = f"""# Phase186 C00 제조업 지표 후보 Screen

## 목적

Phase185는 C00 제조업 잔여오차가 중분류별로 다르며, C00 전체 보정은 위험하다고 판정했다. Phase186은 로컬에 이미 있는 제조업 관련 지표를 중분류별로 screen한다.

중요한 제한은 다음과 같다.

- 이 단계는 **운영 채택이 아니라 후보 screen**이다.
- 고양·포항 target actual은 사후 평가에만 사용한다.
- 2023 시군구×중분류 부가가치 지표처럼 예측 대상과 매우 가까운 자료는 성능이 좋아도 **누수위험 후보**로 기각한다.
- 속보 후보는 공표시점 및 외부검증이 끝나기 전까지 채택하지 않는다.

## 후보 요약

{md_table(summary.to_dict("records"), [
    ("city", "지역"),
    ("source_id_short", "후보ID"),
    ("source_label", "지표"),
    ("candidate_track", "트랙"),
    ("cells", "셀"),
    ("covered_cells", "커버"),
    ("phase179_wape_pct", "기준 WAPE(%)"),
    ("candidate_wape_pct", "후보 WAPE(%)"),
    ("error_reduction_eok", "오차감소(억원)"),
    ("worsened_cells", "악화셀"),
    ("gt20_before", "20%초과 전"),
    ("gt20_after", "20%초과 후"),
    ("guardrail_decision", "판정"),
]) if not summary.empty else "- 후보 지표 없음."}

## 누수위험 후보

{md_table(leakage.to_dict("records"), [
    ("city", "지역"),
    ("source_id_short", "후보ID"),
    ("source_label", "지표"),
    ("candidate_wape_pct", "후보 WAPE(%)"),
    ("error_reduction_eok", "오차감소(억원)"),
    ("candidate_caveat", "기각 사유"),
]) if not leakage.empty else "- 누수위험 후보 없음."}

## 비누수 후보 상위

{md_table(best_nonleak, [
    ("city", "지역"),
    ("source_id_short", "후보ID"),
    ("source_label", "지표"),
    ("candidate_track", "트랙"),
    ("candidate_wape_pct", "후보 WAPE(%)"),
    ("error_reduction_eok", "오차감소(억원)"),
    ("worsened_cells", "악화셀"),
    ("guardrail_decision", "판정"),
    ("candidate_caveat", "주의"),
]) if best_nonleak else "- 비누수 후보 없음."}

## C00 잔여 중분류별 필요자료

{route_text if route_text else "- Phase185 routebook 없음."}

## 판정

1. 같은 해 시군구×중분류 제조업 부가가치 지표는 성능이 좋아도 채택하면 안 된다. 이는 우리가 예측하려는 target에 너무 가깝기 때문에 데이터 유출 위험이 크다.
2. 개인사업자 지연 구조자료(`lag2021`)는 속보 후보가 될 수 있으나, 제조업 전체 중분류를 안정적으로 개선하는지 여부는 외부 도시/상위 집계검증이 필요하다.
3. 현재 로컬 자료만으로는 C00 잔여 19개를 한 번에 10% 이내로 끌어내릴 안전한 후보가 확인되지 않았다.
4. 다음 개선은 자료 수집 없이도 가능한 “후보 만들기”와, 추가 API가 필요한 “직접 활동자료 보강”으로 나눠야 한다.
   - 즉시 가능: 공장등록 생산품/면적/종업원 + 전력 + 개인사업자 lag2021을 중분류별로 조합한 후보 생성.
   - 추가 필요: 산업용 기계 수리업의 정비계약·대형설비 보유 사업장, 비금속/기계장비의 프로젝트·설비투자 수요, 제조업 중분류별 지역 생산액의 공표시점 확인.

## 산출물

- 후보 상세: `{detail_path.relative_to(ROOT)}`
- 후보 요약: `{summary_path.relative_to(ROOT)}`
- 상위 후보 셀 변화: `{top_detail_path.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")

    manifest = {
        "phase": 186,
        "target_c00_cells": int(len(target)),
        "indicator_rows": int(len(all_ind)),
        "screened_candidate_city_sources": int(len(summary)),
        "safe_candidate_rows": int(len(safe)),
        "leakage_candidate_rows": int(len(leakage)),
        "outputs": [str(detail_path.relative_to(ROOT)), str(summary_path.relative_to(ROOT)), str(top_detail_path.relative_to(ROOT)), str(REPORT.relative_to(ROOT))],
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
