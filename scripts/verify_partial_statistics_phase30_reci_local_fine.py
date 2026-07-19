from __future__ import annotations

import json
import re

import pandas as pd

from kosis_common import CSV_ENCODING, ROOT


DERIVED_DIR = ROOT / "data" / "derived"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def csv(name: str) -> pd.DataFrame:
    path = DERIVED_DIR / name
    require(path.exists(), f"missing artifact: {name}")
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def main() -> int:
    final = json.loads((DERIVED_DIR / "phase30_final_status.json").read_text(encoding="utf-8"))
    require(final["target"] == "RECI-LF", "target mismatch")
    require(final["phase29_reproduction_status"] == "pass", "Phase29 reproduction failed")
    require(final["production_use"] is False and final["official_statistics_claim"] is False, "forbidden claim")
    require(final["paid_private_source_used"] is False, "paid private source used")
    require(final["grade_a_for_emd_fine_count"] == 0, "EMD fine Grade A violation")
    require(final["u_value_violation_count"] == 0, "U rows should not have values")

    claim = csv("phase30_claim_grade.csv")
    require(set(claim["claim_grade"]) == {"O", "A", "B", "C", "D", "E", "U"}, "claim grades incomplete")
    require(claim[claim["claim_grade"].eq("A")]["allowed_for_emd_fine_reci"].iloc[0] == "N", "Grade A allowed incorrectly")

    resolution = csv("phase30_adaptive_resolution_rules.csv")
    require({"region", "industry", "time"}.issubset(set(resolution["axis"])), "adaptive resolution axes incomplete")

    ledger = csv("phase30_source_release_ledger.csv")
    require(len(ledger) >= 8, "source ledger too small")
    require(ledger["evidence_grade"].isin(["R1", "R2", "R3", "R4", "R5"]).all(), "invalid evidence grade")

    paid = csv("phase30_paid_private_source_exclusion_log.csv")
    require(paid["status"].eq("excluded").all(), "paid source exclusion failed")

    pre2020 = csv("phase30_pre2020_gva_audit.csv")
    require("reference_or_proxy_only_not_official_actual" in set(pre2020["use_policy"]) or "no_pre2020_rows" in set(pre2020["use_policy"]), "pre-2020 audit missing policy")

    spatial = csv("phase30_spatial_component_scorecard.csv")
    require("S0_previous_sigungu_share" in set(spatial["component_id"]), "spatial S0 missing")

    temporal = csv("phase30_temporal_component_scorecard.csv")
    tq3 = temporal[temporal["component_id"].eq("TQ3_service_prior_profile")].iloc[0]
    require(tq3["selection_status"] == "development_component_improved_not_promoted_to_direct_gva", "TQ3 status mismatch")

    withheld = csv("phase30_withheld_proxy_scorecard.csv")
    require(withheld["generation_proxy_family"].ne(withheld["withheld_proxy_family"]).all(), "proxy family leakage")

    shadow = csv("phase30_reci_local_fine_shadow.csv")
    require(len(shadow) == final["shadow_row_count"], "shadow row count mismatch")
    require(shadow["production_use"].eq("false").all(), "shadow production use violation")
    require(shadow["official_statistics_claim"].eq("false").all(), "shadow official claim violation")
    require(~shadow["claim_grade"].eq("A").any(), "shadow Grade A violation")
    require(shadow[shadow["claim_grade"].eq("U")]["reci_index"].eq("").all(), "U rows should be value-empty")
    require(shadow["direct_actual_available"].eq("N").all(), "lower direct actual should be unavailable")

    reports = [
        "partial_statistics_estimation_phase30_reci_local_fine.md",
        "phase30_public_data_readiness.md",
        "phase30_spatial_downscaling_validation.md",
        "phase30_industry_downscaling_validation.md",
        "phase30_temporal_component_validation.md",
        "phase30_external_validation.md",
        "phase30_poc_claim_and_confidence.md",
    ]
    for report_name in reports:
        path = ROOT / "reports" / report_name
        require(path.exists(), f"missing report: {report_name}")
    main_report = (ROOT / "reports" / "partial_statistics_estimation_phase30_reci_local_fine.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", main_report, flags=re.MULTILINE)]
    require(sections == list(range(1, 9)), "main report sections must be 1..8")
    for phrase in ["RECI-LF", "Claim Grade", "Final Status", "아직 주장할 수 없는 내용"]:
        require(phrase in main_report, f"main report missing phrase: {phrase}")

    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
