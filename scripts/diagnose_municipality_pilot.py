from __future__ import annotations

from collections import defaultdict
from math import log
from statistics import mean, median
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv


EPS = 1e-12
REPORT_DIR = ROOT / "reports"


def num(value: Any, default: float = 0.0) -> float:
    parsed = parse_number(value)
    return default if parsed is None else float(parsed)


def grouped(rows: list[dict[str, Any]], keys: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[tuple(row.get(key, "") for key in keys)].append(row)
    return out


def load_policy(policy: str) -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(PROCESSED_DIR / "sigungu_global_model_pilot_predictions.csv"):
        if row.get("policy") != policy:
            continue
        actual = num(row.get("actual_annual_gva"))
        baseline = num(row.get("baseline_prediction"))
        prediction = num(row.get("prediction"))
        parent = num(row.get("parent_predicted_annual_gva"))
        if min(actual, baseline, prediction, parent) <= 0:
            continue
        rows.append(
            {
                "source_region": row.get("source_region", ""),
                "sigungu_code": row.get("sigungu_code", ""),
                "sigungu_name": row.get("sigungu_name", ""),
                "sector_code": row.get("sector_code", ""),
                "sector_name": row.get("sector_name", ""),
                "target_year": int(row.get("target_year", 0)),
                "actual": actual,
                "baseline": baseline,
                "prediction": prediction,
                "parent_forecast": parent,
            }
        )
    return rows


def wmape(rows: list[dict[str, Any]], field: str) -> float:
    denom = sum(abs(float(r["actual"])) for r in rows)
    if denom <= EPS:
        return 0.0
    return sum(abs(float(r[field]) - float(r["actual"])) for r in rows) / denom * 100.0


def mape(rows: list[dict[str, Any]], field: str) -> float:
    values = [abs((float(r[field]) - float(r["actual"])) / float(r["actual"])) * 100 for r in rows if float(r["actual"])]
    return mean(values) if values else 0.0


def improvement(base: float, current: float) -> float:
    return (base - current) / base * 100.0 if base else 0.0


def parent_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return (row["source_region"], row["sector_code"], int(row["target_year"]))


def attach_parent_actual(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actual_parent = {key: sum(r["actual"] for r in items) for key, items in grouped(rows, ["source_region", "sector_code", "target_year"]).items()}
    out = []
    for row in rows:
        out.append({**row, "parent_actual": actual_parent[parent_key(row)]})
    return out


def decompose_errors() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = attach_parent_actual(load_policy("baseline"))
    ml_by_key = {
        (r["source_region"], r["sigungu_code"], r["sector_code"], r["target_year"]): r
        for r in attach_parent_actual(load_policy("global_full_strength"))
    }
    detail = []
    for key, items in grouped(base, ["source_region", "sector_code", "target_year"]).items():
        ml_items = [ml_by_key.get((r["source_region"], r["sigungu_code"], r["sector_code"], r["target_year"])) for r in items]
        if any(row is None for row in ml_items):
            continue
        ml_items_typed = [row for row in ml_items if row is not None]
        forecast_parent = items[0]["parent_forecast"]
        actual_parent = items[0]["parent_actual"]
        baseline_total = sum(r["baseline"] for r in items)
        ml_total = sum(r["prediction"] for r in ml_items_typed)
        rows_for_group = []
        for b, m in zip(items, ml_items_typed):
            baseline_share = b["baseline"] / baseline_total if baseline_total else 0.0
            ml_share = m["prediction"] / ml_total if ml_total else 0.0
            scenarios = {
                "forecast_parent_baseline_share": forecast_parent * baseline_share,
                "forecast_parent_ml_share": forecast_parent * ml_share,
                "actual_parent_baseline_share": actual_parent * baseline_share,
                "actual_parent_ml_share": actual_parent * ml_share,
            }
            for scenario, pred in scenarios.items():
                rows_for_group.append({**b, "scenario": scenario, "prediction": pred})
                detail.append(
                    {
                        "source_region": b["source_region"],
                        "sigungu_code": b["sigungu_code"],
                        "sigungu_name": b["sigungu_name"],
                        "sector_code": b["sector_code"],
                        "sector_name": b["sector_name"],
                        "target_year": b["target_year"],
                        "scenario": scenario,
                        "actual_annual_gva": round(b["actual"], 6),
                        "prediction": round(pred, 6),
                        "baseline_share": round(baseline_share, 12),
                        "ml_share": round(ml_share, 12),
                        "actual_share": round(b["actual"] / actual_parent if actual_parent else 0.0, 12),
                        "parent_forecast": round(forecast_parent, 6),
                        "parent_actual": round(actual_parent, 6),
                        "parent_total_error_pct": round((forecast_parent - actual_parent) / actual_parent * 100, 6) if actual_parent else "",
                    }
                )
    summary = summarize_policy(detail, "scenario")
    return detail, summary


def summarize_policy(rows: list[dict[str, Any]], group_field: str) -> list[dict[str, Any]]:
    out = []
    for (name,), items in grouped(rows, [group_field]).items():
        normalized = [
            {
                **r,
                "actual": num(r.get("actual_annual_gva"), num(r.get("actual"))),
                "prediction": num(r.get("prediction")),
            }
            for r in items
        ]
        denom = sum(abs(r["actual"]) for r in normalized)
        err = sum(abs(r["prediction"] - r["actual"]) for r in normalized)
        out.append(
            {
                group_field: name,
                "count": len(items),
                "wmape": round(err / denom * 100, 6) if denom else "",
                "mape": round(mean([abs((r["prediction"] - r["actual"]) / r["actual"]) * 100 for r in normalized if r["actual"]]), 6),
                "actual_sum": round(denom, 6),
                "absolute_error_sum": round(err, 6),
            }
        )
    if group_field == "model":
        base = next((r for r in out if r[group_field] == "zero_residual"), None)
    else:
        base = next((r for r in out if str(r[group_field]).endswith("baseline_share") and str(r[group_field]).startswith("forecast")), None)
    if base:
        for row in out:
            row["improvement_vs_forecast_baseline_pct"] = round(improvement(float(base["wmape"]), float(row["wmape"])), 6)
    return sorted(out, key=lambda r: str(r[group_field]))


def residual_diagnostics() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = attach_parent_actual(load_policy("baseline"))
    for row in rows:
        row["residual"] = log((row["actual"] + EPS) / (row["baseline"] + EPS))
    by_cell = grouped(rows, ["source_region", "sigungu_code", "sector_code"])
    diag = []
    for key, items in by_cell.items():
        ordered = sorted(items, key=lambda r: r["target_year"])
        residuals = [r["residual"] for r in ordered]
        lag_pairs = [(ordered[i]["residual"], ordered[i - 1]["residual"]) for i in range(1, len(ordered))]
        lag2_pairs = [(ordered[i]["residual"], ordered[i - 2]["residual"]) for i in range(2, len(ordered))]
        diag.append(
            {
                "source_region": key[0],
                "sigungu_code": key[1],
                "sector_code": key[2],
                "observation_count": len(items),
                "residual_mean": round(mean(residuals), 8),
                "residual_std": round(float(np.std(residuals)), 8),
                "residual_p05": round(float(np.percentile(residuals, 5)), 8),
                "residual_p95": round(float(np.percentile(residuals, 95)), 8),
                "lag1_correlation": round(corr([a for a, _b in lag_pairs], [b for _a, b in lag_pairs]), 8) if len(lag_pairs) >= 2 else "",
                "lag2_correlation": round(corr([a for a, _b in lag2_pairs], [b for _a, b in lag2_pairs]), 8) if len(lag2_pairs) >= 2 else "",
                "same_sign_ratio": round(mean([1.0 if a * b > 0 else 0.0 for a, b in lag_pairs]), 8) if lag_pairs else "",
            }
        )
    benchmarks = residual_benchmarks(rows)
    oracle = oracle_alpha(rows)
    return diag, benchmarks, oracle


def residual_benchmarks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    by_key = {(r["source_region"], r["sigungu_code"], r["sector_code"], r["target_year"]): r["residual"] for r in rows}
    for row in rows:
        hist = [v for (region, code, sector, year), v in by_key.items() if region == row["source_region"] and code == row["sigungu_code"] and sector == row["sector_code"] and year < row["target_year"]]
        lag1 = by_key.get((row["source_region"], row["sigungu_code"], row["sector_code"], row["target_year"] - 1))
        province_sector_hist = [v for (region, _code, sector, year), v in by_key.items() if region == row["source_region"] and sector == row["sector_code"] and year < row["target_year"]]
        sector_hist = [v for (_region, _code, sector, year), v in by_key.items() if sector == row["sector_code"] and year < row["target_year"]]
        candidates = {
            "zero_residual": 0.0,
            "cell_mean_residual": mean(hist) if hist else 0.0,
            "lag1_residual": lag1 if lag1 is not None else 0.0,
            "province_sector_mean_residual": mean(province_sector_hist) if province_sector_hist else 0.0,
            "sector_mean_residual": mean(sector_hist) if sector_hist else 0.0,
        }
        for model, residual in candidates.items():
            out.append(
                {
                    "model": model,
                    "source_region": row["source_region"],
                    "sigungu_code": row["sigungu_code"],
                    "sigungu_name": row["sigungu_name"],
                    "sector_code": row["sector_code"],
                    "sector_name": row["sector_name"],
                    "target_year": row["target_year"],
                    "actual_annual_gva": round(row["actual"], 6),
                    "baseline_prediction": round(row["baseline"], 6),
                    "prediction": round(row["baseline"] * np.exp(residual), 6),
                }
            )
    return summarize_policy(out, "model")


def oracle_alpha(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = load_policy("baseline")
    ml = {
        (r["source_region"], r["sigungu_code"], r["sector_code"], r["target_year"]): r
        for r in load_policy("global_full_strength")
    }
    all_rows = []
    for row in base:
        key = (row["source_region"], row["sigungu_code"], row["sector_code"], row["target_year"])
        model = ml.get(key)
        if not model:
            continue
        for alpha in [v / 10 for v in range(0, 11)]:
            pred = row["baseline"] * np.exp(alpha * log((model["prediction"] + EPS) / (row["baseline"] + EPS)))
            all_rows.append({**row, "oracle_group": "sector_year", "alpha": alpha, "prediction": pred})
    out = []
    for group_name, keys in {
        "sector_year": ["sector_code", "target_year"],
        "province_sector_year": ["source_region", "sector_code", "target_year"],
    }.items():
        for group_key, items in grouped([r for r in all_rows if r["oracle_group"] == group_name], keys).items():
            by_alpha = grouped(items, ["alpha"])
            best_alpha, best_wmape = min(((alpha[0], wmape_like(part)) for alpha, part in by_alpha.items()), key=lambda x: x[1])
            base_w = wmape_like([r for r in items if r["alpha"] == 0.0])
            out.append(
                {
                    "oracle_group": group_name,
                    **{field: value for field, value in zip(keys, group_key)},
                    "best_alpha": best_alpha,
                    "baseline_wmape": round(base_w, 6),
                    "oracle_wmape": round(best_wmape, 6),
                    "oracle_improvement_pct": round(improvement(base_w, best_wmape), 6),
                }
            )
    return out


def wmape_like(rows: list[dict[str, Any]]) -> float:
    denom = sum(abs(float(r["actual"])) for r in rows)
    return sum(abs(float(r["prediction"]) - float(r["actual"])) for r in rows) / denom * 100 if denom else 0.0


def corr(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    mx, my = mean(x), mean(y)
    vx = sum((v - mx) ** 2 for v in x)
    vy = sum((v - my) ** 2 for v in y)
    if vx <= EPS or vy <= EPS:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (vx * vy) ** 0.5


def share_stability() -> list[dict[str, Any]]:
    rows = attach_parent_actual(load_policy("baseline"))
    by_parent = grouped(rows, ["source_region", "sector_code", "target_year"])
    share_rows = []
    for key, items in by_parent.items():
        parent_actual = sum(r["actual"] for r in items)
        parent_baseline = sum(r["baseline"] for r in items)
        for rank, row in enumerate(sorted(items, key=lambda r: r["actual"], reverse=True), start=1):
            actual_share = row["actual"] / parent_actual if parent_actual else 0.0
            baseline_share = row["baseline"] / parent_baseline if parent_baseline else 0.0
            share_rows.append({**row, "actual_share": actual_share, "baseline_share": baseline_share, "actual_rank": rank})
    out = []
    for key, items in grouped(share_rows, ["source_region", "sector_code", "target_year"]).items():
        prev = [r for r in share_rows if r["source_region"] == key[0] and r["sector_code"] == key[1] and r["target_year"] == int(key[2]) - 1]
        prev_by_code = {r["sigungu_code"]: r for r in prev}
        aligned = [(r, prev_by_code[r["sigungu_code"]]) for r in items if r["sigungu_code"] in prev_by_code]
        actual_shares = [r["actual_share"] for r in items]
        baseline_shares = [r["baseline_share"] for r in items]
        out.append(
            {
                "source_region": key[0],
                "sector_code": key[1],
                "target_year": key[2],
                "count": len(items),
                "year_share_correlation": round(corr([r["actual_share"] for r, _p in aligned], [p["actual_share"] for _r, p in aligned]), 8) if len(aligned) >= 2 else "",
                "share_mae": round(mean([abs(a - b) for a, b in zip(actual_shares, baseline_shares)]), 10) if items else "",
                "share_wmape": round(sum(abs(a - b) for a, b in zip(actual_shares, baseline_shares)) / sum(actual_shares) * 100, 6) if sum(actual_shares) else "",
                "top1_concentration": round(max(actual_shares), 8) if actual_shares else "",
                "top3_concentration": round(sum(sorted(actual_shares, reverse=True)[:3]), 8) if actual_shares else "",
                "hhi": round(sum(v * v for v in actual_shares), 8),
                "jensen_shannon_divergence": round(js_divergence(actual_shares, baseline_shares), 8),
            }
        )
    return out


def js_divergence(p: list[float], q: list[float]) -> float:
    p_arr = np.asarray(p, dtype=float) + EPS
    q_arr = np.asarray(q, dtype=float) + EPS
    p_arr = p_arr / p_arr.sum()
    q_arr = q_arr / q_arr.sum()
    m_arr = 0.5 * (p_arr + q_arr)
    return float(0.5 * np.sum(p_arr * np.log(p_arr / m_arr)) + 0.5 * np.sum(q_arr * np.log(q_arr / m_arr)))


def small_cell_analysis() -> list[dict[str, Any]]:
    rows = load_policy("global_regret_adaptive")
    out_rows = []
    sector_values = defaultdict(list)
    for row in rows:
        sector_values[row["sector_code"]].append(row["actual"])
    thresholds = {sector: np.percentile(values, [10, 25, 50, 75, 90]) for sector, values in sector_values.items()}
    for row in rows:
        t = thresholds[row["sector_code"]]
        actual = row["actual"]
        if actual <= 0:
            bucket = "zero"
        elif actual < t[0]:
            bucket = "p00_p10"
        elif actual < t[1]:
            bucket = "p10_p25"
        elif actual < t[2]:
            bucket = "p25_p50"
        elif actual < t[3]:
            bucket = "p50_p75"
        elif actual < t[4]:
            bucket = "p75_p90"
        else:
            bucket = "p90_p100"
        out_rows.append({**row, "size_bucket": bucket})
    out = []
    for key, items in grouped(out_rows, ["sector_code", "size_bucket"]).items():
        baseline_w = wmape(items, "baseline")
        model_w = wmape(items, "prediction")
        apes = [abs((r["prediction"] - r["actual"]) / r["actual"]) * 100 for r in items if r["actual"]]
        out.append(
            {
                "sector_code": key[0],
                "size_bucket": key[1],
                "count": len(items),
                "actual_sum": round(sum(r["actual"] for r in items), 6),
                "baseline_wmape": round(baseline_w, 6),
                "model_wmape": round(model_w, 6),
                "improvement_pct": round(improvement(baseline_w, model_w), 6),
                "median_ape": round(median(apes), 6) if apes else "",
                "p90_ape": round(float(np.percentile(apes, 90)), 6) if apes else "",
                "absolute_error": round(sum(abs(r["prediction"] - r["actual"]) for r in items), 6),
            }
        )
    return out


def write_reports(
    decomposition_summary: list[dict[str, Any]],
    residual_summary: list[dict[str, Any]],
    oracle: list[dict[str, Any]],
    share: list[dict[str, Any]],
    small: list[dict[str, Any]],
) -> None:
    lines = ["# 시군구 오차 분해", "", "## Parent × Share 조합", ""]
    write_table(lines, decomposition_summary, ["scenario", "count", "wmape", "mape", "improvement_vs_forecast_baseline_pct", "actual_sum", "absolute_error_sum"])
    lines.extend(["", "## 해석", "", "actual parent에서도 ML share가 baseline share보다 나쁘면 문제는 부모 총량보다 하위 share 모델에 있다."])
    (REPORT_DIR / "municipality_error_decomposition.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 시군구 Residual Learnability", "", "## 단순 residual benchmark", ""]
    write_table(lines, residual_summary, ["model", "count", "wmape", "mape", "improvement_vs_forecast_baseline_pct"])
    lines.extend(["", "## Oracle alpha", ""])
    write_table(lines, oracle[:60], ["oracle_group", "sector_code", "target_year", "source_region", "best_alpha", "baseline_wmape", "oracle_wmape", "oracle_improvement_pct"])
    (REPORT_DIR / "municipality_residual_learnability.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 시군구 Share 안정성", "", "## Parent group share metrics", ""]
    write_table(lines, share[:120], ["source_region", "sector_code", "target_year", "count", "year_share_correlation", "share_mae", "share_wmape", "top1_concentration", "top3_concentration", "hhi", "jensen_shannon_divergence"])
    (REPORT_DIR / "municipality_share_stability.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 시군구 Small-cell 분석", "", "## 산업별 actual 규모 구간", ""]
    write_table(lines, small, ["sector_code", "size_bucket", "count", "actual_sum", "baseline_wmape", "model_wmape", "improvement_pct", "median_ape", "p90_ape"])
    (REPORT_DIR / "municipality_small_cell_analysis.md").write_text("\n".join(lines), encoding="utf-8")

    for filename, title, body in [
        ("municipality_feature_analysis.md", "시군구 전용 Feature 분석", "이번 라운드는 feature 추가 전 진단 단계다. parent-relative 사업체·종사자·매출 share, 산업 LQ, 지역 유형, 산업단지·대형사업장 이벤트 feature를 다음 구현 후보로 둔다."),
        ("municipality_partial_pooling.md", "시군구 Partial Pooling", "global XGBoost와 sector-independent 사이의 partial pooling은 아직 구현하지 않았다. 오차 분해와 oracle alpha에서 개선 upper bound가 확인되는 경우에만 Ridge fixed effect 및 province-sector residual correction부터 비교한다."),
        ("municipality_gate_analysis.md", "시군구 Gate 분석", "현재 시도 수준 gate를 전이한 ML 적용률은 높다. 다음 단계는 parent group 단위 과거 개선율, share 안정성, small-cell 비율을 이용해 적용률을 낮추는 conservative gate를 실험한다."),
        ("municipality_noninferiority.md", "시군구 비열등성 분석", "global_regret_adaptive와 baseline의 WMAPE 차이가 작으므로 parent group bootstrap으로 비열등성을 평가해야 한다. 이번 라운드에서는 bootstrap 구현 전 진단 파일을 생성했다."),
    ]:
        (REPORT_DIR / filename).write_text(f"# {title}\n\n{body}\n", encoding="utf-8")


def write_table(lines: list[str], rows: list[dict[str, Any]], columns: list[str]) -> None:
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" if col in {"scenario", "model", "oracle_group", "source_region", "sector_code", "size_bucket"} else "---:" for col in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")


def main() -> int:
    decomposition, decomposition_summary = decompose_errors()
    residual_diag, residual_summary, oracle = residual_diagnostics()
    share = share_stability()
    small = small_cell_analysis()
    write_csv(PROCESSED_DIR / "municipality_error_decomposition.csv", decomposition)
    write_csv(PROCESSED_DIR / "municipality_error_decomposition_summary.csv", decomposition_summary)
    write_csv(PROCESSED_DIR / "municipality_residual_diagnostics.csv", residual_diag)
    write_csv(PROCESSED_DIR / "municipality_residual_benchmark_summary.csv", residual_summary)
    write_csv(PROCESSED_DIR / "municipality_oracle_alpha.csv", oracle)
    write_csv(PROCESSED_DIR / "municipality_share_stability.csv", share)
    write_csv(PROCESSED_DIR / "municipality_size_bin_results.csv", small)
    # Keep the latest pilot comparison under the requested generic name.
    comparison = read_csv(PROCESSED_DIR / "sigungu_global_model_pilot_summary.csv")
    write_csv(PROCESSED_DIR / "municipality_policy_comparison.csv", comparison)
    write_reports(decomposition_summary, residual_summary, oracle, share, small)
    print(f"decomposition rows: {len(decomposition)}")
    print(f"residual diagnostics: {len(residual_diag)}")
    print(f"share rows: {len(share)}")
    print(f"small-cell rows: {len(small)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
