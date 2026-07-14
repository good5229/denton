from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


SEOUL_CODE = "11"


def load_seoul_rows(filename: str) -> list[dict[str, str]]:
    rows = read_csv(PROCESSED_DIR / filename)
    return [row for row in rows if row.get("parent_area_code") == SEOUL_CODE]


def sum_by_emd_2023(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    names: dict[str, str] = {}
    sigungu_names: dict[str, str] = {}

    for row in rows:
        if row.get("year") != "2023":
            continue
        emd_code = row.get("emd_code", "")
        if not emd_code:
            continue
        value = parse_number(row.get("estimated_annual_gva")) or 0.0
        totals[emd_code] += value
        names[emd_code] = row.get("emd_name", "")
        sigungu_names[emd_code] = row.get("sigungu_name", "")

    out = [
        {
            "rank": rank,
            "sigungu_name": sigungu_names[emd_code],
            "emd_code": emd_code,
            "emd_name": names[emd_code],
            "estimated_annual_gva_2023": round(value, 6),
        }
        for rank, (emd_code, value) in enumerate(
            sorted(totals.items(), key=lambda item: item[1], reverse=True),
            start=1,
        )
    ]
    return out


def summarize_by_sigungu(
    annual_rows: list[dict[str, str]],
    diagnostic_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    annual_stats: dict[str, dict[str, Any]] = {}
    for row in annual_rows:
        code = row.get("sigungu_code", "")
        if not code:
            continue
        stat = annual_stats.setdefault(
            code,
            {
                "sigungu_code": code,
                "sigungu_name": row.get("sigungu_name", ""),
                "unique_emd": set(),
                "annual_rows": 0,
                "estimated_annual_gva_2023": 0.0,
                "max_absolute_constraint_error": 0.0,
            },
        )
        stat["unique_emd"].add(row.get("emd_code", ""))
        stat["annual_rows"] += 1
        if row.get("year") == "2023":
            stat["estimated_annual_gva_2023"] += (
                parse_number(row.get("estimated_annual_gva")) or 0.0
            )

    for row in diagnostic_rows:
        code = row.get("sigungu_code", "")
        if code not in annual_stats:
            continue
        error = parse_number(row.get("absolute_constraint_error")) or 0.0
        annual_stats[code]["max_absolute_constraint_error"] = max(
            annual_stats[code]["max_absolute_constraint_error"], error
        )

    out: list[dict[str, Any]] = []
    for stat in annual_stats.values():
        out.append(
            {
                "sigungu_code": stat["sigungu_code"],
                "sigungu_name": stat["sigungu_name"],
                "unique_emd": len({code for code in stat["unique_emd"] if code}),
                "annual_rows": stat["annual_rows"],
                "estimated_annual_gva_2023": round(stat["estimated_annual_gva_2023"], 6),
                "max_absolute_constraint_error": stat["max_absolute_constraint_error"],
            }
        )
    return sorted(out, key=lambda row: row["sigungu_code"])


def build_summary(
    quarterly_rows: list[dict[str, str]],
    annual_rows: list[dict[str, str]],
    diagnostic_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    max_error = max(
        (parse_number(row.get("absolute_constraint_error")) or 0.0 for row in diagnostic_rows),
        default=0.0,
    )
    years = sorted({row.get("year", "") for row in annual_rows if row.get("year")})
    periods = sorted(
        {
            f"{row.get('year')}Q{row.get('quarter')}"
            for row in quarterly_rows
            if row.get("year") and row.get("quarter")
        }
    )
    return [
        {
            "region_scope": "서울특별시 전체 읍면동",
            "unique_sigungu": len({row.get("sigungu_code") for row in annual_rows}),
            "unique_emd": len({row.get("emd_code") for row in annual_rows}),
            "annual_rows": len(annual_rows),
            "quarterly_rows": len(quarterly_rows),
            "diagnostic_rows": len(diagnostic_rows),
            "first_year": years[0] if years else "",
            "last_year": years[-1] if years else "",
            "first_period": periods[0] if periods else "",
            "last_period": periods[-1] if periods else "",
            "max_absolute_constraint_error": max_error,
        }
    ]


def main() -> None:
    quarterly_rows = load_seoul_rows("emd_quarterly_gva_estimates.csv")
    annual_rows = load_seoul_rows("emd_annual_gva_estimates.csv")
    diagnostic_rows = load_seoul_rows("emd_constraint_diagnostics.csv")

    outputs: list[tuple[Path, list[dict[str, Any]]]] = [
        (PROCESSED_DIR / "seoul_emd_quarterly_gva_estimates.csv", quarterly_rows),
        (PROCESSED_DIR / "seoul_emd_annual_gva_estimates.csv", annual_rows),
        (PROCESSED_DIR / "seoul_emd_constraint_diagnostics.csv", diagnostic_rows),
        (PROCESSED_DIR / "seoul_emd_summary.csv", build_summary(quarterly_rows, annual_rows, diagnostic_rows)),
        (PROCESSED_DIR / "seoul_emd_by_sigungu_summary.csv", summarize_by_sigungu(annual_rows, diagnostic_rows)),
        (PROCESSED_DIR / "seoul_emd_top_annual_2023.csv", sum_by_emd_2023(annual_rows)),
    ]
    for path, rows in outputs:
        write_csv(path, rows)

    summary = outputs[3][1][0]
    print(
        "Wrote Seoul EMD extracts: "
        f"{summary['unique_sigungu']} districts, {summary['unique_emd']} EMDs, "
        f"{summary['quarterly_rows']} quarterly rows."
    )


if __name__ == "__main__":
    main()
