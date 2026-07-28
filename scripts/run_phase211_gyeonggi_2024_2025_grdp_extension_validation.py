#!/usr/bin/env python3
"""Phase 211: extend Gyeonggi GRDP market-price validation to 2024-2025.

This is an internal validation experiment only; posters are not modified.

Target boundary
---------------
The project target remains GVA.  Statistics Korea's experimental quarterly
regional table provides GRDP at market prices.  To compare against that upper
official boundary without using same-year Gyeonggi actuals as features, this
script extrapolates:

1. Main GVA blocks (mining/manufacturing, construction, services) from the
   2023 Gyeonggi project GVA block level using national same-activity quarterly
   YoY growth from the Statistics Korea XLSX.
2. Other industries and net product taxes using lagged Gyeonggi accounting
   ratios and national quarterly shares.

Two tracks are emitted:

- recursive_no_target_actual: 2025 uses the model's own 2024 predicted
  other/NPT ratio, not 2024 Gyeonggi official values.
- prior_year_official_ratio: 2025 uses the already-known prior-year official
  Gyeonggi other/NPT ratio.  This is a "precision after prior-year publication"
  track, not a pure nowcast track.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE209 = ROOT / "data" / "processed" / "phase209_gyeonggi_sigungu_gva_expansion"
RAW_XLSX_DIR = ROOT / "data" / "raw" / "sido_quarterly"
OUT = ROOT / "data" / "processed" / "phase211_gyeonggi_2024_2025_grdp_extension"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase211_gyeonggi_2024_2025_grdp_extension.md"

MAIN_BLOCKS = {
    "mining_manufacturing": {
        "xlsx_activity": "광업, 제조업",
        "project_sector_codes": ["B00", "C00"],
        "label": "광업·제조업",
    },
    "construction": {
        "xlsx_activity": "건설업",
        "project_sector_codes": ["F00"],
        "label": "건설업",
    },
    "services": {
        "xlsx_activity": "서비스업",
        "project_sector_codes": ["G00", "H00", "I00", "J00", "K00", "L00", "MN0", "O00", "P00", "Q00", "ERS"],
        "label": "서비스업",
    },
}
OTHER_NPT_ACTIVITY = "기타산업 및 순생산물세"
TOTAL_ACTIVITY = "지역내총생산(시장가격)"


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


def normalize_region(value: str) -> str:
    if value == "경기":
        return "경기도"
    return str(value)


def quarter_label_to_period(value) -> str | None:
    text = str(value).strip()
    m = re.fullmatch(r"(\d{4})\.(\d)/4p?", text)
    if not m:
        return None
    return f"{m.group(1)}Q{m.group(2)}"


def load_sido_xlsx_quarterly() -> pd.DataFrame:
    files = [p for p in RAW_XLSX_DIR.glob("*.xlsx") if not p.name.startswith("~$")]
    if not files:
        raise FileNotFoundError(f"no xlsx under {RAW_XLSX_DIR}")
    path = sorted(files)[-1]
    raw = pd.read_excel(path, sheet_name="실질금액", header=None)
    header = raw.iloc[4]
    quarter_cols = [(idx, quarter_label_to_period(value)) for idx, value in header.items()]
    quarter_cols = [(idx, period) for idx, period in quarter_cols if period]

    rows: list[dict] = []
    current_region = None
    for _, row in raw.iloc[5:].iterrows():
        if pd.notna(row.iloc[1]):
            current_region = normalize_region(str(row.iloc[1]).strip())
        activity = row.iloc[2]
        if pd.isna(activity) or current_region is None:
            continue
        activity = str(activity).strip()
        for idx, period in quarter_cols:
            value = pd.to_numeric(row.iloc[idx], errors="coerce")
            if pd.isna(value):
                continue
            year = int(period[:4])
            quarter = int(period[-1])
            rows.append(
                {
                    "region": current_region,
                    "activity": activity,
                    "period": period,
                    "year": year,
                    "quarter": quarter,
                    "official_value_billion_krw": float(value),
                    "official_value_eok": float(value) * 10,
                    "source_file": str(path.relative_to(ROOT)),
                }
            )
    return pd.DataFrame(rows)


def load_project_2020_2023_blocks() -> pd.DataFrame:
    est = pd.read_parquet(PHASE209 / "phase209_gyeonggi_sigungu_sector_quarterly_gva.parquet")
    parts = []
    for block_id, spec in MAIN_BLOCKS.items():
        part = (
            est[est.sector_code.isin(spec["project_sector_codes"])]
            .groupby(["year", "quarter", "period"], as_index=False)
            .estimated_quarterly_gva.sum()
            .rename(columns={"estimated_quarterly_gva": "project_gva_million_krw"})
        )
        part["project_gva_eok"] = part.project_gva_million_krw / 100
        part["block_id"] = block_id
        part["block_label"] = spec["label"]
        part["xlsx_activity"] = spec["xlsx_activity"]
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def build_national_growth(xlsx: pd.DataFrame) -> pd.DataFrame:
    nat = xlsx[xlsx.region.eq("전국") & xlsx.activity.isin([spec["xlsx_activity"] for spec in MAIN_BLOCKS.values()])].copy()
    nat = nat.sort_values(["activity", "year", "quarter"])
    nat["previous_year_value_eok"] = nat.groupby(["activity", "quarter"]).official_value_eok.shift(1)
    nat["national_yoy_factor"] = nat.official_value_eok / nat.previous_year_value_eok
    return nat[["activity", "year", "quarter", "period", "national_yoy_factor"]].dropna()


def extrapolate_main_blocks(project_blocks: pd.DataFrame, growth: pd.DataFrame) -> pd.DataFrame:
    history = project_blocks.copy()
    history["estimate_track"] = "observed_project_gva_2020_2023"
    history = history.rename(columns={"project_gva_eok": "predicted_main_block_gva_eok"})

    preds = []
    previous = history[history.year.eq(2023)][
        ["block_id", "block_label", "xlsx_activity", "quarter", "predicted_main_block_gva_eok"]
    ].copy()
    for year in [2024, 2025]:
        g = growth[growth.year.eq(year)].copy()
        current = previous.merge(
            g,
            left_on=["xlsx_activity", "quarter"],
            right_on=["activity", "quarter"],
            how="inner",
            validate="one_to_one",
        )
        current["predicted_main_block_gva_eok"] = (
            current.predicted_main_block_gva_eok * current.national_yoy_factor
        )
        current["year"] = year
        current["period"] = current.year.astype(str) + "Q" + current.quarter.astype(str)
        current["estimate_track"] = "national_activity_yoy_extrapolation"
        preds.append(
            current[
                [
                    "year",
                    "quarter",
                    "period",
                    "block_id",
                    "block_label",
                    "xlsx_activity",
                    "predicted_main_block_gva_eok",
                    "national_yoy_factor",
                    "estimate_track",
                ]
            ]
        )
        previous = current[["block_id", "block_label", "xlsx_activity", "quarter", "predicted_main_block_gva_eok"]].copy()

    return pd.concat(preds, ignore_index=True)


def official_gyeonggi_components(xlsx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    gyeonggi = xlsx[xlsx.region.eq("경기도")].copy()
    total = (
        gyeonggi[gyeonggi.activity.eq(TOTAL_ACTIVITY)][["period", "year", "quarter", "official_value_eok"]]
        .rename(columns={"official_value_eok": "official_grdp_market_price_eok"})
    )
    other = (
        gyeonggi[gyeonggi.activity.eq(OTHER_NPT_ACTIVITY)][["period", "year", "quarter", "official_value_eok"]]
        .rename(columns={"official_value_eok": "official_other_npt_eok"})
    )
    main = gyeonggi[gyeonggi.activity.isin([spec["xlsx_activity"] for spec in MAIN_BLOCKS.values()])][
        ["period", "year", "quarter", "activity", "official_value_eok"]
    ].copy()
    return total, other, main


def national_other_npt_share(xlsx: pd.DataFrame) -> pd.DataFrame:
    nat = xlsx[xlsx.region.eq("전국") & xlsx.activity.eq(OTHER_NPT_ACTIVITY)].copy()
    nat["annual_other_npt_eok"] = nat.groupby("year").official_value_eok.transform("sum")
    nat["national_other_npt_quarter_share"] = nat.official_value_eok / nat.annual_other_npt_eok
    return nat[["year", "quarter", "national_other_npt_quarter_share"]]


def assemble_predictions(main_pred: pd.DataFrame, xlsx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    total_actual, other_actual, main_actual = official_gyeonggi_components(xlsx)
    share = national_other_npt_share(xlsx)

    main_q = (
        main_pred.groupby(["year", "quarter", "period"], as_index=False)
        .predicted_main_block_gva_eok.sum()
        .rename(columns={"predicted_main_block_gva_eok": "predicted_main_blocks_eok"})
    )
    main_y = (
        main_q.groupby("year", as_index=False)
        .predicted_main_blocks_eok.sum()
        .rename(columns={"predicted_main_blocks_eok": "predicted_main_blocks_annual_eok"})
    )
    official_main_y = (
        main_actual.groupby("year", as_index=False)
        .official_value_eok.sum()
        .rename(columns={"official_value_eok": "official_main_blocks_annual_eok"})
    )
    official_other_y = (
        other_actual.groupby("year", as_index=False)
        .official_other_npt_eok.sum()
        .rename(columns={"official_other_npt_eok": "official_other_npt_annual_eok"})
    )

    # Baseline ratio through 2023 comes from actual accounting relation, but not
    # from 2024/2025 targets.  For 2024 this is the only lag available.
    prior_basis = (
        official_other_y.merge(official_main_y, on="year", how="inner")
        .assign(official_other_npt_to_main_ratio=lambda d: d.official_other_npt_annual_eok / d.official_main_blocks_annual_eok)
        [["year", "official_other_npt_to_main_ratio"]]
    )

    results = []
    recursive_ratios: dict[int, float] = {}
    for track in ["recursive_no_target_actual", "prior_year_official_ratio"]:
        annual_pred = main_y[main_y.year.isin([2024, 2025])].copy()
        ratio_rows = []
        for year in [2024, 2025]:
            prior_year = year - 1
            if track == "recursive_no_target_actual" and prior_year in recursive_ratios:
                ratio = recursive_ratios[prior_year]
                ratio_source = f"prior_year_predicted_ratio_{prior_year}"
            else:
                ratio_match = prior_basis[prior_basis.year.eq(prior_year)]
                if ratio_match.empty:
                    raise ValueError(f"missing prior official ratio for {prior_year}")
                ratio = float(ratio_match.official_other_npt_to_main_ratio.iloc[0])
                ratio_source = f"prior_year_official_ratio_{prior_year}"
            pred_main_annual = float(annual_pred[annual_pred.year.eq(year)].predicted_main_blocks_annual_eok.iloc[0])
            pred_other_annual = pred_main_annual * ratio
            if track == "recursive_no_target_actual":
                recursive_ratios[year] = pred_other_annual / pred_main_annual
            ratio_rows.append(
                {
                    "year": year,
                    "ratio_track": track,
                    "other_npt_to_main_ratio": ratio,
                    "ratio_source": ratio_source,
                    "predicted_other_npt_annual_eok": pred_other_annual,
                }
            )
        ratio_df = pd.DataFrame(ratio_rows)
        pred = (
            main_q[main_q.year.isin([2024, 2025])]
            .merge(main_y, on="year", how="left", validate="many_to_one")
            .merge(ratio_df, on="year", how="left", validate="many_to_one")
            .merge(share, on=["year", "quarter"], how="left", validate="many_to_one")
            .merge(total_actual, on=["period", "year", "quarter"], how="left", validate="one_to_one")
        )
        pred["predicted_other_npt_eok"] = (
            pred.predicted_other_npt_annual_eok * pred.national_other_npt_quarter_share
        )
        pred["predicted_grdp_market_price_eok"] = (
            pred.predicted_main_blocks_eok + pred.predicted_other_npt_eok
        )
        pred["error_eok"] = pred.predicted_grdp_market_price_eok - pred.official_grdp_market_price_eok
        pred["abs_error_eok"] = pred.error_eok.abs()
        pred["ape_pct"] = pred.abs_error_eok / pred.official_grdp_market_price_eok.abs() * 100
        pred["main_blocks_only_ape_pct"] = (
            (pred.predicted_main_blocks_eok - pred.official_grdp_market_price_eok).abs()
            / pred.official_grdp_market_price_eok.abs()
            * 100
        )
        pred["validation_boundary"] = "official_gyeonggi_grdp_market_price_xlsx"
        results.append(pred)

    combined = pd.concat(results, ignore_index=True)
    summary = (
        combined.groupby(["ratio_track", "year"], as_index=False)
        .agg(
            quarters=("period", "nunique"),
            official_grdp_sum_eok=("official_grdp_market_price_eok", "sum"),
            predicted_grdp_sum_eok=("predicted_grdp_market_price_eok", "sum"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            wape_pct=("abs_error_eok", lambda s: s.sum() / combined.loc[s.index, "official_grdp_market_price_eok"].abs().sum() * 100),
            max_ape_pct=("ape_pct", "max"),
        )
        .sort_values(["ratio_track", "year"])
    )
    return combined, summary


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    xlsx = load_sido_xlsx_quarterly()
    project_blocks = load_project_2020_2023_blocks()
    growth = build_national_growth(xlsx)
    main_pred = extrapolate_main_blocks(project_blocks, growth)
    validation, summary = assemble_predictions(main_pred, xlsx)

    xlsx_path = OUT / "phase211_sido_quarterly_xlsx_long.csv"
    main_path = OUT / "phase211_gyeonggi_main_block_extrapolation_2024_2025.csv"
    validation_path = OUT / "phase211_gyeonggi_grdp_extension_validation_2024_2025.csv"
    summary_path = OUT / "phase211_gyeonggi_grdp_extension_summary_2024_2025.csv"
    manifest_path = OUT / "phase211_manifest.json"

    xlsx.to_csv(xlsx_path, index=False, encoding="utf-8-sig")
    main_pred.to_csv(main_path, index=False, encoding="utf-8-sig")
    validation.to_csv(validation_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    official_periods = xlsx[xlsx.region.eq("경기도") & xlsx.activity.eq(TOTAL_ACTIVITY)].period
    manifest = {
        "created_at": now_kst(),
        "official_gyeonggi_grdp_period_min": str(official_periods.min()),
        "official_gyeonggi_grdp_period_max": str(official_periods.max()),
        "validated_periods": ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4"],
        "poster_updated": False,
        "claim_boundary": "internal_extension_validation_not_yet_poster_claim",
        "outputs": {
            "xlsx_long": str(xlsx_path.relative_to(ROOT)),
            "main_block_extrapolation": str(main_path.relative_to(ROOT)),
            "validation": str(validation_path.relative_to(ROOT)),
            "summary": str(summary_path.relative_to(ROOT)),
            "report": str(REPORT.relative_to(ROOT)),
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    display = validation[
        [
            "ratio_track",
            "period",
            "predicted_main_blocks_eok",
            "predicted_other_npt_eok",
            "predicted_grdp_market_price_eok",
            "official_grdp_market_price_eok",
            "error_eok",
            "ape_pct",
            "ratio_source",
        ]
    ].round(
        {
            "predicted_main_blocks_eok": 0,
            "predicted_other_npt_eok": 0,
            "predicted_grdp_market_price_eok": 0,
            "official_grdp_market_price_eok": 0,
            "error_eok": 0,
            "ape_pct": 3,
        }
    )
    summary_display = summary.round(
        {
            "official_grdp_sum_eok": 0,
            "predicted_grdp_sum_eok": 0,
            "abs_error_sum_eok": 0,
            "wape_pct": 3,
            "max_ape_pct": 3,
        }
    )
    main_block_summary = (
        main_pred.groupby(["year", "block_label"], as_index=False)
        .predicted_main_block_gva_eok.sum()
        .assign(predicted_main_block_gva_eok=lambda d: d.predicted_main_block_gva_eok.round(0))
    )

    report = f"""# Phase 211: 2024·2025 경기도 GRDP 확장 검증

## 목적

포스터에는 아직 반영하지 않고, 평가시점이 2026년이라는 점을 고려해 2024년과 2025년까지 추정값-공식값 비교가 가능한지 내부 검증했다.

## 실제값 확보 여부

- 통계청 실험적 통계 XLSX `실질금액` 시트에는 경기도 `지역내총생산(시장가격)` 분기 수준값이 **2015Q1~2026Q1**까지 존재한다.
- 이번 검증은 완결 연도인 **2024Q1~2025Q4**를 사용했다.
- 2026Q1도 존재하지만 1개 분기만 있으므로 이번 연간 비교에서는 제외했다.

## 추정 방식

| 구분 | 사용 정보 | 경기도 2024·2025 공식값 사용 여부 |
| --- | --- | --- |
| 광업·제조업 | 2023 경기도 프로젝트 GVA × 전국 동업종 분기 전년동기 성장률 | 미사용 |
| 건설업 | 2023 경기도 프로젝트 GVA × 전국 건설업 분기 전년동기 성장률 | 미사용 |
| 서비스업 | 2023 경기도 프로젝트 GVA × 전국 서비스업 분기 전년동기 성장률 | 미사용 |
| 기타산업·순생산물세 | 전년도 경기도 회계비율 × 전국 분기 배분비중 | 같은 해 공식값 미사용 |
| 검증값 | 통계청 XLSX 경기도 GRDP 시장가격 | 사후 대조에만 사용 |

## 트랙 구분

| 트랙 | 의미 |
| --- | --- |
| `recursive_no_target_actual` | 2025년에도 2024년 경기도 공식 회계비율을 쓰지 않고, 2024년 예측 비율을 이어 붙인 순수 외삽형 |
| `prior_year_official_ratio` | 2025년 예측 때 이미 공표된 전년도(2024년) 공식 회계비율은 사용할 수 있다고 보는 정밀화형 |

## 2024·2025 주 산업블록 추정 규모

{md_table(main_block_summary)}

## 분기별 GRDP 시장가격 검증

{md_table(display)}

## 연도별 요약

{md_table(summary_display)}

## 판정

- 2024년과 2025년 모두 공식 actual이 존재하므로, 포스터 밖 내부 검증으로는 비교 가능하다.
- 단, 현재 고양시·포항시 동·업종 GVA 파이프라인은 2023년 공식 시군구·산업 기준에서 출발하므로, 2024·2025는 **경기도 상위 GRDP 경계의 외삽 검증**으로 해석해야 한다.
- `recursive_no_target_actual`은 완전 외삽에 가깝고, `prior_year_official_ratio`는 전년도 공식값 공표 후 정밀화에 가깝다.
- 포스터에 반영하려면 `2024·2025p 경기도 상위 GRDP 외부검증`이라고 좁게 표기해야 하며, 고양시 행정동 GVA의 2024·2025 공식 검증처럼 쓰면 안 된다.

## 산출물

- `{manifest['outputs']['xlsx_long']}`
- `{manifest['outputs']['main_block_extrapolation']}`
- `{manifest['outputs']['validation']}`
- `{manifest['outputs']['summary']}`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(validation_path)
    print(summary_path)
    print(REPORT)
    print(summary_display.to_string(index=False))


if __name__ == "__main__":
    main()
