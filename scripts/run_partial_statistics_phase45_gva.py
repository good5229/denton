from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from run_partial_statistics_phase42_gva import (
    accounting, build_cube, current_group_shares, hierarchy_prior, monthly_controls, multiresolution, spatial_shares,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase45_gva.md"


def employee_weighted_groups(groups: pd.DataFrame) -> pd.DataFrame:
    out = groups.copy()
    seed = out.employees + .01
    out["group_share_within_parent"] = seed / seed.groupby(out.gva_parent_code).transform("sum")
    out["group_share_within_division"] = seed / seed.groupby(out.division_code).transform("sum")
    return out


def common_proxy_audit(base: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for section, frame in base.groupby("section_code"):
        pivot = frame.pivot_table(index="group_code", columns=["period", "emd_code"], values="estimated_emd_group_monthly_gva", aggfunc="sum", fill_value=0)
        normalized = pivot.div(pivot.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
        hashes = normalized.round(11).astype(str).agg("|".join, axis=1)
        rows.append({"section_code": section, "small_industries": len(pivot), "unique_spatiotemporal_profiles": hashes.nunique(), "identical_profile_rate": float(hashes.duplicated(False).mean()), "effective_rank": int(np.linalg.matrix_rank(normalized.to_numpy(), tol=1e-10))})
    return pd.DataFrame(rows)


def final_diagnostics() -> pd.DataFrame:
    industry = pd.read_csv(DATA / "partial_stats_phase44_pohang_industry_weight_cv_detail.csv", encoding="utf-8-sig", dtype={"industry_code": str})
    industry = industry[industry.industry_level.eq("중분류")].groupby(["industry_code", "industry_name"], as_index=False).abs_error_pp.mean().rename(columns={"abs_error_pp": "industry_cv_mae_pp"})
    spatial = pd.read_csv(DATA / "partial_stats_phase43_pohang_spatial_cv_summary.csv", encoding="utf-8-sig", dtype={"division_code": str})
    spatial = spatial[["division_code", "division_name", "cv_mae_pp"]].rename(columns={"division_code": "industry_code", "division_name": "industry_name", "cv_mae_pp": "spatial_cv_mae_pp"})
    gu = pd.read_csv(DATA / "partial_stats_phase43_pohang_gu_sales_cv_detail.csv", encoding="utf-8-sig", dtype={"division_code": str})
    gu = gu.groupby(["division_code", "division_name"], as_index=False).cv_abs_error_pp.mean().rename(columns={"division_code": "industry_code", "division_name": "industry_name", "cv_abs_error_pp": "gu_sales_cv_mae_pp"})
    out = industry.merge(spatial, on=["industry_code", "industry_name"], how="outer").merge(gu, on=["industry_code", "industry_name"], how="outer")
    out["combined_cv_score_pp"] = out[["industry_cv_mae_pp", "spatial_cv_mae_pp", "gu_sales_cv_mae_pp"]].mean(axis=1)
    complete = out[["industry_cv_mae_pp", "spatial_cv_mae_pp", "gu_sales_cv_mae_pp"]].notna().all(axis=1)
    out["prediction_group"] = "검증 일부"
    out.loc[complete, "prediction_group"] = pd.qcut(out.loc[complete, "combined_cv_score_pp"].rank(method="first"), 3, labels=["예측 양호", "예측 보통", "예측 취약"]).astype(str)
    return out.sort_values("combined_cv_score_pp")


def main() -> dict[str, object]:
    groups, divisions = hierarchy_prior(); groups = employee_weighted_groups(groups)
    controls = monthly_controls(); shares = current_group_shares(groups); space = spatial_shares(divisions)
    base = build_cube(controls, shares, space); multi = multiresolution(base); checks = accounting(base, controls)
    common = common_proxy_audit(base); diagnostics = final_diagnostics()
    s43 = json.loads((DATA / "partial_stats_phase43_pohang_status.json").read_text()); s44 = json.loads((DATA / "partial_stats_phase44_pohang_status.json").read_text())
    status = {"sections": int(base.section_code.nunique()), "divisions": int(base.division_code.nunique()), "groups": int(base.group_code.nunique()), "emd": int(base.emd_code.nunique()), "months": int(base.period.nunique()), "middle_industry_cv_mae_pp": s44["middle_cv_mae_pp"], "small_industry_cv_mae_pp": s44["small_cv_mae_pp"], "spatial_cv_mae_pp": s43["improved_spatial_cv_mae_pp"], "gu_sales_cv_mae_pp": s43["improved_gu_sales_cv_mae_pp"], "accounting_max_abs_error": float(checks.max_abs_error.max()), "full_replication_sections": int((common.identical_profile_rate == 1).sum()), "base_rows": len(base), "cube_rows": len(multi), "final_decision": "포항 개발통계 최종 후보; 중분류 공간·산업 교차검증 가능, 읍면동 소분류 월 actual 부재"}
    base.to_parquet(DATA / "partial_stats_phase45_pohang_final_emd_small_monthly.parquet", index=False)
    multi.to_parquet(DATA / "partial_stats_phase45_pohang_final_multiresolution_cube.parquet", index=False)
    checks.to_csv(DATA / "partial_stats_phase45_pohang_final_accounting.csv", index=False, encoding="utf-8-sig")
    common.to_csv(DATA / "partial_stats_phase45_pohang_final_common_proxy_audit.csv", index=False, encoding="utf-8-sig")
    diagnostics.to_csv(DATA / "partial_stats_phase45_pohang_final_industry_diagnostics.csv", index=False, encoding="utf-8-sig")
    (DATA / "partial_stats_phase45_pohang_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(f"""# 포항시 전 산업 읍면동 월간 GVA 최종 통합 실험

## 최종 결과

29개 행정 읍면동, 19개 대분류, 74개 중분류, 228개 소분류, 2021~2023년 36개월의 최종 개발통계 큐브를 생성했다. 산업배분은 상위산업 제외 검증에서 선택된 포항 종사자 가중치를 적용했고, 서비스 세부산업은 분기 생산지수로 갱신했다.

- 산업 매출비중 홀드아웃 MAE: 중분류 **{status['middle_industry_cv_mae_pp']:.3f}%p**, 소분류 **{status['small_industry_cv_mae_pp']:.3f}%p**
- 읍면동 산업분포 중첩교차검증 MAE: **{status['spatial_cv_mae_pp']:.3f}%p**
- 남·북구 산업매출 leave-one-industry-out MAE: **{status['gu_sales_cv_mae_pp']:.3f}%p**
- 산업·시간·공간 재집계 최대오차: **{status['accounting_max_abs_error']:.3e}백만원**
- 공통 시공간 프로필 100% 복제 대분류: **{status['full_replication_sections']}개**

## 해석

산업, 공간, 차년도 구 매출의 actual을 서로 다른 검증축으로 사용했고, 상위합계 일치는 별도의 회계검사로만 처리했다. 따라서 0에 가까운 재집계 오차를 예측정확도로 주장하지 않는다. 최종 산업별 양호·보통·취약 판정은 세 홀드아웃 오차가 모두 존재하는 중분류만 대상으로 한다.

## 남은 한계

읍면동×소분류×월 실제 GVA는 존재하지 않는다. 2015 산업구조, 2023 읍면동 사업체분포, 2024 구 매출 사이의 시차와 매출·GVA 개념 차이도 남는다. 결과는 공식통계가 아니라 현장확인 후보를 좁히는 개발통계로 사용한다.
""", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2)); return status


if __name__ == "__main__":
    main()
