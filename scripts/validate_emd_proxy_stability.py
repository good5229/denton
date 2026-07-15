from __future__ import annotations

from collections import defaultdict
from typing import Any

from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


def summarize_comparison(rows: list[dict[str, str]], keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key, "") for key in keys)].append(row)
    out: list[dict[str, Any]] = []
    for key, items in sorted(groups.items()):
        abs_diffs = [parse_number(row.get("absolute_difference")) for row in items]
        abs_diffs = [value for value in abs_diffs if value is not None]
        pct_diffs = [parse_number(row.get("percent_difference_vs_old")) for row in items]
        pct_diffs = [abs(value) for value in pct_diffs if value is not None]
        old_sum = sum(parse_number(row.get("old_2015_proxy_annual_gva")) or 0.0 for row in items)
        new_sum = sum(parse_number(row.get("new_2024_proxy_annual_gva")) or 0.0 for row in items)
        out.append(
            {
                **{field: value for field, value in zip(keys, key)},
                "comparison_count": len(items),
                "old_proxy_sum": round(old_sum, 6),
                "new_proxy_sum": round(new_sum, 6),
                "absolute_difference_sum": round(sum(abs_diffs), 6),
                "mean_absolute_difference": round(sum(abs_diffs) / len(abs_diffs), 6) if abs_diffs else "",
                "mean_absolute_percent_difference_vs_old": round(sum(pct_diffs) / len(pct_diffs), 6) if pct_diffs else "",
            }
        )
    return out


def parent_constraint_summary() -> list[dict[str, Any]]:
    rows = read_csv(PROCESSED_DIR / "emd_constraint_diagnostics.csv")
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row.get("source_region", ""), row.get("sector_code", ""))].append(row)
    out: list[dict[str, Any]] = []
    for (source_region, sector_code), items in sorted(groups.items()):
        max_abs = max((parse_number(row.get("absolute_constraint_error")) or 0.0 for row in items), default=0.0)
        out.append(
            {
                "source_region": source_region,
                "sector_code": sector_code,
                "diagnostic_rows": len(items),
                "max_absolute_constraint_error": round(max_abs, 9),
                "constraint_ok": max_abs < 0.001,
            }
        )
    return out


def main() -> int:
    comparison = read_csv(PROCESSED_DIR / "seoul_emd_2015_vs_2024_proxy_comparison.csv")
    by_sector = summarize_comparison(comparison, ["sector_code"])
    by_sigungu_sector = summarize_comparison(comparison, ["sigungu_name", "sector_code"])
    constraints = parent_constraint_summary()
    write_csv(PROCESSED_DIR / "emd_proxy_stability_by_sector.csv", by_sector)
    write_csv(PROCESSED_DIR / "emd_proxy_stability_by_sigungu_sector.csv", by_sigungu_sector)
    write_csv(PROCESSED_DIR / "emd_parent_constraint_summary.csv", constraints)
    print(f"emd proxy sector rows: {len(by_sector)}")
    print(f"emd proxy sigungu-sector rows: {len(by_sigungu_sector)}")
    print(f"emd constraint rows: {len(constraints)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
