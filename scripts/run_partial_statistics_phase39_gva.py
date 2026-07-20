from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase39_gva.md"
RUN_ID = "partial_statistics_estimation_phase39_gva"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def audit(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    payload = out.head(20_000).to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, frame: pd.DataFrame) -> None:
    audit(frame).to_csv(DATA / name, index=False, encoding="utf-8-sig")


def denton(indicator: np.ndarray, benchmarks: np.ndarray, frequency: int = 3) -> np.ndarray:
    i, b = np.asarray(indicator, float), np.asarray(benchmarks, float)
    n = len(i)
    m = np.diag(1 / i)
    d = np.zeros((n - 1, n))
    for r in range(n - 1):
        d[r, r], d[r, r + 1] = -1, 1
    h = 2 * m.T @ d.T @ d @ m
    j = np.zeros((len(b), n))
    for k in range(len(b)):
        j[k, k * frequency:(k + 1) * frequency] = 1
    lhs = np.block([[h, j.T], [j, np.zeros((len(b), len(b)))]] )
    answer = np.linalg.lstsq(lhs, np.r_[np.zeros(n), b], rcond=None)[0][:n]
    if np.any(answer <= 0):
        answer = np.concatenate([i[k*frequency:(k+1)*frequency] / i[k*frequency:(k+1)*frequency].sum() * b[k] for k in range(len(b))])
    return answer


def ras(seed: np.ndarray, row_targets: np.ndarray, col_targets: np.ndarray) -> np.ndarray:
    x = np.maximum(np.asarray(seed, float), 1e-12)
    for _ in range(10_000):
        x *= (row_targets / x.sum(axis=1))[:, None]
        x *= (col_targets / x.sum(axis=0))[None, :]
        if max(abs(x.sum(axis=1)-row_targets).max(), abs(x.sum(axis=0)-col_targets).max()) < max(1, col_targets.sum()) * 1e-11:
            return x
    raise RuntimeError("RAS did not converge")


def load_middle_actual() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(DATA / "expanded_manufacturing_sigungu_ksic.csv", encoding="cp949", dtype=str)
    raw = raw[(raw.c1_nm == "고양시") & raw.c2_id.str.startswith("C")].copy()
    raw["year"] = raw.prd_de.astype(int)
    raw["value_num"] = pd.to_numeric(raw.value, errors="coerce")
    p = raw.pivot_table(index=["year", "c2_id", "c2_nm"], columns="metric", values="value_num", aggfunc="sum").reset_index()
    complete = p.groupby("c2_id").agg(years=("year", "nunique"), va=("value_added", "count"), emp=("employees", "count"), est=("establishments", "count"))
    eligible = complete[(complete.years == 5) & (complete.va == 5) & (complete.emp == 5) & (complete.est == 5)].index
    p = p[p.c2_id.isin(eligible)].copy()
    positive = p.groupby("c2_id")[["value_added", "employees", "establishments"]].min().min(axis=1)
    p = p[p.c2_id.isin(positive[positive > 0].index)].copy()
    for metric in ["value_added", "employees", "establishments"]:
        p[f"{metric}_share"] = p[metric] / p.groupby("year")[metric].transform("sum")
    coverage = raw[raw.metric == "value_added"].groupby("year").value_num.sum().rename("all_observed_va").reset_index().merge(
        p.groupby("year").value_added.sum().rename("eligible_va").reset_index(), on="year"
    )
    coverage["eligible_observed_coverage"] = coverage.eligible_va / coverage.all_observed_va
    return p, coverage


def middle_share_holdout(actual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    z = actual.sort_values(["c2_id", "year"]).copy()
    z["proxy_share"] = (z.employees_share + z.establishments_share) / 2
    for col in ["value_added_share", "proxy_share"]:
        z[f"lag_{col}"] = z.groupby("c2_id")[col].shift(1)
    rows = []
    for alpha in np.linspace(0, 1, 11):
        for year, split in [(2022, "development"), (2023, "holdout_1"), (2024, "holdout_2")]:
            x = z[z.year == year].dropna(subset=["lag_value_added_share", "proxy_share"]).copy()
            # same-year proxy is a cross-variable holdout; value-added remains hidden.
            pred = alpha * x.lag_value_added_share + (1-alpha) * x.proxy_share
            pred /= pred.sum()
            rows.append({"alpha_lagged_va": alpha, "year": year, "split": split,
                         "mae_pp": float((pred-x.value_added_share).abs().mean()*100),
                         "spearman": float(pred.corr(x.value_added_share, method="spearman"))})
    grid = pd.DataFrame(rows)
    alpha = float(grid[grid.split == "development"].sort_values(["mae_pp", "alpha_lagged_va"]).iloc[0].alpha_lagged_va)
    results = []
    for year, split in [(2023, "prospective_holdout"), (2024, "second_holdout")]:
        x = z[z.year == year].dropna(subset=["lag_value_added_share", "lag_proxy_share", "proxy_share"]).copy()
        models = {
            "uniform": pd.Series(1/len(x), index=x.index),
            "lagged_value_added": x.lag_value_added_share / x.lag_value_added_share.sum(),
            "lagged_proxy": x.lag_proxy_share / x.lag_proxy_share.sum(),
            "contemporaneous_proxy": x.proxy_share / x.proxy_share.sum(),
            "selected_blend": (alpha*x.lag_value_added_share + (1-alpha)*x.proxy_share),
        }
        for model, pred in models.items():
            pred = pred / pred.sum()
            results.append({"year": year, "split": split, "model": model, "cells": len(x),
                            "mae_pp": float((pred-x.value_added_share).abs().mean()*100),
                            "spearman": float(pred.corr(x.value_added_share, method="spearman"))})
    return pd.DataFrame(results), grid, alpha


def monthly_city_total() -> tuple[pd.DataFrame, pd.DataFrame]:
    controls = pd.read_parquet(DATA / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    q = controls[(controls.source_region == "경기도") & (controls.sigungu_name == "고양시") & (controls.sector_code == "C00") & controls.year.between(2021, 2023)].copy()
    q = q.sort_values(["year", "quarter"])
    prod = pd.read_csv(DATA / "rolling_mining_manufacturing_production_index.csv", encoding="cp949")
    prod = prod[(prod.c1_nm == "경기도") & (prod.c2_nm == "제조업")].copy()
    prod["year"] = prod.prd_de.astype(str).str[:4].astype(int)
    prod["quarter"] = prod.prd_de.astype(str).str[-2:].astype(int)
    prod["production_index"] = pd.to_numeric(prod.value, errors="coerce")
    prod = prod.loc[prod.index.repeat(3)].copy()
    prod["month_in_quarter"] = prod.groupby(["year", "quarter"]).cumcount()+1
    prod["month"] = (prod.quarter-1)*3+prod.month_in_quarter
    elec = pd.read_csv(DATA / "municipality_electricity_features_2021_2023.csv", encoding="cp949")
    e = elec[elec.sigungu_name == "고양시"][["year", "month", "electricity_industrial_kwh"]].rename(
        columns={"electricity_industrial_kwh": "industrial_kwh"}
    )
    m = prod.merge(e, on=["year", "month"], how="inner")
    m = m[m.year.between(2021, 2023)].sort_values(["year", "month"])
    for col in ["production_index", "industrial_kwh"]:
        m[f"{col}_norm"] = m[col] / m.groupby("year")[col].transform("mean")
    m["indicator"] = np.sqrt(m.production_index_norm * m.industrial_kwh_norm)
    fit = denton(m.indicator.to_numpy(), q.estimated_quarterly_gva.to_numpy())
    m["estimated_city_manufacturing_monthly_gva"] = fit
    m["quarter"] = (m.month-1)//3+1
    check = m.groupby(["year", "quarter"], as_index=False).estimated_city_manufacturing_monthly_gva.sum().merge(
        q[["year", "quarter", "estimated_quarterly_gva"]], on=["year", "quarter"]
    )
    check["error"] = check.estimated_city_manufacturing_monthly_gva-check.estimated_quarterly_gva
    return m, check


def middle_monthly(city: pd.DataFrame, actual: pd.DataFrame, alpha: float) -> pd.DataFrame:
    a = actual.sort_values(["c2_id", "year"]).copy()
    a["proxy_share"] = (a.employees_share+a.establishments_share)/2
    a["lag_va"] = a.groupby("c2_id").value_added_share.shift(1)
    a["predicted_share"] = alpha*a.lag_va + (1-alpha)*a.proxy_share
    a["predicted_share"] /= a.groupby("year").predicted_share.transform("sum")
    a = a[a.year.between(2021, 2023)]
    idx = pd.read_csv(DATA / "partial_stats_phase39_manufacturing_middle_production_index.csv", encoding="cp949")
    idx["year"] = idx.prd_de.astype(str).str[:4].astype(int)
    idx["quarter"] = idx.prd_de.astype(str).str[-2:].astype(int)
    idx["index_value"] = pd.to_numeric(idx.value, errors="coerce")
    idx = idx.groupby(["year", "quarter", "c1_nm"], as_index=False).index_value.mean()
    idx = idx.loc[idx.index.repeat(3)].copy()
    idx["month_in_quarter"] = idx.groupby(["year", "quarter", "c1_nm"]).cumcount()+1
    idx["month"] = (idx.quarter-1)*3+idx.month_in_quarter
    wide = idx.pivot_table(index=["year", "month"], columns="c1_nm", values="index_value", aggfunc="first").reset_index()
    rows = []
    for year in [2021, 2022, 2023]:
        ctl = city[city.year == year].sort_values("month")
        sectors = a[a.year == year].sort_values("c2_id")
        profiles = []
        for r in sectors.itertuples():
            source = "반도체 및 부품" if r.c2_id == "C26" and "반도체 및 부품" in wide else "제조업"
            z = wide[wide.year == year].sort_values("month")[source].to_numpy()
            profiles.append(z/z.mean())
        seed = np.asarray(profiles) * ctl.estimated_city_manufacturing_monthly_gva.to_numpy()[None, :]
        row_targets = sectors.predicted_share.to_numpy()*ctl.estimated_city_manufacturing_monthly_gva.sum()
        col_targets = ctl.estimated_city_manufacturing_monthly_gva.to_numpy()
        fitted = ras(seed, row_targets, col_targets)
        for i, r in enumerate(sectors.itertuples()):
            for j, month in enumerate(ctl.month):
                rows.append({"year": year, "month": int(month), "period": f"{year}-{int(month):02d}",
                             "middle_code": r.c2_id, "middle_name": r.c2_nm,
                             "estimated_city_middle_monthly_gva": fitted[i, j],
                             "annual_predicted_middle_share": r.predicted_share,
                             "monthly_profile_source": "national semiconductor/components index" if r.c2_id == "C26" else "Gyeonggi manufacturing index + Goyang industrial electricity"})
    return pd.DataFrame(rows)


def emd_factory_weights(actual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    emd = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_current.csv", dtype={"emd_code": str})
    factory = pd.read_csv(RAW / "public_data_portal" / "factory_full_snapshot_15106170_download.csv", encoding="cp949", dtype=str, low_memory=False)
    factory = factory[(factory["시도명"] == "경기도") & factory["시군구명"].str.contains("고양시", na=False)].copy()
    factory["general_gu"] = factory["시군구명"].str.extract(r"고양시\s*(덕양구|일산동구|일산서구)")[0]
    factory["middle_code"] = "C" + factory["대표업종"].str.extract(r"(\d{2})")[0]
    factory["employee_count"] = pd.to_numeric(factory["종업원합계"], errors="coerce").fillna(0)
    factory["weight"] = 1 + factory.employee_count
    factory["legal_dong"] = factory["공장주소"].str.extract(r"\(([가-힣0-9]+(?:동|읍|면))(?:,|\))")[0]
    missing = factory.legal_dong.isna()
    factory.loc[missing, "legal_dong"] = factory.loc[missing, "공장주소"].str.extract(r"\s([가-힣0-9]+(?:동|읍|면))\s*\d")[0]
    emd["base_dong"] = emd.emd_name.str.replace(r"\d+(?=동$)", "", regex=True)
    eligible = set(actual.c2_id.unique())
    factory = factory[factory.middle_code.isin(eligible) & factory.general_gu.notna()].copy()
    rows = []
    exact_weight = 0.0
    for f in factory.itertuples():
        candidates = emd[(emd.general_gu == f.general_gu) & (emd.base_dong == f.legal_dong)]
        method = "legal_dong_to_current_admin_dong"
        if candidates.empty:
            candidates = emd[emd.general_gu == f.general_gu]
            method = "general_gu_population_fallback"
        shares = candidates.population_2024 / candidates.population_2024.sum()
        if method.startswith("legal"):
            exact_weight += f.weight
        for c, share in zip(candidates.itertuples(), shares):
            rows.append({"emd_code": c.emd_code, "emd_name": c.emd_name, "general_gu": c.general_gu,
                         "middle_code": f.middle_code, "allocated_factory_weight": f.weight*share,
                         "mapping_method": method})
    alloc = pd.DataFrame(rows)
    weights = alloc.groupby(["emd_code", "emd_name", "general_gu", "middle_code"], as_index=False).allocated_factory_weight.sum()
    grid = pd.MultiIndex.from_product([emd.emd_code, sorted(eligible)], names=["emd_code", "middle_code"]).to_frame(index=False)
    grid = grid.merge(emd[["emd_code", "emd_name", "general_gu", "population_2024"]], on="emd_code").merge(weights, on=["emd_code", "emd_name", "general_gu", "middle_code"], how="left")
    grid.allocated_factory_weight = grid.allocated_factory_weight.fillna(0)
    # Positive fallback within each general-gu and middle sector.
    grid["seed"] = grid.allocated_factory_weight + grid.population_2024/grid.groupby(["general_gu", "middle_code"]).population_2024.transform("sum")*.01
    grid["emd_share_within_gu_middle"] = grid.seed/grid.groupby(["general_gu", "middle_code"]).seed.transform("sum")
    audit_map = pd.DataFrame([{"factory_rows": len(factory), "total_factory_weight": factory.weight.sum(),
                              "exact_or_split_dong_weight_share": exact_weight/factory.weight.sum(),
                              "fallback_weight_share": 1-exact_weight/factory.weight.sum()}])
    return grid, audit_map, factory


def gu_holdout(factory: pd.DataFrame) -> pd.DataFrame:
    actual = pd.read_csv(DATA / "partial_stats_phase37_goyang_gu_industry_annual_actual.csv")
    x = actual[(actual.sector_code == "C") & actual.general_gu.ne("합계")].copy()
    x["share"] = x.value/x.groupby(["year", "metric"]).value.transform("sum")
    a = x.groupby(["year", "general_gu"], as_index=False).share.mean()
    f = factory.groupby("general_gu").agg(factory_count=("weight", "size"), factory_weight=("weight", "sum")).reset_index()
    for col in ["factory_count", "factory_weight"]:
        f[f"{col}_share"] = f[col]/f[col].sum()
    pop = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_current.csv").groupby("general_gu", as_index=False).population_2024.sum()
    pop["population_share"] = pop.population_2024/pop.population_2024.sum()
    test = a[a.year == 2023].merge(f, on="general_gu").merge(pop, on="general_gu")
    prev = a[a.year == 2022][["general_gu", "share"]].rename(columns={"share": "previous_share"})
    test = test.merge(prev, on="general_gu")
    rows = []
    for model, pred in {"uniform": np.repeat(1/3, 3), "population": test.population_share,
                        "factory_count_2020": test.factory_count_share, "factory_employee_weight_2020": test.factory_weight_share,
                        "previous_actual_2022": test.previous_share}.items():
        rows.append({"evaluation_year": 2023, "model": model, "mae_pp": float((np.asarray(pred)-test.share).astype(float).abs().mean()*100),
                     "correlation": float(pd.Series(np.asarray(pred)).corr(pd.Series(test.share.to_numpy())))})
    return pd.DataFrame(rows)


def final_emd(city_middle: pd.DataFrame, spatial: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    gu_actual = pd.read_csv(DATA / "partial_stats_phase37_goyang_gu_industry_annual_actual.csv")
    gu_actual = gu_actual[(gu_actual.sector_code == "C") & gu_actual.general_gu.ne("합계")].copy()
    gu_actual["metric_share"] = gu_actual.value/gu_actual.groupby(["year", "metric"]).value.transform("sum")
    gu_share = gu_actual.groupby(["year", "general_gu"], as_index=False).metric_share.mean()
    gu_share["gu_share"] = gu_share.metric_share/gu_share.groupby("year").metric_share.transform("sum")
    rows = []
    gu_middle_rows = []
    for year in [2021, 2022, 2023]:
        sectors = sorted(city_middle[city_middle.year == year].middle_code.unique())
        gus = sorted(gu_share.general_gu.unique())
        annual_middle = city_middle[city_middle.year == year].groupby("middle_code").estimated_city_middle_monthly_gva.sum().reindex(sectors)
        total = annual_middle.sum()
        gu_targets = gu_share[gu_share.year == year].set_index("general_gu").reindex(gus).gu_share*total
        seed = np.zeros((len(gus), len(sectors)))
        for i, gu in enumerate(gus):
            for j, sector in enumerate(sectors):
                seed[i, j] = spatial[(spatial.general_gu == gu) & (spatial.middle_code == sector)].allocated_factory_weight.sum()+1e-6
        fitted = ras(seed, gu_targets.to_numpy(), annual_middle.to_numpy())
        for i, gu in enumerate(gus):
            for j, sector in enumerate(sectors):
                gu_middle_rows.append({"year": year, "general_gu": gu, "middle_code": sector, "estimated_gu_middle_annual_gva": fitted[i, j]})
                monthly = city_middle[(city_middle.year == year) & (city_middle.middle_code == sector)].sort_values("month")
                month_share = monthly.estimated_city_middle_monthly_gva/monthly.estimated_city_middle_monthly_gva.sum()
                emds = spatial[(spatial.general_gu == gu) & (spatial.middle_code == sector)]
                for e in emds.itertuples():
                    for m, ms in zip(monthly.itertuples(), month_share):
                        value = fitted[i, j]*e.emd_share_within_gu_middle*ms
                        rows.append({"year": year, "month": m.month, "period": m.period, "emd_code": e.emd_code,
                                     "emd_name": e.emd_name, "general_gu": gu, "middle_code": sector,
                                     "estimated_emd_middle_monthly_gva": value})
    detail = pd.DataFrame(rows)
    total_emd = detail.groupby(["year", "month", "period", "emd_code", "emd_name", "general_gu"], as_index=False).estimated_emd_middle_monthly_gva.sum().rename(columns={"estimated_emd_middle_monthly_gva": "estimated_emd_manufacturing_monthly_gva"})
    profiles = total_emd.pivot(index="emd_code", columns="period", values="estimated_emd_manufacturing_monthly_gva")
    norm = profiles.div(profiles.sum(axis=1), axis=0)
    hashes = norm.round(12).astype(str).agg("|".join, axis=1)
    common = pd.DataFrame([{"emd_count": len(norm), "effective_rank": int(np.linalg.matrix_rank(norm.to_numpy(), tol=1e-10)),
                            "unique_normalized_profiles": int(hashes.nunique()), "identical_profile_rate": float(hashes.duplicated(False).mean()),
                            "all_profiles_identical": bool(hashes.nunique() == 1),
                            "mean_pairwise_correlation": float(norm.T.corr().where(~np.eye(len(norm), dtype=bool)).stack().mean())}])
    return detail, total_emd, common


def main() -> dict[str, object]:
    actual, coverage = load_middle_actual()
    middle_holdout, alpha_grid, alpha = middle_share_holdout(actual)
    city, quarter_check = monthly_city_total()
    city_middle = middle_monthly(city, actual, alpha)
    spatial, spatial_audit, factory = emd_factory_weights(actual)
    gu_validation = gu_holdout(factory)
    detail, total_emd, common = final_emd(city_middle, spatial)
    accounting = total_emd.groupby(["year", "month"], as_index=False).estimated_emd_manufacturing_monthly_gva.sum().merge(
        city[["year", "month", "estimated_city_manufacturing_monthly_gva"]], on=["year", "month"]
    )
    accounting["error"] = accounting.estimated_emd_manufacturing_monthly_gva-accounting.estimated_city_manufacturing_monthly_gva
    status = {
        "eligible_middle_sectors": int(actual.c2_id.nunique()), "emd_count": int(total_emd.emd_code.nunique()),
        "months": int(total_emd.period.nunique()), "final_total_rows": len(total_emd), "detail_rows": len(detail),
        "selected_alpha_lagged_va": alpha,
        "middle_2023_mae_pp": float(middle_holdout[(middle_holdout.year == 2023) & (middle_holdout.model == "selected_blend")].mae_pp.iloc[0]),
        "middle_2024_mae_pp": float(middle_holdout[(middle_holdout.year == 2024) & (middle_holdout.model == "selected_blend")].mae_pp.iloc[0]),
        "gu_2023_best_model": str(gu_validation.sort_values("mae_pp").iloc[0].model),
        "gu_2023_best_mae_pp": float(gu_validation.mae_pp.min()),
        "exact_dong_mapping_weight_share": float(spatial_audit.exact_or_split_dong_weight_share.iloc[0]),
        "accounting_max_abs_error": float(accounting.error.abs().max()),
        "unique_emd_profiles": int(common.unique_normalized_profiles.iloc[0]),
        "effective_profile_rank": int(common.effective_rank.iloc[0]),
        "all_profiles_identical": bool(common.all_profiles_identical.iloc[0]),
        "decision": "retain manufacturing EMD-month estimate as experimental; validate at observed city-middle-year and gu-sector-year intervals",
    }
    write_csv("partial_stats_phase39_manufacturing_middle_actual.csv", actual)
    write_csv("partial_stats_phase39_manufacturing_coverage.csv", coverage)
    write_csv("partial_stats_phase39_manufacturing_middle_holdout.csv", middle_holdout)
    write_csv("partial_stats_phase39_manufacturing_alpha_grid.csv", alpha_grid)
    write_csv("partial_stats_phase39_manufacturing_city_monthly.csv", city)
    write_csv("partial_stats_phase39_manufacturing_city_middle_monthly.csv", city_middle)
    write_csv("partial_stats_phase39_manufacturing_factory_emd_weights.csv", spatial)
    write_csv("partial_stats_phase39_manufacturing_factory_mapping_audit.csv", spatial_audit)
    write_csv("partial_stats_phase39_manufacturing_gu_holdout.csv", gu_validation)
    write_csv("partial_stats_phase39_manufacturing_emd_middle_monthly.csv", detail)
    write_csv("partial_stats_phase39_manufacturing_emd_monthly.csv", total_emd)
    write_csv("partial_stats_phase39_manufacturing_common_proxy_audit.csv", common)
    write_csv("partial_stats_phase39_manufacturing_accounting.csv", accounting)
    write_csv("partial_stats_phase39_manufacturing_quarter_check.csv", quarter_check)
    (DATA / "partial_stats_phase39_manufacturing_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(
        "# 고양시 제조업 행정동·월 추정 및 실측구간 재집계 검증\n\n"
        "## 결론\n\n"
        f"제조업 직접 행정동·월 GVA가 없어도 하위 값을 추정한 뒤 실측이 존재하는 구간으로 재집계해 검증했다. "
        f"산출물은 {status['emd_count']}개 행정동×{status['months']}개월이며, 내부적으로 {status['eligible_middle_sectors']}개 제조업 중분류를 사용했다.\n\n"
        "## 검증 설계\n\n"
        "- 시간: 고양시 산업용 전력과 경기도 제조업 생산지수로 월 경로를 만들고 공식 분기 제조업 GVA에 Denton 제약.\n"
        "- 산업: 중분류별 부가가치 비중을 추정하고 2023·2024 광업·제조업조사 부가가치 실측으로 외삽 검증.\n"
        "- 공간: 2020 공장등록 주소·업종·종사자 프록시를 44개 행정동에 배분하고 2023 일반구 제조업 사업체·종사자 실측으로 검증.\n"
        "- 엄격 검사: 행정동 제조업 월 프로필의 공통 복제 여부와 동→구→시 합계 보존을 별도 검사.\n\n"
        f"## 핵심 결과\n\n- 중분류 2023 holdout MAE: {status['middle_2023_mae_pp']:.3f}%p\n"
        f"- 중분류 2024 second holdout MAE: {status['middle_2024_mae_pp']:.3f}%p\n"
        f"- 일반구 2023 최우수 모형: {status['gu_2023_best_model']} / MAE {status['gu_2023_best_mae_pp']:.3f}%p\n"
        f"- 주소기반 행정동 직접·분할 매핑 가중비: {status['exact_dong_mapping_weight_share']:.1%}\n"
        f"- 행정동 고유 월 프로필: {status['unique_emd_profiles']}/{status['emd_count']}, 유효 rank {status['effective_profile_rank']}\n"
        f"- 회계 합계 최대오차: {status['accounting_max_abs_error']:.3e}\n\n"
        "## 해석 제한\n\n실측구간 재집계 검증은 중분류와 일반구 수준의 외삽·배분 타당성을 평가한다. 행정동 GVA actual이 생긴 것은 아니며, "
        "행정동 값은 공장주소 기반 공간배분과 산업구성 기반 월 상호작용 추정치다. 같은 통계로 강제한 합계 일치는 정확도 증거와 분리한다.\n",
        encoding="utf-8",
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    main()
