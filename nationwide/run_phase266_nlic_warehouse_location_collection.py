#!/usr/bin/env python3
"""Phase266 National Logistics Information Center warehouse location XLS parser.

The source is the National Logistics Information Center statistics download
endpoint exposed from the official public-data file page for "물류창고업 등록현황".

It is useful as a province-level *flow* signal for H52 창고업 / transport-
warehouse diagnostics.  It is not a GVA actual, and it has no sigungu spatial
resolution in the downloaded table.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase266_nlic_warehouse_location"
OUT = ROOT / "data" / "processed" / "phase266_nlic_warehouse_location"
NOUT = ROOT / "nationwide" / "outputs"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase266_nlic_warehouse_location_collection.md"
META = ROOT / "nationwide" / "nlic_warehouse_location_source_metadata.md"

YEARS = list(range(2015, 2026))
DOWNLOAD_URL_TEMPLATE = (
    "https://www.nlic.go.kr/nlic/WhsStatsWarehouseLocation.action?"
    "command=DWLOAD&S_D_FROM={year}&S_D_TO={year}"
)

CATEGORY_COLUMNS = {
    1: ("합계", "전체 등록건수"),
    2: ("물류시설의 개발 및 운영에 관한 법률", "물시법창고"),
    3: ("물류시설의 개발 및 운영에 관한 법률", "항만창고"),
    4: ("관세법", "보세창고"),
    5: ("화학물질관리법", "보관저장업"),
    6: ("식품위생법", "냉동냉장"),
    7: ("축산물위생관리법", "축산물보관"),
    8: ("수산식품산업의 육성 및 지원에 관한 법률", "냉동냉장"),
}

PROVINCE_RENAME = {
    "강원도": "강원특별자치도",
    "전라북도": "전북특별자치도",
}
EXPECTED_PROVINCES = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]


def md_table(df: pd.DataFrame, max_rows: int | None = None, digits: int = 3) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_해당 없음_"
    x = df.copy()
    for c in x.columns:
        if str(c).lower() in {"year", "count_2015", "count_2020", "count_2025"}:
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else str(int(v)))
        elif pd.api.types.is_float_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{v:,.{digits}f}")
        elif pd.api.types.is_integer_dtype(x[c]):
            x[c] = x[c].map(lambda v: "" if pd.isna(v) else f"{int(v):,}")
        else:
            x[c] = x[c].fillna("").astype(str)
    lines = [
        "| " + " | ".join(x.columns) + " |",
        "| " + " | ".join(["---"] * len(x.columns)) + " |",
    ]
    for _, r in x.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in x.columns) + " |")
    return "\n".join(lines)


def parse_one(path: Path, year: int) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    rows: list[dict[str, object]] = []
    present: set[str] = set()
    for i in range(3, len(raw)):
        province = str(raw.iloc[i, 0]).strip()
        if not province or province == "nan" or province == "합계":
            continue
        province = PROVINCE_RENAME.get(province, province)
        present.add(province)
        for col, (law, warehouse_category) in CATEGORY_COLUMNS.items():
            value = pd.to_numeric(raw.iloc[i, col], errors="coerce")
            if pd.isna(value):
                continue
            rows.append(
                {
                    "year": year,
                    "province_full": province,
                    "warehouse_law": law,
                    "warehouse_category": warehouse_category,
                    "category_key": f"{law} / {warehouse_category}",
                    "registered_count": int(value),
                    "source_row_present": True,
                    "source_file": path.name,
                    "source_url": DOWNLOAD_URL_TEMPLATE.format(year=year),
                }
            )
    for province in EXPECTED_PROVINCES:
        if province in present:
            continue
        for _col, (law, warehouse_category) in CATEGORY_COLUMNS.items():
            rows.append(
                {
                    "year": year,
                    "province_full": province,
                    "warehouse_law": law,
                    "warehouse_category": warehouse_category,
                    "category_key": f"{law} / {warehouse_category}",
                    "registered_count": 0,
                    "source_row_present": False,
                    "source_file": path.name,
                    "source_url": DOWNLOAD_URL_TEMPLATE.format(year=year),
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    NOUT.mkdir(parents=True, exist_ok=True)

    missing = [y for y in YEARS if not (RAW / f"nlic_warehouse_location_{y}.xls").exists()]
    if missing:
        raise FileNotFoundError(f"missing NLIC XLS files: {missing}")

    frames = [parse_one(RAW / f"nlic_warehouse_location_{y}.xls", y) for y in YEARS]
    long = pd.concat(frames, ignore_index=True)
    pivot = (
        long.pivot_table(
            index=["year", "province_full"],
            columns=["category_key"],
            values="registered_count",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    total_col = "합계 / 전체 등록건수"
    if total_col in pivot.columns:
        detail_cols = [c for c in pivot.columns if c not in {"year", "province_full", total_col}]
        pivot["detail_sum_count"] = pivot[detail_cols].sum(axis=1)
        pivot["total_minus_detail_count"] = pivot[total_col] - pivot["detail_sum_count"]

    total_rows = long[long["category_key"].eq("합계 / 전체 등록건수")].copy()
    coverage = (
        total_rows.groupby(["year"], as_index=False)
        .agg(
            province_count=("province_full", "nunique"),
            source_row_province_count=("source_row_present", lambda s: int(s.sum())),
            source_row_missing_province_count=("source_row_present", lambda s: int((~s).sum())),
            total_registered_count=("registered_count", "sum"),
        )
        .sort_values("year")
    )
    coverage["category_count"] = long.groupby("year")["category_key"].nunique().reindex(coverage["year"]).to_numpy()
    coverage = coverage[
        [
            "year",
            "province_count",
            "source_row_province_count",
            "source_row_missing_province_count",
            "category_count",
            "total_registered_count",
        ]
    ]
    latest = (
        long[long["category_key"].eq("합계 / 전체 등록건수")]
        .pivot(index="province_full", columns="year", values="registered_count")
        .reset_index()
    )
    latest["change_2015_2025_count"] = latest[2025] - latest[2015]
    latest["change_2015_2025_pct"] = latest["change_2015_2025_count"] / latest[2015].replace(0, pd.NA) * 100
    top_change = latest.sort_values("change_2015_2025_count", ascending=False)[
        ["province_full", 2015, 2020, 2025, "change_2015_2025_count", "change_2015_2025_pct"]
    ]
    top_change = top_change.rename(columns={2015: "count_2015", 2020: "count_2020", 2025: "count_2025"})

    long_path = OUT / "nlic_warehouse_location_2015_2025_long.csv"
    pivot_path = OUT / "nlic_warehouse_location_2015_2025_province_wide.csv"
    coverage_path = NOUT / "phase266_nlic_warehouse_location_coverage.csv"
    top_change_path = NOUT / "phase266_nlic_warehouse_location_top_change.csv"
    long.to_csv(long_path, index=False, encoding="utf-8-sig")
    pivot.to_csv(pivot_path, index=False, encoding="utf-8-sig")
    coverage.to_csv(coverage_path, index=False, encoding="utf-8-sig")
    top_change.to_csv(top_change_path, index=False, encoding="utf-8-sig")

    created_at = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
    meta = f"""# 국가물류통합정보센터 물류창고업 등록현황 source metadata

생성시각: {created_at}

## 원천

| 항목 | 내용 |
| --- | --- |
| 자료명 | 지역별 물류창고업 등록현황 |
| 공식 연결 | 공공데이터포털 fileData `15083282`, 국가물류통합정보센터 통계 다운로드 |
| 다운로드 URL | `{DOWNLOAD_URL_TEMPLATE}` |
| 로컬 원본 | `data/raw/phase266_nlic_warehouse_location/nlic_warehouse_location_YYYY.xls` |
| 수집기간 | 2015~2025 |
| 지역 해상도 | 시도 |
| 시간 해상도 | 연간 |
| 측정값 | 등록건수 flow/stock 성격의 행정 등록 현황 |
| 사용 가능 역할 | H52 창고업 또는 운수 및 창고업 시도 단위 보조 신호 후보 |
| 금지 해석 | GVA actual 아님, 시군구 공간배분 근거 아님, route 채택 근거 아님 |

## 공표·운영 메모

- 다운로드 endpoint는 별도 API key 없이 XLS attachment를 반환한다.
- 파일명은 다운로드일을 포함하므로 재수집 시 파일명은 달라질 수 있다.
- 일부 연도는 원본 표에서 등록건수 0으로 보이는 시도 행이 생략된다. 파싱 산출물은 17개 시도 패널 유지를 위해 생략 시도를 0으로 채우고 `source_row_present=False`로 표시한다.
- 자료는 시도별 등록건수이므로 Q+1개월 속보성 또는 월별 직접지표로 쓰지 않는다.
- 향후 H52 창고업 시도 검증, 항만 물동량·사업체·전력 등과 결합한 보조 gate에서만 후보로 사용한다.
"""
    META.write_text(meta, encoding="utf-8")

    report = f"""# Phase266 국가물류통합정보센터 물류창고업 등록현황 수집

생성시각: {created_at}

## 결론

2015~2025년 국가물류통합정보센터 `지역별 물류창고업 등록현황` XLS 11개를 수집·파싱했다. 이 자료는 `운수 및 창고업` 중 창고업 관련 시도 단위 보조 신호로는 유용하지만, GVA actual이나 시군구 공간배분 자료는 아니다.

## 1. Coverage

{md_table(coverage, digits=0)}

## 2. 2015~2025 변화 상위

{md_table(top_change.head(12), digits=2)}

## 3. 산출물

| 산출물 | 역할 | git 처리 |
| --- | --- | --- |
| `data/raw/phase266_nlic_warehouse_location/nlic_warehouse_location_YYYY.xls` | 연도별 원본 XLS | `data/` ignore |
| `data/processed/phase266_nlic_warehouse_location/nlic_warehouse_location_2015_2025_long.csv` | province×year×법령×창고구분 long table | `data/`·`*.csv` ignore |
| `data/processed/phase266_nlic_warehouse_location/nlic_warehouse_location_2015_2025_province_wide.csv` | 시도×연도 wide table | `data/`·`*.csv` ignore |
| `nationwide/outputs/phase266_nlic_warehouse_location_coverage.csv` | coverage 감사 | `nationwide/outputs/*.csv` ignore |
| `nationwide/outputs/phase266_nlic_warehouse_location_top_change.csv` | 변화 상위 감사 | `nationwide/outputs/*.csv` ignore |
| `nationwide/nlic_warehouse_location_source_metadata.md` | 출처·공표주기·금지해석 | tracked |

## 4. 적용 판정

| 항목 | 판정 |
| --- | --- |
| H52 창고업 시도 단위 보조 신호 | 후보 |
| 운수 및 창고업 전체 GVA actual | 아님 |
| 시군구 공간배분 근거 | 아님 |
| 월별·분기별 속보 지표 | 아님 |
| 운영 route 채택 | 미채택 |

다음 실험에서 쓰려면 `항만 물동량`, `전력`, `사업체`, `상위 시도 운수·창고업 actual`과 함께 rolling out-of-year gate를 통과해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(coverage.to_string(index=False))
    print(top_change.head(12).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
