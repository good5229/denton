from __future__ import annotations

import csv
import math
import ssl
import urllib.request
from collections import defaultdict
from datetime import date
from io import StringIO
from statistics import mean
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


FRED_SERIES = {
    "wti_oil_usd": "DCOILWTICO",
    "usd_krw": "DEXKOUS",
    "coal_australia_usd": "PCOALAUUSDM",
    "natural_gas_usd": "PNGASUSDM",
}


def quarter_key(text: str) -> str:
    y, m, _ = [int(part) for part in text.split("-")]
    return f"{y}Q{((m - 1) // 3) + 1}"


def fetch_fred(series_id: str) -> list[dict[str, str]]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    context = None
    try:
        import certifi  # type: ignore

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=60, context=context) as response:
        body = response.read().decode("utf-8-sig")
    return list(csv.DictReader(StringIO(body)))


def collect_external() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for name, series_id in FRED_SERIES.items():
        try:
            raw = fetch_fred(series_id)
        except Exception as exc:  # pragma: no cover - depends on network
            failures.append({"indicator": name, "series_id": series_id, "error": str(exc)})
            continue
        buckets: dict[str, list[float]] = defaultdict(list)
        for row in raw:
            value = parse_number(row.get(series_id))
            obs = row.get("observation_date", "")
            if value is None or not obs:
                continue
            period = quarter_key(obs)
            if "2015Q1" <= period <= "2025Q4":
                buckets[period].append(value)
        for period, values in sorted(buckets.items()):
            rows.append(
                {
                    "indicator": name,
                    "series_id": series_id,
                    "period": period,
                    "quarterly_average": round(mean(values), 6),
                    "observations": len(values),
                    "source": "FRED",
                }
            )
    write_csv(PROCESSED_DIR / "energy_exogenous_quarterly.csv", rows)
    write_csv(PROCESSED_DIR / "energy_exogenous_failures.csv", failures)
    return rows, failures


def period_sort(period: str) -> int:
    year = int(period[:4])
    quarter = int(period[-1])
    return year * 10 + quarter


def add_changes(series: dict[str, float]) -> dict[str, dict[str, float]]:
    periods = sorted(series, key=period_sort)
    out: dict[str, dict[str, float]] = {}
    for idx, period in enumerate(periods):
        value = series[period]
        item = {"level": value}
        if idx > 0 and series[periods[idx - 1]] != 0:
            item["qoq_pct"] = (value / series[periods[idx - 1]] - 1.0) * 100.0
        if idx > 3 and series[periods[idx - 4]] != 0:
            item["yoy_pct"] = (value / series[periods[idx - 4]] - 1.0) * 100.0
        out[period] = item
    return out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 6 or len(xs) != len(ys):
        return None
    mx, my = mean(xs), mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def target_series() -> dict[str, dict[str, float]]:
    targets: dict[str, dict[str, float]] = defaultdict(dict)
    for row in read_csv(PROCESSED_DIR / "rolling_electricity_gas_production_index.csv"):
        if row.get("c1_id") == "00":
            value = parse_number(row.get("value"))
            if value is not None:
                prd = row.get("prd_de", "")
                targets["electric_gas_production_index"][f"{prd[:4]}Q{int(prd[-2:])}"] = value
    for row in read_csv(PROCESSED_DIR / "all_industries_quarterly_gva_estimates.csv"):
        if row.get("area_code") == "00" and row.get("sector_code") == "D00":
            value = parse_number(row.get("estimated_gva"))
            if value is not None:
                targets["national_d00_estimated_gva"][row.get("period", "")] = value
            gdp = parse_number(row.get("national_gdp_benchmark"))
            if gdp is not None:
                targets["national_d00_gdp_benchmark"][row.get("period", "")] = gdp
    for row in read_csv(PROCESSED_DIR / "rolling_national_quarterly_gdp_deflator.csv"):
        if row.get("c1_id") == "13102134503ACC_ITEM.1104":
            value = parse_number(row.get("value"))
            if value is not None:
                prd = row.get("prd_de", "")
                targets["national_d00_gdp_deflator"][f"{prd[:4]}Q{int(prd[-2:])}"] = value
    return targets


def correlation_diagnostics(external_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    external: dict[str, dict[str, float]] = defaultdict(dict)
    for row in external_rows:
        value = parse_number(row.get("quarterly_average"))
        if value is not None:
            external[row["indicator"]][row["period"]] = value
    external_changes = {name: add_changes(values) for name, values in external.items()}
    targets = {name: add_changes(values) for name, values in target_series().items()}

    rows: list[dict[str, Any]] = []
    for indicator, indicator_values in external_changes.items():
        for target_name, target_values in targets.items():
            for transform in ("level", "qoq_pct", "yoy_pct"):
                periods = sorted(set(indicator_values) & set(target_values), key=period_sort)
                xs = [indicator_values[p][transform] for p in periods if transform in indicator_values[p] and transform in target_values[p]]
                ys = [target_values[p][transform] for p in periods if transform in indicator_values[p] and transform in target_values[p]]
                corr = pearson(xs, ys)
                if corr is None:
                    continue
                rows.append(
                    {
                        "indicator": indicator,
                        "target": target_name,
                        "transform": transform,
                        "observations": len(xs),
                        "pearson_corr": round(corr, 6),
                        "absolute_corr": round(abs(corr), 6),
                        "recommended_for_augmented_indicator": "yes" if abs(corr) >= 0.35 else "no",
                    }
                )
    rows.sort(key=lambda row: float(row["absolute_corr"]), reverse=True)
    write_csv(PROCESSED_DIR / "energy_exogenous_correlations.csv", rows)
    return rows


def main() -> int:
    external_rows, failures = collect_external()
    correlations = correlation_diagnostics(external_rows)
    print(f"energy exogenous rows: {len(external_rows)}")
    print(f"energy exogenous failures: {len(failures)}")
    print(f"energy correlation rows: {len(correlations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
