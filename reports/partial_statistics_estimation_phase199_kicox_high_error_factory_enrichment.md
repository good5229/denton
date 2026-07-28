# Phase199 KICOX 고오차 제조업 공장 생산정보 제한 수집

## 목적

고양시·포항시 제조업 중분류 고오차 업종에 대해 KICOX 공장등록 생산정보 API가 실제 개선 후보가 될 수 있는지 제한 수집했다. 전수 수집이 아니라, 각 고오차 중분류별 종업원·제조시설면적 상위 공장 최대 15개 회사명을 대상으로 조회했다.

## 수집 요약

| 요청 회사수 | 정상 요청수 | API 응답 행수 | 대상도시·중분류 매칭 공장수 | 대상도시·중분류 매칭 회사수 |
| --- | --- | --- | --- | --- |
| 168 | 168 | 612 | 141 | 127 |

## 등록일 기반 시간 적격성 요약

KICOX 생산정보의 `frstFctryRegistDe`를 사용해 2023년·2024년 시점에 이미 등록된 공장인지 확인했다. 이 단계는 현재 스냅샷의 미래등록 공장 혼입을 줄이기 위한 감사다.

| 지역 | 중분류 | 대상연도 | 등록일 판정 | 공장수 | 종업원수 | 회사수 |
| --- | --- | --- | --- | --- | --- | --- |
| 고양시 | C13 | 2023 | eligible_by_registration_date | 8 | 163 | 8 |
| 고양시 | C13 | 2024 | eligible_by_registration_date | 8 | 163 | 8 |
| 고양시 | C14 | 2023 | eligible_by_registration_date | 7 | 162 | 7 |
| 고양시 | C14 | 2024 | eligible_by_registration_date | 7 | 162 | 7 |
| 고양시 | C21 | 2023 | eligible_by_registration_date | 6 | 151 | 6 |
| 고양시 | C21 | 2024 | eligible_by_registration_date | 6 | 151 | 6 |
| 고양시 | C23 | 2023 | eligible_by_registration_date | 12 | 226 | 12 |
| 고양시 | C23 | 2024 | eligible_by_registration_date | 12 | 226 | 12 |
| 고양시 | C29 | 2023 | eligible_by_registration_date | 10 | 234 | 9 |
| 고양시 | C29 | 2024 | eligible_by_registration_date | 10 | 234 | 9 |
| 포항시 | C20 | 2023 | eligible_by_registration_date | 13 | 433 | 10 |
| 포항시 | C20 | 2024 | eligible_by_registration_date | 13 | 433 | 10 |
| 포항시 | C23 | 2023 | eligible_by_registration_date | 19 | 983 | 14 |
| 포항시 | C23 | 2024 | eligible_by_registration_date | 19 | 983 | 14 |
| 포항시 | C24 | 2023 | eligible_by_registration_date | 13 | 3560 | 12 |
| 포항시 | C24 | 2023 | future_registered_excluded | 1 | 10 | 1 |
| 포항시 | C24 | 2023 | unknown_registration_date | 4 | 33 | 4 |
| 포항시 | C24 | 2024 | eligible_by_registration_date | 14 | 3570 | 13 |
| 포항시 | C24 | 2024 | unknown_registration_date | 4 | 33 | 4 |
| 포항시 | C25 | 2023 | eligible_by_registration_date | 13 | 1355 | 12 |
| 포항시 | C25 | 2024 | eligible_by_registration_date | 13 | 1355 | 12 |
| 포항시 | C27 | 2023 | eligible_by_registration_date | 11 | 873 | 10 |
| 포항시 | C27 | 2023 | future_registered_excluded | 2 | 12 | 2 |
| 포항시 | C27 | 2024 | eligible_by_registration_date | 11 | 873 | 10 |
| 포항시 | C27 | 2024 | future_registered_excluded | 2 | 12 | 2 |
| 포항시 | C28 | 2023 | eligible_by_registration_date | 9 | 350 | 9 |
| 포항시 | C28 | 2024 | eligible_by_registration_date | 9 | 350 | 9 |
| 포항시 | C29 | 2023 | eligible_by_registration_date | 12 | 384 | 12 |
| 포항시 | C29 | 2024 | eligible_by_registration_date | 12 | 384 | 12 |
| 포항시 | C34 | 2023 | eligible_by_registration_date | 1 | 4 | 1 |
| 포항시 | C34 | 2024 | eligible_by_registration_date | 1 | 4 | 1 |

## 판정

1. KICOX 생산정보 API는 고오차 제조업 중분류의 생산품·업종코드·종업원·최초등록일을 보강하는 데 사용할 수 있다.
2. 다만 회사명 검색형 API라 전수 자동화는 로컬 전국 공장 스냅샷의 회사명 목록을 기반으로 제한적으로 수행해야 한다.
3. 이번 제한 수집은 고오차 업종 상위 공장 중심이므로 전체 중분류 GVA 예측값을 바로 대체하지 않는다.
4. 다음 단계는 `등록일 적격 공장 활동자료`와 기존 공장 스냅샷 지표를 함께 써서 C13/C21/C23/C29, C23/C24/C25/C28/C34 등의 중분류별 후보식을 외부연도 검증하는 것이다.
5. 필지정보 API는 Phase193에서 403이므로, 면적 보강은 현재 로컬 스냅샷 면적을 사용하거나 별도 활용신청 확인이 필요하다.
