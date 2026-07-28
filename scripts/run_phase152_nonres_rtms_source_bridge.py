#!/usr/bin/env python3
"""Summarise Phase152 non-residential RTMS collection for later GVA modelling."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase152_rtms_nonres_trade_history"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase152_nonres_rtms_source_bridge.md"


def money_eok(s: pd.Series) -> float:
    return float(pd.to_numeric(s, errors="coerce").fillna(0).sum() / 10000)


def md_table(df: pd.DataFrame, floatfmt: str = ".2f") -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            if pd.api.types.is_float_dtype(view[col]):
                view[col] = view[col].map(lambda x: format(float(x), floatfmt))
            else:
                view[col] = view[col].map(lambda x: f"{int(x):,}")
    view = view.astype(str)
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in view.to_numpy()]
    return "\n".join([header, sep, *rows])


def main() -> None:
    rows = pd.read_csv(OUT / "phase152_nonres_rtms_trade_rows.csv", encoding="utf-8-sig", dtype=str)
    calls = pd.read_csv(OUT / "phase152_nonres_rtms_call_manifest.csv", encoding="utf-8-sig", dtype=str)
    monthly = pd.read_csv(OUT / "phase152_nonres_rtms_trade_gu_monthly.csv", encoding="utf-8-sig", dtype=str)

    rows["deal_amount_10k_krw_num"] = pd.to_numeric(rows["deal_amount_10k_krw"], errors="coerce").fillna(0)
    rows["building_area_sqm_num"] = pd.to_numeric(rows["building_area_sqm"], errors="coerce").fillna(0)
    rows["plottage_area_sqm_num"] = pd.to_numeric(rows["plottage_area_sqm"], errors="coerce").fillna(0)

    call_summary = pd.DataFrame(
        [
            {
                "호출수": len(calls),
                "정상호출": int(calls["result_code"].eq("000").sum()),
                "실패호출": int((~calls["result_code"].eq("000")).sum()),
                "수집 Row": len(rows),
                "월별 셀": len(monthly),
            }
        ]
    )

    city_summary = (
        rows.groupby("city", as_index=False)
        .agg(
            row_count=("period", "size"),
            months=("period", "nunique"),
            deal_amount_eok=("deal_amount_10k_krw_num", lambda s: s.sum() / 10000),
            building_area_sqm=("building_area_sqm_num", "sum"),
            plottage_area_sqm=("plottage_area_sqm_num", "sum"),
        )
        .sort_values("city")
    )
    city_summary.columns = ["지역", "Row", "월수", "거래금액(억원)", "건물면적(㎡)", "대지면적(㎡)"]

    gu_summary = (
        rows.groupby(["city", "general_gu"], as_index=False)
        .agg(
            row_count=("period", "size"),
            months=("period", "nunique"),
            deal_amount_eok=("deal_amount_10k_krw_num", lambda s: s.sum() / 10000),
            building_area_sqm=("building_area_sqm_num", "sum"),
        )
        .sort_values(["city", "general_gu"])
    )
    gu_summary.columns = ["지역", "구", "Row", "월수", "거래금액(억원)", "건물면적(㎡)"]

    year_summary = (
        rows.groupby(["city", "deal_year"], as_index=False)
        .agg(
            row_count=("period", "size"),
            deal_amount_eok=("deal_amount_10k_krw_num", lambda s: s.sum() / 10000),
            building_area_sqm=("building_area_sqm_num", "sum"),
        )
        .sort_values(["city", "deal_year"])
    )
    year_summary.columns = ["지역", "연도", "Row", "거래금액(억원)", "건물면적(㎡)"]

    use_summary = (
        rows.groupby("building_use", as_index=False)
        .agg(
            row_count=("period", "size"),
            deal_amount_eok=("deal_amount_10k_krw_num", lambda s: s.sum() / 10000),
            building_area_sqm=("building_area_sqm_num", "sum"),
        )
        .sort_values("deal_amount_eok", ascending=False)
        .head(12)
    )
    use_summary.columns = ["건물주용도", "Row", "거래금액(억원)", "건물면적(㎡)"]

    monthly_numeric = monthly.copy()
    for c in ["deal_count", "deal_amount_10k_krw", "building_area_sqm", "plottage_area_sqm"]:
        monthly_numeric[c] = pd.to_numeric(monthly_numeric[c], errors="coerce").fillna(0)
    monthly_numeric["거래금액(억원)"] = monthly_numeric["deal_amount_10k_krw"] / 10000
    monthly_numeric.to_csv(OUT / "phase152_nonres_rtms_trade_gu_monthly_for_gva.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "phase": "phase152_nonres_rtms_source_bridge",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_files": [
            "phase152_nonres_rtms_trade_rows.csv",
            "phase152_nonres_rtms_call_manifest.csv",
            "phase152_nonres_rtms_trade_gu_monthly.csv",
        ],
        "output_files": [
            "phase152_nonres_rtms_trade_gu_monthly_for_gva.csv",
            str(REPORT.relative_to(ROOT)),
        ],
        "source_url": "https://www.data.go.kr/data/15126463/openapi.do",
        "source_name": "국토교통부_상업업무용 부동산 매매 실거래가 자료",
        "strict_asof_limit": "행별 공표일자/등기일자가 없어 Q+1개월 속보 성능에는 직접 주장하지 않는다.",
    }
    (OUT / "phase152_nonres_rtms_source_bridge_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = f"""# Phase152 상업업무용 실거래 활동자료 수집 및 GVA 연결 메모

## 목적

Phase149에서 아파트 매매 실거래액은 `부동산업(KSIC 68)` 총부가가치(GVA)를 직접 예측하는 지표로 채택하지 않기로 했다. Phase150에서도 `681 부동산 임대 및 공급업`과 `682 부동산 관련 서비스업`을 나눌 때 거래축과 재고축을 분리해야 한다는 결론을 냈다.

이번 단계는 무료 공개자료인 `국토교통부_상업업무용 부동산 매매 실거래가 자료`를 수집해, 부동산업 내부 배분의 거래·중개서비스 축 후보로 연결할 수 있는지 확인한다.

## 자료 출처

- 자료명: 국토교통부_상업업무용 부동산 매매 실거래가 자료
- 링크: https://www.data.go.kr/data/15126463/openapi.do
- 엔드포인트: `RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade`
- 접근: 기존 공공데이터포털 `DATA_GO_KR` 키로 호출 가능 확인
- 범위: 고양시 3개 구, 포항시 2개 구 × 2020~2023년 월별
- 사용상 주의: 계약월 기준 회고 수집이다. 행별 공표일자나 등기일자가 제공되지 않으므로 Q+1개월 strict 속보 성능에는 직접 주장하지 않고, 정밀화 또는 보수 lag 적용 후보로 사용한다.

## 수집 결과

{md_table(call_summary)}

## 도시별 수집 규모

{md_table(city_summary)}

## 구별 수집 규모

{md_table(gu_summary)}

## 연도별 흐름

{md_table(year_summary)}

## 건물주용도 상위

{md_table(use_summary)}

## GVA 모델 연결 판단

1. `부동산업(KSIC 68)` 총량 직접 예측에는 사용하지 않는다.
2. `682 부동산 관련 서비스업`의 거래·중개활동 축에는 사용할 수 있다. 특히 `거래건수`, `거래금액`, `중개거래 여부`, `중개사 소재지`가 기존 아파트 거래축보다 넓은 범위를 설명한다.
3. `681 부동산 임대 및 공급업`에는 단독 사용하지 않는다. 재고가치, 건물면적, 공시가격, 임대차 흐름과 결합해야 한다.
4. 속보성 실험에서는 행별 공표일자가 없는 한 `계약월+보수적 lag`를 둔 후보로만 비교한다.
5. 정밀화 실험에서는 상업업무용 거래액·면적을 기존 공시가격/건축물 stock과 결합해 681/682 분할식을 다시 비교한다.

## 다음 작업

- 전월세·오피스텔·연립다세대·단독다가구 실거래 API도 같은 방식으로 추가 수집한다.
- `phase152_nonres_rtms_trade_gu_monthly_for_gva.csv`를 Phase150 2축 모델의 거래서비스축 보강 입력으로 붙인다.
- 새 성능 수치를 주장하기 전, 2023년 소분류 집계검증에서 기존 Phase150 공통 후보보다 실제 격차가 줄어드는지 확인한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"rows={len(rows)} calls={len(calls)} ok_calls={int(calls['result_code'].eq('000').sum())}")


if __name__ == "__main__":
    main()
