# 중분류·소분류 Proxy 검증

## 목적

시군구 중분류·소분류·세분류에는 official GVA actual이 없다. 따라서 정확도 검증은 두 층으로 나눈다.

1. 상위 시군구 부모 산업 총량과 세부산업 합계가 일치하는지 확인한다.
2. 제조업은 사후 공개되는 같은 연도 value-added proxy share와 예측 시점에 사용한 lagged proxy share를 비교한다.

## 제조업 Proxy Share Backtest

예측 시점에는 target year의 광업제조업조사 value-added를 사용할 수 없다. 따라서 기존 배분은 공표시점 기준으로 사용 가능한 최신 proxy를 쓴다. 검증에서는 나중에 공개된 target year value-added share를 평가용으로만 사용한다.

```text
predicted_share = estimated_detail_gva / sum(estimated_detail_gva within sigungu × level)
actual_proxy_share = same_year_value_added / sum(same_year_value_added within sigungu × level)
```

## 산출물

| 파일 | 설명 |
| --- | --- |
| `detail_manufacturing_proxy_share_backtest.csv` | 제조업 상세산업 predicted share와 사후 actual proxy share 비교 |
| `detail_manufacturing_proxy_share_by_level.csv` | 중·소·세분류별 share error 요약 |
| `detail_manufacturing_proxy_share_by_year.csv` | 연도별 share error 요약 |
| `detail_parent_constraint_summary.csv` | 제조업·서비스 상세산업 부모 총량 정합성 요약 |

## 해석

이 검증은 official GVA actual 비교가 아니다. 다만 세부산업 배분비율이 나중에 관측되는 산업구조 proxy와 얼마나 가까운지를 보여주므로, 중분류·소분류 추정값의 상대적 신뢰도를 평가하는 보조 지표로 쓸 수 있다.

## 1차 결과

제조업 proxy share 비교는 `9,457`건 생성되었다. 평균 절대 share error는 다음과 같다.

| 세부수준 | 비교 건수 | 평균 절대 share error |
| --- | ---: | ---: |
| 중분류 | 7,234 | 0.0274 |
| 소분류 | 2,223 | 0.0057 |

연도별 평균 절대 share error는 2022년 `0.0245`, 2023년 `0.0227`, 2024년 `0.0197`이다. 부모 총량 정합성은 제조업·서비스업의 중분류·소분류·세분류 모두 통과했다.

다만 중분류 error가 소분류보다 크게 보이는 것은 중분류 수가 적어 한 업종의 비중 변화가 share error에 크게 반영되기 때문이다. 이 값은 공식 GVA 오차가 아니라 산업구조 proxy와의 거리로 해석해야 한다.
