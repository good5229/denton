from __future__ import annotations

import pandas as pd

from phase33_common import DERIVED_DIR, add_audit, read_csv, write_csv


def build_multi_proxy_scorecard() -> pd.DataFrame:
    rows = [
        ("A1", "business_count;employee_count", "economic_census_2015", 1, "same census family", "composition agreement descriptive only", "Retained"),
        ("A2_all", "business_count;employee_count", "manufacturing_mining_sigungu_ksic", 1, "same KOSIS table family", "no independent fine composition target", "Retained"),
        ("A2_manufacturing_presence", "business/employment;factory", "manufacturing_mining_sigungu_ksic;factory_admin_snapshot", 2, "independent broad presence only", "factory cannot validate middle-industry shares", "Retained"),
        ("B", "service_index;RQ1_service_growth", "service_production_index;official_quarterly_grdp_release", 2, "independent but semantic mismatch", "external direction diagnostic only", "Retained"),
        ("C", "A1_share;official_sigungu_GVA", "economic_census_2015;official_sigungu_GVA", 2, "independent accounting inputs", "no direct EMD GVA accuracy target", "Retained"),
        ("D", "none", "none", 0, "interaction source absent", "no joint rows generated", "Blocked"),
    ]
    frame = pd.DataFrame(rows, columns=["product_id", "sources", "source_families", "independent_family_count", "independence_interpretation", "validation_scope", "decision"])
    frame["c_promotion_allowed"] = "N"
    frame["leave_one_family_out_status"] = "not_identified_for_C_promotion"
    return add_audit(frame)


def build_event_archive() -> pd.DataFrame:
    phase32 = read_csv(DERIVED_DIR / "phase32_event_archive.csv")
    rows = []
    if not phase32.empty:
        for row in phase32.to_dict("records"):
            rows.append(
                {
                    "event_id": row.get("event_id", row.get("event_family", "phase32_event")),
                    "event_family": row.get("event_family", "unknown"),
                    "announcement_date": row.get("announcement_date", ""),
                    "operation_date": row.get("operation_date", ""),
                    "treatment_definition": row.get("treatment_definition", ""),
                    "control_definition": row.get("control_definition", ""),
                    "pretrend_status": row.get("pretrend_status", "missing"),
                    "placebo_status": row.get("placebo_status", "missing"),
                    "validation_status": "Blocked_no_control_or_pretrend",
                    "claim_use": "none_confirmatory",
                }
            )
    if not rows:
        rows = [
            {"event_id": "buildinghub_pilot", "event_family": "building_permit_start_approval", "announcement_date": "", "operation_date": "event_fields_separated_in_prior_phase", "treatment_definition": "pilot_only", "control_definition": "", "pretrend_status": "missing", "placebo_status": "missing", "validation_status": "Blocked_no_control_or_pretrend", "claim_use": "none_confirmatory"},
            {"event_id": "factory_snapshot", "event_family": "factory_open_close", "announcement_date": "", "operation_date": "missing", "treatment_definition": "", "control_definition": "", "pretrend_status": "missing", "placebo_status": "missing", "validation_status": "Blocked_snapshot_not_event_history", "claim_use": "none_confirmatory"},
        ]
    return add_audit(pd.DataFrame(rows))


def build_claim_registry() -> pd.DataFrame:
    rows = [
        ("EV-A1-2015", "A1", "economic_census_2015", "emd×KSIC_section×2015_snapshot", "historical observed spatial structure proxy", "D", "Retained", "new independent holdout missing"),
        ("EV-A2-2021-2023", "A2", "manufacturing_mining_sigungu_ksic", "sigungu×KSIC_middle×annual", "fine industry composition proxy", "D", "Retained", "coverage manufacturing/mining; related family"),
        ("EV-B-SERVICE", "B", "service_production_index", "sido×service_series×quarter", "observed service activity signal", "O_proxy", "Retained", "not GVA RECI"),
        ("EV-C-ALLOCATION", "C", "official_sigungu_GVA+economic_census_2015", "emd×broad×annual", "GVA-consistent allocation", "D", "Retained", "historical share and no direct EMD GVA holdout"),
        ("EV-D-BLOCK", "D", "none", "local×fine×time", "unavailable", "U", "Blocked", "interaction evidence absent"),
    ]
    frame = pd.DataFrame(rows, columns=["evidence_id", "product_id", "source_family_id", "validated_grain", "claim_scope", "evidence_grade", "decision", "known_limitation"])
    frame["development_or_confirmatory"] = "development_or_observed_proxy"
    frame["confirmatory_reuse"] = "N"
    frame["production_use"] = "false"
    frame["official_statistics_claim"] = "false"
    return add_audit(frame)


def main() -> int:
    write_csv("phase33_multi_proxy_scorecard.csv", build_multi_proxy_scorecard())
    write_csv("phase33_event_archive.csv", build_event_archive())
    write_csv("phase33_claim_evidence_registry.csv", build_claim_registry())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
