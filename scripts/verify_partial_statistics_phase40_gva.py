from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def main() -> None:
    matrix = pd.read_csv(DATA / "partial_stats_phase40_accuracy_matrix.csv")
    keys = ["industry_level", "time_level", "geo_level"]
    assert len(matrix) == 27 and matrix[keys].drop_duplicates().shape[0] == 27
    assert set(matrix.industry_level) == {"대분류", "중분류", "소분류"}
    assert set(matrix.time_level) == {"연", "분기", "월"}
    assert set(matrix.geo_level) == {"시", "구", "행정동"}
    assert set(matrix.validation_grade) <= {"A", "B", "C", "D"}
    # No quarterly/monthly cell may be promoted using annual spatial evidence.
    assert (matrix[matrix.time_level.isin(["분기", "월"])].validation_grade == "D").all()
    small_city = matrix[(matrix.industry_level == "소분류") & (matrix.time_level == "연") & (matrix.geo_level == "시")].iloc[0]
    assert small_city.validation_grade == "C" and "직접 actual 아님" in small_city.critical_limit

    cube = pd.read_csv(DATA / "partial_stats_phase40_goyang_emd_small_monthly.csv", dtype={"emd_code": str})
    assert cube.emd_code.nunique() == 44 and cube.period.nunique() == 36
    assert cube.small_code.nunique() >= 50 and cube.middle_code.nunique() == 19
    assert (cube.estimated_emd_small_monthly_gva >= 0).all()

    multi = pd.read_csv(DATA / "partial_stats_phase40_manufacturing_multiresolution_cube.csv", low_memory=False)
    combos = multi[["industry_level", "time_level", "geo_level"]].drop_duplicates()
    assert len(combos) == 27
    assert (multi.estimated_gva >= 0).all()
    assert (multi[multi.industry_level.isin(["중분류", "소분류"])].sector_scope.str.contains("manufacturing only")).all()

    checks = pd.read_csv(DATA / "partial_stats_phase40_hierarchy_checks.csv")
    assert set(checks.check) == {
        "small→middle / EMD×month", "EMD→city and small→middle / month",
        "month→quarter / manufacturing", "quarter→official annual GVA / manufacturing",
    }
    assert checks.max_abs_error.max() < 0.001

    external = pd.read_csv(DATA / "partial_stats_phase40_small_external_holdout_summary.csv")
    held = external[external.year.between(2021, 2024)]
    assert set(held.year) == {2021, 2022, 2023, 2024}
    assert (held.factory_mae_pp < held.uniform_mae_pp).all()
    assert (held.factory_better_group_rate > .5).all()

    common = pd.read_csv(DATA / "partial_stats_phase40_common_proxy_audit.csv")
    small_common = common[common.audit == "small profiles within same EMD-middle"].iloc[0]
    assert small_common.identical_rate == 1.0
    assert "no small-specific monthly signal" in small_common.interpretation

    status = json.loads((DATA / "partial_stats_phase40_status.json").read_text(encoding="utf-8"))
    assert status["matrix_cells"] == 27
    assert status["hierarchy_max_abs_error"] < 0.001
    print("phase40 verification: PASS")


if __name__ == "__main__":
    main()
