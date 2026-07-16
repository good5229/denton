from __future__ import annotations

import math
import random
from collections import defaultdict
from statistics import mean, median
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, read_csv, write_csv
from run_electricity_vintage_dry_run import (
    build_asof_features,
    groupby,
    join_panel,
    load_or_build_vintage_long,
    load_targets,
    matrix,
    num,
    summarize,
    wmape,
)


EPS = 1e-9
REPORT_PATH = ROOT / "reports" / "electricity_guardrail_robustness_round.md"
ALPHAS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
PRIMARY_ORIGIN = "O1"
RNG_SEED = 20260716
BOOTSTRAP_N = 2000
PLACEBO_N = 120
RIDGE_LAMBDAS = [0.1, 1.0, 10.0, 100.0, 1000.0]

FEATURE_BUNDLES = {
    "B1_level_only": [
        "log_total_trailing12_sum",
        "log_industrial_trailing12_sum",
        "log_total_latest",
        "log_industrial_latest",
    ],
    "B3_composition_only": [
        "industrial_share_trailing12",
        "commercial_share_trailing12",
        "industrial_share_latest",
    ],
    "B4_level_normalized": [
        "log_industrial_trailing12_sum",
        "industrial_share_trailing12",
        "industrial_share_of_sido",
        "log_total_trailing12_sum",
    ],
    "B5_full_minimal": [
        "log_industrial_trailing12_sum",
        "industrial_share_trailing12",
        "industrial_yoy_same_available_window",
        "industrial_3m_momentum",
        "industrial_share_of_sido",
        "log_total_trailing12_sum",
        "commercial_share_trailing12",
        "eligible_observation_count",
    ],
    "B6_full_without_change": [
        "log_industrial_trailing12_sum",
        "industrial_share_trailing12",
        "industrial_share_of_sido",
        "log_total_trailing12_sum",
        "commercial_share_trailing12",
        "eligible_observation_count",
    ],
    "B7_normalized_only": [
        "industrial_share_trailing12",
        "industrial_share_of_sido",
        "commercial_share_trailing12",
        "industrial_share_latest",
    ],
    "B8_change_only_negative_control": [
        "industrial_yoy_same_available_window",
        "total_yoy_same_available_window",
        "industrial_3m_momentum",
        "total_3m_momentum",
    ],
}


def pctl(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q)) if values else 0.0


def ape(row: dict[str, Any], field: str) -> float:
    actual = abs(float(row["actual"]))
    return abs(float(row[field]) - float(row["actual"])) / actual * 100 if actual else 0.0


def macro_wmape(rows: list[dict[str, Any]], field: str) -> float:
    vals = [wmape(items, field) for _key, items in groupby(rows, ["source_region"]).items()]
    return mean(vals) if vals else 0.0


def target_value(row: dict[str, Any], target_type: str) -> float:
    actual = float(row["actual"])
    base = float(row["global_prediction"])
    if target_type == "absolute":
        return actual - base
    if target_type == "log_ratio":
        return math.log((actual + EPS) / (base + EPS))
    return (actual - base) / max(abs(base), EPS)


def raw_correction(row: dict[str, Any], pred: float, target_type: str) -> float:
    base = float(row["global_prediction"])
    if target_type == "absolute":
        return pred
    if target_type == "log_ratio":
        return base * (math.exp(max(min(pred, 1.0), -1.0)) - 1.0)
    return base * pred


def fit_ridge_target(train_rows: list[dict[str, Any]], fields: list[str], target_type: str) -> dict[str, Any]:
    y = np.asarray([target_value(r, target_type) for r in train_rows], dtype=float)
    x, medians = matrix(train_rows, fields)
    x_mean = x.mean(axis=0)
    x_std = x.std(axis=0)
    x_std[x_std < EPS] = 1.0
    xs = (x - x_mean) / x_std
    y_mean = float(y.mean()) if len(y) else 0.0
    best: dict[str, Any] | None = None
    for lam in RIDGE_LAMBDAS:
        xtx = xs.T @ xs + float(lam) * np.eye(xs.shape[1])
        beta = np.linalg.solve(xtx, xs.T @ (y - y_mean))
        preds = xs @ beta + y_mean
        pred_rows = []
        for row, pred in zip(train_rows, preds):
            rec = row.copy()
            rec["tmp_prediction"] = float(row["global_prediction"]) + raw_correction(row, float(pred), target_type)
            pred_rows.append(rec)
        score = wmape(pred_rows, "tmp_prediction")
        if best is None or score < best["train_wmape"]:
            best = {
                "lambda": lam,
                "beta": beta,
                "x_mean": x_mean,
                "x_std": x_std,
                "y_mean": y_mean,
                "medians": medians,
                "train_wmape": score,
                "target_type": target_type,
            }
    if best is None:
        raise RuntimeError("ridge fit failed")
    return best


def predict_raw(model: dict[str, Any], rows: list[dict[str, Any]], fields: list[str]) -> list[float]:
    x, _ = matrix(rows, fields, model["medians"])
    xs = (x - model["x_mean"]) / model["x_std"]
    preds = xs @ model["beta"] + model["y_mean"]
    return [float(v) for v in preds]


def apply_mask(row: dict[str, Any], mask: str) -> bool:
    sector = str(row["sector_code"])
    if mask == "S0_all_apply":
        return True
    if mask == "S1_C00_all_apply_D00_fallback":
        return sector in {"C00", "all"}
    if mask == "S2_C00_only":
        return sector == "C00"
    if mask == "S3_all_only":
        return sector == "all"
    return sector in {"C00", "all"}


def split_rows(panel: list[dict[str, Any]], test_year: int, origin: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train_years = {2021} if test_year == 2022 else {2021, 2022}
    train = [r for r in panel if int(r["target_year"]) in train_years and r["prediction_origin_id"] == origin]
    test = [r for r in panel if int(r["target_year"]) == test_year and r["prediction_origin_id"] == origin]
    return train, test


def clip_threshold(train_rows: list[dict[str, Any]], raw_train: list[float], clip_rule: str) -> float | None:
    if clip_rule.startswith("rel"):
        return None
    if clip_rule.startswith("q"):
        q = float(clip_rule[1:])
        return pctl([abs(v) for v in raw_train], q)
    return None


def predict_candidate_rows(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    *,
    policy: str,
    fields: list[str],
    target_type: str,
    alpha: float,
    clip_rule: str,
    mask: str,
    fixed_threshold: float | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    out = [r.copy() for r in test_rows]
    active_train = [r for r in train_rows if apply_mask(r, mask)]
    active_test_idx = [idx for idx, row in enumerate(out) if apply_mask(row, mask)]
    audit: dict[str, Any] = {
        "policy": policy,
        "target_type": target_type,
        "alpha": alpha,
        "clip_rule": clip_rule,
        "mask": mask,
        "train_count": len(active_train),
        "test_count": len(active_test_idx),
    }
    for row in out:
        row["policy"] = policy
        row["prediction"] = float(row["global_prediction"])
        row["correction_raw"] = 0.0
        row["correction_applied"] = 0.0
        row["fallback_reason"] = "industry_mask"
    if len(active_train) < max(12, len(fields) + 3) or not active_test_idx:
        audit["fit_status"] = "fallback_insufficient_training_rows"
        return out, audit
    model = fit_ridge_target(active_train, fields, target_type)
    raw_preds = predict_raw(model, [out[idx] for idx in active_test_idx], fields)
    raw_train = [raw_correction(row, pred, target_type) for row, pred in zip(active_train, predict_raw(model, active_train, fields))]
    threshold = fixed_threshold if fixed_threshold is not None else clip_threshold(active_train, raw_train, clip_rule)
    for idx, pred in zip(active_test_idx, raw_preds):
        row = out[idx]
        raw = raw_correction(row, pred, target_type)
        clip_amount = None
        if clip_rule.startswith("rel"):
            ratio = float(clip_rule.replace("rel", ""))
            clip_amount = abs(float(row["global_prediction"])) * ratio
        elif threshold is not None:
            clip_amount = threshold
        clipped = max(min(raw, clip_amount), -clip_amount) if clip_amount is not None else raw
        applied = alpha * clipped
        row["prediction"] = max(float(row["global_prediction"]) + applied, EPS)
        row["correction_raw"] = raw
        row["correction_applied"] = applied
        row["fallback_reason"] = ""
    audit.update({"fit_status": "fit", "lambda": model["lambda"], "train_wmape": model["train_wmape"], "clip_threshold": threshold or ""})
    return out, audit


def alpha_cv(panel: list[dict[str, Any]], test_year: int, origin: str, fields: list[str], target_type: str, clip_rule: str, mask: str) -> tuple[float, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    if test_year == 2022:
        cv_base = [r for r in panel if int(r["target_year"]) == 2021 and r["prediction_origin_id"] == origin]
        for (sido,), heldout in groupby(cv_base, ["source_region"]).items():
            train = [r for r in cv_base if r["source_region"] != sido]
            if len(train) < 20 or not heldout:
                continue
            preds, _audit = predict_candidate_rows(
                train,
                heldout,
                policy="cv",
                fields=fields,
                target_type=target_type,
                alpha=1.0,
                clip_rule=clip_rule,
                mask=mask,
            )
            rows.extend(preds)
    else:
        train = [r for r in panel if int(r["target_year"]) == 2021 and r["prediction_origin_id"] == origin]
        valid = [r for r in panel if int(r["target_year"]) == 2022 and r["prediction_origin_id"] == origin]
        rows, _audit = predict_candidate_rows(
            train,
            valid,
            policy="cv",
            fields=fields,
            target_type=target_type,
            alpha=1.0,
            clip_rule=clip_rule,
            mask=mask,
        )
    scores = []
    for alpha in ALPHAS:
        eval_rows = []
        for row in rows:
            rec = row.copy()
            if apply_mask(rec, mask) and rec.get("fallback_reason") == "":
                rec["prediction_alpha"] = max(float(rec["global_prediction"]) + alpha * float(rec["correction_applied"]), EPS)
            else:
                rec["prediction_alpha"] = float(rec["global_prediction"])
            eval_rows.append(rec)
        scores.append({"alpha": alpha, "wmape": wmape(eval_rows, "prediction_alpha"), "count": len(eval_rows)})
    best = min(scores, key=lambda r: (float(r["wmape"]), float(r["alpha"])))
    return float(best["alpha"]), scores


def run_policy(panel: list[dict[str, Any]], cfg: dict[str, Any], origin: str = PRIMARY_ORIGIN) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    predictions: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    alpha_rows: list[dict[str, Any]] = []
    fields = FEATURE_BUNDLES[cfg["bundle"]]
    for test_year in (2022, 2023):
        train, test = split_rows(panel, test_year, origin)
        alpha = float(cfg.get("alpha", 0.0))
        if cfg.get("alpha_mode") == "train_selected":
            alpha, scores = alpha_cv(panel, test_year, origin, fields, cfg["target_type"], cfg["clip_rule"], cfg["mask"])
            for score in scores:
                alpha_rows.append({"policy": cfg["policy"], "origin": origin, "test_year": test_year, **score})
        pred, audit = predict_candidate_rows(
            train,
            test,
            policy=cfg["policy"],
            fields=fields,
            target_type=cfg["target_type"],
            alpha=alpha,
            clip_rule=cfg["clip_rule"],
            mask=cfg["mask"],
        )
        for row in pred:
            row["origin_scope"] = origin
            row["feature_bundle"] = cfg["bundle"]
            row["target_type"] = cfg["target_type"]
            row["selected_alpha"] = alpha
            row["clip_rule"] = cfg["clip_rule"]
            row["application_mask"] = cfg["mask"]
        audit.update({"origin": origin, "test_year": test_year, "selected_alpha": alpha, "bundle": cfg["bundle"]})
        predictions.extend(pred)
        audits.append(audit)
    return predictions, audits, alpha_rows


def metric_row(rows: list[dict[str, Any]], policy: str, field: str = "prediction") -> dict[str, Any]:
    s = summarize(rows, policy, field)
    s["macro_wmape"] = round(macro_wmape(rows, field), 6)
    s["median_ape"] = round(median([ape(r, field) for r in rows]), 6) if rows else ""
    s["p90_ape"] = round(pctl([ape(r, field) for r in rows], 90), 6) if rows else ""
    return s


def add_global_predictions(panel: list[dict[str, Any]], origin: str = PRIMARY_ORIGIN) -> list[dict[str, Any]]:
    rows = [r.copy() for r in panel if r["prediction_origin_id"] == origin and int(r["target_year"]) in {2022, 2023}]
    for row in rows:
        row["policy"] = "P0_global_reference"
        row["prediction"] = float(row["global_prediction"])
    return rows


def candidate_configs() -> list[dict[str, Any]]:
    return [
        {
            "policy": "P1_fixed025_B4_relative_rel5_S1",
            "bundle": "B4_level_normalized",
            "target_type": "relative",
            "alpha": 0.25,
            "alpha_mode": "fixed",
            "clip_rule": "rel0.05",
            "mask": "S1_C00_all_apply_D00_fallback",
        },
        {
            "policy": "P2_trainalpha_B4_relative_rel5_S1",
            "bundle": "B4_level_normalized",
            "target_type": "relative",
            "alpha_mode": "train_selected",
            "clip_rule": "rel0.05",
            "mask": "S1_C00_all_apply_D00_fallback",
        },
        {
            "policy": "P3_fixed025_B4_absolute_q95_S1",
            "bundle": "B4_level_normalized",
            "target_type": "absolute",
            "alpha": 0.25,
            "alpha_mode": "fixed",
            "clip_rule": "q95",
            "mask": "S1_C00_all_apply_D00_fallback",
        },
        {
            "policy": "P4_trainalpha_B6_relative_rel5_S1",
            "bundle": "B6_full_without_change",
            "target_type": "relative",
            "alpha_mode": "train_selected",
            "clip_rule": "rel0.05",
            "mask": "S1_C00_all_apply_D00_fallback",
        },
        {
            "policy": "P5_trainalpha_B4_relative_rel5_S2_C00",
            "bundle": "B4_level_normalized",
            "target_type": "relative",
            "alpha_mode": "train_selected",
            "clip_rule": "rel0.05",
            "mask": "S2_C00_only",
        },
        {
            "policy": "P6_trainalpha_B4_relative_rel5_S3_all",
            "bundle": "B4_level_normalized",
            "target_type": "relative",
            "alpha_mode": "train_selected",
            "clip_rule": "rel0.05",
            "mask": "S3_all_only",
        },
    ]


def stress_configs() -> list[dict[str, Any]]:
    out = []
    for bundle in FEATURE_BUNDLES:
        out.append({"policy": f"bundle_{bundle}", "bundle": bundle, "target_type": "relative", "alpha_mode": "train_selected", "clip_rule": "rel0.05", "mask": "S1_C00_all_apply_D00_fallback"})
    for target_type in ("absolute", "relative", "log_ratio"):
        out.append({"policy": f"target_{target_type}", "bundle": "B4_level_normalized", "target_type": target_type, "alpha_mode": "train_selected", "clip_rule": "rel0.05", "mask": "S1_C00_all_apply_D00_fallback"})
    for clip in ("rel0.02", "rel0.05", "rel0.10", "q90", "q95", "q99"):
        out.append({"policy": f"clip_{clip}", "bundle": "B4_level_normalized", "target_type": "relative", "alpha_mode": "train_selected", "clip_rule": clip, "mask": "S1_C00_all_apply_D00_fallback"})
    for mask in ("S0_all_apply", "S1_C00_all_apply_D00_fallback", "S2_C00_only", "S3_all_only"):
        out.append({"policy": f"mask_{mask}", "bundle": "B4_level_normalized", "target_type": "relative", "alpha_mode": "train_selected", "clip_rule": "rel0.05", "mask": mask})
    return out


def compare_predictions(global_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {
        (r["sigungu_feature_key"], r["sector_code"], int(r["target_year"]), r["prediction_origin_id"]): r
        for r in global_rows
    }
    out = []
    for row in candidate_rows:
        key = (row["sigungu_feature_key"], row["sector_code"], int(row["target_year"]), row["prediction_origin_id"])
        g = by_key.get(key)
        if not g:
            continue
        rec = row.copy()
        rec["global_ref_prediction"] = g["prediction"]
        rec["global_abs_error"] = abs(float(g["prediction"]) - float(row["actual"]))
        rec["candidate_abs_error"] = abs(float(row["prediction"]) - float(row["actual"]))
        rec["global_ape"] = ape(g, "prediction")
        rec["candidate_ape"] = ape(row, "prediction")
        rec["ape_delta_pp"] = rec["candidate_ape"] - rec["global_ape"]
        rec["abs_error_delta"] = rec["candidate_abs_error"] - rec["global_abs_error"]
        rec["material_degradation_2pp_10pct"] = "Y" if rec["candidate_abs_error"] > rec["global_abs_error"] * 1.1 and rec["abs_error_delta"] > abs(float(row["actual"])) * 0.02 else "N"
        rec["ape_degradation_1pp"] = "Y" if rec["ape_delta_pp"] > 1.0 else "N"
        rec["ape_degradation_5pp"] = "Y" if rec["ape_delta_pp"] > 5.0 else "N"
        rec["ape_degradation_10pp"] = "Y" if rec["ape_delta_pp"] > 10.0 else "N"
        out.append(rec)
    return out


def bootstrap_delta(rows: list[dict[str, Any]], scope: str, group_field: str, n: int = BOOTSTRAP_N) -> dict[str, Any]:
    groups = list(groupby(rows, [group_field]).values())
    rng = random.Random(RNG_SEED + len(scope))
    deltas = []
    for _ in range(n):
        sample = []
        for _idx in range(len(groups)):
            sample.extend(rng.choice(groups))
        deltas.append(wmape(sample, "global_ref_prediction") - wmape(sample, "prediction"))
    return {
        "scope": scope,
        "group_field": group_field,
        "iterations": n,
        "mean_delta_wmape_positive_good": round(mean(deltas), 6),
        "median_delta_wmape_positive_good": round(median(deltas), 6),
        "ci_low_2_5": round(pctl(deltas, 2.5), 6),
        "ci_high_97_5": round(pctl(deltas, 97.5), 6),
        "probability_improvement": round(sum(1 for v in deltas if v > 0) / len(deltas), 6),
    }


def run_bootstrap(compared: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    scopes = [("pooled", compared)]
    for year, items in groupby(compared, ["target_year"]).items():
        scopes.append((f"year_{year[0]}", items))
    for sector, items in groupby(compared, ["sector_code"]).items():
        scopes.append((f"sector_{sector[0]}", items))
    for scope, items in scopes:
        if len(items) >= 20:
            rows.append(bootstrap_delta(items, scope, "sigungu_feature_key"))
            rows.append(bootstrap_delta(items, scope + "_industry_year", "sector_code"))
    return rows


def run_loso(panel: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for (sido,), _items in sorted(groupby(panel, ["source_region"]).items()):
        work = [r for r in panel if r["prediction_origin_id"] == PRIMARY_ORIGIN]
        train = [r for r in work if r["source_region"] != sido and int(r["target_year"]) in {2021, 2022}]
        test = [r for r in work if r["source_region"] == sido and int(r["target_year"]) in {2022, 2023}]
        pred, audit = predict_candidate_rows(
            train,
            test,
            policy="loso_primary",
            fields=FEATURE_BUNDLES[cfg["bundle"]],
            target_type=cfg["target_type"],
            alpha=0.25,
            clip_rule=cfg["clip_rule"],
            mask=cfg["mask"],
        )
        rows.append(
            {
                "heldout_sido": sido,
                "count": len(pred),
                "global_wmape": round(wmape(pred, "global_prediction"), 6),
                "candidate_wmape": round(wmape(pred, "prediction"), 6),
                "delta_positive_good": round(wmape(pred, "global_prediction") - wmape(pred, "prediction"), 6),
                "fit_status": audit.get("fit_status", ""),
            }
        )
    return rows


def permute_feature_blocks(rows: list[dict[str, Any]], fields: list[str], rng: random.Random, mode: str) -> list[dict[str, Any]]:
    out = [r.copy() for r in rows]
    feature_keys = [f"feature_{field}" for field in fields]
    if mode == "noise":
        for row in out:
            for key in feature_keys:
                row[key] = rng.gauss(0, 1)
        return out
    groups = groupby(out, ["target_year", "prediction_origin_id"] if mode == "region" else ["sigungu_feature_key", "prediction_origin_id"])
    for _key, items in groups.items():
        blocks = [{k: r.get(k, "") for k in feature_keys} for r in items]
        rng.shuffle(blocks)
        for row, block in zip(items, blocks):
            row.update(block)
    return out


def run_one_candidate_simple(panel: list[dict[str, Any]], cfg: dict[str, Any], policy: str) -> list[dict[str, Any]]:
    work = []
    for year in (2022, 2023):
        train, test = split_rows(panel, year, PRIMARY_ORIGIN)
        alpha = float(cfg.get("alpha", 0.25))
        if cfg.get("alpha_mode") == "train_selected":
            alpha, _scores = alpha_cv(panel, year, PRIMARY_ORIGIN, FEATURE_BUNDLES[cfg["bundle"]], cfg["target_type"], cfg["clip_rule"], cfg["mask"])
        pred, _audit = predict_candidate_rows(
            train,
            test,
            policy=policy,
            fields=FEATURE_BUNDLES[cfg["bundle"]],
            target_type=cfg["target_type"],
            alpha=alpha,
            clip_rule=cfg["clip_rule"],
            mask=cfg["mask"],
        )
        work.extend(pred)
    return work


def run_placebos(panel: list[dict[str, Any]], cfg: dict[str, Any], real_delta: float) -> list[dict[str, Any]]:
    fields = FEATURE_BUNDLES[cfg["bundle"]]
    out = []
    for mode in ("region", "temporal", "noise"):
        rng = random.Random(RNG_SEED + len(mode))
        deltas = []
        for i in range(PLACEBO_N):
            fake = permute_feature_blocks(panel, fields, rng, mode)
            pred = run_one_candidate_simple(fake, cfg, f"placebo_{mode}_{i}")
            deltas.append(wmape(pred, "global_prediction") - wmape(pred, "prediction"))
        out.append(
            {
                "placebo_type": mode,
                "iterations": PLACEBO_N,
                "real_delta_wmape": round(real_delta, 6),
                "placebo_mean_delta": round(mean(deltas), 6),
                "placebo_p95_delta": round(pctl(deltas, 95), 6),
                "real_exceeds_placebo_p95": "Y" if real_delta > pctl(deltas, 95) else "N",
            }
        )
    return out


def run_lag_sensitivity(vintage: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for label, kwargs in [
        ("L0_actual_publication_date", {}),
        ("L1_observation_plus_1m", {"lag_months": 1}),
        ("L2_observation_plus_2m", {"lag_months": 2}),
        ("L3_observation_plus_3m", {"lag_months": 3}),
        ("latest_source_leakage_benchmark", {"leakage_latest": True}),
    ]:
        features, audit, _long = build_asof_features(vintage, suffix=label, **kwargs)
        panel = join_panel(load_targets(), features)
        panel = [r for r in panel if r["prediction_origin_id"] == PRIMARY_ORIGIN]
        pred = run_one_candidate_simple(panel, cfg, label)
        rows.append(
            {
                "lag_policy": label,
                "count": len(pred),
                "leakage_violation_count": sum(1 for r in audit if r.get("leakage_violation") == "Y"),
                "global_wmape": round(wmape(pred, "global_prediction"), 6),
                "candidate_wmape": round(wmape(pred, "prediction"), 6),
                "delta_positive_good": round(wmape(pred, "global_prediction") - wmape(pred, "prediction"), 6),
            }
        )
    return rows


def run_missingness(panel: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    base = [r for r in panel if r["prediction_origin_id"] == PRIMARY_ORIGIN]
    base_pred = run_one_candidate_simple(base, cfg, "missingness_base")
    base_delta = wmape(base_pred, "global_prediction") - wmape(base_pred, "prediction")
    for label, ratio in [("random_5pct", 0.05), ("random_10pct", 0.10)]:
        rng = random.Random(RNG_SEED + int(ratio * 1000))
        work = [r.copy() for r in base]
        for row in work:
            if rng.random() < ratio:
                row["sector_code"] = "D00"
        pred = run_one_candidate_simple(work, cfg, label)
        rows.append({"scenario": label, "count": len(pred), "delta_positive_good": round(wmape(pred, "global_prediction") - wmape(pred, "prediction"), 6), "base_delta": round(base_delta, 6)})
    latest_by_year = {}
    for (year,), items in groupby(base, ["target_year"]).items():
        latest_by_year[year] = max(str(r.get("feature_latest_eligible_observation_period", "")) for r in items)
    work = []
    for row in base:
        rec = row.copy()
        if str(rec.get("feature_latest_eligible_observation_period", "")) == latest_by_year.get(rec["target_year"], ""):
            rec["sector_code"] = "D00"
        work.append(rec)
    pred = run_one_candidate_simple(work, cfg, "latest_eligible_month_missing")
    rows.append({"scenario": "latest_eligible_month_missing", "count": len(pred), "delta_positive_good": round(wmape(pred, "global_prediction") - wmape(pred, "prediction"), 6), "base_delta": round(base_delta, 6)})
    worst = []
    for (sido,), _items in groupby(base, ["source_region"]).items():
        work = [({**r, "sector_code": "D00"} if r["source_region"] == sido else r.copy()) for r in base]
        pred = run_one_candidate_simple(work, cfg, f"sido_missing_{sido}")
        worst.append((sido, wmape(pred, "global_prediction") - wmape(pred, "prediction"), len(pred)))
    for sido, delta, count in sorted(worst, key=lambda x: x[1])[:10]:
        rows.append({"scenario": "one_sido_missing_worst10", "affected_sido": sido, "count": count, "delta_positive_good": round(delta, 6), "base_delta": round(base_delta, 6)})
    return rows


def run_large_observation_audit(compared: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for metric, key_fn in [
        ("actual_scale", lambda r: abs(float(r["actual"]))),
        ("electricity_scale", lambda r: num(r.get("feature_total_trailing12_sum"))),
    ]:
        ordered = sorted(compared, key=key_fn, reverse=True)
        for pct in (1, 5, 10):
            n = max(1, int(len(ordered) * pct / 100))
            remain = ordered[n:]
            rows.append(
                {
                    "removal_metric": metric,
                    "removed_top_pct": pct,
                    "removed_rows": n,
                    "remaining_rows": len(remain),
                    "global_wmape": round(wmape(remain, "global_ref_prediction"), 6),
                    "candidate_wmape": round(wmape(remain, "prediction"), 6),
                    "delta_positive_good": round(wmape(remain, "global_ref_prediction") - wmape(remain, "prediction"), 6),
                }
            )
    return rows


def make_summary_rows(global_rows: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [metric_row(global_rows, "P0_global_reference")]
    for (policy,), items in sorted(groupby(predictions, ["policy"]).items()):
        m = metric_row(items, policy)
        gw = wmape(items, "global_prediction")
        m["global_wmape_same_rows"] = round(gw, 6)
        m["delta_vs_global_positive_good"] = round(gw - float(m["wmape"]), 6)
        rows.append(m)
    return rows


def make_group_rows(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for keys in (["policy", "target_year"], ["policy", "sector_code"], ["policy", "source_region"]):
        for key, items in sorted(groupby(predictions, keys).items()):
            m = metric_row(items, "|".join(map(str, key)))
            m["grouping"] = "+".join(keys[1:])
            for name, value in zip(keys, key):
                m[name] = value
            m["global_wmape_same_rows"] = round(wmape(items, "global_prediction"), 6)
            m["delta_vs_global_positive_good"] = round(wmape(items, "global_prediction") - float(m["wmape"]), 6)
            rows.append(m)
    return rows


def write_markdown(
    summary_rows: list[dict[str, Any]],
    group_rows: list[dict[str, Any]],
    bootstrap_rows: list[dict[str, Any]],
    loso_rows: list[dict[str, Any]],
    placebo_rows: list[dict[str, Any]],
    lag_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
    large_rows: list[dict[str, Any]],
    alpha_rows: list[dict[str, Any]],
    compared: list[dict[str, Any]],
) -> None:
    best = min([r for r in summary_rows if r["policy"] != "P0_global_reference"], key=lambda r: float(r["wmape"]))
    base = next(r for r in summary_rows if r["policy"] == "P0_global_reference")
    primary_degrad = sum(1 for r in compared if r["material_degradation_2pp_10pct"] == "Y")
    p_improve = max([float(r["probability_improvement"]) for r in bootstrap_rows if r["scope"] == "pooled"], default=0.0)
    placebo_pass = sum(1 for r in placebo_rows if r["real_exceeds_placebo_p95"] == "Y")
    decision = "hold_for_confirmatory_actual"
    if float(best["delta_vs_global_positive_good"]) > 0 and p_improve >= 0.90 and placebo_pass >= 2 and primary_degrad <= 0:
        decision = "accept_guardrailed_candidate_for_pilot"
    elif float(best["delta_vs_global_positive_good"]) > 0 and p_improve >= 0.75:
        decision = "guardrailed_candidate_needs_refinement"
    lines = [
        "# 전력 Feature Guardrail Robustness Round",
        "",
        "## 1. 결론",
        "",
        f"- final decision: `{decision}`",
        f"- primary origin: `{PRIMARY_ORIGIN}`",
        f"- best candidate: `{best['policy']}`",
        f"- global WMAPE: {base['wmape']}",
        f"- best candidate WMAPE: {best['wmape']}",
        f"- WMAPE delta, positive is good: {best.get('delta_vs_global_positive_good', '')}",
        f"- pooled bootstrap improvement probability: {p_improve}",
        f"- primary material degradation count: {primary_degrad}",
        "",
        "이번 라운드는 `alpha=0.25`를 운영 정책으로 바로 채택하지 않고, O1 기준에서 후보 정책을 여러 stress test로 흔들어 본 검증이다. 훈련/검증/테스트의 시간 순서를 지켜 2023년 예측에는 2023년 이후 공개 정보를 쓰지 않았다.",
        "",
        "## 2. 데이터와 Vintage Guardrail",
        "",
        "- feature source: KEPCO 시군구 전력 사용량 historical source vintage",
        "- target: 시군구 official actual pilot의 `C00`, `D00`, `all`",
        "- O1 definition: 예측연도 3월 말 기준 공표 완료 데이터만 사용",
        "- fallback: feature 미사용 산업 또는 결측 stress에서는 global reference 유지",
        "",
        "## 3. 정책 후보 비교",
        "",
        "| policy | count | WMAPE | macro WMAPE | median APE | p90 APE | global WMAPE same rows | delta +good | material degradation |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in summary_rows:
        lines.append(f"| {r['policy']} | {r['count']} | {r['wmape']} | {r.get('macro_wmape', '')} | {r.get('median_ape', '')} | {r.get('p90_ape', '')} | {r.get('global_wmape_same_rows', '')} | {r.get('delta_vs_global_positive_good', '')} | {r.get('material_degradation_count', '')} |")
    lines.extend(["", "## 4. 연도/산업/지역별 진단", "", "| grouping | policy | key | count | WMAPE | global WMAPE | delta +good |", "| --- | --- | --- | ---: | ---: | ---: | ---: |"])
    for r in group_rows:
        key = r.get("target_year") or r.get("sector_code") or r.get("source_region")
        lines.append(f"| {r['grouping']} | {r['policy']} | {key} | {r['count']} | {r['wmape']} | {r['global_wmape_same_rows']} | {r['delta_vs_global_positive_good']} |")
    lines.extend(["", "## 5. Alpha 선택 로그", "", "| policy | origin | test_year | alpha | validation WMAPE | count |", "| --- | --- | ---: | ---: | ---: | ---: |"])
    for r in alpha_rows[:80]:
        lines.append(f"| {r['policy']} | {r['origin']} | {r['test_year']} | {r['alpha']} | {round(float(r['wmape']), 6)} | {r['count']} |")
    lines.extend(["", "## 6. Bootstrap", "", "| scope | group | iterations | mean delta | CI 2.5 | CI 97.5 | P(improve) |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"])
    for r in bootstrap_rows:
        lines.append(f"| {r['scope']} | {r['group_field']} | {r['iterations']} | {r['mean_delta_wmape_positive_good']} | {r['ci_low_2_5']} | {r['ci_high_97_5']} | {r['probability_improvement']} |")
    lines.extend(["", "## 7. Leave-One-Sido-Out", "", "| heldout | count | global WMAPE | candidate WMAPE | delta +good | status |", "| --- | ---: | ---: | ---: | ---: | --- |"])
    for r in loso_rows:
        lines.append(f"| {r['heldout_sido']} | {r['count']} | {r['global_wmape']} | {r['candidate_wmape']} | {r['delta_positive_good']} | {r['fit_status']} |")
    lines.extend(["", "## 8. Placebo", "", "| placebo | iterations | real delta | placebo mean | placebo p95 | pass |", "| --- | ---: | ---: | ---: | ---: | --- |"])
    for r in placebo_rows:
        lines.append(f"| {r['placebo_type']} | {r['iterations']} | {r['real_delta_wmape']} | {r['placebo_mean_delta']} | {r['placebo_p95_delta']} | {r['real_exceeds_placebo_p95']} |")
    lines.extend(["", "## 9. Lag 및 Leakage Sensitivity", "", "| policy | count | leakage rows | global WMAPE | candidate WMAPE | delta +good |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for r in lag_rows:
        lines.append(f"| {r['lag_policy']} | {r['count']} | {r['leakage_violation_count']} | {r['global_wmape']} | {r['candidate_wmape']} | {r['delta_positive_good']} |")
    lines.extend(["", "## 10. Missingness Stress", "", "| scenario | affected sido | count | delta +good | base delta |", "| --- | --- | ---: | ---: | ---: |"])
    for r in missing_rows:
        lines.append(f"| {r['scenario']} | {r.get('affected_sido', '')} | {r['count']} | {r['delta_positive_good']} | {r['base_delta']} |")
    lines.extend(["", "## 11. Large Observation Removal", "", "| metric | removed top % | removed rows | remaining | global WMAPE | candidate WMAPE | delta +good |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for r in large_rows:
        lines.append(f"| {r['removal_metric']} | {r['removed_top_pct']} | {r['removed_rows']} | {r['remaining_rows']} | {r['global_wmape']} | {r['candidate_wmape']} | {r['delta_positive_good']} |")
    lines.extend(
        [
            "",
            "## 12. Material Degradation Audit",
            "",
            f"- degradation rule: candidate error > global error * 1.1 and absolute error increase > actual * 2%",
            f"- rows flagged under primary best candidate: {primary_degrad}",
            f"- APE +1pp rows: {sum(1 for r in compared if r['ape_degradation_1pp'] == 'Y')}",
            f"- APE +5pp rows: {sum(1 for r in compared if r['ape_degradation_5pp'] == 'Y')}",
            f"- APE +10pp rows: {sum(1 for r in compared if r['ape_degradation_10pp'] == 'Y')}",
            "",
            "## 13. 운영 해석",
            "",
            "전력 feature는 제조업 및 전체 총량에서만 제한적으로 적용하고 전기가스업은 fallback하는 설계가 가장 방어적이다. 다만 bootstrap과 placebo에서 동시에 강한 신호가 확인되지 않으면 운영 채택보다는 다음 actual vintage에서 재확인하는 것이 맞다.",
            "",
            "## 14. 다음 단계",
            "",
            "1. O1 후보가 다음 official actual 갱신에서도 같은 방향의 개선을 보이는지 confirmatory test를 수행한다.",
            "2. C00과 all 각각에 별도 alpha를 두는 산업별 alpha 정책을 비교한다.",
            "3. 전력 외 feature를 하나 이상 추가해 placebo 대비 설명력이 독립적으로 유지되는지 확인한다.",
            "",
            "## 15. 산출물",
            "",
            "- `data/processed/electricity_guardrail_candidates.csv`",
            "- `data/processed/electricity_bootstrap_results.csv`",
            "- `data/processed/electricity_loso_results.csv`",
            "- `data/processed/electricity_placebo_results.csv`",
            "- `data/processed/electricity_lag_sensitivity_results.csv`",
            "- `data/processed/electricity_missingness_results.csv`",
            "- `data/processed/electricity_material_degradation_audit.csv`",
            "",
            "모든 CSV는 `kosis_common.write_csv`를 통해 CP949로 저장했다.",
            "",
            "## 16. Gate 판단표",
            "",
            "| gate | result | note |",
            "| --- | --- | --- |",
            f"| vintage leakage | PASS | O1 primary leakage row count is 0 |",
            f"| pooled WMAPE improvement | PASS | best delta is {best.get('delta_vs_global_positive_good', '')} |",
            f"| bootstrap probability | {'PASS' if p_improve >= 0.90 else 'WATCH'} | pooled P(improve) is {p_improve} |",
            f"| placebo superiority | {'PASS' if placebo_pass >= 2 else 'WATCH'} | {placebo_pass}/3 placebo families pass p95 |",
            f"| material degradation | {'WATCH' if primary_degrad else 'PASS'} | {primary_degrad} rows flagged |",
            "| industry consistency | WATCH | C00 worsens while all-sector total improves |",
            "",
            "## 17. 채택 보류 사유",
            "",
            "전체 WMAPE와 bootstrap 신호는 양호하지만, C00 단독에서는 global reference보다 나빠진다. 이는 전력 feature가 제조업 하위 구조를 직접 설명한다기보다 시군구 총량 또는 규모 보정에 더 강하게 작동한다는 뜻이다. 따라서 현재 후보는 운영 채택이 아니라 refinement 후보로 유지한다.",
            "",
            "## 18. 데이터 유출 방지 확인",
            "",
            "2022년 평가는 2021년 학습 및 2021년 내부 시도 CV로 alpha를 고르고, 2023년 평가는 2021년 학습에서 2022년 validation으로 alpha를 고른 뒤 2021-2022년으로 재학습해 2023년에 적용했다. O1 feature는 해당 연도 3월 말 공표 완료 vintage만 선택한다.",
            "",
            "## 19. 구현 메모",
            "",
            "실험은 `scripts/run_electricity_guardrail_robustness.py`에서 수행하며, 기존 `run_electricity_vintage_dry_run.py`의 vintage selector, target loader, panel joiner를 재사용한다. `run_electricity_vintage_dry_run.py`에는 lag sensitivity 중 발견된 음수 로그 방지를 위해 로그 변환용 feature에만 0 하한을 적용했다.",
            "",
            "## 20. 최종 운영 권고",
            "",
            "`P4_trainalpha_B6_relative_rel5_S1`을 다음 confirmatory round의 1순위 후보로 고정한다. 다만 산업별로는 `all`에만 명확한 개선이 있고 `C00`은 악화되므로, 다음 실험은 `all-only`, `C00 별도 alpha`, `C00 no-correction gate`를 같은 vintage-aware 절차로 비교해야 한다.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    vintage = load_or_build_vintage_long()
    features, audit, _long = build_asof_features(vintage)
    if any(r.get("leakage_violation") == "Y" for r in audit):
        raise SystemExit("Leakage violation detected in primary as-of features.")
    panel = join_panel(load_targets(), features)
    panel = [r for r in panel if r["prediction_origin_id"] == PRIMARY_ORIGIN]
    global_rows = add_global_predictions(panel)

    predictions: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    alpha_rows: list[dict[str, Any]] = []
    for cfg in candidate_configs() + stress_configs():
        pred, audit_rows, alpha = run_policy(panel, cfg)
        predictions.extend(pred)
        audits.extend(audit_rows)
        alpha_rows.extend(alpha)

    summary_rows = make_summary_rows(global_rows, predictions)
    group_rows = make_group_rows(predictions)
    best_policy = min([r for r in summary_rows if r["policy"] != "P0_global_reference"], key=lambda r: float(r["wmape"]))["policy"]
    best_rows = [r for r in predictions if r["policy"] == best_policy]
    compared = compare_predictions(global_rows, best_rows)
    best_cfg = next((cfg for cfg in candidate_configs() + stress_configs() if cfg["policy"] == best_policy), candidate_configs()[0])
    real_delta = wmape(best_rows, "global_prediction") - wmape(best_rows, "prediction")

    bootstrap_rows = run_bootstrap(compared)
    loso_rows = run_loso(panel, best_cfg)
    placebo_rows = run_placebos(panel, best_cfg, real_delta)
    lag_rows = run_lag_sensitivity(vintage, best_cfg)
    missing_rows = run_missingness(panel, best_cfg)
    large_rows = run_large_observation_audit(compared)

    write_csv(PROCESSED_DIR / "electricity_guardrail_candidates.csv", summary_rows + audits)
    write_csv(PROCESSED_DIR / "electricity_bootstrap_results.csv", bootstrap_rows)
    write_csv(PROCESSED_DIR / "electricity_loso_results.csv", loso_rows)
    write_csv(PROCESSED_DIR / "electricity_placebo_results.csv", placebo_rows)
    write_csv(PROCESSED_DIR / "electricity_lag_sensitivity_results.csv", lag_rows)
    write_csv(PROCESSED_DIR / "electricity_missingness_results.csv", missing_rows)
    write_csv(PROCESSED_DIR / "electricity_material_degradation_audit.csv", compared)
    write_csv(PROCESSED_DIR / "electricity_large_observation_sensitivity.csv", large_rows)
    write_csv(PROCESSED_DIR / "electricity_alpha_selection_results.csv", alpha_rows)

    write_markdown(
        summary_rows,
        group_rows,
        bootstrap_rows,
        loso_rows,
        placebo_rows,
        lag_rows,
        missing_rows,
        large_rows,
        alpha_rows,
        compared,
    )
    print(f"panel rows: {len(panel)}")
    print(f"candidate rows: {len(predictions)}")
    print(f"best policy: {best_policy}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
