#!/usr/bin/env python3
"""Phase216: precision-vs-flash dominance guard audit.

Phase214 reduced many precision errors, but two cells still had a precision
estimate worse than the Q4+1 month flash estimate.  That is not acceptable for
public wording such as "precision/refinement improved the estimate."  This
phase creates an explicit audit layer:

* identify every city×parent×middle cell where the safe precision estimate is
  worse than the flash estimate;
* create a validation-floor track that reclassifies those cells as "flash
  retained / additional direct data required";
* keep this clearly separated from an operational forecast rule, because the
  reclassification uses actual GVA during validation;
* carry forward the >10% and >20% residual queues that still require new direct
  activity data.

It does not overwrite Phase214.  It supplies a stricter reporting surface for
posters/reports and a target list for the next data-collection pass.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase216_precision_flash_dominance_guard"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase216_precision_flash_dominance_guard.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


DIRECT_DATA_NEEDS = {
    ("C00", "22"): "고무·플라스틱 제품 출하액, 주요 공장 생산액, 전력사용량의 업종별 월/연 집계",
    ("C00", "30"): "자동차·트레일러 부품 출하액, 주요 사업장 생산액·고용보험 임금총액",
    ("C00", "14"): "의복 제조 출하액, 공장별 생산액, 고용보험 임금총액",
    ("C00", "15"): "가죽·가방·신발 제조 출하액, 주요 공장 생산액",
    ("C00", "16"): "목재·나무제품 출하액, 공장 생산액, 산업단지 입주기업 생산액",
    ("C00", "28"): "전기장비 출하액, 공장별 생산액, 전력사용량",
    ("C00", "34"): "산업용 기계·장비 수리 매출, 정비계약액, 고용보험 임금총액",
    ("ERS", "36"): "상수도 생산량, 유수수량, 요금수입",
    ("ERS", "37"): "하수·폐수 처리량, 처리시설 용량, 위탁계약액",
    ("ERS", "39"): "환경정화 계약액, 복원사업 집행액, 처리량",
    ("ERS", "94"): "비영리단체 등록수, 지방보조금, 회비·수입, 회원수",
    ("H00", "50"): "수상여객·화물 실적, 선박·항만·하천 이용량",
    ("J00", "60"): "방송사업자 매출, 송출시설·채널 수, 제작 인력",
    ("J00", "63"): "정보서비스 사업장 매출, 플랫폼·데이터센터 활동량",
    ("K00", "66"): "보험·금융상품 판매수수료, 계약건수, 금융서비스 사업장 매출",
    ("MN0", "74"): "시설관리·조경 계약액, 공공조달 낙찰액, 고용보험 임금총액",
}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def z2(s: pd.Series) -> pd.Series:
    return s.astype(str).str.extract(r"(\d+)")[0].str.zfill(2)


def fmt_num(x: object, digits: int = 2) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    if isinstance(x, (float, np.floating)):
        return f"{float(x):,.{digits}f}"
    return str(x)


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            view[col] = view[col].map(lambda x: fmt_num(x, digits))
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def summarize(df: pd.DataFrame, scope: str, pred_col: str, err_col: str, rate_col: str) -> dict[str, object]:
    actual = float(df["actual_gva_eok"].abs().sum())
    err = float(df[err_col].sum())
    return {
        "범위": scope,
        "셀수": int(len(df)),
        "실제합계_억원": actual,
        "추정합계_억원": float(df[pred_col].sum()),
        "오차합계_억원": err,
        "WAPE_pct": err / actual * 100 if actual else np.nan,
        "10pct초과": int((df[rate_col] > 10).sum()),
        "20pct초과": int((df[rate_col] > 20).sum()),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    src = DATA / "phase214_remaining_direct_activity_refinement" / "phase214_refined_registry.csv"
    df = pd.read_csv(src, dtype={"middle_code": str}, low_memory=False)
    df["middle_code"] = z2(df["middle_code"])

    required = {
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "flash_predicted_gva_eok",
        "flash_error_gva_eok",
        "flash_error_rate_pct",
        "phase214_safe_predicted_gva_eok",
        "phase214_safe_error_gva_eok",
        "phase214_safe_error_rate_pct",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"missing columns in {src}: {missing}")

    df["precision_worse_than_flash_after_phase214"] = (
        df["phase214_safe_error_gva_eok"] > df["flash_error_gva_eok"] + 1e-9
    )
    df["phase216_validation_floor_predicted_gva_eok"] = np.where(
        df["precision_worse_than_flash_after_phase214"],
        df["flash_predicted_gva_eok"],
        df["phase214_safe_predicted_gva_eok"],
    )
    df["phase216_validation_floor_route"] = np.where(
        df["precision_worse_than_flash_after_phase214"],
        "속보 유지: 정밀화 검증 실패",
        "정밀화 유지",
    )
    df["phase216_validation_floor_error_gva_eok"] = (
        df["phase216_validation_floor_predicted_gva_eok"] - df["actual_gva_eok"]
    ).abs()
    df["phase216_validation_floor_error_rate_pct"] = (
        df["phase216_validation_floor_error_gva_eok"] / df["actual_gva_eok"].abs() * 100
    )
    df["phase216_public_claim_status"] = np.select(
        [
            df["precision_worse_than_flash_after_phase214"],
            df["phase216_validation_floor_error_rate_pct"] > 20,
            df["phase216_validation_floor_error_rate_pct"] > 10,
        ],
        [
            "정밀화 성능 주장 제외",
            "20% 초과 직접자료 필요",
            "10% 초과 직접자료 필요",
        ],
        default="10% 이내 검증",
    )
    df["phase216_direct_data_needed"] = [
        DIRECT_DATA_NEEDS.get((str(parent), str(middle).zfill(2)), "업종별 직접 활동자료 추가 확인")
        for parent, middle in zip(df["parent_code"], df["middle_code"])
    ]

    dominance_fail = df[df["precision_worse_than_flash_after_phase214"]].copy().sort_values(
        ["city", "phase214_safe_error_rate_pct"], ascending=[True, False]
    )
    residual10 = df[df["phase216_validation_floor_error_rate_pct"] > 10].copy().sort_values(
        ["city", "phase216_validation_floor_error_rate_pct"], ascending=[True, False]
    )
    residual20 = df[df["phase216_validation_floor_error_rate_pct"] > 20].copy().sort_values(
        ["city", "phase216_validation_floor_error_rate_pct"], ascending=[True, False]
    )

    summaries: list[dict[str, object]] = []
    for city, g in df.groupby("city", sort=False):
        summaries.append(summarize(g, f"{city} / 속보", "flash_predicted_gva_eok", "flash_error_gva_eok", "flash_error_rate_pct"))
        summaries.append(summarize(g, f"{city} / Phase214 정밀화", "phase214_safe_predicted_gva_eok", "phase214_safe_error_gva_eok", "phase214_safe_error_rate_pct"))
        summaries.append(summarize(g, f"{city} / Phase216 검증표기", "phase216_validation_floor_predicted_gva_eok", "phase216_validation_floor_error_gva_eok", "phase216_validation_floor_error_rate_pct"))
    summary = pd.DataFrame(summaries)

    source_audit = pd.DataFrame(
        [
            {
                "검사": "phase214 정밀화가 속보보다 나쁜 셀",
                "값": int(df["precision_worse_than_flash_after_phase214"].sum()),
                "판정": "0이어야 공개 정밀화 성능으로 안전",
            },
            {
                "검사": "phase216 검증표기 후 속보보다 나쁜 셀",
                "값": int((df["phase216_validation_floor_error_gva_eok"] > df["flash_error_gva_eok"] + 1e-9).sum()),
                "판정": "0",
            },
            {
                "검사": "city×parent×middle 중복키",
                "값": int(df.duplicated(["city", "parent_code", "middle_code"]).sum()),
                "판정": "0",
            },
            {
                "검사": "음수 또는 결측 실제값",
                "값": int((df["actual_gva_eok"].isna() | (df["actual_gva_eok"] <= 0)).sum()),
                "판정": "0",
            },
        ]
    )

    df.to_csv(OUT / "phase216_validation_guard_registry.csv", index=False, encoding="utf-8-sig")
    dominance_fail.to_csv(OUT / "phase216_precision_worse_than_flash_cells.csv", index=False, encoding="utf-8-sig")
    residual10.to_csv(OUT / "phase216_residual_gt10_after_guard.csv", index=False, encoding="utf-8-sig")
    residual20.to_csv(OUT / "phase216_residual_gt20_after_guard.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase216_city_summary.csv", index=False, encoding="utf-8-sig")
    source_audit.to_csv(OUT / "phase216_strict_audit.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "created_at": CREATED_AT,
        "git_hash": git_hash(),
        "source": str(src.relative_to(ROOT)),
        "outputs": [
            "phase216_validation_guard_registry.csv",
            "phase216_precision_worse_than_flash_cells.csv",
            "phase216_residual_gt10_after_guard.csv",
            "phase216_residual_gt20_after_guard.csv",
            "phase216_city_summary.csv",
            "phase216_strict_audit.csv",
        ],
        "important_note": "phase216_validation_floor_route uses actual GVA to identify validation failures; it is an audit/reporting guard, not a pure real-time forecast rule.",
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fail_view = dominance_fail[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "flash_predicted_gva_eok",
            "flash_error_rate_pct",
            "phase214_safe_predicted_gva_eok",
            "phase214_safe_error_rate_pct",
            "phase216_direct_data_needed",
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
            "phase214_safe_predicted_gva_eok": "정밀추정_억원",
            "phase214_safe_error_rate_pct": "정밀오차_pct",
            "phase216_direct_data_needed": "필요자료",
        }
    )
    res_view = residual20[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase216_validation_floor_predicted_gva_eok",
            "phase216_validation_floor_error_rate_pct",
            "phase216_direct_data_needed",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase216_validation_floor_predicted_gva_eok": "검증표기추정_억원",
            "phase216_validation_floor_error_rate_pct": "오차_pct",
            "phase216_direct_data_needed": "필요자료",
        }
    )

    report = f"""# Phase216 정밀화-속보 우위 게이트 검증

생성시각: {CREATED_AT}

## 목적

정밀화 추정이 속보 추정보다 나쁜 셀을 공개 성능표에서 그대로 두지 않기 위한 검증 레이어를 만들었다.  
이 단계는 Phase214를 덮어쓰지 않고, 포스터·보고서에서 어떤 셀을 정밀화 성능으로 주장하면 안 되는지 분리한다.

## 핵심 결과

{md_table(summary, 3)}

## 정밀화가 속보보다 나쁜 셀

{md_table(fail_view, 2)}

해석:

- 위 셀은 정밀화 추정값이 기존 속보 추정보다 실제 GVA와 더 멀다.
- 따라서 “정밀화 성능 개선” 셀로 표시하면 안 된다.
- 단, 실제값을 보고 속보로 되돌리는 것은 운영 예측 성능이 아니므로, 공개 문구에서는 “속보 유지·직접자료 필요”로 표현한다.

## 20% 초과 잔여 업종

{md_table(res_view, 2)}

## 엄격 검증

{md_table(source_audit, 0)}

## 결론

1. Phase214 정밀화에는 아직 속보보다 나쁜 셀이 2개 남아 있었다.
2. 이 문제는 정밀화 산식 자체보다 최종 채택 게이트가 약했던 문제다.
3. 포스터·제안서에서는 해당 셀을 정밀화 성공으로 쓰지 말고, “속보 유지/추가 직접자료 필요”로 재분류해야 한다.
4. 잔여 20% 초과 업종은 실제값 사후선택 후보를 성능으로 채택하지 말고, 표의 필요자료를 확보한 뒤 사전 고정 규칙으로 재검증해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(summary.to_string(index=False))
    print(source_audit.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
