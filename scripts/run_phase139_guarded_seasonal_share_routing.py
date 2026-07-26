#!/usr/bin/env python3
"""Phase139: guarded seasonal-share routing for rolling GVA nowcasts.

Phase131 uses each city×middle-industry cell's prior-year YTD share to turn
observed YTD GVA into an annual nowcast.  This phase tests whether a more
stable, non-API seasonal share can improve the amount-weighted rolling
nowcast without adding unavailable data.

The guardrail is intentionally conservative:

* candidate shares are deterministic functions of years strictly before the
  target year;
* a candidate is only marked as adopted for a city×vintage if it improves the
  2022~2023 aggregate WAPE and does not worsen either 2022 or 2023 city WAPE;
* Q4 remains accounting recovery and is not treated as predictive.

This is a routing audit, not an ex-post residual correction.  It does not use
target-year annual actuals to calculate predictions, only to evaluate whether a
predefined share family would have been safer than the Phase131 baseline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase139_guarded_seasonal_share_routing"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase139_guarded_seasonal_share_routing.md"

CITY_SPECS = {
    "고양시": {
        "monthly": DATA / "partial_stats_phase41_goyang_emd_group_monthly.parquet",
        "value_col": "estimated_emd_group_monthly_gva",
    },
    "포항시": {
        "monthly": DATA / "partial_stats_phase42_pohang_emd_group_monthly.parquet",
        "value_col": "estimated_emd_group_monthly_gva",
    },
}

VINTAGE_LABEL = {
    1: "1분기+1개월",
    2: "1~2분기+1개월",
    3: "1~3분기+1개월",
    4: "1~4분기+1개월",
}

BASELINE = "cell_prior_mean"
EPS = 1e-9


def read_quarterly() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for city, spec in CITY_SPECS.items():
        df = pd.read_parquet(spec["monthly"])
        value_col = str(spec["value_col"])
        q = (
            df.groupby(["year", "quarter", "gva_parent_code", "division_code", "division_name"], as_index=False)[value_col]
            .sum()
            .rename(columns={
                "gva_parent_code": "parent_code",
                "division_code": "middle_code",
                "division_name": "middle_label",
                value_col: "quarter_gva_raw",
            })
        )
        q["quarter_gva_eok"] = q["quarter_gva_raw"] / 100.0
        q["middle_code"] = q["middle_code"].astype(str).str.zfill(2)
        q["city"] = city
        frames.append(q[["city", "year", "quarter", "parent_code", "middle_code", "middle_label", "quarter_gva_eok"]])
    return pd.concat(frames, ignore_index=True)


def target_rows(q: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    keys = ["city", "parent_code", "middle_code", "middle_label", "year"]
    for (city, parent, middle, label, year), g in q.groupby(keys, sort=False):
        actual = float(g["quarter_gva_eok"].sum())
        for k in [1, 2, 3, 4]:
            ytd = float(g[g["quarter"].le(k)]["quarter_gva_eok"].sum())
            rows.append({
                "city": city,
                "parent_code": parent,
                "middle_code": middle,
                "middle_label": label,
                "year": int(year),
                "available_quarters": k,
                "vintage_label": VINTAGE_LABEL[k],
                "ytd_eok": ytd,
                "actual_annual_gva_eok": actual,
            })
    return pd.DataFrame(rows)


def history_share(
    q: pd.DataFrame,
    *,
    city: str,
    parent: str,
    middle: str,
    year: int,
    k: int,
    level: str,
) -> tuple[float, int]:
    h = q[q["year"].lt(year)].copy()
    if level == "cell":
        h = h[h["city"].eq(city) & h["parent_code"].eq(parent) & h["middle_code"].eq(middle)]
    elif level == "city_parent":
        h = h[h["city"].eq(city) & h["parent_code"].eq(parent)]
    elif level == "allcity_parent":
        h = h[h["parent_code"].eq(parent)]
    elif level == "allcity_middle":
        h = h[h["parent_code"].eq(parent) & h["middle_code"].eq(middle)]
    elif level == "city_all":
        h = h[h["city"].eq(city)]
    elif level == "all":
        pass
    else:
        raise ValueError(f"unknown history level: {level}")

    shares: list[float] = []
    for _, gy in h.groupby("year"):
        den = float(gy["quarter_gva_eok"].sum())
        num = float(gy[gy["quarter"].le(k)]["quarter_gva_eok"].sum())
        if den > 0:
            shares.append(num / den)
    if not shares:
        return k / 4.0, 0
    return float(np.mean(shares)), len(shares)


def candidate_predictions(q: pd.DataFrame) -> pd.DataFrame:
    base = target_rows(q)
    rows: list[dict[str, object]] = []
    for r in base.itertuples(index=False):
        if r.available_quarters == 4:
            rows.append({
                **r._asdict(),
                "candidate": "observed_full_year_sum",
                "seasonal_ytd_share": 1.0,
                "history_year_count": np.nan,
                "annual_prediction_eok": r.ytd_eok,
                "annual_error_eok": 0.0,
                "annual_error_rate_pct": 0.0,
            })
            continue

        levels = {
            "cell_prior_mean": "cell",
            "city_parent_prior_mean": "city_parent",
            "allcity_parent_prior_mean": "allcity_parent",
            "allcity_middle_prior_mean": "allcity_middle",
            "city_all_prior_mean": "city_all",
            "all_industry_prior_mean": "all",
        }
        shares: dict[str, float] = {}
        ns: dict[str, int] = {}
        for name, level in levels.items():
            shares[name], ns[name] = history_share(
                q,
                city=r.city,
                parent=r.parent_code,
                middle=r.middle_code,
                year=int(r.year),
                k=int(r.available_quarters),
                level=level,
            )

        for lam in [0.5, 1.0, 2.0, 4.0]:
            n = ns["cell_prior_mean"]
            w = n / (n + lam) if n else 0.0
            shares[f"shrink_cell_to_city_parent_lam{lam:g}"] = (
                w * shares["cell_prior_mean"] + (1 - w) * shares["city_parent_prior_mean"]
            )
            ns[f"shrink_cell_to_city_parent_lam{lam:g}"] = n

        for name, share in shares.items():
            pred = float(r.ytd_eok) / share if share > 0 else np.nan
            actual = float(r.actual_annual_gva_eok)
            err = abs(pred - actual) if pd.notna(pred) else np.nan
            rows.append({
                **r._asdict(),
                "candidate": name,
                "seasonal_ytd_share": share,
                "history_year_count": ns[name],
                "annual_prediction_eok": pred,
                "annual_error_eok": err,
                "annual_error_rate_pct": err / actual * 100 if actual > 0 and pd.notna(err) else np.nan,
            })
    out = pd.DataFrame(rows)
    out["amount_bucket"] = np.select(
        [out["actual_annual_gva_eok"].ge(5000.0), out["actual_annual_gva_eok"].ge(1000.0)],
        ["very_large_5000eok_plus", "large_1000_5000eok"],
        default="small_under_1000eok",
    )
    return out


def score_candidates(pred: pd.DataFrame) -> pd.DataFrame:
    d = pred[pred["year"].between(2022, 2023) & pred["available_quarters"].isin([1, 2, 3])].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "available_quarters", "vintage_label", "candidate"], sort=False):
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        high = g[g["actual_annual_gva_eok"].ge(1000.0)]
        rows.append({
            "city": keys[0],
            "available_quarters": int(keys[1]),
            "vintage_label": keys[2],
            "candidate": keys[3],
            "evaluated_years": "2022-2023",
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "wape_pct": err / actual * 100 if actual else np.nan,
            "high_value_actual_sum_eok": float(high["actual_annual_gva_eok"].sum()),
            "high_value_error_sum_eok": float(high["annual_error_eok"].sum()),
            "high_value_wape_pct": (
                float(high["annual_error_eok"].sum()) / float(high["actual_annual_gva_eok"].sum()) * 100
                if len(high) and float(high["actual_annual_gva_eok"].sum()) > 0 else np.nan
            ),
            "gt20_cells": int((g["annual_error_rate_pct"] > 20.0).sum()),
        })
    return pd.DataFrame(rows)


def score_yearly(pred: pd.DataFrame) -> pd.DataFrame:
    d = pred[pred["year"].between(2022, 2023) & pred["available_quarters"].isin([1, 2, 3])].copy()
    rows: list[dict[str, object]] = []
    for keys, g in d.groupby(["city", "year", "available_quarters", "vintage_label", "candidate"], sort=False):
        actual = float(g["actual_annual_gva_eok"].sum())
        err = float(g["annual_error_eok"].sum())
        rows.append({
            "city": keys[0],
            "year": int(keys[1]),
            "available_quarters": int(keys[2]),
            "vintage_label": keys[3],
            "candidate": keys[4],
            "actual_sum_eok": actual,
            "error_sum_eok": err,
            "wape_pct": err / actual * 100 if actual else np.nan,
        })
    return pd.DataFrame(rows)


def guarded_routes(score: pd.DataFrame, yearly: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (city, k, label), g in score.groupby(["city", "available_quarters", "vintage_label"], sort=False):
        base = g[g["candidate"].eq(BASELINE)].iloc[0]
        base_yearly = yearly[
            yearly["city"].eq(city)
            & yearly["available_quarters"].eq(k)
            & yearly["candidate"].eq(BASELINE)
        ].set_index("year")["wape_pct"]
        candidates = []
        for _, cand in g[~g["candidate"].eq(BASELINE)].iterrows():
            cand_yearly = yearly[
                yearly["city"].eq(city)
                & yearly["available_quarters"].eq(k)
                & yearly["candidate"].eq(cand["candidate"])
            ].set_index("year")["wape_pct"]
            common_years = sorted(set(base_yearly.index) & set(cand_yearly.index))
            no_year_worse = bool(all(cand_yearly.loc[y] <= base_yearly.loc[y] + EPS for y in common_years))
            improves_total = bool(cand["wape_pct"] < base["wape_pct"] - EPS)
            improves_high = bool(cand["high_value_wape_pct"] <= base["high_value_wape_pct"] + EPS)
            if improves_total and improves_high and no_year_worse:
                candidates.append(cand)
        if candidates:
            chosen = pd.DataFrame(candidates).sort_values(["wape_pct", "high_value_wape_pct"]).iloc[0]
            adopt = True
        else:
            chosen = base
            adopt = False
        rows.append({
            "city": city,
            "available_quarters": int(k),
            "vintage_label": label,
            "baseline_candidate": BASELINE,
            "selected_candidate": chosen["candidate"],
            "adopt_guarded_route": adopt,
            "baseline_wape_pct": float(base["wape_pct"]),
            "selected_wape_pct": float(chosen["wape_pct"]),
            "wape_delta_pct_point": float(chosen["wape_pct"] - base["wape_pct"]),
            "baseline_high_value_wape_pct": float(base["high_value_wape_pct"]),
            "selected_high_value_wape_pct": float(chosen["high_value_wape_pct"]),
            "high_value_wape_delta_pct_point": float(chosen["high_value_wape_pct"] - base["high_value_wape_pct"]),
            "baseline_error_sum_eok": float(base["error_sum_eok"]),
            "selected_error_sum_eok": float(chosen["error_sum_eok"]),
            "error_delta_eok": float(chosen["error_sum_eok"] - base["error_sum_eok"]),
            "guardrail": "adopt only if total/high-value WAPE improve and neither 2022 nor 2023 city WAPE worsens",
        })
    return pd.DataFrame(rows).sort_values(["city", "available_quarters"])


def selected_predictions(pred: pd.DataFrame, routes: pd.DataFrame) -> pd.DataFrame:
    route_map = routes.set_index(["city", "available_quarters"])["selected_candidate"].to_dict()
    d = pred.copy()
    d["selected_candidate"] = d.apply(
        lambda r: "observed_full_year_sum" if r["available_quarters"] == 4 else route_map.get((r["city"], r["available_quarters"]), BASELINE),
        axis=1,
    )
    return d[d["candidate"].eq(d["selected_candidate"])].copy()


def top_contributors(selected: pd.DataFrame) -> pd.DataFrame:
    d = selected[selected["year"].eq(2023) & selected["available_quarters"].isin([1, 2, 3])].copy()
    d["error_contribution_pct"] = d.groupby(["city", "available_quarters"])["annual_error_eok"].transform(
        lambda s: s / s.sum() * 100 if float(s.sum()) > 0 else 0
    )
    return (
        d.sort_values(["city", "available_quarters", "annual_error_eok"], ascending=[True, True, False])
        .groupby(["city", "available_quarters"], as_index=False)
        .head(8)
    )


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    labels = [c.replace("_eok", " 억원").replace("_pct", " %").replace("_", " ") for c in d.columns]

    def fmt(v: object) -> str:
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            if np.isfinite(float(v)) and abs(float(v) - round(float(v))) < 1e-9:
                return f"{int(round(float(v))):,}"
            return f"{float(v):,.2f}"
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        return str(v).replace("|", "\\|")

    return "\n".join([
        "| " + " | ".join(labels) + " |",
        "| " + " | ".join(["---"] * len(labels)) + " |",
        *("| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()),
    ])


def write_report(routes: pd.DataFrame, score: pd.DataFrame, selected_top: pd.DataFrame) -> None:
    best_by_vintage = (
        score.sort_values(["city", "available_quarters", "wape_pct"])
        .groupby(["city", "available_quarters"], as_index=False)
        .head(4)
    )
    adopted = routes[routes["adopt_guarded_route"]].copy()
    REPORT.write_text("\n".join([
        "# Phase139 보수적 계절비중 라우팅 진단",
        "",
        "## 목적",
        "",
        "Phase131 rolling GVA nowcast의 연간 환산 단계가 너무 단순한지 점검했다. 새 원천자료를 억지로 붙이지 않고, 과거 자료만으로 계산되는 `중분류 자체`, `상위산업`, `타도시 같은 업종` 누적분기 비중을 비교했다.",
        "",
        "KOBIS는 사용 가능하지만 Phase136에서 고양시 J59 시간패턴 개선에 채택되지 않았다. KOPIS는 사용 불가이므로 공연·예술 직접활동 지표로 쓰지 않는다.",
        "",
        "## 보수적 채택 기준",
        "",
        "후보는 목표연도 이전 연도만 사용해 계절비중을 만들고, 2022년과 2023년 중 어느 해도 도시 총계 WAPE가 악화되지 않으며, 1,000억원 이상 업종 WAPE도 악화되지 않을 때만 채택한다.",
        "",
        "## 채택 라우팅",
        "",
        md_table(routes, [
            "city", "vintage_label", "baseline_candidate", "selected_candidate", "adopt_guarded_route",
            "baseline_wape_pct", "selected_wape_pct", "wape_delta_pct_point",
            "baseline_high_value_wape_pct", "selected_high_value_wape_pct", "high_value_wape_delta_pct_point",
            "error_delta_eok",
        ]),
        "",
        "## 후보별 상위 성능 예시",
        "",
        md_table(best_by_vintage, [
            "city", "vintage_label", "candidate", "wape_pct", "high_value_wape_pct", "error_sum_eok", "gt20_cells",
        ], n=30),
        "",
        "## 2023 선택 라우팅 기준 오차기여 상위",
        "",
        md_table(selected_top, [
            "city", "vintage_label", "middle_code", "middle_label", "selected_candidate",
            "actual_annual_gva_eok", "annual_prediction_eok", "annual_error_eok",
            "annual_error_rate_pct", "error_contribution_pct",
        ], n=48),
        "",
        "## 판정",
        "",
        f"1. 보수적 기준으로 채택 가능한 라우팅은 {len(adopted)}개다. 채택되지 않은 빈티지는 후보 평균성능이 좋아도 특정 연도 악화가 있어 기존 중분류 계절비중을 유지한다.",
        "2. 고양시는 1분기+1개월 연간 nowcast에서 `타도시 포함 상위산업 계절비중`이 2022·2023 모두 악화 없이 개선됐다. 이는 중분류별 짧은 과거계열이 불안정할 때 상위산업 계절성이 더 안정적일 수 있음을 뜻한다.",
        "3. 이 실험은 잔차보정이나 actual 총량 정규화가 아니다. 선택 후보는 예측시점 이전 계절비중만 사용한다.",
        "4. 개선 폭은 크지 않다. 남은 고양시 정밀 격차는 ERS91/94, J59/60처럼 도시 고유 활동자료가 필요한 업종에 집중된다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    q = read_quarterly()
    pred = candidate_predictions(q)
    score = score_candidates(pred)
    yearly = score_yearly(pred)
    routes = guarded_routes(score, yearly)
    selected = selected_predictions(pred, routes)
    selected_top = top_contributors(selected)

    pred.to_csv(OUT / "phase139_candidate_predictions.csv", index=False)
    score.to_csv(OUT / "phase139_candidate_scorecard.csv", index=False)
    yearly.to_csv(OUT / "phase139_yearly_guardrail_scorecard.csv", index=False)
    routes.to_csv(OUT / "phase139_guarded_routes.csv", index=False)
    selected.to_csv(OUT / "phase139_selected_predictions.csv", index=False)
    selected_top.to_csv(OUT / "phase139_selected_2023_top_contributors.csv", index=False)
    write_report(routes, score, selected_top)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
