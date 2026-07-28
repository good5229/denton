#!/usr/bin/env python3
"""Phase219: water/sewer accounting source feasibility audit.

Phase218 showed that simple physical activity indicators (treatment volume,
facility capacity, waste recycling volume) do not improve the ERS36/37/38/39
GVA split.  The next plausible source class is accounting/fee/cost data.

This audit records what was found:

* MOIS water/sewer public-enterprise accounting tables have monetary concepts
  but only broad agency classes in the KOSIS API metadata, not Goyang/Pohang
  city rows.
* Gyeonggi water-use/water-fee tables have monetary/use concepts, but split
  only into south/north regional water offices, not Goyang city.
* Gyeongbuk/Pohang water/sewer/waste/environment city tables were collected in
  Phase218 and tested; they did not pass the no-worsening adoption gate.

The phase intentionally does not alter the registry.  It narrows the remaining
data request to city-level accounting/fee/cost/contract data.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase219_water_sewer_accounting_feasibility_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase219_water_sewer_accounting_feasibility_audit.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


MOIS_TABLES = [
    ("110", "DT_110020_A003", "상수도 손익계산서", "매출액·매출원가·영업이익"),
    ("110", "DT_110020_A004", "상수도 업종별 요금현황", "요금수입·조정량"),
    ("110", "DT_110020_A005", "상수도 총괄원가", "급수수익·총괄원가"),
    ("110", "DT_110020_A006", "상수도 사업운영현황", "연간총생산량·시설용량"),
    ("110", "DT_110020_B003", "하수도 손익계산서", "매출액·매출원가·영업손익"),
    ("110", "DT_110020_B004", "하수도 업종별 요금현황", "요금수입·조정량"),
    ("110", "DT_110020_B005", "하수도 총괄원가", "사용료수익·총괄원가"),
    ("110", "DT_110020_B006", "하수도 사업운영현황", "연간총하수처리량·시설용량"),
]

GYEONGGI_TABLES = [
    ("210", "DT_21002G009", "급수사용량", "합계/남부/북부 권역"),
    ("210", "DT_21002G010", "급수사용료 부과", "합계/남부/북부 권역"),
    ("210", "DT_21002G007", "상수도 보급현황", "합계/남부/북부 권역"),
]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def read_meta(org: str, tbl: str) -> dict[str, Any] | None:
    path = RAW / f"kosis_{org}_{tbl}_metadata.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def class_summary(info: dict[str, Any] | None) -> str:
    if not info:
        return "메타데이터 없음"
    parts: list[str] = []
    for cls in info.get("classInfoList", []):
        names = [str(x.get("scrKor") or "") for x in cls.get("itmList", [])[:8]]
        parts.append(f"{cls.get('classNm')}={','.join(names)}")
    return " / ".join(parts)


def has_city_code(info: dict[str, Any] | None, *cities: str) -> bool:
    if not info:
        return False
    text = json.dumps(info, ensure_ascii=False)
    return any(city in text for city in cities)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    mois_rows = []
    for org, tbl, name, concepts in MOIS_TABLES:
        info = read_meta(org, tbl)
        mois_rows.append(
            {
                "기관": org,
                "표ID": tbl,
                "표명": name,
                "금액/운영개념": concepts,
                "분류요약": class_summary(info),
                "고양/포항 직접행": "있음" if has_city_code(info, "고양", "포항") else "없음",
                "판정": "시군구 행 없음: 직접 개선 불가",
            }
        )
    gg_rows = []
    for org, tbl, name, scope in GYEONGGI_TABLES:
        info = read_meta(org, tbl)
        gg_rows.append(
            {
                "기관": org,
                "표ID": tbl,
                "표명": name,
                "분류수준": scope,
                "분류요약": class_summary(info),
                "고양 직접행": "있음" if has_city_code(info, "고양") else "없음",
                "판정": "남부/북부 권역 수준: 고양 직접 개선 불가",
            }
        )
    phase218_summary = pd.read_csv(DATA / "phase218_environment_direct_activity_refinement" / "phase218_city_summary.csv")
    phase218_audit = pd.read_csv(DATA / "phase218_environment_direct_activity_refinement" / "phase218_strict_audit.csv")
    candidate_screen = pd.read_csv(DATA / "phase218_environment_direct_activity_refinement" / "phase218_environment_candidate_screen.csv")
    best_failed = (
        candidate_screen.sort_values(["city", "candidate_block_error_eok"])
        .groupby("city", as_index=False)
        .head(1)
        .copy()
    )
    best_failed = best_failed[
        [
            "city",
            "variant",
            "alpha",
            "base_block_error_eok",
            "candidate_block_error_eok",
            "error_reduction_eok",
            "worsened_cells",
            "source_notes",
        ]
    ].rename(
        columns={
            "city": "지역",
            "variant": "후보",
            "alpha": "혼합강도",
            "base_block_error_eok": "기존묶음오차_억원",
            "candidate_block_error_eok": "후보묶음오차_억원",
            "error_reduction_eok": "감소_억원",
            "worsened_cells": "악화셀",
            "source_notes": "자료구성",
        }
    )

    mois = pd.DataFrame(mois_rows)
    gg = pd.DataFrame(gg_rows)
    mois.to_csv(OUT / "phase219_mois_accounting_feasibility.csv", index=False, encoding="utf-8-sig")
    gg.to_csv(OUT / "phase219_gyeonggi_water_feasibility.csv", index=False, encoding="utf-8-sig")
    best_failed.to_csv(OUT / "phase219_best_failed_environment_candidates.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "created_at": CREATED_AT,
        "git_hash": git_hash(),
        "inputs": [
            "data/raw/kosis_110_DT_110020_A003_metadata.json",
            "data/raw/kosis_110_DT_110020_A004_metadata.json",
            "data/raw/kosis_110_DT_110020_A005_metadata.json",
            "data/raw/kosis_110_DT_110020_A006_metadata.json",
            "data/raw/kosis_110_DT_110020_B003_metadata.json",
            "data/raw/kosis_110_DT_110020_B004_metadata.json",
            "data/raw/kosis_110_DT_110020_B005_metadata.json",
            "data/raw/kosis_110_DT_110020_B006_metadata.json",
            "data/raw/kosis_210_DT_21002G009_metadata.json",
            "data/raw/kosis_210_DT_21002G010_metadata.json",
            "data/raw/kosis_210_DT_21002G007_metadata.json",
            "data/processed/phase218_environment_direct_activity_refinement/phase218_environment_candidate_screen.csv",
        ],
        "outputs": [
            "phase219_mois_accounting_feasibility.csv",
            "phase219_gyeonggi_water_feasibility.csv",
            "phase219_best_failed_environment_candidates.csv",
        ],
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = f"""# Phase219 상하수도 금액형 직접자료 가능성 감사

생성시각: {CREATED_AT}

## 목적

Phase218에서 처리량·시설용량 같은 물량형 지표는 ERS36/37/38/39 GVA 내부비중을 개선하지 못했다.  
이번 단계는 GVA에 더 가까운 금액형 자료인 상수도·하수도 손익, 요금수입, 총괄원가, 사업운영 자료가 고양·포항 시군구 단위로 제공되는지 확인했다.

## 행정안전부 상하수도 회계표

{md_table(mois, 1)}

## 경기도 상수도 시군 후보표

{md_table(gg, 1)}

## Phase218 물량형 후보 재확인

{md_table(phase218_summary, 3)}

{md_table(phase218_audit, 0)}

## 가장 덜 나쁜 물량형 후보

{md_table(best_failed, 2)}

## 판정

1. 행정안전부 상하수도 회계표는 금액 개념이 좋지만, KOSIS API 분류가 `합계/광역시/광역도` 수준이라 고양시·포항시 직접 행이 없다.
2. 경기도 급수사용량·급수사용료 표는 고양시가 아니라 `남부/북부` 권역 수준으로 제공되어 고양시 수도업 GVA 검증에는 직접 사용할 수 없다.
3. 포항시·경상북도 환경/상수도 물량형 자료는 Phase218에서 이미 수집·검증했지만, 내부비중을 악화시켜 채택하지 않았다.
4. 다음에 실제로 필요한 자료는 `시군구별 상수도/하수도 요금수입·총괄원가·운영비·위탁계약액`, 또는 `사업장별 매출/계약액`이다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(mois[["표ID", "표명", "고양/포항 직접행", "판정"]].to_string(index=False))
    print(gg[["표ID", "표명", "고양 직접행", "판정"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
