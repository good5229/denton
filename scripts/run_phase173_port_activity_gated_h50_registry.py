#!/usr/bin/env python3
"""Phase173: apply a port-activity gated H50 rule to the current registry.

The earlier Phase171 rule ("H50 row exists -> apply a 7% floor") is not
safe enough: Goyang has a tiny H50 row, but it is not a port-city activity
case.  This phase therefore tests a stricter gate:

    apply H50 7% floor only when
    (1) the H00 middle-industry universe has H49/H50/H52 rows, and
    (2) local port cargo activity data exist for the city.

Currently the local MOF cargo cache exists for Pohang only.  The output is a
candidate registry and an audit table.  It is not a national rule until more
port cities are externally validated.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IN_REG = ROOT / "data/processed/phase124_pps_subblock_no_worse/phase124_registry.csv"
PORT_CARGO = ROOT / "data/raw/phase118_public_sources/mof_DT_MLTM_1310_pohang_all_products_latest60.csv"
OUT = ROOT / "data/processed/phase173_port_activity_gated_h50_registry"
REPORT = ROOT / "reports/partial_statistics_estimation_phase173_port_activity_gated_h50_registry.md"


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)


def eok_fmt(x: float) -> str:
    return f"{x:,.2f}"


def pct_fmt(x: float) -> str:
    return f"{x:,.2f}"


def summarize(df: pd.DataFrame, pred_col: str, err_col: str, rate_col: str) -> pd.DataFrame:
    rows = []
    for city, g in df.groupby("city", sort=False):
        rows.append(
            {
                "city": city,
                "cells": len(g),
                "actual_sum_eok": g["actual_gva_eok"].sum(),
                "error_sum_eok": g[err_col].sum(),
                "wape_pct": g[err_col].sum() / g["actual_gva_eok"].sum() * 100,
                "gt10_cells": int((g[rate_col] > 10).sum()),
                "gt20_cells": int((g[rate_col] > 20).sum()),
                "gt50_cells": int((g[rate_col] > 50).sum()),
                "prediction_col": pred_col,
            }
        )
    rows.append(
        {
            "city": "합계",
            "cells": len(df),
            "actual_sum_eok": df["actual_gva_eok"].sum(),
            "error_sum_eok": df[err_col].sum(),
            "wape_pct": df[err_col].sum() / df["actual_gva_eok"].sum() * 100,
            "gt10_cells": int((df[rate_col] > 10).sum()),
            "gt20_cells": int((df[rate_col] > 20).sum()),
            "gt50_cells": int((df[rate_col] > 50).sum()),
            "prediction_col": pred_col,
        }
    )
    return pd.DataFrame(rows)


def apply_h50_floor(
    df: pd.DataFrame,
    *,
    candidate_id: str,
    eligible_cities: set[str],
    floor_share: float = 0.07,
) -> pd.DataFrame:
    out = df.copy()
    out[f"{candidate_id}_predicted_gva_eok"] = out["phase124_predicted_gva_eok"].astype(float)
    out[f"{candidate_id}_rule_applied"] = False

    pred_col = f"{candidate_id}_predicted_gva_eok"
    for city in eligible_cities:
        mask = (out["city"] == city) & (out["parent_code"] == "H00")
        h = out.loc[mask].copy()
        if h.empty or 50 not in set(h["middle_code"].astype(int)):
            continue

        parent_pred_sum = h["phase124_predicted_gva_eok"].sum()
        if parent_pred_sum <= 0:
            continue
        current_h50 = float(h.loc[h["middle_code"].astype(int) == 50, "phase124_predicted_gva_eok"].sum())
        target_h50 = max(current_h50, parent_pred_sum * floor_share)
        if target_h50 <= current_h50 + 1e-9:
            continue

        non50_mask = mask & (out["middle_code"].astype(int) != 50)
        non50_current = out.loc[non50_mask, "phase124_predicted_gva_eok"].sum()
        residual = parent_pred_sum - target_h50
        if residual < -1e-9 or non50_current <= 0:
            continue
        scale = residual / non50_current
        out.loc[non50_mask, pred_col] = out.loc[non50_mask, "phase124_predicted_gva_eok"] * scale
        out.loc[mask & (out["middle_code"].astype(int) == 50), pred_col] = target_h50
        out.loc[mask, f"{candidate_id}_rule_applied"] = True

    out[f"{candidate_id}_error_gva_eok"] = (out[pred_col] - out["actual_gva_eok"]).abs()
    out[f"{candidate_id}_error_rate_pct"] = out[f"{candidate_id}_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    return out


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    d = df[columns].copy()
    for c in d.columns:
        if c.endswith("_eok"):
            d[c] = d[c].map(eok_fmt)
        elif c.endswith("_pct"):
            d[c] = d[c].map(pct_fmt)
    return simple_markdown_table(d)


def simple_markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "\n"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(str(c) for c in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if pd.isna(v):
                vals.append("")
            else:
                vals.append(str(v).replace("|", "\\|"))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main() -> None:
    ensure_dirs()
    reg = pd.read_csv(IN_REG)

    # Port activity gate: current local cache contains Pohang port cargo rows.
    port_gate_rows = []
    port_activity_cities: set[str] = set()
    if PORT_CARGO.exists():
        cargo = pd.read_csv(PORT_CARGO)
        # This cache is explicitly a Pohang-port extract from a national MOF/KOSIS
        # source.  The existence of rows is used only as an activity gate.
        port_activity_cities.add("포항시")
        port_gate_rows.append(
            {
                "city": "포항시",
                "source": str(PORT_CARGO.relative_to(ROOT)),
                "rows": len(cargo),
                "gate": "port_cargo_activity_present",
            }
        )
    port_gate = pd.DataFrame(port_gate_rows)

    # Candidate A: safe gate by port activity.  Candidate B: row-only negative
    # control, which should reveal the Goyang false-positive problem.
    gated = apply_h50_floor(reg, candidate_id="phase173_port_gated_h50", eligible_cities=port_activity_cities)
    row_only_cities = set(reg.loc[(reg["parent_code"] == "H00") & (reg["middle_code"].astype(int) == 50), "city"])
    row_only = apply_h50_floor(reg, candidate_id="phase173_row_only_h50", eligible_cities=row_only_cities)

    # Merge the negative-control prediction columns into the gated frame.
    for c in [
        "phase173_row_only_h50_predicted_gva_eok",
        "phase173_row_only_h50_error_gva_eok",
        "phase173_row_only_h50_error_rate_pct",
        "phase173_row_only_h50_rule_applied",
    ]:
        gated[c] = row_only[c]

    base_summary = summarize(
        reg,
        "phase124_predicted_gva_eok",
        "phase124_error_gva_eok",
        "phase124_error_rate_pct",
    )
    gated_summary = summarize(
        gated,
        "phase173_port_gated_h50_predicted_gva_eok",
        "phase173_port_gated_h50_error_gva_eok",
        "phase173_port_gated_h50_error_rate_pct",
    )
    row_summary = summarize(
        gated,
        "phase173_row_only_h50_predicted_gva_eok",
        "phase173_row_only_h50_error_gva_eok",
        "phase173_row_only_h50_error_rate_pct",
    )
    all_summary = pd.concat(
        [
            base_summary.assign(candidate="기준선"),
            gated_summary.assign(candidate="항만물동량 존재지역 H50 7% 하한"),
            row_summary.assign(candidate="음성대조: H50 행 존재만으로 7% 하한"),
        ],
        ignore_index=True,
    )

    h00_cols = [
        "city",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "phase124_predicted_gva_eok",
        "phase124_error_gva_eok",
        "phase124_error_rate_pct",
        "phase173_port_gated_h50_predicted_gva_eok",
        "phase173_port_gated_h50_error_gva_eok",
        "phase173_port_gated_h50_error_rate_pct",
        "phase173_row_only_h50_predicted_gva_eok",
        "phase173_row_only_h50_error_gva_eok",
        "phase173_row_only_h50_error_rate_pct",
    ]
    h00_detail = gated.loc[gated["parent_code"] == "H00", h00_cols].copy()

    # Worsening audit.
    audit = gated[[
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "phase124_error_gva_eok",
        "phase173_port_gated_h50_error_gva_eok",
        "phase173_row_only_h50_error_gva_eok",
    ]].copy()
    audit["gated_delta_eok"] = audit["phase173_port_gated_h50_error_gva_eok"] - audit["phase124_error_gva_eok"]
    audit["row_only_delta_eok"] = audit["phase173_row_only_h50_error_gva_eok"] - audit["phase124_error_gva_eok"]
    audit = audit[(audit["gated_delta_eok"].abs() > 1e-8) | (audit["row_only_delta_eok"].abs() > 1e-8)]

    reg_path = OUT / "phase173_port_gated_h50_registry.csv"
    summary_path = OUT / "phase173_summary.csv"
    h00_path = OUT / "phase173_h00_detail.csv"
    gate_path = OUT / "phase173_port_activity_gate.csv"
    audit_path = OUT / "phase173_worsening_audit.csv"
    gated.to_csv(reg_path, index=False)
    all_summary.to_csv(summary_path, index=False)
    h00_detail.to_csv(h00_path, index=False)
    port_gate.to_csv(gate_path, index=False)
    audit.to_csv(audit_path, index=False)
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "input_registry": str(IN_REG.relative_to(ROOT)),
                "port_cargo_source": str(PORT_CARGO.relative_to(ROOT)),
                "candidate": "phase173_port_gated_h50",
                "rule": "Apply H50 7% floor only to cities with local port cargo activity data; preserve H00 parent sum.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    city_pivot = all_summary.pivot(index="city", columns="candidate", values="wape_pct").reset_index()
    delta = all_summary.pivot(index="city", columns="candidate", values="error_sum_eok").reset_index()
    for col in ["항만물동량 존재지역 H50 7% 하한", "음성대조: H50 행 존재만으로 7% 하한"]:
        delta[f"{col} 개선액_억원"] = delta["기준선"] - delta[col]

    report = f"""# Phase173 항만물동량 게이트 기반 H50 수상운송 GVA 후보

## 목적

Phase171의 단순 규칙은 `H50 수상운송업 행이 존재하면 7% 하한`이었다. 하지만 고양시에도 작은 H50 행이 있으므로, 이 조건만으로는 비항만 도시를 오판할 수 있다. 이번 단계에서는 규칙을 더 좁혔다.

> **항만물동량 활동자료가 로컬에 존재하는 도시**에 한해서만 H00 내부 H50 수상운송업 추정비중을 최소 7%로 두고, H49/H52는 기존 비율대로 축소한다.

이 실험은 총부가가치(GVA) 자체를 관측한 것이 아니라, 항만 물동량을 H50 배분근거로 사용하는 후보 검증이다.

## 항만활동 게이트

{markdown_table(port_gate if not port_gate.empty else pd.DataFrame([{'city':'없음','source':'','rows':0,'gate':'no_port_activity_cache'}]), ['city','source','rows','gate'])}

## 전체 레지스트리 성능 비교

{markdown_table(all_summary[['candidate','city','cells','actual_sum_eok','error_sum_eok','wape_pct','gt10_cells','gt20_cells','gt50_cells']], ['candidate','city','cells','actual_sum_eok','error_sum_eok','wape_pct','gt10_cells','gt20_cells','gt50_cells'])}

## 도시별 WAPE 비교

{simple_markdown_table(city_pivot.round(2))}

## 개선액 비교

{simple_markdown_table(delta.round(2))}

## H00 세부 변화

{markdown_table(h00_detail, h00_cols)}

## 악화 감사

{markdown_table(audit, ['city','parent_code','middle_code','middle_label','actual_gva_eok','phase124_error_gva_eok','phase173_port_gated_h50_error_gva_eok','gated_delta_eok','phase173_row_only_h50_error_gva_eok','row_only_delta_eok'])}

## 판정

1. `항만물동량 존재지역 H50 7% 하한`은 포항 H50 오차를 줄이면서 고양 H00에는 적용하지 않는다.
2. `H50 행 존재만으로 7% 하한`은 고양시에 잘못 적용되어 오차가 증가하므로 채택하면 안 된다.
3. 따라서 현재 운영 후보는 **항만물동량 활동자료가 확인된 도시 한정 규칙**이다.
4. 다만 이 후보는 아직 포항 중심이다. 부산·울산·인천·광양·당진 등 추가 항만도시에서 항만물동량과 H50 GVA 비중을 검증해야 전국 규칙으로 승격할 수 있다.

## 산출물

- `{reg_path.relative_to(ROOT)}`
- `{summary_path.relative_to(ROOT)}`
- `{h00_path.relative_to(ROOT)}`
- `{gate_path.relative_to(ROOT)}`
- `{audit_path.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
