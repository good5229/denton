# 읍면동·세부산업 추정 시퀀스

## 목적

상업적 활용을 위해서는 `시도 × 산업대분류`보다 더 낮은 해상도, 즉 `시군구/읍면동 × KSIC 소분류` 수준의 경기·부가가치 프록시가 필요하다. 현재 공개자료만으로 이 해상도의 분기 GVA actual은 직접 관측되지 않으므로, 본 프로젝트는 상위 공식 벤치마크에 합계가 맞는 하향 배분 추정 데이터베이스를 만든다.

## 근거가 되는 통계 방법

1. 시간 배분: 비례형 Denton
   - 연간 벤치마크를 분기 지표 흐름에 맞춰 배분하되, 분기 추정값 합이 연간 값과 일치하도록 제약한다.
   - 본 프로젝트의 시도·시군구 분기 GVA는 이 구조를 따른다.

2. 공간·산업 배분: benchmarked small-area allocation
   - 작은 지역·세부 산업에 직접 관측값이 없을 때, 보조자료를 가중치로 사용해 상위 총량을 하위 셀에 배분한다.
   - small area estimation과 benchmarking 문헌에서 공통적으로 요구하는 핵심은 “하위 추정치가 상위 총량과 정합적이어야 한다”는 점이다.

3. 해석 한계
   - 이 결과는 공식 읍면동 GVA가 아니다.
   - 정확한 표현은 “공식 상위 벤치마크에 합계가 일치하는 소지역·세부산업 GVA 프록시”이다.

참고:
- IMF, *Quarterly National Accounts Manual* 계열의 temporal disaggregation/benchmarking 원칙
- Ghosh and Steorts, “Two-stage Benchmarking as Applied to Small Area Estimation”, 2013, https://arxiv.org/abs/1305.6657
- Pfeffermann, “New Important Developments in Small Area Estimation”, 2013, https://arxiv.org/abs/1302.4907
- Okonek and Wakefield, “A Computationally Efficient Approach to Fully Bayesian Benchmarking”, 2022, https://arxiv.org/abs/2203.12195

## 현재 구축한 1차 시퀀스: 시군구 제조업 KSIC 세부

### 입력

| 단계 | 데이터 | 역할 |
|---|---|---|
| 상위 연간 벤치마크 | 시군구 경제활동별 GRVA | 시군구 제조업 연간 총량 |
| 상위 분기 경로 | `sigungu_quarterly_gva_estimates.csv` | 시군구 제조업 분기 총량 |
| 세부산업 프록시 | `expanded_manufacturing_sigungu_ksic.csv` | 시군구×KSIC 중·소·세분류의 사업체수, 종사자수, 부가가치 |

### 배분 규칙

각 시군구 `r`, 연도 `y`, KSIC 세부업종 `k`에 대해 프록시 비중을 만든다.

```text
w_{r,k,y} = proxy_{r,k,y} / Σ_k proxy_{r,k,y}
```

프록시는 아래 우선순위를 따른다.

1. 부가가치
2. 종사자수
3. 사업체수

분기 세부산업 GVA는 시군구 제조업 분기 총량에 이 비중을 곱한다.

```text
X_{r,k,y,q} = GVA_{r,C00,y,q} × w_{r,k,y}
```

프록시 연도가 없는 경우에는 가장 가까운 사용 가능 연도의 비중을 사용한다. 예를 들어 2019년 세부 제조업 프록시가 없으면 2020년 비중을 사용한다.

### 산출물

| 파일 | 설명 |
|---|---|
| `detailed_industry_quarterly_estimates.csv` | 시군구×KSIC 세부 제조업 분기 추정값 |
| `detailed_industry_annual_estimates.csv` | 분기 추정값을 연간 합산한 세부산업 추정값 및 프록시 actual 비교 |
| `detailed_industry_constraint_diagnostics.csv` | 세부산업 합계가 시군구 제조업 총량과 맞는지 검증 |

### 검증 결과

현재 산출 결과에서 세부산업 배분 합계와 시군구 제조업 부모 총량의 최대 절대 제약 오차는 약 `0.00000006` 백만원 수준이다. 이는 반올림 오차에 가까우므로, “상위 제조업 총량 정합성”은 충족된다.

종로구 제조업도 이 방식으로 분기 추정이 생성되었다. 예를 들어 2023년 종로구 제조업 중분류 연간 추정 상위 업종은 다음과 같다.

| KSIC | 업종 | 2023년 추정 GVA |
|---|---|---:|
| C33 | 기타 제품 제조업 | 221,360.762 |
| C14 | 의복·액세서리·모피제품 제조업 | 178,983.853 |
| C20 | 화학물질 및 화학제품 제조업 | 68,484.618 |
| C28 | 전기장비 제조업 | 28,258.821 |
| C18 | 인쇄 및 기록매체 복제업 | 21,978.139 |

## 읍면동 확장 시퀀스

읍면동은 아직 직접 GVA 벤치마크가 없다. 따라서 공식 GVA가 아니라 시군구 GVA를 읍면동 프록시로 하향 배분하는 방식으로 접근한다.

1. 시군구 분기 GVA를 부모 총량으로 둔다.
2. 읍면동별 사업체수·종사자수·매출액 프록시를 수집한다.
3. 산업대분류 또는 KSIC 가능한 수준에서 읍면동 비중을 만든다.
4. 시군구 총량을 읍면동으로 배분한다.
5. 검증 가능한 지역, 예를 들어 서울시 행정동 사업체/종사자 자료와 자치구 총량을 사용해 합계 정합성과 외삽 안정성을 검증한다.

읍면동 결과는 `official estimate`가 아니라 `proxy allocation estimate`로 표시해야 한다.

### 현재 구현

`scripts/collect_emd_economic_census.py`로 KOSIS 경제총조사 2015년 `DT_1KI1511_10`을 산업별로 나누어 수집했다. 전체 요청은 40,000셀 제한에 걸리므로, `A~S` 산업대분류와 `사업체수·종사자수·매출액` 항목을 개별 요청으로 가져온다.

`scripts/allocate_emd_gva.py`는 수집한 읍면동 프록시를 사용해 `sigungu_quarterly_gva_estimates.csv`의 시군구×산업×분기 GVA를 읍면동으로 배분한다.

프록시 우선순위는 다음과 같다.

1. 매출액
2. 종사자수
3. 사업체수

산업 매핑은 경제총조사 산업대분류를 RECI 산업 코드에 맞춘다. 예를 들어 `M`과 `N`은 `MN0`, `E/R/S`는 `ERS`로 묶는다.

산출 결과:

| 파일 | 설명 |
|---|---|
| `emd_economic_census_2015.csv` | 2015년 읍면동×산업대분류 프록시 |
| `emd_quarterly_gva_estimates.csv` | 읍면동×산업×분기 GVA 프록시 추정값 |
| `emd_annual_gva_estimates.csv` | 읍면동×산업×연간 GVA 프록시 추정값 |
| `emd_constraint_diagnostics.csv` | 읍면동 합계가 시군구 부모 총량과 맞는지 검증 |
| `emd_allocation_skipped.csv` | 행정구역 매칭 또는 프록시 부재로 제외된 행 |

이번 실행에서는 `emd_quarterly_gva_estimates.csv` 683,140행, `emd_annual_gva_estimates.csv` 148,322행이 생성되었다. 부모 시군구 총량과 읍면동 배분 합계의 최대 제약 오차는 약 `0.000000004` 백만원으로, 합계 정합성은 충족된다.

다만 2015년 경제총조사 프록시를 이후 모든 분기에 고정 가중치로 사용하므로, 읍면동 내 산업구조 변화는 반영하지 못한다. 서울처럼 더 최신 행정동 사업체 자료가 있는 지역은 후속 단계에서 최신 프록시로 가중치를 갱신해야 한다.

## 대시보드 반영

대시보드에는 `시군구 세부산업` 지역 수준과 읍면동 추정값 표시를 추가했다.

- 연도: 세부산업 연간 추정값과 제조업조사 부가가치 프록시 actual을 비교한다.
- 분기: 세부산업 분기 추정값을 표시한다. 직접 actual은 없으므로 예측값만 표시한다.
- 산업군 필터: KSIC 중분류·소분류·세분류 코드가 선택 가능하다.
- 읍면동: 2015 경제총조사 프록시로 배분한 분기/연간 추정값을 표시한다.
