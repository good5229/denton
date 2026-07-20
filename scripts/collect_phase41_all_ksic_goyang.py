from __future__ import annotations

from kosis_common import PROCESSED_DIR, RAW_DIR, get_kosis_key, kosis_data, normalize_kosis_rows, write_csv, write_json


TABLE = "DT_1KI1510_10"


def main() -> int:
    all_rows, raw = [], {}
    for item_id, metric in [("T10", "establishments"), ("T20", "employees"), ("T30", "sales")]:
        rows = kosis_data(
            api_key=get_kosis_key(), org_id="101", tbl_id=TABLE, item_id=item_id,
            period="F", start="2015", end="2015", obj={1: "ALL", 2: "31100"},
        )
        raw[item_id] = rows
        for row in normalize_kosis_rows(rows, "phase41_goyang_2015_all_ksic"):
            row["metric"] = metric
            all_rows.append(row)
    write_json(RAW_DIR / "phase41_goyang_2015_all_ksic.json", raw)
    write_csv(PROCESSED_DIR / "partial_stats_phase41_goyang_2015_all_ksic.csv", all_rows)
    print(f"rows={len(all_rows)} codes={len({r.get('c1_id') for r in all_rows})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
