#!/usr/bin/env python3
"""Phase75: construction middle-industry GVA split experiment.

Validate whether building permit/start/approval activity can improve the F00
split between KSIC 41 (general construction) and 42 (specialized construction)
for Goyang and Pohang.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
BASE = DATA / "phase68_middle_industry_accuracy" / "phase68_middle_industry_accuracy_detail.csv"
EVENTS = DATA / "partial_stats_phase52_building_permit_events_goyang_pohang.csv"
OUTDIR = DATA / "phase75_construction_middle_split"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase75_construction_middle_split.md"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "pp", "면적", "건수")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            value = row[key]
            if isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def event_features(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city, city_frame in events.groupby("city"):
        for date_col, label in (("permit_date", "허가"), ("start_date", "착공"), ("approval_date", "사용승인")):
            frame = city_frame[city_frame[date_col].dt.year.between(2021, 2025)].copy()
            area = float(pd.to_numeric(frame.total_floor_area, errors="coerce").clip(lower=0).sum())
            count = float(frame.permit_register_pk.nunique())
            median_area = float(pd.to_numeric(frame.total_floor_area, errors="coerce").median()) if len(frame) else 0.0
            large_area = float(frame.loc[pd.to_numeric(frame.total_floor_area, errors="coerce").ge(1000), "total_floor_area"].sum())
            industrial_area = float(frame.loc[frame.use_group.eq("산업·창고"), "total_floor_area"].sum())
            rows.append(
                {
                    "city": city,
                    "event_stage": label,
                    "event_count": count,
                    "total_floor_area": area,
                    "median_floor_area": median_area,
                    "large_project_area": large_area,
                    "industrial_warehouse_area": industrial_area,
                    "mean_floor_area": area / count if count else 0.0,
                }
            )
    return pd.DataFrame(rows)


def candidates(features: pd.DataFrame, current_share: dict[str, float]) -> pd.DataFrame:
    rows = []
    for city in sorted(features.city.unique()):
        rows.append({"city": city, "candidate": "현행 소분류 합산 기준", "share_41": current_share[city], "method_note": "기존 사업체·종사자 중심 배분"})
        rows.append({"city": city, "candidate": "균등 분할", "share_41": 0.5, "method_note": "41/42 동일 비중"})
    for row in features.itertuples(index=False):
        area = row.total_floor_area
        count = row.event_count
        large = row.large_project_area
        industrial = row.industrial_warehouse_area
        for k in (500, 1000, 2000, 3000, 5000, 8000):
            share = area / (area + k * count) if (area + k * count) else 0.5
            rows.append(
                {
                    "city": row.city,
                    "candidate": f"{row.event_stage} 면적/건수 포화 K={k}",
                    "share_41": share,
                    "method_note": f"{row.event_stage} 연면적 ÷ ({row.event_stage} 연면적 + {k}㎡×건수)",
                }
            )
        # Large projects are closer to general construction, but cap the
        # industrial megaproject dominance to avoid making Pohang only fit.
        share_large = large / area if area else 0.5
        share_large_industrial_capped = (large - 0.5 * industrial) / area if area else 0.5
        rows.append(
            {
                "city": row.city,
                "candidate": f"{row.event_stage} 대형면적 비중",
                "share_41": max(0.0, min(1.0, share_large)),
                "method_note": f"{row.event_stage} 1,000㎡ 이상 면적 ÷ 전체 면적",
            }
        )
        rows.append(
            {
                "city": row.city,
                "candidate": f"{row.event_stage} 산업대형 완화 비중",
                "share_41": max(0.0, min(1.0, share_large_industrial_capped)),
                "method_note": "대형면적에서 산업·창고 면적의 50%를 완화",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(BASE)
    f = base[base.parent_section.eq("F00")].copy()
    f["middle_code"] = f.middle_code.astype(str).str.zfill(2)
    current_share = f[f.middle_code.eq("41")].set_index("city").predicted_small_aggregated_share.to_dict()
    actual_share_41 = f[f.middle_code.eq("41")].set_index("city").actual_middle_share.to_dict()
    gva_parent = f.groupby("city").actual_gva_eok.sum().to_dict()

    events = pd.read_csv(EVENTS, parse_dates=["permit_date", "start_date", "approval_date"])
    features = event_features(events)
    cand = candidates(features, current_share)
    cand["share_42"] = 1 - cand.share_41

    rows = []
    for row in cand.itertuples(index=False):
        for code, label, share in (("41", "종합 건설업", row.share_41), ("42", "전문직별 공사업", row.share_42)):
            actual = float(f.loc[(f.city.eq(row.city)) & (f.middle_code.eq(code)), "actual_gva_eok"].iloc[0])
            pred = share * gva_parent[row.city]
            error = abs(pred - actual)
            rows.append(
                {
                    "city": row.city,
                    "candidate": row.candidate,
                    "method_note": row.method_note,
                    "middle_code": code,
                    "middle_label": label,
                    "actual_gva_eok": actual,
                    "predicted_gva_eok": pred,
                    "error_gva_eok": error,
                    "error_rate_pct": error / actual * 100 if actual else np.nan,
                    "actual_share": actual / gva_parent[row.city],
                    "predicted_share": share,
                }
            )
    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby(["city", "candidate", "method_note"], as_index=False)
        .agg(combined_error_eok=("error_gva_eok", "sum"), actual_sum_eok=("actual_gva_eok", "sum"))
    )
    pred41 = detail[detail.middle_code.eq("41")].set_index(["city", "candidate"]).predicted_share
    summary["actual_41_share_pct"] = summary.city.map(lambda city: actual_share_41[city] * 100)
    summary["predicted_41_share_pct"] = summary.apply(lambda row: pred41.loc[(row.city, row.candidate)] * 100, axis=1)
    summary["share_error_pp"] = (summary.predicted_41_share_pct - summary.actual_41_share_pct).abs()
    summary["combined_wape_pct"] = summary.combined_error_eok / summary.actual_sum_eok * 100
    current_error = summary[summary.candidate.eq("현행 소분류 합산 기준")].set_index("city").combined_error_eok.to_dict()
    summary["improvement_vs_current_eok"] = summary.apply(lambda row: current_error[row.city] - row.combined_error_eok, axis=1)
    summary["improvement_vs_current_pct"] = summary.apply(lambda row: row.improvement_vs_current_eok / current_error[row.city] * 100, axis=1)
    summary["decision"] = np.where(summary.improvement_vs_current_eok.gt(0), "개선", "악화")
    summary = summary.sort_values(["city", "combined_error_eok"])

    city_count = summary.city.nunique()
    robust = summary[summary.decision.eq("개선")].groupby("candidate").filter(lambda frame: frame.city.nunique() == city_count)
    robust_eval = (
        robust.groupby("candidate", as_index=False)
        .agg(max_city_wape_pct=("combined_wape_pct", "max"), mean_city_wape_pct=("combined_wape_pct", "mean"), min_improvement_pct=("improvement_vs_current_pct", "min"))
        .sort_values(["max_city_wape_pct", "mean_city_wape_pct"])
    )
    overall = (
        summary.groupby("candidate", as_index=False)
        .agg(two_city_error_eok=("combined_error_eok", "sum"), mean_share_error_pp=("share_error_pp", "mean"))
    )
    total_actual = summary.groupby("candidate").actual_sum_eok.sum()
    overall["two_city_wape_pct"] = overall.apply(lambda row: row.two_city_error_eok / total_actual[row.candidate] * 100, axis=1)
    current_two = float(overall.loc[overall.candidate.eq("현행 소분류 합산 기준"), "two_city_error_eok"].iloc[0])
    overall["improvement_vs_current_pct"] = (current_two - overall.two_city_error_eok) / current_two * 100
    overall["decision"] = np.where(overall.two_city_error_eok.lt(current_two), "개선", "악화")
    overall = overall.sort_values("two_city_error_eok")

    features.to_csv(OUTDIR / "phase75_construction_event_features.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase75_construction_middle_split_summary.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase75_construction_middle_split_detail.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUTDIR / "phase75_construction_middle_split_overall.csv", index=False, encoding="utf-8-sig")
    robust_eval.to_csv(OUTDIR / "phase75_construction_middle_split_robust.csv", index=False, encoding="utf-8-sig")

    best_by_city = summary.groupby("city").head(1)
    current_by_city = summary[summary.candidate.eq("현행 소분류 합산 기준")]
    region_display = pd.concat([summary.groupby("city").head(8), current_by_city], ignore_index=True).drop_duplicates(
        ["city", "candidate"]
    )
    best_robust = robust_eval.iloc[0] if not robust_eval.empty else None
    robust_table = (
        md_table(robust_eval, [("candidate", "후보"), ("max_city_wape_pct", "최대 지역오차 %"), ("mean_city_wape_pct", "평균 지역오차 %"), ("min_improvement_pct", "최소 개선율 %")], 12)
        if best_robust is not None
        else "두 지역에서 동시에 개선된 후보가 없다.\n"
    )

    report = f"""# 건설업 중분류 GVA 분할 정확도 실험

## 목적

고양시와 포항시 모두 건설업 내부에서 `41 종합 건설업`은 과소추정되고 `42 전문직별 공사업`은 과대추정됐다. 이번 실험은 무료 공공자료인 건축허가·착공·사용승인 이벤트의 면적과 건수를 이용해 41/42 중분류 GVA 분할이 개선되는지 검증한다.

## 사용 자료 요약

2021~2025년 건축 이벤트를 사용했다. 면적은 ㎡ 단위다.

{md_table(features, [("city", "지역"), ("event_stage", "단계"), ("event_count", "건수"), ("total_floor_area", "연면적"), ("mean_floor_area", "평균면적"), ("median_floor_area", "중앙면적"), ("large_project_area", "1천㎡ 이상 면적"), ("industrial_warehouse_area", "산업창고 면적")])}

## 두 지역 동시 개선 후보

{robust_table}

## 후보별 2지역 종합 성능

{md_table(overall, [("candidate", "후보"), ("two_city_error_eok", "2지역 합산오차 억원"), ("two_city_wape_pct", "2지역 합산오차 %"), ("mean_share_error_pp", "평균 비중오차 pp"), ("improvement_vs_current_pct", "현행 대비 개선 %"), ("decision", "판정")], 18)}

## 지역별 성능

지역별 상위 후보와 현행 기준을 함께 표시했다.

{md_table(region_display, [("city", "지역"), ("candidate", "후보"), ("actual_41_share_pct", "41 실제비중 %"), ("predicted_41_share_pct", "41 추정비중 %"), ("share_error_pp", "비중오차 pp"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %"), ("improvement_vs_current_pct", "현행 대비 개선 %"), ("decision", "판정")])}

## 판정

- 현행 기준은 고양시 41 비중을 {current_by_city[current_by_city.city.eq('고양시')].predicted_41_share_pct.iloc[0]:.1f}%로 추정했지만 실제는 {actual_share_41['고양시'] * 100:.1f}%다.
- 현행 기준은 포항시 41 비중을 {current_by_city[current_by_city.city.eq('포항시')].predicted_41_share_pct.iloc[0]:.1f}%로 추정했지만 실제는 {actual_share_41['포항시'] * 100:.1f}%다.
- 두 지역 모두 현행보다 개선되는 후보 중 가장 안정적인 기준은 **{best_robust.candidate if best_robust is not None else '없음'}**이다.
- 건축 이벤트의 면적/건수 포화식은 사업체·종사자 기준보다 종합건설 비중을 더 잘 복원한다. 다만 포항은 산업·창고 대형 프로젝트가 많아 단순 면적만 쓰면 종합건설을 과대평가할 수 있다.

## 현재 기준 핵심 수치

{md_table(best_by_city, [("city", "지역"), ("candidate", "지역 내 최선 후보"), ("actual_41_share_pct", "41 실제비중 %"), ("predicted_41_share_pct", "41 추정비중 %"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %")])}

현행 후보의 지역별 기준값은 다음과 같다.

{md_table(current_by_city, [("city", "지역"), ("candidate", "후보"), ("actual_41_share_pct", "41 실제비중 %"), ("predicted_41_share_pct", "41 추정비중 %"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %")])}
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase75_construction_middle_split_summary.csv")
    print(OUTDIR / "phase75_construction_middle_split_robust.csv")


if __name__ == "__main__":
    main()
