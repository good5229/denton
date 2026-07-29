#!/usr/bin/env python3
"""Phase244 multi-source construction activity route audit.

Uses only fully available sources at this point:
- CALS annual construction contracts (road/river public SOC)
- Seoul redevelopment project file (start-date units)
- BuildingHUB top5 permit/start/approval events already collected

PPS contract rows are intentionally not used yet because full 2021~2023
collection is large and incomplete in the current cache.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase244_construction_multi_source_activity_route"
NOUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase244_construction_multi_source_activity_route.md"

ERR = NOUT / "annual_sigungu_activity_error_audit.csv"
CALS = ROOT / "data" / "processed" / "phase241_cals_construction_contract_rows.csv"
SEOUL_REDEV = ROOT / "data" / "raw" / "phase241_seoul_redevelopment" / "seoul_redevelopment_oa22856_seq1.xlsx"
BH = ROOT / "data" / "processed" / "buildinghub_priority_events_phase239_top5_construction.csv"

PROVINCE_NAMES = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "강원도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]


def normalize_province(name: str) -> str:
    x = str(name or "").strip()
    if x == "강원도":
        return "강원특별자치도"
    if x == "전라북도":
        return "전북특별자치도"
    return x


def parse_region(text: object) -> tuple[str, str]:
    s = str(text or "").strip()
    if not s or s.lower() == "nan":
        return "", ""
    province = ""
    for p in PROVINCE_NAMES:
        if s.startswith(p):
            province = normalize_province(p)
            rest = s[len(p) :].strip()
            break
    else:
        return "", ""
    # Keep first city/county/district token.  This is conservative and avoids
    # inventing lower-level locations from free text.
    m = re.search(r"([가-힣A-Za-z0-9]+(?:시|군|구))", rest)
    city = m.group(1) if m else ""
    if province == "세종특별자치시" and not city:
        city = "세종특별자치시"
    return province, city


def metric(df: pd.DataFrame, pred_col: str = "candidate_predicted_eok") -> dict[str, float | int]:
    actual = df["actual_eok"].astype(float)
    pred = df[pred_col].astype(float)
    abs_err = (pred - actual).abs()
    ape = np.where(actual.abs().gt(0), abs_err / actual.abs() * 100, np.nan)
    denom = actual.abs().sum()
    return {
        "rows": int(len(df)),
        "actual_sum_eok": float(actual.sum()),
        "abs_error_sum_eok": float(abs_err.sum()),
        "wape_pct": float(abs_err.sum() / denom * 100) if denom else np.nan,
        "over10_cells": int((ape > 10).sum()),
        "over20_cells": int((ape > 20).sum()),
        "max_ape_pct": float(np.nanmax(ape)) if len(ape) else np.nan,
    }


def md_table(df: pd.DataFrame, max_rows: int | None = None, digits: int = 3) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{v:,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = ["| " + " | ".join(x.columns) + " |", "| " + " | ".join(["---"] * len(x.columns)) + " |"]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def base_frame() -> pd.DataFrame:
    err = pd.read_csv(ERR)
    x = err[(err["activity"].eq("건설업")) & (err["year"].between(2021, 2023)) & (err["actual_eok"].gt(0))].copy()
    # parent total = actual province construction total; baseline share = current predicted share.
    prov = (
        x.groupby(["quarter_region", "year"], as_index=False)
        .agg(sido_actual_eok=("actual_eok", "sum"), sido_predicted_eok=("predicted_eok", "sum"))
    )
    x = x.merge(prov, on=["quarter_region", "year"], how="left")
    x["current_share"] = x["predicted_eok"] / x["sido_predicted_eok"]
    x["baseline_parent_predicted_eok"] = x["sido_actual_eok"] * x["current_share"]
    return x


def cals_signal() -> pd.DataFrame:
    if not CALS.exists():
        return pd.DataFrame(columns=["province_full", "city", "year", "cals_amount_eok"])
    c = pd.read_csv(CALS)
    c["year"] = pd.to_datetime(c.get("contract_stwrDt"), errors="coerce").dt.year
    c["amount_eok"] = pd.to_numeric(c.get("contract_totAmt"), errors="coerce").fillna(0) / 100_000_000
    parsed = c["pdznNm"].map(parse_region)
    c["province_full"] = parsed.map(lambda x: x[0])
    c["city"] = parsed.map(lambda x: x[1])
    c = c[c["year"].between(2021, 2023) & c["province_full"].ne("") & c["city"].ne("") & c["amount_eok"].gt(0)].copy()
    return c.groupby(["province_full", "city", "year"], as_index=False).agg(cals_amount_eok=("amount_eok", "sum"))


def seoul_redevelopment_signal() -> pd.DataFrame:
    if not SEOUL_REDEV.exists():
        return pd.DataFrame(columns=["province_full", "city", "year", "redevelopment_units"])
    df = pd.read_excel(SEOUL_REDEV, header=4)
    if "착공일" not in df.columns:
        return pd.DataFrame(columns=["province_full", "city", "year", "redevelopment_units"])
    df["year"] = pd.to_datetime(df["착공일"], errors="coerce").dt.year
    units = pd.to_numeric(df.get("건립세대수_총합계"), errors="coerce").fillna(0)
    demo = pd.to_numeric(df.get("기존가구수(멸실량)"), errors="coerce").fillna(0)
    df["redevelopment_units"] = np.maximum(units, demo)
    df["province_full"] = "서울특별시"
    df["city"] = df["자치구"].astype(str).str.strip()
    df = df[df["year"].between(2021, 2023) & df["redevelopment_units"].gt(0)].copy()
    return df.groupby(["province_full", "city", "year"], as_index=False).agg(redevelopment_units=("redevelopment_units", "sum"))


def buildinghub_signal() -> pd.DataFrame:
    if not BH.exists():
        return pd.DataFrame(columns=["province_full", "city", "year", "buildinghub_area"])
    b = pd.read_csv(BH)
    # Prefer construction activity dates: start, then approval, then permit.
    for col in ["start_date", "approval_date", "permit_date"]:
        if col not in b.columns:
            b[col] = pd.NaT
        b[col] = pd.to_datetime(b[col], errors="coerce")
    b["event_date"] = b["start_date"].fillna(b["approval_date"]).fillna(b["permit_date"])
    b["year"] = b["event_date"].dt.year
    b["buildinghub_area"] = pd.to_numeric(b.get("total_floor_area"), errors="coerce").fillna(0)
    b = b[b["year"].between(2021, 2023) & b["buildinghub_area"].gt(0)].copy()
    return b.groupby(["province_full", "city", "year"], as_index=False).agg(buildinghub_area=("buildinghub_area", "sum"))


def add_signal_share(base: pd.DataFrame, signal: pd.DataFrame, value_col: str, share_col: str) -> pd.DataFrame:
    x = base.merge(signal, on=["province_full", "city", "year"], how="left")
    x[value_col] = x[value_col].fillna(0.0)
    total = x.groupby(["province_full", "year"])[value_col].transform("sum")
    x[share_col] = np.where(total.gt(0), x[value_col] / total, np.nan)
    return x


def evaluate_candidates(x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    signal_cols = [
        ("cals_share", "CALS 공공/SOC 계약금액"),
        ("redevelopment_share", "서울 정비사업 착공세대"),
        ("buildinghub_share", "BuildingHUB 건축면적"),
    ]
    rows = []
    details = []
    scenarios = [("baseline_parent_control", {}, 0.0)]
    for col, label in signal_cols:
        for a in [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]:
            scenarios.append((f"{label} {a:.2f}", {col: a}, a))
    # limited combined route: small weights only
    for cals_a in [0.01, 0.02, 0.03, 0.05]:
        for redev_a in [0.01, 0.02, 0.03, 0.05]:
            for bh_a in [0.01, 0.02, 0.03]:
                scenarios.append((f"조합 cals{cals_a:.2f}_redevelop{redev_a:.2f}_bh{bh_a:.2f}", {"cals_share": cals_a, "redevelopment_share": redev_a, "buildinghub_share": bh_a}, cals_a + redev_a + bh_a))
    for name, weights, total_alpha in scenarios:
        d = x.copy()
        raw = d["current_share"].copy()
        # For each province-year, only apply a signal where that signal has a
        # positive province-year total.  Missing signals keep the current share.
        applied_alpha = pd.Series(0.0, index=d.index)
        raw = d["current_share"].astype(float).copy()
        for share_col, alpha in weights.items():
            has_signal = d[share_col].notna()
            raw = np.where(has_signal, raw + alpha * (d[share_col].fillna(0) - d["current_share"]), raw)
            applied_alpha = np.where(has_signal, applied_alpha + alpha, applied_alpha)
        raw = pd.Series(raw, index=d.index).clip(lower=0)
        share_sum = raw.groupby([d["province_full"], d["year"]]).transform("sum")
        d["candidate_share"] = np.where(share_sum.gt(0), raw / share_sum, d["current_share"])
        d["candidate_predicted_eok"] = d["sido_actual_eok"] * d["candidate_share"]
        d["candidate_abs_error_eok"] = (d["candidate_predicted_eok"] - d["actual_eok"]).abs()
        d["candidate_ape_pct"] = np.where(d["actual_eok"].gt(0), d["candidate_abs_error_eok"] / d["actual_eok"] * 100, np.nan)
        m = metric(d)
        m["scenario"] = name
        m["weight_sum"] = float(total_alpha)
        m["signal_cells"] = int((applied_alpha > 0).sum())
        rows.append(m)
        d["scenario"] = name
        details.append(d[["scenario", "province_full", "city", "year", "actual_eok", "baseline_parent_predicted_eok", "candidate_predicted_eok", "candidate_abs_error_eok", "candidate_ape_pct", "cals_amount_eok", "redevelopment_units", "buildinghub_area"]].copy())
    summary = pd.DataFrame(rows).sort_values(["wape_pct", "over10_cells", "over20_cells", "max_ape_pct"])
    detail = pd.concat(details, ignore_index=True)
    return summary, detail


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    base = base_frame()
    base_metric = metric(base.rename(columns={"baseline_parent_predicted_eok": "candidate_predicted_eok"}))

    cals = cals_signal()
    redev = seoul_redevelopment_signal()
    bh = buildinghub_signal()
    x = add_signal_share(base, cals, "cals_amount_eok", "cals_share")
    x = add_signal_share(x, redev, "redevelopment_units", "redevelopment_share")
    x = add_signal_share(x, bh, "buildinghub_area", "buildinghub_share")
    for col in ["cals_amount_eok", "redevelopment_units", "buildinghub_area"]:
        x[col] = x[col].fillna(0.0)

    summary, detail = evaluate_candidates(x)
    current = summary[summary["scenario"].eq("baseline_parent_control")].iloc[0]
    safe = summary[
        summary["scenario"].ne("baseline_parent_control")
        & summary["wape_pct"].lt(float(current["wape_pct"]))
        & summary["over10_cells"].le(int(current["over10_cells"]))
        & summary["over20_cells"].le(int(current["over20_cells"]))
        & summary["max_ape_pct"].le(float(current["max_ape_pct"]))
    ].copy()

    # Stronger local guardrail: among cities where a candidate changes at least
    # one year materially, city-level WAPE must not worsen.
    city_base = (
        detail[detail["scenario"].eq("baseline_parent_control")]
        .assign(abs_err=lambda d: (d["baseline_parent_predicted_eok"] - d["actual_eok"]).abs())
        .groupby(["province_full", "city"], as_index=False)
        .agg(base_actual=("actual_eok", "sum"), base_abs=("abs_err", "sum"))
    )
    city_base["base_wape"] = city_base["base_abs"] / city_base["base_actual"] * 100
    local_rows = []
    for scen in safe["scenario"].head(20):
        d = detail[detail["scenario"].eq(scen)].copy()
        d["abs_err"] = (d["candidate_predicted_eok"] - d["actual_eok"]).abs()
        g = d.groupby(["province_full", "city"], as_index=False).agg(actual=("actual_eok", "sum"), abs_err=("abs_err", "sum"))
        g["wape"] = g["abs_err"] / g["actual"] * 100
        g = g.merge(city_base, on=["province_full", "city"], how="left")
        g["worsened"] = g["wape"] > g["base_wape"] + 1e-9
        local_rows.append({"scenario": scen, "worsened_cities": int(g["worsened"].sum()), "max_city_wape_increase": float((g["wape"] - g["base_wape"]).max())})
    local_guard = pd.DataFrame(local_rows)
    if not local_guard.empty:
        safe = safe.merge(local_guard, on="scenario", how="left")
        strict_safe = safe[safe["worsened_cities"].eq(0)].copy()
    else:
        strict_safe = safe.copy()

    summary.to_csv(OUT / "phase244_candidate_summary.csv", index=False, encoding="utf-8-sig")
    safe.to_csv(OUT / "phase244_guardrail_safe_candidates.csv", index=False, encoding="utf-8-sig")
    strict_safe.to_csv(OUT / "phase244_strict_safe_candidates.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT / "phase244_candidate_detail.csv", index=False, encoding="utf-8-sig")
    cals.to_csv(OUT / "phase244_cals_signal.csv", index=False, encoding="utf-8-sig")
    redev.to_csv(OUT / "phase244_seoul_redevelopment_signal.csv", index=False, encoding="utf-8-sig")
    bh.to_csv(OUT / "phase244_buildinghub_signal.csv", index=False, encoding="utf-8-sig")

    best = summary.iloc[0]
    best_safe = safe.iloc[0] if not safe.empty else None
    best_strict = strict_safe.iloc[0] if not strict_safe.empty else None

    source_summary = pd.DataFrame(
        [
            {"source": "CALS 공공/SOC 계약", "rows": len(cals), "signal_city_years": len(cals), "amount_or_units_sum": cals["cals_amount_eok"].sum() if not cals.empty else 0},
            {"source": "서울 정비사업 착공", "rows": len(redev), "signal_city_years": len(redev), "amount_or_units_sum": redev["redevelopment_units"].sum() if not redev.empty else 0},
            {"source": "BuildingHUB top5", "rows": len(bh), "signal_city_years": len(bh), "amount_or_units_sum": bh["buildinghub_area"].sum() if not bh.empty else 0},
        ]
    )

    report = f"""# Phase244 건설업 다중 공개활동자료 route 검증

생성시각: {datetime.now().astimezone().isoformat(timespec='seconds')}

## 결론

새로 확보한 자료 중 즉시 전기간 검증 가능한 `CALS 공공/SOC 계약`, `서울 도시정비사업`, 기존 `BuildingHUB top5`를 결합해 건설업 시군구 공간배분을 다시 점검했다.

- 기준선: 시도 건설업 actual 총량은 맞추고 기존 시군구 share 사용
- 후보: 기준선 share에 활동자료 share를 1~20% 범위로 소량 혼합
- 검증: 2021~2023년 시군구×건설업 actual에 집계 비교
- 조달청 계약정보는 API가 열렸지만 3년 전량 수집량이 매우 커서 이번 채택 검증에서는 제외했다. 현재 캐시는 2021년 1월 전체와 2021년 2월 일부다.

## 1. 자료 신호 규모

{md_table(source_summary, digits=2)}

## 2. 전체 후보 성능 상위

{md_table(summary[["scenario", "rows", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct", "signal_cells"]].head(15), digits=3)}

## 3. Guardrail 통과 후보

조건: 기준선보다 WAPE가 낮고, 10% 초과 셀·20% 초과 셀·최대오차율이 악화되지 않는 후보.

{md_table(safe[["scenario", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct", "worsened_cities", "max_city_wape_increase"]].head(15), digits=3) if not safe.empty else "_없음_"}

## 4. 시군구별 WAPE 악화까지 금지한 엄격 후보

조건: 위 Guardrail에 더해, 후보가 영향을 준 도시의 2021~2023 합산 WAPE가 하나도 악화되지 않을 것.

{md_table(strict_safe[["scenario", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct", "worsened_cities", "max_city_wape_increase"]].head(15), digits=3) if not strict_safe.empty else "_없음_"}

## 5. 판정

| 항목 | 값 |
| --- | ---: |
| 기준 WAPE | {float(current['wape_pct']):.3f}% |
| 단순 최선 후보 WAPE | {float(best['wape_pct']):.3f}% |
| Guardrail 최선 후보 | {str(best_safe['scenario']) if best_safe is not None else '없음'} |
| Guardrail 최선 WAPE | {f"{float(best_safe['wape_pct']):.3f}%" if best_safe is not None else '없음'} |
| 엄격 후보 | {str(best_strict['scenario']) if best_strict is not None else '없음'} |
| 엄격 후보 WAPE | {f"{float(best_strict['wape_pct']):.3f}%" if best_strict is not None else '없음'} |

현재 즉시 사용 가능한 자료만으로는 건설업 시군구 WAPE 10% 목표에 도달하지 못한다. 다만 CALS/서울정비사업/BuildingHUB는 보조 신호로서 일부 WAPE를 낮추는 후보가 존재한다. 운영 route로 채택하려면 조달청 계약정보 전량과 LH 공고를 기간 필터가 검증된 형태로 수집한 뒤, 같은 guardrail을 다시 적용해야 한다.

## 6. 산출물

- `data/processed/phase244_construction_multi_source_activity_route/phase244_candidate_summary.csv`
- `data/processed/phase244_construction_multi_source_activity_route/phase244_guardrail_safe_candidates.csv`
- `data/processed/phase244_construction_multi_source_activity_route/phase244_strict_safe_candidates.csv`
- `data/processed/phase244_construction_multi_source_activity_route/phase244_candidate_detail.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(summary.head(5).to_string(index=False))
    print("safe", len(safe), "strict_safe", len(strict_safe))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
