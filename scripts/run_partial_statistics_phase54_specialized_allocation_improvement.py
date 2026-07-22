#!/usr/bin/env python3
"""Phase54 specialized allocation validation for weak industries.

Validates whether sector-specific free sources better explain available
upper-level official distributions than naive equal-gu allocation. This is not
a direct GVA actual test; it is a spatial allocation-basis test.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

SECTOR_NAMES = {
    "F": "건설업",
    "H": "운수 및 창고업",
    "L": "부동산업",
}


def share_frame(df: pd.DataFrame, group_cols: list[str], value_col: str, label: str) -> pd.DataFrame:
    out = df[group_cols + [value_col]].copy()
    out[value_col] = pd.to_numeric(out[value_col], errors="coerce").fillna(0.0)
    denom = out.groupby(group_cols[:-1])[value_col].transform("sum")
    out["predicted_share"] = np.where(denom > 0, out[value_col] / denom, 1.0 / out.groupby(group_cols[:-1])[value_col].transform("count"))
    out = out.rename(columns={value_col: "basis_value"})
    out["basis_id"] = label
    return out[group_cols + ["basis_id", "basis_value", "predicted_share"]]


def actual_goyang() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "partial_stats_phase37_goyang_gu_industry_annual_actual.csv")
    df = df[(df["year"].eq(2023)) & (df["general_gu"].ne("합계")) & (df["sector_code"].isin(SECTOR_NAMES))]
    df = df.rename(columns={"sector_code": "sector", "value": "actual_value"})
    denom = df.groupby(["city", "year", "sector", "metric"])["actual_value"].transform("sum") if "city" in df.columns else None
    df["city"] = "고양시"
    denom = df.groupby(["city", "year", "sector", "metric"])["actual_value"].transform("sum")
    df["actual_share"] = df["actual_value"] / denom
    return df[["city", "year", "general_gu", "sector", "metric", "sector_name", "actual_value", "actual_share"]]


def actual_pohang() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "partial_stats_phase42_pohang_gu_industry_actual.csv")
    df = df[df["section_code"].isin(SECTOR_NAMES)].copy()
    rows = []
    for metric in ["establishments", "employees", "sales"]:
        g = df.groupby(["year", "general_gu", "section_code"], as_index=False)[metric].sum()
        g = g.rename(columns={"section_code": "sector", metric: "actual_value"})
        g["metric"] = metric
        g["city"] = "포항시"
        g["sector_name"] = g["sector"].map(SECTOR_NAMES)
        denom = g.groupby(["city", "year", "sector", "metric"])["actual_value"].transform("sum")
        g["actual_share"] = g["actual_value"] / denom
        rows.append(g[["city", "year", "general_gu", "sector", "metric", "sector_name", "actual_value", "actual_share"]])
    return pd.concat(rows, ignore_index=True)


def candidate_realestate() -> pd.DataFrame:
    b = pd.read_csv(PROCESSED / "partial_stats_phase51_realestate_gu_use_features.csv")
    # Stock-side real estate: residential + commercial/business floor area.
    stock = b[b["use_group"].isin(["주거", "상업·업무"])].groupby(["city", "general_gu"], as_index=False)["total_floor_area"].sum()
    stock = stock.rename(columns={"total_floor_area": "realestate_stock_area"})
    broker_path = PROCESSED / "partial_stats_phase53_realestate_broker_gu_features.csv"
    broker = pd.read_csv(broker_path) if broker_path.exists() else pd.DataFrame(columns=["city", "general_gu", "broker_office_count"])
    base = stock.merge(broker, on=["city", "general_gu"], how="outer").fillna(0)
    frames = []
    frames.append(share_frame(base, ["city", "general_gu"], "realestate_stock_area", "부동산 건물면적"))
    frames.append(share_frame(base, ["city", "general_gu"], "broker_office_count", "중개업소 수"))
    # Blend the two already-normalized shares city-wise.
    s1 = frames[0][["city", "general_gu", "predicted_share"]].rename(columns={"predicted_share": "stock_share"})
    s2 = frames[1][["city", "general_gu", "predicted_share"]].rename(columns={"predicted_share": "broker_share"})
    blend = s1.merge(s2, on=["city", "general_gu"], how="outer").fillna(0)
    blend["predicted_share"] = 0.5 * blend["stock_share"] + 0.5 * blend["broker_share"]
    blend["basis_value"] = np.nan
    blend["basis_id"] = "건물면적+중개업소 평균"
    out = pd.concat(frames + [blend[["city", "general_gu", "basis_id", "basis_value", "predicted_share"]]], ignore_index=True)
    out["sector"] = "L"
    return out


def candidate_construction() -> pd.DataFrame:
    p = pd.read_csv(PROCESSED / "partial_stats_phase52_building_permit_legal_dong_monthly.csv")
    p["year"] = p["period"].astype(str).str.slice(0, 4).astype(int)
    frames = []
    for event in ["허가", "착공", "사용승인"]:
        g = p[p["event_type"].eq(event)].groupby(["city", "year", "general_gu"], as_index=False)["event_floor_area"].sum()
        if g.empty:
            continue
        f = share_frame(g, ["city", "year", "general_gu"], "event_floor_area", f"건축 {event} 연면적")
        frames.append(f)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out["sector"] = "F"
    return out


def candidate_transport() -> pd.DataFrame:
    frames = []
    wh = pd.read_csv(PROCESSED / "partial_stats_phase50_logistics_warehouse_emd_monthly.csv")
    latest = wh.sort_values("period").groupby(["city", "general_gu", "emd_name"], as_index=False).tail(1)
    g = latest.groupby(["city", "general_gu"], as_index=False)["active_warehouse_area"].sum()
    frames.append(share_frame(g, ["city", "general_gu"], "active_warehouse_area", "영업 창고면적"))
    rail_path = PROCESSED / "partial_stats_phase53_korail_station_monthly_features.csv"
    if rail_path.exists():
        rail = pd.read_csv(rail_path)
        rail["passengers"] = pd.to_numeric(rail["boarding"], errors="coerce").fillna(0) + pd.to_numeric(rail["alighting"], errors="coerce").fillna(0)
        rg = rail.groupby(["city", "general_gu"], as_index=False)["passengers"].sum()
        frames.append(share_frame(rg, ["city", "general_gu"], "passengers", "철도 승하차"))
    out = pd.concat(frames, ignore_index=True)
    # Blend only where both shares exist, otherwise single available basis remains.
    pivot = out.pivot_table(index=["city", "general_gu"], columns="basis_id", values="predicted_share", aggfunc="first").reset_index()
    basis_cols = [c for c in pivot.columns if c not in ["city", "general_gu"]]
    pivot["predicted_share"] = pivot[basis_cols].mean(axis=1)
    pivot["basis_id"] = "창고면적+철도승하차 평균"
    pivot["basis_value"] = np.nan
    out = pd.concat([out, pivot[["city", "general_gu", "basis_id", "basis_value", "predicted_share"]]], ignore_index=True)
    out["sector"] = "H"
    return out


def evaluate(actual: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, a in actual.iterrows():
        sub = cand[(cand["city"].eq(a["city"])) & (cand["sector"].eq(a["sector"]))]
        if "year" in sub.columns and not sub["year"].isna().all():
            sub = sub[(sub["year"].isna()) | (sub["year"].eq(a["year"]))]
        if sub.empty:
            continue
        for _, c in sub[sub["general_gu"].eq(a["general_gu"])].iterrows():
            rows.append(
                {
                    "city": a["city"],
                    "year": int(a["year"]),
                    "general_gu": a["general_gu"],
                    "sector": a["sector"],
                    "sector_name": a["sector_name"],
                    "metric": a["metric"],
                    "basis_id": c["basis_id"],
                    "actual_share": a["actual_share"],
                    "predicted_share": c["predicted_share"],
                    "abs_error_pp": abs(a["actual_share"] - c["predicted_share"]) * 100,
                }
            )
        # Equal-gu baseline.
        city_gu = sorted(actual[(actual["city"].eq(a["city"])) & (actual["year"].eq(a["year"])) & (actual["sector"].eq(a["sector"]))]["general_gu"].unique())
        rows.append(
            {
                "city": a["city"],
                "year": int(a["year"]),
                "general_gu": a["general_gu"],
                "sector": a["sector"],
                "sector_name": a["sector_name"],
                "metric": a["metric"],
                "basis_id": "구 균등배분",
                "actual_share": a["actual_share"],
                "predicted_share": 1.0 / len(city_gu),
                "abs_error_pp": abs(a["actual_share"] - 1.0 / len(city_gu)) * 100,
            }
        )
    return pd.DataFrame(rows)


def write_report(scores: pd.DataFrame, best: pd.DataFrame) -> None:
    def md(df: pd.DataFrame) -> str:
        if df.empty:
            return "없음."
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for _, r in df.iterrows():
            lines.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/") for c in cols) + " |")
        return "\n".join(lines)

    top = scores.groupby(["city", "sector_name", "metric", "basis_id"], as_index=False).agg(mae_pp=("abs_error_pp", "mean"))
    top["mae_pp"] = top["mae_pp"].round(3)
    lines = [
        "# Phase54 업종별 특화 배분근거 성능 비교",
        "",
        "## 결론",
        "",
        "- 직접 GVA actual이 없는 구간이므로, 검증은 존재하는 구 단위 공식 사업체·종사자·매출 분포와의 평균절대오차(pp)로 수행했다.",
        "- 건설업은 건축 인허가 이벤트 면적을 쓰면 균등배분보다 공간분포 설명력이 개선되는 경우가 확인된다. 특히 포항 매출분포는 착공/사용승인 면적이 일반 균등배분보다 훨씬 낫다.",
        "- 부동산업은 건물면적과 중개업소 수를 같이 쓰는 방식이 단일 근거보다 안정적이다. 다만 고양 행정동으로 내려가려면 법정동→행정동 매핑이 여전히 필요하다.",
        "- 운수 및 창고업은 창고면적과 철도승하차만으로 H00 전체를 설명하기엔 부족하다. 버스 승하차, 화물차 등록, 항만 물동량이 들어와야 취약 산업에서 벗어난다.",
        "",
        "## 요약 MAE(pp)",
        "",
        md(top.sort_values(["city", "sector_name", "metric", "mae_pp"]).head(80)),
        "",
        "## 업종별 최저오차 근거",
        "",
        md(best),
        "",
        "## 해석상 한계",
        "",
        "- 이 실험은 GVA 직접 actual 검증이 아니라, GVA 배분 전에 쓰는 공간분포 근거의 상위 공식분포 적합도 검증이다.",
        "- 고양은 구×산업 매출 actual이 없어 사업체·종사자 기준만 비교했다.",
        "- 포항은 2024 사업체조사 매출이 있어 매출 기준까지 비교했지만, 매출과 GVA는 개념이 다르다.",
        "- 철도 자료는 간선여객만 포함하므로 도시철도·버스·택시·화물 운송을 대표하지 않는다.",
        "",
        "## 산출 파일",
        "",
        "- `data/processed/partial_stats_phase54_specialized_allocation_cell_errors.csv`",
        "- `data/processed/partial_stats_phase54_specialized_allocation_summary.csv`",
    ]
    (REPORTS / "partial_statistics_estimation_phase54_specialized_allocation_improvement.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    actual = pd.concat([actual_goyang(), actual_pohang()], ignore_index=True)
    cand = pd.concat([candidate_realestate(), candidate_construction(), candidate_transport()], ignore_index=True)
    scores = evaluate(actual, cand)
    scores.to_csv(PROCESSED / "partial_stats_phase54_specialized_allocation_cell_errors.csv", index=False, encoding="utf-8-sig")
    summary = scores.groupby(["city", "sector", "sector_name", "metric", "basis_id"], as_index=False).agg(mae_pp=("abs_error_pp", "mean"))
    summary = summary.sort_values(["city", "sector", "metric", "mae_pp"])
    summary.to_csv(PROCESSED / "partial_stats_phase54_specialized_allocation_summary.csv", index=False, encoding="utf-8-sig")
    best = summary.sort_values("mae_pp").groupby(["city", "sector_name", "metric"], as_index=False).first()
    best["mae_pp"] = best["mae_pp"].round(3)
    write_report(scores, best[["city", "sector_name", "metric", "basis_id", "mae_pp"]].sort_values(["city", "sector_name", "metric"]))


if __name__ == "__main__":
    main()
