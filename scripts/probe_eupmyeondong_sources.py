from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from kosis_common import RAW_DIR, write_csv


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "eupmyeondong_data_sources.md"


KOSIS_CANDIDATES = [
    ("101", "DT_1KI2003", "전국 경제총조사 2010 읍면동×산업대분류 총괄"),
    ("101", "DT_1KI1511_10", "전국 경제총조사 2015 읍면동×산업대분류 총괄"),
    ("101", "DT_1K52F08", "전국사업체조사 2020년 이후 시도×산업 총괄"),
]

SEOUL_API = "https://stat.eseoul.go.kr/stat/sip/sts/map/getChartDataList.do"
SEOUL_PAGE = "https://stat.eseoul.go.kr/stat/sip/sts/map/statsMap.do"


def metadata(org_id: str, tbl_id: str) -> dict[str, Any] | None:
    path = RAW_DIR / f"kosis_{org_id}_{tbl_id}_metadata.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    alt = RAW_DIR / f"kosis_{tbl_id}_metadata.json"
    if alt.exists():
        return json.loads(alt.read_text(encoding="utf-8"))
    return None


def dimension_summary(info: dict[str, Any] | None) -> str:
    if not info:
        return "metadata not cached"
    dims = []
    item_count = (info.get("itemInfo") or {}).get("itmCnt")
    dims.append(f"항목 {item_count}개")
    for class_info in info.get("classInfoList", []):
        dims.append(
            f"{class_info.get('classNm')} {class_info.get('itmCnt')}개(level {class_info.get('depthLvl')})"
        )
    return "; ".join(dims)


def fetch_seoul_probe() -> dict[str, Any]:
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
            "statsMapId=1&curOrgId=201&prdDe=2024&searchPrdDe=2024",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(completed.stdout)
    charts = []
    for item in data.get("mapChartList", []):
        chart_data = item.get("mapChartData", {})
        charts.append(
            {
                "map_chart_id": item.get("mapChartId"),
                "name": item.get("mapChartNm"),
                "tbl_id": item.get("tblId"),
                "rows": len(chart_data.get("dataList", [])),
                "items": ", ".join(c.get("cndtnNm", "") for c in chart_data.get("chcList", [])[:6]),
            }
        )
    return {"charts": charts}


def main() -> int:
    rows = []
    for org_id, tbl_id, note in KOSIS_CANDIDATES:
        info = metadata(org_id, tbl_id)
        rows.append(
            {
                "source": "KOSIS",
                "org_id": org_id,
                "table_id": tbl_id,
                "name": info.get("tblNm") if info else note,
                "period": info.get("containPeriod") if info else "",
                "dimensions": dimension_summary(info),
                "assessment": note,
            }
        )

    seoul = fetch_seoul_probe()
    for chart in seoul["charts"]:
        rows.append(
            {
                "source": "서울시 한눈에 보는 사업체",
                "org_id": "201",
                "table_id": chart["tbl_id"],
                "name": chart["name"],
                "period": "2015-2024 page option observed",
                "dimensions": f"행정동/자치구 지도 rows {chart['rows']}; items {chart['items']}",
                "assessment": "서울 최신 행정동 사업체수·종사자수 프록시 후보",
            }
        )

    write_csv(ROOT / "data" / "processed" / "eupmyeondong_source_inventory.csv", rows)

    lines = [
        "# 읍면동 자료 탐색 결과",
        "",
        "## 결론",
        "",
        "읍면동 단위의 공식 GVA는 확인되지 않았다. 다만 읍면동 또는 행정동 단위 사업체수·종사자수·매출액을 공간 배분 프록시로 쓰는 경로는 존재한다.",
        "",
        "전국 공통 자료는 KOSIS 경제총조사 2010·2015년 테이블에서 확인된다. 최신 연속 자료는 서울시가 별도 통계지도 형태로 2015-2024년 행정동 사업체수·종사자수 자료를 제공한다.",
        "",
        "## 확인된 자료",
        "",
        "| 출처 | 테이블 | 기간 | 해상도/항목 | 판단 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['source']} | `{row['table_id']}` {row['name']} | {row['period']} | {row['dimensions']} | {row['assessment']} |"
        )
    lines.extend(
        [
            "",
            "## 모델링 사용 방식",
            "",
            "1. 시군구 분기 GVA를 먼저 추정한다.",
            "2. 읍면동 사업체수·종사자수·매출액을 업종별 공간 가중치로 변환한다.",
            "3. 업종별로 적절한 가중치를 선택한다. 예를 들어 서비스업은 종사자수와 사업체수를, 제조업은 제조업 사업체/종사자 및 가능하면 부가가치 프록시를 우선한다.",
            "4. 읍면동 추정값은 시군구 합계가 반드시 시군구 추정값과 일치하도록 raking 또는 constrained allocation으로 보정한다.",
            "",
            "## 한계",
            "",
            "- 전국 공통 읍면동 자료는 경제총조사 2015년 이후 최신 연속 테이블이 KOSIS에서 바로 확인되지 않았다.",
            "- 서울은 최신 행정동 자료가 있지만, 동일 형식이 모든 시도에서 공통 제공되는지는 추가 지자체별 포털 확인이 필요하다.",
            "- 읍면동 결과는 직접 관측 GVA가 아니라 프록시 기반 하향 배분값으로 표시해야 한다.",
            "",
            "## 주요 URL",
            "",
            f"- KOSIS 통계표 메타데이터: `DT_1KI2003`, `DT_1KI1511_10`",
            f"- 서울시 한눈에 보는 사업체: {SEOUL_PAGE}",
            f"- 서울시 내부 데이터 API 확인 endpoint: {SEOUL_API}",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("eupmyeondong source inventory written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
