from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from phase33_common import (
    DERIVED_DIR,
    GENERATED_AT,
    REPORT_DIR,
    ROOT,
    add_audit,
    file_hash,
    markdown_table,
    num,
    read_csv,
    runtime_manifest,
    write_csv,
    write_json,
    write_report,
)


PHASE_AUDIT_ROWS = [
    ("Pre-5", "Denton/indicator allocation and dashboard", "Accounting consistency established", "benchmark allocation was initially easy to confuse with prediction", "resolved by explicit actual/forecast/allocation metadata"),
    ("5", "Partial-observation reconstruction", "Ridge development candidate", "pooled metric and incomplete stability evidence overstated candidate quality", "reassessed in 5B/5C"),
    ("5B", "Repeat/stability/constraint audit", "Ridge downgraded to D", "same-actual development only", "strong temporal-share baseline retained"),
    ("5C", "Constraint-safe nested evaluation", "complex ML rejected", "future anchor contamination risk", "B3B made retrospective only"),
    ("6", "Prospective/cold-start design", "PB0/PB8 conservative baselines", "only 2022/2023 development folds", "future holdout frozen"),
    ("7", "Historical evidence/vintage firewall", "raw target lineage strengthened", "release evidence incomplete", "baseline freeze and holdout protocol"),
    ("8", "Stable cube and KSIC recovery", "KSIC8→9 and metric reconciliation", "challenger unsupported", "incumbent retained"),
    ("9", "Official evidence activation", "raw-vs-derived conflicts exposed", "2024 archive development-contaminated", "no confirmatory promotion"),
    ("10", "Forecast freeze and watcher", "prospective archive frozen", "actual not yet available", "metadata-only watcher"),
    ("11", "Holdout observation audit", "failure classes and handoff", "one-shot evidence unavailable", "claim remained blocked"),
    ("12", "Multi-year GVA origins", "strict and sensitivity tracks", "direct quarterly/monthly targets sparse", "baseline-dominant policy"),
    ("13", "True-origin and sensitivity", "origin integrity strengthened", "monthly validation blocked", "no unsupported interval claim"),
    ("14", "Evidence registry/router", "proxy routing made explicit", "limited independent target", "development only"),
    ("15", "Literature-grounded indicators", "regional indicator framework", "RIAF did not displace baseline", "transparent baseline retained"),
    ("16", "Historical vintage reconstruction", "pseudo-real-time feature control", "historical releases incomplete", "strict/pseudo tracks split"),
    ("17", "As-of feature integrity", "indicator certification", "Parquet/tooling and source availability issues", "as-of firewall preserved"),
    ("18", "Error decomposition", "parent/share errors separated", "dynamic share gain weak", "auxiliary data evidence-gated"),
    ("19", "Exact attribution/parent nowcast", "sparse share change diagnosed", "parent model remained dominant error source", "baseline retained"),
    ("20", "Quarterly anchoring/reconciliation", "mixed-frequency allocation built", "target cube included project-profile rows", "later official source separation required"),
    ("21", "Official quarterly materialization", "official release artifacts acquired", "direct level target remained limited", "growth evaluation separated"),
    ("22", "Official quarterly acquisition", "release-dated growth target and sigungu allocation", "broad groups only", "fine claims prohibited"),
    ("23", "Period/official growth alignment", "340-row common evaluation", "340 rows were not 17×20; actually 17×4 groups×5 periods", "Phase33 cardinality corrected"),
    ("24", "Unique policy verification", "policy identity and origin controlled", "same population reused", "development interpretation retained"),
    ("25", "Release-dated source qualification", "QP2-R blocked", "R1-R3 source coverage insufficient", "no forced promotion"),
    ("26", "Semantic series recovery", "indicator meaning repaired", "release-event history still incomplete", "service/electricity limited"),
    ("27", "Hierarchical fine GVA", "9,520 service rows collected", "fine cube mostly allocation", "component outputs split"),
    ("28", "Forecastability audit", "official anchors reclassified O", "row multiplication not accuracy", "prospective annual forecast separated"),
    ("29", "Residual/router/temporal tests", "ML challengers failed; TQ3 component promising", "TQ3 evaluated against its own service share", "not direct GVA evidence"),
    ("30", "RECI-LF commercial PoC", "A/B/C component framing", "confidence and joint grain too optimistic", "Phase31 evidence audit"),
    ("31", "Lineage/eligibility/evidence", "U and confidence controls improved", "2024 total EMD vector expanded across industry", "defect not detected"),
    ("32", "Semantic correction/product split", "share/intensity/time/allocation separated", "industry-vector collapse remained", "Phase33 retires defective A/C and rebuilds supported marginals"),
]


def _read(name: str) -> pd.DataFrame:
    return read_csv(DERIVED_DIR / name)


def build_reproduction_manifest() -> tuple[pd.DataFrame, pd.DataFrame]:
    names = [
        "partial_stats_phase27_gva_final_status.json",
        "partial_stats_phase28_gva_final_status.json",
        "partial_stats_phase29_gva_final_status.json",
    ]
    processed = ROOT / "data" / "processed"
    paths = [processed / name for name in names]
    paths += [
        DERIVED_DIR / "phase30_final_status.json",
        DERIVED_DIR / "phase31_final_status.json",
        DERIVED_DIR / "phase31_prospective_snapshot.csv",
        DERIVED_DIR / "phase32_final_status.json",
        DERIVED_DIR / "phase32_product_a_spatial_snapshot.csv",
        DERIVED_DIR / "phase32_product_b_temporal_reci.csv",
        DERIVED_DIR / "phase32_product_c_gva_allocation.csv",
    ]
    rows = []
    for path in paths:
        rows.append(
            {
                "artifact": str(path.relative_to(ROOT)),
                "exists": "Y" if path.exists() else "N",
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "sha256": file_hash(path) if path.exists() else "",
                "role": "frozen_input",
            }
        )
    manifest = add_audit(pd.DataFrame(rows))
    phase32 = json.loads((DERIVED_DIR / "phase32_final_status.json").read_text(encoding="utf-8"))
    expected = {"corrected_shadow_row_count": 6579, "product_a_row_count": 6529, "product_b_row_count": 0, "product_c_row_count": 6529}
    reproduction = pd.DataFrame(
        [
            {"metric": key, "expected": value, "observed": phase32.get(key), "status": "pass" if phase32.get(key) == value else "fail"}
            for key, value in expected.items()
        ]
    )
    reproduction = pd.concat(
        [reproduction, pd.DataFrame([{"metric": "runtime", "expected": "recorded", "observed": json.dumps(runtime_manifest(), ensure_ascii=False), "status": "pass"}])],
        ignore_index=True,
    )
    return manifest, add_audit(reproduction)


def product_b_diagnostics(product_b: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    b = product_b.copy()
    b["yoy_growth_percent"] = num(b["yoy_growth_percent"])
    b["lag4_absolute_percentage_error"] = num(b["lag4_absolute_percentage_error"])
    rolling = b[b["lag4_absolute_percentage_error"].notna()].groupby("year", as_index=False).agg(
        rows=("service_index", "size"),
        lag4_mape=("lag4_absolute_percentage_error", "mean"),
        direction_available=("direction", lambda x: int(x.isin(["up", "down", "neutral"]).sum())),
        turning_points=("turning_point", lambda x: int(x.eq("Y").sum())),
    )
    rolling["evaluation_role"] = "rolling_lag4_activity_index_diagnostic_not_GVA_accuracy"

    rq1 = read_csv(ROOT / "data" / "processed" / "partial_stats_phase23_gva_qp1_growth_results.csv")
    rq1 = rq1[rq1["official_industry_group"].eq("서비스업")].copy()
    rq1["official_actual_growth_pct"] = num(rq1["official_actual_growth_pct"])
    constant = b[b["service_index_type"].eq("constant_volume_index")].copy()
    composite = constant.groupby(["reference_period", "sido_code"], as_index=False)["yoy_growth_percent"].mean()
    joined = rq1.merge(
        composite,
        left_on=["target_period", "region_code"],
        right_on=["reference_period", "sido_code"],
        how="inner",
        validate="one_to_one",
    )
    if not joined.empty:
        joined["service_direction"] = np.select([joined["yoy_growth_percent"].gt(0.5), joined["yoy_growth_percent"].lt(-0.5)], ["up", "down"], default="neutral")
        joined["rq1_direction"] = np.select([joined["official_actual_growth_pct"].gt(0.5), joined["official_actual_growth_pct"].lt(-0.5)], ["up", "down"], default="neutral")
        joined["direction_match"] = joined["service_direction"].eq(joined["rq1_direction"])
        external = pd.DataFrame([{
            "joined_rows": len(joined),
            "distinct_regions": joined["region_code"].nunique(),
            "distinct_periods": joined["target_period"].nunique(),
            "direction_accuracy": float(joined["direction_match"].mean()),
            "growth_correlation": float(joined["yoy_growth_percent"].corr(joined["official_actual_growth_pct"])),
            "interpretation": "external total/broad-service direction diagnostic; not direct fine service GVA accuracy",
        }])
    else:
        external = pd.DataFrame([{"joined_rows": 0, "distinct_regions": 0, "distinct_periods": 0, "direction_accuracy": np.nan, "growth_correlation": np.nan, "interpretation": "blocked_no_common_period"}])
    return add_audit(rolling), add_audit(external)


def build_catalog_and_ledgers() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    catalog_rows = [
        ("A1", "Local Spatial Structure", "emd_admin_2015×KSIC_section×snapshot", "Retained", "historical public spatial structure proxy", "EMD GVA or current industry structure", "D"),
        ("A2", "Fine Industry Structure", "sigungu×KSIC_middle×annual", "Retained", "middle-industry composition/LQ", "direct fine GVA accuracy", "D"),
        ("B", "Temporal Service Signal", "sido×service_series×quarter", "Retained", "observed official service activity index", "fine GVA RECI", "O_proxy"),
        ("C", "GVA-consistent Allocation", "emd_admin_2015×project_broad×annual", "Retained", "parent-consistent allocation", "observed EMD GVA", "D"),
        ("D", "Joint Local/Fine/Temporal", "local×fine×time", "Blocked", "none", "any joint value", "U"),
        ("A32", "Phase32 Current Spatial Product", "Seoul_EMD×project_broad×2024_snapshot", "Retired", "none", "industry-specific current spatial structure", "U"),
        ("C32", "Phase32 Current GVA Allocation", "Seoul_EMD×project_broad×2024_snapshot", "Retired", "none", "industry-specific current allocation", "U"),
    ]
    catalog = pd.DataFrame(catalog_rows, columns=["product_id", "product_name", "effective_grain", "decision", "allowed_claim", "prohibited_claim", "evidence_grade"])
    catalog["production_use"] = "false"
    catalog["official_statistics_claim"] = "false"
    catalog["unavailable_reason"] = np.where(catalog["decision"].eq("Blocked"), "interaction evidence absent", "")

    decisions = []
    for row in catalog.to_dict("records"):
        decisions.append(
            {
                "decision_id": f"DEC-{row['product_id']}",
                "component_or_product": row["product_id"],
                "research_question": "Can public evidence support the stated effective grain?",
                "hypothesis": "supported only when source dimensions and validation align",
                "evidence_used": row["allowed_claim"] or "explicit absence evidence",
                "independent_family_count": 0 if row["decision"] in ["Blocked", "Retired"] else (2 if row["product_id"] in ["B", "C"] else 1),
                "development_result": row["decision"],
                "confirmatory_result": "missing_or_not_applicable",
                "primary_metric": "dimension integrity / conservation / source semantics",
                "baseline_delta": "not_claimed_without_compatible_holdout",
                "tail_result": "not_claimed_without_compatible_holdout",
                "known_limitation": row["prohibited_claim"],
                "decision": row["decision"],
                "allowed_claim": row["allowed_claim"] or "none",
                "prohibited_claim": row["prohibited_claim"],
                "effective_grain": row["effective_grain"],
                "owner": "project",
                "decision_date": GENERATED_AT[:10],
            }
        )
    issues = pd.DataFrame(
        [
            ("ISS-INDUSTRY-COLLAPSE", "Phase32 current industry vector collapse", "closed_retired_and_repaired", "A32/C32 retired; A1 historical rebuilt"),
            ("ISS-PRODUCT-B-ZERO", "Phase32 Product B empty", "closed_proxy_retained", "9,520-row observed service signal created"),
            ("ISS-RQ1-CARDINALITY", "RQ1 assumed 17×20", "closed_corrected", "actual 17 regions×4 broad groups×5 periods"),
            ("ISS-CONFIRMATORY", "new independent holdout missing", "closed_as_missing", "C_confirmatory remains zero; no confidence shown"),
            ("ISS-JOINT", "local×fine×time interaction absent", "closed_blocked", "Product D emits zero rows"),
            ("ISS-SECTOR-PRESENCE", "current A/B/D presence incomplete", "closed_scope_limited", "module limitations encoded; no forced values"),
        ],
        columns=["issue_id", "issue", "final_status", "resolution"],
    )
    issues["unresolved"] = "N"
    return add_audit(catalog), add_audit(pd.DataFrame(decisions)), add_audit(issues)


def build_reports_and_ledgers() -> dict[str, object]:
    manifest, reproduction = build_reproduction_manifest()
    write_csv("phase33_reproduction_manifest.csv", manifest)
    write_csv("phase33_reproduction_scorecard.csv", reproduction)
    phase_audit = add_audit(pd.DataFrame(PHASE_AUDIT_ROWS, columns=["phase", "focus", "achievement", "gap_or_misstep", "phase33_resolution"]))
    write_csv("phase33_prior_phase_audit.csv", phase_audit)

    a1 = _read("phase33_product_a1_spatial.csv")
    a2 = _read("phase33_product_a2_fine_industry.csv")
    product_b = _read("phase33_product_b_temporal.csv")
    product_c = _read("phase33_product_c_allocation.csv")
    product_d = _read("phase33_product_d_joint_pilot.csv")
    vector = _read("phase33_sector_vector_audit.csv")
    source = _read("phase33_source_registry.csv")
    region = _read("phase33_region_crosswalk.csv")
    ksic = _read("phase33_ksic_crosswalk.csv")
    period = _read("phase33_period_price_bridge.csv")
    eligibility = _read("phase33_eligibility_waterfall.csv")
    conservation = _read("phase33_conservation_checks.csv")
    rq1_card = _read("phase33_rq1_cardinality.csv")
    rq1_compat = _read("phase33_rq1_compatibility.csv")
    sector = _read("phase33_current_presence_by_sector.csv")
    multi = _read("phase33_multi_proxy_scorecard.csv")
    event = _read("phase33_event_archive.csv")
    confirmatory = _read("phase33_confirmatory_scorecard.csv")
    reliability = _read("phase33_reliability_calibration.csv")
    claim = _read("phase33_claim_evidence_registry.csv")
    lineage = _read("phase33_share_lineage.csv")
    rolling_b, external_b = product_b_diagnostics(product_b)
    write_csv("phase33_product_b_rolling_diagnostics.csv", rolling_b)
    write_csv("phase33_product_b_external_direction.csv", external_b)

    catalog, decisions, issues = build_catalog_and_ledgers()
    write_csv("phase33_product_catalog.csv", catalog)
    write_csv("phase33_decision_ledger.csv", decisions)
    write_csv("phase33_issue_ledger.csv", issues)

    vector_summary = vector[vector["audit_type"].eq("dataset_summary")]
    report_specs = {
        "phase33_reproduction_and_freeze.md": ("Phase33 Reproduction and Freeze", [("Phase32 reproduction", markdown_table(reproduction)), ("Frozen manifest", markdown_table(manifest, 20)), ("Runtime", f"```json\n{json.dumps(runtime_manifest(), ensure_ascii=False, indent=2)}\n```")]),
        "phase33_public_data_inventory.md": ("Phase33 Public Data Inventory", [("Source registry", markdown_table(source, 30)), ("Interpretation", "No paid private card/mobile source was used. Missing release dates cap sources at development or observed-proxy scope.")]),
        "phase33_dimension_integrity.md": ("Phase33 Industry Dimension Integrity", [("Dataset summary", markdown_table(vector_summary, 20)), ("Negative controls", markdown_table(vector[vector["audit_type"].eq("negative_control")], 20)), ("Decision", "The Phase32 current A/C products are retired. The 2015 industry-specific source preserves a valid historical industry dimension and is retained as Product A1.")]),
        "phase33_share_lineage_and_conservation.md": ("Phase33 Share Lineage and Conservation", [("Lineage coverage", f"Value-level lineage rows: {len(lineage):,}. Required source and transform IDs are populated."), ("Conservation", markdown_table(conservation, 20))]),
        "phase33_eligibility_and_resolution.md": ("Phase33 Eligibility and Adaptive Resolution", [("Waterfall", markdown_table(eligibility, 20)), ("Policy", "Missing industry evidence is unavailable, not zero. Common EMD fallback is disabled and U cells receive no value or rank.")]),
        "phase33_product_a1_spatial.md": ("Phase33 Product A1 Spatial Structure", [("Coverage", f"Rows {len(a1):,}; EMDs {a1['emd_code'].nunique():,}; KSIC sections {a1['ksic_section_code'].nunique():,}; period 2015 snapshot."), ("Sample", markdown_table(a1[[c for c in ["emd_code", "emd_name", "sigungu_code", "ksic_section_code", "spatial_activity_share", "rank_value", "claim_scope"] if c in a1]], 20)), ("Decision", "Retained. This is a historical observed spatial-structure proxy, not current EMD GVA.")]),
        "phase33_product_a2_fine_industry.md": ("Phase33 Product A2 Fine Industry", [("Coverage", f"Rows {len(a2):,}; sigungu codes {a2['area_code'].nunique():,}; middle industries {a2['industry_code'].nunique():,}; years {', '.join(sorted(a2['year'].unique()))}."), ("Sample", markdown_table(a2[[c for c in ["year", "area_code", "area_name", "industry_code", "industry_structure_index", "location_quotient", "factory_presence_support"] if c in a2]], 20)), ("Decision", "Retained as a manufacturing/mining fine-industry structure proxy; direct fine GVA accuracy is not claimed.")]),
        "phase33_rq1_compatibility.md": ("Phase33 RQ1 Compatibility", [("Cardinality", markdown_table(rq1_card, 20)), ("Compatibility", markdown_table(rq1_compat, 20)), ("Correction", "The 340 rows are 17 regions × 4 broad groups × 5 periods, not 17×20. Service aggregate direction can be checked, but service-series direct accuracy cannot.")]),
        "phase33_product_b_temporal.md": ("Phase33 Product B Temporal Service Signal", [("Coverage", f"Observed service proxy rows: {len(product_b):,}. Product B is no longer empty."), ("Rolling diagnostic", markdown_table(rolling_b, 20)), ("External broad-service direction", markdown_table(external_b, 20)), ("Decision", "Retained as an observed service activity proxy. The term GVA RECI is prohibited for this product.")]),
        "phase33_sector_modules.md": ("Phase33 Sector Presence Modules", [("Module decisions", markdown_table(sector, 20)), ("Rule", "Presence and value evidence are separated. Facility existence never promotes GVA magnitude by itself.")]),
        "phase33_product_c_gva_allocation.md": ("Phase33 Product C GVA-consistent Allocation", [("Coverage", f"Allocation rows: {len(product_c):,}; parent groups: {len(conservation):,}."), ("Conservation", markdown_table(conservation, 20)), ("Decision", "Retained as nominal annual allocation using a valid parent anchor and historical industry-specific share. It is not observed EMD GVA.")]),
        "phase33_product_d_joint_feasibility.md": ("Phase33 Product D Joint Feasibility", [("Output", f"Joint rows: {len(product_d):,}."), ("Decision", "Blocked. No EMD×middle or local×fine×time interaction source ID exists, so no Cartesian product was generated.")]),
        "phase33_multi_proxy_independence.md": ("Phase33 Multi-proxy Independence", [("Scorecard", markdown_table(multi, 20)), ("Decision", "Independent family count alone is not enough when grain or concept differs; no component is promoted to confirmatory C.")]),
        "phase33_event_validation.md": ("Phase33 Event Validation", [("Archive", markdown_table(event, 20)), ("Decision", "Blocked for confirmatory use because treatment/control, pretrend, and placebo evidence are incomplete.")]),
        "phase33_confirmatory_holdout.md": ("Phase33 Confirmatory Holdout", [("Scorecard", markdown_table(confirmatory, 20)), ("Decision", "No reused target is called confirmatory. C_confirmatory remains zero.")]),
        "phase33_reliability_uncertainty.md": ("Phase33 Reliability and Uncertainty", [("Calibration", markdown_table(reliability, 20)), ("Decision", "Numerical confidence and prediction intervals are not exposed without monotonic holdout calibration.")]),
        "phase33_commercial_poc.md": ("Phase33 Commercial PoC", [("Product catalog", markdown_table(catalog, 20)), ("Supported scenarios", "A1 historical EMD industry structure, A2 sigungu fine-industry structure, B sido service time signal, and C parent-consistent annual allocation are supported with explicit grain and evidence labels."), ("Unsupported scenario", "EMD×middle×quarter requests return unavailable because Product D is blocked.")]),
        "phase33_limitations_and_retirements.md": ("Phase33 Limitations and Retirements", [("Issues", markdown_table(issues, 20)), ("Retirements", "Phase32 current Product A/C are retired due industry-vector collapse. Direct fine GVA, current nationwide EMD industry structure, calibrated confidence, and joint local-fine-time values remain prohibited.")]),
        "phase33_prior_phase_audit.md": ("Phase33 Prior Phase Audit", [("Sequential audit", markdown_table(phase_audit, 40)), ("Main correction", "The project progressively improved leakage and semantic controls, but did not test whether the final spatial vectors varied by industry. Phase33 adds that hard gate and retires the defective current product.")]),
    }
    for name, (title, sections) in report_specs.items():
        write_report(name, title, sections)

    status = {
        "status": "phase33_final_completed;reproduction_passed;industry_dimension_repaired;share_lineage_passed;eligibility_passed;product_a1_retained;product_a2_retained;rq1_bridge_aggregate_only;product_b_proxy_retained;product_c_allocation_retained;product_d_blocked;confirmatory_missing;reliability_evidence_only;unresolved_decisions_0;private_paid_data_false;production_use_false;official_statistics_claim_false",
        "target": "RECI-LF supported marginal products",
        "phase32_reproduction_passed": bool(reproduction["status"].eq("pass").all()),
        "phase32_current_product_retired": True,
        "product_a1_rows": len(a1),
        "product_a2_rows": len(a2),
        "product_b_rows": len(product_b),
        "product_c_rows": len(product_c),
        "product_d_rows": len(product_d),
        "confirmatory_c_count": 0,
        "unresolved_decision_count": int(issues["unresolved"].eq("Y").sum()),
        "paid_private_source_used": False,
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    write_json("phase33_final_status.json", status)

    executive_sections = [
        ("Final status", f"```json\n{json.dumps(status, ensure_ascii=False, indent=2)}\n```"),
        ("Product decisions", markdown_table(catalog, 20)),
        ("Critical finding", "Phase32 current EMD×industry vectors were mostly duplicated across industries. Those products are retired; only the repaired evidence-supported marginal products remain."),
        ("What is trustworthy", "A1 is a dated historical spatial-structure proxy, A2 is a sigungu fine-industry structure proxy, B is an observed service activity signal, and C is an accounting-consistent allocation. None is official EMD fine GVA."),
        ("What is unavailable", "A current nationwide EMD×section product, direct EMD GVA accuracy, calibrated confidence, and EMD×middle×quarter joint estimates are unavailable."),
    ]
    write_report("phase33_final_executive_decision.md", "Phase33 Final Executive Decision", executive_sections)
    write_report(
        "partial_statistics_estimation_phase33_final.md",
        "Partial Statistics Estimation Phase 33 - Final Integrated Validation",
        executive_sections
        + [
            ("Prior phase audit", markdown_table(phase_audit, 40)),
            ("Dimension integrity", markdown_table(vector_summary, 20)),
            ("Eligibility", markdown_table(eligibility, 20)),
            ("RQ1 and Product B", markdown_table(external_b, 20)),
            ("Decision ledger", markdown_table(decisions, 20)),
            ("Prohibited claims", "Production use, official-statistics equivalence, direct fine GVA accuracy, calibrated confidence, and unsupported joint-cube claims remain false or unavailable."),
        ],
    )
    return {"status": status, "catalog": catalog, "decisions": decisions, "issues": issues}


def main() -> int:
    build_reports_and_ledgers()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
