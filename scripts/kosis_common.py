from __future__ import annotations

import csv
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
CSV_ENCODING = "cp949"

CP949_REPLACEMENTS = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
    }
)


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    env_path = ROOT / ".env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def get_kosis_key() -> str:
    env = load_env()
    for name in ("KOSIS_API_KEY", "KOSIS_KEY", "KOSIS_OPENAPI_KEY", "API_KEY"):
        value = env.get(name)
        if value:
            return value
    raise SystemExit(
        "KOSIS API key not found. Add KOSIS_API_KEY=... to .env and rerun."
    )


def request_json(url: str, params: dict[str, str], timeout: int = 60) -> Any:
    query = urllib.parse.urlencode(params)
    context = None
    try:
        import certifi  # type: ignore

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = None
    with urllib.request.urlopen(f"{url}?{query}", timeout=timeout, context=context) as response:
        body = response.read().decode("utf-8-sig")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}: {body[:500]}") from exc
    if isinstance(data, dict) and data.get("err"):
        raise RuntimeError(f"KOSIS error {data.get('err')}: {data.get('errMsg')}")
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cp949_safe(value: Any) -> Any:
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    text = value.translate(CP949_REPLACEMENTS)
    return text.encode(CSV_ENCODING, errors="replace").decode(CSV_ENCODING)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding=CSV_ENCODING)
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding=CSV_ENCODING, newline="", errors="replace") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: cp949_safe(value) for key, value in row.items()} for row in rows])


def read_csv(path: Path) -> list[dict[str, str]]:
    last_exc: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "utf-8", CSV_ENCODING):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError as exc:
            last_exc = exc
    if last_exc:
        raise last_exc
    return []


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "...", "X"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def extract_stat_info(html_path: Path) -> dict[str, Any]:
    text = html_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"var\s+g_jsonStatInfo\s*=\s*'(.+?)';", text, re.S)
    if not match:
        raise RuntimeError(f"Could not find g_jsonStatInfo in {html_path}")
    raw = unescape(match.group(1))
    return json.loads(raw)


def save_metadata_csv(table_id: str) -> None:
    info = extract_stat_info(RAW_DIR / f"kosis_{table_id}_statHtmlContent.html")
    rows: list[dict[str, Any]] = []
    for class_info in info.get("classInfoList", []):
        for item in class_info.get("itmList", []):
            rows.append(
                {
                    "tbl_id": table_id,
                    "dimension_id": class_info.get("classId"),
                    "dimension_name": class_info.get("classNm"),
                    "code": item.get("itmId"),
                    "name": item.get("scrKor"),
                    "english_name": item.get("scrEng"),
                    "level": item.get("lvl"),
                    "parent_code": item.get("upItmId"),
                    "leaf": item.get("leaf"),
                }
            )
    item_info = info.get("itemInfo", {})
    for item in item_info.get("itmList", []):
        rows.append(
            {
                "tbl_id": table_id,
                "dimension_id": "ITM_ID",
                "dimension_name": item_info.get("itmNm", "항목"),
                "code": item.get("itmId"),
                "name": item.get("scrKor"),
                "english_name": item.get("scrEng"),
                "level": item.get("lvl"),
                "parent_code": item.get("upItmId"),
                "leaf": item.get("leaf"),
            }
        )
    write_json(RAW_DIR / f"kosis_{table_id}_metadata.json", info)
    write_csv(PROCESSED_DIR / f"kosis_{table_id}_metadata.csv", rows)


def normalize_kosis_rows(rows: list[dict[str, Any]], dataset: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        norm = {
            "dataset": dataset,
            "org_id": row.get("ORG_ID"),
            "tbl_id": row.get("TBL_ID"),
            "tbl_nm": row.get("TBL_NM"),
            "prd_se": row.get("PRD_SE"),
            "prd_de": row.get("PRD_DE"),
            "item_id": row.get("ITM_ID"),
            "item_nm": row.get("ITM_NM"),
            "unit_nm": row.get("UNIT_NM"),
            "value": row.get("DT"),
        }
        for idx in range(1, 9):
            code_key = f"C{idx}"
            name_key = f"C{idx}_NM"
            if code_key in row or name_key in row:
                norm[f"c{idx}_id"] = row.get(code_key)
                norm[f"c{idx}_nm"] = row.get(name_key)
        out.append(norm)
    return out


def kosis_data(
    *,
    api_key: str,
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
    data = request_json(
        "https://kosis.kr/openapi/Param/statisticsParameterData.do", params
    )
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected KOSIS response for {tbl_id}: {data!r}")
    return data


def main_metadata(argv: list[str]) -> int:
    for table_id in argv:
        save_metadata_csv(table_id)
        print(f"metadata saved: {table_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_metadata(sys.argv[1:]))
