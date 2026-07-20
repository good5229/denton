from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_partial_statistics_phase41_gva import SECTION_NAMES, parent_for_section, section_for_division


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase42_gva.md"
RUN_ID = "partial_statistics_estimation_phase42_gva"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
DIVISION_NAME_OVERRIDES = {"05": "석탄, 원유 및 천연가스 광업", "06": "금속 광업", "08": "광업 지원 서비스업", "12": "담배 제조업"}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def stamp(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    payload = out.head(20_000).to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash(); out["run_id"] = RUN_ID; out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, frame: pd.DataFrame) -> None:
    stamp(frame).to_csv(DATA / name, index=False, encoding="utf-8-sig")


def hierarchy_prior() -> tuple[pd.DataFrame, pd.DataFrame]:
    registry = pd.read_csv(DATA / "ksic10_official_registry.csv", encoding="cp949", dtype=str)
    universe = registry[["division_code", "group_code"]].drop_duplicates().copy()
    universe["division_code"] = universe.division_code.str.zfill(2); universe["group_code"] = universe.group_code.str.zfill(3)
    universe = universe[~universe.division_code.isin(["97", "98", "99"])].copy()
    universe["section_code"] = universe.division_code.map(section_for_division)
    universe["gva_parent_code"] = universe.section_code.map(parent_for_section)
    raw = pd.read_csv(DATA / "partial_stats_phase42_pohang_2015_all_ksic.csv", encoding="cp949", dtype=str)
    raw["value_num"] = pd.to_numeric(raw.value, errors="coerce")
    pivot = raw.pivot_table(index=["c1_id", "c1_nm"], columns="metric", values="value_num", aggfunc="first").reset_index()
    groups = pivot[pivot.c1_id.str.len().eq(3)].rename(columns={"c1_id": "group_code", "c1_nm": "group_name"})
    divisions = pivot[pivot.c1_id.str.len().eq(2)].rename(columns={"c1_id": "division_code", "c1_nm": "division_name"})
    groups = universe.merge(groups[["group_code", "group_name", "establishments", "employees", "sales"]], on="group_code", how="left")
    groups = groups.merge(divisions[["division_code", "division_name"]], on="division_code", how="left")
    groups["group_name"] = groups.group_name.fillna("분류 " + groups.group_code)
    groups["division_name"] = groups.division_name.fillna(groups.division_code.map(DIVISION_NAME_OVERRIDES)).fillna("산업중분류 " + groups.division_code)
    for col in ("establishments", "employees", "sales"):
        groups[col] = groups[col].fillna(0).clip(lower=0)
    for col in ("establishments", "employees"):
        seed = groups[col] + .01
        groups[f"{col}_within_division"] = seed / seed.groupby(groups.division_code).transform("sum")
    groups["group_share_within_division"] = groups[["establishments_within_division", "employees_within_division"]].mean(axis=1)
    division = groups.groupby(["gva_parent_code", "section_code", "division_code", "division_name"], as_index=False)[["establishments", "employees", "sales"]].sum()
    for col in ("establishments", "employees"):
        seed = division[col] + .01
        division[f"{col}_within_parent"] = seed / seed.groupby(division.gva_parent_code).transform("sum")
    division["division_share_within_parent"] = division[["establishments_within_parent", "employees_within_parent"]].mean(axis=1)
    groups = groups.merge(division[["division_code", "division_share_within_parent"]], on="division_code", how="left")
    groups["group_share_within_parent"] = groups.group_share_within_division * groups.division_share_within_parent
    groups["group_share_within_parent"] /= groups.groupby("gva_parent_code").group_share_within_parent.transform("sum")
    return groups, division


def industry_holdout(groups: pd.DataFrame, divisions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    details = []
    d = divisions[divisions.sales > 0].copy()
    d["actual"] = d.sales / d.groupby("gva_parent_code").sales.transform("sum")
    d["predicted"] = d.division_share_within_parent / d.groupby("gva_parent_code").division_share_within_parent.transform("sum")
    d["uniform"] = 1 / d.groupby("gva_parent_code").division_code.transform("count")
    for r in d.itertuples():
        details.append({"industry_level": "중분류", "parent_code": r.gva_parent_code, "industry_code": r.division_code, "industry_name": r.division_name, "actual_share": r.actual, "predicted_share": r.predicted, "uniform_share": r.uniform})
    g = groups[groups.sales > 0].copy()
    g["actual_within_division"] = g.sales / g.groupby("division_code").sales.transform("sum")
    g["predicted_within_division"] = g.group_share_within_division / g.groupby("division_code").group_share_within_division.transform("sum")
    actual_div = d.set_index("division_code").actual; predicted_div = d.set_index("division_code").predicted
    g = g[g.division_code.isin(actual_div.index)].copy()
    g["actual"] = g.actual_within_division * g.division_code.map(actual_div)
    g["predicted"] = g.predicted_within_division * g.division_code.map(predicted_div)
    g["uniform"] = 1 / g.groupby("gva_parent_code").group_code.transform("count")
    for r in g.itertuples():
        details.append({"industry_level": "소분류", "parent_code": r.gva_parent_code, "industry_code": r.group_code, "industry_name": r.group_name, "actual_share": r.actual, "predicted_share": r.predicted, "uniform_share": r.uniform})
    detail = pd.DataFrame(details)
    detail["abs_error_pp"] = (detail.predicted_share - detail.actual_share).abs() * 100
    detail["uniform_abs_error_pp"] = (detail.uniform_share - detail.actual_share).abs() * 100
    summary = detail.groupby("industry_level").agg(cells=("industry_code", "size"), mae_pp=("abs_error_pp", "mean"), uniform_mae_pp=("uniform_abs_error_pp", "mean")).reset_index()
    summary["validation"] = "2015 포항시 경제총조사 매출비중 홀드아웃; 사업체·종사자만 적합"
    return detail, summary


def spatial_proxy_holdout(divisions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    actual = pd.read_csv(DATA / "partial_stats_phase42_pohang_emd_industry_actual.csv", dtype={"division_code": str, "emd_code": str})
    registry = pd.read_csv(DATA / "partial_stats_phase42_pohang_emd_population.csv", dtype={"emd_code": str})
    actual = actual.merge(registry[["emd_code", "emd_name", "population"]], on="emd_name", how="left", validate="many_to_one")
    if actual.emd_code.isna().any():
        raise RuntimeError(f"unmatched official EMD actual names: {actual.loc[actual.emd_code.isna(), 'emd_name'].unique()}")
    for col in ("establishments", "employees"):
        actual[f"{col}_share"] = (actual[col] + .01) / (actual.groupby("division_code")[col].transform("sum") + .01 * actual.groupby("division_code").emd_code.transform("count"))
    actual["actual_share"] = actual[["establishments_share", "employees_share"]].mean(axis=1)
    actual["population_share"] = actual.population / actual.population.sum()
    proxy = pd.read_csv(DATA / "partial_stats_phase42_pohang_emd_monthly_proxy.csv", dtype={"emd_code": str})
    proxy = proxy[proxy.period.eq("2023-12")].copy()
    proxy["section_code"] = proxy.sector_code.str[0]
    proxy = proxy.groupby(["emd_code", "section_code"], as_index=False).active_license_stock.sum()
    proxy["special_share"] = (proxy.active_license_stock + .01) / proxy.groupby("section_code").active_license_stock.transform(lambda x: x.sum() + .01 * len(x))
    factory = pd.read_csv(DATA / "partial_stats_phase42_pohang_factory_snapshot.csv", dtype={"emd_code": str})
    factory = factory[factory.emd_code.notna()].groupby("emd_code", as_index=False).size().rename(columns={"size": "factory_count"})
    factory["factory_share"] = (factory.factory_count + .01) / (factory.factory_count.sum() + .01 * len(registry))
    out = actual.merge(divisions[["division_code", "section_code", "division_name"]], on="division_code", how="left")
    out = out.merge(proxy[["emd_code", "section_code", "special_share"]], on=["emd_code", "section_code"], how="left")
    out = out.merge(factory[["emd_code", "factory_share"]], on="emd_code", how="left")
    out["special_share"] = np.where(out.section_code.eq("C"), out.factory_share, out.special_share)
    out["proxy_source"] = np.where(out.section_code.eq("C"), "공장주소", np.where(out.section_code.isin(list("GIQRS")), "LOCALDATA 인허가", "인구"))
    out["predicted_share"] = np.where(out.section_code.isin(list("CGIQRS")), .9 * out.special_share.fillna(out.population_share) + .1 * out.population_share, out.population_share)
    out["predicted_share"] /= out.groupby("division_code").predicted_share.transform("sum")
    out["abs_error_pp"] = (out.predicted_share - out.actual_share).abs() * 100
    out["population_abs_error_pp"] = (out.population_share - out.actual_share).abs() * 100
    summary = out.groupby(["section_code", "division_code", "division_name", "proxy_source"]).agg(mae_pp=("abs_error_pp", "mean"), population_mae_pp=("population_abs_error_pp", "mean"), emd_cells=("emd_code", "size")).reset_index()
    summary["improvement_vs_population_pp"] = summary.population_mae_pp - summary.mae_pp
    return out, summary


def monthly_controls() -> pd.DataFrame:
    cube = pd.read_parquet(DATA / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    q = cube[(cube.source_region == "경상북도") & (cube.sigungu_name == "포항시") & cube.year.between(2021, 2023)].copy()
    rows = []
    proxy = pd.read_csv(DATA / "partial_stats_phase42_pohang_emd_monthly_proxy.csv")
    city_proxy = proxy.groupby(["period", "sector_code"], as_index=False).active_license_stock.sum()
    for r in q.itertuples():
        months = list(range((int(r.quarter) - 1) * 3 + 1, int(r.quarter) * 3 + 1))
        periods = [f"{int(r.year)}-{month:02d}" for month in months]
        shape = city_proxy[(city_proxy.period.isin(periods)) & (city_proxy.sector_code == r.sector_code)].set_index("period").active_license_stock.reindex(periods)
        if shape.notna().all() and shape.sum() > 0:
            weights = (shape + .01) / (shape.sum() + .03); source = "포항 월 인허가 영업재고"
        else:
            weights = pd.Series([1 / 3] * 3, index=periods); source = "분기 내 균등"
        for period, month, weight in zip(periods, months, weights):
            rows.append({"year": int(r.year), "quarter": int(r.quarter), "month": month, "period": period, "gva_parent_code": r.sector_code, "estimated_city_parent_monthly_gva": float(r.estimated_quarterly_gva) * float(weight), "temporal_source": source, "quarterly_parent_source": r.benchmark_source})
    return pd.DataFrame(rows)


def current_group_shares(groups: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for year in (2021, 2022, 2023):
        for quarter in (1, 2, 3, 4):
            z = groups.copy(); z["share"] = z.group_share_within_parent; z["share_source"] = "2015 포항 사업체+종사자 계층비중"
            frames.append(z.assign(year=year, quarter=quarter))
    out = pd.concat(frames, ignore_index=True)
    service = pd.read_csv(DATA / "service_detail_quarterly_estimates.csv", encoding="cp949", usecols=["sigungu_name", "parent_sector_code", "detail_code", "detail_level", "year", "quarter", "allocation_share"])
    service = service[(service.sigungu_name == "포항시") & (service.detail_level == "small") & service.year.between(2021, 2023)].copy()
    service["group_code"] = service.detail_code.astype(str).str.extract(r"(\d{3})")[0]
    service = service.dropna(subset=["group_code"]).groupby(["year", "quarter", "parent_sector_code", "group_code"], as_index=False).allocation_share.mean()
    service = service.rename(columns={"parent_sector_code": "gva_parent_code", "allocation_share": "fresh_share"})
    out = out.merge(service, on=["year", "quarter", "gva_parent_code", "group_code"], how="left")
    total = out.groupby(["year", "quarter", "gva_parent_code"]).fresh_share.transform("sum")
    use = total > 0; fresh = out.fresh_share.fillna(0) / total.replace(0, np.nan)
    out.loc[use, "share"] = .95 * fresh[use] + .05 * out.loc[use, "group_share_within_parent"]
    out.loc[use, "share_source"] = "95% 전국 서비스 세부 분기지수+5% 포항 구조"
    out["share"] /= out.groupby(["year", "quarter", "gva_parent_code"]).share.transform("sum")
    return out[["year", "quarter", "gva_parent_code", "section_code", "division_code", "division_name", "group_code", "group_name", "share", "share_source"]]


def spatial_shares(divisions: pd.DataFrame) -> pd.DataFrame:
    actual = pd.read_csv(DATA / "partial_stats_phase42_pohang_emd_industry_actual.csv", dtype={"division_code": str})
    registry = pd.read_csv(DATA / "partial_stats_phase42_pohang_emd_population.csv", dtype={"emd_code": str})
    actual = actual.merge(registry[["emd_code", "emd_name", "general_gu", "population"]], on=["emd_name", "general_gu"], how="left", validate="many_to_one")
    for col in ("establishments", "employees"):
        actual[f"{col}_share"] = (actual[col] + .01 * actual.population / actual.population.sum()) / actual.groupby("division_code")[col].transform(lambda x: x.sum() + .01)
    actual["base_share"] = actual[["establishments_share", "employees_share"]].mean(axis=1)
    actual["base_share"] /= actual.groupby("division_code").base_share.transform("sum")
    grid = divisions[["section_code", "division_code"]].merge(registry, how="cross")
    grid = grid.merge(actual[["division_code", "emd_code", "base_share"]], on=["division_code", "emd_code"], how="left")
    pop_share = grid.population / grid.groupby("division_code").population.transform("sum")
    grid["base_share"] = grid.base_share.fillna(pop_share)
    proxy = pd.read_csv(DATA / "partial_stats_phase42_pohang_emd_monthly_proxy.csv", dtype={"emd_code": str})
    proxy["section_code"] = proxy.sector_code.str[0]
    proxy = proxy.groupby(["period", "emd_code", "section_code"], as_index=False).active_license_stock.sum()
    proxy["dynamic_share"] = (proxy.active_license_stock + .01) / proxy.groupby(["period", "section_code"]).active_license_stock.transform(lambda x: x.sum() + .01 * len(x))
    frames = []
    for period in pd.period_range("2021-01", "2023-12", freq="M").astype(str):
        z = grid.copy().merge(proxy[proxy.period.eq(period)][["emd_code", "section_code", "dynamic_share"]], on=["emd_code", "section_code"], how="left")
        supported = z.section_code.isin(list("GIQRS")) & z.dynamic_share.notna()
        z["spatial_share"] = z.base_share
        z.loc[supported, "spatial_share"] = .75 * z.loc[supported, "base_share"] + .25 * z.loc[supported, "dynamic_share"]
        z["spatial_share"] /= z.groupby("division_code").spatial_share.transform("sum")
        z["spatial_source"] = np.where(supported, "2023 읍면동 산업 actual+월 인허가", "2023 읍면동 산업 actual 정적")
        frames.append(z.assign(period=period))
    return pd.concat(frames, ignore_index=True)


def build_cube(controls: pd.DataFrame, groups: pd.DataFrame, space: pd.DataFrame) -> pd.DataFrame:
    city = controls.merge(groups, on=["year", "quarter", "gva_parent_code"], how="inner")
    city["estimated_city_group_monthly_gva"] = city.estimated_city_parent_monthly_gva * city.share
    out = city.merge(space, on=["period", "section_code", "division_code"], how="inner")
    out["estimated_emd_group_monthly_gva"] = out.estimated_city_group_monthly_gva * out.spatial_share
    return out


def multiresolution(base: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for level, code, name in (("소분류", "group_code", "group_name"), ("중분류", "division_code", "division_name"), ("대분류", "section_code", None)):
        keys = ["year", "quarter", "month", "period", "emd_code", "emd_name", "general_gu", code]
        z = base.groupby(keys, as_index=False).estimated_emd_group_monthly_gva.sum().rename(columns={code: "industry_code", "estimated_emd_group_monthly_gva": "estimated_gva"})
        if level == "대분류": z["industry_name"] = z.industry_code.map(SECTION_NAMES)
        else: z = z.merge(base[[code, name]].drop_duplicates().rename(columns={code: "industry_code", name: "industry_name"}), on="industry_code", how="left")
        z["industry_level"] = level
        for geo in ("읍면동", "구", "시"):
            if geo == "읍면동": g = z.rename(columns={"emd_code": "geo_code", "emd_name": "geo_name"}).copy()
            elif geo == "구":
                g = z.groupby(["year", "quarter", "month", "period", "industry_level", "industry_code", "industry_name", "general_gu"], as_index=False).estimated_gva.sum(); g["geo_code"] = g.general_gu; g["geo_name"] = g.general_gu
            else:
                g = z.groupby(["year", "quarter", "month", "period", "industry_level", "industry_code", "industry_name"], as_index=False).estimated_gva.sum(); g["geo_code"] = "37010"; g["geo_name"] = "포항시"
            g["geo_level"] = geo; g["time_level"] = "월"; frames.append(g)
            q = g.groupby(["year", "quarter", "industry_level", "industry_code", "industry_name", "geo_level", "geo_code", "geo_name"], as_index=False).estimated_gva.sum(); q["month"] = pd.NA; q["period"] = q.year.astype(str) + "Q" + q.quarter.astype(str); q["time_level"] = "분기"; frames.append(q)
            a = g.groupby(["year", "industry_level", "industry_code", "industry_name", "geo_level", "geo_code", "geo_name"], as_index=False).estimated_gva.sum(); a["quarter"] = pd.NA; a["month"] = pd.NA; a["period"] = a.year.astype(str); a["time_level"] = "연"; frames.append(a)
    columns = ["industry_level", "industry_code", "industry_name", "time_level", "year", "quarter", "month", "period", "geo_level", "geo_code", "geo_name", "estimated_gva"]
    return pd.concat(frames, ignore_index=True)[columns]


def gu_temporal_holdout(space: pd.DataFrame, divisions: pd.DataFrame) -> pd.DataFrame:
    predicted = space[space.period.eq("2023-12")].groupby(["division_code", "general_gu"], as_index=False).spatial_share.sum().rename(columns={"spatial_share": "predicted_2024_gu_share"})
    actual = pd.read_csv(DATA / "partial_stats_phase42_pohang_gu_industry_actual.csv", dtype={"division_code": str})
    actual = actual.drop(columns=["section_code", "division_name"], errors="ignore")
    for metric in ("establishments", "employees", "sales"):
        actual[f"{metric}_share"] = actual[metric] / actual.groupby("division_code")[metric].transform("sum")
    out = actual.merge(predicted, on=["division_code", "general_gu"], how="inner").merge(divisions[["division_code", "section_code", "division_name"]], on="division_code", how="left")
    for metric in ("establishments", "employees", "sales"):
        out[f"{metric}_abs_error_pp"] = (out.predicted_2024_gu_share - out[f"{metric}_share"]).abs() * 100
    return out


def accounting(base: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    rows = []
    monthly = base.groupby(["year", "month", "gva_parent_code"]).estimated_emd_group_monthly_gva.sum().sort_index()
    target = controls.set_index(["year", "month", "gva_parent_code"]).estimated_city_parent_monthly_gva.sort_index().reindex(monthly.index)
    err = monthly.to_numpy() - target.to_numpy(); rows.append({"check": "읍면동·소분류→시·GVA상위 / 월", "cells": len(err), "max_abs_error": abs(err).max(), "mean_abs_error": abs(err).mean()})
    quarterly = base.groupby(["year", "quarter", "gva_parent_code"]).estimated_emd_group_monthly_gva.sum().sort_index()
    qtarget = controls.groupby(["year", "quarter", "gva_parent_code"]).estimated_city_parent_monthly_gva.sum().sort_index().reindex(quarterly.index)
    err = quarterly.to_numpy() - qtarget.to_numpy(); rows.append({"check": "월→분기 / GVA상위", "cells": len(err), "max_abs_error": abs(err).max(), "mean_abs_error": abs(err).mean()})
    return pd.DataFrame(rows)


def industry_diagnostics(industry: pd.DataFrame, spatial: pd.DataFrame, gu: pd.DataFrame) -> pd.DataFrame:
    a = industry[industry.industry_level.eq("중분류")].groupby(["industry_code", "industry_name"], as_index=False).abs_error_pp.mean().rename(columns={"abs_error_pp": "city_industry_mae_pp"})
    b = spatial.groupby(["division_code", "division_name"], as_index=False).mae_pp.mean().rename(columns={"division_code": "industry_code", "division_name": "industry_name", "mae_pp": "emd_spatial_mae_pp"})
    c = gu.groupby(["division_code", "division_name"], as_index=False).sales_abs_error_pp.mean().rename(columns={"division_code": "industry_code", "division_name": "industry_name", "sales_abs_error_pp": "next_year_gu_sales_mae_pp"})
    out = a.merge(b, on=["industry_code", "industry_name"], how="outer").merge(c, on=["industry_code", "industry_name"], how="outer")
    out["combined_score_pp"] = out[["city_industry_mae_pp", "emd_spatial_mae_pp", "next_year_gu_sales_mae_pp"]].mean(axis=1)
    out["prediction_group"] = pd.qcut(out.combined_score_pp.rank(method="first"), 3, labels=["예측 양호", "예측 보통", "예측 취약"])
    return out.sort_values("combined_score_pp")


def report(status: dict[str, object], industry_summary: pd.DataFrame, spatial_summary: pd.DataFrame, gu: pd.DataFrame, diagnostics: pd.DataFrame) -> str:
    good = diagnostics[diagnostics.prediction_group.eq("예측 양호")].head(6)
    bad = diagnostics[diagnostics.prediction_group.eq("예측 취약")].sort_values("combined_score_pp", ascending=False).head(6)
    def lines(frame: pd.DataFrame) -> str:
        def value(number: float) -> str:
            return "자료없음" if pd.isna(number) else f"{number:.2f}%p"
        return "\n".join(f"- {r.industry_name}: 종합오차 {r.combined_score_pp:.2f}%p (시 산업 {value(r.city_industry_mae_pp)}, 읍면동 공간 {value(r.emd_spatial_mae_pp)}, 차년도 구 매출 {value(r.next_year_gu_sales_mae_pp)})" for r in frame.itertuples())
    return f"""# 포항시 전 산업 KSIC 중·소분류 시공간 GVA 계층 추정

## 결론

포항시의 2021~2023년 GVA를 **29개 행정 읍면동×{status['divisions']}개 KSIC 중분류×{status['groups']}개 소분류×36개월**로 배분하고 연·분기·월, 시·구·읍면동의 27개 해상도로 재집계했다. 추정치는 공식값이 아니라 상위 실제값에 제약된 개발통계다.

## 독립 검증

- 산업축: 2015 경제총조사 매출을 숨기고 사업체·종사자로 예측한 중분류 MAE **{status['middle_mae_pp']:.2f}%p**, 소분류 **{status['small_mae_pp']:.2f}%p**.
- 공간축: 인구·공장·인허가만으로 2023 읍면동×중분류 사업체·종사자 비중을 예측한 MAE **{status['spatial_mae_pp']:.2f}%p**; 인구 단독 **{status['population_spatial_mae_pp']:.2f}%p**.
- 시점·공간 외삽: 2023 공간구조를 2024 남·북구에 적용해 실제 구별 매출비중과 비교한 MAE **{status['gu_sales_mae_pp']:.2f}%p**.
- 회계축: 하위합을 월·분기·시·산업상위 실제 통제로 되돌린 최대 오차 **{status['accounting_max_abs_error']:.2e}백만원**. 이는 정확도가 아니라 제약식 통과 검사다.

## 예측 양호 산업

{lines(good)}

## 예측 취약 산업

{lines(bad)}

예측 취약은 사업체·고용과 매출·부가가치가 비례하지 않거나, 소수 대형 사업장이 특정 읍면동에 집중된 경우에 주로 발생한다. 산업별 상세 오차는 CSV에 공개한다.

## 사용 데이터와 절차

1. KOSIS 2015 포항시 산업소분류별 사업체·종사자·매출: 산업 계층 홀드아웃.
2. 포항시 2023 사업체조사 읍면동×산업중분류 사업체·종사자: 공간 actual 및 본 추정의 기준 공간구조.
3. 포항시 2024 사업체조사 남·북구×산업중분류 매출: 차년도 공간 외삽 홀드아웃.
4. 포항시 공장등록현황, LOCALDATA 19종 월 인허가, 2026 읍면동 인구: 공간·월 보조지표.
5. 포항시 연간 산업 GVA에 제약된 분기 상위통제와 전국 서비스 세부 생산지수: 총량·세부산업 시간배분.

## 한계

- 2015 산업구조와 2023~2024 사업체조사의 분류·구조 시차가 있다.
- 읍면동 소분류 GVA actual은 없으므로 중분류 공간 검증을 넘는 정확도는 주장하지 않는다.
- 2024 구 매출은 GVA와 개념이 다르며 외삽 강건성의 보조증거다.
- 월 actual이 없어 월 결과는 분기총량에 제약된 실험값이다.
"""


def main() -> dict[str, object]:
    groups, divisions = hierarchy_prior(); industry_detail, industry_summary = industry_holdout(groups, divisions)
    spatial_detail, spatial_summary = spatial_proxy_holdout(divisions)
    controls = monthly_controls(); shares = current_group_shares(groups); space = spatial_shares(divisions)
    base = build_cube(controls, shares, space); multi = multiresolution(base)
    gu = gu_temporal_holdout(space, divisions); checks = accounting(base, controls); diagnostics = industry_diagnostics(industry_detail, spatial_summary, gu)
    mid = industry_summary[industry_summary.industry_level.eq("중분류")].iloc[0]; small = industry_summary[industry_summary.industry_level.eq("소분류")].iloc[0]
    status = {
        "sections": int(base.section_code.nunique()), "divisions": int(base.division_code.nunique()), "groups": int(base.group_code.nunique()), "emd": int(base.emd_code.nunique()), "months": int(base.period.nunique()),
        "base_rows": len(base), "multiresolution_rows": len(multi), "middle_mae_pp": float(mid.mae_pp), "small_mae_pp": float(small.mae_pp),
        "spatial_mae_pp": float(spatial_detail.abs_error_pp.mean()), "population_spatial_mae_pp": float(spatial_detail.population_abs_error_pp.mean()), "gu_sales_mae_pp": float(gu.sales_abs_error_pp.mean()),
        "accounting_max_abs_error": float(checks.max_abs_error.max()), "decision": "constrained experimental statistics; middle-industry spatial evidence available; monthly/small-EMD actual absent",
    }
    write_csv("partial_stats_phase42_pohang_industry_holdout_detail.csv", industry_detail); write_csv("partial_stats_phase42_pohang_industry_holdout_summary.csv", industry_summary)
    write_csv("partial_stats_phase42_pohang_spatial_proxy_holdout_detail.csv", spatial_detail); write_csv("partial_stats_phase42_pohang_spatial_proxy_holdout_summary.csv", spatial_summary)
    write_csv("partial_stats_phase42_pohang_parent_monthly_controls.csv", controls); write_csv("partial_stats_phase42_pohang_gu_2024_holdout.csv", gu)
    write_csv("partial_stats_phase42_pohang_accounting.csv", checks); write_csv("partial_stats_phase42_pohang_industry_diagnostics.csv", diagnostics)
    stamp(base).to_parquet(DATA / "partial_stats_phase42_pohang_emd_group_monthly.parquet", index=False); stamp(multi).to_parquet(DATA / "partial_stats_phase42_pohang_multiresolution_cube.parquet", index=False)
    (DATA / "partial_stats_phase42_pohang_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(report(status, industry_summary, spatial_summary, gu, diagnostics), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2)); return status


if __name__ == "__main__":
    main()
