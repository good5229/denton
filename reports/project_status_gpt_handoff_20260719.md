# 지역·산업별 GVA/RECI 추정 프로젝트 현황 정리

작성일: 2026-07-19  
저장소: `/Users/bellhundred/git-repo/denton`  
현재 브랜치: `main`  
최신 커밋: `2628e66 feat: add partial statistics phase28 gva forecastability audit`

이 문서는 현재까지의 프로젝트 진행상황을 다른 GPT에게 전달하기 위한 handoff 문서다. 목적은 실험 개선이 지지부진한 이유를 제3자의 관점에서 진단하고, 더 나은 실험 설계와 데이터 확보 방향을 찾는 것이다.

---

## 1. 프로젝트 목적

이 프로젝트는 공식 통계기관에서 충분히 빠르고 세밀하게 제공하지 않는 지역·산업별 경제활동 지표를 복원·예측하려는 작업이다.

궁극 목표는 다음과 같다.

1. 지역 단위: 시도 → 시군구 → 읍면동까지 세분화
2. 산업 단위: KSIC 대분류 → 중분류 → 소분류/세분류까지 세분화
3. 시간 단위: 연간 → 분기 → 월간까지 세분화
4. 목표 변수: 지역×산업별 총부가가치(GVA/GRDP), 그리고 이를 기반으로 한 RECI형 지역경기상황지수
5. 실제 사용 목적: 상업적으로 의미 있는 수준의 지역·업종별 경제활동 추정 및 대시보드/포트폴리오 제시

초기 방법론은 한국은행 BOK 이슈노트의 지역경기상황지수 개발 방식을 참고했다. 핵심은 산업생산지수, 서비스업생산지수, GRDP/GVA, GDP 디플레이터, 산업별 보조지표를 이용해 고빈도·세분화 지표를 만들고, 비례형 Denton법과 계층 정합(reconciliation)으로 상위 통계와 합계를 맞추는 것이다.

---

## 2. 현재까지 확보·활용한 데이터 축

### 2.1 공식 GVA/GRDP 계열

- 시도 단위 연간/분기 GRDP 또는 GVA
- 시군구 단위 연간 GRDP/GVA
- 일부 서울시 자치구 연간 총부가가치
- 전국 산업별 GDP/GVA 및 디플레이터
- KOSIS, ECOS, 서울 열린데이터광장 등 API/웹자료 활용

중요한 제약:

- 시군구×산업×분기 공식 actual은 일반적으로 직접 제공되지 않는다.
- 읍면동×산업×GVA actual은 거의 없고, 서울 등 일부 지역의 proxy 또는 준actual만 가능하다.
- 따라서 많은 하위 단위 결과는 “실제 예측 검증”이 아니라 “상위합 제약을 만족하는 배분”에 가깝다.

### 2.2 생산/활동 지표

- 광공업생산지수
- 서비스업생산지수
- 산업생산지수 2020년 기준 및 일부 2015년 기준 연장 가능성 검토
- 전력 사용량(KEPCO 계열)
- 건축HUB 인허가/착공/사용승인 이벤트 후보
- 공장등록, 산업단지, 사업체/종사자, 경제총조사, 읍면동 proxy 후보

중요한 제약:

- 일부 자료는 현재 시도 단위까지만 안정적으로 붙는다.
- 시군구 단위 구조자료는 확보되더라도 publication date, first eligible period, historical vintage가 불명확한 경우가 많다.
- 이 때문에 과거 시점 기준 예측에서 사용하면 data leakage 위험이 커진다.

### 2.3 구조적 feature 후보

현재까지 탐색한 구조 feature는 다음과 같다.

- 시군구×산업×연도 종사자 수
- 시군구×산업×연도 사업체 수
- 공장등록 snapshot
- 산업단지 생산/입주/면적
- 건축 인허가·착공·사용승인
- 전력 사용량
- 농림어업 관련 면적/농가/작물 proxy
- 광업 관련 광산·채굴 proxy
- 전기가스업 관련 전력·연료·환율·석탄·천연가스·유가 proxy
- 행정구역/수도권/도시위계/산업벨트/공간 그래프/인접행렬

하지만 대부분은 아직 “모델 학습에 바로 쓸 수 있는 ML-ready feature”로 승격되지 못했다. 특히 release date와 historical coverage가 반복적으로 문제였다.

---

## 3. 주요 방법론 흐름

### 3.1 Denton/배분 기반

기본 구조는 다음과 같다.

1. 상위 연간 GVA 또는 GRDP를 anchor로 둔다.
2. 산업생산지수 또는 서비스업생산지수 등 고빈도 indicator를 이용해 분기/월 profile을 만든다.
3. 비례형 Denton법으로 연간합 제약을 만족하도록 고빈도 값을 조정한다.
4. 시도 → 시군구 → 읍면동, 대분류 → 중분류 → 소분류 방향으로 share 또는 proxy를 이용해 배분한다.
5. 계층 정합으로 상위합과 하위합을 맞춘다.

장점:

- 회계적으로 일관된 결과를 만들기 쉽다.
- 공식 연간값이 있으면 연간합은 정확히 맞출 수 있다.
- baseline으로 매우 강력하다.

단점:

- 이미 아는 연간값을 나눠 갖는 것은 진짜 예측 성능이 아니다.
- 하위 분기/월 actual이 없으면 직접 정확도 검증이 어렵다.
- share가 안정적인 산업/지역에서는 잘 작동하지만, 구조 변화가 큰 산업에서는 약하다.

### 3.2 ML 보정 실험

여러 차례 ML 실험을 수행했다.

사용한 접근:

- Ridge/ElasticNet/Huber
- XGBoost 등 tree model
- residual correction
- share/log-ratio reconciliation
- global pooled model
- sector-specific model
- partial pooling
- regret gating
- adaptive shrinkage
- feature ablation
- electricity feature ablation
- spatial/industry share-change model

반복된 결과:

- 복잡한 ML 모델이 투명한 baseline을 안정적으로 이기지 못했다.
- 일부 fold나 일부 그룹에서는 개선이 있었지만, 전체 WMAPE 또는 worst group에서 악화가 자주 발생했다.
- data leakage를 막는 strict vintage 기준을 적용하면 사용할 수 있는 feature가 크게 줄었다.
- 고오차 산업(광업, 전기가스, 농림어업, 건설 등)은 일반 feature로 설명력이 부족했다.

### 3.3 검증 원칙

현재 프로젝트는 다음 guardrail을 점점 강화해 왔다.

- baseline과 challenger는 반드시 동일 evaluation population에서 비교
- 미래에 공표된 데이터를 과거 예측에 사용하지 않음
- official actual을 본 뒤 선택한 파라미터는 prospective policy로 사용하지 않음
- coverage와 prediction performance를 분리
- 상위합 정합성 100%를 예측 정확도라고 주장하지 않음
- 직접 actual이 없는 분기/월/읍면동 결과는 component validation 또는 structural uncertainty로만 표현
- 고정 10/20/30% interval 같은 근거 없는 prediction interval 제거

---

## 4. 단계별 진행 요약

### 4.1 초기 확장 및 대시보드

초기에는 KOSIS/ECOS/서울시 자료를 수집해 시도·시군구·읍면동 및 산업별 GVA 추정 대시보드를 만들었다.

주요 이슈:

- 지역명이 코드로 표시되는 문제를 수정했다.
- 시도/시군구/읍면동 선택 UI를 검색·복수선택 모달로 개선했다.
- 산업군도 대/중/소/세분류 검색으로 나눴다.
- 예측값과 실제값을 같은 색상, 예측값 점선, 실제값 실선으로 표시하도록 차트 개선을 진행했다.
- Plotly 등으로 차트 안정성을 높이는 방향을 반영했다.

중요한 인식 변화:

- 시군구 연간 actual이 있는 경우 이를 배분해 만든 값이 actual과 100% 일치하는 것은 예측 성능이 아니다.
- “실제 정부 공식 통계값”과 “공식 연간값을 나눠 만든 benchmarked allocation”을 명확히 구분해야 한다.

### 4.2 시군구 ML 실험

시군구×산업 GVA를 대상으로 global pooled model, sector model, XGBoost, residual correction 등을 실험했다.

주요 결론:

- 기존 feature만으로는 시군구 share/residual을 안정적으로 개선하기 어렵다.
- oracle upper bound조차 큰 개선을 보이지 않는 구간이 있었다.
- 따라서 단순히 모델만 복잡하게 바꾸는 것은 효과가 작았다.
- 직접적인 생산활동 feature가 필요하다는 결론이 나왔다.

이후 ML restart 조건:

- 시군구×산업×연도 수준의 종사자/사업체 feature
- 전력 사용량의 vintage-aware panel
- 공장등록/산업단지/건축 activity
- 산업별 특화 feature
- publication lag가 검증된 source

### 4.3 전력 feature 실험

KEPCO 전력 feature를 활용해 시군구 ML 보정을 시도했다.

결론:

- 전력 feature는 일부 신호가 있으나 standalone residual correction으로는 안정적인 승격 실패
- all-sector total에서는 개선이 보이기도 했지만 C00 제조업 또는 특정 sector에서 악화
- placebo, bootstrap, leave-one-sido-out, lag/missingness guardrail에서 충분히 안정적이지 않음
- 최종적으로 전력 단독 policy는 종료
- 전력은 향후 공장등록·산업단지·건축·사업체 feature와 interaction으로만 재검토

핵심 원인:

- 전력은 활동량 proxy이지만 산업별 GVA 변동과 일대일 대응하지 않는다.
- 전기/가스업이나 제조업 일부에는 강할 수 있으나 서비스·농림·광업 등에는 불균질하다.
- 시점별 공표 가능성/vintage를 엄격히 적용하면 사용 가능한 구간이 제한된다.

### 4.4 구조자료 수집

공공데이터포털, 건축HUB, 공장등록, 산업단지, 법정동코드, SGIS geometry 등 구조자료를 탐색했다.

성과:

- 법정동코드 전체자료 로컬 확보
- 건축HUB API 승인 후 pilot feature 생성
- 건축허가/착공/사용승인 event date 분리
- 공장등록 snapshot 일부 파싱
- 산업단지 geometry/공간 그래프 일부 정비
- KSIC 8/9/10 연계표 자료 확인 및 mapping 작업
- SGIS 기반 시군구 geometry/queen/rook/distance graph 일부 생성

계속 막힌 부분:

- 전국 historical monthly/annual coverage 미완료
- release timestamp/first eligible period 불명확
- 공장등록 snapshot이 특정 시점 stock 자료라 flow feature로 쓰기 어려움
- 건축HUB startDate/endDate 조회가 실제 event filter인지 불명확했던 구간 존재
- VWorld 산업단지 SHP 등 일부 source 다운로드/검증 문제
- KSIC crosswalk에서 unresolved row/employee 비율이 gate threshold를 만족하지 못한 구간 존재

### 4.5 Partial Statistics Estimation Phase 5~28

Phase 5 이후는 “부분관측 통계 복원”이라는 관점에서 실험을 더 엄격하게 정리한 흐름이다.

핵심 전환:

- 단순히 많은 행을 만들기보다, 각 행이 observed actual인지, forecast인지, allocation인지, fallback인지 구분
- official actual을 숨기는 rolling-origin backtest 강화
- strict/pseudo source track 분리
- release-date가 없는 feature는 production model에 쓰지 않음
- future/prospective archive를 backdating하지 않음

최근 Phase별 요약:

| Phase | 핵심 내용 | 결론 |
| --- | --- | --- |
| Phase 21~22 | official quarterly GRDP materialization/acquisition | 분기 공식 target 확보와 성장률 정합 점검 |
| Phase 23 | official growth alignment, period-key integrity | period key와 official growth 정렬 강화 |
| Phase 24 | unique-policy verification, origin governance | 정책별 unique 비교와 origin 통제 |
| Phase 25 | release-dated source qualification | QP2 등 개선 후보가 R1-R3 release-dated source 부족으로 blocked |
| Phase 26 | semantic series recovery | 지표 의미 회복, GDP/서비스/전력 source 정리, SW0 유지 |
| Phase 27 | hierarchical fine-grained modeling | 서비스업생산 17지역×14업종×20분기 수집, fine cube 생성, challenger 대부분 미승격 |
| Phase 28 | forecastability audit | observed anchor와 forecast/allocation 분리, annual forecast 생성, baseline 유지 |

---

## 5. 최신 Phase 28 결과

최신 보고서: `reports/partial_statistics_estimation_phase28_gva.md`

### 5.1 핵심 상태

```text
status = forecastability_audited;actual_anchor_grade_O;annual_anchor_forecast_created;forward_release_ledger_active;incumbents_retained
target = GVA
price basis = real_growth_and_nominal_level_tracks_separated
production_use = false
official_statistics_claim = false
```

### 5.2 관측/예측/배분 분리

Phase 28에서 과거 공식 연간 GVA anchor를 예측값으로 보지 않도록 재분류했다.

| 구분 | 상태 | 등급 | 행 수 |
| --- | --- | --- | ---: |
| 과거 공식 연간 anchor | observed_official_actual | O | 11,732 |
| 2024 prospective annual forecast | prospective_forecast | A | 2,297 |
| 분기 배분 | development_allocation | D | 46,928 |
| 월 배분 | experimental_allocation | E | 140,784 |

중요:

- 과거 official actual은 Grade A가 아니라 Grade O다.
- 분기 4배, 월 12배로 행 수가 증가한 것은 예측 성능 개선이 아니다.
- 분기/월 direct actual이 없으므로 empirical accuracy를 주장하지 않는다.

### 5.3 NA1 completeness

시군구×KSIC 대분류×연도 이론 cell:

```text
223 regions × 16 industries × 4 years = 14,272 cells
```

결과:

| 항목 | 값 |
| --- | ---: |
| theoretical cell count | 14,272 |
| observed cell count | 11,579 |
| observed row count | 11,732 |
| missing source cell count | 2,693 |
| coverage rate | 0.8113 |
| suppression count | 0 |
| not applicable count | 0 |

현재 결측은 주로 `missing_source`로 분류되어 있으며, true zero/statistical suppression/not applicable 등을 충분히 분리하지 못한 상태다.

### 5.4 Annual Anchor Forecast 성능

rolling-origin annual anchor backtest를 수행했다.

| Policy | 설명 | WMAPE | MAPE | Median APE | 상태 |
| --- | --- | ---: | ---: | ---: | --- |
| AN0_lag_level | 전년도 GVA 수준 유지 | 0.07598 | 0.24759 | 0.06362 | baseline |
| AN1_lag_growth | 전년도 성장률 반복 | 0.09671 | 0.35542 | 0.07628 | baseline |
| AN2_parent_growth | 시도/산업 성장률 적용 | 0.07843 | 0.26148 | 0.06579 | baseline |
| ANR_shrunk_lag_parent_growth | shrinked challenger | 0.08493 | 0.30399 | 0.06862 | challenger_development |

결론:

- 최강 baseline은 `AN0_lag_level`
- challenger는 baseline보다 악화되어 승격하지 못함
- selected annual policy는 `AN0_lag_level`

### 5.5 Worst group

Annual forecast 기준 주요 오차:

| 항목 | 값 |
| --- | --- |
| annual macro region WMAPE | 0.0740 |
| annual macro industry WMAPE | 0.0971 |
| annual worst-decile APE | 0.3065 |
| worst region | 인천광역시 |
| worst industry | F00, 건설업 |
| worst year | 2022 |

과거 다른 검증에서는 official actual 기준 상위 오차가 광업(B), 전기가스(D), 농림어업(A)에 집중되기도 했다. Phase28 annual forecast에서는 F00 건설업이 worst industry로 나타났다. 즉 high-error 산업은 평가 population과 target 정의에 따라 달라진다.

### 5.6 Parent/Spatial/Industry/Temporal 정책

| 축 | 현재 선택 | Challenger 상태 |
| --- | --- | --- |
| Parent | QP1_G_national_growth_bridge | PR2/PR3 blocked, nested CV not scored |
| Spatial | SW0_last_annual_gva_share | SWD_feature_share_change blocked |
| Industry | IS0_previous_year_industry_share | employee/business share-change blocked |
| Quarterly | TP1_project_parent_proxy_profile | service profile development ready but not promoted |
| Monthly | TM0_equal_month | native monthly source coverage 0.0 |
| Reconciliation | proportional_reconciliation_same_price_basis | 유지 |

### 5.7 Interval

50/80/95% interval은 모두 `not_calibrated`로 표시했다.

이전의 고정 10/20/30% interval width는 근거 없는 placeholder이므로 제거했다. 현재는 empirical prediction interval을 주장할 수 없다.

---

## 6. 왜 실험 개선이 지지부진한가

아래는 현재까지 관찰된 주요 병목이다.

### 6.1 baseline이 너무 강하다

시군구×산업 GVA는 단기적으로 전년도 level/share가 강한 baseline이다.

특히:

- 지역별 산업구조 share는 상당히 안정적이다.
- 공식 연간값을 anchor로 쓰면 회계 정합성이 높다.
- 작은 cell은 변동성이 크지만 전체 WMAPE에서는 대형 cell의 안정성이 지배한다.

따라서 새로운 feature가 약간의 signal을 가져도 baseline 대비 개선 폭이 작다.

### 6.2 실제 예측 target이 부족하다

많은 하위 단위에는 공식 actual이 없다.

- 시군구×산업×분기 official actual 없음
- 시군구×중분류/소분류 GVA official actual 제한적 또는 없음
- 읍면동×산업 GVA actual 거의 없음
- 월별 GVA actual 없음

이 때문에 모델이 좋아졌는지 직접 검증하기 어렵고, 상위합 정합성이나 proxy validation에 머무른다.

### 6.3 “배분”과 “예측”이 섞이면 성능 착시가 생긴다

시군구 연간 actual을 알고 이를 분기/월로 나누면 연간합은 당연히 맞는다. 그러나 이것은 미지의 값을 예측한 것이 아니다.

최근 Phase28에서 이를 분리했다.

- observed_official_actual: 공식값
- backtest_prediction: actual을 숨기고 만든 과거 예측
- prospective_forecast: 공표 전 미래 예측
- development_allocation: 직접 actual 없는 배분
- experimental_allocation: 균등 또는 약한 proxy 배분

이 구분 이후 실제로 평가 가능한 “예측” 범위가 크게 줄었다.

### 6.4 data leakage guardrail이 강해질수록 usable feature가 줄어든다

사용자 요구상 예측 시점 기준으로 공표되지 않은 데이터를 사용하면 안 된다.

예:

- 어떤 2024년 월별 지표를 예측할 때, feature C가 2025년 12월에 발표된다면 C의 2024년 값은 사용할 수 없다.
- 익익년도 12월 발표 자료는 해당 시점 이전 nowcast/forecast에 사용 불가

이 원칙을 적용하면 종사자/사업체/경제총조사/건축/공장등록 자료 중 상당수가 historical backtest에서 사용 불가능하거나 pseudo track으로만 남는다.

### 6.5 구조 feature가 ML-ready가 아니다

전력 외 구조 feature는 아직 아래 조건을 충분히 만족하지 못했다.

- 전국 coverage
- 산업 coverage
- 시군구 crosswalk 안정성
- KSIC version crosswalk 안정성
- publication date
- first eligible period
- historical vintage
- flow/stock 의미 구분
- target과 같은 기간에 쓸 수 있는지 여부

따라서 structural feature challenger는 대부분 blocked 상태다.

### 6.6 산업별 동학이 다르다

광업, 전기가스, 농림어업, 건설업은 일반적인 lag/share/생산지수로 설명하기 어렵다.

가능한 이유:

- 광업: 소수 사업장, 지역별 큰 jump, commodity/광산 단위 shock
- 전기가스: 발전소 위치, 연료가격, 정책/요금, 환율, 에너지 mix
- 농림어업: 기상, 작황, 면적, 재해, 가격, 계절성
- 건설업: 대형 프로젝트, 인허가-착공-기성 간 lag, 지역별 개발 cycle

전체 pooled model이 이런 산업을 동시에 설명하면 평균적으로 안전한 baseline으로 수렴하기 쉽다.

### 6.7 소형 cell과 near-zero cell 문제가 크다

시군구×산업으로 내려가면 작은 cell이 많다.

문제:

- actual이 작으면 APE가 폭발한다.
- 0 또는 거의 0인 cell에서 log transform과 ratio가 불안정하다.
- pooled WMAPE는 대형 cell 중심, MAPE는 소형 cell에 민감해 metric 간 정책 선택이 달라진다.

따라서 현재 metric과 loss가 상업적 목표와 잘 맞는지도 재검토 필요하다.

### 6.8 ML 모델이 target 구조를 충분히 반영하지 못했다

시도한 모델은 많지만, 대부분 다음 제약을 깊게 통합하지 못했다.

- compositional share sum-to-one
- 시도 parent total과 시군구 child sum
- 산업 parent와 세부산업 child sum
- annual-to-quarter-to-month accounting identity
- spatial autocorrelation
- industry hierarchy
- region type hierarchy
- release-aware missingness

단순 XGBoost/Ridge residual correction은 이런 계층 구조를 사후 reconciliation으로 맞추는 수준에 머물렀다.

### 6.9 feature의 설명 대상이 “GVA”가 아니라 “활동량”일 수 있다

전력, 사업체 수, 종사자 수, 공장 수, 인허가 면적은 생산활동 proxy다. 그러나 GVA는 가격, 생산성, 부가가치율, 산업구조, 중간투입 변화의 영향을 받는다.

예:

- 전력 사용량이 증가해도 부가가치가 동일하게 증가하지 않을 수 있다.
- 사업체 수 증가가 고부가가치 증가를 뜻하지 않을 수 있다.
- 건축허가는 미래 건설활동의 선행지표지만 해당 분기 GVA와 lag가 복잡하다.

따라서 feature engineering에서 “활동량 → 부가가치” 변환을 더 명시적으로 다뤄야 한다.

---

## 7. 현재 주장할 수 있는 것과 없는 것

### 7.1 주장 가능한 것

- 공식 연간 GVA anchor와 배분값을 구분하는 체계가 만들어졌다.
- 시군구×KSIC 대분류 연간 anchor forecast backtest를 수행했다.
- 현재 최강 연간 baseline은 lag-level이다.
- Phase28 기준 annual baseline WMAPE는 약 7.60%다.
- challenger는 현재 baseline을 안정적으로 이기지 못했다.
- 전력 단독 residual correction은 운영정책으로 승격하지 않는다.
- 분기/월 결과는 개발/실험 배분이며 직접 GVA accuracy는 주장하지 않는다.
- interval은 아직 calibration되지 않았다.
- production use 또는 official statistics equivalence는 주장하지 않는다.

### 7.2 아직 주장하면 안 되는 것

- 시군구×산업×분기 GVA를 실제 official actual 수준으로 예측했다고 주장
- 읍면동×산업 GVA accuracy가 검증됐다고 주장
- 중분류/소분류 GVA accuracy가 official actual로 검증됐다고 주장
- 분기/월 forecast row 수 증가를 accuracy 개선이라고 주장
- 상위합 정합 100%를 예측 성공이라고 주장
- 전력/건축/공장등록 feature가 ML-ready이며 성능 개선한다고 주장
- calibrated prediction interval 또는 coverage를 주장
- Phase27 PR1 beta=-0.5 같은 official-visible 진단 가설을 prospective policy로 사용

---

## 8. GPT에게 묻고 싶은 핵심 질문

다음 GPT에게는 아래 질문을 중심으로 의견을 구하고 싶다.

### 8.1 실험 설계 진단

1. 현재처럼 strict vintage/release-date guardrail을 적용하면 사용 가능한 feature가 너무 줄어든다. 이 상황에서 어떤 실험 설계가 가장 타당한가?
2. official actual이 희소한 상황에서 proxy validation, accounting reconciliation, component validation을 어떻게 계층적으로 평가해야 하는가?
3. 시군구×산업×연간 forecast와 시군구×산업×분기/month allocation을 별도 문제로 분리한 현재 구조가 적절한가?
4. “상업적으로 쓸 만한 읍면동×소분류 지표”를 만들려면 accuracy claim을 어떤 식으로 제한해야 하는가?

### 8.2 모델링 전략

1. lag-level/share baseline이 강한 상황에서 ML이 이길 수 있는 target을 어떻게 재정의해야 하는가?
2. level 예측보다 growth, residual, share-change, rank-change, direction, anomaly detection 중 무엇이 더 적합한가?
3. XGBoost 같은 tree model을 계속 쓴다면 어떤 target transform과 loss/weighting을 써야 하는가?
4. compositional/hierarchical constraint를 모델 내부에 반영하는 더 좋은 방법은 무엇인가?
5. Bayesian hierarchical model, state-space model, mixed-frequency dynamic factor model, small area estimation, temporal hierarchical forecasting 중 어느 접근이 가장 유망한가?
6. 고오차 산업인 광업, 전기가스, 농림어업, 건설업은 pooled model에서 제외하고 산업별 특화모델로 다루는 것이 나은가?

### 8.3 데이터 전략

1. 시군구×산업 GVA 예측력을 높이기 위해 가장 먼저 확보해야 할 데이터는 무엇인가?
2. 종사자/사업체/전력/공장등록/건축/산업단지/농지/기상/연료가격 중 실제 GVA forecast에 가장 유효할 가능성이 높은 source 조합은 무엇인가?
3. release date가 불명확한 자료를 development-only로 사용할 때, 어떤 방식으로 prospective 유효성을 검증할 수 있는가?
4. 읍면동 단위는 official actual이 거의 없는데, 어떤 준actual 또는 external validation target을 써야 하는가?

### 8.4 평가 metric 전략

1. WMAPE, MAPE, median APE, directional accuracy, aggregate error, worst-decile error 중 어떤 metric 조합이 상업적 사용성에 적합한가?
2. near-zero/small-cell 문제를 어떻게 다뤄야 하는가?
3. 대형 cell 중심의 WMAPE와 소형 cell 리스크를 함께 만족시키는 promotion gate를 어떻게 설계해야 하는가?
4. 실제값이 없는 분기/월 결과의 불확실성은 어떻게 정량화해야 하는가?

### 8.5 다음 실험 제안 요청

다음 GPT에게 구체적으로 요청하고 싶은 것은 다음이다.

1. 현재 실험이 baseline을 못 이기는 이유에 대한 가장 그럴듯한 원인 순위
2. 당장 구현 가능한 3개 실험안
3. 데이터 확보가 필요한 중기 실험안 3개
4. 고오차 산업별 특화모델 설계안
5. 시군구→읍면동, 대분류→소분류로 내려갈 때의 validation strategy
6. production claim 없이도 포트폴리오/상업적 PoC로 설득 가능한 output framing

---

## 9. 다음에 시도해볼 만한 실험 후보

아래는 현재 저장소 상황을 바탕으로 내가 보기에도 다음 단계 후보가 될 수 있는 방향이다.

### 9.1 Annual anchor forecast를 “level”이 아니라 “regime + residual”로 재설계

현재 AN0 lag-level이 강하다. 이를 직접 이기려 하기보다 다음처럼 분해할 수 있다.

```text
GVA_t = lag_level × parent_growth × local_share_change × sector_regime_adjustment
```

실험:

- target을 `delta_log_gva - parent_industry_growth`로 정의
- 소형 cell은 강한 shrinkage
- 지역×산업 random effect 또는 partial pooling
- sector별 cap 분리
- worst-decile 비악화 gate

### 9.2 고오차 산업만 별도 challenger

전체 pooled model 대신 산업별로 다른 feature set과 모델을 둔다.

후보:

- A 농림어업: 경지면적, 농가, 작물, 기상, 재해, 농산물가격
- B 광업: 광산 수, 채굴/출하, 지역별 광업 사업체, commodity price
- D 전기가스: 발전량, 전력판매량, LNG/석탄/유가, 환율, 발전소 위치
- F 건설업: 건축허가, 착공, 사용승인, 면적, 공공공사, lag structure

정책:

- 해당 산업에서만 challenger 사용
- 나머지는 baseline 유지
- 산업별 promotion gate를 별도 적용

### 9.3 Forecast target을 “값”이 아니라 “상대 변화/순위/방향”으로 분리

상업적으로는 정확한 금액보다 어느 지역·업종이 상승/하락하는지, 이상징후가 있는지가 중요할 수 있다.

실험:

- direction accuracy
- top-decile growth hit rate
- rank correlation
- anomaly detection
- regional relative performance index

이것은 RECI와도 더 자연스럽게 연결될 수 있다.

### 9.4 Component validation을 공식화

직접 actual이 없는 분기/월/읍면동 결과는 다음 component별로 검증한다.

- annual anchor forecast error
- spatial share stability error
- industry share stability error
- quarterly profile proxy error
- monthly profile proxy error
- reconciliation adjustment magnitude

각 component의 uncertainty를 합성해 final confidence score를 산출한다.

### 9.5 구조 feature의 release ledger부터 완성

모델보다 먼저 source별로 다음 표를 완성해야 한다.

```text
source_id
grain
frequency
reference_period
publication_date
first_eligible_period
region_coverage
industry_coverage
historical_coverage
vintage_available
flow_or_stock
target_applicability
```

이 표가 없으면 좋은 모델을 만들어도 leakage 논란 때문에 승격하기 어렵다.

---

## 10. 주요 산출물 위치

최신 핵심 보고서:

- `reports/partial_statistics_estimation_phase28_gva.md`
- `reports/partial_statistics_estimation_phase27_gva.md`
- `reports/partial_statistics_estimation_phase26_gva.md`
- `reports/validation_backtest_summary.md`
- `reports/municipality_ml_stop_decision.md`
- `reports/municipality_new_feature_dataset.md`
- `reports/electricity_preconfirmatory_policy_selection.md`
- `reports/next_structural_feature_workstreams.md`
- `reports/structural_feature_phase1_readiness.md`
- `reports/structural_phase2_long_running_data_discovery.md`
- `reports/structural_phase3_data_native_ksic_and_spatial_readiness.md`

주제별 index:

- `reports/README.md`
- `reports/topics/ml.md`
- `reports/topics/data.md`
- `reports/topics/methods.md`
- `reports/topics/validation.md`
- `reports/topics/overview.md`

최신 Phase28 실행/검증 코드:

- `scripts/run_partial_statistics_phase28_gva.py`
- `scripts/verify_partial_statistics_phase28_gva.py`
- `tests/test_partial_statistics_phase28_gva.py`

---

## 11. GPT에게 전달할 짧은 요청문 예시

아래 문장을 이 문서와 함께 GPT에게 전달하면 된다.

```text
첨부한 문서는 지역×산업별 GVA/GRDP를 시군구·읍면동 및 KSIC 세분류까지 복원/예측하려는 프로젝트의 현재 상태입니다.

현재 문제는 baseline(Denton, lag-level, previous share)이 매우 강하고, ML challenger가 strict vintage/leakage guardrail을 통과하면서 안정적으로 개선하지 못한다는 점입니다. 또한 하위 단위 actual이 부족해 배분과 예측이 섞이면 성능 착시가 발생합니다.

이 문서를 바탕으로:
1. 실험 개선이 지지부진한 가장 큰 원인을 진단하고,
2. 현재 데이터 조건에서 가장 유망한 모델링/검증 전략을 제안하고,
3. 추가 확보해야 할 데이터 우선순위를 정하고,
4. 고오차 산업별 특화모델과 validation gate를 설계해 주세요.

특히 미래 공표 데이터 사용으로 인한 data leakage를 피해야 하며, official actual이 없는 구간에서는 어떤 종류의 proxy/component validation을 주장할 수 있는지도 구분해 주세요.
```

---

## 12. 현재 결론

현재 프로젝트는 “많은 값을 생성하는 단계”에서는 상당히 진전했지만, “생성값이 진짜 예측으로서 baseline을 이기는가”에서는 아직 뚜렷한 성과가 제한적이다.

가장 큰 이유는 다음 세 가지로 보인다.

1. 시군구×산업 GVA는 lag/share baseline이 강하고 단기 구조가 안정적이다.
2. 하위 단위 official actual이 부족해 직접 검증 가능한 target이 적다.
3. leakage를 막으면 구조 feature 대부분이 아직 ML-ready가 아니다.

따라서 다음 개선은 단순히 더 복잡한 모델을 쓰는 것보다, target을 더 잘 정의하고, 산업별로 feature를 다르게 설계하며, release-aware source ledger와 component validation 체계를 먼저 완성하는 방향이 더 유망해 보인다.
