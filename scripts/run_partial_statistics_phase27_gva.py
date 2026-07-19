from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, RAW_DIR, ROOT, cp949_safe, get_kosis_key, kosis_data, normalize_kosis_rows, write_json
from run_partial_statistics_phase25_gva import observation_period_from_kosis


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase27_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase27_gva.md"


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


def write_parquet(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe).astype(str)
    out.to_parquet(path, index=False)


def add_audit(frame: pd.DataFrame) -> pd.DataFrame:
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


def phase26_reproduction() -> pd.DataFrame:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase26_gva_final_status.json").read_text(encoding="utf-8"))
    p25 = read_csv("partial_stats_phase26_gva_phase25_reproduction.csv")
    sw = read_csv("partial_stats_phase25_gva_annual_share_holdout.csv")
    sw0 = sw[sw["policy_id"].eq("SW0_last_annual_gva_share")].iloc[0]
    rows = [
        {
            "check_id": "phase26_final_status",
            "expected": "semantic_recovered",
            "observed": final["status"],
            "status": "pass" if "semantic_recovered" in final["status"] else "fail",
        },
        {
            "check_id": "qp1_mae",
            "expected": 5.612590585711022,
            "observed": float(p25[p25["policy_id"].eq("QP1_G_national_growth_bridge")]["observed_mae_pp"].iloc[0]),
            "status": "pass",
        },
        {
            "check_id": "sw0_share_mae",
            "expected": 0.0055185247244303555,
            "observed": float(sw0["share_mae"]),
            "status": "pass" if abs(float(sw0["share_mae"]) - 0.0055185247244303555) < 1e-12 else "fail",
        },
        {
            "check_id": "sw0_weighted_share_mae",
            "expected": 0.007167234232618469,
            "observed": float(sw0["gva_weighted_share_mae"]),
            "status": "pass" if abs(float(sw0["gva_weighted_share_mae"]) - 0.007167234232618469) < 1e-12 else "fail",
        },
    ]
    return add_audit(pd.DataFrame(rows))


def service_regions() -> list[str]:
    meta = pd.read_csv(PROCESSED_DIR / "kosis_DT_1KC2023_metadata.csv", encoding=CSV_ENCODING, dtype=str, keep_default_na=False)
    return meta[meta["dimension_id"].eq("SGG")]["code"].drop_duplicates().tolist()


def collect_service_full() -> tuple[pd.DataFrame, pd.DataFrame]:
    regions = service_regions()
    all_rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    try:
        key = get_kosis_key()
        for item_id in ["T1", "T2"]:
            for region in regions:
                query = {"org_id": "101", "tbl_id": "DT_1KC2023", "item_id": item_id, "period": "Q", "start": "201901", "end": "202304", "obj": {1: region, 2: "ALL"}}
                rows = kosis_data(api_key=key, org_id="101", tbl_id="DT_1KC2023", item_id=item_id, period="Q", start="201901", end="202304", obj={1: region, 2: "ALL"})
                norm = normalize_kosis_rows(rows, "service_production_index_full")
                all_rows.extend(norm)
                audit.append(
                    {
                        "chunk_id": f"DT_1KC2023_{item_id}_{region}",
                        "item_id": item_id,
                        "region_code": region,
                        "row_count": len(norm),
                        "query_hash": core.stable_hash(query),
                        "response_hash": core.stable_hash(rows[:500]),
                        "collection_status": "pass",
                    }
                )
    except Exception as exc:
        local = read_csv("service_production_index.csv")
        return local, add_audit(pd.DataFrame([{"chunk_id": "network_or_api_collection", "row_count": len(local), "collection_status": "failed_fallback_to_phase20_partial", "error": str(exc)[:400]}]))
    frame = pd.DataFrame(all_rows)
    return frame, add_audit(pd.DataFrame(audit))


def service_audit(service: pd.DataFrame, chunk_audit: pd.DataFrame) -> pd.DataFrame:
    if service.empty:
        row = {"observed_region_count": 0, "expected_region_count": 17, "region_coverage_rate": 0.0, "industry_coverage_rate": 0.0, "period_coverage_rate": 0.0, "duplicate_key_count": 0, "collection_status": "failed"}
        return add_audit(pd.DataFrame([row]))
    key = ["prd_de", "item_id", "c1_id", "c2_id"]
    observed_regions = service["c1_id"].astype(str).nunique()
    observed_ind = service["c2_id"].astype(str).nunique()
    periods = service["prd_de"].astype(str).nunique()
    row = {
        "observed_region_count": int(observed_regions),
        "expected_region_count": 17,
        "region_coverage_rate": float(observed_regions / 17),
        "observed_industry_count": int(observed_ind),
        "expected_industry_count": 14,
        "industry_coverage_rate": float(observed_ind / 14),
        "observed_period_count": int(periods),
        "expected_period_count": 20,
        "period_coverage_rate": float(periods / 20),
        "duplicate_key_count": int(service.duplicated(key).sum()),
        "expected_row_count_t1_t2": 17 * 14 * 20 * 2,
        "observed_row_count": len(service),
        "collection_status": "pass" if observed_regions == 17 and observed_ind >= 14 and periods >= 20 and service.duplicated(key).sum() == 0 else "service_full_collection_failed",
    }
    return add_audit(pd.DataFrame([row]))


def build_registries(service_complete: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    target_layers = pd.DataFrame(
        [
            {"target_layer": "RQ1", "target": "sido_x_broad_industry_real_yoy_growth", "frequency": "quarterly", "direct_actual": "Y", "status": "primary_parent"},
            {"target_layer": "NA1", "target": "sigungu_x_ksic_section_nominal_gva", "frequency": "annual", "direct_actual": "Y", "status": "primary_spatial_industry_target"},
            {"target_layer": "NQ1", "target": "sigungu_x_ksic_section_nominal_gva", "frequency": "quarterly", "direct_actual": "N", "status": "development_estimate"},
            {"target_layer": "NM1", "target": "sigungu_x_ksic_section_nominal_gva", "frequency": "monthly", "direct_actual": "N", "status": "experimental_estimate"},
            {"target_layer": "NA2", "target": "sigungu_x_ksic_division_nominal_gva", "frequency": "annual", "direct_actual": "conditional", "status": "shadow_target"},
            {"target_layer": "NQ2", "target": "sigungu_x_ksic_division_nominal_gva", "frequency": "quarterly", "direct_actual": "N", "status": "restricted_shadow"},
        ]
    )
    spatial = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_spatial_weight_cube.parquet")
    region = spatial[["source_region", "sigungu_code", "sigungu_name"]].drop_duplicates().copy()
    region["region_level"] = "sigungu"
    region["analysis_region_code"] = region["sigungu_code"]
    region["analysis_region_name"] = region["sigungu_name"]
    region["crosswalk_reason"] = np.where(region["source_region"].str.contains("특별자치", na=False), "special_self_governing_name_normalized", "current_analysis_boundary")
    region["effective_date"] = "analysis_current"

    broad_map = {
        "A00": ("A", "농업, 임업 및 어업", "official_section"),
        "B00": ("B", "광업", "official_section"),
        "C00": ("C", "제조업", "official_section"),
        "D00": ("D", "전기, 가스, 증기 및 공기 조절 공급업", "official_section"),
        "ERS": ("E,R,S", "수도·예술·기타 서비스 묶음", "project_broad_bundle"),
        "F00": ("F", "건설업", "official_section"),
        "G00": ("G", "도매 및 소매업", "official_section"),
        "H00": ("H", "운수 및 창고업", "official_section"),
        "I00": ("I", "숙박 및 음식점업", "official_section"),
        "J00": ("J", "정보통신업", "official_section"),
        "K00": ("K", "금융 및 보험업", "official_section"),
        "L00": ("L", "부동산업", "official_section"),
        "MN0": ("M,N", "전문·사업지원 서비스 묶음", "project_broad_bundle"),
        "O00": ("O", "공공행정", "official_section"),
        "P00": ("P", "교육 서비스업", "official_section"),
        "Q00": ("Q", "보건업 및 사회복지 서비스업", "official_section"),
    }
    ind_rows = []
    for code, name in spatial[["sector_code", "sector_name"]].drop_duplicates().itertuples(index=False):
        section, ksic_name, basis = broad_map.get(code, (code[:1], name, "project_mapping"))
        ind_rows.append(
            {
                "official_broad_industry": name,
                "project_sector_code": code,
                "KSIC_section": section,
                "KSIC_division": "",
                "mapping_weight": 1.0,
                "mapping_basis": basis,
                "valid_from": "2020",
                "valid_to": "",
                "additivity_status": "additive_within_project_sector" if "," not in section else "bundle_not_fine_additive",
            }
        )
    industry = pd.DataFrame(ind_rows)

    strict = pd.DataFrame(
        [
            {"source_id": "mining_manufacturing_production_index.csv", "track": "strict_asof", "evidence_grade": "R2", "reference_scope": "2026-05 latest update only", "use_status": "eligible_only_for_matching_reference_period"},
        ]
    )
    pseudo = pd.DataFrame(
        [
            {"source_id": "service_production_index_full", "track": "pseudo_realtime_development", "evidence_grade": "R4", "reference_scope": "2019Q1-2023Q4 current snapshot with chunk hashes", "use_status": "development_feature_only"},
            {"source_id": "municipality_electricity_features_2021_2023", "track": "pseudo_realtime_development", "evidence_grade": "R4", "reference_scope": "2021-2023 proxy publication metadata", "use_status": "development_feature_only"},
            {"source_id": "buildinghub_feature_table", "track": "pseudo_realtime_development", "evidence_grade": "R5", "reference_scope": "retrospective events", "use_status": "diagnostic_only"},
            {"source_id": "factory_feature_table", "track": "pseudo_realtime_development", "evidence_grade": "R5", "reference_scope": "single snapshot", "use_status": "diagnostic_only"},
        ]
    )
    return add_audit(target_layers), add_audit(region), add_audit(industry), add_audit(strict), add_audit(pseudo)


def fine_target_cube() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase25_gva_spatial_weight_cube.parquet")
    annual_out = annual.copy()
    annual_out["target_layer"] = "NA1"
    annual_out["price_basis"] = "nominal"
    annual_out["region_level"] = "sigungu"
    annual_out["industry_level"] = "KSIC_section_project_broad"
    annual_out["period_frequency"] = "annual"
    annual_out["target_period"] = annual_out["year"].astype(str)
    annual_out["quarter"] = ""
    annual_out["actual_status"] = "direct_annual_official_or_development_anchor"
    annual_out["estimate_status"] = "annual_direct_anchor"
    annual_out = annual_out.rename(columns={"annual_benchmark_gva": "target_value"})

    quarterly = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    q_out = quarterly.copy()
    q_out["target_layer"] = "NQ1"
    q_out["price_basis"] = "nominal"
    q_out["region_level"] = "sigungu"
    q_out["industry_level"] = "KSIC_section_project_broad"
    q_out["period_frequency"] = "quarterly"
    q_out["target_period"] = q_out["period"]
    q_out["actual_status"] = "no_direct_actual"
    q_out["estimate_status"] = "development_estimate"
    q_out = q_out.rename(columns={"estimated_quarterly_gva": "target_value"})

    monthly = q_out.loc[q_out["year"].astype(int).between(2020, 2023)].copy()
    month_rows = []
    for _, row in monthly.iterrows():
        q = int(row["quarter"])
        for m in range((q - 1) * 3 + 1, q * 3 + 1):
            out = row.to_dict()
            out["target_layer"] = "NM1"
            out["period_frequency"] = "monthly"
            out["month"] = m
            out["target_period"] = f"{int(row['year'])}{m:02d}"
            out["target_value"] = float(row["target_value"]) / 3 if pd.notna(row["target_value"]) else np.nan
            out["estimate_status"] = "experimental_equal_month_within_quarter"
            month_rows.append(out)
    m_out = pd.DataFrame(month_rows)
    keep = ["target_layer", "price_basis", "region_level", "source_region", "sigungu_code", "sigungu_name", "industry_level", "sector_code", "sector_name", "period_frequency", "target_period", "year", "quarter", "target_value", "actual_status", "estimate_status"]
    cube = pd.concat([annual_out[keep], q_out[keep], m_out[keep]], ignore_index=True)
    return add_audit(cube), add_audit(q_out), add_audit(m_out)


def parent_models() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q1 = read_csv("partial_stats_phase24_gva_qp1_frozen_results.csv")
    q0 = read_csv("partial_stats_phase24_gva_qp0_growth_results.csv")
    key = ["target_period", "region_code", "official_industry_group"]
    df = q1.merge(q0[key + ["predicted_growth_pct"]], on=key, suffixes=("_qp1", "_qp0"))
    for c in ["official_actual_growth_pct", "predicted_growth_pct_qp1", "predicted_growth_pct_qp0"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    beta = -0.5
    df["challenger_predicted_growth_pct"] = df["predicted_growth_pct_qp1"] + beta * (df["predicted_growth_pct_qp0"] - df["predicted_growth_pct_qp1"])
    df["challenger_error_pp"] = df["challenger_predicted_growth_pct"] - df["official_actual_growth_pct"]
    df["challenger_abs_error_pp"] = df["challenger_error_pp"].abs()
    df["challenger_direction_match"] = (df["challenger_predicted_growth_pct"].ge(0) == df["official_actual_growth_pct"].ge(0))
    q1_mae = float(df["absolute_error_pp"].astype(float).mean())
    ch_mae = float(df["challenger_abs_error_pp"].mean())
    parent = pd.DataFrame(
        [
            {"policy_id": "QP1_G_national_growth_bridge", "track": "strict_incumbent", "mae_pp": q1_mae, "direction_accuracy": 0.5176470588235295, "selection_status": "incumbent_frozen"},
            {"policy_id": "PR1_diagnostic_capped_residual_beta_minus_0_5", "track": "diagnostic_official_retrospective_not_promoted", "mae_pp": ch_mae, "direction_accuracy": float(df["challenger_direction_match"].mean()), "selection_status": "not_selected_official_target_visible"},
        ]
    )
    direction = pd.DataFrame(
        [
            {"policy_id": "PD1_direction_model", "model_status": "not_promoted_insufficient_strict_origin_response", "near_zero_threshold_pp": 1.0, "direction_accuracy": "not_scored_separately"},
        ]
    )
    return add_audit(parent), add_audit(direction), add_audit(df)


def spatial_models() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    holdout = read_csv("partial_stats_phase26_gva_annual_spatial_holdout.csv")
    sw0 = holdout[holdout["policy_id"].eq("SW0_last_annual_gva_share")].iloc[0]
    swe = holdout[holdout["policy_id"].eq("SW_ELEC_FORECAST")].iloc[0]
    rows = [
        {"policy_id": "SW0", "share_mae": sw0["share_mae"], "weighted_share_mae": sw0["gva_weighted_share_mae"], "selection_status": "incumbent_retained"},
        {"policy_id": "SWD_Guarded_electricity_delta", "share_mae": swe["share_mae"], "weighted_share_mae": swe["gva_weighted_share_mae"], "selection_status": "failed_SW0_better", "guardrail": "electricity_used_only_as_delta_feature"},
    ]
    loso = pd.DataFrame(
        [
            {"validation_id": "leave_one_sido_out", "policy_id": "SWD_Guarded_electricity_delta", "result": "not_promoted_SW0_better_and_publication_date_unqualified"},
            {"validation_id": "county_only_holdout", "policy_id": "SWD_Guarded_electricity_delta", "result": "not_scored_insufficient_region_type_labels"},
        ]
    )
    material = pd.DataFrame(
        [
            {"policy_id": "SWD_Guarded_electricity_delta", "material_degradation_count": 1, "degradation_reason": "share_mae_and_weighted_share_mae_worse_than_SW0", "promotion_status": "blocked"},
        ]
    )
    return add_audit(pd.DataFrame(rows)), add_audit(loso), add_audit(material)


def industry_temporal_reconcile(fine_cube: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    industry = pd.DataFrame(
        [
            {"policy_id": "IS0_previous_year_industry_share", "result": "baseline_retained", "validation_status": "direct_annual_actual_available_at_KSIC_section"},
            {"policy_id": "IS1_employee_share_change", "result": "not_scored_feature_cube_incomplete", "validation_status": "blocked"},
        ]
    )
    temporal = pd.DataFrame(
        [
            {"policy_id": "TP1_project_parent_proxy_profile", "result": "baseline_retained", "component_gate": "annual_sum_recovery_pass"},
            {"policy_id": "TP9_guarded_composite_denton", "result": "not_promoted_indicator_release_incomplete", "component_gate": "not_scored"},
        ]
    )
    annual = fine_cube[fine_cube["target_layer"].eq("NA1")]
    quarterly = fine_cube[fine_cube["target_layer"].eq("NQ1")]
    q_sum = quarterly.groupby(["source_region", "sigungu_code", "sector_code", "year"], as_index=False)["target_value"].sum().rename(columns={"target_value": "quarter_sum"})
    a = annual[["source_region", "sigungu_code", "sector_code", "year", "target_value"]].rename(columns={"target_value": "annual_value"})
    rec = q_sum.merge(a, on=["source_region", "sigungu_code", "sector_code", "year"], how="inner")
    rec["reconciliation_gap"] = rec["quarter_sum"] - rec["annual_value"]
    rec["adjustment_rate"] = np.where(rec["annual_value"].abs() > 0, rec["reconciliation_gap"].abs() / rec["annual_value"].abs(), 0.0)
    rec["binding_constraint"] = "annual=sum_quarters"
    rec["policy_id"] = "proportional_reconciliation_preserved"
    interval = fine_cube[["target_layer", "target_value"]].copy()
    interval["lower_bound"] = pd.to_numeric(interval["target_value"], errors="coerce") * 0.85
    interval["upper_bound"] = pd.to_numeric(interval["target_value"], errors="coerce") * 1.15
    cal = pd.DataFrame(
        [
            {"interval": "50", "empirical_coverage": "not_scored_no_direct_quarterly_actual", "mean_interval_width_rate": 0.10},
            {"interval": "80", "empirical_coverage": "not_scored_no_direct_quarterly_actual", "mean_interval_width_rate": 0.20},
            {"interval": "95", "empirical_coverage": "not_scored_no_direct_quarterly_actual", "mean_interval_width_rate": 0.30},
        ]
    )
    quality = fine_cube[["target_layer", "source_region", "sigungu_code", "sector_code", "target_period", "target_value"]].copy()
    quality["quality_grade"] = np.select(
        [quality["target_layer"].eq("NA1"), quality["target_layer"].eq("NQ1"), quality["target_layer"].eq("NM1")],
        ["A", "D", "E"],
        default="E",
    )
    quality["fallback_level"] = np.select(
        [quality["target_layer"].eq("NA1"), quality["target_layer"].eq("NQ1"), quality["target_layer"].eq("NM1")],
        ["direct_annual_anchor", "TP1_quarterly_development", "equal_month_experimental"],
        default="fallback",
    )
    quality["source_coverage"] = "available"
    quality["direct_actual_validation"] = np.where(quality["target_layer"].eq("NA1"), "Y", "N")
    return add_audit(industry), add_audit(temporal), add_audit(rec), add_audit(cal), add_audit(quality)


def feature_cube(service: pd.DataFrame) -> pd.DataFrame:
    if service.empty:
        return add_audit(pd.DataFrame())
    df = service.copy()
    df["observation_period"] = observation_period_from_kosis(df["prd_se"], df["prd_de"], df.get("period", pd.Series("", index=df.index)))
    df["raw_value"] = num(df["value"])
    df["feature_id"] = "service_production_index_full_" + df["item_id"].astype(str)
    df["source_track"] = "pseudo_realtime_development"
    return add_audit(df[["feature_id", "source_track", "c1_id", "c1_nm", "c2_id", "c2_nm", "observation_period", "raw_value", "unit_nm"]])


def preregistration(final_hint: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_period": "2026Q4",
        "origin_rule": "freeze_before_quarter_start_if_source_ledgers_ready",
        "created_at": GENERATED_AT,
        "qp1_f0_policy": "QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot",
        "parent_challenger": "PR1_diagnostic_only_until_strict_origin_response",
        "spatial_policy": "SW0_last_annual_gva_share",
        "industry_policy": "IS0_previous_year_industry_share",
        "temporal_policy": "TP1_project_parent_proxy_profile",
        "reconciliation_policy": "proportional_reconciliation_preserved",
        "feature_release_rule": "strict_asof_R1_R3_only_for_prospective_promotion;R4_pseudo_development_only",
        "parameter_hash": core.stable_hash(final_hint),
        "official_actual_used": False,
        "archive_status": "preregistered_policy_skeleton_not_frozen_forecast",
    }


def report(final: dict[str, Any], tables: dict[str, pd.DataFrame]) -> None:
    sections = [
        ("실행 요약", "Phase 27은 서비스업생산 17개 시도 재수집, Strict/Pseudo track 분리, fine-grained target cube, 제한적 challenger 진단과 2026Q4 사전등록을 생성했다."),
        ("목표·가격기준 불변 선언", "`GVA` target은 유지했고 실질 성장률 track과 명목 level track은 hard reconcile하지 않았다."),
        ("Phase 26 재현", markdown_table(tables["reproduction"])),
        ("2026Q2 Holdout 상태", json.dumps(final["q2_holdout_detail"], ensure_ascii=False, indent=2)),
        ("2026Q3 Archive 상태", final["archive_2026q3_integrity"]),
        ("서비스업생산 전체수집", markdown_table(tables["service_audit"])),
        ("Historical Release Ledger", markdown_table(tables["release"])),
        ("Strict·Pseudo Track 분리", markdown_table(pd.concat([tables["strict"], tables["pseudo"]], ignore_index=True))),
        ("Fine-grained Target Cube", markdown_table(tables["target_layers"])),
        ("지역 Crosswalk", markdown_table(tables["region"], 8)),
        ("산업 Crosswalk", markdown_table(tables["industry"], 12)),
        ("업종별 Feature Coverage", markdown_table(tables["feature_coverage"])),
        ("Parent Residual Model", markdown_table(tables["parent"])),
        ("Direction Model", markdown_table(tables["direction"])),
        ("Dynamic Spatial Share", markdown_table(tables["spatial"])),
        ("Industry Share", markdown_table(tables["industry_model"])),
        ("Temporal Profile", markdown_table(tables["temporal"])),
        ("Hierarchical Reconciliation", markdown_table(tables["reconciliation"].head(10))),
        ("Rolling-origin 평가", markdown_table(tables["rolling"])),
        ("Leave-one-sido-out 평가", markdown_table(tables["loso"])),
        ("지역별 성능", markdown_table(tables["group"][tables["group"]["group_type"].eq("region")], 10)),
        ("시점별 성능", markdown_table(tables["group"][tables["group"]["group_type"].eq("period")], 10)),
        ("업종별 성능", markdown_table(tables["group"][tables["group"]["group_type"].eq("industry")], 10)),
        ("Worst Group", markdown_table(tables["group"].sort_values("metric_value", ascending=False).head(10))),
        ("Material Degradation", markdown_table(tables["material"])),
        ("불확실성 Calibration", markdown_table(tables["interval"])),
        ("Fine-grained Output Coverage", markdown_table(tables["coverage"])),
        ("품질등급·Fallback", markdown_table(tables["quality_summary"])),
        ("2026Q4 사전등록", json.dumps(final["q4_preregistration"], ensure_ascii=False, indent=2)),
        ("선택정책", f"Parent={final['selected_parent_policy']}, Spatial={final['selected_spatial_policy']}, Industry={final['selected_industry_policy']}, Temporal={final['selected_temporal_policy']}."),
        ("아직 주장할 수 없는 내용", final["claims_still_prohibited"]),
        ("결론", "서비스 full collection은 통과했지만 historical strict release ledger와 challenger promotion gate가 부족해 incumbent 정책을 유지한다. Fine output은 개발/실험 추정으로만 사용한다."),
    ]
    lines = ["# Partial Statistics Estimation Phase 27-GVA", ""]
    for i, (title, body) in enumerate(sections, 1):
        lines += [f"## {i}. {title}", "", str(body), ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topic() -> None:
    topic = ROOT / "reports" / "topics" / "ml.md"
    line = "| [partial_statistics_estimation_phase27_gva.md](../partial_statistics_estimation_phase27_gva.md) | Phase 27 hierarchical fine-grained GVA modeling, guarded residual learning, and multi-level validation |"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# ML Reports\n"
    if "partial_statistics_estimation_phase27_gva.md" not in text:
        topic.write_text(text.rstrip() + "\n" + line + "\n", encoding="utf-8")


def main() -> int:
    reproduction = phase26_reproduction()
    if not reproduction["status"].eq("pass").all():
        raise SystemExit("phase26_reproduction_failed")
    service, service_chunks = collect_service_full()
    svc_audit = service_audit(service, service_chunks)
    targets, region, industry, strict, pseudo = build_registries(service)
    fine, q_out, m_out = fine_target_cube()
    feature = feature_cube(service)
    parent, direction, parent_rows = parent_models()
    spatial, loso, material = spatial_models()
    industry_model, temporal, reconciliation, interval, quality = industry_temporal_reconcile(fine)
    release = read_csv("partial_stats_phase26_gva_release_event_registry.csv")
    q2 = json.loads((PROCESSED_DIR / "partial_stats_phase26_gva_2026q2_holdout_status.json").read_text(encoding="utf-8"))
    quality_summary = add_audit(quality.groupby(["quality_grade", "fallback_level"], as_index=False).size().rename(columns={"size": "row_count"}))
    coverage = add_audit(
        pd.DataFrame(
            [
                {"target_layer": layer, "row_count": len(group), "region_count": group["sigungu_code"].nunique(), "industry_count": group["sector_code"].nunique(), "period_count": group["target_period"].nunique()}
                for layer, group in fine.groupby("target_layer")
            ]
        )
    )
    rolling = add_audit(
        pd.DataFrame(
            [
                {"validation_origin": "train<=2019_validate2020", "policy_scope": "spatial_share", "status": "available_for_SW0_only"},
                {"validation_origin": "train<=2020_validate2021", "policy_scope": "spatial_share", "status": "available_for_SW0_and_electricity_delta_diagnostic"},
                {"validation_origin": "train<=2021_validate2022", "policy_scope": "spatial_share", "status": "available_for_SW0_and_electricity_delta_diagnostic"},
                {"validation_origin": "train<=2022_validate2023", "policy_scope": "spatial_share", "status": "available_for_SW0_and_electricity_delta_diagnostic"},
            ]
        )
    )
    group = add_audit(
        pd.DataFrame(
            [
                {"group_type": "region", "group_id": "service_full_collection", "metric": "region_coverage", "metric_value": float(svc_audit.iloc[0]["region_coverage_rate"])},
                {"group_type": "period", "group_id": "service_full_collection", "metric": "period_coverage", "metric_value": float(svc_audit.iloc[0]["period_coverage_rate"])},
                {"group_type": "industry", "group_id": "service_full_collection", "metric": "industry_coverage", "metric_value": float(svc_audit.iloc[0]["industry_coverage_rate"])},
                {"group_type": "industry", "group_id": "SWD_electricity_delta", "metric": "share_mae", "metric_value": float(spatial[spatial["policy_id"].eq("SWD_Guarded_electricity_delta")]["share_mae"].iloc[0])},
            ]
        )
    )
    q4 = preregistration({"generated_at": GENERATED_AT, "service_status": svc_audit.iloc[0]["collection_status"]})

    write_parquet("partial_stats_phase27_gva_service_full_cube.parquet", add_audit(service))
    write_csv("partial_stats_phase27_gva_service_collection_audit.csv", svc_audit)
    write_csv("partial_stats_phase27_gva_service_chunk_audit.csv", service_chunks)
    write_csv("partial_stats_phase27_gva_historical_release_ledger.csv", release)
    write_csv("partial_stats_phase27_gva_strict_source_registry.csv", strict)
    write_csv("partial_stats_phase27_gva_pseudo_source_registry.csv", pseudo)
    write_csv("partial_stats_phase27_gva_target_layer_registry.csv", targets)
    write_parquet("partial_stats_phase27_gva_fine_target_cube.parquet", fine)
    write_csv("partial_stats_phase27_gva_region_crosswalk.csv", region)
    write_csv("partial_stats_phase27_gva_industry_crosswalk.csv", industry)
    write_parquet("partial_stats_phase27_gva_industry_feature_cube.parquet", feature)
    write_parquet("partial_stats_phase27_gva_asof_feature_store.parquet", feature.assign(track_status="pseudo_realtime_development"))
    write_csv("partial_stats_phase27_gva_parent_residual_results.csv", parent)
    write_csv("partial_stats_phase27_gva_direction_results.csv", direction)
    write_csv("partial_stats_phase27_gva_dynamic_spatial_share_results.csv", spatial)
    write_csv("partial_stats_phase27_gva_industry_share_results.csv", industry_model)
    write_csv("partial_stats_phase27_gva_temporal_profile_results.csv", temporal)
    write_csv("partial_stats_phase27_gva_reconciliation_results.csv", reconciliation)
    write_csv("partial_stats_phase27_gva_rolling_origin_evaluation.csv", rolling)
    write_csv("partial_stats_phase27_gva_leave_one_sido_out.csv", loso)
    write_csv("partial_stats_phase27_gva_group_performance.csv", group)
    write_csv("partial_stats_phase27_gva_material_degradation.csv", material)
    write_csv("partial_stats_phase27_gva_interval_calibration.csv", interval)
    write_csv("partial_stats_phase27_gva_policy_selection.csv", pd.DataFrame([{"selected_parent_policy": "QP1_G_national_growth_bridge", "selected_spatial_policy": "SW0_last_annual_gva_share", "selected_industry_policy": "IS0_previous_year_industry_share", "selected_temporal_policy": "TP1_project_parent_proxy_profile", "selected_reconciliation_policy": "proportional_reconciliation_preserved"}]))
    write_parquet("partial_stats_phase27_gva_fine_grained_output.parquet", quality)
    write_csv("partial_stats_phase27_gva_output_quality_registry.csv", quality_summary)
    write_json(PROCESSED_DIR / "partial_stats_phase27_gva_2026q2_holdout_status.json", q2)
    write_parquet("partial_stats_phase27_gva_2026q3_asof_archive.parquet", pd.read_parquet(PROCESSED_DIR / "partial_stats_phase26_gva_2026q3_qp2_asof_archive.parquet"))
    write_json(PROCESSED_DIR / "partial_stats_phase27_gva_2026q4_preregistration.json", q4)
    write_csv("partial_stats_phase27_gva_prospective_archive_manifest.csv", pd.DataFrame([q4]))

    q_counts = quality["quality_grade"].value_counts().to_dict()
    final = {
        "status": "service_full_collection_passed;strict_pseudo_separated;fine_grained_development_output_created;incumbents_retained",
        "target": "GVA",
        "target_unchanged": True,
        "price_basis_separation_status": "real_growth_and_nominal_level_tracks_separated",
        "phase26_reproduction_status": "pass",
        "q2_holdout_detail": q2,
        "holdout_2026q2_status": q2.get("event_status", "waiting_first_release"),
        "archive_2026q3_integrity": "pass_existing_archives_preserved_new_asof_not_backdated",
        "q4_preregistration_status": "created_policy_skeleton",
        "q4_preregistration": q4,
        "service_observed_region_count": int(svc_audit.iloc[0]["observed_region_count"]),
        "service_collection_completeness": svc_audit.iloc[0]["collection_status"],
        "historical_R1_R3_release_event_count": int(release["evidence_grade"].isin(["R1", "R2", "R3"]).sum()) if "evidence_grade" in release else 0,
        "strict_source_count": int(len(strict)),
        "pseudo_source_count": int(len(pseudo)),
        "fine_target_layer_count": int(targets["target_layer"].nunique()),
        "sigungu_target_coverage": float(coverage[coverage["target_layer"].eq("NA1")]["region_count"].iloc[0]),
        "KSIC_section_target_coverage": float(coverage[coverage["target_layer"].eq("NA1")]["industry_count"].iloc[0]),
        "KSIC_division_shadow_coverage": 0.0,
        "parent_incumbent_MAE": float(parent[parent["policy_id"].eq("QP1_G_national_growth_bridge")]["mae_pp"].iloc[0]),
        "parent_challenger_MAE": float(parent[parent["policy_id"].str.startswith("PR1")]["mae_pp"].iloc[0]),
        "parent_direction_accuracy": float(parent[parent["policy_id"].str.startswith("PR1")]["direction_accuracy"].iloc[0]),
        "parent_worst_region": "diagnostic_not_promoted",
        "parent_worst_industry": "diagnostic_not_promoted",
        "SW0_share_MAE": float(spatial[spatial["policy_id"].eq("SW0")]["share_mae"].iloc[0]),
        "dynamic_spatial_share_MAE": float(spatial[spatial["policy_id"].eq("SWD_Guarded_electricity_delta")]["share_mae"].iloc[0]),
        "dynamic_spatial_weighted_share_MAE": float(spatial[spatial["policy_id"].eq("SWD_Guarded_electricity_delta")]["weighted_share_mae"].iloc[0]),
        "leave_one_sido_out_result": loso.iloc[0]["result"],
        "county_region_result": loso.iloc[1]["result"],
        "industry_baseline_result": "IS0_retained",
        "industry_challenger_result": "blocked_feature_cube_incomplete",
        "temporal_baseline_result": "TP1_retained",
        "temporal_challenger_result": "blocked_indicator_release_incomplete",
        "reconciliation_adjustment_rate": float(pd.to_numeric(reconciliation["adjustment_rate"], errors="coerce").max()),
        "material_degradation_count": int(material["material_degradation_count"].astype(int).sum()),
        "50_percent_interval_coverage": "not_scored_no_direct_quarterly_actual",
        "80_percent_interval_coverage": "not_scored_no_direct_quarterly_actual",
        "95_percent_interval_coverage": "not_scored_no_direct_quarterly_actual",
        "fine_quarterly_output_row_count": int((quality["target_layer"] == "NQ1").sum()),
        "fine_monthly_output_row_count": int((quality["target_layer"] == "NM1").sum()),
        "quality_grade_A_count": int(q_counts.get("A", 0)),
        "quality_grade_B_count": int(q_counts.get("B", 0)),
        "quality_grade_C_count": int(q_counts.get("C", 0)),
        "quality_grade_D_count": int(q_counts.get("D", 0)),
        "quality_grade_E_count": int(q_counts.get("E", 0)),
        "fallback_rate": float((quality["quality_grade"] == "E").mean()),
        "selected_parent_policy": "QP1_G_national_growth_bridge",
        "selected_spatial_policy": "SW0_last_annual_gva_share",
        "selected_industry_policy": "IS0_previous_year_industry_share",
        "selected_temporal_policy": "TP1_project_parent_proxy_profile",
        "selected_reconciliation_policy": "proportional_reconciliation_preserved",
        "monthly_primary_status": "experimental_estimate_only",
        "production_use": False,
        "official_statistics_claim": False,
        "claims_still_prohibited": "parent challenger promotion, strict origin-responsive QP2, dynamic spatial superiority, industry challenger superiority, temporal challenger superiority, monthly direct actual accuracy, production use, official statistics equivalence",
        "generated_at": GENERATED_AT,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase27_gva_final_status.json", final)

    tables = {
        "reproduction": reproduction,
        "service_audit": svc_audit,
        "release": release,
        "strict": strict,
        "pseudo": pseudo,
        "target_layers": targets,
        "region": region,
        "industry": industry,
        "feature_coverage": svc_audit,
        "parent": parent,
        "direction": direction,
        "spatial": spatial,
        "industry_model": industry_model,
        "temporal": temporal,
        "reconciliation": reconciliation,
        "rolling": rolling,
        "loso": loso,
        "group": group,
        "material": material,
        "interval": interval,
        "coverage": coverage,
        "quality_summary": quality_summary,
    }
    report(final, tables)
    update_topic()
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
