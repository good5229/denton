#!/usr/bin/env python3
"""Compute construction WAPE reduction frontier for staged data collection.

This is an oracle/ROI diagnostic, not a predictive performance claim.  It
answers how much error reduction is required in the priority collection set for
construction WAPE to fall below 10%.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "nationwide" / "construction_wape_reduction_frontier.md"
PRIORITY = OUT / "construction_buildinghub_collection_priority.csv"
ERR = OUT / "annual_sigungu_activity_error_audit.csv"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ["WAPE", "%", "억원", "개", "N", "감축"]) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            v = row.get(key, "")
            if isinstance(v, (float, np.floating)):
                vals.append(f"{v:,.3f}")
            elif isinstance(v, (int, np.integer)):
                vals.append(f"{v:,}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    priority = pd.read_csv(PRIORITY).sort_values("priority_rank").copy()
    err = pd.read_csv(ERR)
    construction = err[err["activity"].eq("건설업")].copy()
    total_actual = float(construction["actual_eok"].abs().sum())
    total_error = float(construction["abs_error_eok"].sum())
    current_wape = total_error / total_actual * 100
    target_error = total_actual * 0.10
    required_reduction = max(0.0, total_error - target_error)
    required_reduction_pct_of_total_error = required_reduction / total_error * 100 if total_error else np.nan

    rows = []
    for n in [1, 3, 5, 10, 15, 20, 25, 28, 30, 40, 52, 70, 88, 120]:
        sub = priority.head(min(n, len(priority))).copy()
        captured = float(sub["abs_error_sum_eok"].sum())
        req_within = required_reduction / captured * 100 if captured else np.inf
        for assumed_reduction_rate in [0.25, 0.50, 0.75, 1.00]:
            remaining_error = total_error - captured * assumed_reduction_rate
            rows.append(
                {
                    "top_n_cities": int(min(n, len(priority))),
                    "legal_dong_requests": int(sub["active_legal_dong_requests"].sum()),
                    "captured_error_eok": captured,
                    "captured_error_share_pct": captured / total_error * 100 if total_error else np.nan,
                    "required_reduction_within_set_pct": req_within,
                    "assumed_reduction_rate_pct": assumed_reduction_rate * 100,
                    "oracle_remaining_error_eok": remaining_error,
                    "oracle_wape_pct": remaining_error / total_actual * 100 if total_actual else np.nan,
                    "target_10pct_met": remaining_error <= target_error,
                }
            )
    frontier = pd.DataFrame(rows)

    threshold_rows = []
    for reduction_rate in [0.25, 0.50, 0.75, 1.00]:
        chosen = None
        for n in range(1, len(priority) + 1):
            sub = priority.head(n)
            remaining_error = total_error - float(sub["abs_error_sum_eok"].sum()) * reduction_rate
            if remaining_error <= target_error:
                chosen = {
                    "assumed_reduction_rate_pct": reduction_rate * 100,
                    "min_top_n_cities": n,
                    "legal_dong_requests": int(sub["active_legal_dong_requests"].sum()),
                    "captured_error_eok": float(sub["abs_error_sum_eok"].sum()),
                    "oracle_wape_pct": remaining_error / total_actual * 100,
                }
                break
        if chosen is None:
            chosen = {
                "assumed_reduction_rate_pct": reduction_rate * 100,
                "min_top_n_cities": "not_reached",
                "legal_dong_requests": int(priority["active_legal_dong_requests"].sum()),
                "captured_error_eok": float(priority["abs_error_sum_eok"].sum()),
                "oracle_wape_pct": (total_error - float(priority["abs_error_sum_eok"].sum()) * reduction_rate) / total_actual * 100,
            }
        threshold_rows.append(chosen)
    threshold = pd.DataFrame(threshold_rows)

    contribution = priority.copy()
    contribution["remaining_wape_if_city_fully_fixed_pct"] = (total_error - contribution["abs_error_sum_eok"]) / total_actual * 100
    contribution["wape_drop_if_city_fully_fixed_pp"] = current_wape - contribution["remaining_wape_if_city_fully_fixed_pct"]

    frontier.to_csv(OUT / "construction_wape_reduction_frontier.csv", index=False, encoding="utf-8-sig")
    threshold.to_csv(OUT / "construction_wape_reduction_thresholds.csv", index=False, encoding="utf-8-sig")
    contribution.to_csv(OUT / "construction_city_error_reduction_contribution.csv", index=False, encoding="utf-8-sig")

    one_line = {
        "current_wape_pct": current_wape,
        "target_wape_pct": 10.0,
        "total_actual_eok": total_actual,
        "current_abs_error_eok": total_error,
        "target_abs_error_eok": target_error,
        "required_abs_error_reduction_eok": required_reduction,
        "required_reduction_pct_of_total_error": required_reduction_pct_of_total_error,
    }

    lines = [
        "# 건설업 WAPE 10% 달성 필요 감축량 및 staged collection frontier",
        "",
        "## 결론",
        "",
        f"- 현재 건설업 WAPE는 {current_wape:.3f}%다.",
        f"- 10% 이하로 내려가려면 절대오차를 {required_reduction:,.1f}억원 줄여야 한다.",
        f"- 이는 현재 건설업 절대오차의 {required_reduction_pct_of_total_error:.1f}%에 해당한다.",
        "- 오차기여 상위 28개 시군구는 전체 건설업 오차의 약 50%를 포착하므로, 해당 집합을 거의 완전히 설명해야 WAPE 10% 근처에 도달한다.",
        "- 따라서 1차 staged collection은 충분히 의미 있지만, top28만으로 안정적인 10% 이하를 보장하려면 높은 설명력이 필요하다.",
        "- 이 문서는 oracle/상한 진단이며, 예측성능으로 주장하지 않는다.",
        "",
        "## 기준 수치",
        "",
        md_table(pd.DataFrame([one_line]), [("current_wape_pct", "현재 WAPE_%"), ("target_wape_pct", "목표 WAPE_%"), ("total_actual_eok", "실제합_억원"), ("current_abs_error_eok", "현재 절대오차_억원"), ("target_abs_error_eok", "목표 절대오차_억원"), ("required_abs_error_reduction_eok", "필요 감축_억원"), ("required_reduction_pct_of_total_error", "필요 감축/현재오차_%")]),
        "",
        "## 10% 달성에 필요한 최소 수집범위",
        "",
        md_table(threshold, [("assumed_reduction_rate_pct", "수집집합 내 오차감축률_%"), ("min_top_n_cities", "최소 상위 N"), ("legal_dong_requests", "법정동 요청 개"), ("captured_error_eok", "포착오차_억원"), ("oracle_wape_pct", "oracle WAPE_%")]),
        "",
        "## staged collection oracle frontier",
        "",
        md_table(frontier[frontier["assumed_reduction_rate_pct"].isin([50.0, 75.0, 100.0])], [("top_n_cities", "상위 N"), ("legal_dong_requests", "법정동 요청 개"), ("captured_error_eok", "포착오차_억원"), ("captured_error_share_pct", "포착오차_%"), ("required_reduction_within_set_pct", "집합내 필요감축_%"), ("assumed_reduction_rate_pct", "가정감축_%"), ("oracle_wape_pct", "oracle WAPE_%"), ("target_10pct_met", "10%달성")], 45),
        "",
        "## 해석",
        "",
        "- top5만으로는 모든 오차를 없애도 WAPE 10%에 도달하지 못한다.",
        "- top28은 오차기여 50% 집합이므로, 집합 내 오차를 약 100% 가까이 줄여야 10% 경계에 접근한다.",
        "- 75% 감축률을 현실적 상한으로 보면 top40~top52 범위까지 수집해야 한다.",
        "- 따라서 다음 실험은 top1 또는 top5로 pipeline을 검증하고, 성능 방향이 맞으면 top28→top52 순서로 확장하는 것이 합리적이다.",
        "",
        "## 산출 파일",
        "",
        "- `nationwide/outputs/construction_wape_reduction_frontier.csv`",
        "- `nationwide/outputs/construction_wape_reduction_thresholds.csv`",
        "- `nationwide/outputs/construction_city_error_reduction_contribution.csv`",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(REPORT)
    print(OUT / "construction_wape_reduction_thresholds.csv")


if __name__ == "__main__":
    main()
