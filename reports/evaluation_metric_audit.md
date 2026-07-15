# 평가 산식 및 모집단 감사

## 코드 수정 전 분석 요약

1. `global_model`은 2018~2023년 1,620건이고, sector/full ML은 2019~2023년 1,350건이다.
2. `global_model` improvement 5.364796%는 global 자체 모집단의 baseline WMAPE 4.182586 대비 계산된 값이다.
3. `sector_group_model:*`은 각 산업 또는 산업군 내부 WMAPE이므로 전체 산업 WMAPE와 직접 비교하면 안 된다.
4. 현재 global common-feature 모델은 F6/F7 indicator·exogenous를 포함하지 않는다. 따라서 `global_fixed_full`은 사실상 common-feature pruned model이다.
5. 산업코드는 one-hot, 지역코드도 one-hot으로 처리된다.
6. 기존 global 고정 파라미터는 `BASE_PARAMS`, seed 42다.
7. 결과는 log-ratio residual 예측 후 연도×산업 부모 baseline에 reconciliation된 값이다.
8. 기존 sector full ML은 산업별 full-grid tuning, global은 고정 파라미터였으므로 tuning budget이 달랐다.
9. global common matrix는 outer train/test별로 생성되며 target year actual은 학습 target 평가 외 feature에는 쓰지 않는다.
10. nested tuning은 outer target year 이전 fold만 사용하도록 구현했다.

## 공통 모집단 감사

| model | orig count | common count | orig base | orig WMAPE | orig imp | common base | common WMAPE | common imp | years | common years |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_all | 1350 | 1350 | 4.388658 | 4.388658 | 0.0 | 4.388658 | 4.388658 | 0.0 | 2019,2020,2021,2022,2023 | 2019,2020,2021,2022,2023 |
| sector_full_ml | 1350 | 1350 | 4.388658 | 4.230372 | 3.606707 | 4.388658 | 4.230372 | 3.606707 | 2019,2020,2021,2022,2023 | 2019,2020,2021,2022,2023 |
| adaptive_shrinkage | 1350 | 1350 | 4.388658 | 4.282983 | 2.40791 | 4.388658 | 4.282983 | 2.40791 | 2019,2020,2021,2022,2023 | 2019,2020,2021,2022,2023 |
| regret_mean_gt_0.0 | 1350 | 1350 | 4.388658 | 4.253818 | 3.072458 | 4.388658 | 4.253818 | 3.072458 | 2019,2020,2021,2022,2023 | 2019,2020,2021,2022,2023 |
| global_model | 1620 | 1350 | 4.182586 | 3.958199 | 5.364796 | 4.388658 | 4.124072 | 6.028854 | 2018,2019,2020,2021,2022,2023 | 2019,2020,2021,2022,2023 |