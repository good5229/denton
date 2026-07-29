# Active goal WAPE frontier audit

## 결론

- 목표를 전국 합산 하나로 보면 너무 느슨하므로, `업종×운영시점`, `광역시도×업종`, `시군구×업종` 세 층으로 분리한다.
- 업종×운영시점 총괄은 `운수 및 창고업` 1개 route로 Q1 최대 WAPE 10.525% → 9.581%가 되어 10% 이하에 들어온다.
- 광역시도×업종 셀은 운수 route가 가장 안전하고, 건설업은 Phase235 기준 Q1/Q2 시간경로에 한해 제한 채택 후보로 둔다. 건설·숙박·제조 일괄 route는 악화 사례가 있어 자동채택하지 않는다.
- 시군구×업종 연간은 최선 scenario에서도 업종 최대 WAPE 19.432%로, 건설업 1개가 잔류한다.
- 따라서 현재 goal frontier는 `운수 및 창고업 채택 + 광역시도 건설업 Q1/Q2 시간경로 제한 채택 후보 + 시군구 건설업 staged data collection`이다.
- 건설업 41/42 중분류 분할은 고양·포항 local proof에서 건축활동 gate 적용 시 WAPE 68.779% → 3.424%로 내려갔다. 다만 표본이 2개 도시뿐이라 전국 시군구×건설업 route 채택이 아니라 `건설업 특화모형 후보 1순위`로 둔다.
- 서울 강남구·종로구 BuildingHUB 샘플 holdout에서는 건축활동 단일지표가 현행 추정비중보다 크게 악화됐다. 따라서 건설업 공간배분은 `건축활동 단일 route`가 아니라 `기존 share fallback + 민간건축 + 정비사업 + 공공·토목`의 제한적 혼합 route로 재설계한다.
- BuildingHUB 제한혼합도 pooled WAPE 일부 개선은 있었지만 모든 연도 guardrail 통과 후보가 0개였으므로 미채택한다. 다음 건설업 실험 우선순위는 PPS/공공·토목 블록이다.
- PPS 공공공사 신호도 서울 강남·종로 pair에서는 현행보다 악화되어 단독/제한혼합 route를 미채택한다. PPS는 전국 공통 건설업 route가 아니라 공공·토목형 지역 전용 보조 feature로만 유지한다.

## 1. 업종×운영시점 총괄 frontier

| 시나리오 | 분기수 | 운영시점 | 업종최대 WAPE_% | 10%초과 업종수 |
| --- | --- | --- | ---: | ---: |
| prior_year_anchor_all | 1 | 1분기+1개월 | 8.750 | 0 |
| minimal_activity_hybrid | 1 | 1분기+1개월 | 9.581 | 0 |
| prior_year_anchor_all | 2 | 1~2분기+1개월 | 5.768 | 0 |
| minimal_activity_hybrid | 2 | 1~2분기+1개월 | 8.165 | 0 |
| prior_year_anchor_all | 3 | 1~3분기+1개월 | 5.559 | 0 |
| minimal_activity_hybrid | 3 | 1~3분기+1개월 | 8.069 | 0 |
| prior_year_anchor_all | 4 | 공표 후 정밀화 | 5.476 | 0 |
| minimal_activity_hybrid | 4 | 공표 후 정밀화 | 7.983 | 0 |


해석: `prior_year_anchor_all`은 전업종 직전연도 anchor를 쓰는 정밀화 참고 기준이다. 목표인 “최대한 적은 산업군” 기준의 운영 후보는 `minimal_activity_hybrid`, 즉 운수 및 창고업 1개 route다.

## 2. 광역시도×업종 셀 frontier

| 시나리오 | 분기수 | route 업종수 | route 업종 | 10%초과 셀 | 전체 WAPE_% |
| --- | --- | ---: | ---: | ---: | ---: |
| transport_info_only | 1 | 2 | 운수 및 창고업, 정보통신업 | 17 | 3.139 |
| transport_only | 1 | 1 | 운수 및 창고업 | 18 | 3.093 |
| baseline | 1 | 0 | none | 20 | 3.106 |
| top4_sido_q1 | 1 | 4 | 건설업, 숙박 및 음식점업, 운수 및 창고업, 정보통신업 | 26 | 3.219 |
| transport_info_only | 2 | 2 | 운수 및 창고업, 정보통신업 | 8 | 2.542 |
| transport_only | 2 | 1 | 운수 및 창고업 | 9 | 2.514 |
| baseline | 2 | 0 | none | 12 | 2.536 |
| top4_sido_q1 | 2 | 4 | 건설업, 숙박 및 음식점업, 운수 및 창고업, 정보통신업 | 15 | 2.621 |
| transport_info_only | 3 | 2 | 운수 및 창고업, 정보통신업 | 7 | 2.315 |
| transport_only | 3 | 1 | 운수 및 창고업 | 8 | 2.296 |
| baseline | 3 | 0 | none | 12 | 2.332 |
| top4_sido_q1 | 3 | 4 | 건설업, 숙박 및 음식점업, 운수 및 창고업, 정보통신업 | 13 | 2.395 |
| transport_only | 4 | 1 | 운수 및 창고업 | 7 | 2.148 |
| transport_info_only | 4 | 2 | 운수 및 창고업, 정보통신업 | 7 | 2.149 |
| baseline | 4 | 0 | none | 11 | 2.195 |
| top4_sido_q1 | 4 | 4 | 건설업, 숙박 및 음식점업, 운수 및 창고업, 정보통신업 | 14 | 2.213 |


## 3. 시군구×업종 연간 scenario frontier

| 시나리오 | 업종최대 WAPE_% | 10%초과 업종수 | 셀 10%초과 | 셀 20%초과 |
| --- | ---: | ---: | ---: | ---: |
| parent_control_all_activities | 19.432 | 1 | 1,982 | 851 |
| parent_control_construction_transport | 19.432 | 1 | 2,106 | 878 |
| parent_control_top3 | 19.432 | 1 | 2,087 | 881 |
| parent_control_transport_only | 20.675 | 1 | 2,110 | 879 |
| strict_baseline | 20.675 | 2 | 2,107 | 882 |


## 4. 시군구 잔류 업종

| 업종 | 최선 시나리오 | WAPE_% | 10%초과 셀 | 20%초과 셀 |
| ---: | --- | ---: | ---: | ---: |
| 건설업 | parent_control_all_activities | 19.432 | 361 | 224 |
| 운수 및 창고업 | parent_control_all_activities | 8.124 | 235 | 88 |
| 정보통신업 | parent_control_all_activities | 7.980 | 241 | 137 |
| 사업서비스업 | parent_control_all_activities | 6.641 | 219 | 100 |
| 금융 및 보험업 | parent_control_all_activities | 6.361 | 162 | 69 |
| 문화 및 기타서비스업 | parent_control_all_activities | 5.998 | 135 | 38 |
| 광업, 제조업 | parent_control_all_activities | 5.032 | 162 | 44 |
| 숙박 및 음식점업 | parent_control_all_activities | 4.637 | 101 | 29 |
| 도매 및 소매업 | parent_control_all_activities | 4.099 | 94 | 32 |
| 교육 서비스업 | parent_control_all_activities | 3.824 | 81 | 25 |
| 부동산업 | parent_control_all_activities | 3.802 | 95 | 36 |
| 보건 및 사회복지업 | parent_control_all_activities | 2.717 | 67 | 20 |


## 5. 현재 채택 가능한 광역시도 시간경로 policy

| 업종 | 분기수 | 적용범위 | 기준 WAPE_% | 선택 WAPE_% | 변화 pp | 기준10%셀 | 선택10%셀 | 판정 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 건설업 | 1 | 광역시도×건설업 시간경로 | 9.987 | 8.843 | -1.144 | 20 | 16 | Phase235 Q1 제한 채택 후보 |
| 건설업 | 2 | 광역시도×건설업 시간경로 | 9.670 | 8.889 | -0.781 | 22 | 19 | Phase235 Q2 제한 채택 후보 |
| 건설업 | 3 | 광역시도×건설업 시간경로 | 9.635 | 9.635 | 0.000 | 21 | 21 | 연도별 guardrail 실패 가능성으로 baseline 유지 |
| 건설업 | 4 | 광역시도×건설업 시간경로 | 9.577 | 9.577 | 0.000 | 24 | 24 | 연도별 guardrail 실패 가능성으로 baseline 유지 |
| 운수 및 창고업 | 1 | 광역시도×업종 운영시점 | 10.629 | 9.463 | -1.166 | 32 | 27 | rolling mixture 채택 |
| 운수 및 창고업 | 2 | 광역시도×업종 운영시점 | 9.022 | 6.792 | -2.229 | 21 | 13 | rolling mixture 채택 |
| 운수 및 창고업 | 3 | 광역시도×업종 운영시점 | 8.924 | 6.552 | -2.372 | 23 | 15 | rolling mixture 채택 |
| 운수 및 창고업 | 4 | 광역시도×업종 운영시점 | 8.846 | 5.935 | -2.911 | 22 | 12 | rolling mixture 채택 |

주의:

- 건설업 Q1/Q2 route는 `BOK식 건축12·토목24분기 분산 + rolling 지역 gate`이고, 광역시도×건설업 시간경로에만 적용한다.
- 건설업 Q1/Q2는 평가기간 pooled WAPE가 10% 이하이나 2025년 일부 단년 WAPE가 10%를 소폭 초과하므로 “전 연도 10% 이하 달성”으로 표현하지 않는다.
- 건설업 Q3/Q4는 pooled 개선 후보가 있어도 연도별 guardrail 실패 가능성이 있어 운영 기본안에서는 baseline을 유지한다.
- 이 섹션은 시군구 공간배분 성능이 아니다.


## 6. 건설업 staged collection 부담

| 범위 | 시군구 개 | 법정동 요청 개 | 누적오차기여_% |
| --- | ---: | ---: | ---: |
| 건설업 오차기여 50% | 28 | 1,924 | 49.978 |
| 건설업 오차기여 70% | 52 | 3,882 | 69.443 |


## 7. 건설업 41/42 local proof

`reports/partial_statistics_estimation_phase227_construction_building_activity_gate.md`에서 고양·포항 건설업 내부 중분류 분할을 점검했다. 선택식은 중분류 actual을 직접 입력하지 않고, 건축허가 event의 산업·창고 면적비중·평균면적·중앙면적 등 활동특성만 사용했다.

| 시나리오 | 실제합_억원 | 오차합_억원 | WAPE_% | 도시최대 WAPE_% | 10%초과 도시 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 현행 소분류 합산 기준 | 35,220.820 | 24,224.569 | 68.779 | 73.451 | 2 |
| 건축활동 gate 선택 | 35,220.820 | 1,205.870 | 3.424 | 5.224 | 0 |

해석:

- 고양시는 소형 도시건축 중심 특성으로 41/42 균등분할이 안정적이었다.
- 포항시는 산업·창고 대형 프로젝트 비중이 높아 허가 산업대형 완화 비중이 맞았다.
- 이 결과는 건축활동 자료가 건설업 내부 분할을 설명한다는 강한 단서다.
- 단, gate threshold가 local proof 이후 설계됐을 가능성이 있으므로 전국 채택 전 train/holdout 또는 rolling out-of-year 검증이 필요하다.

## 8. BuildingHUB 샘플 공간배분 holdout

`reports/partial_statistics_estimation_phase228_construction_buildinghub_sample_spatial_holdout.md`에서 로컬 BuildingHUB vintage 샘플 중 같은 시도 내 비교가 가능한 서울 강남구·종로구 pair를 사용해 건설업 대분류 공간배분을 점검했다.

| 후보 | 실제합_억원 | 오차합_억원 | pooled WAPE_% | 평균 WAPE_% | 최대 WAPE_% |
| --- | ---: | ---: | ---: | ---: | ---: |
| 현행 추정비중 | 53,254.980 | 5,517.676 | 10.361 | 9.835 | 12.377 |
| 허가 건수 | 53,254.980 | 58,041.245 | 108.987 | 112.939 | 128.594 |
| 사용승인 연면적 | 53,254.980 | 60,792.801 | 114.154 | 122.230 | 156.242 |
| 건축허가 연면적 | 53,254.980 | 66,779.782 | 125.396 | 136.015 | 171.605 |
| 착공 연면적 | 53,254.980 | 79,823.114 | 149.889 | 155.181 | 177.253 |

해석:

- Phase227은 건설업 `내부 41/42 분할`에 대한 local proof다.
- Phase228은 건설업 `시군구 전체 공간배분`에 대해 건축활동 단일지표가 위험하다는 반증이다.
- 따라서 건설업 route는 건축HUB 단독 대체가 아니라 기존 share를 중심에 둔 제한적 혼합이어야 한다.
- 다음 실험은 민간건축, 정비사업, 공공·토목, 잔차 fallback을 분리하고 각 블록의 혼합상한을 rolling 검증으로 고정한다.

## 9. BuildingHUB 제한혼합 guardrail

`reports/partial_statistics_estimation_phase229_construction_limited_building_mix.md`에서 기존 share를 유지하면서 BuildingHUB 활동 share를 alpha 1~15%, 이동상한 ±1~10%p로 제한혼합했다.

| 후보 | alpha | 상한_pp | pooled WAPE_% | 기준 pooled WAPE_% | 변화_pp | 통과연도 | 검증연도 | 전체통과 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 사용승인 연면적 | 0.05 | 5.0 | 9.535 | 10.361 | -0.825 | 1 | 3 | False |
| 사용승인 연면적 | 0.02 | 2.0 | 10.031 | 10.361 | -0.330 | 1 | 3 | False |
| 사용승인 연면적 | 0.01 | 1.0 | 10.196 | 10.361 | -0.165 | 1 | 3 | False |

판정:

- pooled WAPE만 보면 일부 후보가 좋아진다.
- 그러나 모든 연도에서 WAPE와 최대 APE가 현행보다 악화되지 않는 후보는 0개다.
- 평균 WAPE 개선을 건설업 성능개선으로 주장하지 않는다.
- BuildingHUB 제한혼합은 미채택하고, 다음 실험은 PPS/공공·토목 블록을 우선한다.

## 10. PPS 공공공사 블록 서울 pair 실험

`reports/partial_statistics_estimation_phase230_construction_pps_pair_mix.md`에서 서울 강남구·종로구 2021 pair를 대상으로 PPS 공공공사 금액·공고건수 신호를 점검했다.

| 기간 | 신호 | 방식 | alpha | WAPE_% | 기준 WAPE_% | 변화_pp | 최대 APE_% | 기준 최대 APE_% | 통과 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | 현행 추정비중 | baseline | 0.00 | 9.141 | 9.141 | 0.000 | 32.266 | 32.266 | True |
| 2021M05 | PPS 금액 | limited_mix | 0.01 | 9.637 | 9.141 | 0.496 | 34.017 | 32.266 | False |
| 2021M04 | PPS 공고건수 | limited_mix | 0.01 | 9.716 | 9.141 | 0.575 | 34.295 | 32.266 | False |
| 2021M01_M05 | PPS 금액 | limited_mix | 0.01 | 9.772 | 9.141 | 0.631 | 34.494 | 32.266 | False |

판정:

- PPS는 서울 강남·종로 pair에서 강남 share를 낮추는 방향으로 작동해 현행보다 악화됐다.
- PPS 단독 route와 PPS 제한혼합 route는 미채택한다.
- PPS는 공공공사·토목형 지역 전용 보조 feature로만 유지한다.
- 건설업 route는 지역유형 gate가 필요하다.

## 평가관/과학자 반영

- 과학자: 전량 수집 전 오차 집중 시군구와 건축활동 방향성을 먼저 보라는 제안을 반영했다.
- 평가관: 2023 상위오차 표본은 탐색 표본이며, 채택 평가는 rolling out-of-year로 해야 한다는 조건을 반영했다.
- Phase227 local proof는 고양·포항 한정 건설업 후보의 설명력 근거로 반영하되, 전국 route 채택으로 과대해석하지 않는다.
- actual 직접 입력은 없지만 threshold 사후선택 가능성이 있으므로, 다음 단계에서는 threshold 사전고정·holdout 검증을 적용한다.
- Phase228 holdout을 반영해 `건축활동 단일 공간배분 route`는 미채택한다. 건축활동 feature는 민간건축 블록의 제한적 보조지표로만 유지한다.
- Phase229 제한혼합은 pooled WAPE 개선 신호만 있고 전연도 guardrail 통과가 없어 미채택한다. 평가관 권고에 따라 평균 WAPE만으로 성능개선 주장을 하지 않는다.
- Phase230 PPS 실험은 서울 pair에서 guardrail을 통과하지 못했으므로 PPS 단독/제한혼합 route도 미채택한다. PPS는 공공·토목형 지역 gate 안에서만 재검증한다.
- Phase231 route decision registry를 추가해 건설업 관련 route의 채택/후보/미채택 판정을 한 곳에 고정했다. 현재 건설업 대분류 시군구 공간배분에서 운영 채택 가능한 신규 route는 없고, 건축HUB·PPS·정비사업 자료는 지역유형 gate를 둔 다음 실험 후보로만 유지한다.
- Phase234에서 BOK reference식 건축12·토목24분기 분산을 재감사했다. 건설수주 원자료보다는 훨씬 안정적이지만, 전체 광역시도 상세 guardrail에서는 기준보다 악화되는 셀이 있어 전국 공통 시간route로 즉시 채택하지 않는다. 취약 광역시도·특정 운영기준의 후보로 유지하고, rolling 지역 gate 통과 시에만 적용한다.
- Phase235에서 BOK식 건설수주 시간분산을 rolling 지역 gate로 제한 적용했다. 엄격 운영정책은 Q1 `prior2_sum_improves`, Q2 `expanding_guardrail`, Q3/Q4 baseline 유지다. 2023~2025 평가기간 평균 WAPE는 Q1 9.987→8.843, Q2 9.670→8.889로 개선되고 pooled 10% 이하이나, 2025년 단년 WAPE는 10%를 소폭 초과하므로 “전 연도 10% 이하 달성”으로 표현하지 않는다. 이 route는 광역시도×건설업 시간경로 한정이며 시군구 공간배분 개선이 아니다.
- Phase236에서 goal frontier를 재합성했다. 현재 방식은 총량·광역시도 업종 모니터링에는 실용성이 있으나, 시군구×건설업처럼 위치성이 강한 업종은 추가 event 자료 기반 공간배분이 필요하다는 판정으로 고정한다.
- Phase237에서 건설업 특화 route 하네스를 추가했다. 현재 최선 시군구×건설업 WAPE 19.432%를 기준으로 보면 10% 도달에는 절대오차 281,557.4억원, 현재 오차의 48.5% 감축이 필요하다. top28은 현재 최선 기준 오차의 53.2%, top52는 73.9%를 포착하므로, 실제 건축HUB·정비사업·PPS·SOC 자료를 top1→top5→top28→top52 순서로 붙여 rolling 검증해야 한다.
- Phase238에서 top1 평택시 BuildingHUB event를 실제 수집했다. 200개 법정동, 236 API page, 16,655행을 확보했다. 허가 총연면적은 2022년 급등·2023년 하락으로 평택시 건설업 오차 방향을 설명하지만, prior-selected 후보는 WAPE 16.666%→14.456% 개선에도 최대 APE 24.643%→30.671% 악화로 전체 guardrail을 통과하지 못했다. 따라서 운영 route는 guarded fallback 유지이고, 다음은 top5 유형검증이다.
- Phase239에서 top5 시군구 BuildingHUB event를 수집하고 보수 grid를 적용했다. 519개 법정동, 649 API page, 41,286행을 확보했다. pooled WAPE는 32.198%→32.115%로 소폭 개선되지만, 평택·강서·여수의 시군구별 WAPE 또는 최대 APE가 악화되어 top5 guardrail은 실패했다. BuildingHUB 단일 보정은 미채택이고, 정비사업·공공/SOC·기존 share 이동상한 결합 route가 필요하다.
- Phase240에서 추가 API 없이 가능한 가장 보수적인 `city-type small-shift`를 검증했다. alpha≤0.10, cap≤0.05, prior-year 방향성 일치 조건을 적용해도 top5 WAPE는 32.198%→32.100%에 그치고, 강남구 WAPE가 55.117%→55.199%로 악화되어 guardrail을 통과하지 못했다. 따라서 BuildingHUB만으로는 건설업 시군구 병목을 해결하기 어렵다는 결론이 강화됐다.
- 외부 API 수집은 top5까지 진행됐고, top28/top52 확장과 정비사업·공공/SOC 블록 수집은 아직 남아 있다. 건설업 route 채택은 여전히 보류다.

## 다음 실행 명령

```bash
.venv/bin/python nationwide/collect_buildinghub_priority_events.py \
  --limit-cities 1 --priority-stage 1차 \
  --output-tag construction_priority_top1_pyeongtaek
```

그 다음 top1 event를 이용해 `기존 share + 착공/사용승인 면적 share + PPS 금액 share` 후보를 rolling 검증한다.
