# Electricity Feature Acceptance Decision

Current decision: `guardrailed_candidate_needs_robustness`

전력 feature는 아직 운영 정책으로 채택하지 않는다. 다만 alpha=0.25 guardrail 정책은 global 대비 WMAPE를 개선했으므로 후속 robustness 검증 대상으로 유지한다. 채택에는 lag sensitivity, placebo superiority, region generalization, bootstrap uncertainty, material degradation 검토가 추가로 필요하다.
