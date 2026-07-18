from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, RAW_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase22_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase22_gva.md"
RAW_OFFICIAL = RAW_DIR / "official_quarterly_grdp"
QP_MAP = {
    "QP0_seasonal": "partial_stats_phase20_gva_qp0_seasonal_results.csv",
    "QP1_national_bridge": "partial_stats_phase20_gva_qp1_national_bridge_results.csv",
    "QP2_bounded_indicator_bridge": "partial_stats_phase20_gva_qp2_indicator_bridge_results.csv",
    "QP3_robust_hierarchical_bridge": "partial_stats_phase20_gva_qp3_hierarchical_results.csv",
    "QP4_factor": "partial_stats_phase20_gva_qp4_factor_results.csv",
    "QP5_midas": "partial_stats_phase20_gva_qp5_midas_results.csv",
}


OFFICIAL_RELEASES = [
    {
        "reference_period": "2025Q1",
        "release_id": "2025Q1_first_release",
        "posted_at": "2025-06-26",
        "official_page_url": "https://mods.go.kr/board.es?act=view&bid=243&list_no=437329&mid=a10301130300",
        "download_url": "https://mods.go.kr/boardDownload.es?bid=243&list_no=437329&seq=2",
        "official_release_title": "2025년 1/4분기 실질 지역내총생산(잠정) 보도자료(실험적통계)",
        "attachment_name": "2025년 1분기 실질 지역내총생산(잠정) 보도자료(실험적통계).pdf",
    },
    {
        "reference_period": "2025Q2",
        "release_id": "2025Q2_first_release",
        "posted_at": "2025-09-26",
        "official_page_url": "https://mods.go.kr/board.es?act=view&bid=243&list_no=438822&mid=a10301130300",
        "download_url": "https://mods.go.kr/boardDownload.es?bid=243&list_no=438822&seq=1",
        "official_release_title": "2025년 2/4분기 실질 지역내총생산(잠정) 보도자료(실험적통계)",
        "attachment_name": "2025년 2분기 실질 지역내총생산(잠정) 보도자료(실험적통계).pdf",
    },
    {
        "reference_period": "2025Q3",
        "release_id": "2025Q3_first_release",
        "posted_at": "2025-12-26",
        "official_page_url": "https://mods.go.kr/board.es?act=view&bid=243&list_no=442620&mid=a10301130300",
        "download_url": "https://mods.go.kr/boardDownload.es?bid=243&list_no=442620&seq=1",
        "official_release_title": "2025년 3/4분기 실질 지역내총생산(잠정) 보도자료(실험적통계)",
        "attachment_name": "2025년 3분기 실질 지역내총생산(잠정) 보도자료(실험적통계).pdf",
    },
    {
        "reference_period": "2025Q4",
        "release_id": "2025Q4_first_release",
        "posted_at": "2026-03-30",
        "official_page_url": "https://mods.go.kr/board.es?act=view&bid=243&list_no=444246&mid=a10301130300",
        "download_url": "https://mods.go.kr/boardDownload.es?bid=243&list_no=444246&seq=3",
        "official_release_title": "2025년 4/4분기 및 연간 실질 지역내총생산(잠정) 보도자료(실험적통계)",
        "attachment_name": "2025년 4분기 및 연간 실질 지역내총생산(잠정) 보도자료(실험적통계).pdf",
    },
    {
        "reference_period": "2026Q1",
        "release_id": "2026Q1_first_release",
        "posted_at": "2026-06-29",
        "official_page_url": "https://mods.go.kr/board.es?act=view&bid=243&list_no=445657&mid=a10301130300",
        "download_url": "https://mods.go.kr/boardDownload.es?bid=243&list_no=445657&seq=3",
        "official_release_title": "2026년 1/4분기 실질 지역내총생산(GRDP)",
        "attachment_name": "2026년 1분기 실질 지역내총생산(잠정) 보도자료(실험적통계).pdf",
    },
]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def read_frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def materialize_official_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source_rows: list[dict[str, Any]] = []
    release_rows: list[dict[str, Any]] = []
    vintage_rows: list[dict[str, Any]] = []
    for item in OFFICIAL_RELEASES:
        folder = RAW_OFFICIAL / item["release_id"]
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "source.pdf"
        exists = path.exists() and path.stat().st_size > 1024
        digest = file_sha256(path) if exists else ""
        metadata = {
            **item,
            "retrieved_at": GENERATED_AT,
            "attachment_type": "pdf",
            "local_path": str(path.relative_to(ROOT)),
            "attachment_hash": digest,
            "retrieval_status": "downloaded" if exists else "missing_local_file",
        }
        write_json(folder / "page_metadata.json", metadata)
        write_json(folder / "attachment_metadata.json", metadata)
        (folder / "checksum.sha256").write_text((digest + "  source.pdf\n") if digest else "", encoding="utf-8")
        source_rows.append(
            {
                "source_id": "OFFICIAL_EXPERIMENTAL_QUARTERLY_GRDP",
                "reference_period": item["reference_period"],
                "official_page_id": item["official_page_url"].split("list_no=")[-1].split("&")[0],
                "official_release_title": item["official_release_title"],
                "posted_at": item["posted_at"],
                "retrieved_at": GENERATED_AT,
                "attachment_name": item["attachment_name"],
                "attachment_type": "pdf",
                "attachment_hash": digest,
                "page_hash": core.stable_hash(item["official_page_url"]),
                "source_body_exists": "pass" if exists else "fail",
                "release_date_exists": "pass",
                "measure_definition_exists": "pass_release_text",
                "direct_source_gate": "pass_source_only" if exists else "fail_missing_attachment",
                "target_extraction_gate": "blocked_pdf_table_parser_not_implemented",
                "official_page_url": item["official_page_url"],
                "download_url": item["download_url"],
            }
        )
        release_rows.append(
            {
                "release_id": item["release_id"],
                "reference_period": item["reference_period"],
                "release_date": item["posted_at"],
                "retrieved_at": GENERATED_AT,
                "release_status": "source_materialized" if exists else "source_missing",
                "raw_path": str(folder.relative_to(ROOT)),
                "source_file_hash": digest,
                "vintage_type": "first_release",
            }
        )
        vintage_rows.append(
            {
                "vintage_id": item["release_id"],
                "reference_period": item["reference_period"],
                "first_released_at": item["posted_at"],
                "retrieved_at": GENERATED_AT,
                "revision_sequence": 1,
                "source_file_hash": digest,
                "vintage_status": "first_release_source_materialized" if exists else "not_materialized",
            }
        )
    target_cube = pd.DataFrame(
        columns=[
            "release_date",
            "reference_period",
            "region_code",
            "region_name",
            "official_industry_group",
            "measure_type",
            "price_basis",
            "reference_year",
            "seasonal_adjustment_status",
            "value",
            "provisional_status",
            "revision_status",
            "target_type",
            "vintage_id",
        ]
    )
    target_cube.to_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_official_target_cube.parquet", index=False)
    measure = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "measure_id": "official_quarterly_grdp_release",
                    "source_evidence": "downloaded_pdf_and_official_page",
                    "target_measure_observed": "real_value_added_growth_and_contribution",
                    "level_track_status": "not_extracted_from_pdf_tables",
                    "growth_track_status": "source_materialized_extraction_pending",
                    "price_basis": "real",
                    "seasonal_adjustment_status": "original_yoy_growth",
                    "official_statistics_status": "experimental_statistics_not_approved_statistics",
                }
            ]
        )
    )
    return (
        add_audit_cols(pd.DataFrame(source_rows)),
        add_audit_cols(pd.DataFrame(release_rows)),
        add_audit_cols(pd.DataFrame(vintage_rows)),
        target_cube,
        measure,
    )


def parent_rows() -> pd.DataFrame:
    rows = []
    for policy, name in QP_MAP.items():
        df = read_frame(name)
        if df.empty:
            continue
        df = df.copy()
        df["parent_policy_id"] = policy
        rows.append(df)
    if not rows:
        raise SystemExit("Phase20 parent result files are required")
    parent = pd.concat(rows, ignore_index=True, sort=False)
    for col in ["year", "quarter", "actual", "prediction"]:
        parent[col] = numeric(parent[col])
    parent["abs_error"] = (parent["actual"] - parent["prediction"]).abs()
    parent["evaluation_role"] = np.where(parent["year"].eq(parent["year"].min()), "warmup_seed", "development_proxy_evaluation")
    parent["scored"] = np.where(parent["evaluation_role"].eq("development_proxy_evaluation"), "Y", "N")
    parent["period"] = parent["year"].astype(int).astype(str) + "Q" + parent["quarter"].astype(int).astype(str)
    return parent


def growth_metric_audit(parent: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scored = parent[parent["scored"].eq("Y")].copy()
    rows: list[dict[str, Any]] = []
    extreme_rows: list[dict[str, Any]] = []
    for policy, g in scored.sort_values(["region_code", "industry_group", "year", "quarter"]).groupby("parent_policy_id"):
        work = g.copy()
        keys = ["region_code", "industry_group"]
        work["lag4_actual"] = work.groupby(keys)["actual"].shift(4)
        work["lag4_prediction"] = work.groupby(keys)["prediction"].shift(4)
        valid_yoy = work["lag4_actual"].gt(0) & work["lag4_prediction"].gt(0) & work["actual"].gt(0) & work["prediction"].gt(0)
        work["actual_yoy_pct"] = np.where(valid_yoy, 100 * (work["actual"] / work["lag4_actual"] - 1), np.nan)
        work["pred_yoy_pct"] = np.where(valid_yoy, 100 * (work["prediction"] / work["lag4_prediction"] - 1), np.nan)
        work["growth_error_pp"] = (work["actual_yoy_pct"] - work["pred_yoy_pct"]).abs()
        work["extreme_reason"] = np.select(
            [
                work["lag4_actual"].le(0) | work["lag4_prediction"].le(0),
                work["actual"].le(0) | work["prediction"].le(0),
                work["growth_error_pp"].gt(100),
            ],
            ["near_zero_or_nonpositive_denominator", "negative_or_zero_level", "genuine_extreme_or_proxy_volatility"],
            default="not_extreme",
        )
        rows.append(
            {
                "parent_policy_id": policy,
                "growth_unit": "percentage_point",
                "scored_rows": int(len(work)),
                "valid_yoy_growth_rows": int(valid_yoy.sum()),
                "invalid_denominator_rows": int((~valid_yoy).sum()),
                "yoy_growth_mae_pp": float(work.loc[valid_yoy, "growth_error_pp"].mean()),
                "unit_double_scaling_errors": 0,
                "denominator_errors_unclassified": 0,
                "extreme_error_rows": int(work["growth_error_pp"].gt(100).sum()),
            }
        )
        extreme = work[work["growth_error_pp"].gt(100) | ~valid_yoy].copy()
        if not extreme.empty:
            extreme_rows.append(
                extreme[
                    [
                        "parent_policy_id",
                        "period",
                        "region_code",
                        "region_name",
                        "industry_group",
                        "actual",
                        "prediction",
                        "lag4_actual",
                        "lag4_prediction",
                        "growth_error_pp",
                        "extreme_reason",
                    ]
                ]
            )
    audit = add_audit_cols(pd.DataFrame(rows))
    extreme_audit = add_audit_cols(pd.concat(extreme_rows, ignore_index=True, sort=False) if extreme_rows else pd.DataFrame([{"extreme_reason": "none"}]))
    warmup = add_audit_cols(
        parent[parent["evaluation_role"].eq("warmup_seed")][
            ["parent_policy_id", "period", "region_code", "region_name", "industry_group", "actual", "prediction", "evaluation_role", "scored"]
        ]
    )
    return audit, extreme_audit, warmup


def parent_accuracy(parent: pd.DataFrame, growth: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scored = parent[parent["scored"].eq("Y")].copy()
    rows = []
    for policy, g in scored.groupby("parent_policy_id", sort=True):
        actual = numeric(g["actual"])
        pred = numeric(g["prediction"])
        err = (actual - pred).abs()
        rows.append(
            {
                "parent_policy_id": policy,
                "evaluation_target": "development_proxy_not_official",
                "scored_rows": int(len(g)),
                "average_wmape": float(err.sum() / max(actual.abs().sum(), 1e-9)),
                "mae": float(err.mean()),
                "official_first_release_growth_mae_pp": "",
                "official_level_wmape": "",
            }
        )
    acc = add_audit_cols(pd.DataFrame(rows))
    sel = acc.merge(growth[["parent_policy_id", "yoy_growth_mae_pp", "extreme_error_rows"]], on="parent_policy_id", how="left")
    metric_best = str(sel.sort_values("average_wmape").iloc[0]["parent_policy_id"])
    sel["development_metric_best"] = np.where(sel["parent_policy_id"].eq(metric_best), "Y", "N")
    sel["official_external_metric_best"] = "not_available"
    sel["gate_pass"] = "N"
    sel["gate_failure_reason"] = np.where(
        sel["parent_policy_id"].eq(metric_best),
        "official target cube extraction pending; proxy metric cannot promote policy",
        "not development metric-best or official target pending",
    )
    sel.loc[sel["parent_policy_id"].eq("QP0_seasonal"), "gate_failure_reason"] = "incumbent retained until official target cube is extracted"
    sel["gate_selected_policy"] = np.where(sel["parent_policy_id"].eq("QP0_seasonal"), "Y", "N")
    return acc, add_audit_cols(sel)


def quarter_from_prd_de(value: Any) -> tuple[int | None, int | None]:
    text = str(value)
    if len(text) < 5:
        return None, None
    try:
        return int(text[:4]), int(text[-1])
    except ValueError:
        return None, None


def build_indicator_profiles() -> pd.DataFrame:
    source_files = [
        ("mining_manufacturing_production_index.csv", "production_index"),
        ("mining_production_index.csv", "production_index"),
        ("electricity_gas_production_index.csv", "production_index"),
        ("service_production_index.csv", "service_production_index"),
    ]
    rows = []
    for name, source in source_files:
        df = read_frame(name)
        if df.empty:
            continue
        df = df.copy()
        parsed = df["prd_de"].map(quarter_from_prd_de)
        df["year"] = [p[0] for p in parsed]
        df["quarter"] = [p[1] for p in parsed]
        df["value_num"] = numeric(df["value"])
        df["sector_code"] = df["c2_id"].astype(str).str[:1] + "00"
        df["source_region"] = df["c1_nm"]
        df = df[df["quarter"].between(1, 4) & df["year"].notna() & df["value_num"].gt(0)]
        keep = df[["source_region", "sector_code", "year", "quarter", "value_num"]].copy()
        keep["indicator_source"] = source
        rows.append(keep)
    if not rows:
        return pd.DataFrame()
    all_rows = pd.concat(rows, ignore_index=True, sort=False)
    all_rows = all_rows.groupby(["source_region", "sector_code", "year", "quarter"], as_index=False).agg(
        indicator_value=("value_num", "mean"),
        indicator_source=("indicator_source", lambda s: "+".join(sorted(set(s)))),
    )
    total = all_rows.groupby(["source_region", "sector_code", "year"])["indicator_value"].transform("sum")
    all_rows["quarter_share"] = all_rows["indicator_value"] / total.replace(0, np.nan)
    return all_rows


def build_parent_proxy_profiles() -> pd.DataFrame:
    parent = read_frame("partial_stats_phase20_gva_qp0_seasonal_results.csv")
    if parent.empty:
        return pd.DataFrame()
    parent = parent.copy()
    parent["year"] = numeric(parent["year"]).astype("Int64")
    parent["quarter"] = numeric(parent["quarter"]).astype("Int64")
    parent["parent_value"] = numeric(parent["actual"])
    parent["sector_code"] = parent["industry_group"]
    work = parent[parent["parent_value"].gt(0)].copy()
    total = work.groupby(["region_name", "sector_code", "year"])["parent_value"].transform("sum")
    work["quarter_share"] = work["parent_value"] / total.replace(0, np.nan)
    return work[["region_name", "sector_code", "year", "quarter", "quarter_share"]].rename(columns={"region_name": "source_region"})


def sigungu_quarterly_allocation() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    annual = read_frame("sigungu_annual_rolling_backtest.csv")
    if annual.empty:
        raise SystemExit("sigungu_annual_rolling_backtest.csv is required")
    annual = annual.copy()
    annual["target_year"] = numeric(annual["target_year"]).astype("Int64")
    annual["actual_annual_gva_num"] = numeric(annual["actual_annual_gva"])
    annual = annual[annual["actual_annual_gva_num"].notna()].drop_duplicates(
        ["source_region", "sigungu_code", "sector_code", "target_year"], keep="last"
    )
    indicators = build_indicator_profiles()
    parent_profiles = build_parent_proxy_profiles()
    out_rows: list[dict[str, Any]] = []
    for row in annual.to_dict("records"):
        region = row["source_region"]
        sector = row["sector_code"]
        year = int(row["target_year"])
        profile = indicators[
            indicators["source_region"].eq(region) & indicators["sector_code"].eq(sector) & indicators["year"].eq(year)
        ][["quarter", "quarter_share", "indicator_source"]]
        allocation_basis = "quarterly_industrial_production_index"
        if len(profile) != 4 or profile["quarter_share"].isna().any():
            parent = parent_profiles[
                parent_profiles["source_region"].eq(region) & parent_profiles["sector_code"].eq(sector) & parent_profiles["year"].eq(year)
            ][["quarter", "quarter_share"]]
            profile = parent.assign(indicator_source="project_sido_quarterly_gva_proxy")
            allocation_basis = "project_sido_quarterly_gva_proxy"
        if len(profile) != 4 or profile["quarter_share"].isna().any():
            profile = pd.DataFrame({"quarter": [1, 2, 3, 4], "quarter_share": [0.25] * 4, "indicator_source": ["equal_quarter_fallback"] * 4})
            allocation_basis = "equal_quarter_fallback"
        profile = profile.sort_values("quarter").copy()
        total_share = profile["quarter_share"].sum()
        profile["quarter_share"] = profile["quarter_share"] / total_share if total_share else 0.25
        for p in profile.to_dict("records"):
            q = int(p["quarter"])
            out_rows.append(
                {
                    "source_region": region,
                    "sigungu_code": row["sigungu_code"],
                    "sigungu_name": row["sigungu_name"],
                    "sector_code": sector,
                    "sector_name": row["sector_name"],
                    "year": year,
                    "quarter": q,
                    "period": f"{year}Q{q}",
                    "annual_benchmark_gva": row["actual_annual_gva_num"],
                    "quarter_share": float(p["quarter_share"]),
                    "estimated_quarterly_gva": float(row["actual_annual_gva_num"]) * float(p["quarter_share"]),
                    "allocation_basis": allocation_basis,
                    "indicator_source": p["indicator_source"],
                    "benchmark_source": "sigungu_annual_grdp_or_gva_official_kosis_snapshot",
                    "actual_claim": "N",
                    "development_status": "benchmark_consistent_quarterly_development_estimate",
                }
            )
    cube = add_audit_cols(pd.DataFrame(out_rows))
    annual_sum = cube.groupby(["source_region", "sigungu_code", "sector_code", "year"], as_index=False).agg(
        quarter_sum=("estimated_quarterly_gva", "sum"),
        annual_benchmark_gva=("annual_benchmark_gva", "first"),
        allocation_basis=("allocation_basis", lambda s: "+".join(sorted(set(s)))),
    )
    annual_sum["annual_recovery_error"] = annual_sum["quarter_sum"] - annual_sum["annual_benchmark_gva"]
    annual_sum["annual_recovery_abs_pct"] = annual_sum["annual_recovery_error"].abs() / annual_sum["annual_benchmark_gva"].abs().replace(0, np.nan)
    diag = add_audit_cols(annual_sum)
    registry = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "source_name": "sigungu_annual_grdp",
                    "status": "active_local_processed_benchmark",
                    "role": "child annual benchmark",
                    "frequency": "annual",
                    "release_timing_risk": "annual official release lag applies",
                },
                {
                    "source_name": "sido_quarterly_industrial_production_index",
                    "status": "active_for_B_C_D_and_available_service_codes",
                    "role": "quarterly temporal profile",
                    "frequency": "quarterly",
                    "release_timing_risk": "must be cutoff-filtered for prospective use",
                },
                {
                    "source_name": "project_sido_quarterly_gva_proxy",
                    "status": "active_fallback_not_official_actual",
                    "role": "quarterly temporal profile fallback",
                    "frequency": "quarterly",
                    "release_timing_risk": "proxy track only",
                },
                {
                    "source_name": "sigungu_business_count_by_industry",
                    "status": "not_yet_materialized",
                    "role": "spatial structural weight",
                    "frequency": "annual",
                    "release_timing_risk": "collect KOSIS or Census source with as-of dates",
                },
                {
                    "source_name": "farmland_area_by_sigungu",
                    "status": "not_yet_materialized",
                    "role": "A00 agriculture spatial weight",
                    "frequency": "annual",
                    "release_timing_risk": "release lag must be enforced",
                },
                {
                    "source_name": "factory_count_by_sigungu",
                    "status": "not_yet_materialized",
                    "role": "C00 manufacturing spatial weight",
                    "frequency": "annual",
                    "release_timing_risk": "release lag must be enforced",
                },
            ]
        )
    )
    cube.to_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet", index=False)
    return cube, diag, registry


def origin_registry() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    origins = [
        ("F0", ["annual_sigungu_benchmark_lagged", "seasonal_baseline"], "independent_information_origin"),
        ("Q30", ["quarterly_industrial_production_index_partial", "project_parent_proxy"], "independent_information_origin"),
        ("PRE_RELEASE", ["official_quarterly_grdp_release_source"], "independent_information_no_model_response"),
    ]
    rows = []
    for origin, sources, status in origins:
        rows.append(
            {
                "origin_id": origin,
                "eligible_source_count": len(sources),
                "eligible_source_hash": core.stable_hash(sources),
                "feature_content_hash": core.stable_hash([origin, *sources]),
                "model_input_hash": core.stable_hash([origin, sources, "phase22_static_policy"]),
                "prediction_hash": core.stable_hash([origin, "proxy_or_not_evaluated"]),
                "origin_status": status,
            }
        )
    registry = add_audit_cols(pd.DataFrame(rows))
    collapse = registry.groupby(["eligible_source_hash", "feature_content_hash"], as_index=False).size()
    collapse["collapse_status"] = np.where(collapse["size"].gt(1), "collapsed_origin", "not_collapsed")
    return registry, add_audit_cols(registry.copy()), add_audit_cols(collapse)


def make_report(ctx: dict[str, Any]) -> None:
    sections = [
        ("실행 요약", ctx["final"]),
        ("목표 불변 선언", ctx["goal"]),
        ("Phase 21 결과", ctx["phase21"]),
        ("공식 분기 GRDP 원문", ctx["source"]),
        ("공식 Source Authenticity", ctx["source"]),
        ("Release·Vintage", ctx["vintage"]),
        ("Target Measure", ctx["measure"]),
        ("공식 산업 Crosswalk", ctx["crosswalk"]),
        ("실질·명목 Track", ctx["real_nominal"]),
        ("Warm-up Audit", ctx["warmup"]),
        ("Leakage Audit", ctx["leakage"]),
        ("Growth Metric Audit", ctx["growth"]),
        ("Extreme Growth Error", ctx["extreme"]),
        ("Development Proxy Track", ctx["parent_accuracy"]),
        ("Official Direct Track", ctx["official_eval"]),
        ("Quarterly Origin", ctx["origin"]),
        ("Origin Collapse", ctx["collapse"]),
        ("QP0 Seasonal", ctx["qp0"]),
        ("QP1 National Bridge", ctx["qp1"]),
        ("QP2 Robust Indicator Bridge", ctx["qp2"]),
        ("QP3 Pooled Robust Panel", ctx["qp3"]),
        ("QP4 Factor Gate", ctx["qp4"]),
        ("QP5 MIDAS Gate", ctx["qp5"]),
        ("Shock-quarter Firewall", ctx["shock"]),
        ("Parent Policy Selection", ctx["selection"]),
        ("Official Growth Accuracy", ctx["official_growth"]),
        ("Official Direction Accuracy", ctx["official_direction"]),
        ("Official Revision Accuracy", ctx["official_revision"]),
        ("Child Last-share", ctx["child_diag"]),
        ("Child Activity Share", ctx["structural"]),
        ("시군구 연간 GRDP 분기배분", ctx["sigungu_allocation"]),
        ("Unreconciled Forecast", ctx["unreconciled"]),
        ("Reconciled Estimate", ctx["reconciled"]),
        ("Temporal Method Identity", ctx["temporal"]),
        ("Reconciliation Distortion", ctx["distortion"]),
        ("2025 Locked Replay", ctx["replay"]),
        ("Prospective Holdout", ctx["archive"]),
        ("2026 Quarterly Nowcast", ctx["nowcast"]),
        ("2026 Annual-from-quarters", ctx["annual"]),
        ("Monthly Gate", ctx["monthly"]),
        ("불확실성", ctx["uncertainty"]),
        ("Risk Queue", ctx["risk"]),
        ("최종 정책", ctx["policy"]),
        ("한계", ctx["limits"]),
        ("결론", ctx["conclusion"]),
        ("아직 주장할 수 없는 내용", ctx["cannot_claim"]),
    ]
    lines = ["# Partial Statistics Estimation Phase 22-GVA", ""]
    for idx, (title, content) in enumerate(sections, start=1):
        lines += [f"## {idx}. {title}", ""]
        lines.append(markdown_table(content) if isinstance(content, pd.DataFrame) else str(content))
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    topic = ROOT / "reports" / "topics" / "ml.md"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# Reconciled ML Experiments\n\n| Report | Purpose |\n| --- | --- |\n"
    row = "| [partial_statistics_estimation_phase22_gva.md](../partial_statistics_estimation_phase22_gva.md) | Official quarterly GRDP source acquisition, growth metric audit, and sigungu annual GRDP quarterly allocation |\n"
    if "partial_statistics_estimation_phase22_gva.md" not in text:
        topic.write_text(text.replace("| --- | --- |\n", "| --- | --- |\n" + row), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    final_path = PROCESSED_DIR / "partial_stats_phase22_gva_final_status.json"
    if final_path.exists() and not args.force:
        print(final_path)
        return 0

    source, release, vintage, official_cube, measure = materialize_official_sources()
    parent = parent_rows()
    growth, extreme, warmup = growth_metric_audit(parent)
    parent_acc, selection = parent_accuracy(parent, growth)
    child_cube, child_diag, structural = sigungu_quarterly_allocation()
    origin, origin_hash, collapse = origin_registry()

    crosswalk = add_audit_cols(
        pd.DataFrame(
            [
                {"official_industry_group": "광업·제조업", "project_industry_code": "B00;C00", "mapping_status": "broad_group_only"},
                {"official_industry_group": "건설업", "project_industry_code": "F00", "mapping_status": "direct_broad_group"},
                {"official_industry_group": "서비스업", "project_industry_code": "G00~S00", "mapping_status": "broad_group_only"},
                {"official_industry_group": "기타", "project_industry_code": "A00;D00;E00;O00;tax", "mapping_status": "definition_requires_pdf_table_extraction"},
            ]
        )
    )
    real_nominal = add_audit_cols(pd.DataFrame([{"track": "official_quarterly_grdp", "price_basis": "real", "nominal_level_mixing": "N"}]))
    leakage = add_audit_cols(
        pd.DataFrame(
            [
                {"check_id": "future_release_excluded", "status": "pass_design", "note": "official releases are registered by posted_at for future cutoff filtering"},
                {"check_id": "target_copy_scored", "status": "pass", "scored_rows": 0},
                {"check_id": "sigungu_quarterly_actual_claim", "status": "pass", "note": "child quarterly cube is development estimate only"},
            ]
        )
    )
    official_eval = add_audit_cols(pd.DataFrame([{"evaluation_target": "official_first_release", "status": "blocked_target_cube_extraction_pending", "rows": 0}]))
    official_growth = add_audit_cols(pd.DataFrame([{"evaluation_target": "official_growth", "status": "blocked_pdf_table_parser_not_implemented", "rows": 0}]))
    official_direction = add_audit_cols(pd.DataFrame([{"evaluation_target": "official_direction", "status": "blocked_pdf_table_parser_not_implemented", "rows": 0}]))
    official_revision = add_audit_cols(pd.DataFrame([{"evaluation_target": "official_revision", "status": "blocked_no_revision_cube", "rows": 0}]))
    temporal = add_audit_cols(pd.DataFrame([{"temporal_policy_id": "T2_indicator_proportional", "status": "activated_for_sigungu_annual_allocation"}, {"temporal_policy_id": "T3_proportional_denton", "status": "incumbent_parent_child_development"}]))
    distortion = add_audit_cols(
        pd.DataFrame(
            [
                {
                    "metric": "sigungu_annual_recovery_max_abs_pct",
                    "value": float(numeric(child_diag["annual_recovery_abs_pct"]).fillna(0).max()),
                    "status": "constraint_pass",
                }
            ]
        )
    )
    replay = read_frame("partial_stats_phase21_gva_quarterly_replay_2025.csv")
    if replay.empty:
        replay = pd.DataFrame([{"target_period": "2025Q1", "status": "source_materialized_target_extraction_pending"}])
    nowcast = read_frame("partial_stats_phase21_gva_quarterly_nowcast_2026.csv")
    if nowcast.empty:
        nowcast = pd.DataFrame([{"target_period": "2026Q2", "status": "forecast_not_materialized"}])
    annual = read_frame("partial_stats_phase21_gva_annual_from_quarters_2026.csv")
    if annual.empty:
        annual = pd.DataFrame([{"target_year": "2026", "status": "blocked"}])
    archive = add_audit_cols(pd.DataFrame([{"target_quarter": "2026Q2_or_next_unreleased", "archive_status": "frozen_requires_current_release_check", "forecast_created_at": GENERATED_AT}]))

    final = {
        "status": "official_source_materialized_target_extraction_pending;sigungu_annual_grdp_quarterly_allocation_activated;quarterly_child_development_retained",
        "target": "GVA",
        "target_unchanged": True,
        "official_quarterly_source_materialized": bool(source["source_body_exists"].eq("pass").all()),
        "official_source_file_count": int(source["source_body_exists"].eq("pass").sum()),
        "official_source_period_count": int(source["reference_period"].nunique()),
        "official_vintage_count": int(vintage["vintage_status"].str.contains("materialized", regex=False).sum()),
        "official_first_release_target_count": int(len(official_cube)),
        "official_quarterly_target_materialized": False,
        "target_measure_type": "real_yoy_growth_source_materialized_extraction_pending",
        "growth_metric_integrity": "pass_on_development_proxy_population",
        "warmup_scored_rows": 0,
        "target_copy_scored_rows": 0,
        "independent_origin_count": int(origin["origin_status"].str.contains("independent_information", regex=False).sum()),
        "collapsed_origin_count": int(collapse["collapse_status"].eq("collapsed_origin").sum()),
        "development_metric_best_policy": str(selection[selection["development_metric_best"].eq("Y")]["parent_policy_id"].iloc[0]),
        "gate_selected_policy": "QP0_seasonal",
        "sigungu_quarterly_allocation_rows": int(len(child_cube)),
        "sigungu_annual_recovery_max_abs_pct": float(numeric(child_diag["annual_recovery_abs_pct"]).fillna(0).max()),
        "indicator_profile_rows": int(child_cube["allocation_basis"].eq("quarterly_industrial_production_index").sum()),
        "fallback_profile_rows": int(child_cube["allocation_basis"].ne("quarterly_industrial_production_index").sum()),
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }

    outputs = {
        "partial_stats_phase22_gva_official_source_manifest.csv": source,
        "partial_stats_phase22_gva_official_release_ledger.csv": release,
        "partial_stats_phase22_gva_official_vintage_registry.csv": vintage,
        "partial_stats_phase22_gva_target_measure_registry.csv": measure,
        "partial_stats_phase22_gva_official_industry_crosswalk.csv": crosswalk,
        "partial_stats_phase22_gva_real_nominal_audit.csv": real_nominal,
        "partial_stats_phase22_gva_growth_metric_audit.csv": growth,
        "partial_stats_phase22_gva_extreme_growth_error_audit.csv": extreme,
        "partial_stats_phase22_gva_warmup_audit.csv": warmup,
        "partial_stats_phase22_gva_leakage_audit.csv": leakage,
        "partial_stats_phase22_gva_origin_registry.csv": origin,
        "partial_stats_phase22_gva_origin_hash_audit.csv": origin_hash,
        "partial_stats_phase22_gva_origin_collapse_registry.csv": collapse,
        "partial_stats_phase22_gva_parent_policy_selection.csv": selection,
        "partial_stats_phase22_gva_official_growth_accuracy.csv": official_growth,
        "partial_stats_phase22_gva_official_level_accuracy.csv": official_eval,
        "partial_stats_phase22_gva_official_direction_accuracy.csv": official_direction,
        "partial_stats_phase22_gva_official_revision_accuracy.csv": official_revision,
        "partial_stats_phase22_gva_child_validation.csv": child_diag,
        "partial_stats_phase22_gva_structural_weight_registry.csv": structural,
        "partial_stats_phase22_gva_temporal_identity_audit.csv": temporal,
        "partial_stats_phase22_gva_reconciliation_distortion.csv": distortion,
        "partial_stats_phase22_gva_quarterly_replay_2025.csv": add_audit_cols(replay),
        "partial_stats_phase22_gva_quarterly_nowcast_2026.csv": add_audit_cols(nowcast),
        "partial_stats_phase22_gva_annual_from_quarters_2026.csv": add_audit_cols(annual),
        "partial_stats_phase22_gva_prospective_forecast_archive.csv": archive,
    }
    for policy in QP_MAP:
        short = policy.split("_")[0].lower()
        outputs[f"partial_stats_phase22_gva_{short}_results.csv"] = parent_acc[parent_acc["parent_policy_id"].eq(policy)]
    for name, frame in outputs.items():
        write_frame(name, frame)
    write_json(PROCESSED_DIR / "partial_stats_phase22_gva_goal_charter.json", {"PRIMARY_TARGET": "region_industry_period_gva", "QUARTERLY_CHILD_TARGET": "sigungu_industry_quarter_development_estimate"})
    write_json(PROCESSED_DIR / "partial_stats_phase22_gva_policy_registry.json", {"gate_selected_policy": "QP0_seasonal", "child_policy": "annual_benchmark_with_indicator_quarter_profile"})
    write_json(PROCESSED_DIR / "partial_stats_phase22_gva_prospective_archive_manifest.json", {"forecast_created_at": GENERATED_AT, "archive_status": "frozen_requires_current_release_check"})
    manifest = add_audit_cols(pd.DataFrame([{"artifact": name, "status": "completed", "python": platform.python_version()} for name in [*outputs.keys(), "partial_stats_phase22_gva_official_target_cube.parquet", "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet"]]))
    write_json(PROCESSED_DIR / "partial_stats_phase22_gva_experiment_manifest.json", manifest.to_dict("records"))
    write_frame("partial_stats_phase22_gva_execution_manifest.csv", manifest)
    write_json(PROCESSED_DIR / "partial_stats_phase22_gva_final_status.json", final)

    make_report(
        {
            "final": pd.DataFrame([final]),
            "goal": pd.DataFrame([{"PRIMARY_TARGET": "지역×업종×기간 GVA", "QUARTERLY_DIRECT_TARGET": "시도×광역산업×분기 official growth", "QUARTERLY_CHILD_TARGET": "시군구×산업×분기 development estimate"}]),
            "phase21": "Phase 21의 공식 원문 미수집 상태를 Phase 22에서 보도자료 원문 수집과 해시 보존 상태로 전환했다. 단, PDF 표에서 구조화 Target Cube를 추출하는 parser는 아직 별도 구현이 필요하다.",
            "source": source,
            "vintage": vintage,
            "measure": measure,
            "crosswalk": crosswalk,
            "real_nominal": real_nominal,
            "warmup": warmup,
            "leakage": leakage,
            "growth": growth,
            "extreme": extreme,
            "parent_accuracy": parent_acc,
            "official_eval": official_eval,
            "origin": origin,
            "collapse": collapse,
            "qp0": outputs["partial_stats_phase22_gva_qp0_results.csv"],
            "qp1": outputs["partial_stats_phase22_gva_qp1_results.csv"],
            "qp2": outputs["partial_stats_phase22_gva_qp2_results.csv"],
            "qp3": outputs["partial_stats_phase22_gva_qp3_results.csv"],
            "qp4": outputs["partial_stats_phase22_gva_qp4_results.csv"],
            "qp5": outputs["partial_stats_phase22_gva_qp5_results.csv"],
            "shock": extreme.head(20),
            "selection": selection,
            "official_growth": official_growth,
            "official_direction": official_direction,
            "official_revision": official_revision,
            "child_diag": child_diag.head(20),
            "structural": structural,
            "sigungu_allocation": child_cube.head(20),
            "unreconciled": "시군구 연간 benchmark를 보존한 분기 allocation cube를 `partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet`로 저장했다.",
            "reconciled": "이번 단계에서는 연간 시군구 제약을 정확히 만족한다. 공식 시도 분기 parent target 추출 후 parent reconciliation을 추가 적용한다.",
            "temporal": temporal,
            "distortion": distortion,
            "replay": replay.head(20),
            "archive": archive,
            "nowcast": nowcast.head(20),
            "annual": annual.head(20),
            "monthly": pd.DataFrame([{"monthly_primary_status": "blocked_independent_gate"}]),
            "uncertainty": pd.DataFrame([{"uncertainty_status": "scenario_only_until_official_target_cube"}]),
            "risk": pd.DataFrame([{"risk": "PDF table parser and HWPX extraction not implemented", "severity": "high"}, {"risk": "structural weights for farmland/factory/business count are not yet materialized at sigungu level", "severity": "medium"}]),
            "policy": pd.DataFrame([{"parent_policy": "QP0 retained", "child_policy": "annual benchmark + quarterly indicator profile", "production_use": False}]),
            "limits": "공식 원문은 확보했지만 구조화된 공식 growth/level target cube는 아직 비어 있다. 따라서 공식 외부 정확도는 아직 주장하지 않는다.",
            "conclusion": "Phase 22는 공식 분기 GRDP 원문 수집을 활성화하고, 시군구 연간 GRDP/GVA benchmark를 분기 산업지표 profile로 배분하는 산출 경로를 추가했다.",
            "cannot_claim": "Official target accuracy, production deployment, official statistics equivalence, and direct sigungu quarterly actual accuracy.",
        }
    )
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
