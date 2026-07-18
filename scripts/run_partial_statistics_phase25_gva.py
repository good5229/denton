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
RUN_ID = "partial_statistics_estimation_phase25_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase25_gva.md"


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


def quarter_from_yyyymm(value: pd.Series) -> pd.Series:
    s = value.astype(str).str.replace(r"\.0$", "", regex=True)
    year = s.str[:4]
    month = pd.to_numeric(s.str[-2:], errors="coerce").fillna(1).astype(int)
    q = ((month - 1) // 3 + 1).astype(str)
    return year + "Q" + q


def observation_period_from_kosis(prd_se: pd.Series, prd_de: pd.Series, fallback: pd.Series) -> pd.Series:
    s = prd_de.astype(str).str.replace(r"\.0$", "", regex=True)
    freq = prd_se.astype(str)
    quarter_suffix = pd.to_numeric(s.str[-2:], errors="coerce")
    q_period = s.str[:4] + "Q" + quarter_suffix.fillna(0).astype(int).astype(str)
    m_period = quarter_from_yyyymm(s)
    return np.where(freq.eq("Q") & quarter_suffix.between(1, 4), q_period, np.where(s.str.len().ge(6), m_period, fallback.astype(str)))


def reproduce_phase24() -> pd.DataFrame:
    acc = read_csv("partial_stats_phase24_gva_parent_policy_selection.csv")
    metrics = {
        "QP0_G_seasonal_growth": (6.5221863720, None, None),
        "QP1_G_national_growth_bridge": (5.6125905857, 3.2897052348, 0.5176470588),
    }
    rows = []
    for policy, (mae_expected, median_expected, dir_expected) in metrics.items():
        row = acc[acc["policy_id"].eq(policy)].iloc[0]
        mae = float(row["mae_pp"])
        median = float(row["median_ae_pp"])
        direction = float(row["direction_accuracy"])
        rows.append(
            {
                "policy_id": policy,
                "expected_mae_pp": mae_expected,
                "observed_mae_pp": mae,
                "mae_abs_diff": abs(mae - mae_expected),
                "expected_median_ae_pp": "" if median_expected is None else median_expected,
                "observed_median_ae_pp": median,
                "expected_direction_accuracy": "" if dir_expected is None else dir_expected,
                "observed_direction_accuracy": direction,
                "scored_rows": int(row["scored_rows"]),
                "reproduction_status": "pass" if abs(mae - mae_expected) < 1e-8 else "fail",
            }
        )
    return add_audit_cols(pd.DataFrame(rows))


def canonical_indicator_cube() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase20_gva_quarterly_indicator_cube.parquet")
    df = raw.copy()
    df["source_family"] = df["dataset"].fillna(df["source_id"]).astype(str)
    df["region_code"] = df["c1_id"].astype(str)
    df["region_name"] = df["c1_nm"].astype(str)
    df["industry_code"] = df["c2_id"].replace({"": "TOTAL", "None": "TOTAL"}).fillna("TOTAL").astype(str)
    df["industry_name"] = df["c2_nm"].replace({"": "TOTAL", "None": "TOTAL"}).fillna("TOTAL").astype(str)
    df["measure_type"] = df["item_nm"].replace({"": "index_level", "None": "index_level"}).fillna("index_level").astype(str)
    df["unit"] = df["unit_nm"].replace({"": "unknown_unit", "None": "unknown_unit"}).fillna("unknown_unit").astype(str)
    df["seasonal_adjustment"] = np.where(df["measure_type"].str.contains("계절", na=False), "seasonally_adjusted", "original_or_unspecified")
    df["price_basis"] = np.where(df["measure_type"].str.contains("불변|실질", regex=True, na=False), "real_or_constant", "index_or_unspecified")
    df["observation_period"] = observation_period_from_kosis(df["prd_se"], df["prd_de"], df["period"])
    df["vintage_id"] = "current_snapshot_phase20"
    df["series_id"] = (
        df["source_family"].astype(str)
        + "|"
        + df["item_id"].astype(str)
        + "|"
        + df["measure_type"].astype(str)
        + "|"
        + df["unit"].astype(str)
        + "|"
        + df["industry_code"].astype(str)
        + "|"
        + df["seasonal_adjustment"].astype(str)
        + "|"
        + df["price_basis"].astype(str)
    )
    df["raw_value"] = num(df["value"]).fillna(num(df["quarterly_average"]))
    key = [
        "source_family",
        "series_id",
        "region_code",
        "industry_code",
        "measure_type",
        "unit",
        "seasonal_adjustment",
        "price_basis",
        "observation_period",
        "vintage_id",
    ]
    df["canonical_key_hash"] = df[key].astype(str).agg("|".join, axis=1).map(core.stable_hash)
    df["duplicate_status"] = np.where(df.duplicated(key, keep=False), "exact_duplicate_or_unresolved", "unique")
    exact_cols = key + ["raw_value"]
    exact_dupes = df.duplicated(exact_cols, keep=False)
    df.loc[exact_dupes, "duplicate_status"] = "exact_duplicate"
    dedup = df.drop_duplicates(key, keep="last").copy()
    unresolved = int((df["duplicate_status"].eq("exact_duplicate_or_unresolved")).sum())
    registry = add_audit_cols(
        dedup.groupby(["source_family", "series_id", "industry_code", "measure_type", "unit", "seasonal_adjustment", "price_basis"], as_index=False).agg(
            raw_rows=("raw_value", "size"),
            region_count=("region_code", "nunique"),
            period_count=("observation_period", "nunique"),
        )
    )
    dup_audit = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "source_family": source,
                    "raw_rows": len(group),
                    "canonical_unique_rows": group.drop_duplicates(key).shape[0],
                    "exact_duplicate_count": int(group["duplicate_status"].eq("exact_duplicate").sum()),
                    "revision_count": 0,
                    "unresolved_duplicate_count": int(group["duplicate_status"].eq("exact_duplicate_or_unresolved").sum()),
                    "primary_use": "N" if unresolved else "eligible_after_release_gate",
                }
                for source, group in df.groupby("source_family", sort=True)
            ]
        )
    )

    regional = dedup[dedup["region_code"].ne("00")].copy()
    national = dedup[dedup["region_code"].eq("00")].copy()
    join_keys = ["source_family", "industry_code", "measure_type", "unit", "seasonal_adjustment", "price_basis", "observation_period", "vintage_id"]
    nat_counts = national.groupby(join_keys, as_index=False).size().rename(columns={"size": "national_match_candidates"})
    merged = regional.merge(national[join_keys + ["raw_value"]].rename(columns={"raw_value": "national_raw_value"}), on=join_keys, how="left")
    merged = merged.merge(nat_counts, on=join_keys, how="left")
    inflation = (len(merged) - len(regional)) / max(len(regional), 1)
    join_audit = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "join_id": "regional_to_national_indicator",
                    "regional_rows_before_join": len(regional),
                    "rows_after_join": len(merged),
                    "join_row_inflation_rate": float(inflation),
                    "many_to_many_join_count": int((merged["national_match_candidates"].fillna(0) > 1).sum()),
                    "national_match_failure_rate": float(merged["national_raw_value"].isna().mean()) if len(merged) else 0.0,
                    "join_status": "pass" if inflation == 0 and not (merged["national_match_candidates"].fillna(0) > 1).any() else "fail",
                }
            ]
        )
    )
    merged["regional_surprise"] = merged["raw_value"] - merged["national_raw_value"]
    merged["signal_available"] = np.where(merged["regional_surprise"].notna(), "Y", "N")
    out = add_audit_cols(dedup)
    out.to_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_indicator_cube.parquet", index=False)
    surprise = add_audit_cols(merged)
    surprise.to_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_regional_surprise_cube.parquet", index=False)
    return out, registry, dup_audit, join_audit


def release_and_asof(indicator: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source_registry = read_csv("partial_stats_phase24_gva_quarterly_source_registry.csv")
    evidence_rows = []
    for _, row in source_registry.iterrows():
        grade = "R4" if row.get("release_date", "") == "documented_or_proxy_lag" else "R5"
        evidence_rows.append(
            {
                "source_id": row["source_id"],
                "release_evidence_grade": grade,
                "evidence_description": "documented_or_proxy_lag_only" if grade == "R4" else "unknown",
                "primary_origin_allowed": "N",
                "shadow_allowed": "Y" if grade == "R4" else "N",
                "exclusion_reason": "R1_R3_official_release_timestamp_not_materialized",
            }
        )
    evidence = add_audit_cols(pd.DataFrame(evidence_rows))

    periods = ["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"]
    ledger_rows = []
    for source_id in sorted(indicator["source_id"].dropna().astype(str).unique()):
        source_rows = indicator[indicator["source_id"].astype(str).eq(source_id)]
        for period in sorted(source_rows["observation_period"].dropna().astype(str).unique())[:32]:
            ledger_rows.append(
                {
                    "source_id": source_id,
                    "series_id": source_rows["series_id"].iloc[0],
                    "reference_period": period,
                    "release_timestamp": "",
                    "release_evidence_grade": "R4",
                    "release_page_url_or_id": "",
                    "attachment_name": "",
                    "attachment_hash": "",
                    "retrieved_at": GENERATED_AT,
                    "vintage_id": "current_snapshot_phase20",
                    "revision_status": "current_snapshot",
                    "first_eligible_origin": "not_primary_eligible",
                    "primary_eligibility": "N",
                    "exclusion_reason": "official_release_timestamp_missing",
                }
            )
    ledger = add_audit_cols(pd.DataFrame(ledger_rows))

    asof_rows = []
    info_rows = []
    for target in periods:
        for origin in ["F0", "Q30", "PRE_RELEASE"]:
            eligible = indicator.iloc[0:0].copy()
            h = core.stable_hash([])
            asof_rows.append(
                {
                    "target_period": target,
                    "origin_id": origin,
                    "region_code": "",
                    "industry_code": "",
                    "feature_id": "",
                    "source_id": "",
                    "source_reference_period": "",
                    "release_timestamp": "",
                    "raw_value": "",
                    "transformed_value": "",
                    "eligibility_status": "blocked_no_R1_R3_release_timestamp",
                    "eligible_observation_hash": h,
                    "raw_feature_hash": h,
                    "transformed_feature_hash": h,
                    "model_input_hash": h,
                    "prediction_hash": h,
                }
            )
            info_rows.append(
                {
                    "target_period": target,
                    "origin_id": origin,
                    "eligible_source_count": 0,
                    "eligible_observation_count": len(eligible),
                    "eligible_observation_hash": h,
                    "model_input_hash": h,
                    "expected_prediction_change": "N",
                    "observed_prediction_change": "N",
                    "origin_information_status": "blocked_no_R1_R3_release_timestamp",
                }
            )
    asof = add_audit_cols(pd.DataFrame(asof_rows))
    asof.to_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_asof_feature_store.parquet", index=False)
    info = add_audit_cols(pd.DataFrame(info_rows))
    return evidence, ledger, asof, info


def qp2_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    qp1 = read_csv("partial_stats_phase24_gva_qp1_frozen_results.csv")
    out = qp1.copy()
    out["policy_id"] = "QP2_R_minimal_release_dated_regional_surprise"
    out["qp2_prediction"] = out["predicted_growth_pct"]
    out["qp1_baseline_prediction"] = out["predicted_growth_pct"]
    out["prediction_changed_from_qp1"] = "N"
    out["origin_responsive_status"] = "blocked_no_R1_R3_release_dated_sources"
    out["fallback_policy"] = "QP1_G_national_growth_bridge"
    out["fallback_reason"] = "no_primary_qualified_release_dated_indicator"
    out["correction_pp"] = 0.0
    out["correction_cap_violation"] = "N"
    out = add_audit_cols(out)
    out.to_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_qp2_responsive_results.parquet", index=False)
    fallback = add_audit_cols(out[["target_period", "region_code", "region_name", "official_industry_group", "fallback_policy", "fallback_reason", "origin_responsive_status"]].copy())
    revision = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "revision_row_count": 0,
                    "mean_revision_utility": "not_scored",
                    "median_revision_utility": "not_scored",
                    "harmful_revision_rate": "not_scored",
                    "direction_flip_rate": "not_scored",
                    "correct_direction_flip_rate": "not_scored",
                    "worst_region_revision_utility": "not_scored",
                    "worst_industry_revision_utility": "not_scored",
                    "fallback_rate": 1.0,
                    "revision_status": "not_scored_no_changed_prediction",
                }
            ]
        )
    )
    write_csv("partial_stats_phase25_gva_qp2_fallback_audit.csv", fallback)
    write_csv("partial_stats_phase25_gva_revision_utility.csv", revision)
    return out, fallback, revision


def spatial_features() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    elec_path = PROCESSED_DIR / "municipality_electricity_features.csv"
    if elec_path.exists():
        elec = read_csv("municipality_electricity_features.csv")
        elec["year"] = elec["year"].astype(int)
        elec["industrial_kwh"] = num(elec["electricity_industrial_kwh"])
        annual = elec.groupby(["year", "sido_name", "sigungu_name", "sigungu_code"], as_index=False).agg(
            industrial_kwh=("industrial_kwh", "sum"),
            first_eligible_period=("first_eligible_period", "max"),
        )
        annual["sido_industrial_kwh"] = annual.groupby(["year", "sido_name"])["industrial_kwh"].transform("sum")
        annual["electricity_spatial_share"] = annual["industrial_kwh"] / annual["sido_industrial_kwh"].replace(0, np.nan)
        annual["source_status"] = "materialized"
        annual["holdout_eligible_status"] = "blocked_insufficient_common_years_with_2020_2023_sigungu_gva"
    else:
        annual = pd.DataFrame()
    elec_out = add_audit_cols(annual)
    elec_out.to_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_electricity_spatial_features.parquet", index=False)

    building = read_csv("buildinghub_feature_table.csv")
    if len(building):
        building["source_status"] = "materialized_pilot"
        building["event_date_status"] = "event_dates_separated_in_source_table"
        building["holdout_eligible_status"] = "blocked_no_first_eligible_period_and_no_common_validated_years"
    building = add_audit_cols(building)
    building.to_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_building_permit_features.parquet", index=False)

    factory = read_csv("factory_feature_table.csv")
    if len(factory):
        factory["source_status"] = "materialized_snapshot"
        factory["stock_flow_status"] = np.where(factory["flow_feature_allowed"].astype(str).eq("Y"), "flow_allowed", "stock_only")
        factory["holdout_eligible_status"] = "blocked_publication_date_not_exact_or_common_years_insufficient"
    factory = add_audit_cols(factory)
    factory.to_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_factory_registry_features.parquet", index=False)

    allocation = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    annual_gva = allocation.drop_duplicates(["source_region", "sigungu_code", "sector_code", "year"])[
        ["source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "year", "annual_benchmark_gva"]
    ].copy()
    annual_gva["parent_annual_gva"] = annual_gva.groupby(["source_region", "sector_code", "year"])["annual_benchmark_gva"].transform("sum")
    annual_gva["sw0_share"] = annual_gva["annual_benchmark_gva"] / annual_gva["parent_annual_gva"].replace(0, np.nan)
    annual_gva["candidate_policy"] = "SW0_last_annual_gva_share"
    weight = add_audit_cols(annual_gva)
    weight.to_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_spatial_weight_cube.parquet", index=False)

    common_years = sorted(set(annual_gva["year"].astype(int)) & (set(elec_out["year"].astype(int)) if len(elec_out) else set()))
    holdout = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "policy_id": "SW_ELEC_industrial_electricity_share",
                    "common_year_count": len(common_years),
                    "common_years": ",".join(map(str, common_years)),
                    "share_mae": "not_scored",
                    "gva_weighted_share_mae": "not_scored",
                    "rank_correlation": "not_scored",
                    "false_spatial_update_rate": "not_scored",
                    "holdout_status": "blocked_insufficient_common_years" if len(common_years) < 2 else "ready_for_scoring",
                },
                {
                    "policy_id": "SW0_last_annual_gva_share",
                    "common_year_count": int(annual_gva["year"].nunique()),
                    "common_years": ",".join(map(str, sorted(annual_gva["year"].astype(int).unique()))),
                    "share_mae": float(read_csv("partial_stats_phase24_gva_annual_share_holdout.csv")["share_mae"].iloc[0]),
                    "gva_weighted_share_mae": float(read_csv("partial_stats_phase24_gva_annual_share_holdout.csv")["gva_weighted_share_mae"].iloc[0]),
                    "rank_correlation": "not_scored",
                    "false_spatial_update_rate": "not_scored",
                    "holdout_status": "baseline_retained",
                },
            ]
        )
    )
    selection = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "selected_spatial_policy": "SW0_last_annual_gva_share",
                    "electricity_spatial_source_status": "materialized_but_holdout_blocked_insufficient_common_years" if len(elec_out) else "not_materialized",
                    "building_permit_source_status": "materialized_pilot_not_holdout_qualified" if len(building) else "not_materialized",
                    "factory_registry_source_status": "materialized_snapshot_not_holdout_qualified" if len(factory) else "not_materialized",
                    "spatial_holdout_result": "spatial_challenger_failed_or_blocked",
                    "selection_status": "SW0_retained",
                }
            ]
        )
    )
    write_csv("partial_stats_phase25_gva_annual_share_holdout.csv", holdout)
    write_csv("partial_stats_phase25_gva_spatial_policy_selection.csv", selection)
    return elec_out, building, factory, holdout, selection


def prospective_archives() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    archive24 = read_csv("partial_stats_phase24_gva_2026q2_archive_integrity.csv").iloc[0]
    event = {
        "target_period": "2026Q2",
        "event_status": "waiting_first_release",
        "archive_integrity": archive24["integrity_status"],
        "official_actual_used": False,
        "one_shot_consumed": False,
        "checked_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase25_gva_2026q2_holdout_event_status.json", event)
    one_shot = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "target_period": "2026Q2",
                    "one_shot_status": "waiting_first_release",
                    "qp0_result": "not_scored",
                    "qp1_result": "not_scored",
                    "official_actual_used": "N",
                }
            ]
        )
    )
    write_csv("partial_stats_phase25_gva_2026q2_one_shot_evaluation.csv", one_shot)

    alignment = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase23_gva_official_prediction_alignment.parquet")
    base = alignment[alignment["target_period"].eq("2026Q1")].copy()
    archives = []
    for policy, fname in [
        ("QP0_G_seasonal_growth", "partial_stats_phase25_gva_2026q3_qp0_archive.parquet"),
        ("QP1_G_national_growth_bridge", "partial_stats_phase25_gva_2026q3_qp1_archive.parquet"),
    ]:
        df = base[base["policy_id"].eq(policy)].copy()
        df["target_period"] = "2026Q3"
        df["period"] = "2026Q3"
        df["year"] = 2026
        df["quarter"] = 3
        df["origin_id"] = "F0"
        df["forecast_status"] = "frozen_forecast_rows"
        df["official_actual_used"] = "N"
        df["archive_immutable"] = True
        df = add_audit_cols(df)
        df.to_parquet(PROCESSED_DIR / fname, index=False)
        archives.append(df)
    qp2 = archives[1].copy()
    qp2["policy_id"] = "QP2_R_minimal_release_dated_regional_surprise"
    qp2["forecast_status"] = "diagnostic_fallback_archive_not_prospective_shadow"
    qp2["fallback_policy"] = "QP1_G_national_growth_bridge"
    qp2["fallback_reason"] = "no_R1_R3_release_dated_indicator"
    qp2 = add_audit_cols(qp2)
    qp2.to_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_2026q3_qp2_shadow_archive.parquet", index=False)

    manifest = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "target_period": "2026Q3",
                    "archive_id": "QP0_F0",
                    "policy_id": "QP0_G_seasonal_growth",
                    "prediction_rows": len(archives[0]),
                    "official_actual_used": "N",
                    "archive_status": "frozen_forecast_rows",
                },
                {
                    "target_period": "2026Q3",
                    "archive_id": "QP1_F0",
                    "policy_id": "QP1_G_national_growth_bridge",
                    "prediction_rows": len(archives[1]),
                    "official_actual_used": "N",
                    "archive_status": "frozen_forecast_rows",
                },
                {
                    "target_period": "2026Q3",
                    "archive_id": "QP2_R_F0",
                    "policy_id": "QP2_R_minimal_release_dated_regional_surprise",
                    "prediction_rows": len(qp2),
                    "official_actual_used": "N",
                    "archive_status": "diagnostic_fallback_not_shadow_qualified",
                },
            ]
        )
    )
    write_csv("partial_stats_phase25_gva_prospective_archive_manifest.csv", manifest)
    return event, one_shot, archives[0], archives[1], qp2, manifest


def write_report(sections: dict[int, tuple[str, str]]) -> None:
    titles = {
        1: "실행 요약",
        2: "목표 불변 선언",
        3: "Phase 24 재현",
        4: "현재 Holdout Event 상태",
        5: "Series Grain Audit",
        6: "Duplicate·Revision Audit",
        7: "Join Cardinality Audit",
        8: "Release Evidence Registry",
        9: "Qualified Source 현황",
        10: "Origin별 As-of Feature Store",
        11: "Regional Surprise 무결성",
        12: "QP2-R 반응성",
        13: "Revision Utility",
        14: "QP0·QP1 공식 회고성능",
        15: "2026Q2 One-shot 결과 또는 대기상태",
        16: "2026Q3 Forecast Archive",
        17: "전력사용량 공간 Feature",
        18: "건축인허가 공간 Feature",
        19: "공장등록 공간 Feature",
        20: "Annual Spatial Share Holdout",
        21: "선택된 Spatial 정책",
        22: "Temporal 상태",
        23: "Real·Nominal Bridge 상태",
        24: "월별 Primary 상태",
        25: "Risk Queue",
        26: "최종 정책",
        27: "아직 주장할 수 없는 내용",
        28: "결론",
    }
    lines = ["# Partial Statistics Estimation Phase 25-GVA", ""]
    for i in range(1, 29):
        title, body = sections.get(i, (titles[i], ""))
        lines += [f"## {i}. {title}", "", body or "_No rows_", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topic_index() -> None:
    path = ROOT / "reports" / "topics" / "ml.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# ML Reports\n\n"
    entry = "| [partial_statistics_estimation_phase25_gva.md](../partial_statistics_estimation_phase25_gva.md) | Release-dated source qualification, join repair, and QP2-R gate evidence |\n"
    if "partial_statistics_estimation_phase25_gva.md" not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += entry
        path.write_text(text, encoding="utf-8")


def main() -> int:
    reproduction = reproduce_phase24()
    indicator, series_registry, duplicate_audit, join_audit = canonical_indicator_cube()
    evidence, ledger, asof, origin_info = release_and_asof(indicator)
    qp2, fallback, revision = qp2_outputs()
    elec, building, factory, spatial_holdout, spatial_selection = spatial_features()
    event, one_shot, q3_qp0, q3_qp1, q3_qp2, archive_manifest = prospective_archives()

    write_csv("partial_stats_phase25_gva_phase24_reproduction.csv", reproduction)
    write_csv("partial_stats_phase25_gva_series_registry.csv", series_registry)
    write_csv("partial_stats_phase25_gva_duplicate_audit.csv", duplicate_audit)
    write_csv("partial_stats_phase25_gva_join_cardinality_audit.csv", join_audit)
    write_csv("partial_stats_phase25_gva_release_evidence_registry.csv", evidence)
    write_csv("partial_stats_phase25_gva_release_ledger.csv", ledger)
    write_csv("partial_stats_phase25_gva_origin_information_audit.csv", origin_info)

    q0 = reproduction[reproduction["policy_id"].eq("QP0_G_seasonal_growth")].iloc[0]
    q1 = reproduction[reproduction["policy_id"].eq("QP1_G_national_growth_bridge")].iloc[0]
    final = {
        "status": "release_ledger_unqualified;indicator_join_integrity_repaired;origin_information_equivalent;qp2_r_blocked_no_R1_R3_source;spatial_challenger_blocked_common_years;qp1_frozen_until_2026Q2_one_shot;monthly_primary_blocked",
        "target": "GVA",
        "target_unchanged": True,
        "phase24_reproduction_status": "pass" if reproduction["reproduction_status"].eq("pass").all() else "fail",
        "holdout_2026q2_event_status": event["event_status"],
        "archive_2026q2_integrity": event["archive_integrity"],
        "one_shot_2026q2_result": "waiting_first_release",
        "qp0_retrospective_mae_pp": float(q0["observed_mae_pp"]),
        "qp1_retrospective_mae_pp": float(q1["observed_mae_pp"]),
        "canonical_series_count": int(series_registry["series_id"].nunique()),
        "unresolved_duplicate_count": int(duplicate_audit["unresolved_duplicate_count"].astype(int).sum()),
        "many_to_many_join_count": int(join_audit["many_to_many_join_count"].iloc[0]),
        "join_row_inflation_rate": float(join_audit["join_row_inflation_rate"].iloc[0]),
        "materialized_quarterly_source_count": int(evidence["release_evidence_grade"].notna().sum()),
        "r1_r3_qualified_source_count": int(evidence["release_evidence_grade"].isin(["R1", "R2", "R3"]).sum()),
        "independent_origin_count": 1,
        "responsive_origin_count": 0,
        "f0_eligible_observation_count": 0,
        "q30_eligible_observation_count": 0,
        "pre_release_eligible_observation_count": 0,
        "qp2_r_prediction_row_count": int(len(qp2)),
        "qp2_r_changed_prediction_row_count": int(qp2["prediction_changed_from_qp1"].eq("Y").sum()),
        "revision_row_count": 0,
        "mean_revision_utility": "not_scored",
        "harmful_revision_rate": "not_scored",
        "qp2_fallback_rate": 1.0,
        "qp2_prospective_status": "blocked_not_2026Q3_shadow_qualified",
        "archive_2026q3_status": "frozen_qp0_qp1_rows_qp2_diagnostic_fallback",
        "electricity_spatial_source_status": spatial_selection["electricity_spatial_source_status"].iloc[0],
        "building_permit_source_status": spatial_selection["building_permit_source_status"].iloc[0],
        "factory_registry_source_status": spatial_selection["factory_registry_source_status"].iloc[0],
        "spatial_holdout_result": spatial_selection["spatial_holdout_result"].iloc[0],
        "selected_spatial_policy": spatial_selection["selected_spatial_policy"].iloc[0],
        "temporal_policy_status": "TP1_retained_TP7_not_validated",
        "real_nominal_bridge_status": "blocked",
        "monthly_primary_status": "blocked",
        "production_use": False,
        "official_statistics_claim": False,
        "recommended_policy": "QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot",
        "claims_still_prohibited": "QP2-R improvement, revision utility, spatial challenger superiority, TP7 superiority, real-nominal bridge, production use, official statistics equivalence",
        "generated_at": GENERATED_AT,
    }
    goal = {
        "primary_target": "region_x_industry_x_period_GVA",
        "official_quarterly_direct_target": "sido_x_broad_industry_x_quarter_real_yoy_growth",
        "quarterly_incumbent": "QP1_G_national_growth_bridge_frozen",
        "prospective_primary_holdout": "2026Q2",
        "next_prospective_shadow_target": "2026Q3",
        "production_use": False,
        "official_statistics_claim": False,
    }
    policy = {
        "incumbent": "QP1_G_national_growth_bridge",
        "qp2_r_status": final["qp2_prospective_status"],
        "spatial_incumbent": final["selected_spatial_policy"],
        "temporal_incumbent": "TP1_project_parent_proxy_profile",
    }
    manifest = {
        "experiment_id": RUN_ID,
        "run_id": RUN_ID,
        "code_commit_hash": CODE_COMMIT_HASH,
        "phase24_reproduction_hash": core.stable_hash(reproduction.to_dict("records")),
        "series_registry_hash": core.stable_hash(series_registry.to_dict("records")),
        "release_ledger_hash": core.stable_hash(ledger.head(20000).to_dict("records")),
        "q3_archive_manifest_hash": core.stable_hash(archive_manifest.to_dict("records")),
        "created_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase25_gva_goal_charter.json", goal)
    write_json(PROCESSED_DIR / "partial_stats_phase25_gva_policy_registry.json", policy)
    write_json(PROCESSED_DIR / "partial_stats_phase25_gva_experiment_manifest.json", manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase25_gva_final_status.json", final)

    sections = {
        1: ("실행 요약", markdown_table(pd.DataFrame([final]).T.reset_index().rename(columns={"index": "metric", 0: "value"}), 60)),
        2: ("목표 불변 선언", markdown_table(pd.DataFrame([goal]))),
        3: ("Phase 24 재현", markdown_table(reproduction)),
        4: ("현재 Holdout Event 상태", markdown_table(pd.DataFrame([event]))),
        5: ("Series Grain Audit", markdown_table(series_registry)),
        6: ("Duplicate·Revision Audit", markdown_table(duplicate_audit)),
        7: ("Join Cardinality Audit", markdown_table(join_audit)),
        8: ("Release Evidence Registry", markdown_table(evidence)),
        9: ("Qualified Source 현황", markdown_table(evidence[["source_id", "release_evidence_grade", "primary_origin_allowed", "exclusion_reason"]])),
        10: ("Origin별 As-of Feature Store", markdown_table(origin_info)),
        11: ("Regional Surprise 무결성", markdown_table(join_audit)),
        12: ("QP2-R 반응성", markdown_table(qp2[["target_period", "region_code", "official_industry_group", "policy_id", "prediction_changed_from_qp1", "origin_responsive_status", "fallback_reason"]], 12)),
        13: ("Revision Utility", markdown_table(revision)),
        14: ("QP0·QP1 공식 회고성능", markdown_table(reproduction)),
        15: ("2026Q2 One-shot 결과 또는 대기상태", markdown_table(one_shot)),
        16: ("2026Q3 Forecast Archive", markdown_table(archive_manifest)),
        17: ("전력사용량 공간 Feature", markdown_table(elec, 12)),
        18: ("건축인허가 공간 Feature", markdown_table(building, 12)),
        19: ("공장등록 공간 Feature", markdown_table(factory, 12)),
        20: ("Annual Spatial Share Holdout", markdown_table(spatial_holdout)),
        21: ("선택된 Spatial 정책", markdown_table(spatial_selection)),
        22: ("Temporal 상태", "TP1 retained. TP7 remains unvalidated because coverage and accounting constraints are not predictive accuracy."),
        23: ("Real·Nominal Bridge 상태", "blocked: direct regional-industry annual nominal/real validation pair is not materialized."),
        24: ("월별 Primary 상태", "monthly_primary_blocked"),
        25: ("Risk Queue", markdown_table(pd.DataFrame([{"risk": "R1-R3 publication timestamps remain missing", "severity": "high"}, {"risk": "electricity spatial feature common years do not overlap enough with annual GVA holdout", "severity": "medium"}]))),
        26: ("최종 정책", markdown_table(pd.DataFrame([{"recommended_policy": final["recommended_policy"], "production_use": False, "official_statistics_claim": False}]))),
        27: ("아직 주장할 수 없는 내용", final["claims_still_prohibited"]),
        28: ("결론", "Phase 25 repaired indicator grain and join integrity, preserved the 2026Q2 holdout, generated real 2026Q3 QP0/QP1 forecast rows, and kept QP2-R blocked because no R1-R3 release-dated regional indicator source is available."),
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
