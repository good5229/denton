#!/usr/bin/env python3
"""Phase71: stabilize Pohang manufacturing proxy after steel improvement."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE70 = DATA / "phase70_pohang_steel_factory_scale" / "phase70_pohang_steel_factory_scale_detail.csv"
OUTDIR = DATA / "phase71_pohang_manufacturing_stabilization"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase71_pohang_manufacturing_stabilization.md"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int = 20) -> str:
    if df.empty:
        return "\n해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "pp")) else "---" for _, label in cols) + " |")
    for _, row in df.head(limit).iterrows():
        vals = []
        for key, _ in cols:
            val = row[key]
            vals.append(f"{val:,.1f}" if isinstance(val, float) else str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def evaluate(frame: pd.DataFrame, candidate: str, pred_share: pd.Series) -> tuple[dict, pd.DataFrame]:
    out = frame.copy()
    out["candidate"] = candidate
    out["middle_code"] = out.middle_code.astype(str).str.zfill(2)
    out["predicted_share_pct"] = out.middle_code.map(pred_share) * 100
    parent = float((out.actual_gva_eok / (out.actual_share_pct / 100)).median())
    out["predicted_gva_eok"] = out["predicted_share_pct"] / 100 * parent
    out["error_gva_eok"] = (out.predicted_gva_eok - out.actual_gva_eok).abs()
    out["error_rate_pct"] = out.error_gva_eok / out.actual_gva_eok * 100
    metal = out[out.middle_code.astype(str).str.zfill(2).eq("24")].iloc[0]
    summary = {
        "candidate": candidate,
        "manufacturing_wape_pct": out.error_gva_eok.sum() / out.actual_gva_eok.sum() * 100,
        "manufacturing_mae_pp": ((out.predicted_share_pct - out.actual_share_pct).abs()).mean(),
        "primary_metal_predicted_share_pct": metal.predicted_share_pct,
        "primary_metal_error_gva_eok": metal.error_gva_eok,
        "primary_metal_error_rate_pct": metal.error_rate_pct,
    }
    return summary, out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    detail = pd.read_csv(PHASE70)
    current = detail[detail.candidate.eq("current_common_proxy")].copy()
    current["middle_code"] = current.middle_code.astype(str).str.zfill(2)
    area = detail[detail.candidate.eq("manufacturing_facility_area")].copy()
    area["middle_code"] = area.middle_code.astype(str).str.zfill(2)
    base = current.sort_values("middle_code").reset_index(drop=True)
    area = area.sort_values("middle_code").reset_index(drop=True)
    current_share = current.set_index("middle_code").predicted_share_pct / 100
    area_share = area.set_index("middle_code").predicted_share_pct / 100

    candidates: dict[str, pd.Series] = {
        "current_common_proxy": current_share,
        "manufacturing_facility_area_all": area_share,
    }

    # Replace only KSIC 24 with the area-based share and preserve the current
    # relative structure for all other manufacturing industries.
    non24 = [code for code in current_share.index if code != "24"]
    pred = current_share.copy()
    pred.loc["24"] = area_share.loc["24"]
    pred.loc[non24] = current_share.loc[non24] / current_share.loc[non24].sum() * (1 - pred.loc["24"])
    candidates["area_24_current_rest"] = pred

    # Blend the non-24 part between current and area structures after fixing
    # KSIC 24 to the area-based estimate.
    for beta in [0.25, 0.5, 0.75]:
        pred = current_share.copy()
        pred.loc["24"] = area_share.loc["24"]
        area_non = area_share.loc[non24] / area_share.loc[non24].sum()
        current_non = current_share.loc[non24] / current_share.loc[non24].sum()
        pred.loc[non24] = ((1 - beta) * current_non + beta * area_non) * (1 - pred.loc["24"])
        candidates[f"area_24_non24_blend_beta_{beta:g}"] = pred

    summaries = []
    details = []
    for name, share in candidates.items():
        summary, frame = evaluate(base, name, share)
        summaries.append(summary)
        details.append(frame)
    summary = pd.DataFrame(summaries).sort_values("manufacturing_wape_pct")
    detail_out = pd.concat(details, ignore_index=True)
    summary.to_csv(OUTDIR / "phase71_pohang_manufacturing_stabilization_summary.csv", index=False, encoding="utf-8-sig")
    detail_out.to_csv(OUTDIR / "phase71_pohang_manufacturing_stabilization_detail.csv", index=False, encoding="utf-8-sig")

    best = summary.iloc[0]
    current_top = detail_out[detail_out.candidate.eq("current_common_proxy")].sort_values("error_gva_eok", ascending=False)
    best_top = detail_out[detail_out.candidate.eq(best.candidate)].sort_values("error_gva_eok", ascending=False)

    report = f"""# 포항 제조업 오차축소 안정화 비교

## 목적

Phase70에서는 공장등록 `제조시설면적`이 포항 1차 금속 제조업 오차를 크게 줄인다는 점을 확인했다. 그러나 일부 제조업 중분류는 과대추정될 수 있으므로, 이번 실험은 1차 금속만 보강하고 나머지 제조업 구조를 보존하는 안정화 후보를 함께 비교한다.

## 후보별 결과

{md_table(summary, [("candidate", "후보"), ("manufacturing_wape_pct", "제조업 WAPE %"), ("manufacturing_mae_pp", "제조업 MAE pp"), ("primary_metal_predicted_share_pct", "1차금속 추정비중 %"), ("primary_metal_error_gva_eok", "1차금속 오차 억원"), ("primary_metal_error_rate_pct", "1차금속 오차 %")])}

## 판정

- 현재 보유자료 기준 최선 후보는 `{best.candidate}`다.
- 1차 금속만 제조시설면적으로 보정하고 나머지를 기존 구조로 유지하면 금속가공 과대는 일부 줄지만, 식료품·기계수리 등 다른 제조업 오차가 커져 제조업 전체 WAPE가 악화된다.
- 따라서 포항 제조업의 1차 개선안은 `제조시설면적 전체 적용`으로 두고, 2차 개선은 금속가공·식료품·기계수리의 개별 보강자료를 추가하는 방식이 맞다.

## 기존 공통모델 오차 상위

{md_table(current_top, [("middle_name", "중분류"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 10)}

## 최선 후보 오차 상위

{md_table(best_top, [("middle_name", "중분류"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 10)}
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase71_pohang_manufacturing_stabilization_summary.csv")
    print(OUTDIR / "phase71_pohang_manufacturing_stabilization_detail.csv")


if __name__ == "__main__":
    main()
