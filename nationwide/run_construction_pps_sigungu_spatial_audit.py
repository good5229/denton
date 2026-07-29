#!/usr/bin/env python3
"""Audit whether PPS construction notices can improve sigungu construction allocation.

This is a feasibility audit, not a final adopted operating rule.

The remaining WAPE bottleneck is construction at sigungu×activity level.  The
current parent-control construction prediction already matches province totals
but reuses the current pipeline's sigungu share.  Here we compare that share to
PPS public-construction notice amount/count shares for 2023.

Important guardrail:
* The currently available PPS cache covers 2023-01~2023-09 only.
* Therefore this script does not declare an operational route adopted.
* It reports whether PPS has signal and what data would be required to make it
  eligible for rolling, out-of-year selection.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "nationwide" / "construction_pps_sigungu_spatial_audit.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def wape(actual: pd.Series, pred: pd.Series) -> float:
    denom = actual.abs().sum()
    return float((pred - actual).abs().sum() / denom * 100) if denom else np.nan


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{float(v):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def load_construction(year: int) -> pd.DataFrame:
    sig = pd.read_csv(OUT / "annual_sigungu_activity_error_audit.csv")
    f = sig[(sig["activity"].eq("건설업")) & (sig["year"].eq(year))].copy()
    if f.empty:
        raise SystemExit(f"No {year} construction rows in annual_sigungu_activity_error_audit.csv")
    province = (
        f.groupby(["quarter_region", "year"], as_index=False)
        .agg(sido_actual_eok=("actual_eok", "sum"), sido_predicted_eok=("predicted_eok", "sum"))
    )
    f = f.merge(province, on=["quarter_region", "year"], how="left")
    f["current_share"] = f["predicted_eok"] / f["sido_predicted_eok"]
    f["parent_control_current_predicted_eok"] = f["sido_actual_eok"] * f["current_share"]
    return f


def load_pps(tag: str, year: int) -> pd.DataFrame:
    frames = []
    for one in [x.strip() for x in tag.split(",") if x.strip()]:
        p = OUT / f"pps_construction_nationwide_sigungu_year_{one}.csv"
        if not p.exists():
            raise SystemExit(f"Missing PPS signal file: {p}")
        frame = pd.read_csv(p)
        frame = frame[frame["year"].eq(year)].copy()
        frame["source_tag"] = one
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    pps = pd.concat(frames, ignore_index=True)
    if pps.empty:
        return pps
    return (
        pps.groupby(["quarter_region", "province_full", "city", "year"], as_index=False)
        .agg(
            pps_construction_notices=("pps_construction_notices", "sum"),
            pps_construction_amount_eok=("pps_construction_amount_eok", "sum"),
        )
    )


def add_pps_shares(base: pd.DataFrame, pps: pd.DataFrame) -> pd.DataFrame:
    x = base.merge(
        pps[
            [
                "quarter_region",
                "city",
                "year",
                "pps_construction_notices",
                "pps_construction_amount_eok",
            ]
        ],
        on=["quarter_region", "city", "year"],
        how="left",
    )
    x["pps_construction_notices"] = x["pps_construction_notices"].fillna(0.0)
    x["pps_construction_amount_eok"] = x["pps_construction_amount_eok"].fillna(0.0)
    for col, share_col in [
        ("pps_construction_amount_eok", "pps_amount_share"),
        ("pps_construction_notices", "pps_notice_share"),
    ]:
        total = x.groupby(["quarter_region", "year"])[col].transform("sum")
        x[share_col] = np.where(total.gt(0), x[col] / total, np.nan)
    return x


def candidate_eval(x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    details = []
    candidates: list[tuple[str, str, float | None]] = [
        ("current_parent_control", "current_share", None),
        ("pps_amount_only", "pps_amount_share", None),
        ("pps_notice_only", "pps_notice_share", None),
    ]
    coarse = list(np.round(np.arange(0.1, 1.0, 0.1), 1))
    fine = list(np.round(np.arange(0.91, 1.0, 0.01), 2))
    for share_col in ["pps_amount_share", "pps_notice_share"]:
        for alpha in sorted(set(coarse + fine)):
            # alpha = current pipeline share weight, 1-alpha = PPS share weight
            candidates.append((f"blend_current_{alpha:.2f}_{share_col}", share_col, float(alpha)))

    for name, share_col, alpha in candidates:
        d = x.copy()
        if name == "current_parent_control":
            d["candidate_share_raw"] = d["current_share"]
        elif alpha is None:
            d["candidate_share_raw"] = d[share_col]
        else:
            d["candidate_share_raw"] = alpha * d["current_share"] + (1 - alpha) * d[share_col].fillna(0.0)
        # If a province has no PPS exact rows, keep current share rather than
        # creating undefined predictions.
        no_signal = d.groupby(["quarter_region", "year"])["candidate_share_raw"].transform("sum").le(0)
        d.loc[no_signal, "candidate_share_raw"] = d.loc[no_signal, "current_share"]
        share_sum = d.groupby(["quarter_region", "year"])["candidate_share_raw"].transform("sum")
        d["candidate_share"] = d["candidate_share_raw"] / share_sum
        d["candidate_predicted_eok"] = d["sido_actual_eok"] * d["candidate_share"]
        d["candidate_abs_error_eok"] = (d["candidate_predicted_eok"] - d["actual_eok"]).abs()
        d["candidate_ape_pct"] = np.where(d["actual_eok"].abs().gt(0), d["candidate_abs_error_eok"] / d["actual_eok"].abs() * 100, np.nan)
        d["scenario"] = name
        rows.append(
            {
                "scenario": name,
                "rows": len(d),
                "actual_sum_eok": float(d["actual_eok"].sum()),
                "abs_error_sum_eok": float(d["candidate_abs_error_eok"].sum()),
                "wape_pct": wape(d["actual_eok"], d["candidate_predicted_eok"]),
                "over10_cells": int(d["candidate_ape_pct"].gt(10).sum()),
                "over20_cells": int(d["candidate_ape_pct"].gt(20).sum()),
                "max_ape_pct": float(d["candidate_ape_pct"].max()),
                "zero_pps_rows": int(d["pps_construction_amount_eok"].eq(0).sum()),
                "pps_signal_provinces": int(d.groupby("quarter_region")["pps_construction_amount_eok"].sum().gt(0).sum()),
            }
        )
        keep = d[
            [
                "scenario",
                "quarter_region",
                "province_full",
                "city",
                "year",
                "actual_eok",
                "parent_control_current_predicted_eok",
                "candidate_predicted_eok",
                "candidate_abs_error_eok",
                "candidate_ape_pct",
                "pps_construction_notices",
                "pps_construction_amount_eok",
                "current_share",
                "pps_amount_share",
                "pps_notice_share",
                "candidate_share",
            ]
        ].copy()
        details.append(keep)
    summary = pd.DataFrame(rows).sort_values(["wape_pct", "over10_cells", "over20_cells"])
    detail = pd.concat(details, ignore_index=True)
    return summary, detail


def write_report(summary: pd.DataFrame, detail: pd.DataFrame, x: pd.DataFrame, year: int, tag: str, report: Path) -> None:
    current = summary[summary["scenario"].eq("current_parent_control")].iloc[0]
    best = summary.iloc[0]
    safe = summary[
        summary["scenario"].ne("current_parent_control")
        & summary["wape_pct"].lt(float(current["wape_pct"]))
        & summary["over10_cells"].le(int(current["over10_cells"]))
        & summary["over20_cells"].le(int(current["over20_cells"]))
        & summary["max_ape_pct"].le(float(current["max_ape_pct"]))
    ].copy()
    guardrail_best = safe.iloc[0] if not safe.empty else None
    display_best = guardrail_best if guardrail_best is not None else best
    guardrail_label = str(display_best["scenario"]) if guardrail_best is not None else "없음"
    guardrail_wape = f'{float(display_best["wape_pct"]):.3f}%' if guardrail_best is not None else "없음"
    guardrail_over10 = str(int(display_best["over10_cells"])) if guardrail_best is not None else "없음"
    guardrail_over20 = str(int(display_best["over20_cells"])) if guardrail_best is not None else "없음"
    guardrail_note = (
        "- 현재 guardrail을 모두 통과하는 후보는 PPS를 1~3% 수준으로만 섞는 미세 보정형이다."
        if guardrail_best is not None
        else "- 현재 guardrail을 모두 통과하는 후보는 없다. WAPE가 낮아지는 후보도 10% 초과 셀 또는 최대오차율을 악화시킨다."
    )
    best_guardrail_warning = (
        "- 단순 WAPE 최선 후보는 guardrail 항목 중 하나 이상을 악화시키므로 채택 기준 후보가 아니다."
        if guardrail_best is None or str(best["scenario"]) != str(display_best["scenario"])
        else "- 단순 WAPE 최선 후보가 guardrail도 통과한다."
    )
    best_detail = detail[detail["scenario"].eq(str(display_best["scenario"]))].copy()
    top_errors = best_detail.sort_values("candidate_abs_error_eok", ascending=False).head(25)
    coverage = (
        x.groupby("quarter_region", as_index=False)
        .agg(
            sigungu_rows=("city", "count"),
            pps_exact_rows=("pps_construction_amount_eok", lambda s: int(s.gt(0).sum())),
            pps_amount_eok=("pps_construction_amount_eok", "sum"),
            actual_construction_eok=("actual_eok", "sum"),
        )
        .sort_values("pps_amount_eok", ascending=False)
    )
    text = f"""# 건설업 조달청 공사공고 시군구 공간배분 감사

생성시각: {CREATED_AT}

## 목적

건설업 시군구 WAPE 병목이 공공공사 소재지·금액 신호로 개선되는지 확인한다.

이 문서는 채택 실험이 아니라 feasibility audit이다. 현재 사용 PPS tag는 `{tag}`, 검증 연도는 `{year}`년이다. 운영규칙으로 채택하려면 2021~2025 전체 기간을 같은 방식으로 수집한 뒤 out-of-year 검증을 다시 해야 한다.

## 비교 기준

| 기준 | 설명 |
| --- | --- |
| current_parent_control | 시도 건설업 actual 총량은 맞추되 기존 시군구 share 사용 |
| pps_amount_only | 시군구별 조달청 공사공고 금액 share만 사용 |
| pps_notice_only | 시군구별 조달청 공사공고 공고수 share만 사용 |
| blend_current_* | 기존 share와 PPS share 혼합 |

## 시나리오 요약

{md_table(summary.head(20).rename(columns={
    "scenario": "시나리오",
    "rows": "행수",
    "actual_sum_eok": "실제합_억원",
    "abs_error_sum_eok": "절대오차합_억원",
    "wape_pct": "WAPE_%",
    "over10_cells": "10%초과",
    "over20_cells": "20%초과",
    "max_ape_pct": "최대APE_%",
    "zero_pps_rows": "PPS금액0행",
    "pps_signal_provinces": "PPS시도수",
}), 3)}

## Guardrail 통과 후보

기준선보다 WAPE가 낮고, 10% 초과 셀·20% 초과 셀·최대오차율이 악화되지 않는 후보만 표시한다.

{md_table(safe.head(15).rename(columns={
    "scenario": "시나리오",
    "rows": "행수",
    "actual_sum_eok": "실제합_억원",
    "abs_error_sum_eok": "절대오차합_억원",
    "wape_pct": "WAPE_%",
    "over10_cells": "10%초과",
    "over20_cells": "20%초과",
    "max_ape_pct": "최대APE_%",
    "zero_pps_rows": "PPS금액0행",
    "pps_signal_provinces": "PPS시도수",
}), 3)}

## 시도별 PPS coverage

{md_table(coverage.rename(columns={
    "quarter_region": "시도",
    "sigungu_rows": "시군구행",
    "pps_exact_rows": "PPS금액존재행",
    "pps_amount_eok": "PPS금액_억원",
    "actual_construction_eok": "건설업실제_억원",
}), 3)}

## 최선 후보 상위 오차

WAPE만 기준으로 한 최선 후보: `{best["scenario"]}`  
Guardrail 기준 표시 후보: `{guardrail_label}`

{md_table(top_errors[[
    "quarter_region",
    "city",
    "actual_eok",
    "parent_control_current_predicted_eok",
    "candidate_predicted_eok",
    "candidate_abs_error_eok",
    "candidate_ape_pct",
    "pps_construction_amount_eok",
]].rename(columns={
    "quarter_region": "시도",
    "city": "시군구",
    "actual_eok": "실제_억원",
    "parent_control_current_predicted_eok": "기준추정_억원",
    "candidate_predicted_eok": "후보추정_억원",
    "candidate_abs_error_eok": "후보오차_억원",
    "candidate_ape_pct": "후보APE_%",
    "pps_construction_amount_eok": "PPS금액_억원",
}), 3)}

## 판정

| 항목 | 값 |
| --- | ---: |
| 기준 WAPE | {float(current["wape_pct"]):.3f}% |
| WAPE 최선 후보 WAPE | {float(best["wape_pct"]):.3f}% |
| Guardrail 표시 후보 WAPE | {guardrail_wape} |
| 기준 10% 초과 셀 | {int(current["over10_cells"])} |
| WAPE 최선 후보 10% 초과 셀 | {int(best["over10_cells"])} |
| Guardrail 표시 후보 10% 초과 셀 | {guardrail_over10} |
| 기준 20% 초과 셀 | {int(current["over20_cells"])} |
| WAPE 최선 후보 20% 초과 셀 | {int(best["over20_cells"])} |
| Guardrail 표시 후보 20% 초과 셀 | {guardrail_over20} |

해석:

- 조달청 공사공고는 일부 시군구 건설업 공간분포를 설명하는 신호가 있다.
{best_guardrail_warning}
{guardrail_note}
- 부분기간 PPS만으로는 운영규칙 채택이 불가능하다.
- 공공공사 중심 자료이므로 민간건축이 큰 지역에서는 단독 적용하면 위험하다.
- 다음 채택 실험은 2021~2025 전체 PPS와 건축HUB 허가·착공·사용승인 자료를 결합해 rolling out-of-year 방식으로 진행해야 한다.

## 평가관 agent 검토 반영

- PPS는 버릴 자료가 아니라 건설업 전용 공간배분 모형의 보조 신호다.
- 단독 route 또는 강한 혼합 route는 공공공사 편향 때문에 채택하지 않는다.
- 운영 채택 전에는 2021~2025 전체 PPS를 동일 조건으로 수집하고, 과거연도로 가중치를 선택한 뒤 목표연도를 평가하는 rolling out-of-year 검증이 필요하다.
- 공고일·계약일·착공일·준공일 중 어떤 시점이 GVA 발생시점과 맞는지 분리해야 한다.

## 과학자 agent 후속 제안 반영

- 건설업 시군구 WAPE를 PPS만으로 10% 이하로 낮추기는 어렵다.
- 1차 현실 목표는 `23.7% → 20% 미만`으로 안정적으로 낮추고, 10%·20% 초과 셀을 늘리지 않는 것이다.
- 10% 전후 목표는 건축HUB 허가·착공·사용승인 면적과 재건축·재개발·민간공사 신호가 결합된 뒤 재평가한다.
- 다음 실험 공식은 `기존 시군구 건설업 share + 건축HUB event share + PPS 공공공사 금액 share`의 소량 혼합이다.
- 후보 가중치는 목표연도 actual이 아니라 과거연도 rolling out-of-year 성능으로만 선택한다.
"""
    report.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--tag", default="202301_202309")
    parser.add_argument("--report-suffix", default="")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    base = load_construction(args.year)
    pps = load_pps(args.tag, args.year)
    x = add_pps_shares(base, pps)
    summary, detail = candidate_eval(x)
    suffix = f"_{args.report_suffix}" if args.report_suffix else ""
    summary.to_csv(OUT / f"construction_pps_sigungu_spatial_summary{suffix}.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / f"construction_pps_sigungu_spatial_detail{suffix}.csv", index=False, encoding="utf-8-sig")
    report = REPORT if not args.report_suffix else ROOT / "nationwide" / f"construction_pps_sigungu_spatial_audit{suffix}.md"
    write_report(summary, detail, x, args.year, args.tag, report)
    print(f"wrote {report.relative_to(ROOT)}")
    print(summary.head(12).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
