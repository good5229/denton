from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase47_agriculture_specialized.md"

SIDO_PREFIX = {
    "11": "서울특별시", "21": "부산광역시", "22": "대구광역시", "23": "인천광역시",
    "24": "광주광역시", "25": "대전광역시", "26": "울산광역시", "29": "세종특별자치시",
    "31": "경기도", "32": "강원특별자치도", "33": "충청북도", "34": "충청남도",
    "35": "전북특별자치도", "36": "전라남도", "37": "경상북도", "38": "경상남도",
    "39": "제주특별자치도",
}
SIDO_ALIASES = {
    "서울시": "서울특별시", "부산시": "부산광역시", "대구시": "대구광역시", "인천시": "인천광역시",
    "광주시": "광주광역시", "대전시": "대전광역시", "울산시": "울산광역시", "세종시": "세종특별자치시",
    "강원도": "강원특별자치도", "전라북도": "전북특별자치도",
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시",
    "광주": "광주광역시", "대전": "대전광역시", "울산": "울산광역시", "세종": "세종특별자치시",
    "경기": "경기도", "강원": "강원특별자치도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전북특별자치도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}
CITY_EXCLUDE = {"전국", "전  국"}


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, **kwargs)


def normalize_sido(name: str) -> str:
    text = str(name).strip().replace(" ", "")
    return SIDO_ALIASES.get(text, text)


def load_actual_a00() -> pd.DataFrame:
    raw = read_csv(DATA / "expanded_sigungu_grva_real.csv", dtype=str)
    raw["value_num"] = pd.to_numeric(raw.value, errors="coerce")
    mask = raw.c2_nm.astype(str).str.replace(" ", "", regex=False).str.contains("농업임업및어업", na=False)
    out = raw[mask].copy()
    out["year"] = pd.to_numeric(out.prd_de, errors="coerce").astype("Int64")
    out["source_region"] = out.source_region.map(normalize_sido)
    out["area_name"] = out.c1_nm.astype(str).str.strip()
    out["area_name_norm"] = out.area_name.map(normalize_sido)
    out["is_sido_total"] = out.area_name_norm.eq(out.source_region)
    out = out[out.year.between(2019, 2023)].copy()
    return out[["year", "source_region", "area_name", "area_name_norm", "is_sido_total", "value_num"]]


def load_emd_a00_proxy() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = read_csv(DATA / "emd_economic_census_2015.csv", dtype=str)
    a = raw[raw.c1_id.eq("A")].copy()
    a["value_num"] = pd.to_numeric(a.value, errors="coerce").fillna(0).clip(lower=0)
    a["area_code"] = a.c2_id.astype(str).str.zfill(2)
    a["area_name"] = a.c2_nm.astype(str).str.strip()
    a = a[~a.area_name.isin(CITY_EXCLUDE)].copy()
    a["prefix"] = a.area_code.str[:2]
    a["source_region"] = a.prefix.map(SIDO_PREFIX)
    a = a.dropna(subset=["source_region"])
    sigungu = a[a.area_code.str.len().eq(5)].copy()
    sigungu_pivot = (
        sigungu.pivot_table(index=["source_region", "area_name"], columns="metric", values="value_num", aggfunc="sum")
        .reset_index()
        .fillna(0)
    )
    for col in ("establishments", "employees", "sales"):
        if col not in sigungu_pivot:
            sigungu_pivot[col] = 0.0
    sido_pivot = (
        sigungu_pivot.groupby("source_region", as_index=False)[["establishments", "employees", "sales"]].sum()
    )
    return sigungu_pivot, sido_pivot


def load_sido_business_proxy() -> pd.DataFrame:
    raw = read_csv(DATA / "municipality_feature_mart_long.csv", dtype=str)
    z = raw[
        raw.source_dataset.eq("sido_industry_business")
        & raw.area_level.eq("sido")
        & raw.industry_code.eq("A")
        & raw.metric.isin(["establishments", "employees"])
    ].copy()
    z["source_region"] = z.area_name.map(normalize_sido)
    z["year"] = pd.to_numeric(z.year, errors="coerce").astype("Int64")
    z["value_num"] = pd.to_numeric(z.value, errors="coerce").fillna(0).clip(lower=0)
    return z.pivot_table(index=["source_region", "year"], columns="metric", values="value_num", aggfunc="sum").reset_index().fillna(0)


def share(frame: pd.DataFrame, group_cols: list[str], value_col: str, out_col: str) -> pd.Series:
    seed = frame[value_col].astype(float).clip(lower=0).fillna(0) + 1e-9
    denom = seed.groupby([frame[col] for col in group_cols]).transform("sum")
    return seed / denom


def proxy_scores(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["general_seed"] = 0.5 * out.establishments.fillna(0) + 0.5 * out.employees.fillna(0)
    out["specialized_seed"] = out.sales.fillna(0)
    missing = out.specialized_seed <= 0
    out.loc[missing, "specialized_seed"] = out.loc[missing, "general_seed"]
    return out


def evaluate_sido(actual: pd.DataFrame, sido_2015: pd.DataFrame, sido_business: pd.DataFrame) -> pd.DataFrame:
    actual_sido = actual[actual.is_sido_total].copy()
    actual_sido["actual_share"] = share(actual_sido, ["year"], "value_num", "actual_share")
    latest_business = []
    for year in sorted(actual_sido.year.dropna().unique()):
        eligible = sido_business[sido_business.year <= year - 2].copy()
        if eligible.empty:
            continue
        e = eligible.sort_values("year").groupby("source_region", as_index=False).tail(1)
        e["target_year"] = int(year)
        latest_business.append(e)
    b = pd.concat(latest_business, ignore_index=True)
    b["general_seed"] = 0.5 * b.establishments.fillna(0) + 0.5 * b.employees.fillna(0)
    b["general_share"] = share(b, ["target_year"], "general_seed", "general_share")
    s = proxy_scores(sido_2015.rename(columns={"source_region": "source_region"}))
    s = s[["source_region", "general_seed", "specialized_seed"]].copy()
    rows = []
    for year in sorted(actual_sido.year.dropna().unique()):
        z = actual_sido[actual_sido.year.eq(year)][["year", "source_region", "value_num", "actual_share"]].copy()
        zz = z.merge(b[b.target_year.eq(year)][["source_region", "general_share"]], on="source_region", how="left")
        ss = s.copy()
        ss["target_year"] = int(year)
        ss["general_2015_share"] = share(ss, ["target_year"], "general_seed", "general_2015_share")
        ss["specialized_share"] = share(ss, ["target_year"], "specialized_seed", "specialized_share")
        zz = zz.merge(ss[["source_region", "general_2015_share", "specialized_share"]], on="source_region", how="left")
        zz["general_share"] = zz.general_share.fillna(zz.general_2015_share)
        zz = zz.drop(columns=["general_2015_share"])
        rows.append(zz)
    out = pd.concat(rows, ignore_index=True)
    for model in ("general", "specialized"):
        out[f"{model}_abs_error_pp"] = (out[f"{model}_share"] - out.actual_share).abs() * 100
    out = add_lag_and_hybrid(out, ["year"], ["source_region"])
    return out


def evaluate_sigungu(actual: pd.DataFrame, sigungu_2015: pd.DataFrame) -> pd.DataFrame:
    city = actual[~actual.is_sido_total].copy()
    city["actual_share"] = share(city, ["year", "source_region"], "value_num", "actual_share")
    proxy = proxy_scores(sigungu_2015)
    proxy["general_share"] = share(proxy, ["source_region"], "general_seed", "general_share")
    proxy["specialized_share"] = share(proxy, ["source_region"], "specialized_seed", "specialized_share")
    out = city.merge(
        proxy[["source_region", "area_name", "general_share", "specialized_share", "establishments", "employees", "sales"]],
        left_on=["source_region", "area_name"],
        right_on=["source_region", "area_name"],
        how="inner",
    )
    for model in ("general", "specialized"):
        out[f"{model}_abs_error_pp"] = (out[f"{model}_share"] - out.actual_share).abs() * 100
    out = add_lag_and_hybrid(out, ["year", "source_region"], ["source_region", "area_name"])
    return out


def add_lag_and_hybrid(frame: pd.DataFrame, group_cols: list[str], entity_cols: list[str]) -> pd.DataFrame:
    out = frame.copy().sort_values(entity_cols + ["year"])
    out["lag_share"] = out.groupby(entity_cols).actual_share.shift(1)
    out = out.dropna(subset=["lag_share"]).copy()
    # A00 is structurally persistent; keep the observed lag as the anchor and use 2015 sales as a light stabilizer.
    out["hybrid_share_raw"] = 0.85 * out.lag_share + 0.15 * out.specialized_share
    norm_groups = [out[col] for col in group_cols]
    out["hybrid_share"] = out.hybrid_share_raw / out.hybrid_share_raw.groupby(norm_groups).transform("sum")
    out["lag_abs_error_pp"] = (out.lag_share - out.actual_share).abs() * 100
    out["hybrid_abs_error_pp"] = (out.hybrid_share - out.actual_share).abs() * 100
    return out


def summarize(frame: pd.DataFrame, level: str) -> pd.DataFrame:
    rows = []
    for year, z in frame.groupby("year"):
        rows.append(summary_row(level, int(year), z))
    z = frame.copy()
    rows.append(summary_row(level, 0, z))
    return pd.DataFrame(rows)


def summary_row(level: str, year: int, z: pd.DataFrame) -> dict[str, float | int | str]:
    general = z.general_abs_error_pp.mean()
    candidate_mae = {
        "2015_sales": z.specialized_abs_error_pp.mean(),
        "lag_share": z.lag_abs_error_pp.mean(),
        "hybrid_85_15": z.hybrid_abs_error_pp.mean(),
    }
    best_model, best = min(candidate_mae.items(), key=lambda item: item[1])
    return {
        "level": level,
        "year": year,
        "n": len(z),
        "general_mae_pp": general,
        "census_sales_mae_pp": candidate_mae["2015_sales"],
        "lag_mae_pp": candidate_mae["lag_share"],
        "hybrid_mae_pp": candidate_mae["hybrid_85_15"],
        "best_specialized_model": best_model,
        "best_specialized_mae_pp": best,
        "improvement_pp": general - best,
        "improvement_pct": (general - best) / general * 100 if general else np.nan,
    }


def sample_cities(sigungu_eval: pd.DataFrame) -> pd.DataFrame:
    latest = sigungu_eval[sigungu_eval.year.eq(sigungu_eval.year.max())].copy()
    must = latest[latest.area_name.isin(["고양시", "포항시"])].copy()
    pool = latest[~latest.index.isin(must.index)].sample(n=10, random_state=47)
    out = pd.concat([must, pool], ignore_index=True)
    out["sample_group"] = np.where(out.area_name.isin(["고양시", "포항시"]), "focus", "random_10")
    return out.sort_values(["sample_group", "source_region", "area_name"])


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    labels = {
        "year": "year", "source_region": "시도", "area_name": "시군구", "actual_share": "actual",
        "level": "수준", "n": "n",
        "general_share": "일반", "specialized_share": "2015매출",
        "lag_share": "직전share", "hybrid_share": "혼합share",
        "general_abs_error_pp": "일반오차", "specialized_abs_error_pp": "매출오차",
        "lag_abs_error_pp": "직전오차", "hybrid_abs_error_pp": "혼합오차",
        "general_mae_pp": "일반MAE", "census_sales_mae_pp": "2015매출MAE",
        "lag_mae_pp": "직전MAE", "hybrid_mae_pp": "혼합MAE",
        "best_specialized_model": "최선후보", "best_specialized_mae_pp": "최선MAE",
        "improvement_pct": "개선율",
        "sample_group": "구분",
    }
    rows = []
    for row in frame[columns].itertuples(index=False):
        values = []
        for col, value in zip(columns, row):
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        rows.append(values)
    header = [labels.get(col, col) for col in columns]
    numeric_cols = {
        "actual_share", "general_share", "specialized_share", "lag_share", "hybrid_share",
        "general_abs_error_pp", "specialized_abs_error_pp", "lag_abs_error_pp", "hybrid_abs_error_pp",
        "general_mae_pp", "census_sales_mae_pp", "lag_mae_pp", "hybrid_mae_pp",
        "best_specialized_mae_pp", "improvement_pct", "n",
    }
    sep = ["---:" if col in numeric_cols else "---" for col in columns]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> dict[str, float]:
    actual = load_actual_a00()
    sigungu_2015, sido_2015 = load_emd_a00_proxy()
    sido_business = load_sido_business_proxy()
    sido_eval = evaluate_sido(actual, sido_2015, sido_business)
    sigungu_eval = evaluate_sigungu(actual, sigungu_2015)
    summary = pd.concat([summarize(sido_eval, "sido"), summarize(sigungu_eval, "sigungu")], ignore_index=True)
    sample = sample_cities(sigungu_eval)
    status = {
        "sido_general_mae_pp": float(summary[(summary.level.eq("sido")) & (summary.year.eq(0))].general_mae_pp.iloc[0]),
        "sido_census_sales_mae_pp": float(summary[(summary.level.eq("sido")) & (summary.year.eq(0))].census_sales_mae_pp.iloc[0]),
        "sido_lag_mae_pp": float(summary[(summary.level.eq("sido")) & (summary.year.eq(0))].lag_mae_pp.iloc[0]),
        "sido_specialized_model": str(summary[(summary.level.eq("sido")) & (summary.year.eq(0))].best_specialized_model.iloc[0]),
        "sido_specialized_mae_pp": float(summary[(summary.level.eq("sido")) & (summary.year.eq(0))].best_specialized_mae_pp.iloc[0]),
        "sigungu_general_mae_pp": float(summary[(summary.level.eq("sigungu")) & (summary.year.eq(0))].general_mae_pp.iloc[0]),
        "sigungu_census_sales_mae_pp": float(summary[(summary.level.eq("sigungu")) & (summary.year.eq(0))].census_sales_mae_pp.iloc[0]),
        "sigungu_lag_mae_pp": float(summary[(summary.level.eq("sigungu")) & (summary.year.eq(0))].lag_mae_pp.iloc[0]),
        "sigungu_specialized_model": str(summary[(summary.level.eq("sigungu")) & (summary.year.eq(0))].best_specialized_model.iloc[0]),
        "sigungu_specialized_mae_pp": float(summary[(summary.level.eq("sigungu")) & (summary.year.eq(0))].best_specialized_mae_pp.iloc[0]),
        "sigungu_rows": int(len(sigungu_eval)),
        "sido_rows": int(len(sido_eval)),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    status["sido_improvement_pct"] = (status["sido_general_mae_pp"] - status["sido_specialized_mae_pp"]) / status["sido_general_mae_pp"] * 100
    status["sigungu_improvement_pct"] = (status["sigungu_general_mae_pp"] - status["sigungu_specialized_mae_pp"]) / status["sigungu_general_mae_pp"] * 100
    sido_eval.to_csv(DATA / "partial_stats_phase47_agri_sido_validation.csv", index=False, encoding="utf-8-sig")
    sigungu_eval.to_csv(DATA / "partial_stats_phase47_agri_sigungu_validation.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(DATA / "partial_stats_phase47_agri_validation_summary.csv", index=False, encoding="utf-8-sig")
    sample.to_csv(DATA / "partial_stats_phase47_agri_random_city_sample.csv", index=False, encoding="utf-8-sig")
    (DATA / "partial_stats_phase47_agri_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    focus_cols = ["year", "source_region", "area_name", "actual_share", "general_share", "specialized_share", "lag_share", "hybrid_share", "general_abs_error_pp", "specialized_abs_error_pp", "lag_abs_error_pp", "hybrid_abs_error_pp", "sample_group"]
    year_cols = ["level", "year", "n", "general_mae_pp", "census_sales_mae_pp", "lag_mae_pp", "hybrid_mae_pp", "best_specialized_model", "best_specialized_mae_pp", "improvement_pct"]
    yearly = summary[summary.year.ne(0)].copy()
    REPORT.write_text(f"""# 농림어업 특화 배분 1차 검증

## 실험 설계

농림어업(A00)을 일반 사업체·종사자 프록시에서 분리해 전용 배분 proxy를 검증했다. 기존 일반 proxy는 사업체수와 종사자수를 50:50으로 섞은 share이다. 1차 특화 후보는 2015 읍면동 경제총조사의 농림어업 매출 share, 직전 관측 A00 share, 그리고 `직전 관측 share 85% + 2015 매출 share 15%` 혼합모형이다. 최종 특화모형은 actual을 행·열 집계한 검증 구간에서 수준별 평균오차가 가장 낮은 후보로 판정했다.

품목별 생산량·경지면적·사육두수·임산물·어획량은 아직 미수집이므로 이번 실험은 `1차 특화 배분`이다. actual은 KOSIS 시군구 지역내총부가가치의 농업·임업·어업 연간 실제값을 사용했다.

## 전체 성능

| 수준 | 일반 MAE(%p) | 2015 매출 MAE(%p) | 직전 share MAE(%p) | 혼합 MAE(%p) | 최종 특화 | 최종 MAE(%p) | 개선율 |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 광역시도 | {status['sido_general_mae_pp']:.3f} | {status['sido_census_sales_mae_pp']:.3f} | {status['sido_lag_mae_pp']:.3f} | {float(summary[(summary.level.eq("sido")) & (summary.year.eq(0))].hybrid_mae_pp.iloc[0]):.3f} | {status['sido_specialized_model']} | {status['sido_specialized_mae_pp']:.3f} | {status['sido_improvement_pct']:.1f}% |
| 시군구 | {status['sigungu_general_mae_pp']:.3f} | {status['sigungu_census_sales_mae_pp']:.3f} | {status['sigungu_lag_mae_pp']:.3f} | {float(summary[(summary.level.eq("sigungu")) & (summary.year.eq(0))].hybrid_mae_pp.iloc[0]):.3f} | {status['sigungu_specialized_model']} | {status['sigungu_specialized_mae_pp']:.3f} | {status['sigungu_improvement_pct']:.1f}% |

## 연도별 안정성

{markdown_table(yearly, year_cols)}

## 고양·포항 및 무작위 10개 시군구

{markdown_table(sample, focus_cols)}

## 판정

농림어업은 일반 사업체·종사자 proxy에서 제거하고 A00 전용 proxy를 적용하는 편이 낫다. 단, 2015 농림어업 매출 구조만 단독으로 쓰면 시군구에서 불안정하다. 검증상 광역시도는 직전 share와 2015 매출구조를 섞은 혼합모형이 가장 낮고, 시군구는 직전 관측 A00 share 유지모형이 가장 낮다. 다음 단계에서는 경지면적, 작물별 생산량, 축산두수, 산림면적, 임산물 생산량, 어항·어선·위판량 자료를 붙여 2차 특화모형을 만들어야 한다.
""", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    main()
