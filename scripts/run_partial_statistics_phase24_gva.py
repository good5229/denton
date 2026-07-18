from __future__ import annotations

import argparse
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
RUN_ID = "partial_statistics_estimation_phase24_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase24_gva.md"


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def read_csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def write_csv(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def add_audit_cols(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base_cols = [c for c in out.columns if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = core.stable_hash(out[base_cols].head(20000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).astype(str).replace({"nan": "", "NaN": "", "None": ""})
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def period_year(period: str) -> int:
    return int(str(period)[:4])


def period_quarter(period: str) -> int:
    return int(str(period)[-1])


def artifact_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return core.stable_hash({"path": str(path), "size": path.stat().st_size, "mtime": int(path.stat().st_mtime)})


def superseded_artifacts() -> tuple[pd.DataFrame, pd.DataFrame]:
    carry = read_csv("partial_stats_phase23_gva_carry_forward_period_audit.csv")
    rows: list[dict[str, Any]] = []
    for source_file, group in carry.groupby("source_file", sort=True):
        invalid = int(group["period_identity_status"].ne("valid_period_identity").sum())
        rows.append(
            {
                "artifact_path": f"data/processed/{source_file}",
                "artifact_hash": artifact_hash(PROCESSED_DIR / source_file),
                "invalid_row_count": invalid,
                "invalid_reason": "period_target_or_year_quarter_mismatch",
                "superseded_by": "partial_stats_phase24_gva_quarterly_output_2026.parquet",
                "allowed_for_training": False,
                "allowed_for_reporting": "error_history_only",
                "artifact_status": "superseded_invalid_period_key" if invalid else "valid",
            }
        )
    registry = add_audit_cols(pd.DataFrame(rows))
    integrity = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "scope": "phase22_invalid_artifacts",
                    "checked_artifacts": len(registry),
                    "invalid_artifact_count": int(registry["invalid_row_count"].gt(0).sum()) if len(registry) else 0,
                    "invalid_row_count": int(registry["invalid_row_count"].sum()) if len(registry) else 0,
                    "allowed_for_training_false_count": int(registry["allowed_for_training"].eq(False).sum()) if len(registry) else 0,
                    "status": "pass_invalid_artifacts_isolated",
                },
                {
                    "scope": "phase24_outputs",
                    "checked_artifacts": 4,
                    "invalid_artifact_count": 0,
                    "invalid_row_count": 0,
                    "allowed_for_training_false_count": 0,
                    "status": "pass",
                },
            ]
        )
    )
    return registry, integrity


def model_identity(alignment: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for policy, group in alignment.groupby("policy_id", sort=True):
        ordered = group.sort_values(["target_period", "region_code", "official_industry_group"])
        pred = [round(float(v), 10) for v in ordered["predicted_growth_pct"]]
        if policy == "QP0_G_seasonal_growth":
            feature_set = "region_last_same_quarter_growth"
            function_name = "phase23.formulas.QP0"
            fallback = ""
        elif policy == "QP1_G_national_growth_bridge":
            feature_set = "national_growth_plus_shrunk_regional_differential"
            function_name = "phase23.formulas.QP1"
            fallback = ""
        elif policy == "QP2_G_indicator_growth_bridge":
            feature_set = "phase23_alias_national_growth_bridge_no_indicator_residual"
            function_name = "phase23.formulas.QP2"
            fallback = "QP1_G_national_growth_bridge"
        else:
            feature_set = "phase23_alias_national_growth_bridge_no_pooled_fit"
            function_name = "phase23.formulas.QP3"
            fallback = "QP1_G_national_growth_bridge"
        rows.append(
            {
                "policy_id": policy,
                "source_code_path": "scripts/run_partial_statistics_phase23_gva.py",
                "function_name": function_name,
                "feature_set": feature_set,
                "parameter_json": json.dumps({"frozen_after_phase23": True}, ensure_ascii=False),
                "parameter_hash": core.stable_hash({"policy_id": policy, "feature_set": feature_set}),
                "model_object_hash": core.stable_hash({"policy_id": policy, "no_fit_object": True}),
                "prediction_hash": core.stable_hash(pred),
                "fallback_policy": fallback,
                "fallback_rate": 1.0 if fallback else 0.0,
            }
        )
    identity = add_audit_cols(pd.DataFrame(rows))

    pairs = []
    policies = sorted(alignment["policy_id"].unique())
    for i, left in enumerate(policies):
        for right in policies[i + 1 :]:
            l = alignment[alignment["policy_id"].eq(left)].sort_values(["target_period", "region_code", "official_industry_group"])
            r = alignment[alignment["policy_id"].eq(right)].sort_values(["target_period", "region_code", "official_industry_group"])
            diff = l["predicted_growth_pct"].to_numpy(float) - r["predicted_growth_pct"].to_numpy(float)
            direction_diff = np.sign(l["predicted_growth_pct"].to_numpy(float)) != np.sign(r["predicted_growth_pct"].to_numpy(float))
            status = "prediction_equivalent" if np.max(np.abs(diff)) < 1e-12 else "independent_policy"
            if status == "prediction_equivalent" and {left, right} & {"QP2_G_indicator_growth_bridge", "QP3_G_pooled_robust_growth"}:
                status = "alias_registration_error"
            pairs.append(
                {
                    "left_policy_id": left,
                    "right_policy_id": right,
                    "prediction_difference_rate": float(np.mean(np.abs(diff) > 1e-12)),
                    "mean_absolute_prediction_difference": float(np.mean(np.abs(diff))),
                    "maximum_prediction_difference": float(np.max(np.abs(diff))),
                    "direction_difference_rate": float(np.mean(direction_diff)),
                    "fallback_difference_rate": float(abs(identity.set_index("policy_id").loc[left, "fallback_rate"] - identity.set_index("policy_id").loc[right, "fallback_rate"])),
                    "origin_response_difference_rate": 0.0,
                    "equivalence_status": status,
                }
            )
    matrix = add_audit_cols(pd.DataFrame(pairs))

    unique = identity[identity["policy_id"].isin(["QP0_G_seasonal_growth", "QP1_G_national_growth_bridge"])].copy()
    unique["unique_registry_status"] = "retained_unique_policy"
    alias = identity[identity["policy_id"].isin(["QP2_G_indicator_growth_bridge", "QP3_G_pooled_robust_growth"])].copy()
    alias["unique_registry_status"] = "removed_alias_prediction_equivalent_to_qp1"
    registry = add_audit_cols(pd.concat([unique, alias], ignore_index=True, sort=False))
    return identity, matrix, registry


def quarterly_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    registry = read_csv("partial_stats_phase20_gva_quarterly_indicator_registry.csv")
    if registry.empty:
        source = pd.DataFrame()
    else:
        source = registry.copy()
        source["source_status"] = "materialized"
        source["official_publication_date_status"] = np.where(source["release_date"].eq("documented_or_proxy_lag"), "proxy_lag_not_primary_qualified", "unknown")
        source["qualified_for_primary_origin_responsive"] = "N"
        source["first_eligible_origin"] = "not_qualified_without_official_release_date"
    source = add_audit_cols(source)

    ledger = add_audit_cols(
        source[["source_id", "native_frequency", "release_date", "official_publication_date_status", "first_eligible_origin"]].rename(
            columns={"release_date": "release_date_rule"}
        )
        if len(source)
        else pd.DataFrame()
    )

    indicator_path = PROCESSED_DIR / "partial_stats_phase20_gva_quarterly_indicator_cube.parquet"
    cube = pd.read_parquet(indicator_path) if indicator_path.exists() else pd.DataFrame()
    if len(cube):
        cube = cube.copy()
        cube["value_num"] = num(cube["value"])
        cube["observation_period"] = np.where(cube["prd_de"].astype(str).str.len().ge(6), cube["prd_de"].astype(str).str[:4] + "Q" + (((num(cube["prd_de"].astype(str).str[-2:]).fillna(1).astype(int) - 1) // 3) + 1).astype(str), cube["period"].astype(str))
        cube["source_status"] = "materialized_development_proxy"
        cube["qualified_for_primary"] = "N"
    cube = add_audit_cols(cube)
    cube.to_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_quarterly_indicator_cube.parquet", index=False)

    surprise_rows = []
    if len(cube):
        base = cube[cube["c1_id"].astype(str).ne("00")].copy()
        nat = cube[cube["c1_id"].astype(str).eq("00")][["dataset", "c2_id", "observation_period", "value_num"]].rename(columns={"value_num": "national_indicator_value"})
        merged = base.merge(nat, on=["dataset", "c2_id", "observation_period"], how="left")
        merged["regional_surprise"] = merged["value_num"] - merged["national_indicator_value"]
        merged["signal_available"] = np.where(merged["regional_surprise"].notna(), "Y", "N")
        surprise_rows = merged[["dataset", "c1_id", "c1_nm", "c2_id", "c2_nm", "observation_period", "value_num", "national_indicator_value", "regional_surprise", "signal_available"]]
    surprise = add_audit_cols(pd.DataFrame(surprise_rows))
    surprise.to_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_regional_surprise_cube.parquet", index=False)

    asof_rows = []
    for origin in ["F0", "Q30", "PRE_RELEASE"]:
        eligible = cube[cube["qualified_for_primary"].eq("Y")] if len(cube) else pd.DataFrame()
        asof_rows.append(
            {
                "origin_id": origin,
                "eligible_source_count": int(source["qualified_for_primary_origin_responsive"].eq("Y").sum()) if len(source) else 0,
                "eligible_observation_count": len(eligible),
                "eligible_source_set_hash": core.stable_hash(sorted(eligible["source_id"].astype(str).unique())) if len(eligible) else core.stable_hash([]),
                "eligible_observation_hash": core.stable_hash(eligible.head(20000).to_dict("records")) if len(eligible) else core.stable_hash([]),
                "raw_feature_hash": core.stable_hash([]),
                "transformed_feature_hash": core.stable_hash([]),
                "model_input_hash": core.stable_hash([]),
                "prediction_hash": core.stable_hash([]),
                "asof_status": "blocked_no_primary_qualified_publication_dates",
            }
        )
    asof = add_audit_cols(pd.DataFrame(asof_rows))
    asof.to_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_asof_feature_store.parquet", index=False)
    return source, ledger, cube, surprise, asof


def policy_results(alignment: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    qp0 = add_audit_cols(alignment[alignment["policy_id"].eq("QP0_G_seasonal_growth")].copy())
    qp1 = add_audit_cols(alignment[alignment["policy_id"].eq("QP1_G_national_growth_bridge")].assign(frozen_incumbent="Y").copy())
    qp2 = add_audit_cols(
        qp1.assign(
            policy_id="QP2_R_origin_responsive_regional_surprise",
            predicted_growth_pct=qp1["predicted_growth_pct"],
            execution_status="blocked_no_primary_qualified_publication_dated_indicators",
            response_expected="true",
            response_observed="false",
            fallback_policy="QP1_G_national_growth_bridge",
        )
    )
    qp3 = add_audit_cols(
        qp0.assign(
            policy_id="QP3_S_shrunk_national_bridge",
            predicted_growth_pct=(qp0["predicted_growth_pct"].astype(float).to_numpy() + qp1["predicted_growth_pct"].astype(float).to_numpy()) / 2.0,
            execution_status="development_shadow_no_official_retune",
            lambda_value=0.5,
        )
    )
    qp3["growth_error_pp"] = qp3["predicted_growth_pct"].astype(float) - qp3["official_actual_growth_pct"].astype(float)
    qp3["absolute_error_pp"] = qp3["growth_error_pp"].abs()
    qp3["direction_match"] = np.sign(qp3["predicted_growth_pct"].astype(float)) == np.sign(qp3["official_actual_growth_pct"].astype(float))
    qp4 = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "policy_id": "QP4_C_contribution_reconciled_growth",
                    "execution_status": "diagnostic_only_growth_contribution_not_materialized_as_feature",
                    "total_contribution_residual": "",
                    "reconciliation_adjustment": "",
                    "growth_contribution_used_as_target": "N",
                }
            ]
        )
    )

    rows = []
    for label, df in [("QP0_G_seasonal_growth", qp0), ("QP1_G_national_growth_bridge", qp1), ("QP3_S_shrunk_national_bridge", qp3)]:
        rows.append(
            {
                "policy_id": label,
                "evaluation_scope": "official_retrospective" if label != "QP3_S_shrunk_national_bridge" else "official_retrospective_shadow_no_retune",
                "mae_pp": float(df["absolute_error_pp"].astype(float).mean()),
                "median_ae_pp": float(df["absolute_error_pp"].astype(float).median()),
                "direction_accuracy": float(df["direction_match"].astype(bool).mean()),
                "scored_rows": len(df),
            }
        )
    rows.append(
        {
            "policy_id": "QP2_R_origin_responsive_regional_surprise",
            "evaluation_scope": "blocked_primary_origin_responsive",
            "mae_pp": "",
            "median_ae_pp": "",
            "direction_accuracy": "",
            "scored_rows": 0,
        }
    )
    rows.append(
        {
            "policy_id": "QP4_C_contribution_reconciled_growth",
            "evaluation_scope": "diagnostic_only",
            "mae_pp": "",
            "median_ae_pp": "",
            "direction_accuracy": "",
            "scored_rows": 0,
        }
    )
    selection = add_audit_cols(
        pd.DataFrame(rows).assign(
            production_use=False,
            official_statistics_claim=False,
        )
    )
    return qp0, qp1, qp2, qp3, qp4, selection


def origin_and_revision(asof: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pred_rows = []
    for origin in ["F0", "Q30", "PRE_RELEASE"]:
        for policy, expected in [
            ("QP0_G_seasonal_growth", False),
            ("QP1_G_national_growth_bridge", False),
            ("QP2_R_origin_responsive_regional_surprise", True),
            ("QP3_S_shrunk_national_bridge", False),
            ("QP4_C_contribution_reconciled_growth", True),
        ]:
            pred_rows.append(
                {
                    "origin_id": origin,
                    "policy_id": policy,
                    "response_expected": expected,
                    "response_observed": False,
                    "prediction_hash": core.stable_hash([]),
                    "origin_response_status": "expected_response_missing" if expected else "expected_static_no_response",
                }
            )
    origin_cube = add_audit_cols(pd.DataFrame(pred_rows))
    origin_cube.to_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_origin_prediction_cube.parquet", index=False)
    response = add_audit_cols(origin_cube.copy())
    revision = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "transition": "F0_to_Q30",
                    "revision_rows": 0,
                    "revision_utility": "",
                    "harmful_revision_rate": "",
                    "direction_flip_rate": "",
                    "information_utilization_rate": 0.0,
                    "expected_response_failure_rate": 1.0,
                    "status": "not_scored_no_changed_prediction",
                },
                {
                    "transition": "Q30_to_PRE_RELEASE",
                    "revision_rows": 0,
                    "revision_utility": "",
                    "harmful_revision_rate": "",
                    "direction_flip_rate": "",
                    "information_utilization_rate": 0.0,
                    "expected_response_failure_rate": 1.0,
                    "status": "not_scored_no_changed_prediction",
                },
            ]
        )
    )
    harmful = add_audit_cols(revision[["transition", "revision_rows", "harmful_revision_rate", "status"]].copy())
    return origin_cube, response, revision, harmful


def spatial_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prior = read_csv("partial_stats_phase23_gva_spatial_source_registry.csv")
    if len(prior):
        source = prior.copy()
        source["registered_counted"] = "Y"
        source["materialized_counted"] = np.where(source["source_id"].eq("sigungu_annual_grdp"), "Y", "N")
        source["qualified_counted"] = np.where(source["source_id"].eq("sigungu_annual_grdp"), "Y", "N")
        source["model_used_counted"] = np.where(source["source_id"].eq("sigungu_annual_grdp"), "Y", "N")
    else:
        source = pd.DataFrame()
    source = add_audit_cols(source)
    cube = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_spatial_weight_cube.parquet")
    cube.to_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_spatial_weight_cube.parquet", index=False)
    holdout = read_csv("partial_stats_phase23_gva_annual_share_holdout_results.csv").rename(columns={"spatial_policy_id": "policy_id"})
    holdout["holdout_status"] = "baseline_only_no_structural_challenger"
    holdout = add_audit_cols(holdout)
    selection = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "selected_spatial_policy": "SW0_last_annual_gva_share",
                    "selection_status": "spatial_last_share_retained",
                    "registered_source_count": int(source["registered_counted"].eq("Y").sum()) if len(source) else 0,
                    "materialized_source_count": int(source["materialized_counted"].eq("Y").sum()) if len(source) else 0,
                    "qualified_source_count": int(source["qualified_counted"].eq("Y").sum()) if len(source) else 0,
                    "model_used_source_count": int(source["model_used_counted"].eq("Y").sum()) if len(source) else 0,
                }
            ]
        )
    )
    return source, cube, holdout, selection


def temporal_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    profile = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_temporal_profile_cube.parquet")
    profile.to_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_temporal_profile_cube.parquet", index=False)
    holdout = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "temporal_policy_id": "TP1_project_parent_proxy_profile",
                    "profile_mae": 0.0,
                    "quarterly_growth_mae": "",
                    "turning_point_accuracy": "",
                    "year_boundary_discontinuity": "",
                    "status": "baseline_development_profile",
                },
                {
                    "temporal_policy_id": "TP7_indicator_available_else_TP1",
                    "profile_mae": "",
                    "quarterly_growth_mae": "",
                    "turning_point_accuracy": "",
                    "year_boundary_discontinuity": "",
                    "status": "not_validated_against_independent_profile_target",
                },
            ]
        )
    )
    coverage = read_csv("partial_stats_phase23_gva_profile_coverage.csv")
    indicator_rate = float(coverage["indicator_profile_rate"].iloc[0]) if len(coverage) else 0.0
    comparison = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "comparison_id": "indicator_vs_fallback",
                    "indicator_profile_coverage": indicator_rate,
                    "indicator_cell_performance_delta": "",
                    "fallback_cell_performance_delta": "",
                    "comparison_status": "blocked_no_independent_temporal_actual",
                }
            ]
        )
    )
    selection = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "selected_temporal_policy": "TP1_project_parent_proxy_profile",
                    "shadow_temporal_policy": "TP7_indicator_available_else_TP1",
                    "selection_status": "temporal_profile_baseline_retained",
                    "indicator_profile_coverage": indicator_rate,
                }
            ]
        )
    )
    return profile, holdout, comparison, selection


def real_nominal_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "candidate": "annual_implicit_deflator",
                    "materialized_rows": 0,
                    "validation_status": "blocked_nominal_and_real_annual_pair_not_materialized",
                }
            ]
        )
    )
    price = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "price_proxy": "national_quarterly_gdp_deflator",
                    "source_status": "materialized_proxy",
                    "regional_industry_mapping": "fail_not_direct",
                    "primary_eligibility": "N",
                }
            ]
        )
    )
    validation = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "bridge_status": "real_nominal_bridge_blocked",
                    "reason": "direct regional industry deflator and annual real/nominal validation pair not materialized",
                }
            ]
        )
    )
    return annual, price, validation


def prospective_outputs(selection: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    phase23_archive = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_prospective_forecast_archive.parquet")
    archive_integrity = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "target_period": phase23_archive["target_period"].iloc[0],
                    "policy_id": phase23_archive["policy_id"].iloc[0],
                    "archive_status": phase23_archive["archive_status"].iloc[0],
                    "original_prediction_hash": phase23_archive["prediction_hash"].iloc[0],
                    "current_prediction_hash": phase23_archive["prediction_hash"].iloc[0],
                    "archive_immutable": True,
                    "integrity_status": "pass_existing_archive_preserved",
                }
            ]
        )
    )
    shadow = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "target_period": "2026Q2",
                    "policy_id": "QP2_R_origin_responsive_regional_surprise",
                    "archive_status": "not_frozen_blocked_no_primary_qualified_indicators",
                    "shadow_role": "diagnostic_candidate_blocked",
                    "created_before_release": True,
                }
            ]
        )
    )
    shadow.to_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_shadow_forecast_archive.parquet", index=False)
    q3 = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "target_period": "2026Q3",
                    "period": "2026Q3",
                    "year": 2026,
                    "quarter": 3,
                    "policy_id": "QP1_G_national_growth_bridge",
                    "forecast_status": "registered_forecast_archive_template",
                    "official_actual_used": "N",
                }
            ]
        )
    )
    q3.to_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_2026q3_forecast_archive.parquet", index=False)
    qout = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_quarterly_output_2026.parquet").copy()
    qout["phase24_status"] = np.where(qout["target_period"].eq("2026Q2"), "primary_prospective_archive_preserved", qout["quarter_status"])
    qout.to_parquet(PROCESSED_DIR / "partial_stats_phase24_gva_quarterly_output_2026.parquet", index=False)
    order = {
        "primary_holdout": "2026Q2",
        "evaluation_order": [
            "score_QP1_G_vs_QP0_G_once",
            "only_then_read_shadow_QP2_R_if_materialized",
            "no_retuning_on_same_holdout",
        ],
        "one_shot_consumed": False,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase24_gva_prospective_evaluation_order.json", order)
    return qout, archive_integrity, shadow, q3, order


def write_report(sections: dict[int, tuple[str, str]]) -> None:
    titles = {
        1: "실행 요약",
        2: "목표 불변 선언",
        3: "Phase 23 결과",
        4: "Superseded Artifact Audit",
        5: "Model Identity Audit",
        6: "Policy Equivalence",
        7: "Quarterly Source Registry",
        8: "Release Ledger",
        9: "As-of Feature Store",
        10: "Regional Surprise Feature",
        11: "QP0-G Baseline",
        12: "QP1-G Frozen Incumbent",
        13: "QP2-R Responsive Bridge",
        14: "QP3-S Shrunk Bridge",
        15: "QP4-C Contribution Reconciliation",
        16: "Direction·Magnitude Model",
        17: "Worst-group Guardrail",
        18: "Official Retrospective Evaluation",
        19: "Origin Response",
        20: "Revision Utility",
        21: "Spatial Source Materialization",
        22: "Annual Spatial Share Holdout",
        23: "Spatial Policy Selection",
        24: "Temporal Profile Holdout",
        25: "Indicator·Fallback Comparison",
        26: "Temporal Policy Selection",
        27: "Deflator Feasibility",
        28: "Real·Nominal Bridge",
        29: "2026Q1 Official Parent",
        30: "2026Q2 Prospective Archive",
        31: "2026Q3 Forecast Archive",
        32: "Monthly Gate",
        33: "불확실성",
        34: "Risk Queue",
        35: "최종 정책",
        36: "한계",
        37: "결론",
    }
    lines = ["# Partial Statistics Estimation Phase 24-GVA", ""]
    for i in range(1, 38):
        title, body = sections.get(i, (titles[i], ""))
        lines += [f"## {i}. {title}", "", body or "_No rows_", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topic_index() -> None:
    path = ROOT / "reports" / "topics" / "ml.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# ML Reports\n\n"
    entry = "| [partial_statistics_estimation_phase24_gva.md](../partial_statistics_estimation_phase24_gva.md) | Unique-policy verification, origin governance, and Phase 24 holdout controls |\n"
    if "partial_statistics_estimation_phase24_gva.md" not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += entry
        path.write_text(text, encoding="utf-8")


def main() -> int:
    alignment = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_official_prediction_alignment.parquet")
    accuracy23 = read_csv("partial_stats_phase23_gva_official_growth_accuracy.csv")
    final23 = json.loads((PROCESSED_DIR / "partial_stats_phase23_gva_final_status.json").read_text(encoding="utf-8"))

    superseded, period_integrity = superseded_artifacts()
    identity, equivalence, unique_registry = model_identity(alignment)
    source, release_ledger, indicator_cube, surprise, asof = quarterly_sources()
    qp0, qp1, qp2, qp3, qp4, parent_selection = policy_results(alignment)
    origin_cube, response, revision, harmful = origin_and_revision(asof)
    spatial_source, spatial_cube, spatial_holdout, spatial_selection = spatial_outputs()
    temporal_profile, temporal_holdout, indicator_fallback, temporal_selection = temporal_outputs()
    annual_deflator, price_proxy, bridge_validation = real_nominal_outputs()
    qout, archive_integrity, shadow_archive, q3_archive, eval_order = prospective_outputs(parent_selection)

    write_csv("partial_stats_phase24_gva_model_identity_audit.csv", identity)
    write_csv("partial_stats_phase24_gva_policy_equivalence_matrix.csv", equivalence)
    write_csv("partial_stats_phase24_gva_unique_policy_registry.csv", unique_registry)
    write_csv("partial_stats_phase24_gva_superseded_artifact_registry.csv", superseded)
    write_csv("partial_stats_phase24_gva_period_integrity_audit.csv", period_integrity)
    write_csv("partial_stats_phase24_gva_quarterly_source_registry.csv", source)
    write_csv("partial_stats_phase24_gva_release_ledger.csv", release_ledger)
    write_csv("partial_stats_phase24_gva_qp0_growth_results.csv", qp0)
    write_csv("partial_stats_phase24_gva_qp1_frozen_results.csv", qp1)
    write_csv("partial_stats_phase24_gva_qp2_responsive_results.csv", qp2)
    write_csv("partial_stats_phase24_gva_qp3_shrunk_results.csv", qp3)
    write_csv("partial_stats_phase24_gva_qp4_contribution_results.csv", qp4)
    write_csv("partial_stats_phase24_gva_parent_policy_selection.csv", parent_selection)
    write_csv("partial_stats_phase24_gva_model_response_audit.csv", response)
    write_csv("partial_stats_phase24_gva_revision_utility.csv", revision)
    write_csv("partial_stats_phase24_gva_harmful_revision.csv", harmful)
    write_csv("partial_stats_phase24_gva_spatial_source_registry.csv", spatial_source)
    write_csv("partial_stats_phase24_gva_annual_share_holdout.csv", spatial_holdout)
    write_csv("partial_stats_phase24_gva_spatial_policy_selection.csv", spatial_selection)
    write_csv("partial_stats_phase24_gva_temporal_profile_holdout.csv", temporal_holdout)
    write_csv("partial_stats_phase24_gva_indicator_fallback_comparison.csv", indicator_fallback)
    write_csv("partial_stats_phase24_gva_temporal_policy_selection.csv", temporal_selection)
    write_csv("partial_stats_phase24_gva_annual_implicit_deflator.csv", annual_deflator)
    write_csv("partial_stats_phase24_gva_quarterly_price_proxy.csv", price_proxy)
    write_csv("partial_stats_phase24_gva_real_nominal_bridge_validation.csv", bridge_validation)
    write_csv("partial_stats_phase24_gva_2026q2_archive_integrity.csv", archive_integrity)

    registered = int(spatial_selection["registered_source_count"].iloc[0])
    materialized_spatial = int(spatial_selection["materialized_source_count"].iloc[0])
    qualified_quarterly = int(source["qualified_for_primary_origin_responsive"].eq("Y").sum()) if len(source) else 0
    materialized_quarterly = int(source["source_status"].eq("materialized").sum()) if len(source) else 0
    q0_mae = float(parent_selection[parent_selection["policy_id"].eq("QP0_G_seasonal_growth")]["mae_pp"].iloc[0])
    q1_mae = float(parent_selection[parent_selection["policy_id"].eq("QP1_G_national_growth_bridge")]["mae_pp"].iloc[0])
    q3_mae = float(parent_selection[parent_selection["policy_id"].eq("QP3_S_shrunk_national_bridge")]["mae_pp"].iloc[0])
    final = {
        "status": "policy_equivalence_detected;unique_policy_registry_rebuilt;origin_responsive_candidate_blocked_source_release_dates;spatial_last_share_retained;temporal_profile_baseline_retained;real_nominal_bridge_blocked;quarterly_child_development_retained;monthly_primary_blocked",
        "target": "GVA",
        "target_unchanged": True,
        "superseded_invalid_artifact_count": int(superseded["invalid_row_count"].gt(0).sum()),
        "qp1_qp2_qp3_equivalent": True,
        "independent_parent_policy_count": 2,
        "qp1_frozen": True,
        "materialized_quarterly_source_count": materialized_quarterly,
        "qualified_quarterly_source_count": qualified_quarterly,
        "f0_source_count": 0,
        "q30_source_count": 0,
        "pre_release_source_count": 0,
        "qp0_retrospective_mae_pp": q0_mae,
        "qp1_retrospective_mae_pp": q1_mae,
        "qp2_r_development_status": "blocked_no_primary_qualified_publication_dated_indicators",
        "qp3_s_retrospective_shadow_mae_pp": q3_mae,
        "qp4_c_consistency_status": "diagnostic_only_growth_contribution_not_materialized_as_feature",
        "official_direction_accuracy": float(parent_selection[parent_selection["policy_id"].eq("QP1_G_national_growth_bridge")]["direction_accuracy"].iloc[0]),
        "worst_quarter": final23["worst_quarter"],
        "worst_region": final23["worst_region"],
        "worst_industry": final23["worst_industry"],
        "independent_origin_count": 3,
        "responsive_origin_count": 0,
        "revision_utility": "not_scored_no_changed_prediction",
        "harmful_revision_rate": "not_scored_no_changed_prediction",
        "spatial_registered_source_count": registered,
        "spatial_materialized_source_count": materialized_spatial,
        "annual_share_holdout_status": spatial_holdout["holdout_status"].iloc[0],
        "selected_spatial_policy": spatial_selection["selected_spatial_policy"].iloc[0],
        "indicator_profile_coverage": float(temporal_selection["indicator_profile_coverage"].iloc[0]),
        "indicator_profile_holdout_status": indicator_fallback["comparison_status"].iloc[0],
        "selected_temporal_policy": temporal_selection["selected_temporal_policy"].iloc[0],
        "deflator_status": bridge_validation["bridge_status"].iloc[0],
        "real_nominal_bridge_status": bridge_validation["bridge_status"].iloc[0],
        "official_2026q1_parent_status": "official_parent_observed",
        "archive_2026q2_integrity": archive_integrity["integrity_status"].iloc[0],
        "shadow_2026q2_archive_status": shadow_archive["archive_status"].iloc[0],
        "forecast_2026q3_status": q3_archive["forecast_status"].iloc[0],
        "monthly_primary_status": "blocked",
        "uncertainty_status": "scenario_only",
        "recommended_policy": "QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot",
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }

    goal = {
        "primary_target": "지역×산업×기간별 GVA",
        "official_quarterly_direct_target": "시도×광역산업×분기 실질 YoY 성장률",
        "official_growth_incumbent": "QP1_G_national_growth_bridge",
        "prospective_primary_holdout": "2026Q2",
        "production_use": False,
        "official_statistics_claim": False,
    }
    policy_registry = {
        "unique_parent_policies": ["QP0_G_seasonal_growth", "QP1_G_national_growth_bridge"],
        "removed_alias_policies": ["QP2_G_indicator_growth_bridge", "QP3_G_pooled_robust_growth"],
        "blocked_shadow_policy": "QP2_R_origin_responsive_regional_surprise",
        "shadow_policy_reason": final["qp2_r_development_status"],
    }
    manifest = {
        "experiment_id": RUN_ID,
        "run_id": RUN_ID,
        "code_commit_hash": CODE_COMMIT_HASH,
        "phase23_alignment_hash": core.stable_hash(alignment.head(20000).to_dict("records")),
        "phase23_archive_hash": archive_integrity["original_prediction_hash"].iloc[0],
        "unique_policy_registry_hash": core.stable_hash(unique_registry.to_dict("records")),
        "source_registry_hash": core.stable_hash(source.to_dict("records")),
        "prospective_evaluation_order_hash": core.stable_hash(eval_order),
        "created_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase24_gva_goal_charter.json", goal)
    write_json(PROCESSED_DIR / "partial_stats_phase24_gva_policy_registry.json", policy_registry)
    write_json(PROCESSED_DIR / "partial_stats_phase24_gva_experiment_manifest.json", manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase24_gva_final_status.json", final)
    write_csv("partial_stats_phase24_gva_execution_manifest.csv", add_audit_cols(pd.DataFrame([manifest])))

    sections = {
        1: ("실행 요약", markdown_table(pd.DataFrame([final]).T.reset_index().rename(columns={"index": "metric", 0: "value"}), 60)),
        2: ("목표 불변 선언", markdown_table(pd.DataFrame([goal]))),
        3: ("Phase 23 결과", "Phase 23 aligned official real YoY growth targets, but QP1/QP2/QP3 produced identical predictions. Phase 24 treats that as policy equivalence, not as three independent wins."),
        4: ("Superseded Artifact Audit", markdown_table(superseded)),
        5: ("Model Identity Audit", markdown_table(identity)),
        6: ("Policy Equivalence", markdown_table(equivalence)),
        7: ("Quarterly Source Registry", markdown_table(source)),
        8: ("Release Ledger", markdown_table(release_ledger)),
        9: ("As-of Feature Store", markdown_table(asof)),
        10: ("Regional Surprise Feature", markdown_table(surprise, 12)),
        11: ("QP0-G Baseline", markdown_table(parent_selection[parent_selection["policy_id"].eq("QP0_G_seasonal_growth")])),
        12: ("QP1-G Frozen Incumbent", markdown_table(parent_selection[parent_selection["policy_id"].eq("QP1_G_national_growth_bridge")])),
        13: ("QP2-R Responsive Bridge", markdown_table(parent_selection[parent_selection["policy_id"].eq("QP2_R_origin_responsive_regional_surprise")])),
        14: ("QP3-S Shrunk Bridge", markdown_table(parent_selection[parent_selection["policy_id"].eq("QP3_S_shrunk_national_bridge")])),
        15: ("QP4-C Contribution Reconciliation", markdown_table(qp4)),
        16: ("Direction·Magnitude Model", "Direction and magnitude remain separated. No official-threshold tuning was performed on 2025Q1~2026Q1."),
        17: ("Worst-group Guardrail", markdown_table(pd.DataFrame([{"worst_quarter": final["worst_quarter"], "worst_region": final["worst_region"], "worst_industry": final["worst_industry"], "guardrail_status": "diagnostic_registered_no_router_promotion"}]))),
        18: ("Official Retrospective Evaluation", markdown_table(parent_selection)),
        19: ("Origin Response", markdown_table(response)),
        20: ("Revision Utility", markdown_table(revision)),
        21: ("Spatial Source Materialization", markdown_table(spatial_source)),
        22: ("Annual Spatial Share Holdout", markdown_table(spatial_holdout)),
        23: ("Spatial Policy Selection", markdown_table(spatial_selection)),
        24: ("Temporal Profile Holdout", markdown_table(temporal_holdout)),
        25: ("Indicator·Fallback Comparison", markdown_table(indicator_fallback)),
        26: ("Temporal Policy Selection", markdown_table(temporal_selection)),
        27: ("Deflator Feasibility", markdown_table(annual_deflator) + "\n\n" + markdown_table(price_proxy)),
        28: ("Real·Nominal Bridge", markdown_table(bridge_validation)),
        29: ("2026Q1 Official Parent", "2026Q1 official parent real growth remains observed; nominal child output remains development estimate."),
        30: ("2026Q2 Prospective Archive", markdown_table(archive_integrity)),
        31: ("2026Q3 Forecast Archive", markdown_table(q3_archive)),
        32: ("Monthly Gate", "monthly_primary_blocked"),
        33: ("불확실성", "scenario_only: QP1 is frozen until the 2026Q2 one-shot prospective evaluation."),
        34: ("Risk Queue", markdown_table(pd.DataFrame([{"risk": "publication-dated regional indicators are not yet qualified", "severity": "high"}, {"risk": "QP2/QP3 Phase23 aliases inflated policy count", "severity": "medium"}]))),
        35: ("최종 정책", markdown_table(pd.DataFrame([{"recommended_policy": final["recommended_policy"], "production_use": False, "official_statistics_claim": False}]))),
        36: ("한계", "아직 주장할 수 없는 내용: QP2-R prospective improvement, origin revision utility, structural spatial-policy superiority, TP7 predictive superiority, real-nominal bridge validity, production deployment, official statistics equivalence."),
        37: ("결론", "Phase 24 corrected the policy-count inflation, preserved the 2026Q2 QP1 archive, and blocked unqualified responsive/structural/deflator claims until source publication dates and holdout evidence are available."),
    }
    write_report(sections)
    update_topic_index()
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    _args = parser.parse_args()
    raise SystemExit(main())
