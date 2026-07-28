from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase188_manufacturing_production_index_extension"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase188_manufacturing_production_index_extension.md"
RUN_ID = "partial_statistics_estimation_phase188_manufacturing_production_index_extension"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


CITY_TO_SIDO = {"고양시": "경기도", "포항시": "경상북도"}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, **kwargs)


def add_audit(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    payload = out.to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    add_audit(df).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame, digits: int = 2, max_rows: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if max_rows and len(view) > max_rows:
        view = view.head(max_rows)
    for c in view.columns:
        if pd.api.types.is_float_dtype(view[c]):
            view[c] = view[c].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
        else:
            view[c] = view[c].map(lambda x: "" if pd.isna(x) else str(x))
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    if max_rows and len(df) > max_rows:
        lines.append(f"\n_상위 {max_rows:,}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def load_manufacturing_actual() -> pd.DataFrame:
    raw = read_csv(DATA / "expanded_manufacturing_sigungu_ksic.csv", dtype=str)
    x = raw[
        raw["c1_nm"].isin(CITY_TO_SIDO)
        & raw["c2_id"].astype(str).str.startswith("C", na=False)
        & raw["metric"].eq("value_added")
    ].copy()
    x["year"] = x["prd_de"].astype(int)
    x["middle_code"] = x["c2_id"].astype(str)
    x["middle_name"] = x["c2_nm"].astype(str)
    x["actual_gva_eok"] = pd.to_numeric(x["value"], errors="coerce") / 100.0
    x = x.dropna(subset=["actual_gva_eok"])
    totals = x.groupby(["c1_nm", "year"], as_index=False)["actual_gva_eok"].sum().rename(columns={"actual_gva_eok": "city_c00_total_eok"})
    x = x.merge(totals, on=["c1_nm", "year"], how="left")
    x["actual_share"] = x["actual_gva_eok"] / x["city_c00_total_eok"]
    return x.rename(columns={"c1_nm": "city"})


def load_detail_index_growth() -> pd.DataFrame:
    idx = read_csv(DATA / "partial_stats_phase39_manufacturing_middle_production_index.csv")
    idx["year"] = idx["prd_de"].astype(str).str[:4].astype(int)
    idx["quarter"] = idx["prd_de"].astype(str).str[-2:].astype(int)
    idx["value_num"] = pd.to_numeric(idx["value"], errors="coerce")
    annual = idx.groupby(["year", "c1_nm"], as_index=False)["value_num"].mean()
    wide = annual.pivot(index="year", columns="c1_nm", values="value_num")
    rows = []
    for year in sorted(wide.index):
        prev = year - 1
        if prev not in wide.index:
            continue
        mfg_growth = wide.loc[year, "제조업"] / wide.loc[prev, "제조업"] if "제조업" in wide else np.nan
        c26_growth = wide.loc[year, "반도체 및 부품"] / wide.loc[prev, "반도체 및 부품"] if "반도체 및 부품" in wide else np.nan
        rows.append({"year": year, "mfg_growth": mfg_growth, "c26_growth": c26_growth, "c26_relative_to_mfg": c26_growth / mfg_growth})
    return pd.DataFrame(rows)


def middle_share_backtest(actual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail_growth = load_detail_index_growth()
    rows = []
    for city in sorted(actual["city"].unique()):
        city_df = actual[actual["city"].eq(city)].copy()
        for target_year in [2021, 2022, 2023, 2024]:
            prev = city_df[city_df["year"].eq(target_year - 1)].copy()
            tgt = city_df[city_df["year"].eq(target_year)].copy()
            if prev.empty or tgt.empty:
                continue
            common = sorted(set(prev["middle_code"]) & set(tgt["middle_code"]))
            prev = prev[prev["middle_code"].isin(common)].copy()
            tgt = tgt[tgt["middle_code"].isin(common)].copy()
            target_total = float(tgt["actual_gva_eok"].sum())
            base_share = prev.set_index("middle_code")["actual_gva_eok"]
            base_share = base_share / base_share.sum()
            candidates = {
                "전년 중분류 구조 유지": base_share.copy(),
                "시도 제조업 산업생산지수 적용": base_share.copy(),
            }
            g = detail_growth[detail_growth["year"].eq(target_year)]
            if not g.empty and "C26" in base_share.index:
                adjusted = base_share.copy()
                rel = float(g.iloc[0]["c26_relative_to_mfg"])
                if np.isfinite(rel) and rel > 0:
                    adjusted.loc["C26"] = adjusted.loc["C26"] * rel
                    adjusted = adjusted / adjusted.sum()
                    candidates["제한 세부지수 적용(C26만)"] = adjusted
            for cand, share in candidates.items():
                for code in common:
                    r = tgt[tgt["middle_code"].eq(code)].iloc[0]
                    pred = float(share.loc[code] * target_total)
                    actual_eok = float(r["actual_gva_eok"])
                    rows.append(
                        {
                            "city": city,
                            "target_year": target_year,
                            "candidate": cand,
                            "middle_code": code,
                            "middle_name": r["middle_name"],
                            "actual_gva_eok": actual_eok,
                            "predicted_gva_eok": pred,
                            "error_gva_eok": abs(pred - actual_eok),
                            "error_rate_pct": abs(pred - actual_eok) / actual_eok * 100 if actual_eok else np.nan,
                            "target_total_c00_eok": target_total,
                            "note": "상위 C00 총량은 집계검증용 actual; 후보 선택에는 현년 중분류 actual 미사용",
                        }
                    )
    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby(["city", "target_year", "candidate"], as_index=False)
        .agg(
            cells=("middle_code", "nunique"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("error_gva_eok", "sum"),
            gt10_cells=("error_rate_pct", lambda s: int((s > 10).sum())),
            gt20_cells=("error_rate_pct", lambda s: int((s > 20).sum())),
            gt50_cells=("error_rate_pct", lambda s: int((s > 50).sum())),
        )
    )
    summary["wape_pct"] = summary["error_sum_eok"] / summary["actual_sum_eok"] * 100
    return detail, summary


def denton_quarter(indicator: np.ndarray, quarterly: np.ndarray) -> np.ndarray:
    out = []
    for q in range(len(quarterly)):
        sl = indicator[q * 3 : q * 3 + 3].astype(float)
        if not np.isfinite(sl).all() or sl.sum() <= 0:
            weights = np.ones(3) / 3
        else:
            weights = sl / sl.sum()
        out.extend(weights * quarterly[q])
    return np.asarray(out)


def pohang_temporal_extension() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    controls = read_csv(DATA / "partial_stats_phase42_pohang_parent_monthly_controls.csv")
    c00 = controls[controls["gva_parent_code"].eq("C00")].copy().sort_values(["year", "month"])
    q = c00.groupby(["year", "quarter"], as_index=False)["estimated_city_parent_monthly_gva"].sum()

    prod = read_csv(DATA / "rolling_mining_manufacturing_production_index.csv")
    prod = prod[(prod["c1_nm"].eq("경상북도")) & (prod["c2_nm"].eq("제조업"))].copy()
    prod["year"] = prod["prd_de"].astype(str).str[:4].astype(int)
    prod["quarter"] = prod["prd_de"].astype(str).str[-2:].astype(int)
    prod["production_index"] = pd.to_numeric(prod["value"], errors="coerce")
    prod = prod.loc[prod.index.repeat(3)].copy()
    prod["month"] = (prod["quarter"] - 1) * 3 + prod.groupby(["year", "quarter"]).cumcount() + 1

    elec = read_csv(DATA / "municipality_electricity_features_2021_2023.csv")
    e = elec[elec["sigungu_name"].eq("포항시")][["year", "month", "electricity_industrial_kwh"]].copy()
    e = e.rename(columns={"electricity_industrial_kwh": "industrial_kwh"})

    panel = c00[["year", "quarter", "month", "period", "estimated_city_parent_monthly_gva"]].merge(
        prod[["year", "quarter", "month", "production_index"]], on=["year", "quarter", "month"], how="left"
    ).merge(e, on=["year", "month"], how="left")
    for col in ["production_index", "industrial_kwh"]:
        panel[f"{col}_norm"] = panel[col] / panel.groupby("year")[col].transform("mean")
    panel["indicator"] = np.sqrt(panel["production_index_norm"] * panel["industrial_kwh_norm"])

    fitted = []
    for year, yg in panel.groupby("year", sort=True):
        yq = q[q["year"].eq(year)].sort_values("quarter")["estimated_city_parent_monthly_gva"].to_numpy()
        fitted.extend(denton_quarter(yg.sort_values("month")["indicator"].to_numpy(), yq))
    panel["industrial_index_power_monthly_gva"] = fitted
    panel["uniform_monthly_gva"] = panel["estimated_city_parent_monthly_gva"]
    panel["monthly_delta_vs_uniform_eok"] = (panel["industrial_index_power_monthly_gva"] - panel["uniform_monthly_gva"]) / 100.0
    panel["industrial_index_power_monthly_gva_eok"] = panel["industrial_index_power_monthly_gva"] / 100.0
    panel["uniform_monthly_gva_eok"] = panel["uniform_monthly_gva"] / 100.0
    check = (
        panel.groupby(["year", "quarter"], as_index=False)
        .agg(
            uniform_quarter=("uniform_monthly_gva", "sum"),
            index_power_quarter=("industrial_index_power_monthly_gva", "sum"),
        )
    )
    check["quarter_error"] = check["index_power_quarter"] - check["uniform_quarter"]
    for col in ["uniform_quarter", "index_power_quarter", "quarter_error"]:
        check[f"{col}_eok"] = check[col] / 100.0
    shape = (
        panel.groupby("year", as_index=False)
        .agg(
            months=("month", "count"),
            max_abs_month_delta_eok=("monthly_delta_vs_uniform_eok", lambda s: float(s.abs().max())),
            mean_abs_month_delta_eok=("monthly_delta_vs_uniform_eok", lambda s: float(s.abs().mean())),
            production_index_min=("production_index", "min"),
            production_index_max=("production_index", "max"),
            industrial_kwh_min=("industrial_kwh", "min"),
            industrial_kwh_max=("industrial_kwh", "max"),
        )
    )
    return panel, check, shape


def write_report(summary: pd.DataFrame, detail: pd.DataFrame, quarter_check: pd.DataFrame, temporal_shape: pd.DataFrame) -> None:
    latest = summary[summary["target_year"].isin([2023, 2024])].copy()
    cmp_rows = []
    for (city, year), g in latest.groupby(["city", "target_year"]):
        base = g[g["candidate"].eq("전년 중분류 구조 유지")]
        broad = g[g["candidate"].eq("시도 제조업 산업생산지수 적용")]
        detail_idx = g[g["candidate"].eq("제한 세부지수 적용(C26만)")]
        cmp_rows.append(
            {
                "지역": city,
                "연도": year,
                "전년구조 WAPE(%)": float(base.iloc[0]["wape_pct"]) if len(base) else np.nan,
                "시도 제조업지수 WAPE(%)": float(broad.iloc[0]["wape_pct"]) if len(broad) else np.nan,
                "제한 세부지수 WAPE(%)": float(detail_idx.iloc[0]["wape_pct"]) if len(detail_idx) else np.nan,
                "판정": "중분류 횡단면 개선 없음" if len(broad) and len(base) and abs(float(broad.iloc[0]["wape_pct"]) - float(base.iloc[0]["wape_pct"])) < 1e-9 else "변화 있음",
            }
        )
    cmp = pd.DataFrame(cmp_rows)

    worst = detail[detail["target_year"].isin([2023, 2024]) & detail["candidate"].eq("전년 중분류 구조 유지")].copy()
    worst = worst.sort_values("error_gva_eok", ascending=False).head(20)

    text = f"""# Phase188 제조업 산업생산지수 적용 확장 실험

## 목적

Phase187에서 확인한 누락을 실험으로 보정했다. 제조업 산업생산지수를 두 용도로 분리했다.

1. **시간배분**: 제조업 전체 월별 총부가가치 경로를 만들 때 사용한다.
2. **중분류 배분**: KSIC 중분류별 금액 격차를 줄이는 데 직접 쓸 수 있는지 검증한다.

## 핵심 결론

- 포항 제조업 월 경로는 기존 `분기 내 균등` 대신 **경북 제조업 산업생산지수 + 포항 산업용 전력량**으로 개선 가능하다. 분기 총량은 그대로 보존된다.
- 그러나 시도 제조업 산업생산지수는 모든 제조업 중분류에 동일하게 적용되는 지표라서, 상위 C00 총량에 정규화하면 **중분류 비중은 전년 구조와 같아진다**. 즉 중분류 오차를 줄이는 독립 정보가 아니다.
- 전국 세부 광공업생산지수는 현재 로컬 기준 `반도체 및 부품` 등 일부 항목만 있어 C26에만 제한 적용 가능하다. 전체 KSIC 중분류 개선에는 부족하다.
- 따라서 제조업 중분류/소분류 오차를 10% 근처로 줄이려면 산업생산지수를 시간축 중심 지표로 두고, 중분류 횡단면은 공장등록 생산품·공장면적·종업원·산업용 전력 중분류 매핑·항만 물동량 같은 **지역 활동자료**로 보강해야 한다.

## 2023~2024 중분류 집계검증 비교

단위: 실제·추정은 억원 기반 집계, WAPE는 `Σ|추정-실제| / Σ실제`.

{md_table(cmp, 2)}

## 포항 제조업 월 경로 개선 검증

기존 포항 C00는 분기 내 균등 배분이었다. 새 후보는 경북 제조업 산업생산지수와 포항 산업용 전력량을 결합해 월별 굴곡을 만든다. 실제 월별 GVA는 없으므로 성능 수치가 아니라 **시간 해상도 개선 및 분기 총량 보존 검증**으로 해석한다.

### 분기 총량 보존 검증

단위: 억원.

{md_table(quarter_check[["year","quarter","uniform_quarter_eok","index_power_quarter_eok","quarter_error_eok"]].rename(columns={
    "year": "연도",
    "quarter": "분기",
    "uniform_quarter_eok": "기존 분기합계",
    "index_power_quarter_eok": "개선후 분기합계",
    "quarter_error_eok": "분기오차",
}), 4)}

### 월별 굴곡 생성 규모

단위: 억원, kWh, 지수.

{md_table(temporal_shape.rename(columns={
    "year": "연도",
    "months": "월수",
    "max_abs_month_delta_eok": "최대 월 차이",
    "mean_abs_month_delta_eok": "평균 월 차이",
    "production_index_min": "생산지수 최소",
    "production_index_max": "생산지수 최대",
    "industrial_kwh_min": "산업용전력 최소",
    "industrial_kwh_max": "산업용전력 최대",
}), 2)}

## 2023~2024 금액오차 상위 제조업 중분류

이 표는 산업생산지수 단독으로는 해결되지 않는 중분류 구조오차다.

{md_table(worst[["city","target_year","middle_code","middle_name","actual_gva_eok","predicted_gva_eok","error_gva_eok","error_rate_pct"]].rename(columns={
    "city": "지역",
    "target_year": "연도",
    "middle_code": "코드",
    "middle_name": "중분류",
    "actual_gva_eok": "실제(억원)",
    "predicted_gva_eok": "추정(억원)",
    "error_gva_eok": "오차(억원)",
    "error_rate_pct": "오차율(%)",
}), 2, 20)}

## 운영 판정

1. 제조업 산업생산지수는 포스터/보고서에서 반드시 제조업 시간배분의 핵심 지표로 설명해야 한다.
2. 포항 C00 월별 큐브는 향후 재생성 시 `분기 내 균등`이 아니라 `경북 제조업 산업생산지수 + 포항 산업용 전력량` 경로로 대체하는 것이 맞다.
3. 단, 이 변경은 월별 시간분포 개선이지 중분류 금액오차 개선이 아니다. 중분류 오차 감소를 주장하면 안 된다.
4. 중분류 개선의 다음 작업은 C10/C18/C23/C29/C34 등 잔여오차 업종별로 공장등록·전력·항만·정비계약성 자료를 분리 적용하는 것이다.
"""
    REPORT.write_text(text, encoding="utf-8")


def main() -> None:
    actual = load_manufacturing_actual()
    detail, summary = middle_share_backtest(actual)
    temporal_panel, quarter_check, temporal_shape = pohang_temporal_extension()
    write_csv("phase188_middle_share_backtest_detail.csv", detail)
    write_csv("phase188_middle_share_backtest_summary.csv", summary)
    write_csv("phase188_pohang_c00_index_power_monthly_panel.csv", temporal_panel)
    write_csv("phase188_pohang_c00_index_power_quarter_check.csv", quarter_check)
    write_csv("phase188_pohang_c00_index_power_year_shape.csv", temporal_shape)
    write_report(summary, detail, quarter_check, temporal_shape)
    print(REPORT)


if __name__ == "__main__":
    main()
