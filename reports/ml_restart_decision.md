# Municipality ML Restart Decision

## Decision

시군구 ML 보정 실험은 full 재개가 아니라, vintage-aware dry-run ablation 단계로 이동한다. 당초 2025~2026 KEPCO 시군구 월간 전력사용량만으로는 official actual 평가기간과 겹치지 않았지만, 과거 KEPCO 게시판 수집을 통해 2021~2023년 36개월 전력 feature가 확보됐다.

따라서 다음 단계에서는 동일 모집단, 동일 split, prediction-origin별 eligible vintage를 고정한 뒤 baseline, 기존 global policy, electricity-only 정책을 비교할 수 있다.

## Evidence

| 항목 | 결과 |
| --- | --- |
| 전력 feature 기간 | 2025-2026 월간 + 2021-2023 historical |
| 기존 시군구 official actual pilot 기간 | 2021-2023 |
| 공통 official actual 평가기간 | 2021-2023 |
| ML ablation status | `ready_for_vintage_aware_dry_run` |

## Completed Readiness Gate

| Gate | Status | Note |
| --- | --- | --- |
| 원천 파일 보존 | Pass | XLSX vintage, URL, hash, size, downloaded_at 보존 |
| revision audit | Pass | 130,043개 중복 관측 비교, 수정 0건 |
| publication lag audit | Pass | 실제 게시월 반영, 최대 4개월 지연 확인 |
| leakage eligibility | Pass | `max(observation+2개월, publication_month)` 적용 |
| region crosswalk | Pass | 227 direct + 2 manual / 229, 최종 미매칭 0 |
| total consistency | Pass | 합계 불일치 0건 |
| feature key uniqueness | Pass | 전국 고유 `sigungu_feature_key` 적용 |
| historical common period | Pass | 2021-2023 36개월 확보 |
| official actual join | Pass | 2021, 2022, 2023 region join rate 1.000 |

## Operating Rule

전력 feature는 향후 시군구 ML dry-run ablation에 사용할 수 있다. 단, 학습·평가 시 다음 조건을 반드시 적용한다.

```text
first_eligible_period <= prediction_origin_period
```

이 조건을 만족하지 않는 feature는 특정 예측시점에 아직 공표되지 않은 정보이므로 사용하지 않는다.

과거 feature에서는 latest-source 값과 availability를 분리한다. `first_observed_eligible_period`는 관측월이 최초로 사용 가능해진 시점이고, `first_eligible_period_latest_source`는 latest-source 값 자체의 공표시점이다. 실제 실험에서는 prediction origin별로 사용 가능한 source vintage를 선택해야 하며, latest-source 값을 최초 관측 가능 시점으로 앞당겨 사용해서는 안 된다.

## Next Restart Conditions

1. Vintage-aware feature selector를 구현한다.
2. Baseline, global policy, electricity-only dry-run harness를 동일 모집단에서 실행한다.
3. Lag sensitivity, temporal placebo, region permutation을 추가한다.
4. 건축허가·공장등록 등 두 번째 직접 feature source를 확보해 전력 단일 feature에 과도하게 의존하지 않는 실험 설계를 만든다.

## Conclusion

Vintage-aware dry-run 결과 full-strength electricity correction은 악화됐고, alpha=0.25 guardrail 정책은 global 대비 WMAPE를 개선했다. 따라서 현재 결론은 “운영 채택”이 아니라 `guardrailed_candidate_needs_robustness`다. 다음 단계는 bootstrap, future-lead placebo, missingness simulation, leave-one-sido-out, material degradation 검토다.
