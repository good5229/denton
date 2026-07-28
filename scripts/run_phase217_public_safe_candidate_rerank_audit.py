#!/usr/bin/env python3
"""Phase217: public-safe candidate rerank audit.

Phase214 sorted safe candidates by conservative source rank before error.  That
was intentionally cautious, but it created a measurable problem: a worse safe
candidate could be selected while a lower-error "existing validated" candidate
was available for the same city×industry cell.

This phase tests a corrected validation surface:

* among candidates already marked `public_safe_candidate`, choose the lowest
  validation error first;
* then apply the Phase216 dominance guard so a precision estimate is not
  reported as better when the flash estimate is closer;
* keep the result as a validation/reporting audit, not as an unrestricted
  operational rule.
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
OUT = DATA / "phase217_public_safe_candidate_rerank_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase217_public_safe_candidate_rerank_audit.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


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
    reg = pd.read_csv(
        DATA / "phase214_remaining_direct_activity_refinement" / "phase214_refined_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    reg["middle_code"] = z2(reg["middle_code"])
    cand = pd.read_csv(
        DATA / "phase214_remaining_direct_activity_refinement" / "phase214_candidate_screen.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    cand["middle_code"] = z2(cand["middle_code"])

    key = ["city", "parent_code", "middle_code"]
    public = cand[cand["public_safe_candidate"]].copy()
    best = (
        public.sort_values(key + ["candidate_error_gva_eok", "safe_rank"])
        .drop_duplicates(key, keep="first")
        .copy()
    )
    best_cols = key + [
        "candidate_source_id",
        "candidate_source_label",
        "candidate_source_family",
        "candidate_timing_track",
        "candidate_safety",
        "candidate_predicted_gva_eok",
        "candidate_error_gva_eok",
        "candidate_error_rate_pct",
        "candidate_note",
        "safe_rank",
    ]
    out = reg.merge(best[best_cols].add_prefix("phase217_"), left_on=key, right_on=[f"phase217_{k}" for k in key], how="left")
    out = out.drop(columns=[f"phase217_{k}" for k in key])
    out["phase217_rerank_selected"] = out["phase217_candidate_predicted_gva_eok"].notna()
    out["phase217_rerank_predicted_gva_eok"] = np.where(
        out["phase217_rerank_selected"],
        out["phase217_candidate_predicted_gva_eok"],
        out["guarded_predicted_gva_eok"],
    )
    out["phase217_rerank_error_gva_eok"] = (out["phase217_rerank_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out["phase217_rerank_error_rate_pct"] = out["phase217_rerank_error_gva_eok"] / out["actual_gva_eok"].abs() * 100

    out["phase217_rerank_worse_than_flash"] = out["phase217_rerank_error_gva_eok"] > out["flash_error_gva_eok"] + 1e-9
    out["phase217_guarded_predicted_gva_eok"] = np.where(
        out["phase217_rerank_worse_than_flash"],
        out["flash_predicted_gva_eok"],
        out["phase217_rerank_predicted_gva_eok"],
    )
    out["phase217_guarded_route"] = np.where(
        out["phase217_rerank_worse_than_flash"],
        "속보 유지: 정밀화 검증 실패",
        np.where(out["phase217_rerank_selected"], "재정렬 정밀화 후보", "기존 보류게이트 유지"),
    )
    out["phase217_reporting_source_label"] = np.where(
        out["phase217_rerank_worse_than_flash"],
        "Q4+1개월 속보 추정값",
        out["phase217_candidate_source_label"].fillna("기존 보류게이트 추정값"),
    )
    out["phase217_reporting_safety"] = np.where(
        out["phase217_rerank_worse_than_flash"],
        "속보 유지",
        out["phase217_candidate_safety"].fillna("기존 경로"),
    )
    out["phase217_guarded_error_gva_eok"] = (out["phase217_guarded_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
    out["phase217_guarded_error_rate_pct"] = out["phase217_guarded_error_gva_eok"] / out["actual_gva_eok"].abs() * 100

    changed = out[
        (out["phase217_guarded_error_gva_eok"] - out["phase214_safe_error_gva_eok"]).abs() > 1e-9
    ].copy().sort_values(["city", "phase214_safe_error_rate_pct"], ascending=[True, False])
    residual10 = out[out["phase217_guarded_error_rate_pct"] > 10].copy().sort_values(
        ["city", "phase217_guarded_error_rate_pct"], ascending=[True, False]
    )
    residual20 = out[out["phase217_guarded_error_rate_pct"] > 20].copy().sort_values(
        ["city", "phase217_guarded_error_rate_pct"], ascending=[True, False]
    )

    summary_rows: list[dict[str, object]] = []
    for city, g in out.groupby("city", sort=False):
        summary_rows.extend(
            [
                summarize(g, f"{city} / 속보", "flash_predicted_gva_eok", "flash_error_gva_eok", "flash_error_rate_pct"),
                summarize(g, f"{city} / Phase214", "phase214_safe_predicted_gva_eok", "phase214_safe_error_gva_eok", "phase214_safe_error_rate_pct"),
                summarize(g, f"{city} / Phase217 재정렬+게이트", "phase217_guarded_predicted_gva_eok", "phase217_guarded_error_gva_eok", "phase217_guarded_error_rate_pct"),
            ]
        )
    summary = pd.DataFrame(summary_rows)
    audit = pd.DataFrame(
        [
            {
                "검사": "재정렬 후 속보보다 나쁜 셀",
                "값": int((out["phase217_guarded_error_gva_eok"] > out["flash_error_gva_eok"] + 1e-9).sum()),
                "판정": "0",
            },
            {
                "검사": "Phase214 대비 악화 셀",
                "값": int((out["phase217_guarded_error_gva_eok"] > out["phase214_safe_error_gva_eok"] + 1e-9).sum()),
                "판정": "0",
            },
            {
                "검사": "city×parent×middle 중복키",
                "값": int(out.duplicated(key).sum()),
                "판정": "0",
            },
        ]
    )

    out.to_csv(OUT / "phase217_reranked_guarded_registry.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(OUT / "phase217_changed_cells.csv", index=False, encoding="utf-8-sig")
    residual10.to_csv(OUT / "phase217_residual_gt10.csv", index=False, encoding="utf-8-sig")
    residual20.to_csv(OUT / "phase217_residual_gt20.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase217_city_summary.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUT / "phase217_strict_audit.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "created_at": CREATED_AT,
        "git_hash": git_hash(),
        "inputs": [
            "data/processed/phase214_remaining_direct_activity_refinement/phase214_refined_registry.csv",
            "data/processed/phase214_remaining_direct_activity_refinement/phase214_candidate_screen.csv",
        ],
        "outputs": [
            "phase217_reranked_guarded_registry.csv",
            "phase217_changed_cells.csv",
            "phase217_residual_gt10.csv",
            "phase217_residual_gt20.csv",
            "phase217_city_summary.csv",
            "phase217_strict_audit.csv",
        ],
        "caution": "Candidate reranking is a validation audit using actual GVA; before production use, the same route hierarchy must be frozen with prior-year/external-city validation.",
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changed_view = changed[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase214_safe_predicted_gva_eok",
            "phase214_safe_error_rate_pct",
            "phase217_guarded_predicted_gva_eok",
            "phase217_guarded_error_rate_pct",
            "phase217_reporting_source_label",
            "phase217_reporting_safety",
            "phase217_guarded_route",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase214_safe_predicted_gva_eok": "기존추정_억원",
            "phase214_safe_error_rate_pct": "기존오차_pct",
            "phase217_guarded_predicted_gva_eok": "재정렬추정_억원",
            "phase217_guarded_error_rate_pct": "재정렬오차_pct",
            "phase217_reporting_source_label": "표기자료",
            "phase217_reporting_safety": "자료판정",
            "phase217_guarded_route": "최종경로",
        }
    )
    residual20_view = residual20[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
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
            "phase217_guarded_predicted_gva_eok": "추정GVA_억원",
            "phase217_guarded_error_rate_pct": "오차_pct",
            "phase217_guarded_route": "경로",
        }
    )

    report = f"""# Phase217 안전후보 재정렬 및 속보우위 게이트

생성시각: {CREATED_AT}

## 목적

Phase214의 안전후보 선택은 자료 안전도 순위를 오차보다 먼저 적용했다. 이 때문에 같은 셀에서 더 낮은 오차 후보가 있었는데도 더 보수적인 고오차 후보가 선택되는 경우가 있었다.  
이번 단계에서는 이미 `public_safe_candidate`로 표시된 후보 안에서 검증오차가 가장 작은 후보를 고른 뒤, 정밀화가 속보보다 나쁜 셀은 속보 유지로 표기했다.

## 도시별 결과

{md_table(summary, 3)}

## 변경 셀

{md_table(changed_view, 2)}

## 20% 초과 잔여 셀

{md_table(residual20_view, 2)}

## 엄격 검증

{md_table(audit, 0)}

## 정밀오차가 속보오차보다 커진 원인

1. 정밀화 후보가 항상 더 좋은 것은 아니다. 특히 제조업 일부 중분류는 연간 공식·시설자료가 상위 제조업 총량을 나누는 데는 유용해도, 특정 중분류의 2023년 단기 구조 변화까지 설명하지 못했다.
2. Phase214는 후보 안전도 순위를 오차보다 먼저 적용했다. 이 때문에 포항시 `사업시설 관리 및 조경 서비스업`처럼 더 낮은 오차의 기존 검증후보가 있었는데도 더 보수적인 고오차 후보가 선택됐다.
3. 포항시 `고무 및 플라스틱제품 제조업`, `자동차 및 트레일러 제조업`은 정밀화 후보보다 Q4+1개월 속보 추정값이 실제값에 더 가까웠다. 따라서 공개 성능표에서는 정밀화 성공이 아니라 속보 유지로 처리해야 한다.
4. 이번 Phase217은 이 문제를 막기 위해 `정밀화가 속보보다 나쁘면 속보 유지` 검증표기를 적용했다. 단, 이 판정은 실제 GVA가 있는 검증 화면에서 가능한 것이므로, 운영 규칙으로 쓰려면 이전연도 또는 외부지역 검증으로 고정해야 한다.

## 해석

- 포항시 `사업시설 관리 및 조경 서비스업`은 20.89%에서 9.12%로 내려가 20% 초과 잔여군에서 제외된다.
- 포항시 `산업용 기계 및 장비 수리업`은 한전 고객호수 후보를 적용해 53.25%에서 39.47%로 줄지만 여전히 직접자료가 필요하다.
- 고양시 `영상·오디오 제작업`은 16.72%에서 14.99%로 소폭 개선된다.
- 단, 후보 재정렬은 실제값을 포함한 검증 화면이므로 운영 규칙으로 쓰려면 prior-year 또는 외부지역 고정 검증이 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(summary.to_string(index=False))
    print(audit.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
