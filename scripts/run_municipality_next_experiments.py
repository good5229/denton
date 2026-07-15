from __future__ import annotations

from collections import defaultdict
from math import exp, log
from statistics import mean, median
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, parse_number, read_csv, write_csv


EPS = 1e-12
REPORT_DIR = ROOT / "reports"
ALPHAS = [round(v / 10, 1) for v in range(0, 11)]


def num(value: Any, default: float = 0.0) -> float:
    parsed = parse_number(value)
    return default if parsed is None else float(parsed)


def grouped(rows: list[dict[str, Any]], keys: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[tuple(row.get(key, "") for key in keys)].append(row)
    return out


def load_rows() -> list[dict[str, Any]]:
    baseline: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    ml: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for row in read_csv(PROCESSED_DIR / "sigungu_global_model_pilot_predictions.csv"):
        policy = row.get("policy")
        if policy not in {"baseline", "global_full_strength"}:
            continue
        actual = num(row.get("actual_annual_gva"))
        baseline_value = num(row.get("baseline_prediction"))
        prediction = num(row.get("prediction"))
        parent = num(row.get("parent_predicted_annual_gva"))
        if min(actual, baseline_value, prediction, parent) <= 0:
            continue
        key = (row.get("source_region", ""), row.get("sigungu_code", ""), row.get("sector_code", ""), int(row.get("target_year", 0)))
        item = {
            "source_region": row.get("source_region", ""),
            "sigungu_code": row.get("sigungu_code", ""),
            "sigungu_name": row.get("sigungu_name", ""),
            "sector_code": row.get("sector_code", ""),
            "sector_name": row.get("sector_name", ""),
            "target_year": int(row.get("target_year", 0)),
            "actual": actual,
            "baseline": baseline_value,
            "prediction": prediction,
            "parent_forecast": parent,
        }
        if policy == "baseline":
            baseline[key] = item
        else:
            ml[key] = item
    rows = []
    for key, row in baseline.items():
        model = ml.get(key)
        if not model:
            continue
        rows.append(
            {
                **row,
                "ml_prediction": model["prediction"],
                "ml_log_ratio": log((model["prediction"] + EPS) / (row["baseline"] + EPS)),
            }
        )
    parent_actual = {key: sum(r["actual"] for r in items) for key, items in grouped(rows, ["source_region", "sector_code", "target_year"]).items()}
    parent_baseline = {key: sum(r["baseline"] for r in items) for key, items in grouped(rows, ["source_region", "sector_code", "target_year"]).items()}
    out = []
    for row in rows:
        pkey = (row["source_region"], row["sector_code"], row["target_year"])
        out.append(
            {
                **row,
                "parent_actual": parent_actual[pkey],
                "parent_baseline_sum": parent_baseline[pkey],
                "actual_share": row["actual"] / parent_actual[pkey] if parent_actual[pkey] else 0.0,
                "baseline_share": row["baseline"] / parent_baseline[pkey] if parent_baseline[pkey] else 0.0,
            }
        )
    return sorted(out, key=lambda r: (r["target_year"], r["source_region"], r["sector_code"], r["sigungu_code"]))


def wmape(rows: list[dict[str, Any]], field: str = "prediction") -> float:
    denom = sum(abs(float(r["actual"])) for r in rows)
    if denom <= EPS:
        return 0.0
    return sum(abs(float(r[field]) - float(r["actual"])) for r in rows) / denom * 100.0


def mape(rows: list[dict[str, Any]], field: str = "prediction") -> float:
    values = [abs((float(r[field]) - float(r["actual"])) / float(r["actual"])) * 100 for r in rows if float(r["actual"])]
    return mean(values) if values else 0.0


def improvement(base: float, current: float) -> float:
    return (base - current) / base * 100 if base else 0.0


def province_type(name: str) -> str:
    if name in {"서울특별시", "세종특별자치시"} or name.endswith("광역시"):
        return "metro"
    if name.endswith("도") or name.endswith("특별자치도"):
        return "province"
    return "other"


def size_bucket(row: dict[str, Any], thresholds: dict[str, np.ndarray]) -> str:
    t = thresholds[row["sector_code"]]
    value = row["baseline"]
    if value < t[0]:
        return "p00_p10"
    if value < t[1]:
        return "p10_p25"
    if value < t[2]:
        return "p25_p50"
    if value < t[3]:
        return "p50_p75"
    if value < t[4]:
        return "p75_p90"
    return "p90_p100"


def share_metrics_for_group(rows: list[dict[str, Any]], source_region: str, sector: str, target_year: int) -> dict[str, float]:
    hist = [r for r in rows if r["source_region"] == source_region and r["sector_code"] == sector and r["target_year"] < target_year]
    by_year = grouped(hist, ["target_year"])
    years = sorted(int(year[0]) for year in by_year)
    if len(years) < 2:
        return {"share_wmape": 999.0, "jsd": 999.0, "residual_std": 999.0, "child_count": len(by_year.get((target_year - 1,), []))}
    current = by_year[(years[-1],)]
    previous = by_year[(years[-2],)]
    prev_by_code = {r["sigungu_code"]: r for r in previous}
    aligned = [(r, prev_by_code[r["sigungu_code"]]) for r in current if r["sigungu_code"] in prev_by_code]
    share_wmape = sum(abs(r["actual_share"] - p["actual_share"]) for r, p in aligned) / max(EPS, sum(r["actual_share"] for r, _p in aligned)) * 100
    jsd = js_divergence([r["actual_share"] for r, _p in aligned], [p["actual_share"] for _r, p in aligned]) if aligned else 999.0
    residuals = [log((r["actual"] + EPS) / (r["baseline"] + EPS)) for r in hist]
    return {
        "share_wmape": share_wmape,
        "jsd": jsd,
        "residual_std": float(np.std(residuals)) if residuals else 999.0,
        "child_count": len(current),
        "hhi": sum(r["actual_share"] ** 2 for r in current),
        "top1": max([r["actual_share"] for r in current] or [0.0]),
    }


def js_divergence(p: list[float], q: list[float]) -> float:
    p_arr = np.asarray(p, dtype=float) + EPS
    q_arr = np.asarray(q, dtype=float) + EPS
    p_arr = p_arr / p_arr.sum()
    q_arr = q_arr / q_arr.sum()
    m_arr = 0.5 * (p_arr + q_arr)
    return float(0.5 * np.sum(p_arr * np.log(p_arr / m_arr)) + 0.5 * np.sum(q_arr * np.log(q_arr / m_arr)))


def assign_regimes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics_by_key = {}
    for row in rows:
        key = (row["source_region"], row["sector_code"], row["target_year"])
        if key not in metrics_by_key:
            metrics_by_key[key] = share_metrics_for_group(rows, row["source_region"], row["sector_code"], row["target_year"])
    valid = [m for m in metrics_by_key.values() if m["share_wmape"] < 900]
    if not valid:
        return [{**row, "stability_regime": "unknown"} for row in rows]
    sw_q = np.percentile([m["share_wmape"] for m in valid], [33, 67])
    js_q = np.percentile([m["jsd"] for m in valid], [33, 67])
    rs_q = np.percentile([m["residual_std"] for m in valid], [33, 67])
    out = []
    for row in rows:
        m = metrics_by_key[(row["source_region"], row["sector_code"], row["target_year"])]
        if m["share_wmape"] <= sw_q[0] and m["jsd"] <= js_q[0] and m["residual_std"] <= rs_q[0]:
            regime = "stable"
        elif m["share_wmape"] >= sw_q[1] or m["jsd"] >= js_q[1] or m["residual_std"] >= rs_q[1]:
            regime = "unstable"
        else:
            regime = "intermediate"
        out.append({**row, "stability_regime": regime, **{f"regime_{k}": round(v, 8) if isinstance(v, float) else v for k, v in m.items()}})
    return out


def oracle_results(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    thresholds = {sector: np.percentile([r["baseline"] for r in items], [10, 25, 50, 75, 90]) for (sector,), items in grouped(rows, ["sector_code"]).items()}
    enriched = []
    for row in assign_regimes(rows):
        enriched.append(
            {
                **row,
                "province_type": province_type(row["source_region"]),
                "size_bucket": size_bucket(row, thresholds),
            }
        )
    group_defs = {
        "sector_year": ["sector_code", "target_year"],
        "province_sector_year": ["source_region", "sector_code", "target_year"],
        "sector_size_year": ["sector_code", "size_bucket", "target_year"],
        "province_type_sector_year": ["province_type", "sector_code", "target_year"],
        "stability_regime_sector_year": ["stability_regime", "sector_code", "target_year"],
    }
    detail = []
    summary_rows = []
    for group_name, keys in group_defs.items():
        selected_rows = []
        for group_key, items in grouped(enriched, keys).items():
            candidates = []
            for alpha in ALPHAS:
                pred_rows = [{**r, "prediction": r["baseline"] * exp(alpha * r["ml_log_ratio"])} for r in items]
                candidates.append((alpha, wmape(pred_rows), pred_rows))
            best_alpha, best_wmape, best_rows = min(candidates, key=lambda x: x[1])
            base_w = wmape([{**r, "prediction": r["baseline"]} for r in items])
            ml_w = wmape([{**r, "prediction": r["ml_prediction"]} for r in items])
            gate_policy = "ml" if ml_w < base_w else "baseline"
            gate_rows = [{**r, "prediction": r["ml_prediction"] if gate_policy == "ml" else r["baseline"]} for r in items]
            capped_rows = []
            for r in items:
                capped = max(-0.03, min(0.03, r["ml_log_ratio"]))
                capped_rows.append({**r, "prediction": r["baseline"] * exp(capped)})
            capped_w = wmape(capped_rows)
            selected_rows.extend(best_rows)
            detail.append(
                {
                    "oracle_group": group_name,
                    **{field: value for field, value in zip(keys, group_key)},
                    "count": len(items),
                    "baseline_wmape": round(base_w, 6),
                    "ml_wmape": round(ml_w, 6),
                    "best_alpha": best_alpha,
                    "oracle_alpha_wmape": round(best_wmape, 6),
                    "oracle_alpha_improvement_pct": round(improvement(base_w, best_wmape), 6),
                    "oracle_gate_policy": gate_policy,
                    "oracle_gate_wmape": round(wmape(gate_rows), 6),
                    "oracle_capped_ml_wmape": round(capped_w, 6),
                }
            )
        base_all = wmape([{**r, "prediction": r["baseline"]} for r in enriched])
        oracle_all = wmape(selected_rows)
        best_alpha_zero_rate = mean([1.0 if d["best_alpha"] == 0 else 0.0 for d in detail if d["oracle_group"] == group_name])
        summary_rows.append(
            {
                "oracle_group": group_name,
                "count": len(selected_rows),
                "baseline_wmape": round(base_all, 6),
                "oracle_wmape": round(oracle_all, 6),
                "oracle_improvement_pct": round(improvement(base_all, oracle_all), 6),
                "best_alpha_zero_rate": round(best_alpha_zero_rate, 6),
                "ml_selected_group_rate": round(mean([1.0 if d["oracle_gate_policy"] == "ml" else 0.0 for d in detail if d["oracle_group"] == group_name]), 6),
            }
        )
    return detail, summary_rows


def regime_policy_results(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    enriched = assign_regimes(rows)
    disagreement_values = [abs(r["ml_log_ratio"]) for r in enriched]
    low_unc_threshold = float(np.percentile(disagreement_values, 33)) if disagreement_values else 0.0
    size_thresholds = {sector: np.percentile([r["baseline"] for r in items], 25) for (sector,), items in grouped(enriched, ["sector_code"]).items()}
    predictions = []
    for r in enriched:
        use_stable = r["stability_regime"] == "stable"
        use_intermediate = r["stability_regime"] in {"stable", "intermediate"}
        use_low_unc = abs(r["ml_log_ratio"]) <= low_unc_threshold
        use_large = r["baseline"] >= size_thresholds[r["sector_code"]]
        policies = {
            "baseline_all": r["baseline"],
            "ml_all": r["ml_prediction"],
            "ml_stable_only": r["ml_prediction"] if use_stable else r["baseline"],
            "ml_stable_intermediate": r["ml_prediction"] if use_intermediate else r["baseline"],
            "ml_low_uncertainty_only": r["ml_prediction"] if use_low_unc else r["baseline"],
            "ml_stable_large_cell_only": r["ml_prediction"] if use_stable and use_large else r["baseline"],
        }
        for policy, pred in policies.items():
            predictions.append(
                {
                    "policy": policy,
                    "source_region": r["source_region"],
                    "sigungu_code": r["sigungu_code"],
                    "sector_code": r["sector_code"],
                    "target_year": r["target_year"],
                    "stability_regime": r["stability_regime"],
                    "actual": round(r["actual"], 6),
                    "baseline": round(r["baseline"], 6),
                    "prediction": round(pred, 6),
                    "ml_selected": pred != r["baseline"],
                }
            )
    summary = summarize_policy(predictions, "policy")
    return predictions, summary


def dynamic_baseline_results(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # Forecast parent condition; share alternatives use only pre-target actual shares.
    predictions = []
    by_cell = grouped(rows, ["source_region", "sigungu_code", "sector_code"])
    hist_by_cell = {key: sorted(items, key=lambda r: r["target_year"]) for key, items in by_cell.items()}
    for row in rows:
        hist = [h for h in hist_by_cell[(row["source_region"], row["sigungu_code"], row["sector_code"])] if h["target_year"] < row["target_year"]]
        if not hist:
            continue
        shares = [h["actual_share"] for h in hist]
        candidates = {
            "last_share": shares[-1],
            "mean2_share": mean(shares[-2:]),
            "mean3_share": mean(shares[-3:]),
            "ewma_0_7_share": ewma(shares, 0.7),
            "ewma_0_4_share": ewma(shares, 0.4),
        }
        for model, share in candidates.items():
            predictions.append(
                {
                    "model": model,
                    "source_region": row["source_region"],
                    "sigungu_code": row["sigungu_code"],
                    "sector_code": row["sector_code"],
                    "target_year": row["target_year"],
                    "actual": round(row["actual"], 6),
                    "baseline": round(row["baseline"], 6),
                    "prediction": round(row["parent_forecast"] * share, 6),
                }
            )
    return predictions, summarize_policy(predictions, "model")


def ewma(values: list[float], lam: float) -> float:
    current = values[0]
    for value in values[1:]:
        current = lam * value + (1 - lam) * current
    return current


def summarize_policy(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    out = []
    for (name,), items in grouped(rows, [field]).items():
        normalized = [{**r, "actual": num(r["actual"]), "prediction": num(r["prediction"]), "baseline": num(r["baseline"])} for r in items]
        base_w = wmape([{**r, "prediction": r["baseline"]} for r in normalized])
        model_w = wmape(normalized)
        sy = [improvement(wmape([{**r, "prediction": r["baseline"]} for r in part]), wmape(part)) for _k, part in grouped(normalized, ["sector_code", "target_year"]).items()]
        out.append(
            {
                field: name,
                "count": len(items),
                "wmape": round(model_w, 6),
                "mape": round(mape(normalized), 6),
                "baseline_wmape": round(base_w, 6),
                "improvement_pct": round(improvement(base_w, model_w), 6),
                "material_degradation_count": sum(1 for v in sy if v < -2),
                "worst_sector_year_improvement": round(min(sy), 6) if sy else "",
                "ml_rate": round(mean([1.0 if r.get("ml_selected") else 0.0 for r in items]), 6) if items and "ml_selected" in items[0] else "",
            }
        )
    return sorted(out, key=lambda r: str(r[field]))


def write_reports(
    oracle_summary: list[dict[str, Any]],
    regime_summary: list[dict[str, Any]],
    dynamic_summary: list[dict[str, Any]],
    oracle_detail: list[dict[str, Any]],
) -> None:
    lines = ["# 시군구 Oracle Upper Bound", "", "## Oracle 단위별 전체 상한", ""]
    write_table(lines, oracle_summary, ["oracle_group", "count", "baseline_wmape", "oracle_wmape", "oracle_improvement_pct", "best_alpha_zero_rate", "ml_selected_group_rate"])
    lines.extend(["", "## 판단", ""])
    ps = next((r for r in oracle_summary if r["oracle_group"] == "province_sector_year"), None)
    if ps and float(ps["oracle_improvement_pct"]) < 1.0:
        lines.append("province×sector×year oracle 개선율이 1% 미만이므로 현재 ML residual에는 실용적으로 이용 가능한 신호가 부족하다.")
    else:
        lines.append("일부 oracle 단위에서 1% 이상 개선 가능성이 있으므로 제한적 후속 실험 여지가 있다.")
    (REPORT_DIR / "municipality_oracle_upper_bound.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 시군구 Share Stability Regime", "", "## Regime 정책 비교", ""]
    write_table(lines, regime_summary, ["policy", "count", "wmape", "mape", "baseline_wmape", "improvement_pct", "material_degradation_count", "worst_sector_year_improvement", "ml_rate"])
    lines.extend(["", "## 해석", "", "Stable group에만 ML을 적용해도 baseline을 이기지 못하면 share stability만으로는 현재 ML의 적용 대상을 충분히 선별하지 못한다."])
    (REPORT_DIR / "municipality_stability_regime.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 시군구 Dynamic Baseline", "", "## 과거 share smoothing 후보", ""]
    write_table(lines, dynamic_summary, ["model", "count", "wmape", "mape", "baseline_wmape", "improvement_pct", "material_degradation_count", "worst_sector_year_improvement"])
    lines.extend(["", "## 해석", "", "ML residual보다 baseline share 자체의 smoothing이 더 나은지 확인하기 위한 통계적 baseline 비교다."])
    (REPORT_DIR / "municipality_dynamic_baseline.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 시군구 Compositional Model", "", "이번 라운드의 oracle/regime 분석에서 현 ML residual의 실용 신호가 약하면 ALR/CLR/softmax 모델 구현은 보류한다.", "", "## 현재 판단", ""]
    if ps and float(ps["oracle_improvement_pct"]) < 1.0:
        lines.append("province×sector×year oracle 개선율이 1% 미만이므로 compositional regression 구현을 보류한다.")
    else:
        lines.append("oracle에서 일부 개선 여지가 있어 baseline-offset softmax를 다음 후보로 둘 수 있다.")
    (REPORT_DIR / "municipality_compositional_model.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 시군구 Small-cell 정책", "", "Small-cell 정책은 기존 `municipality_small_cell_analysis.md`의 구간별 악화 양상을 기준으로, actual이 아니라 baseline 또는 lagged share 기준으로만 적용해야 한다.", "", "## 현재 판단", "", "small-cell만 제외해도 C00, G00, L00의 중위 구간 악화는 남으므로 단독 해결책이 아니다."]
    (REPORT_DIR / "municipality_small_cell_policy.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# 시군구 Feature Feasibility", "", "## 우선 확보 후보", "", "| feature | source | region unit | industry unit | period | release lag | feasibility |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in feature_feasibility_rows():
        lines.append(f"| {row['feature']} | {row['source']} | {row['region_unit']} | {row['industry_unit']} | {row['period']} | {row['release_lag']} | {row['feasibility']} |")
    (REPORT_DIR / "municipality_feature_feasibility.md").write_text("\n".join(lines), encoding="utf-8")

    stop_lines = ["# 시군구 ML 보정 중단 판단", "", "## 실험 결과", ""]
    write_table(stop_lines, oracle_summary, ["oracle_group", "oracle_improvement_pct", "best_alpha_zero_rate"])
    stop_lines.extend(["", "## Baseline 유지 근거", "", "현재 데이터의 ML residual은 세분화 oracle에서도 개선 상한이 작고, share stability regime만으로 적용 대상을 안정적으로 선별하지 못한다면 시군구 운영은 baseline을 유지한다.", "", "## 권장 운영", "", "- 시도×산업: locked global policy 유지", "- 시군구×산업: Denton/indicator baseline 유지", "- 읍면동×산업: proxy 배분과 confidence grade만 제공"])
    (REPORT_DIR / "municipality_ml_stop_decision.md").write_text("\n".join(stop_lines), encoding="utf-8")


def feature_feasibility_rows() -> list[dict[str, str]]:
    return [
        {"feature": "시군구×산업 종사자 수", "source": "전국사업체조사/KOSIS", "region_unit": "시군구", "industry_unit": "KSIC", "period": "연간", "release_lag": "약 1년 이상", "feasibility": "high"},
        {"feature": "시군구×산업 사업체 수", "source": "전국사업체조사/KOSIS", "region_unit": "시군구", "industry_unit": "KSIC", "period": "연간", "release_lag": "약 1년 이상", "feasibility": "high"},
        {"feature": "종사자 규모별 사업체 수", "source": "전국사업체조사/MDIS 또는 KOSIS", "region_unit": "시군구", "industry_unit": "KSIC", "period": "연간", "release_lag": "약 1년 이상", "feasibility": "medium"},
        {"feature": "산업단지 생산·수출·고용", "source": "산업단지공단/공공데이터", "region_unit": "산단/시군구 매핑", "industry_unit": "제조 중심", "period": "월/분기/연", "release_lag": "자료별 상이", "feasibility": "medium"},
        {"feature": "건축허가·착공 면적", "source": "국토교통부/KOSIS", "region_unit": "시군구", "industry_unit": "건설 proxy", "period": "월간", "release_lag": "짧음", "feasibility": "high"},
        {"feature": "전력 판매량", "source": "전력데이터개방포털/KEPCO", "region_unit": "시군구 가능성 확인 필요", "industry_unit": "용도별", "period": "월간", "release_lag": "짧음", "feasibility": "medium"},
        {"feature": "학교·학생·교직원", "source": "교육통계/KOSIS", "region_unit": "시군구", "industry_unit": "교육 proxy", "period": "연간", "release_lag": "약 1년", "feasibility": "high"},
        {"feature": "부동산 거래·건축물 연면적", "source": "국토교통부/건축데이터", "region_unit": "시군구", "industry_unit": "부동산 proxy", "period": "월/연", "release_lag": "짧음~중간", "feasibility": "medium"},
    ]


def write_table(lines: list[str], rows: list[dict[str, Any]], columns: list[str]) -> None:
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" if col in {"oracle_group", "policy", "model"} else "---:" for col in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")


def main() -> int:
    rows = load_rows()
    oracle_detail, oracle_summary = oracle_results(rows)
    regime_predictions, regime_summary = regime_policy_results(rows)
    dynamic_predictions, dynamic_summary = dynamic_baseline_results(rows)
    write_csv(PROCESSED_DIR / "municipality_oracle_results.csv", oracle_detail)
    write_csv(PROCESSED_DIR / "municipality_oracle_summary.csv", oracle_summary)
    write_csv(PROCESSED_DIR / "municipality_regime_predictions.csv", regime_predictions)
    write_csv(PROCESSED_DIR / "municipality_regime_results.csv", regime_summary)
    write_csv(PROCESSED_DIR / "municipality_dynamic_baseline_predictions.csv", dynamic_predictions)
    write_csv(PROCESSED_DIR / "municipality_dynamic_baseline_results.csv", dynamic_summary)
    # No compositional prediction is generated when the oracle stop criterion is met.
    write_csv(PROCESSED_DIR / "municipality_compositional_predictions.csv", [])
    write_csv(PROCESSED_DIR / "municipality_small_cell_results.csv", read_csv(PROCESSED_DIR / "municipality_size_bin_results.csv"))
    write_reports(oracle_summary, regime_summary, dynamic_summary, oracle_detail)
    print(f"oracle groups: {len(oracle_detail)}")
    print(f"regime predictions: {len(regime_predictions)}")
    print(f"dynamic predictions: {len(dynamic_predictions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
