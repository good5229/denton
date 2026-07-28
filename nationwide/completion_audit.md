# 전국 확장 검증 완료 감사

생성일: 2026-07-28

## 요구사항별 확인

| 요구사항 | 증거 | 판정 |
| --- | --- | --- |
| `nationwide/` 폴더에 분석 결과물 배치 | `nationwide/nationwide_quarterly_grdp_validation_report.md`, `nationwide/outputs/*.csv` | 충족 |
| 전국 각 광역시/도에 대한 시군구/단층시 기반 분기누적·연간환산 WAPE 검증 | `nationwide/outputs/operating_point_sido_grdp_validation.csv`: 17개 지역 × 5개 연도 × 4개 운영시점 × 2개 트랙 = 680행 | 충족 |
| 전국 하위 추정값 합계와 대한민국 분기별 GDP actual 비교 | `nationwide/outputs/national_gdp_yearly_summary.csv`, `nationwide/outputs/national_gdp_coverage_validation.csv` | 충족 |
| 세종 처리 | BOK RECI 17개 광역 기준에 따라 `세종특별자치시 → 세종시` 1개 하위단위로 처리 | 충족 |
| 데이터 출처와 공표주기 기재 | `nationwide/data_sources_and_release_cycles.md` | 충족 |
| 국책은행 담당자 agent 검토 및 피드백 반영 | `nationwide/bank_policy_reviewer_feedback.md` | 충족 |
| 결측·중복·actual 누락 감사 | `nationwide/outputs/audit.csv`: 시도 actual 결측 0, 업종 actual 결측 0, 전국 actual 결측 0 | 충족 |
| 원천 공백 명시 | `nationwide/outputs/missing_2023_sigungu_source_audit.csv`, 보고서 기준값 사용 감사 | 충족 |

## 주요 검증 수치

| 트랙 | Q1 연간환산 WAPE | Q1~Q2 연간환산 WAPE | Q1~Q3 연간환산 WAPE | Q4/정밀화 WAPE |
| --- | ---: | ---: | ---: | ---: |
| 엄격 속보형 | 1.889% | 1.390% | 1.293% | 1.311% |
| 직전연도 시도총량 보정형 | 1.644% | 1.135% | 1.050% | 1.071% |

## 해석 제한

- 본 검증은 최신 공표 빈티지 기준의 사후 백테스트다.
- 공표시점별 원천 빈티지를 완전 재현한 실시간 운용성과로 해석하지 않는다.
- 전국 GDP 경계 WAPE는 외부 일관성 참고지표이며, 시도별·업종별 예측력이 모두 높다는 뜻은 아니다.
- 기타산업 및 순생산물세는 시도 단위 bridge이므로 시군구별 총 GRDP 확정치나 순위 산출에 직접 사용하지 않는다.
