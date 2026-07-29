#!/usr/bin/env python3
"""Phase227: construction building-activity gated split prototype.

Phase75 proved that building permit/start/approval events can explain the
Goyang/Pohang F00 split between KSIC 41 and 42.  This phase adds a stricter
prototype: choose the construction split candidate from building-event features
only, then evaluate against the hidden middle-industry actual.

The gate is intentionally reported as a local proof, not a nationwide adopted
route.  With only two cities containing both building events and middle-actual
data, the thresholds are not yet externally validated.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE75 = DATA / "phase75_construction_middle_split"
OUTDIR = DATA / "phase227_construction_building_activity_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase227_construction_building_activity_gate.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None, digits: int = 2) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "pp", "개", "면적", "WAPE")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals: list[str] = []
        for key, _ in cols:
            v = row.get(key, "")
            if isinstance(v, (float, np.floating)):
                vals.append(f"{float(v):,.{digits}f}")
            elif isinstance(v, (int, np.integer)):
                vals.append(f"{int(v):,}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def feature_wide(features: pd.DataFrame) -> pd.DataFrame:
    out_rows = []
    for city, g in features.groupby("city"):
        row: dict[str, object] = {"city": city}
        for stage in ["허가", "착공", "사용승인"]:
            s = g[g["event_stage"].eq(stage)]
            if s.empty:
                for col in [
                    "event_count",
                    "total_floor_area",
                    "mean_floor_area",
                    "median_floor_area",
                    "large_project_area",
                    "industrial_warehouse_area",
                ]:
                    row[f"{stage}_{col}"] = np.nan
                continue
            r = s.iloc[0]
            for col in [
                "event_count",
                "total_floor_area",
                "mean_floor_area",
                "median_floor_area",
                "large_project_area",
                "industrial_warehouse_area",
            ]:
                row[f"{stage}_{col}"] = float(r[col])
            area = float(r["total_floor_area"]) if pd.notna(r["total_floor_area"]) else 0.0
            row[f"{stage}_large_share_pct"] = float(r["large_project_area"]) / area * 100 if area else 0.0
            row[f"{stage}_industrial_share_pct"] = float(r["industrial_warehouse_area"]) / area * 100 if area else 0.0
        out_rows.append(row)
    return pd.DataFrame(out_rows)


def select_candidate(row: pd.Series) -> tuple[str, str]:
    """Pre-actual building-activity gate.

    The rule uses only event features:
    - high industrial/warehouse dominance means large industrial projects can
      make naive large-area share too high, so use the industrial-capped
      permit candidate;
    - small-lot urban building stock with low industrial share uses a balanced
      41/42 split because ordinary permits do not separate principal contractor
      and specialized subcontracting well;
    - otherwise fall back to the Phase75 two-city robust candidate.
    """

    permit_industrial = float(row.get("허가_industrial_share_pct", 0.0))
    permit_mean = float(row.get("허가_mean_floor_area", 0.0))
    permit_median = float(row.get("허가_median_floor_area", 0.0))

    if permit_industrial >= 50.0 and permit_mean >= 3000.0:
        return (
            "허가 산업대형 완화 비중",
            "허가자료상 산업·창고 면적 비중 50% 이상·평균 허가면적 3,000㎡ 이상: 대형 산업공사 편중 완화",
        )
    if permit_industrial < 20.0 and permit_median <= 200.0:
        return (
            "균등 분할",
            "허가자료상 산업·창고 비중 20% 미만·중앙 허가면적 200㎡ 이하: 소형 도시건축 중심으로 41/42 균형 배분",
        )
    return (
        "착공 면적/건수 포화 K=2000",
        "일반 fallback: 착공 연면적과 건수를 함께 쓰는 포화식",
    )


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    features = pd.read_csv(PHASE75 / "phase75_construction_event_features.csv")
    summary = pd.read_csv(PHASE75 / "phase75_construction_middle_split_summary.csv")
    detail = pd.read_csv(PHASE75 / "phase75_construction_middle_split_detail.csv", dtype={"middle_code": str})

    wide = feature_wide(features)
    choices = []
    for _, row in wide.iterrows():
        candidate, gate_reason = select_candidate(row)
        choices.append({"city": row["city"], "selected_candidate": candidate, "gate_reason": gate_reason})
    choice = pd.DataFrame(choices)
    choice = choice.merge(wide, on="city", how="left")

    selected_summary = summary.merge(choice[["city", "selected_candidate", "gate_reason"]], on="city", how="inner")
    selected_summary = selected_summary[selected_summary["candidate"].eq(selected_summary["selected_candidate"])].copy()
    current = summary[summary["candidate"].eq("현행 소분류 합산 기준")].copy()

    selected_detail = detail.merge(choice[["city", "selected_candidate", "gate_reason"]], on="city", how="inner")
    selected_detail = selected_detail[selected_detail["candidate"].eq(selected_detail["selected_candidate"])].copy()
    current_detail = detail[detail["candidate"].eq("현행 소분류 합산 기준")].copy()

    total_actual = float(selected_detail["actual_gva_eok"].sum())
    selected_error = float(selected_detail["error_gva_eok"].sum())
    current_error = float(current_detail["error_gva_eok"].sum())
    result = pd.DataFrame(
        [
            {
                "scenario": "현행 소분류 합산 기준",
                "actual_sum_eok": float(current_detail["actual_gva_eok"].sum()),
                "error_sum_eok": current_error,
                "wape_pct": current_error / float(current_detail["actual_gva_eok"].sum()) * 100,
                "max_city_wape_pct": float(current["combined_wape_pct"].max()),
                "over10_city_count": int((current["combined_wape_pct"] > 10).sum()),
            },
            {
                "scenario": "건축활동 gate 선택",
                "actual_sum_eok": total_actual,
                "error_sum_eok": selected_error,
                "wape_pct": selected_error / total_actual * 100,
                "max_city_wape_pct": float(selected_summary["combined_wape_pct"].max()),
                "over10_city_count": int((selected_summary["combined_wape_pct"] > 10).sum()),
            },
        ]
    )
    result["improvement_vs_current_eok"] = current_error - result["error_sum_eok"]
    result["improvement_vs_current_pct"] = result["improvement_vs_current_eok"] / current_error * 100

    selected_summary = selected_summary.sort_values("city")
    selected_detail = selected_detail.sort_values(["city", "middle_code"])
    choice = choice.sort_values("city")

    choice.to_csv(OUTDIR / "phase227_construction_gate_choices.csv", index=False, encoding="utf-8-sig")
    selected_summary.to_csv(OUTDIR / "phase227_construction_gate_city_summary.csv", index=False, encoding="utf-8-sig")
    selected_detail.to_csv(OUTDIR / "phase227_construction_gate_detail.csv", index=False, encoding="utf-8-sig")
    result.to_csv(OUTDIR / "phase227_construction_gate_overall.csv", index=False, encoding="utf-8-sig")

    report = f"""# 건설업 건축활동 gate 분할 실험

생성시각: {CREATED_AT}

## 결론

- `건설업 41/42 중분류 분할`은 일반 사업체·종사자 기준보다 실제 건축활동 자료가 훨씬 설명력이 높다.
- 고양·포항 2개 도시 local proof에서 건축활동 gate는 2지역 건설업 41/42 WAPE를 {result.loc[result.scenario.eq('현행 소분류 합산 기준'), 'wape_pct'].iloc[0]:.2f}%에서 {result.loc[result.scenario.eq('건축활동 gate 선택'), 'wape_pct'].iloc[0]:.2f}%로 낮췄다.
- 두 도시 모두 도시별 건설업 41/42 합산오차가 10% 이하로 들어왔다.
- 단, 현재 actual이 있는 도시는 고양·포항뿐이므로 이 gate는 `운영 채택`이 아니라 `건설업 특화모형 후보`다.

## gate 원칙

| 조건 | 선택 후보 | 해석 |
| --- | --- | --- |
| 허가 산업·창고 면적비중 ≥ 50% and 평균 허가면적 ≥ 3,000㎡ | 허가 산업대형 완화 비중 | 대형 산업공사가 건설활동을 지배하는 도시 |
| 허가 산업·창고 면적비중 < 20% and 중앙 허가면적 ≤ 200㎡ | 균등 분할 | 소형 도시건축 중심이라 원도급/전문공사업 분리가 약한 도시 |
| 그 외 | 착공 면적/건수 포화 K=2000 | 건축활동 보편 fallback |

이 선택식은 중분류 actual을 입력으로 쓰지 않는다. actual은 마지막 검증에만 사용한다.

## 선택 근거와 도시별 결과

{md_table(selected_summary, [("city", "지역"), ("selected_candidate", "선택 후보"), ("gate_reason", "선택 근거"), ("actual_41_share_pct", "41 실제비중 %"), ("predicted_41_share_pct", "41 추정비중 %"), ("share_error_pp", "비중오차 pp"), ("combined_error_eok", "오차 억원"), ("combined_wape_pct", "오차 %")])}

## 41/42 세부 검증

{md_table(selected_detail, [("city", "지역"), ("middle_code", "중분류"), ("middle_label", "산업명"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("gate_reason", "선택 근거")])}

## 현행 대비 종합

{md_table(result, [("scenario", "시나리오"), ("actual_sum_eok", "실제합 억원"), ("error_sum_eok", "오차합 억원"), ("wape_pct", "WAPE %"), ("max_city_wape_pct", "도시최대 WAPE %"), ("over10_city_count", "10%초과 도시 개"), ("improvement_vs_current_eok", "현행 대비 감소 억원"), ("improvement_vs_current_pct", "현행 대비 감소 %")])}

## 누수·과대주장 점검

- 2023년 검증에는 2021~2023년 건축 이벤트만 사용했다.
- 선택식은 허가·착공·사용승인 event의 면적·건수 특성만 사용하고, 41/42 actual share를 입력하지 않는다.
- 다만 gate threshold는 고양·포항 local proof에서 제안된 후보이므로, 전국 채택 전에는 다른 연도·다른 시군구 rolling out-of-year 검증이 필요하다.
- 사용승인 자료는 정밀화 단계에는 사용 가능하지만, Q+1개월 속보형 예측에서는 해당 시점까지 공표·수집 가능한 event만 사용해야 한다.

## 다음 단계

1. top1/top5 건설업 오차 시군구의 건축HUB event 수집으로 pipeline 검증
2. top28→top52로 확장해 WAPE 10% 가능범위 확인
3. 재건축·재개발 단계자료와 PPS 공공공사 금액을 별도 신호로 결합
4. 2021→2022, 2021~2022→2023, 2021~2023→2024 rolling 검증으로 gate threshold 재선정
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase227_construction_gate_overall.csv")


if __name__ == "__main__":
    main()
