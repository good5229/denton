from __future__ import annotations

from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, get_kosis_key, kosis_data, normalize_kosis_rows, write_csv, write_json


ORG_ID = "101"
TBL_ID = "DT_1K52F08"
START_YEAR = "2020"
END_YEAR = "2024"
ITEMS = {
    "T1": "establishments",
    "T2": "employees",
    "T3": "sales",
}
SECTORS = {
    "A": "A00",
    "B": "B00",
    "D": "D00",
}


def collect() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    api_key = get_kosis_key()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    for item_id, metric in ITEMS.items():
        for kosis_sector, sector_code in SECTORS.items():
            try:
                data = kosis_data(
                    api_key=api_key,
                    org_id=ORG_ID,
                    tbl_id=TBL_ID,
                    item_id=item_id,
                    period="Y",
                    start=START_YEAR,
                    end=END_YEAR,
                    obj={1: "ALL", 2: kosis_sector},
                )
            except Exception as exc:
                failures.append({"item_id": item_id, "metric": metric, "sector": kosis_sector, "error": str(exc)})
                continue
            raw[f"{item_id}_{kosis_sector}"] = data
            for row in normalize_kosis_rows(data, "sector_structural_business_stats"):
                row["metric"] = metric
                row["sector_code"] = sector_code
                row["kosis_sector_code"] = kosis_sector
                rows.append(row)
    write_json(RAW_DIR / "sector_structural_business_stats.json", raw)
    write_csv(PROCESSED_DIR / "sector_structural_business_stats.csv", rows)
    write_csv(PROCESSED_DIR / "sector_structural_business_failures.csv", failures)
    write_csv(
        PROCESSED_DIR / "sector_structural_business_summary.csv",
        [
            {
                "source": f"KOSIS {ORG_ID} {TBL_ID}",
                "rows": len(rows),
                "failures": len(failures),
                "years": f"{START_YEAR}-{END_YEAR}",
                "sectors": ",".join(SECTORS.values()),
                "metrics": ",".join(ITEMS.values()),
                "publication_lag_policy": "annual structural business feature is eligible only after release; modeling uses target-year Jan 1 and max year <= target_year-2",
            }
        ],
    )
    return rows, failures


def main() -> int:
    rows, failures = collect()
    print(f"sector structural rows: {len(rows)}")
    print(f"failures: {len(failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
