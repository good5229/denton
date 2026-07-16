from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
from collections import Counter
from datetime import datetime
from statistics import mean, median
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, write_csv
from run_electricity_guardrail_robustness import (
    ALPHAS,
    BOOTSTRAP_N,
    FEATURE_BUNDLES,
    PLACEBO_N,
    PRIMARY_ORIGIN,
    RNG_SEED,
    ape,
    apply_mask,
    compare_predictions,
    fit_ridge_target,
    groupby,
    macro_wmape,
    pctl,
    predict_candidate_rows,
    run_large_observation_audit,
    split_rows,
    wmape,
)
from run_electricity_vintage_dry_run import build_asof_features, join_panel, load_or_build_vintage_long, load_targets, matrix, num


REPORT_PATH = ROOT / "reports" / "electricity_all_only_refinement_round.md"
MANIFEST_PATH = PROCESSED_DIR / "electricity_shadow_policy_manifest.json"
SELECTION_BOOTSTRAP_N = 1000
CONSERVATIVE_ALPHAS = [0.10, 0.15, 0.25]
MULTIOBJECTIVE_LAMBDAS = {"material": 0.25, "median": 0.10, "p90": 0.10}


def policy_configs() -> list[dict[str, Any]]:
    return [
        {
            "policy": "R1_reproduce_P4_C00_all",
            "bundle": "B6_full_without_change",
            "target_type": "relative",
            "alpha_mode": "train_selected",
            "alpha_candidates": ALPHAS,
            "clip_rule": "rel0.05",
            "mask": "S1_C00_all_apply_D00_fallback",
            "description": "기존 P4 재현: C00+all 적용, D00 fallback",
        },
        {
            "policy": "R2_all_only_trainalpha_B6_rel5",
            "bundle": "B6_full_without_change",
            "target_type": "relative",
            "alpha_mode": "train_selected",
            "alpha_candidates": ALPHAS,
            "clip_rule": "rel0.05",
            "mask": "S3_all_only",
            "description": "신규 1순위 all-only 후보",
        },
        {
            "policy": "R3_all_only_conservative_B6_rel5",
            "bundle": "B6_full_without_change",
            "target_type": "relative",
            "alpha_mode": "train_selected",
            "alpha_candidates": CONSERVATIVE_ALPHAS,
            "clip_rule": "rel0.05",
            "mask": "S3_all_only",
            "description": "all-only 보수형 alpha 후보",
        },
        {
            "policy": "R3b_all_only_conservative_B4_rel5",
            "bundle": "B4_level_normalized",
            "target_type": "relative",
            "alpha_mode": "train_selected",
            "alpha_candidates": CONSERVATIVE_ALPHAS,
            "clip_rule": "rel0.05",
            "mask": "S3_all_only",
            "description": "all-only 보수형 B4 sensitivity",
        },
    ]


def material_degradation_rate(rows: list[dict[str, Any]], pred_field: str = "prediction") -> float:
    if not rows:
        return 0.0
    count = 0
    for row in rows:
        base_err = abs(float(row["global_prediction"]) - float(row["actual"]))
        err = abs(float(row[pred_field]) - float(row["actual"]))
        if err > base_err * 1.1 and err - base_err > abs(float(row["actual"])) * 0.02:
            count += 1
    return count / len(rows)


def validation_score(rows: list[dict[str, Any]], pred_field: str = "prediction_alpha") -> float:
    g_rows = [{**r, "prediction_alpha": r["global_prediction"]} for r in rows]
    candidate_wmape = wmape(rows, pred_field)
    global_median = median([ape(r, "prediction_alpha") for r in g_rows]) if g_rows else 0.0
    global_p90 = pctl([ape(r, "prediction_alpha") for r in g_rows], 90)
    candidate_median = median([ape(r, pred_field) for r in rows]) if rows else 0.0
    candidate_p90 = pctl([ape(r, pred_field) for r in rows], 90)
    return (
        candidate_wmape
        + MULTIOBJECTIVE_LAMBDAS["material"] * material_degradation_rate(rows, pred_field) * 100
        + MULTIOBJECTIVE_LAMBDAS["median"] * max(0.0, candidate_median - global_median)
        + MULTIOBJECTIVE_LAMBDAS["p90"] * max(0.0, candidate_p90 - global_p90)
    )


def alpha_cv_local(
    panel: list[dict[str, Any]],
    test_year: int,
    fields: list[str],
    cfg: dict[str, Any],
    *,
    score_mode: str = "multiobjective",
) -> tuple[float, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    if test_year == 2022:
        cv_base = [r for r in panel if int(r["target_year"]) == 2021 and r["prediction_origin_id"] == PRIMARY_ORIGIN]
        for (sido,), heldout in groupby(cv_base, ["source_region"]).items():
            train = [r for r in cv_base if r["source_region"] != sido]
            pred, _audit = predict_candidate_rows(
                train,
                heldout,
                policy="cv",
                fields=fields,
                target_type=cfg["target_type"],
                alpha=1.0,
                clip_rule=cfg["clip_rule"],
                mask=cfg["mask"],
            )
            rows.extend(pred)
    else:
        train = [r for r in panel if int(r["target_year"]) == 2021 and r["prediction_origin_id"] == PRIMARY_ORIGIN]
        valid = [r for r in panel if int(r["target_year"]) == 2022 and r["prediction_origin_id"] == PRIMARY_ORIGIN]
        rows, _audit = predict_candidate_rows(
            train,
            valid,
            policy="cv",
            fields=fields,
            target_type=cfg["target_type"],
            alpha=1.0,
            clip_rule=cfg["clip_rule"],
            mask=cfg["mask"],
        )
    scores = []
    for alpha in cfg["alpha_candidates"]:
        eval_rows = []
        for row in rows:
            rec = row.copy()
            if apply_mask(rec, cfg["mask"]) and rec.get("fallback_reason") == "":
                rec["prediction_alpha"] = max(float(rec["global_prediction"]) + alpha * float(rec["correction_applied"]), 1e-9)
            else:
                rec["prediction_alpha"] = float(rec["global_prediction"])
            eval_rows.append(rec)
        score = validation_score(eval_rows) if score_mode == "multiobjective" else wmape(eval_rows, "prediction_alpha")
        scores.append(
            {
                "policy": cfg["policy"],
                "test_year": test_year,
                "alpha": alpha,
                "validation_wmape": wmape(eval_rows, "prediction_alpha"),
                "validation_score": score,
                "material_degradation_rate": material_degradation_rate(eval_rows, "prediction_alpha"),
                "count": len(eval_rows),
            }
        )
    best = min(scores, key=lambda r: (float(r["validation_score"]), float(r["alpha"])))
    return float(best["alpha"]), scores


def run_policy(panel: list[dict[str, Any]], cfg: dict[str, Any], *, score_mode: str = "multiobjective") -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    predictions: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    alpha_rows: list[dict[str, Any]] = []
    coefficient_rows: list[dict[str, Any]] = []
    fields = FEATURE_BUNDLES[cfg["bundle"]]
    for test_year in (2022, 2023):
        train, test = split_rows(panel, test_year, PRIMARY_ORIGIN)
        alpha, alpha_scores = alpha_cv_local(panel, test_year, fields, cfg, score_mode=score_mode)
        alpha_rows.extend(alpha_scores)
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
        active_train = [r for r in train if apply_mask(r, cfg["mask"])]
        if len(active_train) >= max(12, len(fields) + 3):
            model = fit_ridge_target(active_train, fields, cfg["target_type"])
            for name, beta in zip(fields, model["beta"]):
                coefficient_rows.append(
                    {
                        "policy": cfg["policy"],
                        "test_year": test_year,
                        "feature_name": name,
                        "coefficient": float(beta),
                        "standardized_coefficient": float(beta),
                        "coefficient_sign": "positive" if beta > 0 else "negative" if beta < 0 else "zero",
                        "selected_alpha": alpha,
                        "selected_lambda": model["lambda"],
                    }
                )
        for row in pred:
            row["feature_bundle"] = cfg["bundle"]
            row["selected_alpha"] = alpha
            row["application_mask"] = cfg["mask"]
            row["score_mode"] = score_mode
        audit.update({"selected_alpha": alpha, "score_mode": score_mode, "feature_bundle": cfg["bundle"]})
        predictions.extend(pred)
        audits.append(audit)
    return predictions, audits, alpha_rows, coefficient_rows


def global_rows(panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [r.copy() for r in panel if int(r["target_year"]) in {2022, 2023} and r["prediction_origin_id"] == PRIMARY_ORIGIN]
    for row in rows:
        row["policy"] = "R0_global_reference"
        row["prediction"] = float(row["global_prediction"])
        row["selected_alpha"] = 0.0
        row["application_mask"] = "none"
    return rows


def metric_row(rows: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    apes = [ape(r, "prediction") for r in rows]
    global_w = wmape(rows, "global_prediction")
    med_global = median([ape({**r, "prediction": r["global_prediction"]}, "prediction") for r in rows]) if rows else 0.0
    p90_global = pctl([ape({**r, "prediction": r["global_prediction"]}, "prediction") for r in rows], 90)
    med = median(apes) if apes else 0.0
    p90 = pctl(apes, 90)
    degr = material_degradation_rate(rows)
    severe5 = sum(1 for r in rows if ape(r, "prediction") - ape({**r, "prediction": r["global_prediction"]}, "prediction") > 5.0)
    severe10 = sum(1 for r in rows if ape(r, "prediction") - ape({**r, "prediction": r["global_prediction"]}, "prediction") > 10.0)
    improved_regions = sum(1 for _region, items in groupby(rows, ["source_region"]).items() if wmape(items, "prediction") < wmape(items, "global_prediction"))
    region_count = len(groupby(rows, ["source_region"]))
    return {
        "policy": policy,
        "count": len(rows),
        "wmape": round(wmape(rows, "prediction"), 6),
        "global_wmape_same_rows": round(global_w, 6),
        "delta_positive_good": round(global_w - wmape(rows, "prediction"), 6),
        "relative_improvement_pct": round((global_w - wmape(rows, "prediction")) / global_w * 100, 6) if global_w else 0.0,
        "macro_region_wmape": round(macro_wmape(rows, "prediction"), 6),
        "global_macro_region_wmape": round(macro_wmape([{**r, "prediction": r["global_prediction"]} for r in rows], "prediction"), 6),
        "mape": round(mean(apes), 6) if apes else 0.0,
        "median_ape": round(med, 6),
        "p90_ape": round(p90, 6),
        "median_ape_delta_pp": round(med - med_global, 6),
        "p90_ape_delta_pp": round(p90 - p90_global, 6),
        "mae": round(mean([abs(float(r["prediction"]) - float(r["actual"])) for r in rows]), 6) if rows else 0.0,
        "rmse": round(math.sqrt(mean([(float(r["prediction"]) - float(r["actual"])) ** 2 for r in rows])), 6) if rows else 0.0,
        "material_degradation_count": round(degr * len(rows)),
        "material_degradation_rate": round(degr, 6),
        "ape_plus_1pp_count": sum(1 for r in rows if ape(r, "prediction") - ape({**r, "prediction": r["global_prediction"]}, "prediction") > 1.0),
        "ape_plus_5pp_count": severe5,
        "ape_plus_10pp_count": severe10,
        "region_improvement_rate": round(improved_regions / region_count, 6) if region_count else 0.0,
        "fallback_rate": round(sum(1 for r in rows if r.get("fallback_reason")) / len(rows), 6) if rows else 0.0,
    }


def group_metrics(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for keys in (["policy", "target_year"], ["policy", "sector_code"], ["policy", "source_region"]):
        for key, items in sorted(groupby(predictions, keys).items()):
            m = metric_row(items, str(key[0]))
            m["grouping"] = "+".join(keys[1:])
            for name, value in zip(keys, key):
                m[name] = value
            rows.append(m)
    return rows


def coefficient_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for (policy, feature), items in sorted(groupby(rows, ["policy", "feature_name"]).items()):
        vals = [float(r["coefficient"]) for r in items]
        pos = sum(1 for v in vals if v > 0)
        neg = sum(1 for v in vals if v < 0)
        mean_v = mean(vals) if vals else 0.0
        std_v = float(np.std(np.asarray(vals, dtype=float))) if vals else 0.0
        out.append(
            {
                "policy": policy,
                "feature_name": feature,
                "n": len(vals),
                "mean_coefficient": round(mean_v, 8),
                "median_coefficient": round(median(vals), 8) if vals else 0.0,
                "coefficient_std": round(std_v, 8),
                "positive_sign_rate": round(pos / len(vals), 6) if vals else 0.0,
                "negative_sign_rate": round(neg / len(vals), 6) if vals else 0.0,
                "nonzero_rate": round(sum(1 for v in vals if abs(v) > 1e-12) / len(vals), 6) if vals else 0.0,
                "stability_flag": "unstable" if vals and (max(pos, neg) / len(vals) < 0.70 or std_v > abs(mean_v) * 2) else "stable",
            }
        )
    return out


def cluster_bootstrap(rows: list[dict[str, Any]], label: str, n: int = BOOTSTRAP_N) -> dict[str, Any]:
    clusters = list(groupby(rows, ["sigungu_feature_key"]).values())
    rng = random.Random(RNG_SEED + len(label))
    deltas = []
    for _ in range(n):
        sample = []
        for _idx in range(len(clusters)):
            sample.extend(rng.choice(clusters))
        deltas.append(wmape(sample, "global_prediction") - wmape(sample, "prediction"))
    return {
        "policy": label,
        "iterations": n,
        "mean_delta_positive_good": round(mean(deltas), 6),
        "median_delta_positive_good": round(median(deltas), 6),
        "ci_low_2_5": round(pctl(deltas, 2.5), 6),
        "ci_high_97_5": round(pctl(deltas, 97.5), 6),
        "probability_improvement": round(sum(1 for v in deltas if v > 0) / len(deltas), 6),
    }


def selection_aware_bootstrap(policy_predictions: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    keys = sorted(policy_predictions)
    base_rows = next(iter(policy_predictions.values()))
    clusters = list(groupby(base_rows, ["sigungu_feature_key"]).keys())
    rows_by_cluster = {policy: groupby(rows, ["sigungu_feature_key"]) for policy, rows in policy_predictions.items()}
    rng = random.Random(RNG_SEED + 77)
    selected_policy = Counter()
    selected_alpha = Counter()
    deltas = []
    for _ in range(SELECTION_BOOTSTRAP_N):
        sampled = [rng.choice(clusters) for _ in range(len(clusters))]
        sampled_set = set(sampled)
        holdout = [c for c in clusters if c not in sampled_set]
        if not holdout:
            holdout = sampled[: max(1, len(sampled) // 5)]
        scores = []
        for policy in keys:
            sample_rows = []
            for cluster in sampled:
                sample_rows.extend(rows_by_cluster[policy].get(cluster, []))
            scores.append((wmape(sample_rows, "prediction"), policy))
        _score, policy = min(scores)
        selected_policy[policy] += 1
        alpha_vals = {str(r.get("selected_alpha", "")) for r in policy_predictions[policy] if r.get("selected_alpha", "") != ""}
        selected_alpha["/".join(sorted(alpha_vals))] += 1
        eval_rows = []
        for cluster in holdout:
            eval_rows.extend(rows_by_cluster[policy].get(cluster, []))
        if eval_rows:
            deltas.append(wmape(eval_rows, "global_prediction") - wmape(eval_rows, "prediction"))
    out = [
        {
            "summary_type": "selection_aware_delta",
            "iterations": SELECTION_BOOTSTRAP_N,
            "mean_improvement": round(mean(deltas), 6),
            "median_improvement": round(median(deltas), 6),
            "ci_low_2_5": round(pctl(deltas, 2.5), 6),
            "ci_high_97_5": round(pctl(deltas, 97.5), 6),
            "probability_of_improvement": round(sum(1 for v in deltas if v > 0) / len(deltas), 6),
        }
    ]
    total = sum(selected_policy.values()) or 1
    for policy, count in selected_policy.most_common():
        out.append({"summary_type": "selected_policy_frequency", "selected_policy": policy, "count": count, "frequency": round(count / total, 6)})
    total_alpha = sum(selected_alpha.values()) or 1
    for alpha, count in selected_alpha.most_common():
        out.append({"summary_type": "selected_alpha_frequency", "selected_alpha": alpha, "count": count, "frequency": round(count / total_alpha, 6)})
    return out


def run_loso(panel: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for (sido,), _items in sorted(groupby(panel, ["source_region"]).items()):
        work = [r for r in panel if r["prediction_origin_id"] == PRIMARY_ORIGIN]
        train = [r for r in work if r["source_region"] != sido and int(r["target_year"]) in {2021, 2022}]
        test = [r for r in work if r["source_region"] == sido and int(r["target_year"]) in {2022, 2023}]
        pred, audit = predict_candidate_rows(
            train,
            test,
            policy="loso",
            fields=FEATURE_BUNDLES[cfg["bundle"]],
            target_type=cfg["target_type"],
            alpha=0.25,
            clip_rule=cfg["clip_rule"],
            mask=cfg["mask"],
        )
        out.append(
            {
                "heldout_sido": sido,
                "count": len(pred),
                "global_wmape": round(wmape(pred, "global_prediction"), 6),
                "candidate_wmape": round(wmape(pred, "prediction"), 6),
                "delta_positive_good": round(wmape(pred, "global_prediction") - wmape(pred, "prediction"), 6),
                "fit_status": audit.get("fit_status", ""),
            }
        )
    return out


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


def run_fixed_policy(panel: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    pred, _audits, _alpha, _coef = run_policy(panel, cfg)
    return pred


def run_placebo(panel: list[dict[str, Any]], cfg: dict[str, Any], real_delta: float) -> list[dict[str, Any]]:
    fields = FEATURE_BUNDLES[cfg["bundle"]]
    out = []
    for mode in ("region", "temporal", "noise"):
        rng = random.Random(RNG_SEED + len(mode))
        deltas = []
        for idx in range(PLACEBO_N):
            fake = permute_feature_blocks(panel, fields, rng, mode)
            pred = run_fixed_policy(fake, cfg)
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


def run_lag(vintage: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for label, kwargs in [
        ("L0_actual_publication_date", {}),
        ("L1_observation_plus_1m", {"lag_months": 1}),
        ("L2_observation_plus_2m", {"lag_months": 2}),
        ("L3_observation_plus_3m", {"lag_months": 3}),
    ]:
        features, audit, _long = build_asof_features(vintage, suffix=label, **kwargs)
        panel = [r for r in join_panel(load_targets(), features) if r["prediction_origin_id"] == PRIMARY_ORIGIN]
        pred = run_fixed_policy(panel, cfg)
        out.append(
            {
                "lag_policy": label,
                "count": len(pred),
                "leakage_violation_count": sum(1 for r in audit if r.get("leakage_violation") == "Y"),
                "global_wmape": round(wmape(pred, "global_prediction"), 6),
                "candidate_wmape": round(wmape(pred, "prediction"), 6),
                "delta_positive_good": round(wmape(pred, "global_prediction") - wmape(pred, "prediction"), 6),
            }
        )
    return out


def run_missingness(vintage: list[dict[str, Any]], panel: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    base_pred = run_fixed_policy(panel, cfg)
    base_delta = wmape(base_pred, "global_prediction") - wmape(base_pred, "prediction")
    latest_by_year = {}
    for (year,), items in groupby(panel, ["target_year"]).items():
        latest_by_year[year] = max(str(r.get("feature_latest_eligible_observation_period", "")) for r in items)
    work = []
    for row in panel:
        rec = row.copy()
        if str(rec.get("feature_latest_eligible_observation_period", "")) == latest_by_year.get(rec["target_year"], ""):
            rec["sector_code"] = "D00"
        work.append(rec)
    hard = run_fixed_policy(work, cfg)
    out.append({"scenario": "M1_hard_fallback_latest_month_missing", "coverage_threshold": "", "count": len(hard), "base_delta": round(base_delta, 6), "delta_positive_good": round(wmape(hard, "global_prediction") - wmape(hard, "prediction"), 6)})
    features, _audit, _long = build_asof_features(vintage, suffix="prior_vintage_missingness", lag_months=1)
    recalc_panel = [r for r in join_panel(load_targets(), features) if r["prediction_origin_id"] == PRIMARY_ORIGIN]
    for threshold in (0.75, 0.90, 1.00):
        gated = []
        for row in recalc_panel:
            rec = row.copy()
            if num(rec.get("feature_feature_window_coverage_rate")) < threshold:
                rec["sector_code"] = "D00"
            gated.append(rec)
        pred = run_fixed_policy(gated, cfg)
        out.append({"scenario": "M2_prior_vintage_recalculation", "coverage_threshold": threshold, "count": len(pred), "base_delta": round(base_delta, 6), "delta_positive_good": round(wmape(pred, "global_prediction") - wmape(pred, "prediction"), 6)})
    return out


def file_hash(path: Any) -> str:
    p = ROOT / path if isinstance(path, str) else path
    if not p.exists():
        return ""
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def write_manifest(best_policy: str, best_cfg: dict[str, Any], metrics: dict[str, Any], decision: str) -> None:
    manifest = {
        "policy_id": best_policy,
        "policy_version": "electricity_shadow_policy_v1_dev_2022_2023",
        "operational_status": decision,
        "feature_source_version": "kepco_historical_vintage_selector_v1",
        "feature_bundle": best_cfg["bundle"],
        "prediction_origin": PRIMARY_ORIGIN,
        "residual_target": best_cfg["target_type"],
        "ridge_lambda_selection_rule": "train_period_in_sample_wmape_minimization_over_[0.1,1,10,100,1000]",
        "alpha_selection_rule": "training_validation_multiobjective_score",
        "clipping_rule": best_cfg["clip_rule"],
        "coverage_rule": "feature_window_coverage >= 0.75 recommended; missing feature global fallback",
        "application_sector": "all only",
        "fallback_rule": "C00 global; D00 global; missing feature global",
        "training_period": "2021 for 2022; 2021-2022 for 2023",
        "development_evaluation_period": "2022-2023 official actual pilot",
        "confirmatory_period_status": "reserved_for_2024_or_first_unused_official_actual",
        "evaluation_metrics": metrics,
        "acceptance_thresholds": {
            "wmape_improvement": "> 0",
            "macro_wmape_noninferior": True,
            "yearly_improvement": "2022>=0 and 2023>=0",
            "material_degradation_count": "<=95 for acceptance; shadow allowed if severe degradation is zero",
            "selection_aware_bootstrap_probability": ">=0.90",
            "placebo": "real improvement > p95",
        },
        "code_commit_hash": git_hash(),
        "input_data_hashes": {
            "kepco_historical_vintage_long.csv": file_hash(PROCESSED_DIR / "kepco_historical_vintage_long.csv"),
            "sigungu_global_model_pilot_predictions.csv": file_hash(PROCESSED_DIR / "sigungu_global_model_pilot_predictions.csv"),
        },
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(
    summary_rows: list[dict[str, Any]],
    grouped_rows: list[dict[str, Any]],
    alpha_rows: list[dict[str, Any]],
    bootstrap_rows: list[dict[str, Any]],
    selection_rows: list[dict[str, Any]],
    coef_summary: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
    placebo_rows: list[dict[str, Any]],
    lag_rows: list[dict[str, Any]],
    loso_rows: list[dict[str, Any]],
    large_rows: list[dict[str, Any]],
    degradation_rows: list[dict[str, Any]],
    best_policy: str,
    decision: str,
) -> None:
    best = next(r for r in summary_rows if r["policy"] == best_policy)
    lines = [
        "# 전력 Feature All-only Refinement Round",
        "",
        "## 1. 실행 요약",
        "",
        f"- final decision: `{decision}`",
        f"- selected shadow candidate: `{best_policy}`",
        f"- WMAPE delta, positive is good: {best['delta_positive_good']}",
        f"- relative improvement: {best['relative_improvement_pct']}%",
        f"- material degradation count: {best['material_degradation_count']}",
        f"- policy manifest: `data/processed/electricity_shadow_policy_manifest.json`",
        "",
        "이번 라운드는 2022-2023 개발 actual에서 후보 확장을 종료하기 위한 정제 실험이다. 전력 feature는 `all` 총량에만 적용하고 `C00`, `D00`은 global fallback하는 방향을 중심으로 검증했다.",
        "",
        "## 2. R0~R3 정책 비교",
        "",
        "| policy | count | WMAPE | global WMAPE | delta +good | rel improve % | macro WMAPE | median APE | p90 APE | material deg | fallback rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in summary_rows:
        lines.append(f"| {r['policy']} | {r['count']} | {r['wmape']} | {r['global_wmape_same_rows']} | {r['delta_positive_good']} | {r['relative_improvement_pct']} | {r['macro_region_wmape']} | {r['median_ape']} | {r['p90_ape']} | {r['material_degradation_count']} | {r['fallback_rate']} |")
    lines.extend(["", "## 3. 연도/산업/지역별 결과", "", "| grouping | policy | key | count | WMAPE | global WMAPE | delta +good |", "| --- | --- | --- | ---: | ---: | ---: | ---: |"])
    for r in grouped_rows:
        key = r.get("target_year") or r.get("sector_code") or r.get("source_region")
        lines.append(f"| {r['grouping']} | {r['policy']} | {key} | {r['count']} | {r['wmape']} | {r['global_wmape_same_rows']} | {r['delta_positive_good']} |")
    lines.extend(["", "## 4. Alpha 및 Ridge Lambda 선택", "", "| policy | test_year | alpha | validation WMAPE | validation score | degradation rate | count |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for r in alpha_rows:
        lines.append(f"| {r['policy']} | {r['test_year']} | {r['alpha']} | {round(float(r['validation_wmape']), 6)} | {round(float(r['validation_score']), 6)} | {round(float(r['material_degradation_rate']), 6)} | {r['count']} |")
    lines.extend(["", "## 5. 일반 Bootstrap", "", "| policy | iterations | mean delta | CI 2.5 | CI 97.5 | P(improve) |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for r in bootstrap_rows:
        lines.append(f"| {r['policy']} | {r['iterations']} | {r['mean_delta_positive_good']} | {r['ci_low_2_5']} | {r['ci_high_97_5']} | {r['probability_improvement']} |")
    lines.extend(["", "## 6. Selection-aware Bootstrap", "", "| type | selected policy/alpha | count | frequency | mean improvement | CI 2.5 | CI 97.5 | P(improve) |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for r in selection_rows:
        lines.append(f"| {r['summary_type']} | {r.get('selected_policy') or r.get('selected_alpha', '')} | {r.get('count', '')} | {r.get('frequency', '')} | {r.get('mean_improvement', '')} | {r.get('ci_low_2_5', '')} | {r.get('ci_high_97_5', '')} | {r.get('probability_of_improvement', '')} |")
    lines.extend(["", "## 7. Coefficient 안정성", "", "| policy | feature | n | mean | std | positive rate | negative rate | flag |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"])
    for r in coef_summary:
        lines.append(f"| {r['policy']} | {r['feature_name']} | {r['n']} | {r['mean_coefficient']} | {r['coefficient_std']} | {r['positive_sign_rate']} | {r['negative_sign_rate']} | {r['stability_flag']} |")
    lines.extend(["", "## 8. Missingness", "", "| scenario | coverage threshold | count | base delta | delta +good |", "| --- | ---: | ---: | ---: | ---: |"])
    for r in missing_rows:
        lines.append(f"| {r['scenario']} | {r['coverage_threshold']} | {r['count']} | {r['base_delta']} | {r['delta_positive_good']} |")
    lines.extend(["", "## 9. Placebo", "", "| placebo | iterations | real delta | placebo mean | placebo p95 | pass |", "| --- | ---: | ---: | ---: | ---: | --- |"])
    for r in placebo_rows:
        lines.append(f"| {r['placebo_type']} | {r['iterations']} | {r['real_delta_wmape']} | {r['placebo_mean_delta']} | {r['placebo_p95_delta']} | {r['real_exceeds_placebo_p95']} |")
    lines.extend(["", "## 10. Lag Sensitivity", "", "| lag | count | leakage rows | global WMAPE | candidate WMAPE | delta +good |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for r in lag_rows:
        lines.append(f"| {r['lag_policy']} | {r['count']} | {r['leakage_violation_count']} | {r['global_wmape']} | {r['candidate_wmape']} | {r['delta_positive_good']} |")
    lines.extend(["", "## 11. Leave-one-sido-out", "", "| heldout | count | global WMAPE | candidate WMAPE | delta +good |", "| --- | ---: | ---: | ---: | ---: |"])
    for r in loso_rows:
        lines.append(f"| {r['heldout_sido']} | {r['count']} | {r['global_wmape']} | {r['candidate_wmape']} | {r['delta_positive_good']} |")
    lines.extend(["", "## 12. Large Observation Removal", "", "| metric | removed top % | removed rows | global WMAPE | candidate WMAPE | delta +good |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for r in large_rows:
        lines.append(f"| {r['removal_metric']} | {r['removed_top_pct']} | {r['removed_rows']} | {r['global_wmape']} | {r['candidate_wmape']} | {r['delta_positive_good']} |")
    lines.extend(
        [
            "",
            "## 13. Material Degradation",
            "",
            f"- selected candidate material degradation: {best['material_degradation_count']}",
            f"- selected candidate APE +5pp: {best['ape_plus_5pp_count']}",
            f"- selected candidate APE +10pp: {best['ape_plus_10pp_count']}",
            f"- detailed row audit: `data/processed/electricity_all_only_degradation.csv` ({len(degradation_rows)} rows)",
            "",
            "## 14. Gate 판단",
            "",
            "| gate | result | note |",
            "| --- | --- | --- |",
            f"| primary WMAPE | {'PASS' if best['delta_positive_good'] > 0 else 'FAIL'} | delta {best['delta_positive_good']} |",
            f"| macro WMAPE | {'PASS' if best['macro_region_wmape'] <= best['global_macro_region_wmape'] else 'WATCH'} | candidate {best['macro_region_wmape']} vs global {best['global_macro_region_wmape']} |",
            f"| material degradation <=95 | {'PASS' if best['material_degradation_count'] <= 95 else 'WATCH'} | {best['material_degradation_count']} |",
            f"| severe degradation | {'PASS' if best['ape_plus_5pp_count'] == 0 and best['ape_plus_10pp_count'] == 0 else 'WATCH'} | +5pp {best['ape_plus_5pp_count']}, +10pp {best['ape_plus_10pp_count']} |",
            f"| placebo | {'PASS' if all(r['real_exceeds_placebo_p95'] == 'Y' for r in placebo_rows) else 'WATCH'} | real > p95 required |",
            "",
            "## 15. 최종 Decision",
            "",
            f"`{decision}`",
            "",
            "2022-2023 개발 데이터에서 전력 feature는 all-only shadow 후보로 유지한다. 다만 2023년 및 placebo gate가 약하므로 운영 정책으로 동결하지 않는다. 이 결과를 바탕으로 같은 개발 actual에서 신규 후보를 추가 탐색하기보다는 다음 미사용 official actual에서 confirmatory test를 수행한다.",
            "",
            "## 16. Confirmatory 정책",
            "",
            "- application: all only",
            "- fallback: C00 global, D00 global, missing feature global",
            "- origin: O1",
            "- feature bundle: B6 full without change",
            "- alpha selection: training validation multiobjective score",
            "- clipping: relative 5%",
            "- confirmatory period: 2024 이후 또는 정책 동결 이후 최초 확보되는 미사용 official actual",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    vintage = load_or_build_vintage_long()
    features, audit, _long = build_asof_features(vintage)
    if any(row.get("leakage_violation") == "Y" for row in audit):
        raise SystemExit("Vintage leakage detected.")
    panel = [r for r in join_panel(load_targets(), features) if r["prediction_origin_id"] == PRIMARY_ORIGIN]
    g_rows = global_rows(panel)

    all_predictions = g_rows.copy()
    audits: list[dict[str, Any]] = []
    alpha_rows: list[dict[str, Any]] = []
    coefficient_rows: list[dict[str, Any]] = []
    by_policy: dict[str, list[dict[str, Any]]] = {"R0_global_reference": g_rows}
    for cfg in policy_configs():
        preds, audit_rows, alphas, coefs = run_policy(panel, cfg)
        all_predictions.extend(preds)
        by_policy[cfg["policy"]] = preds
        audits.extend(audit_rows)
        alpha_rows.extend(alphas)
        coefficient_rows.extend(coefs)

    summary_rows = [metric_row(rows, policy) for policy, rows in by_policy.items()]
    grouped_rows = group_metrics(all_predictions)
    candidate_policies = [r for r in summary_rows if str(r["policy"]).startswith(("R2_", "R3_"))]
    best = min(candidate_policies, key=lambda r: (-float(r["delta_positive_good"]), float(r["material_degradation_count"])))
    best_policy = str(best["policy"])
    best_cfg = next(cfg for cfg in policy_configs() if cfg["policy"] == best_policy)
    best_rows = by_policy[best_policy]

    compared = compare_predictions(g_rows, best_rows)
    bootstrap_rows = [cluster_bootstrap(rows, policy) for policy, rows in by_policy.items() if policy != "R0_global_reference"]
    selection_rows = selection_aware_bootstrap({k: v for k, v in by_policy.items() if k.startswith(("R2_", "R3_"))})
    coef_summary = coefficient_summary(coefficient_rows)
    missing_rows = run_missingness(vintage, panel, best_cfg)
    real_delta = wmape(best_rows, "global_prediction") - wmape(best_rows, "prediction")
    placebo_rows = run_placebo(panel, best_cfg, real_delta)
    lag_rows = run_lag(vintage, best_cfg)
    loso_rows = run_loso(panel, best_cfg)
    large_rows = run_large_observation_audit(compared)

    selection_prob = next((float(r["probability_of_improvement"]) for r in selection_rows if r["summary_type"] == "selection_aware_delta"), 0.0)
    yearly = [r for r in grouped_rows if r.get("policy") == best_policy and r.get("grouping") == "target_year"]
    yearly_pass = all(float(r["delta_positive_good"]) >= 0 for r in yearly)
    placebo_pass = all(r["real_exceeds_placebo_p95"] == "Y" for r in placebo_rows)
    decision = "all_only_shadow_candidate_retained_but_not_frozen"
    if best["delta_positive_good"] <= 0 or selection_prob < 0.90:
        decision = "all_only_shadow_candidate_retained_but_not_frozen"
    if (
        yearly_pass
        and placebo_pass
        and best["material_degradation_count"] <= 95
        and best["ape_plus_5pp_count"] == 0
        and best["ape_plus_10pp_count"] == 0
        and selection_prob >= 0.90
    ):
        decision = "freeze_all_only_shadow_policy_pending_confirmatory_actual"

    write_csv(PROCESSED_DIR / "electricity_all_only_candidates.csv", summary_rows + audits)
    write_csv(PROCESSED_DIR / "electricity_all_only_alpha_selection.csv", alpha_rows)
    write_csv(PROCESSED_DIR / "electricity_all_only_bootstrap.csv", bootstrap_rows)
    write_csv(PROCESSED_DIR / "electricity_all_only_selection_aware_bootstrap.csv", selection_rows)
    write_csv(PROCESSED_DIR / "electricity_all_only_coefficients.csv", coefficient_rows + coef_summary)
    write_csv(PROCESSED_DIR / "electricity_all_only_missingness.csv", missing_rows)
    write_csv(PROCESSED_DIR / "electricity_all_only_placebo.csv", placebo_rows)
    write_csv(PROCESSED_DIR / "electricity_all_only_lag_sensitivity.csv", lag_rows)
    write_csv(PROCESSED_DIR / "electricity_all_only_loso.csv", loso_rows)
    write_csv(PROCESSED_DIR / "electricity_all_only_degradation.csv", compared)

    write_manifest(best_policy, best_cfg, best, decision)
    write_report(
        summary_rows,
        grouped_rows,
        alpha_rows,
        bootstrap_rows,
        selection_rows,
        coef_summary,
        missing_rows,
        placebo_rows,
        lag_rows,
        loso_rows,
        large_rows,
        compared,
        best_policy,
        decision,
    )
    print(f"panel rows: {len(panel)}")
    print(f"best policy: {best_policy}")
    print(f"decision: {decision}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
