from __future__ import annotations

import json
import math
import ssl
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, load_env, parse_number, read_csv, write_csv, write_json


BASE_URL = "https://ecos.bok.or.kr/api"
RAW_ECOS_DIR = RAW_DIR / "ecos"
START_Q = "2015Q1"
END_Q = "2026Q2"
GDP_END_Q = "2026Q1"
START_A = "2015"
END_A = "2024"
IO_YEAR = "2019"


NATIONAL_ACCOUNT_SPECS = [
    {
        "dataset": "ecos_gdp_gni_nominal_sa",
        "stat_code": "200Y103",
        "cycle": "Q",
        "start": START_Q,
        "end": GDP_END_Q,
        "role": "national_quarterly_nominal_sa",
    },
    {
        "dataset": "ecos_gdp_gni_real_original",
        "stat_code": "200Y106",
        "cycle": "Q",
        "start": START_Q,
        "end": GDP_END_Q,
        "role": "national_quarterly_real_original",
    },
    {
        "dataset": "ecos_gdp_deflator",
        "stat_code": "200Y111",
        "cycle": "Q",
        "start": START_Q,
        "end": GDP_END_Q,
        "role": "national_quarterly_deflator",
    },
    {
        "dataset": "ecos_annual_nominal_gva",
        "stat_code": "200Y114",
        "cycle": "A",
        "start": START_A,
        "end": END_A,
        "items": ["3"],
        "role": "national_annual_nominal_gva",
    },
]

IO_SPECS = [
    {"dataset": "ecos_io_production_inducement_middle", "stat_code": "271Y070"},
    {"dataset": "ecos_io_value_added_inducement_middle", "stat_code": "271Y072"},
]

ECOS_EXOGENOUS_SPECS = [
    {
        "indicator": "ecos_usd_krw_avg",
        "stat_code": "731Y004",
        "items": ["0000001"],
        "keep_item2": "0000100",
        "description": "원/미국달러 매매기준율 평균",
    },
    {"indicator": "ecos_import_price_total", "stat_code": "401Y015", "items": ["*AA"], "description": "수입물가지수 총지수"},
    {"indicator": "ecos_import_price_bituminous_coal", "stat_code": "401Y015", "items": ["201112AA"], "description": "수입물가지수 유연탄"},
    {"indicator": "ecos_import_price_crude_oil", "stat_code": "401Y015", "items": ["201121AA"], "description": "수입물가지수 원유"},
    {"indicator": "ecos_import_price_lng", "stat_code": "401Y015", "items": ["201122AA"], "description": "수입물가지수 천연가스(LNG)"},
    {"indicator": "ecos_import_price_oil_gas", "stat_code": "401Y015", "items": ["20112AA"], "description": "수입물가지수 원유및천연가스"},
    {"indicator": "ecos_import_price_lpg", "stat_code": "401Y015", "items": ["304127AA"], "description": "수입물가지수 액화석유가스"},
    {"indicator": "ecos_ppi_total", "stat_code": "404Y014", "items": ["*AA"], "description": "생산자물가지수 총지수"},
    {"indicator": "ecos_ppi_coal", "stat_code": "404Y014", "items": ["20111AA"], "description": "생산자물가지수 석탄"},
    {"indicator": "ecos_ppi_oil_gas", "stat_code": "404Y014", "items": ["2011AA"], "description": "생산자물가지수 석탄,원유및천연가스"},
    {"indicator": "ecos_ppi_power", "stat_code": "404Y014", "items": ["401111AA"], "description": "생산자물가지수 전력"},
    {"indicator": "ecos_ppi_city_gas", "stat_code": "404Y014", "items": ["40121AA"], "description": "생산자물가지수 도시가스"},
    {"indicator": "ecos_ppi_power_gas_steam", "stat_code": "404Y014", "items": ["401AA"], "description": "생산자물가지수 전력,가스및증기"},
]


def get_ecos_key() -> str:
    env = load_env()
    for name in ("ECOS_API_KEY", "BOK_ECOS_API_KEY", "BOK_API_KEY"):
        value = env.get(name)
        if value:
            return value
    raise SystemExit("ECOS API key not found. Add ECOS_API_KEY=... to .env and rerun.")


def ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def ecos_request(service: str, api_key: str, start_no: int, end_no: int, *args: str) -> dict[str, Any]:
    parts = [service, api_key, "json", "kr", str(start_no), str(end_no), *args]
    url = f"{BASE_URL}/{'/'.join(urllib.parse.quote(part, safe='') for part in parts)}"
    with urllib.request.urlopen(url, timeout=30, context=ssl_context()) as response:
        body = response.read().decode("utf-8-sig")
    data = json.loads(body)
    if isinstance(data, dict) and "RESULT" in data:
        result = data.get("RESULT", {})
        code = result.get("CODE")
        if code and code != "INFO-000":
            raise RuntimeError(f"ECOS {service} error {code}: {result.get('MESSAGE')}")
    return data


def response_rows(data: dict[str, Any], service: str) -> list[dict[str, Any]]:
    node = data.get(service)
    if not isinstance(node, dict):
        return []
    rows = node.get("row", [])
    if isinstance(rows, dict):
        return [rows]
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def search(api_key: str, stat_code: str, cycle: str, start: str, end: str, *items: str, limit: int = 10000) -> list[dict[str, Any]]:
    data = ecos_request("StatisticSearch", api_key, 1, limit, stat_code, cycle, start, end, *items)
    return response_rows(data, "StatisticSearch")


def read_item_metadata(stat_code: str) -> list[dict[str, Any]]:
    path = RAW_ECOS_DIR / "items" / f"{stat_code}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return response_rows(data, "StatisticItemList")


def group_items(stat_code: str, group_code: str, cycle: str = "A") -> list[dict[str, Any]]:
    rows = [
        row
        for row in read_item_metadata(stat_code)
        if row.get("GRP_CODE") == group_code and row.get("CYCLE") == cycle
    ]
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("ITEM_CODE") or "")
        if code and code not in seen:
            seen[code] = row
    return list(seen.values())


def normalize_rows(dataset: str, role: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "dataset": dataset,
                "role": role,
                "stat_code": row.get("STAT_CODE"),
                "stat_name": row.get("STAT_NAME"),
                "period": row.get("TIME"),
                "item_code1": row.get("ITEM_CODE1"),
                "item_name1": row.get("ITEM_NAME1"),
                "item_code2": row.get("ITEM_CODE2"),
                "item_name2": row.get("ITEM_NAME2"),
                "unit_name": row.get("UNIT_NAME"),
                "value": row.get("DATA_VALUE"),
                "source": "ECOS",
            }
        )
    return out


def collect_national_accounts(api_key: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    for spec in NATIONAL_ACCOUNT_SPECS:
        rows = search(
            api_key,
            spec["stat_code"],
            spec["cycle"],
            spec["start"],
            spec["end"],
            *spec.get("items", []),
        )
        raw[spec["dataset"]] = rows
        out.extend(normalize_rows(spec["dataset"], spec["role"], rows))
        print(f"{spec['dataset']}: {len(rows)} rows")
    write_json(RAW_ECOS_DIR / "ecos_national_accounts.json", raw)
    write_csv(PROCESSED_DIR / "ecos_national_accounts.csv", out)
    return out


def collect_io(api_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    for spec in IO_SPECS:
        stat_code = spec["stat_code"]
        demand_items = group_items(stat_code, "Group1", "A")
        stat_rows: list[dict[str, Any]] = []
        for item in demand_items:
            code = str(item.get("ITEM_CODE"))
            rows = search(api_key, stat_code, "A", IO_YEAR, IO_YEAR, code, limit=1000)
            stat_rows.extend(rows)
        raw[stat_code] = stat_rows
        all_rows.extend(normalize_rows(spec["dataset"], "io_middle_matrix", stat_rows))
        print(f"{spec['dataset']}: {len(stat_rows)} rows")
    write_json(RAW_ECOS_DIR / "ecos_io_middle_matrix.json", raw)
    write_csv(PROCESSED_DIR / "ecos_io_middle_matrix.csv", all_rows)
    prior = build_io_prior(all_rows)
    write_csv(PROCESSED_DIR / "ecos_io_middle_industry_prior.csv", prior)
    return all_rows, prior


def build_io_prior(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        demand = str(row.get("item_code1") or "")
        input_code = str(row.get("item_code2") or "")
        if not demand or not input_code:
            continue
        if input_code in {"9590", "9801"}:
            continue
        key = (str(row.get("period") or IO_YEAR), demand, input_code)
        record = by_key.setdefault(
            key,
            {
                "year": row.get("period") or IO_YEAR,
                "demand_code": demand,
                "demand_name": row.get("item_name1"),
                "input_code": input_code,
                "input_name": row.get("item_name2"),
            },
        )
        value = parse_number(row.get("value"))
        if row.get("dataset") == "ecos_io_production_inducement_middle":
            record["production_inducement"] = value
        elif row.get("dataset") == "ecos_io_value_added_inducement_middle":
            record["value_added_inducement"] = value

    totals: dict[str, dict[str, float]] = defaultdict(lambda: {"production": 0.0, "value_added": 0.0})
    for (_, demand, _), row in by_key.items():
        prod = row.get("production_inducement")
        va = row.get("value_added_inducement")
        if isinstance(prod, (int, float)) and prod > 0:
            totals[demand]["production"] += float(prod)
        if isinstance(va, (int, float)) and va > 0:
            totals[demand]["value_added"] += float(va)

    out: list[dict[str, Any]] = []
    for (_, demand, _), row in sorted(by_key.items()):
        prod = row.get("production_inducement")
        va = row.get("value_added_inducement")
        prod_total = totals[demand]["production"]
        va_total = totals[demand]["value_added"]
        out.append(
            {
                **row,
                "production_inducement": round(float(prod), 9) if isinstance(prod, (int, float)) else "",
                "value_added_inducement": round(float(va), 9) if isinstance(va, (int, float)) else "",
                "production_share_within_demand": round(float(prod) / prod_total, 9)
                if isinstance(prod, (int, float)) and prod_total
                else "",
                "value_added_share_within_demand": round(float(va) / va_total, 9)
                if isinstance(va, (int, float)) and va_total
                else "",
                "source": "ECOS",
                "interpretation": "national_input_output_prior_not_regional_actual",
            }
        )
    return out


def collect_exogenous(api_key: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    for spec in ECOS_EXOGENOUS_SPECS:
        rows = search(api_key, spec["stat_code"], "Q", START_Q, END_Q, *spec["items"], limit=2000)
        keep_item2 = spec.get("keep_item2")
        if keep_item2:
            rows = [row for row in rows if row.get("ITEM_CODE2") == keep_item2]
        raw[spec["indicator"]] = rows
        for row in rows:
            out.append(
                {
                    "indicator": spec["indicator"],
                    "description": spec["description"],
                    "stat_code": row.get("STAT_CODE"),
                    "stat_name": row.get("STAT_NAME"),
                    "period": row.get("TIME"),
                    "item_code1": row.get("ITEM_CODE1"),
                    "item_name1": row.get("ITEM_NAME1"),
                    "item_code2": row.get("ITEM_CODE2"),
                    "item_name2": row.get("ITEM_NAME2"),
                    "unit_name": row.get("UNIT_NAME"),
                    "quarterly_value": row.get("DATA_VALUE"),
                    "source": "ECOS",
                }
            )
        print(f"{spec['indicator']}: {len(rows)} rows")
    write_json(RAW_ECOS_DIR / "ecos_energy_price_fx_quarterly.json", raw)
    write_csv(PROCESSED_DIR / "ecos_energy_price_fx_quarterly.csv", out)
    merged = merge_energy_exogenous(out)
    write_csv(PROCESSED_DIR / "energy_exogenous_with_ecos_quarterly.csv", merged)
    return out


def merge_energy_exogenous(ecos_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "energy_exogenous_quarterly.csv"):
        rows.append(row)
    for row in ecos_rows:
        rows.append(
            {
                "indicator": row.get("indicator"),
                "series_id": row.get("stat_code"),
                "period": row.get("period"),
                "quarterly_average": row.get("quarterly_value"),
                "observations": "",
                "source": "ECOS",
                "description": row.get("description"),
                "item_code1": row.get("item_code1"),
                "item_name1": row.get("item_name1"),
                "item_code2": row.get("item_code2"),
                "item_name2": row.get("item_name2"),
            }
        )
    return rows


def period_from_kosis(prd_de: str) -> str:
    if len(prd_de) == 6:
        return f"{prd_de[:4]}Q{int(prd_de[-2:])}"
    return prd_de


def ecos_item_suffix(code: str) -> str:
    return code.split(".")[-1]


def build_crosscheck(ecos_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kosis_sources = {
        "ecos_gdp_gni_real_original": "rolling_national_quarterly_gdp_real.csv",
        "ecos_gdp_deflator": "rolling_national_quarterly_gdp_deflator.csv",
    }
    kosis: dict[tuple[str, str, str], dict[str, Any]] = {}
    for dataset, filename in kosis_sources.items():
        for row in read_csv(PROCESSED_DIR / filename):
            code = ecos_item_suffix(str(row.get("c1_id") or ""))
            period = period_from_kosis(str(row.get("prd_de") or ""))
            kosis[(dataset, period, code)] = row

    out: list[dict[str, Any]] = []
    for row in ecos_rows:
        dataset = str(row.get("dataset") or "")
        if dataset not in kosis_sources:
            continue
        period = str(row.get("period") or "")
        code = str(row.get("item_code1") or "")
        other = kosis.get((dataset, period, code))
        if not other:
            continue
        ev = parse_number(row.get("value"))
        kv = parse_number(other.get("value"))
        if ev is None or kv is None:
            continue
        diff = ev - kv
        pct = diff / kv * 100.0 if kv else None
        out.append(
            {
                "dataset": dataset,
                "period": period,
                "item_code": code,
                "item_name_ecos": row.get("item_name1"),
                "item_name_kosis": other.get("c1_nm"),
                "ecos_unit": row.get("unit_name"),
                "kosis_unit": other.get("unit_nm"),
                "ecos_value": ev,
                "kosis_value": kv,
                "abs_diff": round(abs(diff), 9),
                "pct_diff": round(pct, 9) if pct is not None and math.isfinite(pct) else "",
                "match_within_1e_6": "yes" if abs(diff) <= 1e-6 else "no",
                "comparison_status": comparison_status(dataset, row.get("unit_name"), other.get("unit_nm"), diff),
            }
        )
    write_csv(PROCESSED_DIR / "ecos_kosis_gdp_crosscheck.csv", out)
    return out


def comparison_status(dataset: str, ecos_unit: Any, kosis_unit: Any, diff: float) -> str:
    if abs(diff) <= 1e-6:
        return "same_value"
    if dataset == "ecos_gdp_deflator" and str(ecos_unit) != str(kosis_unit):
        return "different_index_base_or_table_version"
    return "value_differs"


def summarize(national: list[dict[str, Any]], io_rows: list[dict[str, Any]], prior: list[dict[str, Any]], exog: list[dict[str, Any]], crosscheck: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mismatches = [row for row in crosscheck if row.get("match_within_1e_6") != "yes"]
    value_differs = [row for row in crosscheck if row.get("comparison_status") == "value_differs"]
    base_differs = [row for row in crosscheck if row.get("comparison_status") == "different_index_base_or_table_version"]
    return [
        {"metric": "ecos_national_accounts_rows", "value": len(national), "note": "GDP/GVA/deflator collected from ECOS"},
        {"metric": "ecos_io_middle_matrix_rows", "value": len(io_rows), "note": f"{IO_YEAR} input-output middle-class matrix rows"},
        {"metric": "ecos_io_middle_prior_rows", "value": len(prior), "note": "merged production/value-added prior rows"},
        {"metric": "ecos_energy_price_fx_rows", "value": len(exog), "note": "quarterly energy/price/fx rows"},
        {"metric": "ecos_kosis_crosscheck_rows", "value": len(crosscheck), "note": "overlapping ECOS-KOSIS GDP/deflator comparisons"},
        {"metric": "ecos_kosis_crosscheck_mismatches", "value": len(mismatches), "note": "absolute difference > 1e-6"},
        {"metric": "ecos_kosis_value_differs", "value": len(value_differs), "note": "differences not explained by index-base/table-version labels"},
        {"metric": "ecos_kosis_deflator_base_or_version_differs", "value": len(base_differs), "note": "deflator differs because local KOSIS file and ECOS use different index bases/table versions"},
    ]


def main() -> int:
    api_key = get_ecos_key()
    RAW_ECOS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    national = collect_national_accounts(api_key)
    io_rows, prior = collect_io(api_key)
    exog = collect_exogenous(api_key)
    crosscheck = build_crosscheck(national)
    summary = summarize(national, io_rows, prior, exog, crosscheck)
    write_csv(PROCESSED_DIR / "ecos_augmented_data_summary.csv", summary)
    for row in summary:
        print(f"{row['metric']}: {row['value']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ECOS augmented collection failed: {exc}", file=sys.stderr)
        raise
