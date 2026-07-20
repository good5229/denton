from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from kosis_common import get_kosis_key, kosis_data


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "phase37_goyang_emd" / "kosis_DT_1D00006_2021_2023.json"
OUT_PATH = ROOT / "data" / "processed" / "partial_stats_phase37_goyang_gu_industry_annual_actual.csv"
SECTOR_CODES = tuple("ABCDEFGHIJKLMNOPQRS")
SECTOR_NAMES = (
    "농림어업", "광업", "제조업", "전기·가스", "수도·폐기물", "건설업", "도소매", "운수·창고",
    "숙박·음식점", "정보통신", "금융·보험", "부동산", "전문·과학·기술", "사업시설·지원",
    "공공행정", "교육", "보건·사회복지", "예술·스포츠·여가", "협회·개인서비스",
)


def main() -> int:
    rows = kosis_data(
        api_key=get_kosis_key(), org_id="620", tbl_id="DT_1D00006", item_id="ALL",
        period="Y", start="2021", end="2023", obj={1: "ALL", 2: "ALL"},
    )
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    lookup: dict[str, tuple[str, str, str]] = {}
    for index, (code, name) in enumerate(zip(SECTOR_CODES, SECTOR_NAMES)):
        lookup[f"13103117062T{6 + index * 2}"] = (code, name, "establishments")
        lookup[f"13103117062T{7 + index * 2}"] = (code, name, "employees")
    records = []
    for row in rows:
        decoded = lookup.get(str(row.get("C2")))
        if not decoded:
            continue
        sector_code, sector_name, metric = decoded
        records.append(
            {
                "year": int(row["PRD_DE"]),
                "general_gu": row["C1_NM"],
                "sector_code": sector_code,
                "sector_name": sector_name,
                "metric": metric,
                "value": pd.to_numeric(row["DT"], errors="coerce"),
                "unit": row.get("UNIT_NM"),
                "org_id": row.get("ORG_ID"),
                "table_id": row.get("TBL_ID"),
            }
        )
    output = pd.DataFrame(records)
    full_index = pd.MultiIndex.from_product(
        [range(2021, 2024), ["합계", "덕양구", "일산동구", "일산서구"], SECTOR_CODES, ["establishments", "employees"]],
        names=["year", "general_gu", "sector_code", "metric"],
    )
    output = output.set_index(["year", "general_gu", "sector_code", "metric"]).reindex(full_index).reset_index()
    output["kosis_omitted_zero"] = output["value"].isna()
    output["value"] = output["value"].fillna(0)
    output["sector_name"] = output["sector_code"].map(dict(zip(SECTOR_CODES, SECTOR_NAMES)))
    output["unit"] = output["metric"].map({"establishments": "개", "employees": "명"})
    output["org_id"] = output["org_id"].fillna("620")
    output["table_id"] = output["table_id"].fillna("DT_1D00006")
    output = output.sort_values(["year", "general_gu", "sector_code", "metric"])
    output.to_csv(OUT_PATH, index=False)
    expected = 3 * 4 * 19 * 2
    if len(output) != expected:
        raise RuntimeError(f"unexpected decoded row count: {len(output)} != {expected}")
    print(f"annual actual rows: {len(output)}; years: {output.year.min()}-{output.year.max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
