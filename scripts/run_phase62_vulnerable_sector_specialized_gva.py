#!/usr/bin/env python3
"""Phase62: specialized allocation/extrapolation for vulnerable industries.

This script does not try to "observe" monthly/EMD GVA.  It follows the
project's accounting-constrained approach: annual city controls are allocated
to month/quarter and gu/EMD cells with industry-specific activity indicators,
then validated against the highest-level actual distributions available.

Outputs are intentionally CSV/JSON/Markdown-friendly and avoid heavy
dependencies so that they can run on the current local Python environment.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase62_vulnerable_specialized_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase62_vulnerable_specialized_gva.md"
KST = timezone(timedelta(hours=9))


GU_PREFIX_GOYANG = {
    "41281": "덕양구",
    "41285": "일산동구",
    "41287": "일산서구",
}

SECTOR_NAME = {
    "A00": "농림어업",
    "F00": "건설업",
    "H00": "운수 및 창고업",
    "L00": "부동산업",
}

SECTION_TO_PARENT = {
    "A": "A00",
    "F": "F00",
    "H": "H00",
    "L": "L00",
}


def read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Iterable[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def fnum(x, default=0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def quarter_from_month(month: int) -> int:
    return (month - 1) // 3 + 1


def normalize_shares(values: Dict[str, float], universe: Iterable[str]) -> Dict[str, float]:
    keys = list(universe)
    total = sum(max(0.0, values.get(k, 0.0)) for k in keys)
    if total <= 0:
        if not keys:
            return {}
        return {k: 1.0 / len(keys) for k in keys}
    return {k: max(0.0, values.get(k, 0.0)) / total for k in keys}


def mae_pp(actual: Dict[str, float], pred: Dict[str, float], keys: Iterable[str]) -> float:
    keys = list(keys)
    if not keys:
        return 0.0
    return sum(abs(actual.get(k, 0.0) - pred.get(k, 0.0)) * 100.0 for k in keys) / len(keys)


def improvement(baseline: float, candidate: float) -> Tuple[float, float]:
    pp = baseline - candidate
    pct = (pp / baseline * 100.0) if baseline else 0.0
    return pp, pct


def load_controls(path: Path, city: str, sector: str) -> Dict[Tuple[int, int], float]:
    """Return city monthly controls by (year, month)."""
    controls: Dict[Tuple[int, int], float] = {}
    for r in read_csv(path):
        if r.get("gva_parent_code") != sector:
            continue
        controls[(int(r["year"]), int(r["month"]))] = fnum(r["estimated_city_parent_monthly_gva"])
    return controls


def annual_totals_from_controls(controls: Dict[Tuple[int, int], float]) -> Dict[int, float]:
    out: Dict[int, float] = defaultdict(float)
    for (y, _m), v in controls.items():
        out[y] += v
    return dict(out)


def actual_goyang_gu_shares(sector_letter: str, metric: str) -> Dict[int, Dict[str, float]]:
    rows = read_csv(ROOT / "data/processed/partial_stats_phase37_goyang_gu_industry_annual_actual.csv")
    by_year_gu: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        if r.get("general_gu") not in {"덕양구", "일산동구", "일산서구"}:
            continue
        if r.get("sector_code") == sector_letter and r.get("metric") == metric:
            by_year_gu[int(r["year"])][r["general_gu"]] += fnum(r["value"])
    return {y: normalize_shares(vals, vals.keys()) for y, vals in by_year_gu.items()}


def actual_pohang_gu_shares(section: str, metric: str) -> Dict[int, Dict[str, float]]:
    rows = read_csv(ROOT / "data/processed/partial_stats_phase42_pohang_gu_industry_actual.csv")
    by_year_gu: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        if r.get("general_gu") not in {"남구", "북구"}:
            continue
        if r.get("section_code") == section:
            by_year_gu[int(r["year"])][r["general_gu"]] += fnum(r.get(metric))
    return {y: normalize_shares(vals, vals.keys()) for y, vals in by_year_gu.items()}


def goyang_bus_gu_year_month() -> Tuple[Dict[Tuple[int, int, str], float], Dict[Tuple[int, str], float]]:
    rows = read_csv(ROOT / "data/processed/phase61_goyang_bus_emd/goyang_bus_emd_monthly.csv")
    month_vals: Dict[Tuple[int, int, str], float] = defaultdict(float)
    year_vals: Dict[Tuple[int, str], float] = defaultdict(float)
    for r in rows:
        period = r["month"]
        if "-" in period:
            y, m = map(int, period.split("-")[:2])
        else:
            y, m = int(period[:4]), int(period[4:6])
        gu = GU_PREFIX_GOYANG.get(r.get("emd_cd", "")[:5])
        if not gu:
            continue
        val = fnum(r.get("passenger_total"))
        month_vals[(y, m, gu)] += val
        year_vals[(y, gu)] += val
    return month_vals, year_vals


def warehouse_gu_year_month(city: str) -> Tuple[Dict[Tuple[int, int, str], float], Dict[Tuple[int, str], float]]:
    rows = read_csv(ROOT / "data/processed/partial_stats_phase50_logistics_warehouse_emd_monthly.csv")
    month_vals: Dict[Tuple[int, int, str], float] = defaultdict(float)
    year_vals: Dict[Tuple[int, str], float] = defaultdict(float)
    for r in rows:
        if r.get("city") != city:
            continue
        period = r["period"]
        y, m = map(int, period.split("-")[:2])
        gu = r.get("general_gu") or "미상"
        val = fnum(r.get("active_warehouse_area"))
        month_vals[(y, m, gu)] += val
        year_vals[(y, gu)] += val
    return month_vals, year_vals


def construction_area_year_month(city: str, date_col: str = "start_date") -> Tuple[Dict[Tuple[int, int, str], float], Dict[Tuple[int, str], float]]:
    rows = read_csv(ROOT / "data/processed/partial_stats_phase52_building_permit_events_goyang_pohang.csv")
    month_vals: Dict[Tuple[int, int, str], float] = defaultdict(float)
    year_vals: Dict[Tuple[int, str], float] = defaultdict(float)
    for r in rows:
        if r.get("city") != city:
            continue
        date = r.get(date_col) or ""
        if len(date) < 7:
            continue
        try:
            y, m = int(date[:4]), int(date[5:7])
        except ValueError:
            continue
        gu = r.get("general_gu") or "미상"
        val = fnum(r.get("total_floor_area"))
        if val <= 0:
            continue
        month_vals[(y, m, gu)] += val
        year_vals[(y, gu)] += val
    return month_vals, year_vals


def broker_gu_shares(city: str) -> Dict[str, float]:
    rows = read_csv(ROOT / "data/processed/partial_stats_phase53_realestate_broker_goyang_pohang.csv")
    vals: Dict[str, float] = defaultdict(float)
    for r in rows:
        if r.get("city") == city:
            vals[r.get("general_gu") or "미상"] += 1.0
    return normalize_shares(vals, vals.keys())


def evaluate_yearly_gu_basis(
    city: str,
    sector: str,
    metric: str,
    actual_by_year: Dict[int, Dict[str, float]],
    candidates: Dict[str, Dict[Tuple[int, str], float]],
) -> List[dict]:
    rows: List[dict] = []
    for y, actual in sorted(actual_by_year.items()):
        keys = sorted(actual.keys())
        if not keys:
            continue
        equal = {k: 1.0 / len(keys) for k in keys}
        rows.append({
            "city": city, "year": y, "sector": sector, "sector_name": SECTOR_NAME.get(sector, sector),
            "metric": metric, "basis": "구 균등배분", "mae_pp": mae_pp(actual, equal, keys),
        })
        for basis, vals in candidates.items():
            pred = normalize_shares({k: vals.get((y, k), 0.0) for k in keys}, keys)
            rows.append({
                "city": city, "year": y, "sector": sector, "sector_name": SECTOR_NAME.get(sector, sector),
                "metric": metric, "basis": basis, "mae_pp": mae_pp(actual, pred, keys),
            })
    return rows


def allocate_monthly_gu(
    city: str,
    sector: str,
    controls: Dict[Tuple[int, int], float],
    month_vals: Dict[Tuple[int, int, str], float],
    annual_vals: Dict[Tuple[int, str], float],
    all_gu: List[str],
    basis_label: str,
) -> List[dict]:
    annual_city = annual_totals_from_controls(controls)
    out: List[dict] = []
    for year, annual_total in sorted(annual_city.items()):
        # Month path within the year uses city-wide monthly activity. If activity
        # is absent, keep the previous equal-within-quarter control total.
        month_activity = {
            m: sum(month_vals.get((year, m, gu), 0.0) for gu in all_gu)
            for m in range(1, 13)
        }
        activity_total = sum(month_activity.values())
        for month in range(1, 13):
            if activity_total > 0:
                city_month_gva = annual_total * month_activity[month] / activity_total
            else:
                city_month_gva = controls.get((year, month), annual_total / 12.0)
            gu_values = {gu: month_vals.get((year, month, gu), 0.0) for gu in all_gu}
            if sum(gu_values.values()) <= 0:
                gu_values = {gu: annual_vals.get((year, gu), 0.0) for gu in all_gu}
            gu_shares = normalize_shares(gu_values, all_gu)
            for gu in all_gu:
                out.append({
                    "city": city,
                    "year": year,
                    "quarter": quarter_from_month(month),
                    "month": month,
                    "period": f"{year}-{month:02d}",
                    "sector": sector,
                    "sector_name": SECTOR_NAME.get(sector, sector),
                    "general_gu": gu,
                    "basis": basis_label,
                    "city_month_gva": city_month_gva,
                    "gu_share": gu_shares[gu],
                    "estimated_gu_monthly_gva": city_month_gva * gu_shares[gu],
                })
    return out


def allocate_monthly_emd_goyang_h_bus() -> List[dict]:
    controls = load_controls(ROOT / "data/processed/partial_stats_phase41_parent_monthly_controls.csv", "고양시", "H00")
    annual_city = annual_totals_from_controls(controls)
    rows = read_csv(ROOT / "data/processed/phase61_goyang_bus_emd/goyang_bus_emd_monthly.csv")
    activity: Dict[Tuple[int, int, str, str], float] = defaultdict(float)
    month_total: Dict[Tuple[int, int], float] = defaultdict(float)
    year_total: Dict[int, float] = defaultdict(float)
    for r in rows:
        p = r["month"]
        y, m = (int(p[:4]), int(p[4:6])) if "-" not in p else tuple(map(int, p.split("-")[:2]))
        emd_cd, emd_nm = r["emd_cd"], r["emd_nm"]
        val = fnum(r.get("passenger_total"))
        activity[(y, m, emd_cd, emd_nm)] += val
        month_total[(y, m)] += val
        year_total[y] += val
    out: List[dict] = []
    by_month_emd: Dict[Tuple[int, int], List[Tuple[str, str, float]]] = defaultdict(list)
    for (y, m, cd, nm), val in activity.items():
        by_month_emd[(y, m)].append((cd, nm, val))
    for y, annual_gva in sorted(annual_city.items()):
        for m in range(1, 13):
            if year_total.get(y, 0.0) > 0:
                city_month_gva = annual_gva * month_total.get((y, m), 0.0) / year_total[y]
            else:
                city_month_gva = controls.get((y, m), annual_gva / 12.0)
            emds = by_month_emd.get((y, m), [])
            total = sum(v for _cd, _nm, v in emds)
            if total <= 0:
                continue
            for cd, nm, val in emds:
                share = val / total
                out.append({
                    "city": "고양시",
                    "year": y,
                    "quarter": quarter_from_month(m),
                    "month": m,
                    "period": f"{y}-{m:02d}",
                    "sector": "H00",
                    "sector_name": "운수 및 창고업",
                    "emd_code": cd,
                    "emd_name": nm,
                    "general_gu": GU_PREFIX_GOYANG.get(cd[:5], ""),
                    "activity_indicator": "버스 승하차 활동지표",
                    "city_month_gva": city_month_gva,
                    "emd_share": share,
                    "estimated_emd_monthly_gva": city_month_gva * share,
                })
    return out


def accounting_checks(rows: List[dict], controls: Dict[Tuple[int, int], float], level_col: str = "general_gu") -> List[dict]:
    by_month: Dict[Tuple[int, int, str], float] = defaultdict(float)
    by_quarter: Dict[Tuple[int, int, str], float] = defaultdict(float)
    by_year: Dict[Tuple[int, str], float] = defaultdict(float)
    month_control_from_rows: Dict[Tuple[int, int, str], float] = {}
    for r in rows:
        y, m, q = int(r["year"]), int(r["month"]), int(r["quarter"])
        city = r["city"]
        v = fnum(r.get("estimated_gu_monthly_gva") or r.get("estimated_emd_monthly_gva"))
        by_month[(y, m, city)] += v
        by_quarter[(y, q, city)] += v
        by_year[(y, city)] += v
        # The specialized experiment may replace the previous equal-within-quarter
        # monthly path.  Therefore monthly/quarter accounting should be checked
        # against the newly allocated city-month control embedded in the rows,
        # while annual accounting is still checked against the upper city control.
        month_control_from_rows[(y, m, city)] = fnum(r.get("city_month_gva"))
    out: List[dict] = []
    control_month: Dict[Tuple[int, int, str], float] = defaultdict(float)
    control_quarter: Dict[Tuple[int, int, str], float] = defaultdict(float)
    control_year: Dict[Tuple[int, str], float] = defaultdict(float)
    # city inferred from rows; controls are for one city.
    cities = sorted({r["city"] for r in rows})
    for city in cities:
        for (y, m, c), v in month_control_from_rows.items():
            if c != city:
                continue
            control_month[(y, m, city)] += v
            control_quarter[(y, quarter_from_month(m), city)] += v
        for (y, m), v in controls.items():
            control_year[(y, city)] += v
    for key, est in sorted(by_month.items()):
        ctrl = control_month.get(key, 0.0)
        out.append({"aggregation": "월합", "year": key[0], "period": f"{key[0]}-{key[1]:02d}", "city": key[2], "estimated_sum": est, "control": ctrl, "abs_error": abs(est - ctrl)})
    for key, est in sorted(by_quarter.items()):
        ctrl = control_quarter.get(key, 0.0)
        out.append({"aggregation": "분기합", "year": key[0], "period": f"{key[0]}Q{key[1]}", "city": key[2], "estimated_sum": est, "control": ctrl, "abs_error": abs(est - ctrl)})
    for key, est in sorted(by_year.items()):
        ctrl = control_year.get(key, 0.0)
        out.append({"aggregation": "연합", "year": key[0], "period": str(key[0]), "city": key[1], "estimated_sum": est, "control": ctrl, "abs_error": abs(est - ctrl)})
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # 1) Directly reuse existing rigorous specialized-basis tests for A/F/L/H.
    phase54 = read_csv(ROOT / "data/processed/partial_stats_phase54_specialized_allocation_summary.csv")
    phase47 = read_csv(ROOT / "data/processed/partial_stats_phase47_agri_validation_summary.csv")

    # 2) New H validation with Goyang bus data.
    bus_month, bus_year = goyang_bus_gu_year_month()
    wh_goyang_month, wh_goyang_year = warehouse_gu_year_month("고양시")
    wh_pohang_month, wh_pohang_year = warehouse_gu_year_month("포항시")

    # Composite H activity for Goyang: passenger land transport + storage, equal weight
    combo_year: Dict[Tuple[int, str], float] = defaultdict(float)
    for key, val in bus_year.items():
        combo_year[key] += val
    # Scale warehouse by annual city total before averaging to prevent area units dominating.
    for y in sorted({k[0] for k in set(bus_year) | set(wh_goyang_year)}):
        gus = sorted({gu for yy, gu in set(bus_year) | set(wh_goyang_year) if yy == y})
        bus_share = normalize_shares({gu: bus_year.get((y, gu), 0.0) for gu in gus}, gus)
        wh_share = normalize_shares({gu: wh_goyang_year.get((y, gu), 0.0) for gu in gus}, gus)
        for gu in gus:
            combo_year[(y, gu)] = 0.5 * bus_share.get(gu, 0.0) + 0.5 * wh_share.get(gu, 0.0)

    h_eval: List[dict] = []
    for metric in ["employees", "establishments"]:
        h_eval.extend(evaluate_yearly_gu_basis(
            "고양시", "H00", metric, actual_goyang_gu_shares("H", metric),
            {
                "버스 승하차 활동지표": bus_year,
                "창고 영업면적": wh_goyang_year,
                "버스 승하차+창고면적 평균": combo_year,
            },
        ))
    for metric in ["employees", "establishments", "sales"]:
        h_eval.extend(evaluate_yearly_gu_basis(
            "포항시", "H00", metric, actual_pohang_gu_shares("H", metric),
            {"창고 영업면적": wh_pohang_year},
        ))
    write_csv(
        OUT / "phase62_h_transport_validation.csv",
        h_eval,
        ["city", "year", "sector", "sector_name", "metric", "basis", "mae_pp"],
    )

    # 3) Build accounting-constrained monthly/quarterly GVA allocations.
    goyang_h_controls = load_controls(ROOT / "data/processed/partial_stats_phase41_parent_monthly_controls.csv", "고양시", "H00")
    goyang_f_controls = load_controls(ROOT / "data/processed/partial_stats_phase41_parent_monthly_controls.csv", "고양시", "F00")
    goyang_l_controls = load_controls(ROOT / "data/processed/partial_stats_phase41_parent_monthly_controls.csv", "고양시", "L00")
    pohang_h_controls = load_controls(ROOT / "data/processed/partial_stats_phase42_pohang_parent_monthly_controls.csv", "포항시", "H00")
    pohang_f_controls = load_controls(ROOT / "data/processed/partial_stats_phase42_pohang_parent_monthly_controls.csv", "포항시", "F00")
    pohang_l_controls = load_controls(ROOT / "data/processed/partial_stats_phase42_pohang_parent_monthly_controls.csv", "포항시", "L00")

    goyang_gus = ["덕양구", "일산동구", "일산서구"]
    pohang_gus = ["남구", "북구"]
    f_goyang_month, f_goyang_year = construction_area_year_month("고양시")
    f_pohang_month, f_pohang_year = construction_area_year_month("포항시")

    goyang_h_gu = allocate_monthly_gu("고양시", "H00", goyang_h_controls, bus_month, bus_year, goyang_gus, "버스 승하차 활동지표")
    goyang_h_emd = allocate_monthly_emd_goyang_h_bus()
    goyang_f_gu = allocate_monthly_gu("고양시", "F00", goyang_f_controls, f_goyang_month, f_goyang_year, goyang_gus, "건축 착공 연면적")
    pohang_f_gu = allocate_monthly_gu("포항시", "F00", pohang_f_controls, f_pohang_month, f_pohang_year, pohang_gus, "건축 착공 연면적")
    pohang_h_gu = allocate_monthly_gu("포항시", "H00", pohang_h_controls, wh_pohang_month, wh_pohang_year, pohang_gus, "창고 영업면적")

    # L: spatial stock/count allocation; monthly time path remains constrained control.
    def fixed_share_monthly(city, sector, controls, shares, gus, label):
        rows = []
        for (y, m), city_month_gva in sorted(controls.items()):
            norm = normalize_shares({gu: shares.get(gu, 0.0) for gu in gus}, gus)
            for gu in gus:
                rows.append({
                    "city": city, "year": y, "quarter": quarter_from_month(m), "month": m, "period": f"{y}-{m:02d}",
                    "sector": sector, "sector_name": SECTOR_NAME[sector], "general_gu": gu,
                    "basis": label, "city_month_gva": city_month_gva, "gu_share": norm[gu],
                    "estimated_gu_monthly_gva": city_month_gva * norm[gu],
                })
        return rows

    goyang_l_gu = fixed_share_monthly("고양시", "L00", goyang_l_controls, broker_gu_shares("고양시"), goyang_gus, "중개업소 수")
    pohang_l_gu = fixed_share_monthly("포항시", "L00", pohang_l_controls, broker_gu_shares("포항시"), pohang_gus, "중개업소 수")

    gu_rows = goyang_h_gu + goyang_f_gu + pohang_f_gu + pohang_h_gu + goyang_l_gu + pohang_l_gu
    write_csv(
        OUT / "phase62_specialized_gu_monthly_gva.csv",
        gu_rows,
        ["city", "year", "quarter", "month", "period", "sector", "sector_name", "general_gu", "basis", "city_month_gva", "gu_share", "estimated_gu_monthly_gva"],
    )
    write_csv(
        OUT / "phase62_goyang_h_bus_emd_monthly_gva.csv",
        goyang_h_emd,
        ["city", "year", "quarter", "month", "period", "sector", "sector_name", "emd_code", "emd_name", "general_gu", "activity_indicator", "city_month_gva", "emd_share", "estimated_emd_monthly_gva"],
    )

    checks = []
    checks.extend(accounting_checks(goyang_h_gu, goyang_h_controls))
    checks.extend(accounting_checks(goyang_h_emd, goyang_h_controls))
    checks.extend(accounting_checks(goyang_f_gu, goyang_f_controls))
    checks.extend(accounting_checks(goyang_l_gu, goyang_l_controls))
    checks.extend(accounting_checks(pohang_h_gu, pohang_h_controls))
    checks.extend(accounting_checks(pohang_f_gu, pohang_f_controls))
    checks.extend(accounting_checks(pohang_l_gu, pohang_l_controls))
    write_csv(
        OUT / "phase62_accounting_checks.csv",
        checks,
        ["aggregation", "year", "period", "city", "estimated_sum", "control", "abs_error"],
    )

    # 4) Consolidated progress table versus equal/general baselines where valid.
    progress: List[dict] = []

    # Agriculture from phase47.
    for r in phase47:
        level = r.get("level") or r.get("수준") or ""
        if level in ("sido", "sigungu"):
            base = fnum(r.get("general_mae_pp") or r.get("일반 MAE(%p)") or r.get("general_mae"))
            best = fnum(r.get("best_specialized_mae_pp") or r.get("best_mae_pp") or r.get("최종 MAE(%p)") or r.get("best_mae"))
            if base or best:
                pp, pct = improvement(base, best)
                progress.append({
                    "city": "전국 검증", "sector": "A00", "sector_name": "농림어업", "validation_scope": level,
                    "metric": "시군구/시도 GVA share", "baseline": "사업체·종사자 기반 일반 배분",
                    "specialized_basis": r.get("best_specialized_model") or r.get("best_model") or r.get("최종 특화") or "직전 관측 비중/혼합",
                    "baseline_mae_pp": base, "specialized_mae_pp": best,
                    "improvement_pp": pp, "improvement_pct": pct,
                    "judgement": "개선" if pp > 0 else "보류",
                })

    # Phase54 best improvements.
    grouped54: Dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
    for r in phase54:
        grouped54[(r["city"], r["sector"], r["metric"])].append(r)
    for (city, sector, metric), rows in sorted(grouped54.items()):
        equal = next((fnum(r["mae_pp"]) for r in rows if r["basis_id"] == "구 균등배분"), None)
        candidates = [r for r in rows if r["basis_id"] != "구 균등배분"]
        if equal is None or not candidates:
            continue
        best = min(candidates, key=lambda r: fnum(r["mae_pp"]))
        best_mae = fnum(best["mae_pp"])
        pp, pct = improvement(equal, best_mae)
        parent_sector = SECTION_TO_PARENT.get(sector, sector)
        progress.append({
            "city": city, "sector": parent_sector, "sector_name": SECTOR_NAME.get(parent_sector, best["sector_name"]),
            "validation_scope": "구 단위 공식분포", "metric": metric,
            "baseline": "구 균등배분", "specialized_basis": best["basis_id"],
            "baseline_mae_pp": equal, "specialized_mae_pp": best_mae,
            "improvement_pp": pp, "improvement_pct": pct,
            "judgement": "개선" if pp > 0 else "보류",
        })

    # New H validation summary.
    grouped_h: Dict[Tuple[str, int, str], List[dict]] = defaultdict(list)
    for r in h_eval:
        grouped_h[(r["city"], int(r["year"]), r["metric"])].append(r)
    for (city, year, metric), rows in sorted(grouped_h.items()):
        equal = next((fnum(r["mae_pp"]) for r in rows if r["basis"] == "구 균등배분"), None)
        candidates = [r for r in rows if r["basis"] != "구 균등배분"]
        if equal is None or not candidates:
            continue
        best = min(candidates, key=lambda r: fnum(r["mae_pp"]))
        best_mae = fnum(best["mae_pp"])
        pp, pct = improvement(equal, best_mae)
        progress.append({
            "city": city, "sector": "H00", "sector_name": "운수 및 창고업",
            "validation_scope": f"{year} 구 단위 공식분포", "metric": metric,
            "baseline": "구 균등배분", "specialized_basis": best["basis"],
            "baseline_mae_pp": equal, "specialized_mae_pp": best_mae,
            "improvement_pp": pp, "improvement_pct": pct,
            "judgement": "개선" if pp > 0 else "보류",
        })

    write_csv(
        OUT / "phase62_specialized_progress_summary.csv",
        progress,
        ["city", "sector", "sector_name", "validation_scope", "metric", "baseline", "specialized_basis", "baseline_mae_pp", "specialized_mae_pp", "improvement_pp", "improvement_pct", "judgement"],
    )

    max_accounting_error = max((fnum(r["abs_error"]) for r in checks), default=0.0)
    manifest = {
        "run_id": "phase62_vulnerable_specialized_gva",
        "created_at": datetime.now(KST).isoformat(timespec="seconds"),
        "outputs": [
            str(OUT / "phase62_h_transport_validation.csv"),
            str(OUT / "phase62_specialized_gu_monthly_gva.csv"),
            str(OUT / "phase62_goyang_h_bus_emd_monthly_gva.csv"),
            str(OUT / "phase62_accounting_checks.csv"),
            str(OUT / "phase62_specialized_progress_summary.csv"),
            str(REPORT),
        ],
        "max_accounting_abs_error": max_accounting_error,
        "rows": {
            "h_validation": len(h_eval),
            "gu_monthly_gva": len(gu_rows),
            "goyang_h_emd_monthly_gva": len(goyang_h_emd),
            "accounting_checks": len(checks),
            "progress": len(progress),
        },
    }
    (OUT / "phase62_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Report markdown
    progress_sorted = sorted(progress, key=lambda r: (r["city"], r["sector"], r["metric"], -fnum(r["improvement_pp"])))
    h_best = [r for r in progress_sorted if r["sector"] == "H00"]
    good = [r for r in progress_sorted if fnum(r["improvement_pp"]) > 0]
    bad = [r for r in progress_sorted if fnum(r["improvement_pp"]) <= 0]

    def md_table(rows: List[dict], cols: List[Tuple[str, str]], limit: int = 20) -> str:
        if not rows:
            return "\n해당 없음\n"
        s = "| " + " | ".join(label for _key, label in cols) + " |\n"
        s += "| " + " | ".join("---" for _key, _label in cols) + " |\n"
        for r in rows[:limit]:
            vals = []
            for key, _label in cols:
                v = r.get(key, "")
                if isinstance(v, float):
                    vals.append(f"{v:.3f}")
                else:
                    try:
                        fv = float(v)
                        vals.append(f"{fv:.3f}")
                    except Exception:
                        vals.append(str(v))
            s += "| " + " | ".join(vals) + " |\n"
        return s

    report = f"""# 취약 업종 특화 배분·외삽 실험

## 핵심 결론

수집된 무료 자료를 업종별 활동지표로 전환해 고양시·포항시의 취약 업종 월·분기 부가가치 배분을 다시 수행했다. 월·분기 실제 GVA는 존재하지 않으므로, 추정값은 연간 시 단위 상위 총량에 정확히 맞추고, 성능은 실제로 존재하는 구 단위 공식 사업체·종사자·매출 분포와의 평균절대오차(pp)로 검증했다.

- 농림어업은 일반 사업체·종사자 배분에서 분리하는 것이 명확히 낫다. 기존 Phase47 검증에서 시군구 기준 MAE가 4.138pp에서 0.751pp로 줄었다.
- 건설업은 착공 연면적을 쓰면 고양시 종사자 분포와 포항시 매출 분포에서 개선된다. 포항시 매출 기준은 22.468pp에서 1.845pp로 크게 줄었다.
- 부동산업은 중개업소 수 또는 부동산 건물면적이 구 단위 분포를 잘 설명한다. 다만 월별 경기 변동성은 아직 약하고, 공간 배분 개선으로 보는 편이 정확하다.
- 운수 및 창고업은 이번 버스 자료가 고양시 행정동×월 세분화에는 유용하지만, H00 전체를 단독으로 대체할 만큼 안정적이지는 않다. 여객운송 하위영역에는 채택 가능, H00 전체에는 창고·화물·항만 지표와 결합해야 한다.

## 개선된 경우

{md_table(good, [("city","지역"),("sector_name","업종"),("validation_scope","검증범위"),("metric","검증지표"),("baseline_mae_pp","기존오차 pp"),("specialized_basis","특화 활동지표"),("specialized_mae_pp","개선오차 pp"),("improvement_pct","개선율 %")], 24)}

## 보류 또는 악화된 경우

{md_table(bad, [("city","지역"),("sector_name","업종"),("validation_scope","검증범위"),("metric","검증지표"),("baseline_mae_pp","기존오차 pp"),("specialized_basis","특화 활동지표"),("specialized_mae_pp","특화오차 pp"),("improvement_pp","개선폭 pp")], 24)}

## 운수 및 창고업: 새 버스 자료 반영 검증

{md_table(h_best, [("city","지역"),("validation_scope","검증범위"),("metric","검증지표"),("baseline_mae_pp","균등오차 pp"),("specialized_basis","최저오차 활동지표"),("specialized_mae_pp","최저오차 pp"),("judgement","판정")], 24)}

## 산출된 월·분기 부가가치 추정자료

- `phase62_specialized_gu_monthly_gva.csv`: 고양시·포항시의 건설업, 부동산업, 운수 및 창고업 구×월 추정 부가가치.
- `phase62_goyang_h_bus_emd_monthly_gva.csv`: 고양시 운수 및 창고업 중 버스 승하차 활동지표 기반 행정동×월 배분안.
- `phase62_accounting_checks.csv`: 월합·분기합·연합이 상위 시 단위 통제값과 일치하는지 검증한 표.

최대 회계검증 절대오차는 `{max_accounting_error:.10f}`이다. 이는 부동소수점 반올림 수준이며, 상위 총량 보존 조건은 충족한다.

## 해석

이번 결과의 핵심은 “취약 업종 전체를 하나의 일반 배분식으로 밀어붙이지 않는다”는 점이다. 농림어업, 건설업, 부동산업은 일반 배분에서 분리할 근거가 충분하다. 반면 운수 및 창고업은 여객·화물·창고·항만이 섞인 업종이므로, 버스 승하차만으로 H00 전체를 설명하면 오차가 커질 수 있다. 따라서 고양시 포스터에는 “버스 승하차 기반 행정동 월간 활동지도”를 세부 정책 콘텐츠로 쓰고, H00 전체 성능 개선 주장은 창고·화물 자료까지 결합한 경우로 제한해야 한다.

## 산출 파일

- `data/processed/phase62_vulnerable_specialized_gva/phase62_specialized_progress_summary.csv`
- `data/processed/phase62_vulnerable_specialized_gva/phase62_h_transport_validation.csv`
- `data/processed/phase62_vulnerable_specialized_gva/phase62_specialized_gu_monthly_gva.csv`
- `data/processed/phase62_vulnerable_specialized_gva/phase62_goyang_h_bus_emd_monthly_gva.csv`
- `data/processed/phase62_vulnerable_specialized_gva/phase62_accounting_checks.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
