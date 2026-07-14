# 국제문헌 기준 방법론 타당성 검토

## 검토 질문

현재 프로젝트는 연간 GRVA, 분기 지표, 시군구·읍면동 보조자료를 결합해 분기·소지역 GVA를 추정한다. 이 접근이 국제적으로 납득 가능한 방법인지, 과도한 논리적 비약이 있는지 검토했다.

## 참고한 문헌·자료

- Denton, F. T. (1971), *Adjustment of monthly or quarterly series to annual totals: an approach based on quadratic minimization*.
- IMF, *Quarterly National Accounts Manual*, 2017 edition.
- Eurostat, *Handbook on quarterly national accounts*, 2013 edition.
- Vera-Jaramillo (2025), *tempdisagg: A Python Framework for Temporal Disaggregation of Time Series Data*, arXiv:2503.22054.
- Ghosh and Steorts (2013), *Two-stage Benchmarking as Applied to Small Area Estimation*, arXiv:1305.6657.
- Steorts (2014), *Smoothing, Clustering, and Benchmarking for Small Area Estimation*, arXiv:1410.7056.

## 판단 요약

| 작업 | 타당성 | 판단 |
| --- | --- | --- |
| 연간 시도 GRVA를 분기 지표로 비례형 덴튼 배분 | 높음 | Denton 계열 시간분해/벤치마킹의 표준 사용처와 부합 |
| 2024·2025를 직전 비율로 외삽 | 중간 | nowcasting/monitoring 용도로 가능하나 확정 통계로 해석하면 안 됨 |
| 시군구 연간 GRVA를 벤치마크로 분기화 | 높음 | 연간 시군구 합계 제약이 있으므로 시도 방식과 같은 논리 |
| 부모 시도 분기 프로파일을 시군구 분기 지표로 사용 | 중간 | 직접 시군구 분기 지표 부재 시 합리적 대체이나, 시군구별 이질적 계절성을 놓칠 수 있음 |
| 읍면동 사업체·종사자 자료로 시군구 GVA를 하향 배분 | 낮음~중간 | small area estimation/benchmarking과 유사하지만, GVA 직접 관측이 아니므로 프록시 배분으로 명시해야 함 |
| KSIC 소분류·세분류를 시군구까지 확정 추정 | 낮음 | KOSIS 자료가 주로 시도/전국 수준이라 시군구 세부 업종값은 보조 배분 이상으로 주장하기 어려움 |

## 방법별 검토

### 1. 비례형 덴튼

비례형 덴튼은 저빈도 총량을 고빈도 지표의 움직임을 따라 분해하면서 연간 합계 제약을 만족시키는 방식이다. `tempdisagg` 문헌도 Denton, Chow-Lin, Litterman, Fernández 등을 저빈도 통계를 고빈도 추정치로 변환하는 고전적 시간분해 방법군으로 정리한다.

따라서 `연간 GRVA + 분기 생산지수/서비스업생산지수` 조합은 방법론적으로 타당하다. 현재 코드도 연간 합계 제약을 정확히 만족시키는지 진단하고 있으므로, 공식통계 복원 실험으로 설명할 수 있다.

### 2. 롤링 외삽

직전 벤치마크 분기의 `GVA / indicator` 비율을 유지해 다음 연도를 외삽하는 방식은 단기 모니터링에는 사용할 수 있다. 다만 이는 연간 실제 GRVA가 공개되기 전의 잠정 예측이다.

따라서 산출물 이름과 설명은 다음처럼 구분해야 한다.

- `benchmarked estimate`: 실제 연간 GRVA 제약으로 닫힌 값
- `extrapolated prediction`: 연간 GRVA가 아직 없는 기간의 외삽값

2024·2025 값은 후자로 관리하는 것이 안전하다.

### 3. 시군구 분기화

시군구 연간 GRVA가 존재하므로, 시군구 분기화는 시도 분기화와 같은 벤치마킹 문제다. 부모 시도 분기 GVA 프로파일을 지표로 쓰는 것은 직접 시군구 분기 지표가 없을 때의 보수적 대체안이다.

하지만 다음 한계는 명시해야 한다.

- 같은 시도 안의 모든 시군구가 동일한 분기 패턴을 가진다는 강한 가정이 들어간다.
- 산업별로 시군구 특화 계절성이 있으면 반영되지 않는다.
- 시군구별 월·분기 사업체 활동자료가 확보되면 그 자료를 우선해야 한다.

### 4. 읍면동 하향 배분

small area estimation 문헌은 작은 지역에 직접 추정치가 부족할 때 보조자료를 사용하고, 상위 총량과 일치하도록 benchmarking constraint를 부여하는 접근을 다룬다. 이 프로젝트의 읍면동 확장도 같은 계열의 아이디어와 닮아 있다.

다만 현재 확보 가능한 읍면동 자료는 사업체수, 종사자수, 매출액 같은 프록시다. GVA 자체가 아니다. 따라서 읍면동 결과는 다음 표현이 적절하다.

- 가능: `시군구 GVA의 읍면동 프록시 배분 추정`
- 부적절: `읍면동 공식 GVA 추정`

읍면동 추정은 반드시 시군구 합계와 일치하도록 constrained allocation 또는 raking을 적용해야 하며, 불확실성을 별도 점수로 표시하는 것이 좋다.

## 과도한 비약 방지 규칙

1. 연간 벤치마크가 있는 단위와 없는 단위를 라벨로 구분한다.
2. 직접 관측 지표와 프록시 지표를 같은 신뢰도로 표시하지 않는다.
3. 2024·2025 외삽값은 사후 벤치마크 전까지 예측값으로만 표기한다.
4. 읍면동 값은 시군구 합계 일치 제약을 통과한 경우에만 배포한다.
5. KSIC 소분류·세분류는 지역 하위 자료가 부족하므로 업종 구조 보조 배분으로만 사용한다.
6. 모든 결과 테이블에 `method`, `benchmark_status`, `source_resolution`, `constraint_error`를 포함한다.

## 최종 판단

현재 프로젝트의 핵심 방법론은 국제적으로 납득 가능한 범위에 있다. 특히 연간 GRVA를 분기 지표로 비례형 덴튼 배분하는 부분은 공식통계 시간분해 문제와 잘 맞는다.

다만 읍면동과 KSIC 세분류 확장은 직접 관측값이 아니라 프록시 기반 하향 배분이다. 포트폴리오와 보고서에서는 이를 명확히 표시해야 한다. “공식 GVA를 복원했다”가 아니라 “공식 상위 벤치마크에 합계가 일치하는 소지역 프록시 추정 데이터베이스를 구축했다”라고 설명하는 것이 정확하다.

## 참고 링크

- IMF Quarterly National Accounts Manual: https://www.imf.org/external/pubs/ft/qna/
- Eurostat Handbook on quarterly national accounts: https://ec.europa.eu/eurostat
- tempdisagg paper: https://arxiv.org/abs/2503.22054
- Two-stage benchmarking for small area estimation: https://arxiv.org/abs/1305.6657
- Constrained benchmarking for small area estimation: https://arxiv.org/abs/1410.7056
