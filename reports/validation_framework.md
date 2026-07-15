# 검증 레지스트리 설계

## 목적

시군구·읍면동과 중분류·소분류 추정값은 공식 actual, 연간 벤치마크, proxy, forecast가 섞여 있다. 따라서 모든 값을 같은 오차율로 평가하면 이미 알고 있는 값을 재배분한 결과와 미지의 값을 예측한 결과가 뒤섞인다.

`validation_registry.csv`는 각 산출물의 값이 어떤 성격인지 먼저 고정한다.

## 값의 역할

| 역할 | 의미 |
| --- | --- |
| `official_actual` | 정부·지자체가 직접 공표한 actual과 비교 가능 |
| `benchmark` | Denton 제약에 사용한 공식 연간 총량과 정합성 비교 가능 |
| `partial_official_actual` | 일부 집계 수준에서만 official actual 비교 가능 |
| `proxy` | 공식 하위 GVA actual은 없고 생산지수·사업체·종사자 등 proxy와 비교 |
| `future_or_unavailable` | 아직 actual이 공표되지 않았거나 해당 주기의 official actual이 없음 |
| `unavailable` | 공식 actual 부재 |

## 검증 우선순위

1. official actual과 직접 비교한다.
2. official annual benchmark와 회계 정합성을 확인한다.
3. 상위 지역·상위 산업 총량과 합계 정합성을 확인한다.
4. proxy actual 또는 외부 준actual과 비교한다.
5. 비교 가능한 actual이 없으면 신뢰등급을 낮추고 탐색용으로 표시한다.

## 산출물

| 파일 | 설명 |
| --- | --- |
| `validation_registry.csv` | 데이터셋별 actual 역할, 검증 방식, 행 수, 비교 가능 행 수 |
| `validation_registry_summary.csv` | 지역 수준·산업 깊이별 검증 가능성 요약 |

모든 CSV는 MS Office 호환을 위해 CP949로 저장한다.
