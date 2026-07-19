from __future__ import annotations

import pandas as pd

from phase33_common import PROCESSED_DIR, add_audit, read_csv, write_csv


def build_rq1_audit() -> tuple[pd.DataFrame, pd.DataFrame]:
    path = PROCESSED_DIR / "partial_stats_phase23_gva_qp1_growth_results.csv"
    target = read_csv(path)
    region_col = next((c for c in ["region_code", "sido_code"] if c in target.columns), "")
    region_name_col = next((c for c in ["region_name", "sido_name"] if c in target.columns), "")
    period_col = next((c for c in ["reference_period", "period"] if c in target.columns), "")
    industry_col = next((c for c in ["industry_group", "sector", "official_industry_group"] if c in target.columns), "")
    cardinality = pd.DataFrame(
        [
            {"dimension": "row_count", "value": len(target), "interpretation": "primary RQ1 evaluation rows"},
            {"dimension": "region", "value": target[region_col].nunique() if region_col else 0, "interpretation": region_col or "missing"},
            {"dimension": "region_name", "value": target[region_name_col].nunique() if region_name_col else 0, "interpretation": region_name_col or "missing"},
            {"dimension": "period", "value": target[period_col].nunique() if period_col else 0, "interpretation": period_col or "missing"},
            {"dimension": "industry", "value": target[industry_col].nunique() if industry_col else 0, "interpretation": industry_col or "industry axis absent"},
            {"dimension": "unique_key", "value": target.drop_duplicates([c for c in [region_col, period_col] if c]).shape[0] if region_col and period_col else 0, "interpretation": "region×period"},
            {"dimension": "duplicate_key", "value": int(target.duplicated([c for c in [region_col, period_col] if c]).sum()) if region_col and period_col else 0, "interpretation": "region×period duplicates"},
        ]
    )
    cardinality["is_17_by_20"] = "Y" if len(target) == 340 else "N"

    compatibility = pd.DataFrame(
        [
            {
                "bridge_id": "TQ3_quarter_share_to_RQ1_real_yoy",
                "tq3_semantics": "service_index_quarter_share",
                "rq1_semantics": "total_GRDP_real_YoY_growth",
                "region_compatibility": "sido",
                "industry_compatibility": "fail_RQ1_has_no_service_industry_axis",
                "period_compatibility": "quarter",
                "concept_compatibility": "fail_share_vs_growth",
                "price_basis_compatibility": "not_directly_comparable",
                "decision": "Retired",
                "allowed_use": "none",
            },
            {
                "bridge_id": "service_composite_yoy_to_RQ1_total_grdp_yoy",
                "tq3_semantics": "service_index_equal_weight_composite_YoY",
                "rq1_semantics": "total_GRDP_real_YoY_growth",
                "region_compatibility": "sido",
                "industry_compatibility": "aggregate_only",
                "period_compatibility": "quarter",
                "concept_compatibility": "direction_only_external_validation",
                "price_basis_compatibility": "index_current_price_vs_real_growth_mismatch",
                "decision": "Retained",
                "allowed_use": "external_direction_diagnostic_not_direct_accuracy",
            },
        ]
    )
    return add_audit(cardinality), add_audit(compatibility)


def main() -> int:
    cardinality, compatibility = build_rq1_audit()
    write_csv("phase33_rq1_cardinality.csv", cardinality)
    write_csv("phase33_rq1_compatibility.csv", compatibility)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
