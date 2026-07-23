#!/usr/bin/env python3
"""Phase120: integrate newly approved finance/procurement public sources.

This phase starts from Phase117 flash candidates and adds the newly collected
Financial Services Commission personal-business APIs:

* personal-business profile counts by city and KSIC middle class;
* personal-business sales and financial amounts by city and KSIC middle class.

The personal-business APIs are valuable, but their exact historical public
vintage is not archived in the local dataset.  Therefore this script separates:

* `flash_lag_safe`: records with financial base year <= 2021, treated as
  plausibly available before the 2023-09-30 flash cut-off;
* `refinement_candidate`: all collected records, usable after source/vintage
  audit as a precision-improvement candidate.

Middle-industry GVA actuals are used only by the inherited screening evaluator,
not as an allocation input.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import run_phase115_flash_gt20_source_improvement as p115
import run_phase116_expanded_flash_gt20_improvement as p116
import run_phase117_max_source_flash_push as p117


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase120_finance_procurement_source_integration"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase120_finance_procurement_source_integration.md"
PERSONAL_RAW = RAW / "phase120_finance_procurement_probe" / "personal_business_city_full"


CITY_SLUG = {"goyang": "고양시", "pohang": "포항시"}


def parent_for_middle(code: str) -> str | None:
    c = int(str(code).zfill(2))
    if 1 <= c <= 3:
        return "A00"
    if 10 <= c <= 34:
        return "C00"
    if 41 <= c <= 42:
        return "F00"
    if 45 <= c <= 47:
        return "G00"
    if 49 <= c <= 52:
        return "H00"
    if 55 <= c <= 56:
        return "I00"
    if 58 <= c <= 63:
        return "J00"
    if 64 <= c <= 66:
        return "K00"
    if 70 <= c <= 76:
        return "MN0"
    if 86 <= c <= 87:
        return "Q00"
    if 90 <= c <= 96:
        return "ERS"
    # L68 부동산업 is not present in the current middle-GVA registry, so do not
    # inject it into the evaluator.
    return None


def read_jsonl(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return pd.DataFrame()
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce").fillna(0.0)


def add_indicator(
    rows: list[dict[str, Any]],
    city: str,
    parent: str,
    middle: str,
    source_id: str,
    label: str,
    value: float,
    unit: str,
    timing_track: str,
    note: str,
) -> None:
    if pd.notna(value) and np.isfinite(value) and value > 0:
        rows.append(
            {
                "city": city,
                "parent_code": parent,
                "middle_code": str(middle).zfill(2),
                "source_id": source_id,
                "source_label": label,
                "indicator_raw_value": float(value),
                "indicator_value": float(np.log1p(value)),
                "allocation_value": float(value),
                "unit": unit,
                "timing_track": timing_track,
                "timing_note": note,
            }
        )


def personal_business_indicators() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for slug, city in CITY_SLUG.items():
        profile = read_jsonl(PERSONAL_RAW / f"profile_{slug}.jsonl")
        sales = read_jsonl(PERSONAL_RAW / f"sales_{slug}.jsonl")
        finance = read_jsonl(PERSONAL_RAW / f"finance_{slug}.jsonl")

        for name, df in [("profile", profile), ("sales", sales), ("finance", finance)]:
            audit_rows.append(
                {
                    "city": city,
                    "dataset": name,
                    "rows": int(len(df)),
                    "min_basYm": str(df.get("basYm", pd.Series(dtype=str)).min()) if not df.empty and "basYm" in df.columns else "",
                    "max_basYm": str(df.get("basYm", pd.Series(dtype=str)).max()) if not df.empty and "basYm" in df.columns else "",
                    "min_fnafBasYr": str(df.get("fnafBasYr", pd.Series(dtype=str)).min()) if not df.empty and "fnafBasYr" in df.columns else "",
                    "max_fnafBasYr": str(df.get("fnafBasYr", pd.Series(dtype=str)).max()) if not df.empty and "fnafBasYr" in df.columns else "",
                }
            )

        if not profile.empty:
            profile["middle_code"] = profile["bizBzcCd"].astype(str).str.extract(r"(\d+)")[0].str.zfill(2)
            profile["parent_code"] = profile["middle_code"].map(parent_for_middle)
            g = profile[profile["parent_code"].notna()].groupby(["parent_code", "middle_code"], as_index=False).size()
            for _, r in g.iterrows():
                add_indicator(
                    rows,
                    city,
                    r.parent_code,
                    r.middle_code,
                    "phase120_personal_business_profile_count_all",
                    "개인사업자 기본정보 사업자 행수",
                    float(r["size"]),
                    "건",
                    "정밀화",
                    "금융위원회 개인사업자기본정보 전량; 매년 1회 갱신, 현재 API 빈티지라 속보성 성능값에는 신중 적용",
                )

        for dataset_name, df in [("sales", sales), ("finance", finance)]:
            if df.empty:
                continue
            df = df.copy()
            df["middle_code"] = df["bizBzcCd"].astype(str).str.extract(r"(\d+)")[0].str.zfill(2)
            df["parent_code"] = df["middle_code"].map(parent_for_middle)
            df["fnafBasYr_num"] = pd.to_numeric(df.get("fnafBasYr"), errors="coerce")
            df["saleAmt_num"] = num(df.get("saleAmt", pd.Series(0, index=df.index)))
            df["positive_sale"] = df["saleAmt_num"].clip(lower=0)
            df["abs_sale"] = df["saleAmt_num"].abs()
            if "bzopPftAmt" in df.columns:
                df["profit_pos"] = num(df["bzopPftAmt"]).clip(lower=0)
            else:
                df["profit_pos"] = 0.0
            if "astTsumAmt" in df.columns:
                df["asset_pos"] = num(df["astTsumAmt"]).clip(lower=0)
            else:
                df["asset_pos"] = 0.0

            for track_name, mask, timing, note_suffix in [
                (
                    "lag2021",
                    df["fnafBasYr_num"].le(2021),
                    "속보성",
                    "fnafBasYr<=2021만 사용: 2023-09-30 속보시점 이전 이용 가능성이 높은 지연 구조자료",
                ),
                (
                    "all_vintage_unverified",
                    pd.Series(True, index=df.index),
                    "정밀화",
                    "전체 수집자료: 현재 API 빈티지이므로 공표시점 확인 전에는 정밀화 후보로만 사용",
                ),
            ]:
                sub = df[mask & df["parent_code"].notna()].copy()
                if sub.empty:
                    continue
                agg = (
                    sub.groupby(["parent_code", "middle_code"], as_index=False)
                    .agg(
                        positive_sale=("positive_sale", "sum"),
                        abs_sale=("abs_sale", "sum"),
                        profit_pos=("profit_pos", "sum"),
                        asset_pos=("asset_pos", "sum"),
                        rows=("middle_code", "size"),
                    )
                )
                for _, r in agg.iterrows():
                    for metric, label, unit in [
                        ("positive_sale", "개인사업자 양수 매출합계", "원"),
                        ("abs_sale", "개인사업자 절대 매출합계", "원"),
                        ("profit_pos", "개인사업자 양수 영업이익합계", "원"),
                        ("asset_pos", "개인사업자 양수 자산합계", "원"),
                        ("rows", "개인사업자 재무/매출 행수", "건"),
                    ]:
                        value = float(r[metric])
                        if metric in {"profit_pos", "asset_pos"} and dataset_name != "finance":
                            continue
                        add_indicator(
                            rows,
                            city,
                            r.parent_code,
                            r.middle_code,
                            f"phase120_personal_business_{dataset_name}_{metric}_{track_name}",
                            label,
                            value,
                            unit,
                            timing,
                            f"금융위원회 개인사업자{('재무정보' if dataset_name == 'finance' else '매출액정보')} {note_suffix}",
                        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = (
            out.groupby(["city", "parent_code", "middle_code", "source_id", "source_label", "unit", "timing_track", "timing_note"], as_index=False)
            .agg(indicator_raw_value=("indicator_raw_value", "sum"), indicator_value=("indicator_value", "sum"), allocation_value=("allocation_value", "sum"))
        )
    return out, pd.DataFrame(audit_rows)


def build_indicators(include_refinement_candidates: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = p117.build_indicators()
    personal, audit = personal_business_indicators()
    if not include_refinement_candidates and not personal.empty:
        personal = personal[personal["timing_track"].eq("속보성")].copy()
    out = pd.concat([base, personal], ignore_index=True) if not personal.empty else base.copy()
    if not out.empty:
        out["allocation_value"] = out.get("allocation_value", out["indicator_raw_value"])
    return out, audit


def select(screen: pd.DataFrame) -> pd.DataFrame:
    selected = p117.select(screen)
    if selected.empty:
        return selected
    selected = selected.copy()
    selected.loc[selected["option_id"].astype(str).str.contains("all_vintage_unverified", na=False), "public_claim_status"] = "정밀화 후보: API 빈티지 확인 필요"
    selected.loc[selected["option_id"].astype(str).str.contains("lag2021", na=False), "public_claim_status"] = "속보 후보: 2021 이하 지연자료"
    return selected


def apply_and_rename(base: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame, prefix: str) -> pd.DataFrame:
    reg = p115.apply(base, selected, detail).rename(
        columns={
            "phase115_flash_predicted_gva_eok": f"{prefix}_predicted_gva_eok",
            "phase115_flash_error_gva_eok": f"{prefix}_error_gva_eok",
            "phase115_flash_error_rate_pct": f"{prefix}_error_rate_pct",
            "phase115_option_id": f"{prefix}_option_id",
            "phase115_flash_error_reduction_eok": f"{prefix}_error_reduction_eok",
        }
    )
    return reg


def summarize(reg: pd.DataFrame, pred_prefix: str) -> pd.DataFrame:
    rows = []
    for city, g in reg.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        old = float(g["flash_baseline_error_gva_eok"].sum())
        new = float(g[f"{pred_prefix}_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "baseline_error_eok": old,
                "baseline_wape_pct": old / actual * 100,
                "phase120_error_eok": new,
                "phase120_wape_pct": new / actual * 100,
                "error_reduction_eok": old - new,
                "wape_reduction_pp": (old - new) / actual * 100,
                "baseline_gt20_cells": int((g["flash_baseline_error_rate_pct"] > 20).sum()),
                "phase120_gt20_cells": int((g[f"{pred_prefix}_error_rate_pct"] > 20).sum()),
                "baseline_gt10_cells": int((g["flash_baseline_error_rate_pct"] > 10).sum()),
                "phase120_gt10_cells": int((g[f"{pred_prefix}_error_rate_pct"] > 10).sum()),
                "worsened_cells": int((g[f"{pred_prefix}_error_gva_eok"] > g["flash_baseline_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = p115.load_base()

    strict_indicators, personal_audit = build_indicators(include_refinement_candidates=False)
    strict_screen, strict_detail = p116.evaluate(base, strict_indicators)
    strict_selected = select(strict_screen)
    strict_registry = apply_and_rename(base, strict_selected, strict_detail, "phase120_strict_flash")
    strict_summary = summarize(strict_registry, "phase120_strict_flash")

    all_indicators, _ = build_indicators(include_refinement_candidates=True)
    all_screen, all_detail = p116.evaluate(base, all_indicators)
    all_selected = select(all_screen)
    all_registry = apply_and_rename(base, all_selected, all_detail, "phase120_candidate")
    all_summary = summarize(all_registry, "phase120_candidate")

    personal_indicators = all_indicators[all_indicators["source_id"].astype(str).str.contains("phase120_personal_business", na=False)].copy()
    personal_source_summary = (
        personal_indicators.groupby(["city", "parent_code", "source_id", "timing_track"], as_index=False)
        .agg(middle_cells=("middle_code", "nunique"), indicator_total=("allocation_value", "sum"))
        .sort_values(["city", "parent_code", "source_id"])
    )

    all_improved = all_registry[all_registry["phase120_candidate_error_reduction_eok"].gt(1e-9)].sort_values(
        ["city", "phase120_candidate_error_reduction_eok"], ascending=[True, False]
    )
    all_remaining_gt20 = all_registry[all_registry["phase120_candidate_error_rate_pct"].gt(20)].sort_values(
        ["city", "phase120_candidate_error_gva_eok"], ascending=[True, False]
    )
    strict_remaining_gt20 = strict_registry[strict_registry["phase120_strict_flash_error_rate_pct"].gt(20)].sort_values(
        ["city", "phase120_strict_flash_error_gva_eok"], ascending=[True, False]
    )

    personal_audit.to_csv(OUT / "phase120_personal_business_collection_audit.csv", index=False, encoding="utf-8-sig")
    personal_indicators.to_csv(OUT / "phase120_personal_business_indicators.csv", index=False, encoding="utf-8-sig")
    personal_source_summary.to_csv(OUT / "phase120_personal_business_source_summary.csv", index=False, encoding="utf-8-sig")
    strict_indicators.to_csv(OUT / "phase120_strict_flash_indicators.csv", index=False, encoding="utf-8-sig")
    strict_screen.to_csv(OUT / "phase120_strict_flash_candidate_screen.csv", index=False, encoding="utf-8-sig")
    strict_selected.to_csv(OUT / "phase120_strict_flash_selected_options.csv", index=False, encoding="utf-8-sig")
    strict_registry.to_csv(OUT / "phase120_strict_flash_registry.csv", index=False, encoding="utf-8-sig")
    strict_summary.to_csv(OUT / "phase120_strict_flash_city_summary.csv", index=False, encoding="utf-8-sig")
    strict_remaining_gt20.to_csv(OUT / "phase120_strict_flash_remaining_gt20.csv", index=False, encoding="utf-8-sig")

    all_indicators.to_csv(OUT / "phase120_all_candidate_indicators.csv", index=False, encoding="utf-8-sig")
    all_screen.to_csv(OUT / "phase120_all_candidate_screen.csv", index=False, encoding="utf-8-sig")
    all_selected.to_csv(OUT / "phase120_all_selected_options.csv", index=False, encoding="utf-8-sig")
    all_registry.to_csv(OUT / "phase120_candidate_registry.csv", index=False, encoding="utf-8-sig")
    all_summary.to_csv(OUT / "phase120_candidate_city_summary.csv", index=False, encoding="utf-8-sig")
    all_improved.to_csv(OUT / "phase120_candidate_improved_cells.csv", index=False, encoding="utf-8-sig")
    all_remaining_gt20.to_csv(OUT / "phase120_candidate_remaining_gt20.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase120 금융·조달 공개자료 통합 수집 및 GVA 후보실험

## 목적

활용신청이 완료된 조달청·금융공공데이터를 실제 고양시·포항시 중분류 총부가가치(GVA) 추정 실험에 연결한다. 이번 단계의 핵심은 “접속 확인”이 아니라, 무료 공개자료를 `지역 × KSIC 중분류` 활동자료로 바꿔 기존 속보/정밀화 오차 체계에 넣을 수 있는지 검증하는 것이다.

## 수집 완료 자료

{p115.md_table(personal_audit, [("city", "지역"), ("dataset", "자료"), ("rows", "행수"), ("min_basYm", "최소 기준년월"), ("max_basYm", "최대 기준년월"), ("min_fnafBasYr", "최소 재무기준연도"), ("max_fnafBasYr", "최대 재무기준연도")])}

조달청 나라장터 입찰공고정보서비스는 HTTP 공공데이터포털 게이트웨이에서 정상 호출을 확인했다. 다만 날짜 외 지역 필터가 없어, 전국 공고 전량 수집 뒤 수요기관명·공고기관명으로 고양/포항을 걸러야 한다. API 응답이 느리고 이번 단계의 핵심 취약 업종에는 개인사업자 매출자료가 더 직접적이므로, 조달청은 배치 수집 후보로 남겼다.

보험가입정보와 금융회사재무신용정보도 정상 호출을 확인했다. 생명보험은 광역 지역 필드, 자동차보험은 전국 월별 계약·보험료 성격, 금융회사재무는 회사 단위 자료이므로 이번 중분류 공간배분에는 단독 투입하지 않았다.

## 개인사업자 자료의 집계 특성

{p115.md_table(personal_source_summary, [("city", "지역"), ("parent_code", "상위산업"), ("source_id", "지표"), ("timing_track", "사용트랙"), ("middle_cells", "중분류 수"), ("indicator_total", "지표합계")], 80)}

주의: 개인사업자 매출자료에는 음수 매출이 존재한다. 따라서 이번 실험은 `양수 매출합계`, `절대 매출합계`, `행수`, `영업이익`, `자산`을 별도 후보로 두고, 후보 선택 과정에서 실제 GVA와 직접 맞추는 방식은 쓰지 않았다.

## 속보성 엄격 실험

`fnafBasYr<=2021`인 개인사업자 재무·매출 자료만 속보성 지연 구조자료로 허용했다. 현재 API의 과거 공표 빈티지가 로컬에 보존되어 있지 않기 때문에, 2022년 이후 기준자료는 속보성 성능값에 넣지 않았다.

{p115.md_table(strict_summary, [("city", "지역"), ("actual_sum_eok", "실제합계 억원"), ("baseline_error_eok", "기준오차 억원"), ("baseline_wape_pct", "기준오차 %"), ("phase120_error_eok", "Phase120 오차 억원"), ("phase120_wape_pct", "Phase120 오차 %"), ("error_reduction_eok", "감소 억원"), ("wape_reduction_pp", "감소 pp"), ("baseline_gt20_cells", "기준 20%초과"), ("phase120_gt20_cells", "Phase120 20%초과"), ("baseline_gt10_cells", "기준 10%초과"), ("phase120_gt10_cells", "Phase120 10%초과"), ("worsened_cells", "악화 셀")])}

### 속보성 채택 후보

{p115.md_table(strict_selected, [("city", "지역"), ("parent_code", "상위산업"), ("option_id", "선택 지표"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("public_claim_status", "판정")], 60)}

## 정밀화 후보 포함 실험

아래는 현재 API 전체 자료를 정밀화 후보까지 포함해 평가한 결과다. 이 값은 “현 시점에서 더 정밀하게 재배분할 가능성”을 보는 것이며, 예측시점 당시 사용할 수 있었다고 주장하려면 공표시점·빈티지 검사가 추가로 필요하다.

{p115.md_table(all_summary, [("city", "지역"), ("actual_sum_eok", "실제합계 억원"), ("baseline_error_eok", "기준오차 억원"), ("baseline_wape_pct", "기준오차 %"), ("phase120_error_eok", "Phase120 후보오차 억원"), ("phase120_wape_pct", "Phase120 후보오차 %"), ("error_reduction_eok", "감소 억원"), ("wape_reduction_pp", "감소 pp"), ("baseline_gt20_cells", "기준 20%초과"), ("phase120_gt20_cells", "후보 20%초과"), ("baseline_gt10_cells", "기준 10%초과"), ("phase120_gt10_cells", "후보 10%초과"), ("worsened_cells", "악화 셀")])}

### 정밀화 후보 채택 지표

{p115.md_table(all_selected, [("city", "지역"), ("parent_code", "상위산업"), ("option_id", "선택 지표"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("public_claim_status", "판정")], 80)}

## 개선된 중분류

{p115.md_table(all_improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("flash_baseline_error_gva_eok", "기준오차 억원"), ("phase120_candidate_error_gva_eok", "후보오차 억원"), ("phase120_candidate_error_rate_pct", "후보오차 %"), ("phase120_candidate_error_reduction_eok", "감소 억원"), ("phase120_candidate_option_id", "적용 지표")], 100)}

## 남은 20% 초과 중분류

{p115.md_table(all_remaining_gt20, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase120_candidate_predicted_gva_eok", "후보추정 억원"), ("phase120_candidate_error_gva_eok", "오차 억원"), ("phase120_candidate_error_rate_pct", "오차 %"), ("phase120_candidate_option_id", "적용 지표")], 120)}

## 판정

1. 원하는 공개 API의 접속은 사실상 완료됐다. 추가 API key 요청은 현재 없다.
2. 모델에 바로 강하게 들어갈 수 있는 자료는 개인사업자 재무·매출이다. 조달청은 전문서비스·건설의 속보성 보조자료지만, 지역 필터가 없어 별도 배치 수집 설계가 필요하다.
3. 개인사업자 자료는 고양·포항의 도소매·숙박음식·운수·전문서비스·개인서비스 계열을 직접 보강할 수 있다. 다만 현재 API 빈티지라 정밀화 후보와 속보성 후보를 분리해야 한다.
4. 보험·금융회사 API는 K00 금융보험업 보조자료로 유효하지만, 시군구 중분류 GVA 공간배분의 단독 근거로 쓰기에는 지역 해상도가 부족하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
