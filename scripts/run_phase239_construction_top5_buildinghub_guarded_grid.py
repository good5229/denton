"""Phase239 top5 BuildingHUB guarded-grid audit for construction.

Uses the top5 BuildingHUB collection and a more conservative grid suggested by
the scientist reviewer.  The output answers whether the signal from
Pyeongtaek generalizes to several high-error construction cities without
violating no-worse guardrails.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/phase239_construction_top5_buildinghub_guarded_grid"
REPORT = ROOT / "reports/partial_statistics_estimation_phase239_construction_top5_buildinghub_guarded_grid.md"
EVENTS = ROOT / "data/processed/buildinghub_priority_events_phase239_top5_construction.csv"
MANIFEST = ROOT / "data/processed/buildinghub_priority_events_manifest_phase239_top5_construction.csv"
AUDIT = ROOT / "nationwide/outputs/annual_sigungu_activity_error_audit.csv"
PRIORITY = ROOT / "nationwide/outputs/construction_buildinghub_collection_priority.csv"


FEATURES = [
    "permit_전체_area",
    "permit_전체_count",
    "permit_산업·창고_area",
    "permit_상업·업무_area",
    "permit_주거_area",
    "start_전체_area",
    "start_전체_count",
    "approval_전체_area",
    "approval_전체_count",
]
ALPHAS = [0.02, 0.05, 0.10, 0.15]
CAPS = [0.02, 0.05, 0.10]


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


def annual_features(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for event, col in [("permit", "permit_date"), ("start", "start_date"), ("approval", "approval_date")]:
        d = events.dropna(subset=[col]).copy()
        d["year"] = d[col].dt.year
        d = d[(d["year"] >= 2019) & (d["year"] <= 2023)]
        for (province, city, year), gy in d.groupby(["province_full", "city", "year"]):
            for group in ["전체", "산업·창고", "상업·업무", "주거"]:
                g = gy if group == "전체" else gy[gy["use_group"].eq(group)]
                rows.append(
                    {
                        "province_full": province,
                        "city": city,
                        "year": int(year),
                        "feature": f"{event}_{group}_area",
                        "value": float(g["total_floor_area"].sum()),
                    }
                )
                rows.append(
                    {
                        "province_full": province,
                        "city": city,
                        "year": int(year),
                        "feature": f"{event}_{group}_count",
                        "value": float(len(g)),
                    }
                )
    return pd.DataFrame(rows)


def build_candidates(base: pd.DataFrame, feat: pd.DataFrame) -> pd.DataFrame:
    wide = feat.pivot_table(index=["province_full", "city", "year"], columns="feature", values="value", aggfunc="sum")
    rows: list[dict[str, object]] = []
    for _, b in base.iterrows():
        province = str(b["province_full"])
        city = str(b["city"])
        y = int(b["year"])
        pred0 = float(b["predicted_eok"])
        actual = float(b["actual_eok"])
        rows.append(
            {
                "province_full": province,
                "city": city,
                "year": y,
                "candidate": "baseline",
                "feature": "",
                "alpha": 0.0,
                "cap": 0.0,
                "predicted_eok": pred0,
                "actual_eok": actual,
                "abs_error_eok": abs(pred0 - actual),
                "ape_pct": abs(pred0 - actual) / actual * 100,
                "feature_ratio": np.nan,
                "adjustment_ratio": 1.0,
            }
        )
        idx = (province, city, y)
        pidx = (province, city, y - 1)
        if idx not in wide.index or pidx not in wide.index:
            continue
        for feature in FEATURES:
            if feature not in wide.columns:
                continue
            cur = float(wide.loc[idx, feature] or 0.0)
            prev = float(wide.loc[pidx, feature] or 0.0)
            if cur <= 0 or prev <= 0:
                continue
            ratio = cur / prev
            change = ratio - 1.0
            for cap in CAPS:
                clipped = float(np.clip(change, -cap, cap))
                for alpha in ALPHAS:
                    adj = max(0.05, 1 + alpha * clipped)
                    pred = pred0 * adj
                    rows.append(
                        {
                            "province_full": province,
                            "city": city,
                            "year": y,
                            "candidate": f"{feature}_alpha{alpha:.2f}_cap{cap:.2f}",
                            "feature": feature,
                            "alpha": alpha,
                            "cap": cap,
                            "predicted_eok": pred,
                            "actual_eok": actual,
                            "abs_error_eok": abs(pred - actual),
                            "ape_pct": abs(pred - actual) / actual * 100,
                            "feature_ratio": ratio,
                            "adjustment_ratio": adj,
                        }
                    )
    return pd.DataFrame(rows)


def select_prior(candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    selections: list[dict[str, object]] = []
    selected_rows: list[pd.Series] = []
    for (province, city), cg in candidates.groupby(["province_full", "city"]):
        for y in [2021, 2022, 2023]:
            base_row = cg[(cg["year"].eq(y)) & (cg["candidate"].eq("baseline"))].iloc[0]
            if y == 2021:
                chosen = base_row
                reason = "first_year_fallback"
            else:
                prior_years = [yy for yy in [2021, 2022, 2023] if yy < y]
                prior = cg[cg["year"].isin(prior_years)].copy()
                base_prior = prior[prior["candidate"].eq("baseline")][["year", "abs_error_eok"]]
                ok: list[tuple[float, float, float, str]] = []
                for cand, g in prior.groupby("candidate"):
                    if cand == "baseline" or len(g) < len(prior_years):
                        continue
                    merged = g[["year", "abs_error_eok"]].merge(
                        base_prior, on="year", suffixes=("_candidate", "_baseline")
                    )
                    if not (merged["abs_error_eok_candidate"] <= merged["abs_error_eok_baseline"]).all():
                        continue
                    total = float(g["abs_error_eok"].sum())
                    base_total = float(base_prior["abs_error_eok"].sum())
                    if total < base_total:
                        meta = g.iloc[0]
                        ok.append((total, float(meta["alpha"]), float(meta["cap"]), cand))
                if ok:
                    ok.sort()
                    cand = ok[0][3]
                    chosen = cg[(cg["year"].eq(y)) & (cg["candidate"].eq(cand))].iloc[0]
                    reason = "prior_no_worse_lower_error"
                else:
                    chosen = base_row
                    reason = "no_prior_candidate_passed"
            selections.append(
                {
                    "province_full": province,
                    "city": city,
                    "year": y,
                    "chosen_candidate": chosen["candidate"],
                    "reason": reason,
                }
            )
            selected_rows.append(chosen)
    return pd.DataFrame(selections), pd.DataFrame(selected_rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(EVENTS, parse_dates=["permit_date", "start_date", "approval_date", "created_at"])
    manifest = pd.read_csv(MANIFEST)
    priority = pd.read_csv(PRIORITY).head(5)
    audit = pd.read_csv(AUDIT)
    base = audit[
        audit["activity"].eq("건설업")
        & audit["year"].between(2021, 2023)
        & audit["city"].isin(priority["city"])
        & audit["province_full"].isin(priority["province_full"])
    ].copy()
    # Avoid accidental same-name city collisions.
    base = base.merge(priority[["province_full", "city", "priority_rank"]], on=["province_full", "city"], how="inner")

    feat = annual_features(events)
    candidates = build_candidates(base, feat)
    selections, prior_selected = select_prior(candidates)
    baseline = candidates[candidates["candidate"].eq("baseline")].copy()

    baseline_summary = metric(baseline).assign(policy="baseline")
    prior_summary = metric(prior_selected).assign(policy="prior_selected_diagnostic")
    baseline_city_for_guard = metric(baseline, ["province_full", "city"]).set_index(["province_full", "city"])
    prior_city_for_guard = metric(prior_selected, ["province_full", "city"]).set_index(["province_full", "city"])
    pass_guard = (
        float(prior_summary["wape_pct"].iloc[0]) <= float(baseline_summary["wape_pct"].iloc[0])
        and int(prior_summary["over10_cells"].iloc[0]) <= int(baseline_summary["over10_cells"].iloc[0])
        and int(prior_summary["over20_cells"].iloc[0]) <= int(baseline_summary["over20_cells"].iloc[0])
        and float(prior_summary["max_ape_pct"].iloc[0]) <= float(baseline_summary["max_ape_pct"].iloc[0])
        and (
            prior_city_for_guard["wape_pct"].le(baseline_city_for_guard["wape_pct"]).all()
            and prior_city_for_guard["over10_cells"].le(baseline_city_for_guard["over10_cells"]).all()
            and prior_city_for_guard["over20_cells"].le(baseline_city_for_guard["over20_cells"]).all()
            and prior_city_for_guard["max_ape_pct"].le(baseline_city_for_guard["max_ape_pct"]).all()
        )
    )
    guarded = prior_selected.copy() if pass_guard else baseline.copy()
    guarded_summary = metric(guarded).assign(
        policy="guarded_operational_candidate" if pass_guard else "guarded_operational_fallback"
    )
    summary = pd.concat([baseline_summary, prior_summary, guarded_summary], ignore_index=True)

    city_summary = pd.concat(
        [
            metric(baseline, ["province_full", "city"]).assign(policy="baseline"),
            metric(prior_selected, ["province_full", "city"]).assign(policy="prior_selected_diagnostic"),
        ],
        ignore_index=True,
    ).sort_values(["city", "policy"])
    city_guard = (
        prior_city_for_guard[["wape_pct", "over10_cells", "over20_cells", "max_ape_pct"]]
        .join(
            baseline_city_for_guard[["wape_pct", "over10_cells", "over20_cells", "max_ape_pct"]],
            lsuffix="_prior",
            rsuffix="_baseline",
        )
        .reset_index()
    )
    city_guard["city_guard_pass"] = (
        city_guard["wape_pct_prior"].le(city_guard["wape_pct_baseline"])
        & city_guard["over10_cells_prior"].le(city_guard["over10_cells_baseline"])
        & city_guard["over20_cells_prior"].le(city_guard["over20_cells_baseline"])
        & city_guard["max_ape_pct_prior"].le(city_guard["max_ape_pct_baseline"])
    )

    collection = (
        manifest.groupby(["province_full", "city"], as_index=False)
        .agg(
            legal_dongs=("bjdong_cd", "count"),
            api_pages=("requested_pages", "sum"),
            event_rows=("received_rows", "sum"),
            error_legal_dongs=("error", lambda s: int(s.notna().sum())),
            legal_dongs_with_rows=("received_rows", lambda s: int((s > 0).sum())),
        )
        .merge(priority[["province_full", "city", "priority_rank"]], on=["province_full", "city"], how="left")
        .sort_values("priority_rank")
    )

    # Candidate best cases are diagnostic only; they show signal existence, not
    # an adoptable rule.
    best_by_city_year = (
        candidates.sort_values(["province_full", "city", "year", "ape_pct"])
        .groupby(["province_full", "city", "year"], as_index=False)
        .head(1)
        .sort_values(["province_full", "city", "year"])
    )

    feat.to_csv(OUT / "phase239_top5_buildinghub_annual_features.csv", index=False)
    candidates.to_csv(OUT / "phase239_top5_candidate_detail.csv", index=False)
    selections.to_csv(OUT / "phase239_top5_prior_selections.csv", index=False)
    prior_selected.to_csv(OUT / "phase239_top5_prior_selected_detail.csv", index=False)
    summary.to_csv(OUT / "phase239_top5_policy_summary.csv", index=False)
    city_summary.to_csv(OUT / "phase239_top5_city_policy_summary.csv", index=False)
    city_guard.to_csv(OUT / "phase239_top5_city_guardrail.csv", index=False)
    collection.to_csv(OUT / "phase239_top5_collection_quality.csv", index=False)
    best_by_city_year.to_csv(OUT / "phase239_top5_best_case_by_city_year.csv", index=False)

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    report = "\n\n".join(
        [
            "# Phase239 건설업 BuildingHUB top5 보수 grid 검증",
            f"생성시각: {now}",
            "## 결론",
            (
                "- top5 오차기여 시군구에 대해 BuildingHUB event를 수집하고 보수 alpha/cap grid를 적용했다.\n"
                "- 과학자 검토를 반영해 alpha는 0.02~0.15, cap은 0.02~0.10으로 낮췄다.\n"
                "- prior-selected 후보가 전체 및 시군구별 guardrail을 통과하지 못하면 운영 route는 fallback이다.\n"
                f"- 이번 top5 guarded 판정은 **{'candidate 채택' if pass_guard else 'fallback 유지'}**다."
            ),
            "## 1. 수집 품질",
            md_table(
                collection,
                [
                    ("priority_rank", "순위"),
                    ("province_full", "시도"),
                    ("city", "시군구"),
                    ("legal_dongs", "법정동"),
                    ("api_pages", "API page"),
                    ("event_rows", "event 행"),
                    ("error_legal_dongs", "에러 법정동"),
                    ("legal_dongs_with_rows", "행 보유 법정동"),
                ],
            ),
            "## 2. top5 전체 정책 비교",
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
            "## 3. 시군구별 비교",
            md_table(
                city_summary,
                [
                    ("policy", "정책"),
                    ("province_full", "시도"),
                    ("city", "시군구"),
                    ("actual_sum_eok", "실제합_억원"),
                    ("abs_error_sum_eok", "절대오차_억원"),
                    ("wape_pct", "WAPE_%"),
                    ("over10_cells", "10%초과"),
                    ("max_ape_pct", "최대APE_%"),
                ],
            ),
            "## 4. prior-selected 후보",
            md_table(
                selections,
                [
                    ("province_full", "시도"),
                    ("city", "시군구"),
                    ("year", "연도"),
                    ("chosen_candidate", "선택후보"),
                    ("reason", "이유"),
                ],
            ),
            "## 5. 시군구별 guardrail",
            md_table(
                city_guard,
                [
                    ("province_full", "시도"),
                    ("city", "시군구"),
                    ("wape_pct_baseline", "기준WAPE_%"),
                    ("wape_pct_prior", "priorWAPE_%"),
                    ("max_ape_pct_baseline", "기준최대APE_%"),
                    ("max_ape_pct_prior", "prior최대APE_%"),
                    ("city_guard_pass", "시군구통과"),
                ],
            ),
            "## 6. best-case 후보 참고",
            "아래 표는 actual을 보고 고른 후보라 운영 성능이 아니다. 어떤 feature가 방향성을 갖는지 확인하기 위한 참고표다.",
            md_table(
                best_by_city_year,
                [
                    ("province_full", "시도"),
                    ("city", "시군구"),
                    ("year", "연도"),
                    ("candidate", "best 후보"),
                    ("predicted_eok", "추정_억원"),
                    ("actual_eok", "실제_억원"),
                    ("ape_pct", "APE_%"),
                    ("feature_ratio", "feature ratio"),
                    ("adjustment_ratio", "조정배율"),
                ],
                max_rows=20,
            ),
            "## 7. 판정",
            (
                "- top5 결과는 건축HUB 신호가 일부 지역·연도에 존재함을 보여준다.\n"
                "- pooled WAPE가 소폭 좋아져도 시군구별 WAPE 또는 최대 APE가 악화되면 건설업 운영 route로 채택하지 않는다.\n"
                "- 서울권 고오차 지역은 허가/착공 총량보다 정비사업·대형 상업건축·본사/수주 소재지 요인이 섞여 있어 별도 블록이 필요하다.\n"
                "- 다음 개선은 BuildingHUB 단일 보정이 아니라 `정비사업 블록 + 공공/SOC 블록 + 기존 share 이동상한` 결합으로 가야 한다."
            ),
            "## 산출 파일",
            (
                f"- `{OUT.relative_to(ROOT)}/phase239_top5_policy_summary.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase239_top5_city_policy_summary.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase239_top5_city_guardrail.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase239_top5_candidate_detail.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase239_top5_collection_quality.csv`"
            ),
        ]
    )
    REPORT.write_text(report + "\n", encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
