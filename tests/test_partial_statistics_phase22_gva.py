from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def test_phase22_official_source_and_growth_target_materialized() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase22_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["official_quarterly_source_materialized"] is True
    assert final["official_source_file_count"] >= 5
    assert final["official_source_period_count"] >= 5
    assert final["official_quarterly_target_materialized"] is True
    assert final["official_first_release_target_count"] > 0
    assert final["official_statistics_claim"] is False
    assert final["production_use"] is False

    source = read_csv("partial_stats_phase22_gva_official_source_manifest.csv")
    assert source["source_body_exists"].eq("pass").all()
    assert source["attachment_hash"].str.len().eq(64).all()
    assert source["target_extraction_gate"].eq("pass").all()
    assert pd.to_numeric(source["extracted_target_rows"], errors="coerce").gt(0).all()

    cube = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_official_target_cube.parquet")
    assert len(cube) == final["official_first_release_target_count"]
    assert cube["measure_type"].eq("yoy_growth").all()
    assert cube["price_basis"].eq("real").all()
    assert cube["value"].notna().all()
    key = ["reference_period", "region_code", "official_industry_group", "measure_type", "target_type", "vintage_id"]
    assert not cube.duplicated(key).any()


def test_phase22_growth_warmup_and_origin_gates() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase22_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["warmup_scored_rows"] == 0
    assert final["target_copy_scored_rows"] == 0
    assert final["independent_origin_count"] >= 2

    growth = read_csv("partial_stats_phase22_gva_growth_metric_audit.csv")
    assert growth["growth_unit"].eq("percentage_point").all()
    assert pd.to_numeric(growth["unit_double_scaling_errors"], errors="coerce").eq(0).all()

    origin = read_csv("partial_stats_phase22_gva_origin_registry.csv")
    assert origin["origin_status"].str.contains("independent_information", regex=False).sum() >= 2


def test_phase22_sigungu_annual_grdp_quarterly_allocation() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase22_gva_final_status.json").read_text(encoding="utf-8"))
    allocation = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    assert len(allocation) == final["sigungu_quarterly_allocation_rows"]
    assert allocation["actual_claim"].eq("N").all()
    assert allocation["development_status"].eq("benchmark_consistent_quarterly_development_estimate").all()

    annual = allocation.groupby(["source_region", "sigungu_code", "sector_code", "year"], as_index=False).agg(
        quarter_sum=("estimated_quarterly_gva", "sum"),
        annual=("annual_benchmark_gva", "first"),
    )
    assert ((annual["quarter_sum"] - annual["annual"]).abs() < 1e-6).all()
    assert final["indicator_profile_rows"] > 0

    structural = read_csv("partial_stats_phase22_gva_structural_weight_registry.csv")
    assert "farmland_area_by_sigungu" in set(structural["source_name"])
    assert "factory_count_by_sigungu" in set(structural["source_name"])


def test_phase22_report_and_topic_index() -> None:
    report = (ROOT / "reports" / "partial_statistics_estimation_phase22_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 47))
    assert "공식 분기 GRDP 원문" in report
    assert "시군구 연간 GRDP 분기배분" in report
    assert "아직 주장할 수 없는 내용" in report

    topic_index = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase22_gva.md" in topic_index
