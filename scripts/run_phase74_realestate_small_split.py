#!/usr/bin/env python3
"""Phase74: real-estate small-industry split accuracy.

This experiment checks whether free public real-estate stock/transaction/broker
data improves the split inside KSIC L00:

    681 real-estate rental and supply
    682 real-estate related services

The validation target is the hidden small-industry sales share used in earlier
holdout files.  Errors are also converted to 2023 L00 GVA amounts so that the
result answers "how accurate is the industry GVA estimate?" rather than only
share accuracy.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase74_realestate_small_split"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase74_realestate_small_split.md"


def large_gva(city: str, code: str = "L") -> float:
    path = (
        DATA / "partial_stats_phase41_all_ksic_multiresolution_cube.parquet"
        if city == "고양시"
        else DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet"
    )
    cube = pd.read_parquet(path, columns=["industry_level", "industry_code", "time_level", "period", "geo_level", "estimated_gva"])
    sub = cube[
        cube.industry_level.eq("대분류")
        & cube.industry_code.astype(str).eq(code)
        & cube.time_level.eq("연")
        & cube.period.astype(str).eq("2023")
        & cube.geo_level.eq("시")
    ]
    if sub.empty:
        raise RuntimeError(f"missing large GVA for {city} {code}")
    return float(sub.estimated_gva.sum()) / 100.0


def actual_and_current() -> pd.DataFrame:
    goyang = pd.read_csv(DATA / "partial_stats_phase41_all_ksic_holdout_detail.csv")
    goyang = goyang[(goyang.industry_level.eq("small")) & (goyang.parent_code.eq("L00"))].copy()
    goyang = goyang.rename(columns={"actual_sales_share": "actual_share", "predicted_proxy_share": "current_share"})
    goyang["city"] = "고양시"
    pohang = pd.read_csv(DATA / "partial_stats_phase42_pohang_industry_holdout_detail.csv")
    pohang = pohang[(pohang.industry_level.eq("소분류")) & (pohang.parent_code.eq("L00"))].copy()
    pohang = pohang.rename(columns={"predicted_share": "current_share"})
    pohang["city"] = "포항시"
    keep = ["city", "industry_code", "actual_share", "current_share", "uniform_share"]
    out = pd.concat([goyang[keep], pohang[keep]], ignore_index=True)
    out["industry_code"] = out.industry_code.astype(str)
    return out


def feature_table() -> pd.DataFrame:
    building = pd.read_csv(DATA / "partial_stats_phase51_realestate_admin_name_direct_features.csv")
    housing = pd.read_parquet(DATA / "phase56_housing_price" / "molit_public_housing_price_2025_goyang_pohang.parquet")
    broker = pd.read_csv(DATA / "partial_stats_phase53_realestate_broker_goyang_pohang.csv")
    rtms = pd.read_csv(DATA / "partial_stats_phase55_rtms_apt_trade_goyang_pohang_2024.csv")

    rows = []
    for city in ("고양시", "포항시"):
        b = building[building.city.eq(city)]
        residential_area = float(b.loc[b.use_group.eq("주거"), "total_floor_area"].sum())
        commercial_area = float(b.loc[b.use_group.eq("상업·업무"), "total_floor_area"].sum())
        if city == "고양시":
            h = housing[housing["시군구"].astype(str).str.contains("고양", na=False)]
        else:
            h = housing[housing["시군구"].astype(str).str.contains("포항", na=False)]
        assessed_value_eok = float(pd.to_numeric(h["공시가격"], errors="coerce").sum() / 1e8)
        br = broker[broker.city.eq(city)]
        broker_count = float(len(br))
        r = rtms[rtms.city.eq(city)]
        transaction_value_eok = float(pd.to_numeric(r.deal_amount_10k_krw, errors="coerce").sum() * 1e4 / 1e8)
        rows.append(
            {
                "city": city,
                "residential_area_sqm": residential_area,
                "commercial_area_sqm": commercial_area,
                "assessed_housing_value_eok": assessed_value_eok,
                "broker_count": broker_count,
                "transaction_value_eok": transaction_value_eok,
                "stock_value_per_broker_eok": assessed_value_eok / broker_count if broker_count else np.nan,
                "transaction_turnover_rate_pct": transaction_value_eok / assessed_value_eok * 100 if assessed_value_eok else np.nan,
            }
        )
    return pd.DataFrame(rows)


def candidate_shares(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in features.itertuples(index=False):
        city = row.city
        area_share = row.residential_area_sqm / (row.residential_area_sqm + row.commercial_area_sqm)
        stock_dominance = row.assessed_housing_value_eok / (
            row.assessed_housing_value_eok + row.transaction_value_eok + row.broker_count
        )
        turnover_inverse = max(0.0, min(1.0, 1 - row.transaction_turnover_rate_pct / 100))
        rows.extend(
            [
                {"city": city, "candidate": "현행 소분류 합산 기준", "share_681": np.nan, "method_note": "기존 사업체·종사자 중심 배분"},
                {"city": city, "candidate": "균등 분할", "share_681": 0.5, "method_note": "681/682 동일 비중"},
                {"city": city, "candidate": "주거·상업 면적 기준", "share_681": area_share, "method_note": "주거 연면적 ÷ 주거+상업업무 연면적"},
                {"city": city, "candidate": "주택재고 우위 기준", "share_681": stock_dominance, "method_note": "공시가격총액 ÷ 공시가격총액+거래액+중개업소수"},
                {"city": city, "candidate": "거래회전율 역수 기준", "share_681": turnover_inverse, "method_note": "1 - 아파트 거래액/공시가격총액"},
            ]
        )
        for k in (300, 500, 700, 900):
            share = row.stock_value_per_broker_eok / (row.stock_value_per_broker_eok + k)
            rows.append(
                {
                    "city": city,
                    "candidate": f"재고가치/중개업소 포화 기준 K={k}",
                    "share_681": share,
                    "method_note": f"공시가격총액/중개업소수 ÷ (공시가격총액/중개업소수 + {k})",
                }
            )
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, columns: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    lines = ["| " + " | ".join(label for _, label in columns) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "K=", "수", "면적")) else "---" for _, label in columns) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in columns:
            value = row[key]
            if isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    actual = actual_and_current()
    features = feature_table()
    candidates = candidate_shares(features)

    # Fill current shares by city from the 681 row.
    current_681 = actual[actual.industry_code.eq("681")].set_index("city").current_share.to_dict()
    candidates["share_681"] = candidates.apply(
        lambda row: current_681[row.city] if row.candidate == "현행 소분류 합산 기준" else row.share_681,
        axis=1,
    )
    candidates["share_682"] = 1 - candidates.share_681

    rows = []
    for cand in candidates.itertuples(index=False):
        gva = large_gva(cand.city, "L")
        for code, label, share in (("681", "부동산 임대 및 공급업", cand.share_681), ("682", "부동산 관련 서비스업", cand.share_682)):
            actual_share = float(actual.loc[(actual.city.eq(cand.city)) & (actual.industry_code.eq(code)), "actual_share"].iloc[0])
            actual_eok = actual_share * gva
            pred_eok = share * gva
            error_eok = abs(pred_eok - actual_eok)
            rows.append(
                {
                    "city": cand.city,
                    "candidate": cand.candidate,
                    "method_note": cand.method_note,
                    "industry_code": code,
                    "industry_name": label,
                    "actual_share": actual_share,
                    "predicted_share": share,
                    "actual_gva_eok": actual_eok,
                    "predicted_gva_eok": pred_eok,
                    "error_gva_eok": error_eok,
                    "error_rate_pct": error_eok / actual_eok * 100 if actual_eok else np.nan,
                }
            )
    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby(["city", "candidate", "method_note"], as_index=False)
        .agg(
            combined_error_eok=("error_gva_eok", "sum"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            share_error_pp=("actual_share", lambda _: np.nan),
        )
    )
    share_681_actual = actual[actual.industry_code.eq("681")].set_index("city").actual_share.to_dict()
    pred_681 = detail[detail.industry_code.eq("681")].set_index(["city", "candidate"]).predicted_share
    summary["actual_681_share_pct"] = summary.city.map(lambda city: share_681_actual[city] * 100)
    summary["predicted_681_share_pct"] = summary.apply(lambda row: pred_681.loc[(row.city, row.candidate)] * 100, axis=1)
    summary["share_error_pp"] = (summary.predicted_681_share_pct - summary.actual_681_share_pct).abs()
    summary["combined_wape_pct"] = summary.combined_error_eok / summary.actual_sum_eok * 100
    current_error = summary[summary.candidate.eq("현행 소분류 합산 기준")].set_index("city").combined_error_eok.to_dict()
    summary["improvement_vs_current_eok"] = summary.apply(lambda row: current_error[row.city] - row.combined_error_eok, axis=1)
    summary["improvement_vs_current_pct"] = summary.apply(
        lambda row: row.improvement_vs_current_eok / current_error[row.city] * 100 if current_error[row.city] else np.nan,
        axis=1,
    )
    summary["decision"] = np.where(summary.improvement_vs_current_eok.gt(0), "개선", "악화")
    overall = (
        summary.groupby(["candidate", "method_note"], as_index=False)
        .agg(two_city_error_eok=("combined_error_eok", "sum"), two_city_wape_pct=("combined_error_eok", "sum"), mean_share_error_pp=("share_error_pp", "mean"))
    )
    total_actual = summary.drop_duplicates(["city", "candidate"]).groupby("candidate").actual_sum_eok.sum()
    overall["two_city_wape_pct"] = overall.apply(lambda row: row.two_city_error_eok / total_actual[row.candidate] * 100, axis=1)
    current_two = float(overall.loc[overall.candidate.eq("현행 소분류 합산 기준"), "two_city_error_eok"].iloc[0])
    overall["improvement_vs_current_pct"] = (current_two - overall.two_city_error_eok) / current_two * 100
    overall["decision"] = np.where(overall.two_city_error_eok.lt(current_two), "개선", "악화")
    summary = summary.sort_values(["city", "combined_error_eok"])
    overall = overall.sort_values("two_city_error_eok")

    features.to_csv(OUTDIR / "phase74_realestate_feature_summary.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase74_realestate_small_split_summary.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase74_realestate_small_split_detail.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUTDIR / "phase74_realestate_small_split_overall.csv", index=False, encoding="utf-8-sig")

    best_by_city = summary.groupby("city").head(1)
    city_count = summary.city.nunique()
    robust_candidates = summary[summary.decision.eq("개선")].groupby("candidate").filter(lambda frame: frame.city.nunique() == city_count)
    robust_eval = (
        robust_candidates.groupby("candidate", as_index=False)
        .agg(max_city_wape_pct=("combined_wape_pct", "max"), mean_city_wape_pct=("combined_wape_pct", "mean"), min_improvement_pct=("improvement_vs_current_pct", "min"))
        .sort_values(["max_city_wape_pct", "mean_city_wape_pct"])
    )
    best_overall = overall.iloc[0]
    best_robust = robust_eval.iloc[0] if not robust_eval.empty else None
    robust_table = (
        md_table(robust_eval, [("candidate", "후보"), ("max_city_wape_pct", "최대 지역오차 %"), ("mean_city_wape_pct", "평균 지역오차 %"), ("min_improvement_pct", "최소 개선율 %")])
        if best_robust is not None
        else "두 지역에서 동시에 개선된 후보가 없다.\n"
    )
    current_by_city = summary[summary.candidate.eq("현행 소분류 합산 기준")]
    report = f"""# 부동산업 소분류 GVA 분할 정확도 실험

## 목적

부동산업은 대분류/중분류가 사실상 하나(`L00 → 68`)라서 중분류 집계검증만으로는 내부 오차가 드러나지 않는다. 따라서 이번 실험은 `681 부동산 임대 및 공급업`과 `682 부동산 관련 서비스업`의 소분류 분할을 검증한다. 검증값은 기존 숨김검증의 소분류 실제 매출비중이고, 결과는 2023년 부동산업 GVA에 곱해 억원 단위 오차로 환산했다.

## 사용한 무료 자료

{md_table(features, [("city", "지역"), ("assessed_housing_value_eok", "공시가격 총액 억원"), ("broker_count", "중개업소 수"), ("transaction_value_eok", "아파트 거래액 억원"), ("residential_area_sqm", "주거 연면적"), ("commercial_area_sqm", "상업업무 연면적"), ("stock_value_per_broker_eok", "중개업소당 공시가격 억원"), ("transaction_turnover_rate_pct", "거래회전율 %")])}

## 후보별 2지역 종합 성능

{md_table(overall, [("candidate", "후보"), ("two_city_error_eok", "2지역 합산오차 억원"), ("two_city_wape_pct", "2지역 합산오차 %"), ("mean_share_error_pp", "평균 비중오차 pp"), ("improvement_vs_current_pct", "현행 대비 개선 %"), ("decision", "판정")])}

## 두 지역 동시 개선 후보

아래 표는 고양시와 포항시에서 모두 현행보다 나아진 후보만 남긴 것이다. 특정 한 지역의 GVA 규모가 커서 전체 합산오차만 낮아지는 후보는 제외했다.

{robust_table}

## 지역별 성능

{md_table(summary, [("city", "지역"), ("candidate", "후보"), ("actual_681_share_pct", "681 실제비중 %"), ("predicted_681_share_pct", "681 추정비중 %"), ("share_error_pp", "비중오차 pp"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %"), ("improvement_vs_current_pct", "현행 대비 개선 %"), ("decision", "판정")], 18)}

## 판정

- 고양시는 현행이 681 비중을 7.0%로 추정했지만 실제는 60.6%였다. 사업체·종사자 중심 배분이 중개·관리 서비스업 쪽으로 과도하게 쏠린다.
- 포항시는 실제 681 비중이 22.6%로 고양보다 훨씬 낮다. 따라서 고양에 맞춘 주택재고 중심 기준을 그대로 적용하면 포항에서 악화될 수 있다.
- 2지역 합산오차만 보면 **{best_overall.candidate}**이 가장 작다. 그러나 이 후보는 지역별 악화 여부를 함께 확인해야 한다.
- 두 지역 모두 현행보다 개선되는 후보만 남기면 **{best_robust.candidate if best_robust is not None else '없음'}**이 가장 안정적이다.
- 현재까지의 엄격 판정은 `부동산업은 단순 사업체·종사자 기준을 버려야 하지만, 무료자료만으로 고양·포항에 동시에 안정적인 공통식은 아직 부족`이다.

## 개선 방향

1. 고양시 포스터에는 “부동산업 내부 분할은 중개업소 수만 쓰면 임대·공급업을 과소평가한다”는 진단을 넣는 편이 안전하다.
2. 실제 개선모델은 임대·공급업에는 공시가격·주거/상업 연면적·임대료 지표를, 관련 서비스업에는 중개업소·거래건수·거래액·관리대상 건축물 수를 분리 적용해야 한다.
3. 10% 전후 오차를 목표로 하려면 전월세 실거래, 상업용 임대료, 집합건물 관리업체/관리면적, 신규분양·공급물량이 필요하다.

## 현재 기준 핵심 수치

{md_table(best_by_city, [("city", "지역"), ("candidate", "지역 내 최선 후보"), ("actual_681_share_pct", "681 실제비중 %"), ("predicted_681_share_pct", "681 추정비중 %"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %")])}

현행 후보의 지역별 기준값은 다음과 같다.

{md_table(current_by_city, [("city", "지역"), ("candidate", "후보"), ("actual_681_share_pct", "681 실제비중 %"), ("predicted_681_share_pct", "681 추정비중 %"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %")])}
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase74_realestate_small_split_summary.csv")
    print(OUTDIR / "phase74_realestate_small_split_overall.csv")


if __name__ == "__main__":
    main()
