# Phase239 건설업 BuildingHUB top5 보수 grid 검증

생성시각: 2026-07-29T10:49:06+09:00

## 결론

- top5 오차기여 시군구에 대해 BuildingHUB event를 수집하고 보수 alpha/cap grid를 적용했다.
- 과학자 검토를 반영해 alpha는 0.02~0.15, cap은 0.02~0.10으로 낮췄다.
- prior-selected 후보가 전체 및 시군구별 guardrail을 통과하지 못하면 운영 route는 fallback이다.
- 이번 top5 guarded 판정은 **fallback 유지**다.

## 1. 수집 품질

| 순위 | 시도 | 시군구 | 법정동 | API page | event 행 | 에러 법정동 | 행 보유 법정동 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 경기도 | 평택시 | 200 | 236 | 16,559 | 7 | 159 |
| 2 | 서울특별시 | 강남구 | 68 | 99 | 4,582 | 1 | 15 |
| 3 | 서울특별시 | 영등포구 | 102 | 113 | 4,335 | 4 | 34 |
| 4 | 서울특별시 | 강서구 | 27 | 35 | 1,955 | 3 | 12 |
| 5 | 전라남도 | 여수시 | 122 | 166 | 13,855 | 10 | 109 |

## 2. top5 전체 정책 비교

| 정책 | 셀 | 실제합_억원 | 절대오차_억원 | WAPE_% | 10%초과 | 20%초과 | 최대APE_% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 15 | 326,240.260 | 105,042.198 | 32.198 | 12 | 10 | 148.630 |
| prior_selected_diagnostic | 15 | 326,240.260 | 104,771.390 | 32.115 | 12 | 10 | 144.901 |
| guarded_operational_fallback | 15 | 326,240.260 | 105,042.198 | 32.198 | 12 | 10 | 148.630 |

## 3. 시군구별 비교

| 정책 | 시도 | 시군구 | 실제합_억원 | 절대오차_억원 | WAPE_% | 10%초과 | 최대APE_% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 서울특별시 | 강남구 | 45,541.730 | 25,101.108 | 55.117 | 3 | 148.630 |
| prior_selected_diagnostic | 서울특별시 | 강남구 | 45,541.730 | 24,705.457 | 54.248 | 3 | 144.901 |
| baseline | 서울특별시 | 강서구 | 33,915.130 | 15,831.786 | 46.681 | 2 | 77.723 |
| prior_selected_diagnostic | 서울특별시 | 강서구 | 33,915.130 | 15,956.582 | 47.049 | 2 | 80.389 |
| baseline | 전라남도 | 여수시 | 58,259.970 | 14,353.087 | 24.636 | 2 | 33.087 |
| prior_selected_diagnostic | 전라남도 | 여수시 | 58,259.970 | 14,712.216 | 25.253 | 2 | 35.084 |
| baseline | 서울특별시 | 영등포구 | 32,101.590 | 23,686.871 | 73.787 | 3 | 120.673 |
| prior_selected_diagnostic | 서울특별시 | 영등포구 | 32,101.590 | 23,544.380 | 73.343 | 3 | 117.363 |
| baseline | 경기도 | 평택시 | 156,421.840 | 26,069.346 | 16.666 | 2 | 24.643 |
| prior_selected_diagnostic | 경기도 | 평택시 | 156,421.840 | 25,852.755 | 16.528 | 2 | 25.773 |

## 4. prior-selected 후보

| 시도 | 시군구 | 연도 | 선택후보 | 이유 |
| --- | --- | --- | --- | --- |
| 경기도 | 평택시 | 2,021 | baseline | first_year_fallback |
| 경기도 | 평택시 | 2,022 | approval_전체_area_alpha0.15_cap0.10 | prior_no_worse_lower_error |
| 경기도 | 평택시 | 2,023 | permit_전체_area_alpha0.15_cap0.10 | prior_no_worse_lower_error |
| 서울특별시 | 강남구 | 2,021 | baseline | first_year_fallback |
| 서울특별시 | 강남구 | 2,022 | approval_전체_area_alpha0.15_cap0.10 | prior_no_worse_lower_error |
| 서울특별시 | 강남구 | 2,023 | approval_전체_area_alpha0.15_cap0.10 | prior_no_worse_lower_error |
| 서울특별시 | 강서구 | 2,021 | baseline | first_year_fallback |
| 서울특별시 | 강서구 | 2,022 | permit_산업·창고_area_alpha0.15_cap0.10 | prior_no_worse_lower_error |
| 서울특별시 | 강서구 | 2,023 | permit_산업·창고_area_alpha0.15_cap0.10 | prior_no_worse_lower_error |
| 서울특별시 | 영등포구 | 2,021 | baseline | first_year_fallback |
| 서울특별시 | 영등포구 | 2,022 | approval_전체_count_alpha0.15_cap0.10 | prior_no_worse_lower_error |
| 서울특별시 | 영등포구 | 2,023 | permit_주거_area_alpha0.15_cap0.10 | prior_no_worse_lower_error |
| 전라남도 | 여수시 | 2,021 | baseline | first_year_fallback |
| 전라남도 | 여수시 | 2,022 | approval_전체_area_alpha0.15_cap0.10 | prior_no_worse_lower_error |
| 전라남도 | 여수시 | 2,023 | baseline | no_prior_candidate_passed |

## 5. 시군구별 guardrail

| 시도 | 시군구 | 기준WAPE_% | priorWAPE_% | 기준최대APE_% | prior최대APE_% | 시군구통과 |
| --- | --- | --- | --- | --- | --- | --- |
| 경기도 | 평택시 | 16.666 | 16.528 | 24.643 | 25.773 | 0 |
| 서울특별시 | 강남구 | 55.117 | 54.248 | 148.630 | 144.901 | 1 |
| 서울특별시 | 강서구 | 46.681 | 47.049 | 77.723 | 80.389 | 0 |
| 서울특별시 | 영등포구 | 73.787 | 73.343 | 120.673 | 117.363 | 1 |
| 전라남도 | 여수시 | 24.636 | 25.253 | 33.087 | 35.084 | 0 |

## 6. best-case 후보 참고

아래 표는 actual을 보고 고른 후보라 운영 성능이 아니다. 어떤 feature가 방향성을 갖는지 확인하기 위한 참고표다.

| 시도 | 시군구 | 연도 | best 후보 | 추정_억원 | 실제_억원 | APE_% | feature ratio | 조정배율 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 경기도 | 평택시 | 2,021 | permit_전체_area_alpha0.15_cap0.10 | 42,124.210 | 44,773.240 | 5.917 | 2.965 | 1.015 |
| 경기도 | 평택시 | 2,022 | permit_전체_area_alpha0.15_cap0.10 | 45,895.332 | 60,003.500 | 23.512 | 1.696 | 1.015 |
| 경기도 | 평택시 | 2,023 | permit_전체_area_alpha0.15_cap0.10 | 58,761.619 | 51,645.100 | 13.780 | 0.421 | 0.985 |
| 서울특별시 | 강남구 | 2,021 | permit_전체_count_alpha0.15_cap0.10 | 16,840.302 | 18,657.260 | 9.739 | 1.181 | 1.015 |
| 서울특별시 | 강남구 | 2,022 | permit_전체_count_alpha0.15_cap0.10 | 18,559.576 | 7,578.410 | 144.901 | 0.786 | 0.985 |
| 서울특별시 | 강남구 | 2,023 | permit_상업·업무_area_alpha0.15_cap0.10 | 7,647.598 | 19,306.060 | 60.388 | 1.406 | 1.015 |
| 서울특별시 | 강서구 | 2,021 | permit_산업·창고_area_alpha0.15_cap0.10 | 8,161.974 | 8,074.850 | 1.079 | 0.009 | 0.985 |
| 서울특별시 | 강서구 | 2,022 | permit_전체_area_alpha0.15_cap0.10 | 8,277.219 | 16,570.460 | 50.048 | 1.593 | 1.015 |
| 서울특별시 | 강서구 | 2,023 | permit_전체_area_alpha0.15_cap0.10 | 16,227.504 | 9,269.820 | 75.057 | 0.326 | 0.985 |
| 서울특별시 | 영등포구 | 2,021 | permit_전체_area_alpha0.15_cap0.10 | 12,013.454 | 7,375.230 | 62.889 | 0.382 | 0.985 |
| 서울특별시 | 영등포구 | 2,022 | permit_주거_area_alpha0.15_cap0.10 | 7,560.065 | 17,046.330 | 55.650 | 5.091 | 1.015 |
| 서울특별시 | 영등포구 | 2,023 | permit_전체_count_alpha0.15_cap0.10 | 16,693.525 | 7,680.030 | 117.363 | 0.793 | 0.985 |
| 전라남도 | 여수시 | 2,021 | approval_전체_area_alpha0.15_cap0.10 | 30,323.733 | 23,706.930 | 27.911 | 0.334 | 0.985 |
| 전라남도 | 여수시 | 2,022 | permit_전체_count_alpha0.15_cap0.10 | 23,582.807 | 17,989.650 | 31.091 | 0.889 | 0.985 |
| 전라남도 | 여수시 | 2,023 | permit_전체_area_alpha0.15_cap0.10 | 17,617.322 | 16,563.390 | 6.363 | 0.803 | 0.985 |

## 7. 판정

- top5 결과는 건축HUB 신호가 일부 지역·연도에 존재함을 보여준다.
- pooled WAPE가 소폭 좋아져도 시군구별 WAPE 또는 최대 APE가 악화되면 건설업 운영 route로 채택하지 않는다.
- 서울권 고오차 지역은 허가/착공 총량보다 정비사업·대형 상업건축·본사/수주 소재지 요인이 섞여 있어 별도 블록이 필요하다.
- 다음 개선은 BuildingHUB 단일 보정이 아니라 `정비사업 블록 + 공공/SOC 블록 + 기존 share 이동상한` 결합으로 가야 한다.

## 산출 파일

- `data/processed/phase239_construction_top5_buildinghub_guarded_grid/phase239_top5_policy_summary.csv`
- `data/processed/phase239_construction_top5_buildinghub_guarded_grid/phase239_top5_city_policy_summary.csv`
- `data/processed/phase239_construction_top5_buildinghub_guarded_grid/phase239_top5_city_guardrail.csv`
- `data/processed/phase239_construction_top5_buildinghub_guarded_grid/phase239_top5_candidate_detail.csv`
- `data/processed/phase239_construction_top5_buildinghub_guarded_grid/phase239_top5_collection_quality.csv`
