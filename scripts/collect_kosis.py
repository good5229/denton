from __future__ import annotations

import sys
from pathlib import Path

from kosis_common import (
    PROCESSED_DIR,
    RAW_DIR,
    get_kosis_key,
    kosis_data,
    normalize_kosis_rows,
    save_metadata_csv,
    write_csv,
    write_json,
)


COLLECTIONS = [
    {
        "name": "annual_grva_real",
        "org_id": "101",
        "tbl_id": "DT_1C92",
        "item_id": "T11",
        "period": "Y",
        "start": "2019",
        "end": "2023",
        "obj": {1: "ALL", 2: "ALL"},
        "description": "시도별 경제활동별 지역내총부가가치(실질), 2020년 연쇄가격",
    },
    {
        "name": "mining_manufacturing_production_index",
        "org_id": "101",
        "tbl_id": "DT_1F02001",
        "item_id": "T10",
        "period": "Q",
        "start": "201901",
        "end": "202304",
        "obj": {1: "ALL", 2: "C"},
        "description": "시도/산업별 광공업생산지수(2020=100)",
    },
    {
        "name": "mining_production_index",
        "org_id": "101",
        "tbl_id": "DT_1F02001",
        "item_id": "T10",
        "period": "Q",
        "start": "201901",
        "end": "202304",
        "obj": {1: "ALL", 2: "B"},
        "description": "시도/산업별 광업 생산지수 원지수(2020=100)",
    },
    {
        "name": "electricity_gas_production_index",
        "org_id": "101",
        "tbl_id": "DT_1F02001",
        "item_id": "T10",
        "period": "Q",
        "start": "201901",
        "end": "202304",
        "obj": {1: "ALL", 2: "D"},
        "description": "시도/산업별 전기업 및 가스업 생산지수 원지수(2020=100)",
    },
    {
        "name": "service_production_index",
        "org_id": "101",
        "tbl_id": "DT_1KC2023",
        "item_id": "T2",
        "period": "Q",
        "start": "201901",
        "end": "202304",
        "obj": {1: "ALL", 2: "ALL"},
        "description": "시도별 업종별 서비스업생산지수(2020=100.0)",
    },
    {
        "name": "construction_orders_by_region_type",
        "org_id": "101",
        "tbl_id": "DT_1G1B035",
        "item_id": "T1",
        "period": "Q",
        "start": "201301",
        "end": "202304",
        "obj": {1: "ALL", 2: "ALL"},
        "description": "공사지역/공종별 건설수주액(경상)",
    },
    {
        "name": "national_quarterly_gdp_real",
        "org_id": "301",
        "tbl_id": "DT_200Y106",
        "item_id": "13103136275999",
        "period": "Q",
        "start": "201901",
        "end": "202304",
        "obj": {1: "ALL"},
        "description": "경제활동별 GDP 및 GNI(원계열, 실질, 분기)",
    },
    {
        "name": "national_quarterly_gdp_deflator",
        "org_id": "301",
        "tbl_id": "DT_200Y011",
        "item_id": "13103134503999",
        "period": "Q",
        "start": "201901",
        "end": "202304",
        "obj": {1: "ALL"},
        "description": "경제활동별 국내총생산 디플레이터(분기)",
    },
]


def collect_one(api_key: str, spec: dict[str, object]) -> list[dict[str, object]]:
    rows = kosis_data(
        api_key=api_key,
        org_id=str(spec["org_id"]),
        tbl_id=str(spec["tbl_id"]),
        item_id=str(spec["item_id"]),
        period=str(spec["period"]),
        start=str(spec["start"]),
        end=str(spec["end"]),
        obj=spec["obj"],  # type: ignore[arg-type]
    )
    raw_path = RAW_DIR / f"{spec['name']}.json"
    processed_path = PROCESSED_DIR / f"{spec['name']}.csv"
    write_json(raw_path, rows)
    normalized = normalize_kosis_rows(rows, str(spec["name"]))
    write_csv(processed_path, normalized)
    print(f"{spec['name']}: {len(rows)} rows")
    return normalized


def main() -> int:
    api_key = get_kosis_key()
    for table_id in ("DT_1C92", "DT_1F02001", "DT_1KC2023", "DT_1G1B035", "DT_200Y106", "DT_200Y011"):
        html_path = RAW_DIR / f"kosis_{table_id}_statHtmlContent.html"
        if html_path.exists():
            save_metadata_csv(table_id)
    all_rows: list[dict[str, object]] = []
    for spec in COLLECTIONS:
        try:
            all_rows.extend(collect_one(api_key, spec))
        except Exception as exc:
            print(f"ERROR while collecting {spec['name']}: {exc}", file=sys.stderr)
            raise
    write_csv(PROCESSED_DIR / "kosis_collected_all.csv", all_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
