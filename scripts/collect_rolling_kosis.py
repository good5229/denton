from __future__ import annotations

import sys
from copy import deepcopy
from typing import Any

from collect_kosis import COLLECTIONS
from collect_expanded_kosis import get_data
from kosis_common import PROCESSED_DIR, RAW_DIR, get_kosis_key, normalize_kosis_rows, write_csv, write_json


START_YEAR = "2015"
END_YEAR_CANDIDATES = ["2025", "2024", "2023"]
END_QUARTER_CANDIDATES = [
    f"{year}{quarter:02d}"
    for year in range(2025, 2022, -1)
    for quarter in range(4, 0, -1)
]


def rolling_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for source in COLLECTIONS:
        spec = deepcopy(source)
        spec["name"] = f"rolling_{spec['name']}"
        if spec["period"] == "Y":
            spec["start"] = START_YEAR
            spec["end_candidates"] = END_YEAR_CANDIDATES
        elif spec["period"] == "Q":
            if spec["name"] == "rolling_construction_orders_by_region_type":
                spec["start"] = "201301"
            else:
                spec["start"] = f"{START_YEAR}01"
            spec["end_candidates"] = END_QUARTER_CANDIDATES
        specs.append(spec)
    return specs


def collect_with_fallback(api_key: str, spec: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    errors: list[str] = []
    for end in spec["end_candidates"]:
        try:
            rows = get_data(
                api_key=api_key,
                org_id=str(spec["org_id"]),
                tbl_id=str(spec["tbl_id"]),
                item_id=str(spec["item_id"]),
                period=str(spec["period"]),
                start=str(spec["start"]),
                end=str(end),
                obj=spec["obj"],
            )
        except Exception as exc:
            errors.append(f"{end}: {exc}")
            continue
        if rows:
            return rows, str(end)
    raise RuntimeError("; ".join(errors))


def main() -> int:
    api_key = get_kosis_key()
    all_rows: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for spec in rolling_specs():
        try:
            rows, selected_end = collect_with_fallback(api_key, spec)
        except Exception as exc:
            failures.append({"dataset": spec["name"], "error": str(exc)})
            print(f"ERROR while collecting {spec['name']}: {exc}", file=sys.stderr)
            continue
        write_json(RAW_DIR / f"{spec['name']}.json", rows)
        normalized = normalize_kosis_rows(rows, str(spec["name"]))
        write_csv(PROCESSED_DIR / f"{spec['name']}.csv", normalized)
        all_rows.extend(normalized)
        summary.append(
            {
                "dataset": spec["name"],
                "rows": len(rows),
                "start": spec["start"],
                "selected_end": selected_end,
                "period": spec["period"],
            }
        )
        print(f"{spec['name']}: {len(rows)} rows through {selected_end}")
    write_csv(PROCESSED_DIR / "rolling_kosis_collected_all.csv", all_rows)
    write_csv(PROCESSED_DIR / "rolling_kosis_collection_summary.csv", summary)
    write_csv(PROCESSED_DIR / "rolling_kosis_collection_failures.csv", failures)
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
