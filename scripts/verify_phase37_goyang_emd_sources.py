from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def correlation(left: pd.Series, right: pd.Series) -> float:
    if left.nunique() < 2 or right.nunique() < 2:
        return float("nan")
    return float(left.corr(right))


def main() -> int:
    panel = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_industry_monthly_proxy.csv", dtype={"emd_code": str})
    actual = pd.read_csv(DATA / "partial_stats_phase37_goyang_gu_industry_annual_actual.csv")
    actual["panel_sector_code"] = actual["sector_code"].astype(str) + "00"
    audit = pd.read_csv(DATA / "partial_stats_phase37_goyang_source_audit.csv")
    emd = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_current.csv", dtype={"emd_code": str})

    checks: list[dict[str, object]] = []
    checks.append({"check": "current_emd_count", "value": emd.emd_code.nunique(), "threshold": 44, "passed": emd.emd_code.nunique() == 44})
    checks.append({"check": "population_complete", "value": int(emd.population_2024.notna().sum()), "threshold": 44, "passed": emd.population_2024.notna().all()})
    checks.append({"check": "source_count", "value": len(audit), "threshold": 19, "passed": len(audit) == 19})
    checks.append({"check": "minimum_source_coordinate_match_rate", "value": audit.coordinate_match_rate.min(), "threshold": 0.79, "passed": audit.coordinate_match_rate.min() >= 0.79})
    checks.append({"check": "monthly_panel_complete", "value": len(panel), "threshold": 44 * 5 * 66, "passed": len(panel) == 44 * 5 * 66})

    continuity_failures = 0
    for _, group in panel.groupby(["emd_code", "sector_code"], observed=True):
        group = group.sort_values("period")
        expected = group.active_license_stock.shift(1) + group.license_openings - group.license_closures
        continuity_failures += int((group.active_license_stock.iloc[1:] != expected.iloc[1:]).sum())
    checks.append({"check": "stock_flow_identity_failures", "value": continuity_failures, "threshold": 0, "passed": continuity_failures == 0})

    actual_detail = actual[(actual.general_gu != "합계") & (actual.metric == "establishments")]
    actual_total = actual[(actual.general_gu == "합계") & (actual.metric == "establishments")]
    reconciled = actual_detail.groupby(["year", "sector_code"], as_index=False).value.sum().merge(
        actual_total[["year", "sector_code", "value"]], on=["year", "sector_code"], suffixes=("_gu_sum", "_city")
    )
    max_margin_error = (reconciled.value_gu_sum - reconciled.value_city).abs().max()
    checks.append({"check": "kosis_gu_to_city_max_abs_error", "value": max_margin_error, "threshold": 0, "passed": max_margin_error == 0})

    spatial_rows = []
    target_sectors = sorted(set(panel.sector_code) & set(actual.panel_sector_code))
    for year in (2021, 2022, 2023):
        proxy = panel[panel.period == f"{year}-12"].groupby(["general_gu", "sector_code"], as_index=False).active_license_stock.sum()
        truth = actual_detail[actual_detail.year == year][["general_gu", "panel_sector_code", "value"]].rename(
            columns={"panel_sector_code": "sector_code"}
        )
        merged = proxy.merge(truth, on=["general_gu", "sector_code"])
        for sector in target_sectors:
            group = merged[merged.sector_code == sector].copy()
            group["proxy_share"] = group.active_license_stock / group.active_license_stock.sum()
            group["actual_share"] = group.value / group.value.sum()
            spatial_rows.append(
                {
                    "year": year,
                    "sector_code": sector,
                    "gu_share_mae_pp": float((group.proxy_share - group.actual_share).abs().mean() * 100),
                    "gu_share_correlation": correlation(group.proxy_share, group.actual_share),
                    "top_gu_match": group.loc[group.proxy_share.idxmax(), "general_gu"] == group.loc[group.actual_share.idxmax(), "general_gu"],
                    "license_coverage_ratio": float(group.active_license_stock.sum() / group.value.sum()) if group.value.sum() else np.nan,
                }
            )
    spatial = pd.DataFrame(spatial_rows)
    spatial.to_csv(DATA / "partial_stats_phase37_goyang_spatial_cross_validation.csv", index=False)
    sector_gate = spatial.groupby("sector_code", as_index=False).agg(
        mean_gu_share_mae_pp=("gu_share_mae_pp", "mean"),
        mean_gu_share_correlation=("gu_share_correlation", "mean"),
        mean_license_coverage_ratio=("license_coverage_ratio", "mean"),
        top_gu_match_rate=("top_gu_match", "mean"),
    )
    sector_gate["spatial_use_gate"] = np.select(
        [
            (sector_gate.mean_gu_share_mae_pp <= 1) & (sector_gate.mean_gu_share_correlation >= 0.95),
            (sector_gate.mean_gu_share_mae_pp <= 5) & (sector_gate.mean_gu_share_correlation >= 0.80),
        ],
        ["strong", "supplementary"],
        default="reject_as_standalone",
    )
    sector_gate.to_csv(DATA / "partial_stats_phase37_goyang_sector_use_gate.csv", index=False)

    proxy_city = panel[panel.period.str.endswith("-12")].groupby(["period", "sector_code"], as_index=False).active_license_stock.sum()
    proxy_city["year"] = proxy_city.period.str[:4].astype(int)
    truth_city = actual[(actual.general_gu == "합계") & (actual.metric == "establishments")][
        ["year", "panel_sector_code", "value"]
    ].rename(columns={"panel_sector_code": "sector_code", "value": "actual_establishments"})
    temporal = proxy_city.merge(truth_city, on=["year", "sector_code"]).sort_values(["sector_code", "year"])
    temporal["proxy_growth_pct"] = temporal.groupby("sector_code").active_license_stock.pct_change(fill_method=None) * 100
    temporal["actual_growth_pct"] = temporal.groupby("sector_code").actual_establishments.pct_change(fill_method=None) * 100
    temporal["growth_abs_error_pp"] = (temporal.proxy_growth_pct - temporal.actual_growth_pct).abs()
    temporal["growth_direction_match"] = np.sign(temporal.proxy_growth_pct) == np.sign(temporal.actual_growth_pct)
    temporal.to_csv(DATA / "partial_stats_phase37_goyang_temporal_cross_validation.csv", index=False)

    common_rows = []
    exact_equal_pairs = 0
    max_corr = -1.0
    for period, month in panel.groupby("period"):
        pivot = month.pivot(index="emd_code", columns="sector_code", values="active_license_stock").astype(float)
        shares = pivot.div(pivot.sum(axis=0), axis=1)
        for left, right in combinations(shares.columns, 2):
            exact = bool(np.allclose(shares[left], shares[right], rtol=0, atol=1e-12))
            corr = correlation(shares[left], shares[right])
            exact_equal_pairs += int(exact)
            if not np.isnan(corr):
                max_corr = max(max_corr, corr)
            common_rows.append({"period": period, "sector_left": left, "sector_right": right, "identical_spatial_share": exact, "correlation": corr})
    common = pd.DataFrame(common_rows)
    common.to_csv(DATA / "partial_stats_phase37_goyang_common_proxy_audit.csv", index=False)
    checks.append({"check": "identical_cross_sector_spatial_share_pairs", "value": exact_equal_pairs, "threshold": 0, "passed": exact_equal_pairs == 0})
    checks.append({"check": "maximum_cross_sector_spatial_share_correlation", "value": max_corr, "threshold": 0.999, "passed": max_corr < 0.999})

    profiles = []
    for sector, group in panel.groupby("sector_code"):
        pivot = group.pivot(index="emd_code", columns="period", values="active_license_stock")
        profiles.append(
            {
                "sector_code": sector,
                "emd_count": len(pivot),
                "unique_monthly_stock_profiles": len(pivot.drop_duplicates()),
                "nonzero_emd_count": int((pivot.max(axis=1) > 0).sum()),
            }
        )
    pd.DataFrame(profiles).to_csv(DATA / "partial_stats_phase37_goyang_profile_diversity.csv", index=False)
    pd.DataFrame(checks).to_csv(DATA / "partial_stats_phase37_goyang_verification.csv", index=False)

    failed = [row for row in checks if not row["passed"]]
    print(pd.DataFrame(checks).to_string(index=False))
    print("\nspatial validation summary")
    print(spatial.groupby("sector_code")[["gu_share_mae_pp", "gu_share_correlation", "license_coverage_ratio"]].mean().to_string())
    print("\nsector use gate")
    print(sector_gate.to_string(index=False))
    print(f"failed checks: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
