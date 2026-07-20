from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase41_gva.md"
RUN_ID = "partial_statistics_estimation_phase41_gva"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

SECTION_NAMES = {
    "A": "농업·임업·어업", "B": "광업", "C": "제조업", "D": "전기·가스", "E": "수도·하수·폐기물",
    "F": "건설업", "G": "도매·소매", "H": "운수·창고", "I": "숙박·음식", "J": "정보통신",
    "K": "금융·보험", "L": "부동산", "M": "전문·과학·기술", "N": "사업시설·지원·임대",
    "O": "공공행정", "P": "교육", "Q": "보건·사회복지", "R": "예술·스포츠·여가", "S": "협회·수리·개인서비스",
}

PARENT_DIAGNOSIS = {
    "A00": ("생산액이 사업체·종사자보다 작목·경지·위탁생산 규모에 좌우", "작목별 생산액·재배면적·축산두수·농업서비스 매출"),
    "C00": ("사업체·종사자 프록시가 비교적 안정적이나 업종별 자본집약도 차이 잔존", "공장별 출하액·부가가치·전력사용량·가동률"),
    "D00": ("소수 대형 설비의 발전·공급량이 고용과 비례하지 않음", "사업소별 판매전력·공급량·설비용량"),
    "F00": ("종합건설과 전문공사의 계약금액·원도급 구조가 고용과 불일치", "공사계약액·기성액·착공면적·원하도급 구분"),
    "G00": ("도매·소매의 객단가와 대형점 매출이 사업체 수에 반영되지 않음", "업종별 매출·상권 매출지수·대형점 판매액"),
    "H00": ("화물·여객·창고의 운송량과 시설규모가 종사자 수와 불일치", "화물톤수·여객수·창고면적·택배물동량"),
    "I00": ("객실·좌석 규모와 객단가 차이가 인허가·종사자 수에 미반영", "숙박가동률·객실수·좌석수·관광소비지수"),
    "J00": ("통신·플랫폼·출판의 무형자산 및 전국매출 귀속이 지역고용과 불일치", "사업장별 통신량·소프트웨어 매출·콘텐츠 매출"),
    "K00": ("예금·대출·보험료 등 금융취급액이 지점·종사자 수와 불일치", "지점별 예수금·대출잔액·보험료·수수료"),
    "L00": ("임대·개발 거래액과 중개업 고용 사이의 생산성 격차가 큼", "건축물 연면적·임대료·거래금액·공시가격"),
    "MN0": ("연구개발·전문서비스의 계약규모와 고숙련 생산성 차이", "연구개발비·사업수주액·직종별 임금·근로시간"),
    "O00": ("행정서비스 산출이 기관 수보다 예산·인력배치에 좌우", "기관별 세출·정원·민원처리량"),
    "P00": ("학교급·학원별 학생수와 수강료 차이가 기관·종사자 수에 미반영", "학생·수강생수·수업료·학교급별 교직원"),
    "Q00": ("병원과 복지시설의 병상·환자·급여 규모가 고용과 비례하지 않음", "병상수·환자수·건강보험 급여비·시설정원"),
    "ERS": ("공공서비스·여가·개인서비스가 한 상위묶음에 결합되고 이용량 차이 큼", "시설별 이용객·입장료·폐기물량·개인서비스 매출"),
}


def section_for_division(code: str) -> str:
    n = int(str(code).zfill(2))
    ranges = [(1, 3, "A"), (5, 8, "B"), (10, 34, "C"), (35, 35, "D"), (36, 39, "E"),
              (41, 42, "F"), (45, 47, "G"), (49, 52, "H"), (55, 56, "I"), (58, 63, "J"),
              (64, 66, "K"), (68, 68, "L"), (70, 73, "M"), (74, 76, "N"), (84, 84, "O"),
              (85, 85, "P"), (86, 87, "Q"), (90, 91, "R"), (94, 96, "S")]
    for lo, hi, section in ranges:
        if lo <= n <= hi:
            return section
    raise ValueError(f"unmapped KSIC division {code}")


def parent_for_section(section: str) -> str:
    if section in {"E", "R", "S"}:
        return "ERS"
    if section in {"M", "N"}:
        return "MN0"
    return section + "00"


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def stamp(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    payload = out.head(20_000).to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, frame: pd.DataFrame) -> None:
    stamp(frame).to_csv(DATA / name, index=False, encoding="utf-8-sig")


def write_parquet(name: str, frame: pd.DataFrame) -> None:
    stamp(frame).to_parquet(DATA / name, index=False)


def hierarchy_prior() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    registry = pd.read_csv(DATA / "ksic10_official_registry.csv", encoding="cp949", dtype=str)
    universe = registry[["division_code", "group_code"]].drop_duplicates().copy()
    universe["division_code"] = universe.division_code.str.zfill(2)
    universe["group_code"] = universe.group_code.str.zfill(3)
    # T(97~98), U(99)는 고양시 지역계정 상위 GVA 통제가 없어 별도 비추정 등록 대상이다.
    universe = universe[~universe.division_code.isin(["97", "98", "99"])].copy()
    universe["section_code"] = universe.division_code.map(section_for_division)
    universe["gva_parent_code"] = universe.section_code.map(parent_for_section)

    raw = pd.read_csv(DATA / "partial_stats_phase41_goyang_2015_all_ksic.csv", encoding="cp949", dtype=str)
    raw["value_num"] = pd.to_numeric(raw.value, errors="coerce")
    p = raw.pivot_table(index=["c1_id", "c1_nm"], columns="metric", values="value_num", aggfunc="first").reset_index()
    groups = p[p.c1_id.str.len().eq(3)].rename(columns={"c1_id": "group_code", "c1_nm": "group_name"})
    divisions = p[p.c1_id.str.len().eq(2)].rename(columns={"c1_id": "division_code", "c1_nm": "division_name"})
    sections = p[p.c1_id.str.len().eq(1) & p.c1_id.isin(SECTION_NAMES)].rename(columns={"c1_id": "section_code", "c1_nm": "section_name"})
    u = universe.merge(groups[["group_code", "group_name", "establishments", "employees", "sales"]], on="group_code", how="left")
    u = u.merge(divisions[["division_code", "division_name"]], on="division_code", how="left")
    u["group_name"] = u.group_name.fillna("KSIC9 소분류 " + u.group_code)
    u["division_name"] = u.division_name.fillna("KSIC9 중분류 " + u.division_code)
    for col in ["establishments", "employees", "sales"]:
        u[col] = u[col].fillna(0).clip(lower=0)
    # A tiny uniform prior retains every official code without presenting missing cells as observed zeros.
    for col in ["establishments", "employees"]:
        base = u[col] + .01
        u[f"{col}_within_division"] = base / base.groupby(u.division_code).transform("sum")
    u["group_share_within_division"] = u[["establishments_within_division", "employees_within_division"]].mean(axis=1)
    div = u.groupby(["gva_parent_code", "section_code", "division_code", "division_name"], as_index=False)[["establishments", "employees", "sales"]].sum()
    for col in ["establishments", "employees"]:
        base = div[col] + .01
        div[f"{col}_within_parent"] = base / base.groupby(div.gva_parent_code).transform("sum")
    div["division_share_within_parent"] = div[["establishments_within_parent", "employees_within_parent"]].mean(axis=1)
    u = u.merge(div[["division_code", "division_share_within_parent"]], on="division_code", how="left")
    u["group_share_within_parent"] = u.group_share_within_division * u.division_share_within_parent
    u["group_share_within_parent"] /= u.groupby("gva_parent_code").group_share_within_parent.transform("sum")
    return u, div, sections


def cross_section_holdout(groups: pd.DataFrame, divisions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, detail = [], []
    d = divisions[divisions.sales > 0].copy()
    d["actual_share"] = d.sales / d.groupby("gva_parent_code").sales.transform("sum")
    d["predicted_share"] = d.division_share_within_parent / d.groupby("gva_parent_code").division_share_within_parent.transform("sum")
    d["uniform_share"] = 1 / d.groupby("gva_parent_code").division_code.transform("count")
    for r in d.itertuples():
        detail.append({"industry_level": "middle", "parent_code": r.gva_parent_code, "industry_code": r.division_code,
                       "actual_sales_share": r.actual_share, "predicted_proxy_share": r.predicted_share, "uniform_share": r.uniform_share})
    g = groups[groups.sales > 0].copy()
    g["actual_within_division"] = g.sales / g.groupby("division_code").sales.transform("sum")
    g["predicted_within_division"] = g.group_share_within_division / g.groupby("division_code").group_share_within_division.transform("sum")
    actual_div = d.set_index("division_code").actual_share
    pred_div = d.set_index("division_code").predicted_share
    g = g[g.division_code.isin(actual_div.index)].copy()
    g["actual_share"] = g.actual_within_division * g.division_code.map(actual_div)
    g["predicted_share"] = g.predicted_within_division * g.division_code.map(pred_div)
    g["uniform_share"] = 1 / g.groupby("gva_parent_code").group_code.transform("count")
    for r in g.itertuples():
        detail.append({"industry_level": "small", "parent_code": r.gva_parent_code, "industry_code": r.group_code,
                       "actual_sales_share": r.actual_share, "predicted_proxy_share": r.predicted_share, "uniform_share": r.uniform_share})
    detail_df = pd.DataFrame(detail)
    for level, z in detail_df.groupby("industry_level"):
        cors = z.groupby("parent_code").apply(lambda q: q.predicted_proxy_share.corr(q.actual_sales_share, method="spearman"), include_groups=False)
        rows.append({"industry_level": level, "cells": len(z), "parent_groups": z.parent_code.nunique(),
                     "proxy_mae_pp": float((z.predicted_proxy_share-z.actual_sales_share).abs().mean()*100),
                     "uniform_mae_pp": float((z.uniform_share-z.actual_sales_share).abs().mean()*100),
                     "spearman_median": float(cors.median()), "heldout_actual": "2015 Goyang Economic Census sales share",
                     "inputs": "2015 establishments+employees; sales excluded from fitting"})
    return detail_df, pd.DataFrame(rows)


def industry_error_diagnostics(detail: pd.DataFrame, groups: pd.DataFrame, divisions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Explain where a headcount proxy fails; accounting equality is deliberately not an accuracy metric."""
    name_frames = {
        "middle": divisions[["division_code", "division_name"]].drop_duplicates().rename(columns={"division_code": "industry_code", "division_name": "industry_name"}),
        "small": groups[["group_code", "group_name"]].drop_duplicates().rename(columns={"group_code": "industry_code", "group_name": "industry_name"}),
    }
    summaries, cells = [], []
    for level, z0 in detail.groupby("industry_level"):
        z = z0.copy().merge(name_frames[level], on="industry_code", how="left")
        z["abs_error_pp"] = (z.predicted_proxy_share - z.actual_sales_share).abs() * 100
        z["uniform_abs_error_pp"] = (z.uniform_share - z.actual_sales_share).abs() * 100
        z["signed_error_pp"] = (z.predicted_proxy_share - z.actual_sales_share) * 100
        z["error_rank"] = z.abs_error_pp.rank(method="first", ascending=False).astype(int)
        cells.append(z)
        for parent, q in z.groupby("parent_code"):
            cause, needed = PARENT_DIAGNOSIS.get(parent, ("산업 산출과 사업체·종사자 규모의 관계가 불안정", "지역별 산업매출·생산량·자본투입 자료"))
            worst = q.loc[q.abs_error_pp.idxmax()]
            proxy_mae = q.abs_error_pp.mean(); uniform_mae = q.uniform_abs_error_pp.mean()
            summaries.append({
                "industry_level": level, "parent_code": parent, "cells": len(q),
                "proxy_mae_pp": proxy_mae, "uniform_mae_pp": uniform_mae,
                "improvement_vs_uniform_pp": uniform_mae - proxy_mae,
                "worst_industry_code": worst.industry_code, "worst_industry_name": worst.industry_name,
                "worst_cell_error_pp": worst.abs_error_pp,
                "failure_diagnosis": cause, "additional_data_needed": needed,
                "use_decision": "우선 개선" if proxy_mae >= 10 else ("보조지표 필요" if proxy_mae >= 5 else "제약추정 가능"),
            })
    return pd.DataFrame(summaries), pd.concat(cells, ignore_index=True)


def parent_monthly_controls() -> pd.DataFrame:
    controls = pd.read_parquet(DATA / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    q = controls[(controls.source_region == "경기도") & (controls.sigungu_name == "고양시") & controls.year.between(2021, 2023)].copy()
    expected = pd.MultiIndex.from_product([[2021, 2022, 2023], sorted(q.sector_code.unique()), [1, 2, 3, 4]], names=["year", "sector_code", "quarter"]).to_frame(index=False)
    missing = expected.merge(q[["year", "sector_code", "quarter"]], on=["year", "sector_code", "quarter"], how="left", indicator=True)
    for miss in missing[missing._merge == "left_only"].itertuples():
        adjacent = q[(q.sector_code == miss.sector_code) & (q.quarter == miss.quarter) & q.year.isin([miss.year-1, miss.year+1])]
        template = q[q.sector_code == miss.sector_code].iloc[0].copy()
        template["year"], template["quarter"], template["period"] = miss.year, miss.quarter, f"{miss.year}Q{miss.quarter}"
        template["annual_benchmark_gva"] = q[(q.sector_code == miss.sector_code) & q.year.isin([miss.year-1, miss.year+1])].groupby("year").annual_benchmark_gva.first().mean()
        template["quarter_share"] = adjacent.quarter_share.mean()
        template["estimated_quarterly_gva"] = template.annual_benchmark_gva * template.quarter_share
        template["allocation_basis"] = "linear adjacent-year interpolation for missing parent benchmark"
        q = pd.concat([q, template.to_frame().T], ignore_index=True)
    q["control_status"] = np.where(q.allocation_basis.astype(str).str.contains("interpolation"), "interpolated_missing_parent_year", "observed_annual_parent_constrained_quarter")
    rows = []
    for r in q.itertuples():
        for m in range((r.quarter-1)*3+1, r.quarter*3+1):
            rows.append({"year": r.year, "quarter": r.quarter, "month": m, "period": f"{r.year}-{m:02d}",
                         "gva_parent_code": r.sector_code, "estimated_city_parent_monthly_gva": r.estimated_quarterly_gva/3,
                         "temporal_source": "equal month within constrained quarter", "control_status": r.control_status})
    out = pd.DataFrame(rows)
    # Replace equal shares where a local monthly interaction path already exists, while preserving each quarter.
    p36 = pd.read_csv(DATA / "partial_stats_phase36_gva_goyang_emd_monthly.csv", encoding="cp949")
    shapes = p36.groupby(["year", "month", "quarter", "sector_code"], as_index=False).estimated_monthly_gva.first()
    shapes = shapes.rename(columns={"sector_code": "gva_parent_code", "estimated_monthly_gva": "shape"})
    mfg = pd.read_csv(DATA / "partial_stats_phase39_manufacturing_city_monthly.csv")
    mfg = mfg.rename(columns={"estimated_city_manufacturing_monthly_gva": "shape"})
    mfg["gva_parent_code"] = "C00"
    shapes = pd.concat([shapes[["year", "month", "quarter", "gva_parent_code", "shape"]], mfg[["year", "month", "quarter", "gva_parent_code", "shape"]]], ignore_index=True)
    shapes = shapes.groupby(["year", "month", "quarter", "gva_parent_code"], as_index=False).shape.mean()
    out = out.merge(shapes, on=["year", "month", "quarter", "gva_parent_code"], how="left")
    out["raw"] = out["shape"].fillna(out.estimated_city_parent_monthly_gva)
    qsum = out.groupby(["year", "quarter", "gva_parent_code"]).estimated_city_parent_monthly_gva.transform("sum")
    out["estimated_city_parent_monthly_gva"] = out.raw / out.groupby(["year", "quarter", "gva_parent_code"]).raw.transform("sum") * qsum
    out.loc[out["shape"].notna(), "temporal_source"] = "local monthly proxy path constrained to Phase22 quarter"
    return out.drop(columns=["shape", "raw"])


def current_group_shares(prior: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year in [2021, 2022, 2023]:
        for quarter in [1, 2, 3, 4]:
            z = prior.copy()
            z["share"] = z.group_share_within_parent
            z["share_source"] = "2015 Goyang establishments+employees hierarchy prior"
            rows.append(z.assign(year=year, quarter=quarter))
    out = pd.concat(rows, ignore_index=True)
    # National service detail production-index shares update ten service parents.
    service = pd.read_csv(DATA / "service_detail_quarterly_estimates.csv", encoding="cp949", usecols=["sigungu_name", "parent_sector_code", "detail_code", "detail_level", "year", "quarter", "allocation_share"])
    service = service[(service.sigungu_name == "고양시") & (service.detail_level == "small") & service.year.between(2021, 2023)].copy()
    service["group_code"] = service.detail_code.astype(str).str.extract(r"(\d{3})")[0]
    service = service.dropna(subset=["group_code"])
    service = service.groupby(["year", "quarter", "parent_sector_code", "group_code"], as_index=False).allocation_share.mean()
    service = service.rename(columns={"parent_sector_code": "gva_parent_code", "allocation_share": "fresh_share"})
    out = out.merge(service, on=["year", "quarter", "gva_parent_code", "group_code"], how="left")
    available = out.groupby(["year", "quarter", "gva_parent_code"]).fresh_share.transform("sum")
    use = available > 0
    # 5% local structural prior prevents nationally indexed but locally absent classes from being forced to zero.
    fresh = out.fresh_share.fillna(0)
    fresh = fresh / available.replace(0, np.nan)
    out.loc[use, "share"] = .95*fresh[use] + .05*out.loc[use, "group_share_within_parent"]
    out.loc[use, "share_source"] = "95% national service detail quarterly index + 5% Goyang 2015 hierarchy prior"
    out["share"] /= out.groupby(["year", "quarter", "gva_parent_code"]).share.transform("sum")
    return out[["year", "quarter", "gva_parent_code", "section_code", "division_code", "division_name", "group_code", "group_name", "share", "share_source"]]


def city_group_monthly(controls: pd.DataFrame, shares: pd.DataFrame) -> pd.DataFrame:
    out = controls.merge(shares, on=["year", "quarter", "gva_parent_code"], how="inner")
    out["estimated_city_group_monthly_gva"] = out.estimated_city_parent_monthly_gva * out.share
    return out


def spatial_allocate(city: pd.DataFrame) -> pd.DataFrame:
    emd = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_current.csv", dtype={"emd_code": str})
    pop = emd.copy(); pop["pop_share"] = pop.population_2024 / pop.groupby("general_gu").population_2024.transform("sum")
    gu = pd.read_csv(DATA / "partial_stats_phase37_goyang_gu_industry_annual_actual.csv")
    gu = gu[(gu.general_gu != "합계") & gu.year.between(2021, 2023)].copy()
    gu["share"] = gu.value / gu.groupby(["year", "sector_code", "metric"]).value.transform("sum")
    gu = gu.groupby(["year", "sector_code", "general_gu"], as_index=False).share.mean()
    all_gu = pd.MultiIndex.from_product([[2021, 2022, 2023], list(SECTION_NAMES), sorted(emd.general_gu.unique())], names=["year", "sector_code", "general_gu"]).to_frame(index=False)
    gu = all_gu.merge(gu, on=["year", "sector_code", "general_gu"], how="left")
    fallback = emd.groupby("general_gu", as_index=False).population_2024.sum(); fallback["fallback"] = fallback.population_2024/fallback.population_2024.sum()
    gu = gu.merge(fallback[["general_gu", "fallback"]], on="general_gu", how="left")
    gu["share"] = gu.share.fillna(gu.fallback)
    gu["share"] /= gu.groupby(["year", "sector_code"]).share.transform("sum")

    proxy = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_industry_monthly_proxy.csv", dtype={"emd_code": str})
    proxy_map = {"G": "G00", "I": "I00", "Q": "Q00", "R": "R00", "S": "S00"}
    proxy = proxy[proxy.sector_code.isin(proxy_map.values())].copy()
    reverse = {v:k for k,v in proxy_map.items()}; proxy["sector_code"] = proxy.sector_code.map(reverse)
    proxy = proxy.merge(pop[["emd_code", "pop_share"]], on="emd_code", how="left")
    proxy["seed"] = proxy.active_license_stock.clip(lower=0) + .01*proxy.pop_share
    proxy["emd_share"] = proxy.seed / proxy.groupby(["period", "general_gu", "sector_code"]).seed.transform("sum")

    rows = []
    for r in city.itertuples():
        gshares = gu[(gu.year == r.year) & (gu.sector_code == r.section_code)]
        for gr in gshares.itertuples():
            candidates = proxy[(proxy.period == r.period) & (proxy.general_gu == gr.general_gu) & (proxy.sector_code == r.section_code)]
            source = "current EMD-month LOCALDATA within general-gu"
            if candidates.empty:
                candidates = pop[pop.general_gu == gr.general_gu].copy()
                candidates["emd_share"] = candidates.pop_share
                source = "2024 population static within general-gu"
            for e in candidates.itertuples():
                rows.append({"year": r.year, "quarter": r.quarter, "month": r.month, "period": r.period,
                             "emd_code": e.emd_code, "emd_name": e.emd_name, "general_gu": gr.general_gu,
                             "section_code": r.section_code, "division_code": r.division_code, "division_name": r.division_name,
                             "group_code": r.group_code, "group_name": r.group_name, "gva_parent_code": r.gva_parent_code,
                             "estimated_emd_group_monthly_gva": r.estimated_city_group_monthly_gva*gr.share*e.emd_share,
                             "industry_share_source": r.share_source, "spatial_source": source})
    return pd.DataFrame(rows)


def multiresolution(base: pd.DataFrame) -> pd.DataFrame:
    frames = []
    specs = [
        ("소분류", "group_code", "group_name"),
        ("중분류", "division_code", "division_name"),
        ("대분류", "section_code", None),
    ]
    for level, code, name in specs:
        keys = ["year", "quarter", "month", "period", "emd_code", "emd_name", "general_gu", code]
        z = base.groupby(keys, as_index=False).estimated_emd_group_monthly_gva.sum().rename(columns={code:"industry_code", "estimated_emd_group_monthly_gva":"estimated_gva"})
        z["industry_name"] = z.industry_code.map(SECTION_NAMES) if level == "대분류" else base[[code, name]].drop_duplicates().set_index(code)[name].reindex(z.industry_code).to_numpy()
        z["industry_level"] = level
        for geo_level in ["행정동", "구", "시"]:
            if geo_level == "행정동":
                g = z.rename(columns={"emd_code":"geo_code", "emd_name":"geo_name"}).copy()
            elif geo_level == "구":
                g = z.groupby(["year","quarter","month","period","industry_level","industry_code","industry_name","general_gu"],as_index=False).estimated_gva.sum()
                g["geo_code"],g["geo_name"] = g.general_gu,g.general_gu
            else:
                g = z.groupby(["year","quarter","month","period","industry_level","industry_code","industry_name"],as_index=False).estimated_gva.sum()
                g["geo_code"],g["geo_name"] = "41280","고양시"
            g["geo_level"],g["time_level"] = geo_level,"월"; frames.append(g)
            qkeys=["year","quarter","industry_level","industry_code","industry_name","geo_level","geo_code","geo_name"]
            q=g.groupby(qkeys,as_index=False).estimated_gva.sum();q["month"]=pd.NA;q["period"]=q.year.astype(str)+"Q"+q.quarter.astype(str);q["time_level"]="분기";frames.append(q)
            akeys=["year","industry_level","industry_code","industry_name","geo_level","geo_code","geo_name"]
            a=g.groupby(akeys,as_index=False).estimated_gva.sum();a["quarter"]=pd.NA;a["month"]=pd.NA;a["period"]=a.year.astype(str);a["time_level"]="연";frames.append(a)
    cols=["industry_level","industry_code","industry_name","time_level","year","quarter","month","period","geo_level","geo_code","geo_name","estimated_gva"]
    return pd.concat(frames,ignore_index=True)[cols]


def accounting(base: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    city=base.groupby(["year","month","gva_parent_code"]).estimated_emd_group_monthly_gva.sum().sort_index()
    ctl=controls.set_index(["year","month","gva_parent_code"]).estimated_city_parent_monthly_gva.sort_index().reindex(city.index)
    err=city.to_numpy()-ctl.to_numpy();rows.append({"check":"small→middle→section→GVA parent and EMD→city / month","cells":len(city),"max_abs_error":abs(err).max(),"mean_abs_error":abs(err).mean(),"evidence":"accounting"})
    q=base.groupby(["year","quarter","gva_parent_code"]).estimated_emd_group_monthly_gva.sum().sort_index()
    qc=controls.groupby(["year","quarter","gva_parent_code"]).estimated_city_parent_monthly_gva.sum().sort_index().reindex(q.index)
    err=q.to_numpy()-qc.to_numpy();rows.append({"check":"month→quarter / all 16 GVA parents","cells":len(q),"max_abs_error":abs(err).max(),"mean_abs_error":abs(err).mean(),"evidence":"estimated quarterly parent"})
    return pd.DataFrame(rows)


def common_proxy(base: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for section,z in base.groupby("section_code"):
        p=z.groupby(["group_code","emd_code","period"],as_index=False).estimated_emd_group_monthly_gva.sum().pivot(index=["group_code","emd_code"],columns="period",values="estimated_emd_group_monthly_gva")
        n=p.div(p.sum(axis=1),axis=0).fillna(0).round(12); hashes=n.astype(str).agg("|".join,axis=1)
        rows.append({"section_code":section,"profiles":len(n),"unique_normalized_profiles":hashes.nunique(),"identical_profile_rate":hashes.duplicated(False).mean(),"effective_rank":np.linalg.matrix_rank(n.to_numpy(),tol=1e-10)})
    return pd.DataFrame(rows)


def accuracy_matrix(holdout: pd.DataFrame, divisions: int, groups: int) -> pd.DataFrame:
    mid=holdout[holdout.industry_level=="middle"].iloc[0];small=holdout[holdout.industry_level=="small"].iloc[0]
    rows=[]
    for industry in ["대분류","중분류","소분류"]:
        for time in ["연","분기","월"]:
            for geo in ["시","구","행정동"]:
                grade="D";metric="actual 없음";validation="상위합계 정합성";limit="정확도 수치 제시 금지"
                if time=="연" and geo=="시" and industry=="대분류":grade="A/C";metric="14개 직접·5개 묶음배분";validation="공식 시군구 GVA";limit="E/R/S 및 M/N은 묶음 안 배분"
                elif time=="연" and geo=="시" and industry=="중분류":grade="C";metric=f"2015 매출비중 MAE {mid.proxy_mae_pp:.3f}%p";validation="사업체+종사자→매출 holdout";limit="매출은 GVA actual 아님"
                elif time=="연" and geo=="시" and industry=="소분류":grade="C";metric=f"2015 매출비중 MAE {small.proxy_mae_pp:.3f}%p";validation="계층형 사업체+종사자→매출 holdout";limit="매출은 GVA actual 아님"
                elif time=="연" and geo=="구" and industry=="대분류":grade="C";metric="2022→2023 프록시 MAE 1.170%p";validation="구 사업체·종사자 비중";limit="GVA actual 아님"
                elif time=="연" and geo=="행정동" and industry=="대분류":grade="C";metric="2015 매출공간 중앙 MAE 2.838%p";validation="경제총조사 공간 holdout";limit="과거 경계·동일 조사계열"
                rows.append({"industry_level":industry,"time_level":time,"geo_level":geo,"coverage":f"19 sections / {divisions} divisions / {groups} groups", "validation_grade":grade,"validation":validation,"metric":metric,"critical_limit":limit})
    return pd.DataFrame(rows)


def not_estimable_registry() -> pd.DataFrame:
    """Keep official KSIC sections outside regional-GVA coverage explicit, not silently dropped."""
    return pd.DataFrame([
        {"section_code": "T", "section_name": "가구 내 고용활동 및 자가소비 생산활동",
         "division_codes": "97,98", "status": "not_estimable",
         "reason": "고양시 지역계정의 대응 산업별 GVA 상위통제가 없어 총량 제약 추정 불가"},
        {"section_code": "U", "section_name": "국제 및 외국기관",
         "division_codes": "99", "status": "not_estimable",
         "reason": "고양시 지역계정의 대응 산업별 GVA 상위통제가 없어 총량 제약 추정 불가"},
    ])


def main() -> dict[str,object]:
    prior,divisions,sections=hierarchy_prior()
    holdout_detail,holdout=cross_section_holdout(prior,divisions);diagnostics,cell_errors=industry_error_diagnostics(holdout_detail,prior,divisions)
    controls=parent_monthly_controls();shares=current_group_shares(prior);city=city_group_monthly(controls,shares)
    base=spatial_allocate(city);multi=multiresolution(base);checks=accounting(base,controls);common=common_proxy(base);matrix=accuracy_matrix(holdout, prior.division_code.nunique(), prior.group_code.nunique());not_estimable=not_estimable_registry()
    status={"sections":int(multi[multi.industry_level=="대분류"].industry_code.nunique()),"divisions":int(multi[multi.industry_level=="중분류"].industry_code.nunique()),"groups":int(multi[multi.industry_level=="소분류"].industry_code.nunique()),"emd_count":int(base.emd_code.nunique()),"months":int(base.period.nunique()),"base_rows":len(base),"multiresolution_rows":len(multi),"middle_sales_holdout_mae_pp":float(holdout[holdout.industry_level=="middle"].proxy_mae_pp.iloc[0]),"middle_uniform_mae_pp":float(holdout[holdout.industry_level=="middle"].uniform_mae_pp.iloc[0]),"small_sales_holdout_mae_pp":float(holdout[holdout.industry_level=="small"].proxy_mae_pp.iloc[0]),"small_uniform_mae_pp":float(holdout[holdout.industry_level=="small"].uniform_mae_pp.iloc[0]),"full_replication_sections":int((common.identical_profile_rate==1).sum()),"accounting_max_abs_error":float(checks.max_abs_error.max()),"decision":"all-industry hierarchy complete; annual city middle/small are proxy-validated, finer time/geography remain constrained estimates"}
    write_csv("partial_stats_phase41_all_ksic_prior.csv",prior);write_csv("partial_stats_phase41_all_ksic_holdout_detail.csv",holdout_detail);write_csv("partial_stats_phase41_all_ksic_holdout_summary.csv",holdout);write_csv("partial_stats_phase41_industry_error_diagnostics.csv",diagnostics);write_csv("partial_stats_phase41_industry_cell_errors.csv",cell_errors);write_csv("partial_stats_phase41_parent_monthly_controls.csv",controls);write_csv("partial_stats_phase41_all_ksic_accounting.csv",checks);write_csv("partial_stats_phase41_all_ksic_common_proxy_audit.csv",common);write_csv("partial_stats_phase41_all_ksic_accuracy_matrix.csv",matrix);write_csv("partial_stats_phase41_not_estimable.csv",not_estimable)
    write_parquet("partial_stats_phase41_goyang_emd_group_monthly.parquet",base);write_parquet("partial_stats_phase41_all_ksic_multiresolution_cube.parquet",multi)
    (DATA/"partial_stats_phase41_status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    REPORT.write_text(report(status,holdout,checks,common,matrix,diagnostics),encoding="utf-8")
    print(json.dumps(status,ensure_ascii=False,indent=2));return status


def report(status,h,c,k,m,d):
    mid = d[d.industry_level.eq("middle")].sort_values("proxy_mae_pp", ascending=False).head(5)
    small = d[d.industry_level.eq("small")].sort_values("proxy_mae_pp", ascending=False).head(6)
    def table(z):
        rows = ["| 상위산업 | MAE(%p) | 최악 세부업종 | 원인 | 개선 데이터 |", "| --- | ---: | --- | --- | --- |"]
        for r in z.itertuples():
            rows.append(f"| {r.parent_code} | {r.proxy_mae_pp:.2f} | {r.worst_industry_name} ({r.worst_cell_error_pp:.2f}) | {r.failure_diagnosis} | {r.additional_data_needed} |")
        return "\n".join(rows)
    return f"""# 고양시 전 산업 KSIC 대·중·소분류 시공간 GVA 계층 추정

## 결론

제조업만이 아니라 **KSIC 19개 대분류·{status['divisions']}개 중분류·{status['groups']}개 소분류**를 2021~2023년 고양시·3개 구·44개 행정동 및 연·분기·월 해상도로 물리화했다. 총 {status['multiresolution_rows']:,}행이며, 모든 하위값은 소→중→대→공식 GVA 상위묶음과 행정동→구→시, 월→분기를 보존한다. 지역계정 상위통제가 없는 T·U는 값을 만들지 않고 비추정 범위로 남겼다.

## 실제값 검증

- 2015 경제총조사 고양시×산업소분류 actual 876행(사업체·종사자·매출)을 신규 수집했다.
- 매출을 숨기고 사업체수+종사자수로 중분류 비중을 추정한 MAE: **{status['middle_sales_holdout_mae_pp']:.3f}%p**
- 소분류를 중분류 안에서 추정하고 다시 상위 GVA 묶음으로 재집계한 MAE: **{status['small_sales_holdout_mae_pp']:.3f}%p**
- 단순 균등배분 기준선은 각각 **{status['middle_uniform_mae_pp']:.3f}%p**, **{status['small_uniform_mae_pp']:.3f}%p**로, 계층 프록시가 두 수준 모두 개선했다.
- 매출은 GVA actual이 아니므로 중·소분류 연간 시 결과는 C등급이다. 제조업 중분류의 별도 2023/2024 부가가치 홀드아웃(0.670/0.567%p)은 추가 증거로 유지한다.

## 현재 추정 구조

- 대분류 상위통제: 고양시 공식 연간 GVA에 제약된 16개 GRDP 산업묶음
- 산업배분: 2015 고양시 전 산업 계층구조, 서비스업 분기 생산지수, 제조업 공장·부가가치 검증자료
- 시간배분: 제조업 및 8개 서비스 묶음은 지역 월 프록시, 나머지는 분기 안 균등배분
- B00의 2022년 공식 상위통제 누락은 2021·2023년 인접연도 보간으로만 연결했으며, 12개 월 셀 모두 별도 상태값으로 표시했다.
- 구 배분: 2021~2023 구×KSIC 대분류 사업체·종사자 비중
- 행정동 배분: 지원되는 G·I·Q·R·S는 월 인허가, 나머지는 구 내부 인구 정적 배분

## 회계 검증

최대 절대오차는 **{status['accounting_max_abs_error']:.3e}백만원**이다. 이는 배분값을 다시 더했을 때 투입한 상위 총량으로 돌아오는지 확인한 회계 검사일 뿐이다. 실제값과 일치했다는 의미가 아니며, 오차가 0인 것은 모형 성능이 아니라 제약식의 결과다.

## 어떤 산업이 특히 예측되지 않는가

중분류에서 건설(F00, 31.60%p), 보건·사회복지(Q00, 30.32%p), 운수·창고(H00, 23.98%p)가 가장 취약했다. 소분류에서는 부동산(L00, 53.60%p), 농림어업(A00, 40.06%p), 운수·창고(H00, 13.02%p), 보건·사회복지(Q00, 11.61%p)가 취약했다. 공통 원인은 **사업체·종사자 수가 매출·생산 규모와 비례하지 않는 산업 생산성 이질성**이다.

### 중분류 취약 산업

{table(mid)}

### 소분류 취약 산업

{table(small)}

이 원인 판정은 홀드아웃의 오차 방향과 산업 생산구조를 결합한 진단이며 인과효과 추정은 아니다. 특히 부동산·금융·통신·건설처럼 거래액, 자산, 계약 규모가 핵심인 산업에는 사업체수 프록시를 확대 적용해서는 안 된다.

전체 MAE는 세부 셀을 동일가중한 평균이어서 68개 소분류를 가진 제조업처럼 셀이 많은 산업의 양호한 결과가 부동산·농림어업의 실패를 가릴 수 있다. 실제로 프록시가 균등배분보다 나쁜 묶음은 중분류 F00·H00, 소분류 L00·H00·F00이었다. 또한 하위산업이 하나뿐인 상위묶음의 0%p는 구조적으로 자명한 값이지 예측성능 증거가 아니다. 따라서 전체 평균과 산업묶음별 MAE를 반드시 함께 사용한다.

## 타 지역 확장 및 성능개선 실험

1. 동일한 2015 경제총조사 홀드아웃을 서울·경기 주요 시군구에 반복해 산업별 오차분포와 지역 전이성을 측정한다.
2. 지역을 학습·검증 단위로 분리하는 leave-one-region-out 검증으로 해당 지역 자료를 보지 않은 성능을 제시한다.
3. 산업별로 무료 물량자료를 하나씩 추가하고, 기존 사업체·종사자 기준 대비 홀드아웃 MAE 감소량을 평가한다.
4. 연도별 actual이 확보되는 경우 과거연도 학습→미래연도 검증을 병행해 구조 시차를 측정한다.
5. 상위합계 정합성, actual 예측오차, 공통 프록시 복제를 서로 다른 지표로 계속 공개한다.

## 엄격 판정

- 27개 조합을 모두 생성했으나 분기·월은 actual 부재로 모두 D등급이다.
- 19개 KSIC 대분류 중 14개는 공식 GVA와 일대일이고, E/R/S와 M/N은 각각 ERS·MN0 묶음 안 배분이다.
- 중·소분류 행정동 월 경로는 다수 산업에서 동일 프록시를 상속한다. 공통 프로필 감사 결과를 별도 CSV로 공개하며 고유 동×산업×월 경기변동 주장을 허용하지 않는다.
- 공통 프로필 전면 복제가 확인된 대분류는 **{status['full_replication_sections']}/19개**다. 이 셀들은 ‘세부 경기측정’이 아니라 상위 총량의 제약배분값으로만 사용한다.
- KSIC9 기준 2015 구조를 현재 기간에 사용하는 분류·구조 시차가 있으므로, 최신 사업체 마이크로데이터 확보 전 공식통계로 승격하지 않는다.

## 산출물

- `partial_stats_phase41_all_ksic_multiresolution_cube.parquet`: 27개 해상도 통합 큐브
- `partial_stats_phase41_goyang_emd_group_monthly.parquet`: 44개 행정동×228개 소분류×36개월 기반표
- `partial_stats_phase41_all_ksic_accuracy_matrix.csv`: 조합별 실제값·정합성·등급
- `partial_stats_phase41_all_ksic_holdout_summary.csv`: 전 산업 중·소분류 매출 홀드아웃
- `partial_stats_phase41_industry_error_diagnostics.csv`: 산업별 실패 원인·필요 데이터
- `partial_stats_phase41_industry_cell_errors.csv`: 세부업종별 actual·예측 오차와 순위
- `partial_stats_phase41_all_ksic_accounting.csv`: 산업·시간·공간 재집계 검증
- `partial_stats_phase41_all_ksic_common_proxy_audit.csv`: 공통 변화 복제검사
- `partial_stats_phase41_not_estimable.csv`: T·U 비추정 사유 등록부
"""


if __name__=="__main__":main()
