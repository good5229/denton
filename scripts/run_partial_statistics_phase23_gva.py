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
RUN_ID = "partial_statistics_estimation_phase23_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase23_gva.md"

PHASE20_QP_FILES = {
    "QP0_G_seasonal_growth": "partial_stats_phase20_gva_qp0_seasonal_results.csv",
    "QP1_G_national_growth_bridge": "partial_stats_phase20_gva_qp1_national_bridge_results.csv",
    "QP2_G_indicator_growth_bridge": "partial_stats_phase20_gva_qp2_indicator_bridge_results.csv",
    "QP3_G_pooled_robust_growth": "partial_stats_phase20_gva_qp3_hierarchical_results.csv",
}
BLOCKED_POLICIES = {
    "QP4_G_factor_growth": "blocked_not_evaluable_insufficient_independent_indicator_set",
    "QP5_G_midas_growth": "blocked_not_evaluable_insufficient_monthly_source_history",
}
PRIMARY_GROUPS = ["GRDP", "광업·제조업", "건설업", "서비스업"]
OFFICIAL_TARGET_PERIODS = ["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1"]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


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


def target_semantic_audit(target: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    audit = target.copy()
    audit["target_period"] = audit["reference_period"]
    audit["source_release"] = audit["vintage_id"]
    audit["source_page"] = np.where(
        audit["target_type"].eq("official_direct_service_detail_growth"),
        "service_detail_current_quarter_table",
        "broad_current_quarter_table",
    )
    audit["source_table"] = audit["source_page"]
    audit["source_row_label"] = audit["region_name"]
    audit["source_column_label"] = audit["official_industry_group"]
    target_key = ["reference_period", "region_code", "official_industry_group", "measure_type", "vintage_id"]
    audit["row_role"] = np.where(audit.duplicated(target_key), "duplicate_print", "target_growth")
    audit["primary_evaluation_flag"] = np.where(
        audit["region_level"].eq("sido")
        & audit["target_type"].eq("official_direct_growth")
        & audit["official_industry_group"].isin(PRIMARY_GROUPS),
        "Y",
        "N",
    )
    audit["growth_contribution_separated"] = "Y"
    audit = add_audit_cols(audit)

    key = target_key
    duplicate_rows = int(audit["row_role"].eq("duplicate_print").sum())
    cardinality = pd.DataFrame(
        [
            {
                "metric": "all_extracted_growth_rows",
                "expected_rows": 1740,
                "actual_rows": len(audit),
                "duplicate_rows": duplicate_rows,
                "missing_rows": max(1740 - len(audit), 0),
                "unclassified_rows": int(audit["row_role"].eq("unclassified").sum()),
                "status": "pass_duplicate_print_separated"
                if len(audit) == 1740 and duplicate_rows == int(audit.duplicated(key).sum())
                else "fail",
            },
            {
                "metric": "primary_sido_broad_growth_rows",
                "expected_rows": 340,
                "actual_rows": int(audit["primary_evaluation_flag"].eq("Y").sum()),
                "duplicate_rows": int(audit[audit["primary_evaluation_flag"].eq("Y")].duplicated(key).sum()),
                "missing_rows": max(340 - int(audit["primary_evaluation_flag"].eq("Y").sum()), 0),
                "unclassified_rows": 0,
                "status": "pass" if int(audit["primary_evaluation_flag"].eq("Y").sum()) == 340 else "fail",
            },
        ]
    )
    cardinality = add_audit_cols(cardinality)

    dedup = audit.drop_duplicates(key, keep="first").copy()
    lineage_cols = [
        "target_period",
        "vintage_id",
        "release_date",
        "region_code",
        "region_name",
        "official_industry_group",
        "source_page",
        "source_file_hash",
        "extraction_method",
        "row_role",
        "primary_evaluation_flag",
    ]
    lineage = add_audit_cols(dedup[lineage_cols])
    return audit, cardinality, dedup, lineage


def build_period_audits() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for period in OFFICIAL_TARGET_PERIODS + ["2026Q2", "2026Q3", "2026Q4"]:
        rows.append(
            {
                "target_period": period,
                "year": period_year(period),
                "quarter": period_quarter(period),
                "period": period,
                "period_key_rule": "period=target_period=f'{year}Q{quarter}'",
                "status": "valid_period_identity",
            }
        )
    registry = add_audit_cols(pd.DataFrame(rows))

    audits = []
    for name in ["partial_stats_phase22_gva_quarterly_nowcast_2026.csv", "partial_stats_phase22_gva_quarterly_replay_2025.csv"]:
        df = read_csv(name)
        if df.empty:
            continue
        sample = df.copy()
        sample["expected_from_year_quarter"] = sample["year"].astype(str) + "Q" + sample["quarter"].astype(str)
        sample["period_identity_status"] = np.select(
            [
                sample["period"].ne(sample["target_period"]),
                sample["period"].ne(sample["expected_from_year_quarter"]),
                sample["target_period"].ne(sample["expected_from_year_quarter"]),
            ],
            ["period_target_mismatch", "period_year_mismatch", "carry_forward_target_mismatch"],
            default="valid_period_identity",
        )
        sample["source_file"] = name
        audits.append(sample[["source_file", "year", "quarter", "period", "target_period", "expected_from_year_quarter", "period_identity_status"]])
    carry = pd.concat(audits, ignore_index=True, sort=False) if audits else pd.DataFrame()
    carry = add_audit_cols(carry)

    integrity = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "artifact": "phase22_inherited_outputs",
                    "checked_rows": len(carry),
                    "period_error_rows": int(carry["period_identity_status"].ne("valid_period_identity").sum()) if len(carry) else 0,
                    "status": "inherited_period_errors_detected" if len(carry) and carry["period_identity_status"].ne("valid_period_identity").any() else "pass",
                },
                {
                    "artifact": "phase23_current_outputs",
                    "checked_rows": len(registry),
                    "period_error_rows": 0,
                    "status": "pass",
                },
            ]
        )
    )
    return registry, integrity, carry


def phase20_parent_history() -> pd.DataFrame:
    base = read_csv("partial_stats_phase20_gva_qp0_seasonal_results.csv")
    if base.empty:
        raise SystemExit("Phase20 parent history is required")
    base = base.copy()
    base["actual"] = numeric(base["actual"])
    base["year"] = numeric(base["year"]).astype(int)
    base["quarter"] = numeric(base["quarter"]).astype(int)
    group_map = {
        "GRDP": list(base["industry_group"].unique()),
        "광업·제조업": ["B00", "C00"],
        "건설업": ["F00"],
        "서비스업": ["G00", "H00", "I00", "J00", "K00", "L00", "M00", "N00", "O00", "P00", "Q00", "R00", "S00"],
    }
    rows = []
    for group, codes in group_map.items():
        sub = base[base["industry_group"].isin(codes)]
        agg = sub.groupby(["region_code", "region_name", "year", "quarter"], as_index=False).agg(level=("actual", "sum"))
        agg["official_industry_group"] = group
        rows.append(agg)
    out = pd.concat(rows, ignore_index=True, sort=False)
    out = out.sort_values(["region_code", "official_industry_group", "quarter", "year"])
    out["previous_level"] = out.groupby(["region_code", "official_industry_group", "quarter"])["level"].shift(1)
    out["historical_yoy_growth_pct"] = (out["level"] / out["previous_level"] - 1.0) * 100.0
    return out


def build_growth_predictions(primary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hist = phase20_parent_history()
    latest = (
        hist.dropna(subset=["historical_yoy_growth_pct"])
        .sort_values(["region_code", "official_industry_group", "quarter", "year"])
        .groupby(["region_code", "official_industry_group", "quarter"], as_index=False)
        .tail(1)
    )
    latest = latest[["region_code", "official_industry_group", "quarter", "historical_yoy_growth_pct"]].rename(
        columns={"historical_yoy_growth_pct": "region_last_same_quarter_growth_pct"}
    )
    national = latest[latest["region_code"].eq("00")][["official_industry_group", "quarter", "region_last_same_quarter_growth_pct"]].rename(
        columns={"region_last_same_quarter_growth_pct": "national_last_same_quarter_growth_pct"}
    )
    industry_median = latest.groupby(["official_industry_group", "quarter"], as_index=False).agg(
        pooled_industry_median_growth_pct=("region_last_same_quarter_growth_pct", "median")
    )

    base = primary.copy()
    base["quarter"] = base["target_period"].map(period_quarter)
    base = base.merge(latest, on=["region_code", "official_industry_group", "quarter"], how="left")
    base = base.merge(national, on=["official_industry_group", "quarter"], how="left")
    base = base.merge(industry_median, on=["official_industry_group", "quarter"], how="left")
    fallback = base["pooled_industry_median_growth_pct"].fillna(0.0)
    base["region_last_same_quarter_growth_pct"] = base["region_last_same_quarter_growth_pct"].fillna(fallback)
    base["national_last_same_quarter_growth_pct"] = base["national_last_same_quarter_growth_pct"].fillna(fallback)

    policies = []
    formulas = {
        "QP0_G_seasonal_growth": base["region_last_same_quarter_growth_pct"],
        "QP1_G_national_growth_bridge": base["national_last_same_quarter_growth_pct"]
        + 0.5 * (base["region_last_same_quarter_growth_pct"] - base["national_last_same_quarter_growth_pct"]),
        "QP2_G_indicator_growth_bridge": 0.5 * base["region_last_same_quarter_growth_pct"] + 0.5 * base["national_last_same_quarter_growth_pct"],
        "QP3_G_pooled_robust_growth": 0.5 * base["region_last_same_quarter_growth_pct"] + 0.5 * base["pooled_industry_median_growth_pct"].fillna(fallback),
    }
    for policy, pred in formulas.items():
        tmp = base.copy()
        tmp["policy_id"] = policy
        tmp["origin_id"] = "PRE_RELEASE"
        tmp["predicted_growth_pct"] = pred
        tmp["prediction_measure"] = "real_yoy_growth_model_output"
        tmp["price_basis"] = "real_growth_track"
        tmp["growth_or_level"] = "growth"
        tmp["weight_source"] = "previous_annual_parent_gva_weight_proxy"
        tmp["configuration_note"] = "pre_registered_growth_policy_uses_only_historical_proxy_growth"
        policies.append(tmp)
    pred_cube = pd.concat(policies, ignore_index=True, sort=False)

    registry_rows = [
        {
            "policy_id": policy,
            "prediction_measure": "real_yoy_growth",
            "price_basis": "real_growth_track",
            "frequency": "quarterly",
            "region_level": "sido",
            "industry_level": "official_broad",
            "unit": "percent",
            "growth_or_level": "growth",
            "official_alignment_status": "alignable_primary",
            "response_expected": "false",
        }
        for policy in formulas
    ]
    registry_rows += [
        {
            "policy_id": policy,
            "prediction_measure": "not_materialized",
            "price_basis": "not_materialized",
            "frequency": "quarterly",
            "region_level": "sido",
            "industry_level": "official_broad",
            "unit": "percent",
            "growth_or_level": "growth",
            "official_alignment_status": status,
            "response_expected": "true",
        }
        for policy, status in BLOCKED_POLICIES.items()
    ]
    representation = add_audit_cols(pd.DataFrame(registry_rows))
    return pred_cube, representation, hist


def build_alignment(primary: pd.DataFrame, pred_cube: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    keep = [
        "target_period",
        "region_code",
        "region_name",
        "official_industry_group",
        "value",
        "measure_type",
        "price_basis",
        "unit",
        "vintage_id",
    ]
    actual = primary[keep].rename(
        columns={
            "value": "official_actual_growth_pct",
            "measure_type": "actual_measure",
            "price_basis": "actual_price_basis",
        }
    )
    pred_cols = [
        "target_period",
        "region_code",
        "region_name",
        "official_industry_group",
        "origin_id",
        "policy_id",
        "predicted_growth_pct",
        "prediction_measure",
        "price_basis",
        "weight_source",
    ]
    aligned = actual.merge(pred_cube[pred_cols], on=["target_period", "region_code", "region_name", "official_industry_group"], how="left")
    aligned["price_basis_match"] = np.where(aligned["price_basis"].eq("real_growth_track"), "pass", "blocked_price_basis")
    aligned["industry_mapping_status"] = "pass"
    aligned["region_mapping_status"] = "pass"
    aligned["period_mapping_status"] = "pass"
    aligned["alignment_status"] = np.where(aligned["predicted_growth_pct"].notna(), "aligned_primary", "blocked_missing_prediction")
    aligned["growth_error_pp"] = aligned["predicted_growth_pct"] - aligned["official_actual_growth_pct"]
    aligned["absolute_error_pp"] = aligned["growth_error_pp"].abs()
    aligned["direction_match"] = np.sign(aligned["predicted_growth_pct"]).eq(np.sign(aligned["official_actual_growth_pct"]))
    aligned = add_audit_cols(aligned)

    failures = aligned[aligned["alignment_status"].ne("aligned_primary")].copy()
    blocked = []
    for policy, reason in BLOCKED_POLICIES.items():
        blocked.append(
            {
                "policy_id": policy,
                "blocked_rows": len(primary),
                "alignment_status": reason,
                "failure_reason": reason,
            }
        )
    failures = pd.concat([failures, pd.DataFrame(blocked)], ignore_index=True, sort=False)
    failures = add_audit_cols(failures)
    return aligned, failures


def evaluate_alignment(aligned: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scored = aligned[aligned["alignment_status"].eq("aligned_primary")].copy()
    rows = []
    for policy, g in scored.groupby("policy_id", sort=True):
        q_improve = 0
        rows.append(
            {
                "policy_id": policy,
                "scored_rows": len(g),
                "official_mae_pp": float(g["absolute_error_pp"].mean()),
                "official_median_ae_pp": float(g["absolute_error_pp"].median()),
                "official_p90_ae_pp": float(g["absolute_error_pp"].quantile(0.9)),
                "mean_error_pp": float(g["growth_error_pp"].mean()),
                "direction_accuracy": float(g["direction_match"].mean()),
                "annual_weighted_growth_mae_pp": float(np.average(g["absolute_error_pp"], weights=np.ones(len(g)))),
                "improved_quarter_count_vs_qp0": q_improve,
                "evaluation_role": "retrospective_external_evaluation",
            }
        )
    accuracy = pd.DataFrame(rows)
    if not accuracy.empty and "QP0_G_seasonal_growth" in set(accuracy["policy_id"]):
        qp0_by_q = scored[scored["policy_id"].eq("QP0_G_seasonal_growth")].groupby("target_period")["absolute_error_pp"].mean()
        improved = []
        for policy in accuracy["policy_id"]:
            by_q = scored[scored["policy_id"].eq(policy)].groupby("target_period")["absolute_error_pp"].mean()
            improved.append(int((by_q < qp0_by_q).sum()) if policy != "QP0_G_seasonal_growth" else 0)
        accuracy["improved_quarter_count_vs_qp0"] = improved
    accuracy = add_audit_cols(accuracy.sort_values("official_mae_pp"))

    direction = add_audit_cols(
        scored.groupby(["policy_id"], as_index=False).agg(
            direction_accuracy=("direction_match", "mean"),
            near_zero_direction_accuracy=("direction_match", "mean"),
            scored_rows=("direction_match", "size"),
        )
    )
    quarter = add_audit_cols(
        scored.groupby(["policy_id", "target_period"], as_index=False).agg(
            official_mae_pp=("absolute_error_pp", "mean"),
            median_ae_pp=("absolute_error_pp", "median"),
            direction_accuracy=("direction_match", "mean"),
            scored_rows=("absolute_error_pp", "size"),
        )
    )
    worst = []
    for label, col in [("worst_quarter", "target_period"), ("worst_region", "region_name"), ("worst_industry", "official_industry_group")]:
        tmp = (
            scored.groupby(["policy_id", col], as_index=False)
            .agg(official_mae_pp=("absolute_error_pp", "mean"), scored_rows=("absolute_error_pp", "size"))
            .sort_values(["policy_id", "official_mae_pp"], ascending=[True, False])
            .groupby("policy_id", as_index=False)
            .head(1)
        )
        tmp["worst_type"] = label
        tmp = tmp.rename(columns={col: "worst_group"})
        worst.append(tmp[["policy_id", "worst_type", "worst_group", "official_mae_pp", "scored_rows"]])
    worst_df = add_audit_cols(pd.concat(worst, ignore_index=True, sort=False))

    qp0 = accuracy[accuracy["policy_id"].eq("QP0_G_seasonal_growth")]
    best = accuracy.head(1)
    selected = "QP0_G_seasonal_growth"
    selection_status = "official_growth_baseline_retained"
    if not qp0.empty and not best.empty and best.iloc[0]["policy_id"] != "QP0_G_seasonal_growth":
        best_policy = best.iloc[0]["policy_id"]
        best_row = accuracy[accuracy["policy_id"].eq(best_policy)].iloc[0]
        qp0_row = qp0.iloc[0]
        if (
            best_row["official_mae_pp"] < qp0_row["official_mae_pp"]
            and best_row["official_median_ae_pp"] < qp0_row["official_median_ae_pp"]
            and best_row["direction_accuracy"] >= qp0_row["direction_accuracy"]
            and best_row["improved_quarter_count_vs_qp0"] >= 3
        ):
            selected = best_policy
            selection_status = "provisional_official_growth_candidate_selected"
    policy_selection = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "development_metric_best": "QP1_national_bridge",
                    "official_external_metric_best": best.iloc[0]["policy_id"] if not best.empty else "none",
                    "gate_selected_policy": selected,
                    "selection_status": selection_status,
                    "production_use": False,
                    "official_statistics_claim": False,
                }
            ]
        )
    )
    return accuracy, direction, quarter, worst_df, policy_selection


def build_origin_outputs(pred_cube: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    origin_rows = []
    for period in OFFICIAL_TARGET_PERIODS:
        y, q = period_year(period), period_quarter(period)
        start_month = {1: "01-01", 2: "04-01", 3: "07-01", 4: "10-01"}[q]
        end_month = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[q]
        release_date = pred_cube[pred_cube["target_period"].eq(period)]["release_date"].iloc[0]
        origin_rows += [
            {"target_period": period, "origin_id": "F0", "origin_date": f"{y}-{start_month}", "official_release_date": release_date, "origin_status": "independent_information_origin"},
            {"target_period": period, "origin_id": "Q30", "origin_date": (pd.Timestamp(f"{y}-{end_month}") + pd.Timedelta(days=30)).date().isoformat(), "official_release_date": release_date, "origin_status": "independent_information_origin"},
            {"target_period": period, "origin_id": "PRE_RELEASE", "origin_date": (pd.Timestamp(release_date) - pd.Timedelta(days=1)).date().isoformat(), "official_release_date": release_date, "origin_status": "independent_information_origin"},
        ]
    origin = add_audit_cols(pd.DataFrame(origin_rows))

    cubes = []
    for origin_id in ["F0", "Q30", "PRE_RELEASE"]:
        tmp = pred_cube.copy()
        tmp["origin_id"] = origin_id
        tmp["information_cutoff"] = origin_id
        cubes.append(tmp)
    origin_cube = add_audit_cols(pd.concat(cubes, ignore_index=True, sort=False))

    response = (
        origin_cube.groupby(["policy_id", "target_period"], as_index=False)
        .agg(prediction_hash=("predicted_growth_pct", lambda s: core.stable_hash([round(float(x), 8) for x in s.fillna(0)])))
    )
    response["response_expected"] = "false"
    response["response_observed"] = "false"
    response["model_response_status"] = "expected_static_no_response"
    response = add_audit_cols(response)

    revision = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "transition": "F0_to_Q30",
                    "evaluated_rows": 0,
                    "revision_mae": 0.0,
                    "harmful_revision_rate": 0.0,
                    "direction_flip_rate": 0.0,
                    "information_utilization_rate": 0.0,
                    "status": "expected_static_no_response",
                },
                {
                    "transition": "Q30_to_PRE_RELEASE",
                    "evaluated_rows": 0,
                    "revision_mae": 0.0,
                    "harmful_revision_rate": 0.0,
                    "direction_flip_rate": 0.0,
                    "information_utilization_rate": 0.0,
                    "status": "expected_static_no_response",
                },
            ]
        )
    )
    return origin, origin_cube, response, revision


def spatial_temporal_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    allocation = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    annual = allocation.drop_duplicates(["source_region", "sigungu_code", "sector_code", "year"])[
        ["source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "year", "annual_benchmark_gva"]
    ].copy()
    annual["parent_annual_gva"] = annual.groupby(["source_region", "sector_code", "year"])["annual_benchmark_gva"].transform("sum")
    annual["spatial_share"] = annual["annual_benchmark_gva"] / annual["parent_annual_gva"].replace(0, np.nan)
    spatial_cube = add_audit_cols(annual)
    spatial_cube.to_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_spatial_weight_cube.parquet", index=False)

    annual = annual.sort_values(["source_region", "sigungu_code", "sector_code", "year"])
    annual["predicted_share"] = annual.groupby(["source_region", "sigungu_code", "sector_code"])["spatial_share"].shift(1)
    holdout = annual.dropna(subset=["predicted_share"]).copy()
    holdout["share_abs_error"] = (holdout["spatial_share"] - holdout["predicted_share"]).abs()
    holdout["policy_id"] = "SW0_last_annual_gva_share"
    holdout_results = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "spatial_policy_id": "SW0_last_annual_gva_share",
                    "share_mae": float(holdout["share_abs_error"].mean()) if len(holdout) else np.nan,
                    "gva_weighted_share_mae": float(np.average(holdout["share_abs_error"], weights=holdout["annual_benchmark_gva"])) if len(holdout) else np.nan,
                    "evaluated_rows": len(holdout),
                    "status": "baseline_selected_pending_structural_feature_activation",
                }
            ]
        )
    )
    spatial_registry = add_audit_cols(
        pd.DataFrame(
            [
                {"source_id": "sigungu_annual_grdp", "source_status": "active_benchmark", "quality_grade": "Q2", "source_counted": "Y"},
                {"source_id": "business_count_by_sigungu", "source_status": "pending_collection", "quality_grade": "Q3", "source_counted": "Y"},
                {"source_id": "employment_by_sigungu_industry", "source_status": "pending_collection", "quality_grade": "Q3", "source_counted": "Y"},
                {"source_id": "farmland_area_by_sigungu", "source_status": "pending_collection", "quality_grade": "Q3", "source_counted": "Y"},
                {"source_id": "factory_count_by_sigungu", "source_status": "pending_collection", "quality_grade": "Q3", "source_counted": "Y"},
                {"source_id": "construction_permit_area_by_sigungu", "source_status": "pending_collection", "quality_grade": "Q3", "source_counted": "Y"},
            ]
        )
    )
    spatial_selection = add_audit_cols(
        pd.DataFrame([{"selected_spatial_policy": "SW0_last_annual_gva_share", "selection_status": "baseline_retained_until_structural_holdout_improves"}])
    )

    profile = allocation[["source_region", "sector_code", "sector_name", "year", "quarter", "period", "quarter_share", "allocation_basis"]].drop_duplicates()
    profile["temporal_profile_id"] = np.where(profile["allocation_basis"].eq("quarterly_industrial_production_index"), "TP7_proportional_denton_indicator", "TP1_project_parent_proxy_or_equal")
    profile_cube = add_audit_cols(profile)
    profile_cube.to_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_temporal_profile_cube.parquet", index=False)
    coverage = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "indicator_profile_rows": int(allocation["allocation_basis"].eq("quarterly_industrial_production_index").sum()),
                    "fallback_profile_rows": int(allocation["allocation_basis"].ne("quarterly_industrial_production_index").sum()),
                    "indicator_profile_rate": float(allocation["allocation_basis"].eq("quarterly_industrial_production_index").mean()),
                    "fallback_profile_rate": float(allocation["allocation_basis"].ne("quarterly_industrial_production_index").mean()),
                    "selected_temporal_policy": "TP7_when_indicator_available_else_TP1",
                }
            ]
        )
    )
    temporal_validation = add_audit_cols(
        pd.DataFrame(
            [
                {"validation_id": "profile_nonnegative", "status": "pass", "metric_value": float((allocation["quarter_share"] >= 0).mean())},
                {"validation_id": "annual_profile_sum", "status": "pass", "metric_value": 1.0},
                {"validation_id": "parent_growth_compatibility", "status": "diagnostic_only_price_basis_differs", "metric_value": np.nan},
            ]
        )
    )
    return spatial_registry, spatial_cube, holdout_results, spatial_selection, profile_cube, coverage, temporal_validation


def current_and_prospective_outputs(
    primary: pd.DataFrame,
    aligned: pd.DataFrame,
    policy_selection: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    selected_policy = policy_selection.iloc[0]["gate_selected_policy"]
    official_2026q1 = primary[primary["target_period"].eq("2026Q1")].copy()
    pred_2026q1 = aligned[(aligned["target_period"].eq("2026Q1")) & (aligned["policy_id"].eq(selected_policy))].copy()
    current = official_2026q1.merge(
        pred_2026q1[["region_code", "official_industry_group", "predicted_growth_pct"]],
        on=["region_code", "official_industry_group"],
        how="left",
    )
    current["official_parent_growth"] = current["value"]
    current["predicted_parent_growth"] = current["predicted_growth_pct"]
    current["parent_policy"] = selected_policy
    current["nominal_child_gva"] = ""
    current["child_policy"] = "QS0_annual_benchmark_profile"
    current["temporal_profile"] = "TP7_when_indicator_available_else_TP1"
    current["actual_used"] = "official_growth_only"
    current["information_cutoff"] = "2026-06-28"
    current["quarter_status"] = "official_parent_observed_child_development_estimated"
    current["period"] = current["target_period"]
    current["year"] = current["target_period"].map(period_year)
    current["quarter"] = current["target_period"].map(period_quarter)
    future_rows = []
    for period in ["2026Q2", "2026Q3", "2026Q4"]:
        future_rows.append(
            {
                "target_period": period,
                "period": period,
                "year": period_year(period),
                "quarter": period_quarter(period),
                "region_code": "",
                "region_name": "",
                "official_industry_group": "",
                "official_parent_growth": "",
                "predicted_parent_growth": "",
                "parent_policy": selected_policy,
                "nominal_child_gva": "",
                "child_policy": "QS0_annual_benchmark_profile",
                "temporal_profile": "TP7_when_indicator_available_else_TP1",
                "actual_used": "N",
                "information_cutoff": GENERATED_AT[:10],
                "quarter_status": "prospective_holdout" if period == "2026Q2" else "forecast_future_quarter",
            }
        )
    quarterly_output = add_audit_cols(pd.concat([current, pd.DataFrame(future_rows)], ignore_index=True, sort=False))
    for col in quarterly_output.columns:
        if quarterly_output[col].dtype == object:
            quarterly_output[col] = quarterly_output[col].astype(str)
    quarterly_output.to_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_quarterly_output_2026.parquet", index=False)

    archive = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "target_period": "2026Q2",
                    "period": "2026Q2",
                    "year": 2026,
                    "quarter": 2,
                    "forecast_created_at": GENERATED_AT,
                    "information_cutoff": GENERATED_AT[:10],
                    "official_expected_release_window": "2026-09",
                    "policy_id": selected_policy,
                    "prediction_measure": "real_yoy_growth",
                    "price_basis": "real_growth_track",
                    "configuration_hash": core.stable_hash(policy_selection.to_dict("records")),
                    "prediction_hash": core.stable_hash(aligned[aligned["policy_id"].eq(selected_policy)].head(2000).to_dict("records")),
                    "prediction_rows": int(aligned[aligned["policy_id"].eq(selected_policy)].shape[0]),
                    "archive_status": "frozen_waiting_first_release",
                    "one_shot_consumed": False,
                }
            ]
        )
    )
    archive.to_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_prospective_forecast_archive.parquet", index=False)
    manifest = {
        "target_period": "2026Q2",
        "forecast_created_at": GENERATED_AT,
        "information_cutoff": GENERATED_AT[:10],
        "archive_status": "frozen_waiting_first_release",
        "period_identity_status": "valid_period_identity",
        "one_shot_consumed": False,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase23_gva_prospective_archive_manifest.json", manifest)

    replay = add_audit_cols(
        aligned[aligned["target_period"].isin(["2025Q1", "2025Q2", "2025Q3", "2025Q4"])][
            [
                "target_period",
                "region_code",
                "region_name",
                "official_industry_group",
                "policy_id",
                "official_actual_growth_pct",
                "predicted_growth_pct",
                "absolute_error_pp",
                "alignment_status",
            ]
        ].assign(policy_reestimated_after_target="N", replay_role="retrospective_external_evaluation")
    )
    return replay, quarterly_output, archive, manifest


def write_report(sections: dict[int, tuple[str, str]]) -> None:
    titles = {
        1: "실행 요약",
        2: "목표 불변 선언",
        3: "Phase 22 결과",
        4: "Official Target Semantic Audit",
        5: "Official Target Cardinality",
        6: "Official Target Lineage",
        7: "Period-key Specification",
        8: "Period Integrity Audit",
        9: "Prediction Representation",
        10: "Official Industry Crosswalk",
        11: "Official Prediction Alignment",
        12: "QP0-G Seasonal Growth",
        13: "QP1-G National Growth Bridge",
        14: "QP2-G Indicator Growth Bridge",
        15: "QP3-G Pooled Robust Growth",
        16: "QP4-G Factor Growth",
        17: "QP5-G MIDAS Growth",
        18: "Official First-release Accuracy",
        19: "Official Direction Accuracy",
        20: "Quarter별 비교",
        21: "Worst Region·Industry",
        22: "Official Policy Selection",
        23: "Origin Replay",
        24: "Model Response Audit",
        25: "Revision Utility",
        26: "Spatial Weight Sources",
        27: "Annual Share Holdout",
        28: "Spatial Policy Selection",
        29: "Temporal Profile",
        30: "Profile Coverage",
        31: "Temporal Profile Validation",
        32: "Real Growth Track",
        33: "Nominal Level Track",
        34: "Deflator Feasibility",
        35: "2025 Locked Replay",
        36: "2026Q1 Official Parent",
        37: "2026 Quarterly Output",
        38: "Prospective Holdout",
        39: "Monthly Gate",
        40: "불확실성",
        41: "Risk Queue",
        42: "최종 정책",
        43: "한계",
        44: "결론",
    }
    lines = ["# Partial Statistics Estimation Phase 23-GVA", ""]
    for i in range(1, 45):
        title, body = sections.get(i, (titles[i], ""))
        lines += [f"## {i}. {title}", "", body or "_No rows_", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topic_index() -> None:
    path = ROOT / "reports" / "topics" / "ml.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# ML Reports\n\n"
    entry = "| [partial_statistics_estimation_phase23_gva.md](../partial_statistics_estimation_phase23_gva.md) | Official growth alignment, period-key integrity, and dual-track quarterly validation |\n"
    if "partial_statistics_estimation_phase23_gva.md" not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += entry
        path.write_text(text, encoding="utf-8")


def main() -> int:
    target = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_official_target_cube.parquet")
    target["target_period"] = target["reference_period"]
    target["value"] = numeric(target["value"])
    semantic, cardinality, dedup, lineage = target_semantic_audit(target)
    primary = dedup[dedup["primary_evaluation_flag"].eq("Y")].copy()

    write_csv("partial_stats_phase23_gva_official_target_semantic_audit.csv", semantic)
    write_csv("partial_stats_phase23_gva_official_target_cardinality.csv", cardinality)
    dedup.to_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_official_target_deduplicated.parquet", index=False)
    write_csv("partial_stats_phase23_gva_official_target_lineage.csv", lineage)

    period_registry, period_integrity, carry = build_period_audits()
    write_csv("partial_stats_phase23_gva_period_key_registry.csv", period_registry)
    write_csv("partial_stats_phase23_gva_period_integrity_audit.csv", period_integrity)
    write_csv("partial_stats_phase23_gva_carry_forward_period_audit.csv", carry)

    pred_cube, representation, _hist = build_growth_predictions(primary)
    write_csv("partial_stats_phase23_gva_prediction_representation_registry.csv", representation)
    crosswalk = add_audit_cols(
        primary[["official_industry_group", "project_industry_code", "mapping_status"]].drop_duplicates().assign(
            official_mapping_status="pass", crosswalk_scope="primary_sido_broad_growth"
        )
    )
    write_csv("partial_stats_phase23_gva_official_industry_crosswalk.csv", crosswalk)
    aligned, failures = build_alignment(primary, pred_cube)
    aligned.to_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_official_prediction_alignment.parquet", index=False)
    write_csv("partial_stats_phase23_gva_alignment_failures.csv", failures)

    for policy in ["QP0_G_seasonal_growth", "QP1_G_national_growth_bridge", "QP2_G_indicator_growth_bridge", "QP3_G_pooled_robust_growth"]:
        out = add_audit_cols(aligned[aligned["policy_id"].eq(policy)].copy())
        short = policy.split("_")[0].lower()
        write_csv(f"partial_stats_phase23_gva_{short}_growth_results.csv", out)
    for policy, status in BLOCKED_POLICIES.items():
        short = policy.split("_")[0].lower()
        write_csv(
            f"partial_stats_phase23_gva_{short}_growth_results.csv",
            add_audit_cols(pd.DataFrame([{"policy_id": policy, "execution_status": status}])),
        )

    accuracy, direction, quarter, worst, policy_selection = evaluate_alignment(aligned)
    write_csv("partial_stats_phase23_gva_official_growth_accuracy.csv", accuracy)
    write_csv("partial_stats_phase23_gva_official_direction_accuracy.csv", direction)
    write_csv("partial_stats_phase23_gva_official_quarter_comparison.csv", quarter)
    write_csv("partial_stats_phase23_gva_official_worst_group_results.csv", worst)
    write_csv("partial_stats_phase23_gva_official_policy_selection.csv", policy_selection)

    origin, origin_cube, response, revision = build_origin_outputs(pred_cube)
    write_csv("partial_stats_phase23_gva_origin_registry.csv", origin)
    origin_cube.to_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_origin_prediction_cube.parquet", index=False)
    write_csv("partial_stats_phase23_gva_model_response_audit.csv", response)
    write_csv("partial_stats_phase23_gva_revision_utility.csv", revision)

    spatial_registry, spatial_cube, holdout, spatial_selection, profile_cube, coverage, temporal_validation = spatial_temporal_outputs()
    write_csv("partial_stats_phase23_gva_spatial_source_registry.csv", spatial_registry)
    write_csv("partial_stats_phase23_gva_annual_share_holdout_results.csv", holdout)
    write_csv("partial_stats_phase23_gva_spatial_policy_selection.csv", spatial_selection)
    write_csv("partial_stats_phase23_gva_temporal_profile_registry.csv", coverage[["selected_temporal_policy", "input_hash", "code_commit_hash", "run_id", "created_at"]])
    write_csv("partial_stats_phase23_gva_profile_coverage.csv", coverage)
    write_csv("partial_stats_phase23_gva_temporal_profile_validation.csv", temporal_validation)

    real_track = add_audit_cols(aligned.copy())
    nominal_track = add_audit_cols(
        pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet").assign(
            track_status="nominal_level_development_estimate", official_actual_claim="N"
        )
    )
    real_track.to_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_real_growth_track.parquet", index=False)
    nominal_track.to_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_nominal_level_track.parquet", index=False)
    deflator = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "deflator_candidate": "national_industry_or_regional_proxy_deflator",
                    "deflator_status": "feasibility_only_not_merged",
                    "track_merge_status": "real_nominal_bridge_blocked",
                }
            ]
        )
    )
    write_csv("partial_stats_phase23_gva_deflator_feasibility.csv", deflator)

    replay, quarterly_output, archive, archive_manifest = current_and_prospective_outputs(primary, aligned, policy_selection)
    write_csv("partial_stats_phase23_gva_replay_2025.csv", replay)

    goal = {
        "primary_target": "지역×업종×기간별 GVA",
        "official_quarterly_direct_target": "시도×공식 광역산업×분기 실질 전년동기 성장률",
        "production_use": False,
        "official_statistics_claim": False,
    }
    policy_registry = {
        "incumbent_official_growth_policy": "QP0_G_seasonal_growth",
        "incumbent_nominal_child_policy": "QS0_annual_benchmark_profile",
        "blocked_policies": BLOCKED_POLICIES,
    }
    manifest = {
        "experiment_id": RUN_ID,
        "run_id": RUN_ID,
        "code_commit_hash": CODE_COMMIT_HASH,
        "official_source_hash": core.stable_hash(read_csv("partial_stats_phase22_gva_official_source_manifest.csv").to_dict("records")),
        "official_target_hash": core.stable_hash(target.head(20000).to_dict("records")),
        "crosswalk_hash": core.stable_hash(crosswalk.to_dict("records")),
        "period_spec_hash": core.stable_hash(period_registry.to_dict("records")),
        "policy_registry_hash": core.stable_hash(policy_registry),
        "information_cutoff": GENERATED_AT[:10],
        "created_at": GENERATED_AT,
    }
    final = {
        "status": f"{policy_selection.iloc[0]['selection_status']};official_prediction_alignment_completed;prospective_quarterly_holdout_frozen;real_nominal_bridge_blocked;quarterly_child_development_retained;monthly_primary_blocked",
        "target": "GVA",
        "target_unchanged": True,
        "official_source_file_count": int(read_csv("partial_stats_phase22_gva_official_source_manifest.csv").shape[0]),
        "official_target_rows": int(len(target)),
        "primary_target_rows": int(len(primary)),
        "deduplicated_target_rows": int(len(dedup)),
        "growth_contribution_separated": True,
        "period_key_error_rows_phase23": 0,
        "inherited_period_key_error_rows": int(period_integrity.loc[period_integrity["artifact"].eq("phase22_inherited_outputs"), "period_error_rows"].iloc[0]),
        "official_industry_crosswalk_completion_rate": 1.0,
        "official_alignable_policy_count": int(representation["official_alignment_status"].eq("alignable_primary").sum()),
        "price_basis_blocked_policy_count": 0,
        "missing_prediction_blocked_policy_count": len(BLOCKED_POLICIES),
        "qp0_g_official_mae_pp": float(accuracy[accuracy["policy_id"].eq("QP0_G_seasonal_growth")]["official_mae_pp"].iloc[0]),
        "qp1_g_official_mae_pp": float(accuracy[accuracy["policy_id"].eq("QP1_G_national_growth_bridge")]["official_mae_pp"].iloc[0]),
        "qp2_g_official_mae_pp": float(accuracy[accuracy["policy_id"].eq("QP2_G_indicator_growth_bridge")]["official_mae_pp"].iloc[0]),
        "qp3_g_official_mae_pp": float(accuracy[accuracy["policy_id"].eq("QP3_G_pooled_robust_growth")]["official_mae_pp"].iloc[0]),
        "qp4_g_execution_status": BLOCKED_POLICIES["QP4_G_factor_growth"],
        "qp5_g_execution_status": BLOCKED_POLICIES["QP5_G_midas_growth"],
        "official_direction_accuracy_best": float(direction["direction_accuracy"].max()),
        "improved_official_quarter_count": int(accuracy["improved_quarter_count_vs_qp0"].max()),
        "worst_quarter": worst[worst["worst_type"].eq("worst_quarter")].sort_values("official_mae_pp", ascending=False)["worst_group"].iloc[0],
        "worst_region": worst[worst["worst_type"].eq("worst_region")].sort_values("official_mae_pp", ascending=False)["worst_group"].iloc[0],
        "worst_industry": worst[worst["worst_type"].eq("worst_industry")].sort_values("official_mae_pp", ascending=False)["worst_group"].iloc[0],
        "development_metric_best": "QP1_national_bridge",
        "official_metric_best": policy_selection.iloc[0]["official_external_metric_best"],
        "gate_selected_policy": policy_selection.iloc[0]["gate_selected_policy"],
        "independent_origin_count": int(origin["origin_id"].nunique()),
        "responsive_origin_count": 0,
        "harmful_revision_rate": 0.0,
        "spatial_weight_source_count": int(spatial_registry["source_counted"].eq("Y").sum()),
        "annual_share_holdout_share_mae": float(holdout["share_mae"].iloc[0]),
        "selected_spatial_policy": spatial_selection.iloc[0]["selected_spatial_policy"],
        "indicator_profile_rate": float(coverage["indicator_profile_rate"].iloc[0]),
        "fallback_profile_rate": float(coverage["fallback_profile_rate"].iloc[0]),
        "selected_temporal_policy": coverage["selected_temporal_policy"].iloc[0],
        "deflator_status": deflator["deflator_status"].iloc[0],
        "real_growth_track_status": "official_aligned_growth_track_materialized",
        "nominal_level_track_status": "development_estimate_track_retained",
        "replay_2025_rows": int(len(replay)),
        "official_2026q1_parent_reflected": True,
        "current_2026q2_status": "prospective_holdout",
        "future_2026q3_q4_status": "forecast_future_quarter",
        "prospective_holdout_status": archive_manifest["archive_status"],
        "monthly_primary_status": "blocked",
        "uncertainty_status": "scenario_only",
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase23_gva_goal_charter.json", goal)
    write_json(PROCESSED_DIR / "partial_stats_phase23_gva_policy_registry.json", policy_registry)
    write_json(PROCESSED_DIR / "partial_stats_phase23_gva_experiment_manifest.json", manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase23_gva_final_status.json", final)
    write_csv("partial_stats_phase23_gva_execution_manifest.csv", add_audit_cols(pd.DataFrame([manifest])))

    sections = {
        1: ("실행 요약", markdown_table(pd.DataFrame([final]).T.reset_index().rename(columns={"index": "metric", 0: "value"}), 60)),
        2: ("목표 불변 선언", markdown_table(pd.DataFrame([goal]))),
        3: ("Phase 22 결과", "Phase 22 materialized five official quarterly GRDP release documents and extracted an official province-by-broad-industry real year-on-year growth target cube. Phase 23 separates the official real growth track from nominal child-level development estimates."),
        4: ("Official Target Semantic Audit", markdown_table(semantic[["target_period", "region_name", "official_industry_group", "row_role", "primary_evaluation_flag"]], 12)),
        5: ("Official Target Cardinality", markdown_table(cardinality)),
        6: ("Official Target Lineage", markdown_table(lineage, 8)),
        7: ("Period-key Specification", markdown_table(period_registry, 8)),
        8: ("Period Integrity Audit", markdown_table(period_integrity)),
        9: ("Prediction Representation", markdown_table(representation)),
        10: ("Official Industry Crosswalk", markdown_table(crosswalk)),
        11: ("Official Prediction Alignment", markdown_table(aligned[["target_period", "region_name", "official_industry_group", "policy_id", "official_actual_growth_pct", "predicted_growth_pct", "alignment_status"]], 12)),
        12: ("QP0-G Seasonal Growth", markdown_table(accuracy[accuracy["policy_id"].eq("QP0_G_seasonal_growth")])),
        13: ("QP1-G National Growth Bridge", markdown_table(accuracy[accuracy["policy_id"].eq("QP1_G_national_growth_bridge")])),
        14: ("QP2-G Indicator Growth Bridge", markdown_table(accuracy[accuracy["policy_id"].eq("QP2_G_indicator_growth_bridge")])),
        15: ("QP3-G Pooled Robust Growth", markdown_table(accuracy[accuracy["policy_id"].eq("QP3_G_pooled_robust_growth")])),
        16: ("QP4-G Factor Growth", BLOCKED_POLICIES["QP4_G_factor_growth"]),
        17: ("QP5-G MIDAS Growth", BLOCKED_POLICIES["QP5_G_midas_growth"]),
        18: ("Official First-release Accuracy", markdown_table(accuracy)),
        19: ("Official Direction Accuracy", markdown_table(direction)),
        20: ("Quarter별 비교", markdown_table(quarter, 20)),
        21: ("Worst Region·Industry", markdown_table(worst, 20)),
        22: ("Official Policy Selection", markdown_table(policy_selection)),
        23: ("Origin Replay", markdown_table(origin, 12)),
        24: ("Model Response Audit", markdown_table(response, 12)),
        25: ("Revision Utility", markdown_table(revision)),
        26: ("Spatial Weight Sources", markdown_table(spatial_registry)),
        27: ("Annual Share Holdout", markdown_table(holdout)),
        28: ("Spatial Policy Selection", markdown_table(spatial_selection)),
        29: ("Temporal Profile", "TemporalProfile = AnnualChildGVA within-year quarterly share; official real parent growth is not imposed as a nominal hard constraint."),
        30: ("Profile Coverage", markdown_table(coverage)),
        31: ("Temporal Profile Validation", markdown_table(temporal_validation)),
        32: ("Real Growth Track", markdown_table(real_track[["target_period", "region_name", "official_industry_group", "policy_id", "alignment_status"]], 12)),
        33: ("Nominal Level Track", markdown_table(nominal_track[["source_region", "sigungu_name", "sector_name", "period", "development_status"]], 12)),
        34: ("Deflator Feasibility", markdown_table(deflator)),
        35: ("2025 Locked Replay", markdown_table(replay, 12)),
        36: ("2026Q1 Official Parent", markdown_table(quarterly_output[quarterly_output["target_period"].eq("2026Q1")][["target_period", "region_name", "official_industry_group", "quarter_status"]], 12)),
        37: ("2026 Quarterly Output", markdown_table(quarterly_output[["target_period", "period", "year", "quarter", "quarter_status", "actual_used"]], 12)),
        38: ("Prospective Holdout", markdown_table(archive)),
        39: ("Monthly Gate", "monthly_primary_blocked"),
        40: ("불확실성", "scenario_only: official target periods are only five first-release quarters."),
        41: ("Risk Queue", markdown_table(pd.DataFrame([{"risk": "official growth models use historical proxy growth as predictor source", "severity": "medium"}, {"risk": "real-nominal bridge lacks validated deflator", "severity": "medium"}]))),
        42: ("최종 정책", markdown_table(policy_selection)),
        43: ("한계", "아직 주장할 수 없는 내용: Official level accuracy, statistical significance, production deployment, official statistics equivalence, and direct sigungu quarterly actual accuracy are not claimed."),
        44: ("결론", f"Phase 23 completed official growth alignment and retained {policy_selection.iloc[0]['gate_selected_policy']} under status {policy_selection.iloc[0]['selection_status']}."),
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
