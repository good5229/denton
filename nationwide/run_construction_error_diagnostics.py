#!/usr/bin/env python3
"""Diagnose remaining construction GVA errors and prioritize BuildingHUB collection.

This script does not tune a model.  It identifies where the construction
sigungu error is concentrated so the next data collection can target the
smallest useful set of regions before attempting a nationwide BuildingHUB pull.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "nationwide" / "construction_error_diagnostics.md"
ERR = OUT / "annual_sigungu_activity_error_audit.csv"
LEGAL = ROOT / "data" / "processed" / "buildinghub_legal_dong_request_universe.csv"
LOCAL_EVENTS = ROOT / "data" / "processed" / "partial_stats_phase52_building_permit_events_goyang_pohang.csv"


def wape(frame: pd.DataFrame) -> float:
    denom = frame["actual_eok"].abs().sum()
    return float(frame["abs_error_eok"].sum() / denom * 100) if denom else np.nan


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    aligns = []
    for _, label in cols:
        aligns.append("---:" if any(token in label for token in ["억원", "%", "개", "비중", "WAPE", "순위"]) else "---")
    lines.append("| " + " | ".join(aligns) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            value = row.get(key, "")
            if isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}")
            elif isinstance(value, (int, np.integer)):
                vals.append(f"{value:,}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def normalize_sigungu_name(name: str) -> str:
    return str(name).replace(" ", "").strip()


def read_csv_fallback(path: Path, **kwargs) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return pd.read_csv(path, **kwargs)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    err = pd.read_csv(ERR)
    c = err[err["activity"].eq("건설업")].copy()
    c = c[c["actual_eok"].gt(0)].copy()
    c["abs_error_share_pct"] = c["abs_error_eok"] / c["abs_error_eok"].sum() * 100
    c["large_actual"] = c["actual_eok"].ge(1000)
    total_wape = wape(c)
    large = c[c["large_actual"]].copy()
    large_wape = wape(large)

    by_year = (
        c.groupby("year", as_index=False)
        .agg(rows=("city", "count"), actual_sum_eok=("actual_eok", "sum"), abs_error_sum_eok=("abs_error_eok", "sum"), over10_cells=("ape_pct", lambda s: int((s > 10).sum())), over20_cells=("ape_pct", lambda s: int((s > 20).sum())), max_ape_pct=("ape_pct", "max"))
        .sort_values("year")
    )
    by_year["wape_pct"] = by_year["abs_error_sum_eok"] / by_year["actual_sum_eok"] * 100

    by_prov = (
        c.groupby(["quarter_region", "province_full"], as_index=False)
        .agg(rows=("city", "count"), years=("year", "nunique"), actual_sum_eok=("actual_eok", "sum"), abs_error_sum_eok=("abs_error_eok", "sum"), over10_cells=("ape_pct", lambda s: int((s > 10).sum())), over20_cells=("ape_pct", lambda s: int((s > 20).sum())), max_ape_pct=("ape_pct", "max"))
    )
    by_prov["wape_pct"] = by_prov["abs_error_sum_eok"] / by_prov["actual_sum_eok"] * 100
    by_prov["abs_error_share_pct"] = by_prov["abs_error_sum_eok"] / by_prov["abs_error_sum_eok"].sum() * 100
    by_prov = by_prov.sort_values("abs_error_sum_eok", ascending=False)

    by_city = (
        c.groupby(["quarter_region", "province_full", "city"], as_index=False)
        .agg(years=("year", "nunique"), actual_sum_eok=("actual_eok", "sum"), abs_error_sum_eok=("abs_error_eok", "sum"), over10_cells=("ape_pct", lambda s: int((s > 10).sum())), over20_cells=("ape_pct", lambda s: int((s > 20).sum())), max_ape_pct=("ape_pct", "max"))
    )
    by_city["wape_pct"] = by_city["abs_error_sum_eok"] / by_city["actual_sum_eok"] * 100
    by_city["abs_error_share_pct"] = by_city["abs_error_sum_eok"] / by_city["abs_error_sum_eok"].sum() * 100
    by_city = by_city.sort_values("abs_error_sum_eok", ascending=False)
    by_city["cum_abs_error_share_pct"] = by_city["abs_error_share_pct"].cumsum()
    by_city["priority_rank"] = np.arange(1, len(by_city) + 1)

    top_cells = c.sort_values("abs_error_eok", ascending=False).head(50).copy()
    top_cells["direction"] = np.where(top_cells["predicted_eok"] > top_cells["actual_eok"], "과대", "과소")

    # BuildingHUB collection burden by target city.
    legal = read_csv_fallback(LEGAL)
    legal["norm_city"] = legal["sigungu_name"].map(normalize_sigungu_name)
    # The locally built legal-dong universe keeps many rows as
    # ``abolished_or_unknown`` because the source text did not expose a clean
    # current/abolished flag.  The Phase52 collector therefore used the
    # request universe without filtering by this flag.  Use the same rule here:
    # estimate request burden from distinct request keys, not from the
    # uncertain abolished flag.
    legal_count = (
        legal.groupby(["sido_name", "sigungu_name"], as_index=False)
        .agg(active_legal_dong_requests=("request_key", "nunique"))
    )
    legal_count["norm_city"] = legal_count["sigungu_name"].map(normalize_sigungu_name)
    priority = by_city.merge(
        legal_count[["sido_name", "sigungu_name", "norm_city", "active_legal_dong_requests"]],
        left_on=["province_full", by_city["city"].map(normalize_sigungu_name)],
        right_on=["sido_name", "norm_city"],
        how="left",
    ).drop(columns=["key_1"], errors="ignore")
    priority["active_legal_dong_requests"] = priority["active_legal_dong_requests"].fillna(0).astype(int)
    priority["collection_priority"] = np.select(
        [
            priority["cum_abs_error_share_pct"].le(50),
            priority["cum_abs_error_share_pct"].le(70),
            priority["cum_abs_error_share_pct"].le(85),
        ],
        ["1차", "2차", "3차"],
        default="후순위",
    )
    priority = priority[["priority_rank", "collection_priority", "quarter_region", "province_full", "city", "years", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct", "active_legal_dong_requests", "cum_abs_error_share_pct"]]

    local_coverage = pd.DataFrame()
    if LOCAL_EVENTS.exists():
        ev = pd.read_csv(LOCAL_EVENTS, usecols=["city", "sigungu_cd", "bjdong_cd", "permit_register_pk"])
        local_coverage = (
            ev.groupby(["city"], as_index=False)
            .agg(raw_event_rows=("permit_register_pk", "count"), legal_dong_requests_observed=("bjdong_cd", "nunique"))
        )

    top_cells.to_csv(OUT / "construction_error_top_cells.csv", index=False, encoding="utf-8-sig")
    by_year.to_csv(OUT / "construction_error_by_year.csv", index=False, encoding="utf-8-sig")
    by_prov.to_csv(OUT / "construction_error_by_province.csv", index=False, encoding="utf-8-sig")
    by_city.to_csv(OUT / "construction_error_by_city.csv", index=False, encoding="utf-8-sig")
    priority.to_csv(OUT / "construction_buildinghub_collection_priority.csv", index=False, encoding="utf-8-sig")
    if not local_coverage.empty:
        local_coverage.to_csv(OUT / "construction_local_buildinghub_coverage.csv", index=False, encoding="utf-8-sig")

    first50 = int((priority["cum_abs_error_share_pct"] <= 50).sum())
    first70 = int((priority["cum_abs_error_share_pct"] <= 70).sum())
    first85 = int((priority["cum_abs_error_share_pct"] <= 85).sum())
    first50_req = int(priority.head(first50)["active_legal_dong_requests"].sum()) if first50 else 0
    first70_req = int(priority.head(first70)["active_legal_dong_requests"].sum()) if first70 else 0
    first85_req = int(priority.head(first85)["active_legal_dong_requests"].sum()) if first85 else 0

    lines = [
        "# 건설업 시군구 오차 집중 진단 및 건축HUB 수집 우선순위",
        "",
        "## 결론",
        "",
        f"- 현재 건설업 전체 시군구 WAPE는 {total_wape:.2f}%이고, actual 1,000억원 이상 셀 기준 WAPE는 {large_wape:.2f}%다.",
        "- 남은 오차는 모든 지역에 균등하게 퍼진 문제가 아니라 일부 시군구·연도 대형 셀에 집중되어 있다.",
        "- 따라서 전국 건축HUB 전량 수집 전에, 오차 기여 상위 시군구부터 허가·착공·사용승인 event를 확장 수집하는 staged 방식이 합리적이다.",
        "- 이 진단은 모델 가중치 선택이 아니라 수집 우선순위 산정이므로 target-year actual을 예측식에 넣지 않는다.",
        "",
        "## 연도별 건설업 오차",
        "",
        md_table(by_year, [("year", "연도"), ("rows", "셀 개수"), ("actual_sum_eok", "실제합_억원"), ("abs_error_sum_eok", "절대오차합_억원"), ("wape_pct", "WAPE_%"), ("over10_cells", "10%초과"), ("over20_cells", "20%초과"), ("max_ape_pct", "최대APE_%")]),
        "",
        "## 시도별 오차 기여 상위",
        "",
        md_table(by_prov, [("province_full", "시도"), ("rows", "셀 개수"), ("actual_sum_eok", "실제합_억원"), ("abs_error_sum_eok", "절대오차합_억원"), ("wape_pct", "WAPE_%"), ("abs_error_share_pct", "오차기여_%"), ("over10_cells", "10%초과"), ("max_ape_pct", "최대APE_%")], 15),
        "",
        "## 시군구 수집 우선순위 상위",
        "",
        md_table(priority, [("priority_rank", "순위"), ("collection_priority", "수집단계"), ("province_full", "시도"), ("city", "시군구"), ("actual_sum_eok", "실제합_억원"), ("abs_error_sum_eok", "절대오차합_억원"), ("wape_pct", "WAPE_%"), ("active_legal_dong_requests", "법정동요청_개"), ("cum_abs_error_share_pct", "누적오차기여_%")], 30),
        "",
        "## 수집량 추정",
        "",
        f"- 오차기여 50%까지: 상위 {first50}개 시군구, 법정동 요청 약 {first50_req:,}개",
        f"- 오차기여 70%까지: 상위 {first70}개 시군구, 법정동 요청 약 {first70_req:,}개",
        f"- 오차기여 85%까지: 상위 {first85}개 시군구, 법정동 요청 약 {first85_req:,}개",
        "",
        "## 현재 로컬 건축HUB event coverage",
        "",
        md_table(local_coverage, [("city", "도시"), ("raw_event_rows", "event 행"), ("legal_dong_requests_observed", "관측 법정동")]) if not local_coverage.empty else "- 로컬 event coverage 파일 없음\n",
        "",
        "## 다음 실험 제안",
        "",
        "1. 수집 1차: 오차기여 50% 내 시군구만 건축HUB 허가·착공·사용승인 event 수집",
        "2. 후보식: 기존 시군구 건설업 share + 착공/사용승인 면적 share + PPS 금액 share의 소량 혼합",
        "3. 선택규칙: 과거연도 rolling 검증으로만 가중치 선택",
        "4. 채택기준: WAPE, 10% 초과 셀, 20% 초과 셀, 최대 APE, 대형 actual 셀 절대오차가 모두 기준보다 악화되지 않을 것",
        "5. 실패 시: 재건축·재개발 단계, 대형 민간개발, 토목 사업예산을 별도 부문으로 추가",
        "",
        "## 산출 파일",
        "",
        "- `nationwide/outputs/construction_error_top_cells.csv`",
        "- `nationwide/outputs/construction_error_by_year.csv`",
        "- `nationwide/outputs/construction_error_by_province.csv`",
        "- `nationwide/outputs/construction_error_by_city.csv`",
        "- `nationwide/outputs/construction_buildinghub_collection_priority.csv`",
        "- `nationwide/outputs/construction_local_buildinghub_coverage.csv`",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(REPORT)
    print(OUT / "construction_buildinghub_collection_priority.csv")


if __name__ == "__main__":
    main()
