from __future__ import annotations

from collections import defaultdict
from math import exp, log
from statistics import mean
from typing import Any

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv


PREDICTIONS = PROCESSED_DIR / "reconciled_model_predictions.csv"
SAFE = PROCESSED_DIR / "reconciled_model_safe_predictions.csv"
REPORT = ROOT / "reports" / "reconciled_model_next_experiments.md"
ML_FIELD = "xgboost_log_ratio_reconciled_prediction"
POLICIES = [
    "baseline_all",
    "full_ml_all",
    "safe_selected_current",
    "rolling_grade_a_only",
    "rolling_grade_ab",
    "rolling_best_policy",
    "oracle_sector_policy",
]

GRADE_CONFIG = {
    "min_history_years": 2,
    "grade_a_min_average_improvement_pct": 2.0,
    "grade_a_min_improved_year_ratio": 0.60,
    "grade_a_min_recent_improved_years": 2,
    "grade_a_max_worst_degradation_pct": 10.0,
    "grade_b_min_average_improvement_pct": 0.0,
    "grade_b_min_improved_year_ratio": 0.50,
}


def load_rows() -> list[dict[str, Any]]:
    safe_rows = {}
    for row in read_csv(SAFE):
        key = (row["area_code"], row["sector_code"], int(row["target_year"]))
        safe_rows[key] = row
    rows = []
    for row in read_csv(PREDICTIONS):
        key = (row["area_code"], row["sector_code"], int(row["target_year"]))
        safe = safe_rows.get(key, {})
        actual = parse_number(row.get("actual_annual_gva"))
        baseline = parse_number(row.get("baseline_prediction"))
        full_ml = parse_number(row.get(ML_FIELD))
        safe_selected = parse_number(safe.get("safe_selected_prediction"))
        shrink = parse_number(safe.get("shrink_prediction"))
        blend = parse_number(safe.get("blend_prediction"))
        parent_baseline = parse_number(row.get("parent_baseline_total"))
        parent_actual = parse_number(row.get("parent_actual_total"))
        if None in {actual, baseline, full_ml, safe_selected, shrink, blend, parent_baseline, parent_actual}:
            continue
        rows.append(
            {
                "area_code": row["area_code"],
                "area_name": row["area_name"],
                "sector_code": row["sector_code"],
                "sector_name": row["sector_name"],
                "target_year": int(row["target_year"]),
                "actual": float(actual),
                "baseline": float(baseline),
                "full_ml": float(full_ml),
                "safe_selected": float(safe_selected),
                "shrink": float(shrink),
                "blend": float(blend),
                "parent_baseline_total": float(parent_baseline),
                "parent_actual_total": float(parent_actual),
            }
        )
    return sorted(rows, key=lambda r: (r["sector_code"], r["target_year"], r["area_code"]))


def wmape(rows: list[dict[str, Any]], field: str) -> float:
    actual_sum = sum(abs(r["actual"]) for r in rows)
    if actual_sum == 0:
        return 0.0
    return sum(abs(r[field] - r["actual"]) for r in rows) / actual_sum * 100.0


def mape(rows: list[dict[str, Any]], field: str) -> float:
    values = [abs((r[field] - r["actual"]) / r["actual"]) * 100.0 for r in rows if r["actual"]]
    return mean(values) if values else 0.0


def improvement(base: float, model: float) -> float:
    return (base - model) / base * 100.0 if base else 0.0


def groups(rows: list[dict[str, Any]], keys: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[tuple(row[k] for k in keys)].append(row)
    return out


def sector_year_history(rows: list[dict[str, Any]], sector: str, target_year: int, field: str = "full_ml") -> list[dict[str, Any]]:
    out = []
    for year, items in sorted(groups([r for r in rows if r["sector_code"] == sector and r["target_year"] < target_year], ["target_year"]).items()):
        base = wmape(items, "baseline")
        model = wmape(items, field)
        out.append({"target_year": year[0], "improvement_pct": improvement(base, model), "baseline_wmape": base, "model_wmape": model})
    return out


def grade_from_history(history: list[dict[str, Any]]) -> tuple[str, str]:
    if len(history) < GRADE_CONFIG["min_history_years"]:
        return "U", "insufficient_history"
    improvements = [h["improvement_pct"] for h in history]
    avg = mean(improvements)
    ratio = sum(1 for v in improvements if v > 0) / len(improvements)
    recent = sum(1 for v in improvements[-2:] if v > 0)
    worst = min(improvements)
    if (
        avg >= GRADE_CONFIG["grade_a_min_average_improvement_pct"]
        and ratio >= GRADE_CONFIG["grade_a_min_improved_year_ratio"]
        and recent >= GRADE_CONFIG["grade_a_min_recent_improved_years"]
        and worst >= -GRADE_CONFIG["grade_a_max_worst_degradation_pct"]
    ):
        return "A", f"avg={avg:.3f};ratio={ratio:.3f};recent={recent};worst={worst:.3f}"
    if avg >= GRADE_CONFIG["grade_b_min_average_improvement_pct"] and ratio >= GRADE_CONFIG["grade_b_min_improved_year_ratio"]:
        return "B", f"avg={avg:.3f};ratio={ratio:.3f};recent={recent};worst={worst:.3f}"
    if avg > 0:
        return "C", f"avg={avg:.3f};ratio={ratio:.3f};recent={recent};worst={worst:.3f}"
    return "D", f"avg={avg:.3f};ratio={ratio:.3f};recent={recent};worst={worst:.3f}"


def best_policy_from_history(history_rows: list[dict[str, Any]]) -> str:
    if not history_rows:
        return "baseline"
    candidates = ["baseline", "full_ml", "safe_selected", "shrink", "blend"]
    scores = {candidate: wmape(history_rows, candidate) for candidate in candidates}
    return min(scores, key=scores.get)


def prediction_for_policy(row: dict[str, Any], policy: str, grade: str, best_model: str, sector_year_rows: list[dict[str, Any]]) -> tuple[float, str, bool, str]:
    if policy == "baseline_all":
        return row["baseline"], "baseline", True, "policy_baseline"
    if policy == "full_ml_all":
        return row["full_ml"], "full_ml", False, ""
    if policy == "safe_selected_current":
        return row["safe_selected"], "safe_selected", False, ""
    if policy == "rolling_grade_a_only":
        if grade == "A":
            return row["full_ml"], "full_ml", False, ""
        return row["baseline"], "baseline", True, f"grade_{grade}_fallback"
    if policy == "rolling_grade_ab":
        if grade == "A":
            return row["full_ml"], "full_ml", False, ""
        if grade == "B":
            return row["safe_selected"], "safe_selected", False, ""
        return row["baseline"], "baseline", True, f"grade_{grade}_fallback"
    if policy == "rolling_best_policy":
        return row[best_model], best_model, best_model == "baseline", f"history_best={best_model}"
    if policy == "oracle_sector_policy":
        sector = [r for r in sector_year_rows if r["sector_code"] == row["sector_code"] and r["target_year"] == row["target_year"]]
        candidates = ["baseline", "full_ml", "safe_selected", "shrink", "blend"]
        scores = {candidate: wmape(sector, candidate) for candidate in candidates}
        best = min(scores, key=scores.get)
        return row[best], best, best == "baseline", "uses_target_actual_oracle"
    raise ValueError(policy)


def rolling_policy_backtest(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    out = []
    for (sector, year), items in sorted(groups(rows, ["sector_code", "target_year"]).items()):
        history = sector_year_history(rows, sector, year, "full_ml")
        grade, reason = grade_from_history(history)
        history_rows = [r for r in rows if r["sector_code"] == sector and r["target_year"] < year]
        best_model = best_policy_from_history(history_rows)
        for policy in POLICIES:
            for row in items:
                pred, selected, fallback, fallback_reason = prediction_for_policy(row, policy, grade, best_model, rows)
                out.append(
                    {
                        "policy": policy,
                        "target_year": year,
                        "sector_code": sector,
                        "sector_name": row["sector_name"],
                        "area_code": row["area_code"],
                        "area_name": row["area_name"],
                        "actual_annual_gva": round(row["actual"], 6),
                        "baseline_prediction": round(row["baseline"], 6),
                        "policy_prediction": round(pred, 6),
                        "selected_model": selected,
                        "confidence_grade_before_prediction": grade,
                        "grade_reason": reason,
                        "fallback_applied": fallback,
                        "fallback_reason": fallback_reason,
                    }
                )
    summary = summarize_policies(out)
    return out, summary


def summarize_policies(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    by_policy = groups(predictions, ["policy"])
    baseline_by_year = {}
    for year_key, items in groups([r for r in predictions if r["policy"] == "baseline_all"], ["target_year"]).items():
        baseline_by_year[year_key[0]] = wmape_generic(items, "baseline_prediction")
    for policy, items in sorted(by_policy.items()):
        policy_name = policy[0]
        overall_wmape = wmape_generic(items, "policy_prediction")
        baseline_wmape = wmape_generic(items, "baseline_prediction")
        by_year = groups(items, ["target_year"])
        by_sector_year = groups(items, ["sector_code", "target_year"])
        year_improvements = [improvement(baseline_by_year[y[0]], wmape_generic(part, "policy_prediction")) for y, part in by_year.items()]
        sector_improvements = [improvement(wmape_generic(part, "baseline_prediction"), wmape_generic(part, "policy_prediction")) for part in by_sector_year.values()]
        ml_rows = [r for r in items if r["selected_model"] != "baseline"]
        switch_count = 0
        for sector_key, sector_items in groups(items, ["sector_code"]).items():
            ordered = sorted(sector_items, key=lambda r: (r["target_year"], r["area_code"]))
            by_year = []
            for year_key, year_items in groups(ordered, ["target_year"]).items():
                selected = sorted({r["selected_model"] for r in year_items})
                by_year.append((year_key[0], "+".join(selected)))
            by_year.sort()
            switch_count += sum(1 for idx in range(1, len(by_year)) if by_year[idx][1] != by_year[idx - 1][1])
        rows.append(
            {
                "policy": policy_name,
                "count": len(items),
                "overall_mape": round(mape_generic(items, "policy_prediction"), 6),
                "overall_wmape": round(overall_wmape, 6),
                "improvement_vs_baseline_pct": round(improvement(baseline_wmape, overall_wmape), 6),
                "improved_year_count": sum(1 for value in year_improvements if value > 0),
                "degraded_year_count": sum(1 for value in year_improvements if value < 0),
                "improved_sector_year_count": sum(1 for value in sector_improvements if value > 0),
                "degraded_sector_year_count": sum(1 for value in sector_improvements if value < 0),
                "worst_year_improvement_pct": round(min(year_improvements), 6) if year_improvements else "",
                "worst_sector_improvement_pct": round(min(sector_improvements), 6) if sector_improvements else "",
                "ml_adoption_rate": round(len(ml_rows) / len(items), 6) if items else "",
                "model_switch_count": switch_count,
            }
        )
    return rows


def wmape_generic(rows: list[dict[str, Any]], field: str) -> float:
    actual_sum = sum(abs(parse_number(r.get("actual_annual_gva")) or 0) for r in rows)
    if actual_sum == 0:
        return 0.0
    err = sum(abs((parse_number(r.get(field)) or 0) - (parse_number(r.get("actual_annual_gva")) or 0)) for r in rows)
    return err / actual_sum * 100


def mape_generic(rows: list[dict[str, Any]], field: str) -> float:
    values = []
    for r in rows:
        actual = parse_number(r.get("actual_annual_gva"))
        pred = parse_number(r.get(field))
        if actual and pred is not None:
            values.append(abs((pred - actual) / actual) * 100)
    return mean(values) if values else 0.0


def parent_sensitivity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scenarios = []
    shocks = [-0.10, -0.05, -0.03, -0.01, 0.0, 0.01, 0.03, 0.05, 0.10]
    for mode in ["forecast_parent", "actual_parent"]:
        scale_field = "parent_baseline_total" if mode == "forecast_parent" else "parent_actual_total"
        for source in ["baseline", "full_ml"]:
            adjusted = []
            for row in rows:
                factor = row[scale_field] / row["parent_baseline_total"] if row["parent_baseline_total"] else 1.0
                adjusted.append({**row, "prediction": row[source] * factor})
            scenarios.append(summarize_parent_case(adjusted, f"{mode}_{source}", 0.0))
    for shock in shocks:
        adjusted = []
        for row in rows:
            adjusted.append({**row, "prediction": row["full_ml"] * (1.0 + shock)})
        scenarios.append(summarize_parent_case(adjusted, "full_ml_parent_shock", shock))
    return scenarios


def summarize_parent_case(rows: list[dict[str, Any]], scenario: str, shock: float) -> dict[str, Any]:
    actual_sum = sum(abs(r["actual"]) for r in rows)
    error = sum(abs(r["prediction"] - r["actual"]) for r in rows)
    parent_error = abs(sum(r["prediction"] for r in rows) - sum(r["actual"] for r in rows)) / sum(r["actual"] for r in rows) * 100
    baseline_error = sum(abs(r["baseline"] - r["actual"]) for r in rows)
    wmape = error / actual_sum * 100 if actual_sum else 0.0
    base = baseline_error / actual_sum * 100 if actual_sum else 0.0
    return {
        "scenario": scenario,
        "parent_shock": shock,
        "child_level_wmape": round(wmape, 6),
        "parent_level_percent_error": round(parent_error, 6),
        "improvement_vs_baseline_pct": round(improvement(base, wmape), 6),
        "mean_reconciliation_scaling_factor": round(mean([r["prediction"] / r["full_ml"] for r in rows if r["full_ml"]]), 6),
    }


def residual_benchmarks(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    out = []
    diagnostics = []
    by_key = {(r["area_code"], r["sector_code"], r["target_year"]): log(r["actual"] / r["baseline"]) for r in rows}
    for row in rows:
        lags = [by_key.get((row["area_code"], row["sector_code"], row["target_year"] - lag)) for lag in [1, 2, 3]]
        available = [v for v in lags if v is not None]
        sector_hist = [v for (area, sector, year), v in by_key.items() if sector == row["sector_code"] and year < row["target_year"]]
        region_hist = [v for (area, sector, year), v in by_key.items() if area == row["area_code"] and year < row["target_year"]]
        candidates = {
            "zero_residual": 0.0,
            "lag1_residual": lags[0] if lags[0] is not None else 0.0,
            "lag1_shrunk_residual": (lags[0] * 0.5) if lags[0] is not None else 0.0,
            "rolling_mean_residual": mean(available) if available else 0.0,
            "sector_mean_residual": mean(sector_hist) if sector_hist else 0.0,
            "region_mean_residual": mean(region_hist) if region_hist else 0.0,
            "xgboost_log_ratio": log(row["full_ml"] / row["baseline"]) if row["baseline"] else 0.0,
        }
        for model, residual in candidates.items():
            out.append(
                {
                    "model": model,
                    "area_code": row["area_code"],
                    "area_name": row["area_name"],
                    "sector_code": row["sector_code"],
                    "sector_name": row["sector_name"],
                    "target_year": row["target_year"],
                    "actual_annual_gva": round(row["actual"], 6),
                    "baseline_prediction": round(row["baseline"], 6),
                    "prediction": round(row["baseline"] * exp(residual), 6),
                }
            )
    for (sector, area), items in groups(rows, ["sector_code", "area_code"]).items():
        pairs = []
        signs = []
        for row in items:
            current = by_key.get((area, sector, row["target_year"]))
            lag1 = by_key.get((area, sector, row["target_year"] - 1))
            lag2 = by_key.get((area, sector, row["target_year"] - 2))
            if current is not None and lag1 is not None:
                pairs.append((current, lag1, lag2))
                signs.append(1 if current * lag1 > 0 else 0)
        diagnostics.append(
            {
                "sector_code": sector,
                "area_code": area,
                "residual_lag1_corr": round(corr([p[0] for p in pairs], [p[1] for p in pairs]), 6) if len(pairs) >= 2 else "",
                "residual_lag2_corr": round(corr([p[0] for p in pairs if p[2] is not None], [p[2] for p in pairs if p[2] is not None]), 6)
                if sum(1 for p in pairs if p[2] is not None) >= 2
                else "",
                "same_sign_ratio": round(mean(signs), 6) if signs else "",
                "residual_mean": round(mean([p[0] for p in pairs]), 6) if pairs else "",
            }
        )
    return out, diagnostics


def corr(x: list[float], y: list[float]) -> float:
    mx, my = mean(x), mean(y)
    vx = sum((v - mx) ** 2 for v in x)
    vy = sum((v - my) ** 2 for v in y)
    if vx == 0 or vy == 0:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (vx * vy) ** 0.5


def summarize_residual_models(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for model, items in sorted(groups(rows, ["model"]).items()):
        base = wmape_generic(items, "baseline_prediction")
        model_w = wmape_generic(items, "prediction")
        out.append(
            {
                "model": model[0],
                "count": len(items),
                "mape": round(mape_generic(items, "prediction"), 6),
                "wmape": round(model_w, 6),
                "improvement_vs_baseline_pct": round(improvement(base, model_w), 6),
            }
        )
    return out


def report(policy_summary: list[dict[str, Any]], parent_rows: list[dict[str, Any]], residual_summary: list[dict[str, Any]]) -> None:
    lines = [
        "# Reconciled ML 차기 실험 통합 보고서",
        "",
        "## 1. Rolling Gated Hybrid Backtest",
        "",
        "| policy | WMAPE | MAPE | improvement % | improved years | degraded sector-years | worst year improvement | worst sector improvement | ML adoption rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in policy_summary:
        lines.append(
            f"| {row['policy']} | {row['overall_wmape']} | {row['overall_mape']} | {row['improvement_vs_baseline_pct']} | {row['improved_year_count']} | {row['degraded_sector_year_count']} | {row['worst_year_improvement_pct']} | {row['worst_sector_improvement_pct']} | {row['ml_adoption_rate']} |"
        )
    lines.extend(
        [
            "",
            "## 2. Parent Total 민감도",
            "",
            "| scenario | shock | child WMAPE | parent error | improvement % | mean scale |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in parent_rows:
        lines.append(
            f"| {row['scenario']} | {row['parent_shock']} | {row['child_level_wmape']} | {row['parent_level_percent_error']} | {row['improvement_vs_baseline_pct']} | {row['mean_reconciliation_scaling_factor']} |"
        )
    lines.extend(
        [
            "",
            "## 3. 단순 Residual Benchmark",
            "",
            "| model | count | MAPE | WMAPE | improvement % |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in residual_summary:
        lines.append(f"| {row['model']} | {row['count']} | {row['mape']} | {row['wmape']} | {row['improvement_vs_baseline_pct']} |")
    lines.extend(
        [
            "",
            "## 4. 결론",
            "",
            "rolling policy는 사후 전체기간 grade를 쓰지 않고 target year 이전 성능 이력만 사용한다. `oracle_sector_policy`는 운영용이 아니라 후보 모델군의 이론적 상한선이다. Parent total 민감도는 현재 개선이 하위 share 보정인지 parent 총량 오차에 민감한지 구분하기 위한 진단이다.",
            "",
            "상세 CSV는 `data/processed/next_*` 파일로 저장되며 CP949 정책을 따른다.",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows = load_rows()
    policy_predictions, policy_summary = rolling_policy_backtest(rows)
    parent_rows = parent_sensitivity(rows)
    residual_rows, residual_diag = residual_benchmarks(rows)
    residual_summary = summarize_residual_models(residual_rows)
    write_csv(PROCESSED_DIR / "next_rolling_policy_predictions.csv", policy_predictions)
    write_csv(PROCESSED_DIR / "next_rolling_policy_summary.csv", policy_summary)
    write_csv(PROCESSED_DIR / "next_parent_total_sensitivity.csv", parent_rows)
    write_csv(PROCESSED_DIR / "next_residual_benchmark_predictions.csv", residual_rows)
    write_csv(PROCESSED_DIR / "next_residual_benchmark_summary.csv", residual_summary)
    write_csv(PROCESSED_DIR / "next_residual_diagnostics.csv", residual_diag)
    report(policy_summary, parent_rows, residual_summary)
    print(f"policy rows: {len(policy_predictions)}")
    print(f"policy summary rows: {len(policy_summary)}")
    print(f"parent scenarios: {len(parent_rows)}")
    print(f"residual rows: {len(residual_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
