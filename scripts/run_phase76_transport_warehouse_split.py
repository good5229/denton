#!/usr/bin/env python3
"""Phase76: transport/warehouse middle-industry GVA split experiment.

Validate H00 split across:
  49 land transport
  50 water transport
  52 warehousing and transport support

using currently available free public data.  Port cargo is not available in the
current processed/raw state, so water transport candidates are explicitly
treated as provisional rather than promoted.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "phase50_free_vulnerable_sources"
BASE = DATA / "phase68_middle_industry_accuracy" / "phase68_middle_industry_accuracy_detail.csv"
OUTDIR = DATA / "phase76_transport_warehouse_split"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase76_transport_warehouse_split.md"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "pp", "수", "면적", "승객")) else "---" for _, label in cols) + " |")
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


def active_mask(frame: pd.DataFrame) -> pd.Series:
    status = frame.get("영업상태명", pd.Series("", index=frame.index)).astype(str)
    detail = frame.get("상세영업상태명", pd.Series("", index=frame.index)).astype(str)
    return status.str.contains("영업|정상", na=False) | detail.str.contains("영업|정상", na=False)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.replace("-", "", regex=False), errors="coerce")


def feature_table() -> pd.DataFrame:
    rows = []
    bus_path = DATA / "phase59_transport_bus_signal" / "phase59_goyang_bus_monthly_feature.csv"
    bus = pd.read_csv(bus_path)
    bus_goyang_2023 = float(bus[bus.month.astype(str).str.startswith("2023")].passenger_total.sum())
    korail = pd.read_csv(DATA / "partial_stats_phase53_korail_station_daily_goyang_pohang.csv", parse_dates=["date"])
    for city, slug in (("고양시", "goyang"), ("포항시", "pohang")):
        k = korail[(korail.city.eq(city)) & (korail.date.dt.year.eq(2023))]
        rail_passenger = float((pd.to_numeric(k.boarding, errors="coerce") + pd.to_numeric(k.alighting, errors="coerce")).sum())
        bus_passenger = bus_goyang_2023 if city == "고양시" else 0.0
        wh = pd.read_csv(RAW / f"localdata_logistics_warehouses_{slug}.csv", encoding="cp949", low_memory=False)
        active = active_mask(wh)
        general_area = num(wh.loc[active, "일반창고면적"]).sum()
        cold_area = num(wh.loc[active, "냉동냉장창고면적"]).sum()
        storage_area = num(wh.loc[active, "보관장소면적"]).sum()
        staff = num(wh.loc[active, "직원수"]).sum()
        rows.append(
            {
                "city": city,
                "bus_passenger_2023": bus_passenger,
                "rail_passenger_2023": rail_passenger,
                "passenger_total_2023": bus_passenger + rail_passenger,
                "warehouse_count": float(active.sum()),
                "warehouse_area_sqm": float(general_area + cold_area + storage_area),
                "warehouse_staff": float(staff),
                "port_cargo_available": "N",
            }
        )
    return pd.DataFrame(rows)


def normalize3(a: float, b: float, c: float) -> tuple[float, float, float]:
    s = a + b + c
    if s <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    return a / s, b / s, c / s


def candidates(features: pd.DataFrame, current: dict[tuple[str, str], float]) -> pd.DataFrame:
    rows = []
    for f in features.itertuples(index=False):
        city = f.city
        rows.append(
            {
                "city": city,
                "candidate": "현행 소분류 합산 기준",
                "share_49": current[(city, "49")],
                "share_50": current[(city, "50")],
                "share_52": current[(city, "52")],
                "method_note": "기존 사업체·종사자 중심 배분",
            }
        )
        rows.append(
            {
                "city": city,
                "candidate": "균등 분할",
                "share_49": 1 / 3,
                "share_50": 1 / 3,
                "share_52": 1 / 3,
                "method_note": "49/50/52 동일 비중",
            }
        )
        # Candidate 1: keep water transport at current because port cargo is
        # missing, and split the remaining share by log passenger vs log
        # warehouse capacity.
        water = current[(city, "50")]
        land_score = np.log1p(f.passenger_total_2023)
        wh_score = np.log1p(f.warehouse_area_sqm + 100 * f.warehouse_count + 10 * f.warehouse_staff)
        land_resid, wh_resid, _ = normalize3(land_score, wh_score, 0)
        rows.append(
            {
                "city": city,
                "candidate": "승객·창고 로그 기준 + 수상 현행유지",
                "share_49": (1 - water) * land_resid,
                "share_50": water,
                "share_52": (1 - water) * wh_resid,
                "method_note": "수상운송은 현행 유지, 나머지는 log(승객)·log(창고규모) 분할",
            }
        )
        # Candidate 2: allow a minimum water share for a port city, but mark it
        # as provisional in the report.
        water_floor = 0.07 if city == "포항시" else max(water, 0.002)
        water = max(water, water_floor)
        land_resid, wh_resid, _ = normalize3(land_score, wh_score, 0)
        rows.append(
            {
                "city": city,
                "candidate": "승객·창고 로그 기준 + 항만도시 최소비중",
                "share_49": (1 - water) * land_resid,
                "share_50": water,
                "share_52": (1 - water) * wh_resid,
                "method_note": "포항 수상운송 최소 7%; 항만 물동량 부재 시 임시 후보",
            }
        )
        # Candidate 3: shrink halfway from current to activity split.
        water = current[(city, "50")]
        activity_49 = (1 - water) * land_resid
        activity_52 = (1 - water) * wh_resid
        rows.append(
            {
                "city": city,
                "candidate": "현행-활동지표 50:50 혼합",
                "share_49": 0.5 * current[(city, "49")] + 0.5 * activity_49,
                "share_50": water,
                "share_52": 0.5 * current[(city, "52")] + 0.5 * activity_52,
                "method_note": "현행 구조와 승객·창고 로그 기준을 1:1 혼합",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(BASE)
    h = base[base.parent_section.eq("H00")].copy()
    h["middle_code"] = h.middle_code.astype(str).str.zfill(2)
    h = h[h.middle_code.isin(["49", "50", "52"])].copy()
    parent_gva = h.groupby("city").actual_gva_eok.sum().to_dict()
    current = h.set_index(["city", "middle_code"]).predicted_small_aggregated_share.to_dict()
    actual_share = h.set_index(["city", "middle_code"]).actual_middle_share.to_dict()
    features = feature_table()
    cand = candidates(features, current)
    for col in ["share_49", "share_50", "share_52"]:
        cand[col] = cand[col].astype(float)
    cand["share_sum"] = cand[["share_49", "share_50", "share_52"]].sum(axis=1)

    rows = []
    labels = {"49": "육상운송업", "50": "수상 운송업", "52": "창고·운송관련 서비스업"}
    for c in cand.itertuples(index=False):
        for code in ("49", "50", "52"):
            pred_share = getattr(c, f"share_{code}")
            actual = float(h.loc[(h.city.eq(c.city)) & (h.middle_code.eq(code)), "actual_gva_eok"].iloc[0])
            pred = pred_share * parent_gva[c.city]
            error = abs(pred - actual)
            rows.append(
                {
                    "city": c.city,
                    "candidate": c.candidate,
                    "method_note": c.method_note,
                    "middle_code": code,
                    "middle_label": labels[code],
                    "actual_share": actual_share[(c.city, code)],
                    "predicted_share": pred_share,
                    "actual_gva_eok": actual,
                    "predicted_gva_eok": pred,
                    "error_gva_eok": error,
                    "error_rate_pct": error / actual * 100 if actual else np.nan,
                }
            )
    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby(["city", "candidate", "method_note"], as_index=False)
        .agg(combined_error_eok=("error_gva_eok", "sum"), actual_sum_eok=("actual_gva_eok", "sum"))
    )
    for code in ("49", "50", "52"):
        pred = detail[detail.middle_code.eq(code)].set_index(["city", "candidate"]).predicted_share
        summary[f"actual_{code}_share_pct"] = summary.city.map(lambda city: actual_share[(city, code)] * 100)
        summary[f"predicted_{code}_share_pct"] = summary.apply(lambda row: pred.loc[(row.city, row.candidate)] * 100, axis=1)
        summary[f"error_{code}_pp"] = (summary[f"predicted_{code}_share_pct"] - summary[f"actual_{code}_share_pct"]).abs()
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
    overall = summary.groupby("candidate", as_index=False).agg(two_city_error_eok=("combined_error_eok", "sum"))
    total_actual = summary.groupby("candidate").actual_sum_eok.sum()
    overall["two_city_wape_pct"] = overall.apply(lambda row: row.two_city_error_eok / total_actual[row.candidate] * 100, axis=1)
    current_two = float(overall.loc[overall.candidate.eq("현행 소분류 합산 기준"), "two_city_error_eok"].iloc[0])
    overall["improvement_vs_current_pct"] = (current_two - overall.two_city_error_eok) / current_two * 100
    overall["decision"] = np.where(overall.two_city_error_eok.lt(current_two), "개선", "악화")
    overall = overall.sort_values("two_city_error_eok")

    features.to_csv(OUTDIR / "phase76_transport_feature_summary.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase76_transport_warehouse_split_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase76_transport_warehouse_split_summary.csv", index=False, encoding="utf-8-sig")
    robust_eval.to_csv(OUTDIR / "phase76_transport_warehouse_split_robust.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUTDIR / "phase76_transport_warehouse_split_overall.csv", index=False, encoding="utf-8-sig")

    best_by_city = summary.groupby("city").head(1)
    current_by_city = summary[summary.candidate.eq("현행 소분류 합산 기준")]
    display = pd.concat([summary.groupby("city").head(5), current_by_city], ignore_index=True).drop_duplicates(["city", "candidate"])
    best_robust = robust_eval.iloc[0] if not robust_eval.empty else None
    formal_robust = robust_eval[~robust_eval.candidate.str.contains("항만도시", regex=False)].copy()
    best_formal = formal_robust.iloc[0] if not formal_robust.empty else None
    robust_table = (
        md_table(robust_eval, [("candidate", "후보"), ("max_city_wape_pct", "최대 지역오차 %"), ("mean_city_wape_pct", "평균 지역오차 %"), ("min_improvement_pct", "최소 개선율 %")])
        if best_robust is not None
        else "두 지역에서 동시에 개선된 후보가 없다.\n"
    )
    report = f"""# 운수·창고업 중분류 GVA 분할 정확도 실험

## 목적

고양시와 포항시는 `49 육상운송업`이 과대추정되고 `52 창고·운송관련 서비스업`이 과소추정되는 공통 문제가 있었다. 이번 실험은 승객 이동량, 철도 이용량, 물류창고 면적을 이용해 H00 내부 GVA 분할이 개선되는지 검증한다.

## 사용 자료 요약

{md_table(features, [("city", "지역"), ("bus_passenger_2023", "버스 승객"), ("rail_passenger_2023", "철도 승객"), ("passenger_total_2023", "승객 합계"), ("warehouse_count", "창고 수"), ("warehouse_area_sqm", "창고 면적"), ("warehouse_staff", "창고 직원수"), ("port_cargo_available", "항만 물동량")])}

## 두 지역 동시 개선 후보

{robust_table}

## 후보별 2지역 종합 성능

{md_table(overall, [("candidate", "후보"), ("two_city_error_eok", "2지역 합산오차 억원"), ("two_city_wape_pct", "2지역 합산오차 %"), ("improvement_vs_current_pct", "현행 대비 개선 %"), ("decision", "판정")])}

## 지역별 성능

{md_table(display, [("city", "지역"), ("candidate", "후보"), ("actual_49_share_pct", "49 실제 %"), ("predicted_49_share_pct", "49 추정 %"), ("actual_50_share_pct", "50 실제 %"), ("predicted_50_share_pct", "50 추정 %"), ("actual_52_share_pct", "52 실제 %"), ("predicted_52_share_pct", "52 추정 %"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %"), ("improvement_vs_current_pct", "개선 %"), ("decision", "판정")])}

## 판정

- 현행 기준은 두 지역 모두 창고·운송관련 서비스업을 과소추정한다. 고양은 52 실제비중 {actual_share[('고양시', '52')] * 100:.1f}% 대비 현행 {current[('고양시', '52')] * 100:.1f}%, 포항은 실제 {actual_share[('포항시', '52')] * 100:.1f}% 대비 현행 {current[('포항시', '52')] * 100:.1f}%다.
- 두 지역 모두 현행보다 개선되는 후보 중 수치상 가장 안정적인 기준은 **{best_robust.candidate if best_robust is not None else '없음'}**이다.
- 그러나 `항만도시 최소비중`은 항만 물동량 없이 포항에 최소 수상운송 비중을 둔 임시 규칙이다. 정식 활동지표 후보는 **{best_formal.candidate if best_formal is not None else '없음'}**로 두는 것이 더 엄격하다.
- 포항의 수상운송은 항만 물동량 자료가 빠져 있어 정확도 한계가 남는다. 항만 물동량 수집 전까지 50 수상운송은 승격하지 않는다.

## 현재 기준 핵심 수치

{md_table(best_by_city, [("city", "지역"), ("candidate", "지역 내 최선 후보"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %"), ("improvement_vs_current_pct", "현행 대비 개선 %")])}

현행 후보의 지역별 기준값은 다음과 같다.

{md_table(current_by_city, [("city", "지역"), ("candidate", "후보"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %")])}
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase76_transport_warehouse_split_summary.csv")
    print(OUTDIR / "phase76_transport_warehouse_split_robust.csv")


if __name__ == "__main__":
    main()
