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


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def test_phase20_frequency_gates_and_source_labels() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase20_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["target_unchanged"] is True
    assert final["annual_primary_status"] == "active"
    assert final["quarterly_parent_primary_status"] == "quarterly_parent_baseline_retained"
    assert final["quarterly_child_status"] == "quarterly_child_development_activated"
    assert final["monthly_primary_status"] == "monthly_primary_blocked"
    assert final["official_quarterly_grdp_direct_source"] is False
    assert final["official_statistics_claim"] is False
    assert final["production_use"] is False

    source = read_csv("partial_stats_phase20_gva_quarterly_grdp_source_registry.csv")
    benchmark = source[source["source_id"].eq("PROJECT_SIDO_QUARTERLY_GVA_BENCHMARK")].iloc[0]
    assert benchmark["official_direct_actual"] == "N"
    assert benchmark["role"] == "development_parent_anchor_proxy"


def test_phase20_quarterly_parent_and_indicator_artifacts() -> None:
    target = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase20_gva_quarterly_grdp_target_cube.parquet")
    assert {"period", "region_code", "industry_group", "real_grdp_level", "vintage_id"}.issubset(target.columns)
    assert num(target["real_grdp_level"]).notna().all()
    assert (PROCESSED_DIR / "partial_stats_phase20_gva_quarterly_grdp_vintages.parquet").exists()
    assert (PROCESSED_DIR / "partial_stats_phase20_gva_quarterly_indicator_cube.parquet").exists()

    parent = read_csv("partial_stats_phase20_gva_quarterly_parent_accuracy.csv")
    assert set(parent["parent_policy_id"]) == {
        "QP0_seasonal",
        "QP1_national_bridge",
        "QP2_indicator_bridge",
        "QP3_hierarchical",
        "QP4_factor",
        "QP5_midas",
        "QP7_ensemble",
    }
    assert num(parent["quarterly_wmape"]).between(0, 10).all()

    indicator = read_csv("partial_stats_phase20_gva_quarterly_indicator_registry.csv")
    assert len(indicator) >= 4
    assert indicator["primary_eligibility"].isin(["strict", "conservative", "sensitivity", "blocked_missing"]).all()


def test_phase20_child_temporal_and_reconciliation_constraints() -> None:
    child = read_csv("partial_stats_phase20_gva_quarterly_child_validation.csv")
    assert child["parent_exactness_status"].eq("pass").all()
    assert num(child["parent_exactness_max_gap"]).fillna(0).max() < 1e-5

    temporal = read_csv("partial_stats_phase20_gva_temporal_constraints.csv")
    assert temporal[temporal["constraint_id"].eq("quarter_sum_to_annual")]["status"].iloc[0] == "pass"

    consistency = read_csv("partial_stats_phase20_gva_consistency_audit.csv")
    assert consistency[consistency["check_id"].eq("quarter_sum_equals_annual")]["status"].iloc[0] == "pass"
    assert consistency[consistency["check_id"].eq("child_sum_to_parent")]["status"].iloc[0] == "pass"

    for name in [
        "partial_stats_phase20_gva_equal_quarter_results.csv",
        "partial_stats_phase20_gva_denton_results.csv",
        "partial_stats_phase20_gva_chow_lin_results.csv",
        "partial_stats_phase20_gva_fernandez_litterman_results.csv",
    ]:
        assert len(read_csv(name)) > 0


def test_phase20_current_outputs_report_and_topic_index() -> None:
    nowcast = read_csv("partial_stats_phase20_gva_quarterly_nowcast_2026.csv")
    assert nowcast["actual_used"].eq("N").all()
    assert nowcast["official_parent_status"].eq("not_materialized").all()

    annual = read_csv("partial_stats_phase20_gva_annual_from_quarters_2026.csv")
    assert annual["actual_used"].eq("N").all()
    assert annual["annual_status"].eq("full_year_quarterly_forecast").all()

    report = (ROOT / "reports" / "partial_statistics_estimation_phase20_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 50))
    assert "공식 분기 GRDP Source" in report
    assert "Monthly Gate" in report

    topic_index = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase20_gva.md" in topic_index
    assert "Quarterly GRDP anchoring" in topic_index
