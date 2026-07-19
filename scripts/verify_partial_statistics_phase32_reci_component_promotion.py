from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, ROOT


DERIVED_DIR = ROOT / "data" / "derived"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv(name: str) -> pd.DataFrame:
    path = DERIVED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def main() -> int:
    final = json.loads((DERIVED_DIR / "phase32_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "RECI-LF", "target mismatch")
    require(final["phase31_reproduction_status"] == "pass", "Phase31 reproduction failed")
    require(final["semantic_audit_passed"] is True, "semantic audit failed")
    require(final["full_reci_lf_available"] is False, "full RECI-LF should not be available")
    require(final["confirmatory_c_count"] == 0, "confirmatory C must be zero without new holdout")
    require(final["rank_small_group_violation_count"] == 0, "rank min-n violation")
    require(final["temporal_snapshot_violation_count"] == 0, "snapshot temporal violation")
    require(final["confidence_non_null_count"] == 0, "failed confidence should be null")
    require(final["bc_missing_evidence_count"] == 0, "B/C evidence missing")
    require(final["fuzzy_join_used"] is False, "fuzzy join used")
    require(final["production_use"] is False, "production claim violation")
    require(final["official_statistics_claim"] is False, "official claim violation")
    require(final["paid_private_source_used"] is False, "paid private source used")

    corrected = csv("phase32_corrected_shadow_schema.csv")
    required_cols = {
        "spatial_activity_share",
        "spatial_intensity_index",
        "temporal_reci_index",
        "temporal_change_rate",
        "gva_consistent_allocation",
        "rank_type",
        "rank_group_key",
        "rank_n",
        "rank_value",
        "rank_percentile",
        "spatial_claim_grade",
        "industry_claim_grade",
        "temporal_claim_grade",
        "external_validation_grade",
        "composite_claim_grade",
        "composite_claim_bottleneck",
    }
    require(required_cols.issubset(corrected.columns), "corrected schema columns missing")
    require(corrected["temporal_reci_index"].eq("").all(), "snapshot temporal index should be null")
    require(corrected["direction"].eq("").all(), "snapshot direction should be null")
    require(corrected["anomaly_score"].eq("").all(), "snapshot anomaly should be null")
    require(corrected["confidence_score"].eq("").all(), "confidence score should be hidden")
    require(corrected["production_use"].eq("false").all(), "corrected production use violation")
    require(corrected["official_statistics_claim"].eq("false").all(), "corrected official claim violation")

    share_base = corrected[corrected["spatial_activity_share"].ne("")].copy()
    share_sum = share_base.groupby(["reference_period", "sigungu_code", "industry_key"])["spatial_activity_share"].apply(lambda s: num(s).sum())
    require((share_sum - 1).abs().max() < 1e-9, "spatial share does not sum to 1")
    require(num(corrected["spatial_intensity_index"]).median() > 0, "intensity index invalid")
    small_rank = corrected[corrected["rank_n"].astype(int) < 5]
    require(small_rank["rank_value"].eq("").all(), "small rank group should have null rank")

    evidence = csv("phase32_claim_evidence_registry.csv")
    require({"evidence_id", "component", "validated_grain", "development_or_confirmatory", "promotion_status"}.issubset(evidence.columns), "evidence columns missing")
    require(~evidence["development_or_confirmatory"].eq("confirmatory").any(), "Phase31 target reused as confirmatory")
    require(evidence["promotion_status"].str.contains("not_promoted|development|D_only|blocked|sector_policy", regex=True).all(), "unexpected promotion")

    negative = csv("phase32_eligibility_negative_controls.csv")
    require("negative_control_state" in negative.columns, "negative-control state missing")
    score = csv("phase32_eligibility_scorecard.csv")
    require("u_candidate_rate" in set(score["negative_control_state"]), "U candidate metric missing")

    spatial_policy = csv("phase32_spatial_policy_by_sector.csv")
    require("facility_presence_first" in set(spatial_policy["sector_policy"]), "facility sector policy missing")
    spatial_confirm = csv("phase32_spatial_confirmatory_scorecard.csv")
    require(spatial_confirm["new_holdout_available"].eq("N").all(), "new holdout should be unavailable")
    require(spatial_confirm["claim_grade"].eq("D").all(), "spatial confirmatory should remain D")

    waterfall = csv("phase32_tq3_rq1_join_waterfall.csv")
    require(list(waterfall["step"])[-1] == "final_eligible_join", "join waterfall incomplete")
    bridge = csv("phase32_tq3_rq1_bridge_scorecard.csv")
    require(bridge["fuzzy_join_used"].eq("N").all(), "fuzzy join guardrail failed")
    require(bridge["temporal_claim_grade"].eq("U").all(), "temporal bridge should be U")

    fine = csv("phase32_fine_industry_public_sources.csv")
    require(fine["fine_industry_promotion_status"].eq("not_promoted").all(), "fine industry should not promote")
    multi = csv("phase32_multi_proxy_scorecard.csv")
    require(multi["run_status"].eq("not_run").all(), "multi proxy should not run")

    product_a = csv("phase32_product_a_spatial_snapshot.csv")
    product_b = csv("phase32_product_b_temporal_reci.csv")
    product_c = csv("phase32_product_c_gva_allocation.csv")
    require(len(product_a) == final["product_a_row_count"], "Product A count mismatch")
    require(len(product_b) == final["product_b_row_count"], "Product B count mismatch")
    require(len(product_c) == final["product_c_row_count"], "Product C count mismatch")
    require(len(product_b) == 0, "Product B should be empty until temporal bridge/history exists")

    prospective = csv("phase32_prospective_snapshot_status.csv")
    require(prospective["overwrite_status"].eq("preserved_not_overwritten").all(), "prospective snapshot overwritten")

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
    for report_name in reports:
        require((ROOT / "reports" / report_name).exists(), f"missing report: {report_name}")
    main_report = (ROOT / "reports" / "partial_statistics_estimation_phase32_reci_component_promotion.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", main_report, flags=re.MULTILINE)]
    require(sections == list(range(1, 12)), "main report sections must be 1..11")
    for phrase in ["Semantic Integrity", "Claim Evidence", "Products", "아직 주장할 수 없는 내용"]:
        require(phrase in main_report, f"main report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
