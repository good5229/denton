#!/usr/bin/env python3
"""Build and audit nationwide sigungu monthly GVA estimates from quarterly predictions.

The monthly layer is a *quarter-constrained bridge*: it never changes the
already validated sigungu-by-industry quarterly estimate.  It only distributes
each quarter to three months using available monthly activity indicators.

This makes two claims explicit:

1. Monthly values are available as operational estimates for 2021~2025.
2. Monthly estimates are internally validated by exact re-aggregation to the
   previously validated quarterly predictions.  They are not treated as direct
   monthly actual accuracy, because no official monthly sigungu GVA actual
   exists.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
QUARTERLY = OUT / "sigungu_industry_quarterly_predictions.csv"
REPORT = HERE / "nationwide_monthly_bridge_validation.md"

INDEX_PATHS = {
    "manufacturing": ROOT / "data" / "processed" / "phase195_monthly_mining_manufacturing_production_index.csv",
    "mining": ROOT / "data" / "processed" / "phase195_monthly_mining_manufacturing_production_index.csv",
    # 전국 산업별 서비스업생산지수: prd_se=M, prd_de=YYYYMM, 2020=100.
    # It has no regional dimension, so it is used only as an intra-quarter
    # temporal path, never as a spatial allocation signal.
    "service_national_monthly": ROOT
    / "data"
    / "processed"
    / "phase208_monthly_indicator_collection"
    / "phase208_DT_1KC2020_산업별_서비스업생산지수_2020_100.0.csv",
    # Older rolling service snapshot kept for audit context. It is quarterly,
    # so the monthly bridge intentionally does not use it.
    "service_quarterly_legacy": ROOT / "data" / "processed" / "rolling_service_production_index.csv",
    "all_industry_national_monthly": ROOT
    / "data"
    / "processed"
    / "phase208_monthly_indicator_collection"
    / "phase208_DT_1JH20201_전산업생산지수_원지수.csv",
    "electricity_gas": ROOT / "data" / "processed" / "rolling_electricity_gas_production_index.csv",
}

SERVICE_ACTIVITY_MAP = {
    "도매 및 소매업": {"도매 및 소매업"},
    "운수 및 창고업": {"운수 및 창고업"},
    "숙박 및 음식점업": {"숙박 및 음식점업"},
    "정보통신업": {"정보통신업"},
    "금융 및 보험업": {"금융 및 보험업"},
    "부동산업": {"부동산업"},
    "사업서비스업": {"전문 과학 및 기술 서비스업", "사업시설 관리 사업지원 및 임대 서비스업"},
    "교육 서비스업": {"교육 서비스업"},
    "보건 및 사회복지업": {"보건업 및 사회복지 서비스업"},
    "문화 및 기타서비스업": {
        "예술 스포츠 및 여가 관련 서비스업",
        "협회 및 단체 수리  및 기타 개인 서비스업",
    },
}

PROVINCE_SHORT = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기도",
    "강원특별자치도": "강원",
    "강원도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라북도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}


def read_csv_any(path: Path, **kwargs) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False, **kwargs)
        except UnicodeDecodeError as exc:
            last = exc
            continue
    if last:
        raise last
    return pd.read_csv(path, **kwargs)


def norm(s: object) -> str:
    return re.sub(r"\s+", "", str(s or "")).replace("·", "").replace(",", "")


def short_region(s: object) -> str:
    text = str(s or "").strip()
    return PROVINCE_SHORT.get(text, text)


def quarter_of_month(period: int | str) -> int:
    m = int(str(period)[4:6])
    return (m - 1) // 3 + 1


def load_index(path: Path) -> pd.DataFrame:
    d = read_csv_any(path)
    if "prd_se" in d.columns:
        d = d[d["prd_se"].astype(str).str.upper().eq("M")].copy()
    d["period"] = d["prd_de"].astype(str).str.extract(r"(\d{6})")[0]
    d = d[d["period"].notna()].copy()
    d["year"] = d["period"].str[:4].astype(int)
    d["month"] = d["period"].str[4:6].astype(int)
    d["quarter"] = d["month"].map(lambda m: (m - 1) // 3 + 1)
    d["quarter_period"] = d["year"].astype(str) + "Q" + d["quarter"].astype(str)
    d["region_short"] = d["c1_nm"].map(short_region)
    d["indicator_value"] = pd.to_numeric(d["value"], errors="coerce")
    d["activity_raw"] = d["c2_nm"].astype(str).str.strip()
    return d[d["indicator_value"].notna()].copy()


def load_national_service_index(path: Path) -> pd.DataFrame:
    d = read_csv_any(path)
    if "prd_se" in d.columns:
        d = d[d["prd_se"].astype(str).str.upper().eq("M")].copy()
    d["period"] = d["prd_de"].astype(str).str.extract(r"(\d{6})")[0]
    d = d[d["period"].notna()].copy()
    d["year"] = d["period"].str[:4].astype(int)
    d["month"] = d["period"].str[4:6].astype(int)
    d = d[d["month"].between(1, 12)].copy()
    d["quarter"] = d["month"].map(lambda m: (m - 1) // 3 + 1)
    d["indicator_value"] = pd.to_numeric(d["value"], errors="coerce")
    d["activity_raw"] = d["c1_nm"].astype(str).str.strip()
    return d[d["indicator_value"].notna()].copy()


def equal_month_rows(q: pd.DataFrame) -> pd.DataFrame:
    months = []
    for qq in [1, 2, 3, 4]:
        months.extend([(qq, (qq - 1) * 3 + 1), (qq, (qq - 1) * 3 + 2), (qq, (qq - 1) * 3 + 3)])
    m = pd.DataFrame(months, columns=["quarter", "month"])
    out = q.merge(m, on="quarter", how="left")
    out["month_share"] = 1.0 / 3.0
    out["monthly_indicator_source"] = "equal_split_no_monthly_indicator"
    out["monthly_indicator_coverage"] = "fallback_equal_split"
    return out


def build_monthly_weights(q: pd.DataFrame) -> pd.DataFrame:
    all_weights: list[pd.DataFrame] = []

    # 광업·제조업: 시도별 제조업 생산지수로 월중 분기 비중을 만든다.
    manuf = load_index(INDEX_PATHS["manufacturing"])
    manuf = manuf[manuf["activity_raw"].map(norm).eq(norm("제조업"))].copy()
    manuf["activity_group"] = "광업, 제조업"
    all_weights.append(
        manuf[["region_short", "activity_group", "year", "quarter", "month", "period", "indicator_value"]]
        .assign(monthly_indicator_source="시도별 제조업 생산지수")
    )

    # 서비스 세부업종: 전국 산업별 월 지수만 사용한다. 지역 정보가 없는
    # 자료이므로 공간배분에는 쓰지 않고, 같은 업종·분기의 시군구 추정값을
    # 3개월로 나누는 시간경로로만 사용한다.
    service = load_national_service_index(INDEX_PATHS["service_national_monthly"])
    frames = []
    service_norm = service["activity_raw"].map(norm)
    for activity, raw_names in SERVICE_ACTIVITY_MAP.items():
        mask = service_norm.isin({norm(x) for x in raw_names})
        tmp = service[mask].copy()
        if tmp.empty:
            continue
        tmp["activity_group"] = activity
        frames.append(tmp)
    if frames:
        svc = pd.concat(frames, ignore_index=True)
        # Composite activities such as 사업서비스업 and 문화/기타 are averaged
        # within month after selecting their public subindices.
        svc = (
            svc.groupby(["activity_group", "year", "quarter", "month", "period"], as_index=False)
            .agg(indicator_value=("indicator_value", "mean"))
            .assign(monthly_indicator_source="전국 산업별 서비스업생산지수")
        )
        regions = q[["region_short"]].drop_duplicates()
        svc = regions.merge(svc, how="cross")
        all_weights.append(svc)

    # 건설업·공공행정: 전국 전산업생산지수 월별 원지수 항목을 사용한다.
    # 지역 차원이 없으므로 서비스업과 마찬가지로 분기 내 시간경로만
    # 빌리고, 시도/시군구 공간배분에는 관여하지 않는다.
    broad = load_national_service_index(INDEX_PATHS["all_industry_national_monthly"])
    broad_map = {
        "건설업": {"건설업"},
        "공공 행정, 국방·사회보장": {"공공행정"},
    }
    broad_frames = []
    broad_norm = broad["activity_raw"].map(norm)
    for activity, raw_names in broad_map.items():
        mask = broad_norm.isin({norm(x) for x in raw_names})
        tmp = broad[mask].copy()
        if tmp.empty:
            continue
        tmp["activity_group"] = activity
        broad_frames.append(tmp)
    if broad_frames:
        b = pd.concat(broad_frames, ignore_index=True)
        b = (
            b.groupby(["activity_group", "year", "quarter", "month", "period"], as_index=False)
            .agg(indicator_value=("indicator_value", "mean"))
            .assign(monthly_indicator_source="전국 전산업생산지수 원지수")
        )
        b = q[["region_short"]].drop_duplicates().merge(b, how="cross")
        all_weights.append(b)

    if not all_weights:
        return pd.DataFrame()

    w = pd.concat(all_weights, ignore_index=True)
    w = w[w["year"].between(2021, 2025)].copy()
    w["indicator_value"] = w["indicator_value"].clip(lower=0)
    w["months_in_quarter"] = w.groupby(["region_short", "activity_group", "year", "quarter"])["month"].transform("nunique")
    w = w[w["months_in_quarter"].eq(3)].copy()
    w["quarter_indicator_sum"] = w.groupby(["region_short", "activity_group", "year", "quarter"])["indicator_value"].transform("sum")
    w["month_share"] = w["indicator_value"] / w["quarter_indicator_sum"]
    w = w[w["month_share"].notna() & w["month_share"].gt(0)].copy()
    return w[
        [
            "region_short",
            "activity_group",
            "year",
            "quarter",
            "month",
            "period",
            "month_share",
            "monthly_indicator_source",
        ]
    ].copy()


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "_해당 없음_"
    v = df.copy()
    for c in v.columns:
        if str(c).lower() in {"year", "years_min", "years_max", "year_min", "year_max", "tracks", "activity_count"}:
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else str(int(round(float(x)))))
        elif pd.api.types.is_float_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(v[c]):
            v[c] = v[c].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            v[c] = v[c].fillna("").astype(str)
    lines = ["| " + " | ".join(v.columns) + " |", "| " + " | ".join(["---"] * len(v.columns)) + " |"]
    for _, r in v.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in v.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    q = read_csv_any(QUARTERLY)
    q = q[q["year"].between(2021, 2025)].copy()
    q["region_short"] = q["quarter_region"].map(short_region)
    q["quarter"] = q["quarter"].astype(int)
    q["year"] = q["year"].astype(int)

    weights = build_monthly_weights(q)
    key = ["region_short", "activity_group", "year", "quarter"]
    if weights.empty:
        monthly = equal_month_rows(q)
    else:
        with_w = q.merge(weights, on=[*key], how="left", suffixes=("", "_indicator"))
        # Split matched and unmatched quarter rows separately. A monthly
        # indicator is used only if all three months of the quarter are present.
        matched = with_w[with_w["month_share"].notna()].copy()
        matched["monthly_indicator_coverage"] = "monthly_indicator"
        unmatched_keys = (
            with_w[with_w["month_share"].isna()][["track", "quarter_region", "province_full", "year", "quarter", "period", "city", "activity_group"]]
            .drop_duplicates()
        )
        unmatched = q.merge(
            unmatched_keys,
            on=["track", "quarter_region", "province_full", "year", "quarter", "period", "city", "activity_group"],
            how="inner",
        )
        if not unmatched.empty:
            unmatched = equal_month_rows(unmatched)
            unmatched["period"] = unmatched["year"].astype(str) + unmatched["month"].astype(int).astype(str).str.zfill(2)
        monthly = pd.concat([matched, unmatched], ignore_index=True, sort=False)

    monthly["month"] = monthly["month"].astype(int)
    monthly["month_period"] = monthly["year"].astype(str) + monthly["month"].astype(str).str.zfill(2)
    monthly["estimated_monthly_gva_eok"] = monthly["predicted_gva_eok"] * monthly["month_share"]
    monthly = monthly[
        [
            "track",
            "quarter_region",
            "province_full",
            "region_short",
            "year",
            "quarter",
            "month",
            "month_period",
            "city",
            "activity_group",
            "estimated_monthly_gva_eok",
            "predicted_gva_eok",
            "month_share",
            "monthly_indicator_source",
            "monthly_indicator_coverage",
            "basis_source",
        ]
    ].copy()

    monthly.to_csv(OUT / "sigungu_industry_monthly_predictions.csv", index=False, encoding="utf-8-sig")

    # Exact aggregation audit: monthly sums must equal the source quarterly row.
    q_key = ["track", "quarter_region", "province_full", "year", "quarter", "city", "activity_group"]
    m_q = (
        monthly.groupby(q_key, as_index=False)
        .agg(monthly_sum_eok=("estimated_monthly_gva_eok", "sum"), months=("month", "nunique"))
    )
    q0 = q[q_key + ["predicted_gva_eok"]].drop_duplicates()
    audit = m_q.merge(q0, on=q_key, how="left")
    audit["reaggregation_error_eok"] = audit["monthly_sum_eok"] - audit["predicted_gva_eok"]
    audit["abs_reaggregation_error_eok"] = audit["reaggregation_error_eok"].abs()
    audit.to_csv(OUT / "monthly_bridge_quarter_reaggregation_audit.csv", index=False, encoding="utf-8-sig")

    share_audit = (
        monthly.groupby(q_key, as_index=False)
        .agg(
            months=("month", "nunique"),
            month_share_sum=("month_share", "sum"),
            negative_month_values=("estimated_monthly_gva_eok", lambda s: int((s < 0).sum())),
        )
    )
    share_audit["abs_share_sum_error"] = (share_audit["month_share_sum"] - 1.0).abs()
    share_audit.to_csv(OUT / "monthly_bridge_share_integrity_audit.csv", index=False, encoding="utf-8-sig")

    coverage = (
        monthly.groupby(["track", "activity_group", "monthly_indicator_coverage", "monthly_indicator_source"], as_index=False)
        .agg(
            rows=("estimated_monthly_gva_eok", "size"),
            estimated_sum_eok=("estimated_monthly_gva_eok", "sum"),
            city_count=("city", "nunique"),
            year_min=("year", "min"),
            year_max=("year", "max"),
        )
    )
    coverage.to_csv(OUT / "monthly_bridge_indicator_coverage.csv", index=False, encoding="utf-8-sig")

    source_period_coverage = (
        monthly[monthly["monthly_indicator_coverage"].eq("monthly_indicator")]
        .groupby(["activity_group", "monthly_indicator_source", "year", "quarter"], as_index=False)
        .agg(months=("month", "nunique"), rows=("estimated_monthly_gva_eok", "size"))
    )
    source_period_coverage = source_period_coverage[source_period_coverage["months"].eq(3)].copy()
    source_period_coverage["quarter_period"] = source_period_coverage["year"].astype(str) + "Q" + source_period_coverage["quarter"].astype(str)
    source_period_summary = (
        source_period_coverage.groupby(["activity_group", "monthly_indicator_source"], as_index=False)
        .agg(
            complete_quarters=("quarter_period", "nunique"),
            first_complete_quarter=("quarter_period", "min"),
            last_complete_quarter=("quarter_period", "max"),
        )
        .sort_values(["monthly_indicator_source", "activity_group"])
    )
    source_period_summary.to_csv(OUT / "monthly_bridge_indicator_period_coverage.csv", index=False, encoding="utf-8-sig")

    summary = pd.DataFrame(
        [
            {
                "monthly_rows": len(monthly),
                "tracks": monthly["track"].nunique(),
                "years_min": int(monthly["year"].min()),
                "years_max": int(monthly["year"].max()),
                "sigungu_count": monthly[["quarter_region", "city"]].drop_duplicates().shape[0],
                "activity_count": monthly["activity_group"].nunique(),
                "indicator_rows_pct": float((monthly["monthly_indicator_coverage"].eq("monthly_indicator")).mean() * 100),
                "fallback_equal_split_rows_pct": float((monthly["monthly_indicator_coverage"].eq("fallback_equal_split")).mean() * 100),
                "max_abs_quarter_reaggregation_error_eok": float(audit["abs_reaggregation_error_eok"].max()),
                "bad_quarter_cells_gt_1won_equiv": int(audit["abs_reaggregation_error_eok"].gt(1e-8).sum()),
                "bad_month_count_cells": int(share_audit["months"].ne(3).sum()),
                "bad_month_share_sum_cells": int(share_audit["abs_share_sum_error"].gt(1e-10).sum()),
                "negative_month_value_cells": int(share_audit["negative_month_values"].sum()),
            }
        ]
    )
    summary.to_csv(OUT / "monthly_bridge_summary.csv", index=False, encoding="utf-8-sig")

    top_fallback = (
        coverage[coverage["monthly_indicator_coverage"].eq("fallback_equal_split")]
        .groupby(["activity_group"], as_index=False)
        .agg(fallback_sum_eok=("estimated_sum_eok", "sum"), fallback_rows=("rows", "sum"))
        .sort_values("fallback_sum_eok", ascending=False)
    )

    report = f"""# 전국 시군구 월별 GVA bridge 및 집계검증

생성시각: {datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")}

## 1. 목적

기존 `시군구×업종×분기` 추정값을 월 단위 운영자료로 확장했다. 월별 산출은 분기 추정값을 바꾸지 않고, 보유 월별 활동지표가 있는 업종은 해당 월별 지표 비중으로, 없는 업종은 분기 내 균등분할로 배분한다.

## 2. 산출 요약

{md_table(summary, digits=6)}

## 3. 사용한 월별 시간경로

| 업종군 | 월별 배분 기준 | 비고 |
| --- | --- | --- |
| 광업, 제조업 | 시도별 제조업 생산지수 | 광업+제조업 통합 GVA의 월중 변화 후보. 세부 광업 분리는 별도 actual 부족으로 보류 |
| 서비스 세부업종 | 전국 산업별 서비스업생산지수 | 지역별 배분에는 사용하지 않고, 같은 업종·분기의 시군구 GVA를 3개월로 나누는 시간경로로만 사용 |
| 건설업 | 전국 전산업생산지수 원지수의 건설업 항목 | 조달청 PPS가 coverage gate를 통과하기 전까지 지역별 공간배분은 기존 분기값 보존 |
| 공공 행정, 국방·사회보장 | 전국 전산업생산지수 원지수의 공공행정 항목 | 지역별 배분에는 사용하지 않고 분기 내 시간경로로만 사용 |
| 기타산업 및 순생산물세 등 | 분기 내 균등분할 | 월별 직접 지표가 없는 항목은 보수적 bridge |

## 4. 활동지표 coverage

{md_table(coverage.sort_values(["activity_group", "monthly_indicator_coverage"]).head(40), digits=3)}

## 5. 활동지표 완전분기 범위

월별 지표는 해당 분기의 3개월 값이 모두 있을 때만 사용했다. 2025년 최신월이 일부만 있는 경우에는 부분월을 외삽하지 않고 균등분할로 돌렸다.

{md_table(source_period_summary, digits=3)}

## 6. 균등분할 fallback이 큰 업종

{md_table(top_fallback.head(20), digits=3)}

## 7. 분기 재집계 및 월 share 무결성 검증

월별 추정값은 원 분기 추정값을 보존해야 한다. 따라서 각 `track×시도×시군구×업종×분기`별 월합과 원 분기값을 비교했다.

{md_table(summary[["max_abs_quarter_reaggregation_error_eok", "bad_quarter_cells_gt_1won_equiv", "bad_month_count_cells", "bad_month_share_sum_cells", "negative_month_value_cells"]], digits=10)}

## 8. 해석

1. 이 산출물은 월별 official actual 검증이 아니라 **상위 분기 추정값을 보존하는 월별 운영 bridge**다.
2. 광업·제조업은 시도별 월별 생산지수로 월중 변화를 반영한다.
3. 서비스업·건설업·공공행정은 전국 월별 지수만 사용하므로 **공간배분 근거가 아니라 시간배분 근거**다.
4. 조달청 PPS 계약정보가 2015~2025 coverage gate를 통과하기 전까지 건설업의 시군구 공간배분 route는 자동채택하지 않는다.
5. `bad_quarter_cells_gt_1won_equiv=0`이면 월별 추정값을 다시 분기로 합산했을 때 기존 분기 추정과 실질적으로 완전히 일치한다.

## 9. 산출물

- `nationwide/outputs/sigungu_industry_monthly_predictions.csv`
- `nationwide/outputs/monthly_bridge_quarter_reaggregation_audit.csv`
- `nationwide/outputs/monthly_bridge_share_integrity_audit.csv`
- `nationwide/outputs/monthly_bridge_indicator_coverage.csv`
- `nationwide/outputs/monthly_bridge_indicator_period_coverage.csv`
- `nationwide/outputs/monthly_bridge_summary.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
