from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase189_manufacturing_factory_metric_screen"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase189_manufacturing_factory_metric_screen.md"
RUN_ID = "partial_statistics_estimation_phase189_manufacturing_factory_metric_screen"
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


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    payload = out.to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    out.to_csv(OUT / name, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame, digits: int = 2, limit: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if limit is not None and len(view) > limit:
        view = view.head(limit)
    for c in view.columns:
        if pd.api.types.is_float_dtype(view[c]):
            view[c] = view[c].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
        else:
            view[c] = view[c].map(lambda x: "" if pd.isna(x) else str(x))
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    if limit is not None and len(df) > limit:
        lines.append(f"\n_상위 {limit:,}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def load_actual() -> pd.DataFrame:
    raw = read_csv(DATA / "expanded_manufacturing_sigungu_ksic.csv", dtype=str)
    x = raw[
        raw["c1_nm"].isin(["고양시", "포항시"])
        & raw["c2_id"].astype(str).str.startswith("C", na=False)
        & raw["metric"].eq("value_added")
    ].copy()
    x["year"] = x["prd_de"].astype(int)
    x["middle_code"] = x["c2_id"].astype(str)
    x["middle_name"] = x["c2_nm"].astype(str)
    x["actual_gva_eok"] = pd.to_numeric(x["value"], errors="coerce") / 100
    x = x.dropna(subset=["actual_gva_eok"])
    return x.rename(columns={"c1_nm": "city"})[["city", "year", "middle_code", "middle_name", "actual_gva_eok"]]


def numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce").fillna(0)


def load_factory_metrics() -> pd.DataFrame:
    f = read_csv(RAW / "public_data_portal" / "factory_full_snapshot_15106170_download.csv", dtype=str, low_memory=False)
    f = f[f["시군구명"].astype(str).str.contains("고양시|포항시", na=False)].copy()
    f["city"] = np.where(f["시군구명"].astype(str).str.contains("고양시", na=False), "고양시", "포항시")
    f["middle_code"] = "C" + f["대표업종"].astype(str).str.extract(r"(\d{2})")[0]
    f = f[f["middle_code"].astype(str).str.match(r"C\d{2}", na=False)].copy()
    f["factory_count"] = 1.0
    f["employee_count"] = numeric(f.get("종업원합계", pd.Series(index=f.index)))
    f["manufacturing_area_sqm"] = numeric(f.get("제조시설면적", pd.Series(index=f.index)))
    f["building_area_sqm"] = numeric(f.get("건축면적", pd.Series(index=f.index)))
    f["land_area_sqm"] = numeric(f.get("용지면적", pd.Series(index=f.index)))
    agg = (
        f.groupby(["city", "middle_code"], as_index=False)
        .agg(
            factory_count=("factory_count", "sum"),
            employee_count=("employee_count", "sum"),
            manufacturing_area_sqm=("manufacturing_area_sqm", "sum"),
            building_area_sqm=("building_area_sqm", "sum"),
            land_area_sqm=("land_area_sqm", "sum"),
            products=("생산품", lambda s: "; ".join(sorted(set(str(v) for v in s.dropna().head(5))))),
        )
    )
    agg["sqrt_employee_area"] = np.sqrt(np.maximum(agg["employee_count"], 0) + 1) * np.sqrt(np.maximum(agg["manufacturing_area_sqm"], 0) + 1)
    return agg


def safe_share(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0).clip(lower=0)
    if s.sum() <= 0:
        return pd.Series(np.ones(len(s)) / max(len(s), 1), index=s.index)
    return s / s.sum()


def evaluate(actual: pd.DataFrame, factory: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics = [
        "factory_count",
        "employee_count",
        "manufacturing_area_sqm",
        "building_area_sqm",
        "land_area_sqm",
        "sqrt_employee_area",
    ]
    alphas = [0.0, 0.25, 0.5, 0.75, 1.0]
    rows = []
    detail_rows = []
    for city in ["고양시", "포항시"]:
        fa = factory[factory["city"].eq(city)].set_index("middle_code")
        for target_year in [2023, 2024]:
            prev_year = target_year - 1
            prev = actual[(actual["city"].eq(city)) & (actual["year"].eq(prev_year))].set_index("middle_code")
            tgt = actual[(actual["city"].eq(city)) & (actual["year"].eq(target_year))].set_index("middle_code")
            common = sorted(set(prev.index) & set(tgt.index))
            if not common:
                continue
            prev = prev.loc[common]
            tgt = tgt.loc[common]
            total = float(tgt["actual_gva_eok"].sum())
            prev_share = safe_share(prev["actual_gva_eok"])
            for metric in metrics:
                activity = fa.reindex(common)[metric] if metric in fa else pd.Series(0, index=common)
                activity_share = safe_share(activity)
                for alpha in alphas:
                    share = alpha * prev_share + (1 - alpha) * activity_share
                    share = safe_share(share)
                    pred = share * total
                    err = (pred - tgt["actual_gva_eok"]).abs()
                    rate = err / tgt["actual_gva_eok"].replace(0, np.nan) * 100
                    rows.append(
                        {
                            "city": city,
                            "target_year": target_year,
                            "metric": metric,
                            "alpha_prev_gva": alpha,
                            "cells": len(common),
                            "actual_sum_eok": total,
                            "error_sum_eok": float(err.sum()),
                            "wape_pct": float(err.sum() / total * 100),
                            "gt10_cells": int((rate > 10).sum()),
                            "gt20_cells": int((rate > 20).sum()),
                            "gt50_cells": int((rate > 50).sum()),
                        }
                    )
                    for code in common:
                        detail_rows.append(
                            {
                                "city": city,
                                "target_year": target_year,
                                "metric": metric,
                                "alpha_prev_gva": alpha,
                                "middle_code": code,
                                "middle_name": tgt.loc[code, "middle_name"],
                                "actual_gva_eok": float(tgt.loc[code, "actual_gva_eok"]),
                                "predicted_gva_eok": float(pred.loc[code]),
                                "error_gva_eok": float(err.loc[code]),
                                "error_rate_pct": float(rate.loc[code]) if pd.notna(rate.loc[code]) else np.nan,
                                "activity_value": float(activity.reindex(common).fillna(0).loc[code]),
                            }
                        )
    screen = pd.DataFrame(rows)
    detail = pd.DataFrame(detail_rows)

    selected = []
    for city in ["고양시", "포항시"]:
        train = screen[(screen["city"].eq(city)) & (screen["target_year"].eq(2023))].sort_values(["wape_pct", "gt20_cells", "gt10_cells"])
        if train.empty:
            continue
        best = train.iloc[0]
        test = screen[
            screen["city"].eq(city)
            & screen["target_year"].eq(2024)
            & screen["metric"].eq(best["metric"])
            & screen["alpha_prev_gva"].eq(best["alpha_prev_gva"])
        ]
        baseline = screen[
            screen["city"].eq(city)
            & screen["target_year"].eq(2024)
            & screen["metric"].eq("factory_count")
            & screen["alpha_prev_gva"].eq(1.0)
        ]
        if len(test):
            selected.append(
                {
                    "city": city,
                    "selection_basis": "2023 holdout에서 최소 WAPE 후보 선택 후 2024 평가",
                    "selected_metric": best["metric"],
                    "selected_alpha_prev_gva": float(best["alpha_prev_gva"]),
                    "train_2023_wape_pct": float(best["wape_pct"]),
                    "test_2024_wape_pct": float(test.iloc[0]["wape_pct"]),
                    "baseline_2024_prev_share_wape_pct": float(baseline.iloc[0]["wape_pct"]) if len(baseline) else np.nan,
                    "test_delta_vs_baseline_pp": float(test.iloc[0]["wape_pct"] - baseline.iloc[0]["wape_pct"]) if len(baseline) else np.nan,
                    "test_gt20_cells": int(test.iloc[0]["gt20_cells"]),
                    "baseline_gt20_cells": int(baseline.iloc[0]["gt20_cells"]) if len(baseline) else np.nan,
                    "adoption_judgement": "adopt_if_no_worse_and_material" if len(baseline) and test.iloc[0]["wape_pct"] < baseline.iloc[0]["wape_pct"] else "reject_or_diagnostic_only",
                }
            )
    return screen, detail, pd.DataFrame(selected)


def write_report(screen: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame) -> None:
    best_by_city_year = screen.sort_values(["city", "target_year", "wape_pct"]).groupby(["city", "target_year"], as_index=False).head(3)
    test_details = []
    for _, r in selected.iterrows():
        z = detail[
            detail["city"].eq(r["city"])
            & detail["target_year"].eq(2024)
            & detail["metric"].eq(r["selected_metric"])
            & detail["alpha_prev_gva"].eq(r["selected_alpha_prev_gva"])
        ].copy()
        z = z.sort_values("error_gva_eok", ascending=False).head(8)
        test_details.append(z)
    test_detail = pd.concat(test_details, ignore_index=True) if test_details else pd.DataFrame()
    text = f"""# Phase189 제조업 공장등록 활동자료 스크리닝

## 목적

Phase188에서 시도 제조업 산업생산지수는 제조업 전체 시간배분에는 유효하지만, KSIC 중분류 구조오차를 줄이는 독립 정보가 아니라는 점을 확인했다. Phase189는 무료 로컬 자료인 전국 공장등록 스냅샷에서 공장 수·종업원·제조시설면적·건축면적·용지면적을 중분류별 활동자료로 만들어, 전년 중분류 구조와 혼합했을 때 정밀오차가 줄어드는지 검증한다.

## 검증 설계

- 예측대상: 고양시·포항시 KSIC 제조업 중분류 총부가가치.
- 후보식: `alpha × 전년 중분류 GVA 구조 + (1-alpha) × 공장등록 활동자료 구조`.
- alpha 후보: 0, 0.25, 0.5, 0.75, 1.
- 선택 방식: 2022→2023 holdout에서 후보를 고르고, 같은 후보를 2023→2024에 적용한다.
- 제한: 공장등록은 현재 스냅샷이므로 **속보성 지표가 아니라 정밀화 후보**다.

## 도시별 2024 외부연도 평가

{md_table(selected.rename(columns={
    "city": "지역",
    "selection_basis": "선택방식",
    "selected_metric": "선택 활동자료",
    "selected_alpha_prev_gva": "전년구조 비중",
    "train_2023_wape_pct": "2023 선택 WAPE(%)",
    "test_2024_wape_pct": "2024 평가 WAPE(%)",
    "baseline_2024_prev_share_wape_pct": "2024 전년구조 WAPE(%)",
    "test_delta_vs_baseline_pp": "WAPE 증감(pp)",
    "test_gt20_cells": "후보 20%초과",
    "baseline_gt20_cells": "기준 20%초과",
    "adoption_judgement": "판정",
}), 2)}

## 도시·연도별 상위 후보

{md_table(best_by_city_year[["city","target_year","metric","alpha_prev_gva","wape_pct","gt10_cells","gt20_cells","gt50_cells"]].rename(columns={
    "city": "지역",
    "target_year": "연도",
    "metric": "활동자료",
    "alpha_prev_gva": "전년구조 비중",
    "wape_pct": "WAPE(%)",
    "gt10_cells": "10%초과",
    "gt20_cells": "20%초과",
    "gt50_cells": "50%초과",
}), 2, 24)}

## 2024 선택후보 오차 상위 셀

{md_table(test_detail[["city","middle_code","middle_name","actual_gva_eok","predicted_gva_eok","error_gva_eok","error_rate_pct","activity_value"]].rename(columns={
    "city": "지역",
    "middle_code": "코드",
    "middle_name": "중분류",
    "actual_gva_eok": "실제(억원)",
    "predicted_gva_eok": "추정(억원)",
    "error_gva_eok": "오차(억원)",
    "error_rate_pct": "오차율(%)",
    "activity_value": "활동자료값",
}), 2, 20)}

## 판정

1. 공장등록 활동자료는 업종별 보정 후보로 유용하지만, 모든 도시·연도에 자동 채택할 정도로 안정적이지는 않다.
2. 고양/포항 모두 선택후보가 2024에서 전년구조 기준선을 이기지 못하면 운영값에는 넣지 않는다. 이 경우 공장등록은 포스터의 성능개선 숫자가 아니라 제조업 공간배분·진단 근거로 둔다.
3. 중분류 금액오차를 줄이려면 공장등록 전체 지표보다 업종별 라우팅이 필요하다.
   - 전기장비·1차금속·금속가공: 전력·공장면적·항만/철강 물동량 결합.
   - 식료품·섬유·인쇄·의료정밀: 생산품 텍스트와 종업원/면적의 세부 매핑.
   - 산업용 기계 수리업: 공장 생산보다 정비계약·대형설비 사업장 활동자료.
"""
    REPORT.write_text(text, encoding="utf-8")


def main() -> None:
    actual = load_actual()
    factory = load_factory_metrics()
    screen, detail, selected = evaluate(actual, factory)
    write_csv("phase189_factory_middle_metrics.csv", factory)
    write_csv("phase189_factory_metric_screen.csv", screen)
    write_csv("phase189_factory_metric_detail.csv", detail)
    write_csv("phase189_factory_metric_selected_2024_eval.csv", selected)
    write_report(screen, selected, detail)
    print(REPORT)


if __name__ == "__main__":
    main()
