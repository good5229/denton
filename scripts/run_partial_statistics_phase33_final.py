from __future__ import annotations

import subprocess
import sys

from apply_phase33_eligibility import build_eligibility_waterfall
from audit_phase33_industry_dimension import build_industry_dimension_audit
from audit_phase33_rq1 import build_rq1_audit
from build_phase33_canonical_keys import build_ksic_crosswalk, build_period_price_bridge, build_region_crosswalk
from build_phase33_evidence import build_claim_registry, build_event_archive, build_multi_proxy_scorecard
from build_phase33_final_report import build_reports_and_ledgers
from build_phase33_product_a1 import build_product_a1
from build_phase33_product_a2 import build_product_a2
from build_phase33_product_b import build_product_b
from build_phase33_product_c import build_product_c
from build_phase33_public_source_registry import build_source_registry
from build_phase33_sector_presence import build_sector_presence
from calibrate_phase33_reliability import build_reliability_calibration
from evaluate_phase33_product_d import build_product_d
from phase33_common import ROOT, write_csv
from run_phase33_confirmatory import build_confirmatory_scorecard
from verify_phase33_share_lineage import build_share_lineage


def main() -> int:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_partial_statistics_phase32_reci_component_promotion.py")],
        cwd=ROOT,
        check=True,
    )
    write_csv("phase33_source_registry.csv", build_source_registry())
    write_csv("phase33_region_crosswalk.csv", build_region_crosswalk())
    write_csv("phase33_ksic_crosswalk.csv", build_ksic_crosswalk())
    write_csv("phase33_period_price_bridge.csv", build_period_price_bridge())
    write_csv("phase33_product_a1_spatial.csv", build_product_a1())
    write_csv("phase33_sector_vector_audit.csv", build_industry_dimension_audit())
    write_csv("phase33_product_a2_fine_industry.csv", build_product_a2())
    rq1_cardinality, rq1_compatibility = build_rq1_audit()
    write_csv("phase33_rq1_cardinality.csv", rq1_cardinality)
    write_csv("phase33_rq1_compatibility.csv", rq1_compatibility)
    write_csv("phase33_product_b_temporal.csv", build_product_b())
    write_csv("phase33_current_presence_by_sector.csv", build_sector_presence())
    product_c, conservation = build_product_c()
    write_csv("phase33_product_c_allocation.csv", product_c)
    write_csv("phase33_conservation_checks.csv", conservation)
    write_csv("phase33_product_d_joint_pilot.csv", build_product_d())
    write_csv("phase33_eligibility_waterfall.csv", build_eligibility_waterfall())
    write_csv("phase33_share_lineage.csv", build_share_lineage())
    write_csv("phase33_multi_proxy_scorecard.csv", build_multi_proxy_scorecard())
    write_csv("phase33_event_archive.csv", build_event_archive())
    write_csv("phase33_confirmatory_scorecard.csv", build_confirmatory_scorecard())
    write_csv("phase33_reliability_calibration.csv", build_reliability_calibration())
    write_csv("phase33_claim_evidence_registry.csv", build_claim_registry())
    build_reports_and_ledgers()
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_partial_statistics_phase33_final.py")],
        cwd=ROOT,
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
