# Phase129 균형형 정밀 라우팅 실험

## 목적

정밀오차가 산업별로 크게 갈리는 문제를 줄이기 위해, Phase127 후보자료를 더 적극적으로 선택하되 고오차 셀 수 증가와 악화폭을 제한했다. 실제 GVA를 후보값으로 직접 대입하지 않고, 고용·산재 사업장 구조 같은 외부 활동자료 비중으로 만든 후보만 사용했다.

## 기존 대비 성능

| city | phase127 strict error 억원 | phase127 strict wape % | phase127 strict gt10 cells | phase127 risk error 억원 | phase127 risk wape % | phase127 risk gt10 cells | phase129 error 억원 | phase129 wape % | phase129 gt10 cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 5,114.68 | 3.02 | 17 | 4,795.57 | 2.83 | 16 | 4,466.53 | 2.64 | 14 |
| 포항시 | 7,718.22 | 5.00 | 21 | 7,278.52 | 4.71 | 20 | 7,278.52 | 4.71 | 20 |

## Phase114 기준 균형 선택 요약

| city | actual sum 억원 | base error 억원 | base wape % | phase129 balanced error 억원 | phase129 balanced wape % | reduction 억원 | base gt20 cells | phase129 balanced gt20 cells | base gt10 cells | phase129 balanced gt10 cells | worsened cells | worsen sum 억원 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 169,395.14 | 5,202.32 | 3.07 | 4,466.53 | 2.64 | 735.79 | 8 | 7 | 17 | 14 | 8 | 318.75 |
| 포항시 | 154,484.79 | 9,065.93 | 5.87 | 7,278.52 | 4.71 | 1,787.41 | 15 | 14 | 21 | 20 | 1 | 0.48 |

## 채택 라우팅

| city | parent code | block id | middle codes | metric label | alpha | baseline floor | error reduction 억원 | base gt20 cells | candidate gt20 cells | base gt10 cells | candidate gt10 cells | worsened cells | worsen sum 억원 | max worsen pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 포항시 | F00 | F00_all | 41,42 | 고용보험 상시근로자수 | 0.25 | 0.00 | 1,026.87 | 0 | 0 | 0 | 0 | 0 | 0.00 | -4.07 |
| 포항시 | MN0 | facility_support_74_76 | 74,75,76 | 사업장수 | 0.33 | 0.10 | 453.06 | 1 | 0 | 2 | 1 | 1 | 0.48 | 0.08 |
| 포항시 | Q00 | Q00_all | 86,87 | 고용보험 상시근로자수 | 0.05 | 0.20 | 307.48 | 0 | 0 | 0 | 0 | 0 | 0.00 | -1.76 |
| 고양시 | J00 | content_58_60 | 58,59,60 | 고용보험 상시근로자수 | 0.67 | 0.10 | 198.89 | 2 | 1 | 2 | 2 | 1 | 24.11 | 2.53 |
| 고양시 | MN0 | professional_70_73 | 70,71,72,73 | 사업장수 | 0.33 | 0.60 | 188.55 | 0 | 0 | 2 | 0 | 2 | 185.68 | 3.03 |
| 고양시 | G00 | G00_all | 45,46,47 | 고용보험 상시근로자수 | 0.25 | 0.80 | 130.61 | 0 | 0 | 0 | 0 | 1 | 36.82 | 0.23 |
| 고양시 | K00 | K00_all | 64,65,66 | 사업장수 | 0.02 | 0.40 | 86.65 | 0 | 0 | 0 | 0 | 1 | 53.66 | 1.02 |
| 고양시 | MN0 | facility_support_74_76 | 74,75,76 | 고용보험 상시근로자수 | 0.08 | 0.60 | 72.58 | 0 | 0 | 0 | 0 | 0 | 0.00 | -0.11 |
| 고양시 | ERS | environment_36_39 | 36,37,38 | 사업장수 | 0.05 | 0.20 | 29.33 | 1 | 1 | 2 | 1 | 1 | 7.45 | 1.67 |
| 고양시 | C00 | mfg_material_20_25 | 20,21,22,23,24,25 | 사업장수 | 0.08 | 0.60 | 29.17 | 1 | 1 | 2 | 2 | 2 | 11.04 | 1.07 |

## 개선 셀

| city | parent code | middle code | middle label | actual gva 억원 | phase129 base error gva 억원 | phase129 balanced error gva 억원 | phase129 balanced error rate % | phase129 balanced reduction vs base 억원 | phase129 balanced option id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 포항시 | F00 | 41 | 종합 건설업 | 12,603.38 | 516.59 | 3.16 | 0.03 | 513.43 | phase127_comwel_employment_workers_F00_all |
| 포항시 | F00 | 42 | 전문직별 공사업 | 6,565.34 | 516.59 | 3.16 | 0.05 | 513.43 | phase127_comwel_employment_workers_F00_all |
| 포항시 | MN0 | 74 | 사업시설 관리 및 조경 서비스업 | 1,421.27 | 390.23 | 129.65 | 9.12 | 260.58 | phase127_comwel_workplace_count_facility_support_74_76 |
| 고양시 | MN0 | 70 | 연구개발업 | 1,920.21 | 223.45 | 5.63 | 0.29 | 217.82 | phase127_comwel_workplace_count_professional_70_73 |
| 포항시 | MN0 | 75 | 사업지원 서비스업 | 2,693.30 | 226.53 | 33.57 | 1.25 | 192.96 | phase127_comwel_workplace_count_facility_support_74_76 |
| 고양시 | MN0 | 73 | 과학기술 서비스업 | 968.98 | 159.62 | 3.20 | 0.33 | 156.41 | phase127_comwel_workplace_count_professional_70_73 |
| 포항시 | Q00 | 87 | 사회복지 서비스업 | 1,795.00 | 157.93 | 4.19 | 0.23 | 153.74 | phase127_comwel_employment_workers_Q00_all |
| 포항시 | Q00 | 86 | 보건업 | 8,754.86 | 157.93 | 4.19 | 0.05 | 153.74 | phase127_comwel_employment_workers_Q00_all |
| 고양시 | J00 | 58 | 출판업 | 2,524.21 | 123.94 | 0.39 | 0.02 | 123.56 | phase127_comwel_employment_workers_content_58_60 |
| 고양시 | G00 | 47 | 소매업 | 12,778.67 | 110.42 | 5.79 | 0.05 | 104.64 | phase127_comwel_employment_workers_G00_all |
| 고양시 | J00 | 59 | 영상·오디오 제작업 | 1,467.02 | 319.38 | 219.93 | 14.99 | 99.44 | phase127_comwel_employment_workers_content_58_60 |
| 고양시 | K00 | 66 | 금융·보험 관련 서비스업 | 1,473.92 | 111.58 | 14.59 | 0.99 | 96.98 | phase127_comwel_workplace_count_K00_all |
| 고양시 | G00 | 45 | 자동차·부품 판매업 | 2,304.83 | 107.92 | 45.12 | 1.96 | 62.80 | phase127_comwel_employment_workers_G00_all |
| 고양시 | K00 | 64 | 금융업 | 6,909.30 | 174.92 | 131.60 | 1.90 | 43.33 | phase127_comwel_workplace_count_K00_all |
| 고양시 | MN0 | 76 | 임대업 | 1,610.20 | 48.22 | 5.38 | 0.33 | 42.84 | phase127_comwel_employment_workers_facility_support_74_76 |
| 고양시 | MN0 | 74 | 사업시설 관리업 | 1,389.38 | 31.76 | 6.55 | 0.47 | 25.20 | phase127_comwel_employment_workers_facility_support_74_76 |
| 고양시 | C00 | 23 | 비금속 광물제품 제조업 | 1,153.87 | 20.46 | 0.27 | 0.02 | 20.18 | phase127_comwel_workplace_count_mfg_material_20_25 |
| 고양시 | ERS | 38 | 폐기물 처리·재생업 | 1,408.65 | 22.11 | 1.98 | 0.14 | 20.13 | phase127_comwel_workplace_count_environment_36_39 |
| 고양시 | ERS | 36 | 수도업 | 377.33 | 38.94 | 22.29 | 5.91 | 16.65 | phase127_comwel_workplace_count_environment_36_39 |
| 고양시 | C00 | 22 | 고무·플라스틱 제조업 | 1,557.02 | 18.31 | 7.74 | 0.50 | 10.57 | phase127_comwel_workplace_count_mfg_material_20_25 |
| 고양시 | C00 | 20 | 화학물질·화학제품 제조업 | 723.76 | 103.08 | 93.96 | 12.98 | 9.13 | phase127_comwel_workplace_count_mfg_material_20_25 |
| 고양시 | MN0 | 75 | 사업지원 서비스업 | 4,277.03 | 68.07 | 63.53 | 1.49 | 4.53 | phase127_comwel_employment_workers_facility_support_74_76 |
| 고양시 | C00 | 21 | 의약품 제조업 | 69.97 | 33.00 | 32.68 | 46.70 | 0.32 | phase127_comwel_workplace_count_mfg_material_20_25 |

## 악화 셀 감사

| city | parent code | middle code | middle label | actual gva 억원 | phase129 base error gva 억원 | phase129 balanced error gva 억원 | phase129 balanced error rate % | phase129 balanced option id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | J00 | 60 | 방송업 | 954.74 | 406.84 | 430.95 | 45.14 | phase127_comwel_employment_workers_content_58_60 |
| 고양시 | MN0 | 71 | 전문 서비스업 | 4,106.09 | 4.81 | 129.17 | 3.15 | phase127_comwel_workplace_count_professional_70_73 |
| 고양시 | K00 | 65 | 보험·연금업 | 5,240.25 | 63.35 | 117.00 | 2.23 | phase127_comwel_workplace_count_K00_all |
| 고양시 | ERS | 37 | 하수·폐수 처리업 | 444.87 | 91.79 | 99.23 | 22.31 | phase127_comwel_workplace_count_environment_36_39 |
| 고양시 | MN0 | 72 | 건축·엔지니어링 서비스업 | 2,345.78 | 7.42 | 68.74 | 2.93 | phase127_comwel_workplace_count_professional_70_73 |
| 고양시 | G00 | 46 | 도매·상품중개업 | 16,007.70 | 2.50 | 39.33 | 0.25 | phase127_comwel_employment_workers_G00_all |
| 고양시 | C00 | 25 | 금속가공제품 제조업 | 1,295.89 | 6.93 | 16.49 | 1.27 | phase127_comwel_workplace_count_mfg_material_20_25 |
| 고양시 | C00 | 24 | 1차 금속 제조업 | 137.41 | 3.09 | 4.57 | 3.32 | phase127_comwel_workplace_count_mfg_material_20_25 |
| 포항시 | MN0 | 76 | 임대업; 부동산 제외 | 635.20 | 90.91 | 91.39 | 14.39 | phase127_comwel_workplace_count_facility_support_74_76 |

## 남은 10% 초과 셀

| city | parent code | middle code | middle label | actual gva 억원 | phase129 balanced predicted gva 억원 | phase129 balanced error gva 억원 | phase129 balanced error rate % | phase129 balanced option id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | ERS | 94 | 협회·단체 | 990.96 | 1,775.00 | 784.03 | 79.12 | phase114_precision_base |
| 고양시 | ERS | 91 | 스포츠·오락 서비스업 | 4,365.64 | 3,634.49 | 731.16 | 16.75 | phase114_precision_base |
| 고양시 | J00 | 60 | 방송업 | 954.74 | 523.79 | 430.95 | 45.14 | phase127_comwel_employment_workers_content_58_60 |
| 고양시 | C00 | 14 | 의복·모피 제조업 | 977.21 | 728.74 | 248.47 | 25.43 | phase114_precision_base |
| 고양시 | J00 | 59 | 영상·오디오 제작업 | 1,467.02 | 1,686.95 | 219.93 | 14.99 | phase127_comwel_employment_workers_content_58_60 |
| 고양시 | C00 | 15 | 가죽·가방·신발 제조업 | 572.01 | 418.43 | 153.58 | 26.85 | phase114_precision_base |
| 고양시 | J00 | 62 | 컴퓨터·시스템통합업 | 750.55 | 892.10 | 141.55 | 18.86 | phase114_precision_base |
| 고양시 | C00 | 10 | 식료품 제조업 | 1,085.48 | 1,198.24 | 112.76 | 10.39 | phase114_precision_base |
| 고양시 | ERS | 37 | 하수·폐수 처리업 | 444.87 | 345.63 | 99.23 | 22.31 | phase127_comwel_workplace_count_environment_36_39 |
| 고양시 | C00 | 20 | 화학물질·화학제품 제조업 | 723.76 | 629.80 | 93.96 | 12.98 | phase127_comwel_workplace_count_mfg_material_20_25 |
| 고양시 | C00 | 34 | 산업용 기계 수리업 | 388.16 | 447.03 | 58.87 | 15.17 | phase114_precision_base |
| 고양시 | C00 | 21 | 의약품 제조업 | 69.97 | 102.65 | 32.68 | 46.70 | phase127_comwel_workplace_count_mfg_material_20_25 |
| 고양시 | C00 | 30 | 자동차·트레일러 제조업 | 159.83 | 190.31 | 30.48 | 19.07 | phase114_precision_base |
| 고양시 | H00 | 50 | 수상 운송업 | 35.94 | 22.03 | 13.91 | 38.71 | phase114_precision_base |
| 포항시 | MN0 | 72 | 건축기술 엔지니어링 및 기타 과학기술 서비스업 | 2,535.33 | 3,567.79 | 1,032.46 | 40.72 | phase114_precision_base |
| 포항시 | K00 | 65 | 보험 및 연금업 | 4,807.52 | 4,114.05 | 693.47 | 14.42 | phase114_precision_base |
| 포항시 | K00 | 66 | 금융 및 보험 관련 서비스업 | 859.14 | 1,268.31 | 409.17 | 47.63 | phase114_precision_base |
| 포항시 | C00 | 28 | 전기장비 제조업 | 971.67 | 585.54 | 386.13 | 39.74 | phase114_precision_base |
| 포항시 | ERS | 96 | 기타 개인 서비스업 | 910.66 | 1,260.62 | 349.96 | 38.43 | phase114_precision_base |
| 포항시 | C00 | 34 | 산업용 기계 및 장비 수리업 | 503.93 | 169.34 | 334.59 | 66.40 | phase114_precision_base |
| 포항시 | K00 | 64 | 금융업 | 2,788.74 | 3,073.03 | 284.30 | 10.19 | phase114_precision_base |
| 포항시 | ERS | 36 | 수도업 | 439.72 | 267.40 | 172.32 | 39.19 | phase114_precision_base |
| 포항시 | ERS | 37 | 하수 폐수 및 분뇨 처리업 | 296.03 | 159.05 | 136.99 | 46.27 | phase114_precision_base |
| 포항시 | MN0 | 76 | 임대업; 부동산 제외 | 635.20 | 543.81 | 91.39 | 14.39 | phase127_comwel_workplace_count_facility_support_74_76 |
| 포항시 | J00 | 60 | 방송업 | 386.79 | 304.82 | 81.98 | 21.19 | phase114_precision_base |
| 포항시 | MN0 | 73 | 기타 전문 과학 및 기술 서비스업 | 120.05 | 192.38 | 72.32 | 60.24 | phase114_precision_base |
| 포항시 | J00 | 62 | 컴퓨터 프로그래밍 시스템 통합 및 관리업 | 194.64 | 266.36 | 71.72 | 36.85 | phase114_precision_base |
| 포항시 | C00 | 31 | 기타 운송장비 제조업 | 255.79 | 295.58 | 39.79 | 15.56 | phase114_precision_base |
| 포항시 | C00 | 16 | 목재 및 나무제품 제조업; 가구 제외 | 60.44 | 85.92 | 25.48 | 42.15 | phase114_precision_base |
| 포항시 | C00 | 22 | 고무 및 플라스틱제품 제조업 | 101.94 | 123.26 | 21.32 | 20.91 | phase114_precision_base |
| 포항시 | ERS | 39 | 환경 정화 및 복원업 | 34.85 | 14.63 | 20.22 | 58.01 | phase114_precision_base |
| 포항시 | J00 | 59 | 영상ㆍ오디오 기록물 제작 및 배급업 | 139.78 | 120.92 | 18.86 | 13.50 | phase114_precision_base |
| 포항시 | C00 | 30 | 자동차 및 트레일러 제조업 | 104.53 | 116.84 | 12.31 | 11.77 | phase114_precision_base |
| 포항시 | J00 | 63 | 정보서비스업 | 3.95 | 13.83 | 9.88 | 250.49 | phase114_precision_base |

## 판정

균형형 라우팅은 포스터에 바로 넣기보다는 내부 정밀화 후보로 쓰는 것이 안전하다. 다만 고양·포항 모두 총오차와 10% 초과 셀 수를 추가로 줄였고, 남은 큰 오차는 협회·단체, 방송·정보서비스, 시설처리·환경, 일부 제조 소분류처럼 공개 활동자료 설명력이 낮은 군에 집중된다.
