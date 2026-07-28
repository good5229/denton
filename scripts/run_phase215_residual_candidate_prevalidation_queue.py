#!/usr/bin/env python3
"""Phase215: residual candidate prevalidation queue.

Phase214 left several >20% middle-industry errors.  A broad scan of historical
candidate registries shows many very low-error alternatives, but most of them
were produced by grids whose winning option was selected with actual GVA in
view.  This phase therefore does *not* silently adopt those estimates.  It
creates a prevalidation queue:

1. current Phase214 safe estimate,
2. best additional diagnostic candidate from already-collected sources,
3. source-risk grade explaining why it can or cannot be used as a public rule.

The output is meant to guide the next real data-collection / fixed-rule
validation pass.
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
OUT = DATA / "phase215_residual_candidate_prevalidation_queue"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase215_residual_candidate_prevalidation_queue.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


SOURCE_FILES = [
    "phase85_parent_balanced_accuracy_selection/phase85_candidate_option_detail.csv",
    "phase86_structural_template_screen/phase86_structural_template_options.csv",
    "phase87_remaining_family_template_screen/phase87_remaining_family_options.csv",
    "phase114_block_routed_refinement_audit/phase114_block_candidate_detail.csv",
    "phase115_flash_gt20_source_improvement/phase115_flash_candidate_detail.csv",
    "phase116_expanded_flash_gt20_improvement/phase116_flash_candidate_detail.csv",
    "phase125_comwel_workplace_refinement/phase125_candidate_detail.csv",
    "phase127_precision_comwel_after_phase114/phase127_candidate_detail.csv",
    "phase133_goyang_amount_weighted_refinement/phase133_candidate_cell_detail.csv",
]


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
    view = view.fillna("").astype(str)
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[c].replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def source_grade(path: str, row: pd.Series) -> tuple[str, str]:
    option = str(row.get("option_name", row.get("option_id", row.get("option_label", ""))))
    metric = str(row.get("metric", ""))
    if "phase125" in path or "phase127" in path:
        return (
            "직접자료·사후그리드",
            f"고용보험/사업장 계열 직접자료 후보이나 alpha·floor 조합을 실제값으로 선별한 그리드 후보({metric}, {option})",
        )
    if "phase114" in path or "phase133" in path:
        return (
            "블록후보·사후그리드",
            f"블록별 후보 조합을 실제값으로 선별한 후보({option})",
        )
    if "phase85" in path:
        if "상한" in option:
            return ("구조상한·사후선택", f"구조상한 후보로 직접 활동자료가 아니라 판정 경계 조정({option})")
        return ("과거구조·사후선택", f"2015 경제총조사/과거 구조자료 결합 후보이나 셀별 최저오차 선택 필요({option})")
    if "phase86" in path or "phase87" in path:
        return ("구조상한·사후선택", f"구조상한/하한 템플릿 후보로 직접 활동자료가 아님({option})")
    if "phase115" in path or "phase116" in path:
        return ("속보후보·사후그리드", f"속보 개선 후보이나 실제값 기반 후보 스크리닝 산출물({option})")
    return ("후보·검증필요", option)


def collect_candidates(current: pd.DataFrame) -> pd.DataFrame:
    keys = set(zip(current["city"], current["parent_code"], current["middle_code"]))
    rows: list[dict[str, object]] = []
    for rel in SOURCE_FILES:
        path = DATA / rel
        if not path.exists():
            continue
        df = pd.read_csv(path, dtype={"middle_code": str}, low_memory=False)
        if not {"city", "parent_code", "middle_code", "actual_gva_eok"}.issubset(df.columns):
            continue
        df["middle_code"] = z2(df["middle_code"])
        sub = df[df.apply(lambda r: (r["city"], r["parent_code"], r["middle_code"]) in keys, axis=1)].copy()
        if sub.empty:
            continue
        pred_cols = [c for c in sub.columns if c.endswith("predicted_gva_eok") or c == "predicted_gva_eok"]
        for pred_col in pred_cols:
            for _, row in sub.iterrows():
                pred = pd.to_numeric(pd.Series([row.get(pred_col)]), errors="coerce").iloc[0]
                actual = pd.to_numeric(pd.Series([row.get("actual_gva_eok")]), errors="coerce").iloc[0]
                if pd.isna(pred) or pd.isna(actual) or actual == 0:
                    continue
                err = abs(float(pred) - float(actual))
                grade, note = source_grade(rel, row)
                rows.append(
                    {
                        "city": row["city"],
                        "parent_code": row["parent_code"],
                        "middle_code": row["middle_code"],
                        "middle_label": row.get("middle_label", ""),
                        "actual_gva_eok": float(actual),
                        "candidate_predicted_gva_eok": float(pred),
                        "candidate_error_gva_eok": err,
                        "candidate_error_rate_pct": err / abs(float(actual)) * 100,
                        "candidate_file": rel,
                        "candidate_pred_col": pred_col,
                        "candidate_option": row.get("option_name", row.get("option_id", row.get("option_label", ""))),
                        "candidate_grade": grade,
                        "candidate_risk_note": note,
                    }
                )
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, scope: str, err_col: str, rate_col: str) -> dict[str, object]:
    actual = float(df["actual_gva_eok"].sum())
    err = float(df[err_col].sum())
    return {
        "범위": scope,
        "셀수": int(len(df)),
        "실제합계_억원": actual,
        "오차합계_억원": err,
        "WAPE_pct": err / actual * 100 if actual else np.nan,
        "10pct초과": int((df[rate_col] > 10).sum()),
        "20pct초과": int((df[rate_col] > 20).sum()),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(
        DATA / "phase214_remaining_direct_activity_refinement" / "phase214_refined_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    base["middle_code"] = z2(base["middle_code"])
    current = base[base["phase214_safe_error_rate_pct"] > 20].copy()

    candidates = collect_candidates(current)
    if candidates.empty:
        best = pd.DataFrame()
    else:
        candidates = candidates.merge(
            current[
                [
                    "city",
                    "parent_code",
                    "middle_code",
                    "phase214_safe_predicted_gva_eok",
                    "phase214_safe_error_gva_eok",
                    "phase214_safe_error_rate_pct",
                ]
            ],
            on=["city", "parent_code", "middle_code"],
            how="inner",
        )
        candidates["improves_phase214"] = (
            candidates["candidate_error_gva_eok"] < candidates["phase214_safe_error_gva_eok"] - 1e-9
        )
        best = (
            candidates[candidates["improves_phase214"]]
            .sort_values(["city", "parent_code", "middle_code", "candidate_error_gva_eok"])
            .drop_duplicates(["city", "parent_code", "middle_code"], keep="first")
            .copy()
        )

    queue = current.merge(
        best[
            [
                "city",
                "parent_code",
                "middle_code",
                "candidate_predicted_gva_eok",
                "candidate_error_gva_eok",
                "candidate_error_rate_pct",
                "candidate_file",
                "candidate_option",
                "candidate_grade",
                "candidate_risk_note",
            ]
        ],
        on=["city", "parent_code", "middle_code"],
        how="left",
    )
    queue["phase215_diagnostic_predicted_gva_eok"] = queue["candidate_predicted_gva_eok"].fillna(
        queue["phase214_safe_predicted_gva_eok"]
    )
    queue["phase215_diagnostic_error_gva_eok"] = (
        queue["phase215_diagnostic_predicted_gva_eok"] - queue["actual_gva_eok"]
    ).abs()
    queue["phase215_diagnostic_error_rate_pct"] = (
        queue["phase215_diagnostic_error_gva_eok"] / queue["actual_gva_eok"].abs() * 100
    )
    queue["prevalidation_action"] = np.where(
        queue["candidate_predicted_gva_eok"].notna(),
        "고정 규칙으로 재검증 후 채택 가능성 평가",
        "직접 활동자료 추가 수집 필요",
    )
    queue["needed_direct_data"] = queue["middle_code"].map(
        {
            "94": "단체 등록·회원수·보조금·회비/수입",
            "60": "방송사업자 매출·채널/송출시설·제작인력",
            "50": "해운/수상여객·화물 실적 또는 선박/항만 이용량",
            "15": "품목별 출하액·주요 공장 생산액·신발/가방 제조 직접 생산지표",
            "14": "의복 제조 출하액·고용보험 임금총액·주요 공장 생산액",
            "37": "하수·폐수 처리량·시설용량·위탁계약액",
            "39": "환경정화 계약액·복원사업 집행액·처리량",
            "34": "수리업 매출·정비계약·고용보험 임금총액",
            "66": "보험/금융상품 판매수수료·계약건수·지역 금융서비스 매출",
            "36": "상수도 생산량·유수수량·요금수입",
            "28": "전기장비 출하액·공장별 생산액·전력/생산지수",
            "63": "정보서비스 사업장 매출·데이터센터/플랫폼 활동량",
            "74": "시설관리 계약액·조경공사/유지관리 계약액·임금총액",
        }
    ).fillna("업종별 직접 활동자료")

    summary_rows = []
    for city, g in queue.groupby("city", sort=False):
        summary_rows.append(summarize(g, f"{city} Phase214 20%초과 / 현재", "phase214_safe_error_gva_eok", "phase214_safe_error_rate_pct"))
        summary_rows.append(
            summarize(
                g,
                f"{city} Phase214 20%초과 / 진단최저후보",
                "phase215_diagnostic_error_gva_eok",
                "phase215_diagnostic_error_rate_pct",
            )
        )
    summary = pd.DataFrame(summary_rows)

    strict = {
        "residual_rows": int(len(queue)),
        "candidate_rows": int(len(candidates)),
        "best_candidate_rows": int(len(best)),
        "duplicate_queue_keys": int(len(queue) - queue[["city", "parent_code", "middle_code"]].drop_duplicates().shape[0]),
        "diagnostic_without_improvement": int(
            (
                queue["candidate_predicted_gva_eok"].notna()
                & (queue["phase215_diagnostic_error_gva_eok"] >= queue["phase214_safe_error_gva_eok"] - 1e-9)
            ).sum()
        ),
    }

    candidates.to_csv(OUT / "phase215_candidate_screen.csv", index=False, encoding="utf-8-sig")
    best.to_csv(OUT / "phase215_best_candidate_by_cell.csv", index=False, encoding="utf-8-sig")
    queue.to_csv(OUT / "phase215_prevalidation_queue.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase215_summary.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "code_commit_hash": git_hash(),
                "inputs": SOURCE_FILES
                + ["phase214_remaining_direct_activity_refinement/phase214_refined_registry.csv"],
                "actual_use": "validation and candidate queue construction; diagnostic candidates are not public performance",
                "strict_checks": strict,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    queue_view = queue[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase214_safe_predicted_gva_eok",
            "phase214_safe_error_rate_pct",
            "phase215_diagnostic_predicted_gva_eok",
            "phase215_diagnostic_error_rate_pct",
            "candidate_grade",
            "candidate_file",
            "needed_direct_data",
            "prevalidation_action",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제(억원)",
            "phase214_safe_predicted_gva_eok": "현재추정(억원)",
            "phase214_safe_error_rate_pct": "현재오차(%)",
            "phase215_diagnostic_predicted_gva_eok": "후보추정(억원)",
            "phase215_diagnostic_error_rate_pct": "후보오차(%)",
            "candidate_grade": "후보위험등급",
            "candidate_file": "후보출처",
            "needed_direct_data": "필요 직접자료",
            "prevalidation_action": "다음 조치",
        }
    )

    REPORT.write_text(
        f"""# Phase215 잔여 취약 업종 후보 재검증 큐

## 목적

Phase214 안전채택 이후에도 20%를 초과한 중분류에 대해, 이미 수집·생성된 후보자료에서 오차를 줄일 수 있는 후보를 찾았다. 다만 후보 다수가 실제값을 보고 선택된 그리드 결과이므로, 이번 Phase는 최종 성능 개선값이 아니라 `사전 고정 규칙 재검증 대상 목록`이다.

## 요약

{md_table(summary, 2)}

## 잔여 셀별 후보

{md_table(queue_view, 2)}

## 엄격검증

- 잔여 큐: {strict['residual_rows']}개.
- 후보 스크린 행: {strict['candidate_rows']}개.
- 셀별 최저 후보: {strict['best_candidate_rows']}개.
- 큐 고유키 중복: {strict['duplicate_queue_keys']}개.
- 후보 적용 시 개선 없는 셀: {strict['diagnostic_without_improvement']}개.

## 해석

- 여러 업종은 이미 수집된 후보자료만으로도 10% 이내까지 내려갈 가능성이 있다. 특히 고양시 협회·단체/방송업/하수·폐수, 포항시 K66/수도·하수·방송/제조수리에서 후보 성능이 크게 낮아진다.
- 그러나 1% 내외 후보는 대부분 사후 그리드 최저값이다. 이 값을 그대로 채택하면 데이터 유출 또는 사후선택이라는 비판을 피하기 어렵다.
- 다음 단계는 후보 파일의 `option_id`, `metric`, `alpha`, `baseline_floor`를 업종군별로 사전에 고정하고, 2021~2022 또는 외부 시군구에서 성능을 먼저 검증한 뒤 2023에 적용하는 것이다.
- 직접자료가 추가로 필요한 업종은 방송·정보서비스, 협회·단체, 환경처리·수도, 금융서비스, 수상운송이다.
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
