from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, ROOT, read_csv, write_csv, write_json


REPORT_PATH = ROOT / "reports" / "structural_feature_phase0_readiness.md"
WORKSTREAM_REPORT_PATH = ROOT / "reports" / "next_structural_feature_workstreams.md"
MANIFEST_PATH = PROCESSED_DIR / "structural_phase0_restart_manifest.json"
GATE_PATH = PROCESSED_DIR / "structural_phase0_source_gates.csv"
BUNDLE_PATH = PROCESSED_DIR / "structural_phase0_bundle_registry.csv"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def passfail(value: bool | str | None) -> str:
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    if value in {"pass", "partial", "fail", "not_started", "not_applicable"}:
        return str(value)
    return "unknown"


def source_gate_rows() -> list[dict[str, Any]]:
    factory = load_json(PROCESSED_DIR / "factory_ml_readiness.json")
    industrial = load_json(PROCESSED_DIR / "industrial_complex_ml_readiness.json")
    building = load_json(PROCESSED_DIR / "buildinghub_final_ml_readiness.json")
    building_route = load_json(PROCESSED_DIR / "buildinghub_source_final_status.json")
    structural_inventory = read_csv(PROCESSED_DIR / "structural_source_inventory.csv") if (PROCESSED_DIR / "structural_source_inventory.csv").exists() else []
    business_scores = read_csv(PROCESSED_DIR / "business_employment_source_scores.csv") if (PROCESSED_DIR / "business_employment_source_scores.csv").exists() else []

    factory_rows = [r for r in structural_inventory if "factory" in r.get("source_id", "")]
    industrial_rows = [r for r in structural_inventory if "industrial_complex" in r.get("source_id", "")]
    factory_real_rows = sum(int(r.get("rows_downloaded") or 0) for r in factory_rows)
    industrial_real_rows = sum(int(r.get("rows_downloaded") or 0) for r in industrial_rows)
    business_best_score = max((float(r.get("weighted_score") or 0) for r in business_scores), default=0.0)
    building_gates = building.get("gates", {})

    rows = [
        {
            "source_group": "factory_registration",
            "priority": 1,
            "target_sector": "C00",
            "source_role": "manufacturing_stock_flow_scale",
            "phase0_status": "development_only",
            "access": passfail(factory.get("gates", {}).get("access")),
            "historical": passfail(factory.get("gates", {}).get("historical_coverage")),
            "region": passfail(factory.get("gates", {}).get("regional_coverage")),
            "crosswalk": passfail(factory.get("gates", {}).get("region_crosswalk")),
            "vintage": passfail(factory.get("gates", {}).get("vintage_and_eligibility")),
            "eligibility": "partial",
            "quality": passfail(factory.get("gates", {}).get("quality")),
            "feature_table": passfail(factory.get("gates", {}).get("feature_readiness")),
            "real_rows_observed": factory.get("real_rows_observed_or_downloaded", factory_real_rows),
            "coverage_basis": "sample/file rows only; national sigungu coverage not audited",
            "blocking_issue": "historical reconstruction, full regional coverage, official crosswalk, and quality gates are incomplete",
            "next_action": "Build full factory snapshot inventory and validate address-to-sigungu/KSIC schema before C1/C3/C4/C5 bundles",
        },
        {
            "source_group": "industrial_complex_activity",
            "priority": 2,
            "target_sector": "C00",
            "source_role": "manufacturing_activity_production_exports_employment",
            "phase0_status": "development_only",
            "access": passfail(industrial.get("gates", {}).get("access")),
            "historical": passfail(industrial.get("gates", {}).get("historical_coverage")),
            "region": passfail(industrial.get("gates", {}).get("regional_coverage")),
            "crosswalk": passfail(industrial.get("gates", {}).get("region_crosswalk")),
            "vintage": passfail(industrial.get("gates", {}).get("vintage_and_eligibility")),
            "eligibility": "partial",
            "quality": passfail(industrial.get("gates", {}).get("quality")),
            "feature_table": passfail(industrial.get("gates", {}).get("feature_readiness")),
            "real_rows_observed": industrial.get("real_rows_observed_or_downloaded", industrial_real_rows),
            "coverage_basis": "file sample observed; complex-to-sigungu allocation not implemented",
            "blocking_issue": "industrial-complex geography allocation and historical publication lag are not audited",
            "next_action": "Create complex-to-sigungu allocation table and production/export/employment long feature table",
        },
        {
            "source_group": "building_activity",
            "priority": 3,
            "target_sector": "F00,L00",
            "source_role": "construction_pipeline_real_estate_supply",
            "phase0_status": "blocked",
            "access": passfail(building_gates.get("access") == "pass"),
            "historical": "partial",
            "region": "partial",
            "crosswalk": "partial",
            "vintage": "partial",
            "eligibility": "fail",
            "quality": "fail",
            "feature_table": "partial",
            "real_rows_observed": len(read_csv(PROCESSED_DIR / "buildinghub_feature_table.csv")) if (PROCESSED_DIR / "buildinghub_feature_table.csv").exists() else 0,
            "coverage_basis": "pilot historical inventory only",
            "blocking_issue": building_route.get("reason") or building.get("reason") or "event-date filter and nationwide route are not selected",
            "next_action": "Do not run nationwide row collection until bulk route or broad-collection post-filter pilot is manually approved",
        },
        {
            "source_group": "business_employment_activity",
            "priority": 4,
            "target_sector": "all,C00,G00,I00,F00",
            "source_role": "regional_business_employment_activity",
            "phase0_status": "prospective_only",
            "access": "partial",
            "historical": "partial",
            "region": "partial",
            "crosswalk": "unknown",
            "vintage": "unknown",
            "eligibility": "unknown",
            "quality": "unknown",
            "feature_table": "fail",
            "real_rows_observed": 0,
            "coverage_basis": f"source scoring only; best score {business_best_score:.0f}/100",
            "blocking_issue": "source choice, publication lag, industry mapping, and sigungu feature table are not fixed",
            "next_action": "Select one business/employment source and build first-eligible-period aware long feature table",
        },
        {
            "source_group": "electricity_pipeline",
            "priority": 0,
            "target_sector": "interaction_only",
            "source_role": "auxiliary_activity_intensity",
            "phase0_status": "retained_auxiliary_only",
            "access": "pass",
            "historical": "pass",
            "region": "pass",
            "crosswalk": "pass",
            "vintage": "pass",
            "eligibility": "pass",
            "quality": "pass",
            "feature_table": "pass",
            "real_rows_observed": len(read_csv(PROCESSED_DIR / "municipality_electricity_features_2021_2023.csv")) if (PROCESSED_DIR / "municipality_electricity_features_2021_2023.csv").exists() else 0,
            "coverage_basis": "historical KEPCO panel exists, but electricity-only correction is closed",
            "blocking_issue": "cannot be standalone challenger; may be used only after structural source is eligible",
            "next_action": "Use only as intensity/interaction feature after C1/C3/A4 structural baseline is frozen",
        },
    ]
    for row in rows:
        required = [row[k] for k in ("access", "historical", "region", "crosswalk", "vintage", "eligibility", "quality", "feature_table")]
        row["ml_ready"] = "Y" if all(v == "pass" for v in required) and row["source_group"] != "electricity_pipeline" else "N"
        row["as_of"] = now()
    return rows


def bundle_rows(gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    status = {row["source_group"]: row["phase0_status"] for row in gates}
    specs = [
        ("C00", "C0", "Global only", [], "champion_only"),
        ("C00", "C1", "Global + factory registration", ["factory_registration"], "blocked_until_factory_ml_ready"),
        ("C00", "C2", "Global + industrial complex activity", ["industrial_complex_activity"], "blocked_until_industrial_complex_ml_ready"),
        ("C00", "C3", "Global + factory + industrial complex", ["factory_registration", "industrial_complex_activity"], "blocked_until_C1_C2_sources_ml_ready"),
        ("C00", "C4", "Global + factory + electricity intensity", ["factory_registration", "electricity_pipeline"], "blocked_until_factory_ml_ready"),
        ("C00", "C5", "Global + factory + industrial complex + electricity intensity", ["factory_registration", "industrial_complex_activity", "electricity_pipeline"], "blocked_until_C3_sources_ml_ready"),
        ("F00,L00", "BL0", "Global only", [], "champion_only"),
        ("F00,L00", "BL1", "Global + building permits", ["building_activity"], "blocked_until_building_ml_ready"),
        ("F00,L00", "BL2", "Global + construction starts", ["building_activity"], "blocked_until_building_ml_ready"),
        ("F00,L00", "BL3", "Global + approvals", ["building_activity"], "blocked_until_building_ml_ready"),
        ("F00,L00", "BL4", "Global + permit + start", ["building_activity"], "blocked_until_building_ml_ready"),
        ("F00,L00", "BL5", "Global + permit + start + approval", ["building_activity"], "blocked_until_building_ml_ready"),
        ("all", "A0", "Global only", [], "champion_only"),
        ("all", "A1", "Global + business activity", ["business_employment_activity"], "blocked_until_business_activity_ml_ready"),
        ("all", "A2", "Global + employment activity", ["business_employment_activity"], "blocked_until_employment_activity_ml_ready"),
        ("all", "A3", "Global + building activity", ["building_activity"], "blocked_until_building_ml_ready"),
        ("all", "A4", "Global + business + employment", ["business_employment_activity"], "blocked_until_business_employment_ml_ready"),
        ("all", "A5", "Global + business + employment + electricity", ["business_employment_activity", "electricity_pipeline"], "blocked_until_A4_structural_baseline_frozen"),
    ]
    out = []
    for sector, bundle, definition, prereqs, blocked_reason in specs:
        eligible = bool(prereqs) and all(status.get(item) == "ml_ready" for item in prereqs if item != "electricity_pipeline")
        if "electricity_pipeline" in prereqs and len(prereqs) == 1:
            eligible = False
        out.append(
            {
                "target_sector": sector,
                "bundle": bundle,
                "definition": definition,
                "required_sources": ",".join(prereqs) if prereqs else "",
                "model_classes_allowed": "Ridge,ElasticNet" if prereqs else "not_applicable",
                "phase1_eligible": "Y" if eligible else "N",
                "status": "eligible_for_preregistered_ml" if eligible else blocked_reason,
                "electricity_role": "interaction_only" if "electricity_pipeline" in prereqs else "not_used",
            }
        )
    return out


def write_report(gates: list[dict[str, Any]], bundles: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    lines = [
        "# Structural Feature Phase 0 Readiness",
        "",
        "## 실행 요약",
        "",
        "전력 단독 residual correction은 `closed_no_confirmatory_challenger`로 종료됐고, 차기 실험은 structural source가 ML-ready gate를 통과한 뒤에만 시작한다. 이번 Phase 0 판정에서는 공장등록, 산업단지, 건축, 사업체·고용 중 어느 source도 아직 ML-ready가 아니다.",
        "",
        f"- restart_decision: `{manifest['restart_decision']}`",
        f"- operating_policy: `{manifest['operating_policy']}`",
        f"- eligible_structural_sources: `{manifest['eligible_structural_sources']}`",
        f"- same_actual_retuning_allowed: `{str(manifest['same_actual_retuning_allowed']).lower()}`",
        "",
        "## Source Gate Matrix",
        "",
        "| source | status | access | historical | region | crosswalk | vintage | eligibility | quality | feature table | next action |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in gates:
        lines.append(
            f"| {row['source_group']} | {row['phase0_status']} | {row['access']} | {row['historical']} | {row['region']} | {row['crosswalk']} | {row['vintage']} | {row['eligibility']} | {row['quality']} | {row['feature_table']} | {row['next_action']} |"
        )
    lines.extend(
        [
            "",
            "## Bundle Eligibility",
            "",
            "| sector | bundle | definition | required sources | eligible | status | electricity role |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in bundles:
        lines.append(f"| {row['target_sector']} | {row['bundle']} | {row['definition']} | {row['required_sources']} | {row['phase1_eligible']} | {row['status']} | {row['electricity_role']} |")
    lines.extend(
        [
            "",
            "## 운영 결론",
            "",
            "1. `global + electricity only`, R2/R3b 파생형, 전력 혼합 정책은 차기 후보에서 제외한다.",
            "2. 전력은 공장등록·산업단지·사업체·고용 source가 먼저 통과한 뒤 intensity 또는 interaction 변수로만 평가한다.",
            "3. 2022~2023 actual은 development actual로 이미 사용됐으므로, 새 structural policy의 confirmatory 근거가 될 수 없다.",
            "4. 미사용 official actual은 frozen challenger, frozen feature bundle, frozen model procedure, frozen gates, committed manifest가 있을 때만 confirmatory로 사용한다.",
            "",
            "## 다음 작업 우선순위",
            "",
            "1. 공장등록: 전체 snapshot의 주소-시군구 crosswalk와 KSIC/종업원/면적 schema를 확정한다.",
            "2. 산업단지: 단지-시군구 allocation과 생산·수출·고용 long feature table을 만든다.",
            "3. 건축HUB: broad collection + event-date post-filter pilot은 수동 승인 후 작은 표본으로만 수행한다.",
            "4. 사업체·고용: 전국사업체조사, LOCALDATA 대체 source, 고용보험 source 중 하나를 선택해 first eligible period를 구현한다.",
            "",
            "## 산출물",
            "",
            f"- `{GATE_PATH.relative_to(ROOT)}`",
            f"- `{BUNDLE_PATH.relative_to(ROOT)}`",
            f"- `{MANIFEST_PATH.relative_to(ROOT)}`",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_workstream_pointer() -> None:
    if not WORKSTREAM_REPORT_PATH.exists():
        return
    text = WORKSTREAM_REPORT_PATH.read_text(encoding="utf-8")
    marker = "## Phase 0 Structural Source Gate"
    block = "\n".join(
        [
            marker,
            "",
            "최신 Phase 0 판정은 `reports/structural_feature_phase0_readiness.md`에 별도 정리했다. 현재 ML 재개 판단은 `blocked_no_ml_ready_structural_source`이며, 전력 feature는 standalone correction이 아니라 structural source 통과 이후의 interaction/auxiliary 변수로만 유지한다.",
            "",
        ]
    )
    if marker in text:
        head = text.split(marker, 1)[0].rstrip()
        WORKSTREAM_REPORT_PATH.write_text(f"{head}\n\n{block}", encoding="utf-8")
    else:
        WORKSTREAM_REPORT_PATH.write_text(f"{text.rstrip()}\n\n{block}", encoding="utf-8")


def main() -> int:
    gates = source_gate_rows()
    bundles = bundle_rows(gates)
    eligible_sources = [row["source_group"] for row in gates if row["ml_ready"] == "Y"]
    manifest = {
        "as_of": now(),
        "code_commit_hash": git_hash(),
        "operating_policy": "global",
        "champion": "global",
        "restart_decision": "blocked_no_ml_ready_structural_source",
        "eligible_structural_sources": len(eligible_sources),
        "eligible_source_groups": eligible_sources,
        "electricity_only_policy_status": "closed_no_confirmatory_challenger",
        "electricity_standalone_candidate_allowed": False,
        "electricity_allowed_roles": ["auxiliary_feature", "interaction_feature", "activity_intensity_feature"],
        "same_actual_retuning_allowed": False,
        "primary_model": "Ridge",
        "optional_secondary_model": "ElasticNet",
        "ridge_alpha_grid": [0.1, 1.0, 10.0, 100.0],
        "maximum_C00_bundles": 6,
        "maximum_F00_L00_bundles": 6,
        "maximum_all_bundles": 6,
        "bootstrap_iterations_required": 2000,
        "placebo_iterations_required_per_type": 1000,
        "selection_aware_p_improve_threshold": 0.9,
        "unused_actual_policy": "do_not_open_for_confirmatory_until_frozen_challenger_manifest_committed",
    }
    write_csv(GATE_PATH, gates)
    write_csv(BUNDLE_PATH, bundles)
    write_json(MANIFEST_PATH, manifest)
    write_report(gates, bundles, manifest)
    append_workstream_pointer()
    print(f"source gates: {len(gates)}")
    print(f"bundle rows: {len(bundles)}")
    print(f"restart decision: {manifest['restart_decision']}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
