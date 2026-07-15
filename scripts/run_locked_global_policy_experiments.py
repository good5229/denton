from __future__ import annotations

from collections import defaultdict
from math import exp, log
from statistics import mean, median
from time import perf_counter
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv
from run_global_reconciled_experiments import (
    BASE_PARAMS,
    EPS,
    common_matrix_cached,
    grouped,
    global_predict_for_year,
    improvement_pct,
    normalize_policy_rows,
    summarize_predictions,
    tune_for_outer,
    train_xgb,
    wmape_pct,
    mape_pct,
)
from run_reconciled_model_experiment import MIN_TRAIN_ROWS, context, load_rows, reconcile_group, target_values, xgb


REPORT_DIR = ROOT / "reports"
CONFIG_DIR = ROOT / "config"
PILOT_SECTORS = {"A00", "B00", "C00", "D00", "F00", "G00", "L00", "O00", "P00"}
POSITIVE_PILOT = {"B00", "F00", "G00", "L00", "P00"}
BORDERLINE_PILOT = {"C00", "O00"}
NEGATIVE_CONTROL = {"A00", "D00"}


def num(value: Any, default: float = 0.0) -> float:
    parsed = parse_number(value)
    return default if parsed is None else float(parsed)


def write_locked_configs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    common = [
        "feature_set: current_global_common_features",
        "parent_model: parent_baseline",
        "reconciliation: parent_baseline_hard_reconciliation",
        "xgboost:",
        f"  objective: {BASE_PARAMS['objective']}",
        f"  n_estimators: {BASE_PARAMS['n_estimators']}",
        f"  max_depth: {BASE_PARAMS['max_depth']}",
        f"  learning_rate: {BASE_PARAMS['learning_rate']}",
        f"  subsample: {BASE_PARAMS['subsample']}",
        f"  colsample_bytree: {BASE_PARAMS['colsample_bytree']}",
        f"  reg_lambda: {BASE_PARAMS['reg_lambda']}",
        f"  min_child_weight: {BASE_PARAMS['min_child_weight']}",
        "random_seed: 42",
        "preprocessing:",
        "  baseline_features: log_baseline, baseline_share, log_baseline_share",
        "  history_features: lagged_actual_share, rolling_share, lagged_log_ratio, rolling_log_ratio",
        "  structural_features: release_aware_business_stats",
        "  fixed_effects: region_onehot, sector_onehot, method_onehot",
        "unused_actual_lock: do_not_change_thresholds_after_confirmatory_actual",
    ]
    performance = [
        "policy_name: global_adaptive_shrinkage",
        "role: performance_shadow_estimate",
        "source_model: global_tuned_full_rule_frozen",
        "adaptive_alpha:",
        "  formula: exp(-5.0 * abs(log(global_prediction / baseline_prediction)))",
        "  residual_application: baseline * exp(alpha * log(global_prediction / baseline_prediction))",
        "fallback_rule: never_fallback_by_regret",
    ] + common
    conservative = [
        "policy_name: global_regret_adaptive",
        "role: default_published_estimate",
        "source_model: global_tuned_full_rule_frozen",
        "regret_gate:",
        "  predicted_improvement: mean_pre_target_sector_year_improvement",
        "  alpha_regret: clip(predicted_improvement / 5.0, 0.0, 1.0)",
        "  minimum_history_years: 1",
        "adaptive_alpha:",
        "  formula: exp(-5.0 * abs(log(global_prediction / baseline_prediction))) * alpha_regret",
        "  fallback_rule: alpha_is_zero_when_no_positive_pre_target_improvement",
    ] + common
    (CONFIG_DIR / "global_performance_policy.yaml").write_text("\n".join(performance) + "\n", encoding="utf-8")
    (CONFIG_DIR / "global_conservative_policy.yaml").write_text("\n".join(conservative) + "\n", encoding="utf-8")


def policy_rows_from_global(base_rows: list[dict[str, Any]], policy_year_min: int | None = None) -> list[dict[str, Any]]:
    normalized = normalize_policy_rows(base_rows)
    out: list[dict[str, Any]] = []
    for row in normalized:
        if policy_year_min is not None and int(row["target_year"]) < policy_year_min:
            continue
        hist = []
        for _year, items in grouped(
            [r for r in normalized if r["sector_code"] == row["sector_code"] and r["target_year"] < row["target_year"]],
            ["target_year"],
        ).items():
            hist.append(improvement_pct(wmape_pct(items, "baseline"), wmape_pct(items, "prediction")))
        avg = mean(hist) if hist else -999.0
        disagreement = abs(log((row["prediction"] + EPS) / (row["baseline"] + EPS)))
        alpha_unc = exp(-5.0 * disagreement)
        alpha_regret = max(0.0, min(1.0, avg / 5.0)) if avg > -100 else 0.0
        policies = {
            "baseline": (row["baseline"], False, 0.0),
            "global_full_strength": (row["prediction"], True, 1.0),
            "global_adaptive_shrinkage": (row["baseline"] * exp(alpha_unc * log((row["prediction"] + EPS) / (row["baseline"] + EPS))), True, alpha_unc),
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
                    "expected_improvement": round(avg, 6),
                    "adaptive_alpha": round(alpha, 8),
                    "ml_selected": selected,
                }
            )
    return out


def run_confirmatory() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_rows()
    ctx = context(rows)
    years = [year for year in sorted({r["target_year"] for r in rows}) if year > 2023]
    raw_global: list[dict[str, Any]] = []
    tuning_rows: list[dict[str, Any]] = []
    start = perf_counter()
    for year in years:
        best_params, tune_rows = tune_for_outer(rows, ctx, year, "global_fixed_full")
        tuning_rows.extend(tune_rows)
        pred = global_predict_for_year(rows, ctx, year, "global_fixed_full", best_params, 42)
        for row in pred:
            row["policy"] = "global_tuned_full_locked_rule"
        raw_global.extend(pred)
    policy_rows = policy_rows_from_global(raw_global, policy_year_min=2024)
    summary = summarize_predictions(policy_rows)
    elapsed = round(perf_counter() - start, 3)
    for row in summary:
        row["elapsed_seconds"] = elapsed
        if row["policy"] == "global_regret_adaptive":
            row["confirmatory_role"] = "conservative_locked_policy"
            row["pass_wmape"] = float(row["wmape"]) < float(row["baseline_wmape"])
            row["pass_mape"] = float(row["mape"]) <= baseline_mape(policy_rows)
            row["pass_material_rate"] = (int(row["material_degraded_sector_years"]) / max(1, sector_year_count(policy_rows))) <= 0.15
            row["pass_worst"] = float(row["worst_sector_year_improvement"]) >= -10.0
        elif row["policy"] == "global_adaptive_shrinkage":
            row["confirmatory_role"] = "performance_locked_policy"
            row["pass_wmape_improvement"] = float(row["improvement_vs_baseline_pct"]) >= 3.0
            row["pass_mape"] = float(row["mape"]) <= baseline_mape(policy_rows)
            row["pass_material_rate"] = (int(row["material_degraded_sector_years"]) / max(1, sector_year_count(policy_rows))) <= 0.25
            row["pass_worst"] = float(row["worst_sector_year_improvement"]) >= -25.0
        else:
            row["confirmatory_role"] = "comparison"
    return policy_rows, summary, tuning_rows


def baseline_mape(rows: list[dict[str, Any]]) -> float:
    baseline = [r for r in rows if r["policy"] == "baseline"]
    return mape_pct(normalize_policy_rows(baseline), "prediction")


def sector_year_count(rows: list[dict[str, Any]]) -> int:
    return len({(r["sector_code"], r["target_year"]) for r in rows if r["policy"] == "baseline"})


def material_count(rows: list[dict[str, Any]], field: str = "prediction") -> int:
    values = []
    for _key, items in grouped(normalize_policy_rows(rows), ["sector_code", "target_year"]).items():
        values.append(improvement_pct(wmape_pct(items, "baseline"), wmape_pct(items, field)))
    return sum(1 for value in values if value < -2)


def load_sigungu_rows() -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(PROCESSED_DIR / "sigungu_annual_rolling_backtest.csv"):
        sector = row.get("sector_code", "")
        if sector not in PILOT_SECTORS:
            continue
        actual = num(row.get("actual_annual_gva"))
        baseline = num(row.get("predicted_annual_gva"))
        parent = num(row.get("parent_predicted_annual_gva"))
        if min(actual, baseline, parent) <= 0:
            continue
        rows.append(
            {
                "source_region": row.get("source_region", ""),
                "parent_area_code": row.get("source_region", ""),
                "sigungu_code": row.get("sigungu_code", ""),
                "sigungu_name": row.get("sigungu_name", ""),
                "sector_code": sector,
                "sector_name": row.get("sector_name", ""),
                "target_year": int(row.get("target_year", 0)),
                "actual": actual,
                "baseline": baseline,
                "parent_baseline": parent,
                "last_observed_share": num(row.get("last_observed_share")),
                "share_base_year": int(num(row.get("share_base_year"))),
            }
        )
    return sorted(rows, key=lambda r: (r["target_year"], r["source_region"], r["sector_code"], r["sigungu_code"]))


def sigungu_matrix(rows: list[dict[str, Any]], all_regions: list[str], all_sigungu: list[str], all_sectors: list[str]) -> np.ndarray:
    region_index = {value: idx for idx, value in enumerate(all_regions)}
    sigungu_index = {value: idx for idx, value in enumerate(all_sigungu)}
    sector_index = {value: idx for idx, value in enumerate(all_sectors)}
    by_key = {(r["sigungu_code"], r["sector_code"], r["target_year"]): r for r in rows}
    vectors = []
    for row in rows:
        prev = by_key.get((row["sigungu_code"], row["sector_code"], row["target_year"] - 1))
        prev_ratio = log((prev["actual"] + EPS) / (prev["baseline"] + EPS)) if prev else 0.0
        region_dummy = [0.0] * len(all_regions)
        region_dummy[region_index[row["source_region"]]] = 1.0
        sigungu_dummy = [0.0] * len(all_sigungu)
        sigungu_dummy[sigungu_index[row["sigungu_code"]]] = 1.0
        sector_dummy = [0.0] * len(all_sectors)
        sector_dummy[sector_index[row["sector_code"]]] = 1.0
        base = [
            1.0,
            (row["target_year"] - 2019.0) / 10.0,
            log(row["baseline"] + EPS),
            row["last_observed_share"],
            log(row["last_observed_share"] + EPS),
            prev_ratio,
            row["target_year"] - row["share_base_year"],
        ]
        vectors.append(base + region_dummy + sigungu_dummy + sector_dummy)
    return np.asarray(vectors, dtype=float)


def train_sigungu_global(train_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]], params: dict[str, Any], sector_only: bool = False) -> list[float]:
    if xgb is None or len(train_rows) < MIN_TRAIN_ROWS:
        return [r["baseline"] for r in test_rows]
    if sector_only:
        out = []
        for sector, sector_test in grouped(test_rows, ["sector_code"]).items():
            sector_train = [r for r in train_rows if r["sector_code"] == sector[0]]
            out.extend(zip([id(r) for r in sector_test], train_sigungu_global(sector_train, sector_test, params, sector_only=False)))
        by_id = {item_id: value for item_id, value in out}
        return [by_id[id(r)] for r in test_rows]
    all_regions = sorted({r["source_region"] for r in train_rows + test_rows})
    all_sigungu = sorted({r["sigungu_code"] for r in train_rows + test_rows})
    all_sectors = sorted({r["sector_code"] for r in train_rows + test_rows})
    x_train = sigungu_matrix(train_rows, all_regions, all_sigungu, all_sectors)
    x_test = sigungu_matrix(test_rows, all_regions, all_sigungu, all_sectors)
    y_train = np.asarray([log((r["actual"] + EPS) / (r["baseline"] + EPS)) for r in train_rows], dtype=float)
    raw = train_xgb(x_train, y_train, x_test, params, 42)
    raw_pred = [row["baseline"] * exp(float(value)) for row, value in zip(test_rows, raw)]
    return reconcile_sigungu(test_rows, raw_pred)


def reconcile_sigungu(rows: list[dict[str, Any]], raw_values: list[float]) -> list[float]:
    out = [0.0] * len(rows)
    group_indices: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        group_indices[(row["source_region"], row["sector_code"], row["target_year"])].append(idx)
    for _key, indices in group_indices.items():
        parent = rows[indices[0]]["parent_baseline"]
        total = sum(max(raw_values[idx], 0.0) for idx in indices)
        if total <= 0:
            for idx in indices:
                out[idx] = rows[idx]["baseline"]
            continue
        for idx in indices:
            out[idx] = parent * max(raw_values[idx], 0.0) / total
    return out


def run_sigungu_pilot() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_sigungu_rows()
    predictions = []
    for year in sorted({r["target_year"] for r in rows}):
        train = [r for r in rows if r["target_year"] < year]
        test = [r for r in rows if r["target_year"] == year]
        if len(train) < MIN_TRAIN_ROWS or not test:
            continue
        global_pred = train_sigungu_global(train, test, BASE_PARAMS)
        sector_pred = train_sigungu_global(train, test, BASE_PARAMS, sector_only=True)
        global_rows = make_sigungu_policy_rows(test, global_pred, "global_full_strength")
        sector_rows = make_sigungu_policy_rows(test, sector_pred, "sector_independent_model")
        policies = policy_rows_from_sigungu_global(global_rows)
        predictions.extend(make_sigungu_policy_rows(test, [r["baseline"] for r in test], "baseline"))
        predictions.extend(global_rows)
        predictions.extend(sector_rows)
        predictions.extend(policies)
    summary = summarize_sigungu(predictions)
    sector_summary = summarize_sigungu(predictions, ["sector_code", "sector_name", "policy"])
    crosswalk = build_sigungu_crosswalk(rows)
    return predictions, summary, sector_summary, crosswalk


def make_sigungu_policy_rows(test_rows: list[dict[str, Any]], predictions: list[float], policy: str) -> list[dict[str, Any]]:
    out = []
    for row, pred in zip(test_rows, predictions):
        out.append(
            {
                "policy": policy,
                "source_region": row["source_region"],
                "sigungu_code": row["sigungu_code"],
                "sigungu_name": row["sigungu_name"],
                "sector_code": row["sector_code"],
                "sector_name": row["sector_name"],
                "target_year": row["target_year"],
                "actual_annual_gva": round(row["actual"], 6),
                "baseline_prediction": round(row["baseline"], 6),
                "prediction": round(pred, 6),
                "parent_predicted_annual_gva": round(row["parent_baseline"], 6),
                "ml_selected": policy != "baseline",
            }
        )
    return out


def policy_rows_from_sigungu_global(global_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = normalize_policy_rows(global_rows)
    out = []
    for row in normalized:
        # Pilot-safe local rule: no target-year actual is used; uses baseline/global disagreement only.
        disagreement = abs(log((row["prediction"] + EPS) / (row["baseline"] + EPS)))
        alpha_unc = exp(-5.0 * disagreement)
        alpha_regret = 0.6 if row["sector_code"] in POSITIVE_PILOT | BORDERLINE_PILOT else 0.0
        specs = {
            "global_adaptive_shrinkage": (row["baseline"] * exp(alpha_unc * log((row["prediction"] + EPS) / (row["baseline"] + EPS))), alpha_unc),
            "global_regret_adaptive": (row["baseline"] * exp(alpha_unc * alpha_regret * log((row["prediction"] + EPS) / (row["baseline"] + EPS))), alpha_unc * alpha_regret),
        }
        for policy, (prediction, alpha) in specs.items():
            out.append({**row, "policy": policy, "prediction": round(prediction, 6), "adaptive_alpha": round(alpha, 8), "ml_selected": alpha > 0})
    return out


def summarize_sigungu(rows: list[dict[str, Any]], keys: list[str] | None = None) -> list[dict[str, Any]]:
    keys = keys or ["policy"]
    out = []
    for group_key, items in grouped(rows, keys).items():
        normalized = normalize_policy_rows(items)
        base = wmape_pct(normalized, "baseline")
        model = wmape_pct(normalized, "prediction")
        apes = [abs((r["prediction"] - r["actual"]) / r["actual"]) * 100 for r in normalized if r["actual"]]
        region_wmapes = [wmape_pct(part, "prediction") for _k, part in grouped(normalized, ["sigungu_code"]).items()]
        sector_imps = [
            improvement_pct(wmape_pct(part, "baseline"), wmape_pct(part, "prediction"))
            for _k, part in grouped(normalized, ["sector_code", "target_year"]).items()
        ]
        out.append(
            {
                **{field: value for field, value in zip(keys, group_key)},
                "count": len(items),
                "wmape": round(model, 6),
                "mape": round(mape_pct(normalized, "prediction"), 6),
                "macro_region_wmape": round(mean(region_wmapes), 6) if region_wmapes else "",
                "median_ape": round(median(apes), 6) if apes else "",
                "p90_ape": round(float(np.percentile(apes, 90)), 6) if apes else "",
                "baseline_wmape": round(base, 6),
                "improvement_vs_baseline_pct": round(improvement_pct(base, model), 6),
                "material_degradation_count": sum(1 for value in sector_imps if value < -2),
                "worst_sector_year_improvement": round(min(sector_imps), 6) if sector_imps else "",
                "ml_rate": round(sum(1 for r in items if str(r.get("ml_selected", "")).lower() == "true") / len(items), 6) if items else "",
            }
        )
    return out


def build_sigungu_crosswalk(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for (code, name), items in grouped(rows, ["sigungu_code", "sigungu_name"]).items():
        years = sorted({r["target_year"] for r in items})
        out.append(
            {
                "original_region_code": code,
                "original_region_name": name,
                "harmonized_region_code": code,
                "harmonized_region_name": name,
                "valid_from": min(years),
                "valid_to": max(years),
                "crosswalk_weight": 1.0,
                "crosswalk_reason": "stable code-name pair in available pilot data; no split/merge adjustment applied",
            }
        )
    return out


def write_reports(
    confirm_summary: list[dict[str, Any]],
    sigungu_summary: list[dict[str, Any]],
    sigungu_sector_summary: list[dict[str, Any]],
) -> None:
    analysis = [
        "# Locked Global Policy 차기 실험 분석",
        "",
        "## 코드 수정 전 분석",
        "",
        "1. `global_adaptive_shrinkage`: global common-feature log-ratio residual 예측값에 `alpha = exp(-5 * |log(global/baseline)|)`를 적용한다.",
        "2. `global_regret_adaptive`: 산업별 pre-target 개선율 평균을 regret proxy로 두고 `alpha_regret = clip(avg_improvement / 5, 0, 1)`을 곱한다.",
        "3. target year별 흐름: baseline 생성 → global residual 예측 → 부모 총량 reconciliation → alpha/gate 적용 → 정책별 산출.",
        "4. material degradation: 산업×연도 WMAPE 개선율이 -2% 미만이면 1건으로 센다.",
        "5. 동결 설정: feature set, XGBoost grid/seed, alpha 산식, regret threshold, parent baseline, reconciliation rule.",
        "6. 시군구 actual은 현재 pilot 데이터 기준 2020~2023, 시도 parent annual actual은 2019~2023 범위다.",
        "7. crosswalk는 stable code-name 기준 1:1 파일을 생성했다. 통폐합 가중 crosswalk는 아직 외부 원장이 필요하다.",
        "8. sample weight 전달 위치는 `train_xgb(..., weights=...)`다.",
        "9. time decay는 train row 생성 직후 sample weight 배열을 만들 때 적용하면 된다.",
        "10. out-of-fold residual은 이번 신규 confirmatory/pilot 결과 파일에 행 단위로 저장되며 conformal calibration 입력으로 사용할 수 있다.",
    ]
    (REPORT_DIR / "locked_global_policy_analysis.md").write_text("\n".join(analysis), encoding="utf-8")

    lines = ["# Global Model Confirmatory Test", "", "동결된 성능형·안정형 정책을 2024년 이후 available actual에 적용한다. Confirmatory actual을 기준으로 threshold를 사후 변경하지 않는다.", "", "## 결과", ""]
    if confirm_summary:
        write_table(lines, confirm_summary, ["policy", "count", "wmape", "mape", "baseline_wmape", "improvement_vs_baseline_pct", "material_degraded_sector_years", "worst_sector_year_improvement", "confirmatory_role"])
    else:
        lines.extend(
            [
                "현재 `rolling_annual_prediction_comparisons.csv`에는 2024·2025 target 행이 있으나 official actual 값이 비어 있어 confirmatory 평가 모집단을 만들 수 없다.",
                "",
                "따라서 이번 라운드에서는 정책과 설정을 동결하고, 미사용 actual 연도가 확보되면 동일 스크립트를 재실행해 평가한다.",
            ]
        )
    (REPORT_DIR / "global_model_confirmatory_test.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 시군구 Global Model Pilot", "", "## 전체 정책 비교", ""]
    write_table(lines, sigungu_summary, ["policy", "count", "wmape", "mape", "macro_region_wmape", "median_ape", "p90_ape", "improvement_vs_baseline_pct", "material_degradation_count", "worst_sector_year_improvement", "ml_rate"])
    lines.extend(["", "## 산업별 결과", ""])
    write_table(lines, sigungu_sector_summary, ["sector_code", "sector_name", "policy", "count", "wmape", "mape", "improvement_vs_baseline_pct", "material_degradation_count", "worst_sector_year_improvement"])
    (REPORT_DIR / "sigungu_global_model_pilot.md").write_text("\n".join(lines), encoding="utf-8")


def write_table(lines: list[str], rows: list[dict[str, Any]], columns: list[str]) -> None:
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" if col in {"policy", "sector_code", "sector_name", "confirmatory_role"} else "---:" for col in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")


def main() -> int:
    write_locked_configs()
    confirm_predictions, confirm_summary, confirm_tuning = run_confirmatory()
    sigungu_predictions, sigungu_summary, sigungu_sector_summary, crosswalk = run_sigungu_pilot()
    write_csv(PROCESSED_DIR / "global_model_confirmatory_predictions.csv", confirm_predictions)
    write_csv(PROCESSED_DIR / "global_model_confirmatory_sector_results.csv", confirm_summary)
    write_csv(PROCESSED_DIR / "global_model_confirmatory_tuning_audit.csv", confirm_tuning)
    write_csv(PROCESSED_DIR / "sigungu_global_model_pilot_predictions.csv", sigungu_predictions)
    write_csv(PROCESSED_DIR / "sigungu_global_model_pilot_summary.csv", sigungu_summary)
    write_csv(PROCESSED_DIR / "sigungu_global_model_pilot_by_sector.csv", sigungu_sector_summary)
    write_csv(PROCESSED_DIR / "sigungu_region_crosswalk.csv", crosswalk)
    write_reports(confirm_summary, sigungu_summary, sigungu_sector_summary)
    print(f"confirmatory predictions: {len(confirm_predictions)}")
    print(f"sigungu pilot predictions: {len(sigungu_predictions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
