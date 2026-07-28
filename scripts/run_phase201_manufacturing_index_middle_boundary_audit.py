from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase201_manufacturing_index_middle_boundary_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase201_manufacturing_index_middle_boundary_audit.md"
RUN_ID = "partial_statistics_estimation_phase201_manufacturing_index_middle_boundary_audit"
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
    payload = out.to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp(df).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
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


def actual_middle_shares() -> pd.DataFrame:
    raw = read_csv(DATA / "expanded_manufacturing_sigungu_ksic.csv")
    a = raw[
        raw["metric"].eq("value_added")
        & raw["ksic_level"].eq("middle")
        & raw["c1_nm"].isin(["고양시", "포항시"])
        & raw["c2_id"].astype(str).str.startswith("C")
    ].copy()
    a["actual_value_added"] = pd.to_numeric(a["value"], errors="coerce")
    a = a.dropna(subset=["actual_value_added"])
    a["year"] = a["prd_de"].astype(int)
    a["middle_code"] = a["c2_id"].astype(str)
    a["city"] = a["c1_nm"]
    a["middle_name"] = a["c2_nm"]
    a["actual_share"] = a["actual_value_added"] / a.groupby(["city", "year"])["actual_value_added"].transform("sum")
    return a[["city", "year", "middle_code", "middle_name", "actual_value_added", "actual_share"]]


def goyang_old_estimate() -> pd.DataFrame:
    # Phase39 has annual predicted middle shares and the pre-Phase195/196 monthly path.
    g = read_csv(DATA / "partial_stats_phase39_manufacturing_city_middle_monthly.csv")
    g = g[g["middle_code"].astype(str).str.startswith("C")].copy()
    annual = (
        g.groupby(["year", "middle_code", "middle_name"], as_index=False)["estimated_city_middle_monthly_gva"].sum()
    )
    annual["city"] = "고양시"
    annual["estimate_source"] = "old_quarterly_index_path"
    annual["estimated_share"] = annual["estimated_city_middle_monthly_gva"] / annual.groupby(["city", "year"])[
        "estimated_city_middle_monthly_gva"
    ].transform("sum")
    return annual.rename(columns={"estimated_city_middle_monthly_gva": "estimated_value"})[
        ["city", "year", "middle_code", "middle_name", "estimate_source", "estimated_value", "estimated_share"]
    ]


def goyang_new_estimate() -> pd.DataFrame:
    g = pd.read_parquet(DATA / "phase196_monthly_manufacturing_index_cubes" / "phase196_goyang_manufacturing_multiresolution_cube.parquet")
    g = g[
        g["industry_level"].eq("중분류")
        & g["time_level"].eq("연")
        & g["geo_level"].eq("시")
        & g["industry_code"].astype(str).str.startswith("C")
    ].copy()
    g["city"] = "고양시"
    g["middle_code"] = g["industry_code"].astype(str)
    g["middle_name"] = g["industry_name"].astype(str)
    g["estimate_source"] = "new_monthly_index_path"
    g["estimated_share"] = g["estimated_gva"] / g.groupby(["city", "year"])["estimated_gva"].transform("sum")
    return g.rename(columns={"estimated_gva": "estimated_value"})[
        ["city", "year", "middle_code", "middle_name", "estimate_source", "estimated_value", "estimated_share"]
    ]


def pohang_estimate(path: Path, source: str) -> pd.DataFrame:
    p = pd.read_parquet(path)
    p = p[
        p["industry_level"].eq("중분류")
        & p["time_level"].eq("연")
        & p["geo_level"].eq("시")
        & p["industry_code"].astype(str).str.fullmatch(r"\d{2}")
    ].copy()
    p = p[p["industry_code"].astype(str).astype(int).between(10, 34)].copy()
    p["city"] = "포항시"
    p["middle_code"] = "C" + p["industry_code"].astype(str)
    p["middle_name"] = p["industry_name"].astype(str)
    p["estimate_source"] = source
    p["estimated_share"] = p["estimated_gva"] / p.groupby(["city", "year"])["estimated_gva"].transform("sum")
    return p.rename(columns={"estimated_gva": "estimated_value"})[
        ["city", "year", "middle_code", "middle_name", "estimate_source", "estimated_value", "estimated_share"]
    ]


def score(est: pd.DataFrame, actual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = est.merge(actual, on=["city", "year", "middle_code"], how="inner", suffixes=("_est", "_actual"))
    # Score as share percentage-point error because official manufacturing survey middle totals
    # do not equal the GRDP/GVA control total used by the monthly cube.
    x["share_error_pp"] = (x["estimated_share"] - x["actual_share"]) * 100
    x["abs_share_error_pp"] = x["share_error_pp"].abs()
    x["actual_share_pct"] = x["actual_share"] * 100
    x["estimated_share_pct"] = x["estimated_share"] * 100
    x["actual_value_added_eok"] = x["actual_value_added"] / 100.0
    detail = x[
        [
            "city",
            "year",
            "middle_code",
            "middle_name_actual",
            "estimate_source",
            "actual_value_added_eok",
            "actual_share_pct",
            "estimated_share_pct",
            "share_error_pp",
            "abs_share_error_pp",
        ]
    ].rename(columns={"middle_name_actual": "middle_name"})
    summary = (
        detail.groupby(["city", "year", "estimate_source"], as_index=False)
        .agg(
            cells=("middle_code", "nunique"),
            actual_sum_eok=("actual_value_added_eok", "sum"),
            mae_share_pp=("abs_share_error_pp", "mean"),
            wape_share_pp=("abs_share_error_pp", "sum"),
            gt5pp_cells=("abs_share_error_pp", lambda s: int((s > 5).sum())),
            gt10pp_cells=("abs_share_error_pp", lambda s: int((s > 10).sum())),
            max_abs_share_error_pp=("abs_share_error_pp", "max"),
        )
        .sort_values(["city", "year", "estimate_source"])
    )
    return detail, summary


def main() -> int:
    actual = actual_middle_shares()
    estimates = pd.concat(
        [
            goyang_old_estimate(),
            goyang_new_estimate(),
            pohang_estimate(
                DATA / "phase191_pohang_c00_temporal_candidate_cube" / "phase191_pohang_multiresolution_cube.parquet",
                "old_quarterly_or_uniform_path",
            ),
            pohang_estimate(
                DATA / "phase196_monthly_manufacturing_index_cubes" / "phase196_pohang_multiresolution_cube.parquet",
                "new_monthly_index_path",
            ),
        ],
        ignore_index=True,
    )
    detail, summary = score(estimates, actual)
    diff = (
        detail.pivot_table(
            index=["city", "year", "middle_code", "middle_name"],
            columns="estimate_source",
            values="estimated_share_pct",
            aggfunc="first",
        )
        .reset_index()
    )
    source_cols = [c for c in diff.columns if c not in ["city", "year", "middle_code", "middle_name"]]
    if len(source_cols) >= 2:
        base_cols = [c for c in source_cols if c.startswith("old_")]
        new_cols = [c for c in source_cols if c == "new_monthly_index_path"]
        if base_cols and new_cols:
            old_share = diff[base_cols].bfill(axis=1).iloc[:, 0]
            diff["new_minus_old_estimated_share_pp"] = diff[new_cols[0]] - old_share
    else:
        diff["new_minus_old_estimated_share_pp"] = pd.NA
    shift_summary = (
        diff.groupby(["city", "year"], as_index=False)["new_minus_old_estimated_share_pp"]
        .agg(max_abs_shift_pp=lambda s: s.abs().max(), mean_abs_shift_pp=lambda s: s.abs().mean())
        .sort_values(["city", "year"])
    )

    write_csv("phase201_middle_share_error_detail.csv", detail)
    write_csv("phase201_middle_share_error_summary.csv", summary)
    write_csv("phase201_old_new_middle_share_shift.csv", diff)
    write_csv("phase201_old_new_middle_share_shift_summary.csv", shift_summary)

    bad = (
        detail[detail["estimate_source"].eq("new_monthly_index_path")]
        .sort_values(["city", "year", "abs_share_error_pp"], ascending=[True, True, False])
        .groupby(["city", "year"])
        .head(5)
    )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase201 제조업 산업생산지수 중분류 경계효과 검증

## 목적

Phase195~196에서 월간 제조업 산업생산지수를 제조업 C00 월별 총부가가치 경로에 반영했다. 이번 검증은 그 효과가 KSIC 제조업 중분류 금액 구조까지 개선하는지, 아니면 시간경로 개선에 머무는지를 분리해 확인한다.

## 검증 원칙

KOSIS `시도(시군구)/산업분류별 주요지표(10명 이상)`의 중분류 부가가치 합계는 GRDP 기반 제조업 C00 통제총량과 같지 않다. 따라서 직접 금액을 비교하면 총량 차이가 중분류 오차처럼 섞인다.

이번 검증은 중분류 actual 내부 구성비와 추정 구성비를 비교한다. 단위는 `%p`다.

## 요약

{md_table(summary.rename(columns={
    "city": "지역",
    "year": "연도",
    "estimate_source": "추정경로",
    "cells": "중분류수",
    "actual_sum_eok": "actual 합계(억원)",
    "mae_share_pp": "평균 구성비 오차(%p)",
    "wape_share_pp": "구성비 절대오차 합(%p)",
    "gt5pp_cells": "5%p 초과",
    "gt10pp_cells": "10%p 초과",
    "max_abs_share_error_pp": "최대 구성비 오차(%p)",
}))}

## 월간 산업생산지수 반영 전후 중분류 구성 변화

{md_table(shift_summary.rename(columns={
    "city": "지역",
    "year": "연도",
    "max_abs_shift_pp": "전후 최대 구성비 변화(%p)",
    "mean_abs_shift_pp": "전후 평균 구성비 변화(%p)",
}))}

## 신규 월간 경로 기준 잔여 고오차 중분류

{md_table(bad[[
    "city",
    "year",
    "middle_code",
    "middle_name",
    "actual_value_added_eok",
    "actual_share_pct",
    "estimated_share_pct",
    "abs_share_error_pp",
]].rename(columns={
    "city": "지역",
    "year": "연도",
    "middle_code": "KSIC",
    "middle_name": "업종명",
    "actual_value_added_eok": "actual(억원)",
    "actual_share_pct": "actual 구성비(%)",
    "estimated_share_pct": "추정 구성비(%)",
    "abs_share_error_pp": "구성비 오차(%p)",
}))}

## 판정

월간 제조업 산업생산지수는 제조업 C00의 월별 시간경로를 개선한다. 그러나 중분류별 연간 구성비를 결정하는 정보는 아니다. 고양시는 전후 중분류 구성 변화가 거의 0에 가깝고, 포항도 C00 월별 스케일 조정이 중분류 구조를 크게 바꾸지 않는다.

따라서 중분류·소분류 오차를 줄이려면 산업생산지수를 `제조업 전체 시간축`에 두고, 중분류 구조는 다음 계열의 별도 활동자료로 추정해야 한다.

1. 공장등록 기반 생산품·업종·종업원·면적
2. 업종별 전력 또는 에너지 사용량
3. 포항의 1차 금속·금속가공 계열은 항만 품목 물동량과 대형 공장 활동자료
4. C26 등 일부 업종은 제한적 세부 생산지수

이번 결과는 산업생산지수를 빼자는 뜻이 아니다. 반대로 산업생산지수는 반드시 넣되, 역할을 `월별 총량 경로`로 제한해야 한다는 검증 결과다.
""",
        encoding="utf-8",
    )
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
