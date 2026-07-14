from __future__ import annotations

import json
import html
import re
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, get_kosis_key, normalize_kosis_rows, write_csv, write_json


DATA_API = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
METADATA_API = "https://kosis.kr/statHtml/statHtmlContent.do"

YEARS = ("2019", "2020", "2021", "2022", "2023")
MANUFACTURING_YEARS = ("2020", "2021", "2022", "2023", "2024")

SIGUNGU_GVA_TABLES = [
    ("201", "DT_201012_D040031", "서울특별시"),
    ("202", "DT_F10108", "부산광역시"),
    ("203", "DT_2020Y22GRDP2", "대구광역시"),
    ("204", "DT_2020Y23GRDP2", "인천광역시"),
    ("205", "DT_2020Y24GRDP2", "광주광역시"),
    ("206", "DT_2020Y25GRDP2", "대전광역시"),
    ("207", "DT_GRDP_2020_02", "울산광역시"),
    ("210", "DT_GRDP008_2020", "경기도"),
    ("211", "DT_2020Y32GRDP2", "강원특별자치도"),
    ("212", "DT_2020Y33GRDP2", "충청북도"),
    ("213", "DT_2020Y34GRDP2", "충청남도"),
    ("214", "DT_2020Y35GRDP2", "전북특별자치도"),
    ("215", "DT_2020Y36GRDP2", "전라남도"),
    ("216", "DT_GRDP202037_02", "경상북도"),
    ("217", "DT_2020Y38GRDP2", "경상남도"),
    ("218", "DT_2020GRDP39_02", "제주특별자치도"),
]


def request_json(params: dict[str, str]) -> Any:
    try:
        completed = subprocess.run(
            [
                "curl",
                "-sS",
                "--connect-timeout",
                "10",
                "--max-time",
                "60",
                "--retry",
                "2",
                "--retry-delay",
                "1",
                f"{DATA_API}?{urllib.parse.urlencode(params)}",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        safe = {key: value for key, value in params.items() if key != "apiKey"}
        raise RuntimeError(f"curl failed for {DATA_API}?{urllib.parse.urlencode(safe)}") from exc
    data = json.loads(completed.stdout)
    if isinstance(data, dict) and data.get("err"):
        raise RuntimeError(f"KOSIS error {data.get('err')}: {data.get('errMsg')}")
    return data


def fetch_metadata(org_id: str, tbl_id: str) -> dict[str, Any]:
    path = RAW_DIR / f"kosis_{org_id}_{tbl_id}_metadata.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    params = urllib.parse.urlencode({"orgId": org_id, "tblId": tbl_id, "conn_path": "C1"})
    try:
        completed = subprocess.run(
            [
                "curl",
                "-L",
                "-sS",
                "--connect-timeout",
                "10",
                "--max-time",
                "60",
                "--retry",
                "2",
                "--retry-delay",
                "1",
                f"{METADATA_API}?{params}",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"curl failed for {METADATA_API}?{params}") from exc
    text = completed.stdout
    (RAW_DIR / f"kosis_{org_id}_{tbl_id}_statHtmlContent.html").write_text(text, encoding="utf-8")
    match = re.search(r"var\s+g_jsonStatInfo\s*=\s*'(.+?)';", text, re.S)
    if not match:
        raise RuntimeError("g_jsonStatInfo not found")
    info = json.loads(html.unescape(match.group(1)))
    write_json(path, info)
    return info


def years_available(info: dict[str, Any], desired: tuple[str, ...]) -> tuple[str, str] | None:
    years = set(info.get("periodInfo", {}).get("listY") or [])
    selected = [year for year in desired if year in years]
    if not selected:
        return None
    return selected[0], selected[-1]


def real_gva_item_id(info: dict[str, Any]) -> str | None:
    scored: list[tuple[int, str]] = []
    for item in (info.get("itemInfo") or {}).get("itmList", []):
        name = str(item.get("scrKor") or "")
        if "부가가치" not in name:
            continue
        score = 0
        if "지역내" in name:
            score += 3
        if any(token in name for token in ("연쇄가격", "실질", "기준년")):
            score += 5
        if "명목" in name:
            score -= 4
        scored.append((score, str(item.get("itmId"))))
    if scored:
        scored.sort(reverse=True)
        return scored[0][1]
    items = (info.get("itemInfo") or {}).get("itmList", [])
    if len(items) == 1:
        return str(items[0].get("itmId"))
    return None


def object_selection(info: dict[str, Any]) -> dict[int, str]:
    obj: dict[int, str] = {}
    for idx, class_info in enumerate(info.get("classInfoList", []), start=1):
        class_name = str(class_info.get("classNm") or "")
        selected = "ALL"
        if "항목" in class_name:
            for item in class_info.get("itmList", []):
                name = str(item.get("scrKor") or "")
                if "실질" in name and item.get("leaf") == 1:
                    selected = str(item.get("itmId"))
                    break
        obj[idx] = selected
    return obj


def filter_real_gva_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    item_dimension = None
    for idx in range(1, 9):
        if any("항목" in str(row.get(f"C{idx}_OBJ_NM") or "") for row in rows):
            item_dimension = idx
            break
    if item_dimension is None:
        return rows, ""
    code_key = f"C{item_dimension}"
    name_key = f"C{item_dimension}_NM"
    candidates = {
        str(row.get(code_key))
        for row in rows
        if "총부가가치" in str(row.get(name_key) or "").replace(" ", "")
    }
    if len(candidates) <= 1:
        return rows, next(iter(candidates), "")

    def code_score(code: str) -> int:
        digits = "".join(ch for ch in code if ch.isdigit())
        return int(digits) if digits else -1

    selected = max(candidates, key=code_score)
    return [row for row in rows if str(row.get(code_key)) == selected], selected


def get_data(
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
    data = request_json(params)
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected response for {tbl_id}: {data!r}")
    return data


def collect_sigungu_gva(api_key: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}
    specs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for org_id, tbl_id, region in SIGUNGU_GVA_TABLES:
        try:
            info = fetch_metadata(org_id, tbl_id)
            period = years_available(info, YEARS)
            if period is None:
                raise RuntimeError(f"no overlap with requested years {YEARS[0]}-{YEARS[-1]}")
            item_id = real_gva_item_id(info)
            if not item_id:
                raise RuntimeError("could not identify a real gross value-added item")
            obj = object_selection(info)
            rows = get_data(
                api_key,
                org_id=org_id,
                tbl_id=tbl_id,
                item_id=item_id,
                period="Y",
                start=period[0],
                end=period[1],
                obj=obj,
            )
            rows, filtered_item_code = filter_real_gva_rows(rows)
        except Exception as exc:
            failures.append(
                {
                    "source_region": region,
                    "org_id": org_id,
                    "tbl_id": tbl_id,
                    "error": str(exc),
                }
            )
            print(f"sigungu_grva_real {region}: skipped ({exc})")
            continue
        raw[f"{org_id}_{tbl_id}"] = rows
        for row in normalize_kosis_rows(rows, "sigungu_grva_real"):
            row["source_region"] = region
            out.append(row)
        specs.append(
            {
                "source_region": region,
                "org_id": org_id,
                "tbl_id": tbl_id,
                "item_id": item_id,
                "obj": json.dumps(obj, ensure_ascii=False),
                "filtered_item_code": filtered_item_code,
                "start_year": period[0],
                "end_year": period[1],
                "rows": len(rows),
            }
        )
        print(f"sigungu_grva_real {region}: {len(rows)} rows ({period[0]}-{period[1]})")
    write_json(RAW_DIR / "expanded_sigungu_grva_real.json", raw)
    write_csv(PROCESSED_DIR / "expanded_sigungu_grva_real.csv", out)
    write_csv(PROCESSED_DIR / "expanded_sigungu_grva_specs.csv", specs)
    write_csv(PROCESSED_DIR / "expanded_sigungu_grva_failures.csv", failures)
    return out


def collect_manufacturing_code_list(api_key: str) -> list[dict[str, str]]:
    rows = get_data(
        api_key,
        org_id="101",
        tbl_id="DT_1FS1101",
        item_id="T06",
        period="Y",
        start="2024",
        end="2024",
        obj={1: "00", 2: "ALL"},
    )
    codes: list[dict[str, str]] = []
    for row in rows:
        code = str(row.get("C2", ""))
        if not code or code == "0":
            continue
        # KSIC code includes section letter. C10 = 중분류, C101 = 소분류, C1011 = 세분류.
        if len(code) in {3, 4, 5}:
            level = {3: "middle", 4: "small", 5: "class"}[len(code)]
            codes.append(
                {
                    "industry_code": code,
                    "industry_name": row.get("C2_NM", ""),
                    "ksic_level": level,
                }
            )
    write_csv(PROCESSED_DIR / "expanded_manufacturing_ksic_codes.csv", codes)
    return codes


def collect_manufacturing_sigungu(api_key: str, codes: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    raw_dir = RAW_DIR / "expanded_manufacturing_sigungu_by_code"
    raw_dir.mkdir(parents=True, exist_ok=True)
    items = [("T01", "establishments"), ("T02", "employees"), ("T06", "value_added")]
    start, end = MANUFACTURING_YEARS[0], MANUFACTURING_YEARS[-1]
    for idx, code_row in enumerate(codes, start=1):
        code = code_row["industry_code"]
        for item_id, item_label in items:
            raw_path = raw_dir / f"{code}_{item_id}.json"
            try:
                if raw_path.exists():
                    rows = json.loads(raw_path.read_text(encoding="utf-8"))
                else:
                    rows = get_data(
                        api_key,
                        org_id="101",
                        tbl_id="DT_1FS1101",
                        item_id=item_id,
                        period="Y",
                        start=start,
                        end=end,
                        obj={1: "ALL", 2: code},
                    )
            except Exception as exc:
                failures.append(
                    {
                        "industry_code": code,
                        "industry_name": code_row["industry_name"],
                        "item_id": item_id,
                        "metric": item_label,
                        "error": str(exc),
                    }
                )
                continue
            write_json(raw_path, rows)
            for row in normalize_kosis_rows(rows, "manufacturing_sigungu_ksic"):
                row["metric"] = item_label
                row["ksic_level"] = code_row["ksic_level"]
                out.append(row)
            time.sleep(0.03)
        if idx % 25 == 0:
            print(f"manufacturing_sigungu_ksic: {idx}/{len(codes)} codes")
    write_csv(PROCESSED_DIR / "expanded_manufacturing_sigungu_ksic.csv", out)
    write_csv(PROCESSED_DIR / "expanded_manufacturing_sigungu_failures.csv", failures)
    return out


def collect_service_detailed_index(api_key: str) -> list[dict[str, Any]]:
    rows = get_data(
        api_key,
        org_id="101",
        tbl_id="DT_1KC2020",
        item_id="T2",
        period="Q",
        start="201901",
        end="202404",
        obj={1: "ALL"},
    )
    out = normalize_kosis_rows(rows, "national_service_ksic_production_index")
    write_json(RAW_DIR / "expanded_national_service_ksic_production_index.json", rows)
    write_csv(PROCESSED_DIR / "expanded_national_service_ksic_production_index.csv", out)
    print(f"national_service_ksic_production_index: {len(rows)} rows")
    return out


def main() -> int:
    api_key = get_kosis_key()
    gva_rows = collect_sigungu_gva(api_key)
    codes: list[dict[str, str]] = []
    manufacturing_rows: list[dict[str, Any]] = []
    service_rows: list[dict[str, Any]] = []
    try:
        codes = collect_manufacturing_code_list(api_key)
        manufacturing_rows = collect_manufacturing_sigungu(api_key, codes)
    except Exception as exc:
        write_csv(PROCESSED_DIR / "expanded_manufacturing_top_level_failure.csv", [{"error": str(exc)}])
        print(f"manufacturing collection skipped ({exc})")
    try:
        service_rows = collect_service_detailed_index(api_key)
    except Exception as exc:
        write_csv(PROCESSED_DIR / "expanded_service_index_failure.csv", [{"error": str(exc)}])
        print(f"service index collection skipped ({exc})")
    write_csv(
        PROCESSED_DIR / "expanded_collection_summary.csv",
        [
            {"dataset": "expanded_sigungu_grva_real", "rows": len(gva_rows)},
            {"dataset": "expanded_manufacturing_ksic_codes", "rows": len(codes)},
            {"dataset": "expanded_manufacturing_sigungu_ksic", "rows": len(manufacturing_rows)},
            {"dataset": "expanded_national_service_ksic_production_index", "rows": len(service_rows)},
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
