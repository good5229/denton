# Reconciled ML 후속 검증 및 안전장치 보고서

## 1. 목적

이 보고서는 `Denton/indicator baseline + ML log-ratio residual + parent reconciliation` 구조가 운영 모델로 사용할 만큼 안정적인지 추가 검증한 결과를 정리한다. 전체 WMAPE 개선만으로 ML을 전면 채택하지 않고, 연도별·산업별·지역별 안정성, bootstrap, 산업별 confidence rule, shrinkage/blending 안전장치를 함께 확인했다.

## 2. 안정성 검증 결과

평가 모델은 `xgboost_log_ratio_reconciled`다.

| 항목 | 값 |
| --- | ---: |
| 전체 baseline WMAPE | 4.388658% |
| 전체 model WMAPE | 4.230372% |
| 전체 개선율 | 3.606707% |
| 개선 연도 수 | 5/5 |
| 최대 개선 연도 | 2020, 5.058946% |
| 최소 개선 연도 | 2022, 2.442246% |

Leave-one-year-out 분석에서도 특정 연도 하나를 제외했을 때 개선율이 0 이하로 떨어지지 않았다.

| 제외 연도 | baseline WMAPE | model WMAPE | 개선율 |
| --- | ---: | ---: | ---: |
| 2019 | 4.655235 | 4.484468 | 3.668289% |
| 2020 | 4.378315 | 4.235616 | 3.259231% |
| 2021 | 4.482758 | 4.327141 | 3.471468% |
| 2022 | 3.986594 | 3.824857 | 4.057040% |
| 2023 | 4.435584 | 4.274857 | 3.623570% |

## 3. Bootstrap 결과

| 재표집 단위 | 평균 ΔWMAPE | 95% CI low | 95% CI high | P(model better) |
| --- | ---: | ---: | ---: | ---: |
| target year × sector parent | 0.156886 | 0.021520 | 0.295924 | 0.987 |
| region | 0.139742 | -0.114385 | 0.298151 | 0.901 |
| target year block | 0.158034 | 0.127916 | 0.191782 | 1.000 |

parent group 및 year block 기준에서는 신뢰구간 하한이 0보다 크다. 다만 region 단위 bootstrap에서는 신뢰구간 하한이 음수이므로, 일부 지역 조합에서는 개선이 불안정할 수 있다.

## 4. 산업별 confidence rule

초기 운영 기준은 다음 조건을 사용했다.

| 조건 | 기준 |
| --- | --- |
| 평균 개선율 | 2% 이상 |
| 개선 연도 비율 | 60% 이상 |
| 최근 2개 연도 개선 | 2개 연도 모두 개선 |
| 최악 연도 악화폭 | -10% 이상 |
| bootstrap 개선 확률 | 0.60 이상 |

산업별 판정 결과는 다음과 같다.

| 등급 | 산업 |
| --- | --- |
| A: ML 보정 우선 후보 | B00, F00, G00, L00, P00 |
| B: baseline과 ML 병행 표시 | C00, O00 |
| C: baseline 유지, ML 참고 | ERS, I00, K00, MN0 |
| D: ML 미사용 | A00, D00, H00, J00, Q00 |

특히 농림어업(`A00`)과 전기·가스(`D00`)는 후속 검증에서도 ML 보정이 악화되어 baseline 유지가 적절하다.

## 5. Shrinkage/Blending 안전장치

full ML residual을 그대로 쓰는 대신, target year 이전 구간에서만 보정 강도를 선택하는 두 방식을 비교했다.

1. Residual shrinkage: `baseline * exp(alpha * predicted_log_ratio)`
2. Linear blending: `(1 - w) * baseline + w * ML`

| 모델 | MAPE | WMAPE | baseline 대비 개선율 |
| --- | ---: | ---: | ---: |
| baseline | 6.652706 | 4.388658 | 0.000000% |
| full ML | 6.702529 | 4.230372 | 3.606706% |
| shrink | 6.600604 | 4.286941 | 2.317724% |
| blend | 6.601305 | 4.286948 | 2.317565% |
| safe selected | 6.600451 | 4.286962 | 2.317246% |

full ML은 WMAPE 개선폭이 가장 크지만 MAPE는 baseline보다 약간 나쁘다. shrink/blend 안전장치는 WMAPE 개선폭은 줄어들지만 MAPE를 baseline보다 낮추므로, 운영 안정성 측면에서는 더 보수적인 후보가 된다.

## 6. 운영 결론

현재 결과만으로 전체 산업을 ML로 전면 대체하지 않는다. 권장 운영 방식은 산업별 gating이다.

| 산업군 | 운영 방식 |
| --- | --- |
| confidence A | ML log-ratio residual + reconciliation 적용 가능. 단, shrink/blend 안전장치 병행 검토 |
| confidence B | 대시보드에 baseline과 ML을 병행 표시하고, 확정 산출은 baseline 우선 |
| confidence C | baseline 유지, ML은 진단용 |
| confidence D | ML 미사용 |

## 7. 다음 단계

1. confidence A/B 산업을 대상으로 시군구 rolling backtest에 동일한 log-ratio residual + reconciliation 구조를 적용한다.
2. full ML과 shrink/blend의 선택 기준을 산업별로 분리한다.
3. XGBoost 파라미터 선택 안정성 표에 validation WMAPE를 추가하고, global fixed parameter와 target-year tuned parameter를 비교한다.
4. feature ablation을 실시해 lagged residual, baseline share, 구조통계 feature 중 실제 개선 기여도를 분리한다.
5. A00/D00는 현 feature로 ML을 반복하기보다 경지면적·발전량·전력판매량 같은 직접 feature 수집을 우선한다.

## 8. 산출물

| 파일 | 설명 |
| --- | --- |
| `reports/reconciled_model_stability_report.md` | 연도·산업·지역 안정성, bootstrap, confidence rule |
| `reports/reconciled_model_safety_report.md` | shrinkage/blending 안전장치 실험 |
| `data/processed/reconciled_model_stability_*.csv` | 안정성 상세 CSV |
| `data/processed/reconciled_model_safe_*.csv` | 안전장치 상세 CSV |

CSV 산출물은 모두 CP949 인코딩으로 확인했다.
