# Phase183 다음 개선 실험 사전 검증 감사

## 목적

Phase183은 새 총부가가치(GVA) 예측값을 만들지 않는다. 대신 Phase179/180/182가 다음 개선 실험의 안전한 출발점인지 검사한다. 특히 target actual 유출, 낡은 `현행유지가능` 판정의 잔존, KOBIS 같은 보조지표의 무검증 채택을 막는 것이 목적이다.

## 검증 결과

| 검증항목 | 범위 | 판정 | 증거 | 실패 시 조치 |
| --- | --- | --- | --- | --- |
| P179_TARGET_ACTUAL_AUDIT_ONLY | Phase179 route decision | PASS | manifest target_actual_use=audit only | Phase179 decision logic must be re-read and any target-actual-driven adoption removed. |
| P179_NO_WORSENING_VS_177 | Phase179 applied cells | PASS | worsened_vs_phase177_rows=0 | Revert worsening rows or add independent validation gate before adoption. |
| P179_NO_WORSENING_VS_124 | Phase179 applied cells | PASS | worsened_vs_phase124_rows=0 | Do not use candidate as operational baseline until no-worse constraint is restored. |
| P179_APPLIED_GATE_CONDITIONS | Phase179 6 adopted cells | PASS | applied_rows=6, gate_mismatches=0 | Recompute applied set from explicit gate columns only. |
| P180_RESIDUAL_RECLASSIFIED | 20%+ residual cells | PASS | residual_rows=56, not_reclassified_rows=0 | Every >20% residual cell must be treated as improvement-needed; no public accuracy claim. |
| P182_NO_STALE_ROUTEBOOK_LOGIC | Phase182 residual routebook | PASS | routebook_rows=56, stale_term_rows=0 | Remove old no-data-needed/public-claim labels from all residual guidance. |
| P182_SOURCE_PACK_ACTIONABLE | Phase182 source priority | PASS | source_rows=9, required_columns_present=True | Each residual source pack needs source, API dependency and model action. |
| KOBIS_NO_AUTO_ADOPTION | Phase136 KOBIS J59 guard | PASS | kobis_vintages=4, invalid_adoptions=0 | Reject KOBIS for J59 vintage unless it beats generic seasonal share. |
| P179_ERROR_FORMULA | Phase179 registry arithmetic | PASS | rows=110, error_mismatch=0, rate_mismatch=0 | Fix error formula before showing values in reports/posters. |

## 실패 항목

모든 사전 검증 항목이 통과했다.

## 다음 실험 규칙

| 규칙 | 적용 방식 |
| --- | --- |
| 새 활동자료는 먼저 외부 도시/상위 집계 검증 | 고양·포항 actual 오차 감소만으로 채택 금지. 최소한 LOO 또는 상위산업 집계검증 통과. |
| 20% 초과 잔여 셀은 공개성과 주장 금지 | 포스터/보고서에서는 개선 필요 또는 진단 대상으로 표시. |
| 속보성과 정밀화 분리 | 공표시점 불명 자료는 속보 트랙 제외. 정밀화 트랙에서만 사용. |
| 업종군 일괄 보정 금지 | C00/MN0/ERS 같은 대블록 전체가 아니라 중분류별 활동자료로 라우팅. |
| KOBIS 같은 직관적 자료도 검증 후 채택 | Phase136처럼 기존 계절비중보다 못하면 사용 가능한 API라도 기각. |

## 해석

1. Phase179는 현재 파일 기준으로 target actual을 적용 판단에 쓰지 않고, Phase124/177 대비 악화 셀도 없다.
2. Phase180의 20% 초과 잔여 셀은 모두 추가개선/운영개선 대상으로 재분류되어야 하며, Phase183은 이 조건을 검사한다.
3. Phase182 라우트북은 다음 API 수집이 열릴 때 바로 연결할 수 있는 작업지시서 역할을 한다. 다만 신규 자료는 반드시 외부 검증 또는 상위 집계검증을 통과해야 한다.
4. KOBIS는 사용 가능하지만, 기존 Phase136 검증에서는 고양시 J59 시간축 개선에 실패했으므로 자동 채택하지 않는다.

## 산출물

- 검증 체크: `data/processed/phase183_guardrail_audit/phase183_guardrail_checks.csv`
- 실패 항목: `data/processed/phase183_guardrail_audit/phase183_guardrail_failures.csv`
- 다음 실험 규칙: `data/processed/phase183_guardrail_audit/phase183_next_experiment_rules.csv`
