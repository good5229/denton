#!/usr/bin/env python3
"""Phase255: residual priority audit for sigungu annual GVA validation.

This is not a new forecasting route.  It summarizes where the remaining
sigungu×activity errors are concentrated in the public annual actual window,
so subsequent collection work can target the largest bottlenecks without
pretending that unpublished 2015~2025 sigungu actuals exist.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase255_sigungu_residual_priority_audit.md"
SOURCE = OUT / "annual_sigungu_activity_error_audit.csv"
OVER10_LARGE = OUT / "annual_sigungu_activity_over_10pct_errors_actual_ge_1000eok.csv"
SCENARIOS = OUT / "minimal_activity_routing_sigungu_scenarios.csv"
CREATED_AT = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


DATA_NEEDS = {
    "건설업": {
        "priority": "최상",
        "needed_data": "건축허가·착공·사용승인 면적, 정비사업 단계, 공공공사 계약·공고 완전월",
        "current_status": "PPS는 429로 blocked/partial, 건축HUB 전량 수집 미완료",
        "guardrail": "완전월·완전연도만 사용, target-year actual 미사용 rolling 선택, WAPE·10/20%초과·max APE 비악화",
    },
    "운수 및 창고업": {
        "priority": "상",
        "needed_data": "항만·철도·화물 물동량, 대중교통 승하차, 창고·물류시설 인허가",
        "current_status": "일부 교통·물류 자료는 후보이나 전국 시군구×연도 완전 route는 미확정",
        "guardrail": "여객/화물/창고를 분리한 뒤 상위 운수창고 actual로 재집계 검증",
    },
    "정보통신업": {
        "priority": "상",
        "needed_data": "통신·데이터센터·방송·콘텐츠 사업장 규모, ICT 사업체 매출/고용 보조자료",
        "current_status": "전국 지역 차원의 직접 활동자료 부족",
        "guardrail": "대형사업장 편중 지역을 별도 진단하고 서비스업생산지수 단독 공간배분 금지",
    },
    "광업, 제조업": {
        "priority": "상",
        "needed_data": "시군구 제조업 세부 사업체/종사자, 공장등록, 제조업 세부 생산지수, 전력사용량",
        "current_status": "시도 제조업 지수는 있으나 시군구 세부 생산활동 직접자료 부족",
        "guardrail": "광업+제조업 결합 actual 한계를 명시하고 중분류/소분류 합산 검증으로 제한",
    },
    "숙박 및 음식점업": {
        "priority": "중",
        "needed_data": "숙박 객실·관광객·음식점 인허가/폐업·지역 방문객",
        "current_status": "전국 월별 서비스 지수는 시간경로 후보일 뿐 시군구 공간배분 근거 아님",
        "guardrail": "관광/상권 자료의 공표시점 확인 후 out-of-year 검증",
    },
    "문화 및 기타서비스업": {
        "priority": "중",
        "needed_data": "공연·영화·체육시설·개인서비스 사업체 활동자료",
        "current_status": "세부 활동자료 coverage가 지역별로 불균형",
        "guardrail": "지역 편중 자료는 해당 지역 후보로만 두고 전국 일반화 금지",
    },
}


def md_table(df: pd.DataFrame, limit: int | None = None, digits: int = 2) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if c == "year":
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else str(int(v)))
        elif pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{float(v):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = [
        "| " + " | ".join(x.columns) + " |",
        "| " + " | ".join(["---"] * len(x.columns)) + " |",
    ]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def summarize(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    def min_nonempty(s: pd.Series) -> str:
        v = s.fillna("").astype(str)
        v = v[v.ne("")]
        return "" if v.empty else str(v.min())

    def max_nonempty(s: pd.Series) -> str:
        v = s.fillna("").astype(str)
        v = v[v.ne("")]
        return "" if v.empty else str(v.max())

    g = (
        df.groupby(keys, as_index=False)
        .agg(
            rows=("actual_eok", "size"),
            years=("year", "nunique"),
            province_count=("province_full", "nunique"),
            city_count=("sigungu_unit", "nunique"),
            actual_sum_eok=("actual_eok", "sum"),
            predicted_sum_eok=("predicted_eok", "sum"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            max_ape_pct=("ape_pct", "max"),
            over10_cells=("ape_pct", lambda s: int((s > 10).sum())),
            over20_cells=("ape_pct", lambda s: int((s > 20).sum())),
            large_actual_over10_cells=("large_actual_over10", "sum"),
            latest_change_min=("source_release_date", min_nonempty),
            latest_change_max=("source_release_date", max_nonempty),
        )
    )
    g["wape_pct"] = np.where(g["actual_sum_eok"].abs().gt(0), g["abs_error_sum_eok"] / g["actual_sum_eok"].abs() * 100, np.nan)
    g["signed_error_sum_eok"] = g["predicted_sum_eok"] - g["actual_sum_eok"]
    return g


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not SOURCE.exists():
        raise SystemExit(f"missing {SOURCE}")
    df = pd.read_csv(SOURCE)
    for c in ["predicted_eok", "actual_eok", "abs_error_eok", "ape_pct"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df[df["year"].notna() & df["actual_eok"].notna() & df["actual_eok"].abs().gt(0)].copy()
    df["year"] = df["year"].astype(int)
    df["large_actual_over10"] = (df["actual_eok"].abs().ge(1000) & df["ape_pct"].gt(10)).astype(int)
    df["source_release_date"] = df["latest_change_date"].astype(str).where(
        df["latest_change_date"].astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}"),
        "",
    )
    df["sigungu_unit"] = df["province_full"].fillna("").astype(str) + " " + df["city"].fillna("").astype(str)

    if OVER10_LARGE.exists():
        large = pd.read_csv(OVER10_LARGE)
    else:
        large = df[df["large_actual_over10"].eq(1)].copy()
    return df, large


def scenario_delta() -> pd.DataFrame:
    if not SCENARIOS.exists():
        return pd.DataFrame()
    sc = pd.read_csv(SCENARIOS)
    if sc.empty or "scenario" not in sc:
        return pd.DataFrame()
    base = sc[sc["scenario"].eq("strict_baseline")][["activity", "wape_pct", "over10_cells", "over20_cells"]].copy()
    cand = sc[sc["scenario"].eq("parent_control_all_activities")][["activity", "wape_pct", "over10_cells", "over20_cells"]].copy()
    if base.empty or cand.empty:
        return pd.DataFrame()
    out = base.merge(cand, on="activity", suffixes=("_baseline", "_parent_control"))
    out["delta_wape_pp"] = out["wape_pct_parent_control"] - out["wape_pct_baseline"]
    out["delta_over10_cells"] = out["over10_cells_parent_control"] - out["over10_cells_baseline"]
    out["delta_over20_cells"] = out["over20_cells_parent_control"] - out["over20_cells_baseline"]
    return out.sort_values(["delta_wape_pp", "activity"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df, large = load_inputs()

    total_abs = float(df["abs_error_eok"].sum())
    activity = summarize(df, ["activity"]).sort_values("abs_error_sum_eok", ascending=False)
    activity["abs_error_contribution_pct"] = activity["abs_error_sum_eok"] / total_abs * 100
    activity["priority_score"] = (
        activity["abs_error_contribution_pct"]
        + activity["wape_pct"].clip(upper=50) * 0.5
        + activity["large_actual_over10_cells"] / max(activity["large_actual_over10_cells"].max(), 1) * 10
    )
    activity = activity.sort_values("priority_score", ascending=False)

    province_activity = summarize(df, ["province_full", "activity"]).sort_values("abs_error_sum_eok", ascending=False)
    province_activity["abs_error_contribution_pct"] = province_activity["abs_error_sum_eok"] / total_abs * 100

    city_activity = summarize(df, ["province_full", "city", "activity"]).sort_values("abs_error_sum_eok", ascending=False)
    city_activity["abs_error_contribution_pct"] = city_activity["abs_error_sum_eok"] / total_abs * 100
    city_activity["cum_abs_error_sum_eok"] = city_activity["abs_error_sum_eok"].cumsum()
    city_activity["cum_abs_error_contribution_pct"] = city_activity["cum_abs_error_sum_eok"] / total_abs * 100
    frontier_rows: list[dict[str, object]] = []
    for threshold in [50, 70, 85, 90]:
        covered = city_activity[city_activity["cum_abs_error_contribution_pct"].le(threshold)]
        if covered.empty:
            n = 1
        else:
            n = min(len(covered) + 1, len(city_activity))
        take = city_activity.head(n)
        frontier_rows.append(
            {
                "cum_error_threshold_pct": threshold,
                "city_activity_cells_needed": int(len(take)),
                "province_count": int(take["province_full"].nunique()),
                "city_count": int((take["province_full"].astype(str) + " " + take["city"].astype(str)).nunique()),
                "activity_count": int(take["activity"].nunique()),
                "covered_abs_error_sum_eok": float(take["abs_error_sum_eok"].sum()),
                "covered_abs_error_pct": float(take["abs_error_sum_eok"].sum() / total_abs * 100),
                "top_activities": ", ".join(take.groupby("activity")["abs_error_sum_eok"].sum().sort_values(ascending=False).head(5).index),
            }
        )
    frontier = pd.DataFrame(frontier_rows)

    year_activity = summarize(df, ["year", "activity"]).sort_values(["year", "abs_error_sum_eok"], ascending=[True, False])
    year_activity["abs_error_contribution_pct"] = year_activity["abs_error_sum_eok"] / total_abs * 100

    top_cells = df.sort_values("abs_error_eok", ascending=False).head(120).copy()
    scenario = scenario_delta()

    data_needs = pd.DataFrame(
        [
            {
                "activity": activity_name,
                **meta,
            }
            for activity_name, meta in DATA_NEEDS.items()
        ]
    )
    priority_order = {"최상": 0, "상": 1, "중": 2, "하": 3}
    data_needs["priority_rank"] = data_needs["priority"].map(priority_order).fillna(9).astype(int)
    data_needs = data_needs.merge(
        activity[["activity", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "large_actual_over10_cells", "abs_error_contribution_pct"]],
        on="activity",
        how="left",
    ).sort_values(["priority_rank", "abs_error_sum_eok"], ascending=[True, False])

    coverage = (
        df.groupby(["year"], as_index=False)
        .agg(
            rows=("activity", "size"),
            province_count=("province_full", "nunique"),
            city_count=("sigungu_unit", "nunique"),
            activity_count=("activity", "nunique"),
            latest_change_min=("source_release_date", lambda s: "" if s.fillna("").astype(str).eq("").all() else s[s.fillna("").astype(str).ne("")].min()),
            latest_change_max=("source_release_date", lambda s: "" if s.fillna("").astype(str).eq("").all() else s[s.fillna("").astype(str).ne("")].max()),
        )
        .sort_values("year")
    )

    activity.to_csv(OUT / "phase255_residual_priority_by_activity.csv", index=False, encoding="utf-8-sig")
    province_activity.to_csv(OUT / "phase255_residual_priority_by_province_activity.csv", index=False, encoding="utf-8-sig")
    city_activity.to_csv(OUT / "phase255_residual_priority_by_city_activity.csv", index=False, encoding="utf-8-sig")
    frontier.to_csv(OUT / "phase255_residual_priority_cumulative_frontier.csv", index=False, encoding="utf-8-sig")
    year_activity.to_csv(OUT / "phase255_residual_priority_by_year_activity.csv", index=False, encoding="utf-8-sig")
    top_cells.to_csv(OUT / "phase255_residual_priority_top_cells.csv", index=False, encoding="utf-8-sig")
    data_needs.to_csv(OUT / "phase255_residual_priority_data_needs.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(OUT / "phase255_residual_priority_actual_coverage.csv", index=False, encoding="utf-8-sig")
    if not scenario.empty:
        scenario.to_csv(OUT / "phase255_residual_priority_scenario_delta.csv", index=False, encoding="utf-8-sig")

    top_activity = activity.head(8).copy()
    top_province_activity = province_activity.head(15).copy()
    top_city_activity = city_activity.head(15).copy()
    large_summary = (
        large.groupby("activity", as_index=False)
        .agg(
            large_over10_rows=("activity", "size"),
            actual_sum_eok=("actual_eok", "sum"),
            abs_error_sum_eok=("abs_error_eok", "sum"),
            max_ape_pct=("ape_pct", "max"),
        )
        .sort_values("abs_error_sum_eok", ascending=False)
        if not large.empty
        else pd.DataFrame()
    )

    report = f"""# Phase255 시군구×업종 잔여오차 우선순위 감사

생성시각: {CREATED_AT}

## 1. 목적

PPS 건설업 자료가 계속 `HTTP 429`로 blocked 상태이므로, 다음 개선은 무작정 새 route를 붙이는 방식이 아니라 공개 actual이 있는 시군구×업종 연간 검증 구간에서 잔여오차가 어디에 집중되는지 정량화하는 것부터 시작한다.

이 문서는 2015~2025 전체의 직접 시군구 actual 검증이 아니다. 현재 로컬에서 직접 검증 가능한 시군구 annual GVA actual 범위는 아래 표와 같고, 나머지 연도는 시도·전국 상위 actual 집계검증 또는 사후 backcast/운영 bridge로 분리해야 한다.

## 2. actual 공표 범위

{md_table(coverage, digits=0)}

## 3. 업종별 잔여오차 우선순위

표는 절대오차 기여도, WAPE, actual 1,000억원 이상 10% 초과 셀을 함께 본 운영 우선순위 점수로 정렬했다. `city_count`는 같은 구 이름 중복을 합치지 않은 `시도×시군구명` 조합 수다.

{md_table(top_activity[["activity", "rows", "province_count", "city_count", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "large_actual_over10_cells", "abs_error_contribution_pct"]], digits=2)}

## 4. 시도×업종 오차 집중 상위

{md_table(top_province_activity[["province_full", "activity", "rows", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "abs_error_contribution_pct"]], digits=2)}

## 5. 시군구×업종 오차 집중 상위

{md_table(top_city_activity[["province_full", "city", "activity", "rows", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "abs_error_contribution_pct"]], digits=2)}

## 6. 누적오차 설명 frontier

시군구×업종 묶음을 절대오차 기여도순으로 정렬했을 때, 전체 잔여오차의 50/70/85/90%를 설명하는 데 필요한 묶음 수다. 이 표는 추가 자료 수집을 어디부터 시작해야 하는지 보여주는 우선순위 지도이며, 같은 셀에서 바로 성능개선을 주장하는 용도로 쓰지 않는다.

상위 오차 셀은 사후 진단용 표본이다. 해당 셀을 보고 선택한 자료·가중치·route의 개선폭을 같은 셀·같은 연도에서 성과로 보고하면 selection leakage다. 후보 route는 사전 고정한 뒤 out-of-year 또는 holdout 지역·연도에서 별도 검증한다.

{md_table(frontier, digits=2)}

## 7. 대형 actual 셀 기준 10% 초과 업종

actual 1,000억원 이상이면서 APE 10%를 초과한 셀만 별도로 본다. 작은 분모 때문에 생기는 과장된 상대오차를 줄이고, 실제 정책·경제 규모가 큰 병목을 우선하기 위한 표다.

{md_table(large_summary.head(10), digits=2)}

## 8. 기존 최소 route 실험의 시군구 효과

{md_table(scenario.head(12), digits=3) if not scenario.empty else "_기존 scenario 요약 없음_"}

## 9. 추가자료 후보와 guardrail

{md_table(data_needs[["activity", "priority", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "needed_data", "current_status", "guardrail"]], digits=2)}

## 10. 결론

1. 금액오차 기준으로는 광업·제조업과 건설업이 가장 큰 축이고, 상대오차·대형 over10 셀 기준으로는 건설업이 최우선 병목이다.
2. 운수 및 창고업, 정보통신업, 광업·제조업은 단순 계층배분만으로 일부 대형 시군구의 10% 초과 오차가 반복된다.
3. 숙박 및 음식점업과 문화·기타서비스업은 총량 기여는 중간이지만 지역 이벤트·관광·상권 충격을 반영할 자료가 있으면 보조 route 후보가 된다.
4. 추가자료는 `완전월/완전연도 coverage`, `공표시점/vintage freeze`, `target-year actual 미사용`, `rolling out-of-year 선택`, `WAPE·10%초과·20%초과·max APE 비악화`를 통과하기 전까지 운영 산출물에 반영하지 않는다.
5. 지역별 누락률, 공표중단, 행정구역 변경, 대형사업장 편중 여부를 별도 coverage guardrail로 점검해야 한다.
6. 2015~2025 전체 목표에서 시군구 direct actual 검증은 공표범위상 제한되므로, 공개 actual 구간의 잔여오차 진단과 시도·전국 상위 집계검증을 분리해 보고해야 한다.

## 11. 산출물

- `nationwide/outputs/phase255_residual_priority_by_activity.csv`
- `nationwide/outputs/phase255_residual_priority_by_province_activity.csv`
- `nationwide/outputs/phase255_residual_priority_by_city_activity.csv`
- `nationwide/outputs/phase255_residual_priority_cumulative_frontier.csv`
- `nationwide/outputs/phase255_residual_priority_by_year_activity.csv`
- `nationwide/outputs/phase255_residual_priority_top_cells.csv`
- `nationwide/outputs/phase255_residual_priority_data_needs.csv`
- `nationwide/outputs/phase255_residual_priority_actual_coverage.csv`
- `nationwide/outputs/phase255_residual_priority_scenario_delta.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(activity.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
