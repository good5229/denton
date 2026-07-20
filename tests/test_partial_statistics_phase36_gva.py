import numpy as np

from run_partial_statistics_phase36_gva import generalized_proportional_denton, nts_sector


def test_generalized_denton_hits_quarterly_controls():
    indicator = np.array([8., 10., 12., 13., 11., 9.])
    fitted = generalized_proportional_denton(indicator, np.array([300., 330.]), frequency=3)
    assert np.all(fitted > 0)
    assert np.allclose(fitted.reshape(-1, 3).sum(axis=1), [300., 330.])


def test_nts_bridge_is_explicit_and_drops_total():
    assert nts_sector("한식음식점") == "I00"
    assert nts_sector("치과병원ㆍ의원") == "Q00"
    assert nts_sector("교습소ㆍ공부방") == "P00"
    assert nts_sector("업종전체") is None
