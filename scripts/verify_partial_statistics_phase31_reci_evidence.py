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


def main() -> int:
    final = json.loads((DERIVED_DIR / "phase31_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "RECI-LF", "target mismatch")
    require(final["phase30_reproduction_status"] == "pass", "Phase30 reproduction failed")
    require(final["production_use"] is False, "production use must be false")
    require(final["official_statistics_claim"] is False, "official statistics claim must be false")
    require(final["paid_private_source_used"] is False, "paid private source used")
    require(final["source_family_count_min_for_c_enforced"] is True, "C source-family gate missing")
    require(final["static_snapshot_quarter_observation_violation_count"] == 0, "snapshot marked as quarter observation")
    require(final["u_value_violation_count"] == 0, "U rows must have empty values")

    lineage = csv("phase31_source_lineage.csv")
    required = {
        "source_id",
        "source_family_id",
        "raw_observation_grain",
        "model_expanded_grain",
        "reference_period",
        "release_at",
        "snapshot_or_flow",
        "derived_from_source_ids",
        "feature_role",
        "validation_role",
        "independence_group",
        "region_mapping_version",
        "industry_mapping_version",
        "unit",
        "normalization",
    }
    require(required.issubset(set(lineage.columns)), "lineage columns missing")
    require(lineage["source_family_id"].ne("").all(), "source family missing")
    snapshot = lineage[lineage["source_id"].isin(["emd_2015_economic_census_proxy", "seoul_2024_business_map_proxy"])]
    require(snapshot["raw_observation_grain"].str.contains("snapshot").all(), "snapshot raw grain missing")
    require(~snapshot["raw_observation_grain"].str.contains("quarter", case=False).any(), "snapshot raw grain incorrectly quarterly")
    factory = lineage[lineage["source_id"].eq("factory_feature_snapshot")]
    require(factory["lineage_status"].str.contains("flow_use_forbidden").all(), "factory flow guardrail missing")

    raw_expanded = csv("phase31_raw_vs_expanded_grain.csv")
    require(len(raw_expanded) == len(lineage), "raw/expanded grain count mismatch")

    cell = csv("phase31_cell_eligibility.csv")
    require({"observed_presence", "probable_presence", "stale_only", "structural_zero", "mapping_unknown"}.intersection(set(cell["eligibility_state"])), "eligibility states missing")
    require(cell["value_policy"].ne("").all(), "value policy missing")

    adaptive = csv("phase31_adaptive_resolution.csv")
    require(adaptive["row_count"].astype(int).sum() == len(cell), "adaptive resolution count mismatch")

    boundary = csv("phase31_emd_boundary_crosswalk.csv")
    require(boundary["stable_boundary_flag"].isin(["Y", "N"]).all(), "invalid boundary flag")
    require(boundary["validation_population"].ne("").all(), "validation population missing")

    normalized = csv("phase31_2015_2024_normalized_validation.csv")
    require({"weighted_share_mae", "spearman_rank_corr", "presence_agreement"}.issubset(normalized.columns), "normalized validation metrics missing")

    spatial = csv("phase31_spatial_transfer_scorecard.csv")
    require("S1_2015_prior_normalized_share" in set(spatial["component_id"]), "spatial transfer candidate missing")
    require(spatial["validated_grain"].str.contains("EMD").any(), "EMD validated grain not explicit")

    industry = csv("phase31_industry_lineage_scorecard.csv")
    i1 = industry[industry["component_id"].eq("I1_manufacturing_lagged_proxy_share")].iloc[0]
    require(i1["phase31_grade"] != "B", "I1 should not remain B before target lineage confirmation")

    tq3 = csv("phase31_tq3_rq1_bridge.csv")
    require(tq3["same_quarter_actual_used_as_feature"].eq("N").all(), "TQ3 leakage guardrail failed")
    require(tq3["bridge_status"].str.contains("blocked|passed|failed", regex=True).all(), "bridge status invalid")

    proxy = csv("phase31_public_proxy_manifest.csv")
    require("urban_service_core" in set(proxy["pilot_id"]), "urban service pilot missing")

    event_archive = csv("phase31_event_archive.csv")
    if len(event_archive):
        require({"event_date", "public_release_at", "source_family_id"}.issubset(event_archive.columns), "event schema incomplete")
    event_score = csv("phase31_event_scorecard.csv")
    require(event_score["validation_status"].ne("").all(), "event score status missing")
    require(~event_score["validation_status"].str.contains("passed").any(), "event should not pass without controls")

    confidence = csv("phase31_confidence_calibration.csv")
    require("confidence_error_monotonicity" in confidence.columns, "confidence monotonicity missing")

    shadow = csv("phase31_reci_lf_shadow.csv")
    require(len(shadow) == final["shadow_row_count"], "shadow row count mismatch")
    require(shadow["production_use"].eq("false").all(), "shadow production use violation")
    require(shadow["official_statistics_claim"].eq("false").all(), "shadow official claim violation")
    require(~shadow["claim_grade"].isin(["O", "A"]).any(), "lower fine official/direct grade violation")
    c_rows = shadow[shadow["claim_grade"].eq("C")]
    require(c_rows["source_family_count"].astype(int).ge(2).all(), "C source family violation")
    require(shadow[shadow["claim_grade"].eq("U")]["reci_index"].eq("").all(), "U rows should be value-empty")
    require(shadow["direction"].eq("").all(), "static source direction should be empty")
    require(shadow["anomaly_score"].eq("").all(), "short-history anomaly should be empty")
    require(shadow["rank_universe"].str.contains("same_period").all(), "rank universe not explicit")

    prospective = csv("phase31_prospective_snapshot.csv")
    require(prospective["snapshot_status"].eq("frozen_forward_shadow").all(), "prospective snapshot not frozen")

    reports = [
        "partial_statistics_estimation_phase31_reci_evidence.md",
        "phase31_source_lineage_audit.md",
        "phase31_cell_eligibility.md",
        "phase31_emd_spatial_validation.md",
        "phase31_industry_evidence.md",
        "phase31_tq3_rq1_bridge.md",
        "phase31_public_proxy_and_event_validation.md",
        "phase31_confidence_calibration.md",
    ]
    for report_name in reports:
        require((ROOT / "reports" / report_name).exists(), f"missing report: {report_name}")
    main_report = (ROOT / "reports" / "partial_statistics_estimation_phase31_reci_evidence.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", main_report, flags=re.MULTILINE)]
    require(sections == list(range(1, 12)), "main report sections must be 1..11")
    for phrase in ["RECI-LF", "Source Lineage", "Cell Eligibility", "아직 주장할 수 없는 내용"]:
        require(phrase in main_report, f"main report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
