from __future__ import annotations

from pathlib import Path

import pandas as pd

from phase33_common import PROCESSED_DIR, add_audit, read_csv, read_table, write_csv


def _rows(path: Path) -> int:
    frame = read_table(path)
    return len(frame)


def build_sector_presence() -> pd.DataFrame:
    specs = [
        ("A", "농림어업", "emd_economic_census_2015.csv", "economic_census_2015", "historical EMD presence only", "Retained", "current national EMD facility evidence missing"),
        ("B", "광업", "business_employment_feature_table.csv", "manufacturing_mining_sigungu_ksic", "2021-2023 sigungu business/employment presence", "Retained", "mine operation/location status not independently verified"),
        ("C", "제조업", "factory_feature_table.csv", "factory_admin_snapshot", "factory broad presence plus business/employment", "Retained", "factory snapshot does not measure output or fine composition"),
        ("D", "전기·가스", "municipality_electricity_feature_cube.csv", "kepco_admin", "electricity use diagnostic when local artifact exists", "Blocked", "generation facility/output attribution evidence incomplete"),
        ("F", "건설", "buildinghub_feature_table.csv", "buildinghub_admin", "building permit/start/approval pilot", "Retained", "publication lag and national historical coverage incomplete"),
        ("SERVICE", "서비스업", "partial_stats_phase27_gva_service_full_cube.parquet", "service_production_index", "official sido×service-series quarterly activity", "Retained", "does not identify EMD or sigungu current presence"),
    ]
    rows = []
    for code, name, filename, family, evidence, decision, limitation in specs:
        path = PROCESSED_DIR / filename
        exists = path.exists()
        rows.append(
            {
                "sector_module": code,
                "sector_name": name,
                "source_family_id": family,
                "local_source": filename,
                "source_available": "Y" if exists else "N",
                "source_row_count": _rows(path) if exists else 0,
                "presence_evidence": evidence if exists else "missing_local_artifact",
                "value_evidence": "not_established_by_presence_source",
                "independent_presence_family_count": 1 if exists else 0,
                "module_decision": decision if exists or decision == "Blocked" else "Blocked",
                "known_limitation": limitation,
                "production_use": "false",
                "official_statistics_claim": "false",
            }
        )
    return add_audit(pd.DataFrame(rows))


def main() -> int:
    write_csv("phase33_current_presence_by_sector.csv", build_sector_presence())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
