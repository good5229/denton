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


def test_phase32_semantic_corrections() -> None:
    final = json.loads((DERIVED_DIR / "phase32_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "RECI-LF"
    assert final["phase31_reproduction_status"] == "pass"
    assert final["semantic_audit_passed"] is True
    assert final["confirmatory_c_count"] == 0
    assert final["full_reci_lf_available"] is False
    assert final["confidence_non_null_count"] == 0

    corrected = read_csv("phase32_corrected_shadow_schema.csv")
    assert {"spatial_activity_share", "spatial_intensity_index", "temporal_reci_index", "gva_consistent_allocation"}.issubset(corrected.columns)
    assert corrected["temporal_reci_index"].eq("").all()
    assert corrected["direction"].eq("").all()
    assert corrected["anomaly_score"].eq("").all()
    assert corrected["confidence_score"].eq("").all()
    assert corrected["production_use"].eq("false").all()
    assert corrected["official_statistics_claim"].eq("false").all()

    share_base = corrected[corrected["spatial_activity_share"].ne("")]
    share_sum = share_base.groupby(["reference_period", "sigungu_code", "industry_key"])["spatial_activity_share"].apply(lambda s: num(s).sum())
    assert (share_sum - 1).abs().max() < 1e-9


def test_phase32_rank_and_claim_vector() -> None:
    corrected = read_csv("phase32_corrected_shadow_schema.csv")
    assert {"rank_type", "rank_group_key", "rank_n", "rank_value", "rank_percentile"}.issubset(corrected.columns)
    assert corrected["rank_type"].eq("emd_within_sigungu_for_same_industry").all()
    assert corrected["rank_group_key"].ne("").all()
    small = corrected[corrected["rank_n"].astype(int) < 5]
    assert small["rank_value"].eq("").all()
    assert {"spatial_claim_grade", "industry_claim_grade", "temporal_claim_grade", "external_validation_grade", "composite_claim_grade", "composite_claim_bottleneck"}.issubset(corrected.columns)
    assert not corrected["composite_claim_grade"].isin(["O", "A", "B", "C"]).any()

    evidence = read_csv("phase32_claim_evidence_registry.csv")
    assert evidence["evidence_id"].ne("").all()
    assert not evidence["development_or_confirmatory"].eq("confirmatory").any()


def test_phase32_eligibility_mapping_and_promotion_gates() -> None:
    negative = read_csv("phase32_eligibility_negative_controls.csv")
    assert "negative_control_state" in negative.columns
    score = read_csv("phase32_eligibility_scorecard.csv")
    assert "u_candidate_rate" in set(score["negative_control_state"])

    spatial = read_csv("phase32_spatial_confirmatory_scorecard.csv")
    assert spatial["new_holdout_available"].eq("N").all()
    assert spatial["claim_grade"].eq("D").all()

    bridge = read_csv("phase32_tq3_rq1_bridge_scorecard.csv")
    assert bridge["fuzzy_join_used"].eq("N").all()
    assert bridge["temporal_claim_grade"].eq("U").all()

    fine = read_csv("phase32_fine_industry_public_sources.csv")
    assert fine["fine_industry_promotion_status"].eq("not_promoted").all()
    multi = read_csv("phase32_multi_proxy_scorecard.csv")
    assert multi["run_status"].eq("not_run").all()


def test_phase32_products_and_prospective_snapshot() -> None:
    final = json.loads((DERIVED_DIR / "phase32_final_status.json").read_text(encoding="utf-8"))
    product_a = read_csv("phase32_product_a_spatial_snapshot.csv")
    product_b = read_csv("phase32_product_b_temporal_reci.csv")
    product_c = read_csv("phase32_product_c_gva_allocation.csv")
    assert len(product_a) == final["product_a_row_count"]
    assert len(product_b) == 0
    assert len(product_c) == final["product_c_row_count"]
    assert "spatial_intensity_index" in product_a.columns
    assert "gva_consistent_allocation" in product_c.columns

    prospective = read_csv("phase32_prospective_snapshot_status.csv")
    assert prospective["overwrite_status"].eq("preserved_not_overwritten").all()


def test_phase32_reports_exist_and_topic_indexed() -> None:
    reports = [
        "partial_statistics_estimation_phase32_reci_component_promotion.md",
        "phase32_semantic_integrity.md",
        "phase32_claim_evidence_registry.md",
        "phase32_eligibility_calibration.md",
        "phase32_spatial_confirmatory.md",
        "phase32_tq3_rq1_mapping_bridge.md",
        "phase32_fine_industry_evidence.md",
        "phase32_reliability_calibration.md",
        "phase32_prospective_evaluation.md",
    ]
    for report in reports:
        assert (ROOT / "reports" / report).exists()

    topic = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase32_reci_component_promotion.md" in topic
