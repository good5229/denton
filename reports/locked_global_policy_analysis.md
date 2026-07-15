# Locked Global Policy 차기 실험 분석

## 코드 수정 전 분석

1. `global_adaptive_shrinkage`: global common-feature log-ratio residual 예측값에 `alpha = exp(-5 * |log(global/baseline)|)`를 적용한다.
2. `global_regret_adaptive`: 산업별 pre-target 개선율 평균을 regret proxy로 두고 `alpha_regret = clip(avg_improvement / 5, 0, 1)`을 곱한다.
3. target year별 흐름: baseline 생성 → global residual 예측 → 부모 총량 reconciliation → alpha/gate 적용 → 정책별 산출.
4. material degradation: 산업×연도 WMAPE 개선율이 -2% 미만이면 1건으로 센다.
5. 동결 설정: feature set, XGBoost grid/seed, alpha 산식, regret threshold, parent baseline, reconciliation rule.
6. 시군구 actual은 현재 pilot 데이터 기준 2020~2023, 시도 parent annual actual은 2019~2023 범위다.
7. crosswalk는 stable code-name 기준 1:1 파일을 생성했다. 통폐합 가중 crosswalk는 아직 외부 원장이 필요하다.
8. sample weight 전달 위치는 `train_xgb(..., weights=...)`다.
9. time decay는 train row 생성 직후 sample weight 배열을 만들 때 적용하면 된다.
10. out-of-fold residual은 이번 신규 confirmatory/pilot 결과 파일에 행 단위로 저장되며 conformal calibration 입력으로 사용할 수 있다.