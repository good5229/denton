#!/usr/bin/env python3
"""Audit mining/manufacturing split feasibility and annual >10% errors."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "nationwide" / "mining_manufacturing_split_and_10pct_error_audit.md"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
TRACK = "recursive_no_target_actual"


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def annual_sido_activity_errors() -> pd.DataFrame:
    q = pd.read_csv(OUT / "sido_activity_quarterly_validation.csv")
    q = q[q["track"].eq(TRACK)].copy()
    annual = (
        q.groupby(["track", "quarter_region", "year", "activity"], as_index=False)
        .agg(predicted_eok=("predicted_value_eok", "sum"), actual_eok=("official_value_eok", "sum"))
    )
    annual["abs_error_eok"] = (annual["predicted_eok"] - annual["actual_eok"]).abs()
    annual["ape_pct"] = annual["abs_error_eok"] / annual["actual_eok"].abs() * 100
    return annual


def annual_sigungu_errors() -> tuple[pd.DataFrame, pd.DataFrame]:
    pred = pd.read_csv(OUT / "sigungu_industry_quarterly_predictions.csv")
    pred = pred[pred["track"].eq(TRACK)].copy()
    pred_ann = (
        pred.groupby(["quarter_region", "province_full", "city", "activity_group", "year"], as_index=False)
        .agg(predicted_eok=("predicted_gva_eok", "sum"))
        .rename(columns={"activity_group": "activity"})
    )
    actual = pd.read_csv(OUT / "annual_sigungu_gva_normalized.csv").rename(
        columns={"activity_group": "activity", "annual_gva_eok": "actual_eok"}
    )
    actual = actual[["quarter_region", "province_full", "city", "activity", "year", "actual_eok", "table_id", "table_name", "latest_change_date"]]
    act = pred_ann.merge(
        actual,
        on=["quarter_region", "province_full", "city", "activity", "year"],
        how="inner",
    )
    act["abs_error_eok"] = (act["predicted_eok"] - act["actual_eok"]).abs()
    act["ape_pct"] = act["abs_error_eok"] / act["actual_eok"].abs() * 100

    total_pred = pred_ann.groupby(["quarter_region", "province_full", "city", "year"], as_index=False)["predicted_eok"].sum()
    total_actual = actual.groupby(["quarter_region", "province_full", "city", "year"], as_index=False)["actual_eok"].sum()
    total = total_pred.merge(total_actual, on=["quarter_region", "province_full", "city", "year"], how="inner")
    total["abs_error_eok"] = (total["predicted_eok"] - total["actual_eok"]).abs()
    total["ape_pct"] = total["abs_error_eok"] / total["actual_eok"].abs() * 100
    return total, act


def mining_source_summary() -> pd.DataFrame:
    rows = []
    candidates = [
        ("광업 생산지수", ROOT / "data/processed/mining_production_index.csv"),
        ("제조업 생산지수", ROOT / "data/processed/phase195_monthly_mining_manufacturing_production_index.csv"),
        ("제조업 세부 생산지수", ROOT / "data/processed/phase195_monthly_detail_manufacturing_production_index.csv"),
    ]
    for name, path in candidates:
        if not path.exists():
            rows.append({"자료": name, "파일": str(path.relative_to(ROOT)), "행수": 0, "지역수": 0, "산업": "미확보", "기간": "-"})
            continue
        df = read_csv_any(path)
        region_col = "c1_nm" if "c1_nm" in df.columns else None
        industry_col = "c2_nm" if "c2_nm" in df.columns else ("c1_nm" if "c1_nm" in df.columns else None)
        period_col = "prd_de" if "prd_de" in df.columns else None
        regions = sorted(df[region_col].dropna().astype(str).unique().tolist()) if region_col else []
        industries = sorted(df[industry_col].dropna().astype(str).unique().tolist()) if industry_col else []
        periods = df[period_col].dropna().astype(str) if period_col else pd.Series(dtype=str)
        rows.append(
            {
                "자료": name,
                "파일": str(path.relative_to(ROOT)),
                "행수": len(df),
                "지역수": len(regions),
                "산업": ", ".join(industries[:8]),
                "기간": f"{periods.min()}~{periods.max()}" if not periods.empty else "-",
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    sido = annual_sido_activity_errors()
    sigungu_total, sigungu_activity = annual_sigungu_errors()

    sido_over10 = sido[sido["ape_pct"].gt(10)].sort_values(["ape_pct"], ascending=False)
    sigungu_total_over10 = sigungu_total[sigungu_total["ape_pct"].gt(10)].sort_values(["ape_pct"], ascending=False)
    sigungu_activity_over10 = sigungu_activity[sigungu_activity["ape_pct"].gt(10)].sort_values(["ape_pct"], ascending=False)

    sido.to_csv(OUT / "annual_sido_activity_error_audit.csv", index=False, encoding="utf-8-sig")
    sido_over10.to_csv(OUT / "annual_sido_activity_over_10pct_errors.csv", index=False, encoding="utf-8-sig")
    sigungu_total.to_csv(OUT / "annual_sigungu_total_error_audit.csv", index=False, encoding="utf-8-sig")
    sigungu_activity.to_csv(OUT / "annual_sigungu_activity_error_audit.csv", index=False, encoding="utf-8-sig")
    sigungu_total_over10.to_csv(OUT / "annual_sigungu_total_over_10pct_errors.csv", index=False, encoding="utf-8-sig")
    sigungu_activity_over10.to_csv(OUT / "annual_sigungu_activity_over_10pct_errors.csv", index=False, encoding="utf-8-sig")

    source_summary = mining_source_summary()
    source_summary.to_csv(OUT / "mining_manufacturing_split_source_summary.csv", index=False, encoding="utf-8-sig")

    seoul_2025 = sido[
        sido["quarter_region"].eq("서울")
        & sido["year"].eq(2025)
        & sido["activity"].eq("광업, 제조업")
    ].copy()

    by_activity = (
        sido_over10.groupby("activity", as_index=False)
        .agg(rows=("ape_pct", "count"), max_ape_pct=("ape_pct", "max"), abs_error_sum_eok=("abs_error_eok", "sum"))
        .sort_values(["rows", "max_ape_pct"], ascending=[False, False])
    )
    sigungu_by_activity = (
        sigungu_activity_over10.groupby("activity", as_index=False)
        .agg(rows=("ape_pct", "count"), max_ape_pct=("ape_pct", "max"), abs_error_sum_eok=("abs_error_eok", "sum"))
        .sort_values(["rows", "max_ape_pct"], ascending=[False, False])
    )
    sigungu_large = sigungu_activity[sigungu_activity["actual_eok"].abs().ge(1000)].copy()
    sigungu_large_over10 = sigungu_large[sigungu_large["ape_pct"].gt(10)].copy()
    sigungu_large_by_activity = (
        sigungu_large_over10.groupby("activity", as_index=False)
        .agg(rows=("ape_pct", "count"), max_ape_pct=("ape_pct", "max"), abs_error_sum_eok=("abs_error_eok", "sum"))
        .sort_values(["rows", "max_ape_pct"], ascending=[False, False])
    )
    sigungu_large_over10.to_csv(OUT / "annual_sigungu_activity_over_10pct_errors_actual_ge_1000eok.csv", index=False, encoding="utf-8-sig")

    report = f"""# 광업·제조업 분리 가능성 및 10% 초과 연간오차 감사

생성시각: {CREATED_AT}

## 1. 광업·제조업 분리 가능성

현재 전국 분기 actual 검증 경계인 통계청 실험적 분기 GRDP XLSX와 KOSIS 시군구 연간 GVA 원천은 `광업, 제조업`을 결합 항목으로 제공한다. 따라서 공개 actual만으로는 광업과 제조업 각각의 분기 GVA 오차를 직접 검증할 수 없다.

다만 시간배분 지표로는 KOSIS `광업제조업동향조사`의 `시도/산업별 광공업생산지수(2020=100)`를 사용할 수 있다. 로컬 수집 상태는 다음과 같다.

{md_table(source_summary.rename(columns={"자료": "자료", "파일": "로컬파일", "행수": "행수", "지역수": "지역수", "산업": "산업", "기간": "기간"}), 3)}

### 판단

- Reference의 BOK 이슈노트(2023-9호)는 RECI 총부가가치 작성 과정에서 제조업·서비스업 생산지수만으로는 전산업 포괄성이 부족하므로 건설업, 전기가스수도, 농림어업, 광업 등을 포함하는 방식으로 처리한다. 또한 산업 대응표에도 `광업`이 제조업과 별도 항목으로 제시된다.
- 광업 생산지수는 별도 파일로 확보되어 있어 광업이 실제로 존재하는 시도에서는 `광업` 시간경로를 제조업과 분리할 수 있다.
- 제조업 생산지수는 모든 시도에 가까운 범위로 확보되어 있어 제조업 시간경로 분리에 바로 사용할 수 있다.
- 서울은 로컬 광업 생산지수 지역 목록에 없고, 공개 actual도 `광업, 제조업` 결합이다. 따라서 서울 2025년 `광업, 제조업` 오차는 실질적으로 제조업 오차로 해석하는 편이 타당하다.
- 최종 모델에서는 `B 광업`과 `C 제조업`을 내부적으로 분리하되, 검증은 다시 `B+C`로 합산해 공식 actual과 비교해야 한다.

## 2. 서울 2025년 광업·제조업 오차

{md_table(seoul_2025[["quarter_region", "year", "activity", "predicted_eok", "actual_eok", "abs_error_eok", "ape_pct"]].rename(columns={
    "quarter_region": "지역",
    "year": "연도",
    "activity": "업종",
    "predicted_eok": "추정_억원",
    "actual_eok": "실제_억원",
    "abs_error_eok": "절대오차_억원",
    "ape_pct": "오차율_pct",
}), 3)}

## 3. 시도×업종 연간오차 10% 초과 집계

| 항목 | 값 |
| --- | ---: |
| 전체 검증행 | {len(sido):,} |
| 10% 초과 행 | {len(sido_over10):,} |
| 10% 초과 업종 수 | {sido_over10["activity"].nunique():,} |
| 10% 초과 시도 수 | {sido_over10["quarter_region"].nunique():,} |

{md_table(by_activity.rename(columns={
    "activity": "업종",
    "rows": "10pct초과_행수",
    "max_ape_pct": "최대오차율_pct",
    "abs_error_sum_eok": "절대오차합_억원",
}), 3)}

## 4. 시군구 연간오차 10% 초과 집계

| 항목 | 전체행 | 10% 초과행 |
| --- | ---: | ---: |
| 시군구 total GVA | {len(sigungu_total):,} | {len(sigungu_total_over10):,} |
| 시군구×업종 GVA | {len(sigungu_activity):,} | {len(sigungu_activity_over10):,} |

### 시군구×업종 10% 초과 상위 업종

{md_table(sigungu_by_activity.head(15).rename(columns={
    "activity": "업종",
    "rows": "10pct초과_행수",
    "max_ape_pct": "최대오차율_pct",
    "abs_error_sum_eok": "절대오차합_억원",
}), 3)}

### 시군구×업종 10% 초과 상위 업종: 실제값 1,000억원 이상 셀만

소액 업종 셀에서는 작은 금액 차이도 수백~수천 %로 확대될 수 있다. 정책·예산 판단에는 금액 영향이 있는 셀을 별도 필터링해야 한다.

| 항목 | 값 |
| --- | ---: |
| 실제값 1,000억원 이상 시군구×업종 행 | {len(sigungu_large):,} |
| 그중 10% 초과 행 | {len(sigungu_large_over10):,} |

{md_table(sigungu_large_by_activity.head(15).rename(columns={
    "activity": "업종",
    "rows": "10pct초과_행수",
    "max_ape_pct": "최대오차율_pct",
    "abs_error_sum_eok": "절대오차합_억원",
}), 3)}

## 5. 개선 방향

1. `광업, 제조업` 결합 항목은 내부적으로 `광업`과 `제조업`을 분리해 시간경로를 만든 뒤, 검증 시 `광업+제조업`으로 다시 합산한다.
2. 광업은 생산지수가 없는 시도에서는 광업 비중을 0 또는 직전연도 구조비중으로 제한한다. 서울처럼 광업 지표가 없는 지역은 제조업 단독으로 처리한다.
3. 제조업은 시도별 제조업 생산지수를 기본으로 쓰되, 중분류별 생산지수·출하지수·재고지수·가동률이 있는 경우 중분류 묶음에 우선 적용한다.
4. 10% 초과가 반복되는 운수·창고, 건설, 숙박·음식, 정보통신은 단일 공통 계절비중 대신 항만물동량, 건설기성/수주, 관광·숙박 인허가, 콘텐츠·통신 직접 활동자료를 따로 붙여야 한다.
5. 성능 개선이 안 되는 경우의 원인은 대체로 세 가지다. 첫째, 공개 actual이 상위 결합항목이라 분리 오차를 직접 볼 수 없다. 둘째, 시군구 단위 직접 활동자료가 부족하다. 셋째, 특정 대형 사업장·항만·건설 프로젝트 충격이 공통 계절비중에 잡히지 않는다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(source_summary.to_string(index=False))
    print("sido over10", len(sido_over10), "sigungu total over10", len(sigungu_total_over10), "sigungu activity over10", len(sigungu_activity_over10))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
