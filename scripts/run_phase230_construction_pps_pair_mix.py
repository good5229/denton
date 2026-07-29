#!/usr/bin/env python3
"""Phase230: PPS public-construction block test for Seoul pair.

After BuildingHUB failed the spatial-allocation guardrail for Gangnam/Jongno,
test whether PPS public construction notices/amounts provide a safer
public/civil-works block signal.

Local PPS coverage currently supports 2021 Jan-Mar, Apr, May.  Therefore this
is a 2021-only diagnostic, not an adopted route.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nationwide" / "outputs"
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase230_construction_pps_pair_mix"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase230_construction_pps_pair_mix.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

PPS_FILES = {
    "2021Q1": OUT / "pps_construction_nationwide_sigungu_year_202101_202103.csv",
    "2021M04": OUT / "pps_construction_nationwide_sigungu_year_202104_202104_robust_n100_complete.csv",
    "2021M05": OUT / "pps_construction_nationwide_sigungu_year_202105_202105_robust_n100_complete.csv",
}


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
    total = float(v.sum())
    if total <= 0:
        return pd.Series(1.0 / len(v), index=v.index)
    return v / total


def capped_mix(base_share: pd.Series, signal_share: pd.Series, alpha: float, cap_pp: float) -> pd.Series:
    raw = base_share + alpha * (signal_share - base_share)
    cap = cap_pp / 100.0
    lower = (base_share - cap).clip(lower=0)
    upper = (base_share + cap).clip(upper=1)
    capped = raw.clip(lower=lower, upper=upper)
    s = float(capped.sum())
    if s <= 0:
        return base_share
    return capped / s


def load_base() -> pd.DataFrame:
    audit = pd.read_csv(OUT / "annual_sigungu_activity_error_audit.csv")
    b = audit[
        (audit["activity"].eq("건설업"))
        & (audit["city"].isin(["강남구", "종로구"]))
        & (audit["year"].eq(2021))
    ].copy()
    b["actual_eok"] = pd.to_numeric(b["actual_eok"], errors="coerce")
    b["predicted_eok"] = pd.to_numeric(b["predicted_eok"], errors="coerce")
    return b[["city", "actual_eok", "predicted_eok"]].sort_values("city").reset_index(drop=True)


def load_pps() -> pd.DataFrame:
    frames = []
    for tag, path in PPS_FILES.items():
        df = pd.read_csv(path)
        df = df[(df["year"].eq(2021)) & (df["city"].isin(["강남구", "종로구"]))].copy()
        df["period_tag"] = tag
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    cumulative = (
        raw.groupby(["city", "year"], as_index=False)
        .agg(
            pps_construction_notices=("pps_construction_notices", "sum"),
            pps_construction_amount_eok=("pps_construction_amount_eok", "sum"),
        )
    )
    cumulative["period_tag"] = "2021M01_M05"
    raw = pd.concat([raw, cumulative], ignore_index=True)
    return raw


def evaluate(base: pd.DataFrame, pps: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    total_actual = float(base["actual_eok"].sum())
    base_share = safe_share(base["predicted_eok"])
    base_pred = total_actual * base_share
    base_err = (base_pred - base["actual_eok"]).abs()
    base_ape = base_err / base["actual_eok"].replace(0, np.nan) * 100
    baseline_wape = float(base_err.sum() / total_actual * 100)
    baseline_max_ape = float(base_ape.max())

    rows = [
        {
            "period_tag": "baseline",
            "signal_type": "현행 추정비중",
            "mode": "baseline",
            "alpha": 0.0,
            "cap_pp": 0.0,
            "actual_sum_eok": total_actual,
            "error_sum_eok": float(base_err.sum()),
            "wape_pct": baseline_wape,
            "max_ape_pct": baseline_max_ape,
            "baseline_wape_pct": baseline_wape,
            "baseline_max_ape_pct": baseline_max_ape,
            "delta_wape_pp": 0.0,
            "delta_max_ape_pp": 0.0,
            "guardrail_pass": True,
        }
    ]
    cell_rows = []
    for period, pg in pps.groupby("period_tag"):
        pair = base.merge(
            pg[["city", "pps_construction_notices", "pps_construction_amount_eok"]],
            on="city",
            how="left",
        ).fillna(0.0)
        signals = [
            ("PPS 금액", "pps_construction_amount_eok"),
            ("PPS 공고건수", "pps_construction_notices"),
        ]
        for signal_type, col in signals:
            signal_share = safe_share(pair[col])
            for mode, alpha, cap_pp in [("single", 1.0, 100.0)]:
                shares = signal_share
                pred = total_actual * shares
                err = (pred - pair["actual_eok"]).abs()
                ape = err / pair["actual_eok"].replace(0, np.nan) * 100
                rows.append(
                    {
                        "period_tag": period,
                        "signal_type": signal_type,
                        "mode": mode,
                        "alpha": alpha,
                        "cap_pp": cap_pp,
                        "actual_sum_eok": total_actual,
                        "error_sum_eok": float(err.sum()),
                        "wape_pct": float(err.sum() / total_actual * 100),
                        "max_ape_pct": float(ape.max()),
                        "baseline_wape_pct": baseline_wape,
                        "baseline_max_ape_pct": baseline_max_ape,
                        "delta_wape_pp": float(err.sum() / total_actual * 100) - baseline_wape,
                        "delta_max_ape_pp": float(ape.max()) - baseline_max_ape,
                        "guardrail_pass": bool((err.sum() / total_actual * 100 <= baseline_wape + 1e-9) and (ape.max() <= baseline_max_ape + 1e-9)),
                    }
                )
            for alpha in [0.01, 0.02, 0.05, 0.10]:
                for cap_pp in [1.0, 2.0, 3.0, 5.0]:
                    shares = capped_mix(base_share, signal_share, alpha, cap_pp)
                    pred = total_actual * shares
                    err = (pred - pair["actual_eok"]).abs()
                    ape = err / pair["actual_eok"].replace(0, np.nan) * 100
                    wape = float(err.sum() / total_actual * 100)
                    max_ape = float(ape.max())
                    rows.append(
                        {
                            "period_tag": period,
                            "signal_type": signal_type,
                            "mode": "limited_mix",
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
                                "period_tag": period,
                                "signal_type": signal_type,
                                "mode": "limited_mix",
                                "alpha": alpha,
                                "cap_pp": cap_pp,
                                "city": row["city"],
                                "base_share_pct": float(base_share.loc[i] * 100),
                                "signal_share_pct": float(signal_share.loc[i] * 100),
                                "mixed_share_pct": float(shares.loc[i] * 100),
                                "actual_eok": float(row["actual_eok"]),
                                "predicted_eok": float(pred.loc[i]),
                                "error_eok": float(err.loc[i]),
                                "ape_pct": float(ape.loc[i]),
                            }
                        )
    return pd.DataFrame(rows), pd.DataFrame(cell_rows)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = load_base()
    pps = load_pps()
    summary, detail = evaluate(base, pps)
    summary = summary.sort_values(["guardrail_pass", "wape_pct", "max_ape_pct"], ascending=[False, True, True])
    passed = summary[(summary["guardrail_pass"]) & (summary["mode"].ne("baseline"))].copy()

    base.to_csv(OUTDIR / "phase230_seoul_pair_base.csv", index=False, encoding="utf-8-sig")
    pps.to_csv(OUTDIR / "phase230_seoul_pair_pps_signal.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase230_pps_pair_summary.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase230_pps_pair_detail.csv", index=False, encoding="utf-8-sig")

    report = f"""# 건설업 PPS 공공공사 블록 서울 pair 실험

생성시각: {CREATED_AT}

## 목적

BuildingHUB 단일·제한혼합이 서울 강남구·종로구 공간배분 guardrail을 통과하지 못했으므로, 공공·토목 블록 후보인 조달청 공사공고(PPS) 금액·공고건수 신호를 같은 pair에서 점검한다.

## 자료

- actual: 2021년 서울 강남구·종로구 건설업 GVA
- 기준: 기존 추정비중
- PPS: 2021년 1~3월, 4월, 5월, 1~5월 누적 공사공고 금액·공고건수

## guardrail 통과 후보

{md_table(passed, [("period_tag", "기간"), ("signal_type", "신호"), ("mode", "방식"), ("alpha", "alpha"), ("cap_pp", "상한 pp"), ("wape_pct", "WAPE %"), ("baseline_wape_pct", "기준 WAPE %"), ("delta_wape_pp", "변화 pp"), ("max_ape_pct", "최대 APE %"), ("baseline_max_ape_pct", "기준 최대 APE %")], 20)}

## 전체 상위 후보

{md_table(summary, [("period_tag", "기간"), ("signal_type", "신호"), ("mode", "방식"), ("alpha", "alpha"), ("cap_pp", "상한 pp"), ("wape_pct", "WAPE %"), ("baseline_wape_pct", "기준 WAPE %"), ("delta_wape_pp", "변화 pp"), ("max_ape_pct", "최대 APE %"), ("baseline_max_ape_pct", "기준 최대 APE %"), ("guardrail_pass", "통과")], 25)}

## 판정

- PPS는 공공공사/토목 블록 후보이지만, 강남·종로 2021 pair에서는 현행 기준보다 강남 share를 낮추는 방향이라 단일 대체는 위험하다.
- 제한혼합에서 guardrail 통과 후보가 있으면 공공·토목 미세보정 후보로 유지한다.
- 통과 후보가 없으면 PPS도 서울 pair 기준으로는 단독/미세보정 모두 미채택하고, 전국·다년 rolling 검증으로만 후보를 유지한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase230_pps_pair_summary.csv")


if __name__ == "__main__":
    main()
