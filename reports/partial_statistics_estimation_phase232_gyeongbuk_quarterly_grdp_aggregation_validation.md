# Phase232 경북 시군·업종 분기 GRDP 집계검증

생성시각: 2026-07-28T20:53:06+09:00

## 목적

포항시 단독 업종 추정값을 더 고치는 단계는 일단 중단하고, 같은 구조를 경상북도 전체 시군으로 확장했을 때 상위 공식 분기 GRDP와 맞는지 검증했다. 핵심은 `시군·업종 하위 추정 → 경북 상위 actual 집계검증`이다.

## 누수 방지 기준

| 항목 | 사용 여부 |
| --- | --- |
| 목표 분기의 경북 공식 업종값을 배분비로 사용 | 미사용 |
| 전년도 경북 시군·업종 연간 GVA | 사용 |
| 전국 동업종 분기 변화 | 사용 |
| 목표 분기 경북 GRDP actual | 검증에만 사용 |
| 2025년 전년도 경북 상위 공식값 | `prior_year_province_anchor` 트랙에서만 사용 |

## 추정 트랙

| 트랙 | 의미 |
| --- | --- |
| `recursive_no_target_actual` | 2025년에도 2024년 예측 시군·업종값을 이어 쓰는 완전 외삽형 |
| `prior_year_province_anchor` | 2025년 예측 전 이미 알 수 있는 2024년 경북 상위 연간 공식값으로 전년도 기준만 정렬한 정밀형 |

## 검증 감사

| 검사 | 값 | 판정 |
| --- | --- | --- |
| 경북 시군 수(2023) | 23 | 정보 |
| 시군×업종 분기 추정 행 | 11,960 | 정보 |
| 공식 경북 분기 actual 누락 | 0 | 0 |
| 업종 actual 누락 | 0 | 0 |

연간 시군·업종표의 경북 경계는 2023년 KOSIS 원천표 기준 23개 시군이다. 이 표에는 군위군이 포함되어 있으므로, 행정구역 기준연도 변경을 적용하는 별도 실험에서는 경계 재정렬이 필요하다.

## 연도별 경북 GRDP 시장가격 검증

| 트랙 | 연도 | 분기수 | 공식합계_억원 | 예측합계_억원 | 절대오차합_억원 | WAPE_pct | 최대분기오차율_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| recursive_no_target_actual | 2021 | 4 | 1,148,926.540 | 1,175,902.755 | 26,976.215 | 2.348 | 3.776 |
| recursive_no_target_actual | 2022 | 4 | 1,156,124.710 | 1,178,406.749 | 22,282.039 | 1.927 | 3.736 |
| recursive_no_target_actual | 2023 | 4 | 1,183,661.580 | 1,174,027.974 | 12,227.441 | 1.033 | 1.977 |
| recursive_no_target_actual | 2024 | 4 | 1,193,491.920 | 1,212,512.459 | 23,834.035 | 1.997 | 4.348 |
| recursive_no_target_actual | 2025 | 4 | 1,204,120.010 | 1,225,230.524 | 21,110.514 | 1.753 | 3.456 |
| prior_year_province_anchor | 2021 | 4 | 1,148,926.540 | 1,175,902.755 | 26,976.215 | 2.348 | 3.776 |
| prior_year_province_anchor | 2022 | 4 | 1,156,124.710 | 1,178,406.749 | 22,282.039 | 1.927 | 3.736 |
| prior_year_province_anchor | 2023 | 4 | 1,183,661.580 | 1,174,027.974 | 12,227.441 | 1.033 | 1.977 |
| prior_year_province_anchor | 2024 | 4 | 1,193,491.920 | 1,212,512.459 | 23,834.035 | 1.997 | 4.348 |
| prior_year_province_anchor | 2025 | 4 | 1,204,120.010 | 1,205,778.464 | 15,254.282 | 1.267 | 1.792 |

## 2024~2025 분기별 경북 GRDP 시장가격 검증

| 트랙 | 분기 | 예측GRDP_억원 | 공식GRDP_억원 | 오차_억원 | 오차율_pct |
| --- | --- | --- | --- | --- | --- |
| recursive_no_target_actual | 2024Q1 | 290,328.403 | 286,088.800 | 4,239.603 | 1.482 |
| recursive_no_target_actual | 2024Q2 | 304,273.738 | 291,594.820 | 12,678.918 | 4.348 |
| recursive_no_target_actual | 2024Q3 | 304,554.372 | 306,961.120 | -2,406.748 | 0.784 |
| recursive_no_target_actual | 2024Q4 | 313,355.947 | 308,847.180 | 4,508.767 | 1.460 |
| recursive_no_target_actual | 2025Q1 | 290,759.132 | 289,512.370 | 1,246.762 | 0.431 |
| recursive_no_target_actual | 2025Q2 | 306,205.189 | 295,977.000 | 10,228.189 | 3.456 |
| recursive_no_target_actual | 2025Q3 | 311,069.541 | 309,545.560 | 1,523.981 | 0.492 |
| recursive_no_target_actual | 2025Q4 | 317,196.663 | 309,085.080 | 8,111.583 | 2.624 |
| prior_year_province_anchor | 2024Q1 | 290,328.403 | 286,088.800 | 4,239.603 | 1.482 |
| prior_year_province_anchor | 2024Q2 | 304,273.738 | 291,594.820 | 12,678.918 | 4.348 |
| prior_year_province_anchor | 2024Q3 | 304,554.372 | 306,961.120 | -2,406.748 | 0.784 |
| prior_year_province_anchor | 2024Q4 | 313,355.947 | 308,847.180 | 4,508.767 | 1.460 |
| prior_year_province_anchor | 2025Q1 | 286,149.418 | 289,512.370 | -3,362.952 | 1.162 |
| prior_year_province_anchor | 2025Q2 | 301,282.333 | 295,977.000 | 5,305.333 | 1.792 |
| prior_year_province_anchor | 2025Q3 | 306,110.598 | 309,545.560 | -3,434.962 | 1.110 |
| prior_year_province_anchor | 2025Q4 | 312,236.114 | 309,085.080 | 3,151.034 | 1.019 |

## 업종별 집계검증: 오차가 큰 업종

| 트랙 | 업종 | 공식합계_억원 | 예측합계_억원 | 절대오차합_억원 | WAPE_pct | 최대분기오차율_pct |
| --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 사업서비스업 | 236,638.990 | 231,274.890 | 13,397.057 | 5.661 | 13.216 |
| prior_year_province_anchor | 건설업 | 302,513.970 | 296,226.218 | 16,769.025 | 5.543 | 13.543 |
| prior_year_province_anchor | 운수 및 창고업 | 213,078.720 | 215,303.767 | 10,555.607 | 4.954 | 19.600 |
| prior_year_province_anchor | 문화 및 기타서비스업 | 159,275.110 | 164,156.400 | 7,684.587 | 4.825 | 15.605 |
| prior_year_province_anchor | 정보통신업 | 72,904.110 | 73,954.951 | 3,056.614 | 4.193 | 16.207 |
| prior_year_province_anchor | 광업, 제조업 | 2,311,768.190 | 2,371,840.572 | 93,951.336 | 4.064 | 13.488 |
| prior_year_province_anchor | 숙박 및 음식점업 | 111,100.470 | 108,432.070 | 4,195.607 | 3.776 | 10.359 |
| prior_year_province_anchor | 기타산업 및 순생산물세 | 824,796.100 | 821,643.426 | 30,388.740 | 3.684 | 10.037 |
| recursive_no_target_actual | 사업서비스업 | 236,638.990 | 231,583.710 | 13,263.957 | 5.605 | 13.216 |
| recursive_no_target_actual | 운수 및 창고업 | 213,078.720 | 213,512.305 | 11,490.332 | 5.393 | 19.600 |
| recursive_no_target_actual | 건설업 | 302,513.970 | 295,085.871 | 15,628.679 | 5.166 | 13.543 |
| recursive_no_target_actual | 문화 및 기타서비스업 | 159,275.110 | 164,558.832 | 7,896.835 | 4.958 | 15.605 |
| recursive_no_target_actual | 숙박 및 음식점업 | 111,100.470 | 107,570.585 | 4,988.670 | 4.490 | 10.359 |
| recursive_no_target_actual | 광업, 제조업 | 2,311,768.190 | 2,394,163.996 | 97,061.814 | 4.199 | 13.488 |
| recursive_no_target_actual | 정보통신업 | 72,904.110 | 73,943.043 | 3,050.553 | 4.184 | 16.117 |
| recursive_no_target_actual | 기타산업 및 순생산물세 | 824,796.100 | 820,092.176 | 30,383.337 | 3.684 | 10.037 |

## 해석

1. 경북 23개 시군의 업종별 연간 GVA를 모두 분기화해 합산하면, 경북 공식 분기 GRDP와 직접 비교할 수 있다.
2. 이 검증은 포항 한 도시의 숫자만 맞추는 것이 아니라, 같은 추정 방식이 경북 전체 회계경계에서 어느 정도 닫히는지 보는 외부 검증이다.
3. 공식 XLSX의 업종 구분은 제조업 세부 중분류가 아니라 광업·제조업/건설업/서비스업 및 서비스 세부 업종이므로, 제조업 중분류별 공식 분기 대조는 현재 불가능하다.
4. 업종별로는 서비스 세부 업종과 기타산업·순생산물세에서 오차가 커지는지 확인해야 하며, 이 부분이 포항시 잔여 고오차 업종과 연결된다.

## 산출물

- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_sigungu_industry_quarterly_predictions.csv`
- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_quarterly_grdp_validation.csv`
- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_activity_quarterly_validation.csv`
- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_yearly_summary.csv`
- `data/processed/phase232_gyeongbuk_quarterly_grdp_aggregation_validation/phase232_gyeongbuk_activity_summary.csv`
