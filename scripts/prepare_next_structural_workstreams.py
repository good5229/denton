from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from kosis_common import PROCESSED_DIR, ROOT, write_csv


REPORT_PATH = ROOT / "reports" / "next_structural_feature_workstreams.md"
PROTOCOL_PATH = ROOT / "reports" / "next_structural_feature_experiment_protocol.md"
STATUS_PATH = PROCESSED_DIR / "next_feature_source_status.csv"


TODAY = datetime.now().date().isoformat()


def status_rows() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "factoryon_factory_registration",
            "source_name": "FactoryOn 공장등록/공장기업 검색",
            "target_sector": "C00",
            "priority": 1,
            "access_status": "access_investigation",
            "download_status": "not_started",
            "parser_status": "not_started",
            "historical_coverage": "unknown",
            "regional_coverage": "unknown",
            "publication_lag_status": "unknown_requires_audit",
            "vintage_status": "not_implemented",
            "quality_status": "not_started",
            "ml_ready_status": "not_ready",
            "blocking_issue": "bulk endpoint and historical registration/closure dates not verified",
            "next_action": "Inspect FactoryOn network requests and alternative local-government factory registration files",
            "last_updated": TODAY,
        },
        {
            "source_id": "kicox_factory_registration_stats",
            "source_name": "한국산업단지공단_공장등록 현황 통계정보",
            "target_sector": "C00",
            "priority": 1,
            "access_status": "downloadable_but_empty_probe",
            "download_status": "schema_probe_downloaded",
            "parser_status": "blocked_empty_workbook",
            "historical_coverage": "not_verified",
            "regional_coverage": "not_verified",
            "publication_lag_status": "unknown_requires_audit",
            "vintage_status": "not_implemented",
            "quality_status": "blocked",
            "ml_ready_status": "not_ready",
            "blocking_issue": "downloaded workbook contains title rows only in prior probe",
            "next_action": "Reinspect workbook internals, query tables, connections, defined names, and source endpoint",
            "last_updated": TODAY,
        },
        {
            "source_id": "kicox_industrial_complex_trends",
            "source_name": "한국산업단지공단 국가산업단지 산업동향정보",
            "target_sector": "C00",
            "priority": 2,
            "access_status": "candidate",
            "download_status": "not_started",
            "parser_status": "not_started",
            "historical_coverage": "unknown",
            "regional_coverage": "requires_complex_to_sigungu_allocation",
            "publication_lag_status": "unknown_requires_audit",
            "vintage_status": "not_implemented",
            "quality_status": "not_started",
            "ml_ready_status": "not_ready",
            "blocking_issue": "complex code standardization and multi-sigungu allocation rule not built",
            "next_action": "Build industrial complex source inventory and allocation quality policy",
            "last_updated": TODAY,
        },
        {
            "source_id": "molit_building_permit_basic",
            "source_name": "국토교통부 건축인허가 기본개요/건축HUB",
            "target_sector": "F00,L00",
            "priority": 3,
            "access_status": "metadata_collected_source_file_pending",
            "download_status": "not_started",
            "parser_status": "not_started",
            "historical_coverage": "unknown",
            "regional_coverage": "expected_sigungu_if_bulk_available",
            "publication_lag_status": "unknown_requires_audit",
            "vintage_status": "not_implemented",
            "quality_status": "not_started",
            "ml_ready_status": "not_ready",
            "blocking_issue": "bulk/API access route and event date quality not verified",
            "next_action": "Confirm BuildingHub bulk or API access, then split permit/start/approval events",
            "last_updated": TODAY,
        },
        {
            "source_id": "business_employment_activity",
            "source_name": "사업체·고용 Activity 후보군",
            "target_sector": "all,C00,G00,I00,F00",
            "priority": 4,
            "access_status": "not_started",
            "download_status": "not_started",
            "parser_status": "not_started",
            "historical_coverage": "unknown",
            "regional_coverage": "unknown",
            "publication_lag_status": "unknown_requires_audit",
            "vintage_status": "not_implemented",
            "quality_status": "not_started",
            "ml_ready_status": "not_ready",
            "blocking_issue": "source choice not fixed",
            "next_action": "Compare employment insurance, business opening/closure, and workplace count sources",
            "last_updated": TODAY,
        },
        {
            "source_id": "card_sales_foot_traffic",
            "source_name": "카드매출·유동인구 후보군",
            "target_sector": "G00,I00,all",
            "priority": 5,
            "access_status": "not_started",
            "download_status": "not_started",
            "parser_status": "not_started",
            "historical_coverage": "unknown",
            "regional_coverage": "pilot_first",
            "publication_lag_status": "unknown_requires_audit",
            "vintage_status": "not_implemented",
            "quality_status": "not_started",
            "ml_ready_status": "not_ready",
            "blocking_issue": "national free source not fixed",
            "next_action": "Identify free/open pilot sources and mark non-generalizable pilot scope",
            "last_updated": TODAY,
        },
        {
            "source_id": "kepco_electricity_pipeline",
            "source_name": "KEPCO 시군구 전력사용량",
            "target_sector": "research_context",
            "priority": 0,
            "access_status": "active",
            "download_status": "downloaded_historical_panel",
            "parser_status": "implemented",
            "historical_coverage": "2021-2023 historical common panel in current repository",
            "regional_coverage": "sigungu_panel_available",
            "publication_lag_status": "implemented_for_current_vintage_selector",
            "vintage_status": "implemented",
            "quality_status": "active_monthly_audit_required",
            "ml_ready_status": "retained_for_combined_model_only",
            "blocking_issue": "electricity-only correction closed; must not trigger ML restart by itself",
            "next_action": "Continue monthly source manifest, schema drift, revision, lag, duplicate, and negative-value audits",
            "last_updated": TODAY,
        },
    ]


def factory_inventory() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "factoryon_factory_search",
            "source_name": "FactoryOn 공장(기업)검색",
            "source_url": "https://www.factoryon.go.kr/mobile/main/main.do",
            "provider": "한국산업단지공단",
            "access_status": "access_investigation",
            "expected_fields": "factory_id,factory_name,address,industry_code,status,registration_date,closure_date,employee_count,area,industrial_complex_code",
            "historical_stock_feasibility": "requires_registration_and_closure_dates",
            "blocking_issue": "bulk download/API endpoint not verified",
        },
        {
            "source_id": "data_go_kr_kicox_factory_registration_stats",
            "source_name": "공장등록 현황 통계정보",
            "source_url": "https://www.data.go.kr/data/3041646/fileData.do",
            "provider": "한국산업단지공단",
            "access_status": "schema_probe_downloaded_empty_workbook",
            "expected_fields": "sido,sigungu,industry,factory_count,area,employee",
            "historical_stock_feasibility": "not_available_until_real_rows_found",
            "blocking_issue": "prior workbook probe found title rows only",
        },
        {
            "source_id": "local_government_factory_registration_files",
            "source_name": "지자체별 공장등록 현황",
            "source_url": "multiple_local_government_open_data_pages",
            "provider": "local_governments",
            "access_status": "not_started",
            "expected_fields": "factory_name,address,industry_code,registration_date,status,employee_count,area",
            "historical_stock_feasibility": "depends_on_snapshot_frequency_and_dates",
            "blocking_issue": "national coverage and schema consistency unknown",
        },
    ]


def industrial_complex_inventory() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "data_go_kr_kicox_national_industrial_complex_trends",
            "source_name": "국가산업단지 산업동향정보",
            "source_url": "https://www.data.go.kr/data/3042071/fileData.do",
            "provider": "한국산업단지공단",
            "access_status": "candidate_not_collected",
            "periodicity": "unknown_until_collection",
            "expected_fields": "complex_code,reference_period,operating_company_count,employment,production,exports,utilization_rate",
            "sigungu_allocation_need": "high",
            "blocking_issue": "complex-to-sigungu allocation and publication lag not audited",
        },
        {
            "source_id": "kicox_industrial_complex_statistics_publications",
            "source_name": "전국산업단지 통계/분기별 산업단지 동향",
            "source_url": "https://www.kicox.or.kr/",
            "provider": "한국산업단지공단",
            "access_status": "not_started",
            "periodicity": "quarterly_or_annual_expected",
            "expected_fields": "complex_name,company_count,employment,production,exports,area",
            "sigungu_allocation_need": "high",
            "blocking_issue": "file catalog and historical archive not enumerated",
        },
    ]


def building_inventory() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "data_go_kr_molit_building_permit_basic",
            "source_name": "국토교통부 건축인허가 기본개요",
            "source_url": "https://www.data.go.kr/data/15044695/fileData.do?recommendDataYn=Y",
            "provider": "국토교통부",
            "access_status": "metadata_collected_source_file_pending",
            "expected_events": "permit,start,approval",
            "expected_fields": "sigungu_code,legal_dong_code,main_use_code,permit_date,start_date,approval_date,total_floor_area,site_area",
            "target_sectors": "F00,L00",
            "blocking_issue": "bulk file/API route not confirmed in current repository",
        },
        {
            "source_id": "buildinghub_bulk_or_api",
            "source_name": "건축데이터 민간개방시스템/건축HUB",
            "source_url": "buildinghub_bulk_or_api_to_be_confirmed",
            "provider": "국토교통부/건축데이터 민간개방",
            "access_status": "not_started",
            "expected_events": "permit,start,approval",
            "expected_fields": "event_date,use_code,floor_area,location_code",
            "target_sectors": "F00,L00",
            "blocking_issue": "endpoint/authentication/sample download not verified",
        },
    ]


def structural_feature_registry() -> list[dict[str, Any]]:
    features = [
        ("factory_registration", "active_factory_count", "C00", "stock", "count active factories by sigungu and period"),
        ("factory_registration", "new_factory_registration_count", "C00", "flow", "count registrations during period"),
        ("factory_registration", "factory_closure_count", "C00", "flow", "count closures during period"),
        ("factory_registration", "factory_employee_count", "C00", "stock", "sum factory employees"),
        ("factory_registration", "factory_site_area", "C00", "stock", "sum site area"),
        ("industrial_complex_activity", "industrial_complex_production", "C00", "activity", "allocated production"),
        ("industrial_complex_activity", "industrial_complex_exports", "C00", "activity", "allocated exports"),
        ("industrial_complex_activity", "industrial_complex_employment", "C00", "activity", "allocated employment"),
        ("industrial_complex_activity", "industrial_complex_utilization", "C00", "activity", "utilization rate"),
        ("building_activity", "permit_floor_area", "F00,L00", "pipeline", "permitted floor area"),
        ("building_activity", "start_floor_area", "F00,L00", "pipeline", "construction started floor area"),
        ("building_activity", "approval_floor_area", "F00,L00", "pipeline", "approved floor area"),
        ("business_employment_activity", "active_business_count", "all,C00,G00,I00,F00", "activity", "active business establishments"),
        ("business_employment_activity", "insured_employee_count", "all,C00,G00,I00,F00", "activity", "insured employees"),
        ("electricity_pipeline", "industrial_kwh_per_factory", "C00", "interaction", "electricity intensity conditional on factory stock"),
        ("electricity_pipeline", "industrial_kwh_per_employee", "C00", "interaction", "electricity intensity conditional on factory employees"),
    ]
    return [
        {
            "feature_group": group,
            "feature_name": name,
            "target_sector": sector,
            "feature_role": role,
            "definition": definition,
            "source_status_required": "ml_ready",
            "first_eligible_period_required": "Y",
            "vintage_required": "Y",
            "current_status": "planned" if group != "electricity_pipeline" else "available_for_interaction_only",
        }
        for group, name, sector, role, definition in features
    ]


def write_protocol() -> None:
    lines = [
        "# Next Structural Feature Experiment Protocol",
        "",
        "## Status",
        "",
        "This is a preregistration template. No new ML run is allowed until at least one required structural source reaches ML-ready status and this protocol is updated and committed before viewing any unused official actual.",
        "",
        "## Target Sectors",
        "",
        "- C00: manufacturing, after factory registration or industrial complex activity is ML-ready",
        "- F00/L00: construction and real estate, after building permit/start/approval data is ML-ready",
        "- all: only after non-electricity activity source is ML-ready",
        "",
        "## Candidate Feature Bundles",
        "",
        "| sector | bundle | definition |",
        "| --- | --- | --- |",
        "| C00 | B0 | global only |",
        "| C00 | B1 | global + factory registration |",
        "| C00 | B2 | global + industrial complex activity |",
        "| C00 | B3 | global + factory + industrial complex |",
        "| C00 | B4 | global + factory + electricity intensity |",
        "| C00 | B5 | global + factory + industrial complex + electricity intensity |",
        "| all | A0 | global only |",
        "| all | A1 | global + business activity |",
        "| all | A2 | global + employment |",
        "| all | A3 | global + building activity |",
        "| all | A4 | global + business + employment |",
        "| all | A5 | global + business + employment + electricity |",
        "",
        "## Fixed Principles",
        "",
        "- Electricity-only correction is closed and cannot be revived without a new structural source.",
        "- 2022-2023 actual cannot be used for new post-hoc tuning of electricity-only policies.",
        "- Every source must include or derive `publication_date`, `source_vintage`, and `first_eligible_period`.",
        "- An unused actual cannot be both development and confirmatory data.",
        "",
        "## Gates Before ML Restart",
        "",
        "- regional coverage >= 90% for C00/F00/L00/all national models",
        "- official actual common period exists",
        "- first eligible period implemented",
        "- source vintage preserved",
        "- quality audit passed",
        "- candidate count and acceptance gates frozen before model results are inspected",
    ]
    PROTOCOL_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report() -> None:
    status = status_rows()
    lines = [
        "# 다음 Structural Feature Workstreams",
        "",
        "## 1. 실행 요약",
        "",
        "전력 단독 residual correction은 종료됐고, 공식 운영 정책은 `global`로 유지한다. 다음 단계는 전력 feature를 독립 보정기가 아니라 공장등록, 산업단지, 건축활동, 사업체·고용 activity와 결합하는 구조 feature 실험으로 전환하는 것이다.",
        "",
        "## 2. 전력 단독 정책 종료 상태",
        "",
        "- experiment_status: `closed_no_confirmatory_challenger`",
        "- champion: `global`",
        "- challenger: `null`",
        "- electricity_ml_correction: `inactive`",
        "- same_actual_retuning_allowed: `false`",
        "",
        "## 3. 전력 Pipeline 운영 현황",
        "",
        "전력 pipeline은 계속 유지한다. 다만 신규 전력 데이터 갱신은 ML correction 재시작 조건이 아니다. 월별 source manifest, file hash, publication date, source vintage, schema drift, revision, negative value, duplicate key, publication lag drift를 점검한다.",
        "",
        "## 4. 공장등록 Source 조사",
        "",
        "| source | status | blocking issue | next action |",
        "| --- | --- | --- | --- |",
    ]
    for row in factory_inventory():
        lines.append(f"| {row['source_name']} | {row['access_status']} | {row['blocking_issue']} | {row.get('historical_stock_feasibility', '')} |")
    lines.extend(["", "## 5. 산업단지 Activity 조사", "", "| source | status | allocation need | blocking issue |", "| --- | --- | --- | --- |"])
    for row in industrial_complex_inventory():
        lines.append(f"| {row['source_name']} | {row['access_status']} | {row['sigungu_allocation_need']} | {row['blocking_issue']} |")
    lines.extend(["", "## 6. 건축 인허가 Source 조사", "", "| source | status | target sectors | blocking issue |", "| --- | --- | --- | --- |"])
    for row in building_inventory():
        lines.append(f"| {row['source_name']} | {row['access_status']} | {row['target_sectors']} | {row['blocking_issue']} |")
    lines.extend(["", "## 7. 사업체·고용 Source 조사", "", "사업체·고용 activity는 아직 source choice가 고정되지 않았다. 고용보험 사업장/피보험자, 사업자등록 개폐업, 지방행정 인허가, 전국사업체조사, 워크넷 구인공고를 비교하되, 산업분류와 publication lag가 확인되기 전까지 ML-ready로 판정하지 않는다.", "", "## 8. Source별 Coverage 및 Publication Lag", "", "| source_id | access | regional coverage | publication lag | ml ready | blocking issue |", "| --- | --- | --- | --- | --- | --- |"])
    for row in status:
        lines.append(f"| {row['source_id']} | {row['access_status']} | {row['regional_coverage']} | {row['publication_lag_status']} | {row['ml_ready_status']} | {row['blocking_issue']} |")
    lines.extend(["", "## 9. Feature 설계", "", "| group | feature | sector | role | status |", "| --- | --- | --- | --- | --- |"])
    for row in structural_feature_registry():
        lines.append(f"| {row['feature_group']} | {row['feature_name']} | {row['target_sector']} | {row['feature_role']} | {row['current_status']} |")
    lines.extend(
        [
            "",
            "## 10. ML-ready Gate",
            "",
            "- C00: factory registration 또는 industrial complex activity가 ML-ready이고 coverage >= 90%, first eligible period, source vintage, common actual period, quality audit를 통과해야 한다.",
            "- F00/L00: permit/start/approval event date validity와 use-code mapping이 완료돼야 한다.",
            "- all: electricity 외 business/employment/building/card/foot-traffic source 중 하나 이상이 ML-ready여야 한다.",
            "",
            "## 11. 차기 결합 실험 후보",
            "",
            "C00에서는 `global + factory`, `global + industrial complex`, `global + factory + industrial complex`, `global + factory + electricity intensity`, `global + factory + industrial complex + electricity intensity`를 비교한다. 전력의 추가효과는 구조 feature가 있는 bundle과 전력 intensity를 추가한 bundle 차이로만 평가한다.",
            "",
            "## 12. 미사용 Actual 관리",
            "",
            "현재 confirmatory challenger가 없으므로 2024 이후 actual로 R2/R3b를 자동 평가하지 않는다. 새 structural policy가 actual 공개 전에 동결되면 confirmatory로 쓰고, 그렇지 않으면 development_extension으로 지정해 confirmatory 자격을 포기한다.",
            "",
            "## 13. Blocking Issues",
            "",
            "- FactoryOn bulk/API endpoint 미확인",
            "- 공장등록 workbook 빈 데이터 문제",
            "- 산업단지 complex-to-sigungu allocation 미구현",
            "- BuildingHub bulk/API 접근 경로 미확정",
            "- 사업체·고용 source choice 미고정",
            "",
            "## 14. 다음 실행 항목",
            "",
            "1. FactoryOn XLSX 내부구조 및 network 요청 조사",
            "2. 산업단지 통계 source inventory와 complex allocation rule 작성",
            "3. BuildingHub bulk/API 샘플 접근 확인",
            "4. Source별 publication lag와 first eligible period 설계",
            "5. ML-ready source가 생기기 전까지 모델 학습 금지",
            "",
            "## 15. 최종 재개 판단",
            "",
            "현 시점에서는 시군구 ML correction 재개 조건이 충족되지 않았다. 다음 실험은 전력 단독이 아니라 structural source가 ML-ready가 된 뒤 사전등록 프로토콜을 commit하고 진행한다.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_closure_manifest() -> None:
    path = PROCESSED_DIR / "electricity_policy_closure_manifest.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(
        {
            "electricity_only_reactivation": "prohibited_without_new_feature_source",
            "next_workstream_status_table": str(STATUS_PATH.relative_to(ROOT)),
            "next_protocol": str(PROTOCOL_PATH.relative_to(ROOT)),
            "last_updated": datetime.now().isoformat(timespec="seconds"),
        }
    )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    write_csv(STATUS_PATH, status_rows())
    write_csv(PROCESSED_DIR / "factory_source_inventory.csv", factory_inventory())
    write_csv(PROCESSED_DIR / "industrial_complex_source_inventory.csv", industrial_complex_inventory())
    write_csv(PROCESSED_DIR / "building_source_inventory.csv", building_inventory())
    write_csv(PROCESSED_DIR / "structural_feature_registry.csv", structural_feature_registry())
    write_protocol()
    write_report()
    update_closure_manifest()
    print(f"status rows: {len(status_rows())}")
    print(f"report: {REPORT_PATH}")
    print(f"protocol: {PROTOCOL_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
