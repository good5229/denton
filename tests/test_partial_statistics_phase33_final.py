from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, ROOT


DERIVED_DIR = ROOT / "data" / "derived"


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DERIVED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def test_phase33_final_decisions_are_closed() -> None:
    status = json.loads((DERIVED_DIR / "phase33_final_status.json").read_text(encoding="utf-8"))
    assert status["phase32_reproduction_passed"] is True
    assert status["phase32_current_product_retired"] is True
    assert status["unresolved_decision_count"] == 0
    assert status["production_use"] is False
    assert status["official_statistics_claim"] is False

    catalog = read_csv("phase33_product_catalog.csv")
    decisions = dict(zip(catalog["product_id"], catalog["decision"]))
    assert decisions["A1"] == "Retained"
    assert decisions["A2"] == "Retained"
    assert decisions["B"] == "Retained"
    assert decisions["C"] == "Retained"
    assert decisions["D"] == "Blocked"
    assert decisions["A32"] == "Retired"
    assert decisions["C32"] == "Retired"


def test_phase33_industry_dimension_is_repaired() -> None:
    audit = read_csv("phase33_sector_vector_audit.csv")
    summary = audit[audit["audit_type"].eq("dataset_summary")].set_index("dataset_id")
    old_rate = float(summary.loc["phase32_current_expanded", "near_duplicate_rate"])
    new_rate = float(summary.loc["phase33_historical_observed", "near_duplicate_rate"])
    assert old_rate > 0.90
    assert new_rate < 0.01
    assert float(summary.loc["phase33_historical_observed", "median_distinct_vectors"]) == 19


def test_phase33_products_have_honest_grains() -> None:
    a1 = read_csv("phase33_product_a1_spatial.csv")
    a2 = read_csv("phase33_product_a2_fine_industry.csv")
    product_b = read_csv("phase33_product_b_temporal.csv")
    product_d = read_csv("phase33_product_d_joint_pilot.csv")
    assert len(a1) == 55_438
    assert a1["effective_time_level"].eq("2015_snapshot").all()
    assert len(a2) == 12_536
    assert a2["effective_industry_level"].eq("KSIC_middle").all()
    assert len(product_b) == 13_804
    assert product_b["reference_period"].max() == "2026Q1"
    assert product_b["claim_scope"].str.contains("not_GVA_RECI").all()
    assert len(product_d) == 0


def test_phase33_conservation_and_u_hard_gates() -> None:
    conservation = read_csv("phase33_conservation_checks.csv")
    assert conservation["status"].eq("pass").all()
    assert num(conservation["absolute_conservation_error"]).max() < 1e-6

    eligibility = read_csv("phase33_eligibility_waterfall.csv")
    assert num(eligibility["u_value_non_null_count"]).sum() == 0
    assert num(eligibility["u_rank_non_null_count"]).sum() == 0
    assert eligibility["common_fallback_disabled"].eq("Y").all()


def test_phase33_all_90_checks_and_reports() -> None:
    checks = read_csv("phase33_automatic_checks.csv")
    assert len(checks) == 90
    assert checks["status"].eq("pass").all()
    for name in [
        "partial_statistics_estimation_phase33_final.md",
        "phase33_final_executive_decision.md",
        "phase33_prior_phase_audit.md",
        "phase33_dimension_integrity.md",
        "phase33_product_b_temporal.md",
        "phase33_limitations_and_retirements.md",
    ]:
        assert (ROOT / "reports" / name).exists()
