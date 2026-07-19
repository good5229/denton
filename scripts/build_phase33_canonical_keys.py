from __future__ import annotations

import pandas as pd

from phase33_common import DERIVED_DIR, PROCESSED_DIR, add_audit, num, read_csv, read_table, write_csv


def build_region_crosswalk() -> pd.DataFrame:
    census = read_csv(PROCESSED_DIR / "emd_economic_census_2015.csv")
    census = census[census["c2_id"].str.len().eq(7)][["c2_id", "c2_nm"]].drop_duplicates()
    census = census.rename(columns={"c2_id": "region_code", "c2_nm": "region_name"})
    census["region_level"] = "admin_dong"
    census["code_system"] = "KOSIS_2015_admin_dong"
    census["boundary_version"] = "2015"
    census["sigungu_code"] = census["region_code"].str[:5]
    census["legal_admin_distinction"] = "administrative_dong"
    census["mapping_status"] = "canonical_historical"

    seoul = read_csv(PROCESSED_DIR / "seoul_emd_business_proxy_2024.csv")
    seoul = seoul[seoul["admin_level"].eq("emd") & seoul["emd_code_2024"].ne("")][
        ["emd_code_2024", "area_name", "sigungu_code"]
    ].drop_duplicates()
    seoul = seoul.rename(columns={"emd_code_2024": "region_code", "area_name": "region_name"})
    seoul["region_level"] = "admin_dong"
    seoul["code_system"] = "Seoul_2024_admin_dong"
    seoul["boundary_version"] = "2024"
    seoul["legal_admin_distinction"] = "administrative_dong"
    seoul["mapping_status"] = "canonical_current_seoul"
    columns = ["region_code", "region_name", "region_level", "code_system", "boundary_version", "sigungu_code", "legal_admin_distinction", "mapping_status"]
    return add_audit(pd.concat([census[columns], seoul[columns]], ignore_index=True).drop_duplicates())


def _normalize_crosswalk(frame: pd.DataFrame, pair: str, source_file: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame([{"version_pair": pair, "source_file": source_file, "source_code": "", "target_code": "", "relationship_type": "missing_local_source", "mapping_status": "blocked"}])
    columns = list(frame.columns)
    source_col = next((c for c in ["source_code", "ksic8_code", "ksic9_code", "ksic10_code"] if c in columns), columns[0])
    target_col = next((c for c in ["target_code", "ksic9_code", "ksic10_code", "ksic11_code"] if c in columns and c != source_col), columns[min(1, len(columns) - 1)])
    out = frame[[source_col, target_col]].astype(str).drop_duplicates().rename(columns={source_col: "source_code", target_col: "target_code"})
    out["version_pair"] = pair
    out["source_file"] = source_file
    source_counts = out.groupby("source_code")["target_code"].transform("nunique")
    target_counts = out.groupby("target_code")["source_code"].transform("nunique")
    out["relationship_type"] = "one_to_one"
    out.loc[source_counts.gt(1), "relationship_type"] = "one_to_many_split"
    out.loc[target_counts.gt(1), "relationship_type"] = "many_to_one_merge"
    out.loc[source_counts.gt(1) & target_counts.gt(1), "relationship_type"] = "many_to_many"
    out["mapping_status"] = "official_crosswalk_record"
    return out[["version_pair", "source_file", "source_code", "target_code", "relationship_type", "mapping_status"]]


def build_ksic_crosswalk() -> pd.DataFrame:
    specs = [
        ("8_to_9", "ksic8_9_official_crosswalk_phase5.csv"),
        ("9_to_10", "ksic9_10_official_crosswalk.csv"),
        ("10_to_11", "ksic10_11_official_crosswalk.csv"),
    ]
    frames = [_normalize_crosswalk(read_csv(PROCESSED_DIR / name), pair, name) for pair, name in specs]
    return add_audit(pd.concat(frames, ignore_index=True))


def build_period_price_bridge() -> pd.DataFrame:
    current = DERIVED_DIR / "phase33_service_source_current.parquet"
    service = read_table(current if current.exists() else PROCESSED_DIR / "partial_stats_phase27_gva_service_full_cube.parquet")
    periods = service[["prd_de"]].drop_duplicates().rename(columns={"prd_de": "source_period"})
    periods["year"] = periods["source_period"].str[:4]
    periods["quarter"] = periods["source_period"].str[-2:].astype(int)
    periods["canonical_period"] = periods["year"] + "Q" + periods["quarter"].astype(str)
    periods["period_type"] = "calendar_quarter"
    periods["value_concept"] = "index_level"
    periods["nominal_real"] = "current_price_activity_index_not_GVA"
    periods["price_base_year"] = "2020=100"
    periods["seasonally_adjusted"] = "N"
    periods["release_vintage"] = "current_snapshot_release_archive_missing"
    periods["mapping_status"] = "mapped"
    return add_audit(periods)


def main() -> int:
    write_csv("phase33_region_crosswalk.csv", build_region_crosswalk())
    write_csv("phase33_ksic_crosswalk.csv", build_ksic_crosswalk())
    write_csv("phase33_period_price_bridge.csv", build_period_price_bridge())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
