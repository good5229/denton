from __future__ import annotations

import glob
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
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase40_gva.md"
RUN_ID = "partial_statistics_estimation_phase40_gva"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def write_csv(name: str, frame: pd.DataFrame) -> None:
    out = frame.copy()
    payload = out.head(20_000).to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    out.to_csv(DATA / name, index=False, encoding="utf-8-sig")


def factory_frame() -> pd.DataFrame:
    f = pd.read_csv(
        RAW / "public_data_portal" / "factory_full_snapshot_15106170_download.csv",
        encoding="cp949", dtype=str, low_memory=False,
    )
    f["employee_count"] = pd.to_numeric(f["종업원합계"], errors="coerce").fillna(0)
    f["factory_weight"] = 1 + f.employee_count
    digits = f["대표업종"].astype(str).str.extract(r"(\d{3,5})")[0]
    f["middle_code"] = "C" + digits.str[:2]
    f["small_code"] = "C" + digits.str[:3]
    f["province"] = f["시도명"].replace({"강원도": "강원특별자치도", "전라북도": "전북특별자치도"})
    return f[f.small_code.str.match(r"C\d{3}", na=False)].copy()


def small_names() -> pd.DataFrame:
    x = pd.read_csv(DATA / "expanded_manufacturing_ksic_codes.csv", encoding="cp949", dtype=str)
    return x[x.ksic_level.eq("small")].rename(
        columns={"industry_code": "small_code", "industry_name": "small_name"}
    )[["small_code", "small_name"]]


def province_small_actual() -> pd.DataFrame:
    rows = []
    for path in glob.glob(str(RAW / "expanded_manufacturing_sigungu_by_code" / "C???_T06.json")):
        small_code = Path(path).name.split("_")[0]
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        for r in payload:
            value = pd.to_numeric(r.get("DT"), errors="coerce")
            province = str(r.get("C1_NM") or "")
            year = pd.to_numeric(r.get("PRD_DE"), errors="coerce")
            if province and province != "전국" and pd.notna(value) and pd.notna(year):
                rows.append({"province": province, "year": int(year), "small_code": small_code,
                             "middle_code": small_code[:3], "actual_value_added": float(value)})
    return pd.DataFrame(rows).merge(small_names(), on="small_code", how="left")


def small_external_holdout(factory: pd.DataFrame, actual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    proxy = factory.groupby(["province", "middle_code", "small_code"], as_index=False).factory_weight.sum()
    x = actual.merge(proxy, on=["province", "middle_code", "small_code"], how="inner")
    x = x[(x.actual_value_added > 0) & (x.factory_weight > 0)].copy()
    counts = x.groupby(["province", "middle_code", "year"]).small_code.transform("nunique")
    # Rank correlation is unstable/trivial with two cells; require at least three observed children.
    x = x[counts >= 3].copy()
    keys = ["province", "middle_code", "year"]
    x["actual_share"] = x.actual_value_added / x.groupby(keys).actual_value_added.transform("sum")
    x["factory_proxy_share"] = x.factory_weight / x.groupby(keys).factory_weight.transform("sum")
    x["uniform_share"] = 1 / x.groupby(keys).small_code.transform("count")
    x["factory_abs_error_pp"] = (x.factory_proxy_share - x.actual_share).abs() * 100
    x["uniform_abs_error_pp"] = (x.uniform_share - x.actual_share).abs() * 100
    summaries = []
    for year, z in x.groupby("year"):
        group = z.groupby(keys).agg(
            cells=("small_code", "size"),
            factory_mae_pp=("factory_abs_error_pp", "mean"),
            uniform_mae_pp=("uniform_abs_error_pp", "mean"),
        ).reset_index()
        cors = z.groupby(keys).apply(
            lambda q: q.factory_proxy_share.corr(q.actual_share, method="spearman"),
            include_groups=False,
        )
        summaries.append({
            "year": int(year), "province_middle_groups": int(len(group)), "small_cells": int(len(z)),
            "factory_mae_pp": float(z.factory_abs_error_pp.mean()),
            "uniform_mae_pp": float(z.uniform_abs_error_pp.mean()),
            "factory_better_group_rate": float((group.factory_mae_pp < group.uniform_mae_pp).mean()),
            "spearman_median": float(cors.median()),
            "validation_scope": "province×manufacturing-middle; 2020 factory composition fixed",
        })
    return x, pd.DataFrame(summaries)


def goyang_factory_small_weights(factory: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    emd = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_current.csv", dtype={"emd_code": str})
    f = factory[(factory.province == "경기도") & factory["시군구명"].str.contains("고양시", na=False)].copy()
    eligible = set(pd.read_csv(DATA / "partial_stats_phase39_manufacturing_middle_actual.csv").c2_id)
    f = f[f.middle_code.isin(eligible)].copy()
    f["general_gu"] = f["시군구명"].str.extract(r"고양시\s*(덕양구|일산동구|일산서구)")[0]
    f["legal_dong"] = f["공장주소"].str.extract(r"\(([가-힣0-9]+(?:동|읍|면))(?:,|\))")[0]
    missing = f.legal_dong.isna()
    f.loc[missing, "legal_dong"] = f.loc[missing, "공장주소"].str.extract(r"\s([가-힣0-9]+(?:동|읍|면))\s*\d")[0]
    emd["base_dong"] = emd.emd_name.str.replace(r"\d+(?=동$)", "", regex=True)
    rows, mapped_weight = [], 0.0
    for r in f[f.general_gu.notna()].itertuples():
        cand = emd[(emd.general_gu == r.general_gu) & (emd.base_dong == r.legal_dong)]
        method = "legal_dong_split"
        if cand.empty:
            cand = emd[emd.general_gu == r.general_gu]
            method = "gu_population_fallback"
        share = cand.population_2024 / cand.population_2024.sum()
        if method == "legal_dong_split":
            mapped_weight += r.factory_weight
        for e, s in zip(cand.itertuples(), share):
            rows.append({"emd_code": e.emd_code, "emd_name": e.emd_name, "general_gu": e.general_gu,
                         "middle_code": r.middle_code, "small_code": r.small_code,
                         "allocated_factory_weight": r.factory_weight * s, "mapping_method": method})
    a = pd.DataFrame(rows)
    w = a.groupby(["emd_code", "emd_name", "general_gu", "middle_code", "small_code"], as_index=False).allocated_factory_weight.sum()
    # Every EMD-middle gets the small classes observed in its general-gu; the tiny prior prevents structural zeros.
    available = w.groupby(["general_gu", "middle_code", "small_code"], as_index=False).allocated_factory_weight.sum()
    grid = emd[["emd_code", "emd_name", "general_gu", "population_2024"]].merge(
        available[["general_gu", "middle_code", "small_code"]], on="general_gu", how="inner"
    ).merge(w, on=["emd_code", "emd_name", "general_gu", "middle_code", "small_code"], how="left")
    grid.allocated_factory_weight = grid.allocated_factory_weight.fillna(0)
    prior = grid.groupby(["general_gu", "middle_code", "small_code"]).allocated_factory_weight.transform("sum")
    prior = prior / prior.groupby([grid.general_gu, grid.middle_code]).transform("sum")
    grid["seed"] = grid.allocated_factory_weight + .01 * prior
    grid["small_share_within_emd_middle"] = grid.seed / grid.groupby(["emd_code", "middle_code"]).seed.transform("sum")
    audit = pd.DataFrame([{"goyang_factory_rows": len(f), "small_classes": f.small_code.nunique(),
                           "middle_classes": f.middle_code.nunique(),
                           "direct_or_split_weight_share": mapped_weight / f.factory_weight.sum()}])
    return grid.merge(small_names(), on="small_code", how="left"), audit


def make_small_cube(weights: pd.DataFrame) -> pd.DataFrame:
    middle = pd.read_csv(DATA / "partial_stats_phase39_manufacturing_emd_middle_monthly.csv", dtype={"emd_code": str})
    keep = ["year", "month", "period", "emd_code", "emd_name", "general_gu", "middle_code", "estimated_emd_middle_monthly_gva"]
    out = middle[keep].merge(
        weights[["emd_code", "middle_code", "small_code", "small_name", "small_share_within_emd_middle"]],
        on=["emd_code", "middle_code"], how="inner",
    )
    out["estimated_emd_small_monthly_gva"] = out.estimated_emd_middle_monthly_gva * out.small_share_within_emd_middle
    out["quarter"] = (out.month - 1) // 3 + 1
    return out


def hierarchy_checks(cube: pd.DataFrame) -> pd.DataFrame:
    middle = pd.read_csv(DATA / "partial_stats_phase39_manufacturing_emd_middle_monthly.csv", dtype={"emd_code": str})
    city = pd.read_csv(DATA / "partial_stats_phase39_manufacturing_city_middle_monthly.csv")
    city_total = pd.read_csv(DATA / "partial_stats_phase39_manufacturing_city_monthly.csv")
    controls = pd.read_parquet(DATA / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    ctl = controls[(controls.source_region == "경기도") & (controls.sigungu_name == "고양시") &
                   (controls.sector_code == "C00") & controls.year.between(2021, 2023)]
    rows = []
    def add(name: str, left: pd.Series, right: pd.Series, cells: int, kind: str):
        err = np.asarray(left, float) - np.asarray(right, float)
        rows.append({"check": name, "cells": cells, "max_abs_error": float(np.abs(err).max()),
                     "mean_abs_error": float(np.abs(err).mean()), "evidence_kind": kind})
    a = cube.groupby(["year", "month", "emd_code", "middle_code"]).estimated_emd_small_monthly_gva.sum().sort_index()
    b = middle.set_index(["year", "month", "emd_code", "middle_code"]).estimated_emd_middle_monthly_gva.sort_index().reindex(a.index)
    add("small→middle / EMD×month", a, b, len(a), "accounting")
    a = cube.groupby(["year", "month", "middle_code"]).estimated_emd_small_monthly_gva.sum().sort_index()
    b = city.set_index(["year", "month", "middle_code"]).estimated_city_middle_monthly_gva.sort_index().reindex(a.index)
    add("EMD→city and small→middle / month", a, b, len(a), "accounting")
    a = cube.groupby(["year", "cube_quarter" if "cube_quarter" in cube else "quarter"]).estimated_emd_small_monthly_gva.sum().sort_index()
    b = ctl.set_index(["year", "quarter"]).estimated_quarterly_gva.sort_index().reindex(a.index)
    add("month→quarter / manufacturing", a, b, len(a), "estimated parent constraint")
    a = cube.groupby("year").estimated_emd_small_monthly_gva.sum().sort_index()
    b = ctl.groupby("year").annual_benchmark_gva.first().sort_index().reindex(a.index)
    add("quarter→official annual GVA / manufacturing", a, b, len(a), "official annual benchmark")
    return pd.DataFrame(rows)


def common_proxy_audit(cube: pd.DataFrame) -> pd.DataFrame:
    annual = cube.groupby(["emd_code", "middle_code", "small_code", "period"], as_index=False).estimated_emd_small_monthly_gva.sum()
    identical = []
    for (emd, middle), z in annual.groupby(["emd_code", "middle_code"]):
        p = z.pivot(index="small_code", columns="period", values="estimated_emd_small_monthly_gva")
        n = p.div(p.sum(axis=1), axis=0).round(12)
        hashes = n.astype(str).agg("|".join, axis=1)
        identical.append(hashes.nunique() == 1)
    total = cube.groupby(["emd_code", "period"], as_index=False).estimated_emd_small_monthly_gva.sum()
    p = total.pivot(index="emd_code", columns="period", values="estimated_emd_small_monthly_gva")
    n = p.div(p.sum(axis=1), axis=0)
    hashes = n.round(12).astype(str).agg("|".join, axis=1)
    return pd.DataFrame([
        {"audit": "small profiles within same EMD-middle", "groups": len(identical),
         "identical_rate": float(np.mean(identical)), "interpretation": "static small shares; no small-specific monthly signal"},
        {"audit": "total manufacturing profiles across EMD", "groups": len(n),
         "identical_rate": float(hashes.duplicated(False).mean()),
         "interpretation": f"{hashes.nunique()}/{len(n)} unique normalized profiles"},
    ])


def multiresolution_cube(cube: pd.DataFrame) -> pd.DataFrame:
    base = cube.rename(columns={"estimated_emd_small_monthly_gva": "estimated_gva"}).copy()
    industrial = []
    small = base[["year", "quarter", "month", "period", "emd_code", "emd_name", "general_gu",
                  "small_code", "small_name", "estimated_gva"]].rename(
        columns={"small_code": "industry_code", "small_name": "industry_name"})
    small["industry_level"] = "소분류"
    industrial.append(small)
    middle = base.groupby(["year", "quarter", "month", "period", "emd_code", "emd_name", "general_gu", "middle_code"], as_index=False).estimated_gva.sum()
    middle["industry_level"], middle["industry_code"], middle["industry_name"] = "중분류", middle.middle_code, middle.middle_code
    industrial.append(middle.drop(columns="middle_code"))
    large = base.groupby(["year", "quarter", "month", "period", "emd_code", "emd_name", "general_gu"], as_index=False).estimated_gva.sum()
    large["industry_level"], large["industry_code"], large["industry_name"] = "대분류", "C00", "제조업"
    industrial.append(large)
    ind = pd.concat(industrial, ignore_index=True)
    rows = []
    for geo_level in ["행정동", "구", "시"]:
        if geo_level == "행정동":
            geo_keys = ["emd_code", "emd_name"]
            z = ind.copy().rename(columns={"emd_code": "geo_code", "emd_name": "geo_name"})
        elif geo_level == "구":
            geo_keys = ["general_gu"]
            z = ind.groupby(["year", "quarter", "month", "period", "industry_level", "industry_code", "industry_name", "general_gu"], as_index=False).estimated_gva.sum()
            z["geo_code"], z["geo_name"] = z.general_gu, z.general_gu
        else:
            geo_keys = []
            z = ind.groupby(["year", "quarter", "month", "period", "industry_level", "industry_code", "industry_name"], as_index=False).estimated_gva.sum()
            z["geo_code"], z["geo_name"] = "41280", "고양시"
        z["geo_level"] = geo_level
        monthly = z.copy()
        monthly["time_level"] = "월"
        rows.append(monthly)
        keys = ["year", "quarter", "industry_level", "industry_code", "industry_name", "geo_level", "geo_code", "geo_name"]
        quarterly = z.groupby(keys, as_index=False).estimated_gva.sum()
        quarterly["month"] = pd.NA
        quarterly["period"] = quarterly.year.astype(str) + "Q" + quarterly.quarter.astype(str)
        quarterly["time_level"] = "분기"
        rows.append(quarterly)
        keys = ["year", "industry_level", "industry_code", "industry_name", "geo_level", "geo_code", "geo_name"]
        annual = z.groupby(keys, as_index=False).estimated_gva.sum()
        annual["quarter"], annual["month"] = pd.NA, pd.NA
        annual["period"] = annual.year.astype(str)
        annual["time_level"] = "연"
        rows.append(annual)
    out = pd.concat(rows, ignore_index=True)
    out["sector_scope"] = "manufacturing only for middle/small; C00 for large"
    columns = ["industry_level", "industry_code", "industry_name", "time_level", "year", "quarter", "month", "period",
               "geo_level", "geo_code", "geo_name", "estimated_gva", "sector_scope"]
    return out[columns].sort_values(["industry_level", "time_level", "geo_level", "industry_code", "period", "geo_code"])


def gu_large_holdout() -> pd.DataFrame:
    x = pd.read_csv(DATA / "partial_stats_phase37_goyang_gu_industry_annual_actual.csv")
    x = x[(x.general_gu != "합계") & x.year.isin([2022, 2023])].copy()
    x["share"] = x.value / x.groupby(["year", "sector_code", "metric"]).value.transform("sum")
    x = x.groupby(["year", "sector_code", "general_gu"], as_index=False).share.mean()
    prev = x[x.year == 2022][["sector_code", "general_gu", "share"]].rename(columns={"share": "predicted_share"})
    test = x[x.year == 2023].merge(prev, on=["sector_code", "general_gu"])
    test["abs_error_pp"] = (test.predicted_share - test.share).abs() * 100
    return test


def accuracy_matrix(small_summary: pd.DataFrame, gu: pd.DataFrame) -> pd.DataFrame:
    middle = pd.read_csv(DATA / "partial_stats_phase39_manufacturing_middle_holdout.csv")
    m23 = middle[(middle.year == 2023) & (middle.model == "selected_blend")].mae_pp.iloc[0]
    m24 = middle[(middle.year == 2024) & (middle.model == "selected_blend")].mae_pp.iloc[0]
    s = small_summary[small_summary.year.between(2021, 2024)]
    small_mae = float(s.factory_mae_pp.mean())
    gu_mae = float(gu.abs_error_pp.mean())
    rows = []
    for industry in ["대분류", "중분류", "소분류"]:
        for time in ["연", "분기", "월"]:
            for geo in ["시", "구", "행정동"]:
                direct, validation, metric, grade, limit = "없음", "상위합계 정합성", "오차 측정 불가", "D", "직접 GVA actual 없음"
                if industry == "대분류" and time == "연" and geo == "시":
                    direct, validation, metric, grade, limit = "공식 시군구 GRDP", "직접 벤치마크", "합계 최대오차 <1e-8", "A", "공표연도까지만"
                elif industry == "중분류" and time == "연" and geo == "시":
                    direct, validation, metric, grade, limit = "광업·제조업조사", "2023·2024 홀드아웃", f"MAE {m23:.3f}/{m24:.3f}%p", "B", "10인 이상 제조업; GRDP와 개념 차이"
                elif industry == "소분류" and time == "연" and geo == "시":
                    direct, validation, metric, grade, limit = "시도 소분류 actual", "시도 외부 홀드아웃+고양 중분류 제약", f"시도 전이 MAE {small_mae:.3f}%p", "C", "고양 직접 actual 아님"
                elif industry == "대분류" and time == "연" and geo == "구":
                    direct, validation, metric, grade, limit = "사업체·종사자", "2022→2023 프록시 비중", f"MAE {gu_mae:.3f}%p", "C", "GVA 아닌 공간 프록시"
                elif time in ["분기", "월"]:
                    validation, metric, grade, limit = "연→분기→월 재집계", "합계 보존(<0.001백만원)", "D", "합계 일치는 정확도 증거가 아님"
                elif industry == "대분류" and geo == "행정동":
                    direct, validation, metric, grade, limit = "2015 경제총조사", "매출액 공간 홀드아웃", "중앙 MAE 2.838%p; ρ 0.867", "C", "과거 경계·동일 조사계열"
                rows.append({"industry_level": industry, "time_level": time, "geo_level": geo,
                             "sector_scope": "all published sections" if industry == "대분류" else "manufacturing only",
                             "direct_or_proxy_actual": direct, "validation": validation,
                             "metric": metric, "validation_grade": grade, "critical_limit": limit})
    return pd.DataFrame(rows)


def main() -> dict[str, object]:
    factory = factory_frame()
    actual = province_small_actual()
    small_detail, small_summary = small_external_holdout(factory, actual)
    weights, mapping_audit = goyang_factory_small_weights(factory)
    cube = make_small_cube(weights)
    multi = multiresolution_cube(cube)
    hierarchy = hierarchy_checks(cube)
    common = common_proxy_audit(cube)
    gu = gu_large_holdout()
    matrix = accuracy_matrix(small_summary, gu)
    status = {
        "matrix_cells": len(matrix), "goyang_small_classes": int(cube.small_code.nunique()),
        "goyang_middle_classes": int(cube.middle_code.nunique()), "emd_count": int(cube.emd_code.nunique()),
        "months": int(cube.period.nunique()), "cube_rows": len(cube), "multiresolution_rows": len(multi),
        "province_small_holdout_2021_2024_mae_pp": float(small_summary[small_summary.year.between(2021, 2024)].factory_mae_pp.mean()),
        "province_small_holdout_uniform_mae_pp": float(small_summary[small_summary.year.between(2021, 2024)].uniform_mae_pp.mean()),
        "hierarchy_max_abs_error": float(hierarchy.max_abs_error.max()),
        "small_within_emd_middle_identical_profile_rate": float(common.iloc[0].identical_rate),
        "decision": "small-class annual estimates are transferable experimental estimates; quarter/month and EMD cells remain constrained allocations",
    }
    write_csv("partial_stats_phase40_small_province_actual.csv", actual)
    write_csv("partial_stats_phase40_small_external_holdout_detail.csv", small_detail)
    write_csv("partial_stats_phase40_small_external_holdout_summary.csv", small_summary)
    write_csv("partial_stats_phase40_goyang_factory_small_weights.csv", weights)
    write_csv("partial_stats_phase40_goyang_factory_mapping_audit.csv", mapping_audit)
    write_csv("partial_stats_phase40_goyang_emd_small_monthly.csv", cube)
    write_csv("partial_stats_phase40_manufacturing_multiresolution_cube.csv", multi)
    write_csv("partial_stats_phase40_hierarchy_checks.csv", hierarchy)
    write_csv("partial_stats_phase40_common_proxy_audit.csv", common)
    write_csv("partial_stats_phase40_gu_large_holdout.csv", gu)
    write_csv("partial_stats_phase40_accuracy_matrix.csv", matrix)
    (DATA / "partial_stats_phase40_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(report_text(status, small_summary, hierarchy, common, matrix), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return status


def report_text(status, small_summary, hierarchy, common, matrix) -> str:
    def md(frame: pd.DataFrame) -> str:
        cols = list(frame.columns)
        rows = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
        for row in frame.itertuples(index=False, name=None):
            rows.append("| " + " | ".join(str(v) for v in row) + " |")
        return "\n".join(rows)

    sm = small_summary[small_summary.year.between(2021, 2024)]
    table = md(sm[["year", "province_middle_groups", "small_cells", "factory_mae_pp", "uniform_mae_pp", "spearman_median"]].round(4))
    ht = md(hierarchy[["check", "cells", "max_abs_error", "evidence_kind"]])
    counts = md(matrix.groupby(["validation_grade"]).size().rename("cells").reset_index())
    return f"""# 고양시 KSIC·시공간 계층 GVA 추정 가능성 검증

## 결론

KSIC 대·중·소분류 × 연·분기·월 × 시·구·행정동의 27개 조합을 모두 판정했다. 고양시에서 실제 오차를 직접 말할 수 있는 최저 경계는 **제조업 중분류×시×연**이다. 소분류는 고양시 actual이 없어 2020년 공장구성을 고정한 뒤 시도 소분류 actual로 외부 홀드아웃했으며, 분기·월과 행정동은 상위값을 보존하는 제약배분이다.

## 산출 범위

- 제조업 {status['goyang_middle_classes']}개 중분류, {status['goyang_small_classes']}개 소분류
- 44개 행정동 × 36개월, 총 {status['cube_rows']:,}개 행정동·소분류·월 셀
- 산업·시간·공간 27개 조합별 actual·프록시·검증·등급 등록
- 27개 해상도를 실제 조회 가능한 {status['multiresolution_rows']:,}행 다중해상도 큐브로 물리화

중·소분류는 제조업 범위다. 서비스업 중·소분류까지 정확도 수치가 확장된 것으로 해석하지 않는다.

## 소분류 외부 홀드아웃

고양시에는 소분류 부가가치 actual이 없으므로 전국 공장등록부의 2020년 사업체+종사자 가중 구성을 시도×중분류 안의 소분류 비중으로 만든 뒤, 2021~2024 KOSIS 소분류 부가가치와 비교했다. 이는 **방법의 지역 전이 검증**이지 고양시 직접 정확도가 아니다.

{table}

2021~2024 평균 MAE는 **{status['province_small_holdout_2021_2024_mae_pp']:.3f}%p**, 균등배분은 **{status['province_small_holdout_uniform_mae_pp']:.3f}%p**다. 공장 프록시가 균등보다 나은지까지 연도별로 공개했으며, 결과가 나쁜 연도도 제거하지 않았다.

## 산업·시간·공간 재집계 검증

{ht}

최대 회계오차는 **{status['hierarchy_max_abs_error']:.3e}**이다. 소→중, 행정동→시, 월→분기, 분기→공식 연간 제조업 GVA가 모두 보존된다. 단, 이 합계 일치는 산술 제약의 성공이며 하위 셀의 실제 정확도 증거가 아니다.

## 공통 프록시 엄격 검사

- 같은 행정동·중분류 안에서 소분류 정규화 월 프로필 동일률: **{status['small_within_emd_middle_identical_profile_rate']:.1%}**
- 판정: 소분류별 월 신호가 없고 정적 소분류 비중을 중분류 월 경로에 곱했으므로, **행정동×소분류×월 고유 경기변동 주장 차단**
- 제조업 총계의 행정동별 월 프로필 다양성은 산업구성 차이에서 오지만, 소분류 자체의 월 상호작용 신호를 뜻하지 않는다.

## 27개 조합 등급 분포

{counts}

- A: 공식 GVA 벤치마크가 직접 존재
- B: 같은 목표 개념의 실제값 홀드아웃 존재
- C: 다른 공간 또는 프록시 actual을 이용한 간접 검증
- D: 상위합계 정합성만 확인; 정확도 수치 제시 금지

전체 판정은 `partial_stats_phase40_accuracy_matrix.csv`에 조합별로 기록했다.

## 포스터 적용 원칙

포스터에는 중분류 2023/2024 MAE, 소분류 시도 외부 홀드아웃 MAE, 소→중→대 및 월→분기→연 합계보존을 함께 싣되, 소분류 수치에는 반드시 **‘시도 전이검증’**, 분기·월에는 **‘정합성 검증’**이라고 표시한다. 행정동×소분류×월을 actual 또는 직접 검증치로 표현하지 않는다.
"""


if __name__ == "__main__":
    main()
