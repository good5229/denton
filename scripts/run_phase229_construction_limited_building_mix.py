#!/usr/bin/env python3
"""Phase229: limited building-activity mix for construction spatial allocation.

Phase228 rejected replacing construction sigungu shares with BuildingHUB
activity shares.  This phase tests a safer design: retain the current share as
fallback and add building activity only as a small capped adjustment.

The local holdout is still Seoul Gangnam/Jongno only, so results are a
diagnostic guardrail experiment, not a nationwide adopted route.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE228 = DATA / "phase228_construction_buildinghub_sample_spatial_holdout"
OUTDIR = DATA / "phase229_construction_limited_building_mix"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase229_construction_limited_building_mix.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None, digits: int = 3) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "pp", "WAPE", "APE", "개")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            v = row.get(key, "")
            if isinstance(v, (float, np.floating)):
                vals.append(f"{float(v):,.{digits}f}")
            elif isinstance(v, (int, np.integer)):
                vals.append(f"{int(v):,}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def safe_share(values: pd.Series) -> pd.Series:
    v = pd.to_numeric(values, errors="coerce").fillna(0.0).clip(lower=0.0)
    s = float(v.sum())
    if s <= 0:
        return pd.Series(1.0 / len(v), index=v.index)
    return v / s


def capped_mix(base_share: pd.Series, signal_share: pd.Series, alpha: float, cap_pp: float) -> pd.Series:
    raw = base_share + alpha * (signal_share - base_share)
    cap = cap_pp / 100.0
    lower = (base_share - cap).clip(lower=0.0)
    upper = (base_share + cap).clip(upper=1.0)
    capped = raw.clip(lower=lower, upper=upper)
    total = float(capped.sum())
    if total <= 0:
        return base_share
    return capped / total


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    detail = pd.read_csv(PHASE228 / "phase228_seoul_pair_candidate_detail.csv")
    base = detail[detail["candidate_id"].eq("baseline_current_share")][
        ["year", "city", "actual_eok", "predicted_eok"]
    ].copy()
    signals = detail[~detail["candidate_id"].eq("baseline_current_share")][
        ["year", "city", "candidate_id", "candidate_label", "source_value"]
    ].copy()

    alphas = [0.01, 0.02, 0.05, 0.10, 0.15]
    caps = [1.0, 2.0, 3.0, 5.0, 10.0]
    rows = []
    cell_rows = []
    baseline_rows = []
    for year, g in base.groupby("year"):
        g = g.sort_values("city").reset_index(drop=True)
        total_actual = float(g["actual_eok"].sum())
        base_share = safe_share(g["predicted_eok"])
        base_pred = total_actual * base_share
        base_err = (base_pred - g["actual_eok"]).abs()
        baseline_wape = float(base_err.sum() / total_actual * 100)
        baseline_max_ape = float((base_err / g["actual_eok"].replace(0, np.nan) * 100).max())
        baseline_rows.append(
            {
                "year": int(year),
                "baseline_error_sum_eok": float(base_err.sum()),
                "baseline_wape_pct": baseline_wape,
                "baseline_max_ape_pct": baseline_max_ape,
            }
        )
        sig_year = signals[signals["year"].eq(year)].copy()
        for (candidate_id, label), sg in sig_year.groupby(["candidate_id", "candidate_label"], sort=False):
            pair = g.merge(sg[["city", "source_value"]], on="city", how="left").fillna({"source_value": 0.0})
            signal_share = safe_share(pair["source_value"])
            for alpha in alphas:
                for cap_pp in caps:
                    mix = capped_mix(base_share, signal_share, alpha, cap_pp)
                    pred = total_actual * mix
                    err = (pred - pair["actual_eok"]).abs()
                    ape = err / pair["actual_eok"].replace(0, np.nan) * 100
                    wape = float(err.sum() / total_actual * 100)
                    max_ape = float(ape.max())
                    rows.append(
                        {
                            "year": int(year),
                            "candidate_id": candidate_id,
                            "candidate_label": label,
                            "alpha": alpha,
                            "cap_pp": cap_pp,
                            "actual_sum_eok": total_actual,
                            "error_sum_eok": float(err.sum()),
                            "wape_pct": wape,
                            "max_ape_pct": max_ape,
                            "baseline_wape_pct": baseline_wape,
                            "baseline_max_ape_pct": baseline_max_ape,
                            "delta_wape_pp": wape - baseline_wape,
                            "delta_max_ape_pp": max_ape - baseline_max_ape,
                            "guardrail_pass": bool((wape <= baseline_wape + 1e-9) and (max_ape <= baseline_max_ape + 1e-9)),
                        }
                    )
                    for i, row in pair.iterrows():
                        cell_rows.append(
                            {
                                "year": int(year),
                                "city": row["city"],
                                "candidate_id": candidate_id,
                                "candidate_label": label,
                                "alpha": alpha,
                                "cap_pp": cap_pp,
                                "base_share_pct": float(base_share.loc[i] * 100),
                                "signal_share_pct": float(signal_share.loc[i] * 100),
                                "mixed_share_pct": float(mix.loc[i] * 100),
                                "actual_eok": float(row["actual_eok"]),
                                "predicted_eok": float(pred.loc[i]),
                                "error_eok": float(err.loc[i]),
                                "ape_pct": float(ape.loc[i]),
                            }
                        )

    summary = pd.DataFrame(rows)
    cells = pd.DataFrame(cell_rows)
    baseline = pd.DataFrame(baseline_rows)
    if not summary.empty:
        overall = (
            summary.groupby(["candidate_id", "candidate_label", "alpha", "cap_pp"], as_index=False)
            .agg(
                actual_sum_eok=("actual_sum_eok", "sum"),
                error_sum_eok=("error_sum_eok", "sum"),
                mean_wape_pct=("wape_pct", "mean"),
                max_wape_pct=("wape_pct", "max"),
                mean_max_ape_pct=("max_ape_pct", "mean"),
                max_ape_pct=("max_ape_pct", "max"),
                pass_years=("guardrail_pass", "sum"),
                tested_years=("guardrail_pass", "count"),
            )
        )
        overall["pooled_wape_pct"] = overall["error_sum_eok"] / overall["actual_sum_eok"] * 100
        baseline_error = float(baseline["baseline_error_sum_eok"].sum())
        baseline_actual = float(summary.drop_duplicates("year")["actual_sum_eok"].sum())
        baseline_pooled_wape = baseline_error / baseline_actual * 100
        overall["baseline_pooled_wape_pct"] = baseline_pooled_wape
        overall["delta_pooled_wape_pp"] = overall["pooled_wape_pct"] - baseline_pooled_wape
        overall["all_year_guardrail_pass"] = overall["pass_years"].eq(overall["tested_years"])
        overall = overall.sort_values(["all_year_guardrail_pass", "delta_pooled_wape_pp", "max_wape_pct"], ascending=[False, True, True])
    else:
        overall = pd.DataFrame()

    summary = summary.sort_values(["year", "guardrail_pass", "delta_wape_pp"], ascending=[True, False, True])
    cells = cells.sort_values(["year", "candidate_id", "alpha", "cap_pp", "city"])

    summary.to_csv(OUTDIR / "phase229_limited_mix_year_summary.csv", index=False, encoding="utf-8-sig")
    cells.to_csv(OUTDIR / "phase229_limited_mix_cell_detail.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUTDIR / "phase229_limited_mix_overall.csv", index=False, encoding="utf-8-sig")
    baseline.to_csv(OUTDIR / "phase229_limited_mix_baseline.csv", index=False, encoding="utf-8-sig")

    pass_all = overall[overall["all_year_guardrail_pass"]].copy() if not overall.empty else pd.DataFrame()
    best = overall.head(12) if not overall.empty else pd.DataFrame()
    best_pass = pass_all.head(12)
    best_by_year = summary.groupby("year", as_index=False).head(5) if not summary.empty else pd.DataFrame()

    report = f"""# 건설업 BuildingHUB 제한혼합 공간배분 실험

생성시각: {CREATED_AT}

## 목적

Phase228에서 건축활동 단일지표는 서울 강남구·종로구 건설업 공간배분을 크게 악화시켰다. 이번 실험은 기존 추정비중을 유지하면서 건축활동 share를 작은 비율로만 섞고, share 이동상한을 둔 제한혼합이 안전한지 확인한다.

## 설계

- 기준: 현행 추정비중
- 후보: 허가·착공·사용승인 면적/건수 등 BuildingHUB 활동 share
- 혼합: `기준 share + alpha × (활동 share - 기준 share)`
- 이동상한: 각 구의 share가 기준 대비 ±1/2/3/5/10%p 이상 움직이지 않도록 제한
- guardrail: 연도별 WAPE와 최대 APE가 모두 현행 기준보다 악화되지 않을 것

## 모든 연도 guardrail 통과 후보

{md_table(best_pass, [("candidate_label", "후보"), ("alpha", "alpha"), ("cap_pp", "상한 pp"), ("pooled_wape_pct", "pooled WAPE %"), ("baseline_pooled_wape_pct", "기준 pooled WAPE %"), ("delta_pooled_wape_pp", "변화 pp"), ("max_wape_pct", "최대 연도 WAPE %"), ("max_ape_pct", "최대 APE %"), ("pass_years", "통과연도"), ("tested_years", "검증연도")])}

## 전체 상위 후보

{md_table(best, [("candidate_label", "후보"), ("alpha", "alpha"), ("cap_pp", "상한 pp"), ("pooled_wape_pct", "pooled WAPE %"), ("baseline_pooled_wape_pct", "기준 pooled WAPE %"), ("delta_pooled_wape_pp", "변화 pp"), ("max_wape_pct", "최대 연도 WAPE %"), ("max_ape_pct", "최대 APE %"), ("pass_years", "통과연도"), ("tested_years", "검증연도"), ("all_year_guardrail_pass", "전체통과")])}

## 연도별 상위 후보

{md_table(best_by_year, [("year", "연도"), ("candidate_label", "후보"), ("alpha", "alpha"), ("cap_pp", "상한 pp"), ("wape_pct", "WAPE %"), ("baseline_wape_pct", "기준 WAPE %"), ("delta_wape_pp", "변화 pp"), ("max_ape_pct", "최대 APE %"), ("baseline_max_ape_pct", "기준 최대 APE %"), ("guardrail_pass", "통과")])}

## 판정

- 제한혼합은 건축활동 단일 대체보다 안전하지만, 모든 연도 guardrail을 통과하는 후보가 없다면 운영 route로 채택하지 않는다.
- 일부 연도만 좋아지는 후보는 건설업 공간배분의 보조 feature 후보로만 유지한다.
- 다음 단계는 정비사업·PPS·토목 자료를 추가해 블록별 제한혼합을 평가하는 것이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase229_limited_mix_overall.csv")


if __name__ == "__main__":
    main()
