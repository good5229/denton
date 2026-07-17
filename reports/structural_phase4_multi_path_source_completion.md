# Structural Feature Phase 4

## 1. 실행 요약

- 실행일: `2026-07-18T01:15:59+09:00`
- 공식 KSIC PDF: `data/raw/한국표준산업분류-해설서-개정분류-9차10차연계표포함.pdf` (9→10 연계표를 PDF p.866~944에서 추출)
- DAM_PDAN: `1,451`개 Point, `G3 diagnostic_only`
- ML 재개: **blocked_source_completion**. 이번 Phase에서도 모델 학습과 Actual 기반 사후선택은 실행하지 않았다.

## 2. Phase 3 결과 정합성

`496`은 전체 미해결 code-name-version 조합 수이고 `50`은 Gate에 표시했던 상위 queue의 크기였다. 두 수치를 별도 지표로 재정의했다.

| 지표 | 재계산 값 |
|---|---:|
| unresolved_unique_raw_codes | 314.0 |
| unresolved_code_name_pairs | 496.0 |
| unresolved_top_frequency_codes | 50.0 |
| unresolved_factory_rows | 2156.0 |
| unresolved_employee_weight | 61262.0 |

## 3. Unknown Candidate 재분류

Phase 3의 unknown 후보를 파일 signature·헤더·XLSX 내부 member·키워드·geometry type으로 재분류했다. 분류 분포: `{"irrelevant": 3143, "manual_review": 88, "probable_industrial_activity": 7, "confirmed_ksic_table": 1, "probable_factory_snapshot": 1, "corrupted": 1}`.

## 4. 신규 Source 발견

내용 기반 후보 `0`개를 재검토 queue로 등록했다. 별도로 사용자가 제공한 KSIC PDF와 DAM Point layer를 즉시 검증했다.

## 5. KSIC 미해결 지표 재정의

미해결 raw code, code-name pair, 공장 원행, employee weight, 상위 영향도 queue를 서로 다른 지표로 관리한다. Gate에는 전체 queue 크기를 상위 50개 수치처럼 표시하지 않는다.

## 6. KSIC 8·9·10·11차 Registry

공식 PDF에서 KSIC9 `1,145`개, KSIC10 `1,196`개 세세분류 registry와 9→10 관계 `1,377`행을 구축했다. 10→11은 Phase 3 공식 XLSX `1,231`행을 연결했다. 8→9 공식표는 아직 없다.

## 7. KSIC Fine·Group·Division Mapping

| Gate | 행 매핑률 | 종업원 가중 매핑률 | 상태 |
|---|---:|---:|---|
| K_FINE | 99.2711% | 98.7211% | blocked_mapping_quality |
| K_GROUP | 99.3437% | 99.3002% | blocked_mapping_quality |
| K_DIVISION | 99.3664% | 99.3393% | blocked_mapping_quality |

One-to-many 관계는 강제 단일화하지 않았다. 동일한 2자리·3자리 prefix가 공식 관계 전체에서 유지될 때만 상위분류를 결정했다.

## 8. 공장 Historical Source 탐색

2021·2022·2023 전국 snapshot은 확인되지 않았다. 현재 활성공장 파일의 등록일만으로 과거를 재구성하면 폐쇄공장이 사라지는 survivorship bias가 생기므로 금지했다.

## 9. 공장 Stock 및 Flow 가능성

공장 경로 상태는 `blocked_history`이다. snapshot pair가 없으므로 stock도 ML-ready가 아니며, 소실 행을 폐쇄로 간주하는 flow는 생성하지 않았다.

## 10. 산업단지 Geometry Source

DAM_PDAN은 완전한 SHP component set이지만 geometry가 `Point`이다. 따라서 `G3`이며 대표점 존재·거리 진단만 허용한다. Point를 이용한 시군구 전량배분은 하지 않았다.

## 11. 산업단지 Historical Activity

FactoryOn 대용량 파일의 목표기간 중 `2021Q2`에서 `tenant_company_count`와 `approved_registered_factory_count` stock `2,050`행을 복원했다. 2021Q1과 2021Q3~2023Q4는 비어 있어 historical Gate는 실패한다. 생산·수출은 없고, `산업단지별 고용` 시트는 종업원 수가 아니라 고용구간별 공장 수 구조여서 employment 값으로 사용하지 않았다.

## 12. 산업단지 Allocation

Polygon, 입주기업 주소, 근무지 종업원 주소가 없어 allocation은 차단했다. DAM 대표점의 행정구역 귀속은 진단표에만 남겼다.

## 13. 사업체·고용 Fallback Source

현재 로컬 KOSIS mart에서 2021~2023 시군구 제조업·광업 세부자료를 확인했으나 전 산업 공통 coverage가 아니므로 `development_only`이다. 정확한 release date도 없어 가정한 2년 lag는 개발용 규칙으로만 유지한다.

## 14. 한국형 Spatial Feature

228개 시군구에 면적·둘레·compactness·도서 component·수도권 여부·서울/광역거점 거리·Queen/Rook 차수·50/100km 밀도와 graph centrality를 생성했다. 모델 후보 graph는 `Queen`, `nearest-5` 두 개로 동결했다.

## 15. Publication Lag

기준시점과 공표시점을 분리했다. FactoryOn 파일의 과거 공식 게시일이 확인되지 않아 retrieval date를 release date로 대체하지 않았고 historical ML 사용을 차단했다.

## 16. First Eligible Period

정확한 공표일이 없는 산업단지 동적자료는 first eligible을 비워 두고 blocked 처리했다. KOSIS 사업체 자료의 `target year + 2`는 개발 가정이며 confirmatory 사용 전 공식 release month 검증이 필요하다.

## 17. Source Triangulation

산업단지 stock은 2021Q2 한 분기만 있어 기간 coverage부터 미완성이고, 공식 전국 published total도 없어 총량 1% Gate를 수행하지 못했다. 공장과 사업체 경로도 각각 history와 scope가 미완성이다.

## 18. Quality Audit

선택된 산업단지 업체수 시트의 2021Q2 schema와 count 비음수 조건은 통과했지만 12개 분기 연속성은 실패했다. 이상치를 자동 제거하지 않았으며, source revision·unit change를 판별할 근거가 부족한 항목은 차단 상태로 남겼다.

## 19. 사용자 개입 요청

1. KSIC 8→9 공식 연계표 원본
2. 공식 산업단지 경계 Polygon (현재 DAM은 Point)
3. 2021·2022·2023 전국 등록공장 snapshot

비밀번호·API 키 원문·개인 로그인정보는 공유하지 않는다.

## 20. Source Gate Matrix

| Source | 상태 |
|---|---|
| spatial_static | pass |
| ksic_fine | blocked_mapping_quality |
| ksic_group | blocked_mapping_quality |
| ksic_division | blocked_mapping_quality |
| factory_registration | blocked_history |
| industrial_complex_activity | development_only |
| business_employment_activity | development_only |

## 21. Bundle Eligibility

`C0 Global`과 static geography 진단용 `C6`만 구조상 준비됐다. Structural source를 요구하는 C1S·C2·C7S·C8·A4는 source Hard Gate 통과 전까지 학습 후보가 아니다.

## 22. ML Restart 결정

결정: **blocked_source_completion**. 최소 한 개 structural source가 아직 모든 history·공표·총량·allocation Gate를 동시에 통과하지 못했다.

## 23. Blocking Issues

- KSIC 8→9 공식 관계 부재
- 공장 2021~2023 snapshot 부재
- 산업단지 Polygon/활동별 allocation 근거 부재
- 산업단지 생산·수출·실제 고용 및 공식 release date 부재
- 사업체·고용 fallback의 전 산업 시군구 공통 coverage와 정확한 release date 부재

## 24. 다음 실행 항목

1. KSIC 8→9 표를 받으면 상위분류 Gate를 즉시 재계산한다.
2. 산업단지 Polygon 또는 입주기업 주소를 확보해 stock을 시군구에 배분하고 공식 총량과 대조한다.
3. 전국사업체조사 시군구×대분류 2021~2023 원표와 공표일을 확보해 Fallback Lane을 먼저 ML-ready로 만든다.
4. 최소 한 경로가 통과한 뒤에만 Phase 5 사전등록 문서를 작성한다.
