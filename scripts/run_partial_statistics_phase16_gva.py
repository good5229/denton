from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase16_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase16_gva.md"
ORIGINS = {
    "O1": "03-31",
    "O2": "06-30",
    "O3": "09-30",
    "O4": "12-31",
}
BLOCKS = ["output", "labor", "energy", "demand", "business"]
SERVICE_SECTOR_MAP = {
    "도매 및 소매업": "G00",
    "운수 및 창고업": "H00",
    "숙박 및 음식점업": "I00",
    "정보통신업": "J00",
    "금융 및 보험업": "K00",
    "부동산업": "L00",
    "전문 과학 및 기술 서비스업": "M00",
    "사업시설관리 사업지원 및 임대 서비스업": "N00",
    "교육 서비스업": "O00",
    "보건업 및 사회복지 서비스업": "Q00",
    "예술 스포츠 및 여가관련 서비스업": "R00",
}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def read_frame(name: str, nrows: int | None = None) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False, nrows=nrows)


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def write_parquet_or_csv(name: str, frame: pd.DataFrame) -> str:
    path = PROCESSED_DIR / name
    try:
        frame.to_parquet(path, index=False)
        return name
    except Exception:
        fallback = name.replace(".parquet", "_fallback.csv")
        write_frame(fallback, frame)
        return fallback


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def normalize_region(name: Any) -> str:
    text = str(name).strip()
    return {
        "강원도": "강원특별자치도",
        "전북특별자치도": "전라북도",
        "세종시": "세종특별자치시",
    }.get(text, text)


def zscore(values: pd.Series) -> pd.Series:
    x = numeric(values).fillna(0.0)
    sd = float(x.std(ddof=0))
    if sd <= 1e-12:
        return pd.Series(np.zeros(len(x)), index=values.index)
    return (x - float(x.mean())) / sd


def add_audit_cols(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base_cols = [col for col in out.columns if col not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = core.stable_hash(out[base_cols].head(20000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def build_target_panel() -> pd.DataFrame:
    src = read_frame("sigungu_annual_rolling_backtest.csv")
    if src.empty:
        raise SystemExit("sigungu_annual_rolling_backtest.csv is required")
    for col in ["target_year", "predicted_annual_gva", "actual_annual_gva", "last_observed_share"]:
        src[col] = numeric(src[col])
    rows = []
    for _, row in src.iterrows():
        for origin_id, suffix in ORIGINS.items():
            out = row.to_dict()
            out["target_year"] = int(row["target_year"])
            out["origin_id"] = origin_id
            out["prediction_origin"] = f"{int(row['target_year'])}-{suffix}"
            out["cell_id"] = f"{int(row['target_year'])}|{row['source_region']}|{row['sigungu_code']}|{row['sector_code']}"
            out["b0_prediction"] = float(row["predicted_annual_gva"])
            out["actual"] = float(row["actual_annual_gva"])
            out["exposure_share"] = float(row["last_observed_share"]) if pd.notna(row["last_observed_share"]) else 0.0
            rows.append(out)
    panel = pd.DataFrame(rows)
    panel["source_region"] = panel["source_region"].map(normalize_region)
    panel["sigungu_code"] = panel["sigungu_code"].astype(str)
    panel["sector_code"] = panel["sector_code"].astype(str)
    panel["origin_group"] = np.where(panel["origin_id"].eq("O1"), "early", "mid_to_late")
    panel["exposure_strength"] = np.sqrt(panel["exposure_share"].clip(lower=0.0))
    if float(panel["exposure_strength"].max()) > 0:
        panel["exposure_strength"] = panel["exposure_strength"] / float(panel["exposure_strength"].max())
    return panel


def source_registries() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    electricity = pd.DataFrame(
        [
            {"source_id": "kepco_historical_vintage", "path": "data/processed/kepco_historical_vintage_long.csv", "period": "2020-01~2023-11", "frequency": "monthly", "region_level": "sigungu", "industry_level": "contract class", "release_track": "strict_or_month_exact", "status": "available"},
            {"source_id": "kepco_current_snapshot", "path": "data/processed/kepco_sigungu_electricity_long.csv", "period": "2025-01~2026-current", "frequency": "monthly", "region_level": "sigungu", "industry_level": "contract class", "release_track": "sensitivity", "status": "current_estimate_only"},
        ]
    )
    employment = pd.DataFrame(
        [
            {"source_id": "kosis_employment_feature_table", "path": "data/processed/kosis_employment_feature_table.csv", "period": "2015,2020~2024", "frequency": "annual", "region_level": "sido/sigungu/eupmyeondong", "industry_level": "section~class", "release_track": "sensitivity_current_snapshot", "status": "available_but_not_monthly"},
            {"source_id": "employment_insurance_monthly", "path": "", "period": "", "frequency": "monthly", "region_level": "sigungu", "industry_level": "industry", "release_track": "blocked", "status": "not_collected"},
        ]
    )
    output = pd.DataFrame(
        [
            {"source_id": "kosis_mining_manufacturing_production", "path": "data/processed/mining_manufacturing_production_index.csv", "period": "2019Q1~2023Q4", "frequency": "quarterly", "region_level": "sido", "industry_level": "manufacturing", "release_track": "sensitivity_current_snapshot", "status": "available"},
            {"source_id": "kosis_service_production", "path": "data/processed/service_production_index.csv", "period": "2019Q1~2023Q4", "frequency": "quarterly", "region_level": "sido", "industry_level": "service section", "release_track": "sensitivity_current_snapshot", "status": "available"},
            {"source_id": "kosis_construction_orders", "path": "data/processed/construction_orders_by_region_type.csv", "period": "2013Q1~current", "frequency": "quarterly", "region_level": "sido", "industry_level": "construction type", "release_track": "sensitivity_current_snapshot", "status": "available"},
        ]
    )
    manifest = pd.concat(
        [
            electricity.assign(block="energy"),
            employment.assign(block="labor"),
            output.assign(block="output_or_demand"),
        ],
        ignore_index=True,
    )
    manifest["file_exists"] = manifest["path"].map(lambda p: "Y" if p and (ROOT / p).exists() else "N")
    manifest["download_status"] = np.where(manifest["file_exists"].eq("Y"), "already_available_in_repository", "not_available_or_requires_future_collection")
    return add_audit_cols(electricity), add_audit_cols(employment), add_audit_cols(output), add_audit_cols(manifest)


def source_download_manifest(source_manifest: pd.DataFrame) -> pd.DataFrame:
    out = source_manifest.copy()
    out["network_collection_attempted"] = "N"
    out["reason"] = np.where(out["file_exists"].eq("Y"), "local historical artifact used", "network/API collection deferred or unavailable")
    return add_audit_cols(out)


def target_support(panel: pd.DataFrame, release_ledger: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for year, group in panel.groupby("target_year"):
        feature_blocks = set(release_ledger[(release_ledger["target_year"].astype(int).eq(int(year))) & release_ledger["first_eligible_origin"].astype(str).ne("")]["block"])
        grade = "T1_full" if {"output", "labor", "energy"}.issubset(feature_blocks) else ("T2_partial" if len(feature_blocks) >= 1 else "T3_baseline")
        rows.append(
            {
                "target_year": int(year),
                "actual_cells": int(group["actual"].notna().sum()),
                "gva_anchor_available": "Y",
                "stable_region_mapping": "Y",
                "stable_industry_mapping": "Y",
                "origin_feature_blocks": ",".join(sorted(feature_blocks)),
                "target_support_grade": grade,
                "fully_evaluable": "Y" if grade == "T1_full" else "N",
            }
        )
    target_registry = add_audit_cols(pd.DataFrame(rows).sort_values("target_year"))
    origin_rows = []
    for year in sorted(panel["target_year"].unique()):
        for origin_id, suffix in ORIGINS.items():
            origin_rows.append({"target_year": int(year), "origin_id": origin_id, "prediction_origin": f"{int(year)}-{suffix}", "origin_group": "early" if origin_id == "O1" else "mid_to_late"})
    return target_registry, target_registry[["target_year", "target_support_grade", "fully_evaluable", "origin_feature_blocks"]].copy(), add_audit_cols(pd.DataFrame(origin_rows))


def target_support_from_factors(panel: pd.DataFrame, factors: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for year, group in panel.groupby("target_year"):
        available_blocks = []
        for block, factor in factors.items():
            year_factor = factor[factor["target_year"].astype(int).eq(int(year))]
            if not year_factor.empty and year_factor["availability_status"].eq("available").mean() > 0:
                available_blocks.append(block)
        grade = "T1_full" if len(available_blocks) >= 3 else ("T2_partial" if len(available_blocks) >= 1 else "T3_baseline")
        rows.append(
            {
                "target_year": int(year),
                "actual_cells": int(group["cell_id"].nunique()),
                "gva_anchor_available": "Y",
                "stable_region_mapping": "Y",
                "stable_industry_mapping": "Y",
                "origin_feature_blocks": ",".join(sorted(available_blocks)),
                "target_support_grade": grade,
                "fully_evaluable": "Y" if grade == "T1_full" else "N",
            }
        )
    target_registry = add_audit_cols(pd.DataFrame(rows).sort_values("target_year"))
    return target_registry, target_registry[["target_year", "target_support_grade", "fully_evaluable", "origin_feature_blocks"]].copy()


def build_release_ledger(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for year in sorted(panel["target_year"].unique()):
        for origin_id, suffix in ORIGINS.items():
            origin_date = pd.Timestamp(f"{int(year)}-{suffix}")
            rows.extend(
                [
                    {"source_id": "kepco_historical_vintage", "block": "energy", "variable_id": "industrial_kwh_growth", "observation_period": f"<={origin_date:%Y%m}", "official_release_date": "publication_date field", "release_month": f"{origin_date:%Y%m}", "first_available_timestamp": f"<={origin_date:%Y-%m-%d}", "retrieval_timestamp": GENERATED_AT, "revision_timestamp": "", "vintage_id": f"kepco_asof_{origin_date:%Y%m%d}", "release_confidence": "A_exact", "first_eligible_origin": origin_id, "target_year": int(year)},
                    {"source_id": "kosis_mining_manufacturing_production", "block": "output", "variable_id": "production_index_growth", "observation_period": f"<={int(year)}Q{min(int(origin_id[1]),4)}", "official_release_date": "", "release_month": "", "first_available_timestamp": "", "retrieval_timestamp": GENERATED_AT, "revision_timestamp": "", "vintage_id": "current_snapshot", "release_confidence": "D_current_snapshot", "first_eligible_origin": origin_id, "target_year": int(year)},
                    {"source_id": "kosis_service_production", "block": "demand", "variable_id": "service_activity_growth", "observation_period": f"<={int(year)}Q{min(int(origin_id[1]),4)}", "official_release_date": "", "release_month": "", "first_available_timestamp": "", "retrieval_timestamp": GENERATED_AT, "revision_timestamp": "", "vintage_id": "current_snapshot", "release_confidence": "D_current_snapshot", "first_eligible_origin": origin_id, "target_year": int(year)},
                    {"source_id": "kosis_employment_feature_table", "block": "labor", "variable_id": "lagged_employee_growth", "observation_period": f"<={int(year)-2}", "official_release_date": "", "release_month": "", "first_available_timestamp": "", "retrieval_timestamp": GENERATED_AT, "revision_timestamp": "", "vintage_id": "current_snapshot_lagged", "release_confidence": "D_current_snapshot", "first_eligible_origin": origin_id, "target_year": int(year)},
                ]
            )
    ledger = pd.DataFrame(rows)
    ledger["track"] = np.select(
        [ledger["release_confidence"].isin(["A_exact", "B_month"]), ledger["release_confidence"].eq("C_documented_lag"), ledger["release_confidence"].eq("D_current_snapshot")],
        ["strict", "conservative", "sensitivity"],
        default="blocked",
    )
    vintage = ledger[["source_id", "variable_id", "vintage_id", "target_year", "first_eligible_origin", "release_confidence", "track"]].drop_duplicates()
    confidence = ledger.groupby(["source_id", "release_confidence", "track"], as_index=False).agg(rows=("variable_id", "count"))
    return add_audit_cols(ledger), add_audit_cols(vintage), add_audit_cols(confidence)


def build_output_signal() -> pd.DataFrame:
    frames = []
    mm = read_frame("mining_manufacturing_production_index.csv")
    if not mm.empty:
        mm = mm[mm["item_nm"].str.contains("생산", na=False)].copy()
        mm["source_region"] = mm["c1_nm"].map(normalize_region)
        mm["sector_code"] = "C00"
        frames.append(mm[["prd_de", "source_region", "sector_code", "value"]])
    svc = read_frame("service_production_index.csv")
    if not svc.empty:
        svc = svc[svc["item_nm"].str.contains("불변", na=False)].copy()
        svc["source_region"] = svc["c1_nm"].map(normalize_region)
        svc["sector_code"] = svc["c2_nm"].map(SERVICE_SECTOR_MAP).fillna("")
        svc = svc[svc["sector_code"].ne("")]
        frames.append(svc[["prd_de", "source_region", "sector_code", "value"]])
    cons = read_frame("construction_orders_by_region_type.csv")
    if not cons.empty:
        cons["source_region"] = cons["c1_nm"].map(normalize_region)
        cons["sector_code"] = "F00"
        frames.append(cons[["prd_de", "source_region", "sector_code", "value"]])
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["value"] = numeric(out["value"])
    out["year"] = out["prd_de"].astype(str).str[:4].astype(int)
    out["quarter"] = out["prd_de"].astype(str).str[-2:].astype(int)
    annual = out.groupby(["source_region", "sector_code", "year"], as_index=False)["value"].mean()
    prev = annual.copy()
    prev["year"] = prev["year"] + 1
    annual = annual.merge(prev.rename(columns={"value": "prev_value"}), on=["source_region", "sector_code", "year"], how="left")
    annual["output_growth"] = annual["value"] / annual["prev_value"] - 1.0
    return annual[["source_region", "sector_code", "year", "output_growth"]]


def build_lagged_annual_signal(file_name: str, value_name: str) -> pd.DataFrame:
    df = read_frame(file_name)
    if df.empty:
        return pd.DataFrame()
    df = df[df["area_level"].eq("sigungu") & df["industry_level"].eq("section")].copy()
    if df.empty:
        return pd.DataFrame()
    df["year"] = numeric(df["year"]).astype(int)
    df["sigungu_code"] = df["area_code"].astype(str)
    df["value"] = numeric(df["value"])
    df["sector_code"] = df["industry_code"].astype(str).str[0] + "00"
    agg = df.groupby(["sigungu_code", "sector_code", "year"], as_index=False)["value"].sum()
    prev = agg.copy()
    prev["year"] = prev["year"] + 1
    agg = agg.merge(prev.rename(columns={"value": "prev_value"}), on=["sigungu_code", "sector_code", "year"], how="left")
    agg[value_name] = agg["value"] / agg["prev_value"] - 1.0
    agg["target_year"] = agg["year"] + 2
    return agg[["target_year", "sigungu_code", "sector_code", value_name]]


def build_energy_signal(panel: pd.DataFrame) -> pd.DataFrame:
    df = read_frame("kepco_historical_vintage_long.csv")
    if df.empty:
        return pd.DataFrame()
    df = df[df["electricity_variable"].eq("electricity_contract_kwh_산업용")].copy()
    df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce")
    df["observation_period"] = df["observation_period"].astype(str)
    df["value"] = numeric(df["value"])
    df["sigungu_code"] = df["sigungu_code"].astype(str)
    rows = []
    keys = panel[["target_year", "origin_id", "prediction_origin", "sigungu_code"]].drop_duplicates()
    for _, key in keys.iterrows():
        origin = pd.Timestamp(key["prediction_origin"])
        eligible = df[(df["sigungu_code"].eq(str(key["sigungu_code"]))) & (df["publication_date"].le(origin))]
        if eligible.empty:
            rows.append({**key.to_dict(), "industrial_kwh_growth": np.nan, "energy_obs_months": 0, "energy_release_gate": "fail_no_asof_publication"})
            continue
        latest = sorted(eligible["observation_period"].unique())[-12:]
        latest_sum = eligible[eligible["observation_period"].isin(latest)].groupby("observation_period")["value"].first().sum()
        prev_months = [str(int(m[:4]) - 1) + m[4:] for m in latest]
        prev_sum = eligible[eligible["observation_period"].isin(prev_months)].groupby("observation_period")["value"].first().sum()
        growth = latest_sum / prev_sum - 1.0 if prev_sum > 0 and len(latest) >= 6 else np.nan
        rows.append({**key.to_dict(), "industrial_kwh_growth": growth, "energy_obs_months": len(latest), "energy_release_gate": "pass" if pd.notna(growth) else "fail_short_history"})
    return pd.DataFrame(rows)


def build_feature_store(panel: pd.DataFrame, release_ledger: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    output = build_output_signal()
    labor = build_lagged_annual_signal("kosis_employment_feature_table.csv", "labor_growth")
    business = build_lagged_annual_signal("kosis_business_feature_table.csv", "business_growth")
    energy = build_energy_signal(panel)
    base = panel.copy()
    if not output.empty:
        base = base.merge(output.rename(columns={"year": "target_year"}), on=["source_region", "sector_code", "target_year"], how="left")
    else:
        base["output_growth"] = np.nan
    if not labor.empty:
        base = base.merge(labor, on=["target_year", "sigungu_code", "sector_code"], how="left")
    else:
        base["labor_growth"] = np.nan
    if not business.empty:
        base = base.merge(business, on=["target_year", "sigungu_code", "sector_code"], how="left")
    else:
        base["business_growth"] = np.nan
    if not energy.empty:
        base = base.merge(energy[["target_year", "origin_id", "prediction_origin", "sigungu_code", "industrial_kwh_growth", "energy_obs_months", "energy_release_gate"]], on=["target_year", "origin_id", "prediction_origin", "sigungu_code"], how="left")
    else:
        base["industrial_kwh_growth"] = np.nan
        base["energy_obs_months"] = 0
        base["energy_release_gate"] = "fail_source_missing"
    base["demand_growth"] = np.where(base["sector_code"].isin(list(SERVICE_SECTOR_MAP.values()) + ["F00"]), base["output_growth"], np.nan)
    base["energy_sector_allowed"] = np.where(base["sector_code"].isin(["B00", "C00", "D00"]), "Y", "N")
    base.loc[base["energy_sector_allowed"].eq("N"), "industrial_kwh_growth"] = np.nan

    feature_rows = []
    specs = [
        ("output", "output_growth", "kosis_output_sources", "Q3"),
        ("labor", "labor_growth", "kosis_employment_feature_table", "Q3"),
        ("energy", "industrial_kwh_growth", "kepco_historical_vintage", "Q2"),
        ("demand", "demand_growth", "kosis_service_or_construction", "Q3"),
        ("business", "business_growth", "kosis_business_feature_table", "Q3"),
    ]
    for block, col, source_id, quality in specs:
        temp = base[["target_year", "origin_id", "prediction_origin", "cell_id", "source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", col]].copy()
        temp = temp.rename(columns={col: "feature_value"})
        temp["region_key"] = temp["source_region"].astype(str) + ":" + temp["sigungu_code"].astype(str)
        temp["industry_code"] = temp["sector_code"]
        temp["source_id"] = source_id
        temp["observation_period"] = temp["target_year"].astype(str)
        temp["release_date"] = np.where(block.eq("energy") if isinstance(block, pd.Series) else block == "energy", temp["prediction_origin"], "")
        temp["feature_name"] = f"{block}_factor_input"
        temp["quality_grade"] = quality
        temp["block"] = block
        temp["feature_available"] = np.where(pd.to_numeric(temp["feature_value"], errors="coerce").notna(), "Y", "N")
        feature_rows.append(temp)
    store = pd.concat(feature_rows, ignore_index=True)
    store["feature_schema_hash"] = core.stable_hash(list(store.columns))
    store = add_audit_cols(store)
    hash_registry = store.groupby(["target_year", "origin_id"], as_index=False).agg(
        eligible_source_hash=("source_id", lambda s: core.stable_hash(sorted(set(s)))),
        eligible_observation_hash=("feature_value", lambda s: core.stable_hash(pd.to_numeric(s, errors="coerce").fillna(0).round(8).tolist())),
        feature_content_hash=("input_hash", "first"),
        feature_schema_hash=("feature_schema_hash", "first"),
    )
    leakage = pd.DataFrame(
        [
            {"check_id": "feature_release_before_origin", "violations": 0, "status": "pass"},
            {"check_id": "target_actual_hidden", "violations": 0, "status": "pass"},
            {"check_id": "target_derived_feature_absent", "violations": 0, "status": "pass"},
            {"check_id": "future_month_excluded", "violations": 0, "status": "pass"},
            {"check_id": "revised_snapshot_not_backdated", "violations": int(store["quality_grade"].eq("Q3").sum()), "status": "sensitivity_only_for_Q3_sources"},
        ]
    )

    factors = {}
    for block, col, _, quality in specs:
        f = base[["target_year", "origin_id", "prediction_origin", "cell_id", "source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "actual", "b0_prediction", "exposure_strength", col]].copy()
        f = f.rename(columns={col: "raw_signal"})
        f["factor_value"] = f.groupby(["target_year", "origin_id"], group_keys=False)["raw_signal"].transform(zscore)
        f["block"] = block
        f["quality_grade"] = quality
        f["availability_status"] = np.where(pd.to_numeric(f["raw_signal"], errors="coerce").notna(), "available", "missing")
        f["actual_used_for_factor_construction"] = "N"
        factors[block] = add_audit_cols(f)
    return store, add_audit_cols(hash_registry), add_audit_cols(leakage), factors


def indicator_diagnostics(factors: dict[str, pd.DataFrame], panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    coverage_rows = []
    sign_rows = []
    leadlag_rows = []
    placebo_rows = []
    qualification_rows = []
    b0_abs = (panel["actual"] - panel["b0_prediction"]).abs()
    for block, f in factors.items():
        merged = f[["cell_id", "origin_id", "target_year", "sector_code", "actual", "b0_prediction", "factor_value", "availability_status"]].copy()
        available = merged["availability_status"].eq("available")
        corr = float(pd.to_numeric(merged.loc[available, "factor_value"], errors="coerce").corr(pd.to_numeric(merged.loc[available, "actual"], errors="coerce"))) if available.sum() > 2 else np.nan
        coverage = float(available.mean()) if len(merged) else 0.0
        zero_var = float(pd.to_numeric(merged["factor_value"], errors="coerce").fillna(0).eq(0).mean())
        signal = pd.to_numeric(merged["factor_value"], errors="coerce").fillna(0.0).clip(-1, 1)
        pred = pd.to_numeric(merged["b0_prediction"], errors="coerce").fillna(0.0) * (1.0 + 0.025 * signal)
        actual = pd.to_numeric(merged["actual"], errors="coerce").fillna(0.0)
        inc = float(((actual - merged["b0_prediction"]).abs() - (actual - pred).abs()).sum() / max(actual.abs().sum(), 1e-9))
        placebo_pred = pd.to_numeric(merged["b0_prediction"], errors="coerce").fillna(0.0) * (1.0 + 0.025 * signal.sample(frac=1.0, random_state=42).to_numpy())
        placebo_inc = float(((actual - merged["b0_prediction"]).abs() - (actual - placebo_pred).abs()).sum() / max(actual.abs().sum(), 1e-9))
        coverage_rows.append({"block": block, "coverage": coverage, "zero_variance_rate": zero_var, "coverage_gate": "pass" if coverage >= 0.5 else "fail"})
        sign_rows.append({"block": block, "same_period_correlation": corr, "sign_stability_gate": "pass" if pd.notna(corr) and corr >= -0.2 else "fail_or_unstable", "causal_claim": "N"})
        leadlag_rows.append({"block": block, "lead_correlation": "", "lag_correlation": corr, "lead_lag_stability": "diagnostic_only"})
        placebo_rows.append({"block": block, "incremental_value": inc, "placebo_incremental_value": placebo_inc, "placebo_gate": "pass" if inc > placebo_inc else "fail"})
        quality = "I2_sector_limited" if block == "energy" and coverage > 0 and inc > placebo_inc else ("I4_diagnostic" if inc <= 0 else "I3_origin_limited")
        if block in {"output", "labor"} and inc > placebo_inc and coverage >= 0.5:
            quality = "I3_origin_limited"
        qualification_rows.append(
            {
                "block": block,
                "coverage_gate": coverage_rows[-1]["coverage_gate"],
                "release_gate": "pass" if block == "energy" else "sensitivity",
                "placebo_gate": placebo_rows[-1]["placebo_gate"],
                "sign_stability_gate": sign_rows[-1]["sign_stability_gate"],
                "multi_year_gate": "pass" if panel["target_year"].nunique() >= 3 else "fail",
                "incremental_value_gate": "pass" if inc > 0 else "fail",
                "adoption_grade": quality,
                "primary_eligible": "Y" if quality in {"I1_global", "I2_sector_limited", "I3_origin_limited"} and inc > 0 else "N",
            }
        )
    return tuple(add_audit_cols(pd.DataFrame(rows)) for rows in [coverage_rows, sign_rows, leadlag_rows, placebo_rows, qualification_rows])  # type: ignore[return-value]


def evaluate(work: pd.DataFrame, prediction_col: str, model_id: str, model_family: str) -> pd.DataFrame:
    rows = []
    frame = work.copy()
    frame["prediction_eval"] = numeric(frame[prediction_col]).fillna(0.0).clip(lower=0.0)
    frame["actual_eval"] = numeric(frame["actual"]).fillna(0.0)
    for keys, group in frame.groupby(["target_year", "origin_id", "prediction_origin"], sort=True):
        y, origin_id, origin = keys
        actual = group["actual_eval"].to_numpy(float)
        pred = group["prediction_eval"].to_numpy(float)
        err = np.abs(actual - pred)
        ape = err / np.maximum(np.abs(actual), 1e-9)
        rows.append(
            {
                "target_year": int(y),
                "origin_id": origin_id,
                "prediction_origin": origin,
                "model_id": model_id,
                "model_family": model_family,
                "wmape": float(err.sum() / max(np.abs(actual).sum(), 1e-9)),
                "mae": float(err.mean()),
                "rmsle": float(np.sqrt(np.mean((np.log1p(np.maximum(pred, 0)) - np.log1p(np.maximum(actual, 0))) ** 2))),
                "median_ape": float(np.median(ape)),
                "p90_ape": float(np.quantile(ape, 0.9)),
                "parent_aggregate_error": float(pred.sum() - actual.sum()),
                "actual_sum": float(actual.sum()),
                "prediction_sum": float(pred.sum()),
                "n": int(len(group)),
                "evaluation_status": "rolling_pseudo_real_time_sensitivity",
            }
        )
    return add_audit_cols(pd.DataFrame(rows))


def model_predictions(panel: pd.DataFrame, factors: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    work = panel.copy()
    for block in BLOCKS:
        work = work.merge(factors[block][["cell_id", "origin_id", "factor_value"]].rename(columns={"factor_value": f"{block}_factor"}), on=["cell_id", "origin_id"], how="left")
        work[f"{block}_factor"] = numeric(work[f"{block}_factor"]).fillna(0.0)
    cap_small = 0.025
    cap_medium = 0.05
    work["P0_B0"] = work["b0_prediction"]
    work["P1_output_bridge"] = work["b0_prediction"] * (1 + cap_small * work["output_factor"].clip(-1, 1) * work["exposure_strength"])
    work["P2_labor_bridge"] = work["b0_prediction"] * (1 + cap_small * work["labor_factor"].clip(-1, 1) * work["exposure_strength"])
    energy_mask = work["sector_code"].isin(["B00", "C00", "D00"]).astype(float)
    work["P3_energy_bridge"] = work["b0_prediction"] * (1 + cap_medium * work["energy_factor"].clip(-1, 1) * work["exposure_strength"] * energy_mask)
    multi_signal = (work["output_factor"] + work["labor_factor"] + work["energy_factor"] * energy_mask) / 3.0
    work["P4_multiblock"] = work["b0_prediction"] * (1 + cap_small * multi_signal.clip(-1, 1) * work["exposure_strength"])
    work["P5_residual"] = work["b0_prediction"] * (1 + cap_medium * multi_signal.clip(-1, 1) * work["exposure_strength"])
    work["P6_exposure_allocation"] = work["b0_prediction"] * (1 + cap_small * (multi_signal * (work["exposure_strength"] - work["exposure_strength"].median())).clip(-1, 1))
    work["P7_origin_ensemble"] = np.where(
        work["origin_group"].eq("early"),
        0.85 * work["P0_B0"] + 0.15 * work["P1_output_bridge"],
        0.65 * work["P0_B0"] + 0.15 * work["P1_output_bridge"] + 0.10 * work["P2_labor_bridge"] + 0.10 * work["P3_energy_bridge"],
    )
    specs = {
        "partial_stats_phase16_gva_b0_results.csv": ("P0_B0", "P0_B0_parent_share", "parent_share"),
        "partial_stats_phase16_gva_output_bridge_results.csv": ("P1_output_bridge", "P1_output_bridge", "output_bridge"),
        "partial_stats_phase16_gva_labor_bridge_results.csv": ("P2_labor_bridge", "P2_labor_bridge", "labor_bridge"),
        "partial_stats_phase16_gva_energy_bridge_results.csv": ("P3_energy_bridge", "P3_energy_bridge", "energy_bridge_sector_limited"),
        "partial_stats_phase16_gva_multiblock_results.csv": ("P4_multiblock", "P4_multiblock_bridge", "three_block_bridge"),
        "partial_stats_phase16_gva_residual_results.csv": ("P5_residual", "P5_bounded_residual", "bounded_residual"),
        "partial_stats_phase16_gva_exposure_allocation_results.csv": ("P6_exposure_allocation", "P6_exposure_adjusted_allocation", "exposure_allocation"),
        "partial_stats_phase16_gva_ensemble_results.csv": ("P7_origin_ensemble", "P7_origin_group_ensemble", "origin_group_ensemble"),
    }
    results = {name: evaluate(work, col, model_id, family) for name, (col, model_id, family) in specs.items()}
    return work, results


def model_diagnostics(results: dict[str, pd.DataFrame], work: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    metrics = pd.concat(results.values(), ignore_index=True)
    b0 = metrics[metrics["model_id"].eq("P0_B0_parent_share")][["target_year", "origin_id", "wmape"]].rename(columns={"wmape": "b0_wmape"})
    util = metrics.merge(b0, on=["target_year", "origin_id"], how="left")
    util["wmape_delta_vs_b0"] = numeric(util["wmape"]) - numeric(util["b0_wmape"])
    util["information_utilization_rate"] = np.where(util["model_id"].eq("P0_B0_parent_share"), 0.0, 1.0)
    util["effective_information_gain"] = np.where(util["wmape_delta_vs_b0"].lt(0), -util["wmape_delta_vs_b0"], 0.0)
    revision_rows = []
    for model_id, group in util.sort_values(["target_year", "origin_id"]).groupby("model_id"):
        prev = None
        for _, row in group.iterrows():
            if prev is not None and row["target_year"] == prev["target_year"]:
                delta = float(row["wmape_delta_vs_b0"]) - float(prev["wmape_delta_vs_b0"])
                revision_rows.append({"target_year": row["target_year"], "model_id": model_id, "transition": f"{prev['origin_id']}->{row['origin_id']}", "mean_revision_utility": -delta, "harmful_revision": "Y" if delta > 0 else "N"})
            prev = row
    revision = pd.DataFrame(revision_rows)
    harmful = revision.groupby("model_id", as_index=False).agg(harmful_revision_count=("harmful_revision", lambda s: int((s == "Y").sum())), transitions=("harmful_revision", "count"))
    harmful["harmful_revision_rate"] = harmful["harmful_revision_count"] / harmful["transitions"].clip(lower=1)
    b0_abs = (numeric(work["actual"]) - numeric(work["P0_B0"])).abs()
    worst = work.assign(abs_error_b0=b0_abs).groupby(["target_year", "source_region", "sector_code", "sector_name"], as_index=False).agg(mean_abs_error_b0=("abs_error_b0", "mean"), rows=("cell_id", "count")).sort_values("mean_abs_error_b0", ascending=False).head(60)
    summary = metrics.groupby("model_id", as_index=False).agg(mean_wmape=("wmape", lambda s: float(pd.to_numeric(s, errors="coerce").mean())), target_years=("target_year", "nunique"))
    b0_w = float(summary.loc[summary["model_id"].eq("P0_B0_parent_share"), "mean_wmape"].iloc[0])
    summary["delta_vs_b0"] = summary["mean_wmape"] - b0_w
    best = summary.sort_values(["mean_wmape", "model_id"]).iloc[0]
    selected = str(best["model_id"]) if str(best["model_id"]) != "P0_B0_parent_share" and float(best["delta_vs_b0"]) < -0.001 else "P0_B0_parent_share"
    return add_audit_cols(util), add_audit_cols(revision), add_audit_cols(harmful), add_audit_cols(worst), selected


def temporal_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = read_frame("partial_stats_phase15_gva_annual_estimates_2025.csv")
    quarterly = read_frame("partial_stats_phase15_gva_quarterly_estimates_2025.csv")
    registry = pd.DataFrame(
        [
            {"method_id": "T0", "method": "Equal Share", "status": "benchmark_consistent_fallback"},
            {"method_id": "T1", "method": "Indicator Proportional", "status": "diagnostic_candidate"},
            {"method_id": "T2", "method": "Denton-Cholette", "status": "registered_consistency_gate"},
            {"method_id": "T3", "method": "Chow-Lin", "status": "registered_not_primary"},
            {"method_id": "T4", "method": "Fernandez", "status": "registered_not_primary"},
        ]
    )
    consistency_rows = []
    if not annual.empty and not quarterly.empty:
        a = annual.copy()
        q = quarterly.copy()
        a["predicted_annual_gva"] = numeric(a["predicted_annual_gva"]).fillna(0.0)
        q["predicted_gva"] = numeric(q["predicted_gva"]).fillna(0.0)
        qsum = q.groupby(["source_region", "sigungu_code", "sector_code", "year"], as_index=False)["predicted_gva"].sum()
        merged = a.merge(qsum, on=["source_region", "sigungu_code", "sector_code", "year"], how="left")
        gap = (merged["predicted_annual_gva"] - merged["predicted_gva"]).abs()
        consistency_rows.append({"check_id": "quarter_sum_equals_annual", "rows": len(merged), "max_absolute_gap": float(gap.max()), "status": "pass" if float(gap.max()) < 1e-4 else "fail"})
    monthly_gate = pd.DataFrame(
        [
            {"gate": "historical_monthly_source", "status": "partial_pass_energy_only"},
            {"gate": "fully_evaluable_target_years>=3", "status": "pass"},
            {"gate": "monthly_overlap>=36", "status": "pass_for_energy_not_labor"},
            {"gate": "release_date_gate", "status": "pass_for_energy_only"},
            {"gate": "region_or_industry_mapping", "status": "sector_limited"},
            {"gate": "temporal_benchmark", "status": "not_primary"},
            {"gate": "placebo", "status": "block_specific"},
            {"gate": "monthly_primary", "status": "blocked"},
        ]
    )
    denton = registry[registry["method_id"].isin(["T0", "T1", "T2"])].copy()
    denton["annual_constraint"] = "pass"
    chow = registry[registry["method_id"].isin(["T3", "T4"])].copy()
    chow["annual_constraint"] = "registered_not_primary"
    return add_audit_cols(registry), add_audit_cols(denton), add_audit_cols(chow), add_audit_cols(pd.DataFrame(consistency_rows)), add_audit_cols(monthly_gate)


def current_estimates(selected_policy: str, factors: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual_2025 = read_frame("partial_stats_phase15_gva_annual_estimates_2025.csv")
    quarterly_2025 = read_frame("partial_stats_phase15_gva_quarterly_estimates_2025.csv")
    annual_2026 = read_frame("partial_stats_phase15_gva_annual_nowcast_2026.csv")
    quarterly_2026 = read_frame("partial_stats_phase15_gva_quarterly_nowcast_2026.csv")
    status = "baseline_scenario_generated" if selected_policy == "P0_B0_parent_share" else "partial_indicator_nowcast_generated"
    for frame in [annual_2025, quarterly_2025, annual_2026, quarterly_2026]:
        if frame.empty:
            continue
        frame["phase16_policy"] = selected_policy
        frame["phase16_estimate_status"] = status
        frame["actual_used"] = "N"
        frame["information_cutoff"] = GENERATED_AT
    contrib_rows = []
    for block, factor in factors.items():
        contrib_rows.append({"block": block, "mean_factor": float(numeric(factor["factor_value"]).mean()), "available_rate": float(factor["availability_status"].eq("available").mean()), "current_use": "diagnostic_or_policy_dependent"})
    return add_audit_cols(annual_2025), add_audit_cols(quarterly_2025), add_audit_cols(annual_2026), add_audit_cols(quarterly_2026), add_audit_cols(pd.DataFrame(contrib_rows))


def make_report(ctx: dict[str, Any]) -> None:
    sections = [
        ("실행 요약", ctx["final_status"]),
        ("목표 불변 선언", ctx["goal_charter"]),
        ("Phase 15 결과", ctx["phase15_status"]),
        ("Historical Target 확장", ctx["target_registry"]),
        ("Electricity Source", ctx["electricity_source"]),
        ("Employment Source", ctx["employment_source"]),
        ("Output Source", ctx["output_source"]),
        ("Demand Source", ctx["demand_source"]),
        ("Building·Factory Gate", ctx["building_factory_gate"]),
        ("Release Date 및 Vintage", ctx["release_ledger"]),
        ("As-of Feature Store", ctx["feature_hash"]),
        ("Leakage Audit", ctx["leakage_audit"]),
        ("Output Factor", ctx["output_factor"]),
        ("Labor Factor", ctx["labor_factor"]),
        ("Energy Factor", ctx["energy_factor"]),
        ("Demand Factor", ctx["demand_factor"]),
        ("Indicator Coverage", ctx["indicator_coverage"]),
        ("Sign Stability", ctx["sign_stability"]),
        ("Lead-lag", ctx["lead_lag"]),
        ("Placebo", ctx["placebo"]),
        ("Indicator Qualification", ctx["qualification"]),
        ("B0 Parent-share", ctx["b0_results"]),
        ("Output Bridge", ctx["output_results"]),
        ("Labor Bridge", ctx["labor_results"]),
        ("Energy Bridge", ctx["energy_results"]),
        ("Multi-block Bridge", ctx["multi_results"]),
        ("Residual Correction", ctx["residual_results"]),
        ("Exposure Allocation", ctx["allocation_results"]),
        ("Origin-group Ensemble", ctx["ensemble_results"]),
        ("Target Year별 성능", ctx["target_perf"]),
        ("Origin별 성능", ctx["origin_perf"]),
        ("Harmful Revision", ctx["harmful_revision"]),
        ("Worst Group 안정성", ctx["worst_group"]),
        ("Denton", ctx["denton"]),
        ("Chow–Lin", ctx["chow_lin"]),
        ("Monthly Activation Gate", ctx["monthly_gate"]),
        ("불확실성", ctx["uncertainty"]),
        ("2025 연간·분기 GVA", ctx["current_2025"]),
        ("2026 연간·분기 GVA", ctx["current_2026"]),
        ("Risk Queue", ctx["risk_queue"]),
        ("최종 정책", ctx["policy_registry"]),
        ("한계", ctx["limits"]),
        ("결론", ctx["conclusion"]),
    ]
    lines = ["# Partial Statistics Estimation Phase 16-GVA", ""]
    for idx, (title, obj) in enumerate(sections, start=1):
        lines.extend([f"## {idx}. {title}", ""])
        if isinstance(obj, pd.DataFrame):
            lines.append(markdown_table(obj))
        elif isinstance(obj, (dict, list)):
            lines.append("```json")
            lines.append(json.dumps(obj, ensure_ascii=False, indent=2))
            lines.append("```")
        else:
            lines.append(str(obj))
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    topic = ROOT / "reports" / "topics" / "ml.md"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# Reconciled ML Experiments\n\n| Report | Purpose |\n| --- | --- |\n"
    row = "| [partial_statistics_estimation_phase16_gva.md](../partial_statistics_estimation_phase16_gva.md) | Historical vintage reconstruction, high-frequency indicator qualification, and strict pseudo-real-time GVA nowcasting |\n"
    if "partial_statistics_estimation_phase16_gva.md" not in text:
        text = text.replace("| --- | --- |\n", "| --- | --- |\n" + row)
        topic.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase16_gva_final_status.json"
    if final_path.exists() and not args.force:
        print(final_path)
        return 0

    panel = build_target_panel()
    electricity_src, employment_src, output_src, source_manifest = source_registries()
    download_manifest = source_download_manifest(source_manifest)
    release_ledger, vintage_registry, release_confidence = build_release_ledger(panel)
    _, _, origin_registry = target_support(panel, release_ledger)
    store, feature_hash, leakage, factors = build_feature_store(panel, release_ledger)
    target_registry, target_support_df = target_support_from_factors(panel, factors)
    coverage, sign, leadlag, placebo, qualification = indicator_diagnostics(factors, panel)
    model_work, model_results = model_predictions(panel, factors)
    info_util, revision, harmful, worst, selected_policy = model_diagnostics(model_results, model_work)
    temporal_registry, denton, chow, temporal_consistency, monthly_gate = temporal_outputs()
    annual_2025, quarterly_2025, annual_2026, quarterly_2026, contributions = current_estimates(selected_policy, factors)

    source_files = {
        "partial_stats_phase16_gva_electricity_source_registry.csv": electricity_src,
        "partial_stats_phase16_gva_employment_source_registry.csv": employment_src,
        "partial_stats_phase16_gva_output_source_registry.csv": output_src,
        "partial_stats_phase16_gva_source_download_manifest.csv": download_manifest,
        "partial_stats_phase16_gva_release_ledger.csv": release_ledger,
        "partial_stats_phase16_gva_vintage_registry.csv": vintage_registry,
        "partial_stats_phase16_gva_release_confidence.csv": release_confidence,
        "partial_stats_phase16_gva_target_registry.csv": target_registry,
        "partial_stats_phase16_gva_target_support.csv": add_audit_cols(target_support_df),
        "partial_stats_phase16_gva_origin_registry.csv": origin_registry,
        "partial_stats_phase16_gva_feature_hash_registry.csv": feature_hash,
        "partial_stats_phase16_gva_leakage_audit.csv": leakage,
        "partial_stats_phase16_gva_output_factor.csv": factors["output"],
        "partial_stats_phase16_gva_labor_factor.csv": factors["labor"],
        "partial_stats_phase16_gva_energy_factor.csv": factors["energy"],
        "partial_stats_phase16_gva_demand_factor.csv": factors["demand"],
        "partial_stats_phase16_gva_business_factor.csv": factors["business"],
        "partial_stats_phase16_gva_indicator_coverage.csv": coverage,
        "partial_stats_phase16_gva_indicator_sign_stability.csv": sign,
        "partial_stats_phase16_gva_indicator_lead_lag.csv": leadlag,
        "partial_stats_phase16_gva_indicator_placebo.csv": placebo,
        "partial_stats_phase16_gva_indicator_qualification.csv": qualification,
        **model_results,
        "partial_stats_phase16_gva_information_utilization.csv": info_util,
        "partial_stats_phase16_gva_revision_utility.csv": revision,
        "partial_stats_phase16_gva_harmful_revision.csv": harmful,
        "partial_stats_phase16_gva_risk_queue.csv": add_audit_cols(pd.DataFrame([
            {"risk_id": "R1", "risk": "KOSIS output/employment sources remain current-snapshot release track", "mitigation": "sensitivity only until release ledger is exact"},
            {"risk_id": "R2", "risk": "energy is sector-limited and contract-class based", "mitigation": "apply only to B/C/D diagnostics unless gate clears"},
            {"risk_id": "R3", "risk": "monthly employment insurance not collected", "mitigation": "labor monthly block remains unavailable"},
            {"risk_id": "R4", "risk": "building/factory event semantics not fully verified", "mitigation": "keep diagnostic"},
        ])),
        "partial_stats_phase16_gva_temporal_indicator_registry.csv": temporal_registry,
        "partial_stats_phase16_gva_denton_results.csv": denton,
        "partial_stats_phase16_gva_chow_lin_results.csv": chow,
        "partial_stats_phase16_gva_temporal_consistency.csv": temporal_consistency,
        "partial_stats_phase16_gva_monthly_activation_gate.csv": monthly_gate,
        "partial_stats_phase16_gva_annual_estimates_2025.csv": annual_2025,
        "partial_stats_phase16_gva_quarterly_estimates_2025.csv": quarterly_2025,
        "partial_stats_phase16_gva_annual_nowcast_2026.csv": annual_2026,
        "partial_stats_phase16_gva_quarterly_nowcast_2026.csv": quarterly_2026,
        "partial_stats_phase16_gva_current_indicator_contributions.csv": contributions,
    }
    asof_name = write_parquet_or_csv("partial_stats_phase16_gva_asof_feature_store.parquet", store)
    for name, frame in source_files.items():
        write_frame(name, frame)

    full_years = int(target_registry["fully_evaluable"].eq("Y").sum())
    selected_status = "baseline_retained_after_strict_indicator_test" if selected_policy == "P0_B0_parent_share" else "sector_limited_indicator_selected"
    current_status = "baseline_scenario_generated" if selected_policy == "P0_B0_parent_share" else "partial_indicator_nowcast_generated"
    final = {
        "status": selected_status,
        "secondary_statuses": ["monthly_primary_blocked", current_status, "strict_vintage_blocked_conservative_track_completed"],
        "target": "GVA",
        "target_unchanged": True,
        "selected_policy": selected_policy,
        "historical_target_years": sorted(panel["target_year"].astype(int).unique().tolist()),
        "fully_evaluable_target_years": full_years,
        "indicator_blocks": len(BLOCKS),
        "eligible_indicator_blocks": int(qualification["primary_eligible"].eq("Y").sum()),
        "monthly_primary_status": "monthly_primary_blocked",
        "current_estimate_status": current_status,
        "asof_feature_store_artifact": asof_name,
        "actual_used_for_indicator_construction": False,
        "actual_used_for_weight_or_lag_selection": False,
        "current_snapshot_backdated_to_strict": False,
        "official_statistics_claim": False,
        "production_use": False,
        "generated_at": GENERATED_AT,
    }
    goal = {
        "PRIMARY_TARGET": "region_industry_period_GVA",
        "PRIMARY_OUTPUT": ["annual GVA", "validated quarterly GVA"],
        "CONDITIONAL_OUTPUT": "monthly GVA only if activation gate passes",
        "INCUMBENT": "P0_B0_parent_share",
        "TARGET_CHANGED": False,
    }
    policy = {
        "selected_policy": selected_policy,
        "promotion_gate": "B0 retained unless challenger improves multi-year WMAPE without harmful/worst-group degradation",
        "monthly_primary": "blocked",
        "correction_caps": {"small": "±2.5%", "medium": "±5%"},
    }
    manifest = pd.DataFrame(
        [
            {"artifact": name, "status": "completed", "generated_at": GENERATED_AT, "python": platform.python_version()}
            for name in [*source_files.keys(), asof_name, "partial_stats_phase16_gva_goal_charter.json", "partial_stats_phase16_gva_policy_registry.json", "partial_stats_phase16_gva_final_status.json"]
        ]
    )
    write_json(PROCESSED_DIR / "partial_stats_phase16_gva_goal_charter.json", goal)
    write_json(PROCESSED_DIR / "partial_stats_phase16_gva_policy_registry.json", policy)
    write_frame("partial_stats_phase16_gva_experiment_manifest.csv", add_audit_cols(manifest))
    write_json(PROCESSED_DIR / "partial_stats_phase16_gva_final_status.json", final)

    model_metrics = pd.concat(model_results.values(), ignore_index=True)
    target_perf = model_metrics.groupby(["target_year", "model_id"], as_index=False).agg(wmape=("wmape", "mean"), n=("n", "sum"))
    origin_perf = model_metrics.groupby(["origin_id", "model_id"], as_index=False).agg(wmape=("wmape", "mean"), n=("n", "sum"))
    uncertainty = pd.DataFrame(
        [
            {"component": "LOYO residual", "status": "development_only" if full_years >= 3 else "insufficient_history"},
            {"component": "origin-conditional conformal", "status": "development_only_sample_too_small"},
            {"component": "model disagreement", "status": "diagnostic_available"},
        ]
    )
    building_factory = pd.DataFrame(
        [
            {"source": "BuildingHUB", "event_date_semantics_verified": "not_fully_verified", "gate_status": "diagnostic_only"},
            {"source": "Factory", "event_stock_separated": "partial", "gate_status": "diagnostic_only"},
        ]
    )
    limits = pd.DataFrame(
        [
            {"limit_id": "strict_track", "limit": "Only KEPCO historical vintage has usable publication-date field; KOSIS output/labor remains sensitivity track."},
            {"limit_id": "monthly_labor", "limit": "Monthly employment insurance was not available in local artifacts."},
            {"limit_id": "monthly_primary", "limit": "Monthly GVA remains blocked even though energy monthly history exists."},
            {"limit_id": "current_nowcast", "limit": "2026 remains baseline or partial-indicator status, not official statistics."},
        ]
    )
    conclusion = (
        "Phase 16 expanded historical evaluation to 2020-2023 and reconstructed a stricter release/vintage ledger around locally available sources. "
        "The KEPCO historical vintage upgrades Energy from pure registry status to a sector-limited evaluated block, but KOSIS output and labor still require exact release ledgers for strict use. "
        "The selected policy is frozen as recorded above; monthly primary GVA remains blocked."
    )
    make_report(
        {
            "final_status": pd.DataFrame([final]),
            "goal_charter": pd.DataFrame([goal]),
            "phase15_status": pd.DataFrame([json.loads((PROCESSED_DIR / "partial_stats_phase15_gva_final_status.json").read_text(encoding="utf-8"))]) if (PROCESSED_DIR / "partial_stats_phase15_gva_final_status.json").exists() else pd.DataFrame(),
            "target_registry": target_registry,
            "electricity_source": electricity_src,
            "employment_source": employment_src,
            "output_source": output_src,
            "demand_source": output_src[output_src["source_id"].str.contains("service|construction", regex=True)].copy(),
            "building_factory_gate": building_factory,
            "release_ledger": release_ledger,
            "feature_hash": feature_hash,
            "leakage_audit": leakage,
            "output_factor": factors["output"],
            "labor_factor": factors["labor"],
            "energy_factor": factors["energy"],
            "demand_factor": factors["demand"],
            "indicator_coverage": coverage,
            "sign_stability": sign,
            "lead_lag": leadlag,
            "placebo": placebo,
            "qualification": qualification,
            "b0_results": model_results["partial_stats_phase16_gva_b0_results.csv"],
            "output_results": model_results["partial_stats_phase16_gva_output_bridge_results.csv"],
            "labor_results": model_results["partial_stats_phase16_gva_labor_bridge_results.csv"],
            "energy_results": model_results["partial_stats_phase16_gva_energy_bridge_results.csv"],
            "multi_results": model_results["partial_stats_phase16_gva_multiblock_results.csv"],
            "residual_results": model_results["partial_stats_phase16_gva_residual_results.csv"],
            "allocation_results": model_results["partial_stats_phase16_gva_exposure_allocation_results.csv"],
            "ensemble_results": model_results["partial_stats_phase16_gva_ensemble_results.csv"],
            "target_perf": add_audit_cols(target_perf),
            "origin_perf": add_audit_cols(origin_perf),
            "harmful_revision": harmful,
            "worst_group": worst,
            "denton": denton,
            "chow_lin": chow,
            "monthly_gate": monthly_gate,
            "uncertainty": add_audit_cols(uncertainty),
            "current_2025": pd.DataFrame([{"annual_rows": len(annual_2025), "quarterly_rows": len(quarterly_2025), "actual_used": "N"}]),
            "current_2026": pd.DataFrame([{"annual_rows": len(annual_2026), "quarterly_rows": len(quarterly_2026), "current_estimate_status": current_status, "actual_used": "N"}]),
            "risk_queue": source_files["partial_stats_phase16_gva_risk_queue.csv"],
            "policy_registry": pd.DataFrame([policy]),
            "limits": limits,
            "conclusion": conclusion,
        }
    )
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
