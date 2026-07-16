from __future__ import annotations

import csv
import html
import json
import re
import subprocess
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any

from kosis_common import (
    PROCESSED_DIR,
    RAW_DIR,
    get_kosis_key,
    normalize_kosis_rows,
    parse_number,
    read_csv,
    write_csv,
    write_json,
)


DATA_API = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
METADATA_API = "https://kosis.kr/statHtml/statHtmlContent.do"
YEARS = ("2020", "2021", "2022", "2023", "2024")

STRUCTURAL_BUSINESS_TABLE = ("101", "DT_1K52F08")
BUSINESS_SIZE_TABLE = ("101", "DT_1K52F03")

ITEM_NAME_TO_METRIC = {
    "사업체수": "establishments",
    "종사자수": "employees",
    "매출액": "sales",
}


def curl_json(url: str, params: dict[str, str]) -> Any:
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    completed = subprocess.run(
        [
            "curl",
            "-sS",
            "--connect-timeout",
            "10",
            "--max-time",
            "90",
            "--retry",
            "2",
            "--retry-delay",
            "1",
            full_url,
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(completed.stdout)
    if isinstance(data, dict) and data.get("err"):
        raise RuntimeError(f"KOSIS error {data.get('err')}: {data.get('errMsg')}")
    return data


def fetch_metadata(org_id: str, tbl_id: str) -> dict[str, Any]:
    path = RAW_DIR / f"kosis_{org_id}_{tbl_id}_metadata.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    params = {"orgId": org_id, "tblId": tbl_id, "conn_path": "C1"}
    completed = subprocess.run(
        [
            "curl",
            "-L",
            "-sS",
            "--connect-timeout",
            "10",
            "--max-time",
            "90",
            "--retry",
            "2",
            "--retry-delay",
            "1",
            f"{METADATA_API}?{urllib.parse.urlencode(params)}",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    html_path = RAW_DIR / f"kosis_{org_id}_{tbl_id}_statHtmlContent.html"
    html_path.write_text(completed.stdout, encoding="utf-8")
    match = re.search(r"var\s+g_jsonStatInfo\s*=\s*'(.+?)';", completed.stdout, re.S)
    if not match:
        raise RuntimeError(f"g_jsonStatInfo not found for {org_id}/{tbl_id}")
    info = json.loads(html.unescape(match.group(1)))
    write_json(path, info)
    return info


def kosis_data_curl(
    api_key: str,
    *,
    org_id: str,
    tbl_id: str,
    item_id: str,
    period: str,
    start: str,
    end: str,
    obj: dict[int, str],
) -> list[dict[str, Any]]:
    params = {
        "method": "getList",
        "apiKey": api_key,
        "orgId": org_id,
        "tblId": tbl_id,
        "itmId": item_id,
        "prdSe": period,
        "startPrdDe": start,
        "endPrdDe": end,
        "format": "json",
        "jsonVD": "Y",
    }
    for idx, value in obj.items():
        params[f"objL{idx}"] = value
    data = curl_json(DATA_API, params)
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected KOSIS response for {tbl_id}: {data!r}")
    return data


def item_metrics(info: dict[str, Any], wanted: set[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for item in (info.get("itemInfo") or {}).get("itmList", []):
        name = str(item.get("scrKor") or "").replace(" ", "")
        for token, metric in ITEM_NAME_TO_METRIC.items():
            if token in name and metric in wanted:
                out.append((str(item.get("itmId")), metric))
                break
    return out


def industry_codes(info: dict[str, Any]) -> list[tuple[str, str]]:
    for class_info in info.get("classInfoList", []):
        name = str(class_info.get("classNm") or "")
        if "산업" not in name:
            continue
        codes = []
        for item in class_info.get("itmList", []):
            code = str(item.get("itmId") or "")
            if not code:
                continue
            codes.append((code, str(item.get("scrKor") or "")))
        return codes
    return []


def collect_structural_business(api_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    org_id, tbl_id = STRUCTURAL_BUSINESS_TABLE
    info = fetch_metadata(org_id, tbl_id)
    items = item_metrics(info, {"establishments", "employees", "sales"})
    industries = industry_codes(info)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    for item_id, metric in items:
        for industry_id, industry_name in industries:
            try:
                data = kosis_data_curl(
                    api_key,
                    org_id=org_id,
                    tbl_id=tbl_id,
                    item_id=item_id,
                    period="Y",
                    start=YEARS[0],
                    end=YEARS[-1],
                    obj={1: "ALL", 2: industry_id},
                )
            except Exception as exc:
                failures.append(
                    {
                        "source": "sido_industry_business",
                        "org_id": org_id,
                        "tbl_id": tbl_id,
                        "item_id": item_id,
                        "metric": metric,
                        "industry_code": industry_id,
                        "industry_name": industry_name,
                        "error": str(exc),
                    }
                )
                continue
            raw[f"{item_id}_{industry_id}"] = data
            for row in normalize_kosis_rows(data, "sido_industry_business"):
                row["metric"] = metric
                rows.append(row)
            time.sleep(0.02)
    write_json(RAW_DIR / "business_sido_industry_all.json", raw)
    write_csv(PROCESSED_DIR / "business_sido_industry_all.csv", rows)
    write_csv(PROCESSED_DIR / "business_sido_industry_failures.csv", failures)
    return rows, failures


def collect_business_size(api_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    org_id, tbl_id = BUSINESS_SIZE_TABLE
    info = fetch_metadata(org_id, tbl_id)
    items = item_metrics(info, {"establishments", "employees"})
    industries = industry_codes(info)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    for item_id, metric in items:
        for industry_id, industry_name in industries:
            try:
                data = kosis_data_curl(
                    api_key,
                    org_id=org_id,
                    tbl_id=tbl_id,
                    item_id=item_id,
                    period="Y",
                    start=YEARS[0],
                    end=YEARS[-1],
                    obj={1: "ALL", 2: industry_id, 3: "ALL"},
                )
            except Exception as exc:
                failures.append(
                    {
                        "source": "sido_industry_employee_size",
                        "org_id": org_id,
                        "tbl_id": tbl_id,
                        "item_id": item_id,
                        "metric": metric,
                        "industry_code": industry_id,
                        "industry_name": industry_name,
                        "error": str(exc),
                    }
                )
                continue
            raw[f"{item_id}_{industry_id}"] = data
            for row in normalize_kosis_rows(data, "sido_industry_employee_size"):
                row["metric"] = metric
                rows.append(row)
            time.sleep(0.02)
    write_json(RAW_DIR / "business_size_sido_industry.json", raw)
    write_csv(PROCESSED_DIR / "business_size_sido_industry.csv", rows)
    write_csv(PROCESSED_DIR / "business_size_sido_industry_failures.csv", failures)
    return rows, failures


def area_level(code: str) -> str:
    code = str(code or "").strip()
    if code in {"", "00", "0"}:
        return "national"
    if len(code) == 2:
        return "sido"
    if len(code) == 5:
        return "sigungu"
    if len(code) >= 7:
        return "eupmyeondong"
    return "unknown"


def industry_level(code: str, name: str = "") -> str:
    code = str(code or "").strip()
    if code in {"", "0"}:
        return "all"
    if len(code) == 1 and code.isalpha():
        return "section"
    if len(code) == 3:
        return "middle"
    if len(code) == 4:
        return "small"
    if len(code) == 5:
        return "class"
    if len(code) >= 6:
        return "subclass"
    if name:
        return "named"
    return "unknown"


def add_long_row(
    out: list[dict[str, Any]],
    *,
    source_dataset: str,
    source_table: str,
    year: str,
    area_code: str,
    area_name: str,
    industry_code: str,
    industry_name: str,
    metric: str,
    value: Any,
    unit: str,
    metric_scope: str,
) -> None:
    numeric = parse_number(value)
    if numeric is None:
        return
    out.append(
        {
            "source_dataset": source_dataset,
            "source_table": source_table,
            "year": year,
            "area_code": area_code,
            "area_name": area_name,
            "area_level": area_level(area_code),
            "industry_code": industry_code,
            "industry_name": industry_name,
            "industry_level": industry_level(industry_code, industry_name),
            "metric": metric,
            "metric_scope": metric_scope,
            "value": numeric,
            "unit": unit,
            "release_lag_years_assumed": 2,
            "first_eligible_target_year": int(year) + 2 if str(year).isdigit() else "",
            "leakage_policy": "Use only if source year <= target year - 2 for Jan-1 forecast backtests.",
        }
    )


def build_feature_mart() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    long_rows: list[dict[str, Any]] = []

    for row in read_csv(PROCESSED_DIR / "business_sido_industry_all.csv"):
        add_long_row(
            long_rows,
            source_dataset="sido_industry_business",
            source_table=f"{row.get('org_id')}/{row.get('tbl_id')}",
            year=row.get("prd_de", ""),
            area_code=row.get("c1_id", ""),
            area_name=row.get("c1_nm", ""),
            industry_code=row.get("c2_id", ""),
            industry_name=row.get("c2_nm", ""),
            metric=row.get("metric", ""),
            value=row.get("value"),
            unit=row.get("unit_nm", ""),
            metric_scope="sido_industry",
        )

    for row in read_csv(PROCESSED_DIR / "business_size_sido_industry.csv"):
        size_code = row.get("c3_id", "")
        size_name = row.get("c3_nm", "")
        metric = f"{row.get('metric', '')}_size_{size_code}"
        add_long_row(
            long_rows,
            source_dataset="sido_industry_employee_size",
            source_table=f"{row.get('org_id')}/{row.get('tbl_id')}",
            year=row.get("prd_de", ""),
            area_code=row.get("c1_id", ""),
            area_name=row.get("c1_nm", ""),
            industry_code=row.get("c2_id", ""),
            industry_name=row.get("c2_nm", ""),
            metric=metric,
            value=row.get("value"),
            unit=row.get("unit_nm", ""),
            metric_scope=f"employee_size:{size_name}",
        )

    expanded_path = PROCESSED_DIR / "expanded_manufacturing_sigungu_ksic.csv"
    if expanded_path.exists():
        for row in read_csv(expanded_path):
            add_long_row(
                long_rows,
                source_dataset="manufacturing_mining_sigungu_ksic",
                source_table=f"{row.get('org_id')}/{row.get('tbl_id')}",
                year=row.get("prd_de", ""),
                area_code=row.get("c1_id", ""),
                area_name=row.get("c1_nm", ""),
                industry_code=row.get("c2_id", ""),
                industry_name=row.get("c2_nm", ""),
                metric=row.get("metric", ""),
                value=row.get("value"),
                unit=row.get("unit_nm", ""),
                metric_scope=f"ksic_{row.get('ksic_level', '')}",
            )

    emd_path = PROCESSED_DIR / "emd_economic_census_2015.csv"
    if emd_path.exists():
        for row in read_csv(emd_path):
            add_long_row(
                long_rows,
                source_dataset="emd_economic_census_2015",
                source_table=f"{row.get('org_id')}/{row.get('tbl_id')}",
                year=row.get("prd_de", ""),
                area_code=row.get("c2_id", ""),
                area_name=row.get("c2_nm", ""),
                industry_code=row.get("c1_id", ""),
                industry_name=row.get("c1_nm", ""),
                metric=row.get("metric", ""),
                value=row.get("value"),
                unit=row.get("unit_nm", ""),
                metric_scope="emd_section_proxy",
            )

    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    metric_values: defaultdict[tuple[str, str, str, str], dict[str, float]] = defaultdict(dict)
    for row in long_rows:
        key = (
            str(row["year"]),
            str(row["area_code"]),
            str(row["industry_code"]),
            str(row["source_dataset"]),
        )
        groups.setdefault(
            key,
            {
                "year": row["year"],
                "area_code": row["area_code"],
                "area_name": row["area_name"],
                "area_level": row["area_level"],
                "industry_code": row["industry_code"],
                "industry_name": row["industry_name"],
                "industry_level": row["industry_level"],
                "source_dataset": row["source_dataset"],
                "first_eligible_target_year": row["first_eligible_target_year"],
            },
        )
        metric_values[key][str(row["metric"])] = float(row["value"])

    wide_rows: list[dict[str, Any]] = []
    for key, base in groups.items():
        metrics = metric_values[key]
        out = dict(base)
        for metric, value in sorted(metrics.items()):
            out[metric] = value
        if "employees" in metrics and "establishments" in metrics and metrics["establishments"]:
            out["employees_per_establishment"] = metrics["employees"] / metrics["establishments"]
        if "sales" in metrics and "employees" in metrics and metrics["employees"]:
            out["sales_per_employee"] = metrics["sales"] / metrics["employees"]
        if "value_added" in metrics and "employees" in metrics and metrics["employees"]:
            out["value_added_per_employee"] = metrics["value_added"] / metrics["employees"]
        wide_rows.append(out)

    write_csv(PROCESSED_DIR / "municipality_feature_mart_long.csv", long_rows)
    write_csv(PROCESSED_DIR / "municipality_feature_mart_wide.csv", wide_rows)
    return long_rows, wide_rows


def source_inventory(rows: list[dict[str, Any]], failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        source = str(row["source_dataset"])
        rec = summary.setdefault(
            source,
            {
                "source_dataset": source,
                "source_table": row.get("source_table", ""),
                "rows": 0,
                "years": set(),
                "area_levels": set(),
                "industry_levels": set(),
                "metrics": set(),
                "coverage_note": "",
            },
        )
        rec["rows"] += 1
        rec["years"].add(str(row.get("year", "")))
        rec["area_levels"].add(str(row.get("area_level", "")))
        rec["industry_levels"].add(str(row.get("industry_level", "")))
        rec["metrics"].add(str(row.get("metric", "")))

    out: list[dict[str, Any]] = []
    failure_count = defaultdict(int)
    for fail in failures:
        failure_count[str(fail.get("source", ""))] += 1
    for rec in summary.values():
        area_levels = sorted(level for level in rec["area_levels"] if level)
        industry_levels = sorted(level for level in rec["industry_levels"] if level)
        out.append(
            {
                "source_dataset": rec["source_dataset"],
                "source_table": rec["source_table"],
                "rows": rec["rows"],
                "years": ",".join(sorted(rec["years"])),
                "area_levels": ",".join(area_levels),
                "industry_levels": ",".join(industry_levels),
                "metrics": ",".join(sorted(rec["metrics"])),
                "release_lag_policy": "assume year+2 availability unless table-specific release calendar is later confirmed",
                "failure_count": failure_count.get(rec["source_dataset"], 0),
            }
        )
    return sorted(out, key=lambda row: str(row["source_dataset"]))


def feature_source_candidates() -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "candidate": "electricity_sales_by_use",
            "expected_source": "한국전력공사 시군구별 전력사용량",
            "target_sectors": "C00,D00,E00,all",
            "desired_area_level": "sigungu",
            "desired_metrics": "industrial_electricity_sales, total_electricity_sales",
            "reason": "전국 시군구 월간 flow feature로 산업생산과 사업장 가동 강도를 직접 반영 가능",
            "current_status": "collected_kepco_monthly_panel",
        },
        {
            "priority": 2,
            "candidate": "building_permits_and_starts",
            "expected_source": "국토교통부 건축인허가 기본개요/건축HUB",
            "target_sectors": "F00,L00",
            "desired_area_level": "sigungu",
            "desired_metrics": "permit_area, start_area, building_stock_by_use",
            "reason": "건설업·부동산업 지역 변동을 설명할 수 있는 직접 activity 변수",
            "current_status": "metadata_collected_source_file_pending",
        },
        {
            "priority": 3,
            "candidate": "factory_registration",
            "expected_source": "공장등록/공장설립온라인지원시스템 또는 공공데이터포털",
            "target_sectors": "B00,C00",
            "desired_area_level": "sigungu",
            "desired_metrics": "registered_factories, factory_area, employee_capacity",
            "reason": "광업·제조업 시군구 share를 직접 설명할 수 있는 입지/설비 stock 변수",
            "current_status": "schema_probe_empty_workbook",
        },
        {
            "priority": 4,
            "candidate": "industrial_complex_activity",
            "expected_source": "한국산업단지공단/공공데이터포털",
            "target_sectors": "C00",
            "desired_area_level": "sigungu",
            "desired_metrics": "tenant_firms, employment, production, exports",
            "reason": "제조업 생산·수출·고용 변동을 시군구별로 직접 반영 가능",
            "current_status": "not_collected",
        },
        {
            "priority": 5,
            "candidate": "agriculture_livestock_fishery",
            "expected_source": "농림축산식품부·해양수산부·KOSIS 농어업 통계",
            "target_sectors": "A00",
            "desired_area_level": "sigungu",
            "desired_metrics": "cultivated_area, crop_output, livestock_heads, fishery_output",
            "reason": "농림어업은 사업체수보다 생산량·면적·사육두수 신호가 직접적",
            "current_status": "not_collected",
        },
        {
            "priority": 6,
            "candidate": "local_card_sales_and_foot_traffic",
            "expected_source": "지자체 상권/카드매출/생활인구 자료",
            "target_sectors": "G00,I00,R00",
            "desired_area_level": "sigungu,eupmyeondong",
            "desired_metrics": "card_sales, visitors, floating_population",
            "reason": "도소매·숙박음식·여가서비스의 하위지역 수요 proxy",
            "current_status": "not_collected",
        },
    ]


def write_report(inventory: list[dict[str, Any]], long_count: int, wide_count: int) -> None:
    lines = [
        "# 시군구 ML 재개용 신규 Feature 데이터셋 확보",
        "",
        "## 목적",
        "",
        "시군구 ML 보정은 기존 feature만으로 oracle 상한이 낮았으므로, 모델 변경 전에 시군구×산업 생산활동을 더 직접적으로 설명하는 변수를 확보했다.",
        "",
        "## 산출물",
        "",
        "| 파일 | 내용 |",
        "| --- | --- |",
        "| `data/processed/business_sido_industry_all.csv` | 시도×산업 사업체수·종사자수·매출액 전체 산업 확장 |",
        "| `data/processed/business_size_sido_industry.csv` | 시도×산업×종사자규모 사업체수·종사자수 |",
        "| `data/processed/municipality_feature_mart_long.csv` | source/지역/산업/연도/지표 단위 long feature mart |",
        "| `data/processed/municipality_feature_mart_wide.csv` | 모델링 결합용 wide feature mart |",
        "| `data/processed/municipality_direct_feature_inventory.csv` | source별 coverage와 공표지연 정책 요약 |",
        "",
        f"- long mart rows: {long_count:,}",
        f"- wide mart rows: {wide_count:,}",
        "",
        "## 확보 Source 요약",
        "",
        "| Source | 행 수 | 기간 | 지역 레벨 | 산업 레벨 | 지표 |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for row in inventory:
        lines.append(
            "| {source_dataset} | {rows} | {years} | {area_levels} | {industry_levels} | {metrics} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## 공표지연 및 데이터 유출 방지",
            "",
            "연간 구조통계는 목표연도 초에 같은 해 값이 공개되어 있다고 볼 수 없다. 현재 mart에는 보수적으로 `first_eligible_target_year = source_year + 2`를 부여했다.",
            "",
            "예를 들어 2024년을 2024년 1월 1일 기준으로 예측하는 backtest에서는 2022년 이하 구조변수만 사용할 수 있다.",
            "",
            "## 해석",
            "",
            "- 시군구에 직접 붙는 강한 신규 feature는 광업·제조업 주요지표와 2015년 경제총조사 읍면동 proxy다.",
            "- 전국사업체조사 계열은 현재 시도 단위라 시군구 직접 signal은 아니지만, 부모 시도 산업구조와 규모별 분포를 설명하는 보조 feature로 사용할 수 있다.",
            "- 서비스업·도소매·건설·전기가스의 시군구 직접 변수는 아직 제한적이므로, 다음 단계에서는 공장등록, 건축허가, 전력판매량, 산업단지 자료 같은 외부 행정자료 연결이 필요하다.",
            "",
            "## 추가 탐색 후보",
            "",
            "`municipality_feature_source_candidates.csv`에는 아직 확보하지 못했지만 ML 재개 조건을 만족시키기 위해 우선 탐색해야 할 후보를 정리했다.",
            "",
            "| 우선순위 | 후보 | 대상 산업 | 희망 지역 레벨 | 이유 |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for row in feature_source_candidates():
        lines.append(
            f"| {row['priority']} | {row['candidate']} | {row['target_sectors']} | {row['desired_area_level']} | {row['reason']} |"
        )
    (Path("reports") / "municipality_new_feature_dataset.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    api_key = get_kosis_key()
    structural_rows, structural_failures = collect_structural_business(api_key)
    size_rows, size_failures = collect_business_size(api_key)
    long_rows, wide_rows = build_feature_mart()
    failures = structural_failures + size_failures
    inventory = source_inventory(long_rows, failures)
    write_csv(PROCESSED_DIR / "municipality_direct_feature_inventory.csv", inventory)
    write_csv(PROCESSED_DIR / "municipality_feature_source_candidates.csv", feature_source_candidates())
    write_csv(
        PROCESSED_DIR / "municipality_feature_collection_summary.csv",
        [
            {"dataset": "business_sido_industry_all", "rows": len(structural_rows), "failures": len(structural_failures)},
            {"dataset": "business_size_sido_industry", "rows": len(size_rows), "failures": len(size_failures)},
            {"dataset": "municipality_feature_mart_long", "rows": len(long_rows), "failures": 0},
            {"dataset": "municipality_feature_mart_wide", "rows": len(wide_rows), "failures": 0},
        ],
    )
    write_report(inventory, len(long_rows), len(wide_rows))
    print(f"structural rows: {len(structural_rows)} failures: {len(structural_failures)}")
    print(f"size rows: {len(size_rows)} failures: {len(size_failures)}")
    print(f"feature mart long rows: {len(long_rows)}")
    print(f"feature mart wide rows: {len(wide_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
