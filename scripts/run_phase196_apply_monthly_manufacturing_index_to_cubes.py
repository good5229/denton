from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_partial_statistics_phase40_gva import multiresolution_cube as goyang_multiresolution
from run_partial_statistics_phase42_gva import multiresolution as pohang_multiresolution


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase196_monthly_manufacturing_index_cubes"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase196_monthly_manufacturing_index_cubes.md"
RUN_ID = "partial_statistics_estimation_phase196_monthly_manufacturing_index_cubes"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


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
    payload = out.head(100_000).to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp(df).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def write_parquet(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp(df).to_parquet(OUT / name, index=False)


def md_table(df: pd.DataFrame, digits: int = 4) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
        else:
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else str(x))
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    return "\n".join(lines)


def phase195_controls() -> pd.DataFrame:
    p = OUT.parent / "phase195_monthly_manufacturing_index_rebuild" / "phase195_city_c00_monthly_panel.csv"
    if not p.exists():
        raise FileNotFoundError("Run Phase195 first: " + str(p.relative_to(ROOT)))
    x = read_csv(p)
    if "period" not in x.columns:
        x["period"] = x["year"].astype(int).astype(str) + "-" + x["month"].astype(int).astype(str).str.zfill(2)
    return x[["city", "year", "quarter", "month", "period", "monthly_index_power_gva"]].rename(
        columns={"monthly_index_power_gva": "new_city_c00_monthly_gva"}
    )


def scale_goyang(controls: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = read_csv(DATA / "partial_stats_phase40_goyang_emd_small_monthly.csv", dtype={"emd_code": str})
    ctl = controls[controls["city"].eq("고양시")].copy()
    old_month = (
        base.groupby(["year", "quarter", "month", "period"], as_index=False)["estimated_emd_small_monthly_gva"]
        .sum()
        .rename(columns={"estimated_emd_small_monthly_gva": "old_city_c00_monthly_gva"})
    )
    scale = old_month.merge(ctl, on=["year", "quarter", "month", "period"], how="left")
    scale["scale_factor"] = np.where(
        scale["old_city_c00_monthly_gva"].abs() > 0,
        scale["new_city_c00_monthly_gva"] / scale["old_city_c00_monthly_gva"],
        1.0,
    )
    new_base = base.merge(
        scale[["year", "month", "scale_factor", "new_city_c00_monthly_gva"]],
        on=["year", "month"],
        how="left",
    )
    new_base["estimated_emd_middle_monthly_gva"] = (
        new_base["estimated_emd_middle_monthly_gva"] * new_base["scale_factor"].fillna(1.0)
    )
    new_base["estimated_emd_small_monthly_gva"] = (
        new_base["estimated_emd_small_monthly_gva"] * new_base["scale_factor"].fillna(1.0)
    )
    new_base["temporal_source"] = "월간 경기도 제조업 산업생산지수+고양시 산업용 전력"
    new_base = new_base.drop(columns=["scale_factor", "new_city_c00_monthly_gva"], errors="ignore")
    multi = goyang_multiresolution(new_base)
    return new_base, multi, scale


def scale_pohang(controls: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base_path = DATA / "phase191_pohang_c00_temporal_candidate_cube" / "phase191_pohang_emd_group_monthly.parquet"
    if not base_path.exists():
        base_path = DATA / "partial_stats_phase45_pohang_final_emd_small_monthly.parquet"
    base = pd.read_parquet(base_path)
    ctl = controls[controls["city"].eq("포항시")].copy()
    is_c00 = base["gva_parent_code"].eq("C00")
    old_month = (
        base[is_c00]
        .groupby(["year", "quarter", "month", "period", "gva_parent_code"], as_index=False)["estimated_emd_group_monthly_gva"]
        .sum()
        .rename(columns={"estimated_emd_group_monthly_gva": "old_city_c00_monthly_gva"})
    )
    scale = old_month.merge(ctl, on=["year", "quarter", "month", "period"], how="left")
    scale["scale_factor"] = np.where(
        scale["old_city_c00_monthly_gva"].abs() > 0,
        scale["new_city_c00_monthly_gva"] / scale["old_city_c00_monthly_gva"],
        1.0,
    )
    new_base = base.copy()
    c00 = new_base[is_c00].merge(
        scale[["year", "month", "gva_parent_code", "scale_factor", "new_city_c00_monthly_gva"]],
        on=["year", "month", "gva_parent_code"],
        how="left",
    )
    c00["estimated_city_parent_monthly_gva"] = c00["new_city_c00_monthly_gva"].fillna(
        c00["estimated_city_parent_monthly_gva"]
    )
    c00["estimated_city_group_monthly_gva"] = (
        c00["estimated_city_group_monthly_gva"] * c00["scale_factor"].fillna(1.0)
    )
    c00["estimated_emd_group_monthly_gva"] = (
        c00["estimated_emd_group_monthly_gva"] * c00["scale_factor"].fillna(1.0)
    )
    c00["temporal_source"] = "월간 경북 제조업 산업생산지수+포항시 산업용 전력"
    c00 = c00.drop(columns=["scale_factor", "new_city_c00_monthly_gva"], errors="ignore")
    new_base = pd.concat([new_base[~is_c00], c00], ignore_index=True).sort_values(
        ["year", "month", "gva_parent_code", "division_code", "group_code", "emd_code"]
    )
    multi = pohang_multiresolution(new_base)
    return new_base, multi, scale


def check_goyang(base: pd.DataFrame, multi: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ctl = controls[controls["city"].eq("고양시")]
    city_month = (
        base.groupby(["year", "quarter", "month", "period"], as_index=False)["estimated_emd_small_monthly_gva"]
        .sum()
        .merge(ctl, on=["year", "quarter", "month", "period"], how="left")
    )
    err = city_month["estimated_emd_small_monthly_gva"] - city_month["new_city_c00_monthly_gva"]
    rows.append(
        {
            "city": "고양시",
            "check": "행정동·소분류 월합→시 C00 월통제",
            "cells": len(city_month),
            "max_abs_error": float(err.abs().max()),
            "mean_abs_error": float(err.abs().mean()),
        }
    )
    city_quarter = (
        city_month.groupby(["year", "quarter"], as_index=False)
        .agg(estimated=("estimated_emd_small_monthly_gva", "sum"), target=("new_city_c00_monthly_gva", "sum"))
    )
    qerr = city_quarter["estimated"] - city_quarter["target"]
    rows.append(
        {
            "city": "고양시",
            "check": "월→분기 C00 보존",
            "cells": len(city_quarter),
            "max_abs_error": float(qerr.abs().max()),
            "mean_abs_error": float(qerr.abs().mean()),
        }
    )
    city_year = (
        city_month.groupby("year", as_index=False)
        .agg(estimated=("estimated_emd_small_monthly_gva", "sum"), target=("new_city_c00_monthly_gva", "sum"))
    )
    yerr = city_year["estimated"] - city_year["target"]
    rows.append(
        {
            "city": "고양시",
            "check": "월→연 C00 보존",
            "cells": len(city_year),
            "max_abs_error": float(yerr.abs().max()),
            "mean_abs_error": float(yerr.abs().mean()),
        }
    )
    return pd.DataFrame(rows)


def check_pohang(base: pd.DataFrame, multi: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ctl = controls[controls["city"].eq("포항시")]
    c00 = base[base["gva_parent_code"].eq("C00")].copy()
    city_month = (
        c00.groupby(["year", "quarter", "month", "period"], as_index=False)["estimated_emd_group_monthly_gva"]
        .sum()
        .merge(ctl, on=["year", "quarter", "month", "period"], how="left")
    )
    err = city_month["estimated_emd_group_monthly_gva"] - city_month["new_city_c00_monthly_gva"]
    rows.append(
        {
            "city": "포항시",
            "check": "읍면동·소분류 월합→시 C00 월통제",
            "cells": len(city_month),
            "max_abs_error": float(err.abs().max()),
            "mean_abs_error": float(err.abs().mean()),
        }
    )
    city_quarter = (
        city_month.groupby(["year", "quarter"], as_index=False)
        .agg(estimated=("estimated_emd_group_monthly_gva", "sum"), target=("new_city_c00_monthly_gva", "sum"))
    )
    qerr = city_quarter["estimated"] - city_quarter["target"]
    rows.append(
        {
            "city": "포항시",
            "check": "월→분기 C00 보존",
            "cells": len(city_quarter),
            "max_abs_error": float(qerr.abs().max()),
            "mean_abs_error": float(qerr.abs().mean()),
        }
    )
    city_year = (
        city_month.groupby("year", as_index=False)
        .agg(estimated=("estimated_emd_group_monthly_gva", "sum"), target=("new_city_c00_monthly_gva", "sum"))
    )
    yerr = city_year["estimated"] - city_year["target"]
    rows.append(
        {
            "city": "포항시",
            "check": "월→연 C00 보존",
            "cells": len(city_year),
            "max_abs_error": float(yerr.abs().max()),
            "mean_abs_error": float(yerr.abs().mean()),
        }
    )
    return pd.DataFrame(rows)


def scale_summary(scale: pd.DataFrame, city: str) -> pd.DataFrame:
    out = (
        scale.groupby("year", as_index=False)
        .agg(
            months=("month", "count"),
            old_sum=("old_city_c00_monthly_gva", "sum"),
            new_sum=("new_city_c00_monthly_gva", "sum"),
            min_scale=("scale_factor", "min"),
            max_scale=("scale_factor", "max"),
            mean_abs_month_delta=("scale_factor", lambda s: np.nan),
        )
    )
    d = scale.copy()
    d["abs_delta_eok"] = (d["new_city_c00_monthly_gva"] - d["old_city_c00_monthly_gva"]).abs() / 100.0
    mean_delta = d.groupby("year")["abs_delta_eok"].mean().reset_index(name="mean_abs_month_delta_eok")
    max_delta = d.groupby("year")["abs_delta_eok"].max().reset_index(name="max_abs_month_delta_eok")
    out = out.drop(columns=["mean_abs_month_delta"]).merge(mean_delta, on="year").merge(max_delta, on="year")
    out["old_sum_eok"] = out["old_sum"] / 100.0
    out["new_sum_eok"] = out["new_sum"] / 100.0
    out["annual_delta_eok"] = out["new_sum_eok"] - out["old_sum_eok"]
    out.insert(0, "city", city)
    return out[
        [
            "city",
            "year",
            "months",
            "old_sum_eok",
            "new_sum_eok",
            "annual_delta_eok",
            "min_scale",
            "max_scale",
            "mean_abs_month_delta_eok",
            "max_abs_month_delta_eok",
        ]
    ]


def main() -> int:
    controls = phase195_controls()
    goyang_base, goyang_multi, goyang_scale = scale_goyang(controls)
    pohang_base, pohang_multi, pohang_scale = scale_pohang(controls)

    checks = pd.concat(
        [check_goyang(goyang_base, goyang_multi, controls), check_pohang(pohang_base, pohang_multi, controls)],
        ignore_index=True,
    )
    summaries = pd.concat([scale_summary(goyang_scale, "고양시"), scale_summary(pohang_scale, "포항시")], ignore_index=True)

    write_parquet("phase196_goyang_emd_small_monthly.parquet", goyang_base)
    write_parquet("phase196_goyang_manufacturing_multiresolution_cube.parquet", goyang_multi)
    write_parquet("phase196_pohang_emd_group_monthly.parquet", pohang_base)
    write_parquet("phase196_pohang_multiresolution_cube.parquet", pohang_multi)
    write_csv("phase196_accounting_checks.csv", checks)
    write_csv("phase196_c00_monthly_scale_summary.csv", summaries)
    write_csv("phase196_goyang_c00_monthly_scale.csv", goyang_scale)
    write_csv("phase196_pohang_c00_monthly_scale.csv", pohang_scale)

    check_show = checks.copy()
    for col in ["max_abs_error", "mean_abs_error"]:
        check_show[col + "_eok"] = check_show[col] / 100.0
    report = f"""# Phase196 월간 제조업 산업생산지수 반영 후보 큐브

## 목적

Phase195에서 재수집한 월간 제조업 산업생산지수를 고양시·포항시의 하위 공간·산업 큐브에 실제 반영했다. 기존 최종 산출물은 덮어쓰지 않고 별도 후보 큐브로 저장했다.

## 적용 방식

- 대상 산업: 제조업 C00
- 대상 시간: 2021년 1월~2023년 12월
- 월 통제값: Phase195 `sqrt(월간 시도 제조업 산업생산지수 × 시군구 산업용 전력량)` 비례 Denton 경로
- 하위 셀 반영: 기존 월별 하위 셀 비중은 유지하고, 월별 C00 총량 변화율을 모든 제조업 하위 셀에 동일 적용
- 재집계: 월 셀 적용 후 분기·연, 시·구·행정동/읍면동, 대·중·소분류를 다시 집계

## 산출물

- 고양 후보 행정동×소분류×월: `data/processed/phase196_monthly_manufacturing_index_cubes/phase196_goyang_emd_small_monthly.parquet`
- 고양 후보 다해상도 큐브: `data/processed/phase196_monthly_manufacturing_index_cubes/phase196_goyang_manufacturing_multiresolution_cube.parquet`
- 포항 후보 읍면동×소분류×월: `data/processed/phase196_monthly_manufacturing_index_cubes/phase196_pohang_emd_group_monthly.parquet`
- 포항 후보 다해상도 큐브: `data/processed/phase196_monthly_manufacturing_index_cubes/phase196_pohang_multiresolution_cube.parquet`

## C00 월경로 변화 요약

단위: 억원. 연간 총량 차이가 0에 가까운 것은 연·분기 통제총량을 보존하면서 월별 분포만 바꿨기 때문이다.

{md_table(summaries.rename(columns={
    "city": "지역",
    "year": "연도",
    "months": "월수",
    "old_sum_eok": "기존 연합계",
    "new_sum_eok": "후보 연합계",
    "annual_delta_eok": "연합계 차이",
    "min_scale": "최소 월배율",
    "max_scale": "최대 월배율",
    "mean_abs_month_delta_eok": "평균 월차이",
    "max_abs_month_delta_eok": "최대 월차이",
}), 4)}

## 회계 검증

원 단위 오차와 억원 환산 오차를 함께 기록했다.

{md_table(check_show.rename(columns={
    "city": "지역",
    "check": "검증",
    "cells": "셀수",
    "max_abs_error": "최대오차",
    "mean_abs_error": "평균오차",
    "max_abs_error_eok": "최대오차(억원)",
    "mean_abs_error_eok": "평균오차(억원)",
}), 10)}

## 판정

1. Phase195 월간 제조업 산업생산지수 경로는 고양·포항 하위 공간·산업 큐브에 회계적으로 안전하게 적용 가능하다.
2. 이번 개선은 제조업 C00의 월별 시간 경로 개선이다. 중분류·소분류의 연간 금액오차 자체를 줄이는 증거는 아니다.
3. 따라서 포스터/보고서에는 `제조업 월별 총부가가치 경로는 월간 산업생산지수와 산업용 전력으로 재산정`이라고 쓸 수 있다.
4. 반대로 `제조업 중분류 예측오차가 산업생산지수로 개선됐다`고 쓰면 안 된다. 그 개선은 KICOX·항만·공장·전력 중분류 매핑 등 별도 활동자료 검증 이후에만 주장 가능하다.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
