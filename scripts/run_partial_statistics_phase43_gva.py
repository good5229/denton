from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase43_gva.md"


def normalize_name(value: object) -> str:
    return re.sub(r"[^가-힣A-Za-z0-9]", "", str(value)).replace("외1종", "")


def map_factories() -> tuple[pd.DataFrame, pd.DataFrame]:
    factory = pd.read_csv(DATA / "partial_stats_phase42_pohang_factory_snapshot.csv", dtype={"emd_code": str})
    registry = pd.read_csv(DATA / "ksic10_official_registry.csv", encoding="cp949", dtype=str)
    names = registry[["division_code", "name"]].dropna().drop_duplicates().copy()
    names["normalized"] = names.name.map(normalize_name)
    exact = names.drop_duplicates("normalized").set_index("normalized").division_code.to_dict()
    candidates = names.to_records(index=False)
    cache: dict[str, tuple[str | None, float, str]] = {}
    for raw in factory["업종명"].fillna("").unique():
        primary = re.split(r"\s+외\s+\d+\s*종", str(raw))[0]
        key = normalize_name(primary)
        if key in exact:
            cache[str(raw)] = (exact[key], 1.0, "official_name_exact")
            continue
        best_code, best_score = None, 0.0
        for division, _name, normalized in candidates:
            score = difflib.SequenceMatcher(None, key, normalized).ratio()
            if score > best_score:
                best_code, best_score = str(division).zfill(2), score
        cache[str(raw)] = (best_code if best_score >= .68 else None, best_score, "official_name_fuzzy_0.68")
    mapped = factory.copy()
    mapped[["division_code", "name_match_score", "name_match_method"]] = mapped["업종명"].fillna("").map(cache).apply(pd.Series)
    mapped["matched_for_spatial_model"] = mapped.emd_code.notna() & mapped.division_code.notna()
    audit = pd.DataFrame([{
        "factory_rows": len(mapped), "emd_matched_rows": int(mapped.emd_code.notna().sum()),
        "industry_matched_rows": int(mapped.division_code.notna().sum()), "both_matched_rows": int(mapped.matched_for_spatial_model.sum()),
        "both_match_rate": float(mapped.matched_for_spatial_model.mean()), "minimum_fuzzy_score": .68,
    }])
    return mapped, audit


def enriched_spatial_inputs(mapped_factory: pd.DataFrame) -> pd.DataFrame:
    detail = pd.read_csv(DATA / "partial_stats_phase42_pohang_spatial_proxy_holdout_detail.csv", encoding="utf-8-sig", dtype={"division_code": str, "emd_code": str})
    counts = mapped_factory[mapped_factory.matched_for_spatial_model].groupby(["division_code", "emd_code"], as_index=False).size().rename(columns={"size": "division_factory_count"})
    counts["division_factory_share"] = (counts.division_factory_count + .01) / counts.groupby("division_code").division_factory_count.transform(lambda x: x.sum() + .01 * detail.emd_code.nunique())
    out = detail.merge(counts[["division_code", "emd_code", "division_factory_share"]], on=["division_code", "emd_code"], how="left")
    manufacturing = out.section_code.eq("C") & out.groupby("division_code").division_factory_share.transform("count").gt(0)
    out.loc[manufacturing, "special_share"] = out.loc[manufacturing, "division_factory_share"].fillna(0)
    total = out.groupby("division_code").special_share.transform("sum")
    out.loc[manufacturing, "special_share"] = out.loc[manufacturing, "special_share"] / total[manufacturing]
    out["enriched_special_source"] = np.where(manufacturing, "업종명 매칭 공장분포", out.proxy_source)
    out["special_share"] = out.special_share.fillna(out.population_share)
    return out


def centroid(data: pd.DataFrame, train_codes: set[str], target_section: str) -> pd.Series:
    same = data[data.division_code.isin(train_codes) & data.section_code.eq(target_section)]
    if same.division_code.nunique() == 0:
        same = data[data.division_code.isin(train_codes)]
    return same.groupby("emd_code").actual_share.mean()


def predict(data: pd.DataFrame, division: str, train_codes: set[str], weights: tuple[float, float, float]) -> pd.DataFrame:
    target = data[data.division_code.eq(division)].copy()
    section = target.section_code.iat[0]
    center = centroid(data, train_codes, section)
    target["centroid_share"] = target.emd_code.map(center).fillna(target.population_share)
    wc, ws, wp = weights
    target["cv_predicted_share"] = wc * target.centroid_share + ws * target.special_share + wp * target.population_share
    target["cv_predicted_share"] /= target.cv_predicted_share.sum()
    return target


def nested_spatial_cv(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    codes = sorted(data.division_code.unique())
    candidates = [(wc / 10, ws / 10, 1 - (wc + ws) / 10) for wc in range(11) for ws in range(11 - wc)]
    outputs = []
    for outer in codes:
        training = [code for code in codes if code != outer]
        scores = []
        # Deterministic nested validation: every fifth training division covers all sections while limiting runtime.
        inner_codes = training[::5]
        for weights in candidates:
            errors = []
            for inner in inner_codes:
                inner_train = set(training) - {inner}
                trial = predict(data, inner, inner_train, weights)
                errors.append((trial.cv_predicted_share - trial.actual_share).abs().mean())
            scores.append((float(np.mean(errors)), weights))
        best_error, best = min(scores, key=lambda item: item[0])
        result = predict(data, outer, set(training), best)
        result["outer_division"] = outer; result["centroid_weight"] = best[0]; result["special_weight"] = best[1]; result["population_weight"] = best[2]; result["inner_cv_mae"] = best_error
        outputs.append(result)
    detail = pd.concat(outputs, ignore_index=True)
    detail["cv_abs_error_pp"] = (detail.cv_predicted_share - detail.actual_share).abs() * 100
    summary = detail.groupby(["section_code", "division_code", "division_name", "enriched_special_source"], as_index=False).agg(
        cv_mae_pp=("cv_abs_error_pp", "mean"), baseline_mae_pp=("abs_error_pp", "mean"), population_mae_pp=("population_abs_error_pp", "mean"),
        centroid_weight=("centroid_weight", "first"), special_weight=("special_weight", "first"), population_weight=("population_weight", "first"),
    )
    summary["improvement_vs_baseline_pp"] = summary.baseline_mae_pp - summary.cv_mae_pp
    return detail, summary


def gu_cross_industry_cv() -> tuple[pd.DataFrame, pd.DataFrame]:
    gu = pd.read_csv(DATA / "partial_stats_phase42_pohang_gu_2024_holdout.csv", encoding="utf-8-sig", dtype={"division_code": str})
    south = gu[gu.general_gu.eq("남구")].copy().sort_values("division_code")
    eps = 1e-4
    x_est = np.clip(south.establishments_share.to_numpy(), eps, 1 - eps)
    x_emp = np.clip(south.employees_share.to_numpy(), eps, 1 - eps)
    y = np.clip(south.sales_share.to_numpy(), eps, 1 - eps)
    logit_x = np.column_stack([np.log(x_est / (1 - x_est)), np.log(x_emp / (1 - x_emp))]); logit_y = np.log(y / (1 - y))
    predictions = []
    for i in range(len(south)):
        train = np.arange(len(south)) != i
        design = np.column_stack([np.ones(train.sum()), logit_x[train]])
        ridge = np.diag([1e-8, .2, .2])
        beta = np.linalg.solve(design.T @ design + ridge, design.T @ logit_y[train])
        fitted = beta[0] + logit_x[i] @ beta[1:]
        predictions.append(1 / (1 + np.exp(-fitted)))
    south["cv_predicted_sales_share"] = predictions
    south["cv_abs_error_pp"] = (south.cv_predicted_sales_share - south.sales_share).abs() * 100
    summary = pd.DataFrame([{
        "validation": "2024 division leave-one-out; other industries train logit sales share from contemporaneous establishments+employees",
        "divisions": len(south), "baseline_mae_pp": south.sales_abs_error_pp.mean(), "cv_calibrated_mae_pp": south.cv_abs_error_pp.mean(),
        "improvement_pp": south.sales_abs_error_pp.mean() - south.cv_abs_error_pp.mean(),
    }])
    return south, summary


def common_proxy_audit(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for section, group in detail.groupby("section_code"):
        matrix = group.pivot(index="division_code", columns="emd_code", values="cv_predicted_share").fillna(0)
        hashes = matrix.round(12).astype(str).agg("|".join, axis=1)
        rows.append({"section_code": section, "divisions": len(matrix), "unique_spatial_profiles": hashes.nunique(), "identical_profile_rate": float(hashes.duplicated(False).mean()), "effective_rank": int(np.linalg.matrix_rank(matrix.to_numpy(), tol=1e-10))})
    return pd.DataFrame(rows)


def main() -> dict[str, float]:
    mapped, factory_audit = map_factories(); enriched = enriched_spatial_inputs(mapped)
    spatial_detail, spatial_summary = nested_spatial_cv(enriched); gu_detail, gu_summary = gu_cross_industry_cv(); common = common_proxy_audit(spatial_detail)
    status = {
        "factory_both_match_rate": float(factory_audit.both_match_rate.iat[0]),
        "baseline_spatial_mae_pp": float(spatial_detail.abs_error_pp.mean()), "improved_spatial_cv_mae_pp": float(spatial_detail.cv_abs_error_pp.mean()),
        "spatial_improvement_pp": float(spatial_detail.abs_error_pp.mean() - spatial_detail.cv_abs_error_pp.mean()),
        "baseline_gu_sales_mae_pp": float(gu_summary.baseline_mae_pp.iat[0]), "improved_gu_sales_cv_mae_pp": float(gu_summary.cv_calibrated_mae_pp.iat[0]),
        "gu_sales_improvement_pp": float(gu_summary.improvement_pp.iat[0]), "full_replication_sections": int((common.identical_profile_rate == 1).sum()),
    }
    mapped.to_csv(DATA / "partial_stats_phase43_pohang_factory_industry_mapping.csv", index=False, encoding="utf-8-sig")
    factory_audit.to_csv(DATA / "partial_stats_phase43_pohang_factory_mapping_audit.csv", index=False, encoding="utf-8-sig")
    spatial_detail.to_csv(DATA / "partial_stats_phase43_pohang_spatial_cv_detail.csv", index=False, encoding="utf-8-sig")
    spatial_summary.to_csv(DATA / "partial_stats_phase43_pohang_spatial_cv_summary.csv", index=False, encoding="utf-8-sig")
    gu_detail.to_csv(DATA / "partial_stats_phase43_pohang_gu_sales_cv_detail.csv", index=False, encoding="utf-8-sig")
    gu_summary.to_csv(DATA / "partial_stats_phase43_pohang_gu_sales_cv_summary.csv", index=False, encoding="utf-8-sig")
    common.to_csv(DATA / "partial_stats_phase43_pohang_common_proxy_audit.csv", index=False, encoding="utf-8-sig")
    (DATA / "partial_stats_phase43_pohang_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(f"""# 포항시 시공간 GVA 성능개선 실험

## 결과

- 공장 1,465건 중 행정 읍면동과 KSIC 중분류를 모두 연결한 비율: **{status['factory_both_match_rate']:.1%}**.
- 읍면동×산업중분류 공간 MAE: 고정 프록시 **{status['baseline_spatial_mae_pp']:.3f}%p** → 산업 제외 중첩교차검증 혼합모형 **{status['improved_spatial_cv_mae_pp']:.3f}%p** (개선 {status['spatial_improvement_pp']:.3f}%p).
- 남·북구 매출비중 MAE: 2023 공간구조 직접외삽 **{status['baseline_gu_sales_mae_pp']:.3f}%p** → 동시점 사업체·종사자 기반 산업 제외 로짓 보정 **{status['improved_gu_sales_cv_mae_pp']:.3f}%p** (개선 {status['gu_sales_improvement_pp']:.3f}%p).
- 동일 공간프로필 100% 복제 대분류: **{status['full_replication_sections']}개**.

## 방법

공장 업종명을 KSIC 공식 세세분류명에 정확·유사도 매칭해 제조업 중분류별 공장분포를 만들었다. 공간모형은 인구, 해당 산업 공장·인허가, 같은 대분류의 다른 산업 actual 공간중심을 혼합한다. 각 산업을 완전히 제외한 바깥 검증과, 남은 산업에서 가중치를 고르는 안쪽 검증을 분리했다. 구 매출 보정은 목표 산업의 매출을 보지 않고 다른 산업의 동시점 사업체·종사자와 매출 관계만 학습하는 leave-one-industry-out이다.

## 판정

개선치는 상위합계 강제 일치가 아니라 실제 홀드아웃 오차 감소다. 다만 ‘다른 산업의 공간분포’를 쓰는 접근은 공통 프록시 복제 위험이 있으므로 대분류별 고유 프로필 수와 유효랭크를 함께 공개한다. 월·소분류 actual 부재는 여전히 해소되지 않았다.
""", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2)); return status


if __name__ == "__main__":
    main()
