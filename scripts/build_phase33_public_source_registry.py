from __future__ import annotations

from pathlib import Path

import pandas as pd

from phase33_common import DERIVED_DIR, GENERATED_AT, PROCESSED_DIR, RAW_DIR, add_audit, file_hash, write_csv


SERVICE_SOURCE = DERIVED_DIR / "phase33_service_source_current.parquet"
if not SERVICE_SOURCE.exists():
    SERVICE_SOURCE = PROCESSED_DIR / "partial_stats_phase27_gva_service_full_cube.parquet"


SOURCE_SPECS = [
    ("S_EMD_2015", "economic_census_2015", "KOSIS", "읍면동별 산업대분류별 총괄", PROCESSED_DIR / "emd_economic_census_2015.csv", "2015-01-01", "2015-12-31", "emd", "KSIC_section", "annual_snapshot", "establishments/employees/sales", "public_statistical_table", "conditional_metadata_only", "A1,C"),
    ("S_SEOUL_2024", "seoul_business_map", "서울 열린데이터광장", "한눈에 보는 사업체", PROCESSED_DIR / "seoul_emd_business_proxy_2024.csv", "2024-01-01", "2024-12-31", "emd", "all_industries", "annual_snapshot", "establishments/employees", "public_city_data", "conditional_metadata_only", "A1_total_activity_validation"),
    ("S_SERVICE_Q", "service_production_index", "KOSIS", "시도별 서비스업생산지수(2020=100)", SERVICE_SOURCE, "2019-01-01", "2026-06-30", "sido", "service_series", "quarter", "current_and_constant_price_index", "public_statistical_table", "conditional_metadata_only", "B"),
    ("S_RQ1", "official_quarterly_grdp_release", "통계청 지역소득 보도자료", "분기 지역내총생산 성장률", PROCESSED_DIR / "partial_stats_phase23_gva_qp1_growth_results.csv", "2020-01-01", "2025-12-31", "sido", "GRDP_total", "quarter", "real_yoy_growth", "public_release_attachment", "conditional_metadata_only", "B_external"),
    ("S_FINE_BE", "manufacturing_mining_sigungu_ksic", "KOSIS", "시도(시군구)/산업분류별 주요지표(10명 이상)", PROCESSED_DIR / "business_employment_feature_table.csv", "2021-01-01", "2023-12-31", "sigungu", "KSIC_middle", "annual", "establishments/employees/value_added", "public_statistical_table", "conditional_metadata_only", "A2"),
    ("S_FACTORY", "factory_admin_snapshot", "공공데이터포털/FactoryOn", "전국공장등록현황", PROCESSED_DIR / "factory_feature_table.csv", "2020-01-01", "2020-12-31", "sigungu", "manufacturing_total", "snapshot", "factory_count", "public_file_data", "conditional_metadata_only", "A2_presence,sector_C"),
    ("S_BUILDING", "buildinghub_admin", "국토교통부 건축HUB", "건축 인허가·착공·사용승인", PROCESSED_DIR / "buildinghub_feature_table.csv", "2021-01-01", "2024-12-31", "legal_dong_or_sigungu", "building_use", "month_or_snapshot", "event_count/area", "public_api", "not_redistributed_raw", "sector_F,event"),
    ("S_ELECTRICITY", "kepco_admin", "한국전력", "시군구 전력사용량", PROCESSED_DIR / "municipality_electricity_feature_cube.csv", "2021-01-01", "2023-12-31", "sigungu", "contract_or_use_class", "month", "usage/customer_count", "public_statistical_table", "conditional_metadata_only", "sector_C,D"),
    ("S_KSIC_8_9", "official_ksic_crosswalk", "통계청", "KSIC 8차-9차 연계표", PROCESSED_DIR / "ksic8_9_official_crosswalk_phase5.csv", "", "", "none", "KSIC_crosswalk", "version", "mapping", "official_classification", "redistribution_review", "keys"),
    ("S_KSIC_9_10", "official_ksic_crosswalk", "통계청", "KSIC 9차-10차 연계표", PROCESSED_DIR / "ksic9_10_official_crosswalk.csv", "", "", "none", "KSIC_crosswalk", "version", "mapping", "official_classification", "redistribution_review", "keys"),
    ("S_KSIC_10_11", "official_ksic_crosswalk", "통계청", "KSIC 10차-11차 연계표", PROCESSED_DIR / "ksic10_11_official_crosswalk.csv", "", "", "none", "KSIC_crosswalk", "version", "mapping", "official_classification", "redistribution_review", "keys"),
]


def build_source_registry() -> pd.DataFrame:
    rows = []
    for source_id, family, provider, dataset, path, start, end, region, industry, time, concept, license_name, redistribution, products in SOURCE_SPECS:
        exists = path.exists()
        rows.append(
            {
                "source_id": source_id,
                "source_family_id": family,
                "provider": provider,
                "dataset_name": dataset,
                "local_path": str(path.relative_to(path.parents[2])) if exists else str(path),
                "public_url_or_api": "recorded_in_prior_source_manifest_or_provider_catalog",
                "retrieval_date": GENERATED_AT[:10],
                "release_date": "source_specific_or_missing_development_only",
                "reference_period_start": start,
                "reference_period_end": end,
                "revision_policy": "latest_snapshot_preserved; historical vintage only when separately archived",
                "region_grain": region,
                "industry_grain": industry,
                "time_grain": time,
                "ksic_version": "source_specific; normalized_in_phase33_key_registry",
                "value_concept": concept,
                "unit": "source_specific",
                "nominal_real": "not_applicable_or_source_specific",
                "price_base_year": "2020 for service index; otherwise not_applicable",
                "seasonally_adjusted": "N_or_not_applicable",
                "coverage": "local_materialized" if exists else "missing_local_artifact",
                "suppression_rule": "source_specific; zero/missing/suppressed not conflated",
                "license": license_name,
                "redistribution_allowed": redistribution,
                "independence_group": family,
                "usable_products": products,
                "known_bias": "snapshot/release-lag/coverage limitations retained in claim scope",
                "local_exists": "Y" if exists else "N",
                "row_count": len(pd.read_parquet(path)) if exists and path.suffix == ".parquet" else (sum(1 for _ in path.open("rb")) - 1 if exists and path.suffix == ".csv" else 0),
                "sha256": file_hash(path) if exists else "",
                "paid_private_source": "N",
            }
        )
    return add_audit(pd.DataFrame(rows))


def main() -> int:
    registry = build_source_registry()
    write_csv("phase33_source_registry.csv", registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
