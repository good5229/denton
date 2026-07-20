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
    status_path = PROCESSED_DIR / "partial_stats_phase35_final_status.json"
    report_path = ROOT / "reports" / "partial_statistics_estimation_phase35_gva.md"
    require(status_path.exists(), "missing Phase35 final status")
    require(report_path.exists(), "missing Phase35 report")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    inventory = read_csv("partial_stats_phase35_source_inventory.csv")
    candidate = read_csv("partial_stats_phase35_kepco_monthly_candidate.csv")
    support = read_csv("partial_stats_phase35_kepco_support.csv")
    conservation = read_csv("partial_stats_phase35_kepco_conservation.csv")
    identity = read_csv("partial_stats_phase35_interaction_identity_audit.csv")
    labels = read_csv("partial_stats_phase35_nts_label_drift.csv")
    release = read_csv("partial_stats_phase35_release_audit.csv")
    negative = read_csv("partial_stats_phase35_negative_controls.csv")

    require(inventory["cost"].eq("free").all(), "non-free source entered inventory")
    require(not inventory["source_family"].str.contains("card", case=False).any(), "card data entered experiment")
    require(len(candidate) == 1401, "unexpected KEPCO candidate row count")
    require(not candidate.duplicated([
        "source_region", "sigungu_code", "industry_code", "target_year", "month"
    ]).any(), "candidate composite key is not unique")
    require(candidate["month"].isin(["1", "2", "3"]).all(), "candidate is not 2023Q1 monthly")
    require(candidate["release_asof_quarter_end"].eq("N").all(), "release leakage guard failed")
    require(candidate["production_use"].eq("false").all(), "production-use guard failed")
    require(conservation["status"].eq("pass").all(), "monthly-to-quarter conservation failed")
    require(pd.to_numeric(conservation["absolute_error"]).max() <= 1e-6, "conservation error too large")
    require(pd.to_numeric(support["middle_gva_support_rate"]).dropna().le(1 + 1e-9).all(), "support exceeds parent")

    lookup = identity.set_index(["source", "audit_id"])
    kepco_rank = float(lookup.loc[("KEPCO KSIC middle electricity", "median_effective_temporal_rank"), "value"])
    joined_common = float(lookup.loc[("KEPCO-joined Phase34 candidate", "all_joined_industries_identical_profile_group_rate"), "value"])
    nts_rank = float(lookup.loc[("NTS 100 lifestyle industries", "median_effective_temporal_rank"), "value"])
    require(kepco_rank > 1, "KEPCO interaction remains rank one")
    require(joined_common == 0, "common proxy remains in multi-industry joined groups")
    require(nts_rank > 1, "NTS interaction remains rank one")
    require(pd.to_numeric(labels["observed_months"]).eq(36).sum() == 80, "NTS common label count changed")
    require(release["available_by_reference_month_end"].eq("N").all(), "NTS release leakage result changed")
    require(negative["conservation_still_passes"].eq("Y").all(), "negative-control conservation missing")
    require(negative["semantic_alignment_destroyed"].eq("Y").all(), "negative-control semantic warning missing")

    require(status["paid_card_data_used"] is False, "paid card status incorrect")
    require(status["api_key_required_for_completed_experiment"] is False, "API-key status incorrect")
    require(status["full_sigungu_middle_quarter_product_decision"] == "Blocked", "full product must stay blocked")
    require(status["direct_monthly_middle_gva_actual_available"] is False, "direct actual claim leaked")
    require(status["production_use"] is False and status["official_statistics_claim"] is False, "claim guardrails failed")
    report = report_path.read_text(encoding="utf-8")
    require("유료 카드 자료는 수집·사용하지 않았다" in report, "free-data constraint absent from report")
    require("시군구 코드" not in report or "시도" in report, "composite-key context missing")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
