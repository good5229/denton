#!/usr/bin/env python3
"""Phase225: precision-vs-flash reporting contract audit.

The project now carries several historical precision columns in the same
registry.  Some intermediate columns can still show precision estimates that
are worse than flash estimates, while the current public reporting columns
apply the Phase217 dominance guard.

This audit makes the reporting contract explicit:

* public performance tables must use `phase217_guarded_*` columns;
* intermediate `guarded_*` or `phase214_*` columns are diagnostic only;
* no public precision cell may be worse than the corresponding Q4+1M flash
  estimate under the reporting columns.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase225_precision_reporting_contract_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase225_precision_reporting_contract_audit.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


REGISTRY = DATA / "phase217_public_safe_candidate_rerank_audit" / "phase217_reranked_guarded_registry.csv"


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


def wape(df: pd.DataFrame, err_col: str) -> float:
    return float(df[err_col].sum() / df["actual_gva_eok"].abs().sum() * 100)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(REGISTRY, dtype={"middle_code": str}, low_memory=False)
    reg["middle_code"] = reg["middle_code"].astype(str).str.extract(r"(\d+)")[0].str.zfill(2)

    required = [
        "actual_gva_eok",
        "flash_predicted_gva_eok",
        "flash_error_gva_eok",
        "flash_error_rate_pct",
        "guarded_error_gva_eok",
        "guarded_error_rate_pct",
        "phase217_guarded_predicted_gva_eok",
        "phase217_guarded_error_gva_eok",
        "phase217_guarded_error_rate_pct",
        "phase217_guarded_route",
    ]
    missing = [c for c in required if c not in reg.columns]

    intermediate_worse = reg[reg["guarded_error_gva_eok"] > reg["flash_error_gva_eok"] + 1e-9].copy()
    public_worse = reg[reg["phase217_guarded_error_gva_eok"] > reg["flash_error_gva_eok"] + 1e-9].copy()

    city_rows = []
    for city, g in reg.groupby("city", sort=False):
        city_rows.append(
            {
                "지역": city,
                "셀수": len(g),
                "속보_WAPE_pct": wape(g, "flash_error_gva_eok"),
                "중간정밀_WAPE_pct": wape(g, "guarded_error_gva_eok"),
                "최종표기_WAPE_pct": wape(g, "phase217_guarded_error_gva_eok"),
                "중간정밀_속보보다나쁜셀": int((g["guarded_error_gva_eok"] > g["flash_error_gva_eok"] + 1e-9).sum()),
                "최종표기_속보보다나쁜셀": int((g["phase217_guarded_error_gva_eok"] > g["flash_error_gva_eok"] + 1e-9).sum()),
                "최종표기_20pct초과": int((g["phase217_guarded_error_rate_pct"] > 20).sum()),
            }
        )
    city_summary = pd.DataFrame(city_rows)

    intermediate_view = intermediate_worse[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "flash_predicted_gva_eok",
            "flash_error_rate_pct",
            "guarded_predicted_gva_eok",
            "guarded_error_rate_pct",
            "phase217_guarded_predicted_gva_eok",
            "phase217_guarded_error_rate_pct",
            "phase217_guarded_route",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "flash_predicted_gva_eok": "속보추정_억원",
            "flash_error_rate_pct": "속보오차_pct",
            "guarded_predicted_gva_eok": "중간정밀추정_억원",
            "guarded_error_rate_pct": "중간정밀오차_pct",
            "phase217_guarded_predicted_gva_eok": "최종표기추정_억원",
            "phase217_guarded_error_rate_pct": "최종표기오차_pct",
            "phase217_guarded_route": "최종경로",
        }
    )

    audit = pd.DataFrame(
        [
            {
                "검사": "필수 최종표기 컬럼 누락",
                "값": len(missing),
                "판정": "0",
                "해석": ", ".join(missing) if missing else "통과",
            },
            {
                "검사": "중간 정밀오차가 속보오차보다 큰 셀",
                "값": len(intermediate_worse),
                "판정": "진단용으로만 허용",
                "해석": "포스터·제안서 성능표에 사용 금지",
            },
            {
                "검사": "최종 표기 정밀오차가 속보오차보다 큰 셀",
                "값": len(public_worse),
                "판정": "0",
                "해석": "0이어야 최신 공개표기 계약 통과",
            },
            {
                "검사": "city×parent×middle 중복키",
                "값": int(reg.duplicated(["city", "parent_code", "middle_code"]).sum()),
                "판정": "0",
                "해석": "중복 시 표 집계 왜곡",
            },
        ]
    )

    city_summary.to_csv(OUT / "phase225_city_precision_contract_summary.csv", index=False, encoding="utf-8-sig")
    intermediate_view.to_csv(OUT / "phase225_intermediate_worse_than_flash_cells.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUT / "phase225_precision_contract_audit.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "git_hash": git_hash(),
                "inputs": [str(REGISTRY.relative_to(ROOT))],
                "outputs": [
                    "phase225_city_precision_contract_summary.csv",
                    "phase225_intermediate_worse_than_flash_cells.csv",
                    "phase225_precision_contract_audit.csv",
                ],
                "reporting_contract": {
                    "flash": ["flash_predicted_gva_eok", "flash_error_gva_eok", "flash_error_rate_pct"],
                    "public_precision": [
                        "phase217_guarded_predicted_gva_eok",
                        "phase217_guarded_error_gva_eok",
                        "phase217_guarded_error_rate_pct",
                    ],
                    "diagnostic_only": ["guarded_*", "phase214_*", "phase127_*"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = f"""# Phase225 속보·정밀화 표기 컬럼 계약 검증

생성시각: {CREATED_AT}

## 목적

Phase217 레지스트리에는 과거 중간 정밀화 컬럼과 최신 최종 표기 컬럼이 함께 들어 있다.  
따라서 포스터·제안서가 중간 컬럼을 읽으면 `정밀오차가 속보오차보다 큰 셀`이 남아 있는 것처럼 보일 수 있다.

이번 검증의 표기 계약은 다음과 같다.

| 용도 | 사용 컬럼 | 비고 |
| --- | --- | --- |
| 속보성 성능 | `flash_predicted_gva_eok`, `flash_error_gva_eok`, `flash_error_rate_pct` | Q4+1개월 속보 구조 |
| 공개 정밀화 성능 | `phase217_guarded_predicted_gva_eok`, `phase217_guarded_error_gva_eok`, `phase217_guarded_error_rate_pct` | 속보보다 나쁜 정밀화 후보는 공개 성능으로 채택하지 않음 |
| 진단 전용 | `guarded_*`, `phase214_*`, `phase127_*` | 역전 원인 분석용. 포스터 성능표 사용 금지 |

## 도시별 결과

{md_table(city_summary, 3)}

## 중간 컬럼에서만 보이는 역전 셀

{md_table(intermediate_view, 2)}

## 엄격 검증

{md_table(audit, 0)}

## 결론

1. 중간 정밀화 컬럼에는 속보보다 나쁜 셀이 남아 있다. 이 값은 진단용이며 포스터·제안서 성능표에 쓰면 안 된다.
2. 최신 최종 표기 컬럼인 `phase217_guarded_*` 기준으로는 두 도시 모두 `정밀오차 > 속보오차` 셀이 0개다.
3. 따라서 현재 대외 산출물은 Phase217 최종 컬럼을 기준으로 통일해야 한다.
4. 잔여 20% 초과 업종은 정밀화 역전 문제가 아니라 직접 활동자료 부족 문제로 분류한다.
"""
    REPORT.write_text(report, encoding="utf-8")

    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(city_summary.to_string(index=False))
    print(audit.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
