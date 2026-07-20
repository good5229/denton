from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def main() -> None:
    status = json.loads((DATA / "partial_stats_phase41_status.json").read_text(encoding="utf-8"))
    assert (status["sections"], status["divisions"], status["groups"]) == (19, 74, 228)
    assert status["base_rows"] == 44 * 36 * 228

    base = pd.read_parquet(DATA / "partial_stats_phase41_goyang_emd_group_monthly.parquet")
    assert base.emd_code.nunique() == 44 and base.period.nunique() == 36 and base.group_code.nunique() == 228
    assert not base.estimated_emd_group_monthly_gva.isna().any()
    assert (base.estimated_emd_group_monthly_gva >= 0).all()
    assert set(base.section_code) == set("ABCDEFGHIJKLMNOPQRS")

    multi = pd.read_parquet(DATA / "partial_stats_phase41_all_ksic_multiresolution_cube.parquet")
    combos = multi[["industry_level", "time_level", "geo_level"]].drop_duplicates()
    assert len(combos) == 27
    assert multi.groupby("industry_level").industry_code.nunique().to_dict() == {"대분류": 19, "중분류": 74, "소분류": 228}
    annual_city = multi[(multi.time_level == "연") & (multi.geo_level == "시")]
    assert annual_city.groupby("industry_level").size().to_dict() == {"대분류": 57, "중분류": 222, "소분류": 684}
    monthly_city = multi[(multi.time_level == "월") & (multi.geo_level == "시")]
    totals = monthly_city.groupby(["industry_level", "period"]).estimated_gva.sum().unstack(0)
    assert np.max(np.abs(totals["대분류"]-totals["중분류"])) < 1e-7
    assert np.max(np.abs(totals["중분류"]-totals["소분류"])) < 1e-7

    checks = pd.read_csv(DATA / "partial_stats_phase41_all_ksic_accounting.csv")
    assert checks.max_abs_error.max() < 1e-8
    holdout = pd.read_csv(DATA / "partial_stats_phase41_all_ksic_holdout_summary.csv")
    assert set(holdout.industry_level) == {"middle", "small"}
    assert (holdout.proxy_mae_pp < holdout.uniform_mae_pp).all()
    diagnostics = pd.read_csv(DATA / "partial_stats_phase41_industry_error_diagnostics.csv")
    assert set(diagnostics.industry_level) == {"middle", "small"}
    assert diagnostics.failure_diagnosis.notna().all() and diagnostics.additional_data_needed.notna().all()
    mid_worst = diagnostics[diagnostics.industry_level == "middle"].nlargest(3, "proxy_mae_pp").parent_code.tolist()
    small_worst = diagnostics[diagnostics.industry_level == "small"].nlargest(2, "proxy_mae_pp").parent_code.tolist()
    assert mid_worst == ["F00", "Q00", "H00"]
    assert small_worst == ["L00", "A00"]
    cell_errors = pd.read_csv(DATA / "partial_stats_phase41_industry_cell_errors.csv")
    assert len(cell_errors) == 249 and cell_errors.abs_error_pp.notna().all()

    controls = pd.read_csv(DATA / "partial_stats_phase41_parent_monthly_controls.csv")
    interpolated = controls[controls.control_status == "interpolated_missing_parent_year"]
    assert len(interpolated) == 12 and set(interpolated.gva_parent_code) == {"B00"} and set(interpolated.year) == {2022}

    matrix = pd.read_csv(DATA / "partial_stats_phase41_all_ksic_accuracy_matrix.csv")
    assert len(matrix) == 27
    assert (matrix[matrix.time_level.isin(["분기", "월"])].validation_grade == "D").all()
    common = pd.read_csv(DATA / "partial_stats_phase41_all_ksic_common_proxy_audit.csv")
    assert len(common) == 19 and (common.identical_profile_rate == 1).sum() >= 10
    print("phase41 all-KSIC verification: PASS")


if __name__ == "__main__":
    main()
