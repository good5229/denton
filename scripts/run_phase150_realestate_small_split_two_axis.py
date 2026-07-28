#!/usr/bin/env python3
"""Phase150 two-axis real-estate small-industry split.

Phase149 showed that apartment trade activity should not replace the KSIC 68
middle-industry GVA nowcast.  This phase tests a narrower use: the split inside
KSIC 68 between

* 681: real-estate rental and supply
* 682: real-estate related services

The experiment separates stock-oriented signals (housing assessed value,
residential/commercial floor area) from transaction-service signals (apartment
deal count/value and broker offices).  It also labels ex-post/routed rules so
that a visually good two-city fit is not mistaken for an operationally validated
general model.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase150_realestate_small_split_two_axis"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase150_realestate_small_split_two_axis.md"

GOYANG_HOLDOUT = DATA / "partial_stats_phase41_all_ksic_holdout_detail.csv"
POHANG_HOLDOUT = DATA / "partial_stats_phase42_pohang_industry_holdout_detail.csv"
GOYANG_CUBE = DATA / "partial_stats_phase41_all_ksic_multiresolution_cube.parquet"
POHANG_CUBE = DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet"
BUILDING = DATA / "partial_stats_phase51_realestate_admin_name_direct_features.csv"
HOUSING = DATA / "phase56_housing_price" / "molit_public_housing_price_2025_goyang_pohang.parquet"
BROKER = DATA / "partial_stats_phase53_realestate_broker_goyang_pohang.csv"
RTMS_ROWS = DATA / "phase149_realestate_rtms_asof_candidate" / "phase149_rtms_apt_trade_rows.csv"
RTMS_STATUS = DATA / "phase149_realestate_rtms_asof_candidate" / "phase149_rtms_registered_date_status_summary.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
    out = out.fillna("").astype(str)
    cols = list(out.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in out.iterrows():
        lines.append("| " + " | ".join(row[col].replace("|", "\\|") for col in cols) + " |")
    return "\n".join(lines)


def large_gva(city: str) -> float:
    path = GOYANG_CUBE if city == "고양시" else POHANG_CUBE
    cube = pd.read_parquet(
        path,
        columns=["industry_level", "industry_code", "time_level", "period", "geo_level", "estimated_gva"],
    )
    sub = cube[
        cube["industry_level"].eq("대분류")
        & cube["industry_code"].astype(str).eq("L")
        & cube["time_level"].eq("연")
        & cube["period"].astype(str).eq("2023")
        & cube["geo_level"].eq("시")
    ]
    if sub.empty:
        raise RuntimeError(f"missing L large GVA for {city}")
    return float(sub["estimated_gva"].sum()) / 100.0


def actual_split() -> pd.DataFrame:
    goyang = pd.read_csv(GOYANG_HOLDOUT)
    goyang = goyang[goyang["industry_level"].eq("small") & goyang["parent_code"].eq("L00")].copy()
    goyang = goyang.rename(
        columns={"actual_sales_share": "actual_share", "predicted_proxy_share": "current_share"}
    )
    goyang["city"] = "고양시"

    pohang = pd.read_csv(POHANG_HOLDOUT)
    pohang = pohang[pohang["industry_level"].eq("소분류") & pohang["parent_code"].eq("L00")].copy()
    pohang = pohang.rename(columns={"predicted_share": "current_share"})
    pohang["city"] = "포항시"

    out = pd.concat(
        [
            goyang[["city", "industry_code", "actual_share", "current_share", "uniform_share"]],
            pohang[["city", "industry_code", "actual_share", "current_share", "uniform_share"]],
        ],
        ignore_index=True,
    )
    out["industry_code"] = out["industry_code"].astype(str)
    return out


def feature_table() -> pd.DataFrame:
    building = pd.read_csv(BUILDING)
    housing = pd.read_parquet(HOUSING)
    broker = pd.read_csv(BROKER)
    rtms = pd.read_csv(RTMS_ROWS)
    rtms["deal_year"] = pd.to_numeric(rtms["deal_year"], errors="coerce").astype("Int64")
    rtms["deal_amount_eok"] = pd.to_numeric(rtms["deal_amount_10k_krw"], errors="coerce").fillna(0.0) / 10000.0
    rows: list[dict[str, object]] = []
    for city in ["고양시", "포항시"]:
        b = building[building["city"].eq(city)]
        hmask = housing["시군구"].astype(str).str.contains("고양" if city == "고양시" else "포항", na=False)
        h = housing[hmask]
        br = broker[broker["city"].eq(city)]
        r = rtms[rtms["city"].eq(city) & rtms["deal_year"].eq(2023)]
        r2022 = rtms[rtms["city"].eq(city) & rtms["deal_year"].eq(2022)]
        stock = float(pd.to_numeric(h["공시가격"], errors="coerce").sum() / 1e8)
        broker_count = float(len(br))
        transaction_value = float(r["deal_amount_eok"].sum())
        transaction_count = float(len(r))
        rows.append(
            {
                "city": city,
                "assessed_housing_value_eok": stock,
                "residential_area_sqm": float(b.loc[b["use_group"].eq("주거"), "total_floor_area"].sum()),
                "commercial_area_sqm": float(b.loc[b["use_group"].eq("상업·업무"), "total_floor_area"].sum()),
                "broker_count": broker_count,
                "rtms_2023_deal_value_eok": transaction_value,
                "rtms_2023_deal_count": transaction_count,
                "rtms_2022_deal_value_eok": float(r2022["deal_amount_eok"].sum()),
                "rtms_value_yoy_pct": (
                    (transaction_value / float(r2022["deal_amount_eok"].sum()) - 1) * 100
                    if float(r2022["deal_amount_eok"].sum()) > 0
                    else np.nan
                ),
                "stock_value_per_broker_eok": stock / broker_count if broker_count else np.nan,
                "deal_value_per_broker_eok": transaction_value / broker_count if broker_count else np.nan,
                "deal_count_per_broker": transaction_count / broker_count if broker_count else np.nan,
                "turnover_value_pct": transaction_value / stock * 100 if stock else np.nan,
            }
        )
    return pd.DataFrame(rows)


def candidate_shares(features: pd.DataFrame, actual: pd.DataFrame) -> pd.DataFrame:
    current_681 = actual[actual["industry_code"].eq("681")].set_index("city")["current_share"].to_dict()
    rows: list[dict[str, object]] = []
    for r in features.itertuples(index=False):
        city = r.city
        stock_per_broker = float(r.stock_value_per_broker_eok)
        area_share = r.residential_area_sqm / (r.residential_area_sqm + r.commercial_area_sqm)
        stock_dominance = r.assessed_housing_value_eok / (
            r.assessed_housing_value_eok + r.rtms_2023_deal_value_eok + r.broker_count
        )
        turnover_inverse = max(0.0, min(1.0, 1 - r.turnover_value_pct / 100))
        base = [
            ("현행 소분류 합산 기준", current_681[city], "기존 사업체·종사자 중심", "baseline", "운영 기준"),
            ("균등 분할", 0.5, "681/682 균등", "common_rule", "단순 기준"),
            ("주거·상업 면적 기준", area_share, "주거 연면적 ÷ 주거+상업업무 연면적", "stock_axis", "정밀화 구조 후보"),
            ("주택재고 우위+2023 거래액 기준", stock_dominance, "공시가격 ÷ 공시가격+2023거래액+중개업소수", "stock_axis", "정밀화 구조 후보"),
            ("2023 거래회전율 역수 기준", turnover_inverse, "1 - 2023 아파트 거래액/공시가격", "transaction_axis", "보조 진단"),
        ]
        for name, share, note, family, status in base:
            rows.append(
                {
                    "city": city,
                    "candidate": name,
                    "share_681": share,
                    "method_note": note,
                    "candidate_family": family,
                    "validation_status": status,
                }
            )
        for k in [200, 300, 400, 500, 600, 700, 800, 900, 1000]:
            rows.append(
                {
                    "city": city,
                    "candidate": f"재고가치/중개업소 포화 기준 K={k}",
                    "share_681": stock_per_broker / (stock_per_broker + k),
                    "method_note": f"공시가격총액/중개업소수 ÷ (공시가격총액/중개업소수 + {k})",
                    "candidate_family": "stock_broker_saturation_common_k",
                    "validation_status": "동일식 K 후보(미채택)",
                }
            )
        # A transparent two-axis family.  The service axis combines transaction
        # value and broker count; lambda is still grid-screened, so it must not
        # be treated as a finalized rule.
        service_axis = r.rtms_2023_deal_value_eok * r.broker_count / 1000.0
        for lam in [1, 5, 10, 20, 50, 100, 200]:
            rows.append(
                {
                    "city": city,
                    "candidate": f"재고축/(재고축+거래서비스축×{lam})",
                    "share_681": r.assessed_housing_value_eok / (r.assessed_housing_value_eok + lam * service_axis),
                    "method_note": "재고축=공시가격, 거래서비스축=2023거래액×중개업소수/1000",
                    "candidate_family": "two_axis_grid_expost",
                    "validation_status": "사후 grid 후보",
                }
            )
        routed_k = 300 if stock_per_broker >= 300 else 700
        rows.append(
            {
                "city": city,
                "candidate": "재고가치 밀도 라우팅 K=300/700",
                "share_681": stock_per_broker / (stock_per_broker + routed_k),
                "method_note": "중개업소당 공시가격 300억원 이상 K=300, 미만 K=700",
                "candidate_family": "routed_rule_two_city_pilot",
                "validation_status": "2도시 파일럿: 외부지역 검증 전 채택금지",
            }
        )
    return pd.DataFrame(rows)


def evaluate(candidates: pd.DataFrame, actual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for cand in candidates.itertuples(index=False):
        gva = large_gva(cand.city)
        for code, label, share in [
            ("681", "부동산 임대 및 공급업", cand.share_681),
            ("682", "부동산 관련 서비스업", 1.0 - cand.share_681),
        ]:
            target = actual[actual["city"].eq(cand.city) & actual["industry_code"].eq(code)].iloc[0]
            actual_eok = float(target["actual_share"]) * gva
            pred_eok = share * gva
            err = abs(pred_eok - actual_eok)
            rows.append(
                {
                    "city": cand.city,
                    "candidate": cand.candidate,
                    "candidate_family": cand.candidate_family,
                    "validation_status": cand.validation_status,
                    "method_note": cand.method_note,
                    "industry_code": code,
                    "industry_name": label,
                    "actual_share_pct": float(target["actual_share"]) * 100,
                    "predicted_share_pct": share * 100,
                    "actual_gva_eok": actual_eok,
                    "predicted_gva_eok": pred_eok,
                    "abs_error_eok": err,
                    "error_rate_pct": err / actual_eok * 100 if actual_eok else np.nan,
                }
            )
    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby(["city", "candidate", "candidate_family", "validation_status", "method_note"], as_index=False)
        .agg(
            actual_sum_eok=("actual_gva_eok", "sum"),
            combined_error_eok=("abs_error_eok", "sum"),
        )
    )
    share681 = detail[detail["industry_code"].eq("681")][
        ["city", "candidate", "actual_share_pct", "predicted_share_pct"]
    ].copy()
    summary = summary.merge(share681, on=["city", "candidate"], how="left", validate="one_to_one")
    summary["share_error_pp"] = (summary["predicted_share_pct"] - summary["actual_share_pct"]).abs()
    summary["combined_wape_pct"] = summary["combined_error_eok"] / summary["actual_sum_eok"] * 100
    baseline_err = summary[summary["candidate"].eq("현행 소분류 합산 기준")].set_index("city")["combined_error_eok"]
    summary["improvement_vs_current_eok"] = summary.apply(
        lambda r: float(baseline_err[r["city"]]) - r["combined_error_eok"],
        axis=1,
    )
    summary["improvement_vs_current_pct"] = summary.apply(
        lambda r: r["improvement_vs_current_eok"] / float(baseline_err[r["city"]]) * 100
        if float(baseline_err[r["city"]]) > 0
        else np.nan,
        axis=1,
    )
    summary["decision"] = np.where(summary["improvement_vs_current_eok"].gt(0), "현행대비 개선", "현행대비 악화")

    overall = (
        summary.groupby(["candidate", "candidate_family", "validation_status", "method_note"], as_index=False)
        .agg(
            city_count=("city", "nunique"),
            two_city_actual_eok=("actual_sum_eok", "sum"),
            two_city_error_eok=("combined_error_eok", "sum"),
            max_city_wape_pct=("combined_wape_pct", "max"),
            mean_city_wape_pct=("combined_wape_pct", "mean"),
            mean_share_error_pp=("share_error_pp", "mean"),
            min_improvement_vs_current_pct=("improvement_vs_current_pct", "min"),
        )
    )
    overall["two_city_wape_pct"] = overall["two_city_error_eok"] / overall["two_city_actual_eok"] * 100
    overall["all_cities_improved"] = overall["min_improvement_vs_current_pct"].gt(0)
    overall["target_10pct_status"] = np.select(
        [
            overall["candidate_family"].isin(["two_axis_grid_expost", "routed_rule_two_city_pilot"])
            & overall["max_city_wape_pct"].le(10.0),
            overall["max_city_wape_pct"].le(10.0),
        ],
        ["사후 10% 이내(채택금지)", "2도시 모두 10% 이내"],
        default="10% 목표 미달",
    )
    overall = overall.sort_values(["all_cities_improved", "max_city_wape_pct", "two_city_wape_pct"], ascending=[False, True, True])
    return detail, summary, overall


def main() -> None:
    for p in [
        GOYANG_HOLDOUT,
        POHANG_HOLDOUT,
        GOYANG_CUBE,
        POHANG_CUBE,
        BUILDING,
        HOUSING,
        BROKER,
        RTMS_ROWS,
    ]:
        if not p.exists():
            raise FileNotFoundError(p)
    OUT.mkdir(parents=True, exist_ok=True)
    actual = actual_split()
    features = feature_table()
    candidates = candidate_shares(features, actual)
    detail, summary, overall = evaluate(candidates, actual)
    status = pd.read_csv(RTMS_STATUS) if RTMS_STATUS.exists() else pd.DataFrame()

    actual.to_csv(OUT / "phase150_realestate_actual_small_split.csv", index=False, encoding="utf-8-sig")
    features.to_csv(OUT / "phase150_realestate_two_axis_features.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(OUT / "phase150_realestate_two_axis_candidates.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase150_realestate_two_axis_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase150_realestate_two_axis_city_summary.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT / "phase150_realestate_two_axis_overall.csv", index=False, encoding="utf-8-sig")

    best_operational = overall[
        overall["all_cities_improved"]
        & ~overall["candidate_family"].isin(["two_axis_grid_expost", "routed_rule_two_city_pilot"])
    ].head(8)
    ex_post = overall[
        overall["candidate_family"].isin(["two_axis_grid_expost", "routed_rule_two_city_pilot"])
    ].head(8)
    city_best = summary.sort_values(["city", "combined_wape_pct"]).groupby("city", as_index=False).head(5)

    manifest = {
        "phase": "phase150_realestate_small_split_two_axis",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "inputs": [
            {"path": str(p.relative_to(ROOT)), "sha256": sha256(p)}
            for p in [GOYANG_HOLDOUT, POHANG_HOLDOUT, BUILDING, HOUSING, BROKER, RTMS_ROWS]
        ],
        "outputs": [
            "phase150_realestate_actual_small_split.csv",
            "phase150_realestate_two_axis_features.csv",
            "phase150_realestate_two_axis_candidates.csv",
            "phase150_realestate_two_axis_detail.csv",
            "phase150_realestate_two_axis_city_summary.csv",
            "phase150_realestate_two_axis_overall.csv",
            str(REPORT.relative_to(ROOT)),
        ],
        "adoption_warning": "Routed and grid candidates are two-city diagnostics; do not promote without external-city validation.",
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = f"""# Phase150 부동산업 소분류 2축 배분 실험

## 목적

Phase149에서 아파트 실거래액은 `부동산업(KSIC 68)` 총부가가치 직접 예측식으로 부적합하다고 판정했다. 이번 Phase150은 사용처를 좁혀, `681 부동산 임대 및 공급업`과 `682 부동산 관련 서비스업`의 **소분류 내부 배분**에 실거래 자료를 제한적으로 활용할 수 있는지 검증한다.

## 자료와 시점

- 검증 대상: 2023년 부동산업 소분류 681/682
- 금액 단위: 억원
- 재고축: 2025 주택 공시가격, 건축물대장 주거/상업 연면적, 중개업소 수
- 거래서비스축: Phase149에서 수집·보강한 2023년 아파트 매매 실거래액/건수
- 시점 판정: 이 실험은 **2023년 사후 정밀화 진단**이다. 2025 공시가격과 건축물대장 기반 stock 자료가 포함되어 있으므로 2023년 각 분기 종료 후 1개월 내 속보 예측으로 사용할 수 없다.
- 엄격 제한: 포스터에는 2023 실거래·2025 공시가격·건축물대장 혼합 결과를 “속보 성능” 또는 “운영 성능” 수치로 제시하지 않는다.

## 등기일자 보강 상태

{md_table(status.rename(columns={
    'city': '지역',
    'deal_year': '계약연도',
    'registered_date_status': '등기일자 상태',
    'rows': '행수',
    'share_pct': '비중(%)',
}) if not status.empty else status)}

## 2축 피처

{md_table(features.rename(columns={
    'city': '지역',
    'assessed_housing_value_eok': '공시가격 총액(억원)',
    'residential_area_sqm': '주거 연면적',
    'commercial_area_sqm': '상업업무 연면적',
    'broker_count': '중개업소 수',
    'rtms_2023_deal_value_eok': '2023 아파트 거래액(억원)',
    'rtms_2023_deal_count': '2023 거래건수',
    'rtms_2022_deal_value_eok': '2022 아파트 거래액(억원)',
    'rtms_value_yoy_pct': '거래액 전년대비(%)',
    'stock_value_per_broker_eok': '중개업소당 공시가격(억원)',
    'deal_value_per_broker_eok': '중개업소당 거래액(억원)',
    'deal_count_per_broker': '중개업소당 거래건수',
    'turnover_value_pct': '공시가격 대비 거래액(%)',
}))}

## 공통 개선 후보 상위(목표 미달)

아래 표는 두 도시 모두 현행보다 개선되고, 사후 grid 또는 2도시 라우팅 후보를 제외한 후보만 표시한다. 즉 “공통으로 나아지는 방향”을 찾기 위한 후보군이지, 운영 채택안이 아니다.

중요: 공통 후보들은 “현행보다 낫다”는 뜻이지, 목표였던 10% 오차 이내를 달성했다는 뜻이 아니다. 최대 도시 WAPE가 10%를 넘으면 포스터에서 성능 달성 수치로 쓰지 않는다.

{md_table(best_operational[[
    'candidate',
    'candidate_family',
    'validation_status',
    'target_10pct_status',
    'two_city_error_eok',
    'two_city_wape_pct',
    'max_city_wape_pct',
    'mean_share_error_pp',
    'min_improvement_vs_current_pct',
]].rename(columns={
    'candidate': '후보',
    'candidate_family': '후보군',
    'validation_status': '검증상태',
    'target_10pct_status': '10% 목표',
    'two_city_error_eok': '2도시 오차(억원)',
    'two_city_wape_pct': '2도시 WAPE(%)',
    'max_city_wape_pct': '최대 도시 WAPE(%)',
    'mean_share_error_pp': '평균 681 비중오차(%p)',
    'min_improvement_vs_current_pct': '최소 현행개선율(%)',
}))}

## 사후 진단 후보(채택 금지)

아래 후보는 두 도시 자료를 본 뒤 grid 또는 라우팅으로 좋아진 조합이다. 외부 시군구 검증 전에는 포스터 성능이나 운영 후보로 쓰지 않는다.

{md_table(ex_post[[
    'candidate',
    'candidate_family',
    'validation_status',
    'target_10pct_status',
    'two_city_error_eok',
    'two_city_wape_pct',
    'max_city_wape_pct',
    'mean_share_error_pp',
    'min_improvement_vs_current_pct',
]].rename(columns={
    'candidate': '후보',
    'candidate_family': '후보군',
    'validation_status': '검증상태',
    'target_10pct_status': '10% 목표',
    'two_city_error_eok': '2도시 오차(억원)',
    'two_city_wape_pct': '2도시 WAPE(%)',
    'max_city_wape_pct': '최대 도시 WAPE(%)',
    'mean_share_error_pp': '평균 681 비중오차(%p)',
    'min_improvement_vs_current_pct': '최소 현행개선율(%)',
}))}

## 지역별 상위 후보

{md_table(city_best[[
    'city',
    'candidate',
    'validation_status',
    'actual_share_pct',
    'predicted_share_pct',
    'share_error_pp',
    'combined_error_eok',
    'combined_wape_pct',
    'improvement_vs_current_pct',
]].rename(columns={
    'city': '지역',
    'candidate': '후보',
    'validation_status': '검증상태',
    'actual_share_pct': '681 실제비중(%)',
    'predicted_share_pct': '681 추정비중(%)',
    'share_error_pp': '681 비중오차(%p)',
    'combined_error_eok': '합산오차(억원)',
    'combined_wape_pct': '합산 WAPE(%)',
    'improvement_vs_current_pct': '현행개선율(%)',
}))}

## 판정

1. 부동산업 총량 예측은 Phase145 baseline을 유지한다. 실거래액을 총량에 직접 섞는 방식은 Phase149에서 채택하지 않았다.
2. 소분류 내부 배분에서는 `재고가치/중개업소 포화 기준` 계열이 기존 사업체·종사자 배분보다 개선 방향을 보인다. 다만 2025 공시가격·건축물대장 자료가 섞여 있어 정밀화 진단으로만 해석한다.
3. 동일식 K 후보 중 현재 10% 목표를 만족하는 후보는 없다. 가장 나은 K=400도 최대 도시 WAPE가 23.4%라서 “목표 달성”으로 표현하면 안 된다.
4. 고양시는 K=300, 포항시는 K=700이 각각 잘 맞는다. 이 K=300/700 라우팅은 두 도시 결과를 본 뒤 만든 2도시 파일럿 규칙이므로, 외부 시군구 검증 전에는 채택 금지다.
5. 포스터에 안전하게 반영 가능한 문구는 “부동산업 내부 배분은 거래액 단독보다 재고가치·중개업소·거래활동을 분리한 2축 진단이 필요” 수준이다.
6. 포스터에 반영하면 안 되는 수치는 K=300/700 라우팅의 2도시 WAPE 4.28%, 고양 5.39%, 포항 0.74%다. 이 값은 사후 라우팅 결과라 운영 성능이 아니다.
7. 다음 일반화 단계에서는 임의 10개 시군구를 추가해 `중개업소당 공시가격` 또는 `거래회전율`이 K 선택을 안정적으로 설명하는지 검증해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    for name in [
        "phase150_realestate_actual_small_split.csv",
        "phase150_realestate_two_axis_features.csv",
        "phase150_realestate_two_axis_candidates.csv",
        "phase150_realestate_two_axis_detail.csv",
        "phase150_realestate_two_axis_city_summary.csv",
        "phase150_realestate_two_axis_overall.csv",
        "execution_manifest.json",
    ]:
        print(f"Wrote {(OUT / name).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
