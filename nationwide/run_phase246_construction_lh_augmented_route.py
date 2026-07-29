#!/usr/bin/env python3
"""Phase246 add LH public housing/land notice signal to construction route."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PH244 = ROOT / "data" / "processed" / "phase244_construction_multi_source_activity_route"
OUT = ROOT / "data" / "processed" / "phase246_construction_lh_augmented_route"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase246_construction_lh_augmented_route.md"
LH = ROOT / "data" / "processed" / "phase243_lh_notice_rows_202101_202312.csv"
ERR = ROOT / "nationwide" / "outputs" / "annual_sigungu_activity_error_audit.csv"


def normalize_province(x: object) -> str:
    s = str(x or "").replace(" 외", "").strip()
    if s == "강원도":
        return "강원특별자치도"
    if s == "전라북도":
        return "전북특별자치도"
    # LH currently has a merged display label; do not force it to one province.
    if s == "전남광주통합특별시":
        return ""
    return s


def short_city(city: str) -> str:
    c = str(city).strip()
    for suf in ["특례시", "자치시", "시", "군", "구"]:
        if c.endswith(suf) and len(c) > len(suf) + 1:
            return c[: -len(suf)]
    return c


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


def metric(df: pd.DataFrame, pred_col: str) -> dict[str, float | int]:
    actual = df["actual_eok"].astype(float)
    pred = df[pred_col].astype(float)
    abs_err = (pred - actual).abs()
    ape = np.where(actual.gt(0), abs_err / actual * 100, np.nan)
    return {
        "rows": int(len(df)),
        "actual_sum_eok": float(actual.sum()),
        "abs_error_sum_eok": float(abs_err.sum()),
        "wape_pct": float(abs_err.sum() / actual.sum() * 100),
        "over10_cells": int((ape > 10).sum()),
        "over20_cells": int((ape > 20).sum()),
        "max_ape_pct": float(np.nanmax(ape)),
    }


def base_frame() -> pd.DataFrame:
    err = pd.read_csv(ERR)
    x = err[(err["activity"].eq("건설업")) & (err["year"].between(2021, 2023)) & (err["actual_eok"].gt(0))].copy()
    prov = x.groupby(["quarter_region", "year"], as_index=False).agg(sido_actual_eok=("actual_eok", "sum"), sido_predicted_eok=("predicted_eok", "sum"))
    x = x.merge(prov, on=["quarter_region", "year"], how="left")
    x["current_share"] = x["predicted_eok"] / x["sido_predicted_eok"]
    x["baseline_parent_predicted_eok"] = x["sido_actual_eok"] * x["current_share"]
    return x


def lh_signal(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not LH.exists():
        return pd.DataFrame(columns=["province_full", "city", "year", "lh_notice_count"]), pd.DataFrame()
    lh = pd.read_csv(LH)
    lh["province_full"] = lh["CNP_CD_NM"].map(normalize_province)
    lh["year"] = pd.to_datetime(lh["PAN_NT_ST_DT"], errors="coerce").dt.year
    lh = lh[lh["year"].between(2021, 2023) & lh["province_full"].ne("")].copy()
    cities = base[["province_full", "city"]].drop_duplicates().copy()
    cities["city_short"] = cities["city"].map(short_city)
    rows = []
    for r in lh.itertuples(index=False):
        province = getattr(r, "province_full")
        name = str(getattr(r, "PAN_NM", "") or "")
        candidates = cities[cities["province_full"].eq(province)].copy()
        matched = []
        for c in candidates.itertuples(index=False):
            city = str(c.city)
            s = str(c.city_short)
            if city and city in name:
                matched.append(city)
            elif s and len(s) >= 2 and s in name:
                matched.append(city)
        matched = sorted(set(matched))
        if len(matched) == 1:
            rows.append(
                {
                    "province_full": province,
                    "city": matched[0],
                    "year": int(getattr(r, "year")),
                    "PAN_ID": getattr(r, "PAN_ID", ""),
                    "PAN_NM": name,
                    "UPP_AIS_TP_NM": getattr(r, "UPP_AIS_TP_NM", ""),
                    "AIS_TP_CD_NM": getattr(r, "AIS_TP_CD_NM", ""),
                }
            )
    matched = pd.DataFrame(rows)
    if matched.empty:
        return pd.DataFrame(columns=["province_full", "city", "year", "lh_notice_count"]), matched
    signal = matched.groupby(["province_full", "city", "year"], as_index=False).agg(lh_notice_count=("PAN_ID", "nunique"))
    return signal, matched


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    base = base_frame()
    lh, matched = lh_signal(base)
    x = base.merge(lh, on=["province_full", "city", "year"], how="left")
    x["lh_notice_count"] = x["lh_notice_count"].fillna(0.0)
    total = x.groupby(["province_full", "year"])["lh_notice_count"].transform("sum")
    x["lh_share"] = np.where(total.gt(0), x["lh_notice_count"] / total, np.nan)

    rows = []
    details = []
    for alpha in [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10]:
        d = x.copy()
        raw = np.where(d["lh_share"].notna(), d["current_share"] + alpha * (d["lh_share"].fillna(0) - d["current_share"]), d["current_share"])
        raw = pd.Series(raw, index=d.index).clip(lower=0)
        raw_sum = raw.groupby([d["province_full"], d["year"]]).transform("sum")
        d["candidate_share"] = np.where(raw_sum.gt(0), raw / raw_sum, d["current_share"])
        d["candidate_predicted_eok"] = d["sido_actual_eok"] * d["candidate_share"]
        d["candidate_abs_error_eok"] = (d["candidate_predicted_eok"] - d["actual_eok"]).abs()
        d["candidate_ape_pct"] = np.where(d["actual_eok"].gt(0), d["candidate_abs_error_eok"] / d["actual_eok"] * 100, np.nan)
        m = metric(d, "candidate_predicted_eok")
        m["scenario"] = f"LH 공고건수 {alpha:.3f}"
        m["signal_cells"] = int(d["lh_notice_count"].gt(0).sum())
        rows.append(m)
        d["scenario"] = m["scenario"]
        details.append(d)

    baseline = metric(x, "baseline_parent_predicted_eok")
    baseline["scenario"] = "baseline_parent_control"
    baseline["signal_cells"] = 0
    summary = pd.concat([pd.DataFrame([baseline]), pd.DataFrame(rows)], ignore_index=True).sort_values("wape_pct")
    current = summary[summary["scenario"].eq("baseline_parent_control")].iloc[0]
    safe = summary[
        summary["scenario"].ne("baseline_parent_control")
        & summary["wape_pct"].lt(float(current["wape_pct"]))
        & summary["over10_cells"].le(int(current["over10_cells"]))
        & summary["over20_cells"].le(int(current["over20_cells"]))
        & summary["max_ape_pct"].le(float(current["max_ape_pct"]))
    ].copy()
    all_detail = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    summary.to_csv(OUT / "phase246_lh_candidate_summary.csv", index=False, encoding="utf-8-sig")
    safe.to_csv(OUT / "phase246_lh_guardrail_safe_candidates.csv", index=False, encoding="utf-8-sig")
    lh.to_csv(OUT / "phase246_lh_signal.csv", index=False, encoding="utf-8-sig")
    matched.to_csv(OUT / "phase246_lh_matched_notices.csv", index=False, encoding="utf-8-sig")
    if not all_detail.empty:
        all_detail.to_csv(OUT / "phase246_lh_candidate_detail.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase246 LH 공공주택·토지 공고 신호 건설업 route 검증

생성시각: {datetime.now().astimezone().isoformat(timespec='seconds')}

## 결론

LH 분양임대공고문 2021~2023년 9,465건을 수집했고, 공고명 안의 시군구명이 같은 시도 내에서 단일하게 식별되는 경우만 건설업 보조신호로 사용했다.

- 매칭 공고: {len(matched):,}건
- 시군구×연도 신호: {len(lh):,}개
- 신호값: 공고건수
- 적용 방식: 기존 시군구 share에 LH 공고건수 share를 0.5~10% 소량 혼합

## 1. 후보 성능

{md_table(summary[["scenario", "rows", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct", "signal_cells"]], digits=3)}

## 2. Guardrail 통과 후보

조건: 기준선보다 WAPE가 낮고, 10% 초과 셀·20% 초과 셀·최대오차율이 악화되지 않을 것.

{md_table(safe[["scenario", "actual_sum_eok", "abs_error_sum_eok", "wape_pct", "over10_cells", "over20_cells", "max_ape_pct", "signal_cells"]], digits=3) if not safe.empty else "_없음_"}

## 3. 판정

LH 공고건수는 공공주택·토지 공급 이벤트의 위치 신호로는 유용하지만, 건설업 GVA 금액을 대체할 만큼 직접적인 금액자료가 아니다. 따라서 단독 보정 route로는 채택하지 않는다. 다만 조달청 계약금액 전량과 결합할 때 공공주택·토지 블록의 위치 후보로 제한 사용할 수 있다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(summary.to_string(index=False))
    print("matched_notices", len(matched), "safe", len(safe))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
