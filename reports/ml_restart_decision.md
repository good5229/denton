# Municipality ML Restart Decision

## Decision

시군구 ML 보정 실험은 아직 재개하지 않는다. 이번 단계에서 KEPCO 시군구 월간 전력사용량은 source manifest, publication-lag rule, revision audit, 지역 매칭, feature registry를 갖춘 ML-ready feature로 정리됐지만, 현재 보유한 official actual 평가기간과 전력 feature 기간이 겹치지 않는다.

따라서 전력 feature를 이용한 baseline 대비 ablation은 데이터 유출 없이 수행할 수 없다.

## Evidence

| 항목 | 결과 |
| --- | --- |
| 전력 feature 기간 | 2025-2026 월간 |
| 기존 시군구 official actual pilot 기간 | 2021-2023 |
| 공통 official actual 평가기간 | 없음 |
| ML ablation status | `blocked_no_common_official_actual_period` |

## Completed Readiness Gate

| Gate | Status | Note |
| --- | --- | --- |
| 원천 파일 보존 | Pass | XLSX vintage, URL, hash, size, downloaded_at 보존 |
| revision audit | Pass | 130,043개 중복 관측 비교, 수정 0건 |
| publication lag audit | Pass | 실제 게시월 반영, 최대 4개월 지연 확인 |
| leakage eligibility | Pass | `max(observation+2개월, publication_month)` 적용 |
| region crosswalk | Warning | 227/229 매칭, 군위군·세종시 미매칭 |
| total consistency | Pass | 합계 불일치 0건 |
| feature key uniqueness | Pass | 전국 고유 `sigungu_feature_key` 적용 |

## Operating Rule

전력 feature는 향후 시군구 ML 재개 시 사용할 수 있다. 단, 학습·평가 시 다음 조건을 반드시 적용한다.

```text
first_eligible_period <= prediction_origin_period
```

이 조건을 만족하지 않는 feature는 특정 예측시점에 아직 공표되지 않은 정보이므로 사용하지 않는다.

## Next Restart Conditions

1. 2025년 이후 시군구 official actual 또는 검증 가능한 proxy actual이 확보된다.
2. KEPCO 과거 월간 전력사용량 vintage를 추가 확보해 2021-2023 official actual과 겹치는 기간을 만든다.
3. 건축허가·공장등록 등 두 번째 직접 feature source를 확보해 전력 단일 feature에 과도하게 의존하지 않는 실험 설계를 만든다.

## Conclusion

이번 작업의 결론은 “ML 재개”가 아니라 “전력 feature의 운영 가능한 편입 완료”다. 다음 실험은 공통 평가기간이 생긴 뒤 baseline, electricity-only, electricity+structural feature 조합을 동일 population에서 비교하는 방식으로 진행한다.
