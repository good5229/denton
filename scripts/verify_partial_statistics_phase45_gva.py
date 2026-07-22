from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def main() -> int:
    status = json.loads((DATA / "partial_stats_phase45_pohang_status.json").read_text())
    base = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_emd_small_monthly.parquet")
    cube = pd.read_parquet(DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet")
    checks = pd.read_csv(DATA / "partial_stats_phase45_pohang_final_accounting.csv", encoding="utf-8-sig")
    common = pd.read_csv(DATA / "partial_stats_phase45_pohang_final_common_proxy_audit.csv", encoding="utf-8-sig")
    diagnostics = pd.read_csv(DATA / "partial_stats_phase45_pohang_final_industry_diagnostics.csv", encoding="utf-8-sig")
    assert (status["emd"], status["months"], status["sections"], status["divisions"], status["groups"]) == (29, 36, 19, 74, 228)
    assert not base.duplicated(["period", "emd_code", "group_code"]).any()
    assert set(cube.geo_level) == {"시", "구", "읍면동"} and set(cube.time_level) == {"연", "분기", "월"}
    assert set(cube.industry_level) == {"대분류", "중분류", "소분류"}
    assert cube[["geo_level", "time_level", "industry_level"]].drop_duplicates().shape[0] == 27
    assert checks.max_abs_error.max() < 1e-6
    assert status["full_replication_sections"] == 4 and common.section_code.nunique() == 19
    replicated = set(common.loc[common.identical_profile_rate.eq(1), "section_code"])
    assert replicated == {"B", "D", "F", "O"}
    assert {"예측 양호", "예측 보통", "예측 취약"} <= set(diagnostics.prediction_group)
    group_to_parent = (
        base[["group_code", "division_code", "division_name", "section_code"]]
        .drop_duplicates()
        .rename(columns={"group_code": "industry_code"})
    )
    small = cube[cube.industry_level.eq("소분류")].merge(group_to_parent, on="industry_code")
    middle_from_small = (
        small.groupby(["geo_level", "geo_code", "time_level", "period", "division_code"], as_index=False)
        .estimated_gva.sum()
        .rename(columns={"division_code": "industry_code", "estimated_gva": "from_child"})
    )
    middle = cube[cube.industry_level.eq("중분류")][["geo_level", "geo_code", "time_level", "period", "industry_code", "estimated_gva"]]
    diff = middle.merge(middle_from_small, on=["geo_level", "geo_code", "time_level", "period", "industry_code"])
    assert (diff.estimated_gva - diff.from_child).abs().max() < 1e-6
    division_to_section = base[["division_code", "section_code"]].drop_duplicates().rename(columns={"division_code": "industry_code"})
    middle_with_section = middle.merge(division_to_section, on="industry_code")
    section_from_middle = (
        middle_with_section.groupby(["geo_level", "geo_code", "time_level", "period", "section_code"], as_index=False)
        .estimated_gva.sum()
        .rename(columns={"section_code": "industry_code", "estimated_gva": "from_child"})
    )
    section = cube[cube.industry_level.eq("대분류")][["geo_level", "geo_code", "time_level", "period", "industry_code", "estimated_gva"]]
    diff = section.merge(section_from_middle, on=["geo_level", "geo_code", "time_level", "period", "industry_code"])
    assert (diff.estimated_gva - diff.from_child).abs().max() < 1e-6
    emd_to_gu = base[["emd_code", "general_gu"]].drop_duplicates().rename(columns={"emd_code": "geo_code"})
    emd_month_small = cube[(cube.geo_level.eq("읍면동")) & (cube.time_level.eq("월")) & (cube.industry_level.eq("소분류"))]
    gu_from_emd = (
        emd_month_small.merge(emd_to_gu, on="geo_code").assign(geo_code=lambda df: df.general_gu)
        .groupby(["period", "industry_code", "geo_code"], as_index=False).estimated_gva.sum()
        .rename(columns={"estimated_gva": "from_child"})
    )
    gu_month_small = cube[(cube.geo_level.eq("구")) & (cube.time_level.eq("월")) & (cube.industry_level.eq("소분류"))][["period", "industry_code", "geo_code", "estimated_gva"]]
    diff = gu_month_small.merge(gu_from_emd, on=["period", "industry_code", "geo_code"])
    assert (diff.estimated_gva - diff.from_child).abs().max() < 1e-6
    month = cube[(cube.geo_level.eq("시")) & (cube.time_level.eq("월")) & (cube.industry_level.eq("대분류"))]
    quarter_from_month = (
        month.groupby(["year", "quarter", "industry_code"], as_index=False).estimated_gva.sum()
        .rename(columns={"estimated_gva": "from_child"})
    )
    quarter = cube[(cube.geo_level.eq("시")) & (cube.time_level.eq("분기")) & (cube.industry_level.eq("대분류"))]
    diff = quarter[["year", "quarter", "industry_code", "estimated_gva"]].merge(quarter_from_month, on=["year", "quarter", "industry_code"])
    assert (diff.estimated_gva - diff.from_child).abs().max() < 1e-6
    print(f"phase45 final verification: PASS base={len(base)} cube={len(cube)} accounting={checks.max_abs_error.max():.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
