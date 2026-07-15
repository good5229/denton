from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from data_availability import ReleaseRule, annual_forecast_origin, is_available_as_of, quarter_sort_key
from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


DEFAULT_QUARTERLY_RELEASE_RULE = ReleaseRule(
    source="FRED/ECOS quarterly transformed indicator",
    frequency="Q",
    publication_lag_months=1,
    note="Use only quarters released before the annual forecast origin.",
)

FORECAST_ORIGIN_MONTH = 1
FORECAST_ORIGIN_DAY = 1
FEATURE_SOURCE_FILE = "energy_exogenous_with_ecos_quarterly.csv"


def indicator_release_rule(indicator: str, source: str) -> ReleaseRule:
    # Quarterly FRED and ECOS price/fx inputs are treated as short-lag indicators.
    # The forecast filter still prevents target-year observations from leaking in.
    return DEFAULT_QUARTERLY_RELEASE_RULE


def load_quarterly_features() -> dict[str, dict[str, dict[str, Any]]]:
    quarterly: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_csv(PROCESSED_DIR / FEATURE_SOURCE_FILE):
        value = parse_number(row.get("quarterly_average"))
        period = row.get("period", "")
        indicator = row.get("indicator", "")
        if value is None or len(period) < 6 or not indicator:
            continue
        source = row.get("source", "")
        rule = indicator_release_rule(indicator, source)
        quarterly[indicator][period] = {
            "value": value,
            "source": source,
            "release_lag_months": rule.publication_lag_months,
            "description": row.get("description", ""),
        }
    return quarterly


def load_annual_features() -> dict[int, dict[str, float]]:
    quarterly = load_quarterly_features()
    features: dict[int, dict[str, float]] = defaultdict(dict)
    for target_year in range(2015, 2027):
        as_of = annual_forecast_origin(target_year, FORECAST_ORIGIN_MONTH, FORECAST_ORIGIN_DAY)
        for indicator, by_period in quarterly.items():
            available = [
                (period, payload)
                for period, payload in by_period.items()
                if is_available_as_of(
                    period,
                    "Q",
                    int(payload["release_lag_months"]),
                    as_of,
                )
            ]
            available.sort(key=lambda item: quarter_sort_key(item[0]))
            if len(available) < 8:
                continue
            recent4 = available[-4:]
            previous4 = available[-8:-4]
            level = mean(float(payload["value"]) for _, payload in recent4)
            prev = mean(float(payload["value"]) for _, payload in previous4)
            features[target_year][f"{indicator}_latest4q_level"] = level
            if prev:
                features[target_year][f"{indicator}_latest4q_yoy_pct"] = (level / prev - 1.0) * 100.0
            features[target_year][f"{indicator}_latest_period_end"] = float(recent4[-1][0].replace("Q", "."))
    return features


def feature_names(features: dict[int, dict[str, float]]) -> list[str]:
    names = sorted({name for by_year in features.values() for name in by_year})
    return [name for name in names if not name.endswith("_latest_period_end")]


def load_d00_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "rolling_annual_prediction_comparisons.csv"):
        if row.get("sector_code") != "D00":
            continue
        predicted = parse_number(row.get("predicted_annual_gva"))
        actual = parse_number(row.get("actual_annual_gva"))
        year = parse_number(row.get("target_year"))
        if predicted is None or actual is None or predicted == 0 or actual == 0 or year is None:
            continue
        item = dict(row)
        item["_year"] = int(year)
        item["_predicted"] = predicted
        item["_actual"] = actual
        item["_baseline_ape"] = abs(predicted - actual) / actual * 100.0
        item["_ratio"] = actual / predicted
        rows.append(item)
    return rows


def fit_univariate(xs: list[float], ys: list[float]) -> tuple[float, float] | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx, my = mean(xs), mean(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom <= 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    intercept = my - slope * mx
    return intercept, slope


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def evaluate_feature(training: list[dict[str, Any]], features: dict[int, dict[str, float]], feature: str) -> dict[str, Any] | None:
    xs: list[float] = []
    ys: list[float] = []
    for row in training:
        x = features.get(row["_year"], {}).get(feature)
        if x is None:
            continue
        xs.append(x)
        ys.append(float(row["_ratio"]))
    fit = fit_univariate(xs, ys)
    if fit is None:
        return None
    intercept, slope = fit
    adjusted_apes: list[float] = []
    baseline_apes: list[float] = []
    for row in training:
        x = features.get(row["_year"], {}).get(feature)
        if x is None:
            continue
        correction = clamp(intercept + slope * x, 0.75, 1.25)
        adjusted = float(row["_predicted"]) * correction
        actual = float(row["_actual"])
        adjusted_apes.append(abs(adjusted - actual) / actual * 100.0)
        baseline_apes.append(float(row["_baseline_ape"]))
    if not adjusted_apes:
        return None
    return {
        "feature": feature,
        "intercept": intercept,
        "slope": slope,
        "training_count": len(adjusted_apes),
        "training_baseline_mape": mean(baseline_apes),
        "training_adjusted_mape": mean(adjusted_apes),
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    actual_sum = sum(float(row["actual_annual_gva"]) for row in rows)
    baseline_abs_sum = sum(abs(float(row["baseline_error"])) for row in rows)
    adjusted_abs_sum = sum(abs(float(row["adjusted_error"])) for row in rows)
    baseline_mape = mean(float(row["baseline_absolute_percent_error"]) for row in rows)
    adjusted_mape = mean(float(row["adjusted_absolute_percent_error"]) for row in rows)
    return [
        {
            "comparison_count": len(rows),
            "target_year_start": min(row["target_year"] for row in rows),
            "target_year_end": max(row["target_year"] for row in rows),
            "baseline_mape": round(baseline_mape, 6),
            "adjusted_mape": round(adjusted_mape, 6),
            "mape_delta": round(adjusted_mape - baseline_mape, 6),
            "baseline_wmape": round(baseline_abs_sum / actual_sum * 100.0, 6) if actual_sum else "",
            "adjusted_wmape": round(adjusted_abs_sum / actual_sum * 100.0, 6) if actual_sum else "",
            "adopt_augmented_indicator": "yes" if adjusted_mape < baseline_mape else "no",
            "decision_rule": "adopt only if expanding-window adjusted MAPE is lower than baseline D00 rolling MAPE",
        }
    ]


def run_backtest() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    features = load_annual_features()
    candidates_to_test = feature_names(features)
    rows = load_d00_rows()
    out: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for row in sorted(rows, key=lambda item: (item["_year"], item.get("area_code", ""))):
        year = int(row["_year"])
        training = [item for item in rows if int(item["_year"]) < year]
        candidates = [
            result
            for feature in candidates_to_test
            if (result := evaluate_feature(training, features, feature)) is not None
        ]
        usable = [item for item in candidates if float(item["training_adjusted_mape"]) < float(item["training_baseline_mape"])]
        selected = min(usable, key=lambda item: float(item["training_adjusted_mape"]), default=None)
        correction = 1.0
        selected_feature = ""
        training_count = 0
        if selected:
            x = features.get(year, {}).get(str(selected["feature"]))
            if x is not None:
                correction = clamp(float(selected["intercept"]) + float(selected["slope"]) * x, 0.75, 1.25)
                selected_feature = str(selected["feature"])
                training_count = int(selected["training_count"])
        latest_period_feature = selected_feature.replace("_latest4q_level", "_latest_period_end").replace("_latest4q_yoy_pct", "_latest_period_end")
        latest_period = features.get(year, {}).get(latest_period_feature)
        adjusted = float(row["_predicted"]) * correction
        actual = float(row["_actual"])
        baseline_error = float(row["_predicted"]) - actual
        adjusted_error = adjusted - actual
        out.append(
            {
                "area_code": row.get("area_code", ""),
                "area_name": row.get("area_name", ""),
                "target_year": year,
                "baseline_predicted_annual_gva": round(float(row["_predicted"]), 6),
                "actual_annual_gva": round(actual, 6),
                "baseline_error": round(baseline_error, 6),
                "baseline_absolute_percent_error": round(float(row["_baseline_ape"]), 6),
                "selected_feature": selected_feature or "baseline",
                "feature_source_file": FEATURE_SOURCE_FILE if selected_feature else "",
                "forecast_as_of": f"{year:04d}-{FORECAST_ORIGIN_MONTH:02d}-{FORECAST_ORIGIN_DAY:02d}",
                "selected_feature_latest_period": latest_period if latest_period is not None and selected_feature else "",
                "release_filter": "feature quarters must be released before forecast_as_of",
                "training_count": training_count,
                "correction_factor": round(correction, 9),
                "adjusted_predicted_annual_gva": round(adjusted, 6),
                "adjusted_error": round(adjusted_error, 6),
                "adjusted_absolute_percent_error": round(abs(adjusted_error) / actual * 100.0, 6),
                "method": "expanding-window univariate exogenous correction for D00 only",
            }
        )
        for candidate in candidates:
            diagnostics.append(
                {
                    "target_year": year,
                    "area_code": row.get("area_code", ""),
                    "feature": candidate["feature"],
                    "training_count": candidate["training_count"],
                    "training_baseline_mape": round(float(candidate["training_baseline_mape"]), 6),
                    "training_adjusted_mape": round(float(candidate["training_adjusted_mape"]), 6),
                    "selected_for_target": "yes" if selected and candidate["feature"] == selected["feature"] else "no",
                    "forecast_as_of": f"{year:04d}-{FORECAST_ORIGIN_MONTH:02d}-{FORECAST_ORIGIN_DAY:02d}",
                    "release_filter": "lag-aware latest available 4-quarter feature",
                }
            )
    return out, diagnostics


def release_calendar_rows() -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for row in read_csv(PROCESSED_DIR / FEATURE_SOURCE_FILE):
        indicator = row.get("indicator", "")
        if not indicator or indicator in seen:
            continue
        rule = indicator_release_rule(indicator, row.get("source", ""))
        seen[indicator] = {
            "indicator": indicator,
            "source": row.get("source", ""),
            "frequency": rule.frequency,
            "publication_lag_months": rule.publication_lag_months,
            "forecast_origin": "target-year Jan 1",
            "application_rule": "Use latest four quarters whose period_end + lag is before forecast origin; compare with prior four available quarters for yoy features.",
            "note": rule.note,
        }
    return sorted(seen.values(), key=lambda row: row["indicator"])


def main() -> int:
    rows, diagnostics = run_backtest()
    write_csv(PROCESSED_DIR / "energy_augmented_backtest.csv", rows)
    write_csv(PROCESSED_DIR / "energy_augmented_feature_diagnostics.csv", diagnostics)
    write_csv(PROCESSED_DIR / "energy_augmented_summary.csv", summarize(rows))
    write_csv(PROCESSED_DIR / "energy_augmented_release_calendar.csv", release_calendar_rows())
    print(f"energy augmented rows: {len(rows)}")
    print(f"feature diagnostics: {len(diagnostics)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
