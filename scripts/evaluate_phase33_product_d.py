from __future__ import annotations

import pandas as pd

from phase33_common import add_audit, write_csv


COLUMNS = [
    "reference_period", "emd_code", "ksic_middle_code", "quarter", "interaction_source_id",
    "joint_value", "joint_coverage", "evidence_grade", "claim_scope", "unavailable_reason",
    "production_use", "official_statistics_claim",
]


def build_product_d() -> pd.DataFrame:
    return add_audit(pd.DataFrame(columns=COLUMNS))


def main() -> int:
    write_csv("phase33_product_d_joint_pilot.csv", build_product_d())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
