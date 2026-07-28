#!/usr/bin/env python3
"""Phase149 real-estate RTMS as-of candidate audit.

This phase tests whether apartment trade activity can improve the Goyang/Pohang
middle-industry GVA nowcast for KSIC 68 (real estate).

The test is intentionally conservative:

* strict/flash uses only 2023 rows with `registered_date <= Q+1 month cutoff`;
* precision uses retrospective deal-month totals;
* scaling uses year-2 GVA and year-2 same-YTD RTMS activity, avoiding target
  year actual totals;
* candidates are compared against the already selected Phase145 baseline and
  are not adopted if they worsen the rolling benchmark.
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
OUT = DATA / "phase149_realestate_rtms_asof_candidate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase149_realestate_rtms_asof_candidate.md"

RTMS_ROWS = OUT / "phase149_rtms_apt_trade_rows.csv"
RTMS_MONTHLY = OUT / "phase149_rtms_apt_trade_gu_monthly.csv"
RTMS_MANIFEST = OUT / "phase149_rtms_collection_manifest.json"
RTMS_STATUS_SUMMARY = OUT / "phase149_rtms_registered_date_status_summary.csv"
PHASE145_SELECTED = DATA / "phase145_operational_route_decision_registry" / "phase145_selected_operational_predictions.csv"
SIGUNGU_GVA = DATA / "expanded_sigungu_grva_real.csv"

CUTOFF = {
    1: "04-30",
    2: "07-31",
    3: "10-31",
    4: "01-31",
}


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


def load_realestate_gva() -> pd.DataFrame:
    gva = pd.read_csv(SIGUNGU_GVA, encoding="cp949", dtype=str)
    gva = gva[
        gva["c1_nm"].isin(["고양시", "포항시"])
        & gva["c2_nm"].astype(str).str.contains("부동산업", na=False)
    ].copy()
    gva["city"] = gva["c1_nm"]
    gva["year"] = gva["prd_de"].astype(int)
    gva["actual_gva_eok"] = pd.to_numeric(gva["value"].replace("-", np.nan), errors="coerce") / 100.0
    return gva[["city", "year", "actual_gva_eok"]].dropna()


def prep_rtms() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = pd.read_csv(RTMS_ROWS)
    rows["year"] = rows["period"].astype(str).str[:4].astype(int)
    rows["month"] = rows["period"].astype(str).str[4:].astype(int)
    rows["registered_dt"] = pd.to_datetime(rows["registered_date"], format="%y.%m.%d", errors="coerce")
    rows["deal_amount_eok"] = pd.to_numeric(rows["deal_amount_10k_krw"], errors="coerce").fillna(0.0) / 10000.0
    rows["deal_count_one"] = 1.0

    if "registered_date_status" not in rows.columns:
        rows["registered_date_status"] = np.where(
            rows["year"].lt(2023) & rows["registered_dt"].isna(),
            "not_disclosed_pre_2023_contract_by_molit_rule",
            np.where(rows["registered_dt"].notna(), "actual_rgstDate_provided_by_molit", "blank_after_2023"),
        )
    coverage = (
        rows.groupby(["city", "year"], as_index=False)
        .agg(
            row_count=("deal_count_one", "sum"),
            registered_date_rows=("registered_dt", lambda s: int(s.notna().sum())),
            deal_amount_eok=("deal_amount_eok", "sum"),
        )
    )
    coverage["registered_date_coverage_pct"] = (
        coverage["registered_date_rows"] / coverage["row_count"] * 100
    )
    return rows, coverage


def ytd_amount(rows: pd.DataFrame, city: str, year: int, k: int, track: str) -> tuple[float, int, int]:
    max_month = 12 if k == 4 else k * 3
    part = rows[rows["city"].eq(city) & rows["year"].eq(year) & rows["month"].le(max_month)].copy()
    before = len(part)
    if track == "strict_registered_q_plus_1":
        cutoff_year = year + 1 if k == 4 else year
        cutoff = pd.Timestamp(f"{cutoff_year}-{CUTOFF[k]}")
        part = part[part["registered_dt"].le(cutoff)]
    return float(part["deal_amount_eok"].sum()), before, int(len(part))


def make_candidates(rows: pd.DataFrame, gva: pd.DataFrame) -> pd.DataFrame:
    base = pd.read_csv(PHASE145_SELECTED, dtype={"middle_code": str})
    base = base[
        base["middle_code"].str.zfill(2).eq("68")
        & base["year"].between(2022, 2023)
        & base["available_quarters"].isin([1, 2, 3])
    ].copy()

    rows_out: list[dict[str, object]] = []
    weights = [0.0, 0.10, 0.25, 0.50, 0.75, 1.0]
    for _, b in base.iterrows():
        city = str(b["city"])
        year = int(b["year"])
        k = int(b["available_quarters"])
        lag_year = year - 2
        lag_gva = gva[gva["city"].eq(city) & gva["year"].eq(lag_year)]["actual_gva_eok"]
        if lag_gva.empty:
            continue
        lag_ytd, _, _ = ytd_amount(rows, city, lag_year, k, "precision_deal_month")
        if lag_ytd <= 0:
            continue
        for track in ["precision_deal_month", "strict_registered_q_plus_1"]:
            if track == "strict_registered_q_plus_1" and year != 2023:
                # 2020~2022 RTMS rows do not carry registered_date in this API
                # response, so strict historical reconstruction is not auditable.
                continue
            cur_ytd, pre_filter_rows, used_rows = ytd_amount(rows, city, year, k, track)
            rtms_pred = float(lag_gva.iloc[0]) * cur_ytd / lag_ytd
            for w in weights:
                pred = (1.0 - w) * float(b["annual_prediction_eok"]) + w * rtms_pred
                error = abs(pred - float(b["actual_annual_gva_eok"]))
                rows_out.append(
                    {
                        "city": city,
                        "year": year,
                        "available_quarters": k,
                        "vintage_label": b["vintage_label"],
                        "track": track,
                        "mix_weight_rtms": w,
                        "actual_gva_eok": float(b["actual_annual_gva_eok"]),
                        "phase145_baseline_pred_eok": float(b["annual_prediction_eok"]),
                        "rtms_y2_scaled_pred_eok": rtms_pred,
                        "candidate_pred_eok": pred,
                        "abs_error_eok": error,
                        "error_rate_pct": error / float(b["actual_annual_gva_eok"]) * 100,
                        "baseline_abs_error_eok": float(b["annual_error_eok"]),
                        "baseline_error_rate_pct": float(b["annual_error_rate_pct"]),
                        "delta_error_eok_vs_baseline": error - float(b["annual_error_eok"]),
                        "current_ytd_rtms_amount_eok": cur_ytd,
                        "lag2_ytd_rtms_amount_eok": lag_ytd,
                        "pre_filter_rows": pre_filter_rows,
                        "used_rows": used_rows,
                        "registered_filter_retention_pct": used_rows / pre_filter_rows * 100 if pre_filter_rows else np.nan,
                        "leakage_guard": "uses y-2 GVA and y-2 same-YTD RTMS; target actual only for evaluation",
                    }
                )
    return pd.DataFrame(rows_out)


def summarize(cand: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    overall = (
        cand.groupby(["track", "available_quarters", "mix_weight_rtms"], as_index=False)
        .agg(
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("abs_error_eok", "sum"),
            baseline_error_sum_eok=("baseline_abs_error_eok", "sum"),
            cells=("abs_error_eok", "size"),
        )
    )
    overall["wape_pct"] = overall["error_sum_eok"] / overall["actual_sum_eok"] * 100
    overall["baseline_wape_pct"] = overall["baseline_error_sum_eok"] / overall["actual_sum_eok"] * 100
    overall["delta_wape_pp"] = overall["wape_pct"] - overall["baseline_wape_pct"]
    overall["adoption_status"] = np.where(
        overall["delta_wape_pp"].lt(-0.10),
        "사후 개선(채택불가)",
        np.where(overall["delta_wape_pp"].le(0.10), "동률권", "악화"),
    )

    city = (
        cand.groupby(["city", "track", "available_quarters", "mix_weight_rtms"], as_index=False)
        .agg(
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("abs_error_eok", "sum"),
            baseline_error_sum_eok=("baseline_abs_error_eok", "sum"),
            cells=("abs_error_eok", "size"),
        )
    )
    city["wape_pct"] = city["error_sum_eok"] / city["actual_sum_eok"] * 100
    city["baseline_wape_pct"] = city["baseline_error_sum_eok"] / city["actual_sum_eok"] * 100
    city["delta_wape_pp"] = city["wape_pct"] - city["baseline_wape_pct"]

    best = (
        overall.sort_values(["track", "available_quarters", "wape_pct"])
        .groupby(["track", "available_quarters"], as_index=False)
        .head(1)
    )
    return overall, city, best


def main() -> None:
    for p in [RTMS_ROWS, RTMS_MONTHLY, RTMS_MANIFEST, PHASE145_SELECTED, SIGUNGU_GVA]:
        if not p.exists():
            raise FileNotFoundError(p)
    OUT.mkdir(parents=True, exist_ok=True)
    rtms_rows, coverage = prep_rtms()
    status_summary = pd.read_csv(RTMS_STATUS_SUMMARY) if RTMS_STATUS_SUMMARY.exists() else pd.DataFrame()
    gva = load_realestate_gva()
    candidates = make_candidates(rtms_rows, gva)
    overall, city, best = summarize(candidates)

    coverage.to_csv(OUT / "phase149_rtms_registered_date_coverage.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(OUT / "phase149_realestate_rtms_candidate_detail.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT / "phase149_realestate_rtms_candidate_overall.csv", index=False, encoding="utf-8-sig")
    city.to_csv(OUT / "phase149_realestate_rtms_candidate_city.csv", index=False, encoding="utf-8-sig")
    best.to_csv(OUT / "phase149_realestate_rtms_candidate_best_by_vintage.csv", index=False, encoding="utf-8-sig")

    # Compact views for the report.
    coverage_view = coverage.copy()
    coverage_view["row_count"] = coverage_view["row_count"].astype(int)
    coverage_view["registered_date_rows"] = coverage_view["registered_date_rows"].astype(int)
    best_view = best[
        [
            "track",
            "available_quarters",
            "mix_weight_rtms",
            "actual_sum_eok",
            "error_sum_eok",
            "baseline_error_sum_eok",
            "wape_pct",
            "baseline_wape_pct",
            "delta_wape_pp",
            "adoption_status",
        ]
    ].copy()
    ex_post_note = "사후 최선(채택근거 아님)"
    best_view["selection_note"] = ex_post_note
    city_best = (
        city.sort_values(["city", "track", "available_quarters", "wape_pct"])
        .groupby(["city", "track", "available_quarters"], as_index=False)
        .head(1)
    )

    manifest = {
        "phase": "phase149_realestate_rtms_asof_candidate",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "inputs": [
            {"path": str(RTMS_ROWS.relative_to(ROOT)), "rows": int(len(rtms_rows)), "sha256": sha256(RTMS_ROWS)},
            {"path": str(RTMS_MONTHLY.relative_to(ROOT)), "sha256": sha256(RTMS_MONTHLY)},
            {"path": str(PHASE145_SELECTED.relative_to(ROOT)), "sha256": sha256(PHASE145_SELECTED)},
            {"path": str(SIGUNGU_GVA.relative_to(ROOT)), "sha256": sha256(SIGUNGU_GVA)},
        ],
        "outputs": [
            "phase149_rtms_registered_date_coverage.csv",
            "phase149_realestate_rtms_candidate_detail.csv",
            "phase149_realestate_rtms_candidate_overall.csv",
            "phase149_realestate_rtms_candidate_city.csv",
            "phase149_realestate_rtms_candidate_best_by_vintage.csv",
            str(REPORT.relative_to(ROOT)),
        ],
        "adoption_decision": "Do not adopt RTMS apartment trade as total KSIC 68 nowcast route. Keep as subcomponent/precision diagnostic candidate.",
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = f"""# Phase149 부동산업 실거래 활동지표 strict/as-of 후보 감사

## 목적

Phase148에서 고양시·포항시 모두 `부동산업(KSIC 68)`이 금액가중 우선순위이면서 직접 as-of 후보가 비어 있는 것으로 확인됐다. 이번 단계는 공공데이터포털의 무료 `국토교통부_아파트매매 실거래 상세 자료`를 수집해, 부동산업 총부가가치(GVA) 예측에 넣을 수 있는지 검증한다.

## 사용 자료

- 자료명: 국토교통부_아파트매매 실거래 상세 자료
- 링크: https://www.data.go.kr/data/15126469/openapi.do
- 공공데이터포털 데이터셋 등록일/수정일: 2024-01-25 / 2026-07-22
- 업데이트 주기: 실시간
- 수집 범위: 고양시 3개 구, 포항시 2개 구, 2020~2023년 월별 아파트 매매
- 수집 결과: 248회 호출, 76,679건, 실패 호출 0건
- 공식 등기일자 공개 기준: 2023년 1월 1일 이후 아파트 매매 계약 체결 건
- 주의: 행별 `registered_date`는 원천 XML의 `rgstDate`, 즉 소유권 이전등기일자다. 공공데이터포털의 데이터셋 `등록일`과 다르다.
- 보강: 원천 XML을 다시 파싱해 `registered_date`를 채웠고, 후속 호환을 위해 오타형 `registerd_date` 컬럼도 추가했다. 2020~2022년 `rgstDate` 공백은 파서 문제가 아니라 원천 공개대상 밖이므로 실제 날짜를 임의 보간하지 않고 `registered_date_filled/status/is_actual`로 상태를 기록했다.

## 등록일 필드 적격성

{md_table(coverage_view.rename(columns={
    'city': '지역',
    'year': '연도',
    'row_count': '거래행 수',
    'registered_date_rows': '등록일 존재행',
    'deal_amount_eok': '거래액(억원)',
    'registered_date_coverage_pct': '등록일 존재율(%)',
}))}

## 등록일 보강 상태

{md_table(status_summary.rename(columns={
    'city': '지역',
    'deal_year': '계약연도',
    'registered_date_status': '등기일자 상태',
    'rows': '행수',
    'share_pct': '비중(%)',
}) if not status_summary.empty else status_summary)}

## 후보식

부동산업은 거래액 변동과 총부가가치가 같은 속도로 움직인다고 보기 어렵다. 따라서 후보식은 직접 대체와 보수 혼합을 모두 비교했다.

- 실거래 흐름형: `y-2년 부동산 GVA × 당해 YTD 실거래액 / y-2년 같은 YTD 실거래액`
- 보수 혼합형: `Phase145 기존 예측 × (1-w) + 실거래 흐름형 × w`
- `w`: 0, 0.10, 0.25, 0.50, 0.75, 1.00
- strict 후보: 2023년만 등록일 `Q+1개월 말일 이하` 행 사용
- 정밀화 후보: 회고적으로 확인 가능한 거래월 전체 행 사용

## 사후 최선 조합 진단(채택 근거 아님)

아래 표는 실제값을 본 뒤 혼합비중 `w` 중 가장 낮은 오차를 고른 **사후 진단표**다. 따라서 운영 채택 또는 포스터용 성능 수치로 쓰지 않는다. 특히 strict 2023 조합은 등록일 필터가 가능한 2023년 2개 도시 셀에 한정되므로 Phase145의 2022~2023 rolling 성능과 직접 비교할 수 없다.

{md_table(best_view.rename(columns={
    'track': '자료트랙',
    'available_quarters': '가용분기',
    'mix_weight_rtms': '실거래 혼합비중',
    'actual_sum_eok': '실제합계(억원)',
    'error_sum_eok': '후보오차합(억원)',
    'baseline_error_sum_eok': '기존오차합(억원)',
    'wape_pct': '후보 WAPE(%)',
    'baseline_wape_pct': '기존 WAPE(%)',
    'delta_wape_pp': '기존 대비 차이(%p)',
    'adoption_status': '판정',
    'selection_note': '선택주의',
}))}

## 지역별 사후 최선 조합(채택 근거 아님)

{md_table(city_best[[
    'city',
    'track',
    'available_quarters',
    'mix_weight_rtms',
    'actual_sum_eok',
    'error_sum_eok',
    'baseline_error_sum_eok',
    'wape_pct',
    'baseline_wape_pct',
    'delta_wape_pp',
]].rename(columns={
    'city': '지역',
    'track': '자료트랙',
    'available_quarters': '가용분기',
    'mix_weight_rtms': '실거래 혼합비중',
    'actual_sum_eok': '실제합계(억원)',
    'error_sum_eok': '후보오차합(억원)',
    'baseline_error_sum_eok': '기존오차합(억원)',
    'wape_pct': '후보 WAPE(%)',
    'baseline_wape_pct': '기존 WAPE(%)',
    'delta_wape_pp': '기존 대비 차이(%p)',
}))}

## 판정

1. 아파트 매매 실거래액은 부동산업 총 GVA의 직접 예측식으로 채택하지 않는다. 정밀화 트랙의 2022~2023 rolling 전체에서는 기존 Phase145 baseline인 `w=0`이 최선이다.
2. 원인은 부동산업 GVA가 거래수수료만이 아니라 임대, 관리, 귀속임대료, 비거래 재고가치 성격을 크게 포함하기 때문이다. 2020~2023년 아파트 매매액은 급등락했지만 부동산업 GVA는 상대적으로 완만했다.
3. 2020~2022년 등록일 필드가 원천 미공개이므로 과거 Q+1개월 속보 재현은 불가능하다. 2023년 strict 필터의 낮은 오차는 실제값을 본 뒤 혼합비중을 고른 사후 결과라 운영 성능으로 채택하지 않는다.
4. 실거래 자료는 버리지 않는다. 다만 `부동산업 전체`가 아니라 `부동산 관련 서비스업(중개·거래 서비스)` 또는 부동산업 내부 소분류 배분의 한 구성요소로 제한하는 것이 맞다.
5. 다음 개선은 공시가격·주거/상업 연면적·건축물 stock을 부동산업의 재고축으로 두고, 실거래는 회전율/중개서비스축으로 분리한 2축 모델이어야 한다.

## 다음 단계

1. Phase74의 부동산 소분류 분할식과 이번 RTMS 시계열을 결합해 `681 임대 및 공급업`과 `682 부동산 관련 서비스업`을 분리한다.
2. 681은 공시가격·주거/상업 연면적·건축물 stock 중심, 682는 실거래 건수·거래액·중개업소 수 중심으로 배분한다.
3. 중분류 68 총량 검증은 기존 Phase145 baseline을 유지하고, 소분류 내부 검증에서만 실거래 지표를 제한적으로 사용한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    for name in [
        "phase149_rtms_registered_date_coverage.csv",
        "phase149_realestate_rtms_candidate_detail.csv",
        "phase149_realestate_rtms_candidate_overall.csv",
        "phase149_realestate_rtms_candidate_city.csv",
        "phase149_realestate_rtms_candidate_best_by_vintage.csv",
        "execution_manifest.json",
    ]:
        print(f"Wrote {(OUT / name).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
