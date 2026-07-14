from __future__ import annotations

from collections import Counter, defaultdict

from denton_all_industries import SERVICE_INDICATOR_MAP, SECTOR_NAMES
from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


SERVICE_SECTORS = set(SERVICE_INDICATOR_MAP)


def main() -> int:
    estimates = read_csv(PROCESSED_DIR / "all_industries_quarterly_gva_estimates.csv")
    sigungu = read_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv")
    service_index = read_csv(PROCESSED_DIR / "service_production_index.csv")
    detailed_service = read_csv(PROCESSED_DIR / "expanded_national_service_ksic_production_index.csv")

    method_counts = Counter(row.get("method", "") for row in estimates)
    service_rows = [row for row in estimates if row.get("sector_code") in SERVICE_SECTORS]
    service_methods = Counter(row.get("method", "") for row in service_rows)
    sigungu_service_rows = [row for row in sigungu if row.get("sector_code") in SERVICE_SECTORS]

    regional_coverage: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in service_index:
        if parse_number(row.get("value")) is None:
            continue
        regional_coverage[(row.get("c1_id", ""), row.get("c2_id", ""))].add(row.get("prd_de", ""))

    detailed_coverage: dict[str, set[str]] = defaultdict(set)
    for row in detailed_service:
        if parse_number(row.get("value")) is None:
            continue
        detailed_coverage[row.get("c1_id", "")].add(row.get("prd_de", ""))

    rows = [
        {"metric": "total_sido_quarterly_estimate_rows", "value": len(estimates)},
        {"metric": "sido_rows_using_regional_service_index", "value": method_counts["regional service production index"]},
        {"metric": "service_sector_sido_rows", "value": len(service_rows)},
        {"metric": "service_sector_sido_rows_by_regional_service_index", "value": service_methods["regional service production index"]},
        {"metric": "sigungu_service_quarterly_estimate_rows", "value": len(sigungu_service_rows)},
        {"metric": "regional_service_index_area_industry_pairs", "value": len(regional_coverage)},
        {"metric": "regional_service_index_periods", "value": f"{min().join([]) if False else ''}"},
        {"metric": "national_detailed_service_industries", "value": len(detailed_coverage)},
    ]
    periods = sorted({period for periods in regional_coverage.values() for period in periods})
    detailed_periods = sorted({period for periods in detailed_coverage.values() for period in periods})
    rows[6]["value"] = f"{periods[0]}-{periods[-1]}" if periods else ""
    rows.append(
        {
            "metric": "national_detailed_service_index_periods",
            "value": f"{detailed_periods[0]}-{detailed_periods[-1]}" if detailed_periods else "",
        }
    )

    write_csv(PROCESSED_DIR / "service_index_usage_summary.csv", rows)

    report = [
        "# 서비스업생산지수 활용 점검",
        "",
        "## 결론",
        "",
        "서비스업생산지수는 이미 시도 단위 전체 업종 분기 GVA 추정에 직접 반영되어 있다. 시군구 확장에서는 부모 시도 분기 GVA 프로파일을 분기 지표로 쓰므로, 서비스업생산지수의 효과가 시도 추정치를 통해 간접 반영된다.",
        "",
        "## 적용 범위",
        "",
        f"- 시도 분기 추정 전체 행: {len(estimates):,}",
        f"- `regional service production index` 방법 행: {method_counts['regional service production index']:,}",
        f"- 서비스업 계열 시도 추정 행: {len(service_rows):,}",
        f"- 서비스업 계열 중 서비스업생산지수 기반 행: {service_methods['regional service production index']:,}",
        f"- 시군구 서비스업 계열 분기 추정 행: {len(sigungu_service_rows):,}",
        f"- 시도별 서비스업생산지수 지역×업종 조합: {len(regional_coverage):,}",
        f"- 전국 세부 서비스업생산지수 업종 수: {len(detailed_coverage):,}",
        "",
        "## 해석",
        "",
        "- 시도 단위 서비스업은 `DT_1KC2023`의 시도별 서비스업생산지수로 직접 배분된다.",
        "- 시군구 단위 서비스업은 시군구별 분기 서비스 생산지수가 없어서, 부모 시도의 서비스업 분기 GVA 프로파일을 지표로 사용한다.",
        "- 전국 세부 서비스업생산지수는 업종 세부 시간 프로파일로 유용하지만, 지역 차원이 없어 시군구별 수준을 직접 식별하는 근거로 쓰기는 어렵다.",
        "- 향후 서비스업 세분화는 시군구 연간 벤치마크, 전국 세부 서비스업생산지수, 지역별 사업체/종사자 프록시를 결합하는 2단계 배분 구조가 적절하다.",
    ]
    (PROCESSED_DIR.parents[1] / "reports" / "service_index_usage.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("service index usage summary written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
