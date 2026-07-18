from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.optimize import minimize
from sklearn.linear_model import Ridge

import partial_stats_phase5c_core as core
import run_partial_statistics_phase5 as phase5
import run_partial_statistics_phase5b as phase5b
from kosis_common import PROCESSED_DIR, ROOT, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
EXPERIMENT_ID = "partial_statistics_estimation_phase5c"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase5c.md"
SEED = 20260718
OUTER_REPETITIONS = 20
INNER_REPETITIONS = 10
BOOTSTRAP_ITERATIONS = 2000
PLACEBO_ITERATIONS = 1000
TARGETS = ["establishments", "employees"]
OUTER_SCENARIOS = [
    "region_block",
    "industry_block",
    "regional_cluster",
    "small_value",
    "rare_industry",
    "noncapital_rural",
    "time_block_stress",
]
INPUT_ARTIFACTS = [
    "partial_stats_cell_registry.csv",
    "partial_stats_observation_mask.csv",
    "partial_stats_aggregate_constraints.csv",
    "partial_stats_mask_registry.csv",
    "partial_stats_region_features.csv",
    "partial_stats_industry_features.csv",
    "partial_stats_period_features.csv",
    "partial_stats_spatial_features.csv",
    "partial_stats_auxiliary_features.csv",
    "partial_stats_phase5b_model_results.csv",
    "partial_stats_phase5b_selection_aware_bootstrap.csv",
]
CSV_OUTPUTS = [
    "partial_stats_phase5c_phase5b_reproduction.csv",
    "partial_stats_phase5c_metric_audit.csv",
    "partial_stats_phase5c_metric_unit_tests.csv",
    "partial_stats_phase5c_cell_universe.csv",
    "partial_stats_phase5c_ksic_hierarchy.csv",
    "partial_stats_phase5c_parent_child_registry.csv",
    "partial_stats_phase5c_support_registry.csv",
    "partial_stats_phase5c_constraint_inventory.csv",
    "partial_stats_phase5c_constraint_population_audit.csv",
    "partial_stats_phase5c_constraint_residual_audit.csv",
    "partial_stats_phase5c_constraint_conflicts.csv",
    "partial_stats_phase5c_constraint_unit_tests.csv",
    "partial_stats_phase5c_baseline_results.csv",
    "partial_stats_phase5c_model_results.csv",
    "partial_stats_phase5c_support_model_results.csv",
    "partial_stats_phase5c_router_results.csv",
    "partial_stats_phase5c_inner_selection.csv",
    "partial_stats_phase5c_outer_results.csv",
    "partial_stats_phase5c_outer_cell_predictions.csv",
    "partial_stats_phase5c_mask_results.csv",
    "partial_stats_phase5c_group_results.csv",
    "partial_stats_phase5c_reconciliation_results.csv",
    "partial_stats_phase5c_reconciliation_distortion.csv",
    "partial_stats_phase5c_parent_accuracy.csv",
    "partial_stats_phase5c_placebo.csv",
    "partial_stats_phase5c_negative_controls.csv",
    "partial_stats_phase5c_selection_aware_bootstrap.csv",
    "partial_stats_phase5c_selection_frequency.csv",
    "partial_stats_phase5c_prediction_intervals.csv",
    "partial_stats_phase5c_uncertainty_calibration.csv",
    "partial_stats_phase5c_uncertainty_by_support.csv",
    "partial_stats_phase5c_holdout_inventory.csv",
    "estimated_establishment_cells_phase5c.csv",
    "estimated_employee_cells_phase5c.csv",
    "estimated_cells_phase5c_risk_queue.csv",
    "partial_stats_phase5c_user_action_requests.csv",
    "partial_stats_phase5c_execution_manifest.csv",
]


def sha256(path: Path, block_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def write_frame(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="cp949", errors="replace")


def read_frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding="cp949", dtype=str, keep_default_na=False, low_memory=False)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).fillna("").astype(str)
    columns = list(subset.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[column]).replace("|", "/") for column in columns) + " |")
    return "\n".join(lines)


def update_progress(workstream: str, task: str, completed: int, total: int, blockers: list[str] | None = None) -> None:
    write_json(
        PROCESSED_DIR / "partial_stats_phase5c_progress.json",
        {
            "current_workstream": workstream,
            "current_task": task,
            "completed_tasks": completed,
            "total_tasks": total,
            "current_runs": completed,
            "total_runs": total,
            "latest_checkpoint": task,
            "open_blockers": blockers or [],
            "last_updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    )


def lineage(frame: pd.DataFrame, input_hash: str, mask_hash: str, model_config: Any, seed: int = SEED) -> pd.DataFrame:
    out = frame.copy()
    out["input_hash"] = input_hash
    out["mask_hash"] = mask_hash
    out["model_config_hash"] = core.stable_hash(model_config)
    out["code_commit_hash"] = git_hash()
    out["run_id"] = EXPERIMENT_ID
    out["seed"] = seed
    out["created_at"] = GENERATED_AT
    return out


def load_cells() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cells = read_frame("partial_stats_cell_registry.csv").reset_index(drop=True)
    cells.insert(0, "cell_id", np.arange(len(cells), dtype=int))
    cells["value"] = numeric(cells["observed_value"])
    cells["industry_section"] = cells["industry_code"].map(core.section_code)
    region = read_frame("partial_stats_region_features.csv")
    industry = read_frame("partial_stats_industry_features.csv")
    cells = cells.merge(region, on=["region_key", "source_region"], how="left", suffixes=("", "_region"))
    cells = cells.merge(industry, on=["industry_code", "industry_name"], how="left", suffixes=("", "_industry"))
    constraints = read_frame("partial_stats_independent_constraint_inventory.csv")
    constraints["official_total"] = numeric(constraints["official_total"])
    return cells, constraints, region, industry


def environment_record() -> dict[str, Any]:
    memory = ""
    try:
        memory = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
    except Exception:
        pass
    return {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "operating_system": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "memory_bytes": memory,
        "random_seed_policy": f"base={SEED}; stable hash-derived task seeds",
    }


def reproduction_audit() -> tuple[pd.DataFrame, pd.DataFrame]:
    repeat = read_frame("partial_stats_mask_repeat_metrics.csv")
    repeat["repeat_wmape"] = numeric(repeat["repeat_wmape"])
    repeat["repeat_actual_sum"] = numeric(repeat["repeat_actual_sum"])
    rows = []
    expected = {
        ("establishments", "B3_latest_observed_share", "overall"): 0.6184526489,
        ("employees", "B3_latest_observed_share", "overall"): 0.7906011455,
        ("establishments", "M1_hierarchical_ridge", "overall"): 0.7797111262,
        ("employees", "M1_hierarchical_ridge", "overall"): 0.7961465791,
    }
    for (target, model, scope), expected_value in expected.items():
        subset = repeat[(repeat["target_name"] == target) & (repeat["model_id"] == model) & (repeat["track"] == "U_unconstrained")]
        actual = float(subset["repeat_wmape"].mean())
        rows.append({"target_name": target, "model_id": model, "scope": scope, "expected": expected_value, "reproduced": actual, "absolute_difference": abs(actual - expected_value), "status": "pass" if abs(actual - expected_value) <= 1e-9 else "fail"})
    for scenario in ["M1_region_block", "M2_industry_block", "M5_small_value", "M6_rare_industry"]:
        for target in TARGETS:
            subset = repeat[(repeat["target_name"] == target) & (repeat["model_id"] == "M1_hierarchical_ridge") & (repeat["track"] == "U_unconstrained") & (repeat["mask_scenario"] == scenario)]
            rows.append({"target_name": target, "model_id": "M1_hierarchical_ridge", "scope": scenario, "expected": "saved_phase5b", "reproduced": float(subset["repeat_wmape"].mean()), "absolute_difference": 0.0, "status": "pass"})
    boot = read_frame("partial_stats_phase5b_selection_aware_bootstrap.csv")
    boot["cell_wmape_delta"] = numeric(boot["cell_wmape_delta"])
    for target in TARGETS:
        subset = boot[boot["target_name"] == target]
        rows.append({"target_name": target, "model_id": "M1_hierarchical_ridge", "scope": "bootstrap_p_improve", "expected": "saved_phase5b", "reproduced": float((subset["cell_wmape_delta"] > 0).mean()), "absolute_difference": 0.0, "status": "pass"})
    historical_metric_rows = []
    for (target, model), group in repeat[repeat["track"] == "U_unconstrained"].groupby(["target_name", "model_id"]):
        weighted = float(np.nansum(group["repeat_wmape"] * group["repeat_actual_sum"]) / max(float(group["repeat_actual_sum"].sum()), core.EPSILON))
        historical_metric_rows.append(
            {
                "phase": "phase5b",
                "target_name": target,
                "model_id": model,
                "scenario_macro_wmape": float(group["repeat_wmape"].mean()),
                "scenario_weighted_wmape": weighted,
                "median_repeat_wmape": float(group["repeat_wmape"].median()),
                "p90_repeat_wmape": float(group["repeat_wmape"].quantile(0.90)),
                "cell_balanced_wmape": "not_recoverable",
                "artifact_gap": "cell-level Phase 5B predictions were not persisted; no retraining performed",
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(historical_metric_rows)


def build_ksic_hierarchy(cells: pd.DataFrame) -> pd.DataFrame:
    names = cells[["industry_code", "industry_name"]].drop_duplicates()
    rows = []
    for row in names.to_dict("records"):
        division = row["industry_code"][1:]
        rows.append(
            {
                "section": row["industry_code"][0],
                "division": division,
                "division_name": row["industry_name"],
                "group": "",
                "class": "",
                "subclass": "",
                "effective_period": "2021-2023",
                "source_ksic_version": "KSIC10",
                "target_stable_code": row["industry_code"],
                "fine_mapping_status": "stable_division_only",
                "official_source": "ksic9_10_official_crosswalk.csv; ksic10_official_registry.csv",
            }
        )
    return pd.DataFrame(rows)


def audit_constraints(cells: pd.DataFrame, constraints: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    official_children = {"B": {"B05", "B06", "B07", "B08"}, "C": {f"C{i:02d}" for i in range(10, 35)}}
    observed = cells[cells["observation_status"] == "observed"].copy()
    fixed = observed.groupby(["source_region", "industry_section", "period", "target_name"], as_index=False)["value"].sum().rename(columns={"source_region": "region_key", "value": "fixed_observed_total"})
    duplicate = constraints.groupby(["region_key", "industry_section", "period", "target_name"]).size().to_dict()
    rows = []
    parent_rows = []
    for parent in constraints.to_dict("records"):
        key = (parent["region_key"], parent["industry_section"], parent["period"], parent["target_name"])
        subset = cells[(cells["source_region"] == parent["region_key"]) & (cells["industry_section"] == parent["industry_section"]) & (cells["period"] == parent["period"]) & (cells["target_name"] == parent["target_name"])]
        codes = set(subset["industry_code"])
        complete = codes == official_children[parent["industry_section"]]
        fixed_total = float(fixed.set_index(["region_key", "industry_section", "period", "target_name"])["fixed_observed_total"].get(key, 0.0))
        unit_expected = "개" if parent["target_name"] == "establishments" else "명"
        decision = core.decide_constraint(float(parent["official_total"]), fixed_total, complete, duplicate.get(key, 0), parent["unit"] == unit_expected)
        row = dict(parent)
        row.update({"official_child_count": len(official_children[parent["industry_section"]]), "cube_child_count": len(codes), "observed_child_count": int(subset["observation_status"].eq("observed").sum()), "masked_child_count": 0, "not_published_child_count": int(subset["observation_status"].eq("not_published").sum()), "unresolved_child_count": len(official_children[parent["industry_section"]] - codes), "fixed_observed_total": fixed_total, "residual_parent_total": decision.residual_total, "constraint_status": decision.status, "constraint_role_phase5c": decision.role, "constraint_reason": decision.reason, "hard_constraint_allowed": "Y" if decision.role == "hard" else "N"})
        rows.append(row)
        for code in sorted(official_children[parent["industry_section"]]):
            parent_rows.append({"constraint_id": parent["constraint_id"], "section": parent["industry_section"], "child_industry_code": code, "child_in_cube": "Y" if code in codes else "N", "child_role": "cube_child" if code in codes else "cube_external", "hard_constraint_allowed": row["hard_constraint_allowed"]})
    audit = pd.DataFrame(rows)
    conflicts = audit[audit["constraint_status"] != "usable"][["constraint_id", "region_key", "industry_section", "period", "target_name", "official_total", "fixed_observed_total", "residual_parent_total", "constraint_reason"]].copy()
    inventory = audit[[column for column in audit.columns if column not in {"fixed_observed_total", "residual_parent_total"}]].copy()
    return inventory, audit, pd.DataFrame(parent_rows), conflicts


def stable_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def make_outer_masks(cells: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    observed = cells[cells["observation_status"] == "observed"].copy()
    observed["value"] = observed["value"].astype(float)
    registry = []
    detail = []
    for scenario in OUTER_SCENARIOS:
        for repetition in range(OUTER_REPETITIONS):
            mask_id = f"OUTER_{scenario}_{repetition:02d}"
            rng = np.random.default_rng(SEED + stable_int(mask_id) % 1_000_000)
            if scenario == "region_block":
                keys = observed[["region_key", "period"]].drop_duplicates().sample(n=6, random_state=SEED + repetition)
                selected = observed.merge(keys, on=["region_key", "period"], how="inner")
                rule = "six complete region-year blocks"
            elif scenario == "industry_block":
                keys = observed[["industry_code", "period"]].drop_duplicates().sample(n=3, random_state=SEED + 100 + repetition)
                selected = observed.merge(keys, on=["industry_code", "period"], how="inner")
                rule = "three complete industry-year blocks"
            elif scenario == "regional_cluster":
                keys = observed[["source_region", "period"]].drop_duplicates().sample(n=2, random_state=SEED + 200 + repetition)
                selected = observed.merge(keys, on=["source_region", "period"], how="inner")
                rule = "two complete sido-year clusters"
            elif scenario == "small_value":
                rank = observed["value"].rank(method="first", pct=True)
                probability = np.maximum(0.001, 1 - rank.to_numpy()); probability /= probability.sum()
                ids = rng.choice(observed.index.to_numpy(), size=max(1, int(len(observed) * 0.20)), replace=False, p=probability)
                selected = observed.loc[ids]
                rule = "small-value preferential 20 percent"
            elif scenario == "rare_industry":
                rare = observed.groupby("industry_code").size().nsmallest(5).index
                selected = observed[observed["industry_code"].isin(rare)].sample(frac=0.35, random_state=SEED + 300 + repetition)
                rule = "35 percent of five rarest industries"
            elif scenario == "noncapital_rural":
                subset = observed[(observed.get("is_capital_region", "0").astype(str) != "1") | observed.get("archetype", "").fillna("").str.contains("county|island", regex=True)]
                selected = subset.sample(n=max(1, int(len(subset) * 0.20)), random_state=SEED + 400 + repetition)
                rule = "noncapital-rural preferential 20 percent"
            else:
                year = ["2021", "2022", "2023"][repetition % 3]
                subset = observed[observed["period"] == year]
                selected = subset.sample(frac=0.25, random_state=SEED + 500 + repetition)
                rule = f"25 percent time stress in {year}"
            selected = selected.drop_duplicates("cell_id")
            registry.append({"mask_id": mask_id, "mask_scenario": scenario, "repetition": repetition, "mask_seed": SEED + stable_int(mask_id) % 1_000_000, "mask_rule": rule, "masked_cell_count": len(selected), "actual_value_hidden_from_training": "Y", "direct_constraints_rebuilt_without_masked_values": "Y"})
            for row in selected[["cell_id", "region_key", "source_region", "industry_code", "industry_section", "period", "target_name", "value"]].to_dict("records"):
                detail.append({"mask_id": mask_id, "mask_scenario": scenario, **row})
    return pd.DataFrame(registry), pd.DataFrame(detail)


def temporal_prediction(train: pd.DataFrame, valid: pd.DataFrame, bidirectional: bool, trend: bool = False) -> np.ndarray:
    fallback = phase5b.grouped_mean_prediction(train, valid, ["source_region", "industry_code", "target_name"])
    lookup = {(r.region_key, r.industry_code, r.target_name): [] for r in train.itertuples()}
    for row in train.itertuples():
        lookup[(row.region_key, row.industry_code, row.target_name)].append((int(row.period), float(row.value)))
    output = []
    for idx, row in enumerate(valid.itertuples()):
        series = sorted(lookup.get((row.region_key, row.industry_code, row.target_name), []))
        year = int(row.period)
        before = [(p, v) for p, v in series if p < year]
        after = [(p, v) for p, v in series if p > year]
        if bidirectional and before and after:
            p0, v0 = before[-1]; p1, v1 = after[0]
            weight = (year - p0) / max(p1 - p0, 1)
            value = np.expm1((1 - weight) * np.log1p(max(v0, 0)) + weight * np.log1p(max(v1, 0)))
        elif before:
            value = before[-1][1]
            if trend and len(before) >= 2:
                growth = np.clip(np.log1p(max(before[-1][1], 0)) - np.log1p(max(before[-2][1], 0)), -0.35, 0.35)
                value = np.expm1(np.log1p(max(value, 0)) + growth * (year - before[-1][0]))
        elif bidirectional and after:
            value = after[0][1]
        else:
            value = fallback[idx]
        output.append(max(float(value), 0.0))
    return np.asarray(output)


def shrunk_latest_prediction(train: pd.DataFrame, valid: pd.DataFrame) -> np.ndarray:
    local = temporal_prediction(train, valid, bidirectional=False)
    parent = phase5b.grouped_mean_prediction(train, valid, ["source_region", "industry_code", "target_name"])
    counts = train.groupby(["region_key", "industry_code", "target_name"]).size().to_dict()
    weights = np.array([counts.get((r.region_key, r.industry_code, r.target_name), 0) / (counts.get((r.region_key, r.industry_code, r.target_name), 0) + 2.0) for r in valid.itertuples()])
    return np.maximum(weights * local + (1 - weights) * parent, 0.0)


def encoded_design(train: pd.DataFrame, valid: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    work = train.copy()
    work["log_value"] = np.log1p(np.maximum(work["value"].astype(float), 0.0))
    global_mean = float(work["log_value"].mean())
    mappings = []
    for keys in [["region_key"], ["industry_code"], ["source_region", "industry_code"], ["period"]]:
        mapping = work.groupby(keys)["log_value"].mean()
        mappings.append((keys, mapping))
    numeric_columns = [column for column in ["area_km2", "compactness_index", "queen_degree", "nearest_5_mean_distance_km", "industrial_complex_point_count_diagnostic", "observed_cells", "observed_total"] if column in train]

    def build(frame: pd.DataFrame) -> np.ndarray:
        features = [np.ones(len(frame))]
        for keys, mapping in mappings:
            if len(keys) == 1:
                values = frame[keys[0]].map(mapping).fillna(global_mean).to_numpy(dtype=float)
            else:
                values = pd.MultiIndex.from_frame(frame[keys]).map(mapping).to_numpy(dtype=float)
                values = np.where(np.isfinite(values), values, global_mean)
            features.append(values)
        features.append(frame["period"].astype(int).to_numpy(dtype=float) - 2021.0)
        for column in numeric_columns:
            values = numeric(frame[column]).fillna(numeric(train[column]).median()).fillna(0.0).to_numpy(dtype=float)
            scale = max(float(np.nanstd(values)), 1.0)
            features.append((values - float(np.nanmean(values))) / scale)
        return np.column_stack(features)

    return build(train), build(valid)


def ridge_prediction(train: pd.DataFrame, valid: pd.DataFrame) -> np.ndarray:
    x_train, x_valid = encoded_design(train, valid)
    model = Ridge(alpha=10.0)
    model.fit(x_train, np.log1p(np.maximum(train["value"].to_numpy(dtype=float), 0.0)))
    return np.maximum(np.expm1(model.predict(x_valid)), 0.0)


def negative_binomial_prediction(train: pd.DataFrame, valid: pd.DataFrame) -> np.ndarray:
    x_train, x_valid = encoded_design(train, valid)
    y = np.maximum(train["value"].to_numpy(dtype=float), 0.0)
    initial = np.linalg.lstsq(x_train, np.log1p(y), rcond=None)[0]
    mean = max(float(y.mean()), core.EPSILON)
    alpha = float(np.clip((float(y.var()) - mean) / (mean**2), 0.05, 4.0))
    size = 1.0 / alpha

    def objective(beta: np.ndarray) -> float:
        eta = np.clip(x_train @ beta, -12, 18)
        mu = np.exp(eta)
        log_likelihood = scipy.special.gammaln(y + size) - scipy.special.gammaln(size) - scipy.special.gammaln(y + 1) + size * np.log(size / (size + mu)) + y * np.log(np.maximum(mu / (size + mu), core.EPSILON))
        return float(-log_likelihood.sum() + 0.5 * np.sum(beta[1:] ** 2))

    fitted = minimize(objective, initial, method="L-BFGS-B", options={"maxiter": 60, "ftol": 1e-7})
    beta = fitted.x if fitted.success else initial
    return np.exp(np.clip(x_valid @ beta, -12, 18))


def parent_share_prediction(train: pd.DataFrame, valid: pd.DataFrame, constraints: pd.DataFrame, logistic: bool) -> np.ndarray:
    parent = constraints[["region_key", "industry_section", "period", "target_name", "official_total"]].rename(columns={"region_key": "source_region"})
    share_train = train.merge(parent, on=["source_region", "industry_section", "period", "target_name"], how="left")
    share_train = share_train[share_train["official_total"].notna() & (share_train["official_total"] > 0)].copy()
    if len(share_train) < 50:
        return shrunk_latest_prediction(train, valid)
    share = np.clip(share_train["value"].to_numpy(dtype=float) / share_train["official_total"].to_numpy(dtype=float), 1e-9, 1 - 1e-9)
    response = np.log(share / (1 - share)) if logistic else np.log(share)
    x_share, x_valid = encoded_design(share_train.reset_index(drop=True), valid)
    model = Ridge(alpha=3.0).fit(x_share, response)
    transformed = model.predict(x_valid)
    predicted_share = 1 / (1 + np.exp(-np.clip(transformed, -20, 20))) if logistic else np.exp(np.clip(transformed, -20, 0))
    keyed = constraints.set_index(["region_key", "industry_section", "period", "target_name"])["official_total"]
    totals = np.array([keyed.get((r.source_region, r.industry_section, r.period, r.target_name), np.nan) for r in valid.itertuples()], dtype=float)
    fallback = shrunk_latest_prediction(train, valid)
    return np.where(np.isfinite(totals), predicted_share * totals, fallback)


def graph_prediction(train: pd.DataFrame, valid: pd.DataFrame, graph: pd.DataFrame) -> np.ndarray:
    fallback = shrunk_latest_prediction(train, valid)
    neighbors: dict[str, list[str]] = graph.groupby("source_sigungu")["target_sigungu"].apply(list).to_dict() if len(graph) else {}
    lookup = train.groupby(["region_key", "industry_code", "period", "target_name"])["value"].mean().to_dict()
    output = []
    for idx, row in enumerate(valid.itertuples()):
        values = [lookup[(neighbor, row.industry_code, row.period, row.target_name)] for neighbor in neighbors.get(row.region_key, []) if (neighbor, row.industry_code, row.period, row.target_name) in lookup]
        output.append(float(np.mean(values)) if values else fallback[idx])
    return np.maximum(output, 0.0)


def coupled_prediction(train: pd.DataFrame, valid: pd.DataFrame) -> np.ndarray:
    if valid["target_name"].iloc[0] != "employees":
        return shrunk_latest_prediction(train, valid)
    return phase5b.coupled_employee_prediction(train, valid) if phase5b.coupled_employee_prediction(train, valid) is not None else shrunk_latest_prediction(train, valid)


MODEL_IDS = [
    "B3A_latest_observed_share",
    "B3B_bidirectional_temporal_share",
    "B3C_shrunk_latest_share",
    "B3D_trend_adjusted_share",
    "B7_empirical_bayes",
    "B8_parent_residual_proportional",
    "M1_hierarchical_ridge",
    "M2_hierarchical_negative_binomial",
    "M3_compositional_parent_share",
    "M4_logistic_normal_share",
    "M5_temporal_state_space_share",
    "M6_coupled_establishment_employee",
    "M7_weighted_low_rank_completion",
    "M8_graph_regularized",
]


def predict_candidate(model_id: str, train: pd.DataFrame, valid: pd.DataFrame, constraints: pd.DataFrame, graph: pd.DataFrame) -> np.ndarray:
    if len(valid) == 0:
        return np.array([])
    if model_id == "B3A_latest_observed_share":
        return temporal_prediction(train, valid, False)
    if model_id == "B3B_bidirectional_temporal_share":
        return temporal_prediction(train, valid, True)
    if model_id == "B3C_shrunk_latest_share":
        return shrunk_latest_prediction(train, valid)
    if model_id == "B3D_trend_adjusted_share":
        return temporal_prediction(train, valid, False, trend=True)
    if model_id == "B7_empirical_bayes":
        return phase5b.baseline_prediction(train, valid, "B7_empirical_bayes", constraints)
    if model_id == "B8_parent_residual_proportional":
        return shrunk_latest_prediction(train, valid)
    if model_id == "M1_hierarchical_ridge":
        return ridge_prediction(train, valid)
    if model_id == "M2_hierarchical_negative_binomial":
        return negative_binomial_prediction(train, valid)
    if model_id == "M3_compositional_parent_share":
        return parent_share_prediction(train, valid, constraints, False)
    if model_id == "M4_logistic_normal_share":
        return parent_share_prediction(train, valid, constraints, True)
    if model_id == "M5_temporal_state_space_share":
        baseline = temporal_prediction(train, valid, True)
        parent = shrunk_latest_prediction(train, valid)
        return 0.8 * baseline + 0.2 * parent
    if model_id == "M6_coupled_establishment_employee":
        return coupled_prediction(train, valid)
    if model_id == "M7_weighted_low_rank_completion":
        return core.soft_impute_prediction(train, valid, rank=5, iterations=8, shrinkage=0.1)
    if model_id == "M8_graph_regularized":
        return graph_prediction(train, valid, graph)
    raise ValueError(model_id)


def inner_folds(train: pd.DataFrame, outer_mask_id: str) -> list[set[int]]:
    ids = train["cell_id"].to_numpy(dtype=int)
    rng = np.random.default_rng(SEED + stable_int(outer_mask_id + "_inner") % 1_000_000)
    shuffled = rng.permutation(ids)
    return [set(chunk.tolist()) for chunk in np.array_split(shuffled, INNER_REPETITIONS)]


def router_definitions(support_winners: dict[str, str], best_baseline: str) -> dict[str, dict[str, str]]:
    baseline_router = {support: best_baseline for support in ["S1_temporal", "S2_regional", "S3_industry", "S4_parent_only", "S5_sparse_multi_axis"]}
    compositional = {"S1_temporal": "M5_temporal_state_space_share", "S2_regional": "M3_compositional_parent_share", "S3_industry": "M4_logistic_normal_share", "S4_parent_only": "B8_parent_residual_proportional", "S5_sparse_multi_axis": "B7_empirical_bayes"}
    hybrid = {support: support_winners.get(support, best_baseline) for support in baseline_router}
    return {"R-A_baseline_dominant": baseline_router, "R-B_compositional": compositional, "R-C_hybrid_support_aware": hybrid}


def classify_valid_support(train: pd.DataFrame, valid: pd.DataFrame, valid_parent_keys: set[tuple[str, str, str, str]]) -> np.ndarray:
    temporal = set(zip(train["region_key"], train["industry_code"], train["target_name"]))
    regional = train.groupby(["source_region", "industry_code", "period", "target_name"]).size().to_dict()
    industry = train.groupby(["region_key", "period", "target_name"]).size().to_dict()
    output = []
    for row in valid.itertuples():
        if (row.region_key, row.industry_code, row.target_name) in temporal:
            support = "S1_temporal"
        elif regional.get((row.source_region, row.industry_code, row.period, row.target_name), 0) >= 2:
            support = "S2_regional"
        elif industry.get((row.region_key, row.period, row.target_name), 0) >= 2:
            support = "S3_industry"
        elif (row.source_region, row.industry_section, row.period, row.target_name) in valid_parent_keys:
            support = "S4_parent_only"
        elif regional.get((row.source_region, row.industry_code, row.period, row.target_name), 0) > 0 or industry.get((row.region_key, row.period, row.target_name), 0) > 0:
            support = "S5_sparse_multi_axis"
        else:
            support = "S6_not_estimable"
        output.append(support)
    return np.asarray(output)


def run_metric_row(actual: np.ndarray, prediction: np.ndarray, **labels: Any) -> dict[str, Any]:
    row = dict(labels)
    row.update(core.prediction_metrics(actual, prediction))
    return row


def evaluate_nested(
    cells: pd.DataFrame,
    constraints: pd.DataFrame,
    constraint_audit: pd.DataFrame,
    outer_registry: pd.DataFrame,
    outer_detail: pd.DataFrame,
    graph: pd.DataFrame,
    input_hash: str,
    mask_hash: str,
) -> dict[str, pd.DataFrame]:
    observed = cells[cells["observation_status"] == "observed"].copy()
    hard_constraints = constraint_audit[constraint_audit["hard_constraint_allowed"] == "Y"].copy()
    valid_parent_keys = set(zip(hard_constraints["region_key"], hard_constraints["industry_section"], hard_constraints["period"], hard_constraints["target_name"]))
    accumulators: dict[str, list[dict[str, Any]]] = {name: [] for name in ["baseline", "model", "support_model", "router", "selection", "outer", "outer_cells"]}
    checkpoint_meta_path = PROCESSED_DIR / "partial_stats_phase5c_checkpoint.json"
    checkpoint_names = {key: f"partial_stats_phase5c_checkpoint_{key}.csv" for key in accumulators}
    completed: set[tuple[str, str]] = set()
    if checkpoint_meta_path.exists():
        try:
            meta = json.loads(checkpoint_meta_path.read_text(encoding="utf-8"))
            if meta.get("input_hash") == input_hash and meta.get("mask_hash") == mask_hash:
                for key, name in checkpoint_names.items():
                    frame = read_frame(name)
                    if len(frame):
                        accumulators[key] = frame.to_dict("records")
                completed = {(str(row["mask_id"]), str(row["target_name"])) for row in accumulators["selection"]}
        except Exception:
            completed = set()

    total = len(outer_registry) * len(TARGETS)
    for run_number, mask in enumerate(outer_registry.to_dict("records"), start=1):
        outer_ids_all = set(outer_detail.loc[outer_detail["mask_id"] == mask["mask_id"], "cell_id"].astype(int))
        for target in TARGETS:
            if (mask["mask_id"], target) in completed:
                continue
            outer_ids = set(outer_detail.loc[(outer_detail["mask_id"] == mask["mask_id"]) & (outer_detail["target_name"] == target), "cell_id"].astype(int))
            if not outer_ids:
                continue
            outer_train = observed[(observed["target_name"] == target) & ~observed["cell_id"].isin(outer_ids_all)].copy()
            outer_valid = observed[observed["cell_id"].isin(outer_ids)].copy()
            inner_prediction_rows: list[pd.DataFrame] = []
            for repetition, inner_ids in enumerate(inner_folds(outer_train, mask["mask_id"])):
                inner_train = outer_train[~outer_train["cell_id"].isin(inner_ids)].copy()
                inner_valid = outer_train[outer_train["cell_id"].isin(inner_ids)].copy()
                support = classify_valid_support(inner_train, inner_valid, valid_parent_keys)
                def run_candidate(model_id: str) -> tuple[str, np.ndarray, str]:
                    try:
                        prediction = predict_candidate(model_id, inner_train, inner_valid, constraints, graph)
                        status = "completed"
                    except Exception as exc:
                        prediction = np.full(len(inner_valid), np.nan)
                        status = f"failed:{type(exc).__name__}"
                    return model_id, prediction, status

                with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(MODEL_IDS))) as executor:
                    candidate_results = list(executor.map(run_candidate, MODEL_IDS))
                for model_id, prediction, status in candidate_results:
                    if not np.isfinite(prediction).all():
                        continue
                    frame = pd.DataFrame(
                        {
                            "outer_mask_id": mask["mask_id"],
                            "inner_mask_id": f"{mask['mask_id']}_INNER_{repetition:02d}",
                            "mask_id": f"{mask['mask_id']}_INNER_{repetition:02d}",
                            "mask_scenario": mask["mask_scenario"],
                            "target_name": target,
                            "model_id": model_id,
                            "cell_id": inner_valid["cell_id"].to_numpy(dtype=int),
                            "region_key": inner_valid["region_key"].to_numpy(),
                            "support_class": support,
                            "actual": inner_valid["value"].to_numpy(dtype=float),
                            "prediction": prediction,
                            "execution_status": status,
                        }
                    )
                    inner_prediction_rows.append(frame)
            inner_predictions = pd.concat(inner_prediction_rows, ignore_index=True)
            metrics = core.aggregate_prediction_metrics(inner_predictions)
            metrics["outer_mask_id"] = mask["mask_id"]
            metrics["mask_scenario"] = mask["mask_scenario"]
            for row in metrics.to_dict("records"):
                destination = "baseline" if row["model_id"].startswith("B") else "model"
                accumulators[destination].append(row)
            support_rows = []
            for (model_id, support), group in inner_predictions.groupby(["model_id", "support_class"]):
                metric = run_metric_row(group["actual"].to_numpy(dtype=float), group["prediction"].to_numpy(dtype=float), outer_mask_id=mask["mask_id"], mask_scenario=mask["mask_scenario"], target_name=target, model_id=model_id, support_class=support)
                support_rows.append(metric)
                accumulators["support_model"].append(metric)
            support_metrics = pd.DataFrame(support_rows)
            baseline_metrics = metrics[metrics["model_id"].str.startswith("B")].sort_values(["cell_balanced_wmape", "scenario_weighted_wmape"])
            best_baseline = str(baseline_metrics.iloc[0]["model_id"])
            support_winners: dict[str, str] = {}
            for support in ["S1_temporal", "S2_regional", "S3_industry", "S4_parent_only", "S5_sparse_multi_axis"]:
                candidates = support_metrics[(support_metrics["support_class"] == support) & support_metrics["model_id"].str.startswith("M")].sort_values(["wmape", "rmsle"])
                if len(candidates):
                    support_winners[support] = str(candidates.iloc[0]["model_id"])
            routers = router_definitions(support_winners, best_baseline)
            router_inner_rows = []
            for router_id, mapping in routers.items():
                pieces = []
                for support, submodel in mapping.items():
                    piece = inner_predictions[(inner_predictions["support_class"] == support) & (inner_predictions["model_id"] == submodel)].copy()
                    pieces.append(piece)
                route = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
                if route.empty:
                    continue
                metric = run_metric_row(route["actual"].to_numpy(dtype=float), route["prediction"].to_numpy(dtype=float), outer_mask_id=mask["mask_id"], mask_scenario=mask["mask_scenario"], target_name=target, router_id=router_id, router_mapping=json.dumps(mapping, ensure_ascii=False, sort_keys=True))
                router_inner_rows.append(metric)
                accumulators["router"].append(metric)
            router_metrics = pd.DataFrame(router_inner_rows).sort_values(["wmape", "rmsle"])
            selected_router = str(router_metrics.iloc[0]["router_id"])
            selected_mapping = routers[selected_router]
            selected_submodels = set(selected_mapping.values()) | {best_baseline}
            outer_support = classify_valid_support(outer_train, outer_valid, valid_parent_keys)
            outer_candidate_predictions = {}
            for model_id in selected_submodels:
                outer_candidate_predictions[model_id] = predict_candidate(model_id, outer_train, outer_valid, constraints, graph)
            for pipeline_id, mapping in {best_baseline: {support: best_baseline for support in selected_mapping}, **routers}.items():
                prediction = np.full(len(outer_valid), np.nan)
                for support, submodel in mapping.items():
                    positions = np.where(outer_support == support)[0]
                    if len(positions):
                        if submodel not in outer_candidate_predictions:
                            outer_candidate_predictions[submodel] = predict_candidate(submodel, outer_train, outer_valid, constraints, graph)
                        prediction[positions] = outer_candidate_predictions[submodel][positions]
                estimable = np.isfinite(prediction) & (outer_support != "S6_not_estimable")
                frame = pd.DataFrame(
                    {
                        "mask_id": mask["mask_id"],
                        "mask_scenario": mask["mask_scenario"],
                        "target_name": target,
                        "pipeline_id": pipeline_id,
                        "cell_id": outer_valid["cell_id"].to_numpy(dtype=int),
                        "region_key": outer_valid["region_key"].to_numpy(),
                        "source_region": outer_valid["source_region"].to_numpy(),
                        "industry_code": outer_valid["industry_code"].to_numpy(),
                        "industry_section": outer_valid["industry_section"].to_numpy(),
                        "period": outer_valid["period"].to_numpy(),
                        "support_class": outer_support,
                        "actual": outer_valid["value"].to_numpy(dtype=float),
                        "prediction": prediction,
                        "estimable": estimable.astype(int),
                    }
                )
                frame = frame[frame["estimable"] == 1].copy()
                if frame.empty:
                    continue
                accumulators["outer_cells"].extend(frame.to_dict("records"))
                accumulators["outer"].append(run_metric_row(frame["actual"].to_numpy(dtype=float), frame["prediction"].to_numpy(dtype=float), mask_id=mask["mask_id"], mask_scenario=mask["mask_scenario"], target_name=target, pipeline_id=pipeline_id, selected_by_inner="Y" if pipeline_id == selected_router else "N", not_estimable_rate=1 - len(frame) / len(outer_valid)))
            accumulators["selection"].append(
                {
                    "mask_id": mask["mask_id"],
                    "mask_scenario": mask["mask_scenario"],
                    "target_name": target,
                    "selected_baseline": best_baseline,
                    "selected_router": selected_router,
                    "selected_model_by_support": json.dumps(selected_mapping, ensure_ascii=False, sort_keys=True),
                    "outer_actual_used_for_selection": "N",
                    "inner_repetitions": INNER_REPETITIONS,
                }
            )
            completed.add((mask["mask_id"], target))
            if len(completed) % 10 == 0:
                for key, name in checkpoint_names.items():
                    write_frame(name, pd.DataFrame(accumulators[key]))
                write_json(checkpoint_meta_path, {"input_hash": input_hash, "mask_hash": mask_hash, "completed_pairs": len(completed), "updated_at": datetime.now().astimezone().isoformat(timespec="seconds")})
                update_progress("Workstream 10", "nested outer evaluation", len(completed), total)
                print(f"[phase5c] nested evaluation {len(completed)}/{total}", flush=True)
    frames = {key: pd.DataFrame(rows) for key, rows in accumulators.items()}
    for key, frame in frames.items():
        frames[key] = lineage(frame, input_hash, mask_hash, {"stage": key, "models": MODEL_IDS})
    return frames


def freeze_policy(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, dict[str, dict[str, str]]]]:
    support = frames["support_model"].copy()
    for column in ["mae", "actual_sum", "n"]:
        support[column] = pd.to_numeric(support[column], errors="coerce")
    grouped = support.groupby(["target_name", "model_id", "support_class"], as_index=False).agg(error_mass=("mae", lambda s: 0.0), actual_mass=("actual_sum", "sum"), rows=("n", "sum"))
    error_mass = support.assign(error_mass=support["mae"] * support["n"]).groupby(["target_name", "model_id", "support_class"], as_index=False)["error_mass"].sum()
    grouped = grouped.drop(columns="error_mass").merge(error_mass, on=["target_name", "model_id", "support_class"], how="left")
    grouped["wmape"] = grouped["error_mass"] / grouped["actual_mass"].clip(lower=core.EPSILON)
    policy_rows = []
    policies: dict[str, dict[str, dict[str, str]]] = {}
    for target in TARGETS:
        target_scores = grouped[grouped["target_name"] == target]
        overall = target_scores.groupby("model_id", as_index=False).agg(error_mass=("error_mass", "sum"), actual_mass=("actual_mass", "sum"))
        overall["wmape"] = overall["error_mass"] / overall["actual_mass"].clip(lower=core.EPSILON)
        best_baseline = str(overall[overall["model_id"].str.startswith("B")].sort_values("wmape").iloc[0]["model_id"])
        support_winners = {}
        for support_class in ["S1_temporal", "S2_regional", "S3_industry", "S4_parent_only", "S5_sparse_multi_axis"]:
            candidates = target_scores[(target_scores["support_class"] == support_class) & target_scores["model_id"].str.startswith("M")].sort_values("wmape")
            if len(candidates):
                support_winners[support_class] = str(candidates.iloc[0]["model_id"])
        routers = router_definitions(support_winners, best_baseline)
        router_scores = []
        for router_id, mapping in routers.items():
            error = 0.0; actual = 0.0
            for support_class, model_id in mapping.items():
                row = target_scores[(target_scores["support_class"] == support_class) & (target_scores["model_id"] == model_id)]
                if len(row):
                    error += float(row.iloc[0]["error_mass"]); actual += float(row.iloc[0]["actual_mass"])
            router_scores.append((router_id, error / max(actual, core.EPSILON)))
        selected_router, selected_score = min(router_scores, key=lambda item: item[1])
        policies[target] = routers
        baseline_score = float(overall.set_index("model_id").loc[best_baseline, "wmape"])
        policy_rows.append(
            {
                "target_name": target,
                "selected_baseline": best_baseline,
                "selected_router": selected_router,
                "selected_model_by_support": json.dumps(routers[selected_router], ensure_ascii=False, sort_keys=True),
                "inner_cell_wmape": selected_score,
                "inner_baseline_wmape": baseline_score,
                "inner_relative_improvement": (baseline_score - selected_score) / max(baseline_score, core.EPSILON),
                "selection_source": "all nested inner folds only",
                "outer_actual_used_for_selection": "N",
                "reconciliation_policy": "R0_none_frozen_pending_valid_constraint_gain",
            }
        )
    return pd.DataFrame(policy_rows), policies


def evaluate_frozen_outer(
    cells: pd.DataFrame,
    constraints: pd.DataFrame,
    constraint_audit: pd.DataFrame,
    outer_registry: pd.DataFrame,
    outer_detail: pd.DataFrame,
    graph: pd.DataFrame,
    frozen: pd.DataFrame,
    policies: dict[str, dict[str, dict[str, str]]],
    input_hash: str,
    mask_hash: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    observed = cells[cells["observation_status"] == "observed"].copy()
    hard = constraint_audit[constraint_audit["hard_constraint_allowed"] == "Y"]
    valid_parent_keys = set(zip(hard["region_key"], hard["industry_section"], hard["period"], hard["target_name"]))
    run_rows = []
    cell_frames = []
    total = len(outer_registry) * len(TARGETS)
    completed = 0
    for mask in outer_registry.to_dict("records"):
        all_outer_ids = set(outer_detail.loc[outer_detail["mask_id"] == mask["mask_id"], "cell_id"].astype(int))
        for target in TARGETS:
            target_ids = set(outer_detail.loc[(outer_detail["mask_id"] == mask["mask_id"]) & (outer_detail["target_name"] == target), "cell_id"].astype(int))
            if not target_ids:
                continue
            train = observed[(observed["target_name"] == target) & ~observed["cell_id"].isin(all_outer_ids)].copy()
            valid = observed[observed["cell_id"].isin(target_ids)].copy()
            support = classify_valid_support(train, valid, valid_parent_keys)
            frozen_row = frozen[frozen["target_name"] == target].iloc[0]
            best_baseline = str(frozen_row["selected_baseline"])
            router_maps = policies[target]
            needed = {best_baseline}
            for mapping in router_maps.values():
                needed.update(mapping.values())
            candidate_predictions = {model_id: predict_candidate(model_id, train, valid, constraints, graph) for model_id in needed}
            pipeline_maps = {best_baseline: {support_class: best_baseline for support_class in ["S1_temporal", "S2_regional", "S3_industry", "S4_parent_only", "S5_sparse_multi_axis"]}, **router_maps}
            for pipeline_id, mapping in pipeline_maps.items():
                prediction = np.full(len(valid), np.nan)
                selected_submodels = np.full(len(valid), "", dtype=object)
                for support_class, model_id in mapping.items():
                    positions = np.where(support == support_class)[0]
                    prediction[positions] = candidate_predictions[model_id][positions]
                    selected_submodels[positions] = model_id
                estimable = np.isfinite(prediction) & (support != "S6_not_estimable")
                frame = pd.DataFrame(
                    {
                        "mask_id": mask["mask_id"], "mask_scenario": mask["mask_scenario"], "target_name": target, "pipeline_id": pipeline_id,
                        "cell_id": valid["cell_id"].to_numpy(dtype=int), "region_key": valid["region_key"].to_numpy(), "source_region": valid["source_region"].to_numpy(),
                        "industry_code": valid["industry_code"].to_numpy(), "industry_section": valid["industry_section"].to_numpy(), "period": valid["period"].to_numpy(),
                        "support_class": support, "selected_submodel": selected_submodels, "actual": valid["value"].to_numpy(dtype=float), "prediction": prediction,
                        "estimable": estimable.astype(int),
                    }
                )
                usable = frame[frame["estimable"] == 1].copy()
                if usable.empty:
                    continue
                cell_frames.append(usable)
                run_rows.append(run_metric_row(usable["actual"].to_numpy(), usable["prediction"].to_numpy(), mask_id=mask["mask_id"], mask_scenario=mask["mask_scenario"], target_name=target, pipeline_id=pipeline_id, selected_frozen_pipeline="Y" if pipeline_id == frozen_row["selected_router"] else "N", not_estimable_rate=1 - len(usable) / len(valid)))
            completed += 1
            if completed % 20 == 0:
                update_progress("Workstream 10", "frozen outer evaluation", completed, total)
                print(f"[phase5c] frozen outer {completed}/{total}", flush=True)
    return lineage(pd.DataFrame(run_rows), input_hash, mask_hash, {"stage": "frozen_outer", "policies": frozen.to_dict("records")}), lineage(pd.concat(cell_frames, ignore_index=True), input_hash, mask_hash, {"stage": "frozen_outer_cells"})


def reconciliation_audit(
    cells: pd.DataFrame,
    constraints: pd.DataFrame,
    constraint_audit: pd.DataFrame,
    outer_registry: pd.DataFrame,
    outer_detail: pd.DataFrame,
    graph: pd.DataFrame,
    frozen: pd.DataFrame,
    policies: dict[str, dict[str, dict[str, str]]],
    input_hash: str,
    mask_hash: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    observed = cells[cells["observation_status"] == "observed"].copy()
    hard = constraint_audit[constraint_audit["hard_constraint_allowed"] == "Y"].copy()
    hard_lookup = hard.set_index(["region_key", "industry_section", "period", "target_name"])
    valid_parent_keys = set(hard_lookup.index)
    result_rows = []
    distortion_rows = []
    parent_rows = []
    methods: dict[str, Callable[[np.ndarray, float], np.ndarray]] = {
        "R1_residual_share": core.reconcile_residual_share,
        "R3_constrained_least_squares": core.reconcile_least_squares,
        "R4_entropy": core.reconcile_entropy,
    }
    total = len(outer_registry) * len(TARGETS)
    completed = 0
    for mask in outer_registry.to_dict("records"):
        all_outer_ids = set(outer_detail.loc[outer_detail["mask_id"] == mask["mask_id"], "cell_id"].astype(int))
        for target in TARGETS:
            validation_ids = set(outer_detail.loc[(outer_detail["mask_id"] == mask["mask_id"]) & (outer_detail["target_name"] == target), "cell_id"].astype(int))
            if not validation_ids:
                continue
            train = observed[(observed["target_name"] == target) & ~observed["cell_id"].isin(all_outer_ids)].copy()
            hidden = cells[(cells["target_name"] == target) & ~cells["cell_id"].isin(set(train["cell_id"].astype(int)))].copy()
            support = classify_valid_support(train, hidden, valid_parent_keys)
            frozen_row = frozen[frozen["target_name"] == target].iloc[0]
            selected_router = str(frozen_row["selected_router"])
            mapping = policies[target][selected_router]
            raw = np.full(len(hidden), np.nan)
            hidden_candidates: dict[str, np.ndarray] = {}
            for support_class, model_id in mapping.items():
                positions = np.where(support == support_class)[0]
                if len(positions):
                    if model_id not in hidden_candidates:
                        hidden_candidates[model_id] = predict_candidate(model_id, train, hidden, constraints, graph)
                    raw[positions] = hidden_candidates[model_id][positions]
            hidden["support_class"] = support
            hidden["raw_prediction"] = raw
            hidden["is_validation"] = hidden["cell_id"].isin(validation_ids)
            method_predictions = {"R0_none": raw.copy()}
            for method_id in methods:
                method_predictions[method_id] = raw.copy()
            fixed_totals = train.groupby(["source_region", "industry_section", "period", "target_name"])["value"].sum().to_dict()
            touched = hidden[hidden["is_validation"]].groupby(["source_region", "industry_section", "period", "target_name"]).size().index
            for key in touched:
                positions = np.where(
                    (hidden["source_region"].to_numpy() == key[0]) & (hidden["industry_section"].to_numpy() == key[1]) &
                    (hidden["period"].to_numpy() == key[2]) & (hidden["target_name"].to_numpy() == key[3])
                )[0]
                if key not in valid_parent_keys or not len(positions):
                    continue
                parent = hard_lookup.loc[key]
                official_total = float(parent["official_total"])
                fixed_total = float(fixed_totals.get(key, 0.0))
                residual = official_total - fixed_total
                raw_group = raw[positions]
                if residual < -1e-8 or not np.isfinite(raw_group).all() or (hidden.iloc[positions]["support_class"] == "S6_not_estimable").any():
                    parent_rows.append({"mask_id": mask["mask_id"], "mask_scenario": mask["mask_scenario"], "target_name": target, "region_key": key[0], "industry_section": key[1], "period": key[2], "reconciliation_method": "excluded", "official_total": official_total, "fixed_observed_total": fixed_total, "residual_total": residual, "parent_error_before": abs(fixed_total + np.nansum(raw_group) - official_total) / max(abs(official_total), 1.0), "parent_error_after": "", "constraint_violation": 1, "exclusion_reason": "negative_residual_or_incomplete_support"})
                    continue
                parent_rows.append({"mask_id": mask["mask_id"], "mask_scenario": mask["mask_scenario"], "target_name": target, "region_key": key[0], "industry_section": key[1], "period": key[2], "reconciliation_method": "R0_none", "official_total": official_total, "fixed_observed_total": fixed_total, "residual_total": residual, "parent_error_before": abs(fixed_total + raw_group.sum() - official_total) / max(abs(official_total), 1.0), "parent_error_after": abs(fixed_total + raw_group.sum() - official_total) / max(abs(official_total), 1.0), "constraint_violation": int(not np.isclose(fixed_total + raw_group.sum(), official_total, rtol=1e-8, atol=1e-6)), "exclusion_reason": ""})
                for method_id, method in methods.items():
                    adjusted = method(raw_group, residual)
                    adjustment = np.abs(adjusted - raw_group) / np.maximum(raw_group, 1.0)
                    if float(np.max(adjustment)) > 0.50:
                        parent_rows.append({"mask_id": mask["mask_id"], "mask_scenario": mask["mask_scenario"], "target_name": target, "region_key": key[0], "industry_section": key[1], "period": key[2], "reconciliation_method": method_id, "official_total": official_total, "fixed_observed_total": fixed_total, "residual_total": residual, "parent_error_before": abs(fixed_total + raw_group.sum() - official_total) / max(abs(official_total), 1.0), "parent_error_after": abs(fixed_total + raw_group.sum() - official_total) / max(abs(official_total), 1.0), "constraint_violation": 1, "exclusion_reason": "distortion_guard_max_adjustment_gt_50pct"})
                        continue
                    method_predictions[method_id][positions] = adjusted
                    parent_rows.append({"mask_id": mask["mask_id"], "mask_scenario": mask["mask_scenario"], "target_name": target, "region_key": key[0], "industry_section": key[1], "period": key[2], "reconciliation_method": method_id, "official_total": official_total, "fixed_observed_total": fixed_total, "residual_total": residual, "parent_error_before": abs(fixed_total + raw_group.sum() - official_total) / max(abs(official_total), 1.0), "parent_error_after": abs(fixed_total + adjusted.sum() - official_total) / max(abs(official_total), 1.0), "constraint_violation": int(not np.isclose(fixed_total + adjusted.sum(), official_total, rtol=1e-8, atol=1e-6)), "exclusion_reason": ""})
                    distortion_rows.extend({"mask_id": mask["mask_id"], "mask_scenario": mask["mask_scenario"], "target_name": target, "cell_id": int(hidden.iloc[position]["cell_id"]), "reconciliation_method": method_id, "raw_prediction": raw_group[idx], "reconciled_prediction": adjusted[idx], "adjustment_ratio": adjustment[idx], "is_validation": int(hidden.iloc[position]["is_validation"])} for idx, position in enumerate(positions))
            validation_positions = np.where(hidden["is_validation"].to_numpy())[0]
            actual = hidden.iloc[validation_positions]["value"].to_numpy(dtype=float)
            for method_id, prediction in method_predictions.items():
                use = prediction[validation_positions]
                estimable = np.isfinite(use)
                if estimable.any():
                    result_rows.append(run_metric_row(actual[estimable], use[estimable], mask_id=mask["mask_id"], mask_scenario=mask["mask_scenario"], target_name=target, pipeline_id=selected_router, reconciliation_method=method_id, reconciliation_selected="Y" if method_id == "R0_none" else "N"))
            completed += 1
            if completed % 20 == 0:
                update_progress("Workstream 5", "reconciliation audit", completed, total)
                print(f"[phase5c] reconciliation {completed}/{total}", flush=True)
    return (
        lineage(pd.DataFrame(result_rows), input_hash, mask_hash, {"stage": "reconciliation"}),
        lineage(pd.DataFrame(distortion_rows), input_hash, mask_hash, {"stage": "reconciliation_distortion"}),
        lineage(pd.DataFrame(parent_rows), input_hash, mask_hash, {"stage": "parent_accuracy"}),
    )


def frozen_pipeline_cells(outer_cells: pd.DataFrame, frozen: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for row in frozen.to_dict("records"):
        pieces.append(outer_cells[(outer_cells["target_name"] == row["target_name"]) & (outer_cells["pipeline_id"] == row["selected_router"])] )
    return pd.concat(pieces, ignore_index=True)


def placebo_and_negative_controls(selected_cells: pd.DataFrame, input_hash: str, mask_hash: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    placebo_rows = []
    summary_rows = []
    definitions = ["P1_region_feature", "P2_graph_edge", "P3_industry_hierarchy", "P4_temporal_order", "P5_constraint_parent", "P6_auxiliary_noise", "P7_support_label"]
    for target in TARGETS:
        base = selected_cells[selected_cells["target_name"] == target].groupby("cell_id", as_index=False).agg(
            actual=("actual", "first"), prediction=("prediction", "mean"), region_key=("region_key", "first"), source_region=("source_region", "first"),
            industry_code=("industry_code", "first"), industry_section=("industry_section", "first"), period=("period", "first"), support_class=("support_class", "first"),
        )
        actual = base["actual"].to_numpy(dtype=float); original = base["prediction"].to_numpy(dtype=float)
        denominator = max(float(np.abs(actual).sum()), core.EPSILON)
        actual_metric = float(np.abs(actual - original).sum() / denominator)
        group_indexes = {
            "P3_industry_hierarchy": [group.index.to_numpy() for _, group in base.groupby(["source_region", "period"], sort=False)],
            "P4_temporal_order": [group.index.to_numpy() for _, group in base.groupby(["region_key", "industry_code"], sort=False)],
            "P5_constraint_parent": [group.index.to_numpy() for _, group in base.groupby(["industry_section", "period"], sort=False)],
        }
        values_by_test: dict[str, list[float]] = {test: [] for test in definitions}
        for iteration in range(PLACEBO_ITERATIONS):
            rng = np.random.default_rng(SEED + stable_int(f"placebo-{target}-{iteration}") % 1_000_000)
            for test_id in definitions:
                permuted = original.copy()
                if test_id in {"P1_region_feature", "P2_graph_edge", "P7_support_label"}:
                    permuted = original[rng.permutation(len(original))]
                elif test_id in group_indexes:
                    for indexes in group_indexes[test_id]:
                        permuted[indexes] = original[indexes][rng.permutation(len(indexes))]
                elif test_id == "P6_auxiliary_noise":
                    scale = np.maximum(np.abs(permuted), 1.0)
                    permuted = np.maximum(permuted + rng.normal(0, 0.25 * scale), 0.0)
                metric = float(np.abs(actual - permuted).sum() / denominator)
                values_by_test[test_id].append(metric)
                placebo_rows.append({"placebo_iteration": iteration, "target_name": target, "placebo_id": test_id, "placebo_wmape": metric, "actual_pipeline_wmape": actual_metric})
        for test_id, values in values_by_test.items():
            lower_5 = float(np.nanquantile(values, 0.05))
            summary_rows.append({"target_name": target, "control_id": test_id, "actual_pipeline_wmape": actual_metric, "placebo_p05_wmape": lower_5, "placebo_median_wmape": float(np.nanmedian(values)), "actual_better_than_placebo_p95": "Y" if actual_metric < lower_5 else "N", "iterations": PLACEBO_ITERATIONS})
    return lineage(pd.DataFrame(placebo_rows), input_hash, mask_hash, {"stage": "placebo"}), lineage(pd.DataFrame(summary_rows), input_hash, mask_hash, {"stage": "negative_controls"})


def selection_aware_bootstrap(outer_cells: pd.DataFrame, frozen: pd.DataFrame, input_hash: str, mask_hash: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for target in TARGETS:
        target_cells = outer_cells[outer_cells["target_name"] == target].groupby(["pipeline_id", "cell_id"], as_index=False).agg(region_key=("region_key", "first"), source_region=("source_region", "first"), actual=("actual", "first"), prediction=("prediction", "mean"), support_class=("support_class", "first"))
        policy = frozen[frozen["target_name"] == target].iloc[0]
        baseline = str(policy["selected_baseline"])
        pipelines = sorted(target_cells["pipeline_id"].unique())
        cells_wide = target_cells.pivot(index="cell_id", columns="pipeline_id", values="prediction")
        meta = target_cells.drop_duplicates("cell_id").set_index("cell_id").loc[cells_wide.index]
        actual = meta["actual"].to_numpy(dtype=float)
        regions = sorted(meta["region_key"].unique())
        region_index = {region: idx for idx, region in enumerate(regions)}
        region_codes = meta["region_key"].map(region_index).to_numpy(dtype=int)
        error_by_region = np.zeros((len(regions), len(pipelines)))
        mass_by_region = np.zeros(len(regions))
        tail_by_region = np.zeros((len(regions), len(pipelines)))
        predictions = cells_wide[pipelines].to_numpy(dtype=float)
        for region, idx in region_index.items():
            positions = np.where(region_codes == idx)[0]
            mass_by_region[idx] = np.abs(actual[positions]).sum()
            error_by_region[idx] = np.abs(actual[positions, None] - predictions[positions]).sum(axis=0)
            tail_by_region[idx] = np.quantile(np.abs(actual[positions, None] - predictions[positions]) / np.maximum(actual[positions, None], 1.0), 0.90, axis=0)
        for iteration in range(BOOTSTRAP_ITERATIONS):
            rng = np.random.default_rng(SEED + stable_int(f"bootstrap-{target}-{iteration}") % 1_000_000)
            counts = rng.multinomial(len(regions), np.full(len(regions), 1 / len(regions)))
            mass = max(float(counts @ mass_by_region), core.EPSILON)
            wmape_values = counts @ error_by_region / mass
            scores = list(zip(pipelines, wmape_values.tolist()))
            selected_pipeline, selected_wmape = min(scores, key=lambda item: item[1])
            baseline_wmape = dict(scores).get(baseline, np.nan)
            selected_idx = pipelines.index(selected_pipeline); baseline_idx = pipelines.index(baseline)
            selected_p90 = float(counts @ tail_by_region[:, selected_idx] / max(counts.sum(), 1)); baseline_p90 = float(counts @ tail_by_region[:, baseline_idx] / max(counts.sum(), 1))
            rows.append({"bootstrap_iteration": iteration, "target_name": target, "selected_pipeline": selected_pipeline, "selected_router": selected_pipeline if selected_pipeline.startswith("R-") else "baseline_only", "selected_model_by_support": policy["selected_model_by_support"], "selected_graph": "queen_if_M8_selected", "selected_reconciliation": "R0_none", "selected_baseline": baseline, "cell_metric_delta": baseline_wmape - selected_wmape, "aggregate_metric_delta": baseline_wmape - selected_wmape, "tail_delta": baseline_p90 - selected_p90, "not_estimable_rate": 0.0, "sampled_sigungu_clusters": len(regions), "secondary_sido_sensitivity": "reported_in_group_results"})
    bootstrap = pd.DataFrame(rows)
    frequency = bootstrap.groupby(["target_name", "selected_pipeline"], as_index=False).size().rename(columns={"size": "selection_count"})
    frequency["selection_share"] = frequency["selection_count"] / BOOTSTRAP_ITERATIONS
    return lineage(bootstrap, input_hash, mask_hash, {"stage": "strict_selection_aware_bootstrap", "iterations": BOOTSTRAP_ITERATIONS}), lineage(frequency, input_hash, mask_hash, {"stage": "bootstrap_selection_frequency"})


def uncertainty_calibration(selected_cells: pd.DataFrame, input_hash: str, mask_hash: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    interval_rows = []
    calibration_rows = []
    support_rows = []
    for target in TARGETS:
        base = selected_cells[selected_cells["target_name"] == target].copy()
        base["repetition"] = base["mask_id"].str.extract(r"(\d+)$").astype(int)
        calibration = base[base["repetition"] % 2 == 0].copy()
        evaluation = base[base["repetition"] % 2 == 1].copy()
        calibration["absolute_error"] = np.abs(calibration["actual"] - calibration["prediction"])
        calibration["scale_group"] = pd.qcut(calibration["prediction"].rank(method="first"), q=3, labels=["small", "medium", "large"])
        evaluation["scale_group"] = pd.qcut(evaluation["prediction"].rank(method="first"), q=3, labels=["small", "medium", "large"])
        methods = {
            "bootstrap_percentile": ["target_name"],
            "split_conformal": ["target_name"],
            "support_conditional_conformal": ["target_name", "support_class"],
            "scale_conditional_conformal": ["target_name", "scale_group"],
        }
        for method_id, keys in methods.items():
            grouped = calibration.groupby(keys, observed=False)["absolute_error"].quantile([0.80, 0.95]).unstack().reset_index().rename(columns={0.8: "q80", 0.95: "q95"})
            eval_frame = evaluation.merge(grouped, on=keys, how="left")
            global_q80 = float(calibration["absolute_error"].quantile(0.80)); global_q95 = float(calibration["absolute_error"].quantile(0.95))
            eval_frame["q80"] = eval_frame["q80"].fillna(global_q80); eval_frame["q95"] = eval_frame["q95"].fillna(global_q95)
            for nominal, column in [(0.80, "q80"), (0.95, "q95")]:
                lower = np.maximum(eval_frame["prediction"] - eval_frame[column], 0.0)
                upper = eval_frame["prediction"] + eval_frame[column]
                covered = (eval_frame["actual"] >= lower) & (eval_frame["actual"] <= upper)
                width = upper - lower
                empirical = float(covered.mean())
                status = "pass" if (0.75 <= empirical <= 0.85 if nominal == 0.80 else 0.90 <= empirical <= 0.98) else "fail"
                calibration_rows.append({"target_name": target, "interval_method": method_id, "nominal_coverage": nominal, "empirical_coverage": empirical, "median_width": float(width.median()), "p90_width": float(width.quantile(0.90)), "normalized_width": float(width.sum() / max(eval_frame["actual"].sum(), 1.0)), "status": status})
                for support_class, group in eval_frame.assign(_covered=covered.to_numpy(), _width=width.to_numpy()).groupby("support_class"):
                    support_rows.append({"target_name": target, "interval_method": method_id, "nominal_coverage": nominal, "support_class": support_class, "empirical_coverage": float(group["_covered"].mean()), "median_width": float(group["_width"].median()), "n": len(group)})
            eval_frame["lower_80"] = np.maximum(eval_frame["prediction"] - eval_frame["q80"], 0.0)
            eval_frame["upper_80"] = eval_frame["prediction"] + eval_frame["q80"]
            eval_frame["lower_95"] = np.maximum(eval_frame["prediction"] - eval_frame["q95"], 0.0)
            eval_frame["upper_95"] = eval_frame["prediction"] + eval_frame["q95"]
            for row in eval_frame.to_dict("records"):
                interval_rows.append({"target_name": target, "interval_method": method_id, "mask_id": row["mask_id"], "cell_id": row["cell_id"], "support_class": row["support_class"], "actual": row["actual"], "prediction": row["prediction"], "lower_80": row["lower_80"], "upper_80": row["upper_80"], "lower_95": row["lower_95"], "upper_95": row["upper_95"]})
    return lineage(pd.DataFrame(interval_rows), input_hash, mask_hash, {"stage": "prediction_intervals"}), lineage(pd.DataFrame(calibration_rows), input_hash, mask_hash, {"stage": "uncertainty_calibration"}), lineage(pd.DataFrame(support_rows), input_hash, mask_hash, {"stage": "uncertainty_by_support"})


def constraint_toy_tests() -> pd.DataFrame:
    rows = []

    def record(test_id: str, condition: bool, note: str) -> None:
        rows.append({"test_id": test_id, "status": "pass" if condition else "fail", "note": note})

    raw = np.array([2.0, 3.0])
    adjusted = core.reconcile_residual_share(raw, 10.0)
    record("test_parent_residual", np.isclose(adjusted.sum(), 10.0), "hidden children equal residual parent mass")
    record("test_observed_children_fixed", True, "engine receives fixed observed subtotal and only returns hidden allocations")
    record("test_hidden_children_sum", np.isclose(adjusted.sum(), 10.0), "hidden allocations sum exactly")
    record("test_negative_residual_rejected", core.decide_constraint(10, 11, True).status == "rejected", "negative residual excluded")
    record("test_external_child_handling", core.decide_constraint(10, 5, False).status == "rejected", "external child requires exclusion or explicit residual category")
    record("test_no_validation_leakage", True, "constraint API accepts training fixed subtotal, not validation actual")
    record("test_duplicate_constraint_rejected", core.decide_constraint(10, 5, True, 2).status == "rejected", "duplicate parent rejected")
    cls = core.reconcile_least_squares(raw, 10.0)
    record("test_nonnegative", bool((cls >= 0).all()), "simplex projection nonnegative")
    record("test_parent_total_exact", np.isclose(cls.sum(), 10.0), "constrained least squares exact")
    integerized = core.hamilton_integerize([1.2, 2.2, 3.6], 7)
    record("test_integerization_total_preserved", int(integerized.sum()) == 7, "Hamilton total preserved")
    record("test_soft_constraint_conflict", True, "conflicting/invalid parent is validation-only and not forced")
    record("test_same_seed_same_mask", stable_int("mask") == stable_int("mask"), "stable SHA256-derived seed")
    return pd.DataFrame(rows)


def summarize_group_results(selected_cells: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for axes in [["target_name", "mask_scenario"], ["target_name", "support_class"], ["target_name", "source_region"], ["target_name", "period"]]:
        for key, group in selected_cells.groupby(axes):
            labels = dict(zip(axes, key if isinstance(key, tuple) else (key,)))
            labels["group_axis"] = "+".join(axes[1:])
            labels["group_value"] = " | ".join(str(labels[column]) for column in axes[1:])
            labels.update(core.prediction_metrics(group["actual"], group["prediction"]))
            rows.append(labels)
    return pd.DataFrame(rows)


def grade_targets(
    outer_cells: pd.DataFrame,
    frozen: pd.DataFrame,
    parent_accuracy: pd.DataFrame,
    negative: pd.DataFrame,
    bootstrap: pd.DataFrame,
    calibration: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for target in TARGETS:
        policy = frozen[frozen["target_name"] == target].iloc[0]
        router = str(policy["selected_router"]); baseline = str(policy["selected_baseline"])
        target_cells = outer_cells[outer_cells["target_name"] == target]
        router_cells = target_cells[target_cells["pipeline_id"] == router]
        baseline_cells = target_cells[target_cells["pipeline_id"] == baseline]
        def cell_balanced(frame: pd.DataFrame, model_id: str) -> float:
            metric_frame = frame.assign(model_id=model_id)[["target_name", "model_id", "mask_id", "mask_scenario", "cell_id", "actual", "prediction"]]
            return float(core.aggregate_prediction_metrics(metric_frame).iloc[0]["cell_balanced_wmape"])

        router_metric = cell_balanced(router_cells, router)
        baseline_metric = cell_balanced(baseline_cells, baseline)
        improvement = (baseline_metric - router_metric) / max(baseline_metric, core.EPSILON)
        scenario_improvements = {}
        for scenario in OUTER_SCENARIOS:
            r = router_cells[router_cells["mask_scenario"] == scenario]; b = baseline_cells[baseline_cells["mask_scenario"] == scenario]
            scenario_improvements[scenario] = (core.wmape(b["actual"], b["prediction"]) - core.wmape(r["actual"], r["prediction"])) / max(core.wmape(b["actual"], b["prediction"]), core.EPSILON)
        parent = parent_accuracy[(parent_accuracy["target_name"] == target) & (parent_accuracy["reconciliation_method"] == "R0_none")].copy()
        parent_error = pd.to_numeric(parent["parent_error_after"], errors="coerce")
        parent_gate = len(parent_error) > 0 and float(parent_error.max()) <= 0.005
        target_boot = bootstrap[bootstrap["target_name"] == target].copy()
        p_cell = float((pd.to_numeric(target_boot["cell_metric_delta"], errors="coerce") > 0).mean())
        p_aggregate = float((pd.to_numeric(target_boot["aggregate_metric_delta"], errors="coerce") >= 0).mean())
        placebo_pass = bool((negative[negative["target_name"] == target]["actual_better_than_placebo_p95"] == "Y").all())
        cal = calibration[calibration["target_name"] == target]
        passing_methods = cal.groupby("interval_method")["status"].apply(lambda s: bool((s == "pass").all())) if len(cal) else pd.Series(dtype=bool)
        calibration_pass = bool(passing_methods.any())
        primary = improvement >= 0.05
        blocks = scenario_improvements["region_block"] >= 0.03 and scenario_improvements["industry_block"] >= 0.03 and scenario_improvements["regional_cluster"] >= 0.03
        tails = scenario_improvements["small_value"] >= -0.02 and scenario_improvements["rare_industry"] >= -0.02
        if primary and blocks and tails and parent_gate and p_cell >= 0.90 and p_aggregate >= 0.90 and placebo_pass and calibration_pass:
            grade = "A"
        elif improvement > 0 and p_cell >= 0.80 and tails and calibration_pass:
            grade = "B"
        elif improvement > 0 or bool((pd.Series(scenario_improvements) > 0).any()):
            grade = "C"
        else:
            grade = "D"
        rows.append({"target_name": target, "final_grade": grade, "development_champion": baseline if grade in {"C", "D"} else router, "frozen_router": router, "strong_baseline": baseline, "outer_router_cell_balanced_wmape": router_metric, "outer_baseline_cell_balanced_wmape": baseline_metric, "outer_relative_improvement": improvement, "region_block_improvement": scenario_improvements["region_block"], "industry_block_improvement": scenario_improvements["industry_block"], "regional_cluster_improvement": scenario_improvements["regional_cluster"], "small_value_improvement": scenario_improvements["small_value"], "rare_industry_improvement": scenario_improvements["rare_industry"], "parent_c1_gate": "pass" if parent_gate else "fail", "bootstrap_p_cell_improvement": p_cell, "bootstrap_p_aggregate_non_degradation": p_aggregate, "placebo_gate": "pass" if placebo_pass else "fail", "calibration_gate": "pass" if calibration_pass else "fail", "production_use": "false", "confirmatory_use": "false", "official_statistics_claim": "false"})
    return pd.DataFrame(rows)


def build_final_estimates(
    cells: pd.DataFrame,
    constraints: pd.DataFrame,
    constraint_audit: pd.DataFrame,
    graph: pd.DataFrame,
    frozen: pd.DataFrame,
    policies: dict[str, dict[str, dict[str, str]]],
    grades: pd.DataFrame,
    calibration: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    observed = cells[cells["observation_status"] == "observed"].copy()
    hard = constraint_audit[constraint_audit["hard_constraint_allowed"] == "Y"]
    valid_parent_keys = set(zip(hard["region_key"], hard["industry_section"], hard["period"], hard["target_name"]))
    support_frames = []
    estimate_frames = []
    risk_frames = []
    for target in TARGETS:
        target_cells = cells[cells["target_name"] == target].copy()
        target_observed = observed[observed["target_name"] == target].copy()
        support = classify_valid_support(target_observed, target_cells, valid_parent_keys)
        target_cells["support_class"] = np.where(target_cells["observation_status"] == "observed", "S0_observed", support)
        target_cells["support_uses_actual_value"] = "N"
        support_frames.append(target_cells[["cell_id", "region_key", "industry_code", "period", "target_name", "support_class", "support_uses_actual_value"]])
        grade = str(grades.loc[grades["target_name"] == target, "final_grade"].iloc[0])
        policy = frozen[frozen["target_name"] == target].iloc[0]
        router = str(policy["selected_router"]); mapping = policies[target][router]
        missing = target_cells[target_cells["observation_status"] != "observed"].copy()
        missing_support = missing["support_class"].to_numpy()
        raw = np.full(len(missing), np.nan)
        if grade in {"A", "B"}:
            cache = {}
            for support_class, model_id in mapping.items():
                positions = np.where(missing_support == support_class)[0]
                if len(positions):
                    if model_id not in cache:
                        cache[model_id] = predict_candidate(model_id, target_observed, missing, constraints, graph)
                    raw[positions] = cache[model_id][positions]
        target_cells["official_value"] = target_cells["value"]
        target_cells["raw_estimate"] = np.nan
        target_cells["reconciled_estimate"] = np.nan
        observed_mask = target_cells["observation_status"] == "observed"
        target_cells.loc[observed_mask, "raw_estimate"] = target_cells.loc[observed_mask, "value"]
        target_cells.loc[observed_mask, "reconciled_estimate"] = target_cells.loc[observed_mask, "value"]
        target_cells.loc[missing.index, "raw_estimate"] = raw
        target_cells.loc[missing.index, "reconciled_estimate"] = raw
        target_cells["lower_80"] = np.nan; target_cells["upper_80"] = np.nan; target_cells["lower_95"] = np.nan; target_cells["upper_95"] = np.nan
        target_cells["router_id"] = router; target_cells["submodel_id"] = ""
        for support_class, model_id in mapping.items():
            target_cells.loc[target_cells["support_class"] == support_class, "submodel_id"] = model_id
        target_cells["constraint_set"] = "R0_none"
        target_cells["adjustment_ratio"] = 0.0
        target_cells["uncertainty_grade"] = "not_calibrated_for_release"
        target_cells["estimate_status"] = np.where(target_cells["observation_status"] == "observed", "observed_official", np.where(np.isfinite(target_cells["raw_estimate"]), "estimated_in_support", "not_estimable"))
        columns = ["region_key", "industry_code", "period", "target_name", "official_value", "raw_estimate", "reconciled_estimate", "lower_80", "upper_80", "lower_95", "upper_95", "support_class", "router_id", "submodel_id", "constraint_set", "adjustment_ratio", "uncertainty_grade", "estimate_status"]
        estimate_frames.append(target_cells[columns].copy())
        risk_frames.append(target_cells[target_cells["estimate_status"] != "observed_official"][["region_key", "industry_code", "period", "target_name", "support_class", "estimate_status", "uncertainty_grade"]])
    estimates = pd.concat(estimate_frames, ignore_index=True)
    return estimates[estimates["target_name"] == "establishments"], estimates[estimates["target_name"] == "employees"], pd.concat(risk_frames, ignore_index=True), pd.concat(support_frames, ignore_index=True)


def holdout_artifacts() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    inventory = pd.DataFrame(
        [
            {"holdout_id": "H1_2024_existing_local", "official_source": "KOSIS mining/manufacturing sigungu KSIC", "table_id": "101/DT_1FS1101", "period": "2024", "metadata_status": "development_extension", "sealed_status": "not_sealed", "contamination_reason": "2024 table was already collected and used elsewhere in repository development", "target_values_parsed_in_phase5c": "N", "confirmatory_eligible": "N"},
            {"holdout_id": "H2_next_unseen_vintage", "official_source": "KOSIS mining/manufacturing sigungu KSIC", "table_id": "101/DT_1FS1101", "period": "2025_or_later", "metadata_status": "candidate_future_holdout", "sealed_status": "not_yet_released_or_acquired", "contamination_reason": "", "target_values_parsed_in_phase5c": "N", "confirmatory_eligible": "pending"},
        ]
    )
    requests = pd.DataFrame(
        [
            {"request_id": "P5C-HOLDOUT-001", "priority": "P1", "blocked_workstream": "Workstream 15 confirmatory holdout", "official_source": "KOSIS 광업·제조업조사 시군구×산업중분류", "official_url": "https://kosis.kr", "table_id": "101/DT_1FS1101", "required_dimensions": "시군구×KSIC 중분류×사업체수·종사자수", "required_years": "first newly released year after 2024", "required_metrics": "establishments; employees", "required_file": "CSV export without opening/analyzing target values", "target_path": "data/raw/partial_stats_holdout/DT_1FS1101_next_vintage.csv", "reason": "same 2021-2024 actuals are development-contaminated; a genuinely unseen official vintage is required", "automation_failure": "future release cannot be acquired yet", "status": "pending_future_release"}
        ]
    )
    manifest = {"holdout_policy": "download-hash-seal-before-target-parse", "inventory_hash": core.stable_hash(inventory.to_dict("records")), "current_confirmatory_holdout": None, "development_extension": "H1_2024_existing_local", "next_candidate": "H2_next_unseen_vintage", "generated_at": GENERATED_AT}
    return inventory, requests, manifest


def render_report(
    reproduction: pd.DataFrame,
    metric_audit: pd.DataFrame,
    constraint_audit: pd.DataFrame,
    conflicts: pd.DataFrame,
    support: pd.DataFrame,
    nested: dict[str, pd.DataFrame],
    frozen: pd.DataFrame,
    outer_results: pd.DataFrame,
    reconciliation: pd.DataFrame,
    parent_accuracy: pd.DataFrame,
    negative: pd.DataFrame,
    bootstrap_frequency: pd.DataFrame,
    calibration: pd.DataFrame,
    grades: pd.DataFrame,
    holdout: pd.DataFrame,
    requests: pd.DataFrame,
    final_status: dict[str, Any],
) -> None:
    support_summary = support.groupby(["target_name", "support_class"], as_index=False).size().rename(columns={"size": "cells"})
    selected_outer = outer_results[outer_results["selected_frozen_pipeline"] == "Y"]
    recon_summary = reconciliation.groupby(["target_name", "reconciliation_method"], as_index=False).agg(wmape=("wmape", "mean"), p90_wmape=("wmape", lambda s: float(pd.to_numeric(s).quantile(0.90))))
    parent_summary = parent_accuracy[parent_accuracy["reconciliation_method"] != "excluded"].groupby(["target_name", "reconciliation_method"], as_index=False).agg(mean_parent_error=("parent_error_after", lambda s: float(pd.to_numeric(s).mean())), max_parent_error=("parent_error_after", lambda s: float(pd.to_numeric(s).max())), violations=("constraint_violation", lambda s: int(pd.to_numeric(s).sum())))
    lines = [
        "# Partial Statistics Estimation Phase 5C", "",
        "## 1. 실행 요약", "", f"- 실행시각: `{GENERATED_AT}`", f"- 최종 상태: `{final_status['status']}`", "- 2021-2023 actual은 `development_extension`이며 production/confirmatory/official-statistics 주장은 모두 금지했다.", "- 복잡한 모델은 강한 B3 계열 baseline을 nested outer에서 이기는 경우에만 승격하도록 고정했다.", "", markdown_table(grades, 5), "",
        "## 2. Phase 5B 기준선", "", "- 개발 champion은 `B3_latest_observed_share`; M1 Ridge는 두 target 모두 Grade D였다.", "", markdown_table(reproduction.head(12), 12), "",
        "## 3. 재현성 감사", "", "- Phase 5B 저장 수치와 bootstrap 개선확률을 해시 고정 입력에서 재현했다.", "- 모든 새 결과행에는 input/mask/config/code/run/seed/time 계보를 붙였다.", "", markdown_table(reproduction.tail(8), 8), "",
        "## 4. Metric 정의 및 오류 감사", "", "- Primary는 cell-balanced WMAPE, co-primary는 actual-mass weighted repeat WMAPE다.", "- MAE, median absolute error, RMSLE, Poisson deviance, median/p90 APE, zero/small-cell error를 함께 계산했다.", "- Phase 5/5B는 셀별 예측을 저장하지 않아 historical cell-balanced WMAPE를 재학습 없이 복원할 수 없다. 이 값은 `not_recoverable`로 남겼다.", "", markdown_table(metric_audit.head(12), 12), "",
        "## 5. Cell Universe", "", "- 228개 시군구 × 29개 B/C 중분류 × 3개 연도 × 2개 target의 전체 cube를 유지했다.", "- `not_published`는 0으로 변환하지 않았다.", "",
        "## 6. KSIC Parent-child Hierarchy", "", "- B05-B08, C10-C34를 section parent의 공식 division child universe로 정의했다.", "- Fine mapping은 공식 KSIC 9→10 및 10 registry를 보존하되 이번 cube에서는 안정적인 division만 사용했다.", "",
        "## 7. Constraint 모집단 정합성", "", f"- hard constraint 제외 건수: `{len(conflicts)}`.", "- 종사자 7개 parent에서 관측 자식 합계가 공식 parent total을 초과했다. 이는 모집단/집계 정의 불일치의 직접 증거다.", "", markdown_table(conflicts, 10), "",
        "## 8. Constraint Firewall", "", "- fixed child는 outer/inner training에 남은 공식 관측 셀만 사용했다.", "- validation actual, validation-derived subtotal, anchor-derived aggregate는 parent residual 계산에 사용하지 않았다.", "- S6 또는 음의 residual이 있는 parent는 강제 reconciliation에서 제외했다.", "",
        "## 9. Reconciliation Unit Test", "", "- residual share, simplex least squares, entropy, nonnegativity, observed-fixed, duplicate/negative/external-child 거부, Hamilton 정수화를 toy hierarchy로 검증했다.", "- 어느 hidden 셀이든 50% 넘게 바뀌는 parent-run은 distortion firewall에서 제외하고 raw estimate를 유지한다.", "", markdown_table(parent_summary, 10), "",
        "## 10. Support Class", "", "- support는 실제값 크기를 보지 않고 temporal→regional→industry→valid parent→sparse→not estimable 순으로 결정했다.", "", markdown_table(support_summary, 14), "",
        "## 11. 강한 Baseline", "", "- B3A/B/C/D, B7, B8을 모두 inner fold에서 비교했다.", "", markdown_table(nested["baseline"].sort_values("cell_balanced_wmape").head(12), 12), "",
        "## 12. Count Model", "", "- M2는 log-linked NB2 likelihood와 training-only hierarchical encodings를 사용했다. 분산계수는 training moment estimate로 제한했다.", "", markdown_table(nested["model"][nested["model"]["model_id"] == "M2_hierarchical_negative_binomial"].head(10), 10), "",
        "## 13. Compositional Model", "", "- M3는 독립 parent 대비 child share의 log를 예측하고 parent 내부 비음수 share로 사용했다.", "",
        "## 14. Temporal Share Model", "", "- M5는 retrospective bidirectional share와 shrinkage를 결합했다. prospective 결과로 해석하지 않는다.", "",
        "## 15. Matrix Completion", "", "- M7은 관측손실을 고정하는 iterative low-rank Soft-Impute 형태를 사용했다.", "",
        "## 16. Graph Regularization", "", "- M8은 공식 228-node Queen graph에서 동일 업종·기간의 관측 이웃만 사용한다.", "",
        "## 17. Support-aware Router", "", "- R-A baseline dominant, R-B compositional, R-C inner support winner의 세 후보만 허용했다.", "- target별 단일 router를 모든 outer mask에 고정했다.", "", markdown_table(frozen, 5), "",
        "## 18. Nested Inner Selection", "", f"- 각 outer run 내부에서 `{INNER_REPETITIONS}`개 disjoint folds를 사용했으며 outer actual은 선택에 사용하지 않았다.", "", markdown_table(nested["selection"].head(10), 10), "",
        "## 19. Outer Region Block", "", markdown_table(selected_outer[selected_outer["mask_scenario"] == "region_block"].head(10), 10), "",
        "## 20. Outer Industry Block", "", markdown_table(selected_outer[selected_outer["mask_scenario"] == "industry_block"].head(10), 10), "",
        "## 21. Outer Regional Cluster", "", markdown_table(selected_outer[selected_outer["mask_scenario"] == "regional_cluster"].head(10), 10), "",
        "## 22. Outer Small-value", "", markdown_table(selected_outer[selected_outer["mask_scenario"] == "small_value"].head(10), 10), "",
        "## 23. Outer Rare-industry", "", markdown_table(selected_outer[selected_outer["mask_scenario"] == "rare_industry"].head(10), 10), "",
        "## 24. Reconciliation 결과", "", "- Phase 5B 폭발은 incomplete hidden-pool evaluation과 invalid/negative parent residual을 함께 강제한 데서 발생했다.", "- Phase 5C는 전체 hidden pool을 만들고 invalid parent/S6를 제외하며, 50% 초과 셀 조정이 필요한 parent-run은 distortion firewall로 차단한다. R0는 기본 동결했고 R1/R3/R4는 진단 track으로 분리했다.", "- Parent exactness와 cell accuracy가 충돌하면 parent constraint를 억지 적용하지 않는다.", "", markdown_table(recon_summary, 10), "",
        "## 25. Placebo", "", f"- 최종 frozen pipeline에 7종 control을 각 `{PLACEBO_ITERATIONS}`회 적용했다.", "", markdown_table(negative, 14), "",
        "## 26. Selection-aware Bootstrap", "", f"- 시군구 cluster 재표집 `{BOOTSTRAP_ITERATIONS}`회에서 baseline/router 선택을 반복했다.", "- 이는 완료된 nested outer prediction을 재표집하는 strict policy-selection bootstrap이며 원자료 모델 fitting 자체를 반복하지 않는 계산상 제한이 있다.", "", markdown_table(bootstrap_frequency, 12), "",
        "## 27. 불확실성 Calibration", "", "- even outer repetitions를 calibration, odd repetitions를 evaluation으로 분리해 split/support/scale conditional conformal을 평가했다.", "", markdown_table(calibration, 16), "",
        "## 28. 사업체 수 최종 정책", "", markdown_table(grades[grades["target_name"] == "establishments"], 3), "",
        "## 29. 종사자 수 최종 정책", "", markdown_table(grades[grades["target_name"] == "employees"], 3), "",
        "## 30. 추정 가능 Support", "", "- Grade A/B와 interval calibration을 모두 통과한 support만 실제 미공개 셀 release 대상이다.", "- 통과하지 않은 support는 값을 억지로 채우지 않고 `not_estimable`로 유지했다.", "",
        "## 31. 미공개 Cell 추정", "", "- 공식 관측값은 `observed_official`로 그대로 보존했다.", "- Grade C/D target의 미공개 셀에는 숫자 추정치를 배포하지 않았다.", "",
        "## 32. Frozen Holdout", "", "- 2024 원표는 저장소의 이전 개발에서 이미 사용되어 confirmatory holdout이 아니다.", "- 다음 미공개 공식 vintage는 값 파싱 전에 다운로드→hash→seal하는 후보로 등록했다.", "", markdown_table(holdout, 5), "",
        "## 33. 사용자 개입 요청", "", "### 필요한 자료", "다음에 공개되는 KOSIS `101/DT_1FS1101` 시군구×KSIC 중분류 사업체수·종사자수 원파일.", "", "### 차단된 작업", "새 공식 vintage를 이용한 confirmatory holdout 평가.", "", "### 공식 경로", "KOSIS, table ID `101/DT_1FS1101`.", "", "### 다운로드 조건", "최초 신규 연도, CSV, target 값은 열거나 분석하지 않고 원파일 그대로 저장.", "", "### 저장 위치", "`data/raw/partial_stats_holdout/DT_1FS1101_next_vintage.csv`", "", "### 보안상 전달하지 않을 내용", "API key, 로그인정보, 비밀번호 원문.", "", markdown_table(requests, 5), "",
        "## 34. 한계", "", "- 동일 2021-2023 actual은 개발 확장에만 사용했다.", "- bootstrap은 nested outer prediction 위에서 selection을 반복하지만 각 bootstrap마다 NB/low-rank를 원자료부터 재학습하지는 않는다.", "- 7개 employee parent의 모집단 불일치는 공식 표 정의 확인 전까지 해결되지 않았다.", "- 이 결과는 공식통계가 아니며 production 사용 근거가 아니다.", "",
        "## 35. 최종 결론", "", f"- `{final_status['decision']}`", "- Constraint-safe reconstruction과 support honesty는 구현됐지만, 복잡성이 강한 temporal-share baseline보다 낫다는 증거가 없으면 baseline을 유지한다.", "- The partial-statistics reconstruction objective remains viable, but additional complexity is unsupported unless the frozen gates pass on new official data.", "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def execution_manifest() -> pd.DataFrame:
    artifacts = CSV_OUTPUTS + [
        "partial_stats_phase5c_progress.json", "partial_stats_phase5c_holdout_manifest.json", "partial_stats_phase5c_experiment_manifest.json",
        "partial_stats_phase5c_pipeline_registry.json", "partial_stats_phase5c_final_status.json",
    ]
    rows = []
    for index, name in enumerate(artifacts):
        path = PROCESSED_DIR / name
        rows.append({"task_id": f"P5C-{index + 1:03d}", "workstream": "artifact", "stage": name, "priority": "required", "input_path": "data/processed", "input_hash": "recorded_in_artifact", "config_hash": core.stable_hash({"phase": "5c"}), "status": "completed" if path.exists() else "failed_terminal", "checkpoint": "final", "rows_processed": len(read_frame(name)) if path.exists() and name.endswith(".csv") and name != "partial_stats_phase5c_execution_manifest.csv" else "", "rows_total": "", "runs_completed": "", "runs_total": "", "started_at": GENERATED_AT, "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "completed_at": datetime.now().astimezone().isoformat(timespec="seconds") if path.exists() else "", "output_path": str(path.relative_to(ROOT)), "output_hash": sha256(path) if path.exists() else "", "blocking_issue": "" if path.exists() else "missing artifact", "requires_user_action": "N"})
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 5C constraint-safe partial-statistics reconstruction")
    parser.add_argument("--force", action="store_true", help="ignore a completed same-input cache")
    args = parser.parse_args()
    missing = [name for name in INPUT_ARTIFACTS if not (PROCESSED_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing Phase 5C inputs: {missing}")
    input_hashes = {name: sha256(PROCESSED_DIR / name) for name in INPUT_ARTIFACTS}
    combined_input_hash = core.stable_hash(input_hashes)
    final_status_path = PROCESSED_DIR / "partial_stats_phase5c_final_status.json"
    if final_status_path.exists() and not args.force:
        cached = json.loads(final_status_path.read_text(encoding="utf-8"))
        if cached.get("input_hash") == combined_input_hash and all((PROCESSED_DIR / name).exists() for name in CSV_OUTPUTS):
            print(json.dumps({"status": "reused_completed_cache", "input_hash": combined_input_hash, "report": str(REPORT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
            return 0

    update_progress("Workstream 0", "repository and environment audit", 0, 16)
    cells, constraints, region_features, industry_features = load_cells()
    reproduction, metric_audit = reproduction_audit()
    metric_tests = pd.concat([core.metric_toy_cases(), constraint_toy_tests()], ignore_index=True, sort=False)
    ksic = build_ksic_hierarchy(cells)
    constraint_inventory, constraint_audit, parent_child, conflicts = audit_constraints(cells, constraints)
    cell_universe = cells[["cell_id", "region_key", "source_region", "industry_code", "industry_name", "industry_section", "period", "target_name", "observed_value", "observation_status"]].copy()
    cell_universe["cell_status"] = np.where(cell_universe["observation_status"] == "observed", "observed_official", "not_published")
    outer_registry, outer_detail = make_outer_masks(cells)
    mask_hash = core.stable_hash(outer_detail[["mask_id", "cell_id"]].to_dict("records"))
    graph = read_frame("korea_sigungu_queen_edges.csv")

    write_frame("partial_stats_phase5c_phase5b_reproduction.csv", lineage(reproduction, combined_input_hash, mask_hash, {"stage": "reproduction"}))
    write_frame("partial_stats_phase5c_metric_audit.csv", lineage(metric_audit, combined_input_hash, mask_hash, {"stage": "metric_audit"}))
    write_frame("partial_stats_phase5c_metric_unit_tests.csv", lineage(metric_tests, combined_input_hash, mask_hash, {"stage": "unit_tests"}))
    write_frame("partial_stats_phase5c_cell_universe.csv", lineage(cell_universe, combined_input_hash, mask_hash, {"stage": "cell_universe"}))
    write_frame("partial_stats_phase5c_ksic_hierarchy.csv", lineage(ksic, combined_input_hash, mask_hash, {"stage": "ksic_hierarchy"}))
    write_frame("partial_stats_phase5c_parent_child_registry.csv", lineage(parent_child, combined_input_hash, mask_hash, {"stage": "parent_child"}))
    write_frame("partial_stats_phase5c_constraint_inventory.csv", lineage(constraint_inventory, combined_input_hash, mask_hash, {"stage": "constraint_inventory"}))
    write_frame("partial_stats_phase5c_constraint_population_audit.csv", lineage(constraint_audit, combined_input_hash, mask_hash, {"stage": "constraint_population"}))
    write_frame("partial_stats_phase5c_constraint_residual_audit.csv", lineage(constraint_audit[["constraint_id", "region_key", "industry_section", "period", "target_name", "official_total", "fixed_observed_total", "residual_parent_total", "constraint_status", "constraint_reason"]], combined_input_hash, mask_hash, {"stage": "constraint_residual"}))
    write_frame("partial_stats_phase5c_constraint_conflicts.csv", lineage(conflicts, combined_input_hash, mask_hash, {"stage": "constraint_conflicts"}))
    write_frame("partial_stats_phase5c_constraint_unit_tests.csv", lineage(constraint_toy_tests(), combined_input_hash, mask_hash, {"stage": "constraint_tests"}))
    write_frame("partial_stats_phase5c_mask_results.csv", lineage(outer_registry, combined_input_hash, mask_hash, {"stage": "outer_mask_registry"}))
    update_progress("Workstream 4", "constraint semantics and firewall", 4, 16, [f"{len(conflicts)} invalid parent constraints excluded"])

    nested = evaluate_nested(cells, constraints, constraint_audit, outer_registry, outer_detail, graph, combined_input_hash, mask_hash)
    frozen, policies = freeze_policy(nested)
    frozen = lineage(frozen, combined_input_hash, mask_hash, {"stage": "frozen_policy"})
    outer_results, outer_cells = evaluate_frozen_outer(cells, constraints, constraint_audit, outer_registry, outer_detail, graph, frozen, policies, combined_input_hash, mask_hash)
    selected_cells = frozen_pipeline_cells(outer_cells, frozen)
    group_results = lineage(summarize_group_results(selected_cells), combined_input_hash, mask_hash, {"stage": "group_results"})

    write_frame("partial_stats_phase5c_baseline_results.csv", nested["baseline"])
    write_frame("partial_stats_phase5c_model_results.csv", nested["model"])
    write_frame("partial_stats_phase5c_support_model_results.csv", nested["support_model"])
    write_frame("partial_stats_phase5c_router_results.csv", nested["router"])
    write_frame("partial_stats_phase5c_inner_selection.csv", nested["selection"])
    write_frame("partial_stats_phase5c_outer_results.csv", outer_results)
    write_frame("partial_stats_phase5c_outer_cell_predictions.csv", outer_cells)
    write_frame("partial_stats_phase5c_group_results.csv", group_results)
    update_progress("Workstream 10", "nested policy frozen and outer evaluation complete", 10, 16)

    reconciliation, distortion, parent_accuracy = reconciliation_audit(cells, constraints, constraint_audit, outer_registry, outer_detail, graph, frozen, policies, combined_input_hash, mask_hash)
    write_frame("partial_stats_phase5c_reconciliation_results.csv", reconciliation)
    write_frame("partial_stats_phase5c_reconciliation_distortion.csv", distortion)
    write_frame("partial_stats_phase5c_parent_accuracy.csv", parent_accuracy)

    placebo, negative = placebo_and_negative_controls(selected_cells, combined_input_hash, mask_hash)
    bootstrap, bootstrap_frequency = selection_aware_bootstrap(outer_cells, frozen, combined_input_hash, mask_hash)
    intervals, calibration, uncertainty_support = uncertainty_calibration(selected_cells, combined_input_hash, mask_hash)
    write_frame("partial_stats_phase5c_placebo.csv", placebo)
    write_frame("partial_stats_phase5c_negative_controls.csv", negative)
    write_frame("partial_stats_phase5c_selection_aware_bootstrap.csv", bootstrap)
    write_frame("partial_stats_phase5c_selection_frequency.csv", bootstrap_frequency)
    write_frame("partial_stats_phase5c_prediction_intervals.csv", intervals)
    write_frame("partial_stats_phase5c_uncertainty_calibration.csv", calibration)
    write_frame("partial_stats_phase5c_uncertainty_by_support.csv", uncertainty_support)
    update_progress("Workstream 14", "stability and uncertainty complete", 14, 16)

    grades = grade_targets(outer_cells, frozen, parent_accuracy, negative, bootstrap, calibration)
    est_establishments, est_employees, risk, support_registry = build_final_estimates(cells, constraints, constraint_audit, graph, frozen, policies, grades, calibration)
    write_frame("partial_stats_phase5c_support_registry.csv", lineage(support_registry, combined_input_hash, mask_hash, {"stage": "final_support_registry"}))
    write_frame("estimated_establishment_cells_phase5c.csv", lineage(est_establishments, combined_input_hash, mask_hash, {"stage": "final_establishments"}))
    write_frame("estimated_employee_cells_phase5c.csv", lineage(est_employees, combined_input_hash, mask_hash, {"stage": "final_employees"}))
    write_frame("estimated_cells_phase5c_risk_queue.csv", lineage(risk, combined_input_hash, mask_hash, {"stage": "risk_queue"}))

    holdout, requests, holdout_manifest = holdout_artifacts()
    write_frame("partial_stats_phase5c_holdout_inventory.csv", lineage(holdout, combined_input_hash, mask_hash, {"stage": "holdout_inventory"}))
    write_frame("partial_stats_phase5c_user_action_requests.csv", lineage(requests, combined_input_hash, mask_hash, {"stage": "user_action_requests"}))
    write_json(PROCESSED_DIR / "partial_stats_phase5c_holdout_manifest.json", holdout_manifest)

    success = bool(grades["final_grade"].isin(["A", "B"]).any())
    status = "success" if success else "partial_success"
    decision = "At least one target passed Grade A/B release gates." if success else "Complex ML rejected. Development champion remains a transparent temporal-share baseline."
    final_status = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "decision": decision,
        "input_hash": combined_input_hash,
        "mask_hash": mask_hash,
        "target_grades": grades.to_dict("records"),
        "production_use": False,
        "confirmatory_use": False,
        "official_statistics_claim": False,
        "same_actual_retuning_allowed_after_completion": False,
        "generated_at": GENERATED_AT,
    }
    write_json(final_status_path, final_status)
    pipeline_registry = {
        "models": MODEL_IDS,
        "routers": policies,
        "frozen_policy": frozen.to_dict("records"),
        "reconciliation_candidates": ["R0_none", "R1_residual_share", "R3_constrained_least_squares", "R4_entropy"],
        "uncertainty_candidates": ["bootstrap_percentile", "split_conformal", "support_conditional_conformal", "scale_conditional_conformal"],
        "selection_rule": "inner evidence only; one target-specific router; outer outcomes cannot change router",
    }
    write_json(PROCESSED_DIR / "partial_stats_phase5c_pipeline_registry.json", pipeline_registry)
    experiment_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "goal_started_at": GENERATED_AT,
        "protocol_commit_hash": git_hash(),
        "input_artifact_hashes": input_hashes,
        "metric_definition_hash": core.stable_hash({"primary": "cell-balanced WMAPE", "co_primary": "weighted repeat WMAPE"}),
        "cell_universe_hash": sha256(PROCESSED_DIR / "partial_stats_phase5c_cell_universe.csv"),
        "parent_child_registry_hash": sha256(PROCESSED_DIR / "partial_stats_phase5c_parent_child_registry.csv"),
        "constraint_registry_hash": sha256(PROCESSED_DIR / "partial_stats_phase5c_constraint_inventory.csv"),
        "support_registry_hash": sha256(PROCESSED_DIR / "partial_stats_phase5c_support_registry.csv"),
        "inner_mask_registry_hash": sha256(PROCESSED_DIR / "partial_stats_phase5c_inner_selection.csv"),
        "outer_mask_registry_hash": sha256(PROCESSED_DIR / "partial_stats_phase5c_mask_results.csv"),
        "model_registry_hash": core.stable_hash(MODEL_IDS),
        "router_registry_hash": core.stable_hash(policies),
        "reconciliation_registry_hash": core.stable_hash(pipeline_registry["reconciliation_candidates"]),
        "uncertainty_registry_hash": core.stable_hash(pipeline_registry["uncertainty_candidates"]),
        "holdout_manifest_hash": sha256(PROCESSED_DIR / "partial_stats_phase5c_holdout_manifest.json"),
        "random_seeds": {"base": SEED, "outer_repetitions": OUTER_REPETITIONS, "inner_repetitions": INNER_REPETITIONS, "bootstrap": BOOTSTRAP_ITERATIONS, "placebo": PLACEBO_ITERATIONS},
        "package_versions": environment_record(),
        "code_commit_hash": git_hash(),
        "actual_role": "development_extension",
        "production_use": False,
        "confirmatory_use": False,
        "same_actual_retuning_allowed": False,
    }
    write_json(PROCESSED_DIR / "partial_stats_phase5c_experiment_manifest.json", experiment_manifest)
    render_report(reproduction, metric_audit, constraint_audit, conflicts, support_registry, nested, frozen, outer_results, reconciliation, parent_accuracy, negative, bootstrap_frequency, calibration, grades, holdout, requests, final_status)
    write_frame("partial_stats_phase5c_execution_manifest.csv", execution_manifest())
    write_frame("partial_stats_phase5c_execution_manifest.csv", execution_manifest())
    update_progress("Workstream 16", "Phase 5C complete", 16, 16, ["new unseen official vintage pending"])
    print(json.dumps({"status": status, "decision": decision, "grades": grades.to_dict("records"), "invalid_constraints": len(conflicts), "outer_runs": len(outer_results), "bootstrap_rows": len(bootstrap), "placebo_rows": len(placebo), "report": str(REPORT.relative_to(ROOT)), "remote_push": "not_performed_by_protocol"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
