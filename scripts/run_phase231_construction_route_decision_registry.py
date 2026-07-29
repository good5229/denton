#!/usr/bin/env python3
"""Phase231: construction route decision registry.

Collect construction-specific experiments into one decision registry so the
active WAPE goal cannot accidentally overclaim rejected routes.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase231_construction_route_decision_registry"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase231_construction_route_decision_registry.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None, digits: int = 3) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "_해당 없음_\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("WAPE", "%", "억원", "개", "APE", "pp")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            v = row.get(key, "")
            if isinstance(v, (float, np.floating)):
                vals.append(f"{float(v):,.{digits}f}")
            elif isinstance(v, (int, np.integer)):
                vals.append(f"{int(v):,}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    # Phase227: local 41/42 middle split proof.
    p227 = read_csv(DATA / "phase227_construction_building_activity_gate" / "phase227_construction_gate_overall.csv")
    p227_base = p227[p227["scenario"].eq("현행 소분류 합산 기준")].iloc[0]
    p227_gate = p227[p227["scenario"].eq("건축활동 gate 선택")].iloc[0]
    rows.append(
        {
            "route_id": "construction_41_42_building_activity_gate",
            "route_layer": "중분류 내부 분할",
            "signal_family": "건축활동",
            "scope": "고양·포항 41/42 local proof",
            "baseline_wape_pct": float(p227_base["wape_pct"]),
            "candidate_wape_pct": float(p227_gate["wape_pct"]),
            "guardrail_pass": True,
            "decision": "후보유지",
            "adoption_level": "local_proof_only",
            "reason": "2개 도시 41/42 분할은 10% 이하이나 threshold 사후선택 가능성과 외부 holdout 부족",
            "allowed_use": "건설업 내부 세부구조 진단 후보",
            "forbidden_use": "전국 시군구 건설업 공간배분 route로 주장 금지",
            "next_required_evidence": "top1/top5/top28 수집도시 또는 다른 연도 holdout에서 threshold 사전고정 검증",
            "source_report": "reports/partial_statistics_estimation_phase227_construction_building_activity_gate.md",
        }
    )

    # Phase228: BuildingHUB single spatial replacement.
    p228 = read_csv(DATA / "phase228_construction_buildinghub_sample_spatial_holdout" / "phase228_seoul_pair_candidate_overall.csv")
    p228_base = p228[p228["candidate_id"].eq("baseline_current_share")].iloc[0]
    p228_best_signal = p228[p228["candidate_id"].ne("baseline_current_share")].sort_values("pooled_wape_pct").iloc[0]
    rows.append(
        {
            "route_id": "construction_buildinghub_single_spatial_share",
            "route_layer": "시군구 대분류 공간배분",
            "signal_family": "건축활동",
            "scope": "서울 강남·종로 pair 2021~2023",
            "baseline_wape_pct": float(p228_base["pooled_wape_pct"]),
            "candidate_wape_pct": float(p228_best_signal["pooled_wape_pct"]),
            "guardrail_pass": False,
            "decision": "미채택",
            "adoption_level": "rejected_single_route",
            "reason": "건축활동 단일 share가 현행보다 크게 악화",
            "allowed_use": "민간건축 블록 후보의 원천자료",
            "forbidden_use": "건설업 전체 공간배분을 건축면적/건수 단일 share로 대체 금지",
            "next_required_evidence": "기존 share fallback과 블록별 제한혼합, 지역유형 gate 필요",
            "source_report": "reports/partial_statistics_estimation_phase228_construction_buildinghub_sample_spatial_holdout.md",
        }
    )

    # Phase229: BuildingHUB limited mix.
    p229 = read_csv(DATA / "phase229_construction_limited_building_mix" / "phase229_limited_mix_overall.csv")
    p229_best = p229.sort_values("pooled_wape_pct").iloc[0]
    rows.append(
        {
            "route_id": "construction_buildinghub_limited_mix",
            "route_layer": "시군구 대분류 공간배분",
            "signal_family": "건축활동",
            "scope": "서울 강남·종로 pair 2021~2023",
            "baseline_wape_pct": float(p229_best["baseline_pooled_wape_pct"]),
            "candidate_wape_pct": float(p229_best["pooled_wape_pct"]),
            "guardrail_pass": bool(p229_best["all_year_guardrail_pass"]),
            "decision": "미채택",
            "adoption_level": "rejected_guardrail",
            "reason": "pooled WAPE는 일부 개선되나 전연도 WAPE·최대APE guardrail 통과 후보 0개",
            "allowed_use": "정밀화 민간건축 보조 feature 후보",
            "forbidden_use": "평균 WAPE 개선을 성능개선으로 주장 금지",
            "next_required_evidence": "정비사업·PPS·토목과 블록 결합 후 rolling guardrail 재검증",
            "source_report": "reports/partial_statistics_estimation_phase229_construction_limited_building_mix.md",
        }
    )

    # Phase230: PPS pair mix.
    p230 = read_csv(DATA / "phase230_construction_pps_pair_mix" / "phase230_pps_pair_summary.csv")
    p230_base = p230[p230["mode"].eq("baseline")].iloc[0]
    p230_best = p230[p230["mode"].ne("baseline")].sort_values("wape_pct").iloc[0]
    rows.append(
        {
            "route_id": "construction_pps_public_works_mix",
            "route_layer": "시군구 대분류 공간배분",
            "signal_family": "PPS 공공공사",
            "scope": "서울 강남·종로 pair 2021",
            "baseline_wape_pct": float(p230_base["wape_pct"]),
            "candidate_wape_pct": float(p230_best["wape_pct"]),
            "guardrail_pass": bool(p230_best["guardrail_pass"]),
            "decision": "미채택",
            "adoption_level": "rejected_guardrail",
            "reason": "PPS가 강남 share를 낮추는 방향으로 작동해 현행보다 악화",
            "allowed_use": "공공·토목형 지역 전용 보조 feature 후보",
            "forbidden_use": "전국 공통 PPS 건설업 route 또는 민간건축형 지역 자동적용 금지",
            "next_required_evidence": "SOC·항만·산단·공공청사 등 공공·토목형 지역에서 별도 holdout 검증",
            "source_report": "reports/partial_statistics_estimation_phase230_construction_pps_pair_mix.md",
        }
    )

    # Nationwide PPS guardrail feasibility.
    pps = read_csv(ROOT / "nationwide" / "outputs" / "construction_pps_sigungu_spatial_summary.csv")
    pps_current = pps[pps["scenario"].eq("current_parent_control")].iloc[0]
    pps_guard = pps[pps["scenario"].eq("blend_current_0.98_pps_amount_share")].iloc[0]
    rows.append(
        {
            "route_id": "construction_pps_nationwide_partial_2023",
            "route_layer": "시군구 대분류 공간배분",
            "signal_family": "PPS 공공공사",
            "scope": "2023 부분기간 전국 일부 시도",
            "baseline_wape_pct": float(pps_current["wape_pct"]),
            "candidate_wape_pct": float(pps_guard["wape_pct"]),
            "guardrail_pass": True,
            "decision": "후보유지",
            "adoption_level": "feasibility_only",
            "reason": "일부 guardrail 후보는 있으나 2023 부분기간·전국 raw 불완전으로 운영 채택 불가",
            "allowed_use": "공공·토목형 보조 feature feasibility",
            "forbidden_use": "2021~2025 rolling 검증 전 PPS route 채택 주장 금지",
            "next_required_evidence": "2021~2025 전체 PPS raw 수집 후 out-of-year·지역유형별 guardrail",
            "source_report": "nationwide/construction_pps_sigungu_spatial_audit.md",
        }
    )

    # Lag share audit.
    rows.append(
        {
            "route_id": "construction_lag_share_refinement",
            "route_layer": "시군구 대분류 공간배분",
            "signal_family": "전년도 share",
            "scope": "전국 시군구 2021~2023",
            "baseline_wape_pct": 19.432,
            "candidate_wape_pct": 19.432,
            "guardrail_pass": False,
            "decision": "미채택",
            "adoption_level": "identity_rejected",
            "reason": "현재 예측 share가 전년도 actual share와 사실상 동일해 새 정보가 아님",
            "allowed_use": "fallback 기준",
            "forbidden_use": "성능개선 route로 주장 금지",
            "next_required_evidence": "신규 공간활동자료 필요",
            "source_report": "nationwide/construction_sigungu_share_refinement_audit.md",
        }
    )

    # Frontier / collection need.
    rows.append(
        {
            "route_id": "construction_staged_collection_frontier",
            "route_layer": "수집전략",
            "signal_family": "건축HUB·정비사업·PPS",
            "scope": "전국 건설업 오차기여 상위 시군구",
            "baseline_wape_pct": 20.675,
            "candidate_wape_pct": np.nan,
            "guardrail_pass": False,
            "decision": "수집필요",
            "adoption_level": "collection_plan",
            "reason": "WAPE 10% 이하에는 현재 절대오차의 51.6% 감축 필요. top52에서 75% 감축 가정 시 oracle 9.907%",
            "allowed_use": "수집 우선순위·상한 진단",
            "forbidden_use": "예측성능으로 주장 금지",
            "next_required_evidence": "top1/top5 pipeline 검증 후 top28→top52 확장",
            "source_report": "nationwide/construction_wape_reduction_frontier.md",
        }
    )

    reg = pd.DataFrame(rows)
    status_order = {"채택": 0, "후보유지": 1, "수집필요": 2, "미채택": 3}
    reg["decision_order"] = reg["decision"].map(status_order).fillna(9)
    reg["wape_delta_pp"] = reg["candidate_wape_pct"] - reg["baseline_wape_pct"]
    reg = reg.sort_values(["decision_order", "route_id"]).drop(columns=["decision_order"])

    summary = (
        reg.groupby(["decision", "route_layer"], as_index=False)
        .agg(route_count=("route_id", "count"))
        .sort_values(["decision", "route_layer"])
    )

    reg.to_csv(OUTDIR / "phase231_construction_route_decision_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase231_construction_route_decision_summary.csv", index=False, encoding="utf-8-sig")

    report = f"""# 건설업 route decision registry

생성시각: {CREATED_AT}

## 결론

- 현재 건설업은 시군구×업종 WAPE 10% 목표의 마지막 병목이다.
- 채택 가능한 건설업 대분류 공간배분 route는 아직 없다.
- 고양·포항 41/42 내부 분할은 건축활동 gate가 유망하지만 local proof에 그친다.
- BuildingHUB 단일/제한혼합, PPS 서울 pair, lag-share는 운영 route로 미채택한다.
- PPS는 공공·토목형 지역 보조 feature 후보, BuildingHUB는 민간건축·세부구조 보조 feature 후보로만 유지한다.
- 다음 실험은 지역유형 gate를 전제로 top1/top5→top28→top52 staged collection이다.

## decision summary

{md_table(summary, [("decision", "판정"), ("route_layer", "층위"), ("route_count", "route 수")])}

## route registry

{md_table(reg, [("route_id", "route"), ("route_layer", "층위"), ("signal_family", "신호군"), ("scope", "검증범위"), ("baseline_wape_pct", "기준 WAPE %"), ("candidate_wape_pct", "후보 WAPE %"), ("wape_delta_pp", "변화 pp"), ("guardrail_pass", "guardrail"), ("decision", "판정"), ("adoption_level", "채택수준"), ("reason", "사유")], digits=3)}

## 표현 원칙

- `채택`이 아닌 route는 포스터·보고서에서 성능개선으로 표현하지 않는다.
- pooled WAPE만 개선된 후보는 guardrail 실패 시 미채택으로 쓴다.
- 건설업 41/42 local proof는 세부구조 진단으로만 표현하고 전국 공간배분으로 일반화하지 않는다.
- PPS는 공공·토목형 지역 gate 안에서만 재검증한다.
- BuildingHUB는 민간건축/정밀화 보조 feature로만 유지한다.

## 다음 실험 요구사항

1. top1/top5 건설업 오차지역 BuildingHUB event 수집
2. 지역유형 gate 사전정의: 민간건축형, 공공·토목형, 혼합형, fallback형
3. 각 gate별 허용 feature 제한
4. rolling out-of-year로 threshold/혼합비 선택
5. WAPE, 10% 초과 셀, 20% 초과 셀, 최대 APE, 대형 actual 셀 절대오차 guardrail 동시 적용
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase231_construction_route_decision_registry.csv")


if __name__ == "__main__":
    main()
