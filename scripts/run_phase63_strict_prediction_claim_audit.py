#!/usr/bin/env python3
"""Strict audit of poster prediction-accuracy claims.

The project predicts accounting-constrained GVA.  Many available actuals are
not GVA itself at the target resolution, so this audit separates:
  1) direct GVA validation,
  2) adjacent distribution validation (sales/establishments/employees), and
  3) accounting identity checks.

The goal is to prevent poster language such as "1% prediction" from being
stronger than the evidence permits.
"""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "partial_statistics_estimation_phase63_strict_prediction_claim_audit.md"
DATA = ROOT / "data" / "processed"


def rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def f(x):
    try:
        return float(x)
    except Exception:
        return None


def main() -> None:
    goyang = list(rows(DATA / "partial_stats_phase41_industry_error_diagnostics.csv"))
    pohang = list(rows(DATA / "partial_stats_phase45_pohang_final_industry_diagnostics.csv"))
    accuracy = list(rows(DATA / "partial_stats_phase41_all_ksic_accuracy_matrix.csv"))

    goyang_middle = [r for r in goyang if r["industry_level"] == "middle" and int(float(r["cells"])) > 1]
    goyang_small = [r for r in goyang if r["industry_level"] == "small" and int(float(r["cells"])) > 1]
    goyang_small_le1 = [r for r in goyang_small if f(r["proxy_mae_pp"]) is not None and f(r["proxy_mae_pp"]) <= 1.0]
    goyang_middle_le1 = [r for r in goyang_middle if f(r["proxy_mae_pp"]) is not None and f(r["proxy_mae_pp"]) <= 1.0]

    pohang_combined_le1 = [r for r in pohang if f(r["combined_cv_score_pp"]) is not None and f(r["combined_cv_score_pp"]) <= 1.0]
    pohang_all_axes_le1 = [
        r for r in pohang
        if all(f(r.get(c)) is not None and f(r.get(c)) <= 1.0 for c in ["industry_cv_mae_pp", "spatial_cv_mae_pp", "gu_sales_cv_mae_pp"])
    ]

    weak_pohang = [r for r in pohang if str(r["industry_name"]).startswith(("농업", "임업"))]

    def md_table(data, cols, limit=20):
        if not data:
            return "\n해당 없음\n"
        s = "| " + " | ".join(label for _key, label in cols) + " |\n"
        s += "| " + " | ".join("---" for _ in cols) + " |\n"
        for r in data[:limit]:
            vals = []
            for key, _label in cols:
                val = r.get(key, "")
                try:
                    if val != "":
                        vals.append(f"{float(val):.3f}")
                    else:
                        vals.append("")
                except Exception:
                    vals.append(str(val))
            s += "| " + " | ".join(vals) + " |\n"
        return s

    acc_lines = []
    for r in accuracy:
        if r["time_level"] in {"분기", "월"}:
            acc_lines.append(f"- {r['industry_level']}×{r['time_level']}×{r['geo_level']}: {r['validation']} / {r['metric']} / 제한: {r['critical_limit']}")

    report = f"""# Phase63 예측성능 주장 엄격 검증

## 판정 요약

- 예측 대상은 총부가가치(GVA)다.
- 고양시·포항시의 행정동×소분류×월 실제 GVA는 존재하지 않으므로, 해당 해상도에서 “실제 GVA를 1% 이내로 예측”했다고 말할 수 없다.
- 1% 안팎 수치는 대부분 `매출·사업체·종사자 등 인접 실제값 분포` 또는 `여러 검증축 평균`의 오차다.
- 월·분기 합계 일치는 회계 제약 검증이지 예측 정확도 검증이 아니다.

## 고양시 1% 주장 점검

- 중분류에서 셀이 2개 이상인 산업군 중 1%p 이하 MAE는 {len(goyang_middle_le1)}개다.
- 소분류에서 셀이 2개 이상인 산업군 중 1%p 이하 MAE는 {len(goyang_small_le1)}개다.
- 단, 이는 2015 경제총조사 매출비중 숨김검증이며 행정동×월 GVA actual 검증이 아니다.
- 특히 소분류 패널에서 `농림어업`처럼 대분류명을 쓰면 “농림어업 자체가 소분류”처럼 보이므로, 포스터에는 내부 세부업종명 또는 “소분류 포함 산업군”으로 표현해야 한다.

{md_table(goyang_small_le1, [("parent_code","상위 산업군"),("cells","소분류 셀"),("proxy_mae_pp","MAE pp"),("uniform_mae_pp","균등 MAE pp"),("worst_industry_name","최대오차 세부업종")])}

## 포항시 1% 주장 점검

- 종합오차 평균 기준 1%p 이하 업종은 {len(pohang_combined_le1)}개다.
- 그러나 산업축·공간축·구 매출축 세 검증축이 모두 1%p 이하인 업종은 {len(pohang_all_axes_le1)}개다.
- 따라서 포항 포스터의 표현은 “일부 업종은 종합 검증오차가 1% 안팎”까지가 안전하다.

{md_table(pohang_combined_le1, [("industry_code","KSIC 중분류"),("industry_name","업종"),("industry_cv_mae_pp","산업축"),("spatial_cv_mae_pp","공간축"),("gu_sales_cv_mae_pp","구 검증축"),("combined_cv_score_pp","종합")])}

## 포항 농업·임업 취약성

{md_table(weak_pohang, [("industry_code","KSIC"),("industry_name","업종"),("industry_cv_mae_pp","산업축"),("spatial_cv_mae_pp","공간축"),("gu_sales_cv_mae_pp","구 검증축"),("combined_cv_score_pp","종합")])}

농업·임업의 오차를 10%p 전후로 낮추려면 사업체·종사자 기준을 버리고 생산량·면적·자원량 기반으로 나눠야 한다. 농업은 작물별 재배면적, 농산물 생산량/생산액, 농업경영체, 농지대장, 시설원예 면적이 필요하다. 임업은 산림면적, 임상도, 임산물 생산량, 벌채·조림 실적, 산림경영계획 인가자료가 필요하다. 포항은 읍면동 단위 해안·산지·도심 격차가 커서, 농업/임업을 한 업종군으로 묶으면 10%대 진입이 어렵다.

## 월·분기 해상도 검증 한계

{chr(10).join(acc_lines[:12])}

## 포스터 반영 원칙

1. “총부가가치 예측”을 제목·방법의 중심에 둔다.
2. 매출·사업체·종사자 오차는 “GVA 배분 검증오차”로만 표현한다.
3. “1% 이내 예측”은 금지한다. 대신 “일부 업종의 종합 검증오차 1% 안팎”으로 쓴다.
4. 소분류 패널은 대분류명을 단독 표기하지 않는다.
5. 개선효과 별도 소개 패널은 제거하고, 신뢰등급·검증한계·활용범위 패널로 대체한다.
"""
    OUT.write_text(report, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
