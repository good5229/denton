# Reconciled ML 후속 안정성 검증

## 요약

- 평가 모델: `xgboost_log_ratio_reconciled`
- 전체 baseline WMAPE: `4.388658`%
- 전체 model WMAPE: `4.230372`%
- 전체 개선율: `3.606707`%
- 개선 연도 수: `5/5`
- 최대 개선 연도: `2020` (5.058946%)
- 최대 악화 연도: `2022` (2.442246%)

## Bootstrap

| unit | mean delta WMAPE | median | 95% low | 95% high | P(model better) |
| --- | ---: | ---: | ---: | ---: | ---: |
| target_year_sector_parent | 0.156886 | 0.1553 | 0.02152 | 0.295924 | 0.987 |
| region | 0.139742 | 0.152398 | -0.114385 | 0.298151 | 0.901 |
| target_year_block | 0.158034 | 0.15747 | 0.127916 | 0.191782 | 1.0 |

## Leave-One-Year-Out

| excluded year | baseline WMAPE | model WMAPE | improvement % |
| --- | ---: | ---: | ---: |
| 2019 | 4.655235 | 4.484468 | 3.668289 |
| 2020 | 4.378315 | 4.235616 | 3.259231 |
| 2021 | 4.482758 | 4.327141 | 3.471468 |
| 2022 | 3.986594 | 3.824857 | 4.05704 |
| 2023 | 4.435584 | 4.274857 | 3.62357 |

## 산업별 채택 등급

| sector | selected model | grade | avg improvement | improved year ratio | recent improved years | bootstrap P | reason |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| A00 | baseline | D | -12.988994 | 0.2 | 1 | 0.101 | avg=fail; ratio=fail; recent=fail; worst=fail; bootstrap=fail |
| B00 | xgboost_log_ratio_reconciled | A | 15.310062 | 1.0 | 2 | 1.0 | avg=pass; ratio=pass; recent=pass; worst=pass; bootstrap=pass |
| C00 | baseline_and_xgboost_log_ratio_reconciled | B | 5.859465 | 0.8 | 1 | 0.892 | avg=pass; ratio=pass; recent=fail; worst=pass; bootstrap=pass |
| D00 | baseline | D | -13.804916 | 0.2 | 0 | 0.011 | avg=fail; ratio=fail; recent=fail; worst=fail; bootstrap=fail |
| ERS | baseline | C | 0.466626 | 0.6 | 0 | 0.85 | avg=fail; ratio=pass; recent=fail; worst=pass; bootstrap=pass |
| F00 | xgboost_log_ratio_reconciled | A | 12.347165 | 1.0 | 2 | 1.0 | avg=pass; ratio=pass; recent=pass; worst=pass; bootstrap=pass |
| G00 | xgboost_log_ratio_reconciled | A | 2.579108 | 0.8 | 2 | 0.869 | avg=pass; ratio=pass; recent=pass; worst=pass; bootstrap=pass |
| H00 | baseline | D | -3.639295 | 0.2 | 0 | 0.003 | avg=fail; ratio=fail; recent=fail; worst=pass; bootstrap=fail |
| I00 | baseline | C | 0.163655 | 0.6 | 0 | 0.593 | avg=fail; ratio=pass; recent=fail; worst=pass; bootstrap=fail |
| J00 | baseline | D | -0.900094 | 0.4 | 1 | 0.372 | avg=fail; ratio=fail; recent=fail; worst=fail; bootstrap=fail |
| K00 | baseline | C | 0.423735 | 0.6 | 1 | 0.647 | avg=fail; ratio=pass; recent=fail; worst=pass; bootstrap=pass |
| L00 | xgboost_log_ratio_reconciled | A | 6.112672 | 1.0 | 2 | 1.0 | avg=pass; ratio=pass; recent=pass; worst=pass; bootstrap=pass |
| MN0 | baseline | C | 2.210076 | 0.8 | 2 | 0.575 | avg=pass; ratio=pass; recent=pass; worst=fail; bootstrap=fail |
| O00 | baseline_and_xgboost_log_ratio_reconciled | B | 8.701634 | 0.8 | 1 | 1.0 | avg=pass; ratio=pass; recent=fail; worst=pass; bootstrap=pass |
| P00 | xgboost_log_ratio_reconciled | A | 4.442928 | 1.0 | 2 | 1.0 | avg=pass; ratio=pass; recent=pass; worst=pass; bootstrap=pass |
| Q00 | baseline | D | -3.439005 | 0.4 | 1 | 0.076 | avg=fail; ratio=fail; recent=fail; worst=fail; bootstrap=fail |

## 해석

전체 평균 개선만으로 ML을 전면 채택하지 않는다. 산업별 등급은 평균 개선율, 개선 연도 비율, 최근 연도 개선 지속성, 최악 연도 악화폭, bootstrap 안정성을 함께 본다. `A/B`가 아닌 산업은 기본 산출에서 baseline을 유지하고 ML은 참고값으로만 둔다.

상세 표는 `data/processed/reconciled_model_*` 안정성 CSV에 저장된다.