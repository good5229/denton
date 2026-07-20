from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def read(name: str, encoding: str = "utf-8-sig") -> pd.DataFrame:
    return pd.read_csv(DATA / name, encoding=encoding)


def main() -> int:
    registry = read("partial_stats_phase42_pohang_emd_registry.csv")
    population = read("partial_stats_phase42_pohang_emd_population.csv")
    proxy = read("partial_stats_phase42_pohang_emd_monthly_proxy.csv")
    audit = read("partial_stats_phase42_pohang_source_audit.csv")
    kosis = read("partial_stats_phase42_pohang_2015_all_ksic.csv", "cp949")

    assert len(registry) == registry.emd_code.nunique() == 29
    assert set(registry.general_gu) == {"남구", "북구"}
    assert len(population) == 29 and population.population.notna().all() and (population.population > 0).all()
    assert population.emd_code.nunique() == 29
    assert set(kosis.metric) == {"establishments", "employees", "sales"}
    assert set(kosis.c2_nm) == {"포항시"}
    assert kosis.c1_id.astype(str).str.len().isin([1, 2, 3]).all()
    assert len(audit) == 20 and audit.match_rate.between(0, 1).all()
    assert audit.loc[audit.source == "포항시 공장등록현황", "raw_rows"].iat[0] == 1465
    assert proxy.emd_code.nunique() == 29
    assert proxy.period.min() == "2021-01" and proxy.period.max() == "2026-06"
    expected = 29 * proxy.sector_code.nunique() * proxy.period.nunique()
    assert len(proxy) == expected and not proxy.duplicated(["emd_code", "sector_code", "period"]).any()
    assert (proxy[["active_license_stock", "openings", "closures"]] >= 0).all().all()
    print(
        "phase42 source verification: PASS "
        f"emd={len(registry)} kosis_rows={len(kosis)} proxy_rows={len(proxy)} "
        f"geocoded={int(audit.matched_emd_rows.fillna(0).sum())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
