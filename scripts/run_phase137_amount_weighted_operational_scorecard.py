#!/usr/bin/env python3
"""Phase137: amount-weighted operational GVA scorecard.

This phase consolidates the rolling-vintage nowcast outputs and the latest
post-publication precision registries into an amount-weighted scorecard for
Goyang and Pohang.

Why this exists:
percentage errors alone over-emphasize small industries.  For the requested
operational use, large-GVA industries with moderate percentage errors may matter
more than tiny industries with huge percentage errors.  The scorecard therefore
separates:

* high-value industries and their WAPE by quarterly vintage;
* small-value high-percentage errors that should be monitored but not over-sold;
* top 2023 absolute-error contributors for the next data-collection queue.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase137_amount_weighted_operational_scorecard"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase137_amount_weighted_operational_scorecard.md"

ROLLING = DATA / "phase131_rolling_vintage_gva_update" / "phase131_rolling_vintage_predictions.csv"
GOYANG_PRECISION = DATA / "phase130_goyang_precision_adoption" / "phase130_goyang_precision_registry.csv"
POHANG_PRECISION = DATA / "phase127_precision_comwel_after_phase114" / "phase127_strict_registry.csv"

LARGE_EOK = 1000.0
VERY_LARGE_EOK = 5000.0


def amount_bucket(v: pd.Series) -> pd.Series:
    return np.select(
        [v.ge(VERY_LARGE_EOK), v.ge(LARGE_EOK)],
        ["very_large_5000eok_plus", "large_1000_5000eok"],
        default="small_under_1000eok",
    )


def rolling_scorecard() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(ROLLING, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    eval_df = df[df["year"].ge(2022)].copy()
    eval_df["amount_bucket"] = amount_bucket(eval_df["actual_annual_gva_eok"])
    rows = []
    for keys, g in eval_df.groupby(["city", "vintage_id", "vintage_label", "available_quarters", "amount_bucket"], sort=False):
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        rows.append({
            "city": keys[0],
            "vintage_id": keys[1],
            "vintage_label": keys[2],
            "available_quarters": int(keys[3]),
            "amount_bucket": keys[4],
            "evaluated_years": "2022-2023",
            "cell_count": int(len(g)),
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "wape_pct": err / actual * 100 if actual else np.nan,
            "gt10_cells": int((g["annual_error_rate_pct"] > 10).sum()),
            "gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
        })
    bucket_score = pd.DataFrame(rows).sort_values(["city", "available_quarters", "amount_bucket"])

    total_rows = []
    for keys, g in eval_df.groupby(["city", "vintage_id", "vintage_label", "available_quarters"], sort=False):
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        high = g[g["actual_annual_gva_eok"].ge(LARGE_EOK)]
        small = g[g["actual_annual_gva_eok"].lt(LARGE_EOK)]
        total_rows.append({
            "city": keys[0],
            "vintage_id": keys[1],
            "vintage_label": keys[2],
            "available_quarters": int(keys[3]),
            "evaluated_years": "2022-2023",
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "overall_wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_actual_sum_eok": float(high["actual_annual_gva_eok"].sum()),
            "high_value_error_sum_eok": float(high["annual_error_eok"].sum()),
            "high_value_wape_pct": float(high["annual_error_eok"].sum()) / float(high["actual_annual_gva_eok"].sum()) * 100 if len(high) else np.nan,
            "small_high_pct_cells": int((small["annual_error_rate_pct"] > 20).sum()),
            "all_gt20_cells": int((g["annual_error_rate_pct"] > 20).sum()),
        })
    total_score = pd.DataFrame(total_rows).sort_values(["city", "available_quarters"])

    detail_2023 = df[df["year"].eq(2023)].copy()
    detail_2023["amount_bucket"] = amount_bucket(detail_2023["actual_annual_gva_eok"])
    detail_2023["error_contribution_pct"] = detail_2023.groupby(["city", "vintage_id"])["annual_error_eok"].transform(
        lambda s: s / s.sum() * 100 if s.sum() else 0
    )
    top_nowcast = (
        detail_2023[detail_2023["available_quarters"].isin([1, 2, 3])]
        .sort_values(["city", "available_quarters", "annual_error_eok"], ascending=[True, True, False])
        .groupby(["city", "available_quarters"], as_index=False)
        .head(8)
    )
    return bucket_score, total_score, top_nowcast


def precision_registry() -> pd.DataFrame:
    frames = []
    if GOYANG_PRECISION.exists():
        g = pd.read_csv(GOYANG_PRECISION, dtype={"middle_code": str})
        g = g[g["city"].eq("고양시")].copy()
        g["middle_code"] = g["middle_code"].astype(str).str.zfill(2)
        g["precision_track"] = "phase130_goyang"
        g["prediction_eok"] = g["phase130_predicted_gva_eok"]
        g["error_eok"] = g["phase130_error_gva_eok"]
        g["error_rate_pct"] = g["phase130_error_rate_pct"]
        frames.append(g[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "prediction_eok", "error_eok", "error_rate_pct", "precision_track"]])
    if POHANG_PRECISION.exists():
        p = pd.read_csv(POHANG_PRECISION, dtype={"middle_code": str})
        p = p[p["city"].eq("포항시")].copy()
        p["middle_code"] = p["middle_code"].astype(str).str.zfill(2)
        p["precision_track"] = "phase127_pohang_strict"
        p["prediction_eok"] = p["phase127_strict_predicted_gva_eok"]
        p["error_eok"] = p["phase127_strict_error_gva_eok"]
        p["error_rate_pct"] = p["phase127_strict_error_rate_pct"]
        frames.append(p[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "prediction_eok", "error_eok", "error_rate_pct", "precision_track"]])
    out = pd.concat(frames, ignore_index=True)
    out["amount_bucket"] = amount_bucket(out["actual_gva_eok"])
    out["error_contribution_pct"] = out.groupby("city")["error_eok"].transform(lambda s: s / s.sum() * 100 if s.sum() else 0)
    return out


def precision_scorecard(reg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bucket_rows = []
    for keys, g in reg.groupby(["city", "amount_bucket"], sort=False):
        actual = float(g["actual_gva_eok"].sum())
        err = float(g["error_eok"].sum())
        bucket_rows.append({
            "city": keys[0],
            "amount_bucket": keys[1],
            "target_year": 2023,
            "cell_count": int(len(g)),
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "wape_pct": err / actual * 100 if actual else np.nan,
            "gt10_cells": int((g["error_rate_pct"] > 10).sum()),
            "gt20_cells": int((g["error_rate_pct"] > 20).sum()),
        })
    bucket = pd.DataFrame(bucket_rows).sort_values(["city", "amount_bucket"])

    total_rows = []
    for city, g in reg.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        err = float(g["error_eok"].sum())
        high = g[g["actual_gva_eok"].ge(LARGE_EOK)]
        small = g[g["actual_gva_eok"].lt(LARGE_EOK)]
        total_rows.append({
            "city": city,
            "target_year": 2023,
            "precision_track": g["precision_track"].iloc[0],
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "overall_wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_actual_sum_eok": float(high["actual_gva_eok"].sum()),
            "high_value_error_sum_eok": float(high["error_eok"].sum()),
            "high_value_wape_pct": float(high["error_eok"].sum()) / float(high["actual_gva_eok"].sum()) * 100 if len(high) else np.nan,
            "small_high_pct_cells": int((small["error_rate_pct"] > 20).sum()),
            "all_gt20_cells": int((g["error_rate_pct"] > 20).sum()),
        })
    total = pd.DataFrame(total_rows)

    top = reg.sort_values(["city", "error_eok"], ascending=[True, False]).groupby("city", as_index=False).head(12)
    small_high = reg[reg["actual_gva_eok"].lt(LARGE_EOK) & reg["error_rate_pct"].gt(20)].sort_values(["city", "error_eok"], ascending=[True, False])
    return bucket, total, top, small_high


def improvement_queue(precision_top: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in precision_top.iterrows():
        direct_need = "직접 활동자료/지역 매출자료"
        if r["parent_code"] == "ERS" and r["middle_code"] == "91":
            direct_need = "체육·오락 이용객·매출·회원권·시설가동률"
        elif r["parent_code"] == "J00" and r["middle_code"] in {"59", "60"}:
            direct_need = "영상·방송 기업 매출·제작지원·촬영/상영 활동"
        elif r["parent_code"] == "C00":
            direct_need = "제조업 세부 부가가치·공장규모·고용보험 세부업종 holdout"
        elif r["parent_code"] == "MN0":
            direct_need = "계약·수주·사업장 면적·전문서비스 매출"
        rows.append({
            "city": r["city"],
            "parent_code": r["parent_code"],
            "middle_code": r["middle_code"],
            "middle_label": r["middle_label"],
            "actual_gva_eok": float(r["actual_gva_eok"]),
            "error_eok": float(r["error_eok"]),
            "error_rate_pct": float(r["error_rate_pct"]),
            "error_contribution_pct": float(r["error_contribution_pct"]),
            "amount_bucket": r["amount_bucket"],
            "priority_reason": "large absolute gap" if r["actual_gva_eok"] >= LARGE_EOK or r["error_eok"] >= 100 else "monitor as small high-percent cell",
            "needed_data": direct_need,
        })
    return pd.DataFrame(rows).sort_values(["city", "error_eok"], ascending=[True, False])


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    labels = [c.replace("_eok", " 억원").replace("_pct", " %").replace("_", " ") for c in d.columns]

    def fmt(v: object) -> str:
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            if np.isfinite(float(v)) and abs(float(v) - round(float(v))) < 1e-9:
                return f"{int(round(float(v))):,}"
            return f"{float(v):,.2f}"
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        return str(v).replace("|", "\\|")

    body = ["| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *body])


def write_report(total_roll: pd.DataFrame, bucket_roll: pd.DataFrame, total_prec: pd.DataFrame, bucket_prec: pd.DataFrame, top_prec: pd.DataFrame, small_high: pd.DataFrame, queue: pd.DataFrame) -> None:
    q3_roll = total_roll[total_roll["available_quarters"].eq(3)]
    REPORT.write_text("\n".join([
        "# Phase137 금액가중 운영형 GVA scorecard",
        "",
        "## 목적",
        "",
        "고양·포항 GVA 예측을 상대오차만이 아니라 금액규모별 WAPE로 재정렬했다. 작은 업종의 큰 %오차와 큰 업종의 큰 억원 격차를 분리해, 다음 자료수집·모델개선 우선순위를 정하기 위한 운영형 scorecard다.",
        "",
        "## rolling annual nowcast 총괄: 2022~2023",
        "",
        md_table(total_roll, ["city", "vintage_label", "evaluated_years", "actual_sum_eok", "error_sum_eok", "overall_wape_pct", "high_value_error_sum_eok", "high_value_wape_pct", "small_high_pct_cells", "all_gt20_cells"]),
        "",
        "## Q3+1개월 시점 금액가중 상태",
        "",
        md_table(q3_roll, ["city", "vintage_label", "overall_wape_pct", "high_value_wape_pct", "small_high_pct_cells", "all_gt20_cells"]),
        "",
        "## rolling annual nowcast 금액규모별 WAPE",
        "",
        md_table(bucket_roll, ["city", "vintage_label", "amount_bucket", "cell_count", "actual_sum_eok", "error_sum_eok", "wape_pct", "gt10_cells", "gt20_cells"], n=80),
        "",
        "## 2023 정밀화 총괄",
        "",
        md_table(total_prec, ["city", "precision_track", "actual_sum_eok", "error_sum_eok", "overall_wape_pct", "high_value_error_sum_eok", "high_value_wape_pct", "small_high_pct_cells", "all_gt20_cells"]),
        "",
        "## 2023 정밀화 금액규모별 WAPE",
        "",
        md_table(bucket_prec, ["city", "amount_bucket", "cell_count", "actual_sum_eok", "error_sum_eok", "wape_pct", "gt10_cells", "gt20_cells"]),
        "",
        "## 2023 정밀화 금액격차 상위",
        "",
        md_table(top_prec, ["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "prediction_eok", "error_eok", "error_rate_pct", "error_contribution_pct", "amount_bucket"], n=24),
        "",
        "## 작은 금액·높은 %오차 분리",
        "",
        md_table(small_high, ["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "error_eok", "error_rate_pct", "error_contribution_pct"], n=24),
        "",
        "## 다음 개선 큐",
        "",
        md_table(queue, ["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "error_eok", "error_rate_pct", "priority_reason", "needed_data"], n=24),
        "",
        "## 판정",
        "",
        "1. 운영 평가는 `전체 WAPE`, `1,000억원 이상 업종 WAPE`, `작은 금액 고%오차 셀 수`를 함께 봐야 한다.",
        "2. Q4+1개월의 0% 오차는 예측력이 아니라 1~4분기 합계가 연간 최종값을 회계적으로 회수한다는 뜻이다. 운영 성능 비교는 Q1~Q3 빈티지를 중심으로 해석해야 한다.",
        "3. 작은 금액 업종의 20% 초과 상대오차는 품질 경보로 남기되, 공모전·정책 설명에서는 억원 격차와 오차 기여도를 병기해야 한다.",
        "4. 고양시는 스포츠·오락, 방송·영상, 일부 제조업이 금액격차 우선순위다. KOBIS는 J59 시간패턴에 채택하지 않는 것이 검증상 안전하므로, 고양시 고유 영상·체육 매출/이용량 자료가 다음 핵심이다.",
        "5. 포항시는 전문서비스·건축기술·사업시설관리 등 MN0 계열의 금액격차가 크다. 단순 사업장 수보다 수주·계약·전문인력·사업장 규모 자료가 필요하다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bucket_roll, total_roll, top_nowcast = rolling_scorecard()
    reg = precision_registry()
    bucket_prec, total_prec, top_prec, small_high = precision_scorecard(reg)
    queue = improvement_queue(top_prec)

    bucket_roll.to_csv(OUT / "phase137_rolling_amount_bucket_scorecard.csv", index=False)
    total_roll.to_csv(OUT / "phase137_rolling_total_scorecard.csv", index=False)
    top_nowcast.to_csv(OUT / "phase137_2023_nowcast_top_error_contributors.csv", index=False)
    reg.to_csv(OUT / "phase137_precision_registry_normalized.csv", index=False)
    bucket_prec.to_csv(OUT / "phase137_precision_amount_bucket_scorecard.csv", index=False)
    total_prec.to_csv(OUT / "phase137_precision_total_scorecard.csv", index=False)
    top_prec.to_csv(OUT / "phase137_precision_top_error_contributors.csv", index=False)
    small_high.to_csv(OUT / "phase137_small_amount_high_pct_cells.csv", index=False)
    queue.to_csv(OUT / "phase137_next_improvement_queue.csv", index=False)
    write_report(total_roll, bucket_roll, total_prec, bucket_prec, top_prec, small_high, queue)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
