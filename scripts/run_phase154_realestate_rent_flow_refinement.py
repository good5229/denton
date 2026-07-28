#!/usr/bin/env python3
"""Phase154: add residential-rent flow to real-estate 681/682 split diagnostics.

This is a refinement experiment on top of Phase150.  It tests whether the
newly collected residential jeonse/monthly-rent flow (Phase153) can reduce the
681/682 split error.  Because only two target cities are currently available,
grid-screened parameters are labelled as two-city calibration candidates, not
operational performance.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import run_phase150_realestate_small_split_two_axis as p150


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase154_realestate_rent_flow_refinement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase154_realestate_rent_flow_refinement.md"
RENT_ROWS = DATA / "phase153_rtms_rent_history" / "phase153_rtms_rent_rows.csv"
RENT_MANIFEST = DATA / "phase153_rtms_rent_history" / "phase153_rtms_rent_collection_manifest.json"


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy().where(pd.notna(df), "")
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if x == "" else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: f"{int(x):,}" if x != "" else "")
    view = view.astype(str).replace({"nan": "", "NaN": "", "None": ""})
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[col].replace("|", "\\|") for col in view.columns) + " |")
    return "\n".join(lines)


def rent_features() -> pd.DataFrame:
    rows = pd.read_csv(RENT_ROWS, encoding="utf-8-sig", low_memory=False)
    rows["deal_year"] = pd.to_numeric(rows["deal_year"], errors="coerce").astype("Int64")
    rows = rows[rows["deal_year"].eq(2023)].copy()
    for col in ["deposit_10k_krw", "monthly_rent_10k_krw", "area_sqm"]:
        rows[col] = pd.to_numeric(rows[col], errors="coerce").fillna(0.0)
    out = (
        rows.groupby("city", as_index=False)
        .agg(
            apt_rent_contract_count=("deposit_10k_krw", "size"),
            apt_rent_deposit_eok=("deposit_10k_krw", lambda s: s.sum() / 10000),
            apt_monthly_rent_eok=("monthly_rent_10k_krw", lambda s: s.sum() / 10000),
            apt_rent_area_sqm=("area_sqm", "sum"),
        )
    )
    out["apt_rent_deposit_per_area_eok"] = out["apt_rent_deposit_eok"] / out["apt_rent_area_sqm"].replace(0, np.nan)
    out["apt_rent_deposit_per_contract_eok"] = out["apt_rent_deposit_eok"] / out[
        "apt_rent_contract_count"
    ].replace(0, np.nan)
    out["apt_monthly_rent_per_contract_eok"] = out["apt_monthly_rent_eok"] / out[
        "apt_rent_contract_count"
    ].replace(0, np.nan)
    return out


def combined_features() -> pd.DataFrame:
    f = p150.feature_table()
    r = rent_features()
    out = f.merge(r, on="city", how="left", validate="one_to_one")
    out["apt_rent_deposit_to_stock_pct"] = out["apt_rent_deposit_eok"] / out[
        "assessed_housing_value_eok"
    ].replace(0, np.nan) * 100
    out["apt_rent_contracts_per_broker"] = out["apt_rent_contract_count"] / out["broker_count"].replace(0, np.nan)
    out["apt_rent_deposit_per_broker_eok"] = out["apt_rent_deposit_eok"] / out["broker_count"].replace(0, np.nan)
    return out


def make_candidates(features: pd.DataFrame, actual: pd.DataFrame) -> pd.DataFrame:
    # Start with Phase150 candidates so the baseline comparison is exactly
    # reproducible, then add rent-flow candidates.
    rows = p150.candidate_shares(features, actual).to_dict("records")

    rent_density_neutral = float(features["apt_rent_deposit_per_area_eok"].median())
    rent_contract_neutral = float(features["apt_rent_deposit_per_contract_eok"].median())
    stock_per_broker_neutral = float(features["stock_value_per_broker_eok"].median())
    for r in features.itertuples(index=False):
        city = r.city
        rent_density_ratio = float(r.apt_rent_deposit_per_area_eok / rent_density_neutral)
        rent_contract_ratio = float(r.apt_rent_deposit_per_contract_eok / rent_contract_neutral)
        stock_ratio = float(r.stock_value_per_broker_eok / stock_per_broker_neutral)
        rent_to_stock = float(r.apt_rent_deposit_to_stock_pct)

        for k in [300, 400, 500, 600, 700]:
            stock_share = float(r.stock_value_per_broker_eok / (r.stock_value_per_broker_eok + k))
            for alpha in [0.15, 0.25, 0.35, 0.45, 0.55]:
                # Higher residential rent density indicates stronger rental/supply
                # activity (681), especially in dense metro markets.  The
                # multiplier is centred at the two-city median, so this is only
                # a two-city calibration candidate for now.
                adjusted = stock_share * (rent_density_ratio**alpha)
                rows.append(
                    {
                        "city": city,
                        "candidate": f"재고·중개업소 K={k}+전월세면적밀도 α={alpha}",
                        "share_681": min(max(adjusted, 0.01), 0.99),
                        "method_note": "중개업소당 공시가격 포화식에 2023 주거 전월세 보증금/면적 밀도를 곱함",
                        "candidate_family": "rent_flow_two_city_calibrated",
                        "validation_status": "2도시 보정 후보: 외부지역 검증 전 채택금지",
                    }
                )
            for beta in [0.15, 0.25, 0.35, 0.45, 0.55]:
                adjusted = stock_share * (rent_contract_ratio**beta)
                rows.append(
                    {
                        "city": city,
                        "candidate": f"재고·중개업소 K={k}+전월세계약단가 β={beta}",
                        "share_681": min(max(adjusted, 0.01), 0.99),
                        "method_note": "중개업소당 공시가격 포화식에 2023 주거 전월세 보증금/계약건수를 곱함",
                        "candidate_family": "rent_flow_two_city_calibrated",
                        "validation_status": "2도시 보정 후보: 외부지역 검증 전 채택금지",
                    }
                )

        for gamma in [0.2, 0.35, 0.5, 0.7]:
            # Pure rent-flow candidate; useful as a diagnostic because it
            # avoids the sale-transaction axis, but it is also two-city centred.
            share = 0.5 * (rent_density_ratio**gamma) * (stock_ratio**0.25)
            rows.append(
                {
                    "city": city,
                    "candidate": f"전월세면적밀도×재고밀도 γ={gamma}",
                    "share_681": min(max(share, 0.01), 0.99),
                    "method_note": "2023 주거 전월세 보증금/면적과 중개업소당 공시가격을 결합",
                    "candidate_family": "rent_flow_two_city_calibrated",
                    "validation_status": "2도시 보정 후보: 외부지역 검증 전 채택금지",
                }
            )
        rows.append(
            {
                "city": city,
                "candidate": "전월세보증금/주택재고 비율 진단",
                "share_681": min(max(rent_to_stock / (rent_to_stock + 6.0), 0.01), 0.99),
                "method_note": "2023 주거 전월세 보증금 ÷ 공시가격총액",
                "candidate_family": "rent_flow_diagnostic",
                "validation_status": "정밀화 진단 후보",
            }
        )
        for k, alpha in [(468, 1.1525), (474, 1.1525)]:
            stock_share = float(r.stock_value_per_broker_eok / (r.stock_value_per_broker_eok + k))
            adjusted = stock_share * (rent_density_ratio**alpha)
            rows.append(
                {
                    "city": city,
                    "candidate": f"사후미세탐색 K={k}+전월세면적밀도 α={alpha}",
                    "share_681": min(max(adjusted, 0.01), 0.99),
                    "method_note": "2도시 미세탐색으로 찾은 재고·중개업소+전월세 면적밀도 조합",
                    "candidate_family": "rent_flow_micro_expost",
                    "validation_status": "사후 미세탐색 후보: 외부지역 검증 전 채택금지",
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    if not RENT_ROWS.exists():
        raise FileNotFoundError(RENT_ROWS)
    OUT.mkdir(parents=True, exist_ok=True)
    rent_all = pd.read_csv(RENT_ROWS, encoding="utf-8-sig", low_memory=False)
    rent_source_summary = (
        rent_all.groupby(["source_name", "asset_type"], as_index=False)
        .agg(row_count=("period", "size"), months=("period", "nunique"))
        .sort_values(["asset_type", "source_name"])
    )
    actual = p150.actual_split()
    features = combined_features()
    candidates = make_candidates(features, actual)
    detail, summary, overall = p150.evaluate(candidates, actual)

    current_overall = overall[overall["candidate"].eq("현행 소분류 합산 기준")].copy()
    phase150_common = overall[overall["candidate"].eq("재고가치/중개업소 포화 기준 K=400")].copy()
    rent_candidates = overall[overall["candidate_family"].str.contains("rent_flow", na=False)].copy()
    rent_best = rent_candidates.sort_values(["max_city_wape_pct", "two_city_wape_pct"]).head(12)
    safe_diag = rent_candidates[rent_candidates["candidate_family"].eq("rent_flow_diagnostic")].copy()
    city_best = (
        summary[summary["candidate_family"].str.contains("rent_flow", na=False)]
        .sort_values(["city", "combined_wape_pct"])
        .groupby("city", as_index=False)
        .head(8)
    )

    features.to_csv(OUT / "phase154_realestate_rent_flow_features.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(OUT / "phase154_realestate_rent_flow_candidates.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase154_realestate_rent_flow_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase154_realestate_rent_flow_city_summary.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT / "phase154_realestate_rent_flow_overall.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "phase": "phase154_realestate_rent_flow_refinement",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": [
            str(RENT_ROWS.relative_to(ROOT)),
            str((DATA / "phase150_realestate_small_split_two_axis" / "phase150_realestate_two_axis_overall.csv").relative_to(ROOT)),
        ],
        "outputs": [
            "phase154_realestate_rent_flow_features.csv",
            "phase154_realestate_rent_flow_candidates.csv",
            "phase154_realestate_rent_flow_detail.csv",
            "phase154_realestate_rent_flow_city_summary.csv",
            "phase154_realestate_rent_flow_overall.csv",
            str(REPORT.relative_to(ROOT)),
        ],
        "adoption_warning": "Rent-flow calibrated candidates are screened on two cities only and must not be claimed as operational performance before external-city validation.",
    }
    if RENT_MANIFEST.exists():
        manifest["rent_collection_manifest"] = json.loads(RENT_MANIFEST.read_text(encoding="utf-8"))
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    best = rent_best.iloc[0] if not rent_best.empty else None
    baseline = current_overall.iloc[0] if not current_overall.empty else None
    common = phase150_common.iloc[0] if not phase150_common.empty else None

    report = f"""# Phase154 주거 전월세 흐름 기반 부동산 소분류 배분 개선 실험

## 목적

Phase153에서 수집한 주거 전월세 실거래 3종을 부동산업 내부 소분류 배분에 추가했다. 검증 대상은 2023년 `681 부동산 임대 및 공급업`과 `682 부동산 관련 서비스업`이며, 실제와 추정의 합산 GVA 격차가 기존 Phase150보다 줄어드는지를 본다.

## 자료와 사용 제한

- 수집 자료: 아파트·오피스텔·단독/다가구 전월세 실거래 {len(rent_all):,}건, 고양·포항 2020~2023년
- 이번 실험 사용: 2023년 계약건수, 보증금합계, 월세합계, 면적
- 사용 위치: `681` 임대흐름 축과 `682` 계약서비스 보조축
- 제한: 행별 공표일자/확정일자 공개시점이 없으므로 Q+1개월 속보 성능으로 주장하지 않는다.
- 제한: 전월세 보정강도는 현재 고양·포항 2도시에서만 screen했으므로 외부 시군구 검증 전 채택 금지다.

## 수집 자료 구성

{md_table(rent_source_summary.rename(columns={
    'source_name': '자료명',
    'asset_type': '유형',
    'row_count': 'Row',
    'months': '월수',
}))}

## 결합 피처

{md_table(features.rename(columns={
    'city': '지역',
    'assessed_housing_value_eok': '공시가격 총액(억원)',
    'broker_count': '중개업소 수',
    'stock_value_per_broker_eok': '중개업소당 공시가격(억원)',
    'rtms_2023_deal_value_eok': '2023 매매거래액(억원)',
    'apt_rent_contract_count': '2023 전월세 계약건수',
    'apt_rent_deposit_eok': '2023 전월세 보증금(억원)',
    'apt_monthly_rent_eok': '2023 월세합계(억원)',
    'apt_rent_area_sqm': '2023 전월세 면적(㎡)',
    'apt_rent_deposit_per_area_eok': '전월세 보증금/㎡(억원)',
    'apt_rent_deposit_per_contract_eok': '전월세 보증금/계약(억원)',
    'apt_rent_deposit_to_stock_pct': '전월세보증금/공시가격(%)',
    'apt_rent_contracts_per_broker': '중개업소당 전월세계약',
})[[
    '지역', '공시가격 총액(억원)', '중개업소 수', '중개업소당 공시가격(억원)',
    '2023 매매거래액(억원)', '2023 전월세 계약건수', '2023 전월세 보증금(억원)',
    '2023 월세합계(억원)', '전월세 보증금/㎡(억원)', '전월세 보증금/계약(억원)',
    '전월세보증금/공시가격(%)', '중개업소당 전월세계약'
]])}

## 기준 대비 결과

| 비교대상 | 2도시 WAPE(%) | 최대 도시 WAPE(%) | 해석 |
| --- | ---: | ---: | --- |
| 현행 소분류 합산 기준 | {float(baseline['two_city_wape_pct']) if baseline is not None else np.nan:.2f} | {float(baseline['max_city_wape_pct']) if baseline is not None else np.nan:.2f} | 기존 사업체·종사자 중심 |
| Phase150 공통 후보 K=400 | {float(common['two_city_wape_pct']) if common is not None else np.nan:.2f} | {float(common['max_city_wape_pct']) if common is not None else np.nan:.2f} | 전월세 없음, 재고·중개업소 중심 |
| Phase154 전월세 포함 최상위 후보 | {float(best['two_city_wape_pct']) if best is not None else np.nan:.2f} | {float(best['max_city_wape_pct']) if best is not None else np.nan:.2f} | 2도시 보정 후보, 채택 금지 |

## 전월세 포함 후보 상위

{md_table(rent_best[[
    'candidate', 'candidate_family', 'validation_status', 'two_city_error_eok',
    'two_city_wape_pct', 'max_city_wape_pct', 'mean_share_error_pp',
    'min_improvement_vs_current_pct', 'target_10pct_status'
]].rename(columns={
    'candidate': '후보',
    'candidate_family': '후보군',
    'validation_status': '검증상태',
    'two_city_error_eok': '2도시 오차(억원)',
    'two_city_wape_pct': '2도시 WAPE(%)',
    'max_city_wape_pct': '최대 도시 WAPE(%)',
    'mean_share_error_pp': '평균 681 비중오차(%p)',
    'min_improvement_vs_current_pct': '최소 현행개선율(%)',
    'target_10pct_status': '10% 목표'
}))}

## 지역별 전월세 후보 상위

{md_table(city_best[[
    'city', 'candidate', 'actual_share_pct', 'predicted_share_pct',
    'share_error_pp', 'combined_error_eok', 'combined_wape_pct',
    'improvement_vs_current_pct', 'validation_status'
]].rename(columns={
    'city': '지역',
    'candidate': '후보',
    'actual_share_pct': '681 실제비중(%)',
    'predicted_share_pct': '681 추정비중(%)',
    'share_error_pp': '681 비중오차(%p)',
    'combined_error_eok': '합산오차(억원)',
    'combined_wape_pct': '합산 WAPE(%)',
    'improvement_vs_current_pct': '현행개선율(%)',
    'validation_status': '검증상태',
}))}

## 판정

1. 주거 전월세 흐름은 방향성이 있다. 고양은 포항보다 전월세 보증금/면적과 계약단가가 높아 `681 임대 및 공급업` 비중을 상대적으로 끌어올리는 신호를 제공한다.
2. Phase150의 공통 후보 K=400은 2도시 WAPE 20%대였고, 전월세 밀도를 붙인 후보는 2도시 내부검증에서 더 낮은 오차 후보를 만든다.
3. 그러나 전월세 보정강도는 고양·포항 두 도시에서 screen한 값이므로 현재 수치는 운영 성능이 아니다. 외부 10개 시군구 검증 전에는 포스터에 “오차 달성” 숫자로 쓰면 안 된다.
4. 사후 미세탐색 후보는 최대 도시 WAPE를 10% 이내로 낮추지만, 이는 두 도시 값에 파라미터를 맞춘 결과라서 성능 주장으로 쓰면 안 된다. 다만 “전월세 면적밀도”가 오차를 줄이는 강한 후보 변수라는 근거로는 유효하다.
5. 안전한 결론은 “부동산 소분류 배분은 재고가치·중개업소만으로 부족하고, 임대차 흐름을 함께 넣어야 고양형 고밀도 임대시장과 포항형 저밀도 시장을 구분할 수 있다”이다.
6. 다음 필요작업은 고양·포항 밖의 임의 시군구로 같은 산식을 검증하는 것이다. 현재 수치는 2도시 보정 결과이므로 일반화 성능으로 주장하지 않는다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    print(f"best_rent_candidate={best['candidate'] if best is not None else 'none'}")
    print(f"best_two_city_wape={float(best['two_city_wape_pct']) if best is not None else np.nan:.4f}")
    print(f"best_max_city_wape={float(best['max_city_wape_pct']) if best is not None else np.nan:.4f}")


if __name__ == "__main__":
    main()
