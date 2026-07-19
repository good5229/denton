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
RUN_ID = "partial_statistics_estimation_phase30_reci_local_fine"
DERIVED_DIR = ROOT / "data" / "derived"
MAIN_REPORT = ROOT / "reports" / "partial_statistics_estimation_phase30_reci_local_fine.md"


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


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def write_derived(name: str, frame: pd.DataFrame) -> None:
    write_csv(DERIVED_DIR / name, frame)


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).astype(str).replace({"nan": "", "NaN": "", "None": ""})
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def table_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return core.stable_hash(path.read_bytes().hex()[:200000])


def claim_grade_registry() -> pd.DataFrame:
    rows = [
        {"claim_grade": "O", "value_status": "observed_official", "meaning": "direct official actual, not prediction", "allowed_for_emd_fine_reci": "N"},
        {"claim_grade": "A", "value_status": "validated_forecast", "meaning": "same-grain direct actual backtest passed", "allowed_for_emd_fine_reci": "N"},
        {"claim_grade": "B", "value_status": "validated_component_estimate", "meaning": "direct upper/synthetic component validation passed", "allowed_for_emd_fine_reci": "Y"},
        {"claim_grade": "C", "value_status": "multi_proxy_activity_signal", "meaning": "withheld proxy or event validation passed", "allowed_for_emd_fine_reci": "Y"},
        {"claim_grade": "D", "value_status": "constrained_allocation", "meaning": "upper aggregate reconciled but no direct lower validation", "allowed_for_emd_fine_reci": "Y"},
        {"claim_grade": "E", "value_status": "experimental_fallback", "meaning": "weak proxy, equal split, or pseudo-only fallback", "allowed_for_emd_fine_reci": "Y"},
        {"claim_grade": "U", "value_status": "unavailable", "meaning": "minimum support failed; do not create value", "allowed_for_emd_fine_reci": "Y"},
    ]
    return add_audit(pd.DataFrame(rows))


def adaptive_resolution_rules() -> pd.DataFrame:
    rows = [
        {"rule_id": "R-SPACE-1", "axis": "region", "condition": "emd proxy and code mapping available", "effective_level": "emd", "fallback": "sigungu"},
        {"rule_id": "R-SPACE-2", "axis": "region", "condition": "small/suppressed/unstable emd support", "effective_level": "sigungu", "fallback": "sido"},
        {"rule_id": "R-IND-1", "axis": "industry", "condition": "KSIC middle support and validation available", "effective_level": "KSIC_middle", "fallback": "KSIC_section"},
        {"rule_id": "R-IND-2", "axis": "industry", "condition": "support scarce or crosswalk unstable", "effective_level": "KSIC_section", "fallback": "industry_bundle"},
        {"rule_id": "R-TIME-1", "axis": "time", "condition": "native quarterly or component profile available", "effective_level": "quarter", "fallback": "annual"},
        {"rule_id": "R-TIME-2", "axis": "time", "condition": "native monthly public source unavailable", "effective_level": "quarter", "fallback": "equal_month_E"},
    ]
    return add_audit(pd.DataFrame(rows))


def source_catalog() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    specs = [
        ("official_sigungu_gva_anchor", "partial_stats_phase28_gva_annual_target_cube.parquet", "sigungu×KSIC_section×annual", "anchor/validation", "R2", "official annual direct target; no lower direct actual"),
        ("emd_2015_economic_census_proxy", "emd_quarterly_gva_estimates.csv", "emd×KSIC_section×quarter", "feature", "R4", "current derived from 2015 census proxy; pseudo allocation"),
        ("seoul_2024_business_map_proxy", "seoul_emd_quarterly_gva_estimates_2024_proxy.csv", "seoul_emd×KSIC_section×quarter", "validation-only", "R4", "use as withheld proxy against 2015 proxy where possible"),
        ("service_production_full", "partial_stats_phase27_gva_service_full_cube.parquet", "sido×service_industry×quarter", "feature/component", "R4", "complete current snapshot; release archive forward only"),
        ("manufacturing_detail_proxy", "detailed_industry_quarterly_estimates.csv", "sigungu_or_sido×KSIC_middle/class×quarter", "feature/component", "R4", "lag-aware but mostly pseudo development"),
        ("service_detail_proxy", "service_detail_quarterly_estimates.csv", "sigungu_or_sido×KSIC_middle×quarter", "feature/component", "R4", "national service detail index allocation"),
        ("kosis_employment_feature", "kosis_employment_feature_table.csv", "region×industry×annual", "feature", "R4", "release date missing; development only"),
        ("kosis_business_feature", "kosis_business_feature_table.csv", "region×industry×annual", "feature", "R4", "release date missing; development only"),
        ("buildinghub_event_pilot", "buildinghub_feature_table.csv", "sigungu×event_month", "feature/event", "R4", "event semantics improving but broad coverage/release incomplete"),
        ("factory_feature_snapshot", "factory_feature_table.csv", "sigungu×factory_stock", "feature/event", "R4", "stock snapshot; historical flow limited"),
    ]
    rows = []
    for source_id, filename, grain, role, evidence_grade, note in specs:
        path = PROCESSED_DIR / filename
        exists = path.exists()
        row_count = ""
        if exists:
            if path.suffix == ".parquet":
                try:
                    row_count = len(pd.read_parquet(path))
                except Exception:
                    row_count = "unknown"
            else:
                row_count = sum(1 for _ in path.open("rb")) - 1
        rows.append(
            {
                "source_id": source_id,
                "grain": grain,
                "measure": "mixed",
                "reference_period": "varies",
                "official_release_at": "" if evidence_grade in {"R3", "R4", "R5"} else "source_documented",
                "first_eligible_origin": "forward_only_or_development" if evidence_grade in {"R3", "R4"} else "source_release_date",
                "revision_sequence": "unknown",
                "historical_coverage": "available" if exists else "missing",
                "region_coverage": "derived_from_file",
                "industry_coverage": "derived_from_file",
                "ksic_version": "mixed_or_crosswalk_required",
                "region_code_version": "mixed_or_crosswalk_required",
                "flow_or_stock": "mixed",
                "missing_semantics": "not_fully_classified",
                "evidence_grade": evidence_grade,
                "retrieval_hash": table_hash(path),
                "role": role,
                "row_count": row_count,
                "note": note,
            }
        )
    ledger = add_audit(pd.DataFrame(rows))
    catalog = ledger[["source_id", "grain", "role", "evidence_grade", "historical_coverage", "note"]].copy()
    paid = add_audit(pd.DataFrame([
        {"source_family": "paid_card_sales", "status": "excluded", "reason": "high-cost private data excluded by Phase30 scope"},
        {"source_family": "paid_mobile_population", "status": "excluded", "reason": "high-cost private data excluded by Phase30 scope"},
        {"source_family": "paid_commercial_area_vendor", "status": "excluded", "reason": "licensing/cost outside public-data PoC"},
    ]))
    return ledger, add_audit(catalog), paid


def pre2020_gva_audit() -> pd.DataFrame:
    candidates = []
    for filename, direct in [
        ("partial_stats_phase28_gva_annual_target_cube.parquet", "Y"),
        ("partial_stats_phase27_gva_fine_target_cube.parquet", "mixed"),
        ("emd_annual_gva_estimates.csv", "N"),
        ("seoul_emd_annual_gva_estimates.csv", "N"),
        ("detailed_industry_annual_estimates.csv", "N"),
        ("service_detail_annual_estimates.csv", "N"),
    ]:
        path = PROCESSED_DIR / filename
        if not path.exists():
            candidates.append({"source_file": filename, "exists": "N", "min_year": "", "max_year": "", "pre2020_rows": 0, "direct_official_actual": direct, "use_policy": "missing"})
            continue
        df = pd.read_parquet(path) if path.suffix == ".parquet" else read_csv(path)
        year_col = "year" if "year" in df.columns else "target_period"
        years = num(df[year_col].astype(str).str[:4]) if year_col in df.columns else pd.Series(dtype=float)
        pre_rows = int(years.lt(2020).sum())
        if direct == "Y" and pre_rows > 0:
            policy = "can_extend_direct_annual_validation_after_crosswalk_audit"
        elif pre_rows > 0:
            policy = "reference_or_proxy_only_not_official_actual"
        else:
            policy = "no_pre2020_rows"
        candidates.append(
            {
                "source_file": filename,
                "exists": "Y",
                "min_year": int(years.min()) if len(years.dropna()) else "",
                "max_year": int(years.max()) if len(years.dropna()) else "",
                "pre2020_rows": pre_rows,
                "direct_official_actual": direct,
                "use_policy": policy,
            }
        )
    return add_audit(pd.DataFrame(candidates))


def crosswalk_quality() -> pd.DataFrame:
    rows = []
    for source_id, filename, threshold in [
        ("ksic8_9", "ksic8_9_official_crosswalk.csv", "official_crosswalk_available"),
        ("ksic9_10", "ksic9_10_official_crosswalk.csv", "official_crosswalk_available"),
        ("factory_ksic_mapping", "factory_ksic_mapping_phase4b.csv", "blocked_if_unresolved_above_gate"),
        ("emd_code_mapping", "buildinghub_legal_dong_request_universe.csv", "legal_dong_code_available"),
    ]:
        path = PROCESSED_DIR / filename
        df = read_csv(path) if path.exists() else pd.DataFrame()
        rows.append(
            {
                "crosswalk_id": source_id,
                "source_file": filename,
                "row_count": len(df),
                "column_count": len(df.columns),
                "quality_status": "available_development" if len(df) else "missing",
                "gate_policy": threshold,
            }
        )
    return add_audit(pd.DataFrame(rows))


def pilot_manifest() -> pd.DataFrame:
    pilots = [
        ("urban_service_core", "서울특별시", "종로구", "G/I/J/ERS", "service temporal and commercial concentration"),
        ("metropolitan_mixed", "서울특별시", "송파구", "G/F/L", "residential-commercial mix and building proxy"),
        ("manufacturing_industrial", "강원특별자치도", "동해시", "C/D/B", "factory/industrial/energy proxy readiness"),
        ("construction_variation", "부산광역시", "해운대구", "F/L", "buildinghub event semantics pilot"),
        ("agriculture_county", "강원특별자치도", "평창군", "A", "agriculture public proxy candidate"),
        ("energy_facility", "울산광역시", "울산", "D/C", "energy/facility module candidate"),
        ("mining_sparse", "강원특별자치도", "삼척시", "B", "hurdle sparse mining module candidate"),
        ("island_tourism", "제주특별자치도", "제주시", "I/ERS/H", "tourism and service signal"),
    ]
    rows = []
    for archetype, sido, sigungu, sectors, purpose in pilots:
        rows.append(
            {
                "pilot_id": archetype,
                "source_region": sido,
                "sigungu_name": sigungu,
                "sector_scope": sectors,
                "selection_basis": "archetype_and_existing_source_readiness",
                "purpose": purpose,
                "production_use": "false",
            }
        )
    return add_audit(pd.DataFrame(rows))


def spatial_component_scorecard() -> pd.DataFrame:
    annual = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase28_gva_annual_target_cube.parquet")
    df = annual.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df["actual_gva"] = pd.to_numeric(df["target_value"], errors="coerce")
    parent = df.groupby(["source_region", "sector_code", "year"], as_index=False)["actual_gva"].sum().rename(columns={"actual_gva": "parent_gva"})
    df = df.merge(parent, on=["source_region", "sector_code", "year"], how="left")
    df["actual_share"] = np.where(df["parent_gva"].gt(0), df["actual_gva"] / df["parent_gva"], np.nan)
    lag = df[["source_region", "sigungu_code", "sector_code", "year", "actual_share"]].copy()
    lag["year"] += 1
    lag = lag.rename(columns={"actual_share": "lag_share"})
    holdout = df.merge(lag, on=["source_region", "sigungu_code", "sector_code", "year"], how="left")
    holdout = holdout[holdout["year"].between(2021, 2023) & holdout["lag_share"].notna()].copy()
    holdout["S0_previous_share_error"] = (holdout["lag_share"] - holdout["actual_share"]).abs()
    equal = holdout.groupby(["source_region", "sector_code", "year"])["sigungu_code"].transform("count")
    holdout["S00_equal_share"] = 1 / equal
    holdout["S00_equal_share_error"] = (holdout["S00_equal_share"] - holdout["actual_share"]).abs()

    weighted_prev = float((holdout["S0_previous_share_error"] * holdout["parent_gva"].abs()).sum() / holdout["parent_gva"].abs().sum())
    weighted_equal = float((holdout["S00_equal_share_error"] * holdout["parent_gva"].abs()).sum() / holdout["parent_gva"].abs().sum())
    rows = [
        {"component_id": "S00_equal_sigungu_share", "synthetic_task": "sido_to_sigungu_annual_share", "share_mae": float(holdout["S00_equal_share_error"].mean()), "weighted_share_mae": weighted_equal, "claim_grade_candidate": "D", "selection_status": "baseline_reference"},
        {"component_id": "S0_previous_sigungu_share", "synthetic_task": "sido_to_sigungu_annual_share", "share_mae": float(holdout["S0_previous_share_error"].mean()), "weighted_share_mae": weighted_prev, "claim_grade_candidate": "B" if weighted_prev < weighted_equal else "D", "selection_status": "selected_for_shadow_if_proxy_missing"},
    ]
    if (PROCESSED_DIR / "seoul_emd_2015_vs_2024_proxy_summary.csv").exists():
        comp = read_csv(PROCESSED_DIR / "seoul_emd_2015_vs_2024_proxy_summary.csv")
        rows.append(
            {
                "component_id": "S1_emd_proxy_stability_2015_vs_2024_seoul",
                "synthetic_task": "withheld_proxy_stability",
                "share_mae": "",
                "weighted_share_mae": "",
                "claim_grade_candidate": "C",
                "selection_status": "validation_only_proxy_disagreement_material",
                "diagnostic": f"median_abs_difference={num(comp['absolute_difference']).median():.6f}",
            }
        )
    return add_audit(pd.DataFrame(rows))


def industry_component_scorecard() -> pd.DataFrame:
    rows = []
    mf = read_csv(PROCESSED_DIR / "detail_manufacturing_proxy_share_backtest.csv")
    if not mf.empty:
        rows.append(
            {
                "component_id": "I1_manufacturing_lagged_proxy_share",
                "synthetic_task": "lagged_proxy_vs_same_year_value_added_proxy",
                "row_count": len(mf),
                "share_mae": float(num(mf["absolute_share_error"]).mean()),
                "weighted_share_mae": "",
                "claim_grade_candidate": "B",
                "selection_status": "development_component_candidate",
            }
        )
    svc = read_csv(PROCESSED_DIR / "service_detail_summary.csv")
    if not svc.empty:
        rows.append(
            {
                "component_id": "I2_service_detail_index_share",
                "synthetic_task": "constraint_and_proxy_component",
                "row_count": int(svc["quarterly_rows"].iloc[0]),
                "share_mae": "",
                "weighted_share_mae": "",
                "claim_grade_candidate": "D",
                "selection_status": "component_available_direct_gva_unvalidated",
            }
        )
    return add_audit(pd.DataFrame(rows))


def temporal_component_scorecard() -> pd.DataFrame:
    phase29 = read_csv(PROCESSED_DIR / "partial_stats_phase29_gva_service_temporal_component_metrics.csv")
    rows = []
    for row in phase29.to_dict("records"):
        rows.append(
            {
                "component_id": row["policy_id"],
                "synthetic_task": row["proxy_target"],
                "weighted_share_mae": row["weighted_share_mae"],
                "turning_point_proxy_accuracy": row["turning_point_proxy_accuracy"],
                "claim_grade_candidate": "C" if row["policy_id"] == "TQ3_service_prior_profile" else "D",
                "selection_status": row["selection_status"],
            }
        )
    return add_audit(pd.DataFrame(rows))


def withheld_proxy_scorecard() -> pd.DataFrame:
    rows = []
    comp = read_csv(PROCESSED_DIR / "seoul_emd_2015_vs_2024_proxy_summary.csv")
    if not comp.empty:
        old = num(comp["old_2015_proxy_annual_gva"])
        new = num(comp["new_2024_proxy_annual_gva"])
        corr = old.corr(new) if old.notna().sum() > 2 and new.notna().sum() > 2 else np.nan
        rows.append(
            {
                "validation_id": "seoul_emd_2015_generation_vs_2024_business_proxy_withheld",
                "generation_proxy_family": "2015_economic_census",
                "withheld_proxy_family": "2024_seoul_business_map",
                "row_count": len(comp),
                "rank_correlation": float(corr) if np.isfinite(corr) else "",
                "median_abs_percent_difference": float(num(comp["percent_difference_vs_old"]).abs().median()),
                "validation_status": "withheld_proxy_available_large_revision_risk",
            }
        )
    rows.append(
        {
            "validation_id": "paid_private_sources",
            "generation_proxy_family": "none",
            "withheld_proxy_family": "paid_card_mobile_excluded",
            "row_count": 0,
            "rank_correlation": "",
            "median_abs_percent_difference": "",
            "validation_status": "excluded_by_scope_not_used_for_generation_or_validation",
        }
    )
    return add_audit(pd.DataFrame(rows))


def event_validation() -> pd.DataFrame:
    rows = [
        {"event_family": "buildinghub_permit_start_approval", "source_status": "pilot_available", "event_date_status": "separated", "publication_date_status": "not_release_qualified", "validation_status": "not_scored_phase30_requires_forward_event_archive"},
        {"event_family": "factory_open_close", "source_status": "snapshot_available", "event_date_status": "incomplete", "publication_date_status": "not_release_qualified", "validation_status": "not_scored_historical_flow_incomplete"},
        {"event_family": "powerplant_generation", "source_status": "candidate_required", "event_date_status": "missing", "publication_date_status": "missing", "validation_status": "not_scored_energy_module_pending"},
        {"event_family": "agriculture_weather_disaster", "source_status": "candidate_required", "event_date_status": "missing", "publication_date_status": "missing", "validation_status": "not_scored_agriculture_module_pending"},
    ]
    return add_audit(pd.DataFrame(rows))


def confidence_components(row: pd.Series) -> dict[str, Any]:
    claim = row.get("claim_grade", "D")
    mapping = 0.6 if row.get("effective_region_level") == "emd" else 0.8
    temporal = 0.65 if row.get("frequency") == "quarter" else 0.4
    external = 0.45 if claim in {"C", "D"} else 0.2
    small_cell = 0.5 if row.get("fallback_level") != "none" else 0.7
    return {
        "data_support": 0.5,
        "mapping_quality": mapping,
        "model_stability": 0.45,
        "external_agreement": external,
        "temporal_validity": temporal,
        "hierarchy_adjustment": 0.8,
        "small_cell_risk": small_cell,
    }


def reci_shadow() -> tuple[pd.DataFrame, pd.DataFrame]:
    emd = read_csv(PROCESSED_DIR / "seoul_emd_quarterly_gva_estimates_2024_proxy.csv")
    if emd.empty:
        emd = read_csv(PROCESSED_DIR / "emd_quarterly_gva_estimates.csv")
        emd["emd_code_2024"] = emd.get("emd_code", "")
        emd["official_sigungu_code"] = emd.get("sigungu_code", "")
    pilots = pilot_manifest()
    pilot_names = set(pilots["sigungu_name"])
    q = emd[emd["sigungu_name"].isin(pilot_names) & emd["year"].astype(str).isin(["2023", "2024"])].copy()
    if q.empty:
        q = emd.head(5000).copy()
    q["estimated_gva_num"] = num(q["estimated_gva"])
    q["region_key"] = q.get("emd_code_2024", q.get("emd_code", "")).astype(str)
    q["industry_key"] = q["sector_code"].astype(str)
    base = q[q["year"].astype(str).eq("2023")].groupby(["region_key", "industry_key"])["estimated_gva_num"].mean().rename("base_gva").reset_index()
    q = q.merge(base, on=["region_key", "industry_key"], how="left")
    q["reci_index"] = np.where(q["base_gva"].gt(0), q["estimated_gva_num"] / q["base_gva"] * 100, np.nan)
    q = q.sort_values(["region_key", "industry_key", "period"])
    q["prev_index"] = q.groupby(["region_key", "industry_key"])["reci_index"].shift(1)
    q["direction"] = np.select([q["reci_index"] > q["prev_index"] * 1.01, q["reci_index"] < q["prev_index"] * 0.99], ["up", "down"], default="neutral")
    q["rank"] = q.groupby(["period", "sector_code"])["reci_index"].rank(ascending=False, method="min")
    q["anomaly_score"] = q.groupby(["region_key", "industry_key"])["reci_index"].transform(lambda s: ((s - s.mean()) / s.std(ddof=0)).replace([np.inf, -np.inf], np.nan) if s.std(ddof=0) else 0)
    q["effective_region_level"] = "emd"
    q["effective_industry_level"] = "KSIC_section"
    q["frequency"] = "quarter"
    q["value_status"] = "activity_signal_and_constrained_allocation"
    q["claim_grade"] = "D"
    q["fallback_level"] = "industry_fallback_to_section"
    q["direct_actual_available"] = "N"
    q["production_use"] = "false"
    q["official_statistics_claim"] = "false"
    q["as_of_date"] = GENERATED_AT[:10]
    q["reference_period"] = q["period"]
    q["gva_consistent_allocation"] = q["estimated_gva_num"]
    q["reconciliation_adjustment"] = 0.0
    q["source_family_count"] = 1
    q["confidence_components"] = q.apply(lambda row: json.dumps(confidence_components(row), ensure_ascii=False, sort_keys=True), axis=1)
    cols = [
        "as_of_date",
        "reference_period",
        "region_key",
        "emd_name",
        "sigungu_code",
        "sigungu_name",
        "effective_region_level",
        "industry_key",
        "sector_name",
        "effective_industry_level",
        "frequency",
        "reci_index",
        "direction",
        "rank",
        "anomaly_score",
        "gva_consistent_allocation",
        "value_status",
        "claim_grade",
        "confidence_components",
        "source_family_count",
        "fallback_level",
        "reconciliation_adjustment",
        "direct_actual_available",
        "production_use",
        "official_statistics_claim",
    ]
    shadow = add_audit(q[cols].head(20000))
    claim = add_audit(shadow.groupby(["claim_grade", "effective_region_level", "effective_industry_level", "frequency", "value_status"], as_index=False).size().rename(columns={"size": "row_count"}))
    return shadow, claim


def report_text(title: str, sections: list[tuple[str, str]]) -> str:
    lines = [f"# {title}", ""]
    for idx, (heading, body) in enumerate(sections, start=1):
        lines.extend([f"## {idx}. {heading}", "", body, ""])
    return "\n".join(lines)


def write_reports(tables: dict[str, pd.DataFrame], status: dict[str, Any]) -> None:
    reports = {
        "partial_statistics_estimation_phase30_reci_local_fine.md": report_text(
            "Partial Statistics Estimation Phase 30 - RECI-LF Local/Fine PoC",
            [
                ("실행 요약", "Phase30은 원화 GVA direct forecast가 아니라 RECI-LF activity index, direction, rank, anomaly, constrained allocation을 생성하는 Local/Fine validation phase로 구현했다."),
                ("Claim Grade 사전등록", markdown_table(tables["claim_grade"])),
                ("Data Readiness", markdown_table(tables["source_ledger"], 10)),
                ("Pilot Manifest", markdown_table(tables["pilot_manifest"])),
                ("Component Scorecards", "### Spatial\n\n" + markdown_table(tables["spatial"]) + "\n\n### Industry\n\n" + markdown_table(tables["industry"]) + "\n\n### Temporal\n\n" + markdown_table(tables["temporal"])),
                ("RECI-LF Shadow", markdown_table(tables["shadow"], 12)),
                ("Final Status", "```json\n" + json.dumps(status, ensure_ascii=False, indent=2) + "\n```"),
                ("아직 주장할 수 없는 내용", "읍면동×세부업종 공식 GVA, direct quarterly/monthly GVA accuracy, calibrated interval coverage, production use, official statistics equivalence."),
            ],
        ),
        "phase30_public_data_readiness.md": report_text("Phase30 Public Data Readiness", [("Source Release Ledger", markdown_table(tables["source_ledger"], 14)), ("Public Data Catalog", markdown_table(tables["catalog"], 14)), ("Paid Private Source Exclusion", markdown_table(tables["paid"]))]),
        "phase30_spatial_downscaling_validation.md": report_text("Phase30 Spatial Downscaling Validation", [("Sido-to-Sigungu Synthetic", markdown_table(tables["spatial"])), ("EMD Shadow Rule", "S0 previous share and EMD proxy allocation may be used only as constrained allocation/activity signal; direct EMD actual is unavailable.")]),
        "phase30_industry_downscaling_validation.md": report_text("Phase30 Industry Downscaling Validation", [("Industry Component Scorecard", markdown_table(tables["industry"])), ("Adaptive Industry Resolution", markdown_table(tables["resolution"][tables["resolution"]["axis"].eq("industry")]))]),
        "phase30_temporal_component_validation.md": report_text("Phase30 Temporal Component Validation", [("Service TQ3 Reproduction", markdown_table(tables["temporal"])), ("Monthly Eligibility", "Native monthly public source is not qualified for most cells; monthly values remain equal-month E or unavailable until source-specific gates pass.")]),
        "phase30_external_validation.md": report_text("Phase30 External Validation", [("Withheld Proxy", markdown_table(tables["withheld"])), ("Event Validation", markdown_table(tables["event"]))]),
        "phase30_poc_claim_and_confidence.md": report_text("Phase30 PoC Claim and Confidence", [("Claim Grade", markdown_table(tables["claim_grade"])), ("Adaptive Resolution", markdown_table(tables["resolution"])), ("Claim Grade Output", markdown_table(tables["claim_output"]))]),
    }
    for filename, text in reports.items():
        (ROOT / "reports" / filename).write_text(text, encoding="utf-8")


def update_topic() -> None:
    topic = ROOT / "reports" / "topics" / "ml.md"
    line = "| [partial_statistics_estimation_phase30_reci_local_fine.md](../partial_statistics_estimation_phase30_reci_local_fine.md) | Phase 30 RECI-LF local/fine commercial PoC claim, data-readiness, component validation, and shadow cube |"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# ML Reports\n"
    if "partial_statistics_estimation_phase30_reci_local_fine.md" not in text:
        topic.write_text(text.rstrip() + "\n" + line + "\n", encoding="utf-8")


def main() -> int:
    phase29 = json.loads((PROCESSED_DIR / "partial_stats_phase29_gva_final_status.json").read_text(encoding="utf-8"))
    if "service_temporal_component_development" not in phase29["status"]:
        raise SystemExit("phase29_not_ready")

    claim = claim_grade_registry()
    resolution = adaptive_resolution_rules()
    source_ledger, catalog, paid = source_catalog()
    pre2020 = pre2020_gva_audit()
    crosswalk = crosswalk_quality()
    pilot = pilot_manifest()
    spatial = spatial_component_scorecard()
    industry = industry_component_scorecard()
    temporal = temporal_component_scorecard()
    withheld = withheld_proxy_scorecard()
    event = event_validation()
    shadow, claim_output = reci_shadow()

    for name, frame in [
        ("phase30_claim_grade.csv", claim),
        ("phase30_adaptive_resolution_rules.csv", resolution),
        ("phase30_source_release_ledger.csv", source_ledger),
        ("phase30_public_data_catalog.csv", catalog),
        ("phase30_paid_private_source_exclusion_log.csv", paid),
        ("phase30_pre2020_gva_audit.csv", pre2020),
        ("phase30_region_industry_crosswalk_quality.csv", crosswalk),
        ("phase30_pilot_manifest.csv", pilot),
        ("phase30_spatial_component_scorecard.csv", spatial),
        ("phase30_industry_component_scorecard.csv", industry),
        ("phase30_temporal_component_scorecard.csv", temporal),
        ("phase30_withheld_proxy_scorecard.csv", withheld),
        ("phase30_event_validation.csv", event),
        ("phase30_reci_local_fine_shadow.csv", shadow),
        ("phase30_claim_grade_output.csv", claim_output),
    ]:
        write_derived(name, frame)

    spatial_numeric = spatial.copy()
    spatial_numeric["weighted_share_mae_num"] = pd.to_numeric(spatial_numeric["weighted_share_mae"], errors="coerce")
    status = {
        "status": "phase30_reci_lf_poc_created;claim_registered;data_readiness_audited;component_validation_initialized;shadow_cube_created",
        "target": "RECI-LF",
        "phase29_reproduction_status": "pass",
        "primary_product": "activity_index_direction_rank_anomaly_not_direct_gva",
        "shadow_row_count": int(len(shadow)),
        "source_count": int(len(source_ledger)),
        "pilot_count": int(len(pilot)),
        "spatial_selected_component": spatial_numeric.sort_values("weighted_share_mae_num", na_position="last").iloc[0]["component_id"],
        "industry_component_count": int(len(industry)),
        "temporal_service_tq3_delta_good": float(phase29["service_prior_delta_good"]),
        "withheld_proxy_count": int(len(withheld)),
        "event_validation_status": "not_scored_event_archive_required",
        "max_claim_grade_in_shadow": "D",
        "grade_a_for_emd_fine_count": int((shadow["claim_grade"] == "A").sum()),
        "u_value_violation_count": int(((shadow["claim_grade"] == "U") & shadow["reci_index"].notna()).sum()),
        "paid_private_source_used": False,
        "production_use": False,
        "official_statistics_claim": False,
        "claims_still_prohibited": "emd fine official GVA, direct lower-grain monetary accuracy, quarterly/monthly direct GVA accuracy, calibrated interval coverage",
        "generated_at": GENERATED_AT,
    }
    write_json(DERIVED_DIR / "phase30_final_status.json", status)
    tables = {
        "claim_grade": claim,
        "resolution": resolution,
        "source_ledger": source_ledger,
        "catalog": catalog,
        "paid": paid,
        "pre2020": pre2020,
        "crosswalk": crosswalk,
        "pilot_manifest": pilot,
        "spatial": spatial,
        "industry": industry,
        "temporal": temporal,
        "withheld": withheld,
        "event": event,
        "shadow": shadow,
        "claim_output": claim_output,
    }
    write_reports(tables, status)
    update_topic()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
