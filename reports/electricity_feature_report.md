# 전력사용량 Feature 편입 및 ML 재개 준비 결과

## 실행 요약

KEPCO 시군구별 전력사용량 원천 XLSX를 vintage 자료로 보존하고, source manifest, revision audit, 지역코드 매칭, feature table, leakage eligibility audit, 품질검증을 생성했다.

| 항목 | 결과 |
| --- | ---: |
| source manifest rows | 12 |
| duplicate observation comparisons | 130,043 |
| changed duplicate observations | 0 |
| revision rate | 0.000000 |
| region matched | 227 / 229 |
| unmatched regions | 2 |
| feature rows | 3,664 |

## 생성 산출물

| 파일 | 내용 |
| --- | --- |
| `data/processed/source_manifest.csv` | 원천 파일 해시·크기·게시일·관측기간 manifest |
| `data/processed/municipality_electricity_monthly.csv` | latest source wins 적용 후 monthly long table |
| `data/processed/municipality_electricity_features.csv` | ML-ready 시군구 월간 전력 feature table |
| `data/processed/electricity_duplicate_observation_comparison.csv` | 중복 관측월 vintage 비교 |
| `data/processed/electricity_source_revision_log.csv` | source pair별 revision 요약 |
| `data/processed/electricity_latest_source_selection_audit.csv` | latest source selection audit |
| `data/processed/electricity_region_crosswalk_audit.csv` | 시군구 코드 매칭 audit |
| `data/processed/electricity_unmatched_region_rows.csv` | 지역코드 미매칭 목록 |
| `data/processed/electricity_total_consistency_audit.csv` | 원표 합계·정규화 합계 일치 검증 |
| `data/processed/feature_registry.csv` | ML feature registry |
| `docs/data_contracts/electricity.md` | 전력 source data contract |

## Revision Audit

동일 관측월이 후속 source file에 반복 포함되므로, 각 observation key에 대해 최신 source period를 채택했다. Revision audit 결과는 다음과 같다.

| previous | latest | compared | revised | revision_rate | max_abs_diff |
| --- | --- | ---: | ---: | ---: | ---: |
| 202511 | 202512 | 102014 | 0 | 0.000000 | 0.000 |
| 202512 | 202603 | 36 | 0 | 0.000000 | 0.000 |
| 202603 | 202604 | 27993 | 0 | 0.000000 | 0.000 |

## Publication Lag

게시판에서 확인 가능한 게시일을 이용해 최신 관측월 대비 게시월 차이를 계산했다. ML 결합 시에는 `max(observation+2개월, publication_month)`를 `first_eligible_period`로 사용한다.

| source_period | publication_date | latest_observation_period | delay_months | conservative |
| --- | --- | --- | --- | --- |
| 202505 | 2025-08-12 | 202505 | 3 | N |
| 202506 | 2025-08-12 | 202506 | 2 | Y |
| 202507 | 2025-11-04 | 202507 | 4 | N |
| 202508 | 2025-11-04 | 202508 | 3 | N |
| 202509 | 2025-11-04 | 202509 | 2 | Y |
| 202510 | 2025-12-01 | 202510 | 2 | Y |
| 202511 | 2026-01-12 | 202511 | 2 | Y |
| 202512 | 2026-02-26 | 202512 | 2 | Y |
| 202601 | 2026-03-12 | 202601 | 2 | Y |
| 202602 | 2026-04-15 | 202602 | 2 | Y |
| 202603 | 2026-05-11 | 202603 | 2 | Y |
| 202604 | 2026-06-15 | 202604 | 2 | Y |

## Region Crosswalk

전력 원천의 시도·시군구 명칭을 기존 시군구 pilot crosswalk와 매칭했다. 매칭률은 `227/229`이다.

미매칭 지역은 별도 파일에 보존했다. 대표 예시는 다음과 같다.

| 시도 | 시군구 |
| --- | --- |
| 대구광역시 | 군위군 |
| 세종특별자치시 | 세종시 |

## Quality Checks

| Check | Value | Pass |
| --- | ---: | --- |
| feature_rows | 3664 | Y |
| total_consistency_failed_rows | 0 | Y |
| duplicate_feature_keys | 0 | Y |
| unmatched_regions | 2 | N |
| negative_total_kwh_rows | 0 | Y |
| zero_total_kwh_rows | 0 | Y |

## ML Ablation Readiness

`blocked_no_common_official_actual_period`: Electricity feature starts in 2025, while available municipality official-actual pilot uses earlier target years.

현재 확보된 KEPCO feature는 2025~2026년 월간 자료이고, 기존 시군구 official-actual pilot 평가기간은 그 이전 연도다. 따라서 이번 단계에서는 feature table을 ML-ready로 만들었지만, baseline 대비 ablation은 공통 official actual 기간이 확보된 뒤 실행해야 한다.

## 결론

전력 feature는 source manifest, revision audit, 지역 매칭, eligibility rule, 품질검증을 갖춘 ML-ready 상태다. 다만 시군구 official actual과의 공통 평가기간이 아직 없어 신규 feature의 성능개선 여부는 보류한다.
