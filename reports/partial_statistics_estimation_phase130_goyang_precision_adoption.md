# Phase130 고양시 정밀오차 개선안 채택 감사

## 목적

Phase129 균형형 정밀 라우팅을 고양시 정밀화 산출물에 적용할 수 있는지 감사했다. 예측값은 실제 GVA를 직접 대입하지 않고, Phase127 후보자료에서 검증된 고용·산재 사업장 구조 및 활동자료 비중을 사용한 값이다.

## 요약

| city | phase127 strict error 억원 | phase127 strict wape % | phase127 strict gt10 cells | phase127 strict gt20 cells | phase130 error 억원 | phase130 wape % | phase130 gt10 cells | phase130 gt20 cells | error reduction 억원 | worsened cells | worsen sum 억원 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 5,114.68 | 3.02 | 17 | 8 | 4,466.53 | 2.64 | 14 | 7 | 648.15 | 8 | 320.42 |

## 개선 셀

| parent code | middle code | middle label | actual gva 억원 | phase127 strict error gva 억원 | phase130 error gva 억원 | phase130 error rate % | phase130 error reduction vs phase127 strict 억원 | phase130 option id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MN0 | 70 | 연구개발업 | 1,920.21 | 223.45 | 5.63 | 0.29 | 217.82 | phase127_comwel_workplace_count_professional_70_73 |
| MN0 | 73 | 과학기술 서비스업 | 968.98 | 159.62 | 3.20 | 0.33 | 156.41 | phase127_comwel_workplace_count_professional_70_73 |
| J00 | 58 | 출판업 | 2,524.21 | 123.94 | 0.39 | 0.02 | 123.56 | phase127_comwel_employment_workers_content_58_60 |
| J00 | 59 | 영상·오디오 제작업 | 1,467.02 | 319.38 | 219.93 | 14.99 | 99.44 | phase127_comwel_employment_workers_content_58_60 |
| K00 | 66 | 금융·보험 관련 서비스업 | 1,473.92 | 111.58 | 14.59 | 0.99 | 96.98 | phase127_comwel_workplace_count_K00_all |
| G00 | 47 | 소매업 | 12,778.67 | 102.05 | 5.79 | 0.05 | 96.26 | phase127_comwel_employment_workers_G00_all |
| G00 | 45 | 자동차·부품 판매업 | 2,304.83 | 102.89 | 45.12 | 1.96 | 57.78 | phase127_comwel_employment_workers_G00_all |
| K00 | 64 | 금융업 | 6,909.30 | 174.92 | 131.60 | 1.90 | 43.33 | phase127_comwel_workplace_count_K00_all |
| C00 | 23 | 비금속 광물제품 제조업 | 1,153.87 | 20.46 | 0.27 | 0.02 | 20.18 | phase127_comwel_workplace_count_mfg_material_20_25 |
| ERS | 38 | 폐기물 처리·재생업 | 1,408.65 | 22.11 | 1.98 | 0.14 | 20.13 | phase127_comwel_workplace_count_environment_36_39 |
| ERS | 36 | 수도업 | 377.33 | 38.94 | 22.29 | 5.91 | 16.65 | phase127_comwel_workplace_count_environment_36_39 |
| C00 | 22 | 고무·플라스틱 제조업 | 1,557.02 | 18.31 | 7.74 | 0.50 | 10.57 | phase127_comwel_workplace_count_mfg_material_20_25 |
| C00 | 20 | 화학물질·화학제품 제조업 | 723.76 | 103.08 | 93.96 | 12.98 | 9.13 | phase127_comwel_workplace_count_mfg_material_20_25 |
| C00 | 21 | 의약품 제조업 | 69.97 | 33.00 | 32.68 | 46.70 | 0.32 | phase127_comwel_workplace_count_mfg_material_20_25 |

## 악화 셀 감사

| parent code | middle code | middle label | actual gva 억원 | phase127 strict error gva 억원 | phase130 error gva 억원 | phase130 error rate % | phase130 option id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| J00 | 60 | 방송업 | 954.74 | 406.84 | 430.95 | 45.14 | phase127_comwel_employment_workers_content_58_60 |
| MN0 | 71 | 전문 서비스업 | 4,106.09 | 4.81 | 129.17 | 3.15 | phase127_comwel_workplace_count_professional_70_73 |
| K00 | 65 | 보험·연금업 | 5,240.25 | 63.35 | 117.00 | 2.23 | phase127_comwel_workplace_count_K00_all |
| ERS | 37 | 하수·폐수 처리업 | 444.87 | 91.79 | 99.23 | 22.31 | phase127_comwel_workplace_count_environment_36_39 |
| MN0 | 72 | 건축·엔지니어링 서비스업 | 2,345.78 | 7.42 | 68.74 | 2.93 | phase127_comwel_workplace_count_professional_70_73 |
| G00 | 46 | 도매·상품중개업 | 16,007.70 | 0.84 | 39.33 | 0.25 | phase127_comwel_employment_workers_G00_all |
| C00 | 25 | 금속가공제품 제조업 | 1,295.89 | 6.93 | 16.49 | 1.27 | phase127_comwel_workplace_count_mfg_material_20_25 |
| C00 | 24 | 1차 금속 제조업 | 137.41 | 3.09 | 4.57 | 3.32 | phase127_comwel_workplace_count_mfg_material_20_25 |

## 남은 10% 초과 셀

| parent code | middle code | middle label | actual gva 억원 | phase130 predicted gva 억원 | phase130 error gva 억원 | phase130 error rate % | phase130 option id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ERS | 94 | 협회·단체 | 990.96 | 1,775.00 | 784.03 | 79.12 | phase114_precision_base |
| ERS | 91 | 스포츠·오락 서비스업 | 4,365.64 | 3,634.49 | 731.16 | 16.75 | phase114_precision_base |
| J00 | 60 | 방송업 | 954.74 | 523.79 | 430.95 | 45.14 | phase127_comwel_employment_workers_content_58_60 |
| C00 | 14 | 의복·모피 제조업 | 977.21 | 728.74 | 248.47 | 25.43 | phase114_precision_base |
| J00 | 59 | 영상·오디오 제작업 | 1,467.02 | 1,686.95 | 219.93 | 14.99 | phase127_comwel_employment_workers_content_58_60 |
| C00 | 15 | 가죽·가방·신발 제조업 | 572.01 | 418.43 | 153.58 | 26.85 | phase114_precision_base |
| J00 | 62 | 컴퓨터·시스템통합업 | 750.55 | 892.10 | 141.55 | 18.86 | phase114_precision_base |
| C00 | 10 | 식료품 제조업 | 1,085.48 | 1,198.24 | 112.76 | 10.39 | phase114_precision_base |
| ERS | 37 | 하수·폐수 처리업 | 444.87 | 345.63 | 99.23 | 22.31 | phase127_comwel_workplace_count_environment_36_39 |
| C00 | 20 | 화학물질·화학제품 제조업 | 723.76 | 629.80 | 93.96 | 12.98 | phase127_comwel_workplace_count_mfg_material_20_25 |
| C00 | 34 | 산업용 기계 수리업 | 388.16 | 447.03 | 58.87 | 15.17 | phase114_precision_base |
| C00 | 21 | 의약품 제조업 | 69.97 | 102.65 | 32.68 | 46.70 | phase127_comwel_workplace_count_mfg_material_20_25 |
| C00 | 30 | 자동차·트레일러 제조업 | 159.83 | 190.31 | 30.48 | 19.07 | phase114_precision_base |
| H00 | 50 | 수상 운송업 | 35.94 | 22.03 | 13.91 | 38.71 | phase114_precision_base |

## 판정

고양시는 Phase130 개선안을 적용하면 총 정밀오차와 10% 초과 셀 수가 함께 감소한다. 다만 일부 저오차 셀이 소폭 악화되므로, 포스터에는 총오차 개선과 남은 취약 산업을 함께 표시하는 방식이 안전하다.
