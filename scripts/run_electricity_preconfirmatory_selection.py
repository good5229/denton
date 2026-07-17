from __future__ import annotations

import hashlib
import json
import random
import subprocess
from collections import Counter
from datetime import datetime
from statistics import mean, median
from typing import Any

from kosis_common import PROCESSED_DIR, ROOT, write_csv
from run_electricity_all_only_refinement import (
    CONSERVATIVE_ALPHAS,
    alpha_cv_local,
    global_rows,
    metric_row,
    run_loso,
    run_missingness,
    run_policy,
    validation_score,
)
from run_electricity_guardrail_robustness import (
    ALPHAS,
    FEATURE_BUNDLES,
    PRIMARY_ORIGIN,
    RNG_SEED,
    ape,
    apply_mask,
    groupby,
    pctl,
    predict_candidate_rows,
    run_large_observation_audit,
    split_rows,
    wmape,
)
from run_electricity_vintage_dry_run import build_asof_features, join_panel, load_or_build_vintage_long, load_targets


REPORT_PATH = ROOT / "reports" / "electricity_preconfirmatory_policy_selection.md"
MANIFEST_PATH = PROCESSED_DIR / "electricity_confirmatory_challenger_manifest.json"
SELECTION_BOOTSTRAP_N = 2000
PLACEBO_N = 1000


def challenger_configs() -> list[dict[str, Any]]:
    return [
        {
            "policy": "R2_all_only_trainalpha_B6_rel5",
            "bundle": "B6_full_without_change",
            "target_type": "relative",
            "alpha_candidates": ALPHAS,
            "clip_rule": "rel0.05",
            "mask": "S3_all_only",
            "description": "All-only B6 train-selected alpha, relative 5% clipping",
        },
        {
            "policy": "R3b_all_only_conservative_B4_rel5",
            "bundle": "B4_level_normalized",
            "target_type": "relative",
            "alpha_candidates": CONSERVATIVE_ALPHAS,
            "clip_rule": "rel0.05",
            "mask": "S3_all_only",
            "description": "All-only B4 conservative alpha, relative 5% clipping",
        },
    ]


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


def material_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    material = 0
    plus_5 = 0
    plus_10 = 0
    for row in rows:
        global_row = {**row, "prediction": row["global_prediction"]}
        base_err = abs(float(row["global_prediction"]) - float(row["actual"]))
        err = abs(float(row["prediction"]) - float(row["actual"]))
        delta_ape = ape(row, "prediction") - ape(global_row, "prediction")
        if err > base_err * 1.1 and err - base_err > abs(float(row["actual"])) * 0.02:
            material += 1
        if delta_ape > 5:
            plus_5 += 1
        if delta_ape > 10:
            plus_10 += 1
    return {"material_degradation_count": material, "ape_plus_5pp_count": plus_5, "ape_plus_10pp_count": plus_10}


def policy_eval(panel: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    preds, _audits, alpha_rows, _coef = run_policy(panel, cfg)
    return preds, alpha_rows


def alpha_cv_sampled(sampled_panel: list[dict[str, Any]], cfg: dict[str, Any], test_year: int) -> tuple[float, float]:
    fields = FEATURE_BUNDLES[cfg["bundle"]]
    alpha, scores = alpha_cv_local(sampled_panel, test_year, fields, cfg)
    best = min((r for r in scores if float(r["alpha"]) == alpha), key=lambda r: float(r["validation_score"]))
    return alpha, float(best["validation_score"])


def evaluate_on_holdout(
    panel: list[dict[str, Any]],
    cfg: dict[str, Any],
    sampled_clusters: list[str],
    holdout_clusters: set[str],
) -> tuple[list[dict[str, Any]], float, list[float]]:
    sampled_counts = Counter(sampled_clusters)
    sampled_panel = []
    for row in panel:
        count = sampled_counts.get(row["sigungu_feature_key"], 0)
        for _idx in range(count):
            sampled_panel.append(row.copy())
    validation_scores = []
    selected_alphas = []
    out = []
    for test_year in (2022, 2023):
        alpha, score = alpha_cv_sampled(sampled_panel, cfg, test_year)
        selected_alphas.append(alpha)
        validation_scores.append(score)
        train_years = {2021} if test_year == 2022 else {2021, 2022}
        train = [r for r in sampled_panel if int(r["target_year"]) in train_years and r["prediction_origin_id"] == PRIMARY_ORIGIN]
        test = [
            r
            for r in panel
            if int(r["target_year"]) == test_year
            and r["prediction_origin_id"] == PRIMARY_ORIGIN
            and r["sigungu_feature_key"] in holdout_clusters
        ]
        pred, _audit = predict_candidate_rows(
            train,
            test,
            policy=cfg["policy"],
            fields=FEATURE_BUNDLES[cfg["bundle"]],
            target_type=cfg["target_type"],
            alpha=alpha,
            clip_rule=cfg["clip_rule"],
            mask=cfg["mask"],
        )
        for row in pred:
            row["selected_alpha"] = alpha
        out.extend(pred)
    return out, mean(validation_scores), selected_alphas


def selection_aware_bootstrap(panel: list[dict[str, Any]], cfgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters = sorted({r["sigungu_feature_key"] for r in panel if r["prediction_origin_id"] == PRIMARY_ORIGIN})
    rng = random.Random(RNG_SEED + 303)
    selected_policy = Counter()
    selected_alpha = Counter()
    deltas = []
    for _idx in range(SELECTION_BOOTSTRAP_N):
        sampled = [rng.choice(clusters) for _ in range(len(clusters))]
        holdout = set(clusters) - set(sampled)
        if not holdout:
            holdout = set(sampled[: max(1, len(sampled) // 5)])
        candidates = []
        for cfg in cfgs:
            preds, score, alphas = evaluate_on_holdout(panel, cfg, sampled, holdout)
            candidates.append((score, cfg["policy"], preds, alphas))
        _score, policy, preds, alphas = min(candidates, key=lambda x: (x[0], x[1]))
        selected_policy[policy] += 1
        selected_alpha["/".join(str(a) for a in alphas)] += 1
        if preds:
            deltas.append(wmape(preds, "global_prediction") - wmape(preds, "prediction"))
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


def selection_aware_bootstrap_from_predictions(policy_predictions: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    policies = sorted(policy_predictions)
    base_rows = next(iter(policy_predictions.values()))
    clusters = sorted({r["sigungu_feature_key"] for r in base_rows})
    rows_by_cluster = {policy: groupby(rows, ["sigungu_feature_key"]) for policy, rows in policy_predictions.items()}
    rng = random.Random(RNG_SEED + 404)
    selected_policy = Counter()
    selected_alpha = Counter()
    deltas = []
    for _idx in range(SELECTION_BOOTSTRAP_N):
        sampled = [rng.choice(clusters) for _ in range(len(clusters))]
        sampled_set = set(sampled)
        holdout = [c for c in clusters if c not in sampled_set]
        if not holdout:
            holdout = sampled[: max(1, len(sampled) // 5)]
        scores = []
        for policy in policies:
            sample_rows = []
            for cluster in sampled:
                sample_rows.extend(rows_by_cluster[policy].get((cluster,), []))
            scores.append((wmape(sample_rows, "prediction"), policy))
        _score, policy = min(scores, key=lambda x: (x[0], x[1]))
        selected_policy[policy] += 1
        alphas = sorted({str(r.get("selected_alpha", "")) for r in policy_predictions[policy] if r.get("selected_alpha", "") != ""})
        selected_alpha["/".join(alphas)] += 1
        eval_rows = []
        for cluster in holdout:
            eval_rows.extend(rows_by_cluster[policy].get((cluster,), []))
        if eval_rows:
            deltas.append(wmape(eval_rows, "global_prediction") - wmape(eval_rows, "prediction"))
    out = [
        {
            "summary_type": "selection_aware_delta_fixed_policy",
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


def permute_features(rows: list[dict[str, Any]], cfg: dict[str, Any], rng: random.Random, mode: str) -> list[dict[str, Any]]:
    out = [r.copy() for r in rows]
    keys = [f"feature_{field}" for field in FEATURE_BUNDLES[cfg["bundle"]]]
    if mode == "noise":
        for row in out:
            for key in keys:
                row[key] = rng.gauss(0, 1)
        return out
    group_keys = ["target_year", "prediction_origin_id"] if mode == "region" else ["sigungu_feature_key", "prediction_origin_id"]
    for _key, items in groupby(out, group_keys).items():
        blocks = [{k: r.get(k, "") for k in keys} for r in items]
        rng.shuffle(blocks)
        for row, block in zip(items, blocks):
            row.update(block)
    return out


def fixed_alpha_policy_eval(panel: list[dict[str, Any]], cfg: dict[str, Any], alpha_by_year: dict[int, float]) -> list[dict[str, Any]]:
    rows = []
    for test_year in (2022, 2023):
        train, test = split_rows(panel, test_year, PRIMARY_ORIGIN)
        pred, _audit = predict_candidate_rows(
            train,
            test,
            policy=cfg["policy"],
            fields=FEATURE_BUNDLES[cfg["bundle"]],
            target_type=cfg["target_type"],
            alpha=alpha_by_year.get(test_year, 0.0),
            clip_rule=cfg["clip_rule"],
            mask=cfg["mask"],
        )
        for row in pred:
            row["selected_alpha"] = alpha_by_year.get(test_year, 0.0)
        rows.extend(pred)
    return rows


def selected_alpha_by_year(preds: list[dict[str, Any]]) -> dict[int, float]:
    out = {}
    for (year,), rows in groupby(preds, ["target_year"]).items():
        vals = sorted({float(r.get("selected_alpha") or 0.0) for r in rows})
        out[int(year)] = vals[-1] if vals else 0.0
    return out


def placebo(panel: list[dict[str, Any]], cfg: dict[str, Any], real_delta: float, alpha_by_year: dict[int, float]) -> list[dict[str, Any]]:
    rows = []
    for mode in ("region", "temporal", "noise"):
        rng = random.Random(RNG_SEED + len(mode) + len(cfg["policy"]))
        deltas = []
        for _idx in range(PLACEBO_N):
            fake_panel = permute_features(panel, cfg, rng, mode)
            preds = fixed_alpha_policy_eval(fake_panel, cfg, alpha_by_year)
            deltas.append(wmape(preds, "global_prediction") - wmape(preds, "prediction"))
        rows.append(
            {
                "policy": cfg["policy"],
                "placebo_type": mode,
                "iterations": PLACEBO_N,
                "real_improvement": round(real_delta, 6),
                "placebo_mean": round(mean(deltas), 6),
                "placebo_p90": round(pctl(deltas, 90), 6),
                "placebo_p95": round(pctl(deltas, 95), 6),
                "placebo_p99": round(pctl(deltas, 99), 6),
                "real_improvement_percentile": round(sum(1 for v in deltas if v <= real_delta) / len(deltas), 6),
                "pass_p95": "Y" if real_delta > pctl(deltas, 95) else "N",
            }
        )
    return rows


def loso_summary(panel: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = run_loso(panel, cfg)
    deltas = [float(r["delta_positive_good"]) for r in rows]
    summary = {
        "policy": cfg["policy"],
        "improved_sido_count": sum(1 for v in deltas if v > 0),
        "degraded_sido_count": sum(1 for v in deltas if v < 0),
        "median_sido_delta": round(median(deltas), 6) if deltas else 0,
        "worst_sido_delta": round(min(deltas), 6) if deltas else 0,
    }
    for row in rows:
        row["policy"] = cfg["policy"]
    return rows, summary


def large_summary(compared_rows: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    rows = run_large_observation_audit(compared_rows)
    for row in rows:
        row["policy"] = policy
    return rows


def year_delta_rows(preds: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    rows = []
    for (year,), items in sorted(groupby(preds, ["target_year"]).items()):
        rows.append(
            {
                "policy": policy,
                "target_year": year,
                "global_wmape": round(wmape(items, "global_prediction"), 6),
                "candidate_wmape": round(wmape(items, "prediction"), 6),
                "delta_positive_good": round(wmape(items, "global_prediction") - wmape(items, "prediction"), 6),
            }
        )
    return rows


def compare_to_global(global_pred: list[dict[str, Any]], preds: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    g = {(r["sigungu_feature_key"], r["sector_code"], int(r["target_year"]), r["prediction_origin_id"]): r for r in global_pred}
    out = []
    for row in preds:
        key = (row["sigungu_feature_key"], row["sector_code"], int(row["target_year"]), row["prediction_origin_id"])
        base = g.get(key)
        if not base:
            continue
        rec = row.copy()
        rec["policy"] = policy
        rec["global_ref_prediction"] = base["prediction"]
        out.append(rec)
    return out


def gate_results(
    cfg: dict[str, Any],
    metric: dict[str, Any],
    years: list[dict[str, Any]],
    placebo_rows: list[dict[str, Any]],
    selection_rows: list[dict[str, Any]],
    loso: dict[str, Any],
    large_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    year_by = {int(r["target_year"]): float(r["delta_positive_good"]) for r in years if r["policy"] == cfg["policy"]}
    selection_prob = next((float(r["probability_of_improvement"]) for r in selection_rows if r["summary_type"].startswith("selection_aware_delta")), 0.0)
    rows = [
        {"policy": cfg["policy"], "gate": "data_integrity", "pass": "Y", "note": "primary vintage audit has zero leakage"},
        {"policy": cfg["policy"], "gate": "year_consistency", "pass": "Y" if year_by.get(2022, 0) > 0 and year_by.get(2023, -999) >= -0.10 and float(metric["delta_positive_good"]) > 0 else "N", "note": f"2022={year_by.get(2022)}, 2023={year_by.get(2023)}, pooled={metric['delta_positive_good']}"},
        {"policy": cfg["policy"], "gate": "placebo", "pass": "Y" if all(r["pass_p95"] == "Y" for r in placebo_rows if r["policy"] == cfg["policy"]) else "N", "note": "requires all three placebo p95 passes"},
        {"policy": cfg["policy"], "gate": "selection_aware_bootstrap", "pass": "Y" if selection_prob >= 0.90 else "N", "note": f"P(improve)={selection_prob}"},
        {"policy": cfg["policy"], "gate": "tail_stability", "pass": "Y" if int(metric["material_degradation_count"]) == 0 and int(metric["ape_plus_5pp_count"]) == 0 and int(metric["ape_plus_10pp_count"]) == 0 else "N", "note": f"material={metric['material_degradation_count']}, +5pp={metric['ape_plus_5pp_count']}, +10pp={metric['ape_plus_10pp_count']}"},
        {"policy": cfg["policy"], "gate": "region_generalization", "pass": "Y" if int(loso["improved_sido_count"]) >= 9 and float(loso["worst_sido_delta"]) >= -0.25 else "N", "note": f"improved={loso['improved_sido_count']}, worst={loso['worst_sido_delta']}"},
        {"policy": cfg["policy"], "gate": "large_observation_removal", "pass": "Y" if all(float(r["delta_positive_good"]) > 0 for r in large_rows if r["policy"] == cfg["policy"]) else "N", "note": "requires positive improvement after every removal"},
    ]
    return rows


def decide_challenger(gates: list[dict[str, Any]], metrics: list[dict[str, Any]], placebo_rows: list[dict[str, Any]], selection_rows: list[dict[str, Any]]) -> tuple[str, str]:
    cfg_names = [cfg["policy"] for cfg in challenger_configs()]
    passed = [name for name in cfg_names if all(r["pass"] == "Y" for r in gates if r["policy"] == name)]
    if len(passed) == 1:
        return passed[0], "single_candidate_passed_all_gates"
    if len(passed) == 2:
        metric_by = {r["policy"]: r for r in metrics}
        year_2023 = {}
        for name in passed:
            # More positive is better; if not present, neutral.
            year_2023[name] = 0.0
        ranked = sorted(passed, key=lambda p: (float(metric_by[p]["delta_positive_good"]), -len(FEATURE_BUNDLES[next(c for c in challenger_configs() if c["policy"] == p)["bundle"]])), reverse=True)
        return ranked[0], "both_passed_selected_by_predefined_tiebreak"
    return "none", "no_candidate_passed_all_preconfirmatory_gates"


def write_manifest(challenger: str, reason: str, gates: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> None:
    selected_cfg = next((c for c in challenger_configs() if c["policy"] == challenger), None)
    manifest = {
        "confirmatory_challenger": challenger,
        "selection_reason": reason,
        "operating_policy": "global",
        "production_replacement": "prohibited",
        "shadow_evaluation": "allowed" if challenger != "none" else "disabled",
        "policy_version": "electricity_preconfirmatory_selection_v1",
        "feature_bundle": selected_cfg["bundle"] if selected_cfg else "",
        "feature_source_version": "kepco_historical_vintage_selector_v1",
        "prediction_origin": PRIMARY_ORIGIN,
        "training_window": "2021 for 2022; 2021-2022 for 2023",
        "residual_target": selected_cfg["target_type"] if selected_cfg else "",
        "ridge_lambda_selection_rule": "train-period ridge lambda selection over fixed grid",
        "alpha_selection_rule": "R2 full grid or R3b conservative grid, validation-only",
        "clipping_rule": "relative 5%",
        "coverage_rule": "prior-vintage recalculation; require window coverage >= 0.90",
        "prior_vintage_recalculation_rule": "if latest eligible month missing, recompute using previous available vintage before fallback",
        "application_sector": "all only",
        "fallback_rule": "C00 global; D00 global; unavailable feature global",
        "development_actual_period": "2022-2023",
        "confirmatory_actual_period": "2024_or_first_unused_official_actual",
        "acceptance_criteria": {
            "challenger_wmape": "< champion global WMAPE",
            "relative_wmape_improvement": ">= 1.0%",
            "macro_wmape": "<= champion macro WMAPE",
            "median_ape_deterioration": "<= 0.10pp",
            "p90_ape_deterioration": "<= 0.10pp",
            "material_degradation_count": 0,
            "severe_degradation_count": 0,
        },
        "gate_results": gates,
        "development_metrics": metrics,
        "input_hashes": {
            "kepco_historical_vintage_long.csv": file_hash(PROCESSED_DIR / "kepco_historical_vintage_long.csv"),
            "sigungu_global_model_pilot_predictions.csv": file_hash(PROCESSED_DIR / "sigungu_global_model_pilot_predictions.csv"),
        },
        "code_commit_hash": git_hash(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(
    metrics: list[dict[str, Any]],
    years: list[dict[str, Any]],
    selection_rows: list[dict[str, Any]],
    placebo_rows: list[dict[str, Any]],
    loso_summary_rows: list[dict[str, Any]],
    large_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    challenger: str,
    reason: str,
) -> None:
    lines = [
        "# 전력 Feature Pre-confirmatory Policy Selection",
        "",
        "## 현재 상태",
        "",
        "- champion: `global`",
        "- challenger candidates: `R2_all_only_trainalpha_B6_rel5`, `R3b_all_only_conservative_B4_rel5`",
        "- production replacement: prohibited",
        f"- final confirmatory challenger: `{challenger}`",
        f"- selection reason: `{reason}`",
        "",
        "## 후보 정의",
        "",
        "| policy | feature bundle | alpha grid | application | fallback |",
        "| --- | --- | --- | --- | --- |",
    ]
    for cfg in challenger_configs():
        lines.append(f"| {cfg['policy']} | {cfg['bundle']} | {','.join(map(str, cfg['alpha_candidates']))} | all only | C00/D00/global unavailable |")
    lines.extend(["", "## R2/R3b 성능 비교", "", "| policy | WMAPE | global WMAPE | delta +good | relative % | macro WMAPE | median APE delta | p90 APE delta | material | +5pp | +10pp |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for row in metrics:
        lines.append(f"| {row['policy']} | {row['wmape']} | {row['global_wmape_same_rows']} | {row['delta_positive_good']} | {row['relative_improvement_pct']} | {row['macro_region_wmape']} | {row['median_ape_delta_pp']} | {row['p90_ape_delta_pp']} | {row['material_degradation_count']} | {row['ape_plus_5pp_count']} | {row['ape_plus_10pp_count']} |")
    lines.extend(["", "## 연도별 결과", "", "| policy | year | global WMAPE | candidate WMAPE | delta +good |", "| --- | ---: | ---: | ---: | ---: |"])
    for row in years:
        lines.append(f"| {row['policy']} | {row['target_year']} | {row['global_wmape']} | {row['candidate_wmape']} | {row['delta_positive_good']} |")
    lines.extend(["", "## Selection-aware Bootstrap", "", "| type | selected | count | frequency | mean | median | CI 2.5 | CI 97.5 | P(improve) |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for row in selection_rows:
        lines.append(f"| {row['summary_type']} | {row.get('selected_policy') or row.get('selected_alpha', '')} | {row.get('count', '')} | {row.get('frequency', '')} | {row.get('mean_improvement', '')} | {row.get('median_improvement', '')} | {row.get('ci_low_2_5', '')} | {row.get('ci_high_97_5', '')} | {row.get('probability_of_improvement', '')} |")
    lines.extend(["", "## Placebo", "", "| policy | placebo | real | mean | p90 | p95 | p99 | percentile | pass p95 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"])
    for row in placebo_rows:
        lines.append(f"| {row['policy']} | {row['placebo_type']} | {row['real_improvement']} | {row['placebo_mean']} | {row['placebo_p90']} | {row['placebo_p95']} | {row['placebo_p99']} | {row['real_improvement_percentile']} | {row['pass_p95']} |")
    lines.extend(["", "## LOSO", "", "| policy | improved | degraded | median delta | worst delta |", "| --- | ---: | ---: | ---: | ---: |"])
    for row in loso_summary_rows:
        lines.append(f"| {row['policy']} | {row['improved_sido_count']} | {row['degraded_sido_count']} | {row['median_sido_delta']} | {row['worst_sido_delta']} |")
    lines.extend(["", "## Large-observation Removal", "", "| policy | metric | top % | global WMAPE | candidate WMAPE | delta +good |", "| --- | --- | ---: | ---: | ---: | ---: |"])
    for row in large_rows:
        lines.append(f"| {row['policy']} | {row['removal_metric']} | {row['removed_top_pct']} | {row['global_wmape']} | {row['candidate_wmape']} | {row['delta_positive_good']} |")
    lines.extend(["", "## Missingness", "", "| policy | scenario | coverage | base delta | delta +good |", "| --- | --- | ---: | ---: | ---: |"])
    for row in missing_rows:
        lines.append(f"| {row['policy']} | {row['scenario']} | {row.get('coverage_threshold', '')} | {row['base_delta']} | {row['delta_positive_good']} |")
    lines.extend(["", "## Gate 판정", "", "| policy | gate | pass | note |", "| --- | --- | --- | --- |"])
    for row in gates:
        lines.append(f"| {row['policy']} | {row['gate']} | {row['pass']} | {row['note']} |")
    lines.extend(
        [
            "",
            "## 최종 행동양식",
            "",
            f"- confirmatory challenger: `{challenger}`",
            "- operating policy remains: `global`",
            "- C00 policy: global fallback",
            "- D00 policy: global fallback",
            "- no additional 2022-2023 tuning is allowed after this report",
            "- if challenger is `none`, electricity-only policy remains research candidate only",
            "",
            "## Manifest 요약",
            "",
            f"- manifest: `data/processed/{MANIFEST_PATH.name}`",
            "- confirmatory actual: 2024 이후 또는 최초 미사용 official actual",
            "- confirmatory failure action: reject frozen challenger and retain global; no same-actual retuning",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    vintage = load_or_build_vintage_long()
    features, audit, _long = build_asof_features(vintage)
    if any(r.get("leakage_violation") == "Y" for r in audit):
        raise SystemExit("Vintage leakage detected.")
    panel = [r for r in join_panel(load_targets(), features) if r["prediction_origin_id"] == PRIMARY_ORIGIN]
    g_rows = global_rows(panel)
    cfgs = challenger_configs()

    by_policy: dict[str, list[dict[str, Any]]] = {}
    alpha_rows = []
    for cfg in cfgs:
        preds, alphas = policy_eval(panel, cfg)
        by_policy[cfg["policy"]] = preds
        alpha_rows.extend(alphas)

    metrics = []
    year_rows = []
    degradation_rows = []
    large_rows = []
    loso_detail = []
    loso_summary_rows = []
    missing_rows = []
    placebo_rows = []
    for cfg in cfgs:
        preds = by_policy[cfg["policy"]]
        metric = metric_row(preds, cfg["policy"])
        metric.update(material_counts(preds))
        metrics.append(metric)
        year_rows.extend(year_delta_rows(preds, cfg["policy"]))
        compared = compare_to_global(g_rows, preds, cfg["policy"])
        degradation_rows.extend(compared)
        large_rows.extend(large_summary(compared, cfg["policy"]))
        loso_rows, loso_s = loso_summary(panel, cfg)
        loso_detail.extend(loso_rows)
        loso_summary_rows.append(loso_s)
        m_rows = run_missingness(vintage, panel, cfg)
        for row in m_rows:
            row["policy"] = cfg["policy"]
        missing_rows.extend(m_rows)
        real_delta = wmape(preds, "global_prediction") - wmape(preds, "prediction")
        placebo_rows.extend(placebo(panel, cfg, real_delta, selected_alpha_by_year(preds)))

    selection_rows = selection_aware_bootstrap(panel, cfgs)
    gates = []
    for cfg in cfgs:
        metric = next(r for r in metrics if r["policy"] == cfg["policy"])
        loso_s = next(r for r in loso_summary_rows if r["policy"] == cfg["policy"])
        gates.extend(gate_results(cfg, metric, year_rows, placebo_rows, selection_rows, loso_s, large_rows))
    challenger, reason = decide_challenger(gates, metrics, placebo_rows, selection_rows)

    write_csv(PROCESSED_DIR / "electricity_r2_r3b_comparison.csv", metrics + year_rows + alpha_rows)
    write_csv(PROCESSED_DIR / "electricity_r2_r3b_selection_aware_bootstrap.csv", selection_rows)
    write_csv(PROCESSED_DIR / "electricity_r2_r3b_placebo.csv", placebo_rows)
    write_csv(PROCESSED_DIR / "electricity_r2_r3b_loso.csv", loso_detail + loso_summary_rows)
    write_csv(PROCESSED_DIR / "electricity_r2_r3b_large_removal.csv", large_rows)
    write_csv(PROCESSED_DIR / "electricity_r2_r3b_degradation.csv", degradation_rows)

    write_manifest(challenger, reason, gates, metrics)
    write_report(metrics, year_rows, selection_rows, placebo_rows, loso_summary_rows, large_rows, missing_rows, gates, challenger, reason)
    print(f"panel rows: {len(panel)}")
    print(f"confirmatory challenger: {challenger}")
    print(f"reason: {reason}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
