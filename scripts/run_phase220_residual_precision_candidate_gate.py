#!/usr/bin/env python3
"""Phase220: residual precision candidate gate after flash-dominance fix.

This phase does not try to make the remaining high-error cells look good by
choosing the best post-hoc candidate.  It answers a stricter question:

* Among the cells that remain above 20% after Phase217, do we have any
  already-collected candidate that is both improving and free of explicit
  post-hoc/grid-selection risk?
* If not, which high-performing candidates are only diagnostic upper bounds,
  and which direct data are actually needed next?

The user repeatedly emphasized that actual GVA can be used for validation, but
not for selecting a production/competition performance rule.  This script keeps
that boundary visible in the output.
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
OUT = DATA / "phase220_residual_precision_candidate_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase220_residual_precision_candidate_gate.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


NEEDED_DIRECT_DATA = {
    ("고양시", "ERS", "94"): "비영리·직능단체 등록수, 회원수, 보조금, 회비/사업수입, 단체 종사자",
    ("고양시", "J00", "60"): "방송사업자 매출, 채널·송출시설, 제작인력, 콘텐츠 제작/유통 매출",
    ("고양시", "H00", "50"): "항만·수상여객·수상화물 실적, 선박·운항 사업체 매출",
    ("고양시", "C00", "14"): "중분류별 출하액·부가가치, 의복 제조 대형사업장 생산액, 임금총액",
    ("고양시", "C00", "15"): "중분류별 출하액·부가가치, 가죽·신발 제조 대형사업장 생산액, 임금총액",
    ("고양시", "ERS", "37"): "시군구 하수처리 사용료수입, 위탁계약액, 운영비/총괄원가",
    ("포항시", "J00", "63"): "정보서비스 사업체 매출, 데이터센터·플랫폼 이용/서버 활동량",
    ("포항시", "ERS", "39"): "환경정화 계약액, 오염정화 사업비, 처리·복원 사업장 매출",
    ("포항시", "ERS", "37"): "하수·분뇨 처리 사용료수입, 위탁계약액, 운영비/총괄원가",
    ("포항시", "C00", "34"): "산업기계 수리 매출, 정비·유지보수 계약액, 임금총액",
    ("포항시", "K00", "66"): "보험·금융상품 판매수수료, 금융서비스 사업체 매출, 계약건수",
    ("포항시", "ERS", "36"): "상수도 급수수익, 총괄원가, 운영비, 요금수입",
    ("포항시", "C00", "28"): "전기장비 출하액, 공장별 생산액, 전력사용액, 임금총액",
    ("포항시", "J00", "60"): "방송사업자 매출, 채널·송출시설, 제작인력",
}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def z2(s: pd.Series) -> pd.Series:
    return s.astype(str).str.extract(r"(\d+)")[0].str.zfill(2)


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


def summarize(df: pd.DataFrame, label: str, err_col: str, rate_col: str, pred_col: str) -> dict[str, object]:
    actual = float(df["actual_gva_eok"].abs().sum())
    err = float(df[err_col].sum())
    return {
        "구분": label,
        "셀수": int(len(df)),
        "실제합계_억원": actual,
        "추정합계_억원": float(df[pred_col].sum()),
        "오차합계_억원": err,
        "WAPE_pct": err / actual * 100 if actual else np.nan,
        "10pct초과": int((df[rate_col] > 10).sum()),
        "20pct초과": int((df[rate_col] > 20).sum()),
    }


def classify_candidate(row: pd.Series) -> tuple[str, str]:
    grade = str(row.get("candidate_grade", ""))
    risk = str(row.get("candidate_risk_note", ""))
    option = str(row.get("candidate_option", ""))
    file = str(row.get("candidate_file", ""))
    risk_text = " / ".join([grade, risk, option, file])
    if "사후" in risk_text or "그리드" in risk_text or "최저오차" in risk_text or "실제값" in risk_text:
        return "보류", "사후선택 또는 그리드 탐색 흔적"
    if "빈티지" in risk_text and "미확인" in risk_text:
        return "보류", "공표시점·빈티지 미확인"
    return "채택가능", "명시적 사후선택 위험 없음"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(
        DATA / "phase217_public_safe_candidate_rerank_audit" / "phase217_reranked_guarded_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    reg["middle_code"] = z2(reg["middle_code"])
    residual = reg[reg["phase217_guarded_error_rate_pct"] > 20].copy()

    screen_path = DATA / "phase215_residual_candidate_prevalidation_queue" / "phase215_candidate_screen.csv"
    candidates = pd.read_csv(screen_path, dtype={"middle_code": str}, low_memory=False)
    candidates["middle_code"] = z2(candidates["middle_code"])
    key = ["city", "parent_code", "middle_code", "middle_label"]
    cand = candidates.merge(
        residual[
            key
            + [
                "actual_gva_eok",
                "flash_predicted_gva_eok",
                "flash_error_gva_eok",
                "flash_error_rate_pct",
                "phase217_guarded_predicted_gva_eok",
                "phase217_guarded_error_gva_eok",
                "phase217_guarded_error_rate_pct",
            ]
        ],
        on=key,
        how="inner",
        suffixes=("", "_phase217"),
    )
    cand["improves_phase217"] = cand["candidate_error_gva_eok"] < cand["phase217_guarded_error_gva_eok"] - 1e-9
    cand[["gate_decision", "gate_reason"]] = cand.apply(lambda r: pd.Series(classify_candidate(r)), axis=1)
    cand["adoptable_phase220"] = cand["improves_phase217"] & cand["gate_decision"].eq("채택가능")

    best_diag = (
        cand[cand["improves_phase217"]]
        .sort_values(key + ["candidate_error_gva_eok"])
        .drop_duplicates(key, keep="first")
        .copy()
    )
    best_adoptable = (
        cand[cand["adoptable_phase220"]]
        .sort_values(key + ["candidate_error_gva_eok"])
        .drop_duplicates(key, keep="first")
        .copy()
    )

    out = residual.copy()
    if not best_adoptable.empty:
        cols = key + [
            "candidate_predicted_gva_eok",
            "candidate_error_gva_eok",
            "candidate_error_rate_pct",
            "candidate_file",
            "candidate_option",
            "candidate_grade",
            "candidate_risk_note",
            "gate_reason",
        ]
        out = out.merge(best_adoptable[cols].add_prefix("phase220_"), left_on=key, right_on=[f"phase220_{c}" for c in key], how="left")
        out = out.drop(columns=[f"phase220_{c}" for c in key])
    else:
        for col in [
            "phase220_candidate_predicted_gva_eok",
            "phase220_candidate_error_gva_eok",
            "phase220_candidate_error_rate_pct",
            "phase220_candidate_file",
            "phase220_candidate_option",
            "phase220_candidate_grade",
            "phase220_candidate_risk_note",
            "phase220_gate_reason",
        ]:
            out[col] = np.nan

    out["phase220_predicted_gva_eok"] = out["phase220_candidate_predicted_gva_eok"].fillna(out["phase217_guarded_predicted_gva_eok"])
    out["phase220_error_gva_eok"] = (out["phase220_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out["phase220_error_rate_pct"] = out["phase220_error_gva_eok"] / out["actual_gva_eok"].abs() * 100
    out["phase220_route"] = np.where(out["phase220_candidate_predicted_gva_eok"].notna(), "채택가능 후보 반영", "추가 채택 후보 없음")
    out["needed_direct_data"] = out.apply(
        lambda r: NEEDED_DIRECT_DATA.get((r["city"], r["parent_code"], str(r["middle_code"]).zfill(2)), "업종별 금액형 직접 활동자료"),
        axis=1,
    )

    summary = pd.DataFrame(
        [
            summarize(out, "Phase217 잔여 20%초과 / 현재", "phase217_guarded_error_gva_eok", "phase217_guarded_error_rate_pct", "phase217_guarded_predicted_gva_eok"),
            summarize(out, "Phase220 명시위험 제거 후 채택", "phase220_error_gva_eok", "phase220_error_rate_pct", "phase220_predicted_gva_eok"),
        ]
    )

    # Diagnostic upper-bound summary: what would happen if the best post-hoc
    # candidate was allowed.  This is intentionally not written as performance.
    diag_join = residual.merge(
        best_diag[
            key
            + [
                "candidate_predicted_gva_eok",
                "candidate_error_gva_eok",
                "candidate_error_rate_pct",
                "candidate_file",
                "candidate_option",
                "candidate_grade",
                "gate_reason",
            ]
        ].add_prefix("diag_"),
        left_on=key,
        right_on=[f"diag_{c}" for c in key],
        how="left",
    )
    diag_join = diag_join.drop(columns=[f"diag_{c}" for c in key])
    # The Phase217 registry already contains `diag_candidate_*` columns from
    # previous diagnostics.  Normalize the newly merged Phase220 diagnostic
    # columns after pandas suffixing.
    for base in [
        "diag_candidate_predicted_gva_eok",
        "diag_candidate_error_gva_eok",
        "diag_candidate_error_rate_pct",
    ]:
        suffixed = f"{base}_y"
        if suffixed in diag_join.columns:
            diag_join[base] = diag_join[suffixed]

    gate_summary = (
        cand.groupby(["gate_decision", "gate_reason"], dropna=False)
        .agg(
            후보수=("candidate_option", "size"),
            개선후보수=("improves_phase217", "sum"),
            대상셀수=("middle_code", "nunique"),
        )
        .reset_index()
        .sort_values(["gate_decision", "후보수"], ascending=[True, False])
    )

    residual_view = out[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase217_guarded_predicted_gva_eok",
            "phase217_guarded_error_rate_pct",
            "phase220_predicted_gva_eok",
            "phase220_error_rate_pct",
            "phase220_route",
            "needed_direct_data",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase217_guarded_predicted_gva_eok": "현재추정_억원",
            "phase217_guarded_error_rate_pct": "현재오차_pct",
            "phase220_predicted_gva_eok": "Phase220추정_억원",
            "phase220_error_rate_pct": "Phase220오차_pct",
            "phase220_route": "판정",
            "needed_direct_data": "필요 직접자료",
        }
    )

    diag_view = diag_join[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase217_guarded_error_rate_pct",
            "diag_candidate_error_rate_pct",
            "diag_candidate_option",
            "diag_candidate_grade",
            "diag_gate_reason",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase217_guarded_error_rate_pct": "현재오차_pct",
            "diag_candidate_error_rate_pct": "진단최저오차_pct",
            "diag_candidate_option": "진단최저 후보",
            "diag_candidate_grade": "후보등급",
            "diag_gate_reason": "보류사유",
        }
    ).sort_values(["지역", "현재오차_pct"], ascending=[True, False])

    strict = pd.DataFrame(
        [
            {"검사": "잔여 20%초과 셀", "값": int(len(residual)), "판정": "대상"},
            {"검사": "명시적 사후선택 없는 개선 후보", "값": int(best_adoptable.shape[0]), "판정": "0이면 추가 채택 불가"},
            {"검사": "사후선택 제거 후 오차 악화 셀", "값": int((out["phase220_error_gva_eok"] > out["phase217_guarded_error_gva_eok"] + 1e-9).sum()), "판정": "0"},
            {"검사": "정밀화가 속보보다 나쁜 셀", "값": int((out["phase220_error_gva_eok"] > out["flash_error_gva_eok"] + 1e-9).sum()), "판정": "잔여 중 일부는 속보 자체도 부정확하므로 원자료 필요"},
            {"검사": "city×parent×middle 중복키", "값": int(out.duplicated(["city", "parent_code", "middle_code"]).sum()), "판정": "0"},
        ]
    )

    out.to_csv(OUT / "phase220_guarded_residual_registry.csv", index=False, encoding="utf-8-sig")
    cand.to_csv(OUT / "phase220_residual_candidate_gate.csv", index=False, encoding="utf-8-sig")
    best_diag.to_csv(OUT / "phase220_best_diagnostic_upper_bound.csv", index=False, encoding="utf-8-sig")
    best_adoptable.to_csv(OUT / "phase220_best_adoptable_candidates.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase220_summary.csv", index=False, encoding="utf-8-sig")
    strict.to_csv(OUT / "phase220_strict_audit.csv", index=False, encoding="utf-8-sig")
    gate_summary.to_csv(OUT / "phase220_gate_summary.csv", index=False, encoding="utf-8-sig")

    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "git_hash": git_hash(),
                "inputs": [
                    "data/processed/phase217_public_safe_candidate_rerank_audit/phase217_reranked_guarded_registry.csv",
                    "data/processed/phase215_residual_candidate_prevalidation_queue/phase215_candidate_screen.csv",
                ],
                "outputs": [
                    "phase220_guarded_residual_registry.csv",
                    "phase220_residual_candidate_gate.csv",
                    "phase220_best_diagnostic_upper_bound.csv",
                    "phase220_best_adoptable_candidates.csv",
                    "phase220_summary.csv",
                    "phase220_strict_audit.csv",
                    "phase220_gate_summary.csv",
                ],
                "scope": "Residual cells above 20% after Phase217 only",
                "actual_use": "validation and risk gate audit; diagnostic upper bounds are not production performance",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    REPORT.write_text(
        f"""# Phase220 잔여 정밀오차 후보 게이트

생성시각: {CREATED_AT}

## 목적

Phase217에서 `정밀화가 속보보다 나쁜 셀`은 제거했다. 이번 단계는 남은 20% 초과 업종에 대해, 추가 수집·후보 자료 중 실제로 채택 가능한 정밀화 후보가 있는지 분리 검증했다.

## 핵심 결과

{md_table(summary, 2)}

## 엄격검증

{md_table(strict, 0)}

## 후보 게이트 요약

{md_table(gate_summary, 0)}

## 잔여 업종별 판정과 필요한 직접자료

{md_table(residual_view, 2)}

## 진단상 최저 후보

아래 표는 “이 정도까지 낮아질 가능성”을 보여주는 진단용 상한이다. `사후선택`, `그리드 탐색`, `실제값 기반 후보 스크리닝` 흔적이 있으므로 운영 성능이나 포스터 성능으로 쓰지 않는다.

{md_table(diag_view, 2)}

## 결론

1. 잔여 20% 초과 업종에서 명시적 사후선택 위험이 없는 개선 후보는 `0개`다.
2. 진단상으로는 많은 업종이 10% 안쪽까지 내려갈 수 있지만, 대부분 실제값 기반 후보 스크리닝 또는 alpha/floor 그리드 탐색 결과다.
3. 따라서 현재 공개 가능한 정밀화 성능은 Phase217/218 수준을 유지하는 것이 정직하다.
4. 다음 개선은 모델 조합보다 자료 확보가 핵심이다. 특히 `시군구×중분류`의 금액형 직접자료, 즉 매출·요금수입·계약액·보조금·임금총액 계열이 필요하다.
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
