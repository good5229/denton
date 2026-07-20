from __future__ import annotations

from kosis_common import PROCESSED_DIR, RAW_DIR, get_kosis_key, kosis_data, normalize_kosis_rows, write_csv, write_json


def main() -> int:
    rows = kosis_data(
        api_key=get_kosis_key(), org_id="101", tbl_id="DT_1F02011", item_id="T10",
        period="Q", start="202001", end="202412", obj={1: "ALL"},
    )
    write_json(RAW_DIR / "phase39_manufacturing_middle_production_index.json", rows)
    normalized = normalize_kosis_rows(rows, "phase39_manufacturing_middle_production_index")
    write_csv(PROCESSED_DIR / "partial_stats_phase39_manufacturing_middle_production_index.csv", normalized)
    print(f"rows={len(normalized)}")
    if normalized:
        print(f"columns={list(normalized[0])}")
        names = sorted({str(row.get('c1_nm') or row.get('c2_nm') or '') for row in normalized})
        print(f"series={len(names)} sample={names[:20]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
