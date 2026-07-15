# 추정값 등급·메타데이터 정책

## 목적

RECI 프로젝트의 산출값은 공식 벤치마크, rolling 예측, 시군구 하향 추정, 읍면동 프록시 배분이 섞여 있다. 같은 그래프에 표시되더라도 값의 신뢰도와 해석 범위는 서로 다르므로, 모든 핵심 산출물에 companion metadata를 붙여 `값의 성격`을 명확히 구분한다.

## 등급 체계

| 등급 | 의미 | 예시 |
|---|---|---|
| A | 공식 연간 벤치마크로 닫힌 값 | 시도 분기 GVA, RECI 지수 |
| B | rolling backtest 또는 공식 시군구 벤치마크로 검증 가능한 값 | rolling 예측, 시군구 분기 GVA |
| C | 상위 총량 제약은 만족하지만 세부 산업은 프록시 배분인 값 | 시군구 제조업 KSIC 세부 추정 |
| D | 공식 하위 GVA가 없고 고정 프록시 가중치에 의존하는 탐색용 값 | 읍면동 GVA 프록시 |

## 생성 파일

`scripts/build_estimate_metadata.py`가 다음 companion CSV를 생성한다. 모든 CSV는 CP949로 저장한다.

| 파일 | 등급 | 설명 |
|---|---:|---|
| `all_industries_quarterly_gva_metadata.csv` | A | 시도 산업별 분기 GVA |
| `rolling_quarterly_gva_prediction_metadata.csv` | B | 목표연도별 rolling 분기 예측 |
| `sigungu_quarterly_gva_metadata.csv` | B | 시군구 산업별 분기 GVA |
| `detailed_industry_quarterly_metadata.csv` | C | 시군구 제조업 KSIC 세부 프록시 |
| `emd_quarterly_gva_metadata.csv` | D | 읍면동 산업별 프록시 |
| `reci_quarterly_index_metadata.csv` | A | RECI 분기 지수 |
| `reci_rolling_validation_metadata.csv` | B | RECI rolling 검증 |
| `estimate_metadata_summary.csv` | - | 메타데이터 생성 요약 |

## 해석 규칙

1. A등급은 공식 연간 총량과 회계적으로 정합적인 benchmarked estimate로 표시한다.
2. B등급은 검증 가능한 nowcast/prediction 또는 공식 시군구 벤치마크 기반 추정으로 표시한다.
3. C등급은 상위 총량 제약이 맞는 세부산업 proxy allocation으로 표시한다.
4. D등급은 읍면동 공식 GVA가 아니라 exploratory proxy로 표시한다.
5. 대시보드와 외부 보고서에서는 `benchmark_status`, `confidence_grade`, `method_note`를 함께 노출해 값의 성격을 숨기지 않는다.
