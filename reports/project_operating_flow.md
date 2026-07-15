# RECI/GVA 추정 프로젝트 운영 흐름

이 문서는 현재 프로젝트를 재현하거나 확장할 때 따라야 할 운영 순서를 정리한다. 핵심 원칙은 `실제값`, `벤치마크`, `추정값`, `prior`, `exogenous`를 분리해서 표시하고, 예측 실험에는 예측 시점에 공표된 데이터만 쓰는 것이다.

## 1. 데이터 수집

1. KOSIS에서 시도 GRVA, 산업생산지수, 서비스업생산지수, GDP/디플레이터, 시군구 연간 GRVA, 서울 자치구 GRVA, 제조업/서비스 세부산업 proxy를 수집한다.
2. ECOS에서 전국 계정 검산용 GDP/GVA, 산업연관 prior, 수입물가, 생산자물가, 환율 등 외생변수 후보를 수집한다.
3. 모든 CSV 산출물은 `cp949`로 저장해 MS Office에서 한글이 깨지지 않게 유지한다.

## 2. 공표시점 필터

예측 실험에는 `scripts/data_availability.py`의 공표시점 규칙을 적용한다.

| 데이터 성격 | 사용 규칙 |
|---|---|
| 월간/분기 지표 | 관측기간 종료 후 공표 lag가 지난 값만 사용 |
| 연간 GRVA/조사 proxy | 통상 익익년 말 공표로 보고 target year의 값을 사후적으로 쓰지 않음 |
| ECOS 외생변수 | forecast origin 이전에 공표된 최신 4개 분기만 feature로 사용 |
| 산업연관표 prior | 공표연도 이전 forecast에만 사용 |

이 규칙 때문에 벤치마크 배분 결과와 예측 검증 결과는 서로 다르게 해석해야 한다.

## 3. 추정 계층

| 계층 | 현재 방식 | 해석 |
|---|---|---|
| 시도 × 대분류 | 연간 GRVA와 분기 지표를 비례형 Denton으로 결합 | 공식 annual benchmark를 만족하는 분기 추정 |
| 시군구 × 대분류 | 시군구 연간 GRVA를 parent 시도 분기 경로로 배분 | 실제 분기 actual이 아니라 benchmark-constrained allocation |
| 시군구 × 세부산업 | 제조업/서비스 proxy와 ECOS IO prior를 결합 후 parent 총량에 정규화 | 세부산업 구조 추정 |
| 읍면동 | 경제총조사 등 proxy로 시군구 추정치를 배분 | 상업적 탐색용 proxy allocation |
| RECI | 보유 지표와 추정 GVA를 결합해 지역 경기 흐름을 지수화 | 실제 경기지표와의 상관/방향성 검증 필요 |

## 4. 검증

검증은 세 종류로 나눠 운영한다.

| 검증 | 목적 |
|---|---|
| 정합성 검증 | 하위 합계가 상위 총량과 일치하는지 확인 |
| 사후 오차 검증 | 공식 actual이 공개된 구간에서 MAPE/WMAPE/RMSE 계산 |
| release-aware backtest | 예측시점에 사용 가능했던 데이터만으로 추정하고 이후 actual과 비교 |

시군구 연간 GRVA를 다시 분기 배분한 뒤 연간 합이 100% 일치하는 것은 품질 지표가 아니라 제약조건 충족 여부다. 예측 품질은 `release-aware backtest`와 상위 시도 분기 actual 대비 하위 합계 오차를 중심으로 판단한다.

## 5. 신뢰등급

`scripts/build_confidence_scores.py`는 검증 결과를 결합해 `A-D` 등급을 만든다.

| 등급 | 의미 |
|---|---|
| A | actual 또는 benchmark가 직접 존재하거나, 사후 오차가 낮음 |
| B | 구조적으로 합리적이고 일부 검증 가능 |
| C | proxy allocation 성격이 강해 보조 해석 필요 |
| D | 공식 actual이 없고 정태 proxy 의존도가 높음 |

대시보드는 선택 조건에 맞는 동적 신뢰등급을 우선 표시하고, 해당 조합의 진단값이 없으면 수준별 fallback 등급을 표시한다.

## 6. 운영 명령 순서

```bash
PYTHONPATH=scripts .venv/bin/python scripts/collect_kosis.py
PYTHONPATH=scripts .venv/bin/python scripts/collect_expanded_kosis.py
PYTHONPATH=scripts .venv/bin/python scripts/probe_ecos_sources.py
PYTHONPATH=scripts .venv/bin/python scripts/collect_ecos_augmented_data.py

PYTHONPATH=scripts .venv/bin/python scripts/denton_all_industries.py
PYTHONPATH=scripts .venv/bin/python scripts/denton_sigungu.py
PYTHONPATH=scripts .venv/bin/python scripts/allocate_detailed_industry.py
PYTHONPATH=scripts .venv/bin/python scripts/allocate_emd_gva.py

PYTHONPATH=scripts .venv/bin/python scripts/test_energy_augmented_indicator.py
PYTHONPATH=scripts .venv/bin/python scripts/build_confidence_scores.py
PYTHONPATH=scripts .venv/bin/python scripts/make_release_aware_report.py
PYTHONPATH=scripts .venv/bin/python scripts/ensure_cp949_csv.py
```

대시보드 업데이트 후에는 기존 서버를 먼저 종료한다.

```bash
python3 scripts/stop_dashboard_server.py 8000
python3 -m http.server 8000
```

## 7. 다음 개선 방향

1. 공표일 메타데이터를 실제 출처별로 더 촘촘히 채워 forecast-origin 판정을 개선한다.
2. 시도별 분기 actual 출처를 KOSIS/지자체에서 추가 탐색해 사후 검증 대상을 늘린다.
3. 전기·가스 외생변수는 현재 자동 보정 성능이 낮으므로, 지역별 발전/수요 proxy를 추가한 뒤 재검증한다.
4. 읍면동 추정은 상업적 활용 가능성이 크지만 D등급 영역이 많으므로 카드매출, 사업체, 인구이동, 상권 proxy 등 민간/공공 후보를 추가해야 한다.
