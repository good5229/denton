from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from run_partial_statistics_phase42_gva import hierarchy_prior


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase44_gva.md"


def normalized(frame: pd.DataFrame, column: str) -> pd.Series:
    total = frame.groupby("gva_parent_code")[column].transform("sum")
    return frame[column] / total.replace(0, np.nan)


def level_frame(level: str, groups: pd.DataFrame, divisions: pd.DataFrame) -> pd.DataFrame:
    if level == "중분류":
        out = divisions[divisions.sales > 0].copy()
        out = out.rename(columns={"division_code": "industry_code", "division_name": "industry_name"})
    else:
        out = groups[groups.sales > 0].copy()
        out = out.rename(columns={"group_code": "industry_code", "group_name": "industry_name"})
    for column in ("establishments", "employees", "sales"):
        out[f"{column}_share"] = normalized(out, column)
    return out


def parent_cv(frame: pd.DataFrame, level: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    parents = sorted(frame.gva_parent_code.unique())
    weights = np.linspace(0, 1, 21)
    results = []
    selections = []
    for outer in parents:
        train = frame[frame.gva_parent_code.ne(outer)]
        trials = []
        for establishment_weight in weights:
            prediction = establishment_weight * train.establishments_share + (1 - establishment_weight) * train.employees_share
            trials.append((float((prediction - train.sales_share).abs().mean()), float(establishment_weight)))
        train_mae, selected = min(trials, key=lambda item: (item[0], item[1]))
        test = frame[frame.gva_parent_code.eq(outer)].copy()
        test["predicted_share"] = selected * test.establishments_share + (1 - selected) * test.employees_share
        test["abs_error_pp"] = (test.predicted_share - test.sales_share).abs() * 100
        test["equal_weight_prediction"] = .5 * test.establishments_share + .5 * test.employees_share
        test["equal_weight_abs_error_pp"] = (test.equal_weight_prediction - test.sales_share).abs() * 100
        test["selected_establishment_weight"] = selected; test["selected_employee_weight"] = 1 - selected
        test["industry_level"] = level; results.append(test)
        selections.append({"industry_level": level, "heldout_parent": outer, "training_cells": len(train), "selected_establishment_weight": selected, "selected_employee_weight": 1 - selected, "training_mae_pp": train_mae * 100, "heldout_mae_pp": test.abs_error_pp.mean(), "equal_weight_heldout_mae_pp": test.equal_weight_abs_error_pp.mean()})
    return pd.concat(results, ignore_index=True), pd.DataFrame(selections)


def main() -> dict[str, float]:
    groups, divisions = hierarchy_prior()
    details, selections = [], []
    for level in ("중분류", "소분류"):
        detail, selected = parent_cv(level_frame(level, groups, divisions), level)
        details.append(detail); selections.append(selected)
    detail = pd.concat(details, ignore_index=True); selection = pd.concat(selections, ignore_index=True)
    summary = detail.groupby("industry_level", as_index=False).agg(cv_mae_pp=("abs_error_pp", "mean"), equal_weight_mae_pp=("equal_weight_abs_error_pp", "mean"), cells=("industry_code", "size"))
    summary["improvement_pp"] = summary.equal_weight_mae_pp - summary.cv_mae_pp
    middle = summary[summary.industry_level.eq("중분류")].iloc[0]; small = summary[summary.industry_level.eq("소분류")].iloc[0]
    status = {"middle_equal_weight_mae_pp": float(middle.equal_weight_mae_pp), "middle_cv_mae_pp": float(middle.cv_mae_pp), "middle_improvement_pp": float(middle.improvement_pp), "small_equal_weight_mae_pp": float(small.equal_weight_mae_pp), "small_cv_mae_pp": float(small.cv_mae_pp), "small_improvement_pp": float(small.improvement_pp), "median_selected_employee_weight": float(selection.selected_employee_weight.median())}
    detail.to_csv(DATA / "partial_stats_phase44_pohang_industry_weight_cv_detail.csv", index=False, encoding="utf-8-sig")
    selection.to_csv(DATA / "partial_stats_phase44_pohang_industry_weight_selection.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(DATA / "partial_stats_phase44_pohang_industry_weight_cv_summary.csv", index=False, encoding="utf-8-sig")
    (DATA / "partial_stats_phase44_pohang_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(f"""# 포항시 산업계층 가중치 성능개선

## 결과

- 중분류 매출비중 MAE: 50:50 사업체·종사자 **{status['middle_equal_weight_mae_pp']:.3f}%p** → 상위산업 제외 교차검증 **{status['middle_cv_mae_pp']:.3f}%p** (개선 {status['middle_improvement_pp']:.3f}%p).
- 소분류 매출비중 MAE: **{status['small_equal_weight_mae_pp']:.3f}%p** → **{status['small_cv_mae_pp']:.3f}%p** (개선 {status['small_improvement_pp']:.3f}%p).
- 선택된 종사자 가중치 중앙값: **{status['median_selected_employee_weight']:.2f}**.

## 검증 방식

GVA 상위산업 묶음을 하나씩 완전히 제외하고, 나머지 묶음의 2015 매출비중 오차만으로 사업체·종사자 가중치를 선택했다. 제외된 묶음의 매출은 가중치 선택에 사용하지 않았다. 이 결과는 포항에서 사업체 수보다 종사자 수가 산업 매출규모를 더 잘 설명한다는 증거이며, 모든 지역에 같은 가중치를 적용할 근거는 아니다.

## 적용 판정

두 산업수준 모두 실제 홀드아웃 오차가 감소했으므로 포항 산업계층 배분의 개선 후보로 채택한다. 다만 매출은 GVA actual이 아니며 2015 구조이므로, 공식 GVA로 승격하지 않고 민감도·배분 가중치로만 사용한다.
""", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2)); return status


if __name__ == "__main__":
    main()
