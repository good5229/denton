#!/usr/bin/env python3
"""Phase128: redesign flash GVA estimates as quarterly publication vintages.

The old poster "flash" column used the initial middle-industry prediction.  It
is not a valid Q+1M flash estimate and its error is dominated by poor
middle-industry allocation.  This phase separates:

* quarterly flash vintages: Q1/Q2/Q3/Q4 + one month, using only the parent
  industry nowcast already present in the Phase12 origin file plus a structural
  middle-industry split;
* precision refinement: all available public data after publication.

The current Phase12 origin file has identical predictions across origins, so
the report explicitly marks the numeric vintage panel as a current proxy and
requires the future implementation to refresh parent nowcasts with truly
origin-specific source vintages.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase128_vintage_flash_redesign"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase128_vintage_flash_redesign.md"

PHASE12_2023 = DATA / "partial_stats_phase12_gva_2023_origin_results.csv"
PHASE127 = DATA / "phase127_precision_comwel_after_phase114" / "phase127_strict_registry.csv"


VINTAGES = [
    ("Q1_plus_1m", "1분기+1개월", "2023-04-30", "O1"),
    ("Q2_plus_1m", "1~2분기+1개월", "2023-07-31", "O2"),
    ("Q3_plus_1m", "1~3분기+1개월", "2023-10-31", "O3"),
    ("Q4_plus_1m", "1~4분기+1개월", "2024-01-31", "O4"),
]

SHARE_MODELS = [
    ("legacy_initial_middle_split", "기존 초기 중분류 배분", "initial_predicted_gva_eok", "reject"),
    ("historical_middle_split", "과거 구조 중분류 배분", "phase92_predicted_gva_eok", "flash_candidate"),
    ("block_routed_precision_split", "블록 라우팅 정밀 배분", "phase114_predicted_gva_eok", "precision_only"),
    ("comwel_no_worse_precision_split", "고용·산재 사업장 무악화 정밀 배분", "phase127_strict_predicted_gva_eok", "precision_only"),
]


def read_phase12_parent() -> pd.DataFrame:
    df = pd.read_csv(PHASE12_2023, encoding="cp949", dtype={"sector_code": str, "sigungu_code": str})
    df = df[df["sigungu_name"].isin(["고양시", "포항시"])].copy()
    df["city"] = df["sigungu_name"]
    df["parent_code"] = df["sector_code"]
    # Phase12 values are in million KRW; poster tables use 100 million KRW.
    df["parent_flash_predicted_gva_eok"] = pd.to_numeric(df["prediction_value"], errors="coerce") / 100.0
    df["parent_actual_gva_eok"] = pd.to_numeric(df["actual_value"], errors="coerce") / 100.0
    return df


def read_middle_registry() -> pd.DataFrame:
    reg = pd.read_csv(PHASE127, dtype={"middle_code": str})
    reg["middle_code"] = reg["middle_code"].astype(str).str.zfill(2)
    return reg


def build_middle_vintage_panel(parent: pd.DataFrame, reg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    details = []
    origin_equivalence = []

    for vintage_id, vintage_label, prediction_date, origin_id in VINTAGES:
        p = parent[parent["origin_id"].eq(origin_id)].copy()
        if p.empty:
            p = parent[parent["origin_id"].eq("O0")].copy()
        for model_id, model_label, share_col, allowed_track in SHARE_MODELS:
            base = reg[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", share_col]].copy()
            base[share_col] = pd.to_numeric(base[share_col], errors="coerce")
            denom = base.groupby(["city", "parent_code"])[share_col].transform("sum")
            base["middle_share"] = np.where(denom > 0, base[share_col] / denom, np.nan)
            m = base.merge(
                p[["city", "parent_code", "parent_flash_predicted_gva_eok", "parent_actual_gva_eok"]],
                on=["city", "parent_code"],
                how="inner",
            )
            m["flash_predicted_gva_eok"] = m["parent_flash_predicted_gva_eok"] * m["middle_share"]
            m["flash_error_gva_eok"] = (m["flash_predicted_gva_eok"] - m["actual_gva_eok"]).abs()
            m["flash_error_rate_pct"] = m["flash_error_gva_eok"] / m["actual_gva_eok"].replace(0, np.nan) * 100.0
            m["vintage_id"] = vintage_id
            m["vintage_label"] = vintage_label
            m["prediction_date"] = prediction_date
            m["phase12_origin_id"] = origin_id
            m["share_model_id"] = model_id
            m["share_model_label"] = model_label
            m["allowed_track"] = allowed_track
            details.append(m)
            for city, g in m.groupby("city", sort=False):
                actual_sum = float(g["actual_gva_eok"].sum())
                error_sum = float(g["flash_error_gva_eok"].sum())
                rows.append(
                    {
                        "vintage_id": vintage_id,
                        "vintage_label": vintage_label,
                        "prediction_date": prediction_date,
                        "city": city,
                        "share_model_id": model_id,
                        "share_model_label": model_label,
                        "allowed_track": allowed_track,
                        "actual_sum_eok": actual_sum,
                        "flash_error_sum_eok": error_sum,
                        "flash_wape_pct": error_sum / actual_sum * 100.0,
                        "flash_gt20_cells": int((g["flash_error_rate_pct"] > 20).sum()),
                        "flash_gt10_cells": int((g["flash_error_rate_pct"] > 10).sum()),
                    }
                )

    # Explicitly audit whether Phase12 origin values are actually distinct.
    key_cols = ["city", "parent_code"]
    for city, cg in parent.groupby("city"):
        pivot = cg.pivot_table(index=key_cols, columns="origin_id", values="parent_flash_predicted_gva_eok", aggfunc="first")
        origin_cols = [c for c in ["O1", "O2", "O3", "O4"] if c in pivot.columns]
        if not origin_cols:
            continue
        same_as_o1 = all(np.allclose(pivot[c].fillna(-999999), pivot[origin_cols[0]].fillna(-999999)) for c in origin_cols[1:])
        origin_equivalence.append(
            {
                "city": city,
                "origin_columns": ",".join(origin_cols),
                "phase12_origin_values_identical": bool(same_as_o1),
                "implication": "numeric vintages are protocol placeholders unless parent nowcasts are regenerated from true as-of sources"
                if same_as_o1
                else "origin-specific parent nowcasts available",
            }
        )

    detail = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    summary = pd.DataFrame(rows)
    audit = pd.DataFrame(origin_equivalence)
    return detail, summary, audit


def build_small_method() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "level": "중분류",
                "flash_rule": "상위산업 Q+1개월 속보 총량 × 과거/직전 공표 구조의 중분류 비중",
                "precision_rule": "상위산업 공식 GVA + 사업체조사/경제총조사/고용·산재 사업장 구조자료로 재배분",
                "validation": "중분류 실제 GVA와 직접 비교",
            },
            {
                "level": "소분류",
                "flash_rule": "중분류 속보 총량 × 직전 공표 소분류 구조비중; 당해연도 소분류 actual 사용 금지",
                "precision_rule": "중분류 정밀 총량 × 경제총조사·공장·인허가·사업장 구조자료로 내부 재배분",
                "validation": "소분류 합계가 중분류 실제와 맞는지 집계검증; 소분류 actual 부재 시 외부 전이검증",
            },
        ]
    )


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    def fmt(x: object) -> str:
        if pd.isna(x):
            return ""
        if isinstance(x, (float, np.floating)):
            return f"{float(x):,.2f}"
        if isinstance(x, (int, np.integer)):
            return f"{int(x):,}"
        return str(x).replace("|", "\\|")
    headers = [c.replace("_", " ") for c in d.columns]
    rows = [[fmt(x) for x in r] for r in d.to_numpy()]
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |", *["| " + " | ".join(r) + " |" for r in rows]])


def write_report(summary: pd.DataFrame, audit: pd.DataFrame, method: pd.DataFrame) -> None:
    reject = summary[summary["share_model_id"].eq("legacy_initial_middle_split")]
    flash = summary[summary["share_model_id"].eq("historical_middle_split")]
    precision = summary[summary["share_model_id"].eq("comwel_no_worse_precision_split")]
    comparison = pd.concat([reject, flash, precision], ignore_index=True)
    REPORT.write_text(
        "\n".join(
            [
                "# Phase128 분기+1개월 빈티지 속보 재설계",
                "",
                "## 결론",
                "",
                "기존 포스터의 초기 속보오차는 Q+1개월 속보 성능이 아니라 초기 중분류 배분 실패를 보여주는 값이다. 공모전/제안서에서는 이 값을 속보 성능으로 쓰면 안 된다.",
                "",
                "새 속보 정의는 `상위산업 Q+1개월 속보 총량 × 중·소분류 구조배분`이다. 정밀화는 모든 공표 자료를 사용해 별도 산출한다.",
                "",
                "## 빈티지 정의",
                "",
                md_table(pd.DataFrame(VINTAGES, columns=["vintage_id", "vintage_label", "prediction_date", "phase12_origin_id"]), ["vintage_id", "vintage_label", "prediction_date", "phase12_origin_id"]),
                "",
                "## 중분류 배분방식별 성능",
                "",
                md_table(
                    comparison.sort_values(["city", "vintage_id", "allowed_track", "flash_wape_pct"]),
                    [
                        "vintage_label",
                        "prediction_date",
                        "city",
                        "share_model_label",
                        "allowed_track",
                        "actual_sum_eok",
                        "flash_error_sum_eok",
                        "flash_wape_pct",
                        "flash_gt20_cells",
                        "flash_gt10_cells",
                    ],
                    80,
                ),
                "",
                "## Phase12 origin 감사",
                "",
                md_table(audit, ["city", "origin_columns", "phase12_origin_values_identical", "implication"]),
                "",
                "## 중분류·소분류 운영 규칙",
                "",
                md_table(method, ["level", "flash_rule", "precision_rule", "validation"]),
                "",
                "## 포스터 반영 원칙",
                "",
                "1. `초기 속보오차`라는 단일 컬럼은 제거한다.",
                "2. 속보는 Q1+1M, Q2+1M, Q3+1M, Q4+1M 빈티지별 WAPE/오차개수로 표시한다.",
                "3. 현재 Phase12 origin 값이 동일하므로 수치표에는 `현행 프록시` 또는 `재산출 필요`를 명시한다.",
                "4. 정밀화 표는 Phase127 무악화 결과를 사용하되, 공표 후 재산출로만 설명한다.",
                "5. 소분류는 중분류 총량 안에서만 배분하고, 소분류 합계를 중분류 실제와 비교하는 집계검증을 함께 제시한다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parent = read_phase12_parent()
    reg = read_middle_registry()
    detail, summary, audit = build_middle_vintage_panel(parent, reg)
    method = build_small_method()
    detail.to_csv(OUT / "phase128_vintage_middle_flash_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase128_vintage_middle_flash_summary.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUT / "phase128_phase12_origin_equivalence_audit.csv", index=False, encoding="utf-8-sig")
    method.to_csv(OUT / "phase128_middle_small_operating_rules.csv", index=False, encoding="utf-8-sig")
    write_report(summary, audit, method)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
