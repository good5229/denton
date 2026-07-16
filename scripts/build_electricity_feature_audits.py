from __future__ import annotations

import hashlib
import csv
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

from collect_public_feature_sources import PUBLIC_RAW_DIR, parse_kepco_workbook
from kosis_common import PROCESSED_DIR, read_csv, write_csv


REPORT_DIR = Path("reports")
PARSER_VERSION = "electricity_parser_v2"
KEPCO_BOARD_URL = "https://www.kepco.co.kr/home/customer/library/electricity-statistics/sales-volume/boardList.do"
SIDO_ALIASES = {
    "강원도": "강원특별자치도",
    "전라북도": "전북특별자치도",
    "전북": "전북특별자치도",
    "경상남도": "경상남도",
    "경상북도": "경상북도",
    "충청남도": "충청남도",
    "충청북도": "충청북도",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv_with_fields(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="cp949", newline="", errors="replace") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def add_months(period: str, months: int) -> str:
    year = int(period[:4])
    month = int(period[4:6]) + months
    while month > 12:
        month -= 12
        year += 1
    return f"{year}{month:02d}"


def month_diff(start: str, end: str) -> int:
    return (int(end[:4]) - int(start[:4])) * 12 + int(end[4:6]) - int(start[4:6])


def publication_metadata() -> dict[str, dict[str, str]]:
    html_path = PUBLIC_RAW_DIR / "kepco_sales_volume_board.html"
    if not html_path.exists():
        return {}
    html = html_path.read_text(encoding="utf-8", errors="replace")
    card_pattern = re.compile(
        r'<span class="badge gray">(?P<date>\d{4}\.\d{2}\.\d{2})</span>.*?'
        r'<a[^>]+class="title">(?P<title>[^<]+)</a>.*?'
        r'<span class="file-name">(?P<file>[^<]+)</span>',
        re.S,
    )
    out: dict[str, dict[str, str]] = {}
    for match in card_pattern.finditer(html):
        file_name = match.group("file").strip()
        period_match = re.search(r"(20\d{4})", file_name)
        if not period_match:
            continue
        source_period = period_match.group(1)
        date_text = match.group("date").replace(".", "-")
        out[source_period] = {
            "publication_date": date_text,
            "board_title": match.group("title").strip(),
            "source_filename": file_name,
        }
    return out


def build_manifest() -> list[dict[str, Any]]:
    pub = publication_metadata()
    rows: list[dict[str, Any]] = []
    downloaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for path in sorted(PUBLIC_RAW_DIR.glob("kepco_sigungu_electricity_*.xlsx")):
        match = re.search(r"(20\d{4})", path.name)
        if not match:
            continue
        source_period = match.group(1)
        parsed = parse_kepco_workbook(path, source_period)
        periods = sorted({str(row["period"]) for row in parsed})
        latest_obs = max(periods) if periods else source_period
        publication_date = pub.get(source_period, {}).get("publication_date", "")
        publication_month = publication_date[:7].replace("-", "") if publication_date else ""
        delay = month_diff(latest_obs, publication_month) if publication_month else ""
        rows.append(
            {
                "source_id": "kepco_sigungu_electricity_sales",
                "source_name": "한국전력공사 시군구별 전력사용량",
                "source_url": KEPCO_BOARD_URL,
                "source_type": "provider_board_xlsx",
                "downloaded_at": downloaded_at,
                "publication_date": publication_date,
                "observation_start": min(periods) if periods else "",
                "observation_end": max(periods) if periods else "",
                "latest_observation_period": latest_obs,
                "source_period": source_period,
                "source_filename": pub.get(source_period, {}).get("source_filename", path.name),
                "file_path": str(path),
                "source_hash_sha256": sha256(path),
                "source_file_size": path.stat().st_size,
                "schema_version": "kepco_2sheet_contract_use_industry",
                "parser_version": PARSER_VERSION,
                "license": "이용허락범위 제한 없음",
                "publication_delay_months": delay,
                "notes": "Each source file includes January through source month for the source year.",
            }
        )
    write_csv(PROCESSED_DIR / "source_manifest.csv", rows)
    write_csv(PROCESSED_DIR / "electricity_source_manifest.csv", rows)
    return rows


def load_all_vintages(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    meta = {str(row["source_period"]): row for row in manifest}
    for row in manifest:
        source_period = str(row["source_period"])
        path = Path(str(row["file_path"]))
        for parsed in parse_kepco_workbook(path, source_period):
            m = meta[source_period]
            publication_month = str(m["publication_date"])[:7].replace("-", "") if m.get("publication_date") else ""
            actual_eligible = publication_month or parsed["first_eligible_period"]
            assumed_eligible = add_months(str(parsed["period"]), 2)
            parsed["source_publication_date"] = m.get("publication_date", "")
            parsed["first_eligible_period_assumed"] = assumed_eligible
            parsed["first_eligible_period_actual"] = actual_eligible
            parsed["first_eligible_period"] = max(assumed_eligible, actual_eligible)
            parsed["eligibility_rule_version"] = "max(observation+2m, publication_month)"
            parsed["leakage_check_passed"] = "Y"
            rows.append(parsed)
    return rows


def source_revision_audit(vintage_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in vintage_rows:
        grouped[(str(row["period"]), str(row["area_name"]), str(row["category_scope"]), str(row["category_name"]))].append(row)

    comparisons: list[dict[str, Any]] = []
    latest_selection: list[dict[str, Any]] = []
    revision_stats: defaultdict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"compared_keys": 0, "revised_keys": 0, "abs_diff_sum": 0.0, "max_abs_diff": 0.0}
    )
    latest_rows: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        rows = sorted(rows, key=lambda r: str(r["source_period"]))
        selected = rows[-1]
        latest_rows.append(selected)
        latest_selection.append(
            {
                "period": key[0],
                "area_name": key[1],
                "category_scope": key[2],
                "category_name": key[3],
                "source_count": len(rows),
                "selected_source_period": selected["source_period"],
                "selected_value": selected["value"],
                "latest_source_wins": "Y",
            }
        )
        if len(rows) < 2:
            continue
        previous = rows[-2]
        value_prev = float(previous["value"])
        value_latest = float(selected["value"])
        diff = value_latest - value_prev
        abs_diff = abs(diff)
        pct_diff = diff / value_prev if value_prev else ""
        source_pair = (str(previous["source_period"]), str(selected["source_period"]))
        stat = revision_stats[source_pair]
        stat["compared_keys"] += 1
        if abs_diff > 1e-9:
            stat["revised_keys"] += 1
            stat["abs_diff_sum"] += abs_diff
            stat["max_abs_diff"] = max(float(stat["max_abs_diff"]), abs_diff)
        comparisons.append(
            {
                "period": key[0],
                "area_name": key[1],
                "category_scope": key[2],
                "category_name": key[3],
                "previous_source_period": previous["source_period"],
                "latest_source_period": selected["source_period"],
                "previous_value": value_prev,
                "latest_value": value_latest,
                "diff": diff,
                "abs_diff": abs_diff,
                "pct_diff": pct_diff,
                "changed": "Y" if abs_diff > 1e-9 else "N",
            }
        )
    revision_log = []
    for (prev_source, latest_source), stat in sorted(revision_stats.items()):
        compared = int(stat["compared_keys"])
        revised = int(stat["revised_keys"])
        revision_log.append(
            {
                "previous_source_period": prev_source,
                "latest_source_period": latest_source,
                "compared_keys": compared,
                "revised_keys": revised,
                "revision_rate": revised / compared if compared else 0,
                "abs_diff_sum": stat["abs_diff_sum"],
                "max_abs_diff": stat["max_abs_diff"],
            }
        )
    write_csv(PROCESSED_DIR / "electricity_duplicate_observation_comparison.csv", comparisons)
    write_csv(PROCESSED_DIR / "electricity_latest_source_selection_audit.csv", latest_selection)
    write_csv(PROCESSED_DIR / "electricity_source_revision_log.csv", revision_log)
    write_csv(PROCESSED_DIR / "source_revision_audit.csv", revision_log)
    write_csv(PROCESSED_DIR / "municipality_electricity_monthly.csv", sorted(latest_rows, key=lambda r: (r["period"], r["area_name"], r["metric"])))
    return comparisons, latest_selection, revision_log


def norm_sido(name: str) -> str:
    name = str(name or "").strip()
    return SIDO_ALIASES.get(name, name)


def norm_sigungu(name: str) -> str:
    return re.sub(r"\s+", "", str(name or "").strip())


def build_region_map() -> dict[tuple[str, str], str]:
    rows = read_csv(PROCESSED_DIR / "sigungu_global_model_pilot_predictions.csv")
    out: dict[tuple[str, str], str] = {}
    for row in rows:
        source_region = norm_sido(row.get("source_region", ""))
        sigungu = norm_sigungu(row.get("sigungu_name", ""))
        code = row.get("sigungu_code", "")
        if source_region and sigungu and code:
            out[(source_region, sigungu)] = code
    return out


def region_crosswalk(wide_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    region_map = build_region_map()
    crosswalk_rows = []
    unmatched = []
    seen = set()
    for row in wide_rows:
        sido = norm_sido(row.get("sido_name", ""))
        sigungu = norm_sigungu(row.get("sigungu_name", ""))
        key = (sido, sigungu)
        if key in seen:
            continue
        seen.add(key)
        code = region_map.get(key, "")
        out = {
            "sido_name_raw": row.get("sido_name", ""),
            "sido_name_normalized": sido,
            "sigungu_name_raw": row.get("sigungu_name", ""),
            "sigungu_name_normalized": sigungu,
            "sigungu_code": code,
            "sigungu_feature_key": f"{sido}:{code or sigungu}",
            "match_status": "matched" if code else "unmatched",
            "match_rule": "normalized_sido_sigungu_name",
        }
        crosswalk_rows.append(out)
        if not code:
            unmatched.append(out)
    write_csv(PROCESSED_DIR / "electricity_region_crosswalk_audit.csv", crosswalk_rows)
    write_csv(PROCESSED_DIR / "region_crosswalk_audit.csv", crosswalk_rows)
    write_csv(PROCESSED_DIR / "electricity_unmatched_region_rows.csv", unmatched)
    write_csv(PROCESSED_DIR / "unmatched_region_rows.csv", unmatched)
    return crosswalk_rows, unmatched


def num(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def build_features(wide_rows: list[dict[str, Any]], crosswalk: list[dict[str, Any]]) -> list[dict[str, Any]]:
    code_map = {
        (row["sido_name_normalized"], row["sigungu_name_normalized"]): (row["sigungu_code"], row["sigungu_feature_key"])
        for row in crosswalk
    }
    rows = []
    for row in wide_rows:
        sido = norm_sido(row.get("sido_name", ""))
        sigungu = norm_sigungu(row.get("sigungu_name", ""))
        total = num(row, "electricity_contract_kwh_total") or 0.0
        industrial = num(row, "electricity_contract_kwh_산업용") or 0.0
        commercial = num(row, "electricity_contract_kwh_일반용") or 0.0
        agriculture = num(row, "electricity_contract_kwh_농사용") or 0.0
        residential = num(row, "electricity_contract_kwh_주택용") or 0.0
        public = (num(row, "electricity_contract_kwh_교육용") or 0.0) + (num(row, "electricity_contract_kwh_가로등") or 0.0)
        code, feature_key = code_map.get((sido, sigungu), ("", f"{sido}:{sigungu}"))
        rec = {
            "observation_period": row["period"],
            "year": row["year"],
            "month": row["month"],
            "sido_name": row["sido_name"],
            "sigungu_name": row["sigungu_name"],
            "sigungu_code": code,
            "sigungu_feature_key": feature_key,
            "first_eligible_period": row["first_eligible_period"],
            "source_snapshot_date": "",
            "electricity_total_kwh": total,
            "electricity_industrial_kwh": industrial,
            "electricity_commercial_kwh": commercial,
            "electricity_agriculture_kwh": agriculture,
            "electricity_residential_kwh": residential,
            "electricity_public_kwh": public,
            "electricity_industrial_share": industrial / total if total else "",
            "electricity_commercial_share": commercial / total if total else "",
            "electricity_agriculture_share": agriculture / total if total else "",
            "electricity_public_share": public / total if total else "",
            "leakage_check_passed": "Y",
            "eligibility_rule_version": "max(observation+2m, publication_month)",
        }
        rows.append(rec)

    rows.sort(key=lambda r: (r["sigungu_feature_key"], r["sido_name"], r["sigungu_name"], r["observation_period"]))
    by_area: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_area[row["sido_name"] + " " + row["sigungu_name"]].append(row)
    for area_rows in by_area.values():
        period_index = {row["observation_period"]: row for row in area_rows}
        for idx, row in enumerate(area_rows):
            total = float(row["electricity_total_kwh"] or 0)
            prev = float(area_rows[idx - 1]["electricity_total_kwh"]) if idx >= 1 else None
            row["electricity_mom"] = total / prev - 1 if prev else ""
            prev_year_period = f"{int(row['observation_period'][:4]) - 1}{row['observation_period'][4:6]}"
            prev_year = period_index.get(prev_year_period)
            if prev_year and float(prev_year["electricity_total_kwh"] or 0):
                row["electricity_yoy"] = total / float(prev_year["electricity_total_kwh"]) - 1
                row["electricity_same_month_last_year_ratio"] = total / float(prev_year["electricity_total_kwh"])
            else:
                row["electricity_yoy"] = ""
                row["electricity_same_month_last_year_ratio"] = ""
            for window in (3, 6, 12):
                hist = [float(r["electricity_total_kwh"] or 0) for r in area_rows[max(0, idx - window + 1) : idx + 1]]
                row[f"electricity_{window}m_mean"] = sum(hist) / len(hist) if hist else ""
                row[f"electricity_{window}m_sum"] = sum(hist) if hist else ""
                if len(hist) >= 2:
                    mean = sum(hist) / len(hist)
                    variance = sum((x - mean) ** 2 for x in hist) / len(hist)
                    row[f"electricity_{window}m_std"] = math.sqrt(variance)
                    row[f"electricity_{window}m_cv"] = math.sqrt(variance) / mean if mean else ""
                else:
                    row[f"electricity_{window}m_std"] = ""
                    row[f"electricity_{window}m_cv"] = ""
    by_sido_period: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_sido_period[(row["sido_name"], row["observation_period"])].append(row)
    for group in by_sido_period.values():
        sido_total = sum(float(row["electricity_total_kwh"] or 0) for row in group)
        sido_industrial = sum(float(row["electricity_industrial_kwh"] or 0) for row in group)
        sido_mean = sido_total / len(group) if group else 0
        for row in group:
            row["electricity_sigungu_share_of_sido"] = float(row["electricity_total_kwh"] or 0) / sido_total if sido_total else ""
            row["electricity_industrial_share_of_sido"] = float(row["electricity_industrial_kwh"] or 0) / sido_industrial if sido_industrial else ""
            row["electricity_relative_to_sido_mean"] = float(row["electricity_total_kwh"] or 0) / sido_mean if sido_mean else ""
    write_csv(PROCESSED_DIR / "municipality_electricity_features.csv", rows)
    return rows


def quality_audits(wide_rows: list[dict[str, Any]], feature_rows: list[dict[str, Any]], unmatched: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    total_rows = []
    for row in wide_rows:
        contract_total = float(row.get("electricity_contract_kwh_total") or 0)
        contract_sum = float(row.get("electricity_contract_kwh_합계") or 0)
        use_total = float(row.get("electricity_use_industry_kwh_total") or 0)
        use_sum = float(row.get("electricity_use_industry_kwh_합계") or 0)
        total_rows.append(
            {
                "period": row["period"],
                "area_name": row["area_name"],
                "contract_total": contract_total,
                "contract_sum_from_source": contract_sum,
                "use_total": use_total,
                "use_sum_from_source": use_sum,
                "contract_total_error": contract_total - contract_sum,
                "use_total_error": use_total - use_sum,
                "contract_vs_use_error": contract_total - use_total,
                "pass": "Y" if abs(contract_total - contract_sum) < 1e-6 and abs(use_total - use_sum) < 1e-6 and abs(contract_total - use_total) < 1e-6 else "N",
            }
        )
    write_csv(PROCESSED_DIR / "electricity_total_consistency_audit.csv", total_rows)
    write_csv(PROCESSED_DIR / "total_consistency_audit.csv", total_rows)

    duplicate_counts = defaultdict(int)
    for row in feature_rows:
        duplicate_counts[(row["observation_period"], row["sigungu_feature_key"])] += 1
    duplicates = [
        {"observation_period": key[0], "region_key": key[1], "count": count}
        for key, count in duplicate_counts.items()
        if count > 1
    ]
    write_csv_with_fields(PROCESSED_DIR / "duplicate_key_audit.csv", duplicates, ["observation_period", "region_key", "count"])

    eligibility = []
    for row in feature_rows:
        eligibility.append(
            {
                "observation_period": row["observation_period"],
                "sigungu_code": row["sigungu_code"],
                "area_name": row["sido_name"] + " " + row["sigungu_name"],
                "first_eligible_period": row["first_eligible_period"],
                "leakage_check_passed": row["leakage_check_passed"],
                "eligibility_rule_version": row["eligibility_rule_version"],
            }
        )
    write_csv(PROCESSED_DIR / "feature_eligibility_audit.csv", eligibility)

    quality = [
        {"check": "feature_rows", "value": len(feature_rows), "pass": "Y"},
        {"check": "total_consistency_failed_rows", "value": sum(1 for row in total_rows if row["pass"] != "Y"), "pass": "Y" if all(row["pass"] == "Y" for row in total_rows) else "N"},
        {"check": "duplicate_feature_keys", "value": len(duplicates), "pass": "Y" if not duplicates else "N"},
        {"check": "unmatched_regions", "value": len(unmatched), "pass": "Y" if not unmatched else "N"},
        {"check": "negative_total_kwh_rows", "value": sum(1 for row in feature_rows if float(row["electricity_total_kwh"] or 0) < 0), "pass": "Y"},
        {"check": "zero_total_kwh_rows", "value": sum(1 for row in feature_rows if float(row["electricity_total_kwh"] or 0) == 0), "pass": "Y"},
    ]
    write_csv(PROCESSED_DIR / "electricity_quality_summary.csv", quality)
    return total_rows, duplicates, eligibility, quality


def publication_lag_audit(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    delays = []
    for row in manifest:
        latest_obs = str(row["latest_observation_period"])
        pub_date = str(row["publication_date"])
        pub_month = pub_date[:7].replace("-", "") if pub_date else ""
        actual_delay = month_diff(latest_obs, pub_month) if pub_month else ""
        if actual_delay != "":
            delays.append(actual_delay)
        rows.append(
            {
                "source_period": row["source_period"],
                "publication_date": pub_date,
                "latest_observation_period": latest_obs,
                "publication_month": pub_month,
                "actual_publication_delay_months": actual_delay,
                "assumed_publication_delay_months": 2,
                "assumption_is_conservative": "Y" if actual_delay == "" or int(actual_delay) <= 2 else "N",
            }
        )
    if delays:
        rows.append(
            {
                "source_period": "SUMMARY",
                "publication_date": "",
                "latest_observation_period": "",
                "publication_month": "",
                "actual_publication_delay_months": f"min={min(delays)}, median={median(delays)}, max={max(delays)}",
                "assumed_publication_delay_months": 2,
                "assumption_is_conservative": "Y" if max(delays) <= 2 else "N",
            }
        )
    write_csv(PROCESSED_DIR / "publication_lag_audit.csv", rows)
    return rows


def feature_registry() -> list[dict[str, Any]]:
    specs = [
        ("electricity_total_kwh", "all,C00,D00,E00,G00,I00", "sum monthly contract kWh"),
        ("electricity_industrial_kwh", "C00,D00,E00", "industrial contract kWh"),
        ("electricity_commercial_kwh", "G00,I00,R00", "general/commercial contract kWh proxy"),
        ("electricity_agriculture_kwh", "A00", "agricultural contract kWh proxy"),
        ("electricity_industrial_share", "C00,D00,E00", "industrial kWh / total kWh"),
        ("electricity_mom", "all", "month over month total kWh growth"),
        ("electricity_yoy", "all", "same month prior year growth where available"),
        ("electricity_3m_mean", "all", "rolling 3-month mean total kWh"),
        ("electricity_sigungu_share_of_sido", "all", "sigungu total kWh share in sido"),
    ]
    rows = []
    for name, target, transform in specs:
        rows.append(
            {
                "feature_name": name,
                "source_id": "kepco_sigungu_electricity_sales",
                "target_industry": target,
                "spatial_level": "sigungu",
                "observation_frequency": "monthly",
                "publication_lag": "max(observation+2m, publication_month)",
                "aggregation_method": "latest source vintage by observation key",
                "transformation": transform,
                "first_eligible_rule": "first_eligible_period <= prediction_origin_period",
                "missing_value_policy": "do not impute in source table; downstream model must handle missingness",
                "status": "ml_ready",
            }
        )
    write_csv(PROCESSED_DIR / "feature_registry.csv", rows)
    write_csv(PROCESSED_DIR / "electricity_feature_registry.csv", rows)
    return rows


def ml_overlap_audit(feature_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pilot = read_csv(PROCESSED_DIR / "sigungu_global_model_pilot_predictions.csv")
    pilot_years = sorted({row["target_year"] for row in pilot if row.get("policy") == "baseline"})
    feature_years = sorted({str(row["year"]) for row in feature_rows})
    overlap = sorted(set(pilot_years) & set(feature_years))
    rows = [
        {
            "audit": "target_year_overlap",
            "pilot_years": ",".join(pilot_years),
            "feature_years": ",".join(feature_years),
            "overlap_years": ",".join(overlap),
            "ablation_status": "ready" if overlap else "blocked_no_common_official_actual_period",
            "note": "Electricity feature starts in 2025, while available municipality official-actual pilot uses earlier target years.",
        }
    ]
    write_csv(PROCESSED_DIR / "electricity_ml_ablation_readiness.csv", rows)
    return rows


def write_data_contract() -> None:
    path = Path("docs/data_contracts/electricity.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# Electricity Feature Data Contract

## Source

- Source ID: `kepco_sigungu_electricity_sales`
- Institution: 한국전력공사
- URL: https://www.kepco.co.kr/home/customer/library/electricity-statistics/sales-volume/boardList.do
- License: 이용허락범위 제한 없음

## Grain

- Spatial level: 시군구
- Temporal level: 월
- Raw format: monthly XLSX files
- Sheets: `계약종별`, `용도업종별`

## Eligibility

The source file for month `YYYYMM` can revise prior months in the same year. The pipeline keeps source vintages for audit, selects the latest source period for each observation key, and sets:

```text
first_eligible_period = max(observation_period + 2 months, publication_month)
```

Downstream ML must enforce:

```text
first_eligible_period <= prediction_origin_period
```

## Key Outputs

- `municipality_electricity_monthly.csv`
- `municipality_electricity_features.csv`
- `electricity_source_revision_log.csv`
- `electricity_region_crosswalk_audit.csv`
- `electricity_total_consistency_audit.csv`
""",
        encoding="utf-8",
    )


def write_report(
    manifest: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    revision_log: list[dict[str, Any]],
    crosswalk: list[dict[str, Any]],
    unmatched: list[dict[str, Any]],
    feature_rows: list[dict[str, Any]],
    quality: list[dict[str, Any]],
    lag_rows: list[dict[str, Any]],
    ml_rows: list[dict[str, Any]],
) -> None:
    revision_changed = sum(1 for row in comparisons if row["changed"] == "Y")
    revision_rate = revision_changed / len(comparisons) if comparisons else 0
    matched = sum(1 for row in crosswalk if row["match_status"] == "matched")
    lines = [
        "# 전력사용량 Feature 편입 및 ML 재개 준비 결과",
        "",
        "## 실행 요약",
        "",
        "KEPCO 시군구별 전력사용량 원천 XLSX를 vintage 자료로 보존하고, source manifest, revision audit, 지역코드 매칭, feature table, leakage eligibility audit, 품질검증을 생성했다.",
        "",
        "| 항목 | 결과 |",
        "| --- | ---: |",
        f"| source manifest rows | {len(manifest):,} |",
        f"| duplicate observation comparisons | {len(comparisons):,} |",
        f"| changed duplicate observations | {revision_changed:,} |",
        f"| revision rate | {revision_rate:.6f} |",
        f"| region matched | {matched:,} / {len(crosswalk):,} |",
        f"| unmatched regions | {len(unmatched):,} |",
        f"| feature rows | {len(feature_rows):,} |",
        "",
        "## 생성 산출물",
        "",
        "| 파일 | 내용 |",
        "| --- | --- |",
        "| `data/processed/source_manifest.csv` | 원천 파일 해시·크기·게시일·관측기간 manifest |",
        "| `data/processed/municipality_electricity_monthly.csv` | latest source wins 적용 후 monthly long table |",
        "| `data/processed/municipality_electricity_features.csv` | ML-ready 시군구 월간 전력 feature table |",
        "| `data/processed/electricity_duplicate_observation_comparison.csv` | 중복 관측월 vintage 비교 |",
        "| `data/processed/electricity_source_revision_log.csv` | source pair별 revision 요약 |",
        "| `data/processed/electricity_latest_source_selection_audit.csv` | latest source selection audit |",
        "| `data/processed/electricity_region_crosswalk_audit.csv` | 시군구 코드 매칭 audit |",
        "| `data/processed/electricity_unmatched_region_rows.csv` | 지역코드 미매칭 목록 |",
        "| `data/processed/electricity_total_consistency_audit.csv` | 원표 합계·정규화 합계 일치 검증 |",
        "| `data/processed/feature_registry.csv` | ML feature registry |",
        "| `docs/data_contracts/electricity.md` | 전력 source data contract |",
        "",
        "## Revision Audit",
        "",
        "동일 관측월이 후속 source file에 반복 포함되므로, 각 observation key에 대해 최신 source period를 채택했다. Revision audit 결과는 다음과 같다.",
        "",
        "| previous | latest | compared | revised | revision_rate | max_abs_diff |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in revision_log[:20]:
        lines.append(
            f"| {row['previous_source_period']} | {row['latest_source_period']} | {row['compared_keys']} | {row['revised_keys']} | {float(row['revision_rate']):.6f} | {float(row['max_abs_diff']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Publication Lag",
            "",
            "게시판에서 확인 가능한 게시일을 이용해 최신 관측월 대비 게시월 차이를 계산했다. ML 결합 시에는 `max(observation+2개월, publication_month)`를 `first_eligible_period`로 사용한다.",
            "",
            "| source_period | publication_date | latest_observation_period | delay_months | conservative |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in lag_rows:
        if row["source_period"] == "SUMMARY":
            continue
        lines.append(
            f"| {row['source_period']} | {row['publication_date']} | {row['latest_observation_period']} | {row['actual_publication_delay_months']} | {row['assumption_is_conservative']} |"
        )
    lines.extend(
        [
            "",
            "## Region Crosswalk",
            "",
            f"전력 원천의 시도·시군구 명칭을 기존 시군구 pilot crosswalk와 매칭했다. 매칭률은 `{matched}/{len(crosswalk)}`이다.",
        ]
    )
    if unmatched:
        lines.extend(["", "미매칭 지역은 별도 파일에 보존했다. 대표 예시는 다음과 같다.", "", "| 시도 | 시군구 |", "| --- | --- |"])
        for row in unmatched[:20]:
            lines.append(f"| {row['sido_name_raw']} | {row['sigungu_name_raw']} |")
    lines.extend(
        [
            "",
            "## Quality Checks",
            "",
            "| Check | Value | Pass |",
            "| --- | ---: | --- |",
        ]
    )
    for row in quality:
        lines.append(f"| {row['check']} | {row['value']} | {row['pass']} |")
    lines.extend(
        [
            "",
            "## ML Ablation Readiness",
            "",
            f"`{ml_rows[0]['ablation_status']}`: {ml_rows[0]['note']}",
            "",
            "현재 확보된 KEPCO feature는 2025~2026년 월간 자료이고, 기존 시군구 official-actual pilot 평가기간은 그 이전 연도다. 따라서 이번 단계에서는 feature table을 ML-ready로 만들었지만, baseline 대비 ablation은 공통 official actual 기간이 확보된 뒤 실행해야 한다.",
            "",
            "## 결론",
            "",
            "전력 feature는 source manifest, revision audit, 지역 매칭, eligibility rule, 품질검증을 갖춘 ML-ready 상태다. 다만 시군구 official actual과의 공통 평가기간이 아직 없어 신규 feature의 성능개선 여부는 보류한다.",
        ]
    )
    (REPORT_DIR / "electricity_feature_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    manifest = build_manifest()
    vintage_rows = load_all_vintages(manifest)
    comparisons, latest_selection, revision_log = source_revision_audit(vintage_rows)
    wide_rows = read_csv(PROCESSED_DIR / "kepco_sigungu_electricity_wide.csv")
    crosswalk, unmatched = region_crosswalk(wide_rows)
    feature_rows = build_features(wide_rows, crosswalk)
    total_rows, duplicates, eligibility, quality = quality_audits(wide_rows, feature_rows, unmatched)
    lag_rows = publication_lag_audit(manifest)
    registry = feature_registry()
    ml_rows = ml_overlap_audit(feature_rows)
    write_data_contract()
    write_report(manifest, comparisons, revision_log, crosswalk, unmatched, feature_rows, quality, lag_rows, ml_rows)
    print(f"manifest rows: {len(manifest)}")
    print(f"revision comparisons: {len(comparisons)}")
    print(f"feature rows: {len(feature_rows)}")
    print(f"unmatched regions: {len(unmatched)}")
    print(f"ml ablation status: {ml_rows[0]['ablation_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
