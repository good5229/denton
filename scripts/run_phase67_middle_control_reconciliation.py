#!/usr/bin/env python3
"""Phase67: reconcile vulnerable middle-industry aggregate errors.

The project target is GVA.  Fine KSIC actual GVA is mostly unavailable, so the
safe workflow is:

1. Estimate fine cells using activity indicators.
2. When an upper/middle official or validation control is available, use it as
   a control total.
3. Re-scale lower cells inside the control total and validate the aggregate.

This script quantifies the difference between the unconstrained small-to-middle
diagnostic and the middle-controlled reconciliation that should be used for
production/disclosure whenever middle controls exist.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
INFILE = DATA / "phase64_hierarchical_aggregate_validation" / "phase64_small_to_middle_aggregate_validation_detail.csv"
OUTDIR = DATA / "phase67_middle_control_reconciliation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase67_middle_control_reconciliation.md"


KSIC_MIDDLE_NAME = {
    "01": "농업",
    "02": "임업",
    "10": "식료품 제조업",
    "11": "음료 제조업",
    "13": "섬유제품 제조업",
    "14": "의복·모피 제조업",
    "15": "가죽·가방·신발 제조업",
    "16": "목재·나무제품 제조업",
    "17": "펄프·종이 제조업",
    "18": "인쇄·기록매체 복제업",
    "19": "코크스·석유정제품 제조업",
    "20": "화학물질·화학제품 제조업",
    "21": "의약품 제조업",
    "22": "고무·플라스틱 제조업",
    "23": "비금속 광물제품 제조업",
    "24": "1차 금속 제조업",
    "25": "금속가공제품 제조업",
    "26": "전자부품·컴퓨터 제조업",
    "27": "의료·정밀기기 제조업",
    "28": "전기장비 제조업",
    "29": "기계·장비 제조업",
    "30": "자동차·트레일러 제조업",
    "31": "기타 운송장비 제조업",
    "32": "가구 제조업",
    "33": "기타 제품 제조업",
    "34": "산업용 기계 수리업",
    "35": "전기·가스 공급업",
    "36": "수도업",
    "37": "하수·폐수 처리업",
    "38": "폐기물 처리·재생업",
    "39": "환경 정화·복원업",
    "41": "종합 건설업",
    "42": "전문직별 공사업",
    "45": "자동차·부품 판매업",
    "46": "도매·상품중개업",
    "47": "소매업",
    "49": "육상운송업",
    "50": "수상 운송업",
    "51": "항공 운송업",
    "52": "창고·운송관련 서비스업",
    "55": "숙박업",
    "56": "음식점·주점업",
    "58": "출판업",
    "59": "영상·오디오 제작업",
    "60": "방송업",
    "61": "우편·통신업",
    "62": "컴퓨터·시스템통합업",
    "63": "정보서비스업",
    "64": "금융업",
    "65": "보험·연금업",
    "66": "금융·보험 관련 서비스업",
    "68": "부동산업",
    "70": "연구개발업",
    "71": "전문 서비스업",
    "72": "건축·엔지니어링 서비스업",
    "73": "과학기술 서비스업",
    "74": "사업시설 관리업",
    "75": "사업지원 서비스업",
    "76": "임대업",
    "84": "공공행정",
    "85": "교육 서비스업",
    "86": "보건업",
    "87": "사회복지 서비스업",
    "90": "창작·예술 서비스업",
    "91": "스포츠·오락 서비스업",
    "94": "협회·단체",
    "95": "개인용품 수리업",
    "96": "기타 개인 서비스업",
}


def parent_letters(parent_section: str) -> list[str]:
    parent_section = str(parent_section)
    if parent_section == "ERS":
        return ["E", "R", "S"]
    if parent_section == "MN0":
        return ["M", "N"]
    return [parent_section[0]]


def large_gva_by_code(city: str) -> dict[str, float]:
    path = (
        DATA / "partial_stats_phase41_all_ksic_multiresolution_cube.parquet"
        if city == "고양시"
        else DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet"
    )
    cube = pd.read_parquet(
        path,
        columns=["industry_level", "industry_code", "time_level", "period", "geo_level", "estimated_gva"],
    )
    large = cube[
        cube.industry_level.eq("대분류")
        & cube.time_level.eq("연")
        & cube.period.astype(str).eq("2023")
        & cube.geo_level.eq("시")
    ].copy()
    return large.groupby(large.industry_code.astype(str)).estimated_gva.sum().to_dict()


def add_money_columns(df: pd.DataFrame) -> pd.DataFrame:
    maps = {city: large_gva_by_code(city) for city in sorted(df.city.unique())}
    out = df.copy()
    out["parent_gva_eok"] = out.apply(
        lambda r: sum(maps[r.city].get(letter, 0.0) for letter in parent_letters(r.parent_section)) / 100,
        axis=1,
    )
    out["middle_code"] = out.middle_code.astype(str).str.zfill(2)
    out["middle_label"] = np.where(
        out.middle_name.fillna("").astype(str).str.len().gt(0),
        out.middle_name,
        out.middle_code.map(KSIC_MIDDLE_NAME).fillna(out.middle_code),
    )
    out["actual_eok"] = out.actual_middle_share * out.parent_gva_eok
    out["unconstrained_pred_eok"] = out.predicted_small_aggregated_share * out.parent_gva_eok
    out["unconstrained_error_eok"] = (out.unconstrained_pred_eok - out.actual_eok).abs()
    out["unconstrained_error_rate_pct"] = out.unconstrained_error_eok / out.actual_eok.replace(0, np.nan) * 100
    out["controlled_pred_eok"] = out.actual_eok
    out["controlled_error_eok"] = 0.0
    out["controlled_error_rate_pct"] = 0.0
    out["control_multiplier"] = out.actual_middle_share / out.predicted_small_aggregated_share.replace(0, np.nan)
    out["control_policy"] = np.where(
        out.predicted_small_aggregated_share.gt(0),
        "중분류 통제총량 비례보정",
        "중분류 통제총량 균등재배분",
    )
    return out


def metric_rows(detail: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for city, sub in detail.groupby("city"):
        usable = sub[sub.actual_middle_share.between(0.001, 0.999)].copy()
        actual_sum = usable.actual_eok.sum()
        for mode, prefix in [
            ("비제약 소분류 집계", "unconstrained"),
            ("중분류 통제총량 적용", "controlled"),
        ]:
            err = usable[f"{prefix}_error_eok"]
            rel = usable[f"{prefix}_error_rate_pct"].replace([np.inf, -np.inf], np.nan)
            rows.append(
                {
                    "city": city,
                    "mode": mode,
                    "cells": int(len(usable)),
                    "actual_sum_eok": round(float(actual_sum), 3),
                    "error_sum_eok": round(float(err.sum()), 3),
                    "wape_pct": round(float(err.sum() / actual_sum * 100), 3) if actual_sum else np.nan,
                    "median_error_rate_pct": round(float(rel.median()), 3),
                    "p90_error_rate_pct": round(float(rel.quantile(0.9)), 3),
                    "max_error_rate_pct": round(float(rel.max()), 3),
                    "max_error_eok": round(float(err.max()), 3),
                    "over_10pct_cells": int(rel.gt(10).sum()),
                    "over_20pct_cells": int(rel.gt(20).sum()),
                }
            )
    return rows


def md_table(df: pd.DataFrame, columns: list[tuple[str, str]], limit: int = 20) -> str:
    if df.empty:
        return "\n해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in columns) + " |"]
    lines.append("| " + " | ".join("---" if not label.endswith("%") and "억원" not in label else "---:" for _, label in columns) + " |")
    for _, r in df.head(limit).iterrows():
        vals = []
        for key, _ in columns:
            v = r[key]
            if isinstance(v, float):
                vals.append(f"{v:,.1f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(INFILE)
    detail = add_money_columns(raw)
    usable = detail[detail.actual_middle_share.between(0.001, 0.999)].copy()
    metrics = pd.DataFrame(metric_rows(detail))

    detail_out = usable[
        [
            "city",
            "parent_section",
            "middle_code",
            "middle_label",
            "actual_middle_share",
            "predicted_small_aggregated_share",
            "parent_gva_eok",
            "actual_eok",
            "unconstrained_pred_eok",
            "unconstrained_error_eok",
            "unconstrained_error_rate_pct",
            "controlled_pred_eok",
            "controlled_error_eok",
            "controlled_error_rate_pct",
            "control_multiplier",
            "control_policy",
        ]
    ].sort_values(["city", "unconstrained_error_rate_pct"], ascending=[True, False])
    detail_out.to_csv(OUTDIR / "phase67_middle_control_reconciliation_detail.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUTDIR / "phase67_middle_control_reconciliation_summary.csv", index=False, encoding="utf-8-sig")

    vulnerable = detail_out.sort_values(["city", "unconstrained_error_rate_pct"], ascending=[True, False])
    goyang_v = vulnerable[vulnerable.city.eq("고양시")].head(8)
    pohang_v = vulnerable[vulnerable.city.eq("포항시")].head(8)

    metric_view = metrics.copy()
    report = f"""# 중분류 통제총량 적용에 따른 회계정합화 참고

## 목적

예측 대상은 총부가가치(GVA)다. 소분류 actual GVA가 공개되지 않는 경우에도 중분류 또는 대분류 actual/검증총량이 있으면, 배포용 하위 추정치는 상위 총량에 맞춰 재배분할 수 있다. 다만 이 절차는 회계정합화이지 예측 정확도 평가가 아니다. 산업별 예측 정확도는 Phase68의 `실제 중분류 GVA 환산액 vs 추정 중분류 GVA`로 판단한다.

## 방법

- 실제: `2023년 대분류 GVA × 중분류 검증 비중`
- 비제약 집계: `2023년 대분류 GVA × 소분류 추정값의 중분류 합산 비중`
- 통제총량 적용: 중분류 실제 환산액을 총량으로 고정하고, 그 안에서 소분류 추정 비중만 재스케일
- 오차: `|예측액 - 실제액|`, 단위는 억원이며 괄호 안 비율은 `오차 / 실제액 × 100`

## 회계정합화 참고 결과

{md_table(metric_view, [("city", "지역"), ("mode", "방식"), ("cells", "셀"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_rate_pct", "중앙오차 %"), ("p90_error_rate_pct", "p90오차 %"), ("over_10pct_cells", "10%초과"), ("over_20pct_cells", "20%초과")])}

## 고양시 중분류 추정오차: 통제총량 적용 전

{md_table(goyang_v, [("middle_label", "중분류"), ("actual_eok", "실제 억원"), ("unconstrained_pred_eok", "추정 억원"), ("unconstrained_error_eok", "오차 억원"), ("unconstrained_error_rate_pct", "오차 %"), ("control_policy", "회계정합 방식")], 8)}

## 포항시 중분류 추정오차: 통제총량 적용 전

{md_table(pohang_v, [("middle_label", "중분류"), ("actual_eok", "실제 억원"), ("unconstrained_pred_eok", "추정 억원"), ("unconstrained_error_eok", "오차 억원"), ("unconstrained_error_rate_pct", "오차 %"), ("control_policy", "회계정합 방식")], 8)}

## 판정

- 중분류 actual 또는 그에 준하는 검증총량이 존재하는 항목은 배포 단계에서 `중분류 통제총량 적용`을 할 수 있다. 그러나 이때 사라지는 잔차는 회계상 잔차이며, 예측 정확도 성과가 아니다.
- 포스터와 성능 보고서에는 통제총량 적용 후 0%를 쓰지 않는다. 반드시 `실제 중분류 GVA 환산액`, `추정 중분류 GVA`, `오차(억원·%)`를 제시한다.
- 통제총량을 쓰지 않는 집계값은 산업별 예측오차를 드러내는 성능 진단값이다.
- 중분류 actual이 없는 항목은 여전히 별도 개선이 필요하다. 이때는 농림어업의 경지·생산량, 건설의 착공·허가·기성, 부동산의 공시가격·연면적·거래량, 운수·창고의 승하차·물동량·창고면적처럼 업종별 활동자료를 사용해야 한다.
- 상대오차가 큰 일부 항목은 실제액이 작아 분모 효과가 커진다. 포스터에는 억원과 %를 병기하되, 활용 판정은 가중오차와 절대금액을 함께 보아야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase67_middle_control_reconciliation_summary.csv")


if __name__ == "__main__":
    main()
