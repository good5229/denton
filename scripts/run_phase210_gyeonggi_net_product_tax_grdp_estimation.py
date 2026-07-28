#!/usr/bin/env python3
"""Phase 210: estimate Gyeonggi GRDP by adding a net-product-tax component.

The project target remains GVA.  This script adds a separate GRDP-market-price
bridge for external validation against Statistics Korea's experimental
quarterly real GRDP XLSX.

Leakage guard:
  - It does not use same-quarter official Gyeonggi GRDP as a feature.
  - Net-product-tax scale is estimated from the prior year's implied
    Gyeonggi net-product-tax-to-GVA ratio.
  - Quarterly shape is taken from national quarterly net product taxes.
  - For 2020, the Phase209 cube starts in 2020, so a documented feasibility
    fallback uses the median 2020-2023 implied ratio.  Production use should
    replace this with a true 2019 ratio once 2019 Gyeonggi GVA is materialized.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE209 = ROOT / "data" / "processed" / "phase209_gyeonggi_sigungu_gva_expansion"
OUT = ROOT / "data" / "processed" / "phase210_gyeonggi_net_product_tax_grdp"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase210_gyeonggi_net_product_tax_grdp.md"


def now_kst() -> str:
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_표시할 행 없음_"
    str_df = df.copy()
    for col in str_df.columns:
        str_df[col] = str_df[col].map(lambda v: "" if pd.isna(v) else str(v))
    lines = [
        "| " + " | ".join(str_df.columns) + " |",
        "| " + " | ".join(["---"] * len(str_df.columns)) + " |",
    ]
    for row in str_df.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def load_project_gva() -> tuple[pd.DataFrame, pd.DataFrame]:
    est = pd.read_parquet(PHASE209 / "phase209_gyeonggi_sigungu_sector_quarterly_gva.parquet")
    quarterly = (
        est.groupby(["period", "year", "quarter"], as_index=False)
        .estimated_quarterly_gva_eok.sum()
        .rename(columns={"estimated_quarterly_gva_eok": "project_gva_eok"})
    )
    annual = (
        quarterly.groupby("year", as_index=False)
        .project_gva_eok.sum()
        .rename(columns={"project_gva_eok": "project_gva_annual_eok"})
    )
    return quarterly, annual


def load_official_gyeonggi_grdp() -> tuple[pd.DataFrame, pd.DataFrame]:
    level = pd.read_csv(PHASE209 / "phase209_official_xlsx_gyeonggi_real_grdp_market_price_level.csv")
    total = (
        level[level.activity.eq("지역내총생산(시장가격)")][["period", "year", "quarter", "official_value_eok"]]
        .rename(columns={"official_value_eok": "official_grdp_eok"})
    )
    annual = (
        total.groupby("year", as_index=False)
        .official_grdp_eok.sum()
        .rename(columns={"official_grdp_eok": "official_grdp_annual_eok"})
    )
    return total, annual


def load_national_net_product_tax_quarter_share() -> pd.DataFrame:
    raw = pd.DataFrame(json.loads((ROOT / "data" / "raw" / "national_quarterly_gdp_real.json").read_text(encoding="utf-8")))
    npt = raw[raw.C1_NM.eq("순생산물세")].copy()
    npt["year"] = npt.PRD_DE.astype(str).str[:4].astype(int)
    npt["quarter"] = npt.PRD_DE.astype(str).str[-2:].astype(int)
    npt["national_net_product_tax_billion_krw"] = pd.to_numeric(npt.DT, errors="coerce")
    npt["annual_national_net_product_tax_billion_krw"] = npt.groupby("year").national_net_product_tax_billion_krw.transform("sum")
    npt["national_npt_quarter_share"] = (
        npt.national_net_product_tax_billion_krw
        / npt.annual_national_net_product_tax_billion_krw
    )
    return npt[["year", "quarter", "national_npt_quarter_share"]]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    gva_q, gva_y = load_project_gva()
    official_q, official_y = load_official_gyeonggi_grdp()
    national_share = load_national_net_product_tax_quarter_share()

    implied_annual = official_y.merge(gva_y, on="year", how="inner")
    implied_annual["implied_net_product_tax_eok"] = (
        implied_annual.official_grdp_annual_eok
        - implied_annual.project_gva_annual_eok
    )
    implied_annual["implied_npt_to_gva_ratio"] = (
        implied_annual.implied_net_product_tax_eok
        / implied_annual.project_gva_annual_eok
    )

    lag_ratio = implied_annual[["year", "implied_npt_to_gva_ratio"]].copy()
    lag_ratio["year"] = lag_ratio.year + 1
    lag_ratio = lag_ratio.rename(columns={"implied_npt_to_gva_ratio": "lagged_npt_to_gva_ratio"})

    pred = (
        official_q.merge(gva_q, on=["period", "year", "quarter"], how="inner", validate="one_to_one")
        .merge(gva_y, on="year", how="left", validate="many_to_one")
        .merge(lag_ratio, on="year", how="left", validate="many_to_one")
        .merge(national_share, on=["year", "quarter"], how="left", validate="many_to_one")
    )
    feasibility_backfill_ratio = float(implied_annual[implied_annual.year.between(2020, 2023)].implied_npt_to_gva_ratio.median())
    pred["npt_ratio_source"] = "prior_year_implied_ratio"
    pred.loc[pred.lagged_npt_to_gva_ratio.isna(), "npt_ratio_source"] = "feasibility_backfill_median_2020_2023_need_2019_gva"
    pred["lagged_npt_to_gva_ratio"] = pred.lagged_npt_to_gva_ratio.fillna(feasibility_backfill_ratio)
    pred["predicted_annual_net_product_tax_eok"] = (
        pred.project_gva_annual_eok
        * pred.lagged_npt_to_gva_ratio
    )
    pred["predicted_net_product_tax_eok"] = (
        pred.predicted_annual_net_product_tax_eok
        * pred.national_npt_quarter_share
    )
    pred["predicted_grdp_market_price_eok"] = (
        pred.project_gva_eok
        + pred.predicted_net_product_tax_eok
    )
    pred["gva_only_gap_eok"] = pred.project_gva_eok - pred.official_grdp_eok
    pred["gva_only_gap_pct"] = pred.gva_only_gap_eok.abs() / pred.official_grdp_eok.abs() * 100
    pred["grdp_with_predicted_npt_gap_eok"] = (
        pred.predicted_grdp_market_price_eok
        - pred.official_grdp_eok
    )
    pred["grdp_with_predicted_npt_gap_pct"] = (
        pred.grdp_with_predicted_npt_gap_eok.abs()
        / pred.official_grdp_eok.abs()
        * 100
    )
    pred["method"] = "lagged_gyeonggi_npt_to_gva_ratio_x_national_npt_quarter_share"

    pred_path = OUT / "phase210_gyeonggi_predicted_net_product_tax_grdp_validation.csv"
    implied_path = OUT / "phase210_gyeonggi_implied_annual_net_product_tax.csv"
    summary_path = OUT / "phase210_manifest.json"
    pred.to_csv(pred_path, index=False, encoding="utf-8-sig")
    implied_annual.to_csv(implied_path, index=False, encoding="utf-8-sig")

    eval_df = pred[pred.year.between(2020, 2023)].copy()
    summary = {
        "created_at": now_kst(),
        "rows_2020_2023": int(len(eval_df)),
        "gva_only_mean_gap_pct": float(eval_df.gva_only_gap_pct.mean()),
        "gva_only_max_gap_pct": float(eval_df.gva_only_gap_pct.max()),
        "grdp_with_predicted_npt_mean_gap_pct": float(eval_df.grdp_with_predicted_npt_gap_pct.mean()),
        "grdp_with_predicted_npt_max_gap_pct": float(eval_df.grdp_with_predicted_npt_gap_pct.max()),
        "feasibility_backfill_ratio_for_missing_2019": feasibility_backfill_ratio,
        "outputs": {
            "prediction_csv": str(pred_path.relative_to(ROOT)),
            "implied_annual_npt_csv": str(implied_path.relative_to(ROOT)),
            "manifest": str(summary_path.relative_to(ROOT)),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    annual_display = implied_annual[implied_annual.year.between(2020, 2023)][
        ["year", "official_grdp_annual_eok", "project_gva_annual_eok", "implied_net_product_tax_eok", "implied_npt_to_gva_ratio"]
    ].round({
        "official_grdp_annual_eok": 0,
        "project_gva_annual_eok": 0,
        "implied_net_product_tax_eok": 0,
        "implied_npt_to_gva_ratio": 4,
    })
    pred_display = eval_df[
        [
            "period",
            "project_gva_eok",
            "predicted_net_product_tax_eok",
            "predicted_grdp_market_price_eok",
            "official_grdp_eok",
            "grdp_with_predicted_npt_gap_eok",
            "gva_only_gap_pct",
            "grdp_with_predicted_npt_gap_pct",
            "npt_ratio_source",
        ]
    ].round({
        "project_gva_eok": 0,
        "predicted_net_product_tax_eok": 0,
        "predicted_grdp_market_price_eok": 0,
        "official_grdp_eok": 0,
        "grdp_with_predicted_npt_gap_eok": 0,
        "gva_only_gap_pct": 3,
        "grdp_with_predicted_npt_gap_pct": 3,
    })

    report = f"""# Phase 210: 경기도 순생산물세 포함 GRDP 추정 검증

## 목적

기존 예측 대상은 총부가가치(GVA)지만, 통계청 실험적 통계 XLSX는 `지역내총생산(시장가격)`을 제공한다. 이번 단계는 순생산물세를 별도 추정해 `GVA + 순생산물세` 형태의 GRDP 시장가격 추정값을 만들 수 있는지 점검한다.

## 방법

| 구성요소 | 사용 방식 | 유출 방지 |
| --- | --- | --- |
| 경기도 GVA | Phase209 경기도 31개 시군×산업×분기 GVA 합계 | 예측 산출물 |
| 순생산물세 연간 규모 | 전년도 경기도 암묵 순생산물세/GVA 비율 × 당해 연도 GVA | 같은 해 공식 GRDP 수준값을 feature로 쓰지 않음 |
| 순생산물세 분기 배분 | 전국 분기 순생산물세의 연중 분기비중 | 지역 actual 미사용 |
| 검증값 | 통계청 XLSX 경기도 실질 GRDP 시장가격 | 사후 검증에만 사용 |

2020년은 현재 Phase209 큐브가 2020년부터 시작해 2019년 경기도 GVA 기반 전년도 비율이 없다. 따라서 이번 feasibility 실험에서는 2020~2023 암묵 비율 중앙값을 2020년에만 대체 적용했다. 운영형으로 쓰려면 2019년 경기도 GVA를 물질화해 이 대체값을 제거해야 한다.

## 경기도 암묵 순생산물세 연간 규모

{md_table(annual_display)}

## 분기 GRDP 추정 검증

{md_table(pred_display)}

## 결과

- GVA 합계만 공식 GRDP와 비교한 평균 오차율: **{summary['gva_only_mean_gap_pct']:.3f}%**
- GVA 합계만 공식 GRDP와 비교한 최대 오차율: **{summary['gva_only_max_gap_pct']:.3f}%**
- 순생산물세 추정 포함 GRDP 평균 오차율: **{summary['grdp_with_predicted_npt_mean_gap_pct']:.3f}%**
- 순생산물세 추정 포함 GRDP 최대 오차율: **{summary['grdp_with_predicted_npt_max_gap_pct']:.3f}%**

## 판정

순생산물세까지 포함한 GRDP 시장가격 추정은 가능하다. 다만 이 값은 기존 GVA 예측과 별도 산출물로 관리해야 한다. 포스터나 보고서에서는 `총부가가치 추정`과 `순생산물세 포함 GRDP 환산 검증`을 구분해 표기하는 것이 안전하다.

## 산출물

- `{summary['outputs']['prediction_csv']}`
- `{summary['outputs']['implied_annual_npt_csv']}`
- `{summary['outputs']['manifest']}`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(summary_path)
    print(REPORT)


if __name__ == "__main__":
    main()
