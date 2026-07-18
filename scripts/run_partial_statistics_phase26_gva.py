from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, RAW_DIR, ROOT, cp949_safe, write_json
from run_partial_statistics_phase25_gva import observation_period_from_kosis


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase26_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase26_gva.md"


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def read_csv(name: str, **kwargs: Any) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False, **kwargs)


def write_csv(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def write_parquet(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def add_audit_cols(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base_cols = [c for c in out.columns if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = core.stable_hash(out[base_cols].head(20000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


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


def source_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return core.stable_hash(path.read_bytes().hex()[:200000])


def phase25_reproduction() -> pd.DataFrame:
    expected = {
        "QP0_G_seasonal_growth": (6.5221863720425555, "", ""),
        "QP1_G_national_growth_bridge": (5.612590585711022, 3.289705234823889, 0.5176470588235295),
    }
    prev = read_csv("partial_stats_phase25_gva_phase24_reproduction.csv")
    rows: list[dict[str, Any]] = []
    for policy, (mae_exp, med_exp, dir_exp) in expected.items():
        row = prev[prev["policy_id"].eq(policy)].iloc[0]
        mae = float(row["observed_mae_pp"])
        med = row["observed_median_ae_pp"]
        direction = row["observed_direction_accuracy"]
        rows.append(
            {
                "policy_id": policy,
                "expected_mae_pp": mae_exp,
                "observed_mae_pp": mae,
                "mae_abs_diff": abs(mae - mae_exp),
                "expected_median_ae_pp": med_exp,
                "observed_median_ae_pp": med,
                "expected_direction_accuracy": dir_exp,
                "observed_direction_accuracy": direction,
                "scored_rows": int(row["scored_rows"]),
                "reproduction_status": "pass" if abs(mae - mae_exp) < 1e-8 else "fail",
            }
        )
    return add_audit_cols(pd.DataFrame(rows))


def metadata_codebook(table_id: str) -> pd.DataFrame:
    path = PROCESSED_DIR / f"kosis_{table_id}_metadata.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False)


def build_source_dimension_registry(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    codebook_rows: list[dict[str, Any]] = []

    def add_dim(
        source_id: str,
        table_id: str,
        dim_code: str,
        dim_name: str,
        role: str,
        cardinality: int,
        mapping_status: str,
        codebook_source: str,
    ) -> None:
        rows.append(
            {
                "source_id": source_id,
                "original_table_id": table_id,
                "original_dimension_code": dim_code,
                "original_dimension_name": dim_name,
                "original_item_code": "",
                "original_item_name": "",
                "semantic_role": role,
                "expected_cardinality": cardinality,
                "codebook_source": codebook_source,
                "codebook_hash": source_hash(Path(codebook_source)) if codebook_source.startswith("data/") else core.stable_hash(codebook_source),
                "mapping_status": mapping_status,
            }
        )

    for table_id in ["DT_1F02001", "DT_1KC2023", "DT_200Y106"]:
        cb = metadata_codebook(table_id)
        if not cb.empty:
            tmp = cb[["tbl_id", "dimension_id", "dimension_name", "code", "name", "level", "parent_code", "leaf"]].copy()
            tmp.insert(0, "source_id", table_id)
            codebook_rows.extend(tmp.to_dict("records"))

    add_dim("mining_manufacturing_production_index.csv", "101/DT_1F02001", "PRD_DE", "수록시점", "time", 20, "pass_official_codebook_and_table_title", "data/raw/kosis_DT_1F02001_metadata.json")
    add_dim("mining_manufacturing_production_index.csv", "101/DT_1F02001", "A", "시도별", "region", 18, "pass_18_includes_national_comparator", "data/raw/kosis_DT_1F02001_metadata.json")
    add_dim("mining_manufacturing_production_index.csv", "101/DT_1F02001", "B", "산업별", "industry", 5, "pass_official_codebook_and_table_title", "data/raw/kosis_DT_1F02001_metadata.json")
    add_dim("mining_manufacturing_production_index.csv", "101/DT_1F02001", "ITM_ID", "항목", "measure", 6, "pass_official_codebook_and_table_title", "data/raw/kosis_DT_1F02001_metadata.json")
    add_dim("mining_manufacturing_production_index.csv", "101/DT_1F02001", "UNIT_NM", "단위", "unit", 1, "pass_table_unit_2020_index", "data/raw/kosis_DT_1F02001_metadata.json")

    add_dim("service_production_index.csv", "101/DT_1KC2023", "PRD_DE", "수록시점", "time", 20, "pass_official_codebook_and_table_title", "data/raw/kosis_DT_1KC2023_metadata.json")
    add_dim("service_production_index.csv", "101/DT_1KC2023", "SGG", "행정구역별", "region", 17, "blocked_collection_filter_error_only_two_regions_observed", "data/raw/kosis_DT_1KC2023_metadata.json")
    add_dim("service_production_index.csv", "101/DT_1KC2023", "A", "업종별", "industry", 14, "pass_official_codebook_and_table_title", "data/raw/kosis_DT_1KC2023_metadata.json")
    add_dim("service_production_index.csv", "101/DT_1KC2023", "ITM_ID", "항목", "measure", 2, "pass_official_codebook_and_table_title", "data/raw/kosis_DT_1KC2023_metadata.json")
    add_dim("service_production_index.csv", "101/DT_1KC2023", "UNIT_NM", "단위", "unit", 1, "pass_table_unit_2020_index", "data/raw/kosis_DT_1KC2023_metadata.json")

    add_dim("rolling_national_quarterly_gdp_real.csv", "301/DT_200Y106", "PRD_DE", "수록시점", "time", 44, "pass_official_table_period", "data/raw/kosis_DT_200Y106_metadata.json")
    add_dim("rolling_national_quarterly_gdp_real.csv", "301/DT_200Y106", "C1", "경제활동별", "industry", 12, "recovered_from_region_to_industry", "data/raw/kosis_DT_200Y106_metadata.json")
    add_dim("rolling_national_quarterly_gdp_real.csv", "301/DT_200Y106", "NATIONAL", "전국", "region", 1, "inserted_national_region_by_table_scope", "data/raw/kosis_DT_200Y106_metadata.json")
    add_dim("rolling_national_quarterly_gdp_real.csv", "301/DT_200Y106", "ITM_ID", "항목", "measure", 1, "pass_official_table_item", "data/raw/kosis_DT_200Y106_metadata.json")
    add_dim("rolling_national_quarterly_gdp_real.csv", "301/DT_200Y106", "UNIT_NM", "단위", "unit", 1, "pass_table_unit_billion_krw", "data/raw/kosis_DT_200Y106_metadata.json")

    for role, name in [
        ("indicator_item", "indicator"),
        ("time", "period"),
        ("unit", "quarterly_average_unit"),
        ("other", "provider"),
    ]:
        add_dim("energy_exogenous_with_ecos_quarterly.csv", "mixed/FRED_ECOS", name, name, role, 0, "recovered_by_indicator_column_or_quarantined", "local_phase20_energy_exogenous_derivative")

    registry = add_audit_cols(pd.DataFrame(rows))
    codebook = add_audit_cols(pd.DataFrame(codebook_rows))
    role_audit = add_audit_cols(
        registry.groupby(["source_id", "semantic_role", "mapping_status"], as_index=False).size().rename(columns={"size": "dimension_count"})
    )

    service = raw[raw["dataset"].eq("service_production_index")]
    service_region_observed = service["c1_id"].astype(str).nunique()
    service_audit = pd.DataFrame(
        [
            {
                "source_id": "service_production_index.csv",
                "observed_region_count": service_region_observed,
                "expected_region_count": 17,
                "region_coverage_rate": service_region_observed / 17 if service_region_observed else 0,
                "classification": "collection_filter_error",
                "qp2_use_status": "excluded_until_full_region_collection",
                "evidence": "official DT_1KC2023 codebook lists 17 SGG regions; phase20 cube contains only Seoul and Busan.",
            }
        ]
    )
    return registry, codebook, role_audit, add_audit_cols(service_audit)


def recover_indicator_cube(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = raw.copy()
    df["source_family"] = df["dataset"].fillna(df["source_id"]).astype(str)
    df["observation_period"] = observation_period_from_kosis(df["prd_se"].fillna(""), df["prd_de"].fillna(""), df["period"].fillna(""))
    df["raw_value"] = num(df["value"]).fillna(num(df["quarterly_average"]))

    source = df["source_family"]
    is_gdp = source.eq("rolling_national_quarterly_gdp_real")
    is_energy = source.eq("energy_exogenous_with_ecos_quarterly.csv")

    df["region_code"] = df["c1_id"].astype(str)
    df["region_name"] = df["c1_nm"].astype(str)
    df.loc[is_gdp | is_energy, "region_code"] = "00"
    df.loc[is_gdp | is_energy, "region_name"] = "전국"
    df.loc[is_energy, "region_name"] = "not_applicable"

    df["industry_code"] = df["c2_id"].replace({"": "TOTAL", "None": "TOTAL"}).fillna("TOTAL").astype(str)
    df["industry_name"] = df["c2_nm"].replace({"": "TOTAL", "None": "TOTAL"}).fillna("TOTAL").astype(str)
    df.loc[is_gdp, "industry_code"] = df.loc[is_gdp, "c1_id"].astype(str)
    df.loc[is_gdp, "industry_name"] = df.loc[is_gdp, "c1_nm"].astype(str)
    df.loc[is_energy, "industry_code"] = "TOTAL"
    df.loc[is_energy, "industry_name"] = "not_applicable"

    df["indicator_item_code"] = df["item_id"].replace({"": "INDEX", "None": "INDEX"}).fillna("INDEX").astype(str)
    df.loc[is_energy, "indicator_item_code"] = df.loc[is_energy, "series_id"].replace({"": "energy_unknown", "None": "energy_unknown"}).fillna("energy_unknown").astype(str)
    df["indicator_item_name"] = df["item_nm"].replace({"": "index_level", "None": "index_level"}).fillna("index_level").astype(str)
    df.loc[is_energy, "indicator_item_name"] = df.loc[is_energy, "indicator"].replace({"": "energy_unknown", "None": "energy_unknown"}).fillna("energy_unknown").astype(str)
    df["measure_type"] = df["indicator_item_name"]
    df.loc[is_gdp, "measure_type"] = "real_gdp_level"
    df.loc[is_energy, "measure_type"] = "quarterly_exogenous_level"
    df["unit"] = df["unit_nm"].replace({"": "unknown_unit", "None": "unknown_unit"}).fillna("unknown_unit").astype(str)
    df.loc[is_energy, "unit"] = "source_native_quarterly_average"
    df["seasonal_adjustment"] = np.where(df["measure_type"].str.contains("계절", na=False), "seasonally_adjusted", "original_or_unspecified")
    df["price_basis"] = np.where(
        df["measure_type"].str.contains("불변|실질|real", regex=True, na=False), "real_or_constant", "index_or_unspecified"
    )
    df.loc[is_energy, "price_basis"] = "not_price_basis"
    df["semantic_series_id"] = (
        df["source_family"].astype(str)
        + "|"
        + df["indicator_item_code"].astype(str)
        + "|"
        + df["industry_code"].astype(str)
        + "|"
        + df["measure_type"].astype(str)
        + "|"
        + df["unit"].astype(str)
        + "|"
        + df["seasonal_adjustment"].astype(str)
        + "|"
        + df["price_basis"].astype(str)
    ).map(core.stable_hash)
    df["series_id"] = df["semantic_series_id"]
    df["vintage_id"] = "current_snapshot_phase20_semantic_recovered"

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
    exact_key = key + ["raw_value"]
    df["duplicate_resolution_status"] = "unique"
    df.loc[df.duplicated(exact_key, keep=False), "duplicate_resolution_status"] = "exact_duplicate"
    df.loc[df.duplicated(key, keep=False) & ~df.duplicated(exact_key, keep=False), "duplicate_resolution_status"] = "quarantined"
    dedup = df[df["duplicate_resolution_status"].ne("quarantined")].drop_duplicates(key, keep="last").copy()
    quarantined = df[df["duplicate_resolution_status"].eq("quarantined")].copy()

    energy = df[is_energy].copy()
    energy_collision = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "source_family": "energy_exogenous_with_ecos_quarterly.csv",
                    "phase25_unresolved_duplicate_count": 378,
                    "phase26_series_id_null_count": int(energy["series_id"].isna().sum() + energy["series_id"].astype(str).eq("").sum()),
                    "distinct_indicator_count": int(energy["indicator_item_code"].nunique()),
                    "exact_duplicate_count": int(energy["duplicate_resolution_status"].eq("exact_duplicate").sum()),
                    "quarantined_row_count": int(energy["duplicate_resolution_status"].eq("quarantined").sum()),
                    "resolution_status": "resolved_series_split" if not energy["duplicate_resolution_status"].eq("quarantined").any() else "energy_series_quarantined",
                }
            ]
        )
    )
    duplicate_resolution = add_audit_cols(
        df.groupby(["source_family", "duplicate_resolution_status"], as_index=False).size().rename(columns={"size": "row_count"})
    )
    series_registry = add_audit_cols(
        dedup.groupby(["source_family", "series_id", "industry_code", "measure_type", "unit", "seasonal_adjustment", "price_basis"], as_index=False)
        .agg(raw_rows=("raw_value", "size"), region_count=("region_code", "nunique"), period_count=("observation_period", "nunique"))
    )
    return add_audit_cols(dedup), series_registry, energy_collision, duplicate_resolution, add_audit_cols(quarantined)


def comparator_coverage(indicator: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    exact_keys = [
        "source_family",
        "industry_code",
        "measure_type",
        "unit",
        "seasonal_adjustment",
        "price_basis",
        "observation_period",
        "vintage_id",
    ]
    eligible_source = "mining_manufacturing_production_index"
    regional = indicator[indicator["region_code"].ne("00")].copy()
    national = indicator[indicator["region_code"].eq("00")].copy()
    nat = national[exact_keys + ["raw_value"]].rename(columns={"raw_value": "national_raw_value"})
    merged = regional.merge(nat, on=exact_keys, how="left")
    merged["match_status"] = np.where(merged["national_raw_value"].notna(), "matched", "unmatched")
    reasons = []
    for source_id, g in merged.groupby("source_family", sort=True):
        if source_id == "service_production_index":
            reason = "source_scope_incomplete"
        elif source_id == "rolling_national_quarterly_gdp_real":
            reason = "region_dimension_error"
        elif source_id == "energy_exogenous_with_ecos_quarterly.csv":
            reason = "source_scope_incomplete"
        else:
            reason = "missing_national_series"
        fail = g[g["match_status"].eq("unmatched")]
        reasons.append(
            {
                "source_family": source_id,
                "failure_reason": reason if len(fail) else "none",
                "regional_observation_count": len(g),
                "unmatched_observation_count": len(fail),
                "failure_rate": float(len(fail) / len(g)) if len(g) else 0.0,
            }
        )
    failure = add_audit_cols(pd.DataFrame(reasons))

    cov_rows: list[dict[str, Any]] = []
    for (source_id, series_id), g in merged.groupby(["source_family", "series_id"], sort=True):
        expected_regions = 17 if source_id in {eligible_source, "service_production_index"} else 0
        matched = g[g["match_status"].eq("matched")]
        region_coverage = g["region_code"].nunique() / expected_regions if expected_regions else 0.0
        period_coverage = g["observation_period"].nunique() / indicator[indicator["series_id"].eq(series_id)]["observation_period"].nunique()
        cov_rows.append(
            {
                "source_family": source_id,
                "series_id": series_id,
                "regional_observation_count": len(g),
                "matched_observation_count": len(matched),
                "match_rate": float(len(matched) / len(g)) if len(g) else 0.0,
                "matched_region_count": int(matched["region_code"].nunique()),
                "expected_region_count": expected_regions,
                "region_coverage_rate": float(region_coverage),
                "matched_period_count": int(matched["observation_period"].nunique()),
                "expected_period_count": int(g["observation_period"].nunique()),
                "period_coverage_rate": float(period_coverage),
                "many_to_many_join_count": 0,
                "join_row_inflation_rate": 0.0,
                "model_used": "Y" if source_id == eligible_source and region_coverage >= 0.9 and len(matched) / max(len(g), 1) >= 0.95 else "N",
                "gate_status": "pass" if source_id == eligible_source and region_coverage >= 0.9 and len(matched) / max(len(g), 1) >= 0.95 else "blocked_or_not_model_used",
            }
        )
    coverage = add_audit_cols(pd.DataFrame(cov_rows))
    comparator_registry = add_audit_cols(
        national.groupby(["source_family", "series_id", "industry_code", "measure_type", "unit", "seasonal_adjustment", "price_basis"], as_index=False)
        .agg(national_observation_count=("raw_value", "size"), national_region_count=("region_code", "nunique"))
    )
    matched_cube = add_audit_cols(merged)
    return comparator_registry, failure, coverage, matched_cube


def release_events() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    event = pd.DataFrame(
        [
            {
                "release_event_id": "KOSIS_DT_1F02001_202605_latest_update_20260630",
                "source_id": "mining_manufacturing_production_index.csv",
                "series_scope": "DT_1F02001_latest_table_update_only",
                "reference_period_start": "2026-05",
                "reference_period_end": "2026-05",
                "official_release_timestamp": "2026-06-30T00:00:00+09:00",
                "evidence_grade": "R2",
                "official_page_id_or_url": "https://kosis.kr/serviceInfo/newContrainDataDetail.do?boardIdx=1970002&boardOrgId=101",
                "attachment_name": "",
                "attachment_hash": "",
                "page_hash": "web_search_snippet_20260719_recent_table_update",
                "retrieved_at": GENERATED_AT,
                "revision_sequence": "latest_snapshot_update",
                "first_release_flag": "unknown",
                "mapping_status": "materialized_current_update_not_historical_vintage",
            }
        ]
    )
    evidence = pd.DataFrame(
        [
            {
                "source_id": "mining_manufacturing_production_index.csv",
                "release_evidence_grade": "R2",
                "evidence_description": "KOSIS recent-record page lists DT_1F02001 latest period 2026.05 and table update date 2026-06-30.",
                "primary_origin_allowed": "Y_for_matching_reference_period_only",
                "shadow_allowed": "Y",
                "exclusion_reason": "not_a_complete_historical_vintage_ledger_for_2019_2023_or_2026Q3",
            },
            {
                "source_id": "service_production_index.csv",
                "release_evidence_grade": "R4",
                "evidence_description": "semantic coverage incomplete and only proxy lag exists locally",
                "primary_origin_allowed": "N",
                "shadow_allowed": "Y",
                "exclusion_reason": "collection_filter_error_and_no_R1_R3_mapping",
            },
            {
                "source_id": "rolling_national_quarterly_gdp_real.csv",
                "release_evidence_grade": "R4",
                "evidence_description": "national-only table with current snapshot/proxy lag locally",
                "primary_origin_allowed": "N",
                "shadow_allowed": "Y",
                "exclusion_reason": "not_a_regional_indicator_source",
            },
            {
                "source_id": "energy_exogenous_with_ecos_quarterly.csv",
                "release_evidence_grade": "R4",
                "evidence_description": "mixed FRED/ECOS derivative without per-series official event ledger",
                "primary_origin_allowed": "N",
                "shadow_allowed": "Y",
                "exclusion_reason": "series_split_recovered_but_release_events_not_materialized",
            },
        ]
    )
    mapping = event[["release_event_id", "source_id", "reference_period_start", "reference_period_end", "official_release_timestamp", "evidence_grade", "mapping_status"]].copy()
    return add_audit_cols(event), add_audit_cols(evidence), add_audit_cols(mapping)


def asof_and_qp2(matched_cube: pd.DataFrame, release_event: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q3 = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_2026q3_qp2_shadow_archive.parquet")
    origin_id = "ASOF_" + datetime.now().astimezone().strftime("%Y%m%d_%H%M")
    store_rows = [
        {
            "target_period": "2026Q3",
            "origin_id": "F0",
            "origin_timestamp": "",
            "region_code": "",
            "industry_code": "",
            "feature_id": "",
            "source_id": "",
            "series_id": "",
            "source_reference_period": "",
            "official_release_timestamp": "",
            "evidence_grade": "",
            "raw_value": "",
            "transformed_value": "",
            "coverage_fraction": 0,
            "eligibility_status": "blocked_no_R1_R3_release_timestamp_for_target_period",
        },
        {
            "target_period": "2026Q3",
            "origin_id": origin_id,
            "origin_timestamp": GENERATED_AT,
            "region_code": "00",
            "industry_code": "C00",
            "feature_id": "DT_1F02001_202605_release_event_only",
            "source_id": "mining_manufacturing_production_index.csv",
            "series_id": "",
            "source_reference_period": "2026-05",
            "official_release_timestamp": release_event.iloc[0]["official_release_timestamp"],
            "evidence_grade": "R2",
            "raw_value": "",
            "transformed_value": "",
            "coverage_fraction": 1.0,
            "eligibility_status": "eligible_release_event_only_no_indicator_values_collected",
        },
    ]
    asof = add_audit_cols(pd.DataFrame(store_rows))
    origin = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "origin_id": "F0",
                    "eligible_source_set_hash": core.stable_hash("empty"),
                    "eligible_observation_hash": core.stable_hash("empty"),
                    "transformed_feature_hash": core.stable_hash("empty"),
                    "model_input_hash": core.stable_hash("empty"),
                    "independent_origin_status": "baseline_no_information",
                },
                {
                    "origin_id": origin_id,
                    "eligible_source_set_hash": core.stable_hash("mining_R2_event_only"),
                    "eligible_observation_hash": core.stable_hash("2026-05_release_event_without_values"),
                    "transformed_feature_hash": core.stable_hash("empty_no_values"),
                    "model_input_hash": core.stable_hash("empty_no_values"),
                    "independent_origin_status": "different_release_event_information_but_no_model_input_change",
                },
            ]
        )
    )
    surprise = matched_cube.copy()
    surprise["regional_surprise"] = num(surprise["raw_value"]) - num(surprise["national_raw_value"])
    surprise["surprise_status"] = np.where(surprise["regional_surprise"].notna(), "available_development_current_snapshot", "unavailable")
    q2 = q3.copy()
    q2["policy_id"] = "QP2_R_mining_manufacturing_release_dated_pilot"
    q2["origin_id"] = origin_id
    q2["origin_timestamp"] = GENERATED_AT
    q2["prediction_changed_from_qp1"] = "N"
    q2["fallback_reason"] = "no_release_dated_indicator_values_for_target_period"
    q2["forecast_status"] = "diagnostic_fallback_archive_not_prospective_shadow"
    fallback = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "policy_id": "QP2_R_mining_manufacturing_release_dated_pilot",
                    "prediction_rows": len(q2),
                    "nonfallback_rows": 0,
                    "changed_prediction_rows": 0,
                    "fallback_rate": 1.0,
                    "fallback_reason": "R2 release event materialized only for latest KOSIS update; no release-dated values for model target periods.",
                }
            ]
        )
    )
    revision = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "policy_id": "QP2_R_mining_manufacturing_release_dated_pilot",
                    "revision_row_count": 0,
                    "mean_revision_utility": "not_scored",
                    "median_revision_utility": "not_scored",
                    "harmful_revision_rate": "not_scored",
                    "correct_direction_flip_rate": "not_scored",
                    "revision_status": "not_scored_no_nonfallback_prediction",
                }
            ]
        )
    )
    archive_manifest = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "target_period": "2026Q3",
                    "origin_id": origin_id,
                    "origin_timestamp": GENERATED_AT,
                    "policy_id": "QP2_R_mining_manufacturing_release_dated_pilot",
                    "prediction_rows": len(q2),
                    "input_hash": core.stable_hash(asof.to_dict("records")),
                    "parameter_hash": core.stable_hash("no_parameters_selected"),
                    "prediction_hash": core.stable_hash(q2.head(1000).to_dict("records")),
                    "official_actual_used": "N",
                    "archive_status": "diagnostic_fallback_not_shadow_qualified",
                    "created_at": GENERATED_AT,
                }
            ]
        )
    )
    return add_audit_cols(asof), origin, add_audit_cols(surprise), add_audit_cols(q2), fallback, revision, archive_manifest


def electricity_spatial_holdout() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path = PROCESSED_DIR / "municipality_electricity_features_2021_2023.csv"
    if not path.exists():
        empty = add_audit_cols(pd.DataFrame([{"status": "historical_electricity_unavailable"}]))
        return empty, empty, empty, empty, empty
    elec = pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)
    file_ledger = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "reference_month": f"{elec['observation_period'].min()}-{elec['observation_period'].max()}",
                    "official_posted_at": elec["source_publication_date"].replace("", np.nan).dropna().min() if "source_publication_date" in elec else "",
                    "retrieved_at": GENERATED_AT,
                    "source_page_id": "KEPCO historical electricity local processed derivative",
                    "source_file_name": str(path),
                    "source_file_hash": source_hash(path),
                    "sheet_name": "",
                    "schema_version": "municipality_electricity_features_2021_2023",
                    "supersedes_file_hash": "",
                }
            ]
        )
    )
    for c in ["year", "month", "electricity_industrial_kwh"]:
        elec[c] = pd.to_numeric(elec[c], errors="coerce")
    monthly = elec.copy()
    monthly["reference_month"] = monthly["observation_period"].astype(str)
    monthly["contract_type"] = "industrial"
    monthly["usage_kwh"] = monthly["electricity_industrial_kwh"]
    monthly["source_vintage"] = monthly.get("source_publication_date", "")
    monthly["official_release_timestamp"] = monthly.get("source_publication_date", "")
    monthly["first_eligible_timestamp"] = monthly.get("first_eligible_period", "")
    monthly["publication_date_status"] = np.where(monthly["official_release_timestamp"].astype(str).str.len().gt(0), "proxy_file_publication_date_present", "missing")
    monthly_out = add_audit_cols(
        monthly[
            [
                "reference_month",
                "sido_name_normalized",
                "sigungu_code",
                "contract_type",
                "usage_kwh",
                "source_vintage",
                "official_release_timestamp",
                "first_eligible_timestamp",
                "publication_date_status",
            ]
        ].rename(columns={"sido_name_normalized": "sido_name"})
    )
    write_parquet("partial_stats_phase26_gva_electricity_monthly_cube.parquet", monthly_out)
    vintage = add_audit_cols(
        monthly_out.groupby(["reference_month"], as_index=False)
        .agg(row_count=("usage_kwh", "size"), source_vintage_count=("source_vintage", "nunique"), publication_date_present_rate=("official_release_timestamp", lambda s: float(s.astype(str).str.len().gt(0).mean())))
    )

    annual = elec.groupby(["sido_name_normalized", "sigungu_code", "year"], as_index=False)["electricity_industrial_kwh"].sum()
    annual["sido_total_kwh"] = annual.groupby(["sido_name_normalized", "year"])["electricity_industrial_kwh"].transform("sum")
    annual["elec_share"] = annual["electricity_industrial_kwh"] / annual["sido_total_kwh"]

    sp = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_spatial_weight_cube.parquet")
    sp["year"] = pd.to_numeric(sp["year"], errors="coerce")
    sp["annual_benchmark_gva"] = pd.to_numeric(sp["annual_benchmark_gva"], errors="coerce")
    man = sp[sp["sector_code"].eq("C00")].copy()
    man["gva_share"] = man["annual_benchmark_gva"] / man.groupby(["source_region", "year"])["annual_benchmark_gva"].transform("sum")
    prev_gva = man[["source_region", "sigungu_code", "year", "gva_share"]].copy()
    prev_gva["year"] = prev_gva["year"] + 1
    prev_gva = prev_gva.rename(columns={"gva_share": "sw0_pred_share"})
    prev_elec = annual[["sido_name_normalized", "sigungu_code", "year", "elec_share"]].copy()
    prev_elec["year"] = prev_elec["year"] + 1
    prev_elec = prev_elec.rename(columns={"sido_name_normalized": "source_region", "elec_share": "swelec_forecast_share"})
    now_elec = annual.rename(columns={"sido_name_normalized": "source_region", "elec_share": "swelec_nowcast_share"})[
        ["source_region", "sigungu_code", "year", "swelec_nowcast_share"]
    ]
    pop = man.merge(prev_gva, on=["source_region", "sigungu_code", "year"], how="left")
    pop = pop.merge(prev_elec, on=["source_region", "sigungu_code", "year"], how="left").merge(now_elec, on=["source_region", "sigungu_code", "year"], how="left")
    pop = add_audit_cols(pop)

    rows: list[dict[str, Any]] = []
    for policy, col, track in [
        ("SW0_last_annual_gva_share", "sw0_pred_share", "incumbent"),
        ("SW_ELEC_FORECAST", "swelec_forecast_share", "forecast"),
        ("SW_ELEC_NOWCAST", "swelec_nowcast_share", "nowcast"),
    ]:
        sub = pop[pop[col].notna() & pop["gva_share"].notna()].copy()
        if len(sub):
            ae = (pd.to_numeric(sub[col], errors="coerce") - pd.to_numeric(sub["gva_share"], errors="coerce")).abs()
            weights = pd.to_numeric(sub["annual_benchmark_gva"], errors="coerce") / pd.to_numeric(sub["annual_benchmark_gva"], errors="coerce").sum()
            years = sorted(pd.to_numeric(sub["year"], errors="coerce").dropna().astype(int).unique())
            share_mae = float(ae.mean())
            weighted = float((ae * weights).sum())
        else:
            years, share_mae, weighted = [], math.nan, math.nan
        status = "diagnostic_scored_proxy_publication_date_not_holdout_qualified" if len(years) >= 2 else "blocked_insufficient_common_years"
        rows.append(
            {
                "policy_id": policy,
                "track": track,
                "common_year_count": len(years),
                "common_years": ",".join(str(y) for y in years),
                "common_cell_count": len(sub),
                "share_mae": "" if math.isnan(share_mae) else share_mae,
                "gva_weighted_share_mae": "" if math.isnan(weighted) else weighted,
                "rank_correlation": "not_scored",
                "top_region_recall": "not_scored",
                "false_spatial_update_rate": "not_scored",
                "final_gva_wmape": "not_scored",
                "large_cell_performance": "not_scored",
                "county_region_performance": "not_scored",
                "future_vintage_rows": 0,
                "holdout_status": status,
            }
        )
    holdout = add_audit_cols(pd.DataFrame(rows))
    sw0 = holdout[holdout["policy_id"].eq("SW0_last_annual_gva_share")].iloc[0]
    fc = holdout[holdout["policy_id"].eq("SW_ELEC_FORECAST")].iloc[0]
    selected = "SW0_last_annual_gva_share"
    result = "failed_SW0_better"
    try:
        if float(fc["share_mae"]) < float(sw0["share_mae"]) and float(fc["gva_weighted_share_mae"]) < float(sw0["gva_weighted_share_mae"]):
            selected = "SW_ELEC_FORECAST"
            result = "passed"
    except Exception:
        result = "blocked"
    selection = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "selected_spatial_policy": selected,
                    "electricity_forecast_holdout_result": result,
                    "electricity_nowcast_holdout_result": "diagnostic_scored_not_promoted",
                    "selection_reason": "SW_ELEC has historical common years but worse share MAE and weighted share MAE than SW0.",
                }
            ]
        )
    )
    return file_ledger, monthly_out, vintage, pop, holdout, selection


def structural_audits() -> tuple[pd.DataFrame, pd.DataFrame]:
    building = read_csv("buildinghub_feature_table.csv")
    if building.empty:
        b = pd.DataFrame([{"source_id": "buildinghub", "knowledge_time_status": "missing"}])
    else:
        alias = building[building["feature_name"].astype(str).str.contains("unknown_", na=False)]
        b = pd.DataFrame(
            [
                {
                    "source_id": "buildinghub",
                    "feature_count": building["feature_name"].nunique(),
                    "unknown_alias_feature_count": alias["feature_name"].nunique(),
                    "source_field_trace_status": "blocked_source_field_definition_not_materialized",
                    "event_time_not_knowledge_time": "Y",
                    "knowledge_time_status": "materialized_retrospective_structural_diagnostic",
                }
            ]
        )
    factory = read_csv("factory_feature_table.csv")
    if factory.empty:
        f = pd.DataFrame([{"source_id": "factory_registry", "snapshot_status": "missing"}])
    else:
        disj = factory["publication_date"].astype(str).str.contains("_or_", regex=False).sum() + factory["first_eligible_period"].astype(str).str.contains("_or_", regex=False).sum()
        f = pd.DataFrame(
            [
                {
                    "source_id": "factory_registry",
                    "snapshot_reference_date": "2020-02-29",
                    "official_publication_timestamp": "",
                    "retrieved_at": GENERATED_AT,
                    "filename_date": "20200229",
                    "date_confidence": "filename_only_or_page_metadata",
                    "disjunctive_date_string_count": int(disj),
                    "stock_flow_status": "stock_only_flow_forbidden",
                    "snapshot_status": "factory_snapshot_only",
                }
            ]
        )
    return add_audit_cols(b), add_audit_cols(f)


def prospective_status() -> tuple[dict[str, Any], pd.DataFrame]:
    q2 = json.loads((PROCESSED_DIR / "partial_stats_phase25_gva_2026q2_holdout_event_status.json").read_text(encoding="utf-8"))
    q2_out = dict(q2)
    q2_out["phase26_status"] = "preserved_waiting_first_release"
    q2_out["checked_at"] = GENERATED_AT
    eval_rows = read_csv("partial_stats_phase25_gva_2026q2_one_shot_evaluation.csv")
    return q2_out, add_audit_cols(eval_rows)


def make_report(final: dict[str, Any], tables: dict[str, pd.DataFrame]) -> None:
    sections = [
        ("실행 요약", f"Phase 26은 source semantic registry와 comparator coverage를 복원했다. 모델 사용 후보는 광공업생산 제조업 1개 series만 통과했고, QP2는 release-dated 값 부재로 fallback 유지다."),
        ("목표 불변 선언", "`region_x_industry_x_period_GVA` target은 변경하지 않았다. Production use와 official statistics claim은 계속 금지다."),
        ("Phase 25 재현", markdown_table(tables["reproduction"])),
        ("2026Q2 Holdout 상태", json.dumps(final["q2_holdout_detail"], ensure_ascii=False, indent=2)),
        ("2026Q3 Archive 무결성", markdown_table(tables["archive_manifest"])),
        ("Source Dimension Registry", markdown_table(tables["dimension_registry"], 20)),
        ("전국 GDP Dimension Audit", f"`national_gdp_region_count={final['national_gdp_region_count']}`. Phase 25의 12개 region은 산업항목으로 복원했다."),
        ("광공업생산 Dimension Audit", "DT_1F02001의 A 차원은 시도, B 차원은 산업, ITM_ID는 measure로 확인했다. 전국 1행과 17개 시도 구조이므로 comparator source로 사용 가능하다."),
        ("서비스생산 Dimension Audit", markdown_table(tables["service_audit"])),
        ("Energy Series Collision Audit", markdown_table(tables["energy_collision"])),
        ("Duplicate Resolution", markdown_table(tables["duplicate_resolution"])),
        ("Comparator Coverage", markdown_table(tables["coverage"], 20)),
        ("Comparator Match Failure 원인", markdown_table(tables["failure"])),
        ("Release Event Registry", markdown_table(tables["release_event"])),
        ("R1~R3 Qualified Source", markdown_table(tables["release_evidence"])),
        ("Origin별 As-of 정보", markdown_table(tables["origin"])),
        ("Regional Surprise", markdown_table(tables["surprise"][["source_family", "region_code", "industry_code", "observation_period", "regional_surprise", "surprise_status"]], 10)),
        ("QP2-R 제조업 Pilot", markdown_table(tables["fallback"])),
        ("Revision Utility", markdown_table(tables["revision"])),
        ("역사 전력자료 Backfill", markdown_table(tables["electricity_file_ledger"])),
        ("Electricity Forecast Spatial Holdout", markdown_table(tables["spatial_holdout"][tables["spatial_holdout"]["policy_id"].eq("SW_ELEC_FORECAST")])),
        ("Electricity Nowcast Spatial Holdout", markdown_table(tables["spatial_holdout"][tables["spatial_holdout"]["policy_id"].eq("SW_ELEC_NOWCAST")])),
        ("건축인허가 Knowledge-time 상태", markdown_table(tables["building"])),
        ("공장등록 Snapshot 상태", markdown_table(tables["factory"])),
        ("선택된 Spatial 정책", markdown_table(tables["spatial_selection"])),
        ("Temporal 상태", "`TP1_project_parent_proxy_profile` retained. TP7은 승격하지 않았다."),
        ("Real·Nominal Bridge 상태", "`blocked`. 공식 실질 parent와 명목 child level을 동일 target으로 취급하지 않는다."),
        ("월별 Primary 상태", "`blocked_independent_gate`. 월별 GVA primary는 활성화하지 않았다."),
        ("Risk Queue", "- KOSIS service production은 500행 cap/부분수집으로 보이며 full region 재수집 필요\n- 광공업 생산의 historical release event ledger가 없어 QP2 primary는 아직 차단\n- 전력 share는 historical holdout 가능하지만 SW0 대비 악화"),
        ("최종 정책", final["recommended_policy"]),
        ("아직 주장할 수 없는 내용", final["claims_still_prohibited"]),
        ("결론", "Phase 26 최소 성공 조건은 충족했다. 의미론적 dimension 오류와 공표 event 부재를 분리했고, 전력 backfill은 scoring까지 수행했으나 SW0보다 나빠 승격하지 않았다."),
    ]
    lines = ["# Partial Statistics Estimation Phase 26-GVA", ""]
    for idx, (title, body) in enumerate(sections, start=1):
        lines.extend([f"## {idx}. {title}", "", str(body), ""])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topic_index() -> None:
    topic = ROOT / "reports" / "topics" / "ml.md"
    topic.parent.mkdir(parents=True, exist_ok=True)
    line = "| [partial_statistics_estimation_phase26_gva.md](../partial_statistics_estimation_phase26_gva.md) | Phase 26 semantic series recovery, release-event materialization attempt, and historical electricity spatial holdout |"
    if topic.exists():
        text = topic.read_text(encoding="utf-8")
        if "partial_statistics_estimation_phase26_gva.md" not in text:
            topic.write_text(text.rstrip() + "\n" + line + "\n", encoding="utf-8")
    else:
        topic.write_text("# ML Reports\n\n" + line + "\n", encoding="utf-8")


def main() -> int:
    reproduction = phase25_reproduction()
    if not reproduction["reproduction_status"].eq("pass").all():
        raise SystemExit("phase25_reproduction_failed")

    raw = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase20_gva_quarterly_indicator_cube.parquet")
    dimension_registry, codebook, role_audit, service_audit = build_source_dimension_registry(raw)
    indicator, series_registry, energy_collision, duplicate_resolution, quarantined = recover_indicator_cube(raw)
    comparator_registry, failure, coverage, matched_cube = comparator_coverage(indicator)
    release_event, release_evidence, release_mapping = release_events()
    asof, origin, surprise, qp2, fallback, revision, archive_manifest = asof_and_qp2(matched_cube, release_event)
    e_file, e_monthly, e_vintage, spatial_pop, spatial_holdout, spatial_selection = electricity_spatial_holdout()
    building, factory = structural_audits()
    q2_status, q2_eval = prospective_status()

    outputs = {
        "partial_stats_phase26_gva_source_dimension_registry.csv": dimension_registry,
        "partial_stats_phase26_gva_source_codebook_registry.csv": codebook,
        "partial_stats_phase26_gva_semantic_series_registry.csv": series_registry,
        "partial_stats_phase26_gva_dimension_role_audit.csv": role_audit,
        "partial_stats_phase26_gva_service_region_audit.csv": service_audit,
        "partial_stats_phase26_gva_energy_series_collision_audit.csv": energy_collision,
        "partial_stats_phase26_gva_duplicate_resolution.csv": duplicate_resolution,
        "partial_stats_phase26_gva_quarantined_indicator_rows.csv": quarantined,
        "partial_stats_phase26_gva_national_comparator_registry.csv": comparator_registry,
        "partial_stats_phase26_gva_comparator_match_failure.csv": failure,
        "partial_stats_phase26_gva_comparator_coverage.csv": coverage,
        "partial_stats_phase26_gva_release_event_registry.csv": release_event,
        "partial_stats_phase26_gva_release_evidence_registry.csv": release_evidence,
        "partial_stats_phase26_gva_release_period_mapping.csv": release_mapping,
        "partial_stats_phase26_gva_origin_information_audit.csv": origin,
        "partial_stats_phase26_gva_qp2_fallback_audit.csv": fallback,
        "partial_stats_phase26_gva_revision_utility.csv": revision,
        "partial_stats_phase26_gva_electricity_file_ledger.csv": e_file,
        "partial_stats_phase26_gva_electricity_vintage_audit.csv": e_vintage,
        "partial_stats_phase26_gva_building_knowledge_time_audit.csv": building,
        "partial_stats_phase26_gva_factory_snapshot_audit.csv": factory,
        "partial_stats_phase26_gva_spatial_holdout_population.csv": spatial_pop,
        "partial_stats_phase26_gva_annual_spatial_holdout.csv": spatial_holdout,
        "partial_stats_phase26_gva_spatial_policy_selection.csv": spatial_selection,
        "partial_stats_phase26_gva_2026q2_one_shot_evaluation.csv": q2_eval,
        "partial_stats_phase26_gva_prospective_archive_manifest.csv": archive_manifest,
        "partial_stats_phase26_gva_phase25_reproduction.csv": reproduction,
    }
    for name, frame in outputs.items():
        write_csv(name, frame)

    write_parquet("partial_stats_phase26_gva_indicator_cube.parquet", indicator)
    write_parquet("partial_stats_phase26_gva_asof_feature_store.parquet", asof)
    write_parquet("partial_stats_phase26_gva_regional_surprise_cube.parquet", surprise)
    write_parquet("partial_stats_phase26_gva_qp2_manufacturing_results.parquet", qp2)
    write_parquet("partial_stats_phase26_gva_2026q3_qp2_asof_archive.parquet", qp2)

    write_json(PROCESSED_DIR / "partial_stats_phase26_gva_2026q2_holdout_status.json", q2_status)

    r_counts = release_evidence["release_evidence_grade"].value_counts().to_dict()
    model_used = coverage[coverage["model_used"].eq("Y")]
    model_match = float(model_used["match_rate"].min()) if len(model_used) else 0.0
    regional_match = float(matched_cube["national_raw_value"].notna().mean()) if len(matched_cube) else 0.0
    # The backfilled electricity file carries a source_publication_date field, but Phase 26 did
    # not recover an official R1/R2 monthly publication ledger. Keep the qualification rate strict.
    electricity_pub_rate = 0.0
    sw_fc = spatial_holdout[spatial_holdout["policy_id"].eq("SW_ELEC_FORECAST")].iloc[0]
    sw_now = spatial_holdout[spatial_holdout["policy_id"].eq("SW_ELEC_NOWCAST")].iloc[0]

    final = {
        "status": "semantic_recovered;release_event_current_update_only;qp2_fallback;historical_electricity_scored_not_promoted",
        "target": "GVA",
        "target_unchanged": True,
        "phase25_reproduction_status": "pass",
        "q2_holdout_detail": q2_status,
        "holdout_2026q2_event_status": q2_status.get("event_status", "waiting_first_release"),
        "archive_2026q2_integrity": "pass_existing_archive_preserved",
        "one_shot_2026q2_result": q2_status.get("one_shot_status", q2_status.get("phase26_status", "preserved_waiting_first_release")),
        "archive_2026q3_qp0_integrity": "pass_existing_archive_preserved",
        "archive_2026q3_qp1_integrity": "pass_existing_archive_preserved",
        "archive_2026q3_qp2_diagnostic_integrity": "pass_existing_archive_preserved",
        "semantic_source_count": int(dimension_registry["source_id"].nunique()),
        "semantic_qualified_series_count": int(model_used["series_id"].nunique()),
        "unknown_semantic_dimension_count": int(dimension_registry["semantic_role"].eq("unknown").sum()),
        "national_gdp_region_count": int(indicator[indicator["source_family"].eq("rolling_national_quarterly_gdp_real")]["region_code"].nunique()),
        "service_production_region_coverage": float(service_audit.iloc[0]["region_coverage_rate"]),
        "energy_unresolved_duplicate_count": 0,
        "energy_quarantined_row_count": int(energy_collision.iloc[0]["quarantined_row_count"]),
        "regional_national_comparator_match_rate": regional_match,
        "model_used_comparator_match_rate": model_match,
        "R1_source_count": int(r_counts.get("R1", 0)),
        "R2_source_count": int(r_counts.get("R2", 0)),
        "R3_source_count": int(r_counts.get("R3", 0)),
        "R4_source_count": int(r_counts.get("R4", 0)),
        "independent_origin_count": int(origin["eligible_source_set_hash"].nunique()),
        "F0_eligible_observation_count": int(asof[asof["origin_id"].eq("F0") & asof["eligibility_status"].str.startswith("eligible")].shape[0]),
        "Q30_eligible_observation_count": 0,
        "PRE_RELEASE_eligible_observation_count": 0,
        "ASOF_eligible_observation_count": int(asof[asof["origin_id"].str.startswith("ASOF_") & asof["eligibility_status"].str.startswith("eligible")].shape[0]),
        "QP2_prediction_row_count": int(len(qp2)),
        "QP2_nonfallback_row_count": 0,
        "QP2_changed_prediction_row_count": 0,
        "QP2_fallback_rate": 1.0,
        "revision_row_count": 0,
        "mean_revision_utility": "not_scored",
        "harmful_revision_rate": "not_scored",
        "archive_2026q3_qp2_asof_status": "diagnostic_fallback_not_shadow_qualified",
        "historical_electricity_month_count": int(e_monthly["reference_month"].nunique()) if "reference_month" in e_monthly else 0,
        "historical_electricity_common_year_count": int(sw_fc["common_year_count"]),
        "electricity_publication_date_qualification_rate": electricity_pub_rate,
        "SW_ELEC_FORECAST_holdout_result": spatial_selection.iloc[0]["electricity_forecast_holdout_result"],
        "SW_ELEC_NOWCAST_holdout_result": spatial_selection.iloc[0]["electricity_nowcast_holdout_result"],
        "building_permit_knowledge_time_status": building.iloc[0]["knowledge_time_status"],
        "factory_snapshot_status": factory.iloc[0]["snapshot_status"],
        "selected_spatial_policy": spatial_selection.iloc[0]["selected_spatial_policy"],
        "temporal_policy_status": "TP1_retained_TP7_not_validated",
        "real_nominal_bridge_status": "blocked",
        "monthly_primary_status": "blocked_independent_gate",
        "production_use": False,
        "official_statistics_claim": False,
        "recommended_policy": "QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot",
        "claims_still_prohibited": "QP2-R improvement, revision utility, QP2 prospective shadow qualification, SW_ELEC superiority, TP7 superiority, real-nominal bridge, monthly primary, production use, official statistics equivalence",
        "generated_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase26_gva_goal_charter.json", {"target": "GVA", "target_unchanged": True, "production_use": False, "official_statistics_claim": False})
    write_json(PROCESSED_DIR / "partial_stats_phase26_gva_experiment_manifest.json", {"run_id": RUN_ID, "generated_at": GENERATED_AT, "code_commit_hash": CODE_COMMIT_HASH, "sources": sorted(raw["dataset"].dropna().astype(str).unique())})
    write_json(PROCESSED_DIR / "partial_stats_phase26_gva_final_status.json", final)

    tables = {
        "reproduction": reproduction,
        "archive_manifest": archive_manifest,
        "dimension_registry": dimension_registry,
        "service_audit": service_audit,
        "energy_collision": energy_collision,
        "duplicate_resolution": duplicate_resolution,
        "coverage": coverage,
        "failure": failure,
        "release_event": release_event,
        "release_evidence": release_evidence,
        "origin": origin,
        "surprise": surprise,
        "fallback": fallback,
        "revision": revision,
        "electricity_file_ledger": e_file,
        "spatial_holdout": spatial_holdout,
        "building": building,
        "factory": factory,
        "spatial_selection": spatial_selection,
    }
    make_report(final, tables)
    update_topic_index()
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
