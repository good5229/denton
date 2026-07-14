from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

from denton_reci import proportional_denton, quarter_label
from kosis_common import PROCESSED_DIR, parse_number, read_csv, write_csv


SECTOR_NAME_MAP = {
    "농업임업및어업": ("A00", "농업, 임업 및 어업"),
    "광업": ("B00", "광업"),
    "제조업": ("C00", "제조업"),
    "전기가스증기및공기조절공급업": ("D00", "전기, 가스, 증기 및 공기 조절 공급업"),
    "건설업": ("F00", "건설업"),
    "도매및소매업": ("G00", "도매 및 소매업"),
    "운수및창고업": ("H00", "운수 및 창고업"),
    "숙박및음식점업": ("I00", "숙박 및 음식점업"),
    "정보통신업": ("J00", "정보통신업"),
    "금융및보험업": ("K00", "금융 및 보험업"),
    "부동산업": ("L00", "부동산업"),
    "사업서비스업": ("MN0", "사업서비스업"),
    "공공행정국방및사회보장행정": ("O00", "공공 행정, 국방 및 사회보장 행정"),
    "교육서비스업": ("P00", "교육 서비스업"),
    "보건업및사회복지서비스업": ("Q00", "보건업 및 사회복지 서비스업"),
    "문화및기타서비스업": ("ERS", "문화 및 기타서비스업"),
}

REGION_NAME_ALIASES = {
    "서울시": "서울특별시",
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "경기": "경기도",
    "강원도": "강원특별자치도",
    "강원": "강원특별자치도",
    "전라북도": "전북특별자치도",
    "전북": "전북특별자치도",
    "전라남도": "전라남도",
    "전남": "전라남도",
    "충북": "충청북도",
    "충남": "충청남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}


def normalize_name(name: str) -> str:
    text = re.sub(r"[\s,·ㆍ()]", "", name)
    return text.replace("서비스업", "서비스업")


def canonical_region(name: str) -> str:
    return REGION_NAME_ALIASES.get(name, name)


def load_province_codes() -> dict[str, str]:
    out: dict[str, str] = {}
    for row in read_csv(PROCESSED_DIR / "annual_grva_real.csv"):
        if row.get("c2_id") != "A00":
            continue
        name = canonical_region(row.get("c1_nm", ""))
        code = row.get("c1_id", "")
        if name and code:
            out[name] = code
    return out


def load_sigungu_annual() -> dict[tuple[str, str, str, str, str], dict[int, float]]:
    annual: dict[tuple[str, str, str, str, str], dict[int, float]] = defaultdict(dict)
    for row in read_csv(PROCESSED_DIR / "expanded_sigungu_grva_real.csv"):
        sector = SECTOR_NAME_MAP.get(normalize_name(row.get("c2_nm", "")))
        if not sector:
            continue
        value = parse_number(row.get("value"))
        if value is None or value <= 0:
            continue
        sector_code, sector_name = sector
        key = (
            canonical_region(row.get("source_region", "")),
            row.get("c1_id", ""),
            row.get("c1_nm", ""),
            sector_code,
            sector_name,
        )
        annual[key][int(row["prd_de"])] = value
    return annual


def load_parent_indicators() -> dict[tuple[str, str], dict[tuple[int, int], float]]:
    indicators: dict[tuple[str, str], dict[tuple[int, int], float]] = defaultdict(dict)
    for row in read_csv(PROCESSED_DIR / "all_industries_quarterly_gva_estimates.csv"):
        value = parse_number(row.get("estimated_gva"))
        if value is None or value <= 0:
            continue
        key = (row.get("area_code", ""), row.get("sector_code", ""))
        indicators[key][(int(row["year"]), int(row["quarter"]))] = value
    return indicators


def consecutive_years(years: list[int]) -> list[int]:
    if not years:
        return []
    longest: list[int] = []
    current = [years[0]]
    for year in years[1:]:
        if year == current[-1] + 1:
            current.append(year)
        else:
            if len(current) > len(longest):
                longest = current
            current = [year]
    if len(current) > len(longest):
        longest = current
    return longest


def estimate() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    province_codes = load_province_codes()
    annual = load_sigungu_annual()
    parent_indicators = load_parent_indicators()
    estimates: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for key, annual_by_year in sorted(annual.items()):
        source_region, sigungu_code, sigungu_name, sector_code, sector_name = key
        province_code = province_codes.get(source_region)
        if not province_code:
            skipped.append(
                {
                    "source_region": source_region,
                    "sigungu_code": sigungu_code,
                    "sector_code": sector_code,
                    "reason": "missing parent province code",
                }
            )
            continue
        indicator_by_q = parent_indicators.get((province_code, sector_code))
        if not indicator_by_q:
            skipped.append(
                {
                    "source_region": source_region,
                    "sigungu_code": sigungu_code,
                    "sector_code": sector_code,
                    "reason": "missing parent quarterly indicator",
                }
            )
            continue
        candidate_years = [
            year
            for year in sorted(annual_by_year)
            if all((year, quarter) in indicator_by_q for quarter in range(1, 5))
        ]
        years = consecutive_years(candidate_years)
        if len(years) < 2:
            skipped.append(
                {
                    "source_region": source_region,
                    "sigungu_code": sigungu_code,
                    "sector_code": sector_code,
                    "reason": "fewer than two consecutive annual benchmarks",
                }
            )
            continue
        try:
            indicator = [
                indicator_by_q[(year, quarter)]
                for year in years
                for quarter in range(1, 5)
            ]
            fitted = proportional_denton(indicator, [annual_by_year[year] for year in years])
        except Exception as exc:
            skipped.append(
                {
                    "source_region": source_region,
                    "sigungu_code": sigungu_code,
                    "sector_code": sector_code,
                    "reason": str(exc),
                }
            )
            continue

        annual_check: dict[int, float] = defaultdict(float)
        idx = 0
        for year in years:
            for quarter in range(1, 5):
                estimate_value = float(fitted[idx])
                annual_check[year] += estimate_value
                estimates.append(
                    {
                        "source_region": source_region,
                        "parent_area_code": province_code,
                        "sigungu_code": sigungu_code,
                        "sigungu_name": sigungu_name,
                        "sector_code": sector_code,
                        "sector_name": sector_name,
                        "year": year,
                        "quarter": quarter,
                        "period": quarter_label(year, quarter),
                        "method": "proportional Denton using parent 시도 quarterly GVA profile",
                        "indicator": round(float(indicator[idx]), 6),
                        "estimated_gva": round(estimate_value, 6),
                        "benchmark_annual_gva": annual_by_year[year],
                    }
                )
                idx += 1

        for year in years:
            benchmark = annual_by_year[year]
            fitted_sum = annual_check[year]
            error = fitted_sum - benchmark
            diagnostics.append(
                {
                    "source_region": source_region,
                    "parent_area_code": province_code,
                    "sigungu_code": sigungu_code,
                    "sigungu_name": sigungu_name,
                    "sector_code": sector_code,
                    "sector_name": sector_name,
                    "year": year,
                    "benchmark_annual_gva": round(benchmark, 6),
                    "estimated_annual_sum": round(fitted_sum, 6),
                    "constraint_error": round(error, 9),
                    "absolute_constraint_error": round(abs(error), 9),
                    "percent_constraint_error": round(error / benchmark * 100.0, 12) if benchmark else math.nan,
                }
            )
    return estimates, diagnostics, skipped


def main() -> int:
    estimates, diagnostics, skipped = estimate()
    write_csv(PROCESSED_DIR / "sigungu_quarterly_gva_estimates.csv", estimates)
    write_csv(PROCESSED_DIR / "sigungu_denton_constraint_diagnostics.csv", diagnostics)
    write_csv(PROCESSED_DIR / "sigungu_denton_skipped.csv", skipped)

    if diagnostics:
        max_abs = max(float(row["absolute_constraint_error"]) for row in diagnostics)
    else:
        max_abs = math.nan
    write_csv(
        PROCESSED_DIR / "sigungu_denton_summary.csv",
        [
            {
                "quarterly_estimate_rows": len(estimates),
                "diagnostic_rows": len(diagnostics),
                "skipped": len(skipped),
                "max_absolute_constraint_error": round(max_abs, 9),
            }
        ],
    )
    print(f"sigungu quarterly estimates: {len(estimates)} rows")
    print(f"constraint diagnostics: {len(diagnostics)} rows")
    print(f"skipped: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
