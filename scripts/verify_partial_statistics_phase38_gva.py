from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def main() -> int:
    final = pd.read_csv(DATA/"partial_stats_phase38_goyang_emd_monthly_gva.csv", dtype={"emd_code":str})
    checks = pd.read_csv(DATA/"partial_stats_phase38_goyang_accounting_checks.csv")
    common = pd.read_csv(DATA/"partial_stats_phase38_goyang_common_proxy_audit.csv")
    holdout = pd.read_csv(DATA/"partial_stats_phase38_goyang_holdout_validation.csv")
    decisions = pd.read_csv(DATA/"partial_stats_phase38_goyang_sector_decision.csv")
    audit = [
        ("row_count", len(final)==44*3*36, len(final)),
        ("current_emd_count", final.emd_code.nunique()==44, final.emd_code.nunique()),
        ("sector_count", final.sector_code.nunique()==3, final.sector_code.nunique()),
        ("month_count", final[["year","month"]].drop_duplicates().shape[0]==36, final[["year","month"]].drop_duplicates().shape[0]),
        ("unique_cells", not final.duplicated(["year","month","sector_code","emd_code"]).any(), int(final.duplicated(["year","month","sector_code","emd_code"]).sum())),
        ("positive_estimates", final.estimated_emd_monthly_gva.gt(0).all(), float(final.estimated_emd_monthly_gva.min())),
        ("accounting", checks.max_abs_error.max()<1e-6, float(checks.max_abs_error.max())),
        ("common_proxy_removed", not common.all_emd_profiles_identical.any(), int(common.all_emd_profiles_identical.sum())),
        ("holdout_models", set(holdout.model)=={"uniform","proxy_current","carry_forward","selected_blend"}, sorted(holdout.model.unique())),
        ("sector_decisions", set(decisions.sector_code)=={"I00","Q00","ERS"}, sorted(decisions.sector_code)),
        ("claim_scope", final.claim_scope.str.contains("not observed EMD GVA",regex=False).all(), final.claim_scope.iloc[0]),
    ]
    table=pd.DataFrame(audit,columns=["check","passed","value"])
    print(table.to_string(index=False))
    return 1 if not table.passed.all() else 0


if __name__ == "__main__":
    raise SystemExit(main())
