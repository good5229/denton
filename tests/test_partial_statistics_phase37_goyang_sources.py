from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def test_phase37_current_geography_and_panel_are_complete():
    emd = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_current.csv", dtype={"emd_code": str})
    panel = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_industry_monthly_proxy.csv", dtype={"emd_code": str})
    assert emd.emd_code.nunique() == 44
    assert emd.population_2024.notna().all()
    assert len(panel) == 44 * 5 * 66
    assert not panel.duplicated(["emd_code", "sector_code", "period"]).any()


def test_phase37_stock_flow_identity_and_source_geocoding():
    panel = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_industry_monthly_proxy.csv", dtype={"emd_code": str})
    audit = pd.read_csv(DATA / "partial_stats_phase37_goyang_source_audit.csv")
    assert len(audit) == 19
    assert audit.coordinate_match_rate.min() >= 0.79
    for _, group in panel.groupby(["emd_code", "sector_code"]):
        group = group.sort_values("period")
        expected = group.active_license_stock.shift(1) + group.license_openings - group.license_closures
        assert (group.active_license_stock.iloc[1:] == expected.iloc[1:]).all()


def test_phase37_common_proxy_defect_is_not_repeated():
    common = pd.read_csv(DATA / "partial_stats_phase37_goyang_common_proxy_audit.csv")
    assert common.identical_spatial_share.sum() == 0
    assert common.correlation.max() < 0.999


def test_phase37_cross_validation_gates_are_sector_specific():
    gate = pd.read_csv(DATA / "partial_stats_phase37_goyang_sector_use_gate.csv").set_index("sector_code")
    assert gate.loc["I00", "spatial_use_gate"] == "strong"
    assert gate.loc["S00", "spatial_use_gate"] == "strong"
    assert gate.loc["Q00", "spatial_use_gate"] == "supplementary"
    assert gate.loc["R00", "spatial_use_gate"] == "supplementary"
    assert gate.loc["G00", "spatial_use_gate"] == "reject_as_standalone"
