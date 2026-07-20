import numpy as np
import pandas as pd

from run_partial_statistics_phase38_gva import ras_biproportional


def test_ras_hits_both_margins():
    seed=np.array([[2.,3.,5.],[4.,3.,3.]])
    row=np.array([40.,60.])
    col=np.array([20.,30.,50.])
    fitted=ras_biproportional(seed,row,col)
    assert np.allclose(fitted.sum(axis=1),row)
    assert np.allclose(fitted.sum(axis=0),col)
    assert (fitted>0).all()


def test_phase38_output_is_current_44_emd_complete_and_conserved():
    final=pd.read_csv("data/processed/partial_stats_phase38_goyang_emd_monthly_gva.csv",dtype={"emd_code":str})
    checks=pd.read_csv("data/processed/partial_stats_phase38_goyang_accounting_checks.csv")
    assert len(final)==44*3*36
    assert final.emd_code.nunique()==44
    assert set(final.sector_code)=={"I00","Q00","ERS"}
    assert not final.duplicated(["year","month","sector_code","emd_code"]).any()
    assert checks.max_abs_error.max()<1e-6


def test_phase38_removes_common_month_profile_defect_without_overclaim():
    final=pd.read_csv("data/processed/partial_stats_phase38_goyang_emd_monthly_gva.csv")
    common=pd.read_csv("data/processed/partial_stats_phase38_goyang_common_proxy_audit.csv")
    assert not common.all_emd_profiles_identical.any()
    assert common.unique_normalized_profiles.min()>1
    assert final.claim_scope.str.contains("not observed EMD GVA",regex=False).all()


def test_phase38_holdout_is_prospective_and_sector_gated():
    holdout=pd.read_csv("data/processed/partial_stats_phase38_goyang_holdout_validation.csv")
    decision=pd.read_csv("data/processed/partial_stats_phase38_goyang_sector_decision.csv").set_index("sector_code")
    assert holdout.evaluation_year.eq(2023).all()
    assert holdout.split.eq("prospective_holdout").all()
    assert set(holdout.model)=={"uniform","proxy_current","carry_forward","selected_blend"}
    assert decision.loc["I00","output_decision"]=="primary_allocation"
    assert decision.loc["Q00","output_decision"]=="supplementary_allocation"
    assert decision.loc["ERS","output_decision"]=="supplementary_allocation"
