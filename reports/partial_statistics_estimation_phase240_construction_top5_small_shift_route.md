# Phase240 건설업 top5 city-type small-shift route 감사

생성시각: 2026-07-29T10:54:10+09:00

## 결론

- BuildingHUB 단일 보정 실패 이후, 기존 share를 거의 유지하는 small-shift route를 검증했다.
- 후보는 과거연도에서 모든 prior year를 개선하고, alpha≤0.10·cap≤0.05이며, 조정 방향이 불일치하지 않을 때만 활성화했다.
- 전체 및 시군구별 guardrail 판정은 **실패**다.
- 따라서 운영 판정은 **fallback 유지**다.

## 1. 정책 비교

| 정책 | 셀 | 실제합_억원 | 절대오차_억원 | WAPE_% | 10%초과 | 20%초과 | 최대APE_% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 15 | 326,240.260 | 105,042.198 | 32.198 | 12 | 10 | 148.630 |
| small_shift | 15 | 326,240.260 | 104,723.916 | 32.100 | 12 | 10 | 148.630 |

## 2. 시군구별 guardrail

| 시도 | 시군구 | 기준WAPE_% | smallWAPE_% | 기준최대APE_% | small최대APE_% | 통과 |
| --- | --- | --- | --- | --- | --- | --- |
| 경기도 | 평택시 | 16.666 | 16.522 | 24.643 | 24.266 | 1 |
| 서울특별시 | 강남구 | 55.117 | 55.199 | 148.630 | 148.630 | 0 |
| 서울특별시 | 강서구 | 46.681 | 46.438 | 77.723 | 76.835 | 1 |
| 서울특별시 | 영등포구 | 73.787 | 73.639 | 120.673 | 119.569 | 1 |
| 전라남도 | 여수시 | 24.636 | 24.636 | 33.087 | 33.087 | 1 |

## 3. 선택 후보

| 시도 | 시군구 | 연도 | 선택후보 | 블록 | alpha | cap | 조정배율 | 이유 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 경기도 | 평택시 | 2,021 | baseline | fallback | 0.000 | 0.000 | 1.000 | warmup_baseline |
| 경기도 | 평택시 | 2,022 | permit_전체_area_alpha0.10_cap0.05 | permit_flash | 0.100 | 0.050 | 1.005 | small_shift_prior_direction_pass |
| 경기도 | 평택시 | 2,023 | baseline | fallback | 0.000 | 0.000 | 1.000 | fallback_no_small_shift_candidate |
| 서울특별시 | 강남구 | 2,021 | baseline | fallback | 0.000 | 0.000 | 1.000 | warmup_baseline |
| 서울특별시 | 강남구 | 2,022 | baseline | fallback | 0.000 | 0.000 | 1.000 | fallback_no_small_shift_candidate |
| 서울특별시 | 강남구 | 2,023 | permit_전체_count_alpha0.10_cap0.05 | permit_flash | 0.100 | 0.050 | 0.995 | small_shift_prior_direction_pass |
| 서울특별시 | 강서구 | 2,021 | baseline | fallback | 0.000 | 0.000 | 1.000 | warmup_baseline |
| 서울특별시 | 강서구 | 2,022 | baseline | fallback | 0.000 | 0.000 | 1.000 | fallback_no_small_shift_candidate |
| 서울특별시 | 강서구 | 2,023 | start_전체_area_alpha0.10_cap0.05 | start_flash | 0.100 | 0.050 | 0.995 | small_shift_prior_direction_pass |
| 서울특별시 | 영등포구 | 2,021 | baseline | fallback | 0.000 | 0.000 | 1.000 | warmup_baseline |
| 서울특별시 | 영등포구 | 2,022 | approval_전체_count_alpha0.10_cap0.05 | completion_refinement | 0.100 | 0.050 | 0.995 | small_shift_prior_direction_pass |
| 서울특별시 | 영등포구 | 2,023 | permit_주거_area_alpha0.10_cap0.05 | housing_building | 0.100 | 0.050 | 0.995 | small_shift_prior_direction_pass |
| 전라남도 | 여수시 | 2,021 | baseline | fallback | 0.000 | 0.000 | 1.000 | warmup_baseline |
| 전라남도 | 여수시 | 2,022 | baseline | fallback | 0.000 | 0.000 | 1.000 | fallback_no_small_shift_candidate |
| 전라남도 | 여수시 | 2,023 | baseline | fallback | 0.000 | 0.000 | 1.000 | fallback_no_small_shift_candidate |

## 4. 블록별 요약

| 블록 | 이유 | 셀 | 활성셀 |
| --- | --- | --- | --- |
| completion_refinement | small_shift_prior_direction_pass | 1 | 1 |
| fallback | fallback_no_small_shift_candidate | 5 | 0 |
| fallback | warmup_baseline | 5 | 0 |
| housing_building | small_shift_prior_direction_pass | 1 | 1 |
| permit_flash | small_shift_prior_direction_pass | 2 | 2 |
| start_flash | small_shift_prior_direction_pass | 1 | 1 |

## 5. 판정

- 이 실험은 추가 API 없이 가능한 가장 보수적인 BuildingHUB small-shift 검증이다.
- 여기서도 WAPE 10%에 접근하지 못하거나 guardrail을 통과하지 못하면, BuildingHUB만으로 건설업 병목을 해결하기 어렵다는 근거가 강화된다.
- 다음 성능개선은 정비사업·공공/SOC·민간공사 전량자료를 별도 블록으로 수집한 뒤 같은 guardrail을 적용해야 한다.
- PPS는 기존 local cache가 2021 일부월·2023 일부기간으로 불완전해, rolling route 선택에는 아직 쓰지 않는다.

## 산출 파일

- `data/processed/phase240_construction_top5_small_shift_route/phase240_small_shift_policy_summary.csv`
- `data/processed/phase240_construction_top5_small_shift_route/phase240_small_shift_city_guardrail.csv`
- `data/processed/phase240_construction_top5_small_shift_route/phase240_small_shift_choices.csv`
- `data/processed/phase240_construction_top5_small_shift_route/phase240_small_shift_policy_detail.csv`
