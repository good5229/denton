# 연간 모델링 패널

## 목적

ML 또는 통계모형을 실험하려면 시도, 시군구, 읍면동, 상세산업 산출물이 같은 형태의 long table로 정리되어야 한다. `modeling_panel_annual.csv`는 현재 산출물을 연간 단위로 표준화한 공통 입력 테이블이다.

## 포함 범위

- 시도 × 대분류 rolling 연간 예측과 official actual
- 시군구 × 대분류 연간 Denton 벤치마크 정합성 행
- 시군구 × 대분류 연간 forecast 행
- 시군구 × 제조업 중·소·세분류 연간 proxy allocation
- 시군구 × 서비스 중·소·세분류 연간 proxy allocation
- 읍면동 × 대분류 연간 proxy allocation

## 주요 컬럼

| 컬럼 | 의미 |
| --- | --- |
| `level` | `sido`, `sigungu`, `emd` |
| `industry_depth` | `large`, `middle`, `small`, `class` |
| `predicted_value` | 예측·추정·배분된 값 |
| `actual_value` | official actual, benchmark, proxy actual이 있을 때만 입력 |
| `actual_role` | actual 값의 성격 |
| `value_role` | forecast, benchmarked allocation, proxy allocation 구분 |
| `benchmark_status` | 부모값이 벤치마크 제약값인지 out-of-sample forecast인지 |
| `is_comparable` | 오차 계산이 가능한 행인지 여부 |

## 해석

`is_comparable=True`인 행만 직접 오차율 계산에 사용한다. `actual_role=benchmark`인 행은 예측 정확도가 아니라 회계 정합성 검증이다. `actual_role=proxy` 또는 `proxy_unavailable`인 행은 공식 actual이 아니므로 모델 학습 또는 검증 시 별도 가중치를 낮춰야 한다.
