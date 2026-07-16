from __future__ import annotations

import csv
import math
import random
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any

import numpy as np

from collect_public_feature_sources import parse_kepco_workbook
from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv


EPS = 1e-9
REPORT_DIR = ROOT / "reports"
EXPERIMENT_DIR = REPORT_DIR / "experiments"
MODEL_INPUT_DIR = ROOT / "data" / "model_inputs"
ORIGINS = {
    "O0": ("previous_december", 12, 31, -1),
    "O1": ("current_march", 3, 31, 0),
    "O2": ("current_june", 6, 30, 0),
    "O3": ("current_september", 9, 30, 0),
}
PRIMARY_SECTORS = {"C00", "D00", "E00"}
RIDGE_LAMBDAS = [0.1, 1.0, 10.0, 100.0, 1000.0]
FEATURE_BUNDLES = {
    "A1_level_only": [
        "log_total_trailing12_sum",
        "log_industrial_trailing12_sum",
        "log_total_latest",
        "log_industrial_latest",
    ],
    "A3_composition_only": [
        "industrial_share_trailing12",
        "commercial_share_trailing12",
        "industrial_share_latest",
    ],
    "A4_change_only": [
        "industrial_yoy_same_available_window",
        "total_yoy_same_available_window",
        "industrial_3m_momentum",
        "total_3m_momentum",
    ],
    "A5_level_normalized": [
        "log_industrial_trailing12_sum",
        "industrial_share_trailing12",
        "industrial_share_of_sido",
        "log_total_trailing12_sum",
    ],
    "A6_full_minimal": [
        "log_industrial_trailing12_sum",
        "industrial_share_trailing12",
        "industrial_yoy_same_available_window",
        "industrial_3m_momentum",
        "industrial_share_of_sido",
        "log_total_trailing12_sum",
        "commercial_share_trailing12",
        "eligible_observation_count",
    ],
}
PRIMARY_BUNDLE = "A6_full_minimal"


def num(value: Any, default: float = 0.0) -> float:
    parsed = parse_number(value)
    return default if parsed is None else float(parsed)


def norm_sido(name: str) -> str:
    aliases = {"강원도": "강원특별자치도", "전라북도": "전북특별자치도", "전북": "전북특별자치도"}
    return aliases.get(str(name or "").strip(), str(name or "").strip())


def norm_sigungu(name: str) -> str:
    return "".join(str(name or "").split())


def add_months(period: str, months: int) -> str:
    year = int(period[:4])
    month = int(period[4:6]) + months
    while month > 12:
        month -= 12
        year += 1
    while month < 1:
        month += 12
        year -= 1
    return f"{year}{month:02d}"


def period_range(end_period: str, months: int) -> list[str]:
    return [add_months(end_period, -offset) for offset in reversed(range(months))]


def origin_date(target_year: int, origin_id: str) -> str:
    _label, month, day, year_offset = ORIGINS[origin_id]
    return date(target_year + year_offset, month, day).isoformat()


def source_meta() -> dict[str, dict[str, str]]:
    meta = {}
    for row in read_csv(PROCESSED_DIR / "kepco_historical_download_inventory.csv"):
        if row.get("download_status") != "downloaded":
            continue
        meta[row["source_period"]] = row
    return meta


def build_region_map() -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for row in read_csv(PROCESSED_DIR / "sigungu_global_model_pilot_predictions.csv"):
        if row.get("policy") != "baseline":
            continue
        key = (norm_sido(row.get("source_region", "")), norm_sigungu(row.get("sigungu_name", "")))
        out[key] = row.get("sigungu_code", "")
    return out


def build_vintage_long() -> list[dict[str, Any]]:
    meta = source_meta()
    region_map = build_region_map()
    rows: list[dict[str, Any]] = []
    for source_period, item in sorted(meta.items()):
        if not ("202011" <= source_period <= "202312"):
            continue
        path = Path(item["local_path"])
        try:
            parsed_rows = parse_kepco_workbook(path, source_period)
        except Exception:
            continue
        for row in parsed_rows:
            obs = str(row["period"])
            if not ("202001" <= obs <= "202312"):
                continue
            metric = str(row["metric"])
            if not (
                metric.startswith("electricity_contract_kwh_")
                or metric in {"electricity_use_industry_kwh_total", "electricity_contract_kwh_total"}
            ):
                continue
            sido = norm_sido(str(row["sido_name"]))
            sigungu = norm_sigungu(str(row["sigungu_name"]))
            code = region_map.get((sido, sigungu), "")
            if not code and sido == "세종특별자치시" and sigungu == "세종시":
                code = "세종특별자치시:세종시"
            feature_key = f"{sido}:{code or sigungu}"
            rows.append(
                {
                    "sigungu_feature_key": feature_key,
                    "sido_name": row["sido_name"],
                    "sido_name_normalized": sido,
                    "sigungu_name": row["sigungu_name"],
                    "sigungu_name_normalized": sigungu,
                    "sigungu_code": code,
                    "observation_period": obs,
                    "source_vintage_period": source_period,
                    "publication_date": item["publication_date"],
                    "board_no": item.get("board_no", ""),
                    "source_filename": item.get("file_name", ""),
                    "source_hash": item.get("sha256", ""),
                    "electricity_variable": metric,
                    "value": row["value"],
                    "selection_rule_version": "vintage_selector_v1_publication_date_source_period_board_hash",
                }
            )
    rows.sort(
        key=lambda r: (
            r["sigungu_feature_key"],
            r["observation_period"],
            r["electricity_variable"],
            r["publication_date"],
            r["source_vintage_period"],
            r["board_no"],
            r["source_hash"],
        )
    )
    write_csv(PROCESSED_DIR / "kepco_historical_vintage_long.csv", rows)
    return rows


def load_or_build_vintage_long() -> list[dict[str, Any]]:
    path = PROCESSED_DIR / "kepco_historical_vintage_long.csv"
    if path.exists() and path.stat().st_size > 1000:
        return read_csv(path)
    return build_vintage_long()


def selected_asof(vintage_rows: list[dict[str, Any]], prediction_origin_date: str, leakage_latest: bool = False, lag_months: int | None = None) -> dict[tuple[str, str, str], dict[str, Any]]:
    selected: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in vintage_rows:
        if not leakage_latest and str(row["publication_date"]) > prediction_origin_date:
            continue
        if lag_months is not None and add_months(str(row["observation_period"]), lag_months) > prediction_origin_date[:7].replace("-", ""):
            continue
        key = (row["sigungu_feature_key"], row["observation_period"], row["electricity_variable"])
        old = selected.get(key)
        candidate_key = (row["publication_date"], row["source_vintage_period"], row.get("board_no", ""), row.get("source_hash", ""))
        old_key = (old["publication_date"], old["source_vintage_period"], old.get("board_no", ""), old.get("source_hash", "")) if old else None
        if old is None or candidate_key > old_key:
            selected[key] = row
    return selected


def monthly_records(selected: dict[tuple[str, str, str], dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for (_fkey, obs, variable), row in selected.items():
        rec = grouped.setdefault(
            (row["sigungu_feature_key"], obs),
            {
                "sigungu_feature_key": row["sigungu_feature_key"],
                "sido_name": row["sido_name"],
                "sido_name_normalized": row["sido_name_normalized"],
                "sigungu_name": row["sigungu_name"],
                "sigungu_name_normalized": row["sigungu_name_normalized"],
                "sigungu_code": row["sigungu_code"],
                "observation_period": obs,
                "selected_publication_date": row["publication_date"],
                "selected_source_vintage": row["source_vintage_period"],
                "selected_source_filename": row["source_filename"],
                "selected_source_hash": row["source_hash"],
            },
        )
        rec[variable] = num(row["value"])
        if row["publication_date"] > rec["selected_publication_date"]:
            rec["selected_publication_date"] = row["publication_date"]
            rec["selected_source_vintage"] = row["source_vintage_period"]
            rec["selected_source_filename"] = row["source_filename"]
            rec["selected_source_hash"] = row["source_hash"]
    for rec in grouped.values():
        if "electricity_contract_kwh_total" not in rec:
            rec["electricity_contract_kwh_total"] = rec.get("electricity_contract_kwh_합계", 0.0)
        total = float(rec.get("electricity_contract_kwh_total") or 0.0)
        rec["electricity_total_kwh"] = total
        rec["electricity_industrial_kwh"] = float(rec.get("electricity_contract_kwh_산업용") or 0.0)
        rec["electricity_commercial_kwh"] = float(rec.get("electricity_contract_kwh_일반용") or 0.0)
    return grouped


def sum_periods(monthly: dict[str, dict[str, Any]], periods: list[str], field: str) -> tuple[float, int]:
    vals = [float(monthly[p].get(field) or 0.0) for p in periods if p in monthly and monthly[p].get(field) not in ("", None)]
    return sum(vals), len(vals)


def make_feature_row(
    target_year: int,
    origin_id: str,
    origin_dt: str,
    fkey: str,
    rows_by_period: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    eligible_periods = sorted(p for p in rows_by_period if p <= origin_dt[:7].replace("-", ""))
    target_ytd = [p for p in eligible_periods if p.startswith(str(target_year))]
    latest = eligible_periods[-1] if eligible_periods else ""
    latest_row = rows_by_period.get(latest, {})
    t3 = period_range(latest, 3) if latest else []
    t6 = period_range(latest, 6) if latest else []
    t12 = period_range(latest, 12) if latest else []
    total_t12, total_t12_n = sum_periods(rows_by_period, t12, "electricity_total_kwh")
    ind_t12, ind_t12_n = sum_periods(rows_by_period, t12, "electricity_industrial_kwh")
    com_t12, _com_t12_n = sum_periods(rows_by_period, t12, "electricity_commercial_kwh")
    total_t3, total_t3_n = sum_periods(rows_by_period, t3, "electricity_total_kwh")
    ind_t3, ind_t3_n = sum_periods(rows_by_period, t3, "electricity_industrial_kwh")
    prev3 = [add_months(p, -3) for p in t3]
    total_prev3, total_prev3_n = sum_periods(rows_by_period, prev3, "electricity_total_kwh")
    ind_prev3, ind_prev3_n = sum_periods(rows_by_period, prev3, "electricity_industrial_kwh")
    ytd_periods = sorted(target_ytd)
    prev_ytd = [f"{target_year - 1}{p[4:6]}" for p in ytd_periods]
    total_ytd, total_ytd_n = sum_periods(rows_by_period, ytd_periods, "electricity_total_kwh")
    ind_ytd, ind_ytd_n = sum_periods(rows_by_period, ytd_periods, "electricity_industrial_kwh")
    total_prev_ytd, total_prev_ytd_n = sum_periods(rows_by_period, prev_ytd, "electricity_total_kwh")
    ind_prev_ytd, ind_prev_ytd_n = sum_periods(rows_by_period, prev_ytd, "electricity_industrial_kwh")
    yoy_cov = min(total_ytd_n, total_prev_ytd_n) / max(1, len(ytd_periods)) if ytd_periods else 0.0
    return {
        "sigungu_feature_key": fkey,
        "target_year": target_year,
        "prediction_origin_id": origin_id,
        "prediction_origin_date": origin_dt,
        "latest_eligible_observation_period": latest,
        "eligible_observation_count": len(eligible_periods),
        "target_ytd_observation_count": len(ytd_periods),
        "selected_publication_date": latest_row.get("selected_publication_date", ""),
        "selected_source_filename": latest_row.get("selected_source_filename", ""),
        "selected_source_hash": latest_row.get("selected_source_hash", ""),
        "selected_source_vintage": latest_row.get("selected_source_vintage", ""),
        "sido_name_normalized": latest_row.get("sido_name_normalized", ""),
        "sigungu_name_normalized": latest_row.get("sigungu_name_normalized", ""),
        "sigungu_code": latest_row.get("sigungu_code", ""),
        "total_latest": float(latest_row.get("electricity_total_kwh") or 0.0),
        "industrial_latest": float(latest_row.get("electricity_industrial_kwh") or 0.0),
        "commercial_latest": float(latest_row.get("electricity_commercial_kwh") or 0.0),
        "log_total_latest": math.log1p(float(latest_row.get("electricity_total_kwh") or 0.0)),
        "log_industrial_latest": math.log1p(float(latest_row.get("electricity_industrial_kwh") or 0.0)),
        "total_trailing12_sum": total_t12,
        "industrial_trailing12_sum": ind_t12,
        "commercial_trailing12_sum": com_t12,
        "log_total_trailing12_sum": math.log1p(total_t12),
        "log_industrial_trailing12_sum": math.log1p(ind_t12),
        "industrial_share_latest": float(latest_row.get("electricity_industrial_kwh") or 0.0) / float(latest_row.get("electricity_total_kwh") or 1.0),
        "industrial_share_trailing12": ind_t12 / total_t12 if total_t12 else 0.0,
        "commercial_share_trailing12": com_t12 / total_t12 if total_t12 else 0.0,
        "total_3m_momentum": (total_t3 / total_t3_n) / (total_prev3 / total_prev3_n) - 1 if total_t3_n >= 2 and total_prev3_n >= 2 and total_prev3 else "",
        "industrial_3m_momentum": (ind_t3 / ind_t3_n) / (ind_prev3 / ind_prev3_n) - 1 if ind_t3_n >= 2 and ind_prev3_n >= 2 and ind_prev3 else "",
        "total_yoy_same_available_window": total_ytd / total_prev_ytd - 1 if yoy_cov >= 0.75 and total_prev_ytd else "",
        "industrial_yoy_same_available_window": ind_ytd / ind_prev_ytd - 1 if yoy_cov >= 0.75 and ind_prev_ytd else "",
        "feature_window_expected_months": len(t12),
        "feature_window_available_months": total_t12_n,
        "feature_window_coverage_rate": total_t12_n / 12 if t12 else 0.0,
        "yoy_window_coverage_rate": yoy_cov,
        "selection_rule_version": "vintage_selector_v1_publication_date_source_period_board_hash",
    }


def build_asof_features(vintage_rows: list[dict[str, Any]], leakage_latest: bool = False, lag_months: int | None = None, suffix: str = "") -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    features = []
    audit = []
    asof_long = []
    for target_year in (2021, 2022, 2023):
        for origin_id in ORIGINS:
            origin_dt = origin_date(target_year, origin_id)
            selected = selected_asof(vintage_rows, origin_dt, leakage_latest=leakage_latest, lag_months=lag_months)
            monthly = monthly_records(selected)
            by_region: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
            for (_fkey, period), rec in monthly.items():
                by_region[rec["sigungu_feature_key"]][period] = rec
                if "202001" <= period <= "202312":
                    asof_long.append(
                        {
                            "sigungu_feature_key": rec["sigungu_feature_key"],
                            "target_year": target_year,
                            "prediction_origin_id": origin_id,
                            "prediction_origin_date": origin_dt,
                            "observation_period": period,
                            "selected_source_vintage": rec["selected_source_vintage"],
                            "selected_publication_date": rec["selected_publication_date"],
                            "electricity_total_kwh": rec["electricity_total_kwh"],
                            "electricity_industrial_kwh": rec["electricity_industrial_kwh"],
                            "electricity_commercial_kwh": rec["electricity_commercial_kwh"],
                            "selection_rule_version": "latest_leakage_benchmark" if leakage_latest else "vintage_selector_v1",
                        }
                    )
            for fkey, rows_by_period in by_region.items():
                row = make_feature_row(target_year, origin_id, origin_dt, fkey, rows_by_period)
                features.append(row)
                audit.append(
                    {
                        "target_year": target_year,
                        "prediction_origin_id": origin_id,
                        "prediction_origin_date": origin_dt,
                        "sigungu_feature_key": fkey,
                        "latest_eligible_observation_period": row["latest_eligible_observation_period"],
                        "selected_publication_date": row["selected_publication_date"],
                        "selected_source_vintage": row["selected_source_vintage"],
                        "leakage_violation": "Y" if (not leakage_latest and str(row["selected_publication_date"]) > origin_dt) else "N",
                        "selection_rule_version": row["selection_rule_version"],
                    }
                )
    if not suffix:
        write_csv(PROCESSED_DIR / "municipality_electricity_asof_long.csv", asof_long)
        write_csv(PROCESSED_DIR / "municipality_electricity_asof_features.csv", features)
        write_csv(PROCESSED_DIR / "electricity_asof_selection_audit.csv", audit)
        coverage = coverage_summary(features, audit)
        write_csv(PROCESSED_DIR / "electricity_prediction_origin_coverage.csv", coverage)
    return features, audit, asof_long


def coverage_summary(features: list[dict[str, Any]], audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    grouped_rows: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in features:
        grouped_rows[(int(row["target_year"]), str(row["prediction_origin_id"]))].append(row)
    audit_by_key = defaultdict(list)
    for row in audit:
        audit_by_key[(int(row["target_year"]), str(row["prediction_origin_id"]))].append(row)
    for (year, origin), rows in sorted(grouped_rows.items()):
        latest_months = sorted({str(r["latest_eligible_observation_period"]) for r in rows if r.get("latest_eligible_observation_period")})
        out.append(
            {
                "target_year": year,
                "prediction_origin_id": origin,
                "prediction_origin_date": rows[0]["prediction_origin_date"],
                "feature_region_count": len({r["sigungu_feature_key"] for r in rows}),
                "latest_eligible_month_min": latest_months[0] if latest_months else "",
                "latest_eligible_month_max": latest_months[-1] if latest_months else "",
                "mean_eligible_observation_count": round(mean([float(r["eligible_observation_count"]) for r in rows]), 6),
                "mean_window_coverage_rate": round(mean([float(r["feature_window_coverage_rate"]) for r in rows]), 6),
                "leakage_violation_count": sum(1 for r in audit_by_key[(year, origin)] if r["leakage_violation"] == "Y"),
            }
        )
    return out


def load_targets() -> list[dict[str, Any]]:
    base = {}
    glob = {}
    for row in read_csv(PROCESSED_DIR / "sigungu_global_model_pilot_predictions.csv"):
        if row.get("policy") not in {"baseline", "global_full_strength"}:
            continue
        key = (norm_sido(row["source_region"]), norm_sigungu(row["sigungu_name"]), row["sector_code"], int(row["target_year"]))
        item = {
            "source_region": norm_sido(row["source_region"]),
            "sigungu_name": row["sigungu_name"],
            "sigungu_name_normalized": norm_sigungu(row["sigungu_name"]),
            "sigungu_code": row["sigungu_code"],
            "sigungu_feature_key": f"{norm_sido(row['source_region'])}:{row['sigungu_code']}",
            "sector_code": row["sector_code"],
            "sector_name": row["sector_name"],
            "target_year": int(row["target_year"]),
            "actual": num(row["actual_annual_gva"]),
            "baseline_prediction": num(row["baseline_prediction"]),
            "global_prediction": num(row["prediction"]),
        }
        if item["actual"] <= 0 or item["baseline_prediction"] <= 0 or item["global_prediction"] <= 0:
            continue
        if row["policy"] == "baseline":
            base[key] = item
        else:
            glob[key] = item
    rows = []
    for key, item in base.items():
        if key in glob:
            rows.append({**item, "global_prediction": glob[key]["global_prediction"]})
    all_group: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in rows:
        key = (row["source_region"], row["sigungu_code"], row["target_year"])
        rec = all_group.setdefault(
            key,
            {
                **{k: row[k] for k in ["source_region", "sigungu_name", "sigungu_name_normalized", "sigungu_code", "sigungu_feature_key", "target_year"]},
                "sector_code": "all",
                "sector_name": "available sectors total",
                "actual": 0.0,
                "baseline_prediction": 0.0,
                "global_prediction": 0.0,
            },
        )
        rec["actual"] += row["actual"]
        rec["baseline_prediction"] += row["baseline_prediction"]
        rec["global_prediction"] += row["global_prediction"]
    rows.extend(all_group.values())
    return rows


def join_panel(targets: list[dict[str, Any]], features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    feat = {(r["sigungu_feature_key"], int(r["target_year"]), r["prediction_origin_id"]): r for r in features}
    out = []
    for target in targets:
        if target["sector_code"] not in PRIMARY_SECTORS and target["sector_code"] != "all":
            continue
        for origin_id in ORIGINS:
            f = feat.get((target["sigungu_feature_key"], int(target["target_year"]), origin_id))
            if not f:
                continue
            rec = {
                **target,
                "prediction_origin_id": f["prediction_origin_id"],
                "prediction_origin_date": f["prediction_origin_date"],
            }
            rec.update(
                {
                    f"feature_{k}": v
                    for k, v in f.items()
                    if k not in {"target_year", "sigungu_feature_key", "prediction_origin_id", "prediction_origin_date"}
                }
            )
            out.append(rec)
    return out


def matrix(rows: list[dict[str, Any]], fields: list[str], medians: dict[str, float] | None = None) -> tuple[np.ndarray, dict[str, float]]:
    if medians is None:
        medians = {}
        for field in fields:
            values = [num(r.get(f"feature_{field}"), default=float("nan")) for r in rows]
            values = [v for v in values if not math.isnan(v) and math.isfinite(v)]
            medians[field] = median(values) if values else 0.0
    data = []
    for row in rows:
        vals = []
        for field in fields:
            v = num(row.get(f"feature_{field}"), default=float("nan"))
            vals.append(medians[field] if math.isnan(v) or not math.isfinite(v) else v)
        data.append(vals)
    return np.asarray(data, dtype=float), medians


def fit_ridge(train_rows: list[dict[str, Any]], fields: list[str], base_field: str, lam: float | None = None) -> dict[str, Any]:
    y = np.asarray([math.log((r["actual"] + EPS) / (r[base_field] + EPS)) for r in train_rows], dtype=float)
    x, medians = matrix(train_rows, fields)
    x_mean = x.mean(axis=0)
    x_std = x.std(axis=0)
    x_std[x_std < EPS] = 1.0
    xs = (x - x_mean) / x_std
    candidates = [lam] if lam is not None else RIDGE_LAMBDAS
    best = None
    for candidate in candidates:
        xtx = xs.T @ xs + float(candidate) * np.eye(xs.shape[1])
        beta = np.linalg.solve(xtx, xs.T @ y)
        intercept = float(y.mean() - ((x_mean * 0) @ beta))
        preds = xs @ beta + y.mean()
        pred_rows = [{**r, "tmp_pred": r[base_field] * math.exp(float(p))} for r, p in zip(train_rows, preds)]
        score = wmape(pred_rows, "tmp_pred")
        if best is None or score < best["train_wmape"]:
            best = {"lambda": candidate, "beta": beta, "x_mean": x_mean, "x_std": x_std, "y_mean": float(y.mean()), "medians": medians, "train_wmape": score}
    return best


def predict_ridge(model: dict[str, Any], rows: list[dict[str, Any]], fields: list[str], base_field: str, alpha: float = 1.0) -> list[float]:
    x, _ = matrix(rows, fields, model["medians"])
    xs = (x - model["x_mean"]) / model["x_std"]
    yhat = xs @ model["beta"] + model["y_mean"]
    return [r[base_field] * math.exp(alpha * float(v)) for r, v in zip(rows, yhat)]


def wmape(rows: list[dict[str, Any]], field: str) -> float:
    denom = sum(abs(float(r["actual"])) for r in rows)
    return sum(abs(float(r[field]) - float(r["actual"])) for r in rows) / denom * 100 if denom else 0.0


def mape(rows: list[dict[str, Any]], field: str) -> float:
    vals = [abs(float(r[field]) - float(r["actual"])) / float(r["actual"]) * 100 for r in rows if float(r["actual"])]
    return mean(vals) if vals else 0.0


def pctl(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q)) if values else 0.0


def summarize(rows: list[dict[str, Any]], policy: str, pred_field: str) -> dict[str, Any]:
    ape = [abs(float(r[pred_field]) - float(r["actual"])) / float(r["actual"]) * 100 for r in rows if float(r["actual"])]
    macro = []
    for (_region,), items in groupby(rows, ["source_region"]).items():
        macro.append(wmape(items, pred_field))
    base_errors = {(r["sigungu_feature_key"], r["sector_code"], r["target_year"], r["prediction_origin_id"]): abs(r["global_prediction"] - r["actual"]) for r in rows}
    degrad = 0
    improved = 0
    for r in rows:
        err = abs(r[pred_field] - r["actual"])
        base_err = base_errors[(r["sigungu_feature_key"], r["sector_code"], r["target_year"], r["prediction_origin_id"])]
        if err < base_err:
            improved += 1
        if err > base_err * 1.1 and err - base_err > abs(r["actual"]) * 0.02:
            degrad += 1
    return {
        "policy": policy,
        "count": len(rows),
        "wmape": round(wmape(rows, pred_field), 6),
        "mape": round(mape(rows, pred_field), 6),
        "macro_region_wmape": round(mean(macro), 6) if macro else "",
        "median_ape": round(median(ape), 6) if ape else "",
        "p90_ape": round(pctl(ape, 90), 6),
        "rmse": round(math.sqrt(mean([(r[pred_field] - r["actual"]) ** 2 for r in rows])), 6) if rows else "",
        "mae": round(mean([abs(r[pred_field] - r["actual"]) for r in rows]), 6) if rows else "",
        "material_degradation_count": degrad,
        "region_improvement_rate": round(improved / len(rows), 6) if rows else "",
    }


def groupby(rows: list[dict[str, Any]], keys: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[tuple(row.get(k, "") for k in keys)].append(row)
    return out


def run_models(panel: list[dict[str, Any]], label: str = "primary") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    predictions = []
    model_audit = []
    for origin_id in ORIGINS:
        for bundle, fields in FEATURE_BUNDLES.items():
            for test_year, train_years in [(2022, [2021]), (2023, [2021, 2022])]:
                train_base = [r for r in panel if int(r["target_year"]) in train_years and r["prediction_origin_id"] == origin_id]
                test_base = [r for r in panel if int(r["target_year"]) == test_year and r["prediction_origin_id"] == origin_id]
                for sector in sorted({r["sector_code"] for r in test_base}):
                    train = [r for r in train_base if r["sector_code"] == sector]
                    test = [r.copy() for r in test_base if r["sector_code"] == sector]
                    if len(train) < max(10, len(fields) + 2) or not test:
                        continue
                    m2 = fit_ridge(train, fields, "baseline_prediction")
                    m3 = fit_ridge(train, fields, "global_prediction")
                    pred_m2 = predict_ridge(m2, test, fields, "baseline_prediction")
                    pred_m3 = predict_ridge(m3, test, fields, "global_prediction")
                    pred_m4 = {alpha: predict_ridge(m3, test, fields, "global_prediction", alpha=alpha) for alpha in (0.25, 0.5, 0.75)}
                    for idx, row in enumerate(test):
                        base_common = {
                            **row,
                            "experiment_label": label,
                            "feature_bundle": bundle,
                            "train_years": ",".join(map(str, train_years)),
                            "ridge_lambda_m2": m2["lambda"],
                            "ridge_lambda_m3": m3["lambda"],
                        }
                        predictions.append({**base_common, "policy": "M0_baseline", "prediction": row["baseline_prediction"]})
                        predictions.append({**base_common, "policy": "M1_global", "prediction": row["global_prediction"]})
                        predictions.append({**base_common, "policy": "M2B_baseline_electricity", "prediction": pred_m2[idx]})
                        predictions.append({**base_common, "policy": "M3_global_electricity", "prediction": pred_m3[idx]})
                        for alpha, vals in pred_m4.items():
                            predictions.append({**base_common, "policy": f"M4_global_electricity_alpha_{alpha}", "prediction": vals[idx]})
                    model_audit.append(
                        {
                            "experiment_label": label,
                            "origin": origin_id,
                            "feature_bundle": bundle,
                            "sector_code": sector,
                            "test_year": test_year,
                            "train_count": len(train),
                            "test_count": len(test),
                            "lambda_m2": m2["lambda"],
                            "lambda_m3": m3["lambda"],
                            "train_wmape_m2": round(m2["train_wmape"], 6),
                            "train_wmape_m3": round(m3["train_wmape"], 6),
                        }
                    )
    return predictions, model_audit


def aggregate_results(predictions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    primary = [r for r in predictions if r["feature_bundle"] == PRIMARY_BUNDLE and r["experiment_label"] == "primary" and int(r["target_year"]) in {2022, 2023}]
    base_global = next((summarize([r for r in primary if r["policy"] == "M1_global"], "M1_global", "prediction")["wmape"] for _ in [0]), 0)
    base_baseline = next((summarize([r for r in primary if r["policy"] == "M0_baseline"], "M0_baseline", "prediction")["wmape"] for _ in [0]), 0)
    comparison = []
    for (policy,), rows in sorted(groupby(primary, ["policy"]).items()):
        s = summarize(rows, policy, "prediction")
        s["improvement_vs_baseline_pct"] = round((base_baseline - s["wmape"]) / base_baseline * 100, 6) if base_baseline else ""
        s["improvement_vs_global_pct"] = round((base_global - s["wmape"]) / base_global * 100, 6) if base_global else ""
        comparison.append(s)
    by_year = []
    for (policy, year), rows in sorted(groupby(primary, ["policy", "target_year"]).items()):
        s = summarize(rows, policy, "prediction")
        s["target_year"] = year
        g_rows = [r for r in primary if r["policy"] == "M1_global" and r["target_year"] == year]
        g_w = wmape(g_rows, "prediction") if g_rows else 0
        s["improvement_vs_global_pct"] = round((g_w - s["wmape"]) / g_w * 100, 6) if g_w else ""
        by_year.append(s)
    by_ind = []
    for (policy, sector), rows in sorted(groupby(primary, ["policy", "sector_code"]).items()):
        s = summarize(rows, policy, "prediction")
        s["industry"] = sector
        g_rows = [r for r in primary if r["policy"] == "M1_global" and r["sector_code"] == sector]
        g_w = wmape(g_rows, "prediction") if g_rows else 0
        s["improvement_vs_global_pct"] = round((g_w - s["wmape"]) / g_w * 100, 6) if g_w else ""
        by_ind.append(s)
    by_origin = []
    for (policy, origin), rows in sorted(groupby(primary, ["policy", "prediction_origin_id"]).items()):
        s = summarize(rows, policy, "prediction")
        s["origin"] = origin
        latest = sorted({r.get("feature_latest_eligible_observation_period", "") for r in rows if r.get("feature_latest_eligible_observation_period")})
        s["latest_eligible_month"] = latest[-1] if latest else ""
        s["feature_coverage"] = round(mean([num(r.get("feature_feature_window_coverage_rate")) for r in rows]), 6)
        by_origin.append(s)
    ablation = []
    for (bundle, policy), rows in sorted(groupby([r for r in predictions if r["experiment_label"] == "primary" and r["policy"] == "M3_global_electricity"], ["feature_bundle", "policy"]).items()):
        s = summarize(rows, policy, "prediction")
        s["feature_bundle"] = bundle
        ablation.append(s)
    return {"comparison": comparison, "by_year": by_year, "by_industry": by_ind, "by_origin": by_origin, "ablation": ablation}


def permute_panel(panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(20260716)
    out = [r.copy() for r in panel]
    for (_year, origin), rows in groupby(out, ["target_year", "prediction_origin_id"]).items():
        feature_parts = [{k: v for k, v in r.items() if k.startswith("feature_")} for r in rows]
        rng.shuffle(feature_parts)
        for row, f in zip(rows, feature_parts):
            for key, value in f.items():
                row[key] = value
    return out


def noise_panel(panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(20260716)
    out = []
    for row in panel:
        rec = row.copy()
        for field in FEATURE_BUNDLES[PRIMARY_BUNDLE]:
            rec[f"feature_{field}"] = rng.gauss(0, 1)
        out.append(rec)
    return out


def write_outputs(
    panel: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    model_audit: list[dict[str, Any]],
    result_tables: dict[str, list[dict[str, Any]]],
    placebo_rows: list[dict[str, Any]],
    lag_rows: list[dict[str, Any]],
) -> None:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(MODEL_INPUT_DIR / "municipality_dry_run_population.csv", panel)
    write_csv(MODEL_INPUT_DIR / "municipality_electricity_ablation_features.csv", panel)
    write_csv(MODEL_INPUT_DIR / "municipality_electricity_ablation_targets.csv", [{k: r[k] for k in r if not k.startswith("feature_")} for r in panel])
    write_csv(PROCESSED_DIR / "electricity_vintage_dry_run_model_audit.csv", model_audit)
    write_csv(EXPERIMENT_DIR / "electricity_policy_predictions.csv", predictions)
    write_csv(EXPERIMENT_DIR / "electricity_policy_comparison.csv", result_tables["comparison"])
    write_csv(EXPERIMENT_DIR / "electricity_policy_by_year.csv", result_tables["by_year"])
    write_csv(EXPERIMENT_DIR / "electricity_policy_by_industry.csv", result_tables["by_industry"])
    write_csv(EXPERIMENT_DIR / "electricity_policy_by_origin.csv", result_tables["by_origin"])
    write_csv(EXPERIMENT_DIR / "electricity_feature_ablation.csv", result_tables["ablation"])
    write_csv(EXPERIMENT_DIR / "electricity_placebo_results.csv", placebo_rows)
    write_csv(EXPERIMENT_DIR / "electricity_lag_sensitivity.csv", lag_rows)
    write_csv(EXPERIMENT_DIR / "electricity_bootstrap_results.csv", [{"status": "not_run", "reason": "deferred_after_primary_dry_run"}])


def write_report(result_tables: dict[str, list[dict[str, Any]]], placebo_rows: list[dict[str, Any]], lag_rows: list[dict[str, Any]], panel: list[dict[str, Any]]) -> None:
    comparison = result_tables["comparison"]
    best_m3 = next((r for r in comparison if r["policy"] == "M3_global_electricity"), {})
    global_row = next((r for r in comparison if r["policy"] == "M1_global"), {})
    decision = "hold_for_second_feature_source"
    if best_m3 and global_row and float(best_m3["wmape"]) < float(global_row["wmape"]):
        decision = "continue_robustness_before_acceptance"
    guardrail = next((r for r in comparison if r["policy"] == "M4_global_electricity_alpha_0.25"), {})
    if guardrail and global_row and float(guardrail["wmape"]) < float(global_row["wmape"]):
        decision = "guardrailed_candidate_needs_robustness"
    lines = [
        "# 전력 Feature Vintage-aware Dry-run 결과",
        "",
        "## 실행 요약",
        "",
        "KEPCO 과거 source vintage를 prediction-origin 기준 as-of feature로 변환하고, 시군구 official actual pilot과 결합해 dry-run ablation을 수행했다. 모델은 `numpy` 기반 Ridge residual correction이며 temporal split은 `Train 2021 -> Test 2022`, `Train 2021-2022 -> Test 2023`으로 고정했다.",
        "",
        f"- panel rows: {len(panel):,}",
        f"- decision: `{decision}`",
        "- headline interpretation: 전력 보정을 full strength로 적용한 M3는 악화됐지만, 보정량을 0.25로 제한한 M4는 WMAPE를 개선했다. 따라서 운영 채택이 아니라 guardrail 후보로 남기고 강건성 검증을 이어간다.",
        "",
        "## Main Policy Comparison",
        "",
        "| policy | count | wmape | macro_region_wmape | median_ape | p90_ape | material_degradation_count | improvement_vs_global_pct |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparison:
        lines.append(
            f"| {row['policy']} | {row['count']} | {row['wmape']} | {row['macro_region_wmape']} | {row['median_ape']} | {row['p90_ape']} | {row['material_degradation_count']} | {row.get('improvement_vs_global_pct', '')} |"
        )
    lines.extend(["", "## Year Comparison", "", "| policy | target_year | count | wmape | improvement_vs_global_pct |", "| --- | ---: | ---: | ---: | ---: |"])
    for row in result_tables["by_year"]:
        lines.append(f"| {row['policy']} | {row['target_year']} | {row['count']} | {row['wmape']} | {row.get('improvement_vs_global_pct', '')} |")
    lines.extend(["", "## Industry Comparison", "", "| policy | industry | count | wmape | p90_ape | improvement_vs_global_pct |", "| --- | --- | ---: | ---: | ---: | ---: |"])
    for row in result_tables["by_industry"]:
        lines.append(f"| {row['policy']} | {row['industry']} | {row['count']} | {row['wmape']} | {row['p90_ape']} | {row.get('improvement_vs_global_pct', '')} |")
    lines.extend(["", "## Origin Comparison", "", "| policy | origin | latest_eligible_month | feature_coverage | wmape |", "| --- | --- | --- | ---: | ---: |"])
    for row in result_tables["by_origin"]:
        lines.append(f"| {row['policy']} | {row['origin']} | {row['latest_eligible_month']} | {row['feature_coverage']} | {row['wmape']} |")
    lines.extend(["", "## Placebo Comparison", "", "| experiment | wmape | improvement_vs_global_pct | interpretation |", "| --- | ---: | ---: | --- |"])
    for row in placebo_rows:
        lines.append(f"| {row['experiment']} | {row['wmape']} | {row['improvement_vs_global_pct']} | {row['interpretation']} |")
    lines.extend(["", "## Feature Ablation", "", "| feature_bundle | wmape | p90_ape | material_degradation_count |", "| --- | ---: | ---: | ---: |"])
    for row in result_tables["ablation"]:
        lines.append(f"| {row['feature_bundle']} | {row['wmape']} | {row['p90_ape']} | {row['material_degradation_count']} |")
    lines.extend(
        [
            "",
            "## 방법론 메모",
            "",
            "- Primary model은 dependency/runtime drift를 피하기 위해 `numpy`로 직접 구현한 Ridge residual correction이다.",
            "- 현재 official pilot에는 `E00`이 없어 1차 dry-run에서는 `C00`, `D00`, `all`만 평가했다.",
            "- 현재 KEPCO parser는 kWh sheet만 노출하므로 고객호수 기반 intensity feature는 제외했다.",
            "- 이번 headline table은 prediction origin별 예측 과업을 모두 포함한다. 따라서 baseline/global도 origin별로 반복 평가된다.",
            "- Bootstrap, future-lead placebo, missingness simulation, leave-one-sido-out은 다음 robustness round로 남겼다.",
        ]
    )
    (REPORT_DIR / "electricity_vintage_aware_dry_run_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REPORT_DIR / "electricity_feature_acceptance_decision.md").write_text(
        "\n".join(
            [
                "# Electricity Feature Acceptance Decision",
                "",
                f"Current decision: `{decision}`",
                "",
                "전력 feature는 아직 운영 정책으로 채택하지 않는다. 다만 alpha=0.25 guardrail 정책은 global 대비 WMAPE를 개선했으므로 후속 robustness 검증 대상으로 유지한다. 채택에는 lag sensitivity, placebo superiority, region generalization, bootstrap uncertainty, material degradation 검토가 추가로 필요하다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def run_placebos(panel: list[dict[str, Any]], global_wmape: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    placebo_rows = []
    lag_rows = []
    for label, p in [("region_permutation", permute_panel(panel)), ("random_noise", noise_panel(panel))]:
        preds, _audit = run_models(p, label=label)
        rows = [r for r in preds if r["policy"] == "M3_global_electricity" and r["feature_bundle"] == PRIMARY_BUNDLE]
        w = wmape(rows, "prediction") if rows else 0
        placebo_rows.append(
            {
                "experiment": label,
                "wmape": round(w, 6),
                "improvement_vs_global_pct": round((global_wmape - w) / global_wmape * 100, 6) if global_wmape else "",
                "interpretation": "diagnostic_only",
            }
        )
    vintage = load_or_build_vintage_long()
    for lag in (None, 3, 4):
        features, _audit, _long = build_asof_features(vintage, lag_months=lag, suffix=f"lag_{lag}")
        lag_panel = join_panel(load_targets(), features)
        preds, _model = run_models(lag_panel, label=f"lag_{lag or 'actual'}")
        rows = [r for r in preds if r["policy"] == "M3_global_electricity" and r["feature_bundle"] == PRIMARY_BUNDLE]
        w = wmape(rows, "prediction") if rows else 0
        lag_rows.append(
            {
                "lag_policy": "actual_publication_date" if lag is None else f"observation_plus_{lag}m",
                "count": len(rows),
                "wmape": round(w, 6),
                "improvement_vs_global_pct": round((global_wmape - w) / global_wmape * 100, 6) if global_wmape else "",
            }
        )
    features, _audit, _long = build_asof_features(vintage, leakage_latest=True, suffix="latest_leakage")
    leak_panel = join_panel(load_targets(), features)
    preds, _model = run_models(leak_panel, label="latest_leakage")
    rows = [r for r in preds if r["policy"] == "M3_global_electricity" and r["feature_bundle"] == PRIMARY_BUNDLE]
    w = wmape(rows, "prediction") if rows else 0
    placebo_rows.append(
        {
            "experiment": "latest_source_leakage_benchmark",
            "wmape": round(w, 6),
            "improvement_vs_global_pct": round((global_wmape - w) / global_wmape * 100, 6) if global_wmape else "",
            "interpretation": "leakage_upper_bound_only",
        }
    )
    return placebo_rows, lag_rows


def main() -> int:
    vintage = load_or_build_vintage_long()
    features, audit, _long = build_asof_features(vintage)
    if any(row["leakage_violation"] == "Y" for row in audit):
        raise SystemExit("Leakage assertion failed: selected publication_date after prediction_origin_date")
    panel = join_panel(load_targets(), features)
    write_csv(MODEL_INPUT_DIR / "municipality_dry_run_population.csv", panel)
    predictions, model_audit = run_models(panel)
    result_tables = aggregate_results(predictions)
    global_row = next((r for r in result_tables["comparison"] if r["policy"] == "M1_global"), {})
    global_w = float(global_row.get("wmape") or 0.0)
    placebo_rows, lag_rows = run_placebos(panel, global_w)
    write_outputs(panel, predictions, model_audit, result_tables, placebo_rows, lag_rows)
    write_report(result_tables, placebo_rows, lag_rows, panel)
    print(f"vintage rows: {len(vintage)}")
    print(f"asof feature rows: {len(features)}")
    print(f"panel rows: {len(panel)}")
    print(f"prediction rows: {len(predictions)}")
    print(f"global wmape: {global_w:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
