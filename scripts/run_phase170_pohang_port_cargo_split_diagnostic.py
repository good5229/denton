#!/usr/bin/env python3
"""Phase170: Pohang port cargo split diagnostic for H00/C00 GVA allocation.

This phase uses only local cached data.  It does not collect new API rows.

Important boundary:
- Port cargo R/T is a direct physical activity signal, not GVA actual.
- The script reports diagnostic performance against known middle actuals, but
  any floor/weight chosen from Pohang actual is marked non-operational.
- The only operationally safer conclusion is whether the signal justifies a
  *candidate* route for future externally validated calibration.
"""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "data" / "processed" / "phase170_pohang_port_cargo_split_diagnostic"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase170_pohang_port_cargo_split_diagnostic.md"
REGISTRY = ROOT / "data" / "processed" / "phase124_pps_subblock_no_worse" / "phase124_registry.csv"
MOF = ROOT / "data" / "raw" / "phase118_public_sources" / "mof_DT_MLTM_1310_pohang_all_products_latest60.csv"

STEEL_PRODUCTS = {"철광석", "유연탄", "철강 및 그제품", "고 철", "비철금속 및 그제품"}
MINERAL_PRODUCTS = {"기타광석 및 생산품", "시멘트", "무연탄"}


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            value = row.get(key, "")
            if isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals).replace("\n", " ") + " |")
    return "\n".join(lines) + "\n"


def load_registry() -> pd.DataFrame:
    df = pd.read_csv(REGISTRY)
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["baseline_predicted_gva_eok"] = pd.to_numeric(df["phase124_predicted_gva_eok"], errors="coerce")
    df["actual_gva_eok"] = pd.to_numeric(df["actual_gva_eok"], errors="coerce")
    return df[df["city"].eq("포항시") & df["parent_code"].isin(["H00", "C00"])].copy()


def load_port_summary() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(MOF)
    df["period"] = pd.to_numeric(df["PRD_DE"], errors="coerce")
    df["year"] = (df["period"] // 100).astype("Int64")
    df["month"] = (df["period"] % 100).astype("Int64")
    df["value_rt"] = pd.to_numeric(df["DT"], errors="coerce").fillna(0.0)
    df["product"] = df["C2_NM"].astype(str)
    product_year = (
        df[df["product"].ne("총계")]
        .groupby(["year", "product"], as_index=False)
        .agg(value_rt=("value_rt", "sum"))
        .sort_values(["year", "value_rt"], ascending=[True, False])
    )
    annual = df[df["product"].eq("총계")].groupby("year", as_index=False).agg(total_rt=("value_rt", "sum"))
    steel = product_year[product_year["product"].isin(STEEL_PRODUCTS)].groupby("year", as_index=False).agg(steel_rt=("value_rt", "sum"))
    mineral = product_year[product_year["product"].isin(MINERAL_PRODUCTS)].groupby("year", as_index=False).agg(mineral_rt=("value_rt", "sum"))
    annual = annual.merge(steel, on="year", how="left").merge(mineral, on="year", how="left").fillna(0.0)
    annual["steel_share_pct"] = annual["steel_rt"] / annual["total_rt"] * 100
    annual["mineral_share_pct"] = annual["mineral_rt"] / annual["total_rt"] * 100
    annual["steel_mineral_share_pct"] = (annual["steel_rt"] + annual["mineral_rt"]) / annual["total_rt"] * 100
    return annual, product_year


def summarize_block(df: pd.DataFrame, pred_col: str, block: str) -> dict[str, float]:
    part = df[df["parent_code"].eq(block)].copy()
    err = (part[pred_col] - part["actual_gva_eok"]).abs()
    return {
        "actual_sum_eok": float(part["actual_gva_eok"].sum()),
        "predicted_sum_eok": float(part[pred_col].sum()),
        "error_sum_eok": float(err.sum()),
        "wape_pct": float(err.sum() / part["actual_gva_eok"].sum() * 100),
        "gt10_cells": int(((err / part["actual_gva_eok"] * 100) > 10).sum()),
        "gt20_cells": int(((err / part["actual_gva_eok"] * 100) > 20).sum()),
    }


def h00_candidates(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    h = base[base["parent_code"].eq("H00")].copy()
    total = float(h["actual_gva_eok"].sum())
    baseline = h.set_index("middle_code")["baseline_predicted_gva_eok"] / total
    labels = h.set_index("middle_code")["middle_label"].to_dict()
    actual = h.set_index("middle_code")["actual_gva_eok"].to_dict()

    rows = []
    detail_rows = []
    floors = [baseline["50"], 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    for floor in floors:
        old_resid = baseline[["49", "52"]].sum()
        shares = baseline.copy()
        shares["50"] = floor
        shares["49"] = baseline["49"] / old_resid * (1 - floor)
        shares["52"] = baseline["52"] / old_resid * (1 - floor)
        candidate = "baseline" if abs(floor - baseline["50"]) < 1e-12 else f"H50 항만활동 최소비중 {floor * 100:.0f}%"
        op_status = "기준선" if candidate == "baseline" else "진단 후보: 외부 검증 전 채택금지"
        errs = []
        for code in ["49", "50", "52"]:
            pred = float(shares[code] * total)
            err = abs(pred - actual[code])
            errs.append(err)
            detail_rows.append(
                {
                    "block": "H00",
                    "candidate": candidate,
                    "middle_code": code,
                    "middle_label": labels[code],
                    "actual_gva_eok": actual[code],
                    "predicted_gva_eok": pred,
                    "error_eok": err,
                    "error_rate_pct": err / actual[code] * 100,
                    "predicted_share_pct": shares[code] * 100,
                    "adoption_status": op_status,
                }
            )
        rows.append(
            {
                "block": "H00",
                "candidate": candidate,
                "h50_floor_pct": floor * 100,
                "error_sum_eok": sum(errs),
                "wape_pct": sum(errs) / total * 100,
                "gt10_cells": sum((pd.Series(errs).to_numpy() / np.array([actual["49"], actual["50"], actual["52"]]) * 100) > 10),
                "gt20_cells": sum((pd.Series(errs).to_numpy() / np.array([actual["49"], actual["50"], actual["52"]]) * 100) > 20),
                "adoption_status": op_status,
            }
        )
    return pd.DataFrame(rows).sort_values("error_sum_eok"), pd.DataFrame(detail_rows)


def c00_diagnostics(base: pd.DataFrame, port_annual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    c = base[base["parent_code"].eq("C00")].copy()
    c["raw_predicted_gva_eok"] = c["baseline_predicted_gva_eok"]
    parent_total = float(c["actual_gva_eok"].sum())
    raw_total = float(c["raw_predicted_gva_eok"].sum())
    c["parent_normalized_predicted_gva_eok"] = c["raw_predicted_gva_eok"] * (parent_total / raw_total)

    steel_share = float(port_annual.loc[port_annual["year"].eq(2023), "steel_mineral_share_pct"].iloc[0]) / 100
    # Non-operational diagnostic: blend parent-normalized baseline internal
    # shares toward the physical cargo steel/mineral share for 23/24/25.
    # This deliberately exposes whether port cargo direction helps, but the
    # mapping coefficient is not externally calibrated.
    candidate_details = []
    summary_rows = []
    for alpha in [0.0, 0.1, 0.2, 0.3]:
        temp = c.copy()
        base_pred = temp["parent_normalized_predicted_gva_eok"].copy()
        block_mask = temp["middle_code"].isin(["23", "24", "25"])
        block_base_total = float(base_pred[block_mask].sum())
        target_block_total = parent_total * (alpha * steel_share + (1 - alpha) * (block_base_total / parent_total))
        other_total = parent_total - target_block_total
        pred = base_pred.copy()
        if block_base_total > 0:
            pred.loc[block_mask] = base_pred.loc[block_mask] / block_base_total * target_block_total
        other_base_total = float(base_pred[~block_mask].sum())
        if other_base_total > 0:
            pred.loc[~block_mask] = base_pred.loc[~block_mask] / other_base_total * other_total
        candidate = "상위총량 정규화 기준" if alpha == 0 else f"철강·광물 물동량 내부비중 {alpha:.1f} 혼합"
        status = "분할 기준선" if alpha == 0 else "진단 후보: 외부 검증 전 채택금지"
        err = (pred - temp["actual_gva_eok"]).abs()
        summary_rows.append(
            {
                "block": "C00",
                "candidate": candidate,
                "cargo_steel_mineral_share_pct": steel_share * 100,
                "error_sum_eok": float(err.sum()),
                "wape_pct": float(err.sum() / parent_total * 100),
                "gt10_cells": int(((err / temp["actual_gva_eok"] * 100) > 10).sum()),
                "gt20_cells": int(((err / temp["actual_gva_eok"] * 100) > 20).sum()),
                "adoption_status": status,
            }
        )
        for idx, row in temp.iterrows():
            candidate_details.append(
                {
                    "block": "C00",
                    "candidate": candidate,
                    "middle_code": row["middle_code"],
                    "middle_label": row["middle_label"],
                    "actual_gva_eok": row["actual_gva_eok"],
                    "predicted_gva_eok": float(pred.loc[idx]),
                    "error_eok": float(abs(pred.loc[idx] - row["actual_gva_eok"])),
                    "error_rate_pct": float(abs(pred.loc[idx] - row["actual_gva_eok"]) / row["actual_gva_eok"] * 100),
                    "adoption_status": status,
                }
            )
    return pd.DataFrame(summary_rows).sort_values("error_sum_eok"), pd.DataFrame(candidate_details)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = load_registry()
    port_annual, port_products = load_port_summary()

    h_summary, h_detail = h00_candidates(base)
    c_summary, c_detail = c00_diagnostics(base, port_annual)

    port_annual.to_csv(OUTDIR / "phase170_pohang_port_annual_summary.csv", index=False, encoding="utf-8-sig")
    port_products.to_csv(OUTDIR / "phase170_pohang_port_product_year.csv", index=False, encoding="utf-8-sig")
    h_summary.to_csv(OUTDIR / "phase170_h00_port_floor_summary.csv", index=False, encoding="utf-8-sig")
    h_detail.to_csv(OUTDIR / "phase170_h00_port_floor_detail.csv", index=False, encoding="utf-8-sig")
    c_summary.to_csv(OUTDIR / "phase170_c00_steel_cargo_summary.csv", index=False, encoding="utf-8-sig")
    c_detail.to_csv(OUTDIR / "phase170_c00_steel_cargo_detail.csv", index=False, encoding="utf-8-sig")

    h_base = h_summary[h_summary["candidate"].eq("baseline")].iloc[0]
    h_best = h_summary.iloc[0]
    c_base = c_summary[c_summary["candidate"].eq("상위총량 정규화 기준")].iloc[0]
    c_best = c_summary.iloc[0]
    top_products_2023 = (
        port_products[port_products["year"].eq(2023)]
        .sort_values("value_rt", ascending=False)
        .head(8)
        .assign(value_mrt=lambda d: d["value_rt"] / 1_000_000)
    )
    h_detail_best = h_detail[h_detail["candidate"].eq(h_best["candidate"])].sort_values("middle_code")
    c_detail_base_worst = c_detail[c_detail["candidate"].eq("상위총량 정규화 기준")].sort_values("error_eok", ascending=False).head(8)

    manifest = {
        "input_registry": str(REGISTRY.relative_to(ROOT)),
        "input_mof": str(MOF.relative_to(ROOT)),
        "important_boundary": "Port cargo R/T is activity data, not GVA actual; diagnostic candidates are not operationally adopted without external calibration.",
    }
    (OUTDIR / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = f"""# Phase170 포항항 물동량 기반 H00/C00 분리 진단

## 목적

포항항 월별 품목 물동량 캐시를 사용해 포항시 총부가가치(GVA) 중 운수·창고업(H00)과 제조업(C00)의 중분류 배분을 개선할 수 있는지 점검했다. 이 실험은 신규 API 수집 없이 로컬 캐시만 사용했다.

중요한 경계는 명확하다. 포항항 물동량 R/T는 실제 GVA가 아니라 물리적 활동자료다. 따라서 물동량으로 방향성을 확인할 수는 있지만, 포항 actual에 맞춘 변환계수를 운영 성능으로 주장하지 않는다.

## 포항항 물동량 구조

{md_table(port_annual[port_annual["year"].between(2021, 2025)], [("year", "연도"), ("total_rt", "총 물동량 R/T"), ("steel_rt", "철강관련 R/T"), ("mineral_rt", "광물·시멘트 R/T"), ("steel_share_pct", "철강관련 %"), ("steel_mineral_share_pct", "철강+광물 %")])}

2023년 상위 품목은 다음과 같다.

{md_table(top_products_2023, [("product", "품목"), ("value_mrt", "물동량 백만 R/T")])}

## H00 운수·창고업: H50 수상운송 최소비중 진단

Phase124 기준 포항 H00의 중분류 오차는 H50 수상운송업에서 집중된다. baseline H50 추정은 실제 948.61억원 대비 374.39억원으로, 오차율 60.53%다. 포항항 총 물동량이 2023년 5,018.80만 R/T이므로 H50을 현행 사업체·종사자 배분 그대로 두는 것은 설명력이 약하다.

{md_table(h_summary, [("candidate", "후보"), ("h50_floor_pct", "H50 최소비중 %"), ("error_sum_eok", "H00 합산오차 억원"), ("wape_pct", "H00 WAPE %"), ("gt10_cells", "10%초과 셀"), ("gt20_cells", "20%초과 셀"), ("adoption_status", "채택상태")])}

수치상 최선 후보의 중분류별 결과:

{md_table(h_detail_best, [("middle_code", "중분류"), ("middle_label", "업종"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("predicted_share_pct", "추정비중 %")])}

H00 기준선 대비 최선 진단 후보의 WAPE는 {h_base.wape_pct:,.2f}% → {h_best.wape_pct:,.2f}%다. 하지만 H50 최소비중 7~8% 같은 계수는 포항 actual 없이 외부에서 보정된 값이 아니므로, **운영 채택이 아니라 진단 후보**로 둔다.

## C00 제조업: 철강·광물 물동량 혼합 진단

C00은 상위 제조업 총량 오차와 내부 중분류 분할오차가 섞여 있으므로, 먼저 C00 상위총량을 실제 C00 총량에 정규화한 기준선을 별도로 만들었다. 이는 중분류 배분 검증용 기준이며, 상위총량 보정 자체를 예측력으로 주장하지 않는다.

{md_table(c_summary, [("candidate", "후보"), ("cargo_steel_mineral_share_pct", "철강+광물 물동량 %"), ("error_sum_eok", "C00 합산오차 억원"), ("wape_pct", "C00 WAPE %"), ("gt10_cells", "10%초과 셀"), ("gt20_cells", "20%초과 셀"), ("adoption_status", "채택상태")])}

상위총량 정규화 기준에서 금액오차가 큰 중분류:

{md_table(c_detail_base_worst, [("middle_code", "중분류"), ("middle_label", "업종"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_eok", "오차 억원"), ("error_rate_pct", "오차 %")])}

C00에서는 철강·광물 물동량 혼합이 기준선보다 안정적으로 낫다고 보기 어렵다. 특히 1차 금속 제조업은 상위총량 정규화 기준에서 이미 오차율이 낮아, 물동량 비중을 강하게 섞으면 다른 제조업 중분류를 흔들 위험이 크다. 따라서 C00에는 포항항 물동량을 전면 재배분식으로 채택하지 않는다.

## 판정

1. **H00/H50**: 포항항 물동량은 수상운송업 과소추정 문제를 설명하는 강한 활동자료다. 다만 R/T→GVA 비중 변환계수는 외부 항만도시 검증이 필요하므로 현재는 진단 후보로만 유지한다.
2. **C00/C24**: 철강 관련 물동량은 포항 제조업 구조를 설명하지만, C24 1차 금속은 상위총량 정규화 기준에서 이미 안정적이다. 물동량 혼합은 보조 해석으로만 두고, C00 운영식은 현재 기준을 유지한다.
3. 다음 개선은 포항항만으로 끝내면 안 된다. 부산·울산·광양·당진·인천 등 항만도시 외부 표본에서 같은 H50 floor 또는 물동량/GVA 계수를 검증해야 한다.

## 산출물

- `data/processed/phase170_pohang_port_cargo_split_diagnostic/phase170_pohang_port_annual_summary.csv`
- `data/processed/phase170_pohang_port_cargo_split_diagnostic/phase170_h00_port_floor_summary.csv`
- `data/processed/phase170_pohang_port_cargo_split_diagnostic/phase170_h00_port_floor_detail.csv`
- `data/processed/phase170_pohang_port_cargo_split_diagnostic/phase170_c00_steel_cargo_summary.csv`
- `data/processed/phase170_pohang_port_cargo_split_diagnostic/phase170_c00_steel_cargo_detail.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR)


if __name__ == "__main__":
    main()
