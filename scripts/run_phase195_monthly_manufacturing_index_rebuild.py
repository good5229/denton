from __future__ import annotations

import hashlib
import sys
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from kosis_common import get_kosis_key, kosis_data, normalize_kosis_rows, write_json  # noqa: E402


DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase195_monthly_manufacturing_index_rebuild"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase195_monthly_manufacturing_index_rebuild.md"
RUN_ID = "partial_statistics_estimation_phase195_monthly_manufacturing_index_rebuild"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


CITY_SPECS = {
    "고양시": {
        "sido": "경기도",
        "previous_path": DATA / "partial_stats_phase39_manufacturing_city_monthly.csv",
        "previous_col": "estimated_city_manufacturing_monthly_gva",
    },
    "포항시": {
        "sido": "경상북도",
        "previous_path": DATA
        / "phase188_manufacturing_production_index_extension"
        / "phase188_pohang_c00_index_power_monthly_panel.csv",
        "previous_col": "industrial_index_power_monthly_gva",
    },
}


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


def stamp(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    payload = out.to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp(df).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def write_processed_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
        else:
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else str(x))
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    return "\n".join(lines)


def proportional_denton(indicator: np.ndarray, benchmarks: np.ndarray, frequency: int = 3) -> np.ndarray:
    i, b = np.asarray(indicator, float), np.asarray(benchmarks, float)
    n = len(i)
    if n != len(b) * frequency:
        raise ValueError(f"indicator length {n} != benchmark length {len(b)} * {frequency}")
    i = np.where(np.isfinite(i) & (i > 0), i, np.nan)
    if np.isnan(i).any():
        median = np.nanmedian(i)
        i = np.where(np.isnan(i), median if np.isfinite(median) and median > 0 else 1.0, i)
    m = np.diag(1 / i)
    d = np.zeros((n - 1, n))
    for r in range(n - 1):
        d[r, r], d[r, r + 1] = -1, 1
    h = 2 * m.T @ d.T @ d @ m
    j = np.zeros((len(b), n))
    for k in range(len(b)):
        j[k, k * frequency : (k + 1) * frequency] = 1
    lhs = np.block([[h, j.T], [j, np.zeros((len(b), len(b)))]] )
    answer = np.linalg.lstsq(lhs, np.r_[np.zeros(n), b], rcond=None)[0][:n]
    if np.any(answer <= 0):
        fallback = []
        for k, benchmark in enumerate(b):
            sl = i[k * frequency : (k + 1) * frequency]
            fallback.extend((sl / sl.sum() * benchmark).tolist())
        answer = np.asarray(fallback)
    return answer


def collect_monthly_kosis() -> tuple[pd.DataFrame, pd.DataFrame]:
    key = get_kosis_key()
    RAW.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    mm_rows = kosis_data(
        api_key=key,
        org_id="101",
        tbl_id="DT_1F02001",
        item_id="T10",
        period="M",
        start="201501",
        end="202505",
        obj={1: "ALL", 2: "C"},
    )
    detail_rows = kosis_data(
        api_key=key,
        org_id="101",
        tbl_id="DT_1F02011",
        item_id="T10",
        period="M",
        start="202001",
        end="202505",
        obj={1: "ALL"},
    )
    write_json(RAW / "phase195_kosis_DT_1F02001_monthly_manufacturing.json", mm_rows)
    write_json(RAW / "phase195_kosis_DT_1F02011_monthly_detail_manufacturing.json", detail_rows)

    mm_norm = normalize_kosis_rows(mm_rows, "phase195_monthly_mining_manufacturing_production_index")
    detail_norm = normalize_kosis_rows(detail_rows, "phase195_monthly_detail_manufacturing_production_index")
    mm_path = DATA / "phase195_monthly_mining_manufacturing_production_index.csv"
    detail_path = DATA / "phase195_monthly_detail_manufacturing_production_index.csv"
    write_processed_csv(mm_path, mm_norm)
    write_processed_csv(detail_path, detail_norm)
    return pd.DataFrame(mm_norm), pd.DataFrame(detail_norm)


def load_quarter_controls(city: str) -> pd.DataFrame:
    if city == "고양시":
        controls = pd.read_parquet(DATA / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
        q = controls[
            controls["source_region"].eq("경기도")
            & controls["sigungu_name"].eq("고양시")
            & controls["sector_code"].eq("C00")
            & controls["year"].between(2021, 2023)
        ][["year", "quarter", "estimated_quarterly_gva"]].copy()
        return q.rename(columns={"estimated_quarterly_gva": "quarterly_c00_gva"})
    controls = read_csv(DATA / "partial_stats_phase42_pohang_parent_monthly_controls.csv")
    c00 = controls[controls["gva_parent_code"].eq("C00") & controls["year"].between(2021, 2023)].copy()
    return (
        c00.groupby(["year", "quarter"], as_index=False)["estimated_city_parent_monthly_gva"]
        .sum()
        .rename(columns={"estimated_city_parent_monthly_gva": "quarterly_c00_gva"})
    )


def rebuild_city(city: str, monthly_index: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    spec = CITY_SPECS[city]
    sido = spec["sido"]
    prod = monthly_index[(monthly_index["c1_nm"].eq(sido)) & (monthly_index["c2_nm"].eq("제조업"))].copy()
    prod["year"] = prod["prd_de"].astype(str).str[:4].astype(int)
    prod["month"] = prod["prd_de"].astype(str).str[-2:].astype(int)
    prod["quarter"] = ((prod["month"] - 1) // 3 + 1).astype(int)
    prod["production_index_monthly"] = pd.to_numeric(prod["value"], errors="coerce")
    prod = prod[prod["year"].between(2021, 2023)].sort_values(["year", "month"])

    elec = read_csv(DATA / "municipality_electricity_features_2021_2023.csv")
    e = elec[elec["sigungu_name"].eq(city)][["year", "month", "electricity_industrial_kwh"]].copy()
    e = e.rename(columns={"electricity_industrial_kwh": "industrial_kwh"})

    panel = prod[
        [
            "dataset",
            "tbl_id",
            "tbl_nm",
            "prd_se",
            "prd_de",
            "item_nm",
            "unit_nm",
            "c1_id",
            "c1_nm",
            "c2_id",
            "c2_nm",
            "year",
            "quarter",
            "month",
            "production_index_monthly",
        ]
    ].merge(e, on=["year", "month"], how="left")
    if panel["industrial_kwh"].isna().any():
        missing = panel[panel["industrial_kwh"].isna()][["year", "month"]].drop_duplicates()
        raise RuntimeError(f"{city} industrial electricity missing: {missing.to_dict('records')[:5]}")
    for col in ["production_index_monthly", "industrial_kwh"]:
        panel[f"{col}_norm"] = panel[col] / panel.groupby("year")[col].transform("mean")
    panel["indicator_monthly_index_power"] = np.sqrt(
        panel["production_index_monthly_norm"] * panel["industrial_kwh_norm"]
    )
    panel["indicator_electricity_only"] = np.sqrt(panel["industrial_kwh_norm"])
    panel["indicator_production_only"] = panel["production_index_monthly_norm"]

    q = load_quarter_controls(city).sort_values(["year", "quarter"])
    q = q[q["year"].between(2021, 2023)].copy()
    if len(q) != 12:
        raise RuntimeError(f"{city} expected 12 quarterly controls, got {len(q)}")

    panel = panel.sort_values(["year", "month"]).copy()
    benchmarks = q["quarterly_c00_gva"].to_numpy()
    panel["monthly_index_power_gva"] = proportional_denton(panel["indicator_monthly_index_power"].to_numpy(), benchmarks)
    panel["monthly_electricity_only_gva"] = proportional_denton(panel["indicator_electricity_only"].to_numpy(), benchmarks)
    panel["monthly_production_only_gva"] = proportional_denton(panel["indicator_production_only"].to_numpy(), benchmarks)

    prev_path = spec["previous_path"]
    if prev_path.exists():
        prev = read_csv(prev_path)
        prev_cols = ["year", "month", spec["previous_col"]]
        panel = panel.merge(prev[prev_cols], on=["year", "month"], how="left")
        panel = panel.rename(columns={spec["previous_col"]: "previous_monthly_gva"})
    else:
        panel["previous_monthly_gva"] = np.nan

    for col in [
        "monthly_index_power_gva",
        "monthly_electricity_only_gva",
        "monthly_production_only_gva",
        "previous_monthly_gva",
    ]:
        panel[f"{col}_eok"] = panel[col] / 100.0
    panel["delta_vs_previous_eok"] = panel["monthly_index_power_gva_eok"] - panel["previous_monthly_gva_eok"]
    panel["delta_vs_electricity_only_eok"] = (
        panel["monthly_index_power_gva_eok"] - panel["monthly_electricity_only_gva_eok"]
    )

    check = (
        panel.groupby(["year", "quarter"], as_index=False)
        .agg(
            monthly_index_power_sum=("monthly_index_power_gva", "sum"),
            monthly_electricity_only_sum=("monthly_electricity_only_gva", "sum"),
            monthly_production_only_sum=("monthly_production_only_gva", "sum"),
        )
        .merge(q, on=["year", "quarter"], how="left")
    )
    for col in ["monthly_index_power_sum", "monthly_electricity_only_sum", "monthly_production_only_sum"]:
        check[f"{col}_error"] = check[col] - check["quarterly_c00_gva"]
        check[f"{col}_error_eok"] = check[f"{col}_error"] / 100.0
    check.insert(0, "city", city)
    panel.insert(0, "city", city)
    return panel, check


def summarize_panels(panel: pd.DataFrame, check: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = (
        panel.groupby(["city", "year"], as_index=False)
        .agg(
            months=("month", "count"),
            production_index_min=("production_index_monthly", "min"),
            production_index_max=("production_index_monthly", "max"),
            industrial_kwh_min=("industrial_kwh", "min"),
            industrial_kwh_max=("industrial_kwh", "max"),
            max_abs_delta_vs_previous_eok=("delta_vs_previous_eok", lambda s: float(s.abs().max())),
            mean_abs_delta_vs_previous_eok=("delta_vs_previous_eok", lambda s: float(s.abs().mean())),
            max_abs_delta_vs_electricity_only_eok=("delta_vs_electricity_only_eok", lambda s: float(s.abs().max())),
            mean_abs_delta_vs_electricity_only_eok=("delta_vs_electricity_only_eok", lambda s: float(s.abs().mean())),
        )
    )
    accounting = (
        check.groupby("city", as_index=False)
        .agg(
            quarters=("quarter", "count"),
            max_abs_quarter_error_eok=("monthly_index_power_sum_error_eok", lambda s: float(s.abs().max())),
            mean_abs_quarter_error_eok=("monthly_index_power_sum_error_eok", lambda s: float(s.abs().mean())),
        )
    )
    return summary, accounting


def main() -> int:
    monthly_index, detail_index = collect_monthly_kosis()
    panels = []
    checks = []
    for city in CITY_SPECS:
        panel, check = rebuild_city(city, monthly_index)
        panels.append(panel)
        checks.append(check)
    panel_all = pd.concat(panels, ignore_index=True)
    check_all = pd.concat(checks, ignore_index=True)
    summary, accounting = summarize_panels(panel_all, check_all)

    write_csv("phase195_city_c00_monthly_panel.csv", panel_all)
    write_csv("phase195_quarter_accounting_check.csv", check_all)
    write_csv("phase195_monthly_change_summary.csv", summary)
    write_csv("phase195_accounting_summary.csv", accounting)

    source_summary = pd.DataFrame(
        [
            {
                "source": "DT_1F02001",
                "description": "시도/산업별 광공업생산지수(2020=100)",
                "period": "M",
                "rows": len(monthly_index),
                "period_min": monthly_index["prd_de"].astype(str).min(),
                "period_max": monthly_index["prd_de"].astype(str).max(),
                "regions": monthly_index["c1_nm"].nunique(),
                "industries": monthly_index["c2_nm"].nunique(),
            },
            {
                "source": "DT_1F02011",
                "description": "기본분류 일부항목 제외 광공업생산지수(2020=100)",
                "period": "M",
                "rows": len(detail_index),
                "period_min": detail_index["prd_de"].astype(str).min(),
                "period_max": detail_index["prd_de"].astype(str).max(),
                "regions": 0,
                "industries": detail_index["c1_nm"].nunique() if "c1_nm" in detail_index else np.nan,
            },
        ]
    )
    write_csv("phase195_source_summary.csv", source_summary)

    report = f"""# Phase195 월간 제조업 산업생산지수 재수집 및 C00 월별 경로 재산정

## 목적

Phase194 감사에서 제조업 산업생산지수가 분기(`Q`)로 수집되어 월별 제조업 총부가가치 경로에 충분히 반영되지 못한 문제가 확인됐다. Phase195는 KOSIS 월간(`M`) 자료를 재수집하고, 고양시·포항시 제조업 C00 월별 총부가가치 경로를 다시 만든다.

## 수집 결과

{md_table(source_summary.rename(columns={
    "source": "원천",
    "description": "자료명",
    "period": "주기",
    "rows": "행수",
    "period_min": "시작",
    "period_max": "종료",
    "regions": "지역수",
    "industries": "항목수",
}), 0)}

## 재산정 방식

- 대상: 고양시·포항시 제조업 C00 총부가가치
- 시간: 2021년 1월~2023년 12월
- 통제총량: 기존 분기 제조업 GVA 총량
- 월별 지표: `sqrt(월간 시도 제조업 산업생산지수 × 시군구 산업용 전력량)`
- 제약 방식: 비례 Denton. 월 합계가 분기 총량과 일치하도록 조정

## 분기 총량 보존

단위: 억원.

{md_table(accounting.rename(columns={
    "city": "지역",
    "quarters": "분기수",
    "max_abs_quarter_error_eok": "최대 분기오차",
    "mean_abs_quarter_error_eok": "평균 분기오차",
}), 8)}

## 기존 경로 대비 변화

단위: 월별 GVA 차이는 억원.

{md_table(summary.rename(columns={
    "city": "지역",
    "year": "연도",
    "months": "월수",
    "production_index_min": "월간 생산지수 최소",
    "production_index_max": "월간 생산지수 최대",
    "industrial_kwh_min": "산업용전력 최소",
    "industrial_kwh_max": "산업용전력 최대",
    "max_abs_delta_vs_previous_eok": "기존경로 대비 최대차",
    "mean_abs_delta_vs_previous_eok": "기존경로 대비 평균차",
    "max_abs_delta_vs_electricity_only_eok": "전력단독 대비 최대차",
    "mean_abs_delta_vs_electricity_only_eok": "전력단독 대비 평균차",
}), 2)}

## 판정

1. 월간 제조업 산업생산지수 수집은 가능하며, 기존 분기 수집 설정은 교정되어야 한다.
2. 고양시와 포항시 모두 월간 생산지수를 반영하면 기존 월별 제조업 GVA 경로가 유의미하게 달라진다.
3. 분기 총량 보존 오차는 사실상 0이므로 회계 정합성은 유지된다.
4. 이 결과는 제조업 C00의 **시간 해상도 개선**이다. KSIC 중분류·소분류 금액오차 개선은 별도 직접 활동자료 결합이 필요하다.

## 후속 작업

1. Phase195 경로를 포항 Phase191 큐브와 고양 제조업 월별 큐브 후보에 반영한다.
2. 포스터의 제조업 설명에서 `분기 산업생산지수` 표현을 제거하고 `월간 산업생산지수` 기반으로 교체한다.
3. 중분류 개선은 월간 세부 생산지수의 항목 매핑 가능성과 KICOX/항만/공장 자료를 결합해 별도 검증한다.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
