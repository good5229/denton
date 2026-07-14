from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, get_kosis_key, kosis_data, normalize_kosis_rows, write_csv, write_json


ORG_ID = "101"
TBL_ID = "DT_1KI1511_10"
YEAR = "2015"
INDUSTRIES = tuple("ABCDEFGHIJKLMNOPQRS")
ITEMS = {
    "T10": "establishments",
    "T20": "employees",
    "T30": "sales",
}


def collect() -> list[dict[str, Any]]:
    api_key = get_kosis_key()
    raw_dir = RAW_DIR / "emd_economic_census_2015"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for industry in INDUSTRIES:
        for item_id, metric in ITEMS.items():
            raw_path = raw_dir / f"{industry}_{item_id}.json"
            try:
                if raw_path.exists():
                    rows = json.loads(raw_path.read_text(encoding="utf-8"))
                else:
                    rows = kosis_data(
                        api_key=api_key,
                        org_id=ORG_ID,
                        tbl_id=TBL_ID,
                        item_id=item_id,
                        period="F",
                        start=YEAR,
                        end=YEAR,
                        obj={1: industry, 2: "ALL"},
                    )
                    write_json(raw_path, rows)
                    time.sleep(0.05)
                for row in normalize_kosis_rows(rows, "emd_economic_census_2015"):
                    row["metric"] = metric
                    out.append(row)
            except Exception as exc:
                failures.append({"industry": industry, "item_id": item_id, "metric": metric, "error": str(exc)})
                print(f"failed {industry} {item_id}: {exc}")
    write_csv(PROCESSED_DIR / "emd_economic_census_2015.csv", out)
    write_csv(PROCESSED_DIR / "emd_economic_census_failures.csv", failures)
    print(f"emd economic census rows: {len(out)}")
    print(f"failures: {len(failures)}")
    return out


def main() -> int:
    collect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
