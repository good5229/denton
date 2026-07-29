"""Phase240 top5 construction city-type small-shift route audit.

The prior BuildingHUB route failed because it moved some city-years in the
wrong direction.  This audit tries the smallest safe alternative without new
data: use only prior-year direction consistency, keep existing shares as the
anchor, and apply very small feature-based adjustments only when a candidate
improved all prior years for the same city.

This remains a local top5 audit, not a nationwide route adoption.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/phase240_construction_top5_small_shift_route"
REPORT = ROOT / "reports/partial_statistics_estimation_phase240_construction_top5_small_shift_route.md"
CAND = ROOT / "data/processed/phase239_construction_top5_buildinghub_guarded_grid/phase239_top5_candidate_detail.csv"
BASE_REPORT = ROOT / "reports/partial_statistics_estimation_phase239_construction_top5_buildinghub_guarded_grid.md"


def fmt(x: object, digits: int = 3) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, (float, np.floating)):
        return f"{x:,.{digits}f}"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    return str(x)


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    lines = [
        "| " + " | ".join(label for _, label in cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(row.get(key, "")) for key, _ in cols) + " |")
    return "\n".join(lines)


def metric(df: pd.DataFrame, group_cols: list[str] | None = None) -> pd.DataFrame:
    if group_cols is None:
        group_cols = []
    rows = []
    grouped = [((), df)] if not group_cols else df.groupby(group_cols, dropna=False)
    for key, g in grouped:
        if group_cols and not isinstance(key, tuple):
            key = (key,)
        rec = {c: v for c, v in zip(group_cols, key)}
        actual_sum = float(g["actual_eok"].sum())
        abs_sum = float(g["abs_error_eok"].sum())
        rec.update(
            {
                "rows": int(len(g)),
                "actual_sum_eok": actual_sum,
                "abs_error_sum_eok": abs_sum,
                "wape_pct": abs_sum / actual_sum * 100 if actual_sum else np.nan,
                "over10_cells": int((g["ape_pct"] > 10).sum()),
                "over20_cells": int((g["ape_pct"] > 20).sum()),
                "max_ape_pct": float(g["ape_pct"].max()) if len(g) else np.nan,
            }
        )
        rows.append(rec)
    return pd.DataFrame(rows)


def infer_block(feature: str) -> str:
    feature = "" if feature is None or str(feature).lower() == "nan" else str(feature)
    if not feature:
        return "fallback"
    if "산업" in feature:
        return "industrial_building"
    if "상업" in feature:
        return "commercial_building"
    if "주거" in feature:
        return "housing_building"
    if "approval" in feature:
        return "completion_refinement"
    if "start" in feature:
        return "start_flash"
    if "permit" in feature:
        return "permit_flash"
    return "buildinghub"


def select_small_shift(candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select candidates using prior years and an explicit conservative rule.

    Year 2021 is warmup.  For 2022 and 2023, a candidate is eligible only if:
    - it improved every prior year available for the same city;
    - it did not increase prior max APE;
    - alpha <= 0.10 and cap <= 0.05;
    - the adjustment direction in the target year is the same sign as the
      average successful prior adjustment direction.

    If no candidate qualifies, keep baseline.
    """

    selected = []
    choices = []
    for (province, city), cg in candidates.groupby(["province_full", "city"]):
        for y in [2021, 2022, 2023]:
            base = cg[(cg["year"].eq(y)) & (cg["candidate"].eq("baseline"))].iloc[0]
            if y == 2021:
                chosen = base.copy()
                reason = "warmup_baseline"
            else:
                prior_years = [yy for yy in [2021, 2022] if yy < y]
                base_prior = cg[(cg["year"].isin(prior_years)) & (cg["candidate"].eq("baseline"))][
                    ["year", "abs_error_eok", "ape_pct"]
                ]
                eligible = []
                for cand, g in cg[cg["year"].isin(prior_years)].groupby("candidate"):
                    if cand == "baseline" or len(g) < len(prior_years):
                        continue
                    meta = g.iloc[0]
                    if float(meta["alpha"]) > 0.10 or float(meta["cap"]) > 0.05:
                        continue
                    merged = g[["year", "abs_error_eok", "ape_pct", "adjustment_ratio"]].merge(
                        base_prior, on="year", suffixes=("_cand", "_base")
                    )
                    if not (merged["abs_error_eok_cand"] <= merged["abs_error_eok_base"]).all():
                        continue
                    if not (merged["ape_pct_cand"] <= merged["ape_pct_base"]).all():
                        continue
                    target = cg[(cg["year"].eq(y)) & (cg["candidate"].eq(cand))]
                    if target.empty:
                        continue
                    target = target.iloc[0]
                    prior_direction = np.sign((merged["adjustment_ratio"] - 1.0).mean())
                    target_direction = np.sign(float(target["adjustment_ratio"]) - 1.0)
                    if prior_direction != 0 and target_direction != 0 and prior_direction != target_direction:
                        continue
                    total_prior = float(g["abs_error_eok"].sum())
                    alpha = float(meta["alpha"])
                    cap = float(meta["cap"])
                    eligible.append((total_prior, alpha, cap, cand, target))
                if eligible:
                    eligible.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
                    chosen = eligible[0][4].copy()
                    reason = "small_shift_prior_direction_pass"
                else:
                    chosen = base.copy()
                    reason = "fallback_no_small_shift_candidate"
            choices.append(
                {
                    "province_full": province,
                    "city": city,
                    "year": y,
                    "chosen_candidate": chosen["candidate"],
                    "reason": reason,
                    "block": infer_block(str(chosen.get("feature", ""))),
                    "alpha": float(chosen.get("alpha", 0.0)),
                    "cap": float(chosen.get("cap", 0.0)),
                    "adjustment_ratio": float(chosen.get("adjustment_ratio", 1.0)),
                }
            )
            selected.append(chosen)
    return pd.DataFrame(choices), pd.DataFrame(selected)


def guardrail(selected: pd.DataFrame, baseline: pd.DataFrame) -> tuple[bool, pd.DataFrame, pd.DataFrame]:
    overall = metric(selected).assign(policy="small_shift")
    base_overall = metric(baseline).assign(policy="baseline")
    city = metric(selected, ["province_full", "city"]).set_index(["province_full", "city"])
    base_city = metric(baseline, ["province_full", "city"]).set_index(["province_full", "city"])
    city_guard = city[["wape_pct", "over10_cells", "over20_cells", "max_ape_pct"]].join(
        base_city[["wape_pct", "over10_cells", "over20_cells", "max_ape_pct"]],
        lsuffix="_small_shift",
        rsuffix="_baseline",
    ).reset_index()
    city_guard["city_guard_pass"] = (
        city_guard["wape_pct_small_shift"].le(city_guard["wape_pct_baseline"])
        & city_guard["over10_cells_small_shift"].le(city_guard["over10_cells_baseline"])
        & city_guard["over20_cells_small_shift"].le(city_guard["over20_cells_baseline"])
        & city_guard["max_ape_pct_small_shift"].le(city_guard["max_ape_pct_baseline"])
    )
    pass_all = (
        float(overall["wape_pct"].iloc[0]) <= float(base_overall["wape_pct"].iloc[0])
        and int(overall["over10_cells"].iloc[0]) <= int(base_overall["over10_cells"].iloc[0])
        and int(overall["over20_cells"].iloc[0]) <= int(base_overall["over20_cells"].iloc[0])
        and float(overall["max_ape_pct"].iloc[0]) <= float(base_overall["max_ape_pct"].iloc[0])
        and bool(city_guard["city_guard_pass"].all())
    )
    summary = pd.concat([base_overall, overall], ignore_index=True)
    return pass_all, summary, city_guard


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = pd.read_csv(CAND)
    # Ensure only top5 candidate rows and baseline rows are used.
    baseline = candidates[candidates["candidate"].eq("baseline")].copy()
    choices, selected = select_small_shift(candidates)
    passed, summary, city_guard = guardrail(selected, baseline)

    detail = pd.concat(
        [
            baseline.assign(policy="baseline"),
            selected.assign(policy="small_shift_candidate"),
            (selected if passed else baseline).assign(policy="guarded_operational_" + ("candidate" if passed else "fallback")),
        ],
        ignore_index=True,
    )
    block_summary = (
        choices.groupby(["block", "reason"], as_index=False)
        .agg(cells=("year", "count"), active_cells=("adjustment_ratio", lambda s: int((s != 1.0).sum())))
        .sort_values(["block", "reason"])
    )

    choices.to_csv(OUT / "phase240_small_shift_choices.csv", index=False)
    selected.to_csv(OUT / "phase240_small_shift_selected_detail.csv", index=False)
    summary.to_csv(OUT / "phase240_small_shift_policy_summary.csv", index=False)
    city_guard.to_csv(OUT / "phase240_small_shift_city_guardrail.csv", index=False)
    detail.to_csv(OUT / "phase240_small_shift_policy_detail.csv", index=False)
    block_summary.to_csv(OUT / "phase240_small_shift_block_summary.csv", index=False)

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    report = "\n\n".join(
        [
            "# Phase240 건설업 top5 city-type small-shift route 감사",
            f"생성시각: {now}",
            "## 결론",
            (
                "- BuildingHUB 단일 보정 실패 이후, 기존 share를 거의 유지하는 small-shift route를 검증했다.\n"
                "- 후보는 과거연도에서 모든 prior year를 개선하고, alpha≤0.10·cap≤0.05이며, 조정 방향이 불일치하지 않을 때만 활성화했다.\n"
                f"- 전체 및 시군구별 guardrail 판정은 **{'통과' if passed else '실패'}**다.\n"
                f"- 따라서 운영 판정은 **{'small-shift 후보 채택' if passed else 'fallback 유지'}**다."
            ),
            "## 1. 정책 비교",
            md_table(
                summary,
                [
                    ("policy", "정책"),
                    ("rows", "셀"),
                    ("actual_sum_eok", "실제합_억원"),
                    ("abs_error_sum_eok", "절대오차_억원"),
                    ("wape_pct", "WAPE_%"),
                    ("over10_cells", "10%초과"),
                    ("over20_cells", "20%초과"),
                    ("max_ape_pct", "최대APE_%"),
                ],
            ),
            "## 2. 시군구별 guardrail",
            md_table(
                city_guard,
                [
                    ("province_full", "시도"),
                    ("city", "시군구"),
                    ("wape_pct_baseline", "기준WAPE_%"),
                    ("wape_pct_small_shift", "smallWAPE_%"),
                    ("max_ape_pct_baseline", "기준최대APE_%"),
                    ("max_ape_pct_small_shift", "small최대APE_%"),
                    ("city_guard_pass", "통과"),
                ],
            ),
            "## 3. 선택 후보",
            md_table(
                choices,
                [
                    ("province_full", "시도"),
                    ("city", "시군구"),
                    ("year", "연도"),
                    ("chosen_candidate", "선택후보"),
                    ("block", "블록"),
                    ("alpha", "alpha"),
                    ("cap", "cap"),
                    ("adjustment_ratio", "조정배율"),
                    ("reason", "이유"),
                ],
            ),
            "## 4. 블록별 요약",
            md_table(block_summary, [("block", "블록"), ("reason", "이유"), ("cells", "셀"), ("active_cells", "활성셀")]),
            "## 5. 판정",
            (
                "- 이 실험은 추가 API 없이 가능한 가장 보수적인 BuildingHUB small-shift 검증이다.\n"
                "- 여기서도 WAPE 10%에 접근하지 못하거나 guardrail을 통과하지 못하면, BuildingHUB만으로 건설업 병목을 해결하기 어렵다는 근거가 강화된다.\n"
                "- 다음 성능개선은 정비사업·공공/SOC·민간공사 전량자료를 별도 블록으로 수집한 뒤 같은 guardrail을 적용해야 한다.\n"
                "- PPS는 기존 local cache가 2021 일부월·2023 일부기간으로 불완전해, rolling route 선택에는 아직 쓰지 않는다."
            ),
            "## 산출 파일",
            (
                f"- `{OUT.relative_to(ROOT)}/phase240_small_shift_policy_summary.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase240_small_shift_city_guardrail.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase240_small_shift_choices.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase240_small_shift_policy_detail.csv`"
            ),
        ]
    )
    REPORT.write_text(report + "\n", encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
