# Municipality ML Restart Decision

Current status: `guardrailed_candidate_needs_robustness`

KEPCO 과거 전력자료로 2021~2023 공통 평가기간을 확보했고, prediction-origin 기준 vintage-aware dry-run을 실행했다.

핵심 결과는 다음과 같다.

| policy | WMAPE | interpretation |
| --- | ---: | --- |
| M1 global | 5.470158 | 기준 정책 |
| M3 global + electricity | 5.938832 | full-strength 전력 보정은 악화 |
| M4 alpha=0.25 | 5.363593 | guardrail 적용 시 개선 |

따라서 시군구 ML은 full 재개가 아니라 guardrailed electricity 후보의 강건성 검증 단계로 이동한다. 운영 채택 전에는 bootstrap, region holdout, future-lead placebo, missingness simulation, material degradation 검토가 필요하다.
