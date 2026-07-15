from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


CURRENT_BASE_SOURCES = [
    ("rolling_mining_manufacturing_production_index.csv", "production_index_2020_base"),
    ("rolling_mining_production_index.csv", "production_index_2020_base"),
    ("rolling_electricity_gas_production_index.csv", "production_index_2020_base"),
    ("rolling_service_production_index.csv", "service_index_2020_base"),
    ("expanded_national_service_ksic_production_index.csv", "service_detail_index_2020_base"),
]

LEGACY_CANDIDATES = [
    "legacy_2015_base_production_index.csv",
    "legacy_2015_base_service_index.csv",
    "production_index_2015_base.csv",
    "service_index_2015_base.csv",
]


def key_for(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row.get("tbl_id", ""),
        row.get("item_id", ""),
        row.get("c1_id", ""),
        row.get("c2_id", ""),
    )


def period(row: dict[str, str]) -> str:
    return row.get("prd_de", "")


def summarize_current_sources() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for filename, source_type in CURRENT_BASE_SOURCES:
        path = PROCESSED_DIR / filename
        if not path.exists():
            rows.append({"filename": filename, "status": "missing"})
            continue
        data = read_csv(path)
        periods = sorted({period(row) for row in data if period(row)})
        units = sorted({row.get("unit_nm", "") for row in data if row.get("unit_nm")})
        rows.append(
            {
                "filename": filename,
                "status": "available",
                "source_type": source_type,
                "rows": len(data),
                "period_start": periods[0] if periods else "",
                "period_end": periods[-1] if periods else "",
                "unit_names": "; ".join(units),
            }
        )
    return rows


def load_legacy_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for filename in LEGACY_CANDIDATES:
        path = PROCESSED_DIR / filename
        if not path.exists():
            continue
        for row in read_csv(path):
            rows.append({**row, "legacy_filename": filename})
    return rows


def current_rows_by_key() -> dict[tuple[str, str, str, str], dict[str, float]]:
    out: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(dict)
    for filename, _source_type in CURRENT_BASE_SOURCES:
        path = PROCESSED_DIR / filename
        if not path.exists():
            continue
        for row in read_csv(path):
            value = parse_number(row.get("value"))
            if value is None:
                continue
            out[key_for(row)][period(row)] = value
    return out


def build_bridge_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    legacy = load_legacy_rows()
    if not legacy:
        return [], [
            {
                "status": "no_legacy_2015_base_files",
                "note": "Current local KOSIS production/service index files already use 2020=100 and are backcast to 2015. Put a legacy 2015-base CSV under data/processed using the expected filenames to build bridge factors.",
            }
        ]

    current = current_rows_by_key()
    by_series: dict[tuple[str, str, str, str], dict[str, dict[str, object]]] = defaultdict(dict)
    for row in legacy:
        value = parse_number(row.get("value"))
        if value is None:
            continue
        by_series[key_for(row)][period(row)] = {"row": row, "legacy_value": value}

    bridge_rows: list[dict[str, object]] = []
    converted_rows: list[dict[str, object]] = []
    for key, legacy_periods in by_series.items():
        current_periods = current.get(key, {})
        overlaps = [
            (p, float(payload["legacy_value"]), current_periods[p])
            for p, payload in legacy_periods.items()
            if p in current_periods and float(payload["legacy_value"]) != 0
        ]
        if not overlaps:
            continue
        factors = [current_value / legacy_value for _p, legacy_value, current_value in overlaps]
        factor = mean(factors)
        bridge_rows.append(
            {
                "tbl_id": key[0],
                "item_id": key[1],
                "c1_id": key[2],
                "c2_id": key[3],
                "overlap_periods": len(overlaps),
                "bridge_factor_2020_over_2015": round(factor, 12),
                "overlap_start": min(p for p, _legacy, _current in overlaps),
                "overlap_end": max(p for p, _legacy, _current in overlaps),
            }
        )
        for p, payload in legacy_periods.items():
            row = payload["row"]
            converted_rows.append(
                {
                    **row,
                    "dataset": f"{row.get('dataset', 'legacy')}_converted_to_2020_base",
                    "prd_de": p,
                    "legacy_value": payload["legacy_value"],
                    "value": round(float(payload["legacy_value"]) * factor, 12),
                    "unit_nm": "2020=100 estimated from 2015-base bridge",
                    "bridge_factor_2020_over_2015": round(factor, 12),
                }
            )
    return converted_rows, bridge_rows


def main() -> int:
    source_summary = summarize_current_sources()
    converted, bridge = build_bridge_rows()
    write_csv(PROCESSED_DIR / "index_base_bridge_source_summary.csv", source_summary)
    write_csv(PROCESSED_DIR / "index_base_bridge_factors.csv", bridge)
    write_csv(PROCESSED_DIR / "index_base_bridge_converted_2020_base.csv", converted)
    print(f"current source rows: {len(source_summary)}")
    print(f"bridge factors: {len(bridge)}")
    print(f"converted rows: {len(converted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
