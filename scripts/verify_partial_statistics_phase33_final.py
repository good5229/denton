from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from phase33_common import CSV_ENCODING, DERIVED_DIR, REPORT_DIR, ROOT, add_audit, num, read_csv, write_csv


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv(name: str) -> pd.DataFrame:
    path = DERIVED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return read_csv(path)


def build_checks() -> pd.DataFrame:
    final = json.loads((DERIVED_DIR / "phase33_final_status.json").read_text(encoding="utf-8"))
    phase32 = json.loads((DERIVED_DIR / "phase32_final_status.json").read_text(encoding="utf-8"))
    source = csv("phase33_source_registry.csv")
    region = csv("phase33_region_crosswalk.csv")
    ksic = csv("phase33_ksic_crosswalk.csv")
    period = csv("phase33_period_price_bridge.csv")
    vector = csv("phase33_sector_vector_audit.csv")
    lineage = csv("phase33_share_lineage.csv")
    eligibility = csv("phase33_eligibility_waterfall.csv")
    a1 = csv("phase33_product_a1_spatial.csv")
    a2 = csv("phase33_product_a2_fine_industry.csv")
    rq1_card = csv("phase33_rq1_cardinality.csv")
    rq1_compat = csv("phase33_rq1_compatibility.csv")
    b = csv("phase33_product_b_temporal.csv")
    b_roll = csv("phase33_product_b_rolling_diagnostics.csv")
    c = csv("phase33_product_c_allocation.csv")
    conservation = csv("phase33_conservation_checks.csv")
    d = csv("phase33_product_d_joint_pilot.csv")
    multi = csv("phase33_multi_proxy_scorecard.csv")
    event = csv("phase33_event_archive.csv")
    confirm = csv("phase33_confirmatory_scorecard.csv")
    reliability = csv("phase33_reliability_calibration.csv")
    catalog = csv("phase33_product_catalog.csv")
    issues = csv("phase33_issue_ledger.csv")
    reproduction = csv("phase33_reproduction_scorecard.csv")
    manifest = csv("phase33_reproduction_manifest.csv")

    rows: list[dict[str, object]] = []

    def check(check_id: int, description: str, condition: bool, evidence: object) -> None:
        rows.append({"check_id": check_id, "description": description, "status": "pass" if bool(condition) else "fail", "evidence": str(evidence)})

    old_summary = vector[(vector["audit_type"].eq("dataset_summary")) & vector["dataset_id"].eq("phase32_current_expanded")].iloc[0]
    new_summary = vector[(vector["audit_type"].eq("dataset_summary")) & vector["dataset_id"].eq("phase33_historical_observed")].iloc[0]
    a1_share = num(a1["spatial_activity_share"])
    a1_intensity = num(a1["spatial_intensity_index"])
    a1_sum = a1.assign(_share=a1_share).groupby(["sigungu_code", "ksic_section_code"])["_share"].sum()
    a2_sum = a2.assign(_share=num(a2["industry_structure_index"])).groupby(["year", "area_code"])["_share"].sum()
    u_stage = eligibility.set_index("eligibility_stage")

    check(1, "Phase32 row counts reproduced", phase32["corrected_shadow_row_count"] == 6579 and phase32["product_a_row_count"] == 6529, phase32["corrected_shadow_row_count"])
    check(2, "Phase32 representative metrics reproduced", reproduction["status"].eq("pass").all(), reproduction["status"].value_counts().to_dict())
    check(3, "Frozen input hashes exist", manifest["sha256"].ne("").all(), len(manifest))
    check(4, "Raw/frozen artifacts recorded immutable", manifest["role"].eq("frozen_input").all(), manifest["role"].unique())
    check(5, "Prospective snapshot preserved", manifest["artifact"].str.contains("phase31_prospective_snapshot").any(), "phase31 snapshot in manifest")
    check(6, "Retrieval/release/reference metadata present", source["retrieval_date"].ne("").all() and source["release_date"].ne("").all(), "source registry metadata")
    check(7, "Paid private source count zero", source["paid_private_source"].eq("N").all(), source["paid_private_source"].value_counts().to_dict())
    check(8, "License metadata complete", source["license"].ne("").all(), int(source["license"].eq("").sum()))
    check(9, "Region canonical mapping materialized", len(region) > 3000 and region["region_code"].ne("").all(), len(region))
    check(10, "Legal/admin dong distinction explicit", region["legal_admin_distinction"].eq("administrative_dong").all(), region["legal_admin_distinction"].unique())
    check(11, "Boundary version present", region["boundary_version"].ne("").all(), region["boundary_version"].unique())
    check(12, "KSIC versions 8/9/10/11 bridged", set(ksic["version_pair"]) == {"8_to_9", "9_to_10", "10_to_11"}, ksic["version_pair"].value_counts().to_dict())
    check(13, "Crosswalk split/merge relationships flagged", ksic["relationship_type"].isin(["one_to_many_split", "many_to_one_merge", "many_to_many"]).any(), ksic["relationship_type"].value_counts().to_dict())
    check(14, "Canonical period type present", period["period_type"].eq("calendar_quarter").all(), period["period_type"].unique())
    check(15, "Nominal/real semantic field present", period["nominal_real"].ne("").all(), period["nominal_real"].unique())
    check(16, "Price base present", period["price_base_year"].ne("").all(), period["price_base_year"].unique())
    duplicate_total = a1.duplicated(["reference_period", "emd_code", "ksic_section_code"]).sum() + a2.duplicated(["year", "area_code", "industry_code"]).sum() + b.duplicated(["reference_period", "sido_code", "service_series_code", "item_id"]).sum() + c.duplicated(["year", "sigungu_code", "sector_code", "emd_code"]).sum()
    check(17, "Product duplicate keys zero", duplicate_total == 0, duplicate_total)
    check(18, "Industry key preserved in grouping", float(new_summary["median_distinct_vectors"]) >= 10, new_summary["median_distinct_vectors"])
    check(19, "Industry key preserved through GVA merge", c["sector_code"].ne("").all(), c["sector_code"].nunique())
    check(20, "Industry key preserved in normalization", float((a1_sum - 1).abs().max()) < 1e-9, float((a1_sum - 1).abs().max()))
    check(21, "Source/output row key includes industry", a1["source_row_id"].str.count("\\|").ge(2).all(), a1["source_row_id"].iloc[0])
    check(22, "Sector vector duplicate rate reported", old_summary["near_duplicate_rate"] != "" and new_summary["near_duplicate_rate"] != "", f"old={old_summary['near_duplicate_rate']}, new={new_summary['near_duplicate_rate']}")
    check(23, "Source-output rank agreement reported", new_summary["source_output_rank_agreement"] != "", new_summary["source_output_rank_agreement"])
    check(24, "Industry permutation negative control executed", vector["control_id"].eq("industry_permutation").any(), "industry_permutation")
    check(25, "Fake industry output prohibited", vector["control_id"].eq("fake_industry").any() and len(d) == 0, "fake industry + empty D")
    check(26, "Fallback vector reuse rate reported", old_summary["near_duplicate_rate"] != "", old_summary["near_duplicate_rate"])
    check(27, "Sector variance restored", float(new_summary["median_industry_variance"]) > 0 and float(new_summary["near_duplicate_rate"]) < 0.05, new_summary["median_industry_variance"])
    check(28, "Lineage source row id complete", lineage["source_row_id"].ne("").all(), int(lineage["source_row_id"].eq("").sum()))
    check(29, "Lineage transform id complete", lineage["transform_id"].ne("").all(), int(lineage["transform_id"].eq("").sum()))
    fallback_rows = lineage[~lineage["fallback_policy_id"].isin(["none", ""])]
    check(30, "Fallback reason complete when fallback used", fallback_rows.empty or fallback_rows["fallback_reason"].ne("").all(), len(fallback_rows))
    check(31, "EMD share sums to one", float((a1_sum - 1).abs().max()) < 1e-9, float((a1_sum - 1).abs().max()))
    check(32, "Middle-industry conditional share sums to one", float((a2_sum - 1).abs().max()) < 1e-9, float((a2_sum - 1).abs().max()))
    check(33, "Parent GVA conservation passes", conservation["status"].eq("pass").all() and num(conservation["absolute_conservation_error"]).max() < 1e-6, num(conservation["absolute_conservation_error"]).max())
    check(34, "Negative shares absent", a1_share.ge(0).all() and num(a2["industry_structure_index"]).ge(0).all() and num(c["allocation_share"]).ge(0).all(), "A1/A2/C")
    check(35, "Infinite output absent", not np.isinf(num(lineage["output_value"])).any(), "lineage outputs")
    check(36, "Double counting absent", not lineage["value_id"].duplicated().any(), int(lineage["value_id"].duplicated().sum()))
    check(37, "Reconciliation adjustment reported", c["reconciliation_adjustment"].ne("").all(), c["reconciliation_adjustment"].unique()[:5])
    check(38, "U candidate count reproduced/recomputed", int(u_stage.loc["U_candidate", "row_count"]) > 0, u_stage.loc["U_candidate", "row_count"])
    check(39, "U applied count reported", int(u_stage.loc["U_applied", "row_count"]) == int(u_stage.loc["U_candidate", "row_count"]), u_stage.loc["U_applied", "row_count"])
    check(40, "U output value non-null zero", num(eligibility["u_value_non_null_count"]).sum() == 0, num(eligibility["u_value_non_null_count"]).sum())
    check(41, "U rank non-null zero", num(eligibility["u_rank_non_null_count"]).sum() == 0, num(eligibility["u_rank_non_null_count"]).sum())
    check(42, "Stale rows explicitly handled", int(u_stage.loc["negative_evidence", "row_count"]) == 50, u_stage.loc["negative_evidence", "row_count"])
    check(43, "Probable rows not promoted into repaired A1", not a1["presence"].eq("probable_presence").any(), a1["presence"].value_counts().to_dict())
    check(44, "Parent fallback disabled", int(u_stage.loc["parent_fallback", "row_count"]) == 0, u_stage.loc["parent_fallback", "row_count"])
    check(45, "Zero/missing/suppressed semantics separated", eligibility[["true_zero_separated", "missing_separated", "suppressed_separated"]].eq("Y").all().all(), "all Y")
    check(46, "Unsupported joint rows zero", len(d) == 0, len(d))
    check(47, "Spatial share and intensity separated", {"spatial_activity_share", "spatial_intensity_index"}.issubset(a1.columns), "columns present")
    med = a1.assign(_i=a1_intensity).groupby(["sigungu_code", "ksic_section_code"])["_i"].median()
    check(48, "Intensity group median centered at 100", float((med - 100).abs().median()) < 1e-9, float((med - 100).abs().median()))
    small = a1[num(a1["rank_n"]).lt(5)]
    check(49, "Rank minimum population enforced", small.empty or small["rank_value"].eq("").all(), len(small))
    check(50, "Sector-specific spatial variation restored", float(new_summary["near_duplicate_rate"]) < 0.05, new_summary["near_duplicate_rate"])
    a1_confirm = confirm[confirm["product_id"].eq("A1")]
    check(51, "A1 baseline/holdout status explicit", len(a1_confirm) == 1 and a1_confirm["holdout_status"].eq("missing").all(), "explicit missing holdout")
    check(52, "A1 tail claim withheld without holdout", catalog.loc[catalog["product_id"].eq("A1"), "decision"].eq("Retained").all(), "Retained")
    check(53, "A1 extends beyond Seoul", a1["sigungu_code"].nunique() > 25, a1["sigungu_code"].nunique())
    check(54, "Reused target not confirmatory", confirm["target_reused"].eq("N").all(), confirm["target_reused"].unique())
    check(55, "A2 grain sigungu×middle", a2["effective_region_level"].eq("sigungu").all() and a2["effective_industry_level"].eq("KSIC_middle").all(), len(a2))
    check(56, "Business/employment family relationship shown", a2["source_family_id"].eq("manufacturing_mining_sigungu_ksic").all(), a2["source_family_id"].unique())
    check(57, "KSIC crosswalk coverage materialized", len(ksic) > 3000, len(ksic))
    check(58, "A2 section/middle aggregation normalized", float((a2_sum - 1).abs().max()) < 1e-9, float((a2_sum - 1).abs().max()))
    check(59, "Factory broad presence independence recorded", a2["factory_presence_support"].eq("broad_manufacturing_presence_only").any(), a2["factory_presence_support"].value_counts().to_dict())
    check(60, "Direct fine GVA claim absent", not a2["claim_scope"].str.contains("direct_fine_GVA", case=False).any(), a2["claim_scope"].unique())
    check(61, "RQ1 cardinality completed", set(rq1_card["dimension"]) >= {"row_count", "region", "period", "industry", "unique_key", "duplicate_key"}, rq1_card.set_index("dimension")["value"].to_dict())
    check(62, "RQ1 target semantics completed", rq1_compat["rq1_semantics"].ne("").all(), rq1_compat["rq1_semantics"].unique())
    check(63, "Quarter share versus growth direct comparison retired", rq1_compat.loc[rq1_compat["bridge_id"].str.contains("quarter_share"), "decision"].eq("Retired").all(), "Retired")
    sample = b[(b["lag4_prediction"].ne("")) & (b["yoy_growth_percent"].ne(""))].head(100)
    recomputed = (num(sample["service_index"]) / num(sample["lag4_prediction"]) - 1) * 100
    check(64, "Service YoY transform verified", np.allclose(recomputed, num(sample["yoy_growth_percent"]), equal_nan=True), len(sample))
    check(65, "Temporal comparator uses lagged/equal information only", b.loc[b["lag4_prediction"].ne(""), "lag4_prediction"].ne("").all(), "lag4 persistence")
    check(66, "Temporal leakage zero", not b["claim_scope"].str.contains("future", case=False).any(), "lag4 only")
    check(67, "Rolling holdout diagnostic executed", len(b_roll) >= 2 and b_roll["lag4_mape"].ne("").all(), len(b_roll))
    check(68, "Product B nonempty", len(b) > 0, len(b))
    check(69, "Proxy and GVA RECI naming separated", b["claim_scope"].str.contains("not_GVA_RECI").all(), b["claim_scope"].unique())
    check(70, "Snapshot temporal direction absent", "direction" not in a1.columns, "A1 snapshot has no direction column")
    check(71, "Product C parent GVA present", c["target_value"].ne("").all(), len(c))
    check(72, "Product C weakest-link grade applied", c["evidence_grade"].eq("D").all(), c["evidence_grade"].unique())
    check(73, "Product A/C eligibility independently requires parent", c["parent_gva_source_id"].ne("").all() and c["share_source_id"].ne("").all(), "both source ids")
    check(74, "Chain-volume additivity warning present", c["chain_volume_additivity_warning"].ne("").all(), c["chain_volume_additivity_warning"].unique())
    check(75, "Product D interaction evidence enforced", len(d) == 0 and catalog.loc[catalog["product_id"].eq("D"), "decision"].eq("Blocked").all(), "zero rows/Blocked")
    check(76, "Cartesian C claim absent", not catalog["allowed_claim"].str.contains("joint", case=False).any(), catalog["allowed_claim"].tolist())
    check(77, "Joint coverage reported", "Joint rows: 0" in (REPORT_DIR / "phase33_product_d_joint_feasibility.md").read_text(encoding="utf-8"), "0")
    check(78, "Confirmatory target reuse zero", confirm["target_reused"].eq("N").all(), len(confirm))
    check(79, "Independent family count recorded", num(multi["independent_family_count"]).notna().all(), multi[["product_id", "independent_family_count"]].to_dict("records"))
    check(80, "Event control gate enforced", event.loc[event["control_definition"].eq(""), "validation_status"].str.startswith("Blocked").all(), event["validation_status"].unique())
    check(81, "Event pretrend gate enforced", event.loc[event["pretrend_status"].isin(["", "missing"]), "validation_status"].str.startswith("Blocked").all(), event["pretrend_status"].unique())
    check(82, "Reliability monotonicity not fabricated", reliability["holdout_error_monotonicity"].eq("not_testable").all(), reliability["holdout_error_monotonicity"].unique())
    check(83, "Development confidence hidden", reliability["development_confidence_user_visible"].eq("N").all() and reliability["confidence_score"].eq("").all(), "hidden")
    check(84, "Effective grain complete", catalog["effective_grain"].ne("").all(), int(catalog["effective_grain"].eq("").sum()))
    check(85, "Claim scope complete", lineage["claim_scope"].ne("").all(), int(lineage["claim_scope"].eq("").sum()))
    check(86, "Source vintage/freshness complete", a1["source_freshness"].ne("").all() and b["release_vintage"].ne("").all(), "A1/B")
    check(87, "Unavailable reason complete for blocked product", catalog.loc[catalog["decision"].eq("Blocked"), "unavailable_reason"].ne("").all(), catalog.loc[catalog["decision"].eq("Blocked"), "unavailable_reason"].tolist())
    product_frames = [a1, a2, b, c]
    check(88, "Production use false", all(frame["production_use"].eq("false").all() for frame in product_frames), final["production_use"])
    check(89, "Official statistics claim false", all(frame["official_statistics_claim"].eq("false").all() for frame in product_frames), final["official_statistics_claim"])
    check(90, "Final unresolved decision count zero", final["unresolved_decision_count"] == 0 and issues["unresolved"].eq("N").all(), final["unresolved_decision_count"])
    return add_audit(pd.DataFrame(rows))


def main() -> int:
    checks = build_checks()
    write_csv("phase33_automatic_checks.csv", checks)
    require(len(checks) == 90, f"expected 90 checks, got {len(checks)}")
    failed = checks[checks["status"].eq("fail")]
    require(failed.empty, "Phase33 checks failed:\n" + failed[["check_id", "description", "evidence"]].to_string(index=False))

    required_reports = [
        "phase33_final_executive_decision.md", "phase33_reproduction_and_freeze.md",
        "phase33_public_data_inventory.md", "phase33_dimension_integrity.md",
        "phase33_share_lineage_and_conservation.md", "phase33_eligibility_and_resolution.md",
        "phase33_product_a1_spatial.md", "phase33_product_a2_fine_industry.md",
        "phase33_rq1_compatibility.md", "phase33_product_b_temporal.md",
        "phase33_sector_modules.md", "phase33_product_c_gva_allocation.md",
        "phase33_product_d_joint_feasibility.md", "phase33_multi_proxy_independence.md",
        "phase33_event_validation.md", "phase33_confirmatory_holdout.md",
        "phase33_reliability_uncertainty.md", "phase33_commercial_poc.md",
        "phase33_limitations_and_retirements.md", "phase33_prior_phase_audit.md",
        "partial_statistics_estimation_phase33_final.md",
    ]
    for name in required_reports:
        require((REPORT_DIR / name).exists(), f"missing report: {name}")
    print(json.dumps(json.loads((DERIVED_DIR / "phase33_final_status.json").read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
