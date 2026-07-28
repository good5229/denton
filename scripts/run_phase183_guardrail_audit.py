#!/usr/bin/env python3
"""Phase183: guardrail audit for subsequent GVA refinement experiments.

This is a pre-flight audit, not a prediction update.  It checks that the current
best candidate and the residual routebook satisfy the rules needed before we
attach newly collected activity data:

- target actual is audit-only in Phase179;
- no Phase179 worsening versus Phase124/177;
- all residual >20% cells are reclassified as improvement-needed;
- Phase182 source packs do not preserve stale "no additional data needed" logic;
- KOBIS is not auto-adopted when its validation did not beat the generic track.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase183_guardrail_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase183_guardrail_audit.md"

P179_MANIFEST = DATA / "phase179_metadata_guarded_middle_gate" / "execution_manifest.json"
P179_WORSE_177 = DATA / "phase179_metadata_guarded_middle_gate" / "phase179_worsened_vs_phase177_cells.csv"
P179_WORSE_124 = DATA / "phase179_metadata_guarded_middle_gate" / "phase179_worsened_vs_phase124_cells.csv"
P179_APPLIED = DATA / "phase179_metadata_guarded_middle_gate" / "phase179_applied_cells.csv"
P179_REGISTRY = DATA / "phase179_metadata_guarded_middle_gate" / "phase179_metadata_guarded_registry.csv"
P178_REGISTRY = DATA / "phase178_middle_only_gate_diagnostic" / "phase178_middle_only_gate_registry.csv"
P180_RESIDUAL = DATA / "phase180_residual_source_retriage" / "phase180_residual_cells_retriaged.csv"
P182_ROUTEBOOK = DATA / "phase182_residual_improvement_routebook" / "phase182_residual_routebook.csv"
P182_SOURCE = DATA / "phase182_residual_improvement_routebook" / "phase182_source_pack_priority.csv"
P136_KOBIS = DATA / "phase136_kobis_boxoffice_temporal_proxy" / "phase136_goyang_j59_route_decision.csv"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def md_table(rows: list[dict[str, Any]], cols: list[tuple[str, str]]) -> str:
    out = ["| " + " | ".join(h for _, h in cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        vals = []
        for key, _ in cols:
            val = str(row.get(key, ""))
            vals.append(val.replace("|", "/").replace("\n", " ")[:260])
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    p179_manifest = read_json(P179_MANIFEST)
    worse177 = read_csv(P179_WORSE_177)
    worse124 = read_csv(P179_WORSE_124)
    applied = read_csv(P179_APPLIED)
    registry = read_csv(P179_REGISTRY)
    p178 = read_csv(P178_REGISTRY)
    residual = read_csv(P180_RESIDUAL)
    routebook = read_csv(P182_ROUTEBOOK)
    source = read_csv(P182_SOURCE)
    kobis = read_csv(P136_KOBIS)

    checks: list[dict[str, Any]] = []

    checks.append(
        {
            "check_id": "P179_TARGET_ACTUAL_AUDIT_ONLY",
            "scope": "Phase179 route decision",
            "verdict": verdict(p179_manifest.get("target_actual_use") == "audit only"),
            "evidence": f"manifest target_actual_use={p179_manifest.get('target_actual_use', '<missing>')}",
            "required_action_if_fail": "Phase179 decision logic must be re-read and any target-actual-driven adoption removed.",
        }
    )

    checks.append(
        {
            "check_id": "P179_NO_WORSENING_VS_177",
            "scope": "Phase179 applied cells",
            "verdict": verdict(worse177.empty),
            "evidence": f"worsened_vs_phase177_rows={len(worse177)}",
            "required_action_if_fail": "Revert worsening rows or add independent validation gate before adoption.",
        }
    )
    checks.append(
        {
            "check_id": "P179_NO_WORSENING_VS_124",
            "scope": "Phase179 applied cells",
            "verdict": verdict(worse124.empty),
            "evidence": f"worsened_vs_phase124_rows={len(worse124)}",
            "required_action_if_fail": "Do not use candidate as operational baseline until no-worse constraint is restored.",
        }
    )

    if not applied.empty:
        applied_for_gate = applied.copy()
        if "phase178_route" not in applied_for_gate.columns and not p178.empty:
            key = ["city", "parent_code", "middle_code"]
            if set(key + ["phase178_route"]).issubset(p178.columns):
                applied_for_gate = applied_for_gate.merge(p178[key + ["phase178_route"]], on=key, how="left")
        required = {
            "phase177_route": "기준 유지",
            "phase178_route": "외부검증 통과 중분류 독립 peer 배분",
            "public_claim_track": "추가개선 필요",
            "operational_track": "운영 개선 필요",
        }
        mismatches = 0
        for col, expected in required.items():
            if col not in applied_for_gate.columns:
                mismatches += len(applied_for_gate)
            else:
                mismatches += int((applied_for_gate[col] != expected).sum())
        if "phase92_queue" in applied_for_gate.columns:
            mismatches += int((~applied_for_gate["phase92_queue"].isin(["주의", "취약"])).sum())
        checks.append(
            {
                "check_id": "P179_APPLIED_GATE_CONDITIONS",
                "scope": "Phase179 6 adopted cells",
                "verdict": verdict(mismatches == 0),
                "evidence": f"applied_rows={len(applied)}, gate_mismatches={mismatches}",
                "required_action_if_fail": "Recompute applied set from explicit gate columns only.",
            }
        )
    else:
        checks.append(
            {
                "check_id": "P179_APPLIED_GATE_CONDITIONS",
                "scope": "Phase179 adopted cells",
                "verdict": "FAIL",
                "evidence": "phase179_applied_cells.csv missing or empty",
                "required_action_if_fail": "Regenerate Phase179 before using it as baseline.",
            }
        )

    if not residual.empty:
        residual_bad = residual[
            (residual.get("phase179_error_rate_pct", pd.Series(dtype=float)) > 20)
            & (
                (residual.get("updated_public_claim_track", pd.Series(dtype=str)) != "추가개선 필요")
                | (residual.get("updated_operational_track", pd.Series(dtype=str)) != "운영 개선 필요")
            )
        ]
        checks.append(
            {
                "check_id": "P180_RESIDUAL_RECLASSIFIED",
                "scope": "20%+ residual cells",
                "verdict": verdict(residual_bad.empty),
                "evidence": f"residual_rows={len(residual)}, not_reclassified_rows={len(residual_bad)}",
                "required_action_if_fail": "Every >20% residual cell must be treated as improvement-needed; no public accuracy claim.",
            }
        )
    else:
        residual_bad = pd.DataFrame()
        checks.append(
            {
                "check_id": "P180_RESIDUAL_RECLASSIFIED",
                "scope": "20%+ residual cells",
                "verdict": "FAIL",
                "evidence": "phase180 residual file missing",
                "required_action_if_fail": "Regenerate Phase180.",
            }
        )

    stale_terms = ["추가 자료 불필요", "현행유지가능", "정확도 주장 가능", "운영 적용 가능"]
    route_text_cols = [c for c in ["root_cause", "source_pack", "model_action", "api_dependency"] if c in routebook.columns]
    stale_route_rows = pd.DataFrame()
    if route_text_cols and not routebook.empty:
        mask = pd.Series(False, index=routebook.index)
        for c in route_text_cols:
            s = routebook[c].astype(str)
            for term in stale_terms:
                mask |= s.str.contains(term, regex=False)
        stale_route_rows = routebook[mask]
    checks.append(
        {
            "check_id": "P182_NO_STALE_ROUTEBOOK_LOGIC",
            "scope": "Phase182 residual routebook",
            "verdict": verdict(not routebook.empty and stale_route_rows.empty),
            "evidence": f"routebook_rows={len(routebook)}, stale_term_rows={len(stale_route_rows)}",
            "required_action_if_fail": "Remove old no-data-needed/public-claim labels from all residual guidance.",
        }
    )

    source_has_action = not source.empty and {"source_pack", "api_dependency", "model_action"}.issubset(source.columns)
    checks.append(
        {
            "check_id": "P182_SOURCE_PACK_ACTIONABLE",
            "scope": "Phase182 source priority",
            "verdict": verdict(source_has_action),
            "evidence": f"source_rows={len(source)}, required_columns_present={source_has_action}",
            "required_action_if_fail": "Each residual source pack needs source, API dependency and model action.",
        }
    )

    if not kobis.empty and "adopt_for_j59_temporal_nowcast" in kobis.columns and "error_reduction_eok" in kobis.columns:
        bad_kobis = kobis[(kobis["adopt_for_j59_temporal_nowcast"].astype(str).str.lower().isin(["true", "1"])) & (kobis["error_reduction_eok"] <= 0)]
        checks.append(
            {
                "check_id": "KOBIS_NO_AUTO_ADOPTION",
                "scope": "Phase136 KOBIS J59 guard",
                "verdict": verdict(bad_kobis.empty),
                "evidence": f"kobis_vintages={len(kobis)}, invalid_adoptions={len(bad_kobis)}",
                "required_action_if_fail": "Reject KOBIS for J59 vintage unless it beats generic seasonal share.",
            }
        )
    else:
        checks.append(
            {
                "check_id": "KOBIS_NO_AUTO_ADOPTION",
                "scope": "Phase136 KOBIS J59 guard",
                "verdict": "FAIL",
                "evidence": "KOBIS decision file missing or columns absent",
                "required_action_if_fail": "Recreate Phase136 or exclude KOBIS from the next model.",
            }
        )

    if not registry.empty and {"actual_gva_eok", "phase179_predicted_gva_eok", "phase179_error_gva_eok", "phase179_error_rate_pct"}.issubset(registry.columns):
        calc_error = (registry["phase179_predicted_gva_eok"] - registry["actual_gva_eok"]).abs()
        calc_rate = calc_error / registry["actual_gva_eok"].abs() * 100
        error_mismatch = int(((calc_error - registry["phase179_error_gva_eok"]).abs() > 1e-6).sum())
        rate_mismatch = int(((calc_rate - registry["phase179_error_rate_pct"]).abs() > 1e-6).sum())
        checks.append(
            {
                "check_id": "P179_ERROR_FORMULA",
                "scope": "Phase179 registry arithmetic",
                "verdict": verdict(error_mismatch == 0 and rate_mismatch == 0),
                "evidence": f"rows={len(registry)}, error_mismatch={error_mismatch}, rate_mismatch={rate_mismatch}",
                "required_action_if_fail": "Fix error formula before showing values in reports/posters.",
            }
        )
    else:
        checks.append(
            {
                "check_id": "P179_ERROR_FORMULA",
                "scope": "Phase179 registry arithmetic",
                "verdict": "FAIL",
                "evidence": "required registry columns missing",
                "required_action_if_fail": "Regenerate Phase179 registry.",
            }
        )

    checks_df = pd.DataFrame(checks)
    checks_path = OUT / "phase183_guardrail_checks.csv"
    checks_df.to_csv(checks_path, index=False, encoding="utf-8-sig")

    failures = checks_df[checks_df["verdict"] != "PASS"].copy()
    failures_path = OUT / "phase183_guardrail_failures.csv"
    failures.to_csv(failures_path, index=False, encoding="utf-8-sig")

    next_rules = [
        {
            "rule": "새 활동자료는 먼저 외부 도시/상위 집계 검증",
            "implementation": "고양·포항 actual 오차 감소만으로 채택 금지. 최소한 LOO 또는 상위산업 집계검증 통과.",
        },
        {
            "rule": "20% 초과 잔여 셀은 공개성과 주장 금지",
            "implementation": "포스터/보고서에서는 개선 필요 또는 진단 대상으로 표시.",
        },
        {
            "rule": "속보성과 정밀화 분리",
            "implementation": "공표시점 불명 자료는 속보 트랙 제외. 정밀화 트랙에서만 사용.",
        },
        {
            "rule": "업종군 일괄 보정 금지",
            "implementation": "C00/MN0/ERS 같은 대블록 전체가 아니라 중분류별 활동자료로 라우팅.",
        },
        {
            "rule": "KOBIS 같은 직관적 자료도 검증 후 채택",
            "implementation": "Phase136처럼 기존 계절비중보다 못하면 사용 가능한 API라도 기각.",
        },
    ]
    rules_path = OUT / "phase183_next_experiment_rules.csv"
    pd.DataFrame(next_rules).to_csv(rules_path, index=False, encoding="utf-8-sig")

    report = f"""# Phase183 다음 개선 실험 사전 검증 감사

## 목적

Phase183은 새 총부가가치(GVA) 예측값을 만들지 않는다. 대신 Phase179/180/182가 다음 개선 실험의 안전한 출발점인지 검사한다. 특히 target actual 유출, 낡은 `현행유지가능` 판정의 잔존, KOBIS 같은 보조지표의 무검증 채택을 막는 것이 목적이다.

## 검증 결과

{md_table(checks, [
    ("check_id", "검증항목"),
    ("scope", "범위"),
    ("verdict", "판정"),
    ("evidence", "증거"),
    ("required_action_if_fail", "실패 시 조치"),
])}

## 실패 항목

{md_table(failures.to_dict("records"), [
    ("check_id", "검증항목"),
    ("evidence", "증거"),
    ("required_action_if_fail", "조치"),
]) if not failures.empty else "모든 사전 검증 항목이 통과했다."}

## 다음 실험 규칙

{md_table(next_rules, [
    ("rule", "규칙"),
    ("implementation", "적용 방식"),
])}

## 해석

1. Phase179는 현재 파일 기준으로 target actual을 적용 판단에 쓰지 않고, Phase124/177 대비 악화 셀도 없다.
2. Phase180의 20% 초과 잔여 셀은 모두 추가개선/운영개선 대상으로 재분류되어야 하며, Phase183은 이 조건을 검사한다.
3. Phase182 라우트북은 다음 API 수집이 열릴 때 바로 연결할 수 있는 작업지시서 역할을 한다. 다만 신규 자료는 반드시 외부 검증 또는 상위 집계검증을 통과해야 한다.
4. KOBIS는 사용 가능하지만, 기존 Phase136 검증에서는 고양시 J59 시간축 개선에 실패했으므로 자동 채택하지 않는다.

## 산출물

- 검증 체크: `{checks_path.relative_to(ROOT)}`
- 실패 항목: `{failures_path.relative_to(ROOT)}`
- 다음 실험 규칙: `{rules_path.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")

    manifest = {
        "phase": 183,
        "checks": int(len(checks_df)),
        "failures": int(len(failures)),
        "outputs": [
            str(checks_path.relative_to(ROOT)),
            str(failures_path.relative_to(ROOT)),
            str(rules_path.relative_to(ROOT)),
            str(REPORT.relative_to(ROOT)),
        ],
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
