from __future__ import annotations

import json

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_csv(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    shadow_path = PROCESSED_DIR / "partial_stats_phase34_gva_joint_shadow.parquet"
    status_path = PROCESSED_DIR / "partial_stats_phase34_gva_final_status.json"
    report_path = ROOT / "reports" / "partial_statistics_estimation_phase34_gva.md"
    require(shadow_path.exists(), "missing joint shadow")
    require(status_path.exists(), "missing final status")
    require(report_path.exists(), "missing report")

    shadow = pd.read_parquet(shadow_path)
    coverage = read_csv("partial_stats_phase34_gva_coverage.csv")
    conservation = read_csv("partial_stats_phase34_gva_conservation.csv")
    identity = read_csv("partial_stats_phase34_gva_proxy_identity_audit.csv")
    stability = read_csv("partial_stats_phase34_gva_structure_stability.csv")
    negative = read_csv("partial_stats_phase34_gva_negative_controls.csv")
    resolution = read_csv("partial_stats_phase34_gva_resolution_decision.csv")
    status = json.loads(status_path.read_text(encoding="utf-8"))

    require(set(shadow["policy_id"]) == {"R0_contemporaneous_structure", "S0_lag2_structure"}, "unexpected policies")
    require(not shadow.duplicated(["policy_id", "sigungu_code", "parent_sector_code", "industry_code", "target_year", "quarter"]).any(), "duplicate joint keys")
    require(shadow["parent_sector_code"].isin(["B00", "C00"]).all(), "unsupported parent sector")
    require(shadow["quarter"].isin([1, 2, 3, 4]).all(), "invalid quarter")
    require(shadow["quarterly_middle_allocation"].ge(0).all(), "negative allocation")
    require(shadow["direct_quarterly_middle_actual_available"].eq("N").all(), "direct actual claim leaked")
    require(shadow["interaction_source_id"].eq("").all(), "fabricated interaction source")
    require(shadow["production_use"].eq("false").all(), "production use must be false")
    require(shadow["official_statistics_claim"].eq("false").all(), "official claim must be false")
    require(shadow.loc[shadow["policy_id"].eq("R0_contemporaneous_structure"), "structure_asof_eligible"].eq("N").all(), "retrospective policy mislabeled eligible")
    require(shadow.loc[shadow["policy_id"].eq("S0_lag2_structure"), "structure_asof_eligible"].eq("Y").all(), "lag2 structure not eligible")
    require(shadow["temporal_vintage_eligible"].eq("N").all(), "temporal vintage fabricated")
    require(conservation["status"].eq("pass").all(), "parent conservation failed")
    require(pd.to_numeric(conservation["absolute_error"]).max() <= 1e-6, "conservation error too large")
    rank = identity[identity["audit_id"].eq("fine_temporal_matrix_rank")]
    require(pd.to_numeric(rank["value"]).eq(1).all(), "expected rank-one separable cube")
    common = identity[identity["audit_id"].eq("within_parent_identical_industry_temporal_profile_rate")]
    require(pd.to_numeric(common["value"]).eq(1).all(), "common middle-industry proxy not detected")
    require(identity[identity["audit_id"].eq("business_employee_share_correlation")]["status"].eq("related_same_family_not_independent").all(), "same source family issue not recorded")
    require(negative["conservation_still_passes"].eq("Y").all(), "negative-control conservation result missing")
    require(set(resolution["decision"]) >= {"blocked", "blocked_as_joint_GVA", "retain_as_structure_allocation_only"}, "resolution decisions incomplete")
    require(len(stability) == 2 and set(stability["parent_sector_code"]) == {"B00", "C00"}, "stability scope incomplete")
    require(coverage[coverage["policy_id"].eq("R0_contemporaneous_structure")]["matched_parent_cells"].astype(int).sum() > 0, "empty retrospective coverage")
    require(status["joint_product_decision"] == "Blocked", "joint product must be blocked")
    require(status["direct_quarterly_middle_actual_available"] is False, "direct actual status incorrect")
    require(status["interaction_source_available"] is False, "interaction status incorrect")
    require(status["production_use"] is False and status["official_statistics_claim"] is False, "claim guardrails failed")
    require("rank가 1" in report_path.read_text(encoding="utf-8"), "report does not state rank-one limitation")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
