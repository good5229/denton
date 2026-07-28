#!/usr/bin/env python3
"""Phase223: insurance and broadcast API probe report.

This phase records two newly identified residual-source candidates:

* life-insurance join status API: callable, but only sido-level and missing 2023;
* broadcasting industry survey API: most direct for J60, but current key returns
  403 Forbidden.

It does not change the GVA registry because neither source is currently safe for
city-level 2023 precision refinement.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase223_insurance_broadcast_probe"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase223_insurance_broadcast_probe.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


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
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    life_path = ROOT / "data/processed/phase223_insurance_api_probe/life_insurance_join_status_pages.csv"
    life = pd.read_csv(life_path, low_memory=False) if life_path.exists() else pd.DataFrame()
    if life.empty:
        life_summary = pd.DataFrame()
        life_year_area = pd.DataFrame()
    else:
        life["joinCnt_num"] = pd.to_numeric(life["joinCnt"], errors="coerce").fillna(0)
        life_summary = pd.DataFrame(
            [
                {
                    "자료": "생명보험 가입현황",
                    "행수": int(len(life)),
                    "연도": ", ".join(map(str, sorted(life["sttsAccmlTrgtYr"].dropna().astype(str).unique()))),
                    "지역수준": "시도",
                    "지역수": int(life["areaNm"].nunique()),
                    "2023포함": "Y" if "2023" in set(life["sttsAccmlTrgtYr"].astype(str)) else "N",
                    "포항직접행": "N",
                    "K66채택": "N",
                    "배제사유": "시군구가 아니라 시도 단위이고 2023년 행이 없음",
                }
            ]
        )
        life_year_area = (
            life.groupby(["sttsAccmlTrgtYr", "areaNm"], dropna=False)["joinCnt_num"]
            .sum()
            .reset_index()
            .rename(columns={"sttsAccmlTrgtYr": "연도", "areaNm": "시도", "joinCnt_num": "가입건수"})
        )
        life_year_area = life_year_area[life_year_area["시도"].isin(["경기", "경북"])].sort_values(["시도", "연도"])

    blocked = pd.DataFrame(
        [
            {
                "자료": "방송산업 실태조사 정보",
                "링크": "https://www.data.go.kr/data/15108104/openapi.do?recommendDataYn=Y",
                "대상": "고양 J60 방송업, 포항 J60 방송업",
                "현재상태": "현재 공공데이터포털 키 호출 시 403 Forbidden",
                "필요조치": "활용신청/승인 후 재호출",
                "채택가능성": "승인 후 매출·종사자·지역 필드가 있으면 최우선 후보",
            },
            {
                "자료": "일반손해보험 가입정보",
                "링크": "금융위원회 보험가입정보 계열 API",
                "대상": "포항 K66 금융 및 보험 관련 서비스업",
                "현재상태": "현재 키 호출 시 403 Forbidden",
                "필요조치": "활용신청/권한 확인",
                "채택가능성": "시군구 또는 최소 영업점 소재지와 보험료/계약금액이 있을 때만 가능",
            },
        ]
    )

    strict = pd.DataFrame(
        [
            {"검사": "생명보험 API 수집행", "값": int(len(life)), "판정": "행 있음"},
            {"검사": "생명보험 2023년 행 존재", "값": int((life.get("sttsAccmlTrgtYr", pd.Series(dtype=str)).astype(str).eq("2023")).sum()) if not life.empty else 0, "판정": "0이면 2023 정밀화 불가"},
            {"검사": "생명보험 지역수준", "값": "시도", "판정": "시군구 직접 개선 불가"},
            {"검사": "방송 API 현재 호출", "값": "403 Forbidden", "판정": "승인 필요"},
        ]
    )

    life_summary.to_csv(OUT / "phase223_life_insurance_resolution_summary.csv", index=False, encoding="utf-8-sig")
    life_year_area.to_csv(OUT / "phase223_life_insurance_gyeonggi_gyeongbuk_year_area.csv", index=False, encoding="utf-8-sig")
    blocked.to_csv(OUT / "phase223_blocked_high_priority_api.csv", index=False, encoding="utf-8-sig")
    strict.to_csv(OUT / "phase223_strict_audit.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "git_hash": git_hash(),
                "inputs": [
                    "data/processed/phase223_insurance_api_probe/life_insurance_join_status_pages.csv",
                    "manual probe: broadcasting industry survey API returned 403",
                ],
                "outputs": [
                    "phase223_life_insurance_resolution_summary.csv",
                    "phase223_life_insurance_gyeonggi_gyeongbuk_year_area.csv",
                    "phase223_blocked_high_priority_api.csv",
                    "phase223_strict_audit.csv",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    REPORT.write_text(
        f"""# Phase223 보험·방송 API 잔여오차 적용성 검증

생성시각: {CREATED_AT}

## 목적

포항 K66과 고양·포항 J60 잔여 정밀오차를 줄이기 위해 보험가입정보와 방송산업 실태조사 API를 추가 점검했다.

## 생명보험 가입현황 API

{md_table(life_summary, 2)}

### 경기·경북 연도별 가입건수

{md_table(life_year_area, 0)}

## 차단 또는 추가승인 필요 API

{md_table(blocked, 2)}

## 엄격검증

{md_table(strict, 0)}

## 결론

1. 생명보험 가입현황 API는 호출 가능하지만 시도 단위이며 2023년 행이 없어 포항 K66의 2023 정밀화에는 직접 사용할 수 없다.
2. 방송산업 실태조사 API는 J60에 가장 직접적인 후보이나 현재 키로는 403이다.
3. 일반손해보험 가입정보 계열은 K66에 더 직접적일 가능성이 있지만 현재 키로는 403이다.
4. 따라서 Phase223에서도 신규 채택 후보는 없으며, 다음 실제 개선은 방송산업 실태조사와 손해보험/보험료 계열 API 승인 후 가능하다.
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
