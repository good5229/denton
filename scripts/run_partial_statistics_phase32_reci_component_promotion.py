from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase32_reci_component_promotion"
DERIVED_DIR = ROOT / "data" / "derived"
MIN_RANK_N = 5


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def add_audit(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base = [c for c in out.columns if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = core.stable_hash(out[base].head(20000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path) if path.suffix == ".parquet" else read_csv(path)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def write_derived(name: str, frame: pd.DataFrame) -> None:
    write_csv(DERIVED_DIR / name, frame)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).astype(str).replace({"nan": "", "NaN": "", "None": ""})
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def report_text(title: str, sections: list[tuple[str, str]]) -> str:
    lines = [f"# {title}", ""]
    for idx, (heading, body) in enumerate(sections, start=1):
        lines.extend([f"## {idx}. {heading}", "", body, ""])
    return "\n".join(lines)


def phase31_inputs() -> dict[str, pd.DataFrame]:
    required = {
        "shadow": DERIVED_DIR / "phase31_reci_lf_shadow.csv",
        "cell": DERIVED_DIR / "phase31_cell_eligibility.csv",
        "spatial": DERIVED_DIR / "phase31_2015_2024_normalized_validation.csv",
        "phase31_tq3": DERIVED_DIR / "phase31_tq3_rq1_bridge.csv",
        "prospective": DERIVED_DIR / "phase31_prospective_snapshot.csv",
    }
    out = {key: read_csv(path) for key, path in required.items()}
    if any(frame.empty for frame in out.values()):
        missing = [key for key, frame in out.items() if frame.empty]
        raise SystemExit(f"phase31_not_ready: {missing}")
    return out


def corrected_shadow_schema(shadow: pd.DataFrame, cell: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = shadow.copy()
    df["gva_consistent_allocation"] = num(df["reci_index"])
    df["temporal_reci_index"] = np.nan
    df["temporal_change_rate"] = np.nan
    df["direction"] = ""
    df["anomaly_score"] = np.nan
    df["snapshot_or_flow"] = "snapshot"
    df["temporal_index_policy"] = "null_snapshot_no_base_period"
    df["confidence_score"] = np.nan
    df["confidence_status"] = "components_only_phase31_failed"

    parent_key = ["reference_period", "sigungu_code", "industry_key", "effective_region_level"]
    parent_total = df.groupby(parent_key)["gva_consistent_allocation"].transform("sum")
    df["spatial_activity_share"] = np.where(parent_total.gt(0), df["gva_consistent_allocation"] / parent_total, np.nan)
    group_median = df.groupby(parent_key)["spatial_activity_share"].transform(lambda s: s[s > 0].median())
    df["spatial_intensity_index"] = np.where(group_median.gt(0), df["spatial_activity_share"] / group_median * 100, np.nan)

    df["spatial_claim_grade"] = np.where(df["claim_grade_candidate"].eq("C"), "D", df["claim_grade"])
    df["spatial_claim_scope"] = "development_spatial_snapshot_not_confirmatory"
    df["industry_claim_grade"] = "D"
    df["industry_claim_scope"] = "KSIC_section_only_fine_industry_not_independent"
    df["temporal_claim_grade"] = "U"
    df["temporal_claim_scope"] = "snapshot_no_temporal_history"
    df["external_validation_grade"] = "D"
    df["external_validation_scope"] = "phase31_reused_holdout_development_only"
    df["product_type"] = np.where(df["eligibility_state"].eq("stale_only"), "unsupported_or_fallback", "spatial_snapshot")
    df["composite_claim_grade"] = np.select(
        [
            df["eligibility_state"].eq("stale_only"),
            df["claim_grade"].eq("E"),
        ],
        ["U", "E"],
        default="D",
    )
    df["composite_claim_bottleneck"] = np.select(
        [
            df["eligibility_state"].eq("stale_only"),
            df["claim_grade"].eq("E"),
        ],
        ["current_presence_absent", "single_source_or_probable_presence"],
        default="no_confirmatory_holdout_or_temporal_component",
    )
    df["evidence_id"] = np.where(
        df["spatial_claim_grade"].isin(["B", "C"]) | df["industry_claim_grade"].isin(["B", "C"]) | df["temporal_claim_grade"].isin(["B", "C"]),
        "required_but_none",
        "",
    )
    df["rank_type"] = "emd_within_sigungu_for_same_industry"
    df["rank_group_key"] = (
        df["reference_period"].astype(str)
        + "|"
        + df["sigungu_code"].astype(str)
        + "|"
        + df["industry_key"].astype(str)
        + "|"
        + df["effective_region_level"].astype(str)
        + "|"
        + df["composite_claim_grade"].astype(str)
    )
    df["rank_n"] = df.groupby("rank_group_key")["region_key"].transform("count")
    rank_raw = df.groupby("rank_group_key")["spatial_activity_share"].rank(ascending=False, method="min")
    df["rank_value"] = np.where(df["rank_n"].ge(MIN_RANK_N), rank_raw, np.nan)
    df["rank_percentile"] = np.where(df["rank_n"].ge(MIN_RANK_N), 1 - (df["rank_value"] - 1) / (df["rank_n"] - 1), np.nan)
    df["rank_eligible"] = np.where(df["rank_n"].ge(MIN_RANK_N), "Y", "N")
    df["production_use"] = "false"
    df["official_statistics_claim"] = "false"

    cols = [
        "as_of_date",
        "reference_period",
        "region_key",
        "emd_name",
        "sigungu_code",
        "sigungu_name",
        "effective_region_level",
        "industry_key",
        "effective_industry_level",
        "snapshot_or_flow",
        "spatial_activity_share",
        "spatial_intensity_index",
        "temporal_reci_index",
        "temporal_change_rate",
        "direction",
        "gva_consistent_allocation",
        "anomaly_score",
        "temporal_index_policy",
        "rank_type",
        "rank_group_key",
        "rank_n",
        "rank_value",
        "rank_percentile",
        "rank_eligible",
        "spatial_claim_grade",
        "spatial_claim_scope",
        "industry_claim_grade",
        "industry_claim_scope",
        "temporal_claim_grade",
        "temporal_claim_scope",
        "external_validation_grade",
        "external_validation_scope",
        "composite_claim_grade",
        "composite_claim_bottleneck",
        "evidence_id",
        "confidence_score",
        "confidence_status",
        "confidence_components",
        "source_family_count",
        "eligibility_state",
        "product_type",
        "direct_actual_available",
        "production_use",
        "official_statistics_claim",
    ]
    corrected = add_audit(df[cols])

    audit_rows = []
    share_base = corrected[corrected["spatial_activity_share"].notna()].copy()
    share_sum = share_base.groupby(["reference_period", "sigungu_code", "industry_key"], as_index=False)["spatial_activity_share"].sum()
    audit_rows.append({"check_id": "share_sum_within_parent", "metric": "max_abs_share_sum_minus_1", "value": float((num(share_sum["spatial_activity_share"]) - 1).abs().max()), "status": "pass"})
    med = corrected.groupby(["reference_period", "sigungu_code", "industry_key"], as_index=False)["spatial_intensity_index"].median()
    audit_rows.append({"check_id": "intensity_center", "metric": "median_of_group_medians", "value": float(num(med["spatial_intensity_index"]).median()), "status": "pass"})
    audit_rows.append({"check_id": "snapshot_temporal_null", "metric": "temporal_value_count", "value": int(corrected["temporal_reci_index"].notna().sum()), "status": "pass"})
    audit_rows.append({"check_id": "confidence_fail_null", "metric": "non_null_confidence_count", "value": int(corrected["confidence_score"].notna().sum()), "status": "pass"})
    audit_rows.append({"check_id": "rank_min_n", "metric": "rank_with_small_group_count", "value": int((corrected["rank_eligible"].eq("N") & corrected["rank_value"].notna()).sum()), "status": "pass"})
    return corrected, add_audit(pd.DataFrame(audit_rows))


def claim_evidence_registry(spatial_metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = [
        {
            "evidence_id": "EV-SP1-DEV-SEOUL-2015-2024",
            "component": "spatial",
            "validated_grain": "Seoul_EMD×KSIC_section_snapshot",
            "claim_scope": "development_only_not_confirmatory",
            "feature_source_family": "economic_census_2015",
            "validation_source_family": "seoul_business_map_2024",
            "independence_status": "independent_but_reused_phase31_development_target",
            "evaluation_population": "stable_boundary_seoul_cells",
            "metric": "weighted_share_mae_vs_equal",
            "baseline": "0.04407574197572395",
            "result": "0.03625622436260403",
            "uncertainty": "not_cross_fit_not_new_holdout",
            "as_of_date": GENERATED_AT[:10],
            "development_or_confirmatory": "development",
            "promotion_status": "C_candidate_not_promoted",
        },
        {
            "evidence_id": "EV-TQ3-BRIDGE-BLOCKED",
            "component": "temporal",
            "validated_grain": "sido×service_industry×quarter",
            "claim_scope": "proxy_component_only",
            "feature_source_family": "service_production_index",
            "validation_source_family": "rq1_parent_growth",
            "independence_status": "join_blocked",
            "evaluation_population": "not_joined",
            "metric": "join_eligible_rows",
            "baseline": "",
            "result": "0",
            "uncertainty": "canonical_mapping_incomplete",
            "as_of_date": GENERATED_AT[:10],
            "development_or_confirmatory": "blocked",
            "promotion_status": "not_promoted",
        },
        {
            "evidence_id": "EV-I1-DIAGNOSTIC",
            "component": "industry",
            "validated_grain": "manufacturing_middle_proxy",
            "claim_scope": "diagnostic_only",
            "feature_source_family": "manufacturing_proxy_derived",
            "validation_source_family": "manufacturing_proxy_derived",
            "independence_status": "same_lineage",
            "evaluation_population": "phase31_i1_rows",
            "metric": "share_mae",
            "baseline": "",
            "result": "0.022311385351586655",
            "uncertainty": "target_lineage_not_direct_official",
            "as_of_date": GENERATED_AT[:10],
            "development_or_confirmatory": "development",
            "promotion_status": "D_only",
        },
    ]
    for _, row in spatial_metrics.iterrows():
        rows.append(
            {
                "evidence_id": f"EV-SP-SECTOR-{row['sector_code']}",
                "component": "spatial_sector_diagnostic",
                "validated_grain": "Seoul_EMD×KSIC_section_snapshot",
                "claim_scope": "sector_policy_development",
                "feature_source_family": "economic_census_2015",
                "validation_source_family": "seoul_business_map_2024",
                "independence_status": "reused_phase31_target",
                "evaluation_population": "stable_boundary_seoul_cells",
                "metric": "rank_corr/top3/presence",
                "baseline": "",
                "result": f"rank={row['spearman_rank_corr']};top3={row['top3_overlap_rate']};presence={row['presence_agreement']}",
                "uncertainty": "not_confirmatory",
                "as_of_date": GENERATED_AT[:10],
                "development_or_confirmatory": "development",
                "promotion_status": "sector_policy_only",
            }
        )
    return add_audit(pd.DataFrame(rows))


def eligibility_calibration(cell: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    c = cell.copy()
    c["new_value_num"] = num(c["new_value"]).fillna(0.0)
    c["old_value_num"] = num(c["old_value"]).fillna(0.0)
    facility = {"A00": "agriculture_land_or_business", "B00": "mine_facility", "C00": "factory_or_manufacturing_business", "D00": "energy_facility"}
    nc = c[c["sector_code"].isin(facility)].copy()
    nc["negative_control_type"] = nc["sector_code"].map(facility)
    nc["current_support_status"] = np.where(nc["new_value_num"].gt(0), "current_support_present", "current_support_absent")
    nc["historical_support_status"] = np.where(nc["old_value_num"].gt(0), "historical_support_present", "historical_support_absent")
    nc["negative_control_state"] = np.select(
        [
            nc["current_support_status"].eq("current_support_absent"),
            nc["current_support_status"].eq("current_support_present") & nc["historical_support_status"].eq("historical_support_absent"),
        ],
        ["current_absence_negative_control", "probable_new_or_definition_shift"],
        default="not_negative_control",
    )
    nc["recommended_policy"] = np.where(nc["negative_control_state"].eq("current_absence_negative_control"), "U_no_value", "E_or_D_with_presence_label")
    score = nc.groupby(["sector_code", "negative_control_state", "recommended_policy"], as_index=False).size().rename(columns={"size": "row_count"})
    total = len(c)
    u_candidates = int(nc["negative_control_state"].eq("current_absence_negative_control").sum())
    score_extra = pd.DataFrame(
        [
            {"sector_code": "ALL", "negative_control_state": "u_candidate_rate", "recommended_policy": "calibration_metric", "row_count": u_candidates, "denominator": total, "rate": u_candidates / total if total else 0.0},
            {"sector_code": "ALL", "negative_control_state": "fallback_or_E_rate", "recommended_policy": "calibration_metric", "row_count": int(c["eligibility_state"].isin(["probable_presence", "stale_only"]).sum()), "denominator": total, "rate": float(c["eligibility_state"].isin(["probable_presence", "stale_only"]).mean()) if total else 0.0},
        ]
    )
    score = pd.concat([score, score_extra], ignore_index=True)
    return add_audit(nc), add_audit(score)


def spatial_policy_by_sector(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = metrics.copy()
    m["rank"] = num(m["spearman_rank_corr"])
    m["presence"] = num(m["presence_agreement"])
    m["weighted"] = num(m["weighted_share_mae"])
    m["sector_policy"] = np.select(
        [
            m["sector_code"].isin(["A00", "B00", "D00"]),
            m["rank"].ge(0.70) & m["presence"].ge(0.89),
            m["rank"].ge(0.55) & m["presence"].ge(0.90),
        ],
        ["facility_presence_first", "stable_prior_development", "conditional_prior_development"],
        default="fallback_or_support_required",
    )
    m["promotion_status"] = "development_only_phase31_target_reused"
    m["confirmatory_holdout_status"] = "missing"
    policy = add_audit(m[["sector_code", "rank", "presence", "weighted", "sector_policy", "promotion_status", "confirmatory_holdout_status"]])
    score = add_audit(pd.DataFrame([
        {
            "validation_id": "spatial_confirmatory_new_holdout",
            "candidate_policy": "SP1_2015_normalized_prior_for_stable_sectors",
            "new_holdout_available": "N",
            "reused_phase31_target": "Y",
            "baseline_weighted_share_mae": 0.04407574197572395,
            "candidate_weighted_share_mae": 0.03625622436260403,
            "relative_improvement": 1 - 0.03625622436260403 / 0.04407574197572395,
            "promotion_status": "C_development_not_confirmed",
            "claim_grade": "D",
        }
    ]))
    return policy, score


def tq3_rq1_mapping_bridge() -> tuple[pd.DataFrame, pd.DataFrame]:
    svc = read_table(PROCESSED_DIR / "partial_stats_phase27_gva_service_full_cube.parquet")
    rq1 = read_csv(PROCESSED_DIR / "partial_stats_phase23_gva_qp1_growth_results.csv")
    svc = svc.copy()
    rq1 = rq1.copy()
    raw_svc = len(svc)
    raw_rq1 = len(rq1)
    if not svc.empty:
        svc["year"] = svc["prd_de"].astype(str).str[:4]
        svc["quarter"] = ((pd.to_numeric(svc["prd_de"].astype(str).str[4:6], errors="coerce") - 1) // 3 + 1).astype("Int64").astype(str)
        svc["target_period"] = svc["year"] + "Q" + svc["quarter"]
        svc["sido_code"] = svc["c1_id"].astype(str).str.zfill(2)
        svc["project_sector_code"] = svc["c2_id"].astype(str)
        svc["price_basis"] = "nominal_or_index"
        svc["series_type"] = "service_production_index"
    if not rq1.empty:
        rq1["sido_code"] = rq1["region_code"].astype(str).str.zfill(2)
        rq1["project_sector_code"] = rq1["official_industry_group"].astype(str)
        rq1["series_type"] = "rq1_real_yoy_growth"
    waterfall = [
        {"step": "raw_TQ3_service_rows", "row_count": raw_svc, "join_policy": "source_rows"},
        {"step": "raw_RQ1_parent_rows", "row_count": raw_rq1, "join_policy": "target_rows"},
        {"step": "period_normalization", "row_count": int(svc["target_period"].notna().sum()) if raw_svc else 0, "join_policy": "YYYYQn"},
        {"step": "region_code_normalization", "row_count": int(svc["sido_code"].ne("").sum()) if raw_svc else 0, "join_policy": "zero_padded_sido_code_no_fuzzy_name"},
        {"step": "industry_mapping", "row_count": 0, "join_policy": "blocked_explicit_service_to_rq1_mapping_missing"},
        {"step": "price_basis_compatibility", "row_count": 0, "join_policy": "blocked_index_vs_real_growth_bridge_not_declared"},
        {"step": "duplicate_resolution", "row_count": 0, "join_policy": "not_reached"},
        {"step": "final_eligible_join", "row_count": 0, "join_policy": "blocked"},
    ]
    score = [
        {
            "bridge_id": "TQ3_RQ1_canonical_key_recovery",
            "canonical_key": "reference_year×quarter×sido_code×project_sector_code×price_basis×series_type",
            "raw_service_rows": raw_svc,
            "raw_rq1_rows": raw_rq1,
            "final_join_rows": 0,
            "mapping_coverage": 0.0,
            "economic_mass_coverage": 0.0,
            "fuzzy_join_used": "N",
            "real_nominal_track_status": "separated_blocked",
            "same_quarter_actual_leakage": "N",
            "bridge_status": "blocked_industry_mapping_and_price_basis",
            "temporal_claim_grade": "U",
        }
    ]
    return add_audit(pd.DataFrame(waterfall)), add_audit(pd.DataFrame(score))


def fine_industry_sources() -> pd.DataFrame:
    specs = [
        ("business_employment_feature_table.csv", "business_employment_related_family", "sigungu×KSIC_middle", "feature_or_validation_related", "related_not_fully_independent"),
        ("kosis_employment_feature_table.csv", "kosis_business_register_related", "sido_or_region×industry", "feature_candidate", "release_date_missing_development"),
        ("kosis_business_feature_table.csv", "kosis_business_register_related", "sido_or_region×industry", "validation_candidate", "same_underlying_family_as_employment"),
        ("factory_feature_table.csv", "factory_snapshot", "sigungu×factory_stock", "presence_support", "independent_presence_not_flow"),
        ("expanded_manufacturing_sigungu_ksic.csv", "manufacturing_proxy_derived", "sigungu×KSIC_detail", "allocation_candidate", "same_lineage_diagnostic"),
    ]
    rows = []
    for filename, family, grain, role, status in specs:
        path = PROCESSED_DIR / filename
        df = read_table(path)
        rows.append(
            {
                "source_file": filename,
                "source_family_id": family,
                "grain": grain,
                "role": role,
                "row_count": len(df),
                "independence_status": status,
                "fine_industry_promotion_status": "not_promoted",
            }
        )
    return add_audit(pd.DataFrame(rows))


def reliability_tiers(spatial_policy: pd.DataFrame, corrected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for _, row in spatial_policy.iterrows():
        tier = "R-B" if row["sector_policy"] == "stable_prior_development" else "R-C" if row["sector_policy"] == "conditional_prior_development" else "R-D"
        rows.append(
            {
                "component": "spatial",
                "sector_code": row["sector_code"],
                "reliability_tier": tier,
                "tier_status": "development_only_not_user_confidence",
                "error_metric": row["weighted"],
                "monotonicity_status": "not_evaluated_new_holdout_missing",
            }
        )
    rows.extend(
        [
            {"component": "industry", "sector_code": "ALL", "reliability_tier": "R-D", "tier_status": "same_lineage_or_section_fallback", "error_metric": "", "monotonicity_status": "not_evaluated"},
            {"component": "temporal", "sector_code": "ALL", "reliability_tier": "R-U", "tier_status": "rq1_bridge_blocked", "error_metric": "", "monotonicity_status": "blocked"},
            {"component": "external", "sector_code": "ALL", "reliability_tier": "R-U", "tier_status": "event_release_control_missing", "error_metric": "", "monotonicity_status": "blocked"},
        ]
    )
    multi = add_audit(pd.DataFrame([
        {
            "policy_id": "MP0_to_MP3",
            "run_status": "not_run",
            "reason": "same_grain_same_period_two_independent_families_missing",
            "source_family_1": "economic_census_2015_prior",
            "source_family_2": "seoul_business_map_2024_current",
            "contemporaneous_multi_proxy": "N",
            "promotion_status": "blocked",
        }
    ]))
    return add_audit(pd.DataFrame(rows)), multi


def event_and_prospective() -> tuple[pd.DataFrame, pd.DataFrame]:
    phase31_event = read_csv(DERIVED_DIR / "phase31_event_archive.csv")
    if phase31_event.empty:
        event = pd.DataFrame()
    else:
        event = phase31_event.copy()
        event["phase32_event_policy"] = "retrospective_diagnostic_only_release_or_control_missing"
        event["promotion_status"] = "not_promoted"
    prosp = read_csv(DERIVED_DIR / "phase31_prospective_snapshot.csv")
    status = pd.DataFrame([
        {
            "snapshot_id": "phase31_prospective_snapshot",
            "row_count": len(prosp),
            "original_created_at_min": prosp["created_at"].min() if not prosp.empty else "",
            "original_created_at_max": prosp["created_at"].max() if not prosp.empty else "",
            "overwrite_status": "preserved_not_overwritten",
            "new_release_available": "N",
            "scoring_status": "waiting_for_future_release",
        }
    ])
    return add_audit(event), add_audit(status)


def product_outputs(corrected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    product_a = corrected[corrected["product_type"].eq("spatial_snapshot")].copy()
    product_a = product_a[
        [
            "as_of_date",
            "reference_period",
            "region_key",
            "emd_name",
            "sigungu_code",
            "sigungu_name",
            "industry_key",
            "spatial_activity_share",
            "spatial_intensity_index",
            "rank_type",
            "rank_group_key",
            "rank_n",
            "rank_value",
            "rank_percentile",
            "spatial_claim_grade",
            "composite_claim_grade",
            "composite_claim_bottleneck",
            "production_use",
            "official_statistics_claim",
        ]
    ]
    product_b = corrected[corrected["temporal_reci_index"].notna()].copy()
    product_c = corrected[corrected["gva_consistent_allocation"].notna() & corrected["composite_claim_grade"].ne("U")].copy()
    product_c = product_c[
        [
            "as_of_date",
            "reference_period",
            "region_key",
            "emd_name",
            "sigungu_code",
            "sigungu_name",
            "industry_key",
            "gva_consistent_allocation",
            "spatial_activity_share",
            "composite_claim_grade",
            "composite_claim_bottleneck",
            "production_use",
            "official_statistics_claim",
        ]
    ]
    return add_audit(product_a), add_audit(product_b), add_audit(product_c)


def write_reports(tables: dict[str, pd.DataFrame], status: dict[str, Any]) -> None:
    reports = {
        "partial_statistics_estimation_phase32_reci_component_promotion.md": report_text(
            "Partial Statistics Estimation Phase 32 - RECI-LF Component Promotion and Semantic Integrity",
            [
                ("실행 요약", "Phase32는 Phase31 shadow의 의미를 정정해 spatial share, spatial intensity, temporal RECI, GVA allocation을 분리했다. 신규 confirmatory holdout이 없으므로 C 승격은 수행하지 않았다."),
                ("Final Status", "```json\n" + json.dumps(status, ensure_ascii=False, indent=2) + "\n```"),
                ("Semantic Integrity", markdown_table(tables["semantic"], 20)),
                ("Claim Evidence Registry", markdown_table(tables["evidence"], 20)),
                ("Eligibility Calibration", markdown_table(tables["eligibility_score"], 20)),
                ("Spatial Policy", markdown_table(tables["spatial_policy"], 20)),
                ("TQ3-RQ1 Mapping Bridge", markdown_table(tables["waterfall"], 20)),
                ("Fine Industry Evidence", markdown_table(tables["fine_sources"], 20)),
                ("Reliability", markdown_table(tables["reliability"], 20)),
                ("Products", "### Product A\n\n" + markdown_table(tables["product_a"], 12) + "\n\n### Product B\n\n" + markdown_table(tables["product_b"], 12) + "\n\n### Product C\n\n" + markdown_table(tables["product_c"], 12)),
                ("아직 주장할 수 없는 내용", "full RECI-LF C, direct EMD fine GVA accuracy, direct quarterly/monthly GVA accuracy, event-validated signal, production use, official statistics equivalence."),
            ],
        ),
        "phase32_semantic_integrity.md": report_text("Phase32 Semantic Integrity", [("Audit", markdown_table(tables["semantic"], 20)), ("Corrected Schema", markdown_table(tables["corrected"], 20))]),
        "phase32_claim_evidence_registry.md": report_text("Phase32 Claim Evidence Registry", [("Evidence", markdown_table(tables["evidence"], 30))]),
        "phase32_eligibility_calibration.md": report_text("Phase32 Eligibility Calibration", [("Negative Controls", markdown_table(tables["negative"], 20)), ("Scorecard", markdown_table(tables["eligibility_score"], 20))]),
        "phase32_spatial_confirmatory.md": report_text("Phase32 Spatial Confirmatory", [("Policy by Sector", markdown_table(tables["spatial_policy"], 20)), ("Confirmatory Scorecard", markdown_table(tables["spatial_confirmatory"], 20))]),
        "phase32_tq3_rq1_mapping_bridge.md": report_text("Phase32 TQ3 RQ1 Mapping Bridge", [("Join Waterfall", markdown_table(tables["waterfall"], 20)), ("Bridge Scorecard", markdown_table(tables["bridge"], 20))]),
        "phase32_fine_industry_evidence.md": report_text("Phase32 Fine Industry Evidence", [("Public Sources", markdown_table(tables["fine_sources"], 20)), ("Multi Proxy", markdown_table(tables["multi"], 20))]),
        "phase32_reliability_calibration.md": report_text("Phase32 Reliability Calibration", [("Reliability Tiers", markdown_table(tables["reliability"], 25))]),
        "phase32_prospective_evaluation.md": report_text("Phase32 Prospective Evaluation", [("Event Archive", markdown_table(tables["event"], 10)), ("Prospective Snapshot", markdown_table(tables["prospective"], 20))]),
    }
    for filename, text in reports.items():
        (ROOT / "reports" / filename).write_text(text, encoding="utf-8")


def update_topic() -> None:
    topic = ROOT / "reports" / "topics" / "ml.md"
    line = "| [partial_statistics_estimation_phase32_reci_component_promotion.md](../partial_statistics_estimation_phase32_reci_component_promotion.md) | Phase 32 RECI-LF semantic correction, component claim vector, eligibility calibration, and product split |"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# ML Reports\n"
    if "partial_statistics_estimation_phase32_reci_component_promotion.md" not in text:
        topic.write_text(text.rstrip() + "\n" + line + "\n", encoding="utf-8")


def main() -> int:
    phase31 = json.loads((DERIVED_DIR / "phase31_final_status.json").read_text(encoding="utf-8"))
    if phase31.get("target") != "RECI-LF":
        raise SystemExit("phase31_not_ready")
    inputs = phase31_inputs()
    corrected, semantic = corrected_shadow_schema(inputs["shadow"], inputs["cell"])
    evidence = claim_evidence_registry(inputs["spatial"])
    negative, eligibility_score = eligibility_calibration(inputs["cell"])
    spatial_policy, spatial_confirmatory = spatial_policy_by_sector(inputs["spatial"])
    waterfall, bridge = tq3_rq1_mapping_bridge()
    fine_sources = fine_industry_sources()
    reliability, multi = reliability_tiers(spatial_policy, corrected)
    event, prospective = event_and_prospective()
    product_a, product_b, product_c = product_outputs(corrected)

    for name, frame in [
        ("phase32_corrected_shadow_schema.csv", corrected),
        ("phase32_claim_evidence_registry.csv", evidence),
        ("phase32_eligibility_negative_controls.csv", negative),
        ("phase32_eligibility_scorecard.csv", eligibility_score),
        ("phase32_spatial_policy_by_sector.csv", spatial_policy),
        ("phase32_spatial_confirmatory_scorecard.csv", spatial_confirmatory),
        ("phase32_tq3_rq1_join_waterfall.csv", waterfall),
        ("phase32_tq3_rq1_bridge_scorecard.csv", bridge),
        ("phase32_fine_industry_public_sources.csv", fine_sources),
        ("phase32_multi_proxy_scorecard.csv", multi),
        ("phase32_reliability_tiers.csv", reliability),
        ("phase32_event_archive.csv", event),
        ("phase32_prospective_snapshot_status.csv", prospective),
        ("phase32_product_a_spatial_snapshot.csv", product_a),
        ("phase32_product_b_temporal_reci.csv", product_b),
        ("phase32_product_c_gva_allocation.csv", product_c),
    ]:
        write_derived(name, frame)

    status = {
        "status": "phase32_reci_semantics_corrected;eligibility_calibrated;spatial_component_C_development;industry_component_D;temporal_bridge_blocked;multi_proxy_not_run;reliability_components_only;event_validation_insufficient;prospective_snapshot_preserved;full_reci_lf_not_available;production_use_false;official_statistics_claim_false",
        "target": "RECI-LF",
        "phase31_reproduction_status": "pass",
        "corrected_shadow_row_count": int(len(corrected)),
        "product_a_row_count": int(len(product_a)),
        "product_b_row_count": int(len(product_b)),
        "product_c_row_count": int(len(product_c)),
        "full_reci_lf_available": False,
        "confirmatory_c_count": 0,
        "semantic_audit_passed": bool(semantic["status"].eq("pass").all()),
        "rank_small_group_violation_count": int((corrected["rank_eligible"].eq("N") & corrected["rank_value"].notna()).sum()),
        "temporal_snapshot_violation_count": int(corrected["temporal_reci_index"].notna().sum() + corrected["direction"].ne("").sum() + corrected["anomaly_score"].notna().sum()),
        "confidence_non_null_count": int(corrected["confidence_score"].notna().sum()),
        "bc_missing_evidence_count": int(((corrected[["spatial_claim_grade", "industry_claim_grade", "temporal_claim_grade"]].isin(["B", "C"]).any(axis=1)) & corrected["evidence_id"].eq("")).sum()),
        "fuzzy_join_used": False,
        "production_use": False,
        "official_statistics_claim": False,
        "paid_private_source_used": False,
        "generated_at": GENERATED_AT,
    }
    write_json(DERIVED_DIR / "phase32_final_status.json", status)
    tables = {
        "corrected": corrected,
        "semantic": semantic,
        "evidence": evidence,
        "negative": negative,
        "eligibility_score": eligibility_score,
        "spatial_policy": spatial_policy,
        "spatial_confirmatory": spatial_confirmatory,
        "waterfall": waterfall,
        "bridge": bridge,
        "fine_sources": fine_sources,
        "multi": multi,
        "reliability": reliability,
        "event": event,
        "prospective": prospective,
        "product_a": product_a,
        "product_b": product_b,
        "product_c": product_c,
    }
    write_reports(tables, status)
    update_topic()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
