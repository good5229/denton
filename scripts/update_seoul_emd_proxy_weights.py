from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, parse_number, read_csv, write_csv


SEOUL_API = "https://stat.eseoul.go.kr/stat/sip/sts/map/getChartDataList.do"
YEAR = "2024"
SEOUL_CODE = "11"


def normalize_name(name: str) -> str:
    return (
        str(name)
        .replace("·", ".")
        .replace("ㆍ", ".")
        .replace(" ", "")
        .strip()
    )


def fetch_seoul_business_json() -> dict[str, Any]:
    raw_dir = RAW_DIR / "seoul_business_map"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"seoul_business_map_{YEAR}.json"
    if raw_path.exists():
        return json.loads(raw_path.read_text(encoding="utf-8"))
    completed = subprocess.run(
        [
            "curl",
            "-L",
            "-sS",
            "-X",
            "POST",
            SEOUL_API,
            "-H",
            "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",
            "--data",
            f"statsMapId=1&curOrgId=201&prdDe={YEAR}&searchPrdDe={YEAR}",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(completed.stdout)
    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def metric_name(chart_name: str, item_name: str) -> str | None:
    text = f"{chart_name} {item_name}"
    if "총종사자" in text or "종사자수" in text or "종사자 수" in text:
        return "employees"
    if "사업체수" in text or "사업체 수" in text:
        return "establishments"
    return None


def extract_latest_proxy_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chart in data.get("mapChartList", []):
        chart_name = chart.get("mapChartNm", "")
        chart_data = chart.get("mapChartData", {})
        choices = chart_data.get("chcList", [])
        data_rows = chart_data.get("dataList", [])
        for choice in choices:
            item_id = choice.get("cndtnItmId")
            item_name = choice.get("cndtnNm", "")
            metric = metric_name(chart_name, item_name)
            if not item_id or not metric:
                continue
            value_key = f"{YEAR}:{item_id}"
            prev_key = f"2023:{item_id}"
            for row in data_rows:
                code = str(row.get("code", ""))
                value = parse_number(row.get(value_key))
                if value is None or value < 0:
                    continue
                level = "sigungu" if len(code) == 5 else "emd" if len(code) >= 8 else "unknown"
                if level == "unknown":
                    continue
                rows.append(
                    {
                        "source": "서울시 한눈에 보는 사업체",
                        "year": YEAR,
                        "metric": metric,
                        "chart_id": chart.get("mapChartId", ""),
                        "chart_name": chart_name,
                        "item_id": item_id,
                        "item_name": item_name,
                        "sigungu_code": code[:5],
                        "emd_code_2024": code if level == "emd" else "",
                        "area_code": code,
                        "area_name": row.get("category", ""),
                        "admin_level": level,
                        "proxy_value": value,
                        "previous_year_value": row.get(prev_key, ""),
                    }
                )
    # The API exposes several overlapping charts. Keep one value per
    # metric/admin code, preferring the most general chart with many rows.
    best: dict[tuple[str, str], dict[str, Any]] = {}
    rank = {"employees": 0, "establishments": 1}
    for row in rows:
        key = (row["metric"], row["area_code"])
        current = best.get(key)
        if current is None or rank[row["metric"]] <= rank[current["metric"]]:
            best[key] = row
    return sorted(best.values(), key=lambda row: (row["metric"], row["area_code"]))


def build_latest_weights(proxy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in proxy_rows:
        if row.get("admin_level") != "emd":
            continue
        groups[(row["metric"], row["sigungu_code"])].append(row)

    selected: dict[str, list[dict[str, Any]]] = {}
    for metric in ("employees", "establishments"):
        for (_, sigungu_code), rows in groups.items():
            if rows and rows[0]["metric"] == metric and sigungu_code not in selected:
                total = sum(float(row["proxy_value"]) for row in rows)
                if total > 0:
                    selected[sigungu_code] = rows

    weights: list[dict[str, Any]] = []
    for sigungu_code, rows in selected.items():
        total = sum(float(row["proxy_value"]) for row in rows)
        for row in rows:
            weights.append(
                {
                    "sigungu_code": sigungu_code,
                    "emd_code_2024": row["emd_code_2024"],
                    "emd_name": row["area_name"],
                    "proxy_metric": row["metric"],
                    "proxy_year": YEAR,
                    "proxy_value": row["proxy_value"],
                    "latest_share": round(float(row["proxy_value"]) / total, 12),
                }
            )
    return weights


def allocate_seoul_with_latest_weights(
    weights: list[dict[str, Any]],
    proxy_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_sigungu: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in weights:
        by_sigungu[row["sigungu_code"]].append(row)

    official_by_name = {}
    for row in proxy_rows:
        if row.get("admin_level") == "sigungu":
            official_by_name[row.get("area_name", "")] = row.get("area_code", "")

    out: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in read_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv"):
        if row.get("parent_area_code") != SEOUL_CODE:
            continue
        if row.get("sigungu_name") in {"서울시", "서울특별시"}:
            continue
        dashboard_sigungu_code = row.get("sigungu_code", "")
        official_sigungu_code = official_by_name.get(row.get("sigungu_name", ""), dashboard_sigungu_code)
        weight_rows = by_sigungu.get(official_sigungu_code)
        if not weight_rows:
            skipped.append(
                {
                    "sigungu_code": dashboard_sigungu_code,
                    "official_sigungu_code": official_sigungu_code,
                    "sigungu_name": row.get("sigungu_name", ""),
                    "sector_code": row.get("sector_code", ""),
                    "period": row.get("period", ""),
                    "reason": "missing 2024 Seoul proxy weights",
                }
            )
            continue
        parent_value = parse_number(row.get("estimated_gva"))
        if parent_value is None:
            continue
        for weight in weight_rows:
            share = float(weight["latest_share"])
            out.append(
                {
                    "source_region": "서울특별시",
                    "parent_area_code": SEOUL_CODE,
                    "sigungu_code": dashboard_sigungu_code,
                    "official_sigungu_code": official_sigungu_code,
                    "sigungu_name": row.get("sigungu_name", ""),
                    "emd_code_2024": weight["emd_code_2024"],
                    "emd_name": weight["emd_name"],
                    "sector_code": row.get("sector_code", ""),
                    "sector_name": row.get("sector_name", ""),
                    "year": row.get("year", ""),
                    "quarter": row.get("quarter", ""),
                    "period": row.get("period", ""),
                    "estimated_gva": round(parent_value * share, 6),
                    "parent_sigungu_quarterly_gva": round(parent_value, 6),
                    "allocation_share": share,
                    "proxy_metric": weight["proxy_metric"],
                    "proxy_year": YEAR,
                    "method": "2024 Seoul business map proxy share within sigungu quarterly GVA",
                }
            )
    return out, skipped


def compare_2023_totals(latest_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    old_totals: dict[tuple[str, str, str], float] = defaultdict(float)
    old_names: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_csv(PROCESSED_DIR / "seoul_emd_annual_gva_estimates.csv"):
        if row.get("year") != "2023":
            continue
        key = (row.get("sigungu_name", ""), normalize_name(row.get("emd_name", "")), row.get("sector_code", ""))
        old_totals[key] += parse_number(row.get("estimated_annual_gva")) or 0.0
        old_names[(row.get("sigungu_name", ""), normalize_name(row.get("emd_name", "")))] = {
            "emd_code": row.get("emd_code", ""),
            "emd_name": row.get("emd_name", ""),
            "sigungu_code": row.get("sigungu_code", ""),
        }

    latest_totals: dict[tuple[str, str, str], float] = defaultdict(float)
    latest_codes: dict[tuple[str, str], dict[str, str]] = {}
    for row in latest_rows:
        if row.get("year") != "2023":
            continue
        key = (row.get("sigungu_name", ""), normalize_name(row.get("emd_name", "")), row.get("sector_code", ""))
        latest_totals[key] += float(row.get("estimated_gva", 0.0))
        latest_codes[(row.get("sigungu_name", ""), normalize_name(row.get("emd_name", "")))] = {
            "emd_code": row.get("emd_code_2024", ""),
            "emd_name": row.get("emd_name", ""),
            "sigungu_code": row.get("official_sigungu_code", ""),
        }

    comparison: list[dict[str, Any]] = []
    for key in sorted(set(old_totals) | set(latest_totals)):
        sigungu_name, emd_name_key, sector = key
        old_info = old_names.get((sigungu_name, emd_name_key), {})
        new_info = latest_codes.get((sigungu_name, emd_name_key), {})
        old = old_totals.get(key, 0.0)
        new = latest_totals.get(key, 0.0)
        diff = new - old
        comparison.append(
            {
                "sigungu_name": sigungu_name,
                "sigungu_code_2015": old_info.get("sigungu_code", ""),
                "sigungu_code_2024": new_info.get("sigungu_code", ""),
                "emd_name": old_info.get("emd_name") or new_info.get("emd_name") or emd_name_key,
                "old_emd_code_2015": old_info.get("emd_code", ""),
                "new_emd_code_2024": new_info.get("emd_code", ""),
                "sector_code": sector,
                "old_2015_proxy_annual_gva": round(old, 6),
                "new_2024_proxy_annual_gva": round(new, 6),
                "difference": round(diff, 6),
                "absolute_difference": round(abs(diff), 6),
                "percent_difference_vs_old": round(diff / old * 100.0, 6) if old else "",
            }
        )

    by_emd: dict[tuple[str, str], dict[str, Any]] = {}
    for row in comparison:
        key = (row["sigungu_name"], normalize_name(row["emd_name"]))
        item = by_emd.setdefault(
            key,
            {
                "sigungu_name": row["sigungu_name"],
                "emd_name": row["emd_name"],
                "old_emd_code_2015": row["old_emd_code_2015"],
                "new_emd_code_2024": row["new_emd_code_2024"],
                "old_2015_proxy_annual_gva": 0.0,
                "new_2024_proxy_annual_gva": 0.0,
                "absolute_difference": 0.0,
            },
        )
        item["old_2015_proxy_annual_gva"] += float(row["old_2015_proxy_annual_gva"])
        item["new_2024_proxy_annual_gva"] += float(row["new_2024_proxy_annual_gva"])
    summary = []
    for row in by_emd.values():
        diff = row["new_2024_proxy_annual_gva"] - row["old_2015_proxy_annual_gva"]
        old = row["old_2015_proxy_annual_gva"]
        summary.append(
            {
                **row,
                "old_2015_proxy_annual_gva": round(old, 6),
                "new_2024_proxy_annual_gva": round(row["new_2024_proxy_annual_gva"], 6),
                "difference": round(diff, 6),
                "absolute_difference": round(abs(diff), 6),
                "percent_difference_vs_old": round(diff / old * 100.0, 6) if old else "",
            }
        )
    return comparison, sorted(summary, key=lambda row: row["absolute_difference"], reverse=True)


def main() -> int:
    data = fetch_seoul_business_json()
    proxy_rows = extract_latest_proxy_rows(data)
    weights = build_latest_weights(proxy_rows)
    latest_rows, skipped = allocate_seoul_with_latest_weights(weights, proxy_rows)
    comparison, summary = compare_2023_totals(latest_rows)

    write_csv(PROCESSED_DIR / "seoul_emd_business_proxy_2024.csv", proxy_rows)
    write_csv(PROCESSED_DIR / "seoul_emd_business_weights_2024.csv", weights)
    write_csv(PROCESSED_DIR / "seoul_emd_quarterly_gva_estimates_2024_proxy.csv", latest_rows)
    write_csv(PROCESSED_DIR / "seoul_emd_2024_proxy_allocation_skipped.csv", skipped)
    write_csv(PROCESSED_DIR / "seoul_emd_2015_vs_2024_proxy_comparison.csv", comparison)
    write_csv(PROCESSED_DIR / "seoul_emd_2015_vs_2024_proxy_summary.csv", summary)

    print(f"Seoul proxy rows: {len(proxy_rows)}")
    print(f"Seoul weights: {len(weights)}")
    print(f"Latest proxy quarterly rows: {len(latest_rows)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Comparison rows: {len(comparison)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
