from __future__ import annotations

import html
import json
import re
import ssl
import urllib.parse
import urllib.request
from typing import Any

from kosis_common import PROCESSED_DIR, get_kosis_key, kosis_data, normalize_kosis_rows, parse_number, write_csv, write_json


ORG_ID = "201"
TBL_ID = "DT_201012_D040028"
START_YEAR = "2010"
END_YEAR = "2023"
STAT_HTML_HOSTS = (
    "https://stat.eseoul.go.kr/statHtml/statHtmlContent.do",
    "https://kosis.kr/statHtml/statHtmlContent.do",
)


def fetch_text(url: str, params: dict[str, str]) -> str:
    query = urllib.parse.urlencode(params)
    context = ssl.create_default_context()
    with urllib.request.urlopen(f"{url}?{query}", timeout=60, context=context) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_metadata() -> dict[str, Any]:
    params = {"orgId": ORG_ID, "tblId": TBL_ID, "conn_path": "I2"}
    last_error: Exception | None = None
    for host in STAT_HTML_HOSTS:
        try:
            text = fetch_text(host, params)
            match = re.search(r"var\s+g_jsonStatInfo\s*=\s*['\"](.+?)['\"];", text, re.S)
            if not match:
                raise RuntimeError("g_jsonStatInfo not found")
            info = json.loads(html.unescape(match.group(1)))
            write_json(PROCESSED_DIR.parent / "raw" / f"kosis_{ORG_ID}_{TBL_ID}_metadata.json", info)
            return info
        except Exception as exc:  # pragma: no cover - network/source variability
            last_error = exc
    raise RuntimeError(f"could not fetch Seoul metadata: {last_error}")


def score_item(name: str) -> int:
    normalized = name.replace(" ", "")
    score = 0
    if "지역내총부가가치" in normalized:
        score += 10
    if "지역내총생산" in normalized:
        score += 8
    if "총부가가치" in normalized:
        score += 6
    if any(token in normalized for token in ("실질", "연쇄가격", "기준년")):
        score += 5
    if "명목" in normalized or "당해년" in normalized:
        score -= 4
    return score


def selected_item_id(info: dict[str, Any]) -> str:
    candidates: list[tuple[int, str]] = []
    for item in (info.get("itemInfo") or {}).get("itmList", []):
        item_id = str(item.get("itmId") or "")
        name = str(item.get("scrKor") or "")
        if item_id:
            candidates.append((score_item(name), item_id))
    if not candidates:
        raise RuntimeError("metadata has no item candidates")
    candidates.sort(reverse=True)
    return candidates[0][1]


def object_selection(info: dict[str, Any]) -> dict[int, str]:
    obj: dict[int, str] = {}
    for idx, class_info in enumerate(info.get("classInfoList", []), start=1):
        class_name = str(class_info.get("classNm") or "")
        if any(token in class_name for token in ("자치구", "구별", "행정구역", "시군구")):
            obj[idx] = "ALL"
        else:
            obj[idx] = "ALL"
    return obj


def district_fields(row: dict[str, Any]) -> tuple[str, str]:
    for idx in range(1, 9):
        name = str(row.get(f"c{idx}_nm") or "")
        code = str(row.get(f"c{idx}_id") or "")
        if name and (name.endswith("구") or name == "서울특별시"):
            return code, name
    for idx in range(1, 9):
        code = str(row.get(f"c{idx}_id") or "")
        name = str(row.get(f"c{idx}_nm") or "")
        if code or name:
            return code, name
    return "", ""


def main() -> int:
    info = fetch_metadata()
    api_key = get_kosis_key()
    rows = kosis_data(
        api_key=api_key,
        org_id=ORG_ID,
        tbl_id=TBL_ID,
        item_id=selected_item_id(info),
        period="Y",
        start=START_YEAR,
        end=END_YEAR,
        obj=object_selection(info),
    )
    normalized = []
    for row in normalize_kosis_rows(rows, "seoul_district_grdp_annual"):
        code, name = district_fields(row)
        value = parse_number(row.get("value"))
        normalized.append(
            {
                **row,
                "year": row.get("prd_de"),
                "sigungu_code": code,
                "sigungu_name": name,
                "value": "" if value is None else value,
                "source_url": "https://stat.eseoul.go.kr/statHtml/statHtml.do?orgId=201&tblId=DT_201012_D040028&conn_path=I2",
            }
        )
    write_csv(PROCESSED_DIR / "seoul_district_grdp_annual.csv", normalized)
    print(f"wrote {len(normalized)} rows to data/processed/seoul_district_grdp_annual.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
