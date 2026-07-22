# Phase52 건축인허가 이벤트 월별 보강자료

## 결론

- 공공데이터포털 키로 건축HUB 건축인허가 기본개요 API를 호출해 고양시·포항시 현행 법정동 전체의 허가·착공·사용승인 이벤트를 수집했다.
- 2021-01~2026-06 월별 법정동×용도그룹 피처를 생성했으며, 건설업의 월별 생산시점 전환과 부동산업의 신규 공급 흐름 보강에 사용할 수 있다.
- 단, API는 법정동 기반이므로 행정동 배분에는 법정동→행정동 공식 매핑 또는 주소/좌표 보강이 필요하다.

## 수집 요약

- 대상 법정동: 310개
- 원천 이벤트 행: 33,116행
- 2021~2026 월별 피처 행: 9,768행

| 도시 | 이벤트 | 월별 행 | 이벤트 수 | 이벤트 연면적 |
| --- | --- | ---: | ---: | ---: |
| 고양시 | 사용승인 | 521 | 641 | 1,013,122 |
| 고양시 | 착공 | 519 | 658 | 861,176 |
| 고양시 | 허가 | 1220 | 1709 | 1,457,088 |
| 포항시 | 사용승인 | 1747 | 1845 | 19,663,716 |
| 포항시 | 착공 | 1742 | 1872 | 16,079,845 |
| 포항시 | 허가 | 4019 | 4836 | 20,138,049 |

## 산출 파일

- `data/processed/partial_stats_phase52_building_permit_events_goyang_pohang.csv`
- `data/processed/partial_stats_phase52_building_permit_legal_dong_monthly.csv`
- `data/processed/partial_stats_phase52_building_permit_collection_manifest.csv`
- `data/processed/partial_stats_phase52_status.json`
