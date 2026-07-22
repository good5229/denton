from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    status_path = DATA / "partial_stats_phase47_agri_status.json"
    summary_path = DATA / "partial_stats_phase47_agri_validation_summary.csv"
    sample_path = DATA / "partial_stats_phase47_agri_random_city_sample.csv"
    sido_path = DATA / "partial_stats_phase47_agri_sido_validation.csv"
    sigungu_path = DATA / "partial_stats_phase47_agri_sigungu_validation.csv"

    for path in (status_path, summary_path, sample_path, sido_path, sigungu_path):
        require(path.exists(), f"missing output: {path}")

    status = json.loads(status_path.read_text(encoding="utf-8"))
    numeric_keys = [
        "sido_general_mae_pp",
        "sido_census_sales_mae_pp",
        "sido_lag_mae_pp",
        "sido_specialized_mae_pp",
        "sigungu_general_mae_pp",
        "sigungu_census_sales_mae_pp",
        "sigungu_lag_mae_pp",
        "sigungu_specialized_mae_pp",
    ]
    for key in numeric_keys:
        value = status.get(key)
        require(value is not None and pd.notna(value), f"invalid status value: {key}")

    require(status["sido_rows"] > 0, "sido validation has no rows")
    require(status["sigungu_rows"] > 0, "sigungu validation has no rows")
    require(
        status["sido_specialized_mae_pp"] < status["sido_general_mae_pp"],
        "sido specialized model did not improve over general proxy",
    )
    require(
        status["sigungu_specialized_mae_pp"] < status["sigungu_general_mae_pp"],
        "sigungu specialized model did not improve over general proxy",
    )
    require(status["sigungu_specialized_model"] == "lag_share", "unexpected sigungu best model")

    summary = pd.read_csv(summary_path)
    require(not summary.empty, "summary is empty")
    require(not summary[summary.year.eq(0)].empty, "overall summary rows missing")
    require(summary[summary.level.eq("sigungu")].query("year != 0").improvement_pct.min() > 0, "not all sigungu years improved")

    sample = pd.read_csv(sample_path)
    require({"고양시", "포항시"}.issubset(set(sample.area_name)), "focus cities missing")
    require((sample.sample_group == "random_10").sum() == 10, "random sample size is not 10")
    require((sample.sample_group == "focus").sum() >= 2, "focus sample rows missing")

    print(
        json.dumps(
            {
                "ok": True,
                "sido_improvement_pct": status["sido_improvement_pct"],
                "sigungu_improvement_pct": status["sigungu_improvement_pct"],
                "sigungu_year_min_improvement_pct": float(summary[summary.level.eq("sigungu")].query("year != 0").improvement_pct.min()),
                "random_sample_n": int((sample.sample_group == "random_10").sum()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
