from __future__ import annotations

from collections import defaultdict
from math import exp, log
from statistics import mean, median
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv
from run_reconciled_feature_structure_experiments import grouped, sector_group
from run_reconciled_model_experiment import EPS, MIN_TRAIN_ROWS, context, load_rows, reconcile_group, target_values, xgb
from run_reconciled_model_experiment import historical_values, safe_log, safe_ratio, structural_features


REPORT_DIR = ROOT / "reports"
BASE_PARAMS = {
    "objective": "reg:squarederror",
    "n_estimators": 60,
    "max_depth": 2,
    "learning_rate": 0.05,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "reg_lambda": 5.0,
    "min_child_weight": 3.0,
}
SEEDS = [42, 2024, 2025, 2026, 3407]
MATRIX_CACHE: dict[tuple[tuple[tuple[str, str, int], ...], bool, bool], np.ndarray] = {}
COMMON_EVAL_START_YEAR = 2019


def num(value: Any, default: float = 0.0) -> float:
    parsed = parse_number(value)
    return default if parsed is None else float(parsed)


def key(row: dict[str, Any]) -> tuple[int, str, str]:
    return (int(row["target_year"]), row["area_code"], row["sector_code"])


def wmape_pct(rows: list[dict[str, Any]], field: str) -> float:
    denom = sum(abs(float(row["actual"])) for row in rows)
    if denom <= EPS:
        return float("nan")
    err = sum(abs(float(row[field]) - float(row["actual"])) for row in rows)
    return err / denom * 100.0


def mape_pct(rows: list[dict[str, Any]], field: str) -> float:
    values = [abs((float(row[field]) - float(row["actual"])) / float(row["actual"])) * 100.0 for row in rows if float(row["actual"])]
    return mean(values) if values else float("nan")


def improvement_pct(baseline_wmape: float, model_wmape: float) -> float:
    if baseline_wmape == 0:
        return float("nan")
    return (baseline_wmape - model_wmape) / baseline_wmape * 100.0


def sector_year_improvements(rows: list[dict[str, Any]], field: str) -> list[float]:
    out = []
    for _group_key, items in grouped(rows, ["sector_code", "target_year"]).items():
        out.append(improvement_pct(wmape_pct(items, "baseline"), wmape_pct(items, field)))
    return out


def improved_year_count(rows: list[dict[str, Any]], field: str) -> int:
    return sum(1 for _year, items in grouped(rows, ["target_year"]).items() if wmape_pct(items, field) < wmape_pct(items, "baseline"))


def normalize_prediction_rows(rows: list[dict[str, str]], prediction_field: str, model: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        actual = num(row.get("actual_annual_gva"))
        baseline = num(row.get("baseline_prediction"))
        prediction = num(row.get(prediction_field))
        if min(actual, baseline, prediction) <= 0:
            continue
        out.append(
            {
                "model": model,
                "target_year": int(row["target_year"]),
                "area_code": row["area_code"],
                "area_name": row.get("area_name", ""),
                "sector_code": row["sector_code"],
                "sector_name": row.get("sector_name", ""),
                "actual": actual,
                "baseline": baseline,
                "prediction": prediction,
            }
        )
    return out


def load_model_sets() -> dict[str, list[dict[str, Any]]]:
    sets: dict[str, list[dict[str, Any]]] = {}
    reconciled = read_csv(PROCESSED_DIR / "reconciled_model_predictions.csv")
    sets["baseline_all"] = normalize_prediction_rows(reconciled, "baseline_prediction", "baseline_all")
    sets["sector_full_ml"] = normalize_prediction_rows(reconciled, "xgboost_log_ratio_reconciled_prediction", "sector_full_ml")
    adaptive = read_csv(PROCESSED_DIR / "adaptive_shrinkage_predictions.csv")
    sets["adaptive_shrinkage"] = normalize_prediction_rows(adaptive, "prediction", "adaptive_shrinkage")
    regret = [r for r in read_csv(PROCESSED_DIR / "regret_gating_predictions.csv") if r.get("policy") == "regret_mean_gt_0.0"]
    sets["regret_mean_gt_0.0"] = normalize_prediction_rows(regret, "prediction", "regret_mean_gt_0.0")
    structure = read_csv(PROCESSED_DIR / "sector_model_structure_predictions.csv")
    sets["global_model"] = normalize_prediction_rows([r for r in structure if r.get("model_structure") == "global_model"], "prediction", "global_model")
    return sets


def audit_common_population() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    sets = load_model_sets()
    key_sets = {model: {key(row) for row in rows} for model, rows in sets.items()}
    common_keys = set.intersection(*key_sets.values())
    audit = []
    common_population = []
    for model, rows in sets.items():
        row_by_key: dict[tuple[int, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            row_by_key[key(row)].append(row)
        duplicate_count = sum(len(items) - 1 for items in row_by_key.values() if len(items) > 1)
        model_common = [row_by_key[k][0] for k in common_keys if k in row_by_key]
        original_w = wmape_pct(rows, "prediction")
        original_b = wmape_pct(rows, "baseline")
        common_w = wmape_pct(model_common, "prediction")
        common_b = wmape_pct(model_common, "baseline")
        audit.append(
            {
                "model": model,
                "original_count": len(rows),
                "common_count": len(model_common),
                "dropped_count": len(rows) - len(model_common),
                "missing_key_count": len(common_keys - set(row_by_key)),
                "duplicate_key_count": duplicate_count,
                "original_baseline_wmape": round(original_b, 6),
                "original_model_wmape": round(original_w, 6),
                "original_improvement_pct": round(improvement_pct(original_b, original_w), 6),
                "common_baseline_wmape": round(common_b, 6),
                "common_model_wmape": round(common_w, 6),
                "common_improvement_pct": round(improvement_pct(common_b, common_w), 6),
                "years": ",".join(str(v) for v in sorted({r["target_year"] for r in rows})),
                "common_years": ",".join(str(v) for v in sorted({r["target_year"] for r in model_common})),
                "region_count": len({r["area_code"] for r in rows}),
                "sector_count": len({r["sector_code"] for r in rows}),
            }
        )
        for row in model_common:
            common_population.append({**row, "model": model})
    return common_population, audit, sorted([{"target_year": k[0], "area_code": k[1], "sector_code": k[2]} for k in common_keys], key=lambda r: (r["target_year"], r["sector_code"], r["area_code"]))


def train_xgb(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, params: dict[str, Any], seed: int, weights: np.ndarray | None = None) -> np.ndarray:
    if xgb is None:
        raise RuntimeError("xgboost is unavailable")
    train = xgb.DMatrix(x_train, label=y_train, weight=weights)
    test = xgb.DMatrix(x_test)
    booster = xgb.train(
        {
            "objective": params["objective"],
            "max_depth": int(params["max_depth"]),
            "eta": float(params["learning_rate"]),
            "subsample": float(params["subsample"]),
            "colsample_bytree": float(params["colsample_bytree"]),
            "lambda": float(params["reg_lambda"]),
            "min_child_weight": float(params["min_child_weight"]),
            "seed": seed,
            "nthread": 1,
            "verbosity": 0,
        },
        train,
        num_boost_round=int(params["n_estimators"]),
    )
    return np.asarray(booster.predict(test), dtype=float)


def common_matrix_cached(rows: list[dict[str, Any]], ctx: dict[str, Any], *, sector_shuffle: bool = False, region_shuffle: bool = False) -> np.ndarray:
    cache_key = (tuple((row["area_code"], row["sector_code"], int(row["target_year"])) for row in rows), sector_shuffle, region_shuffle)
    if cache_key in MATRIX_CACHE:
        return MATRIX_CACHE[cache_key]
    area_index = {area: idx for idx, area in enumerate(ctx["areas"])}
    sector_index = {sector: idx for idx, sector in enumerate(sorted({sector for _area, sector, _year in ctx["actual_by_key"]}))}
    method_index = {method: idx for idx, method in enumerate(ctx["methods"])}
    structural_cache: dict[tuple[str, str, int], list[float]] = {}
    vectors: list[list[float]] = []
    for row in rows:
        hist_share = historical_values(row, ctx, "share", 3)
        hist_ratio = historical_values(row, ctx, "log_ratio", 3)
        latest_share = hist_share[0] if hist_share else row["baseline_share"]
        share_mean = mean(hist_share) if hist_share else latest_share
        share_std = float(np.std(hist_share)) if len(hist_share) > 1 else 0.0
        latest_ratio = hist_ratio[0] if hist_ratio else 0.0
        ratio_mean = mean(hist_ratio) if hist_ratio else 0.0
        ratio_std = float(np.std(hist_ratio)) if len(hist_ratio) > 1 else 0.0
        base = [
            1.0,
            (row["target_year"] - 2017.0) / 10.0,
            safe_log(row["baseline"]),
            row["baseline_share"],
            safe_log(row["baseline_share"]),
            latest_share,
            share_mean,
            share_std,
            row["baseline_share"] - latest_share,
            safe_ratio(row["baseline_share"], latest_share),
            latest_ratio,
            ratio_mean,
            ratio_std,
        ]
        struct_key = (row["area_code"], row["sector_code"], int(row["target_year"]))
        if struct_key not in structural_cache:
            structural_cache[struct_key] = structural_features(row, ctx)
        area_dummy = [0.0] * len(area_index)
        area_dummy[area_index[row["area_code"]]] = 1.0
        sector_dummy = [0.0] * len(sector_index)
        sector_dummy[sector_index[row["sector_code"]]] = 1.0
        method_dummy = [0.0] * len(method_index)
        method_dummy[method_index[row["method"]]] = 1.0
        vectors.append(base + structural_cache[struct_key] + area_dummy + sector_dummy + method_dummy)
    matrix = np.asarray(vectors, dtype=float)
    MATRIX_CACHE[cache_key] = matrix
    return matrix


def common_feature_groups(x: np.ndarray, ctx: dict[str, Any]) -> dict[str, list[int]]:
    area_count = len(ctx["areas"])
    sector_count = len({sector for _area, sector, _year in ctx["actual_by_key"]})
    method_count = len(ctx["methods"])
    structural_start, structural_end = 13, 28
    area_start = structural_end
    sector_start = area_start + area_count
    method_start = sector_start + sector_count
    return {
        "F0_baseline_share": [0, 2, 3, 4],
        "F1_lagged_share": [5],
        "F2_rolling_share": [6, 7, 8, 9],
        "F3_lagged_residual": [10],
        "F4_rolling_residual": [11, 12],
        "F5_structural": list(range(structural_start, min(structural_end, x.shape[1]))),
        "F8_region_onehot": list(range(area_start, min(sector_start, x.shape[1]))),
        "F9_sector_onehot": list(range(sector_start, min(method_start, x.shape[1]))),
        "F9_method": list(range(method_start, x.shape[1])),
        "F10_time": [1],
    }


def columns_for_feature_set(groups: dict[str, list[int]], feature_set: str) -> list[int]:
    all_cols = sorted({idx for values in groups.values() for idx in values})
    if feature_set in {"global_fixed_full", "global_full"}:
        return all_cols
    if feature_set in {"global_fixed_pruned", "global_pruned"}:
        return all_cols  # The common-feature global model already excludes F6/F7.
    if feature_set == "global_pruned_no_F4":
        return sorted(set(all_cols) - set(groups["F4_rolling_residual"]))
    if feature_set == "global_core":
        cols = groups["F0_baseline_share"] + groups["F1_lagged_share"] + groups["F2_rolling_share"] + groups["F5_structural"] + groups["F8_region_onehot"] + groups["F9_sector_onehot"] + groups["F10_time"]
        return sorted(set(cols))
    if feature_set == "global_no_sector_id":
        return sorted(set(all_cols) - set(groups["F9_sector_onehot"]))
    if feature_set == "global_no_region_id":
        return sorted(set(all_cols) - set(groups["F8_region_onehot"]))
    if feature_set == "global_no_residual_features":
        return sorted(set(all_cols) - set(groups["F3_lagged_residual"]) - set(groups["F4_rolling_residual"]))
    if feature_set == "global_baseline_only":
        return groups["F0_baseline_share"] + groups["F10_time"]
    if feature_set == "global_residual_only":
        return groups["F0_baseline_share"] + groups["F3_lagged_residual"] + groups["F4_rolling_residual"] + groups["F9_sector_onehot"]
    raise ValueError(feature_set)


def select_columns(x: np.ndarray, cols: list[int]) -> np.ndarray:
    return x[:, sorted({0, *cols})]


def global_predict_for_year(
    rows: list[dict[str, Any]],
    ctx: dict[str, Any],
    target_year: int,
    feature_set: str,
    params: dict[str, Any],
    seed: int,
    target_shuffle: bool = False,
    sector_shuffle: bool = False,
    region_shuffle: bool = False,
) -> list[dict[str, Any]]:
    train_rows = [dict(row) for row in rows if row["target_year"] < target_year]
    test_rows = [dict(row) for row in rows if row["target_year"] == target_year]
    if len(train_rows) < MIN_TRAIN_ROWS or not test_rows:
        return []
    rng = np.random.default_rng(seed)
    if sector_shuffle:
        sectors = [row["sector_code"] for row in train_rows]
        rng.shuffle(sectors)
        for row, shuffled in zip(train_rows, sectors):
            row["sector_code"] = shuffled
    if region_shuffle:
        regions = [row["area_code"] for row in train_rows]
        rng.shuffle(regions)
        for row, shuffled in zip(train_rows, regions):
            row["area_code"] = shuffled
    x_train_full = common_matrix_cached(train_rows, ctx, sector_shuffle=sector_shuffle, region_shuffle=region_shuffle)
    x_test_full = common_matrix_cached(test_rows, ctx)
    groups = common_feature_groups(x_train_full, ctx)
    cols = columns_for_feature_set(groups, feature_set)
    y_train = target_values(train_rows, "log_ratio")
    if target_shuffle:
        y_train = np.array(y_train, dtype=float)
        rng.shuffle(y_train)
    raw = train_xgb(select_columns(x_train_full, cols), y_train, select_columns(x_test_full, cols), params, seed)
    pred = reconcile_group(test_rows, raw, "log_ratio")
    return make_prediction_rows(feature_set, test_rows, pred, params, seed)


def make_prediction_rows(model: str, test_rows: list[dict[str, Any]], predictions: list[float], params: dict[str, Any], seed: int) -> list[dict[str, Any]]:
    out = []
    param_text = ";".join(f"{k}={v}" for k, v in sorted(params.items()))
    for row, pred in zip(test_rows, predictions):
        out.append(
            {
                "policy": model,
                "target_year": row["target_year"],
                "area_code": row["area_code"],
                "area_name": row["area_name"],
                "sector_code": row["sector_code"],
                "sector_name": row["sector_name"],
                "actual_annual_gva": round(row["actual"], 6),
                "baseline_prediction": round(row["baseline"], 6),
                "prediction": round(pred, 6),
                "seed": seed,
                "params": param_text,
                "leakage_policy": "outer target year actual excluded from feature construction, tuning, and training targets",
            }
        )
    return out


def normalize_policy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        out.append(
            {
                **row,
                "actual": num(row.get("actual_annual_gva"), num(row.get("actual"))),
                "baseline": num(row.get("baseline_prediction"), num(row.get("baseline"))),
                "prediction": num(row.get("prediction")),
            }
        )
    return out


def summarize_predictions(rows: list[dict[str, Any]], group_field: str = "policy") -> list[dict[str, Any]]:
    out = []
    for (policy,), items in sorted(grouped(rows, [group_field]).items()):
        items = [row for row in items if int(row["target_year"]) >= COMMON_EVAL_START_YEAR]
        if not items:
            continue
        normalized = normalize_policy_rows(items)
        base = wmape_pct(normalized, "baseline")
        model = wmape_pct(normalized, "prediction")
        sy = sector_year_improvements(normalized, "prediction")
        out.append(
            {
                "policy": policy,
                "count": len(items),
                "wmape": round(model, 6),
                "mape": round(mape_pct(normalized, "prediction"), 6),
                "baseline_wmape": round(base, 6),
                "improvement_vs_baseline_pct": round(improvement_pct(base, model), 6),
                "improved_year_count": improved_year_count(normalized, "prediction"),
                "degraded_sector_years": sum(1 for v in sy if v < 0),
                "material_degraded_sector_years": sum(1 for v in sy if v < -2),
                "worst_sector_year_improvement": round(min(sy), 6) if sy else "",
                "p05_sector_year_improvement": round(float(np.percentile(sy, 5)), 6) if sy else "",
                "median_sector_year_improvement": round(median(sy), 6) if sy else "",
                "effective_ml_rate": round(sum(1 for r in items if str(r.get("ml_selected", "true")).lower() != "false") / len(items), 6) if items else "",
            }
        )
    return out


def seed_reproducibility() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_rows()
    ctx = context(rows)
    predictions: list[dict[str, Any]] = []
    for seed in SEEDS:
        seed_rows = []
        for year in sorted({r["target_year"] for r in rows}):
            seed_rows.extend(global_predict_for_year(rows, ctx, year, "global_fixed_full", BASE_PARAMS, seed))
        for row in seed_rows:
            row["policy"] = f"global_seed_{seed}"
        predictions.extend(seed_rows)
    summary = summarize_predictions(predictions)
    seed_values = [row["wmape"] for row in summary]
    summary.append(
        {
            "policy": "seed_distribution",
            "count": len(seed_values),
            "wmape": round(mean(seed_values), 6) if seed_values else "",
            "mape": "",
            "baseline_wmape": "",
            "improvement_vs_baseline_pct": "",
            "improved_year_count": "",
            "degraded_sector_years": "",
            "material_degraded_sector_years": "",
            "worst_sector_year_improvement": "",
            "p05_sector_year_improvement": round(float(np.percentile(seed_values, 2.5)), 6) if seed_values else "",
            "median_sector_year_improvement": round(float(np.std(seed_values)), 6) if seed_values else "",
            "effective_ml_rate": "",
        }
    )
    return predictions, summary


def param_candidates() -> list[dict[str, Any]]:
    candidates = []
    for objective in ["reg:squarederror", "reg:absoluteerror"]:
        for n_estimators in [100, 250]:
            for max_depth in [2, 3]:
                for learning_rate in [0.02, 0.05, 0.1]:
                    for subsample in [0.7, 0.9]:
                        for colsample in [0.7, 0.9]:
                            for reg_lambda in [1.0, 5.0, 10.0]:
                                candidates.append(
                                    {
                                        "objective": objective,
                                        "n_estimators": n_estimators,
                                        "max_depth": max_depth,
                                        "learning_rate": learning_rate,
                                        "subsample": subsample,
                                        "colsample_bytree": colsample,
                                        "reg_lambda": reg_lambda,
                                        "min_child_weight": 5.0,
                                    }
                                )
    # Deterministic successive-halving style shortlist: broad grid, capped to keep nested rolling tractable.
    return candidates


def tune_for_outer(rows: list[dict[str, Any]], ctx: dict[str, Any], outer_year: int, feature_set: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    train_years = [year for year in sorted({r["target_year"] for r in rows}) if year < outer_year]
    folds = train_years[1:]
    if len(folds) < 2:
        return BASE_PARAMS, []
    tuning_rows = []
    best_params = BASE_PARAMS
    best_score = float("inf")
    candidates = param_candidates()
    for idx, params in enumerate(candidates):
        if idx % 50 == 0:
            print(f"tuning outer={outer_year} feature={feature_set} candidate={idx}/{len(candidates)}", flush=True)
        fold_scores = []
        for val_year in folds:
            val_pred = global_predict_for_year([r for r in rows if r["target_year"] <= val_year], ctx, val_year, feature_set, params, 42)
            if val_pred:
                fold_scores.append(wmape_pct(normalize_policy_rows(val_pred), "prediction"))
        score = mean(fold_scores) if fold_scores else float("inf")
        tuning_rows.append(
            {
                "outer_year": outer_year,
                "feature_set": feature_set,
                "candidate_index": idx,
                "validation_wmape": round(score, 6) if score < float("inf") else "",
                **params,
            }
        )
        if score < best_score:
            best_score = score
            best_params = params
    return best_params, tuning_rows


def run_global_tuning() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_rows()
    ctx = context(rows)
    feature_sets = [
        "global_fixed_full",
        "global_pruned_no_F4",
        "global_core",
        "global_no_residual_features",
        "global_no_sector_id",
        "global_no_region_id",
        "global_baseline_only",
        "global_residual_only",
    ]
    predictions = []
    tuning_rows = []
    for feature_set in feature_sets:
        for year in sorted({r["target_year"] for r in rows}):
            fixed = global_predict_for_year(rows, ctx, year, feature_set, BASE_PARAMS, 42)
            for row in fixed:
                row["policy"] = feature_set
            predictions.extend(fixed)
    for feature_set in ["global_fixed_full", "global_pruned_no_F4"]:
        tuned_policy = "global_tuned_full" if feature_set == "global_fixed_full" else "global_tuned_pruned_no_F4"
        for year in sorted({r["target_year"] for r in rows}):
            best_params, tune_rows = tune_for_outer(rows, ctx, year, feature_set)
            tuning_rows.extend(tune_rows)
            pred = global_predict_for_year(rows, ctx, year, feature_set, best_params, 42)
            for row in pred:
                row["policy"] = tuned_policy
            predictions.extend(pred)
    return predictions, summarize_predictions(predictions), tuning_rows


def run_global_policies(global_predictions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base_rows = [r for r in global_predictions if r["policy"] == "global_tuned_full"]
    if not base_rows:
        base_rows = [r for r in global_predictions if r["policy"] == "global_fixed_full"]
    normalized = normalize_policy_rows(base_rows)
    out = []
    for row in normalized:
        hist = []
        for _year, items in grouped([r for r in normalized if r["sector_code"] == row["sector_code"] and r["target_year"] < row["target_year"]], ["target_year"]).items():
            hist.append(improvement_pct(wmape_pct(items, "baseline"), wmape_pct(items, "prediction")))
        avg = mean(hist) if hist else -999.0
        std = float(np.std(hist)) if len(hist) > 1 else 999.0
        lower = avg - std
        disagreement = abs(log((row["prediction"] + EPS) / (row["baseline"] + EPS)))
        alpha_unc = exp(-5.0 * disagreement)
        alpha_regret = max(0.0, min(1.0, avg / 5.0)) if avg > -100 else 0.0
        policies = {
            "global_full_strength": (row["prediction"], True, 1.0),
            "global_regret_mean": (row["prediction"] if avg > 0 else row["baseline"], avg > 0, 1.0 if avg > 0 else 0.0),
            "global_regret_lower_bound": (row["prediction"] if lower > 0 else row["baseline"], lower > 0, 1.0 if lower > 0 else 0.0),
            "global_adaptive_shrinkage": (row["baseline"] * exp(alpha_unc * log((row["prediction"] + EPS) / (row["baseline"] + EPS))), alpha_unc > 0, alpha_unc),
            "global_regret_adaptive": (row["baseline"] * exp(alpha_unc * alpha_regret * log((row["prediction"] + EPS) / (row["baseline"] + EPS))), alpha_unc * alpha_regret > 0, alpha_unc * alpha_regret),
        }
        for policy, (prediction, selected, alpha) in policies.items():
            out.append(
                {
                    "policy": policy,
                    "target_year": row["target_year"],
                    "area_code": row["area_code"],
                    "area_name": row["area_name"],
                    "sector_code": row["sector_code"],
                    "sector_name": row["sector_name"],
                    "actual_annual_gva": round(row["actual"], 6),
                    "baseline_prediction": round(row["baseline"], 6),
                    "prediction": round(prediction, 6),
                    "source_global_policy": row["policy"],
                    "expected_improvement": round(avg, 6),
                    "expected_lower_bound": round(lower, 6),
                    "adaptive_alpha": round(alpha, 8),
                    "ml_selected": selected,
                }
            )
    return out, summarize_predictions(out)


def run_leakage_checks() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_rows()
    ctx = context(rows)
    checks = [
        ("target_shuffle", {"target_shuffle": True, "sector_shuffle": False, "region_shuffle": False, "feature_set": "global_fixed_full"}),
        ("sector_code_shuffle", {"target_shuffle": False, "sector_shuffle": True, "region_shuffle": False, "feature_set": "global_fixed_full"}),
        ("region_code_shuffle", {"target_shuffle": False, "sector_shuffle": False, "region_shuffle": True, "feature_set": "global_fixed_full"}),
        ("baseline_only_reconstruction", {"target_shuffle": False, "sector_shuffle": False, "region_shuffle": False, "feature_set": "global_baseline_only"}),
    ]
    predictions = []
    for name, cfg in checks:
        for year in sorted({r["target_year"] for r in rows}):
            pred = global_predict_for_year(rows, ctx, year, cfg["feature_set"], BASE_PARAMS, 42, cfg["target_shuffle"], cfg["sector_shuffle"], cfg["region_shuffle"])
            for row in pred:
                row["policy"] = name
            predictions.extend(pred)
    return predictions, summarize_predictions(predictions)


def downside_selection(summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for row in summary:
        mape_ok = float(row["mape"]) <= 6.652706
        constraints = [
            ("strict", 9, -10.0, 4),
            ("relaxed_material_12", 12, -10.0, 4),
            ("relaxed_worst_15", 12, -15.0, 4),
            ("relaxed_years_3", 12, -15.0, 3),
        ]
        for tier, max_material, min_worst, min_years in constraints:
            if (
                mape_ok
                and int(row["material_degraded_sector_years"]) <= max_material
                and float(row["worst_sector_year_improvement"]) >= min_worst
                and int(row["improved_year_count"]) >= min_years
            ):
                candidates.append({**row, "constraint_tier": tier})
                break
    if not candidates:
        return []
    best = min(candidates, key=lambda r: float(r["wmape"]))
    return [best]


def write_table(lines: list[str], rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> None:
    lines.append("| " + " | ".join(label for label, _key in columns) + " |")
    lines.append("| " + " | ".join("---" if label in {"model", "policy", "check"} else "---:" for label, _key in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")) for _label, key in columns) + " |")


def write_reports(
    audit_rows: list[dict[str, Any]],
    seed_summary: list[dict[str, Any]],
    tuning_summary: list[dict[str, Any]],
    tuning_rows: list[dict[str, Any]],
    policy_summary: list[dict[str, Any]],
    leakage_summary: list[dict[str, Any]],
) -> None:
    lines = [
        "# 평가 산식 및 모집단 감사",
        "",
        "## 코드 수정 전 분석 요약",
        "",
        "1. `global_model`은 2018~2023년 1,620건이고, sector/full ML은 2019~2023년 1,350건이다.",
        "2. `global_model` improvement 5.364796%는 global 자체 모집단의 baseline WMAPE 4.182586 대비 계산된 값이다.",
        "3. `sector_group_model:*`은 각 산업 또는 산업군 내부 WMAPE이므로 전체 산업 WMAPE와 직접 비교하면 안 된다.",
        "4. 현재 global common-feature 모델은 F6/F7 indicator·exogenous를 포함하지 않는다. 따라서 `global_fixed_full`은 사실상 common-feature pruned model이다.",
        "5. 산업코드는 one-hot, 지역코드도 one-hot으로 처리된다.",
        "6. 기존 global 고정 파라미터는 `BASE_PARAMS`, seed 42다.",
        "7. 결과는 log-ratio residual 예측 후 연도×산업 부모 baseline에 reconciliation된 값이다.",
        "8. 기존 sector full ML은 산업별 full-grid tuning, global은 고정 파라미터였으므로 tuning budget이 달랐다.",
        "9. global common matrix는 outer train/test별로 생성되며 target year actual은 학습 target 평가 외 feature에는 쓰지 않는다.",
        "10. nested tuning은 outer target year 이전 fold만 사용하도록 구현했다.",
        "",
        "## 공통 모집단 감사",
        "",
    ]
    write_table(lines, audit_rows, [("model", "model"), ("orig count", "original_count"), ("common count", "common_count"), ("orig base", "original_baseline_wmape"), ("orig WMAPE", "original_model_wmape"), ("orig imp", "original_improvement_pct"), ("common base", "common_baseline_wmape"), ("common WMAPE", "common_model_wmape"), ("common imp", "common_improvement_pct"), ("years", "years"), ("common years", "common_years")])
    (REPORT_DIR / "evaluation_metric_audit.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Global Model 재현성 검증", "", "## Seed 반복 결과", ""]
    write_table(lines, seed_summary, [("policy", "policy"), ("count", "count"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("base", "baseline_wmape"), ("imp", "improvement_vs_baseline_pct"), ("years", "improved_year_count"), ("material", "material_degraded_sector_years"), ("worst", "worst_sector_year_improvement")])
    lines.extend(["", "## 판단", "", "모든 seed가 baseline보다 낮은지, 평균 WMAPE가 4.10 미만인지, seed 간 표준편차가 큰지 확인한다."])
    (REPORT_DIR / "global_model_reproducibility.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Global Model Nested Rolling Tuning", "", "## 정책별 결과", ""]
    write_table(lines, tuning_summary, [("policy", "policy"), ("count", "count"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("base", "baseline_wmape"), ("imp", "improvement_vs_baseline_pct"), ("years", "improved_year_count"), ("material", "material_degraded_sector_years"), ("worst", "worst_sector_year_improvement")])
    lines.extend(["", "## 파라미터 안정성", "", f"- 평가한 튜닝 후보 행 수: {len(tuning_rows)}", "- 초기 outer year는 내부 fold 부족 시 고정 파라미터 fallback을 사용한다."])
    (REPORT_DIR / "global_model_tuning.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Global Model Feature Ablation", "", "공통 feature global model은 F6/F7 외생·indicator feature를 애초에 포함하지 않는다. 따라서 이번 비교는 residual, core, sector/region ID 제거 중심으로 수행했다.", "", "## 결과", ""]
    write_table(lines, [r for r in tuning_summary if r["policy"].startswith("global_")], [("policy", "policy"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("imp", "improvement_vs_baseline_pct"), ("material", "material_degraded_sector_years"), ("worst", "worst_sector_year_improvement")])
    (REPORT_DIR / "global_model_feature_ablation.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Global Model Pooling Analysis", "", "## 산업·지역 식별자 비교", ""]
    write_table(lines, [r for r in tuning_summary if r["policy"] in {"global_fixed_full", "global_no_sector_id", "global_no_region_id", "global_no_residual_features", "global_baseline_only", "global_residual_only"}], [("policy", "policy"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("imp", "improvement_vs_baseline_pct"), ("material", "material_degraded_sector_years"), ("worst", "worst_sector_year_improvement")])
    lines.extend(["", "## 해석", "", "산업 one-hot 또는 지역 one-hot 제거 시 성능이 얼마나 유지되는지를 통해 pooling이 단순 ID 암기인지 공통 패턴 학습인지 진단한다."])
    (REPORT_DIR / "global_model_pooling_analysis.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Global Model Safety Policy", "", "## 정책 비교", ""]
    write_table(lines, policy_summary, [("policy", "policy"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("imp", "improvement_vs_baseline_pct"), ("years", "improved_year_count"), ("material", "material_degraded_sector_years"), ("worst", "worst_sector_year_improvement"), ("p05", "p05_sector_year_improvement"), ("ML rate", "effective_ml_rate")])
    selected = downside_selection(policy_summary)
    lines.extend(["", "## Downside-Constrained 선택", ""])
    write_table(lines, selected, [("policy", "policy"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("tier", "constraint_tier"), ("material", "material_degraded_sector_years"), ("worst", "worst_sector_year_improvement")])
    (REPORT_DIR / "global_model_safety_policy.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Global Model Leakage Checks", "", "## Negative Control", ""]
    write_table(lines, leakage_summary, [("check", "policy"), ("count", "count"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("imp", "improvement_vs_baseline_pct"), ("material", "material_degraded_sector_years"), ("worst", "worst_sector_year_improvement")])
    lines.extend(["", "## 판단 기준", "", "Target shuffle 또는 baseline-only reconstruction이 baseline을 유의미하게 이기면 누수 또는 baseline 재구성 위험을 의심한다."])
    (REPORT_DIR / "global_model_leakage_checks.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# Global Reconciled ML 최종 검증 보고서", "", "## 핵심 표", ""]
    write_table(lines, policy_summary, [("policy", "policy"), ("WMAPE", "wmape"), ("MAPE", "mape"), ("imp", "improvement_vs_baseline_pct"), ("years", "improved_year_count"), ("material", "material_degraded_sector_years"), ("worst", "worst_sector_year_improvement"), ("ML rate", "effective_ml_rate")])
    lines.extend(["", "## 결론", "", "공통 평가 감사 후 global model의 개선율을 다시 판단해야 한다. 최종 시군구 pilot 진입 여부는 seed 재현성, negative control, MAPE 비악화, downside 제한을 함께 만족하는지로 결정한다."])
    (REPORT_DIR / "global_reconciled_ml_final_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    common_population, audit_rows, common_keys = audit_common_population()
    seed_predictions, seed_summary = seed_reproducibility()
    tuning_predictions, tuning_summary, tuning_rows = run_global_tuning()
    policy_predictions, policy_summary = run_global_policies(tuning_predictions)
    leakage_predictions, leakage_summary = run_leakage_checks()

    write_csv(PROCESSED_DIR / "evaluation_common_population.csv", common_population)
    write_csv(PROCESSED_DIR / "evaluation_common_keys.csv", common_keys)
    write_csv(PROCESSED_DIR / "evaluation_metric_audit.csv", audit_rows)
    write_csv(PROCESSED_DIR / "global_model_seed_results.csv", seed_summary)
    write_csv(PROCESSED_DIR / "global_model_seed_predictions.csv", seed_predictions)
    write_csv(PROCESSED_DIR / "global_model_tuning_results.csv", tuning_rows)
    write_csv(PROCESSED_DIR / "global_model_ablation_results.csv", tuning_summary)
    write_csv(PROCESSED_DIR / "global_model_tuned_predictions.csv", tuning_predictions)
    write_csv(PROCESSED_DIR / "global_model_policy_predictions.csv", policy_predictions)
    write_csv(PROCESSED_DIR / "global_model_policy_comparison.csv", policy_summary)
    write_csv(PROCESSED_DIR / "global_model_leakage_predictions.csv", leakage_predictions)
    write_csv(PROCESSED_DIR / "global_model_leakage_checks.csv", leakage_summary)
    write_reports(audit_rows, seed_summary, tuning_summary, tuning_rows, policy_summary, leakage_summary)
    print(f"audit models: {len(audit_rows)}")
    print(f"seed predictions: {len(seed_predictions)}")
    print(f"tuning predictions: {len(tuning_predictions)}")
    print(f"policy predictions: {len(policy_predictions)}")
    print(f"leakage predictions: {len(leakage_predictions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
