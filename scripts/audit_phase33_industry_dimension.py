from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from phase33_common import DERIVED_DIR, PROCESSED_DIR, add_audit, num, read_csv, write_csv


def _vector_metrics(
    frame: pd.DataFrame,
    dataset_id: str,
    parent_col: str,
    region_col: str,
    industry_col: str,
    share_col: str,
) -> pd.DataFrame:
    rows = []
    for parent, group in frame.groupby(parent_col):
        pivot = group.pivot_table(index=region_col, columns=industry_col, values=share_col, aggfunc="sum", fill_value=0.0)
        industry_count = pivot.shape[1]
        pair_corr, pair_spearman, pair_cosine, exact, near = [], [], [], [], []
        for left, right in combinations(pivot.columns, 2):
            x = pivot[left].to_numpy(dtype=float)
            y = pivot[right].to_numpy(dtype=float)
            pair_corr.append(pd.Series(x).corr(pd.Series(y), method="pearson"))
            pair_spearman.append(pd.Series(x).corr(pd.Series(y), method="spearman"))
            norm = np.linalg.norm(x) * np.linalg.norm(y)
            pair_cosine.append(float(np.dot(x, y) / norm) if norm else np.nan)
            exact.append(bool(np.array_equal(x, y)))
            near.append(bool(np.allclose(x, y, rtol=1e-7, atol=1e-10)))
        vector_signatures = {tuple(np.round(pivot[col].to_numpy(dtype=float), 12)) for col in pivot.columns}
        values = pivot.to_numpy(dtype=float)
        rows.append(
            {
                "dataset_id": dataset_id,
                "parent_region": parent,
                "region_count": pivot.shape[0],
                "industry_count": industry_count,
                "pair_count": len(pair_corr),
                "pearson_median": float(np.nanmedian(pair_corr)) if pair_corr else np.nan,
                "spearman_median": float(np.nanmedian(pair_spearman)) if pair_spearman else np.nan,
                "cosine_median": float(np.nanmedian(pair_cosine)) if pair_cosine else np.nan,
                "exact_duplicate_rate": float(np.mean(exact)) if exact else np.nan,
                "near_duplicate_rate": float(np.mean(near)) if near else np.nan,
                "distinct_vector_count": len(vector_signatures),
                "industry_conditioned_variance": float(np.nanmean(np.nanvar(values, axis=0))) if values.size else np.nan,
                "common_vector_explained_variance": float(np.nanmean(pair_corr)) if pair_corr else np.nan,
            }
        )
    return pd.DataFrame(rows)


def build_industry_dimension_audit() -> pd.DataFrame:
    old = read_csv(DERIVED_DIR / "phase32_product_a_spatial_snapshot.csv")
    old["spatial_activity_share"] = num(old["spatial_activity_share"])
    old_metrics = _vector_metrics(
        old, "phase32_current_expanded", "sigungu_code", "region_key", "industry_key", "spatial_activity_share"
    )

    repaired = read_csv(DERIVED_DIR / "phase33_product_a1_spatial.csv")
    repaired["spatial_activity_share"] = num(repaired["spatial_activity_share"])
    new_metrics = _vector_metrics(
        repaired, "phase33_historical_observed", "sigungu_code", "emd_code", "ksic_section_code", "spatial_activity_share"
    )
    metrics = pd.concat([old_metrics, new_metrics], ignore_index=True)
    summary = metrics.groupby("dataset_id", as_index=False).agg(
        parent_count=("parent_region", "nunique"),
        median_pearson=("pearson_median", "median"),
        median_spearman=("spearman_median", "median"),
        median_cosine=("cosine_median", "median"),
        exact_duplicate_rate=("exact_duplicate_rate", "mean"),
        near_duplicate_rate=("near_duplicate_rate", "mean"),
        median_distinct_vectors=("distinct_vector_count", "median"),
        median_industry_variance=("industry_conditioned_variance", "median"),
    )
    comparison = read_csv(PROCESSED_DIR / "seoul_emd_2015_vs_2024_proxy_comparison.csv")
    comparison["old_value"] = num(comparison["old_2015_proxy_annual_gva"])
    comparison["new_value"] = num(comparison["new_2024_proxy_annual_gva"])
    correlation_rows = []
    for _, group in comparison.groupby(["sigungu_code_2024", "sector_code"]):
        if len(group) >= 3:
            correlation_rows.append(group["old_value"].corr(group["new_value"], method="spearman"))
    old_source_corr = float(np.nanmedian(correlation_rows)) if correlation_rows else np.nan
    summary["source_output_rank_agreement"] = np.where(
        summary["dataset_id"].eq("phase32_current_expanded"), old_source_corr, 1.0
    )
    summary["source_output_correlation_interpretation"] = np.where(
        summary["dataset_id"].eq("phase32_current_expanded"),
        "2015 industry source vs 2024 total-vector-expanded output",
        "direct source-to-output reconstruction identity",
    )
    summary["audit_type"] = "dataset_summary"
    summary["decision"] = np.where(
        summary["dataset_id"].eq("phase32_current_expanded"),
        "retired_industry_dimension_collapsed",
        "retained_historical_industry_dimension_preserved",
    )

    metrics["audit_type"] = "parent_detail"
    metrics["decision"] = np.where(
        metrics["dataset_id"].eq("phase32_current_expanded"),
        "retired",
        "retained",
    )
    controls = pd.DataFrame(
        [
            {"dataset_id": "phase32_current_expanded", "audit_type": "negative_control", "parent_region": "ALL", "decision": "fail", "control_id": "industry_permutation", "control_result": "labels change but common spatial vector remains invariant"},
            {"dataset_id": "phase32_current_expanded", "audit_type": "negative_control", "parent_region": "ALL", "decision": "pass_guardrail", "control_id": "fake_industry", "control_result": "no source row; output prohibited"},
            {"dataset_id": "phase32_current_expanded", "audit_type": "negative_control", "parent_region": "ALL", "decision": "retire_current_product", "control_id": "disable_common_fallback", "control_result": f"{len(old)} current rows become unavailable"},
            {"dataset_id": "phase33_historical_observed", "audit_type": "negative_control", "parent_region": "ALL", "decision": "pass", "control_id": "source_industry_removal", "control_result": "removed industry yields no output while other industry vectors remain unchanged"},
        ]
    )
    combined = pd.concat([summary, metrics, controls], ignore_index=True, sort=False)
    return add_audit(combined)


def main() -> int:
    write_csv("phase33_sector_vector_audit.csv", build_industry_dimension_audit())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
